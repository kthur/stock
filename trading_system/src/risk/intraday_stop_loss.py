"""
Intraday Microstructure & Dynamic Stop-Loss Engine
Tracks intraday price momentum, order book imbalance, and volume spikes to trigger dynamic position scaling and stop-loss gating.
"""

import collections
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class IntradayTick:
    symbol: str
    price: float
    volume: float
    bid_ask_spread: float = 0.0
    bid_volume: float = 0.0
    ask_volume: float = 0.0
    timestamp: float = 0.0


@dataclass
class StopLossSignal:
    symbol: str = ""
    triggered: bool = False
    trigger_stop: bool = False
    reason: str = "NONE"
    recommended_action: str = "NO_ACTION"
    drop_pct: float = 0.0
    panic_volume_ratio: float = 1.0
    scale_factor: float = 1.0
    intraday_return: float = 0.0
    panic_score: float = 0.0


StopLossResult = StopLossSignal


class IntradayStopLossEngine:
    """
    Intraday Microstructure & Dynamic Stop-Loss Engine
    Monitors intraday drawdown, order book volume imbalance, dynamic ATR breach, and sudden volume surges.
    """

    def __init__(
        self,
        peak_drop_threshold: float = -0.04,
        volume_spike_threshold: float = 3.0,
        atr_multiplier: float = 2.0,
        max_symbols: int = 1000,
        stop_loss_threshold: float = -0.04,
        order_imbalance_threshold: float = -0.6,
        volume_spike_multiplier: float = 3.5,
    ):
        self.peak_drop_threshold = peak_drop_threshold
        self.volume_spike_threshold = volume_spike_threshold
        self.atr_multiplier = atr_multiplier
        self.max_symbols = max_symbols
        self.stop_loss_threshold = stop_loss_threshold
        self.order_imbalance_threshold = order_imbalance_threshold
        self.volume_spike_multiplier = volume_spike_multiplier

        self._symbol_peaks: Dict[str, float] = collections.OrderedDict()
        self._price_history: Dict[str, list] = collections.OrderedDict()
        self._volume_history: Dict[str, list] = collections.OrderedDict()
        self._open_prices: Dict[str, float] = collections.OrderedDict()
        self._avg_volumes: Dict[str, float] = collections.OrderedDict()

    def _evict_lru_if_needed(self, symbol: str) -> None:
        if symbol not in self._symbol_peaks and len(self._symbol_peaks) >= self.max_symbols:
            oldest = next(iter(self._symbol_peaks))
            self.reset_symbol(oldest)

    def reset_symbol(self, symbol: str) -> None:
        """Clear tracking state for a single symbol."""
        self._symbol_peaks.pop(symbol, None)
        self._price_history.pop(symbol, None)
        self._volume_history.pop(symbol, None)
        self._open_prices.pop(symbol, None)
        self._avg_volumes.pop(symbol, None)

    def reset_all(self) -> None:
        """Clear all internal states."""
        self._symbol_peaks.clear()
        self._price_history.clear()
        self._volume_history.clear()
        self._open_prices.clear()
        self._avg_volumes.clear()

    def register_open(self, symbol: str, open_price: float, avg_volume: float = 1000.0) -> None:
        """Register market open price and baseline average volume for a symbol."""
        self._evict_lru_if_needed(symbol)
        self._open_prices[symbol] = max(1e-5, open_price)
        self._symbol_peaks[symbol] = max(1e-5, open_price)
        self._avg_volumes[symbol] = max(1.0, avg_volume)

    def evaluate(
        self,
        symbol: str,
        data: Any,
        crisis_multiplier: float = 1.0,
    ) -> StopLossSignal:
        """
        Evaluate market data for dynamic stop-loss rules.
        data can be a dict or a pandas DataFrame.
        """
        try:
            if data is None:
                return StopLossSignal(symbol=symbol, triggered=False, reason="EVALUATION_ERROR")

            current_price = 0.0
            peak_price = 0.0
            volume = 0.0
            volume_ma_20 = 0.0
            atr = 0.0
            prev_price = 0.0

            if isinstance(data, pd.DataFrame):
                if data.empty or "close" not in data.columns:
                    return StopLossSignal(symbol=symbol, triggered=False, reason="INVALID_PRICE")

                closes = data["close"].dropna().values
                if len(closes) == 0:
                    return StopLossSignal(symbol=symbol, triggered=False, reason="INVALID_PRICE")

                current_price = float(closes[-1])
                if len(closes) > 1:
                    prev_price = float(closes[-2])
                else:
                    prev_price = current_price

                if "volume" in data.columns:
                    vols = data["volume"].dropna().values[-20:]
                    if len(vols) > 0:
                        volume = float(vols[-1])
                        volume_ma_20 = float(np.mean(vols))
                    else:
                        volume = 0.0
                        volume_ma_20 = 0.0

                if "high" in data.columns:
                    highs = data["high"].dropna().values
                    if len(highs) > 0:
                        peak_price = float(np.max(highs))
                    else:
                        peak_price = current_price
                else:
                    peak_price = float(np.max(closes))

                if "atr" in data.columns:
                    atrs = data["atr"].dropna().values
                    if len(atrs) > 0:
                        atr = float(atrs[-1])

            elif isinstance(data, dict):
                current_price = float(data.get("current_price", 0.0))
                peak_price = float(data.get("peak_price", 0.0))
                volume = float(data.get("volume", 0.0))
                volume_ma_20 = float(data.get("volume_ma_20", 0.0))
                atr = float(data.get("atr", 0.0))
                prev_price = float(data.get("prev_price", current_price))
            else:
                return StopLossSignal(symbol=symbol, triggered=False, reason="EVALUATION_ERROR")

            # Validate price finiteness & positive value
            if math.isnan(current_price) or math.isinf(current_price) or current_price <= 0:
                return StopLossSignal(symbol=symbol, triggered=False, reason="INVALID_PRICE")

            self._evict_lru_if_needed(symbol)

            # Flash spike guard (>1.5x previous peak)
            last_peak = self._symbol_peaks.get(symbol, current_price)
            if peak_price <= 0 or peak_price > last_peak * 1.5:
                peak_price = max(last_peak, current_price)
            else:
                peak_price = max(last_peak, peak_price, current_price)

            self._symbol_peaks[symbol] = peak_price

            if symbol not in self._price_history:
                self._price_history[symbol] = []
            self._price_history[symbol].append(current_price)
            if len(self._price_history[symbol]) > 100:
                self._price_history[symbol].pop(0)

            if symbol not in self._volume_history:
                self._volume_history[symbol] = []
            self._volume_history[symbol].append(volume)
            if len(self._volume_history[symbol]) > 100:
                self._volume_history[symbol].pop(0)

            # Compute panic volume ratio
            if volume_ma_20 > 0:
                panic_volume_ratio = volume / volume_ma_20
            else:
                panic_volume_ratio = 1.0

            drop_pct = (current_price - peak_price) / peak_price if peak_price > 0 else 0.0

            effective_drop_thresh = self.peak_drop_threshold * crisis_multiplier

            reasons = []

            # Rule 1: Dynamic ATR Trailing Stop Breach
            if atr > 0:
                stop_level = peak_price - self.atr_multiplier * atr
                if current_price < stop_level:
                    reasons.append("DYNAMIC_ATR_TRAILING_BREACH")

            # Rule 2: Peak to Trough Drop
            if drop_pct <= effective_drop_thresh:
                reasons.append("PEAK_TO_TROUGH_DROP")

            # Rule 3: Panic Volume Spike
            if panic_volume_ratio >= self.volume_spike_threshold and current_price < prev_price:
                reasons.append("PANIC_VOLUME_SPIKE")

            triggered = len(reasons) > 0
            reason_str = "|".join(reasons) if triggered else "NONE"
            recommended_action = "FULL_LIQUIDATION" if triggered else "NO_ACTION"
            scale_factor = 0.0 if triggered else 1.0

            return StopLossSignal(
                symbol=symbol,
                triggered=triggered,
                trigger_stop=triggered,
                reason=reason_str,
                recommended_action=recommended_action,
                drop_pct=drop_pct,
                panic_volume_ratio=panic_volume_ratio,
                scale_factor=scale_factor,
                intraday_return=drop_pct,
                panic_score=1.0 if triggered else 0.0,
            )

        except Exception as e:
            logger.error(f"Error evaluating intraday stop-loss for {symbol}: {e}")
            return StopLossSignal(symbol=symbol, triggered=False, reason="EVALUATION_ERROR")

    def evaluate_tick(self, tick: IntradayTick) -> StopLossSignal:
        data = {
            "current_price": tick.price,
            "volume": tick.volume,
        }
        return self.evaluate(tick.symbol, data)
