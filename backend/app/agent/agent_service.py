"""
Agent Service — Phase 16 & 17 Hardening

Orchestrates a full AI Loan Review Agent investigation:
  1. Validate application exists and input format
  2. Build initial LangGraph state with Phase 17 safety tracking
  3. Run the compiled agent graph with partial investigation preservation
  4. Extract final review from state
  5. Persist AgentReviewModel
  6. Return AgentReviewResponse

Also provides retrieval (get_agent_review) and trace (get_agent_trace).
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.db.models import LoanApplicationModel, AgentReviewModel
from app.providers.base_llm_provider import BaseLLMProvider
from app.services.llm_service import get_llm_provider_for_review
from app.agent.graph import build_agent_graph, build_safe_fallback_review
from app.agent.state import AgentState
from app.services.llm_safety_service import log_security_event


# ── Response builder helpers ──────────────────────────────────────────────────

def _model_to_response(obj: AgentReviewModel) -> dict:
    """Convert AgentReviewModel to a response dict."""
    final_review = {}
    if obj.executive_summary:
        final_review = {
            "executive_summary": obj.executive_summary,
            "key_findings": obj.key_findings or [],
            "evidence_references": obj.evidence_references or [],
            "policy_references": obj.policy_references or [],
            "risk_interpretation": obj.risk_interpretation or "",
            "review_interpretation": obj.review_interpretation or "",
            "unresolved_questions": obj.unresolved_questions or [],
            "recommended_next_step": obj.recommended_next_step,
            "confidence": obj.confidence,
            "confidence_level": obj.confidence_level,
            "limitations": obj.limitations or [],
            "grounding_status": obj.grounding_status,
            "evidence_sufficiency": obj.evidence_sufficiency or "SUFFICIENT",
            "claims_support_summary": obj.claims_support_summary or {},
        }

    return {
        "agent_review_id": obj.agent_review_id,
        "application_id": obj.application_id,
        "agent_version": obj.agent_version,
        "instruction_version": obj.instruction_version,
        "investigation_status": obj.investigation_status,
        "step_count": obj.step_count,
        "tools_used": obj.tools_used or [],
        "retries_count": obj.retries_count or 0,
        "escalation_required": bool(obj.escalation_required),
        "escalation_reason": obj.escalation_reason,
        "injection_check_status": obj.injection_check_status,
        "grounding_status": obj.grounding_status,
        "evidence_sufficiency": obj.evidence_sufficiency or "SUFFICIENT",
        "confidence": obj.confidence if obj.confidence is not None else 0.0,
        "confidence_level": obj.confidence_level or "LOW",
        "final_review": final_review,
        "investigation_steps": obj.investigation_steps or [],
        "created_at": obj.created_at.isoformat() if obj.created_at else None,
        "completed_at": obj.completed_at.isoformat() if obj.completed_at else None,
    }


# ── Persistence ───────────────────────────────────────────────────────────────

def _persist_agent_review(
    db: Session,
    application_id: str,
    final_state: AgentState,
) -> AgentReviewModel:
    """Persists the AgentState result into AgentReviewModel."""
    review_id = f"AGT-{application_id}-{uuid.uuid4().hex[:8].upper()}"

    final_review = final_state.get("final_review") or {}
    investigation_steps = final_state.get("investigation_steps", [])
    tools_used = final_state.get("tools_used", [])
    step_count = final_state.get("step_count", 0)
    retries_count = final_state.get("retries_count", 0)
    escalation = bool(final_state.get("escalation_required", False))
    escalation_reason = final_state.get("escalation_reason")
    injection_status = final_state.get("injection_check_status", "CLEAN")
    evidence_sufficiency = final_state.get("evidence_sufficiency", "SUFFICIENT")
    claims_support_summary = final_state.get("claims_support_summary", {})

    grounding_status = final_review.get("grounding_status", "GROUNDED")

    # Determine investigation status
    inv_status = final_state.get("investigation_status")
    if not inv_status:
        if not final_review.get("executive_summary"):
            inv_status = "FAILED"
        elif escalation:
            inv_status = "ESCALATED"
        elif evidence_sufficiency == "INSUFFICIENT":
            inv_status = "DEGRADED"
        else:
            inv_status = "COMPLETED"

    # Enforce final decision boundary
    ALLOWED = {"STANDARD_REVIEW", "OFFICER_INVESTIGATION", "DOCUMENT_FOLLOWUP", "ESCALATE"}
    recommended = final_review.get("recommended_next_step", "OFFICER_INVESTIGATION")
    if recommended not in ALLOWED:
        recommended = "OFFICER_INVESTIGATION"

    obj = AgentReviewModel(
        agent_review_id=review_id,
        application_id=application_id,
        agent_version=final_state.get("agent_version", settings.AGENT_VERSION),
        instruction_version=final_state.get("instruction_version", settings.AGENT_INSTRUCTION_VERSION),
        investigation_status=inv_status,
        step_count=step_count,
        tools_used=tools_used,
        retries_count=retries_count,
        investigation_steps=list(investigation_steps),
        executive_summary=final_review.get("executive_summary", "Review generation failed."),
        key_findings=final_review.get("key_findings", []),
        evidence_references=final_review.get("evidence_references", []),
        policy_references=final_review.get("policy_references", []),
        risk_interpretation=final_review.get("risk_interpretation", ""),
        review_interpretation=final_review.get("review_interpretation", ""),
        unresolved_questions=final_review.get("unresolved_questions", []),
        recommended_next_step=recommended,
        confidence=final_review.get("confidence", final_state.get("confidence", 0.0)),
        confidence_level=final_review.get("confidence_level", final_state.get("confidence_level", "LOW")),
        limitations=final_review.get("limitations", []),
        escalation_required=int(escalation),
        escalation_reason=escalation_reason,
        grounding_status=grounding_status,
        injection_check_status=injection_status,
        evidence_sufficiency=evidence_sufficiency,
        claims_support_summary=claims_support_summary,
        created_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# ── Main orchestrator ─────────────────────────────────────────────────────────

def run_agent_review(
    db: Session,
    application_id: str,
    force_rebuild: bool = False,
    provider_override: Optional[BaseLLMProvider] = None,
) -> dict:
    """
    Full AI Review Agent pipeline for an application.

    Args:
        db:                SQLAlchemy session.
        application_id:    Target application ID.
        force_rebuild:     If True, re-run even if a cached result exists.
        provider_override: Inject a specific provider (e.g. FakeLLMProvider for tests).

    Returns:
        Response dict (see _model_to_response).
    """
    # 1. Validate application ID format
    if not application_id or not isinstance(application_id, str):
        raise ValueError("Application ID must be a non-empty string.")

    # 2. Validate application exists in database
    app_obj = db.query(LoanApplicationModel).filter(
        LoanApplicationModel.application_id == application_id
    ).first()
    if not app_obj:
        raise ValueError(f"Application '{application_id}' not found.")

    # 3. Return cached result unless force_rebuild
    if not force_rebuild:
        cached = (
            db.query(AgentReviewModel)
            .filter(AgentReviewModel.application_id == application_id)
            .order_by(AgentReviewModel.created_at.desc())
            .first()
        )
        if cached:
            logger.info(f"AgentService: Returning cached review '{cached.agent_review_id}' for '{application_id}'.")
            return _model_to_response(cached)

    # 4. Get active provider
    provider = provider_override or get_llm_provider_for_review()

    # 5. Build initial isolated state
    initial_state: AgentState = {
        "application_id": application_id,
        "agent_version": settings.AGENT_VERSION,
        "instruction_version": settings.AGENT_INSTRUCTION_VERSION,
        "initial_context": {},
        "injection_check_status": "CLEAN",
        "security_flags": [],
        "current_findings": [],
        "evidence_references": [],
        "policy_references": [],
        "risk_information": {},
        "review_information": {},
        "investigation_steps": [],
        "tools_used": [],
        "tool_call_history": [],
        "unresolved_questions": [],
        "current_reasoning_summary": "",
        "confidence": 0.5,
        "confidence_level": "MEDIUM",
        "evidence_sufficiency": "SUFFICIENT",
        "claims_support_summary": {},
        "escalation_required": False,
        "escalation_reason": None,
        "investigation_status": "COMPLETED",
        "llm_unavailable": False,
        "final_review": None,
        "step_count": 0,
        "retries_count": 0,
        "next_tool": None,
        "next_tool_query": None,
        "sufficient_evidence": False,
        "needs_more_investigation": True,
        "investigation_complete": False,
    }

    # 6. Run agent graph with safe fallback handling
    try:
        compiled = build_agent_graph(db, provider)
        final_state = compiled.invoke(initial_state)
    except Exception as e:
        logger.error(f"AgentService: Graph execution failed for '{application_id}': {e}")
        log_security_event("GRAPH_EXECUTION_FAILURE", {"application_id": application_id, "error": str(e)})

        fallback_review = build_safe_fallback_review(initial_state, db, f"Execution failed: {e}")
        final_state = {
            **initial_state,
            "final_review": fallback_review,
            "escalation_required": True,
            "escalation_reason": f"Agent graph execution failed: {e}",
            "investigation_status": "DEGRADED",
            "confidence": 0.0,
            "confidence_level": "LOW",
            "evidence_sufficiency": fallback_review.get("evidence_sufficiency", "PARTIAL"),
            "claims_support_summary": fallback_review.get("claims_support_summary", {}),
        }

    obj = _persist_agent_review(db, application_id, final_state)
    logger.info(
        f"AgentService: Completed review '{obj.agent_review_id}' for '{application_id}' "
        f"[status={obj.investigation_status}, steps={obj.step_count}]"
    )
    return _model_to_response(obj)


def get_agent_review(db: Session, application_id: str) -> Optional[dict]:
    """Get the most recent agent review for an application. Returns None if none exist."""
    app_obj = db.query(LoanApplicationModel).filter(
        LoanApplicationModel.application_id == application_id
    ).first()
    if not app_obj:
        raise ValueError(f"Application '{application_id}' not found.")

    obj = (
        db.query(AgentReviewModel)
        .filter(AgentReviewModel.application_id == application_id)
        .order_by(AgentReviewModel.created_at.desc())
        .first()
    )
    return _model_to_response(obj) if obj else None


def get_agent_trace(db: Session, application_id: str) -> Optional[dict]:
    """Get the investigation trace for the most recent agent review."""
    review = get_agent_review(db, application_id)
    if not review:
        return None

    return {
        "agent_review_id": review["agent_review_id"],
        "application_id": review["application_id"],
        "agent_version": review["agent_version"],
        "instruction_version": review["instruction_version"],
        "investigation_status": review["investigation_status"],
        "step_count": review["step_count"],
        "tools_used": review["tools_used"],
        "retries_count": review.get("retries_count", 0),
        "escalation_required": review["escalation_required"],
        "escalation_reason": review["escalation_reason"],
        "investigation_steps": review["investigation_steps"],
        "created_at": review["created_at"],
        "completed_at": review["completed_at"],
    }
