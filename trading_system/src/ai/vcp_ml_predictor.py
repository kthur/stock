import logging
import threading
import pandas as pd
import numpy as np
import xgboost as xgb
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

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
            model_dir = Path(__file__).resolve().parent.parent.parent / "models"
        self.model_dir = Path(model_dir)

        # Feature helper: reuse OnDevicePredictionModel's feature computation
        self._ft = OnDevicePredictionModel(model_dir=self.model_dir)
        self._ft.models = {}
        self._ft.surge_models = {}

        self.models: Dict[str, Dict[int, xgb.XGBClassifier]] = {}

        self._surge_xgb_kwargs = dict(
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
        if _HAS_CUDA:
            self._surge_xgb_kwargs['device'] = 'cuda'

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
            r = (high.tail(w).max() - low.tail(w).max()) / close.tail(w).mean() * 100
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

        tr14 = np.maximum(
            high.tail(14).max() - low.tail(14).min(),
            abs(low.tail(14).min() - close.shift(1).tail(14).min()),
        )
        feat['atr_14d_norm'] = tr14 / max(last_close, 1e-10) * 100 if isinstance(tr14, (int, float)) else 0.0

        feat['monotonic'] = int(all(ranges[i] > ranges[i + 1] for i in range(len(ranges) - 1)))

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

        symbols_list = []
        market_list = []
        feature_list = []

        universe_map = {}
        if universe is not None:
            universe_map = dict(zip(universe['symbol'], universe['market']))

        for sym, df in normed.items():
            if df is None or len(df) < 65:
                continue
            market = universe_map.get(sym, 'SP500')
            if market not in MARKETS:
                market = 'SP500'
            df = df.copy()
            df['symbol'] = sym
            df_feat = self._ft._create_features(df, indicator_df)
            if df_feat.empty:
                continue

            vcp_feat = self._compute_vcp_features(prices_dict.get(sym))
            if vcp_feat.empty:
                continue

            latest = df_feat.iloc[-1:].copy()
            for col in vcp_feat.columns:
                latest[col] = vcp_feat[col].values[0]

            symbols_list.append(sym)
            market_list.append(market)
            all_cols = list(base_features) + VCP_FEATURES
            present = [c for c in all_cols if c in latest.columns]
            feature_list.append(latest[present])

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
            for h in SURGE_HORIZONS:
                if end > h:
                    target = (close.iloc[end - 1] / close.iloc[end - h - 1] - 1)
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
        for idx, (sym, df) in enumerate(prices_dict.items()):
            if idx % 500 == 0:
                logger.info(f"VCP ML progress: {idx}/{total}")
            market = universe_map.get(sym, 'SP500')
            if market not in MARKETS:
                continue
            ws = self._windowed_vcp_features(df, step=20)
            if ws.empty:
                continue
            ws['symbol'] = sym
            ws['market'] = market
            train_rows.append(ws)

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
        for sym, df in normed.items():
            if df is None or len(df) < 65:
                continue
            df = df.copy()
            df['symbol'] = sym
            df_feat = self._ft._create_features(df, indicator_df)
            if df_feat.empty:
                continue
            df_feat['symbol'] = sym
            base_feat_dfs.append(df_feat)
        if base_feat_dfs:
            all_base = pd.concat(base_feat_dfs, ignore_index=True)
            # Map windowed VCP features to nearest time slice in base features
            for sym in df_train['symbol'].unique():
                sym_mask = df_train['symbol'] == sym
                sym_df = df_train[sym_mask].copy()
                base_sym = all_base[all_base['symbol'] == sym]
                if base_sym.empty:
                    df_train = df_train[~sym_mask]
                    continue
                for idx2, row2 in sym_df.iterrows():
                    di = row2['date_idx']
                    match = base_sym.iloc[-1:] if di >= len(base_sym) else base_sym.iloc[[di - 1]]
                    if match.empty:
                        continue
                    for col in self._ft.ALL_FEATURES:
                        if col in match.columns:
                            df_train.at[idx2, col] = match[col].values[0]
            logger.info(f"After base feature merge: {len(df_train)} rows remaining")

        feat_cols = [c for c in self._ft.ALL_FEATURES + VCP_FEATURES if c in df_train.columns]
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

            kw = dict(self._surge_xgb_kwargs)

            cutoff = m_df['date_idx'].quantile(0.8)
            train_idx = m_df['date_idx'] <= cutoff
            val_idx = m_df['date_idx'] > cutoff
            if val_idx.sum() < 50:
                train_idx = pd.Series([True] * len(m_df))
                val_idx = pd.Series([False] * len(m_df))

            local_models = {}
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
                kw['scale_pos_weight'] = scale_pos_weight
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

                if vv.any() and 'early_stopping_rounds' in kw:
                    model = xgb.XGBClassifier(**kw)
                    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
                else:
                    kw_no_es = {k: v for k, v in kw.items() if k != 'early_stopping_rounds'}
                    model = xgb.XGBClassifier(**kw_no_es)
                    model.fit(X_train, y_train)
                local_models[h] = model

            with vcp_train_lock:
                self.models[market] = local_models

        with ThreadPoolExecutor(max_workers=len(MARKETS)) as pool:
            futures = {pool.submit(_train_vcp_market, m, feat_cols): m for m in MARKETS}
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as e:
                    logger.error(f"VCP ML market {futures[f]} failed: {e}")

        self.save_models()
        logger.info(f"VCP ML models trained: {sum(len(v) for v in self.models.values())} total")

    def predict(self, prices_dict: Dict[str, pd.DataFrame],
                indicator_df: pd.DataFrame = None,
                universe: pd.DataFrame = None) -> pd.DataFrame:
        """Predict VCP surge probabilities using market-specific models."""
        if not self.models:
            logger.warning("No VCP ML models loaded, skipping prediction")
            return pd.DataFrame()

        syms, markets, feats = self._batch_features_with_vcp(prices_dict, indicator_df, universe)
        if not feats:
            return pd.DataFrame()

        feat_cols = [c for c in self._ft.ALL_FEATURES + VCP_FEATURES if c in feats[0].columns]

        import warnings
        res_dict = {'symbol': syms, 'market': markets}
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='.*Falling back to prediction using DMatrix.*')
            for h in SURGE_HORIZONS:
                probs = []
                for i, market in enumerate(markets):
                    models = self.models.get(market, {})
                    if h in models:
                        X_row = feats[i][feat_cols]
                        prob = float(models[h].predict_proba(X_row)[0, 1])
                    else:
                        prob = 0.0
                    probs.append(prob)
                res_dict[f'vcp_{h}d'] = probs

        return pd.DataFrame(res_dict)

    def save_models(self):
        try:
            self.model_dir.mkdir(parents=True, exist_ok=True)
            for market, models in self.models.items():
                for h, model in models.items():
                    path = self.model_dir / f"vcp_surge_{market}_{h}d.json"
                    model.get_booster().save_model(str(path))
            logger.info(f"VCP ML models saved to {self.model_dir}")
        except Exception as e:
            logger.error(f"Failed to save VCP ML models: {e}")

    def load_models(self):
        try:
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
                        self.models[market][h] = model
                        logger.debug(f"Loaded VCP ML model for {market} {h}d")
                if not self.models[market]:
                    del self.models[market]
            total = sum(len(v) for v in self.models.values())
            if total:
                logger.info(f"Loaded {total} VCP ML models from {self.model_dir}")
        except Exception as e:
            logger.error(f"Failed to load VCP ML models: {e}")
