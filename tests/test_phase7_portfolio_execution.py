"""
Phase 7 Zenith Quantitative Enhancements: 4-Model Copula Tail Dependency Allocation
& Level-3 Order Book Queue Imbalance Micro-Price Pegging Test Suite.
Requirement R2 (Features F49 and F50):
- F49.1: Archimedean Clayton (lambda_L) & Gumbel (lambda_U) Copula Tail Dependence Estimation.
- F49.2: Continuous Information-Theoretic 4-Model Reliability Optimization with Copula Log-Odds Shifts.
- F49.3: Downside Sortino Tilting with Copula Tail Contagion Drag (-0.40 * max(0, lambda_L - bar_lambda)).
- F49.4: Euler Component CVaR (CCVaR) Risk Budgeting with Residual Headroom Weighted Redistribution.
- F50.1: Physical Distance-Decayed & Fragmentation-Adjusted Level-3 Queue Imbalance (QI_L3*).
- F50.2: Bivariate Hawkes Arrival Intensity Imbalance (Delta lambda_dir) & Branching Ratio.
- F50.3: Toxicity-Suppressed Queue Concession & Directional Adverse Selection Shading in Peg Pricing.
- F50.4: SmartOrderRouter Lit Queue Imbalance Preemption, 0.10 Maker Floor & 0.60 Anti-Gaming MinQty.
- F50.5: Bit-Level Parity between ExecutionOMSEngine and AlmgrenChrissScheduler with Zero Regressions.
"""

import math
import time
import numpy as np
import pandas as pd
import pytest

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.core.fast_lob_engine import FastOrderBookMatchingEngine, BivariateHawkesIntensity
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler
from src.execution.smart_order_router import SmartOrderRouter


# =============================================================================
# 1. FEATURE F49: 4-MODEL COPULA TAIL ALLOCATION & EULER CCVAR BUDGETING
# =============================================================================

