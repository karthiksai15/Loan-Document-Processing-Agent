import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.db.models import DocumentModel, ExtractedFieldModel, DocumentValidationModel, ValidationCheckModel
from app.schemas.validation import ValidationCheckSchema

# --- HELPER PARSERS ---

def safe_float(val_str: Optional[str]) -> Optional[float]:
    if not val_str:
        return None
    try:
        return float(val_str)
    except ValueError:
        return None

def safe_date(val_str: Optional[str]) -> Optional[datetime]:
    if not val_str:
        return None
    try:
        return datetime.strptime(val_str.strip(), "%Y-%m-%d")
    except ValueError:
        return None

# --- CATEGORY VALIDATORS ---

def validate_payslip_fields(fields: Dict[str, ExtractedFieldModel]) -> List[ValidationCheckSchema]:
    checks = []

    # 1. Employee Name
    f_emp = fields.get("employee_name")
    if f_emp and f_emp.normalized_value:
        checks.append(ValidationCheckSchema(
            check_name="employee_name_present",
            severity="INFO",
            status="PASS",
            message="Employee name is present.",
            field_name="employee_name",
            evidence=f_emp.evidence
        ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="employee_name_present",
            severity="ERROR",
            status="FAIL",
            message="Missing required field 'employee_name'.",
            field_name="employee_name"
        ))

    # 2. Employer Name
    f_employer = fields.get("employer_name")
    if f_employer and f_employer.normalized_value:
        checks.append(ValidationCheckSchema(
            check_name="employer_name_present",
            severity="INFO",
            status="PASS",
            message="Employer name is present.",
            field_name="employer_name",
            evidence=f_employer.evidence
        ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="employer_name_present",
            severity="ERROR",
            status="FAIL",
            message="Missing required field 'employer_name'.",
            field_name="employer_name"
        ))

    # 3. Pay Period
    f_period = fields.get("pay_period")
    if f_period and f_period.normalized_value:
        checks.append(ValidationCheckSchema(
            check_name="pay_period_valid",
            severity="INFO",
            status="PASS",
            message=f"Pay period '{f_period.normalized_value}' is present.",
            field_name="pay_period",
            evidence=f_period.evidence
        ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="pay_period_valid",
            severity="WARNING",
            status="WARNING",
            message="Optional field 'pay_period' is missing.",
            field_name="pay_period"
        ))

    # 4. Gross Salary
    f_gross = fields.get("monthly_gross_salary") or fields.get("gross_salary")
    gross_val = safe_float(f_gross.normalized_value) if f_gross else None
    if f_gross and gross_val is not None:
        if gross_val > 0:
            checks.append(ValidationCheckSchema(
                check_name="gross_salary_valid",
                severity="INFO",
                status="PASS",
                message=f"Gross salary is valid positive amount ({gross_val}).",
                field_name=f_gross.field_name,
                evidence=f_gross.evidence
            ))
        else:
            checks.append(ValidationCheckSchema(
                check_name="gross_salary_valid",
                severity="ERROR",
                status="FAIL",
                message=f"Gross salary must be a positive numeric value (got {gross_val}).",
                field_name=f_gross.field_name,
                evidence=f_gross.evidence
            ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="gross_salary_valid",
            severity="ERROR",
            status="FAIL",
            message="Missing required numeric field 'monthly_gross_salary'.",
            field_name="monthly_gross_salary"
        ))

    # 5. Net Salary
    f_net = fields.get("monthly_net_salary") or fields.get("net_salary")
    net_val = safe_float(f_net.normalized_value) if f_net else None
    if f_net and net_val is not None:
        if net_val > 0:
            checks.append(ValidationCheckSchema(
                check_name="net_salary_valid",
                severity="INFO",
                status="PASS",
                message=f"Net salary is valid positive amount ({net_val}).",
                field_name=f_net.field_name,
                evidence=f_net.evidence
            ))
        else:
            checks.append(ValidationCheckSchema(
                check_name="net_salary_valid",
                severity="ERROR",
                status="FAIL",
                message=f"Net salary must be a positive numeric value (got {net_val}).",
                field_name=f_net.field_name,
                evidence=f_net.evidence
            ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="net_salary_valid",
            severity="ERROR",
            status="FAIL",
            message="Missing required numeric field 'monthly_net_salary'.",
            field_name="monthly_net_salary"
        ))

    # 6. Internal Boundary Check: net_salary <= gross_salary
    if gross_val is not None and net_val is not None and gross_val > 0 and net_val > 0:
        if net_val <= gross_val:
            checks.append(ValidationCheckSchema(
                check_name="net_salary_within_gross",
                severity="INFO",
                status="PASS",
                message=f"Net salary ({net_val}) is within gross salary ({gross_val}).",
                field_name="monthly_net_salary",
                evidence=f"Net: {net_val} <= Gross: {gross_val}"
            ))
        else:
            checks.append(ValidationCheckSchema(
                check_name="net_salary_within_gross",
                severity="ERROR",
                status="FAIL",
                message=f"Internal payslip error: Net salary ({net_val}) exceeds gross salary ({gross_val}).",
                field_name="monthly_net_salary",
                evidence=f"Net: {net_val} > Gross: {gross_val}"
            ))

    # 7. Currency
    f_curr = fields.get("currency")
    if f_curr and f_curr.normalized_value in ["INR", "USD", "EUR", "GBP", "₹", "RS"]:
        checks.append(ValidationCheckSchema(
            check_name="currency_valid",
            severity="INFO",
            status="PASS",
            message=f"Recognized currency '{f_curr.normalized_value}'.",
            field_name="currency",
            evidence=f_curr.evidence
        ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="currency_valid",
            severity="WARNING",
            status="WARNING",
            message="Currency symbol is missing or unrecognized.",
            field_name="currency"
        ))

    return checks


