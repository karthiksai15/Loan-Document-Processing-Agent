"""
Unit and Integration Tests for Phase 13 — Policy Knowledge Base

Verifies:
1. Default seeding of 4 RBI Regulatory documents and 1 Internal Underwriting document.
2. Strict separation between statutory RBI rules and internal bank underwriting cutoffs.
3. Source, version, chapter, section, and page traceability.
4. Phase 14 indexing payload extraction interface.
5. REST API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.db.models import PolicyDocumentModel, PolicySectionModel, PolicyRuleModel
from app.services.policy_service import PolicyService
from app.schemas.policy import PolicyDocumentCreate, PolicySectionCreate, PolicyRuleCreate


@pytest.fixture(autouse=True)
def db():
    """Provides a clean database session for policy tests."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    # Clean policy tables to guarantee test isolation
    session.query(PolicyRuleModel).delete()
    session.query(PolicySectionModel).delete()
    session.query(PolicyDocumentModel).delete()
    session.commit()

    try:
        yield session
    finally:
        session.query(PolicyRuleModel).delete()
        session.query(PolicySectionModel).delete()
        session.query(PolicyDocumentModel).delete()
        session.commit()
        session.close()


def test_seed_policies(db: Session):
    """Test seeding default RBI regulatory and internal underwriting policies."""
    result = PolicyService.seed_policies(db)
    assert result.status == "SUCCESS"
    assert result.documents_ingested == 5
    assert result.sections_ingested >= 12
    assert result.rules_ingested >= 7

    # Verify duplicate seeding is idempotent
    result2 = PolicyService.seed_policies(db)
    assert result2.documents_ingested == 0


def test_strict_regulatory_vs_underwriting_separation(db: Session):
    """
    Test strict separation:
    - 4 RBI documents must be tagged REGULATORY & RBI.
    - Internal underwriting document must be tagged INTERNAL_UNDERWRITING & INTERNAL_BANK.
    - No RBI document contains synthetic bank thresholds (FOIR, income, CIBIL cutoff).
    """
    PolicyService.seed_policies(db)

    # 1. Query regulatory docs
    reg_docs = PolicyService.list_policies(db, policy_type="REGULATORY")
    assert len(reg_docs) == 4
    for doc in reg_docs:
        assert doc.authority == "RBI"
        assert doc.policy_type == "REGULATORY"

    # 2. Query internal underwriting docs
    underwriting_docs = PolicyService.list_policies(db, policy_type="INTERNAL_UNDERWRITING")
    assert len(underwriting_docs) == 1
    uw_doc = underwriting_docs[0]
    assert uw_doc.policy_doc_id == "POL_INT_UNDERWRITING_2025"
    assert uw_doc.authority == "INTERNAL_BANK"

    # 3. Check rules separation
    reg_rules = PolicyService.list_rules(db, is_regulatory=True)
    rule_codes = [r.rule_code for r in reg_rules]
    assert "OVD_LIST_CHECK" in rule_codes
    assert "DIRECT_ACCOUNT_TRANSFER" in rule_codes
    assert "CREDIT_DISPUTE_MAX_DAYS" in rule_codes
    # Ensure no internal underwriting threshold exists in regulatory rules
    assert "MAX_FOIR_THRESHOLD" not in rule_codes
    assert "MIN_MONTHLY_INCOME_THRESHOLD" not in rule_codes
    assert "MIN_CIBIL_SCORE_THRESHOLD" not in rule_codes

    internal_rules = PolicyService.list_rules(db, is_regulatory=False)
    int_rule_codes = [r.rule_code for r in internal_rules]
    assert "MAX_FOIR_THRESHOLD" in int_rule_codes
    assert "MIN_MONTHLY_INCOME_THRESHOLD" in int_rule_codes
    assert "MIN_CIBIL_SCORE_THRESHOLD" in int_rule_codes


def test_source_section_page_traceability(db: Session):
    """Test retrieving section with complete parent document, page, and version traceability."""
    PolicyService.seed_policies(db)

    traceability = PolicyService.get_section_traceability(db, "SEC_KYC_CH4_16")
    assert traceability is not None
    assert traceability["section_id"] == "SEC_KYC_CH4_16"
    assert traceability["policy_doc_id"] == "POL_RBI_KYC_2016"
    assert traceability["policy_title"] == "Master Direction - Know Your Customer (KYC) Direction, 2016"
    assert traceability["authority"] == "RBI"
    assert traceability["policy_type"] == "REGULATORY"
    assert traceability["version"] == "2025-08-14"
    assert traceability["reference_code"] == "RBI/DBR/2015-16/18 DBR.AML.BC.No.81/14.01.001/2015-16"
    assert traceability["chapter_or_part"] == "Chapter IV"
    assert traceability["section_number"] == "Section 16"
    assert traceability["page_number"] == 14
    assert "Officially Valid Documents" in traceability["content_text"]


def test_ingest_custom_policy_validation(db: Session):
    """Test ingestion validation rules for policy documents."""
    # Attempting to register an RBI document as INTERNAL_UNDERWRITING must fail
    invalid_doc = PolicyDocumentCreate(
        policy_doc_id="POL_INVALID_RBI",
        title="Invalid RBI Policy",
        policy_type="INTERNAL_UNDERWRITING",
        authority="RBI",
        category="KYC",
        version="1.0",
    )
    with pytest.raises(ValueError, match="All RBI policy documents must have policy_type='REGULATORY'"):
        PolicyService.ingest_policy_document(db, invalid_doc)


def test_phase14_indexing_payload_consumer(db: Session):
    """Test the Phase 14 vector store indexing payload extraction interface."""
    PolicyService.seed_policies(db)

    indexing_payload = PolicyService.get_all_sections_for_indexing(db)
    assert len(indexing_payload) >= 12

    first = indexing_payload[0]
    required_keys = [
        "section_id",
        "policy_doc_id",
        "policy_title",
        "policy_type",
        "authority",
        "category",
        "version",
        "reference_code",
        "official_url",
        "source_filename",
        "chapter_or_part",
        "section_number",
        "section_title",
        "page_number",
        "content_text",
        "summary",
    ]
    for key in required_keys:
        assert key in first


def test_policy_api_endpoints(db: Session):
    """Test Policy Knowledge Base REST API endpoints."""
    client = TestClient(app)

    # 1. Seed API
    res_seed = client.post("/api/v1/policies/seed")
    assert res_seed.status_code == 200
    assert res_seed.json()["status"] == "SUCCESS"

    # 2. List policies API
    res_list = client.get("/api/v1/policies?policy_type=REGULATORY")
    assert res_list.status_code == 200
    docs = res_list.json()
    assert len(docs) == 4

    # 3. Get single policy API
    res_single = client.get("/api/v1/policies/POL_RBI_DIGITAL_LENDING_2022")
    assert res_single.status_code == 200
    single_doc = res_single.json()
    assert single_doc["title"] == "Guidelines on Digital Lending"
    assert len(single_doc["sections"]) == 3

    # 4. Section traceability API
    res_sec = client.get("/api/v1/policies/sections/SEC_DL_KFS_05")
    assert res_sec.status_code == 200
    sec_data = res_sec.json()
    assert sec_data["policy_title"] == "Guidelines on Digital Lending"
    assert sec_data["page_number"] == 5

    # 5. List rules API
    res_rules = client.get("/api/v1/policies/rules/all?is_regulatory=true")
    assert res_rules.status_code == 200
    rules = res_rules.json()
    assert len(rules) >= 4
