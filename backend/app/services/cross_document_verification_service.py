import os
import re
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.db.models import (
    LoanApplicationModel,
    ApplicantModel,
    DocumentModel,
    ExtractedFieldModel,
    ApplicationVerificationModel,
    VerificationFindingModel
)
from app.schemas.verification import VerificationFindingSchema

# Configurable Tolerance Settings
INCOME_TOLERANCE_PERCENT = 10.0


# --- NORMALIZATION UTILITIES ---

def normalize_name(name: Optional[str]) -> str:
    """
    Normalizes names for deterministic comparison:
    - Strips whitespace
    - Converts to lowercase
    - Collapses multiple spaces
    - Removes common punctuation (dots, commas, hyphens)
    """
    if not name:
        return ""
    cleaned = str(name).strip().lower()
    cleaned = re.sub(r'[\.,\-_]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()


def safe_float(val_str: Optional[str]) -> Optional[float]:
    """Safely converts string to float."""
    if val_str is None:
        return None
    try:
        return float(val_str)
    except (ValueError, TypeError):
        return None


def calculate_income_difference(val_a: float, val_b: float, tolerance_percent: float = INCOME_TOLERANCE_PERCENT) -> Tuple[float, float, bool]:
    """
    Calculates absolute difference, percentage difference, and whether within tolerance.
    Returns: (difference, difference_percent, is_within_tolerance)
    """
    diff = abs(val_a - val_b)
    max_val = max(abs(val_a), abs(val_b))
    if max_val == 0.0:
        return 0.0, 0.0, True
    diff_pct = (diff / max_val) * 100.0
    within = diff_pct <= tolerance_percent
    return round(diff, 2), round(diff_pct, 2), within


# --- DATA LOADERS ---

def get_application_profile_data(db: Session, application_id: str) -> Dict[str, Any]:
    """
    Loads application data from LoanApplicationModel and enriches with CSV profile data
    if application_id matches synthetic applicant dataset (e.g. A001..A010).
    """
    app_obj = db.query(LoanApplicationModel).filter(LoanApplicationModel.application_id == application_id).first()
    if not app_obj:
        raise ValueError(f"Application '{application_id}' not found.")

    profile_data = {
        "application_id": app_obj.application_id,
        "applicant_name": app_obj.applicant_name,
        "income_annum": app_obj.income_annum,
        "loan_amount": app_obj.loan_amount,
        "loan_term": None,
        "cibil_score": None,
        "employer": None,
        "address": None,
        "dummy_kyc_id": None,
        "no_of_dependents": None,
        "education": None,
        "self_employed": None,
        "residential_assets_value": None,
        "commercial_assets_value": None,
        "luxury_assets_value": None,
        "bank_asset_value": None
    }

    # Extract target applicant code if available (e.g., "A001" or "APP-A001" -> "A001")
    target_id = application_id.replace("APP-", "").upper()
    profiles_path = os.path.join(settings.DATA_DIR, "processed", "applicant_profiles.csv")

    if os.path.exists(profiles_path):
        try:
            df = pd.read_csv(profiles_path)
            row = df[df["applicant_id"].astype(str).str.upper() == target_id]
            if not row.empty:
                r = row.iloc[0]
                profile_data["applicant_name"] = str(r["applicant_name"]) if pd.notna(r["applicant_name"]) else profile_data["applicant_name"]
                profile_data["income_annum"] = float(r["income_annum"]) if pd.notna(r["income_annum"]) else profile_data["income_annum"]
                profile_data["loan_amount"] = float(r["loan_amount"]) if pd.notna(r["loan_amount"]) else profile_data["loan_amount"]
                profile_data["loan_term"] = int(r["loan_term"]) if pd.notna(r["loan_term"]) else None
                profile_data["cibil_score"] = int(r["cibil_score"]) if pd.notna(r["cibil_score"]) else None
                profile_data["employer"] = str(r["employer"]) if pd.notna(r["employer"]) else None
                profile_data["address"] = str(r["address"]) if pd.notna(r["address"]) else None
                profile_data["dummy_kyc_id"] = str(r["dummy_kyc_id"]) if pd.notna(r["dummy_kyc_id"]) else None
                profile_data["no_of_dependents"] = int(r["no_of_dependents"]) if pd.notna(r["no_of_dependents"]) else None
                profile_data["education"] = str(r["education"]).strip() if pd.notna(r["education"]) else None
                profile_data["self_employed"] = str(r["self_employed"]).strip() if pd.notna(r["self_employed"]) else None
                profile_data["residential_assets_value"] = float(r["residential_assets_value"]) if pd.notna(r["residential_assets_value"]) else None
                profile_data["commercial_assets_value"] = float(r["commercial_assets_value"]) if pd.notna(r["commercial_assets_value"]) else None
                profile_data["luxury_assets_value"] = float(r["luxury_assets_value"]) if pd.notna(r["luxury_assets_value"]) else None
                profile_data["bank_asset_value"] = float(r["bank_asset_value"]) if pd.notna(r["bank_asset_value"]) else None
        except Exception as e:
            logger.warning(f"Error loading applicant_profiles.csv for '{application_id}': {e}")

    # Check database ApplicantModel for customer created applications
    applicant_rec = db.query(ApplicantModel).filter(
        (ApplicantModel.applicant_id == application_id) |
        (ApplicantModel.applicant_id == target_id)
    ).first()
    if applicant_rec:
        if applicant_rec.applicant_name:
            profile_data["applicant_name"] = applicant_rec.applicant_name
        if applicant_rec.income_annum is not None and applicant_rec.income_annum > 0:
            profile_data["income_annum"] = applicant_rec.income_annum
        if applicant_rec.loan_amount is not None and applicant_rec.loan_amount > 0:
            profile_data["loan_amount"] = applicant_rec.loan_amount
        if applicant_rec.loan_term is not None:
            profile_data["loan_term"] = applicant_rec.loan_term
        if applicant_rec.cibil_score is not None:
            profile_data["cibil_score"] = applicant_rec.cibil_score
        if applicant_rec.employer:
            profile_data["employer"] = applicant_rec.employer
        if applicant_rec.address:
            profile_data["address"] = applicant_rec.address
        if applicant_rec.dummy_kyc_id:
            profile_data["dummy_kyc_id"] = applicant_rec.dummy_kyc_id
        if applicant_rec.no_of_dependents is not None:
            profile_data["no_of_dependents"] = applicant_rec.no_of_dependents
        if applicant_rec.education:
            profile_data["education"] = applicant_rec.education
        if applicant_rec.self_employed:
            profile_data["self_employed"] = applicant_rec.self_employed
        if applicant_rec.residential_assets_value is not None:
            profile_data["residential_assets_value"] = applicant_rec.residential_assets_value
        if applicant_rec.commercial_assets_value is not None:
            profile_data["commercial_assets_value"] = applicant_rec.commercial_assets_value
        if applicant_rec.luxury_assets_value is not None:
            profile_data["luxury_assets_value"] = applicant_rec.luxury_assets_value
        if applicant_rec.bank_asset_value is not None:
            profile_data["bank_asset_value"] = applicant_rec.bank_asset_value
        if applicant_rec.scenario:
            profile_data["scenario"] = applicant_rec.scenario

    return profile_data


def get_application_documents_map(db: Session, application_id: str) -> Dict[str, Tuple[DocumentModel, Dict[str, ExtractedFieldModel]]]:
    """
    Retrieves active documents for application and maps classified type to (DocumentModel, fields_map).
    """
    target_id = application_id.replace("APP-", "").upper()
    
    # Query documents by application_id or applicant_id
    docs = db.query(DocumentModel).filter(
        (DocumentModel.application_id == application_id) | (DocumentModel.applicant_id == target_id),
        DocumentModel.processing_status != "DELETED"
    ).all()

    docs_map = {}
    for doc in docs:
        doc_type = (doc.classified_document_type or doc.document_type or "OTHER").upper()
        
        # Load extracted fields into a map
        fields = db.query(ExtractedFieldModel).filter(ExtractedFieldModel.document_id == doc.document_id).all()
        fields_map = {f.field_name: f for f in fields}

        # Save primary document per category
        if doc_type not in docs_map or doc.classification_confidence > docs_map[doc_type][0].classification_confidence:
            docs_map[doc_type] = (doc, fields_map)

    return docs_map


# --- DETERMINISTIC VERIFICATION ENGINE ---

def verify_and_save_application(db: Session, application_id: str) -> LoanApplicationModel:
    """
    Executes cross-document verification engine comparing application profile data
    with extracted fields from PAYSLIP, BANK_STATEMENT, TAX_RETURN, and KYC documents.
    """
    app_obj = db.query(LoanApplicationModel).filter(LoanApplicationModel.application_id == application_id).first()
    if not app_obj:
        raise ValueError(f"Application '{application_id}' not found.")

    # Idempotency check
    if app_obj.verification_status == "COMPLETED" and app_obj.verifications:
        logger.info(f"Application '{application_id}' already verified. Returning cached verification.")
        return app_obj

    app_obj.verification_status = "VERIFYING"
    db.commit()

    profile = get_application_profile_data(db, application_id)
    docs_map = get_application_documents_map(db, application_id)

    findings: List[VerificationFindingSchema] = []

    # Unpack document entries
    payslip_entry = docs_map.get("PAYSLIP")
    bank_entry = docs_map.get("BANK_STATEMENT")
    tax_entry = docs_map.get("TAX_RETURN")
    kyc_entry = docs_map.get("KYC")

    # =========================================================================
    # 1. IDENTITY COMPARISONS
    # =========================================================================

    app_name = profile["applicant_name"]
    norm_app_name = normalize_name(app_name)

    # 1A. Application Name ↔ KYC Full Name
    if kyc_entry and "full_name" in kyc_entry[1] and kyc_entry[1]["full_name"].normalized_value:
        kyc_doc, kyc_fields = kyc_entry
        kyc_name = kyc_fields["full_name"].normalized_value
        norm_kyc_name = normalize_name(kyc_name)

        if norm_app_name == norm_kyc_name:
            findings.append(VerificationFindingSchema(
                verification_type="IDENTITY_COMPARISON",
                rule_name="app_name_vs_kyc_name",
                source_a="APPLICATION",
                field_a="applicant_name",
                value_a=app_name,
                source_b="KYC",
                field_b="full_name",
                value_b=kyc_name,
                normalized_value_a=norm_app_name,
                normalized_value_b=norm_kyc_name,
                result="MATCH",
                severity="INFO",
                comparison_document_id=kyc_doc.document_id,
                message="Application name matches KYC full name.",
                evidence=f"Application: '{app_name}' | KYC: '{kyc_name}'"
            ))
        else:
            findings.append(VerificationFindingSchema(
                verification_type="IDENTITY_COMPARISON",
                rule_name="app_name_vs_kyc_name",
                source_a="APPLICATION",
                field_a="applicant_name",
                value_a=app_name,
                source_b="KYC",
                field_b="full_name",
                value_b=kyc_name,
                normalized_value_a=norm_app_name,
                normalized_value_b=norm_kyc_name,
                result="MISMATCH",
                severity="ERROR",
                comparison_document_id=kyc_doc.document_id,
                message=f"Identity Mismatch: Application name '{app_name}' does not match KYC full name '{kyc_name}'.",
                evidence=f"Application: '{app_name}' != KYC: '{kyc_name}'"
            ))
    else:
        findings.append(VerificationFindingSchema(
            verification_type="IDENTITY_COMPARISON",
            rule_name="app_name_vs_kyc_name",
            source_a="APPLICATION",
            field_a="applicant_name",
            value_a=app_name,
            source_b="KYC",
            field_b="full_name",
            value_b=None,
            result="NOT_AVAILABLE",
            severity="INFO",
            comparison_document_id=kyc_entry[0].document_id if kyc_entry else None,
            message="DOCUMENT_MISSING: KYC document or full_name not available for identity verification.",
            evidence="KYC document or full_name missing."
        ))

    # 1B. KYC Full Name ↔ Payslip Employee Name
    if kyc_entry and "full_name" in kyc_entry[1] and payslip_entry and "employee_name" in payslip_entry[1]:
        kyc_name = kyc_entry[1]["full_name"].normalized_value
        payslip_name = payslip_entry[1]["employee_name"].normalized_value
        norm_kyc = normalize_name(kyc_name)
        norm_payslip = normalize_name(payslip_name)

        if norm_kyc == norm_payslip:
            findings.append(VerificationFindingSchema(
                verification_type="IDENTITY_COMPARISON",
                rule_name="kyc_name_vs_payslip_name",
                source_a="KYC",
                field_a="full_name",
                value_a=kyc_name,
                source_b="PAYSLIP",
                field_b="employee_name",
                value_b=payslip_name,
                normalized_value_a=norm_kyc,
                normalized_value_b=norm_payslip,
                result="MATCH",
                severity="INFO",
                source_document_id=kyc_entry[0].document_id,
                comparison_document_id=payslip_entry[0].document_id,
                message="KYC full name matches Payslip employee name.",
                evidence=f"KYC: '{kyc_name}' | Payslip: '{payslip_name}'"
            ))
        else:
            findings.append(VerificationFindingSchema(
                verification_type="IDENTITY_COMPARISON",
                rule_name="kyc_name_vs_payslip_name",
                source_a="KYC",
                field_a="full_name",
                value_a=kyc_name,
                source_b="PAYSLIP",
                field_b="employee_name",
                value_b=payslip_name,
                normalized_value_a=norm_kyc,
                normalized_value_b=norm_payslip,
                result="MISMATCH",
                severity="WARNING",
                source_document_id=kyc_entry[0].document_id,
                comparison_document_id=payslip_entry[0].document_id,
                message=f"Identity Discrepancy: KYC full name '{kyc_name}' does not match Payslip employee name '{payslip_name}'.",
                evidence=f"KYC: '{kyc_name}' != Payslip: '{payslip_name}'"
            ))

    # 1C. KYC Full Name ↔ Bank Statement Account Holder
    if kyc_entry and "full_name" in kyc_entry[1] and bank_entry and "account_holder_name" in bank_entry[1]:
        kyc_name = kyc_entry[1]["full_name"].normalized_value
        bank_name = bank_entry[1]["account_holder_name"].normalized_value
        norm_kyc = normalize_name(kyc_name)
        norm_bank = normalize_name(bank_name)

        if norm_kyc == norm_bank:
            findings.append(VerificationFindingSchema(
                verification_type="IDENTITY_COMPARISON",
                rule_name="kyc_name_vs_bank_holder",
                source_a="KYC",
                field_a="full_name",
                value_a=kyc_name,
                source_b="BANK_STATEMENT",
                field_b="account_holder_name",
                value_b=bank_name,
                normalized_value_a=norm_kyc,
                normalized_value_b=norm_bank,
                result="MATCH",
                severity="INFO",
                source_document_id=kyc_entry[0].document_id,
                comparison_document_id=bank_entry[0].document_id,
                message="KYC full name matches Bank Statement account holder name.",
                evidence=f"KYC: '{kyc_name}' | Bank: '{bank_name}'"
            ))
        else:
            findings.append(VerificationFindingSchema(
                verification_type="IDENTITY_COMPARISON",
                rule_name="kyc_name_vs_bank_holder",
                source_a="KYC",
                field_a="full_name",
                value_a=kyc_name,
                source_b="BANK_STATEMENT",
                field_b="account_holder_name",
                value_b=bank_name,
                normalized_value_a=norm_kyc,
                normalized_value_b=norm_bank,
                result="MISMATCH",
                severity="WARNING",
                source_document_id=kyc_entry[0].document_id,
                comparison_document_id=bank_entry[0].document_id,
                message=f"Identity Discrepancy: KYC full name '{kyc_name}' does not match Bank account holder '{bank_name}'.",
                evidence=f"KYC: '{kyc_name}' != Bank: '{bank_name}'"
            ))

    # 1D. KYC Full Name ↔ Tax Return Taxpayer Name
    if kyc_entry and "full_name" in kyc_entry[1] and tax_entry and "taxpayer_name" in tax_entry[1]:
        kyc_name = kyc_entry[1]["full_name"].normalized_value
        tax_name = tax_entry[1]["taxpayer_name"].normalized_value
        norm_kyc = normalize_name(kyc_name)
        norm_tax = normalize_name(tax_name)

        if norm_kyc == norm_tax:
            findings.append(VerificationFindingSchema(
                verification_type="IDENTITY_COMPARISON",
                rule_name="kyc_name_vs_tax_name",
                source_a="KYC",
                field_a="full_name",
                value_a=kyc_name,
                source_b="TAX_RETURN",
                field_b="taxpayer_name",
                value_b=tax_name,
                normalized_value_a=norm_kyc,
                normalized_value_b=norm_tax,
                result="MATCH",
                severity="INFO",
                source_document_id=kyc_entry[0].document_id,
                comparison_document_id=tax_entry[0].document_id,
                message="KYC full name matches Tax Return taxpayer name.",
                evidence=f"KYC: '{kyc_name}' | Tax: '{tax_name}'"
            ))
        else:
            findings.append(VerificationFindingSchema(
                verification_type="IDENTITY_COMPARISON",
                rule_name="kyc_name_vs_tax_name",
                source_a="KYC",
                field_a="full_name",
                value_a=kyc_name,
                source_b="TAX_RETURN",
                field_b="taxpayer_name",
                value_b=tax_name,
                normalized_value_a=norm_kyc,
                normalized_value_b=norm_tax,
                result="MISMATCH",
                severity="WARNING",
                source_document_id=kyc_entry[0].document_id,
                comparison_document_id=tax_entry[0].document_id,
                message=f"Identity Discrepancy: KYC full name '{kyc_name}' does not match Tax taxpayer name '{tax_name}'.",
                evidence=f"KYC: '{kyc_name}' != Tax: '{tax_name}'"
            ))

    # =========================================================================
    # 2. INCOME COMPARISONS
    # =========================================================================

    app_income = profile.get("income_annum")

    # 2A. Application Income ↔ Tax Return Income
    if tax_entry and "declared_annual_income" in tax_entry[1]:
        tax_doc, tax_fields = tax_entry
        tax_inc_val = safe_float(tax_fields["declared_annual_income"].normalized_value)

        if app_income is not None and tax_inc_val is not None:
            diff, diff_pct, is_within = calculate_income_difference(app_income, tax_inc_val, INCOME_TOLERANCE_PERCENT)
            if is_within:
                findings.append(VerificationFindingSchema(
                    verification_type="INCOME_COMPARISON",
                    rule_name="app_income_vs_tax_income",
                    source_a="APPLICATION",
                    field_a="income_annum",
                    value_a=str(app_income),
                    source_b="TAX_RETURN",
                    field_b="declared_annual_income",
                    value_b=str(tax_inc_val),
                    normalized_value_a=str(app_income),
                    normalized_value_b=str(tax_inc_val),
                    difference=diff,
                    difference_percent=diff_pct,
                    tolerance_percent=INCOME_TOLERANCE_PERCENT,
                    result="MATCH",
                    severity="INFO",
                    comparison_document_id=tax_doc.document_id,
                    message=f"Application annual income ({app_income:.0f}) matches Tax Return declared income ({tax_inc_val:.0f}).",
                    evidence=f"App: {app_income:.0f} | Tax: {tax_inc_val:.0f} | Diff: {diff_pct:.1f}% <= {INCOME_TOLERANCE_PERCENT}%"
                ))
            else:
                findings.append(VerificationFindingSchema(
                    verification_type="INCOME_COMPARISON",
                    rule_name="app_income_vs_tax_income",
                    source_a="APPLICATION",
                    field_a="income_annum",
                    value_a=str(app_income),
                    source_b="TAX_RETURN",
                    field_b="declared_annual_income",
                    value_b=str(tax_inc_val),
                    normalized_value_a=str(app_income),
                    normalized_value_b=str(tax_inc_val),
                    difference=diff,
                    difference_percent=diff_pct,
                    tolerance_percent=INCOME_TOLERANCE_PERCENT,
                    result="MISMATCH",
                    severity="WARNING",
                    comparison_document_id=tax_doc.document_id,
                    message=f"Income Discrepancy: Application annual income ({app_income:.0f}) differs from Tax Return declared income ({tax_inc_val:.0f}) by {diff_pct:.1f}% (tolerance: {INCOME_TOLERANCE_PERCENT}%).",
                    evidence=f"App: {app_income:.0f} != Tax: {tax_inc_val:.0f} | Diff: {diff_pct:.1f}% > {INCOME_TOLERANCE_PERCENT}%"
                ))
    else:
        findings.append(VerificationFindingSchema(
            verification_type="INCOME_COMPARISON",
            rule_name="app_income_vs_tax_income",
            source_a="APPLICATION",
            field_a="income_annum",
            value_a=str(app_income) if app_income is not None else None,
            source_b="TAX_RETURN",
            field_b="declared_annual_income",
            value_b=None,
            result="NOT_AVAILABLE",
            severity="INFO",
            message="DOCUMENT_MISSING: TAX_RETURN document not available for annual income comparison.",
            evidence="TAX_RETURN document or declared_annual_income missing."
        ))

    # 2B. Application Income ↔ Payslip Annualized Gross Salary
    if payslip_entry and ("monthly_gross_salary" in payslip_entry[1] or "gross_salary" in payslip_entry[1]):
        pay_doc, pay_fields = payslip_entry
        f_gross = pay_fields.get("monthly_gross_salary") or pay_fields.get("gross_salary")
        gross_monthly = safe_float(f_gross.normalized_value) if f_gross else None

        if app_income is not None and gross_monthly is not None:
            annualized_gross = gross_monthly * 12.0
            diff, diff_pct, is_within = calculate_income_difference(app_income, annualized_gross, INCOME_TOLERANCE_PERCENT)
            if is_within:
                findings.append(VerificationFindingSchema(
                    verification_type="INCOME_COMPARISON",
                    rule_name="app_income_vs_payslip_annualized",
                    source_a="APPLICATION",
                    field_a="income_annum",
                    value_a=str(app_income),
                    source_b="PAYSLIP",
                    field_b="monthly_gross_salary_annualized",
                    value_b=str(annualized_gross),
                    normalized_value_a=str(app_income),
                    normalized_value_b=str(annualized_gross),
                    difference=diff,
                    difference_percent=diff_pct,
                    tolerance_percent=INCOME_TOLERANCE_PERCENT,
                    result="MATCH",
                    severity="INFO",
                    comparison_document_id=pay_doc.document_id,
                    message=f"Application annual income ({app_income:.0f}) matches Payslip annualized gross income ({annualized_gross:.0f}).",
                    evidence=f"App: {app_income:.0f} | Payslip Annualized ({gross_monthly:.0f}x12): {annualized_gross:.0f}"
                ))
            else:
                findings.append(VerificationFindingSchema(
                    verification_type="INCOME_COMPARISON",
                    rule_name="app_income_vs_payslip_annualized",
                    source_a="APPLICATION",
                    field_a="income_annum",
                    value_a=str(app_income),
                    source_b="PAYSLIP",
                    field_b="monthly_gross_salary_annualized",
                    value_b=str(annualized_gross),
                    normalized_value_a=str(app_income),
                    normalized_value_b=str(annualized_gross),
                    difference=diff,
                    difference_percent=diff_pct,
                    tolerance_percent=INCOME_TOLERANCE_PERCENT,
                    result="MISMATCH",
                    severity="WARNING",
                    comparison_document_id=pay_doc.document_id,
                    message=f"Income Discrepancy: Application annual income ({app_income:.0f}) differs from Payslip annualized gross income ({annualized_gross:.0f}) by {diff_pct:.1f}%.",
                    evidence=f"App: {app_income:.0f} != Payslip Annualized: {annualized_gross:.0f} | Diff: {diff_pct:.1f}% > {INCOME_TOLERANCE_PERCENT}%"
                ))

    # 2C. Payslip Annualized Gross ↔ Tax Return Declared Income
    if payslip_entry and tax_entry and ("monthly_gross_salary" in payslip_entry[1] or "gross_salary" in payslip_entry[1]) and "declared_annual_income" in tax_entry[1]:
        pay_doc, pay_fields = payslip_entry
        tax_doc, tax_fields = tax_entry
        f_gross = pay_fields.get("monthly_gross_salary") or pay_fields.get("gross_salary")
        gross_monthly = safe_float(f_gross.normalized_value) if f_gross else None
        tax_inc_val = safe_float(tax_fields["declared_annual_income"].normalized_value)

        if gross_monthly is not None and tax_inc_val is not None:
            annualized_gross = gross_monthly * 12.0
            diff, diff_pct, is_within = calculate_income_difference(annualized_gross, tax_inc_val, INCOME_TOLERANCE_PERCENT)
            if is_within:
                findings.append(VerificationFindingSchema(
                    verification_type="INCOME_COMPARISON",
                    rule_name="payslip_annualized_vs_tax_income",
                    source_a="PAYSLIP",
                    field_a="monthly_gross_salary_annualized",
                    value_a=str(annualized_gross),
                    source_b="TAX_RETURN",
                    field_b="declared_annual_income",
                    value_b=str(tax_inc_val),
                    normalized_value_a=str(annualized_gross),
                    normalized_value_b=str(tax_inc_val),
                    difference=diff,
                    difference_percent=diff_pct,
                    tolerance_percent=INCOME_TOLERANCE_PERCENT,
                    result="MATCH",
                    severity="INFO",
                    source_document_id=pay_doc.document_id,
                    comparison_document_id=tax_doc.document_id,
                    message=f"Payslip annualized gross income ({annualized_gross:.0f}) matches Tax Return declared income ({tax_inc_val:.0f}).",
                    evidence=f"Payslip Annualized: {annualized_gross:.0f} | Tax: {tax_inc_val:.0f}"
                ))
            else:
                findings.append(VerificationFindingSchema(
                    verification_type="INCOME_COMPARISON",
                    rule_name="payslip_annualized_vs_tax_income",
                    source_a="PAYSLIP",
                    field_a="monthly_gross_salary_annualized",
                    value_a=str(annualized_gross),
                    source_b="TAX_RETURN",
                    field_b="declared_annual_income",
                    value_b=str(tax_inc_val),
                    normalized_value_a=str(annualized_gross),
                    normalized_value_b=str(tax_inc_val),
                    difference=diff,
                    difference_percent=diff_pct,
                    tolerance_percent=INCOME_TOLERANCE_PERCENT,
                    result="MISMATCH",
                    severity="WARNING",
                    source_document_id=pay_doc.document_id,
                    comparison_document_id=tax_doc.document_id,
                    message=f"Income Discrepancy: Payslip annualized income ({annualized_gross:.0f}) differs from Tax Return declared income ({tax_inc_val:.0f}) by {diff_pct:.1f}%.",
                    evidence=f"Payslip Annualized: {annualized_gross:.0f} != Tax: {tax_inc_val:.0f} | Diff: {diff_pct:.1f}% > {INCOME_TOLERANCE_PERCENT}%"
                ))

    # =========================================================================
    # 3. SALARY CREDIT COMPARISONS (PAYSLIP ↔ BANK STATEMENT)
    # =========================================================================

    if payslip_entry and bank_entry:
        pay_doc, pay_fields = payslip_entry
        bank_doc, bank_fields = bank_entry

        f_gross = pay_fields.get("monthly_gross_salary") or pay_fields.get("gross_salary")
        gross_val = safe_float(f_gross.normalized_value) if f_gross else None

        f_net = pay_fields.get("monthly_net_salary") or pay_fields.get("net_salary")
        net_val = safe_float(f_net.normalized_value) if f_net else None

        f_credit = bank_fields.get("salary_credit_amount")
        credit_val = safe_float(f_credit.normalized_value) if f_credit else None

        if credit_val is not None:
            net_diff, net_pct, net_within = calculate_income_difference(net_val, credit_val, INCOME_TOLERANCE_PERCENT) if net_val is not None else (0.0, 0.0, False)
            gross_diff, gross_pct, gross_within = calculate_income_difference(gross_val, credit_val, INCOME_TOLERANCE_PERCENT) if gross_val is not None else (0.0, 0.0, False)

            if net_within or gross_within:
                matched_val = net_val if net_within else gross_val
                field_name_used = "monthly_net_salary" if net_within else "monthly_gross_salary"
                diff_used = net_diff if net_within else gross_diff
                pct_used = net_pct if net_within else gross_pct

                findings.append(VerificationFindingSchema(
                    verification_type="SALARY_COMPARISON",
                    rule_name="payslip_salary_vs_bank_credit",
                    source_a="PAYSLIP",
                    field_a=field_name_used,
                    value_a=str(matched_val),
                    source_b="BANK_STATEMENT",
                    field_b="salary_credit_amount",
                    value_b=str(credit_val),
                    normalized_value_a=str(matched_val),
                    normalized_value_b=str(credit_val),
                    difference=diff_used,
                    difference_percent=pct_used,
                    tolerance_percent=INCOME_TOLERANCE_PERCENT,
                    result="MATCH",
                    severity="INFO",
                    source_document_id=pay_doc.document_id,
                    comparison_document_id=bank_doc.document_id,
                    message=f"Payslip salary ({matched_val:.0f}) matches Bank Statement salary credit ({credit_val:.0f}).",
                    evidence=f"Payslip ({field_name_used}): {matched_val:.0f} | Bank Credit: {credit_val:.0f} | Diff: {pct_used:.1f}% <= {INCOME_TOLERANCE_PERCENT}%"
                ))
            else:
                base_val = net_val if net_val is not None else (gross_val or 0.0)
                diff, diff_pct, _ = calculate_income_difference(base_val, credit_val, INCOME_TOLERANCE_PERCENT)
                findings.append(VerificationFindingSchema(
                    verification_type="SALARY_COMPARISON",
                    rule_name="payslip_salary_vs_bank_credit",
                    source_a="PAYSLIP",
                    field_a="monthly_net_salary",
                    value_a=str(base_val),
                    source_b="BANK_STATEMENT",
                    field_b="salary_credit_amount",
                    value_b=str(credit_val),
                    normalized_value_a=str(base_val),
                    normalized_value_b=str(credit_val),
                    difference=diff,
                    difference_percent=diff_pct,
                    tolerance_percent=INCOME_TOLERANCE_PERCENT,
                    result="MISMATCH",
                    severity="WARNING",
                    source_document_id=pay_doc.document_id,
                    comparison_document_id=bank_doc.document_id,
                    message=f"Salary Credit Discrepancy: Payslip salary ({base_val:.0f}) differs from Bank salary credit ({credit_val:.0f}) by {diff_pct:.1f}%.",
                    evidence=f"Payslip: {base_val:.0f} != Bank Credit: {credit_val:.0f} | Diff: {diff_pct:.1f}% > {INCOME_TOLERANCE_PERCENT}%"
                ))
        else:
            findings.append(VerificationFindingSchema(
                verification_type="SALARY_COMPARISON",
                rule_name="payslip_salary_vs_bank_credit",
                source_a="PAYSLIP",
                field_a="monthly_net_salary",
                value_a=str(net_val) if net_val else None,
                source_b="BANK_STATEMENT",
                field_b="salary_credit_amount",
                value_b=None,
                result="NOT_AVAILABLE",
                severity="INFO",
                source_document_id=pay_doc.document_id,
                comparison_document_id=bank_doc.document_id,
                message="Bank salary credit amount could not be extracted for comparison.",
                evidence="Bank Statement salary credit transaction missing."
            ))
    elif not bank_entry:
        findings.append(VerificationFindingSchema(
            verification_type="SALARY_COMPARISON",
            rule_name="payslip_salary_vs_bank_credit",
            source_a="PAYSLIP",
            field_a="monthly_net_salary",
            value_a=None,
            source_b="BANK_STATEMENT",
            field_b="salary_credit_amount",
            value_b=None,
            result="NOT_AVAILABLE",
            severity="INFO",
            message="DOCUMENT_MISSING: BANK_STATEMENT document not available for salary credit comparison.",
            evidence="BANK_STATEMENT document missing."
        ))

    # =========================================================================
    # 4. SUMMARY CALCULATION & PERSISTENCE
    # =========================================================================

    total_cnt = len(findings)
    matched_cnt = len([f for f in findings if f.result == "MATCH"])
    mismatched_cnt = len([f for f in findings if f.result == "MISMATCH"])
    unavail_cnt = len([f for f in findings if f.result == "NOT_AVAILABLE"])
    warning_cnt = len([f for f in findings if f.severity == "WARNING"])
    error_cnt = len([f for f in findings if f.severity == "ERROR"])

    if error_cnt > 0 or mismatched_cnt > 0:
        overall = "MISMATCHES_FOUND"
        summary = f"Cross-document verification identified {mismatched_cnt} mismatch(es) ({error_cnt} error(s), {warning_cnt} warning(s))."
    elif warning_cnt > 0:
        overall = "PASSED_WITH_WARNINGS"
        summary = f"Cross-document verification passed with {warning_cnt} warning(s)."
    elif matched_cnt > 0:
        overall = "MATCH"
        summary = f"All {matched_cnt} cross-document comparisons matched successfully."
    else:
        overall = "INCOMPLETE"
        summary = "No cross-document comparisons could be completed."

    # Delete existing verification record if reprocessing
    db.query(ApplicationVerificationModel).filter(ApplicationVerificationModel.application_id == application_id).delete()

    ver_record = ApplicationVerificationModel(
        application_id=application_id,
        status="COMPLETED",
        overall_result=overall,
        summary=summary,
        total_comparisons=total_cnt,
        matched_comparisons=matched_cnt,
        mismatched_comparisons=mismatched_cnt,
        unavailable_comparisons=unavail_cnt,
        warning_count=warning_cnt,
        error_count=error_cnt,
        verification_error=None,
        verified_at=datetime.utcnow()
    )
    db.add(ver_record)
    db.flush()

    for f in findings:
        finding_model = VerificationFindingModel(
            verification_id=ver_record.id,
            verification_type=f.verification_type,
            rule_name=f.rule_name,
            source_a=f.source_a,
            field_a=f.field_a,
            value_a=f.value_a,
            source_b=f.source_b,
            field_b=f.field_b,
            value_b=f.value_b,
            normalized_value_a=f.normalized_value_a,
            normalized_value_b=f.normalized_value_b,
            difference=f.difference,
            difference_percent=f.difference_percent,
            tolerance_percent=f.tolerance_percent,
            result=f.result,
            severity=f.severity,
            source_document_id=f.source_document_id,
            comparison_document_id=f.comparison_document_id,
            message=f.message,
            evidence=f.evidence
        )
        db.add(finding_model)

    app_obj.verification_status = "COMPLETED"
    app_obj.verification_overall_result = overall
    app_obj.verification_error = None
    app_obj.verified_at = datetime.utcnow()

    db.commit()
    db.refresh(app_obj)
    return app_obj


def get_verification_payload(db: Session, application_id: str) -> Dict[str, Any]:
    """Retrieves verification response payload for API response."""
    app_obj = db.query(LoanApplicationModel).filter(LoanApplicationModel.application_id == application_id).first()
    if not app_obj:
        raise ValueError(f"Application '{application_id}' not found.")

    ver_record = db.query(ApplicationVerificationModel).filter(ApplicationVerificationModel.application_id == application_id).first()
    if not ver_record:
        return {
            "application_id": app_obj.application_id,
            "status": app_obj.verification_status,
            "overall_result": app_obj.verification_overall_result or "NOT_VERIFIED",
            "summary": "Verification not performed.",
            "total_comparisons": 0,
            "matched_comparisons": 0,
            "mismatched_comparisons": 0,
            "unavailable_comparisons": 0,
            "warning_count": 0,
            "error_count": 0,
            "findings": [],
            "error": app_obj.verification_error,
            "verified_at": app_obj.verified_at
        }

    finding_models = db.query(VerificationFindingModel).filter(VerificationFindingModel.verification_id == ver_record.id).all()
    findings_list = [VerificationFindingSchema.model_validate(f) for f in finding_models]

    return {
        "application_id": app_obj.application_id,
        "status": ver_record.status,
        "overall_result": ver_record.overall_result,
        "summary": ver_record.summary,
        "total_comparisons": ver_record.total_comparisons,
        "matched_comparisons": ver_record.matched_comparisons,
        "mismatched_comparisons": ver_record.mismatched_comparisons,
        "unavailable_comparisons": ver_record.unavailable_comparisons,
        "warning_count": ver_record.warning_count,
        "error_count": ver_record.error_count,
        "findings": findings_list,
        "error": ver_record.verification_error,
        "verified_at": ver_record.verified_at
    }
