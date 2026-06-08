"""Machine Learning Engine - 가격 상승 예측 모델"""

import pandas as pd
import numpy as np
from typing import List, Any, Optional
import logging

try:
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
    from hmmlearn.hmm import GaussianHMM
    HAS_HMM = True
except ImportError:
    HAS_HMM = False

try:
    import optuna
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False

if not HAS_XGBOOST and not HAS_LIGHTGBM and HAS_SKLEARN:
    from sklearn.ensemble import RandomForestClassifier

logger = logging.getLogger(__name__)

class MLEngine:
    """기계학습 기반 예측 엔진 (Optuna & HMM 지원)"""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.hmm_model = None
        self.feature_cols = [
            'ret_1', 'ret_5', 'sma_10_dist', 'sma_50_dist', 
            'rsi_14', 'volatility_10', 'macd', 'macd_signal', 
            'bb_upper_dist', 'bb_lower_dist', 'atr_14', 'volume_change'
        ]
        if HAS_HMM:
            self.feature_cols.append('hmm_regime')
            self.hmm_model = GaussianHMM(n_components=3, covariance_type="full", n_iter=100, random_state=42)
        
        # 기본 하이퍼파라미터
        self.model_params = {
            'n_estimators': 100,
            'max_depth': 5,
            'learning_rate': 0.05,
            'random_state': 42
        }
        
        self._init_model()
            
        if HAS_SKLEARN:
            self.scaler = StandardScaler()
            
    def _init_model(self):
        if HAS_XGBOOST:
            self.model = XGBClassifier(**self.model_params, eval_metric='logloss')
            logger.info(f"Using XGBoost for MLEngine with {self.model_params}")
        elif HAS_LIGHTGBM:
            self.model = lgb.LGBMClassifier(**self.model_params)
            logger.info(f"Using LightGBM for MLEngine with {self.model_params}")
        elif HAS_SKLEARN:
            rf_params = {k: v for k, v in self.model_params.items() if k in ['n_estimators', 'max_depth', 'random_state']}
            self.model = RandomForestClassifier(**rf_params)
            logger.info("Using RandomForest for MLEngine")
        else:
            logger.warning("No ML library installed. MLEngine will not work properly.")
            
    def _create_features(self, df: pd.DataFrame, is_training: bool = False) -> pd.DataFrame:
        df = df.copy()
        
        # 1. 수익률 (Returns)
        df['ret_1'] = df['close'].pct_change(1)
        df['ret_5'] = df['close'].pct_change(5)
        
        # 2. 이동평균 이격도 (SMA Distance)
        df['sma_10'] = df['close'].rolling(10).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        df['sma_10_dist'] = (df['close'] - df['sma_10']) / df['sma_10']
        df['sma_50_dist'] = (df['close'] - df['sma_50']) / df['sma_50']
        
        # 3. 간이 RSI (14)
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / (avg_loss + 1e-9)
        df['rsi_14'] = 100.0 - (100.0 / (1.0 + rs))
        
        # 4. 변동성 (Volatility)
        df['volatility_10'] = df['ret_1'].rolling(10).std()
        
        # 5. MACD (12, 26, 9)
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # 6. Bollinger Bands (20, 2)
        sma_20 = df['close'].rolling(20).mean()
        std_20 = df['close'].rolling(20).std()
        df['bb_upper_dist'] = (df['close'] - (sma_20 + 2 * std_20)) / df['close']
        df['bb_lower_dist'] = (df['close'] - (sma_20 - 2 * std_20)) / df['close']
        
        # 7. ATR (Average True Range) - 14
        if 'high' in df.columns and 'low' in df.columns:
            tr1 = df['high'] - df['low']
            tr2 = (df['high'] - df['close'].shift()).abs()
            tr3 = (df['low'] - df['close'].shift()).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            df['atr_14'] = tr.rolling(14).mean() / df['close'] # 정규화
        else:
            df['atr_14'] = df['volatility_10'] # 대체값
            
        # 8. 거래량 변화율
        if 'volume' in df.columns:
            df['volume_change'] = df['volume'].pct_change(1).clip(lower=-1, upper=5)
        else:
            df['volume_change'] = 0.0
            
        # 9. HMM Market Regime
        if HAS_HMM and self.hmm_model is not None:
            # HMM requires no NaNs
            hmm_features = df[['ret_1', 'volatility_10']].fillna(0)
            if is_training:
                try:
                    self.hmm_model.fit(hmm_features.values)
                except Exception as e:
                    logger.warning(f"HMM fit failed: {e}")
            
            try:
                regimes = self.hmm_model.predict(hmm_features.values)
                df['hmm_regime'] = regimes
            except Exception as e:
                df['hmm_regime'] = 0
                logger.warning(f"HMM predict failed: {e}")
                
        return df
        
    def train(self, price_bars: List[Any]) -> bool:
        """과거 데이터를 통해 모델을 학습시킵니다."""
        if self.model is None or not price_bars or len(price_bars) < 100:
            return False
            
        df = pd.DataFrame([{
            'close': getattr(b, 'close', getattr(b, 'close', 0)), 
            'high': getattr(b, 'high', getattr(b, 'close', 0)),
            'low': getattr(b, 'low', getattr(b, 'close', 0)),
            'volume': getattr(b, 'volume', 0)
        } for b in price_bars])
        df = self._create_features(df, is_training=True)
        
        # Target: 다음날 종가가 오늘 종가보다 높은지 (1=상승, 0=하락)
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        
        df = df.dropna()
        if len(df) < 50:
            return False
            
        X = df[self.feature_cols]
        y = df['target']
        
        try:
            if self.scaler:
                X = self.scaler.fit_transform(X)
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
            
        df = pd.DataFrame([{
            'close': getattr(b, 'close', getattr(b, 'close', 0)), 
            'high': getattr(b, 'high', getattr(b, 'close', 0)),
            'low': getattr(b, 'low', getattr(b, 'close', 0)),
            'volume': getattr(b, 'volume', 0)
        } for b in price_bars[-60:]])
        df = self._create_features(df, is_training=False)
        
        latest_features = df[self.feature_cols].iloc[-1:]
        if latest_features.isna().any().any():
            return 0.5
            
        try:
            X = latest_features
            if self.scaler:
                if not hasattr(self.scaler, 'mean_'):
                    return 0.5
                X = self.scaler.transform(X)
                
            prob = self.model.predict_proba(X)[0][1] # 클래스 1(상승)의 확률
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
            
        df = pd.DataFrame([{
            'close': getattr(b, 'close', getattr(b, 'close', 0)), 
            'high': getattr(b, 'high', getattr(b, 'close', 0)),
            'low': getattr(b, 'low', getattr(b, 'close', 0)),
            'volume': getattr(b, 'volume', 0)
        } for b in price_bars])
        df = self._create_features(df, is_training=True)
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        df = df.dropna()
        
        if len(df) < 100:
            return None
            
        X = df[self.feature_cols].values
        y = df['target'].values
        
        if self.scaler:
            X = self.scaler.fit_transform(X)
            
        # Time Series Split for Cross Validation
        from sklearn.model_selection import TimeSeriesSplit
        from sklearn.metrics import log_loss
        
        def objective(trial):
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 50, 300, step=50),
                'max_depth': trial.suggest_int('max_depth', 3, 10),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True)
            }
            
            if HAS_XGBOOST:
                clf = XGBClassifier(**params, random_state=42, eval_metric='logloss')
            elif HAS_LIGHTGBM:
                clf = lgb.LGBMClassifier(**params, random_state=42)
            else:
                rf_params = {k:v for k,v in params.items() if k in ['n_estimators', 'max_depth']}
                clf = RandomForestClassifier(**rf_params, random_state=42)
                
            tscv = TimeSeriesSplit(n_splits=3)
            losses = []
            
            for train_index, test_index in tscv.split(X):
                X_train, X_test = X[train_index], X[test_index]
                y_train, y_test = y[train_index], y[test_index]
                
                clf.fit(X_train, y_train)
                y_pred = clf.predict_proba(X_test)
                loss = log_loss(y_test, y_pred)
                losses.append(loss)
                
            return np.mean(losses)
            
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(direction='minimize')
        study.optimize(objective, n_trials=n_trials)
        
        best_params: dict = study.best_params
        logger.info(f"Optimized hyperparameters: {best_params}")
        self.model_params.update(best_params)
        self._init_model()
        return best_params
