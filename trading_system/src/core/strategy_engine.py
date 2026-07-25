"""Strategy Engine - 매매 전략 및 최적화"""

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from src.utils import EventBus
from src.utils.indicators import calc_ema_list, calc_macd
from src.utils.indicators import calc_rsi as _calc_rsi_shared

logger = logging.getLogger(__name__)


class TradeSignal(Enum):
    """매매 신호"""

    BUY = 1
    SELL = -1
    HOLD = 0

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            return self.name == other
        return super().__eq__(other)


class MarketRegime(Enum):
    STRONG_BULL = "strong_bull"
    WEAK_BULL = "weak_bull"
    WEAK_BEAR = "weak_bear"
    STRONG_BEAR = "strong_bear"


REGIME_THRESHOLDS = {
    "strong_bull": {
        "buy": 0.48,
        "sell": 0.38,
        "min_buy_votes": 1,
        "position_pct": 1.0,
        "trail_pct": 0.08,
        "cash_target": 0.10,
    },
    "weak_bull": {
        "buy": 0.52,
        "sell": 0.42,
        "min_buy_votes": 1,
        "position_pct": 0.8,
        "trail_pct": 0.06,
        "cash_target": 0.20,
    },
    "weak_bear": {
        "buy": 0.62,
        "sell": 0.45,
        "min_buy_votes": 2,
        "position_pct": 0.5,
        "trail_pct": 0.04,
        "cash_target": 0.40,
    },
    "strong_bear": {
        "buy": 0.70,
        "sell": 0.50,
        "min_buy_votes": 3,
        "position_pct": 0.25,
        "trail_pct": 0.03,
        "cash_target": 0.70,
    },
}


@dataclass
class StrategyResult:
    """전략 실행 결과"""

    symbol: str
    signal: TradeSignal
    price: float
    confidence: float  # 0.0 ~ 1.0
    reason: str
    timestamp: datetime
    signal_name: str = "strategy"


