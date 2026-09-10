"""
Phase 13 — Policy Knowledge Base Test Suite

Verifies:
1. Policy files load successfully from data/policies/.
2. Policy schema validation and field integrity.
3. All required sources exist: RBI, HDFC_BANK, HDFC_INTERNAL_DEMO.
4. RBI regulatory policies correctly labelled RBI with is_simulated=False.
5. HDFC public policies correctly labelled HDFC_BANK with is_simulated=False.
6. Demo rules correctly labelled HDFC_INTERNAL_DEMO with is_simulated=True.
7. Simulated policies explicitly have is_simulated=True.
8. Policy lookup by policy_id works.
9. Policy filtering by source works.
10. Policy filtering by category works.
11. Provenance completeness (reference_code, official_url, authority).
12. Strict distinction between RBI regulatory rules and HDFC demo rules.
13. No Phase 14 vector store / FAISS / embedding components in Phase 13 service.
14. REST API endpoints for Phase 13 work seamlessly.
"""

import os
import inspect
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.policy_knowledge_service import PolicyKnowledgeService
from app.schemas.policy import PolicyItemSchema, PolicyKnowledgeBaseSummary


client = TestClient(app)


# ── TEST 1: Policy Files Load Successfully ───────────────────────────────────

def test_policy_files_load_successfully():
    """Verify that all policy files load into valid PolicyItemSchema instances."""
    policies = PolicyKnowledgeService.load_policies(force_reload=True)
    assert len(policies) >= 12
    for p in policies:
        assert isinstance(p, PolicyItemSchema)
        assert p.policy_id
        assert p.title
        assert p.text


# ── TEST 2: Schema Validation & Required Fields ──────────────────────────────

def test_policy_schema_validation():
    """Verify that every policy has all required core fields populated."""
    policies = PolicyKnowledgeService.get_all_policies()
    for p in policies:
        data = p.model_dump()
        assert "policy_id" in data and len(data["policy_id"]) > 0
        assert "source" in data and data["source"] in ("RBI", "HDFC_BANK", "HDFC_INTERNAL_DEMO")
        assert "title" in data and len(data["title"]) > 0
        assert "category" in data and len(data["category"]) > 0
        assert "section" in data and len(data["section"]) > 0
        assert "rule" in data and len(data["rule"]) > 0
        assert "description" in data and len(data["description"]) > 0
        assert "text" in data and len(data["text"]) > 0
        assert "applicability" in data and len(data["applicability"]) > 0
        assert isinstance(data["is_simulated"], bool)


# ── TEST 3: All Required Sources Exist ───────────────────────────────────────

def test_all_required_sources_exist():
    """Verify that all three distinct sources are represented in the knowledge base."""
    summary = PolicyKnowledgeService.get_summary()
    assert "RBI" in summary.sources
    assert "HDFC_BANK" in summary.sources
    assert "HDFC_INTERNAL_DEMO" in summary.sources
    assert summary.rbi_policy_count == 5
    assert summary.hdfc_public_policy_count == 2
    assert summary.hdfc_internal_demo_policy_count == 6


# ── TEST 4: RBI Regulatory Policies Labeling ─────────────────────────────────

def test_rbi_policies_labeling():
    """Verify all 5 RBI policies are source=RBI, authority=RBI, and is_simulated=False with official URLs."""
    rbi_policies = PolicyKnowledgeService.get_policies_by_source("RBI")
    assert len(rbi_policies) == 5
    expected_ids = {
        "POL_RBI_KYC_OVD_001",
        "POL_RBI_KYC_NAME_MATCH_002",
        "POL_RBI_CREDIT_DUE_DILIGENCE_003",
        "POL_RBI_FAIR_PRACTICES_004",
        "POL_RBI_DIGITAL_LENDING_005",
    }
    found_ids = {p.policy_id for p in rbi_policies}
    assert expected_ids == found_ids

    for p in rbi_policies:
        assert p.source == "RBI"
        assert p.is_simulated is False
        assert p.authority == "RBI"
        assert p.reference_code is not None and len(p.reference_code) > 0
        assert p.official_url is not None and p.official_url.startswith("https://www.rbi.org.in")
        app_lower = p.applicability.lower()
        assert "regulated" in app_lower or "credit institutions" in app_lower or "banks" in app_lower or "entities" in app_lower


