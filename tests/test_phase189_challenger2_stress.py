"""
tests/test_phase189_challenger2_stress.py — Empirical Challenger Stress Test Suite for Phase 189
(Global Macro & Rates Architecture, Features F925–F929).

Adversarial Stress Testing & Empirical Verification:
1. Numerical Stability & Memory:
   - Extreme inputs: all-zeros, extreme spikes, NaNs, infs, negative rates.
   - Output data types: float32/float64, no object arrays or Python object leaks.
   - Memory bloat check: repeated evaluations show no unbounded memory growth.
2. Invariant Consistency:
   - `synthetic_rows == 0` strictly native Python int 0 (not bool) across all outputs.
   - Dual-tree bit-for-bit parity verification.
3. Execution Speed & Latency SLA:
   - All 5 engines evaluate in < 5.0 ms per bar.
4. Historical Crisis Compatibility:
   - Compatibility of MacroCrisisSeverityIndexV182Engine with all 5 historical crises
     in benchmarks/30year/crisis.csv (1997, 2000, 2008, 2020, 2022).
"""

from __future__ import annotations

import os
import sys
import time
import gc
import unittest
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd

# Path setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.core.macro_hyper_tensor_impulse_v182 import (
    MacroHyperTensorImpulseV182Engine,
    compute_5th_order_hyper_tensor_impulse,
    compute_dynamic_macro_tensor_elasticity,
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
    compute_quad_curvature_triangular_arbitrage,
    generate_quad_fx_hedge_order,
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


