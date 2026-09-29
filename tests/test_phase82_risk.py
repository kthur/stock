r"""
tests/test_phase82_risk.py

Unit test suite for Phase 82 Quantitative Risk Allocation Enhancement:
- Feature F383.1: Higher-Homology-32 Motivic Fisher-Rao Barycenter Blending
  (mu = [7.20, 4.60, 2.75, 8.65], simplex sum=1.0, heavy-tail CVaR prioritization: CVaR > BL > HERC > RP)
- Feature F383.2: 96th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
  (96! ~= 9.917e149, xi_monster = 0.99999999999999999999, order=96)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() and calculate_weights with version=82
- Strict backward compatibility with Phase 81, Phase 80, and earlier versions
- Class and module level alias trees verification for UnifiedPortfolioAllocator and PortfolioAllocator
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import (
    UnifiedPortfolioAllocator,
    compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_32_fisher_rao_barycenter_blend as module_barycenter_blend,
    compute_phase82_barycenter as module_phase82_barycenter,
    compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_32_evar_risk_measure as module_evar_risk_measure,
    compute_phase82_evar as module_phase82_evar,
)
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


def _extract_evar_val(res):
    if isinstance(res, dict):
        for key in res:
            if 'evar' in key.lower() and ('value' in key.lower() or key.lower().endswith('evar')):
                return float(res[key])
        return float(res.get("evar", 0.0))
    return float(res)


class TestPhase82RiskAllocation:
    """Test suite for Phase 82 Risk Allocation, Higher-Homology-32 Barycenter Blending, and 96th-Cumulant EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=82)

    @pytest.fixture
    def portfolio_allocator(self):
        return PortfolioAllocator(version=82)

    def test_feature_f383_1_barycenter_blend_basic_properties(self, allocator):
        """Verify Higher-Homology-32 Fisher-Rao barycenter converges on simplex with mu=[7.20, 4.60, 2.75, 8.65]."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_32_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 8.65, BL is second mu = 7.20, HERC is third mu = 4.60, RP is fourth mu = 2.75
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]
        for k, v in blended.items():
            assert 0.0 < v < 1.0

    def test_feature_f383_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_32_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_32_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_32_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f383_1_barycenter_aliases_and_delegation(self, allocator, portfolio_allocator):
        """Verify barycenter aliases work on UnifiedPortfolioAllocator, PortfolioAllocator, and module level."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_32_fisher_rao_barycenter_blend(w)
        assert isinstance(ref, dict)
        assert math.isclose(sum(ref.values()), 1.0, rel_tol=1e-5)

        # UnifiedPortfolioAllocator aliases
        assert allocator.compute_phase82_barycenter(w) == ref
        assert allocator.compute_phase82_fisher_rao_barycenter(w) == ref
        assert allocator.compute_higher_homology_32_barycenter(w) == ref
        assert allocator.higher_homology_32_blend(w) == ref
        assert allocator.compute_lmbmwdh32_fisher_rao_barycenter_blend(w) == ref

        # PortfolioAllocator delegation and aliases
        pa_res = portfolio_allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_32_fisher_rao_barycenter_blend(w)
        assert math.isclose(sum(pa_res.values()), 1.0, rel_tol=1e-5)
        assert pa_res == ref
        assert portfolio_allocator.compute_phase82_barycenter(w) == ref
        assert portfolio_allocator.compute_phase82_fisher_rao_barycenter(w) == ref

        # Module level aliases
        mod_res = module_barycenter_blend(w)
        assert math.isclose(sum(mod_res.values()), 1.0, rel_tol=1e-5)
        assert mod_res == ref
        assert module_phase82_barycenter(w) == ref

    def test_feature_f383_2_96th_cumulant_evar_computation(self, allocator, portfolio_allocator):
        """Verify 96th-cumulant expansion trans-singular EVaR computation."""
        np.random.seed(42)
        returns = np.random.normal(-0.005, 0.02, 200)

        evar_dict = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_32_evar_risk_measure(
            returns=returns, alpha=0.05
        )
        assert isinstance(evar_dict, dict)
        assert "order" in evar_dict
        assert evar_dict["order"] == 96
        assert "xi_monster" in evar_dict
        assert math.isclose(evar_dict["xi_monster"], 0.99999999999999999999, rel_tol=1e-15)

        val = _extract_evar_val(evar_dict)
        assert val > 0.0
        assert math.isfinite(val)

        # PortfolioAllocator delegation
        pa_evar = portfolio_allocator.compute_phase82_evar(returns=returns, alpha=0.05)
        val_pa = _extract_evar_val(pa_evar)
        assert math.isclose(val, val_pa, rel_tol=1e-5)

        # Module level
        mod_evar = module_phase82_evar(returns=returns, alpha=0.05)
        val_mod = _extract_evar_val(mod_evar)
        assert math.isclose(val, val_mod, rel_tol=1e-5)

    def test_feature_f383_regime_weights_version82(self):
        """Verify get_regime_weights applies Higher-Homology-32 barycenter blend when version >= 82."""
        alloc_v82 = UnifiedPortfolioAllocator(version=82)
        assert alloc_v82.is_phase82 is True
        assert alloc_v82.is_phase81 is True
        assert alloc_v82.is_phase80 is True
        assert alloc_v82.is_phase79 is True
        weights = alloc_v82.compute_information_theoretic_blend_weights(regime="bull_low_vol", version=82)
        assert isinstance(weights, dict)
        assert set(weights.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(weights.values()), 1.0, rel_tol=1e-5)
        # CVaR is boosted due to mu_32=[7.20, 4.60, 2.75, 8.65]
        assert weights["cvar"] > weights["rp"]

    def test_feature_f383_backward_compatibility_v81_and_prior(self):
        """Verify strict backward compatibility with Phase 81, Phase 80, and earlier versions."""
        w = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}

        alloc_v81 = UnifiedPortfolioAllocator(version=81)
        assert alloc_v81.is_phase81 is True
        assert alloc_v81.is_phase82 is False
        b_81 = alloc_v81.compute_phase81_barycenter(w)
        assert math.isclose(sum(b_81.values()), 1.0, rel_tol=1e-5)

        alloc_v80 = UnifiedPortfolioAllocator(version=80)
        assert alloc_v80.is_phase80 is True
        assert alloc_v80.is_phase81 is False
        assert alloc_v80.is_phase82 is False
        b_80 = alloc_v80.compute_phase80_barycenter(w)
        assert math.isclose(sum(b_80.values()), 1.0, rel_tol=1e-5)

        alloc_v79 = UnifiedPortfolioAllocator(version=79)
        assert alloc_v79.is_phase79 is True
        assert alloc_v79.is_phase80 is False
        assert alloc_v79.is_phase81 is False
        assert alloc_v79.is_phase82 is False
        b_79 = alloc_v79.compute_phase79_barycenter(w)
        assert math.isclose(sum(b_79.values()), 1.0, rel_tol=1e-5)