def test_rbi_policies_correct_sections_and_provenance():
    """Verify each of the 5 RBI policies accurately cites official sections/paragraphs and valid reference codes."""
    # 1. POL_RBI_KYC_OVD_001
    p1 = PolicyKnowledgeService.get_policy_by_id("POL_RBI_KYC_OVD_001")
    assert p1 is not None
    assert "Paragraph 16" in p1.section
    assert "3(a)(xiv)" in p1.section
    assert "Chapter IV" not in p1.section  # Must not cite Chapter IV
    assert "DBR.AML.BC.No.81/14.01.001/2015-16" in p1.reference_code

    # 2. POL_RBI_KYC_NAME_MATCH_002
    p2 = PolicyKnowledgeService.get_policy_by_id("POL_RBI_KYC_NAME_MATCH_002")
    assert p2 is not None
    assert "Paragraph 10" in p2.section or "Paragraph 13" in p2.section
    assert "Section 17" not in p2.section  # Must not cite bogus Section 17
    assert "fictitious" in p2.text.lower() or "benami" in p2.text.lower()

    # 3. POL_RBI_CREDIT_DUE_DILIGENCE_003
    p3 = PolicyKnowledgeService.get_policy_by_id("POL_RBI_CREDIT_DUE_DILIGENCE_003")
    assert p3 is not None
    assert "DoR.FIN.REC.No.55/20.16.056/2024-25" in p3.reference_code
    assert "Credit Information Reporting" in p3.title

    # 4. POL_RBI_FAIR_PRACTICES_004
    p4 = PolicyKnowledgeService.get_policy_by_id("POL_RBI_FAIR_PRACTICES_004")
    assert p4 is not None
    assert "DBOD. Leg. No.BC. 104" in p4.reference_code
    assert "Clause 2(a)" in p4.section

    # 5. POL_RBI_DIGITAL_LENDING_005
    p5 = PolicyKnowledgeService.get_policy_by_id("POL_RBI_DIGITAL_LENDING_005")
    assert p5 is not None
    assert "DOR.CRE.REC.66/21.07.001/2022-23" in p5.reference_code
    assert "Clause 1.1" in p5.section


def test_rbi_policies_no_unsupported_zero_tolerance_claims():
    """Verify that RBI policies do not invent unsupported absolute rules like 'zero tolerance' or 'must reject'."""
    rbi_policies = PolicyKnowledgeService.get_policies_by_source("RBI")
    unsupported_phrases = [
        "zero discrepancy",
        "zero tolerance",
        "zero-tolerance",
        "zero unauthorized alias deviation",
        "mandatory loan rejection",
    ]
    for p in rbi_policies:
        for phrase in unsupported_phrases:
            assert phrase not in p.text.lower(), f"Policy {p.policy_id} contains unsupported claim: '{phrase}'"
            assert phrase not in p.description.lower(), f"Policy {p.policy_id} description contains unsupported claim: '{phrase}'"

    # POL_RBI_KYC_OVD_001 explicitly mentions allowed name change with marriage certificate or Gazette notification
    p1 = PolicyKnowledgeService.get_policy_by_id("POL_RBI_KYC_OVD_001")
    assert "marriage certificate" in p1.text.lower()
    assert "gazette notification" in p1.text.lower()


# ── TEST 5: HDFC Public Policies Labeling ────────────────────────────────────

def test_hdfc_public_policies_labeling():
    """Verify public HDFC policies are source=HDFC_BANK, authority=HDFC_BANK, and is_simulated=False with official HDFC URLs."""
    hdfc_public = PolicyKnowledgeService.get_policies_by_source("HDFC_BANK")
    assert len(hdfc_public) == 2
    expected_ids = {"POL_HDFC_PUB_DOCS_001", "POL_HDFC_PUB_CREDITWORTHINESS_003"}
    found_ids = {p.policy_id for p in hdfc_public}
    assert expected_ids == found_ids

    for p in hdfc_public:
        assert p.source == "HDFC_BANK"
        assert p.is_simulated is False
        assert p.authority == "HDFC_BANK"
        assert p.official_url is not None and p.official_url.startswith("https://www.hdfcbank.com")
        assert "personal" in p.applicability.lower() or "salaried" in p.applicability.lower()


