r"""
tests/test_phase37_risk.py

Unit test suite for Phase 37 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F169.1: Lurie Wiles-Taylor-Kisin Motivic Fisher-Rao Barycenter Blending
  (mu_wiles_taylor_kisin = [2.80, 2.30, 2.25, 3.35], simplex sum=1.0, heavy-tail CVaR prioritization)
- Feature F169.1: 33rd-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Wiles EVaR Tail Risk Measure
  (33! = 868,331,761,881,188,649,551,397,040,128,000,000, xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles = 0.99998, order=33)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() with version=37
- Strict backward compatibility with Phase 36 and earlier versions
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase37RiskAllocation:
    """Test suite for Phase 37 Risk Allocation and Barycenter Blending."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_feature_f169_1_barycenter_blend_basic_properties(self, allocator):
        """Verify that Lurie Wiles-Taylor-Kisin Motivic Fisher-Rao barycenter converges on simplex."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_wiles_taylor_kisin_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 3.35, BL is second mu = 2.80, HERC is third mu = 2.30, RP is fourth mu = 2.25
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]

    def test_feature_f169_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        # 1. 1D Array
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_wiles_taylor_kisin_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        # 2. List of dicts
        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_wiles_taylor_kisin_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        # 3. 2D array
        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_wiles_taylor_kisin_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f169_1_barycenter_aliases_and_portfolio_allocator(self, allocator):
        """Verify that all barycenter aliases work on both UnifiedPortfolioAllocator and PortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_wiles_taylor_kisin_fisher_rao_barycenter_blend(w)

        for alias_fn in [
            allocator.compute_lurie_wiles_taylor_kisin_barycenter,
            allocator.compute_lurie_wiles_barycenter,
            allocator.compute_wiles_taylor_kisin_fisher_rao_barycenter,
            allocator.compute_wiles_taylor_kisin_barycenter,
            allocator.compute_phase37_fisher_rao_barycenter,
            allocator.compute_wiles_barycenter,
            allocator.compute_taylor_kisin_barycenter,
            allocator.compute_taylor_kisin_fisher_rao_barycenter,
            allocator.compute_lurie_wiles_fisher_rao_barycenter,
            allocator.compute_lurie_wiles_taylor_kisin_barycenter_blend,
            allocator.compute_wiles_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_lurie_wiles_taylor_kisin_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_lurie_wiles_taylor_kisin_barycenter,
            PortfolioAllocator.compute_lurie_wiles_barycenter,
            PortfolioAllocator.compute_wiles_taylor_kisin_fisher_rao_barycenter,
            PortfolioAllocator.compute_wiles_taylor_kisin_barycenter,
            PortfolioAllocator.compute_phase37_fisher_rao_barycenter,
            PortfolioAllocator.compute_wiles_barycenter,
            PortfolioAllocator.compute_taylor_kisin_barycenter,
            PortfolioAllocator.compute_taylor_kisin_fisher_rao_barycenter,
            PortfolioAllocator.compute_lurie_wiles_fisher_rao_barycenter,
            PortfolioAllocator.compute_lurie_wiles_taylor_kisin_barycenter_blend,
            PortfolioAllocator.compute_wiles_fisher_rao_barycenter_blend,
        ]:
            res = alias_fn(w)
            for k in ["bl", "herc", "rp", "cvar"]:
                assert math.isclose(res[k], ref[k], rel_tol=1e-5)

    def test_feature_f169_1_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles_evar_hierarchy(self, allocator):
        """Verify 33rd-cumulant Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Wiles EVaR strictly bounds lower-order EVaRs."""
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)

        res_wiles = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles_evar_risk_measure(returns, alpha=0.05)
        res_transcendent = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_evar_risk_measure(returns, alpha=0.05)

        assert res_wiles["order"] == 33
        assert math.isclose(res_wiles["xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles"], 0.99998, rel_tol=1e-5)
        # Wiles EVaR >= Transcendent EVaR
        assert res_wiles["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles_evar_value"] >= res_transcendent["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_evar_value"] - 1e-6

    def test_feature_f169_1_evar_aliases_and_portfolio_allocator(self, allocator):
        """Verify all Phase 37 EVaR aliases on UnifiedPortfolioAllocator and PortfolioAllocator."""
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)
        ref = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles_evar_risk_measure(returns)

        for alias_fn in [
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles_evar,
            allocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles_evar_blend,
            allocator.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles_evar,
            allocator.singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles_evar_phase37,
            allocator.compute_33rd_cumulant_evar,
            allocator.compute_phase37_evar,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_wiles_evar,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_wiles_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles_evar,
            PortfolioAllocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles_evar_risk_measure,
            PortfolioAllocator.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles_evar,
            PortfolioAllocator.compute_phase37_evar,
            PortfolioAllocator.compute_33rd_cumulant_evar,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_wiles_evar,
        ]:
            res = alias_fn(returns)
            assert math.isclose(res["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles_evar_value"], ref["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles_evar_value"], rel_tol=1e-5)

    def test_compute_regime_blended_portfolio_v37(self, allocator):
        """Verify end-to-end regime blending under version=37."""
        blended_v37 = allocator.compute_information_theoretic_blend_weights(version=37)
        blended_v36 = allocator.compute_information_theoretic_blend_weights(version=36)

        assert isinstance(blended_v37, dict)
        assert math.isclose(sum(blended_v37.values()), 1.0, rel_tol=1e-5)
        # CVaR is highest in v37
        assert blended_v37["cvar"] > blended_v37["rp"]
        # v37 has even stronger CVaR prioritization than v36 due to Wiles-Taylor-Kisin weights [2.80, 2.30, 2.25, 3.35] vs [2.75, 2.25, 2.20, 3.30]
        assert blended_v37["cvar"] >= blended_v36["cvar"] - 1e-4

    def test_phase37_backward_compatibility(self, allocator):
        """Verify that older version blends continue to compute correctly without errors."""
        for v in [1, 10, 20, 26, 30, 34, 35, 36]:
            w = allocator.compute_information_theoretic_blend_weights(version=v)
            assert isinstance(w, dict)
            assert math.isclose(sum(w.values()), 1.0, rel_tol=1e-5)
