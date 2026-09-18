r"""
tests/test_phase53_risk.py

Unit test suite for Phase 53 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F238.1: Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology-3 Fisher-Rao Barycenter Blending
  (mu_lmbwdh3 = [4.30, 3.15, 3.10, 4.85], simplex sum=1.0, heavy-tail CVaR prioritization)
- Feature F238.2: 49th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
  (49! ~= 6.08282 x 10^62, xi_monster = 0.9999999995, order=49)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() and calculate_weights with version=53
- Strict backward compatibility with Phase 52 and earlier versions
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
            "trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_value",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_evar_value",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_evar",
            res.get("evar", 0.0))))
        ))
    return float(res)


class TestPhase53RiskAllocation:
    """Test suite for Phase 53 Risk Allocation and Barycenter Blending."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_feature_f238_1_barycenter_blend_basic_properties(self, allocator):
        """Verify that Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology-3 Fisher-Rao barycenter converges on simplex."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_3_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 4.85, BL is second mu = 4.30, HERC is third mu = 3.15, RP is fourth mu = 3.10
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]
        # Interior point positivity
        for k, v in blended.items():
            assert 0.0 < v < 1.0

    def test_feature_f238_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        # 1. 1D Array
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_3_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        # 2. List of dicts
        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_3_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        # 3. 2D array
        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_3_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f238_1_barycenter_aliases_and_portfolio_allocator(self, allocator):
        """Verify that all 18 barycenter aliases work on both UnifiedPortfolioAllocator and PortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_3_fisher_rao_barycenter_blend(w)

        # 18 aliases on UnifiedPortfolioAllocator
        upa_aliases = [
            allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_3_barycenter,
            allocator.compute_lurie_drinfeld_higher_homology_3_barycenter,
            allocator.compute_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_3_fisher_rao_barycenter,
            allocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_barycenter,
            allocator.compute_drinfeld_higher_homology_3_barycenter,
            allocator.compute_phase53_fisher_rao_barycenter,
            allocator.compute_phase53_barycenter_blend,
            allocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_fisher_rao_barycenter_blend,
            allocator.compute_motivic_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_barycenter_blend,
            allocator.compute_analytic_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_barycenter_blend,
            allocator.compute_chiral_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_barycenter_blend,
            allocator.compute_quantum_langlands_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_barycenter_blend,
            allocator.compute_chiral_oper_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_barycenter_blend,
            allocator.compute_lurie_quantum_langlands_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_barycenter,
            allocator.compute_lmbmwdh3_barycenter,
            allocator.compute_lmbmwdh3_fisher_rao_barycenter,
            allocator.compute_lmmwdh3_barycenter,
            allocator.compute_lmmwdh3_fisher_rao_barycenter,
        ]
        assert len(upa_aliases) == 18

        for a_fn in upa_aliases:
            res = a_fn(w)
            for k in w:
                assert math.isclose(res[k], ref[k], rel_tol=1e-5)

        # 18 staticmethod delegations on PortfolioAllocator
        pa_aliases = [
            PortfolioAllocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_3_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_3_barycenter,
            PortfolioAllocator.compute_lurie_drinfeld_higher_homology_3_barycenter,
            PortfolioAllocator.compute_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_3_fisher_rao_barycenter,
            PortfolioAllocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_barycenter,
            PortfolioAllocator.compute_drinfeld_higher_homology_3_barycenter,
            PortfolioAllocator.compute_phase53_fisher_rao_barycenter,
            PortfolioAllocator.compute_phase53_barycenter_blend,
            PortfolioAllocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_motivic_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_barycenter_blend,
            PortfolioAllocator.compute_analytic_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_barycenter_blend,
            PortfolioAllocator.compute_chiral_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_barycenter_blend,
            PortfolioAllocator.compute_quantum_langlands_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_barycenter_blend,
            PortfolioAllocator.compute_chiral_oper_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_barycenter_blend,
            PortfolioAllocator.compute_lurie_quantum_langlands_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_barycenter,
            PortfolioAllocator.compute_lmbmwdh3_barycenter,
            PortfolioAllocator.compute_lmbmwdh3_fisher_rao_barycenter,
            PortfolioAllocator.compute_lmmwdh3_barycenter,
            PortfolioAllocator.compute_lmmwdh3_fisher_rao_barycenter,
        ]
        assert len(pa_aliases) == 19

        for a_fn in pa_aliases:
            res = a_fn(w)
            for k in w:
                assert math.isclose(res[k], ref[k], rel_tol=1e-5)

    def test_feature_f238_2_49th_cumulant_evar_risk_measure(self, allocator):
        """Verify 49th-cumulant Trans-Singular Borcherds-Moonshine-Monster-Whittaker-Drinfeld Higher-Homology-3 EVaR risk measure calculation and aliases."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 500)

        res_49 = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_risk_measure(returns, order=49)
        evar_49 = _extract_evar_val(res_49)
        assert isinstance(evar_49, float)
        assert math.isfinite(evar_49)
        assert evar_49 > 0.0
        assert res_49["order"] == 49
        assert math.isclose(res_49["xi_monster"], 0.9999999995, rel_tol=1e-7)

        # Verify heavier tail produces higher EVaR
        fat_tails = np.concatenate([returns, [-0.15, -0.20, -0.25]])
        res_fat = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_risk_measure(fat_tails, order=49)
        evar_fat = _extract_evar_val(res_fat)
        assert evar_fat > evar_49

        # Verify all 18 aliases on UnifiedPortfolioAllocator
        upa_evar_aliases = [
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar,
            allocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_blend,
            allocator.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar,
            allocator.singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_phase53,
            allocator.compute_phase53_evar,
            allocator.compute_phase53_evar_risk_measure,
            allocator.compute_evar_order49,
            allocator.compute_49th_cumulant_evar,
            allocator.compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_risk_measure,
            allocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_risk_measure,
            allocator.compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar,
            allocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar,
            allocator.compute_drinfeld_higher_homology_3_evar_risk_measure,
            allocator.compute_drinfeld_higher_homology_3_evar,
            allocator.compute_lurie_drinfeld_higher_homology_3_evar_risk_measure,
            allocator.compute_lurie_drinfeld_higher_homology_3_evar,
        ]
        assert len(upa_evar_aliases) == 18
        for alias_fn in upa_evar_aliases:
            val = _extract_evar_val(alias_fn(returns))
            assert math.isclose(val, evar_49, rel_tol=1e-5)

        # Verify all 18 aliases on PortfolioAllocator
        pa_evar_aliases = [
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar,
            PortfolioAllocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_blend,
            PortfolioAllocator.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar,
            PortfolioAllocator.singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_phase53,
            PortfolioAllocator.compute_phase53_evar,
            PortfolioAllocator.compute_phase53_evar_risk_measure,
            PortfolioAllocator.compute_evar_order49,
            PortfolioAllocator.compute_49th_cumulant_evar,
            PortfolioAllocator.compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_risk_measure,
            PortfolioAllocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar,
            PortfolioAllocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar,
            PortfolioAllocator.compute_drinfeld_higher_homology_3_evar_risk_measure,
            PortfolioAllocator.compute_drinfeld_higher_homology_3_evar,
            PortfolioAllocator.compute_lurie_drinfeld_higher_homology_3_evar_risk_measure,
            PortfolioAllocator.compute_lurie_drinfeld_higher_homology_3_evar,
        ]
        assert len(pa_evar_aliases) == 19  # Base method + 18 aliases
        for alias_fn in pa_evar_aliases:
            val = _extract_evar_val(alias_fn(returns))
            assert math.isclose(val, evar_49, rel_tol=1e-5)

    def test_compute_information_theoretic_blend_weights_v53(self, allocator):
        """Verify dynamic weighting in compute_information_theoretic_blend_weights and calculate_weights for version=53 in BEAR regime."""
        market_regime = "BEAR"
        weights_v52 = allocator.compute_information_theoretic_blend_weights(market_regime, version=52)
        weights_v53 = allocator.compute_information_theoretic_blend_weights(market_regime, version=53)
        calc_v53 = allocator.calculate_weights(market_regime, version=53)

        assert isinstance(weights_v53, dict)
        assert set(weights_v53.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(weights_v53.values()), 1.0, rel_tol=1e-5)
        # In BEAR regime with Phase 53, CVaR weight is prioritized and boosted
        assert weights_v53["cvar"] >= weights_v52["cvar"] - 1e-6
        for k, v in weights_v53.items():
            assert 0.0 < v < 1.0
            assert math.isclose(v, calc_v53[k], rel_tol=1e-5)

    def test_feature_f238_2_evar_degenerate_and_empty_inputs(self, allocator):
        """Verify EVaR handles empty, single-element, and NaN inputs gracefully."""
        res_empty = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_risk_measure([])
        assert _extract_evar_val(res_empty) == 0.0

        res_single = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_risk_measure([0.05])
        assert _extract_evar_val(res_single) == 0.0

        res_nan = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_3_evar_risk_measure([np.nan, np.nan])
        assert _extract_evar_val(res_nan) == 0.0

    def test_feature_f238_1_barycenter_degenerate_single_model(self, allocator):
        """Verify barycenter handles degenerate single-model concentrated inputs."""
        single_bl = {"bl": 1.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_3_fisher_rao_barycenter_blend(single_bl)
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        for v in blended.values():
            assert v > 0.0

    def test_compute_information_theoretic_blend_weights_v53_all_regimes(self, allocator):
        """Verify version=53 weighting across diverse market regimes (BULL_LOW_VOL, BULL_HIGH_VOL, CRISIS, SIDEWAYS)."""
        regimes = ["BULL_LOW_VOL", "BULL_HIGH_VOL", "CRISIS", "SIDEWAYS"]
        for reg in regimes:
            w = allocator.compute_information_theoretic_blend_weights(reg, version=53)
            assert math.isclose(sum(w.values()), 1.0, rel_tol=1e-5)
            for v in w.values():
                assert 0.0 < v < 1.0

    def test_feature_f238_2_evar_student_t_heavy_tail_monotonicity(self, allocator):
        """Verify that 49th-cumulant EVaR strictly increases for Student-t heavy tail shocks versus Gaussian."""
        np.random.seed(1234)
        gaussian_rets = np.random.normal(0.0005, 0.015, 1000)
        t_rets = np.random.standard_t(df=3, size=1000) * 0.015 + 0.0005

        evar_gauss = _extract_evar_val(allocator.compute_49th_cumulant_evar(gaussian_rets))
        evar_t = _extract_evar_val(allocator.compute_49th_cumulant_evar(t_rets))

        assert evar_t > evar_gauss
