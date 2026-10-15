"""
tests/test_phase109_multi_agent_rl.py
=====================================
Comprehensive Unit, Integration, Invariant, and Adversarial Test Suite for
Multi-Agent Adversarial Reinforcement Learning Execution Policy
(Phase 109 / Feature F516 / Release R125 / v116 Production Master).

Test Categories Covered:
- Category 1: Class Exports, Dataclasses & Full Alias Trees (TC01~TC06)
- Category 2: 12D State Feature Vector & 3D Action Space Properties (TC07~TC12)
- Category 3: Vectorized Actor-Critic Forward Pass & Evaluation (TC13~TC18)
- Category 4: Adversarial Counterparties (PredatoryHFT, MomentumChaser, MarketMaker) (TC19~TC24)
- Category 5: Adversarial Limit Order Book Environment Stepping (TC25~TC30)
- Category 6: Hard ADV Participation Cap (<= 1.50%) (TC31~TC34)
- Category 7: Exact Integer Share Volume Conservation (sum q_k == Q_total) (TC35~TC40)
- Category 8: Hawkes Order Arrival Flow Modulation (T_adverse >= 0.65) (TC41~TC44)
- Category 9: Implementation Shortfall Superiority vs Static TWAP/VWAP (TC45~TC50)
- Category 10: Interface Contracts, Dual Placement & SHA-256 Mirror Hash Parity (TC51~TC55)
"""

from __future__ import annotations

import hashlib
import math
import sys
import unittest
from pathlib import Path
from typing import List

import numpy as np

