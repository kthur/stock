"""
tests/test_phase110_entropy_allocator.py — Test Suite for Phase 110 Milestone M2.

Tests the Multi-Regime Hierarchical Equal Risk Contribution (HERC) with
Black-Litterman Entropy Pooling (Feature F521):
1. Module exports and backward-compatibility alias trees.
2. Meucci's Black-Litterman Entropy Pooling optimization (minimum relative entropy / KL divergence).
3. Equality and inequality view constraint satisfaction.
4. HERC tree clustering with Ward linkage on correlation distance matrices.
5. Multi-regime dynamic capital shift away from high-entropy cluster nodes under stress.
6. Simplex constraint sum(w_i) == 1.000000, non-negativity w_i >= 0, single-stock cap <= 0.20, sector cap <= 0.35.
7. 12% target annual volatility scaling and bull market cash drag eliminator.
8. Asymmetric Leland dynamic no-trade buffer bands with immediate entry/liquidation bypass.
9. Integration with UnifiedPortfolioAllocator (version >= 110 gating).
10. Dual-placement mirror hash integrity (SHA-256 bit-for-bit equivalence across src/ and trading_system/src/).
11. Edge cases: empty universe, single asset N=1, collinear / singular covariance, NaN/Inf sanitization.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import pytest

from src.risk.hierarchical_entropy_allocator import (
    EntropyView,
    EntropyPoolingResult,
    HERCClusterNode,
    HERCAllocationResult,
    HierarchicalEntropyAllocator,
    MultiRegimeEntropyPooledHERC,
    EntropyPooledHERCAllocator,
    Phase110HERCAllocator,
    BlackLittermanEntropyHERC,
    MultiRegimeHERCEntropyAllocator,
    BlackLittermanEntropyHERCAllocator,
    Phase110HERCEntropyAllocator,
    HierarchicalEqualRiskContributionEntropyAllocator,
    calculate_herc_entropy_weights,
    solve_meucci_entropy_pooling,
)
import trading_system.src.risk.hierarchical_entropy_allocator as ts_hea
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator


class TestEntropyAllocatorExportsAndAliases:
    """Verifies all class exports, version metadata, and alias trees."""

    def test_version_metadata(self):
        allocator = HierarchicalEntropyAllocator()
        assert allocator.VERSION == 110
        assert allocator.version == 110

    def test_alias_tree_identities(self):
        assert MultiRegimeEntropyPooledHERC is HierarchicalEntropyAllocator
        assert EntropyPooledHERCAllocator is HierarchicalEntropyAllocator
        assert Phase110HERCAllocator is HierarchicalEntropyAllocator
        assert BlackLittermanEntropyHERC is HierarchicalEntropyAllocator
        assert MultiRegimeHERCEntropyAllocator is HierarchicalEntropyAllocator
        assert BlackLittermanEntropyHERCAllocator is HierarchicalEntropyAllocator
        assert Phase110HERCEntropyAllocator is HierarchicalEntropyAllocator
        assert HierarchicalEqualRiskContributionEntropyAllocator is HierarchicalEntropyAllocator

    def test_dual_tree_import_equivalence(self):
        assert ts_hea.HierarchicalEntropyAllocator is not None
        assert ts_hea.HierarchicalEntropyAllocator.VERSION == 110
        assert ts_hea.MultiRegimeEntropyPooledHERC is ts_hea.HierarchicalEntropyAllocator
        assert ts_hea.calculate_herc_entropy_weights is not None

    def test_dual_placement_mirror_hash_integrity(self):
        p1 = Path("src/risk/hierarchical_entropy_allocator.py")
        p2 = Path("trading_system/src/risk/hierarchical_entropy_allocator.py")
        assert p1.exists(), f"Missing canonical file: {p1}"
        assert p2.exists(), f"Missing mirror file: {p2}"

        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        assert h1 == h2, f"Dual-placement hash mismatch: {h1} vs {h2}"
        assert len(h1) == 64


class TestMeucciEntropyPooling:
    """Tests Meucci's Black-Litterman Entropy Pooling optimization."""

    @pytest.fixture
    def synthetic_scenarios(self):
        rng = np.random.RandomState(42)
        S, N = 252, 5
        # Scenarios centered at zero with correlation
        mean = np.array([0.0005, 0.0008, 0.0003, -0.0002, 0.0006])
        vols = np.array([0.015, 0.020, 0.012, 0.025, 0.018])
        corr = np.array([
            [1.0, 0.5, 0.3, 0.1, 0.4],
            [0.5, 1.0, 0.4, 0.2, 0.5],
            [0.3, 0.4, 1.0, 0.0, 0.2],
            [0.1, 0.2, 0.0, 1.0, 0.3],
            [0.4, 0.5, 0.2, 0.3, 1.0],
        ])
        cov = np.outer(vols, vols) * corr
        L = np.linalg.cholesky(cov)
        Z = rng.randn(S, N)
        X = mean + Z @ L.T
        return X

    def test_zero_views_preserves_uniform_prior(self, synthetic_scenarios):
        allocator = HierarchicalEntropyAllocator()
        res = allocator.solve_entropy_pooling(synthetic_scenarios, views=None)

        assert res.success is True
        assert res.kl_divergence == pytest.approx(0.0, abs=1e-6)
        S = len(synthetic_scenarios)
        expected_p0 = np.full(S, 1.0 / S)
        np.testing.assert_allclose(res.posterior_probabilities, expected_p0, atol=1e-8)
        assert np.sum(res.posterior_probabilities) == pytest.approx(1.0, abs=1e-8)

    def test_equality_mean_view_satisfaction(self, synthetic_scenarios):
        allocator = HierarchicalEntropyAllocator(regularization=1e-9)
        S, N = synthetic_scenarios.shape

        # View: Asset 0 expected return is 0.0030 (significantly higher than prior)
        target_ret = 0.0030
        c_vec = np.zeros(N)
        c_vec[0] = 1.0
        view = EntropyView(
            view_type="asset_mean",
            constraint_type="eq",
            coefficients=c_vec,
            target_value=target_ret,
            confidence=1.0,
        )

        res = allocator.solve_entropy_pooling(synthetic_scenarios, views=[view])
        assert res.success is True
        assert res.kl_divergence > 0.0  # Distribution was tilted away from uniform

        # Check posterior expected return on Asset 0 matches target
        post_mu = res.posterior_expected_returns
        assert post_mu[0] == pytest.approx(target_ret, rel=1e-2, abs=1e-4)
        assert np.all(res.posterior_probabilities >= 0.0)
        assert np.sum(res.posterior_probabilities) == pytest.approx(1.0, abs=1e-8)

    def test_inequality_ranking_view_satisfaction(self, synthetic_scenarios):
        allocator = HierarchicalEntropyAllocator(regularization=1e-9)
        S, N = synthetic_scenarios.shape

        # View: Asset 1 outperforms Asset 3 by at least 0.0020
        # E[X_3 - X_1] <= -0.0020
        c_pair = np.zeros(N)
        c_pair[3] = 1.0
        c_pair[1] = -1.0
        view = EntropyView(
            view_type="ranking",
            constraint_type="ineq",
            coefficients=c_pair,
            target_value=-0.0020,
            confidence=1.0,
        )

        res = allocator.solve_entropy_pooling(synthetic_scenarios, views=[view])
        assert res.success is True
        post_mu = res.posterior_expected_returns
        assert (post_mu[1] - post_mu[3]) >= (0.0020 - 1e-4)

    def test_minimal_kl_divergence_property(self, synthetic_scenarios):
        allocator = HierarchicalEntropyAllocator(regularization=1e-9)
        S, N = synthetic_scenarios.shape
        c_vec = np.zeros(N)
        c_vec[1] = 1.0
        view = EntropyView(
            view_type="asset_mean",
            constraint_type="eq",
            coefficients=c_vec,
            target_value=0.0025,
            confidence=1.0,
        )

        res = allocator.solve_entropy_pooling(synthetic_scenarios, views=[view])
        p_opt = res.posterior_probabilities
        p0 = res.prior_probabilities
        kl_opt = res.kl_divergence

        # Perturb p_opt slightly while maintaining simplex and feasibility
        rng = np.random.RandomState(99)
        noise = rng.normal(0, 0.001, size=S)
        noise -= np.mean(noise)
        p_pert = np.maximum(p_opt + noise, 1e-12)
        p_pert /= np.sum(p_pert)

        kl_pert = float(np.sum(p_pert * np.log(p_pert / p0)))
        # Unconstrained perturbation has higher divergence or equal
        assert kl_opt <= kl_pert + 1e-4

    def test_primal_and_dual_solver_consistency(self, synthetic_scenarios):
        allocator = HierarchicalEntropyAllocator(regularization=1e-8)
        S, N = synthetic_scenarios.shape
        c_vec = np.zeros(N)
        c_vec[0] = 1.0
        view = EntropyView(
            view_type="asset_mean",
            constraint_type="eq",
            coefficients=c_vec,
            target_value=0.0015,
            confidence=1.0,
        )

        res_dual = allocator.solve_entropy_pooling(synthetic_scenarios, views=[view], use_dual_solver=True)
        res_primal = allocator.solve_entropy_pooling(synthetic_scenarios, views=[view], use_dual_solver=False)

        assert res_dual.success is True
        assert res_primal.success is True
        np.testing.assert_allclose(res_dual.posterior_expected_returns, res_primal.posterior_expected_returns, atol=1e-3)
        assert abs(res_dual.kl_divergence - res_primal.kl_divergence) < 0.05


