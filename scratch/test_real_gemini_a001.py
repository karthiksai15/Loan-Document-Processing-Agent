import json
import sys
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.policy_knowledge_service import PolicyKnowledgeService


def _format_policy_label(pol: dict) -> str:
    """
    Formats the display label for policy source:
      - HDFC_BANK + is_simulated=false -> [HDFC_BANK]
      - HDFC_INTERNAL_DEMO + is_simulated=true -> [INTERNAL_DEMO]
      - RBI + is_simulated=false -> [RBI]
    """
    if pol.get("source_label"):
        return pol["source_label"]

    pol_id = str(pol.get("policy_id") or pol.get("section_id") or "")
    source = pol.get("source")
    is_sim = pol.get("is_simulated")

    # Look up in knowledge base if source / is_simulated not in dictionary
    if not source or is_sim is None:
        try:
            policies = PolicyKnowledgeService.load_policies()
            for p in policies:
                if p.policy_id == pol_id or pol_id.startswith(p.policy_id):
                    source = p.source
                    is_sim = p.is_simulated
                    break
        except Exception:
            pass

    # Fallback heuristic based on canonical ID pattern
    if not source:
        if "HDFC_PUB" in pol_id:
            source = "HDFC_BANK"
            is_sim = False
        elif "DEMO" in pol_id or "INTERNAL" in pol_id:
            source = "HDFC_INTERNAL_DEMO"
            is_sim = True
        elif "RBI" in pol_id:
            source = "RBI"
            is_sim = False

    # Required display formatting
    if source == "HDFC_BANK" and not is_sim:
        return "HDFC_BANK"
    elif source == "HDFC_INTERNAL_DEMO" or is_sim:
        return "INTERNAL_DEMO"
    elif source == "RBI":
        return "RBI"

    return pol.get("authority") or source or "UNKNOWN"


def main():
    client = TestClient(app)

    print("=" * 60)
    print("LIVE GEMINI AI REVIEW AGENT VERIFICATION FOR A006")
    print(f"LLM Provider : {settings.LLM_PROVIDER}")
    print(f"Gemini Model : {settings.GEMINI_MODEL}")
    print(f"Max Retries  : {settings.MAX_LLM_RETRIES}")
    print("=" * 60)

    res = client.post(
        "/api/v1/applications/A006/agent/review",
        json={"force_rebuild": True}
    )

    print(f"Status Code: {res.status_code}")
    if res.status_code not in (200, 201):
        print(f"Error: {res.text}")
        sys.exit(1)

    data = res.json()
    final_review = data.get("final_review") or {}

    print("\n--- AGENT REVIEW EXECUTION SUMMARY ---")
    print(f"Review ID            : {data.get('agent_review_id')}")
    print(f"Application ID       : {data.get('application_id')}")
    print(f"Investigation Status : {data.get('investigation_status')}")
    print(f"Grounding Status     : {data.get('grounding_status')}")
    print(f"Evidence Sufficiency : {data.get('evidence_sufficiency')}")
    print(f"Step Count           : {data.get('step_count')}")
    print(f"Retries Count        : {data.get('retries_count')}")
    print(f"Escalation Required  : {data.get('escalation_required')} ({data.get('escalation_reason')})")
    print(f"Confidence           : {data.get('confidence')} ({data.get('confidence_level')})")
    print(f"Recommended Step     : {final_review.get('recommended_next_step')}")

    print("\n--- CITED POLICY REFERENCES ---")
    policy_refs = final_review.get("policy_references", [])
    if not policy_refs:
        print("  (None cited)")
    for i, pol in enumerate(policy_refs, 1):
        pol_id = pol.get("policy_id") or pol.get("section_id")
        display_label = _format_policy_label(pol)
        name = pol.get("policy_name")
        print(f"  {i}. [{display_label}] {pol_id} - {name}")

    print("\n--- CITED EVIDENCE REFERENCES ---")
    ev_refs = final_review.get("evidence_references", [])
    if not ev_refs:
        print("  (None cited)")
    for i, ev in enumerate(ev_refs, 1):
        print(f"  {i}. {ev.get('node_id')}: {ev.get('description')}")

    print("\n--- EXECUTIVE SUMMARY ---")
    print(final_review.get("executive_summary", "N/A"))

    print("\n--- KEY FINDINGS ---")
    for f in final_review.get("key_findings", []):
        print(f"  - {f}")

    print("\n--- INVESTIGATION STEPS TRACE ---")
    for step in data.get("investigation_steps", []):
        print(f"  Step {step.get('step_number')}: [{step.get('action')}] {step.get('result_summary')[:100]}")
    print("=" * 60)


if __name__ == "__main__":
    main()
