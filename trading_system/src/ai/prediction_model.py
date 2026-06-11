import logging
import pandas as pd
import xgboost as xgb
from typing import Dict

logger = logging.getLogger(__name__)

class OnDevicePredictionModel:
    def __init__(self):
        self.models: Dict[int, xgb.XGBRegressor] = {}
        self.horizons = [1, 5, 10, 20, 30, 60]

    def _create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create technical indicators and momentum features."""
        df = df.copy()
        if len(df) < 65:
            return pd.DataFrame()

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

        features = ['ret_1d', 'ret_5d', 'ret_20d', 'ret_60d', 'dist_sma_20', 'vol_20d']

        for h in self.horizons:
            logger.info(f"Training model for {h}d horizon...")
            X = df_train[features]
            y = df_train[f'target_{h}d']

            model = xgb.XGBRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                n_jobs=-1, # use all cores
                random_state=42
            )
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

        latest = df_current.iloc[-1:]
        features = ['ret_1d', 'ret_5d', 'ret_20d', 'ret_60d', 'dist_sma_20', 'vol_20d']
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
        features = ['ret_1d', 'ret_5d', 'ret_20d', 'ret_60d', 'dist_sma_20', 'vol_20d']

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

