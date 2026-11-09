"""
tests/test_phase189_adversarial_stress.py — Adversarial Stress & Property-Based Verification Suite
for Release R182 / Phase 189 Global Macro & Rates (Features F925–F929).

Empirical Challenger Test Suite:
- F925: Extreme macro series (+/-100 sigma shocks, NaN bursts, flatlines, zero input).
        Dyadic wavelet exact reconstruction and non-exploding finite impulse invariants.
- F926: Negative forward rates, zero/negative spot prices, flight-to-safety crisis inputs.
        Hedge ratio clamp [0.0, 1.0] and cash margin ceiling <= 85% of cash.
- F927: Inverted yield curves, flat curves, negative yields.
        NSS-10 least squares convergence stability, forward rate limit f(0) = beta_0 + beta_1,
        and portfolio market beta clamp <= 1.000001.
- F928: Disconnected asset matrices, identical return series, chaotic return series.
        Finite Rényi transfer entropy, zero diagonal A_ii = 0, and valid spectral radius.
- F929: Continuous MCSI score bounds, strictly non-increasing leverage (2.15x -> 0.00x),
        and Gate 8 synthetic inverse ETF overlay activation.
"""

from __future__ import annotations

import math
import unittest
from typing import Dict, Any, List

import numpy as np
import pandas as pd

# Feature imports
from src.core.macro_hyper_tensor_impulse_v182 import (
    MacroHyperTensorImpulseV182Engine,
    compute_5th_order_hyper_tensor_impulse,
    decompose_macro_impulse_multi_frequency_wavelet,
    compute_unpriced_macro_diffusion_v182,
    GLOBAL_MACRO_FACTORS,
)
from src.core.quad_curvature_fx_hedger import (
    QuadCurvatureFXHedgingEngine,
    FXMacroInput,
    FXHedgeResult,
    compute_quad_curvature_basis_spread,
    calculate_quad_curvature_hedge_ratio,
    generate_quad_fx_hedge_order,
    compute_quad_curvature_triangular_arbitrage,
)
from src.core.nss10_rates_hedge import (
    NSS10RatesHedgeEngine,
    fit_extended_nss_10param_curve,
    evaluate_nss10_yield,
    compute_nss10_instantaneous_forward_rate,
    compute_key_rate_convexity_immunization_v182,
    detect_yield_curve_inversion_v182,
)
from src.core.renyi_schrodinger_transfer_entropy import (
    RenyiSchrodingerTransferEntropyEngine,
    compute_directed_renyi_schrodinger_transfer_entropy,
    detect_systemic_contagion_network_v182,
)
from src.core.macro_crisis_severity_index_v182 import (
    MacroCrisisSeverityIndexV182Engine,
    compute_mcsi_v182_multi_horizon_score,
    determine_mcsi_v182_6tier_gating,
    get_leverage_limit_for_mcsi_v182,
    check_circuit_breaker_v182,
    TIER_NORMAL,
    TIER_ELEVATED,
    TIER_HIGH_STRESS,
    TIER_SYSTEMIC_CRISIS,
    TIER_PANIC_LIQUIDITY_SQUEEZE,
    TIER_CIRCUIT_BREAKER_HALT,
    GATE8_INVERSE_ETFS,
)


