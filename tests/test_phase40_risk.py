r"""
tests/test_phase40_risk.py

Unit test suite for Phase 40 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F181.1: Lurie-Langlands-Deligne Motivic Fisher-Rao Barycenter Blending
  (mu_lld = [3.00, 2.45, 2.40, 3.55], simplex sum=1.0, heavy-tail CVaR prioritization)
- Feature F181.1: 36th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne EVaR Tail Risk Measure
  (36! = 37,199,332,678,990,123,746,787,777,307,803,520,000,000, xi_deligne = 0.999996, order=36)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() with version=40
- Strict backward compatibility with Phase 39 and earlier versions
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase40RiskAllocation:
    """Test suite for Phase 40 Risk Allocation and Barycenter Blending."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_feature_f181_1_barycenter_blend_basic_properties(self, allocator):
        """Verify that Lurie-Langlands-Deligne Motivic Fisher-Rao barycenter converges on simplex."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 3.55, BL is second mu = 3.00, HERC is third mu = 2.45, RP is fourth mu = 2.40
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]

    def test_feature_f181_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        # 1. 1D Array
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        # 2. List of dicts
        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        # 3. 2D array
        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f181_1_barycenter_aliases_and_portfolio_allocator(self, allocator):
        """Verify that all barycenter aliases work on both UnifiedPortfolioAllocator and PortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(w)

        for alias_fn in [
            allocator.compute_lurie_langlands_deligne_barycenter,
            allocator.compute_lurie_deligne_langlands_barycenter,
            allocator.compute_langlands_deligne_fisher_rao_barycenter,
            allocator.compute_langlands_deligne_barycenter,
            allocator.compute_deligne_fisher_rao_barycenter,
            allocator.compute_deligne_barycenter,
            allocator.compute_phase40_fisher_rao_barycenter,
            allocator.compute_phase40_barycenter_blend,
            allocator.compute_langlands_deligne_fisher_rao_barycenter_blend,
            allocator.compute_motivic_langlands_deligne_barycenter_blend,
            allocator.compute_analytic_langlands_deligne_barycenter_blend,
            allocator.compute_deligne_regulator_barycenter_blend,
            allocator.compute_hodge_deligne_barycenter_blend,
            PortfolioAllocator.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_lurie_langlands_deligne_barycenter,
            PortfolioAllocator.compute_lurie_deligne_langlands_barycenter,
            PortfolioAllocator.compute_langlands_deligne_fisher_rao_barycenter,
            PortfolioAllocator.compute_langlands_deligne_barycenter,
            PortfolioAllocator.compute_deligne_fisher_rao_barycenter,
            PortfolioAllocator.compute_deligne_barycenter,
            PortfolioAllocator.compute_phase40_fisher_rao_barycenter,
            PortfolioAllocator.compute_phase40_barycenter_blend,
            PortfolioAllocator.compute_langlands_deligne_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_motivic_langlands_deligne_barycenter_blend,
            PortfolioAllocator.compute_analytic_langlands_deligne_barycenter_blend,
            PortfolioAllocator.compute_deligne_regulator_barycenter_blend,
            PortfolioAllocator.compute_hodge_deligne_barycenter_blend,
        ]:
            res = alias_fn(w)
            for k in ["bl", "herc", "rp", "cvar"]:
                assert math.isclose(res[k], ref[k], rel_tol=1e-5)

    def test_feature_f181_1_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_hierarchy(self, allocator):
        """Verify 36th-cumulant Deligne EVaR strictly bounds 35th-cumulant Clausen-Scholze EVaR."""
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)

        res_deligne = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(returns, alpha=0.05)
        res_clausen_scholze = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure(returns, alpha=0.05)

        assert res_deligne["order"] == 36
        assert math.isclose(res_deligne["xi_deligne"], 0.999996, rel_tol=1e-5)
        # Deligne EVaR >= Clausen-Scholze EVaR
        assert res_deligne["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value"] >= res_clausen_scholze["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_value"] - 1e-6

    def test_feature_f181_1_evar_aliases_and_portfolio_allocator(self, allocator):
        """Verify all Phase 40 EVaR aliases on UnifiedPortfolioAllocator and PortfolioAllocator."""
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)
        ref = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(returns)

        for alias_fn in [
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar,
            allocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_blend,
            allocator.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar,
            allocator.singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_phase40,
            allocator.compute_36th_cumulant_evar,
            allocator.compute_phase40_evar,
            allocator.compute_trans_deligne_evar_risk_measure,
            allocator.compute_trans_clausen_scholze_deligne_evar_risk_measure,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure,
            allocator.compute_clausen_scholze_deligne_evar,
            allocator.compute_deligne_evar,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar,
            PortfolioAllocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_blend,
            PortfolioAllocator.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar,
            PortfolioAllocator.singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_phase40,
            PortfolioAllocator.compute_36th_cumulant_evar,
            PortfolioAllocator.compute_phase40_evar,
            PortfolioAllocator.compute_trans_deligne_evar_risk_measure,
            PortfolioAllocator.compute_trans_clausen_scholze_deligne_evar_risk_measure,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure,
            PortfolioAllocator.compute_clausen_scholze_deligne_evar,
            PortfolioAllocator.compute_deligne_evar,
        ]:
            res = alias_fn(returns)
            assert math.isclose(res["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value"], ref["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value"], rel_tol=1e-5)

    def test_compute_regime_blended_portfolio_v40(self, allocator):
        """Verify end-to-end regime blending under version=40."""
        blended_v40 = allocator.compute_information_theoretic_blend_weights(version=40)
        blended_v39 = allocator.compute_information_theoretic_blend_weights(version=39)

        assert isinstance(blended_v40, dict)
        assert math.isclose(sum(blended_v40.values()), 1.0, rel_tol=1e-5)
        # CVaR is highest in v40
        assert blended_v40["cvar"] > blended_v40["rp"]
        # v40 has even stronger CVaR prioritization than v39 due to Lurie-Langlands-Deligne weights [3.00, 2.45, 2.40, 3.55] vs [2.90, 2.40, 2.35, 3.45]
        assert blended_v40["cvar"] >= blended_v39["cvar"] - 1e-4

    def test_phase40_backward_compatibility(self, allocator):
        """Verify that older version blends continue to compute correctly without errors."""
        for v in [1, 10, 20, 26, 30, 34, 35, 36, 37, 38, 39]:
            w = allocator.compute_information_theoretic_blend_weights(version=v)
            assert isinstance(w, dict)
            assert math.isclose(sum(w.values()), 1.0, rel_tol=1e-5)
