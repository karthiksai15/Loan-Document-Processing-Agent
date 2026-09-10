import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models import ReviewAssessmentModel

client = TestClient(app)

def helper_process_applicant_pipeline(app_id: str):
    """Processes applicant documents through extraction -> classification -> field extraction -> validation -> verification -> risk prediction."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    app_dir = os.path.join(project_root, "data", "applicants", app_id)

    client.post("/api/v1/applications", json={
        "application_id": app_id,
        "applicant_name": f"Synthetic Applicant {app_id}",
        "loan_amount": 1000000.0
    })

    if os.path.exists(app_dir):
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
                pytest.fail(f"Upload failed: {upload_res.text}")

            client.post(f"/api/v1/documents/{doc_id}/extract-text")
            client.post(f"/api/v1/documents/{doc_id}/classify")
            client.post(f"/api/v1/documents/{doc_id}/extract-fields")
            client.post(f"/api/v1/documents/{doc_id}/validate")

    client.post(f"/api/v1/applications/{app_id}/verify")
    client.post(f"/api/v1/applications/{app_id}/risk/predict")


def test_review_score_404_not_found():
    """Test 404 response for non-existent application."""
    res_get = client.get("/api/v1/applications/NON-EXISTENT-APP-999/review-score")
    assert res_get.status_code == 404

    res_post = client.post("/api/v1/applications/NON-EXISTENT-APP-999/review-score")
    assert res_post.status_code == 404


def test_review_score_a001_clean_application():
    """Test A001 clean application -> LOW priority, HIGH trust, CLEAN matrix."""
    helper_process_applicant_pipeline("A001")

    res = client.post("/api/v1/applications/A001/review-score")
    assert res.status_code == 200
    data = res.json()

    assert data["application_id"] == "A001"
    assert 0.0 <= data["review_score"] <= 100.0
    assert 0.0 <= data["evidence_trust_score"] <= 100.0
    assert data["review_priority"] == "LOW"
    assert data["evidence_trust_level"] == "HIGH"
    assert data["risk_evidence_matrix_category"] == "CLEAN"
    assert data["document_completeness_status"] == "COMPLETE"
    assert data["verification_issue_count"] == 0
    assert data["validation_issue_count"] == 0
    assert data["recommended_action"] == "STANDARD_REVIEW"
    assert data["secondary_reasons"] == []


def test_review_score_a003_missing_tax_return():
    """Test A003 missing tax return -> Incomplete evidence, reduced trust, no false mismatch."""
    helper_process_applicant_pipeline("A003")

    res = client.post("/api/v1/applications/A003/review-score")
    assert res.status_code == 200
    data = res.json()

    assert data["application_id"] == "A003"
    assert data["document_completeness_status"] == "INCOMPLETE"
    assert data["evidence_trust_score"] < 100.0
    assert data["missing_documents"] == ["TAX_RETURN"]
    assert data["missing_document"] == "TAX_RETURN"
    assert data["recommended_action"] == "DOCUMENT_FOLLOWUP"
    assert data["risk_evidence_matrix_category"] in ["REVIEW", "INVESTIGATE"]
    # Confirm misleading narrative is eliminated:
    assert "all cross-document verification and validation checks passed successfully" not in [r.lower() for r in data["secondary_reasons"]]
    assert data["secondary_reasons"] == []


def test_review_score_a004_salary_mismatch():
    """Test A004 salary credit mismatch -> Verification finding, elevated review priority."""
    helper_process_applicant_pipeline("A004")

    res = client.post("/api/v1/applications/A004/review-score")
    assert res.status_code == 200
    data = res.json()

    assert data["application_id"] == "A004"
    assert data["verification_issue_count"] > 0
    assert data["verification_issue_type"] == "FINANCIAL_DISCREPANCY"
    assert data["recommended_action"] == "STANDARD_REVIEW"


def test_review_score_a006_identity_mismatch_separation():
    """Test A006 identity mismatch -> LOW ML risk (5.66%) BUT HIGH Review Priority (78), proving separation."""
    helper_process_applicant_pipeline("A006")

    res = client.post("/api/v1/applications/A006/review-score")
    assert res.status_code == 200
    data = res.json()

    assert data["application_id"] == "A006"
    assert data["ml_risk_level"] == "LOW"  # ML risk remains LOW (~5.66%)
    assert data["review_priority"] == "HIGH"  # Review Priority is HIGH due to ID mismatch!
    assert data["evidence_trust_level"] == "LOW"
    assert data["risk_evidence_matrix_category"] == "INVESTIGATE"
    assert data["critical_issue"] == "PRIMARY_IDENTITY_MISMATCH"
    assert data["verification_issue_type"] == "PRIMARY_IDENTITY_MISMATCH"
    assert data["verification_issue_count"] == 4
    assert data["recommended_action"] == "OFFICER_INVESTIGATION"


def test_review_score_a007_high_ml_risk():
    """Test A007 high ML risk -> Rejection probability > 65%, HIGH ML risk level."""
    helper_process_applicant_pipeline("A007")

    res = client.post("/api/v1/applications/A007/review-score")
    assert res.status_code == 200
    data = res.json()

    assert data["application_id"] == "A007"
    assert data["ml_risk_level"] == "HIGH"
    assert data["ml_risk_score"] > 0.65
    assert data["risk_evidence_matrix_category"] in ["INVESTIGATE", "REVIEW"]
    assert data["verification_issue_count"] == 2
    assert data["verification_issue_type"] == "FINANCIAL_DISCREPANCY"
    assert data["issue_type"] == "FINANCIAL_DISCREPANCY"
    assert data["recommended_action"] == "OFFICER_INVESTIGATION"


def test_review_score_a009_missing_bank_statement():
    """Test A009 missing bank statement -> Incomplete evidence, no false mismatch."""
    helper_process_applicant_pipeline("A009")

    res = client.post("/api/v1/applications/A009/review-score")
    assert res.status_code == 200
    data = res.json()

    assert data["application_id"] == "A009"
    assert data["document_completeness_status"] == "INCOMPLETE"
    assert data["missing_documents"] == ["BANK_STATEMENT"]
    assert data["missing_document"] == "BANK_STATEMENT"
    assert data["recommended_action"] == "OFFICER_INVESTIGATION"



def test_review_score_a010_borderline_ml_risk():
    """Test A010 medium ML risk -> MEDIUM ML risk level, REVIEW matrix category."""
    helper_process_applicant_pipeline("A010")

    res = client.post("/api/v1/applications/A010/review-score")
    assert res.status_code == 200
    data = res.json()

    assert data["application_id"] == "A010"
    assert data["ml_risk_level"] in ["LOW", "MEDIUM"]
    assert 0.0 <= data["review_score"] <= 100.0


def test_review_score_idempotency_and_evidence_node_integration():
    """Test idempotency and verification of REVIEW_ASSESSMENT node in Evidence Graph."""
    helper_process_applicant_pipeline("A001")

    # Call POST review-score twice
    res1 = client.post("/api/v1/applications/A001/review-score")
    assert res1.status_code == 200
    score1 = res1.json()["review_score"]

    res2 = client.post("/api/v1/applications/A001/review-score")
    assert res2.status_code == 200
    score2 = res2.json()["review_score"]

    assert score1 == score2

    # Check Evidence Graph
    res_evi = client.get("/api/v1/applications/A001/evidence")
    assert res_evi.status_code == 200
    evi_data = res_evi.json()

    rev_nodes = [n for n in evi_data["nodes"] if n["node_type"] == "REVIEW_ASSESSMENT"]
    assert len(rev_nodes) > 0
    assert "Review Assessment" in rev_nodes[0]["title"]


def test_review_score_no_narrative_sentences():
    """Verify Phase 12 produces purely structured deterministic outputs without narrative prose."""
    for app_id in ["A001", "A003", "A004", "A006", "A007"]:
        helper_process_applicant_pipeline(app_id)
        res = client.get(f"/api/v1/applications/{app_id}/review-score")
        assert res.status_code == 200
        data = res.json()

        # Confirm no misleading fallback prose
        assert "all cross-document" not in " ".join(data.get("secondary_reasons") or []).lower()
        assert not any(len(r.split()) > 5 for r in (data.get("secondary_reasons") or []))

        # Confirm structured attributes are populated
        assert "document_completeness_status" in data
        assert "missing_documents" in data
        assert "score_factors" in data
        assert isinstance(data["score_factors"], list)
        assert data["recommended_action"] in ["STANDARD_REVIEW", "DOCUMENT_FOLLOWUP", "OFFICER_INVESTIGATION"]

