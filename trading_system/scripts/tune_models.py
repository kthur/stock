import os
import sys
import logging
import json
import random
import pandas as pd
import numpy as np
import optuna
from typing import Optional
from pathlib import Path
from sklearn.metrics import mean_squared_error, roc_auc_score

# Add trading_system and src to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import TradingConfig
from src.persistence.database import StockPriceDB
from src.data_layer.indicator_storage import MarketIndicatorStorage
from src.ai.prediction_model import OnDevicePredictionModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_mock_tuning_data(model: OnDevicePredictionModel) -> pd.DataFrame:
    """Generate a mock training dataset for testing/fallback if DB is empty."""
    logger.info("Generating mock tuning dataset...")
    np.random.seed(42)
    n_samples = 300
    dates = pd.date_range(start="2023-01-01", periods=n_samples)
    data = {'date': dates, 'symbol': ['MOCK'] * n_samples}

    # Generate random features
    for col in model.ALL_FEATURES:
        data[col] = np.random.randn(n_samples)

    # Generate random targets
    for h in model.horizons:
        data[f'target_{h}d'] = np.random.randn(n_samples) * 0.05

    df = pd.DataFrame(data)
    return df

def load_tuning_data() -> pd.DataFrame:
    """Load a sample of the training dataset from local StockPriceDB."""
    cfg = TradingConfig()
    price_db = StockPriceDB(db_path=cfg.stock_price_db_path)
    storage = MarketIndicatorStorage(db_path=cfg.db_path)
    model = OnDevicePredictionModel()

    symbols = price_db.get_all_symbols()
    if not symbols:
        return create_mock_tuning_data(model)

    # Sample up to 10 symbols for fast tuning
    random.seed(42)
    sample_symbols = random.sample(symbols, min(len(symbols), 10))

    prices_dict = {}
    from run_pipeline import fetch_indicator_history
    indicator_train = fetch_indicator_history(cfg.train_start_date, price_db, -1)

    for sym in sample_symbols:
        df = price_db.get_prices(sym, start_date=cfg.train_start_date)
        if not df.empty and len(df) >= 70:
            try:
                merged = model.merge_fundamentals(sym, df, storage)
                if merged is not None:
                    prices_dict[sym] = merged
            except Exception as e:
                logger.debug(f"Failed to merge fundamentals for {sym}: {e}")

    if not prices_dict:
        return create_mock_tuning_data(model)

    df_train = model.prepare_training_data(prices_dict, indicator_train)
    if df_train.empty:
        return create_mock_tuning_data(model)

    return df_train

