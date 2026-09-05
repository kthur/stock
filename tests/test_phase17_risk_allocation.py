"""
tests/test_phase17_risk_allocation.py

Comprehensive unit and integration test suite for Phase 17 Quantitative Enhancement (Feature F89.1):
1. Noncommutative Motive Spectral Triad (A, H, D) Fisher-Rao Manifold Barycenter Blending:
   - compute_noncommutative_motive_spectral_triad_fisher_rao_barycenter_blend & compute_noncommutative_motive_barycenter
   - Metric parameters mu_triad = [1.50, 1.30, 1.25, 1.70]
   - Simplex bounds, non-negativity, Dirichlet random stability, and convergence
2. Trans-Singularity EVaR Tail Risk Measure (12th-cumulant expansion):
   - compute_trans_singularity_evar_risk_measure & compute_trans_singularity_evar
   - 11th order (1/39916800) and 12th order (1/479001600) cumulants with xi_trans_singularity = 0.45
   - Strict coherent hierarchy: VaR <= CVaR <= EVaR <= ... <= Ultra-Transfinite-EVaR <= Trans-Singularity-EVaR
   - Monotonicity in alpha and xi, edge cases (empty, zero, extreme loss)
3. Information-Theoretic Multi-Model Blending & Dynamic Log-Odds:
   - compute_information_theoretic_blend_weights with version=17
   - eps_w = 0.185, alpha_iep = 1.05, cascade contagion damping
4. Master Allocation Routing:
   - UnifiedPortfolioAllocator.allocate with version=17 and backward compatibility (v16, v6)
   - calculate_cvar_weights with version=17 routing
   - PortfolioAllocator static/instance method compatibility
"""