class HybridStrategyEngine:
    SIGNAL_NAMES = ["sentiment", "technical", "ml", "rl", "darkpool", "llm", "global_market", "cash_ratio", "macro"]

    def __init__(
        self,
        event_bus: EventBus | None = None,
        ml_engine: Any = None,
        rl_engine: Any = None,
        alt_client: Any = None,
        darkpool: Any = None,
        llm_earnings: Any = None,
        stat_arb: Any = None,
        hft_engine: Any = None,
        global_market: Any = None,
        relative_strength: Any = None,
        portfolio: Any = None,
        style_rotator: Any = None,
        sentiment_weight: float = 0.20,
        technical_weight: float = 0.30,
        ml_weight: float = 0.30,
        rl_weight: float = 0.1,
        darkpool_weight: float = 0.0,
        llm_weight: float = 0.1,
        global_market_weight: float = 0.0,
        cash_ratio_weight: float = 0.08,
        macro_weight: float = 0.08,
        spread_threshold: float = 0.001,
        buy_price_threshold: float = 1.01,
        sell_threshold: float = 0.4,
        weight_adaptation_rate: float = 0.05,
        weight_adaptation_window: int = 15,
    ) -> None:
        self.logger = logger
        self.results_history: deque = deque(maxlen=1000)
        self.subscribers: List[Callable] = []
        self.event_bus = event_bus
        self.ml_engine = ml_engine
        self.rl_engine = rl_engine
        self.alt_client = alt_client
        self.darkpool = darkpool
        self.llm_earnings = llm_earnings
        self.stat_arb = stat_arb
        self.hft_engine = hft_engine
        self.global_market = global_market
        self.relative_strength = relative_strength
        self.portfolio = portfolio
        self.style_rotator = style_rotator

        self.volume_threshold = 1000000
        self.sentiment_weight = sentiment_weight
        self.technical_weight = technical_weight
        self.ml_weight = ml_weight
        self.rl_weight = rl_weight
        self.darkpool_weight = darkpool_weight
        self.llm_weight = llm_weight
        self.global_market_weight = global_market_weight
        self.cash_ratio_weight = cash_ratio_weight
        self.macro_weight = macro_weight
        self.spread_threshold = spread_threshold
        self.buy_price_threshold = buy_price_threshold
        self.sell_threshold = sell_threshold
        self.weight_adaptation_rate = weight_adaptation_rate
        self.weight_adaptation_window = weight_adaptation_window

        self._signal_performance: Dict[str, List[bool]] = {s: [] for s in self.SIGNAL_NAMES}
        self._signal_scores: Dict[str, float] = {}
        self._active_regime: str = MarketRegime.WEAK_BULL.value
        self._last_regime_adjustments: dict | None = None

        self.strategy_parameters: Dict[str, Any] = {}
        self._normalize_weights()
        self._baseline_weights = {
            "sentiment_weight": self.sentiment_weight,
            "technical_weight": self.technical_weight,
            "ml_weight": self.ml_weight,
            "rl_weight": self.rl_weight,
            "darkpool_weight": self.darkpool_weight,
            "llm_weight": self.llm_weight,
            "global_market_weight": self.global_market_weight,
            "cash_ratio_weight": self.cash_ratio_weight,
        }
        self._baseline_sell_threshold = self.sell_threshold

    def subscribe(self, callback: Callable) -> None:
        """전략 신호 구독"""
        self.subscribers.append(callback)

    @staticmethod
    def _calc_sma(closes: list, period: int) -> list:
        """단순이동평균(SMA) 계산"""
        from src.utils.indicators import calc_sma

        res = calc_sma(closes, period)
        return list(res) if isinstance(res, (list, tuple)) else []

    def _calc_ema(self, data: list, period: int) -> list:
        """지수이동평균(EMA) 계산"""
        res = calc_ema_list(data, period)
        return list(res) if isinstance(res, (list, tuple)) else []

    def _calc_rsi(self, closes: list, window: int = 14) -> float:
        """현재 RSI 값 계산 (Wilder 방식)"""
        return float(_calc_rsi_shared(closes, window))

    def _calc_macd_histogram(self, closes: list) -> float:
        """현재 MACD 히스토그램 값 계산 (EMA12-EMA26-Signal9)"""
        return float(calc_macd(closes, 12, 26, 9))

    def _calc_bollinger_position(self, closes: list, period: int = 20, std_mult: float = 2.0) -> float:
        """볼린저밴드 내 현재 위치 (0.0=하단, 0.5=중심, 1.0=상단)"""
        if len(closes) < period:
            return 0.5
        sub = closes[-period:]
        sma = sum(sub) / len(sub)
        variance = sum((c - sma) ** 2 for c in sub) / len(sub)
        std_dev = variance**0.5
        if std_dev == 0:
            return 0.5
        upper = sma + std_mult * std_dev
        lower = sma - std_mult * std_dev
        band_width = upper - lower
        if band_width == 0:
            return 0.5
        return float(max(0.0, min(1.0, (closes[-1] - lower) / band_width)))

    def _compute_technical_indicators(self, price_bars: List[Any], volume_bars: Optional[List[Any]] = None, floating_shares: Optional[float] = None) -> Dict[str, Any]:
        """과거 가격 데이터로부터 기술적 지표 종합 점수 산출"""
        closes = []
        volumes = []

        # Extract closes and volumes from price_bars if not provided in volume_bars
        for b in price_bars:
            if isinstance(b, (int, float)):
                closes.append(float(b))
            elif isinstance(b, dict):
                closes.append(float(b.get("close") or b.get("Close") or 0.0))
                if "volume" in b:
                    volumes.append(float(b["volume"] or 0.0))
                elif "Volume" in b:
                    volumes.append(float(b["Volume"] or 0.0))
            else:
                closes.append(float(getattr(b, "close", getattr(b, "Close", 0.0)) or 0.0))
                if hasattr(b, "volume"):
                    volumes.append(float(getattr(b, "volume", 0.0) or 0.0))
                elif hasattr(b, "Volume"):
                    volumes.append(float(getattr(b, "Volume", 0.0) or 0.0))

        if len(closes) < 20:
            return {"score": 0.5, "signal": TradeSignal.HOLD, "details": {}}

        # If volume_bars is explicitly provided, use it instead
        if volume_bars is not None:
            volumes = []
            for v in volume_bars:
                if isinstance(v, (int, float)):
                    volumes.append(float(v))
                elif isinstance(v, dict):
                    volumes.append(float(v.get("volume") or v.get("Volume") or 0.0))
                else:
                    volumes.append(float(getattr(v, "volume", getattr(v, "Volume", 0.0)) or 0.0))

        # RSI (14) - 보다 보수적인 임계값 적용
        rsi = self._calc_rsi(closes)
        if rsi < 25:
            rsi_score = 0.9
        elif rsi < 35:
            rsi_score = 0.6
        elif rsi > 75:
            rsi_score = 0.1
        elif rsi > 65:
            rsi_score = 0.3
        else:
            rsi_score = 0.5

        # MACD histogram
        macd_hist = self._calc_macd_histogram(closes)
        prev_closes = closes[:-1] if len(closes) > 35 else closes
        prev_macd_hist = self._calc_macd_histogram(prev_closes) if len(prev_closes) >= 35 else 0.0

        if prev_macd_hist < 0 and macd_hist > 0:
            macd_score = 0.9  # 골든크로스
        elif prev_macd_hist > 0 and macd_hist < 0:
            macd_score = 0.1  # 데드크로스
        elif macd_hist > 0:
            macd_score = 0.65
        elif macd_hist < 0:
            macd_score = 0.35
        else:
            macd_score = 0.5

        # EMA 정배열 (EMA20 > EMA50)
        ema20 = self._calc_ema(closes, 20)
        ema50 = self._calc_ema(closes, 50) if len(closes) >= 50 else ema20
        if ema20[-1] > ema50[-1]:
            ema_score = 0.7
        elif ema20[-1] < ema50[-1]:
            ema_score = 0.3
        else:
            ema_score = 0.5

        # 볼린저밴드 위치
        bb_pos = self._calc_bollinger_position(closes)
        if bb_pos < 0.15:
            bb_score = 0.85  # 하단 이탈 → 반등 기대
        elif bb_pos > 0.85:
            bb_score = 0.15  # 상단 이탈 → 조정 기대
        else:
            bb_score = 0.5

        # trend strength: EMA slope + cross position
        ema20_slope = (ema20[-1] - ema20[-5]) / max(ema20[-5], 1e-10) if len(ema20) >= 5 else 0.0
        trend_bias = 0.5
        if len(closes) >= 50 and len(ema20) >= 5:
            if ema20[-1] > ema50[-1] and ema20_slope > 0.001:
                trend_bias = 0.8
            elif ema20[-1] < ema50[-1] and ema20_slope < -0.001:
                trend_bias = 0.2

        combined = rsi_score * 0.25 + macd_score * 0.30 + ema_score * 0.25 + bb_score * 0.15
        # 추세 바이어스 (신규 5% 독립 가중치)
        combined = combined * 0.95 + trend_bias * 0.05

        # Define price trend for volume expansion
        price_trend_positive = (ema20[-1] > ema50[-1] if len(closes) >= 50 else False) or macd_hist > 0
        price_trend_negative = (ema20[-1] < ema50[-1] if len(closes) >= 50 else False) or macd_hist < 0

        # Volume expansion bonus/penalty
        volume_5sma = None
        volume_20sma = None
        volume_expansion_active = False
        volume_bonus_applied = 0.0

        if len(volumes) >= 20:
            volume_5sma = sum(volumes[-5:]) / 5.0
            volume_20sma = sum(volumes[-20:]) / 20.0
            if volume_20sma > 0.0 and volume_5sma > 1.5 * volume_20sma:
                volume_expansion_active = True
                if price_trend_positive:
                    volume_bonus_applied = 0.05
                    combined += 0.05
                elif price_trend_negative:
                    volume_bonus_applied = -0.05
                    combined -= 0.05

        # Cap combined score between 0.0 and 1.0
        combined = max(0.0, min(1.0, combined))

        # Liquidity / floating value penalty
        low_liquidity_penalty = False
        if floating_shares is not None:
            current_price = closes[-1]
            floating_value = current_price * floating_shares
            threshold = 10_000_000_000.0 if current_price > 1000.0 else 10_000_000.0
            if floating_value < threshold:
                combined = min(combined, 0.4)
                low_liquidity_penalty = True

        # 투표 기반 신호 결정
        buy_votes = sum(1 for s in [rsi_score, macd_score, ema_score, bb_score] if s > 0.6)
        sell_votes = sum(1 for s in [rsi_score, macd_score, ema_score, bb_score] if s < 0.4)

        if buy_votes >= 3:
            signal = TradeSignal.BUY
        elif sell_votes >= 3:
            signal = TradeSignal.SELL
        else:
            signal = TradeSignal.HOLD

        return {
            "score": combined,
            "signal": signal,
            "details": {
                "rsi": round(rsi, 1),
                "rsi_score": rsi_score,
                "macd_hist": round(macd_hist, 4),
                "macd_score": macd_score,
                "ema_score": ema_score,
                "bb_position": round(bb_pos, 3),
                "bb_score": bb_score,
                "buy_votes": buy_votes,
                "sell_votes": sell_votes,
                "volume_5sma": round(volume_5sma, 1) if volume_5sma is not None else None,
                "volume_20sma": round(volume_20sma, 1) if volume_20sma is not None else None,
                "volume_expansion_active": volume_expansion_active,
                "volume_bonus_applied": volume_bonus_applied,
                "low_liquidity_penalty": low_liquidity_penalty,
            },
        }

    def analyze(
        self,
        symbol: str,
        market_data: Dict,
        news_sentiment: float,
        price_bars: Optional[List[Any]] = None,
        cash_ratio: float = 0.5,
    ) -> StrategyResult:
        """
        종합 분석 수행
        market_data: {price, volume, bid, ask}
        news_sentiment: -1.0 ~ 1.0
        price_bars: ML 예측을 위한 과거 주가 데이터
        cash_ratio: 0.0 ~ 1.0, portfolio cash / total portfolio value
        """
        price = market_data.get("price", 0)
        volume = market_data.get("volume", 0)
        bid = market_data.get("bid", 0)
        ask = market_data.get("ask", 0)

        # 거래량 확인
        if volume < self.volume_threshold:
            signal = TradeSignal.HOLD
            confidence = 0.3
            reason = "Low volume"
        else:
            # 기술적 지표 분석: price_bars가 충분하면 종합 기술 지표 사용, 아니면 스프레드 기반 폴백
            tech_indicators = None
            if price_bars and len(price_bars) >= 20:
                floating_shares = market_data.get("floating_shares", None)
                tech_indicators = self._compute_technical_indicators(price_bars, floating_shares=floating_shares)
                technical_signal = tech_indicators["signal"]
                technical_score = tech_indicators["score"]
            else:
                spread_ratio = (ask - bid) / bid if bid > 0 else 0
                if spread_ratio < self.spread_threshold:
                    technical_signal = TradeSignal.BUY if price > bid * self.buy_price_threshold else TradeSignal.HOLD
                    technical_score = 0.7
                else:
                    technical_signal = TradeSignal.HOLD
                    technical_score = 0.5

            # 감성 분석: gradient 방식 (news_sentiment를 점수에 직접 매핑)
            sentiment_score = max(0.0, min(1.0, 0.5 + news_sentiment * 0.4))
            if sentiment_score > 0.6:
                sentiment_signal = TradeSignal.BUY
            elif sentiment_score < 0.4:
                sentiment_signal = TradeSignal.SELL
            else:
                sentiment_signal = TradeSignal.HOLD

            ml_score = 0.5
            if self.ml_engine and price_bars:
                try:
                    prob = self.ml_engine.predict_prob(price_bars)
                    ml_score = prob
                except Exception as e:
                    self.logger.warning(f"ML Prediction failed: {e}")

            rl_score = 0.5
            rl_action = "HOLD"
            alt_regime = {}
            if self.alt_client:
                alt_regime = self.alt_client.get_market_regime()

            if self.rl_engine:
                try:
                    rsi_val = 50.0
                    macd_val = 0.0
                    if price_bars and len(price_bars) > 15:
                        closes = [b.close for b in price_bars if not isinstance(b, (int, float))]
                        if len(closes) > 15:
                            rsi_val = _calc_rsi_shared(closes, 14)
                            macd_val = calc_macd(closes, 12, 26, 9)
                    state = {
                        "vix": alt_regime.get("vix", 20.0),
                        "rsi": rsi_val,
                        "macd": macd_val,
                        "trend_strength": technical_score,
                    }
                    rl_res = self.rl_engine.get_action(state)
                    rl_action = rl_res["action"]
                    # Map action to score: BUY -> 1.0, SELL -> 0.0, HOLD -> 0.5
                    if rl_action == "BUY":
                        rl_score = 1.0
                    elif rl_action == "SELL":
                        rl_score = 0.0
                except Exception as e:
                    self.logger.warning(f"RL Action failed: {e}")

            darkpool_score = 0.5
            if self.darkpool:
                dp_res = self.darkpool.fetch_darkpool_activity(symbol)
                if dp_res.get("is_accumulation"):
                    darkpool_score = 0.9
                elif dp_res.get("is_distribution"):
                    darkpool_score = 0.1

            llm_score = 0.5
            if self.llm_earnings:
                llm_direction = "POSITIVE" if news_sentiment > 0 else "NEGATIVE"
                transcript = f"최근 뉴스 심리가 {llm_direction}으로 {abs(news_sentiment) * 100:.0f}% 수준입니다."
                llm_res = self.llm_earnings.analyze_earnings_call(symbol, transcript)
                if llm_res.get("guidance") == "POSITIVE":
                    llm_score = 0.9
                elif llm_res.get("guidance") == "NEGATIVE":
                    llm_score = 0.1

            # ── Global market signal ───────────────────────────────────────
            global_market_score = 0.5
            try:
                if self.global_market:
                    gm = self.global_market.get_summary()
                    indices = gm.get("indices", {})
                    up = sum(1 for v in indices.values() if (v.get("change_pct") or 0) > 0)
                    total = len(indices) or 1
                    global_market_score = 0.5 + (up / total - 0.5) * 0.4
            except Exception:
                pass

            # ── Cash ratio signal ──────────────────────────────────────────
            vix_value_raw = alt_regime.get("vix", 20.0) if alt_regime else 20.0
            if vix_value_raw >= 25:
                target_cash = 0.40
            elif vix_value_raw >= 15:
                target_cash = 0.20
            else:
                target_cash = 0.10
            cash_ratio_score = max(0.0, min(1.0, 0.5 + (cash_ratio - target_cash) * 1.0))

            # ── Macro composite signal (VIX + FX + Oil + Rates + DXY) ───────
            macro_score = 0.5
            try:
                if self.global_market:
                    gm = self.global_market.get_summary()
                    fx = gm.get("fx_rates", {})
                    mc = gm.get("macro_commodities", {})
                    usdkrw = float(fx.get("USDKRW=X", {}).get("rate", 1300))
                    oil = float(mc.get("CL=F", {}).get("price", 75))
                    tnx = float(mc.get("^TNX", {}).get("price", 4.0))
                    dxy = float(mc.get("DX-Y.NYB", {}).get("price", 103))
                    vix_val = float(gm.get("indices", {}).get("^VIX", {}).get("price", 20))
                    vix_s = max(0.0, min(1.0, 1.0 - (vix_val - 12) / 35))
                    fx_s = max(0.0, min(1.0, 1.0 - (usdkrw - 1200) / 400))
                    oil_s = max(0.0, min(1.0, 1.0 - (oil - 50) / 150))
                    tnx_s = max(0.0, min(1.0, 1.0 - (tnx - 2.5) / 5.0))
                    dxy_s = max(0.0, min(1.0, 1.0 - (dxy - 95) / 25))
                    macro_score = vix_s * 0.30 + fx_s * 0.20 + oil_s * 0.20 + tnx_s * 0.15 + dxy_s * 0.15
                    self.logger.debug(
                        f"Macro composite: {macro_score:.3f} "
                        f"(VIX={vix_val:.1f}/{vix_s:.2f}, USDKRW={usdkrw:.0f}/{fx_s:.2f}, "
                        f"Oil={oil:.1f}/{oil_s:.2f}, TNX={tnx:.2f}/{tnx_s:.2f}, DXY={dxy:.1f}/{dxy_s:.2f})"
                    )
            except Exception as e:
                self.logger.debug(f"Macro composite failed: {e}")

            # ── Style Rotation signal ─────────────────────────────────────
            style_score = 0.5
            try:
                if self.style_rotator:
                    regime = self.style_rotator.current_regime
                    if regime == "DEFENSIVE":
                        style_score = 0.3  # risk-off
                    elif regime == "EXPANSION":
                        style_score = 0.7  # risk-on
                    elif regime == "RATE_CUTTING":
                        style_score = 0.65
                    elif regime == "INFLATION_RISING":
                        style_score = 0.4
            except Exception:
                pass

            # ── 활성 신호 필터링 (미연동/제로가중치 신호 제외) ────────────
            signal_scores = {
                "sentiment": (sentiment_score, self.sentiment_weight, True),
                "technical": (technical_score, self.technical_weight, True),
                "ml": (ml_score, self.ml_weight, self.ml_engine is not None),
                "rl": (rl_score, self.rl_weight, self.rl_engine is not None),
                "darkpool": (
                    darkpool_score,
                    self.darkpool_weight,
                    self.darkpool is not None and self.darkpool_weight > 0,
                ),
                "llm": (llm_score, self.llm_weight, self.llm_earnings is not None),
                "global_market": (
                    global_market_score,
                    self.global_market_weight,
                    self.global_market is not None and self.global_market_weight > 0,
                ),
                "cash_ratio": (cash_ratio_score, self.cash_ratio_weight, True),
                "macro": (macro_score, self.macro_weight, self.global_market is not None),
            }
            active_scores = {k: (s, w) for k, (s, w, a) in signal_scores.items() if a}
            total_active_weight = sum(w for _, (_, w) in active_scores.items())
            if total_active_weight > 0:
                combined_score = (
                    sum(active_scores[k][0] * active_scores[k][1] for k in active_scores) / total_active_weight
                )
            else:
                combined_score = 0.5

            # Style rotation adjustment (blended, not a formal signal)
            if style_score != 0.5:
                combined_score = combined_score * 0.85 + style_score * 0.15

            # ── 레짐별 동적 임계값 적용 ──────────────────────────────
            regime_profile = REGIME_THRESHOLDS.get(self._active_regime, REGIME_THRESHOLDS["weak_bull"])
            dynamic_buy_threshold = regime_profile["buy"]
            dynamic_sell_threshold = regime_profile["sell"]

            raw_scores = {k: v[0] for k, v in signal_scores.items()}

            # ── Signal consensus scoring ───────────────────────────────
            bullish_signals = sum(1 for v in raw_scores.values() if v > 0.6)
            bearish_signals = sum(1 for v in raw_scores.values() if v < 0.4)
            total_active = len(raw_scores)
            max_agree = max(bullish_signals, bearish_signals)
            consensus_ratio = max_agree / total_active if total_active > 0 else 0
            if consensus_ratio >= 0.6:
                consensus_multiplier = 1.0 + (consensus_ratio - 0.5) * 0.5
                combined_score *= consensus_multiplier
            elif consensus_ratio <= 0.3:
                combined_score *= 0.5 + consensus_ratio

            regime = alt_regime or {}
            if regime.get("is_high_volatility"):
                adjusted = {
                    "sentiment": self.sentiment_weight * 0.8,
                    "technical": self.technical_weight * 1.5,
                    "ml": self.ml_weight * 0.7,
                    "rl": self.rl_weight * 1.3,
                    "darkpool": self.darkpool_weight * 1.2,
                    "llm": self.llm_weight * 0.8,
                    "global_market": self.global_market_weight * 1.1,
                    "cash_ratio": self.cash_ratio_weight * 1.3,
                    "macro": self.macro_weight * 1.4,
                }
                total_adj = sum(adjusted.values())
                if total_adj > 0:
                    weights = {k: v / total_adj for k, v in adjusted.items()}
                    combined_score = sum(raw_scores[k] * weights[k] for k in self.SIGNAL_NAMES)

            # Scale down targets/allocation confidence for assets with low norm_volume or norm_floating_value
            norm_volume = market_data.get("norm_volume")
            norm_floating_value = market_data.get("norm_floating_value")

            # Check if we can get them from price_bars if not in market_data
            if (norm_volume is None or norm_floating_value is None) and price_bars and len(price_bars) > 0:
                last_bar = price_bars[-1]
                if isinstance(last_bar, dict):
                    if norm_volume is None:
                        norm_volume = last_bar.get("norm_volume")
                    if norm_floating_value is None:
                        norm_floating_value = last_bar.get("norm_floating_value")
                elif hasattr(last_bar, "norm_volume") or (hasattr(last_bar, "__getitem__") and not isinstance(last_bar, (str, bytes))):
                    try:
                        if norm_volume is None:
                            norm_volume = getattr(last_bar, "norm_volume", None) or last_bar["norm_volume"]
                    except Exception:
                        pass
                    try:
                        if norm_floating_value is None:
                            norm_floating_value = getattr(last_bar, "norm_floating_value", None) or last_bar["norm_floating_value"]
                    except Exception:
                        pass

            if norm_volume is None:
                norm_volume = 1.0
            if norm_floating_value is None:
                norm_floating_value = 1.0

            scaling_factor = 1.0
            if norm_volume < 0.01:
                scaling_factor = min(scaling_factor, norm_volume / 0.01)
            if norm_floating_value < 0.01:
                scaling_factor = min(scaling_factor, norm_floating_value / 0.01)

            scaling_factor = max(0.1, scaling_factor)
            confidence = combined_score * scaling_factor

            # 매수/매도 판단: 동적 임계값 사용
            buy_signal_count = sum(1 for s in [sentiment_signal, technical_signal] if s == TradeSignal.BUY)

            if combined_score > dynamic_buy_threshold:
                if buy_signal_count >= regime_profile["min_buy_votes"]:
                    signal = TradeSignal.BUY
                    reason = f"Buy signal (regime={self._active_regime})"
                elif buy_signal_count >= 1 and combined_score > dynamic_buy_threshold + 0.10:
                    signal = TradeSignal.BUY
                    reason = f"Buy signal (high score with supporting indicator, regime={self._active_regime})"
                else:
                    signal = TradeSignal.HOLD
                    reason = "Conflicting signals"
            elif combined_score < dynamic_sell_threshold:
                signal = TradeSignal.SELL
                reason = f"Weak signals detected (regime={self._active_regime})"
            else:
                signal = TradeSignal.HOLD
                reason = f"Neutral market (regime={self._active_regime})"

            # Options Hedging Logic:
            # If we hold the stock (assumed by neutral/buy but high VIX), recommend Protective Put
            if alt_regime and alt_regime.get("is_high_volatility") and signal != TradeSignal.SELL:
                reason += " | Recommend Protective Put (High VIX)"

            # Stat Arb (Pairs Trading) Override
            if self.stat_arb and price_bars and len(price_bars) > 30:
                price_dict: Dict[str, List[float]] = {}
                closes = [b.close for b in price_bars if not isinstance(b, (int, float))]
                if closes:
                    price_dict[symbol] = closes
                    for sym, pos in getattr(getattr(self, "portfolio", None), "positions", {}).items():
                        price_dict[sym] = closes[-min(len(closes), 30) :]
                    pairs = self.stat_arb.find_cointegrated_pairs(price_dict)
                    for p in pairs:
                        if symbol in p["pair"]:
                            reason += f" | Stat Arb: {p['signal']} (z={p['z_score']})"

            # Execute HFT if available and signal is strong
            if self.hft_engine and signal != TradeSignal.HOLD:
                self.hft_engine.execute_micro_order(symbol, signal.name, 100)
                reason += " | (Executed via HFT Engine)"

        # Determine dominant signal for performance attribution
        dominant_signal = max(raw_scores, key=lambda k: raw_scores[k])
        if raw_scores.get(dominant_signal, 0.5) < 0.55:
            dominant_signal = "strategy"

        result = StrategyResult(
            symbol=symbol,
            signal=signal,
            price=price,
            confidence=confidence,
            reason=reason,
            timestamp=datetime.now(),
            signal_name=dominant_signal,
        )

        self.results_history.append(result)

        # 이벤트 버스로 전송
        if self.event_bus:
            self.event_bus.publish("strategy_signal", result)

        # 구독자에게 알림 (하위 호환성)
        for callback in self.subscribers:
            try:
                callback(result)
            except Exception as e:
                self.logger.error(f"Strategy callback error: {e}")

        self.logger.info(f"Strategy result: {result}")
        return result

    def record_signal_outcome(self, signal_name: str, was_correct: bool) -> None:
        if signal_name not in self._signal_performance:
            return
        self._signal_performance[signal_name].append(was_correct)
        if len(self._signal_performance[signal_name]) > self.weight_adaptation_window * 2:
            self._signal_performance[signal_name] = self._signal_performance[signal_name][
                -self.weight_adaptation_window :
            ]
        if len(self.results_history) % self.weight_adaptation_window == 0:
            self._adapt_weights()

    def _adapt_weights(self) -> None:
        accuracies = {}
        for name in self.SIGNAL_NAMES:
            perf = self._signal_performance.get(name, [])
            if len(perf) >= 10:
                accuracies[name] = sum(perf) / len(perf)
        if len(accuracies) < 3:
            return
        avg_acc = sum(accuracies.values()) / len(accuracies)
        weight_map = {
            "sentiment": "sentiment_weight",
            "technical": "technical_weight",
            "ml": "ml_weight",
            "rl": "rl_weight",
            "darkpool": "darkpool_weight",
            "llm": "llm_weight",
            "global_market": "global_market_weight",
            "cash_ratio": "cash_ratio_weight",
            "macro": "macro_weight",
        }
        for name, acc in accuracies.items():
            attr = weight_map.get(name)
            if attr is None:
                continue
            current = getattr(self, attr)
            if acc > avg_acc:
                setattr(self, attr, current * (1.0 + self.weight_adaptation_rate))
            else:
                setattr(self, attr, current * (1.0 - self.weight_adaptation_rate))
        self._normalize_weights()

    def _normalize_weights(self) -> None:
        self.sentiment_weight = max(0.0, min(1.0, self.sentiment_weight))
        self.technical_weight = max(0.0, min(1.0, self.technical_weight))
        self.ml_weight = max(0.0, min(1.0, self.ml_weight))
        self.rl_weight = max(0.0, min(1.0, self.rl_weight))
        self.darkpool_weight = max(0.0, min(1.0, self.darkpool_weight))
        self.llm_weight = max(0.0, min(1.0, self.llm_weight))
        self.global_market_weight = max(0.0, min(1.0, self.global_market_weight))
        self.cash_ratio_weight = max(0.0, min(1.0, self.cash_ratio_weight))
        self.macro_weight = max(0.0, min(1.0, self.macro_weight))

        total = (
            self.sentiment_weight
            + self.technical_weight
            + self.ml_weight
            + self.rl_weight
            + self.darkpool_weight
            + self.llm_weight
            + self.global_market_weight
            + self.cash_ratio_weight
            + self.macro_weight
        )
        if total == 0:
            n = len(self.SIGNAL_NAMES)
            self.sentiment_weight = 1.0 / n
            self.technical_weight = 1.0 / n
            self.ml_weight = 1.0 / n
            self.rl_weight = 1.0 / n
            self.darkpool_weight = 1.0 / n
            self.llm_weight = 1.0 / n
            self.global_market_weight = 1.0 / n
            self.cash_ratio_weight = 1.0 / n
            self.macro_weight = 1.0 / n
        else:
            self.sentiment_weight /= total
            self.technical_weight /= total
            self.ml_weight /= total
            self.rl_weight /= total
            self.darkpool_weight /= total
            self.llm_weight /= total
            self.global_market_weight /= total
            self.cash_ratio_weight /= total
            self.macro_weight /= total
        self.logger.info(
            f"Weights adapted: sentiment={self.sentiment_weight:.3f} "
            f"technical={self.technical_weight:.3f} ml={self.ml_weight:.3f} "
            f"rl={self.rl_weight:.3f} darkpool={self.darkpool_weight:.3f} "
            f"llm={self.llm_weight:.3f} global_market={self.global_market_weight:.3f} "
            f"cash_ratio={self.cash_ratio_weight:.3f} macro={self.macro_weight:.3f}"
        )

    def set_strategy_parameters(self, strategy_name: str, parameters: Dict) -> None:
        """Store strategy parameters"""
        self.strategy_parameters[strategy_name] = parameters

    def _calc_adx(self, price_bars: List[Any], period: int = 14) -> float:
        """Calculate ADX (Average Directional Index) for trend strength."""
        if len(price_bars) < period * 2:
            return 0.0
        tr_list, plus_dm_list, minus_dm_list = [], [], []
        for i in range(1, len(price_bars)):
            bar = price_bars[i]
            prev = price_bars[i - 1]
            high = bar["high"] if isinstance(bar, dict) else bar.high
            low = bar["low"] if isinstance(bar, dict) else bar.low
            prev_high = prev["high"] if isinstance(prev, dict) else prev.high
            prev_low = prev["low"] if isinstance(prev, dict) else prev.low
            prev_close = prev["close"] if isinstance(prev, dict) else prev.close
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            up_move = high - prev_high
            down_move = prev_low - low
            plus_dm = up_move if up_move > down_move and up_move > 0 else 0.0
            minus_dm = down_move if down_move > up_move and down_move > 0 else 0.0
            tr_list.append(tr)
            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)
        atr = sum(tr_list[-period:]) / period
        if atr == 0:
            return 0.0
        plus_di = sum(plus_dm_list[-period:]) / period / atr * 100
        minus_di = sum(minus_dm_list[-period:]) / period / atr * 100
        dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0.0
        return dx

    def _calc_bb_width(self, price_bars: List[Any], period: int = 20) -> float:
        """Bollinger Band width as a volatility indicator."""
        if len(price_bars) < period:
            return 0.0
        closes = []
        for bar in price_bars[-period:]:
            closes.append(bar["close"] if isinstance(bar, dict) else bar.close)
        sma = sum(closes) / len(closes)
        variance = sum((c - sma) ** 2 for c in closes) / len(closes)
        std_dev = variance**0.5
        if sma == 0:
            return 0.0
        return float(2.0 * std_dev / sma)

    def detect_regime(self, price_bars: List[Any]) -> str:
        """시장 레짐(추세) 감지 및 가중치/임계값 동적 조절"""
        for bar in price_bars:
            if isinstance(bar, dict):
                if not all(k in bar for k in ["open", "high", "low", "close", "volume"]):
                    raise ValueError("Missing fields in price bar dict")
                if any(bar[k] is None for k in ["open", "high", "low", "close", "volume"]):
                    raise ValueError("None fields in price bar dict")
            else:
                for attr in ["open", "high", "low", "close", "volume"]:
                    if not hasattr(bar, attr):
                        raise ValueError(f"Missing field {attr} in price bar object")
                    if getattr(bar, attr) is None:
                        raise ValueError(f"None field {attr} in price bar object")

        if len(price_bars) < 200:
            self._active_regime = MarketRegime.WEAK_BEAR.value
            return MarketRegime.WEAK_BEAR.value

        closes = [bar.close if not isinstance(bar, dict) else bar["close"] for bar in price_bars]

        ema50 = self._calc_ema(closes, 50)
        ema200 = self._calc_ema(closes, 200)

        # Calculate additional metrics requested:
        # - EMA200 position: check if current close > EMA200
        current_close = closes[-1]
        current_ema200 = ema200[-1]
        ema200_position = current_close > current_ema200

        # - ROC momentum (20 period): calculation `(close[-1] - close[-20]) / close[-20] * 100`
        close_20 = closes[-20]
        roc_momentum = ((current_close - close_20) / close_20 * 100) if close_20 != 0.0 else 0.0

        # - ATR ratio: ATR (14 period) / current close
        tr_values = []
        for i in range(len(price_bars)):
            bar = price_bars[i]
            high = bar["high"] if isinstance(bar, dict) else bar.high
            low = bar["low"] if isinstance(bar, dict) else bar.low
            if i == 0:
                tr = high - low
            else:
                prev_bar = price_bars[i - 1]
                prev_close = prev_bar["close"] if isinstance(prev_bar, dict) else prev_bar.close
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_values.append(tr)
        atr_14 = sum(tr_values[-14:]) / 14.0
        atr_ratio = atr_14 / current_close if current_close != 0.0 else 0.0

        # Compute ADX and BB width for refined regime classification
        adx_value = self._calc_adx(price_bars)
        bb_width = self._calc_bb_width(price_bars)

        # Log computed metrics
        self.logger.info(
            f"Regime metrics - EMA200 Position: {ema200_position}, "
            f"ROC Momentum: {roc_momentum:.4f}%, ATR Ratio: {atr_ratio:.4f}, "
            f"ADX: {adx_value:.1f}, BB Width: {bb_width:.4f}"
        )

        # 4-레짐 분류: EMA50/200 비율 + ADX 강도 + ROC 모멘텀
        ema_bull = ema50[-1] > ema200[-1]
        strong_trend = adx_value > 25
        fast_up = roc_momentum > 5.0
        fast_down = roc_momentum < -5.0

        if ema_bull and (strong_trend or fast_up):
            regime = MarketRegime.STRONG_BULL.value
        elif ema_bull:
            regime = MarketRegime.WEAK_BULL.value
        elif not ema_bull and (strong_trend or fast_down):
            regime = MarketRegime.STRONG_BEAR.value
        else:
            regime = MarketRegime.WEAK_BEAR.value

        # Skip weight/threshold adjustment if regime hasn't changed
        if regime == self._active_regime:
            return regime

        # Regime changed — adjust current (adapted) weights instead of resetting to baseline
        self._active_regime = regime
        profile = REGIME_THRESHOLDS[regime]

        if regime in (MarketRegime.STRONG_BULL.value, MarketRegime.WEAK_BULL.value):
            self.technical_weight *= 1.10
            self.ml_weight *= 1.08
            self.rl_weight *= 1.05
            self.sentiment_weight *= 1.03
            self.cash_ratio_weight *= 0.85 if regime == MarketRegime.STRONG_BULL.value else 0.90
            self.sell_threshold = profile["sell"]
            self.buy_price_threshold = min(1.05, self.buy_price_threshold + 0.01)
            if strong_trend and regime == MarketRegime.STRONG_BULL.value:
                self.technical_weight *= 1.05
            if regime == MarketRegime.WEAK_BULL.value:
                self.technical_weight *= 0.95
            self._normalize_weights()
        else:
            self.ml_weight *= 0.85
            self.rl_weight *= 0.85
            self.sentiment_weight *= 0.90
            self.cash_ratio_weight *= 1.20 if regime == MarketRegime.STRONG_BEAR.value else 1.10
            self.darkpool_weight *= 1.10
            self.sell_threshold = profile["sell"]
            self.buy_price_threshold = max(1.00, self.buy_price_threshold - 0.02)
            if regime == MarketRegime.STRONG_BEAR.value:
                self.cash_ratio_weight *= 1.10
                self.sell_threshold = max(0.1, self.sell_threshold - 0.06)
            else:
                self.sell_threshold = min(0.44, self.sell_threshold)
            self._normalize_weights()

        return regime


