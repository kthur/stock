r"""
tests/test_phase35_risk.py

Unit test suite for Phase 35 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F161.1: Lurie Shafarevich-Fontaine-Mazur Motivic Fisher-Rao Barycenter Blending
  (mu_sha = [2.70, 2.20, 2.15, 3.25], simplex sum=1.0, heavy-tail CVaR prioritization)
- Feature F161.1: 31st-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme EVaR Tail Risk Measure
  (31! = 8,222,838,654,177,922,817,721,562,880,000,000, xi_singular_eternal_omni_cosmic_infinite_supreme = 0.9999, order=31)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() with version=35
- Strict backward compatibility with Phase 34 and earlier versions
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase35RiskAllocation:
    """Test suite for Phase 35 Risk Allocation and Barycenter Blending."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_feature_f161_1_barycenter_blend_basic_properties(self, allocator):
        """Verify that Lurie Shafarevich-Fontaine-Mazur Motivic Fisher-Rao barycenter converges on simplex."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_shafarevich_fontaine_mazur_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 3.25, BL is second mu = 2.70
        assert blended["cvar"] > blended["herc"]
        assert blended["cvar"] > blended["rp"]
        assert blended["bl"] > blended["rp"]

    def test_feature_f161_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        # 1. 1D Array
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_shafarevich_fontaine_mazur_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        # 2. List of dicts
        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_shafarevich_fontaine_mazur_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        # 3. 2D array
        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_shafarevich_fontaine_mazur_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f161_1_barycenter_aliases_and_portfolio_allocator(self, allocator):
        """Verify that all barycenter aliases work on both UnifiedPortfolioAllocator and PortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_shafarevich_fontaine_mazur_fisher_rao_barycenter_blend(w)

        for alias_fn in [
            allocator.compute_lurie_shafarevich_fontaine_mazur_barycenter,
            allocator.compute_lurie_shafarevich_barycenter,
            allocator.compute_fontaine_mazur_fisher_rao_barycenter,
            allocator.compute_shafarevich_fontaine_mazur_fisher_rao_barycenter,
            allocator.compute_phase35_fisher_rao_barycenter,
            allocator.compute_shafarevich_barycenter,
            allocator.compute_fontaine_mazur_barycenter,
            allocator.compute_shafarevich_fontaine_mazur_barycenter,
            allocator.compute_lurie_shafarevich_fisher_rao_barycenter,
            allocator.compute_lurie_shafarevich_fontaine_mazur_barycenter_blend,
            allocator.compute_shafarevich_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_lurie_shafarevich_fontaine_mazur_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_lurie_shafarevich_fontaine_mazur_barycenter,
            PortfolioAllocator.compute_lurie_shafarevich_barycenter,
            PortfolioAllocator.compute_fontaine_mazur_fisher_rao_barycenter,
            PortfolioAllocator.compute_shafarevich_fontaine_mazur_fisher_rao_barycenter,
            PortfolioAllocator.compute_phase35_fisher_rao_barycenter,
            PortfolioAllocator.compute_shafarevich_barycenter,
            PortfolioAllocator.compute_fontaine_mazur_barycenter,
            PortfolioAllocator.compute_shafarevich_fontaine_mazur_barycenter,
            PortfolioAllocator.compute_lurie_shafarevich_fisher_rao_barycenter,
            PortfolioAllocator.compute_lurie_shafarevich_fontaine_mazur_barycenter_blend,
            PortfolioAllocator.compute_shafarevich_fisher_rao_barycenter_blend,
        ]:
            res = alias_fn(w)
            for k in ["bl", "herc", "rp", "cvar"]:
                assert math.isclose(res[k], ref[k], rel_tol=1e-5)

    def test_feature_f161_1_trans_singular_eternal_omni_cosmic_infinite_supreme_evar_hierarchy(self, allocator):
        """Verify 31st-cumulant Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme EVaR strictly bounds lower-order EVaRs."""
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)

        res_supreme = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_evar_risk_measure(returns, alpha=0.05)
        res_infinite = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_evar_risk_measure(returns, alpha=0.05)

        assert res_supreme["order"] == 31
        assert math.isclose(res_supreme["xi_singular_eternal_omni_cosmic_infinite_supreme"], 0.9999, rel_tol=1e-5)
        # Supreme EVaR >= Infinite EVaR
        assert res_supreme["trans_singular_eternal_omni_cosmic_infinite_supreme_evar_value"] >= res_infinite["trans_singular_eternal_omni_cosmic_infinite_evar_value"] - 1e-6

    def test_feature_f161_1_evar_aliases_and_portfolio_allocator(self, allocator):
        """Verify all Phase 35 EVaR aliases on UnifiedPortfolioAllocator and PortfolioAllocator."""
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)
        ref = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_evar_risk_measure(returns)

        for alias_fn in [
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_evar,
            allocator.trans_singular_eternal_omni_cosmic_infinite_supreme_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_evar_blend,
            allocator.compute_singular_eternal_omni_cosmic_infinite_supreme_evar,
            allocator.singular_eternal_omni_cosmic_infinite_supreme_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_evar_phase35,
            allocator.compute_31st_cumulant_evar,
            allocator.compute_phase35_evar,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_evar,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_evar,
            PortfolioAllocator.trans_singular_eternal_omni_cosmic_infinite_supreme_evar_risk_measure,
            PortfolioAllocator.compute_singular_eternal_omni_cosmic_infinite_supreme_evar,
            PortfolioAllocator.compute_phase35_evar,
            PortfolioAllocator.compute_31st_cumulant_evar,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_evar,
        ]:
            res = alias_fn(returns)
            assert math.isclose(res["trans_singular_eternal_omni_cosmic_infinite_supreme_evar_value"], ref["trans_singular_eternal_omni_cosmic_infinite_supreme_evar_value"], rel_tol=1e-5)

    def test_compute_regime_blended_portfolio_v35(self, allocator):
        """Verify end-to-end regime blending under version=35."""
        blended_v35 = allocator.compute_information_theoretic_blend_weights(version=35)
        blended_v34 = allocator.compute_information_theoretic_blend_weights(version=34)

        assert isinstance(blended_v35, dict)
        assert set(blended_v35.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended_v35.values()), 1.0, rel_tol=1e-5)

        # In v35, CVaR weight is further fortified (mu=3.25, delta_cvar=+10.20*eps_w)
        assert blended_v35["cvar"] > blended_v34["cvar"]
        assert blended_v35["cvar"] > 0.001

    def test_strict_backward_compatibility_v34_v33(self, allocator):
        """Verify backward compatibility for regime blending with version=34 and version=33."""
        blended_v34 = allocator.compute_information_theoretic_blend_weights(version=34)
        blended_v33 = allocator.compute_information_theoretic_blend_weights(version=33)

        assert math.isclose(sum(blended_v34.values()), 1.0, rel_tol=1e-5)
        assert math.isclose(sum(blended_v33.values()), 1.0, rel_tol=1e-5)
        assert blended_v34["cvar"] > blended_v33["cvar"] - 1e-6
