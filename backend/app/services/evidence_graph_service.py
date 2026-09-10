import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.db.models import (
    LoanApplicationModel,
    DocumentModel,
    ExtractedFieldModel,
    DocumentValidationModel,
    ValidationCheckModel,
    ApplicationVerificationModel,
    VerificationFindingModel,
    EvidenceNodeModel,
    EvidenceRelationshipModel,
    ReviewAssessmentModel
)
from app.schemas.evidence import EvidenceNodeSchema, EvidenceRelationshipSchema
from app.services.cross_document_verification_service import get_application_profile_data


def build_evidence_graph_for_application(db: Session, application_id: str) -> List[EvidenceNodeModel]:
    """
    Builds or rebuilds the Evidence Graph for an application from Phase 3–9 data.
    Idempotent: deletes prior nodes and relationships for application_id before rebuilding.
    """
    app_obj = db.query(LoanApplicationModel).filter(LoanApplicationModel.application_id == application_id).first()
    if not app_obj:
        raise ValueError(f"Application '{application_id}' not found.")

    target_id = application_id.replace("APP-", "").upper()
    profile = get_application_profile_data(db, application_id)

    # Clean prior graph data for idempotency
    db.query(EvidenceRelationshipModel).filter(EvidenceRelationshipModel.application_id == application_id).delete()
    db.query(EvidenceNodeModel).filter(EvidenceNodeModel.application_id == application_id).delete()
    db.flush()

    nodes: List[EvidenceNodeModel] = []
    relationships: List[EvidenceRelationshipModel] = []
    
    node_map: Dict[str, EvidenceNodeModel] = {}
    rel_set: set = set()

    def add_node(n_id: str, n_type: str, title: str, val: Optional[str] = None, doc_id: Optional[str] = None, src_type: str = "SYSTEM", src_ref: Optional[str] = None, conf: float = 1.0, meta: Optional[dict] = None) -> EvidenceNodeModel:
        if n_id in node_map:
            return node_map[n_id]
        node = EvidenceNodeModel(
            node_id=n_id,
            application_id=application_id,
            document_id=doc_id,
            node_type=n_type,
            title=title,
            value=val,
            source_type=src_type,
            source_reference=src_ref,
            confidence=conf,
            node_metadata=meta or {},
            created_at=datetime.utcnow()
        )
        db.add(node)
        node_map[n_id] = node
        nodes.append(node)
        return node

    def add_rel(rel_type: str, src_id: str, tgt_id: str, meta: Optional[dict] = None) -> Optional[EvidenceRelationshipModel]:
        rel_key = (rel_type, src_id, tgt_id)
        if rel_key in rel_set:
            return None
        if src_id not in node_map or tgt_id not in node_map:
            return None
        rel_id = f"REL-{src_id}-{rel_type}-{tgt_id}"
        rel = EvidenceRelationshipModel(
            relationship_id=rel_id,
            application_id=application_id,
            source_node_id=src_id,
            target_node_id=tgt_id,
            relationship_type=rel_type,
            rel_metadata=meta or {},
            created_at=datetime.utcnow()
        )
        db.add(rel)
        rel_set.add(rel_key)
        relationships.append(rel)
        return rel

    # 1. APPLICATION NODE
    app_node_id = f"NODE-APP-{application_id}"
    app_title = f"Loan Application ({profile['applicant_name']})"
    app_val = f"Applicant: {profile['applicant_name']} | Amount: INR {profile.get('loan_amount', 0):,.0f}"
    add_node(
        n_id=app_node_id,
        n_type="APPLICATION",
        title=app_title,
        val=app_val,
        src_type="APPLICATION_DATA",
        src_ref="applications",
        meta=profile
    )

    # 2. DOCUMENT NODES & FIELD NODES
    docs = db.query(DocumentModel).filter(
        (DocumentModel.application_id == application_id) | (DocumentModel.applicant_id == target_id),
        DocumentModel.processing_status != "DELETED"
    ).all()

    doc_node_ids: Dict[str, str] = {}
    field_node_ids: Dict[Tuple[str, str], str] = {}

    for doc in docs:
        d_type = (doc.classified_document_type or doc.document_type or "OTHER").upper()
        doc_node_id = f"NODE-DOC-{doc.document_id}"
        doc_node_ids[doc.document_id] = doc_node_id
        doc_node_ids[d_type] = doc_node_id

        doc_title = f"{d_type} ({doc.original_filename})"
        doc_val = f"Type: {d_type} | Extracted: {doc.extraction_status}"
        
        add_node(
            n_id=doc_node_id,
            n_type="DOCUMENT",
            title=doc_title,
            val=doc_val,
            doc_id=doc.document_id,
            src_type="DOCUMENT_FILE",
            src_ref=doc.original_filename,
            conf=doc.classification_confidence or 1.0,
            meta={"mime_type": doc.mime_type, "file_size": doc.file_size, "checksum": doc.checksum}
        )
        add_rel("HAS_DOCUMENT", app_node_id, doc_node_id)

        # Extracted fields
        fields = db.query(ExtractedFieldModel).filter(ExtractedFieldModel.document_id == doc.document_id).all()
        for f in fields:
            f_node_id = f"NODE-FIELD-{doc.document_id}-{f.field_name}"
            field_node_ids[(doc.document_id, f.field_name)] = f_node_id
            field_node_ids[(d_type, f.field_name)] = f_node_id

            f_title = f"{f.field_name} = {f.normalized_value or f.raw_value}"
            f_val = str(f.normalized_value or f.raw_value)
            
            add_node(
                n_id=f_node_id,
                n_type="FIELD",
                title=f_title,
                val=f_val,
                doc_id=doc.document_id,
                src_type="EXTRACTED_FIELD",
                src_ref=f.field_name,
                conf=f.confidence,
                meta={"raw_value": f.raw_value, "field_type": f.field_type, "evidence": f.evidence}
            )
            add_rel("CONTAINS_FIELD", doc_node_id, f_node_id)

        # Document Validation Result
        val_record = db.query(DocumentValidationModel).filter(DocumentValidationModel.document_id == doc.document_id).first()
        if val_record:
            val_node_id = f"NODE-VAL-{doc.document_id}"
            val_title = f"Validation Result ({val_record.overall_result})"
            val_val = val_record.summary
            
            add_node(
                n_id=val_node_id,
                n_type="VALIDATION_RESULT",
                title=val_title,
                val=val_val,
                doc_id=doc.document_id,
                src_type="DOCUMENT_VALIDATION",
                src_ref=val_record.status,
                meta={"overall_result": val_record.overall_result}
            )
            add_rel("HAS_VALIDATION", doc_node_id, val_node_id)

    # 3. VERIFICATION FINDINGS & TRACEABILITY
    ver_record = db.query(ApplicationVerificationModel).filter(ApplicationVerificationModel.application_id == application_id).first()
    if ver_record:
        findings = db.query(VerificationFindingModel).filter(VerificationFindingModel.verification_id == ver_record.id).all()
        for finding in findings:
            find_node_id = f"NODE-FINDING-{finding.id}"
            find_title = f"{finding.rule_name}: {finding.result} ({finding.severity})"
            find_val = finding.message

            add_node(
                n_id=find_node_id,
                n_type="VERIFICATION_FINDING",
                title=find_title,
                val=find_val,
                src_type="VERIFICATION_RULE",
                src_ref=finding.rule_name,
                meta={
                    "rule_name": finding.rule_name,
                    "result": finding.result,
                    "severity": finding.severity,
                    "difference": finding.difference,
                    "difference_percent": finding.difference_percent,
                    "tolerance_percent": finding.tolerance_percent,
                    "evidence": finding.evidence
                }
            )
            add_rel("HAS_FINDING", app_node_id, find_node_id)

            # Connect supporting field / document nodes
            src_a_type = finding.source_a
            field_a_name = finding.field_a
            src_b_type = finding.source_b
            field_b_name = finding.field_b

            # Node A lookup
            node_a_id = field_node_ids.get((finding.source_document_id or src_a_type, field_a_name)) or doc_node_ids.get(finding.source_document_id or src_a_type) or app_node_id
            # Node B lookup
            node_b_id = field_node_ids.get((finding.comparison_document_id or src_b_type, field_b_name)) or doc_node_ids.get(finding.comparison_document_id or src_b_type)

            if node_a_id:
                add_rel("SUPPORTS", node_a_id, find_node_id)
            if node_b_id:
                add_rel("SUPPORTS", node_b_id, find_node_id)
            if node_a_id and node_b_id and node_a_id != node_b_id:
                add_rel("COMPARED_WITH", node_a_id, node_b_id)

    # 4. ML RISK ASSESSMENT NODE & RELATIONSHIP
    try:
        from app.ml.predictor import predict_application_risk
        risk_res = predict_application_risk(application_id, profile)
        if risk_res and risk_res.status == "COMPLETED":
            ml_node_id = f"NODE-ML-RISK-{application_id}"
            ml_title = f"ML Risk Assessment ({risk_res.risk_level})"
            ml_val = f"Risk Level: {risk_res.risk_level} | Rejection Probability: {risk_res.rejection_probability:.4f} | Model: {risk_res.model_name}"
            
            add_node(
                n_id=ml_node_id,
                n_type="ML_RISK_ASSESSMENT",
                title=ml_title,
                val=ml_val,
                src_type="ML_MODEL",
                src_ref=risk_res.model_name,
                conf=1.0,
                meta={
                    "rejection_probability": risk_res.rejection_probability,
                    "risk_level": risk_res.risk_level,
                    "prediction": risk_res.prediction,
                    "model_name": risk_res.model_name,
                    "model_version": risk_res.model_version,
                    "target_definition": risk_res.target_definition,
                    "feature_version": risk_res.feature_version,
                    "status": risk_res.status
                }
            )
            add_rel("HAS_RISK_ASSESSMENT", app_node_id, ml_node_id)
    except Exception as e:
        logger.warning(f"Could not build ML Risk Assessment node for '{application_id}': {e}")

    # 5. REVIEW ASSESSMENT NODE & RELATIONSHIP
    try:
        review_obj = db.query(ReviewAssessmentModel).filter(ReviewAssessmentModel.application_id == application_id).first()
        if review_obj:
            rev_node_id = f"NODE-REVIEW-{application_id}"
            rev_title = f"Review Assessment ({review_obj.review_priority})"
            rev_val = f"Priority: {review_obj.review_priority} ({review_obj.review_score}/100) | Trust: {review_obj.evidence_trust_score}/100 | Matrix: {review_obj.risk_evidence_matrix_category}"
            
            add_node(
                n_id=rev_node_id,
                n_type="REVIEW_ASSESSMENT",
                title=rev_title,
                val=rev_val,
                src_type="REVIEW_ENGINE",
                src_ref=review_obj.scoring_version,
                conf=1.0,
                meta={
                    "review_score": review_obj.review_score,
                    "review_priority": review_obj.review_priority,
                    "evidence_trust_score": review_obj.evidence_trust_score,
                    "evidence_trust_level": review_obj.evidence_trust_level,
                    "risk_evidence_matrix_category": review_obj.risk_evidence_matrix_category,
                    "document_completeness_status": review_obj.document_completeness_status,
                    "missing_documents": review_obj.missing_documents or [],
                    "critical_issue": review_obj.critical_issue,
                    "verification_issue_type": review_obj.verification_issue_type,
                    "primary_reason": review_obj.primary_reason if review_obj.primary_reason else None,
                    "recommended_action": review_obj.recommended_action
                }
            )
            add_rel("HAS_REVIEW_ASSESSMENT", app_node_id, rev_node_id)
            
            # Connect to ML node if present
            ml_node_id = f"NODE-ML-RISK-{application_id}"
            if ml_node_id in node_map:
                add_rel("BASED_ON", rev_node_id, ml_node_id)
    except Exception as e:
        logger.warning(f"Could not build Review Assessment node for '{application_id}': {e}")

    db.commit()
    return nodes



