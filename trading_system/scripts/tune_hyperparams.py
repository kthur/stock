import os
import sys
import logging
import json
import optuna
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any

# Add the parent directory of this script's directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import TradingConfig
from src.ai.prediction_model import OnDevicePredictionModel
from src.persistence.database import StockPriceDB
from src.data_layer.indicator_storage import MarketIndicatorStorage

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_data_for_tuning():
    cfg = TradingConfig()
    price_db = StockPriceDB(db_path=cfg.stock_price_db_path)
    storage = MarketIndicatorStorage(db_path=cfg.db_path)
    universe = storage.get_universe()

    if universe.empty:
        logger.error("Universe is empty. Cannot tune.")
        return pd.DataFrame(), pd.DataFrame()

    logger.info("Loading a sample of symbols for hyperparameter tuning...")
    # Sample 10 symbols from SP500 and 10 symbols from KRX to keep tuning fast
    sp500_symbols = universe[universe['market'] == 'SP500']['symbol'].tolist()
    krx_symbols = universe[universe['market'] != 'SP500']['symbol'].tolist()

    import random
    random.seed(42)
    sample_symbols = random.sample(sp500_symbols, min(10, len(sp500_symbols))) + \
                     random.sample(krx_symbols, min(10, len(krx_symbols)))

    model = OnDevicePredictionModel()

    # Fetch recent indicators
    from datetime import datetime, timedelta
    start_date = (datetime.now() - timedelta(days=500)).strftime('%Y-%m-%d')
    indicator_df = yf_indicator_fetch(start_date)

    prices_dict = {}
    for sym in sample_symbols:
        df = price_db.get_prices(sym, start_date=start_date)
        if not df.empty and len(df) >= 200:
            prices_dict[sym] = df

    if not prices_dict:
        logger.error("No valid prices loaded. Tuning aborted.")
        return pd.DataFrame(), pd.DataFrame()

    # Merge fundamentals
    for sym in list(prices_dict.keys()):
        try:
            prices_dict[sym] = model.merge_fundamentals(sym, prices_dict[sym], storage)
        except Exception:
            pass

    df_train = model.prepare_training_data(prices_dict, indicator_df)
    return df_train, universe

def yf_indicator_fetch(start_date: str) -> pd.DataFrame:
    # Minimal yfinance fetch for global indicators
    import yfinance as yf
    tickers = {'^VIX': 'vix_change', '^GSPC': 'sp500_change'}
    combined = {}
    for tk, col in tickers.items():
        try:
            df = yf.download(tk, start=start_date, progress=False, auto_adjust=True)
            if df is not None and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)
                combined[col] = df['Close'].pct_change().fillna(0.0) * 100
        except Exception:
            pass
    if not combined:
        return pd.DataFrame()
    res = pd.concat(combined, axis=1)
    res.index = pd.to_datetime(res.index)
    return res.sort_index()

def tune_regression(df_train: pd.DataFrame, trials: int = 15) -> Dict[str, Any]:
    if df_train.empty:
        return {}

    logger.info("Tuning regression hyperparameters...")
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import mean_squared_error
    import xgboost as xgb

    features = OnDevicePredictionModel.ALL_FEATURES
    # Target 20d horizon for optimization
    target_col = 'target_20d'
    if target_col not in df_train.columns:
        return {}

    df_clean = df_train.dropna(subset=features + [target_col])
    X = df_clean[features].values
    y = df_clean[target_col].values

    if len(X) < 100:
        logger.warning("Insufficient data for tuning regression.")
        return {}

    tscv = TimeSeriesSplit(n_splits=3)

    def objective(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 100, 400),
            'max_depth': trial.suggest_int('max_depth', 3, 6),
            'learning_rate': trial.suggest_float('learning_rate', 0.02, 0.12),
            'subsample': trial.suggest_float('subsample', 0.6, 0.9),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 0.9),
            'reg_lambda': trial.suggest_float('reg_lambda', 0.1, 5.0),
            'n_jobs': -1,
            'random_state': 42
        }

        scores = []
        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]

            model = xgb.XGBRegressor(**params)
            model.fit(X_train, y_train)
            preds = model.predict(X_val)
            scores.append(mean_squared_error(y_val, preds))

        return np.mean(scores)

    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=trials)
    logger.info(f"Best regression parameters: {study.best_params}")
    return study.best_params

