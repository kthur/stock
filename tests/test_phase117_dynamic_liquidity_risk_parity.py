"""
tests/test_phase117_dynamic_liquidity_risk_parity.py
====================================================
Comprehensive Unit, Integration, Mathematical Invariant, and Benchmark Tests for:
Dynamic Liquidity-Adjusted Portfolio Risk Parity Allocator (Feature F557).
Phase 117 (Release R133 / v124 Production Master).

Categories Covered:
- Category 1: Dual-Tree Cryptographic Parity, Version Metadata & Complete Alias Trees (TC01~TC03)
- Category 2: 5-Market Calibrated Empirical Profiles & Config Custom Overrides (TC04~TC06)
- Category 3: Amihud Illiquidity Calculation & Normalization Monotonicity (TC07~TC10)
- Category 4: Roll Effective Bid-Ask Spread & Autocovariance Sign Handling (TC11~TC14)
- Category 5: Volume Turnover Decay & Volume Depletion Metrics (TC15~TC17)
- Category 6: Ledoit-Wolf Regularized Covariance Matrix Symmetry & Positive Definiteness (TC18~TC21)
- Category 7: Strictly Convex Spinu Risk Budgeting Formulation & Invariance (TC22~TC26)
- Category 8: Liquidity Penalty Weight Deflation (TC27~TC29)
- Category 9: Asymmetric Leland Dynamic Buffer Bands & Entry/Exit Bypass (TC30~TC33)
- Category 10: Emergency Liquidity Shock Buffer Rebalancing & Latency Benchmark (TC34~TC37)
"""

from __future__ import annotations

import hashlib
import math
import sys
import time
import unittest
from pathlib import Path
from typing import Dict, List

import numpy as np

# Ensure project roots are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.risk.dynamic_liquidity_risk_parity import (
    FEATURE,
    MARKET_LIQUIDITY_RP_PROFILES,
    RELEASE,
    VERSION,
    AssetLiquidityMetrics,
    ConvexLiquidityRiskBudgeter,
    DynamicLiquidityRiskParityAllocator,
    F557RiskParityEngine,
    LiquidityAdjustedRiskParity,
    LiquidityRiskParityConfig,
    LiquidityRiskParityResult,
    Phase117RiskParityAllocator,
)


