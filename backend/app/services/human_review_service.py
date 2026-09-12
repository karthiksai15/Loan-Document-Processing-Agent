"""
Human Review Service — Phase 18 Confidence + Human-in-the-Loop Review

Implements:
- Deterministic Human Review Gate evaluation
- Officer workflow actions: acknowledge, notes, request documents
- Final human decision recording with strict override governance
- Privacy-safe audit trail logging and retrieval
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.db.models import (
    LoanApplicationModel,
    AgentReviewModel,
    ReviewAssessmentModel,
    DocumentModel,
    ApplicationVerificationModel,
    VerificationFindingModel,
    HumanReviewModel,
    HumanReviewAuditModel,
)
from app.services.confidence_service import evaluate_confidence
from app.services.review_score_service import compute_and_save_review_assessment
from app.schemas.human_review import (
    HumanReviewReason,
    OfficerNoteSchema,
    RequestedDocumentItem,
    HumanReviewGateResponse,
    HumanReviewAuditItem,
    HumanReviewAuditResponse,
)

VALID_DECISIONS = {
    "APPROVED",
    "REJECTED",
    "OFFICER_INVESTIGATION",
    "DOCUMENT_FOLLOWUP",
    "ESCALATED",
}


def log_audit_event(
    db: Session,
    application_id: str,
    action: str,
    actor_type: str = "SYSTEM",
    actor_id: str = "system",
    previous_status: Optional[str] = None,
    new_status: Optional[str] = None,
    note: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> HumanReviewAuditModel:
    """Appends an immutable, privacy-safe audit record to the database."""
    audit_id = f"AUD-{application_id}-{uuid.uuid4().hex[:8]}"
    audit_entry = HumanReviewAuditModel(
        audit_id=audit_id,
        application_id=application_id,
        action=action,
        previous_status=previous_status,
        new_status=new_status,
        actor_type=actor_type,
        actor_id=actor_id,
        note=note,
        details=details or {},
        timestamp=datetime.utcnow(),
    )
    db.add(audit_entry)
    db.flush()
    return audit_entry


def is_decision_override(ai_recommendation: str, human_decision: str) -> bool:
    """
    Determines if human decision deviates from AI recommendation.
    - If ai_recommendation == human_decision: aligned (False)
    - If ai_recommendation == 'STANDARD_REVIEW' and human_decision == 'APPROVED': aligned (False)
    - If ai_recommendation == 'ESCALATE' and human_decision in ('ESCALATE', 'ESCALATED', 'ESCALATE_TO_SENIOR'): aligned (False)
    - If ai_recommendation in ('OFFICER_INVESTIGATION', 'DOCUMENT_FOLLOWUP') and human_decision in (
        'OFFICER_INVESTIGATION',
        'SCHEDULE_INTERVIEW',
        'REQUEST_ADDITIONAL_DOCUMENTS',
        'DOCUMENT_FOLLOWUP',
    ):
        return False
    - In all other cases: override (True)
    """
    ai = (ai_recommendation or "").upper().strip()
    dec = (human_decision or "").upper().strip()
    if ai == dec:
        return False
    if ai == "STANDARD_REVIEW" and dec == "APPROVED":
        return False
    if ai == "ESCALATE" and dec in ("ESCALATE", "ESCALATED", "ESCALATE_TO_SENIOR"):
        return False
    if ai in ("OFFICER_INVESTIGATION", "DOCUMENT_FOLLOWUP") and dec in (
        "OFFICER_INVESTIGATION",
        "SCHEDULE_INTERVIEW",
        "REQUEST_ADDITIONAL_DOCUMENTS",
        "DOCUMENT_FOLLOWUP",
    ):
        return False
    return True


def evaluate_human_review_gate(
    application_id: str,
    db: Session,
    force_rebuild: bool = False,
) -> HumanReviewModel:
    """
    Deterministically evaluates whether an application requires human review.
    Checks:
      1. Identity mismatch across documents (CRITICAL ERROR)
      2. Salary / income mismatch
      3. Missing mandatory documents (PAYSLIP, BANK_STATEMENT, TAX_RETURN, KYC)
      4. Low confidence score (< 50 or level LOW)
      5. Degraded or failed AI investigation
      6. High review priority (Review Intelligence assessment == HIGH)
      7. Ungrounded policy or evidence citations
      8. Safety escalation required
    """
    app_obj = db.query(LoanApplicationModel).filter(LoanApplicationModel.application_id == application_id).first()
    if not app_obj:
        raise ValueError(f"Application '{application_id}' not found.")

    target_id = application_id.replace("APP-", "").upper()

    # If cached gate evaluation exists and not forcing rebuild, return existing
    existing = (
        db.query(HumanReviewModel)
        .filter(HumanReviewModel.application_id == application_id)
        .first()
    )
    if existing and not force_rebuild:
        return existing

    # 1. Fetch Latest Agent Review
    agent_review = (
        db.query(AgentReviewModel)
        .filter(AgentReviewModel.application_id == application_id)
        .order_by(AgentReviewModel.created_at.desc())
        .first()
    )

    # 2. Fetch or Compute Review Assessment
    review_assessment = (
        db.query(ReviewAssessmentModel)
        .filter(ReviewAssessmentModel.application_id == application_id)
        .first()
    )
    if not review_assessment:
        try:
            review_assessment = compute_and_save_review_assessment(db, application_id)
        except Exception as e:
            logger.warning(f"Could not compute review assessment for '{application_id}': {e}")
            review_assessment = None

    # 3. Compute Deterministic Confidence
    confidence = evaluate_confidence(application_id, db, agent_review=agent_review)

    # 4. Fetch Documents & Verification Findings
    docs = (
        db.query(DocumentModel)
        .filter(
            (DocumentModel.application_id == application_id) | (DocumentModel.applicant_id == target_id),
            DocumentModel.processing_status != "DELETED",
        )
        .all()
    )
    doc_types_present = set(
        (d.classified_document_type or d.document_type or "OTHER").upper() for d in docs
    )

    ver_record = (
        db.query(ApplicationVerificationModel)
        .filter(ApplicationVerificationModel.application_id == application_id)
        .first()
    )
    findings: List[VerificationFindingModel] = []
    if ver_record:
        findings = (
            db.query(VerificationFindingModel)
            .filter(VerificationFindingModel.verification_id == ver_record.id)
            .all()
        )

    # -------------------------------------------------------------------------
    # Evaluate Deterministic Gate Reasons
    # -------------------------------------------------------------------------
    reasons: List[Dict[str, str]] = []

    # Reason 1: Identity Mismatch
    identity_mismatches = [
        f for f in findings
        if f.result == "MISMATCH" and (
            f.verification_type in ["IDENTITY_COMPARISON", "APPLICATION_DOCUMENT_COMPARISON"]
            or any(k in (f.rule_name or "").upper() or k in (f.message or "").upper() or k in (f.field_a or "").upper() for k in ["NAME", "IDENTITY", "KYC", "DOB"])
        )
    ]
    if identity_mismatches:
        reasons.append({
            "code": "IDENTITY_MISMATCH",
            "severity": "ERROR",
            "description": "Critical identity mismatch detected between applicant declaration and identity documents.",
        })

    # Reason 2: Salary/Income Mismatch
    salary_mismatches = [
        f for f in findings
        if f.result == "MISMATCH" and (
            f.verification_type in ["INCOME_COMPARISON", "SALARY_COMPARISON"]
            or any(k in (f.rule_name or "").upper() or k in (f.message or "").upper() or k in (f.field_a or "").upper() for k in ["SALARY", "INCOME", "TURNOVER"])
        )
    ]
    if salary_mismatches:
        reasons.append({
            "code": "INCOME_MISMATCH",
            "severity": "WARNING",
            "description": "Declared income does not reconcile with document pay records.",
        })

    # Reason 3: Missing Mandatory Documents
    mandatory_types = ["PAYSLIP", "BANK_STATEMENT", "TAX_RETURN", "KYC"]
    missing_mandatory = [dt for dt in mandatory_types if dt not in doc_types_present]
    if missing_mandatory:
        severity = "ERROR" if len(missing_mandatory) >= 2 else "WARNING"
        reasons.append({
            "code": "MISSING_MANDATORY_DOCUMENTS",
            "severity": severity,
            "description": f"Missing mandatory document(s): {', '.join(missing_mandatory)}.",
        })

    # Reason 4: Low Confidence
    if confidence.level == "LOW" or confidence.score < settings.CONFIDENCE_MEDIUM_THRESHOLD:
        reasons.append({
            "code": "LOW_CONFIDENCE",
            "severity": "ERROR",
            "description": f"Confidence evaluation score ({confidence.score:.1f}/100) is below operational threshold.",
        })

    # Reason 5: Investigation Degraded or Failed
    if agent_review and agent_review.investigation_status in ("DEGRADED", "FAILED"):
        reasons.append({
            "code": "INVESTIGATION_DEGRADED",
            "severity": "ERROR",
            "description": f"AI investigation ended in {agent_review.investigation_status} state.",
        })

    # Reason 6: High Review Priority or High ML Risk
    if review_assessment and (
        review_assessment.review_priority == "HIGH"
        or review_assessment.ml_risk_level == "HIGH"
        or (review_assessment.ml_risk_score is not None and review_assessment.ml_risk_score >= 0.70)
    ):
        reasons.append({
            "code": "HIGH_RISK_PRIORITY",
            "severity": "WARNING",
            "description": "Application marked as HIGH risk / priority by Review Intelligence and ML risk model.",
        })

    # Reason 7: Ungrounded Citations or Evidence Insufficiency
    if agent_review and (
        agent_review.grounding_status == "UNGROUNDED"
        or (agent_review.evidence_sufficiency and agent_review.evidence_sufficiency.upper() == "INSUFFICIENT")
    ):
        reasons.append({
            "code": "UNGROUNDED_EVIDENCE",
            "severity": "ERROR",
            "description": "Agent review contains ungrounded citations or critical evidence gaps.",
        })

    # Reason 8: Safety Escalation
    if agent_review and bool(agent_review.escalation_required):
        reasons.append({
            "code": "SAFETY_ESCALATION",
            "severity": "ERROR",
            "description": f"AI safety guard triggered escalation: {agent_review.escalation_reason or 'Risk policy escalation'}.",
        })

    # Determine Gate Status
    is_required = len(reasons) > 0
    status = "REQUIRED" if is_required else "NOT_REQUIRED"

    # AI Recommendation
    if agent_review and agent_review.recommended_next_step:
        ai_recommendation = agent_review.recommended_next_step
    elif review_assessment and review_assessment.recommended_action:
        ai_recommendation = review_assessment.recommended_action
    else:
        ai_recommendation = "STANDARD_REVIEW"

    # Save / Update Model
    if existing:
        existing.ai_recommendation = ai_recommendation
        existing.confidence_score = confidence.score
        existing.confidence_level = confidence.level
        existing.confidence_factors = [b.model_dump() for b in confidence.breakdown]
        existing.human_review_required = 1 if is_required else 0
        existing.human_review_status = status
        existing.human_review_reasons = reasons
        existing.updated_at = datetime.utcnow()
        record = existing
    else:
        review_action_id = f"HRV-{application_id}-{uuid.uuid4().hex[:8]}"
        record = HumanReviewModel(
            review_action_id=review_action_id,
            application_id=application_id,
            agent_review_id=agent_review.agent_review_id if agent_review else None,
            ai_recommendation=ai_recommendation,
            confidence_score=confidence.score,
            confidence_level=confidence.level,
            confidence_factors=[b.model_dump() for b in confidence.breakdown],
            human_review_required=1 if is_required else 0,
            human_review_status=status,
            human_review_reasons=reasons,
            human_decision=None,
            override=0,
            override_reason=None,
            officer_notes=[],
            requested_documents=[],
            reviewed_by=None,
            reviewed_at=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(record)

    db.flush()

    # Log Audit Event
    log_audit_event(
        db=db,
        application_id=application_id,
        action="HUMAN_REVIEW_GATE_EVALUATED",
        actor_type="SYSTEM",
        actor_id="human_review_gate",
        previous_status=None,
        new_status=status,
        note=f"Gate evaluated: required={is_required}, status={status}, confidence={confidence.score:.1f} ({confidence.level})",
        details={
            "confidence_score": confidence.score,
            "confidence_level": confidence.level,
            "reasons_count": len(reasons),
            "reasons": reasons,
            "ai_recommendation": ai_recommendation,
        },
    )
    db.commit()
    return record


def acknowledge_review(
    application_id: str,
    officer_id: str,
    db: Session,
) -> HumanReviewModel:
    """
    Loan officer acknowledges that an application requires human review.
    Transitions human_review_status from REQUIRED -> IN_REVIEW.
    """
    record = evaluate_human_review_gate(application_id, db)
    prev_status = record.human_review_status

    if prev_status == "REQUIRED":
        record.human_review_status = "IN_REVIEW"
        record.reviewed_by = officer_id
        record.updated_at = datetime.utcnow()

        # Synchronize LoanApplicationModel status
        app_obj = db.query(LoanApplicationModel).filter(
            (LoanApplicationModel.application_id == application_id) |
            (LoanApplicationModel.application_number == application_id)
        ).first()
        if app_obj and app_obj.status in ("SUBMITTED", "PENDING"):
            app_obj.status = "UNDER_REVIEW"
            app_obj.updated_at = datetime.utcnow()

        log_audit_event(
            db=db,
            application_id=application_id,
            action="HUMAN_REVIEW_ACKNOWLEDGED",
            actor_type="LOAN_OFFICER",
            actor_id=officer_id,
            previous_status=prev_status,
            new_status="IN_REVIEW",
            note=f"Review acknowledged by loan officer {officer_id}.",
            details={"officer_id": officer_id},
        )
        db.commit()

    return record


def add_officer_note(
    application_id: str,
    note_text: str,
    officer_id: str,
    db: Session,
) -> HumanReviewModel:
    """Appends an officer note to the application's human review record."""
    if not note_text or not note_text.strip():
        raise ValueError("Officer note content cannot be empty.")

    record = evaluate_human_review_gate(application_id, db)

    current_notes = list(record.officer_notes or [])
    note_obj = {
        "note_id": f"NOTE-{uuid.uuid4().hex[:8]}",
        "officer_id": officer_id,
        "text": note_text.strip(),
        "timestamp": datetime.utcnow().isoformat(),
    }
    current_notes.append(note_obj)

    record.officer_notes = current_notes
    record.updated_at = datetime.utcnow()

    log_audit_event(
        db=db,
        application_id=application_id,
        action="OFFICER_NOTE_ADDED",
        actor_type="LOAN_OFFICER",
        actor_id=officer_id,
        previous_status=record.human_review_status,
        new_status=record.human_review_status,
        note=f"Officer note added by {officer_id}.",
        details={"note_id": note_obj["note_id"], "snippet": note_text[:50]},
    )
    db.commit()
    return record


