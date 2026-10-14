r"""
tests/test_phase98_risk.py

Unit test suite for Phase 98 Quantitative Risk Allocation Enhancement (v105 Production Master, Features F462.1, F462.2):
- Feature F462.1: Higher-Homology-48 Motivic Fisher-Rao Barycenter Blending
  (mu = [9.90, 6.20, 2.75, 12.00], simplex sum=1.0, heavy-tail CVaR prioritization: CVaR > BL > HERC > RP, tau = 0.0000020)
- Feature F462.2: 128th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
  (order=128, xi_monster = 0.999999999999999999999999999999999 [34-nines: 33 nines after decimal point])
- UnifiedPortfolioAllocator with default version=98, is_phase98=True, is_phase97=True, is_phase96=True, is_phase95=True
- Strict backward compatibility with Phase 97, Phase 96, Phase 95 and earlier versions
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
        compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_48_fisher_rao_barycenter_blend as module_barycenter_blend,
        compute_phase98_barycenter as module_phase98_barycenter,
        compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_48_evar_risk_measure as module_evar_risk_measure,
        compute_phase98_evar as module_phase98_evar,
    )
except ImportError:
    import trading_system.src.risk.unified_portfolio_allocator as _upa

    def _missing_upa(name):
        val = getattr(_upa, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'unified_portfolio_allocator' has no Phase 98 attribute '{name}'")
        return _callable

    module_barycenter_blend = _missing_upa('compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_48_fisher_rao_barycenter_blend')
    module_phase98_barycenter = _missing_upa('compute_phase98_barycenter')
    module_evar_risk_measure = _missing_upa('compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_48_evar_risk_measure')
    module_phase98_evar = _missing_upa('compute_phase98_evar')


def _extract_evar_val(res):
    if isinstance(res, dict):
        for key in res:
            if 'evar' in key.lower() and ('value' in key.lower() or key.lower().endswith('evar')):
                return float(res[key])
        return float(res.get("evar", 0.0))
    return float(res)


class TestPhase98RiskAllocation:
    """Test suite for Phase 98 Risk Allocation, Higher-Homology-48 Barycenter Blending, and 128th-Cumulant EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=98)

    @pytest.fixture
    def default_allocator(self):
        return UnifiedPortfolioAllocator()

    @pytest.fixture
    def portfolio_allocator(self):
        return PortfolioAllocator(version=98)

    def test_default_version_is_98(self, default_allocator):
        assert default_allocator.version == 98 or default_allocator.version >= 98
        assert getattr(default_allocator, "is_phase98", False) is True
        assert getattr(default_allocator, "is_phase97", False) is True
        assert getattr(default_allocator, "is_phase96", False) is True
        assert getattr(default_allocator, "is_phase95", False) is True
        assert getattr(default_allocator, "is_phase94", False) is True
        assert getattr(default_allocator, "is_phase93", False) is True
        assert getattr(default_allocator, "is_phase92", False) is True

    def test_feature_f462_1_barycenter_blend_basic_properties(self, allocator):
        # 4 model inputs: BL, HERC, RP, CVaR
        w_bl = {"AAPL": 0.30, "MSFT": 0.40, "GOOGL": 0.30}
        w_herc = {"AAPL": 0.25, "MSFT": 0.45, "GOOGL": 0.30}
        w_rp = {"AAPL": 0.333, "MSFT": 0.334, "GOOGL": 0.333}
        w_cvar = {"AAPL": 0.20, "MSFT": 0.50, "GOOGL": 0.30}

        weights_dict = {"BL": w_bl, "HERC": w_herc, "RP": w_rp, "CVaR": w_cvar}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_48_fisher_rao_barycenter_blend(weights_dict)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"AAPL", "MSFT", "GOOGL"}
        total_weight = sum(blended.values())
        assert math.isclose(total_weight, 1.0, abs_tol=1e-5)
        for sym, w in blended.items():
            assert w >= 0.0

    def test_feature_f462_1_barycenter_curvature_hierarchy(self, allocator):
        # Uniform model weights: {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        # Curvature mu = [9.90, 6.20, 2.75, 12.00]
        # Guarantee: CVaR (12.00) > BL (9.90) > HERC (6.20) > RP (2.75)
        uniform_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_48_fisher_rao_barycenter_blend(uniform_weights)

        assert isinstance(res, dict)
        assert res["cvar"] > res["bl"], f"Expected cvar ({res['cvar']}) > bl ({res['bl']})"
        assert res["bl"] > res["herc"], f"Expected bl ({res['bl']}) > herc ({res['herc']})"
        assert res["herc"] > res["rp"], f"Expected herc ({res['herc']}) > rp ({res['rp']})"
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)

    def test_feature_f462_1_barycenter_input_types(self, allocator):
        # Test DataFrame/Array inputs
        df_weights = pd.DataFrame({
            "BL": [0.4, 0.6],
            "HERC": [0.5, 0.5],
            "RP": [0.3, 0.7],
            "CVaR": [0.45, 0.55],
        }, index=["A", "B"])

        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_48_fisher_rao_barycenter_blend(df_weights)
        assert isinstance(blended, (dict, pd.Series, np.ndarray))
        if isinstance(blended, dict):
            assert math.isclose(sum(blended.values()), 1.0, abs_tol=1e-5)

    def test_feature_f462_1_barycenter_aliases_and_delegation(self, allocator, portfolio_allocator):
        method_names = [
            "compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_48_fisher_rao_barycenter_blend",
            "compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_48_barycenter",
            "compute_lurie_drinfeld_higher_homology_48_barycenter",
            "compute_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_48_fisher_rao_barycenter",
            "compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_48_barycenter",
            "compute_phase98_barycenter",
            "compute_phase98_fisher_rao_barycenter",
            "compute_phase98_barycenter_blend",
            "compute_higher_homology_48_barycenter",
            "phase98_fisher_rao_barycenter",
            "higher_homology_48_blend",
            "compute_lmbmwdh48_fisher_rao_barycenter_blend",
            "phase98_barycenter_blend",
            "higher_homology_48_barycenter",
            "lmbmwdh48_barycenter",
            "compute_higher_homology_48_fisher_rao_barycenter",
            "higher_homology_48_fisher_rao_barycenter_blend",
            "lurie_borcherds_higher_homology_48_barycenter",
        ]
        w_dict = {"BL": {"A": 0.5, "B": 0.5}, "HERC": {"A": 0.4, "B": 0.6}, "RP": {"A": 0.3, "B": 0.7}, "CVaR": {"A": 0.6, "B": 0.4}}
        base_res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_48_fisher_rao_barycenter_blend(w_dict)

        for name in method_names:
            fn = getattr(allocator, name, None)
            assert fn is not None, f"Missing method {name} on UnifiedPortfolioAllocator"
            res = fn(w_dict)
            for k in base_res:
                assert math.isclose(base_res[k], res[k], abs_tol=1e-5)

        # PortfolioAllocator delegation
        pa_fn = getattr(portfolio_allocator, "compute_phase98_barycenter", None)
        assert pa_fn is not None, "Missing compute_phase98_barycenter on PortfolioAllocator"
        pa_res = pa_fn(w_dict)
        for k in base_res:
            assert math.isclose(base_res[k], pa_res[k], abs_tol=1e-5)

    def test_feature_f462_1_allocate_portfolio_dispatch(self, allocator):
        w_dict = {"BL": {"A": 0.5, "B": 0.5}, "HERC": {"A": 0.4, "B": 0.6}, "RP": {"A": 0.3, "B": 0.7}, "CVaR": {"A": 0.6, "B": 0.4}}
        res = allocator.allocate_portfolio(model_weights=w_dict)
        assert isinstance(res, dict)
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)

    def test_feature_f462_2_evar_risk_measure(self, allocator, portfolio_allocator):
        returns = np.array([-0.05, -0.02, 0.01, 0.03, -0.01, 0.02, -0.04, 0.015, -0.005, 0.025])
        evar_res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_48_evar_risk_measure(returns)

        evar_val = _extract_evar_val(evar_res)
        assert evar_val > 0.0

        if isinstance(evar_res, dict):
            assert evar_res.get("order", 128) == 128
            assert math.isclose(float(evar_res.get("xi_monster", 0.0)), 0.999999999999999999999999999999999, rel_tol=1e-12)
            assert "phase98_evar" in evar_res

    def test_feature_f462_2_evar_aliases_and_delegation(self, allocator, portfolio_allocator):
        returns = np.array([-0.05, -0.02, 0.01, 0.03, -0.01, 0.02, -0.04, 0.015, -0.005, 0.025])
        base_res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_48_evar_risk_measure(returns)
        evar_val = _extract_evar_val(base_res)

        # Aliases
        alias_names = [
            "compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_48_evar",
            "trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_48_evar_risk_measure",
            "compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_48_evar_blend",
            "compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_48_evar",
            "singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_48_evar_risk_measure",
            "compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_phase98",
            "compute_phase98_evar",
            "compute_phase98_evar_risk_measure",
            "phase98_evar_risk_measure",
            "compute_higher_homology_48_evar_risk_measure",
            "compute_higher_homology_48_evar",
            "compute_evar_order128",
            "compute_128th_cumulant_evar",
            "compute_monster_whittaker_128th_cumulant_evar",
            "compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_48_evar_risk_measure",
            "compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_48_evar_risk_measure",
            "compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_48_evar",
            "compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_48_evar",
            "compute_drinfeld_higher_homology_48_evar_risk_measure",
            "compute_drinfeld_higher_homology_48_evar",
            "compute_lurie_drinfeld_higher_homology_48_evar_risk_measure",
            "compute_lurie_drinfeld_higher_homology_48_evar",
            "calculate_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_evar_128th_cumulant",
            "evar_128th_cumulant",
            "trans_singular_128th_cumulant_evar",
            "eternal_omni_cosmic_128th_cumulant_evar",
            "supreme_transcendent_evar_128",
            "higher_homology_48_evar",
            "phase98_tail_risk_evar",
            "phase98_evar_bound",
            "compute_lmbmwdh48_evar",
            "lmbmwdh48_evar",
            "trans_singular_evar_v98",
        ]
        for name in alias_names:
            fn = getattr(allocator, name, None)
            assert fn is not None, f"Missing {name} on UnifiedPortfolioAllocator"
            res = fn(returns)
            val = _extract_evar_val(res)
            assert math.isclose(evar_val, val, rel_tol=1e-4)

        # PortfolioAllocator delegation
        pa_fn = getattr(portfolio_allocator, "compute_phase98_evar", None)
        assert pa_fn is not None, "Missing compute_phase98_evar on PortfolioAllocator"
        pa_res = pa_fn(returns)
        pa_val = _extract_evar_val(pa_res)
        assert math.isclose(evar_val, pa_val, rel_tol=1e-4)

    def test_backward_compatibility_v97_v96_v95(self):
        alloc_v97 = UnifiedPortfolioAllocator(version=97)
        assert alloc_v97.is_phase97 is True
        assert getattr(alloc_v97, "is_phase98", False) is False

        alloc_v96 = UnifiedPortfolioAllocator(version=96)
        assert alloc_v96.is_phase96 is True
        assert getattr(alloc_v96, "is_phase97", False) is False
        assert getattr(alloc_v96, "is_phase98", False) is False

        alloc_v95 = UnifiedPortfolioAllocator(version=95)
        assert alloc_v95.is_phase95 is True
        assert getattr(alloc_v95, "is_phase96", False) is False
        assert getattr(alloc_v95, "is_phase98", False) is False

        pa_v97 = PortfolioAllocator(version=97)
        assert pa_v97.is_phase97 is True
        assert getattr(pa_v97, "is_phase98", False) is False

    def test_module_level_exports(self):
        w_dict = {"BL": {"A": 0.5, "B": 0.5}, "HERC": {"A": 0.4, "B": 0.6}, "RP": {"A": 0.3, "B": 0.7}, "CVaR": {"A": 0.6, "B": 0.4}}
        res_blend = module_barycenter_blend(w_dict)
        assert isinstance(res_blend, dict)
        assert math.isclose(sum(res_blend.values()), 1.0, abs_tol=1e-5)

        res_p98_bary = module_phase98_barycenter(w_dict)
        assert isinstance(res_p98_bary, dict)
        assert math.isclose(sum(res_p98_bary.values()), 1.0, abs_tol=1e-5)

        returns = np.array([-0.05, -0.02, 0.01, 0.03, -0.01, 0.02, -0.04, 0.015, -0.005, 0.025])
        res_evar = module_evar_risk_measure(returns)
        assert _extract_evar_val(res_evar) > 0.0

        res_p98_evar = module_phase98_evar(returns)
        assert _extract_evar_val(res_p98_evar) > 0.0
