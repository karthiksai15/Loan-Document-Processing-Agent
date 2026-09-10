"""
Unit and Integration Tests for Phase 14 — Policy RAG

Verifies:
1. Policy chunking & 100% provenance preservation from Phase 13 policies.
2. Local SentenceTransformer embedding generation.
3. FAISS index building, persistence, loading, rebuilding.
4. Semantic policy retrieval, Top-K ranking, similarity scoring.
5. Metadata filtering (source, is_simulated, authority, policy_type, category, policy_id).
6. Strict Regulatory vs Internal Demo distinction (simulated rules are NEVER attributed to RBI).
7. Citation and source traceability across all 13 policies.
8. Retrieval testing for the 4 core review queries.
9. Retrieval verification for the 4 demo scenarios (A003, A004, A006, A007).
10. REST API endpoints.
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.services.policy_knowledge_service import PolicyKnowledgeService
from app.services.policy_chunking_service import PolicyChunkingService
from app.services.policy_embedding_service import PolicyEmbeddingService
from app.services.policy_vector_store import PolicyVectorStore
from app.services.policy_rag_service import PolicyRAGService
from app.schemas.policy_rag import PolicySearchRequest


@pytest.fixture(autouse=True)
def db():
    """Provides a clean database session for policy RAG tests."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def np_norm(vec):
    import numpy as np
    return np.linalg.norm(vec)


# ── TEST 1: Policy Chunking & Metadata Preservation ──────────────────────────

def test_policy_chunking_metadata_preservation():
    """Test policy item chunking and 100% metadata preservation from Phase 13."""
    policies = PolicyKnowledgeService.load_policies(force_reload=True)
    assert len(policies) == 13

    chunks = PolicyChunkingService.chunk_all_policies(policies)
    assert len(chunks) >= 13

    for c in chunks:
        assert c["policy_id"]
        assert c["source"] in ("RBI", "HDFC_BANK", "HDFC_INTERNAL_DEMO")
        assert c["title"]
        assert c["category"]
        assert c["section"]
        assert c["rule"]
        assert c["description"]
        assert c["text"]
        assert c["applicability"]
        assert isinstance(c["is_simulated"], bool)
        assert c["authority"]
        assert c["reference_code"]
        assert c["version"]
        assert len(c["content"]) > 0

        # Verify backward-compatible mappings
        assert c["policy_document_id"] == c["policy_id"]
        assert c["policy_name"] == c["title"]
        assert c["source_authority"] == c["authority"]


# ── TEST 2: Local SentenceTransformer Embedding Generation ───────────────────

def test_embedding_generation():
    """Test local SentenceTransformers embedding generation."""
    text = "Officially Valid Documents for customer identification"
    vec = PolicyEmbeddingService.embed_text(text)
    dim = PolicyEmbeddingService.get_embedding_dimension()

    assert vec is not None
    assert vec.shape == (dim,)
    assert dim == 384
    # Verify vector is L2 normalized (norm approximately 1.0)
    norm = float(np_norm(vec))
    assert norm == pytest.approx(1.0, abs=1e-3)


# ── TEST 3: FAISS Vector Store Lifecycle ─────────────────────────────────────

def test_faiss_vector_store_lifecycle():
    """Test building, saving, loading, and searching FAISS vector index."""
    policies = PolicyKnowledgeService.load_policies(force_reload=True)
    chunks = PolicyChunkingService.chunk_all_policies(policies)
    texts = [c["content"] for c in chunks]

    embeddings = PolicyEmbeddingService.embed_batch(texts)
    model_name = PolicyEmbeddingService.get_model_name()

    store = PolicyVectorStore()
    manifest = store.build_and_save_index(chunks, embeddings, model_name)

    assert manifest["chunk_count"] == len(chunks)
    assert manifest["model_name"] == model_name
    assert os.path.exists(store.index_file)
    assert os.path.exists(store.manifest_file)
    assert store.is_index_valid(model_name) is True

    # Test loading from disk
    store_loaded = PolicyVectorStore()
    assert store_loaded.load_index() is True
    assert len(store_loaded.chunks_map) == len(chunks)

    # Test searching
    query_vec = PolicyEmbeddingService.embed_text("Officially Valid Documents OVD Aadhaar")
    results = store_loaded.search(query_vec, top_k=3)
    assert len(results) > 0
    top_chunk, score = results[0]
    assert "chunk_id" in top_chunk
    assert score > 0.0