def request_documents(
    application_id: str,
    documents: List[str],
    reason: str,
    officer_id: str,
    db: Session,
) -> HumanReviewModel:
    """
    Loan officer requests additional or corrected documents from applicant.
    Appends to requested_documents and updates status to IN_REVIEW if previously REQUIRED.
    """
    if not documents:
        raise ValueError("At least one document type must be specified.")
    if not reason or not reason.strip():
        raise ValueError("Reason for requesting documents cannot be empty.")

    record = evaluate_human_review_gate(application_id, db)
    prev_status = record.human_review_status

    current_requests = list(record.requested_documents or [])
    now_iso = datetime.utcnow().isoformat()
    for doc in documents:
        current_requests.append({
            "doc_type": doc.strip().upper(),
            "reason": reason.strip(),
            "requested_by": officer_id,
            "timestamp": now_iso,
        })

    record.requested_documents = current_requests
    new_status = prev_status
    if prev_status == "REQUIRED":
        new_status = "IN_REVIEW"
        record.human_review_status = new_status

    record.updated_at = datetime.utcnow()

    # Synchronize LoanApplicationModel status
    app_obj = db.query(LoanApplicationModel).filter(
        (LoanApplicationModel.application_id == application_id) |
        (LoanApplicationModel.application_number == application_id)
    ).first()
    if app_obj:
        app_obj.status = "ADDITIONAL_DOCUMENTS_REQUIRED"
        app_obj.updated_at = datetime.utcnow()

    log_audit_event(
        db=db,
        application_id=application_id,
        action="DOCUMENTS_REQUESTED",
        actor_type="LOAN_OFFICER",
        actor_id=officer_id,
        previous_status=prev_status,
        new_status=new_status,
        note=f"Officer requested documents: {', '.join(documents)}.",
        details={"documents": documents, "reason": reason.strip()},
    )
    db.commit()
    return record


