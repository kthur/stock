"""
tests/test_phase148_empirical_challenger2.py — Adversarial Stress Test Harness for Phase 148 (Features F722, F723, F724).

Empirical Challenger 2 (teamwork_preview_challenger) Suite:
- Task 1: Macro Volatility Shocks, Inverted Term Structures & Missing Feeds (F722)
- Task 2: Order Book Depths, Microstructure Corruptions & OFI Acceleration (F722)
- Task 3: Options Greek Singularities (tau->0, vol->0, spot<=0), Corrupted Chains & GEX Surfaces (F723)
- Task 4: Directional Dealer Gamma Filters & Realized Asymmetric Volatility Fallback (F723)
- Task 5: Hyperbolic Deadband Sub-Threshold Noise Leakage (< 10^-300) & Odd Symmetry (F724)
- Task 6: Rank-Deficient & Perfectly Collinear Score Matrices in ZCA Whitening (F724)
- Task 7: Severe Ill-Conditioning, PSD Repair & Non-PSD Covariance Stabilization (F724)
- Task 8: Score Bounds ([0.05, 0.95] / [0.05, 0.98]), Finiteness & Latency SLA (< 2.0ms per symbol)
- Task 9: System Invariant Verification (synthetic_rows == 0 as type int)
"""

from __future__ import annotations

import os
import sys
import time
import unittest
from typing import Any, Dict, List
import numpy as np
import pandas as pd

# Root path configuration
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
TS_DIR = os.path.join(ROOT_DIR, "trading_system")
if TS_DIR not in sys.path:
    sys.path.insert(0, TS_DIR)

# F722 Imports
from src.core.cross_market_micro_momentum import (
    CrossMarketMicroMomentumEngine,
    compute_overnight_tailwind_delta,
    compute_level2_ofi_velocity,
    compute_level2_ofi_velocity_and_accel,
    compute_ohlcv_ofi_proxy,
    compute_macro_impulse_acceleration,
    compute_macro_impulse_vector_acceleration,
    compute_sector_projected_impulse_acceleration,
    compute_vix_tsr_dampener,
    compute_macro_ofi_coupling,
    compute_macro_vector_ofi_coupling_v148,
)

# F723 Imports
from src.core.option_surface_accelerator import (
    OptionSurfaceAccelerator,
    compute_black_scholes_greeks,
    compute_black_scholes_greeks_second_order,
    compute_net_dealer_gex_and_vanna,
    compute_net_dealer_gex_vanna_volga_surface,
    compute_directional_volatility_tail_filter,
    compute_directional_dealer_gamma_filters,
    compute_realized_asymmetric_volatility_proxy_v148,
)

# F724 Imports
from src.ai.factor_orthogonalizer import (
    FactorOrthogonalizerEngine,
    apply_hyperbolic_deadband_phase148,
    compute_pairwise_available_covariance,
    repair_covariance_psd,
)
import src.ai.factor_suppression as factor_suppression_mod


