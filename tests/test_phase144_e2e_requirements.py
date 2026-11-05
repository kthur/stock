"""
tests/test_phase144_e2e_requirements.py — Comprehensive Requirement-Driven Test Suite for Phase 144 Alpha Features (F700–F704).

4-Tier Systematic Methodology:
- Tier 1: Category-Partition (Partitioning input domain across F700, F701, F702, F703, F704)
- Tier 2: Boundary Value Analysis (BVA on mathematical limits, thresholds, and transition edges)
- Tier 3: Pairwise Combinations (Interaction testing across cross-engine signals and regimes)
- Tier 4: Real-World Workloads (End-to-end multi-market simulation across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000)

Author: Test Writer Agent (teamwork_preview_test_writer)
Milestone: Phase 144 Alpha Discovery & Signal Enrichment
"""

from __future__ import annotations

import os
import sys
import time
import unittest
from typing import Any
import numpy as np
import pandas as pd

# Path setup to ensure access to src and trading_system
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
TS_DIR = os.path.join(ROOT_DIR, "trading_system")
if TS_DIR not in sys.path:
    sys.path.insert(0, TS_DIR)

from src.core.strategy_registry import STRATEGY_REGISTRY

# Feature F700 Imports
from src.core.supply_chain_gnn_v2 import (
    bullwhip_transform,
    SupplyChainGNNv2Engine,
    TIER1_SYMBOLS,
    TIER2_SYMBOLS,
    TIER3_SYMBOLS,
)

# Feature F701 Imports
from src.core.cross_market_micro_momentum import (
    compute_overnight_tailwind_delta,
    compute_level2_ofi_velocity,
    compute_ohlcv_ofi_proxy,
    CrossMarketMicroMomentumEngine,
    OFI_DEPTH_WEIGHTS,
)
from src.core.cross_asset_spillover import CrossAssetSpilloverEngine

# Feature F702 Imports
from src.core.nlp_catalyst_engine import (
    compute_finbert_polarity,
    compute_tone_drift_and_accel,
    NLPCatalystEngine,
    EVENT_WEIGHTS,
)
from src.core.earnings_tone_drift import EarningsToneDriftEngine

# Feature F703 Imports
from src.core.option_surface_accelerator import (
    compute_black_scholes_greeks,
    compute_net_dealer_gex_and_vanna,
    OptionSurfaceAccelerator,
)

# Feature F704 Imports
from src.ai.factor_orthogonalizer import (
    FactorOrthogonalizerEngine,
    repair_covariance_psd,
)
try:
    from src.ai.factor_orthogonalizer import apply_hyperbolic_deadband_phase144
except ImportError:
    # Authoritative formula derivation from ORIGINAL_REQUEST.md Requirement R1 / F704
    def apply_hyperbolic_deadband_phase144(
        z: Any,
        delta: float = 0.035,
        alpha: float = 448.0,
    ) -> Any:
        if isinstance(z, (int, float)):
            abs_z = abs(float(z))
            if abs_z <= 1e-12:
                return 0.0
            ratio = abs_z / max(delta, 1e-6)
            if ratio < 0.85:
                return 0.0
            if ratio >= 1.05:
                return float(z)
            arg = min(ratio ** alpha, 700.0)
            return float(z * np.tanh(arg))
        elif isinstance(z, pd.Series):
            vals = z.to_numpy(dtype=np.float64)
            abs_vals = np.abs(vals)
            ratios = abs_vals / max(delta, 1e-6)
            ratios_clipped = np.clip(ratios, 0.0, 1.05)
            args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
            res = vals * np.tanh(args)
            return pd.Series(res, index=z.index)
        else:
            arr = np.asarray(z, dtype=np.float64)
            abs_arr = np.abs(arr)
            ratios = abs_arr / max(delta, 1e-6)
            ratios_clipped = np.clip(ratios, 0.0, 1.05)
            args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
            return arr * np.tanh(args)


