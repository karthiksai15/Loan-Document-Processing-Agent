import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.document_validation_service import (
    validate_payslip_fields,
    validate_bank_statement_fields,
    validate_tax_return_fields,
    validate_kyc_fields,
    validate_other_fields
)
from app.db.models import ExtractedFieldModel

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_validation_app():
    """Ensure test applications exist prior to document validation tests."""
    payload = {
        "application_id": "VAL-TEST-APP",
        "applicant_name": "Rohan Kumar",
        "loan_amount": 4700000.0
    }
    client.post("/api/v1/applications", json=payload)


def test_validate_payslip_unit():
    # Valid payslip
    fields_valid = {
        "employee_name": ExtractedFieldModel(field_name="employee_name", raw_value="Rohan Kumar", normalized_value="Rohan Kumar", confidence=1.0, evidence="Employee Name: Rohan Kumar"),
        "employer_name": ExtractedFieldModel(field_name="employer_name", raw_value="Vertex Systems India", normalized_value="Vertex Systems India", confidence=1.0, evidence="Employer: Vertex Systems India"),
        "pay_period": ExtractedFieldModel(field_name="pay_period", raw_value="August 2026", normalized_value="August 2026", confidence=1.0, evidence="Pay Period: August 2026"),
        "monthly_gross_salary": ExtractedFieldModel(field_name="monthly_gross_salary", raw_value="INR 392,000", normalized_value="392000.0", confidence=1.0, evidence="Gross: INR 392,000"),
        "monthly_net_salary": ExtractedFieldModel(field_name="monthly_net_salary", raw_value="INR 350,000", normalized_value="350000.0", confidence=1.0, evidence="Net: INR 350,000"),
        "currency": ExtractedFieldModel(field_name="currency", raw_value="INR", normalized_value="INR", confidence=1.0, evidence="INR")
    }
    checks = validate_payslip_fields(fields_valid)
    statuses = [c.status for c in checks]
    assert "FAIL" not in statuses
    assert all(c.status == "PASS" for c in checks)

    # Invalid payslip (net salary > gross salary)
    fields_invalid = {
        "employee_name": ExtractedFieldModel(field_name="employee_name", raw_value="Rohan Kumar", normalized_value="Rohan Kumar", confidence=1.0),
        "employer_name": ExtractedFieldModel(field_name="employer_name", raw_value="Vertex Systems India", normalized_value="Vertex Systems India", confidence=1.0),
        "monthly_gross_salary": ExtractedFieldModel(field_name="monthly_gross_salary", raw_value="300000", normalized_value="300000.0", confidence=1.0),
        "monthly_net_salary": ExtractedFieldModel(field_name="monthly_net_salary", raw_value="350000", normalized_value="350000.0", confidence=1.0)
    }
    checks_inv = validate_payslip_fields(fields_invalid)
    failed_checks = [c for c in checks_inv if c.status == "FAIL"]
    assert len(failed_checks) > 0
    assert any(c.check_name == "net_salary_within_gross" for c in failed_checks)


def test_validate_bank_statement_unit():
    fields_valid = {
        "account_holder_name": ExtractedFieldModel(field_name="account_holder_name", raw_value="Rohan Kumar", normalized_value="Rohan Kumar", confidence=1.0),
        "opening_balance": ExtractedFieldModel(field_name="opening_balance", raw_value="50000", normalized_value="50000.0", confidence=1.0),
        "closing_balance": ExtractedFieldModel(field_name="closing_balance", raw_value="75000", normalized_value="75000.0", confidence=1.0)
    }
    checks = validate_bank_statement_fields(fields_valid)
    assert not any(c.status == "FAIL" for c in checks)

    # Missing account holder name -> FAIL
    fields_missing = {
        "opening_balance": ExtractedFieldModel(field_name="opening_balance", raw_value="50000", normalized_value="50000.0", confidence=1.0),
        "closing_balance": ExtractedFieldModel(field_name="closing_balance", raw_value="75000", normalized_value="75000.0", confidence=1.0)
    }
    checks_missing = validate_bank_statement_fields(fields_missing)
    assert any(c.check_name == "account_holder_present" and c.status == "FAIL" for c in checks_missing)


