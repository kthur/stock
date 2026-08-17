"""Machine Learning Engine - 가격 상승 예측 모델"""

import logging
from typing import Any, List, Optional

import numpy as np
import pandas as pd

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    from xgboost import XGBClassifier

    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

try:
    import lightgbm as lgb

    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False

try:
    import torch
    _HAS_CUDA = torch.cuda.is_available()
except Exception:
    _HAS_CUDA = False

try:
    from hmmlearn.hmm import GaussianHMM

    HAS_HMM = True
except ImportError:
    HAS_HMM = False

try:
    import optuna

    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False

logger = logging.getLogger(__name__)


class MLEngine:
    """기계학습 기반 예측 엔진 (Optuna & HMM 지원)"""

    def __init__(self):
        self.model = None
        self.scaler = None
        self.hmm_model = None
        self.feature_cols = [
            "ret_1",
            "ret_5",
            "ret_20",
            "sma_10_dist",
            "sma_50_dist",
            "rsi_14",
            "volatility_10",
            "macd",
            "macd_signal",
            "bb_upper_dist",
            "bb_lower_dist",
            "atr_14",
            "volume_change",
            "log_volume_ratio",
            "gap_pct",
            "intraday_range",
            "bb_width",
            "rsi_5",
            "macd_hist_norm",
            "roc_10",
            "roc_20",
            "higher_high",
            "higher_low",
            "distance_from_52w_high",
        ]
        if HAS_HMM:
            self.feature_cols.append("hmm_regime")
            self.hmm_model = GaussianHMM(n_components=3, covariance_type="full", n_iter=100, random_state=42)

        # 기본 하이퍼파라미터
        self.model_params = {"n_estimators": 100, "max_depth": 5, "learning_rate": 0.05, "random_state": 42}

        self._init_model()

        if HAS_SKLEARN:
            self.scaler = StandardScaler()

    def _init_model(self):
        self.rf_model = None
        self.xgb_model = None

        xgb_kwargs = dict(self.model_params, eval_metric="logloss")
        lgb_kwargs = dict(self.model_params, verbose=-1)
        if _HAS_CUDA:
            xgb_kwargs['tree_method'] = 'gpu_hist'
            lgb_kwargs['device'] = 'gpu'

        if HAS_SKLEARN and HAS_XGBOOST:
            rf_params = {
                k: v for k, v in self.model_params.items() if k in ["n_estimators", "max_depth", "random_state"]
            }
            self.rf_model = RandomForestClassifier(**rf_params)
            self.xgb_model = XGBClassifier(**xgb_kwargs)
            self.model = (self.rf_model, self.xgb_model)
            logger.info(f"Using ensemble of RandomForest and XGBoost with params: {self.model_params}")
        elif HAS_XGBOOST:
            self.xgb_model = XGBClassifier(**xgb_kwargs)
            self.model = self.xgb_model
            logger.info(f"Using XGBoost fallback for MLEngine with {self.model_params}")
        elif HAS_LIGHTGBM:
            self.model = lgb.LGBMClassifier(**lgb_kwargs)
            logger.info(f"Using LightGBM for MLEngine with {self.model_params}")
        elif HAS_SKLEARN:
            rf_params = {
                k: v for k, v in self.model_params.items() if k in ["n_estimators", "max_depth", "random_state"]
            }
            self.rf_model = RandomForestClassifier(**rf_params)
            self.model = self.rf_model
            logger.info("Using RandomForest fallback for MLEngine")
        else:
            self.model = None
            logger.warning("No ML library installed. MLEngine will not work properly.")

    def _create_features(self, df: pd.DataFrame, is_training: bool = False) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=self.feature_cols)

        df = df.copy()
        col_map = {str(c).lower(): c for c in df.columns}

        close_col = col_map.get("close")
        if not close_col:
            return pd.DataFrame(0.0, index=df.index, columns=self.feature_cols)

        df["close"] = pd.to_numeric(df[close_col], errors="coerce").ffill().bfill().replace(0, np.nan)
        if col_map.get("open"):
            df["open"] = pd.to_numeric(df[col_map["open"]], errors="coerce")
        if col_map.get("high"):
            df["high"] = pd.to_numeric(df[col_map["high"]], errors="coerce")
        if col_map.get("low"):
            df["low"] = pd.to_numeric(df[col_map["low"]], errors="coerce")
        if col_map.get("volume"):
            df["volume"] = pd.to_numeric(df[col_map["volume"]], errors="coerce")

        # 1. 수익률 (Returns)
        df["ret_1"] = df["close"].pct_change(1)
        df["ret_5"] = df["close"].pct_change(5)
        df["ret_20"] = df["close"].pct_change(20)

        # 2. 이동평균 이격도 (SMA Distance)
        df["sma_10"] = df["close"].rolling(10).mean()
        df["sma_50"] = df["close"].rolling(50).mean()
        df["sma_10_dist"] = (df["close"] - df["sma_10"]) / df["sma_10"].replace(0, np.nan)
        df["sma_50_dist"] = (df["close"] - df["sma_50"]) / df["sma_50"].replace(0, np.nan)

        # 3. 간이 RSI (14)
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / (avg_loss + 1e-9)
        df["rsi_14"] = 100.0 - (100.0 / (1.0 + rs))

        # 4. 변동성 (Volatility)
        df["volatility_10"] = df["ret_1"].rolling(10).std()

        # 5. MACD (12, 26, 9)
        ema_12 = df["close"].ewm(span=12, adjust=False).mean()
        ema_26 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = ema_12 - ema_26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

        # 6. Bollinger Bands (20, 2)
        sma_20 = df["close"].rolling(20).mean()
        std_20 = df["close"].rolling(20).std()
        df["bb_upper_dist"] = (df["close"] - (sma_20 + 2 * std_20)) / df["close"]
        df["bb_lower_dist"] = (df["close"] - (sma_20 - 2 * std_20)) / df["close"]

        # 7. ATR (Average True Range) - 14
        if "high" in df.columns and "low" in df.columns:
            tr1 = df["high"] - df["low"]
            tr2 = (df["high"] - df["close"].shift()).abs()
            tr3 = (df["low"] - df["close"].shift()).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            df["atr_14"] = tr.rolling(14).mean() / df["close"]  # 정규화
        else:
            df["atr_14"] = df["volatility_10"]  # 대체값

        # 8. 거래량 변화율
        if "volume" in df.columns:
            df["volume_change"] = df["volume"].pct_change(1).clip(lower=-1, upper=5)
            df["log_volume_ratio"] = np.log1p(df["volume"] / (df["volume"].rolling(20).mean() + 1e-9))
        else:
            df["volume_change"] = 0.0
            df["log_volume_ratio"] = 0.0

        # 10. 향상된 Feature Engineering (영역 5-1)
        # 갭 비율
        if "open" in df.columns:
            df["gap_pct"] = (df["open"] - df["close"].shift(1)) / df["close"].shift(1)
        else:
            df["gap_pct"] = 0.0
        # 일중 변동폭
        if "high" in df.columns and "low" in df.columns:
            df["intraday_range"] = (df["high"] - df["low"]) / df["close"]
        else:
            df["intraday_range"] = df["volatility_10"]
        # BB Width
        sma_20 = df["close"].rolling(20).mean()
        std_20 = df["close"].rolling(20).std()
        df["bb_width"] = 2.0 * std_20 / (sma_20 + 1e-9)
        # RSI 5 (단기)
        delta5 = df["close"].diff()
        gain5 = delta5.where(delta5 > 0, 0.0)
        loss5 = -delta5.where(delta5 < 0, 0.0)
        avg_gain5 = gain5.rolling(window=5).mean()
        avg_loss5 = loss5.rolling(window=5).mean()
        rs5 = avg_gain5 / (avg_loss5 + 1e-9)
        df["rsi_5"] = 100.0 - (100.0 / (1.0 + rs5))
        # MACD 히스토그램 정규화
        ema_12 = df["close"].ewm(span=12, adjust=False).mean()
        ema_26 = df["close"].ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()
        df["macd_hist_norm"] = (macd_line - macd_signal) / (df["close"] + 1e-9)
        # ROC (Rate of Change)
        df["roc_10"] = df["close"].pct_change(10)
        df["roc_20"] = df["close"].pct_change(20)
        # 전고점/전저점 돌파
        df["higher_high"] = (df["high"] > df["high"].shift(1)).astype(float) if "high" in df.columns else 0.0
        df["higher_low"] = (df["low"] > df["low"].shift(1)).astype(float) if "low" in df.columns else 0.0
        # 52주 고점 대비 거리
        df["distance_from_52w_high"] = (df["close"].rolling(252).max() - df["close"]) / (df["close"] + 1e-9)

        # 피처 컬럼 목록 갱신
        self.feature_cols = [
            "ret_1",
            "ret_5",
            "ret_20",
            "sma_10_dist",
            "sma_50_dist",
            "rsi_14",
            "rsi_5",
            "volatility_10",
            "macd",
            "macd_signal",
            "bb_upper_dist",
            "bb_lower_dist",
            "atr_14",
            "volume_change",
            "log_volume_ratio",
            "gap_pct",
            "intraday_range",
            "bb_width",
            "macd_hist_norm",
            "roc_10",
            "roc_20",
            "higher_high",
            "higher_low",
            "distance_from_52w_high",
        ]
        if HAS_HMM and self.hmm_model is not None:
            if "hmm_regime" not in self.feature_cols:
                self.feature_cols.append("hmm_regime")

        # 9. HMM Market Regime
        if HAS_HMM and self.hmm_model is not None:
            # HMM requires no NaNs
            hmm_features = df[["ret_1", "volatility_10"]].fillna(0)
            if is_training:
                try:
                    self.hmm_model.fit(hmm_features.values)
                except Exception as e:
                    logger.warning(f"HMM fit failed: {e}")

            try:
                regimes = self.hmm_model.predict(hmm_features.values)
                df["hmm_regime"] = regimes
            except Exception as e:
                df["hmm_regime"] = 0
                logger.warning(f"HMM predict failed: {e}")

        return df

    def train(self, price_bars: List[Any]) -> bool:
        """과거 데이터를 통해 모델을 학습시킵니다."""
        if self.model is None or not price_bars or len(price_bars) < 100:
            return False

        df = pd.DataFrame(
            [
                {
                    "close": getattr(b, "close", getattr(b, "close", 0)),
                    "high": getattr(b, "high", getattr(b, "close", 0)),
                    "low": getattr(b, "low", getattr(b, "close", 0)),
                    "volume": getattr(b, "volume", 0),
                }
                for b in price_bars
            ]
        )
        df = self._create_features(df, is_training=True)

        # Target: 방향(x) + 크기(o) — 0.5% 이상 상승=1, 0.5% 이상 하락=0, 중간=제외(노이즈 필터)
        forward_ret = df["close"].pct_change(1).shift(-1)
        df["target"] = np.where(forward_ret > 0.005, 1, np.where(forward_ret < -0.005, 0, np.nan))

        df = df.dropna()
        if len(df) < 50:
            return False

        X = df[self.feature_cols]
        y = df["target"]

        try:
            if self.scaler:
                X = self.scaler.fit_transform(X)

            # Fit ensemble models or fallback model
            if isinstance(self.model, tuple):
                self.rf_model.fit(X, y)
                self.xgb_model.fit(X, y)
            else:
                self.model.fit(X, y)
            return True
        except Exception as e:
            logger.error(f"ML training failed: {e}")
            return False

    def predict_prob(self, price_bars: List[Any]) -> float:
        """가장 최근 바를 기준으로 다음 바의 상승 확률을 예측합니다."""
        if self.model is None:
            return 0.5

        # 피처 생성을 위해 최소 60개 데이터 필요
        if len(price_bars) < 60:
            return 0.5

        df = pd.DataFrame(
            [
                {
                    "close": getattr(b, "close", getattr(b, "close", 0)),
                    "high": getattr(b, "high", getattr(b, "close", 0)),
                    "low": getattr(b, "low", getattr(b, "close", 0)),
                    "volume": getattr(b, "volume", 0),
                }
                for b in price_bars[-60:]
            ]
        )
        df = self._create_features(df, is_training=False)

        latest_features = df[self.feature_cols].iloc[-1:]
        if latest_features.isna().any().any():
            return 0.5

        try:
            X = latest_features
            if self.scaler:
                if not hasattr(self.scaler, "mean_"):
                    return 0.5
                X = self.scaler.transform(X)

            if isinstance(self.model, tuple):
                # Weighted average (50/50 soft voting) of RF and XGBoost
                prob_rf = self.rf_model.predict_proba(X)[0][1]
                prob_xgb = self.xgb_model.predict_proba(X)[0][1]
                prob = 0.5 * prob_rf + 0.5 * prob_xgb
            else:
                prob = self.model.predict_proba(X)[0][1]  # 클래스 1(상승)의 확률
            return float(prob)
        except Exception as e:
            logger.error(f"ML prediction failed: {e}")
            return 0.5

    def optimize_hyperparameters(self, price_bars: List[Any], n_trials: int = 10) -> Optional[dict]:
        """Optuna를 사용해 해당 종목의 최적 하이퍼파라미터를 찾습니다."""
        if not HAS_OPTUNA or not HAS_SKLEARN:
            logger.warning("Optuna is not installed or sklearn is missing.")
            return None

        if len(price_bars) < 200:
            logger.warning("Not enough data to run optimization (need > 200 bars).")
            return None

        df = pd.DataFrame(
            [
                {
                    "close": getattr(b, "close", getattr(b, "close", 0)),
                    "high": getattr(b, "high", getattr(b, "close", 0)),
                    "low": getattr(b, "low", getattr(b, "close", 0)),
                    "volume": getattr(b, "volume", 0),
                }
                for b in price_bars
            ]
        )
        df = self._create_features(df, is_training=True)
        forward_ret = df["close"].pct_change(1).shift(-1)
        df["target"] = np.where(forward_ret > 0.005, 1, np.where(forward_ret < -0.005, 0, np.nan))
        df = df.dropna()

        if len(df) < 100:
            return None

        X = df[self.feature_cols].values
        y = df["target"].values

        if self.scaler:
            X = self.scaler.fit_transform(X)

        # Time Series Split for Cross Validation
        from sklearn.metrics import log_loss
        try:
            from src.ai.prediction_model import DateAwareTimeSeriesSplit
        except ImportError:
            try:
                from trading_system.src.ai.prediction_model import DateAwareTimeSeriesSplit  # type: ignore[no-redef]
            except ImportError:
                from sklearn.model_selection import TimeSeriesSplit as DateAwareTimeSeriesSplit  # type: ignore[no-redef]

        def objective(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 50, 300, step=50),
                "max_depth": trial.suggest_int("max_depth", 3, 10),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            }

            xgb_kwargs = dict(params, random_state=42, eval_metric="logloss")
            lgb_kwargs = dict(params, random_state=42, verbose=-1)
            if _HAS_CUDA:
                xgb_kwargs['tree_method'] = 'gpu_hist'
                lgb_kwargs['device'] = 'gpu'

            if HAS_SKLEARN and HAS_XGBOOST:

                class EnsembleObjectiveClassifier:
                    def __init__(self, inner_params):
                        rf_params = {k: v for k, v in inner_params.items() if k in ["n_estimators", "max_depth"]}
                        rf_params["random_state"] = 42
                        self.rf = RandomForestClassifier(**rf_params)
                        self.xgb = XGBClassifier(**xgb_kwargs)

                    def fit(self, X_train, y_train):
                        self.rf.fit(X_train, y_train)
                        self.xgb.fit(X_train, y_train)

                    def predict_proba(self, X_test):
                        p_rf = self.rf.predict_proba(X_test)
                        p_xgb = self.xgb.predict_proba(X_test)
                        return (p_rf + p_xgb) / 2.0

                clf = EnsembleObjectiveClassifier(params)
            elif HAS_XGBOOST:
                clf = XGBClassifier(**xgb_kwargs)
            elif HAS_LIGHTGBM:
                clf = lgb.LGBMClassifier(**lgb_kwargs)
            else:
                rf_params = {k: v for k, v in params.items() if k in ["n_estimators", "max_depth"]}
                clf = RandomForestClassifier(**rf_params, random_state=42)

            tscv = DateAwareTimeSeriesSplit(n_splits=3, gap=5)
            losses = []

            for train_index, test_index in tscv.split(X):
                X_train, X_test = X[train_index], X[test_index]
                y_train, y_test = y[train_index], y[test_index]

                clf.fit(X_train, y_train)
                y_pred = clf.predict_proba(X_test)
                loss = log_loss(y_test, y_pred)
                losses.append(loss)

            return np.mean(losses)

        safe_trials = max(1, min(100, int(n_trials))) if n_trials is not None else 10
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=safe_trials)

        best_params: dict = study.best_params
        logger.info(f"Optimized hyperparameters: {best_params}")
        self.model_params.update(best_params)
        self._init_model()
        return best_params
