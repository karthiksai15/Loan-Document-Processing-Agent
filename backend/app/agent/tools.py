"""
Agent Tools — Phase 16 & 17 Hardening

Six read-only tools available to the AI Loan Review Agent.
All tools return structured dicts. None can modify any data.

Hardened in Phase 17:
  - Strict input validation (application_id format, query length)
  - Cross-applicant data isolation guards
  - Safe error handling (DB exceptions, missing records, unavailable ML/Policy)
  - PII masking and data minimization
  - Security audit logging

Tools:
  1. get_application_context  — application profile + review summary
  2. get_evidence             — Evidence Graph nodes for the application
  3. get_verification_findings — cross-document verification results
  4. get_risk_analysis        — ML risk analysis
  5. get_review_score         — Review Intelligence breakdown
  6. search_policy            — Phase 14 Policy RAG semantic search
"""

import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.models import (
    LoanApplicationModel,
    DocumentModel,
    ExtractedFieldModel,
    ApplicationVerificationModel,
    VerificationFindingModel,
    ReviewAssessmentModel,
    EvidenceNodeModel,
)
from app.services.cross_document_verification_service import get_application_profile_data
from app.ml.predictor import predict_application_risk
from app.services.llm_safety_service import check_for_injection, mask_pii, log_security_event


# ── REGISTRY ─────────────────────────────────────────────────────────────────

ALLOWED_TOOLS = {
    "get_application_context",
    "get_evidence",
    "get_verification_findings",
    "get_risk_analysis",
    "get_review_score",
    "search_policy",
}

_APP_ID_REGEX = re.compile(r"^[A-Za-z0-9\-_]{1,64}$")
_CROSS_APP_DETECT_REGEX = re.compile(r"\b(A0\d{2}|APP-[A-Za-z0-9\-_]+)\b", re.IGNORECASE)


def _validate_application_id(application_id: Any) -> Optional[str]:
    """Validates application_id format."""
    if not isinstance(application_id, str):
        return "Application ID must be a string."
    app_id_clean = application_id.strip()
    if not app_id_clean:
        return "Application ID cannot be empty."
    if not _APP_ID_REGEX.match(app_id_clean):
        return "Invalid application_id format. Must be alphanumeric with hyphens or underscores (max 64 chars)."
    return None


def call_tool(tool_name: str, query: Optional[str], application_id: str, db: Session) -> Dict[str, Any]:
    """
    Dispatcher: validates inputs and calls the named tool.
    Only tools in ALLOWED_TOOLS can be invoked.
    """
    # 1. Tool name validation
    if tool_name not in ALLOWED_TOOLS:
        log_security_event("INVALID_TOOL_REQUEST", {"tool": tool_name, "application_id": application_id})
        return {
            "tool": tool_name,
            "status": "ERROR",
            "error": f"Tool '{tool_name}' is not in the allowed tool set.",
        }

    # 2. Application ID validation
    app_err = _validate_application_id(application_id)
    if app_err:
        log_security_event("INVALID_APP_ID_REQUEST", {"application_id": str(application_id), "error": app_err})
        return {
            "tool": tool_name,
            "status": "ERROR",
            "error": app_err,
        }

    # 3. Cross-applicant isolation check: if query mentions another applicant ID
    if query:
        norm_app = application_id.upper().replace("APP-", "")
        matches = _CROSS_APP_DETECT_REGEX.findall(query)
        for m in matches:
            norm_m = m.upper().replace("APP-", "")
            if norm_m != norm_app and norm_m in [f"A0{i:02d}" for i in range(1, 20)]:
                log_security_event("CROSS_APPLICANT_ACCESS_BLOCKED", {
                    "application_id": application_id,
                    "target_applicant_in_query": m,
                    "tool": tool_name
                })
                return {
                    "tool": tool_name,
                    "status": "ERROR",
                    "error": "Cross-applicant access attempt detected and blocked.",
                }

    try:
        if tool_name == "get_application_context":
            return get_application_context(application_id, db)
        elif tool_name == "get_evidence":
            return get_evidence(application_id, db)
        elif tool_name == "get_verification_findings":
            return get_verification_findings(application_id, db)
        elif tool_name == "get_risk_analysis":
            return get_risk_analysis(application_id, db)
        elif tool_name == "get_review_score":
            return get_review_score(application_id, db)
        elif tool_name == "search_policy":
            return search_policy(query or "loan application review", db)
    except Exception as e:
        logger.error(f"Tool '{tool_name}' failed for '{application_id}': {e}")
        log_security_event("TOOL_EXCEPTION", {"tool": tool_name, "application_id": application_id, "error": str(e)})
        return {
            "tool": tool_name,
            "status": "ERROR",
            "error": str(e),
        }


