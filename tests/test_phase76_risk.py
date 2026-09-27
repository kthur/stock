r"""
tests/test_phase76_risk.py

Unit test suite for Phase 76 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F353.1: Higher-Homology-26 Motivic Fisher-Rao Barycenter Blending
  (mu = [6.60, 4.30, 3.05, 7.75], simplex sum=1.0, heavy-tail CVaR prioritization: CVaR > BL > HERC > RP)
- Feature F353.2: 84th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
  (84! ~= 3.314e126, xi_monster = 0.99999999999999998, order=84)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() and calculate_weights with version=76
- Strict backward compatibility with Phase 75 and earlier versions
- Class and module level alias trees verification for UnifiedPortfolioAllocator and PortfolioAllocator
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import (
    UnifiedPortfolioAllocator,
    compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_26_fisher_rao_barycenter_blend as module_barycenter_blend,
    compute_phase76_barycenter as module_phase76_barycenter,
    compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_26_evar_risk_measure as module_evar_risk_measure,
    compute_phase76_evar as module_phase76_evar,
)
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


def _extract_evar_val(res):
    if isinstance(res, dict):
        for key in res:
            if 'evar' in key.lower() and ('value' in key.lower() or key.lower().endswith('evar')):
                return float(res[key])
        return float(res.get("evar", 0.0))
    return float(res)


class TestPhase76RiskAllocation:
    """Test suite for Phase 76 Risk Allocation, Higher-Homology-26 Barycenter Blending, and 84th-Cumulant EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=76)

    @pytest.fixture
    def portfolio_allocator(self):
        return PortfolioAllocator()

    def test_feature_f353_1_barycenter_blend_basic_properties(self, allocator):
        """Verify Higher-Homology-26 Fisher-Rao barycenter converges on simplex with mu=[6.60, 4.30, 3.05, 7.75]."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_26_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 7.75, BL is second mu = 6.60, HERC is third mu = 4.30, RP is fourth mu = 3.05
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]
        for k, v in blended.items():
            assert 0.0 < v < 1.0

    def test_feature_f353_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_26_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_26_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_26_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f353_1_barycenter_aliases_and_delegation(self, allocator, portfolio_allocator):
        """Verify barycenter aliases work on UnifiedPortfolioAllocator, PortfolioAllocator, and module level."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_26_fisher_rao_barycenter_blend(w)
        assert isinstance(ref, dict)
        assert math.isclose(sum(ref.values()), 1.0, rel_tol=1e-5)

        # UnifiedPortfolioAllocator aliases
        assert allocator.compute_phase76_barycenter(w) == ref
        assert allocator.compute_phase76_fisher_rao_barycenter(w) == ref
        assert allocator.compute_higher_homology_26_barycenter(w) == ref
        assert allocator.higher_homology_26_blend(w) == ref
        assert allocator.compute_lmbmwdh26_fisher_rao_barycenter_blend(w) == ref
        assert allocator.borcherds_higher_homology_26_barycenter(w) == ref

        # PortfolioAllocator delegation and aliases
        pa_res = portfolio_allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_26_fisher_rao_barycenter_blend(w)
        assert math.isclose(sum(pa_res.values()), 1.0, rel_tol=1e-5)
        assert pa_res == ref
        assert portfolio_allocator.compute_phase76_barycenter(w) == ref
        assert portfolio_allocator.higher_homology_26_blend(w) == ref
        assert portfolio_allocator.compute_lmbmwdh26_fisher_rao_barycenter_blend(w) == ref

        # Module-level exports
        mod_res = module_barycenter_blend(w)
        assert mod_res == ref
        assert module_phase76_barycenter(w) == ref

    def test_feature_f353_2_84th_cumulant_evar_risk_measure(self, allocator):
        """Verify 84th-cumulant expansion EVaR properties with 84! ~= 3.314e126 and xi_monster = 0.99999999999999998."""
        np.random.seed(76)
        returns = np.random.normal(0.001, 0.02, 500)

        res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_26_evar_risk_measure(
            returns,
            alpha=0.05,
            order=84,
            xi_monster=0.99999999999999998,
        )

        evar_val = _extract_evar_val(res)
        assert math.isfinite(evar_val)
        assert evar_val > 0.0
        assert res["order"] == 84
        assert res["xi_monster"] == 0.99999999999999998

        empty_res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_26_evar_risk_measure(
            [], alpha=0.05
        )
        assert _extract_evar_val(empty_res) == 0.0

    def test_feature_f353_2_evar_fat_tailed_and_volatility_sensitivity(self, allocator):
        """Verify fat-tailed returns have higher EVaR than Gaussian, and EVaR increases with volatility."""
        np.random.seed(7676)
        norm_rets = np.random.normal(0.0, 0.02, 1000)
        t_rets = np.random.standard_t(df=3, size=1000) * 0.02

        evar_norm = _extract_evar_val(allocator.compute_phase76_evar(norm_rets))
        evar_t = _extract_evar_val(allocator.compute_phase76_evar(t_rets))
        assert evar_t > evar_norm

        base = np.random.normal(0.0, 1.0, 1000)
        r_low = base * 0.01
        r_high = base * 0.05
        e_low = _extract_evar_val(allocator.compute_phase76_evar(r_low))
        e_high = _extract_evar_val(allocator.compute_phase76_evar(r_high))
        assert e_high > e_low

    def test_feature_f353_2_evar_aliases_and_delegation(self, allocator, portfolio_allocator):
        """Verify EVaR aliases on UnifiedPortfolioAllocator, PortfolioAllocator, and module level."""
        np.random.seed(76)
        r = np.random.normal(0.001, 0.02, 200)

        ref = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_26_evar_risk_measure(r)
        ref_val = _extract_evar_val(ref)

        # UnifiedPortfolioAllocator aliases
        assert _extract_evar_val(allocator.compute_phase76_evar(r)) == ref_val
        assert _extract_evar_val(allocator.compute_phase76_evar_risk_measure(r)) == ref_val
        assert _extract_evar_val(allocator.compute_evar_order84(r)) == ref_val
        assert _extract_evar_val(allocator.higher_homology_26_evar(r)) == ref_val
        assert _extract_evar_val(allocator.lmbmwdh26_evar(r)) == ref_val

        # PortfolioAllocator delegation and aliases
        pa_res = portfolio_allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_26_evar_risk_measure(r)
        assert _extract_evar_val(pa_res) == ref_val
        assert _extract_evar_val(portfolio_allocator.compute_phase76_evar(r)) == ref_val
        assert _extract_evar_val(portfolio_allocator.compute_evar_order84(r)) == ref_val
        assert _extract_evar_val(portfolio_allocator.higher_homology_26_evar(r)) == ref_val

        # Module-level exports
        mod_res = module_evar_risk_measure(r)
        assert _extract_evar_val(mod_res) == ref_val
        assert _extract_evar_val(module_phase76_evar(r)) == ref_val

    def test_phase76_regime_shifts_and_entropy(self, allocator):
        """Verify Phase 76 regime shifts in compute_information_theoretic_blend_weights."""
        w = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        res = allocator.compute_information_theoretic_blend_weights(w, version=76)
        assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-4)
        assert res["cvar"] > 0.50
        assert res["cvar"] > res["herc"] > res["bl"] > res["rp"]

        # Default invocation
        res_default = allocator.compute_information_theoretic_blend_weights(w)
        assert math.isclose(sum(res_default.values()), 1.0, rel_tol=1e-4)

    def test_backward_compatibility_v75_and_prior(self):
        """Verify backward compatibility for versions 75, 74, 73, 72, 71, 70, 69."""
        for v in [75, 74, 73, 72, 71, 70, 69]:
            alloc = UnifiedPortfolioAllocator(version=v)
            w = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
            res = alloc.compute_information_theoretic_blend_weights(w)
            assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-4)
