r"""
tests/test_phase101_risk.py

Unit test suite for Phase 101 Multi-Factor & Multi-Model Risk & Allocation Enhancements
(Features F477.1, F477.2):
- Feature F477.1: Higher-Homology-51 Motivic Fisher-Rao Barycenter Blending
  (mu = [10.50, 6.65, 2.90, 12.75], simplex sum=1.0, heavy-tail CVaR prioritization: CVaR > BL > HERC > RP, tau = 1.0e-6,
   gradient clipping [-100.0, 100.0])
- Feature F477.1: Sideways Cash Drag Release in scale_target_volatility (0.85 -> 0.95 cap in SIDEWAYS_LOW_VOL when expected return > 0)
- Feature F477.1: Dynamic CVaR Budget Scaling in optimize_with_evt_cvar_constraint and optimize_cvar_with_turnover
- Feature F477.2: 134th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
  (order=134, xi_monster = 0.9999999999999999999999999999999999999 [37-nines])
- UnifiedPortfolioAllocator & PortfolioAllocator with default version=101, is_phase101=True, cascading backward to is_phase100..is_phase92=True
- Strict backward compatibility with Phase 100, Phase 99, Phase 98 and earlier versions
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
        compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_51_fisher_rao_barycenter_blend as module_barycenter_blend,
        compute_phase101_barycenter as module_phase101_barycenter,
        compute_phase101_barycenter_blend as module_phase101_barycenter_blend,
        phase101_barycenter_blend as module_alias_p101_barycenter_blend,
        higher_homology_51_barycenter as module_alias_h51_barycenter,
        lmbmwdh51_barycenter as module_alias_lmbmwdh51_barycenter,
        compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_51_evar_risk_measure as module_evar_risk_measure,
        compute_phase101_evar as module_phase101_evar,
        phase101_evar_risk_measure as module_alias_phase101_evar_risk_measure,
        trans_singular_evar_v101 as module_alias_trans_singular_evar_v101,
    )
except ImportError:
    import trading_system.src.risk.unified_portfolio_allocator as _upa

    def _missing_upa(name):
        val = getattr(_upa, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'unified_portfolio_allocator' has no Phase 101 attribute '{name}'")
        return _callable

    module_barycenter_blend = _missing_upa('compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_51_fisher_rao_barycenter_blend')
    module_phase101_barycenter = _missing_upa('compute_phase101_barycenter')
    module_phase101_barycenter_blend = _missing_upa('compute_phase101_barycenter_blend')
    module_alias_p101_barycenter_blend = _missing_upa('phase101_barycenter_blend')
    module_alias_h51_barycenter = _missing_upa('higher_homology_51_barycenter')
    module_alias_lmbmwdh51_barycenter = _missing_upa('lmbmwdh51_barycenter')
    module_evar_risk_measure = _missing_upa('compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_51_evar_risk_measure')
    module_phase101_evar = _missing_upa('compute_phase101_evar')
    module_alias_phase101_evar_risk_measure = _missing_upa('phase101_evar_risk_measure')
    module_alias_trans_singular_evar_v101 = _missing_upa('trans_singular_evar_v101')


def _extract_evar_val(res):
    if isinstance(res, dict):
        for key in res:
            if 'evar' in key.lower() and ('value' in key.lower() or key.lower().endswith('evar')):
                return float(res[key])
        return float(res.get("evar", 0.0))
    return float(res)


class TestPhase101RiskAllocation:
    """Comprehensive test suite for Phase 101 Risk Allocation, Higher-Homology-51 Barycenter, and 134th-Cumulant EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=101)

    @pytest.fixture
    def default_allocator(self):
        return UnifiedPortfolioAllocator()

    @pytest.fixture
    def portfolio_allocator(self):
        return PortfolioAllocator(version=101)

    @pytest.fixture
    def default_portfolio_allocator(self):
        return PortfolioAllocator()

    def test_default_version_is_101(self, default_allocator, default_portfolio_allocator):
        # 1. Version cascading on UnifiedPortfolioAllocator
        assert default_allocator.version >= 101
        assert getattr(default_allocator, "is_phase101", False) is True
        assert getattr(default_allocator, "is_phase100", False) is True
        assert getattr(default_allocator, "is_phase99", False) is True
        assert getattr(default_allocator, "is_phase98", False) is True
        assert getattr(default_allocator, "is_phase97", False) is True
        assert getattr(default_allocator, "is_phase96", False) is True
        assert getattr(default_allocator, "is_phase95", False) is True
        assert getattr(default_allocator, "is_phase94", False) is True
        assert getattr(default_allocator, "is_phase93", False) is True
        assert getattr(default_allocator, "is_phase92", False) is True

        # 2. Version cascading on PortfolioAllocator
        assert default_portfolio_allocator.version >= 101
        assert getattr(default_portfolio_allocator, "is_phase101", False) is True
        assert getattr(default_portfolio_allocator, "is_phase100", False) is True
        assert getattr(default_portfolio_allocator, "is_phase99", False) is True
        assert getattr(default_portfolio_allocator, "is_phase98", False) is True

    def test_feature_f477_1_barycenter_blend_basic_properties(self, allocator):
        # 4 model inputs: BL, HERC, RP, CVaR
        w_bl = {"AAPL": 0.30, "MSFT": 0.40, "GOOGL": 0.30}
        w_herc = {"AAPL": 0.25, "MSFT": 0.45, "GOOGL": 0.30}
        w_rp = {"AAPL": 0.333, "MSFT": 0.334, "GOOGL": 0.333}
        w_cvar = {"AAPL": 0.20, "MSFT": 0.50, "GOOGL": 0.30}

        weights_dict = {"BL": w_bl, "HERC": w_herc, "RP": w_rp, "CVaR": w_cvar}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_51_fisher_rao_barycenter_blend(weights_dict)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"AAPL", "MSFT", "GOOGL"}
        total_weight = sum(blended.values())
        assert math.isclose(total_weight, 1.0, abs_tol=1e-5)
        for sym, w in blended.items():
            assert w >= 0.0

    def test_feature_f477_1_barycenter_curvature_hierarchy(self, allocator):
        # Uniform model weights: {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        # Curvature mu_lmbmwdh51 = [10.50, 6.65, 2.90, 12.75]
        # Guarantee: CVaR (12.75) > BL (10.50) > HERC (6.65) > RP (2.90)
        uniform_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_51_fisher_rao_barycenter_blend(uniform_weights)

        assert isinstance(res, dict)
        assert res["cvar"] > res["bl"], f"Expected cvar ({res['cvar']}) > bl ({res['bl']})"
        assert res["bl"] > res["herc"], f"Expected bl ({res['bl']}) > herc ({res['herc']})"
        assert res["herc"] > res["rp"], f"Expected herc ({res['herc']}) > rp ({res['rp']})"
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)
        # Check simplex lower bound tau = 1.0e-6
        for k, v in res.items():
            assert v >= 1.0e-6, f"Weight for {k} ({v}) below tau lower bound 1.0e-6"

    def test_feature_f477_1_barycenter_input_types(self, allocator):
        # Test DataFrame inputs
        df_weights = pd.DataFrame({
            "BL": [0.4, 0.6],
            "HERC": [0.5, 0.5],
            "RP": [0.3, 0.7],
            "CVaR": [0.45, 0.55],
        }, index=["A", "B"])

        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_51_fisher_rao_barycenter_blend(df_weights)
        assert isinstance(blended, (dict, pd.Series, np.ndarray))
        if isinstance(blended, dict):
            assert math.isclose(sum(blended.values()), 1.0, abs_tol=1e-5)

        # Test list of dicts
        list_weights = [
            {"bl": 0.3, "herc": 0.3, "rp": 0.2, "cvar": 0.2},
            {"bl": 0.4, "herc": 0.2, "rp": 0.1, "cvar": 0.3},
        ]
        res_list = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_51_fisher_rao_barycenter_blend(list_weights)
        assert isinstance(res_list, dict)
        assert math.isclose(sum(res_list.values()), 1.0, abs_tol=1e-5)

        # Test numpy 1D array
        arr_1d = np.array([0.25, 0.25, 0.25, 0.25])
        res_arr = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_51_fisher_rao_barycenter_blend(arr_1d)
        assert isinstance(res_arr, dict)
        assert math.isclose(sum(res_arr.values()), 1.0, abs_tol=1e-5)

    def test_feature_f477_1_barycenter_all_17_aliases_and_delegation(self, allocator, portfolio_allocator):
        method_names = [
            "compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_51_fisher_rao_barycenter_blend",
            "compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_51_barycenter",
            "compute_lurie_drinfeld_higher_homology_51_barycenter",
            "compute_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_51_fisher_rao_barycenter",
            "compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_51_barycenter",
            "compute_phase101_barycenter",
            "compute_phase101_fisher_rao_barycenter",
            "compute_phase101_barycenter_blend",
            "compute_higher_homology_51_barycenter",
            "phase101_fisher_rao_barycenter",
            "higher_homology_51_blend",
            "compute_lmbmwdh51_fisher_rao_barycenter_blend",
            "phase101_barycenter_blend",
            "higher_homology_51_barycenter",
            "lmbmwdh51_barycenter",
            "compute_higher_homology_51_fisher_rao_barycenter",
            "higher_homology_51_fisher_rao_barycenter_blend",
            "lurie_borcherds_higher_homology_51_barycenter",
        ]
        w_dict = {"BL": {"A": 0.5, "B": 0.5}, "HERC": {"A": 0.4, "B": 0.6}, "RP": {"A": 0.3, "B": 0.7}, "CVaR": {"A": 0.6, "B": 0.4}}
        base_res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_51_fisher_rao_barycenter_blend(w_dict)

        for name in method_names:
            fn = getattr(allocator, name, None)
            assert fn is not None, f"Missing method {name} on UnifiedPortfolioAllocator"
            res = fn(w_dict)
            for k in base_res:
                assert math.isclose(base_res[k], res[k], abs_tol=1e-5)

        # PortfolioAllocator delegation for all aliases
        for name in method_names:
            pa_fn = getattr(portfolio_allocator, name, None)
            assert pa_fn is not None, f"Missing method {name} on PortfolioAllocator"
            pa_res = pa_fn(w_dict)
            for k in base_res:
                assert math.isclose(base_res[k], pa_res[k], abs_tol=1e-5)

    def test_feature_f477_1_optimize_multi_model_blend_dispatch(self, allocator):
        symbols = ["AAPL", "MSFT", "GOOGL"]
        predicted_returns = np.array([0.15, 0.12, 0.10])
        returns_df = pd.DataFrame(
            np.random.RandomState(42).randn(60, 3) * 0.01,
            columns=symbols
        )
        cov_matrix = np.array([
            [0.04, 0.01, 0.01],
            [0.01, 0.03, 0.01],
            [0.01, 0.01, 0.02],
        ])
        res = allocator.optimize_multi_model_blend(
            predicted_returns=predicted_returns,
            returns_df=returns_df,
            cov_matrix=cov_matrix,
            symbols=symbols,
        )
        assert isinstance(res, (np.ndarray, dict))
        if isinstance(res, np.ndarray):
            assert math.isclose(float(np.sum(res)), 1.0, abs_tol=1e-4)
            assert len(res) == len(symbols)
        else:
            assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-4)

    def test_feature_f477_1_allocate_portfolio_dispatch(self, allocator):
        w_dict = {"BL": {"A": 0.5, "B": 0.5}, "HERC": {"A": 0.4, "B": 0.6}, "RP": {"A": 0.3, "B": 0.7}, "CVaR": {"A": 0.6, "B": 0.4}}
        res = allocator.allocate_portfolio(model_weights=w_dict)
        assert isinstance(res, dict)
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)

    def test_feature_f477_1_sideways_cash_drag_release(self, allocator):
        # In SIDEWAYS_LOW_VOL regime with expected returns > 0, cap is relaxed from 0.85 to 0.95
        weights = np.array([0.5, 0.5])
        # Daily cov matrix corresponding to ~3.9% annualized vol: (0.000006 * 252) ** 0.5 ~ 0.0388
        cov_matrix = np.diag([0.000006, 0.000006])
        exp_ret_pos = np.array([0.05, 0.04])
        exp_ret_neg = np.array([-0.05, -0.04])

        # Phase 101 with positive expected return -> relaxed cap 0.95
        scaled_w_p101_pos, alloc_ratio_p101_pos = allocator.scale_target_volatility(
            weights=weights,
            cov_matrix=cov_matrix,
            regime="SIDEWAYS_LOW_VOL",
            expected_returns=exp_ret_pos,
        )
        assert alloc_ratio_p101_pos > 0.85, f"Expected alloc_ratio > 0.85, got {alloc_ratio_p101_pos}"
        assert math.isclose(alloc_ratio_p101_pos, 0.95, abs_tol=1e-4)

        # Phase 101 with negative expected return -> should retain standard 0.85 cap
        scaled_w_p101_neg, alloc_ratio_p101_neg = allocator.scale_target_volatility(
            weights=weights,
            cov_matrix=cov_matrix,
            regime="SIDEWAYS_LOW_VOL",
            expected_returns=exp_ret_neg,
        )
        assert alloc_ratio_p101_neg <= 0.85, f"Expected alloc_ratio <= 0.85, got {alloc_ratio_p101_neg}"

        # Phase 100 allocator -> should retain 0.85 cap even with positive expected return
        alloc_p100 = UnifiedPortfolioAllocator(version=100)
        scaled_w_p100, alloc_ratio_p100 = alloc_p100.scale_target_volatility(
            weights=weights,
            cov_matrix=cov_matrix,
            regime="SIDEWAYS_LOW_VOL",
            expected_returns=exp_ret_pos,
        )
        assert alloc_ratio_p100 <= 0.85, f"Expected Phase 100 alloc_ratio <= 0.85, got {alloc_ratio_p100}"

    def test_feature_f477_1_dynamic_cvar_budget_scaling(self, portfolio_allocator):
        # Test dynamic CVaR budget scaling in optimize_with_evt_cvar_constraint
        expected_returns = pd.Series([0.10, 0.08, 0.06], index=["A", "B", "C"])
        returns_df = pd.DataFrame(
            np.random.RandomState(42).randn(100, 3) * 0.01,
            columns=["A", "B", "C"]
        )

        # 1. Default optimization with dynamic CVaR budget scaling
        weights = portfolio_allocator.optimize_with_evt_cvar_constraint(
            expected_returns=expected_returns,
            returns_df=returns_df,
            max_cvar=0.04,  # default tight budget that triggers dynamic scaling
        )
        assert isinstance(weights, dict)
        assert len(weights) == 3
        assert math.isclose(sum(weights.values()), 1.0, abs_tol=1e-4)

        # 2. Explicit large user max_cvar is preserved
        weights_user = portfolio_allocator.optimize_with_evt_cvar_constraint(
            expected_returns=expected_returns,
            returns_df=returns_df,
            max_cvar=0.08,  # > 0.05 custom explicit budget
        )
        assert isinstance(weights_user, dict)
        assert math.isclose(sum(weights_user.values()), 1.0, abs_tol=1e-4)

        # 3. Dynamic budget scaling in optimize_cvar_with_turnover
        turnover_weights = portfolio_allocator.optimize_cvar_with_turnover(
            expected_returns=expected_returns,
            historical_returns=returns_df,
            max_cvar_limit=0.04,
        )
        assert isinstance(turnover_weights, dict)
        assert math.isclose(sum(turnover_weights.values()), 1.0, abs_tol=1e-4)

    def test_feature_f477_2_evar_risk_measure(self, allocator, portfolio_allocator):
        returns = np.array([-0.05, -0.02, 0.01, 0.03, -0.01, 0.02, -0.04, 0.015, -0.005, 0.025])
        evar_res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_51_evar_risk_measure(returns)

        evar_val = _extract_evar_val(evar_res)
        assert evar_val > 0.0

        if isinstance(evar_res, dict):
            assert evar_res.get("order", 134) == 134
            assert math.isclose(float(evar_res.get("xi_monster", 0.0)), 1.0, abs_tol=1e-12)
            assert "phase101_evar" in evar_res

    def test_feature_f477_2_evar_all_33_aliases_and_delegation(self, allocator, portfolio_allocator):
        returns = np.array([-0.05, -0.02, 0.01, 0.03, -0.01, 0.02, -0.04, 0.015, -0.005, 0.025])
        base_res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_51_evar_risk_measure(returns)
        evar_val = _extract_evar_val(base_res)

        alias_names = [
            "compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_51_evar",
            "trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_51_evar_risk_measure",
            "compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_51_evar_blend",
            "compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_51_evar",
            "singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_51_evar_risk_measure",
            "compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_phase101",
            "compute_phase101_evar",
            "compute_phase101_evar_risk_measure",
            "phase101_evar_risk_measure",
            "compute_higher_homology_51_evar_risk_measure",
            "compute_higher_homology_51_evar",
            "compute_evar_order134",
            "compute_134th_cumulant_evar",
            "compute_monster_whittaker_134th_cumulant_evar",
            "compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_51_evar_risk_measure",
            "compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_51_evar_risk_measure",
            "compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_51_evar",
            "compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_51_evar",
            "compute_drinfeld_higher_homology_51_evar_risk_measure",
            "compute_drinfeld_higher_homology_51_evar",
            "compute_lurie_drinfeld_higher_homology_51_evar_risk_measure",
            "compute_lurie_drinfeld_higher_homology_51_evar",
            "calculate_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_evar_134th_cumulant",
            "evar_134th_cumulant",
            "trans_singular_134th_cumulant_evar",
            "eternal_omni_cosmic_134th_cumulant_evar",
            "supreme_transcendent_evar_134",
            "higher_homology_51_evar",
            "phase101_tail_risk_evar",
            "phase101_evar_bound",
            "compute_lmbmwdh51_evar",
            "lmbmwdh51_evar",
            "trans_singular_evar_v101",
        ]
        assert len(alias_names) == 33, f"Expected 33 aliases, got {len(alias_names)}"

        # Check on UnifiedPortfolioAllocator
        for name in alias_names:
            fn = getattr(allocator, name, None)
            assert fn is not None, f"Missing {name} on UnifiedPortfolioAllocator"
            res = fn(returns)
            val = _extract_evar_val(res)
            assert math.isclose(evar_val, val, rel_tol=1e-4)

        # Check on PortfolioAllocator
        for name in alias_names:
            pa_fn = getattr(portfolio_allocator, name, None)
            assert pa_fn is not None, f"Missing {name} on PortfolioAllocator"
            pa_res = pa_fn(returns)
            pa_val = _extract_evar_val(pa_res)
            assert math.isclose(evar_val, pa_val, rel_tol=1e-4)

    def test_backward_compatibility_v100_v99_v98(self):
        alloc_v100 = UnifiedPortfolioAllocator(version=100)
        assert alloc_v100.is_phase100 is True
        assert getattr(alloc_v100, "is_phase101", False) is False

        alloc_v99 = UnifiedPortfolioAllocator(version=99)
        assert alloc_v99.is_phase99 is True
        assert getattr(alloc_v99, "is_phase100", False) is False
        assert getattr(alloc_v99, "is_phase101", False) is False

        alloc_v98 = UnifiedPortfolioAllocator(version=98)
        assert alloc_v98.is_phase98 is True
        assert getattr(alloc_v98, "is_phase99", False) is False
        assert getattr(alloc_v98, "is_phase100", False) is False
        assert getattr(alloc_v98, "is_phase101", False) is False

        pa_v100 = PortfolioAllocator(version=100)
        assert pa_v100.is_phase100 is True
        assert getattr(pa_v100, "is_phase101", False) is False

        pa_v99 = PortfolioAllocator(version=99)
        assert pa_v99.is_phase99 is True
        assert getattr(pa_v99, "is_phase100", False) is False
        assert getattr(pa_v99, "is_phase101", False) is False

        pa_v98 = PortfolioAllocator(version=98)
        assert pa_v98.is_phase98 is True
        assert getattr(pa_v98, "is_phase99", False) is False
        assert getattr(pa_v98, "is_phase100", False) is False
        assert getattr(pa_v98, "is_phase101", False) is False

    def test_module_level_exports(self):
        w_dict = {"BL": {"A": 0.5, "B": 0.5}, "HERC": {"A": 0.4, "B": 0.6}, "RP": {"A": 0.3, "B": 0.7}, "CVaR": {"A": 0.6, "B": 0.4}}
        res_blend = module_barycenter_blend(w_dict)
        assert isinstance(res_blend, dict)
        assert math.isclose(sum(res_blend.values()), 1.0, abs_tol=1e-5)

        res_p101_bary = module_phase101_barycenter(w_dict)
        assert isinstance(res_p101_bary, dict)
        assert math.isclose(sum(res_p101_bary.values()), 1.0, abs_tol=1e-5)

        res_p101_blend_alias = module_phase101_barycenter_blend(w_dict)
        assert isinstance(res_p101_blend_alias, dict)
        assert math.isclose(sum(res_p101_blend_alias.values()), 1.0, abs_tol=1e-5)

        res_p101_alias = module_alias_p101_barycenter_blend(w_dict)
        assert isinstance(res_p101_alias, dict)
        assert math.isclose(sum(res_p101_alias.values()), 1.0, abs_tol=1e-5)

        res_h51 = module_alias_h51_barycenter(w_dict)
        assert isinstance(res_h51, dict)
        assert math.isclose(sum(res_h51.values()), 1.0, abs_tol=1e-5)

        res_lmb = module_alias_lmbmwdh51_barycenter(w_dict)
        assert isinstance(res_lmb, dict)
        assert math.isclose(sum(res_lmb.values()), 1.0, abs_tol=1e-5)

        returns = np.array([-0.05, -0.02, 0.01, 0.03, -0.01, 0.02, -0.04, 0.015, -0.005, 0.025])
        res_evar = module_evar_risk_measure(returns)
        assert _extract_evar_val(res_evar) > 0.0

        res_p101_evar = module_phase101_evar(returns)
        assert _extract_evar_val(res_p101_evar) > 0.0

        res_p101_evar_alias = module_alias_phase101_evar_risk_measure(returns)
        assert _extract_evar_val(res_p101_evar_alias) > 0.0

        res_trans_alias = module_alias_trans_singular_evar_v101(returns)
        assert _extract_evar_val(res_trans_alias) > 0.0

        import trading_system.src.risk.unified_portfolio_allocator as upa_mod
        expected_exports = [
            "compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_51_fisher_rao_barycenter_blend",
            "compute_phase101_barycenter",
            "compute_phase101_barycenter_blend",
            "phase101_barycenter_blend",
            "higher_homology_51_barycenter",
            "lmbmwdh51_barycenter",
            "compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_51_evar_risk_measure",
            "compute_phase101_evar",
            "phase101_evar_risk_measure",
            "trans_singular_evar_v101",
        ]
        for exp in expected_exports:
            assert exp in upa_mod.__all__, f"{exp} missing from __all__"

    def test_numerical_stability_extreme_gradient_clipping(self, allocator):
        # Extreme skewed weights to test gradient clipping and tau lower bound (tau = 1.0e-6)
        skewed_weights = {"bl": 1e-15, "herc": 1e-15, "rp": 1e-15, "cvar": 0.999999999999}
        res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_51_fisher_rao_barycenter_blend(skewed_weights)
        assert isinstance(res, dict)
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)
        for k, v in res.items():
            assert not math.isnan(v)
            assert not math.isinf(v)
            assert v >= 1.0e-6
