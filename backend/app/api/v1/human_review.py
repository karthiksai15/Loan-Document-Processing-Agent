"""
Human Review & Confidence API — Phase 18 Confidence + Human-in-the-Loop Review

Endpoints:
  POST /api/v1/applications/{application_id}/human-review
  GET  /api/v1/applications/{application_id}/human-review
  POST /api/v1/applications/{application_id}/human-review/acknowledge
  POST /api/v1/applications/{application_id}/human-review/note
  POST /api/v1/applications/{application_id}/human-review/request-documents
  POST /api/v1/applications/{application_id}/human-review/decision
  GET  /api/v1/applications/{application_id}/human-review/audit
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import check_officer_permission
from app.schemas.human_review import (
    HumanReviewGateResponse,
    AcknowledgeReviewRequest,
    OfficerNoteRequest,
    RequestDocumentsRequest,
    HumanDecisionRequest,
    HumanReviewAuditResponse,
    HumanReviewAuditItem,
    OfficerFeedbackRequest,
    OfficerFeedbackItem,
    DecisionHistoryResponse,
)
from app.services import human_review_service

router = APIRouter(prefix="/applications", tags=["Human Review"])


@router.post(
    "/{application_id}/human-review",
    response_model=HumanReviewGateResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate or Refresh Human Review Gate",
    description=(
        "Deterministically evaluates the Human Review Gate and confidence for a loan application. "
        "Flags identity mismatches, salary discrepancies, missing mandatory documents, low confidence, "
        "and degraded investigations."
    ),
)
def evaluate_human_review_endpoint(
    application_id: str,
    db: Session = Depends(get_db),
    current_officer=Depends(check_officer_permission),
):
    try:
        record = human_review_service.evaluate_human_review_gate(
            application_id=application_id,
            db=db,
            force_rebuild=True,
        )
        return human_review_service.format_gate_response(record)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Human review evaluation failed: {str(e)}",
        )


@router.get(
    "/{application_id}/human-review",
    response_model=HumanReviewGateResponse,
    summary="Get Human Review State",
    description="Retrieves current Human Review Gate status, confidence breakdown, officer notes, and decision.",
)
def get_human_review_endpoint(
    application_id: str,
    db: Session = Depends(get_db),
    current_officer=Depends(check_officer_permission),
):
    try:
        record = human_review_service.get_human_review(application_id=application_id, db=db)
        return human_review_service.format_gate_response(record)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieval of human review failed: {str(e)}",
        )


@router.post(
    "/{application_id}/human-review/acknowledge",
    response_model=HumanReviewGateResponse,
    summary="Acknowledge Review",
    description="Transitions an application from REQUIRED review to IN_REVIEW status.",
)
def acknowledge_review_endpoint(
    application_id: str,
    request: AcknowledgeReviewRequest,
    db: Session = Depends(get_db),
    current_officer=Depends(check_officer_permission),
):
    try:
        officer_id = (current_officer.id if current_officer else None) or request.officer_id
        record = human_review_service.acknowledge_review(
            application_id=application_id,
            officer_id=officer_id,
            db=db,
        )
        return human_review_service.format_gate_response(record)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Review acknowledgement failed: {str(e)}",
        )


@router.post(
    "/{application_id}/human-review/note",
    response_model=HumanReviewGateResponse,
    summary="Add Officer Note",
    description="Appends a timestamped note from the loan officer to the application review record.",
)
def add_officer_note_endpoint(
    application_id: str,
    request: OfficerNoteRequest,
    db: Session = Depends(get_db),
    current_officer=Depends(check_officer_permission),
):
    try:
        officer_id = (current_officer.id if current_officer else None) or request.officer_id
        record = human_review_service.add_officer_note(
            application_id=application_id,
            note_text=request.note,
            officer_id=officer_id,
            db=db,
        )
        return human_review_service.format_gate_response(record)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Adding officer note failed: {str(e)}",
        )


@router.post(
    "/{application_id}/human-review/request-documents",
    response_model=HumanReviewGateResponse,
    summary="Request Additional Documents",
    description="Requests specific document follow-ups from the applicant.",
)
def request_documents_endpoint(
    application_id: str,
    request: RequestDocumentsRequest,
    db: Session = Depends(get_db),
    current_officer=Depends(check_officer_permission),
):
    try:
        officer_id = (current_officer.id if current_officer else None) or request.officer_id
        record = human_review_service.request_documents(
            application_id=application_id,
            documents=request.documents,
            reason=request.reason,
            officer_id=officer_id,
            db=db,
        )
        return human_review_service.format_gate_response(record)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Requesting documents failed: {str(e)}",
        )


@router.post(
    "/{application_id}/human-review/decision",
    response_model=HumanReviewGateResponse,
    summary="Record Final Human Decision",
    description=(
        "Records the final human decision (APPROVED, REJECTED, OFFICER_INVESTIGATION, DOCUMENT_FOLLOWUP, ESCALATED). "
        "Strictly requires override_reason if human decision deviates from AI recommendation."
    ),
)
def record_human_decision_endpoint(
    application_id: str,
    request: HumanDecisionRequest,
    db: Session = Depends(get_db),
    current_officer=Depends(check_officer_permission),
):
    try:
        officer_id = (current_officer.id if current_officer else None) or request.officer_id
        record = human_review_service.record_human_decision(
            application_id=application_id,
            decision=request.decision,
            officer_id=officer_id,
            db=db,
            override_reason=request.override_reason,
            notes=request.notes,
            decision_reason=request.decision_reason,
        )
        return human_review_service.format_gate_response(record)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recording human decision failed: {str(e)}",
        )


@router.get(
    "/{application_id}/human-review/audit",
    response_model=HumanReviewAuditResponse,
    summary="Get Human Review Audit Trail",
    description="Returns the complete chronological audit log for the application's review process.",
)
def get_human_review_audit_endpoint(
    application_id: str,
    db: Session = Depends(get_db),
    current_officer=Depends(check_officer_permission),
):
    try:
        events = human_review_service.get_audit_trail(application_id=application_id, db=db)
        items = [
            HumanReviewAuditItem(
                audit_id=ev.audit_id,
                application_id=ev.application_id,
                action=ev.action,
                previous_status=ev.previous_status,
                new_status=ev.new_status,
                actor_type=ev.actor_type,
                actor_id=ev.actor_id,
                note=ev.note,
                details=ev.details,
                timestamp=ev.timestamp.isoformat() if ev.timestamp else "",
            )
            for ev in events
        ]
        return HumanReviewAuditResponse(
            application_id=application_id,
            total_events=len(items),
            events=items,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audit trail retrieval failed: {str(e)}",
        )


@router.post(
    "/{application_id}/feedback",
    response_model=OfficerFeedbackItem,
    summary="Submit Officer Feedback",
    description="Records loan officer feedback and evaluation on the review or AI analysis.",
)
@router.post(
    "/{application_id}/human-review/feedback",
    response_model=OfficerFeedbackItem,
    include_in_schema=False,
)
def add_feedback_endpoint(
    application_id: str,
    request: OfficerFeedbackRequest,
    db: Session = Depends(get_db),
    current_officer=Depends(check_officer_permission),
):
    try:
        officer_id = (current_officer.id if current_officer else None) or request.officer_id
        fb_dict = human_review_service.add_officer_feedback(
            application_id=application_id,
            officer_id=officer_id,
            feedback_text=request.feedback,
            category=request.category,
            db=db,
        )
        return OfficerFeedbackItem(**fb_dict)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Adding officer feedback failed: {str(e)}",
        )


@router.get(
    "/{application_id}/decision-history",
    response_model=DecisionHistoryResponse,
    summary="Get Decision History",
    description="Retrieves the application's AI recommendation, human decision, alignment status, feedback, and audit history.",
)
@router.get(
    "/{application_id}/human-review/decision-history",
    response_model=DecisionHistoryResponse,
    include_in_schema=False,
)
def get_decision_history_endpoint(
    application_id: str,
    db: Session = Depends(get_db),
    current_officer=Depends(check_officer_permission),
):
    try:
        res = human_review_service.get_decision_history(application_id=application_id, db=db)
        return DecisionHistoryResponse(**res)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieving decision history failed: {str(e)}",
        )
