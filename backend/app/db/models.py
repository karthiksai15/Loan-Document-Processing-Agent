from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, JSON, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class LoanApplicationModel(Base):
    __tablename__ = "applications"
    
    application_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    application_number: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(100), ForeignKey("users.id"), nullable=True, index=True)
    applicant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    income_annum: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    loan_amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    
    # Verification Metadata (Phase 9)
    verification_status: Mapped[str] = mapped_column(String(50), default="NOT_VERIFIED")  # NOT_VERIFIED, VERIFYING, COMPLETED, FAILED
    verification_overall_result: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # MATCH, MISMATCHES_FOUND, PASSED_WITH_WARNINGS, INCOMPLETE
    verification_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    customer: Mapped[Optional["UserModel"]] = relationship("UserModel", back_populates="applications", foreign_keys=[user_id])
    documents: Mapped[List["DocumentModel"]] = relationship("DocumentModel", back_populates="application", cascade="all, delete-orphan")
    verifications: Mapped[List["ApplicationVerificationModel"]] = relationship("ApplicationVerificationModel", back_populates="application", cascade="all, delete-orphan")
    review_assessments: Mapped[List["ReviewAssessmentModel"]] = relationship("ReviewAssessmentModel", back_populates="application", cascade="all, delete-orphan")
    llm_reviews: Mapped[List["LLMReviewModel"]] = relationship("LLMReviewModel", back_populates="application", cascade="all, delete-orphan")
    agent_reviews: Mapped[List["AgentReviewModel"]] = relationship("AgentReviewModel", back_populates="application", cascade="all, delete-orphan")
    human_reviews: Mapped[List["HumanReviewModel"]] = relationship("HumanReviewModel", back_populates="application", cascade="all, delete-orphan")
    human_review_audits: Mapped[List["HumanReviewAuditModel"]] = relationship("HumanReviewAuditModel", back_populates="application", cascade="all, delete-orphan")