def test_hdfc_public_policies_no_internal_underwriting_claims():
    """Verify that HDFC_BANK policies do not make unsupported internal underwriting claims."""
    hdfc_public = PolicyKnowledgeService.get_policies_by_source("HDFC_BANK")
    unsupported_internal_claims = [
        "standard deduction tolerances",
        "unverified cash deposits",
        "absence of write-offs or settlements",
        "absence requires follow-up before underwriting",
        "must correspond directly",
    ]
    for p in hdfc_public:
        for claim in unsupported_internal_claims:
            assert claim not in p.text.lower(), f"Public policy {p.policy_id} contains unsupported internal claim: '{claim}'"
            assert claim not in p.description.lower(), f"Public policy {p.policy_id} description contains unsupported internal claim: '{claim}'"


# ── TEST 6 & 7: HDFC Internal Demo Rules Labeling & Simulation Flag ──────────

def test_hdfc_internal_demo_rules_labeling_and_simulation_flag():
    """Verify internal underwriting demo rules are source=HDFC_INTERNAL_DEMO with is_simulated=True."""
    demo_policies = PolicyKnowledgeService.get_policies_by_source("HDFC_INTERNAL_DEMO")
    assert len(demo_policies) == 6
    expected_demo_ids = {
        "POL_HDFC_DEMO_TAX_RETURN_001",
        "POL_HDFC_DEMO_INCOME_DISCREPANCY_002",
        "POL_HDFC_DEMO_IDENTITY_MISMATCH_003",
        "POL_HDFC_DEMO_HIGH_RISK_ESCALATION_004",
        "POL_HDFC_DEMO_MISSING_DOCS_005",
        "POL_HDFC_DEMO_INCOME_VERIFY_002",
    }
    found_demo_ids = {p.policy_id for p in demo_policies}
    assert expected_demo_ids == found_demo_ids

    for p in demo_policies:
        assert p.source == "HDFC_INTERNAL_DEMO"
        assert p.is_simulated is True
        assert p.authority == "INTERNAL_RISK_COMMITTEE"
        assert "[SIMULATED DEMO RULE]" in p.text or "Simulated" in p.title


# ── TEST 8: Policy Lookup by ID ──────────────────────────────────────────────

def test_policy_lookup_by_id():
    """Verify exact policy retrieval by policy_id across all sources."""
    # Test RBI policy
    p_rbi = PolicyKnowledgeService.get_policy_by_id("POL_RBI_KYC_OVD_001")
    assert p_rbi is not None
    assert p_rbi.source == "RBI"
    assert "Officially Valid Documents" in p_rbi.title

    # Test HDFC public policy
    p_pub = PolicyKnowledgeService.get_policy_by_id("POL_HDFC_PUB_DOCS_001")
    assert p_pub is not None
    assert p_pub.source == "HDFC_BANK"

    # Test HDFC internal demo policy
    p_demo = PolicyKnowledgeService.get_policy_by_id("POL_HDFC_DEMO_IDENTITY_MISMATCH_003")
    assert p_demo is not None
    assert p_demo.source == "HDFC_INTERNAL_DEMO"
    assert p_demo.is_simulated is True

    # Non-existent ID returns None
    assert PolicyKnowledgeService.get_policy_by_id("NON_EXISTENT_ID") is None


# ── TEST 9: Policy Filtering by Source ───────────────────────────────────────

def test_policy_filtering_by_source():
    """Verify strict filtering by source preserves complete partition."""
    rbi = PolicyKnowledgeService.get_policies_by_source("RBI")
    hdfc_bank = PolicyKnowledgeService.get_policies_by_source("HDFC_BANK")
    hdfc_demo = PolicyKnowledgeService.get_policies_by_source("HDFC_INTERNAL_DEMO")

    total = PolicyKnowledgeService.get_all_policies()
    assert len(rbi) + len(hdfc_bank) + len(hdfc_demo) == len(total)


# ── TEST 10: Policy Filtering by Category ────────────────────────────────────

