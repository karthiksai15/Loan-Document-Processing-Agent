"""
LLM Grounding Service — Phase 15 GenAI Foundation

Validates that evidence node IDs and policy section IDs cited by the LLM
actually exist in the database for the given application.

This prevents hallucinated citations from reaching the persisted review.
"""

from typing import List, Tuple, Optional
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.models import EvidenceNodeModel, PolicySectionModel


def validate_evidence_citations(
    application_id: str,
    cited_node_ids: List[str],
    db: Session,
) -> Tuple[List[str], List[str]]:
    """
    Checks each cited evidence node ID against the database.

    Args:
        application_id: The loan application being reviewed.
        cited_node_ids: Node IDs returned by the LLM.
        db:             SQLAlchemy session.

    Returns:
        (valid_ids, invalid_ids)
    """
    if not cited_node_ids:
        return [], []

    existing = {
        row.node_id
        for row in db.query(EvidenceNodeModel.node_id).filter(
            EvidenceNodeModel.application_id == application_id,
            EvidenceNodeModel.node_id.in_(cited_node_ids),
        ).all()
    }

    valid = [nid for nid in cited_node_ids if nid in existing]
    invalid = [nid for nid in cited_node_ids if nid not in existing]

    if invalid:
        logger.warning(
            f"LLM Grounding: {len(invalid)} invalid evidence node ID(s) for '{application_id}': {invalid}"
        )

    return valid, invalid


def get_canonical_policy_ids(db: Optional[Session] = None) -> set:
    """Returns all canonical policy and section IDs from Phase 13/14 knowledge base and DB."""
    canonical_ids = set()

    # 1. Phase 13 Policy Knowledge Base (authoritative JSON files)
    try:
        from app.services.policy_knowledge_service import PolicyKnowledgeService
        for p in PolicyKnowledgeService.load_policies():
            if getattr(p, "policy_id", None):
                canonical_ids.add(p.policy_id)
    except Exception as e:
        logger.warning(f"Grounding: Could not load policies from PolicyKnowledgeService: {e}")

    # 2. Phase 14 Policy RAG Vector Store Manifest
    try:
        from app.services.policy_vector_store import PolicyVectorStore
        store = PolicyVectorStore()
        if store.load_index() and store.chunks_map:
            for c in store.chunks_map:
                if c.get("policy_id"):
                    canonical_ids.add(c["policy_id"])
    except Exception as e:
        logger.warning(f"Grounding: Could not load policies from PolicyVectorStore: {e}")

    # 3. Database sections and documents (Phase 13 DB seed)
    if db:
        try:
            from app.db.models import PolicyDocumentModel
            for row in db.query(PolicySectionModel.section_id).all():
                canonical_ids.add(row.section_id)
            for row in db.query(PolicyDocumentModel.policy_doc_id).all():
                canonical_ids.add(row.policy_doc_id)
        except Exception as e:
            logger.warning(f"Grounding: Could not query DB policy tables: {e}")

    return canonical_ids


def validate_policy_citations(
    cited_section_ids: List[str],
    db: Session,
) -> Tuple[List[str], List[str]]:
    """
    Checks each cited policy ID against the canonical Phase 13/14 Policy Knowledge Base,
    Policy RAG manifest, and database policy tables.

    Args:
        cited_section_ids: Policy / Section IDs returned by the LLM.
        db:                SQLAlchemy session.

    Returns:
        (valid_ids, invalid_ids)
    """
    if not cited_section_ids:
        return [], []

    canonical_ids = get_canonical_policy_ids(db)

    valid = [sid for sid in cited_section_ids if sid in canonical_ids]
    invalid = [sid for sid in cited_section_ids if sid not in canonical_ids]

    if invalid:
        logger.warning(
            f"LLM Grounding: {len(invalid)} invalid policy ID(s): {invalid}"
        )

    return valid, invalid


def compute_grounding_status(
    cited_evidence: List[str],
    valid_evidence: List[str],
    cited_policy: List[str],
    valid_policy: List[str],
) -> str:
    """
    Determines the overall grounding status based on citation validation results.

    Returns:
        "GROUNDED"   — all cited IDs are valid (or no IDs were cited)
        "PARTIAL"    — some cited IDs are valid, some are not
        "UNGROUNDED" — all cited IDs are invalid (likely hallucination)
    """
    total_cited = len(cited_evidence) + len(cited_policy)
    total_valid = len(valid_evidence) + len(valid_policy)

    if total_cited == 0:
        return "GROUNDED"

    if total_valid == 0:
        return "UNGROUNDED"

    if total_valid < total_cited:
        return "PARTIAL"

    return "GROUNDED"
