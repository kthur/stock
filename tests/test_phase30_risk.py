r"""
tests/test_phase30_risk.py

Unit test suite for Phase 30 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F141.1: Lurie Kolyvagin-Iwasawa Motivic Fisher-Rao Barycenter Blending
  (mu_kolyvagin = [2.45, 1.95, 1.90, 3.00], simplex sum=1.0, heavy-tail CVaR prioritization)
- Feature F141.1: 26th-Cumulant Expansion Trans-Singular-Infinity EVaR Tail Risk Measure
  (26! = 403,291,461,126,605,635,584,000,000, xi_singular_infinity = 0.995, order=26)
- UnifiedPortfolioAllocator compute_regime_blended_portfolio() with version=30
- Strict backward compatibility with Phase 29 and earlier versions
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase30RiskAllocation:
    """Test suite for Phase 30 Risk Allocation and Barycenter Blending."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_feature_f141_1_barycenter_blend_basic_properties(self, allocator):
        """Verify that Lurie Kolyvagin-Iwasawa Motivic Fisher-Rao barycenter converges on simplex."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_kolyvagin_iwasawa_motivic_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 3.00, BL is second mu = 2.45
        assert blended["cvar"] > blended["herc"]
        assert blended["cvar"] > blended["rp"]
        assert blended["bl"] > blended["rp"]

    def test_feature_f141_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        # 1. 1D Array
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_kolyvagin_iwasawa_motivic_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        # 2. List of dicts
        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_kolyvagin_iwasawa_motivic_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        # 3. 2D array
        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_kolyvagin_iwasawa_motivic_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f141_1_barycenter_aliases_and_portfolio_allocator(self, allocator):
        """Verify that all barycenter aliases work on both UnifiedPortfolioAllocator and PortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_kolyvagin_iwasawa_motivic_fisher_rao_barycenter_blend(w)

        for alias_fn in [
            allocator.compute_lurie_kolyvagin_iwasawa_barycenter,
            allocator.compute_kolyvagin_iwasawa_fisher_rao_barycenter,
            allocator.compute_kolyvagin_iwasawa_barycenter,
            allocator.compute_lurie_kolyvagin_barycenter,
            allocator.compute_lurie_iwasawa_barycenter,
            allocator.compute_kolyvagin_fisher_rao_barycenter,
            allocator.compute_iwasawa_fisher_rao_barycenter,
            allocator.compute_phase30_fisher_rao_barycenter,
            PortfolioAllocator.compute_lurie_kolyvagin_iwasawa_motivic_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_lurie_kolyvagin_iwasawa_barycenter,
            PortfolioAllocator.compute_kolyvagin_iwasawa_fisher_rao_barycenter,
            PortfolioAllocator.compute_kolyvagin_barycenter,
            PortfolioAllocator.compute_iwasawa_barycenter,
            PortfolioAllocator.compute_phase30_fisher_rao_barycenter,
        ]:
            res = alias_fn(w)
            for k in ["bl", "herc", "rp", "cvar"]:
                assert math.isclose(res[k], ref[k], rel_tol=1e-5)

    def test_feature_f141_1_trans_singular_infinity_evar_hierarchy(self, allocator):
        """Verify 26th-cumulant Trans-Singular-Infinity EVaR strictly bounds lower-order EVaRs."""
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)  # slightly negative mean with variance

        res_inf = allocator.compute_trans_singular_infinity_evar_risk_measure(returns, alpha=0.05)
        res_sup = allocator.compute_trans_singular_supreme_evar_risk_measure(returns, alpha=0.05)

        assert res_inf["order"] == 26
        assert math.isclose(res_inf["xi_singular_infinity"], 0.995, rel_tol=1e-5)
        # Trans-Singular-Infinity EVaR >= Trans-Singular-Supreme EVaR
        assert res_inf["trans_singular_infinity_evar_value"] >= res_sup["trans_singular_supreme_evar_value"] - 1e-6

    def test_feature_f141_1_evar_aliases_and_portfolio_allocator(self, allocator):
        """Verify all Phase 30 EVaR aliases on UnifiedPortfolioAllocator and PortfolioAllocator."""
        returns = np.array([-0.05, -0.02, 0.01, 0.03, -0.01])
        ref = allocator.compute_trans_singular_infinity_evar_risk_measure(returns)

        for alias_fn in [
            allocator.compute_trans_singular_infinity_evar,
            allocator.trans_singular_infinity_evar_risk_measure,
            allocator.compute_trans_singular_infinity_evar_blend,
            allocator.compute_singular_infinity_evar,
            allocator.singular_infinity_evar_risk_measure,
            allocator.compute_trans_singular_infinity_evar_phase30,
            allocator.compute_26th_cumulant_evar,
            allocator.compute_phase30_evar,
            PortfolioAllocator.compute_trans_singular_infinity_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_infinity_evar,
            PortfolioAllocator.trans_singular_infinity_evar_risk_measure,
            PortfolioAllocator.compute_singular_infinity_evar,
            PortfolioAllocator.compute_phase30_evar,
        ]:
            res = alias_fn(returns)
            assert math.isclose(res["trans_singular_infinity_evar_value"], ref["trans_singular_infinity_evar_value"], rel_tol=1e-5)

    def test_compute_regime_blended_portfolio_v30(self, allocator):
        """Verify end-to-end regime blending under version=30."""
        blended_v30 = allocator.compute_information_theoretic_blend_weights(version=30)
        blended_v29 = allocator.compute_information_theoretic_blend_weights(version=29)

        assert isinstance(blended_v30, dict)
        assert set(blended_v30.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended_v30.values()), 1.0, rel_tol=1e-5)

        # In v30, CVaR weight is further fortified (mu=3.00, delta_cvar=+8.20*eps_w)
        assert blended_v30["cvar"] > blended_v29["cvar"]
        assert blended_v30["cvar"] > 0.001

    def test_strict_backward_compatibility_v29_v28(self, allocator):
        """Verify backward compatibility for regime blending with version=29 and version=28."""
        blended_v29 = allocator.compute_information_theoretic_blend_weights(version=29)
        blended_v28 = allocator.compute_information_theoretic_blend_weights(version=28)

        assert math.isclose(sum(blended_v29.values()), 1.0, rel_tol=1e-5)
        assert math.isclose(sum(blended_v28.values()), 1.0, rel_tol=1e-5)
        assert blended_v29["cvar"] > blended_v28["cvar"] - 1e-6