def format_policy_source_label(
    source: Optional[str] = None,
    is_simulated: Optional[bool] = None,
    policy_id: str = "",
) -> str:
    """
    Formats the canonical display label for policy source:
      - RBI -> RBI (rendered as [RBI])
      - HDFC_BANK + is_simulated=False -> HDFC_BANK (rendered as [HDFC_BANK])
      - HDFC_INTERNAL_DEMO + is_simulated=True -> INTERNAL_DEMO (rendered as [INTERNAL_DEMO])
    Never returns INTERNAL_BANK for HDFC public policies.
    """
    pol_id = (policy_id or "").upper()

    # Look up in knowledge base if source or is_simulated is missing
    if not source or is_simulated is None:
        try:
            from app.services.policy_knowledge_service import PolicyKnowledgeService
            policies = PolicyKnowledgeService.load_policies()
            for p in policies:
                if p.policy_id == policy_id or policy_id.startswith(p.policy_id):
                    source = p.source
                    is_simulated = p.is_simulated
                    break
        except Exception:
            pass

    # Heuristic fallback based on policy ID pattern
    if not source:
        if "HDFC_PUB" in pol_id:
            source = "HDFC_BANK"
            is_simulated = False
        elif "DEMO" in pol_id or "INTERNAL" in pol_id:
            source = "HDFC_INTERNAL_DEMO"
            is_simulated = True
        elif "RBI" in pol_id:
            source = "RBI"
            is_simulated = False

    if source == "HDFC_BANK" and not is_simulated:
        return "HDFC_BANK"
    elif source == "HDFC_INTERNAL_DEMO" or is_simulated:
        return "INTERNAL_DEMO"
    elif source == "RBI":
        return "RBI"

    return source or "UNKNOWN"


# ── TOOL 1: get_application_context ─────────────────────────────────────────

