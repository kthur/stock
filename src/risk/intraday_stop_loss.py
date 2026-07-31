"""
Bridge module for top-level package resolution of intraday_stop_loss.
"""

from trading_system.src.risk.intraday_stop_loss import (
    IntradayStopLossEngine,
    StopLossResult,
)

__all__ = ["IntradayStopLossEngine", "StopLossResult"]