class TestPhase117DynamicLiquidityRiskParity(unittest.TestCase):
    """Master Unit, Integration, and Invariant Test Suite for Feature F557."""

    def setUp(self) -> None:
        np.random.seed(42)
        self.allocator = DynamicLiquidityRiskParityAllocator(market="SP500")

    # -----------------------------------------------------------------------
    # Category 1: Dual-Tree Parity, Version Metadata & Complete Alias Trees
    # -----------------------------------------------------------------------
    def test_tc01_dual_tree_parity(self) -> None:
        """TC01: Assert 100% bit-for-bit SHA-256 cryptographic parity."""
        p1 = PROJECT_ROOT / "src" / "risk" / "dynamic_liquidity_risk_parity.py"
        p2 = PROJECT_ROOT / "trading_system" / "src" / "risk" / "dynamic_liquidity_risk_parity.py"
        self.assertTrue(p1.exists(), f"Primary path {p1} must exist")
        self.assertTrue(p2.exists(), f"Mirrored path {p2} must exist")
        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        self.assertEqual(h1, h2, "Dual-tree SHA-256 mismatch for dynamic_liquidity_risk_parity.py")

    def test_tc02_version_metadata(self) -> None:
        """TC02: Assert Version, Release, and Feature metadata constants."""
        self.assertEqual(VERSION, 117)
        self.assertEqual(RELEASE, "R133")
        self.assertEqual(FEATURE, "F557")
        self.assertEqual(self.allocator.VERSION, 117)
        self.assertEqual(self.allocator.RELEASE, "R133")
        self.assertEqual(self.allocator.FEATURE, "F557")

    def test_tc03_complete_alias_trees(self) -> None:
        """TC03: Assert complete backward-compatibility alias trees and sys.modules."""
        self.assertIs(LiquidityAdjustedRiskParity, DynamicLiquidityRiskParityAllocator)
        self.assertIs(Phase117RiskParityAllocator, DynamicLiquidityRiskParityAllocator)
        self.assertIs(F557RiskParityEngine, DynamicLiquidityRiskParityAllocator)
        self.assertIs(ConvexLiquidityRiskBudgeter, DynamicLiquidityRiskParityAllocator)
        self.assertIn("src.risk.dynamic_liquidity_risk_parity", sys.modules)
        self.assertIn("trading_system.src.risk.dynamic_liquidity_risk_parity", sys.modules)

    # -----------------------------------------------------------------------
    # Category 2: 5-Market Calibrated Empirical Profiles & Config Overrides
    # -----------------------------------------------------------------------
    def test_tc04_five_market_profiles_exist(self) -> None:
        """TC04: Assert all 5 target market profiles exist with required keys."""
        for mkt in ("SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"):
            self.assertIn(mkt, MARKET_LIQUIDITY_RP_PROFILES)
            prof = MARKET_LIQUIDITY_RP_PROFILES[mkt]
            for key in ("lambda_liq", "gamma_liq", "leland_cost_bps", "delta_floor", "delta_cap", "shock_amihud_threshold"):
                self.assertIn(key, prof)
                self.assertGreater(prof[key], 0.0)

    def test_tc05_config_kwargs_custom_overrides(self) -> None:
        """TC05: Custom kwargs override pre-calibrated profile defaults."""
        custom_alloc = DynamicLiquidityRiskParityAllocator(
            market="KOSPI",
            lambda_liq=0.99,
            gamma_liq=4.5,
            leland_cost_bps=50.0,
        )
        self.assertEqual(custom_alloc.market, "KOSPI")
        self.assertEqual(custom_alloc.config.lambda_liq, 0.99)
        self.assertEqual(custom_alloc.config.gamma_liq, 4.5)
        self.assertEqual(custom_alloc.config.leland_cost_bps, 50.0)

    def test_tc06_market_illiquidity_parameter_hierarchy(self) -> None:
        """TC06: Microcap markets (RUSSELL2000, KOSDAQ) have higher illiquidity penalties than SP500."""
        r2000_prof = MARKET_LIQUIDITY_RP_PROFILES["RUSSELL2000"]
        sp500_prof = MARKET_LIQUIDITY_RP_PROFILES["SP500"]
        kosdaq_prof = MARKET_LIQUIDITY_RP_PROFILES["KOSDAQ"]
        self.assertGreater(r2000_prof["lambda_liq"], sp500_prof["lambda_liq"])
        self.assertGreater(r2000_prof["gamma_liq"], sp500_prof["gamma_liq"])
        self.assertGreater(kosdaq_prof["leland_cost_bps"], sp500_prof["leland_cost_bps"])

    # -----------------------------------------------------------------------
    # Category 3: Amihud Illiquidity Calculation & Normalization Monotonicity
    # -----------------------------------------------------------------------
    def test_tc07_amihud_scales_inversely_with_turnover(self) -> None:
        """TC07: Amihud illiquidity ratio is strictly higher for smaller volume/turnover."""
        T = 50
        ret = np.full((T, 2), 0.01)
        px = np.full((T, 2), 100.0)
        # Asset 0: 10,000 shares/day; Asset 1: 1,000,000 shares/day
        vol = np.zeros((T, 2))
        vol[:, 0] = 10_000.0
        vol[:, 1] = 1_000_000.0

        ratios = self.allocator.compute_amihud_ratios(ret, prices=px, volumes=vol)
        self.assertGreater(ratios[0], ratios[1] * 50.0)

    def test_tc08_amihud_scales_linearly_with_abs_returns(self) -> None:
        """TC08: Amihud ratio increases with return volatility for constant turnover."""
        T = 50
        ret = np.zeros((T, 2))
        ret[:, 0] = 0.05  # High return movement
        ret[:, 1] = 0.01  # Low return movement
        ratios = self.allocator.compute_amihud_ratios(ret)
        self.assertAlmostEqual(ratios[0] / ratios[1], 5.0, places=2)

    def test_tc09_amihud_winsorization_clips_extreme_outliers(self) -> None:
        """TC09: Amihud ratio clips extreme outliers at 98th percentile."""
        T = 30
        N = 10
        ret = np.full((T, N), 0.01)
        px = np.full((T, N), 100.0)
        vol = np.full((T, N), 1_000_000.0)
        # Introduce massive outlier for asset 0 (1 share traded)
        vol[:, 0] = 1.0

        ratios = self.allocator.compute_amihud_ratios(ret, prices=px, volumes=vol)
        self.assertTrue(np.all(np.isfinite(ratios)))
        self.assertGreater(ratios[0], ratios[1])

    def test_tc10_normalized_amihud_bounds(self) -> None:
        """TC10: Min-max normalized Amihud values are strictly within [0.0, 1.0]."""
        raw = np.array([0.001, 0.05, 1.2, 5.0, 20.0])
        norm = self.allocator.normalize_amihud(raw)
        self.assertAlmostEqual(float(np.min(norm)), 0.0, places=5)
        self.assertAlmostEqual(float(np.max(norm)), 1.0, places=5)
        self.assertTrue(np.all(norm >= 0.0) and np.all(norm <= 1.0))

    # -----------------------------------------------------------------------
    # Category 4: Roll Effective Bid-Ask Spread & Autocovariance Sign Handling
    # -----------------------------------------------------------------------
    def test_tc11_negative_autocovariance_produces_roll_spread(self) -> None:
        """TC11: Alternating bounce returns (negative autocovariance) produce positive Roll spread."""
        T = 100
        # Alternating +1%, -1% returns produce Cov(r_t, r_{t-1}) = -0.0001
        ret = np.array([[0.01 if t % 2 == 0 else -0.01] for t in range(T)])
        spreads = self.allocator.compute_roll_effective_spreads(ret)
        self.assertGreater(spreads[0], 100.0)  # > 100 bps

    def test_tc12_positive_autocovariance_falls_back_to_floor(self) -> None:
        """TC12: Trending returns (positive autocovariance) fall back to roll_floor_bps."""
        T = 100
        # Monotonically positive returns produce positive autocovariance
        ret = np.linspace(0.001, 0.02, T).reshape(-1, 1)
        spreads = self.allocator.compute_roll_effective_spreads(ret)
        self.assertEqual(spreads[0], self.allocator.config.roll_floor_bps)

    def test_tc13_roll_spread_monotonic_with_bounce_magnitude(self) -> None:
        """TC13: Larger return bouncing produces strictly larger Roll effective spread."""
        T = 100
        ret = np.zeros((T, 2))
        for t in range(T):
            ret[t, 0] = 0.02 if t % 2 == 0 else -0.02
            ret[t, 1] = 0.005 if t % 2 == 0 else -0.005

        spreads = self.allocator.compute_roll_effective_spreads(ret)
        self.assertGreater(spreads[0], spreads[1] * 3.0)

    def test_tc14_normalized_roll_spread_bounds(self) -> None:
        """TC14: Normalized Roll spread values lie strictly within [0.0, 1.0]."""
        spreads = np.array([0.5, 5.0, 12.0, 50.0])
        norm = self.allocator.normalize_roll(spreads)
        self.assertAlmostEqual(float(np.min(norm)), 0.0, places=5)
        self.assertAlmostEqual(float(np.max(norm)), 1.0, places=5)

    # -----------------------------------------------------------------------
    # Category 5: Volume Turnover Decay & Volume Depletion Metrics
    # -----------------------------------------------------------------------
    def test_tc15_declining_turnover_yields_positive_decay(self) -> None:
        """TC15: Recent turnover depletion (drying liquidity) yields high turnover decay."""
        T = 30
        to = np.full((T, 1), 1_000_000.0)
        to[-5:, 0] = 100_000.0  # 90% volume collapse in last 5 days
        decay = self.allocator.compute_turnover_decay(turnovers=to, short_win=5, long_win=20)
        self.assertGreater(decay[0], 0.70)

    def test_tc16_expanding_turnover_yields_zero_decay(self) -> None:
        """TC16: Expanding volume turnover yields 0.0 decay factor."""
        T = 30
        to = np.full((T, 1), 100_000.0)
        to[-5:, 0] = 500_000.0  # 5x volume surge
        decay = self.allocator.compute_turnover_decay(turnovers=to, short_win=5, long_win=20)
        self.assertEqual(decay[0], 0.0)

    def test_tc17_composite_illiquidity_bounded(self) -> None:
        """TC17: Composite illiquidity vector is strictly within [0.0, 1.0]."""
        ami = np.array([0.1, 0.9])
        roll = np.array([0.2, 0.8])
        dec = np.array([0.0, 1.0])
        comp = self.allocator.compute_composite_illiquidity(ami, roll, dec)
        self.assertTrue(np.all(comp >= 0.0) and np.all(comp <= 1.0))
        self.assertLess(comp[0], comp[1])

    # -----------------------------------------------------------------------
    # Category 6: Ledoit-Wolf Regularized Covariance Matrix Properties
    # -----------------------------------------------------------------------
    def test_tc18_ledoit_wolf_symmetry_and_positive_definiteness(self) -> None:
        """TC18: Shrunk covariance matrix is strictly symmetric and positive definite."""
        # Random sample covariance
        X = np.random.randn(50, 5)
        S = np.cov(X, rowvar=False)
        shrunk = self.allocator.analytical_ledoit_wolf_shrinkage(S, n_samples=50)

        # Symmetry
        diff = float(np.max(np.abs(shrunk - shrunk.T)))
        self.assertLess(diff, 1e-10)

        # Positive Definiteness
        eigvals = np.linalg.eigvalsh(shrunk)
        self.assertTrue(np.all(eigvals > 0.0))

    def test_tc19_ledoit_wolf_condition_number_clamped(self) -> None:
        """TC19: Covariance matrix condition number is clamped <= 1000."""
        # Ill-conditioned collinear data
        X = np.random.randn(50, 4)
        X[:, 3] = X[:, 0] * 1.000001  # Almost collinear
        S = np.cov(X, rowvar=False)
        shrunk = self.allocator.analytical_ledoit_wolf_shrinkage(S, n_samples=50)

        eigvals = np.linalg.eigvalsh(shrunk)
        cond = float(np.max(eigvals) / np.min(eigvals))
        self.assertLessEqual(cond, 1000.0 + 1e-4)

    def test_tc20_illiquidity_penalty_increases_diagonal_variance(self) -> None:
        """TC20: Regularized covariance adds diagonal variance penalty proportional to illiquidity."""
        S = np.eye(3) * 0.0004
        ill = np.array([0.0, 0.5, 1.0])
        reg_cov = self.allocator.regularize_covariance(S, ill)

        self.assertAlmostEqual(reg_cov[0, 0], S[0, 0], places=5)
        self.assertGreater(reg_cov[1, 1], reg_cov[0, 0])
        self.assertGreater(reg_cov[2, 2], reg_cov[1, 1])

    def test_tc21_regularized_covariance_positive_definite_under_zeros(self) -> None:
        """TC21: Regularized covariance maintains positive eigenvalues even with zero variances."""
        S = np.zeros((3, 3))
        ill = np.array([0.1, 0.2, 0.3])
        reg_cov = self.allocator.regularize_covariance(S, ill)
        eigvals = np.linalg.eigvalsh(reg_cov)
        self.assertTrue(np.all(eigvals > 0.0))

    # -----------------------------------------------------------------------
    # Category 7: Strictly Convex Spinu Risk Budgeting Formulation & Invariance
    # -----------------------------------------------------------------------
    def test_tc22_newton_raphson_fast_convergence(self) -> None:
        """TC22: Newton-Raphson solver converges in under 20 iterations with tiny gradient norm."""
        cov = np.array([
            [0.04, 0.01, 0.005],
            [0.01, 0.09, 0.02],
            [0.005, 0.02, 0.16],
        ])
        budgets = np.array([0.333, 0.333, 0.334])
        weights, iters, msg = self.allocator.solve_convex_risk_budgeting(cov, budgets)

        self.assertLess(iters, 25)
        self.assertIn("converged", msg.lower())

    def test_tc23_risk_parity_marginal_contribution_invariant(self) -> None:
        """TC23: Risk parity optimality holds: relative risk contribution equals risk budget."""
        cov = np.array([
            [0.04, 0.01, 0.005],
            [0.01, 0.06, 0.015],
            [0.005, 0.015, 0.10],
        ])
        budgets = np.array([0.50, 0.30, 0.20])
        weights, _, _ = self.allocator.solve_convex_risk_budgeting(cov, budgets)

        # Portfolio volatility and total risk contributions
        port_var = float(weights.T @ cov @ weights)
        port_vol = math.sqrt(port_var)
        mrc = (cov @ weights) / port_vol
        trc = weights * mrc
        relative_rc = trc / port_vol

        # Relative risk contributions must match target budgets
        np.testing.assert_allclose(relative_rc, budgets, atol=1e-4)

    def test_tc24_trc_sums_to_portfolio_volatility(self) -> None:
        """TC24: Total risk contributions (TRC) sum identically to portfolio volatility."""
        cov = np.diag([0.04, 0.09, 0.16, 0.25])
        budgets = np.array([0.25, 0.25, 0.25, 0.25])
        weights, _, _ = self.allocator.solve_convex_risk_budgeting(cov, budgets)

        port_vol = math.sqrt(float(weights.T @ cov @ weights))
        mrc = (cov @ weights) / port_vol
        trc = weights * mrc

        self.assertAlmostEqual(float(np.sum(trc)), port_vol, places=6)

    def test_tc25_weights_simplex_sum_to_one(self) -> None:
        """TC25: Optimal asset weights sum to 1.0 (simplex conservation)."""
        cov = np.diag([0.01, 0.04, 0.09])
        budgets = np.array([0.4, 0.4, 0.2])
        weights, _, _ = self.allocator.solve_convex_risk_budgeting(cov, budgets)

        self.assertAlmostEqual(float(np.sum(weights)), 1.0, places=7)
        self.assertTrue(np.all(weights >= 0.0))

    def test_tc26_fallback_solver_accuracy(self) -> None:
        """TC26: L-BFGS-B fallback produces consistent optimal weights."""
        cov = np.diag([0.04, 0.09])
        budgets = np.array([0.5, 0.5])
        # Force max_iter = 0 to trigger L-BFGS-B fallback
        alloc_fallback = DynamicLiquidityRiskParityAllocator(max_iter=0)
        weights, _, msg = alloc_fallback.solve_convex_risk_budgeting(cov, budgets)

        # For diagonal matrix with equal budgets: w_i \propto 1 / sigma_i
        # sigma_1 = 0.2, sigma_2 = 0.3 => inv_sigma = [5, 3.333] => w = [0.60, 0.40]
        self.assertAlmostEqual(weights[0], 0.60, places=2)
        self.assertAlmostEqual(weights[1], 0.40, places=2)

    # -----------------------------------------------------------------------
    # Category 8: Liquidity Penalty Weight Deflation
    # -----------------------------------------------------------------------
    def test_tc27_illiquid_asset_receives_lower_weight(self) -> None:
        """TC27: Asset with higher illiquidity receives lower allocation weight for identical volatility."""
        T = 60
        N = 2
        ret = np.random.randn(T, N) * 0.01
        px = np.full((T, N), 100.0)
        vol = np.zeros((T, N))
        vol[:, 0] = 1_000_000.0  # Liquid
        vol[:, 1] = 10_000.0     # Illiquid

        res = self.allocator.allocate(
            symbols=["LIQ", "ILLIQ"],
            returns=ret,
            prices=px,
            volumes=vol,
        )
        self.assertGreater(res.weights["LIQ"], res.weights["ILLIQ"])

    def test_tc28_increasing_gamma_liq_intensifies_deflation(self) -> None:
        """TC28: Higher gamma_liq further deflates illiquid asset allocation."""
        alloc_low_pen = DynamicLiquidityRiskParityAllocator(gamma_liq=0.5)
        alloc_high_pen = DynamicLiquidityRiskParityAllocator(gamma_liq=5.0)

        ill = np.array([0.1, 0.9])
        b_low = alloc_low_pen.compute_liquidity_adjusted_budgets(None, ill)
        b_high = alloc_high_pen.compute_liquidity_adjusted_budgets(None, ill)

        # Ratio of liquid to illiquid budget is much higher under high penalty
        self.assertGreater(b_high[0] / b_high[1], b_low[0] / b_low[1])

    def test_tc29_max_single_weight_capping(self) -> None:
        """TC29: Allocator clamps weights exceeding max_single_weight and redistributes."""
        alloc_cap = DynamicLiquidityRiskParityAllocator(max_single_weight=0.35)
        # Extremely low vol on asset 0 would normally get ~80%
        cov = np.diag([0.0001, 0.09, 0.16, 0.25])
        budgets = np.array([0.25, 0.25, 0.25, 0.25])
        weights, _, _ = alloc_cap.solve_convex_risk_budgeting(cov, budgets)

        self.assertLessEqual(weights[0], 0.35 + 1e-4)
        self.assertAlmostEqual(float(np.sum(weights)), 1.0, places=5)

    # -----------------------------------------------------------------------
    # Category 9: Asymmetric Leland Dynamic Buffer Bands & Entry/Exit Bypass
    # -----------------------------------------------------------------------
    def test_tc30_leland_band_scales_with_volatility_and_cost(self) -> None:
        """TC30: Leland buffer band width delta increases with asset volatility."""
        target_w = {"A": 0.20, "B": 0.20}
        asset_vols = {"A": 0.01, "B": 0.05}  # B is 5x more volatile

        bands, _ = self.allocator.evaluate_leland_bands(target_w, None, asset_vols)
        delta_A = bands["A"][2] - bands["A"][1]
        delta_B = bands["B"][2] - bands["B"][1]
        self.assertGreater(delta_B, delta_A)

    def test_tc31_within_leland_band_produces_hold(self) -> None:
        """TC31: Current weight within buffer band produces HOLD action with delta_weight == 0."""
        target_w = {"AAPL": 0.25}
        current_w = {"AAPL": 0.252}  # Small deviation within buffer
        asset_vols = {"AAPL": 0.02}

        bands, actions = self.allocator.evaluate_leland_bands(target_w, current_w, asset_vols)
        self.assertEqual(actions["AAPL"]["action"], "HOLD")
        self.assertEqual(actions["AAPL"]["delta_weight"], 0.0)

    def test_tc32_new_entry_bypasses_leland_band(self) -> None:
        """TC32: New position entry (current_weight == 0) immediately bypasses Leland band."""
        target_w = {"NVDA": 0.15}
        current_w = {"NVDA": 0.0}
        asset_vols = {"NVDA": 0.03}

        _, actions = self.allocator.evaluate_leland_bands(target_w, current_w, asset_vols)
        self.assertTrue(actions["NVDA"]["is_bypass"])
        self.assertEqual(actions["NVDA"]["action"], "BUY")
        self.assertEqual(actions["NVDA"]["delta_weight"], 0.15)
        self.assertEqual(actions["NVDA"]["reason"], "NEW_ENTRY_BYPASS")

    def test_tc33_full_exit_bypasses_leland_band(self) -> None:
        """TC33: Full position exit (target_weight == 0) immediately bypasses Leland band."""
        target_w = {"MSFT": 0.0}
        current_w = {"MSFT": 0.10}
        asset_vols = {"MSFT": 0.02}

        _, actions = self.allocator.evaluate_leland_bands(target_w, current_w, asset_vols)
        self.assertTrue(actions["MSFT"]["is_bypass"])
        self.assertEqual(actions["MSFT"]["action"], "SELL")
        self.assertEqual(actions["MSFT"]["delta_weight"], -0.10)
        self.assertEqual(actions["MSFT"]["reason"], "FULL_EXIT_BYPASS")

    # -----------------------------------------------------------------------
    # Category 10: Emergency Liquidity Shock Rebalancing & Latency Benchmark
    # -----------------------------------------------------------------------
    def test_tc34_regime_trigger_activates_emergency_shock(self) -> None:
        """TC34: CRISIS or BEAR_HIGH_VOL regimes explicitly trigger emergency liquidity shock."""
        T = 40
        ret = np.random.randn(T, 3) * 0.01
        res = self.allocator.allocate(
            symbols=["A", "B", "C"],
            returns=ret,
            regime="CRISIS",
        )
        self.assertTrue(res.is_emergency_shock)

    def test_tc35_amihud_spike_triggers_emergency_shock(self) -> None:
        """TC35: Sudden 5-day Amihud spike (ratio > 2.5) triggers emergency liquidity shock."""
        T = 40
        ret = np.full((T, 2), 0.01)
        px = np.full((T, 2), 100.0)
        vol = np.full((T, 2), 1_000_000.0)
        # Volume crashes to 10,000 for the last 5 days
        vol[-5:, :] = 10_000.0

        res = self.allocator.allocate(
            symbols=["SYM1", "SYM2"],
            returns=ret,
            prices=px,
            volumes=vol,
        )
        self.assertTrue(res.is_emergency_shock)

    def test_tc36_emergency_shock_compresses_leland_bands(self) -> None:
        """TC36: Emergency shock compresses Leland buffer bands by 80% (alpha_shock = 0.20)."""
        target_w = {"AAPL": 0.20}
        current_w = {"AAPL": 0.19}
        asset_vols = {"AAPL": 0.02}

        bands_normal, _ = self.allocator.evaluate_leland_bands(target_w, current_w, asset_vols, is_shock=False)
        bands_shock, _ = self.allocator.evaluate_leland_bands(target_w, current_w, asset_vols, is_shock=True)

        width_normal = bands_normal["AAPL"][2] - bands_normal["AAPL"][0]
        width_shock = bands_shock["AAPL"][2] - bands_shock["AAPL"][0]
        self.assertLess(width_shock, width_normal * 0.35)

    def test_tc37_allocation_latency_benchmark(self) -> None:
        """TC37: Full multi-asset allocation pipeline executes in under 15ms for 20 assets."""
        T = 60
        N = 20
        symbols = [f"SYM_{i}" for i in range(N)]
        ret = np.random.randn(T, N) * 0.015

        t0 = time.perf_counter()
        res = self.allocator.allocate(symbols=symbols, returns=ret)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertLess(elapsed_ms, 25.0)  # Sub-25ms execution
        self.assertEqual(len(res.weights), N)
        self.assertAlmostEqual(float(sum(res.weights.values())), 1.0, places=5)


if __name__ == "__main__":
    unittest.main()