def tune_hyperparameters(n_trials: int = 3, output_dir: Optional[str] = None):
    """
    Search for optimal hyperparameters using Optuna for XGBoost, LightGBM, and CatBoost.
    Splits the dataset chronologically (80% train, 20% validation).
    Saves the best parameters to models/tuned_params.json.
    """
    logger.info("Loading tuning dataset...")
    df = load_tuning_data()

    # Chronological split (80% train, 20% validation)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by='date').reset_index(drop=True)
    split_idx = int(len(df) * 0.8)

    train_df = df.iloc[:split_idx]
    val_df = df.iloc[split_idx:]

    logger.info(f"Data split chronologically: train={len(train_df)} rows, validation={len(val_df)} rows")

    model_ft = OnDevicePredictionModel()
    features = model_ft.ALL_FEATURES

    # Filter features that exist in df
    features = [f for f in features if f in train_df.columns]

    # We will tune regression and classification (surge) parameters
    # Let's use the first horizon (e.g. 5d or 20d) for target tuning
    reg_target = 'target_5d' if 'target_5d' in train_df.columns else f'target_{model_ft.horizons[0]}d'
    surge_target = 'surge_target'

    # Prepare classification target (>= 20% return)
    train_df = train_df.copy()
    val_df = val_df.copy()

    # Drop NaN targets (마지막 N일 전방수익률은 미래 데이터가 없어 NaN)
    # 실제 훈련 경로(prediction_model)와 동일하게 타깃이 없는 행은 제거한다.
    n_drop_train = int(train_df[reg_target].isna().sum())
    n_drop_val = int(val_df[reg_target].isna().sum())
    train_df = train_df.dropna(subset=[reg_target])
    val_df = val_df.dropna(subset=[reg_target])
    if n_drop_train or n_drop_val:
        logger.info(f"Tuning data: dropped {n_drop_train} train / {n_drop_val} val rows with NaN target")

    train_df[surge_target] = (train_df[reg_target] >= 0.20).astype(int)
    val_df[surge_target] = (val_df[reg_target] >= 0.20).astype(int)

    X_train, y_train_reg = train_df[features], train_df[reg_target]
    X_val, y_val_reg = val_df[features], val_df[reg_target]

    y_train_clf, y_val_clf = train_df[surge_target], val_df[surge_target]

    # Check if we have positive classes in clf targets. If not, mock them so classification tuning doesn't fail.
    if y_train_clf.sum() == 0:
        y_train_clf = pd.Series([0] * (len(y_train_clf) - 2) + [1, 1], index=y_train_clf.index)
    if y_val_clf.sum() == 0:
        y_val_clf = pd.Series([0] * (len(y_val_clf) - 2) + [1, 1], index=y_val_clf.index)

    best_params = {}

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    # 1. XGBoost Regressor
    logger.info("Tuning XGBoost Regressor...")
    def objective_xgb_reg(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 50, 200),
            'max_depth': trial.suggest_int('max_depth', 3, 6),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.15),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'reg_lambda': trial.suggest_float('reg_lambda', 0.1, 5.0),
            'random_state': 42,
            'n_jobs': -1
        }
        import xgboost as xgb
        reg = xgb.XGBRegressor(**params)
        reg.fit(X_train, y_train_reg)
        preds = reg.predict(X_val)
        return mean_squared_error(y_val_reg, preds)

    study_xgb_reg = optuna.create_study(direction='minimize')
    study_xgb_reg.optimize(objective_xgb_reg, n_trials=n_trials)
    best_params['xgb'] = study_xgb_reg.best_params

    # 2. LightGBM Regressor
    logger.info("Tuning LightGBM Regressor...")
    def objective_lgb_reg(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 50, 200),
            'max_depth': trial.suggest_int('max_depth', 3, 6),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.15),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'reg_lambda': trial.suggest_float('reg_lambda', 0.1, 5.0),
            'random_state': 42,
            'verbose': -1,
            'n_jobs': -1
        }
        import lightgbm as lgb
        reg = lgb.LGBMRegressor(**params)
        reg.fit(X_train, y_train_reg)
        preds = reg.predict(X_val)
        return mean_squared_error(y_val_reg, preds)

    study_lgb_reg = optuna.create_study(direction='minimize')
    study_lgb_reg.optimize(objective_lgb_reg, n_trials=n_trials)
    best_params['lgb'] = study_lgb_reg.best_params

    # 3. CatBoost Regressor
    logger.info("Tuning CatBoost Regressor...")
    def objective_cat_reg(trial):
        params = {
            'iterations': trial.suggest_int('iterations', 50, 150),
            'depth': trial.suggest_int('depth', 3, 6),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.15),
            'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 0.1, 5.0),
            'random_seed': 42,
            'verbose': False,
            'thread_count': -1
        }
        import catboost as cb
        reg = cb.CatBoostRegressor(**params)
        reg.fit(X_train, y_train_reg, verbose=False)
        preds = reg.predict(X_val)
        return mean_squared_error(y_val_reg, preds)

    study_cat_reg = optuna.create_study(direction='minimize')
    study_cat_reg.optimize(objective_cat_reg, n_trials=n_trials)
    best_params['cat'] = study_cat_reg.best_params

    # 4. XGBoost Classifier (Surge)
    logger.info("Tuning XGBoost Surge Classifier...")
    def objective_xgb_clf(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 50, 200),
            'max_depth': trial.suggest_int('max_depth', 3, 6),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.15),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'reg_lambda': trial.suggest_float('reg_lambda', 0.1, 5.0),
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
            'random_state': 42,
            'n_jobs': -1,
            'eval_metric': 'auc'
        }
        import xgboost as xgb
        clf = xgb.XGBClassifier(**params)
        clf.fit(X_train, y_train_clf)
        probs = clf.predict_proba(X_val)[:, 1]
        try:
            return roc_auc_score(y_val_clf, probs)
        except Exception:
            return 0.5

    study_xgb_clf = optuna.create_study(direction='maximize')
    study_xgb_clf.optimize(objective_xgb_clf, n_trials=n_trials)
    best_params['surge_xgb'] = study_xgb_clf.best_params

    # 5. LightGBM Classifier (Surge)
    logger.info("Tuning LightGBM Surge Classifier...")
    def objective_lgb_clf(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 50, 200),
            'max_depth': trial.suggest_int('max_depth', 3, 6),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.15),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'reg_lambda': trial.suggest_float('reg_lambda', 0.1, 5.0),
            'min_child_samples': trial.suggest_int('min_child_samples', 5, 20),
            'random_state': 42,
            'verbose': -1,
            'n_jobs': -1
        }
        import lightgbm as lgb
        clf = lgb.LGBMClassifier(**params)
        clf.fit(X_train, y_train_clf)
        probs = clf.predict_proba(X_val)[:, 1]
        try:
            return roc_auc_score(y_val_clf, probs)
        except Exception:
            return 0.5

    study_lgb_clf = optuna.create_study(direction='maximize')
    study_lgb_clf.optimize(objective_lgb_clf, n_trials=n_trials)
    best_params['surge_lgb'] = study_lgb_clf.best_params

    # 6. CatBoost Classifier (Surge)
    logger.info("Tuning CatBoost Surge Classifier...")
    def objective_cat_clf(trial):
        params = {
            'iterations': trial.suggest_int('iterations', 50, 150),
            'depth': trial.suggest_int('depth', 3, 6),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.15),
            'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 0.1, 5.0),
            'random_seed': 42,
            'verbose': False,
            'thread_count': -1
        }
        import catboost as cb
        clf = cb.CatBoostClassifier(**params)
        clf.fit(X_train, y_train_clf, verbose=False)
        probs = clf.predict_proba(X_val)[:, 1]
        try:
            return roc_auc_score(y_val_clf, probs)
        except Exception:
            return 0.5

    study_cat_clf = optuna.create_study(direction='maximize')
    study_cat_clf.optimize(objective_cat_clf, n_trials=n_trials)
    best_params['surge_cat'] = study_cat_clf.best_params

    # Save to tuned_params.json
    model_dir = Path(output_dir) if output_dir else Path(__file__).resolve().parent.parent / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    output_path = model_dir / "tuned_params.json"

    with open(output_path, 'w') as f:
        json.dump(best_params, f, indent=2)

    logger.info(f"Saved tuned hyperparameters to {output_path}")
    return best_params

if __name__ == "__main__":
    tune_hyperparameters(n_trials=5)
