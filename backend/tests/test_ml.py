import os
import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient
from app.main import app
from app.ml.features import FinancialFeatureEngineer
from app.ml.preprocessing import build_preprocessing_pipeline, ALL_FEATURE_COLUMNS
from app.ml.predictor import RiskPredictor, predict_application_risk

client = TestClient(app)

def test_feature_engineering_financial_transformer():
    """Unit test for FinancialFeatureEngineer transformer."""
    df_raw = pd.DataFrame([{
        "no_of_dependents": 2,
        "education": " Graduate",
        "self_employed": " No",
        "income_annum": 6000000.0,
        "loan_amount": 18000000.0,
        "loan_term": 12,
        "cibil_score": 750,
        "residential_assets_value": -500000.0,  # Negative value to test clipping
        "commercial_assets_value": 2000000.0,
        "luxury_assets_value": 8000000.0,
        "bank_asset_value": 3000000.0
    }])

    engineer = FinancialFeatureEngineer()
    df_engineered = engineer.fit_transform(df_raw)

    # Check engineered columns presence
    assert "total_asset_value" in df_engineered.columns
    assert "loan_to_income_ratio" in df_engineered.columns
    assert "loan_to_asset_ratio" in df_engineered.columns

    # Check negative residential asset clipping (-500000 -> 0)
    # total_asset_value = 0 + 2,000,000 + 8,000,000 + 3,000,000 = 13,000,000
    assert df_engineered.loc[0, "total_asset_value"] == 13000000.0
    # loan_to_income_ratio = 18,000,000 / 6,000,000 = 3.0
    assert df_engineered.loc[0, "loan_to_income_ratio"] == 3.0
    # loan_to_asset_ratio = 18,000,000 / 13,000,000 ≈ 1.3846
    assert abs(df_engineered.loc[0, "loan_to_asset_ratio"] - (18000000.0 / 13000000.0)) < 1e-4


def test_preprocessing_pipeline_creation():
    """Unit test for ColumnTransformer preprocessing pipeline."""
    pipeline = build_preprocessing_pipeline()

    df_engineered = pd.DataFrame([{
        "no_of_dependents": 2,
        "education": " Graduate",
        "self_employed": " No",
        "income_annum": 6000000.0,
        "loan_amount": 18000000.0,
        "loan_term": 12,
        "cibil_score": 750,
        "residential_assets_value": 5000000.0,
        "commercial_assets_value": 2000000.0,
        "luxury_assets_value": 8000000.0,
        "bank_asset_value": 3000000.0,
        "total_asset_value": 18000000.0,
        "loan_to_income_ratio": 3.0,
        "loan_to_asset_ratio": 1.0
    }])

    X_transformed = pipeline.fit_transform(df_engineered)
    assert X_transformed.shape[0] == 1
    assert X_transformed.shape[1] > 0


def test_trained_artifacts_exist_and_loadable():
    """Verify champion model artifacts exist in backend/app/ml/artifacts/ and load cleanly."""
    predictor = RiskPredictor.get_instance()
    assert predictor.is_loaded is True
    assert predictor.pipeline is not None
    assert predictor.champion_model is not None
    assert predictor.metadata is not None
    assert "champion_model_name" in predictor.metadata

    # Verify all 3 trained models are saved
    artifacts_dir = predictor.artifacts_dir
    assert os.path.exists(os.path.join(artifacts_dir, "logisticregression.joblib"))
    assert os.path.exists(os.path.join(artifacts_dir, "randomforest.joblib"))
    assert os.path.exists(os.path.join(artifacts_dir, "xgboost.joblib"))
    assert os.path.exists(os.path.join(artifacts_dir, "model_comparison.json"))



def test_risk_predictor_inference_valid_sample():
    """Test RiskPredictor inference with a valid complete sample feature dictionary."""
    valid_features = {
        "no_of_dependents": 2,
        "education": "Graduate",
        "self_employed": "No",
        "income_annum": 8000000.0,
        "loan_amount": 15000000.0,
        "loan_term": 12,
        "cibil_score": 800,
        "residential_assets_value": 10000000.0,
        "commercial_assets_value": 5000000.0,
        "luxury_assets_value": 12000000.0,
        "bank_asset_value": 6000000.0
    }

    res = predict_application_risk("TEST-APP-001", valid_features)
    assert res.status == "COMPLETED"
    assert res.application_id == "TEST-APP-001"
    assert 0.0 <= res.rejection_probability <= 1.0
    assert res.risk_level in ["LOW", "MEDIUM", "HIGH"]
    assert res.prediction in [0, 1]
    assert res.model_name != "UNAVAILABLE"


def test_risk_predictor_missing_features_guard():
    """Test RiskPredictor error guard when required features are missing."""
    incomplete_features = {
        "no_of_dependents": 1,
        "income_annum": 5000000.0
    }

    res = predict_application_risk("TEST-APP-MISSING", incomplete_features)
    assert res.status == "UNAVAILABLE"
    assert res.missing_features is not None
    assert len(res.missing_features) > 0
    assert "Required ML feature(s) missing" in res.reason


def test_predict_risk_api_endpoint_a001():
    """Test POST /api/v1/applications/{application_id}/risk/predict endpoint for A001."""
    # Ensure application A001 exists
    client.post("/api/v1/applications", json={
        "application_id": "A001",
        "applicant_name": "Applicant A001",
        "loan_amount": 3500000.0
    })

    res = client.post("/api/v1/applications/A001/risk/predict")
    assert res.status_code == 200
    data = res.json()

    assert data["application_id"] == "A001"
    assert data["status"] == "COMPLETED"
    assert "rejection_probability" in data
    assert 0.0 <= data["rejection_probability"] <= 1.0
    assert data["risk_level"] in ["LOW", "MEDIUM", "HIGH"]


def test_predict_risk_api_endpoint_404():
    """Test POST /api/v1/applications/{application_id}/risk/predict endpoint with 404 for non-existent app."""
    res = client.post("/api/v1/applications/NON-EXISTENT-APP-999/risk/predict")
    assert res.status_code == 404


def test_evidence_graph_ml_node_integration():
    """Test that ML Risk Assessment node is created in Evidence Graph after risk prediction."""
    client.post("/api/v1/applications", json={
        "application_id": "A001",
        "applicant_name": "Applicant A001",
        "loan_amount": 3500000.0
    })

    # Trigger prediction
    client.post("/api/v1/applications/A001/risk/predict")

    # Fetch Evidence Graph
    res = client.get("/api/v1/applications/A001/evidence")
    assert res.status_code == 200
    data = res.json()

    ml_nodes = [n for n in data["nodes"] if n["node_type"] == "ML_RISK_ASSESSMENT"]
    assert len(ml_nodes) > 0
    ml_node = ml_nodes[0]
    assert "ML Risk Assessment" in ml_node["title"]
    assert ml_node["source_type"] == "ML_MODEL"

    ml_rels = [r for r in data["relationships"] if r["relationship_type"] == "HAS_RISK_ASSESSMENT"]
    assert len(ml_rels) > 0
    assert ml_rels[0]["target_node_id"] == ml_node["node_id"]