def record_human_decision(
    application_id: str,
    decision: str,
    officer_id: str,
    db: Session,
    override_reason: Optional[str] = None,
    notes: Optional[str] = None,
    decision_reason: Optional[str] = None,
) -> HumanReviewModel:
    """
    Records final human decision on the application (Phase 18 & 19).
    Enforces:
      - decision_reason is required for APPROVED and REJECTED.
      - override_reason is strictly required if decision != ai_recommendation.
      - Sets override=True and human_review_status='OVERRIDDEN' when deviating.
      - Sets override=False and human_review_status='COMPLETED' when aligned.
    """
    dec_clean = decision.strip().upper()
    if dec_clean not in VALID_DECISIONS:
        raise ValueError(
            f"Invalid decision '{decision}'. Must be one of: {', '.join(sorted(VALID_DECISIONS))}."
        )

    record = evaluate_human_review_gate(application_id, db)
    prev_status = record.human_review_status

    # Evaluate override condition
    override = is_decision_override(record.ai_recommendation, dec_clean)

    if override:
        clean_override_reason = (override_reason or decision_reason or "").strip()
        if not clean_override_reason:
            raise ValueError(
                "Override reason is mandatory; decision reason is required when human decision deviates from AI recommendation."
            )
        new_status = "OVERRIDDEN"
        effective_reason = (decision_reason or override_reason or "").strip()
    else:
        new_status = "COMPLETED"
        effective_reason = (decision_reason or override_reason or "").strip()
        if dec_clean in ("APPROVED", "REJECTED") and not effective_reason:
            raise ValueError(f"Decision reason is required for final action '{dec_clean}'.")
        clean_override_reason = effective_reason or None

    # Append optional note
    if notes and notes.strip():
        current_notes = list(record.officer_notes or [])
        current_notes.append({
            "note_id": f"NOTE-{uuid.uuid4().hex[:8]}",
            "officer_id": officer_id,
            "text": notes.strip(),
            "timestamp": datetime.utcnow().isoformat(),
        })
        record.officer_notes = current_notes

    record.human_decision = dec_clean
    record.override = 1 if override else 0
    record.override_reason = clean_override_reason if override else None
    record.decision_reason = effective_reason if effective_reason else clean_override_reason
    record.human_review_status = new_status
    record.reviewed_by = officer_id
    record.reviewed_at = datetime.utcnow()
    record.updated_at = datetime.utcnow()

    # Synchronize LoanApplicationModel status
    app_obj = db.query(LoanApplicationModel).filter(
        (LoanApplicationModel.application_id == application_id) |
        (LoanApplicationModel.application_number == application_id)
    ).first()
    if app_obj:
        if dec_clean in ("APPROVED", "REJECTED", "ESCALATED"):
            app_obj.status = dec_clean
        elif dec_clean in ("OFFICER_INVESTIGATION", "SCHEDULE_INTERVIEW"):
            app_obj.status = "UNDER_REVIEW"
        elif dec_clean in ("REQUEST_ADDITIONAL_DOCUMENTS", "DOCUMENT_FOLLOWUP"):
            app_obj.status = "ADDITIONAL_DOCUMENTS_REQUIRED"
        app_obj.updated_at = datetime.utcnow()

    # Log Override Audit if applicable
    if override:
        log_audit_event(
            db=db,
            application_id=application_id,
            action="AI_RECOMMENDATION_OVERRIDDEN",
            actor_type="LOAN_OFFICER",
            actor_id=officer_id,
            previous_status=prev_status,
            new_status=new_status,
            note=f"Officer overridden AI recommendation '{record.ai_recommendation}' with '{dec_clean}'. Reason: {clean_override_reason}",
            details={
                "ai_recommendation": record.ai_recommendation,
                "human_decision": dec_clean,
                "override_reason": clean_override_reason,
                "decision_reason": record.decision_reason,
            },
        )

    # Log Human Decision Audit
    log_audit_event(
        db=db,
        application_id=application_id,
        action="HUMAN_DECISION_RECORDED",
        actor_type="LOAN_OFFICER",
        actor_id=officer_id,
        previous_status=prev_status,
        new_status=new_status,
        note=f"Human decision recorded: {dec_clean} (override={override}).",
        details={
            "decision": dec_clean,
            "decision_reason": record.decision_reason,
            "override": override,
            "override_reason": clean_override_reason,
            "ai_recommendation": record.ai_recommendation,
        },
    )
    db.commit()
    return record