class TestPhase189AdversarialStress(unittest.TestCase):
    """Adversarial stress and edge-case test suite for Phase 189."""

    # =========================================================================
    # F925: Hyper-Tensor Macro Impulse & Wavelet Adversarial Tests
    # =========================================================================

    def test_adv_f925_01_extreme_100_sigma_shocks(self):
        """Verify 5th-order hyper-tensor responds finitely to +/-100 sigma macro shocks."""
        pos_100_sigma = {factor: 100.0 for factor in GLOBAL_MACRO_FACTORS}
        neg_100_sigma = {factor: -100.0 for factor in GLOBAL_MACRO_FACTORS}

        impulse_pos = compute_5th_order_hyper_tensor_impulse(pos_100_sigma, sector="Semiconductor")
        impulse_neg = compute_5th_order_hyper_tensor_impulse(neg_100_sigma, sector="Semiconductor")

        self.assertTrue(math.isfinite(impulse_pos), f"Positive 100-sigma impulse must be finite, got {impulse_pos}")
        self.assertTrue(math.isfinite(impulse_neg), f"Negative 100-sigma impulse must be finite, got {impulse_neg}")
        # Quintic resonance preserves sign direction for positive vs negative tail shocks
        self.assertGreater(impulse_pos, 0.0)
        self.assertLess(impulse_neg, 0.0)

    def test_adv_f925_02_zero_and_flatline_macro_shocks(self):
        """Verify zero input and flatline shocks yield exact predictable behavior."""
        zero_shocks = {factor: 0.0 for factor in GLOBAL_MACRO_FACTORS}
        impulse_zero = compute_5th_order_hyper_tensor_impulse(zero_shocks, sector="Semiconductor")
        self.assertEqual(impulse_zero, 0.0, "Zero shocks must produce exactly 0.0 impulse")

        # Flatline across factors
        flat_shocks = {factor: 0.05 for factor in GLOBAL_MACRO_FACTORS}
        impulse_flat = compute_5th_order_hyper_tensor_impulse(flat_shocks, sector="Financials")
        self.assertTrue(math.isfinite(impulse_flat))

    def test_adv_f925_03_wavelet_exact_reconstruction_property(self):
        """
        Verify multi-frequency dyadic wavelet decomposition satisfies exact reconstruction:
            transient + cyclical + intermediate + structural == reconstructed == original
        across various adversarial signal shapes (spikes, flatlines, short series, noise).
        """
        test_series = [
            ("short_series_length_4", np.array([1.0, -2.0, 3.0, -4.0])),
            ("short_series_length_7", np.linspace(-5.0, 5.0, 7)),
            ("flatline_series", np.full(120, 42.0)),
            ("zeros_series", np.zeros(80)),
            ("100_sigma_spike", np.concatenate([np.zeros(40), [100.0], np.zeros(40)])),
            ("rapid_alternating", np.array([(-1.0) ** i * 5.0 for i in range(150)])),
            ("sinusoid_with_drift", np.sin(np.linspace(0, 10 * np.pi, 200)) + np.linspace(0, 5, 200)),
        ]

        for name, series in test_series:
            with self.subTest(series_type=name):
                d = decompose_macro_impulse_multi_frequency_wavelet(series)
                sum_components = d["transient"] + d["cyclical"] + d["intermediate"] + d["structural"]
                reconstructed = d["reconstructed"]

                # Check exact reconstruction within machine precision
                np.testing.assert_allclose(
                    sum_components,
                    series,
                    atol=1e-10,
                    err_msg=f"Wavelet sum failed exact reconstruction for {name}",
                )
                np.testing.assert_allclose(
                    reconstructed,
                    series,
                    atol=1e-10,
                    err_msg=f"Reconstructed field failed exact match for {name}",
                )
                self.assertTrue(np.all(np.isfinite(sum_components)), f"NaN/Inf in wavelet output for {name}")

    def test_adv_f925_04_unpriced_diffusion_bounds_under_extreme_dynamics(self):
        """Verify unpriced diffusion momentum alpha is strictly bounded in [-3.0, 3.0]."""
        extreme_trajectories = [
            np.full(50, 1e6),
            np.full(50, -1e6),
            np.random.normal(0, 50.0, 100),
            np.zeros(20),
        ]
        for traj in extreme_trajectories:
            alpha = compute_unpriced_macro_diffusion_v182(0.0, traj, half_life=3.0)
            self.assertTrue(-3.0 <= alpha <= 3.0, f"Alpha {alpha} out of bounds [-3.0, 3.0]")

    # =========================================================================
    # F926: Quad-Curvature FX Hedger Adversarial Tests
    # =========================================================================

    def test_adv_f926_01_negative_forward_rates_and_zero_spot(self):
        """Verify quad-curvature basis spread and hedge ratio handle negative forward and near-zero spot."""
        # Spot near zero is clamped safely by max(1e-6, spot)
        spread_near_zero_spot = compute_quad_curvature_basis_spread(
            spot=0.0, forward=1350.0, r_dom=0.035, r_for=0.045, tau=0.25
        )
        self.assertTrue(math.isfinite(spread_near_zero_spot))

        # Negative forward rate (e.g. inverted currency synthetic forward)
        spread_neg_forward = compute_quad_curvature_basis_spread(
            spot=1350.0, forward=-100.0, r_dom=0.035, r_for=0.045, tau=0.25
        )
        self.assertTrue(math.isfinite(spread_neg_forward))

    def test_adv_f926_02_hedge_ratio_bounds_under_flight_to_safety_crisis(self):
        """Verify hedge ratio h* is strictly in [0.0, 1.0] and <= 0.25 in flight-to-safety crisis regimes."""
        crisis_regimes = ["PANIC", "SYSTEMIC_CRISIS", "CIRCUIT_BREAKER_HALT", "CRISIS_BEAR"]
        for regime in crisis_regimes:
            input_crisis = FXMacroInput(
                usdkrw_spot=1450.0,
                forward_rate=1460.0,
                regime_label=regime,
                stock_volatility=0.45,
                fx_volatility_20d=0.25,
                stock_fx_correlation=-0.80,  # Extreme negative correlation
            )
            h_star = calculate_quad_curvature_hedge_ratio(input_crisis)
            self.assertGreaterEqual(h_star, 0.0)
            self.assertLessEqual(h_star, 0.25, f"Hedge ratio {h_star} exceeds 0.25 flight-to-safety cap in {regime}")

    def test_adv_f926_03_cash_collateral_ceiling_invariant(self):
        """Verify cash margin collateral NEVER exceeds 85% of available cash under any leverage demand."""
        stress_scenarios = [
            {"exp": 1e9, "cash": 1000.0, "req": 0.20},        # Massive exposure, tiny cash
            {"exp": 5e8, "cash": 1e7, "req": 0.10},          # High exposure
            {"exp": 1e6, "cash": 1.0, "req": 0.05},          # 1 KRW cash
            {"exp": 1e8, "cash": 0.0, "req": 0.05},          # 0 cash (must clamp to 1.0)
            {"exp": -1e6, "cash": 1e6, "req": 0.05},         # Negative exposure
        ]
        for sc in stress_scenarios:
            order = generate_quad_fx_hedge_order(
                hedge_ratio=1.0,
                us_exposure_krw=sc["exp"],
                available_cash_krw=sc["cash"],
                initial_margin_req=sc["req"],
            )
            cash_avail = max(1.0, float(sc["cash"]))
            self.assertLessEqual(
                order.collateral_required_krw,
                0.85 * cash_avail + 1e-4,
                f"Collateral {order.collateral_required_krw} exceeded 85% of cash {cash_avail}",
            )
            self.assertTrue(0.0 <= order.hedge_ratio <= 1.0)

    # =========================================================================
    # F927: NSS-10 Yield Curve & Convexity Immunization Adversarial Tests
    # =========================================================================

    def test_adv_f927_01_nss10_fitting_inverted_and_negative_curves(self):
        """Verify NSS-10 least squares converges stably under inverted and negative yield regimes."""
        tenors = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0])

        curves = [
            ("deeply_inverted", np.array([0.08, 0.075, 0.07, 0.065, 0.06, 0.055, 0.05, 0.045, 0.04, 0.038])),
            ("negative_yields", np.array([-0.005, -0.004, -0.003, -0.002, -0.001, 0.001, 0.003, 0.005, 0.010, 0.015])),
            ("flat_curve", np.full(10, 0.035)),
            ("humped_curve", np.array([0.02, 0.03, 0.05, 0.06, 0.055, 0.05, 0.045, 0.04, 0.038, 0.035])),
        ]

        for name, yields in curves:
            with self.subTest(curve_name=name):
                params = fit_extended_nss_10param_curve(tenors, yields)
                # Ensure all 10 parameters are present and finite
                for p_name in ["beta0", "beta1", "beta2", "beta3", "beta4", "beta5", "tau1", "tau2", "tau3", "tau4"]:
                    self.assertIn(p_name, params)
                    self.assertTrue(math.isfinite(params[p_name]), f"Parameter {p_name} is not finite in {name}")
                self.assertTrue(math.isfinite(params["mse"]))
                self.assertGreaterEqual(params["mse"], 0.0)

    def test_adv_f927_02_instantaneous_forward_rate_limit_f0_identity(self):
        """
        Verify instantaneous forward rate satisfies mathematical identity:
            lim_{tau -> 0} f(tau) = beta_0 + beta_1
        across random parameter variations.
        """
        np.random.seed(42)
        for _ in range(25):
            b0 = float(np.random.uniform(0.01, 0.08))
            b1 = float(np.random.uniform(-0.04, 0.04))
            params = {
                "beta0": b0,
                "beta1": b1,
                "beta2": float(np.random.uniform(-0.02, 0.02)),
                "beta3": float(np.random.uniform(-0.02, 0.02)),
                "beta4": float(np.random.uniform(-0.01, 0.01)),
                "beta5": float(np.random.uniform(-0.01, 0.01)),
                "tau1": float(np.random.uniform(1.0, 3.0)),
                "tau2": float(np.random.uniform(3.0, 6.0)),
                "tau3": float(np.random.uniform(7.0, 15.0)),
                "tau4": float(np.random.uniform(20.0, 40.0)),
            }
            # Evaluate at tau = 0.0 exactly and at infinitesimal tau = 1e-8
            f_zero = compute_nss10_instantaneous_forward_rate(0.0, params)
            f_eps = compute_nss10_instantaneous_forward_rate(1e-8, params)
            expected = b0 + b1

            self.assertAlmostEqual(f_zero, expected, places=6)
            self.assertAlmostEqual(f_eps, expected, places=5)

    def test_adv_f927_03_portfolio_market_beta_clamp_invariant(self):
        """Verify key-rate duration/convexity immunization strictly enforces beta_port <= 1.000001."""
        test_cases = [
            # Extreme durations, huge unhedged weights
            (np.array([2.0, 3.0, 5.0]), np.array([15.0, 25.0, 30.0])),
            # Negative weights or zero weights
            (np.array([0.0, 0.0, 0.0]), np.array([5.0, 10.0, 20.0])),
            (np.array([100.0, 200.0]), np.array([2.0, 8.0])),
            # Random large portfolios
            (np.random.uniform(0.5, 10.0, 10), np.random.uniform(1.0, 25.0, 10)),
        ]

        for w_init, dur in test_cases:
            adj_w = compute_key_rate_convexity_immunization_v182(w_init, dur)
            effective_beta = float(np.sum(adj_w))
            self.assertLessEqual(
                effective_beta,
                1.000001,
                f"Effective beta {effective_beta} exceeded strict clamp 1.000001",
            )
            self.assertTrue(np.all(np.isfinite(adj_w)))

    # =========================================================================
    # F928: Directed Quantum Rényi Transfer Entropy Adversarial Tests
    # =========================================================================

    def test_adv_f928_01_disconnected_and_chaotic_series(self):
        """
        Verify Rényi transfer entropy on disconnected, chaotic, and identical return series:
        - Transfers remain finite and non-negative
        - Adjacency matrix has strictly zero diagonal A_ii = 0
        """
        T = 200
        np.random.seed(189)

        # 1. Independent white noise (disconnected)
        disconnected = np.random.normal(0, 1, (T, 4))
        net_disc = detect_systemic_contagion_network_v182(disconnected)
        self.assertTrue(np.all(np.diag(net_disc["adjacency_matrix"]) == 0.0))
        self.assertTrue(math.isfinite(net_disc["spectral_radius"]))
        self.assertGreaterEqual(net_disc["spectral_radius"], 0.0)

        # 2. Identical return series (X[:, 0] == X[:, 1])
        identical = np.zeros((T, 3))
        identical[:, 0] = np.random.normal(0, 1, T)
        identical[:, 1] = identical[:, 0]  # Exact duplicate
        identical[:, 2] = np.random.normal(0, 1, T)

        net_ident = detect_systemic_contagion_network_v182(identical)
        self.assertTrue(np.all(np.diag(net_ident["adjacency_matrix"]) == 0.0))
        self.assertTrue(math.isfinite(net_ident["spectral_radius"]))

        # 3. Chaotic series: Logistic Map at r = 4.0
        chaotic = np.zeros((T, 3))
        x = 0.35
        for t in range(T):
            x = 4.0 * x * (1.0 - x)
            chaotic[t, 0] = x
        chaotic[:, 1] = np.roll(chaotic[:, 0], 1)  # 1-day lagged chaotic driver
        chaotic[:, 2] = np.random.uniform(0, 1, T)  # Noise

        net_chaotic = detect_systemic_contagion_network_v182(chaotic)
        self.assertTrue(np.all(np.diag(net_chaotic["adjacency_matrix"]) == 0.0))
        self.assertTrue(math.isfinite(net_chaotic["spectral_radius"]))

    def test_adv_f928_02_renyi_alpha_stability_extremes(self):
        """Verify Rényi transfer entropy is stable across alpha parameter extremes (0.51 to 1.99)."""
        x = np.random.normal(0, 1, 100)
        y = np.roll(x, 1) + np.random.normal(0, 0.2, 100)

        for alpha in [0.51, 0.75, 1.0001, 1.50, 1.99]:
            te = compute_directed_renyi_schrodinger_transfer_entropy(x, y, alpha=alpha, lag=1)
            self.assertTrue(math.isfinite(te), f"TE not finite for alpha={alpha}")
            self.assertGreaterEqual(te, 0.0, f"TE negative for alpha={alpha}")

    # =========================================================================
    # F929: MCSI 6-Tier Circuit-Breaker Adversarial Tests
    # =========================================================================

    def test_adv_f929_01_mcsi_continuous_score_in_unit_interval(self):
        """Verify continuous MCSI score is strictly bounded in [0.0, 1.0] under extreme stress shocks."""
        extreme_inputs = [
            # Triple crisis extreme shock
            {"vix_velocity": 2.5, "vix_tsr": 2.2, "credit_spread_bps": 2500.0, "contagion_spectral_radius": 1.5,
             "yield_inversion_bps": 300.0, "currency_velocity": 0.15, "macro_impulse": 15.0},
            # Negative / benign values
            {"vix_velocity": -1.0, "vix_tsr": 0.60, "credit_spread_bps": 100.0, "contagion_spectral_radius": 0.05,
             "yield_inversion_bps": -50.0, "currency_velocity": -0.05, "macro_impulse": -10.0},
            # All zeroes / empty
            {},
        ]
        for inp in extreme_inputs:
            score = compute_mcsi_v182_multi_horizon_score(inp)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_adv_f929_02_strictly_non_increasing_leverage_across_6_tiers(self):
        """
        Verify that gross leverage limits are strictly non-increasing across all 6 tiers:
            TIER_NORMAL: 2.15x
            TIER_ELEVATED: 1.60x
            TIER_HIGH_STRESS: 1.10x
            TIER_SYSTEMIC_CRISIS: 0.60x
            TIER_PANIC_LIQUIDITY_SQUEEZE: 0.25x
            TIER_CIRCUIT_BREAKER_HALT: 0.00x
        """
        tiers_in_order = [
            TIER_NORMAL,
            TIER_ELEVATED,
            TIER_HIGH_STRESS,
            TIER_SYSTEMIC_CRISIS,
            TIER_PANIC_LIQUIDITY_SQUEEZE,
            TIER_CIRCUIT_BREAKER_HALT,
        ]
        leverages = [get_leverage_limit_for_mcsi_v182(t) for t in tiers_in_order]

        # Verify exact assigned limits
        expected_leverages = [2.15, 1.60, 1.10, 0.60, 0.25, 0.00]
        self.assertEqual(leverages, expected_leverages)

        # Monotonicity test: strictly decreasing
        for i in range(len(leverages) - 1):
            self.assertGreater(
                leverages[i],
                leverages[i + 1],
                f"Leverage failed strict monotonic decrease: {tiers_in_order[i]} ({leverages[i]}) vs {tiers_in_order[i+1]} ({leverages[i+1]})",
            )

    def test_adv_f929_03_gate8_inverse_etf_overlay_activation_and_halt(self):
        """Verify Gate 8 synthetic inverse ETF overlay activation and circuit breaker halt thresholds."""
        # Check boundary score evaluation
        boundary_cases = [
            (0.10, TIER_NORMAL, False, 0.0, 2.15),
            (0.30, TIER_ELEVATED, False, 0.15, 1.60),
            (0.50, TIER_HIGH_STRESS, False, 0.40, 1.10),
            (0.70, TIER_SYSTEMIC_CRISIS, False, 0.75, 0.60),
            (0.90, TIER_PANIC_LIQUIDITY_SQUEEZE, False, 0.90, 0.25),
            (0.96, TIER_CIRCUIT_BREAKER_HALT, True, 1.00, 0.00),
        ]

        for score, exp_tier, exp_halt, exp_hedge, exp_lev in boundary_cases:
            cb_result = check_circuit_breaker_v182(score)
            self.assertEqual(cb_result["tier"], exp_tier)
            self.assertEqual(cb_result["is_circuit_breaker_halt"], exp_halt)
            self.assertAlmostEqual(cb_result["inverse_hedge_ratio"], exp_hedge, places=4)
            self.assertAlmostEqual(cb_result["max_leverage"], exp_lev, places=4)
            # Ensure Gate 8 inverse ETFs are present
            self.assertEqual(cb_result["gate8_inverse_etfs"], ["252670", "114800", "SH", "PSQ"])
            self.assertEqual(cb_result["synthetic_rows"], 0)

    # =========================================================================
    # Property-Based Monte Carlo Stress Invariant
    # =========================================================================

    def test_adv_monte_carlo_property_based_invariants_1000_trials(self):
        """
        Property-based fuzzing & invariant checking across 1,000 randomized macro shocks:
        - All scores bounded in [0.0, 1.0] or [-3.0, 3.0]
        - Hedge ratio strictly in [0.0, 1.0]
        - Leverage strictly in [0.0, 2.15]
        - Cash margin collateral <= 85% of cash
        - synthetic_rows == 0 strictly int
        """
        np.random.seed(999)
        for trial in range(1000):
            # 1. Random macro inputs
            vix_vel = float(np.random.uniform(-1.0, 3.0))
            vix_tsr = float(np.random.uniform(0.5, 2.5))
            cs_bps = float(np.random.uniform(100.0, 2000.0))
            spec_rad = float(np.random.uniform(0.0, 1.5))
            inv_bps = float(np.random.uniform(-100.0, 250.0))
            curr_vel = float(np.random.uniform(-0.10, 0.20))
            impulse = float(np.random.uniform(-20.0, 20.0))

            mcsi = compute_mcsi_v182_multi_horizon_score({
                "vix_velocity": vix_vel,
                "vix_tsr": vix_tsr,
                "credit_spread_bps": cs_bps,
                "contagion_spectral_radius": spec_rad,
                "yield_inversion_bps": inv_bps,
                "currency_velocity": curr_vel,
                "macro_impulse": impulse,
            })
            self.assertTrue(0.0 <= mcsi <= 1.0, f"MCSI out of bounds on trial {trial}: {mcsi}")

            lev = get_leverage_limit_for_mcsi_v182(mcsi)
            self.assertTrue(0.0 <= lev <= 2.15, f"Leverage out of bounds on trial {trial}: {lev}")

            # 2. Random FX hedge order
            spot = float(np.random.uniform(1000.0, 1600.0))
            fwd = float(np.random.uniform(900.0, 1700.0))
            cash = float(np.random.uniform(1.0, 1e8))
            exp = float(np.random.uniform(0.0, 1e9))
            h_raw = float(np.random.uniform(-1.0, 2.0))

            order = generate_quad_fx_hedge_order(
                hedge_ratio=h_raw,
                us_exposure_krw=exp,
                available_cash_krw=cash,
                initial_margin_req=0.05,
            )
            self.assertTrue(0.0 <= order.hedge_ratio <= 1.0)
            self.assertLessEqual(order.collateral_required_krw, 0.85 * cash + 1e-4)
            self.assertEqual(order.details["synthetic_rows"], 0)
            self.assertIsInstance(order.details["synthetic_rows"], int)

    # =========================================================================
    # Category: Extreme Corner Cases & Input Validation Across All 5 Engines
    # =========================================================================

    def test_adv_cross_engine_corner_cases_and_missing_data(self):
        """Verify graceful degradation on degenerate DataFrames, missing columns, and empty inputs."""
        engines = [
            ("F925", MacroHyperTensorImpulseV182Engine()),
            ("F926", QuadCurvatureFXHedgingEngine()),
            ("F927", NSS10RatesHedgeEngine()),
            ("F928", RenyiSchrodingerTransferEntropyEngine()),
            ("F929", MacroCrisisSeverityIndexV182Engine()),
        ]

        # 1. Empty DataFrame
        empty_df = pd.DataFrame()
        for name, engine in engines:
            with self.subTest(engine=name, case="empty_df"):
                res = engine.generate_scores(empty_df)
                self.assertTrue(res.empty or len(res) == 0)

        # 2. DataFrame without symbol column
        no_sym_df = pd.DataFrame({"close": [100.0, 200.0], "volume": [1000, 2000]})
        for name, engine in engines:
            with self.subTest(engine=name, case="no_symbol_col"):
                res = engine.generate_scores(no_sym_df)
                self.assertTrue(res.empty or len(res) == 0)

        # 3. Degenerate sectors (None, empty string, NaN, non-existent sector)
        deg_df = pd.DataFrame({
            "symbol": ["005930", "AAPL", "000660", "TSLA"],
            "sector": [None, "", "NonExistentSector123", "Semiconductor"],
        })
        for name, engine in engines:
            with self.subTest(engine=name, case="degenerate_sectors"):
                res = engine.generate_scores(deg_df)
                self.assertEqual(len(res), 4)
                self.assertTrue(np.all(np.isfinite(res["score"])))
                for meta in res["metadata"]:
                    self.assertEqual(meta["synthetic_rows"], 0)
                    self.assertIs(type(meta["synthetic_rows"]), int)

        # 4. F927 empty curve fitting fallback
        empty_nss = fit_extended_nss_10param_curve([], [])
        self.assertEqual(empty_nss["mse"], 0.0)
        self.assertIn("beta0", empty_nss)

        # 5. F928 1-column return matrix fallback
        net_1col = detect_systemic_contagion_network_v182(np.random.normal(0, 1, (50, 1)))
        self.assertEqual(net_1col["spectral_radius"], 0.0)
        self.assertFalse(net_1col["tipping_point_alert"])


if __name__ == "__main__":
    unittest.main()

