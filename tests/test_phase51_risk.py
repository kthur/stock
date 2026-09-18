r"""
tests/test_phase51_risk.py

Unit test suite for Phase 51 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F228.1: Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Homology Motivic Fisher-Rao Barycenter Blending
  (mu_lmbwdh = [4.10, 3.05, 3.00, 4.65], simplex sum=1.0, heavy-tail CVaR prioritization)
- Feature F228.2: 47th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
  (47! ~= 2.58623 x 10^59, xi_monster = 0.999999998, order=47)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() with version=51
- Strict backward compatibility with Phase 50 and earlier versions
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
            "trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_value",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_evar_value",
            res.get("evar", 0.0)))
        ))
    return float(res)


class TestPhase51RiskAllocation:
    """Test suite for Phase 51 Risk Allocation and Barycenter Blending."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_feature_f228_1_barycenter_blend_basic_properties(self, allocator):
        """Verify that Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Homology Fisher-Rao barycenter converges on simplex."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_homology_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 4.65, BL is second mu = 4.10, HERC is third mu = 3.05, RP is fourth mu = 3.00
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]
        # Interior point positivity
        for k, v in blended.items():
            assert 0.0 < v < 1.0

    def test_feature_f228_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        # 1. 1D Array
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_homology_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        # 2. List of dicts
        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_homology_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        # 3. 2D array
        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_homology_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f228_1_barycenter_aliases_and_portfolio_allocator(self, allocator):
        """Verify that all 18 barycenter aliases work on both UnifiedPortfolioAllocator and PortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_homology_fisher_rao_barycenter_blend(w)

        for alias_fn in [
            allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_homology_barycenter,
            allocator.compute_lurie_drinfeld_homology_barycenter,
            allocator.compute_borcherds_monster_moonshine_whittaker_drinfeld_homology_fisher_rao_barycenter,
            allocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_homology_barycenter,
            allocator.compute_drinfeld_homology_barycenter,
            allocator.compute_phase51_fisher_rao_barycenter,
            allocator.compute_phase51_barycenter_blend,
            allocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_homology_fisher_rao_barycenter_blend,
            allocator.compute_motivic_borcherds_moonshine_monster_whittaker_drinfeld_homology_barycenter_blend,
            allocator.compute_analytic_borcherds_moonshine_monster_whittaker_drinfeld_homology_barycenter_blend,
            allocator.compute_chiral_borcherds_moonshine_monster_whittaker_drinfeld_homology_barycenter_blend,
            allocator.compute_quantum_langlands_borcherds_moonshine_monster_whittaker_drinfeld_homology_barycenter_blend,
            allocator.compute_chiral_oper_borcherds_moonshine_monster_whittaker_drinfeld_homology_barycenter_blend,
            allocator.compute_lurie_quantum_langlands_borcherds_moonshine_monster_whittaker_drinfeld_homology_barycenter,
            allocator.compute_lmbmwdh_barycenter,
            allocator.compute_lmbmwdh_fisher_rao_barycenter,
            allocator.compute_lmmwdh_barycenter,
            allocator.compute_lmmwdh_fisher_rao_barycenter,
            PortfolioAllocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_homology_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_homology_barycenter,
            PortfolioAllocator.compute_lurie_drinfeld_homology_barycenter,
            PortfolioAllocator.compute_borcherds_monster_moonshine_whittaker_drinfeld_homology_fisher_rao_barycenter,
            PortfolioAllocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_homology_barycenter,
            PortfolioAllocator.compute_phase51_fisher_rao_barycenter,
            PortfolioAllocator.compute_phase51_barycenter_blend,
            PortfolioAllocator.compute_lmbmwdh_barycenter,
            PortfolioAllocator.compute_lmmwdh_fisher_rao_barycenter,
        ]:
            out = alias_fn(w)
            for k in ref:
                assert math.isclose(out[k], ref[k], rel_tol=1e-5)

    def test_feature_f228_2_47th_cumulant_evar_risk_measure(self, allocator):
        """Verify 47th-cumulant Trans-Singular Borcherds-Moonshine-Monster-Whittaker EVaR risk measure calculation and aliases."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 500)

        res_47 = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_risk_measure(returns, order=47)
        evar_47 = _extract_evar_val(res_47)
        assert isinstance(evar_47, float)
        assert math.isfinite(evar_47)
        assert evar_47 > 0.0

        # Verify heavier tail produces higher EVaR
        fat_tails = np.concatenate([returns, [-0.15, -0.20, -0.25]])
        res_fat = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_risk_measure(fat_tails, order=47)
        evar_fat = _extract_evar_val(res_fat)
        assert evar_fat > evar_47

        # Verify aliases on UnifiedPortfolioAllocator and PortfolioAllocator
        for alias_fn in [
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_phase51,
            allocator.compute_phase51_evar,
            allocator.compute_phase51_evar_risk_measure,
            allocator.compute_evar_order47,
            allocator.compute_47th_cumulant_evar,
            allocator.compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_homology_evar_risk_measure,
            allocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_homology_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_phase51,
            PortfolioAllocator.compute_phase51_evar,
            PortfolioAllocator.compute_phase51_evar_risk_measure,
            PortfolioAllocator.compute_evar_order47,
            PortfolioAllocator.compute_47th_cumulant_evar,
            PortfolioAllocator.compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_homology_evar_risk_measure,
            PortfolioAllocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_homology_evar_risk_measure,
        ]:
            val = _extract_evar_val(alias_fn(returns))
            assert math.isclose(val, evar_47, rel_tol=1e-5)

    def test_compute_information_theoretic_blend_weights_v51(self, allocator):
        """Verify dynamic weighting in compute_information_theoretic_blend_weights for version=51 in BEAR regime."""
        market_regime = "BEAR"
        weights_v50 = allocator.compute_information_theoretic_blend_weights(market_regime, version=50)
        weights_v51 = allocator.compute_information_theoretic_blend_weights(market_regime, version=51)

        assert isinstance(weights_v51, dict)
        assert set(weights_v51.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(weights_v51.values()), 1.0, rel_tol=1e-5)
        # In BEAR regime with Phase 51, CVaR weight is prioritized and boosted
        assert weights_v51["cvar"] >= weights_v50["cvar"] - 1e-6
        for k, v in weights_v51.items():
            assert 0.0 < v < 1.0