VALID_FEEDBACK_CATEGORIES = {
    "CORRECT",
    "PARTIALLY_CORRECT",
    "INCORRECT",
    "NOT_APPLICABLE",
}


def add_officer_feedback(
    application_id: str,
    officer_id: str,
    feedback_text: str,
    db: Session,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """Records structured feedback from a loan officer on the AI review / process."""
    if not feedback_text or not feedback_text.strip():
        raise ValueError("Feedback text cannot be empty.")
    if len(feedback_text) > 2000:
        raise ValueError("Feedback text exceeds maximum length of 2000 characters.")

    cat_clean = category.strip().upper() if category and category.strip() else None
    if cat_clean and cat_clean not in VALID_FEEDBACK_CATEGORIES:
        raise ValueError(
            f"Invalid feedback category '{category}'. Must be one of: {', '.join(sorted(VALID_FEEDBACK_CATEGORIES))}."
        )

    record = evaluate_human_review_gate(application_id, db)

    current_feedback = list(record.officer_feedback or [])
    fb_obj = {
        "feedback_id": f"FB-{uuid.uuid4().hex[:8]}",
        "officer_id": officer_id.strip(),
        "feedback": feedback_text.strip(),
        "category": cat_clean,
        "timestamp": datetime.utcnow().isoformat(),
    }
    current_feedback.append(fb_obj)
    record.officer_feedback = current_feedback
    record.updated_at = datetime.utcnow()

    log_audit_event(
        db=db,
        application_id=application_id,
        action="OFFICER_FEEDBACK_ADDED",
        actor_type="LOAN_OFFICER",
        actor_id=officer_id,
        previous_status=record.human_review_status,
        new_status=record.human_review_status,
        note=f"Officer feedback added: {feedback_text[:50]}",
        details=fb_obj,
    )
    db.commit()
    return fb_obj


def get_decision_history(application_id: str, db: Session) -> Dict[str, Any]:
    """
    Returns the complete decision and feedback history for an application.
    Enforces strict application-level isolation.
    """
    app_obj = db.query(LoanApplicationModel).filter(LoanApplicationModel.application_id == application_id).first()
    if not app_obj:
        raise ValueError(f"Application '{application_id}' not found.")

    record = evaluate_human_review_gate(application_id, db)

    # Determine alignment status
    if record.human_decision is None:
        alignment_status = "PENDING"
    elif bool(record.override):
        alignment_status = "OVERRIDDEN"
    else:
        alignment_status = "ALIGNED"

    # Query chronological audit events related to decisions and feedback
    audit_records = (
        db.query(HumanReviewAuditModel)
        .filter(HumanReviewAuditModel.application_id == application_id)
        .order_by(HumanReviewAuditModel.timestamp.asc())
        .all()
    )

    history_events = []
    for a in audit_records:
        history_events.append({
            "audit_id": a.audit_id,
            "action": a.action,
            "actor_type": a.actor_type,
            "actor_id": a.actor_id,
            "previous_status": a.previous_status,
            "new_status": a.new_status,
            "note": a.note,
            "details": a.details or {},
            "timestamp": a.timestamp.isoformat() if a.timestamp else "",
        })

    from app.schemas.human_review import OfficerFeedbackItem
    feedback_items = [
        OfficerFeedbackItem(
            feedback_id=f.get("feedback_id", ""),
            officer_id=f.get("officer_id", ""),
            feedback=f.get("feedback", ""),
            category=f.get("category"),
            timestamp=f.get("timestamp", ""),
        )
        for f in (record.officer_feedback or [])
    ]

    return {
        "application_id": record.application_id,
        "ai_recommendation": record.ai_recommendation,
        "human_decision": record.human_decision,
        "alignment_status": alignment_status,
        "decision_reason": record.decision_reason or record.override_reason,
        "override_reason": record.override_reason,
        "reviewed_by": record.reviewed_by,
        "reviewed_at": record.reviewed_at.isoformat() if record.reviewed_at else None,
        "feedback": feedback_items,
        "timestamp": record.reviewed_at.isoformat() if record.reviewed_at else (record.updated_at.isoformat() if record.updated_at else None),
        "history": history_events,
    }


def get_human_review(application_id: str, db: Session) -> HumanReviewModel:
    """Retrieves existing human review or evaluates gate if not yet evaluated."""
    return evaluate_human_review_gate(application_id, db)


def get_audit_trail(application_id: str, db: Session) -> List[HumanReviewAuditModel]:
    """
    Returns the chronological audit trail for an application.
    Strictly isolated by application_id.
    """
    app_obj = db.query(LoanApplicationModel).filter(LoanApplicationModel.application_id == application_id).first()
    if not app_obj:
        raise ValueError(f"Application '{application_id}' not found.")

    return (
        db.query(HumanReviewAuditModel)
        .filter(HumanReviewAuditModel.application_id == application_id)
        .order_by(HumanReviewAuditModel.timestamp.asc())
        .all()
    )


def format_gate_response(record: HumanReviewModel) -> HumanReviewGateResponse:
    """Formats HumanReviewModel into HumanReviewGateResponse schema."""
    reasons_list = [
        HumanReviewReason(
            code=r.get("code", "UNKNOWN"),
            severity=r.get("severity", "WARNING"),
            description=r.get("description", ""),
        )
        for r in (record.human_review_reasons or [])
    ]

    notes_list = [
        OfficerNoteSchema(
            note_id=n.get("note_id", ""),
            officer_id=n.get("officer_id", ""),
            text=n.get("text", ""),
            timestamp=n.get("timestamp", ""),
        )
        for n in (record.officer_notes or [])
    ]

    docs_list = [
        RequestedDocumentItem(
            doc_type=d.get("doc_type", ""),
            reason=d.get("reason", ""),
            requested_by=d.get("requested_by", ""),
            timestamp=d.get("timestamp", ""),
        )
        for d in (record.requested_documents or [])
    ]

    return HumanReviewGateResponse(
        application_id=record.application_id,
        review_action_id=record.review_action_id,
        agent_review_id=record.agent_review_id,
        ai_recommendation=record.ai_recommendation,
        confidence_score=record.confidence_score,
        confidence_level=record.confidence_level,
        confidence_factors=record.confidence_factors or [],
        human_review_required=bool(record.human_review_required),
        human_review_status=record.human_review_status,
        reasons=reasons_list,
        human_decision=record.human_decision,
        override=bool(record.override),
        override_reason=record.override_reason,
        decision_reason=record.decision_reason,
        officer_notes=notes_list,
        requested_documents=docs_list,
        officer_feedback=record.officer_feedback or [],
        reviewed_by=record.reviewed_by,
        reviewed_at=record.reviewed_at.isoformat() if record.reviewed_at else None,
        created_at=record.created_at.isoformat() if record.created_at else "",
        updated_at=record.updated_at.isoformat() if record.updated_at else "",
    )
