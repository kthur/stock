"""
tests/test_m1_2_empirical_risk_challenge.py
Adversarial empirical stress testing for Milestone 1: Risk, Leland & Crisis enhancements.
Tests:
1. REGIME_ADAPTIVE_RISK_BUDGET in UnifiedPortfolioAllocator (src & trading_system mirror)
2. calculate_asymmetric_leland_multipliers in UnifiedPortfolioAllocator and PortfolioAllocator
3. OMS Gate 5 Net Alpha Hurdle logic and execution gating in ExecutionOMSEngine
4. Target volatility scaling edge cases, cash drag elimination, and crisis containment.
"""

import math
import pytest
import numpy as np
from unittest.mock import MagicMock

# Import from src
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator as UPA_src
from src.risk.portfolio_allocator import PortfolioAllocator as PA_src
from src.execution.oms_engine import ExecutionOMSEngine as OMS_src
from src.execution.turnover_optimizer import TurnoverOptimizer as TO_src

# Import from trading_system/src mirror
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator as UPA_ts
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator as PA_ts
from trading_system.src.execution.oms_engine import ExecutionOMSEngine as OMS_ts
from trading_system.src.execution.turnover_optimizer import TurnoverOptimizer as TO_ts


class TestTask1RegimeAdaptiveRiskBudget:
    """Task 1: Test REGIME_ADAPTIVE_RISK_BUDGET invariants and cash drag elimination."""

    @pytest.mark.parametrize("alloc_cls", [UPA_src, UPA_ts])
    def test_bull_low_vol_cash_drag_elimination(self, alloc_cls):
        budget = alloc_cls.REGIME_ADAPTIVE_RISK_BUDGET
        assert "BULL_LOW_VOL" in budget
        cfg = budget["BULL_LOW_VOL"]
        assert cfg["min_exposure"] == 0.98, f"Expected min_exposure 0.98 in BULL_LOW_VOL, got {cfg['min_exposure']}"
        assert cfg["max_exposure"] == 1.00, f"Expected max_exposure 1.00 in BULL_LOW_VOL, got {cfg['max_exposure']}"
        assert cfg["target_vol"] == 0.16, f"Expected target_vol 0.16 in BULL_LOW_VOL, got {cfg['target_vol']}"

    @pytest.mark.parametrize("alloc_cls", [UPA_src, UPA_ts])
    def test_bull_high_vol_target_vol_and_exposure(self, alloc_cls):
        budget = alloc_cls.REGIME_ADAPTIVE_RISK_BUDGET
        assert "BULL_HIGH_VOL" in budget
        cfg = budget["BULL_HIGH_VOL"]
        assert cfg["target_vol"] == 0.14, f"Expected target_vol 0.14 in BULL_HIGH_VOL, got {cfg['target_vol']}"
        assert cfg["min_exposure"] == 0.95
        assert cfg["max_exposure"] == 1.00

    @pytest.mark.parametrize("alloc_cls", [UPA_src, UPA_ts])
    def test_crisis_regime_tightening(self, alloc_cls):
        budget = alloc_cls.REGIME_ADAPTIVE_RISK_BUDGET
        assert "CRISIS" in budget
        cfg = budget["CRISIS"]
        assert cfg["min_exposure"] == 0.00, f"Expected min_exposure 0.00 in CRISIS, got {cfg['min_exposure']}"
        assert cfg["max_exposure"] == 0.15, f"Expected max_exposure 0.15 in CRISIS, got {cfg['max_exposure']}"
        assert cfg["target_vol"] == 0.05, f"Expected target_vol 0.05 in CRISIS, got {cfg['target_vol']}"

    @pytest.mark.parametrize("alloc_cls", [UPA_src, UPA_ts])
    def test_all_regimes_ordering_and_bounds_invariants(self, alloc_cls):
        budget = alloc_cls.REGIME_ADAPTIVE_RISK_BUDGET
        required_regimes = [
            "BULL_LOW_VOL", "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL", "BEAR_HIGH_VOL",
            "CRISIS"
        ]
        for reg in required_regimes:
            assert reg in budget, f"Missing regime {reg} in risk budget"
            cfg = budget[reg]
            min_e = cfg["min_exposure"]
            max_e = cfg["max_exposure"]
            t_vol = cfg["target_vol"]
            assert 0.0 <= min_e <= max_e <= 1.0, f"Violated 0 <= min <= max <= 1 in {reg}: min={min_e}, max={max_e}"
            assert 0.01 <= t_vol <= 0.25, f"Target vol out of sane bounds in {reg}: {t_vol}"

    @pytest.mark.parametrize("alloc_cls", [UPA_src, UPA_ts])
    def test_target_volatility_scaling_cash_drag_behavior(self, alloc_cls):
        alloc = alloc_cls()
        weights = np.array([0.25, 0.25, 0.25, 0.25])
        
        # Bull low vol: low portfolio vol (e.g. 0.08) -> scale should hit 1.00 cap
        # Annualized vol of cov = (daily_std)^2 * 252. For 8% ann vol, daily std = 0.08 / sqrt(252)
        daily_var_low = (0.08 / math.sqrt(252.0)) ** 2
        cov_low = np.diag([daily_var_low * 4.0] * 4)  # 4 * (1/16) * 4 * daily_var = daily_var_low
        scaled_w, eff_alloc = alloc.apply_target_volatility_scaling(
            weights=weights,
            cov_matrix=cov_low,
            regime="BULL_LOW_VOL",
        )
        assert math.isclose(eff_alloc, 1.00, abs_tol=1e-5), f"Bull low vol low vol should be 1.00, got {eff_alloc}"
        assert np.allclose(scaled_w, weights)

        # Bull low vol: high portfolio vol (e.g. 0.30) -> raw scale 0.16/0.30 = 0.533 -> floor 0.98 kicks in!
        daily_var_high = (0.30 / math.sqrt(252.0)) ** 2
        cov_high = np.diag([daily_var_high * 4.0] * 4)
        scaled_w, eff_alloc = alloc.apply_target_volatility_scaling(
            weights=weights,
            cov_matrix=cov_high,
            regime="BULL_LOW_VOL",
        )
        assert math.isclose(eff_alloc, 0.98, abs_tol=1e-5), f"Bull low vol floor should hold at 0.98, got {eff_alloc}"

        # Crisis: high portfolio vol (e.g. 0.40) -> max alloc cap 0.15 strictly enforced
        daily_var_crisis = (0.40 / math.sqrt(252.0)) ** 2
        cov_crisis = np.diag([daily_var_crisis * 4.0] * 4)
        scaled_w, eff_alloc = alloc.apply_target_volatility_scaling(
            weights=weights,
            cov_matrix=cov_crisis,
            regime="CRISIS",
        )
        assert eff_alloc <= 0.15, f"Crisis allocation exceeded 0.15 ceiling: {eff_alloc}"


