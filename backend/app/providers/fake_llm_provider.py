"""
Fake LLM Provider — Phase 15, 16 & 17 (Test Only)

Deterministic mock LLM provider for unit and integration tests.
Does NOT call any external API; no GROQ_API_KEY required.
Supports both Phase 15 single-turn reviews, Phase 16 LangGraph multi-node agent workflows,
and Phase 17 adversarial failure/retry simulations.
"""

import json
from typing import Optional, List, Dict, Any
from app.providers.base_llm_provider import BaseLLMProvider


_DEFAULT_REVIEW_TEMPLATE = {
    "summary": "This is a structured LLM review generated for testing purposes. The application appears complete with supporting documents.",
    "executive_summary": "This is a structured LLM review generated for testing purposes. The application appears complete with supporting documents.",
    "application_status": "COMPLETE",
    "documents": {
        "present": ["PAYSLIP", "BANK_STATEMENT", "KYC"],
        "missing": []
    },
    "key_findings": [
        "Income verified across payslip and bank statement",
        "CIBIL score above minimum threshold",
        "No critical document mismatches detected"
    ],
    "risk_assessment": {
        "ml_probability": 0.15,
        "ml_level": "LOW",
        "evidence_quality": 92.0,
        "review_priority_score": 25.0,
        "review_priority_level": "LOW"
    },
    "policy_basis": [
        {
            "source": "HDFC_BANK",
            "is_simulated": False,
            "policy_name": "HDFC Bank Personal Loan — Public Documentation Checklist for Salaried Applicants",
            "relevance": "Standard retail documentation requirements verified as present."
        }
    ],
    "missing_information": [],
    "investigation_points": [],
    "recommended_next_action": "STANDARD_REVIEW",
    "recommended_action": "STANDARD_REVIEW",
    "recommended_next_step": "STANDARD_REVIEW",
    "confidence": 0.82,
    "confidence_level": "HIGH",
    "limitations": [
        "LLM review is based on available structured data only",
        "Final credit decision remains with the loan officer"
    ],
    "evidence_references": [],
    "policy_references": [],
    "risk_interpretation": "The ML model indicates a LOW historical rejection-risk indicator. This is based on patterns in similar applicant profiles, not a direct creditworthiness assessment or guaranteed default probability.",
    "review_interpretation": "Evidence trust is evaluated as consistent across submitted documents.",
    "unresolved_questions": [],
    "escalation_required": False,
    "escalation_reason": None
}


