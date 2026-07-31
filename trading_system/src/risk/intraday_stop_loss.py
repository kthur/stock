"""
Intraday Microstructure & Dynamic Stop-Loss Engine
Tracks intraday price momentum, order book imbalance, and volume spikes to trigger dynamic position scaling and stop-loss gating.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

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
    symbol: str
    trigger_stop: bool
    scale_factor: float
    reason: str
    intraday_return: float
    panic_score: float


class IntradayStopLossEngine:
    """
    Intraday Microstructure & Dynamic Stop-Loss Engine
    Monitors intraday drawdown, order book volume imbalance, and sudden volume surges.
    """

    def __init__(
        self,
        stop_loss_threshold: float = -0.04,
        order_imbalance_threshold: float = -0.6,
        volume_spike_multiplier: float = 3.5,
    ):
        self.stop_loss_threshold = stop_loss_threshold
        self.order_imbalance_threshold = order_imbalance_threshold
        self.volume_spike_multiplier = volume_spike_multiplier
        self._open_prices: Dict[str, float] = {}
        self._peak_prices: Dict[str, float] = {}
        self._avg_volumes: Dict[str, float] = {}

    def register_open(self, symbol: str, open_price: float, avg_volume: float = 1000.0) -> None:
        """Register market open price and baseline average volume for a symbol."""
        self._open_prices[symbol] = max(1e-5, open_price)
        self._peak_prices[symbol] = max(1e-5, open_price)
        self._avg_volumes[symbol] = max(1.0, avg_volume)

    def evaluate_tick(self, tick: IntradayTick) -> StopLossSignal:
        """Evaluate an incoming intraday tick and determine stop-loss / position scale factor."""
        symbol = tick.symbol
        price = tick.price

        open_p = self._open_prices.get(symbol, price)
        peak_p = max(self._peak_prices.get(symbol, price), price)
        self._peak_prices[symbol] = peak_p

        # Compute intraday return & drawdown from peak
        intraday_return = (price - open_p) / open_p
        drawdown_from_peak = (price - peak_p) / peak_p

        # Compute Order Book Imbalance (OBI): (BidVol - AskVol) / (BidVol + AskVol)
        total_depth = tick.bid_volume + tick.ask_volume
        if total_depth > 0:
            obi = (tick.bid_volume - tick.ask_volume) / total_depth
        else:
            obi = 0.0

        # Volume spike ratio
        baseline_vol = self._avg_volumes.get(symbol, 1000.0)
        vol_ratio = tick.volume / baseline_vol if baseline_vol > 0 else 1.0

        # Panic Score computation
        panic_score = 0.0
        reasons: List[str] = []

        if intraday_return <= self.stop_loss_threshold:
            panic_score += 0.5
            reasons.append(f"Intraday drop {intraday_return:.1%}")

        if drawdown_from_peak <= self.stop_loss_threshold:
            panic_score += 0.3
            reasons.append(f"Peak DD {drawdown_from_peak:.1%}")

        if obi <= self.order_imbalance_threshold:
            panic_score += 0.2
            reasons.append(f"Ask imbalance OBI={obi:.2f}")

        if vol_ratio >= self.volume_spike_multiplier and (intraday_return < -0.02 or drawdown_from_peak < -0.02):
            panic_score += 0.3
            reasons.append(f"Volume spike {vol_ratio:.1f}x on drop")

        trigger_stop = panic_score >= 0.5
        if panic_score >= 0.8:
            scale_factor = 0.0  # Liquidation
        elif panic_score >= 0.5:
            scale_factor = 0.5  # De-risk 50%
        else:
            scale_factor = 1.0  # Maintain

        reason_str = ", ".join(reasons) if reasons else "Normal"
        return StopLossSignal(
            symbol=symbol,
            trigger_stop=trigger_stop,
            scale_factor=scale_factor,
            reason=reason_str,
            intraday_return=intraday_return,
            panic_score=min(1.0, panic_score),
        )
