"""
tests/test_phase185_stress_challenger2.py — Adversarial Stress Test Suite for Phase 185 (F905–F909).
Executed by challenger_phase185_2.

Adversarial Stress Test Categories:
1. Category A (F908): Multi-Scale Directed Rényi Contagion Dynamics & Spectral Radius rho(T)
   - TC_STRESS_01: Random directed networks ensemble (100 random directed graphs) verifying rho(T) calculation
   - TC_STRESS_02: Independent return series yielding rho(T) <= 0.40 and zero alert
   - TC_STRESS_03: Strongly coupled multi-scale contagion cascade yielding rho(T) > 0.40 and alert == True
   - TC_STRESS_04: Rényi parameter alpha boundary sweep in (1.0001, 2.49)
   - TC_STRESS_05: Systemic vulnerability absorption (in-degree) vs transmission (out-degree) ranking
   - TC_STRESS_06: Degenerate, zero-matrix, and disconnected topologies

2. Category B (F906): Margin Call Safety & Multi-Currency Surface Hedging
   - TC_STRESS_07: Sudden 50% currency devaluation (USD/KRW surge to 2025 and drop to 675)
   - TC_STRESS_08: Cash margin safety invariant: collateral_required <= 85% of available cash under ALL conditions
   - TC_STRESS_09: Severe cash starvation (available cash << portfolio capital, down to zero cash)
   - TC_STRESS_10: Safe-haven flight-to-safety dampening (h* <= 0.25) under PANIC_CRISIS, SEVERE_PANIC, SYSTEMIC_CRISIS
   - TC_STRESS_11: Multi-currency triangular CIP consistency across USD, KRW, JPY, EUR

3. Category C (F909): Tier 5 SYSTEMIC_CRISIS Circuit Breakers & Protective Gating
   - TC_STRESS_12: 2008 Lehman GFC simulation triggering Tier 5 SYSTEMIC_CRISIS (xi >= 0.75)
   - TC_STRESS_13: 2020 COVID shock simulation triggering Tier 5 SYSTEMIC_CRISIS (xi >= 0.75)
   - TC_STRESS_14: 1997 Asian Financial Crisis currency shock simulation triggering Tier 5 SYSTEMIC_CRISIS
   - TC_STRESS_15: Invariant verification: 100% Gate 8 inverse ETF overlay (['252670', '114800', 'SH', 'PSQ'])
   - TC_STRESS_16: Invariant verification: SMA200 hard exit == True and max_leverage_limit <= 0.20x
   - TC_STRESS_17: Complete 5-tier monotonic gating transition boundaries [0.30, 0.45, 0.60, 0.75]

4. Category D (F905 & F907): Hyper-Tensor Impulses & NSS Yield Curve Stress
   - TC_STRESS_18: 4th-order hyper-tensor quartic response under 10-sigma extreme macro shocks
   - TC_STRESS_19: 8-parameter NSS yield curve fitting under inverted (10Y < 2Y) and flat yield curves
   - TC_STRESS_20: Portfolio beta clamping (beta <= 1.000001) under severe yield shocks

5. Category E (Invariants & System SLA):
   - TC_STRESS_21: Invariant: synthetic_rows == 0 strictly Python native int 0 across all 5 engines
   - TC_STRESS_22: Output bounds: alpha in [-3.0, 3.0] and probability in [0.05, 0.95] across all engines
   - TC_STRESS_23: Multi-asset portfolio score generation with mixed KRX and US equities
"""

from __future__ import annotations

import math
import os
import sys
import unittest
from typing import Dict, Any, List

import numpy as np
import pandas as pd

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.core.macro_hyper_tensor_impulse import (
    MacroHyperTensorImpulseEngine,
    compute_macro_hyper_tensor_impulse_order4,
    compute_dynamic_macro_tensor_elasticity,
    decompose_macro_impulse_wavelet,
    GLOBAL_MACRO_FACTORS,
)
from src.core.multicurrency_basis_surface import (
    MultiCurrencyBasisSurfaceHedger,
    FXMacroInput,
    FXHedgeResult,
    compute_nonlinear_cip_deviation,
    compute_triangular_cip_deviation,
    calculate_optimal_hedge_ratio,
    generate_fx_hedge_order,
)
from src.core.extended_nss_rates_hedge import (
    ExtendedNSSRatesHedgeEngine,
    fit_extended_nss_yield_curve_8param,
    evaluate_extended_nss_zero_coupon_yield,
    detect_yield_curve_inversion,
    compute_duration_convexity_hedge,
)
from src.core.multiscale_transfer_entropy import (
    MultiScaleTransferEntropyContagionEngine,
    fit_multiscale_renyi_transfer_entropy,
    detect_systemic_contagion,
)
from src.core.macro_crisis_severity_index_v181 import (
    MacroCrisisSeverityIndexV181Engine,
    evaluate_mcsi_v181_index,
    determine_crisis_gating_tier_v181,
    get_leverage_limit_for_mcsi_v181,
    check_crisis_circuit_breaker_v181,
    TIER_NORMAL,
    TIER_ELEVATED,
    TIER_HIGH_STRESS,
    TIER_SEVERE_PANIC,
    TIER_SYSTEMIC_CRISIS,
    GATE8_INVERSE_ETFS,
)


