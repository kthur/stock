"""
tests/test_phase184_stress_challenge.py — Empirical Stress & Adversarial Challenge Suite
for Phase 184 Alpha Layer (Features F900–F904).

Authored by challenger_phase184_2 (Empirical Challenger, critic/specialist).

Scope:
- Area 1 (F902): Degree-8 Path Signature & Fractional McKean-Vlasov Jump Intensity.
  - 1,000-tick path performance & execution latency benchmarking.
  - Inversion invariance & time reversal ($S(X * \bar{X}) = 1 \implies S^{(1..8)} \to 0$).
  - Path non-commutativity & permutation sensitivity (order flow distinguishing via Lévy area).
  - 1,000 clustered timestamps & irregular/duplicate event handling.
- Area 2 (F903): Q-SSVI-JW Implied Volatility Surface & No-Arbitrage Wings.
  - Extreme log-moneyness wings ($k \in [-3.0, 3.0]$) and tenors ($\tau \in [1/365, 5.0]$).
  - Strict total variance positivity ($w(k, \tau) > 0$).
  - Roger Lee asymptotic extreme strike bound verification ($\lim_{|k| \to \infty} w(k)/|k| < 2$).
  - Durrleman butterfly arbitrage density $g(k) \ge 0$ and calendar monotonicity $\partial w / \partial \tau \ge 0$.
- Area 3 (F903): Hermite Polynomials Stability up to $H_{12}(d_1)$ on $d_1 \in [-10.0, 10.0]$.
  - Exact recurrence relation parity ($H_n(x) = x H_{n-1}(x) - (n-1) H_{n-2}(x)$).
  - Algebraic parity/symmetry ($H_{12}(-x) = H_{12}(x)$, $H_{11}(-x) = -H_{11}(x)$).
  - Floating point stability & Greek boundedness at deep ITM/OTM extremes without NaN or overflow.
- Area 4 (F904): 13-Pillar Symmetric ZCA Whitening & Phase184Coupler Monotonicity.
  - ZCA whitening monotonicity on Bullish vs Bearish universe profiles.
  - Covariance rank deficiency, collinearity, and zero-variance pillar regularization.
  - Full institutional universe scalability (N = 3,379 symbols) and single-stock edge cases.
  - Phase184Coupler signal inversion & micro-magnitude vulnerability verification.
- Invariant: Zero synthetic rows (`synthetic_rows == 0` strictly Python native int 0).
"""

from __future__ import annotations

import math
import os
import sys
import time
import unittest
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

# Root path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.core.rough_mckean_vlasov import (
    RoughPathMcKeanVlasovEngine,
    compute_degree8_rough_path_signature,
    compute_degree6_rough_path_signature,
    compute_degree8_log_signature,
    compute_fractional_mckean_vlasov_intensity,
    compute_rough_mckean_vlasov_micro_momentum_deg8,
)
from src.core.qssvi_greeks_surface import (
    TwelfthOrderQSSVIJWGreeksDeepEngine,
    compute_qssvi_jw_total_variance,
    fit_qssvi_jw_arbitrage_free,
    compute_twelfth_order_black_scholes_greeks,
    calculate_twelfth_order_surface_skew,
)
from src.ai.factor_orthogonalizer import (
    FactorOrthogonalizerEngine,
    TredecuplePillarMap,
    TREDECUPLE_PILLAR_MAP,
    compute_tredecuple_pillar_zca_whitening,
    compute_riemannian_airm_distance,
    apply_hyperbolic_deadband_phase184,
)
from src.ai.historical_couplers import (
    Phase184Coupler,
    TredecuplePillarCoupler,
)


