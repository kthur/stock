r"""
tests/test_phase89_risk.py

Unit test suite for Phase 89 Quantitative Risk Allocation Enhancement (Feature F417):
- Feature F417.1: Higher-Homology-39 Motivic Fisher-Rao Barycenter Blending
  (mu = [8.10, 4.95, 2.40, 9.80], simplex sum=1.0, heavy-tail CVaR prioritization: CVaR > BL > HERC > RP, tau = 0.0000065)
- Feature F417.2: 110th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
  (order=110, xi_monster = 0.99999999999999999999999995)
- UnifiedPortfolioAllocator with default version=89 and dynamic regime shifts
- Strict backward compatibility with Phase 88, Phase 87, Phase 86, Phase 85, and earlier versions
- Class and module level alias trees verification for UnifiedPortfolioAllocator and PortfolioAllocator
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator

try:
    from trading_system.src.risk.unified_portfolio_allocator import (
        compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_39_fisher_rao_barycenter_blend as module_barycenter_blend,
        compute_phase89_barycenter as module_phase89_barycenter,
        compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_39_evar_risk_measure as module_evar_risk_measure,
        compute_phase89_evar as module_phase89_evar,
    )
except ImportError:
    import trading_system.src.risk.unified_portfolio_allocator as _upa

    def _missing_upa(name):
        val = getattr(_upa, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'unified_portfolio_allocator' has no Phase 89 attribute '{name}'")
        return _callable

    module_barycenter_blend = _missing_upa('compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_39_fisher_rao_barycenter_blend')
    module_phase89_barycenter = _missing_upa('compute_phase89_barycenter')
    module_evar_risk_measure = _missing_upa('compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_39_evar_risk_measure')
    module_phase89_evar = _missing_upa('compute_phase89_evar')


def _extract_evar_val(res):
    if isinstance(res, dict):
        for key in res:
            if 'evar' in key.lower() and ('value' in key.lower() or key.lower().endswith('evar')):
                return float(res[key])
        return float(res.get("evar", 0.0))
    return float(res)


class TestPhase89RiskAllocation:
    """Test suite for Phase 89 Risk Allocation, Higher-Homology-39 Barycenter Blending, and 110th-Cumulant EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=89)

    @pytest.fixture
    def default_allocator(self):
        return UnifiedPortfolioAllocator()

    @pytest.fixture
    def portfolio_allocator(self):
        return PortfolioAllocator(version=89)

    def test_default_version_is_89(self, default_allocator):
        """Verify UnifiedPortfolioAllocator defaults to version=89 with is_phase89=True."""
        assert default_allocator.version == 89
        assert default_allocator.is_phase89 is True
        assert default_allocator.is_phase88 is True
        assert default_allocator.is_phase87 is True
        assert default_allocator.is_phase86 is True
        assert default_allocator.is_phase85 is True

    def test_feature_f417_1_barycenter_blend_basic_properties(self, allocator):
        """Verify Higher-Homology-39 Fisher-Rao barycenter converges on simplex with mu=[8.10, 4.95, 2.40, 9.80]."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_39_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 9.80, BL is second mu = 8.10, HERC is third mu = 4.95, RP is fourth mu = 2.40
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]
        for k, v in blended.items():
            assert 0.0 < v < 1.0

    def test_feature_f417_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_39_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_39_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_39_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f417_1_barycenter_aliases_and_delegation(self, allocator, portfolio_allocator):
        """Verify barycenter aliases work on UnifiedPortfolioAllocator, PortfolioAllocator, and module level."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_39_fisher_rao_barycenter_blend(w)
        assert isinstance(ref, dict)
        assert math.isclose(sum(ref.values()), 1.0, rel_tol=1e-5)

        # UnifiedPortfolioAllocator aliases
        assert allocator.compute_phase89_barycenter(w) == ref
        assert allocator.compute_phase89_fisher_rao_barycenter(w) == ref
        assert allocator.compute_higher_homology_39_barycenter(w) == ref
        assert allocator.higher_homology_39_blend(w) == ref
        assert allocator.compute_lmbmwdh39_fisher_rao_barycenter_blend(w) == ref
        assert allocator.phase89_barycenter_blend(w) == ref
        assert allocator.higher_homology_39_barycenter(w) == ref
        assert allocator.lmbmwdh39_barycenter(w) == ref

        # PortfolioAllocator delegation and aliases
        pa_res = portfolio_allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_39_fisher_rao_barycenter_blend(w)
        assert math.isclose(sum(pa_res.values()), 1.0, rel_tol=1e-5)
        assert pa_res == ref
        assert portfolio_allocator.compute_phase89_barycenter(w) == ref
        assert portfolio_allocator.compute_phase89_fisher_rao_barycenter(w) == ref
        assert portfolio_allocator.compute_phase89_barycenter_blend(w) == ref
        assert portfolio_allocator.higher_homology_39_barycenter(w) == ref
        assert portfolio_allocator.lmbmwdh39_barycenter(w) == ref

        # Module level
        assert module_barycenter_blend(w) == ref
        assert module_phase89_barycenter(w) == ref

    def test_feature_f417_2_evar_risk_measure(self, allocator, portfolio_allocator):
        """Verify 110th-Cumulant Expansion Trans-Singular EVaR Risk Measure."""
        returns = np.array([0.02, -0.015, 0.03, -0.025, 0.01, -0.005, 0.015, -0.01])
        res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_39_evar_risk_measure(returns=returns)

        assert isinstance(res, dict)
        assert "evar" in res
        assert res["order"] == 110
        assert res["xi_monster"] == 0.99999999999999999999999995
        assert "phase89_evar" in res
        assert math.isfinite(res["evar"])
        assert res["evar"] > 0

        # UnifiedPortfolioAllocator aliases
        ref_evar = res["evar"]
        assert math.isclose(_extract_evar_val(allocator.compute_phase89_evar(returns=returns)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(allocator.compute_evar_order110(returns=returns)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(allocator.compute_110th_cumulant_evar(returns=returns)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(allocator.higher_homology_39_evar(returns=returns)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(allocator.phase89_tail_risk_evar(returns=returns)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(allocator.phase89_evar_bound(returns=returns)), ref_evar, rel_tol=1e-5)

        # PortfolioAllocator aliases
        pa_evar = portfolio_allocator.compute_phase89_evar(returns=returns)
        assert math.isclose(_extract_evar_val(pa_evar), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(portfolio_allocator.compute_110th_cumulant_evar(returns=returns)), ref_evar, rel_tol=1e-5)

        # Module level
        assert math.isclose(_extract_evar_val(module_evar_risk_measure(returns=returns)), ref_evar, rel_tol=1e-5)
        assert math.isclose(_extract_evar_val(module_phase89_evar(returns=returns)), ref_evar, rel_tol=1e-5)

    def test_backward_compatibility_v88_v87_v86_v85(self, allocator):
        """Verify version=89 allocator retains backward compatibility for v88, v87, v86, and v85 barycenters."""
        w = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        res88 = allocator.compute_phase88_barycenter(w)
        assert math.isclose(sum(res88.values()), 1.0, rel_tol=1e-5)
        res87 = allocator.compute_phase87_barycenter(w)
        assert math.isclose(sum(res87.values()), 1.0, rel_tol=1e-5)
        res86 = allocator.compute_phase86_barycenter(w)
        assert math.isclose(sum(res86.values()), 1.0, rel_tol=1e-5)
        res85 = allocator.compute_phase85_barycenter(w)
        assert math.isclose(sum(res85.values()), 1.0, rel_tol=1e-5)
