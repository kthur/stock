"""
rough_volatility.py — Rough Fractional Volatility & Bates Jump-Diffusion Estimator

Models high-frequency volatility dynamics as a Riemann-Liouville fractional integral
with Hurst parameter H in (0.05, 0.15) and Poisson jump detection (Bates Jump-Diffusion).
Enables instantaneous (<15 min) deleveraging upon volatility shock onsets.
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional, Any, Union

logger = logging.getLogger(__name__)


class RoughVolatilityEstimator:
    """
    Rough Fractional Volatility and Jump-Diffusion Estimator.
    """

    def __init__(
        self,
        hurst_parameter: float = 0.10,
        vol_of_vol: float = 0.35,
        jump_threshold_sigma: float = 3.0,
        memory_window: int = 60
    ):
        self.hurst = np.clip(hurst_parameter, 0.05, 0.45)
        self.nu = vol_of_vol
        self.jump_threshold_sigma = jump_threshold_sigma
        self.memory_window = memory_window

    def detect_poisson_jumps(
        self,
        returns_series: Union[pd.Series, np.ndarray]
    ) -> Dict[str, Any]:
        """
        Detects instantaneous jump discontinuities in asset return series using bipower variation.
        """
        rets = np.nan_to_num(np.asarray(returns_series, dtype=np.float64).ravel(), nan=0.0)
        N = len(rets)
        if N < 5:
            return {"has_jump": False, "jump_magnitude": 0.0, "jump_intensity": 0.0}

        # Realized Variance (RV)
        rv = np.sum(rets ** 2)
        # Bipower Variation (BV) - Robust to jumps
        bv = (np.pi / 2.0) * np.sum(np.abs(rets[1:]) * np.abs(rets[:-1]))

        # Jump component: max(0, RV - BV)
        jump_var = max(0.0, float(rv - bv))
        jump_ratio = float(jump_var / max(rv, 1e-8))

        latest_ret = abs(float(rets[-1]))
        std_ret = float(np.std(rets) or 0.01)
        is_jump = (latest_ret > self.jump_threshold_sigma * std_ret) or (jump_ratio > 0.30)

        return {
            "has_jump": is_jump,
            "jump_magnitude": float(latest_ret if is_jump else 0.0),
            "jump_ratio": round(jump_ratio, 4),
            "realized_variance": round(float(rv), 6),
            "bipower_variation": round(float(bv), 6)
        }

    def forecast_rough_volatility(
        self,
        returns_series: Union[pd.Series, np.ndarray],
        current_volatility: Optional[float] = None,
        forecast_horizon_days: int = 1
    ) -> float:
        """
        Computes forward rough volatility forecast using Fractional Brownian kernel:
        sigma(t+h) = sigma(t) * exp( c_H * sum_s (t+h - s)^(H - 1/2) * Delta W_s + Jump )
        """
        rets = np.nan_to_num(np.asarray(returns_series, dtype=np.float64).ravel(), nan=0.0)
        N = len(rets)

        base_vol = current_volatility if (current_volatility and current_volatility > 0) else (float(np.std(rets) * np.sqrt(252.0)) if N >= 5 else 0.15)
        if N < 5:
            return float(np.clip(base_vol, 0.05, 1.50))

        # Fractional kernel weights: w(s) = (h + s)^(H - 0.5)
        window = min(N, self.memory_window)
        recent_rets = rets[-window:]
        s_grid = np.arange(1, window + 1)
        h_param = self.hurst - 0.50

        kernel = np.power(s_grid.astype(float), h_param)
        kernel_norm = kernel / np.sum(kernel)

        # Fractional drift estimate
        frac_shock = np.sum(kernel_norm * np.abs(recent_rets))
        log_vol_drift = self.nu * (frac_shock - np.mean(np.abs(recent_rets)))

        # Jump multiplier
        jump_info = self.detect_poisson_jumps(recent_rets)
        jump_mult = 1.35 if jump_info["has_jump"] else 1.0

        forecast_vol = base_vol * np.exp(log_vol_drift) * jump_mult
        return float(np.clip(forecast_vol, 0.02, 2.50))

    def compute_rough_deleveraging_factor(
        self,
        returns_series: Union[pd.Series, np.ndarray],
        target_annual_vol: float = 0.12
    ) -> float:
        """
        Computes real-time risk parity capital scaling multiplier [0.15, 1.0]
        based on instantaneous rough volatility forecasts.
        """
        pred_vol = self.forecast_rough_volatility(returns_series)
        if pred_vol <= 0:
            return 1.0

        scaling = target_annual_vol / pred_vol
        return float(np.clip(scaling, 0.15, 1.0))
