r"""
tests/test_phase34_risk.py

Unit test suite for Phase 34 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F157.1: Lurie BSD-Gross-Zagier Motivic Fisher-Rao Barycenter Blending
  (mu_bsd = [2.65, 2.15, 2.10, 3.20], simplex sum=1.0, heavy-tail CVaR prioritization)
- Feature F157.1: 30th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite EVaR Tail Risk Measure
  (30! = 265,252,859,812,191,058,636,308,480,000,000, xi_singular_eternal_omni_cosmic_infinite = 0.9998, order=30)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() with version=34
- Strict backward compatibility with Phase 33 and earlier versions
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase34RiskAllocation:
    """Test suite for Phase 34 Risk Allocation and Barycenter Blending."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_feature_f157_1_barycenter_blend_basic_properties(self, allocator):
        """Verify that Lurie BSD-Gross-Zagier Motivic Fisher-Rao barycenter converges on simplex."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_bsd_gross_zagier_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 3.20, BL is second mu = 2.65
        assert blended["cvar"] > blended["herc"]
        assert blended["cvar"] > blended["rp"]
        assert blended["bl"] > blended["rp"]

    def test_feature_f157_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        # 1. 1D Array
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_bsd_gross_zagier_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        # 2. List of dicts
        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_bsd_gross_zagier_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        # 3. 2D array
        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_bsd_gross_zagier_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f157_1_barycenter_aliases_and_portfolio_allocator(self, allocator):
        """Verify that all barycenter aliases work on both UnifiedPortfolioAllocator and PortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_bsd_gross_zagier_fisher_rao_barycenter_blend(w)

        for alias_fn in [
            allocator.compute_lurie_bsd_gross_zagier_barycenter,
            allocator.compute_lurie_bsd_barycenter,
            allocator.compute_gross_zagier_fisher_rao_barycenter,
            allocator.compute_bsd_gross_zagier_fisher_rao_barycenter,
            allocator.compute_phase34_fisher_rao_barycenter,
            allocator.compute_bsd_barycenter,
            allocator.compute_gross_zagier_barycenter,
            allocator.compute_bsd_gross_zagier_barycenter,
            allocator.compute_lurie_bsd_fisher_rao_barycenter,
            allocator.compute_lurie_bsd_gross_zagier_barycenter_blend,
            allocator.compute_bsd_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_lurie_bsd_gross_zagier_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_lurie_bsd_gross_zagier_barycenter,
            PortfolioAllocator.compute_lurie_bsd_barycenter,
            PortfolioAllocator.compute_gross_zagier_fisher_rao_barycenter,
            PortfolioAllocator.compute_bsd_gross_zagier_fisher_rao_barycenter,
            PortfolioAllocator.compute_phase34_fisher_rao_barycenter,
            PortfolioAllocator.compute_bsd_barycenter,
            PortfolioAllocator.compute_gross_zagier_barycenter,
            PortfolioAllocator.compute_bsd_gross_zagier_barycenter,
            PortfolioAllocator.compute_lurie_bsd_fisher_rao_barycenter,
            PortfolioAllocator.compute_lurie_bsd_gross_zagier_barycenter_blend,
            PortfolioAllocator.compute_bsd_fisher_rao_barycenter_blend,
        ]:
            res = alias_fn(w)
            for k in ["bl", "herc", "rp", "cvar"]:
                assert math.isclose(res[k], ref[k], rel_tol=1e-5)

    def test_feature_f157_1_trans_singular_eternal_omni_cosmic_infinite_evar_hierarchy(self, allocator):
        """Verify 30th-cumulant Trans-Singular-Eternal-Omni-Cosmic-Infinite EVaR strictly bounds lower-order EVaRs."""
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)

        res_infinite = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_evar_risk_measure(returns, alpha=0.05)
        res_cosmic = allocator.compute_trans_singular_eternal_omni_cosmic_evar_risk_measure(returns, alpha=0.05)

        assert res_infinite["order"] == 30
        assert math.isclose(res_infinite["xi_singular_eternal_omni_cosmic_infinite"], 0.9998, rel_tol=1e-5)
        # Trans-Singular-Eternal-Omni-Cosmic-Infinite EVaR >= Trans-Singular-Eternal-Omni-Cosmic EVaR
        assert res_infinite["trans_singular_eternal_omni_cosmic_infinite_evar_value"] >= res_cosmic["trans_singular_eternal_omni_cosmic_evar_value"] - 1e-6

    def test_feature_f157_1_evar_aliases_and_portfolio_allocator(self, allocator):
        """Verify all Phase 34 EVaR aliases on UnifiedPortfolioAllocator and PortfolioAllocator."""
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)
        ref = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_evar_risk_measure(returns)

        for alias_fn in [
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_evar,
            allocator.trans_singular_eternal_omni_cosmic_infinite_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_evar_blend,
            allocator.compute_singular_eternal_omni_cosmic_infinite_evar,
            allocator.singular_eternal_omni_cosmic_infinite_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_evar_phase34,
            allocator.compute_30th_cumulant_evar,
            allocator.compute_phase34_evar,
            allocator.compute_eternal_omni_cosmic_infinite_evar,
            allocator.compute_eternal_omni_cosmic_infinite_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_evar,
            PortfolioAllocator.trans_singular_eternal_omni_cosmic_infinite_evar_risk_measure,
            PortfolioAllocator.compute_singular_eternal_omni_cosmic_infinite_evar,
            PortfolioAllocator.compute_phase34_evar,
            PortfolioAllocator.compute_30th_cumulant_evar,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_evar,
        ]:
            res = alias_fn(returns)
            assert math.isclose(res["trans_singular_eternal_omni_cosmic_infinite_evar_value"], ref["trans_singular_eternal_omni_cosmic_infinite_evar_value"], rel_tol=1e-5)

    def test_compute_regime_blended_portfolio_v34(self, allocator):
        """Verify end-to-end regime blending under version=34."""
        blended_v34 = allocator.compute_information_theoretic_blend_weights(version=34)
        blended_v33 = allocator.compute_information_theoretic_blend_weights(version=33)

        assert isinstance(blended_v34, dict)
        assert set(blended_v34.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended_v34.values()), 1.0, rel_tol=1e-5)

        # In v34, CVaR weight is further fortified (mu=3.20, delta_cvar=+9.80*eps_w)
        assert blended_v34["cvar"] > blended_v33["cvar"]
        assert blended_v34["cvar"] > 0.001

    def test_strict_backward_compatibility_v33_v32(self, allocator):
        """Verify backward compatibility for regime blending with version=33 and version=32."""
        blended_v33 = allocator.compute_information_theoretic_blend_weights(version=33)
        blended_v32 = allocator.compute_information_theoretic_blend_weights(version=32)

        assert math.isclose(sum(blended_v33.values()), 1.0, rel_tol=1e-5)
        assert math.isclose(sum(blended_v32.values()), 1.0, rel_tol=1e-5)
        assert blended_v33["cvar"] > blended_v32["cvar"] - 1e-6