class ApplicantModel(Base):
    __tablename__ = "applicants"
    
    applicant_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    loan_id: Mapped[int] = mapped_column(Integer, nullable=False)
    applicant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    employer: Mapped[str] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[str] = mapped_column(String(50), nullable=True)
    dummy_kyc_id: Mapped[str] = mapped_column(String(100), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    no_of_dependents: Mapped[int] = mapped_column(Integer, default=0)
    education: Mapped[str] = mapped_column(String(100), nullable=True)
    self_employed: Mapped[str] = mapped_column(String(10), default="No")
    income_annum: Mapped[float] = mapped_column(Float, default=0.0)
    monthly_income: Mapped[float] = mapped_column(Float, default=0.0)
    loan_amount: Mapped[float] = mapped_column(Float, default=0.0)
    loan_term: Mapped[int] = mapped_column(Integer, default=0)
    cibil_score: Mapped[int] = mapped_column(Integer, default=0)
    residential_assets_value: Mapped[float] = mapped_column(Float, default=0.0)
    commercial_assets_value: Mapped[float] = mapped_column(Float, default=0.0)
    luxury_assets_value: Mapped[float] = mapped_column(Float, default=0.0)
    bank_asset_value: Mapped[float] = mapped_column(Float, default=0.0)
    historical_loan_status: Mapped[str] = mapped_column(String(50), nullable=True)
    scenario: Mapped[str] = mapped_column(String(100), default="normal")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    legacy_documents: Mapped[List["DocumentModel"]] = relationship("DocumentModel", back_populates="applicant")
    findings: Mapped[List["FindingModel"]] = relationship("FindingModel", back_populates="applicant")
    review_decisions: Mapped[List["ReviewDecisionModel"]] = relationship("ReviewDecisionModel", back_populates="applicant")


class DocumentModel(Base):
    __tablename__ = "documents"
    
    document_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    application_id: Mapped[Optional[str]] = mapped_column(String(100), ForeignKey("applications.application_id"), nullable=True)
    applicant_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("applicants.applicant_id"), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)  # PAYSLIP, BANK_STATEMENT, TAX_RETURN, KYC, OTHER
    mime_type: Mapped[str] = mapped_column(String(100), default="text/plain")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    checksum: Mapped[str] = mapped_column(String(64), nullable=True)  # SHA-256 hex string
    processing_status: Mapped[str] = mapped_column(String(50), default="UPLOADED")  # UPLOADED, PROCESSING, PROCESSED, FAILED, DELETED
    extracted_fields: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    extraction_confidence: Mapped[float] = mapped_column(Float, default=1.0)
    
    # Text Extraction Metadata (Phase 5)
    extraction_status: Mapped[str] = mapped_column(String(50), default="NOT_PROCESSED")  # NOT_PROCESSED, PROCESSING, COMPLETED, FAILED
    extraction_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # TEXT, PDF_TEXT, OCR
    extracted_text_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_text_length: Mapped[int] = mapped_column(Integer, default=0)
    extraction_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Document Classification Metadata (Phase 6)
    classified_document_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # PAYSLIP, BANK_STATEMENT, TAX_RETURN, KYC, OTHER
    classification_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    classification_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # KEYWORD_RULES
    classification_status: Mapped[str] = mapped_column(String(50), default="NOT_CLASSIFIED")  # NOT_CLASSIFIED, CLASSIFYING, COMPLETED, FAILED
    classification_signals: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    classification_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    classified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Information Field Extraction Metadata (Phase 7)
    field_extraction_status: Mapped[str] = mapped_column(String(50), default="NOT_EXTRACTED")  # NOT_EXTRACTED, EXTRACTING, COMPLETED, FAILED
    field_extraction_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fields_extracted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Document Validation Metadata (Phase 8)
    validation_status: Mapped[str] = mapped_column(String(50), default="NOT_VALIDATED")  # NOT_VALIDATED, VALIDATING, COMPLETED, FAILED
    validation_overall_result: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # PASS, PASS_WITH_WARNINGS, FAIL, UNSUPPORTED
    validation_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(100), ForeignKey("users.id"), nullable=True)
    storage_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    application: Mapped[Optional["LoanApplicationModel"]] = relationship("LoanApplicationModel", back_populates="documents")
    applicant: Mapped[Optional["ApplicantModel"]] = relationship("ApplicantModel", back_populates="legacy_documents")
    extracted_fields_data: Mapped[List["ExtractedFieldModel"]] = relationship("ExtractedFieldModel", back_populates="document", cascade="all, delete-orphan")
    validation_data: Mapped[List["DocumentValidationModel"]] = relationship("DocumentValidationModel", back_populates="document", cascade="all, delete-orphan")
    file_record: Mapped[Optional["DocumentFileModel"]] = relationship("DocumentFileModel", back_populates="document", uselist=False, cascade="all, delete-orphan")


class ExtractedFieldModel(Base):
    __tablename__ = "extracted_fields"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(100), ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    field_type: Mapped[str] = mapped_column(String(50), default="string")  # string, number, date, currency, list
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    extraction_method: Mapped[str] = mapped_column(String(50), default="LABEL_PATTERN")  # LABEL_PATTERN, REGEX_RULE
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    document: Mapped["DocumentModel"] = relationship("DocumentModel", back_populates="extracted_fields_data")


class DocumentValidationModel(Base):
    __tablename__ = "document_validations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(100), ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="NOT_VALIDATED")  # NOT_VALIDATED, VALIDATING, COMPLETED, FAILED
    overall_result: Mapped[str] = mapped_column(String(50), default="PASS")  # PASS, PASS_WITH_WARNINGS, FAIL, UNSUPPORTED
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    validation_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    document: Mapped["DocumentModel"] = relationship("DocumentModel", back_populates="validation_data")
    checks_data: Mapped[List["ValidationCheckModel"]] = relationship("ValidationCheckModel", back_populates="validation_result", cascade="all, delete-orphan")