# ── TEST 4: Policy RAG Index Rebuild ─────────────────────────────────────────

def test_policy_rag_index_rebuild(db: Session):
    """Test PolicyRAGService.rebuild_index pipeline from Phase 13 JSON dataset."""
    res = PolicyRAGService.rebuild_index(db)
    assert res.status == "SUCCESS"
    assert res.chunks_indexed >= 13
    assert res.dimension == 384
    assert res.source_counts == {"RBI": 5, "HDFC_BANK": 2, "HDFC_INTERNAL_DEMO": 6}
    assert os.path.exists(res.index_path)
    assert os.path.exists(res.manifest_path)


# ── TEST 5: Semantic Search KYC & Regulatory Query ───────────────────────────

def test_semantic_search_kyc_query(db: Session):
    """Test semantic search for customer identity verification query."""
    req = PolicySearchRequest(
        query="What policy governs customer identity verification?",
        top_k=3,
    )
    res = PolicyRAGService.search_policies(db, req)
    assert res.total_results > 0
    first = res.results[0]

    # Verify top result is from official KYC policies
    assert first.citation.authority in ("RBI", "INTERNAL_RISK_COMMITTEE")
    assert first.similarity_score > 0.30


# ── TEST 6: Semantic Search Digital Lending Query ────────────────────────────

def test_semantic_search_digital_lending_query(db: Session):
    """Test semantic search for digital lending direct disbursement guidelines."""
    req = PolicySearchRequest(
        query="What are the requirements related to digital lending direct bank account disbursements?",
        top_k=3,
    )
    res = PolicyRAGService.search_policies(db, req)
    assert res.total_results > 0
    first = res.results[0]

    assert first.citation.authority == "RBI"
    assert first.citation.policy_type == "REGULATORY"
    assert "POL_RBI_DIGITAL_LENDING_005" in first.citation.policy_id
    assert "Annex I" in (first.citation.section_reference or "")


# ── TEST 7: Strict Attribution Separation ────────────────────────────────────

def test_semantic_search_strict_attribution(db: Session):
    """
    CRITICAL TEST:
    Simulated demo underwriting rules must NEVER be attributed to RBI or marked is_simulated=False.
    """
    req = PolicySearchRequest(
        query="What is the simulated escalation rule when payslip variance exceeds 10%?",
        top_k=3,
    )
    res = PolicyRAGService.search_policies(db, req)
    assert res.total_results > 0
    first = res.results[0]

    assert first.citation.source == "HDFC_INTERNAL_DEMO"
    assert first.citation.authority == "INTERNAL_RISK_COMMITTEE"
    assert first.citation.is_simulated is True
    assert first.citation.authority != "RBI"


# ── TEST 8: Metadata Filtering (Source, is_simulated, Category) ──────────────

def test_metadata_filtering(db: Session):
    """Test applying metadata filters during semantic retrieval."""
    # 1. Filter strictly for RBI
    req_rbi = PolicySearchRequest(
        query="customer due diligence officially valid documents",
        top_k=5,
        source="RBI",
    )
    res_rbi = PolicyRAGService.search_policies(db, req_rbi)
    assert res_rbi.total_results > 0
    for item in res_rbi.results:
        assert item.citation.source == "RBI"
        assert item.citation.authority == "RBI"
        assert item.citation.is_simulated is False

    # 2. Filter strictly for HDFC_BANK
    req_hdfc = PolicySearchRequest(
        query="documentation checklist",
        top_k=5,
        source="HDFC_BANK",
    )
    res_hdfc = PolicyRAGService.search_policies(db, req_hdfc)
    assert res_hdfc.total_results > 0
    for item in res_hdfc.results:
        assert item.citation.source == "HDFC_BANK"
        assert item.citation.is_simulated is False

    # 3. Filter strictly for is_simulated=True
    req_sim = PolicySearchRequest(
        query="escalation rule",
        top_k=5,
        is_simulated=True,
    )
    res_sim = PolicyRAGService.search_policies(db, req_sim)
    assert res_sim.total_results > 0
    for item in res_sim.results:
        assert item.citation.is_simulated is True
        assert item.citation.source == "HDFC_INTERNAL_DEMO"