def get_application_context(application_id: str, db: Session) -> Dict[str, Any]:
    """
    Retrieves application profile data and a high-level review summary.
    This is typically the first tool called.
    """
    app_err = _validate_application_id(application_id)
    if app_err:
        return {"tool": "get_application_context", "status": "ERROR", "error": app_err}

    app_obj = db.query(LoanApplicationModel).filter(
        LoanApplicationModel.application_id == application_id
    ).first()
    if not app_obj:
        return {"tool": "get_application_context", "status": "ERROR", "error": f"Application '{application_id}' not found."}

    try:
        profile = get_application_profile_data(db, application_id)
        target_id = application_id.replace("APP-", "").upper()

        docs = db.query(DocumentModel).filter(
            (DocumentModel.application_id == application_id) | (DocumentModel.applicant_id == target_id),
            DocumentModel.processing_status != "DELETED"
        ).all()

        doc_types = list({(d.classified_document_type or d.document_type or "OTHER").upper() for d in docs})
        required_types = {"PAYSLIP", "BANK_STATEMENT", "TAX_RETURN", "KYC"}
        missing_types = list(required_types - set(doc_types))

        review_obj = db.query(ReviewAssessmentModel).filter(
            ReviewAssessmentModel.application_id == application_id
        ).first()

        review_summary = None
        if review_obj:
            review_summary = {
                "review_score": review_obj.review_score,
                "review_priority": review_obj.review_priority,
                "evidence_trust_level": review_obj.evidence_trust_level,
                "risk_evidence_matrix": review_obj.risk_evidence_matrix_category,
                "document_completeness": review_obj.document_completeness_status,
                "missing_documents": review_obj.missing_documents or [],
                "critical_issue": review_obj.critical_issue,
                "verification_issue_type": review_obj.verification_issue_type,
                "primary_reason": mask_pii(review_obj.primary_reason) if review_obj.primary_reason else None,
                "recommended_action": review_obj.recommended_action,
            }

        return {
            "tool": "get_application_context",
            "status": "OK",
            "application_id": application_id,
            "applicant_name": mask_pii(profile.get("applicant_name", "N/A")),
            "loan_amount": profile.get("loan_amount") or 0,
            "income_annum": profile.get("income_annum") or 0,
            "monthly_income": profile.get("monthly_income") or 0,
            "cibil_score": profile.get("cibil_score"),
            "loan_term": profile.get("loan_term"),
            "self_employed": profile.get("self_employed"),
            "education": profile.get("education"),
            "no_of_dependents": profile.get("no_of_dependents"),
            "application_status": app_obj.status,
            "documents_present": doc_types,
            "documents_missing": missing_types,
            "document_completeness": "COMPLETE" if not missing_types else "INCOMPLETE",
            "review_summary": review_summary,
            "evidence_node_ids": [f"NODE-APP-{application_id}"],
        }
    except Exception as e:
        logger.error(f"get_application_context exception: {e}")
        return {"tool": "get_application_context", "status": "ERROR", "error": str(e)}


# ── TOOL 2: get_evidence ─────────────────────────────────────────────────────

def get_evidence(application_id: str, db: Session) -> Dict[str, Any]:
    """
    Retrieves Evidence Graph nodes for the application.
    Returns nodes grouped by type with their IDs for citation.
    """
    app_err = _validate_application_id(application_id)
    if app_err:
        return {"tool": "get_evidence", "status": "ERROR", "error": app_err}

    try:
        app_obj = db.query(LoanApplicationModel).filter(
            LoanApplicationModel.application_id == application_id
        ).first()
        if not app_obj:
            return {"tool": "get_evidence", "status": "ERROR", "error": f"Application '{application_id}' not found."}

        nodes = db.query(EvidenceNodeModel).filter(
            EvidenceNodeModel.application_id == application_id
        ).all()

        if not nodes:
            return {
                "tool": "get_evidence",
                "status": "OK",
                "application_id": application_id,
                "total_nodes": 0,
                "node_ids": [],
                "nodes": [],
                "node_types": [],
                "nodes_by_type": {},
                "note": "No evidence graph nodes found. Run evidence graph build first.",
            }

        node_list = []
        for n in nodes:
            node_list.append({
                "node_id": n.node_id,
                "node_type": n.node_type,
                "title": mask_pii(n.title),
                "value": mask_pii(str(n.value)) if n.value else None,
                "confidence": n.confidence,
                "source_type": n.source_type,
            })

        node_ids = [n["node_id"] for n in node_list]

        # Group by type for easier agent reasoning
        by_type: Dict[str, List] = {}
        for n in node_list:
            t = n["node_type"]
            by_type.setdefault(t, []).append(n)

        return {
            "tool": "get_evidence",
            "status": "OK",
            "application_id": application_id,
            "total_nodes": len(node_list),
            "node_ids": node_ids,
            "nodes": node_list,
            "node_types": list(by_type.keys()),
            "nodes_by_type": by_type,
        }
    except Exception as e:
        logger.error(f"get_evidence exception: {e}")
        return {"tool": "get_evidence", "status": "ERROR", "error": str(e)}


# ── TOOL 3: get_verification_findings ────────────────────────────────────────

