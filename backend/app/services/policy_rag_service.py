"""
Policy RAG Service (Phase 14)

Orchestrates policy index rebuilding, semantic vector search, metadata filtering,
top-K ranking, similarity scoring, and source/citation traceability.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.services.policy_knowledge_service import PolicyKnowledgeService
from app.services.policy_chunking_service import PolicyChunkingService
from app.services.policy_embedding_service import PolicyEmbeddingService
from app.services.policy_vector_store import PolicyVectorStore
from app.schemas.policy_rag import (
    PolicySearchRequest,
    PolicySearchResponse,
    PolicySearchResultItem,
    PolicyCitation,
    PolicyIndexRebuildResponse,
)
from app.core.logging import logger


class PolicyRAGService:
    _vector_store_instance: Optional[PolicyVectorStore] = None

    @classmethod
    def get_vector_store(cls) -> PolicyVectorStore:
        """Returns singleton instance of PolicyVectorStore."""
        if cls._vector_store_instance is None:
            cls._vector_store_instance = PolicyVectorStore()
        return cls._vector_store_instance

    @classmethod
    def rebuild_index(cls, db: Optional[Session] = None) -> PolicyIndexRebuildResponse:
        """
        Rebuilds the complete Policy RAG FAISS index from the Phase 13 Policy Knowledge Base data
        (data/policies/rbi_policies.json, hdfc_public_policies.json, hdfc_internal_demo_policies.json).
        """
        # 1. Fetch authoritative policies from Phase 13 Policy Knowledge Base
        policies = PolicyKnowledgeService.load_policies(force_reload=True)
        logger.info(f"Building Policy RAG index from {len(policies)} Phase 13 policy documents.")

        source_counts = {
            "RBI": sum(1 for p in policies if p.source == "RBI"),
            "HDFC_BANK": sum(1 for p in policies if p.source == "HDFC_BANK"),
            "HDFC_INTERNAL_DEMO": sum(1 for p in policies if p.source == "HDFC_INTERNAL_DEMO"),
        }

        # 2. Chunk policies into retrieval units preserving full provenance metadata
        chunks = PolicyChunkingService.chunk_all_policies(policies)

        # 3. Generate embeddings using local SentenceTransformer
        texts_to_embed = [c["content"] for c in chunks]
        embeddings = PolicyEmbeddingService.embed_batch(texts_to_embed)
        model_name = PolicyEmbeddingService.get_model_name()
        dimension = PolicyEmbeddingService.get_embedding_dimension()

        # 4. Build and save FAISS index + manifest
        vector_store = cls.get_vector_store()
        manifest = vector_store.build_and_save_index(chunks, embeddings, model_name)

        return PolicyIndexRebuildResponse(
            status="SUCCESS",
            chunks_indexed=len(chunks),
            embedding_model=model_name,
            dimension=dimension,
            index_path=vector_store.index_file,
            manifest_path=vector_store.manifest_file,
            message=f"Successfully built and persisted FAISS index with {len(chunks)} policy chunks.",
            source_counts=source_counts,
        )

    @classmethod
    def search_policies(cls, db: Optional[Session], request: PolicySearchRequest) -> PolicySearchResponse:
        """
        Executes semantic policy retrieval using FAISS vector search, applies metadata filtering,
        ranks results, and attaches complete citation traceability.
        """
        query = (request.query or "").strip()
        if not query:
            return PolicySearchResponse(
                query=request.query,
                total_results=0,
                results=[],
                filters_applied=request.model_dump(exclude_none=True),
            )

        vector_store = cls.get_vector_store()
        model_name = PolicyEmbeddingService.get_model_name()

        # Ensure index exists and is valid
        if not vector_store.is_index_valid(model_name):
            logger.info("FAISS policy index missing or outdated. Automatically rebuilding index...")
            cls.rebuild_index(db)

        # 1. Embed query using local SentenceTransformer
        query_vec = PolicyEmbeddingService.embed_text(query)

        # 2. Vector search candidate pool
        candidate_pool_size = max(request.top_k * 4, 20)
        candidate_tuples = vector_store.search(query_vec, top_k=candidate_pool_size)

        # 3. Apply Metadata Filtering
        filtered_results: List[PolicySearchResultItem] = []
        rank_counter = 1

        filters_applied = {}
        if request.source:
            filters_applied["source"] = request.source
        if request.is_simulated is not None:
            filters_applied["is_simulated"] = request.is_simulated
        if request.policy_type:
            filters_applied["policy_type"] = request.policy_type
        if request.authority:
            filters_applied["authority"] = request.authority
        if request.category:
            filters_applied["category"] = request.category
        if request.policy_id:
            filters_applied["policy_id"] = request.policy_id

        for chunk_meta, sim_score in candidate_tuples:
            # Metadata filter checks
            if request.source and chunk_meta.get("source") != request.source:
                continue
            if request.is_simulated is not None and chunk_meta.get("is_simulated") != request.is_simulated:
                continue
            if request.policy_type and chunk_meta.get("policy_type") != request.policy_type:
                continue
            if request.authority and chunk_meta.get("source_authority") != request.authority and chunk_meta.get("authority") != request.authority:
                continue
            if request.category and chunk_meta.get("category") != request.category:
                continue
            if request.policy_id and chunk_meta.get("policy_id") != request.policy_id and chunk_meta.get("policy_document_id") != request.policy_id:
                continue

            canonical_policy_id = chunk_meta.get("policy_id") or chunk_meta.get("policy_document_id", "UNKNOWN")

            # Construct Citation object with full Phase 13/14 provenance
            citation = PolicyCitation(
                policy_id=canonical_policy_id,
                policy_name=chunk_meta.get("title") or chunk_meta.get("policy_name", "UNKNOWN"),
                authority=chunk_meta.get("authority") or chunk_meta.get("source_authority", "UNKNOWN"),
                policy_type=chunk_meta.get("policy_type", "REGULATORY" if chunk_meta.get("source") == "RBI" else "INTERNAL_UNDERWRITING"),
                section_id=canonical_policy_id,
                section_title=chunk_meta.get("title") or chunk_meta.get("section_title", "UNKNOWN"),
                section_reference=chunk_meta.get("section") or chunk_meta.get("section_reference"),
                chapter_or_part=chunk_meta.get("section") or chunk_meta.get("chapter_or_part"),
                page_number=chunk_meta.get("page_number"),
                source_document=chunk_meta.get("reference_code") or chunk_meta.get("source_document"),
                source_url=chunk_meta.get("official_url") or chunk_meta.get("source_url"),
                version=chunk_meta.get("version", "1.0"),
                reference_code=chunk_meta.get("reference_code"),
                effective_date=chunk_meta.get("effective_date") or chunk_meta.get("version"),
                source=chunk_meta.get("source"),
                rule=chunk_meta.get("rule"),
                category=chunk_meta.get("category"),
                is_simulated=chunk_meta.get("is_simulated", False),
                applicability=chunk_meta.get("applicability"),
                description=chunk_meta.get("description"),
            )

            item = PolicySearchResultItem(
                rank=rank_counter,
                chunk_id=chunk_meta["chunk_id"],
                content=chunk_meta.get("text") or chunk_meta.get("content") or chunk_meta.get("content_text", ""),
                similarity_score=round(float(sim_score), 4),
                score_type="COSINE_SIMILARITY",
                citation=citation,
            )
            filtered_results.append(item)
            rank_counter += 1

            if len(filtered_results) >= request.top_k:
                break

        return PolicySearchResponse(
            query=query,
            total_results=len(filtered_results),
            results=filtered_results,
            filters_applied=filters_applied,
        )