class TestHERCTreeClustering:
    """Tests HERC dendrogram tree clustering and intra-cluster weighting."""

    def test_ward_hierarchical_clustering(self):
        allocator = HierarchicalEntropyAllocator(linkage_method="ward", max_clusters=3)
        # 6 assets: 2 correlated tech, 2 correlated energy, 2 correlated utilities
        cov = np.array([
            [0.04, 0.035, 0.005, 0.005, 0.002, 0.002],
            [0.035, 0.04, 0.005, 0.005, 0.002, 0.002],
            [0.005, 0.005, 0.09, 0.08, 0.001, 0.001],
            [0.005, 0.005, 0.08, 0.09, 0.001, 0.001],
            [0.002, 0.002, 0.001, 0.001, 0.02, 0.018],
            [0.002, 0.002, 0.001, 0.001, 0.018, 0.02],
        ])
        symbols = ["T1", "T2", "E1", "E2", "U1", "U2"]
        labels, link = allocator.cluster_hierarchical_tree(cov, symbols, max_k=3)

        assert len(labels) == 6
        assert len(np.unique(labels)) <= 3
        # Assets 0 & 1 should share a cluster, 2 & 3 share a cluster, 4 & 5 share a cluster
        assert labels[0] == labels[1]
        assert labels[2] == labels[3]
        assert labels[4] == labels[5]
        assert link is not None


