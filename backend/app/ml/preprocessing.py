from typing import List, Tuple
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from app.ml.features import FinancialFeatureEngineer

CATEGORICAL_FEATURES = ["education", "self_employed"]

NUMERICAL_FEATURES = [
    "no_of_dependents",
    "income_annum",
    "loan_amount",
    "loan_term",
    "cibil_score",
    "residential_assets_value",
    "commercial_assets_value",
    "luxury_assets_value",
    "bank_asset_value",
    "total_asset_value",
    "loan_to_income_ratio",
    "loan_to_asset_ratio"
]

ALL_FEATURE_COLUMNS = [
    "no_of_dependents",
    "education",
    "self_employed",
    "income_annum",
    "loan_amount",
    "loan_term",
    "cibil_score",
    "residential_assets_value",
    "commercial_assets_value",
    "luxury_assets_value",
    "bank_asset_value"
]

def build_preprocessing_pipeline() -> Pipeline:
    """
    Creates a scikit-learn Pipeline containing:
    1. FinancialFeatureEngineer (adds engineered features & handles negative asset values)
    2. ColumnTransformer (StandardScaler for numerical features, OneHotEncoder for categorical features)
    """
    column_transformer = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERICAL_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES)
        ],
        remainder="drop"
    )

    pipeline = Pipeline([
        ("feature_engineer", FinancialFeatureEngineer()),
        ("preprocessor", column_transformer)
    ])

    return pipeline
