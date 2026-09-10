import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models import EvidenceNodeModel, EvidenceRelationshipModel

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_evidence_app():
    """Ensure test application exists prior to evidence tests."""
    payload = {
        "application_id": "EVI-TEST-APP",
        "applicant_name": "Rohan Kumar",
        "loan_amount": 4700000.0
    }
    client.post("/api/v1/applications", json=payload)


def test_evidence_node_and_relationship_models_unit():
    node = EvidenceNodeModel(
        node_id="NODE-TEST-1",
        application_id="EVI-TEST-APP",
        node_type="APPLICATION",
        title="Test Application Node",
        value="Test Value"
    )
    assert node.node_id == "NODE-TEST-1"
    assert node.node_type == "APPLICATION"

    rel = EvidenceRelationshipModel(
        relationship_id="REL-TEST-1",
        application_id="EVI-TEST-APP",
        source_node_id="NODE-TEST-1",
        target_node_id="NODE-TEST-2",
        relationship_type="HAS_DOCUMENT"
    )
    assert rel.relationship_id == "REL-TEST-1"
    assert rel.relationship_type == "HAS_DOCUMENT"


def test_evidence_404_not_found():
    res_get = client.get("/api/v1/applications/NON-EXISTENT-APP/evidence")
    assert res_get.status_code == 404

    res_post = client.post("/api/v1/applications/NON-EXISTENT-APP/evidence")
    assert res_post.status_code == 404


def helper_process_applicant_pipeline(app_id: str):
    """Processes applicant documents through text extraction -> classification -> field extraction -> validation -> verification."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    app_dir = os.path.join(project_root, "data", "applicants", app_id)

    client.post("/api/v1/applications", json={
        "application_id": app_id,
        "applicant_name": f"Synthetic Applicant {app_id}",
        "loan_amount": 1000000.0
    })

    if not os.path.exists(app_dir):
        return

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


def test_evidence_generation_clean_application_a001():
    helper_process_applicant_pipeline("A001")

    res = client.get("/api/v1/applications/A001/evidence")
    assert res.status_code == 200
    data = res.json()

    assert data["application_id"] == "A001"
    assert data["total_nodes"] > 5
    assert data["total_relationships"] > 5

    node_types = [n["node_type"] for n in data["nodes"]]
    assert "APPLICATION" in node_types
    assert "DOCUMENT" in node_types
    assert "FIELD" in node_types

    rel_types = [r["relationship_type"] for r in data["relationships"]]
    assert "HAS_DOCUMENT" in rel_types
    assert "CONTAINS_FIELD" in rel_types


def test_evidence_generation_salary_mismatch_a004():
    helper_process_applicant_pipeline("A004")

    res = client.get("/api/v1/applications/A004/evidence")
    assert res.status_code == 200
    data = res.json()

    # Find salary mismatch finding node
    finding_nodes = [n for n in data["nodes"] if n["node_type"] == "VERIFICATION_FINDING" and "payslip_salary_vs_bank_credit" in n["title"]]
    assert len(finding_nodes) > 0
    salary_finding_node = finding_nodes[0]
    assert "MISMATCH" in salary_finding_node["title"]

    # Verify SUPPORTS relationships pointing to this finding node
    supports_rels = [r for r in data["relationships"] if r["target_node_id"] == salary_finding_node["node_id"] and r["relationship_type"] == "SUPPORTS"]
    assert len(supports_rels) > 0


def test_evidence_generation_identity_mismatch_a006():
    helper_process_applicant_pipeline("A006")

    res = client.get("/api/v1/applications/A006/evidence")
    assert res.status_code == 200
    data = res.json()

    # Find identity mismatch finding node
    finding_nodes = [n for n in data["nodes"] if n["node_type"] == "VERIFICATION_FINDING" and "app_name_vs_kyc_name" in n["title"]]
    assert len(finding_nodes) > 0
    id_finding_node = finding_nodes[0]
    assert "MISMATCH" in id_finding_node["title"]


def test_evidence_idempotency_and_duplicate_safety():
    helper_process_applicant_pipeline("A001")

    # Call POST /evidence twice
    res1 = client.post("/api/v1/applications/A001/evidence")
    assert res1.status_code == 200
    count1_nodes = res1.json()["total_nodes"]
    count1_rels = res1.json()["total_relationships"]

    res2 = client.post("/api/v1/applications/A001/evidence")
    assert res2.status_code == 200
    count2_nodes = res2.json()["total_nodes"]
    count2_rels = res2.json()["total_relationships"]

    assert count1_nodes == count2_nodes
    assert count1_rels == count2_rels