class TestMultiRegimeStressCapitalShift:
    """Tests multi-regime dynamic capital shift away from high-entropy nodes."""

    def test_tranquil_bull_equal_risk_contribution(self):
        allocator = HierarchicalEntropyAllocator(stress_shift_intensity=1.5)
        # 2 clusters: Cluster 1 with risk 0.10, Cluster 2 with risk 0.20
        cluster_risks = {1: 0.10, 2: 0.20}
        cluster_entropies = {1: 0.20, 2: 0.80}

        # In BULL_LOW_VOL (stress factor 0.0), shift multiplier is 1.0 (pure ERC)
        alloc_bull = allocator.shift_cluster_capital_under_stress(
            cluster_risks=cluster_risks,
            cluster_entropies=cluster_entropies,
            regime="BULL_LOW_VOL",
        )

        # In pure ERC: w_1 / w_2 = (1/0.10) / (1/0.20) = 2.0
        assert alloc_bull[1] / alloc_bull[2] == pytest.approx(2.0, rel=1e-3)
        assert sum(alloc_bull.values()) == pytest.approx(1.0, abs=1e-7)

    def test_crisis_stress_dynamic_capital_shift(self):
        allocator = HierarchicalEntropyAllocator(stress_shift_intensity=2.0)
        # 2 clusters: equal risk, but Cluster 2 has significantly higher entropy (0.90 vs 0.10)
        cluster_risks = {1: 0.15, 2: 0.15}
        cluster_entropies = {1: 0.10, 2: 0.90}

        alloc_tranquil = allocator.shift_cluster_capital_under_stress(
            cluster_risks=cluster_risks,
            cluster_entropies=cluster_entropies,
            regime="BULL_LOW_VOL",
        )
        assert alloc_tranquil[1] == pytest.approx(alloc_tranquil[2], abs=1e-5)

        # In CRISIS (stress factor 1.0), capital must shift away from high-entropy Cluster 2
        alloc_crisis = allocator.shift_cluster_capital_under_stress(
            cluster_risks=cluster_risks,
            cluster_entropies=cluster_entropies,
            regime="CRISIS",
        )

        assert alloc_crisis[1] > alloc_crisis[2]
        # Low entropy Cluster 1 gets significant capital increase
        assert alloc_crisis[1] > 0.65
        assert alloc_crisis[2] < 0.35
        assert sum(alloc_crisis.values()) == pytest.approx(1.0, abs=1e-7)


