"""
tests/test_phase181_adversarial.py — Empirical Adversarial Stress Test Suite for Phase 181 (Features F885–F889).

Author: teamwork_challenger_m2_2 (Empirical Challenger)
Milestone: M2 (Release R180, Phase 181)

Adversarial Stress Scenarios:
1. Multi-Horizon Shock Consistency (F885 & F889):
   - Verifies cross-asset impulse aligns directionally and monotonically with MCSI risk index.
   - High-beta sector impulses plummet under escalating macro stress while MCSI escalates to circuit-breaker threshold.
2. Contagion Tipping Point & Perron-Frobenius (F888):
   - Verifies dominant eigenvalue lambda_max(A) > 1.0 tipping point detection.
   - Verifies in-degree vulnerability absorption and out-degree spreader ranking under synthetic panic shock injection.
3. Yield Curve Convexity Stress (F887):
   - Stress-tests 15 distinct yield curve topologies (normal, steep, inverted, barbell, humped, butterfly, etc.).
   - Asserts convexity adjustments remain strictly positive (> 0.0 for D > 0) and market beta clamp NEVER exceeds 1.000001.
4. Non-Linear CIP Arbitrage Bounds & Continuity (F886):
   - Tests synthetic zero interest rate differential and extreme exchange rate spreads.
   - Validates hedge ratio continuity across 1,000 fine-grid steps without discrete jumps or discontinuities.
5. Invariants & Dual-Tree Parity:
   - Zero synthetic rows (synthetic_rows == 0 strictly int).
   - 100% SHA-256 bit-for-bit parity across affected modules.
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
import unittest
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

# F885 Imports
from src.core.cross_asset_spillover import (
    CrossAssetSpilloverEngine,
    compute_macro_tensor_impulse_order3,
    compute_dynamic_macro_tensor_elasticity,
    GLOBAL_MACRO_FACTORS,
    DEFAULT_SECTOR_MACRO_BETAS,
)
from src.core.cross_asset_tensor_impulse import CrossAssetTensorImpulseEngine

# F886 Imports
from src.risk.dynamic_fx_hedging_engine import (
    DynamicFXHedgingEngine,
    calculate_optimal_hedge_ratio as fx_calc_optimal_hedge,
    generate_fx_hedge_order as fx_generate_order,
    FXMacroInput,
    FXHedgeResult,
)
from src.core.nonlinear_cip_hedger import (
    compute_nonlinear_cip_deviation,
    calculate_fx_rsi,
    compute_adaptive_fx_hedge_ratio,
    calculate_optimal_hedge_ratio as cip_calc_optimal_hedge,
    generate_fx_hedge_order as cip_generate_order,
)

# F887 Imports
from src.risk.delta_beta_hedge import (
    DeltaBetaHedgeEngine,
    fit_nss_yield_curve_6param,
    compute_duration_convexity_hedge,
)
from src.core.nss_yield_curve_hedge import (
    NSSYieldCurveDurationHedgeEngine,
    evaluate_nss_zero_coupon_yield,
    compute_nss_instantaneous_forward_rate,
    fit_nss_six_parameter_curve,
    detect_yield_curve_inversion,
)

# F888 Imports
from src.ai.graph_granger_causality import (
    GraphGrangerCausalityNetwork,
    fit_renyi_transfer_entropy_network,
    detect_systemic_contagion,
)
from src.core.transfer_entropy_contagion import (
    TransferEntropyContagionNetwork,
    compute_directed_transfer_entropy_matrix,
    evaluate_systemic_contagion_centrality,
)

# F889 Imports
from src.risk.risk_manager import (
    RiskManager,
    evaluate_mcsi_crisis_severity_index,
    check_crisis_circuit_breaker,
)
from src.core.macro_crisis_severity_index import (
    MacroCrisisSeverityIndexEngine,
    compute_mcsi_score,
    determine_crisis_gating_tier,
    get_leverage_limit_for_mcsi,
    TIER_NORMAL,
    TIER_ELEVATED,
    TIER_HIGH_STRESS,
    TIER_SYSTEMIC_CRISIS,
)


class TestPhase181AdversarialStress(unittest.TestCase):
    """Rigorous empirical adversarial stress suite for Milestone M2 (Phase 181)."""

    # =========================================================================
    # SCENARIO 1: Multi-Horizon Shock Consistency (F885 & F889)
    # =========================================================================

    def test_adv_scenario1_multi_horizon_shock_consistency_and_monotonicity(self):
        """Stress 1.1: Verify cross-asset impulse aligns directionally and monotonically with MCSI."""
        engine_f885 = CrossAssetSpilloverEngine()
        engine_f889 = MacroCrisisSeverityIndexEngine()

        steps = 25
        impulse_trajectory: List[float] = []
        mcsi_trajectory: List[float] = []
        leverage_limits: List[float] = []

        # Progressive shock sweep from benign (0.0) to catastrophic crisis (1.0)
        for s in range(steps):
            stress_level = s / (steps - 1)  # 0.0 to 1.0

            # F885 Macro Shock Vector
            # As stress rises: VIX spikes, SOX plummets, USDKRW depreciates, spreads widen
            macro_shocks = {
                "sox": float(0.03 - 0.15 * stress_level),
                "sp500": float(0.015 - 0.10 * stress_level),
                "vix": float(-0.05 + 0.85 * stress_level),
                "usdkrw": float(-0.005 + 0.06 * stress_level),
                "tnx": float(0.01 - 0.20 * stress_level),
                "hy_spread": float(-0.02 + 0.65 * stress_level),
                "ted_spread": float(-0.01 + 0.40 * stress_level),
                "wti": float(0.01 - 0.08 * stress_level),
                "gold": float(0.00 + 0.05 * stress_level),
                "dxy": float(0.00 + 0.04 * stress_level),
            }

            vol_mult = 1.0 + 3.0 * stress_level
            impulse = engine_f885.compute_macro_tensor_impulse_order3(
                macro_shocks=macro_shocks,
                sector="Semiconductor",
                vol_multiplier=vol_mult,
            )
            impulse_trajectory.append(impulse)

            # F889 MCSI Inputs aligned with the same stress parameters
            vix_vel = float(max(0.0, -0.05 + 0.85 * stress_level))
            vix_tsr = float(0.90 + 0.50 * stress_level)  # Contango -> Backwardation
            credit_bps = float(300.0 + 700.0 * stress_level)
            contagion_eig = float(0.30 + 1.20 * stress_level)

            mcsi = engine_f889.evaluate_mcsi_crisis_severity_index(
                vix_velocity=vix_vel,
                vix_tsr=vix_tsr,
                credit_spread_bps=credit_bps,
                contagion_eig=contagion_eig,
            )
            mcsi_trajectory.append(mcsi)

            cb_result = engine_f889.check_crisis_circuit_breaker(xi=mcsi, threshold=0.65)
            leverage_limits.append(cb_result["max_leverage_limit"])

        # 1. Sanity: Initial impulse is positive, initial MCSI is low
        self.assertGreater(impulse_trajectory[0], 0.0, "Benign market should produce positive impulse for Semiconductor")
        self.assertLess(mcsi_trajectory[0], 0.25, "Benign market MCSI must be low")
        self.assertGreaterEqual(leverage_limits[0], 1.50, "Benign leverage must be expansive")

        # 2. Catastrophic state: Terminal impulse plummets to deep negative territory
        self.assertLess(impulse_trajectory[-1], -2.0, "Crisis shock must severely depress Semiconductor impulse")
        self.assertGreaterEqual(mcsi_trajectory[-1], 0.85, "Crisis shock must drive MCSI near upper ceiling")
        self.assertAlmostEqual(leverage_limits[-1], 0.20, delta=1e-5, msg="Circuit-breaker must hard lock leverage to 0.20x")

        # 3. Directional consistency: High rank correlation between negative impulse and MCSI
        # Invert impulse so higher value means higher distress
        neg_impulse = [-x for x in impulse_trajectory]
        # Spearman rank correlation
        rank_neg_impulse = np.argsort(np.argsort(neg_impulse))
        rank_mcsi = np.argsort(np.argsort(mcsi_trajectory))
        corr = float(np.corrcoef(rank_neg_impulse, rank_mcsi)[0, 1])

        self.assertGreater(corr, 0.85, f"Directional correlation must exceed 0.85, got {corr:.4f}")

    def test_adv_scenario1_circuit_breaker_transition_boundary(self):
        """Stress 1.2: Fine-grained inspection around MCSI threshold xi = 0.65."""
        engine = MacroCrisisSeverityIndexEngine()

        # Step around threshold in steps of 0.005
        xis = np.linspace(0.60, 0.70, 21)
        for xi in xis:
            res = engine.check_crisis_circuit_breaker(float(xi), threshold=0.65)
            self.assertEqual(res["synthetic_rows"], 0)
            self.assertIsInstance(res["synthetic_rows"], int)

            if xi >= 0.65:
                self.assertTrue(res["circuit_breaker_triggered"])
                self.assertEqual(res["max_leverage_limit"], 0.20)
                self.assertEqual(res["hedge_overlay_ratio"], 1.0)
                self.assertTrue(res["gate8_inverse_hedge_active"])
                self.assertTrue(res["new_longs_gated"])
                self.assertTrue(res["sma200_hard_exit"])
                self.assertEqual(res["crisis_status"], "CRISIS_ACTIVE")
                self.assertIn("252670", res["inverse_hedge_etfs"])
                self.assertIn("SH", res["inverse_hedge_etfs"])
            else:
                self.assertFalse(res["circuit_breaker_triggered"])
                self.assertGreater(res["max_leverage_limit"], 0.20)
                self.assertLessEqual(res["hedge_overlay_ratio"], 0.40)
                self.assertFalse(res["gate8_inverse_hedge_active"])
                self.assertFalse(res["new_longs_gated"])
                self.assertFalse(res["sma200_hard_exit"])

    # =========================================================================
    # SCENARIO 2: Contagion Tipping Point & Perron-Frobenius (F888)
    # =========================================================================

    def test_adv_scenario2_perron_frobenius_tipping_point_detection(self):
        """Stress 2.1: Verify dominant eigenvalue lambda_max(A) > 1.0 detected across scaling sweeps."""
        engine = GraphGrangerCausalityNetwork()

        # Build base directed graph with 6 nodes
        # Node 0 is the epicenter radiating information shocks to nodes 1, 2, 3, 4, 5
        K = 6
        base_A = np.zeros((K, K), dtype=np.float64)
        for i in range(1, K):
            base_A[i, 0] = 0.45  # 0 transmits to i
        # Add feedback cycle 1 -> 2 -> 3 -> 0
        base_A[2, 1] = 0.35
        base_A[3, 2] = 0.35
        base_A[0, 3] = 0.30

        # Sweep scale factor from 0.5 (subcritical) to 2.5 (supercritical contagion tipping point)
        scales = np.linspace(0.5, 2.5, 21)
        tipping_point_found = False

        for scale in scales:
            A_scaled = base_A * scale
            np.fill_diagonal(A_scaled, 0.0)

            res = engine.detect_systemic_contagion(A_scaled, threshold=0.35)
            eigs = np.linalg.eigvals(A_scaled)
            actual_lambda_max = float(np.max(np.abs(eigs)))

            self.assertAlmostEqual(res["dominant_eigenvalue"], actual_lambda_max, places=5)
            self.assertAlmostEqual(res["spectral_radius"], actual_lambda_max, places=5)

            if actual_lambda_max > 1.0:
                tipping_point_found = True
                self.assertTrue(res["is_contagion_alert"], "Must raise contagion alert when lambda_max > 1.0")

            # Out-degree spreader ranking must identify Node 0 as the top spreader
            self.assertEqual(res["spreader_ranking"][0], 0, "Node 0 must be top spreader ranking")

        self.assertTrue(tipping_point_found, "Supercritical tipping point lambda_max > 1.0 must be verified")

    def test_adv_scenario2_synthetic_panic_time_series_injection(self):
        """Stress 2.2: Injected panic contagion in time series identified by Rényi Transfer Entropy."""
        engine = GraphGrangerCausalityNetwork()

        np.random.seed(42)
        T = 250
        K = 5

        # Generate standard AR(1) processes
        X = np.random.randn(T, K) * 0.015

        # Sector 0 injects severe lead-lag panic contagion:
        # At t=100..150, Sector 0 experiences extreme volatility jumps
        # Sectors 1, 2, 3, 4 copy Sector 0's t-1 movements with high fidelity
        for t in range(1, T):
            if 80 <= t <= 180:
                X[t, 0] = -0.06 if (t % 3 == 0) else 0.04
                for k in range(1, K):
                    X[t, k] = 0.85 * X[t - 1, 0] + np.random.randn() * 0.005
            else:
                for k in range(1, K):
                    X[t, k] = 0.20 * X[t - 1, k] + np.random.randn() * 0.01

        # Fit directed Rényi Transfer Entropy network
        adj = engine.fit_renyi_transfer_entropy_network(X, alpha=1.5, bins=3, lag=1)

        # Basic structural assertions
        self.assertEqual(adj.shape, (K, K))
        self.assertTrue(np.all(np.diag(adj) == 0.0), "Self-transfer entropy diagonal must be strictly 0.0")
        self.assertTrue(np.all(adj >= 0.0), "Transfer entropy must be non-negative")

        # Detect contagion analytics
        res = engine.detect_systemic_contagion(adj, threshold=0.20)

        # Sector 0 should be top spreader or transmitting strong information
        out_degrees = res["out_degree"]
        in_degrees = res["in_degree"]

        self.assertEqual(res["spreader_ranking"][0], 0, "Injected source Sector 0 must be identified as primary spreader")
        self.assertGreater(out_degrees[0], in_degrees[0], "Sector 0 must be a net information transmitter")

    # =========================================================================
    # SCENARIO 3: Yield Curve Convexity Stress (F887)
    # =========================================================================

    def test_adv_scenario3_fifteen_yield_curve_topologies_convexity_and_beta_clamp(self):
        """Stress 3.1: Stress-test 15 distinct yield curve topologies."""
        delta_engine = DeltaBetaHedgeEngine()
        maturities = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0], dtype=np.float64)

        # 15 distinct yield curve topologies
        topologies: Dict[str, np.ndarray] = {
            "1_normal_upward": np.array([0.030, 0.032, 0.036, 0.040, 0.043, 0.047, 0.050, 0.052, 0.054, 0.055]),
            "2_steep_upward": np.array([0.015, 0.018, 0.025, 0.035, 0.042, 0.050, 0.056, 0.060, 0.063, 0.065]),
            "3_mild_inverted": np.array([0.055, 0.054, 0.052, 0.048, 0.046, 0.044, 0.043, 0.042, 0.041, 0.040]),
            "4_deep_crisis_inverted": np.array([0.075, 0.070, 0.062, 0.052, 0.045, 0.038, 0.035, 0.032, 0.030, 0.028]),
            "5_flat_curve": np.array([0.045, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045]),
            "6_barbell_u_shaped": np.array([0.055, 0.050, 0.042, 0.035, 0.032, 0.034, 0.038, 0.044, 0.052, 0.056]),
            "7_humped_curve": np.array([0.030, 0.035, 0.042, 0.050, 0.054, 0.053, 0.048, 0.044, 0.040, 0.038]),
            "8_inverted_humped": np.array([0.050, 0.045, 0.038, 0.032, 0.030, 0.034, 0.040, 0.045, 0.048, 0.050]),
            "9_butterfly_twist": np.array([0.052, 0.048, 0.042, 0.036, 0.035, 0.039, 0.045, 0.042, 0.048, 0.052]),
            "10_s_shaped_double_inflection": np.array([0.030, 0.038, 0.046, 0.044, 0.041, 0.042, 0.046, 0.050, 0.048, 0.052]),
            "11_zirp_ultra_low": np.array([0.001, 0.002, 0.004, 0.006, 0.008, 0.010, 0.011, 0.012, 0.013, 0.014]),
            "12_hyper_inflation_high": np.array([0.120, 0.125, 0.132, 0.140, 0.145, 0.150, 0.154, 0.158, 0.160, 0.162]),
            "13_near_zero_short_extreme_steep": np.array([0.0005, 0.002, 0.005, 0.015, 0.025, 0.038, 0.048, 0.055, 0.060, 0.065]),
            "14_bear_flattener": np.array([0.065, 0.064, 0.063, 0.062, 0.061, 0.060, 0.059, 0.058, 0.057, 0.056]),
            "15_bull_steepener": np.array([0.010, 0.012, 0.015, 0.020, 0.026, 0.032, 0.036, 0.039, 0.041, 0.042]),
        }

        self.assertEqual(len(topologies), 15, "Must test exactly 15 yield curve topologies")

        # Test portfolio durations across extreme ranges
        portfolio_durations = [0.0, 0.5, 2.0, 5.0, 10.0, 18.0, 25.0, 40.0]

        for name, yields in topologies.items():
            # 1. Fit NSS 6-parameter curve
            params = delta_engine.fit_nss_yield_curve_6param(maturities, yields)
            for key in ("beta0", "beta1", "beta2", "beta3", "lambda1", "lambda2", "tau1", "tau2"):
                self.assertIn(key, params, f"Missing parameter {key} in topology {name}")
                val = params[key]
                self.assertTrue(math.isfinite(val), f"Parameter {key} must be finite in topology {name}, got {val}")

            # 2. Extract 2Y-10Y slope
            idx_2y = 3
            idx_10y = 7
            slope_2y_10y = float(yields[idx_10y] - yields[idx_2y])

            # 3. Test across all portfolio durations
            for dur in portfolio_durations:
                hedge = delta_engine.compute_duration_convexity_hedge(
                    portfolio_duration=dur,
                    slope_2y_10y=slope_2y_10y,
                )

                # ASSERTION A: Convexity adjustment must remain non-negative, and strictly positive for dur > 0
                conv = hedge["convexity_adjustment"]
                if dur > 0.0:
                    self.assertGreater(conv, 0.0, f"Convexity adjustment must be > 0 for dur={dur} in {name}")
                else:
                    self.assertGreaterEqual(conv, 0.0, f"Convexity adjustment must be >= 0 for dur=0 in {name}")

                # ASSERTION B: Market beta clamp must NEVER exceed 1.000001
                beta_clamp = hedge["market_beta_clamp"]
                self.assertLessEqual(
                    beta_clamp,
                    1.000001,
                    f"CRITICAL: Market beta clamp {beta_clamp} exceeded 1.000001 in topology {name} with dur={dur}",
                )

                # ASSERTION C: Duration haircut in [0.20, 1.0]
                haircut = hedge["duration_haircut"]
                self.assertGreaterEqual(haircut, 0.20, f"Haircut below floor 0.20 in {name}")
                self.assertLessEqual(haircut, 1.0, f"Haircut above ceiling 1.0 in {name}")

                # ASSERTION D: Hedge ratio in [0.0, 1.0]
                hr = hedge["hedge_ratio"]
                self.assertGreaterEqual(hr, 0.0, f"Hedge ratio below 0 in {name}")
                self.assertLessEqual(hr, 1.0, f"Hedge ratio above 1 in {name}")

    def test_adv_scenario3_nss_direct_curve_reconstruction_stress(self):
        """Stress 3.2: Direct reconstruction of NSS zero-coupon yield and forward rates."""
        maturities = np.array([0.1, 0.5, 1.0, 5.0, 10.0, 30.0], dtype=np.float64)

        # Test extreme parameters
        test_param_sets = [
            (0.05, -0.02, 0.03, -0.01, 1.5, 6.0),
            (0.15, 0.05, -0.04, 0.02, 0.5, 12.0),
            (0.01, -0.005, 0.002, 0.001, 2.0, 8.0),
        ]

        for b0, b1, b2, b3, t1, t2 in test_param_sets:
            yields = evaluate_nss_zero_coupon_yield(maturities, b0, b1, b2, b3, t1, t2)
            self.assertEqual(len(yields), len(maturities))
            self.assertTrue(np.all(np.isfinite(yields)), "Yields must be finite")

            for m in maturities:
                fwd = compute_nss_instantaneous_forward_rate(float(m), b0, b1, b2, b3, t1, t2)
                self.assertTrue(math.isfinite(fwd), f"Forward rate at maturity {m} must be finite")

    # =========================================================================
    # SCENARIO 4: Non-Linear CIP Arbitrage Bounds & Continuity (F886)
    # =========================================================================

    def test_adv_scenario4_zero_interest_rate_differential_and_extreme_spreads(self):
        """Stress 4.1: Test synthetic zero interest rate differential (r_US == r_KR) and extreme spreads."""
        r_same = 0.035
        spot = 1350.0

        # Extreme forward/spot multipliers from deep discount (0.30x) to extreme premium (3.0x)
        multipliers = [0.30, 0.50, 0.75, 0.90, 0.99, 1.00, 1.01, 1.10, 1.25, 1.50, 2.00, 3.00]

        for mult in multipliers:
            fwd = spot * mult
            dev = compute_nonlinear_cip_deviation(spot, fwd, r_usd=r_same, r_krw=r_same, tenor_days=90)
            self.assertTrue(math.isfinite(dev), f"CIP deviation must be finite for multiplier {mult}")

            # When fwd > spot, dev must be positive; when fwd < spot, dev must be negative
            if mult > 1.0:
                self.assertGreater(dev, 0.0, f"Expected positive deviation for premium forward mult={mult}")
            elif mult < 1.0:
                self.assertLess(dev, 0.0, f"Expected negative deviation for discount forward mult={mult}")

            # Test optimal hedge ratio calculation with zero rate diff
            macro_input = FXMacroInput(
                usdkrw_spot=spot,
                forward_rate=fwd,
                kr_rate=r_same,
                us_rate=r_same,
                fx_momentum_20d=0.0,
                fx_volatility_20d=0.10,
                regime_label="BULL_LOW_VOL",
            )
            h = fx_calc_optimal_hedge(macro_input)
            self.assertGreaterEqual(h, 0.0, f"Hedge ratio must be >= 0.0 for mult={mult}")
            self.assertLessEqual(h, 1.0, f"Hedge ratio must be <= 1.0 for mult={mult}")

    def test_adv_scenario4_hedge_ratio_continuity_and_no_discrete_jumps(self):
        """Stress 4.2: High-resolution fine-grid continuity sweep across 1,000 steps."""
        spot = 1350.0
        r_kr = 0.035
        r_us = 0.050

        # 1. Test NonlinearCIPHedger core (F886): compute_adaptive_fx_hedge_ratio and cip_calc_optimal_hedge
        # Lipschitz continuity: d/dx[2.5 * tanh(100*x)] <= 250.0.
        # For step size Delta x = 0.0004, maximum theoretical Delta h <= 250 * 0.0004 = 0.100.
        n_steps = 1000
        mults = np.linspace(0.80, 1.20, n_steps)
        cip_hedge_ratios: List[float] = []

        for mult in mults:
            fwd = spot * mult
            macro_input = {
                "usdkrw_spot": spot,
                "forward_rate": fwd,
                "kr_rate": r_kr,
                "us_rate": r_us,
                "tenor_days": 90,
                "regime_label": "SIDEWAYS_LOW_VOL",
            }
            h_cip = cip_calc_optimal_hedge(macro_input)
            self.assertTrue(math.isfinite(h_cip))
            self.assertTrue(0.0 <= h_cip <= 1.0)
            cip_hedge_ratios.append(h_cip)

        # Verify Lipschitz continuity: maximum step diff is strictly bounded by 250 * Delta x = 0.1001
        cip_step_diffs = np.abs(np.diff(cip_hedge_ratios))
        cip_max_step_jump = float(np.max(cip_step_diffs))
        self.assertLessEqual(
            cip_max_step_jump,
            0.105,
            f"NonlinearCIPHedger violated Lipschitz bound 250*dx: {cip_max_step_jump:.5f}",
        )

        # Verify asymptotic continuity as step -> 0 (infinitesimal test at inflection point)
        h_left = cip_calc_optimal_hedge({"usdkrw_spot": spot, "forward_rate": spot * 1.00360, "kr_rate": r_kr, "us_rate": r_us, "tenor_days": 90, "regime_label": "SIDEWAYS_LOW_VOL"})
        h_right = cip_calc_optimal_hedge({"usdkrw_spot": spot, "forward_rate": spot * 1.00361, "kr_rate": r_kr, "us_rate": r_us, "tenor_days": 90, "regime_label": "SIDEWAYS_LOW_VOL"})
        infinitesimal_jump = abs(h_right - h_left)
        self.assertLess(
            infinitesimal_jump,
            0.003,
            f"NonlinearCIPHedger must have near-zero jump for infinitesimal step, got {infinitesimal_jump:.6f}",
        )

        # 2. Test DynamicFXHedgingEngine: Empirically document the discrete jump of ~0.026 at -25 bps
        # Finding: `if cip_dev < -25.0: cip_adj = -cip_dev / 1000.0` introduces a step jump of 0.025~0.026
        eng_fx = DynamicFXHedgingEngine()
        fx_hedge_ratios: List[float] = []
        for mult in mults:
            fwd = spot * mult
            macro_input = FXMacroInput(
                usdkrw_spot=spot,
                forward_rate=fwd,
                kr_rate=r_kr,
                us_rate=r_us,
                fx_momentum_20d=0.01 * (mult - 1.0) * 10,
                fx_volatility_20d=0.12,
                regime_label="SIDEWAYS_LOW_VOL",
            )
            h_fx = eng_fx.calculate_optimal_hedge_ratio(macro_input)
            self.assertTrue(math.isfinite(h_fx))
            fx_hedge_ratios.append(h_fx)

        fx_step_diffs = np.abs(np.diff(fx_hedge_ratios))
        fx_max_step_jump = float(np.max(fx_step_diffs))

        # Empirically verify that the un-smoothed threshold in DynamicFXHedgingEngine causes a discrete jump of ~0.026
        self.assertGreater(
            fx_max_step_jump,
            0.020,
            f"Expected discrete jump discontinuity in DynamicFXHedgingEngine > 0.020, got {fx_max_step_jump:.5f}",
        )
        self.assertLess(
            fx_max_step_jump,
            0.035,
            f"Expected discrete jump discontinuity in DynamicFXHedgingEngine < 0.035, got {fx_max_step_jump:.5f}",
        )

    def test_adv_scenario4_interest_rate_differential_continuity_sweep(self):
        """Stress 4.3: Interest rate differential sweep from -10% to +10% with zero forward spread."""
        spot = 1350.0
        r_kr = 0.035
        rate_diffs = np.linspace(-0.10, 0.10, 200)

        # Test NonlinearCIPHedger (smooth tanh basis formulation)
        h_cip_vals: List[float] = []
        for r_diff in rate_diffs:
            r_us = r_kr + r_diff
            macro_in = {
                "usdkrw_spot": spot,
                "forward_rate": spot,  # zero spread
                "kr_rate": r_kr,
                "us_rate": r_us,
                "regime_label": "BULL_LOW_VOL",
            }
            h = cip_calc_optimal_hedge(macro_in)
            self.assertTrue(0.0 <= h <= 1.0)
            h_cip_vals.append(h)

        diffs = np.abs(np.diff(h_cip_vals))
        max_diff = float(np.max(diffs))
        # With Delta r = 0.001, tau = 0.25, Delta basis = 0.00025, max diff <= 250 * 0.00025 = 0.0625
        self.assertLessEqual(max_diff, 0.070, f"NonlinearCIPHedger rate differential jump {max_diff:.5f} > 0.070")

    def test_adv_scenario4_order_emission_and_margin_protection(self):
        """Stress 4.4: Verify structured order generation for both '261250' and 'USDKRW_FWD'."""
        engine = DynamicFXHedgingEngine()

        # Order 1: KRX Inverse ETF
        res_etf = {
            "hedge_notional_krw": 50_000_000.0,
            "hedge_ratio": 0.45,
            "hedge_order_symbol": "261250",
            "hedge_weight": 0.08,
            "collateral_required_krw": 7_500_000.0,
            "reason": "CIP_BEAR_HEDGE",
        }
        order_etf = engine.generate_fx_hedge_order(res_etf)
        self.assertIsNotNone(order_etf)
        self.assertEqual(order_etf["symbol"], "261250")
        self.assertEqual(order_etf["market"], "KRX")
        self.assertEqual(order_etf["order_type"], "MARKET")

        # Order 2: OTC Forward Swap
        res_fwd = {
            "hedge_notional_krw": 120_000_000.0,
            "hedge_ratio": 0.70,
            "hedge_order_symbol": "USDKRW_FWD",
            "hedge_weight": 0.15,
            "collateral_required_krw": 18_000_000.0,
            "reason": "CRISIS_CURRENCY_OVERLAY",
        }
        order_fwd = engine.generate_fx_hedge_order(res_fwd)
        self.assertIsNotNone(order_fwd)
        self.assertEqual(order_fwd["symbol"], "USDKRW_FWD")
        self.assertEqual(order_fwd["market"], "OTC_FX")
        self.assertEqual(order_fwd["order_type"], "FORWARD_SWAP")

        # Order 3: Sub-threshold ratio (< 0.005) or non-positive notional returns None safely
        res_zero = {"hedge_notional_krw": 0.0, "hedge_ratio": 0.0}
        self.assertIsNone(engine.generate_fx_hedge_order(res_zero))

    # =========================================================================
    # SCENARIO 5: Dual-Tree Cryptographic Parity & Invariants
    # =========================================================================

    def test_adv_scenario5_dual_tree_sha256_cryptographic_parity(self):
        """Stress 5.1: Verify bit-for-bit SHA-256 parity for all 5 Phase 181 modules."""
        target_pairs = [
            ("src/core/cross_asset_spillover.py", "trading_system/src/core/cross_asset_spillover.py"),
            ("src/core/cross_asset_tensor_impulse.py", "trading_system/src/core/cross_asset_tensor_impulse.py"),
            ("src/risk/dynamic_fx_hedging_engine.py", "trading_system/src/risk/dynamic_fx_hedging_engine.py"),
            ("src/core/nonlinear_cip_hedger.py", "trading_system/src/core/nonlinear_cip_hedger.py"),
            ("src/risk/delta_beta_hedge.py", "trading_system/src/risk/delta_beta_hedge.py"),
            ("src/core/nss_yield_curve_hedge.py", "trading_system/src/core/nss_yield_curve_hedge.py"),
            ("src/ai/graph_granger_causality.py", "trading_system/src/ai/graph_granger_causality.py"),
            ("src/core/transfer_entropy_contagion.py", "trading_system/src/core/transfer_entropy_contagion.py"),
            ("src/risk/risk_manager.py", "trading_system/src/risk/risk_manager.py"),
            ("src/core/macro_crisis_severity_index.py", "trading_system/src/core/macro_crisis_severity_index.py"),
        ]

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        for rel_src, rel_tgt in target_pairs:
            src_path = os.path.join(base_dir, rel_src)
            tgt_path = os.path.join(base_dir, rel_tgt)

            self.assertTrue(os.path.exists(src_path), f"Source file does not exist: {rel_src}")
            self.assertTrue(os.path.exists(tgt_path), f"Target file does not exist: {rel_tgt}")

            with open(src_path, "rb") as f:
                src_hash = hashlib.sha256(f.read()).hexdigest()
            with open(tgt_path, "rb") as f:
                tgt_hash = hashlib.sha256(f.read()).hexdigest()

            self.assertEqual(
                src_hash,
                tgt_hash,
                f"Cryptographic divergence between {rel_src} and {rel_tgt} (SHA256 mismatch!)",
            )

    def test_adv_scenario5_synthetic_rows_integer_zero_invariant(self):
        """Stress 5.2: Strictly native Python int 0 across all Phase 181 score generators."""
        df_dummy = pd.DataFrame({
            "symbol": ["005930", "AAPL", "000660", "NVDA"],
            "close": [75000.0, 180.0, 120000.0, 450.0],
            "sector": ["Semiconductor", "Information Technology", "Semiconductor", "Tech"],
        })

        engines = [
            CrossAssetTensorImpulseEngine(),
            TransferEntropyContagionNetwork(),
            NSSYieldCurveDurationHedgeEngine(),
            MacroCrisisSeverityIndexEngine(),
        ]

        for eng in engines:
            sdf = eng.generate_scores(df_dummy)
            for item in sdf.to_dict("records"):
                self.assertIn("metadata", item)
                meta = item["metadata"]
                self.assertIn("synthetic_rows", meta)
                val = meta["synthetic_rows"]
                self.assertIs(type(val), int, f"synthetic_rows must be native int, got {type(val)}")
                self.assertEqual(val, 0, f"synthetic_rows must be 0, got {val}")


if __name__ == "__main__":
    unittest.main()
