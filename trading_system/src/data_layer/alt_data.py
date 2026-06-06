import yfinance as yf
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AlternativeDataClient:
    """대체 데이터(Alternative Data) 수집 모듈
    VIX 지수, 풋/콜 비율, 거시경제 지표 등을 수집하여 시장 레짐(Market Regime) 파악에 활용합니다.
    """
    
    def __init__(self):
        self._cache = {}

    def fetch_vix(self) -> float:
        """현재 VIX(변동성 지수) 조회"""
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period="1d")
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
            return 20.0 # fallback
        except Exception as e:
            logger.error(f"VIX 조회 실패: {e}")
            return 20.0

    def fetch_fear_and_greed_proxy(self) -> str:
        """VIX 기반 공포 탐욕 지수 프록시 계산"""
        vix = self.fetch_vix()
        if vix >= 30:
            return "EXTREME_FEAR"
        elif vix >= 20:
            return "FEAR"
        elif vix <= 15:
            return "GREED"
        elif vix <= 12:
            return "EXTREME_GREED"
        return "NEUTRAL"

    def get_market_regime(self) -> Dict[str, Any]:
        """시장의 전반적인 레짐(체제) 정보 반환"""
        vix = self.fetch_vix()
        sentiment = self.fetch_fear_and_greed_proxy()
        
        return {
            "vix": vix,
            "sentiment": sentiment,
            "is_high_volatility": vix > 25,
            "is_bull_market": sentiment in ["GREED", "EXTREME_GREED"]
        }