class TestSimplexAndCapacityConstraints:
    """Tests strict simplex equality sum=1.000000, non-negativity, single-stock and sector caps."""

    def test_simplex_and_caps(self):
        allocator = HierarchicalEntropyAllocator(
            max_single_weight=0.20,
            max_sector_weight=0.35,
        )
        symbols = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
        sectors = ["TECH", "TECH", "TECH", "FIN", "FIN", "HEALTH", "HEALTH", "ENERGY"]
        # Raw weights with violation (e.g. S1 has 0.50, TECH has 0.70)
        raw_w = np.array([0.50, 0.10, 0.10, 0.10, 0.05, 0.05, 0.05, 0.05])

        w_cons = allocator.apply_capacity_constraints(
            raw_weights=raw_w,
            symbols=symbols,
            sectors=sectors,
        )

        # 1. Strict Simplex Sum
        assert np.sum(w_cons) == pytest.approx(1.000000, abs=1e-6)
        # 2. Non-negativity
        assert np.all(w_cons >= 0.0)
        # 3. Single-stock cap <= 0.20
        assert np.max(w_cons) <= 0.20 + 1e-6
        # 4. Sector cap <= 0.35
        tech_indices = [0, 1, 2]
        assert np.sum(w_cons[tech_indices]) <= 0.35 + 1e-6


class TestTargetVolatilityAndCashScaling:
    """Tests 12% target annual volatility scaling and bull market cash drag elimination."""

    def test_target_volatility_in_tranquil_bull(self):
        allocator = HierarchicalEntropyAllocator(target_volatility=0.12)
        # Covariance matrix with 10% annual volatility
        N = 3
        daily_var = (0.10 / math.sqrt(252)) ** 2
        cov = np.eye(N) * daily_var
        w = np.array([1/3, 1/3, 1/3])

        port_vol, gamma_vol, cash_ratio = allocator.scale_target_volatility(
            weights=w,
            covariance=cov,
            regime="BULL_LOW_VOL",
        )

        assert port_vol < 0.12
        # Bull market cash drag eliminator keeps cash ratio at 0.0
        assert cash_ratio == 0.0
        assert gamma_vol > 1.0

    def test_cash_buffer_scaling_in_crisis(self):
        allocator = HierarchicalEntropyAllocator(target_volatility=0.12)
        # High volatility portfolio: 30% annual volatility
        N = 3
        daily_var = (0.30 / math.sqrt(252)) ** 2
        cov = np.eye(N) * daily_var
        w = np.array([1/3, 1/3, 1/3])

        port_vol, gamma_vol, cash_ratio = allocator.scale_target_volatility(
            weights=w,
            covariance=cov,
            regime="CRISIS",
        )

        assert port_vol > 0.12
        assert cash_ratio > 0.0  # Capital de-risked into cash buffer
        assert cash_ratio == pytest.approx(1.0 - (0.12 / port_vol), rel=1e-3)


