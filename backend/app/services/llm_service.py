"""
LLM Service — Phase 15 LLM Service

Orchestrates the LLM review pipeline:
  1. Build structured review context (Phase 3–14 data)
  2. Strict system prompt with banking decision-support constraints
  3. Call LLM provider (Groq by default, or injected mock for tests)
  4. Parse and validate structured output (Phase 15 Section 15 schema)
  5. Ground evidence & policy citations
  6. Return structured LLMReviewResponse
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.db.models import LoanApplicationModel, LLMReviewModel
from app.schemas.llm import (
    LLMReviewResult,
    LLMReviewResponse,
    LLMReviewRequest,
    LLMDirectReviewRequest,
    KeyFinding,
    DocumentPresence,
    RiskAssessment,
    PolicyBasis,
)
from app.providers.base_llm_provider import BaseLLMProvider, LLMProviderUnavailableException
from app.providers.groq_provider import GroqProvider, GroqProviderUnavailableException
from app.providers.gemini_provider import GeminiProvider, GeminiProviderUnavailableException
from app.services.llm_prompts import LOAN_REVIEW_SYSTEM_PROMPT, format_direct_review_prompt
from app.services.llm_context_service import build_llm_context, build_llm_prompt
from app.services.llm_grounding_service import (
    validate_evidence_citations,
    validate_policy_citations,
    compute_grounding_status,
)


# ── Provider Factory ─────────────────────────────────────────────────────────

def get_llm_provider_for_review(
    provider_override: Optional[BaseLLMProvider] = None,
) -> BaseLLMProvider:
    """
    Returns the active LLM provider for Phase 15 review.

    Priority:
      1. Explicit provider_override (used by tests with FakeLLMProvider)
      2. Configured provider from settings.LLM_PROVIDER:
         - "gemini": GeminiProvider (default)
         - "groq": GroqProvider
         - "grok": GrokProvider
    """
    if provider_override is not None:
        return provider_override

    provider_name = (settings.LLM_PROVIDER or "gemini").lower()
    if provider_name == "gemini":
        return GeminiProvider()
    elif provider_name == "groq":
        return GroqProvider()
    elif provider_name == "grok":
        from app.providers.grok_provider import GrokProvider
        return GrokProvider()

    return GeminiProvider()


# ── Output Parser & Validator ────────────────────────────────────────────────

def _parse_llm_output(raw: str) -> Optional[Dict[str, Any]]:
    """
    Parses the LLM's raw string output into a structured dict.
    Handles JSON wrapped in markdown fences (```json ... ```) gracefully.
    """
    text = raw.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        inner = lines[1:] if lines[0].startswith("```") else lines
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        text = "\n".join(inner).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"LLMService: Failed to parse LLM JSON output: {e}\nRaw snippet: {raw[:300]}")
        return None


def _validate_structured_output(parsed: Dict[str, Any]) -> Optional[LLMReviewResult]:
    """
    Validates parsed dict against the LLMReviewResult Pydantic schema.
    Returns None if validation fails.
    """
    try:
        return LLMReviewResult(**parsed)
    except Exception as e:
        logger.error(f"LLMService: Structured output schema validation failed: {e}")
        return None


# ── Fallback Builder ─────────────────────────────────────────────────────────

def _build_fallback_review(application_id: str, error_reason: str) -> LLMReviewResult:
    """Returns a safe fallback review when the LLM fails or output is invalid."""
    return LLMReviewResult(
        summary=f"LLM review could not be generated: {error_reason}. Please review manually.",
        application_status="UNDER_REVIEW",
        documents=DocumentPresence(present=[], missing=[]),
        key_findings=[
            KeyFinding(
                issue="LLM review generation failed — manual review required.",
                severity="WARNING",
                evidence=[]
            )
        ],
        risk_assessment=RiskAssessment(),
        policy_basis=[],
        missing_information=[],
        investigation_points=["Manual verification required due to LLM generation failure."],
        recommended_next_action="OFFICER_INVESTIGATION",
        confidence=0.0,
        executive_summary=f"LLM review could not be generated: {error_reason}. Please review manually.",
        recommended_action="OFFICER_INVESTIGATION",
        confidence_level="LOW",
        risk_interpretation="LLM risk interpretation unavailable.",
        limitations=["LLM review generation failed.", error_reason],
    )


# ── Persistence & Response Conversion ───────────────────────────────────────

def _persist_review(
    db: Session,
    application_id: str,
    provider: BaseLLMProvider,
    result: LLMReviewResult,
    raw_output: str,
    grounding_status: str,
    injection_check_status: str,
) -> LLMReviewModel:
    """Creates or replaces the LLMReviewModel row for the application."""
    review_id = f"LLM-{application_id}-{uuid.uuid4().hex[:8].upper()}"

    # Extract clean list of key_findings for DB storage
    key_findings_data = [
        kf.model_dump() if hasattr(kf, "model_dump") else (
            {"issue": kf, "severity": "INFO", "evidence": []} if isinstance(kf, str) else kf
        )
        for kf in result.key_findings
    ]

    conf_num = float(result.confidence) if isinstance(result.confidence, (int, float)) else 0.0

    review_obj = LLMReviewModel(
        review_id=review_id,
        application_id=application_id,
        llm_provider=provider.name(),
        llm_model=provider.name(),
        executive_summary=result.summary or result.executive_summary or "",
        key_findings=key_findings_data,
        evidence_references=[e.model_dump() if hasattr(e, "model_dump") else e for e in result.evidence_references],
        policy_references=[p.model_dump() if hasattr(p, "model_dump") else p for p in result.policy_references],
        risk_interpretation=result.risk_interpretation or (
            f"Historical rejection-risk indicator: {result.risk_assessment.ml_level} ({result.risk_assessment.ml_probability})"
            if result.risk_assessment and result.risk_assessment.ml_level else "Historical risk analysis computed."
        ),
        recommended_action=result.recommended_next_action or result.recommended_action or "OFFICER_INVESTIGATION",
        confidence=conf_num,
        confidence_level=result.confidence_level or "MEDIUM",
        limitations=list(result.limitations),
        grounding_status=grounding_status,
        injection_check_status=injection_check_status,
        raw_llm_output=raw_output[:10000] if raw_output else None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(review_obj)
    db.commit()
    db.refresh(review_obj)
    return review_obj


def _model_to_response(review_obj: LLMReviewModel) -> LLMReviewResponse:
    raw_findings = review_obj.key_findings or []
    norm_findings = []
    for f in raw_findings:
        if isinstance(f, dict):
            norm_findings.append(f)
        elif isinstance(f, str):
            norm_findings.append({"issue": f, "severity": "INFO", "evidence": []})
        else:
            norm_findings.append({"issue": str(f), "severity": "INFO", "evidence": []})

    summary_text = review_obj.executive_summary

    parsed_raw = _parse_llm_output(review_obj.raw_llm_output) if review_obj.raw_llm_output else {}
    if not isinstance(parsed_raw, dict):
        parsed_raw = {}

    docs_data = parsed_raw.get("documents") if isinstance(parsed_raw.get("documents"), dict) else {"present": [], "missing": []}
    risk_data = parsed_raw.get("risk_assessment") if isinstance(parsed_raw.get("risk_assessment"), dict) else {
        "ml_probability": None,
        "ml_level": None,
        "evidence_quality": None,
        "review_priority_score": None,
        "review_priority_level": None,
    }
    policy_basis_data = parsed_raw.get("policy_basis") if isinstance(parsed_raw.get("policy_basis"), list) else []
    missing_info = parsed_raw.get("missing_information") if isinstance(parsed_raw.get("missing_information"), list) else []
    investigation_pts = parsed_raw.get("investigation_points") if isinstance(parsed_raw.get("investigation_points"), list) else []
    app_status = parsed_raw.get("application_status", "UNDER_REVIEW")

    return LLMReviewResponse(
        review_id=review_obj.review_id,
        application_id=review_obj.application_id,
        llm_provider=review_obj.llm_provider,
        llm_model=review_obj.llm_model,
        summary=summary_text,
        application_status=app_status,
        documents=docs_data,
        key_findings=norm_findings,
        risk_assessment=risk_data,
        policy_basis=policy_basis_data,
        missing_information=missing_info,
        investigation_points=investigation_pts,
        recommended_next_action=review_obj.recommended_action,
        confidence=review_obj.confidence,
        executive_summary=summary_text,
        recommended_action=review_obj.recommended_action,
        confidence_level=review_obj.confidence_level,
        risk_interpretation=review_obj.risk_interpretation,
        limitations=review_obj.limitations or [],
        evidence_references=review_obj.evidence_references or [],
        policy_references=review_obj.policy_references or [],
        grounding_status=review_obj.grounding_status,
        injection_check_status=review_obj.injection_check_status,
        created_at=review_obj.created_at,
        updated_at=review_obj.updated_at,
    )


def _result_to_direct_response(
    application_id: str,
    provider: BaseLLMProvider,
    result: LLMReviewResult,
    raw_output: str,
    grounding_status: str,
    injection_check_status: str,
) -> LLMReviewResponse:
    review_id = f"LLM-{application_id}-{uuid.uuid4().hex[:8].upper()}"
    return LLMReviewResponse(
        review_id=review_id,
        application_id=application_id,
        llm_provider=provider.name(),
        llm_model=provider.name(),
        summary=result.summary,
        application_status=result.application_status,
        documents=result.documents.model_dump(),
        key_findings=[kf.model_dump() if hasattr(kf, "model_dump") else kf for kf in result.key_findings],
        risk_assessment=result.risk_assessment.model_dump(),
        policy_basis=[pb.model_dump() if hasattr(pb, "model_dump") else pb for pb in result.policy_basis],
        missing_information=result.missing_information,
        investigation_points=result.investigation_points,
        recommended_next_action=result.recommended_next_action,
        confidence=result.confidence,
        executive_summary=result.summary,
        recommended_action=result.recommended_next_action,
        confidence_level=result.confidence_level or "MEDIUM",
        risk_interpretation=result.risk_interpretation or "",
        limitations=result.limitations or [],
        evidence_references=[e.model_dump() if hasattr(e, "model_dump") else e for e in result.evidence_references],
        policy_references=[p.model_dump() if hasattr(p, "model_dump") else p for p in result.policy_references],
        grounding_status=grounding_status,
        injection_check_status=injection_check_status,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


# ── Direct Review Pipeline (POST /api/v1/llm/review) ─────────────────────────

def generate_direct_review(
    request: LLMDirectReviewRequest,
    provider_override: Optional[BaseLLMProvider] = None,
    db: Optional[Session] = None,
) -> LLMReviewResponse:
    """
    Direct LLM review generation from structured request context.
    Does not require pre-existing database records.
    Fails gracefully with GroqProviderUnavailableException if Groq API is unconfigured.
    """
    provider = get_llm_provider_for_review(provider_override)

    if hasattr(provider, "is_available") and not provider.is_available():
        if isinstance(provider, GeminiProvider):
            raise GeminiProviderUnavailableException(
                "Gemini API provider is unavailable: GEMINI_API_KEY is not configured in environment or .env file."
            )
        elif isinstance(provider, GroqProvider):
            raise GroqProviderUnavailableException(
                "Groq API provider is unavailable: GROQ_API_KEY is not configured in environment or .env file."
            )
        else:
            raise LLMProviderUnavailableException(
                f"LLM provider '{provider.name()}' is unavailable: API key not configured."
            )

    app_id = request.application_id or "DIRECT"

    user_prompt = format_direct_review_prompt(request)
    system_prompt = LOAN_REVIEW_SYSTEM_PROMPT

    raw_output = ""
    try:
        raw_output = provider.generate(prompt=user_prompt, system_prompt=system_prompt)
    except (LLMProviderUnavailableException, GroqProviderUnavailableException, GeminiProviderUnavailableException):
        raise
    except Exception as e:
        logger.error(f"LLMService direct review call failed: {e}")
        fallback = _build_fallback_review(app_id, f"LLM API error: {e}")
        return _result_to_direct_response(app_id, provider, fallback, raw_output, "UNGROUNDED", "CLEAN")

    parsed = _parse_llm_output(raw_output)
    if parsed is None:
        fallback = _build_fallback_review(app_id, "LLM returned invalid JSON output.")
        return _result_to_direct_response(app_id, provider, fallback, raw_output, "UNGROUNDED", "CLEAN")

    result = _validate_structured_output(parsed)
    if result is None:
        fallback = _build_fallback_review(app_id, "LLM output failed schema validation.")
        return _result_to_direct_response(app_id, provider, fallback, raw_output, "UNGROUNDED", "CLEAN")

    # Final-decision safety rule: LLM must not approve or reject loan
    FORBIDDEN_ACTIONS = {"APPROVED", "REJECTED", "APPROVE", "REJECT"}
    if result.recommended_next_action in FORBIDDEN_ACTIONS or result.recommended_action in FORBIDDEN_ACTIONS:
        logger.warning(
            f"LLM attempted to make final loan decision '{result.recommended_next_action}'. "
            "Enforcing safety override to OFFICER_INVESTIGATION."
        )
        result.recommended_next_action = "OFFICER_INVESTIGATION"
        result.recommended_action = "OFFICER_INVESTIGATION"

    return _result_to_direct_response(app_id, provider, result, raw_output, "GROUNDED", "CLEAN")


# ── Application Review Pipeline (POST /api/v1/applications/{id}/llm/review) ──

def generate_llm_review(
    db: Session,
    application_id: str,
    request: Optional[LLMReviewRequest] = None,
    provider_override: Optional[BaseLLMProvider] = None,
) -> LLMReviewResponse:
    """
    Full LLM review pipeline for an application persisted in the database.
    """
    req = request or LLMReviewRequest()

    # Guard: application must exist first
    app_obj = db.query(LoanApplicationModel).filter(
        LoanApplicationModel.application_id == application_id
    ).first()
    if not app_obj:
        raise ValueError(f"Application '{application_id}' not found.")

    provider = get_llm_provider_for_review(provider_override)

    if hasattr(provider, "is_available") and not provider.is_available():
        if isinstance(provider, GeminiProvider):
            raise GeminiProviderUnavailableException(
                "Gemini API provider is unavailable: GEMINI_API_KEY is not configured in environment or .env file."
            )
        elif isinstance(provider, GroqProvider):
            raise GroqProviderUnavailableException(
                "Groq API provider is unavailable: GROQ_API_KEY is not configured in environment or .env file."
            )
        else:
            raise LLMProviderUnavailableException(
                f"LLM provider '{provider.name()}' is unavailable: API key not configured."
            )

    # ── 1. Return cached result if force_rebuild is False ────────────────────
    if not req.force_rebuild:
        cached = (
            db.query(LLMReviewModel)
            .filter(LLMReviewModel.application_id == application_id)
            .order_by(LLMReviewModel.created_at.desc())
            .first()
        )
        if cached:
            logger.info(f"LLMService: Returning cached review '{cached.review_id}' for '{application_id}'.")
            return _model_to_response(cached)

    # ── 2. Build context ─────────────────────────────────────────────────────
    try:
        context = build_llm_context(db, application_id, max_policy_results=req.max_policy_results)
    except Exception as e:
        logger.error(f"LLMService: Context build failed for '{application_id}': {e}")
        fallback = _build_fallback_review(application_id, f"Context build error: {e}")
        review_obj = _persist_review(db, application_id, provider, fallback, "", "UNGROUNDED", "CLEAN")
        return _model_to_response(review_obj)

    injection_check_status = context["injection_check_status"]

    # ── 3. Build prompt ──────────────────────────────────────────────────────
    system_prompt, user_prompt = build_llm_prompt(context)

    # ── 4. Call LLM ─────────────────────────────────────────────────────────
    raw_output = ""
    try:
        raw_output = provider.generate(prompt=user_prompt, system_prompt=system_prompt)
    except (LLMProviderUnavailableException, GroqProviderUnavailableException, GeminiProviderUnavailableException):
        raise
    except Exception as e:
        logger.error(f"LLMService: LLM call failed for '{application_id}': {e}")
        fallback = _build_fallback_review(application_id, f"LLM API error: {e}")
        review_obj = _persist_review(db, application_id, provider, fallback, "", "GROUNDED", injection_check_status)
        return _model_to_response(review_obj)

    # ── 5. Parse & validate structured output ───────────────────────────────
    parsed = _parse_llm_output(raw_output)
    if parsed is None:
        fallback = _build_fallback_review(application_id, "LLM returned invalid JSON output.")
        review_obj = _persist_review(db, application_id, provider, fallback, raw_output, "UNGROUNDED", injection_check_status)
        return _model_to_response(review_obj)

    result = _validate_structured_output(parsed)
    if result is None:
        fallback = _build_fallback_review(application_id, "LLM output failed schema validation.")
        review_obj = _persist_review(db, application_id, provider, fallback, raw_output, "UNGROUNDED", injection_check_status)
        return _model_to_response(review_obj)

    # Final-decision safety rule
    FORBIDDEN_ACTIONS = {"APPROVED", "REJECTED", "APPROVE", "REJECT"}
    if result.recommended_next_action in FORBIDDEN_ACTIONS or result.recommended_action in FORBIDDEN_ACTIONS:
        result.recommended_next_action = "OFFICER_INVESTIGATION"
        result.recommended_action = "OFFICER_INVESTIGATION"

    # ── 6. Ground citations ──────────────────────────────────────────────────
    cited_evidence_ids = [e.node_id for e in result.evidence_references]
    cited_policy_ids = [p.section_id for p in result.policy_references]

    valid_evidence, invalid_evidence = validate_evidence_citations(application_id, cited_evidence_ids, db)
    valid_policy, invalid_policy = validate_policy_citations(cited_policy_ids, db)

    grounding_status = compute_grounding_status(
        cited_evidence_ids, valid_evidence,
        cited_policy_ids, valid_policy,
    )

    if invalid_evidence:
        result.evidence_references = [e for e in result.evidence_references if e.node_id in valid_evidence]
    if invalid_policy:
        result.policy_references = [p for p in result.policy_references if p.section_id in valid_policy]

    # ── 7. Persist ───────────────────────────────────────────────────────────
    review_obj = _persist_review(
        db, application_id, provider, result, raw_output, grounding_status, injection_check_status
    )
    logger.info(
        f"LLMService: Generated review '{review_obj.review_id}' for '{application_id}' "
        f"[grounding={grounding_status}, injection={injection_check_status}]"
    )
    return _model_to_response(review_obj)


def get_llm_review(db: Session, application_id: str) -> Optional[LLMReviewResponse]:
    """
    Retrieves the most recent LLM review for an application.
    Returns None if no review has been generated yet.
    """
    app_obj = db.query(LoanApplicationModel).filter(
        LoanApplicationModel.application_id == application_id
    ).first()
    if not app_obj:
        raise ValueError(f"Application '{application_id}' not found.")

    review_obj = (
        db.query(LLMReviewModel)
        .filter(LLMReviewModel.application_id == application_id)
        .order_by(LLMReviewModel.created_at.desc())
        .first()
    )
    if not review_obj:
        return None

    return _model_to_response(review_obj)