def validate_bank_statement_fields(fields: Dict[str, ExtractedFieldModel]) -> List[ValidationCheckSchema]:
    checks = []

    # 1. Account Holder Name
    f_holder = fields.get("account_holder_name")
    if f_holder and f_holder.normalized_value:
        checks.append(ValidationCheckSchema(
            check_name="account_holder_present",
            severity="INFO",
            status="PASS",
            message="Account holder name is present.",
            field_name="account_holder_name",
            evidence=f_holder.evidence
        ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="account_holder_present",
            severity="ERROR",
            status="FAIL",
            message="Missing required field 'account_holder_name'.",
            field_name="account_holder_name"
        ))

    # 2. Account Number
    f_acc = fields.get("account_number")
    if f_acc and f_acc.normalized_value:
        checks.append(ValidationCheckSchema(
            check_name="account_number_present",
            severity="INFO",
            status="PASS",
            message="Account number is present.",
            field_name="account_number",
            evidence=f_acc.evidence
        ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="account_number_present",
            severity="WARNING",
            status="WARNING",
            message="Optional field 'account_number' is missing.",
            field_name="account_number"
        ))

    # 3. Statement Period
    f_period = fields.get("statement_period")
    if f_period and f_period.normalized_value:
        checks.append(ValidationCheckSchema(
            check_name="statement_period_valid",
            severity="INFO",
            status="PASS",
            message="Statement period is valid.",
            field_name="statement_period",
            evidence=f_period.evidence
        ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="statement_period_valid",
            severity="WARNING",
            status="WARNING",
            message="Optional field 'statement_period' is missing.",
            field_name="statement_period"
        ))

    # 4. Opening Balance
    f_open = fields.get("opening_balance")
    open_val = safe_float(f_open.normalized_value) if f_open else None
    if f_open and open_val is not None:
        checks.append(ValidationCheckSchema(
            check_name="opening_balance_valid",
            severity="INFO",
            status="PASS",
            message=f"Opening balance is a valid numeric value ({open_val}).",
            field_name="opening_balance",
            evidence=f_open.evidence
        ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="opening_balance_valid",
            severity="ERROR",
            status="FAIL",
            message="Missing or invalid required numeric field 'opening_balance'.",
            field_name="opening_balance"
        ))

    # 5. Closing Balance
    f_close = fields.get("closing_balance")
    close_val = safe_float(f_close.normalized_value) if f_close else None
    if f_close and close_val is not None:
        checks.append(ValidationCheckSchema(
            check_name="closing_balance_valid",
            severity="INFO",
            status="PASS",
            message=f"Closing balance is a valid numeric value ({close_val}).",
            field_name="closing_balance",
            evidence=f_close.evidence
        ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="closing_balance_valid",
            severity="ERROR",
            status="FAIL",
            message="Missing or invalid required numeric field 'closing_balance'.",
            field_name="closing_balance"
        ))

    # 6. Average Balance
    f_avg = fields.get("average_balance")
    avg_val = safe_float(f_avg.normalized_value) if f_avg else None
    if f_avg and avg_val is not None:
        checks.append(ValidationCheckSchema(
            check_name="average_balance_valid",
            severity="INFO",
            status="PASS",
            message=f"Average balance is valid ({avg_val}).",
            field_name="average_balance",
            evidence=f_avg.evidence
        ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="average_balance_valid",
            severity="WARNING",
            status="WARNING",
            message="Optional field 'average_balance' is missing.",
            field_name="average_balance"
        ))

    # 7. Currency
    f_curr = fields.get("currency")
    if f_curr and f_curr.normalized_value in ["INR", "USD", "EUR", "GBP", "₹", "RS"]:
        checks.append(ValidationCheckSchema(
            check_name="currency_valid",
            severity="INFO",
            status="PASS",
            message=f"Recognized currency '{f_curr.normalized_value}'.",
            field_name="currency",
            evidence=f_curr.evidence
        ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="currency_valid",
            severity="WARNING",
            status="WARNING",
            message="Currency symbol is missing or unrecognized.",
            field_name="currency"
        ))

    # 8. Transactions Structural Validation
    f_tx = fields.get("transactions")
    if f_tx and f_tx.normalized_value:
        try:
            tx_list = json.loads(f_tx.normalized_value)
            if isinstance(tx_list, list) and len(tx_list) > 0:
                checks.append(ValidationCheckSchema(
                    check_name="transactions_valid",
                    severity="INFO",
                    status="PASS",
                    message=f"Statement contains {len(tx_list)} structurally valid transaction records.",
                    field_name="transactions",
                    evidence=f_tx.evidence
                ))
            else:
                checks.append(ValidationCheckSchema(
                    check_name="transactions_valid",
                    severity="WARNING",
                    status="WARNING",
                    message="Transaction list is empty.",
                    field_name="transactions"
                ))
        except Exception:
            checks.append(ValidationCheckSchema(
                check_name="transactions_valid",
                severity="WARNING",
                status="WARNING",
                message="Transaction data structure is malformed.",
                field_name="transactions"
            ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="transactions_valid",
            severity="WARNING",
            status="WARNING",
            message="Optional field 'transactions' is missing.",
            field_name="transactions"
        ))

    return checks


