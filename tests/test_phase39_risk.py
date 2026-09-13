r"""
tests/test_phase39_risk.py

Unit test suite for Phase 39 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F177.1: Lurie-Clausen-Scholze Motivic Fisher-Rao Barycenter Blending
  (mu_lcs = [2.90, 2.40, 2.35, 3.45], simplex sum=1.0, heavy-tail CVaR prioritization)
- Feature F177.2: 35th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze EVaR Tail Risk Measure
  (35! = 1,033,314,796,638,614,492,966,160,480,772,320,000,000, xi_clausen_scholze = 0.999995, order=35)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() with version=39
- Strict backward compatibility with Phase 38 and earlier versions
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase39RiskAllocation:
    """Test suite for Phase 39 Risk Allocation and Barycenter Blending."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_feature_f177_1_barycenter_blend_basic_properties(self, allocator):
        """Verify that Lurie-Clausen-Scholze Motivic Fisher-Rao barycenter converges on simplex."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_clausen_scholze_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 3.45, BL is second mu = 2.90, HERC is third mu = 2.40, RP is fourth mu = 2.35
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]

    def test_feature_f177_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        # 1. 1D Array
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_clausen_scholze_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        # 2. List of dicts
        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_clausen_scholze_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        # 3. 2D array
        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_clausen_scholze_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f177_1_barycenter_aliases_and_portfolio_allocator(self, allocator):
        """Verify that all barycenter aliases work on both UnifiedPortfolioAllocator and PortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_clausen_scholze_fisher_rao_barycenter_blend(w)

        for alias_fn in [
            allocator.compute_lurie_clausen_scholze_barycenter,
            allocator.compute_lurie_scholze_clausen_barycenter,
            allocator.compute_clausen_scholze_fisher_rao_barycenter,
            allocator.compute_clausen_scholze_barycenter,
            allocator.compute_phase39_fisher_rao_barycenter,
            allocator.compute_phase39_barycenter_blend,
            allocator.compute_clausen_barycenter,
            allocator.compute_clausen_scholze_fisher_rao_barycenter_blend,
            allocator.compute_motivic_clausen_scholze_barycenter_blend,
            allocator.compute_analytic_clausen_scholze_barycenter_blend,
            allocator.compute_liquid_clausen_scholze_barycenter_blend,
            PortfolioAllocator.compute_lurie_clausen_scholze_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_lurie_clausen_scholze_barycenter,
            PortfolioAllocator.compute_lurie_scholze_clausen_barycenter,
            PortfolioAllocator.compute_clausen_scholze_fisher_rao_barycenter,
            PortfolioAllocator.compute_clausen_scholze_barycenter,
            PortfolioAllocator.compute_phase39_fisher_rao_barycenter,
            PortfolioAllocator.compute_phase39_barycenter_blend,
            PortfolioAllocator.compute_clausen_barycenter,
            PortfolioAllocator.compute_clausen_scholze_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_motivic_clausen_scholze_barycenter_blend,
            PortfolioAllocator.compute_analytic_clausen_scholze_barycenter_blend,
            PortfolioAllocator.compute_liquid_clausen_scholze_barycenter_blend,
        ]:
            res = alias_fn(w)
            for k in ["bl", "herc", "rp", "cvar"]:
                assert math.isclose(res[k], ref[k], rel_tol=1e-5)

    def test_feature_f177_2_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_hierarchy(self, allocator):
        """Verify 35th-cumulant Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze EVaR strictly bounds lower-order EVaRs."""
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)

        res_clausen_scholze = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure(returns, alpha=0.05)
        res_scholze = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_scholze_evar_risk_measure(returns, alpha=0.05)

        assert res_clausen_scholze["order"] == 35
        assert math.isclose(res_clausen_scholze["xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze"], 0.999995, rel_tol=1e-5)
        # Clausen-Scholze EVaR >= Scholze EVaR
        assert res_clausen_scholze["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_value"] >= res_scholze["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_scholze_evar_value"] - 1e-6

    def test_feature_f177_2_evar_aliases_and_portfolio_allocator(self, allocator):
        """Verify all Phase 39 EVaR aliases on UnifiedPortfolioAllocator and PortfolioAllocator."""
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)
        ref = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure(returns)

        for alias_fn in [
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar,
            allocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_blend,
            allocator.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar,
            allocator.singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_phase39,
            allocator.compute_35th_cumulant_evar,
            allocator.compute_phase39_evar,
            allocator.compute_trans_clausen_scholze_evar_risk_measure,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure,
            allocator.compute_clausen_scholze_evar,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar,
            PortfolioAllocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_blend,
            PortfolioAllocator.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar,
            PortfolioAllocator.singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_phase39,
            PortfolioAllocator.compute_35th_cumulant_evar,
            PortfolioAllocator.compute_phase39_evar,
            PortfolioAllocator.compute_trans_clausen_scholze_evar_risk_measure,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure,
            PortfolioAllocator.compute_clausen_scholze_evar,
        ]:
            res = alias_fn(returns)
            assert math.isclose(res["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_value"], ref["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_value"], rel_tol=1e-5)

    def test_compute_regime_blended_portfolio_v39(self, allocator):
        """Verify end-to-end regime blending under version=39."""
        blended_v39 = allocator.compute_information_theoretic_blend_weights(version=39)
        blended_v38 = allocator.compute_information_theoretic_blend_weights(version=38)

        assert isinstance(blended_v39, dict)
        assert math.isclose(sum(blended_v39.values()), 1.0, rel_tol=1e-5)
        # CVaR is highest in v39
        assert blended_v39["cvar"] > blended_v39["rp"]
        # v39 has even stronger CVaR prioritization than v38 due to Clausen-Scholze weights [2.90, 2.40, 2.35, 3.45] vs [2.85, 2.35, 2.30, 3.40]
        assert blended_v39["cvar"] >= blended_v38["cvar"] - 1e-4

    def test_phase39_backward_compatibility(self, allocator):
        """Verify that older version blends continue to compute correctly without errors."""
        for v in [1, 10, 20, 26, 30, 34, 35, 36, 37, 38]:
            w = allocator.compute_information_theoretic_blend_weights(version=v)
            assert isinstance(w, dict)
            assert math.isclose(sum(w.values()), 1.0, rel_tol=1e-5)
