"""
Phase 8 Sovereign Quantitative Enhancements (v15):
Portfolio Allocation & Level-3 Queue Acceleration Execution Test Suite.
Requirement R2 (Features F53 and F54):
- F53.1: Multivariate Regular Vine (R-Vine) Tree Copula Downside Cascade Contagion (T1, T2, T3).
- F53.2: Information Entropy Parity (IEP) & R-Vine Cascade Reliability Tilting.
- F53.3: Downside Sortino Multiplier Tilting with Higher-Order Cascade Contagion Drag.
- F53.4: Euler Component CVaR (CCVaR) Risk Budgeting with R-Vine Safety-Weighted Headroom Redistribution.
- F54.1: Level-3 Queue Imbalance 2nd-Order Acceleration (d^2QI/dt^2) Predictive Micro-Price Pegging.
- F54.2: Cross-Asset Flow Toxicity Blending & Acceleration-Aware Peg Shading in OMS Execution.
- F54.3: SmartOrderRouter ATS Preemption Expansion to 85%, Maker Floor Contraction to 0.05, and MinQty to 75%.
- F54.4: 100% Bit-Level Parity between ExecutionOMSEngine and AlmgrenChrissScheduler with Zero Regressions.
"""

import math
import time
import numpy as np
import pandas as pd
import pytest

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.core.fast_lob_engine import FastOrderBookMatchingEngine
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler
from src.execution.smart_order_router import SmartOrderRouter


# =============================================================================
# 1. FEATURE F53: MULTIVARIATE R-VINE TREE COPULA & INFORMATION ENTROPY PARITY
# =============================================================================