def validate_tax_return_fields(fields: Dict[str, ExtractedFieldModel]) -> List[ValidationCheckSchema]:
    checks = []

    # 1. Taxpayer Name
    f_name = fields.get("taxpayer_name")
    if f_name and f_name.normalized_value:
        checks.append(ValidationCheckSchema(
            check_name="taxpayer_name_present",
            severity="INFO",
            status="PASS",
            message="Taxpayer name is present.",
            field_name="taxpayer_name",
            evidence=f_name.evidence
        ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="taxpayer_name_present",
            severity="ERROR",
            status="FAIL",
            message="Missing required field 'taxpayer_name'.",
            field_name="taxpayer_name"
        ))

    # 2. Tax Year
    f_year = fields.get("tax_year")
    if f_year and f_year.normalized_value:
        checks.append(ValidationCheckSchema(
            check_name="tax_year_valid",
            severity="INFO",
            status="PASS",
            message=f"Tax year '{f_year.normalized_value}' is present.",
            field_name="tax_year",
            evidence=f_year.evidence
        ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="tax_year_valid",
            severity="ERROR",
            status="FAIL",
            message="Missing required field 'tax_year'.",
            field_name="tax_year"
        ))

    # 3. Declared Annual Income
    f_dec = fields.get("declared_annual_income")
    dec_val = safe_float(f_dec.normalized_value) if f_dec else None
    if f_dec and dec_val is not None:
        if dec_val >= 0:
            checks.append(ValidationCheckSchema(
                check_name="declared_income_valid",
                severity="INFO",
                status="PASS",
                message=f"Declared annual income is non-negative ({dec_val}).",
                field_name="declared_annual_income",
                evidence=f_dec.evidence
            ))
        else:
            checks.append(ValidationCheckSchema(
                check_name="declared_income_valid",
                severity="ERROR",
                status="FAIL",
                message=f"Declared annual income cannot be negative ({dec_val}).",
                field_name="declared_annual_income",
                evidence=f_dec.evidence
            ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="declared_income_valid",
            severity="ERROR",
            status="FAIL",
            message="Missing required numeric field 'declared_annual_income'.",
            field_name="declared_annual_income"
        ))

    # 4. Taxable Income
    f_taxable = fields.get("taxable_income")
    taxable_val = safe_float(f_taxable.normalized_value) if f_taxable else None
    if f_taxable and taxable_val is not None:
        if taxable_val >= 0:
            checks.append(ValidationCheckSchema(
                check_name="taxable_income_valid",
                severity="INFO",
                status="PASS",
                message=f"Taxable income is non-negative ({taxable_val}).",
                field_name="taxable_income",
                evidence=f_taxable.evidence
            ))
        else:
            checks.append(ValidationCheckSchema(
                check_name="taxable_income_valid",
                severity="ERROR",
                status="FAIL",
                message=f"Taxable income cannot be negative ({taxable_val}).",
                field_name="taxable_income",
                evidence=f_taxable.evidence
            ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="taxable_income_valid",
            severity="WARNING",
            status="WARNING",
            message="Optional field 'taxable_income' is missing.",
            field_name="taxable_income"
        ))

    # 5. Internal Boundary: taxable_income <= declared_annual_income
    if dec_val is not None and taxable_val is not None and dec_val >= 0 and taxable_val >= 0:
        if taxable_val <= dec_val:
            checks.append(ValidationCheckSchema(
                check_name="taxable_within_declared",
                severity="INFO",
                status="PASS",
                message=f"Taxable income ({taxable_val}) is within declared income ({dec_val}).",
                field_name="taxable_income",
                evidence=f"Taxable: {taxable_val} <= Declared: {dec_val}"
            ))
        else:
            checks.append(ValidationCheckSchema(
                check_name="taxable_within_declared",
                severity="ERROR",
                status="FAIL",
                message=f"Internal tax return error: Taxable income ({taxable_val}) exceeds declared annual income ({dec_val}).",
                field_name="taxable_income",
                evidence=f"Taxable: {taxable_val} > Declared: {dec_val}"
            ))

    # 6. Tax Paid
    f_tax = fields.get("tax_paid")
    tax_val = safe_float(f_tax.normalized_value) if f_tax else None
    if f_tax and tax_val is not None:
        if tax_val >= 0:
            checks.append(ValidationCheckSchema(
                check_name="tax_paid_valid",
                severity="INFO",
                status="PASS",
                message=f"Tax paid amount is valid ({tax_val}).",
                field_name="tax_paid",
                evidence=f_tax.evidence
            ))
        else:
            checks.append(ValidationCheckSchema(
                check_name="tax_paid_valid",
                severity="ERROR",
                status="FAIL",
                message=f"Tax paid cannot be negative ({tax_val}).",
                field_name="tax_paid",
                evidence=f_tax.evidence
            ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="tax_paid_valid",
            severity="WARNING",
            status="WARNING",
            message="Optional field 'tax_paid' is missing.",
            field_name="tax_paid"
        ))

    return checks


