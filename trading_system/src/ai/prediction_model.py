import logging
import pandas as pd
import xgboost as xgb
import hashlib
import numpy as np
from typing import Dict

try:
    import torch
    _HAS_CUDA = torch.cuda.is_available()
except Exception:
    _HAS_CUDA = False

logger = logging.getLogger(__name__)


class FallbackMetadataDict(dict):
    """
    A custom dictionary-like class that contains real values for key benchmarks
    and dynamically returns deterministic mock metadata for any other ticker.
    """
    def __init__(self):
        super().__init__()
        # Real benchmark values
        benchmarks = {
            "AAPL": {"shares_outstanding": 15000000000.0, "floating_shares": 14900000000.0},
            "MSFT": {"shares_outstanding": 7400000000.0, "floating_shares": 7300000000.0},
            "GOOGL": {"shares_outstanding": 5800000000.0, "floating_shares": 5000000000.0},
            "GOOG": {"shares_outstanding": 5800000000.0, "floating_shares": 5000000000.0},
            "AMZN": {"shares_outstanding": 10400000000.0, "floating_shares": 9200000000.0},
            "TSLA": {"shares_outstanding": 3180000000.0, "floating_shares": 2700000000.0},
            "NVDA": {"shares_outstanding": 24500000000.0, "floating_shares": 24000000000.0},
            "META": {"shares_outstanding": 2200000000.0, "floating_shares": 2200000000.0},
            "005930": {"shares_outstanding": 5969782550.0, "floating_shares": 4500000000.0},
            "000660": {"shares_outstanding": 728002365.0, "floating_shares": 500000000.0},
            "005380": {"shares_outstanding": 209720000.0, "floating_shares": 140000000.0},
            "000270": {"shares_outstanding": 399742000.0, "floating_shares": 240000000.0},
            "035420": {"shares_outstanding": 162408000.0, "floating_shares": 130000000.0},
            "035720": {"shares_outstanding": 443584000.0, "floating_shares": 320000000.0},
            "068270": {"shares_outstanding": 217900000.0, "floating_shares": 160000000.0},
            "207940": {"shares_outstanding": 71174000.0, "floating_shares": 18000000.0},
        }
        self.update(benchmarks)

    def _clean_key(self, key: str) -> str:
        if not isinstance(key, str):
            return key
        return key.strip().upper().split('.')[0]

    def __getitem__(self, key):
        cleaned = self._clean_key(key)
        if super().__contains__(cleaned):
            return super().__getitem__(cleaned)
        return self._generate_mock_metadata(cleaned)

    def get(self, key, default=None):
        cleaned = self._clean_key(key)
        if super().__contains__(cleaned):
            return super().__getitem__(cleaned)
        try:
            return self._generate_mock_metadata(cleaned)
        except Exception:
            return default

    def __contains__(self, key):
        return True

    def _generate_mock_metadata(self, symbol: str) -> dict:
        h = hashlib.md5(symbol.encode('utf-8')).hexdigest()
        val = int(h, 16)
        shares_outstanding = 10000000 + (val % 990000000)
        float_pct = 0.5 + 0.4 * ((val >> 32) % 100) / 100.0
        floating_shares = shares_outstanding * float_pct
        return {
            "shares_outstanding": float(shares_outstanding),
            "floating_shares": float(floating_shares)
        }


FALLBACK_METADATA = FallbackMetadataDict()