def tune_surge(df_train: pd.DataFrame, trials: int = 15) -> Dict[str, Any]:
    if df_train.empty:
        return {}

    logger.info("Tuning surge classification hyperparameters...")
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import roc_auc_score
    import xgboost as xgb

    features = OnDevicePredictionModel.ALL_FEATURES
    target_col = 'target_20d'  # 20d surge horizon
    if target_col not in df_train.columns:
        return {}

    df_clean = df_train.dropna(subset=features + [target_col])
    X = df_clean[features].values
    y = (df_clean[target_col] >= 0.20).astype(int).values

    if len(X) < 100 or y.sum() == 0:
        logger.warning("Insufficient surge samples or data for tuning.")
        return {}

    tscv = TimeSeriesSplit(n_splits=3)

    def objective(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 100, 400),
            'max_depth': trial.suggest_int('max_depth', 3, 6),
            'learning_rate': trial.suggest_float('learning_rate', 0.02, 0.12),
            'subsample': trial.suggest_float('subsample', 0.6, 0.9),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 0.9),
            'reg_lambda': trial.suggest_float('reg_lambda', 0.1, 5.0),
            'min_child_weight': trial.suggest_int('min_child_weight', 5, 20),
            'n_jobs': -1,
            'random_state': 42
        }

        scores = []
        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]

            if y_train.sum() == 0 or y_val.sum() == 0:
                return 0.5  # invalid split

            model = xgb.XGBClassifier(**params)
            model.fit(X_train, y_train)
            probs = model.predict_proba(X_val)[:, 1]
            try:
                scores.append(roc_auc_score(y_val, probs))
            except ValueError:
                scores.append(0.5)

        return np.mean(scores)

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=trials)
    logger.info(f"Best surge classification parameters: {study.best_params}")
    return study.best_params

def main():
    df_train, universe = load_data_for_tuning()
    if df_train.empty:
        logger.error("No training data generated. Cannot proceed with tuning.")
        return

    best_xgb_reg = tune_regression(df_train, trials=15)
    best_xgb_surge = tune_surge(df_train, trials=15)

    tuned_data = {}
    if best_xgb_reg:
        # Standardize for regressor params
        tuned_data['xgb'] = best_xgb_reg
        # Match parameters for LightGBM and CatBoost approximately for scaling
        tuned_data['lgb'] = {
            'n_estimators': best_xgb_reg.get('n_estimators', 200),
            'max_depth': best_xgb_reg.get('max_depth', 5),
            'learning_rate': best_xgb_reg.get('learning_rate', 0.05),
            'subsample': best_xgb_reg.get('subsample', 0.8),
            'colsample_bytree': best_xgb_reg.get('colsample_bytree', 0.8),
            'reg_lambda': best_xgb_reg.get('reg_lambda', 1.0)
        }
        tuned_data['cat'] = {
            'iterations': best_xgb_reg.get('n_estimators', 200),
            'depth': best_xgb_reg.get('max_depth', 5),
            'learning_rate': best_xgb_reg.get('learning_rate', 0.05),
            'l2_leaf_reg': best_xgb_reg.get('reg_lambda', 1.0)
        }

    if best_xgb_surge:
        tuned_data['surge_xgb'] = best_xgb_surge
        tuned_data['surge_lgb'] = {
            'n_estimators': best_xgb_surge.get('n_estimators', 200),
            'max_depth': best_xgb_surge.get('max_depth', 4),
            'learning_rate': best_xgb_surge.get('learning_rate', 0.05),
            'subsample': best_xgb_surge.get('subsample', 0.8),
            'colsample_bytree': best_xgb_surge.get('colsample_bytree', 0.8),
            'reg_lambda': best_xgb_surge.get('reg_lambda', 1.0),
            'min_child_samples': best_xgb_surge.get('min_child_weight', 10)
        }
        tuned_data['surge_cat'] = {
            'iterations': best_xgb_surge.get('n_estimators', 200),
            'depth': best_xgb_surge.get('max_depth', 4),
            'learning_rate': best_xgb_surge.get('learning_rate', 0.05),
            'l2_leaf_reg': best_xgb_surge.get('reg_lambda', 1.0)
        }

    if tuned_data:
        models_dir = Path(__file__).resolve().parent.parent / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        tuned_path = models_dir / "tuned_params.json"

        with open(tuned_path, 'w') as f:
            json.dump(tuned_data, f, indent=2)
        logger.info(f"Successfully saved tuned parameters to {tuned_path}")

if __name__ == "__main__":
    main()