def validate_kyc_fields(fields: Dict[str, ExtractedFieldModel]) -> List[ValidationCheckSchema]:
    checks = []

    # 1. Full Name
    f_name = fields.get("full_name")
    if f_name and f_name.normalized_value:
        checks.append(ValidationCheckSchema(
            check_name="full_name_present",
            severity="INFO",
            status="PASS",
            message="Full name is present.",
            field_name="full_name",
            evidence=f_name.evidence
        ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="full_name_present",
            severity="ERROR",
            status="FAIL",
            message="Missing required field 'full_name'.",
            field_name="full_name"
        ))

    # 2. Date of Birth
    f_dob = fields.get("date_of_birth")
    dob_dt = safe_date(f_dob.normalized_value) if f_dob else None
    if f_dob and f_dob.normalized_value:
        if dob_dt and dob_dt <= datetime.utcnow():
            checks.append(ValidationCheckSchema(
                check_name="date_of_birth_valid",
                severity="INFO",
                status="PASS",
                message=f"Date of birth '{f_dob.normalized_value}' is a valid past date.",
                field_name="date_of_birth",
                evidence=f_dob.evidence
            ))
        elif dob_dt and dob_dt > datetime.utcnow():
            checks.append(ValidationCheckSchema(
                check_name="date_of_birth_valid",
                severity="ERROR",
                status="FAIL",
                message=f"Date of birth '{f_dob.normalized_value}' cannot be an impossible future date.",
                field_name="date_of_birth",
                evidence=f_dob.evidence
            ))
        else:
            checks.append(ValidationCheckSchema(
                check_name="date_of_birth_valid",
                severity="WARNING",
                status="WARNING",
                message=f"Date of birth value '{f_dob.normalized_value}' could not be parsed into standard date format.",
                field_name="date_of_birth",
                evidence=f_dob.evidence
            ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="date_of_birth_valid",
            severity="WARNING",
            status="WARNING",
            message="Optional field 'date_of_birth' is missing.",
            field_name="date_of_birth"
        ))

    # 3. Government ID Type
    f_type = fields.get("government_id_type")
    if f_type and f_type.normalized_value:
        checks.append(ValidationCheckSchema(
            check_name="government_id_type_present",
            severity="INFO",
            status="PASS",
            message=f"Government ID type '{f_type.normalized_value}' is present.",
            field_name="government_id_type",
            evidence=f_type.evidence
        ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="government_id_type_present",
            severity="WARNING",
            status="WARNING",
            message="Optional field 'government_id_type' is missing.",
            field_name="government_id_type"
        ))

    # 4. Government ID Number
    f_id = fields.get("government_id_number")
    if f_id and f_id.normalized_value:
        checks.append(ValidationCheckSchema(
            check_name="government_id_number_present",
            severity="INFO",
            status="PASS",
            message="Government ID number is present.",
            field_name="government_id_number",
            evidence=f_id.evidence
        ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="government_id_number_present",
            severity="ERROR",
            status="FAIL",
            message="Missing required field 'government_id_number'.",
            field_name="government_id_number"
        ))

    # 5. Address
    f_addr = fields.get("address")
    if f_addr and f_addr.normalized_value:
        checks.append(ValidationCheckSchema(
            check_name="address_present",
            severity="INFO",
            status="PASS",
            message="Address is present.",
            field_name="address",
            evidence=f_addr.evidence
        ))
    else:
        checks.append(ValidationCheckSchema(
            check_name="address_present",
            severity="WARNING",
            status="WARNING",
            message="Optional field 'address' is missing.",
            field_name="address"
        ))

    return checks


