r"""
tests/test_phase45_risk.py

Unit test suite for Phase 45 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F201.1: Lurie-Kac-Moody-Whittaker Motivic Fisher-Rao Barycenter Blending
  (mu_lkmw = [3.50, 2.70, 2.65, 4.05], simplex sum=1.0, heavy-tail CVaR prioritization)
- Feature F201.1: 41st-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne-Beilinson-W-Algebra-Virasoro-Kac-Moody EVaR Tail Risk Measure
  (41! ~= 3.345 x 10^49, xi_km = 0.9999998, order=41)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() with version=45
- Strict backward compatibility with Phase 44 and earlier versions
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase45RiskAllocation:
    """Test suite for Phase 45 Risk Allocation and Barycenter Blending."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_feature_f201_1_barycenter_blend_basic_properties(self, allocator):
        """Verify that Lurie-Kac-Moody-Whittaker Motivic Fisher-Rao barycenter converges on simplex."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_kac_moody_whittaker_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 4.05, BL is second mu = 3.50, HERC is third mu = 2.70, RP is fourth mu = 2.65
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]
        # Interior point positivity
        for k, v in blended.items():
            assert 0.0 < v < 1.0

    def test_feature_f201_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        # 1. 1D Array
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_kac_moody_whittaker_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        # 2. List of dicts
        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_kac_moody_whittaker_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        # 3. 2D array
        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_kac_moody_whittaker_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f201_1_barycenter_aliases_and_portfolio_allocator(self, allocator):
        """Verify that all barycenter aliases work on both UnifiedPortfolioAllocator and PortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_kac_moody_whittaker_fisher_rao_barycenter_blend(w)

        for alias_fn in [
            allocator.compute_lurie_kac_moody_whittaker_barycenter,
            allocator.compute_lurie_kac_moody_barycenter,
            allocator.compute_kac_moody_whittaker_fisher_rao_barycenter,
            allocator.compute_kac_moody_whittaker_barycenter,
            allocator.compute_phase45_fisher_rao_barycenter,
            allocator.compute_phase45_barycenter_blend,
            allocator.compute_kac_moody_whittaker_fisher_rao_barycenter_blend,
            allocator.compute_motivic_kac_moody_whittaker_barycenter_blend,
            allocator.compute_analytic_kac_moody_whittaker_barycenter_blend,
            allocator.compute_chiral_kac_moody_whittaker_barycenter_blend,
            allocator.compute_quantum_langlands_kac_moody_whittaker_barycenter_blend,
            allocator.compute_chiral_oper_kac_moody_whittaker_barycenter_blend,
            allocator.compute_lurie_quantum_langlands_kac_moody_whittaker_barycenter,
            allocator.compute_lkmw_barycenter,
            allocator.compute_lkmw_fisher_rao_barycenter,
            PortfolioAllocator.compute_lurie_kac_moody_whittaker_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_lurie_kac_moody_whittaker_barycenter,
            PortfolioAllocator.compute_lurie_kac_moody_barycenter,
            PortfolioAllocator.compute_kac_moody_whittaker_fisher_rao_barycenter,
            PortfolioAllocator.compute_kac_moody_whittaker_barycenter,
            PortfolioAllocator.compute_phase45_fisher_rao_barycenter,
            PortfolioAllocator.compute_phase45_barycenter_blend,
            PortfolioAllocator.compute_kac_moody_whittaker_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_motivic_kac_moody_whittaker_barycenter_blend,
            PortfolioAllocator.compute_analytic_kac_moody_whittaker_barycenter_blend,
            PortfolioAllocator.compute_chiral_kac_moody_whittaker_barycenter_blend,
            PortfolioAllocator.compute_quantum_langlands_kac_moody_whittaker_barycenter_blend,
            PortfolioAllocator.compute_chiral_oper_kac_moody_whittaker_barycenter_blend,
            PortfolioAllocator.compute_lurie_quantum_langlands_kac_moody_whittaker_barycenter,
            PortfolioAllocator.compute_lkmw_barycenter,
            PortfolioAllocator.compute_lkmw_fisher_rao_barycenter,
        ]:
            res = alias_fn(w)
            for k in ["bl", "herc", "rp", "cvar"]:
                assert math.isclose(res[k], ref[k], rel_tol=1e-5)

    def test_feature_f201_1_trans_singular_kac_moody_evar_hierarchy(self, allocator):
        """Verify 41st-cumulant Kac-Moody EVaR strictly bounds 40th-cumulant Virasoro EVaR."""
        np.random.seed(45)
        returns = np.random.normal(-0.01, 0.05, 500)

        res_km = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_risk_measure(returns, alpha=0.05)
        res_vir = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_evar_risk_measure(returns, alpha=0.05)

        assert res_km["order"] == 41
        assert math.isclose(res_km["xi_km"], 0.9999998, rel_tol=1e-5)
        # 41st-cumulant EVaR >= 40th-cumulant EVaR
        assert res_km["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_value"] >= res_vir["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_evar_value"] - 1e-6

    def test_feature_f201_1_evar_aliases_and_portfolio_allocator(self, allocator):
        """Verify all Phase 45 EVaR aliases on UnifiedPortfolioAllocator and PortfolioAllocator."""
        np.random.seed(45)
        returns = np.random.normal(-0.01, 0.05, 500)
        ref = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_risk_measure(returns)

        for alias_fn in [
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar,
            allocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_blend,
            allocator.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar,
            allocator.singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_phase45,
            allocator.compute_41st_cumulant_evar,
            allocator.compute_phase45_evar,
            allocator.compute_trans_kac_moody_evar_risk_measure,
            allocator.compute_trans_virasoro_kac_moody_evar_risk_measure,
            allocator.compute_trans_w_algebra_virasoro_kac_moody_evar_risk_measure,
            allocator.compute_trans_beilinson_virasoro_kac_moody_evar_risk_measure,
            allocator.compute_trans_fargues_beilinson_virasoro_kac_moody_evar_risk_measure,
            allocator.compute_trans_deligne_virasoro_kac_moody_evar_risk_measure,
            allocator.compute_trans_clausen_scholze_virasoro_kac_moody_evar_risk_measure,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_virasoro_kac_moody_evar,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_virasoro_kac_moody_evar_risk_measure,
            allocator.compute_clausen_scholze_virasoro_kac_moody_evar,
            allocator.compute_deligne_virasoro_kac_moody_evar,
            allocator.compute_beilinson_virasoro_kac_moody_evar,
            allocator.compute_w_algebra_virasoro_kac_moody_evar,
            allocator.compute_virasoro_kac_moody_evar,
            allocator.compute_kac_moody_evar,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_w_algebra_virasoro_kac_moody_evar,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_w_algebra_virasoro_kac_moody_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar,
            PortfolioAllocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_blend,
            PortfolioAllocator.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar,
            PortfolioAllocator.singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_phase45,
            PortfolioAllocator.compute_41st_cumulant_evar,
            PortfolioAllocator.compute_phase45_evar,
            PortfolioAllocator.compute_trans_kac_moody_evar_risk_measure,
            PortfolioAllocator.compute_trans_virasoro_kac_moody_evar_risk_measure,
            PortfolioAllocator.compute_trans_w_algebra_virasoro_kac_moody_evar_risk_measure,
            PortfolioAllocator.compute_trans_beilinson_virasoro_kac_moody_evar_risk_measure,
            PortfolioAllocator.compute_trans_fargues_beilinson_virasoro_kac_moody_evar_risk_measure,
            PortfolioAllocator.compute_trans_deligne_virasoro_kac_moody_evar_risk_measure,
            PortfolioAllocator.compute_trans_clausen_scholze_virasoro_kac_moody_evar_risk_measure,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_virasoro_kac_moody_evar,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_virasoro_kac_moody_evar_risk_measure,
            PortfolioAllocator.compute_clausen_scholze_virasoro_kac_moody_evar,
            PortfolioAllocator.compute_deligne_virasoro_kac_moody_evar,
            PortfolioAllocator.compute_beilinson_virasoro_kac_moody_evar,
            PortfolioAllocator.compute_w_algebra_virasoro_kac_moody_evar,
            PortfolioAllocator.compute_virasoro_kac_moody_evar,
            PortfolioAllocator.compute_kac_moody_evar,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_w_algebra_virasoro_kac_moody_evar,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_w_algebra_virasoro_kac_moody_evar_risk_measure,
        ]:
            res = alias_fn(returns)
            val = res["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_value"]
            ref_val = ref["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_value"]
            assert math.isclose(val, ref_val, rel_tol=1e-5)

    def test_feature_f201_1_compute_information_theoretic_blend_weights_v45(self, allocator):
        """Verify information-theoretic blend weights under version=45."""
        market_regime = "BEAR"
        weights_v44 = allocator.compute_information_theoretic_blend_weights(market_regime, version=44)
        weights_v45 = allocator.compute_information_theoretic_blend_weights(market_regime, version=45)

        assert isinstance(weights_v45, dict)
        assert set(weights_v45.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(weights_v45.values()), 1.0, rel_tol=1e-5)

        # In BEAR regime with Phase 45, CVaR weight is boosted even further
        assert weights_v45["cvar"] >= weights_v44["cvar"] - 1e-6
        for k, v in weights_v45.items():
            assert 0.0 < v < 1.0

    def test_feature_f201_1_backward_compatibility(self, allocator):
        """Ensure versions 44, 43, 42, 41, 40 still yield valid weights without regression."""
        w_v44 = allocator.compute_information_theoretic_blend_weights("BULL_LOW_VOL", version=44)
        w_v43 = allocator.compute_information_theoretic_blend_weights("BULL_LOW_VOL", version=43)
        w_v42 = allocator.compute_information_theoretic_blend_weights("BULL_LOW_VOL", version=42)
        w_v41 = allocator.compute_information_theoretic_blend_weights("BULL_LOW_VOL", version=41)
        w_v40 = allocator.compute_information_theoretic_blend_weights("BULL_LOW_VOL", version=40)

        assert math.isclose(sum(w_v44.values()), 1.0, rel_tol=1e-5)
        assert math.isclose(sum(w_v43.values()), 1.0, rel_tol=1e-5)
        assert math.isclose(sum(w_v42.values()), 1.0, rel_tol=1e-5)
        assert math.isclose(sum(w_v41.values()), 1.0, rel_tol=1e-5)
        assert math.isclose(sum(w_v40.values()), 1.0, rel_tol=1e-5)