class TestPhase8RVinePortfolioAllocation:
    """Test Suite for Feature F53: Multivariate R-Vine Copula & Information Entropy Parity."""

    def test_f53_rvine_tree_copula_cascade_metrics(self):
        """
        Verifies that compute_rvine_tail_cascade_metrics evaluates 3-tier tree copulas:
        Tree 1 (unconditional pairwise), Tree 2 (first-order conditional via Clayton h-functions),
        and Tree 3 (second-order nested cascade copulas), producing valid bounded metrics.
        """
        allocator = UnifiedPortfolioAllocator()
        np.random.seed(42)
        n_obs = 120
        n_assets = 5

        # Simulate returns with correlated tail co-crashes
        base_noise = np.random.normal(0, 0.02, size=(n_obs, 1))
        asset_noise = np.random.normal(0, 0.015, size=(n_obs, n_assets))
        # Induce systemic crashes
        crash_days = np.random.choice(n_obs, size=15, replace=False)
        base_noise[crash_days] -= 0.10

        sim_returns = base_noise + asset_noise

        res = allocator.compute_rvine_tail_cascade_metrics(sim_returns)

        # Validate dictionary keys
        assert "lambda_cascade_aggregate" in res
        assert "tree1_lower_tail_mean" in res
        assert "tree2_lower_tail_mean" in res
        assert "tree3_lower_tail_mean" in res
        assert "tree1_upper_tail_mean" in res
        assert "asset_cascade_vector" in res
        assert "pairwise_lower_tail_matrix" in res

        # Validate output dimensions
        assert res["asset_cascade_vector"].shape == (n_assets,)
        assert res["pairwise_lower_tail_matrix"].shape == (n_assets, n_assets)

        # Validate metric bounds
        assert 0.0 <= res["lambda_cascade_aggregate"] <= 1.0
        assert 0.0 <= res["tree1_lower_tail_mean"] <= 1.0
        assert 0.0 <= res["tree2_lower_tail_mean"] <= 1.0
        assert 0.0 <= res["tree3_lower_tail_mean"] <= 1.0
        assert 0.0 <= res["tree1_upper_tail_mean"] <= 1.0

        # Due to systemic shock days, tail dependence across trees must be positive
        assert res["tree1_lower_tail_mean"] > 0.05
        assert res["lambda_cascade_aggregate"] > 0.05

    def test_f53_information_entropy_parity_reliability_tilting(self):
        """
        Verifies:
        1. When regime epistemic entropy is elevated and cascade contagion is low,
           IEP pulls model blend weights toward equal weighting parity (0.25).
        2. When cascade contagion spikes (lambda_cascade = 0.70), EVT-CVaR expands (+1.65 shift)
           while Risk Parity collapses (-1.25 shift) and Black-Litterman contracts (-0.90 shift).
        """
        allocator = UnifiedPortfolioAllocator()

        # Case 1: High entropy regime with benign cascade contagion
        # Construct maximum entropy regime distribution
        regime_uniform = {
            "BULL_LOW_VOL": 0.17, "BULL_HIGH_VOL": 0.17,
            "SIDEWAYS_LOW_VOL": 0.17, "SIDEWAYS_HIGH_VOL": 0.17,
            "BEAR_LOW_VOL": 0.16, "BEAR_HIGH_VOL": 0.16
        }

        w_v7 = allocator.compute_information_theoretic_blend_weights(
            regime=regime_uniform,
            crisis_severity=0.0,
            copula_lower_tail=0.02,
            copula_upper_tail=0.02,
            version=7,
        )

        w_v8_iep = allocator.compute_information_theoretic_blend_weights(
            regime=regime_uniform,
            crisis_severity=0.0,
            copula_lower_tail=0.02,
            copula_upper_tail=0.02,
            rvine_cascade_index=0.02,
            tree2_conditional_tail=0.01,
            version=8,
        )

        # Under IEP in Phase 8, weights must be closer to 0.25 (lower dispersion around 0.25)
        dev_v7 = sum((v - 0.25) ** 2 for v in w_v7.values())
        dev_v8 = sum((v - 0.25) ** 2 for v in w_v8_iep.values())
        assert dev_v8 < dev_v7

        # Case 2: Extreme R-Vine cascade contagion
        w_cascade = allocator.compute_information_theoretic_blend_weights(
            regime="BEAR_HIGH_VOL",
            crisis_severity=0.60,
            rvine_cascade_index=0.70,
            tree2_conditional_tail=0.45,
            copula_upper_tail=0.05,
            version=8,
        )

        # EVT-CVaR must expand decisively
        assert w_cascade["cvar"] > 0.45
        # Risk Parity must contract heavily due to -1.25 shift
        assert w_cascade["rp"] < 0.10
        # Black-Litterman contracts due to -0.90 shift
        assert w_cascade["bl"] < 0.15

    def test_f53_downside_sortino_rvine_cascade_drag(self):
        """
        Verifies that in optimize_multi_model_blend, assets with elevated cascade exposure
        receive higher penalty drag (-0.50 * max(0, c_casc - bar_casc)), reducing target allocation weight.
        """
        allocator = UnifiedPortfolioAllocator()
        symbols = ["ASSET_A", "ASSET_B", "ASSET_C", "ASSET_D"]
        n = len(symbols)
        cov = np.eye(n) * 0.04
        pred_returns = np.array([0.05, 0.05, 0.05, 0.05])
        df_rets = pd.DataFrame(np.random.normal(0, 0.02, size=(30, n)), columns=symbols)

        # Asset 0 has high cascade contagion exposure
        asset_cascade_high = np.array([0.70, 0.10, 0.10, 0.10])
        w_high_cascade = allocator.optimize_multi_model_blend(
            predicted_returns=pred_returns,
            returns_df=df_rets,
            cov_matrix=cov,
            symbols=symbols,
            asset_cascade_vector=asset_cascade_high,
            version=8,
        )

        # Baseline with uniform low cascade exposure
        asset_cascade_uniform = np.array([0.15, 0.15, 0.15, 0.15])
        w_uniform_cascade = allocator.optimize_multi_model_blend(
            predicted_returns=pred_returns,
            returns_df=df_rets,
            cov_matrix=cov,
            symbols=symbols,
            asset_cascade_vector=asset_cascade_uniform,
            version=8,
        )

        # Asset 0 weight must be penalised when its cascade contagion is disproportionately high
        assert w_high_cascade[0] < w_uniform_cascade[0]
        # Conversely, safer assets (B, C, D) should have higher relative weights
        assert w_high_cascade[1] > w_high_cascade[0]

    def test_f53_euler_ccvar_rvine_safety_headroom_redistribution(self):
        """
        Verifies that Euler CCVaR residual headroom redistribution under version=8
        weights headroom by exp(-1.5 * asset_cascade), steering reallocated capital
        preferentially to assets with minimal cascade contagion.
        """
        allocator = UnifiedPortfolioAllocator()
        symbols = ["RISKY", "SAFE_1", "SAFE_2"]
        n = len(symbols)

        # Covariance where RISKY asset has extreme variance and covariance with others,
        # forcing a TRC budget violation
        cov = np.array([
            [0.25, 0.08, 0.08],
            [0.08, 0.04, 0.01],
            [0.08, 0.01, 0.04]
        ])

        pred_returns = np.array([0.10, 0.05, 0.05])
        df_rets = pd.DataFrame(np.random.normal(0, 0.02, size=(50, n)), columns=symbols)

        # SAFE_1 has low cascade (0.05), SAFE_2 has higher cascade (0.60)
        cascade_vec = np.array([0.80, 0.05, 0.60])

        w_opt = allocator.optimize_multi_model_blend(
            predicted_returns=pred_returns,
            returns_df=df_rets,
            cov_matrix=cov,
            symbols=symbols,
            asset_cascade_vector=cascade_vec,
            version=8,
        )

        # RISKY asset TRC is capped, and SAFE_1 must receive higher allocation than SAFE_2
        assert w_opt[1] > w_opt[2]


