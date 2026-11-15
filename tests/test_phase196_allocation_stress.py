"""
tests/test_phase196_allocation_stress.py
========================================
Adversarial Empirical Stress Harness for Milestone 2 Feature F974
(Unified Portfolio Allocator Phase 196 / Release R186).

Author: challenger_r186_m2_1
"""

import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.risk.unified_portfolio_allocator import (
    UnifiedPortfolioAllocator,
    AllocationResult,
    allocate_portfolio_phase196,
    FRONTIER_LIMITS_PHASE196,
    TARGET_VOLS_PHASE196,
)


class TestStressVIXContangoLockBoundary:
    """Stress test the 10D contango lock boundary and input mechanisms."""

    def test_10d_contango_lock_success_reaches_2_45x(self):
        """10 consecutive contango days should unlock 2.45x in BULL_STABLE."""
        vts = {"vix1m": 14.0, "vix3m": 18.0, "contango_days": 10}
        res = allocate_portfolio_phase196(
            alpha_vector={"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0, "E": 1.0},
            regime="BULL_STABLE",
            vix_term_structure=vts,
            contango_days=10,
            vts_ratio=0.85,
        )
        assert math.isclose(res["gross_leverage"], 2.45, abs_tol=1e-3), f"Expected 2.45x, got {res['gross_leverage']}"
        assert res.metadata.get("contango_locked") is True

    def test_9d_contango_lock_failure_caps_at_1_45x(self):
        """9 consecutive contango days must strictly cap at <= 1.45x in BULL_STABLE."""
        vts = {"vix1m": 14.0, "vix3m": 18.0, "contango_days": 9}
        res = allocate_portfolio_phase196(
            alpha_vector={"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0, "E": 1.0},
            regime="BULL_STABLE",
            vix_term_structure=vts,
            contango_days=9,
            vts_ratio=0.85,
        )
        assert res["gross_leverage"] <= 1.45 + 1e-4, f"Expected <= 1.45x, got {res['gross_leverage']}"
        assert res.metadata.get("contango_locked") is False

    def test_0d_contango_lock_failure_caps_at_1_45x(self):
        """0 contango days must strictly cap at <= 1.45x in BULL_STABLE."""
        vts = {"vix1m": 14.0, "vix3m": 18.0, "contango_days": 0}
        res = allocate_portfolio_phase196(
            alpha_vector={"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0, "E": 1.0},
            regime="BULL_STABLE",
            vix_term_structure=vts,
            contango_days=0,
            vts_ratio=0.85,
        )
        assert res["gross_leverage"] <= 1.45 + 1e-4, f"Expected <= 1.45x, got {res['gross_leverage']}"
        assert res.metadata.get("contango_locked") is False

    def test_single_corrupted_nan_vix_collapses_lock(self):
        """Corrupted/NaN VIX input must fail contango lock and collapse leverage to <= 1.45x."""
        vts = {"vix1m": float("nan"), "vix3m": 18.0, "contango_days": 10}
        res = allocate_portfolio_phase196(
            alpha_vector={"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0, "E": 1.0},
            regime="BULL_STABLE",
            vix_term_structure=vts,
            contango_days=10,
            vts_ratio=0.85,
        )
        assert res["gross_leverage"] <= 1.45 + 1e-4, f"Expected <= 1.45x on NaN VIX, got {res['gross_leverage']}"
        assert res.metadata.get("contango_locked") is False

    def test_vix_history_sequence_execution(self):
        """Stress: passing vix_history sequence must not crash with UnboundLocalError."""
        history = [{"vix1m": 14.0, "vix3m": 18.0} for _ in range(10)]
        # This will reveal UnboundLocalError in buggy code
        res = allocate_portfolio_phase196(
            alpha_vector={"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0, "E": 1.0},
            regime="BULL_STABLE",
            vix_history=history,
        )
        assert res["gross_leverage"] > 0.0


class TestStressTermStructureInversion:
    """Stress test term structure inversion and leverage capping."""

    def test_inversion_vix1m_gt_vix3m_caps_at_1_0x(self):
        """VIX 1M > 3M with VTS ratio >= 1.0 strictly caps leverage <= 1.00x in BULL_STABLE."""
        vts = {"vix1m": 25.0, "vix3m": 20.0, "contango_days": 15}
        res = allocate_portfolio_phase196(
            alpha_vector={"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0, "E": 1.0},
            regime="BULL_STABLE",
            vix_term_structure=vts,
            vts_ratio=1.25,
        )
        assert res["gross_leverage"] <= 1.00 + 1e-4, f"Expected <= 1.00x, got {res['gross_leverage']}"

    def test_inversion_in_bear_defensive_caps_at_0_40x(self):
        """In BEAR_DEFENSIVE (frontier 0.40x), backwardation should cap at <= 0.40x."""
        vts = {"vix1m": 35.0, "vix3m": 30.0}
        res = allocate_portfolio_phase196(
            alpha_vector={"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0, "E": 1.0},
            regime="BEAR_DEFENSIVE",
            vix_term_structure=vts,
            vts_ratio=1.15,
        )
        assert res["gross_leverage"] <= 0.40 + 1e-4, f"Expected <= 0.40x, got {res['gross_leverage']}"

    def test_inversion_with_lower_requested_gross_leverage(self):
        """Stress: If caller requests gross_leverage=0.30, backwardation must NOT expand leverage to 1.00x."""
        vts = {"vix1m": 25.0, "vix3m": 20.0}
        res = allocate_portfolio_phase196(
            alpha_vector={"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0, "E": 1.0},
            regime="BULL_STABLE",
            gross_leverage=0.30,
            vix_term_structure=vts,
            vts_ratio=1.20,
        )
        # Leverage should not exceed requested 0.30x!
        assert res["gross_leverage"] <= 0.30 + 1e-4, f"Bug: leverage expanded to {res['gross_leverage']} despite requested 0.30x"


class TestStressMCSICrisisBoundaries:
    """Stress test boundary transitions for MCSI crisis scores."""

    def test_mcsi_sub_1_80_boundary(self):
        """MCSI = 1.799: normal/unlocked regime allocation."""
        vts = {"vix1m": 14.0, "vix3m": 18.0, "contango_days": 10}
        res = allocate_portfolio_phase196(
            alpha_vector={"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0, "E": 1.0},
            regime="BULL_STABLE",
            vix_term_structure=vts,
            contango_days=10,
            vts_ratio=0.85,
            mcsi_score=1.799,
        )
        assert math.isclose(res["gross_leverage"], 2.45, abs_tol=1e-3)
        assert math.isclose(res["target_vol"], 0.145, abs_tol=1e-4)

    def test_mcsi_1_800_boundary(self):
        """MCSI = 1.800: defensive clamping to <= 0.25x."""
        vts = {"vix1m": 14.0, "vix3m": 18.0, "contango_days": 10}
        res = allocate_portfolio_phase196(
            alpha_vector={"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0, "E": 1.0},
            regime="BULL_STABLE",
            vix_term_structure=vts,
            contango_days=10,
            vts_ratio=0.85,
            mcsi_score=1.800,
        )
        assert res["gross_leverage"] <= 0.25 + 1e-4

    def test_mcsi_2_499_boundary(self):
        """MCSI = 2.499: defensive clamping to <= 0.25x."""
        vts = {"vix1m": 14.0, "vix3m": 18.0, "contango_days": 10}
        res = allocate_portfolio_phase196(
            alpha_vector={"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0, "E": 1.0},
            regime="BULL_STABLE",
            vix_term_structure=vts,
            contango_days=10,
            vts_ratio=0.85,
            mcsi_score=2.499,
        )
        assert res["gross_leverage"] <= 0.25 + 1e-4
        assert res["gross_leverage"] > 0.0

    def test_mcsi_2_500_unconditional_crisis_collapse(self):
        """MCSI = 2.500: unconditional collapse to gross leverage 0.00x and target vol = 5.5%."""
        vts = {"vix1m": 14.0, "vix3m": 18.0, "contango_days": 10}
        res = allocate_portfolio_phase196(
            alpha_vector={"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0, "E": 1.0},
            regime="BULL_STABLE",
            vix_term_structure=vts,
            contango_days=10,
            vts_ratio=0.85,
            mcsi_score=2.500,
        )
        assert math.isclose(res["gross_leverage"], 0.0, abs_tol=1e-6)
        assert math.isclose(res["net_leverage"], 0.0, abs_tol=1e-6)
        assert math.isclose(res["target_vol"], 0.055, abs_tol=1e-4)


class TestStressCovarianceAndVolatilityShocks:
    """Stress test singular covariance matrices and extreme volatility shocks."""

    def test_zero_covariance_matrix(self):
        """Covariance matrix of all zeros must not crash or yield NaN."""
        cov = np.zeros((5, 5), dtype=np.float64)
        res = allocate_portfolio_phase196(
            alpha_vector={"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.4, "E": 0.2},
            cov_matrix=cov,
            regime="BULL_STABLE",
        )
        assert res["gross_leverage"] > 0.0
        for w in res["weights"].values():
            assert not math.isnan(w)
            assert not math.isinf(w)

    def test_rank_one_covariance_matrix(self):
        """Rank 1 covariance matrix must execute cleanly without numerical explosion."""
        cov = np.ones((5, 5), dtype=np.float64) * 0.04
        res = allocate_portfolio_phase196(
            alpha_vector={"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.4, "E": 0.2},
            cov_matrix=cov,
            regime="BULL_STABLE",
        )
        assert res["gross_leverage"] > 0.0
        for w in res["weights"].values():
            assert not math.isnan(w)
            assert not math.isinf(w)

    def test_ill_conditioned_covariance_matrix(self):
        """Covariance matrix with extreme condition number (1e14) must not produce NaNs."""
        diag = np.array([1e-7, 1e-4, 1.0, 1e4, 1e7])
        cov = np.diag(diag)
        res = allocate_portfolio_phase196(
            alpha_vector={"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.4, "E": 0.2},
            cov_matrix=cov,
            regime="BULL_STABLE",
        )
        assert res["gross_leverage"] > 0.0
        for w in res["weights"].values():
            assert not math.isnan(w)
            assert not math.isinf(w)

    def test_extreme_volatility_spike_100_pct(self):
        """Realized portfolio vol of 100% in Bull regime (target 14.5%) must scale down cleanly."""
        cov = np.eye(5, dtype=np.float64) * (1.0 ** 2)
        vts = {"vix1m": 14.0, "vix3m": 18.0, "contango_days": 10}
        res = allocate_portfolio_phase196(
            alpha_vector={"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0, "E": 1.0},
            cov_matrix=cov,
            regime="BULL_STABLE",
            vix_term_structure=vts,
            contango_days=10,
            vts_ratio=0.85,
        )
        # Port vol is ~ 2.45 / sqrt(5) = 1.09 > 0.145
        # Weights should be scaled down so gross leverage < 2.45
        assert res["gross_leverage"] < 2.45
        assert res["gross_leverage"] > 0.0
        for w in res["weights"].values():
            assert not math.isnan(w)
            assert not math.isinf(w)


class TestStressStatutoryInvariants100RandomPortfolios:
    """Stress test 100 random portfolios across all regime states."""

    REGIMES = [
        "BULL_STABLE", "BULL_LOW_VOL", "BULL_TRENDING", "BULL", "BULL_VOLATILE", "BULL_HIGH_VOL",
        "RELIEF_RALLY", "SIDEWAYS_STABLE", "NEUTRAL_EXPANSION", "SIDEWAYS_LOW_VOL", "SIDEWAYS",
        "SIDEWAYS_VOLATILE", "RANGE_COMPRESSION", "SIDEWAYS_HIGH_VOL", "BEAR_TRENDING",
        "BEAR_STABLE", "BEAR_LOW_VOL", "BEAR_DEFENSIVE", "BEAR", "BEAR_VOLATILE",
        "BEAR_HIGH_VOL", "PANIC_CRISIS", "CRISIS_HALT", "CRISIS", "PANIC"
    ]

    def test_100_random_portfolios_invariant_preservation(self):
        """Verify capital conservation, net <= gross, and synthetic_rows == 0 across 100 random configs."""
        rng = np.random.default_rng(42)

        for i in range(100):
            regime = self.REGIMES[i % len(self.REGIMES)]
            n_assets = int(rng.integers(3, 15))
            symbols = [f"SYM_{j}" for j in range(n_assets)]
            alphas = {s: float(rng.uniform(-2.0, 3.0)) for s in symbols}

            # Generate random cov matrix
            A = rng.normal(0, 0.2, size=(n_assets, n_assets))
            cov = A @ A.T + np.eye(n_assets) * 0.01

            c_days = int(rng.choice([0, 5, 9, 10, 15]))
            vts_r = float(rng.choice([0.80, 0.90, 0.95, 1.05, 1.30]))
            mcsi = float(rng.choice([0.0, 0.5, 1.5, 1.80, 2.10, 2.50, 3.0]))

            res = allocate_portfolio_phase196(
                alpha_vector=alphas,
                cov_matrix=cov,
                regime=regime,
                contango_days=c_days,
                vts_ratio=vts_r,
                mcsi_score=mcsi,
            )

            # Invariant 1: Net leverage <= Gross leverage + 1e-4
            assert res["net_leverage"] <= res["gross_leverage"] + 1e-4, (
                f"Iteration {i} ({regime}): Net {res['net_leverage']} > Gross {res['gross_leverage']}"
            )

            # Invariant 2: Capital conservation is True
            assert res["capital_conservation"] is True, (
                f"Iteration {i} ({regime}): Capital conservation violated"
            )

            # Invariant 3: synthetic_rows == 0 native integer 0
            sr = res["synthetic_rows"]
            assert type(sr) is int and not isinstance(sr, bool) and sr == 0, (
                f"Iteration {i} ({regime}): synthetic_rows is {sr} ({type(sr)})"
            )

            # Invariant 4: No NaN or Inf weights
            for s, w in res["weights"].items():
                assert not math.isnan(w) and not math.isinf(w)
                assert w >= -1e-6, f"Iteration {i}: Negative weight {w} for {s}"


class TestStressAdversarialCornerCasesPhase196:
    """Adversarial probe harness for corner cases (Iteration 2).

    Author: challenger_r186_m2_it2_1
    """

    def test_gross_leverage_zero_across_all_regimes(self):
        """Passing gross_leverage=0.0 must cleanly yield 0.0 leverage and zero weights without crash."""
        for reg in ("BULL_STABLE", "SIDEWAYS", "BEAR_DEFENSIVE", "CRISIS_PANIC"):
            res = allocate_portfolio_phase196(
                alpha_vector={"AAPL": 2.5, "MSFT": 1.8, "GOOGL": -0.5},
                regime=reg,
                gross_leverage=0.0,
            )
            assert res["gross_leverage"] == 0.0, f"Failed in {reg}: {res['gross_leverage']}"
            assert res["net_leverage"] == 0.0
            assert res["capital_conservation"] is True
            assert type(res["synthetic_rows"]) is int and res["synthetic_rows"] == 0
            for w in res["weights"].values():
                assert w == 0.0

    def test_none_inputs_robustness(self):
        """Passing None for optional kwargs (mcsi_score, vts_ratio, etc.) must not raise TypeError."""
        res = allocate_portfolio_phase196(
            alpha_vector={"A": 1.0, "B": 2.0},
            regime="BULL_STABLE",
            mcsi_score=None,
            vts_ratio=None,
            gross_leverage=None,
            vix_term_structure=None,
            vix_series=None,
            vix_history=None,
            target_volatility=None,
            cov_matrix=None,
        )
        assert res["gross_leverage"] > 0.0
        assert type(res["synthetic_rows"]) is int and res["synthetic_rows"] == 0
        assert res["capital_conservation"] is True

    def test_empty_universe_under_all_crisis_regimes(self):
        """Empty universe (N=0) under crisis regimes or severe MCSI must set target_vol=0.055."""
        crisis_regimes = ("CRISIS_HALT", "CRISIS", "PANIC", "CRISIS_PANIC", "PANIC_CRISIS")
        for reg in crisis_regimes:
            res = allocate_portfolio_phase196(
                alpha_vector={},
                regime=reg,
            )
            assert res["gross_leverage"] == 0.0
            assert res["net_leverage"] == 0.0
            assert math.isclose(res["target_vol"], 0.055, abs_tol=1e-5), f"Failed in {reg}: {res['target_vol']}"
            assert res["capital_conservation"] is True
            assert type(res["synthetic_rows"]) is int and res["synthetic_rows"] == 0

        # Also test BULL_STABLE with MCSI >= 2.50 and N=0
        res_bull_mcsi = allocate_portfolio_phase196(
            alpha_vector={},
            regime="BULL_STABLE",
            mcsi_score=2.65,
        )
        assert res_bull_mcsi["gross_leverage"] == 0.0
        assert math.isclose(res_bull_mcsi["target_vol"], 0.055, abs_tol=1e-5)
        assert type(res_bull_mcsi["synthetic_rows"]) is int and res_bull_mcsi["synthetic_rows"] == 0

    def test_dual_tree_direct_execution_equivalence(self):
        """Directly import and execute from both src and trading_system trees to verify identical behavior."""
        import src.risk.unified_portfolio_allocator as src_upa
        import trading_system.src.risk.unified_portfolio_allocator as ts_upa

        inputs = {
            "alpha_vector": {"SYM_1": 1.5, "SYM_2": 2.0, "SYM_3": -0.8},
            "regime": "BULL_STABLE",
            "gross_leverage": 1.25,
            "vts_ratio": 0.88,
            "contango_days": 12,
            "mcsi_score": 0.45,
        }

        res_src = src_upa.allocate_portfolio_phase196(**inputs)
        res_ts = ts_upa.allocate_portfolio_phase196(**inputs)

        assert math.isclose(res_src["gross_leverage"], res_ts["gross_leverage"], abs_tol=1e-6)
        assert math.isclose(res_src["net_leverage"], res_ts["net_leverage"], abs_tol=1e-6)
        assert math.isclose(res_src["target_vol"], res_ts["target_vol"], abs_tol=1e-6)
        assert res_src["synthetic_rows"] == res_ts["synthetic_rows"] == 0
        assert res_src["capital_conservation"] == res_ts["capital_conservation"] is True
        for k in res_src["weights"]:
            assert math.isclose(res_src["weights"][k], res_ts["weights"][k], abs_tol=1e-6)

