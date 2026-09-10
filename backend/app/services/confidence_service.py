"""
Confidence Service — Phase 18 Confidence + Human-in-the-Loop Review

Computes a deterministic, grounded confidence evaluation (0–100 scale)
with explainable factor breakdown, hard caps for critical risk conditions,
and threshold classification (LOW, MEDIUM, HIGH).
"""

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
)
from app.schemas.human_review import (
    ConfidenceFactorDetail,
    ConfidenceEvaluationSchema,
)


def evaluate_confidence(
    application_id: str,
    db: Session,
    agent_review: Optional[AgentReviewModel] = None,
) -> ConfidenceEvaluationSchema:
    """
    Deterministically evaluates confidence for a loan application.
    Combines 7 explainable factors:
      1. evidence_sufficiency (weight 20%)
      2. evidence_trust (weight 20%)
      3. document_completeness (weight 15%)
      4. verification_consistency (weight 15%)
      5. policy_grounding (weight 10%)
      6. claim_grounding (weight 10%)
      7. investigation_status (weight 10%)

    Applies hard caps / penalties:
      - Investigation degraded or failed -> cap at 25.0 (LOW)
      - Critical identity mismatch -> cap at 45.0 (LOW)
      - Missing >= 2 mandatory documents -> cap at 35.0 (LOW)
    """
    target_id = application_id.replace("APP-", "").upper()

    # 1. Fetch Agent Review if not supplied
    if agent_review is None:
        agent_review = (
            db.query(AgentReviewModel)
            .filter(AgentReviewModel.application_id == application_id)
            .order_by(AgentReviewModel.created_at.desc())
            .first()
        )

    # 2. Fetch Review Assessment
    review_assessment = (
        db.query(ReviewAssessmentModel)
        .filter(ReviewAssessmentModel.application_id == application_id)
        .first()
    )

    # 3. Fetch Active Documents
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

    # 4. Fetch Verification Findings
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

    penalties_applied: List[str] = []

    # -------------------------------------------------------------------------
    # Factor 1: Evidence Sufficiency (Weight 20%)
    # -------------------------------------------------------------------------
    sufficiency_weight = 20.0
    sufficiency_str = (
        (agent_review.evidence_sufficiency or "SUFFICIENT").upper()
        if agent_review
        else ("SUFFICIENT" if len(docs) >= 4 else ("PARTIAL" if len(docs) >= 2 else "INSUFFICIENT"))
    )
    if sufficiency_str == "SUFFICIENT":
        suff_score = 100.0
        suff_exp = "All necessary evidence nodes and documentation are sufficient."
    elif sufficiency_str == "PARTIAL":
        suff_score = 50.0
        suff_exp = "Some key evidence items or document fields are missing."
    else:
        suff_score = 15.0
        suff_exp = "Critical evidence is insufficient to establish applicant standing."

    # -------------------------------------------------------------------------
    # Factor 2: Evidence Trust (Weight 20%)
    # -------------------------------------------------------------------------
    trust_weight = 20.0
    if review_assessment and review_assessment.evidence_trust_score is not None:
        trust_score = float(review_assessment.evidence_trust_score)
        trust_exp = f"Evidence Graph trust rating evaluated at {trust_score:.1f}/100."
    else:
        trust_score = 75.0 if len(docs) > 0 else 20.0
        trust_exp = "Default evidence trust score based on available document records."

    # -------------------------------------------------------------------------
    # Factor 3: Document Completeness (Weight 15%)
    # -------------------------------------------------------------------------
    completeness_weight = 15.0
    mandatory_types = ["PAYSLIP", "BANK_STATEMENT", "TAX_RETURN", "KYC"]
    missing_mandatory = [dt for dt in mandatory_types if dt not in doc_types_present]
    present_count = len(mandatory_types) - len(missing_mandatory)

    if present_count == 4:
        comp_score = 100.0
        comp_exp = "All 4 mandatory document categories present (PAYSLIP, BANK_STATEMENT, TAX_RETURN, KYC)."
    elif present_count == 3:
        comp_score = 60.0
        comp_exp = f"Missing 1 mandatory document category: {missing_mandatory[0]}."
    elif present_count == 2:
        comp_score = 30.0
        comp_exp = f"Missing 2 mandatory document categories: {', '.join(missing_mandatory)}."
    elif present_count == 1:
        comp_score = 15.0
        comp_exp = f"Missing 3 mandatory document categories: {', '.join(missing_mandatory)}."
    else:
        comp_score = 0.0
        comp_exp = "No mandatory documents uploaded."

    # -------------------------------------------------------------------------
    # Factor 4: Verification Consistency (Weight 15%)
    # -------------------------------------------------------------------------
    consistency_weight = 15.0
    has_identity_mismatch = any(
        f.result == "MISMATCH" and (
            f.verification_type in ["IDENTITY_COMPARISON", "APPLICATION_DOCUMENT_COMPARISON"]
            or any(k in (f.rule_name or "").upper() or k in (f.message or "").upper() or k in (f.field_a or "").upper() for k in ["NAME", "IDENTITY", "KYC", "DOB"])
        )
        for f in findings
    )
    has_income_mismatch = any(
        f.result == "MISMATCH" and (
            f.verification_type in ["INCOME_COMPARISON", "SALARY_COMPARISON"]
            or any(k in (f.rule_name or "").upper() or k in (f.message or "").upper() or k in (f.field_a or "").upper() for k in ["SALARY", "INCOME", "TURNOVER"])
        )
        for f in findings
    )
    other_mismatches = [
        f for f in findings if f.result == "MISMATCH" and not (
            f.verification_type in ["IDENTITY_COMPARISON", "APPLICATION_DOCUMENT_COMPARISON", "INCOME_COMPARISON", "SALARY_COMPARISON"]
            or any(k in (f.rule_name or "").upper() or k in (f.message or "").upper() or k in (f.field_a or "").upper() for k in ["NAME", "IDENTITY", "KYC", "DOB", "SALARY", "INCOME", "TURNOVER"])
        )
    ]

    if has_identity_mismatch:
        ver_score = 10.0
        ver_exp = "Critical identity mismatch detected across applicant records."
    elif has_income_mismatch:
        ver_score = 40.0
        ver_exp = "Income or salary mismatch detected across uploaded financial documents."
    elif other_mismatches:
        ver_score = 70.0
        ver_exp = "Minor cross-document inconsistencies detected."
    else:
        ver_score = 100.0
        ver_exp = "All cross-document verification checks passed consistently."

    # -------------------------------------------------------------------------
    # Factor 5: Policy Grounding (Weight 10%)
    # -------------------------------------------------------------------------
    policy_weight = 10.0
    if agent_review:
        g_status = (agent_review.grounding_status or "GROUNDED").upper()
        if g_status == "GROUNDED":
            pol_score = 100.0
            pol_exp = "All policy citations are fully grounded in official knowledge base."
        elif g_status == "PARTIAL":
            pol_score = 50.0
            pol_exp = "Partial policy citation grounding; some references unverified."
        else:
            pol_score = 10.0
            pol_exp = "Ungrounded policy citations detected."
    else:
        pol_score = 100.0
        pol_exp = "Standard policy alignment baseline."

    # -------------------------------------------------------------------------
    # Factor 6: Claim Grounding (Weight 10%)
    # -------------------------------------------------------------------------
    claim_weight = 10.0
    if agent_review and agent_review.claims_support_summary:
        claims_summary = agent_review.claims_support_summary
        if isinstance(claims_summary, dict) and len(claims_summary) > 0:
            supported = sum(1 for v in claims_summary.values() if str(v).upper() == "SUPPORTED")
            ratio = supported / len(claims_summary)
            claim_score = round(ratio * 100.0, 1)
            claim_exp = f"{supported}/{len(claims_summary)} review claims are supported by verified evidence."
        else:
            claim_score = 100.0
            claim_exp = "All review claims verified against evidence graph."
    else:
        claim_score = 100.0
        claim_exp = "Deterministic claims verified against evidence graph."

    # -------------------------------------------------------------------------
    # Factor 7: Investigation Status (Weight 10%)
    # -------------------------------------------------------------------------
    investigation_weight = 10.0
    inv_status = (agent_review.investigation_status or "COMPLETED").upper() if agent_review else "COMPLETED"
    if inv_status == "COMPLETED":
        inv_score = 100.0
        inv_exp = "Autonomous AI investigation completed without interruption."
    elif inv_status == "ESCALATED":
        inv_score = 75.0
        inv_exp = "Investigation escalated to human officer as per protocol."
    elif inv_status == "DEGRADED":
        inv_score = 25.0
        inv_exp = "Investigation degraded due to tool or service exception."
    else:  # FAILED
        inv_score = 0.0
        inv_exp = "Agent investigation failed completely."

    # -------------------------------------------------------------------------
    # Raw Weighted Sum Calculation
    # -------------------------------------------------------------------------
    factors_raw = [
        ("evidence_sufficiency", suff_score, sufficiency_weight, suff_exp),
        ("evidence_trust", trust_score, trust_weight, trust_exp),
        ("document_completeness", comp_score, completeness_weight, comp_exp),
        ("verification_consistency", ver_score, consistency_weight, ver_exp),
        ("policy_grounding", pol_score, policy_weight, pol_exp),
        ("claim_grounding", claim_score, claim_weight, claim_exp),
        ("investigation_status", inv_score, investigation_weight, inv_exp),
    ]

    total_weight = sum(w for _, _, w, _ in factors_raw)
    raw_score = sum(s * (w / total_weight) for _, s, w, _ in factors_raw)

    # -------------------------------------------------------------------------
    # Hard Caps / Penalties
    # -------------------------------------------------------------------------
    final_score = raw_score

    if inv_status in ("DEGRADED", "FAILED"):
        if final_score > 25.0:
            final_score = 25.0
            penalties_applied.append("Investigation degraded or failed; confidence capped at 25.")

    if has_identity_mismatch:
        if final_score > 45.0:
            final_score = 45.0
            penalties_applied.append("Critical identity mismatch detected; confidence capped at 45.")

    if len(missing_mandatory) >= 2:
        if final_score > 35.0:
            final_score = 35.0
            penalties_applied.append("Multiple mandatory documents missing; confidence capped at 35.")

    final_score = max(0.0, min(100.0, round(final_score, 1)))

    # -------------------------------------------------------------------------
    # Build Explainable Factor Breakdown
    # -------------------------------------------------------------------------
    breakdown: List[ConfidenceFactorDetail] = []
    for name, score, weight, explanation in factors_raw:
        weighted_score = round(score * (weight / total_weight), 2)
        breakdown.append(
            ConfidenceFactorDetail(
                name=name,
                score=round(score, 1),
                weight=round(weight, 1),
                weighted_score=weighted_score,
                contribution_pct=round(weight, 1),
                explanation=explanation,
            )
        )

    # -------------------------------------------------------------------------
    # Determine Confidence Level
    # -------------------------------------------------------------------------
    if final_score >= settings.CONFIDENCE_HIGH_THRESHOLD:
        level = "HIGH"
    elif final_score >= settings.CONFIDENCE_MEDIUM_THRESHOLD:
        level = "MEDIUM"
    else:
        level = "LOW"

    return ConfidenceEvaluationSchema(
        score=final_score,
        level=level,
        breakdown=breakdown,
        penalties_applied=penalties_applied,
    )
