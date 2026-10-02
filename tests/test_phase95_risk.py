r"""
tests/test_phase95_risk.py

Unit test suite for Phase 95 Quantitative Risk Allocation Enhancement (v102 Production Master, Features F447.1, F447.2):
- Feature F447.1: Higher-Homology-45 Motivic Fisher-Rao Barycenter Blending
  (mu = [9.30, 5.75, 2.60, 11.25], simplex sum=1.0, heavy-tail CVaR prioritization: CVaR > BL > HERC > RP, tau = 0.0000035)
- Feature F447.2: 122nd-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
  (order=122, xi_monster = 0.999999999999999999999999999999 [30-nines + 9])
- UnifiedPortfolioAllocator with default version=95, is_phase95=True, is_phase94=True, is_phase93=True, is_phase92=True
- Strict backward compatibility with Phase 94, Phase 93, Phase 92, Phase 91 and earlier versions
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
        compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_45_fisher_rao_barycenter_blend as module_barycenter_blend,
        compute_phase95_barycenter as module_phase95_barycenter,
        compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_45_evar_risk_measure as module_evar_risk_measure,
        compute_phase95_evar as module_phase95_evar,
    )
except ImportError:
    import trading_system.src.risk.unified_portfolio_allocator as _upa

    def _missing_upa(name):
        val = getattr(_upa, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'unified_portfolio_allocator' has no Phase 95 attribute '{name}'")
        return _callable

    module_barycenter_blend = _missing_upa('compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_45_fisher_rao_barycenter_blend')
    module_phase95_barycenter = _missing_upa('compute_phase95_barycenter')
    module_evar_risk_measure = _missing_upa('compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_45_evar_risk_measure')
    module_phase95_evar = _missing_upa('compute_phase95_evar')


def _extract_evar_val(res):
    if isinstance(res, dict):
        for key in res:
            if 'evar' in key.lower() and ('value' in key.lower() or key.lower().endswith('evar')):
                return float(res[key])
        return float(res.get("evar", 0.0))
    return float(res)


class TestPhase95RiskAllocation:
    """Test suite for Phase 95 Risk Allocation, Higher-Homology-45 Barycenter Blending, and 122nd-Cumulant EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=95)

    @pytest.fixture
    def default_allocator(self):
        return UnifiedPortfolioAllocator()

    @pytest.fixture
    def portfolio_allocator(self):
        return PortfolioAllocator(version=95)

    def test_default_version_is_95(self, default_allocator):
        assert default_allocator.version == 95 or default_allocator.version >= 95
        assert getattr(default_allocator, "is_phase95", False) is True
        assert getattr(default_allocator, "is_phase94", False) is True
        assert getattr(default_allocator, "is_phase93", False) is True
        assert getattr(default_allocator, "is_phase92", False) is True

    def test_feature_f447_1_barycenter_blend_basic_properties(self, allocator):
        # 4 model inputs: BL, HERC, RP, CVaR
        w_bl = {"AAPL": 0.30, "MSFT": 0.40, "GOOGL": 0.30}
        w_herc = {"AAPL": 0.25, "MSFT": 0.45, "GOOGL": 0.30}
        w_rp = {"AAPL": 0.333, "MSFT": 0.334, "GOOGL": 0.333}
        w_cvar = {"AAPL": 0.20, "MSFT": 0.50, "GOOGL": 0.30}

        weights_dict = {"BL": w_bl, "HERC": w_herc, "RP": w_rp, "CVaR": w_cvar}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_45_fisher_rao_barycenter_blend(weights_dict)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"AAPL", "MSFT", "GOOGL"}
        total_weight = sum(blended.values())
        assert math.isclose(total_weight, 1.0, abs_tol=1e-5)
        for sym, w in blended.items():
            assert w >= 0.0

    def test_feature_f447_1_barycenter_input_types(self, allocator):
        # Test DataFrame/Array inputs
        df_weights = pd.DataFrame({
            "BL": [0.4, 0.6],
            "HERC": [0.5, 0.5],
            "RP": [0.3, 0.7],
            "CVaR": [0.45, 0.55],
        }, index=["A", "B"])

        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_45_fisher_rao_barycenter_blend(df_weights)
        assert isinstance(blended, (dict, pd.Series, np.ndarray))
        if isinstance(blended, dict):
            assert math.isclose(sum(blended.values()), 1.0, abs_tol=1e-5)

    def test_feature_f447_1_barycenter_aliases_and_delegation(self, allocator, portfolio_allocator):
        method_names = [
            "compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_45_fisher_rao_barycenter_blend",
            "compute_phase95_barycenter",
            "compute_phase95_fisher_rao_barycenter",
            "compute_higher_homology_45_barycenter",
            "higher_homology_45_blend",
            "phase95_barycenter_blend",
        ]
        w_dict = {"BL": {"A": 0.5, "B": 0.5}, "HERC": {"A": 0.4, "B": 0.6}, "RP": {"A": 0.3, "B": 0.7}, "CVaR": {"A": 0.6, "B": 0.4}}
        base_res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_45_fisher_rao_barycenter_blend(w_dict)

        for name in method_names:
            fn = getattr(allocator, name, None)
            assert fn is not None, f"Missing method {name} on UnifiedPortfolioAllocator"
            res = fn(w_dict)
            for k in base_res:
                assert math.isclose(base_res[k], res[k], abs_tol=1e-5)

        # PortfolioAllocator delegation
        pa_fn = getattr(portfolio_allocator, "compute_phase95_barycenter", None)
        assert pa_fn is not None
        pa_res = pa_fn(w_dict)
        for k in base_res:
            assert math.isclose(base_res[k], pa_res[k], abs_tol=1e-5)

    def test_feature_f447_2_evar_risk_measure(self, allocator, portfolio_allocator):
        returns = np.array([-0.05, -0.02, 0.01, 0.03, -0.01, 0.02, -0.04, 0.015, -0.005, 0.025])
        evar_res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_45_evar_risk_measure(returns)

        evar_val = _extract_evar_val(evar_res)
        assert evar_val > 0.0

        if isinstance(evar_res, dict):
            assert evar_res.get("order", 122) == 122

        # Aliases
        alias_names = [
            "compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_45_evar_risk_measure",
            "compute_phase95_evar",
            "compute_evar_order122",
            "compute_122nd_cumulant_evar",
            "higher_homology_45_evar",
            "phase95_tail_risk_evar",
        ]
        for name in alias_names:
            fn = getattr(allocator, name, None)
            assert fn is not None, f"Missing {name} on UnifiedPortfolioAllocator"
            res = fn(returns)
            val = _extract_evar_val(res)
            assert math.isclose(evar_val, val, rel_tol=1e-4)

    def test_backward_compatibility_v94_v93_v92(self):
        alloc_v94 = UnifiedPortfolioAllocator(version=94)
        assert alloc_v94.is_phase94 is True
        assert getattr(alloc_v94, "is_phase95", False) is False

        alloc_v93 = UnifiedPortfolioAllocator(version=93)
        assert alloc_v93.is_phase93 is True
        assert getattr(alloc_v93, "is_phase94", False) is False

        alloc_v92 = UnifiedPortfolioAllocator(version=92)
        assert alloc_v92.is_phase92 is True
        assert getattr(alloc_v92, "is_phase93", False) is False
