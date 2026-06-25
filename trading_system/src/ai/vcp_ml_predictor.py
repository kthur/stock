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

logger = logging.getLogger(__name__)

_CPU_WORKERS = max(1, (os.cpu_count() or 4))

_HAS_CUDA = False
try:
    import torch
    _HAS_CUDA = torch.cuda.is_available()
except Exception:
    pass

VCP_FEATURES = [
    'range_5v20', 'range_10v20', 'range_20v40', 'range_40v60',
    'vol_20v60',
    'dist_ma50', 'dist_ma200',
    'range_pos_10d', 'range_pos_20d',
    'atr_14d_norm', 'monotonic', 'vcp_score',
]

SURGE_HORIZONS = [1, 3, 5, 20]
SURGE_THRESHOLD = 0.20

MARKETS = ['KOSPI', 'KOSDAQ', 'KONEX', 'SP500']


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
            except Exception as e:
                logger.warning(f"VCPSurgePredictor: Failed to load tuned parameters: {e}")

        if _HAS_CUDA:
            self._surge_xgb_kwargs['device'] = 'cuda'

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
        if df is None or len(df) < 200:
            return pd.DataFrame()

        df = df.copy()
        high = _safe_series(df['High']).astype(float)
        low = _safe_series(df['Low']).astype(float)
        close = _safe_series(df['Close']).astype(float)
        volume = _safe_series(df['Volume']).astype(float)

        windows = [5, 10, 20, 40, 60]
        ranges = []
        for w in windows:
            r = (high.tail(w).max() - low.tail(w).min()) / close.tail(w).mean() * 100
            ranges.append(r)

        feat = {}
        feat['range_5v20'] = ranges[0] / max(ranges[2], 1e-10)
        feat['range_10v20'] = ranges[1] / max(ranges[2], 1e-10)
        feat['range_20v40'] = ranges[2] / max(ranges[3], 1e-10)
        feat['range_40v60'] = ranges[3] / max(ranges[4], 1e-10)

        vol_20d = volume.tail(20).mean()
        vol_60d = volume.tail(60).mean()
        feat['vol_20v60'] = vol_20d / max(vol_60d, 1e-10)

        sma50 = close.rolling(50).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1]
        last_close = close.iloc[-1]
        feat['dist_ma50'] = (last_close - sma50) / max(abs(sma50), 1e-10)
        feat['dist_ma200'] = (last_close - sma200) / max(abs(sma200), 1e-10)

        high_10d = high.tail(10).max()
        low_10d = low.tail(10).min()
        high_20d = high.tail(20).max()
        low_20d = low.tail(20).min()
        feat['range_pos_10d'] = (last_close - low_10d) / max(high_10d - low_10d, 1e-10)
        feat['range_pos_20d'] = (last_close - low_20d) / max(high_20d - low_20d, 1e-10)

        # Standard True Range (TR) and 14-period SMA
        tr_df = pd.DataFrame(index=df.index)
        tr_df['h_l'] = high - low
        tr_df['h_pc'] = (high - close.shift(1)).abs()
        tr_df['l_pc'] = (low - close.shift(1)).abs()
        tr_val = tr_df[['h_l', 'h_pc', 'l_pc']].max(axis=1)
        atr_14 = tr_val.rolling(14).mean().iloc[-1]
        feat['atr_14d_norm'] = (atr_14 / max(last_close, 1e-10)) * 100 if pd.notna(atr_14) else 0.0

        # VCP contraction: shorter windows should have smaller ranges than longer windows.
        # windows=[5,10,20,40,60] → ranges[0]=5d, ranges[4]=60d → ranges[i] < ranges[i+1].
        feat['monotonic'] = int(all(ranges[i] < ranges[i + 1] for i in range(len(ranges) - 1)))

        score = 0.0
        if feat['monotonic']:
            score += 25.0
        if vol_20d < vol_60d * 0.85:
            score += 15.0
        if last_close > sma50:
            score += 15.0
        if last_close > sma200:
            score += 15.0
        if feat['range_pos_10d'] > 0.6:
            score += 15.0
        if close.tail(10).iloc[0] < last_close:
            score += 15.0
        if ranges[0] < 4:
            score += 20.0
        elif ranges[0] < 7:
            score += 12.0
        elif ranges[0] < 10:
            score += 6.0
        feat['vcp_score'] = min(score, 100.0) / 100.0

        return pd.DataFrame([feat])

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
        if universe is not None:
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
                return None

            latest = df_feat.iloc[-1:].copy()
            # Drop VCP columns in latest if they already exist to avoid duplicate columns
            cols_to_drop = [col for col in vcp_feat.columns if col in latest.columns]
            if cols_to_drop:
                latest = latest.drop(columns=cols_to_drop)
            for col in vcp_feat.columns:
                latest[col] = vcp_feat[col].values[0]

            all_cols = list(dict.fromkeys(list(base_features) + VCP_FEATURES))
            present = [c for c in all_cols if c in latest.columns]
            return sym, market, latest[present]

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
        rows = []
        close = _safe_series(df['Close']).astype(float)
        for end in range(len(df), 200, -step):
            window = df.iloc[:end]
            vcp = self._compute_vcp_features(window)
            if vcp.empty:
                continue
            row = vcp.iloc[0].to_dict()
            row['date_idx'] = end
            row['date'] = window.index[-1]
            for h in SURGE_HORIZONS:
                if end - 1 + h < len(df):
                    target = (close.iloc[end - 1 + h] / close.iloc[end - 1] - 1)
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
        """Train VCP surge models per market (KOSPI/KOSDAQ/KONEX/SP500)."""
        logger.info("Computing VCP ML features for training...")

        universe_map = {}
        if universe is not None:
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

            merge_cols = ['symbol', 'date'] + present_base_cols
            df_train = df_train.merge(all_base[merge_cols], on=['symbol', 'date'], how='inner')
            logger.info(f"After base feature merge: {len(df_train)} rows remaining")

        feat_cols = list(dict.fromkeys([c for c in self._ft.ALL_FEATURES + VCP_FEATURES if c in df_train.columns]))
        logger.info(f"Feature columns: {len(feat_cols)}")

        vcp_train_lock = threading.Lock()

        def _train_vcp_market(market: str, feat_cols: list):
            m_cond = df_train['market'] == market
            m_count = m_cond.sum()
            if m_count < 200:
                logger.info(f"VCP ML skip {market}: only {m_count} samples (< 200)")
                return

            m_df = df_train[m_cond].copy()
            m_df = m_df.reset_index(drop=True)
            logger.info(f"Training VCP ML for {market} ({len(m_df)} rows)")

            kw_xgb: Dict[str, Any] = dict(self._surge_xgb_kwargs)
            kw_lgb: Dict[str, Any] = dict(self._surge_lgb_kwargs)
            kw_cat: Dict[str, Any] = dict(self._surge_cat_kwargs)

            m_df['date'] = pd.to_datetime(m_df['date'])
            cutoff = m_df['date'].quantile(0.8)
            train_idx = m_df['date'] <= cutoff
            val_idx = m_df['date'] > cutoff
            if val_idx.sum() < 50:
                train_idx = pd.Series([True] * len(m_df))
                val_idx = pd.Series([False] * len(m_df))

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
                    logger.info(f"VCP ML skip {market} {h}d: only {pos_count} positive (< 10)")
                    continue

                scale_pos_weight = min(neg_count / pos_count, 500)
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
                local_models[h] = model_xgb

                # 2. LightGBM
                model_lgb = lgb.LGBMClassifier(**kw_lgb)
                if vv.any():
                    model_lgb.fit(X_train, y_train, eval_set=[(X_val, y_val)], eval_metric='auc', callbacks=[lgb.early_stopping(50, verbose=False)])
                else:
                    model_lgb.fit(X_train, y_train)
                local_lgb_models[h] = model_lgb

                # 3. CatBoost
                if vv.any():
                    model_cat = cb.CatBoostClassifier(**kw_cat, early_stopping_rounds=50)
                    model_cat.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
                else:
                    model_cat = cb.CatBoostClassifier(**kw_cat)
                    model_cat.fit(X_train, y_train, verbose=False)
                local_cat_models[h] = model_cat

                # Calculate metrics
                X_eval = X_val if vv.any() else X_train
                y_eval = y_val if vv.any() else y_train

                def get_clf_metrics(m, X_e, y_e):
                    probs = m.predict_proba(X_e)[:, 1]
                    preds = m.predict(X_e)
                    try:
                        auc = float(roc_auc_score(y_e, probs))
                    except Exception:
                        auc = 0.5
                    acc = float(accuracy_score(y_e, preds))
                    return auc, acc

                auc_xgb, acc_xgb = get_clf_metrics(model_xgb, X_eval, y_eval)
                auc_lgb, acc_lgb = get_clf_metrics(model_lgb, X_eval, y_eval)
                auc_cat, acc_cat = get_clf_metrics(model_cat, X_eval, y_eval)

                if market not in self.validation_metrics["vcp_ml"]:
                    self.validation_metrics["vcp_ml"][market] = {}
                self.validation_metrics["vcp_ml"][market][h] = {
                    "xgb": {"auc": auc_xgb, "accuracy": acc_xgb},
                    "lgb": {"auc": auc_lgb, "accuracy": acc_lgb},
                    "cat": {"auc": auc_cat, "accuracy": acc_cat}
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
        """Predict VCP surge probabilities using market-specific models (batch optimized)."""
        if not self.models:
            logger.warning("No VCP ML models loaded, skipping prediction")
            return pd.DataFrame()

        syms, markets, feats = self._batch_features_with_vcp(prices_dict, indicator_df, universe)
        if not feats:
            return pd.DataFrame()

        feat_cols = list(dict.fromkeys([c for c in self._ft.ALL_FEATURES + VCP_FEATURES if c in feats[0].columns]))

        import warnings
        res_df = pd.DataFrame({'symbol': syms, 'market': markets})
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
                        X_mkt = df_all.iloc[idx][feat_cols]

                        xgb_m = self.models.get(mkt, {}).get(h)
                        lgb_m = self.lgb_models.get(mkt, {}).get(h)
                        cat_m = self.cat_models.get(mkt, {}).get(h)

                        preds = []
                        weights = []

                        if xgb_m is not None:
                            preds.append(xgb_m.predict_proba(X_mkt)[:, 1])
                            weights.append(0.4)
                        if lgb_m is not None:
                            preds.append(lgb_m.predict_proba(X_mkt)[:, 1])
                            weights.append(0.3)
                        if cat_m is not None:
                            preds.append(cat_m.predict_proba(X_mkt)[:, 1])
                            weights.append(0.3)

                        if preds:
                            total_w = sum(weights)
                            blend_prob = np.zeros(len(idx))
                            for p, w in zip(preds, weights):
                                blend_prob += p * (w / total_w)
                            
                            # Apply Platt Scaling calibration if coefficient metadata is present from prediction model weights
                            calib_dict = self._ft.ensemble_weights.get("calibration", {}).get(mkt, {}).get(str(h), {})
                            if calib_dict:
                                coef = calib_dict.get("coef")
                                intercept = calib_dict.get("intercept")
                                if coef is not None and intercept is not None:
                                    z = np.clip(coef * blend_prob + intercept, -20, 20)
                                    blend_prob = 1.0 / (1.0 + np.exp(-z))
                            res_df.loc[idx, col_name] = blend_prob
                        else:
                            res_df.loc[idx, col_name] = 0.0

        return res_df

    def save_models(self):
        try:
            self.model_dir.mkdir(parents=True, exist_ok=True)
            from src.ai.model_io import save_model
            from datetime import datetime
            current_date = datetime.now().strftime("%Y-%m-%d")

            # XGBoost
            for market, models in self.models.items():
                for h, model in models.items():
                    path = self.model_dir / f"vcp_surge_{market}_{h}d.json"
                    save_model(model, str(path), {"market": market, "horizon": h, "train_date": current_date, "model_type": "vcp_xgb_surge"})
            # LightGBM
            for market, models in self.lgb_models.items():
                for h, model in models.items():
                    path = self.model_dir / f"lgb_vcp_surge_{market}_{h}d.txt"
                    save_model(model, str(path), {"market": market, "horizon": h, "train_date": current_date, "model_type": "vcp_lgb_surge"})
            # CatBoost
            for market, models in self.cat_models.items():
                for h, model in models.items():
                    path = self.model_dir / f"cat_vcp_surge_{market}_{h}d.bin"
                    save_model(model, str(path), {"market": market, "horizon": h, "train_date": current_date, "model_type": "vcp_cat_surge"})
            logger.info(f"VCP ML models saved to {self.model_dir}")
        except Exception as e:
            logger.error(f"Failed to save VCP ML models: {e}")


    def load_models(self):
        try:
            cols = list(dict.fromkeys(self._ft.ALL_FEATURES + VCP_FEATURES))
            dummy_df = pd.DataFrame(0.0, index=[0], columns=cols)

            # Load XGBoost models
            for market in MARKETS:
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
                            _ = model.predict_proba(dummy_df)
                            self.models[market][h] = model
                            logger.debug(f"Loaded VCP ML XGB model for {market} {h}d")
                        except Exception as e:
                            logger.warning(f"VCP ML XGB model for {market} {h}d validation failed: {e}. Skipping.")
                if not self.models[market]:
                    del self.models[market]

            # Load LightGBM models
            for market in MARKETS:
                self.lgb_models[market] = {}
                for h in SURGE_HORIZONS:
                    path = self.model_dir / f"lgb_vcp_surge_{market}_{h}d.txt"
                    if path.exists():
                        booster = lgb.Booster(model_file=str(path))
                        model = lgb.LGBMClassifier(**self._surge_lgb_kwargs)
                        model._Booster = booster
                        model.fitted_ = True

                        try:
                            feature_names = booster.feature_name()
                            n_feats = len(feature_names) if feature_names else len(cols)
                            model._n_features = n_feats
                            model._n_features_in = n_feats
                            model._n_classes = 2
                            model._classes = np.array([0, 1])

                            _ = model.predict_proba(dummy_df)
                            self.lgb_models[market][h] = model
                            logger.debug(f"Loaded VCP ML LGB model for {market} {h}d")
                        except Exception as e:
                            logger.warning(f"VCP ML LGB model for {market} {h}d validation failed: {e}. Skipping.")
                if not self.lgb_models[market]:
                    del self.lgb_models[market]

            # Load CatBoost models
            for market in MARKETS:
                self.cat_models[market] = {}
                for h in SURGE_HORIZONS:
                    path = self.model_dir / f"cat_vcp_surge_{market}_{h}d.bin"
                    if path.exists():
                        model = cb.CatBoostClassifier()
                        model.load_model(str(path))

                        try:
                            _ = model.predict_proba(dummy_df)
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
