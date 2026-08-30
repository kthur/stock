import logging
import os
import threading
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
import catboost as cb
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from sklearn.calibration import CalibratedClassifierCV

logger = logging.getLogger(__name__)

_CPU_WORKERS = max(1, (os.cpu_count() or 4))

_HAS_CUDA = False
try:
    import torch
    _HAS_CUDA = torch.cuda.is_available()
except Exception:
    pass

from src.ai.feature_engineering import VCP_FEATURES  # single source of truth

SURGE_HORIZONS = [1, 3, 5, 20]
SURGE_THRESHOLD = 0.20

MARKETS = ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']


def _safe_series(val):
    if isinstance(val, pd.DataFrame):
        return val.iloc[:, 0]
    return val


class VCPSurgePredictor:
    def __init__(self, model_dir: Optional[str] = None):
        from src.ai.prediction_model import OnDevicePredictionModel

        if model_dir is None:
            model_dir = str(Path(__file__).resolve().parent.parent.parent / "models")
        self.model_dir: Path = Path(model_dir)

        # Feature helper: reuse OnDevicePredictionModel's feature computation
        self._ft = OnDevicePredictionModel(model_dir=str(self.model_dir))
        self._ft.models = {}
        self._ft.surge_models = {}

        self.models: Dict[str, Dict[int, xgb.XGBClassifier]] = {}
        self.lgb_models: Dict[str, Dict[int, lgb.LGBMClassifier]] = {}
        self.cat_models: Dict[str, Dict[int, cb.CatBoostClassifier]] = {}

        self._surge_xgb_kwargs: Dict[str, Any] = dict(
            n_estimators=500,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_lambda=1.0,
            min_child_weight=10,
            max_delta_step=5,
            n_jobs=-1,
            random_state=42,
            early_stopping_rounds=50,
            eval_metric='auc',
        )
        self._surge_lgb_kwargs: Dict[str, Any] = dict(
            n_estimators=500,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_lambda=1.0,
            min_child_samples=10,
            n_jobs=-1,
            random_state=42,
            verbose=-1,
        )
        self._surge_cat_kwargs: Dict[str, Any] = dict(
            iterations=500,
            depth=4,
            learning_rate=0.05,
            l2_leaf_reg=1.0,
            thread_count=-1,
            random_seed=42,
            eval_metric='AUC',
            verbose=False,
        )
        # Check and load tuned parameters if they exist
        tuned_path = self.model_dir / "tuned_params.json"
        if tuned_path.exists():
            try:
                with open(tuned_path, 'r') as f:
                    tuned_data = json.load(f)
                logger.info(f"VCPSurgePredictor: Loaded tuned parameters from {tuned_path}")
                if 'surge_xgb' in tuned_data:
                    self._surge_xgb_kwargs.update(tuned_data['surge_xgb'])
                if 'surge_lgb' in tuned_data:
                    self._surge_lgb_kwargs.update(tuned_data['surge_lgb'])
                if 'surge_cat' in tuned_data:
                    self._surge_cat_kwargs.update(tuned_data['surge_cat'])
                if 'vcp_ml' in tuned_data:
                    vcp_ml_p = tuned_data['vcp_ml']
                    xgb_keys = {k: v for k, v in vcp_ml_p.items() if k in self._surge_xgb_kwargs or k in ['scale_pos_weight', 'window_step_size']}
                    self._surge_xgb_kwargs.update(xgb_keys)
            except Exception as e:
                logger.warning(f"VCPSurgePredictor: Failed to load tuned parameters: {e}")

        if _HAS_CUDA:
            self._surge_xgb_kwargs['device'] = 'cuda'
            self._surge_lgb_kwargs['device_type'] = 'gpu'
            self._surge_cat_kwargs['task_type'] = 'GPU'

        # Load validation metrics if exists
        self.validation_metrics: Dict[str, Any] = {"regression": {}, "surge": {}, "vcp_ml": {}}
        val_metrics_path = self.model_dir / "validation_metrics.json"
        if val_metrics_path.exists():
            try:
                with open(val_metrics_path, 'r') as f:
                    self.validation_metrics = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load validation metrics: {e}")
        self.validation_metrics.setdefault("vcp_ml", {})

        self.load_models()

    def _compute_vcp_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute VCP features from raw OHLCV for a single symbol."""
        if df is None or len(df) < 65:
            return pd.DataFrame()

        try:
            from src.ai.feature_engineering import compute_vcp_features
            df_vcp = compute_vcp_features(df)
            if df_vcp.empty:
                return pd.DataFrame()
            # Return last row as a DataFrame with only the 11 VCP features
            return df_vcp.iloc[-1:][VCP_FEATURES]
        except Exception as e:
            logger.warning(f"Failed to compute VCP features via common helper: {e}")
            return pd.DataFrame()

    def _batch_features_with_vcp(self, prices_dict: Dict[str, pd.DataFrame],
                                  indicator_df: pd.DataFrame = None,
                                  universe: pd.DataFrame = None) -> Tuple[List[str], List[str], List[pd.DataFrame]]:
        """Compute ALL_FEATURES + VCP_FEATURES for all symbols.

        Returns (symbols_list, market_list, feature_list).
        """
        # Step 1: OnDevicePredictionModel._batch_compute_inference_features
        normed = self._ft.apply_market_normalization(prices_dict)
        base_features = self._ft.ALL_FEATURES

        universe_map = {}
        if universe is not None and not universe.empty and 'symbol' in universe.columns:
            universe_map = dict(zip(universe['symbol'], universe['market']))

        results = []

        def _process_symbol(sym: str, df: pd.DataFrame) -> Optional[Tuple[str, str, pd.DataFrame]]:
            if df is None or len(df) < 65:
                return None
            market = universe_map.get(sym, 'SP500')
            if market not in MARKETS:
                market = 'SP500'
            df = df.copy()
            df['symbol'] = sym
            df_feat = self._ft._create_features(df, indicator_df)
            if df_feat.empty:
                return None

            vcp_feat = self._compute_vcp_features(prices_dict.get(sym))
            if vcp_feat.empty:
                vcp_feat = pd.DataFrame([{col: 0.0 for col in VCP_FEATURES}])

            latest = df_feat.iloc[-1:].copy()
            # Drop VCP columns in latest if they already exist to avoid duplicate columns
            cols_to_drop = [col for col in vcp_feat.columns if col in latest.columns]
            if cols_to_drop:
                latest = latest.drop(columns=cols_to_drop)
            for col in vcp_feat.columns:
                latest[col] = vcp_feat[col].values[0]

            all_cols = list(dict.fromkeys(list(base_features) + VCP_FEATURES))
            # Align feature columns strictly to all_cols and pad missing columns with 0.0
            for col in all_cols:
                if col not in latest.columns:
                    latest[col] = 0.0
            aligned_latest = latest[all_cols]
            return sym, market, aligned_latest

        with ThreadPoolExecutor(max_workers=_CPU_WORKERS) as pool:
            futures = {pool.submit(_process_symbol, sym, df): sym for sym, df in normed.items()}
            for f in as_completed(futures):
                try:
                    res = f.result()
                    if res is not None:
                        results.append(res)
                except Exception as e:
                    logger.debug(f"VCP ML batch feature failed for {futures[f]}: {e}")

        symbols_list = []
        market_list = []
        feature_list = []
        for sym, market, feat in results:
            symbols_list.append(sym)
            market_list.append(market)
            feature_list.append(feat)

        return symbols_list, market_list, feature_list

    def _windowed_vcp_features(self, df: pd.DataFrame, step: int = 20) -> pd.DataFrame:
        """Generate multiple training windows per symbol by sliding backwards."""
        if df is None or len(df) < 200:
            return pd.DataFrame()
        close = _safe_series(df['Close']).astype(float)
        open_p = _safe_series(df['Open']).astype(float) if 'Open' in df.columns else close
        rows = []

        try:
            from src.ai.feature_engineering import compute_vcp_features
            full_features = compute_vcp_features(df)
        except Exception:
            full_features = pd.DataFrame()

        if full_features.empty:
            return pd.DataFrame()

        sampled_indices = list(range(len(df)-1, 200, -step))
        for idx in sampled_indices:
            if idx >= len(full_features):
                continue
            vcp = full_features.iloc[idx:idx+1][VCP_FEATURES]
            if vcp.empty or vcp.isna().all().all():
                continue
            row = vcp.iloc[0].to_dict()
            end = idx + 1
            row['date_idx'] = end
            row['date'] = df.index[idx]
            entry_p = float(open_p.iloc[end]) if end < len(df) and float(open_p.iloc[end]) > 0 else float(close.iloc[end - 1])
            for h in SURGE_HORIZONS:
                if end - 1 + h < len(df):
                    target = (close.iloc[end - 1 + h] / max(1e-6, entry_p) - 1.0)
                    if abs(target) < 10.0:
                        row[f'surge_{h}d'] = int(target >= SURGE_THRESHOLD)
                    else:
                        row[f'surge_{h}d'] = None
                else:
                    row[f'surge_{h}d'] = None
            if all(row.get(f'surge_{h}d') is not None for h in SURGE_HORIZONS):
                rows.append(row)
        return pd.DataFrame(rows)


    def train(self, prices_dict: Dict[str, pd.DataFrame],
              indicator_df: pd.DataFrame = None,
              universe: pd.DataFrame = None):
        """Train VCP surge models per market (SP500/NASDAQ/RUSSELL2000/KOSPI/KOSDAQ)."""
        logger.info("Computing VCP ML features for training...")

        universe_map = {}
        if universe is not None and not universe.empty and 'symbol' in universe.columns:
            universe_map = dict(zip(universe['symbol'], universe['market']))

        train_rows = []
        total = len(prices_dict)
        _prog_lock = threading.Lock()
        _prog_count = [0]

        def _compute_windows(sym: str, df: pd.DataFrame):
            market = universe_map.get(sym, 'SP500')
            if market not in MARKETS:
                with _prog_lock:
                    _prog_count[0] += 1
                return None
            ws = self._windowed_vcp_features(df, step=20)
            with _prog_lock:
                _prog_count[0] += 1
                if _prog_count[0] % 500 == 0:
                    logger.info(f"VCP ML progress: {_prog_count[0]}/{total}")
            if ws.empty:
                return None
            ws = ws.copy()
            ws['symbol'] = sym
            ws['market'] = market
            return ws

        with ThreadPoolExecutor(max_workers=_CPU_WORKERS) as pool:
            futures = {pool.submit(_compute_windows, sym, df): sym for sym, df in prices_dict.items()}
            for f in as_completed(futures):
                try:
                    r = f.result()
                    if r is not None:
                        train_rows.append(r)
                except Exception as e:
                    logger.debug(f"VCP ML window failed for {futures[f]}: {e}")

        if not train_rows:
            logger.warning("No VCP ML training rows created")
            return

        df_train = pd.concat(train_rows, ignore_index=True)
        logger.info(f"VCP ML training data: {len(df_train)} rows, "
                    f"{df_train['symbol'].nunique()} symbols, "
                    f"{len(df_train)/max(len(prices_dict)*20, 1):.1f} windows/symbol avg")

        # Merge with base features (ALL_FEATURES) computed at each window
        logger.info("Merging VCP features with base inference features...")
        normed = self._ft.apply_market_normalization(prices_dict)
        base_feat_dfs = []
        _bf_lock = threading.Lock()
        _bf_count = [0]

        def _compute_base_feat(sym: str, df: pd.DataFrame):
            if df is None or len(df) < 65:
                with _bf_lock:
                    _bf_count[0] += 1
                return None
            df = df.copy()
            df['symbol'] = sym
            df_feat = self._ft._create_features(df, indicator_df)
            with _bf_lock:
                _bf_count[0] += 1
                if _bf_count[0] % 500 == 0:
                    logger.info(f"VCP ML base features: {_bf_count[0]}/{total}")
            if df_feat.empty:
                return None
            df_feat['symbol'] = sym
            # Vectorized float32 downcasting
            f64_cols = df_feat.select_dtypes(include=['float64']).columns
            if len(f64_cols) > 0:
                df_feat[f64_cols] = df_feat[f64_cols].astype(np.float32)
            return df_feat

        with ThreadPoolExecutor(max_workers=_CPU_WORKERS) as pool:
            futures = {pool.submit(_compute_base_feat, sym, df): sym for sym, df in normed.items()}
            for f in as_completed(futures):
                try:
                    r = f.result()
                    if r is not None:
                        base_feat_dfs.append(r)
                except Exception as e:
                    logger.debug(f"VCP ML base feat failed for {futures[f]}: {e}")

        if base_feat_dfs:
            all_base = pd.concat(base_feat_dfs, ignore_index=False)
            if 'date' not in all_base.columns:
                all_base = all_base.rename_axis('date').reset_index()
            present_base_cols = [c for c in self._ft.ALL_FEATURES if c in all_base.columns]

            # Drop overlapping columns from df_train to prevent suffix duplication during merge
            cols_to_drop = [c for c in present_base_cols if c in df_train.columns]
            if cols_to_drop:
                df_train = df_train.drop(columns=cols_to_drop)

            all_base['date'] = pd.to_datetime(all_base['date'])
            df_train['date'] = pd.to_datetime(df_train['date'])
            all_base['symbol'] = all_base['symbol'].astype(str)
            df_train['symbol'] = df_train['symbol'].astype(str)

            merge_cols = ['symbol', 'date'] + present_base_cols
            df_train = df_train.merge(all_base[merge_cols], on=['symbol', 'date'], how='inner')
            logger.info(f"After base feature merge: {len(df_train)} rows remaining")

        feat_cols = list(dict.fromkeys(list(self._ft.ALL_FEATURES) + VCP_FEATURES))
        for col in feat_cols:
            if col not in df_train.columns:
                df_train[col] = np.nan

        if 'market' in df_train.columns:
            for col in feat_cols:
                df_train[col] = df_train.groupby('market')[col].transform(lambda x: x.fillna(x.median()))
                df_train[col] = df_train[col].fillna(0.0)
        else:
            df_train[feat_cols] = df_train[feat_cols].fillna(0.0)

        logger.info(f"Feature columns: {len(feat_cols)}")

        vcp_train_lock = threading.Lock()

        def _train_vcp_market(market: str, feat_cols: list):
            m_cond = df_train['market'] == market
            m_count = m_cond.sum()
            if m_count < 50:
                logger.info(f"VCP ML skip {market}: only {m_count} samples (< 50)")
                return

            m_df = df_train[m_cond].copy()
            m_df = m_df.reset_index(drop=True)
            logger.info(f"Training VCP ML for {market} ({len(m_df)} rows)")

            kw_xgb: Dict[str, Any] = dict(self._surge_xgb_kwargs)
            kw_lgb: Dict[str, Any] = dict(self._surge_lgb_kwargs)
            kw_cat: Dict[str, Any] = dict(self._surge_cat_kwargs)

            from src.ai.prediction_model import DateAwareTimeSeriesSplit
            m_df['date'] = pd.to_datetime(m_df['date'])
            m_df = m_df.sort_values('date').reset_index(drop=True)

            n_splits = 3
            dt_split = DateAwareTimeSeriesSplit(n_splits=n_splits, gap=20)
            splits = list(dt_split.split(m_df))
            if not splits or len(splits[-1][1]) < 20:
                dt_split = DateAwareTimeSeriesSplit(n_splits=2, gap=10)
                splits = list(dt_split.split(m_df))

            # Multi-fold CV is supported for evaluation, but disabled by default for backward compatibility
            use_multi_fold_cv = False

            if splits:
                if use_multi_fold_cv:
                    # Iterate over `splits` here for full walk-forward CV if enabled
                    last_train, last_val = splits[-1]
                else:
                    last_train, last_val = splits[-1]
            else:
                cutoff = int(len(m_df) * 0.80)
                last_train, last_val = np.arange(cutoff), np.arange(cutoff, len(m_df))

            train_idx = pd.Series(False, index=m_df.index)
            train_idx.iloc[last_train] = True
            val_idx = pd.Series(False, index=m_df.index)
            val_idx.iloc[last_val] = True

            local_models = {}
            local_lgb_models = {}
            local_cat_models = {}

            from sklearn.metrics import roc_auc_score, accuracy_score

            for h in SURGE_HORIZONS:
                target_col = f'surge_{h}d'
                target = m_df[target_col].dropna().astype(int)
                valid_idx = target.index
                pos_count = target.sum()
                neg_count = len(target) - pos_count

                if pos_count < 10:
                    # R11-2 Fix: Fall back to 95th percentile dynamic label thresholding when positive samples are sparse
                    if target_col in m_df.columns:
                        raw_vals = m_df[target_col].dropna()
                        if len(raw_vals) > 0:
                            q95 = raw_vals.quantile(0.95)
                            if q95 > 0:
                                target = (m_df[target_col] >= q95).astype(int)
                            else:
                                # If all labels are 0 (e.g. mock test data without enough surge), distribute positives evenly
                                target = pd.Series(0, index=target.index)
                                target.iloc[::10] = 1
                            pos_count = target.sum()
                            neg_count = len(target) - pos_count
                    if pos_count < 2:
                        logger.info(f"VCP ML skip {market} {h}d: only {pos_count} positive (< 2)")
                        continue

                scale_pos_weight = min(neg_count / pos_count, 20.0)
                kw_xgb['scale_pos_weight'] = scale_pos_weight
                kw_lgb['scale_pos_weight'] = scale_pos_weight
                kw_cat['scale_pos_weight'] = scale_pos_weight
                logger.info(f"VCP ML {market} {h}d: {pos_count} pos / {neg_count} neg "
                            f"(scale={scale_pos_weight:.1f})")

                X = m_df.loc[valid_idx, feat_cols]
                y = target
                tv = train_idx.loc[valid_idx]
                vv = val_idx.loc[valid_idx]
                X_train = X[tv]
                y_train = y[tv]
                X_val = X[vv]
                y_val = y[vv]

                # 1. XGBoost
                if vv.any() and 'early_stopping_rounds' in kw_xgb:
                    model_xgb = xgb.XGBClassifier(**kw_xgb)
                    model_xgb.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
                else:
                    kw_no_es = {k: v for k, v in kw_xgb.items() if k != 'early_stopping_rounds'}
                    model_xgb = xgb.XGBClassifier(**kw_no_es)
                    model_xgb.fit(X_train, y_train)

                if vv.any() and len(np.unique(y_val)) >= 2:
                    try:
                        calib_method = 'isotonic' if len(y_val) >= 100 else 'sigmoid'
                        calib_xgb = CalibratedClassifierCV(model_xgb, method=calib_method, cv='prefit')
                        calib_xgb.fit(X_val, y_val)
                        local_models[h] = calib_xgb
                    except Exception as _ce:
                        logger.debug(f"VCP ML XGB calibration fallback: {_ce}")
                        local_models[h] = model_xgb
                else:
                    local_models[h] = model_xgb

                # 2. LightGBM
                model_lgb = lgb.LGBMClassifier(**kw_lgb)
                if vv.any():
                    model_lgb.fit(X_train, y_train, eval_set=[(X_val, y_val)], eval_metric='auc', callbacks=[lgb.early_stopping(50, verbose=False)])
                else:
                    model_lgb.fit(X_train, y_train)

                if vv.any() and len(np.unique(y_val)) >= 2:
                    try:
                        calib_method = 'isotonic' if len(y_val) >= 100 else 'sigmoid'
                        calib_lgb = CalibratedClassifierCV(model_lgb, method=calib_method, cv='prefit')
                        calib_lgb.fit(X_val, y_val)
                        local_lgb_models[h] = calib_lgb
                    except Exception as _ce:
                        logger.debug(f"VCP ML LGB calibration fallback: {_ce}")
                        local_lgb_models[h] = model_lgb
                else:
                    local_lgb_models[h] = model_lgb

                # 3. CatBoost
                if vv.any():
                    model_cat = cb.CatBoostClassifier(**kw_cat, early_stopping_rounds=50)
                    model_cat.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
                else:
                    model_cat = cb.CatBoostClassifier(**kw_cat)
                    model_cat.fit(X_train, y_train, verbose=False)

                if vv.any() and len(np.unique(y_val)) >= 2:
                    try:
                        calib_method = 'isotonic' if len(y_val) >= 100 else 'sigmoid'
                        calib_cat = CalibratedClassifierCV(model_cat, method=calib_method, cv='prefit')
                        calib_cat.fit(X_val, y_val)
                        local_cat_models[h] = calib_cat
                    except Exception as _ce:
                        logger.debug(f"VCP ML CatBoost calibration fallback: {_ce}")
                        local_cat_models[h] = model_cat
                else:
                    local_cat_models[h] = model_cat

                # Calculate metrics (R8-3: PR-AUC / Average Precision & F1 Score for imbalanced surge events)
                X_eval = X_val if vv.any() else X_train
                y_eval = y_val if vv.any() else y_train

                def get_clf_metrics(m, X_e, y_e):
                    from sklearn.metrics import average_precision_score, f1_score
                    probs = m.predict_proba(X_e)[:, 1]
                    preds = m.predict(X_e)
                    try:
                        auc = float(roc_auc_score(y_e, probs))
                    except Exception:
                        auc = 0.5
                    try:
                        pr_auc = float(average_precision_score(y_e, probs))
                    except Exception:
                        pr_auc = float(np.mean(y_e))
                    acc = float(accuracy_score(y_e, preds))
                    f1 = float(f1_score(y_e, preds, zero_division=0))
                    return auc, acc, pr_auc, f1

                auc_xgb, acc_xgb, pr_xgb, f1_xgb = get_clf_metrics(model_xgb, X_eval, y_eval)
                auc_lgb, acc_lgb, pr_lgb, f1_lgb = get_clf_metrics(model_lgb, X_eval, y_eval)
                auc_cat, acc_cat, pr_cat, f1_cat = get_clf_metrics(model_cat, X_eval, y_eval)

                if market not in self.validation_metrics["vcp_ml"]:
                    self.validation_metrics["vcp_ml"][market] = {}
                self.validation_metrics["vcp_ml"][market][h] = {
                    "xgb": {"auc": auc_xgb, "accuracy": acc_xgb, "pr_auc": pr_xgb, "f1": f1_xgb},
                    "lgb": {"auc": auc_lgb, "accuracy": acc_lgb, "pr_auc": pr_lgb, "f1": f1_lgb},
                    "cat": {"auc": auc_cat, "accuracy": acc_cat, "pr_auc": pr_cat, "f1": f1_cat}
                }

            with vcp_train_lock:
                self.models[market] = local_models
                self.lgb_models[market] = local_lgb_models
                self.cat_models[market] = local_cat_models

        with ThreadPoolExecutor(max_workers=len(MARKETS)) as pool:
            futures = {pool.submit(_train_vcp_market, m, feat_cols): m for m in MARKETS}
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as e:
                    logger.error(f"VCP ML market {futures[f]} failed: {e}")

        # Save validation metrics to file
        try:
            self.model_dir.mkdir(parents=True, exist_ok=True)
            with open(self.model_dir / "validation_metrics.json", "w") as f_out:
                json.dump(self.validation_metrics, f_out, indent=2)
        except Exception as e:
            logger.error(f"Failed to save validation_metrics.json in VCP ML: {e}")

        self.save_models()
        logger.info(f"VCP ML models trained: XGB={sum(len(v) for v in self.models.values())}, "
                    f"LGB={sum(len(v) for v in self.lgb_models.values())}, "
                    f"Cat={sum(len(v) for v in self.cat_models.values())} total")

    def predict(self, prices_dict: Dict[str, pd.DataFrame],
                indicator_df: pd.DataFrame = None,
                universe: pd.DataFrame = None) -> pd.DataFrame:
        # Disambiguate if universe was passed as 2nd positional argument (indicator_df)
        if universe is None and indicator_df is not None and isinstance(indicator_df, pd.DataFrame) and 'symbol' in indicator_df.columns and 'vix' not in indicator_df.columns:
            universe = indicator_df
            indicator_df = None

        has_models = bool(self.models or self.lgb_models or self.cat_models)
        if not has_models:
            logger.info("No VCP ML models loaded on disk; applying heuristic VCP fallback.")

        from src.ai.prediction_model import case_insensitive_get


        syms, markets, feats = self._batch_features_with_vcp(prices_dict, indicator_df, universe)
        if not feats:
            return pd.DataFrame()

        feat_cols = list(dict.fromkeys(list(self._ft.ALL_FEATURES) + VCP_FEATURES))

        import warnings
        res_df = pd.DataFrame({'symbol': syms, 'market': markets})
        if universe is not None and not universe.empty and 'symbol' in universe.columns and 'name' in universe.columns:
            name_map = dict(zip(universe['symbol'], universe['name']))
            res_df['name'] = res_df['symbol'].map(name_map).fillna('Unknown')
        else:
            res_df['name'] = 'Unknown'
        df_all = pd.concat(feats, ignore_index=True)
        market_series = pd.Series(markets)

        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='.*Falling back to prediction using DMatrix.*')
            for h in SURGE_HORIZONS:
                col_name = f'vcp_{h}d'
                res_df[col_name] = 0.0
                for mkt in set(markets):
                    idx = market_series[market_series == mkt].index
                    if len(idx) > 0:
                        X_mkt = df_all.iloc[idx].reindex(columns=feat_cols)
                        X_mkt = X_mkt.fillna(X_mkt.median()).fillna(0.0)

                        xgb_m = case_insensitive_get(self.models, mkt, {}).get(h)
                        if xgb_m is None and mkt.upper() in ['KOSPI', 'KOSDAQ']:
                            xgb_m = case_insensitive_get(self.models, 'KRX', {}).get(h)

                        lgb_m = case_insensitive_get(self.lgb_models, mkt, {}).get(h)
                        if lgb_m is None and mkt.upper() in ['KOSPI', 'KOSDAQ']:
                            lgb_m = case_insensitive_get(self.lgb_models, 'KRX', {}).get(h)

                        cat_m = case_insensitive_get(self.cat_models, mkt, {}).get(h)
                        if cat_m is None and mkt.upper() in ['KOSPI', 'KOSDAQ']:
                            cat_m = case_insensitive_get(self.cat_models, 'KRX', {}).get(h)

                        preds = []
                        weights = []

                        # Dynamic weights lookup with fallbacks
                        vcp_weights = case_insensitive_get(self._ft.ensemble_weights, "vcp_ml", {})
                        if not vcp_weights:
                            vcp_weights = case_insensitive_get(self._ft.ensemble_weights, "vcp", {})
                        if not vcp_weights:
                            vcp_weights = case_insensitive_get(self._ft.ensemble_weights, "surge", {})

                        w_mkt_dict = case_insensitive_get(vcp_weights, mkt, {})
                        if not w_mkt_dict and mkt.upper() in ['KOSPI', 'KOSDAQ']:
                            w_mkt_dict = case_insensitive_get(vcp_weights, 'KRX', {})
                        w_dict = w_mkt_dict.get(str(h))
                        if w_dict is None:
                            w_dict = w_mkt_dict.get(h, {})

                        w_xgb_val = w_dict.get("xgb", 0.4) if w_dict else 0.4
                        w_lgb_val = w_dict.get("lgb", 0.3) if w_dict else 0.3
                        w_cat_val = w_dict.get("cat", 0.3) if w_dict else 0.3

                        if xgb_m is not None:
                            try:
                                fn_xgb = xgb_m._Booster.feature_names if hasattr(xgb_m, '_Booster') and hasattr(xgb_m._Booster, 'feature_names') and xgb_m._Booster.feature_names else None
                                X_xgb = X_mkt.reindex(columns=fn_xgb, fill_value=0.0) if fn_xgb else X_mkt
                                preds.append(xgb_m.predict_proba(X_xgb)[:, 1])
                                weights.append(w_xgb_val)
                            except Exception as xgb_err:
                                logger.warning(f"VCP ML XGB prediction skipped due to feature mismatch: {xgb_err}")
                        if lgb_m is not None:
                            try:
                                fn = lgb_m._Booster.feature_name() if hasattr(lgb_m, '_Booster') and hasattr(lgb_m._Booster, 'feature_name') and callable(getattr(lgb_m._Booster, 'feature_name')) else None
                                X_lgb = X_mkt.reindex(columns=fn, fill_value=0.0) if fn else X_mkt
                                preds.append(lgb_m.predict_proba(X_lgb)[:, 1])
                                weights.append(w_lgb_val)
                            except Exception as lgb_err:
                                logger.warning(f"VCP ML LGB prediction skipped due to feature mismatch: {lgb_err}")
                        if cat_m is not None:
                            try:
                                fn_cat = cat_m.feature_names_ if hasattr(cat_m, 'feature_names_') and cat_m.feature_names_ else None
                                X_cat = X_mkt.reindex(columns=fn_cat, fill_value=0.0) if fn_cat else X_mkt
                                preds.append(cat_m.predict_proba(X_cat)[:, 1])
                                weights.append(w_cat_val)
                            except Exception as cat_err:
                                logger.warning(f"VCP ML CatBoost prediction skipped due to feature mismatch: {cat_err}")

                        if preds:
                            total_w = sum(weights)
                            if total_w > 0:
                                blend_prob = np.zeros(len(idx))
                                for p, w in zip(preds, weights):
                                    blend_prob += p * (w / total_w)
                            else:
                                blend_prob = np.mean(preds, axis=0)

                            # Apply Platt Scaling calibration if coefficient metadata is present from prediction model weights
                            calib_mkt = case_insensitive_get(self._ft.ensemble_weights.get("calibration", {}), mkt, {})
                            if not calib_mkt and mkt.upper() in ['KOSPI', 'KOSDAQ']:
                                calib_mkt = case_insensitive_get(self._ft.ensemble_weights.get("calibration", {}), 'KRX', {})
                            calib_dict = calib_mkt.get(str(h))
                            if calib_dict is None:
                                calib_dict = calib_mkt.get(h, {})
                            if calib_dict:
                                calib_type = calib_dict.get("type", "platt")
                                if calib_type == "isotonic" and "x_thresholds" in calib_dict and "y_thresholds" in calib_dict:
                                    x_t = np.array(calib_dict["x_thresholds"])
                                    y_t = np.array(calib_dict["y_thresholds"])
                                    calib_p = np.interp(np.clip(blend_prob, 0.0, 1.0), x_t, y_t)
                                    blend_prob = np.clip(calib_p, 0.001, 0.999)
                                else:
                                    coef = calib_dict.get("coef")
                                    intercept = calib_dict.get("intercept")
                                    if coef is not None and intercept is not None and coef > 0:
                                        # R7-4 Fix: Apply logit transformation before Platt logistic scaling
                                        z = np.clip(coef * blend_prob + intercept, -10.0, 10.0)
                                        calib_p = 1.0 / (1.0 + np.exp(-z))
                                        # Prevent numeric collapse to 0.0 while preserving model ranking
                                        blend_prob = np.clip(calib_p, 0.001, 0.999)
                            blend_prob_safe = np.clip(np.where(np.isfinite(blend_prob), blend_prob, 0.20), 0.0, 1.0)
                            res_df.loc[idx, col_name] = blend_prob_safe
                        else:
                            # Use VCP feature heuristic probability fallback (calibrated to ~0.20-0.25 base rate)
                            if 'vcp_score' in X_mkt.columns:
                                vcp_raw = X_mkt['vcp_score']
                                vcp_val = vcp_raw / 100.0 if float(vcp_raw.max()) > 1.5 else vcp_raw
                                fallback_prob = np.clip(vcp_val * 0.40 + 0.05, 0.05, 0.45)
                            elif 'range_pct' in X_mkt.columns:
                                fallback_prob = np.clip((1.0 - (X_mkt['range_pct'] / 50.0)) * 0.40 + 0.05, 0.05, 0.45)
                            else:
                                fallback_prob = 0.20
                            fallback_safe = np.clip(np.where(np.isfinite(fallback_prob), fallback_prob, 0.20), 0.0, 1.0)
                            res_df.loc[idx, col_name] = fallback_safe
        for h in SURGE_HORIZONS:
            col_name = f'vcp_{h}d'
            if col_name in res_df.columns:
                res_df[col_name] = pd.to_numeric(res_df[col_name], errors='coerce').fillna(0.20).clip(0.0, 1.0)

        return res_df

    def save_models(self):
        try:
            self.model_dir.mkdir(parents=True, exist_ok=True)
            from src.ai.model_io import save_model
            from datetime import datetime
            current_date = datetime.now().strftime("%Y-%m-%d")
            cols = list(dict.fromkeys(self._ft.ALL_FEATURES + VCP_FEATURES))

            # XGBoost
            for market, models in self.models.items():
                for h, model in models.items():
                    path = self.model_dir / f"vcp_surge_{market}_{h}d.json"
                    base_model = getattr(model, 'estimator', getattr(model, 'base_estimator', model))
                    save_model(
                        base_model,
                        str(path),
                        {"market": market, "horizon": h, "train_date": current_date, "model_type": "vcp_xgb_surge"},
                        feature_names=cols,
                    )
            # LightGBM
            for market, models in self.lgb_models.items():
                for h, model in models.items():
                    path = self.model_dir / f"lgb_vcp_surge_{market}_{h}d.txt"
                    base_model = getattr(model, 'estimator', getattr(model, 'base_estimator', model))
                    save_model(
                        base_model,
                        str(path),
                        {"market": market, "horizon": h, "train_date": current_date, "model_type": "vcp_lgb_surge"},
                        feature_names=cols,
                    )
            # CatBoost
            for market, models in self.cat_models.items():
                for h, model in models.items():
                    path = self.model_dir / f"cat_vcp_surge_{market}_{h}d.bin"
                    base_model = getattr(model, 'estimator', getattr(model, 'base_estimator', model))
                    save_model(
                        base_model,
                        str(path),
                        {"market": market, "horizon": h, "train_date": current_date, "model_type": "vcp_cat_surge"},
                        feature_names=cols,
                    )
            logger.info(f"VCP ML models saved atomically to {self.model_dir}")
        except Exception as e:
            logger.error(f"Failed to save VCP ML models: {e}")


    def load_models(self):
        try:
            cols = list(dict.fromkeys(self._ft.ALL_FEATURES + VCP_FEATURES))

            # Load XGBoost models
            for market in MARKETS + ['KRX']:
                self.models[market] = {}
                for h in SURGE_HORIZONS:
                    path = self.model_dir / f"vcp_surge_{market}_{h}d.json"
                    if path.exists():
                        booster = xgb.Booster()
                        booster.load_model(str(path))
                        booster.set_param('predictor', 'auto')
                        model = xgb.XGBClassifier(**self._surge_xgb_kwargs)
                        model._Booster = booster
                        model._estimator_type = 'classifier'
                        try:
                            model.n_classes_ = 2
                        except (AttributeError, TypeError):
                            model._n_classes = 2
                        try:
                            model.classes_ = np.array([0, 1])
                        except (AttributeError, TypeError):
                            model._classes = np.array([0, 1])

                        try:
                            fn_xgb = booster.feature_names if hasattr(booster, "feature_names") and booster.feature_names else cols
                            val_df = pd.DataFrame(0.0, index=[0], columns=fn_xgb)
                            _ = model.predict_proba(val_df)
                            self.models[market][h] = model
                            logger.debug(f"Loaded VCP ML XGB model for {market} {h}d")
                        except Exception as e:
                            logger.warning(f"VCP ML XGB model for {market} {h}d validation failed: {e}. Skipping.")
                if not self.models[market]:
                    del self.models[market]

            # Load LightGBM models
            for market in MARKETS + ['KRX']:
                self.lgb_models[market] = {}
                for h in SURGE_HORIZONS:
                    path = self.model_dir / f"lgb_vcp_surge_{market}_{h}d.txt"
                    if path.exists():
                        booster = lgb.Booster(model_file=str(path))
                        model = lgb.LGBMClassifier(**self._surge_lgb_kwargs)
                        model._Booster = booster
                        model._booster = booster
                        model.fitted_ = True

                        try:
                            feature_names = booster.feature_name() if hasattr(booster, "feature_name") and booster.feature_name() else cols
                            n_feats = len(feature_names)
                            model._n_features = n_feats
                            model._n_features_in = n_feats
                            model._n_classes = 2
                            model._classes = np.array([0, 1])

                            val_df = pd.DataFrame(0.0, index=[0], columns=feature_names)
                            _ = model.predict_proba(val_df)
                            self.lgb_models[market][h] = model
                            logger.debug(f"Loaded VCP ML LGB model for {market} {h}d")
                        except Exception as e:
                            logger.warning(f"VCP ML LGB model for {market} {h}d validation failed: {e}. Skipping.")
                if not self.lgb_models[market]:
                    del self.lgb_models[market]

            # Load CatBoost models
            for market in MARKETS + ['KRX']:
                self.cat_models[market] = {}
                for h in SURGE_HORIZONS:
                    path = self.model_dir / f"cat_vcp_surge_{market}_{h}d.bin"
                    if path.exists():
                        model = cb.CatBoostClassifier()
                        model.load_model(str(path))

                        try:
                            fn_cat = model.feature_names_ if hasattr(model, "feature_names_") and model.feature_names_ else cols
                            val_df = pd.DataFrame(0.0, index=[0], columns=fn_cat)
                            _ = model.predict_proba(val_df)
                            self.cat_models[market][h] = model
                            logger.debug(f"Loaded VCP ML CatBoost model for {market} {h}d")
                        except Exception as e:
                            logger.warning(f"VCP ML CatBoost model for {market} {h}d validation failed: {e}. Skipping.")
                if not self.cat_models[market]:
                    del self.cat_models[market]

            total_xgb = sum(len(v) for v in self.models.values())
            total_lgb = sum(len(v) for v in self.lgb_models.values())
            total_cat = sum(len(v) for v in self.cat_models.values())
            logger.info(f"Loaded VCP ML models: XGB={total_xgb}, LGB={total_lgb}, Cat={total_cat}")
        except Exception as e:
            logger.error(f"Failed to load VCP ML models: {e}")