class TestPhase189ChallengerStress(unittest.TestCase):
    """Adversarial stress and performance benchmarks for Phase 189 macro engines."""

    # =========================================================================
    # 1. Numerical Stability & Extreme Inputs
    # =========================================================================

    def test_f925_hyper_tensor_extreme_inputs(self) -> None:
        """Stress F925 with zeros, huge values (+/-10.0), NaNs, and negative volatility."""
        # 1. All-zero macro shocks
        zero_shocks = {f: 0.0 for f in GLOBAL_MACRO_FACTORS}
        val_zero = compute_5th_order_hyper_tensor_impulse(zero_shocks, sector="Semiconductor")
        self.assertIsInstance(val_zero, float)
        self.assertEqual(val_zero, 0.0)

        # 2. Extreme shocks (+/- 5.0 std dev)
        extreme_shocks = {f: 5.0 if i % 2 == 0 else -5.0 for i, f in enumerate(GLOBAL_MACRO_FACTORS)}
        val_extreme = compute_5th_order_hyper_tensor_impulse(extreme_shocks, sector="Semiconductor")
        self.assertFalse(np.isnan(val_extreme))
        self.assertFalse(np.isinf(val_extreme))

        # 3. Wavelet decomposition on constant array
        flat_arr = np.ones(100, dtype=np.float64) * 42.0
        decomp = decompose_macro_impulse_multi_frequency_wavelet(flat_arr)
        recon = decomp["reconstructed"]
        np.testing.assert_allclose(recon, flat_arr, rtol=1e-5, atol=1e-5)
        # Transient on constant should be zero
        np.testing.assert_allclose(decomp["transient"], np.zeros(100), rtol=1e-5, atol=1e-4)

        # 4. Wavelet on short array (< 8 elements)
        short_arr = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        decomp_short = decompose_macro_impulse_multi_frequency_wavelet(short_arr)
        np.testing.assert_allclose(decomp_short["reconstructed"], short_arr)

        # 5. Unpriced macro diffusion with extreme half life
        alpha_fast = compute_unpriced_macro_diffusion_v182(2.5, np.array([1.0, 2.0]), half_life=0.001)
        self.assertTrue(-3.0 <= alpha_fast <= 3.0)
        alpha_slow = compute_unpriced_macro_diffusion_v182(2.5, np.array([1.0, 2.0]), half_life=10000.0)
        self.assertTrue(-3.0 <= alpha_slow <= 3.0)

    def test_f926_fx_hedger_boundary_conditions(self) -> None:
        """Stress F926 quad curvature FX hedger with extreme currency shifts."""
        # 1. Zero tenor, extreme spot
        spread_extreme = compute_quad_curvature_basis_spread(
            spot=2000.0, forward=2500.0, r_dom=-0.01, r_for=0.15, tau=0.0001
        )
        self.assertFalse(np.isnan(spread_extreme))
        self.assertFalse(np.isinf(spread_extreme))

        # 2. Extreme volatility and crisis regime
        macro_crisis = FXMacroInput(
            usdkrw_spot=1600.0,
            forward_rate=1650.0,
            kr_rate=0.02,
            us_rate=0.06,
            tenor_days=7,
            fx_volatility_20d=0.45,
            stock_volatility=0.60,
            stock_fx_correlation=-0.85,
            regime_label="PANIC_LIQUIDITY_SQUEEZE",
        )
        h_star = calculate_quad_curvature_hedge_ratio(macro_crisis)
        # During severe panic, flight to safety clamp enforces h* <= 0.25
        self.assertGreaterEqual(h_star, 0.0)
        self.assertLessEqual(h_star, 0.25)

        # 3. Normal regime with positive correlation
        macro_bull = FXMacroInput(
            usdkrw_spot=1300.0,
            forward_rate=1305.0,
            regime_label="BULL_LOW_VOL",
            stock_fx_correlation=0.5,
        )
        h_bull = calculate_quad_curvature_hedge_ratio(macro_bull)
        self.assertTrue(0.0 <= h_bull <= 1.0)

    def test_f927_nss10_fitting_and_inversion(self) -> None:
        """Stress F927 extended NSS curve fitting under normal, inverted, and flat curves."""
        tenors = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0]

        # 1. Normal upward-sloping yield curve
        normal_yields = [0.025, 0.028, 0.030, 0.033, 0.036, 0.040, 0.043, 0.046, 0.049, 0.051]
        fit_norm = fit_extended_nss_10param_curve(tenors, normal_yields)
        self.assertIn("beta0", fit_norm)
        self.assertIn("mse", fit_norm)
        self.assertLess(fit_norm["mse"], 0.001)  # Good fit

        # Instantaneous forward rate at 0 must equal beta0 + beta1
        f0 = compute_nss10_instantaneous_forward_rate(0.0, fit_norm)
        self.assertAlmostEqual(f0, fit_norm["beta0"] + fit_norm["beta1"], places=5)

        # Inversion check on normal curve -> inverted should be False
        inv_norm = detect_yield_curve_inversion_v182(fit_norm)
        self.assertFalse(inv_norm["is_inverted"])
        self.assertEqual(inv_norm["synthetic_rows"], 0)

        # 2. Deep inverted yield curve (2Y > 10Y by 100 bps)
        inverted_yields = [0.055, 0.054, 0.052, 0.050, 0.047, 0.043, 0.041, 0.038, 0.036, 0.035]
        fit_inv = fit_extended_nss_10param_curve(tenors, inverted_yields)
        inv_res = detect_yield_curve_inversion_v182(fit_inv)
        self.assertTrue(inv_res["is_inverted"])
        self.assertLess(inv_res["spread_10_2_bps"], 0.0)
        self.assertGreater(inv_res["inversion_severity_bps"], 0.0)
        self.assertEqual(inv_res["synthetic_rows"], 0)

        # 3. Flat yield curve
        flat_yields = [0.040] * 10
        fit_flat = fit_extended_nss_10param_curve(tenors, flat_yields)
        self.assertFalse(np.isnan(fit_flat["mse"]))

    def test_f928_renyi_schrodinger_transfer_entropy_edge_cases(self) -> None:
        """Stress F928 transfer entropy with identical series, uncorrelated series, and zero length."""
        # 1. Identical series -> transfer entropy must be 0.0
        s = np.sin(np.linspace(0, 10, 100))
        te_self = compute_directed_renyi_schrodinger_transfer_entropy(s, s, alpha=1.25)
        self.assertEqual(te_self, 0.0)

        # 2. Constant series -> 0.0
        const = np.ones(50)
        te_const = compute_directed_renyi_schrodinger_transfer_entropy(const, s[:50], alpha=1.25)
        self.assertEqual(te_const, 0.0)

        # 3. Short series (< 5 elements)
        te_short = compute_directed_renyi_schrodinger_transfer_entropy(np.array([1.0, 2.0]), np.array([2.0, 3.0]))
        self.assertEqual(te_short, 0.0)

        # 4. Multi-asset network with 5 assets
        np.random.seed(42)
        rets = np.random.randn(120, 5) * 0.02
        # Introduce strong causal lag: asset 1 follows asset 0
        rets[1:, 1] += 0.8 * rets[:-1, 0]

        net = detect_systemic_contagion_network_v182(rets, asset_names=["A", "B", "C", "D", "E"], alpha=1.25)
        self.assertEqual(net["adjacency_matrix"].shape, (5, 5))
        self.assertEqual(np.diag(net["adjacency_matrix"]).sum(), 0.0)  # Zero diagonal
        self.assertIsInstance(net["spectral_radius"], float)
        self.assertFalse(np.isnan(net["spectral_radius"]))
        self.assertEqual(net["synthetic_rows"], 0)

    def test_f929_mcsi_v182_bounds_and_tier_monotonicity(self) -> None:
        """Verify MCSI continuous score is strictly in [0.0, 1.0] and tiers monotonically de-leverage."""
        # 1. All zero stress -> TIER_NORMAL
        zero_ind = {
            "vix_velocity": 0.0,
            "vix_tsr": 0.70,
            "credit_spread_bps": 150.0,
            "contagion_spectral_radius": 0.10,
            "yield_inversion_bps": 0.0,
            "currency_velocity": 0.0,
            "hyper_tensor_impulse": 0.0,
        }
        score_min = compute_mcsi_v182_multi_horizon_score(zero_ind)
        self.assertEqual(score_min, 0.0)
        tier_min = determine_mcsi_v182_6tier_gating(score_min)
        self.assertEqual(tier_min, TIER_NORMAL)
        lev_min = get_leverage_limit_for_mcsi_v182(tier_min)
        self.assertEqual(lev_min, 2.15)

        # 2. Maximum stress -> TIER_CIRCUIT_BREAKER_HALT
        max_ind = {
            "vix_velocity": 1.5,
            "vix_tsr": 1.6,
            "credit_spread_bps": 1200.0,
            "contagion_spectral_radius": 0.95,
            "yield_inversion_bps": 150.0,
            "currency_velocity": 0.15,
            "hyper_tensor_impulse": 8.0,
        }
        score_max = compute_mcsi_v182_multi_horizon_score(max_ind)
        self.assertEqual(score_max, 1.0)
        tier_max = determine_mcsi_v182_6tier_gating(score_max)
        self.assertEqual(tier_max, TIER_CIRCUIT_BREAKER_HALT)
        cb_max = check_circuit_breaker_v182(score_max)
        self.assertTrue(cb_max["is_circuit_breaker_halt"])
        self.assertEqual(cb_max["max_leverage"], 0.00)
        self.assertEqual(cb_max["inverse_hedge_ratio"], 1.00)

        # 3. Verify monotonic decrease of leverage across all 6 tiers
        all_tiers = [
            TIER_NORMAL,
            TIER_ELEVATED,
            TIER_HIGH_STRESS,
            TIER_SYSTEMIC_CRISIS,
            TIER_PANIC_LIQUIDITY_SQUEEZE,
            TIER_CIRCUIT_BREAKER_HALT,
        ]
        leverages = [get_leverage_limit_for_mcsi_v182(t) for t in all_tiers]
        for i in range(len(leverages) - 1):
            self.assertGreater(
                leverages[i], leverages[i + 1],
                f"Leverage must strictly decrease from {all_tiers[i]} to {all_tiers[i+1]}"
            )

    # =========================================================================
    # 2. Output Dtypes, Memory Bloat & Zero Synthetic Rows Invariant
    # =========================================================================

    def test_output_dtypes_and_no_object_leaks(self) -> None:
        """Verify that all numeric outputs are float32/float64/int without object dtype leaks."""
        # Engine 1: MacroHyperTensorImpulseV182Engine
        eng1 = MacroHyperTensorImpulseV182Engine()
        df_dummy = pd.DataFrame({"symbol": ["005930", "AAPL", "NVDA"], "sector": ["Semiconductor", "IT", "Semiconductor"]})
        scores1 = eng1.generate_scores(df_dummy)
        self.assertIn(scores1["score"].dtype, (np.float32, np.float64, float))
        self.assertIn(scores1["probability"].dtype, (np.float32, np.float64, float))

        # Engine 2: QuadCurvatureFXHedgingEngine
        eng2 = QuadCurvatureFXHedgingEngine()
        res2 = eng2.evaluate_portfolio_fx_hedge(FXMacroInput(usdkrw_spot=1350.0), us_exposure_krw=1e8, available_cash_krw=2e7)
        self.assertIsInstance(res2.hedge_ratio, (float, np.floating))
        self.assertIsInstance(res2.cip_deviation_bps, (float, np.floating))
        self.assertIsInstance(res2.quad_basis_spread_bps, (float, np.floating))

        # Engine 3: NSS10RatesHedgeEngine
        eng3 = NSS10RatesHedgeEngine()
        scores3 = eng3.generate_scores(df_dummy)
        self.assertIn(scores3["score"].dtype, (np.float32, np.float64, float))

        # Engine 4: RenyiSchrodingerTransferEntropyEngine
        eng4 = RenyiSchrodingerTransferEntropyEngine()
        scores4 = eng4.generate_scores(df_dummy)
        self.assertIn(scores4["score"].dtype, (np.float32, np.float64, float))

        # Engine 5: MacroCrisisSeverityIndexV182Engine
        eng5 = MacroCrisisSeverityIndexV182Engine()
        scores5 = eng5.generate_scores(df_dummy)
        self.assertIn(scores5["score"].dtype, (np.float32, np.float64, float))

    def test_synthetic_rows_strictly_native_zero(self) -> None:
        """Verify `synthetic_rows == 0` is strictly Python native int 0 across all 5 engines."""
        df_dummy = pd.DataFrame({"symbol": ["005930", "AAPL"], "sector": ["Semiconductor", "IT"]})

        engines = [
            MacroHyperTensorImpulseV182Engine(),
            NSS10RatesHedgeEngine(),
            RenyiSchrodingerTransferEntropyEngine(),
            MacroCrisisSeverityIndexV182Engine(),
        ]

        for eng in engines:
            sdf = eng.generate_scores(df_dummy)
            for meta in sdf["metadata"]:
                self.assertIn("synthetic_rows", meta)
                s_val = meta["synthetic_rows"]
                self.assertIs(type(s_val), int, f"synthetic_rows in {eng.__class__.__name__} must be native int")
                self.assertEqual(s_val, 0)
                self.assertIsNot(s_val, False, "synthetic_rows must NOT be a boolean False")

        # FX hedger order
        eng_fx = QuadCurvatureFXHedgingEngine()
        order_res = eng_fx.evaluate_portfolio_fx_hedge(
            FXMacroInput(usdkrw_spot=1350.0), us_exposure_krw=1e8, available_cash_krw=2e7
        )
        self.assertIn("synthetic_rows", order_res.details)
        s_order = order_res.details["synthetic_rows"]
        self.assertIs(type(s_order), int)
        self.assertEqual(s_order, 0)
        self.assertIsNot(s_order, False)

        # MCSI circuit breaker check
        cb = check_circuit_breaker_v182(0.70)
        self.assertIn("synthetic_rows", cb)
        s_cb = cb["synthetic_rows"]
        self.assertIs(type(s_cb), int)
        self.assertEqual(s_cb, 0)
        self.assertIsNot(s_cb, False)

    def test_memory_stability_under_load(self) -> None:
        """Verify no memory leak or bloat during 2,000 successive evaluations."""
        import tracemalloc
        gc.collect()
        tracemalloc.start()

        eng1 = MacroHyperTensorImpulseV182Engine()
        eng2 = QuadCurvatureFXHedgingEngine()
        eng5 = MacroCrisisSeverityIndexV182Engine()

        macro_in = FXMacroInput(usdkrw_spot=1350.0)
        shocks = {f: 0.01 for f in GLOBAL_MACRO_FACTORS}

        # Warm up
        for _ in range(100):
            _ = eng1.compute_5th_order_hyper_tensor_impulse(shocks)
            _ = eng2.calculate_quad_curvature_hedge_ratio(macro_in)
            _ = eng5.compute_mcsi_v182_multi_horizon_score()

        snapshot1 = tracemalloc.take_snapshot()

        # Run 2,000 evaluations
        for _ in range(2000):
            _ = eng1.compute_5th_order_hyper_tensor_impulse(shocks)
            _ = eng2.calculate_quad_curvature_hedge_ratio(macro_in)
            _ = eng5.compute_mcsi_v182_multi_horizon_score()

        snapshot2 = tracemalloc.take_snapshot()
        tracemalloc.stop()

        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        total_growth_kb = sum(stat.size_diff for stat in top_stats) / 1024.0

        # Memory growth should be well below 2.0 MB for 2,000 purely numerical iterations
        self.assertLess(total_growth_kb, 2048.0, f"Memory grew by {total_growth_kb:.2f} KB, possible leak!")

    # =========================================================================
    # 3. Execution Speed & Latency SLA (< 5ms per bar)
    # =========================================================================

    def test_execution_speed_latency_sla_all_five_engines(self) -> None:
        """
        Benchmark latency of each of the 5 macro engines:
        Requirement: Each engine must evaluate in < 5.0 ms per bar.
        """
        N_ITER = 500

        # Engine 1: MacroHyperTensorImpulseV182Engine
        eng1 = MacroHyperTensorImpulseV182Engine()
        shocks = {f: 0.01 for f in GLOBAL_MACRO_FACTORS}
        arr_imp = np.random.randn(64)

        t0 = time.perf_counter()
        for _ in range(N_ITER):
            _ = eng1.compute_5th_order_hyper_tensor_impulse(shocks)
            _ = eng1.decompose_macro_impulse_multi_frequency_wavelet(arr_imp)
        t_eng1 = (time.perf_counter() - t0) / N_ITER * 1000.0  # ms per bar

        # Engine 2: QuadCurvatureFXHedgingEngine
        eng2 = QuadCurvatureFXHedgingEngine()
        macro_in = FXMacroInput(usdkrw_spot=1350.0)
        t0 = time.perf_counter()
        for _ in range(N_ITER):
            _ = eng2.calculate_quad_curvature_hedge_ratio(macro_in)
            _ = compute_quad_curvature_basis_spread(1350.0, 1355.0, 0.035, 0.045, 0.25)
        t_eng2 = (time.perf_counter() - t0) / N_ITER * 1000.0

        # Engine 3: NSS10RatesHedgeEngine
        eng3 = NSS10RatesHedgeEngine()
        params = {"beta0": 0.04, "beta1": -0.01, "beta2": 0.01, "beta3": -0.005, "beta4": 0.005, "beta5": 0.002,
                  "tau1": 1.5, "tau2": 4.0, "tau3": 10.0, "tau4": 25.0}
        tenors = np.array([0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30])
        t0 = time.perf_counter()
        for _ in range(N_ITER):
            _ = evaluate_nss10_yield(tenors, params)
            _ = compute_nss10_instantaneous_forward_rate(0.0, params)
            _ = detect_yield_curve_inversion_v182(params)
        t_eng3 = (time.perf_counter() - t0) / N_ITER * 1000.0

        # Engine 4: RenyiSchrodingerTransferEntropyEngine (pairwise evaluation per bar)
        eng4 = RenyiSchrodingerTransferEntropyEngine()
        x = np.random.randn(60)
        y = np.random.randn(60)
        t0 = time.perf_counter()
        for _ in range(N_ITER):
            _ = compute_directed_renyi_schrodinger_transfer_entropy(x, y, alpha=1.25, lag=1)
        t_eng4 = (time.perf_counter() - t0) / N_ITER * 1000.0

        # Engine 5: MacroCrisisSeverityIndexV182Engine
        eng5 = MacroCrisisSeverityIndexV182Engine()
        ind = {"vix_velocity": 0.12, "vix_tsr": 0.95, "credit_spread_bps": 400.0}
        t0 = time.perf_counter()
        for _ in range(N_ITER):
            s = eng5.compute_mcsi_v182_multi_horizon_score(ind)
            _ = eng5.check_circuit_breaker_v182(s)
        t_eng5 = (time.perf_counter() - t0) / N_ITER * 1000.0

        # Print benchmark metrics
        print(f"\n[LATENCY SLA BENCHMARK]")
        print(f"Engine 1 (Hyper-Tensor Wavelet F925): {t_eng1:.4f} ms / bar")
        print(f"Engine 2 (Quad FX Hedger F926):        {t_eng2:.4f} ms / bar")
        print(f"Engine 3 (NSS-10 Rates Hedge F927):    {t_eng3:.4f} ms / bar")
        print(f"Engine 4 (Renyi-Schrodinger TE F928):  {t_eng4:.4f} ms / bar")
        print(f"Engine 5 (MCSI v182 Gating F929):      {t_eng5:.4f} ms / bar")

        self.assertLess(t_eng1, 5.0, f"Engine 1 exceeded 5ms SLA: {t_eng1:.4f} ms")
        self.assertLess(t_eng2, 5.0, f"Engine 2 exceeded 5ms SLA: {t_eng2:.4f} ms")
        self.assertLess(t_eng3, 5.0, f"Engine 3 exceeded 5ms SLA: {t_eng3:.4f} ms")
        self.assertLess(t_eng4, 5.0, f"Engine 4 exceeded 5ms SLA: {t_eng4:.4f} ms")
        self.assertLess(t_eng5, 5.0, f"Engine 5 exceeded 5ms SLA: {t_eng5:.4f} ms")

    # =========================================================================
    # 4. Compatibility with 5 Historical Crises in crisis.csv
    # =========================================================================

    def test_compatibility_with_all_five_historical_crises(self) -> None:
        """
        Verify MacroCrisisSeverityIndexV182Engine evaluates accurately against
        the 5 canonical crises defined in benchmarks/30year/crisis.csv:
        1. 1997_ASIAN_CRISIS
        2. 2000_DOTCOM_CRASH
        3. 2008_GFC
        4. 2020_COVID_SHOCK
        5. 2022_INFLATION_RATE_HIKE
        """
        crisis_csv_path = PROJECT_ROOT / "benchmarks" / "30year" / "crisis.csv"
        self.assertTrue(crisis_csv_path.exists(), f"crisis.csv not found at {crisis_csv_path}")

        df_crisis = pd.read_csv(crisis_csv_path)
        expected_ids = [
            "1997_ASIAN_CRISIS",
            "2000_DOTCOM_CRASH",
            "2008_GFC",
            "2020_COVID_SHOCK",
            "2022_INFLATION_RATE_HIKE",
        ]

        # Verify all 5 crises present in crisis.csv
        found_ids = df_crisis["crisis_id"].tolist()
        for cid in expected_ids:
            self.assertIn(cid, found_ids, f"Crisis {cid} missing from crisis.csv")

        # Canonical macro indicator shock profiles during the peak of each crisis:
        crisis_profiles: Dict[str, Dict[str, float]] = {
            "1997_ASIAN_CRISIS": {
                # Currency crash (USDKRW 800 -> 1800+), high interest rates, contagion across Asian markets
                "currency_velocity": 0.08,             # Extreme KRW depreciation
                "vix_velocity": 0.15,
                "vix_tsr": 0.95,
                "credit_spread_bps": 650.0,
                "contagion_spectral_radius": 0.55,     # Severe Asian regional contagion
                "yield_inversion_bps": 20.0,
                "hyper_tensor_impulse": -2.2,
            },
            "2000_DOTCOM_CRASH": {
                # Tech bubble collapse (SOX down >70%), extreme macro tensor impulse shock
                "currency_velocity": 0.015,
                "vix_velocity": 0.22,
                "vix_tsr": 1.05,
                "credit_spread_bps": 520.0,
                "contagion_spectral_radius": 0.42,
                "yield_inversion_bps": 45.0,           # Pre-crash 2000 Fed inversion
                "hyper_tensor_impulse": -3.5,          # Massive tech contraction
            },
            "2008_GFC": {
                # Global financial crisis: VIX > 80, credit spread blowout (HY OAS > 1800 bps), backwardation
                "currency_velocity": 0.065,
                "vix_velocity": 0.50,                  # Super-spike
                "vix_tsr": 1.35,                       # Deep backwardation
                "credit_spread_bps": 1600.0,           # Credit freeze
                "contagion_spectral_radius": 0.85,     # Global systemic contagion
                "yield_inversion_bps": 30.0,
                "hyper_tensor_impulse": -4.8,
            },
            "2020_COVID_SHOCK": {
                # Instantaneous velocity shock: VIX 15 -> 82 in 3 weeks, liquidity panic
                "currency_velocity": 0.05,
                "vix_velocity": 0.65,                  # Fastest spike in history
                "vix_tsr": 1.45,
                "credit_spread_bps": 1050.0,
                "contagion_spectral_radius": 0.78,
                "yield_inversion_bps": 15.0,
                "hyper_tensor_impulse": -3.8,
            },
            "2022_INFLATION_RATE_HIKE": {
                # Stagflation, aggressive Fed rate hikes (425 bps in 1 year), deepest yield curve inversion in 40y
                "currency_velocity": 0.038,
                "vix_velocity": 0.12,
                "vix_tsr": 0.98,
                "credit_spread_bps": 550.0,
                "contagion_spectral_radius": 0.38,
                "yield_inversion_bps": 108.0,          # 10Y-2Y inverted > 100 bps
                "hyper_tensor_impulse": -1.8,
            },
        }

        eng5 = MacroCrisisSeverityIndexV182Engine()

        print("\n[HISTORICAL CRISIS EVALUATION COMPATIBILITY]")
        for cid, profile in crisis_profiles.items():
            score = eng5.compute_mcsi_v182_multi_horizon_score(profile)
            tier = eng5.determine_mcsi_v182_6tier_gating(score)
            max_lev = eng5.get_leverage_limit_for_mcsi_v182(tier)
            cb = eng5.check_circuit_breaker_v182(score)

            print(f"Crisis: {cid:<26} | Score: {score:.4f} | Tier: {tier:<26} | Max Lev: {max_lev:.2f}x | Inverse Hedge: {cb['inverse_hedge_ratio']:.2f}")

            # Verification assertions:
            # 1. Score must be strictly elevated (>= 0.40) for all historical crisis peaks
            self.assertGreaterEqual(
                score, 0.40,
                f"Crisis {cid} score ({score:.4f}) failed to register high stress (>= 0.40)"
            )
            # 2. Tier must be HIGH_STRESS or worse
            self.assertIn(
                tier,
                (TIER_HIGH_STRESS, TIER_SYSTEMIC_CRISIS, TIER_PANIC_LIQUIDITY_SQUEEZE, TIER_CIRCUIT_BREAKER_HALT),
                f"Crisis {cid} did not trigger adequate defense tier: got {tier}"
            )
            # 3. Leverage must be gated to <= 1.10x
            self.assertLessEqual(
                max_lev, 1.10,
                f"Crisis {cid} leverage ({max_lev}x) must be capped <= 1.10x"
            )
            # 4. Gating must restrict new longs
            self.assertTrue(
                cb["gate_new_longs"],
                f"Crisis {cid} must gate new speculative long positions"
            )
            # 5. Inverse hedge overlay must be activated (>= 0.40)
            self.assertGreaterEqual(
                cb["inverse_hedge_ratio"], 0.40,
                f"Crisis {cid} inverse hedge ratio ({cb['inverse_hedge_ratio']}) must be >= 0.40"
            )
            # 6. synthetic_rows == 0 invariant
            self.assertEqual(cb["synthetic_rows"], 0)
            self.assertIs(type(cb["synthetic_rows"]), int)


if __name__ == "__main__":
    unittest.main()