def test_validate_tax_return_unit():
    fields_valid = {
        "taxpayer_name": ExtractedFieldModel(field_name="taxpayer_name", raw_value="Rohan Kumar", normalized_value="Rohan Kumar", confidence=1.0),
        "tax_year": ExtractedFieldModel(field_name="tax_year", raw_value="2025-26", normalized_value="2025-26", confidence=1.0),
        "declared_annual_income": ExtractedFieldModel(field_name="declared_annual_income", raw_value="4700000", normalized_value="4700000.0", confidence=1.0),
        "taxable_income": ExtractedFieldModel(field_name="taxable_income", raw_value="4230000", normalized_value="4230000.0", confidence=1.0),
        "tax_paid": ExtractedFieldModel(field_name="tax_paid", raw_value="470000", normalized_value="470000.0", confidence=1.0)
    }
    checks = validate_tax_return_fields(fields_valid)
    assert not any(c.status == "FAIL" for c in checks)

    # Taxable income > declared income -> FAIL
    fields_invalid = {
        "taxpayer_name": ExtractedFieldModel(field_name="taxpayer_name", raw_value="Rohan Kumar", normalized_value="Rohan Kumar", confidence=1.0),
        "tax_year": ExtractedFieldModel(field_name="tax_year", raw_value="2025-26", normalized_value="2025-26", confidence=1.0),
        "declared_annual_income": ExtractedFieldModel(field_name="declared_annual_income", raw_value="4000000", normalized_value="4000000.0", confidence=1.0),
        "taxable_income": ExtractedFieldModel(field_name="taxable_income", raw_value="4500000", normalized_value="4500000.0", confidence=1.0)
    }
    checks_inv = validate_tax_return_fields(fields_invalid)
    assert any(c.check_name == "taxable_within_declared" and c.status == "FAIL" for c in checks_inv)


def test_validate_kyc_unit():
    fields_valid = {
        "full_name": ExtractedFieldModel(field_name="full_name", raw_value="Rohan Kumar", normalized_value="Rohan Kumar", confidence=1.0),
        "date_of_birth": ExtractedFieldModel(field_name="date_of_birth", raw_value="1987-03-12", normalized_value="1987-03-12", confidence=1.0),
        "government_id_number": ExtractedFieldModel(field_name="government_id_number", raw_value="DEMO-KYC-123", normalized_value="DEMO-KYC-123", confidence=1.0)
    }
    checks = validate_kyc_fields(fields_valid)
    assert not any(c.status == "FAIL" for c in checks)

    # Future date of birth -> FAIL
    fields_future = {
        "full_name": ExtractedFieldModel(field_name="full_name", raw_value="Rohan Kumar", normalized_value="Rohan Kumar", confidence=1.0),
        "date_of_birth": ExtractedFieldModel(field_name="date_of_birth", raw_value="2099-01-01", normalized_value="2099-01-01", confidence=1.0),
        "government_id_number": ExtractedFieldModel(field_name="government_id_number", raw_value="DEMO-KYC-123", normalized_value="DEMO-KYC-123", confidence=1.0)
    }
    checks_fut = validate_kyc_fields(fields_future)
    assert any(c.check_name == "date_of_birth_valid" and c.status == "FAIL" for c in checks_fut)


def test_validate_other_unit():
    checks = validate_other_fields({})
    assert len(checks) == 1
    assert checks[0].status == "NOT_CHECKED"


def test_validation_guards_and_404():
    # 404 for non-existent document
    res_404 = client.post("/api/v1/documents/non-existent-doc-id/validate")
    assert res_404.status_code == 404

    # 400 for unextracted document
    content = b"SYNTHETIC LOAN DOCUMENT\nPAYSLIP\nEmployee Name: Rohan Kumar\nEmployer: Vertex Systems India\nMonthly Gross Salary: INR 392,000\nMonthly Net Salary: INR 350,000"
    files = {"file": ("payslip_guard.txt", content, "text/plain")}
    upload_res = client.post("/api/v1/applications/VAL-TEST-APP/documents", files=files, data={"document_type": "PAYSLIP"})
    doc_id = upload_res.json()["document_id"]

    val_res_unextracted = client.post(f"/api/v1/documents/{doc_id}/validate")
    assert val_res_unextracted.status_code == 400
    assert "not been extracted yet" in val_res_unextracted.json()["detail"].lower()

    # Extract text but don't classify
    client.post(f"/api/v1/documents/{doc_id}/extract-text")
    val_res_unclassified = client.post(f"/api/v1/documents/{doc_id}/validate")
    assert val_res_unclassified.status_code == 400
    assert "not been classified yet" in val_res_unclassified.json()["detail"].lower()

    # Classify but don't extract fields
    client.post(f"/api/v1/documents/{doc_id}/classify")
    val_res_unfields = client.post(f"/api/v1/documents/{doc_id}/validate")
    assert val_res_unfields.status_code == 400
    assert "fields for document" in val_res_unfields.json()["detail"].lower()


