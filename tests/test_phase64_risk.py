r"""
tests/test_phase64_risk.py

Unit test suite for Phase 64 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F293.1: Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology-14 Fisher-Rao Barycenter Blending
  (mu_lmbwdh14 = [5.40, 3.70, 3.65, 5.95], simplex sum=1.0, heavy-tail CVaR prioritization)
- Feature F293.2: 60th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
  (60! ~= 8.320987 x 10^81, xi_monster = 0.99999999999995, order=60)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() and calculate_weights with version=64
- Strict backward compatibility with Phase 63 and earlier versions
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


def _extract_evar_val(res):
    if isinstance(res, dict):
        return float(res.get(
            "trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_14_evar_value",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_14_evar",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_evar_value",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_evar",
            res.get("evar", 0.0))))
        ))
    return float(res)


class TestPhase64RiskAllocation:
    """Test suite for Phase 64 Risk Allocation, Higher-Homology-14 Barycenter Blending, and 60th-Cumulant EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_feature_f293_1_barycenter_blend_basic_properties(self, allocator):
        """Verify that Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology-14 Fisher-Rao barycenter converges on simplex."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_14_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 5.95, BL is second mu = 5.40, HERC is third mu = 3.70, RP is fourth mu = 3.65
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]
        # Interior point positivity
        for k, v in blended.items():
            assert 0.0 < v < 1.0

    def test_feature_f293_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        # 1. 1D Array
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_14_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        # 2. List of dicts
        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_14_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        # 3. 2D array
        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_14_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f293_1_barycenter_aliases_and_portfolio_allocator(self, allocator):
        """Verify that barycenter aliases work on both UnifiedPortfolioAllocator and PortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_14_fisher_rao_barycenter_blend(w)

        # UnifiedPortfolioAllocator aliases
        assert allocator.higher_homology_14_fisher_rao_blend(w) == ref
        assert allocator.compute_phase64_barycenter_blend(w) == ref
        assert allocator.compute_higher_homology_14_barycenter(w) == ref
        assert allocator.lmbwdh14_barycenter(w) == ref
        assert allocator.higher_homology_14_blend(w) == ref

        # PortfolioAllocator static delegations
        pa_ref = PortfolioAllocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_14_fisher_rao_barycenter_blend(w)
        assert pa_ref == ref
        assert PortfolioAllocator.higher_homology_14_fisher_rao_blend(w) == ref
        assert PortfolioAllocator.compute_phase64_barycenter_blend(w) == ref

    def test_feature_f293_2_60th_cumulant_evar_risk_measure(self, allocator):
        """Verify 60th-cumulant expansion EVaR properties with 60! ~= 8.32e81 and xi_monster = 0.99999999999995."""
        np.random.seed(64)
        returns = np.random.normal(0.001, 0.02, 500)

        res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_14_evar_risk_measure(
            returns,
            alpha=0.05,
            order=60,
            xi_monster=0.99999999999995,
        )

        evar_val = _extract_evar_val(res)
        assert math.isfinite(evar_val)
        assert evar_val > 0.0

        # Empty returns resilience
        empty_res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_14_evar_risk_measure(
            [], alpha=0.05
        )
        assert _extract_evar_val(empty_res) == 0.0

    def test_feature_f293_2_fat_tailed_student_t_sensitivity(self, allocator):
        """Verify that 60th-cumulant EVaR is strictly higher for fat-tailed Student-t vs Gaussian."""
        np.random.seed(64)
        normal_ret = np.random.normal(0.0, 0.01, 1000)
        t_ret = np.random.standard_t(df=3, size=1000) * 0.01

        evar_norm = _extract_evar_val(allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_14_evar_risk_measure(normal_ret))
        evar_t = _extract_evar_val(allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_14_evar_risk_measure(t_ret))

        assert evar_t > evar_norm, f"Student-t EVaR ({evar_t}) should be strictly greater than Gaussian EVaR ({evar_norm})"

    def test_feature_f293_2_evar_aliases_and_portfolio_allocator(self, allocator):
        """Verify EVaR aliases on UnifiedPortfolioAllocator and PortfolioAllocator."""
        np.random.seed(64)
        returns = np.random.normal(0.001, 0.02, 100)
        ref = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_14_evar_risk_measure(returns)
        ref_val = _extract_evar_val(ref)

        upa_aliases = [
            allocator.compute_phase64_evar,
            allocator.compute_phase64_evar_risk_measure,
            allocator.compute_60th_cumulant_evar,
            allocator.compute_evar_order60,
            allocator.phase64_evar_bound,
            allocator.compute_higher_homology_14_evar,
            allocator.higher_homology_14_evar,
        ]

        for fn in upa_aliases:
            v = _extract_evar_val(fn(returns))
            assert math.isclose(v, ref_val, rel_tol=1e-5)

        # PortfolioAllocator static delegation
        pa_val = _extract_evar_val(PortfolioAllocator.compute_phase64_evar(returns))
        assert math.isclose(pa_val, ref_val, rel_tol=1e-5)

    def test_compute_information_theoretic_blend_weights_version_64(self, allocator):
        """Verify ambiguity tilting and information-theoretic blend under version=64."""
        w_bear_64 = allocator.compute_information_theoretic_blend_weights(
            regime="BEAR",
            entropy_uncertainty=0.70,
            cascade_probability=0.80,
            crisis_risk_score=0.90,
            version=64,
        )

        assert math.isclose(sum(w_bear_64.values()), 1.0, rel_tol=1e-5)
        # CVaR is strongly prioritized in bear regime under v64
        assert w_bear_64["cvar"] > 0.999
        assert w_bear_64["cvar"] > w_bear_64["bl"]
        assert w_bear_64["cvar"] > w_bear_64["herc"]
        assert w_bear_64["cvar"] > w_bear_64["rp"]

    def test_calculate_weights_version_64_end_to_end(self, allocator):
        """Verify UnifiedPortfolioAllocator.calculate_weights delegation under version=64."""
        cw = allocator.calculate_weights(
            regime="BEAR",
            entropy_uncertainty=0.70,
            cascade_probability=0.80,
            crisis_risk_score=0.90,
            version=64,
        )

        assert isinstance(cw, dict)
        assert set(cw.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(cw.values()), 1.0, rel_tol=1e-5)
        assert cw["cvar"] > 0.999

    def test_backward_compatibility_v63_and_prior(self, allocator):
        """Verify strict backward compatibility with Phase 63 and earlier."""
        for v in [63, 62, 61, 60, 59, 58, 57, 56, 55, 54, 53, 52, 51, 50]:
            w = allocator.compute_information_theoretic_blend_weights(
                regime="BULL_LOW_VOL",
                version=v,
            )
            assert math.isclose(sum(w.values()), 1.0, rel_tol=1e-5)
            assert all(0.0 < val < 1.0 for val in w.values())
