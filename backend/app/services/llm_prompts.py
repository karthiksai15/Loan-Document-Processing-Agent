"""
LLM Prompts and Formatting — Phase 15 LLM Service

Central repository for Loan Review Assistant system prompt, prompt construction,
and strict banking decision-support constraints.
"""

from typing import Dict, Any, List, Optional
from app.schemas.llm import LLMDirectReviewRequest


LOAN_REVIEW_SYSTEM_PROMPT = """You are a Loan Review Assistant helping a human loan officer review a loan application.

PURPOSE:
You provide decision support by analyzing supplied application evidence, document findings, ML risk information, and retrieved policy evidence.

MANDATORY RULES AND CONSTRAINTS:

1. ROLE & FINAL DECISION BOUNDARY:
- You do NOT make the final approval or rejection decision. The loan officer makes the final decision.
- You must NOT recommend an automatic "APPROVED" or "REJECTED" final loan decision.
- Your recommended_next_action MUST be an operational review action, one of:
  "STANDARD_REVIEW", "OFFICER_INVESTIGATION", "DOCUMENT_FOLLOWUP", or "ESCALATE".

2. CLOSED-WORLD EVIDENCE GROUNDING:
- You may use ONLY the facts, document extractions, validation results, verification findings, ML risk scores, and retrieved policies supplied in the prompt.
- DO NOT invent applicant information, missing documents, financial values, policy rules, regulatory mandates, calculations, or conclusions unsupported by evidence.
- If information is unavailable, explicitly state: "Not available" or "Insufficient evidence". Never guess.

3. POLICY SOURCE SEPARATION (STRICT):
- RBI Policies (source="RBI", is_simulated=false): Must be identified as official RBI regulatory requirements.
- HDFC Public Information (source="HDFC_BANK", is_simulated=false): Must be identified as publicly published HDFC Bank guidance.
- HDFC Simulated/Demo Rules (source="HDFC_INTERNAL_DEMO", is_simulated=true): MUST be explicitly identified as "Simulated HDFC internal/demo rule". Never present simulated rules as official HDFC Bank policy. Never attribute simulated rules to RBI.

4. ML RISK INTERPRETATION:
- The ML model predicts a historical rejection-risk indicator based on the Kaggle Loan Approval Prediction Dataset.
- It is NOT a default prediction model, NOT a fraud model, and NOT a final loan decision.
- Always describe it as a "historical rejection-risk indicator".
- Report the supplied level (LOW, MEDIUM, HIGH) and probability.
- You must NOT state "ML says reject" and must NOT automatically recommend rejection because ML risk is HIGH.

5. MISSING DOCUMENTS VS MISMATCHES:
- Missing documents must NOT be treated as data mismatches or inconsistent income.
- For example, if TAX_RETURN is missing: state "Tax return is missing. Tax income verification cannot be completed from available documents." Do not invent contents of missing documents.

6. CONFLICTING INFORMATION:
- When documents conflict, state the conflict and the exact supplied values (e.g., Payslip net salary: INR 117,040 vs Bank average credit: INR 82,000).
- Do NOT arbitrarily decide which document is correct.
- Identify the discrepancy as a point for officer investigation/reconciliation.

7. ANSWER STYLE & CONCISENESS:
- Answers must be simple, concise, structured, scannable, factual, and evidence-based.
- Use approximately 1–3 short sentences per section.
- Avoid unnecessary introductory language or conversational monologues.
- Distinguish facts from interpretation. Do not attack applicant character.

8. CONFIDENCE:
- Report confidence based on supplied evidence quality and completeness.
- If confidence cannot be determined, state "Insufficient evidence to determine confidence".

9. OUTPUT FORMAT:
- You MUST respond ONLY with a valid JSON object matching this schema:
{
  "summary": "<1-3 concise sentences summarizing the review>",
  "application_status": "<COMPLETE | INCOMPLETE | UNDER_REVIEW>",
  "documents": {
    "present": ["<doc_type>", ...],
    "missing": ["<doc_type>", ...]
  },
  "key_findings": [
    {
      "issue": "<issue description>",
      "severity": "<INFO | WARNING | ERROR>",
      "evidence": ["<specific fact 1>", ...]
    }
  ],
  "risk_assessment": {
    "ml_probability": <float or null>,
    "ml_level": "<LOW | MEDIUM | HIGH | null>",
    "evidence_quality": <float or null>,
    "review_priority_score": <float or null>,
    "review_priority_level": "<LOW | MEDIUM | HIGH | null>"
  },
  "policy_basis": [
    {
      "source": "<RBI | HDFC_BANK | HDFC_INTERNAL_DEMO>",
      "is_simulated": <true | false>,
      "policy_name": "<policy title>",
      "relevance": "<concise statement of relevance>"
    }
  ],
  "missing_information": ["<item 1>", ...],
  "investigation_points": ["<point 1>", ...],
  "recommended_next_action": "<STANDARD_REVIEW | OFFICER_INVESTIGATION | DOCUMENT_FOLLOWUP | ESCALATE>",
  "confidence": <float 0.0-1.0 or string explanation>
}
Do not wrap in backticks or code fences. Return raw valid JSON.
"""