class ValidationCheckModel(Base):
    __tablename__ = "validation_checks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    validation_id: Mapped[int] = mapped_column(Integer, ForeignKey("document_validations.id", ondelete="CASCADE"), nullable=False)
    check_name: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="INFO")  # INFO, WARNING, ERROR
    status: Mapped[str] = mapped_column(String(20), default="PASS")  # PASS, WARNING, FAIL, NOT_CHECKED
    message: Mapped[str] = mapped_column(Text, nullable=False)
    field_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    validation_result: Mapped["DocumentValidationModel"] = relationship("DocumentValidationModel", back_populates="checks_data")


class FindingModel(Base):
    __tablename__ = "findings"
    
    finding_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    applicant_id: Mapped[str] = mapped_column(String(50), ForeignKey("applicants.applicant_id"), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="Medium")
    source_document: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_field: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    observed_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    is_overridden: Mapped[bool] = mapped_column(default=False)
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    applicant: Mapped["ApplicantModel"] = relationship("ApplicantModel", back_populates="findings")


class ReviewDecisionModel(Base):
    __tablename__ = "review_decisions"
    
    review_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    applicant_id: Mapped[str] = mapped_column(String(50), ForeignKey("applicants.applicant_id"), nullable=False)
    officer_id: Mapped[str] = mapped_column(String(100), default="LOAN_OFFICER_1")
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    officer_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_support_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ml_risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    applicant: Mapped["ApplicantModel"] = relationship("ApplicantModel", back_populates="review_decisions")


class ApplicationVerificationModel(Base):
    __tablename__ = "application_verifications"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[str] = mapped_column(String(100), ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="NOT_VERIFIED")  # NOT_VERIFIED, VERIFYING, COMPLETED, FAILED
    overall_result: Mapped[str] = mapped_column(String(50), default="MATCH")  # MATCH, MISMATCHES_FOUND, PASSED_WITH_WARNINGS, INCOMPLETE
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_comparisons: Mapped[int] = mapped_column(Integer, default=0)
    matched_comparisons: Mapped[int] = mapped_column(Integer, default=0)
    mismatched_comparisons: Mapped[int] = mapped_column(Integer, default=0)
    unavailable_comparisons: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    verification_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    application: Mapped["LoanApplicationModel"] = relationship("LoanApplicationModel", back_populates="verifications")
    findings_data: Mapped[List["VerificationFindingModel"]] = relationship("VerificationFindingModel", back_populates="verification_result", cascade="all, delete-orphan")


class VerificationFindingModel(Base):
    __tablename__ = "verification_findings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verification_id: Mapped[int] = mapped_column(Integer, ForeignKey("application_verifications.id", ondelete="CASCADE"), nullable=False)
    verification_type: Mapped[str] = mapped_column(String(50), nullable=False)  # IDENTITY_COMPARISON, INCOME_COMPARISON, SALARY_COMPARISON, DOCUMENT_CONSISTENCY, APPLICATION_DOCUMENT_COMPARISON
    rule_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_a: Mapped[str] = mapped_column(String(50), nullable=False)  # APPLICATION, PAYSLIP, BANK_STATEMENT, TAX_RETURN, KYC
    field_a: Mapped[str] = mapped_column(String(100), nullable=False)
    value_a: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_b: Mapped[str] = mapped_column(String(50), nullable=False)
    field_b: Mapped[str] = mapped_column(String(100), nullable=False)
    value_b: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_value_a: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_value_b: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difference: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    difference_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tolerance_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    result: Mapped[str] = mapped_column(String(20), default="MATCH")  # MATCH, MISMATCH, NOT_AVAILABLE
    severity: Mapped[str] = mapped_column(String(20), default="INFO")  # INFO, WARNING, ERROR
    source_document_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    comparison_document_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    verification_result: Mapped["ApplicationVerificationModel"] = relationship("ApplicationVerificationModel", back_populates="findings_data")


