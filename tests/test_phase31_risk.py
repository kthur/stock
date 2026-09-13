r"""
tests/test_phase31_risk.py

Unit test suite for Phase 31 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F145.1: Lurie Kato-Fontaine Motivic Fisher-Rao Barycenter Blending
  (mu_kato = [2.50, 2.00, 1.95, 3.05], simplex sum=1.0, heavy-tail CVaR prioritization)
- Feature F145.1: 27th-Cumulant Expansion Trans-Singular-Eternal EVaR Tail Risk Measure
  (27! = 10,888,869,450,418,352,160,768,000,000, xi_singular_eternal = 0.998, order=27)
- UnifiedPortfolioAllocator compute_regime_blended_portfolio() with version=31
- Strict backward compatibility with Phase 30 and earlier versions
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase31RiskAllocation:
    """Test suite for Phase 31 Risk Allocation and Barycenter Blending."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_feature_f145_1_barycenter_blend_basic_properties(self, allocator):
        """Verify that Lurie Kato-Fontaine Motivic Fisher-Rao barycenter converges on simplex."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_kato_fontaine_motivic_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 3.05, BL is second mu = 2.50
        assert blended["cvar"] > blended["herc"]
        assert blended["cvar"] > blended["rp"]
        assert blended["bl"] > blended["rp"]

    def test_feature_f145_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        # 1. 1D Array
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_kato_fontaine_motivic_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        # 2. List of dicts
        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_kato_fontaine_motivic_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        # 3. 2D array
        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_kato_fontaine_motivic_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f145_1_barycenter_aliases_and_portfolio_allocator(self, allocator):
        """Verify that all barycenter aliases work on both UnifiedPortfolioAllocator and PortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_kato_fontaine_motivic_fisher_rao_barycenter_blend(w)

        for alias_fn in [
            allocator.compute_lurie_kato_fontaine_barycenter,
            allocator.compute_kato_fontaine_fisher_rao_barycenter,
            allocator.compute_kato_fontaine_barycenter,
            allocator.compute_lurie_kato_barycenter,
            allocator.compute_lurie_fontaine_barycenter,
            allocator.compute_kato_fisher_rao_barycenter,
            allocator.compute_fontaine_fisher_rao_barycenter,
            allocator.compute_phase31_fisher_rao_barycenter,
            PortfolioAllocator.compute_lurie_kato_fontaine_motivic_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_lurie_kato_fontaine_barycenter,
            PortfolioAllocator.compute_kato_fontaine_fisher_rao_barycenter,
            PortfolioAllocator.compute_kato_barycenter,
            PortfolioAllocator.compute_fontaine_barycenter,
            PortfolioAllocator.compute_phase31_fisher_rao_barycenter,
        ]:
            res = alias_fn(w)
            for k in ["bl", "herc", "rp", "cvar"]:
                assert math.isclose(res[k], ref[k], rel_tol=1e-5)

    def test_feature_f145_1_trans_singular_eternal_evar_hierarchy(self, allocator):
        """Verify 27th-cumulant Trans-Singular-Eternal EVaR strictly bounds lower-order EVaRs."""
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)  # slightly negative mean with variance

        res_ete = allocator.compute_trans_singular_eternal_evar_risk_measure(returns, alpha=0.05)
        res_inf = allocator.compute_trans_singular_infinity_evar_risk_measure(returns, alpha=0.05)

        assert res_ete["order"] == 27
        assert math.isclose(res_ete["xi_singular_eternal"], 0.998, rel_tol=1e-5)
        # Trans-Singular-Eternal EVaR >= Trans-Singular-Infinity EVaR
        assert res_ete["trans_singular_eternal_evar_value"] >= res_inf["trans_singular_infinity_evar_value"] - 1e-6

    def test_feature_f145_1_evar_aliases_and_portfolio_allocator(self, allocator):
        """Verify all Phase 31 EVaR aliases on UnifiedPortfolioAllocator and PortfolioAllocator."""
        returns = np.array([-0.05, -0.02, 0.01, 0.03, -0.01])
        ref = allocator.compute_trans_singular_eternal_evar_risk_measure(returns)

        for alias_fn in [
            allocator.compute_trans_singular_eternal_evar,
            allocator.trans_singular_eternal_evar_risk_measure,
            allocator.compute_trans_singular_eternal_evar_blend,
            allocator.compute_singular_eternal_evar,
            allocator.singular_eternal_evar_risk_measure,
            allocator.compute_trans_singular_eternal_evar_phase31,
            allocator.compute_27th_cumulant_evar,
            allocator.compute_phase31_evar,
            PortfolioAllocator.compute_trans_singular_eternal_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_evar,
            PortfolioAllocator.trans_singular_eternal_evar_risk_measure,
            PortfolioAllocator.compute_singular_eternal_evar,
            PortfolioAllocator.compute_phase31_evar,
        ]:
            res = alias_fn(returns)
            assert math.isclose(res["trans_singular_eternal_evar_value"], ref["trans_singular_eternal_evar_value"], rel_tol=1e-5)

    def test_compute_regime_blended_portfolio_v31(self, allocator):
        """Verify end-to-end regime blending under version=31."""
        blended_v31 = allocator.compute_information_theoretic_blend_weights(version=31)
        blended_v30 = allocator.compute_information_theoretic_blend_weights(version=30)

        assert isinstance(blended_v31, dict)
        assert set(blended_v31.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended_v31.values()), 1.0, rel_tol=1e-5)

        # In v31, CVaR weight is further fortified (mu=3.05, delta_cvar=+8.50*eps_w)
        assert blended_v31["cvar"] > blended_v30["cvar"]
        assert blended_v31["cvar"] > 0.001

    def test_strict_backward_compatibility_v30_v29(self, allocator):
        """Verify backward compatibility for regime blending with version=30 and version=29."""
        blended_v30 = allocator.compute_information_theoretic_blend_weights(version=30)
        blended_v29 = allocator.compute_information_theoretic_blend_weights(version=29)

        assert math.isclose(sum(blended_v30.values()), 1.0, rel_tol=1e-5)
        assert math.isclose(sum(blended_v29.values()), 1.0, rel_tol=1e-5)
        assert blended_v30["cvar"] > blended_v29["cvar"] - 1e-6
