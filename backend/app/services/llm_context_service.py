"""
LLM Context Service — Phase 15 GenAI Foundation

Assembles a structured, grounded, injection-safe context package
for the LLM to reason over an application.

Context sections (all TRUSTED except where noted):
  1. APPLICATION DATA         — structured fields from the application record
  2. DOCUMENT EVIDENCE        — extracted fields from Phase 7 (untrusted doc text excluded)
  3. VALIDATION RESULTS       — deterministic validation findings from Phase 8
  4. VERIFICATION FINDINGS    — cross-document comparison results from Phase 9
  5. ML RISK ASSESSMENT       — ML risk score / level from Phase 11
  6. REVIEW INTELLIGENCE      — review score / priority from Phase 12
  7. POLICY EVIDENCE          — semantically retrieved policy sections from Phase 14 RAG
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.models import (
    LoanApplicationModel,
    DocumentModel,
    ExtractedFieldModel,
    DocumentValidationModel,
    ValidationCheckModel,
    ApplicationVerificationModel,
    VerificationFindingModel,
    ReviewAssessmentModel,
    EvidenceNodeModel,
)
from app.services.cross_document_verification_service import get_application_profile_data
from app.ml.predictor import predict_application_risk
from app.services.llm_safety_service import check_for_injection, sanitize_untrusted_text


def build_llm_context(
    db: Session,
    application_id: str,
    max_policy_results: int = 5,
) -> Dict[str, Any]:
    """
    Builds a structured context dictionary for the LLM review.

    Returns a dict with keys:
      - sections: ordered list of context section strings
      - injection_check_status: CLEAN or FLAGGED
      - injection_flags: list of matched injection patterns
      - evidence_node_ids: list of all evidence node IDs in the graph (for grounding)
      - policy_section_ids: list of policy section IDs included in context
    """
    app_obj = db.query(LoanApplicationModel).filter(
        LoanApplicationModel.application_id == application_id
    ).first()
    if not app_obj:
        raise ValueError(f"Application '{application_id}' not found.")

    target_id = application_id.replace("APP-", "").upper()
    sections: List[str] = []
    injection_flags: List[str] = []
    policy_section_ids: List[str] = []

    # ── 1. APPLICATION DATA ──────────────────────────────────────────────────
    profile = get_application_profile_data(db, application_id)
    loan_amount = profile.get('loan_amount') or 0
    income_annum = profile.get('income_annum') or 0
    monthly_income = profile.get('monthly_income') or 0
    app_section = (
        f"=== APPLICATION DATA ===\n"
        f"Application ID   : {application_id}\n"
        f"Applicant Name   : {profile.get('applicant_name', 'N/A')}\n"
        f"Loan Amount      : INR {loan_amount:,.0f}\n"
        f"Annual Income    : INR {income_annum:,.0f}\n"
        f"Monthly Income   : INR {monthly_income:,.0f}\n"
        f"CIBIL Score      : {profile.get('cibil_score', 'N/A')}\n"
        f"Loan Term        : {profile.get('loan_term', 'N/A')} months\n"
        f"Employment       : {'Self-Employed' if profile.get('self_employed') == 'Yes' else 'Salaried'}\n"
        f"Education        : {profile.get('education', 'N/A')}\n"
        f"No. of Dependents: {profile.get('no_of_dependents', 'N/A')}\n"
        f"Application Status: {app_obj.status}\n"
    )
    sections.append(app_section)

    # ── 2. DOCUMENT EVIDENCE ─────────────────────────────────────────────────
    docs = db.query(DocumentModel).filter(
        (DocumentModel.application_id == application_id) | (DocumentModel.applicant_id == target_id),
        DocumentModel.processing_status != "DELETED"
    ).all()

    doc_lines = [f"=== DOCUMENT EVIDENCE ===\nDocuments found: {len(docs)}"]
    all_injection_texts: List[str] = []

    for doc in docs:
        d_type = (doc.classified_document_type or doc.document_type or "OTHER").upper()
        doc_lines.append(f"\n[Document: {d_type} | File: {doc.original_filename} | Extraction: {doc.extraction_status}]")

        fields = db.query(ExtractedFieldModel).filter(
            ExtractedFieldModel.document_id == doc.document_id
        ).all()
        for f in fields:
            doc_lines.append(f"  {f.field_name}: {f.normalized_value or f.raw_value} (confidence={f.confidence:.2f})")

        # Collect extracted text for injection scanning (untrusted)
        if doc.extracted_text_path:
            try:
                with open(doc.extracted_text_path, "r", encoding="utf-8", errors="replace") as fh:
                    raw_text = fh.read(3000)
                all_injection_texts.append(raw_text)
            except Exception:
                pass

    sections.append("\n".join(doc_lines))

    # Safety: scan all untrusted document text
    for raw_text in all_injection_texts:
        status, flags = check_for_injection(raw_text)
        if status == "FLAGGED":
            injection_flags.extend(flags)

    injection_check_status = "FLAGGED" if injection_flags else "CLEAN"

    # ── 3. VALIDATION RESULTS ────────────────────────────────────────────────
    val_lines = ["=== VALIDATION RESULTS ==="]
    for doc in docs:
        d_type = (doc.classified_document_type or doc.document_type or "OTHER").upper()
        val_records = db.query(DocumentValidationModel).filter(
            DocumentValidationModel.document_id == doc.document_id
        ).all()
        for vr in val_records:
            val_lines.append(f"[{d_type}] Overall: {vr.overall_result}")
            checks = db.query(ValidationCheckModel).filter(
                ValidationCheckModel.validation_id == vr.id
            ).all()
            for chk in checks:
                if chk.status in ("WARNING", "FAIL"):
                    val_lines.append(f"  [{chk.severity}] {chk.check_name}: {chk.message}")
    sections.append("\n".join(val_lines))

    # ── 4. VERIFICATION FINDINGS ─────────────────────────────────────────────
    ver_lines = ["=== CROSS-DOCUMENT VERIFICATION ==="]
    ver_record = db.query(ApplicationVerificationModel).filter(
        ApplicationVerificationModel.application_id == application_id
    ).first()
    if ver_record:
        ver_lines.append(f"Overall Result: {ver_record.overall_result} | Mismatches: {ver_record.mismatched_comparisons}")
        findings = db.query(VerificationFindingModel).filter(
            VerificationFindingModel.verification_id == ver_record.id
        ).all()
        for f in findings:
            if f.result != "MATCH":
                ver_lines.append(
                    f"  [{f.severity}] {f.rule_name}: {f.source_a}.{f.field_a}={f.value_a} vs "
                    f"{f.source_b}.{f.field_b}={f.value_b} → {f.result}"
                )
    else:
        ver_lines.append("No verification results available.")
    sections.append("\n".join(ver_lines))

    # ── 5. ML RISK ASSESSMENT ────────────────────────────────────────────────
    ml_lines = ["=== ML RISK ASSESSMENT ==="]
    try:
        risk_res = predict_application_risk(application_id, profile)
        if risk_res.status == "COMPLETED":
            ml_lines.append(f"Model: {risk_res.model_name} | Version: {risk_res.model_version}")
            ml_lines.append(f"Rejection Probability: {risk_res.rejection_probability:.4f}")
            ml_lines.append(f"Risk Level: {risk_res.risk_level}")
            ml_lines.append(f"Target Definition: {risk_res.target_definition}")
        else:
            ml_lines.append(f"ML Status: {risk_res.status} — {risk_res.reason or 'N/A'}")
    except Exception as e:
        ml_lines.append(f"ML Risk unavailable: {e}")
    sections.append("\n".join(ml_lines))

    # ── 6. REVIEW INTELLIGENCE ───────────────────────────────────────────────
    rev_lines = ["=== REVIEW INTELLIGENCE (Phase 12) ==="]
    review_obj = db.query(ReviewAssessmentModel).filter(
        ReviewAssessmentModel.application_id == application_id
    ).first()
    if review_obj:
        rev_lines.append(f"Review Score: {review_obj.review_score:.1f}/100")
        rev_lines.append(f"Priority: {review_obj.review_priority}")
        rev_lines.append(f"Evidence Trust: {review_obj.evidence_trust_score:.1f}/100 ({review_obj.evidence_trust_level})")
        rev_lines.append(f"Risk-Evidence Matrix: {review_obj.risk_evidence_matrix_category}")
        rev_lines.append(f"Document Completeness: {review_obj.document_completeness_status}")
        if getattr(review_obj, "missing_documents", None):
            rev_lines.append(f"Missing Documents: {', '.join(review_obj.missing_documents)}")
        if getattr(review_obj, "critical_issue", None):
            rev_lines.append(f"Critical Issue: {review_obj.critical_issue}")
        if getattr(review_obj, "verification_issue_type", None):
            rev_lines.append(f"Verification Issue Type: {review_obj.verification_issue_type}")
        if review_obj.primary_reason:
            rev_lines.append(f"Primary Reason: {review_obj.primary_reason}")
        rev_lines.append(f"Recommended Action (deterministic): {review_obj.recommended_action}")
        secondary = review_obj.secondary_reasons or []
        if isinstance(secondary, list) and secondary:
            for r in secondary[:3]:
                rev_lines.append(f"  - {r}")
    else:
        rev_lines.append("No Review Assessment computed yet.")
    sections.append("\n".join(rev_lines))

    # ── 7. POLICY EVIDENCE (Phase 14 RAG) ───────────────────────────────────
    policy_lines = ["=== POLICY EVIDENCE (Phase 14 RAG) ==="]
    try:
        from app.services.policy_rag_service import PolicyRAGService
        from app.schemas.policy_rag import PolicySearchRequest

        # Build a focused query from key application attributes
        query_parts = ["loan application review"]
        if profile.get("cibil_score"):
            query_parts.append("credit score CIBIL eligibility")
        if profile.get("income_annum"):
            query_parts.append("income verification salary bank statement")
        if ver_record and ver_record.mismatched_comparisons > 0:
            query_parts.append("document mismatch identity verification KYC")

        query = " ".join(query_parts)
        search_req = PolicySearchRequest(query=query, top_k=max_policy_results)
        search_result = PolicyRAGService.search_policies(db, search_req)

        if search_result.results:
            for item in search_result.results:
                cit = item.citation
                policy_lines.append(
                    f"\n[{cit.authority} / {cit.policy_type}] {cit.policy_name}"
                    f" — Section: {cit.section_title}"
                    f" (similarity={item.similarity_score:.3f})"
                )
                policy_lines.append(f"  Section ID: {cit.section_id}")
                policy_lines.append(f"  {item.content[:500]}")
                policy_section_ids.append(cit.section_id)
        else:
            policy_lines.append("No relevant policy sections retrieved.")
    except Exception as e:
        logger.warning(f"Policy RAG context failed for '{application_id}': {e}")
        policy_lines.append(f"Policy RAG unavailable: {e}")
    sections.append("\n".join(policy_lines))

    # ── Collect evidence node IDs (for citation grounding) ──────────────────
    evidence_nodes = db.query(EvidenceNodeModel).filter(
        EvidenceNodeModel.application_id == application_id
    ).all()
    evidence_node_ids = [n.node_id for n in evidence_nodes]

    return {
        "sections": sections,
        "injection_check_status": injection_check_status,
        "injection_flags": injection_flags,
        "evidence_node_ids": evidence_node_ids,
        "policy_section_ids": policy_section_ids,
        "application_id": application_id,
    }


def build_llm_prompt(context: Dict[str, Any]) -> tuple:
    """
    Constructs the system_prompt and user_prompt from the assembled context.

    Returns:
        (system_prompt, user_prompt)
    """
    from app.services.llm_prompts import LOAN_REVIEW_SYSTEM_PROMPT
    full_context = "\n\n".join(context["sections"])
    system_prompt = LOAN_REVIEW_SYSTEM_PROMPT
    user_prompt = (
        f"{full_context}\n\n"
        "---\n"
        "Based strictly on the structured system data above, produce the complete JSON review object matching the required schema.\n"
        "Remember: do not make a final approval or rejection decision. The loan officer makes the final decision."
    )
    return system_prompt, user_prompt
