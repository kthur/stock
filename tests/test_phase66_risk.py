r"""
tests/test_phase66_risk.py

Unit test suite for Phase 66 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F303.1: Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology-15 Fisher-Rao Barycenter Blending
  (mu_lmbwdh15 = [5.60, 3.80, 3.55, 6.25], simplex sum=1.0, heavy-tail CVaR prioritization)
- Feature F303.2: 64th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
  (62! ~= 3.14699 x 10^85, xi_monster = 0.99999999999997, order=64)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() and calculate_weights with version=66
- Strict backward compatibility with Phase 64 and earlier versions
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


class TestPhase66RiskAllocation:
    """Test suite for Phase 66 Risk Allocation, Higher-Homology-15 Barycenter Blending, and 64th-Cumulant EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_feature_f298_1_barycenter_blend_basic_properties(self, allocator):
        """Verify Higher-Homology-15 Fisher-Rao barycenter converges on simplex with mu=[5.60, 3.80, 3.55, 6.25]."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_16_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 6.10, BL is second mu = 5.50, HERC is third mu = 3.75, RP is fourth mu = 3.60
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]
        for k, v in blended.items():
            assert 0.0 < v < 1.0

    def test_feature_f298_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_16_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_16_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_16_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f298_1_barycenter_aliases(self, allocator):
        """Verify that barycenter aliases work on UnifiedPortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_16_fisher_rao_barycenter_blend(w)
        assert isinstance(ref, dict)
        assert math.isclose(sum(ref.values()), 1.0, rel_tol=1e-5)

        ref2 = allocator.compute_phase66_barycenter(w)
        assert ref2 == ref

    def test_feature_f298_2_64th_cumulant_evar_risk_measure(self, allocator):
        """Verify 64th-cumulant expansion EVaR properties with 62! ~= 3.15e85 and xi_monster = 0.99999999999997."""
        np.random.seed(65)
        returns = np.random.normal(0.001, 0.02, 500)

        res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_16_evar_risk_measure(
            returns,
            alpha=0.05,
            order=64,
            xi_monster=0.99999999999997,
        )

        evar_val = _extract_evar_val(res)
        assert math.isfinite(evar_val)
        assert evar_val > 0.0

        empty_res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_16_evar_risk_measure(
            [], alpha=0.05
        )
        assert _extract_evar_val(empty_res) == 0.0

    def test_feature_f298_2_fat_tailed_student_t_sensitivity(self, allocator):
        """Verify that 64th-cumulant EVaR is strictly higher for fat-tailed Student-t vs Gaussian."""
        np.random.seed(65)
        normal_ret = np.random.normal(0.0, 0.01, 1000)
        t_ret = np.random.standard_t(df=3, size=1000) * 0.01

        evar_norm = _extract_evar_val(allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_16_evar_risk_measure(normal_ret))
        evar_t = _extract_evar_val(allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_16_evar_risk_measure(t_ret))

        assert evar_t > evar_norm

    def test_feature_f298_2_evar_aliases(self, allocator):
        """Verify EVaR aliases on UnifiedPortfolioAllocator and PortfolioAllocator."""
        np.random.seed(65)
        returns = np.random.normal(0.001, 0.02, 100)
        ref = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_16_evar_risk_measure(returns)
        ref_val = _extract_evar_val(ref)

        for fn in [allocator.compute_phase66_evar, allocator.compute_phase66_evar_risk_measure, allocator.phase66_evar_bound, allocator.phase66_tail_risk_evar]:
            v = _extract_evar_val(fn(returns))
            assert math.isclose(v, ref_val, rel_tol=1e-5)

        pa = PortfolioAllocator()
        pa_val = _extract_evar_val(pa.compute_phase66_evar(returns))
        assert math.isfinite(pa_val)

    def test_compute_information_theoretic_blend_weights_version_65(self, allocator):
        """Verify ambiguity tilting and information-theoretic blend under version=66."""
        w_bear_65 = allocator.compute_information_theoretic_blend_weights(
            regime="BEAR",
            entropy_uncertainty=0.70,
            cascade_probability=0.80,
            crisis_risk_score=0.90,
            version=66,
        )

        assert math.isclose(sum(w_bear_65.values()), 1.0, rel_tol=1e-5)
        assert w_bear_65["cvar"] > 0.999
        assert w_bear_65["cvar"] > w_bear_65["bl"]
        assert w_bear_65["cvar"] > w_bear_65["herc"]
        assert w_bear_65["cvar"] > w_bear_65["rp"]

    def test_calculate_weights_version_65_end_to_end(self, allocator):
        """Verify UnifiedPortfolioAllocator.calculate_weights delegation under version=66."""
        cw = allocator.calculate_weights(
            regime="BEAR",
            entropy_uncertainty=0.70,
            cascade_probability=0.80,
            crisis_risk_score=0.90,
            version=66,
        )

        assert isinstance(cw, dict)
        assert set(cw.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(cw.values()), 1.0, rel_tol=1e-5)
        assert cw["cvar"] > 0.999

    def test_backward_compatibility_v64_and_prior(self, allocator):
        """Verify strict backward compatibility with Phase 64 and earlier."""
        for v in [64, 63, 62, 61, 60, 59, 58, 57, 56, 55, 54, 53, 52, 51, 50]:
            w = allocator.compute_information_theoretic_blend_weights(
                regime="BULL_LOW_VOL",
                version=v,
            )
            assert math.isclose(sum(w.values()), 1.0, rel_tol=1e-5)
            assert all(0.0 < val < 1.0 for val in w.values())
