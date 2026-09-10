import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.field_extraction_service import (
    extract_payslip_fields,
    extract_bank_statement_fields,
    extract_tax_return_fields,
    extract_kyc_fields,
    extract_other_fields,
    normalize_number,
    parse_currency,
    mask_sensitive_data
)
from app.services.text_extraction_service import extract_text_from_file
from app.services.document_classification_service import classify_text

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_field_extraction_app():
    """Ensure a test application exists prior to field extraction tests."""
    payload = {
        "application_id": "FIELD-TEST-APP",
        "applicant_name": "Rohan Kumar",
        "loan_amount": 4700000.0
    }
    client.post("/api/v1/applications", json=payload)

def test_currency_and_number_normalizers():
    assert normalize_number("INR 1,600,000") == 1600000.0
    assert normalize_number("4700000") == 4700000.0
    assert normalize_number("₹ 25,000") == 25000.0
    
    curr, num = parse_currency("INR 392,000")
    assert curr == "INR"
    assert num == 392000.0
    
    masked = mask_sensitive_data("government_id_number", "DEMO-KYC-A003")
    assert "****" in masked

def test_extract_payslip_fields():
    text = "SYNTHETIC LOAN DOCUMENT\nPAYSLIP\nEmployee Name: Rohan Kumar\nEmployer: Vertex Systems India\nEmployee ID: DEMO-A003\nPay Period: August 2026\nMonthly Gross Salary: INR 392,000\nMonthly Net Salary: INR 350,000\nAnnual Declared Income: INR 4,700,000"
    fields = extract_payslip_fields(text)
    
    field_map = {f.field_name: f for f in fields}
    assert "employee_name" in field_map
    assert field_map["employee_name"].normalized_value == "Rohan Kumar"
    assert "monthly_gross_salary" in field_map
    assert field_map["monthly_gross_salary"].normalized_value == "392000.0"
    assert field_map["monthly_net_salary"].normalized_value == "350000.0"
    assert field_map["monthly_gross_salary"].evidence is not None

def test_extract_bank_statement_fields():
    text = "SYNTHETIC LOAN DOCUMENT\nBANK STATEMENT\nAccount Holder: Rohan Kumar\nAccount Number: XXXX-DEMO-A003\nStatement Period: 01-Aug-2026 to 31-Aug-2026\nOpening Balance: INR 50,000\n\n05-Aug-2026 | SALARY CREDIT | INR 392,000\n15-Aug-2026 | UTILITY PAYMENT | INR 8,500\n\nAverage Balance: INR 50,000\nClosing Balance: INR 75,000"
    fields = extract_bank_statement_fields(text)
    
    field_map = {f.field_name: f for f in fields}
    assert field_map["account_holder_name"].normalized_value == "Rohan Kumar"
    assert field_map["account_number"].normalized_value == "XXXX-DEMO-A003"
    assert field_map["closing_balance"].normalized_value == "75000.0"
    assert "salary_credit_amount" in field_map
    assert field_map["salary_credit_amount"].normalized_value == "392000.0"
    assert "transactions" in field_map

def test_extract_tax_return_fields():
    text = "SYNTHETIC LOAN DOCUMENT\nINCOME TAX RETURN\nTaxpayer Name: Rohan Kumar\nTax Year: FY 2025-26\nDeclared Annual Income: INR 4,700,000\nTaxable Income: INR 4,230,000\nTax Paid: INR 470,000"
    fields = extract_tax_return_fields(text)
    
    field_map = {f.field_name: f for f in fields}
    assert field_map["taxpayer_name"].normalized_value == "Rohan Kumar"
    assert field_map["declared_annual_income"].normalized_value == "4700000.0"
    assert field_map["taxable_income"].normalized_value == "4230000.0"
    assert field_map["tax_paid"].normalized_value == "470000.0"

def test_extract_kyc_fields():
    text = "SYNTHETIC LOAN DOCUMENT\nKYC / IDENTITY DOCUMENT\nFull Name: Rohan Kumar\nDate of Birth: 1987-03-12\nSynthetic ID Number: DEMO-KYC-A003\nAddress: 12, Demo Residency, Bengaluru"
    fields = extract_kyc_fields(text)
    
    field_map = {f.field_name: f for f in fields}
    assert field_map["full_name"].normalized_value == "Rohan Kumar"
    assert field_map["date_of_birth"].normalized_value == "1987-03-12"
    assert field_map["government_id_number"].normalized_value == "DEMO-KYC-A003"

def test_extract_other_fields():
    text = "Random unclassified text document."
    fields = extract_other_fields(text)
    assert fields == []