class EvidenceNodeModel(Base):
    __tablename__ = "evidence_nodes"
    
    node_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    application_id: Mapped[str] = mapped_column(String(100), ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[Optional[str]] = mapped_column(String(100), ForeignKey("documents.document_id", ondelete="SET NULL"), nullable=True)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)  # APPLICATION, DOCUMENT, FIELD, VALIDATION_RESULT, VERIFICATION_FINDING
    title: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), default="SYSTEM")  # APPLICATION_DATA, EXTRACTED_FIELD, VALIDATION_CHECK, VERIFICATION_RULE
    source_reference: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    node_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    outgoing_relationships: Mapped[List["EvidenceRelationshipModel"]] = relationship(
        "EvidenceRelationshipModel",
        foreign_keys="EvidenceRelationshipModel.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan"
    )
    incoming_relationships: Mapped[List["EvidenceRelationshipModel"]] = relationship(
        "EvidenceRelationshipModel",
        foreign_keys="EvidenceRelationshipModel.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan"
    )


class EvidenceRelationshipModel(Base):
    __tablename__ = "evidence_relationships"
    
    relationship_id: Mapped[str] = mapped_column(String(500), primary_key=True)
    application_id: Mapped[str] = mapped_column(String(100), ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False)
    source_node_id: Mapped[str] = mapped_column(String(255), ForeignKey("evidence_nodes.node_id", ondelete="CASCADE"), nullable=False)
    target_node_id: Mapped[str] = mapped_column(String(255), ForeignKey("evidence_nodes.node_id", ondelete="CASCADE"), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)  # HAS_DOCUMENT, CONTAINS_FIELD, HAS_VALIDATION, HAS_FINDING, DERIVED_FROM, SUPPORTS, COMPARED_WITH
    rel_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    source_node: Mapped["EvidenceNodeModel"] = relationship(
        "EvidenceNodeModel",
        foreign_keys=[source_node_id],
        back_populates="outgoing_relationships"
    )
    target_node: Mapped["EvidenceNodeModel"] = relationship(
        "EvidenceNodeModel",
        foreign_keys=[target_node_id],
        back_populates="incoming_relationships"
    )


class ReviewAssessmentModel(Base):
    __tablename__ = "review_assessments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    application_id: Mapped[str] = mapped_column(String(100), ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False)
    review_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    review_priority: Mapped[str] = mapped_column(String(20), default="LOW")  # LOW, MEDIUM, HIGH
    ml_risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Rejection probability 0-1
    ml_risk_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # LOW, MEDIUM, HIGH
    evidence_trust_score: Mapped[float] = mapped_column(Float, default=100.0)  # 0-100
    evidence_trust_level: Mapped[str] = mapped_column(String(20), default="HIGH")  # LOW, MEDIUM, HIGH
    evidence_consistency_category: Mapped[str] = mapped_column(String(50), default="HIGH")  # LOW, MEDIUM, HIGH
    primary_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    secondary_reasons: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)  # list of strings
    missing_documents: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    missing_document: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default=None)
    critical_issue: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default=None)
    verification_issue_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default=None)
    validation_issue_count: Mapped[int] = mapped_column(Integer, default=0)
    verification_issue_count: Mapped[int] = mapped_column(Integer, default=0)
    document_completeness_status: Mapped[str] = mapped_column(String(50), default="COMPLETE")  # COMPLETE, INCOMPLETE
    highest_severity: Mapped[str] = mapped_column(String(20), default="INFO")  # INFO, WARNING, ERROR
    risk_evidence_matrix_category: Mapped[str] = mapped_column(String(50), default="CLEAN")  # CLEAN, REVIEW, INVESTIGATE
    score_factors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)  # list of factor dicts
    scoring_version: Mapped[str] = mapped_column(String(50), default="review_score_v1")
    recommended_action: Mapped[str] = mapped_column(String(50), default="STANDARD_REVIEW")  # STANDARD_REVIEW, OFFICER_INVESTIGATION, DOCUMENT_FOLLOWUP
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    application: Mapped["LoanApplicationModel"] = relationship("LoanApplicationModel", back_populates="review_assessments")