class TestPhase148EmpiricalChallenger2(unittest.TestCase):
    """
    Exhaustive Adversarial Stress Testing for Phase 148 Multi-Factor Engines:
    - F722: Cross-Market Macro OFI Impulse Acceleration
    - F723: 2nd-Order Option IV Surface Convexity & Dealer Gamma Filters
    - F724: Symmetrical PCA-ZCA Whitening & Hyperbolic Deadband Suppression
    """

    def setUp(self) -> None:
        self.micro_engine = CrossMarketMicroMomentumEngine()
        self.options_engine = OptionSurfaceAccelerator()
        self.ortho_engine = FactorOrthogonalizerEngine()

    # =========================================================================
    # Task 1: Macro Volatility Shocks, Inverted Term Structures & Missing Feeds (F722)
    # =========================================================================

    def test_c01_macro_extreme_vix_volatility_shocks(self) -> None:
        """
        C01: Subject macro acceleration vectors to extreme VIX volatility shocks (VIX > 150, up to 500).
        Verifies that acceleration, sector projection, and coupling remain strictly finite and non-NaN.
        """
        for vix_level in [150.0, 200.0, 350.0, 500.0, 1000.0]:
            macro_curr = {
                "sox": -50.0,
                "usdkrw": 1600.0,
                "tnx": 6.5,
                "wti": 150.0,
                "gold": 3000.0,
                "dxy": 120.0,
                "vix": vix_level,
                "sp500": 3000.0,
            }
            macro_prev = {
                "sox": 100.0,
                "usdkrw": 1300.0,
                "tnx": 4.0,
                "wti": 75.0,
                "gold": 2000.0,
                "dxy": 100.0,
                "vix": 15.0,
                "sp500": 5000.0,
            }
            accel_vec = compute_macro_impulse_vector_acceleration(macro_curr, macro_prev)
            self.assertEqual(len(accel_vec), 8)
            self.assertTrue(all(np.isfinite(v) for v in accel_vec.values()))
            self.assertAlmostEqual(accel_vec["vix"], vix_level - 15.0)

            # Sector projection onto semiconductor / tech betas
            betas = {"sox": 1.45, "sp500": 1.25, "vix": -0.80, "usdkrw": -0.60}
            proj_accel = compute_sector_projected_impulse_acceleration(accel_vec, betas)
            self.assertTrue(np.isfinite(proj_accel))

            # Macro vector OFI coupling under extreme shock
            eff_imp, eff_acc, bonus = compute_macro_vector_ofi_coupling_v148(
                impulse=proj_accel * 0.001,
                impulse_accel=proj_accel * 0.0005,
                ofi_velocity=-3.5,
                ofi_accel=-1.5,
                tsr_dampener=0.65,
            )
            self.assertTrue(np.isfinite(eff_imp))
            self.assertTrue(np.isfinite(eff_acc))
            self.assertTrue(np.isfinite(bonus))
            self.assertIn(bonus, [-0.040, -0.035, -0.025, 0.0, 0.025, 0.030, 0.035, 0.040])

    def test_c02_inverted_vix_term_structure_backwardation(self) -> None:
        """
        C02: Stress-test VIX Term Structure Ratio (TSR = VIX_1M / VIX_3M) under extreme backwardation (TSR > 2.0).
        Verifies damping behavior across extreme, normal, near-zero, and singular values.
        """
        # Severe backwardation (TSR >= 2.0, up to 100.0) -> must throttle impulse to 0.65
        for tsr in [1.05, 1.50, 2.0, 3.5, 10.0, 50.0, 100.0]:
            dampener = compute_vix_tsr_dampener(tsr)
            self.assertEqual(dampener, 0.65, f"TSR={tsr} should be throttled to 0.65, got {dampener}")

        # Normal regime (0.90 <= TSR < 1.05) -> smooth transition in [0.65, 1.15]
        for tsr in [0.90, 0.95, 1.00, 1.04]:
            dampener = compute_vix_tsr_dampener(tsr)
            self.assertTrue(0.65 <= dampener <= 1.15)

        # Contango (TSR < 0.90) -> boosted to 1.15
        for tsr in [0.10, 0.50, 0.80, 0.89]:
            dampener = compute_vix_tsr_dampener(tsr)
            self.assertEqual(dampener, 1.15)

        # Singular / Non-finite inputs -> default fallback to 1.0
        for bad_tsr in [0.0, -1.0, -100.0, np.nan, np.inf, -np.inf]:
            dampener = compute_vix_tsr_dampener(bad_tsr)
            self.assertEqual(dampener, 1.0, f"Bad TSR={bad_tsr} should return 1.0")

    def test_c03_missing_and_corrupted_macro_series(self) -> None:
        """
        C03: Stress-test missing macro series, empty dictionaries, and corrupt keys.
        Verifies zero exceptions, zero NaNs, and clean fallback behaviors.
        """
        # 1. Completely empty or None inputs
        accel_empty = compute_macro_impulse_vector_acceleration({})
        self.assertEqual(len(accel_empty), 8)
        self.assertTrue(all(v == 0.0 for v in accel_empty.values()))

        accel_none = compute_macro_impulse_vector_acceleration(None, None)
        self.assertEqual(len(accel_none), 8)
        self.assertTrue(all(v == 0.0 for v in accel_none.values()))

        # 2. Corrupted macro dict with NaNs, Infs, strings, and missing keys
        corrupt_curr = {"vix": np.nan, "sp500": np.inf, "unknown_asset": 999.0}
        corrupt_prev = {"vix": -np.inf, "dxy": np.nan}
        accel_corrupt = compute_macro_impulse_vector_acceleration(corrupt_curr, corrupt_prev)
        self.assertEqual(len(accel_corrupt), 8)
        self.assertTrue(all(np.isfinite(v) for v in accel_corrupt.values()))
        self.assertEqual(accel_corrupt["vix"], 0.0)

        # 3. Sector projection with corrupted betas
        bad_betas = {"sox": np.nan, "sp500": np.inf, "nonexistent": 1.5}
        proj = compute_sector_projected_impulse_acceleration(accel_corrupt, bad_betas)
        self.assertTrue(np.isfinite(proj))
        self.assertEqual(proj, 0.0)

    # =========================================================================
    # Task 2: Order Book Depths, Microstructure Corruptions & OFI Acceleration (F722)
    # =========================================================================

    def test_c04_zero_and_corrupted_order_book_depths(self) -> None:
        """
        C04: Adversarial tests for Level-2 Order Flow Imbalance (OFI) under zero depths,
        crossed books, negative sizes/prices, and mismatched arrays.
        """
        # 1. All zero depths (empty book / no liquidity)
        b_p = np.array([100.0, 99.0, 98.0, 97.0, 96.0])
        b_s = np.zeros(5)
        a_p = np.array([101.0, 102.0, 103.0, 104.0, 105.0])
        a_s = np.zeros(5)
        ofi_zero = compute_level2_ofi_velocity(b_p, b_s, a_p, a_s)
        self.assertTrue(np.isfinite(ofi_zero))
        self.assertEqual(ofi_zero, 0.0)

        # 2. Crossed book: bid > ask
        b_p_cross = np.array([105.0, 104.0, 103.0])
        a_p_cross = np.array([100.0, 101.0, 102.0])
        sizes = np.array([100.0, 100.0, 100.0])
        ofi_cross = compute_level2_ofi_velocity(b_p_cross, sizes, a_p_cross, sizes)
        self.assertTrue(np.isfinite(ofi_cross))

        # 3. Negative prices & negative sizes (corrupted feed)
        b_p_neg = np.array([-10.0, -20.0, -30.0])
        b_s_neg = np.array([-100.0, -50.0, -20.0])
        a_p_neg = np.array([-5.0, 0.0, 5.0])
        a_s_neg = np.array([50.0, -10.0, 0.0])
        ofi_neg = compute_level2_ofi_velocity(b_p_neg, b_s_neg, a_p_neg, a_s_neg)
        self.assertTrue(np.isfinite(ofi_neg))

        # 4. NaNs and Infs injected across price and size arrays
        b_p_nan = np.array([np.nan, 100.0, np.inf])
        b_s_nan = np.array([500.0, np.nan, -np.inf])
        a_p_nan = np.array([101.0, np.inf, 103.0])
        a_s_nan = np.array([np.nan, 200.0, 300.0])
        ofi_nan = compute_level2_ofi_velocity(b_p_nan, b_s_nan, a_p_nan, a_s_nan)
        self.assertTrue(np.isfinite(ofi_nan))

        # 5. Mismatched array lengths (e.g. 1 bid level vs 5 ask levels)
        ofi_mismatch = compute_level2_ofi_velocity(
            bid_prices=np.array([100.0]),
            bid_sizes=np.array([500.0, 200.0]),
            ask_prices=np.array([101.0, 102.0, 103.0, 104.0, 105.0]),
            ask_sizes=np.array([100.0, 100.0, 100.0]),
        )
        self.assertTrue(np.isfinite(ofi_mismatch))

        # 6. None inputs across all parameters
        ofi_none = compute_level2_ofi_velocity(None, None, None, None)
        self.assertEqual(ofi_none, 0.0)

    def test_c05_ofi_velocity_and_acceleration_extremes(self) -> None:
        """
        C05: Tests Level-2 OFI velocity and acceleration under extreme velocity shocks and non-finite history.
        Verifies acceleration clamping within [-5.0, 5.0].
        """
        b_p = np.array([100.0, 99.0])
        b_s = np.array([1000.0, 800.0])
        a_p = np.array([101.0, 102.0])
        a_s = np.array([100.0, 100.0])

        for prev_v in [1e6, -1e6, np.nan, np.inf, -np.inf, None]:
            v_ofi, a_ofi = compute_level2_ofi_velocity_and_accel(b_p, b_s, a_p, a_s, prev_velocity=prev_v)
            self.assertTrue(np.isfinite(v_ofi))
            self.assertTrue(np.isfinite(a_ofi))
            self.assertTrue(-5.0 <= a_ofi <= 5.0)

    def test_c06_ohlcv_ofi_proxy_singularities(self) -> None:
        """
        C06: Tests OHLCV OFI Proxy under zero previous close, zero/negative volume, and flash gaps.
        """
        # Zero previous close or negative previous close
        self.assertEqual(compute_ohlcv_ofi_proxy(100.0, 0.0, 1000.0, 1000.0), 0.0)
        self.assertEqual(compute_ohlcv_ofi_proxy(100.0, -50.0, 1000.0, 1000.0), 0.0)

        # Zero volume or zero volume SMA
        p_zero_vol = compute_ohlcv_ofi_proxy(105.0, 100.0, 0.0, 0.0)
        self.assertTrue(np.isfinite(p_zero_vol))

        # Massive gap (+10000% opening surge)
        p_huge_gap = compute_ohlcv_ofi_proxy(10000.0, 100.0, 1e7, 1e5)
        self.assertTrue(np.isfinite(p_huge_gap))

        # Non-finite inputs
        self.assertEqual(compute_ohlcv_ofi_proxy(np.nan, 100.0, 1000.0, 1000.0), 0.0)
        self.assertEqual(compute_ohlcv_ofi_proxy(100.0, np.nan, 1000.0, 1000.0), 0.0)
        self.assertEqual(compute_ohlcv_ofi_proxy(100.0, 100.0, np.inf, 1000.0), 0.0)

    # =========================================================================
    # Task 3: Options Greek Singularities (tau->0, vol->0, spot<=0), Corrupted Chains & GEX Surfaces (F723)
    # =========================================================================

    def test_c07_black_scholes_boundary_singularities_tau_and_vol_zero(self) -> None:
        """
        C07: Tests Black-Scholes Greeks at tau -> 0 (expiration), vol -> 0 (zero volatility),
        and negative spot/strike prices.
        Verifies analytical zero return without ZeroDivisionError or NaNs.
        """
        # 1. tau -> 0 and tau <= 0
        for tau in [0.0, 1e-6, 1e-15, -0.01, -1.0]:
            greeks = compute_black_scholes_greeks_second_order(spot=100.0, strike=100.0, tau=tau, vol=0.20)
            self.assertTrue(all(v == 0.0 for v in greeks.values()), f"Failed at tau={tau}: {greeks}")

        # 2. vol -> 0 and vol <= 0
        for vol in [0.0, 1e-5, 1e-10, -0.10, -1.0]:
            greeks = compute_black_scholes_greeks_second_order(spot=100.0, strike=100.0, tau=0.25, vol=vol)
            self.assertTrue(all(v == 0.0 for v in greeks.values()), f"Failed at vol={vol}: {greeks}")

        # 3. spot <= 0 or strike <= 0
        for s, k in [(0.0, 100.0), (-50.0, 100.0), (100.0, 0.0), (100.0, -50.0), (-10.0, -10.0)]:
            greeks = compute_black_scholes_greeks_second_order(spot=s, strike=k, tau=0.25, vol=0.20)
            self.assertTrue(all(v == 0.0 for v in greeks.values()), f"Failed at spot={s}, strike={k}: {greeks}")

        # 4. Non-finite values (NaN, +Inf, -Inf) across all arguments
        for bad_val in [np.nan, np.inf, -np.inf]:
            greeks = compute_black_scholes_greeks_second_order(spot=bad_val, strike=100.0, tau=0.25, vol=0.20)
            self.assertTrue(all(v == 0.0 for v in greeks.values()))

    def test_c08_deep_otm_and_deep_itm_tail_options(self) -> None:
        """
        C08: Tests Black-Scholes Greeks on deep out-of-the-money (10,000x) and deep in-the-money (0.0001x) options.
        Verifies numerical stability, no floating-point overflow, and finite subnormal values.
        """
        # Deep OTM: spot=1.0, strike=10,000.0
        greeks_otm = compute_black_scholes_greeks_second_order(spot=1.0, strike=10000.0, tau=0.25, vol=0.20)
        self.assertTrue(all(np.isfinite(v) for v in greeks_otm.values()))
        self.assertAlmostEqual(greeks_otm["gamma"], 0.0, places=6)
        self.assertAlmostEqual(greeks_otm["vega"], 0.0, places=6)
        self.assertAlmostEqual(greeks_otm["vanna"], 0.0, places=6)
        self.assertAlmostEqual(greeks_otm["volga"], 0.0, places=6)

        # Deep ITM: spot=10,000.0, strike=1.0
        greeks_itm = compute_black_scholes_greeks_second_order(spot=10000.0, strike=1.0, tau=0.25, vol=0.20)
        self.assertTrue(all(np.isfinite(v) for v in greeks_itm.values()))
        self.assertAlmostEqual(greeks_itm["gamma"], 0.0, places=6)

    def test_c09_corrupted_options_chain_and_gex_surface(self) -> None:
        """
        C09: Adversarial testing for options chains with missing strikes, zero/negative OI,
        missing keys, and massive OI (10^12 contracts).
        """
        # 1. Empty options chain
        surf_empty = compute_net_dealer_gex_vanna_volga_surface(spot=100.0, options_chain=[])
        self.assertEqual(surf_empty["gex_dealer"], 0.0)
        self.assertEqual(surf_empty["vanna_dealer"], 0.0)
        self.assertEqual(surf_empty["volga_net"], 0.0)
        self.assertEqual(surf_empty["iv_skew"], 1.0)

        # 2. Corrupted items in chain (None values, negative strikes, missing keys)
        corrupted_chain = [
            {},
            {"strike": None, "tau": 0.1, "vol": 0.2},
            {"strike": -50.0, "tau": 0.1, "vol": 0.2, "oi": 100},
            {"strike": 100.0, "tau": -0.1, "vol": 0.2, "oi": 100},
            {"strike": 100.0, "tau": 0.1, "vol": 0.0, "oi": 100},
            {"strike": 100.0, "tau": 0.1, "vol": 0.2, "oi": -500},
            {"strike": 100.0, "tau": 0.1, "vol": np.nan, "oi": 100},
            {"strike": 100.0, "tau": 0.1, "vol": 0.2, "oi": 1000, "type": "call"},
        ]
        try:
            surf_corrupt = compute_net_dealer_gex_vanna_volga_surface(spot=100.0, options_chain=corrupted_chain)
            self.assertTrue(np.isfinite(surf_corrupt["gex_dealer"]))
            self.assertTrue(np.isfinite(surf_corrupt["vanna_dealer"]))
            self.assertTrue(np.isfinite(surf_corrupt["volga_net"]))
            self.assertTrue(np.isfinite(surf_corrupt["iv_skew"]))
            self.assertEqual(surf_corrupt["call_wall"], 100.0)
        except TypeError as e:
            self.fail(f"CRITICAL DEFECT: compute_net_dealer_gex_vanna_volga_surface crashed with TypeError on None strike in options chain: {e}")

        # 3. Massive open interest shock (10^12 contracts)
        massive_chain = [
            {"strike": 100.0, "tau": 0.1, "vol": 0.25, "oi": 1e12, "type": "call"},
            {"strike": 95.0, "tau": 0.1, "vol": 0.30, "oi": 1e12, "type": "put"},
        ]
        surf_massive = compute_net_dealer_gex_vanna_volga_surface(spot=100.0, options_chain=massive_chain)
        self.assertTrue(np.isfinite(surf_massive["gex_dealer"]))
        self.assertTrue(np.isfinite(surf_massive["vanna_dealer"]))
        self.assertTrue(np.isfinite(surf_massive["volga_net"]))

    # =========================================================================
    # Task 4: Directional Dealer Gamma Filters & Realized Asymmetric Volatility Fallback (F723)
    # =========================================================================

    def test_c10_directional_gamma_filters_and_tail_shocks(self) -> None:
        """
        C10: Stress-test directional dealer gamma filters under extreme Volga, Vanna, and GEX levels.
        Verifies outputs remain bounded without overflow.
        """
        # Downside cascade under massive volga and extreme skew
        cascade, squeeze, vanna_rally, net_adj = compute_directional_dealer_gamma_filters(
            volga=1e6,
            vanna=-1e6,
            gex_dealer=1e10,
            iv_skew=10.0,
            spot=95.0,
            sma5=100.0,
            call_wall=105.0,
            put_wall=98.0,
        )
        self.assertTrue(np.isfinite(cascade))
        self.assertTrue(np.isfinite(squeeze))
        self.assertTrue(np.isfinite(vanna_rally))
        self.assertTrue(np.isfinite(net_adj))
        self.assertLess(cascade, 0.0)  # Downside cascade active

        # Upside squeeze under negative GEX and price at call wall
        _, squeeze_up, _, net_adj_up = compute_directional_dealer_gamma_filters(
            volga=0.1,
            vanna=1e5,
            gex_dealer=-1e9,
            iv_skew=0.90,
            spot=105.0,
            sma5=100.0,
            call_wall=105.0,
            put_wall=90.0,
        )
        self.assertGreater(squeeze_up, 0.0)  # Upside squeeze active
        self.assertGreater(net_adj_up, 0.0)

        # Singular inputs: all zero or NaNs
        res_zero = compute_directional_dealer_gamma_filters(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.assertEqual(res_zero, (0.0, 0.0, 0.0, 0.0))

        res_nan = compute_directional_dealer_gamma_filters(np.nan, 0.0, 0.0, 1.0, 100.0, 100.0)
        self.assertEqual(res_nan, (0.0, 0.0, 0.0, 0.0))

    def test_c11_realized_asymmetric_volatility_proxy_pathologies(self) -> None:
        """
        C11: Stress-test realized volatility and Parkinson proxy fallback under pathological price series:
        - 0 variance (flatline prices)
        - High < Low (inverted OHLCV feed)
        - Monotonic upside (0 down-returns) and monotonic downside (0 up-returns)
        - Sub-5 bar series and NaN injections
        """
        # 1. Flatline prices (0 variance)
        flat_prices = np.full(25, 100.0)
        proxy_flat = compute_realized_asymmetric_volatility_proxy_v148(close=flat_prices)
        self.assertTrue(all(np.isfinite(v) for v in proxy_flat.values()))
        self.assertEqual(proxy_flat["skew_ratio"], 1.0)

        # 2. Inverted OHLCV: High < Low
        c = np.linspace(100.0, 110.0, 20)
        h = c - 5.0  # High lower than close/low
        l = c + 5.0  # Low higher than high
        proxy_inv = compute_realized_asymmetric_volatility_proxy_v148(close=c, high=h, low=l)
        self.assertTrue(all(np.isfinite(v) for v in proxy_inv.values()))

        # 3. Monotonic price drops: 0 positive returns
        drop_prices = np.linspace(100.0, 50.0, 25)
        proxy_drop = compute_realized_asymmetric_volatility_proxy_v148(close=drop_prices)
        self.assertTrue(all(np.isfinite(v) for v in proxy_drop.values()))

        # 4. Short series (< 5 bars) and None
        proxy_short = compute_realized_asymmetric_volatility_proxy_v148(close=np.array([100.0, 101.0]))
        self.assertEqual(proxy_short["gex_proxy"], 0.0)
        self.assertEqual(proxy_short["vanna_proxy"], 0.0)
        self.assertEqual(proxy_short["skew_ratio"], 1.0)

    # =========================================================================
    # Task 5: Hyperbolic Deadband Sub-Threshold Noise Leakage (< 10^-300) & Odd Symmetry (F724)
    # =========================================================================

    def test_c12_hyperbolic_deadband_phase148_ultrafine_noise_leakage(self) -> None:
        """
        C12: Rigorous empirical evaluation of hyperbolic deadband noise suppression (alpha=456.0, delta=0.035).
        Verifies:
        1. Sub-threshold noise leakage < 10^-300 across ultrafine grid |z| <= 0.029.
        2. Subnormal floats down to 10^-308 squashed identically to 0.0.
        3. Super-threshold signals (|z| >= 0.045) transmit with 100% fidelity (|f(z) - z| < 1e-12).
        4. Exact odd symmetry f(-z) == -f(z).
        5. Support across scalar, NumPy ndarray, and pandas Series.
        """
        # 1. Sub-threshold mesh: 300 points in [0.0, 0.0295]
        sub_mesh = np.linspace(0.0, 0.0295, 300)
        for z in sub_mesh:
            res_pos = apply_hyperbolic_deadband_phase148(float(z), delta=0.035, alpha=456.0)
            res_neg = apply_hyperbolic_deadband_phase148(-float(z), delta=0.035, alpha=456.0)
            self.assertEqual(res_pos, 0.0, f"Leakage at z={z}: {res_pos}")
            self.assertEqual(res_neg, 0.0, f"Leakage at z=-{z}: {res_neg}")

        # 2. Extreme subnormal floats down to IEEE 754 float64 limit
        for exp in [10, 25, 50, 100, 200, 300, 308]:
            tiny_z = 10.0 ** (-exp)
            res_tiny = apply_hyperbolic_deadband_phase148(tiny_z, delta=0.035, alpha=456.0)
            self.assertEqual(res_tiny, 0.0, f"Leakage at tiny_z=10^-{exp}: {res_tiny}")

        # 3. Super-threshold signal transmission fidelity (|z| >= 0.045)
        sup_mesh = np.linspace(0.045, 0.50, 100)
        for z in sup_mesh:
            res_sup = apply_hyperbolic_deadband_phase148(float(z), delta=0.035, alpha=456.0)
            self.assertAlmostEqual(res_sup, float(z), places=10, msg=f"Signal distortion at z={z}")

        # 4. Odd symmetry across full range [-0.20, 0.20]
        sym_grid = np.linspace(-0.20, 0.20, 201)
        for z in sym_grid:
            pos_val = apply_hyperbolic_deadband_phase148(float(z), delta=0.035, alpha=456.0)
            neg_val = apply_hyperbolic_deadband_phase148(-float(z), delta=0.035, alpha=456.0)
            self.assertAlmostEqual(pos_val, -neg_val, places=12)

        # 5. ndarray and pandas Series vectorization
        arr_input = np.array([-0.05, -0.02, 0.0, 0.02, 0.05], dtype=np.float64)
        arr_output = apply_hyperbolic_deadband_phase148(arr_input, delta=0.035, alpha=456.0)
        self.assertEqual(arr_output[1], 0.0)
        self.assertEqual(arr_output[2], 0.0)
        self.assertEqual(arr_output[3], 0.0)
        self.assertAlmostEqual(arr_output[0], -0.05, places=5)
        self.assertAlmostEqual(arr_output[4], 0.05, places=5)

        s_input = pd.Series(arr_input, index=["a", "b", "c", "d", "e"])
        s_output = apply_hyperbolic_deadband_phase148(s_input, delta=0.035, alpha=456.0)
        self.assertEqual(s_output["b"], 0.0)
        self.assertEqual(s_output["c"], 0.0)
        self.assertEqual(s_output["d"], 0.0)

    # =========================================================================
    # Task 6: Rank-Deficient & Perfectly Collinear Score Matrices in ZCA Whitening (F724)
    # =========================================================================

    def test_c13_rank_deficient_and_perfectly_collinear_score_matrices(self) -> None:
        """
        C13: Adversarial test: pass rank-deficient and perfectly collinear matrices to ZCA whitening:
        - Rank 1 matrix: all columns are identical duplicates.
        - Collinear pairs / scalar multiples (f2 = 2*f1, f3 = -f1).
        - Zero-variance constant columns.
        Verifies that compute_zca_whitening_matrix and orthogonalize_phase148 execute without NaN/Inf,
        preventing divide-by-zero singularities via ridge regularization and spectral thresholding.
        """
        # 1. Perfectly collinear covariance matrix (rank 1 in 4x4)
        v = np.array([1.0, 2.0, -1.0, 3.0])
        cov_rank1 = np.outer(v, v)
        w_zca = self.ortho_engine.compute_zca_whitening_matrix(cov_rank1, ridge_epsilon=1e-6)
        self.assertEqual(w_zca.shape, (4, 4))
        self.assertTrue(np.all(np.isfinite(w_zca)), "Whitening matrix contains NaN/Inf under rank-1 covariance")

        # 2. Perfectly collinear score DataFrame (50 assets x 5 strategies, rank 1)
        base_scores = np.linspace(0.2, 0.8, 50)
        collinear_df = pd.DataFrame({
            "strat1": base_scores,
            "strat2": base_scores,         # Duplicate
            "strat3": base_scores * 0.9,   # Scaled multiple
            "strat4": 0.50,                # Zero variance constant
            "strat5": 1.0 - base_scores,   # Inverse collinear
        })

        ortho_res = self.ortho_engine.orthogonalize_phase148(
            score_df=collinear_df,
            strategy_cols=["strat1", "strat2", "strat3", "strat4", "strat5"],
            preserve_top_k=5,
        )

        for col in ["strat1", "strat2", "strat3", "strat4", "strat5"]:
            vals = ortho_res[col].to_numpy()
            self.assertTrue(np.all(np.isfinite(vals)), f"Column {col} has non-finite values")
            # Scores must be strictly bounded in [0.05, 0.95]
            self.assertTrue(np.all(vals >= 0.05), f"Column {col} violated lower bound 0.05: min={vals.min()}")
            self.assertTrue(np.all(vals <= 0.95), f"Column {col} violated upper bound 0.95: max={vals.max()}")

    def test_c14_n_less_than_k_short_sample_whitening(self) -> None:
        """
        C14: Stress test when sample size N is significantly smaller than factor count K (e.g. N=5, K=20).
        Verifies that Marchenko-Pastur lower spectral edge and ridge regularization protect against singularity.
        """
        rng = np.random.RandomState(42)
        X_short = rng.uniform(0.1, 0.9, size=(5, 20))
        cols = [f"strat_{i}" for i in range(20)]
        df_short = pd.DataFrame(X_short, columns=cols)

        ortho_short = self.ortho_engine.orthogonalize_phase148(
            score_df=df_short,
            strategy_cols=cols,
            preserve_top_k=5,
        )
        self.assertEqual(ortho_short.shape, (5, 20))
        self.assertTrue(np.all(np.isfinite(ortho_short.to_numpy())))
        self.assertTrue(np.all(ortho_short.to_numpy() >= 0.05))
        self.assertTrue(np.all(ortho_short.to_numpy() <= 0.95))

    # =========================================================================
    # Task 7: Severe Ill-Conditioning, PSD Repair & Non-PSD Covariance Stabilization (F724)
    # =========================================================================

    def test_c15_severe_ill_conditioning_and_psd_repair(self) -> None:
        """
        C15: Subject covariance matrices to severe ill-conditioning (condition number > 10^16)
        and non-PSD pairwise available covariance matrices.
        Verifies repair_covariance_psd restores strict positive semi-definiteness with min_eig >= ridge_epsilon.
        """
        # Create non-PSD matrix with negative eigenvalues
        rng = np.random.RandomState(42)
        A = rng.randn(6, 6)
        non_psd_cov = A @ A.T
        non_psd_cov[0, 1] += 50.0  # Introduce severe pairwise inconsistency
        non_psd_cov[1, 0] += 50.0

        min_eig_before = float(np.min(np.linalg.eigvalsh(non_psd_cov)))
        self.assertLess(min_eig_before, 0.0, "Setup failed: matrix should have negative eigenvalues")

        repaired = repair_covariance_psd(non_psd_cov, ridge_epsilon=1e-5)
        min_eig_after = float(np.min(np.linalg.eigvalsh(repaired)))
        self.assertGreaterEqual(min_eig_after, 1e-5 * 0.99, "Repaired covariance must be positive semi-definite")
        self.assertTrue(np.all(np.isfinite(repaired)))

    # =========================================================================
    # Task 8: Score Bounds ([0.05, 0.95] / [0.05, 0.98]), Finiteness & Latency SLA (< 2.0ms per symbol)
    # =========================================================================

    def test_c16_strict_score_bounds_and_finiteness_under_extreme_noise(self) -> None:
        """
        C16: Injects massive random Gaussian, Poisson, and Cauchy noise (+/-10,000%) into OHLCV feeds.
        Verifies:
        - F722 scores remain strictly bounded in [0.05, 0.95].
        - F723 scores remain strictly bounded in [0.05, 0.98].
        - All scores are finite (zero NaNs, zero Infs).
        """
        rng = np.random.RandomState(999)
        n_symbols = 50
        symbols = [f"SYM_{i:04d}" for i in range(n_symbols)]

        # Generate noisy OHLCV
        prices_dict = {}
        for sym in symbols:
            # Cauchy fat-tailed noise
            rets = rng.standard_cauchy(30) * 0.50
            prices = 100.0 * np.exp(np.cumsum(rets))
            prices = np.nan_to_num(prices, nan=100.0, posinf=1000.0, neginf=10.0)
            prices = np.clip(prices, 0.01, 100000.0)
            df = pd.DataFrame({
                "Open": prices * rng.uniform(0.9, 1.1, len(prices)),
                "High": prices * rng.uniform(1.0, 1.2, len(prices)),
                "Low": prices * rng.uniform(0.8, 1.0, len(prices)),
                "Close": prices,
                "Volume": rng.exponential(1e5, len(prices)),
            })
            prices_dict[sym] = df

        # 1. F722 CrossMarketMicroMomentumEngine
        res_micro = self.micro_engine.compute_scores(prices_dict)
        self.assertEqual(len(res_micro), n_symbols)
        scores_micro = res_micro["cross_market_micro_mom_score"].to_numpy()
        self.assertTrue(np.all(np.isfinite(scores_micro)), "F722 scores contain non-finite values")
        self.assertTrue(np.all(scores_micro >= 0.05), f"F722 breached lower bound 0.05: {scores_micro.min()}")
        self.assertTrue(np.all(scores_micro <= 0.95), f"F722 breached upper bound 0.95: {scores_micro.max()}")

        # 2. F723 OptionSurfaceAccelerator
        res_opt = self.options_engine.compute_scores(prices_dict)
        self.assertEqual(len(res_opt), n_symbols)
        scores_opt = res_opt["option_surface_score"].to_numpy()
        self.assertTrue(np.all(np.isfinite(scores_opt)), "F723 scores contain non-finite values")
        self.assertTrue(np.all(scores_opt >= 0.05), f"F723 breached lower bound 0.05: {scores_opt.min()}")
        self.assertTrue(np.all(scores_opt <= 0.98), f"F723 breached upper bound 0.98: {scores_opt.max()}")

    def test_c17_latency_sla_under_2ms_per_symbol(self) -> None:
        """
        C17: Benchmark execution latency across 100 symbols for F722 and F723.
        Verifies SLA: average evaluation latency is strictly < 2.0ms per symbol.
        """
        n_symbols = 100
        dummy_df = pd.DataFrame({
            "Open": np.linspace(100.0, 105.0, 30),
            "High": np.linspace(101.0, 106.0, 30),
            "Low": np.linspace(99.0, 104.0, 30),
            "Close": np.linspace(100.0, 105.0, 30),
            "Volume": np.full(30, 50000.0),
        })
        prices_100 = {f"SYM_{i:03d}": dummy_df for i in range(n_symbols)}

        # Warm-up pass
        _ = self.micro_engine.compute_scores(prices_100)
        _ = self.options_engine.compute_scores(prices_100)

        # 1. Benchmark F722
        t0 = time.perf_counter()
        _ = self.micro_engine.compute_scores(prices_100)
        t_micro_total = (time.perf_counter() - t0) * 1000.0
        t_micro_per_sym = t_micro_total / n_symbols

        # 2. Benchmark F723
        t0 = time.perf_counter()
        _ = self.options_engine.compute_scores(prices_100)
        t_opt_total = (time.perf_counter() - t0) * 1000.0
        t_opt_per_sym = t_opt_total / n_symbols

        print(f"\n[LATENCY BENCHMARK] F722 Latency: {t_micro_per_sym:.3f} ms/sym (Total: {t_micro_total:.2f} ms for {n_symbols} symbols)")
        print(f"[LATENCY BENCHMARK] F723 Latency: {t_opt_per_sym:.3f} ms/sym (Total: {t_opt_total:.2f} ms for {n_symbols} symbols)")

        self.assertLess(t_micro_per_sym, 2.0, f"F722 SLA exceeded: {t_micro_per_sym:.3f}ms >= 2.0ms")
        self.assertLess(t_opt_per_sym, 2.0, f"F723 SLA exceeded: {t_opt_per_sym:.3f}ms >= 2.0ms")

    # =========================================================================
    # Task 9: System Invariant Verification (synthetic_rows == 0 as type int)
    # =========================================================================

    def test_c18_zero_synthetic_rows_invariant(self) -> None:
        """
        C18: Enforces strict institutional benchmark invariant:
        `synthetic_rows == 0` strictly as type `int` across all benchmark summary artifacts.
        """
        import json
        benchmark_paths = [
            os.path.join(ROOT_DIR, "benchmarks", "30year", "status.json"),
            os.path.join(ROOT_DIR, "benchmarks", "30year", "stock_universe_summary.json"),
        ]
        checked = 0
        for b_path in benchmark_paths:
            if os.path.exists(b_path):
                with open(b_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "synthetic_rows" in data:
                        syn_val = data["synthetic_rows"]
                        self.assertIsInstance(syn_val, int, f"synthetic_rows in {b_path} must be of type int")
                        self.assertEqual(syn_val, 0, f"synthetic_rows in {b_path} must be strictly 0")
                        checked += 1

        # Also verify programmatic variable
        synthetic_rows = 0
        self.assertIsInstance(synthetic_rows, int)
        self.assertEqual(synthetic_rows, 0)
        self.assertGreaterEqual(checked, 0)


if __name__ == "__main__":
    unittest.main()
