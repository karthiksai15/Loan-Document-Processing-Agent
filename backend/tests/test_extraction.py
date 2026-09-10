import os
import pymupdf
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.text_extraction_service import extract_text_from_file, is_tesseract_available

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_extraction_test_app():
    """Ensure a test application exists prior to extraction tests."""
    payload = {
        "application_id": "EXTRACTION-TEST-APP",
        "applicant_name": "Aarav Sharma",
        "loan_amount": 300000.0
    }
    client.post("/api/v1/applications", json=payload)

def test_extract_txt_file_directly(tmp_path):
    txt_file = tmp_path / "sample_payslip.txt"
    txt_content = "Employee Name: Aarav Sharma\nMonthly Salary: INR 25,000"
    txt_file.write_text(txt_content, encoding="utf-8")

    res = extract_text_from_file(str(txt_file), "sample_payslip.txt")
    assert res.success is True
    assert res.method == "TEXT"
    assert res.page_count == 1
    assert "Aarav Sharma" in res.text
    assert res.character_count == len(txt_content)

def test_extract_pdf_file_directly(tmp_path):
    pdf_file = tmp_path / "sample_document.pdf"
    doc = pymupdf.open()
    
    # Page 1
    page1 = doc.new_page()
    page1.insert_text((50, 50), "Bank Statement Page 1 Content for Aarav Sharma")
    
    # Page 2
    page2 = doc.new_page()
    page2.insert_text((50, 50), "Bank Statement Page 2 Transaction Summary")
    
    doc.save(str(pdf_file))
    doc.close()

    res = extract_text_from_file(str(pdf_file), "sample_document.pdf")
    assert res.success is True
    assert res.method == "PDF_TEXT"
    assert res.page_count == 2
    assert "--- PAGE 1 ---" in res.text
    assert "--- PAGE 2 ---" in res.text
    assert "Aarav Sharma" in res.text
    assert "Transaction Summary" in res.text

def test_extraction_api_workflow(tmp_path):
    # 1. Upload a TXT document to application
    content = b"Synthetic Payslip Content for Aarav Sharma\nGross Pay: 25000"
    files = {"file": ("payslip_test.txt", content, "text/plain")}
    data = {"document_type": "PAYSLIP"}
    
    upload_res = client.post("/api/v1/applications/EXTRACTION-TEST-APP/documents", files=files, data=data)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["document_id"]

    # 2. Trigger text extraction endpoint
    extract_res = client.post(f"/api/v1/documents/{doc_id}/extract-text")
    assert extract_res.status_code == 200
    ex_data = extract_res.json()
    assert ex_data["document_id"] == doc_id
    assert ex_data["status"] == "COMPLETED"
    assert ex_data["method"] == "TEXT"
    assert "Aarav Sharma" in ex_data["text"]

    # 3. Retrieve extracted text endpoint
    get_res = client.get(f"/api/v1/documents/{doc_id}/text")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["document_id"] == doc_id
    assert get_data["status"] == "COMPLETED"
    assert get_data["text"] == ex_data["text"]

def test_extraction_idempotency():
    content = b"Idempotent Extraction Test Content"
    files = {"file": ("idempotent.txt", content, "text/plain")}
    data = {"document_type": "KYC"}
    
    upload_res = client.post("/api/v1/applications/EXTRACTION-TEST-APP/documents", files=files, data=data)
    doc_id = upload_res.json()["document_id"]

    res1 = client.post(f"/api/v1/documents/{doc_id}/extract-text")
    assert res1.status_code == 200

    # Second call should return cached COMPLETED result
    res2 = client.post(f"/api/v1/documents/{doc_id}/extract-text")
    assert res2.status_code == 200
    assert res2.json()["status"] == "COMPLETED"

def test_nonexistent_document_extraction_404():
    res = client.post("/api/v1/documents/NONEXISTENT-DOC-999/extract-text")
    assert res.status_code == 404

def test_actual_synthetic_documents_extraction():
    """Verify extraction against actual Phase 2 synthetic documents in data/applicants/A001/"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a001_dir = os.path.join(project_root, "data", "applicants", "A001")
    
    test_files = ["01_payslip.txt", "02_bank_statement.txt", "03_tax_return.txt", "04_kyc.txt"]
    
    for f_name in test_files:
        f_path = os.path.join(a001_dir, f_name)
        assert os.path.exists(f_path), f"Synthetic file missing: {f_path}"
        
        res = extract_text_from_file(f_path, f_name)
        assert res.success is True
        assert res.method == "TEXT"
        assert len(res.text) > 0
        assert "Aarav Sharma" in res.text or "DEMO" in res.text

def test_ocr_system_dependency_graceful_handling():
    tesseract_installed = is_tesseract_available()
    print(f"Tesseract installed status: {tesseract_installed}")
    # Verify helper correctly reports system binary state without throwing exception
    assert isinstance(tesseract_installed, bool)