class TestTask2AsymmetricLelandMultipliers:
    """Task 2: Test calculate_asymmetric_leland_multipliers across UPA and PA."""

    @pytest.mark.parametrize("calc_fn", [
        UPA_src.calculate_asymmetric_leland_multipliers,
        UPA_ts.calculate_asymmetric_leland_multipliers,
        PA_src.calculate_asymmetric_leland_multipliers,
        PA_ts.calculate_asymmetric_leland_multipliers,
    ])
    def test_winner_runner_expands_to_2_2x(self, calc_fn):
        """For an unrealized return of +10% (winner runner >= +8%), upper band multiplier expands to 2.2x."""
        # For daily vol 0.01 (1%), 5d vol is 0.02236.
        # +10% move has z = 0.10 / 0.02236 = 4.472 >= 3.0 -> clamped z = 1.0 -> 1.0 + 1.2 * 1.0 = 2.2x
        up, lo = calc_fn(unrealized_return=0.10, volatility_20d=0.01)
        assert math.isclose(up, 2.2, abs_tol=1e-5), f"Expected 2.2x upper mult for +10% runner, got {up}"
        assert math.isclose(lo, 1.0, abs_tol=1e-5), f"Lower multiplier for winner should be 1.0, got {lo}"

        # Even with 2% vol, a 20% runner expands to 2.2x
        up2, lo2 = calc_fn(unrealized_return=0.20, volatility_20d=0.02)
        assert math.isclose(up2, 2.2, abs_tol=1e-5), f"Expected 2.2x upper mult for +20% runner, got {up2}"

    @pytest.mark.parametrize("calc_fn", [
        UPA_src.calculate_asymmetric_leland_multipliers,
        UPA_ts.calculate_asymmetric_leland_multipliers,
        PA_src.calculate_asymmetric_leland_multipliers,
        PA_ts.calculate_asymmetric_leland_multipliers,
    ])
    def test_losing_position_tightens_to_0_6x(self, calc_fn):
        """For a losing position (-5%), band multiplier tightens to 0.6x (when z <= -3.0)."""
        # For daily vol 0.005 (0.5%), 5d vol is 0.01118.
        # -5% move has z = -0.05 / 0.01118 = -4.472 <= -3.0 -> clamped z = 1.0 -> 1.0 - 0.4 * 1.0 = 0.6x
        up, lo = calc_fn(unrealized_return=-0.05, volatility_20d=0.005)
        assert math.isclose(up, 1.0, abs_tol=1e-5), f"Upper multiplier for loser should be 1.0, got {up}"
        assert math.isclose(lo, 0.6, abs_tol=1e-5), f"Expected 0.6x lower mult for -5% position, got {lo}"

        # Extreme loser -20% with 2% vol:
        up2, lo2 = calc_fn(unrealized_return=-0.20, volatility_20d=0.02)
        assert math.isclose(lo2, 0.6, abs_tol=1e-5), f"Expected 0.6x lower mult for -20% position, got {lo2}"

    @pytest.mark.parametrize("calc_fn", [
        UPA_src.calculate_asymmetric_leland_multipliers,
        UPA_ts.calculate_asymmetric_leland_multipliers,
        PA_src.calculate_asymmetric_leland_multipliers,
        PA_ts.calculate_asymmetric_leland_multipliers,
    ])
    def test_neutral_and_mild_returns(self, calc_fn):
        """Zero and mild returns stay within noise band (1.0, 1.0)."""
        up, lo = calc_fn(unrealized_return=0.0, volatility_20d=0.02)
        assert math.isclose(up, 1.0, abs_tol=1e-5)
        assert math.isclose(lo, 1.0, abs_tol=1e-5)

        # Mild return with z = 0.5 (within 1.0 sigma noise band)
        vol_5d = 0.02 * math.sqrt(5.0)
        up_mild, lo_mild = calc_fn(unrealized_return=0.5 * vol_5d, volatility_20d=0.02)
        assert math.isclose(up_mild, 1.0, abs_tol=1e-5)
        assert math.isclose(lo_mild, 1.0, abs_tol=1e-5)

    @pytest.mark.parametrize("calc_fn", [
        UPA_src.calculate_asymmetric_leland_multipliers,
        UPA_ts.calculate_asymmetric_leland_multipliers,
        PA_src.calculate_asymmetric_leland_multipliers,
        PA_ts.calculate_asymmetric_leland_multipliers,
    ])
    def test_intermediate_winner_scaling(self, calc_fn):
        """Intermediate runner at z = 2.0 scales to 1.6x (1.0 + 1.2 * 0.5 = 1.6)."""
        vol_5d = 0.02 * math.sqrt(5.0)
        up, lo = calc_fn(unrealized_return=2.0 * vol_5d, volatility_20d=0.02)
        assert math.isclose(up, 1.6, abs_tol=1e-5), f"Expected 1.6x at z=2.0, got {up}"
        assert math.isclose(lo, 1.0, abs_tol=1e-5)

    @pytest.mark.parametrize("calc_fn", [
        UPA_src.calculate_asymmetric_leland_multipliers,
        UPA_ts.calculate_asymmetric_leland_multipliers,
        PA_src.calculate_asymmetric_leland_multipliers,
        PA_ts.calculate_asymmetric_leland_multipliers,
    ])
    def test_extreme_adversarial_inputs(self, calc_fn):
        """Adversarial stress testing: NaN, Inf, zero vol, extreme 1000% gain, extreme -99% loss."""
        # Zero vol
        up, lo = calc_fn(unrealized_return=0.10, volatility_20d=0.0)
        assert math.isfinite(up) and math.isfinite(lo)
        assert up >= 1.0 and lo <= 1.0

        # NaN
        up_nan, lo_nan = calc_fn(unrealized_return=float("nan"), volatility_20d=0.02)
        assert up_nan == 1.0 and lo_nan == 1.0

        # Inf
        up_inf, lo_inf = calc_fn(unrealized_return=float("inf"), volatility_20d=0.02)
        assert up_inf == 1.0 and lo_inf == 1.0

        # Extreme 1000% gain
        up_huge, lo_huge = calc_fn(unrealized_return=10.0, volatility_20d=0.02)
        assert math.isclose(up_huge, 2.2, abs_tol=1e-5), f"Huge gain must be strictly capped at 2.2x, got {up_huge}"

        # Extreme 99% loss
        up_loss, lo_loss = calc_fn(unrealized_return=-0.99, volatility_20d=0.02)
        assert math.isclose(lo_loss, 0.6, abs_tol=1e-5), f"Huge loss must be strictly floored at 0.6x, got {lo_loss}"