def validate_other_fields(fields: Dict[str, ExtractedFieldModel]) -> List[ValidationCheckSchema]:
    return [
        ValidationCheckSchema(
            check_name="document_type_supported",
            severity="INFO",
            status="NOT_CHECKED",
            message="Document-specific validation rules not supported for OTHER category.",
            field_name=None,
            evidence=None
        )
    ]


# --- SERVICE ENTRYPOINTS ---

def validate_and_save_document(db: Session, document_id: str) -> DocumentModel:
    """
    Validates a document independently using extracted fields and classified type,
    derives overall result, and saves DocumentValidationModel and ValidationCheckModel records.
    """
    doc = db.query(DocumentModel).filter(DocumentModel.document_id == document_id).first()
    if not doc or doc.processing_status == "DELETED":
        raise ValueError(f"Document '{document_id}' not found.")

    if doc.extraction_status != "COMPLETED":
        raise ValueError(f"Text for document '{document_id}' has not been extracted yet. Run /extract-text first.")

    if doc.classification_status != "COMPLETED" or not doc.classified_document_type:
        raise ValueError(f"Document '{document_id}' has not been classified yet. Run /classify first.")

    if doc.field_extraction_status != "COMPLETED":
        raise ValueError(f"Fields for document '{document_id}' have not been extracted yet. Run /extract-fields first.")

    # Idempotency check
    if doc.validation_status == "COMPLETED" and doc.validation_data:
        logger.info(f"Document '{document_id}' already validated. Returning cached validation.")
        return doc

    doc.validation_status = "VALIDATING"
    db.commit()

    # Load extracted fields into map
    field_models = db.query(ExtractedFieldModel).filter(ExtractedFieldModel.document_id == document_id).all()
    fields_map = {f.field_name: f for f in field_models}

    doc_type = doc.classified_document_type.upper()

    if doc_type == "PAYSLIP":
        checks = validate_payslip_fields(fields_map)
    elif doc_type == "BANK_STATEMENT":
        checks = validate_bank_statement_fields(fields_map)
    elif doc_type == "TAX_RETURN":
        checks = validate_tax_return_fields(fields_map)
    elif doc_type == "KYC":
        checks = validate_kyc_fields(fields_map)
    else:
        checks = validate_other_fields(fields_map)

    # Derive overall result
    failed_count = len([c for c in checks if c.status == "FAIL"])
    warning_count = len([c for c in checks if c.status == "WARNING"])
    passed_count = len([c for c in checks if c.status == "PASS"])

    if doc_type == "OTHER":
        overall = "UNSUPPORTED"
        summary = "Document validation not supported for category OTHER."
    elif failed_count > 0:
        overall = "FAIL"
        summary = f"Document validation failed with {failed_count} error(s) and {warning_count} warning(s)."
    elif warning_count > 0:
        overall = "PASS_WITH_WARNINGS"
        summary = f"Document validation passed with {warning_count} warning(s)."
    else:
        overall = "PASS"
        summary = f"All {passed_count} document validation checks passed successfully."

    # Clear prior validation records if reprocessing
    db.query(DocumentValidationModel).filter(DocumentValidationModel.document_id == document_id).delete()

    val_record = DocumentValidationModel(
        document_id=document_id,
        status="COMPLETED",
        overall_result=overall,
        summary=summary,
        validation_error=None,
        validated_at=datetime.utcnow()
    )
    db.add(val_record)
    db.flush()

    for item in checks:
        check_model = ValidationCheckModel(
            validation_id=val_record.id,
            check_name=item.check_name,
            severity=item.severity,
            status=item.status,
            message=item.message,
            field_name=item.field_name,
            evidence=item.evidence
        )
        db.add(check_model)

    doc.validation_status = "COMPLETED"
    doc.validation_overall_result = overall
    doc.validation_error = None
    doc.validated_at = datetime.utcnow()

    db.commit()
    db.refresh(doc)
    return doc


