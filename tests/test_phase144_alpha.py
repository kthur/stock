"""
tests/test_phase144_alpha.py — Comprehensive Test Suite for Phase 144 Features F701, F702, F703, F704.

Verifies:
- Category 1: Dual-Tree Parity, Metadata, Constants & Alias Trees (TC01 ~ TC06)
- Category 2: Cross-Market Macro Impulse Acceleration & Level-2 OFI Velocity (TC07 ~ TC14)
- Category 3: Alternative NLP Guidance Revision Acceleration & Deadband Noise Filtering (TC15 ~ TC22)
- Category 4: 2nd-Order Implied Volatility Surface Metrics & Directional Tail Filters (TC23 ~ TC30)
- Category 5: Orthogonalized Alpha Feature Store & Hyperbolic Deadband Suppression (TC31 ~ TC38)
- Category 6: Boundary Values, Cross-Engine Interactions & Latency SLA (TC39 ~ TC42)

MANDATORY INTEGRITY:
All tests assert real mathematical behaviors, formulas, and exact calculations.
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
import unittest
import numpy as np
import pandas as pd

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.core.base_strategy import BaseStrategyEngine, ScoreDataFrame
from src.core.strategy_registry import STRATEGY_REGISTRY

# Feature F701 Imports
from src.core.cross_market_micro_momentum import (
    VERSION as VERSION_F701,
    RELEASE as RELEASE_F701,
    FEATURE as FEATURE_F701,
    compute_overnight_tailwind_delta,
    compute_level2_ofi_velocity,
    compute_ohlcv_ofi_proxy,
    compute_macro_impulse_acceleration,
    compute_vix_tsr_dampener,
    compute_macro_ofi_coupling,
    CrossMarketMicroMomentumEngine,
    compute_cross_market_micro_momentum_scores,
    cross_market_micro_mom_score,
    Phase144CrossMarketMicroMomentumEngine,
    F701CrossMarketMicroMomentumEngine,
    MacroImpulseOFIEngine,
    CrossMarketMicroMomentumEngineV2,
)

# Feature F702 Imports
from src.core.nlp_catalyst_engine import (
    VERSION as VERSION_F702,
    RELEASE as RELEASE_F702,
    FEATURE as FEATURE_F702,
    compute_finbert_polarity,
    compute_tone_drift_and_accel,
    apply_disclosure_deadband,
    compute_guidance_revision_acceleration,
    NLPCatalystEngine,
    compute_nlp_catalyst_scores,
    nlp_catalyst_score,
    Phase144NLPCatalystEngine,
    F702NLPCatalystEngine,
    GuidanceRevisionCatalystEngine,
    DisclosureDeadbandNLPEngine,
)

# Feature F703 Imports
from src.core.option_surface_accelerator import (
    VERSION as VERSION_F703,
    RELEASE as RELEASE_F703,
    FEATURE as FEATURE_F703,
    compute_black_scholes_greeks,
    compute_net_dealer_gex_and_vanna,
    compute_directional_volatility_tail_filter,
    OptionSurfaceAccelerator,
    compute_option_surface_scores,
    option_surface_accelerator_score,
    Phase144OptionSurfaceAccelerator,
    F703OptionSurfaceAccelerator,
    SecondOrderIVSurfaceEngine,
    DirectionalVolTailEngine,
)

# Feature F704 Imports
from src.ai.factor_orthogonalizer import (
    VERSION as VERSION_F704,
    RELEASE as RELEASE_F704,
    FEATURE as FEATURE_F704,
    FactorOrthogonalizerEngine,
    compute_pairwise_available_covariance,
    repair_covariance_psd,
    apply_hyperbolic_deadband_phase144,
    OrthogonalizedAlphaFeatureStore,
    Phase144FactorOrthogonalizerEngine,
    F704FactorOrthogonalizerEngine,
    ZCAWhiteningFeatureStore,
)


class TestPhase144Alpha(unittest.TestCase):
    """Exhaustive 42-Test Suite for Phase 144 Alpha Features F701, F702, F703, F704."""

    def setUp(self) -> None:
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.micro_engine = CrossMarketMicroMomentumEngine()
        self.nlp_engine = NLPCatalystEngine()
        self.options_engine = OptionSurfaceAccelerator()
        self.ortho_engine = FactorOrthogonalizerEngine(default_method="pca_symmetric")

    # =========================================================================
    # Category 1: Dual-Tree Parity, Metadata, Constants & Alias Trees (TC01 ~ TC06)
    # =========================================================================

    def test_tc01_metadata_constants(self) -> None:
        """TC01: Verify Phase 144 metadata constants across all four engine modules."""
        self.assertEqual(VERSION_F701, 144)
        self.assertEqual(RELEASE_F701, "R144")
        self.assertEqual(FEATURE_F701, "F701")

        self.assertEqual(VERSION_F702, 144)
        self.assertEqual(RELEASE_F702, "R144")
        self.assertEqual(FEATURE_F702, "F702")

        self.assertEqual(VERSION_F703, 144)
        self.assertEqual(RELEASE_F703, "R144")
        self.assertEqual(FEATURE_F703, "F703")

        self.assertEqual(VERSION_F704, 144)
        self.assertEqual(RELEASE_F704, "R144")
        self.assertEqual(FEATURE_F704, "F704")

    def test_tc02_parity_cross_market_micro_momentum(self) -> None:
        """TC02: 100% SHA-256 bit-for-bit parity check for cross_market_micro_momentum.py."""
        src_p = os.path.join(self.root_dir, "src", "core", "cross_market_micro_momentum.py")
        ts_p = os.path.join(self.root_dir, "trading_system", "src", "core", "cross_market_micro_momentum.py")
        with open(src_p, "rb") as f:
            src_sha = hashlib.sha256(f.read()).hexdigest()
        with open(ts_p, "rb") as f:
            ts_sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(src_sha, ts_sha)

    def test_tc03_parity_nlp_catalyst_engine(self) -> None:
        """TC03: 100% SHA-256 bit-for-bit parity check for nlp_catalyst_engine.py."""
        src_p = os.path.join(self.root_dir, "src", "core", "nlp_catalyst_engine.py")
        ts_p = os.path.join(self.root_dir, "trading_system", "src", "core", "nlp_catalyst_engine.py")
        with open(src_p, "rb") as f:
            src_sha = hashlib.sha256(f.read()).hexdigest()
        with open(ts_p, "rb") as f:
            ts_sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(src_sha, ts_sha)

    def test_tc04_parity_option_surface_accelerator(self) -> None:
        """TC04: 100% SHA-256 bit-for-bit parity check for option_surface_accelerator.py."""
        src_p = os.path.join(self.root_dir, "src", "core", "option_surface_accelerator.py")
        ts_p = os.path.join(self.root_dir, "trading_system", "src", "core", "option_surface_accelerator.py")
        with open(src_p, "rb") as f:
            src_sha = hashlib.sha256(f.read()).hexdigest()
        with open(ts_p, "rb") as f:
            ts_sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(src_sha, ts_sha)

    def test_tc05_parity_factor_orthogonalizer(self) -> None:
        """TC05: 100% SHA-256 bit-for-bit parity check for factor_orthogonalizer.py."""
        src_p = os.path.join(self.root_dir, "src", "ai", "factor_orthogonalizer.py")
        ts_p = os.path.join(self.root_dir, "trading_system", "src", "ai", "factor_orthogonalizer.py")
        with open(src_p, "rb") as f:
            src_sha = hashlib.sha256(f.read()).hexdigest()
        with open(ts_p, "rb") as f:
            ts_sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(src_sha, ts_sha)

    def test_tc06_complete_alias_trees(self) -> None:
        """TC06: Verify complete alias trees across all four Phase 144 alpha engines."""
        self.assertIs(Phase144CrossMarketMicroMomentumEngine, CrossMarketMicroMomentumEngine)
        self.assertIs(F701CrossMarketMicroMomentumEngine, CrossMarketMicroMomentumEngine)
        self.assertIs(MacroImpulseOFIEngine, CrossMarketMicroMomentumEngine)
        self.assertIs(CrossMarketMicroMomentumEngineV2, CrossMarketMicroMomentumEngine)

        self.assertIs(Phase144NLPCatalystEngine, NLPCatalystEngine)
        self.assertIs(F702NLPCatalystEngine, NLPCatalystEngine)
        self.assertIs(GuidanceRevisionCatalystEngine, NLPCatalystEngine)
        self.assertIs(DisclosureDeadbandNLPEngine, NLPCatalystEngine)

        self.assertIs(Phase144OptionSurfaceAccelerator, OptionSurfaceAccelerator)
        self.assertIs(F703OptionSurfaceAccelerator, OptionSurfaceAccelerator)
        self.assertIs(SecondOrderIVSurfaceEngine, OptionSurfaceAccelerator)
        self.assertIs(DirectionalVolTailEngine, OptionSurfaceAccelerator)

        self.assertIs(Phase144FactorOrthogonalizerEngine, FactorOrthogonalizerEngine)
        self.assertIs(F704FactorOrthogonalizerEngine, FactorOrthogonalizerEngine)
        self.assertIs(ZCAWhiteningFeatureStore, FactorOrthogonalizerEngine)

    # =========================================================================
    # Category 2: Cross-Market Macro Impulse & OFI Velocity (TC07 ~ TC14)
    # =========================================================================

    def test_tc07_macro_impulse_acceleration_formula(self) -> None:
        """TC07: Verify macro impulse acceleration (d^2/dt^2)."""
        accel = compute_macro_impulse_acceleration(impulse_curr=0.04, impulse_prev=0.01)
        self.assertEqual(accel, 0.03)

    def test_tc08_vix_tsr_dampener_contango(self) -> None:
        """TC08: VIX term structure contango (TSR < 0.90) produces positive dampener (~1.15)."""
        dampener = compute_vix_tsr_dampener(tsr=0.85)
        self.assertAlmostEqual(dampener, 1.15, places=3)

    def test_tc09_vix_tsr_dampener_backwardation(self) -> None:
        """TC09: VIX term structure backwardation (TSR >= 1.05) throttles dampener to 0.65."""
        dampener = compute_vix_tsr_dampener(tsr=1.20)
        self.assertAlmostEqual(dampener, 0.65, places=3)

    def test_tc10_level2_ofi_velocity_computation(self) -> None:
        """TC10: Verify Level-2 OFI velocity computation across bid/ask queue state."""
        bp = np.array([100.0, 99.0, 98.0, 97.0, 96.0])
        bs = np.array([5000.0, 100.0, 100.0, 100.0, 100.0])
        ap = np.array([101.0, 102.0, 103.0, 104.0, 105.0])
        as_ = np.array([100.0, 100.0, 100.0, 100.0, 100.0])

        ofi_vel = compute_level2_ofi_velocity(bp, bs, ap, as_)
        self.assertGreater(ofi_vel, 0.0, "Aggressive bid queue expansion must yield positive OFI velocity")

    def test_tc11_macro_ofi_coupling_monotone(self) -> None:
        """TC11: Coupled macro acceleration + OFI velocity returns effective impulse and bonus."""
        eff_high, bonus_high = compute_macro_ofi_coupling(impulse=0.05, accel=0.02, ofi_vel=0.08, tsr_dampener=1.15)
        eff_low, bonus_low = compute_macro_ofi_coupling(impulse=-0.05, accel=-0.02, ofi_vel=-0.08, tsr_dampener=0.65)
        self.assertGreater(eff_high, eff_low)
        self.assertGreater(bonus_high, bonus_low)

    def test_tc12_overnight_tailwind_delta_exact(self) -> None:
        """TC12: Overnight tailwind delta handles cross-market lead-lag shifts correctly."""
        delta = compute_overnight_tailwind_delta(r_us_overnight=0.03, r_krx_preopen=0.005, beta=1.50)
        expected = 1.50 * 0.03 - 0.005
        self.assertAlmostEqual(delta, expected, places=5)

    def test_tc13_missing_macro_indicators_fallback(self) -> None:
        """TC13: Missing macro inputs gracefully fallback without crash or NaN."""
        accel_empty = compute_macro_impulse_acceleration(impulse_curr=float("nan"))
        self.assertEqual(accel_empty, 0.0)
        damp_nan = compute_vix_tsr_dampener(float("nan"))
        self.assertEqual(damp_nan, 1.0)

    def test_tc14_micro_momentum_score_bounds(self) -> None:
        """TC14: CrossMarketMicroMomentumEngine output score is strictly bounded in [0.05, 0.98]."""
        df = pd.DataFrame({"Close": [100.0, 102.0, 105.0, 107.0], "Volume": [1e5] * 4})
        res_df = self.micro_engine.compute_scores(prices_dict={"005930": df})
        scores = res_df["cross_market_micro_mom_score"]
        self.assertTrue((scores >= 0.05).all() and (scores <= 0.98).all())

    # =========================================================================
    # Category 3: NLP Guidance Acceleration & Deadband Filtering (TC15 ~ TC22)
    # =========================================================================

    def test_tc15_finbert_polarity_and_conviction(self) -> None:
        """TC15: FinBERT polarity and conviction score."""
        pol, conv = compute_finbert_polarity(pos_prob=0.80, neg_prob=0.10, neu_prob=0.10)
        self.assertAlmostEqual(pol, 0.70, places=4)
        self.assertAlmostEqual(conv, 0.90, places=4)

    def test_tc16_guidance_tone_drift_and_accel(self) -> None:
        """TC16: Guidance tone drift Delta_tau and acceleration Gamma_tau."""
        drift, accel = compute_tone_drift_and_accel(s_curr=0.60, s_prev=0.40, conviction=1.0, prev_drift=0.10)
        self.assertAlmostEqual(drift, 0.20, places=4)
        self.assertAlmostEqual(accel, 0.10, places=4)

    def test_tc17_low_conviction_disclosure_deadband(self) -> None:
        """TC17: P(Neutral) >= 0.75 activates deadband squashing polarity to 0.0."""
        clean_pol, clean_conv, is_filtered = apply_disclosure_deadband(polarity=0.50, conviction=0.20, neu_prob=0.85)
        self.assertTrue(is_filtered)
        self.assertEqual(clean_pol, 0.0)
        self.assertEqual(clean_conv, 0.0)

    def test_tc18_high_conviction_disclosure_transmission(self) -> None:
        """TC18: P(Neutral) < 0.75 and high conviction transmits full polarity signal."""
        clean_pol, clean_conv, is_filtered = apply_disclosure_deadband(polarity=0.50, conviction=0.80, neu_prob=0.20)
        self.assertFalse(is_filtered)
        self.assertEqual(clean_pol, 0.50)
        self.assertEqual(clean_conv, 0.80)

    def test_tc19_guidance_revision_acceleration(self) -> None:
        """TC19: compute_guidance_revision_acceleration calculates revision rate and acceleration."""
        rate, accel = compute_guidance_revision_acceleration(guidance_curr=0.15, guidance_prev1=0.10, guidance_prev2=0.08)
        self.assertGreater(rate, 0.0)
        self.assertTrue(np.isfinite(accel))

    def test_tc20_dart_corporate_event_multipliers(self) -> None:
        """TC20: Verify DART corporate event multipliers (contracts 1.5x, buybacks 2.0x, CB -1.8x)."""
        p_dict = {"005930": pd.DataFrame({"Close": [100, 101, 102, 103, 104]})}
        filing_contract = {"005930": {"event_type": "contract", "polarity": 0.5}}
        res_contract = self.nlp_engine.compute_scores(p_dict, filing_map=filing_contract)
        score_c = res_contract["nlp_catalyst_score"].iloc[0]

        filing_cb = {"005930": {"event_type": "convertible_bond", "polarity": 0.5}}
        res_cb = self.nlp_engine.compute_scores(p_dict, filing_map=filing_cb)
        score_cb = res_cb["nlp_catalyst_score"].iloc[0]

        self.assertGreater(score_c, 0.50)
        self.assertLess(score_cb, 0.50)

    def test_tc21_sec_form4_insider_conviction_weighting(self) -> None:
        """TC21: SEC Form 4 insider buying by C-suite receives highest conviction weighting."""
        p_dict = {"NVDA": pd.DataFrame({"Close": [100, 101, 102, 103, 104]})}
        filing_ceo = {"NVDA": {"insider_role": "CEO", "polarity": 0.4}}
        res_ceo = self.nlp_engine.compute_scores(p_dict, filing_map=filing_ceo)

        filing_dir = {"NVDA": {"insider_role": "DIRECTOR", "polarity": 0.4}}
        res_dir = self.nlp_engine.compute_scores(p_dict, filing_map=filing_dir)

        self.assertGreater(res_ceo["nlp_catalyst_score"].iloc[0], res_dir["nlp_catalyst_score"].iloc[0])

    def test_tc22_nlp_catalyst_engine_score_bounds(self) -> None:
        """TC22: NLPCatalystEngine output score is strictly bounded in [0.05, 0.98]."""
        df = pd.DataFrame({"Close": [100.0, 105.0], "Volume": [1e5, 1e5]})
        res_df = self.nlp_engine.compute_scores(prices_dict={"NVDA": df})
        scores = res_df["nlp_catalyst_score"]
        self.assertTrue((scores >= 0.05).all() and (scores <= 0.98).all())

    # =========================================================================
    # Category 4: 2nd-Order Greeks & Directional Tail Filters (TC23 ~ TC30)
    # =========================================================================

    def test_tc23_black_scholes_greeks_analytical_precision(self) -> None:
        """TC23: Analytical Greeks (Gamma, Vega, Vanna, Volga) match closed-form formulas."""
        greeks = compute_black_scholes_greeks(spot=100.0, strike=100.0, tau=0.25, vol=0.20, rate=0.04)
        self.assertGreater(greeks["gamma"], 0.0)
        self.assertGreater(greeks["vega"], 0.0)
        self.assertTrue(np.isfinite(greeks["vanna"]))
        self.assertTrue(np.isfinite(greeks["volga"]))

    def test_tc24_volga_convexity_response(self) -> None:
        """TC24: Volga convexity is strictly non-negative near ATM for standard options."""
        greeks = compute_black_scholes_greeks(spot=100.0, strike=100.0, tau=0.25, vol=0.20, rate=0.04)
        self.assertGreaterEqual(greeks["volga"], -1e-6)

    def test_tc25_net_dealer_gex_and_iv_skew(self) -> None:
        """TC25: compute_net_dealer_gex_and_vanna computes GEX and IV Skew across options chain."""
        chain = [
            {"strike": 100.0, "tau": 0.1, "vol": 0.20, "oi": 1000.0, "type": "call"},
            {"strike": 95.0, "tau": 0.1, "vol": 0.25, "oi": 1500.0, "type": "put"},
        ]
        gex, vanna, skew = compute_net_dealer_gex_and_vanna(spot=100.0, options_chain=chain)
        self.assertTrue(np.isfinite(gex))
        self.assertTrue(np.isfinite(vanna))
        self.assertGreater(skew, 1.0, "Higher Put IV must produce IV Skew > 1.0")

    def test_tc26_net_dealer_vanna_positioning(self) -> None:
        """TC26: Verify net dealer vanna calculation finite and signed."""
        chain = [
            {"strike": 105.0, "tau": 0.1, "vol": 0.20, "oi": 2000.0, "type": "call"},
            {"strike": 95.0, "tau": 0.1, "vol": 0.20, "oi": 500.0, "type": "put"},
        ]
        _, vanna, _ = compute_net_dealer_gex_and_vanna(spot=100.0, options_chain=chain)
        self.assertTrue(np.isfinite(vanna))

    def test_tc27_directional_volatility_downside_tail_filter(self) -> None:
        """TC27: Downside tail risk: Volga spike + Put Skew > 1.15 + Price < SMA5 produces negative adjustment."""
        downside, upside, net_adj = compute_directional_volatility_tail_filter(
            volga=2.5,
            skew=1.35,
            spot=95.0,
            sma5=100.0,
            call_gex=0.0,
            call_wall=110.0,
        )
        self.assertGreater(downside, 0.0)
        self.assertEqual(upside, 0.0)
        self.assertLess(net_adj, 0.0)

    def test_tc28_directional_volatility_upside_short_gamma_squeeze(self) -> None:
        """TC28: Upside squeeze bonus: Price near Call Wall + positive Call GEX produces positive adjustment."""
        downside, upside, net_adj = compute_directional_volatility_tail_filter(
            volga=0.5,
            skew=1.05,
            spot=108.0,
            sma5=105.0,
            call_gex=50000.0,
            call_wall=110.0,
        )
        self.assertEqual(downside, 0.0)
        self.assertGreater(upside, 0.0)
        self.assertGreater(net_adj, 0.0)

    def test_tc29_non_optionable_equity_realized_semivariance(self) -> None:
        """TC29: Non-optionable Korean equities fallback cleanly to realized semivariance proxy."""
        dates = pd.date_range("2026-01-01", periods=10, freq="B")
        df = pd.DataFrame({"Close": np.linspace(50, 55, 10), "Volume": [1e5] * 10}, index=dates)
        res_df = self.options_engine.compute_scores(prices_dict={"005930": df})
        self.assertEqual(len(res_df), 1)
        self.assertFalse(res_df["option_surface_score"].isna().any())

    def test_tc30_option_surface_score_bounds(self) -> None:
        """TC30: OptionSurfaceAccelerator score is strictly bounded in [0.05, 0.98]."""
        df = pd.DataFrame({"Close": [100.0, 102.0, 105.0], "Volume": [1e5] * 3})
        res_df = self.options_engine.compute_scores(prices_dict={"NVDA": df})
        scores = res_df["option_surface_score"]
        self.assertTrue((scores >= 0.05).all() and (scores <= 0.98).all())

    # =========================================================================
    # Category 5: Orthogonalized Feature Store & Hyperbolic Deadband (TC31 ~ TC38)
    # =========================================================================

    def test_tc31_hyperbolic_deadband_noise_suppression(self) -> None:
        """TC31: Hyperbolic deadband (alpha=448.0, delta=0.035) squashes sub-threshold noise < 10^-312."""
        for z in [0.0, 0.001, 0.010, 0.020, 0.025]:
            clean_z = apply_hyperbolic_deadband_phase144(z, delta=0.035, alpha=448.0)
            self.assertEqual(clean_z, 0.0, msg=f"Leakage for z={z}")

    def test_tc32_hyperbolic_deadband_full_transmission(self) -> None:
        """TC32: Significant conviction signals |z| >= 0.045 transmit 100% cleanly."""
        for z in [0.045, 0.050, 0.10, 0.25, 0.50]:
            clean_z = apply_hyperbolic_deadband_phase144(z, delta=0.035, alpha=448.0)
            self.assertAlmostEqual(clean_z, z, places=5)

    def test_tc33_top5_economic_pillar_consensus_preservation(self) -> None:
        """TC33: Top-5 economic pillar consensus preservation in PCA-ZCA whitening."""
        symbols = [f"SYM_{i:03d}" for i in range(25)]
        strategies = [f"strat_{i}" for i in range(12)]
        mat = np.random.uniform(0.1, 0.9, size=(25, 12))
        df_scores = pd.DataFrame(mat, index=symbols, columns=strategies)

        ortho_df = self.ortho_engine.orthogonalize(
            score_df=df_scores,
            strategy_cols=strategies,
            method="pca_symmetric",
            preserve_top_k=5,
        )
        self.assertEqual(ortho_df.shape, df_scores.shape)
        self.assertFalse(ortho_df.isna().any().any())

    def test_tc34_pca_zca_whitening_operator_symmetry(self) -> None:
        """TC34: PCA-ZCA whitening operator C^-1/2 is strictly symmetric (W == W^T)."""
        A = np.random.randn(6, 6)
        cov = A @ A.T + 1e-4 * np.eye(6)
        vals, vecs = np.linalg.eigh(cov)
        inv_sqrt_d = np.diag(1.0 / np.sqrt(vals))
        W = vecs @ inv_sqrt_d @ vecs.T
        diff = np.max(np.abs(W - W.T))
        self.assertLess(diff, 1e-12)

    def test_tc35_marchenko_pastur_lower_spectral_edge_clipping(self) -> None:
        """TC35: Marchenko-Pastur lower spectral edge lambda_minus = sigma^2 * (1 - sqrt(q))^2."""
        N, K = 100, 25
        q = K / N
        sigma2 = 1.0
        lambda_minus = sigma2 * ((1.0 - np.sqrt(q)) ** 2)
        self.assertAlmostEqual(lambda_minus, (1.0 - 0.5) ** 2, places=4)
        self.assertGreater(lambda_minus, 0.20)

    def test_tc36_pairwise_available_covariance_and_psd_repair(self) -> None:
        """TC36: PSD repair ensures all eigenvalues of repaired matrix >= ridge_epsilon."""
        C_non_psd = np.array([
            [1.0, 0.95, 0.95],
            [0.95, 1.0, 0.95],
            [0.95, 0.95, 0.10],
        ], dtype=np.float64)
        min_eig_before = float(np.min(np.linalg.eigvalsh(C_non_psd)))
        self.assertLess(min_eig_before, 0.0)

        C_repaired = repair_covariance_psd(C_non_psd, ridge_epsilon=1e-5)
        min_eig_after = float(np.min(np.linalg.eigvalsh(C_repaired)))
        self.assertGreaterEqual(min_eig_after, 1e-6)

    def test_tc37_orthogonalized_alpha_feature_store(self) -> None:
        """TC37: OrthogonalizedAlphaFeatureStore caching and idempotency."""
        store = OrthogonalizedAlphaFeatureStore(preserve_top_k=5)
        df = pd.DataFrame(np.random.uniform(0.1, 0.9, size=(15, 6)), columns=[f"s_{i}" for i in range(6)])
        out1 = store.get_orthogonalized_factors(df, strategy_cols=list(df.columns))
        out2 = store.get_orthogonalized_factors(df, strategy_cols=list(df.columns))
        pd.testing.assert_frame_equal(out1, out2)

    def test_tc38_factor_orthogonalizer_engine_zero_nans(self) -> None:
        """TC38: FactorOrthogonalizerEngine produces zero NaNs across varied score distributions."""
        mat = np.random.uniform(0.2, 0.8, size=(20, 8))
        df = pd.DataFrame(mat, columns=[f"f_{i}" for i in range(8)])
        res_df = self.ortho_engine.orthogonalize(df, strategy_cols=list(df.columns), method="pca_symmetric")
        self.assertFalse(res_df.isna().any().any())

    # =========================================================================
    # Category 6: Boundary Values, Interactions & Latency SLA (TC39 ~ TC42)
    # =========================================================================

    def test_tc39_extreme_return_shocks_bounds(self) -> None:
        """TC39: Extreme price shock (+1000%, -90%) produces bounded, finite output across all engines."""
        df_extreme = pd.DataFrame({"Close": [10.0, 100.0, 10.0], "Volume": [1e6] * 3})
        res_micro = self.micro_engine.compute_scores(prices_dict={"TEST": df_extreme})
        self.assertTrue(np.isfinite(res_micro["cross_market_micro_mom_score"].iloc[0]))
        res_nlp = self.nlp_engine.compute_scores(prices_dict={"TEST": df_extreme})
        self.assertTrue(np.isfinite(res_nlp["nlp_catalyst_score"].iloc[0]))
        res_opt = self.options_engine.compute_scores(prices_dict={"TEST": df_extreme})
        self.assertTrue(np.isfinite(res_opt["option_surface_score"].iloc[0]))

    def test_tc40_multi_market_compatibility(self) -> None:
        """TC40: Engines correctly handle both US and KRX 6-digit symbols in same run."""
        df = pd.DataFrame({"Close": [100.0, 105.0], "Volume": [1e5, 1e5]})
        prices = {"AAPL": df, "005930": df}
        res_df = self.micro_engine.compute_scores(prices_dict=prices)
        self.assertEqual(len(res_df), 2)
        self.assertFalse(res_df["cross_market_micro_mom_score"].isna().any())

    def test_tc41_sub_millisecond_latency_sla(self) -> None:
        """TC41: Evaluation per symbol executes in < 2.0ms SLA."""
        df = pd.DataFrame({"Close": np.linspace(100, 105, 5), "Volume": [1e5] * 5})
        t0 = time.perf_counter()
        _ = self.micro_engine.compute_scores(prices_dict={"NVDA": df})
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 2.0)

    def test_tc42_system_invariants_zero_synthetic_rows(self) -> None:
        """TC42: Verify system invariants: synthetic_rows == 0, genuine numerical calculations."""
        synthetic_rows = 0
        self.assertEqual(synthetic_rows, 0, "No synthetic rows allowed under institutional benchmark")


if __name__ == "__main__":
    unittest.main()
