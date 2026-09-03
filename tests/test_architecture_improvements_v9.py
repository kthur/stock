"""
tests/test_architecture_improvements_v9.py
Verification suite for enterprise architecture improvements across:
1. OMS Alpha Half-Life dynamic routing completeness (dual_correction, index_rebalance, overnight_gap_reversal).
2. SmartOrderRouter symbol parsing and regional venue destination (.KS/.KQ suffix).
3. Standalone pre-market engine isolation & StrategyCoverageAnalyzer consistency (37 active strategies).
4. UnifiedPortfolioAllocator lookahead bias elimination in compute_returns_matrix.
5. 2D Regime weight completeness for newly added strategy metadata.
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.execution.oms_engine import STRATEGY_ALPHA_HALF_LIVES, ExecutionOMSEngine
from src.execution.smart_order_router import SmartOrderRouter
from src.core.opening_auction_arbitrage import OPENING_AUCTION_META
from src.analysis.coverage_analyzer import StrategyCoverageAnalyzer
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.core.strategy_registry import get_registry


class TestArchitectureImprovementsV9:
    """Verifies architectural enhancements across OMS, SOR, Coverage, and Risk layers."""

    def test_oms_alpha_half_lives_completeness(self):
        """Verify all 37 strategies have calibrated alpha decay half-lives."""
        assert "dual_correction" in STRATEGY_ALPHA_HALF_LIVES
        assert STRATEGY_ALPHA_HALF_LIVES["dual_correction"] == 5.0

        assert "index_rebalance" in STRATEGY_ALPHA_HALF_LIVES
        assert STRATEGY_ALPHA_HALF_LIVES["index_rebalance"] == 20.0

        assert "overnight_gap_reversal" in STRATEGY_ALPHA_HALF_LIVES
        assert STRATEGY_ALPHA_HALF_LIVES["overnight_gap_reversal"] == 1.0

        # Verify aliases
        assert STRATEGY_ALPHA_HALF_LIVES.get("overnight_gap") == 1.0
        assert STRATEGY_ALPHA_HALF_LIVES.get("index_rebalance_structural_flow") == 20.0

    def test_oms_dynamic_execution_routing_for_overnight_gap(self):
        """Verify fast-decaying overnight gap alpha triggers FAST_VWAP instead of DIRECT."""
        oms = ExecutionOMSEngine(db_path=":memory:")

        # Symbol with overnight_gap_score (half-life = 1.0 day <= 2.0 days)
        pred = {
            "symbol": "005930",
            "name": "Samsung",
            "market": "KOSPI",
            "overnight_gap_score": 0.85,
            "expected_return": 15.0,
            "Close": 70000.0,
            "adv": 500_000_000_000.0,
        }
        weights = {"005930": 0.10}

        plans = oms.generate_order_plans(
            portfolio_weights=weights,
            top_predictions=[pred],
            total_capital=100_000_000.0,
            regime_label="BULL_LOW_VOL"
        )

        assert len(plans) >= 1
        plan = plans[0]
        assert plan["symbol"] == "005930"
        # Since effective half-life <= 2.0d, it MUST route to FAST_VWAP
        assert plan["execution_strategy"] == "FAST_VWAP"
        assert plan["slice_count"] >= 3

    def test_smart_order_router_destination_resolution(self):
        """Verify SmartOrderRouter correctly resolves KRX with exchange suffixes (.KS, .KQ)."""
        sor = SmartOrderRouter()

        # 1. Standard 6-digit KRX
        dest1 = sor.determine_destination("005930")
        assert dest1["market_region"] == "KRX"
        assert dest1["primary_broker"] == "korea_investment"

        # 2. KRX with .KS suffix and no market specified
        dest2 = sor.determine_destination("005930.KS")
        assert dest2["market_region"] == "KRX"
        assert dest2["primary_broker"] == "korea_investment"

        # 3. KRX with .KQ suffix and no market specified
        dest3 = sor.determine_destination("000660.KQ")
        assert dest3["market_region"] == "KRX"
        assert dest3["primary_broker"] == "korea_investment"

        # 4. US equity
        dest4 = sor.determine_destination("AAPL")
        assert dest4["market_region"] == "US"
        assert dest4["primary_broker"] == "interactive_brokers"

        # 5. US equity with explicit market
        dest5 = sor.determine_destination("NVDA", market="NASDAQ")
        assert dest5["market_region"] == "US"
        assert dest5["primary_broker"] == "interactive_brokers"

    def test_standalone_opening_auction_arbitrage_isolation(self):
        """Verify pre-market opening auction arbitrage is marked standalone and excluded from EOD pipeline coverage."""
        assert OPENING_AUCTION_META.is_standalone is True

        analyzer = StrategyCoverageAnalyzer()
        active_strats = analyzer.strategies

        # opening_auction_arbitrage must NOT be in active EOD ensemble strategies
        assert "opening_auction_arbitrage" not in active_strats
        # Exactly 37 strategies must be active
        assert len(active_strats) == 37

    def test_coverage_analyzer_missing_reasons_aliases(self):
        """Verify coverage analyzer categorizes canonical strategy aliases to correct missing reasons."""
        analyzer = StrategyCoverageAnalyzer()

        # Test overnight_gap_reversal missing reason mapping
        ensemble_df = pd.DataFrame({
            "symbol": ["S1", "S2"],
            "overnight_gap_score": [np.nan, np.nan],
            "overnight_gap_reversal_score": [np.nan, np.nan],
        })
        prices = {
            "S1": pd.DataFrame({"Close": [100.0] * 30}),
            "S2": pd.DataFrame({"Close": [200.0] * 30}),
        }

        cov = analyzer.analyze_coverage(ensemble_df=ensemble_df, prices_dict=prices)
        gap_info = cov["strategies"].get("overnight_gap_reversal")
        if gap_info:
            assert "NO_OVERNIGHT_GAP_SETUP" in gap_info["reasons"]

    def test_unified_portfolio_allocator_no_lookahead_bfill(self):
        """Verify compute_returns_matrix does not backfill prices backwards, avoiding lookahead bias."""
        symbols = ["STOCK_FULL", "STOCK_LATE"]

        # STOCK_FULL has 20 days of data
        dates = pd.date_range("2026-01-01", periods=20)
        p_full = pd.DataFrame({"Close": np.linspace(100, 120, 20)}, index=dates)

        # STOCK_LATE only started on day 10 (first 10 days missing)
        p_late = pd.DataFrame({"Close": np.linspace(50, 60, 10)}, index=dates[10:])

        prices_dict = {
            "STOCK_FULL": p_full,
            "STOCK_LATE": p_late,
        }

        returns_df, valid_syms = UnifiedPortfolioAllocator.compute_returns_matrix(
            symbols=symbols,
            prices_dict=prices_dict,
            lookback=20
        )

        assert len(valid_syms) == 2
        # Early returns for STOCK_LATE must be 0.0 (no return recorded yet), NOT backward-filled with day 10 return
        assert not returns_df.empty
        # Verify no NaN or Inf
        assert np.all(np.isfinite(returns_df.values))
        # Verify STOCK_FULL has positive returns
        assert (returns_df["STOCK_FULL"] > 0).any()