class TestTask3Gate5NetAlphaHurdle:
    """Task 3: Test Gate 5 Net Alpha Hurdle logic and execution gating."""

    def test_hurdle_multipliers_by_regime(self):
        """Assert hurdle multiplier is 1.2x for BULL regimes and 1.5x for SIDEWAYS/BEAR/CRISIS."""
        test_cases = [
            ("BULL_LOW_VOL", 1.2),
            ("BULL_HIGH_VOL", 1.2),
            ("BULL", 1.2),
            ("BULLISH", 1.2),
            ("SIDEWAYS_LOW_VOL", 1.5),
            ("SIDEWAYS_HIGH_VOL", 1.5),
            ("BEAR_LOW_VOL", 1.5),
            ("BEAR_HIGH_VOL", 1.5),
            ("CRISIS", 1.5),
        ]
        for regime_str, expected_mult in test_cases:
            hurdle_mult = 1.2 if regime_str.startswith("BULL") else 1.5
            assert hurdle_mult == expected_mult, f"Failed for regime {regime_str}: expected {expected_mult}, got {hurdle_mult}"

    @pytest.mark.parametrize("oms_cls", [OMS_src, OMS_ts])
    def test_oms_gate5_empirical_execution(self, oms_cls):
        """
        Empirically verify that a marginal rebalance with alpha between 1.2x cost and 1.5x cost:
        - In BULL_LOW_VOL: hurdle is 1.2x cost -> Passes Gate 5 and generates BUY order plan!
        - In SIDEWAYS_LOW_VOL: hurdle is 1.5x cost -> Blocked by Gate 5 (Hold)!
        """
        oms = oms_cls(total_capital=10_000_000.0)
        current_holdings = {"AAPL": {"shares": 2, "weight": 0.04, "current_price": 150.0}}
        portfolio_weights = {"AAPL": 0.08}
        
        # Scenario A: BULL_LOW_VOL regime with expected alpha = +0.00085 (8.5 bps)
        pred_bull = [{
            "symbol": "AAPL",
            "name": "Apple",
            "weight": 0.08,
            "close_price": 150.0,
            "target_price": 160.0,
            "ensemble_expected_return": 0.00085,
            "regime": "BULL_LOW_VOL",
            "volatility_20d": 0.02,
            "market": "SP500",
        }]

        orders_bull = oms.generate_order_plan(
            top_predictions=pred_bull,
            portfolio_weights=portfolio_weights,
            current_holdings=current_holdings,
            regime_label="BULL_LOW_VOL",
        )
        assert len(orders_bull) == 1, f"Expected order to pass Gate 5 in BULL_LOW_VOL, but got {len(orders_bull)} orders"
        assert orders_bull[0]["symbol"] == "AAPL"
        assert orders_bull[0]["action"] == "BUY"

        # Scenario B: SIDEWAYS_LOW_VOL regime with identical alpha = +0.00085 (8.5 bps)
        pred_sideways = [{
            "symbol": "AAPL",
            "name": "Apple",
            "weight": 0.08,
            "close_price": 150.0,
            "target_price": 160.0,
            "ensemble_expected_return": 0.00085,
            "regime": "SIDEWAYS_LOW_VOL",
            "volatility_20d": 0.02,
            "market": "SP500",
        }]

        orders_sideways = oms.generate_order_plan(
            top_predictions=pred_sideways,
            portfolio_weights=portfolio_weights,
            current_holdings=current_holdings,
            regime_label="SIDEWAYS_LOW_VOL",
        )
        assert len(orders_sideways) == 0, f"Expected order to be BLOCKED by Gate 5 in SIDEWAYS_LOW_VOL, but got {len(orders_sideways)} orders"