class TestPhase7CopulaPortfolioAllocation:
    """Test Suite for Feature F49: Copula Tail Dependency & Euler CCVaR Allocation."""

    def test_f49_copula_tail_dependence_metrics_computation(self):
        """
        Verifies that compute_copula_tail_dependence_metrics correctly estimates
        lower tail dependence lambda_L and upper tail dependence lambda_U from empirical returns.
        """
        allocator = UnifiedPortfolioAllocator()
        np.random.seed(42)
        n_obs = 100
        n_assets = 5

        # Correlated returns with simulated tail co-movements
        base_noise = np.random.normal(0, 0.02, size=(n_obs, 1))
        asset_noise = np.random.normal(0, 0.015, size=(n_obs, n_assets))
        # Induce heavy lower tail crashes (systemic shocks)
        crash_days = np.random.choice(n_obs, size=10, replace=False)
        base_noise[crash_days] -= 0.08

        sim_returns = base_noise + asset_noise

        lam_mat, bar_l, bar_u = allocator.compute_copula_tail_dependence_metrics(sim_returns)

        assert lam_mat.shape == (n_assets, n_assets)
        assert 0.0 <= bar_l <= 1.0
        assert 0.0 <= bar_u <= 1.0
        # Diagonals must be 1.0 (self-dependence)
        for i in range(n_assets):
            assert np.isclose(lam_mat[i, i], 1.0, atol=1e-5)
        # Because we induced systemic crashes, lower tail dependence must be substantial
        assert bar_l > 0.10

    def test_f49_copula_tail_reliability_log_odds_shifts(self):
        """
        Verifies that under severe lower tail dependence (lambda_L > 0.15),
        information-theoretic blending weights tilt towards EVT-CVaR and HERC,
        while contracting Risk Parity and Black-Litterman.
        """
        allocator = UnifiedPortfolioAllocator()
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        regime = "BEAR_HIGH_VOL"

        # Baseline blend weights (lambda_L = 0.0)
        w_base = allocator.compute_information_theoretic_blend_weights(
            regime=regime,
            crisis_severity=0.5,
            copula_lower_tail=0.0,
            copula_upper_tail=0.0,
            version=6,
        )

        # Copula tilted blend weights (severe crash co-dependence lambda_L = 0.65)
        w_copula = allocator.compute_information_theoretic_blend_weights(
            regime=regime,
            crisis_severity=0.5,
            copula_lower_tail=0.65,
            copula_upper_tail=0.10,
            version=7,
        )

        # EVT-CVaR weight must expand (+1.10 shift)
        assert w_copula["cvar"] > w_base["cvar"]
        # HERC relative share over Risk Parity must expand (+0.35 shift vs -0.80 shift)
        assert (w_copula["herc"] / w_copula["rp"]) > (w_base["herc"] / w_base["rp"])
        # Risk Parity must contract (-0.80 shift)
        assert w_copula["rp"] < w_base["rp"]
        # Black-Litterman must contract (-0.60 shift)
        assert w_copula["bl"] < w_base["bl"]
        # Weights must sum to 1.0
        assert np.isclose(sum(w_copula.values()), 1.0, atol=1e-5)

    def test_f49_gumbel_upper_tail_expands_black_litterman(self):
        """
        Verifies that under benign bull conditions with strong upper tail co-movement (lambda_U > 0.20),
        Black-Litterman receives a positive view reliability boost (+0.30 shift).
        """
        allocator = UnifiedPortfolioAllocator()
        regime = "BULL_LOW_VOL"

        w_base = allocator.compute_information_theoretic_blend_weights(
            regime=regime,
            crisis_severity=0.0,
            copula_lower_tail=0.05,
            copula_upper_tail=0.10,
            version=6,
        )

        w_upper = allocator.compute_information_theoretic_blend_weights(
            regime=regime,
            crisis_severity=0.0,
            copula_lower_tail=0.05,
            copula_upper_tail=0.75,
            version=7,
        )

        assert w_upper["bl"] > w_base["bl"]
        assert np.isclose(sum(w_upper.values()), 1.0, atol=1e-5)

    def test_f49_downside_sortino_copula_contagion_drag(self):
        """
        Verifies that an asset with above-average lower-tail crash dependence
        experiences copula drag in Sortino tilting, reducing its final allocated weight.
        """
        allocator = UnifiedPortfolioAllocator()
        symbols = ["STOCK_A", "STOCK_B", "STOCK_C"]
        n = len(symbols)
        pred_returns = np.array([0.08, 0.08, 0.08])

        np.random.seed(42)
        r = np.random.normal(0.001, 0.015, 100)
        df_rets = pd.DataFrame({"STOCK_A": r, "STOCK_B": r.copy(), "STOCK_C": r.copy()})
        cov = np.eye(3) * (0.015 ** 2)

        # STOCK_A has severe lower tail dependence (0.80), whereas STOCK_B and C have mild (0.20)
        cross_copula = np.array([0.80, 0.20, 0.20])

        w_alloc = allocator.optimize_multi_model_blend(
            predicted_returns=pred_returns,
            returns_df=df_rets,
            cov_matrix=cov,
            symbols=symbols,
            cross_asset_copula_lower_tail=cross_copula,
            version=7,
        )

        # STOCK_A must receive a lower weight than STOCK_B due to -0.40 * (0.80 - 0.40) drag
        assert w_alloc[0] < w_alloc[1]
        assert np.isclose(w_alloc[1], w_alloc[2], atol=1e-3)
        assert np.isclose(np.sum(w_alloc), 1.0, atol=1e-4)

    def test_f49_euler_ccvar_headroom_redistribution(self):
        """
        Verifies that when high-risk assets exceed the TRC cap, excess risk budget
        is redistributed to compliant assets weighted by their residual headroom.
        """
        allocator = UnifiedPortfolioAllocator()
        symbols = ["ASSET_1", "ASSET_2", "ASSET_3", "ASSET_4"]
        n = 4
        pred_returns = np.array([0.15, 0.10, 0.05, 0.02])

        # Covariance matrix where ASSET_1 has huge variance and high covariance with all assets
        cov = np.array([
            [0.250, 0.080, 0.060, 0.040],
            [0.080, 0.040, 0.015, 0.010],
            [0.060, 0.015, 0.020, 0.005],
            [0.040, 0.010, 0.005, 0.010],
        ])
        np.random.seed(42)
        df_rets = pd.DataFrame(np.random.multivariate_normal(np.zeros(n), cov, size=100), columns=symbols)

        w_v7 = allocator.optimize_multi_model_blend(
            predicted_returns=pred_returns,
            returns_df=df_rets,
            cov_matrix=cov,
            symbols=symbols,
            version=7,
        )

        # All weights must be non-negative and sum to 1.0
        assert np.all(w_v7 >= 0.0)
        assert np.isclose(np.sum(w_v7), 1.0, atol=1e-4)
        # Check risk contributions under effective covariance
        _, trc = allocator.compute_component_cvar_risk_contributions(w_v7, cov)
        trc_cap = max(1.75 / n, 0.20)
        # No asset should breach the cap significantly
        assert np.all(trc <= trc_cap + 0.05)


# =============================================================================
# 2. FEATURE F50: LEVEL-3 QUEUE IMBALANCE & HAWKES TOXICITY MICRO-PRICE PEGGING
# =============================================================================

