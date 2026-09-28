r"""
tests/test_phase79_risk.py

Unit test suite for Phase 79 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F368.1: Higher-Homology-29 Motivic Fisher-Rao Barycenter Blending
  (mu = [6.90, 4.45, 2.90, 8.20], simplex sum=1.0, heavy-tail CVaR prioritization: CVaR > BL > HERC > RP)
- Feature F368.2: 90th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
  (90! ~= 1.486e138, xi_monster = 0.999999999999999998, order=90)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() and calculate_weights with version=79
- Strict backward compatibility with Phase 78 and earlier versions
- Class and module level alias trees verification for UnifiedPortfolioAllocator and PortfolioAllocator
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import (
    UnifiedPortfolioAllocator,
    compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_29_fisher_rao_barycenter_blend as module_barycenter_blend,
    compute_phase79_barycenter as module_phase79_barycenter,
    compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_29_evar_risk_measure as module_evar_risk_measure,
    compute_phase79_evar as module_phase79_evar,
)
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


def _extract_evar_val(res):
    if isinstance(res, dict):
        for key in res:
            if 'evar' in key.lower() and ('value' in key.lower() or key.lower().endswith('evar')):
                return float(res[key])
        return float(res.get("evar", 0.0))
    return float(res)


class TestPhase79RiskAllocation:
    """Test suite for Phase 79 Risk Allocation, Higher-Homology-29 Barycenter Blending, and 90th-Cumulant EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=79)

    @pytest.fixture
    def portfolio_allocator(self):
        return PortfolioAllocator(version=79)

    def test_feature_f368_1_barycenter_blend_basic_properties(self, allocator):
        """Verify Higher-Homology-29 Fisher-Rao barycenter converges on simplex with mu=[6.90, 4.45, 2.90, 8.20]."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_29_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 8.20, BL is second mu = 6.90, HERC is third mu = 4.45, RP is fourth mu = 2.90
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]
        for k, v in blended.items():
            assert 0.0 < v < 1.0

    def test_feature_f368_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_29_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_29_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_29_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f368_1_barycenter_aliases_and_delegation(self, allocator, portfolio_allocator):
        """Verify barycenter aliases work on UnifiedPortfolioAllocator, PortfolioAllocator, and module level."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_29_fisher_rao_barycenter_blend(w)
        assert isinstance(ref, dict)
        assert math.isclose(sum(ref.values()), 1.0, rel_tol=1e-5)

        # UnifiedPortfolioAllocator aliases
        assert allocator.compute_phase79_barycenter(w) == ref
        assert allocator.compute_phase79_fisher_rao_barycenter(w) == ref
        assert allocator.compute_higher_homology_29_barycenter(w) == ref
        assert allocator.higher_homology_29_blend(w) == ref
        assert allocator.compute_lmbmwdh29_fisher_rao_barycenter_blend(w) == ref
        assert allocator.borcherds_higher_homology_29_barycenter(w) == ref

        # PortfolioAllocator delegation and aliases
        pa_res = portfolio_allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_29_fisher_rao_barycenter_blend(w)
        assert math.isclose(sum(pa_res.values()), 1.0, rel_tol=1e-5)
        assert pa_res == ref
        assert portfolio_allocator.compute_phase79_barycenter(w) == ref
        assert portfolio_allocator.compute_phase79_fisher_rao_barycenter(w) == ref

    def test_feature_f368_2_90th_cumulant_evar_computation(self, allocator, portfolio_allocator):
        """Verify 90th-cumulant expansion trans-singular EVaR computation."""
        np.random.seed(42)
        returns = np.random.normal(-0.005, 0.02, 200)

        evar_dict = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_29_evar_risk_measure(
            returns=returns, alpha=0.05
        )
        assert isinstance(evar_dict, dict)
        assert "order" in evar_dict
        assert evar_dict["order"] == 90
        assert "xi_monster" in evar_dict
        assert math.isclose(evar_dict["xi_monster"], 0.999999999999999998, rel_tol=1e-15)

        val = _extract_evar_val(evar_dict)
        assert val > 0.0
        assert math.isfinite(val)

        # PortfolioAllocator delegation
        pa_evar = portfolio_allocator.compute_phase79_evar(returns=returns, alpha=0.05)
        val_pa = _extract_evar_val(pa_evar)
        assert math.isclose(val, val_pa, rel_tol=1e-5)

    def test_feature_f368_backward_compatibility_v78_and_prior(self):
        """Verify strict backward compatibility with Phase 78 and earlier versions."""
        w = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}

        alloc_v78 = UnifiedPortfolioAllocator(version=78)
        assert alloc_v78.is_phase78 is True
        assert alloc_v78.is_phase79 is False
        b_78 = alloc_v78.compute_phase78_barycenter(w)
        assert math.isclose(sum(b_78.values()), 1.0, rel_tol=1e-5)

        alloc_v77 = UnifiedPortfolioAllocator(version=77)
        assert alloc_v77.is_phase77 is True
        assert alloc_v77.is_phase78 is False
        assert alloc_v77.is_phase79 is False
        b_77 = alloc_v77.compute_phase77_barycenter(w)
        assert math.isclose(sum(b_77.values()), 1.0, rel_tol=1e-5)
