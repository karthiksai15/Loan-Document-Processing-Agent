import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.cross_document_verification_service import (
    normalize_name,
    calculate_income_difference
)

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_verification_app():
    """Ensure test application exists prior to verification tests."""
    payload = {
        "application_id": "VER-TEST-APP",
        "applicant_name": "Rohan Kumar",
        "loan_amount": 4700000.0
    }
    client.post("/api/v1/applications", json=payload)


def test_normalize_name_unit():
    assert normalize_name("  Rohan  Kumar  ") == "rohan kumar"
    assert normalize_name("Mr. Rohan Kumar.") == "mr rohan kumar"
    assert normalize_name("AARAV-SHARMA,") == "aarav sharma"
    assert normalize_name(None) == ""


def test_calculate_income_difference_unit():
    # Exact match
    diff, pct, within = calculate_income_difference(1000000.0, 1000000.0, 10.0)
    assert diff == 0.0
    assert pct == 0.0
    assert within is True

    # Within 10% tolerance (5% difference)
    diff, pct, within = calculate_income_difference(1000000.0, 950000.0, 10.0)
    assert diff == 50000.0
    assert pct == 5.0
    assert within is True

    # Outside 10% tolerance (30% difference)
    diff, pct, within = calculate_income_difference(1600000.0, 1120000.0, 10.0)
    assert diff == 480000.0
    assert pct == 30.0
    assert within is False


def test_verification_404_not_found():
    res_post = client.post("/api/v1/applications/NON-EXISTENT-APP/verify")
    assert res_post.status_code == 404

    res_get = client.get("/api/v1/applications/NON-EXISTENT-APP/verification")
    assert res_get.status_code == 404


def test_verification_idempotency_and_api_workflow():
    app_id = "VER-WORKFLOW-APP"
    client.post("/api/v1/applications", json={"application_id": app_id, "applicant_name": "Rohan Kumar", "loan_amount": 4700000.0})

    # Upload Payslip
    content_pay = b"SYNTHETIC LOAN DOCUMENT\nPAYSLIP\nEmployee Name: Rohan Kumar\nEmployer: Vertex Systems India\nMonthly Gross Salary: INR 392,000\nMonthly Net Salary: INR 350,000"
    upload_res = client.post(f"/api/v1/applications/{app_id}/documents", files={"file": ("payslip.txt", content_pay, "text/plain")}, data={"document_type": "PAYSLIP"})
    if upload_res.status_code == 201:
        doc_id = upload_res.json()["document_id"]
    elif upload_res.status_code == 409:
        docs_res = client.get(f"/api/v1/applications/{app_id}/documents")
        doc_id = docs_res.json()["documents"][0]["document_id"]
    else:
        pytest.fail(f"Upload failed: {upload_res.text}")

    # Process through pipeline
    client.post(f"/api/v1/documents/{doc_id}/extract-text")
    client.post(f"/api/v1/documents/{doc_id}/classify")
    client.post(f"/api/v1/documents/{doc_id}/extract-fields")
    client.post(f"/api/v1/documents/{doc_id}/validate")

    # 1. Trigger verification
    ver_res = client.post(f"/api/v1/applications/{app_id}/verify")
    assert ver_res.status_code == 200
    data = ver_res.json()
    assert data["status"] == "COMPLETED"
    assert data["total_comparisons"] > 0

    # 2. Idempotency test (repeat call)
    ver_repeat = client.post(f"/api/v1/applications/{app_id}/verify")
    assert ver_repeat.status_code == 200
    assert ver_repeat.json()["status"] == "COMPLETED"

    # 3. GET verification
    get_res = client.get(f"/api/v1/applications/{app_id}/verification")
    assert get_res.status_code == 200
    assert get_res.json()["application_id"] == app_id