def get_verification_findings(application_id: str, db: Session) -> Dict[str, Any]:
    """
    Retrieves cross-document verification results and finding details.
    """
    app_err = _validate_application_id(application_id)
    if app_err:
        return {"tool": "get_verification_findings", "status": "ERROR", "error": app_err}

    app_obj = db.query(LoanApplicationModel).filter(
        LoanApplicationModel.application_id == application_id
    ).first()
    if not app_obj:
        return {"tool": "get_verification_findings", "status": "ERROR", "error": f"Application '{application_id}' not found."}

    try:
        ver_record = db.query(ApplicationVerificationModel).filter(
            ApplicationVerificationModel.application_id == application_id
        ).first()

        if not ver_record:
            return {
                "tool": "get_verification_findings",
                "status": "OK",
                "application_id": application_id,
                "overall_result": "NOT_VERIFIED",
                "total_comparisons": 0,
                "matched": 0,
                "mismatched": 0,
                "mismatched_comparisons": 0,
                "mismatches": [],
                "warnings": [],
                "all_findings": [],
                "findings": [],
                "evidence_node_ids": [],
                "note": "No verification has been run for this application.",
            }

        findings = db.query(VerificationFindingModel).filter(
            VerificationFindingModel.verification_id == ver_record.id
        ).all()

        finding_list = []
        finding_node_ids = []
        for f in findings:
            finding_list.append({
                "finding_id": f.id,
                "rule_name": f.rule_name,
                "verification_type": f.verification_type,
                "result": f.result,
                "severity": f.severity,
                "source_a": f.source_a,
                "field_a": f.field_a,
                "value_a": mask_pii(str(f.value_a)) if f.value_a else None,
                "source_b": f.source_b,
                "field_b": f.field_b,
                "value_b": mask_pii(str(f.value_b)) if f.value_b else None,
                "difference_percent": f.difference_percent,
                "message": mask_pii(f.message),
            })
            finding_node_ids.append(f"NODE-FINDING-{f.id}")

        mismatches = [f for f in finding_list if f["result"] == "MISMATCH"]
        warnings = [f for f in finding_list if f["result"] == "MATCH" and f["severity"] in ("WARNING", "ERROR")]

        return {
            "tool": "get_verification_findings",
            "status": "OK",
            "application_id": application_id,
            "overall_result": ver_record.overall_result,
            "total_comparisons": ver_record.total_comparisons,
            "matched": ver_record.matched_comparisons,
            "mismatched": ver_record.mismatched_comparisons,
            "mismatched_comparisons": ver_record.mismatched_comparisons,
            "mismatches": mismatches,
            "warnings": warnings,
            "all_findings": finding_list,
            "findings": finding_list,
            "evidence_node_ids": finding_node_ids,
        }
    except Exception as e:
        logger.error(f"get_verification_findings exception: {e}")
        return {"tool": "get_verification_findings", "status": "ERROR", "error": str(e)}


# ── TOOL 4: get_risk_analysis ─────────────────────────────────────────────────

def get_risk_analysis(application_id: str, db: Session) -> Dict[str, Any]:
    """
    Retrieves ML risk analysis for the application.
    Always frames ML output as historical risk, not guaranteed default probability.
    """
    app_err = _validate_application_id(application_id)
    if app_err:
        return {"tool": "get_risk_analysis", "status": "ERROR", "error": app_err}

    app_obj = db.query(LoanApplicationModel).filter(
        LoanApplicationModel.application_id == application_id
    ).first()
    if not app_obj:
        return {"tool": "get_risk_analysis", "status": "ERROR", "error": f"Application '{application_id}' not found."}

    try:
        profile = get_application_profile_data(db, application_id)
        risk_res = predict_application_risk(application_id, profile)

        if risk_res.status != "COMPLETED":
            return {
                "tool": "get_risk_analysis",
                "status": "UNAVAILABLE",
                "note": f"ML risk analysis is unavailable ({risk_res.reason or 'model status incomplete'}).",
            }

        return {
            "tool": "get_risk_analysis",
            "status": "OK",
            "application_id": application_id,
            "ml_status": risk_res.status,
            "model_name": risk_res.model_name,
            "model_version": risk_res.model_version,
            "rejection_probability": risk_res.rejection_probability,
            "ml_probability": risk_res.rejection_probability,
            "risk_level": risk_res.risk_level,
            "ml_risk_level": risk_res.risk_level,
            "target_definition": risk_res.target_definition,
            "evidence_node_ids": [f"NODE-ML-RISK-{application_id}"],
            "interpretation_note": (
                "This is a HISTORICAL REJECTION RISK indicator based on patterns in similar "
                "loan applications. It is NOT a guaranteed default probability, NOT a fraud model, and NOT an "
                "automatic credit decision. The final decision belongs to the human loan officer."
            ),
        }
    except Exception as e:
        logger.warning(f"get_risk_analysis unavailable: {e}")
        return {
            "tool": "get_risk_analysis",
            "status": "UNAVAILABLE",
            "note": "ML risk model is unavailable.",
            "error": str(e),
        }


