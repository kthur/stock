"""
tests/test_adversarial_phase182_stress_deep.py
=============================================
Deep Empirical Adversarial Stress Harness for Release R180 Milestone M3 (Phase 182).
Challenger Agent: challenger_m3_it2_2

Adversarial Stress Dimensions:
1. Defect 1: Tail index xi clamping across 10 diverse distributions (light to super-heavy, degenerate, single and multi-asset).
2. Defect 2: Fresh entry zero-bypass across dense weight grids (1e-6 to 0.10), full liquidations, 500-asset heterogeneous rebalances.
3. Defect 3: Numerical resilience under single NaN, 100% NaNs, +/-Inf, extreme scale 10^15, None values.
4. Defect 4: Invariant compliance (synthetic_rows == 0 strictly int) on empty dict, empty Series, empty list across all 9 regimes.
5. F890 Hyperbolic Barycenter: Curvature sensitivity, metric axioms, mass conservation.
"""

from __future__ import annotations

import math
import os
import sys
import unittest
from typing import Dict, Any, List

import numpy as np
import pandas as pd
import pytest

# Ensure repo root is on sys.path
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.risk.evt_tail_risk import (
    fit_generalized_pareto,
    compute_evt_var_cvar,
    compute_spectral_expected_shortfall,
    compute_spectral_evt_cvar_risk_budget,
    SpectralEVTCVaRBudgetingEngine,
)
from src.risk.spectral_evt_cvar_allocator import (
    compute_evt_cvar_spectral_budget as standalone_evt_budget,
)
from src.risk.portfolio_allocator import PortfolioAllocator
from src.execution.leland_buffer_bands import (
    compute_asymmetric_leland_bands,
    is_zero_bypass_eligible,
    filter_portfolio_rebalance,
    AsymmetricLelandTurnoverOptimizer,
)
from src.risk.unified_portfolio_allocator import (
    UnifiedPortfolioAllocator,
    allocate_portfolio_phase182,
    AllocationResult,
)
from src.risk.hyperbolic_optimal_transport_allocator import (
    compute_poincare_wasserstein_barycenter,
    HyperbolicOptimalTransportAllocator,
)


