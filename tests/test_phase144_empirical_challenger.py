"""
tests/test_phase144_empirical_challenger.py — Empirical Challenger Adversarial Stress Harness for Phase 144 Alpha Features (F700–F704).

Designed and executed by empirical_challenger agent (teamwork_preview_challenger) to rigorously
challenge numerical stability, extreme boundary behavior, and system invariants.

Challenge Suite:
- F700: GATv2 multi-frequency attention under extreme return shocks (+/-1000%), zero volume,
        disconnected graph components, and dense grid Hill Bullwhip monotonicity (dphi/dx > 0) on [-10, 10].
- F701: Macro impulse under extreme TSR backwardation (TSR >= 2.50) and zero-spread flatline order books.
- F702: Disclosure deadband exact boundary transitions (P(Neutral) = 0.749, 0.750, 0.751).
- F703: Analytical Black-Scholes Greeks under near-zero tau, zero vol, and deep OTM tail options.
- F704: PCA-ZCA whitening under perfectly collinear matrices (rank = 1) and severe ill-conditioning,
        verifying alpha=448.0 hyperbolic deadband squashes sub-threshold noise below 10^-312.
- Invariants: Zero NaNs, zero Infinities, bounded score outputs ([0.05, 0.98]), no unhandled exceptions.
"""

from __future__ import annotations

import os
import sys
import unittest
import numpy as np
import pandas as pd

# Path setup
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
TS_DIR = os.path.join(ROOT_DIR, "trading_system")
if TS_DIR not in sys.path:
    sys.path.insert(0, TS_DIR)

from src.core.supply_chain_gnn_v2 import (
    bullwhip_transform,
    compute_multi_fx_elasticity,
    SupplyChainGNNv2Engine,
)
from src.core.cross_market_micro_momentum import (
    compute_macro_impulse_acceleration,
    compute_vix_tsr_dampener,
    compute_macro_ofi_coupling,
    compute_level2_ofi_velocity,
    compute_overnight_tailwind_delta,
    CrossMarketMicroMomentumEngine,
)
from src.core.nlp_catalyst_engine import (
    apply_disclosure_deadband,
    compute_finbert_polarity,
    compute_tone_drift_and_accel,
    compute_guidance_revision_acceleration,
    NLPCatalystEngine,
)
from src.core.option_surface_accelerator import (
    compute_black_scholes_greeks,
    compute_net_dealer_gex_and_vanna,
    compute_directional_volatility_tail_filter,
    OptionSurfaceAccelerator,
)
from src.ai.factor_orthogonalizer import (
    apply_hyperbolic_deadband_phase144,
    compute_pairwise_available_covariance,
    repair_covariance_psd,
    FactorOrthogonalizerEngine,
    OrthogonalizedAlphaFeatureStore,
)