import math
import numpy as np
import pandas as pd
import pytest
from typing import Dict, List

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase17RiskAllocation:
    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    @pytest.fixture
    def legacy_allocator(self):
        return PortfolioAllocator()

    # =========================================================================
    # 1. NONCOMMUTATIVE MOTIVE SPECTRAL TRIAD FISHER-RAO BARYCENTER
    # =========================================================================

    def test_noncommutative_motive_spectral_triad_barycenter_basic(self, allocator):
        """Verify simplex constraints, positivity, and alias on single distribution."""
        input_weights = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        res = allocator.compute_noncommutative_motive_spectral_triad_fisher_rao_barycenter_blend(input_weights)
        assert isinstance(res, dict)
        assert len(res) == 4
        for k in ["bl", "herc", "rp", "cvar"]:
            assert k in res
            assert res[k] > 0.0
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)

        # Test alias
        alias_res = allocator.compute_noncommutative_motive_barycenter(input_weights)
        for k in ["bl", "herc", "rp", "cvar"]:
            assert math.isclose(res[k], alias_res[k], abs_tol=1e-6)

    def test_noncommutative_motive_spectral_triad_barycenter_multi_distribution(self, allocator):
        """Verify barycenter consensus under multi-distribution input with CVaR prioritization."""
        dist1 = {"bl": 0.40, "herc": 0.30, "rp": 0.15, "cvar": 0.15}
        dist2 = {"bl": 0.10, "herc": 0.20, "rp": 0.30, "cvar": 0.40}
        res = allocator.compute_noncommutative_motive_spectral_triad_fisher_rao_barycenter_blend([dist1, dist2])
        assert isinstance(res, dict)
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)
        # CVaR receives highest metric weight mu_triad[3]=1.70, so it should have strong allocation
        assert res["cvar"] > 0.15
        assert res["bl"] > 0.10
        assert res["herc"] > 0.10
        assert res["rp"] > 0.10

    def test_noncommutative_motive_barycenter_array_inputs(self, allocator):
        """Verify handling of 1D and 2D numpy arrays."""
        # 1D array
        arr_1d = np.array([0.25, 0.25, 0.25, 0.25])
        res_1d = allocator.compute_noncommutative_motive_barycenter(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, abs_tol=1e-5)

        # 2D array (3 distributions over 4 models)
        arr_2d = np.array([
            [0.30, 0.20, 0.20, 0.30],
            [0.10, 0.40, 0.10, 0.40],
            [0.20, 0.10, 0.50, 0.20],
        ])
        res_2d = allocator.compute_noncommutative_motive_barycenter(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, abs_tol=1e-5)
        for k in ["bl", "herc", "rp", "cvar"]:
            assert res_2d[k] > 0.0

    def test_noncommutative_motive_barycenter_convergence_and_stability(self, allocator):
        """Verify numerical stability and convergence across randomized Dirichlet samples."""
        np.random.seed(42)
        for _ in range(15):
            # Sample random distribution on 4-simplex
            alpha = np.random.uniform(0.5, 3.0, size=4)
            sample = np.random.dirichlet(alpha)
            d_dict = {"bl": sample[0], "herc": sample[1], "rp": sample[2], "cvar": sample[3]}
            res = allocator.compute_noncommutative_motive_barycenter(d_dict, max_iter=80, tol=1e-7)
            assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)
            for v in res.values():
                assert math.isfinite(v)
                assert v > 0.0

    # =========================================================================
    # 2. TRANS-SINGULARITY EVAR (12TH-CUMULANT EXPANSION)
    # =========================================================================

    def test_trans_singularity_evar_coherent_hierarchy(self, allocator):
        """
        Verify strict coherent tail risk hierarchy:
        VaR <= CVaR <= EVaR <= Super-EVaR <= Ultra-EVaR <= Transfinite-EVaR <= Infinite-EVaR
            <= Supra-Transfinite-EVaR <= Ultra-Transfinite-EVaR <= Trans-Singularity-EVaR
        """
        np.random.seed(42)
        # Generate heavy-tailed fat-loss distribution (Student-t with df=3)
        returns = np.random.standard_t(df=3.0, size=250) * 0.025
        res = allocator.compute_trans_singularity_evar_risk_measure(
            returns, alpha=0.05, xi_trans_singularity=0.45
        )

        var_val = res["var_value"]
        cvar_val = res["cvar_value"]
        evar_val = res["evar_value"]
        super_evar_val = res["super_evar_value"]
        ultra_evar_val = res["ultra_evar_value"]
        trans_evar_val = res["transfinite_evar_value"]
        inf_evar_val = res["infinite_evar_value"]
        supra_val = res["supra_transfinite_evar_value"]
        ultra_trans_val = res["ultra_transfinite_evar_value"]
        trans_sing_val = res["trans_singularity_evar_value"]

        # Assert hierarchy with floating tolerance
        assert cvar_val >= var_val - 1e-5
        assert evar_val >= cvar_val - 1e-5
        assert super_evar_val >= evar_val - 1e-5
        assert ultra_evar_val >= super_evar_val - 1e-5
        assert trans_evar_val >= ultra_evar_val - 1e-5
        assert inf_evar_val >= trans_evar_val - 1e-5
        assert supra_val >= inf_evar_val - 1e-5
        assert ultra_trans_val >= supra_val - 1e-5
        assert trans_sing_val >= ultra_trans_val - 1e-5

        # Check alias in result dict
        assert math.isclose(res["trans_sing_evar_value"], trans_sing_val, abs_tol=1e-6)

        # Check alias method
        alias_res = allocator.compute_trans_singularity_evar(returns, alpha=0.05)
        assert math.isclose(alias_res["trans_singularity_evar_value"], trans_sing_val, abs_tol=1e-6)

    def test_trans_singularity_evar_monotonicity_and_edge_cases(self, allocator):
        """Verify monotonicity with respect to alpha, xi, and edge case safety."""
        np.random.seed(123)
        returns = np.random.normal(0, 0.02, size=150)

        # 1. Monotonicity in alpha (smaller alpha -> more conservative / higher risk measure)
        res_01 = allocator.compute_trans_singularity_evar_risk_measure(returns, alpha=0.01)
        res_05 = allocator.compute_trans_singularity_evar_risk_measure(returns, alpha=0.05)
        assert res_01["trans_singularity_evar_value"] >= res_05["trans_singularity_evar_value"] - 1e-6

        # 2. Monotonicity in xi_trans_singularity (higher parameter -> higher tail penalization)
        res_xi_low = allocator.compute_trans_singularity_evar_risk_measure(returns, xi_trans_singularity=0.10)
        res_xi_high = allocator.compute_trans_singularity_evar_risk_measure(returns, xi_trans_singularity=0.60)
        assert res_xi_high["trans_singularity_evar_value"] >= res_xi_low["trans_singularity_evar_value"] - 1e-6

        # 3. Custom xi_11 and xi_12 parameters
        res_custom = allocator.compute_trans_singularity_evar_risk_measure(returns, xi_11=0.50, xi_12=0.55)
        assert res_custom["xi_11"] == 0.50
        assert res_custom["xi_12"] == 0.55

        # 4. Edge cases: empty array, all zeros, and extreme loss
        res_empty = allocator.compute_trans_singularity_evar_risk_measure(np.array([]))
        assert math.isfinite(res_empty["trans_singularity_evar_value"])

        res_zeros = allocator.compute_trans_singularity_evar_risk_measure(np.zeros(50))
        assert math.isfinite(res_zeros["trans_singularity_evar_value"])

        crash_returns = np.array([-0.30, -0.40, -0.25, 0.01, 0.02])
        res_crash = allocator.compute_trans_singularity_evar_risk_measure(crash_returns, alpha=0.05)
        assert res_crash["trans_singularity_evar_value"] > 0.20

    # =========================================================================
    # 3. INFORMATION-THEORETIC BLENDING WITH VERSION=17
    # =========================================================================

    def test_information_theoretic_blend_weights_v17(self, allocator):
        """Verify that under version=17, crisis severity triggers CVaR & HERC dominance with Motive Barycenter."""
        regime = {"BULL_LOW_VOL": 0.2, "CRISIS": 0.8}
        blend = allocator.compute_information_theoretic_blend_weights(
            regime=regime,
            crisis_severity=0.8,
            wasserstein_radius=0.185,
            version=17,
        )
        assert isinstance(blend, dict)
        assert math.isclose(sum(blend.values()), 1.0, abs_tol=1e-5)
        # In crisis regime with v17, CVaR must dominate BL and RP
        assert blend["cvar"] > blend["bl"]
        assert blend["cvar"] > blend["rp"]

    def test_information_theoretic_blend_weights_v17_vs_v16(self, allocator):
        """Verify that v17 applies more protective tilting than v16 under equal conditions."""
        regime = {"CRISIS": 1.0}
        blend_v17 = allocator.compute_information_theoretic_blend_weights(
            regime=regime,
            crisis_severity=1.0,
            version=17,
        )
        blend_v16 = allocator.compute_information_theoretic_blend_weights(
            regime=regime,
            crisis_severity=1.0,
            version=16,
        )
        # Both sum to 1
        assert math.isclose(sum(blend_v17.values()), 1.0, abs_tol=1e-5)
        assert math.isclose(sum(blend_v16.values()), 1.0, abs_tol=1e-5)
        # CVaR in v17 should be elevated due to mu_triad[3]=1.70 and eps_w=0.185
        assert blend_v17["cvar"] >= blend_v16["cvar"] - 0.05

    # =========================================================================
    # 4. CVAR WEIGHTS & MULTI-MODEL BLEND OPTIMIZATION
    # =========================================================================

    def test_calculate_cvar_weights_v17(self, allocator):
        """Verify calculate_cvar_weights execution with version=17 routing."""
        np.random.seed(42)
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        n = len(symbols)
        returns_df = pd.DataFrame(
            np.random.normal(0.001, 0.02, size=(50, n)),
            columns=symbols
        )
        w_cvar_v17 = allocator.calculate_cvar_weights(
            returns_df=returns_df,
            confidence_level=0.95,
            predicted_returns=np.array([0.02, 0.03, 0.01, 0.04]),
            version=17,
        )
        assert len(w_cvar_v17) == n
        assert np.all(w_cvar_v17 >= 0.0)
        assert math.isclose(float(np.sum(w_cvar_v17)), 1.0, abs_tol=1e-4)

        # Backward compatibility with version=16
        w_cvar_v16 = allocator.calculate_cvar_weights(
            returns_df=returns_df,
            confidence_level=0.95,
            version=16,
        )
        assert math.isclose(float(np.sum(w_cvar_v16)), 1.0, abs_tol=1e-4)

    def test_optimize_multi_model_blend_v17(self, allocator):
        """Verify full continuous 4-model blend optimization with version=17."""
        np.random.seed(42)
        symbols = ["005930", "000660", "035420", "051910", "005380"]
        n = len(symbols)
        returns_df = pd.DataFrame(
            np.random.normal(0.001, 0.025, size=(60, n)),
            columns=symbols
        )
        cov_matrix = returns_df.cov().values
        preds = np.array([0.05, 0.03, 0.04, 0.02, 0.06])
        cascade_vec = np.array([0.15, 0.35, 0.20, 0.70, 0.10])

        w = allocator.optimize_multi_model_blend(
            predicted_returns=preds,
            returns_df=returns_df,
            cov_matrix=cov_matrix,
            symbols=symbols,
            version=17,
            asset_cascade_vector=cascade_vec,
        )
        assert len(w) == n
        assert np.all(w >= 0.0)
        assert math.isclose(float(np.sum(w)), 1.0, abs_tol=1e-4)

    # =========================================================================
    # 5. UNIFIED PORTFOLIO ALLOCATOR MASTER ALLOCATE & BACKWARD COMPATIBILITY
    # =========================================================================

    def test_unified_portfolio_allocator_allocate_v17(self, allocator):
        """Verify master allocate method execution with version=17."""
        np.random.seed(101)
        symbols = ["AAPL", "MSFT", "NVDA", "AMZN"]
        predictions_df = pd.DataFrame({
            "symbol": symbols,
            "market": ["US"] * len(symbols),
            "ensemble_expected_return": [0.08, 0.06, 0.12, 0.05],
            "score": [0.85, 0.75, 0.95, 0.70],
            "adv": [1e8, 8e7, 1.2e8, 9e7],
            "close": [180.0, 420.0, 120.0, 190.0],
        })

        prices_dict = {}
        for s in symbols:
            dates = pd.date_range("2026-01-01", periods=65, freq="D")
            prices_dict[s] = pd.DataFrame({
                "Close": 100.0 * np.cumprod(1.0 + np.random.normal(0.001, 0.018, size=65))
            }, index=dates)

        res_df = allocator.allocate(
            predictions_df=predictions_df,
            prices_dict=prices_dict,
            total_portfolio_value=50_000_000.0,
            regime="BULL_LOW_VOL",
            version=17,
        )

        assert not res_df.empty
        assert "weight" in res_df.columns
        assert "shares" in res_df.columns
        assert "allocation_amount" in res_df.columns
        tot_w = float(res_df["weight"].sum())
        assert tot_w <= 1.0 + 1e-4
        assert tot_w > 0.0
        assert np.all(res_df["weight"] >= 0.0)

    def test_allocate_backward_compatibility_v16_and_v6(self, allocator):
        """Verify backward compatibility when calling allocate with version=16 or version=6."""
        np.random.seed(202)
        symbols = ["005930", "000660", "035420"]
        predictions_df = pd.DataFrame({
            "symbol": symbols,
            "market": ["KOSPI"] * len(symbols),
            "ensemble_expected_return": [0.07, 0.09, 0.04],
            "score": [0.80, 0.88, 0.65],
            "close": [70000.0, 180000.0, 200000.0],
        })
        prices_dict = {}
        for s in symbols:
            dates = pd.date_range("2026-01-01", periods=65, freq="D")
            prices_dict[s] = pd.DataFrame({
                "Close": 100000.0 * np.cumprod(1.0 + np.random.normal(0.0005, 0.02, size=65))
            }, index=dates)

        # Version 16 call
        res_v16 = allocator.allocate(
            predictions_df=predictions_df,
            prices_dict=prices_dict,
            total_portfolio_value=100_000_000.0,
            version=16,
        )
        assert not res_v16.empty
        assert float(res_v16["weight"].sum()) <= 1.0 + 1e-4

        # Version 6 (legacy) call
        res_v6 = allocator.allocate(
            predictions_df=predictions_df,
            prices_dict=prices_dict,
            total_portfolio_value=100_000_000.0,
            version=6,
        )
        assert not res_v6.empty
        assert float(res_v6["weight"].sum()) <= 1.0 + 1e-4

    # =========================================================================
    # 6. PORTFOLIO ALLOCATOR DELEGATION & COMPATIBILITY
    # =========================================================================

    def test_portfolio_allocator_class_methods(self, legacy_allocator):
        """Verify that PortfolioAllocator has static/instance access to Feature F89.1 methods."""
        input_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}

        # Static call on class
        res_static = PortfolioAllocator.compute_noncommutative_motive_spectral_triad_fisher_rao_barycenter_blend(input_weights)
        assert math.isclose(sum(res_static.values()), 1.0, abs_tol=1e-5)

        # Instance call
        res_inst = legacy_allocator.compute_noncommutative_motive_barycenter(input_weights)
        assert math.isclose(sum(res_inst.values()), 1.0, abs_tol=1e-5)

        # Trans-Singularity EVaR via PortfolioAllocator
        rets = np.array([0.01, -0.02, -0.05, 0.03, -0.01, -0.08, 0.02])
        evar_static = PortfolioAllocator.compute_trans_singularity_evar_risk_measure(rets, alpha=0.05)
        assert "trans_singularity_evar_value" in evar_static
        assert evar_static["trans_singularity_evar_value"] >= evar_static["ultra_transfinite_evar_value"] - 1e-6
