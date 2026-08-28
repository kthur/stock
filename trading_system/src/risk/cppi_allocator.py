"""
cppi_allocator.py — Constant Proportion Portfolio Insurance (CPPI) Drawdown Cushion Engine

Mitigates compounding path-dependent volatility drag (-0.5 * sigma^2 * L^2) and protects
capital against drawdown limits by dynamically scaling leverage based on the distance
between current NAV and the guaranteed floor NAV.
"""

from __future__ import annotations

import logging
import numpy as np
from typing import Dict, Any

logger = logging.getLogger(__name__)


class CPPIDrawdownCushionEngine:
    """
    CPPI Asymmetric Drawdown Cushion and Volatility Drag Mitigation Allocator.
    """

    def __init__(
        self,
        max_tolerable_drawdown: float = 0.06, # Max tolerable drawdown before hard cash exit (6%)
        cppi_multiplier: float = 4.0,        # Standard CPPI multiplier M
        max_leverage: float = 1.50,          # Maximum allowable portfolio gross leverage
        min_cushion_buffer: float = 0.005     # 50 bps buffer before complete liquidation
    ):
        self.max_dd = max_tolerable_drawdown
        self.M = cppi_multiplier
        self.max_leverage = max_leverage
        self.min_cushion_buffer = min_cushion_buffer

    def compute_drawdown_floor(
        self,
        peak_nav: float
    ) -> float:
        """
        Calculates guaranteed floor NAV: Floor_t = (1 - MaxDD) * PeakNAV
        """
        return float(max(0.0, (1.0 - self.max_dd) * peak_nav))

    def compute_cushion(
        self,
        current_nav: float,
        peak_nav: float
    ) -> Dict[str, float]:
        """
        Calculates drawdown cushion: Cushion_t = max(0, (NAV_t - Floor_t) / NAV_t)
        """
        if current_nav <= 0 or peak_nav <= 0:
            return {"cushion": 0.0, "floor_nav": 0.0, "current_drawdown": 1.0}

        effective_peak = max(current_nav, peak_nav)
        floor_nav = self.compute_drawdown_floor(effective_peak)

        cushion = max(0.0, float((current_nav - floor_nav) / current_nav))
        curr_dd = float((effective_peak - current_nav) / effective_peak)

        return {
            "cushion": round(cushion, 6),
            "floor_nav": round(floor_nav, 2),
            "current_drawdown": round(curr_dd, 6)
        }

    def calculate_asymmetric_exposure(
        self,
        expected_return_annual: float,
        annual_volatility: float,
        current_nav: float,
        peak_nav: float,
        risk_free_rate: float = 0.035
    ) -> Dict[str, Any]:
        """
        Calculates optimal asymmetric risk asset allocation:
        Exposure_t = min(MaxLeverage, M * Cushion_t * (mu_t - rf) / sigma_t^2)
        """
        cushion_info = self.compute_cushion(current_nav, peak_nav)
        cushion = cushion_info["cushion"]

        # Hard boundary gating near floor
        if cushion <= self.min_cushion_buffer:
            return {
                "target_gross_exposure": 0.0,
                "cash_weight": 1.0,
                "is_floor_breached": True,
                "cushion_info": cushion_info
            }

        vol = max(annual_volatility, 0.04)
        excess_return = max(0.0, expected_return_annual - risk_free_rate)

        # Kelly-adjusted Sharpe loading
        sharpe_loading = excess_return / (vol ** 2) if vol > 0 else 1.0
        # CPPI Cushion exposure
        target_exposure = self.M * cushion * np.clip(sharpe_loading, 0.20, 2.50)
        final_exposure = float(np.clip(target_exposure, 0.0, self.max_leverage))
        cash_weight = max(0.0, float(1.0 - final_exposure))

        return {
            "target_gross_exposure": round(final_exposure, 4),
            "cash_weight": round(cash_weight, 4),
            "is_floor_breached": False,
            "cushion_info": cushion_info
        }

    def calculate_volatility_drag_loss(
        self,
        annual_volatility: float,
        leverage: float,
        time_horizon_years: float = 1.0
    ) -> float:
        """
        Estimates continuous compounding volatility drag:
        VolDrag = 0.5 * sigma^2 * L^2 * dt (in bps)
        """
        drag = 0.5 * (annual_volatility ** 2) * (leverage ** 2) * time_horizon_years
        return round(float(drag * 10000.0), 2)