class TestLelandDynamicBufferBands:
    """Tests asymmetric Leland dynamic no-trade buffer bands."""

    def test_leland_bands_and_hold_action(self):
        allocator = HierarchicalEntropyAllocator(risk_aversion=1.0, rebalance_mode="boundary")
        target_weights = {"AAPL": 0.10, "MSFT": 0.10}
        current_weights = {"AAPL": 0.098, "MSFT": 0.102}  # Very close to target (within buffer)
        volatilities = {"AAPL": 0.25, "MSFT": 0.25}

        bands, actions = allocator.evaluate_leland_no_trade_bands(
            target_weights=target_weights,
            current_weights=current_weights,
            volatilities=volatilities,
        )

        assert "AAPL" in bands and "MSFT" in bands
        # Buffer half-width should be non-zero and bounded
        lower_aapl, tgt_aapl, upper_aapl = bands["AAPL"]
        assert lower_aapl < tgt_aapl < upper_aapl

        # Both positions inside buffer bands -> Action HOLD, turnover suppressed
        assert actions["AAPL"]["action"] == "HOLD"
        assert actions["AAPL"]["trade_weight"] == 0.0
        assert actions["MSFT"]["action"] == "HOLD"
        assert actions["MSFT"]["trade_weight"] == 0.0

    def test_immediate_bypass_for_new_entry_and_liquidation(self):
        allocator = HierarchicalEntropyAllocator()
        target_weights = {"NEW_BUY": 0.15, "LIQUIDATE": 0.0}
        current_weights = {"NEW_BUY": 0.0, "LIQUIDATE": 0.10}

        bands, actions = allocator.evaluate_leland_no_trade_bands(
            target_weights=target_weights,
            current_weights=current_weights,
        )

        # Immediate bypass on new entry
        assert actions["NEW_BUY"]["is_bypass"] is True
        assert actions["NEW_BUY"]["action"] == "BUY"
        assert actions["NEW_BUY"]["trade_weight"] == pytest.approx(0.15, abs=1e-6)

        # Immediate bypass on liquidation
        assert actions["LIQUIDATE"]["is_bypass"] is True
        assert actions["LIQUIDATE"]["action"] == "SELL"
        assert actions["LIQUIDATE"]["trade_weight"] == pytest.approx(-0.10, abs=1e-6)

    def test_asymmetric_band_scaling_for_winners_and_losers(self):
        allocator = HierarchicalEntropyAllocator()
        target_weights = {"WINNER": 0.10, "LOSER": 0.10}
        current_weights = {"WINNER": 0.10, "LOSER": 0.10}
        volatilities = {"WINNER": 0.20, "LOSER": 0.20}
        unrealized_returns = {"WINNER": +0.15, "LOSER": -0.15}

        bands, _ = allocator.evaluate_leland_no_trade_bands(
            target_weights=target_weights,
            current_weights=current_weights,
            volatilities=volatilities,
            unrealized_returns=unrealized_returns,
        )

        # Winner upper buffer expands: upper_band - target > target - lower_band
        w_lower, w_tgt, w_upper = bands["WINNER"]
        assert (w_upper - w_tgt) > (w_tgt - w_lower)

        # Loser lower buffer tightens: target - lower_band < upper_band - target
        l_lower, l_tgt, l_upper = bands["LOSER"]
        assert (l_tgt - l_lower) < (l_upper - l_tgt)


