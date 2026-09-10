import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_application():
    """Ensure a test application exists prior to document tests."""
    payload = {
        "application_id": "DOC-TEST-APP",
        "applicant_name": "Jane Smith",
        "loan_amount": 750000.0
    }
    client.post("/api/v1/applications", json=payload)

def test_upload_txt_document_success():
    content = b"Sample Payslip Content for Jane Smith"
    files = {"file": ("payslip_august.txt", content, "text/plain")}
    data = {"document_type": "PAYSLIP"}
    
    response = client.post("/api/v1/applications/DOC-TEST-APP/documents", files=files, data=data)
    assert response.status_code == 201
    res = response.json()
    assert res["application_id"] == "DOC-TEST-APP"
    assert res["original_filename"] == "payslip_august.txt"
    assert res["document_type"] == "PAYSLIP"
    assert res["file_size"] == len(content)
    assert res["processing_status"] == "UPLOADED"
    assert "checksum" in res

def test_upload_pdf_document_success():
    content = b"%PDF-1.4 Mock PDF Binary Data Content"
    files = {"file": ("bank_statement.pdf", content, "application/pdf")}
    data = {"document_type": "BANK_STATEMENT"}
    
    response = client.post("/api/v1/applications/DOC-TEST-APP/documents", files=files, data=data)
    assert response.status_code == 201
    res = response.json()
    assert res["original_filename"] == "bank_statement.pdf"
    assert res["document_type"] == "BANK_STATEMENT"

def test_upload_unsupported_extension_rejection():
    content = b"echo 'malicious script'"
    files = {"file": ("script.sh", content, "application/x-sh")}
    data = {"document_type": "OTHER"}
    
    response = client.post("/api/v1/applications/DOC-TEST-APP/documents", files=files, data=data)
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]

def test_upload_empty_file_rejection():
    content = b""
    files = {"file": ("empty.txt", content, "text/plain")}
    data = {"document_type": "KYC"}
    
    response = client.post("/api/v1/applications/DOC-TEST-APP/documents", files=files, data=data)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

def test_upload_file_exceeding_size_limit_rejection():
    # Generate 11MB payload exceeding default 10MB limit
    content = b"X" * (11 * 1024 * 1024)
    files = {"file": ("large_file.txt", content, "text/plain")}
    data = {"document_type": "TAX_RETURN"}
    
    response = client.post("/api/v1/applications/DOC-TEST-APP/documents", files=files, data=data)
    assert response.status_code == 400
    assert "exceeds maximum limit" in response.json()["detail"]

def test_upload_invalid_document_type_rejection():
    content = b"Valid content"
    files = {"file": ("valid.txt", content, "text/plain")}
    data = {"document_type": "INVALID_CATEGORY_XYZ"}
    
    response = client.post("/api/v1/applications/DOC-TEST-APP/documents", files=files, data=data)
    assert response.status_code == 400
    assert "Invalid document category" in response.json()["detail"]

def test_upload_nonexistent_application_404():
    content = b"Valid content"
    files = {"file": ("valid.txt", content, "text/plain")}
    data = {"document_type": "KYC"}
    
    response = client.post("/api/v1/applications/GHOST-APP-999/documents", files=files, data=data)
    assert response.status_code == 404

def test_duplicate_checksum_rejection_409():
    content = b"Unique content for duplicate check test"
    files1 = {"file": ("doc_v1.txt", content, "text/plain")}
    data = {"document_type": "KYC"}
    
    res1 = client.post("/api/v1/applications/DOC-TEST-APP/documents", files=files1, data=data)
    assert res1.status_code == 201
    
    # Attempt to upload identical content to same application
    files2 = {"file": ("doc_v2_renamed.txt", content, "text/plain")}
    res2 = client.post("/api/v1/applications/DOC-TEST-APP/documents", files=files2, data=data)
    assert res2.status_code == 409
    assert "Duplicate document detected" in res2.json()["detail"]

def test_path_traversal_protection():
    content = b"Path traversal payload check"
    files = {"file": ("../../malicious_file.txt", content, "text/plain")}
    data = {"document_type": "OTHER"}
    
    response = client.post("/api/v1/applications/DOC-TEST-APP/documents", files=files, data=data)
    assert response.status_code == 201
    res = response.json()
    assert res["original_filename"] == "malicious_file.txt"

def test_list_and_download_and_delete_document_lifecycle():
    # 1. Upload a document
    content = b"Lifecycle test document payload"
    files = {"file": ("lifecycle_test.txt", content, "text/plain")}
    data = {"document_type": "KYC"}
    
    upload_res = client.post("/api/v1/applications/DOC-TEST-APP/documents", files=files, data=data)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["document_id"]
    
    # 2. List documents for application
    list_res = client.get("/api/v1/applications/DOC-TEST-APP/documents")
    assert list_res.status_code == 200
    docs = list_res.json()["documents"]
    assert any(d["document_id"] == doc_id for d in docs)
    
    # 3. Get document metadata
    meta_res = client.get(f"/api/v1/documents/{doc_id}")
    assert meta_res.status_code == 200
    assert meta_res.json()["document_id"] == doc_id
    
    # 4. Download document
    dl_res = client.get(f"/api/v1/documents/{doc_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.content == content
    
    # 5. Delete document
    del_res = client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 200
    
    # 6. Verify deleted metadata returns 404
    meta_res_after = client.get(f"/api/v1/documents/{doc_id}")
    assert meta_res_after.status_code == 404