def test_policy_filtering_by_category():
    """Verify category filtering for core review domains."""
    kyc_policies = PolicyKnowledgeService.get_policies_by_category("KYC")
    assert len(kyc_policies) >= 1
    for p in kyc_policies:
        assert p.category == "KYC"

    doc_policies = PolicyKnowledgeService.get_policies_by_category("DOCUMENTATION")
    assert len(doc_policies) >= 2

    esc_policies = PolicyKnowledgeService.get_policies_by_category("ESCALATION")
    assert len(esc_policies) >= 1
    assert any("IDENTITY" in p.rule for p in esc_policies)


# ── TEST 11: Provenance Completeness ─────────────────────────────────────────

def test_provenance_completeness():
    """Verify every policy has sufficient provenance metadata."""
    for p in PolicyKnowledgeService.get_all_policies():
        assert p.source in ("RBI", "HDFC_BANK", "HDFC_INTERNAL_DEMO")
        assert p.authority is not None
        assert p.reference_code is not None
        assert len(p.section) > 0


# ── TEST 12: Distinct Separation (No False Claims) ───────────────────────────

def test_rbi_and_hdfc_demo_distinguishability():
    """Verify that simulated thresholds are NEVER assigned source='RBI' or source='HDFC_BANK'."""
    for p in PolicyKnowledgeService.get_all_policies():
        if p.is_simulated:
            assert p.source == "HDFC_INTERNAL_DEMO"
            assert p.source != "RBI"
            assert p.source != "HDFC_BANK"
        if p.source in ("RBI", "HDFC_BANK"):
            assert p.is_simulated is False


# ── TEST 13: No Phase 14 Components in PolicyKnowledgeService ────────────────

def test_no_phase14_components_in_knowledge_service():
    """Verify Phase 13 service does not import FAISS, sentence-transformers, or vector store."""
    import app.services.policy_knowledge_service as pks_module
    with open(pks_module.__file__, "r", encoding="utf-8") as f:
        import_lines = [line.strip().lower() for line in f if line.strip().startswith(("import ", "from "))]

    imports_text = "\n".join(import_lines)
    assert "faiss" not in imports_text
    assert "sentence_transformers" not in imports_text
    assert "vector_store" not in imports_text


# ── TEST 14: REST API Endpoints ──────────────────────────────────────────────

def test_policy_knowledge_api_endpoints():
    """Verify REST API endpoints for Phase 13 Policy Knowledge Base."""
    # 1. Summary endpoint
    res_sum = client.get("/api/v1/policies/knowledge/summary")
    assert res_sum.status_code == 200
    sum_data = res_sum.json()
    assert sum_data["total_policies"] >= 12
    assert sum_data["rbi_policy_count"] >= 4

    # 2. Filter by source=RBI
    res_rbi = client.get("/api/v1/policies?source=RBI")
    assert res_rbi.status_code == 200
    rbi_items = res_rbi.json()
    assert len(rbi_items) >= 4
    assert all(item["source"] == "RBI" for item in rbi_items)

    # 3. Filter by source=HDFC_BANK
    res_hdfc = client.get("/api/v1/policies?source=HDFC_BANK")
    assert res_hdfc.status_code == 200
    hdfc_items = res_hdfc.json()
    assert len(hdfc_items) == 2
    assert all(item["source"] == "HDFC_BANK" for item in hdfc_items)

    # 4. Filter by source=HDFC_INTERNAL_DEMO
    res_demo = client.get("/api/v1/policies?source=HDFC_INTERNAL_DEMO")
    assert res_demo.status_code == 200
    demo_items = res_demo.json()
    assert len(demo_items) == 6
    assert all(item["is_simulated"] is True for item in demo_items)

    # 5. Filter by category=KYC
    res_cat = client.get("/api/v1/policies?category=KYC")
    assert res_cat.status_code == 200
    cat_items = res_cat.json()
    assert len(cat_items) >= 1
    assert all(item["category"] == "KYC" for item in cat_items)

    # 6. Single policy retrieval by ID
    res_single = client.get("/api/v1/policies/POL_RBI_KYC_OVD_001")
    assert res_single.status_code == 200
    single_item = res_single.json()
    assert single_item["policy_id"] == "POL_RBI_KYC_OVD_001"
    assert single_item["source"] == "RBI"
