"""Machine Learning Engine - 가격 상승 예측 모델"""

import pandas as pd
from typing import List, Any
import logging

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

logger = logging.getLogger(__name__)

class MLEngine:
    """기계학습 기반 예측 엔진"""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_cols = ['ret_1', 'ret_5', 'sma_10_dist', 'sma_50_dist', 'rsi_14', 'volatility_10']
        
        if HAS_SKLEARN:
            # 빠른 학습과 과적합 방지를 위한 얕은 랜덤 포레스트
            self.model = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
            self.scaler = StandardScaler()
        else:
            logger.warning("scikit-learn is not installed. MLEngine will not work properly.")
            
    def _create_features(self, df: pd.DataFrame) -> pd.DataFrame:
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
        # 0 나누기 방지
        rs = avg_gain / (avg_loss + 1e-9)
        df['rsi_14'] = 100.0 - (100.0 / (1.0 + rs))
        
        # 4. 변동성 (Volatility)
        df['volatility_10'] = df['ret_1'].rolling(10).std()
        
        return df
        
    def train(self, price_bars: List[Any]) -> bool:
        """과거 데이터를 통해 모델을 학습시킵니다."""
        if not HAS_SKLEARN or not price_bars or len(price_bars) < 100:
            return False
            
        df = pd.DataFrame([{'close': getattr(b, 'close', b), 'volume': getattr(b, 'volume', 0)} for b in price_bars])
        df = self._create_features(df)
        
        # Target: 다음날 종가가 오늘 종가보다 높은지 (1=상승, 0=하락)
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        
        df = df.dropna()
        if len(df) < 50:
            return False
            
        X = df[self.feature_cols]
        y = df['target']
        
        try:
            X_scaled = self.scaler.fit_transform(X)
            self.model.fit(X_scaled, y)
            return True
        except Exception as e:
            logger.error(f"ML training failed: {e}")
            return False
        
    def predict_prob(self, price_bars: List[Any]) -> float:
        """가장 최근 바를 기준으로 다음 바의 상승 확률을 예측합니다."""
        if not HAS_SKLEARN or self.model is None or self.scaler is None:
            return 0.5
            
        # 피처 생성을 위해 최소 60개 데이터 필요
        if len(price_bars) < 60:
            return 0.5
            
        df = pd.DataFrame([{'close': getattr(b, 'close', b), 'volume': getattr(b, 'volume', 0)} for b in price_bars[-60:]])
        df = self._create_features(df)
        
        latest_features = df[self.feature_cols].iloc[-1:]
        if latest_features.isna().any().any():
            return 0.5
            
        try:
            # fit 되어있는지 확인
            if not hasattr(self.scaler, 'mean_'):
                return 0.5
                
            X_scaled = self.scaler.transform(latest_features)
            prob = self.model.predict_proba(X_scaled)[0][1] # 클래스 1(상승)의 확률
            return float(prob)
        except Exception as e:
            logger.error(f"ML prediction failed: {e}")
            return 0.5