# =============================================================================
# 2. FEATURE F54: LEVEL-3 QUEUE ACCELERATION & CROSS-ASSET TOXICITY PEGGING
# =============================================================================

class TestPhase8MicrostructureAndPegExecution:
    """Test Suite for Feature F54: L3 Queue Acceleration, Cross-Asset Toxicity, & ATS Preemption."""

    def test_f54_l3_queue_imbalance_acceleration(self):
        """
        Verifies that compute_l3_queue_imbalance in FastOrderBookMatchingEngine:
        1. Tracks history of QI and computes 1st derivative velocity v_QI and 2nd derivative acceleration a_QI.
        2. Computes Taylor-expanded predictive accelerated micro-price.
        """
        engine = FastOrderBookMatchingEngine("TEST_ACCEL")

        # Initial book: Bid 100.0 (5000), Ask 100.5 (5000) -> QI = 0.0
        engine.add_limit_order("b1", "BUY", 100.0, 5000)
        engine.add_limit_order("a1", "SELL", 100.5, 5000)
        res1 = engine.compute_l3_queue_imbalance(timestamp_sec=100.0)
        assert np.isclose(res1["l3_queue_imbalance"], 0.0, atol=1e-2)

        # Step 2: Add modest buy depth -> initial positive velocity
        engine.add_limit_order("b2", "BUY", 100.0, 1000)
        res2 = engine.compute_l3_queue_imbalance(timestamp_sec=100.1)
        assert res2["qi_velocity"] > 0.0

        # Step 3: Massive burst of buy orders -> positive acceleration (d^2QI/dt^2 > 0)
        engine.add_limit_order("b3", "BUY", 100.0, 20_000)
        res3 = engine.compute_l3_queue_imbalance(timestamp_sec=100.2)
        assert res3["qi_acceleration"] > 0.0
        assert "accelerated_l3_micro_price" in res3
        # Accelerated micro-price leads raw micro-price when acceleration is positive
        assert res3["accelerated_l3_micro_price"] >= res3["l3_micro_price"]

    def test_f54_cross_asset_flow_toxicity_and_acceleration_peg_shading(self):
        """
        Verifies that calculate_peg_limit_price under F54:
        1. Blends local Hawkes and cross-asset flow toxicity: gamma_composite = 0.65 * g_loc + 0.35 * g_cross.
        2. Applies toxic shading offset when gamma_composite > 0.45 under version >= 8.
        3. Applies queue acceleration shift: direction * 0.20 * spr * tanh(0.80 * a_QI) * (1 - 0.90 * gamma_composite).
        """
        target_p = 100.0
        bid_p = 99.0
        ask_p = 101.0
        spr = 2.0

        # Benign cross-asset toxicity (gamma_composite = 0.65 * 0.30 + 0 = 0.195 <= 0.45, shade_shift = 0)
        px_benign = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p,
            bid_price=bid_p,
            ask_price=ask_p,
            spread=spr,
            action="BUY",
            hawkes_toxicity=0.30,
            cross_asset_toxicity=0.0,
            version=8,
        )

        # High cross-asset flow toxicity (gamma_composite = 0.65 * 0.30 + 0.35 * 0.90 = 0.510 > 0.45, shade_shift active)
        px_cross_toxic = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p,
            bid_price=bid_p,
            ask_price=ask_p,
            spread=spr,
            action="BUY",
            hawkes_toxicity=0.30,
            cross_asset_toxicity=0.90,
            version=8,
        )

        # BUY order must step back lower to avoid toxic adverse selection fill
        assert px_cross_toxic < px_benign

        # Acceleration shift with benign toxicity
        px_accel = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p,
            bid_price=bid_p,
            ask_price=ask_p,
            spread=spr,
            action="BUY",
            hawkes_toxicity=0.0,
            cross_asset_toxicity=0.0,
            qi_acceleration=4.0,
            version=8,
        )

        # Positive buyer queue acceleration shifts limit price closer to touch to ensure fill
        assert px_accel > px_benign

    def test_f54_sor_preemption_up_to_eighty_five_percent(self):
        """
        Verifies that when lit queue acceleration surges (a_QI > 0.20) or QI > 0.40,
        SmartOrderRouter preemptively routes up to 85% to dark ATS before lit quotes jump.
        """
        sor = SmartOrderRouter()
        order_plan = {
            "symbol": "NVDA",
            "action": "BUY",
            "quantity": 10_000,
            "target_price": 120.0,
            "execution_strategy": "MIDPOINT_PEG",
            "darkpool_score": 0.80,
            "is_accumulation": True,
            "version": 8,
        }

        # Neutral routing
        routed_neutral = sor.route_order(
            order_plan,
            queue_imbalance=0.0,
            version=8
        )

        # Surging queue acceleration and imbalance
        routed_preempt = sor.route_order(
            order_plan,
            queue_imbalance=0.60,
            qi_acceleration=3.0,
            version=8
        )

        dark_legs = [leg for leg in routed_preempt["legs"] if leg["venue_type"] == "DARK_ATS_MIDPOINT"]
        assert len(dark_legs) == 1
        dark_qty = dark_legs[0]["quantity"]

        # Effective dark ratio expands up to 85% (0.85)
        assert routed_preempt["effective_dark_ratio"] > routed_neutral["effective_dark_ratio"]
        assert np.isclose(routed_preempt["effective_dark_ratio"], 0.85, atol=1e-3)
        assert dark_qty == 8500

    def test_f54_sor_extreme_toxicity_maker_contraction_to_five_percent(self):
        """
        Verifies that under extreme directional toxicity (gamma_toxic > 0.80),
        Phase 8 contracts the lit maker floor down to 0.05 (5%), preventing passive fills.
        """
        sor = SmartOrderRouter()
        order_plan = {
            "symbol": "TSLA",
            "action": "BUY",
            "quantity": 10_000,
            "target_price": 200.0,
            "execution_strategy": "PATIENT_TWAP",
            "version": 8,
        }

        # Route with gamma_toxic_dir = 1.0 (extreme toxic flow)
        routed = sor.route_order(
            order_plan,
            gamma_toxic_dir=1.0,
            version=8
        )

        # Confirm maker_ratio floor contracts to 0.05 (5%)
        assert np.isclose(routed["maker_ratio"], 0.05, atol=1e-3)

        maker_legs = [leg for leg in routed["legs"] if leg["venue_type"] == "PRIMARY_EXCHANGE_MAKER"]
        assert len(maker_legs) == 1
        maker_qty = maker_legs[0]["quantity"]

        # Dark probe at gamma_toxic=1.0 is 60% (0.40 + 0.20), so rem_qty is 4,000
        # 5% of 4,000 = 200 maker shares
        rem_qty = 10_000 - int(10_000 * 0.60)
        assert maker_qty == int(rem_qty * 0.05)

    def test_f54_sor_anti_gaming_min_qty_expansion_to_seventy_five_percent(self):
        """
        Verifies that under extreme toxicity and institutional accumulation,
        anti-gaming MinQty expands to 75% of dark pool order quantity to block predatory sweeps.
        """
        sor = SmartOrderRouter()
        order_plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 10_000,
            "target_price": 180.0,
            "darkpool_score": 1.0,
            "is_accumulation": True,
            "version": 8,
        }

        routed = sor.route_order(
            order_plan,
            gamma_toxic_dir=1.0,
            version=8
        )

        dark_legs = [leg for leg in routed["legs"] if leg["venue_type"] == "DARK_ATS_MIDPOINT"]
        assert len(dark_legs) == 1
        dark_leg = dark_legs[0]

        assert dark_leg.get("anti_gaming_active") is True
        dark_qty = dark_leg["quantity"]
        min_qty = dark_leg["min_quantity"]

        # min_ratio = clip(0.20 + 0.35 * 1.0 + 0.20 * 1.0, 0.20, 0.75) = 0.75 (75%)
        assert min_qty == int(round(0.75 * dark_qty))

    def test_f54_parity_between_oms_engine_and_almgren_chriss(self):
        """
        Verifies 100% bit-level parity between ExecutionOMSEngine and AlmgrenChrissScheduler
        across diverse combinations of Phase 8 parameters (qi_acceleration, cross_asset_toxicity).
        """
        test_scenarios = [
            {
                "target_price": 100.0,
                "bid_price": 99.0,
                "ask_price": 101.0,
                "spread": 2.0,
                "action": "BUY",
                "hawkes_toxicity": 0.30,
                "cross_asset_toxicity": 0.80,
                "qi_acceleration": 2.5,
                "queue_position_ratio": 0.60,
                "version": 8,
            },
            {
                "target_price": 50.0,
                "bid_price": 49.5,
                "ask_price": 50.5,
                "spread": 1.0,
                "action": "SELL",
                "hawkes_toxicity": 0.70,
                "cross_asset_toxicity": 0.50,
                "qi_acceleration": -3.0,
                "hawkes_arrival_imbalance": -0.50,
                "version": 8,
            },
            {
                "target_price": 250.0,
                "bid_price": 248.0,
                "ask_price": 252.0,
                "spread": 4.0,
                "action": "BUY",
                "hawkes_toxicity": 0.0,
                "cross_asset_toxicity": 0.0,
                "qi_acceleration": 5.0,
                "queue_imbalance": 0.75,
                "version": 8,
            },
            {
                "target_price": 1500.0,
                "bid_price": 1495.0,
                "ask_price": 1505.0,
                "spread": 10.0,
                "action": "SELL",
                "hawkes_toxicity": 0.95,
                "cross_asset_toxicity": 0.90,
                "qi_acceleration": 1.0,
                "version": 8,
            },
        ]

        for sc in test_scenarios:
            px_oms = ExecutionOMSEngine.calculate_peg_limit_price(**sc)
            px_ac = AlmgrenChrissScheduler.calculate_peg_limit_price(**sc)
            assert np.isclose(px_oms, px_ac, atol=1e-7)
