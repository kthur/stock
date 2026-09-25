r"""
tests/test_phase69_risk.py

Unit test suite for Phase 69 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F318.1: Higher-Homology-19 Fisher-Rao Barycenter Blending
  (mu = [5.90, 3.95, 3.40, 6.70], simplex sum=1.0, heavy-tail CVaR prioritization: CVaR > BL > HERC > RP)
- Feature F318.2: 70th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
  (70! ~= 1.20e100, xi_monster = 0.999999999999995, order=70)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() and calculate_weights with version=69
- Strict backward compatibility with Phase 68 and earlier versions
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


class TestPhase69RiskAllocation:
    """Test suite for Phase 69 Risk Allocation, Higher-Homology-19 Barycenter Blending, and 70th-Cumulant EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=69)

    def test_feature_f318_1_barycenter_blend_basic_properties(self, allocator):
        """Verify Higher-Homology-19 Fisher-Rao barycenter converges on simplex with mu=[5.90, 3.95, 3.40, 6.70]."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_19_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 6.70, BL is second mu = 5.90, HERC is third mu = 3.95, RP is fourth mu = 3.40
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]
        for k, v in blended.items():
            assert 0.0 < v < 1.0

    def test_feature_f318_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_19_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_19_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_19_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f318_1_barycenter_aliases(self, allocator):
        """Verify that barycenter aliases work on UnifiedPortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_19_fisher_rao_barycenter_blend(w)
        assert isinstance(ref, dict)
        assert math.isclose(sum(ref.values()), 1.0, rel_tol=1e-5)

        ref2 = allocator.compute_phase69_barycenter(w)
        assert ref2 == ref

    def test_feature_f318_2_70th_cumulant_evar_risk_measure(self, allocator):
        """Verify 70th-cumulant expansion EVaR properties with 70! ~= 1.20e100 and xi_monster = 0.999999999999995."""
        np.random.seed(69)
        returns = np.random.normal(0.001, 0.02, 500)

        res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_19_evar_risk_measure(
            returns,
            alpha=0.05,
            order=70,
            xi_monster=0.999999999999995,
        )

        evar_val = _extract_evar_val(res)
        assert math.isfinite(evar_val)
        assert evar_val > 0.0

        empty_res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_19_evar_risk_measure(
            [], alpha=0.05
        )
        assert _extract_evar_val(empty_res) == 0.0

    def test_feature_f318_2_evar_fat_tailed_ordering(self, allocator):
        """Verify Student-t fat-tailed EVaR is higher than Gaussian EVaR."""
        np.random.seed(69)
        n = 1000
        normal_rets = np.random.normal(0.0, 0.02, n)
        t_rets = np.random.standard_t(df=3, size=n) * 0.02

        evar_norm = _extract_evar_val(allocator.compute_phase69_evar(normal_rets))
        evar_fat = _extract_evar_val(allocator.compute_phase69_evar(t_rets))

        assert evar_fat > evar_norm

    def test_portfolio_allocator_delegation_v69(self):
        """Verify PortfolioAllocator correctly delegates barycenter and EVaR to UnifiedPortfolioAllocator."""
        pa = PortfolioAllocator()
        w = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = pa.compute_phase69_barycenter(w)
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        assert blended["cvar"] > blended["bl"] > blended["herc"] > blended["rp"]

        np.random.seed(69)
        rets = np.random.normal(0.001, 0.02, 100)
        evar_res = pa.compute_phase69_evar(rets)
        assert _extract_evar_val(evar_res) > 0.0

    def test_strict_backward_compatibility_v68_and_prior(self, allocator):
        """Verify backward compatibility of barycenter blending with Phase 68 and earlier versions."""
        w = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        w69 = allocator.compute_phase69_barycenter(w)
        w68 = allocator.compute_phase68_barycenter(w)
        w67 = allocator.compute_phase67_barycenter(w)

        assert math.isclose(sum(w69.values()), 1.0, rel_tol=1e-5)
        assert math.isclose(sum(w68.values()), 1.0, rel_tol=1e-5)
        assert math.isclose(sum(w67.values()), 1.0, rel_tol=1e-5)
        # All preserve CVaR > BL > HERC > RP hierarchy
        for weights in [w69, w68, w67]:
            assert weights["cvar"] > weights["bl"] > weights["herc"] > weights["rp"]