def test_synthetic_applicants_cross_document_verification():
    """
    Integration test processing synthetic applicants A001..A010 through the full pipeline:
    Upload -> Extract Text -> Classify -> Extract Fields -> Validate -> Verify.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    for app_id in ["A001", "A002", "A003", "A004", "A005", "A006", "A007", "A008", "A009", "A010"]:
        app_dir = os.path.join(project_root, "data", "applicants", app_id)
        if not os.path.exists(app_dir):
            continue

        # Create application in system
        client.post("/api/v1/applications", json={
            "application_id": app_id,
            "applicant_name": f"Synthetic Applicant {app_id}",
            "loan_amount": 1000000.0
        })

        # Process all documents in applicant directory
        for fname in sorted(os.listdir(app_dir)):
            if not fname.endswith(".txt"):
                continue

            fpath = os.path.join(app_dir, fname)
            with open(fpath, "rb") as f:
                content = f.read()

            upload_res = client.post(
                f"/api/v1/applications/{app_id}/documents",
                files={"file": (fname, content, "text/plain")},
                data={"document_type": "OTHER"}
            )
            
            if upload_res.status_code == 201:
                doc_id = upload_res.json()["document_id"]
            elif upload_res.status_code == 409:
                docs_res = client.get(f"/api/v1/applications/{app_id}/documents")
                doc_list = docs_res.json().get("documents", [])
                matching = [d for d in doc_list if d["original_filename"] == fname]
                if matching:
                    doc_id = matching[0]["document_id"]
                else:
                    continue
            else:
                pytest.fail(f"Upload failed with status {upload_res.status_code}: {upload_res.text}")

            client.post(f"/api/v1/documents/{doc_id}/extract-text")
            client.post(f"/api/v1/documents/{doc_id}/classify")
            client.post(f"/api/v1/documents/{doc_id}/extract-fields")
            client.post(f"/api/v1/documents/{doc_id}/validate")

        # Run cross-document verification
        ver_res = client.post(f"/api/v1/applications/{app_id}/verify")
        assert ver_res.status_code == 200
        val_data = ver_res.json()
        assert val_data["status"] == "COMPLETED"

        # Specific assertions for synthetic test cases
        findings = val_data["findings"]
        findings_map = {f["rule_name"]: f for f in findings}

        if app_id == "A001":
            # Normal applicant: expect zero mismatches
            assert val_data["mismatched_comparisons"] == 0

        elif app_id == "A003":
            # Missing Tax Return: tax comparison must report NOT_AVAILABLE
            assert "app_income_vs_tax_income" in findings_map
            assert findings_map["app_income_vs_tax_income"]["result"] == "NOT_AVAILABLE"

        elif app_id == "A004":
            # Bank Income Mismatch
            assert val_data["mismatched_comparisons"] > 0
            assert "payslip_salary_vs_bank_credit" in findings_map
            assert findings_map["payslip_salary_vs_bank_credit"]["result"] == "MISMATCH"

        elif app_id == "A005":
            # Payslip Income Mismatch
            assert val_data["mismatched_comparisons"] > 0
            assert "app_income_vs_payslip_annualized" in findings_map
            assert findings_map["app_income_vs_payslip_annualized"]["result"] == "MISMATCH"

        elif app_id == "A006":
            # KYC Name Mismatch
            assert val_data["mismatched_comparisons"] > 0
            assert "app_name_vs_kyc_name" in findings_map
            assert findings_map["app_name_vs_kyc_name"]["result"] == "MISMATCH"

        elif app_id == "A007":
            # Tax Income Mismatch
            assert val_data["mismatched_comparisons"] > 0
            assert "app_income_vs_tax_income" in findings_map or "payslip_annualized_vs_tax_income" in findings_map
            if "app_income_vs_tax_income" in findings_map:
                assert findings_map["app_income_vs_tax_income"]["result"] == "MISMATCH"

        elif app_id == "A009":
            # Missing Bank Statement: bank salary comparison must report NOT_AVAILABLE
            assert "payslip_salary_vs_bank_credit" in findings_map
            assert findings_map["payslip_salary_vs_bank_credit"]["result"] == "NOT_AVAILABLE"