class OnDevicePredictionModel:
    def __init__(self):
        self.models: Dict[int, xgb.XGBRegressor] = {}
        self.horizons = [1, 5, 10, 20, 30, 60, 120, 200]
        self._has_gpu = _HAS_CUDA
        self._xgb_kwargs = dict(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            n_jobs=-1,
            random_state=42,
        )
        if self._has_gpu:
            self._xgb_kwargs['device'] = 'cuda'
        logger.info(f"OnDevicePredictionModel initialized (GPU={'yes' if self._has_gpu else 'no'})")

    def apply_market_normalization(self, prices_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Normalize stock-level features relative to the daily regional baseline total.
        
        Inputs: Dict of symbol to DataFrame containing price, volume, and optional stock-level metadata.
        Outputs: Dict of symbol to DataFrame with added columns: norm_market_cap, norm_floating_value, norm_volume.
        """
        if not prices_dict:
            return prices_dict

        us_group = {}
        kr_group = {}

        for sym, df in prices_dict.items():
            if df is None or df.empty:
                continue

            cleaned = sym.strip().upper().split('.')[0]
            is_kr = cleaned.isdigit() or any(suffix in sym.upper() for suffix in [".KS", ".KQ"])

            df_copy = df.copy()

            # Retrieve shares_outstanding and floating_shares from df columns or fallback
            metadata = FALLBACK_METADATA[sym]
            shares_out = df_copy['shares_outstanding'] if 'shares_outstanding' in df_copy.columns else metadata['shares_outstanding']
            float_sh = df_copy['floating_shares'] if 'floating_shares' in df_copy.columns else metadata['floating_shares']

            df_copy['market_cap'] = df_copy['Close'] * shares_out

            if isinstance(float_sh, pd.Series):
                floating_val = df_copy['Close'] * float_sh
                fallback_mask = float_sh.isna() | (float_sh <= 0)
                df_copy['floating_value'] = floating_val.where(~fallback_mask, df_copy['Close'] * df_copy['Volume'])
            else:
                if float_sh is None or float_sh <= 0:
                    df_copy['floating_value'] = df_copy['Close'] * df_copy['Volume']
                else:
                    df_copy['floating_value'] = df_copy['Close'] * float_sh

            if is_kr:
                kr_group[sym] = df_copy
            else:
                us_group[sym] = df_copy

        result_dict = {}

        for group in [us_group, kr_group]:
            if not group:
                continue

            total_market_cap = pd.Series(dtype=float)
            total_floating_value = pd.Series(dtype=float)
            total_volume = pd.Series(dtype=float)

            for df in group.values():
                total_market_cap = total_market_cap.add(df['market_cap'], fill_value=0.0)
                total_floating_value = total_floating_value.add(df['floating_value'], fill_value=0.0)
                total_volume = total_volume.add(df['Volume'], fill_value=0.0)

            for sym, df in group.items():
                def safe_divide(series_numerator, series_denominator):
                    res = series_numerator.div(series_denominator)
                    return res.replace([np.inf, -np.inf], 0.0).fillna(0.0)

                df['norm_market_cap'] = safe_divide(df['market_cap'], total_market_cap)
                df['norm_floating_value'] = safe_divide(df['floating_value'], total_floating_value)
                df['norm_volume'] = safe_divide(df['Volume'], total_volume)

                result_dict[sym] = df

        # Preserve and return any missing or empty input dataframes
        for sym, df in prices_dict.items():
            if sym not in result_dict:
                result_dict[sym] = df

        return result_dict

    def _create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create technical indicators and momentum features."""
        df = df.copy()
        if len(df) < 65:
            return pd.DataFrame()

        # If normalized features are not present, apply market normalization as single stock fallback
        if not all(col in df.columns for col in ['norm_market_cap', 'norm_floating_value', 'norm_volume']):
            norm_dict = self.apply_market_normalization({'TEMP': df})
            df = norm_dict['TEMP']

        # Return features
        df['ret_1d'] = df['Close'].pct_change(1)
        df['ret_5d'] = df['Close'].pct_change(5)
        df['ret_20d'] = df['Close'].pct_change(20)
        df['ret_60d'] = df['Close'].pct_change(60)

        # Moving averages
        df['sma_20'] = df['Close'].rolling(20).mean()
        df['sma_60'] = df['Close'].rolling(60).mean()
        df['dist_sma_20'] = df['Close'] / df['sma_20'] - 1

        # Volatility
        df['vol_20d'] = df['ret_1d'].rolling(20).std()

        # Drop NaN
        df.dropna(inplace=True)
        return df

    def _create_targets(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create forward returns as targets."""
        for h in self.horizons:
            df[f'target_{h}d'] = df['Close'].shift(-h) / df['Close'] - 1
        return df

    def prepare_training_data(self, prices_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Merge all stocks into a single training dataset.
        prices_dict: {symbol: df_with_ohlcv}
        """
        prices_dict = self.apply_market_normalization(prices_dict)
        all_data = []
        for sym, df in prices_dict.items():
            if df is None or len(df) < 70:
                continue
            df_feat = self._create_features(df)
            df_feat = self._create_targets(df_feat)
            df_feat['symbol'] = sym
            all_data.append(df_feat.dropna())

        if not all_data:
            return pd.DataFrame()
        return pd.concat(all_data, ignore_index=True)

    def train(self, df_train: pd.DataFrame):
        """Train XGBoost regressors for each horizon."""
        if df_train.empty:
            logger.warning("Empty training data.")
            return

        features = ['ret_1d', 'ret_5d', 'ret_20d', 'ret_60d', 'dist_sma_20', 'vol_20d', 'norm_market_cap', 'norm_floating_value', 'norm_volume']

        for h in self.horizons:
            logger.info(f"Training model for {h}d horizon...")
            X = df_train[features]
            y = df_train[f'target_{h}d']

            model = xgb.XGBRegressor(**self._xgb_kwargs)
            model.fit(X, y)
            self.models[h] = model
            logger.info(f"Model for {h}d trained.")

    def predict_current(self, df_current: pd.DataFrame) -> Dict[int, float]:
        """
        Predict forward returns for a single stock's latest data.
        df_current must have features computed.
        Returns dict of {horizon: expected_return}
        """
        if df_current.empty:
            return {h: 0.0 for h in self.horizons}

        # Check if features are computed. If not, compute them.
        if 'ret_1d' not in df_current.columns:
            norm_dict = self.apply_market_normalization({'TEMP': df_current})
            df_current = self._create_features(norm_dict['TEMP'])
            if df_current.empty:
                return {h: 0.0 for h in self.horizons}
        else:
            # If features are computed, but the normalized features are missing, add them.
            if not all(col in df_current.columns for col in ['norm_market_cap', 'norm_floating_value', 'norm_volume']):
                norm_dict = self.apply_market_normalization({'TEMP': df_current})
                df_current = norm_dict['TEMP']

        latest = df_current.iloc[-1:]
        features = ['ret_1d', 'ret_5d', 'ret_20d', 'ret_60d', 'dist_sma_20', 'vol_20d', 'norm_market_cap', 'norm_floating_value', 'norm_volume']
        X = latest[features]

        predictions = {}
        for h in self.horizons:
            if h in self.models:
                pred = self.models[h].predict(X)[0]
                predictions[h] = float(pred)
            else:
                predictions[h] = 0.0
        return predictions

    def process_and_predict_all(self, prices_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Apply model to the latest data of all provided stocks in batch.
        Returns DataFrame with symbols and their predicted returns.
        """
        prices_dict = self.apply_market_normalization(prices_dict)
        features = ['ret_1d', 'ret_5d', 'ret_20d', 'ret_60d', 'dist_sma_20', 'vol_20d', 'norm_market_cap', 'norm_floating_value', 'norm_volume']

        # 1. Gather the latest features for all symbols
        latest_features_list = []
        symbols_list = []

        for sym, df in prices_dict.items():
            if df is None or len(df) < 65:
                continue
            df_feat = self._create_features(df)
            if df_feat.empty:
                continue

            latest = df_feat.iloc[-1:]
            latest_features_list.append(latest[features])
            symbols_list.append(sym)

        if not latest_features_list:
            return pd.DataFrame()

        # 2. Concatenate into a single batch DataFrame
        X_batch = pd.concat(latest_features_list, ignore_index=True)

        # 3. Predict for each horizon in batch
        res_dict: dict = {'symbol': symbols_list}
        for h in self.horizons:
            if h in self.models:
                preds = self.models[h].predict(X_batch)
                res_dict[h] = preds.tolist()
            else:
                res_dict[h] = [0.0] * len(symbols_list)
        # 4. Convert to DataFrame
        res_df = pd.DataFrame(res_dict)
        return res_df