class TestAdversarialPhase182DeepStress(unittest.TestCase):
    """Deep adversarial stress harness for Phase 182 risk and allocation engines."""

    # =========================================================================
    # AREA 1: Defect 1 Deep Stress (EVT Clamped Tail Index xi in [0.05, 0.45])
    # =========================================================================

    def test_deep01_evt_clamping_across_10_distributions_single_asset(self):
        """DEEP01: Validate xi in [0.05, 0.45] across 10 distinct return distributions in single-asset pipeline."""
        np.random.seed(42)
        n_samples = 1500

        distributions = {
            "Standard_Normal": np.random.randn(n_samples) * 0.02,
            "Uniform_Light": np.random.uniform(-0.03, 0.03, size=n_samples),
            "Exponential_Laplace": (np.random.exponential(scale=0.01, size=n_samples) - 0.01),
            "StudentT_df30": np.random.standard_t(df=30, size=n_samples) * 0.02,
            "StudentT_df10": np.random.standard_t(df=10, size=n_samples) * 0.02,
            "StudentT_df3": np.random.standard_t(df=3, size=n_samples) * 0.02,
            "StudentT_df2.1": np.random.standard_t(df=2.1, size=n_samples) * 0.02,
            "StudentT_df1.05_Cauchy": np.clip(np.random.standard_t(df=1.05, size=n_samples) * 0.02, -10.0, 10.0),
            "Pareto_Alpha1.5": (np.random.pareto(a=1.5, size=n_samples) * 0.01 - 0.02),
            "Degenerate_Zero": np.zeros(n_samples),
        }

        for dist_name, returns in distributions.items():
            with self.subTest(distribution=dist_name):
                # 1. Direct standalone budget
                res = standalone_evt_budget(returns, alpha=0.95, gamma=3.0, xi_bounds=(0.05, 0.45))
                xi = res["xi_clamped"]
                self.assertGreaterEqual(
                    xi, 0.05 - 1e-6,
                    f"[{dist_name}] xi_clamped {xi} strictly below min 0.05"
                )
                self.assertLessEqual(
                    xi, 0.45 + 1e-6,
                    f"[{dist_name}] xi_clamped {xi} strictly above max 0.45"
                )
                self.assertGreater(res["beta_scale"], 0.0)
                self.assertGreater(res["spectral_budget"], 0.0)
                self.assertEqual(res["synthetic_rows"], 0)
                self.assertIs(type(res["synthetic_rows"]), int)

                # 2. PortfolioAllocator engine
                alloc = PortfolioAllocator()
                res_pa = alloc.compute_evt_cvar_spectral_budget(returns, alpha=0.95, gamma=3.0)
                xi_pa = res_pa.get("xi_shape", res_pa.get("xi_clamped"))
                self.assertIsNotNone(xi_pa)
                self.assertGreaterEqual(xi_pa, 0.05 - 1e-6)
                self.assertLessEqual(xi_pa, 0.45 + 1e-6)

    def test_deep02_evt_clamping_multi_asset_mixtures(self):
        """DEEP02: Multi-asset (N=10) with heterogeneous mixture of light and heavy tail distributions."""
        np.random.seed(999)
        T = 800
        # Create 10 assets with varying tail fatness
        R = np.column_stack([
            np.random.randn(T) * 0.01,                            # Asset 0: Gaussian
            np.random.uniform(-0.02, 0.02, size=T),               # Asset 1: Uniform
            np.random.standard_t(df=2.1, size=T) * 0.02,          # Asset 2: Student-t df=2.1
            np.random.standard_t(df=1.5, size=T) * 0.02,          # Asset 3: Student-t df=1.5
            np.random.standard_t(df=5.0, size=T) * 0.02,          # Asset 4: Student-t df=5.0
            np.random.randn(T) * 0.05,                            # Asset 5: High vol Gaussian
            np.random.standard_t(df=20, size=T) * 0.01,           # Asset 6: Quasi-Gaussian
            np.clip(np.random.standard_t(df=1.05, size=T) * 0.01, -5.0, 5.0), # Asset 7: Cauchy-like
            np.random.exponential(scale=0.01, size=T) - 0.01,     # Asset 8: Asymmetric
            np.zeros(T),                                          # Asset 9: Flat cash-like
        ])

        budget = compute_spectral_evt_cvar_risk_budget(R, alpha=0.95, gamma=4.0, xi_bounds=(0.05, 0.45))

        self.assertGreaterEqual(budget["xi_clamped"], 0.05)
        self.assertLessEqual(budget["xi_clamped"], 0.45)
        self.assertEqual(len(budget["risk_budget_weights"]), 10)
        self.assertAlmostEqual(float(np.sum(budget["risk_budget_weights"])), 1.0, places=4)
        for w in budget["risk_budget_weights"]:
            self.assertGreaterEqual(w, 0.0)
            self.assertTrue(math.isfinite(w))
        self.assertEqual(budget["synthetic_rows"], 0)
        self.assertIs(type(budget["synthetic_rows"]), int)

    def test_deep03_spectral_expected_shortfall_forwarding(self):
        """DEEP03: Verify compute_spectral_expected_shortfall clamps xi directly without unconstrained drift."""
        # For a uniform distribution, Hill / moment estimators yield negative shape
        losses = np.random.uniform(-0.05, 0.05, size=2000)
        ses = compute_spectral_expected_shortfall(losses, gamma=3.0, min_xi=0.05, max_xi=0.45)
        self.assertGreater(ses, 0.0)
        self.assertTrue(math.isfinite(ses))

    # =========================================================================
    # AREA 2: Defect 2 Deep Stress (Leland Zero-Bypass Threshold & Execution)
    # =========================================================================

    def test_deep04_leland_fresh_entry_dense_grid(self):
        """DEEP04: Dense grid of fresh entry weights: test exact cutoff at 1e-4 threshold."""
        grid = [
            (0.0, 1e-6, "HOLD", 0.0),         # Sub-threshold: ignored as noise
            (0.0, 5e-5, "HOLD", 0.0),         # Sub-threshold: ignored
            (0.0, 1e-4, "HOLD", 0.0),         # Boundary (<= 1e-4): ignored
            (0.0, 1.0001e-4, "BYPASS_ENTRY", 1.0001e-4), # Just above threshold: immediate entry!
            (0.0, 0.0005, "BYPASS_ENTRY", 0.0005),       # 5 bps
            (0.0, 0.0010, "BYPASS_ENTRY", 0.0010),       # 10 bps
            (0.0, 0.0020, "BYPASS_ENTRY", 0.0020),       # 20 bps (defect case)
            (0.0, 0.0049, "BYPASS_ENTRY", 0.0049),       # 49 bps (previously blocked by 0.005)
            (0.0, 0.0050, "BYPASS_ENTRY", 0.0050),       # 50 bps (previously boundary)
            (0.0, 0.0051, "BYPASS_ENTRY", 0.0051),       # 51 bps
            (0.0, 0.0500, "BYPASS_ENTRY", 0.0500),       # 500 bps
        ]

        for c_w, t_w, expected_action, expected_exec in grid:
            with self.subTest(c_w=c_w, t_w=t_w):
                out = filter_portfolio_rebalance({"SYM": c_w}, {"SYM": t_w})
                self.assertEqual(
                    out.actions["SYM"], expected_action,
                    f"Failed action for c_w={c_w}, t_w={t_w}: got {out.actions['SYM']}"
                )
                self.assertAlmostEqual(
                    out.executable_weights["SYM"], expected_exec, places=6,
                    msg=f"Failed executable weight for c_w={c_w}, t_w={t_w}"
                )

    def test_deep05_leland_full_exit_dense_grid(self):
        """DEEP05: Full liquidation must bypass buffer for positions large and small."""
        exit_weights = [0.0002, 0.001, 0.005, 0.02, 0.10]
        for c_w in exit_weights:
            with self.subTest(c_w=c_w):
                out = filter_portfolio_rebalance({"SYM": c_w}, {"SYM": 0.0})
                self.assertEqual(out.actions["SYM"], "BYPASS_EXIT")
                self.assertAlmostEqual(out.executable_weights["SYM"], 0.0, places=6)

    def test_deep06_500_asset_heterogeneous_portfolio_rebalance(self):
        """DEEP06: Stress test 500-asset portfolio with 100 entries, 100 exits, 200 micro-shifts, 100 rebalances."""
        np.random.seed(777)
        N = 500
        syms = [f"STK_{i:04d}" for i in range(N)]

        curr_w = {}
        tgt_w = {}
        expected_bypass_entries = set()
        expected_bypass_exits = set()
        expected_holds = set()
        expected_rebalances = set()

        for i, sym in enumerate(syms):
            if i < 100:
                # Fresh entry (small to medium weight: 0.0005 to 0.0050)
                curr_w[sym] = 0.0
                tgt_w[sym] = 0.0005 + (i * 0.000045)
                expected_bypass_entries.add(sym)
            elif i < 200:
                # Full exit
                curr_w[sym] = 0.0010 + ((i - 100) * 0.00004)
                tgt_w[sym] = 0.0
                expected_bypass_exits.add(sym)
            elif i < 400:
                # Micro shift well within the Leland band (shift < 0.001, min_bandwidth >= 0.005)
                base = 0.0020
                curr_w[sym] = base
                tgt_w[sym] = base + 0.0002 * np.random.uniform(-1, 1)
                expected_holds.add(sym)
            else:
                # Large rebalance exceeding the band (shift = 0.08, well above 0.035 band)
                curr_w[sym] = 0.0020
                tgt_w[sym] = 0.0820
                expected_rebalances.add(sym)

        out = filter_portfolio_rebalance(curr_w, tgt_w)

        # 1. Check all fresh entries were bypassed
        for sym in expected_bypass_entries:
            self.assertEqual(out.actions[sym], "BYPASS_ENTRY", f"{sym} should be BYPASS_ENTRY")
            self.assertAlmostEqual(out.executable_weights[sym], tgt_w[sym], places=5)

        # 2. Check all full exits were bypassed
        for sym in expected_bypass_exits:
            self.assertEqual(out.actions[sym], "BYPASS_EXIT", f"{sym} should be BYPASS_EXIT")
            self.assertAlmostEqual(out.executable_weights[sym], 0.0, places=5)

        # 3. Check all micro shifts were held
        for sym in expected_holds:
            self.assertEqual(out.actions[sym], "HOLD", f"{sym} should be HOLD")
            self.assertAlmostEqual(out.executable_weights[sym], curr_w[sym], places=5)

        # 4. Check all large rebalances executed
        for sym in expected_rebalances:
            self.assertEqual(out.actions[sym], "BUY", f"{sym} should be BUY")
            self.assertAlmostEqual(out.executable_weights[sym], tgt_w[sym], places=5)

        self.assertEqual(out.synthetic_rows, 0)
        self.assertIs(type(out.synthetic_rows), int)

    # =========================================================================
    # AREA 3: Defect 3 Deep Stress (NaN / Inf / Extreme Numerical Resilience)
    # =========================================================================

    def test_deep07_nan_and_inf_scenarios_in_allocator(self):
        """DEEP07: Stress test alpha vectors containing various NaN, Inf, and extreme combinations."""
        alloc = UnifiedPortfolioAllocator()

        scenarios = {
            "Single_NaN": {"A": 1.0, "B": np.nan, "C": 2.0},
            "Multiple_NaNs": {f"SYM_{i}": (np.nan if i % 2 == 0 else float(i)) for i in range(10)},
            "All_NaNs": {"X": np.nan, "Y": np.nan, "Z": np.nan},
            "Positive_Inf": {"A": 1.0, "B": np.inf, "C": 2.0},
            "Negative_Inf": {"A": 1.0, "B": -np.inf, "C": 2.0},
            "Both_Infs": {"A": np.inf, "B": -np.inf, "C": 1.0},
            "NaN_and_Inf": {"A": np.nan, "B": np.inf, "C": -np.inf, "D": 2.0},
            "Extreme_Magnitude": {"A": 1e12, "B": -1e12, "C": 0.0},
            "Series_With_None": pd.Series([1.5, None, 2.5], index=["A", "B", "C"], dtype=object),
        }

        for scen_name, alphas in scenarios.items():
            with self.subTest(scenario=scen_name):
                res = alloc.allocate_portfolio_phase182(alphas, regime="BULL_LOW_VOL")
                self.assertIsInstance(res, AllocationResult)
                self.assertGreaterEqual(len(res.target_weights), 1)

                # Weights must all be finite and non-negative
                for sym, w in res.target_weights.items():
                    self.assertTrue(math.isfinite(w), f"[{scen_name}] Symbol {sym} weight {w} is not finite!")
                    self.assertGreaterEqual(w, 0.0, f"[{scen_name}] Symbol {sym} weight {w} is negative!")

                # Capital conservation
                self.assertLessEqual(
                    res.net_leverage, res.gross_leverage + 1e-4,
                    f"[{scen_name}] Net leverage {res.net_leverage} > gross {res.gross_leverage}"
                )
                self.assertEqual(res.metadata["synthetic_rows"], 0)
                self.assertIs(type(res.metadata["synthetic_rows"]), int)

    def test_deep08_nan_alpha_with_leland_filter(self):
        """DEEP08: Allocate with NaN in alpha AND apply_leland=True with current_weights."""
        alloc = UnifiedPortfolioAllocator()
        alphas = {"AAPL": 2.0, "MSFT": np.nan, "GOOG": 1.0}
        curr_w = {"AAPL": 0.05, "MSFT": 0.05, "GOOG": 0.0}

        res = alloc.allocate_portfolio_phase182(
            alphas,
            current_weights=curr_w,
            apply_leland=True,
            regime="BULL_LOW_VOL",
        )

        for sym, w in res.target_weights.items():
            self.assertTrue(math.isfinite(w))
            self.assertGreaterEqual(w, 0.0)
        self.assertEqual(res.metadata["synthetic_rows"], 0)

    # =========================================================================
    # AREA 4: Defect 4 Deep Stress (Empty Portfolios & Invariants Across 9 Regimes)
    # =========================================================================

    def test_deep09_empty_portfolios_across_all_9_regimes(self):
        """DEEP09: Empty inputs (dict, Series, list) across all 9 regimes must satisfy synthetic_rows == 0 strictly int."""
        alloc = UnifiedPortfolioAllocator()
        all_regimes = [
            "BULL_LOW_VOL", "RELIEF_RALLY", "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL", "BEAR_HIGH_VOL",
            "PANIC_CRISIS", "CRISIS"
        ]

        empty_inputs = [
            ("Empty_Dict", {}),
            ("Empty_Series", pd.Series({}, dtype=float)),
            ("Empty_List", []),
        ]

        for reg in all_regimes:
            for inp_name, inp in empty_inputs:
                with self.subTest(regime=reg, input_type=inp_name):
                    res = alloc.allocate_portfolio_phase182(inp, regime=reg)
                    self.assertEqual(res.target_weights, {})
                    self.assertEqual(res.net_leverage, 0.0)
                    self.assertEqual(res.gross_leverage, 0.0)
                    self.assertEqual(res.regime, reg)
                    self.assertIn("synthetic_rows", res.metadata)
                    self.assertEqual(res.metadata["synthetic_rows"], 0)
                    self.assertIs(type(res.metadata["synthetic_rows"]), int)
                    self.assertEqual(res.metadata["symbols_count"], 0)

    def test_deep10_single_asset_portfolio(self):
        """DEEP10: Single-asset portfolio behaves predictably and respects concentration caps."""
        alloc = UnifiedPortfolioAllocator()
        res = alloc.allocate_portfolio_phase182({"SOLO": 3.0}, regime="BULL_LOW_VOL")
        self.assertEqual(len(res.target_weights), 1)
        # Concentration cap max(0.05 * lev, lev / 1) -> 1.95
        self.assertAlmostEqual(res.target_weights["SOLO"], 1.95, places=3)
        self.assertEqual(res.metadata["synthetic_rows"], 0)

    # =========================================================================
    # AREA 5: Feature F890 Deep Stress (Poincaré Barycenter Geometry)
    # =========================================================================

    def test_deep11_poincare_barycenter_curvature_modulation_and_metric_axioms(self):
        """DEEP11: Test that curvature c genuinely modulates weights, satisfies metric identity, and conserves mass."""
        np.random.seed(42)
        n = 5
        coords = np.array([
            [0.1, 0.2],
            [-0.3, 0.1],
            [0.0, -0.4],
            [0.2, -0.2],
            [-0.1, -0.1],
        ])
        w_c = np.array([0.4, 0.1, 0.2, 0.1, 0.2])
        w_t = np.array([0.1, 0.3, 0.1, 0.4, 0.1])

        # 1. Curvature modulation: allocations must differ as curvature changes
        res_c01 = compute_poincare_wasserstein_barycenter(w_c, w_t, curvature=0.1)
        res_c10 = compute_poincare_wasserstein_barycenter(w_c, w_t, curvature=1.0)
        res_c50 = compute_poincare_wasserstein_barycenter(w_c, w_t, curvature=5.0)

        # Confirm non-trivial difference across curvatures
        diff_01_10 = np.linalg.norm(res_c01["barycenter_weights"] - res_c10["barycenter_weights"])
        diff_10_50 = np.linalg.norm(res_c10["barycenter_weights"] - res_c50["barycenter_weights"])
        self.assertGreater(diff_01_10, 1e-4, "Curvature c=0.1 vs c=1.0 produced identical weights!")
        self.assertGreater(diff_10_50, 1e-4, "Curvature c=1.0 vs c=5.0 produced identical weights!")

        # 2. Metric identity: d_P(w_c, w_c) -> 0.0 as entropic regularization bias -> 0
        res_self = compute_poincare_wasserstein_barycenter(w_c, w_c, curvature=1.0, epsilon=0.001)
        self.assertAlmostEqual(res_self["hyperbolic_geodesic_distance"], 0.0, places=5)
        np.testing.assert_allclose(res_self["barycenter_weights"], w_c, atol=1e-5)

        # 3. Mass conservation: sum of weights equals target mass L
        for res in [res_c01, res_c10, res_c50]:
            self.assertAlmostEqual(float(np.sum(res["barycenter_weights"])), 1.0, places=5)
            self.assertEqual(res["synthetic_rows"], 0)
            self.assertIs(type(res["synthetic_rows"]), int)


if __name__ == "__main__":
    unittest.main()
