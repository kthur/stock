r"""
tests/test_phase63_risk.py

Unit test suite for Phase 63 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F288.1: Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology-13 Fisher-Rao Barycenter Blending
  (mu_lmbwdh13 = [5.30, 3.65, 3.60, 5.85], simplex sum=1.0, heavy-tail CVaR prioritization)
- Feature F288.2: 59th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
  (59! ~= 1.386831185 x 10^80, xi_monster = 0.9999999999999, order=59)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() and calculate_weights with version=63
- Strict backward compatibility with Phase 62 and earlier versions
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
            "trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_evar_value",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_evar",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_evar_value",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_evar",
            res.get("evar", 0.0))))
        ))
    return float(res)


class TestPhase63RiskAllocation:
    """Test suite for Phase 63 Risk Allocation, Higher-Homology-13 Barycenter Blending, and 59th-Cumulant EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_feature_f288_1_barycenter_blend_basic_properties(self, allocator):
        """Verify that Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology-13 Fisher-Rao barycenter converges on simplex."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_13_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 5.85, BL is second mu = 5.30, HERC is third mu = 3.65, RP is fourth mu = 3.60
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]
        # Interior point positivity
        for k, v in blended.items():
            assert 0.0 < v < 1.0

    def test_feature_f288_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        # 1. 1D Array
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_13_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        # 2. List of dicts
        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_13_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        # 3. 2D array
        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_13_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f288_1_barycenter_aliases_and_portfolio_allocator(self, allocator):
        """Verify that all barycenter aliases work on both UnifiedPortfolioAllocator and PortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_13_fisher_rao_barycenter_blend(w)

        upa_aliases = [
            allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_13_barycenter,
            allocator.compute_lurie_drinfeld_higher_homology_13_barycenter,
            allocator.compute_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_13_fisher_rao_barycenter,
            allocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_barycenter,
            allocator.compute_drinfeld_higher_homology_13_barycenter,
            allocator.compute_phase63_fisher_rao_barycenter,
            allocator.compute_phase63_barycenter_blend,
            allocator.compute_higher_homology_13_barycenter,
            allocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_fisher_rao_barycenter_blend,
            allocator.compute_motivic_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_barycenter_blend,
            allocator.compute_analytic_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_barycenter_blend,
            allocator.compute_chiral_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_barycenter_blend,
            allocator.compute_quantum_langlands_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_barycenter_blend,
            allocator.compute_chiral_oper_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_barycenter_blend,
            allocator.compute_lurie_quantum_langlands_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_barycenter,
            allocator.compute_lmbmwdh13_barycenter,
            allocator.compute_lmbmwdh13_fisher_rao_barycenter,
            allocator.compute_fisher_rao_barycenter_lmbwdh13,
            allocator.compute_phase63_barycenter,
            allocator.lmbwdh13_barycenter,
            allocator.higher_homology_13_fisher_rao_blend,
            allocator.phase63_fisher_rao_barycenter,
            allocator.compute_phase63_barycenter_blend,
            allocator.higher_homology_13_blend,
            allocator.phase63_homology_barycenter,
        ]

        for fn in upa_aliases:
            res = fn(w)
            for k in ["bl", "herc", "rp", "cvar"]:
                assert math.isclose(res[k], ref[k], rel_tol=1e-5)

        # Static and class delegations on PortfolioAllocator
        pa_ref = PortfolioAllocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_13_fisher_rao_barycenter_blend(w)
        for k in ["bl", "herc", "rp", "cvar"]:
            assert math.isclose(pa_ref[k], ref[k], rel_tol=1e-5)

        pa_inst = PortfolioAllocator()
        assert hasattr(pa_inst, "compute_phase63_fisher_rao_barycenter")
        assert hasattr(pa_inst, "compute_higher_homology_13_barycenter")
        assert hasattr(pa_inst, "lmbwdh13_barycenter")

    def test_feature_f288_2_59th_cumulant_evar_risk_measure(self, allocator):
        """Verify 59th-cumulant expansion EVaR risk measure calculation."""
        np.random.seed(63)
        returns = np.random.normal(0.001, 0.02, 500)

        res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_evar_risk_measure(
            returns,
            alpha=0.05,
            order=59,
            xi_monster=0.9999999999999,
        )

        evar_val = _extract_evar_val(res)
        assert math.isfinite(evar_val)
        assert evar_val > 0.0

        # Empty returns resilience
        empty_res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_evar_risk_measure(
            [], alpha=0.05
        )
        assert _extract_evar_val(empty_res) == 0.0

    def test_feature_f288_2_evar_aliases(self, allocator):
        """Verify aliases for 59th-cumulant EVaR on UnifiedPortfolioAllocator and PortfolioAllocator."""
        np.random.seed(63)
        returns = np.random.normal(0.001, 0.02, 100)

        ref_dict = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_evar_risk_measure(returns)
        ref_val = _extract_evar_val(ref_dict)

        upa_aliases = [
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_evar,
            allocator.compute_higher_homology_13_evar,
            allocator.compute_phase63_evar,
            allocator.compute_phase63_evar_risk_measure,
            allocator.compute_59th_cumulant_evar,
            allocator.compute_evar_order59,
            allocator.higher_homology_13_evar,
            allocator.phase63_evar_bound,
            allocator.compute_lmbmwdh13_evar,
            allocator.lmbmwdh13_evar,
        ]

        for fn in upa_aliases:
            v = _extract_evar_val(fn(returns))
            assert math.isclose(v, ref_val, rel_tol=1e-5)

        # PortfolioAllocator static delegation
        pa_val = _extract_evar_val(
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_evar_risk_measure(returns)
        )
        assert math.isclose(pa_val, ref_val, rel_tol=1e-5)

    def test_information_theoretic_blend_weights_version_63(self, allocator):
        """Verify version=63 ambiguity tilting and higher homology 13 post-softmax barycenter."""
        w_bear_63 = allocator.compute_information_theoretic_blend_weights(
            regime="BEAR",
            entropy_uncertainty=0.70,
            cascade_probability=0.80,
            crisis_risk_score=0.90,
            version=63,
        )

        assert math.isclose(sum(w_bear_63.values()), 1.0, rel_tol=1e-5)
        # CVaR is strongly prioritized in bear regime under v63
        assert w_bear_63["cvar"] > 0.999
        assert w_bear_63["cvar"] > w_bear_63["bl"]
        assert w_bear_63["cvar"] > w_bear_63["herc"]
        assert w_bear_63["cvar"] > w_bear_63["rp"]

        # calculate_weights delegation
        cw = allocator.calculate_weights(
            regime="BEAR",
            entropy_uncertainty=0.70,
            cascade_probability=0.80,
            crisis_risk_score=0.90,
            version=63,
        )
        for k in ["bl", "herc", "rp", "cvar"]:
            assert math.isclose(cw[k], w_bear_63[k], rel_tol=1e-5)

    def test_strict_backward_compatibility_v62_and_earlier(self, allocator):
        """Verify backward compatibility across versions 50~62."""
        for v in [62, 61, 60, 59, 58, 57, 56, 55, 54, 53, 52, 51, 50]:
            w = allocator.compute_information_theoretic_blend_weights(
                regime="BULL_LOW_VOL",
                version=v,
            )
            assert math.isclose(sum(w.values()), 1.0, rel_tol=1e-5)
            assert all(0.0 < val < 1.0 for val in w.values())

    def test_feature_f288_2_fat_tailed_student_t_sensitivity(self, allocator):
        """Verify that 59th-cumulant EVaR is strictly higher for fat-tailed Student-t vs Gaussian."""
        np.random.seed(63)
        normal_ret = np.random.normal(0.0, 0.01, 1000)
        t_ret = np.random.standard_t(df=3, size=1000) * 0.01

        evar_norm = _extract_evar_val(allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_evar_risk_measure(normal_ret))
        evar_t = _extract_evar_val(allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_13_evar_risk_measure(t_ret))

        assert evar_t > evar_norm, f"Student-t EVaR ({evar_t}) should be strictly greater than Gaussian EVaR ({evar_norm})"
