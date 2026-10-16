"""
tests/test_phase114_hierarchical_ppo.py
Unit & Integration Tests for Hierarchical PPO Allocator & Policy Distillation (Phase 114, Features F542 & F543).
"""

import math
import numpy as np
import pytest

from src.ai.hierarchical_ppo_allocator import (
    FACTOR_FAMILIES,
    HierarchicalPPOAllocator,
    LelandCostBuffer,
    create_hierarchical_ppo_allocator,
)
from src.ai.rl_policy_distillation import (
    DistilledStudentPolicy,
    MarketRegime,
    RegimeAdaptivePolicyDistillationEngine,
    create_policy_distillation_engine,
)


class TestHierarchicalPPOAllocator:
    def test_leland_cost_buffer_deadband(self):
        buffer = LelandCostBuffer(linear_cost=0.0015, no_trade_band=0.01)
        curr = np.array([0.50, 0.50])
        # Shift below deadband (0.005 < 0.01)
        target_small = np.array([0.505, 0.495])
        filtered, penalty = buffer.compute_penalty_and_filter(target_small, curr)
        assert np.allclose(filtered, curr)
        assert penalty == 0.0

        # Shift above deadband (0.05 > 0.01)
        target_large = np.array([0.60, 0.40])
        filtered_l, penalty_l = buffer.compute_penalty_and_filter(target_large, curr)
        assert not np.allclose(filtered_l, curr)
        assert penalty_l > 0.0
        assert np.isclose(np.sum(filtered_l), 1.0)

    def test_hierarchical_allocation_simplex_conservation(self):
        allocator = create_hierarchical_ppo_allocator(state_dim=16, use_torch=False)
        macro_state = np.random.randn(16).astype(np.float32)

        num_assets = 10
        asset_scores = {
            fam: np.random.randn(num_assets).astype(np.float32)
            for fam in FACTOR_FAMILIES
        }
        res = allocator.allocate(macro_state, asset_scores)

        # Verify factor weights sum to 1.0
        factor_sum = sum(res.factor_weights.values())
        assert np.isclose(factor_sum, 1.0, atol=1e-5)

        # Verify asset weights sum to 1.0
        assert np.isclose(np.sum(res.asset_weights), 1.0, atol=1e-5)
        assert np.all(res.asset_weights >= 0.0)
        assert res.leland_penalty >= 0.0

    def test_gae_advantage_estimation(self):
        allocator = HierarchicalPPOAllocator(state_dim=8, use_torch=False)
        rewards = np.array([1.0, 0.5, -0.2, 0.8], dtype=np.float32)
        values = np.array([0.8, 0.6, 0.4, 0.5, 0.0], dtype=np.float32)
        dones = np.array([False, False, False, True], dtype=bool)

        adv, ret = allocator.compute_gae_advantages(rewards, values, dones)
        assert len(adv) == 4
        assert len(ret) == 4
        assert np.all(np.isfinite(adv))
        assert np.all(np.isfinite(ret))


class TestPolicyDistillationEngine:
    def test_regime_temperature_mapping(self):
        engine = create_policy_distillation_engine(input_dim=16, output_dim=5, use_torch=False)
        t_bull = engine.get_regime_temperature(MarketRegime.BULL_LOW_VOL)
        t_crisis = engine.get_regime_temperature(MarketRegime.CRISIS)
        assert t_bull < t_crisis
        assert t_bull == 1.0
        assert t_crisis == 3.5

    def test_distillation_loss_step(self):
        engine = create_policy_distillation_engine(input_dim=16, output_dim=5, use_torch=False)
        t_logits = np.array([[2.0, 1.0, 0.5, -0.5, 0.0]], dtype=np.float32)
        s_logits = np.array([[1.8, 0.9, 0.6, -0.4, 0.1]], dtype=np.float32)

        kl, ce, total = engine.distill_step(t_logits, s_logits, temperature=1.5)
        assert kl >= 0.0
        assert ce > 0.0
        assert total > 0.0

    def test_sub_50us_inference_latency(self):
        engine = create_policy_distillation_engine(input_dim=32, output_dim=10, use_torch=False)
        metrics = engine.evaluate_latency_and_parity(num_samples=1500)
        assert metrics.is_sub_50us, f"Latency {metrics.mean_inference_us}us exceeded 50us"
        assert metrics.mean_inference_us < 50.0