class TestUnifiedPortfolioAllocatorIntegration:
    """Tests Phase 110 integration with UnifiedPortfolioAllocator."""

    def test_phase110_gating_and_allocator_initialization(self):
        alloc_110 = UnifiedPortfolioAllocator(version=110)
        assert alloc_110.version == 110
        assert alloc_110.is_phase110 is True
        assert alloc_110.herc_entropy_allocator is not None

        alloc_103 = UnifiedPortfolioAllocator(version=103)
        assert alloc_103.version == 103
        assert alloc_103.is_phase110 is False
        assert alloc_103.is_phase103 is True

    def test_calculate_herc_entropy_weights_method(self):
        allocator = UnifiedPortfolioAllocator(version=110)
        N = 6
        cov = np.eye(N) * 0.04
        for i in range(N):
            for j in range(N):
                if i != j:
                    cov[i, j] = 0.01
        symbols = ["S1", "S2", "S3", "S4", "S5", "S6"]
        pred_rets = np.array([0.02, 0.04, 0.01, 0.03, 0.025, 0.015])

        w_herc = allocator.calculate_herc_entropy_weights(
            cov_matrix=cov,
            predicted_returns=pred_rets,
            symbols=symbols,
            regime="BULL_LOW_VOL",
        )

        assert len(w_herc) == N
        assert np.sum(w_herc) == pytest.approx(1.000000, abs=1e-6)
        assert np.all(w_herc >= 0.0)
        assert np.max(w_herc) <= allocator.max_single_weight + 1e-6

    def test_optimize_multi_model_blend_with_phase110(self):
        allocator = UnifiedPortfolioAllocator(version=110)
        N = 5
        rng = np.random.RandomState(42)
        returns_df = pd.DataFrame(
            rng.normal(0.0005, 0.015, size=(100, N)),
            columns=["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
        )
        cov = returns_df.cov().values
        pred_rets = np.array([0.02, 0.015, 0.03, -0.01, 0.025])
        symbols = list(returns_df.columns)

        w_blend = allocator.optimize_multi_model_blend(
            predicted_returns=pred_rets,
            returns_df=returns_df,
            cov_matrix=cov,
            symbols=symbols,
            regime="SIDEWAYS_LOW_VOL",
            version=110,
        )

        assert len(w_blend) == N
        assert np.sum(w_blend) == pytest.approx(1.000000, abs=1e-5)
        assert np.all(w_blend >= 0.0)


class TestEdgeCasesAndNumericalRobustness:
    """Tests edge cases: N=0, N=1, N=2, extreme returns, and singular covariance."""

    def test_empty_universe(self):
        allocator = HierarchicalEntropyAllocator()
        res = allocator.allocate(returns_data=np.zeros((0, 0)), symbols=[])
        assert len(res.weights) == 0
        assert len(res.weights_vector) == 0

    def test_single_asset_universe(self):
        allocator = HierarchicalEntropyAllocator()
        cov = np.array([[0.04]])
        res = allocator.allocate(returns_data=cov, symbols=["SINGLE"])
        assert res.weights == {"SINGLE": 1.0}
        assert res.weights_vector[0] == 1.0

    def test_two_assets_universe(self):
        allocator = HierarchicalEntropyAllocator()
        cov = np.array([[0.04, 0.01], [0.01, 0.09]])
        res = allocator.allocate(returns_data=cov, symbols=["A", "B"])
        assert len(res.weights) == 2
        assert sum(res.weights.values()) == pytest.approx(1.000000, abs=1e-6)
        # Asset A has lower variance, should get higher weight
        assert res.weights["A"] > res.weights["B"]

    def test_extreme_predicted_returns_and_nans(self):
        allocator = HierarchicalEntropyAllocator()
        N = 4
        cov = np.eye(N) * 0.04
        symbols = ["A", "B", "C", "D"]
        # Extreme return +500%, -99%, NaN, Inf
        pred_rets = np.array([5.00, -0.99, np.nan, np.inf])

        res = allocator.allocate(
            returns_data=cov,
            predicted_returns=pred_rets,
            symbols=symbols,
        )

        assert np.sum(res.weights_vector) == pytest.approx(1.000000, abs=1e-6)
        assert np.all(np.isfinite(res.weights_vector))
        assert np.all(res.weights_vector >= 0.0)

    def test_singular_collinear_covariance(self):
        allocator = HierarchicalEntropyAllocator()
        # 3 identical assets (perfect collinearity, rank 1)
        cov = np.ones((3, 3)) * 0.04
        symbols = ["C1", "C2", "C3"]

        res = allocator.allocate(returns_data=cov, symbols=symbols)
        assert np.sum(res.weights_vector) == pytest.approx(1.000000, abs=1e-6)
        assert np.all(res.weights_vector >= 0.0)
        assert np.all(np.isfinite(res.weights_vector))
        # Dendrogram bifurcates into 2 clusters: {C1, C2} and {C3}
        # C1 and C2 in the same cluster branch receive equal weights
        assert res.weights["C1"] == pytest.approx(res.weights["C2"], abs=1e-3)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