class OptimizationEngine:
    """최적화 엔진 - 슬리피지 및 손익 기반 파라미터 튜닝"""

    def __init__(self, strategy_engine: HybridStrategyEngine) -> None:
        self.strategy_engine = strategy_engine
        self.logger = logger
        self.optimization_history: list = []

        # 성과 메트릭
        self.total_trades = 0
        self.winning_trades = 0
        self.total_slippage = 0.0

        # Performance attribution: PnL per signal
        self._signal_pnl: Dict[str, List[float]] = {}

    def record_trade_result(
        self, signal: TradeSignal, entry_price: float, exit_price: float, quantity: int, signal_name: str | None = None
    ) -> None:
        """트레이드 결과 기록"""
        if signal == TradeSignal.BUY:
            slippage = abs(entry_price - exit_price) / entry_price
        else:
            slippage = abs(exit_price - entry_price) / entry_price

        pnl = (exit_price - entry_price) * quantity
        is_win = pnl > 0

        self.total_trades += 1
        if is_win:
            self.winning_trades += 1
        self.total_slippage += slippage

        # Track PnL per signal for performance attribution
        if signal_name:
            self._signal_pnl.setdefault(signal_name, []).append(pnl)
            if is_win:
                self.strategy_engine.record_signal_outcome(signal_name, True)
            else:
                self.strategy_engine.record_signal_outcome(signal_name, False)

        self.logger.info(f"Trade recorded: PnL={pnl}, slippage={slippage:.4f}")

    def get_win_rate(self) -> float:
        """승률 계산"""
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades

    def get_avg_slippage(self) -> float:
        """평균 슬리피지 계산"""
        if self.total_trades == 0:
            return 0.0
        return self.total_slippage / self.total_trades

    def get_signal_performance_attribution(self) -> Dict[str, Dict]:
        """Return PnL attribution per signal name."""
        attribution = {}
        for signal_name, pnls in self._signal_pnl.items():
            attribution[signal_name] = {
                "total_pnl": round(sum(pnls), 2),
                "avg_pnl": round(sum(pnls) / len(pnls), 2) if pnls else 0.0,
                "trade_count": len(pnls),
                "win_count": sum(1 for p in pnls if p > 0),
                "win_rate": round(sum(1 for p in pnls if p > 0) / len(pnls), 4) if pnls else 0.0,
            }
        return attribution

    def optimize_parameters(self) -> Dict:
        """파라미터 자동 튜닝"""
        win_rate = self.get_win_rate()
        avg_slippage = self.get_avg_slippage()

        optimization = {
            "win_rate": win_rate,
            "avg_slippage": avg_slippage,
            "total_trades": self.total_trades,
            "timestamp": datetime.now(),
        }

        if win_rate < 0.4:
            self.strategy_engine.volume_threshold = int(self.strategy_engine.volume_threshold * 1.1)
            self.logger.warning(f"Adjusted volume threshold to {self.strategy_engine.volume_threshold}")

        if avg_slippage > 0.01:
            self.logger.warning(f"High slippage detected: {avg_slippage:.4f}")

        self.strategy_engine._adapt_weights()

        self.optimization_history.append(optimization)
        return optimization