def test_full_validation_pipeline_and_idempotency():
    content = (
        b"SYNTHETIC LOAN DOCUMENT\n"
        b"PAYSLIP\n"
        b"Employee Name: Rohan Kumar\n"
        b"Employer: Vertex Systems India\n"
        b"Pay Period: August 2026\n"
        b"Monthly Gross Salary: INR 392,000\n"
        b"Monthly Net Salary: INR 350,000\n"
        b"Currency: INR"
    )
    files = {"file": ("payslip_full.txt", content, "text/plain")}
    upload_res = client.post("/api/v1/applications/VAL-TEST-APP/documents", files=files, data={"document_type": "PAYSLIP"})
    doc_id = upload_res.json()["document_id"]

    # 1. Extract text
    client.post(f"/api/v1/documents/{doc_id}/extract-text")

    # 2. Classify
    client.post(f"/api/v1/documents/{doc_id}/classify")

    # 3. Extract fields
    client.post(f"/api/v1/documents/{doc_id}/extract-fields")

    # 4. Validate document
    val_res = client.post(f"/api/v1/documents/{doc_id}/validate")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["status"] == "COMPLETED"
    assert val_data["overall_result"] in ["PASS", "PASS_WITH_WARNINGS"]
    assert val_data["total_checks"] > 0
    assert len(val_data["checks"]) > 0

    # 5. Idempotency test (call validate again)
    val_res_repeat = client.post(f"/api/v1/documents/{doc_id}/validate")
    assert val_res_repeat.status_code == 200
    assert val_res_repeat.json()["status"] == "COMPLETED"

    # 6. GET /validation
    get_res = client.get(f"/api/v1/documents/{doc_id}/validation")
    assert get_res.status_code == 200
    assert get_res.json()["document_id"] == doc_id
    assert get_res.json()["overall_result"] == val_data["overall_result"]


def test_synthetic_documents_validation_across_all_applicants():
    """Verify document-level validation against synthetic documents for applicants A001..A010."""
    from app.services.text_extraction_service import extract_text_from_file
    from app.services.document_classification_service import classify_text
    from app.services.field_extraction_service import (
        extract_payslip_fields,
        extract_bank_statement_fields,
        extract_tax_return_fields,
        extract_kyc_fields,
        extract_other_fields
    )

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    for app_id in ["A001", "A002", "A003", "A004", "A005", "A006", "A007", "A008", "A009", "A010"]:
        app_dir = os.path.join(project_root, "data", "applicants", app_id)
        if not os.path.exists(app_dir):
            continue

        for fname in sorted(os.listdir(app_dir)):
            if not fname.endswith(".txt"):
                continue

            fpath = os.path.join(app_dir, fname)
            ex_res = extract_text_from_file(fpath, fname)
            cls_res = classify_text(ex_res.text)

            fields = []
            if cls_res.document_type == "PAYSLIP":
                fields = extract_payslip_fields(ex_res.text)
                fields_map = {f.field_name: f for f in fields}
                checks = validate_payslip_fields(fields_map)
            elif cls_res.document_type == "BANK_STATEMENT":
                fields = extract_bank_statement_fields(ex_res.text)
                fields_map = {f.field_name: f for f in fields}
                checks = validate_bank_statement_fields(fields_map)
            elif cls_res.document_type == "TAX_RETURN":
                fields = extract_tax_return_fields(ex_res.text)
                fields_map = {f.field_name: f for f in fields}
                checks = validate_tax_return_fields(fields_map)
            elif cls_res.document_type == "KYC":
                fields = extract_kyc_fields(ex_res.text)
                fields_map = {f.field_name: f for f in fields}
                checks = validate_kyc_fields(fields_map)
            else:
                checks = validate_other_fields({})

            assert len(checks) > 0
            assert all(hasattr(c, "status") and hasattr(c, "check_name") for c in checks)

