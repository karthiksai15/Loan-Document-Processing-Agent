"""
Policy Knowledge Base Service (Phase 13)

Manages policy document ingestion, section storage, rule registration,
strict regulatory vs internal underwriting separation, and section/page traceability.
Exposes data consumption interface for Phase 14 Policy RAG indexing.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import PolicyDocumentModel, PolicySectionModel, PolicyRuleModel
from app.schemas.policy import (
    PolicyDocumentCreate,
    PolicySectionCreate,
    PolicyRuleCreate,
    PolicyIngestionResult,
    PolicySectionTraceability,
)
from app.policies.seed_data import SEED_POLICIES


class PolicyService:
    @staticmethod
    def seed_policies(db: Session) -> PolicyIngestionResult:
        """
        Seeds the default 4 verified RBI Regulatory Documents and 1 Internal Underwriting Document
        into the Policy Knowledge Base database if not already present.
        """
        docs_ingested = 0
        sections_ingested = 0
        rules_ingested = 0

        for doc_data in SEED_POLICIES:
            existing = db.execute(
                select(PolicyDocumentModel).where(
                    PolicyDocumentModel.policy_doc_id == doc_data["policy_doc_id"]
                )
            ).scalar_one_or_none()

            if existing:
                continue

            # Create document model
            doc_model = PolicyDocumentModel(
                policy_doc_id=doc_data["policy_doc_id"],
                title=doc_data["title"],
                policy_type=doc_data["policy_type"],
                authority=doc_data["authority"],
                category=doc_data["category"],
                version=doc_data["version"],
                reference_code=doc_data.get("reference_code"),
                official_url=doc_data.get("official_url"),
                source_filename=doc_data.get("source_filename"),
                effective_date=doc_data.get("effective_date"),
                description=doc_data.get("description"),
                status=doc_data.get("status", "ACTIVE"),
            )
            db.add(doc_model)
            docs_ingested += 1

            # Add sections
            for sec_data in doc_data.get("sections", []):
                sec_model = PolicySectionModel(
                    section_id=sec_data["section_id"],
                    policy_doc_id=doc_data["policy_doc_id"],
                    chapter_or_part=sec_data.get("chapter_or_part"),
                    section_number=sec_data.get("section_number"),
                    section_title=sec_data["section_title"],
                    page_number=sec_data.get("page_number"),
                    content_text=sec_data["content_text"],
                    summary=sec_data.get("summary"),
                )
                db.add(sec_model)
                sections_ingested += 1

            # Add rules
            for rule_data in doc_data.get("rules", []):
                rule_model = PolicyRuleModel(
                    rule_id=rule_data["rule_id"],
                    policy_doc_id=doc_data["policy_doc_id"],
                    section_id=rule_data.get("section_id"),
                    rule_code=rule_data["rule_code"],
                    rule_name=rule_data["rule_name"],
                    field_name=rule_data.get("field_name"),
                    operator=rule_data.get("operator"),
                    threshold_value=rule_data.get("threshold_value"),
                    description=rule_data.get("description"),
                    is_regulatory=rule_data.get("is_regulatory", False),
                )
                db.add(rule_model)
                rules_ingested += 1

        db.commit()

        return PolicyIngestionResult(
            status="SUCCESS",
            documents_ingested=docs_ingested,
            sections_ingested=sections_ingested,
            rules_ingested=rules_ingested,
            message=f"Seeded {docs_ingested} documents, {sections_ingested} sections, and {rules_ingested} rules.",
        )

    @staticmethod
    def ingest_policy_document(db: Session, doc_data: PolicyDocumentCreate) -> PolicyDocumentModel:
        """
        Ingests a new custom policy document with its sections and rules into the database.
        Enforces strict separation: No RBI document can contain synthetic underwriting thresholds.
        """
        # Strict validation
        if doc_data.authority == "RBI" and doc_data.policy_type != "REGULATORY":
            raise ValueError("All RBI policy documents must have policy_type='REGULATORY'.")

        existing = db.execute(
            select(PolicyDocumentModel).where(
                PolicyDocumentModel.policy_doc_id == doc_data.policy_doc_id
            )
        ).scalar_one_or_none()

        if existing:
            raise ValueError(f"Policy document with ID '{doc_data.policy_doc_id}' already exists.")

        doc_model = PolicyDocumentModel(
            policy_doc_id=doc_data.policy_doc_id,
            title=doc_data.title,
            policy_type=doc_data.policy_type,
            authority=doc_data.authority,
            category=doc_data.category,
            version=doc_data.version,
            reference_code=doc_data.reference_code,
            official_url=doc_data.official_url,
            source_filename=doc_data.source_filename,
            effective_date=doc_data.effective_date,
            description=doc_data.description,
            status=doc_data.status,
        )
        db.add(doc_model)

        for sec in doc_data.sections:
            sec_model = PolicySectionModel(
                section_id=sec.section_id,
                policy_doc_id=doc_data.policy_doc_id,
                chapter_or_part=sec.chapter_or_part,
                section_number=sec.section_number,
                section_title=sec.section_title,
                page_number=sec.page_number,
                content_text=sec.content_text,
                summary=sec.summary,
            )
            db.add(sec_model)

        for rule in doc_data.rules:
            # Enforce regulatory flag consistency
            is_reg = doc_data.policy_type == "REGULATORY" and doc_data.authority == "RBI"
            rule_model = PolicyRuleModel(
                rule_id=rule.rule_id,
                policy_doc_id=doc_data.policy_doc_id,
                section_id=rule.section_id,
                rule_code=rule.rule_code,
                rule_name=rule.rule_name,
                field_name=rule.field_name,
                operator=rule.operator,
                threshold_value=rule.threshold_value,
                description=rule.description,
                is_regulatory=is_reg,
            )
            db.add(rule_model)

        db.commit()
        db.refresh(doc_model)
        return doc_model

    @staticmethod
    def list_policies(
        db: Session,
        policy_type: Optional[str] = None,
        authority: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[PolicyDocumentModel]:
        """Lists policy documents with optional filtering."""
        query = select(PolicyDocumentModel)
        if policy_type:
            query = query.where(PolicyDocumentModel.policy_type == policy_type)
        if authority:
            query = query.where(PolicyDocumentModel.authority == authority)
        if category:
            query = query.where(PolicyDocumentModel.category == category)

        return list(db.execute(query.order_by(PolicyDocumentModel.created_at.desc())).scalars().all())

    @staticmethod
    def get_policy_document(db: Session, policy_doc_id: str) -> Optional[PolicyDocumentModel]:
        """Gets a policy document by ID with sections and rules."""
        return db.execute(
            select(PolicyDocumentModel).where(PolicyDocumentModel.policy_doc_id == policy_doc_id)
        ).scalar_one_or_none()

    @staticmethod
    def get_section_traceability(db: Session, section_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a section by ID and enriches it with parent policy document metadata,
        providing complete section, page, source, version, and authority traceability.
        """
        sec = db.execute(
            select(PolicySectionModel).where(PolicySectionModel.section_id == section_id)
        ).scalar_one_or_none()

        if not sec:
            return None

        doc = sec.policy_document

        return {
            "section_id": sec.section_id,
            "policy_doc_id": sec.policy_doc_id,
            "chapter_or_part": sec.chapter_or_part,
            "section_number": sec.section_number,
            "section_title": sec.section_title,
            "page_number": sec.page_number,
            "content_text": sec.content_text,
            "summary": sec.summary,
            "created_at": sec.created_at,
            "policy_title": doc.title,
            "policy_type": doc.policy_type,
            "authority": doc.authority,
            "category": doc.category,
            "version": doc.version,
            "reference_code": doc.reference_code,
            "official_url": doc.official_url,
            "source_filename": doc.source_filename,
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "rule_code": r.rule_code,
                    "rule_name": r.rule_name,
                    "field_name": r.field_name,
                    "operator": r.operator,
                    "threshold_value": r.threshold_value,
                    "is_regulatory": r.is_regulatory,
                }
                for r in sec.rules
            ],
        }

    @staticmethod
    def list_rules(
        db: Session,
        is_regulatory: Optional[bool] = None,
        field_name: Optional[str] = None,
    ) -> List[PolicyRuleModel]:
        """Lists policy rules with optional regulatory and field filtering."""
        query = select(PolicyRuleModel)
        if is_regulatory is not None:
            query = query.where(PolicyRuleModel.is_regulatory == is_regulatory)
        if field_name:
            query = query.where(PolicyRuleModel.field_name == field_name)

        return list(db.execute(query).scalars().all())

    # =========================================================================
    # Phase 14 Consumption Interface: Vector Store Indexing Payload Extractor
    # =========================================================================
    @staticmethod
    def get_all_sections_for_indexing(db: Session) -> List[Dict[str, Any]]:
        """
        Phase 14 Interface: Returns all policy sections formatted with metadata
        ready for text chunking, embedding generation, and FAISS indexing.
        """
        sections = db.execute(select(PolicySectionModel)).scalars().all()
        indexing_payload = []

        for sec in sections:
            doc = sec.policy_document
            indexing_payload.append(
                {
                    "section_id": sec.section_id,
                    "policy_doc_id": doc.policy_doc_id,
                    "policy_title": doc.title,
                    "policy_type": doc.policy_type,  # REGULATORY vs INTERNAL_UNDERWRITING
                    "authority": doc.authority,      # RBI vs INTERNAL_BANK
                    "category": doc.category,
                    "version": doc.version,
                    "reference_code": doc.reference_code,
                    "official_url": doc.official_url,
                    "source_filename": doc.source_filename,
                    "chapter_or_part": sec.chapter_or_part,
                    "section_number": sec.section_number,
                    "section_title": sec.section_title,
                    "page_number": sec.page_number,
                    "content_text": sec.content_text,
                    "summary": sec.summary,
                }
            )

        return indexing_payload
