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
    DocumentValidationModel,
    ValidationCheckModel,
    ApplicationVerificationModel,
    VerificationFindingModel,
    ReviewAssessmentModel
)
from app.services.cross_document_verification_service import get_application_profile_data, verify_and_save_application
from app.ml.predictor import predict_application_risk
from app.schemas.review import ApplicationReviewScoreResponse, ReviewFactorSchema

# Configurable Weights
ML_RISK_WEIGHT = 0.30
EVIDENCE_TRUST_WEIGHT = 0.30
VERIFICATION_SEVERITY_WEIGHT = 0.25
COMPLETENESS_WEIGHT = 0.10
VALIDATION_WEIGHT = 0.05

SCORING_VERSION = "review_score_v1"


def compute_and_save_review_assessment(db: Session, application_id: str) -> ReviewAssessmentModel:
    """
    Computes deterministic Review Intelligence assessment for an application.
    Idempotent: updates existing ReviewAssessmentModel if present, or creates a new one.
    """
    app_obj = db.query(LoanApplicationModel).filter(LoanApplicationModel.application_id == application_id).first()
    if not app_obj:
        raise ValueError(f"Application '{application_id}' not found.")

    target_id = application_id.replace("APP-", "").upper()

    # 1. Fetch / Ensure Cross-Document Verification has run
    ver_record = db.query(ApplicationVerificationModel).filter(ApplicationVerificationModel.application_id == application_id).first()
    if not ver_record:
        try:
            ver_record = verify_and_save_application(db, application_id)
        except Exception as e:
            logger.warning(f"Could not auto-trigger verification for '{application_id}': {e}")
            ver_record = None

    findings = []
    if ver_record:
        findings = db.query(VerificationFindingModel).filter(VerificationFindingModel.verification_id == ver_record.id).all()

    # 2. Fetch Active Documents & Validation Results
    docs = db.query(DocumentModel).filter(
        (DocumentModel.application_id == application_id) | (DocumentModel.applicant_id == target_id),
        DocumentModel.processing_status != "DELETED"
    ).all()

    doc_types_present = set((d.classified_document_type or d.document_type or "OTHER").upper() for d in docs)
    
    val_records = []
    val_checks = []
    for d in docs:
        vals = db.query(DocumentValidationModel).filter(DocumentValidationModel.document_id == d.document_id).all()
        for v in vals:
            val_records.append(v)
            checks = db.query(ValidationCheckModel).filter(ValidationCheckModel.validation_id == v.id).all()
            val_checks.extend(checks)

    # 3. Fetch / Ensure ML Risk Prediction
    profile = get_application_profile_data(db, application_id)
    risk_res = predict_application_risk(application_id, profile)

    rejection_probability = risk_res.rejection_probability if risk_res.status == "COMPLETED" else 0.15
    ml_risk_level = risk_res.risk_level if risk_res.status == "COMPLETED" else "LOW"

    # 4. Check Document Completeness
    missing_docs = []
    if "PAYSLIP" not in doc_types_present:
        missing_docs.append("PAYSLIP")
    if "BANK_STATEMENT" not in doc_types_present:
        missing_docs.append("BANK_STATEMENT")
    if "TAX_RETURN" not in doc_types_present:
        missing_docs.append("TAX_RETURN")
    if "KYC" not in doc_types_present:
        missing_docs.append("KYC")

    is_complete = len(missing_docs) == 0
    completeness_status = "COMPLETE" if is_complete else "INCOMPLETE"

    # 5. Compute Evidence Trust Score (0-100)
    trust_score, trust_factors = _calculate_evidence_trust(
        doc_types_present=doc_types_present,
        missing_docs=missing_docs,
        findings=findings,
        val_records=val_records,
        target_id=target_id
    )

    trust_level = "HIGH" if trust_score >= 80 else ("MEDIUM" if trust_score >= 50 else "LOW")
    trust_category = trust_level

    # 6. Compute Review Priority Score (0-100)
    priority_score, priority_level, score_factors = _calculate_review_priority(
        rejection_probability=rejection_probability,
        trust_score=trust_score,
        findings=findings,
        missing_docs=missing_docs,
        val_records=val_records
    )

    # 7. Categorize Risk vs Evidence Matrix
    matrix_category = _derive_matrix_category(
        rejection_probability=rejection_probability,
        trust_score=trust_score,
        findings=findings,
        missing_docs=missing_docs
    )

    # 8. Identify Structured Issues (Purely deterministic facts, no narrative generation)
    critical_issue, verification_issue_type, highest_severity = _derive_structured_issues(
        findings=findings,
        val_records=val_records
    )
    missing_document = missing_docs[0] if missing_docs else None

    # Review Intelligence is purely structured: narrative explanations belong exclusively to Phase 16 AI Agent
    primary_reason = None
    secondary_reasons = []

    # 9. Determine Recommended Action
    if matrix_category == "INVESTIGATE" or priority_level == "HIGH":
        rec_action = "OFFICER_INVESTIGATION"
    elif matrix_category == "REVIEW" or priority_level == "MEDIUM":
        rec_action = "DOCUMENT_FOLLOWUP" if not is_complete else "STANDARD_REVIEW"
    else:
        rec_action = "STANDARD_REVIEW"

    # 10. Persist Assessment to Database (Idempotent Update or Insert)
    review_id = f"REV-{application_id}"
    review_obj = db.query(ReviewAssessmentModel).filter(ReviewAssessmentModel.application_id == application_id).first()

    val_issue_count = sum(1 for v in val_records if v.overall_result in ["FAIL", "PASS_WITH_WARNINGS"])
    ver_issue_count = sum(1 for f in findings if f.result == "MISMATCH")

    all_factors = trust_factors + score_factors

    if not review_obj:
        review_obj = ReviewAssessmentModel(
            review_id=review_id,
            application_id=application_id,
            review_score=round(priority_score, 2),
            review_priority=priority_level,
            ml_risk_score=round(rejection_probability, 4) if risk_res.status == "COMPLETED" else None,
            ml_risk_level=ml_risk_level,
            evidence_trust_score=round(trust_score, 2),
            evidence_trust_level=trust_level,
            evidence_consistency_category=trust_category,
            primary_reason=primary_reason or "",
            secondary_reasons=secondary_reasons,
            missing_documents=missing_docs,
            missing_document=missing_document,
            critical_issue=critical_issue,
            verification_issue_type=verification_issue_type,
            validation_issue_count=val_issue_count,
            verification_issue_count=ver_issue_count,
            document_completeness_status=completeness_status,
            highest_severity=highest_severity,
            risk_evidence_matrix_category=matrix_category,
            score_factors=[f.model_dump() for f in all_factors],
            scoring_version=SCORING_VERSION,
            recommended_action=rec_action,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(review_obj)
    else:
        review_obj.review_score = round(priority_score, 2)
        review_obj.review_priority = priority_level
        review_obj.ml_risk_score = round(rejection_probability, 4) if risk_res.status == "COMPLETED" else None
        review_obj.ml_risk_level = ml_risk_level
        review_obj.evidence_trust_score = round(trust_score, 2)
        review_obj.evidence_trust_level = trust_level
        review_obj.evidence_consistency_category = trust_category
        review_obj.primary_reason = primary_reason or ""
        review_obj.secondary_reasons = secondary_reasons
        review_obj.missing_documents = missing_docs
        review_obj.missing_document = missing_document
        review_obj.critical_issue = critical_issue
        review_obj.verification_issue_type = verification_issue_type
        review_obj.validation_issue_count = val_issue_count
        review_obj.verification_issue_count = ver_issue_count
        review_obj.document_completeness_status = completeness_status
        review_obj.highest_severity = highest_severity
        review_obj.risk_evidence_matrix_category = matrix_category
        review_obj.score_factors = [f.model_dump() for f in all_factors]
        review_obj.recommended_action = rec_action
        review_obj.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(review_obj)

    # 11. Update Evidence Graph Node
    try:
        from app.services.evidence_graph_service import build_evidence_graph_for_application
        build_evidence_graph_for_application(db, application_id)
    except Exception as e:
        logger.warning(f"Could not rebuild Evidence Graph after review score generation: {e}")

    return review_obj


def _calculate_evidence_trust(
    doc_types_present: set,
    missing_docs: List[str],
    findings: List[VerificationFindingModel],
    val_records: List[DocumentValidationModel],
    target_id: str
) -> Tuple[float, List[ReviewFactorSchema]]:
    """Calculates Evidence Trust Score (0-100) from deduplicated underlying issues and completeness."""
    score = 100.0
    factors = []

    # 1. Deduplicated Missing Supporting Documents
    if "BANK_STATEMENT" in missing_docs:
        penalty = 20.0
        score -= penalty
        factors.append(ReviewFactorSchema(
            name="Missing Bank Statement",
            factor_type="NEGATIVE",
            weight_contribution=0.20,
            impact_points=-penalty,
            description="Bank statement missing from application package (Incomplete evidence)"
        ))
    if "TAX_RETURN" in missing_docs:
        penalty = 15.0
        score -= penalty
        factors.append(ReviewFactorSchema(
            name="Missing Tax Return",
            factor_type="NEGATIVE",
            weight_contribution=0.15,
            impact_points=-penalty,
            description="Tax return missing from application package (Incomplete evidence)"
        ))
    if "PAYSLIP" in missing_docs:
        penalty = 25.0
        score -= penalty
        factors.append(ReviewFactorSchema(
            name="Missing Payslip",
            factor_type="NEGATIVE",
            weight_contribution=0.25,
            impact_points=-penalty,
            description="Payslip document missing from application package"
        ))

    # 2. Deduplicated Identity Discrepancy (Grouped Underlying Issue)
    id_findings = [f for f in findings if f.result == "MISMATCH" and "identity" in f.verification_type.lower()]
    has_primary_id_mismatch = any(f.rule_name == "app_name_vs_kyc_name" for f in id_findings)

    if has_primary_id_mismatch or len(id_findings) > 0:
        # Group all identity mismatches into a single underlying identity issue penalty (-55 pts total)
        penalty = 55.0 if has_primary_id_mismatch else 25.0
        score -= penalty
        factors.append(ReviewFactorSchema(
            name="Underlying Identity Discrepancy",
            factor_type="NEGATIVE",
            weight_contribution=0.55 if has_primary_id_mismatch else 0.25,
            impact_points=-penalty,
            description=f"Underlying identity mismatch between application and KYC/supporting documents ({len(id_findings)} related comparison finding(s))"
        ))

    # 3. Deduplicated Income / Salary Discrepancy (Grouped Underlying Issue)
    income_mismatches = [
        f for f in findings
        if f.result == "MISMATCH" and ("income" in f.verification_type.lower() or "salary" in f.verification_type.lower())
    ]
    if income_mismatches:
        penalty = 25.0
        score -= penalty
        factors.append(ReviewFactorSchema(
            name="Underlying Financial Discrepancy",
            factor_type="NEGATIVE",
            weight_contribution=0.25,
            impact_points=-penalty,
            description=f"Underlying financial mismatch across income/salary records ({len(income_mismatches)} finding(s))"
        ))

    # 4. Document Structural Validation Failures
    val_fails = [v for v in val_records if v.overall_result == "FAIL"]
    if val_fails:
        penalty = min(20.0, len(val_fails) * 10.0)
        score -= penalty
        factors.append(ReviewFactorSchema(
            name="Document Validation Failures",
            factor_type="NEGATIVE",
            weight_contribution=0.20,
            impact_points=-penalty,
            description=f"{len(val_fails)} document(s) failed structural format validation rules"
        ))

    final_score = max(0.0, min(100.0, score))
    if not factors:
        factors.append(ReviewFactorSchema(
            name="Complete & Consistent Evidence",
            factor_type="POSITIVE",
            weight_contribution=1.0,
            impact_points=100.0,
            description="All expected supporting documents present and cross-document verification passed without issues"
        ))

    return final_score, factors


def _calculate_review_priority(
    rejection_probability: float,
    trust_score: float,
    findings: List[VerificationFindingModel],
    missing_docs: List[str],
    val_records: List[DocumentValidationModel]
) -> Tuple[float, str, List[ReviewFactorSchema]]:
    """
    Calculates Review Priority Score (0-100) combining 5 weighted factors:
    1. ML Risk Contribution (30% weight)
    2. Evidence Trust Deficit (30% weight)
    3. Verification Findings Severity (25% weight)
    4. Document Package Completeness Deficit (10% weight)
    5. Document Validation Check Failures (5% weight)
    """
    factors = []

    # 1. ML Risk Contribution (Weight: 30%)
    ml_contrib = rejection_probability * 30.0
    factors.append(ReviewFactorSchema(
        name="ML Rejection Risk Signal (30% Weight)",
        factor_type="NEUTRAL" if ml_contrib < 10 else "NEGATIVE",
        weight_contribution=ML_RISK_WEIGHT,
        impact_points=round(ml_contrib, 2),
        description=f"Historical loan rejection probability is {rejection_probability:.2%}"
    ))

    # 2. Evidence Trust Deficit (Weight: 30%)
    trust_deficit = (100.0 - trust_score) * 0.30
    factors.append(ReviewFactorSchema(
        name="Evidence Trust Deficit (30% Weight)",
        factor_type="NEUTRAL" if trust_deficit < 5 else "NEGATIVE",
        weight_contribution=EVIDENCE_TRUST_WEIGHT,
        impact_points=round(trust_deficit, 2),
        description=f"Evidence Trust Score is {trust_score:.1f}/100"
    ))

    # 3. Verification Severity Contribution (Weight: 25%)
    errors = [f for f in findings if f.severity == "ERROR" and f.result == "MISMATCH"]
    warnings = [f for f in findings if f.severity in ["WARNING", "ERROR"] and f.result in ["MISMATCH", "WARNING"]]

    if errors:
        ver_contrib = 25.0
    elif warnings:
        ver_contrib = 12.5
    else:
        ver_contrib = 0.0

    factors.append(ReviewFactorSchema(
        name="Cross-Document Verification Findings Severity (25% Weight)",
        factor_type="NEUTRAL" if ver_contrib == 0 else "NEGATIVE",
        weight_contribution=VERIFICATION_SEVERITY_WEIGHT,
        impact_points=round(ver_contrib, 2),
        description=f"Found {len(errors)} error-level mismatch(es) and {len(warnings)} warning(s)"
    ))

    # 4. Document Completeness Deficit (Weight: 10%)
    comp_contrib = 10.0 if missing_docs else 0.0
    factors.append(ReviewFactorSchema(
        name="Document Package Completeness Deficit (10% Weight)",
        factor_type="NEUTRAL" if comp_contrib == 0 else "NEGATIVE",
        weight_contribution=COMPLETENESS_WEIGHT,
        impact_points=round(comp_contrib, 2),
        description="Missing required supporting document(s): " + (", ".join(missing_docs) if missing_docs else "None")
    ))

    # 5. Validation Check Failures (Weight: 5%)
    val_issue_count = sum(1 for v in val_records if v.overall_result in ["FAIL", "PASS_WITH_WARNINGS"])
    val_contrib = 5.0 if val_issue_count > 0 else 0.0
    factors.append(ReviewFactorSchema(
        name="Document Validation Check Failures (5% Weight)",
        factor_type="NEUTRAL" if val_contrib == 0 else "NEGATIVE",
        weight_contribution=VALIDATION_WEIGHT,
        impact_points=round(val_contrib, 2),
        description=f"Identified {val_issue_count} document validation issue(s)"
    ))

    # Primary ID Mismatch Override (ensures A006 identity mismatch triggers HIGH priority level)
    has_primary_id_mismatch = any(f.result == "MISMATCH" and f.rule_name == "app_name_vs_kyc_name" for f in findings)
    id_boost = 25.0 if has_primary_id_mismatch else 0.0
    if has_primary_id_mismatch:
        factors.append(ReviewFactorSchema(
            name="Critical Identity Mismatch Override",
            factor_type="NEGATIVE",
            weight_contribution=0.25,
            impact_points=id_boost,
            description="Application vs KYC identity mismatch triggers high review priority override"
        ))

    total_score = ml_contrib + trust_deficit + ver_contrib + comp_contrib + val_contrib + id_boost
    final_score = max(0.0, min(100.0, total_score))

    if final_score >= 65.0 or has_primary_id_mismatch:
        priority_level = "HIGH"
    elif final_score >= 35.0:
        priority_level = "MEDIUM"
    else:
        priority_level = "LOW"

    return final_score, priority_level, factors


def _derive_matrix_category(
    rejection_probability: float,
    trust_score: float,
    findings: List[VerificationFindingModel],
    missing_docs: List[str]
) -> str:
    """Categorizes 2x2 Risk vs Evidence Matrix (CLEAN, REVIEW, INVESTIGATE)."""
    has_id_mismatch = any(f.result == "MISMATCH" and f.rule_name == "app_name_vs_kyc_name" for f in findings)

    if rejection_probability > 0.65 or trust_score < 50.0 or has_id_mismatch:
        return "INVESTIGATE"
    elif rejection_probability >= 0.35 or trust_score < 80.0 or len(missing_docs) > 0:
        return "REVIEW"
    else:
        return "CLEAN"


def _derive_structured_issues(
    findings: List[VerificationFindingModel],
    val_records: List[DocumentValidationModel]
) -> Tuple[Optional[str], Optional[str], str]:
    """
    Derives structured issues (critical_issue, verification_issue_type, highest_severity)
    directly from deterministic verification findings and document validations.
    Produces NO narrative sentences or human-style text explanations.
    """
    highest_severity = "INFO"
    if any(f.severity == "ERROR" for f in findings) or any(v.overall_result == "FAIL" for v in val_records):
        highest_severity = "ERROR"
    elif any(f.severity == "WARNING" for f in findings) or any(v.overall_result == "PASS_WITH_WARNINGS" for v in val_records):
        highest_severity = "WARNING"

    id_mismatch = [f for f in findings if f.result == "MISMATCH" and f.rule_name == "app_name_vs_kyc_name"]
    salary_mismatch = [
        f for f in findings 
        if f.result == "MISMATCH" and (
            "salary" in f.rule_name.lower() or 
            "income" in f.rule_name.lower() or 
            "income" in f.verification_type.lower() or 
            "salary" in f.verification_type.lower()
        )
    ]
    other_mismatches = [f for f in findings if f.result == "MISMATCH" and f not in id_mismatch and f not in salary_mismatch]

    critical_issue = None
    if id_mismatch:
        critical_issue = "PRIMARY_IDENTITY_MISMATCH"
    elif any(f.severity == "ERROR" and f.result == "MISMATCH" for f in findings):
        critical_issue = "CRITICAL_VERIFICATION_MISMATCH"

    verification_issue_type = None
    if id_mismatch:
        verification_issue_type = "PRIMARY_IDENTITY_MISMATCH"
    elif salary_mismatch:
        verification_issue_type = "FINANCIAL_DISCREPANCY"
    elif other_mismatches:
        verification_issue_type = other_mismatches[0].verification_type
    elif any(f.result in ["MISMATCH", "WARNING"] and "identity" in f.verification_type.lower() for f in findings):
        verification_issue_type = "IDENTITY_WARNING"

    return critical_issue, verification_issue_type, highest_severity


def get_review_assessment_payload(db: Session, application_id: str) -> Dict[str, Any]:
    """Retrieves structured Review Assessment response for API."""
    review_obj = db.query(ReviewAssessmentModel).filter(ReviewAssessmentModel.application_id == application_id).first()
    
    if not review_obj:
        # Compute dynamically if not built yet
        review_obj = compute_and_save_review_assessment(db, application_id)

    factors = [ReviewFactorSchema(**f) for f in (review_obj.score_factors or [])]

    return {
        "review_id": review_obj.review_id,
        "application_id": review_obj.application_id,
        "review_score": review_obj.review_score,
        "review_priority": review_obj.review_priority,
        "ml_risk_score": review_obj.ml_risk_score,
        "ml_risk_level": review_obj.ml_risk_level,
        "evidence_trust_score": review_obj.evidence_trust_score,
        "evidence_trust_level": review_obj.evidence_trust_level,
        "evidence_consistency_category": review_obj.evidence_consistency_category,
        "primary_reason": review_obj.primary_reason if review_obj.primary_reason else None,
        "secondary_reasons": review_obj.secondary_reasons or [],
        "validation_issue_count": review_obj.validation_issue_count,
        "verification_issue_count": review_obj.verification_issue_count,
        "document_completeness_status": review_obj.document_completeness_status,
        "missing_documents": review_obj.missing_documents or [],
        "missing_document": review_obj.missing_document,
        "critical_issue": review_obj.critical_issue,
        "verification_issue_type": review_obj.verification_issue_type,
        "issue_type": review_obj.verification_issue_type,
        "highest_severity": review_obj.highest_severity,
        "risk_evidence_matrix_category": review_obj.risk_evidence_matrix_category,
        "score_factors": factors,
        "scoring_version": review_obj.scoring_version,
        "recommended_action": review_obj.recommended_action,
        "created_at": review_obj.created_at,
        "updated_at": review_obj.updated_at
    }
