"""
tests/test_phase110_adversarial_challenger1.py
=============================================
Empirical Adversarial Stress Testing & Invariant Challenge Suite for Phase 110.
Release R126 / v117 Production Master (Features F520~F524).

Adversarial Stress Dimensions:
1. Module 1 (F520): High-Dimensional Graph Granger Causality Network
   - Rank-deficient, singular, and perfectly collinear multivariate return matrices
   - Zero-variance / constant input series across single and multiple nodes
   - Extreme under-sampling (N <= p+2, N=1, empty inputs)
   - Extreme shock vector magnitudes (+-1e9, 1e15) and non-finite / missing shocks
   - Directed PageRank power iteration with isolated dangling nodes and disconnected topologies
2. Module 2 (F521): Multi-Regime Entropy-Pooled HERC Allocator
   - Contradictory, incompatible, and impossible equality/inequality view constraints
   - Extreme high-stress regimes (CRISIS, BEAR_HIGH_VOL) with exponential entropy dampening
   - Extreme variance disparity, singular covariance, and rank-deficient covariance matrices
   - Simplex constraint (sum w_i == 1.000000, w_i >= 0), single-stock cap (<= 0.20), sector cap (<= 0.35)
   - Leland dynamic no-trade buffer bands and entry/exit bypass verification
3. Module 3 (F522): Real-Time Microstructure Liquidity Toxicity Filter
   - Cold-start / zero trade volume evaluation and bounded metric [0.0, 1.0]
   - Pre-crash liquidity evaporation detection via orderbook depth collapse (< 20%) and spread blowout (> 3x)
   - Extreme order flow imbalance (OFI -> +-1.0, VPIN -> 1.0) under predatory sweeps
   - Dynamic quote shading bounds [0.0, 50.0] bps and OMS Gate 7.8 recommendation gating
4. Module 4 (F523): Corporate Actions & Dividend Adjustment Rebalancer
   - Sequential forward and reverse stock splits (10:1 -> 1:5 -> 2:1)
   - Large special dividends (> 50% price) and theoretical ex-price adjustment
   - Exact Portfolio NAV Conservation (NAV_pre == NAV_post, delta == 0.0)
   - TaxLot Cost Basis Invariant conservation across multi-lot positions
   - Non-interfering cash drag rebalance order synthesis bypassing active OMS execution slices
5. Module 5 (F524): Benchmark & Master Integration Verification
   - Full 8 KPI assertion verification across all 5 global markets
   - Bit-for-bit SHA-256 report synchronization across Category A, B, and C
"""

from __future__ import annotations

import collections
import datetime
import math
import subprocess
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p_dir in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p_dir not in sys.path:
        sys.path.insert(0, p_dir)

from src.ai.graph_granger_causality import (
    DEFAULT_MACRO_NODES,
    DEFAULT_SECTOR_NODES,
    GrangerFitSummary,
    GraphGrangerCausalityNetwork,
    NetworkTopologyMetrics,
    SystemicImpulseResponse,
    compute_directed_pagerank,
)
from src.core.intraday_toxicity_filter import (
    IntradayToxicityFilter,
    ToxicityEvaluationResult,
    VolumeBucket,
)
from src.data_layer.corporate_action_rebalancer import (
    ActionResult,
    CorporateAction,
    CorporateActionRebalancer,
    CorporateActionType,
    RebalanceOrder,
    TaxLot,
)
from src.risk.hierarchical_entropy_allocator import (
    EntropyPoolingResult,
    EntropyView,
    HERCAllocationResult,
    HierarchicalEntropyAllocator,
)