class TestPhase7MicrostructureAndPegExecution:
    """Test Suite for Feature F50: Level-3 Queue Imbalance, Hawkes Arrival Imbalance & Preemption."""

    def test_f50_l3_distance_decayed_queue_imbalance(self):
        """
        Verifies that compute_l3_queue_imbalance in FastOrderBookMatchingEngine:
        1. Correctly calculates physical distance decay exp(-alpha_dist * |P_k - P_1| / spread).
        2. Incorporates order fragmentation ratio Phi_k.
        3. Spoofing orders placed far from touch are heavily attenuated.
        """
        engine = FastOrderBookMatchingEngine("TEST_L3")

        # Set up 5 bid levels and 5 ask levels
        # Touch: Bid 100.0 (size 1000, 2 orders), Ask 100.5 (size 1000, 2 orders)
        engine.add_limit_order("o_b1", "BUY", 100.0, 1000)
        engine.add_limit_order("o_a1", "SELL", 100.5, 1000)

        # Level 2 (close): Bid 99.9 (size 800), Ask 100.6 (size 800)
        engine.add_limit_order("o_b2", "BUY", 99.9, 800)
        engine.add_limit_order("o_a2", "SELL", 100.6, 800)

        # Add a massive far-away ask spoof at 105.0 (size 10,000 in 20 fragmented retail orders)
        for i in range(20):
            engine.add_limit_order(f"o_spoof_{i}", "SELL", 105.0, 500)

        res = engine.compute_l3_queue_imbalance(levels=10, lambda_depth=0.35, alpha_dist=0.50)

        assert "l3_queue_imbalance" in res
        assert "l3_micro_price" in res
        # Despite 10,000 spoofed ask volume at 105.0, the distance decay (10 ticks away)
        # prevents the queue imbalance from collapsing into extreme negative territory
        assert res["l3_queue_imbalance"] > -0.70
        assert 99.0 <= res["l3_micro_price"] <= 101.5

    def test_f50_bivariate_hawkes_arrival_imbalance(self):
        """
        Verifies that get_arrival_imbalance evaluates Delta lambda_dir in [-1.0, 1.0]
        and measures the branching ratio eta = (alpha_self + alpha_cross) / beta.
        """
        bh = BivariateHawkesIntensity(mu_buy=1.0, mu_sell=1.0, alpha_self=0.6, alpha_cross=0.2, beta=1.0)
        t_base = time.time()

        # Burst of BUY trades
        for i in range(5):
            bh.update("BUY", timestamp_sec=t_base + i * 0.05)

        imb = bh.get_arrival_imbalance(t_query=t_base + 0.30)

        assert imb["arrival_imbalance"] > 0.30
        assert imb["lambda_buy"] > imb["lambda_sell"]
        assert np.isclose(imb["branching_ratio"], (0.6 + 0.2) / 1.0, atol=1e-3)

    def test_f50_toxic_adverse_selection_peg_shading(self):
        """
        Verifies that calculate_peg_limit_price under F50:
        1. Attenuates queue concession q_shift via (1 - 0.85 * gamma_toxic).
        2. Applies toxic shading offset delta_P_shade = -direction * 0.25 * spread * (gamma_toxic - 0.50).
        3. BUY orders step back downwards when adverse toxic flow is detected.
        """
        target_p = 100.0
        bid_p = 99.0
        ask_p = 101.0
        spr = 2.0

        # Benign flow (gamma_toxic = 0.0) with back of queue position (u_q = 0.80)
        px_benign = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p,
            bid_price=bid_p,
            ask_price=ask_p,
            spread=spr,
            action="BUY",
            queue_position_ratio=0.80,
            hawkes_toxicity=0.0,
            version=7,
        )

        # High toxicity flow (gamma_toxic = 0.90) with same queue position
        px_toxic = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p,
            bid_price=bid_p,
            ask_price=ask_p,
            spread=spr,
            action="BUY",
            queue_position_ratio=0.80,
            hawkes_toxicity=0.90,
            version=7,
        )

        # Under high toxicity, BUY order must shade lower to prevent toxic adverse selection fill
        assert px_toxic < px_benign

    def test_f50_hawkes_arrival_imbalance_shifts_micro_price(self):
        """
        Verifies that positive arrival imbalance Delta lambda_dir > 0 shifts the anchor price upwards
        for BUY orders, reflecting aggressive buyer arrival momentum.
        """
        target_p = 100.0
        bid_p = 99.0
        ask_p = 101.0
        spr = 2.0

        px_neutral = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p,
            bid_price=bid_p,
            ask_price=ask_p,
            spread=spr,
            hawkes_arrival_imbalance=0.0,
            version=7,
        )

        px_buy_burst = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p,
            bid_price=bid_p,
            ask_price=ask_p,
            spread=spr,
            hawkes_arrival_imbalance=0.80,
            version=7,
        )

        assert px_buy_burst > px_neutral

    def test_f50_sor_lit_queue_imbalance_preemption(self):
        """
        Verifies that when lit Queue Imbalance aligns with trade direction (QI > 0.50),
        SmartOrderRouter preemptively routes up to 75% to dark ATS before lit spread exhaustion.
        """
        sor = SmartOrderRouter()
        order_plan = {
            "symbol": "NVDA",
            "action": "BUY",
            "quantity": 10_000,
            "target_price": 120.0,
            "execution_strategy": "MIDPOINT_PEG",
            "version": 7,
        }

        # Neutral lit book
        routed_neutral = sor.route_order(order_plan=order_plan, queue_imbalance=0.0)

        # High lit Queue Imbalance indicating imminent ask wipeout (QI = 0.85)
        routed_preempt = sor.route_order(order_plan=order_plan, queue_imbalance=0.85)

        assert routed_preempt["effective_dark_ratio"] > routed_neutral["effective_dark_ratio"]
        assert routed_preempt["effective_dark_ratio"] <= 0.75

    def test_f50_sor_extreme_toxicity_maker_contraction_to_ten_percent(self):
        """
        Verifies that under extreme directional toxicity (gamma_toxic_dir = 1.0) under Phase 7,
        SmartOrderRouter contracts maker_ratio floor from 0.20 down to 0.10.
        """
        sor = SmartOrderRouter()
        order_plan = {
            "symbol": "TSLA",
            "action": "BUY",
            "quantity": 10_000,
            "target_price": 250.0,
            "execution_strategy": "MIDPOINT_PEG",
            "version": 7,
        }

        routed = sor.route_order(order_plan=order_plan, gamma_toxic_dir=1.0, version=7)
        assert np.isclose(routed["maker_ratio"], 0.10, atol=1e-3)

    def test_f50_sor_anti_gaming_min_qty_expansion_to_sixty_percent(self):
        """
        Verifies that under critical toxic accumulation in Phase 7,
        anti-gaming min_quantity expands up to 60% of dark quantity.
        """
        sor = SmartOrderRouter()
        order_plan = {
            "symbol": "META",
            "action": "BUY",
            "quantity": 10_000,
            "target_price": 500.0,
            "execution_strategy": "PATIENT_TWAP",
            "darkpool_score": 1.0,
            "version": 7,
        }

        routed = sor.route_order(order_plan=order_plan, gamma_toxic_dir=1.0, version=7)
        dark_leg = routed["dark_ats_midpoint"]
        assert dark_leg is not None
        assert dark_leg["anti_gaming_active"] is True
        # Under critical toxic accumulation, min_ratio reaches 60%
        assert dark_leg["min_quantity"] == int(round(0.60 * dark_leg["quantity"]))

    def test_f50_parity_between_oms_engine_and_almgren_chriss(self):
        """
        Verifies that ExecutionOMSEngine.calculate_peg_limit_price and
        AlmgrenChrissScheduler.calculate_peg_limit_price maintain exact bit-level parity
        across all Phase 7 parameter combinations.
        """
        test_cases = [
            {
                "target_price": 100.0,
                "bid_price": 99.0,
                "ask_price": 101.0,
                "spread": 2.0,
                "hawkes_toxicity": 0.85,
                "queue_position_ratio": 0.70,
                "hawkes_arrival_imbalance": 0.40,
                "queue_imbalance": 0.50,
                "action": "BUY",
                "version": 7,
            },
            {
                "target_price": 50.0,
                "bid_price": 49.5,
                "ask_price": 50.5,
                "spread": 1.0,
                "hawkes_toxicity": 0.20,
                "queue_position_ratio": 0.20,
                "hawkes_arrival_imbalance": -0.60,
                "queue_imbalance": -0.40,
                "action": "SELL",
                "version": 7,
            },
            {
                "target_price": 200.0,
                "bid_price": 198.0,
                "ask_price": 202.0,
                "spread": 4.0,
                "hawkes_toxicity": 0.95,
                "action": "SELL",
                "version": 7,
            },
        ]

        for tc in test_cases:
            px_oms = ExecutionOMSEngine.calculate_peg_limit_price(**tc)
            px_ac = AlmgrenChrissScheduler.calculate_peg_limit_price(**tc)
            assert np.isclose(px_oms, px_ac, atol=1e-6)
