import os
import re
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.db.models import DocumentModel, ExtractedFieldModel
from app.schemas.extracted_field import ExtractedFieldSchema

# --- NORMALIZATION UTILITIES ---

def normalize_number(raw_val: str) -> Optional[float]:
    """Extract numeric value from string (e.g. 'INR 1,600,000' -> 1600000.0)."""
    if not raw_val:
        return None
    # Remove currency codes/symbols and spaces, keep digits and dots
    clean = re.sub(r'[^\d.]', '', raw_val.replace(',', ''))
    if not clean:
        return None
    try:
        return float(clean)
    except ValueError:
        return None

def parse_currency(raw_val: str) -> Tuple[str, Optional[float]]:
    """Parse currency code and normalized numeric value."""
    if not raw_val:
        return ("INR", None)
    
    currency_code = "INR"
    if "$" in raw_val or "USD" in raw_val:
        currency_code = "USD"
    elif "€" in raw_val or "EUR" in raw_val:
        currency_code = "EUR"
    elif "£" in raw_val or "GBP" in raw_val:
        currency_code = "GBP"
        
    num_val = normalize_number(raw_val)
    return (currency_code, num_val)

def normalize_date(raw_val: str) -> Optional[str]:
    """Standardize date strings to YYYY-MM-DD format if possible."""
    if not raw_val:
        return None
    raw_str = raw_val.strip()
    
    # ISO format YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}$', raw_str):
        return raw_str
        
    # Standard DD-Mon-YYYY e.g. 01-Aug-2026
    m1 = re.match(r'^(\d{1,2})[\/\-\s]([A-Za-z]{3,9})[\/\-\s](\d{4})$', raw_str)
    if m1:
        day, month_str, year = m1.groups()
        try:
            dt = datetime.strptime(f"{day}-{month_str[:3].title()}-{year}", "%d-%b-%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
            
    return raw_str

def mask_sensitive_data(field_name: str, value: str) -> str:
    """Mask sensitive IDs or account numbers for logging."""
    if not value:
        return ""
    if "id" in field_name.lower() or "account" in field_name.lower() or "number" in field_name.lower():
        if len(value) > 6:
            return value[:3] + "****" + value[-3:]
        return "****"
    return value

# --- CATEGORY FIELD EXTRACTORS ---

def extract_payslip_fields(text: str) -> List[ExtractedFieldSchema]:
    fields = []
    lines = text.split("\n")
    
    currency_code = "INR"
    
    for line in lines:
        line_str = line.strip()
        if not line_str or ":" not in line_str:
            continue
            
        parts = line_str.split(":", 1)
        label = parts[0].strip().lower()
        val = parts[1].strip()
        
        if "employee name" in label:
            fields.append(ExtractedFieldSchema(
                field_name="employee_name",
                raw_value=val,
                normalized_value=val,
                field_type="string",
                confidence=0.98,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif label == "employer":
            fields.append(ExtractedFieldSchema(
                field_name="employer_name",
                raw_value=val,
                normalized_value=val,
                field_type="string",
                confidence=0.98,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif "employee id" in label:
            fields.append(ExtractedFieldSchema(
                field_name="employee_id",
                raw_value=val,
                normalized_value=val,
                field_type="string",
                confidence=0.95,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif "pay period" in label:
            fields.append(ExtractedFieldSchema(
                field_name="pay_period",
                raw_value=val,
                normalized_value=val,
                field_type="string",
                confidence=0.95,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif "employment status" in label:
            fields.append(ExtractedFieldSchema(
                field_name="employment_status",
                raw_value=val,
                normalized_value=val,
                field_type="string",
                confidence=0.95,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif "monthly gross salary" in label:
            curr, num = parse_currency(val)
            currency_code = curr
            norm_str = str(num) if num is not None else None
            fields.append(ExtractedFieldSchema(
                field_name="monthly_gross_salary",
                raw_value=val,
                normalized_value=norm_str,
                field_type="currency",
                confidence=0.98,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
            # Also populate alias gross_salary
            fields.append(ExtractedFieldSchema(
                field_name="gross_salary",
                raw_value=val,
                normalized_value=norm_str,
                field_type="currency",
                confidence=0.98,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif "monthly net salary" in label:
            curr, num = parse_currency(val)
            norm_str = str(num) if num is not None else None
            fields.append(ExtractedFieldSchema(
                field_name="monthly_net_salary",
                raw_value=val,
                normalized_value=norm_str,
                field_type="currency",
                confidence=0.98,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
            # Also populate alias net_salary
            fields.append(ExtractedFieldSchema(
                field_name="net_salary",
                raw_value=val,
                normalized_value=norm_str,
                field_type="currency",
                confidence=0.98,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif "annual declared income" in label:
            curr, num = parse_currency(val)
            norm_str = str(num) if num is not None else None
            fields.append(ExtractedFieldSchema(
                field_name="annual_declared_income",
                raw_value=val,
                normalized_value=norm_str,
                field_type="currency",
                confidence=0.95,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))

    fields.append(ExtractedFieldSchema(
        field_name="currency",
        raw_value=currency_code,
        normalized_value=currency_code,
        field_type="string",
        confidence=0.99,
        extraction_method="LABEL_PATTERN",
        evidence="Extracted currency context"
    ))
    return fields


def extract_bank_statement_fields(text: str) -> List[ExtractedFieldSchema]:
    fields = []
    lines = text.split("\n")
    transactions = []
    salary_credit_val = None
    salary_credit_line = None
    currency_code = "INR"

    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue

        # Transaction row parser: e.g. "05-Aug-2026 | SALARY CREDIT | INR 82,000"
        if "|" in line_str:
            parts = [p.strip() for p in line_str.split("|")]
            if len(parts) >= 3:
                tx_date = normalize_date(parts[0])
                tx_desc = parts[1]
                curr, tx_amt = parse_currency(parts[2])
                is_salary = "salary" in tx_desc.lower()
                
                tx_type = "CREDIT" if "credit" in tx_desc.lower() or "deposit" in tx_desc.lower() else "DEBIT"
                if is_salary:
                    salary_credit_val = parts[2]
                    salary_credit_line = line_str

                transactions.append({
                    "date": tx_date,
                    "description": tx_desc,
                    "amount": tx_amt,
                    "transaction_type": tx_type,
                    "is_salary_credit": is_salary,
                    "raw": line_str
                })
            continue

        if ":" not in line_str:
            continue

        parts = line_str.split(":", 1)
        label = parts[0].strip().lower()
        val = parts[1].strip()

        if "account holder" in label:
            fields.append(ExtractedFieldSchema(
                field_name="account_holder_name",
                raw_value=val,
                normalized_value=val,
                field_type="string",
                confidence=0.98,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif "account number" in label:
            fields.append(ExtractedFieldSchema(
                field_name="account_number",
                raw_value=val,
                normalized_value=val,
                field_type="string",
                confidence=0.98,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif "statement period" in label:
            fields.append(ExtractedFieldSchema(
                field_name="statement_period",
                raw_value=val,
                normalized_value=val,
                field_type="string",
                confidence=0.95,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif "opening balance" in label:
            curr, num = parse_currency(val)
            currency_code = curr
            fields.append(ExtractedFieldSchema(
                field_name="opening_balance",
                raw_value=val,
                normalized_value=str(num) if num is not None else None,
                field_type="currency",
                confidence=0.95,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif "average balance" in label:
            curr, num = parse_currency(val)
            fields.append(ExtractedFieldSchema(
                field_name="average_balance",
                raw_value=val,
                normalized_value=str(num) if num is not None else None,
                field_type="currency",
                confidence=0.95,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif "closing balance" in label:
            curr, num = parse_currency(val)
            fields.append(ExtractedFieldSchema(
                field_name="closing_balance",
                raw_value=val,
                normalized_value=str(num) if num is not None else None,
                field_type="currency",
                confidence=0.98,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))

    # Add Salary Credit Field if identified
    if salary_credit_val:
        _, sal_num = parse_currency(salary_credit_val)
        fields.append(ExtractedFieldSchema(
            field_name="salary_credit_amount",
            raw_value=salary_credit_val,
            normalized_value=str(sal_num) if sal_num is not None else None,
            field_type="currency",
            confidence=0.95,
            extraction_method="REGEX_RULE",
            evidence=salary_credit_line
        ))

    # Add Transactions list schema
    if transactions:
        fields.append(ExtractedFieldSchema(
            field_name="transactions",
            raw_value=json.dumps(transactions),
            normalized_value=json.dumps(transactions),
            field_type="list",
            confidence=0.95,
            extraction_method="REGEX_RULE",
            evidence=f"Parsed {len(transactions)} transaction records."
        ))

    fields.append(ExtractedFieldSchema(
        field_name="currency",
        raw_value=currency_code,
        normalized_value=currency_code,
        field_type="string",
        confidence=0.99,
        extraction_method="LABEL_PATTERN",
        evidence="Extracted currency context"
    ))
    return fields


def extract_tax_return_fields(text: str) -> List[ExtractedFieldSchema]:
    fields = []
    lines = text.split("\n")
    currency_code = "INR"

    for line in lines:
        line_str = line.strip()
        if not line_str or ":" not in line_str:
            continue

        parts = line_str.split(":", 1)
        label = parts[0].strip().lower()
        val = parts[1].strip()

        if "taxpayer name" in label:
            fields.append(ExtractedFieldSchema(
                field_name="taxpayer_name",
                raw_value=val,
                normalized_value=val,
                field_type="string",
                confidence=0.98,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif "tax year" in label:
            fields.append(ExtractedFieldSchema(
                field_name="tax_year",
                raw_value=val,
                normalized_value=val,
                field_type="string",
                confidence=0.95,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif "declared annual income" in label:
            curr, num = parse_currency(val)
            currency_code = curr
            norm_str = str(num) if num is not None else None
            fields.append(ExtractedFieldSchema(
                field_name="declared_annual_income",
                raw_value=val,
                normalized_value=norm_str,
                field_type="currency",
                confidence=0.98,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif "taxable income" in label:
            curr, num = parse_currency(val)
            norm_str = str(num) if num is not None else None
            fields.append(ExtractedFieldSchema(
                field_name="taxable_income",
                raw_value=val,
                normalized_value=norm_str,
                field_type="currency",
                confidence=0.95,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif "tax paid" in label:
            curr, num = parse_currency(val)
            norm_str = str(num) if num is not None else None
            fields.append(ExtractedFieldSchema(
                field_name="tax_paid",
                raw_value=val,
                normalized_value=norm_str,
                field_type="currency",
                confidence=0.95,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))

    fields.append(ExtractedFieldSchema(
        field_name="currency",
        raw_value=currency_code,
        normalized_value=currency_code,
        field_type="string",
        confidence=0.99,
        extraction_method="LABEL_PATTERN",
        evidence="Extracted currency context"
    ))
    return fields


def extract_kyc_fields(text: str) -> List[ExtractedFieldSchema]:
    fields = []
    lines = text.split("\n")

    for line in lines:
        line_str = line.strip()
        if not line_str or ":" not in line_str:
            continue

        parts = line_str.split(":", 1)
        label = parts[0].strip().lower()
        val = parts[1].strip()

        if "full name" in label or "name" in label:
            fields.append(ExtractedFieldSchema(
                field_name="full_name",
                raw_value=val,
                normalized_value=val,
                field_type="string",
                confidence=0.98,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif "date of birth" in label or "dob" in label:
            norm_d = normalize_date(val)
            fields.append(ExtractedFieldSchema(
                field_name="date_of_birth",
                raw_value=val,
                normalized_value=norm_d,
                field_type="date",
                confidence=0.95,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif "id number" in label or "synthetic id" in label or "kyc id" in label:
            fields.append(ExtractedFieldSchema(
                field_name="government_id_number",
                raw_value=val,
                normalized_value=val,
                field_type="string",
                confidence=0.98,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif "address" in label:
            fields.append(ExtractedFieldSchema(
                field_name="address",
                raw_value=val,
                normalized_value=val,
                field_type="string",
                confidence=0.95,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))
        elif "document type" in label:
            fields.append(ExtractedFieldSchema(
                field_name="government_id_type",
                raw_value=val,
                normalized_value=val,
                field_type="string",
                confidence=0.90,
                extraction_method="LABEL_PATTERN",
                evidence=line_str
            ))

    return fields


def extract_other_fields(text: str) -> List[ExtractedFieldSchema]:
    """Returns empty list for OTHER document category without fabricating fields."""
    return []


# --- MAIN SERVICE FUNCTIONS ---

def extract_and_save_fields(db: Session, document_id: str) -> DocumentModel:
    """
    Service function that retrieves extracted text and document classification,
    applies the category extraction schema, and persists ExtractedFieldModel records to DB.
    """
    doc = db.query(DocumentModel).filter(DocumentModel.document_id == document_id).first()
    if not doc or doc.processing_status == "DELETED":
        raise ValueError(f"Document '{document_id}' not found.")

    if doc.extraction_status != "COMPLETED" or (not doc.extracted_text_path and not doc.extracted_text):
        raise ValueError(f"Text for document '{document_id}' has not been extracted yet. Run /extract-text first.")

    if doc.classification_status != "COMPLETED" or not doc.classified_document_type:
        raise ValueError(f"Document '{document_id}' has not been classified yet. Run /classify first.")

    # Idempotent check
    if doc.field_extraction_status == "COMPLETED" and len(doc.extracted_fields_data) > 0:
        logger.info(f"Fields for document '{document_id}' already extracted. Returning cached result.")
        return doc

    doc.field_extraction_status = "EXTRACTING"
    db.commit()

    text_content = ""
    if doc.extracted_text:
        text_content = doc.extracted_text
    elif doc.extracted_text_path:
        project_root = os.path.dirname(settings.DATA_DIR)
        abs_text_path = os.path.join(project_root, doc.extracted_text_path)
        if os.path.exists(abs_text_path):
            with open(abs_text_path, "r", encoding="utf-8", errors="replace") as f:
                text_content = f.read()

    doc_type = doc.classified_document_type.upper()
    logger.info(f"Extracting structured fields for document '{document_id}' using schema '{doc_type}'.")

    if doc_type == "PAYSLIP":
        extracted_schemas = extract_payslip_fields(text_content)
    elif doc_type == "BANK_STATEMENT":
        extracted_schemas = extract_bank_statement_fields(text_content)
    elif doc_type == "TAX_RETURN":
        extracted_schemas = extract_tax_return_fields(text_content)
    elif doc_type == "KYC":
        extracted_schemas = extract_kyc_fields(text_content)
    else:
        extracted_schemas = extract_other_fields(text_content)

    # Delete previous field records for this document to ensure clean idempotent overwrite
    db.query(ExtractedFieldModel).filter(ExtractedFieldModel.document_id == document_id).delete()

    for item in extracted_schemas:
        field_model = ExtractedFieldModel(
            document_id=document_id,
            field_name=item.field_name,
            raw_value=item.raw_value,
            normalized_value=item.normalized_value,
            field_type=item.field_type,
            confidence=item.confidence,
            extraction_method=item.extraction_method,
            evidence=item.evidence
        )
        db.add(field_model)

    doc.field_extraction_status = "COMPLETED"
    doc.field_extraction_error = None
    doc.fields_extracted_at = datetime.utcnow()

    db.commit()
    db.refresh(doc)
    return doc


def get_extracted_fields_payload(db: Session, document_id: str) -> Dict[str, Any]:
    """Retrieves extracted fields payload for API response."""
    doc = db.query(DocumentModel).filter(DocumentModel.document_id == document_id).first()
    if not doc or doc.processing_status == "DELETED":
        raise ValueError(f"Document '{document_id}' not found.")

    field_models = db.query(ExtractedFieldModel).filter(ExtractedFieldModel.document_id == document_id).all()
    fields_list = [ExtractedFieldSchema.model_validate(f) for f in field_models]

    return {
        "document_id": doc.document_id,
        "classified_document_type": doc.classified_document_type or "OTHER",
        "status": doc.field_extraction_status,
        "fields_count": len(fields_list),
        "fields": fields_list,
        "error": doc.field_extraction_error,
        "extracted_at": doc.fields_extracted_at
    }
