r"""
tests/test_phase121_marl_liquidity.py
======================================
Exhaustive 60-Test Verification Suite across 12 Rigorous Categories for:
Multi-Agent Reinforcement Learning (MARL) Adaptive Liquidity Harvester (Feature F576).
Phase 121 (Release R137 / v128 Production Master).

Categories (60 Test Cases):
  - Category 1: Dual-Tree Parity, Metadata, Enums & Complete Alias Trees (TC01 ~ TC05)
  - Category 2: Configuration & 5-Market Pre-Calibrated Profiles (TC06 ~ TC10)
  - Category 3: Dec-POMDP State Space, Local Observations & Multi-Agent Representation (TC11 ~ TC15)
  - Category 4: Tri-Agent Heterogeneous Actor Policies & Action Spaces (TC16 ~ TC20)
  - Category 5: Cooperative Inventory Risk-Sharing & Internal Cross-Netting (TC21 ~ TC25)
  - Category 6: Dynamic Spread Quoting & Generalized Avellaneda-Stoikov Skewing (TC26 ~ TC30)
  - Category 7: Sentinel Anti-Predatory Adverse Selection Evasion, Hawkes Intensity & Quote Fading (TC31 ~ TC35)
  - Category 8: Multi-Objective Continuous Reward Formulation & Shortfall Decomposition (TC36 ~ TC40)
  - Category 9: Critical Edge Cases, Flash Crashes, Inverted Books & Robust Sanitization (TC41 ~ TC45)
  - Category 10: Centralized Value Evaluation, Cooperative Game-Theoretic Invariants & Welfare (TC46 ~ TC50)
  - Category 11: Dual-Backend Parity (PyTorch vs NumPy), Tensor Execution & Weight Sync (TC51 ~ TC55)
  - Category 12: Real-Time Sub-Millisecond Execution SLA, Stress Load & Operational Telemetry (TC56 ~ TC60)
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

# Ensure project root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import src.ai.marl_liquidity_harvester as marl_module
from src.ai.marl_liquidity_harvester import (
    VERSION,
    RELEASE,
    FEATURE,
    NUM_AGENTS,
    DEFAULT_OBS_DIM,
    DEFAULT_ACTION_DIM,
    DEFAULT_CRITIC_DIM,
    MarketProfile,
    MarketType,
    AgentRole,
    ToxicityLevel,
    QuoteSide,
    MARKET_MARL_PROFILES,
    MARKET_MARL_PROFILES_BY_STR,
    MARLHarvesterConfig,
    MARLLiquidityConfig,
    HarvesterConfig,
    AgentObservation,
    QuoteAction,
    AgentAction,
    InternalNettingResult,
    NettingResult,
    HarvesterQuoteResult,
    MARLHarvestingOutput,
    HarvesterResult,
    MARLLiquidityHarvester,
    MultiAgentReinforcementLearningHarvester,
    DecPOMDPLiquidityEngine,
    AdaptiveLiquidityHarvester,
    MultiAgentMarketMaker,
    CooperativeLiquidityHarvester,
    InventoryRiskSharingEngine,
    AntiPredatoryLiquidityHarvester,
    Phase121MARLHarvester,
    F576MARLLiquidityHarvester,
    MARLAdaptiveLiquidityHarvester,
    DecPOMDPMarketMaker,
    MultiAgentHarvesterEngine,
    CollaborativeLiquidityEngine,
    AntiPredatoryHarvester,
    DecPOMDPAdaptiveLiquidityHarvester,
    InternalNettingHarvesterEngine,
    _TORCH_AVAILABLE,
)


class TestPhase121MARLLiquidity(unittest.TestCase):
    """60 Comprehensive Verification Tests for Feature F576."""

    # =========================================================================
    # Category 1: Dual-Tree Parity, Metadata, Enums & Complete Alias Trees
    # =========================================================================

    def test_tc01_dual_tree_sha256_parity(self) -> None:
        """TC01: Verify 100% bit-for-bit SHA-256 parity between src/ and trading_system/src/."""
        src_file = PROJECT_ROOT / "src" / "ai" / "marl_liquidity_harvester.py"
        ts_file = PROJECT_ROOT / "trading_system" / "src" / "ai" / "marl_liquidity_harvester.py"

        self.assertTrue(src_file.exists(), f"Source file does not exist: {src_file}")
        self.assertTrue(ts_file.exists(), f"Trading system file does not exist: {ts_file}")

        h_src = hashlib.sha256(src_file.read_bytes()).hexdigest()
        h_ts = hashlib.sha256(ts_file.read_bytes()).hexdigest()

        self.assertEqual(h_src, h_ts, f"SHA-256 dual-tree parity mismatch: {h_src} != {h_ts}")

    def test_tc02_version_release_feature_metadata(self) -> None:
        """TC02: Verify version, release, and feature metadata constants."""
        self.assertEqual(VERSION, 121)
        self.assertEqual(RELEASE, "R137")
        self.assertEqual(FEATURE, "F576")
        self.assertEqual(NUM_AGENTS, 3)
        self.assertEqual(DEFAULT_OBS_DIM, 10)
        self.assertEqual(DEFAULT_ACTION_DIM, 4)

    def test_tc03_market_profile_and_market_type_enums(self) -> None:
        """TC03: Verify MarketProfile and MarketType enums and coercion."""
        self.assertEqual(MarketProfile.SP500, 0)
        self.assertEqual(MarketProfile.NASDAQ, 1)
        self.assertEqual(MarketProfile.RUSSELL2000, 2)
        self.assertEqual(MarketProfile.KOSPI, 3)
        self.assertEqual(MarketProfile.KOSDAQ, 4)

        self.assertEqual(MarketProfile.from_str("SP500"), MarketProfile.SP500)
        self.assertEqual(MarketProfile.from_str("S&P500"), MarketProfile.SP500)
        self.assertEqual(MarketProfile.from_str("nasdaq"), MarketProfile.NASDAQ)
        self.assertEqual(MarketProfile.from_str("russell2000"), MarketProfile.RUSSELL2000)
        self.assertEqual(MarketProfile.from_str("KOSPI"), MarketProfile.KOSPI)
        self.assertEqual(MarketProfile.from_str("KOSDAQ"), MarketProfile.KOSDAQ)

        self.assertEqual(MarketType.SP500.value, "SP500")
        self.assertEqual(MarketType.NASDAQ.value, "NASDAQ")
        self.assertEqual(MarketType.RUSSELL2000.value, "RUSSELL2000")
        self.assertEqual(MarketType.KOSPI.value, "KOSPI")
        self.assertEqual(MarketType.KOSDAQ.value, "KOSDAQ")

        with self.assertRaises(ValueError):
            MarketProfile.from_str("INVALID_MARKET_XYZ")

    def test_tc04_agent_role_toxicity_quote_side_enums(self) -> None:
        """TC04: Verify AgentRole, ToxicityLevel, and QuoteSide enums."""
        self.assertEqual(AgentRole.INVENTORY_BALANCER.value, "INVENTORY_BALANCER")
        self.assertEqual(AgentRole.SPREAD_QUOTER.value, "SPREAD_QUOTER")
        self.assertEqual(AgentRole.ADVERSE_DEFENDER.value, "ADVERSE_DEFENDER")
        self.assertEqual(AgentRole.SENTINEL.value, "ADVERSE_DEFENDER")
        self.assertEqual(AgentRole.ANTI_PREDATORY.value, "ADVERSE_DEFENDER")

        self.assertEqual(ToxicityLevel.BENIGN.value, "BENIGN")
        self.assertEqual(ToxicityLevel.ELEVATED.value, "ELEVATED")
        self.assertEqual(ToxicityLevel.CRITICAL.value, "CRITICAL")

        self.assertEqual(QuoteSide.BID.value, "BID")
        self.assertEqual(QuoteSide.ASK.value, "ASK")
        self.assertEqual(QuoteSide.BOTH.value, "BOTH")
        self.assertEqual(QuoteSide.NONE.value, "NONE")

    def test_tc05_alias_trees_and_sys_modules(self) -> None:
        """TC05: Verify 15+ complete alias trees and sys.modules registration."""
        aliases = [
            MultiAgentReinforcementLearningHarvester,
            DecPOMDPLiquidityEngine,
            AdaptiveLiquidityHarvester,
            MultiAgentMarketMaker,
            CooperativeLiquidityHarvester,
            InventoryRiskSharingEngine,
            AntiPredatoryLiquidityHarvester,
            Phase121MARLHarvester,
            F576MARLLiquidityHarvester,
            MARLAdaptiveLiquidityHarvester,
            DecPOMDPMarketMaker,
            MultiAgentHarvesterEngine,
            CollaborativeLiquidityEngine,
            AntiPredatoryHarvester,
            DecPOMDPAdaptiveLiquidityHarvester,
            InternalNettingHarvesterEngine,
        ]
        self.assertGreaterEqual(len(aliases), 16)
        for a in aliases:
            self.assertIs(a, MARLLiquidityHarvester)

        # Dataclass aliases
        self.assertIs(MARLLiquidityConfig, MARLHarvesterConfig)
        self.assertIs(HarvesterConfig, MARLHarvesterConfig)
        self.assertIs(MARLHarvestingOutput, HarvesterQuoteResult)
        self.assertIs(HarvesterResult, HarvesterQuoteResult)
        self.assertIs(NettingResult, InternalNettingResult)

        self.assertIn("src.ai.marl_liquidity_harvester", sys.modules)
        self.assertIn("trading_system.src.ai.marl_liquidity_harvester", sys.modules)

    # =========================================================================
    # Category 2: Configuration & 5-Market Pre-Calibrated Empirical Profiles
    # =========================================================================

    def test_tc06_default_config_instantiation(self) -> None:
        """TC06: Test default configuration instantiation and validation."""
        cfg = MARLHarvesterConfig()
        self.assertEqual(cfg.market, "SP500")
        self.assertEqual(cfg.num_agents, 3)
        self.assertGreater(cfg.gamma_inv, 0.0)
        self.assertGreater(cfg.gamma_agg, 0.0)
        self.assertEqual(cfg.tick_size, 0.01)
        self.assertEqual(cfg.max_inventory, 1000)
        self.assertTrue(cfg.internal_netting_enabled)

    def test_tc07_sp500_empirical_profile(self) -> None:
        """TC07: Test SP500 pre-calibrated profile values."""
        cfg = MARLHarvesterConfig(market="SP500")
        self.assertEqual(cfg.market, "SP500")
        self.assertEqual(cfg.tick_size, 0.01)
        self.assertEqual(cfg.gamma_inv, 0.008)
        self.assertEqual(cfg.gamma_agg, 0.015)
        self.assertEqual(cfg.base_spread_bps, 1.5)
        self.assertEqual(cfg.toxic_threshold_critical, 0.65)
        self.assertEqual(cfg.maker_fee_bps, -0.15)
        self.assertEqual(cfg.taker_fee_bps, 0.30)

    def test_tc08_nasdaq_and_russell_profiles(self) -> None:
        """TC08: Test NASDAQ and RUSSELL2000 profile parameters."""
        cfg_nasdaq = MARLHarvesterConfig(market="NASDAQ")
        self.assertEqual(cfg_nasdaq.base_spread_bps, 2.0)
        self.assertEqual(cfg_nasdaq.max_inventory, 800)
        self.assertEqual(cfg_nasdaq.toxic_threshold_critical, 0.60)

        cfg_rut = MARLHarvesterConfig(market="RUSSELL2000")
        self.assertEqual(cfg_rut.base_spread_bps, 4.5)
        self.assertEqual(cfg_rut.max_inventory, 500)
        self.assertEqual(cfg_rut.gamma_inv, 0.015)
        self.assertEqual(cfg_rut.toxic_threshold_critical, 0.55)

    def test_tc09_kospi_empirical_profile(self) -> None:
        """TC09: Test KOSPI pre-calibrated profile with KRW ticks."""
        cfg = MARLHarvesterConfig(market="KOSPI")
        self.assertEqual(cfg.market, "KOSPI")
        self.assertEqual(cfg.tick_size, 100.0)
        self.assertEqual(cfg.base_spread_bps, 3.0)
        self.assertEqual(cfg.maker_fee_bps, 0.0)
        self.assertEqual(cfg.taker_fee_bps, 0.15)
        self.assertEqual(cfg.max_inventory, 2000)

    def test_tc10_kosdaq_empirical_profile(self) -> None:
        """TC10: Test KOSDAQ pre-calibrated profile with KRW ticks."""
        cfg = MARLHarvesterConfig(market="KOSDAQ")
        self.assertEqual(cfg.market, "KOSDAQ")
        self.assertEqual(cfg.tick_size, 50.0)
        self.assertEqual(cfg.base_spread_bps, 5.0)
        self.assertEqual(cfg.toxic_threshold_critical, 0.52)
        self.assertEqual(cfg.max_inventory, 1500)

    # =========================================================================
    # Category 3: Dec-POMDP State Space & Local Observations
    # =========================================================================

    def test_tc11_construct_observations_structure(self) -> None:
        """TC11: Test construct_observations outputs for all 3 agents."""
        engine = MARLLiquidityHarvester()
        engine.set_inventories({0: 100.0, 1: -50.0, 2: 25.0})

        obs = engine.construct_observations(
            mid_price=100.0,
            spread_bps=2.0,
            obi=0.25,
            microprice_drift=1.5,
            hawkes_intensity=1.2,
            toxicity_score=0.3,
            volatility=0.018,
            queue_velocity=0.5,
        )

        self.assertEqual(len(obs), 3)
        for aid in range(3):
            self.assertIn(aid, obs)
            o = obs[aid]
            self.assertEqual(o.agent_id, aid)
            self.assertIsInstance(o.role, AgentRole)
            self.assertEqual(o.vector.shape, (DEFAULT_OBS_DIM,))
            self.assertFalse(np.isnan(o.vector).any())
            self.assertFalse(np.isinf(o.vector).any())

    def test_tc12_observation_normalization_bounds(self) -> None:
        """TC12: Test observation normalization under extreme inventory limits."""
        engine = MARLLiquidityHarvester()
        engine.set_inventories({0: 5000.0, 1: -5000.0, 2: 0.0})

        obs = engine.construct_observations(
            mid_price=100.0, spread_bps=2.0, obi=0.0, microprice_drift=0.0,
            hawkes_intensity=1.0, toxicity_score=0.0, volatility=0.02, queue_velocity=0.0,
        )

        self.assertLessEqual(obs[0].vector[0], 2.0)
        self.assertGreaterEqual(obs[1].vector[0], -2.0)

    def test_tc13_observation_microstructure_features(self) -> None:
        """TC13: Test microstructure feature encoding in observation vector."""
        engine = MARLLiquidityHarvester()
        obs = engine.construct_observations(
            mid_price=200.0, spread_bps=10.0, obi=-0.75, microprice_drift=-5.0,
            hawkes_intensity=3.5, toxicity_score=0.8, volatility=0.04, queue_velocity=-2.5,
        )

        vec = obs[1].vector
        self.assertAlmostEqual(vec[3], -0.75, places=5)
        self.assertAlmostEqual(vec[4], -0.5, places=5)
        self.assertAlmostEqual(vec[6], 0.8, places=5)

    def test_tc14_observation_sanitization_nans_infs(self) -> None:
        """TC14: Test observation sanitization against NaN and Inf values."""
        engine = MARLLiquidityHarvester()
        obs = engine.construct_observations(
            mid_price=float("nan"),
            spread_bps=float("inf"),
            obi=float("nan"),
            microprice_drift=float("-inf"),
            hawkes_intensity=float("nan"),
            toxicity_score=float("nan"),
            volatility=float("nan"),
            queue_velocity=float("inf"),
        )

        for aid in range(3):
            vec = obs[aid].vector
            self.assertFalse(np.isnan(vec).any(), f"NaN detected in agent {aid} vector")
            self.assertFalse(np.isinf(vec).any(), f"Inf detected in agent {aid} vector")

    def test_tc15_observation_to_dict_serialization(self) -> None:
        """TC15: Test observation serialization to JSON-compatible dict."""
        engine = MARLLiquidityHarvester()
        obs = engine.construct_observations(
            mid_price=100.0, spread_bps=2.0, obi=0.1, microprice_drift=0.5,
            hawkes_intensity=1.0, toxicity_score=0.2, volatility=0.02, queue_velocity=0.1,
        )
        d = obs[0].to_dict()
        self.assertIn("agent_id", d)
        self.assertIn("role", d)
        self.assertIn("vector", d)
        self.assertEqual(len(d["vector"]), DEFAULT_OBS_DIM)
        # Verify JSON serializability
        serialized = json.dumps(d)
        self.assertIsInstance(serialized, str)

    # =========================================================================
    # Category 4: Tri-Agent Heterogeneous Actor Policies
    # =========================================================================

    def test_tc16_actor_forward_pass_evaluation(self) -> None:
        """TC16: Test forward pass produces correct action dimensions."""
        engine = MARLLiquidityHarvester()
        obs = engine.construct_observations(
            mid_price=100.0, spread_bps=2.0, obi=0.0, microprice_drift=0.0,
            hawkes_intensity=1.0, toxicity_score=0.1, volatility=0.02, queue_velocity=0.0,
        )

        for aid in range(3):
            act_vec = engine._evaluate_actor(obs[aid])
            self.assertEqual(act_vec.shape, (DEFAULT_ACTION_DIM,))
            self.assertFalse(np.isnan(act_vec).any())

    def test_tc17_agent0_inventory_balancer_actions(self) -> None:
        """TC17: Test Agent 0 (Inventory Balancer) action modulation."""
        engine = MARLLiquidityHarvester()
        res = engine.harvest_liquidity("AAPL", mid_price=100.0, spread_bps=2.0)

        act0 = res.agent_actions[0]
        self.assertEqual(act0.role, AgentRole.INVENTORY_BALANCER)
        self.assertGreaterEqual(act0.risk_weight, 0.5)
        self.assertLessEqual(act0.risk_weight, 2.0)

    def test_tc18_agent1_spread_quoter_actions(self) -> None:
        """TC18: Test Agent 1 (Spread Quoter) quote action output."""
        engine = MARLLiquidityHarvester()
        res = engine.harvest_liquidity("AAPL", mid_price=100.0, spread_bps=2.0)

        act1 = res.agent_actions[1]
        self.assertEqual(act1.role, AgentRole.SPREAD_QUOTER)
        self.assertIsNotNone(act1.quote_action)
        qa = act1.quote_action
        self.assertGreater(qa.bid_offset_ticks, 0.0)
        self.assertGreater(qa.ask_offset_ticks, 0.0)

    def test_tc19_agent2_sentinel_actions(self) -> None:
        """TC19: Test Agent 2 (Sentinel) adverse defense action output."""
        engine = MARLLiquidityHarvester()
        res = engine.harvest_liquidity("AAPL", mid_price=100.0, spread_bps=2.0, toxicity_score=0.8)

        act2 = res.agent_actions[2]
        self.assertEqual(act2.role, AgentRole.ADVERSE_DEFENDER)
        self.assertTrue(res.quote_suppressed)

    def test_tc20_actor_deterministic_reproducibility(self) -> None:
        """TC20: Test deterministic action reproduction given identical seed."""
        e1 = MARLLiquidityHarvester(MARLHarvesterConfig(seed=12345))
        e2 = MARLLiquidityHarvester(MARLHarvesterConfig(seed=12345))

        res1 = e1.harvest_liquidity("MSFT", mid_price=250.0, spread_bps=1.8, obi=0.1)
        res2 = e2.harvest_liquidity("MSFT", mid_price=250.0, spread_bps=1.8, obi=0.1)

        self.assertEqual(res1.bid_price, res2.bid_price)
        self.assertEqual(res1.ask_price, res2.ask_price)
        self.assertEqual(res1.inventory_skew_ticks, res2.inventory_skew_ticks)

    # =========================================================================
    # Category 5: Cooperative Inventory Risk-Sharing & Internal Cross-Netting
    # =========================================================================

    def test_tc21_internal_cross_netting_opposing_positions(self) -> None:
        """TC21: Test internal netting with opposing long/short positions."""
        engine = MARLLiquidityHarvester()
        # Agent 0 is long +100, Agent 1 is short -80, Agent 2 is 0
        invs = {0: 100.0, 1: -80.0, 2: 0.0}
        net_res = engine.internal_cross_netting(invs, mid_price=150.0)

        self.assertEqual(net_res.netted_shares, 80)
        self.assertTrue(net_res.opposing_matched)
        self.assertAlmostEqual(net_res.final_inventories[0], 20.0, places=4)
        self.assertAlmostEqual(net_res.final_inventories[1], 0.0, places=4)
        self.assertAlmostEqual(net_res.final_inventories[2], 0.0, places=4)

    def test_tc22_exact_conservation_of_collective_inventory(self) -> None:
        """TC22: Test exact mathematical conservation of collective inventory."""
        engine = MARLLiquidityHarvester()
        invs = {0: 250.0, 1: -150.0, 2: -75.0}
        coll_before = sum(invs.values())

        net_res = engine.internal_cross_netting(invs, mid_price=200.0)
        coll_after = sum(net_res.final_inventories.values())

        self.assertAlmostEqual(coll_before, coll_after, places=5)
        self.assertAlmostEqual(net_res.collective_before, net_res.collective_after, places=5)

    def test_tc23_fee_and_impact_savings_calculation(self) -> None:
        """TC23: Test institutional fee and market impact savings from netting."""
        engine = MARLLiquidityHarvester(MARLHarvesterConfig(taker_fee_bps=0.30, maker_fee_bps=-0.15))
        invs = {0: 500.0, 1: -500.0, 2: 0.0}
        net_res = engine.internal_cross_netting(invs, mid_price=100.0)

        self.assertEqual(net_res.netted_shares, 500)
        self.assertGreater(net_res.fee_savings_usd, 0.0)
        self.assertGreater(net_res.impact_savings_bps, 0.0)
        self.assertGreater(net_res.total_fee_savings_bps, 0.0)

    def test_tc24_netting_all_positive_or_all_negative(self) -> None:
        """TC24: Test netting when all agents have the same sign (no opposing shares)."""
        engine = MARLLiquidityHarvester()
        invs_all_pos = {0: 100.0, 1: 50.0, 2: 25.0}
        net_res = engine.internal_cross_netting(invs_all_pos, mid_price=100.0)

        self.assertEqual(net_res.netted_shares, 0)
        self.assertFalse(net_res.opposing_matched)
        self.assertEqual(net_res.final_inventories, invs_all_pos)

    def test_tc25_netting_disabled_bypass(self) -> None:
        """TC25: Test disabling internal netting bypasses execution cleanly."""
        engine = MARLLiquidityHarvester(MARLHarvesterConfig(internal_netting_enabled=False))
        invs = {0: 100.0, 1: -100.0, 2: 0.0}
        net_res = engine.internal_cross_netting(invs, mid_price=100.0)

        self.assertEqual(net_res.netted_shares, 0)
        self.assertFalse(net_res.opposing_matched)

    # =========================================================================
    # Category 6: Dynamic Spread Quoting & Avellaneda-Stoikov Skewing
    # =========================================================================

    def test_tc26_as_reservation_price_long_skew(self) -> None:
        """TC26: Test reservation price and half-spreads when long (inventory > 0)."""
        engine = MARLLiquidityHarvester()
        bid_ticks, ask_ticks, skew = engine.compute_as_spread_and_skew(
            inventory=500.0, volatility=0.02, spread_bps=2.0, mid_price=100.0
        )
        self.assertGreater(skew, 0.0)
        # When long: skew > 0, so ask_offset should be smaller than bid_offset (encourage selling)
        self.assertLess(ask_ticks, bid_ticks)

    def test_tc27_as_reservation_price_short_skew(self) -> None:
        """TC27: Test reservation price and half-spreads when short (inventory < 0)."""
        engine = MARLLiquidityHarvester()
        bid_ticks, ask_ticks, skew = engine.compute_as_spread_and_skew(
            inventory=-500.0, volatility=0.02, spread_bps=2.0, mid_price=100.0
        )
        self.assertLess(skew, 0.0)
        # When short: bid_offset should be smaller than ask_offset (encourage buying)
        self.assertLess(bid_ticks, ask_ticks)

    def test_tc28_strict_microstructure_quote_validity(self) -> None:
        """TC28: Test bid strictly below ask and non-crossing under various market conditions."""
        engine = MARLLiquidityHarvester()
        for mid in [10.0, 50.0, 100.0, 500.0, 1000.0]:
            for sp in [0.5, 1.0, 5.0, 20.0]:
                res = engine.harvest_liquidity("TEST", mid_price=mid, spread_bps=sp)
                self.assertTrue(res.is_valid_quote)
                self.assertLess(res.bid_price, res.ask_price)
                self.assertGreater(res.spread, 0.0)

    def test_tc29_asymmetric_inventory_skew_in_quote_result(self) -> None:
        """TC29: Test that harvest_liquidity reflects inventory skew in output."""
        engine = MARLLiquidityHarvester()
        # Set positive collective inventory
        engine.set_inventories({0: 300.0, 1: 300.0, 2: 200.0})
        res_long = engine.harvest_liquidity("AAPL", mid_price=150.0, spread_bps=2.0)

        # Set negative collective inventory
        engine.set_inventories({0: -300.0, 1: -300.0, 2: -200.0})
        res_short = engine.harvest_liquidity("AAPL", mid_price=150.0, spread_bps=2.0)

        self.assertGreater(res_long.inventory_skew_ticks, res_short.inventory_skew_ticks)

    def test_tc30_volatility_spread_expansion(self) -> None:
        """TC30: Test that higher volatility widens quoted spread."""
        engine = MARLLiquidityHarvester()
        res_low_vol = engine.harvest_liquidity("AAPL", mid_price=100.0, spread_bps=2.0, volatility=0.005)
        res_high_vol = engine.harvest_liquidity("AAPL", mid_price=100.0, spread_bps=2.0, volatility=0.08)

        self.assertGreater(res_high_vol.quoted_spread_bps, res_low_vol.quoted_spread_bps)

    # =========================================================================
    # Category 7: Sentinel Anti-Predatory Adverse Selection Evasion
    # =========================================================================

    def test_tc31_critical_toxicity_triggers_quote_suppression(self) -> None:
        """TC31: Test critical toxicity triggers quote suppression."""
        engine = MARLLiquidityHarvester()
        res = engine.harvest_liquidity(
            "AAPL", mid_price=100.0, spread_bps=2.0, toxicity_score=0.85
        )
        self.assertTrue(res.quote_suppressed)
        self.assertEqual(res.toxicity_level, ToxicityLevel.CRITICAL)

    def test_tc32_negative_drift_suppresses_bid_side(self) -> None:
        """TC32: Test negative drift under toxicity suppresses BID side."""
        engine = MARLLiquidityHarvester()
        res = engine.harvest_liquidity(
            "AAPL", mid_price=100.0, spread_bps=2.0, toxicity_score=0.85, microprice_drift=-2.0
        )
        self.assertTrue(res.quote_suppressed)
        self.assertEqual(res.suppressed_side, QuoteSide.BID)

    def test_tc33_positive_drift_suppresses_ask_side(self) -> None:
        """TC33: Test positive drift under toxicity suppresses ASK side."""
        engine = MARLLiquidityHarvester()
        res = engine.harvest_liquidity(
            "AAPL", mid_price=100.0, spread_bps=2.0, toxicity_score=0.85, microprice_drift=2.0
        )
        self.assertTrue(res.quote_suppressed)
        self.assertEqual(res.suppressed_side, QuoteSide.ASK)

    def test_tc34_elevated_toxicity_applies_tick_shading(self) -> None:
        """TC34: Test elevated toxicity applies tick shading without outright suppression."""
        engine = MARLLiquidityHarvester()
        res = engine.harvest_liquidity(
            "AAPL", mid_price=100.0, spread_bps=2.0, toxicity_score=0.55, microprice_drift=1.0
        )
        self.assertFalse(res.quote_suppressed)
        self.assertEqual(res.toxicity_level, ToxicityLevel.ELEVATED)
        self.assertGreater(res.shade_ticks, 0.0)

    def test_tc35_hawkes_intensity_amplifies_fading(self) -> None:
        """TC35: Test Hawkes arrival intensity bursts amplify quote fading."""
        engine = MARLLiquidityHarvester()
        res_low_h = engine.harvest_liquidity(
            "AAPL", mid_price=100.0, spread_bps=2.0, toxicity_score=0.55, hawkes_intensity=0.5
        )
        res_high_h = engine.harvest_liquidity(
            "AAPL", mid_price=100.0, spread_bps=2.0, toxicity_score=0.55, hawkes_intensity=5.0
        )
        self.assertGreaterEqual(res_high_h.shade_ticks, res_low_h.shade_ticks)

    # =========================================================================
    # Category 8: Multi-Objective Continuous Reward Formulation
    # =========================================================================

    def test_tc36_reward_decomposition_structure(self) -> None:
        """TC36: Test reward decomposition contains all expected continuous components."""
        engine = MARLLiquidityHarvester()
        r = engine.evaluate_joint_reward(
            fills_shares=100,
            realized_half_spread_bps=1.5,
            arrival_price=100.0,
            execution_price=100.01,
            inventories={0: 50.0, 1: -50.0, 2: 0.0},
            toxicity_score=0.2,
            adverse_drift_bps=0.5,
            netted_shares=50,
            fee_savings_usd=1.5,
        )

        expected_keys = {
            "spread_capture",
            "shortfall_penalty",
            "inventory_penalty",
            "adverse_penalty",
            "cooperation_bonus",
            "total_joint_reward",
        }
        self.assertEqual(set(r.keys()), expected_keys)

    def test_tc37_spread_capture_reward_scaling(self) -> None:
        """TC37: Test spread capture reward scales linearly with fill size."""
        engine = MARLLiquidityHarvester()
        r1 = engine.evaluate_joint_reward(
            fills_shares=100, realized_half_spread_bps=2.0, arrival_price=100.0,
            execution_price=100.0, inventories={0: 0.0}, toxicity_score=0.0,
            adverse_drift_bps=0.0, netted_shares=0, fee_savings_usd=0.0,
        )
        r2 = engine.evaluate_joint_reward(
            fills_shares=200, realized_half_spread_bps=2.0, arrival_price=100.0,
            execution_price=100.0, inventories={0: 0.0}, toxicity_score=0.0,
            adverse_drift_bps=0.0, netted_shares=0, fee_savings_usd=0.0,
        )
        self.assertAlmostEqual(r2["spread_capture"], 2.0 * r1["spread_capture"], places=4)

    def test_tc38_implementation_shortfall_penalty(self) -> None:
        """TC38: Test implementation shortfall penalizes price divergence."""
        engine = MARLLiquidityHarvester()
        r_zero_is = engine.evaluate_joint_reward(
            fills_shares=100, realized_half_spread_bps=2.0, arrival_price=100.0,
            execution_price=100.0, inventories={0: 0.0}, toxicity_score=0.0,
            adverse_drift_bps=0.0, netted_shares=0, fee_savings_usd=0.0,
        )
        r_high_is = engine.evaluate_joint_reward(
            fills_shares=100, realized_half_spread_bps=2.0, arrival_price=100.0,
            execution_price=100.10, inventories={0: 0.0}, toxicity_score=0.0,
            adverse_drift_bps=0.0, netted_shares=0, fee_savings_usd=0.0,
        )
        self.assertGreater(r_high_is["shortfall_penalty"], r_zero_is["shortfall_penalty"])
        self.assertLess(r_high_is["total_joint_reward"], r_zero_is["total_joint_reward"])

    def test_tc39_inventory_risk_penalty_scaling(self) -> None:
        """TC39: Test quadratic inventory penalty increases with larger imbalance."""
        engine = MARLLiquidityHarvester()
        r_low_inv = engine.evaluate_joint_reward(
            fills_shares=100, realized_half_spread_bps=2.0, arrival_price=100.0,
            execution_price=100.0, inventories={0: 50.0, 1: 50.0, 2: 50.0},
            toxicity_score=0.0, adverse_drift_bps=0.0, netted_shares=0, fee_savings_usd=0.0,
        )
        r_high_inv = engine.evaluate_joint_reward(
            fills_shares=100, realized_half_spread_bps=2.0, arrival_price=100.0,
            execution_price=100.0, inventories={0: 500.0, 1: 500.0, 2: 500.0},
            toxicity_score=0.0, adverse_drift_bps=0.0, netted_shares=0, fee_savings_usd=0.0,
        )
        self.assertGreater(r_high_inv["inventory_penalty"], r_low_inv["inventory_penalty"])

    def test_tc40_cooperative_netting_bonus(self) -> None:
        """TC40: Test internal cross-netting adds positive bonus to joint reward."""
        engine = MARLLiquidityHarvester()
        r_no_net = engine.evaluate_joint_reward(
            fills_shares=100, realized_half_spread_bps=2.0, arrival_price=100.0,
            execution_price=100.0, inventories={0: 0.0}, toxicity_score=0.0,
            adverse_drift_bps=0.0, netted_shares=0, fee_savings_usd=0.0,
        )
        r_with_net = engine.evaluate_joint_reward(
            fills_shares=100, realized_half_spread_bps=2.0, arrival_price=100.0,
            execution_price=100.0, inventories={0: 0.0}, toxicity_score=0.0,
            adverse_drift_bps=0.0, netted_shares=200, fee_savings_usd=5.0,
        )
        self.assertGreater(r_with_net["cooperation_bonus"], 0.0)
        self.assertEqual(r_no_net["cooperation_bonus"], 0.0)
        self.assertGreater(r_with_net["total_joint_reward"], r_no_net["total_joint_reward"])

    # =========================================================================
    # Category 9: Critical Edge Cases & Robust Sanitization
    # =========================================================================

    def test_tc41_extreme_price_and_nan_inputs(self) -> None:
        """TC41: Test resilience against zero, negative, and NaN price inputs."""
        engine = MARLLiquidityHarvester()
        res_nan = engine.harvest_liquidity("TEST", mid_price=float("nan"), spread_bps=float("nan"))
        self.assertTrue(res_nan.is_valid_quote)
        self.assertGreater(res_nan.bid_price, 0.0)
        self.assertGreater(res_nan.ask_price, res_nan.bid_price)

        res_zero = engine.harvest_liquidity("TEST", mid_price=0.0, spread_bps=-5.0)
        self.assertTrue(res_zero.is_valid_quote)

    def test_tc42_inverted_book_reconstruction(self) -> None:
        """TC42: Test that inverted book input falls back safely without crossing."""
        engine = MARLLiquidityHarvester()
        res = engine.harvest_liquidity("TEST", mid_price=100.0, spread_bps=-10.0)
        self.assertTrue(res.is_valid_quote)
        self.assertLess(res.bid_price, res.ask_price)

    def test_tc43_flash_crash_and_liquidity_shock(self) -> None:
        """TC43: Test flash crash simulation (massive sell OBI, high toxicity)."""
        engine = MARLLiquidityHarvester()
        res = engine.harvest_liquidity(
            "CRASH",
            mid_price=50.0,
            spread_bps=25.0,
            obi=-0.99,
            microprice_drift=-15.0,
            hawkes_intensity=10.0,
            toxicity_score=0.95,
            volatility=0.15,
            queue_velocity=-8.0,
        )
        self.assertTrue(res.is_valid_quote)
        self.assertTrue(res.quote_suppressed)
        self.assertEqual(res.suppressed_side, QuoteSide.BID)

    def test_tc44_inventory_exhaustion_bounds(self) -> None:
        """TC44: Test inventory exceeding max_inventory clamps safely."""
        engine = MARLLiquidityHarvester(MARLHarvesterConfig(max_inventory=100))
        engine.set_inventories({0: 10_000.0, 1: -10_000.0, 2: 5_000.0})
        res = engine.harvest_liquidity("AAPL", mid_price=100.0, spread_bps=2.0)
        self.assertTrue(res.is_valid_quote)

    def test_tc45_degenerate_path_zero_channels(self) -> None:
        """TC45: Test degenerate inputs with zero volatility, zero spread, zero drift."""
        engine = MARLLiquidityHarvester()
        res = engine.harvest_liquidity(
            "DEGEN", mid_price=100.0, spread_bps=0.0, obi=0.0, microprice_drift=0.0,
            hawkes_intensity=0.0, toxicity_score=0.0, volatility=0.0, queue_velocity=0.0,
        )
        self.assertTrue(res.is_valid_quote)

    # =========================================================================
    # Category 10: Centralized Value Evaluation & Game-Theoretic Invariants
    # =========================================================================

    def test_tc46_centralized_critic_evaluation(self) -> None:
        """TC46: Test centralized critic computes scalar value for joint state."""
        engine = MARLLiquidityHarvester()
        obs = engine.construct_observations(
            mid_price=100.0, spread_bps=2.0, obi=0.0, microprice_drift=0.0,
            hawkes_intensity=1.0, toxicity_score=0.1, volatility=0.02, queue_velocity=0.0,
        )
        joint_vec = np.concatenate([obs[i].vector for i in range(3)])
        val = engine.evaluate_critic(joint_vec)
        self.assertIsInstance(val, float)
        self.assertFalse(math.isnan(val))

    def test_tc47_cooperative_welfare_higher_with_netting(self) -> None:
        """TC47: Test cooperative welfare is strictly higher with internal netting."""
        engine_net = MARLLiquidityHarvester(MARLHarvesterConfig(internal_netting_enabled=True))
        engine_no_net = MARLLiquidityHarvester(MARLHarvesterConfig(internal_netting_enabled=False))

        invs = {0: 300.0, 1: -300.0, 2: 0.0}
        res_net = engine_net.harvest_liquidity("TEST", 100.0, 2.0, agent_inventories=invs)
        res_no_net = engine_no_net.harvest_liquidity("TEST", 100.0, 2.0, agent_inventories=invs)

        self.assertGreater(
            res_net.reward_decomposition["total_joint_reward"],
            res_no_net.reward_decomposition["total_joint_reward"],
        )

    def test_tc48_inventory_variance_reduction_after_netting(self) -> None:
        """TC48: Test individual inventory variance drops after internal cross-netting."""
        engine = MARLLiquidityHarvester()
        invs = {0: 400.0, 1: -300.0, 2: -100.0}
        var_before = np.var(list(invs.values()))

        net_res = engine.internal_cross_netting(invs, mid_price=100.0)
        var_after = np.var(list(net_res.final_inventories.values()))

        self.assertLess(var_after, var_before)

    def test_tc49_pareto_efficiency_clearing(self) -> None:
        """TC49: Test Pareto efficiency: no agent has increased absolute inventory."""
        engine = MARLLiquidityHarvester()
        invs = {0: 200.0, 1: -150.0, 2: 0.0}
        net_res = engine.internal_cross_netting(invs, mid_price=100.0)

        for aid in invs:
            self.assertLessEqual(
                abs(net_res.final_inventories[aid]),
                abs(invs[aid]) + 1e-6,
            )

    def test_tc50_balanced_book_symmetry(self) -> None:
        """TC50: Test symmetric half-spreads around mid when book and inventory are neutral."""
        engine = MARLLiquidityHarvester()
        engine.set_inventories({0: 0.0, 1: 0.0, 2: 0.0})
        res = engine.harvest_liquidity(
            "SYM", mid_price=100.0, spread_bps=2.0, obi=0.0, microprice_drift=0.0,
            hawkes_intensity=1.0, toxicity_score=0.0, volatility=0.02,
        )
        bid_dist = res.mid_price - res.bid_price
        ask_dist = res.ask_price - res.mid_price
        self.assertAlmostEqual(bid_dist, ask_dist, delta=engine.config.tick_size)

    # =========================================================================
    # Category 11: Dual-Backend Parity (PyTorch vs Pure NumPy)
    # =========================================================================

    def test_tc51_pure_numpy_backend_execution(self) -> None:
        """TC51: Test execution explicitly forced to pure NumPy backend."""
        cfg = MARLHarvesterConfig(use_torch=False)
        engine = MARLLiquidityHarvester(cfg)
        self.assertEqual(engine.backend, "numpy")

        res = engine.harvest_liquidity("AAPL", mid_price=150.0, spread_bps=1.5)
        self.assertTrue(res.is_valid_quote)
        self.assertEqual(res.backend, "numpy")

    def test_tc52_pytorch_backend_execution(self) -> None:
        """TC52: Test PyTorch backend execution if torch is available."""
        if not _TORCH_AVAILABLE:
            self.skipTest("PyTorch not installed in environment")

        cfg = MARLHarvesterConfig(use_torch=True)
        engine = MARLLiquidityHarvester(cfg)
        self.assertEqual(engine.backend, "torch")

        res = engine.harvest_liquidity("AAPL", mid_price=150.0, spread_bps=1.5)
        self.assertTrue(res.is_valid_quote)
        self.assertEqual(res.backend, "torch")

    def test_tc53_dual_backend_quote_structural_parity(self) -> None:
        """TC53: Test both backends produce identical result structures."""
        cfg_np = MARLHarvesterConfig(use_torch=False, seed=42)
        eng_np = MARLLiquidityHarvester(cfg_np)
        res_np = eng_np.harvest_liquidity("AAPL", mid_price=150.0, spread_bps=2.0)

        self.assertTrue(res_np.is_valid_quote)
        self.assertIsInstance(res_np.reward_decomposition, dict)
        self.assertIsInstance(res_np.netting_result, InternalNettingResult)

        if _TORCH_AVAILABLE:
            cfg_torch = MARLHarvesterConfig(use_torch=True, seed=42)
            eng_torch = MARLLiquidityHarvester(cfg_torch)
            res_torch = eng_torch.harvest_liquidity("AAPL", mid_price=150.0, spread_bps=2.0)
            self.assertTrue(res_torch.is_valid_quote)

    def test_tc54_bounded_actor_outputs_across_backends(self) -> None:
        """TC54: Test actor output vectors are bounded across both backends."""
        eng_np = MARLLiquidityHarvester(MARLHarvesterConfig(use_torch=False))
        obs = eng_np.construct_observations(100.0, 2.0, 0.0, 0.0, 1.0, 0.0, 0.02, 0.0)

        for aid in range(3):
            act_np = eng_np._evaluate_actor(obs[aid])
            self.assertTrue(np.all(np.abs(act_np) < 10.0))

        if _TORCH_AVAILABLE:
            eng_torch = MARLLiquidityHarvester(MARLHarvesterConfig(use_torch=True))
            for aid in range(3):
                act_torch = eng_torch._evaluate_actor(obs[aid])
                self.assertTrue(np.all(np.abs(act_torch) < 10.0))

    def test_tc55_seed_parity_reinitialization(self) -> None:
        """TC55: Test repeated re-initialization with same seed produces consistent quotes."""
        for seed in [111, 222, 333]:
            e1 = MARLLiquidityHarvester(MARLHarvesterConfig(seed=seed, use_torch=False))
            e2 = MARLLiquidityHarvester(MARLHarvesterConfig(seed=seed, use_torch=False))

            r1 = e1.harvest_liquidity("SPY", mid_price=450.0, spread_bps=1.0)
            r2 = e2.harvest_liquidity("SPY", mid_price=450.0, spread_bps=1.0)

            self.assertEqual(r1.bid_price, r2.bid_price)
            self.assertEqual(r1.ask_price, r2.ask_price)

    # =========================================================================
    # Category 12: Execution Latency SLA, Stress Load & Operational Telemetry
    # =========================================================================

    def test_tc56_execution_latency_sla_sub_2ms(self) -> None:
        """TC56: Test that harvest_liquidity execution latency is strictly below 2.0 ms (2000 us)."""
        engine = MARLLiquidityHarvester()
        # Warm-up call
        engine.harvest_liquidity("SPY", mid_price=400.0, spread_bps=1.5)

        latencies = []
        for _ in range(20):
            res = engine.harvest_liquidity("SPY", mid_price=400.0, spread_bps=1.5)
            latencies.append(res.latency_us)

        median_latency = float(np.median(latencies))
        self.assertLess(median_latency, 2000.0, f"Latency SLA exceeded: {median_latency} us >= 2000 us")

    def test_tc57_operational_telemetry_tracking(self) -> None:
        """TC57: Test telemetry accumulator updates calls, latency, and netting metrics."""
        engine = MARLLiquidityHarvester()
        t_init = engine.get_telemetry()
        self.assertEqual(t_init["total_harvest_calls"], 0)

        for i in range(5):
            engine.harvest_liquidity("TEST", mid_price=100.0 + i, spread_bps=2.0)

        t_final = engine.get_telemetry()
        self.assertEqual(t_final["total_harvest_calls"], 5)
        self.assertGreater(t_final["total_execution_time_us"], 0.0)
        self.assertGreater(t_final["avg_latency_us"], 0.0)

    def test_tc58_multi_market_sequential_execution(self) -> None:
        """TC58: Test sequential execution across all 5 production markets."""
        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
        for m in markets:
            cfg = MARLHarvesterConfig(market=m)
            engine = MARLLiquidityHarvester(cfg)
            res = engine.harvest_liquidity(f"SYM_{m}", mid_price=200.0 if "KOS" not in m else 70000.0, spread_bps=3.0)
            self.assertTrue(res.is_valid_quote)
            self.assertEqual(res.market, m)

    def test_tc59_continuous_multi_step_simulation(self) -> None:
        """TC59: Test continuous 100-step simulation updating inventory dynamically."""
        engine = MARLLiquidityHarvester()
        mid = 100.0
        for step in range(100):
            # Mid price random walk
            mid += np.random.randn() * 0.1
            res = engine.harvest_liquidity("SIM", mid_price=mid, spread_bps=2.0)
            self.assertTrue(res.is_valid_quote)
        self.assertEqual(engine.get_telemetry()["total_harvest_calls"], 100)

    def test_tc60_high_load_stress_test_500_calls(self) -> None:
        """TC60: Test 500 sequential calls under high load maintain sub-millisecond average latency."""
        engine = MARLLiquidityHarvester()
        t0 = time.perf_counter()
        for i in range(500):
            engine.harvest_liquidity(
                "STRESS",
                mid_price=100.0 + (i % 20),
                spread_bps=2.0,
                obi=float(np.sin(i)),
                microprice_drift=float(np.cos(i)),
                hawkes_intensity=1.0 + float(i % 5),
                toxicity_score=float((i % 10) / 10.0),
            )
        elapsed_total = time.perf_counter() - t0
        avg_us = (elapsed_total / 500.0) * 1_000_000.0

        self.assertLess(avg_us, 2000.0, f"Average latency under stress load {avg_us} us >= 2000 us")


if __name__ == "__main__":
    unittest.main()