def test_field_extraction_fails_if_text_not_extracted():
    content = b"Unextracted content"
    files = {"file": ("unextracted.txt", content, "text/plain")}
    data = {"document_type": "PAYSLIP"}
    
    upload_res = client.post("/api/v1/applications/FIELD-TEST-APP/documents", files=files, data=data)
    doc_id = upload_res.json()["document_id"]
    
    res = client.post(f"/api/v1/documents/{doc_id}/extract-fields")
    assert res.status_code == 400
    assert "not been extracted yet" in res.json()["detail"].lower()

def test_field_extraction_fails_if_not_classified():
    content = b"Content extracted but unclassified"
    files = {"file": ("unclassified.txt", content, "text/plain")}
    data = {"document_type": "PAYSLIP"}
    
    upload_res = client.post("/api/v1/applications/FIELD-TEST-APP/documents", files=files, data=data)
    doc_id = upload_res.json()["document_id"]
    
    client.post(f"/api/v1/documents/{doc_id}/extract-text")
    
    res = client.post(f"/api/v1/documents/{doc_id}/extract-fields")
    assert res.status_code == 400
    assert "not been classified yet" in res.json()["detail"].lower()

def test_field_extraction_api_full_workflow():
    content = b"SYNTHETIC LOAN DOCUMENT\nPAYSLIP\nEmployee Name: Rohan Kumar\nEmployer: Vertex Systems India\nMonthly Gross Salary: INR 392,000\nMonthly Net Salary: INR 350,000"
    files = {"file": ("full_workflow_payslip.txt", content, "text/plain")}
    data = {"document_type": "PAYSLIP"}
    
    # 1. Upload
    upload_res = client.post("/api/v1/applications/FIELD-TEST-APP/documents", files=files, data=data)
    doc_id = upload_res.json()["document_id"]

    # 2. Extract Text
    client.post(f"/api/v1/documents/{doc_id}/extract-text")

    # 3. Classify
    client.post(f"/api/v1/documents/{doc_id}/classify")

    # 4. Extract Fields
    extract_res = client.post(f"/api/v1/documents/{doc_id}/extract-fields")
    assert extract_res.status_code == 200
    data_res = extract_res.json()
    assert data_res["document_id"] == doc_id
    assert data_res["status"] == "COMPLETED"
    assert data_res["fields_count"] > 0
    assert any(f["field_name"] == "monthly_gross_salary" for f in data_res["fields"])

    # 5. Get Extracted Fields
    get_res = client.get(f"/api/v1/documents/{doc_id}/extracted-fields")
    assert get_res.status_code == 200
    assert get_res.json()["fields_count"] == data_res["fields_count"]

def test_field_extraction_idempotency():
    content = b"SYNTHETIC LOAN DOCUMENT\nKYC / IDENTITY DOCUMENT\nFull Name: Rohan Kumar\nDate of Birth: 1987-03-12"
    files = {"file": ("idempotent_kyc.txt", content, "text/plain")}
    data = {"document_type": "KYC"}
    
    upload_res = client.post("/api/v1/applications/FIELD-TEST-APP/documents", files=files, data=data)
    doc_id = upload_res.json()["document_id"]

    client.post(f"/api/v1/documents/{doc_id}/extract-text")
    client.post(f"/api/v1/documents/{doc_id}/classify")

    res1 = client.post(f"/api/v1/documents/{doc_id}/extract-fields")
    assert res1.status_code == 200

    # Second call returns cached COMPLETED response
    res2 = client.post(f"/api/v1/documents/{doc_id}/extract-fields")
    assert res2.status_code == 200
    assert res2.json()["status"] == "COMPLETED"

def test_field_extraction_nonexistent_document_404():
    res = client.post("/api/v1/documents/NONEXISTENT-DOC-999/extract-fields")
    assert res.status_code == 404

def test_synthetic_documents_field_extraction_across_all_applicants():
    """Verify field extraction against synthetic documents for applicants A001..A010."""
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
            
            if cls_res.document_type == "PAYSLIP":
                f_list = extract_payslip_fields(ex_res.text)
                assert any(f.field_name == "monthly_gross_salary" for f in f_list)
                assert any(f.field_name == "employee_name" for f in f_list)
            elif cls_res.document_type == "BANK_STATEMENT":
                f_list = extract_bank_statement_fields(ex_res.text)
                assert any(f.field_name == "account_number" for f in f_list)
                assert any(f.field_name == "closing_balance" for f in f_list)
            elif cls_res.document_type == "TAX_RETURN":
                f_list = extract_tax_return_fields(ex_res.text)
                assert any(f.field_name == "declared_annual_income" for f in f_list)
                assert any(f.field_name == "taxpayer_name" for f in f_list)
            elif cls_res.document_type == "KYC":
                f_list = extract_kyc_fields(ex_res.text)
                assert any(f.field_name == "full_name" for f in f_list)
                assert any(f.field_name == "government_id_number" for f in f_list)
