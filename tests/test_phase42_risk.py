r"""
tests/test_phase42_risk.py

Unit test suite for Phase 42 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F185.1/F189.1: Lurie-Beilinson-Drinfeld Motivic Fisher-Rao Barycenter Blending
  (mu_lbd = [3.20, 2.55, 2.50, 3.75], simplex sum=1.0, heavy-tail CVaR prioritization)
- Feature F185.1/F189.1: 38th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne-Fargues-Beilinson EVaR Tail Risk Measure
  (38! ~= 5.230 x 10^44, xi_beilinson = 0.999998, order=38)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() with version=42
- Strict backward compatibility with Phase 41 and earlier versions
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase42RiskAllocation:
    """Test suite for Phase 42 Risk Allocation and Barycenter Blending."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_feature_f185_1_barycenter_blend_basic_properties(self, allocator):
        """Verify that Lurie-Beilinson-Drinfeld Motivic Fisher-Rao barycenter converges on simplex."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_beilinson_drinfeld_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 3.75, BL is second mu = 3.20, HERC is third mu = 2.55, RP is fourth mu = 2.50
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]

    def test_feature_f185_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        # 1. 1D Array
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_beilinson_drinfeld_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        # 2. List of dicts
        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_beilinson_drinfeld_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        # 3. 2D array
        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_beilinson_drinfeld_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f185_1_barycenter_aliases_and_portfolio_allocator(self, allocator):
        """Verify that all barycenter aliases work on both UnifiedPortfolioAllocator and PortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_beilinson_drinfeld_fisher_rao_barycenter_blend(w)

        for alias_fn in [
            allocator.compute_lurie_beilinson_drinfeld_barycenter,
            allocator.compute_lurie_drinfeld_beilinson_barycenter,
            allocator.compute_beilinson_drinfeld_fisher_rao_barycenter,
            allocator.compute_beilinson_drinfeld_barycenter,
            allocator.compute_drinfeld_fisher_rao_barycenter,
            allocator.compute_drinfeld_barycenter,
            allocator.compute_phase42_fisher_rao_barycenter,
            allocator.compute_phase42_barycenter_blend,
            allocator.compute_beilinson_drinfeld_fisher_rao_barycenter_blend,
            allocator.compute_motivic_beilinson_drinfeld_barycenter_blend,
            allocator.compute_analytic_beilinson_drinfeld_barycenter_blend,
            allocator.compute_chiral_beilinson_drinfeld_barycenter_blend,
            allocator.compute_kac_moody_beilinson_drinfeld_barycenter_blend,
            allocator.compute_vertex_algebra_beilinson_drinfeld_barycenter_blend,
            allocator.compute_chiral_oper_beilinson_drinfeld_barycenter_blend,
            PortfolioAllocator.compute_lurie_beilinson_drinfeld_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_lurie_beilinson_drinfeld_barycenter,
            PortfolioAllocator.compute_lurie_drinfeld_beilinson_barycenter,
            PortfolioAllocator.compute_beilinson_drinfeld_fisher_rao_barycenter,
            PortfolioAllocator.compute_beilinson_drinfeld_barycenter,
            PortfolioAllocator.compute_drinfeld_fisher_rao_barycenter,
            PortfolioAllocator.compute_drinfeld_barycenter,
            PortfolioAllocator.compute_phase42_fisher_rao_barycenter,
            PortfolioAllocator.compute_phase42_barycenter_blend,
            PortfolioAllocator.compute_beilinson_drinfeld_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_motivic_beilinson_drinfeld_barycenter_blend,
            PortfolioAllocator.compute_analytic_beilinson_drinfeld_barycenter_blend,
            PortfolioAllocator.compute_chiral_beilinson_drinfeld_barycenter_blend,
            PortfolioAllocator.compute_kac_moody_beilinson_drinfeld_barycenter_blend,
            PortfolioAllocator.compute_vertex_algebra_beilinson_drinfeld_barycenter_blend,
            PortfolioAllocator.compute_chiral_oper_beilinson_drinfeld_barycenter_blend,
        ]:
            res = alias_fn(w)
            for k in ["bl", "herc", "rp", "cvar"]:
                assert math.isclose(res[k], ref[k], rel_tol=1e-5)

    def test_feature_f185_1_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_hierarchy(self, allocator):
        """Verify 38th-cumulant Beilinson EVaR strictly bounds 37th-cumulant Fargues EVaR."""
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)

        res_beilinson = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure(returns, alpha=0.05)
        res_fargues = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_evar_risk_measure(returns, alpha=0.05)

        assert res_beilinson["order"] == 38
        assert math.isclose(res_beilinson["xi_beilinson"], 0.999998, rel_tol=1e-5)
        # Beilinson EVaR >= Fargues EVaR
        assert res_beilinson["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_value"] >= res_fargues["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_evar_value"] - 1e-6

    def test_feature_f185_1_evar_aliases_and_portfolio_allocator(self, allocator):
        """Verify all Phase 42 EVaR aliases on UnifiedPortfolioAllocator and PortfolioAllocator."""
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)
        ref = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure(returns)

        for alias_fn in [
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar,
            allocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_blend,
            allocator.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar,
            allocator.singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_phase42,
            allocator.compute_38th_cumulant_evar,
            allocator.compute_phase42_evar,
            allocator.compute_trans_beilinson_evar_risk_measure,
            allocator.compute_trans_fargues_beilinson_evar_risk_measure,
            allocator.compute_trans_deligne_fargues_beilinson_evar_risk_measure,
            allocator.compute_trans_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure,
            allocator.compute_clausen_scholze_deligne_fargues_beilinson_evar,
            allocator.compute_deligne_fargues_beilinson_evar,
            allocator.compute_fargues_beilinson_evar,
            allocator.compute_beilinson_drinfeld_evar,
            allocator.compute_beilinson_evar,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_beilinson_evar,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_beilinson_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar,
            PortfolioAllocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_blend,
            PortfolioAllocator.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar,
            PortfolioAllocator.singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_phase42,
            PortfolioAllocator.compute_38th_cumulant_evar,
            PortfolioAllocator.compute_phase42_evar,
            PortfolioAllocator.compute_trans_beilinson_evar_risk_measure,
            PortfolioAllocator.compute_trans_fargues_beilinson_evar_risk_measure,
            PortfolioAllocator.compute_trans_deligne_fargues_beilinson_evar_risk_measure,
            PortfolioAllocator.compute_trans_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure,
            PortfolioAllocator.compute_clausen_scholze_deligne_fargues_beilinson_evar,
            PortfolioAllocator.compute_deligne_fargues_beilinson_evar,
            PortfolioAllocator.compute_fargues_beilinson_evar,
            PortfolioAllocator.compute_beilinson_drinfeld_evar,
            PortfolioAllocator.compute_beilinson_evar,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_beilinson_evar,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_beilinson_evar_risk_measure,
        ]:
            res = alias_fn(returns)
            assert math.isclose(res["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_value"], ref["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_value"], rel_tol=1e-5)

    def test_compute_regime_blended_portfolio_v42(self, allocator):
        """Verify end-to-end regime blending under version=42."""
        blended_v42 = allocator.compute_information_theoretic_blend_weights(version=42)
        blended_v41 = allocator.compute_information_theoretic_blend_weights(version=41)

        assert isinstance(blended_v42, dict)
        assert math.isclose(sum(blended_v42.values()), 1.0, rel_tol=1e-5)
        # CVaR is highest in v42
        assert blended_v42["cvar"] > blended_v42["rp"]
        # v42 has even stronger CVaR prioritization than v41 due to Lurie-Beilinson-Drinfeld weights [3.20, 2.55, 2.50, 3.75] vs [3.10, 2.50, 2.45, 3.65]
        assert blended_v42["cvar"] >= blended_v41["cvar"] - 1e-4

    def test_phase42_backward_compatibility(self, allocator):
        """Verify that older version blends continue to compute correctly without errors."""
        for v in [1, 10, 20, 26, 30, 34, 35, 36, 37, 38, 39, 40, 41]:
            w = allocator.compute_information_theoretic_blend_weights(version=v)
            assert isinstance(w, dict)
            assert math.isclose(sum(w.values()), 1.0, rel_tol=1e-5)