# ---------------------------------------------------------------------------
# Path setup: Ensure repo root and trading_system are on sys.path
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(TRADING_SYSTEM_DIR), str(PROJECT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.execution.multi_agent_rl_execution import (
    MultiAgentRLExecutionEngine,
    ActorCriticExecutionPolicy,
    AdversarialLOBEnvironment,
    PredatoryHFTAgent,
    MomentumChaserAgent,
    AdaptiveMarketMakerAgent,
    RLExecutionState,
    RLExecutionAction,
    ExecutionSliceResult,
    MultiAgentExecutionReport,
    ExecutionOrder,
    MarketMicrostructureState,
    # Aliases
    MultiAgentRLExecutor,
    Phase109MultiAgentRLExecutor,
    AdversarialRLExecutionEngine,
    ActorCriticExecutionAgent,
    AdversarialExecutionPolicy,
    MultiAgentRLEnv,
    RLAdversarialEnvironment,
    PredatoryHFT,
    MomentumChaser,
    AdaptiveMarketMaker,
)
from trading_system.src.execution.multi_agent_rl_execution import (
    MultiAgentRLExecutionEngine as MirroredEngine,
    ActorCriticExecutionPolicy as MirroredPolicy,
    AdversarialLOBEnvironment as MirroredEnv,
)


class TestPhase109MultiAgentRL(unittest.TestCase):
    """Master Unit & Integration Test Suite for Multi-Agent Adversarial RL Execution."""

    def setUp(self) -> None:
        """Set up standard test fixtures."""
        self.engine = MultiAgentRLExecutionEngine(
            risk_aversion=1e-4,
            max_adv_participation=0.015,
            version=109,
        )
        self.default_order = ExecutionOrder(
            symbol="005930",
            quantity=10_000,
            side="BUY",
            start_price=70000.0,
            adv_shares=15_000_000.0,
            spread_bps=5.0,
            daily_volatility=0.018,
            horizon_slices=10,
        )

    # =======================================================================
    # Category 1: Class Exports, Dataclasses & Full Alias Trees (TC01~TC06)
    # =======================================================================

    def test_tc01_class_exports_exist(self) -> None:
        """TC01: Verify all required classes exist and are instantiable."""
        self.assertIsNotNone(MultiAgentRLExecutionEngine)
        self.assertIsNotNone(ActorCriticExecutionPolicy)
        self.assertIsNotNone(AdversarialLOBEnvironment)
        self.assertIsNotNone(PredatoryHFTAgent)
        self.assertIsNotNone(MomentumChaserAgent)
        self.assertIsNotNone(AdaptiveMarketMakerAgent)

    def test_tc02_alias_tree_identity(self) -> None:
        """TC02: Verify complete backward-compatibility alias tree mappings."""
        self.assertIs(MultiAgentRLExecutor, MultiAgentRLExecutionEngine)
        self.assertIs(Phase109MultiAgentRLExecutor, MultiAgentRLExecutionEngine)
        self.assertIs(AdversarialRLExecutionEngine, MultiAgentRLExecutionEngine)
        self.assertIs(ActorCriticExecutionAgent, ActorCriticExecutionPolicy)
        self.assertIs(AdversarialExecutionPolicy, ActorCriticExecutionPolicy)
        self.assertIs(MultiAgentRLEnv, AdversarialLOBEnvironment)
        self.assertIs(RLAdversarialEnvironment, AdversarialLOBEnvironment)
        self.assertIs(PredatoryHFT, PredatoryHFTAgent)
        self.assertIs(MomentumChaser, MomentumChaserAgent)
        self.assertIs(AdaptiveMarketMaker, AdaptiveMarketMakerAgent)

    def test_tc03_dataclasses_instantiation(self) -> None:
        """TC03: Verify dataclasses can be initialized with default and custom values."""
        state = RLExecutionState(
            time_progress=0.5,
            inventory_ratio=0.5,
            spread_bps=10.0,
            obi=0.1,
            hawkes_intensity=0.6,
            hawkes_arrival_imbalance=0.2,
            adverse_toxicity=0.3,
            volatility=0.02,
            hft_frontrun_risk=0.1,
            cumulative_drift_bps=2.5,
            execution_pace_dev=0.0,
            depth_ratio=1.0,
        )
        self.assertAlmostEqual(state.time_progress, 0.5)

        action = RLExecutionAction(slice_fraction=1.2, aggressiveness=-0.4, cancel_threshold_bps=0.3)
        self.assertEqual(action.action_type, "PASSIVE_MAKER")

        slice_res = ExecutionSliceResult(
            step=0,
            quantity=1000,
            action_type="MID_PEG",
            exec_price=100.0,
            slippage_bps=0.0,
            hft_frontrun_detected=False,
            remaining_inventory=9000,
        )
        self.assertEqual(slice_res.quantity, 1000)

    def test_tc04_mirrored_import_parity(self) -> None:
        """TC04: Verify imported classes from both trees have identical type names and behaviors."""
        self.assertEqual(MultiAgentRLExecutionEngine.__name__, MirroredEngine.__name__)
        self.assertEqual(ActorCriticExecutionPolicy.__name__, MirroredPolicy.__name__)
        self.assertEqual(AdversarialLOBEnvironment.__name__, MirroredEnv.__name__)

    def test_tc05_execution_order_defaults(self) -> None:
        """TC05: Verify ExecutionOrder helper dataclass defaults."""
        order = ExecutionOrder(symbol="AAPL", quantity=5000)
        self.assertEqual(order.side, "BUY")
        self.assertEqual(order.start_price, 100.0)
        self.assertEqual(order.horizon_slices, 10)

    def test_tc06_market_microstructure_state_defaults(self) -> None:
        """TC06: Verify MarketMicrostructureState helper dataclass defaults."""
        mkt = MarketMicrostructureState()
        self.assertEqual(mkt.mid_price, 100.0)
        self.assertEqual(mkt.spread_bps, 10.0)
        self.assertAlmostEqual(mkt.adverse_toxicity, 0.2)

    # =======================================================================
    # Category 2: 12D State Feature Vector & 3D Action Space Properties (TC07~TC12)
    # =======================================================================

    def test_tc07_state_to_vector_dimension(self) -> None:
        """TC07: Verify state.to_vector() produces exact 12D numpy float64 array."""
        state = RLExecutionState(
            time_progress=0.4,
            inventory_ratio=0.6,
            spread_bps=12.0,
            obi=-0.3,
            hawkes_intensity=0.8,
            hawkes_arrival_imbalance=-0.5,
            adverse_toxicity=0.68,
            volatility=0.025,
            hft_frontrun_risk=0.5,
            cumulative_drift_bps=15.0,
            execution_pace_dev=-0.2,
            depth_ratio=1.4,
        )
        vec = state.to_vector()
        self.assertIsInstance(vec, np.ndarray)
        self.assertEqual(vec.shape, (12,))
        self.assertEqual(vec.dtype, np.float64)

    def test_tc08_state_roundtrip_conversion(self) -> None:
        """TC08: Verify from_vector(state.to_vector()) roundtrip consistency."""
        state = RLExecutionState(
            time_progress=0.75,
            inventory_ratio=0.25,
            spread_bps=20.0,
            obi=0.5,
            hawkes_intensity=0.9,
            hawkes_arrival_imbalance=0.4,
            adverse_toxicity=0.35,
            volatility=0.015,
            hft_frontrun_risk=0.2,
            cumulative_drift_bps=-10.0,
            execution_pace_dev=0.1,
            depth_ratio=1.2,
        )
        vec = state.to_vector()
        recovered = RLExecutionState.from_vector(vec)
        self.assertAlmostEqual(state.time_progress, recovered.time_progress, places=5)
        self.assertAlmostEqual(state.inventory_ratio, recovered.inventory_ratio, places=5)
        self.assertAlmostEqual(state.spread_bps, recovered.spread_bps, places=4)
        self.assertAlmostEqual(state.obi, recovered.obi, places=5)
        self.assertAlmostEqual(state.adverse_toxicity, recovered.adverse_toxicity, places=5)

    def test_tc09_state_property_aliases(self) -> None:
        """TC09: Verify all 12 semantic property aliases match specified definitions."""
        state = RLExecutionState(
            time_progress=0.3,
            inventory_ratio=0.7,
            spread_bps=15.0,
            obi=0.2,
            hawkes_intensity=0.75,
            hawkes_arrival_imbalance=0.1,
            adverse_toxicity=0.45,
            volatility=0.02,
            hft_frontrun_risk=0.3,
            cumulative_drift_bps=5.0,
            execution_pace_dev=0.05,
            depth_ratio=1.5,
        )
        self.assertAlmostEqual(state.order_progress, 0.3)
        self.assertAlmostEqual(state.elapsed_time, 0.3)
        self.assertAlmostEqual(state.current_spread, 15.0)
        self.assertAlmostEqual(state.lob_imbalance, 0.2)
        self.assertAlmostEqual(state.micro_price_drift, 0.1)
        self.assertAlmostEqual(state.inventory_risk_factor, 0.7)
        self.assertAlmostEqual(state.volatility_regime, 0.02)
        self.assertAlmostEqual(state.volume_pace, 1.5)
        self.assertAlmostEqual(state.execution_urgency, 0.05)
        self.assertAlmostEqual(state.short_term_momentum, 5.0)

    def test_tc10_action_space_bounds(self) -> None:
        """TC10: Verify action vector extraction and clamping to [0,2] x [-1,1] x [0,1]."""
        act = RLExecutionAction(slice_fraction=3.5, aggressiveness=2.0, cancel_threshold_bps=-0.5)
        vec = act.to_vector()
        self.assertEqual(vec.shape, (3,))
        self.assertLessEqual(vec[0], 2.0)
        self.assertGreaterEqual(vec[0], 0.0)
        self.assertLessEqual(vec[1], 1.0)
        self.assertGreaterEqual(vec[1], -1.0)
        self.assertGreaterEqual(vec[2], 0.0)
        self.assertLessEqual(vec[2], 1.0)

    def test_tc11_action_type_categorization(self) -> None:
        """TC11: Verify correct mapping of continuous actions to discrete operational types."""
        a_pause = RLExecutionAction(slice_fraction=0.02, aggressiveness=0.0, cancel_threshold_bps=0.5)
        self.assertEqual(a_pause.action_type, "TACTICAL_PAUSE")

        a_maker = RLExecutionAction(slice_fraction=1.0, aggressiveness=-0.60, cancel_threshold_bps=0.3)
        self.assertEqual(a_maker.action_type, "PASSIVE_MAKER")

        a_mid = RLExecutionAction(slice_fraction=1.0, aggressiveness=0.0, cancel_threshold_bps=0.5)
        self.assertEqual(a_mid.action_type, "MID_PEG")

        a_taker = RLExecutionAction(slice_fraction=1.0, aggressiveness=0.80, cancel_threshold_bps=0.5)
        self.assertEqual(a_taker.action_type, "AGGRESSIVE_TAKER")

    def test_tc12_action_property_aliases(self) -> None:
        """TC12: Verify action property aliases (alpha_slice, delta_agg, theta_cancel)."""
        act = RLExecutionAction(slice_fraction=1.25, aggressiveness=0.35, cancel_threshold_bps=0.45)
        self.assertAlmostEqual(act.alpha_slice, 1.25)
        self.assertAlmostEqual(act.delta_agg, 0.35)
        self.assertAlmostEqual(act.theta_cancel, 0.45)

    # =======================================================================
    # Category 3: Vectorized Actor-Critic Forward Pass & Evaluation (TC13~TC18)
    # =======================================================================

    def test_tc13_policy_initialization(self) -> None:
        """TC13: Verify policy initialization shapes and weight matrices."""
        pol = ActorCriticExecutionPolicy(state_dim=12, action_dim=3, hidden_dim=64)
        self.assertEqual(pol.W1.shape, (64, 12))
        self.assertEqual(pol.W2.shape, (64, 64))
        self.assertEqual(pol.W_mu.shape, (3, 64))
        self.assertEqual(pol.W_v.shape, (1, 64))

    def test_tc14_policy_forward_pass_shapes(self) -> None:
        """TC14: Verify forward pass produces 3D action mean, log_std, and scalar V(s)."""
        pol = ActorCriticExecutionPolicy()
        state_vec = np.zeros(12, dtype=np.float64)
        mu, log_std, v = pol.forward(state_vec)
        self.assertEqual(mu.shape, (3,))
        self.assertEqual(log_std.shape, (3,))
        self.assertIsInstance(v, float)
        self.assertTrue(math.isfinite(v))

    def test_tc15_policy_deterministic_select_action(self) -> None:
        """TC15: Verify deterministic action selection is completely reproducible."""
        pol = ActorCriticExecutionPolicy(seed=42)
        state_vec = np.ones(12, dtype=np.float64) * 0.5
        act1 = pol.select_action(state_vec, deterministic=True)
        act2 = pol.select_action(state_vec, deterministic=True)
        self.assertAlmostEqual(act1.slice_fraction, act2.slice_fraction)
        self.assertAlmostEqual(act1.aggressiveness, act2.aggressiveness)
        self.assertAlmostEqual(act1.cancel_threshold_bps, act2.cancel_threshold_bps)

    def test_tc16_policy_stochastic_sampling(self) -> None:
        """TC16: Verify stochastic sampling generates actions within valid bounds with non-zero variance."""
        pol = ActorCriticExecutionPolicy(seed=123)
        state_vec = np.ones(12, dtype=np.float64) * 0.5
        actions = [pol.select_action(state_vec, deterministic=False) for _ in range(30)]
        slices = [a.slice_fraction for a in actions]
        aggs = [a.aggressiveness for a in actions]
        self.assertTrue(all(0.0 <= s <= 2.0 for s in slices))
        self.assertTrue(all(-1.0 <= g <= 1.0 for g in aggs))
        self.assertGreater(float(np.std(slices)), 0.001)

    def test_tc17_policy_evaluate_finite_and_jacobian(self) -> None:
        """TC17: Verify evaluate() returns finite value, log_prob, and entropy with Jacobian correction."""
        pol = ActorCriticExecutionPolicy()
        state = RLExecutionState(
            time_progress=0.5, inventory_ratio=0.5, spread_bps=10.0, obi=0.0,
            hawkes_intensity=0.5, hawkes_arrival_imbalance=0.0, adverse_toxicity=0.2,
            volatility=0.02, hft_frontrun_risk=0.1, cumulative_drift_bps=0.0,
            execution_pace_dev=0.0, depth_ratio=1.0,
        )
        action = RLExecutionAction(slice_fraction=1.0, aggressiveness=0.0, cancel_threshold_bps=0.5)
        v, log_prob, entropy = pol.evaluate(state, action)
        self.assertTrue(math.isfinite(v))
        self.assertTrue(math.isfinite(log_prob))
        self.assertTrue(math.isfinite(entropy))
        self.assertGreater(entropy, 0.0)

    def test_tc18_policy_train_step_gradient(self) -> None:
        """TC18: Verify online train_step processes transitions and computes valid losses."""
        pol = ActorCriticExecutionPolicy()
        transitions = [
            {
                "state": np.zeros(12),
                "action": np.array([1.0, 0.0, 0.5]),
                "reward": 1.5,
                "next_state": np.ones(12) * 0.1,
                "done": False,
            },
            {
                "state": np.ones(12) * 0.1,
                "action": np.array([1.2, -0.2, 0.4]),
                "reward": -0.5,
                "next_state": np.ones(12) * 0.2,
                "done": True,
            },
        ]
        metrics = pol.train_step(transitions)
        self.assertIn("loss", metrics)
        self.assertIn("policy_loss", metrics)
        self.assertIn("value_loss", metrics)
        self.assertTrue(math.isfinite(metrics["loss"]))

    # =======================================================================
    # Category 4: Adversarial Counterparties (PredatoryHFT, MomentumChaser, MarketMaker) (TC19~TC24)
    # =======================================================================

    def test_tc19_predatory_hft_attack_scaling(self) -> None:
        """TC19: Verify PredatoryHFT attack probability increases with large order size relative to depth."""
        hft = PredatoryHFTAgent(sensitivity=1.5, detection_threshold=0.35, seed=42)
        # Small order relative to depth (e.g. 50 shares on 2000 depth)
        attack_small, _ = hft.observe_and_attack(order_qty=50, book_depth=2000.0, arrival_imbalance=0.0)
        self.assertFalse(attack_small)

        # Large order relative to depth (e.g. 3000 shares on 1000 depth)
        attack_large, adverse_shift = hft.observe_and_attack(order_qty=3000, book_depth=1000.0, arrival_imbalance=0.5)
        self.assertTrue(attack_large)
        self.assertGreater(adverse_shift, 0.0)

    def test_tc20_predatory_hft_predictability_detection(self) -> None:
        """TC20: Verify PredatoryHFT locks onto and attacks repetitive identical TWAP tranche sizes."""
        hft = PredatoryHFTAgent(sensitivity=1.5, detection_threshold=0.35, seed=42)
        # Sequence of identical 1000 share tranches
        attacks = [hft.observe_and_attack(1000, 2000.0, 0.0)[0] for _ in range(5)]
        # Predictability detection should trigger attack in later tranches
        self.assertTrue(attacks[-1], "Repeated identical TWAP tranches should be detected by predatory HFT")

    def test_tc21_momentum_chaser_drift_pressure(self) -> None:
        """TC21: Verify MomentumChaser creates directional price drift matching net order flow."""
        mom = MomentumChaserAgent(momentum_factor=0.8)
        # Positive order flow (buying) should generate positive price pressure
        p_buy = mom.compute_drift_pressure(net_order_flow=5000.0, current_volatility=0.02)
        self.assertGreater(p_buy, 0.0)

        # Subsequent negative order flow (selling) reverses accumulated pressure
        mom.reset()
        p_sell = mom.compute_drift_pressure(net_order_flow=-5000.0, current_volatility=0.02)
        self.assertLess(p_sell, 0.0)

    def test_tc22_momentum_chaser_decay(self) -> None:
        """TC22: Verify accumulated momentum decays toward zero without new orders."""
        mom = MomentumChaserAgent(momentum_factor=0.8, decay=0.5)
        mom.compute_drift_pressure(net_order_flow=10_000.0, current_volatility=0.02)
        p1 = mom.accumulated_flow
        mom.compute_drift_pressure(net_order_flow=0.0, current_volatility=0.02)
        p2 = mom.accumulated_flow
        self.assertAlmostEqual(p2, p1 * 0.5)

    def test_tc23_market_maker_inventory_skew(self) -> None:
        """TC23: Verify AdaptiveMarketMaker skews reservation price downward when absorbing buy flow."""
        mm = AdaptiveMarketMakerAgent(gamma_inv=0.1, base_spread_bps=10.0)
        bid1, ask1, spread1 = mm.update_quotes(mid_price=100.0, net_inventory=0.0, vol=0.02)
        self.assertAlmostEqual((bid1 + ask1) / 2.0, 100.0, places=4)

        # After accumulating long inventory (+50,000 shares)
        bid2, ask2, spread2 = mm.update_quotes(mid_price=100.0, net_inventory=50_000.0, vol=0.02)
        mid_skewed = (bid2 + ask2) / 2.0
        self.assertLess(mid_skewed, 100.0, "MM reservation price must skew downward after absorbing buys")

    def test_tc24_market_maker_spread_widening(self) -> None:
        """TC24: Verify AdaptiveMarketMaker widens bid-ask spread during high volatility."""
        mm = AdaptiveMarketMakerAgent(base_spread_bps=10.0)
        _, _, spread_low_vol = mm.update_quotes(mid_price=100.0, net_inventory=0.0, vol=0.01)
        _, _, spread_high_vol = mm.update_quotes(mid_price=100.0, net_inventory=0.0, vol=0.05)
        self.assertGreater(spread_high_vol, spread_low_vol)

    # =======================================================================
    # Category 5: Adversarial Limit Order Book Environment Stepping (TC25~TC30)
    # =======================================================================

    def test_tc25_env_reset(self) -> None:
        """TC25: Verify environment reset restores initial conditions."""
        env = AdversarialLOBEnvironment(initial_price=100.0, total_quantity=10_000, total_steps=10)
        state = env.reset()
        self.assertEqual(env.mid_price, 100.0)
        self.assertEqual(env.remaining_quantity, 10_000)
        self.assertEqual(env.current_step, 0)
        self.assertAlmostEqual(state.time_progress, 0.0)

    def test_tc26_env_midpoint_dark_cross_execution(self) -> None:
        """TC26: Verify MID_PEG executes at midpoint with 0 half-spread and 0 market impact."""
        env = AdversarialLOBEnvironment(initial_price=100.0, spread_bps=10.0, total_quantity=1000, total_steps=1)
        action = RLExecutionAction(slice_fraction=1.0, aggressiveness=0.0, cancel_threshold_bps=0.5)
        next_state, reward, filled, fill_p, done = env.step(action=action, target_slice=1000, side="BUY")
        self.assertEqual(filled, 1000)
        self.assertAlmostEqual(fill_p, 100.0, places=4, msg="MID_PEG should fill at initial midpoint")

    def test_tc27_env_aggressive_taker_slippage(self) -> None:
        """TC27: Verify AGGRESSIVE_TAKER pays half spread and temporary market impact."""
        env = AdversarialLOBEnvironment(initial_price=100.0, spread_bps=10.0, total_quantity=1000, total_steps=1)
        action = RLExecutionAction(slice_fraction=1.0, aggressiveness=0.80, cancel_threshold_bps=0.5)
        next_state, reward, filled, fill_p, done = env.step(action=action, target_slice=1000, side="BUY")
        self.assertGreater(fill_p, 100.0, "Aggressive taker buy must pay half spread + impact")

    def test_tc28_env_tactical_pause_zero_fill(self) -> None:
        """TC28: Verify TACTICAL_PAUSE fills 0 shares and preserves inventory."""
        env = AdversarialLOBEnvironment(initial_price=100.0, total_quantity=1000, total_steps=5)
        action = RLExecutionAction(slice_fraction=0.0, aggressiveness=0.0, cancel_threshold_bps=0.5)
        next_state, reward, filled, fill_p, done = env.step(action=action, target_slice=0, side="BUY")
        self.assertEqual(filled, 0)
        self.assertEqual(env.remaining_quantity, 1000)

    def test_tc29_env_gym_interface_step(self) -> None:
        """TC29: Verify Gym 4-tuple step(action) compatibility."""
        env = AdversarialLOBEnvironment(initial_price=100.0, total_quantity=1000, total_steps=5)
        action_vec = np.array([1.0, 0.0, 0.5])
        obs, reward, done, info = env.step(action_vec)
        self.assertEqual(obs.shape, (12,))
        self.assertIsInstance(reward, float)
        self.assertIsInstance(done, bool)
        self.assertIn("filled_qty", info)

    def test_tc30_almgren_chriss_inventory_penalty_monotonicity(self) -> None:
        """TC30: Verify inventory penalty increases monotonically with remaining shares."""
        env1 = AdversarialLOBEnvironment(total_quantity=10_000, total_steps=10)
        env1.remaining_quantity = 8_000
        r1 = env1.step(RLExecutionAction(1.0, 0.0, 0.5), target_slice=100)[1]

        env2 = AdversarialLOBEnvironment(total_quantity=10_000, total_steps=10)
        env2.remaining_quantity = 1_000
        r2 = env2.step(RLExecutionAction(1.0, 0.0, 0.5), target_slice=100)[1]

        self.assertGreater(r2, r1, "Reward must be higher (less penalized) when remaining inventory is small")

    # =======================================================================
    # Category 6: Hard ADV Participation Cap (<= 1.50%) (TC31~TC34)
    # =======================================================================

    def test_tc31_adv_participation_cap_daily_basis(self) -> None:
        """TC31: Verify each slice quantity respects q_k <= 0.015 * ADV (daily basis)."""
        engine = MultiAgentRLExecutionEngine(max_adv_participation=0.015, participation_basis="daily")
        adv = 1_000_000.0
        total_q = 14_000  # 1.4% of ADV
        report = engine.optimize_execution_schedule(
            symbol="TEST",
            total_quantity=total_q,
            adv_shares=adv,
            horizon_slices=10,
        )
        self.assertLessEqual(report.adv_participation_max, 0.015 + 1e-9)
        for s in report.slices:
            self.assertLessEqual(s.quantity, int(0.015 * adv))

    def test_tc32_adv_participation_cap_interval_basis(self) -> None:
        """TC32: Verify each slice quantity respects q_k <= 0.015 * (ADV / K) (interval basis)."""
        engine = MultiAgentRLExecutionEngine(max_adv_participation=0.015, participation_basis="interval")
        adv = 10_000_000.0
        n_slices = 10
        slice_adv = adv / n_slices
        max_slice_allowed = int(0.015 * slice_adv)

        report = engine.optimize_execution_schedule(
            symbol="TEST_INT",
            total_quantity=max_slice_allowed * 5,
            adv_shares=adv,
            horizon_slices=n_slices,
        )
        self.assertLessEqual(report.adv_participation_max, 0.015 + 1e-9)
        for s in report.slices:
            self.assertLessEqual(s.quantity, max_slice_allowed)

    def test_tc33_adv_participation_cap_with_small_adv(self) -> None:
        """TC33: Verify ADV cap enforcement on low-liquidity stock."""
        engine = MultiAgentRLExecutionEngine(max_adv_participation=0.015)
        adv = 100_000.0
        cap_daily = int(0.015 * adv)  # 1500 shares
        report = engine.optimize_execution_schedule(
            symbol="ILLIQUID",
            total_quantity=1500,
            adv_shares=adv,
            horizon_slices=5,
        )
        self.assertLessEqual(report.adv_participation_max, 0.015 + 1e-9)

    def test_tc34_adv_participation_cap_clamping_invariant(self) -> None:
        """TC34: Verify rounding function clamps all individual tranches to cap."""
        shares = np.array([500.0, 1000.0, 2000.0, 500.0])
        cap = 800
        rounded = self.engine._round_to_exact_integers(shares, target_abs_qty=2500, cap_per_slice=cap)
        for q in rounded:
            self.assertLessEqual(q, cap)

    # =======================================================================
    # Category 7: Exact Integer Share Volume Conservation (TC35~TC40)
    # =======================================================================

    def test_tc35_volume_conservation_standard_order(self) -> None:
        """TC35: Verify sum(q_k) == Q_total for standard institutional order (10,000 shares)."""
        report = self.engine.optimize_execution_schedule(
            symbol="005930",
            total_quantity=10_000,
            horizon_slices=10,
        )
        self.assertTrue(report.is_volume_conserved)
        self.assertEqual(report.executed_quantity, 10_000)
        self.assertEqual(sum(s.quantity for s in report.slices), 10_000)

    def test_tc36_volume_conservation_odd_prime_quantity(self) -> None:
        """TC36: Verify exact integer conservation with prime quantity (e.g. 7,777 shares across 13 slices)."""
        report = self.engine.optimize_execution_schedule(
            symbol="ODD_QTY",
            total_quantity=7777,
            horizon_slices=13,
            adv_shares=2_000_000.0,
        )
        self.assertTrue(report.is_volume_conserved)
        self.assertEqual(report.executed_quantity, 7777)
        self.assertEqual(sum(s.quantity for s in report.slices), 7777)
        for s in report.slices:
            self.assertIsInstance(s.quantity, int)
            self.assertGreaterEqual(s.quantity, 0)

    def test_tc37_volume_conservation_single_share(self) -> None:
        """TC37: Verify exact volume conservation when total quantity is 1 share."""
        report = self.engine.optimize_execution_schedule(
            symbol="SINGLE",
            total_quantity=1,
            horizon_slices=5,
        )
        self.assertTrue(report.is_volume_conserved)
        self.assertEqual(report.executed_quantity, 1)
        self.assertEqual(sum(s.quantity for s in report.slices), 1)

    def test_tc38_volume_conservation_zero_shares(self) -> None:
        """TC38: Verify exact volume conservation when total quantity is 0 shares."""
        report = self.engine.optimize_execution_schedule(
            symbol="ZERO",
            total_quantity=0,
            horizon_slices=5,
        )
        self.assertTrue(report.is_volume_conserved)
        self.assertEqual(report.executed_quantity, 0)
        self.assertEqual(len(report.slices), 0)

    def test_tc39_volume_conservation_single_slice_horizon(self) -> None:
        """TC39: Verify volume conservation when horizon is exactly 1 slice."""
        report = self.engine.optimize_execution_schedule(
            symbol="ONE_SLICE",
            total_quantity=5000,
            horizon_slices=1,
            adv_shares=1_000_000.0,
        )
        self.assertTrue(report.is_volume_conserved)
        self.assertEqual(report.executed_quantity, 5000)
        self.assertEqual(len(report.slices), 1)
        self.assertEqual(report.slices[0].quantity, 5000)

    def test_tc40_volume_conservation_large_basket(self) -> None:
        """TC40: Verify volume conservation across large batch order sizes (50,000 shares across 20 slices)."""
        report = self.engine.optimize_execution_schedule(
            symbol="LARGE",
            total_quantity=50_000,
            horizon_slices=20,
            adv_shares=10_000_000.0,
        )
        self.assertTrue(report.is_volume_conserved)
        self.assertEqual(report.executed_quantity, 50_000)
        self.assertEqual(sum(s.quantity for s in report.slices), 50_000)

    # =======================================================================
    # Category 8: Hawkes Order Arrival Flow Modulation (TC41~TC44)
    # =======================================================================

    def test_tc41_hawkes_toxicity_quote_shading(self) -> None:
        """TC41: Verify quote shading triggers when adverse toxicity >= 0.65."""
        report_toxic = self.engine.optimize_execution_schedule(
            symbol="HAWKES_TOX",
            total_quantity=5000,
            horizon_slices=5,
            hawkes_signals={"adverse_toxicity": 0.85, "hawkes_intensity": 0.9, "hawkes_arrival_imbalance": -0.6},
        )
        self.assertGreaterEqual(report_toxic.metadata["adverse_toxicity"], 0.65)
        # Under high toxicity, policy should moderate pace and shade quotes
        for s in report_toxic.slices:
            self.assertIn(s.action_type, ["PASSIVE_MAKER", "MID_PEG", "TACTICAL_PAUSE"])

    def test_tc42_hawkes_taker_suppression_on_exhausted_arrival(self) -> None:
        """TC42: Verify aggressive taker is suppressed when buy arrival is exhausted (Delta lambda < -0.3)."""
        env = AdversarialLOBEnvironment(initial_price=100.0, spread_bps=10.0, total_quantity=1000, total_steps=5)
        env.adverse_toxicity = 0.80
        env.hawkes_arrival_imbalance = -0.50

        # Attempt aggressive taker order under high toxicity & exhausted arrival
        action = RLExecutionAction(slice_fraction=1.0, aggressiveness=0.8, cancel_threshold_bps=0.5)
        next_st, reward, filled, fill_p, done = env.step(action=action, target_slice=200, side="BUY")
        # Penalty should reflect adverse toxicity drag
        self.assertGreater(fill_p, 100.0 + 0.10)

    def test_tc43_hawkes_modulator_parameter_retrieval(self) -> None:
        """TC43: Verify Hawkes parameters ingested in metadata."""
        signals = {"adverse_toxicity": 0.72, "hawkes_intensity": 0.65, "hawkes_arrival_imbalance": 0.15}
        report = self.engine.optimize_execution_schedule(
            symbol="AAPL",
            total_quantity=2000,
            hawkes_signals=signals,
        )
        self.assertEqual(report.metadata["adverse_toxicity"], 0.72)
        self.assertEqual(report.metadata["hawkes_intensity"], 0.65)

    def test_tc44_tranquil_hawkes_regime(self) -> None:
        """TC44: Verify execution in tranquil regime (toxicity = 0.10, balanced arrival)."""
        signals = {"adverse_toxicity": 0.10, "hawkes_intensity": 0.30, "hawkes_arrival_imbalance": 0.0}
        report = self.engine.optimize_execution_schedule(
            symbol="TRANQUIL",
            total_quantity=2000,
            hawkes_signals=signals,
        )
        self.assertLess(report.metadata["adverse_toxicity"], 0.65)
        self.assertTrue(report.is_volume_conserved)

    # =======================================================================
    # Category 9: Implementation Shortfall Superiority vs Static TWAP/VWAP (TC45~TC50)
    # =======================================================================

    def test_tc45_rl_superiority_vs_twap_buy_side(self) -> None:
        """TC45: Verify RL execution achieves strictly lower Implementation Shortfall than TWAP (BUY)."""
        report = self.engine.optimize_execution_schedule(
            symbol="005930",
            total_quantity=10_000,
            side="BUY",
            horizon_slices=10,
            start_price=70000.0,
            spread_bps=5.0,
            adv_shares=15_000_000.0,
            daily_volatility=0.018,
            hawkes_signals={"adverse_toxicity": 0.70, "hawkes_intensity": 0.8, "hawkes_arrival_imbalance": -0.4},
        )
        self.assertGreater(
            report.cost_savings_vs_twap_bps,
            0.0,
            f"RL should outperform TWAP (RL: {report.implementation_shortfall_bps:.2f} bps, TWAP: {report.twap_shortfall_bps:.2f} bps)",
        )
        self.assertGreater(report.adverse_selection_avoided_bps, 0.0)

    def test_tc46_rl_superiority_vs_twap_sell_side(self) -> None:
        """TC46: Verify RL execution achieves strictly lower Implementation Shortfall than TWAP (SELL)."""
        report = self.engine.optimize_execution_schedule(
            symbol="005930",
            total_quantity=10_000,
            side="SELL",
            horizon_slices=10,
            start_price=70000.0,
            spread_bps=5.0,
            adv_shares=15_000_000.0,
            daily_volatility=0.018,
            hawkes_signals={"adverse_toxicity": 0.70, "hawkes_intensity": 0.8, "hawkes_arrival_imbalance": 0.4},
        )
        self.assertGreater(
            report.cost_savings_vs_twap_bps,
            0.0,
            f"RL should outperform TWAP on SELL (RL: {report.implementation_shortfall_bps:.2f} bps, TWAP: {report.twap_shortfall_bps:.2f} bps)",
        )

    def test_tc47_rl_superiority_vs_vwap(self) -> None:
        """TC47: Verify RL execution achieves lower shortfall compared to static VWAP."""
        report = self.engine.optimize_execution_schedule(
            symbol="NVDA",
            total_quantity=5000,
            side="BUY",
            horizon_slices=10,
            start_price=120.0,
            spread_bps=8.0,
            adv_shares=8_000_000.0,
            daily_volatility=0.025,
            hawkes_signals={"adverse_toxicity": 0.75, "hawkes_intensity": 0.85, "hawkes_arrival_imbalance": -0.3},
        )
        self.assertLessEqual(report.implementation_shortfall_bps, report.vwap_shortfall_bps)

    def test_tc48_adverse_selection_avoided_bps_positive(self) -> None:
        """TC48: Verify adverse selection avoided is non-negative and finite."""
        report = self.engine.optimize_execution_schedule(
            symbol="MSFT",
            total_quantity=3000,
            horizon_slices=8,
            adv_shares=5_000_000.0,
        )
        self.assertGreaterEqual(report.adverse_selection_avoided_bps, 0.0)
        self.assertTrue(math.isfinite(report.adverse_selection_avoided_bps))

    def test_tc49_average_execution_price_consistency_buy(self) -> None:
        """TC49: Verify average execution price equals total cash / total shares for BUY."""
        report = self.engine.optimize_execution_schedule(
            symbol="AMZN",
            total_quantity=4000,
            side="BUY",
            horizon_slices=8,
            start_price=180.0,
        )
        tot_cash = sum(s.quantity * s.exec_price for s in report.slices)
        computed_avg = tot_cash / report.executed_quantity
        self.assertAlmostEqual(report.average_exec_price, computed_avg, places=4)

    def test_tc50_average_execution_price_consistency_sell(self) -> None:
        """TC50: Verify average execution price equals total cash / total shares for SELL."""
        report = self.engine.optimize_execution_schedule(
            symbol="GOOGL",
            total_quantity=4000,
            side="SELL",
            horizon_slices=8,
            start_price=160.0,
        )
        tot_cash = sum(s.quantity * s.exec_price for s in report.slices)
        computed_avg = tot_cash / report.executed_quantity
        self.assertAlmostEqual(report.average_exec_price, computed_avg, places=4)

    # =======================================================================
    # Category 10: Interface Contracts, Dual Placement & Mirror Hash Parity (TC51~TC55)
    # =======================================================================

    def test_tc51_execute_order_interface_contract(self) -> None:
        """TC51: Verify execute_order() interface contract from SCOPE.md."""
        order = ExecutionOrder(symbol="000660", quantity=3000, side="BUY", start_price=180000.0)
        mkt = MarketMicrostructureState(mid_price=180000.0, spread_bps=6.0, adverse_toxicity=0.68)
        report = self.engine.execute_order(order=order, market_state=mkt)
        self.assertIsInstance(report, MultiAgentExecutionReport)
        self.assertEqual(report.symbol, "000660")
        self.assertEqual(report.executed_quantity, 3000)
        self.assertTrue(report.is_volume_conserved)

    def test_tc52_execute_order_dict_contract(self) -> None:
        """TC52: Verify execute_order() works with standard dictionary specification."""
        order_dict = {
            "symbol": "TSLA",
            "quantity": 2500,
            "side": "BUY",
            "start_price": 240.0,
            "adv_shares": 10_000_000.0,
            "horizon_slices": 5,
        }
        report = self.engine.execute_order(order=order_dict)
        self.assertEqual(report.symbol, "TSLA")
        self.assertEqual(report.executed_quantity, 2500)

    def test_tc53_compute_optimal_trajectory_contract(self) -> None:
        """TC53: Verify compute_optimal_trajectory() returns slice list satisfying volume conservation."""
        slices = self.engine.compute_optimal_trajectory(
            total_qty=6000,
            adv=4_000_000.0,
            urgency=0.7,
            horizon_slices=6,
        )
        self.assertEqual(len(slices), 6)
        self.assertEqual(sum(s.quantity for s in slices), 6000)

    def test_tc54_dual_placement_sha256_hash_parity(self) -> None:
        """TC54: Verify bit-for-bit SHA-256 identical parity between dual-placement paths."""
        path1 = PROJECT_ROOT / "src" / "execution" / "multi_agent_rl_execution.py"
        path2 = TRADING_SYSTEM_DIR / "src" / "execution" / "multi_agent_rl_execution.py"

        self.assertTrue(path1.exists(), f"Path does not exist: {path1}")
        self.assertTrue(path2.exists(), f"Path does not exist: {path2}")

        h1 = hashlib.sha256(path1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(path2.read_bytes()).hexdigest()

        self.assertEqual(
            h1,
            h2,
            f"Dual-placement hash mismatch!\nsrc: {h1}\ntrading_system: {h2}",
        )

    def test_tc55_version_flag_and_backward_compatibility(self) -> None:
        """TC55: Verify version attribute and is_phase109 backward compatibility flags."""
        self.assertEqual(self.engine.version, 109)
        self.assertTrue(self.engine.is_phase109)
        old_engine = MultiAgentRLExecutionEngine(version=108)
        self.assertFalse(old_engine.is_phase109)


if __name__ == "__main__":
    unittest.main()
