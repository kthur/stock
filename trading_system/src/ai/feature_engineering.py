import os
import joblib
import pandas as pd
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)

def get_scaler_path(model_dir: str, market: str, horizon: int) -> str:
    return os.path.join(model_dir, f"scaler_{market}_{horizon}d.joblib")

def fit_scaler(df: pd.DataFrame, features: list, model_dir: str, market: str, horizon: int) -> StandardScaler:
    scaler = StandardScaler()
    # Fill remaining NaNs with 0 before scaling to ensure safety
    X = df[features].fillna(0.0)
    scaler.fit(X)
    
    os.makedirs(model_dir, exist_ok=True)
    scaler_path = get_scaler_path(model_dir, market, horizon)
    joblib.dump(scaler, scaler_path)
    logger.info(f"Saved feature scaler for {market} {horizon}d to {scaler_path}")
    return scaler

def load_scaler(model_dir: str, market: str, horizon: int) -> StandardScaler:
    scaler_path = get_scaler_path(model_dir, market, horizon)
    if os.path.exists(scaler_path):
        return joblib.load(scaler_path)
    logger.warning(f"Scaler not found at {scaler_path}. Returning default StandardScaler.")
    return StandardScaler()

def apply_scaler(df: pd.DataFrame, features: list, scaler: StandardScaler) -> pd.DataFrame:
    if df.empty:
        return df
    df_copy = df.copy()
    X = df_copy[features].fillna(0.0)
    # Handle scaler not fitted yet
    try:
        scaled_values = scaler.transform(X)
        df_copy[features] = scaled_values
    except Exception as e:
        logger.warning(f"Failed to apply scaling: {e}. Using raw features.")
    return df_copy