def format_direct_review_prompt(req: LLMDirectReviewRequest) -> str:
    """
    Formats an LLMDirectReviewRequest into structured factual sections
    for the Loan Review Assistant prompt.
    """
    parts = []

    # 1. Application Data
    parts.append("=== APPLICATION DATA ===")
    if req.application_id:
        parts.append(f"Application ID   : {req.application_id}")
    if req.applicant_name:
        parts.append(f"Applicant Name   : {req.applicant_name}")
    if req.loan_amount is not None:
        parts.append(f"Loan Amount      : INR {req.loan_amount:,.0f}")
    if req.annual_income is not None:
        parts.append(f"Annual Income    : INR {req.annual_income:,.0f}")
    if req.monthly_income is not None:
        parts.append(f"Monthly Income   : INR {req.monthly_income:,.0f}")
    if req.cibil_score is not None:
        parts.append(f"CIBIL Score      : {req.cibil_score}")

    # 2. Document Status
    parts.append("\n=== DOCUMENT EVIDENCE ===")
    parts.append(f"Documents Present: {', '.join(req.documents_present) if req.documents_present else 'None declared'}")
    parts.append(f"Documents Missing: {', '.join(req.documents_missing) if req.documents_missing else 'None'}")
    if req.extracted_fields:
        parts.append("Extracted Document Fields:")
        for doc_key, fields in req.extracted_fields.items():
            parts.append(f"  [{doc_key}]")
            if isinstance(fields, dict):
                for k, v in fields.items():
                    parts.append(f"    - {k}: {v}")
            elif isinstance(fields, list):
                for item in fields:
                    parts.append(f"    - {item}")
            else:
                parts.append(f"    - {fields}")

    # 3. Document Validation Warnings
    if req.validation_warnings:
        parts.append("\n=== VALIDATION RESULTS ===")
        for w in req.validation_warnings:
            parts.append(f"  - {w}")

    # 4. Cross-Document Verification Findings
    if req.verification_findings:
        parts.append("\n=== CROSS-DOCUMENT VERIFICATION FINDINGS ===")
        for vf in req.verification_findings:
            if isinstance(vf, dict):
                rule = vf.get("rule_name") or vf.get("rule") or "Check"
                res = vf.get("result") or vf.get("status") or "FINDING"
                msg = vf.get("message") or vf.get("details") or str(vf)
                parts.append(f"  - [{res}] {rule}: {msg}")
            else:
                parts.append(f"  - {vf}")

    # 5. ML Risk Assessment
    if req.ml_risk:
        parts.append("\n=== ML RISK ASSESSMENT ===")
        prob = req.ml_risk.get("rejection_probability") or req.ml_risk.get("ml_probability")
        level = req.ml_risk.get("risk_level") or req.ml_risk.get("ml_level")
        parts.append(f"Target: Historical Rejection-Risk Indicator (Kaggle Dataset)")
        if prob is not None:
            parts.append(f"Rejection Probability: {float(prob):.4f}")
        if level:
            parts.append(f"Risk Level: {level}")

    # 6. Review Score / Intelligence
    if req.review_score:
        parts.append("\n=== REVIEW INTELLIGENCE ===")
        score = req.review_score.get("review_score")
        prio = req.review_score.get("review_priority") or req.review_score.get("priority")
        trust = req.review_score.get("evidence_trust_score")
        matrix = req.review_score.get("risk_evidence_matrix_category")
        if score is not None:
            parts.append(f"Review Score: {score}")
        if prio:
            parts.append(f"Priority: {prio}")
        if trust is not None:
            parts.append(f"Evidence Trust Score: {trust}")
        if matrix:
            parts.append(f"Risk-Evidence Matrix: {matrix}")

    # 7. Retrieved Policies
    if req.retrieved_policies:
        parts.append("\n=== RETRIEVED POLICY EVIDENCE (Phase 14 RAG) ===")
        for idx, p in enumerate(req.retrieved_policies, 1):
            source = p.get("source", "UNKNOWN")
            is_sim = p.get("is_simulated", False)
            title = p.get("policy_name") or p.get("title", "Policy Rule")
            sec = p.get("section") or p.get("section_title") or p.get("rule", "")
            snippet = p.get("snippet") or p.get("content") or p.get("text", "")
            sim_label = "[SIMULATED DEMO RULE]" if is_sim else "[OFFICIAL POLICY]"
            parts.append(f"Policy {idx}: {sim_label} Source={source} | {title} | Section={sec}")
            if snippet:
                parts.append(f"  Text: {snippet[:400].strip()}")

    if req.custom_instructions:
        parts.append(f"\nAdditional Instructions: {req.custom_instructions}")

    parts.append("\nBased strictly on the structured evidence above, produce the complete JSON review object.")
    return "\n".join(parts)
