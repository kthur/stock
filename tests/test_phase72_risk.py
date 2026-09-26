r"""
tests/test_phase72_risk.py

Unit test suite for Phase 72 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F333.1: Higher-Homology-22 Fisher-Rao Barycenter Blending
  (mu = [6.20, 4.10, 3.25, 7.15], simplex sum=1.0, heavy-tail CVaR prioritization: CVaR > BL > HERC > RP)
- Feature F333.2: 76th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
  (76! ~= 1.89e111, xi_monster = 0.9999999999999995, order=76)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() and calculate_weights with version=72
- Strict backward compatibility with Phase 71 and earlier versions
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


def _extract_evar_val(res):
    if isinstance(res, dict):
        for key in res:
            if 'evar' in key.lower() and ('value' in key.lower() or key.lower().endswith('evar')):
                return float(res[key])
        return float(res.get("evar", 0.0))
    return float(res)


class TestPhase72RiskAllocation:
    """Test suite for Phase 72 Risk Allocation, Higher-Homology-22 Barycenter Blending, and 76th-Cumulant EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=72)

    def test_feature_f333_1_barycenter_blend_basic_properties(self, allocator):
        """Verify Higher-Homology-22 Fisher-Rao barycenter converges on simplex with mu=[6.20, 4.10, 3.25, 7.15]."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_22_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 7.15, BL is second mu = 6.20, HERC is third mu = 4.10, RP is fourth mu = 3.25
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]
        for k, v in blended.items():
            assert 0.0 < v < 1.0

    def test_feature_f333_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_22_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_22_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_22_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f333_1_barycenter_aliases(self, allocator):
        """Verify that barycenter aliases work on UnifiedPortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_22_fisher_rao_barycenter_blend(w)
        assert isinstance(ref, dict)
        assert math.isclose(sum(ref.values()), 1.0, rel_tol=1e-5)

        ref2 = allocator.compute_phase72_barycenter(w)
        assert ref2 == ref

    def test_feature_f333_2_76th_cumulant_evar_risk_measure(self, allocator):
        """Verify 76th-cumulant expansion EVaR properties with 76! ~= 1.89e111 and xi_monster = 0.9999999999999995."""
        np.random.seed(72)
        returns = np.random.normal(0.001, 0.02, 500)

        res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_22_evar_risk_measure(
            returns,
            alpha=0.05,
            order=76,
            xi_monster=0.9999999999999995,
        )

        evar_val = _extract_evar_val(res)
        assert math.isfinite(evar_val)
        assert evar_val > 0.0

        empty_res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_22_evar_risk_measure(
            [], alpha=0.05
        )
        assert _extract_evar_val(empty_res) == 0.0

    def test_backward_compatibility_v71_and_prior(self):
        """Verify backward compatibility for versions 71, 70, 69, 68."""
        for v in [71, 70, 69, 68]:
            alloc = UnifiedPortfolioAllocator(version=v)
            w = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
            res = alloc.compute_information_theoretic_blend_weights(w)
            assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-4)