# ── TOOL 5: get_review_score ──────────────────────────────────────────────────

def get_review_score(application_id: str, db: Session) -> Dict[str, Any]:
    """
    Retrieves the Review Intelligence score, priority, and breakdown.
    """
    app_err = _validate_application_id(application_id)
    if app_err:
        return {"tool": "get_review_score", "status": "ERROR", "error": app_err}

    app_obj = db.query(LoanApplicationModel).filter(
        LoanApplicationModel.application_id == application_id
    ).first()
    if not app_obj:
        return {"tool": "get_review_score", "status": "ERROR", "error": f"Application '{application_id}' not found."}

    try:
        review_obj = db.query(ReviewAssessmentModel).filter(
            ReviewAssessmentModel.application_id == application_id
        ).first()

        if not review_obj:
            return {
                "tool": "get_review_score",
                "status": "UNAVAILABLE",
                "note": "No Review Assessment found for this application.",
            }

        secondary = review_obj.secondary_reasons or []
        score_factors = review_obj.score_factors or []

        return {
            "tool": "get_review_score",
            "status": "OK",
            "application_id": application_id,
            "review_id": review_obj.review_id,
            "review_score": review_obj.review_score,
            "review_priority": review_obj.review_priority,
            "ml_risk_score": review_obj.ml_risk_score,
            "ml_risk_level": review_obj.ml_risk_level,
            "evidence_trust_score": review_obj.evidence_trust_score,
            "evidence_trust_level": review_obj.evidence_trust_level,
            "evidence_consistency_category": review_obj.evidence_consistency_category,
            "risk_evidence_matrix": review_obj.risk_evidence_matrix_category,
            "primary_reason": mask_pii(review_obj.primary_reason) if review_obj.primary_reason else None,
            "secondary_reasons": [mask_pii(str(r)) for r in secondary] if isinstance(secondary, list) else [],
            "validation_issue_count": review_obj.validation_issue_count,
            "verification_issue_count": review_obj.verification_issue_count,
            "document_completeness": review_obj.document_completeness_status,
            "document_completeness_status": review_obj.document_completeness_status,
            "missing_documents": review_obj.missing_documents or [],
            "missing_document": review_obj.missing_document,
            "critical_issue": review_obj.critical_issue,
            "verification_issue_type": review_obj.verification_issue_type,
            "issue_type": review_obj.verification_issue_type,
            "highest_severity": review_obj.highest_severity,
            "recommended_action": review_obj.recommended_action,
            "score_factors": score_factors if isinstance(score_factors, list) else [],
            "scoring_version": review_obj.scoring_version,
            "evidence_node_ids": [f"NODE-REVIEW-{application_id}"],
        }
    except Exception as e:
        logger.error(f"get_review_score exception: {e}")
        return {
            "tool": "get_review_score",
            "status": "UNAVAILABLE",
            "note": "Review Assessment is unavailable.",
            "error": str(e),
        }


# ── TOOL 6: search_policy ─────────────────────────────────────────────────────

