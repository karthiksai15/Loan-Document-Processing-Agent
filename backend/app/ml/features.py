import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

class FinancialFeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Scikit-learn compatible transformer that engineer financial features:
    - loan_to_income_ratio: loan_amount / income_annum
    - total_asset_value: sum of non-negative residential, commercial, luxury, and bank assets
    - loan_to_asset_ratio: loan_amount / total_asset_value
    """
    def __init__(self):
        pass

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        df = X.copy()
        
        # Clean column names if needed
        if isinstance(df, pd.DataFrame):
            df.columns = df.columns.str.strip()

        # Handle suspicious negative residential asset value by clipping to 0
        res_assets = np.maximum(0, df['residential_assets_value'])
        comm_assets = np.maximum(0, df['commercial_assets_value'])
        lux_assets = np.maximum(0, df['luxury_assets_value'])
        bank_assets = np.maximum(0, df['bank_asset_value'])

        income = np.maximum(1.0, df['income_annum'])
        loan_amt = np.maximum(0.0, df['loan_amount'])

        df['total_asset_value'] = res_assets + comm_assets + lux_assets + bank_assets
        total_assets = np.maximum(1.0, df['total_asset_value'])

        df['loan_to_income_ratio'] = np.round(loan_amt / income, 4)
        df['loan_to_asset_ratio'] = np.round(loan_amt / total_assets, 4)

        return df

def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Helper function to engineer financial features on a pandas DataFrame."""
    transformer = FinancialFeatureEngineer()
    return transformer.transform(df)