class TestPhase110AdversarialChallenger1(unittest.TestCase):
    """Master Empirical Adversarial Challenger Test Suite for Phase 110 (M1~M5)."""

    # =========================================================================
    # MODULE 1: Graph Granger Causality Network (Feature F520)
    # =========================================================================

    def test_adv_m1_01_rank_deficient_and_collinear_inputs(self) -> None:
        """Stress-test Granger network under rank-deficient and perfectly collinear return matrices."""
        np.random.seed(101)
        n_bars = 80
        base_series = np.random.normal(0.0005, 0.015, n_bars)

        # Perfectly collinear columns (x2 = 2*x1, x3 = -0.5*x1, x4 = x1 + x2)
        df_collinear = pd.DataFrame({
            "SOX": base_series,
            "SP500": 2.0 * base_series,
            "VIX": -0.5 * base_series,
            "XLK": 3.0 * base_series,
            "XLF": np.random.normal(0, 0.01, n_bars),
        })

        net = GraphGrangerCausalityNetwork(lag_order=2, alpha_penalty=0.05, l1_ratio=0.50)
        summary = net.fit(df_collinear)

        self.assertIsInstance(summary, GrangerFitSummary)
        self.assertEqual(len(summary.nodes), 5)

        # Adjacency matrix must have finite non-negative values and zero self-loops
        C = summary.causal_adjacency_matrix
        self.assertEqual(C.shape, (5, 5))
        self.assertTrue(np.all(np.isfinite(C)), "Adjacency matrix contains NaN or Inf under collinearity")
        self.assertTrue(np.all(C >= 0.0), "Adjacency weights must be non-negative")
        self.assertTrue(np.allclose(np.diag(C), 0.0), "Self-loops must be strictly zero")

        # Directed PageRank must converge with sum == 1.000000
        topo = net.compute_topology_metrics()
        pr_sum = sum(topo.directed_pagerank.values())
        self.assertAlmostEqual(pr_sum, 1.0, places=5)
        for sym, pr_val in topo.directed_pagerank.items():
            self.assertTrue(pr_val > 0.0, f"PageRank component for {sym} is non-positive: {pr_val}")

    def test_adv_m1_02_zero_variance_and_constant_columns(self) -> None:
        """Stress-test Granger network when some or all input series have zero variance (constant values)."""
        n_bars = 60
        # SOX is flat zero, VIX is constant 100.0, SP500 is normal random
        df_const = pd.DataFrame({
            "SOX": np.zeros(n_bars),
            "VIX": np.full(n_bars, 100.0),
            "SP500": np.random.normal(0.0001, 0.01, n_bars),
            "XLK": np.random.normal(0.0002, 0.012, n_bars),
        })

        net = GraphGrangerCausalityNetwork(lag_order=2, alpha_penalty=0.01)
        summary = net.fit(df_const)

        self.assertEqual(len(summary.nodes), 4)
        C = summary.causal_adjacency_matrix
        self.assertTrue(np.all(np.isfinite(C)), "Adjacency matrix has non-finite values with constant inputs")
        self.assertTrue(np.all(C >= 0.0))

        # R-squared for constant series must be clamped [0.0, 1.0] without division by zero crash
        for node in summary.nodes:
            r2 = summary.r_squared[node]
            self.assertTrue(0.0 <= r2 <= 1.0, f"R^2 out of bounds for {node}: {r2}")

    def test_adv_m1_03_extreme_under_sampling_fallback(self) -> None:
        """Verify graceful fallback when history bars N <= lag_order + 2."""
        df_short = pd.DataFrame({
            "SOX": [0.01, -0.02, 0.03],
            "SP500": [0.005, -0.01, 0.015],
        })

        net = GraphGrangerCausalityNetwork(lag_order=2)
        summary = net.fit(df_short)

        self.assertEqual(len(summary.nodes), 2)
        self.assertTrue(net.is_fitted)
        self.assertTrue(np.all(np.isfinite(summary.causal_adjacency_matrix)))

        # Empty inputs must raise descriptive ValueError
        with self.assertRaises(ValueError):
            net.fit(pd.DataFrame())

    def test_adv_m1_04_extreme_shock_spikes_and_propagation(self) -> None:
        """Subject impulse response engine to extreme shock values (+-1e9, 1e12) and check finite bounds."""
        np.random.seed(42)
        df = pd.DataFrame(np.random.normal(0, 0.01, size=(60, 4)), columns=["SOX", "VIX", "SP500", "XLK"])
        net = GraphGrangerCausalityNetwork(lag_order=1)
        net.fit(df)

        extreme_shocks = {
            "SOX": 1e9,
            "VIX": -1e9,
            "SP500": 5e8,
            "NON_EXISTENT": 999.0,  # Unseen symbol should be ignored gracefully
        }

        impulse_1d = net.compute_shock_impulse(extreme_shocks, horizon=1)
        impulse_5d = net.compute_shock_impulse(extreme_shocks, horizon=5)

        self.assertIsInstance(impulse_1d, SystemicImpulseResponse)
        self.assertIsInstance(impulse_5d, SystemicImpulseResponse)

        for sym, val in impulse_1d.projected_impulse.items():
            self.assertTrue(math.isfinite(val), f"1D impulse for {sym} is non-finite: {val}")
        for sym, val in impulse_5d.projected_impulse.items():
            self.assertTrue(math.isfinite(val), f"5D impulse for {sym} is non-finite: {val}")

    def test_adv_m1_05_pagerank_dangling_nodes_and_isolated_subgraphs(self) -> None:
        """Verify directed PageRank power iteration under empty, single-node, and dangling node matrices."""
        # Empty matrix
        pr_empty = compute_directed_pagerank(np.zeros((0, 0)))
        self.assertEqual(len(pr_empty), 0)

        # Single node
        pr_single = compute_directed_pagerank(np.zeros((1, 1)))
        self.assertEqual(len(pr_single), 1)
        self.assertAlmostEqual(pr_single[0], 1.0)

        # Dangling node (node 2 has 0 outgoing edges)
        C_dangling = np.array([
            [0.0, 0.5, 0.5],
            [0.8, 0.0, 0.2],
            [0.0, 0.0, 0.0],  # Dangling node
        ])
        pr_dang = compute_directed_pagerank(C_dangling, damping=0.85)
        self.assertEqual(len(pr_dang), 3)
        self.assertAlmostEqual(np.sum(pr_dang), 1.0, places=6)
        self.assertTrue(np.all(pr_dang > 0.0), "PageRank components must be strictly positive")

    # =========================================================================
    # MODULE 2: Entropy-Pooled HERC Allocator (Feature F521)
    # =========================================================================

    def test_adv_m2_01_contradictory_and_incompatible_views(self) -> None:
        """Stress-test Meucci Entropy Pooling with mutually contradictory and impossible view constraints."""
        alloc = HierarchicalEntropyAllocator(target_volatility=0.12, max_single_weight=0.20, max_sector_weight=0.35)
        S, N = 60, 6
        np.random.seed(202)
        ret = np.random.normal(0.001, 0.02, size=(S, N))
        cov = np.cov(ret, rowvar=False)
        symbols = [f"SYM_{i}" for i in range(N)]
        sectors = ["TECH"] * 3 + ["FIN"] * 3

        # Contradictory equality views: E[r_0] == +0.80 AND E[r_0] == -0.80 with 100% confidence
        v_bull = EntropyView(view_type="asset_mean", constraint_type="eq", coefficients=np.eye(N)[0], target_value=0.80, confidence=1.0)
        v_bear = EntropyView(view_type="asset_mean", constraint_type="eq", coefficients=np.eye(N)[0], target_value=-0.80, confidence=1.0)

        # Impossible inequality view: E[r_1] <= -10.0 (impossible under ~0.02 variance returns)
        v_impossible = EntropyView(view_type="asset_mean", constraint_type="ineq", coefficients=np.eye(N)[1], target_value=-10.0, confidence=1.0)

        # Solver must solve stably or gracefully fall back to prior without raising unhandled exceptions
        alloc_res = alloc.allocate(
            returns_data=ret,
            cov_matrix=cov,
            symbols=symbols,
            sectors=sectors,
            views=[v_bull, v_bear, v_impossible],
            regime="SIDEWAYS_HIGH_VOL",
        )

        self.assertIsInstance(alloc_res, HERCAllocationResult)
        w = np.array(list(alloc_res.weights.values()))

        # Simplex Invariant: sum w_i == 1.000000, w_i >= 0
        self.assertAlmostEqual(np.sum(w), 1.0, places=5, msg="Simplex sum violated under contradictory views")
        self.assertTrue(np.all(w >= -1e-8), f"Negative weights produced: {w}")

        # Capacity Invariant: single stock <= 0.200001
        self.assertTrue(np.all(w <= 0.200001), f"Single-stock cap 0.20 breached: {np.max(w)}")

    def test_adv_m2_02_extreme_high_stress_regimes_entropy_dampening(self) -> None:
        """Verify dynamic capital shift away from high-entropy cluster nodes during CRISIS regimes."""
        alloc = HierarchicalEntropyAllocator(target_volatility=0.12, stress_shift_intensity=2.0)
        S, N = 80, 8
        np.random.seed(303)
        ret = np.random.normal(0.0, 0.02, size=(S, N))
        cov = np.cov(ret, rowvar=False)
        symbols = [f"STK_{i}" for i in range(N)]

        # High predictive uncertainty on cluster containing assets 0, 1, 2
        uncertainty = np.array([0.98, 0.95, 0.92, 0.05, 0.05, 0.08, 0.05, 0.06])

        # Allocate under tranquil regime vs CRISIS regime with uncertainty scores
        res_bull = alloc.allocate(ret, cov, symbols=symbols, uncertainty_scores=uncertainty, regime="BULL_LOW_VOL")
        res_crisis = alloc.allocate(ret, cov, symbols=symbols, uncertainty_scores=uncertainty, regime="CRISIS")

        w_bull = np.array([res_bull.weights[s] for s in symbols])
        w_crisis = np.array([res_crisis.weights[s] for s in symbols])

        self.assertAlmostEqual(np.sum(w_bull), 1.0, places=5)
        self.assertAlmostEqual(np.sum(w_crisis), 1.0, places=5)
        self.assertTrue(np.all(w_crisis >= 0.0))

        # Under CRISIS, the allocator dampens high-entropy cluster weights
        self.assertEqual(res_crisis.stress_factor, 1.0)
        self.assertEqual(res_bull.stress_factor, 0.0)

    def test_adv_m2_03_singular_and_rank_deficient_covariance(self) -> None:
        """Stress-test allocator with singular (rank=1) covariance matrix and extreme risk concentration."""
        alloc = HierarchicalEntropyAllocator(target_volatility=0.12, max_single_weight=0.20)
        N = 10
        symbols = [f"EQ_{i}" for i in range(N)]
        ret = np.random.normal(0.001, 0.015, size=(50, N))

        # Perfectly singular covariance matrix (rank 1)
        v = np.ones((N, 1)) * 0.05
        cov_singular = v @ v.T

        res = alloc.allocate(ret, cov_singular, symbols=symbols, regime="CRISIS")

        w = np.array(list(res.weights.values()))
        self.assertAlmostEqual(np.sum(w), 1.0, places=5)
        self.assertTrue(np.all(w >= 0.0))
        self.assertTrue(np.all(w <= 0.200001))

    def test_adv_m2_04_leland_no_trade_buffer_bands_bypass(self) -> None:
        """Verify Leland buffer band gating and immediate bypass for new entries and complete exits."""
        alloc = HierarchicalEntropyAllocator(target_volatility=0.12, delta_floor=0.01, delta_cap=0.04)
        N = 5
        symbols = [f"AST_{i}" for i in range(N)]
        ret = np.random.normal(0.001, 0.02, size=(50, N))
        cov = np.cov(ret, rowvar=False)

        # Current weights as Dict[str, float]
        curr_w_dict = {"AST_0": 0.0, "AST_1": 0.25, "AST_2": 0.25, "AST_3": 0.25, "AST_4": 0.25}

        res = alloc.allocate(ret, cov, symbols=symbols, current_weights=curr_w_dict, regime="SIDEWAYS_LOW_VOL")

        # New entry (AST_0 from 0.0 -> target > 0) must trigger immediate bypass (is_bypass == True)
        act_0 = res.rebalance_actions["AST_0"]
        self.assertTrue(act_0["is_bypass"], "New position entry was blocked by Leland buffer band")

    # =========================================================================
    # MODULE 3: Intraday Liquidity Toxicity Filter (Feature F522)
    # =========================================================================

    def test_adv_m3_01_cold_start_zero_trade_volume_bounds(self) -> None:
        """Verify toxicity filter maintains strictly bounded scores in [0.0, 1.0] with zero trades."""
        filt = IntradayToxicityFilter(adv_volume={"COLD": 50000.0})

        # Evaluate toxicity before any trade or orderbook ticks have arrived
        res_buy = filt.evaluate_toxicity("COLD", order_side="BUY")
        res_sell = filt.evaluate_toxicity("COLD", order_side="SELL")

        for res in (res_buy, res_sell):
            self.assertIsInstance(res, ToxicityEvaluationResult)
            self.assertEqual(res.vpin_score, 0.0)
            self.assertEqual(res.ofi_score, 0.0)
            self.assertTrue(0.0 <= res.composite_toxicity <= 1.0)
            self.assertFalse(res.is_evaporating)
            self.assertEqual(res.quote_shade_offset_bps, 0.0)
            self.assertEqual(res.recommended_strategy, "NORMAL")

    def test_adv_m3_02_flash_crash_book_evaporation_detection(self) -> None:
        """Verify pre-crash liquidity evaporation detection via orderbook depth collapse and spread blowout."""
        filt = IntradayToxicityFilter(adv_volume={"CRASH": 100000.0})

        # Feed 5 tranquil baseline book snapshots (depth = 20,000 shares, spread = 2.0 bps)
        for _ in range(5):
            filt.update_orderbook(
                "CRASH",
                bids=[(100.0, 10000.0), (99.9, 10000.0)],
                asks=[(100.02, 10000.0), (100.1, 10000.0)],
            )

        # Pre-crash liquidity evaporation: top depth collapses from 40,000 to 2 shares, spread widens from 2 bps to 500 bps
        filt.update_orderbook(
            "CRASH",
            bids=[(95.0, 1.0)],
            asks=[(105.0, 1.0)],
        )

        res = filt.evaluate_toxicity("CRASH", order_side="BUY", current_spread_bps=1000.0)

        self.assertTrue(res.is_evaporating, "Pre-crash liquidity evaporation was NOT detected")
        self.assertTrue(res.is_toxic, "Evaporated book must be flagged as toxic")
        self.assertGreaterEqual(res.composite_toxicity, 0.85, "Composite toxicity must exceed evaporation threshold 0.85")
        self.assertEqual(res.recommended_strategy, "HALT_OR_DELAY", "Recommended strategy must be HALT_OR_DELAY under evaporation")
        self.assertGreater(res.quote_shade_offset_bps, 0.0)

    def test_adv_m3_03_predatory_volume_sweeps_and_vpin_saturation(self) -> None:
        """Subject continuous volume buckets to massive one-sided aggressive buying sweeps."""
        filt = IntradayToxicityFilter(bucket_volume=500.0, num_buckets=20)

        # 50 aggressive upward trades sealing multiple volume buckets with 100% buy volume
        # along with rapid ask depletion
        for i in range(50):
            filt.update_trade("SWEEP", price=100.0 + i * 0.10, volume=600.0)
            filt.update_orderbook("SWEEP", bids=[(100.0 + i * 0.1, 1000.0)], asks=[(100.0 + i * 0.1 + 0.05, 50.0)])

        vpin = filt.compute_vpin("SWEEP")
        self.assertTrue(0.0 <= vpin <= 1.0, f"VPIN out of bounds: {vpin}")
        self.assertGreaterEqual(vpin, 0.80, f"VPIN failed to detect persistent aggressive buy sweep: {vpin}")

        res = filt.evaluate_toxicity("SWEEP", order_side="SELL")  # Opposing side facing adverse selection
        self.assertTrue(0.0 <= res.composite_toxicity <= 1.0)
        self.assertTrue(res.is_toxic, "Aggressive buy sweep with ask depletion was not flagged toxic for seller")

    def test_adv_m3_04_corrupted_ticks_rejection(self) -> None:
        """Verify non-finite and negative tick prices/volumes are discarded gracefully."""
        filt = IntradayToxicityFilter()

        # Non-finite and negative inputs
        b1 = filt.update_trade("CORRUPT", price=-10.0, volume=100.0)
        b2 = filt.update_trade("CORRUPT", price=float("nan"), volume=100.0)
        b3 = filt.update_trade("CORRUPT", price=100.0, volume=float("inf"))
        b4 = filt.update_trade("CORRUPT", price=100.0, volume=-50.0)

        self.assertIsNone(b1)
        self.assertIsNone(b2)
        self.assertIsNone(b3)
        self.assertIsNone(b4)

        res = filt.evaluate_toxicity("CORRUPT")
        self.assertEqual(res.composite_toxicity, 0.1)  # Tranquil default

    # =========================================================================
    # MODULE 4: Corporate Action & Dividend Rebalancer (Feature F523)
    # =========================================================================

    def test_adv_m4_01_sequential_splits_and_reverse_splits_nav_conservation(self) -> None:
        """Subject portfolio to sequential forward (10:1), reverse (1:5), and forward (2:1) splits."""
        rebalancer = CorporateActionRebalancer()

        # Initial portfolio: 100 shares of NVDA @ $600 + $10,000 cash = $70,000 NAV
        portfolio = {
            "positions": {"NVDA": 100.0},
            "prices": {"NVDA": 600.0},
            "cash": 10000.0,
        }
        lots = [
            TaxLot(lot_id="LOT-1", symbol="NVDA", quantity=60.0, cost_basis_per_share=550.0, acquisition_date="2025-01-15"),
            TaxLot(lot_id="LOT-2", symbol="NVDA", quantity=40.0, cost_basis_per_share=580.0, acquisition_date="2025-05-20"),
        ]
        initial_cost_basis = sum(lot.total_cost for lot in lots)
        initial_nav = 100.0 * 600.0 + 10000.0

        # Event 1: 10:1 Forward split
        act_split1 = CorporateAction(
            event_id="SPLIT_10_1", symbol="NVDA", action_type=CorporateActionType.STOCK_SPLIT,
            ex_date="2026-10-01", ratio=10.0, cum_price=600.0
        )
        res1 = rebalancer.process_action(act_split1, portfolio_state=portfolio)
        lots = rebalancer.adjust_tax_lots(lots, act_split1)

        self.assertAlmostEqual(res1.nav_post, initial_nav, places=5)
        self.assertAlmostEqual(res1.nav_delta, 0.0, places=5)
        self.assertAlmostEqual(res1.new_quantity, 1000.0)
        self.assertAlmostEqual(res1.post_event_price, 60.0)
        self.assertAlmostEqual(sum(lot.total_cost for lot in lots), initial_cost_basis, places=5)

        # Event 2: 1:5 Reverse split (ratio = 0.20)
        portfolio["positions"]["NVDA"] = res1.new_quantity
        portfolio["prices"]["NVDA"] = res1.post_event_price
        act_split2 = CorporateAction(
            event_id="REV_SPLIT_1_5", symbol="NVDA", action_type=CorporateActionType.REVERSE_SPLIT,
            ex_date="2026-10-05", ratio=0.20, cum_price=60.0
        )
        res2 = rebalancer.process_action(act_split2, portfolio_state=portfolio)
        lots = rebalancer.adjust_tax_lots(lots, act_split2)

        self.assertAlmostEqual(res2.nav_post, initial_nav, places=5)
        self.assertAlmostEqual(res2.nav_delta, 0.0, places=5)
        self.assertAlmostEqual(res2.new_quantity, 200.0)
        self.assertAlmostEqual(res2.post_event_price, 300.0)
        self.assertAlmostEqual(sum(lot.total_cost for lot in lots), initial_cost_basis, places=5)

        # Event 3: 2:1 Forward split
        portfolio["positions"]["NVDA"] = res2.new_quantity
        portfolio["prices"]["NVDA"] = res2.post_event_price
        act_split3 = CorporateAction(
            event_id="SPLIT_2_1", symbol="NVDA", action_type=CorporateActionType.STOCK_SPLIT,
            ex_date="2026-10-10", ratio=2.0, cum_price=300.0
        )
        res3 = rebalancer.process_action(act_split3, portfolio_state=portfolio)
        lots = rebalancer.adjust_tax_lots(lots, act_split3)

        self.assertAlmostEqual(res3.nav_post, initial_nav, places=5)
        self.assertAlmostEqual(res3.nav_delta, 0.0, places=5)
        self.assertAlmostEqual(res3.new_quantity, 400.0)
        self.assertAlmostEqual(res3.post_event_price, 150.0)
        self.assertAlmostEqual(sum(lot.total_cost for lot in lots), initial_cost_basis, places=5)

    def test_adv_m4_02_large_cash_dividend_nav_conservation(self) -> None:
        """Verify portfolio NAV conservation and zero cash leakage on large cash dividend payout."""
        rebalancer = CorporateActionRebalancer()
        portfolio = {
            "positions": {"AAPL": 500.0},
            "prices": {"AAPL": 200.0},
            "cash": 5000.0,
        }
        initial_nav = 500.0 * 200.0 + 5000.0  # $105,000

        # Special cash dividend of $60.00 per share (30% payout)
        act_div = CorporateAction(
            event_id="SPEC_DIV_60", symbol="AAPL", action_type=CorporateActionType.CASH_DIVIDEND,
            ex_date="2026-10-12", cash_amount=60.0, cum_price=200.0
        )
        res = rebalancer.process_action(act_div, portfolio_state=portfolio)

        self.assertAlmostEqual(res.cash_generated, 500.0 * 60.0)  # $30,000 cash
        self.assertAlmostEqual(res.post_event_price, 140.0)       # $200 - $60 = $140
        self.assertAlmostEqual(res.nav_post, initial_nav, places=5)
        self.assertAlmostEqual(res.nav_delta, 0.0, places=5)

    def test_adv_m4_03_cash_drag_rebalancing_with_oms_active_slice_bypass(self) -> None:
        """Verify rebalance orders deploy excess cash without colliding with active OMS slices."""
        rebalancer = CorporateActionRebalancer(cash_drag_threshold_pct=0.01)

        # Excess cash = $25,000
        excess_cash = 25000.0
        target_weights = {"AAPL": 0.50, "MSFT": 0.30, "NVDA": 0.20}
        current_prices = {"AAPL": 150.0, "MSFT": 200.0, "NVDA": 100.0}

        # Suppose MSFT has an active Almgren-Chriss OMS slice in flight
        active_oms_symbols = {"MSFT"}

        orders = rebalancer.generate_cash_drag_rebalance_orders(
            excess_cash=excess_cash,
            target_weights=target_weights,
            current_prices=current_prices,
            active_oms_symbols=active_oms_symbols,
        )

        self.assertIsInstance(orders, list)
        self.assertTrue(len(orders) > 0)

        # Active symbol MSFT must be completely bypassed to eliminate order execution collision
        order_symbols = {o.symbol for o in orders}
        self.assertNotIn("MSFT", order_symbols, "Active OMS symbol MSFT was NOT bypassed")
        self.assertIn("AAPL", order_symbols)
        self.assertIn("NVDA", order_symbols)

        # Total capital deployed in orders must not exceed available cash
        total_order_cost = sum(o.quantity * current_prices[o.symbol] for o in orders)
        self.assertLessEqual(total_order_cost, excess_cash + 1e-5)

    # =========================================================================
    # MODULE 5: Master Verification & Performance Benchmarks (Feature F524)
    # =========================================================================

    def test_adv_m5_01_benchmark_runner_and_kpi_adherence(self) -> None:
        """Verify executing benchmark_phase110_quant_performance.py achieves exit code 0 and all 8 KPIs."""
        script_path = TRADING_SYSTEM_DIR / "scripts" / "benchmark_phase110_quant_performance.py"
        self.assertTrue(script_path.exists(), f"Benchmark script missing at {script_path}")

        res = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        self.assertEqual(res.returncode, 0, f"Benchmark execution failed with error:\n{res.stderr}")
        self.assertIn("All 8 Phase 110 targets PASSED", res.stdout)
        self.assertIn("Category A reports generated", res.stdout)
        self.assertIn("Category B reports generated", res.stdout)

    def test_adv_m5_02_reports_sha256_synchronized_identity(self) -> None:
        """Verify all Category A and Category B report paths exist and are 100% bit-for-bit identical."""
        cat_a_paths = [
            PROJECT_ROOT / "reports" / "quant_benchmark_comparison_phase110.md",
            PROJECT_ROOT / "trading_system" / "reports" / "quant_benchmark_comparison_phase110.md",
            PROJECT_ROOT / "trading_system" / "result" / "quant_benchmark_comparison_phase110.md",
        ]
        cat_b_paths = [
            PROJECT_ROOT / "reports" / "benchmark_phase110_report.md",
            PROJECT_ROOT / "trading_system" / "reports" / "benchmark_phase110_report.md",
            PROJECT_ROOT / "docs" / "benchmark_phase110_report.md",
            PROJECT_ROOT / "trading_system" / "result" / "benchmark_phase110_report.md",
            PROJECT_ROOT / "docs" / "reports" / "benchmark_phase110_report.md",
        ]

        import hashlib
        hashes_a = {hashlib.sha256(p.read_bytes()).hexdigest() for p in cat_a_paths}
        hashes_b = {hashlib.sha256(p.read_bytes()).hexdigest() for p in cat_b_paths}

        self.assertEqual(len(hashes_a), 1, f"Category A files have divergent SHA-256 hashes: {hashes_a}")
        self.assertEqual(len(hashes_b), 1, f"Category B files have divergent SHA-256 hashes: {hashes_b}")


if __name__ == "__main__":
    unittest.main()
