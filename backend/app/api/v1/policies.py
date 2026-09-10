"""
Policy Knowledge Base REST API endpoints (Phase 13)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.policy_service import PolicyService
from app.services.policy_knowledge_service import PolicyKnowledgeService
from app.services.policy_rag_service import PolicyRAGService
from app.schemas.policy import (
    PolicyDocumentCreate,
    PolicyDocumentRead,
    PolicyDocumentDetailRead,
    PolicySectionRead,
    PolicySectionTraceability,
    PolicyRuleRead,
    PolicyIngestionResult,
    PolicyItemSchema,
    PolicyKnowledgeBaseSummary,
)
from app.schemas.policy_rag import (
    PolicySearchRequest,
    PolicySearchResponse,
    PolicyIndexRebuildResponse,
)

router = APIRouter(prefix="/policies", tags=["Policy Knowledge Base"])


@router.post(
    "/seed",
    response_model=PolicyIngestionResult,
    summary="Seed default RBI regulatory and internal underwriting policies",
)
def seed_default_policies(db: Session = Depends(get_db)):
    """Seeds the 4 verified RBI Regulatory Documents and 1 Internal Bank Underwriting Policy into DB."""
    return PolicyService.seed_policies(db)


@router.post(
    "/ingest",
    response_model=PolicyDocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a new policy document with sections and rules",
)
def ingest_policy_document(
    doc_data: PolicyDocumentCreate,
    db: Session = Depends(get_db),
):
    """Ingests a structured policy document into the Policy Knowledge Base."""
    try:
        doc_model = PolicyService.ingest_policy_document(db, doc_data)
        return PolicyDocumentRead(
            policy_doc_id=doc_model.policy_doc_id,
            title=doc_model.title,
            policy_type=doc_model.policy_type,
            authority=doc_model.authority,
            category=doc_model.category,
            version=doc_model.version,
            reference_code=doc_model.reference_code,
            official_url=doc_model.official_url,
            source_filename=doc_model.source_filename,
            effective_date=doc_model.effective_date,
            description=doc_model.description,
            status=doc_model.status,
            created_at=doc_model.created_at,
            updated_at=doc_model.updated_at,
            section_count=len(doc_model.sections),
            rule_count=len(doc_model.rules),
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.get(
    "/knowledge/summary",
    response_model=PolicyKnowledgeBaseSummary,
    summary="Get Policy Knowledge Base summary counts by source and category",
)
def get_policy_knowledge_summary():
    """Returns aggregated count of policies across RBI, HDFC_BANK, and HDFC_INTERNAL_DEMO."""
    return PolicyKnowledgeService.get_summary()


@router.get(
    "",
    summary="List policy documents with filtering by source or category",
)
def list_policies(
    source: Optional[str] = Query(None, description="Filter by source: RBI, HDFC_BANK, HDFC_INTERNAL_DEMO"),
    category: Optional[str] = Query(None, description="Filter by policy category"),
    policy_type: Optional[str] = Query(None, description="Filter by REGULATORY or INTERNAL_UNDERWRITING (DB)"),
    authority: Optional[str] = Query(None, description="Filter by RBI or INTERNAL_BANK (DB)"),
    keyword: Optional[str] = Query(None, description="Optional keyword search query"),
    db: Session = Depends(get_db),
):
    """
    Lists policy documents stored in the knowledge base.
    If policy_type or authority is specified, queries the relational policy documents.
    If source is specified (RBI, HDFC_BANK, HDFC_INTERNAL_DEMO), returns structured knowledge base policies.
    """
    # 1. Relational database query if policy_type or authority specified
    if policy_type or authority:
        docs = PolicyService.list_policies(db, policy_type=policy_type, authority=authority, category=category)
        return [
            PolicyDocumentRead(
                policy_doc_id=doc.policy_doc_id,
                title=doc.title,
                policy_type=doc.policy_type,
                authority=doc.authority,
                category=doc.category,
                version=doc.version,
                reference_code=doc.reference_code,
                official_url=doc.official_url,
                source_filename=doc.source_filename,
                effective_date=doc.effective_date,
                description=doc.description,
                status=doc.status,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                section_count=len(doc.sections),
                rule_count=len(doc.rules),
            )
            for doc in docs
        ]

    # 2. Structured Policy Knowledge Base query
    if keyword:
        return PolicyKnowledgeService.search_policies_keyword(keyword, source=source, category=category)
    elif source:
        policies = PolicyKnowledgeService.get_policies_by_source(source)
        if category:
            policies = [p for p in policies if p.category.upper() == category.strip().upper()]
        return policies
    elif category:
        return PolicyKnowledgeService.get_policies_by_category(category)
    else:
        return PolicyKnowledgeService.get_all_policies()


@router.get(
    "/{policy_doc_id}",
    summary="Get detailed policy document including all sections and rules",
)
def get_policy_document(
    policy_doc_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves full details of a specific policy.
    Checks Phase 13 Policy Knowledge Base first, then relational database documents.
    """
    # 1. Check Policy Knowledge Base
    kb_policy = PolicyKnowledgeService.get_policy_by_id(policy_doc_id)
    if kb_policy:
        return kb_policy

    # 2. Check Relational DB Policy Document
    doc = PolicyService.get_policy_document(db, policy_doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy document '{policy_doc_id}' not found.",
        )

    sections_read = [
        PolicySectionRead(
            section_id=sec.section_id,
            policy_doc_id=sec.policy_doc_id,
            chapter_or_part=sec.chapter_or_part,
            section_number=sec.section_number,
            section_title=sec.section_title,
            page_number=sec.page_number,
            content_text=sec.content_text,
            summary=sec.summary,
            created_at=sec.created_at,
            rules=[
                PolicyRuleRead(
                    rule_id=r.rule_id,
                    policy_doc_id=r.policy_doc_id,
                    section_id=r.section_id,
                    rule_code=r.rule_code,
                    rule_name=r.rule_name,
                    field_name=r.field_name,
                    operator=r.operator,
                    threshold_value=r.threshold_value,
                    description=r.description,
                    is_regulatory=r.is_regulatory,
                    created_at=r.created_at,
                )
                for r in sec.rules
            ],
        )
        for sec in doc.sections
    ]

    rules_read = [
        PolicyRuleRead(
            rule_id=r.rule_id,
            policy_doc_id=r.policy_doc_id,
            section_id=r.section_id,
            rule_code=r.rule_code,
            rule_name=r.rule_name,
            field_name=r.field_name,
            operator=r.operator,
            threshold_value=r.threshold_value,
            description=r.description,
            is_regulatory=r.is_regulatory,
            created_at=r.created_at,
        )
        for r in doc.rules
    ]

    return PolicyDocumentDetailRead(
        policy_doc_id=doc.policy_doc_id,
        title=doc.title,
        policy_type=doc.policy_type,
        authority=doc.authority,
        category=doc.category,
        version=doc.version,
        reference_code=doc.reference_code,
        official_url=doc.official_url,
        source_filename=doc.source_filename,
        effective_date=doc.effective_date,
        description=doc.description,
        status=doc.status,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        section_count=len(doc.sections),
        rule_count=len(doc.rules),
        sections=sections_read,
        rules=rules_read,
    )


