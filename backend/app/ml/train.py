import os
import json
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    brier_score_loss,
    confusion_matrix,
    classification_report
)

from app.core.config import settings
from app.core.logging import logger
from app.ml.features import add_engineered_features
from app.ml.preprocessing import build_preprocessing_pipeline, ALL_FEATURE_COLUMNS

from xgboost import XGBClassifier


def load_and_prepare_dataset(csv_path: str) -> Tuple[pd.DataFrame, pd.Series]:
    """Loads dataset, strips strings, and creates target vector."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found at '{csv_path}'.")

    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    # Strip string values in object columns
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype(str).str.strip()

    # Target definition: 1 = Rejected (historical rejection outcome), 0 = Approved
    y = (df["loan_status"] == "Rejected").astype(int)
    X = df[ALL_FEATURE_COLUMNS].copy()

    return X, y


def train_and_evaluate_models():
    """
    Offline training script:
    1. Loads loan_approval_dataset.csv
    2. Performs 80/20 stratified train/test split
    3. Runs Stratified 5-Fold CV on training set for LR, RF, XGB
    4. Evaluates all models on untouched 20% test set
    5. Selects champion model and saves joblib/json artifacts
    """
    csv_path = os.path.join(settings.DATA_DIR, "raw", "loan_approval_dataset.csv")
    artifacts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)

    logger.info("Loading dataset for ML Risk Analysis...")
    X, y = load_and_prepare_dataset(csv_path)
    logger.info(f"Dataset loaded: {len(X)} samples. Target distribution: {np.bincount(y)}")

    # Stratified 80/20 train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    logger.info(f"Train split: {len(X_train)} samples | Test split: {len(X_test)} samples")

    # Fit preprocessing pipeline on training data ONLY
    preprocessor = build_preprocessing_pipeline()
    X_train_trans = preprocessor.fit_transform(X_train)
    X_test_trans = preprocessor.transform(X_test)

    # Save preprocessing pipeline artifact
    pipeline_path = os.path.join(artifacts_dir, "pipeline.joblib")
    joblib.dump(preprocessor, pipeline_path)

    models: Dict[str, Any] = {
        "LogisticRegression": LogisticRegression(
            max_iter=1000, random_state=42, class_weight="balanced"
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=100, max_depth=10, random_state=42, class_weight="balanced"
        ),
        "XGBoost": XGBClassifier(
            n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, eval_metric="logloss"
        )
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scoring = ["accuracy", "precision", "recall", "f1", "roc_auc"]

    cv_results_summary = {}
    test_results_summary = {}
    fitted_models = {}

    for name, model in models.items():
        logger.info(f"Evaluating {name} with 5-Fold Cross Validation...")
        cv_scores = cross_validate(model, X_train_trans, y_train, cv=cv, scoring=scoring)

        cv_metrics = {
            "cv_accuracy_mean": float(np.mean(cv_scores["test_accuracy"])),
            "cv_accuracy_std": float(np.std(cv_scores["test_accuracy"])),
            "cv_precision_mean": float(np.mean(cv_scores["test_precision"])),
            "cv_precision_std": float(np.std(cv_scores["test_precision"])),
            "cv_recall_mean": float(np.mean(cv_scores["test_recall"])),
            "cv_recall_std": float(np.std(cv_scores["test_recall"])),
            "cv_f1_mean": float(np.mean(cv_scores["test_f1"])),
            "cv_f1_std": float(np.std(cv_scores["test_f1"])),
            "cv_roc_auc_mean": float(np.mean(cv_scores["test_roc_auc"])),
            "cv_roc_auc_std": float(np.std(cv_scores["test_roc_auc"]))
        }
        cv_results_summary[name] = cv_metrics

        # Fit model on entire X_train_trans
        model.fit(X_train_trans, y_train)
        fitted_models[name] = model

        # Save individual model joblib
        joblib.dump(model, os.path.join(artifacts_dir, f"{name.lower()}.joblib"))

        # Evaluate on untouched X_test_trans
        y_pred = model.predict(X_test_trans)
        y_proba = model.predict_proba(X_test_trans)[:, 1]

        cm = confusion_matrix(y_test, y_pred).tolist()
        clf_report = classification_report(y_test, y_pred, output_dict=True)

        test_metrics = {
            "test_accuracy": float(accuracy_score(y_test, y_pred)),
            "test_precision": float(precision_score(y_test, y_pred)),
            "test_recall": float(recall_score(y_test, y_pred)),
            "test_f1": float(f1_score(y_test, y_pred)),
            "test_roc_auc": float(roc_auc_score(y_test, y_proba)),
            "brier_score": float(brier_score_loss(y_test, y_proba)),
            "confusion_matrix": cm,
            "classification_report": clf_report
        }
        test_results_summary[name] = test_metrics

    # Select Champion Model (highest ROC-AUC and F1 on CV/Test)
    champion_name = max(
        models.keys(),
        key=lambda k: (cv_results_summary[k]["cv_roc_auc_mean"], test_results_summary[k]["test_roc_auc"])
    )
    champion_model = fitted_models[champion_name]

    logger.info(f"Champion model selected: '{champion_name}'")

    # Save champion model artifact
    joblib.dump(champion_model, os.path.join(artifacts_dir, "champion_model.joblib"))

    # Save comparison data
    comparison_data = {
        "champion_model_name": champion_name,
        "dataset": "data/raw/loan_approval_dataset.csv",
        "sample_count": len(X),
        "train_sample_count": len(X_train),
        "test_sample_count": len(X_test),
        "cross_validation": cv_results_summary,
        "test_evaluation": test_results_summary
    }

    comparison_path = os.path.join(artifacts_dir, "model_comparison.json")
    with open(comparison_path, "w") as f:
        json.dump(comparison_data, f, indent=2)

    # Save metadata for runtime predictor
    metadata = {
        "champion_model_name": champion_name,
        "model_version": "v1",
        "feature_version": "v1",
        "target_definition": "historical_rejection_outcome",
        "cv_roc_auc": cv_results_summary[champion_name]["cv_roc_auc_mean"],
        "test_roc_auc": test_results_summary[champion_name]["test_roc_auc"],
        "test_accuracy": test_results_summary[champion_name]["test_accuracy"],
        "test_f1": test_results_summary[champion_name]["test_f1"],
        "risk_thresholds": {
            "LOW": 0.35,
            "MEDIUM_UPPER": 0.65,
            "HIGH": 0.65
        },
        "feature_columns": ALL_FEATURE_COLUMNS,
        "generated_at": str(pd.Timestamp.now())
    }

    metadata_path = os.path.join(artifacts_dir, "model_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Model training and artifact generation complete. Champion: {champion_name}")
    return comparison_data


if __name__ == "__main__":
    train_and_evaluate_models()
