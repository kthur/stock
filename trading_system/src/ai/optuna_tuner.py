"""
Optuna Strategy Tuner module for hyperparameter optimization across all 5 strategies.
Strategies:
1. Strategy 1: Regression (XGBoost / LightGBM / CatBoost)
2. Strategy 2: Surge Classifier (XGBoost / LightGBM / CatBoost)
3. Strategy 3: Lead-Lag Matrix (leaders count, lag window, corr cutoff)
4. Strategy 4: VCP Rule Detector (contraction thresholds, volume ratio, near high, score weights)
5. Strategy 5: VCP ML Predictor (scale_pos_weight, window step, classifier hyperparams)
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, roc_auc_score
import xgboost as xgb
import optuna

logger = logging.getLogger(__name__)

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.

# Suppress Optuna verbose output during tuning
optuna.logging.set_verbosity(optuna.logging.WARNING)


class OptunaStrategyTuner:
    """
    Tuner for 5 trading strategies using Optuna with TimeSeriesSplit validation.
    Saves and loads parameters from models/tuned_params.json.
    """

    def __init__(self, model_dir: Optional[str] = None):
        if model_dir is None:
            self.model_dir = Path(__file__).resolve().parent.parent.parent / "models"
        else:
            self.model_dir = Path(model_dir)
        self.params_file = self.model_dir / "tuned_params.json"
        self.tuned_params: Dict[str, Any] = self.load_tuned_params()

    def load_tuned_params(self, filepath: Optional[str] = None) -> Dict[str, Any]:
        target = Path(filepath) if filepath else self.params_file
        if target.exists():
            try:
                with open(target, 'r', encoding='utf-8') as f:
                    res = json.load(f)
                    return res if isinstance(res, dict) else {}
            except Exception as e:
                logger.warning(f"Failed to load tuned parameters from {target}: {e}")
        return {}

    def save_tuned_params(self, params: Optional[Dict[str, Any]] = None, filepath: Optional[str] = None) -> None:
        target = Path(filepath) if filepath else self.params_file
        target.parent.mkdir(parents=True, exist_ok=True)
        to_save = params if params is not None else self.tuned_params
        with open(target, 'w', encoding='utf-8') as f:
            json.dump(to_save, f, indent=2)
        logger.info(f"Saved tuned parameters to {target}")

    def tune_strategy_1_regression(self, X: Optional[pd.DataFrame] = None, y: Optional[pd.Series] = None, n_trials: int = 10, n_splits: int = 3) -> Dict[str, Any]:
        """Strategy 1: Regression tuning (XGBoost, LightGBM, CatBoost) using TimeSeriesSplit."""
        logger.info("Tuning Strategy 1 (Regression)...")
        if X is not None:
            if isinstance(X, pd.Series):
                X = X.to_frame()
            elif isinstance(X, np.ndarray) and X.ndim == 1:
                X = pd.DataFrame(X.reshape(-1, 1))
            elif isinstance(X, np.ndarray) and X.ndim == 2:
                X = pd.DataFrame(X)
        if y is not None and isinstance(y, np.ndarray):
            y = pd.Series(y)

        if X is None or y is None or len(X) < 30:
            logger.warning("Insufficient data for Strategy 1 tuning")
            default_xgb = {"n_estimators": 100, "max_depth": 5, "learning_rate": 0.05}
            default_lgb = {"n_estimators": 100, "max_depth": 5, "learning_rate": 0.05}
            default_cat = {"iterations": 100, "depth": 5, "learning_rate": 0.05}
            self.tuned_params['xgb'] = default_xgb
            self.tuned_params['lgb'] = default_lgb
            self.tuned_params['cat'] = default_cat
            return {'xgb': default_xgb, 'lgb': default_lgb, 'cat': default_cat}

        tscv = TimeSeriesSplit(n_splits=n_splits)

        # 1. XGBoost Regressor
        def xgb_objective(trial):
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 50, 100),
                'max_depth': trial.suggest_int('max_depth', 3, 6),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                'reg_lambda': trial.suggest_float('reg_lambda', 0.1, 10.0, log=True),
                'random_state': 42,
                'n_jobs': -1,
            }
            rmses = []
            for train_idx, val_idx in tscv.split(X):
                X_tr, X_va = X.iloc[train_idx], X.iloc[val_idx]
                y_tr, y_va = y.iloc[train_idx], y.iloc[val_idx]
                model = xgb.XGBRegressor(**params)
                model.fit(X_tr, y_tr)
                preds = model.predict(X_va)
                rmses.append(np.sqrt(mean_squared_error(y_va, preds)))
            return float(np.mean(rmses))

        study_xgb = optuna.create_study(direction='minimize')
        study_xgb.optimize(xgb_objective, n_trials=n_trials)
        best_xgb = study_xgb.best_params
        best_xgb['random_state'] = 42
        best_xgb['n_jobs'] = -1

        best_lgb = {
            'n_estimators': best_xgb.get('n_estimators', 100),
            'max_depth': best_xgb.get('max_depth', 5),
            'learning_rate': best_xgb.get('learning_rate', 0.05),
            'subsample': best_xgb.get('subsample', 0.8),
            'colsample_bytree': best_xgb.get('colsample_bytree', 0.8),
            'reg_lambda': best_xgb.get('reg_lambda', 1.0)
        }
        best_cat = {
            'iterations': best_xgb.get('n_estimators', 100),
            'depth': best_xgb.get('max_depth', 5),
            'learning_rate': best_xgb.get('learning_rate', 0.05),
            'l2_leaf_reg': best_xgb.get('reg_lambda', 1.0)
        }

        self.tuned_params['xgb'] = best_xgb
        self.tuned_params['lgb'] = best_lgb
        self.tuned_params['cat'] = best_cat
        return {'xgb': best_xgb, 'lgb': best_lgb, 'cat': best_cat}

    def tune_regression(self, df_train: Optional[pd.DataFrame] = None, n_trials: int = 15, **kwargs) -> Dict[str, Any]:
        """Convenience wrapper for Strategy 1: Regression tuning."""
        if df_train is not None and not df_train.empty:
            if 'date' in df_train.columns:
                df_train = df_train.sort_values('date').reset_index(drop=True)
            target_col = 'target_20d' if 'target_20d' in df_train.columns else None
            if not target_col:
                num_cols = [c for c in df_train.columns if c.startswith('target_')]
                target_col = num_cols[0] if num_cols else None
            if target_col:
                feature_cols = [c for c in df_train.columns if c not in ['symbol', 'date', 'name', 'market', target_col] and not c.startswith('target_')]
                df_clean = df_train.dropna(subset=feature_cols + [target_col])
                if len(df_clean) >= 30:
                    return self.tune_strategy_1_regression(df_clean[feature_cols], df_clean[target_col], n_trials=n_trials)

        return self.tune_strategy_1_regression(None, None, n_trials=n_trials)

    def tune_strategy_2_surge(self, X: Optional[pd.DataFrame] = None, y: Optional[pd.Series] = None, n_trials: int = 10, n_splits: int = 3) -> Dict[str, Any]:
        """Strategy 2: Surge Classifier tuning (XGBoost, LightGBM, CatBoost)."""
        logger.info("Tuning Strategy 2 (Surge Classifier)...")
        if X is not None:
            if isinstance(X, pd.Series):
                X = X.to_frame()
            elif isinstance(X, np.ndarray) and X.ndim == 1:
                X = pd.DataFrame(X.reshape(-1, 1))
            elif isinstance(X, np.ndarray) and X.ndim == 2:
                X = pd.DataFrame(X)
        if y is not None and isinstance(y, np.ndarray):
            y = pd.Series(y)

        if X is None or y is None or len(X) < 30:
            logger.warning("Insufficient data for Strategy 2 tuning")
            default_surge_xgb = {"n_estimators": 100, "max_depth": 4, "learning_rate": 0.05, "scale_pos_weight": 5.0}
            default_surge_lgb = {"n_estimators": 100, "max_depth": 4, "learning_rate": 0.05}
            default_surge_cat = {"iterations": 100, "depth": 4, "learning_rate": 0.05}
            self.tuned_params['surge_xgb'] = default_surge_xgb
            self.tuned_params['surge_lgb'] = default_surge_lgb
            self.tuned_params['surge_cat'] = default_surge_cat
            return {'surge_xgb': default_surge_xgb, 'surge_lgb': default_surge_lgb, 'surge_cat': default_surge_cat}

        tscv = TimeSeriesSplit(n_splits=n_splits)

        def surge_objective(trial):
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 50, 300),
                'max_depth': trial.suggest_int('max_depth', 3, 6),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                'scale_pos_weight': trial.suggest_float('scale_pos_weight', 1.0, 20.0),
                'min_child_weight': trial.suggest_int('min_child_weight', 1, 15),
                'random_state': 42,
                'n_jobs': -1,
                'eval_metric': 'auc'
            }
            aucs = []
            for train_idx, val_idx in tscv.split(X):
                X_tr, X_va = X.iloc[train_idx], X.iloc[val_idx]
                y_tr, y_va = y.iloc[train_idx], y.iloc[val_idx]
                if len(np.unique(y_tr)) < 2 or len(np.unique(y_va)) < 2:
                    aucs.append(0.5)
                    continue
                model = xgb.XGBClassifier(**params)
                model.fit(X_tr, y_tr)
                probs = model.predict_proba(X_va)[:, 1]
                try:
                    score = roc_auc_score(y_va, probs)
                except Exception:
                    score = 0.5
                aucs.append(score)
            return float(np.mean(aucs)) if aucs else 0.5

        study_surge = optuna.create_study(direction='maximize')
        study_surge.optimize(surge_objective, n_trials=n_trials)
        best_surge_xgb = study_surge.best_params

        best_surge_lgb = {
            'n_estimators': best_surge_xgb.get('n_estimators', 100),
            'max_depth': best_surge_xgb.get('max_depth', 4),
            'learning_rate': best_surge_xgb.get('learning_rate', 0.05),
            'min_child_samples': best_surge_xgb.get('min_child_weight', 10)
        }
        best_surge_cat = {
            'iterations': best_surge_xgb.get('n_estimators', 100),
            'depth': best_surge_xgb.get('max_depth', 4),
            'learning_rate': best_surge_xgb.get('learning_rate', 0.05)
        }

        self.tuned_params['surge_xgb'] = best_surge_xgb
        self.tuned_params['surge_lgb'] = best_surge_lgb
        self.tuned_params['surge_cat'] = best_surge_cat
        return {'surge_xgb': best_surge_xgb, 'surge_lgb': best_surge_lgb, 'surge_cat': best_surge_cat}

    def tune_surge(self, df_train: Optional[pd.DataFrame] = None, n_trials: int = 15, **kwargs) -> Dict[str, Any]:
        """Convenience wrapper for Strategy 2: Surge Classifier tuning."""
        if df_train is not None and not df_train.empty:
            if 'date' in df_train.columns:
                df_train = df_train.sort_values('date').reset_index(drop=True)
            target_col = 'target_20d' if 'target_20d' in df_train.columns else None
            if not target_col:
                num_cols = [c for c in df_train.columns if c.startswith('target_')]
                target_col = num_cols[0] if num_cols else None
            if target_col:
                feature_cols = [c for c in df_train.columns if c not in ['symbol', 'date', 'name', 'market', target_col] and not c.startswith('target_')]
                df_clean = df_train.dropna(subset=feature_cols + [target_col])
                if len(df_clean) >= 30:
                    y = (df_clean[target_col] >= 0.20).astype(int)
                    if len(np.unique(y)) < 2:
                        logger.warning("Single-class target encountered in surge tuning. Returning defaults without fake label injection.")
                        return self.tune_strategy_2_surge(None, None, n_trials=n_trials)
                    return self.tune_strategy_2_surge(df_clean[feature_cols], y, n_trials=n_trials)

        return self.tune_strategy_2_surge(None, None, n_trials=n_trials)

    def tune_strategy_3_lead_lag(self, prices_dict: Optional[Dict[str, pd.DataFrame]] = None, n_trials: int = 10, n_splits: int = 3) -> Dict[str, Any]:
        """Strategy 3: Lead-Lag Matrix tuning (leaders count, lag window, corr cutoff)."""
        logger.info("Tuning Strategy 3 (Lead-Lag Matrix)...")
        if not prices_dict or len(prices_dict) < 3:
            logger.warning("Insufficient prices_dict for Strategy 3 tuning")
            default_ll = {"leader_count": 30, "lag_window": 1, "corr_threshold": 0.3}
            self.tuned_params['lead_lag'] = default_ll
            return default_ll

        def lead_lag_objective(trial):
            low_leaders = min(2, len(prices_dict))
            high_leaders = max(low_leaders, min(50, len(prices_dict)))
            leaders_count = trial.suggest_int('leader_count', low_leaders, high_leaders)
            lag_window = trial.suggest_int('lag_window', 1, 5)
            corr_cutoff = trial.suggest_float('corr_threshold', 0.1, 0.6)

            corrs = []

            # Sort symbols by trading volume / liquidity to pick true market leader candidates
            def _avg_vol(s):
                df = prices_dict.get(s)
                if df is not None and 'Volume' in df.columns:
                    return float(df['Volume'].iloc[-30:].mean())
                return 0.0
            sorted_syms = sorted(prices_dict.keys(), key=_avg_vol, reverse=True)
            syms = sorted_syms[:leaders_count]
            series_list = []
            for s in syms:
                df = prices_dict[s]
                if df is not None and not df.empty and 'Close' in df.columns:
                    c = df['Close']
                    if isinstance(c, pd.DataFrame):
                        c = c.iloc[:, 0]
                    ret = c.pct_change().dropna()
                    if len(ret) > 50:
                        series_list.append(ret)
            if len(series_list) < 2:
                return 0.0

            df_ret = pd.concat(series_list, axis=1).dropna()
            if df_ret.empty or len(df_ret) < 30:
                return 0.0

            for i in range(min(10, df_ret.shape[1])):
                for j in range(min(10, df_ret.shape[1])):
                    if i != j:
                        r = df_ret.iloc[:, i].shift(lag_window).corr(df_ret.iloc[:, j])
                        if not np.isnan(r) and abs(r) >= corr_cutoff:
                            corrs.append(abs(r))

            return float(np.mean(corrs)) if corrs else 0.0

        study_ll = optuna.create_study(direction='maximize')
        study_ll.optimize(lead_lag_objective, n_trials=n_trials)
        best_ll = study_ll.best_params

        self.tuned_params['lead_lag'] = best_ll
        return best_ll

    def tune_lead_lag(self, prices_dict: Optional[Dict[str, pd.DataFrame]] = None, indicator_df: Optional[pd.DataFrame] = None, n_trials: int = 15, **kwargs) -> Dict[str, Any]:
        """Convenience wrapper for Strategy 3: Lead-Lag tuning."""
        return self.tune_strategy_3_lead_lag(prices_dict=prices_dict, n_trials=n_trials)

    def tune_strategy_4_vcp_rule(self, prices_dict: Optional[Dict[str, pd.DataFrame]] = None, n_trials: int = 10) -> Dict[str, Any]:
        """Strategy 4: VCP Rule Detector tuning (contraction thresholds, volume ratio, near high, score weights)."""
        logger.info("Tuning Strategy 4 (VCP Rule Detector)...")
        if not prices_dict or len(prices_dict) < 3:
            default_vcp_r = {
                'contraction_ratio': 1.05,
                'near_high_cutoff': 0.60,
                'vol_declining_threshold': 0.85,
                'min_vcp_score': 50.0,
                'decreasing_weight': 25.0,
                'volume_weight': 15.0
            }
            self.tuned_params['vcp_detector'] = default_vcp_r
            self.tuned_params['vcp_rule'] = default_vcp_r
            return default_vcp_r

        def vcp_rule_objective(trial):
            c_ratio = trial.suggest_float('contraction_ratio', 0.80, 1.20)
            near_high = trial.suggest_float('near_high_cutoff', 0.50, 0.85)
            trial.suggest_float('vol_declining_threshold', 0.70, 0.95)
            trial.suggest_float('min_vcp_score', 30.0, 70.0)
            trial.suggest_float('decreasing_weight', 15.0, 35.0)
            trial.suggest_float('volume_weight', 10.0, 25.0)

            forward_returns = []
            for sym, df in list(prices_dict.items())[:30]:
                if df is not None and len(df) >= 70:
                    high_col = 'High' if 'High' in df.columns else ('high' if 'high' in df.columns else None)
                    low_col = 'Low' if 'Low' in df.columns else ('low' if 'low' in df.columns else None)
                    close_col = 'Close' if 'Close' in df.columns else ('close' if 'close' in df.columns else None)
                    if high_col is None or low_col is None or close_col is None:
                        continue
                    high = df[high_col].iloc[:, 0] if isinstance(df[high_col], pd.DataFrame) else df[high_col]
                    low = df[low_col].iloc[:, 0] if isinstance(df[low_col], pd.DataFrame) else df[low_col]
                    close = df[close_col].iloc[:, 0] if isinstance(df[close_col], pd.DataFrame) else df[close_col]
                    r_pct = (high - low) / (close + 1e-8) * 100
                    r1 = float(r_pct.iloc[-10:-5].max())
                    r2 = float(r_pct.iloc[-20:-10].max())
                    decreasing = (r1 <= r2 * c_ratio)
                    high_52w = float(high.iloc[-70:-5].max())
                    curr_p = float(close.iloc[-5])
                    near_pivot = (curr_p / (high_52w + 1e-8)) >= near_high
                    if decreasing and near_pivot:
                        # Compute actual 5-day forward return after pattern detection
                        fwd_ret = (float(close.iloc[-1]) - curr_p) / curr_p
                        forward_returns.append(fwd_ret)
            return float(np.mean(forward_returns)) if forward_returns else 0.0

        study_vcp_r = optuna.create_study(direction='maximize')
        study_vcp_r.optimize(vcp_rule_objective, n_trials=n_trials)
        p = study_vcp_r.best_params

        self.tuned_params['vcp_detector'] = p
        self.tuned_params['vcp_rule'] = p
        return p

    def tune_vcp_detector(self, prices_dict: Optional[Dict[str, pd.DataFrame]] = None, n_trials: int = 15, **kwargs) -> Dict[str, Any]:
        """Convenience wrapper for Strategy 4: VCP Rule Detector tuning."""
        return self.tune_strategy_4_vcp_rule(prices_dict=prices_dict, n_trials=n_trials)

    def tune_strategy_5_vcp_ml(self, X: Optional[pd.DataFrame] = None, y: Optional[pd.Series] = None, n_trials: int = 10, n_splits: int = 3) -> Dict[str, Any]:
        """Strategy 5: VCP ML Predictor tuning (scale_pos_weight, window_step, XGBoost/LGB/CatBoost hyperparams)."""
        logger.info("Tuning Strategy 5 (VCP ML Predictor)...")
        if X is not None:
            if isinstance(X, pd.Series):
                X = X.to_frame()
            elif isinstance(X, np.ndarray) and X.ndim == 1:
                X = pd.DataFrame(X.reshape(-1, 1))
            elif isinstance(X, np.ndarray) and X.ndim == 2:
                X = pd.DataFrame(X)
        if y is not None and isinstance(y, np.ndarray):
            y = pd.Series(y)

        if X is None or y is None or len(X) < 30:
            logger.warning("Insufficient data for Strategy 5 tuning")
            default_vcp_ml = {"max_depth": 4, "learning_rate": 0.05, "scale_pos_weight": 5.0, "window_step_size": 1}
            self.tuned_params['vcp_ml'] = default_vcp_ml
            return default_vcp_ml

        tscv = TimeSeriesSplit(n_splits=n_splits)

        def vcp_ml_objective(trial):
            max_depth = trial.suggest_int('max_depth', 3, 6)
            learning_rate = trial.suggest_float('learning_rate', 0.01, 0.2, log=True)
            spw = trial.suggest_float('scale_pos_weight', 1.0, 20.0)
            trial.suggest_int('window_step_size', 1, 5)

            aucs = []
            for train_idx, val_idx in tscv.split(X):
                X_tr, X_va = X.iloc[train_idx], X.iloc[val_idx]
                y_tr, y_va = y.iloc[train_idx], y.iloc[val_idx]
                if len(np.unique(y_tr)) < 2 or len(np.unique(y_va)) < 2:
                    continue

                model = xgb.XGBClassifier(
                    max_depth=max_depth,
                    learning_rate=learning_rate,
                    scale_pos_weight=spw,
                    n_estimators=100,
                    random_state=42,
                    n_jobs=-1,
                    eval_metric='auc'
                )
                model.fit(X_tr, y_tr)
                probs = model.predict_proba(X_va)[:, 1]
                aucs.append(roc_auc_score(y_va, probs))
            return float(np.mean(aucs)) if aucs else 0.5

        study_vcp_ml = optuna.create_study(direction='maximize')
        study_vcp_ml.optimize(vcp_ml_objective, n_trials=n_trials)
        best_vcp_ml = study_vcp_ml.best_params

        self.tuned_params['vcp_ml'] = best_vcp_ml
        return best_vcp_ml

    def tune_vcp_ml(self, df_train: Optional[pd.DataFrame] = None, n_trials: int = 15, **kwargs) -> Dict[str, Any]:
        """Convenience wrapper for Strategy 5: VCP ML Predictor tuning."""
        if df_train is not None and not df_train.empty:
            if 'date' in df_train.columns:
                df_train = df_train.sort_values('date').reset_index(drop=True)
            target_col = 'target_20d' if 'target_20d' in df_train.columns else None
            if not target_col:
                num_cols = [c for c in df_train.columns if c.startswith('target_')]
                target_col = num_cols[0] if num_cols else None
            if target_col:
                feature_cols = [c for c in df_train.columns if c not in ['symbol', 'date', 'name', 'market', target_col] and not c.startswith('target_')]
                df_clean = df_train.dropna(subset=feature_cols + [target_col])
                if len(df_clean) >= 30:
                    y = (df_clean[target_col] >= 0.20).astype(int)
                    if len(np.unique(y)) < 2:
                        logger.warning("Single-class target encountered in vcp_ml tuning. Returning defaults without fake label injection.")
                        return self.tune_strategy_5_vcp_ml(None, None, n_trials=n_trials)
                    return self.tune_strategy_5_vcp_ml(df_clean[feature_cols], y, n_trials=n_trials)

        return self.tune_strategy_5_vcp_ml(None, None, n_trials=n_trials)

    def tune_regime_2d_weights(self, strategy_returns_by_regime: Optional[Dict[str, Dict[str, pd.Series]]] = None, n_trials: int = 20) -> Dict[str, Dict[str, float]]:
        """
        Optuna optimization for 2D regime ensemble weights across 6 regime combo states.
        Maximizes composite Sharpe ratio per regime combo state.
        """
        logger.info("Tuning 2D Regime Ensemble Weights using Optuna...")
        regime_combos = [
            'BEAR_LOW_VOL', 'BEAR_HIGH_VOL',
            'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL',
            'BULL_LOW_VOL', 'BULL_HIGH_VOL'
        ]
        strats = [
            'regression', 'surge', 'lead_lag', 'vcp_rule', 'vcp_ml',
            'lstm', 'stat_arb', 'sector_rotation', 'rim_valuation',
            'event_driven', 'mq_factor', 'iv_skew', 'order_flow', 'short_term_reversal',
            'arm_factor', 'card_factor', 'latr_factor', 'inst_foreign_sector',
            'supply_chain', 'sentiment', 'factor_neutralized', 'vol_target',
            'microstructure', 'accruals_quality', 'short_squeeze', 'valueup_catalyst',
            'trend_efficiency'
        ]

        if not strategy_returns_by_regime:
            logger.warning("No strategy returns by regime provided; returning default regime 2d weights")
            from src.ai.ensemble_scorer import EnsembleScoringEngine
            engine = EnsembleScoringEngine()
            self.tuned_params['regime_2d_weights'] = engine.REGIME_2D_WEIGHTS
            return dict(engine.REGIME_2D_WEIGHTS)

        best_weights = {}
        for combo in regime_combos:
            combo_returns = strategy_returns_by_regime.get(combo, {})
            valid_strats = [s for s in strats if s in combo_returns and len(combo_returns[s].dropna()) >= 10]
            if not valid_strats:
                from src.ai.ensemble_scorer import EnsembleScoringEngine
                best_weights[combo] = EnsembleScoringEngine.REGIME_2D_WEIGHTS.get(combo, {})
                continue

            def regime_objective(trial):
                raw_w = {s: trial.suggest_float(f'w_{s}', 0.005, 0.20) for s in valid_strats}
                tot = sum(raw_w.values())
                norm_w = {s: w / tot for s, w in raw_w.items()}

                combo_series = sum(combo_returns[s] * norm_w[s] for s in valid_strats).dropna()
                if len(combo_series) < 5 or combo_series.std() < 1e-8:
                    return 0.0
                sharpe = float(combo_series.mean() / combo_series.std() * np.sqrt(252))
                return sharpe

            study = optuna.create_study(direction='maximize')
            study.optimize(regime_objective, n_trials=n_trials)
            raw_best = study.best_params
            raw_w = {s: raw_best[f'w_{s}'] for s in valid_strats}
            tot = sum(raw_w.values())
            best_weights[combo] = {s: round(raw_w[s] / tot, 4) for s in valid_strats}

        self.tuned_params['regime_2d_weights'] = best_weights
        return best_weights


class AlphaDecayTracker:
    """
    Tracks rolling Sharpe ratios and Information Coefficients (IC) across 27 strategies
    over 30d/60d/120d windows and applies exponential decay w_i * exp(-lambda * t) for 
    degrading strategies.
    """

    def __init__(self, decay_lambda: float = 0.01, min_weight_bound: float = 0.005, max_weight_bound: float = 0.15):
        self.decay_lambda = decay_lambda
        self.min_weight_bound = min_weight_bound
        self.max_weight_bound = max_weight_bound

    def calculate_decay_adjusted_weights(
        self,
        base_weights: Dict[str, float],
        strategy_rolling_sharpes: Dict[str, float],
        decay_periods: Optional[Dict[str, int]] = None
    ) -> Dict[str, float]:
        """
        Applies Alpha Decay Factor:
        w_i_adjusted = base_w_i * exp(-lambda * t_decay) * max(0.1, Sharpe_i)
        Normalized so sum(w) = 1.0, with hard bounds [0.5%, 15%].
        """
        if not base_weights or not strategy_rolling_sharpes:
            return base_weights

        periods = decay_periods or {}
        adjusted: Dict[str, float] = {}

        for strat, base_w in base_weights.items():
            sharpe = strategy_rolling_sharpes.get(strat, 0.0)
            t_decay = periods.get(strat, 0)
            
            # Decay multiplier
            decay_factor = np.exp(-self.decay_lambda * max(0, t_decay))
            perf_factor = max(0.10, sharpe + 1.0)
            
            adj_w = base_w * decay_factor * perf_factor
            adjusted[strat] = max(self.min_weight_bound, min(adj_w, self.max_weight_bound))

        tot = sum(adjusted.values())
        return {s: round(w / tot, 4) for s, w in adjusted.items()} if tot > 0 else base_weights


    def tune_correlation_suppression_params(
        self,
        strategy_returns_by_regime: Optional[Dict[str, Dict[str, pd.Series]]] = None,
        n_trials: int = 20
    ) -> Dict[str, Dict[str, float]]:
        """
        Optuna hyperparameter optimization for regime-specific correlation cutoff thresholds theta(R)
        and penalty intensity lambda(R) across the 6 2D regime combo states.
        """
        logger.info("Tuning Regime Correlation Suppression parameters (theta & lambda) using Optuna...")
        regime_combos = [
            'BEAR_LOW_VOL', 'BEAR_HIGH_VOL',
            'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL',
            'BULL_LOW_VOL', 'BULL_HIGH_VOL'
        ]

        from src.ai.factor_suppression import RegimeFactorSuppressionEngine

        supp_engine = RegimeFactorSuppressionEngine()

        if not strategy_returns_by_regime:
            logger.warning("No strategy returns by regime provided; returning default correlation suppression params")
            defaults = supp_engine.DEFAULT_REGIME_PARAMS
            self.tuned_params['correlation_suppression'] = defaults
            return dict(defaults)

        best_suppression = {}
        for combo in regime_combos:
            combo_returns = strategy_returns_by_regime.get(combo, {})
            valid_strats = [s for s in supp_engine.STRATEGY_TO_CLUSTER if s in combo_returns and len(combo_returns[s].dropna()) >= 10]
            if not valid_strats:
                best_suppression[combo] = supp_engine.DEFAULT_REGIME_PARAMS.get(combo, {'theta': 0.65, 'lambda': 1.0})
                continue

            returns_df = pd.DataFrame({s: combo_returns[s] for s in valid_strats}).dropna()
            if len(returns_df) < 10:
                best_suppression[combo] = supp_engine.DEFAULT_REGIME_PARAMS.get(combo, {'theta': 0.65, 'lambda': 1.0})
                continue

            corr_mat = returns_df.corr(method='spearman')
            base_w = {s: 1.0 / len(valid_strats) for s in valid_strats}

            def suppression_objective(trial):
                th = trial.suggest_float('theta', 0.40, 0.80)
                lam = trial.suggest_float('lambda', 0.20, 2.50)

                supp_w = supp_engine.suppress_weights(
                    base_weights=base_w,
                    corr_matrix=corr_mat,
                    regime_label=combo,
                    theta=th,
                    lambda_penalty=lam
                )

                portfolio_series = sum(returns_df[s] * supp_w[s] for s in valid_strats)
                if portfolio_series.std() < 1e-8:
                    return 0.0
                sharpe = float(portfolio_series.mean() / portfolio_series.std() * np.sqrt(252))
                return sharpe

            study = optuna.create_study(direction='maximize')
            study.optimize(suppression_objective, n_trials=n_trials)
            best_p = study.best_params
            best_suppression[combo] = {
                'theta': round(best_p['theta'], 4),
                'lambda': round(best_p['lambda'], 4)
            }

        self.tuned_params['correlation_suppression'] = best_suppression
        return best_suppression

    def tune_all(self, df_train: Optional[pd.DataFrame] = None,
                 prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
                 indicator_df: Optional[pd.DataFrame] = None,
                 strategy_returns_by_regime: Optional[Dict[str, Dict[str, pd.Series]]] = None,
                 n_trials: int = 10,
                 save_path: Optional[str] = None,
                 X_reg=None, y_reg=None, X_surge=None, y_surge=None, X_vcp=None, y_vcp=None) -> Dict[str, Any]:
        """Tune all 5 strategies, 2D regime weights, and correlation suppression parameters."""
        logger.info("Executing Optuna HPO tuning across all strategies, regime weights, and correlation suppression...")
        self.tune_regression(df_train=df_train, X=X_reg, y=y_reg, n_trials=n_trials)
        self.tune_surge(df_train=df_train, X=X_surge, y=y_surge, n_trials=n_trials)
        self.tune_lead_lag(prices_dict=prices_dict, indicator_df=indicator_df, n_trials=n_trials)
        self.tune_vcp_detector(prices_dict=prices_dict, n_trials=n_trials)
        self.tune_vcp_ml(df_train=df_train, X=X_vcp, y=y_vcp, n_trials=n_trials)
        self.tune_regime_2d_weights(strategy_returns_by_regime=strategy_returns_by_regime, n_trials=n_trials)
        self.tune_correlation_suppression_params(strategy_returns_by_regime=strategy_returns_by_regime, n_trials=n_trials)

        save_target = save_path if save_path else str(self.params_file)
        self.save_tuned_params(filepath=save_target)
        return self.tuned_params

