"""
tests/test_phase122_diffusion_volatility.py
===========================================
Verification Test Suite for:
Continuous Score-Based Generative Diffusion Volatility Surface Forecaster (Feature F580).
Phase 122 (Release R138 / v129 Production Master).
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
from pathlib import Path
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.ai.diffusion_volatility_surface_forecaster import (
    VERSION,
    RELEASE,
    FEATURE,
    MarketProfile,
    SDEType,
    DiffusionVolatilityConfig,
    VolatilitySurfaceOutput,
    ScoreDiffusionVolatilityForecaster,
    DiffusionVolatilitySurfaceForecaster,
)


class TestPhase122DiffusionVolatility:
    """Tests for Continuous Score-Based Generative Diffusion Volatility Surface Forecaster."""

    def test_tc01_version_and_metadata(self):
        """Verifies metadata constants."""
        assert VERSION == 122
        assert RELEASE == "R138"
        assert FEATURE == "F580"

    def test_tc02_dual_tree_sha256_parity(self):
        """Verifies 100% bit-for-bit SHA-256 parity between src/ and trading_system/src/."""
        f1 = PROJECT_ROOT / "src" / "ai" / "diffusion_volatility_surface_forecaster.py"
        f2 = TRADING_SYSTEM_DIR / "src" / "ai" / "diffusion_volatility_surface_forecaster.py"
        assert f1.exists(), f"File {f1} does not exist"
        assert f2.exists(), f"File {f2} does not exist"
        h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
        assert h1 == h2, f"SHA-256 mismatch: {h1} != {h2}"

    def test_tc03_market_profile_resolution(self):
        """Verifies market string resolution across 5 target markets."""
        assert ScoreDiffusionVolatilityForecaster.resolve_market("SP500") == MarketProfile.SP500
        assert ScoreDiffusionVolatilityForecaster.resolve_market("NASDAQ") == MarketProfile.NASDAQ
        assert ScoreDiffusionVolatilityForecaster.resolve_market("RUSSELL2000") == MarketProfile.RUSSELL2000
        assert ScoreDiffusionVolatilityForecaster.resolve_market("KOSPI") == MarketProfile.KOSPI
        assert ScoreDiffusionVolatilityForecaster.resolve_market("KOSDAQ") == MarketProfile.KOSDAQ

    def test_tc04_forward_marginal_params(self):
        """Tests forward SDE marginal scale and variance bounds."""
        forecaster = ScoreDiffusionVolatilityForecaster()
        m_0, s_0 = forecaster.compute_forward_marginal_params(0.0)
        assert abs(m_0 - 1.0) < 1e-4
        assert s_0 < 0.01

        m_1, s_1 = forecaster.compute_forward_marginal_params(1.0)
        assert m_1 < m_0
        assert s_1 > s_0

    def test_tc05_score_function_calculation(self):
        """Tests analytic score function computation."""
        forecaster = ScoreDiffusionVolatilityForecaster()
        noisy_vols = np.array([0.15, 0.25, 0.40])
        score = forecaster.compute_score_function(noisy_vols, t=0.5)
        assert len(score) == 3
        assert np.all(np.isfinite(score))

    def test_tc06_reverse_sde_integration(self):
        """Tests reverse-time SDE integration produces realistic volatility."""
        forecaster = ScoreDiffusionVolatilityForecaster()
        pred_vol = forecaster.integrate_reverse_sde(initial_vol=0.18, steps=25)
        assert 0.02 <= pred_vol <= 1.20
        assert math.isfinite(pred_vol)

    def test_tc07_merton_jump_estimation(self):
        """Tests Merton jump-diffusion intensity and magnitude estimation."""
        forecaster = ScoreDiffusionVolatilityForecaster()
        # Synthetic returns with 2 large jumps
        rets = np.random.normal(0.0, 0.01, 100)
        rets[10] = -0.08  # jump
        rets[50] = 0.07   # jump

        intensity, mean_j, std_j = forecaster.estimate_merton_jumps(rets)
        assert intensity > 0.0
        assert std_j > 0.0
        assert math.isfinite(intensity)

    def test_tc08_svi_surface_fitting(self):
        """Tests 3D SVI volatility surface fitting across strikes and tenors."""
        forecaster = ScoreDiffusionVolatilityForecaster()
        surface = forecaster.fit_svi_surface(atm_vol=0.20)
        # Expected shape: (len(DEFAULT_TENORS_DAYS), len(DEFAULT_STRIKE_MONEYNESS)) = (6, 9)
        assert surface.shape == (6, 9)
        assert np.all(surface > 0.0)
        assert np.all(np.isfinite(surface))
        # OTM Put (strike 0.70, idx 0) should have higher vol than OTM Call (strike 1.30, idx 8) due to negative skew
        assert surface[2, 0] > surface[2, -1]

    def test_tc09_forecast_volatility_surface_full(self):
        """Tests full end-to-end forecasting pipeline output."""
        forecaster = ScoreDiffusionVolatilityForecaster()
        prices = 100.0 * np.cumprod(1.0 + np.random.normal(0.0005, 0.012, 120))
        out = forecaster.forecast_volatility_surface(
            symbol="AAPL",
            price_series=prices,
            market="NASDAQ",
        )
        assert isinstance(out, VolatilitySurfaceOutput)
        assert out.symbol == "AAPL"
        assert out.market == "NASDAQ"
        assert out.atm_volatility > 0.0
        assert out.skew_21d > 0.0  # Put vol - Call vol > 0
        assert out.var_99 > 0.0
        assert out.cvar_99 >= out.var_99  # Expected Shortfall >= VaR
        assert len(out.conditioning_vector) == 10
        assert np.all(np.isfinite(out.conditioning_vector))

    def test_tc10_serialization_and_aliases(self):
        """Tests dictionary serialization and class alias parity."""
        assert DiffusionVolatilitySurfaceForecaster is ScoreDiffusionVolatilityForecaster
        forecaster = DiffusionVolatilitySurfaceForecaster()
        out = forecaster.forecast_volatility_surface("005930.KS", [70000.0, 71000.0, 69500.0, 70500.0, 72000.0], market="KOSPI")
        d = out.to_dict()
        assert d["symbol"] == "005930.KS"
        assert "cvar_99" in d
        assert len(d["conditioning_vector"]) == 10