class PolicyDocumentModel(Base):
    __tablename__ = "policy_documents"
    
    policy_doc_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    policy_type: Mapped[str] = mapped_column(String(50), nullable=False)  # REGULATORY, INTERNAL_UNDERWRITING
    authority: Mapped[str] = mapped_column(String(100), nullable=False)  # RBI, INTERNAL_BANK
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # KYC, DIGITAL_LENDING, CREDIT_REPORTING, FAIR_PRACTICES, UNDERWRITING_METRICS
    version: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 2025-08-14, 1.0
    reference_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    official_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    effective_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")  # ACTIVE, DEPRECATED, DRAFT
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    sections: Mapped[List["PolicySectionModel"]] = relationship(
        "PolicySectionModel", back_populates="policy_document", cascade="all, delete-orphan"
    )
    rules: Mapped[List["PolicyRuleModel"]] = relationship(
        "PolicyRuleModel", back_populates="policy_document", cascade="all, delete-orphan"
    )


class PolicySectionModel(Base):
    __tablename__ = "policy_sections"
    
    section_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    policy_doc_id: Mapped[str] = mapped_column(String(100), ForeignKey("policy_documents.policy_doc_id", ondelete="CASCADE"), nullable=False)
    chapter_or_part: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    section_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    section_title: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    policy_document: Mapped["PolicyDocumentModel"] = relationship("PolicyDocumentModel", back_populates="sections")
    rules: Mapped[List["PolicyRuleModel"]] = relationship("PolicyRuleModel", back_populates="section")


class PolicyRuleModel(Base):
    __tablename__ = "policy_rules"
    
    rule_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    policy_doc_id: Mapped[str] = mapped_column(String(100), ForeignKey("policy_documents.policy_doc_id", ondelete="CASCADE"), nullable=False)
    section_id: Mapped[Optional[str]] = mapped_column(String(100), ForeignKey("policy_sections.section_id", ondelete="SET NULL"), nullable=True)
    rule_code: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    field_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    operator: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # EQUALS, GREATER_THAN_EQUAL, LESS_THAN_EQUAL, IN_LIST
    threshold_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_regulatory: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    policy_document: Mapped["PolicyDocumentModel"] = relationship("PolicyDocumentModel", back_populates="rules")
    section: Mapped[Optional["PolicySectionModel"]] = relationship("PolicySectionModel", back_populates="rules")


class LLMReviewModel(Base):
    """
    Persists a single LLM Review result for a loan application (Phase 15).
    One row per generation; latest is selected by created_at DESC.
    """
    __tablename__ = "llm_reviews"

    review_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    application_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False
    )

    # Provider metadata
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False)   # grok, fake, gemini
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)

    # Structured output fields
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_findings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)          # List[str]
    evidence_references: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)   # List[dict]
    policy_references: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)     # List[dict]
    risk_interpretation: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_level: Mapped[str] = mapped_column(String(20), nullable=False)          # LOW, MEDIUM, HIGH
    limitations: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)           # List[str]

    # Grounding / safety
    grounding_status: Mapped[str] = mapped_column(String(20), default="GROUNDED")      # GROUNDED, PARTIAL, UNGROUNDED
    injection_check_status: Mapped[str] = mapped_column(String(20), default="CLEAN")   # CLEAN, FLAGGED

    # Raw output for audit / debugging
    raw_llm_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    application: Mapped["LoanApplicationModel"] = relationship("LoanApplicationModel", back_populates="llm_reviews")