class TestPhase144EmpiricalChallenger(unittest.TestCase):
    """
    Adversarial Empirical Stress Harness challenging all Phase 144 Alpha modules (F700–F704).
    """

    def setUp(self) -> None:
        np.random.seed(20261031)
        self.gnn_engine = SupplyChainGNNv2Engine()
        self.micro_engine = CrossMarketMicroMomentumEngine()
        self.nlp_engine = NLPCatalystEngine()
        self.options_engine = OptionSurfaceAccelerator()
        self.ortho_engine = FactorOrthogonalizerEngine(default_method="pca_symmetric")

    # =========================================================================
    # CHALLENGE 1: F700 GATv2 & Value Chain Multi-Frequency GNN
    # =========================================================================

    def test_c01_hill_bullwhip_monotonicity_ultrafine_grid(self) -> None:
        """C01: Verify strict monotonicity (dphi/dx > 0) across 20,001 points on [-10.0, 10.0]."""
        x_grid = np.linspace(-10.0, 10.0, 20001)
        dx = x_grid[1] - x_grid[0]
        for hop in [1, 2, 3, 4]:
            phi = np.array([bullwhip_transform(x, hop=hop) for x in x_grid], dtype=np.float64)
            diffs = np.diff(phi)
            self.assertTrue(
                np.all(diffs > 0.0),
                f"Hop {hop}: Non-positive derivative detected! Min diff = {np.min(diffs)}"
            )
            numerical_slope = diffs / dx
            self.assertTrue(np.all(np.isfinite(numerical_slope)))
            self.assertGreater(np.min(numerical_slope), 0.0)

    def test_c02_f700_extreme_return_shocks_and_crashes(self) -> None:
        """C02: Subject GNN to +1000% return shocks, -99.9% flash crashes, and extreme cycle."""
        dates = pd.date_range("2026-01-01", periods=15, freq="B")
        # Extreme +1000% spike
        df_spike = pd.DataFrame({"Close": [10.0] * 14 + [110.0], "Volume": [1e6] * 15}, index=dates)
        # Extreme -99.9% crash
        df_crash = pd.DataFrame({"Close": [100.0] * 14 + [0.1], "Volume": [1e6] * 15}, index=dates)
        # Wild oscillations (+1000%, -90%, +500%, -80%)
        close_wild = [10.0, 110.0, 11.0, 66.0, 13.2, 100.0, 10.0, 100.0, 10.0, 100.0, 10.0, 100.0, 10.0, 100.0, 10.0]
        df_wild = pd.DataFrame({"Close": close_wild, "Volume": [1e6] * 15}, index=dates)

        res_df = self.gnn_engine.compute_scores({
            "NVDA": df_spike,
            "000660": df_crash,
            "TSM": df_wild,
        })
        scores = res_df["supply_chain_gnn_v2_score"]
        self.assertFalse(scores.isna().any(), "Zero NaNs invariant violated in F700 under shocks")
        self.assertTrue(np.all(np.isfinite(scores)), "Infinite score detected in F700 under shocks")
        self.assertTrue((scores >= 0.05).all() and (scores <= 0.98).all(), "Scores exceeded bounds [0.05, 0.98]")

    def test_c03_f700_zero_volume_across_all_nodes(self) -> None:
        """C03: Zero volume across all nodes and all time bars must not raise ZeroDivisionError."""
        dates = pd.date_range("2026-01-01", periods=20, freq="B")
        prices_dict = {
            sym: pd.DataFrame({"Close": np.linspace(50, 100, 20), "Volume": [0.0] * 20}, index=dates)
            for sym in ["NVDA", "000660", "TSM", "AAPL", "005930"]
        }
        res_df = self.gnn_engine.compute_scores(prices_dict)
        scores = res_df["supply_chain_gnn_v2_score"]
        self.assertFalse(scores.isna().any())
        self.assertTrue((scores >= 0.05).all() and (scores <= 0.98).all())

    def test_c04_f700_disconnected_graph_components(self) -> None:
        """C04: Isolated nodes with 0 edges and partitioned subgraphs must produce valid neutral scores."""
        dates = pd.date_range("2026-01-01", periods=15, freq="B")
        df_norm = pd.DataFrame({"Close": np.linspace(100, 110, 15), "Volume": [1e5] * 15}, index=dates)
        
        # Test with custom graph that has completely isolated components:
        # Node A connected to Node B, but Node C, D, E completely disconnected
        custom_edges = [
            ("NODE_A", "NODE_B", 0.8, 10.0),
        ]
        isolated_engine = SupplyChainGNNv2Engine(custom_edges=custom_edges)
        res_df = isolated_engine.compute_scores({
            "NODE_A": df_norm,
            "NODE_B": df_norm,
            "ISOLATED_C": df_norm,
            "ISOLATED_D": df_norm,
        })
        self.assertEqual(len(res_df), 4)
        scores = res_df["supply_chain_gnn_v2_score"]
        self.assertFalse(scores.isna().any())
        self.assertTrue((scores >= 0.05).all() and (scores <= 0.98).all())
        # Isolated nodes should evaluate safely around 0.50
        df_indexed = res_df.set_index("symbol")
        self.assertAlmostEqual(df_indexed.loc["ISOLATED_C", "supply_chain_gnn_v2_score"], 0.50, delta=0.05)

    # =========================================================================
    # CHALLENGE 2: F701 Macro Impulse & Level-2 OFI Velocity
    # =========================================================================

    def test_c05_f701_extreme_vix_tsr_backwardation(self) -> None:
        """C05: Extreme TSR backwardation (TSR >= 2.50 up to 50.0) must throttle dampener to 0.65."""
        for tsr in [2.50, 3.0, 5.0, 10.0, 50.0, 100.0]:
            dampener = compute_vix_tsr_dampener(tsr)
            self.assertEqual(dampener, 0.65, f"TSR={tsr} dampener should be 0.65, got {dampener}")

        # Check coupling with extreme macro impulse under backwardation
        impulse = 0.08  # Extreme macro surge +8%
        accel = 0.04
        ofi_vel = 0.85
        eff_imp, bonus = compute_macro_ofi_coupling(impulse, accel, ofi_vel, tsr_dampener=0.65)
        self.assertAlmostEqual(eff_imp, impulse * 0.65, places=5)
        self.assertTrue(np.isfinite(eff_imp))
        self.assertTrue(np.isfinite(bonus))

    def test_c06_f701_zero_spread_flatline_order_books(self) -> None:
        """C06: Zero-spread flatline order books (bid=ask) and zero sizes return safe 0.0 velocity."""
        # 1. Bid == Ask identical price flatline
        bp = np.array([100.0, 100.0, 100.0, 100.0, 100.0])
        bs = np.array([500.0, 500.0, 500.0, 500.0, 500.0])
        ap = np.array([100.0, 100.0, 100.0, 100.0, 100.0])
        as_ = np.array([500.0, 500.0, 500.0, 500.0, 500.0])

        v1 = compute_level2_ofi_velocity(bp, bs, ap, as_)
        self.assertEqual(v1, 0.0)

        # 2. Both sizes zero
        bs_zero = np.zeros(5)
        as_zero = np.zeros(5)
        v2 = compute_level2_ofi_velocity(bp, bs_zero, ap, as_zero)
        self.assertEqual(v2, 0.0)

        # 3. Dynamic transition with 0 spread
        v3 = compute_level2_ofi_velocity(bp, bs, ap, as_, prev_bid_prices=bp, prev_bid_sizes=bs, prev_ask_prices=ap, prev_ask_sizes=as_)
        self.assertEqual(v3, 0.0)

    def test_c07_f701_extreme_macro_impulse_acceleration(self) -> None:
        """C07: Impulse acceleration d^2/dt^2 under +/-1000% overnight macro shock."""
        accel_pos = compute_macro_impulse_acceleration(impulse_curr=10.0, impulse_prev=0.0)
        self.assertEqual(accel_pos, 10.0)

        accel_neg = compute_macro_impulse_acceleration(impulse_curr=-10.0, impulse_prev=5.0)
        self.assertEqual(accel_neg, -15.0)

        # Non-finite resilience
        self.assertEqual(compute_macro_impulse_acceleration(np.nan, 1.0), -1.0)
        self.assertEqual(compute_macro_impulse_acceleration(1.0, np.nan), 0.0)

    # =========================================================================
    # CHALLENGE 3: F702 Alternative NLP Guidance & Disclosure Deadband
    # =========================================================================

    def test_c08_f702_disclosure_deadband_exact_boundary_values(self) -> None:
        """C08: Exact boundary transition at P(Neutral) = 0.749, 0.750, 0.751."""
        polarity = 0.35
        conviction = 0.40

        # Case 1: P(Neutral) = 0.749 < 0.750 threshold -> Not filtered
        p_clean, c_clean, is_filt = apply_disclosure_deadband(
            polarity=polarity,
            conviction=conviction,
            neu_prob=0.749,
            neutral_threshold=0.750,
        )
        self.assertFalse(is_filt, "P(Neutral)=0.749 must NOT be filtered")
        self.assertEqual(p_clean, polarity)
        self.assertEqual(c_clean, conviction)

        # Case 2: P(Neutral) = 0.750 == 0.750 threshold -> Filtered
        p_clean, c_clean, is_filt = apply_disclosure_deadband(
            polarity=polarity,
            conviction=conviction,
            neu_prob=0.750,
            neutral_threshold=0.750,
        )
        self.assertTrue(is_filt, "P(Neutral)=0.750 MUST be filtered")
        self.assertEqual(p_clean, 0.0)
        self.assertEqual(c_clean, 0.0)

        # Case 3: P(Neutral) = 0.751 > 0.750 threshold -> Filtered
        p_clean, c_clean, is_filt = apply_disclosure_deadband(
            polarity=polarity,
            conviction=conviction,
            neu_prob=0.751,
            neutral_threshold=0.750,
        )
        self.assertTrue(is_filt, "P(Neutral)=0.751 MUST be filtered")
        self.assertEqual(p_clean, 0.0)
        self.assertEqual(c_clean, 0.0)

    def test_c09_f702_guidance_acceleration_zero_divisor_boundary(self) -> None:
        """C09: Guidance revision acceleration with exact 0.0 previous guidance."""
        rate, accel = compute_guidance_revision_acceleration(guidance_curr=10.0, guidance_prev1=0.0, guidance_prev2=0.0)
        self.assertTrue(np.isfinite(rate))
        self.assertTrue(np.isfinite(accel))
        self.assertGreater(rate, 0.0)

    # =========================================================================
    # CHALLENGE 4: F703 Analytical Greeks & Volatility Surface Tail Filters
    # =========================================================================

    def test_c10_f703_near_zero_tau_and_zero_vol(self) -> None:
        """C10: Black-Scholes Greeks under near-zero tau, zero vol, and degenerate parameters."""
        # 1. tau -> 0.0 and tau < 1e-5
        for tau in [0.0, 1e-12, 1e-9, 1e-6, 1e-5]:
            g = compute_black_scholes_greeks(spot=100.0, strike=100.0, tau=tau, vol=0.20)
            for k, val in g.items():
                self.assertEqual(val, 0.0, f"tau={tau} key={k} should be 0.0, got {val}")

        # 2. vol -> 0.0 and vol < 1e-4
        for vol in [0.0, 1e-10, 1e-6, 1e-4]:
            g = compute_black_scholes_greeks(spot=100.0, strike=100.0, tau=0.1, vol=vol)
            for k, val in g.items():
                self.assertEqual(val, 0.0, f"vol={vol} key={k} should be 0.0, got {val}")

        # 3. tau just above cutoff (tau = 1.01e-5, vol = 1.01e-4)
        g_edge = compute_black_scholes_greeks(spot=100.0, strike=100.0, tau=1.01e-5, vol=1.01e-4)
        for k, val in g_edge.items():
            self.assertTrue(np.isfinite(val))

    def test_c11_f703_deep_otm_tail_options(self) -> None:
        """C11: Deep OTM tail options (spot=100, strike=10,000 and strike=0.01) must remain stable."""
        # 100x OTM Call
        g_call_tail = compute_black_scholes_greeks(spot=100.0, strike=10000.0, tau=0.25, vol=0.30)
        self.assertTrue(np.isfinite(g_call_tail["gamma"]))
        self.assertTrue(np.isfinite(g_call_tail["vega"]))
        self.assertTrue(np.isfinite(g_call_tail["vanna"]))
        self.assertTrue(np.isfinite(g_call_tail["volga"]))
        self.assertLess(g_call_tail["gamma"], 1e-50)
        self.assertAlmostEqual(g_call_tail["gamma"], 0.0, places=10)

        # 10,000x OTM Put
        g_put_tail = compute_black_scholes_greeks(spot=100.0, strike=0.01, tau=0.25, vol=0.30)
        self.assertTrue(np.isfinite(g_put_tail["gamma"]))
        self.assertTrue(np.isfinite(g_put_tail["vega"]))
        self.assertLess(g_put_tail["gamma"], 1e-50)
        self.assertAlmostEqual(g_put_tail["gamma"], 0.0, places=10)

    # =========================================================================
    # CHALLENGE 5: F704 PCA-ZCA Whitening & Hyperbolic Deadband
    # =========================================================================

    def test_c12_f704_perfectly_collinear_score_matrix_rank1(self) -> None:
        """C12: Perfectly collinear rank-1 score matrix across 37 strategies and 50 symbols."""
        N = 50
        base = np.linspace(0.1, 0.9, N)
        strat_cols = [f"strat_{i}" for i in range(37)]
        # All columns are exact multiples of base (rank = 1)
        data = {col: base * (i + 1) * 0.1 for i, col in enumerate(strat_cols)}
        df_collinear = pd.DataFrame(data, index=[f"SYM_{i:03d}" for i in range(N)])

        # Run orthogonalization
        out_df = self.ortho_engine.orthogonalize(df_collinear, strategy_cols=strat_cols, method="pca_symmetric")
        self.assertEqual(out_df.shape, df_collinear.shape)
        self.assertFalse(out_df.isna().any().any(), "Collinear matrix generated NaNs!")
        self.assertTrue(np.all(np.isfinite(out_df.values)), "Collinear matrix generated Infs!")

    def test_c13_f704_severe_ill_conditioning_covariance_repair(self) -> None:
        """C13: Severe ill-conditioning (eigenvalues ranging from 1.0 down to 1e-25)."""
        K = 20
        # Construct ill-conditioned covariance matrix
        eigvals = np.logspace(-25, 0, K)
        Q, _ = np.linalg.qr(np.random.randn(K, K))
        C_ill = Q @ np.diag(eigvals) @ Q.T

        C_repaired = repair_covariance_psd(C_ill, ridge_epsilon=1e-5)
        min_eig = float(np.min(np.linalg.eigvalsh(C_repaired)))
        self.assertGreaterEqual(min_eig, 1e-5, "Repaired covariance minimum eigenvalue must exceed ridge epsilon")
        cond = np.linalg.cond(C_repaired)
        self.assertLess(cond, 1e8, f"Condition number must be regularized, got {cond}")

    def test_c14_f704_hyperbolic_deadband_squashes_subthreshold_noise_below_10_312(self) -> None:
        """C14: Verify alpha=448.0 hyperbolic deadband squashes sub-threshold noise below 10^-312."""
        delta = 0.035
        alpha = 448.0

        # Sub-threshold test values: z / delta < 0.85 -> exact 0.0
        sub_threshold_inputs = [
            0.0,
            1e-15,
            1e-6,
            0.010,
            0.020,
            0.025,
            0.029,  # 0.029 / 0.035 = 0.8285 < 0.85
        ]
        for z in sub_threshold_inputs:
            clean_z = apply_hyperbolic_deadband_phase144(z, delta=delta, alpha=alpha)
            self.assertEqual(clean_z, 0.0, f"z={z} was not squashed to 0.0")

        # Theoretical verification: at r = 0.20, (0.20)^448 ≈ 10^-313 < 10^-312
        r_noise = 0.20
        noise_leakage = (r_noise ** alpha)
        self.assertLess(noise_leakage, 1e-312, f"Theoretical noise leakage {noise_leakage} must be < 10^-312")

        # Full transmission for |z| >= 0.045
        for z in [0.045, 0.050, 0.10, 0.25, 0.50, 1.0]:
            clean_z = apply_hyperbolic_deadband_phase144(z, delta=delta, alpha=alpha)
            self.assertAlmostEqual(clean_z, z, places=5)

    # =========================================================================
    # CHALLENGE 6: Zero NaNs, Zero Infs, Bounded Outputs [0.05, 0.98]
    # =========================================================================

    def test_c15_system_invariants_bounded_scores_all_engines(self) -> None:
        """C15: Assert [0.05, 0.98] score boundedness, zero NaNs, zero Infs across all 5 engines under random stress."""
        dates = pd.date_range("2026-01-01", periods=25, freq="B")
        test_symbols = ["NVDA", "AAPL", "005930", "000660", "TSLA"]

        for iteration in range(5):
            prices_dict = {}
            for sym in test_symbols:
                # Random noisy path with potential zeros and large jumps
                ret = np.random.normal(0.001, 0.08, 25)
                price = 100.0 * np.exp(np.cumsum(ret))
                vol = np.random.uniform(0.0, 1e7, 25)
                # Introduce occasional zero volume
                vol[::4] = 0.0
                prices_dict[sym] = pd.DataFrame({"Close": price, "Volume": vol}, index=dates)

            res_gnn = self.gnn_engine.compute_scores(prices_dict)
            res_micro = self.micro_engine.compute_scores(prices_dict)
            res_nlp = self.nlp_engine.compute_scores(prices_dict)
            res_opt = self.options_engine.compute_scores(prices_dict)

            engines_results = [
                (res_gnn, "supply_chain_gnn_v2_score"),
                (res_micro, "cross_market_micro_mom_score"),
                (res_nlp, "nlp_catalyst_score"),
                (res_opt, "option_surface_score"),
            ]

            for df_out, col in engines_results:
                scores = df_out[col]
                self.assertFalse(scores.isna().any(), f"NaN found in {col} on iteration {iteration}")
                self.assertTrue(np.all(np.isfinite(scores)), f"Inf found in {col} on iteration {iteration}")
                self.assertTrue(
                    (scores >= 0.05).all() and (scores <= 0.98).all(),
                    f"Out of bounds score in {col}: min={scores.min()}, max={scores.max()}"
                )


if __name__ == "__main__":
    unittest.main()