@router.get(
    "/sections/{section_id}",
    response_model=PolicySectionTraceability,
    summary="Get section details with source, version, and page traceability",
)
def get_section_traceability(
    section_id: str,
    db: Session = Depends(get_db),
):
    """Returns exact section text with parent document title, version, page number, and source URL."""
    traceability = PolicyService.get_section_traceability(db, section_id)
    if not traceability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy section '{section_id}' not found.",
        )
    return PolicySectionTraceability(**traceability)


@router.get(
    "/rules/all",
    response_model=List[PolicyRuleRead],
    summary="List policy rules",
)
def list_rules(
    is_regulatory: Optional[bool] = Query(None, description="Filter by regulatory vs internal rule"),
    field_name: Optional[str] = Query(None, description="Filter by targeted applicant field"),
    db: Session = Depends(get_db),
):
    """Lists policy rules in the system."""
    rules = PolicyService.list_rules(db, is_regulatory=is_regulatory, field_name=field_name)
    return [
        PolicyRuleRead(
            rule_id=r.rule_id,
            policy_doc_id=r.policy_doc_id,
            section_id=r.section_id,
            rule_code=r.rule_code,
            rule_name=r.rule_name,
            field_name=r.field_name,
            operator=r.operator,
            threshold_value=r.threshold_value,
            description=r.description,
            is_regulatory=r.is_regulatory,
            created_at=r.created_at,
        )
        for r in rules
    ]


@router.post(
    "/index/rebuild",
    response_model=PolicyIndexRebuildResponse,
    summary="Rebuild the FAISS Policy RAG vector index",
)
def rebuild_policy_index(db: Session = Depends(get_db)):
    """Triggers complete policy section chunking, embedding generation, and FAISS index persistence."""
    try:
        return PolicyRAGService.rebuild_index(db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rebuild policy vector index: {str(e)}",
        )


@router.post(
    "/search",
    response_model=PolicySearchResponse,
    summary="Search policy knowledge base semantically",
)
def search_policies(
    request: PolicySearchRequest,
    db: Session = Depends(get_db),
):
    """Executes semantic policy retrieval using SentenceTransformer embeddings and FAISS vector index."""
    try:
        return PolicyRAGService.search_policies(db, request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during policy search: {str(e)}",
        )