class AgentReviewModel(Base):
    """
    Persists AI Loan Review Agent investigation results (Phase 16).
    Stores investigation trace, final review, and metadata.
    One row per run; latest retrieved by created_at DESC.
    """
    __tablename__ = "agent_reviews"

    agent_review_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    application_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False
    )

    # Versioning
    agent_version: Mapped[str] = mapped_column(String(50), default="agent_v1")
    instruction_version: Mapped[str] = mapped_column(String(100), default="loan_review_agent_v1")

    # Investigation summary
    investigation_status: Mapped[str] = mapped_column(String(30), default="COMPLETED")  # COMPLETED, FAILED, ESCALATED
    step_count: Mapped[int] = mapped_column(Integer, default=0)
    tools_used: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)               # List[str]
    investigation_steps: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)      # List[InvestigationStep]

    # Final review fields
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_findings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    evidence_references: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    policy_references: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    risk_interpretation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_interpretation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unresolved_questions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    recommended_next_step: Mapped[str] = mapped_column(String(50), default="OFFICER_INVESTIGATION")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_level: Mapped[str] = mapped_column(String(20), default="LOW")
    limitations: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Escalation
    escalation_required: Mapped[bool] = mapped_column(Integer, default=0)                 # SQLite: store as int
    escalation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Grounding / safety & Phase 17 hardening
    grounding_status: Mapped[str] = mapped_column(String(20), default="GROUNDED")
    injection_check_status: Mapped[str] = mapped_column(String(20), default="CLEAN")
    evidence_sufficiency: Mapped[Optional[str]] = mapped_column(String(30), default="SUFFICIENT")
    claims_support_summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    retries_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    application: Mapped["LoanApplicationModel"] = relationship("LoanApplicationModel", back_populates="agent_reviews")


class HumanReviewModel(Base):
    """
    Persists Human Review Gate evaluation, loan officer workflow state,
    and final human decision (Phase 18).
    Strict separation: ai_recommendation vs human_decision.
    """
    __tablename__ = "human_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_action_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    application_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False
    )
    agent_review_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # AI Recommendation (read-only reference)
    ai_recommendation: Mapped[str] = mapped_column(String(50), default="STANDARD_REVIEW")

    # Confidence Evaluation (0-100)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_level: Mapped[str] = mapped_column(String(20), default="LOW")
    confidence_factors: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Gate Evaluation
    human_review_required: Mapped[bool] = mapped_column(Integer, default=0)
    human_review_status: Mapped[str] = mapped_column(String(30), default="NOT_REQUIRED")  # NOT_REQUIRED, REQUIRED, IN_REVIEW, COMPLETED, OVERRIDDEN
    human_review_reasons: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Human Decision & Override (Phase 18 & 19)
    human_decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    override: Mapped[bool] = mapped_column(Integer, default=0)
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Officer interaction & Feedback (Phase 18 & 19)
    officer_notes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    requested_documents: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    officer_feedback: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    application: Mapped["LoanApplicationModel"] = relationship("LoanApplicationModel", back_populates="human_reviews")


class HumanReviewAuditModel(Base):
    """
    Append-only audit trail for all human review gate evaluations, officer actions,
    document requests, and decisions (Phase 18).
    Privacy-safe: never logs raw PII or secret prompt chain-of-thought.
    """
    __tablename__ = "human_review_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    application_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    previous_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    new_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(30), default="SYSTEM")  # SYSTEM, LOAN_OFFICER
    actor_id: Mapped[str] = mapped_column(String(100), default="system")
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    application: Mapped["LoanApplicationModel"] = relationship("LoanApplicationModel", back_populates="human_review_audits")


class UserModel(Base):
    """
    User account model supporting Google OAuth 2.0 and role-based access (Phase 1 Auth).
    Roles:
      - CUSTOMER: Borrowers accessing customer portal & submitting loan applications
      - LOAN_OFFICER: Bank officers reviewing, verifying, and deciding loan applications
      - MANAGER: Credit managers with supervisory and underwriting review authority
    """
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    google_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    picture_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="CUSTOMER", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    applications: Mapped[List["LoanApplicationModel"]] = relationship("LoanApplicationModel", back_populates="customer")


class DocumentFileModel(Base):
    """
    Binary persistent document storage for Render / Cloud deployment.
    Stores actual document bytes in database to guarantee file survival
    even across ephemeral container restarts.
    """
    __tablename__ = "document_files"

    document_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("documents.document_id", ondelete="CASCADE"), primary_key=True
    )
    file_content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    document: Mapped["DocumentModel"] = relationship("DocumentModel", back_populates="file_record")

