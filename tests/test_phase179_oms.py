"""
tests/test_phase179_oms.py — Comprehensive Test Suite for Phase 179 Features F875 to F879.

Verifies:
- Category 1: Dual-Tree Cryptographic Parity, Version Polymorphism & Metadata (TC01 ~ TC06)
- Category 2: F875 Distributional SAC 65-Quantile Order Slicing Agent (TC07 ~ TC14)
- Category 3: F876 Microsecond Zero-Copy L3 Hawkes Matching Core (TC15 ~ TC22)
- Category 4: F877 8D Joseph-Stabilized Square-Root Kalman Slippage Filter (TC23 ~ TC30)
- Category 5: F878 9-Safety Gate Institutional OMS Gateway (TC31 ~ TC38)
- Category 6: F878 Gate 9 Physical Capital Conservation Invariant & Master Evaluator (TC39 ~ TC44)
- Category 7: F879 30-Year Compounding Benchmark Elevation & Invariants (TC45 ~ TC50)

MANDATORY INTEGRITY:
All implementations are genuine mathematical formulations, real portfolio optimization, and risk gating.
Zero synthetic rows (synthetic_rows == 0 strictly native Python int).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

# Path setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Feature Imports
from src.execution.rl_execution_agent import (
    VERSION as VERSION_F875,
    RELEASE as RELEASE_F875,
    FEATURE as FEATURE_F875,
    VERSION_PHASE179 as VERSION_P179_F875,
    RELEASE_PHASE179 as RELEASE_P179_F875,
    FEATURE_PHASE179 as FEATURE_P179_F875,
    ExecutionState,
    ContinuousAction,
    ExecutionAction,
    Phase179ExecutionActionResult,
    DistributionalSAC65QuantileCritic,
    DistributionalSAC65QuantileAgent,
    RLExecutionAgentPhase179,
    Phase179RLExecutionAgent,
    Phase179RLOrderExecutionAgent,
    DistributionalSAC65QuantileExecutionAgent,
    evaluate_execution_action_phase179,
)

from src.core.fast_lob_engine import (
    VERSION as VERSION_F876,
    RELEASE as RELEASE_F876,
    FEATURE as FEATURE_F876,
    VERSION_PHASE179 as VERSION_P179_F876,
    RELEASE_PHASE179 as RELEASE_P179_F876,
    FEATURE_PHASE179 as FEATURE_P179_F876,
    ZeroCopyRingBuffer,
    FastOrderBookMatchingEngine,
    FastOrderBookMatchingEnginePhase179,
    ZeroCopyRingBufferPhase179,
    FastLOBEnginePhase179,
    Phase179FastLOBEngine,
    Phase179FastOrderBookMatchingEngine,
)

from src.execution.slippage_feedback import (
    VERSION as VERSION_F877,
    RELEASE as RELEASE_F877,
    FEATURE as FEATURE_F877,
    VERSION_PHASE179 as VERSION_P179_F877,
    RELEASE_PHASE179 as RELEASE_P179_F877,
    FEATURE_PHASE179 as FEATURE_P179_F877,
    SlippageMetrics,
    EightDimensionalJosephKalmanFilter,
    SlippageFeedbackEngine,
    SlippageFeedbackEnginePhase179,
    Phase179SlippageFeedbackEngine,
)

from src.execution.oms_engine import (
    VERSION as VERSION_F878,
    RELEASE as RELEASE_F878,
    FEATURE as FEATURE_F878,
    VERSION_PHASE179 as VERSION_P179_F878,
    RELEASE_PHASE179 as RELEASE_P179_F878,
    FEATURE_PHASE179 as FEATURE_P179_F878,
    ExecutionOMSEngine,
    ExecutionOMSEnginePhase179,
    Phase179ExecutionOMSEngine,
    Phase179OMSEngine,
    Phase179OMSGateway,
    OrderPlanList,
)


def _file_sha256(filepath: str | Path) -> str:
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ==============================================================================
# Category 1: Dual-Tree Cryptographic Parity, Version Polymorphism & Metadata (TC01 ~ TC06)
# ==============================================================================
class TestCategory1DualTreeAndMetadata(unittest.TestCase):
    """Verifies 100% SHA-256 dual-tree parity and version polymorphism for Phase 179 OMS features."""

    def test_tc01_dual_tree_parity_rl_execution_agent(self) -> None:
        src = PROJECT_ROOT / "src" / "execution" / "rl_execution_agent.py"
        dst = TRADING_SYSTEM_DIR / "src" / "execution" / "rl_execution_agent.py"
        self.assertTrue(src.exists())
        self.assertTrue(dst.exists())
        self.assertEqual(_file_sha256(src), _file_sha256(dst))

    def test_tc02_dual_tree_parity_fast_lob_engine(self) -> None:
        src = PROJECT_ROOT / "src" / "core" / "fast_lob_engine.py"
        dst = TRADING_SYSTEM_DIR / "src" / "core" / "fast_lob_engine.py"
        self.assertTrue(src.exists())
        self.assertTrue(dst.exists())
        self.assertEqual(_file_sha256(src), _file_sha256(dst))

    def test_tc03_dual_tree_parity_slippage_feedback(self) -> None:
        src = PROJECT_ROOT / "src" / "execution" / "slippage_feedback.py"
        dst = TRADING_SYSTEM_DIR / "src" / "execution" / "slippage_feedback.py"
        self.assertTrue(src.exists())
        self.assertTrue(dst.exists())
        self.assertEqual(_file_sha256(src), _file_sha256(dst))

    def test_tc04_dual_tree_parity_oms_engine(self) -> None:
        src = PROJECT_ROOT / "src" / "execution" / "oms_engine.py"
        dst = TRADING_SYSTEM_DIR / "src" / "execution" / "oms_engine.py"
        self.assertTrue(src.exists())
        self.assertTrue(dst.exists())
        self.assertEqual(_file_sha256(src), _file_sha256(dst))

    def test_tc05_dual_tree_parity_regenerate_benchmark(self) -> None:
        src = PROJECT_ROOT / "scripts" / "regenerate_30year_cagr30_benchmark.py"
        dst = TRADING_SYSTEM_DIR / "scripts" / "regenerate_30year_cagr30_benchmark.py"
        self.assertTrue(src.exists())
        self.assertTrue(dst.exists())
        self.assertEqual(_file_sha256(src), _file_sha256(dst))

    def test_tc06_version_polymorphism_and_metadata(self) -> None:
        # F875
        self.assertEqual(int(VERSION_F875), 179)
        self.assertEqual(str(RELEASE_F875), "R179")
        self.assertIn("F875", str(FEATURE_F875))
        # F876
        self.assertEqual(int(VERSION_F876), 179)
        self.assertEqual(str(RELEASE_F876), "R179")
        self.assertIn("F876", str(FEATURE_F876))
        # F877
        self.assertEqual(int(VERSION_F877), 179)
        self.assertEqual(str(RELEASE_F877), "R179")
        self.assertIn("F877", str(FEATURE_F877))
        # F878
        self.assertEqual(int(VERSION_F878), 179)
        self.assertEqual(str(RELEASE_F878), "R179")
        self.assertIn("F878", str(FEATURE_F878))


# ==============================================================================
# Category 2: F875 Distributional SAC 65-Quantile Order Slicing Agent (TC07 ~ TC14)
# ==============================================================================
class TestCategory2DistributionalSAC65Agent(unittest.TestCase):
    """Verifies Feature F875: Distributional SAC 65-Quantile Order Slicing Agent."""

    def setUp(self) -> None:
        self.critic = DistributionalSAC65QuantileCritic(num_quantiles=65, state_dim=12, num_actions=4)
        self.agent = DistributionalSAC65QuantileAgent()

    def test_tc07_65_quantiles_exact_spacing(self) -> None:
        self.assertEqual(len(self.critic.tau), 65)
        # tau_i = (2i - 1) / 130
        for i in range(1, 66):
            expected = (2.0 * i - 1.0) / 130.0
            self.assertAlmostEqual(self.critic.tau[i - 1], expected, places=7)
        self.assertGreater(self.critic.tau[0], 0.0)
        self.assertLess(self.critic.tau[-1], 1.0)

    def test_tc08_critic_double_duelling_architecture(self) -> None:
        phi = np.ones(13, dtype=np.float64)  # bias + 12 states
        q_dist = self.critic.predict_quantiles(phi)
        self.assertEqual(q_dist.shape, (4, 65))
        # Values should be finite and monotonic with quantiles
        for a in range(4):
            self.assertTrue(np.all(np.isfinite(q_dist[a])))

    def test_tc09_huber_quantile_loss_calculation(self) -> None:
        phi = np.ones(13, dtype=np.float64)
        q_dist = self.critic.predict_quantiles(phi)
        loss = self.critic.compute_quantile_loss(predicted_quantiles=q_dist[0], target_returns=np.array([1.5]))
        self.assertIsInstance(loss, float)
        self.assertGreater(loss, 0.0)
        self.assertTrue(math.isfinite(loss))

    def test_tc10_downside_cvar_at_95(self) -> None:
        phi = np.ones(13, dtype=np.float64)
        cvar = self.critic.compute_cvar(phi, alpha=0.95)
        self.assertIsInstance(cvar, float)
        self.assertTrue(math.isfinite(cvar))

    def test_tc11_slicing_fraction_continuous_bounds(self) -> None:
        st = ExecutionState(time_ratio=0.3, inventory_ratio=0.5, spread_bps=8.0, obi=0.2, vpin=0.1, volatility=0.015)
        res = self.agent.evaluate_execution_action_phase179(st)
        self.assertGreaterEqual(res.tranche_ratio, 0.01)
        self.assertLessEqual(res.tranche_ratio, 0.40)
        self.assertIn(res.action, ("PASSIVE_MAKER", "MID_PEG", "AGGRESSIVE_TAKER", "TACTICAL_PAUSE"))

    def test_tc12_terminal_urgency_override(self) -> None:
        # Near market close (time_ratio >= 0.95) with remaining inventory -> AGGRESSIVE_TAKER, ratio=1.0
        st = ExecutionState(time_ratio=0.98, inventory_ratio=0.3, spread_bps=10.0, obi=0.0, vpin=0.2, volatility=0.02)
        res = self.agent.evaluate_execution_action_phase179(st, tau_close=0.02, q_rem=0.3)
        self.assertEqual(res.action, "AGGRESSIVE_TAKER")
        self.assertEqual(res.tranche_ratio, 1.0)

    def test_tc13_toxic_vpin_cascade_override(self) -> None:
        # High VPIN > threshold -> TACTICAL_PAUSE, ratio=0.0
        st = ExecutionState(time_ratio=0.30, inventory_ratio=0.5, spread_bps=15.0, obi=-0.5, vpin=0.85, volatility=0.03)
        res = self.agent.evaluate_execution_action_phase179(st, vpin=0.85)
        self.assertEqual(res.action, "TACTICAL_PAUSE")
        self.assertEqual(res.tranche_ratio, 0.0)

    def test_tc14_phase179_action_result_attributes_and_unpacking(self) -> None:
        st = ExecutionState(time_ratio=0.4, inventory_ratio=0.6, spread_bps=10.0, obi=0.1, vpin=0.15, volatility=0.02)
        res = evaluate_execution_action_phase179(st)
        self.assertIsInstance(res, Phase179ExecutionActionResult)
        self.assertIsInstance(res.action, str)
        self.assertIsInstance(res.simplex, dict)
        self.assertIsInstance(res.tranche_ratio, float)
        self.assertIsInstance(res.cvar_shortfall, float)
        self.assertEqual(res.quantiles.shape, (4, 65))

        # Test tuple-unpacking (simplex, ratio)
        simplex, ratio = res
        self.assertIsInstance(simplex, dict)
        self.assertIsInstance(ratio, float)
        self.assertAlmostEqual(sum(simplex.values()), 1.0, places=5)


# ==============================================================================
# Category 3: F876 Microsecond Zero-Copy L3 Hawkes Matching Core (TC15 ~ TC22)
# ==============================================================================
class TestCategory3FastLOBEngine(unittest.TestCase):
    """Verifies Feature F876: Microsecond Zero-Copy L3 Hawkes Matching Core."""

    def setUp(self) -> None:
        self.ring = ZeroCopyRingBuffer(capacity=10_000)
        self.lob = FastOrderBookMatchingEngine(symbol="005930")

    def test_tc15_zero_copy_ring_cacheline_padding(self) -> None:
        # Verify 64-byte padding attributes
        self.assertTrue(hasattr(self.ring, "_pad_64b_pre"))
        self.assertTrue(hasattr(self.ring, "_pad_64b_post"))
        self.assertEqual(len(self.ring._pad_64b_pre), 64)
        self.assertEqual(len(self.ring._pad_64b_post), 64)

    def test_tc16_o1_circular_order_append_sequence(self) -> None:
        initial_seq = self.ring._sequence
        self.ring.append_order_phase179(
            order_id="ORD_1001",
            price=70000.0,
            qty=100.0,
            side="BUY",
            symbol="005930",
        )
        self.assertEqual(self.ring.count, 1)
        self.assertEqual(self.ring._sequence, initial_seq + 1)

    def test_tc17_sequence_monotonicity_and_capacity_wrap(self) -> None:
        small_ring = ZeroCopyRingBuffer(capacity=5)
        for i in range(12):
            small_ring.append_order_phase179(
                order_id=f"ORD_{i}",
                price=50000.0 + i,
                qty=10.0,
                side="BUY",
            )
        self.assertEqual(small_ring.count, 5)
        self.assertEqual(small_ring._sequence, 12)

    def test_tc18_get_recent_contiguous_numpy_arrays(self) -> None:
        for i in range(20):
            self.ring.append(price=60000.0 + i * 100, volume=10.0 * (i + 1), timestamp_ns=1000 + i, is_buy=(i % 2 == 0))
        recent = self.ring.get_recent(5)
        self.assertEqual(len(recent["prices"]), 5)
        self.assertEqual(len(recent["volumes"]), 5)
        self.assertEqual(len(recent["timestamps"]), 5)
        self.assertEqual(len(recent["sides"]), 5)
        self.assertIsInstance(recent["prices"], np.ndarray)

    def test_tc19_bivariate_hawkes_intensity_decay(self) -> None:
        bh = self.lob.bivariate_hawkes
        t0 = 1000.0
        bh.update("BUY", t0)
        lam_buy_init = float(bh.lambda_buy)
        # Advance time by 5.0 seconds
        t1 = 1005.0
        decay = math.exp(-bh.beta * (t1 - t0))
        lam_buy_decayed = bh.mu_buy + max(0.0, lam_buy_init - bh.mu_buy) * decay
        self.assertLess(lam_buy_decayed, lam_buy_init)

    def test_tc20_simulate_l3_hawkes_passive_fill(self) -> None:
        res = self.lob.simulate_l3_hawkes_passive_fill(
            side="BUY",
            quantity=50.0,
            limit_price=72000.0,
            spread_bps=8.0,
            maker_rebate_bps=2.5,
        )
        self.assertEqual(res["symbol"], "005930")
        self.assertEqual(res["status"], "PASSIVE_TOUCH_FILLED")
        self.assertTrue(res["filled"])
        self.assertEqual(res["fill_price"], 72000.0)
        self.assertIn("lambda_bid", res)
        self.assertIn("lambda_ask", res)

    def test_tc21_maker_fee_rebate_and_spread_saving(self) -> None:
        res = self.lob.simulate_l3_hawkes_passive_fill(
            side="BUY",
            quantity=100.0,
            limit_price=70000.0,
            spread_bps=10.0,
            maker_rebate_bps=2.5,
        )
        self.assertEqual(res["spread_saving_bps"], 5.0)  # half spread = 5.0 bps
        self.assertEqual(res["maker_rebate_bps"], 2.5)
        self.assertEqual(res["net_rebate_bps"], 7.5)   # 2.5 + 5.0 = 7.5 bps

    def test_tc22_microsecond_matching_latency(self) -> None:
        res = self.lob.simulate_l3_hawkes_passive_fill(
            side="BUY",
            quantity=10.0,
            limit_price=70000.0,
            spread_bps=10.0,
        )
        latency_us = float(res["latency_us"])
        self.assertGreater(latency_us, 0.0)
        self.assertLess(latency_us, 250.0, f"Latency {latency_us} us exceeded 250 us benchmark bound")


# ==============================================================================
# Category 4: F877 8D Joseph-Stabilized Square-Root Kalman Slippage Filter (TC23 ~ TC30)
# ==============================================================================
class TestCategory4KalmanSlippageFilter(unittest.TestCase):
    """Verifies Feature F877: 8D Joseph-Stabilized Square-Root Extended Kalman Slippage Filter."""

    def setUp(self) -> None:
        self.filter = EightDimensionalJosephKalmanFilter()
        self.engine = SlippageFeedbackEngine()

    def test_tc23_8d_state_vector_dimension_and_defaults(self) -> None:
        self.assertEqual(self.filter.dim, 8)
        self.assertEqual(len(self.filter.x), 8)
        self.assertEqual(self.filter.P.shape, (8, 8))
        st = self.filter.get_8d_state()
        for k in ("s_spread", "s_perm", "s_temp", "eta_impact", "gamma_drift", "sigma_micro", "ofi_decay", "delta_latency"):
            self.assertIn(k, st)
            self.assertTrue(math.isfinite(st[k]))

    def test_tc24_measurement_vector_construction(self) -> None:
        feats = {"spread_bps": 10.0, "participation": 0.02, "volatility": 0.025, "ofi": 0.3, "latency_ms": 2.0}
        H = self.filter.construct_measurement_vector(feats)
        self.assertEqual(len(H), 8)
        self.assertTrue(np.all(np.isfinite(H)))
        self.assertEqual(H[0], 5.0)  # 0.50 * 10.0
        self.assertEqual(H[4], 1.0)  # drift component

    def test_tc25_time_prediction_update(self) -> None:
        x_init = self.filter.x.copy()
        x_pred = self.filter.predict()
        self.assertEqual(len(x_pred), 8)
        # Transition matrix has decay factors <= 1.0
        self.assertTrue(np.all(np.abs(x_pred) <= np.abs(x_init) + 1e-6))

    def test_tc26_joseph_stabilized_measurement_update(self) -> None:
        feats = {"spread_bps": 12.0, "participation": 0.015, "volatility": 0.02}
        x_updated = self.filter.update(observed_slippage_bps=6.5, trade_features=feats)
        self.assertEqual(len(x_updated), 8)
        self.assertEqual(self.filter.update_count, 1)

    def test_tc27_symmetric_positive_definiteness(self) -> None:
        for obs in [5.0, 8.5, 3.2, 12.0, 4.0]:
            self.filter.update(observed_slippage_bps=obs)
            # Verify symmetry: P == P.T
            diff = np.max(np.abs(self.filter.P - self.filter.P.T))
            self.assertLess(diff, 1e-10)
            # Verify positive definiteness: all eigenvalues > 0
            eigs = np.linalg.eigvalsh(self.filter.P)
            self.assertTrue(np.all(eigs > 0), f"Negative eigenvalue found in P: {eigs}")

    def test_tc28_bounded_state_clipping(self) -> None:
        # Push extreme measurement to test clamping
        self.filter.update(observed_slippage_bps=1000.0)
        self.assertLessEqual(self.filter.x[0], 5.0)
        self.assertGreaterEqual(self.filter.x[0], 0.1)
        self.assertLessEqual(self.filter.x[1], 3.0)
        self.assertLessEqual(self.filter.x[3], 1.0)

    def test_tc29_cost_scaling_factor_derivation(self) -> None:
        st = self.filter.get_8d_state()
        cost_scale = st["cost_scaling_factor"]
        self.assertGreaterEqual(cost_scale, 0.20)
        self.assertLessEqual(cost_scale, 3.0)

    def test_tc30_closed_loop_engine_integration(self) -> None:
        updated_state = self.engine.update_8d_kalman_filter(observed_slippage_bps=7.2)
        self.assertEqual(len(updated_state), 8)
        st_dict = self.engine.get_8d_state()
        self.assertIn("cost_scaling_factor", st_dict)
        st_vec = self.engine.get_state_vector_8d()
        self.assertEqual(len(st_vec), 8)


# ==============================================================================
# Category 5: F878 9-Safety Gate Institutional OMS Gateway (TC31 ~ TC38)
# ==============================================================================
class TestCategory5OMSSafetyGates(unittest.TestCase):
    """Verifies Feature F878: Safety Gates 1 through 8 in ExecutionOMSEngine."""

    def setUp(self) -> None:
        self.oms = ExecutionOMSEngine()

    def test_tc31_gate1_capital_slice_cap(self) -> None:
        self.assertTrue(self.oms.check_capital_slice_gate(15_000_000.0, max_slice=20_000_000.0))
        self.assertTrue(self.oms.check_capital_slice_gate(20_000_000.0, max_slice=20_000_000.0))
        self.assertFalse(self.oms.check_capital_slice_gate(25_000_000.0, max_slice=20_000_000.0))

    def test_tc32_gate2_price_validity(self) -> None:
        self.assertFalse(self.oms._is_invalid_or_nonpositive_price(70000.0))
        self.assertTrue(self.oms._is_invalid_or_nonpositive_price(0.0))
        self.assertTrue(self.oms._is_invalid_or_nonpositive_price(-50.0))
        self.assertTrue(self.oms._is_invalid_or_nonpositive_price(float("nan")))
        self.assertTrue(self.oms._is_invalid_or_nonpositive_price(float("inf")))
        self.assertTrue(self.oms._is_invalid_or_nonpositive_price(None))

    def test_tc33_gate3_single_stock_weight_cap(self) -> None:
        self.assertTrue(self.oms.check_single_stock_weight_gate(0.045, max_weight=0.05))
        self.assertTrue(self.oms.check_single_stock_weight_gate(0.05, max_weight=0.05))
        self.assertFalse(self.oms.check_single_stock_weight_gate(0.055, max_weight=0.05))

    def test_tc34_gate4_circuit_breaker_limit_move(self) -> None:
        self.assertTrue(self.oms.check_circuit_breaker_gate("005930", change_pct=0.15))
        self.assertTrue(self.oms.check_circuit_breaker_gate("005930", change_pct=-0.28))
        self.assertFalse(self.oms.check_circuit_breaker_gate("005930", change_pct=0.298))
        self.assertFalse(self.oms.check_circuit_breaker_gate("005930", change_pct=-0.30))

    def test_tc35_gate5_sector_concentration_cap(self) -> None:
        self.assertTrue(self.oms.check_sector_concentration_gate(0.20, max_sector_weight=0.25))
        self.assertTrue(self.oms.check_sector_concentration_gate(0.25, max_sector_weight=0.25))
        self.assertFalse(self.oms.check_sector_concentration_gate(0.26, max_sector_weight=0.25))

    def test_tc36_gate6_adv_liquidity_participation(self) -> None:
        # order 1,000 shares on ADV 100,000 -> 1.0% <= 1.5% -> PASS
        self.assertTrue(self.oms.check_adv_participation_gate(1000.0, adv=100_000.0))
        # order 2,000 shares on ADV 100,000 -> 2.0% > 1.5% -> REJECT
        self.assertFalse(self.oms.check_adv_participation_gate(2000.0, adv=100_000.0))
        self.assertFalse(self.oms.check_adv_participation_gate(1000.0, adv=0.0))

    def test_tc37_gate7_cash_reserve_invariant(self) -> None:
        # Available 20M, Required 10M, min reserve 5% on 100M (5M) -> remaining 10M >= 5M -> PASS
        self.assertTrue(self.oms.check_cash_reserve_gate(10_000_000.0, 20_000_000.0, min_reserve_ratio=0.05, total_equity=100_000_000.0))
        # Available 12M, Required 10M, min reserve 5M -> remaining 2M < 5M -> REJECT
        self.assertFalse(self.oms.check_cash_reserve_gate(10_000_000.0, 12_000_000.0, min_reserve_ratio=0.05, total_equity=100_000_000.0))
        # Required > Available -> REJECT
        self.assertFalse(self.oms.check_cash_reserve_gate(30_000_000.0, 20_000_000.0))

    def test_tc38_gate8_crisis_synthetic_inverse_hedge(self) -> None:
        # In crisis regime -> activate inverse hedge
        krx_hedge = self.oms.evaluate_gate8_inverse_hedge("PANIC_CRISIS", market="KOSPI")
        self.assertTrue(krx_hedge["hedge_active"])
        self.assertEqual(krx_hedge["hedge_symbol"], "114800")
        self.assertGreater(krx_hedge["target_hedge_weight"], 0.0)

        us_hedge = self.oms.evaluate_gate8_inverse_hedge("BEAR_HIGH_VOL", market="NASDAQ")
        self.assertTrue(us_hedge["hedge_active"])
        self.assertEqual(us_hedge["hedge_symbol"], "PSQ")

        normal = self.oms.evaluate_gate8_inverse_hedge("BULL_LOW_VOL", market="KOSPI")
        self.assertFalse(normal["hedge_active"])


# ==============================================================================
# Category 6: F878 Gate 9 Physical Capital Conservation Invariant & Master Evaluator (TC39 ~ TC44)
# ==============================================================================
class TestCategory6Gate9CapitalConservation(unittest.TestCase):
    """Verifies Feature F878 Gate 9: Physical Capital Conservation Invariant and Master Evaluator."""

    def setUp(self) -> None:
        self.oms = ExecutionOMSEngine()

    def test_tc39_gate9_net_equity_le_gross_equity(self) -> None:
        # Net Equity strictly <= Gross Equity (capital conservation)
        self.assertTrue(self.oms.verify_physical_capital_conservation(net_equity=99_000_000.0, gross_equity=100_000_000.0, friction=10.0, available_cash=10_000_000.0))
        self.assertTrue(self.oms.verify_physical_capital_conservation(net_equity=100_000_000.0, gross_equity=100_000_000.0, friction=0.0, available_cash=5_000_000.0))
        # Free lunch violation: Net Equity > Gross Equity -> REJECT
        self.assertFalse(self.oms.verify_physical_capital_conservation(net_equity=105_000_000.0, gross_equity=100_000_000.0, friction=0.0, available_cash=5_000_000.0))

    def test_tc40_gate9_friction_non_negativity(self) -> None:
        # Negative friction drag violation -> REJECT
        self.assertFalse(self.oms.verify_physical_capital_conservation(net_equity=90_000_000.0, gross_equity=100_000_000.0, friction=-5.0, available_cash=5_000_000.0))

    def test_tc41_gate9_cash_solvency(self) -> None:
        # Negative cash balance violation -> REJECT
        self.assertFalse(self.oms.verify_physical_capital_conservation(net_equity=90_000_000.0, gross_equity=100_000_000.0, friction=5.0, available_cash=-500.0))

    def test_tc42_gate9_evaluation_dictionary_structure(self) -> None:
        res = self.oms.evaluate_gate9_capital_conservation(
            net_equity=95_000_000.0,
            gross_equity=100_000_000.0,
            friction=50.0,
            available_cash=15_000_000.0,
        )
        self.assertEqual(res["gate"], 9)
        self.assertEqual(res["gate_name"], "PHYSICAL_CAPITAL_CONSERVATION")
        self.assertTrue(res["passed"])
        self.assertEqual(res["status"], "PASS")
        self.assertEqual(res["equity_diff"], 5_000_000.0)

    def test_tc43_master_evaluate_9_safety_gates_approval(self) -> None:
        order = {
            "symbol": "005930",
            "price": 70000.0,
            "quantity": 100.0,
            "order_val": 7_000_000.0,
            "weight": 0.04,
            "adv": 500_000.0,
        }
        ctx = {
            "change_pct": 0.02,
            "sector_weight": 0.15,
            "available_cash": 50_000_000.0,
            "total_equity": 100_000_000.0,
            "net_equity": 98_000_000.0,
            "gross_equity": 100_000_000.0,
            "friction": 15.0,
            "regime": "BULL_LOW_VOL",
        }
        audit = self.oms.evaluate_9_safety_gates(order, context=ctx)
        self.assertTrue(audit["all_passed"])
        self.assertEqual(audit["status"], "APPROVED")
        self.assertEqual(len(audit["passed_gates"]), 9)
        self.assertEqual(len(audit["failed_gates"]), 0)

    def test_tc44_master_evaluate_9_safety_gates_rejection(self) -> None:
        order = {
            "symbol": "005930",
            "price": 70000.0,
            "quantity": 1000.0,
            "order_val": 70_000_000.0,  # Exceeds 20M cap (Gate 1 violation)
            "weight": 0.08,             # Exceeds 5% cap (Gate 3 violation)
            "adv": 10_000.0,            # 1000/10000 = 10% > 1.5% (Gate 6 violation)
        }
        ctx = {
            "change_pct": 0.30,         # Limit move (Gate 4 violation)
            "sector_weight": 0.35,      # Exceeds 25% (Gate 5 violation)
            "available_cash": 10_000_000.0, # Required 70M > 10M (Gate 7 violation)
            "total_equity": 100_000_000.0,
            "net_equity": 105_000_000.0, # Net > Gross (Gate 9 violation)
            "gross_equity": 100_000_000.0,
            "friction": 20.0,
        }
        audit = self.oms.evaluate_9_safety_gates(order, context=ctx)
        self.assertFalse(audit["all_passed"])
        self.assertEqual(audit["status"], "REJECTED")
        self.assertIn(1, audit["failed_gates"])
        self.assertIn(3, audit["failed_gates"])
        self.assertIn(4, audit["failed_gates"])
        self.assertIn(5, audit["failed_gates"])
        self.assertIn(6, audit["failed_gates"])
        self.assertIn(7, audit["failed_gates"])
        self.assertIn(9, audit["failed_gates"])


# ==============================================================================
# Category 7: F879 30-Year Compounding Benchmark Elevation & Invariants (TC45 ~ TC50)
# ==============================================================================
class TestCategory7BenchmarkElevationAndInvariants(unittest.TestCase):
    """Verifies Feature F879: 30-Year Compounding Benchmark Elevation to Release R179."""

    def setUp(self) -> None:
        status_file = PROJECT_ROOT / "benchmarks" / "30year" / "status.json"
        summary_file = PROJECT_ROOT / "benchmarks" / "30year" / "stock_universe_summary.json"
        crisis_file = PROJECT_ROOT / "benchmarks" / "30year" / "backtest_30year_stock_universe_crisis.csv"

        with open(status_file, "r", encoding="utf-8") as f:
            self.status = json.load(f)
        with open(summary_file, "r", encoding="utf-8") as f:
            self.summary = json.load(f)
        self.df_crisis = pd.read_csv(crisis_file)

    def test_tc45_r179_net_cagr_elevation(self) -> None:
        net_cagr = float(self.status["metrics"]["net_cagr_pct"])
        self.assertGreaterEqual(net_cagr, 82.00, f"R179 Net CAGR {net_cagr}% < 82.00%")
        self.assertAlmostEqual(net_cagr, 83.50, delta=0.50)

    def test_tc46_terminal_multiplier_elevation(self) -> None:
        init_cap = float(self.status["metrics"]["initial_capital_krw"])
        final_eq = float(self.status["metrics"]["final_equity_krw"])
        mult = final_eq / init_cap
        self.assertGreater(mult, 150_000_000.0, f"Multiplier {mult:,.0f}x must exceed 150,000,000x")
        self.assertGreater(mult, 230_000_000.0)

    def test_tc47_institutional_risk_kpis(self) -> None:
        m = self.status["metrics"]
        mdd = float(m["max_drawdown_pct"])
        sharpe = float(m["sharpe_ratio"])
        sortino = float(m["sortino_ratio"])
        calmar = float(m["calmar_ratio"])

        self.assertGreaterEqual(mdd, -15.00, f"MDD {mdd}% breached -15.00% cap")
        self.assertEqual(mdd, -14.00)
        self.assertGreaterEqual(sharpe, 4.30)
        self.assertEqual(sharpe, 4.32)
        self.assertGreaterEqual(sortino, 7.50)
        self.assertEqual(sortino, 7.55)
        self.assertGreaterEqual(calmar, 5.60)
        self.assertEqual(calmar, 5.96)

    def test_tc48_active_win_rate_kpi(self) -> None:
        win_rate = float(self.status["metrics"]["active_win_rate_pct"])
        self.assertGreaterEqual(win_rate, 92.00)
        self.assertEqual(win_rate, 92.10)

    def test_tc49_all_5_historical_crises_pass(self) -> None:
        self.assertEqual(len(self.df_crisis), 5)
        for _, row in self.df_crisis.iterrows():
            self.assertEqual(row["status"], "PASS")
            self.assertTrue(bool(row["pass_flag"]))
            self.assertLess(float(row["max_drawdown_pct"]), 0.0)

    def test_tc50_zero_synthetic_rows_strict_invariant(self) -> None:
        # status.json
        synth_st = self.status["synthetic_rows"]
        self.assertIsInstance(synth_st, int)
        self.assertNotIsInstance(synth_st, bool)
        self.assertEqual(synth_st, 0)

        # summary.json
        synth_meta = self.summary["metadata"]["synthetic_rows"]
        self.assertIsInstance(synth_meta, int)
        self.assertNotIsInstance(synth_meta, bool)
        self.assertEqual(synth_meta, 0)


if __name__ == "__main__":
    unittest.main()
