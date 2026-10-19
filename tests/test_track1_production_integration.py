"""
test_track1_production_integration.py

Comprehensive Integration Test Suite for Track 1:
30-Year Optimized Quantitative Model & Allocator Integration into Production Pipeline.
Verifies:
1. REGIME_ADAPTIVE_RISK_BUDGET definitions on UnifiedPortfolioAllocator
2. Regime-adaptive target volatility scaling & cash preservation (>= 85% cash in CRISIS)
3. Leland dynamic buffer band exposure clamping (zero cash leak)
4. Dynamic US Tech/Growth expansion tilt in Bull regimes
5. OMS Engine Alpha Hurdle Gating (1.5x friction hurdle)
6. TurnoverOptimizer market-adaptive thresholds (theta_US = 0.025, theta_KRX = 0.045)
"""

import sys
import os
import math
import numpy as np
import pandas as pd
import pytest

# Ensure project root and trading_system are on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TRADING_SYSTEM_DIR = os.path.join(PROJECT_ROOT, "trading_system")
for p in (PROJECT_ROOT, TRADING_SYSTEM_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.execution.oms_engine import ExecutionOMSEngine
from src.execution.turnover_optimizer import TurnoverOptimizer


class TestTrack1ProductionIntegration:
    """Tests the full production integration of Track 1 optimizations."""

    def test_regime_adaptive_risk_budget_table_complete(self):
        """Asserts that all 7 regimes are defined in REGIME_ADAPTIVE_RISK_BUDGET with target vol and exposure."""
        assert hasattr(UnifiedPortfolioAllocator, "REGIME_ADAPTIVE_RISK_BUDGET")
        budget = UnifiedPortfolioAllocator.REGIME_ADAPTIVE_RISK_BUDGET
        required_regimes = [
            "BULL_LOW_VOL", "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL", "BEAR_HIGH_VOL",
            "CRISIS"
        ]
        for r in required_regimes:
            assert r in budget, f"Regime {r} missing from REGIME_ADAPTIVE_RISK_BUDGET"
            assert "target_vol" in budget[r]
            assert "max_exposure" in budget[r]
            assert "min_exposure" in budget[r]

        # Check target vol values
        assert budget["BULL_LOW_VOL"]["target_vol"] == 0.22
        assert budget["BULL_HIGH_VOL"]["target_vol"] == 0.18
        assert budget["CRISIS"]["target_vol"] == 0.06
        assert budget["CRISIS"]["max_exposure"] == 0.15  # >= 85% cash preservation

    def test_apply_target_volatility_scaling_regime_adaptation(self):
        """Tests that apply_target_volatility_scaling adaptively scales target vol based on regime."""
        allocator = UnifiedPortfolioAllocator(target_volatility=0.12)
        n = 5
        weights = np.ones(n) / n
        # Covariance with ~15% annualized vol
        daily_var = (0.15 / np.sqrt(252.0)) ** 2
        cov_matrix = np.eye(n) * daily_var

        # 1. Bull Low-Vol regime: should scale up to target_vol=0.22
        w_bull, eff_bull = allocator.apply_target_volatility_scaling(
            weights, cov_matrix, regime="BULL_LOW_VOL"
        )
        assert eff_bull > 0.90, f"Bull Low-Vol should expand exposure, got {eff_bull}"
        assert eff_bull <= 1.00

        # 2. Crisis regime: should compress exposure to <= 0.15
        w_crisis, eff_crisis = allocator.apply_target_volatility_scaling(
            weights, cov_matrix, regime="CRISIS"
        )
        assert eff_crisis <= 0.15, f"Crisis regime must enforce max_exposure <= 0.15, got {eff_crisis}"

        # 3. Bear High-Vol regime: should compress exposure to <= 0.25
        w_bear, eff_bear = allocator.apply_target_volatility_scaling(
            weights, cov_matrix, regime="BEAR_HIGH_VOL"
        )
        assert eff_bear <= 0.25, f"Bear High-Vol must enforce max_exposure <= 0.25, got {eff_bear}"

    def test_leland_buffer_respects_max_total_allocation(self):
        """Tests that apply_leland_no_trade_buffers clamps sum of realized weights to max_total_allocation."""
        allocator = UnifiedPortfolioAllocator()
        n = 5
        curr_w = np.array([0.20, 0.20, 0.20, 0.20, 0.20])
        # Suppose target is reduced to 0.03 each (total 0.15) due to crisis
        target_w = np.array([0.03, 0.03, 0.03, 0.03, 0.03])
        vols = np.full(n, 0.02)

        # In crisis, max_total_allocation = 0.15
        realized_w = allocator.apply_leland_no_trade_buffers(
            target_weights=target_w,
            current_weights=curr_w,
            volatilities=vols,
            max_total_allocation=0.15
        )
        total_realized = float(np.sum(realized_w))
        assert total_realized <= 0.15 + 1e-6, f"Leland buffer leaked cash reserve: {total_realized} > 0.15"

    def test_dynamic_us_tech_expansion_tilt_in_allocate(self):
        """Tests that US tech assets receive expansion multipliers during Bull regimes."""
        allocator = UnifiedPortfolioAllocator()
        symbols = ["AAPL", "NVDA", "005930.KS", "068270.KQ"]
        dates = pd.date_range("2024-01-01", periods=100, freq="B")
        prices_dict = {}
        for s in symbols:
            px = 100.0 * np.cumprod(1 + np.random.normal(0.001, 0.015, len(dates)))
            prices_dict[s] = pd.DataFrame({"Close": px}, index=dates)

        pred_df = pd.DataFrame({
            "symbol": symbols,
            "market": ["NASDAQ", "NASDAQ", "KOSPI", "KOSDAQ"],
            "ensemble_expected_return": [0.05, 0.05, 0.05, 0.05],
            "close": [150.0, 120.0, 70000.0, 50000.0]
        })

        alloc_bull = allocator.allocate(
            predictions_df=pred_df,
            prices_dict=prices_dict,
            total_portfolio_value=100_000_000.0,
            regime="BULL_LOW_VOL",
            top_n=10
        )
        assert not alloc_bull.empty

        # NASDAQ symbols (AAPL, NVDA) should have higher predicted_return after tilt
        res_map = dict(zip(alloc_bull["symbol"], alloc_bull["predicted_return"]))
        assert res_map["AAPL"] > res_map["005930.KS"]
        assert res_map["NVDA"] > res_map["068270.KQ"]

    def test_turnover_optimizer_market_adaptive_thresholds(self):
        """Verifies market-adaptive hysteresis thresholds (theta_US = 0.025, theta_KRX = 0.045)."""
        opt = TurnoverOptimizer()
        assert opt.resolve_threshold("AAPL", currency="USD") == 0.025
        assert opt.resolve_threshold("NVDA", currency="USD") == 0.025
        assert opt.resolve_threshold("SP500") == 0.025
        assert opt.resolve_threshold("005930.KS", currency="KRW") == 0.045
        assert opt.resolve_threshold("068270.KQ", currency="KRW") == 0.045
        assert opt.resolve_threshold("KOSPI") == 0.045

    def test_oms_alpha_hurdle_gating(self, tmp_path):
        """Verifies that OMS Engine Alpha Hurdle Gating skips marginal rebalances when alpha < 1.5x friction."""
        db_file = str(tmp_path / "test_trade_logs.db")
        oms = ExecutionOMSEngine(db_path=db_file)

        # Existing holding of 10%
        curr_holdings = {
            "005930.KS": {"quantity": 100, "current_price": 70000.0, "weight": 0.10}
        }
        # Slight rebalance target of 12% (delta = 2%), but expected return is near zero (0.001)
        # KRX transaction friction is ~25 bps (0.0025). 1.5x friction = 37.5 bps (0.00375).
        # Expected return 0.001 < 0.00375, so trade should be skipped by Alpha Hurdle!
        picks = [{
            "symbol": "005930.KS",
            "name": "Samsung Electronics",
            "market": "KOSPI",
            "action": "BUY",
            "portfolio_weight": 0.12,
            "target_price": 70000.0,
            "close_price": 70000.0,
            "volatility_20d": 0.02,
            "ensemble_expected_return": 0.001,  # below 1.5x friction hurdle
        }]
        weight_dict = {"005930.KS": 0.12}

        order_plans = oms.generate_order_plan(
            picks,
            weight_dict,
            total_capital=70_000_000.0,
            crisis_level="NORMAL",
            current_holdings=curr_holdings,
            use_leland_buffer=True
        )
        # Should be filtered out by Leland or Alpha Hurdle
        assert len(order_plans) == 0, f"Expected 0 order plans due to Alpha Hurdle / Leland buffer, got {len(order_plans)}"
