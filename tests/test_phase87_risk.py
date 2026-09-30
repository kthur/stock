r"""
tests/test_phase87_risk.py

Unit test suite for Phase 87 Quantitative Risk Allocation Enhancement (Feature F407):
- Feature F407.1: Higher-Homology-37 Motivic Fisher-Rao Barycenter Blending
  (mu = [7.70, 4.85, 2.50, 9.40], simplex sum=1.0, heavy-tail CVaR prioritization: CVaR > BL > HERC > RP)
- Feature F407.2: 106th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
  (106! ~= 1.146e170, xi_monster = 0.9999999999999999999999995, order=106)
- UnifiedPortfolioAllocator with default version=87 and dynamic regime shifts
- Strict backward compatibility with Phase 86, Phase 85, Phase 84, and earlier versions
- Class and module level alias trees verification for UnifiedPortfolioAllocator and PortfolioAllocator
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import (
    UnifiedPortfolioAllocator,
    compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_37_fisher_rao_barycenter_blend as module_barycenter_blend,
    compute_phase87_barycenter as module_phase87_barycenter,
    compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_37_evar_risk_measure as module_evar_risk_measure,
    compute_phase87_evar as module_phase87_evar,
)
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


def _extract_evar_val(res):
    if isinstance(res, dict):
        for key in res:
            if 'evar' in key.lower() and ('value' in key.lower() or key.lower().endswith('evar')):
                return float(res[key])
        return float(res.get("evar", 0.0))
    return float(res)


class TestPhase87RiskAllocation:
    """Test suite for Phase 87 Risk Allocation, Higher-Homology-37 Barycenter Blending, and 106th-Cumulant EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=87)

    @pytest.fixture
    def default_allocator(self):
        return UnifiedPortfolioAllocator()

    @pytest.fixture
    def portfolio_allocator(self):
        return PortfolioAllocator(version=87)

    def test_default_version_is_87(self, default_allocator):
        """Verify UnifiedPortfolioAllocator defaults to version=87 with is_phase87=True."""
        assert default_allocator.version == 87
        assert default_allocator.is_phase87 is True
        assert default_allocator.is_phase86 is True
        assert default_allocator.is_phase85 is True

    def test_feature_f407_1_barycenter_blend_basic_properties(self, allocator):
        """Verify Higher-Homology-37 Fisher-Rao barycenter converges on simplex with mu=[7.70, 4.85, 2.50, 9.40]."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_37_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 9.40, BL is second mu = 7.70, HERC is third mu = 4.85, RP is fourth mu = 2.50
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]
        for k, v in blended.items():
            assert 0.0 < v < 1.0

    def test_feature_f407_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_37_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_37_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_37_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f407_1_barycenter_aliases_and_delegation(self, allocator, portfolio_allocator):
        """Verify barycenter aliases work on UnifiedPortfolioAllocator, PortfolioAllocator, and module level."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_37_fisher_rao_barycenter_blend(w)
        assert isinstance(ref, dict)
        assert math.isclose(sum(ref.values()), 1.0, rel_tol=1e-5)

        # UnifiedPortfolioAllocator aliases
        assert allocator.compute_phase87_barycenter(w) == ref
        assert allocator.compute_phase87_fisher_rao_barycenter(w) == ref
        assert allocator.compute_higher_homology_37_barycenter(w) == ref
        assert allocator.higher_homology_37_blend(w) == ref
        assert allocator.compute_lmbmwdh37_fisher_rao_barycenter_blend(w) == ref
        assert allocator.phase87_barycenter_blend(w) == ref
        assert allocator.higher_homology_37_barycenter(w) == ref
        assert allocator.lmbmwdh37_barycenter(w) == ref

        # PortfolioAllocator delegation and aliases
        pa_res = portfolio_allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_37_fisher_rao_barycenter_blend(w)
        assert math.isclose(sum(pa_res.values()), 1.0, rel_tol=1e-5)
        assert pa_res == ref
        assert portfolio_allocator.compute_phase87_barycenter(w) == ref
        assert portfolio_allocator.compute_phase87_fisher_rao_barycenter(w) == ref
        assert portfolio_allocator.compute_phase87_barycenter_blend(w) == ref
        assert portfolio_allocator.higher_homology_37_barycenter(w) == ref
        assert portfolio_allocator.lmbmwdh37_barycenter(w) == ref

        # Module level
        assert module_barycenter_blend(w) == ref
        assert module_phase87_barycenter(w) == ref

    def test_feature_f407_2_evar_risk_measure(self, allocator, portfolio_allocator):
        """Verify 106th-Cumulant Expansion Trans-Singular EVaR Risk Measure."""
        returns = np.array([0.02, -0.015, 0.03, -0.025, 0.01, -0.005, 0.015, -0.01])
        res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_37_evar_risk_measure(returns=returns)

        assert isinstance(res, dict)
        assert "evar" in res
        assert res["order"] == 106
        assert res["xi_monster"] == 0.9999999999999999999999995
        assert "phase87_evar" in res
        assert math.isfinite(res["evar"])
        assert res["evar"] > 0

        # UnifiedPortfolioAllocator aliases
        ref_evar = res["evar"]
        assert math.isclose(_extract_evar_val(allocator.compute_phase87_evar(returns=returns)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(allocator.compute_evar_order106(returns=returns)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(allocator.compute_106th_cumulant_evar(returns=returns)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(allocator.higher_homology_37_evar(returns=returns)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(allocator.phase87_tail_risk_evar(returns=returns)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(allocator.phase87_evar_bound(returns=returns)), ref_evar, rel_tol=1e-5)

        # PortfolioAllocator aliases
        pa_evar = portfolio_allocator.compute_phase87_evar(returns=returns)
        assert math.isclose(_extract_evar_val(pa_evar), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(portfolio_allocator.compute_106th_cumulant_evar(returns=returns)), ref_evar, rel_tol=1e-5)

        # Module level
        assert math.isclose(_extract_evar_val(module_evar_risk_measure(returns=returns)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(module_phase87_evar(returns=returns)), ref_evar, rel_tol=1e-5)

    def test_backward_compatibility_v86_v85_v84(self, allocator):
        """Verify version=87 allocator retains backward compatibility for v86, v85, and v84 barycenters."""
        w = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        res86 = allocator.compute_phase86_barycenter(w)
        assert math.isclose(sum(res86.values()), 1.0, rel_tol=1e-5)
        res85 = allocator.compute_phase85_barycenter(w)
        assert math.isclose(sum(res85.values()), 1.0, rel_tol=1e-5)
        res84 = allocator.compute_phase84_barycenter(w)
        assert math.isclose(sum(res84.values()), 1.0, rel_tol=1e-5)