class FakeLLMProvider(BaseLLMProvider):
    """
    Deterministic fake LLM provider for unit tests.
    Supports multi-step LangGraph agent dialogs and adversarial failure simulations.
    """

    def __init__(
        self,
        custom_response: Optional[str] = None,
        inject_evidence_ids: Optional[list] = None,
        inject_policy_ids: Optional[list] = None,
        tool_sequence: Optional[List[str]] = None,
        investigation_needed: bool = True,
        escalation_required: bool = False,
        escalation_reason: Optional[str] = None,
        recommended_next_step: Optional[str] = None,
        risk_interpretation: Optional[str] = None,
        review_interpretation: Optional[str] = None,
        executive_summary: Optional[str] = None,
        unresolved_questions: Optional[List[str]] = None,
        fail_with: Optional[str] = None,
        repeat_tool_calls: bool = False,
        transient_error_count: int = 0,
        malformed_json_count: int = 0,
        inject_invalid_confidence: Optional[float] = None,
        inject_unsupported_tax_claim: bool = False,
        planned_tools: Optional[List[str]] = None,
        key_findings: Optional[List[str]] = None,
    ):
        self.custom_response = custom_response
        self.inject_evidence_ids = list(inject_evidence_ids or [])
        self.inject_policy_ids = list(inject_policy_ids or [])
        self.tool_sequence = list(tool_sequence or [])
        self.planned_tools = list(planned_tools) if planned_tools is not None else None
        self.key_findings = list(key_findings) if key_findings is not None else None
        self.investigation_needed = investigation_needed
        self.escalation_required = escalation_required
        self.escalation_reason = escalation_reason
        self.recommended_next_step = recommended_next_step
        self.risk_interpretation = risk_interpretation
        self.review_interpretation = review_interpretation
        self.executive_summary = executive_summary
        self.unresolved_questions = list(unresolved_questions or [])
        self.fail_with = fail_with
        self.repeat_tool_calls = repeat_tool_calls
        self.transient_error_count = transient_error_count
        self._transient_attempts = 0
        self.malformed_json_count = malformed_json_count
        self._malformed_attempts = 0
        self.inject_invalid_confidence = inject_invalid_confidence
        self.inject_unsupported_tax_claim = inject_unsupported_tax_claim
        self.call_count = 0

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        self.call_count += 1

        # 1. Fatal unrecoverable failure simulation
        if self.fail_with:
            raise RuntimeError(self.fail_with)

        # 2. Transient failure simulation (tests retry logic)
        if self._transient_attempts < self.transient_error_count:
            self._transient_attempts += 1
            raise RuntimeError("Rate-limit 429: temporary upstream provider timeout (transient error)")

        # 3. Malformed output simulation
        if self._malformed_attempts < self.malformed_json_count:
            self._malformed_attempts += 1
            return "{{MALFORMED_JSON_STRING_WITHOUT_CLOSING_BRACKET"

        # 4. Custom raw response override
        if self.custom_response is not None:
            return self.custom_response

        # ── Detect LangGraph node by prompt contents ─────────────────────────

        # Node 1: ANALYZE_CASE
        if "first_tool_needed" in prompt or "initial_assessment" in prompt or "planned_tools" in prompt:
            if self.planned_tools is not None:
                needs_inv = len(self.planned_tools) > 0
                return json.dumps({
                    "initial_assessment": "Initial assessment completed with planned tools.",
                    "key_signals": ["Review signals analyzed."],
                    "investigation_needed": needs_inv,
                    "planned_tools": self.planned_tools,
                    "first_tool_needed": self.planned_tools[0] if self.planned_tools else None,
                    "first_tool_query": None,
                    "reason": "Executing planned tool investigation.",
                    "initial_confidence": 0.85,
                })
            needs_inv = self.investigation_needed if (self.tool_sequence or not self.investigation_needed) else True
            if self.tool_sequence:
                first_tool = self.tool_sequence[0]
                return json.dumps({
                    "initial_assessment": "Initial assessment completed. Investigation required.",
                    "key_signals": ["Review priority and evidence signals detected."],
                    "investigation_needed": True,
                    "first_tool_needed": first_tool,
                    "first_tool_query": None,
                    "reason": f"Investigating via {first_tool}.",
                    "initial_confidence": 0.65,
                })
            elif not self.investigation_needed:
                return json.dumps({
                    "initial_assessment": "Application appears clean and verified from initial context.",
                    "key_signals": ["All required documents present and verified."],
                    "investigation_needed": False,
                    "first_tool_needed": None,
                    "first_tool_query": None,
                    "reason": "Sufficient initial evidence to formulate review.",
                    "initial_confidence": 0.88,
                })
            else:
                return json.dumps({
                    "initial_assessment": "Initial assessment complete. Inspecting application context.",
                    "key_signals": ["Application profile loaded."],
                    "investigation_needed": True,
                    "first_tool_needed": "get_application_context",
                    "first_tool_query": None,
                    "reason": "Loading baseline application context.",
                    "initial_confidence": 0.70,
                })

        # Node 2: DECIDE_NEXT_ACTION
        if "sufficient_evidence" in prompt and "next_tool" in prompt:
            if self.tool_sequence:
                next_t = self.tool_sequence.pop(0) if not self.repeat_tool_calls else self.tool_sequence[0]
                return json.dumps({
                    "sufficient_evidence": False,
                    "next_tool": next_t,
                    "next_tool_query": None,
                    "reason": f"Gathering additional data via {next_t}.",
                    "escalation_needed": self.escalation_required,
                    "escalation_reason": self.escalation_reason,
                })
            else:
                return json.dumps({
                    "sufficient_evidence": True,
                    "next_tool": None,
                    "next_tool_query": None,
                    "reason": "Sufficient evidence collected to proceed to final review.",
                    "escalation_needed": self.escalation_required,
                    "escalation_reason": self.escalation_reason,
                })

        # Node 3: INSPECT_RESULT
        if "new_findings" in prompt or "reasoning_summary" in prompt:
            return json.dumps({
                "new_findings": [
                    "Tool inspection yielded verified operational findings.",
                    "Evidence nodes and policy requirements analyzed."
                ],
                "evidence_node_ids": self.inject_evidence_ids,
                "policy_section_ids": self.inject_policy_ids,
                "unresolved_questions": self.unresolved_questions,
                "reasoning_summary": "Inspected tool output and updated investigation state.",
                "escalation_signal": self.escalation_required,
                "escalation_reason": self.escalation_reason,
                "updated_confidence": 0.85,
            })

        # Node 4: BUILD_REVIEW (or Phase 15 single-turn review)
        result = dict(_DEFAULT_REVIEW_TEMPLATE)

        if self.executive_summary:
            result["executive_summary"] = self.executive_summary
            result["summary"] = self.executive_summary

        if self.recommended_next_step:
            result["recommended_next_step"] = self.recommended_next_step
            result["recommended_action"] = self.recommended_next_step
            result["recommended_next_action"] = self.recommended_next_step

        if self.risk_interpretation:
            result["risk_interpretation"] = self.risk_interpretation

        if self.review_interpretation:
            result["review_interpretation"] = self.review_interpretation

        if self.escalation_required:
            result["escalation_required"] = True
            result["escalation_reason"] = self.escalation_reason or "Escalated for human officer investigation."

        if self.unresolved_questions:
            result["unresolved_questions"] = self.unresolved_questions

        if self.key_findings is not None:
            result["key_findings"] = self.key_findings

        if self.inject_invalid_confidence is not None:
            result["confidence"] = self.inject_invalid_confidence

        if self.inject_unsupported_tax_claim:
            result["key_findings"] = list(result.get("key_findings", [])) + [
                "Tax return document verified and confirms annual income of INR 1,500,000."
            ]

        if self.inject_evidence_ids:
            result["evidence_references"] = [
                {"node_id": nid, "description": f"Evidence node {nid}"}
                for nid in self.inject_evidence_ids
            ]
        elif "Evidence node IDs available:" in prompt:
            import ast
            try:
                line = [l for l in prompt.splitlines() if "Evidence node IDs available:" in l][0]
                raw_ids = line.split(":", 1)[1].strip()
                parsed_ids = ast.literal_eval(raw_ids)
                if parsed_ids:
                    result["evidence_references"] = [
                        {"node_id": nid, "description": f"Evidence node {nid}"}
                        for nid in parsed_ids[:3]
                    ]
            except Exception:
                pass

        if self.inject_policy_ids:
            result["policy_references"] = [
                {
                    "section_id": sid,
                    "policy_name": f"Policy section {sid}",
                    "authority": "RBI" if "RBI" in sid.upper() else "INTERNAL_BANK",
                    "policy_type": "REGULATORY" if "RBI" in sid.upper() else "INTERNAL_UNDERWRITING",
                    "citation_text": f"Section {sid} is relevant to this application"
                }
                for sid in self.inject_policy_ids
            ]
        elif "Policy IDs available:" in prompt:
            import ast
            try:
                line = [l for l in prompt.splitlines() if "Policy IDs available:" in l][0]
                raw_ids = line.split(":", 1)[1].strip()
                parsed_ids = ast.literal_eval(raw_ids)
                if parsed_ids:
                    result["policy_references"] = [
                        {
                            "section_id": sid,
                            "policy_name": f"Policy section {sid}",
                            "authority": "RBI" if "RBI" in sid.upper() else "INTERNAL_BANK",
                            "policy_type": "REGULATORY" if "RBI" in sid.upper() else "INTERNAL_UNDERWRITING",
                            "citation_text": f"Section {sid} is relevant to this application"
                        }
                        for sid in parsed_ids[:2]
                    ]
            except Exception:
                pass

        return json.dumps(result)

    def name(self) -> str:
        return "FakeLLMProvider(test)"