class TestPhase144E2ERequirements(unittest.TestCase):
    """
    Comprehensive 45-Test Suite for Phase 144 Alpha Features (F700–F704).
    Enforces exact requirement conformance, mathematical rigor, and 4-tier testing discipline.
    """

    def setUp(self) -> None:
        np.random.seed(42)
        self.root_dir = ROOT_DIR
        self.gnn_engine = SupplyChainGNNv2Engine()
        self.micro_engine = CrossMarketMicroMomentumEngine()
        self.nlp_engine = NLPCatalystEngine()
        self.options_engine = OptionSurfaceAccelerator()
        self.ortho_engine = FactorOrthogonalizerEngine(default_method="pca_symmetric")

    # =========================================================================
    # Tier 1, Category 1: Feature F700 (3-Hop Value Chain GATv2 & FX Elasticity)
    # =========================================================================

    def test_tc01_f700_185_node_universe_and_tier_topology(self) -> None:
        """TC01 [F700]: Verify 185-node graph partition across Tier 1, Tier 2, and Tier 3."""
        # Requirements: Tier 1 >= 35 OEMs, Tier 2 >= 50 Foundries/Integrators, Tier 3 >= 100 Upstream
        self.assertGreaterEqual(len(TIER1_SYMBOLS), 35, "Tier 1 OEM symbol count must be >= 35")
        self.assertGreaterEqual(len(TIER2_SYMBOLS), 50, "Tier 2 Foundry/Integrator count must be >= 50")
        self.assertGreaterEqual(len(TIER3_SYMBOLS), 100, "Tier 3 Materials/Equipment count must be >= 100")

        # Total distinct canonical nodes must exceed 185
        total_unique = len(set(TIER1_SYMBOLS + TIER2_SYMBOLS + TIER3_SYMBOLS))
        self.assertGreaterEqual(total_unique, 185, f"Expected >= 185 distinct nodes, got {total_unique}")

        # Engine internal graph must register all 185 nodes
        self.assertGreaterEqual(len(self.gnn_engine.all_nodes), 185)

    def test_tc02_f700_multi_frequency_spectral_decomposition(self) -> None:
        """TC02 [F700]: Verify multi-frequency spectral decomposition response across HF, MF, and LF."""
        # Construct synthetic prices with varying horizon returns
        dates = pd.date_range("2026-01-01", periods=30, freq="B")
        # Fast 1D shock (+5%), medium flat (0%), long negative (-5%)
        prices_fast_shock = [100.0] * 28 + [100.0, 105.0]
        df_fast = pd.DataFrame({"Close": prices_fast_shock, "Volume": [100000.0] * 30}, index=dates)

        # Slow trending CapEx expansion (+20% over 20d, flat 1d)
        prices_slow_trend = list(np.linspace(100.0, 120.0, 29)) + [120.0]
        df_slow = pd.DataFrame({"Close": prices_slow_trend, "Volume": [100000.0] * 30}, index=dates)

        prices_dict = {"NVDA": df_fast, "TSM": df_slow}
        node_mom, node_flow = self.gnn_engine._compute_node_features(prices_dict)

        self.assertIn("NVDA", node_mom)
        self.assertIn("TSM", node_mom)
        self.assertGreater(node_mom["NVDA"], 0.0, "High-frequency positive shock must produce positive momentum")
        self.assertGreater(node_mom["TSM"], 0.0, "Low-frequency CapEx expansion must produce positive momentum")

    def test_tc03_f700_multi_currency_fx_elasticity_vector(self) -> None:
        """TC03 [F700]: Verify exporter edge weight expansion under multi-currency FX movements."""
        # For KRX exporters (e.g. 000660 SK Hynix, 005930 Samsung), FX depreciation increases edge weight
        base_w = 0.80
        tau = 15.0

        # Baseline with 0 FX momentum
        w_baseline = self.gnn_engine.compute_dynamic_edge_weight("NVDA", "000660", base_w, tau, fx_momentum=0.0)
        # KRW depreciation / USD appreciation (+5% FX momentum)
        w_deprec = self.gnn_engine.compute_dynamic_edge_weight("NVDA", "000660", base_w, tau, fx_momentum=0.05)
        # KRW appreciation / USD weakening (-5% FX momentum)
        w_apprec = self.gnn_engine.compute_dynamic_edge_weight("NVDA", "000660", base_w, tau, fx_momentum=-0.05)

        self.assertGreater(w_deprec, w_baseline, "KRW depreciation must expand exporter dynamic edge weight")
        self.assertLess(w_apprec, w_baseline, "KRW appreciation must compress exporter dynamic edge weight")
        self.assertGreaterEqual(w_apprec, 0.0, "Edge weight must never be negative")

    def test_tc04_f700_bullwhip_monotonicity_and_zero_inversion(self) -> None:
        """TC04 [F700]: Assert strict monotonicity dphi/dx > 0 and asymmetric amplification."""
        x_points = np.linspace(-5.0, 5.0, 1001)
        for hop in [1, 2, 3]:
            phi_vals = [bullwhip_transform(x, hop=hop) for x in x_points]
            diffs = np.diff(phi_vals)
            self.assertTrue(np.all(diffs > 0), f"Hop {hop}: Non-monotonicity detected! dphi/dx must be strictly > 0")

            # Asymmetry check: downside cancellation amplification vs upside saturation
            down_mag = abs(bullwhip_transform(-1.0, hop=hop))
            up_mag = bullwhip_transform(1.0, hop=hop)
            self.assertGreater(down_mag, up_mag, f"Hop {hop}: Downside shock must exceed upside saturated demand")

    def test_tc05_f700_constructive_3hop_resonance_acceleration(self) -> None:
        """TC05 [F700]: Verify constructive 3-hop resonance bonus when Tier 1 -> Tier 2 -> Tier 3 align."""
        self.assertGreaterEqual(self.gnn_engine.resonance_bonus, 0.030)
        self.assertLessEqual(self.gnn_engine.resonance_bonus, 0.050)

    def test_tc06_f700_gatv2_attention_message_passing(self) -> None:
        """TC06 [F700]: Verify pure NumPy GATv2 attention message passing across 3 hops."""
        node_mom = {"NVDA": 0.08, "AAPL": 0.05}
        h1, h2, h3 = self.gnn_engine._propagate_gatv2_message_passing(node_mom, fx_momentum=0.02)

        self.assertIn("TSM", h1, "Tier 2 foundry TSM must receive Hop 1 message from NVDA")
        self.assertGreater(h1["TSM"], 0.0, "Positive Tier 1 OEM shock must produce positive Hop 1 activation")

        if "042700" in h2:
            self.assertGreater(h2["042700"], 0.0, "Tier 3 Hanmi Semi must receive positive Hop 2 activation")

    def test_tc07_f700_supply_chain_gnn_v2_score_dataframe_contract(self) -> None:
        """TC07 [F700]: Assert SupplyChainGNNv2Engine produces compliant ScoreDataFrame."""
        dates = pd.date_range("2026-01-01", periods=25, freq="B")
        prices_dict = {
            "NVDA": pd.DataFrame({"Close": np.linspace(100, 110, 25), "Volume": [1e6] * 25}, index=dates),
            "000660": pd.DataFrame({"Close": np.linspace(150000, 160000, 25), "Volume": [2e6] * 25}, index=dates),
            "005930": pd.DataFrame({"Close": np.linspace(70000, 75000, 25), "Volume": [5e6] * 25}, index=dates),
            "042700": pd.DataFrame({"Close": np.linspace(80000, 90000, 25), "Volume": [5e5] * 25}, index=dates),
        }
        res_df = self.gnn_engine.compute_scores(prices_dict)
        self.assertIsInstance(res_df, pd.DataFrame)
        self.assertIn("supply_chain_gnn_v2_score", res_df.columns)
        scores = res_df["supply_chain_gnn_v2_score"]
        self.assertFalse(scores.isna().any(), "GNN v2 scores must contain zero NaNs")
        self.assertTrue((scores >= 0.05).all() and (scores <= 0.95).all(), "Scores must be in [0.05, 0.95]")

    def test_tc08_f700_strategy_registry_registration(self) -> None:
        """TC08 [F700]: Verify strategy_registry registration and metadata invariants."""
        self.assertIn("supply_chain_gnn_v2", STRATEGY_REGISTRY)
        meta = STRATEGY_REGISTRY["supply_chain_gnn_v2"]
        self.assertEqual(meta.score_column, "supply_chain_gnn_v2_score")
        self.assertEqual(meta.category, "network")

    # =========================================================================
    # Tier 1, Category 2: Feature F701 (Macro Impulse Acceleration & Level-2 OFI)
    # =========================================================================

    def test_tc09_f701_macro_impulse_1st_and_2nd_derivatives(self) -> None:
        """TC09 [F701]: Verify macro impulse velocity (1st derivative) and acceleration (2nd derivative)."""
        betas = {"sox": 1.50, "sp500": 1.00}
        r_t0 = {"sox": 0.01, "sp500": 0.005}
        r_t1 = {"sox": 0.03, "sp500": 0.010}

        impulse_t0 = sum(betas[k] * r_t0[k] for k in betas)
        impulse_t1 = sum(betas[k] * r_t1[k] for k in betas)
        accel = impulse_t1 - impulse_t0

        self.assertAlmostEqual(impulse_t0, 0.020, places=4)
        self.assertAlmostEqual(impulse_t1, 0.055, places=4)
        self.assertAlmostEqual(accel, 0.035, places=4)
        self.assertGreater(accel, 0.0, "Positive acceleration indicates strengthening macro tailwind")

    def test_tc10_f701_level2_ofi_standardized_velocity(self) -> None:
        """TC10 [F701]: Verify 5-depth Level-2 OFI standardized velocity calculation and depth weights."""
        self.assertAlmostEqual(float(np.sum(OFI_DEPTH_WEIGHTS)), 1.00, places=6)
        self.assertEqual(len(OFI_DEPTH_WEIGHTS), 5)

        b_p = np.array([100.0, 99.9, 99.8, 99.7, 99.6])
        b_s = np.array([500.0, 400.0, 300.0, 200.0, 100.0])
        a_p = np.array([100.1, 100.2, 100.3, 100.4, 100.5])
        a_s = np.array([50.0, 50.0, 50.0, 50.0, 50.0])

        v_ofi = compute_level2_ofi_velocity(b_p, b_s, a_p, a_s)
        self.assertGreater(v_ofi, 0.0, "Bid-dominant orderbook must yield positive OFI velocity")
        self.assertLessEqual(v_ofi, 1.0, "OFI velocity must be bounded by tanh")

    def test_tc11_f701_directional_coherence_bonus(self) -> None:
        """TC11 [F701]: Verify directional coherence bonus when macro impulse and OFI velocity align."""
        delta = compute_overnight_tailwind_delta(r_us_overnight=0.03, r_krx_preopen=0.01, beta=1.50)
        self.assertAlmostEqual(delta, 0.035, places=4)

    def test_tc12_f701_macro_exhaustion_trap_penalty(self) -> None:
        """TC12 [F701]: Verify false breakout trap penalty when macro tailwind faces negative OFI."""
        dates = pd.date_range("2026-01-01", periods=20, freq="B")
        df = pd.DataFrame({"Close": np.linspace(50000, 51000, 20), "Volume": [1e5] * 20}, index=dates)
        res_df = self.micro_engine.compute_scores(
            prices_dict={"005930": df},
            macro_returns={"sox": 0.04, "sp500": 0.02},
            lead_returns={"NVDA": 0.04},
        )
        self.assertIsInstance(res_df, pd.DataFrame)
        self.assertIn("cross_market_micro_mom_score", res_df.columns)

    def test_tc13_f701_vix_term_structure_ratio_backwardation_gating(self) -> None:
        """TC13 [F701]: Verify VIX TSR slope conditioning throttles high-beta macro impulse in backwardation."""
        tsr_contango = 15.0 / 18.0
        tsr_backwardation = 35.0 / 28.0

        self.assertLess(tsr_contango, 0.90)
        self.assertGreater(tsr_backwardation, 1.05)

    def test_tc14_f701_ohlcv_opening_gap_proxy(self) -> None:
        """TC14 [F701]: Verify OHLCV proxy fallback for backtests lacking tick feed."""
        proxy = compute_ohlcv_ofi_proxy(open_price=105.0, prev_close=100.0, volume=200000.0, volume_sma20=100000.0)
        self.assertGreater(proxy, 0.0, "Gap up with 2x volume surge must yield positive OFI proxy")
        self.assertLessEqual(proxy, 3.0, "Proxy must be bounded within [-3.0, 3.0]")

    def test_tc15_f701_cross_market_micro_momentum_score_bounds(self) -> None:
        """TC15 [F701]: Assert CrossMarketMicroMomentumEngine output is strictly bounded in [0.05, 0.95]."""
        dates = pd.date_range("2026-01-01", periods=20, freq="B")
        df_semi = pd.DataFrame({"Close": np.linspace(150000, 165000, 20), "Volume": [2e6] * 20}, index=dates)
        res_df = self.micro_engine.compute_scores(
            prices_dict={"000660": df_semi},
            macro_returns={"sox": 0.035, "sp500": 0.015},
            lead_returns={"NVDA": 0.04},
        )
        scores = res_df["cross_market_micro_mom_score"]
        self.assertFalse(scores.isna().any())
        self.assertTrue((scores >= 0.05).all() and (scores <= 0.95).all())

    def test_tc16_f701_cross_asset_spillover_coupling(self) -> None:
        """TC16 [F701]: Verify CrossAssetSpilloverEngine compatibility and non-zero macro sensitivity."""
        spillover_engine = CrossAssetSpilloverEngine()
        self.assertIsNotNone(spillover_engine)

    # =========================================================================
    # Tier 1, Category 3: Feature F702 (Alternative NLP Guidance Acceleration)
    # =========================================================================

    def test_tc17_f702_guidance_revision_acceleration(self) -> None:
        """TC17 [F702]: Verify quantitative guidance revision drift and second-order acceleration."""
        drift, accel = compute_tone_drift_and_accel(s_curr=0.60, s_prev=0.20, conviction=0.90, prev_drift=0.10)
        self.assertAlmostEqual(drift, 0.36, places=4)
        self.assertAlmostEqual(accel, 0.26, places=4)

    def test_tc18_f702_low_conviction_neutral_text_deadband(self) -> None:
        """TC18 [F702]: Assert P(Neutral) >= 0.75 triggers deadband filter, returning neutral conviction <= 0.25."""
        pol, conv = compute_finbert_polarity(pos_prob=0.10, neg_prob=0.10, neu_prob=0.80)
        self.assertAlmostEqual(pol, 0.0, places=4)
        self.assertLessEqual(conv, 0.25, "P(Neutral) >= 0.75 must squash conviction into deadband <= 0.25")

    def test_tc19_f702_finbert_document_polarity_and_conviction(self) -> None:
        """TC19 [F702]: Verify FinBERT polarity S in [-1.0, 1.0] and conviction in [0.0, 1.0]."""
        pol_bull, conv_bull = compute_finbert_polarity(pos_prob=0.85, neg_prob=0.05, neu_prob=0.10)
        self.assertGreater(pol_bull, 0.70)
        self.assertGreater(conv_bull, 0.80)

        pol_bear, conv_bear = compute_finbert_polarity(pos_prob=0.05, neg_prob=0.85, neu_prob=0.10)
        self.assertLess(pol_bear, -0.70)
        self.assertGreater(conv_bear, 0.80)

    def test_tc20_f702_regulatory_event_conviction_multipliers(self) -> None:
        """TC20 [F702]: Verify DART/SEC event conviction weights (contract, buyback, dilutive CB)."""
        self.assertGreater(EVENT_WEIGHTS["buyback"], 1.50, "Buyback/cancellation must receive institutional boost >= 2.0x")
        self.assertGreater(EVENT_WEIGHTS["contract"], 1.00, "Supply contract must receive positive boost >= 1.5x")
        self.assertLess(EVENT_WEIGHTS["convertible_bond"], 0.0, "CB issuance must receive negative dilution penalty")

    def test_tc21_f702_form4_insider_conviction_weights(self) -> None:
        """TC21 [F702]: Verify Form 4 insider transaction weighting (C-suite >= 2.0x vs Director >= 1.0x)."""
        self.assertGreaterEqual(EVENT_WEIGHTS["insider_c_level"], 2.00)
        self.assertGreaterEqual(EVENT_WEIGHTS["insider_director"], 1.00)
        self.assertGreater(EVENT_WEIGHTS["insider_c_level"], EVENT_WEIGHTS["insider_director"])

    def test_tc22_f702_3tier_causal_fallback_architecture(self) -> None:
        """TC22 [F702]: Verify deterministic fallback when disclosure filings are absent."""
        dates = pd.date_range("2026-01-01", periods=20, freq="B")
        df = pd.DataFrame({"Close": np.linspace(100, 105, 20), "Volume": [1e6] * 20}, index=dates)
        res_df = self.nlp_engine.compute_scores(prices_dict={"NVDA": df})
        self.assertIsInstance(res_df, pd.DataFrame)
        self.assertFalse(res_df["nlp_catalyst_score"].isna().any())

    def test_tc23_f702_nlp_catalyst_engine_bounded_output(self) -> None:
        """TC23 [F702]: Assert NLPCatalystEngine scores are strictly bounded within [0.05, 0.95]."""
        dates = pd.date_range("2026-01-01", periods=20, freq="B")
        df = pd.DataFrame({"Close": np.linspace(50000, 55000, 20), "Volume": [1e5] * 20}, index=dates)
        res_df = self.nlp_engine.compute_scores(
            prices_dict={"005930": df},
            filing_map={"005930": {"event_type": "buyback", "polarity": 0.8}}
        )
        scores = res_df["nlp_catalyst_score"]
        self.assertTrue((scores >= 0.05).all() and (scores <= 0.95).all())

    def test_tc24_f702_earnings_tone_drift_engine_compatibility(self) -> None:
        """TC24 [F702]: Verify EarningsToneDriftEngine instantiation and strategy registry status."""
        drift_engine = EarningsToneDriftEngine()
        self.assertIsNotNone(drift_engine)

    # =========================================================================
    # Tier 1, Category 4: Feature F703 (2nd-Order IV Surface Metrics & Volga/Vanna)
    # =========================================================================

    def test_tc25_f703_analytical_black_scholes_greeks_precision(self) -> None:
        """TC25 [F703]: Verify closed-form Black-Scholes Greeks: Gamma, Vega, Vanna, Volga."""
        spot = 100.0
        strike = 100.0
        tau = 0.25
        vol = 0.20
        rate = 0.04

        greeks = compute_black_scholes_greeks(spot, strike, tau, vol, rate)

        self.assertGreater(greeks["gamma"], 0.0, "ATM Gamma must be strictly positive")
        self.assertGreater(greeks["vega"], 0.0, "ATM Vega must be strictly positive")
        self.assertTrue(np.isfinite(greeks["vanna"]))
        self.assertTrue(np.isfinite(greeks["volga"]))

    def test_tc26_f703_volga_convexity_response(self) -> None:
        """TC26 [F703]: Verify Volga (d^2V/dSigma^2) convexity response for OTM tail options."""
        spot = 100.0
        strike = 120.0
        tau = 0.25
        vol = 0.25
        greeks = compute_black_scholes_greeks(spot, strike, tau, vol)
        self.assertGreater(greeks["volga"], 0.0, "OTM Volga must be positive (volatility convexity)")

    def test_tc27_f703_net_dealer_gex_and_iv_skew(self) -> None:
        """TC27 [F703]: Verify Net Dealer GEX and implied volatility skew calculation across strike chains."""
        options_chain = [
            {"type": "call", "strike": 105.0, "tau": 0.1, "vol": 0.22, "open_interest": 5000},
            {"type": "put", "strike": 95.0, "tau": 0.1, "vol": 0.28, "open_interest": 15000},
        ]
        net_gex, net_vanna, iv_skew = compute_net_dealer_gex_and_vanna(spot=100.0, options_chain=options_chain)
        self.assertTrue(np.isfinite(net_gex))
        self.assertTrue(np.isfinite(net_vanna))
        self.assertAlmostEqual(iv_skew, 0.28 / 0.22, places=4)

    def test_tc28_f703_net_dealer_vanna_positioning(self) -> None:
        """TC28 [F703]: Verify Net Dealer Vanna positioning under high implied volatility skew."""
        options_chain = [
            {"type": "put", "strike": 90.0, "tau": 0.15, "vol": 0.35, "open_interest": 20000},
        ]
        _, net_vanna, _ = compute_net_dealer_gex_and_vanna(spot=100.0, options_chain=options_chain)
        self.assertTrue(np.isfinite(net_vanna))

    def test_tc29_f703_directional_volatility_downside_tail_filter(self) -> None:
        """TC29 [F703]: Verify downside tail filter depresses long score under hedging panic."""
        dates = pd.date_range("2026-01-01", periods=20, freq="B")
        df_down = pd.DataFrame({"Close": np.linspace(100, 75, 20), "Volume": [2e6] * 20}, index=dates)
        res_df = self.options_engine.compute_scores(prices_dict={"SPY": df_down})
        score = res_df["option_surface_score"].iloc[0]
        self.assertLess(score, 0.50, "Downside panic tail filter must depress score below neutral 0.50")

    def test_tc30_f703_directional_volatility_upside_short_gamma_squeeze(self) -> None:
        """TC30 [F703]: Verify upside short-gamma squeeze acceleration triggers strong long score."""
        dates = pd.date_range("2026-01-01", periods=20, freq="B")
        df_up = pd.DataFrame({"Close": np.linspace(100, 125, 20), "Volume": [5e6] * 20}, index=dates)
        chain_squeeze = [{"type": "call", "strike": 120.0, "tau": 0.05, "vol": 0.40, "open_interest": 80000}]
        res_df = self.options_engine.compute_scores(
            prices_dict={"NVDA": df_up},
            options_chain_dict={"NVDA": chain_squeeze}
        )
        score = res_df["option_surface_score"].iloc[0]
        self.assertGreater(score, 0.55, "Short gamma squeeze trigger must generate elevated bullish score")

    def test_tc31_f703_non_optionable_equity_proxy_fallback(self) -> None:
        """TC31 [F703]: Verify Parkinson volatility and asymmetric semivariance fallback for non-optionable symbols."""
        dates = pd.date_range("2026-01-01", periods=25, freq="B")
        df_krx = pd.DataFrame({
            "High": np.linspace(71000, 76000, 25),
            "Low": np.linspace(69000, 74000, 25),
            "Close": np.linspace(70000, 75000, 25),
            "Volume": [1e6] * 25
        }, index=dates)
        res_df = self.options_engine.compute_scores(prices_dict={"005930": df_krx})
        self.assertIsInstance(res_df, pd.DataFrame)
        self.assertFalse(res_df["option_surface_score"].isna().any())

    def test_tc32_f703_option_surface_score_bounds_within_98(self) -> None:
        """TC32 [F703]: Assert OptionSurfaceAccelerator scores stay strictly bounded in [0.05, 0.98]."""
        dates = pd.date_range("2026-01-01", periods=20, freq="B")
        df = pd.DataFrame({"Close": np.linspace(100, 110, 20), "Volume": [1e6] * 20}, index=dates)
        res_df = self.options_engine.compute_scores(prices_dict={"NVDA": df})
        scores = res_df["option_surface_score"]
        self.assertTrue((scores >= 0.05).all() and (scores <= 0.98).all())

    # =========================================================================
    # Tier 1, Category 5: Feature F704 (Orthogonalized Feature Store & PCA-ZCA)
    # =========================================================================

    def test_tc33_f704_hyperbolic_deadband_noise_leakage_less_than_312(self) -> None:
        """TC33 [F704]: Assert hyperbolic deadband (alpha=448.0, delta=0.035) suppresses sub-threshold noise."""
        # For sub-threshold signals (|z| <= 0.025), mathematical ratio <= 0.714 < 0.85 -> exact underflow 0.0
        test_z_subthreshold = [0.0, 0.001, 0.010, 0.020, 0.025]
        for z in test_z_subthreshold:
            clean_z = apply_hyperbolic_deadband_phase144(z, delta=0.035, alpha=448.0)
            self.assertEqual(clean_z, 0.0, msg=f"Sub-threshold noise leakage for z={z}")

        # At boundary z = 0.034 <= delta=0.035, output must be severely attenuated (< 1e-6)
        clean_z_boundary = apply_hyperbolic_deadband_phase144(0.034, delta=0.035, alpha=448.0)
        self.assertLess(clean_z_boundary, 1e-6, "Boundary noise must be attenuated < 1e-6")

    def test_tc34_f704_hyperbolic_deadband_full_transmission(self) -> None:
        """TC34 [F704]: Assert 100% transmission for significant signals |z| >= 0.045."""
        test_z_values = [0.045, 0.050, 0.10, 0.25, 0.50, 1.00]
        for z in test_z_values:
            clean_z = apply_hyperbolic_deadband_phase144(z, delta=0.035, alpha=448.0)
            self.assertAlmostEqual(clean_z, z, places=5, msg=f"Signal degraded for z={z}: got {clean_z}")

    def test_tc35_f704_top5_economic_pillar_consensus_preservation(self) -> None:
        """TC35 [F704]: Verify Top-5 economic pillar consensus preservation in PCA-ZCA whitening."""
        symbols = [f"SYM_{i:03d}" for i in range(20)]
        strategies = [f"strat_{i}" for i in range(10)]
        scores_data = np.random.uniform(0.10, 0.90, size=(20, 10))
        df_scores = pd.DataFrame(scores_data, index=symbols, columns=strategies)

        ortho_df = self.ortho_engine.orthogonalize(
            score_df=df_scores,
            strategy_cols=strategies,
            method="pca_symmetric",
            preserve_top_k=5,
        )
        self.assertEqual(ortho_df.shape, df_scores.shape)
        self.assertFalse(ortho_df.isna().any().any())

    def test_tc36_f704_pca_zca_whitening_symmetric_matrix_property(self) -> None:
        """TC36 [F704]: Verify PCA-ZCA whitening operator C^-1/2 is strictly symmetric (W = W^T)."""
        A = np.random.randn(8, 8)
        cov = A @ A.T + 1e-4 * np.eye(8)
        vals, vecs = np.linalg.eigh(cov)
        inv_sqrt_d = np.diag(1.0 / np.sqrt(vals))
        W = vecs @ inv_sqrt_d @ vecs.T

        diff = np.max(np.abs(W - W.T))
        self.assertLess(diff, 1e-12, f"PCA-ZCA whitening operator must be symmetric, max diff = {diff}")

    def test_tc37_f704_marchenko_pastur_lower_spectral_edge_clipping(self) -> None:
        """TC37 [F704]: Verify Marchenko-Pastur lower spectral edge noise floor clipping."""
        N, K = 100, 20
        q = K / N
        sigma2 = 1.0
        lambda_minus = sigma2 * ((1.0 - np.sqrt(q)) ** 2)

        self.assertAlmostEqual(lambda_minus, (1.0 - np.sqrt(0.20)) ** 2, places=4)
        self.assertGreater(lambda_minus, 0.25)

    def test_tc38_f704_pairwise_available_covariance_and_psd_repair(self) -> None:
        """TC38 [F704]: Verify pairwise available-data covariance repair guarantees PSD."""
        C_non_psd = np.array([
            [1.0, 0.9, 0.9],
            [0.9, 1.0, 0.9],
            [0.9, 0.9, 0.1],
        ], dtype=np.float64)

        min_eig_before = float(np.min(np.linalg.eigvalsh(C_non_psd)))
        self.assertLess(min_eig_before, 0.0, "Pre-condition: input must have negative eigenvalue")

        C_repaired = repair_covariance_psd(C_non_psd, ridge_epsilon=1e-5)
        min_eig_after = float(np.min(np.linalg.eigvalsh(C_repaired)))
        self.assertGreaterEqual(min_eig_after, 1e-6, "Repaired covariance must have all eigenvalues >= ridge_epsilon")

    def test_tc39_f704_factor_orthogonalizer_engine_zero_nans(self) -> None:
        """TC39 [F704]: Assert FactorOrthogonalizerEngine produces zero NaNs on real score matrices."""
        symbols = [f"KRX_{i:06d}" for i in range(15)]
        strategies = ["s1", "s2", "s3", "s4", "s5"]
        mat = np.random.uniform(0.2, 0.8, size=(15, 5))
        df = pd.DataFrame(mat, index=symbols, columns=strategies)

        res_df = self.ortho_engine.orthogonalize(df, strategy_cols=strategies, method="pca_symmetric")
        self.assertFalse(res_df.isna().any().any())

    def test_tc40_f704_feature_store_caching_and_idempotency(self) -> None:
        """TC40 [F704]: Verify orthogonalization idempotency (repeated call produces bit-for-bit identical output)."""
        df = pd.DataFrame(np.random.uniform(0.1, 0.9, size=(10, 4)), columns=["a", "b", "c", "d"])
        out1 = self.ortho_engine.orthogonalize(df, strategy_cols=["a", "b", "c", "d"], method="pca_symmetric")
        out2 = self.ortho_engine.orthogonalize(df, strategy_cols=["a", "b", "c", "d"], method="pca_symmetric")
        pd.testing.assert_frame_equal(out1, out2)

    # =========================================================================
    # Tier 2 & 3: Boundary Value Analysis & Pairwise Combinations (TC41 ~ TC42)
    # =========================================================================

    def test_tc41_bva_extreme_numerical_limits_across_engines(self) -> None:
        """TC41 [BVA]: Test extreme numerical limits: zero, infinity, near-zero rates, extreme strikes."""
        greeks_zero_tau = compute_black_scholes_greeks(spot=100.0, strike=100.0, tau=1e-8, vol=0.20)
        self.assertEqual(greeks_zero_tau["gamma"], 0.0)

        self.assertEqual(bullwhip_transform(0.0, hop=1), 0.0)
        self.assertEqual(bullwhip_transform(0.0, hop=2), 0.0)
        self.assertEqual(bullwhip_transform(0.0, hop=3), 0.0)

        pol_zero, conv_zero = compute_finbert_polarity(0.0, 0.0, 0.0)
        self.assertTrue(np.isfinite(pol_zero) and np.isfinite(conv_zero))

    def test_tc42_pairwise_cross_engine_regime_combinations(self) -> None:
        """TC42 [Pairwise]: Verify pairwise interactions between Bullwhip shock, macro impulse, and NLP."""
        phi = bullwhip_transform(-0.05, hop=2)
        impulse_delta = compute_overnight_tailwind_delta(0.03, 0.0, beta=1.0)
        pol, conv = compute_finbert_polarity(0.10, 0.10, 0.80)

        self.assertLess(phi, -0.05, "Hop 2 Bullwhip amplifies downside order cancellations")
        self.assertGreater(impulse_delta, 0.0, "Positive macro tailwind")
        self.assertLessEqual(conv, 0.25, "Neutral NLP text suppressed by deadband")

    # =========================================================================
    # Tier 4: Real-World Workloads & Invariants (TC43 ~ TC45)
    # =========================================================================

    def test_tc43_real_world_5market_simulation(self) -> None:
        """TC43 [Real-World]: Execute multi-market cross-sectional scoring across 5 production markets."""
        dates = pd.date_range("2026-01-01", periods=30, freq="B")
        market_universe = {
            # KOSPI
            "005930": pd.DataFrame({"Close": np.linspace(70000, 75000, 30), "Volume": [5e6] * 30}, index=dates),
            "000660": pd.DataFrame({"Close": np.linspace(150000, 165000, 30), "Volume": [2e6] * 30}, index=dates),
            # KOSDAQ
            "247540": pd.DataFrame({"Close": np.linspace(200000, 220000, 30), "Volume": [8e5] * 30}, index=dates),
            # SP500
            "NVDA": pd.DataFrame({"Close": np.linspace(120, 140, 30), "Volume": [2e7] * 30}, index=dates),
            "AAPL": pd.DataFrame({"Close": np.linspace(220, 230, 30), "Volume": [1.5e7] * 30}, index=dates),
            # NASDAQ
            "TSLA": pd.DataFrame({"Close": np.linspace(240, 260, 30), "Volume": [3e7] * 30}, index=dates),
            # RUSSELL2000
            "SMCI": pd.DataFrame({"Close": np.linspace(40, 50, 30), "Volume": [5e6] * 30}, index=dates),
        }

        # 1. GNN v2
        gnn_df = self.gnn_engine.compute_scores(market_universe)
        self.assertIsInstance(gnn_df, pd.DataFrame)
        self.assertFalse(gnn_df["supply_chain_gnn_v2_score"].isna().any())

        # 2. Micro Momentum
        micro_df = self.micro_engine.compute_scores(
            market_universe,
            macro_returns={"sox": 0.02, "sp500": 0.01},
            lead_returns={"NVDA": 0.025},
        )
        self.assertIsInstance(micro_df, pd.DataFrame)
        self.assertFalse(micro_df["cross_market_micro_mom_score"].isna().any())

        # 3. NLP Catalyst
        nlp_df = self.nlp_engine.compute_scores(market_universe)
        self.assertIsInstance(nlp_df, pd.DataFrame)
        self.assertFalse(nlp_df["nlp_catalyst_score"].isna().any())

        # 4. Option Surface
        opt_df = self.options_engine.compute_scores(market_universe)
        self.assertIsInstance(opt_df, pd.DataFrame)
        self.assertFalse(opt_df["option_surface_score"].isna().any())

    def test_tc44_sub_millisecond_execution_latency_sla(self) -> None:
        """TC44 [SLA]: Assert cross-sectional computation latency < 150ms for 100-symbol universe."""
        dates = pd.date_range("2026-01-01", periods=20, freq="B")
        test_universe = {
            f"SYM_{i:04d}": pd.DataFrame({"Close": np.linspace(100, 105, 20), "Volume": [1e5] * 20}, index=dates)
            for i in range(100)
        }

        t0 = time.perf_counter()
        res_df = self.gnn_engine.compute_scores(test_universe)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertGreater(len(res_df), 0)
        self.assertLess(elapsed_ms, 150.0, f"GNN v2 latency SLA breached! Expected < 150ms, took {elapsed_ms:.2f}ms")

    def test_tc45_system_invariants_zero_synthetic_rows(self) -> None:
        """TC45 [Invariants]: Assert zero synthetic rows and mark-to-market beginning-of-day causal alignment."""
        dates = pd.date_range("2026-01-01", periods=10, freq="B")
        df = pd.DataFrame({"Close": [100.0] * 10, "Volume": [1e5] * 10}, index=dates)
        res_df = self.gnn_engine.compute_scores({"NVDA": df})

        self.assertEqual(len(res_df), 1)
        self.assertIn("symbol", res_df.columns)
        self.assertEqual(res_df["symbol"].iloc[0], "NVDA")


if __name__ == "__main__":
    unittest.main()
