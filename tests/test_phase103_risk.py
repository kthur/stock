r"""
tests/test_phase103_risk.py

Unit test suite for Phase 103 Multi-Factor & Multi-Model Risk & Allocation Enhancements
(Features F487.1, F487.2):
- Feature F487.1: Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology-53 Motivic Fisher-Rao Barycenter Blending
  (mu = [10.90, 6.95, 3.00, 13.25], simplex sum=1.000000, heavy-tail CVaR prioritization: CVaR > BL > HERC > RP,
   tau = 0.6e-6, gradient clipping [-100.0, 100.0], Sortino ratio HERC weighting)
- Feature F487.1: Waterfall Capital Redistribution (redistribute_waterfall_capital / phase103_waterfall_capital_redistribution)
  Redistributes unallocated capital from liquidity/position constrained assets to unconstrained
  candidate assets in alpha priority order to eliminate idle cash drag under ADV liquidity limits.
- Feature F487.2: 138th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
  (order=138, xi_monster = 1.0 - 10^-39 [39-nines], phase103_evar key)
- UnifiedPortfolioAllocator & PortfolioAllocator with default version=103, is_phase103=True, cascading backward
- Strict backward compatibility with Phase 102, Phase 101, Phase 100, Phase 99 and earlier versions
- Class and module level alias trees verification (17 barycenter + 5 waterfall + 33 EVaR aliases) for UnifiedPortfolioAllocator and PortfolioAllocator
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator

try:
    from trading_system.src.risk.unified_portfolio_allocator import (
        compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_53_fisher_rao_barycenter_blend as module_barycenter_blend,
        compute_phase103_barycenter as module_phase103_barycenter,
        compute_phase103_barycenter_blend as module_phase103_barycenter_blend,
        phase103_barycenter_blend as module_alias_p103_barycenter_blend,
        higher_homology_53_barycenter as module_alias_h53_barycenter,
        lmbmwdh53_barycenter as module_alias_lmbmwdh53_barycenter,
        compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar_risk_measure as module_evar_risk_measure,
        compute_phase103_evar as module_phase103_evar,
        phase103_evar_risk_measure as module_alias_phase103_evar_risk_measure,
        trans_singular_evar_v103 as module_alias_trans_singular_evar_v103,
        redistribute_waterfall_capital as module_redistribute_waterfall_capital,
        phase103_waterfall_capital_redistribution as module_phase103_waterfall_capital_redistribution,
    )
except ImportError:
    import trading_system.src.risk.unified_portfolio_allocator as _upa

    def _missing_upa(name):
        val = getattr(_upa, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'unified_portfolio_allocator' has no Phase 103 attribute '{name}'")
        return _callable

    module_barycenter_blend = _missing_upa('compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_53_fisher_rao_barycenter_blend')
    module_phase103_barycenter = _missing_upa('compute_phase103_barycenter')
    module_phase103_barycenter_blend = _missing_upa('compute_phase103_barycenter_blend')
    module_alias_p103_barycenter_blend = _missing_upa('phase103_barycenter_blend')
    module_alias_h53_barycenter = _missing_upa('higher_homology_53_barycenter')
    module_alias_lmbmwdh53_barycenter = _missing_upa('lmbmwdh53_barycenter')
    module_evar_risk_measure = _missing_upa('compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar_risk_measure')
    module_phase103_evar = _missing_upa('compute_phase103_evar')
    module_alias_phase103_evar_risk_measure = _missing_upa('phase103_evar_risk_measure')
    module_alias_trans_singular_evar_v103 = _missing_upa('trans_singular_evar_v103')
    module_redistribute_waterfall_capital = _missing_upa('redistribute_waterfall_capital')
    module_phase103_waterfall_capital_redistribution = _missing_upa('phase103_waterfall_capital_redistribution')


def _extract_evar_val(res):
    if isinstance(res, dict):
        for key in res:
            if 'evar' in key.lower() and ('value' in key.lower() or key.lower().endswith('evar')):
                return float(res[key])
        return float(res.get("evar", 0.0))
    return float(res)


class TestPhase103RiskAllocation:
    """Comprehensive test suite for Phase 103 Risk Allocation, Higher-Homology-53 Barycenter, EVaR order 138, and Waterfall Redistribution."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=103)

    @pytest.fixture
    def default_allocator(self):
        return UnifiedPortfolioAllocator()

    @pytest.fixture
    def portfolio_allocator(self):
        return PortfolioAllocator(version=103)

    @pytest.fixture
    def default_portfolio_allocator(self):
        return PortfolioAllocator()

    def test_default_version_is_103(self, default_allocator, default_portfolio_allocator):
        # 1. Version cascading on UnifiedPortfolioAllocator
        assert default_allocator.version >= 103
        assert getattr(default_allocator, "is_phase103", False) is True
        assert getattr(default_allocator, "is_phase102", False) is True
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
        assert default_portfolio_allocator.version >= 103
        assert getattr(default_portfolio_allocator, "is_phase103", False) is True
        assert getattr(default_portfolio_allocator, "is_phase102", False) is True
        assert getattr(default_portfolio_allocator, "is_phase101", False) is True
        assert getattr(default_portfolio_allocator, "is_phase100", False) is True
        assert getattr(default_portfolio_allocator, "is_phase99", False) is True
        assert getattr(default_portfolio_allocator, "is_phase98", False) is True

    def test_feature_f487_1_barycenter_blend_basic_properties(self, allocator):
        # 4 model inputs: BL, HERC, RP, CVaR
        w_bl = {"AAPL": 0.30, "MSFT": 0.40, "GOOGL": 0.30}
        w_herc = {"AAPL": 0.25, "MSFT": 0.45, "GOOGL": 0.30}
        w_rp = {"AAPL": 0.333, "MSFT": 0.334, "GOOGL": 0.333}
        w_cvar = {"AAPL": 0.20, "MSFT": 0.50, "GOOGL": 0.30}

        weights_dict = {"BL": w_bl, "HERC": w_herc, "RP": w_rp, "CVaR": w_cvar}
        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_53_fisher_rao_barycenter_blend(weights_dict)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"AAPL", "MSFT", "GOOGL"}
        total_weight = sum(blended.values())
        assert math.isclose(total_weight, 1.0, abs_tol=1e-5)
        for sym, w in blended.items():
            assert w >= 0.0

    def test_feature_f487_1_barycenter_curvature_hierarchy(self, allocator):
        # Uniform model weights: {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        # Curvature mu_lmbmwdh53 = [10.90, 6.95, 3.00, 13.25]
        # Guarantee: CVaR (13.25) > BL (10.90) > HERC (6.95) > RP (3.00)
        uniform_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_53_fisher_rao_barycenter_blend(uniform_weights)

        assert isinstance(res, dict)
        assert res["cvar"] > res["bl"], f"Expected cvar ({res['cvar']}) > bl ({res['bl']})"
        assert res["bl"] > res["herc"], f"Expected bl ({res['bl']}) > herc ({res['herc']})"
        assert res["herc"] > res["rp"], f"Expected herc ({res['herc']}) > rp ({res['rp']})"
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)
        # Check simplex lower bound tau = 0.6e-6
        for k, v in res.items():
            assert v >= 0.6e-6, f"Weight for {k} ({v}) below tau lower bound 0.6e-6"

    def test_feature_f487_1_barycenter_input_types(self, allocator):
        # Test DataFrame inputs
        df_weights = pd.DataFrame({
            "BL": [0.4, 0.6],
            "HERC": [0.5, 0.5],
            "RP": [0.3, 0.7],
            "CVaR": [0.45, 0.55],
        }, index=["A", "B"])

        blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_53_fisher_rao_barycenter_blend(df_weights)
        assert isinstance(blended, (dict, pd.Series, np.ndarray))
        if isinstance(blended, dict):
            assert math.isclose(sum(blended.values()), 1.0, abs_tol=1e-5)

        # Test list of dicts
        list_weights = [
            {"bl": 0.3, "herc": 0.3, "rp": 0.2, "cvar": 0.2},
            {"bl": 0.4, "herc": 0.2, "rp": 0.1, "cvar": 0.3},
        ]
        res_list = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_53_fisher_rao_barycenter_blend(list_weights)
        assert isinstance(res_list, dict)
        assert math.isclose(sum(res_list.values()), 1.0, abs_tol=1e-5)

        # Test numpy 1D array
        arr_1d = np.array([0.25, 0.25, 0.25, 0.25])
        res_arr = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_53_fisher_rao_barycenter_blend(arr_1d)
        assert isinstance(res_arr, dict)
        assert math.isclose(sum(res_arr.values()), 1.0, abs_tol=1e-5)

    def test_feature_f487_1_barycenter_all_17_aliases_and_delegation(self, allocator, portfolio_allocator):
        method_names = [
            "compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_53_fisher_rao_barycenter_blend",
            "compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_53_barycenter",
            "compute_lurie_drinfeld_higher_homology_53_barycenter",
            "compute_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_53_fisher_rao_barycenter",
            "compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_barycenter",
            "compute_phase103_barycenter",
            "compute_phase103_fisher_rao_barycenter",
            "compute_phase103_barycenter_blend",
            "compute_higher_homology_53_barycenter",
            "phase103_fisher_rao_barycenter",
            "higher_homology_53_blend",
            "compute_lmbmwdh53_fisher_rao_barycenter_blend",
            "phase103_barycenter_blend",
            "higher_homology_53_barycenter",
            "lmbmwdh53_barycenter",
            "compute_higher_homology_53_fisher_rao_barycenter",
            "higher_homology_53_fisher_rao_barycenter_blend",
            "lurie_borcherds_higher_homology_53_barycenter",
        ]
        w_dict = {"BL": {"A": 0.5, "B": 0.5}, "HERC": {"A": 0.4, "B": 0.6}, "RP": {"A": 0.3, "B": 0.7}, "CVaR": {"A": 0.6, "B": 0.4}}
        base_res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_53_fisher_rao_barycenter_blend(w_dict)

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

    def test_feature_f487_1_optimize_multi_model_blend_dispatch(self, allocator):
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

    def test_feature_f487_1_allocate_portfolio_dispatch(self, allocator):
        w_dict = {"BL": {"A": 0.5, "B": 0.5}, "HERC": {"A": 0.4, "B": 0.6}, "RP": {"A": 0.3, "B": 0.7}, "CVaR": {"A": 0.6, "B": 0.4}}
        res = allocator.allocate_portfolio(model_weights=w_dict)
        assert isinstance(res, dict)
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)

    def test_feature_f487_1_herc_sortino_ratio_weighting(self, allocator):
        symbols = ["AAPL", "MSFT", "GOOGL"]
        predicted_returns = np.array([0.15, 0.12, 0.10])
        # Generate skewed returns where one asset has severe downside semi-variance
        rng = np.random.RandomState(103)
        returns_data = rng.randn(100, 3) * 0.01
        # Inject downside shocks into GOOGL
        returns_data[:20, 2] -= 0.05
        returns_df = pd.DataFrame(returns_data, columns=symbols)
        cov_matrix = np.cov(returns_data.T)

        res = allocator.optimize_multi_model_blend(
            predicted_returns=predicted_returns,
            returns_df=returns_df,
            cov_matrix=cov_matrix,
            symbols=symbols,
        )
        assert isinstance(res, (np.ndarray, dict))
        if isinstance(res, np.ndarray):
            assert math.isclose(float(np.sum(res)), 1.0, abs_tol=1e-4)
        else:
            assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-4)

    def test_feature_f487_1_waterfall_capital_redistribution_mechanics(self, allocator, portfolio_allocator):
        # 4 assets: A, B, C, D
        # Current weights: A: 0.10, B: 0.10, C: 0.10, D: 0.10 (sum=0.40)
        # Target weights: A: 0.40, B: 0.40, C: 0.10, D: 0.10 (sum=1.00)
        # ADV constraints max_delta_w = 0.05 on A and B
        current_w = {"A": 0.10, "B": 0.10, "C": 0.10, "D": 0.10}
        target_w = {"A": 0.40, "B": 0.40, "C": 0.10, "D": 0.10}
        max_delta = {"A": 0.05, "B": 0.05, "C": 0.20, "D": 0.20}
        alpha_scores = {"A": 0.95, "B": 0.90, "C": 0.85, "D": 0.60}

        # Step 1: Pre-waterfall executed weights under ADV limits
        pre_waterfall = {}
        for sym in current_w:
            delta = target_w[sym] - current_w[sym]
            allowed = max(-max_delta[sym], min(max_delta[sym], delta))
            pre_waterfall[sym] = current_w[sym] + allowed

        assert math.isclose(sum(pre_waterfall.values()), 0.50, abs_tol=1e-5)

        # Step 2: Apply waterfall redistribution under Phase 103
        redistributed = allocator.redistribute_waterfall_capital(
            current_weights=current_w,
            next_weights=pre_waterfall,
            target_weights=target_w,
            max_delta_w=max_delta,
            max_single_weight=0.35,
            alpha_scores=alpha_scores,
        )

        assert isinstance(redistributed, dict)
        assert sum(redistributed.values()) > sum(pre_waterfall.values()), "Waterfall should increase total invested capital"
        assert math.isclose(sum(redistributed.values()), 0.90, abs_tol=1e-4)

        # C should absorb capacity first (alpha 0.85 > D 0.60)
        assert math.isclose(redistributed["C"], 0.30, abs_tol=1e-4)
        assert math.isclose(redistributed["D"], 0.30, abs_tol=1e-4)
        assert math.isclose(redistributed["A"], 0.15, abs_tol=1e-4)
        assert math.isclose(redistributed["B"], 0.15, abs_tol=1e-4)

        # Check all waterfall aliases on UnifiedPortfolioAllocator and PortfolioAllocator
        wf_aliases = [
            "redistribute_waterfall_capital",
            "apply_waterfall_capital_redistribution",
            "waterfall_capital_redistribution",
            "phase102_waterfall_capital_redistribution",
            "phase103_waterfall_capital_redistribution",
        ]
        for alias in wf_aliases:
            fn_upa = getattr(allocator, alias, None)
            assert fn_upa is not None, f"Missing {alias} on UnifiedPortfolioAllocator"
            res_upa = fn_upa(
                current_weights=current_w,
                next_weights=pre_waterfall,
                target_weights=target_w,
                max_delta_w=max_delta,
                max_single_weight=0.35,
                alpha_scores=alpha_scores,
            )
            for k in redistributed:
                assert math.isclose(res_upa[k], redistributed[k], abs_tol=1e-5)

            fn_pa = getattr(portfolio_allocator, alias, None)
            assert fn_pa is not None, f"Missing {alias} on PortfolioAllocator"
            res_pa = fn_pa(
                current_weights=current_w,
                next_weights=pre_waterfall,
                target_weights=target_w,
                max_delta_w=max_delta,
                max_single_weight=0.35,
                alpha_scores=alpha_scores,
            )
            for k in redistributed:
                assert math.isclose(res_pa[k], redistributed[k], abs_tol=1e-5)

    def test_feature_f487_1_waterfall_integration_in_optimize_multi_model_blend(self, allocator):
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        predicted_returns = np.array([0.25, 0.20, 0.15, 0.10])
        returns_df = pd.DataFrame(
            np.random.RandomState(42).randn(60, 4) * 0.01,
            columns=symbols
        )
        cov_matrix = np.diag([0.04, 0.04, 0.04, 0.04])
        current_weights = {"AAPL": 0.05, "MSFT": 0.05, "GOOGL": 0.05, "AMZN": 0.05}
        # Tight max delta for top assets
        max_delta_w = {"AAPL": 0.05, "MSFT": 0.05, "GOOGL": 0.30, "AMZN": 0.30}

        res_p103 = allocator.optimize_multi_model_blend(
            predicted_returns=predicted_returns,
            returns_df=returns_df,
            cov_matrix=cov_matrix,
            symbols=symbols,
            current_weights=current_weights,
            max_delta_w=max_delta_w,
            max_single_weight=0.40,
        )

        assert isinstance(res_p103, (dict, np.ndarray))
        if isinstance(res_p103, dict):
            assert sum(res_p103.values()) > 0.50
            for sym, w in res_p103.items():
                assert w <= 0.40 + 1e-5
        else:
            assert np.sum(res_p103) > 0.50
            for w in res_p103:
                assert w <= 0.40 + 1e-5

    def test_feature_f487_2_evar_risk_measure(self, allocator, portfolio_allocator):
        returns = np.array([-0.05, -0.02, 0.01, 0.03, -0.01, 0.02, -0.04, 0.015, -0.005, 0.025])
        evar_res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar_risk_measure(returns)

        evar_val = _extract_evar_val(evar_res)
        assert evar_val > 0.0

        if isinstance(evar_res, dict):
            assert evar_res.get("order", 138) == 138
            assert math.isclose(float(evar_res.get("xi_monster", 0.0)), 1.0, abs_tol=1e-12)
            assert "phase103_evar" in evar_res

    def test_feature_f487_2_evar_all_33_aliases_and_delegation(self, allocator, portfolio_allocator):
        returns = np.array([-0.05, -0.02, 0.01, 0.03, -0.01, 0.02, -0.04, 0.015, -0.005, 0.025])
        base_res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar_risk_measure(returns)
        evar_val = _extract_evar_val(base_res)

        alias_names = [
            "compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar",
            "trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar_risk_measure",
            "compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar_blend",
            "compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar",
            "singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar_risk_measure",
            "compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_phase103",
            "compute_phase103_evar",
            "compute_phase103_evar_risk_measure",
            "phase103_evar_risk_measure",
            "compute_higher_homology_53_evar_risk_measure",
            "compute_higher_homology_53_evar",
            "compute_evar_order138",
            "compute_138th_cumulant_evar",
            "compute_monster_whittaker_138th_cumulant_evar",
            "compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar_risk_measure",
            "compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar_risk_measure",
            "compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar",
            "compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar",
            "compute_drinfeld_higher_homology_53_evar_risk_measure",
            "compute_drinfeld_higher_homology_53_evar",
            "compute_lurie_drinfeld_higher_homology_53_evar_risk_measure",
            "compute_lurie_drinfeld_higher_homology_53_evar",
            "calculate_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_evar_138th_cumulant",
            "evar_138th_cumulant",
            "trans_singular_138th_cumulant_evar",
            "eternal_omni_cosmic_138th_cumulant_evar",
            "supreme_transcendent_evar_138",
            "higher_homology_53_evar",
            "phase103_tail_risk_evar",
            "phase103_evar_bound",
            "compute_lmbmwdh53_evar",
            "lmbmwdh53_evar",
            "trans_singular_evar_v103",
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

    def test_backward_compatibility_v102_v101_v100_v99(self):
        alloc_v102 = UnifiedPortfolioAllocator(version=102)
        assert alloc_v102.is_phase102 is True
        assert getattr(alloc_v102, "is_phase103", False) is False

        alloc_v101 = UnifiedPortfolioAllocator(version=101)
        assert alloc_v101.is_phase101 is True
        assert getattr(alloc_v101, "is_phase102", False) is False
        assert getattr(alloc_v101, "is_phase103", False) is False

        alloc_v100 = UnifiedPortfolioAllocator(version=100)
        assert alloc_v100.is_phase100 is True
        assert getattr(alloc_v100, "is_phase101", False) is False
        assert getattr(alloc_v100, "is_phase102", False) is False
        assert getattr(alloc_v100, "is_phase103", False) is False

        alloc_v99 = UnifiedPortfolioAllocator(version=99)
        assert alloc_v99.is_phase99 is True
        assert getattr(alloc_v99, "is_phase100", False) is False
        assert getattr(alloc_v99, "is_phase101", False) is False
        assert getattr(alloc_v99, "is_phase102", False) is False
        assert getattr(alloc_v99, "is_phase103", False) is False

        pa_v102 = PortfolioAllocator(version=102)
        assert pa_v102.is_phase102 is True
        assert getattr(pa_v102, "is_phase103", False) is False

        pa_v101 = PortfolioAllocator(version=101)
        assert pa_v101.is_phase101 is True
        assert getattr(pa_v101, "is_phase102", False) is False
        assert getattr(pa_v101, "is_phase103", False) is False

        pa_v100 = PortfolioAllocator(version=100)
        assert pa_v100.is_phase100 is True
        assert getattr(pa_v100, "is_phase101", False) is False
        assert getattr(pa_v100, "is_phase102", False) is False
        assert getattr(pa_v100, "is_phase103", False) is False

        pa_v99 = PortfolioAllocator(version=99)
        assert pa_v99.is_phase99 is True
        assert getattr(pa_v99, "is_phase100", False) is False
        assert getattr(pa_v99, "is_phase101", False) is False
        assert getattr(pa_v99, "is_phase102", False) is False
        assert getattr(pa_v99, "is_phase103", False) is False

    def test_module_level_exports(self):
        w_dict = {"BL": {"A": 0.5, "B": 0.5}, "HERC": {"A": 0.4, "B": 0.6}, "RP": {"A": 0.3, "B": 0.7}, "CVaR": {"A": 0.6, "B": 0.4}}
        res_blend = module_barycenter_blend(w_dict)
        assert isinstance(res_blend, dict)
        assert math.isclose(sum(res_blend.values()), 1.0, abs_tol=1e-5)

        res_p103_bary = module_phase103_barycenter(w_dict)
        assert isinstance(res_p103_bary, dict)
        assert math.isclose(sum(res_p103_bary.values()), 1.0, abs_tol=1e-5)

        res_p103_blend_alias = module_phase103_barycenter_blend(w_dict)
        assert isinstance(res_p103_blend_alias, dict)
        assert math.isclose(sum(res_p103_blend_alias.values()), 1.0, abs_tol=1e-5)

        res_p103_alias = module_alias_p103_barycenter_blend(w_dict)
        assert isinstance(res_p103_alias, dict)
        assert math.isclose(sum(res_p103_alias.values()), 1.0, abs_tol=1e-5)

        res_h53 = module_alias_h53_barycenter(w_dict)
        assert isinstance(res_h53, dict)
        assert math.isclose(sum(res_h53.values()), 1.0, abs_tol=1e-5)

        res_lmb = module_alias_lmbmwdh53_barycenter(w_dict)
        assert isinstance(res_lmb, dict)
        assert math.isclose(sum(res_lmb.values()), 1.0, abs_tol=1e-5)

        returns = np.array([-0.05, -0.02, 0.01, 0.03, -0.01, 0.02, -0.04, 0.015, -0.005, 0.025])
        res_evar = module_evar_risk_measure(returns)
        assert _extract_evar_val(res_evar) > 0.0

        res_p103_evar = module_phase103_evar(returns)
        assert _extract_evar_val(res_p103_evar) > 0.0

        res_p103_evar_alias = module_alias_phase103_evar_risk_measure(returns)
        assert _extract_evar_val(res_p103_evar_alias) > 0.0

        res_trans_alias = module_alias_trans_singular_evar_v103(returns)
        assert _extract_evar_val(res_trans_alias) > 0.0

        # Waterfall module level exports
        cur_w = {"A": 0.2, "B": 0.2}
        nxt_w = {"A": 0.2, "B": 0.2}
        tgt_w = {"A": 0.5, "B": 0.5}
        max_d = {"A": 0.3, "B": 0.3}
        res_wf = module_redistribute_waterfall_capital(
            current_weights=cur_w,
            next_weights=nxt_w,
            target_weights=tgt_w,
            max_delta_w=max_d,
            max_single_weight=0.5,
        )
        assert isinstance(res_wf, dict)
        assert sum(res_wf.values()) > sum(nxt_w.values())

        res_wf_p103 = module_phase103_waterfall_capital_redistribution(
            current_weights=cur_w,
            next_weights=nxt_w,
            target_weights=tgt_w,
            max_delta_w=max_d,
            max_single_weight=0.5,
        )
        assert isinstance(res_wf_p103, dict)

        import trading_system.src.risk.unified_portfolio_allocator as upa_mod
        expected_exports = [
            "compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_53_fisher_rao_barycenter_blend",
            "compute_phase103_barycenter",
            "compute_phase103_barycenter_blend",
            "phase103_barycenter_blend",
            "higher_homology_53_barycenter",
            "lmbmwdh53_barycenter",
            "compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar_risk_measure",
            "compute_phase103_evar",
            "phase103_evar_risk_measure",
            "trans_singular_evar_v103",
            "redistribute_waterfall_capital",
            "phase103_waterfall_capital_redistribution",
        ]
        for exp in expected_exports:
            assert exp in upa_mod.__all__, f"{exp} missing from upa_mod.__all__"

        import trading_system.src.risk.portfolio_allocator as pa_mod
        for exp in expected_exports:
            assert exp in pa_mod.__all__, f"{exp} missing from pa_mod.__all__"

    def test_numerical_stability_extreme_gradient_clipping(self, allocator):
        # Extreme skewed weights to test gradient clipping and tau lower bound (tau = 0.6e-6)
        skewed_weights = {"bl": 1e-15, "herc": 1e-15, "rp": 1e-15, "cvar": 0.999999999999}
        res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_53_fisher_rao_barycenter_blend(skewed_weights)
        assert isinstance(res, dict)
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)
        for k, v in res.items():
            assert not math.isnan(v)
            assert not math.isinf(v)
            assert v >= 0.6e-6