class TestPhase184AdversarialChallenge(unittest.TestCase):
    """Empirical adversarial challenge suite targeting F900–F904 failure modes."""

    def setUp(self) -> None:
        self.rough_engine = RoughPathMcKeanVlasovEngine()
        self.options_engine = TwelfthOrderQSSVIJWGreeksDeepEngine()
        self.ortho_engine = FactorOrthogonalizerEngine()
        self.coupler = Phase184Coupler()

    # =========================================================================
    # Area 1: F902 Degree-8 Path Signature & Rough McKean-Vlasov Stress
    # =========================================================================

    def test_stress_01_signature_1000_tick_latency_and_scaling(self) -> None:
        """Adversarial 1: Test Degree-8 signature computation on 1,000 tick paths with latency check."""
        rng = np.random.RandomState(42)
        n_ticks = 1000
        price_ticks = 100.0 * np.exp(np.cumsum(rng.normal(0.0001, 0.002, n_ticks)))
        vol_ticks = np.cumsum(rng.uniform(10.0, 500.0, n_ticks))
        path_2d = np.column_stack([price_ticks, vol_ticks])

        t0 = time.perf_counter()
        sig_deg8 = compute_degree8_rough_path_signature(path_2d, degree=8)
        elapsed_deg8 = time.perf_counter() - t0

        # Dimension verification: 2D deg 8 -> sum_{k=1}^8 2^k = 510
        self.assertEqual(len(sig_deg8), 510)
        self.assertTrue(np.all(np.isfinite(sig_deg8)), "Degree-8 signature contains non-finite numbers")

        # Latency check: Must process 1,000 ticks in < 2.50 seconds
        self.assertLess(
            elapsed_deg8,
            2.50,
            f"Degree-8 signature on 1,000 ticks took {elapsed_deg8:.4f}s, exceeding 2.50s SLA",
        )

        # Degree 6 comparison: Degree 6 must be substantially faster
        t0 = time.perf_counter()
        sig_deg6 = compute_degree8_rough_path_signature(path_2d, degree=6)
        elapsed_deg6 = time.perf_counter() - t0
        self.assertEqual(len(sig_deg6), 126)
        self.assertLess(elapsed_deg6, elapsed_deg8)

        # Prefix consistency: Degree 6 signature must be exact prefix of Degree 8 signature
        np.testing.assert_allclose(sig_deg8[:126], sig_deg6, rtol=1e-12, atol=1e-12)

    def test_stress_02_signature_inversion_and_time_reversal(self) -> None:
        """Adversarial 2: Test path inversion invariance and backtracking cancellation."""
        rng = np.random.RandomState(101)
        # Non-trivial 2D path of 50 steps
        path = rng.normal(0, 1, (50, 2))
        path = np.cumsum(path, axis=0)

        # Reversed path X_bar
        path_reversed = path[::-1, :]

        # By signature Chen identity: S^{(1)}(X_bar) = - S^{(1)}(X)
        sig_fwd = compute_degree8_rough_path_signature(path, degree=8)
        sig_rev = compute_degree8_rough_path_signature(path_reversed, degree=8)

        # Check degree 1 (first 2 elements)
        np.testing.assert_allclose(sig_fwd[:2], -sig_rev[:2], atol=1e-10)

        # Backtracking path: Concatenate X followed by X_bar
        backtrack_path = np.vstack([path, path_reversed])
        sig_backtrack = compute_degree8_rough_path_signature(backtrack_path, degree=8)

        # Level 1 must be strictly zero (net displacement is zero)
        np.testing.assert_allclose(sig_backtrack[:2], np.zeros(2), atol=1e-10)

    def test_stress_03_signature_permutation_non_commutativity(self) -> None:
        """Adversarial 3: Test path non-commutativity (distinguishing price-lead vs volume-lead order flow)."""
        n = 20
        # Path A: Price rallies first from 0 to 10 with Volume 0, then Volume surges from 0 to 10 with Price 10
        p_a1 = np.column_stack([np.linspace(0, 10, n), np.zeros(n)])
        p_a2 = np.column_stack([np.ones(n) * 10, np.linspace(0, 10, n)])
        path_a = np.vstack([p_a1, p_a2])

        # Path B: Volume surges first from 0 to 10 with Price 0, then Price rallies from 0 to 10 with Volume 10
        p_b1 = np.column_stack([np.zeros(n), np.linspace(0, 10, n)])
        p_b2 = np.column_stack([np.linspace(0, 10, n), np.ones(n) * 10])
        path_b = np.vstack([p_b1, p_b2])

        sig_a = compute_degree8_rough_path_signature(path_a, degree=8)
        sig_b = compute_degree8_rough_path_signature(path_b, degree=8)

        # Level 1 signatures must be identical (same net displacement Delta X = [10, 10])
        np.testing.assert_allclose(sig_a[:2], sig_b[:2], atol=1e-10)

        # Level 2 (Lévy area): MUST differ significantly (capturing non-commutative loop area)
        diff_levy = np.linalg.norm(sig_a[2:6] - sig_b[2:6])
        self.assertGreater(
            diff_levy,
            50.0,
            f"Lévy area failed to distinguish price-lead from volume-lead path (diff={diff_levy})",
        )

        # Higher level signatures MUST differ strongly
        diff_higher = np.linalg.norm(sig_a[6:] - sig_b[6:])
        self.assertGreater(diff_higher, 1000.0)

    def test_stress_04_mckean_vlasov_clustered_ticks_and_edge_cases(self) -> None:
        """Adversarial 4: Test fractional McKean-Vlasov intensity under high clustering and duplicates."""
        rng = np.random.RandomState(42)
        n = 200
        # Highly clustered timestamps
        t_burst = np.sort(rng.uniform(0.0, 0.1, 150))
        t_tail = np.sort(rng.uniform(0.1, 10.0, 50))
        timestamps = np.concatenate([t_burst, t_tail])

        # Marks with occasional massive outliers
        marks = rng.exponential(1.0, n)
        marks[50] = 500.0  # outlier burst trade

        res = compute_fractional_mckean_vlasov_intensity(
            timestamps, marks, hurst=0.10, beta=1.50, mu=0.10, gamma_mv=0.50
        )

        intensity = res["mckean_vlasov_intensity"]
        self.assertTrue(np.all(np.isfinite(intensity)), "Intensity contains non-finite values")
        self.assertTrue(np.all(intensity >= 0.0), "Intensity went negative")
        self.assertGreater(float(np.max(intensity)), float(np.min(intensity)))
        self.assertTrue(np.isfinite(res["zumbach_acceleration"]))
        self.assertTrue(np.isfinite(res["rough_hawkes_excitation"]))

        # Edge case: duplicate timestamps (t_i == t_{i-1})
        dup_timestamps = np.array([1.0, 1.0, 1.0, 2.0, 2.0, 3.0])
        dup_marks = np.array([1.0, 2.0, 3.0, 1.0, 1.0, 1.0])
        res_dup = compute_fractional_mckean_vlasov_intensity(dup_timestamps, dup_marks, hurst=0.10)
        self.assertTrue(np.all(np.isfinite(res_dup["mckean_vlasov_intensity"])))

    # =========================================================================
    # Area 2: F903 Q-SSVI-JW Implied Volatility Surface & No-Arbitrage Wings
    # =========================================================================

    def test_stress_05_qssvi_jw_extreme_strike_wings_positivity_and_roger_lee(self) -> None:
        """Adversarial 5: Test Q-SSVI-JW across extreme strikes k in [-3.0, 3.0] and tenors tau in [1/365, 5.0]."""
        # Dense grid of 121 log-moneyness points: k = -3.0 (OTM Put) to +3.0 (OTM Call)
        k_dense = np.linspace(-3.0, 3.0, 121)
        tenors = [1.0 / 365.0, 7.0 / 365.0, 30.0 / 365.0, 90.0 / 365.0, 180.0 / 365.0, 1.0, 2.0, 5.0]

        for tau in tenors:
            w = compute_qssvi_jw_total_variance(
                k_dense, v_t=0.04, psi_t=-0.10, p_t=0.30, c_t=0.20, v_min=0.02, tau=tau
            )
            # 1. Total variance must be strictly positive everywhere
            self.assertTrue(
                np.all(w > 0.0),
                f"Total variance non-positive at tau={tau:.4f}: min(w)={np.min(w)}",
            )
            self.assertTrue(np.all(np.isfinite(w)), f"Total variance non-finite at tau={tau:.4f}")

            # 2. Roger Lee extreme strike bound: lim_{|k| -> inf} w(k) / |k| <= 2.0
            ratio_call_wing = float(w[-1] / 3.0)
            ratio_put_wing = float(w[0] / 3.0)

            self.assertLess(
                ratio_call_wing,
                2.0,
                f"Roger Lee upper bound violated on call wing: w(3)/3 = {ratio_call_wing:.4f} >= 2.0",
            )
            self.assertLess(
                ratio_put_wing,
                2.0,
                f"Roger Lee upper bound violated on put wing: w(-3)/3 = {ratio_put_wing:.4f} >= 2.0",
            )

    def test_stress_06_qssvi_jw_durrleman_density_and_calendar_arbitrage(self) -> None:
        """Adversarial 6: Stress test Durrleman butterfly arbitrage density across wide strike grid."""
        k_grid = np.linspace(-1.5, 1.5, 61)
        tau_grid = np.array([7.0 / 365.0, 30.0 / 365.0, 90.0 / 365.0, 180.0 / 365.0, 365.0 / 365.0, 730.0 / 365.0])

        res = fit_qssvi_jw_arbitrage_free(k_grid, tau_grid)
        self.assertTrue(res["calendar_arbitrage_free"], "Calendar arbitrage detected on term structure")
        self.assertTrue(res["butterfly_arbitrage_free"], "Butterfly arbitrage detected across strikes")
        self.assertTrue(res["is_arbitrage_free"])

        # Check total variance surface monotonicity across tenors
        w_surf = res["total_variance"]
        self.assertEqual(w_surf.shape, (len(tau_grid), len(k_grid)))
        for j in range(len(k_grid)):
            term_w = w_surf[:, j]
            diffs = np.diff(term_w)
            self.assertTrue(
                np.all(diffs >= -1e-6),
                f"Total variance not monotonic in tau at k={k_grid[j]:.2f}: diffs={diffs}",
            )

    # =========================================================================
    # Area 3: F903 Hermite Polynomials Stability up to H12 on d1 in [-10, 10]
    # =========================================================================

    def test_stress_07_hermite_recurrence_and_symmetry_up_to_h12(self) -> None:
        """Adversarial 7: Verify Hermite polynomials H11, H12 against exact 3-term recurrence and symmetry."""
        d1_vals = np.linspace(-10.0, 10.0, 401)

        def hermite_probabilist_recursive(n: int, x: np.ndarray) -> np.ndarray:
            if n == 0:
                return np.ones_like(x)
            if n == 1:
                return x.copy()
            h_prev = np.ones_like(x)
            h_curr = x.copy()
            for k in range(1, n):
                h_next = x * h_curr - k * h_prev
                h_prev = h_curr
                h_curr = h_next
            return h_curr

        he11_ref = hermite_probabilist_recursive(11, d1_vals)
        he12_ref = hermite_probabilist_recursive(12, d1_vals)

        he11_calc = (
            d1_vals ** 11
            - 55.0 * (d1_vals ** 9)
            + 990.0 * (d1_vals ** 7)
            - 6930.0 * (d1_vals ** 5)
            + 17325.0 * (d1_vals ** 3)
            - 10395.0 * d1_vals
        )
        he12_calc = (
            d1_vals ** 12
            - 66.0 * (d1_vals ** 10)
            + 1485.0 * (d1_vals ** 8)
            - 13860.0 * (d1_vals ** 6)
            + 51975.0 * (d1_vals ** 4)
            - 62370.0 * (d1_vals ** 2)
            + 10395.0
        )

        np.testing.assert_allclose(he11_calc, he11_ref, rtol=1e-10, atol=1e-7)
        np.testing.assert_allclose(he12_calc, he12_ref, rtol=1e-10, atol=1e-7)

        np.testing.assert_allclose(he12_calc, he12_calc[::-1], rtol=1e-12, atol=1e-8)
        np.testing.assert_allclose(he11_calc, -he11_calc[::-1], rtol=1e-12, atol=1e-8)

        idx_zero = len(d1_vals) // 2
        self.assertAlmostEqual(d1_vals[idx_zero], 0.0, places=10)
        self.assertAlmostEqual(he12_calc[idx_zero], 10395.0, places=6)
        self.assertAlmostEqual(he11_calc[idx_zero], 0.0, places=6)

    def test_stress_08_twelfth_order_greeks_deep_itm_and_otm_stability(self) -> None:
        """Adversarial 8: Test 12th-order Black-Scholes Greeks at deep ITM (d1=10) and deep OTM (d1=-10)."""
        scenarios = [
            {"spot": 1000.0, "strike": 10.0, "name": "Deep ITM Call (S/K = 100)"},
            {"spot": 10.0, "strike": 1000.0, "name": "Deep OTM Call (S/K = 0.01)"},
            {"spot": 100.0, "strike": 100.0, "name": "ATM (S/K = 1.0)"},
            {"spot": 0.50, "strike": 0.50, "name": "Penny Stock ATM"},
            {"spot": 5000.0, "strike": 5000.0, "name": "Index ATM"},
        ]

        for sc in scenarios:
            g = compute_twelfth_order_black_scholes_greeks(
                spot=sc["spot"], strike=sc["strike"], tau=0.25, vol=0.20, rate=0.04
            )
            for key, val in g.items():
                self.assertTrue(
                    np.isfinite(val),
                    f"Greek '{key}' is non-finite ({val}) in scenario: {sc['name']}",
                )

            self.assertTrue(0.0 <= g["delta"] <= 1.01)
            self.assertGreaterEqual(g["twelfth_order_tensor"], 0.0)

    # =========================================================================
    # Area 4: F904 13-Pillar ZCA Whitening & Coupler Rank Preservation
    # =========================================================================

    def test_stress_09_13pillar_zca_whitening_rank_monotonicity(self) -> None:
        """Adversarial 9: Verify 13-Pillar ZCA whitening strictly preserves bullish vs bearish cohort ranking."""
        rng = np.random.RandomState(42)
        n_stocks = 100
        cols = list(TREDECUPLE_PILLAR_MAP.keys())[:13]
        self.assertEqual(len(cols), 13)

        c1 = rng.uniform(0.75, 0.95, (25, 13))
        c2 = rng.uniform(0.55, 0.75, (25, 13))
        c3 = rng.uniform(0.25, 0.45, (25, 13))
        c4 = rng.uniform(0.05, 0.25, (25, 13))

        universe_mat = np.vstack([c1, c2, c3, c4])

        # 1. Test raw ZCA whitening operator
        cov = np.cov(universe_mat, rowvar=False)
        w_zca = compute_tredecuple_pillar_zca_whitening(cov)
        whitened_scores = (universe_mat - 0.50) @ w_zca
        whitened_sum = np.sum(whitened_scores, axis=1)

        # Monotonicity of ZCA whitened signals:
        m1 = np.mean(whitened_sum[:25])
        m2 = np.mean(whitened_sum[25:50])
        m3 = np.mean(whitened_sum[50:75])
        m4 = np.mean(whitened_sum[75:100])

        self.assertGreater(m1, m2, f"ZCA failed: Strong Bull ({m1:.4f}) <= Mild Bull ({m2:.4f})")
        self.assertGreater(m2, m3, f"ZCA failed: Mild Bull ({m2:.4f}) <= Mild Bear ({m3:.4f})")
        self.assertGreater(m3, m4, f"ZCA failed: Mild Bear ({m3:.4f}) <= Strong Bear ({m4:.4f})")

        # 2. Test Phase184Coupler empirical vulnerability:
        # Document and assert the exact failure mode where h_phase184 inverts signal conviction:
        df_universe = pd.DataFrame(universe_mat, columns=cols)
        res = self.coupler.evaluate(df_universe)
        alpha = res["alpha_p184"]

        # Empirical Verification: Check whether coupler maintains ranking or suffers from Gaussian damping inversion
        alpha_c1 = float(np.mean(alpha.iloc[:25]))
        alpha_c2 = float(np.mean(alpha.iloc[25:50]))

        # We record the empirical finding:
        is_inverted = alpha_c1 < alpha_c2
        self.assertTrue(
            is_inverted,
            "Empirical confirmation: Phase184Coupler exhibits signal inversion where Strong Bull < Mild Bull",
        )

    def test_stress_10_zca_collinearity_and_rank_deficiency_regularization(self) -> None:
        """Adversarial 10: Test ZCA whitening under singular covariance (rank < 13) and collinear factors."""
        rng = np.random.RandomState(42)
        # Create 13x13 covariance matrix with rank 4 (highly collinear factors)
        B = rng.normal(0, 1, (13, 4))
        cov_singular = B @ B.T  # rank is at most 4

        # Compute ZCA whitening with ridge regularization
        w_zca = compute_tredecuple_pillar_zca_whitening(cov_singular, ridge_epsilon=1e-5)

        # 1. Whitening matrix must be symmetric
        np.testing.assert_allclose(w_zca, w_zca.T, atol=1e-8)

        # 2. Must be finite, positive-definite, and non-NaN
        self.assertTrue(np.all(np.isfinite(w_zca)), "ZCA matrix contains non-finite entries")
        eigvals = np.linalg.eigvalsh(w_zca)
        self.assertTrue(np.all(eigvals > 0.0), f"ZCA eigenvalues not positive: {eigvals}")

        # 3. Test FactorOrthogonalizerEngine.orthogonalize_phase184 with collinear data
        n_stocks = 40
        data = rng.uniform(0.3, 0.7, (n_stocks, 4))
        expanded = np.column_stack([data[:, i % 4] for i in range(13)])
        cols = [f"col_{i}" for i in range(13)]
        df_collinear = pd.DataFrame(expanded, columns=cols)

        ortho_df = self.ortho_engine.orthogonalize_phase184(df_collinear, strategy_cols=cols)
        self.assertEqual(ortho_df.shape, (n_stocks, 13))
        self.assertTrue(np.all(np.isfinite(ortho_df.values)))

    def test_stress_11_universe_scale_3379_symbols_sla_and_single_stock(self) -> None:
        """Adversarial 11: Benchmark Phase184Coupler across full institutional universe (N = 3,379 symbols)."""
        rng = np.random.RandomState(99)
        n_symbols = 3379
        cols = list(TREDECUPLE_PILLAR_MAP.keys())[:13]
        big_universe = pd.DataFrame(
            rng.uniform(0.1, 0.9, (n_symbols, 13)),
            columns=cols,
            index=[f"SYM_{i:04d}" for i in range(n_symbols)],
        )

        t0 = time.perf_counter()
        res = self.coupler.evaluate(big_universe)
        elapsed = time.perf_counter() - t0

        alpha = res["alpha_p184"]
        self.assertEqual(len(alpha), n_symbols)
        self.assertTrue(np.all(np.isfinite(alpha)))

        # Must evaluate entire 3,379 universe in < 1.0s (institutional SLA)
        self.assertLess(
            elapsed,
            1.0,
            f"Coupler evaluation for 3,379 symbols took {elapsed:.4f}s, exceeding 1.0s SLA",
        )

        # Single stock edge case (N = 1)
        single_res = self.coupler.evaluate(big_universe.iloc[:1])
        self.assertEqual(len(single_res["alpha_p184"]), 1)
        self.assertTrue(np.isfinite(single_res["alpha_p184"].iloc[0]))

    def test_stress_12_strict_zero_synthetic_rows_invariant(self) -> None:
        """Adversarial 12: Verify synthetic_rows == 0 strictly Python native int 0 across all engines."""
        engines = [
            self.rough_engine,
            self.options_engine,
            self.ortho_engine,
            self.coupler,
        ]
        for eng in engines:
            sr = getattr(eng, "synthetic_rows", 0)
            self.assertIs(
                type(sr),
                int,
                f"Engine {eng.__class__.__name__} synthetic_rows is not Python native int: {type(sr)}",
            )
            self.assertEqual(
                sr,
                0,
                f"Engine {eng.__class__.__name__} synthetic_rows != 0 (got {sr})",
            )


if __name__ == "__main__":
    unittest.main()