# ── TEST 9: User Review Queries ──────────────────────────────────────────────

def test_user_retrieval_queries(db: Session):
    """Verify the 4 required review queries retrieve relevant policies."""
    queries = [
        ("What documents are required for a salaried personal loan?", "POL_HDFC_PUB_DOCS_001"),
        ("What policy applies when salary evidence does not match the bank statement?", "POL_HDFC_DEMO_INCOME_DISCREPANCY_002"),
        ("What should be checked when the applicant name does not match the KYC document?", "POL_HDFC_DEMO_IDENTITY_MISMATCH_003"),
        ("What policies are relevant when credit risk is high and income evidence is inconsistent?", "POL_HDFC_DEMO_HIGH_RISK_ESCALATION_004"),
    ]
    for q, expected_id in queries:
        req = PolicySearchRequest(query=q, top_k=3)
        res = PolicyRAGService.search_policies(db, req)
        assert res.total_results > 0
        retrieved_ids = [item.citation.policy_id for item in res.results]
        assert expected_id in retrieved_ids, f"Expected {expected_id} in {retrieved_ids} for query '{q}'"


# ── TEST 10: Demo Scenarios A003, A004, A006, A007 ──────────────────────────

def test_demo_scenario_retrievals(db: Session):
    """Verify retrieval accuracy for demo application scenarios."""
    scenarios = [
        ("A003 missing tax return ITR Form 16 document follow-up", "POL_HDFC_DEMO_TAX_RETURN_001"),
        ("A004 salary credit variance payslip bank statement discrepancy", "POL_HDFC_DEMO_INCOME_DISCREPANCY_002"),
        ("A006 applicant identity mismatch KYC name variance officer investigation", "POL_HDFC_DEMO_IDENTITY_MISMATCH_003"),
        ("A007 high historical rejection risk financial discrepancy underwriting escalation", "POL_HDFC_DEMO_HIGH_RISK_ESCALATION_004"),
    ]
    for q, expected_id in scenarios:
        req = PolicySearchRequest(query=q, top_k=3)
        res = PolicyRAGService.search_policies(db, req)
        assert res.total_results > 0
        top_id = res.results[0].citation.policy_id
        assert top_id == expected_id, f"Scenario '{q}' expected top rank {expected_id}, got {top_id}"


# ── TEST 11: Empty Query Handling ────────────────────────────────────────────

def test_empty_query_handling(db: Session):
    """Test handling empty search query cleanly."""
    req = PolicySearchRequest(query="", top_k=5)
    res = PolicyRAGService.search_policies(db, req)
    assert res.total_results == 0
    assert res.results == []


# ── TEST 12: REST API Endpoints ──────────────────────────────────────────────

def test_policy_rag_api_endpoints(db: Session):
    """Test REST API endpoints for index rebuild and semantic search."""
    client = TestClient(app)

    # 1. Rebuild index API
    res_rebuild = client.post("/api/v1/policies/index/rebuild")
    assert res_rebuild.status_code == 200
    data_rebuild = res_rebuild.json()
    assert data_rebuild["status"] == "SUCCESS"
    assert data_rebuild["chunks_indexed"] >= 13

    # 2. Search API with source filter
    payload = {
        "query": "What officially valid documents are accepted for KYC verification?",
        "top_k": 3,
        "source": "RBI",
    }
    res_search = client.post("/api/v1/policies/search", json=payload)
    assert res_search.status_code == 200
    data_search = res_search.json()
    assert data_search["query"] == payload["query"]
    assert data_search["total_results"] > 0

    first_res = data_search["results"][0]
    assert first_res["citation"]["authority"] == "RBI"
    assert first_res["citation"]["source"] == "RBI"
    assert first_res["citation"]["is_simulated"] is False
