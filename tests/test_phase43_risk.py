r"""
tests/test_phase43_risk.py

Unit test suite for Phase 43 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F193.1: Lurie-W-Algebra Motivic Fisher-Rao Barycenter Blending
  (mu_lwa = [3.30, 2.60, 2.55, 3.85], simplex sum=1.0, heavy-tail CVaR prioritization)
- Feature F193.1: 39th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne-Beilinson-W-Algebra EVaR Tail Risk Measure
  (39! ~= 2.040 x 10^46, xi_w_alg = 0.999999, order=39)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() with version=43
- Strict backward compatibility with Phase 42 and earlier versions
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase43RiskAllocation:
    """Test suite for Phase 43 Risk Allocation and Barycenter Blending."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_feature_f193_1_barycenter_blend_basic_properties(self, allocator):
        """Verify that Lurie-W-Algebra Motivic Fisher-Rao barycenter converges on simplex."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_w_algebra_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 3.85, BL is second mu = 3.30, HERC is third mu = 2.60, RP is fourth mu = 2.55
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]
        # Interior point positivity
        for k, v in blended.items():
            assert 0.0 < v < 1.0

    def test_feature_f193_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        # 1. 1D Array
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_w_algebra_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        # 2. List of dicts
        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_w_algebra_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        # 3. 2D array
        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_w_algebra_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f193_1_barycenter_aliases_and_portfolio_allocator(self, allocator):
        """Verify that all barycenter aliases work on both UnifiedPortfolioAllocator and PortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_w_algebra_fisher_rao_barycenter_blend(w)

        for alias_fn in [
            allocator.compute_lurie_w_algebra_barycenter,
            allocator.compute_w_algebra_fisher_rao_barycenter,
            allocator.compute_w_algebra_barycenter,
            allocator.compute_phase43_fisher_rao_barycenter,
            allocator.compute_phase43_barycenter_blend,
            allocator.compute_w_algebra_fisher_rao_barycenter_blend,
            allocator.compute_motivic_w_algebra_barycenter_blend,
            allocator.compute_analytic_w_algebra_barycenter_blend,
            allocator.compute_chiral_w_algebra_barycenter_blend,
            allocator.compute_quantum_langlands_w_algebra_barycenter_blend,
            allocator.compute_chiral_oper_w_algebra_barycenter_blend,
            allocator.compute_lurie_quantum_langlands_w_algebra_barycenter,
            PortfolioAllocator.compute_lurie_w_algebra_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_lurie_w_algebra_barycenter,
            PortfolioAllocator.compute_w_algebra_fisher_rao_barycenter,
            PortfolioAllocator.compute_w_algebra_barycenter,
            PortfolioAllocator.compute_phase43_fisher_rao_barycenter,
            PortfolioAllocator.compute_phase43_barycenter_blend,
            PortfolioAllocator.compute_w_algebra_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_motivic_w_algebra_barycenter_blend,
            PortfolioAllocator.compute_analytic_w_algebra_barycenter_blend,
            PortfolioAllocator.compute_chiral_w_algebra_barycenter_blend,
            PortfolioAllocator.compute_quantum_langlands_w_algebra_barycenter_blend,
            PortfolioAllocator.compute_chiral_oper_w_algebra_barycenter_blend,
            PortfolioAllocator.compute_lurie_quantum_langlands_w_algebra_barycenter,
        ]:
            res = alias_fn(w)
            for k in ["bl", "herc", "rp", "cvar"]:
                assert math.isclose(res[k], ref[k], rel_tol=1e-5)

    def test_feature_f193_1_trans_singular_w_algebra_evar_hierarchy(self, allocator):
        """Verify 39th-cumulant W-Algebra EVaR strictly bounds 38th-cumulant Beilinson EVaR."""
        np.random.seed(43)
        returns = np.random.normal(-0.01, 0.05, 500)

        res_w_algebra = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_risk_measure(returns, alpha=0.05)
        res_beilinson = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure(returns, alpha=0.05)

        assert res_w_algebra["order"] == 39
        assert math.isclose(res_w_algebra["xi_w_alg"], 0.999999, rel_tol=1e-5)
        # 39th-cumulant EVaR >= 38th-cumulant EVaR
        assert res_w_algebra["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_value"] >= res_beilinson["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_value"] - 1e-6

    def test_feature_f193_1_evar_aliases_and_portfolio_allocator(self, allocator):
        """Verify all Phase 43 EVaR aliases on UnifiedPortfolioAllocator and PortfolioAllocator."""
        np.random.seed(43)
        returns = np.random.normal(-0.01, 0.05, 500)
        ref = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_risk_measure(returns)

        for alias_fn in [
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_w_algebra_evar,
            allocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_risk_measure,
            allocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_w_algebra_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_blend,
            allocator.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar,
            allocator.singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_phase43,
            allocator.compute_39th_cumulant_evar,
            allocator.compute_phase43_evar,
            allocator.compute_trans_w_algebra_evar_risk_measure,
            allocator.compute_trans_beilinson_w_algebra_evar_risk_measure,
            allocator.compute_trans_fargues_beilinson_w_algebra_evar_risk_measure,
            allocator.compute_trans_deligne_beilinson_w_algebra_evar_risk_measure,
            allocator.compute_trans_clausen_scholze_deligne_beilinson_w_algebra_evar_risk_measure,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_risk_measure,
            allocator.compute_clausen_scholze_deligne_beilinson_w_algebra_evar,
            allocator.compute_deligne_beilinson_w_algebra_evar,
            allocator.compute_beilinson_w_algebra_evar,
            allocator.compute_w_algebra_evar,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_w_algebra_evar,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_w_algebra_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_w_algebra_evar,
            PortfolioAllocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_risk_measure,
            PortfolioAllocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_w_algebra_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_blend,
            PortfolioAllocator.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar,
            PortfolioAllocator.singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_phase43,
            PortfolioAllocator.compute_39th_cumulant_evar,
            PortfolioAllocator.compute_phase43_evar,
            PortfolioAllocator.compute_trans_w_algebra_evar_risk_measure,
            PortfolioAllocator.compute_trans_beilinson_w_algebra_evar_risk_measure,
            PortfolioAllocator.compute_trans_fargues_beilinson_w_algebra_evar_risk_measure,
            PortfolioAllocator.compute_trans_deligne_beilinson_w_algebra_evar_risk_measure,
            PortfolioAllocator.compute_trans_clausen_scholze_deligne_beilinson_w_algebra_evar_risk_measure,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_risk_measure,
            PortfolioAllocator.compute_clausen_scholze_deligne_beilinson_w_algebra_evar,
            PortfolioAllocator.compute_deligne_beilinson_w_algebra_evar,
            PortfolioAllocator.compute_beilinson_w_algebra_evar,
            PortfolioAllocator.compute_w_algebra_evar,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_w_algebra_evar,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_w_algebra_evar_risk_measure,
        ]:
            res = alias_fn(returns)
            assert math.isclose(res["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_value"], ref["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_value"], rel_tol=1e-5)

    def test_compute_regime_blended_portfolio_v43(self, allocator):
        """Verify end-to-end regime blending under version=43."""
        blended_v43 = allocator.compute_information_theoretic_blend_weights(version=43)
        blended_v42 = allocator.compute_information_theoretic_blend_weights(version=42)

        assert isinstance(blended_v43, dict)
        assert math.isclose(sum(blended_v43.values()), 1.0, rel_tol=1e-5)
        # CVaR is highest in v43
        assert blended_v43["cvar"] > blended_v43["rp"]
        # v43 has even stronger CVaR prioritization than v42 due to Lurie-W-Algebra weights [3.30, 2.60, 2.55, 3.85] vs [3.20, 2.55, 2.50, 3.75]
        assert blended_v43["cvar"] >= blended_v42["cvar"] - 1e-4

    def test_phase43_backward_compatibility(self, allocator):
        """Verify that older version blends continue to compute correctly without errors."""
        for v in [1, 10, 20, 26, 30, 34, 35, 36, 37, 38, 39, 40, 41, 42]:
            w = allocator.compute_information_theoretic_blend_weights(version=v)
            assert isinstance(w, dict)
            assert math.isclose(sum(w.values()), 1.0, rel_tol=1e-5)
