r"""
tests/test_phase33_risk.py

Unit test suite for Phase 33 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F153.1: Lurie Tamagawa-Bloch-Kato Motivic Fisher-Rao Barycenter Blending
  (mu_tamagawa = [2.60, 2.10, 2.05, 3.15], simplex sum=1.0, heavy-tail CVaR prioritization)
- Feature F153.1: 29th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic EVaR Tail Risk Measure
  (29! = 8,841,761,993,739,701,954,543,616,000,000, xi_singular_eternal_omni_cosmic = 0.9995, order=29)
- UnifiedPortfolioAllocator compute_regime_blended_portfolio() with version=33
- Strict backward compatibility with Phase 32 and earlier versions
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase33RiskAllocation:
    """Test suite for Phase 33 Risk Allocation and Barycenter Blending."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_feature_f153_1_barycenter_blend_basic_properties(self, allocator):
        """Verify that Lurie Tamagawa-Bloch-Kato Motivic Fisher-Rao barycenter converges on simplex."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_tamagawa_bloch_kato_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 3.15, BL is second mu = 2.60
        assert blended["cvar"] > blended["herc"]
        assert blended["cvar"] > blended["rp"]
        assert blended["bl"] > blended["rp"]

    def test_feature_f153_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        # 1. 1D Array
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_tamagawa_bloch_kato_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        # 2. List of dicts
        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_tamagawa_bloch_kato_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        # 3. 2D array
        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_tamagawa_bloch_kato_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f153_1_barycenter_aliases_and_portfolio_allocator(self, allocator):
        """Verify that all barycenter aliases work on both UnifiedPortfolioAllocator and PortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_tamagawa_bloch_kato_fisher_rao_barycenter_blend(w)

        for alias_fn in [
            allocator.compute_lurie_tamagawa_bloch_kato_barycenter,
            allocator.compute_lurie_tamagawa_barycenter,
            allocator.compute_bloch_kato_fisher_rao_barycenter,
            allocator.compute_tamagawa_fisher_rao_barycenter,
            allocator.compute_phase33_fisher_rao_barycenter,
            allocator.compute_tamagawa_barycenter,
            allocator.compute_bloch_kato_barycenter,
            allocator.compute_tamagawa_bloch_kato_barycenter,
            allocator.compute_lurie_tamagawa_fisher_rao_barycenter,
            allocator.compute_lurie_tamagawa_bloch_kato_barycenter_blend,
            allocator.compute_tamagawa_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_lurie_tamagawa_bloch_kato_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_lurie_tamagawa_bloch_kato_barycenter,
            PortfolioAllocator.compute_lurie_tamagawa_barycenter,
            PortfolioAllocator.compute_bloch_kato_fisher_rao_barycenter,
            PortfolioAllocator.compute_tamagawa_fisher_rao_barycenter,
            PortfolioAllocator.compute_phase33_fisher_rao_barycenter,
            PortfolioAllocator.compute_tamagawa_barycenter,
            PortfolioAllocator.compute_bloch_kato_barycenter,
            PortfolioAllocator.compute_tamagawa_bloch_kato_barycenter,
            PortfolioAllocator.compute_lurie_tamagawa_fisher_rao_barycenter,
            PortfolioAllocator.compute_lurie_tamagawa_bloch_kato_barycenter_blend,
            PortfolioAllocator.compute_tamagawa_fisher_rao_barycenter_blend,
        ]:
            res = alias_fn(w)
            for k in ["bl", "herc", "rp", "cvar"]:
                assert math.isclose(res[k], ref[k], rel_tol=1e-5)

    def test_feature_f153_1_trans_singular_eternal_omni_cosmic_evar_hierarchy(self, allocator):
        """Verify 29th-cumulant Trans-Singular-Eternal-Omni-Cosmic EVaR strictly bounds lower-order EVaRs."""
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)  # slightly negative mean with variance

        res_cosmic = allocator.compute_trans_singular_eternal_omni_cosmic_evar_risk_measure(returns, alpha=0.05)
        res_omni = allocator.compute_trans_singular_eternal_omni_evar_risk_measure(returns, alpha=0.05)

        assert res_cosmic["order"] == 29
        assert math.isclose(res_cosmic["xi_singular_eternal_omni_cosmic"], 0.9995, rel_tol=1e-5)
        # Trans-Singular-Eternal-Omni-Cosmic EVaR >= Trans-Singular-Eternal-Omni EVaR
        assert res_cosmic["trans_singular_eternal_omni_cosmic_evar_value"] >= res_omni["trans_singular_eternal_omni_evar_value"] - 1e-6

    def test_feature_f153_1_evar_aliases_and_portfolio_allocator(self, allocator):
        """Verify all Phase 33 EVaR aliases on UnifiedPortfolioAllocator and PortfolioAllocator."""
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)
        ref = allocator.compute_trans_singular_eternal_omni_cosmic_evar_risk_measure(returns)

        for alias_fn in [
            allocator.compute_trans_singular_eternal_omni_cosmic_evar,
            allocator.trans_singular_eternal_omni_cosmic_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_evar_blend,
            allocator.compute_singular_eternal_omni_cosmic_evar,
            allocator.singular_eternal_omni_cosmic_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_evar_phase33,
            allocator.compute_29th_cumulant_evar,
            allocator.compute_phase33_evar,
            allocator.compute_eternal_omni_cosmic_evar,
            allocator.compute_eternal_omni_cosmic_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_evar,
            PortfolioAllocator.trans_singular_eternal_omni_cosmic_evar_risk_measure,
            PortfolioAllocator.compute_singular_eternal_omni_cosmic_evar,
            PortfolioAllocator.compute_phase33_evar,
            PortfolioAllocator.compute_29th_cumulant_evar,
            PortfolioAllocator.compute_eternal_omni_cosmic_evar,
        ]:
            res = alias_fn(returns)
            assert math.isclose(res["trans_singular_eternal_omni_cosmic_evar_value"], ref["trans_singular_eternal_omni_cosmic_evar_value"], rel_tol=1e-5)

    def test_compute_regime_blended_portfolio_v33(self, allocator):
        """Verify end-to-end regime blending under version=33."""
        blended_v33 = allocator.compute_information_theoretic_blend_weights(version=33)
        blended_v32 = allocator.compute_information_theoretic_blend_weights(version=32)

        assert isinstance(blended_v33, dict)
        assert set(blended_v33.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended_v33.values()), 1.0, rel_tol=1e-5)

        # In v33, CVaR weight is further fortified (mu=3.15, delta_cvar=+9.50*eps_w)
        assert blended_v33["cvar"] > blended_v32["cvar"]
        assert blended_v33["cvar"] > 0.001

    def test_strict_backward_compatibility_v32_v31(self, allocator):
        """Verify backward compatibility for regime blending with version=32 and version=31."""
        blended_v32 = allocator.compute_information_theoretic_blend_weights(version=32)
        blended_v31 = allocator.compute_information_theoretic_blend_weights(version=31)

        assert math.isclose(sum(blended_v32.values()), 1.0, rel_tol=1e-5)
        assert math.isclose(sum(blended_v31.values()), 1.0, rel_tol=1e-5)
        assert blended_v32["cvar"] > blended_v31["cvar"] - 1e-6