def get_validation_payload(db: Session, document_id: str) -> Dict[str, Any]:
    """Retrieves document validation response payload for API response."""
    doc = db.query(DocumentModel).filter(DocumentModel.document_id == document_id).first()
    if not doc or doc.processing_status == "DELETED":
        raise ValueError(f"Document '{document_id}' not found.")

    val_record = db.query(DocumentValidationModel).filter(DocumentValidationModel.document_id == document_id).first()
    if not val_record:
        return {
            "document_id": doc.document_id,
            "classified_document_type": doc.classified_document_type or "OTHER",
            "status": doc.validation_status,
            "overall_result": doc.validation_overall_result or "UNSUPPORTED",
            "summary": "Validation not performed.",
            "total_checks": 0,
            "passed_checks": 0,
            "warning_checks": 0,
            "failed_checks": 0,
            "checks": [],
            "error": doc.validation_error,
            "validated_at": doc.validated_at
        }

    checks_models = db.query(ValidationCheckModel).filter(ValidationCheckModel.validation_id == val_record.id).all()
    checks_list = [ValidationCheckSchema.model_validate(c) for c in checks_models]

    failed_cnt = len([c for c in checks_list if c.status == "FAIL"])
    warning_cnt = len([c for c in checks_list if c.status == "WARNING"])
    passed_cnt = len([c for c in checks_list if c.status == "PASS"])

    return {
        "document_id": doc.document_id,
        "classified_document_type": doc.classified_document_type or "OTHER",
        "status": val_record.status,
        "overall_result": val_record.overall_result,
        "summary": val_record.summary,
        "total_checks": len(checks_list),
        "passed_checks": passed_cnt,
        "warning_checks": warning_cnt,
        "failed_checks": failed_cnt,
        "checks": checks_list,
        "error": val_record.validation_error,
        "validated_at": val_record.validated_at
    }
