"""VCP Real-Time Breakout Trigger & Supply/Demand Alpha Engine"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _safe_series(val):
    if isinstance(val, pd.DataFrame):
        return val.iloc[:, 0]
    return val


@dataclass
class VCPBreakoutSignal:
    """Represents a real-time VCP breakout signal."""
    symbol: str
    is_breakout: bool
    pivot_price: float
    current_price: float
    volume_ratio: float
    supply_demand_score: float
    vcp_score: float
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    details: Dict[str, Any] = field(default_factory=dict)


class VCPBreakoutTrigger:
    """Detects real-time VCP breakouts during market hours and incorporates institutional/foreign supply-demand alpha."""

    def __init__(
        self,
        breakout_vol_threshold: float = 1.5,
        near_pivot_pct: float = 0.02,
        min_vcp_score: float = 50.0,
    ):
        self.breakout_vol_threshold = breakout_vol_threshold
        self.near_pivot_pct = near_pivot_pct
        self.min_vcp_score = min_vcp_score

    def calculate_pivot_price(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculates VCP Pivot Price (resistance high) and volume baseline from historical daily prices."""
        if df is None or len(df) < 50:
            return {"pivot_price": 0.0, "avg_volume_20": 0.0, "current_close": 0.0}

        df_c = df.copy()
        df_c.columns = [
            str(c).capitalize()
            if str(c).lower() in ["open", "high", "low", "close", "volume"]
            else str(c)
            for c in df_c.columns
        ]

        high = _safe_series(df_c["High"])
        close = _safe_series(df_c["Close"])
        volume = _safe_series(df_c["Volume"])

        # Pivot Price: highest high of the recent 20-day contraction window
        recent_20_high = float(high.iloc[-20:].max())
        avg_vol_20 = float(volume.iloc[-20:].mean())
        if avg_vol_20 <= 0:
            avg_vol_20 = 1.0

        current_close = float(close.iloc[-1])

        return {
            "pivot_price": recent_20_high,
            "avg_volume_20": avg_vol_20,
            "current_close": current_close,
        }

    def compute_supply_demand_score(self, df: pd.DataFrame) -> float:
        """Calculates institutional and foreign net buying supply-demand alpha score [0.0 ~ 1.0]."""
        if df is None or df.empty:
            return 0.5

        score = 0.5  # Neutral default

        inst_col = None
        for col in ["inst_net_buy_5d", "institution_net_buy", "inst_buy"]:
            if col in df.columns:
                inst_col = col
                break

        foreign_col = None
        for col in ["foreigner_net_buy_5d", "foreigner_net_buy", "foreign_buy"]:
            if col in df.columns:
                foreign_col = col
                break

        if inst_col is not None:
            inst_val = float(_safe_series(df[inst_col]).iloc[-1])
            if inst_val > 0:
                score += 0.25
            elif inst_val < 0:
                score -= 0.15

        if foreign_col is not None:
            foreign_val = float(_safe_series(df[foreign_col]).iloc[-1])
            if foreign_val > 0:
                score += 0.25
            elif foreign_val < 0:
                score -= 0.15

        return float(np.clip(score, 0.0, 1.0))

    def evaluate_realtime_breakout(
        self,
        symbol: str,
        current_price: float,
        current_volume: float,
        hist_df: pd.DataFrame,
        vcp_score: float = 60.0,
    ) -> VCPBreakoutSignal:
        """Evaluates whether current price and volume constitute a genuine VCP breakout."""
        pivot_info = self.calculate_pivot_price(hist_df)
        pivot_price = pivot_info["pivot_price"]
        avg_vol_20 = pivot_info["avg_volume_20"]

        if pivot_price <= 0 or avg_vol_20 <= 0:
            return VCPBreakoutSignal(
                symbol=symbol,
                is_breakout=False,
                pivot_price=pivot_price,
                current_price=current_price,
                volume_ratio=0.0,
                supply_demand_score=0.5,
                vcp_score=vcp_score,
                details={"reason": "Insufficient historical data"},
            )

        vol_ratio = current_volume / avg_vol_20 if avg_vol_20 > 0 else 1.0
        sd_score = self.compute_supply_demand_score(hist_df)

        # Breakout Condition:
        # 1. current_price >= pivot_price * (1.0 - near_pivot_pct)
        # 2. volume_ratio >= breakout_vol_threshold (1.5x)
        # 3. vcp_score >= min_vcp_score
        price_condition = current_price >= (pivot_price * (1.0 - self.near_pivot_pct))
        vol_condition = vol_ratio >= self.breakout_vol_threshold
        score_condition = vcp_score >= self.min_vcp_score

        is_breakout = price_condition and vol_condition and score_condition

        details = {
            "price_condition": price_condition,
            "vol_condition": vol_condition,
            "score_condition": score_condition,
            "pivot_price": pivot_price,
            "vol_ratio": round(vol_ratio, 2),
            "sd_score": round(sd_score, 2),
        }

        if is_breakout:
            logger.info(
                f"[VCP REALTIME BREAKOUT] Symbol {symbol}: Current {current_price} >= Pivot {pivot_price}, "
                f"Vol Ratio {vol_ratio:.2f}x >= {self.breakout_vol_threshold}x, SD Score {sd_score:.2f}"
            )

        return VCPBreakoutSignal(
            symbol=symbol,
            is_breakout=is_breakout,
            pivot_price=pivot_price,
            current_price=current_price,
            volume_ratio=float(round(vol_ratio, 2)),
            supply_demand_score=sd_score,
            vcp_score=vcp_score,
            details=details,
        )
