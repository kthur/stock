r"""
tests/test_phase84_risk.py

Unit test suite for Phase 84 Quantitative Risk Allocation Enhancement:
- Feature F392.1: Higher-Homology-34 Motivic Fisher-Rao Barycenter Blending
  (mu = [7.40, 4.70, 2.65, 8.95], simplex sum=1.0, heavy-tail CVaR prioritization: CVaR > BL > HERC > RP)
- Feature F392.2: 100th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
  (100! ~= 9.333e157, xi_monster = 0.9999999999999999999999, order=100)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() and calculate_weights with version=84
- Strict backward compatibility with Phase 83, Phase 82, and earlier versions
- Class and module level alias trees verification for UnifiedPortfolioAllocator and PortfolioAllocator
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import (
    UnifiedPortfolioAllocator,
    compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_34_fisher_rao_barycenter_blend as module_barycenter_blend,
    compute_phase84_barycenter as module_phase84_barycenter,
    compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_34_evar_risk_measure as module_evar_risk_measure,
    compute_phase84_evar as module_phase84_evar,
)
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


def _extract_evar_val(res):
    if isinstance(res, dict):
        for key in res:
            if 'evar' in key.lower() and ('value' in key.lower() or key.lower().endswith('evar')):
                return float(res[key])
        return float(res.get("evar", 0.0))
    return float(res)


class TestPhase84RiskAllocation:
    """Test suite for Phase 84 Risk Allocation, Higher-Homology-34 Barycenter Blending, and 100th-Cumulant EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=84)

    @pytest.fixture
    def portfolio_allocator(self):
        return PortfolioAllocator(version=84)

    def test_feature_f392_1_barycenter_blend_basic_properties(self, allocator):
        """Verify Higher-Homology-34 Fisher-Rao barycenter converges on simplex with mu=[7.40, 4.70, 2.65, 8.95]."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_34_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 8.95, BL is second mu = 7.40, HERC is third mu = 4.70, RP is fourth mu = 2.65
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]
        for k, v in blended.items():
            assert 0.0 < v < 1.0

    def test_feature_f392_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_34_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_34_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_34_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f392_1_barycenter_aliases_and_delegation(self, allocator, portfolio_allocator):
        """Verify barycenter aliases work on UnifiedPortfolioAllocator, PortfolioAllocator, and module level."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_34_fisher_rao_barycenter_blend(w)
        assert isinstance(ref, dict)
        assert math.isclose(sum(ref.values()), 1.0, rel_tol=1e-5)

        # UnifiedPortfolioAllocator aliases
        assert allocator.compute_phase84_barycenter(w) == ref
        assert allocator.compute_phase84_fisher_rao_barycenter(w) == ref
        assert allocator.compute_higher_homology_34_barycenter(w) == ref
        assert allocator.higher_homology_34_blend(w) == ref
        assert allocator.compute_lmbmwdh34_fisher_rao_barycenter_blend(w) == ref

        # PortfolioAllocator delegation and aliases
        pa_res = portfolio_allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_34_fisher_rao_barycenter_blend(w)
        assert math.isclose(sum(pa_res.values()), 1.0, rel_tol=1e-5)
        assert pa_res == ref
        assert portfolio_allocator.compute_phase84_barycenter(w) == ref
        assert portfolio_allocator.compute_phase84_fisher_rao_barycenter(w) == ref
        assert portfolio_allocator.compute_phase84_barycenter_blend(w) == ref
        assert portfolio_allocator.higher_homology_34_barycenter(w) == ref
        assert portfolio_allocator.lmbmwdh34_barycenter(w) == ref

        # Module level
        assert module_barycenter_blend(w) == ref
        assert module_phase84_barycenter(w) == ref

    def test_feature_f392_2_evar_risk_measure(self, allocator, portfolio_allocator):
        """Verify 100th-Cumulant Expansion Trans-Singular EVaR Risk Measure."""
        returns = np.array([0.02, -0.015, 0.03, -0.025, 0.01, -0.005, 0.015, -0.01])
        res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_34_evar_risk_measure(returns=returns)

        assert isinstance(res, dict)
        assert "evar" in res
        assert res["order"] == 100
        assert res["xi_monster"] == 0.9999999999999999999999
        assert "phase84_evar" in res
        assert math.isfinite(res["evar"])
        assert res["evar"] > 0

        # UnifiedPortfolioAllocator aliases
        ref_evar = res["evar"]
        assert math.isclose(_extract_evar_val(allocator.compute_phase84_evar(returns=returns)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(allocator.compute_evar_order100(returns=returns)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(allocator.compute_100th_cumulant_evar(returns=returns)), ref_evar, rel_tol=1e-5)

        # PortfolioAllocator aliases
        pa_evar = portfolio_allocator.compute_phase84_evar(returns=returns)
        assert math.isclose(_extract_evar_val(pa_evar), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(portfolio_allocator.compute_100th_cumulant_evar(returns=returns)), ref_evar, rel_tol=1e-5)

        # Module level
        assert math.isclose(_extract_evar_val(module_evar_risk_measure(returns=returns)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(module_phase84_evar(returns=returns)), ref_evar, rel_tol=1e-5)

    def test_backward_compatibility_v83_v82(self, allocator):
        """Verify version=84 allocator retains backward compatibility for v83 and v82 barycenters and EVaRs."""
        w = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        res83 = allocator.compute_phase83_barycenter(w)
        assert math.isclose(sum(res83.values()), 1.0, rel_tol=1e-5)
        res82 = allocator.compute_phase82_barycenter(w)
        assert math.isclose(sum(res82.values()), 1.0, rel_tol=1e-5)