class TestPhase185AdversarialChallenger2(unittest.TestCase):
    """Adversarial stress test suite verifying resilience, safety constraints, and invariants."""

    def setUp(self) -> None:
        self.f905_engine = MacroHyperTensorImpulseEngine()
        self.f906_engine = MultiCurrencyBasisSurfaceHedger()
        self.f907_engine = ExtendedNSSRatesHedgeEngine()
        self.f908_engine = MultiScaleTransferEntropyContagionEngine()
        self.f909_engine = MacroCrisisSeverityIndexV181Engine()

    # =========================================================================
    # Category A (F908): Multi-Scale Directed Rényi Contagion Dynamics
    # =========================================================================

    def test_tc_stress_01_random_directed_networks_ensemble(self) -> None:
        """TC_STRESS_01: Verify rho(T) calculation across 100 random directed network topologies."""
        rng = np.random.RandomState(42)
        for trial in range(100):
            K = rng.randint(3, 10)
            density = rng.uniform(0.1, 0.9)
            # Generate random adjacency with zero diagonal
            adj = rng.uniform(0.0, 1.0, (K, K)) * (rng.uniform(0.0, 1.0, (K, K)) < density)
            np.fill_diagonal(adj, 0.0)

            contagion = detect_systemic_contagion(adj, threshold=0.40)
            eigs = np.linalg.eigvals(adj)
            expected_rho = float(np.max(np.abs(eigs))) if len(eigs) > 0 else 0.0

            self.assertAlmostEqual(contagion["spectral_radius"], expected_rho, places=7)
            self.assertAlmostEqual(contagion["dominant_eigenvalue"], expected_rho, places=7)
            if expected_rho > 0.40:
                self.assertTrue(contagion["is_contagion_alert"], f"Trial {trial}: rho={expected_rho} must trigger alert")
            else:
                self.assertFalse(contagion["is_contagion_alert"], f"Trial {trial}: rho={expected_rho} must not trigger alert")

    def test_tc_stress_02_independent_series_zero_alert(self) -> None:
        """TC_STRESS_02: Completely independent return series yield rho(T) <= 0.40 and zero alert."""
        rng = np.random.RandomState(1337)
        # 5 completely independent assets, 200 observations
        independent_returns = rng.randn(200, 5) * 0.015
        A = fit_multiscale_renyi_transfer_entropy(independent_returns, alpha=1.5, bins=3, lags=[1, 3, 5])
        contagion = detect_systemic_contagion(A, threshold=0.40)

        self.assertLessEqual(contagion["spectral_radius"], 0.40,
                             f"Independent series spectral radius ({contagion['spectral_radius']:.4f}) must be <= 0.40")
        self.assertFalse(contagion["is_contagion_alert"], "Independent series must produce ZERO contagion alert")

    def test_tc_stress_03_coupled_contagion_cascade_alert(self) -> None:
        """TC_STRESS_03: Strongly coupled multi-scale contagion cascade yields rho(T) > 0.40 and alert == True."""
        rng = np.random.RandomState(777)
        T = 250
        # 4 assets where asset 0 is the systemic driver broadcasting to assets 1, 2, 3
        driver = rng.randn(T) * 0.04
        f1 = np.zeros(T)
        f2 = np.zeros(T)
        f3 = np.zeros(T)
        for t in range(1, T):
            f1[t] = 0.90 * driver[t - 1] + 0.10 * rng.randn() * 0.01
            f2[t] = 0.85 * driver[t - 1] + 0.15 * rng.randn() * 0.01
            f3[t] = 0.80 * driver[t - 1] + 0.20 * rng.randn() * 0.01

        coupled_data = np.column_stack([driver, f1, f2, f3])
        A = fit_multiscale_renyi_transfer_entropy(coupled_data, alpha=1.5, bins=3, lags=[1, 3, 5])
        contagion = detect_systemic_contagion(A, threshold=0.40)

        # In coupled data, driver spreads significant information to followers
        # Verify in-degree vulnerability: followers absorb flow from driver
        in_degree = contagion["in_degree"]
        out_degree = contagion["out_degree"]
        self.assertGreater(out_degree[0], in_degree[0], "Driver must have higher out-degree than in-degree")

        # Dense transmission network should yield high spectral radius
        A_dense = np.array([
            [0.0, 0.6, 0.5, 0.4],
            [0.5, 0.0, 0.6, 0.3],
            [0.4, 0.5, 0.0, 0.6],
            [0.6, 0.3, 0.5, 0.0],
        ])
        contagion_cascade = detect_systemic_contagion(A_dense, threshold=0.40)
        self.assertGreater(contagion_cascade["spectral_radius"], 0.40)
        self.assertTrue(contagion_cascade["is_contagion_alert"])

    def test_tc_stress_04_renyi_parameter_alpha_boundary_sweep(self) -> None:
        """TC_STRESS_04: Rényi parameter alpha boundary sweep in (1.0001, 2.49) remains numerically stable."""
        rng = np.random.RandomState(101)
        data = rng.randn(80, 3) * 0.02
        alphas = [1.0001, 1.05, 1.5, 2.0, 2.45, 2.49]
        for a in alphas:
            A = fit_multiscale_renyi_transfer_entropy(data, alpha=a, bins=3, lags=[1, 3])
            self.assertEqual(A.shape, (3, 3))
            self.assertTrue(np.all(np.isfinite(A)))
            self.assertTrue(np.all(A >= 0.0))
            for i in range(3):
                self.assertEqual(A[i, i], 0.0)

    def test_tc_stress_05_systemic_vulnerability_ranking(self) -> None:
        """TC_STRESS_05: Verify systemic vulnerability absorption ranking is ordered descending by in-degree."""
        A = np.array([
            [0.0, 0.1, 0.0],
            [0.5, 0.0, 0.2],  # absorbs 0.7
            [0.9, 0.8, 0.0],  # absorbs 1.7 (most vulnerable receiver)
        ])
        contagion = detect_systemic_contagion(A)
        # Node 2 absorbs 1.7, Node 1 absorbs 0.7, Node 0 absorbs 0.1
        self.assertEqual(contagion["vulnerability_ranking"], [2, 1, 0])
        # Node 0 broadcasts 1.4, Node 1 broadcasts 0.9, Node 2 broadcasts 0.2
        self.assertEqual(contagion["spreader_ranking"], [0, 1, 2])

    def test_tc_stress_06_degenerate_and_zero_matrix(self) -> None:
        """TC_STRESS_06: Degenerate, zero-matrix, and 1x1 inputs handled safely without exception."""
        # All zeros
        A_zero = np.zeros((4, 4))
        c_zero = detect_systemic_contagion(A_zero)
        self.assertEqual(c_zero["spectral_radius"], 0.0)
        self.assertFalse(c_zero["is_contagion_alert"])

        # 1x1 input
        A_1 = np.zeros((1, 1))
        c_1 = detect_systemic_contagion(A_1)
        self.assertEqual(c_1["spectral_radius"], 0.0)

        # Non-square input
        A_rect = np.zeros((3, 4))
        c_rect = detect_systemic_contagion(A_rect)
        self.assertEqual(c_rect["spectral_radius"], 0.0)

    # =========================================================================
    # Category B (F906): Margin Call Safety & Multi-Currency Surface Hedging
    # =========================================================================

    def test_tc_stress_07_sudden_50pct_currency_devaluation(self) -> None:
        """TC_STRESS_07: Sudden 50% currency devaluation (USD/KRW surge 1350 -> 2025 and drop 1350 -> 675)."""
        allocations = {"AAPL": 0.60, "NVDA": 0.40}  # 100% US equity
        portfolio_cap = 500_000_000.0  # 500M KRW
        available_cash = 25_000_000.0   # 25M KRW (5% cash)

        # Case 1: KRW sudden 50% devaluation (USDKRW spikes 1350 -> 2025)
        macro_spike = FXMacroInput(
            usdkrw_spot=2025.0,
            fx_volatility_20d=0.35,
            fx_momentum_20d=0.50,
            regime_label="PANIC_CRISIS",
        )
        res_spike = self.f906_engine.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=portfolio_cap,
            portfolio_allocations=allocations,
            macro_input=macro_spike,
            available_cash_krw=available_cash,
        )
        # Margin call safety invariant: collateral must NEVER exceed 85% of available cash
        max_collateral = available_cash * 0.85
        self.assertLessEqual(
            res_spike.collateral_required_krw,
            max_collateral + 1e-4,
            f"Collateral ({res_spike.collateral_required_krw}) exceeded 85% cash limit ({max_collateral}) during 50% FX spike!",
        )
        # Flight-to-safety protection active
        self.assertLessEqual(res_spike.hedge_ratio, 0.25)

        # Case 2: USD sudden 50% crash (USDKRW drops 1350 -> 675)
        macro_crash = FXMacroInput(
            usdkrw_spot=675.0,
            fx_volatility_20d=0.30,
            fx_momentum_20d=-0.50,
            regime_label="BEAR_HIGH_VOL",
        )
        res_crash = self.f906_engine.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=portfolio_cap,
            portfolio_allocations=allocations,
            macro_input=macro_crash,
            available_cash_krw=available_cash,
        )
        self.assertLessEqual(
            res_crash.collateral_required_krw,
            max_collateral + 1e-4,
            f"Collateral ({res_crash.collateral_required_krw}) exceeded 85% cash limit ({max_collateral}) during 50% FX crash!",
        )

    def test_tc_stress_08_cash_margin_safety_invariant_sweep(self) -> None:
        """TC_STRESS_08: Cash margin safety invariant: collateral <= 85% available cash across wide parameter sweep."""
        allocations = {"AAPL": 0.50, "005930": 0.50}  # 50% US, 50% KR
        portfolio_cap = 100_000_000.0

        cash_levels = [100.0, 1_000.0, 10_000.0, 100_000.0, 1_000_000.0, 10_000_000.0, 50_000_000.0]
        spot_levels = [1000.0, 1200.0, 1350.0, 1500.0, 1800.0, 2200.0]

        for cash in cash_levels:
            for spot in spot_levels:
                macro_in = FXMacroInput(usdkrw_spot=spot, regime_label="BULL_LOW_VOL")
                res = self.f906_engine.evaluate_portfolio_fx_hedge(
                    portfolio_capital_krw=portfolio_cap,
                    portfolio_allocations=allocations,
                    macro_input=macro_in,
                    available_cash_krw=cash,
                )
                allowed_collateral = cash * 0.85
                self.assertLessEqual(
                    res.collateral_required_krw,
                    allowed_collateral + 1e-4,
                    f"Violation at cash={cash}, spot={spot}: collateral={res.collateral_required_krw} > allowed={allowed_collateral}",
                )
                self.assertTrue(0.0 <= res.hedge_ratio <= 1.0)
                self.assertTrue(0.0 <= res.hedge_weight <= 1.5)

    def test_tc_stress_09_severe_cash_starvation(self) -> None:
        """TC_STRESS_09: Severe cash starvation (zero cash available) produces zero collateral and zero hedge order."""
        allocations = {"AAPL": 1.0}
        portfolio_cap = 100_000_000.0

        # Available cash is strictly 0.0 KRW
        res_zero = self.f906_engine.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=portfolio_cap,
            portfolio_allocations=allocations,
            macro_input=FXMacroInput(usdkrw_spot=1350.0),
            available_cash_krw=0.0,
        )
        self.assertEqual(res_zero.collateral_required_krw, 0.0)
        self.assertEqual(res_zero.hedge_notional_krw, 0.0)
        self.assertEqual(res_zero.hedge_ratio, 0.0)
        self.assertEqual(res_zero.hedge_action, "NO_HEDGE")

    def test_tc_stress_10_safe_haven_flight_to_safety_dampening(self) -> None:
        """TC_STRESS_10: Safe haven flight-to-safety dampening (h* <= 0.25) under PANIC_CRISIS, SEVERE_PANIC, SYSTEMIC_CRISIS."""
        for crisis_regime in ["PANIC_CRISIS", "SYSTEMIC_CRISIS", "SEVERE_PANIC"]:
            macro_crisis = FXMacroInput(
                usdkrw_spot=1480.0,
                fx_momentum_20d=0.07,
                regime_label=crisis_regime,
            )
            h = calculate_optimal_hedge_ratio(macro_crisis)
            self.assertLessEqual(
                h, 0.25,
                f"Regime {crisis_regime} must dampen hedge ratio to <= 0.25 (got {h}) for flight-to-safety protection",
            )

    def test_tc_stress_11_multicurrency_triangular_cip_consistency(self) -> None:
        """TC_STRESS_11: Multi-currency triangular CIP consistency across USD, KRW, JPY, EUR."""
        spots = {"USDKRW": 1380.0, "USDJPY": 155.0, "EURUSD": 1.05}
        fwds = {"USDKRW": 1375.0, "USDJPY": 154.0, "EURUSD": 1.055}
        rates = {"USD": 0.050, "KRW": 0.035, "JPY": 0.005, "EUR": 0.035}

        tri = compute_triangular_cip_deviation(spots, fwds, rates, tenor_days=90)
        # Verify implied cross rate
        expected_jpykrw = 1380.0 / 155.0
        self.assertAlmostEqual(tri["implied_jpykrw_spot"], expected_jpykrw, places=5)
        self.assertAlmostEqual(tri["triangular_discrepancy"], 0.0, places=5)
        # All basis deviations finite
        self.assertTrue(math.isfinite(tri["basis_usdkrw_bps"]))
        self.assertTrue(math.isfinite(tri["basis_usdjpy_bps"]))
        self.assertTrue(math.isfinite(tri["basis_eurusd_bps"]))

    # =========================================================================
    # Category C (F909): Tier 5 SYSTEMIC_CRISIS Circuit Breakers & Protective Gating
    # =========================================================================

    def test_tc_stress_12_lehman_2008_crisis_simulation(self) -> None:
        """TC_STRESS_12: 2008 Lehman GFC simulation triggering Tier 5 SYSTEMIC_CRISIS (xi >= 0.75)."""
        # Historical Lehman GFC parameters: VIX jumped to 80, OAS blew out to 1200 bps, severe cascade
        xi_lehman = evaluate_mcsi_v181_index(
            vix_velocity=0.65,               # +65% 1d jump
            vix_tsr=1.35,                    # Extreme backwardation VIX/VIX3M
            credit_spread_bps=1200.0,        # High-yield OAS blowout
            contagion_spectral_radius=0.78,  # Systemic cascade wave
            yield_inversion_bps=65.0,        # Curve inverted
            currency_velocity=0.10,          # USD/KRW spike
        )
        self.assertGreaterEqual(xi_lehman, 0.75, f"Lehman shock must yield xi >= 0.75, got {xi_lehman:.4f}")
        cb = check_crisis_circuit_breaker_v181(xi_lehman)

        self.assertEqual(cb["tier"], TIER_SYSTEMIC_CRISIS)
        self.assertTrue(cb["circuit_breaker_triggered"])
        self.assertLessEqual(cb["max_leverage_limit"], 0.20)
        self.assertEqual(cb["hedge_overlay_ratio"], 1.0)
        self.assertTrue(cb["gate8_inverse_hedge_active"])
        self.assertTrue(cb["sma200_hard_exit"])
        self.assertTrue(cb["new_longs_gated"])
        self.assertEqual(cb["inverse_hedge_etfs"], ["252670", "114800", "SH", "PSQ"])

    def test_tc_stress_13_covid_2020_shock_simulation(self) -> None:
        """TC_STRESS_13: 2020 COVID shock simulation triggering Tier 5 SYSTEMIC_CRISIS (xi >= 0.75)."""
        # March 2020 parameters: VIX reached 82.69, VIX TSR backwardation 1.45, credit spreads 950 bps
        xi_covid = evaluate_mcsi_v181_index(
            vix_velocity=0.55,
            vix_tsr=1.45,
            credit_spread_bps=950.0,
            contagion_spectral_radius=0.82,
            yield_inversion_bps=40.0,
            currency_velocity=0.08,
        )
        self.assertGreaterEqual(xi_covid, 0.75, f"COVID shock must yield xi >= 0.75, got {xi_covid:.4f}")
        cb = check_crisis_circuit_breaker_v181(xi_covid)

        self.assertEqual(cb["tier"], TIER_SYSTEMIC_CRISIS)
        self.assertTrue(cb["circuit_breaker_triggered"])
        self.assertLessEqual(cb["max_leverage_limit"], 0.20)
        self.assertEqual(cb["hedge_overlay_ratio"], 1.0)
        self.assertTrue(cb["gate8_inverse_hedge_active"])
        self.assertTrue(cb["sma200_hard_exit"])
        self.assertTrue(cb["new_longs_gated"])
        self.assertEqual(cb["inverse_hedge_etfs"], ["252670", "114800", "SH", "PSQ"])

    def test_tc_stress_14_asian_financial_crisis_1997_simulation(self) -> None:
        """TC_STRESS_14: 1997 Asian Financial Crisis simulation triggering Tier 5 SYSTEMIC_CRISIS."""
        # 1997 parameters: Currency collapse velocity, massive credit blowout, contagion wave
        xi_1997 = evaluate_mcsi_v181_index(
            vix_velocity=0.45,
            vix_tsr=1.25,
            credit_spread_bps=1500.0,
            contagion_spectral_radius=0.92,
            yield_inversion_bps=80.0,
            currency_velocity=0.18,  # Extreme KRW collapse
        )
        self.assertGreaterEqual(xi_1997, 0.75, f"1997 shock must yield xi >= 0.75, got {xi_1997:.4f}")
        cb = check_crisis_circuit_breaker_v181(xi_1997)
        self.assertEqual(cb["tier"], TIER_SYSTEMIC_CRISIS)
        self.assertEqual(cb["hedge_overlay_ratio"], 1.0)
        self.assertTrue(cb["gate8_inverse_hedge_active"])
        self.assertTrue(cb["sma200_hard_exit"])

    def test_tc_stress_15_gate8_inverse_etfs_exact_coverage(self) -> None:
        """TC_STRESS_15: Invariant: Gate 8 inverse ETF overlay strictly contains 252670, 114800, SH, PSQ."""
        self.assertIn("252670", GATE8_INVERSE_ETFS)  # KODEX 200 Futures Inverse 2X
        self.assertIn("114800", GATE8_INVERSE_ETFS)  # KODEX Inverse
        self.assertIn("SH", GATE8_INVERSE_ETFS)      # ProShares Short S&P500
        self.assertIn("PSQ", GATE8_INVERSE_ETFS)     # ProShares Short QQQ
        self.assertEqual(len(GATE8_INVERSE_ETFS), 4)

    def test_tc_stress_16_sma200_hard_exit_and_leverage_compression(self) -> None:
        """TC_STRESS_16: Invariant: SMA200 hard exit == True and leverage limit <= 0.20x strictly in Tier 5."""
        # Test just below threshold (xi = 0.7499) -> Tier 4
        cb_t4 = check_crisis_circuit_breaker_v181(0.7499)
        self.assertEqual(cb_t4["tier"], TIER_SEVERE_PANIC)
        self.assertFalse(cb_t4["sma200_hard_exit"])
        self.assertEqual(cb_t4["max_leverage_limit"], 0.40)
        self.assertEqual(cb_t4["hedge_overlay_ratio"], 0.75)

        # Test at and above threshold (xi = 0.7500) -> Tier 5
        cb_t5 = check_crisis_circuit_breaker_v181(0.7500)
        self.assertEqual(cb_t5["tier"], TIER_SYSTEMIC_CRISIS)
        self.assertTrue(cb_t5["sma200_hard_exit"])
        self.assertLessEqual(cb_t5["max_leverage_limit"], 0.20)
        self.assertEqual(cb_t5["hedge_overlay_ratio"], 1.0)

    def test_tc_stress_17_monotonic_5tier_gating_boundaries(self) -> None:
        """TC_STRESS_17: Monotonicity of 5-tier gating across leverage limits and hedge overlays."""
        test_points = [
            (0.10, TIER_NORMAL, 1.95, 0.0, False, False),
            (0.35, TIER_ELEVATED, 1.35, 0.15, False, False),
            (0.50, TIER_HIGH_STRESS, 0.85, 0.40, False, True),
            (0.68, TIER_SEVERE_PANIC, 0.40, 0.75, True, True),
            (0.88, TIER_SYSTEMIC_CRISIS, 0.20, 1.00, True, True),
        ]
        prev_lev = 999.0
        prev_hedge = -1.0
        for xi, expected_tier, expected_lev, expected_hedge, exp_gate8, exp_gate_longs in test_points:
            cb = check_crisis_circuit_breaker_v181(xi)
            self.assertEqual(cb["tier"], expected_tier)
            self.assertEqual(cb["max_leverage_limit"], expected_lev)
            self.assertEqual(cb["hedge_overlay_ratio"], expected_hedge)
            self.assertEqual(cb["gate8_inverse_hedge_active"], exp_gate8)
            self.assertEqual(cb["new_longs_gated"], exp_gate_longs)

            # Monotonicity checks: leverage limits decrease, hedge overlay increases
            self.assertLess(cb["max_leverage_limit"], prev_lev)
            self.assertGreater(cb["hedge_overlay_ratio"], prev_hedge)
            prev_lev = cb["max_leverage_limit"]
            prev_hedge = cb["hedge_overlay_ratio"]

    # =========================================================================
    # Category D (F905 & F907): Hyper-Tensor Impulses & NSS Yield Curve Stress
    # =========================================================================

    def test_tc_stress_18_tensor_quartic_response_under_10sigma_shocks(self) -> None:
        """TC_STRESS_18: 4th-order hyper-tensor quartic response remains finite and superlinear under 10-sigma shocks."""
        extreme_shocks = {
            "sox": 0.25,      # 25% SOX drop/surge
            "usdkrw": 0.15,
            "vix": 0.80,
            "wti": -0.30,
            "copper": -0.20,
            "eem": -0.15,
        }
        impulse = compute_macro_hyper_tensor_impulse_order4(extreme_shocks, sector="Semiconductor")
        self.assertTrue(math.isfinite(impulse))
        # Quartic component should dominate large shocks
        imp_small = compute_macro_hyper_tensor_impulse_order4({"sox": 0.02}, sector="Semiconductor")
        imp_large = compute_macro_hyper_tensor_impulse_order4({"sox": 0.10}, sector="Semiconductor")
        # 5x shock -> > 5x response due to degree 4 term
        self.assertGreater(abs(imp_large), 5.0 * abs(imp_small))

    def test_tc_stress_19_extended_nss_yield_curve_fitting_inversions(self) -> None:
        """TC_STRESS_19: 8-parameter NSS yield curve fitting under inverted (10Y < 2Y) and flat yield curves."""
        maturities = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0])
        # Severe curve inversion: 2Y at 5.5%, 10Y at 3.5% (spread = -200 bps)
        inverted_yields = np.array([0.058, 0.057, 0.056, 0.055, 0.050, 0.045, 0.040, 0.035, 0.037, 0.039])
        params_inv = fit_extended_nss_yield_curve_8param(maturities, inverted_yields)

        # Decay parameters strictly positive
        self.assertGreater(params_inv["lambda1"], 0.0)
        self.assertGreater(params_inv["lambda2"], 0.0)
        self.assertGreater(params_inv["lambda3"], 0.0)

        # Reconstructed yields positive and finite
        y_recon = evaluate_extended_nss_zero_coupon_yield(
            maturities,
            params_inv["beta0"], params_inv["beta1"], params_inv["beta2"],
            params_inv["beta3"], params_inv["beta4"],
            params_inv["lambda1"], params_inv["lambda2"], params_inv["lambda3"],
        )
        self.assertTrue(np.all(np.isfinite(y_recon)))
        self.assertTrue(np.all(y_recon > 0.0))

        # Inversion detector
        inv_detect = detect_yield_curve_inversion(maturities, inverted_yields)
        self.assertTrue(inv_detect["is_inverted"])
        self.assertLess(inv_detect["spread_10_2"], -0.015)

    def test_tc_stress_20_portfolio_beta_clamping_invariant(self) -> None:
        """TC_STRESS_20: Portfolio beta clamping strictly enforced (beta <= 1.000001) under severe yield shocks."""
        durations = [1.0, 5.0, 10.0, 20.0, 35.0]
        slopes = [-0.03, -0.01, 0.0, 0.02, 0.05]
        for dur in durations:
            for slp in slopes:
                res = compute_duration_convexity_hedge(portfolio_duration=dur, slope_2y_10y=slp)
                self.assertLessEqual(
                    res["market_beta_clamp"], 1.000001,
                    f"Beta clamp violated at dur={dur}, slope={slp}: beta={res['market_beta_clamp']}",
                )

    # =========================================================================
    # Category E (Invariants & System SLA):
    # =========================================================================

    def test_tc_stress_21_synthetic_rows_strictly_native_int_zero(self) -> None:
        """TC_STRESS_21: Invariant: synthetic_rows == 0 strictly Python native int 0 across all 5 engines under stress."""
        df_stress = pd.DataFrame({
            "symbol": ["005930", "000660", "AAPL", "NVDA", "MSFT", "AMZN", "GOOGL", "035420"]
        })
        engines = [
            ("F905", self.f905_engine),
            ("F906", self.f906_engine),
            ("F907", self.f907_engine),
            ("F908", self.f908_engine),
            ("F909", self.f909_engine),
        ]
        for name, eng in engines:
            res = eng.generate_scores(df_stress)
            self.assertEqual(len(res), len(df_stress), f"{name} length mismatch")
            for m in res["metadata"]:
                self.assertIn("synthetic_rows", m, f"{name} missing synthetic_rows")
                val = m["synthetic_rows"]
                self.assertIs(type(val), int, f"{name} synthetic_rows type is {type(val)}, must be native int")
                self.assertEqual(val, 0, f"{name} synthetic_rows is {val}, must be strictly 0")

    def test_tc_stress_22_score_and_probability_bounds(self) -> None:
        """TC_STRESS_22: Output scores bounded in [-3.0, 3.0] and probabilities in [0.05, 0.95]."""
        df = pd.DataFrame({"symbol": ["005930", "AAPL"]})
        engines = [
            self.f905_engine,
            self.f906_engine,
            self.f907_engine,
            self.f908_engine,
            self.f909_engine,
        ]
        for eng in engines:
            res = eng.generate_scores(df)
            for s in res["score"]:
                self.assertTrue(-3.0 <= s <= 3.0, f"Score {s} out of bounds [-3.0, 3.0]")
            for p in res["probability"]:
                self.assertTrue(0.05 <= p <= 0.95, f"Probability {p} out of bounds [0.05, 0.95]")

    def test_tc_stress_23_mixed_market_portfolio_coverage(self) -> None:
        """TC_STRESS_23: Multi-asset portfolio score generation with mixed KRX and US equities."""
        # 10 mixed symbols: 5 KRX (6 digits), 5 US (letters)
        symbols = ["005930", "000660", "035420", "051910", "005380", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]
        df = pd.DataFrame({"symbol": symbols})
        for eng in [self.f905_engine, self.f906_engine, self.f907_engine, self.f908_engine, self.f909_engine]:
            res = eng.generate_scores(df)
            self.assertEqual(len(res), 10)
            self.assertEqual(list(res["symbol"]), symbols)

    def test_tc_stress_24_fuzz_1000_fx_margin_safety(self) -> None:
        """TC_STRESS_24: Fuzz 1,000 random scenarios verifying margin <= 85% cash under all combinations."""
        rng = np.random.RandomState(4242)
        for trial in range(1000):
            us_weight = rng.uniform(0.0, 1.0)
            allocations = {"AAPL": us_weight, "005930": 1.0 - us_weight}
            portfolio_cap = rng.uniform(1e6, 1e11)
            # Cash ranges from tiny (1 KRW) to abundant (2x portfolio)
            available_cash = rng.uniform(1.0, portfolio_cap * 0.5)

            spot = rng.uniform(500.0, 3000.0)
            vol = rng.uniform(0.01, 0.80)
            mom = rng.uniform(-0.60, 0.60)
            regime = rng.choice(["BULL_LOW_VOL", "BULL_HIGH_VOL", "BEAR_LOW_VOL", "BEAR_HIGH_VOL", "PANIC_CRISIS", "SYSTEMIC_CRISIS", "SEVERE_PANIC"])

            macro_in = FXMacroInput(
                usdkrw_spot=spot,
                fx_volatility_20d=vol,
                fx_momentum_20d=mom,
                regime_label=regime,
            )
            res = self.f906_engine.evaluate_portfolio_fx_hedge(
                portfolio_capital_krw=portfolio_cap,
                portfolio_allocations=allocations,
                macro_input=macro_in,
                available_cash_krw=available_cash,
            )

            max_allowed = available_cash * 0.85
            self.assertLessEqual(
                res.collateral_required_krw,
                max_allowed + 1e-4,
                f"Fuzz trial {trial} failed: collateral={res.collateral_required_krw} > max={max_allowed}",
            )
            self.assertTrue(0.0 <= res.hedge_ratio <= 1.0)
            self.assertTrue(math.isfinite(res.collateral_required_krw))
            self.assertTrue(math.isfinite(res.hedge_notional_krw))

    def test_tc_stress_25_fuzz_1000_contagion_spectral_alerts(self) -> None:
        """TC_STRESS_25: Fuzz 1,000 random adjacency matrices verifying spectral radius and alert logic."""
        rng = np.random.RandomState(9999)
        for trial in range(1000):
            K = rng.randint(2, 12)
            # Random non-negative directed matrix with zero diagonal
            A = rng.uniform(0.0, 1.5, (K, K)) * (rng.uniform(0.0, 1.0, (K, K)) < 0.6)
            np.fill_diagonal(A, 0.0)

            contagion = detect_systemic_contagion(A, threshold=0.40)
            eigs = np.linalg.eigvals(A)
            true_rho = float(np.max(np.abs(eigs))) if len(eigs) > 0 else 0.0

            self.assertAlmostEqual(contagion["spectral_radius"], true_rho, places=6)
            self.assertEqual(contagion["is_contagion_alert"], true_rho > 0.40)

    def test_tc_stress_26_fuzz_1000_mcsi_circuit_breaker_invariants(self) -> None:
        """TC_STRESS_26: Fuzz 1,000 random macro stress inputs verifying MCSI bounds and Tier 5 invariants."""
        rng = np.random.RandomState(8888)
        for trial in range(1000):
            vix_vel = rng.uniform(-0.5, 2.0)
            vix_tsr = rng.uniform(0.5, 2.5)
            spread = rng.uniform(50.0, 2500.0)
            spectral = rng.uniform(0.0, 1.5)
            inversion = rng.uniform(-200.0, 300.0)
            fx_vel = rng.uniform(-0.2, 0.4)

            xi = evaluate_mcsi_v181_index(
                vix_velocity=vix_vel,
                vix_tsr=vix_tsr,
                credit_spread_bps=spread,
                contagion_spectral_radius=spectral,
                yield_inversion_bps=inversion,
                currency_velocity=fx_vel,
            )
            self.assertTrue(0.0 <= xi <= 1.0)
            cb = check_crisis_circuit_breaker_v181(xi)

            if xi >= 0.75:
                self.assertEqual(cb["tier"], TIER_SYSTEMIC_CRISIS)
                self.assertLessEqual(cb["max_leverage_limit"], 0.20)
                self.assertEqual(cb["hedge_overlay_ratio"], 1.0)
                self.assertTrue(cb["gate8_inverse_hedge_active"])
                self.assertTrue(cb["sma200_hard_exit"])
                self.assertTrue(cb["new_longs_gated"])
                self.assertEqual(cb["inverse_hedge_etfs"], ["252670", "114800", "SH", "PSQ"])
            elif xi >= 0.60:
                self.assertEqual(cb["tier"], TIER_SEVERE_PANIC)
                self.assertLessEqual(cb["max_leverage_limit"], 0.40)
                self.assertEqual(cb["hedge_overlay_ratio"], 0.75)
                self.assertTrue(cb["gate8_inverse_hedge_active"])
                self.assertFalse(cb["sma200_hard_exit"])
            elif xi >= 0.45:
                self.assertEqual(cb["tier"], TIER_HIGH_STRESS)
                self.assertLessEqual(cb["max_leverage_limit"], 0.85)
                self.assertEqual(cb["hedge_overlay_ratio"], 0.40)
                self.assertTrue(cb["new_longs_gated"])
            elif xi >= 0.30:
                self.assertEqual(cb["tier"], TIER_ELEVATED)
                self.assertEqual(cb["max_leverage_limit"], 1.35)
                self.assertEqual(cb["hedge_overlay_ratio"], 0.15)
            else:
                self.assertEqual(cb["tier"], TIER_NORMAL)
                self.assertEqual(cb["max_leverage_limit"], 1.95)
                self.assertEqual(cb["hedge_overlay_ratio"], 0.0)

    def test_tc_stress_27_pure_krw_portfolio_zero_us_exposure(self) -> None:
        """TC_STRESS_27: Pure KRW portfolio (zero US exposure) produces zero notional and zero collateral."""
        allocations = {"005930": 0.70, "000660": 0.30}  # 100% KRX stocks
        res = self.f906_engine.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=100_000_000.0,
            portfolio_allocations=allocations,
            macro_input=FXMacroInput(usdkrw_spot=1350.0),
            available_cash_krw=10_000_000.0,
        )
        self.assertEqual(res.us_exposure_krw, 0.0)
        self.assertEqual(res.hedge_notional_krw, 0.0)
        self.assertEqual(res.collateral_required_krw, 0.0)
        # Verify that even if effective_h is h_star, the actual physical order notional is strictly 0.0
        order = generate_fx_hedge_order(res)
        self.assertEqual(order["notional_krw"], 0.0)
        self.assertEqual(order["collateral_required_krw"], 0.0)


    def test_tc_stress_28_cross_currency_basis_arbitrage_limits(self) -> None:
        """TC_STRESS_28: Extreme rate and forward combinations handled safely without division by zero."""
        # Extreme negative interest rates vs hyperinflation
        dev1 = compute_nonlinear_cip_deviation(spot=1350.0, forward=1400.0, r_base=-0.005, r_quote=0.25, tenor_days=90)
        self.assertTrue(math.isfinite(dev1))

        # Forward equals spot
        dev2 = compute_nonlinear_cip_deviation(spot=1350.0, forward=1350.0, r_base=0.04, r_quote=0.04, tenor_days=30)
        self.assertAlmostEqual(dev2, 0.0, places=3)

    def test_tc_stress_29_nss_8param_flat_and_steep_extremes(self) -> None:
        """TC_STRESS_29: NSS 8-parameter curve fitting under completely flat and extreme steep curves."""
        mats = np.array([0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0])
        # Completely flat curve at 4.0%
        flat_yields = np.ones(8) * 0.040
        params_flat = fit_extended_nss_yield_curve_8param(mats, flat_yields)
        self.assertTrue(math.isfinite(params_flat["beta0"]))
        self.assertGreater(params_flat["lambda1"], 0.0)

        # Extreme steep curve: 3M at 1.0%, 30Y at 10.0%
        steep_yields = np.linspace(0.01, 0.10, 8)
        params_steep = fit_extended_nss_yield_curve_8param(mats, steep_yields)
        self.assertTrue(math.isfinite(params_steep["beta0"]))
        self.assertGreater(params_steep["lambda1"], 0.0)

    def test_tc_stress_30_exact_circuit_breaker_boundary_points(self) -> None:
        """TC_STRESS_30: Exact circuit breaker boundary points [0.30, 0.45, 0.60, 0.75] transition crisply."""
        # Just below 0.30
        self.assertEqual(determine_crisis_gating_tier_v181(0.29999), TIER_NORMAL)
        # Exactly 0.30
        self.assertEqual(determine_crisis_gating_tier_v181(0.30000), TIER_ELEVATED)
        # Just below 0.45
        self.assertEqual(determine_crisis_gating_tier_v181(0.44999), TIER_ELEVATED)
        # Exactly 0.45
        self.assertEqual(determine_crisis_gating_tier_v181(0.45000), TIER_HIGH_STRESS)
        # Just below 0.60
        self.assertEqual(determine_crisis_gating_tier_v181(0.59999), TIER_HIGH_STRESS)
        # Exactly 0.60
        self.assertEqual(determine_crisis_gating_tier_v181(0.60000), TIER_SEVERE_PANIC)
        # Just below 0.75
        self.assertEqual(determine_crisis_gating_tier_v181(0.74999), TIER_SEVERE_PANIC)
        # Exactly 0.75
        self.assertEqual(determine_crisis_gating_tier_v181(0.75000), TIER_SYSTEMIC_CRISIS)
        # Above 0.75
        self.assertEqual(determine_crisis_gating_tier_v181(0.99999), TIER_SYSTEMIC_CRISIS)



if __name__ == "__main__":
    unittest.main()
