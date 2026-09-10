import os
import json
import joblib
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.core.logging import logger
from app.ml.schemas import ApplicationRiskResponse
from app.ml.preprocessing import ALL_FEATURE_COLUMNS

class RiskPredictor:
    """Inference service for ML Loan Rejection Risk prediction."""
    _instance = None

    def __init__(self):
        self.artifacts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")
        self.pipeline = None
        self.champion_model = None
        self.metadata = None
        self.is_loaded = False
        self._load_artifacts()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = RiskPredictor()
        return cls._instance

    def _load_artifacts(self):
        pipeline_path = os.path.join(self.artifacts_dir, "pipeline.joblib")
        model_path = os.path.join(self.artifacts_dir, "champion_model.joblib")
        metadata_path = os.path.join(self.artifacts_dir, "model_metadata.json")

        if os.path.exists(pipeline_path) and os.path.exists(model_path) and os.path.exists(metadata_path):
            try:
                self.pipeline = joblib.load(pipeline_path)
                self.champion_model = joblib.load(model_path)
                with open(metadata_path, "r") as f:
                    self.metadata = json.load(f)
                self.is_loaded = True
                logger.info(f"Loaded ML Champion Model '{self.metadata.get('champion_model_name')}' successfully.")
            except Exception as e:
                logger.error(f"Failed to load ML artifacts: {e}")
                self.is_loaded = False
        else:
            logger.warning("ML artifacts not found. Inference will return UNAVAILABLE until models are trained.")
            self.is_loaded = False

    def predict(self, application_id: str, input_features: Dict[str, Any]) -> ApplicationRiskResponse:
        """Runs risk prediction for an application feature dictionary."""
        if not self.is_loaded:
            self._load_artifacts()

        if not self.is_loaded:
            return ApplicationRiskResponse(
                application_id=application_id,
                model_name="UNAVAILABLE",
                status="UNAVAILABLE",
                reason="ML model artifacts not trained or unavailable.",
                generated_at=datetime.utcnow()
            )

        # Missing features check
        missing = [f for f in ALL_FEATURE_COLUMNS if f not in input_features or input_features[f] is None]
        if missing:
            return ApplicationRiskResponse(
                application_id=application_id,
                model_name=self.metadata.get("champion_model_name", "Unknown"),
                model_version=self.metadata.get("model_version", "v1"),
                status="UNAVAILABLE",
                missing_features=missing,
                reason=f"Required ML feature(s) missing: {', '.join(missing)}",
                generated_at=datetime.utcnow()
            )

        try:
            # Construct DataFrame for single sample
            sample_df = pd.DataFrame([{col: input_features[col] for col in ALL_FEATURE_COLUMNS}])
            X_trans = self.pipeline.transform(sample_df)

            proba = float(self.champion_model.predict_proba(X_trans)[0, 1])
            pred_label = int(proba >= 0.5)

            # Determine risk level from prototype thresholds
            if proba < 0.35:
                risk_level = "LOW"
            elif proba <= 0.65:
                risk_level = "MEDIUM"
            else:
                risk_level = "HIGH"

            return ApplicationRiskResponse(
                application_id=application_id,
                model_name=self.metadata.get("champion_model_name", "Unknown"),
                model_version=self.metadata.get("model_version", "v1"),
                rejection_probability=round(proba, 4),
                risk_level=risk_level,
                prediction=pred_label,
                target_definition=self.metadata.get("target_definition", "historical_rejection_outcome"),
                feature_version=self.metadata.get("feature_version", "v1"),
                status="COMPLETED",
                generated_at=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"Inference error for application '{application_id}': {e}")
            return ApplicationRiskResponse(
                application_id=application_id,
                model_name=self.metadata.get("champion_model_name", "Unknown"),
                status="UNAVAILABLE",
                reason=f"Inference error: {str(e)}",
                generated_at=datetime.utcnow()
            )


def predict_application_risk(application_id: str, input_features: Dict[str, Any]) -> ApplicationRiskResponse:
    """Helper function to execute ML risk prediction."""
    predictor = RiskPredictor.get_instance()
    return predictor.predict(application_id, input_features)