def get_evidence_graph_payload(db: Session, application_id: str) -> Dict[str, Any]:
    """Retrieves structured evidence graph response for API."""
    app_obj = db.query(LoanApplicationModel).filter(LoanApplicationModel.application_id == application_id).first()
    if not app_obj:
        raise ValueError(f"Application '{application_id}' not found.")

    nodes_models = db.query(EvidenceNodeModel).filter(EvidenceNodeModel.application_id == application_id).all()
    rel_models = db.query(EvidenceRelationshipModel).filter(EvidenceRelationshipModel.application_id == application_id).all()

    # If graph not built yet, auto-build
    if not nodes_models:
        build_evidence_graph_for_application(db, application_id)
        nodes_models = db.query(EvidenceNodeModel).filter(EvidenceNodeModel.application_id == application_id).all()
        rel_models = db.query(EvidenceRelationshipModel).filter(EvidenceRelationshipModel.application_id == application_id).all()

    nodes_list = [EvidenceNodeSchema.model_validate(n) for n in nodes_models]
    rel_list = [EvidenceRelationshipSchema.model_validate(r) for r in rel_models]

    node_types_count: Dict[str, int] = {}
    for n in nodes_list:
        node_types_count[n.node_type] = node_types_count.get(n.node_type, 0) + 1

    rel_types_count: Dict[str, int] = {}
    for r in rel_list:
        rel_types_count[r.relationship_type] = rel_types_count.get(r.relationship_type, 0) + 1

    return {
        "application_id": application_id,
        "total_nodes": len(nodes_list),
        "total_relationships": len(rel_list),
        "nodes": nodes_list,
        "relationships": rel_list,
        "graph_summary": {
            "node_types": node_types_count,
            "relationship_types": rel_types_count
        },
        "generated_at": datetime.utcnow()
    }
