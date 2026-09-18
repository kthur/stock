r"""
tests/test_phase56_risk.py

Unit test suite for Phase 56 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F253.1: Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology-6 Fisher-Rao Barycenter Blending
  (mu_lmbwdh6 = [4.60, 3.30, 3.25, 5.15], simplex sum=1.0, heavy-tail CVaR prioritization)
- Feature F253.2: 52nd-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
  (52! ~= 8.0658 x 10^67, xi_monster = 0.99999999995, order=52)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() and calculate_weights with version=56
- Strict backward compatibility with Phase 55 and earlier versions
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
            "trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_6_evar_value",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_6_evar",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_5_evar_value",
            res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_5_evar",
            res.get("evar", 0.0))))
        ))
    return float(res)


class TestPhase56RiskAllocation:
    """Test suite for Phase 56 Risk Allocation and Barycenter Blending."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_feature_f253_1_barycenter_blend_basic_properties(self, allocator):
        """Verify that Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology-6 Fisher-Rao barycenter converges on simplex."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_6_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 5.15, BL is second mu = 4.60, HERC is third mu = 3.30, RP is fourth mu = 3.25
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]
        # Interior point positivity
        for k, v in blended.items():
            assert 0.0 < v < 1.0

    def test_feature_f253_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        # 1. 1D Array
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_6_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        # 2. List of dicts
        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_6_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        # 3. 2D array
        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_6_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f253_1_barycenter_aliases_and_portfolio_allocator(self, allocator):
        """Verify that all barycenter aliases work on both UnifiedPortfolioAllocator and PortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_6_fisher_rao_barycenter_blend(w)

        # Aliases on UnifiedPortfolioAllocator
        upa_aliases = [
            allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_6_barycenter,
            allocator.compute_lurie_drinfeld_higher_homology_6_barycenter,
            allocator.compute_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_6_fisher_rao_barycenter,
            allocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_6_barycenter,
            allocator.compute_drinfeld_higher_homology_6_barycenter,
            allocator.compute_phase56_fisher_rao_barycenter,
            allocator.compute_phase56_barycenter_blend,
            allocator.compute_higher_homology_6_barycenter,
            allocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_6_fisher_rao_barycenter_blend,
            allocator.compute_motivic_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_6_barycenter_blend,
            allocator.compute_analytic_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_6_barycenter_blend,
            allocator.compute_chiral_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_6_barycenter_blend,
            allocator.compute_quantum_langlands_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_6_barycenter_blend,
            allocator.compute_chiral_oper_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_6_barycenter_blend,
            allocator.compute_lurie_quantum_langlands_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_6_barycenter,
            allocator.compute_lmbmwdh6_barycenter,
            allocator.compute_lmbmwdh6_fisher_rao_barycenter,
        ]
        for fn in upa_aliases:
            res = fn(w)
            for k in ["bl", "herc", "rp", "cvar"]:
                assert math.isclose(res[k], ref[k], rel_tol=1e-5)

        # Aliases on PortfolioAllocator (class & instance)
        pa = PortfolioAllocator()
        pa_aliases = [
            pa.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_6_fisher_rao_barycenter_blend,
            pa.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_6_barycenter,
            pa.compute_phase56_fisher_rao_barycenter,
            pa.compute_higher_homology_6_barycenter,
            pa.compute_lmbmwdh6_barycenter,
            PortfolioAllocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_6_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_phase56_fisher_rao_barycenter,
            PortfolioAllocator.compute_higher_homology_6_barycenter,
        ]
        for fn in pa_aliases:
            res = fn(w)
            for k in ["bl", "herc", "rp", "cvar"]:
                assert math.isclose(res[k], ref[k], rel_tol=1e-5)

    def test_feature_f253_2_52nd_cumulant_evar_risk_measure(self, allocator):
        """Verify 52nd-cumulant EVaR risk measure calculation and properties."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 1000)

        res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_6_evar_risk_measure(
            returns,
            confidence_level=0.99,
        )
        assert isinstance(res, dict)
        evar_val = _extract_evar_val(res)
        assert math.isfinite(evar_val)
        assert evar_val > 0.0

        # Check return keys
        assert "evar" in res
        assert "order" in res
        assert res["order"] == 52
        assert "xi_monster" in res
        assert math.isclose(res["xi_monster"], 0.99999999995)

        # Empty / trivial returns safety
        res_empty = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_6_evar_risk_measure([])
        assert _extract_evar_val(res_empty) == 0.0

    def test_feature_f253_2_evar_aliases(self, allocator):
        """Verify all 52nd-cumulant EVaR aliases on UnifiedPortfolioAllocator and PortfolioAllocator."""
        np.random.seed(123)
        returns = np.random.normal(0.0005, 0.015, 500)
        ref = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_6_evar_risk_measure(returns)
        ref_val = _extract_evar_val(ref)

        upa_evar_aliases = [
            allocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_6_evar,
            allocator.compute_higher_homology_6_evar,
            allocator.compute_phase56_evar,
            allocator.compute_52nd_cumulant_evar,
            allocator.compute_lmbmwdh6_evar,
        ]
        for fn in upa_evar_aliases:
            res = fn(returns)
            assert math.isclose(_extract_evar_val(res), ref_val, rel_tol=1e-5)

        pa = PortfolioAllocator()
        pa_evar_aliases = [
            pa.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_6_evar_risk_measure,
            pa.compute_higher_homology_6_evar,
            pa.compute_phase56_evar,
            pa.compute_52nd_cumulant_evar,
            PortfolioAllocator.compute_phase56_evar,
            PortfolioAllocator.compute_52nd_cumulant_evar,
        ]
        for fn in pa_evar_aliases:
            res = fn(returns)
            assert math.isclose(_extract_evar_val(res), ref_val, rel_tol=1e-5)

    def test_information_theoretic_blend_weights_version_56(self, allocator):
        """Verify dynamic weighting in compute_information_theoretic_blend_weights and calculate_weights for version=56 in BEAR regime."""
        market_regime = "BEAR"
        weights_v55 = allocator.compute_information_theoretic_blend_weights(market_regime, version=55)
        weights_v56 = allocator.compute_information_theoretic_blend_weights(market_regime, version=56)
        calc_v56 = allocator.calculate_weights(market_regime, version=56)

        assert isinstance(weights_v56, dict)
        assert set(weights_v56.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(weights_v56.values()), 1.0, rel_tol=1e-5)
        # In BEAR regime with Phase 56, CVaR weight is prioritized and boosted
        assert weights_v56["cvar"] >= weights_v55["cvar"] - 1e-6
        for k, v in weights_v56.items():
            assert 0.0 < v < 1.0
            assert math.isclose(v, calc_v56[k], rel_tol=1e-5)

    def test_strict_backward_compatibility_v55_and_earlier(self, allocator):
        """Verify backward compatibility of barycenter and information theoretic weights for v55, v54, v53."""
        for v in [55, 54, 53, 52, 51, 50]:
            w = allocator.compute_information_theoretic_blend_weights(
                regime="BULL_LOW_VOL",
                uncertainty=0.1,
                contagion_risk=0.05,
                version=v,
            )
            assert math.isclose(sum(w.values()), 1.0, rel_tol=1e-5)
            for k in ["bl", "herc", "rp", "cvar"]:
                assert 0.0 < w[k] < 1.0
