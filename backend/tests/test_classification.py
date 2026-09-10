import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.document_classification_service import classify_text
from app.services.text_extraction_service import extract_text_from_file

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_classification_test_app():
    """Ensure a test application exists prior to classification tests."""
    payload = {
        "application_id": "CLASS-TEST-APP",
        "applicant_name": "Rohan Kumar",
        "loan_amount": 4700000.0
    }
    client.post("/api/v1/applications", json=payload)

def test_classify_payslip_text():
    text = "PAYSLIP\nEmployee Name: Rohan Kumar\nMonthly Gross Salary: INR 392,000\nMonthly Net Salary: INR 350,000\nPay Period: August 2026"
    res = classify_text(text)
    assert res.document_type == "PAYSLIP"
    assert res.confidence >= 0.50
    assert "gross salary" in res.matched_signals or "payslip" in res.matched_signals

def test_classify_bank_statement_text():
    text = "BANK STATEMENT\nAccount Holder: Rohan Kumar\nAccount Number: XXXX-DEMO-A003\nStatement Period: 01-Aug-2026 to 31-Aug-2026\nAverage Monthly Balance: INR 6,500,000\nMonthly Salary Credit: INR 392,000"
    res = classify_text(text)
    assert res.document_type == "BANK_STATEMENT"
    assert res.confidence >= 0.50
    assert "bank statement" in res.matched_signals or "account number" in res.matched_signals

def test_classify_tax_return_text():
    text = "INCOME TAX RETURN\nTaxpayer Name: Rohan Kumar\nTax Year: FY 2025-26\nDeclared Annual Income: INR 4,700,000\nGross Total Income: INR 4,700,000\nAssessment Year: 2026-27"
    res = classify_text(text)
    assert res.document_type == "TAX_RETURN"
    assert res.confidence >= 0.50
    assert "tax return" in res.matched_signals or "declared annual income" in res.matched_signals

def test_classify_kyc_text():
    text = "KYC / IDENTITY DOCUMENT\nFull Name: Rohan Kumar\nDate of Birth: 1987-03-12\nSynthetic ID Number: DEMO-KYC-A003\nAddress: 12, Demo Residency, Bengaluru"
    res = classify_text(text)
    assert res.document_type == "KYC"
    assert res.confidence >= 0.50
    assert "kyc" in res.matched_signals or "date of birth" in res.matched_signals

def test_classify_unrelated_text_returns_other():
    text = "This is a university event notification regarding an upcoming sports tournament next Friday."
    res = classify_text(text)
    assert res.document_type == "OTHER"
    assert res.confidence < 0.40

def test_classify_empty_text_returns_other():
    res = classify_text("")
    assert res.document_type == "OTHER"
    assert res.confidence == 0.0

def test_classify_ambiguous_text_returns_other():
    # Text with equal scores across PAYSLIP (salary + employee = 2.0) and BANK_STATEMENT (account + transaction = 2.0)
    text = "Salary employee account transaction details."
    res = classify_text(text)
    assert res.document_type == "OTHER"
    assert res.confidence <= 0.35

def test_case_insensitivity_normalization():
    res1 = classify_text("PAYSLIP\nMONTHLY GROSS SALARY: 50000")
    res2 = classify_text("payslip\nmonthly gross salary: 50000")
    assert res1.document_type == res2.document_type == "PAYSLIP"

def test_classification_fails_if_text_not_extracted():
    # 1. Upload a document without extracting text
    content = b"Synthetic Payslip Content"
    files = {"file": ("unextracted_payslip.txt", content, "text/plain")}
    data = {"document_type": "PAYSLIP"}
    
    upload_res = client.post("/api/v1/applications/CLASS-TEST-APP/documents", files=files, data=data)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["document_id"]

    # 2. Attempt classification before text extraction
    class_res = client.post(f"/api/v1/documents/{doc_id}/classify")
    assert class_res.status_code == 400
    assert "not been extracted yet" in class_res.json()["detail"].lower()

def test_classification_api_full_workflow():
    # 1. Upload
    content = b"SYNTHETIC LOAN DOCUMENT\nPAYSLIP\nEmployee Name: Rohan Kumar\nMonthly Gross Salary: INR 392,000\nMonthly Net Salary: INR 350,000"
    files = {"file": ("workflow_payslip.txt", content, "text/plain")}
    data = {"document_type": "OTHER"}  # User metadata set to OTHER
    
    upload_res = client.post("/api/v1/applications/CLASS-TEST-APP/documents", files=files, data=data)
    doc_id = upload_res.json()["document_id"]

    # 2. Extract text
    ex_res = client.post(f"/api/v1/documents/{doc_id}/extract-text")
    assert ex_res.status_code == 200

    # 3. Classify
    class_res = client.post(f"/api/v1/documents/{doc_id}/classify")
    assert class_res.status_code == 200
    c_data = class_res.json()
    assert c_data["document_id"] == doc_id
    assert c_data["classified_document_type"] == "PAYSLIP"
    assert c_data["status"] == "COMPLETED"
    assert len(c_data["matched_signals"]) > 0

    # 4. Get classification endpoint
    get_res = client.get(f"/api/v1/documents/{doc_id}/classification")
    assert get_res.status_code == 200
    assert get_res.json()["classified_document_type"] == "PAYSLIP"

def test_classification_idempotency():
    content = b"SYNTHETIC LOAN DOCUMENT\nINCOME TAX RETURN\nTaxpayer Name: Rohan Kumar\nTax Year: FY 2025-26\nDeclared Annual Income: INR 4,700,000"
    files = {"file": ("idempotent_tax.txt", content, "text/plain")}
    data = {"document_type": "TAX_RETURN"}
    
    upload_res = client.post("/api/v1/applications/CLASS-TEST-APP/documents", files=files, data=data)
    doc_id = upload_res.json()["document_id"]

    client.post(f"/api/v1/documents/{doc_id}/extract-text")
    
    res1 = client.post(f"/api/v1/documents/{doc_id}/classify")
    assert res1.status_code == 200
    assert res1.json()["classified_document_type"] == "TAX_RETURN"

    # Second call returns cached result
    res2 = client.post(f"/api/v1/documents/{doc_id}/classify")
    assert res2.status_code == 200
    assert res2.json()["status"] == "COMPLETED"

def test_classification_nonexistent_document_404():
    res = client.post("/api/v1/documents/NONEXISTENT-DOC-999/classify")
    assert res.status_code == 404

def test_synthetic_documents_classification_across_applicants():
    """Verify classification against extracted synthetic documents for A001, A002, A004, A008."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    expected_mapping = {
        "01_payslip.txt": "PAYSLIP",
        "02_bank_statement.txt": "BANK_STATEMENT",
        "03_tax_return.txt": "TAX_RETURN",
        "04_kyc.txt": "KYC"
    }

    for app_id in ["A001", "A002", "A004", "A008"]:
        app_dir = os.path.join(project_root, "data", "applicants", app_id)
        for fname, expected_cat in expected_mapping.items():
            fpath = os.path.join(app_dir, fname)
            if not os.path.exists(fpath):
                continue
                
            ex_res = extract_text_from_file(fpath, fname)
            assert ex_res.success is True
            
            c_res = classify_text(ex_res.text)
            assert c_res.document_type == expected_cat, f"Mismatch for {app_id}/{fname}: expected {expected_cat}, got {c_res.document_type}"
            assert c_res.confidence >= 0.50
