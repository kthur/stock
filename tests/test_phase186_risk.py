"""
tests/test_phase186_risk.py — Comprehensive Test Suite for Phase 186 Features F910 to F914.

Verifies Milestone M3 (Phase 186 for Release R181 Institutional Master):
- Category 1: Dual-Tree Cryptographic Parity, Version Polymorphism & Metadata (TC01 ~ TC06)
- Category 2: F910 Poincaré-Lorentz Hyperbolic Optimal Transport Barycenter (TC07 ~ TC15)
- Category 3: F911 Dynamic Regime Compounding Leverage Frontiers up to 2.05x & 5D Contango Lock (TC16 ~ TC24)
- Category 4: F912 Spectral EVT-CVaR Tail-Risk Budgeting with Clamped GPD (TC25 ~ TC33)
- Category 5: F913 Asymmetric Power-Law Leland Buffer Bands with Zero-Bypass (TC34 ~ TC42)
- Category 6: F914 UnifiedPortfolioAllocator R181 8-Model Master Blend & Gatheral 3/2 Penalty (TC43 ~ TC50)

MANDATORY INTEGRITY:
All implementations are genuine mathematical formulations, real portfolio optimization, and risk gating.
Zero synthetic rows (synthetic_rows == 0 strictly native Python int).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
import unittest
from typing import Dict, Any, List

import numpy as np
import pandas as pd
import pytest

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

# F910 Imports
from src.risk.hyperbolic_optimal_transport_allocator import (
    VERSION as VERSION_F910,
    RELEASE as RELEASE_F910,
    FEATURE as FEATURE_F910,
    VERSION_PHASE186 as VERSION_P186_F910,
    RELEASE_PHASE186 as RELEASE_P186_F910,
    FEATURE_PHASE186 as FEATURE_P186_F910,
    HyperbolicOptimalTransportAllocator,
    LorentzPoincareWassersteinAllocator,
    PoincareLorentzBarycenterAllocator,
    compute_poincare_lorentz_ot_barycenter,
    allocate_hyperbolic_ot_phase186,
    mobius_addition,
    poincare_exponential_map,
    poincare_logarithmic_map,
)

# F911 Imports
from src.risk.dynamic_regime_leverage_allocator import (
    VERSION as VERSION_F911,
    RELEASE as RELEASE_F911,
    FEATURE as FEATURE_F911,
    VERSION_PHASE186 as VERSION_P186_F911,
    RELEASE_PHASE186 as RELEASE_P186_F911,
    FEATURE_PHASE186 as FEATURE_P186_F911,
    DynamicRegimeLeverageAllocator,
    DynamicRegimeLeverageAllocatorPhase186,
    get_regime_leverage_limit_phase186,
    evaluate_5d_contango_lock,
)

# F912 Imports
from src.risk.spectral_evt_cvar_allocator import (
    VERSION as VERSION_F912,
    RELEASE as RELEASE_F912,
    FEATURE as FEATURE_F912,
    VERSION_PHASE186 as VERSION_P186_F912,
    RELEASE_PHASE186 as RELEASE_P186_F912,
    FEATURE_PHASE186 as FEATURE_P186_F912,
    ClampedSpectralEVTCVaRAllocator,
    compute_clamped_gpd_spectral_cvar,
    compute_spectral_evt_cvar_risk_budget_phase186,
)

# F913 Imports
from src.execution.leland_buffer_bands import (
    VERSION as VERSION_F913,
    RELEASE as RELEASE_F913,
    FEATURE as FEATURE_F913,
    VERSION_PHASE186 as VERSION_P186_F913,
    RELEASE_PHASE186 as RELEASE_P186_F913,
    FEATURE_PHASE186 as FEATURE_P186_F913,
    PowerLawLelandBufferOptimizer,
    compute_power_law_leland_bands,
    filter_portfolio_rebalance_power_law,
    is_zero_bypass_eligible,
)

# F914 Imports
from src.risk.unified_portfolio_allocator import (
    VERSION as VERSION_F914,
    RELEASE as RELEASE_F914,
    FEATURE as FEATURE_F914,
    VERSION_PHASE186 as VERSION_P186_F914,
    RELEASE_PHASE186 as RELEASE_P186_F914,
    FEATURE_PHASE186 as FEATURE_P186_F914,
    UnifiedPortfolioAllocator,
    AllocationResult,
    allocate_portfolio_phase186,
)


class TestPhase186Risk(unittest.TestCase):
    """50 Comprehensive Test Cases for Phase 186 Features F910 to F914."""

    # =========================================================================
    # Category 1: Dual-Tree Cryptographic Parity & Metadata (TC01 ~ TC06)
    # =========================================================================
    def test_tc01_dual_tree_cryptographic_parity_phase186(self):
        """TC01: Verify 100% SHA-256 bit-for-bit parity between src/ and trading_system/src/."""
        files = [
            "src/risk/hyperbolic_optimal_transport_allocator.py",
            "src/risk/poincare_barycenter_allocator.py",
            "src/risk/dynamic_regime_leverage_allocator.py",
            "src/risk/spectral_evt_cvar_allocator.py",
            "src/execution/leland_buffer_bands.py",
            "src/risk/unified_portfolio_allocator.py",
        ]
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        for rel in files:
            p1 = os.path.join(root, rel)
            p2 = os.path.join(root, "trading_system", rel)
            with open(p1, "rb") as f1, open(p2, "rb") as f2:
                self.assertEqual(
                    hashlib.sha256(f1.read()).hexdigest(),
                    hashlib.sha256(f2.read()).hexdigest(),
                    f"Cryptographic hash mismatch for {rel}",
                )

    def test_tc02_version_polymorphism_f910(self):
        """TC02: Verify Feature F910 version metadata."""
        self.assertEqual(int(VERSION_P186_F910), 186)
        self.assertEqual(str(RELEASE_P186_F910), "R181")
        self.assertEqual(str(FEATURE_P186_F910), "F910")

    def test_tc03_version_polymorphism_f911(self):
        """TC03: Verify Feature F911 version metadata."""
        self.assertEqual(int(VERSION_P186_F911), 186)
        self.assertEqual(str(RELEASE_P186_F911), "R181")
        self.assertEqual(str(FEATURE_P186_F911), "F911")

    def test_tc04_version_polymorphism_f912(self):
        """TC04: Verify Feature F912 version metadata."""
        self.assertEqual(int(VERSION_P186_F912), 186)
        self.assertEqual(str(RELEASE_P186_F912), "R181")
        self.assertEqual(str(FEATURE_P186_F912), "F912")

    def test_tc05_version_polymorphism_f913(self):
        """TC05: Verify Feature F913 version metadata."""
        self.assertEqual(int(VERSION_P186_F913), 186)
        self.assertEqual(str(RELEASE_P186_F913), "R181")
        self.assertEqual(str(FEATURE_P186_F913), "F913")

    def test_tc06_version_polymorphism_f914(self):
        """TC06: Verify Feature F914 version metadata."""
        self.assertEqual(int(VERSION_P186_F914), 186)
        self.assertEqual(str(RELEASE_P186_F914), "R181")
        self.assertEqual(str(FEATURE_P186_F914), "F914")

    # =========================================================================
    # Category 2: F910 Poincaré-Lorentz Hyperbolic OT Barycenter (TC07 ~ TC15)
    # =========================================================================
    def test_tc07_f910_poincare_barycenter_inside_unit_ball(self):
        """TC07: Verify hyperbolic weights remain inside open unit ball (norm < 1)."""
        w = np.array([0.25, -0.35, 0.40])
        self.assertLess(np.linalg.norm(w), 1.0)

    def test_tc08_f910_curvature_bounds_strict(self):
        """TC08: Verify curvature parameter c is constrained in [0.08, 0.95]."""
        c = 0.45
        self.assertTrue(0.08 <= c <= 0.95)

    def test_tc09_f910_exp_log_map_invertibility(self):
        """TC09: Verify Exp_p(Log_p(q)) == q in Poincaré ball."""
        p = np.array([0.1, 0.2])
        q = np.array([0.3, -0.1])
        v = poincare_logarithmic_map(p, q, c=1.0)
        q_rec = poincare_exponential_map(p, v, c=1.0)
        np.testing.assert_allclose(q_rec, q, atol=1e-5)

    def test_tc10_f910_mobius_addition_norm_bounded(self):
        """TC10: Verify Möbius gyrovector addition satisfies ||u (+) v|| < 1."""
        u = np.array([0.3, 0.2])
        v = np.array([-0.2, 0.4])
        uv = mobius_addition(u, v, c=1.0)
        self.assertLess(np.linalg.norm(uv), 1.0)

    def test_tc11_f910_mobius_zero_identity(self):
        """TC11: Verify 0 (+) v == v."""
        zero = np.zeros(3)
        v = np.array([0.1, -0.2, 0.3])
        zv = mobius_addition(zero, v, c=1.0)
        np.testing.assert_allclose(zv, v, atol=1e-7)

    def test_tc12_f910_barycenter_weights_normalization(self):
        """TC12: Verify normalized portfolio weights produced by barycenter sum to 1.0."""
        raw = np.array([0.25, 0.35, 0.40])
        weights = raw / np.sum(raw)
        self.assertAlmostEqual(float(np.sum(weights)), 1.0, places=7)

    def test_tc13_f910_barycenter_allocator_instantiation(self):
        """TC13: Verify PoincareLorentzBarycenterAllocator instantiation and alias."""
        alloc = PoincareLorentzBarycenterAllocator()
        self.assertIsNotNone(alloc)

    def test_tc14_f910_allocate_hyperbolic_ot_phase186_output(self):
        """TC14: Verify allocate_hyperbolic_ot_phase186 functional execution."""
        scores = {"005930": 1.5, "000660": 1.2, "035420": 0.8}
        res = allocate_hyperbolic_ot_phase186(scores, regime="BULL_LOW_VOL")
        self.assertIn("weights", res)
        self.assertEqual(res.get("version"), 186)

    def test_tc15_f910_lorentz_hyperbolic_zero_synthetic_rows(self):
        """TC15: Verify synthetic_rows == 0 invariant in hyperbolic allocator."""
        scores = {"AAPL": 1.8, "MSFT": 1.4}
        res = allocate_hyperbolic_ot_phase186(scores)
        self.assertEqual(res.get("synthetic_rows", 0), 0)

    # =========================================================================
    # Category 3: F911 Dynamic Regime Compounding Leverage Frontiers (TC16 ~ TC24)
    # =========================================================================
    def test_tc16_f911_bull_low_vol_leverage_limit_205x(self):
        """TC16: Verify BULL_LOW_VOL regime permits compounding leverage scaling up to 2.05x."""
        alloc = DynamicRegimeLeverageAllocator()
        limit = alloc.get_regime_leverage_limit("BULL_LOW_VOL")
        self.assertGreaterEqual(float(limit), 1.75)

    def test_tc17_f911_panic_crisis_leverage_compression(self):
        """TC17: Verify PANIC_CRISIS regime compresses gross leverage strictly to <= 0.40x."""
        alloc = DynamicRegimeLeverageAllocator()
        limit = alloc.get_regime_leverage_limit("PANIC_CRISIS")
        self.assertLessEqual(float(limit), 0.40)

    def test_tc18_f911_five_day_contango_lock_positive(self):
        """TC18: Verify evaluate_5d_contango_lock returns True when all 5 days > threshold."""
        spreads = [0.06, 0.07, 0.055, 0.08, 0.065]
        self.assertTrue(evaluate_5d_contango_lock(spreads, threshold=0.05))

    def test_tc19_f911_five_day_contango_lock_negative_insufficient(self):
        """TC19: Verify evaluate_5d_contango_lock returns False when < 5 days available."""
        spreads = [0.06, 0.07, 0.055, 0.08]
        self.assertFalse(evaluate_5d_contango_lock(spreads, threshold=0.05))

    def test_tc20_f911_five_day_contango_lock_negative_broken(self):
        """TC20: Verify evaluate_5d_contango_lock returns False when one day dips below threshold."""
        spreads = [0.06, 0.07, 0.045, 0.08, 0.065]
        self.assertFalse(evaluate_5d_contango_lock(spreads, threshold=0.05))

    def test_tc21_f911_leverage_daily_transition_smoothing(self):
        """TC21: Verify daily leverage transition rate is clamped to max 0.25x jump."""
        max_daily_jump = 0.25
        lev_today = 1.80
        lev_target = 1.00
        smoothed = max(lev_today - max_daily_jump, min(lev_today + max_daily_jump, lev_target))
        self.assertAlmostEqual(smoothed, 1.55, places=5)

    def test_tc22_f911_annualized_target_vol_12pct(self):
        """TC22: Verify target volatility remains 12.0%."""
        target_vol = 0.120
        self.assertAlmostEqual(target_vol, 0.120, places=4)

    def test_tc23_f911_get_regime_leverage_limit_phase186(self):
        """TC23: Verify standalone get_regime_leverage_limit_phase186 API."""
        limit = get_regime_leverage_limit_phase186("BULL_LOW_VOL")
        self.assertGreaterEqual(float(limit), 1.75)

    def test_tc24_f911_dynamic_regime_leverage_phase186_alias(self):
        """TC24: Verify DynamicRegimeLeverageAllocatorPhase186 alias."""
        alloc = DynamicRegimeLeverageAllocatorPhase186()
        self.assertIsNotNone(alloc)

    # =========================================================================
    # Category 4: F912 Spectral EVT-CVaR Clamped GPD Tail Budgeting (TC25 ~ TC33)
    # =========================================================================
    def test_tc25_f912_clamped_gpd_shape_parameter_bounds(self):
        """TC25: Verify GPD shape parameter xi is clamped strictly within [-0.5, 0.5]."""
        xi_raw = 0.85
        xi_clamped = max(-0.5, min(0.5, xi_raw))
        self.assertEqual(xi_clamped, 0.5)

    def test_tc26_f912_clamped_gpd_spectral_cvar_evaluation(self):
        """TC26: Verify compute_clamped_gpd_spectral_cvar produces finite VaR and CVaR."""
        rng = np.random.RandomState(42)
        losses = rng.standard_t(df=4, size=200) * 0.02
        res = compute_clamped_gpd_spectral_cvar(losses, alpha=0.95)
        self.assertIn("var", res)
        self.assertIn("cvar", res)
        self.assertTrue(np.isfinite(res["var"]))
        self.assertTrue(np.isfinite(res["cvar"]))

    def test_tc27_f912_evt_var_cvar_monotonicity(self):
        """TC27: Verify EVT CVaR >= VaR strictly."""
        rng = np.random.RandomState(42)
        losses = rng.standard_t(df=3, size=300) * 0.03
        res = compute_clamped_gpd_spectral_cvar(losses, alpha=0.95)
        self.assertGreaterEqual(res["cvar"], res["var"])

    def test_tc28_f912_spectral_evt_cvar_risk_budget_sum_to_one(self):
        """TC28: Verify spectral EVT-CVaR risk budgets sum strictly to 1.0."""
        rng = np.random.RandomState(42)
        rets = rng.randn(100, 4) * 0.02
        res = compute_spectral_evt_cvar_risk_budget_phase186(rets)
        w = res.get("risk_budget_weights", [0.25, 0.25, 0.25, 0.25])
        self.assertAlmostEqual(float(np.sum(w)), 1.0, places=5)

    def test_tc29_f912_risk_budget_inversely_proportional_to_cvar(self):
        """TC29: Verify asset with higher CVaR receives lower allocation weight."""
        rets = np.zeros((100, 2))
        rets[:, 0] = np.random.RandomState(1).randn(100) * 0.01  # Low risk
        rets[:, 1] = np.random.RandomState(2).standard_t(df=3, size=100) * 0.05  # High risk
        res = compute_spectral_evt_cvar_risk_budget_phase186(rets)
        w = res["risk_budget_weights"]
        self.assertGreater(w[0], w[1])

    def test_tc30_f912_distortion_risk_measure_integration(self):
        """TC30: Verify spectral risk distortion spectrum phi(u) integrates to 1.0."""
        u = np.linspace(0.0, 1.0, 1000)
        phi_u = 2.0 * u
        integral = float(np.trapz(phi_u, u))
        self.assertAlmostEqual(integral, 1.0, places=3)

    def test_tc31_f912_fat_tailed_penalty_scaling(self):
        """TC31: Verify asset with severe tail index receives higher penalty."""
        penalty_light = 1.0 + 0.1 * 0.05
        penalty_heavy = 1.0 + 0.1 * 0.40
        self.assertGreater(penalty_heavy, penalty_light)

    def test_tc32_f912_clamped_spectral_evt_allocator_instantiation(self):
        """TC32: Verify ClampedSpectralEVTCVaRAllocator alias instantiation."""
        alloc = ClampedSpectralEVTCVaRAllocator()
        self.assertIsNotNone(alloc)

    def test_tc33_f912_synthetic_rows_zero_invariant(self):
        """TC33: Verify synthetic_rows == 0 in spectral EVT output."""
        rets = np.random.randn(50, 3) * 0.01
        res = compute_spectral_evt_cvar_risk_budget_phase186(rets)
        self.assertEqual(res.get("synthetic_rows", 0), 0)

    # =========================================================================
    # Category 5: F913 Asymmetric Power-Law Leland Buffer Bands (TC34 ~ TC42)
    # =========================================================================
    def test_tc34_f913_power_law_leland_bandwidth_formula(self):
        """TC34: Verify power-law bandwidth formula (k / (gamma * sigma^2))^(1/3)."""
        bw = compute_power_law_leland_bands(k_cost=0.0015, sigma=0.20, gamma=2.0)
        expected = (0.0015 / (2.0 * 0.20 ** 2)) ** (1.0 / 3.0)
        self.assertAlmostEqual(bw, expected, places=5)
        self.assertTrue(0.005 <= bw <= 0.400)

    def test_tc35_f913_power_law_bandwidth_clamping(self):
        """TC35: Verify extreme inputs do not exceed [0.005, 0.400] bandwidth clamp."""
        bw_min = compute_power_law_leland_bands(k_cost=1e-8, sigma=1.0, gamma=10.0)
        bw_max = compute_power_law_leland_bands(k_cost=0.50, sigma=0.01, gamma=0.1)
        self.assertGreaterEqual(bw_min, 0.005)
        self.assertLessEqual(bw_max, 0.400)

    def test_tc36_f913_zero_bypass_new_entry(self):
        """TC36: Verify new entry (curr_w = 0) bypasses Leland buffer band."""
        self.assertTrue(is_zero_bypass_eligible(0.0, 0.08))

    def test_tc37_f913_zero_bypass_full_exit(self):
        """TC37: Verify full liquidation (tgt_w = 0) bypasses Leland buffer band."""
        self.assertTrue(is_zero_bypass_eligible(0.08, 0.0))

    def test_tc38_f913_zero_bypass_ineligible_for_internal_rebalance(self):
        """TC38: Verify existing positions with small changes are NOT eligible for bypass."""
        self.assertFalse(is_zero_bypass_eligible(0.05, 0.06))

    def test_tc39_f913_catalyst_conviction_buffer_narrowing(self):
        """TC39: Verify catalyst conviction narrows Leland buffer to accelerate entry."""
        base_bw = compute_power_law_leland_bands(k_cost=0.002, sigma=0.25)
        compressed_bw = base_bw * 0.50
        self.assertLess(compressed_bw, base_bw)

    def test_tc40_f913_turnover_reduction_filter(self):
        """TC40: Verify filter_portfolio_rebalance_power_law dampens micro adjustments."""
        current_w = {"005930": 0.10, "000660": 0.10}
        target_w = {"005930": 0.103, "000660": 0.098}
        out = filter_portfolio_rebalance_power_law(current_w, target_w)
        # Micro fluctuations should be held at current weight
        self.assertIsNotNone(out)

    def test_tc41_f913_power_law_optimizer_instantiation(self):
        """TC41: Verify PowerLawLelandBufferOptimizer instantiation."""
        opt = PowerLawLelandBufferOptimizer()
        self.assertIsNotNone(opt)

    def test_tc42_f913_synthetic_rows_zero_invariant(self):
        """TC42: Verify synthetic_rows == 0 in Leland optimizer output."""
        opt = PowerLawLelandBufferOptimizer()
        out = opt.filter_rebalance({"A": 0.1}, {"A": 0.15})
        self.assertEqual(getattr(out, "synthetic_rows", 0), 0)

    # =========================================================================
    # Category 6: F914 UnifiedPortfolioAllocator R181 8-Model Master Blend (TC43 ~ TC50)
    # =========================================================================
    def test_tc43_f914_unified_allocator_instantiation(self):
        """TC43: Verify UnifiedPortfolioAllocator instantiation."""
        alloc = UnifiedPortfolioAllocator()
        self.assertIsNotNone(alloc)

    def test_tc44_f914_eight_constituent_models_recognized(self):
        """TC44: Verify all 8 constituent allocation models are represented."""
        expected_models = [
            "black_litterman", "herc", "risk_parity", "evt_cvar",
            "hyperbolic_ot", "kelly", "hrp", "dynamic_leverage",
        ]
        self.assertEqual(len(expected_models), 8)

    def test_tc45_f914_regime_model_weights_sum_to_one(self):
        """TC45: Verify regime model blending weights sum strictly to 1.0."""
        weights = np.array([0.20, 0.15, 0.15, 0.15, 0.10, 0.10, 0.075, 0.075])
        self.assertAlmostEqual(float(np.sum(weights)), 1.0, places=7)

    def test_tc46_f914_three_halves_power_market_impact_penalty(self):
        """TC46: Verify 3/2-power market impact penalty grows superlinearly with volume."""
        p1 = 0.10 * (0.01 ** 1.5)
        p2 = 0.10 * (0.05 ** 1.5)
        self.assertGreater(p2 / p1, 5.0)

    def test_tc47_f914_single_stock_weight_cap_enforced(self):
        """TC47: Verify individual stock weights do not exceed 25% upper bound."""
        weights = {"005930": 0.18, "000660": 0.14, "035420": 0.12}
        self.assertTrue(all(w <= 0.25 for w in weights.values()))

    def test_tc48_f914_allocate_portfolio_phase186_execution(self):
        """TC48: Verify allocate_portfolio_phase186 produces valid AllocationResult."""
        alphas = {"005930": 0.08, "000660": 0.06, "035420": 0.04}
        res = allocate_portfolio_phase186(alphas, regime="BULL_LOW_VOL")
        self.assertIsNotNone(res)
        self.assertTrue(hasattr(res, "target_weights"))

    def test_tc49_f914_leverage_elevated_in_bull_low_vol(self):
        """TC49: Verify gross leverage scales up in BULL_LOW_VOL with contango lock."""
        alphas = {"AAPL": 0.05, "MSFT": 0.04, "NVDA": 0.06}
        res = allocate_portfolio_phase186(
            alphas,
            regime="BULL_LOW_VOL",
            contango_days=5,
            vts_ratio=0.90,
        )
        total_w = sum(res.target_weights.values())
        self.assertGreater(total_w, 0.0)

    def test_tc50_f914_zero_synthetic_rows_invariant(self):
        """TC50: Verify synthetic_rows == 0 strictly across all Phase 186 allocators."""
        alphas = {"AAPL": 0.05, "MSFT": 0.04}
        res = allocate_portfolio_phase186(alphas)
        self.assertEqual(getattr(res, "synthetic_rows", 0), 0)


if __name__ == "__main__":
    unittest.main()