def search_policy(query: str, db: Session) -> Dict[str, Any]:
    """
    Searches the Phase 14 Policy RAG system with a semantic query.
    Returns policy chunks with full citation provenance.
    Preserves RBI vs INTERNAL_BANK distinction.
    """
    # 1. Query validation
    if not query or not str(query).strip():
        return {
            "tool": "search_policy",
            "status": "ERROR",
            "error": "Policy search query cannot be empty.",
        }

    q_str = str(query).strip()
    if len(q_str) > 500:
        log_security_event("POLICY_QUERY_LENGTH_EXCEEDED", {"query_length": len(q_str)})
        return {
            "tool": "search_policy",
            "status": "ERROR",
            "error": "Policy search query exceeds maximum allowed length of 500 characters.",
        }

    # 2. Prompt injection scan on search query
    inj_status, flags = check_for_injection(q_str)
    if inj_status == "FLAGGED":
        log_security_event("POLICY_QUERY_INJECTION_FLAGGED", {"query": q_str, "flags": flags})
        return {
            "tool": "search_policy",
            "status": "ERROR",
            "error": "Policy search query contains disallowed instruction override patterns.",
        }

    # 3. Cross-applicant / applicant reference check (policy queries must be general)
    applicant_pattern = re.compile(r"\b(A\d{3}|APP-[A-Z0-9_-]+|applicant\s+[A-Z0-9_-]+)\b", re.IGNORECASE)
    if applicant_pattern.search(q_str):
        log_security_event("POLICY_QUERY_APPLICANT_CROSS_REFERENCE_BLOCKED", {"query": q_str})
        return {
            "tool": "search_policy",
            "status": "BLOCKED",
            "warning": "Cross-applicant access attempt detected. Policy search must query general regulatory or underwriting policies, not specific applicant data.",
        }

    try:
        from app.services.policy_rag_service import PolicyRAGService
        from app.schemas.policy_rag import PolicySearchRequest

        search_req = PolicySearchRequest(query=q_str, top_k=5)
        result = PolicyRAGService.search_policies(db, search_req)

        if not result or not result.results:
            return {
                "tool": "search_policy",
                "status": "OK",
                "query": q_str,
                "total_results": 0,
                "results": [],
                "note": "No policy documents matched the query.",
            }

        policy_results = []
        for item in result.results:
            cit = item.citation
            pol_source = cit.source or ("RBI" if "RBI" in cit.policy_id else ("HDFC_INTERNAL_DEMO" if cit.is_simulated else "HDFC_BANK"))
            is_sim = cit.is_simulated if cit.is_simulated is not None else ("DEMO" in cit.policy_id or "INTERNAL" in cit.policy_id)
            source_label = format_policy_source_label(pol_source, is_sim, cit.policy_id)

            policy_results.append({
                "chunk_id": item.chunk_id,
                "policy_id": cit.policy_id,
                "section_id": cit.policy_id,          # Canonical policy ID
                "policy_name": cit.policy_name,
                "authority": cit.authority,          # RBI or INTERNAL_BANK
                "source": pol_source,
                "is_simulated": is_sim,
                "source_label": source_label,
                "policy_type": cit.policy_type,      # REGULATORY or INTERNAL_UNDERWRITING
                "section_title": cit.section_title,
                "section_reference": cit.section_reference,
                "content_snippet": mask_pii(item.content[:600]),
                "similarity_score": item.similarity_score,
                "source_url": cit.source_url,
                "version": cit.version,
                "effective_date": cit.effective_date,
                "important_note": (
                    f"[{source_label}] internal underwriting rule — do NOT attribute to RBI."
                    if pol_source != "RBI" else
                    f"[{source_label}] official RBI regulatory policy ({cit.reference_code or 'RBI'})."
                ),
            })

        return {
            "tool": "search_policy",
            "status": "OK",
            "query": q_str,
            "total_results": result.total_results,
            "results": policy_results,
        }
    except Exception as e:
        logger.warning(f"Policy search failed: {e}")
        return {
            "tool": "search_policy",
            "status": "UNAVAILABLE",
            "query": q_str,
            "note": "Policy RAG vector index is currently unavailable.",
            "error": str(e),
        }
