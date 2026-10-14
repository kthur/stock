r"""
tests/test_phase100_risk.py

Unit test suite for Phase 100 Century Milestone Quantitative Risk Allocation Enhancement
(v107 Production Master, Features F472.1, F472.2, Release R116):
- Feature F472.1: Higher-Homology-50 Motivic Fisher-Rao Barycenter Blending
  (mu = [10.30, 6.50, 2.85, 12.50], simplex sum=1.0, heavy-tail CVaR prioritization: CVaR > BL > HERC > RP, tau = 1.2e-6,
   gradient clipping [-100.0, 100.0])
- Feature F472.2: 132nd-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
  (order=132, xi_monster = 0.999999999999999999999999999999999999 [36-nines])
- UnifiedPortfolioAllocator with default version=100, is_phase100=True, is_phase99=True, ..., is_phase92=True
- Strict backward compatibility with Phase 99, Phase 98, Phase 97, Phase 96 and earlier versions
- Class and module level alias trees verification (17 barycenter + 33 EVaR = 50 aliases) for UnifiedPortfolioAllocator and PortfolioAllocator
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator

try:
    from trading_system.src.risk.unified_portfolio_allocator import (
        compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_50_fisher_rao_barycenter_blend as module_barycenter_blend,
        compute_phase100_barycenter as module_phase100_barycenter,
        compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_50_evar_risk_measure as module_evar_risk_measure,
        compute_phase100_evar as module_phase100_evar,
    )
except ImportError:
    import trading_system.src.risk.unified_portfolio_allocator as _upa

    def _missing_upa(name):
        val = getattr(_upa, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'unified_portfolio_allocator' has no Phase 100 attribute '{name}'")
        return _callable

    module_barycenter_blend = _missing_upa('compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_50_fisher_rao_barycenter_blend')
    module_phase100_barycenter = _missing_upa('compute_phase100_barycenter')
    module_evar_risk_measure = _missing_upa('compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_50_evar_risk_measure')
    module_phase100_evar = _missing_upa('compute_phase100_evar')


def _extract_evar_val(res):
    if isinstance(res, dict):
        for key in res:
            if 'evar' in key.lower() and ('value' in key.lower() or key.lower().endswith('evar')):
                return float(res[key])
        return float(res.get("evar", 0.0))
    return float(res)


class TestPhase100RiskAllocation:
    """Test suite for Phase 100 Risk Allocation, Higher-Homology-50 Barycenter Blending, and 132nd-Cumulant EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=100)

    @pytest.fixture
    def default_allocator(self):
        return UnifiedPortfolioAllocator()

    @pytest.fixture
    def portfolio_allocator(self):
        return PortfolioAllocator(version=100)

    def test_default_version_is_100(self, default_allocator):
        assert default_allocator.version == 100 or default_allocator.version >= 100
        assert getattr(default_allocator, "is_phase100", False) is True
        assert getattr(default_allocator, "is_phase99", False) is True
        assert getattr(default_allocator, "is_phase98", False) is True
        assert getattr(default_allocator, "is_phase97", False) is True
        assert getattr(default_allocator, "is_phase96", False) is True
        assert getattr(default_allocator, "is_phase95", False) is True
        assert getattr(default_allocator, "is_phase94", False) is True
        assert getattr(default_allocator, "is_phase93", False) is True
        assert getattr(default_allocator, "is_phase92", False) is True

    def test_feature_f472_1_barycenter_blend_basic_properties(self, allocator):
        # 4 model inputs: BL, HERC, RP, CVaR
        w_bl = {"AAPL": 0.30, "MSFT": 0.40, "GOOGL": 0.30}
        w_herc = {"AAPL": 0.25, "MSFT": 0.45, "GOOGL": 0.30}
        w_rp = {"AAPL": 0.333, "MSFT": 0.334, "GOOGL": 0.333}
        w_cvar = {"AAPL": 0.20, "MSFT": 0.50, "GOOGL": 0.30}

        weights_dict = {"BL": w_bl, "HERC": w_herc, "RP": w_rp, "CVaR": w_cvar}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_50_fisher_rao_barycenter_blend(weights_dict)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"AAPL", "MSFT", "GOOGL"}
        total_weight = sum(blended.values())
        assert math.isclose(total_weight, 1.0, abs_tol=1e-5)
        for sym, w in blended.items():
            assert w >= 0.0

    def test_feature_f472_1_barycenter_curvature_hierarchy(self, allocator):
        # Uniform model weights: {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        # Curvature mu = [10.30, 6.50, 2.85, 12.50]
        # Guarantee: CVaR (12.50) > BL (10.30) > HERC (6.50) > RP (2.85)
        uniform_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_50_fisher_rao_barycenter_blend(uniform_weights)

        assert isinstance(res, dict)
        assert res["cvar"] > res["bl"], f"Expected cvar ({res['cvar']}) > bl ({res['bl']})"
        assert res["bl"] > res["herc"], f"Expected bl ({res['bl']}) > herc ({res['herc']})"
        assert res["herc"] > res["rp"], f"Expected herc ({res['herc']}) > rp ({res['rp']})"
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)
        # Check simplex lower bound tau = 1.2e-6
        for k, v in res.items():
            assert v >= 1.2e-6, f"Weight for {k} ({v}) below tau lower bound 1.2e-6"

    def test_feature_f472_1_barycenter_input_types(self, allocator):
        # Test DataFrame inputs
        df_weights = pd.DataFrame({
            "BL": [0.4, 0.6],
            "HERC": [0.5, 0.5],
            "RP": [0.3, 0.7],
            "CVaR": [0.45, 0.55],
        }, index=["A", "B"])

        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_50_fisher_rao_barycenter_blend(df_weights)
        assert isinstance(blended, (dict, pd.Series, np.ndarray))
        if isinstance(blended, dict):
            assert math.isclose(sum(blended.values()), 1.0, abs_tol=1e-5)

        # Test list of dicts
        list_weights = [
            {"bl": 0.3, "herc": 0.3, "rp": 0.2, "cvar": 0.2},
            {"bl": 0.4, "herc": 0.2, "rp": 0.1, "cvar": 0.3},
        ]
        res_list = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_50_fisher_rao_barycenter_blend(list_weights)
        assert isinstance(res_list, dict)
        assert math.isclose(sum(res_list.values()), 1.0, abs_tol=1e-5)

        # Test numpy 1D array
        arr_1d = np.array([0.25, 0.25, 0.25, 0.25])
        res_arr = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_50_fisher_rao_barycenter_blend(arr_1d)
        assert isinstance(res_arr, dict)
        assert math.isclose(sum(res_arr.values()), 1.0, abs_tol=1e-5)

    def test_feature_f472_1_barycenter_aliases_and_delegation(self, allocator, portfolio_allocator):
        method_names = [
            "compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_50_fisher_rao_barycenter_blend",
            "compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_50_barycenter",
            "compute_lurie_drinfeld_higher_homology_50_barycenter",
            "compute_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_50_fisher_rao_barycenter",
            "compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_50_barycenter",
            "compute_phase100_barycenter",
            "compute_phase100_fisher_rao_barycenter",
            "compute_phase100_barycenter_blend",
            "compute_higher_homology_50_barycenter",
            "phase100_fisher_rao_barycenter",
            "higher_homology_50_blend",
            "compute_lmbmwdh50_fisher_rao_barycenter_blend",
            "phase100_barycenter_blend",
            "higher_homology_50_barycenter",
            "lmbmwdh50_barycenter",
            "compute_higher_homology_50_fisher_rao_barycenter",
            "higher_homology_50_fisher_rao_barycenter_blend",
            "lurie_borcherds_higher_homology_50_barycenter",
        ]
        w_dict = {"BL": {"A": 0.5, "B": 0.5}, "HERC": {"A": 0.4, "B": 0.6}, "RP": {"A": 0.3, "B": 0.7}, "CVaR": {"A": 0.6, "B": 0.4}}
        base_res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_50_fisher_rao_barycenter_blend(w_dict)

        for name in method_names:
            fn = getattr(allocator, name, None)
            assert fn is not None, f"Missing method {name} on UnifiedPortfolioAllocator"
            res = fn(w_dict)
            for k in base_res:
                assert math.isclose(base_res[k], res[k], abs_tol=1e-5)

        # PortfolioAllocator delegation
        pa_fn = getattr(portfolio_allocator, "compute_phase100_barycenter", None)
        assert pa_fn is not None, "Missing compute_phase100_barycenter on PortfolioAllocator"
        pa_res = pa_fn(w_dict)
        for k in base_res:
            assert math.isclose(base_res[k], pa_res[k], abs_tol=1e-5)

    def test_feature_f472_1_allocate_portfolio_dispatch(self, allocator):
        w_dict = {"BL": {"A": 0.5, "B": 0.5}, "HERC": {"A": 0.4, "B": 0.6}, "RP": {"A": 0.3, "B": 0.7}, "CVaR": {"A": 0.6, "B": 0.4}}
        res = allocator.allocate_portfolio(model_weights=w_dict)
        assert isinstance(res, dict)
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)

    def test_feature_f472_2_evar_risk_measure(self, allocator, portfolio_allocator):
        returns = np.array([-0.05, -0.02, 0.01, 0.03, -0.01, 0.02, -0.04, 0.015, -0.005, 0.025])
        evar_res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_50_evar_risk_measure(returns)

        evar_val = _extract_evar_val(evar_res)
        assert evar_val > 0.0

        if isinstance(evar_res, dict):
            assert evar_res.get("order", 132) == 132
            assert math.isclose(float(evar_res.get("xi_monster", 0.0)), 1.0, abs_tol=1e-12)
            assert "phase100_evar" in evar_res

    def test_feature_f472_2_evar_aliases_and_delegation(self, allocator, portfolio_allocator):
        returns = np.array([-0.05, -0.02, 0.01, 0.03, -0.01, 0.02, -0.04, 0.015, -0.005, 0.025])
        base_res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_50_evar_risk_measure(returns)
        evar_val = _extract_evar_val(base_res)

        # Aliases
        alias_names = [
            "compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_50_evar",
            "trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_50_evar_risk_measure",
            "compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_50_evar_blend",
            "compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_50_evar",
            "singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_50_evar_risk_measure",
            "compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_phase100",
            "compute_phase100_evar",
            "compute_phase100_evar_risk_measure",
            "phase100_evar_risk_measure",
            "compute_higher_homology_50_evar_risk_measure",
            "compute_higher_homology_50_evar",
            "compute_evar_order132",
            "compute_132nd_cumulant_evar",
            "compute_monster_whittaker_132nd_cumulant_evar",
            "compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_50_evar_risk_measure",
            "compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_50_evar_risk_measure",
            "compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_50_evar",
            "compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_50_evar",
            "compute_drinfeld_higher_homology_50_evar_risk_measure",
            "compute_drinfeld_higher_homology_50_evar",
            "compute_lurie_drinfeld_higher_homology_50_evar_risk_measure",
            "compute_lurie_drinfeld_higher_homology_50_evar",
            "calculate_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_evar_132nd_cumulant",
            "evar_132nd_cumulant",
            "trans_singular_132nd_cumulant_evar",
            "eternal_omni_cosmic_132nd_cumulant_evar",
            "supreme_transcendent_evar_132",
            "higher_homology_50_evar",
            "phase100_tail_risk_evar",
            "phase100_evar_bound",
            "compute_lmbmwdh50_evar",
            "lmbmwdh50_evar",
            "trans_singular_evar_v100",
        ]
        for name in alias_names:
            fn = getattr(allocator, name, None)
            assert fn is not None, f"Missing {name} on UnifiedPortfolioAllocator"
            res = fn(returns)
            val = _extract_evar_val(res)
            assert math.isclose(evar_val, val, rel_tol=1e-4)

        # PortfolioAllocator delegation
        pa_fn = getattr(portfolio_allocator, "compute_phase100_evar", None)
        assert pa_fn is not None, "Missing compute_phase100_evar on PortfolioAllocator"
        pa_res = pa_fn(returns)
        pa_val = _extract_evar_val(pa_res)
        assert math.isclose(evar_val, pa_val, rel_tol=1e-4)

    def test_backward_compatibility_v99_v98_v97(self):
        alloc_v99 = UnifiedPortfolioAllocator(version=99)
        assert alloc_v99.is_phase99 is True
        assert getattr(alloc_v99, "is_phase100", False) is False

        alloc_v98 = UnifiedPortfolioAllocator(version=98)
        assert alloc_v98.is_phase98 is True
        assert getattr(alloc_v98, "is_phase99", False) is False
        assert getattr(alloc_v98, "is_phase100", False) is False

        alloc_v97 = UnifiedPortfolioAllocator(version=97)
        assert alloc_v97.is_phase97 is True
        assert getattr(alloc_v97, "is_phase98", False) is False
        assert getattr(alloc_v97, "is_phase99", False) is False
        assert getattr(alloc_v97, "is_phase100", False) is False

        pa_v99 = PortfolioAllocator(version=99)
        assert pa_v99.is_phase99 is True
        assert getattr(pa_v99, "is_phase100", False) is False

        pa_v98 = PortfolioAllocator(version=98)
        assert pa_v98.is_phase98 is True
        assert getattr(pa_v98, "is_phase99", False) is False
        assert getattr(pa_v98, "is_phase100", False) is False

    def test_module_level_exports(self):
        w_dict = {"BL": {"A": 0.5, "B": 0.5}, "HERC": {"A": 0.4, "B": 0.6}, "RP": {"A": 0.3, "B": 0.7}, "CVaR": {"A": 0.6, "B": 0.4}}
        res_blend = module_barycenter_blend(w_dict)
        assert isinstance(res_blend, dict)
        assert math.isclose(sum(res_blend.values()), 1.0, abs_tol=1e-5)

        res_p100_bary = module_phase100_barycenter(w_dict)
        assert isinstance(res_p100_bary, dict)
        assert math.isclose(sum(res_p100_bary.values()), 1.0, abs_tol=1e-5)

        returns = np.array([-0.05, -0.02, 0.01, 0.03, -0.01, 0.02, -0.04, 0.015, -0.005, 0.025])
        res_evar = module_evar_risk_measure(returns)
        assert _extract_evar_val(res_evar) > 0.0

        res_p100_evar = module_phase100_evar(returns)
        assert _extract_evar_val(res_p100_evar) > 0.0

    def test_numerical_stability_extreme_gradient_clipping(self, allocator):
        # Extreme skewed weights to test gradient clipping and tau lower bound
        skewed_weights = {"bl": 1e-12, "herc": 1e-12, "rp": 1e-12, "cvar": 0.999999}
        res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_50_fisher_rao_barycenter_blend(skewed_weights)
        assert isinstance(res, dict)
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)
        for k, v in res.items():
            assert not math.isnan(v)
            assert not math.isinf(v)
            assert v >= 1.2e-6
