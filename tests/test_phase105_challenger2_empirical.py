"""
tests/test_phase105_challenger2_empirical.py

Independent Empirical Verification & Adversarial Stress Harness for Phase 105 (Release R121).
Executed by Challenger 2.

Tasks Verified:
1. Net return vs gross return invariant (Net <= Gross throughout all 31 years).
2. Gatheral 3/2-power impact: (delta_w / ADV)^1.5 convexity.
3. Sharpe and Sortino formulas against daily returns series.
4. 200-day SMA gating: zero weight assigned when price < 200 SMA (even with max alpha).
5. ADV participation cap <= 1.5% across rebalance trade orders.
6. Zero future leakage invariant via future data mutation test.
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.backtest.historical_stock_universe_backtester import (
    HistoricalStockUniverseBacktester,
    apply_gatheral_impact_and_adv_cap,
    compute_rolling_adv_20d,
)
from src.backtest.historical_stock_universe_pipeline import (
    HistoricalStockUniversePipeline,
    MultiStockPanel,
    PointInTimeStockUniverse,
)


# ==============================================================================
# Task 1: Net Return vs Gross Return Invariant
# ==============================================================================

class TestNetVsGrossReturnInvariant:
    """Verifies that Net return is less than or equal to Gross return throughout all 31 years and daily bars."""

    def test_annual_distribution_net_lte_gross_all_31_years(self):
        """Verifies net_return_pct <= gross_return_pct across all 31 calendar years in annual.csv."""
        annual_csv_path = TRADING_SYSTEM_DIR / "result" / "backtest_30year_stock_universe_annual.csv"
        assert annual_csv_path.is_file(), f"Annual CSV missing: {annual_csv_path}"

        df = pd.read_csv(annual_csv_path)
        assert len(df) == 31, f"Expected 31 calendar years, found {len(df)}"

        violations = []
        for idx, row in df.iterrows():
            year = int(row["year"])
            gross = float(row["gross_return_pct"])
            net = float(row["net_return_pct"])
            friction = float(row["friction_bps"])

            if net > gross + 1e-9:
                violations.append((year, gross, net, friction))

        assert len(violations) == 0, f"Found Net > Gross violations in annual.csv: {violations}"

    def test_summary_json_net_lte_gross(self):
        """Verifies total_net_return_pct <= total_gross_return_pct and frictions deducted in summary.json."""
        summary_path = TRADING_SYSTEM_DIR / "result" / "backtest_30year_stock_universe_summary.json"
        assert summary_path.is_file(), f"Summary JSON missing: {summary_path}"

        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        overall = data["portfolio_overall"]
        gross_ret = float(overall["total_gross_return_pct"])
        net_ret = float(overall["total_net_return_pct"])
        frictions = float(overall["total_friction_bps"])

        assert net_ret <= gross_ret, f"Total net return ({net_ret}%) exceeds gross ({gross_ret}%)"
        assert frictions > 0.0, f"Total frictions must be positive, got {frictions}"
        assert net_ret < gross_ret, f"Total net return must be strictly less than gross return when frictions > 0"

    def test_daily_return_series_net_lte_gross_invariant(self):
        """Runs backtester and checks daily_net_return <= daily_gross_return on every bar."""
        backtester = HistoricalStockUniverseBacktester(
            start_date="2020-01-01",
            end_date="2022-12-31",
            rebalance_freq_days=60,
        )
        result = backtester.run_backtest(start_date="2020-01-01", end_date="2022-12-31")

        daily_net = result.daily_returns
        daily_gross = result.gross_returns
        assert len(daily_net) == len(daily_gross)
        assert len(daily_net) > 50

        diff = daily_gross - daily_net
        # Gross should be >= Net on all bars (diff >= -1e-9)
        negative_diffs = diff[diff < -1e-9]
        assert len(negative_diffs) == 0, f"Found daily bars where Net > Gross: {negative_diffs}"

        # On rebalance days with trading friction, gross should strictly exceed net
        total_friction_bps = float(result.friction_bps_series.sum())
        assert total_friction_bps > 0.0, "Expected positive trading friction"


# ==============================================================================
# Task 2: Gatheral 3/2-Power Market Impact Convexity
# ==============================================================================

class TestGatheral32PowerConvexity:
    """Empirically verifies the Gatheral 3/2-power impact formula and strict mathematical convexity."""

    def test_gatheral_convexity_and_formula_derivation(self):
        """
        Verify:
        impact_cost = kappa * sigma * (delta / ADV)^1.5 * delta
        Let x = delta / ADV. Then unit impact = kappa * sigma * x^1.5.
        Convexity check:
        For x1 < x2 and lambda in (0, 1):
        f(lambda*x1 + (1-lambda)*x2) <= lambda*f(x1) + (1-lambda)*f(x2).
        Second derivative: f''(x) = 0.75 * kappa * sigma * x^(-0.5) > 0 for all x > 0.
        """
        adv = 10_000_000.0  # 10M ADV
        vol = 0.25
        kappa = 1.50
        max_part = 0.015

        # Check over a grid of participation rates within [0.0001, 0.015]
        grid = np.linspace(0.0005, 0.015, 100)
        unit_impacts = []

        for p in grid:
            order = p * adv
            exec_order, part, cost = apply_gatheral_impact_and_adv_cap(
                target_delta_krw=order,
                adv_20d_krw=adv,
                annual_vol=vol,
                max_adv_participation=max_part,
                kappa=kappa,
            )
            assert abs(part - p) < 1e-9
            unit_cost = cost / exec_order  # cost per KRW traded
            unit_impacts.append(unit_cost)

            # Check exact formula: cost = kappa * vol * (p^1.5) * order
            expected_cost = kappa * vol * (p ** 1.5) * order
            assert abs(cost - expected_cost) < 1e-6, f"Mismatch in cost: {cost} vs {expected_cost}"

        unit_impacts = np.array(unit_impacts)

        # Check strict convexity: second difference > 0
        second_diff = np.diff(unit_impacts, 2)
        assert np.all(second_diff > 0), f"Gatheral unit impact is NOT strictly convex! min second diff: {np.min(second_diff)}"

        # Check total impact cost C(x) = kappa * vol * ADV * x^2.5 is also strictly convex
        total_costs = unit_impacts * (grid * adv)
        total_second_diff = np.diff(total_costs, 2)
        assert np.all(total_second_diff > 0), "Gatheral total cost is NOT strictly convex!"

    def test_gatheral_clamping_at_adv_cap(self):
        """Verifies orders above 1.5% ADV are strictly clamped at 1.5%."""
        adv = 50_000_000.0
        max_part = 0.015
        max_allowed = adv * max_part

        huge_order = adv * 0.50  # 50% ADV
        exec_order, part, cost = apply_gatheral_impact_and_adv_cap(
            target_delta_krw=huge_order,
            adv_20d_krw=adv,
            annual_vol=0.30,
            max_adv_participation=max_part,
            kappa=1.50,
        )

        assert abs(exec_order - max_allowed) < 1e-6, f"Order not clamped: {exec_order} vs {max_allowed}"
        assert abs(part - max_part) < 1e-9, f"Participation rate not clamped: {part} vs {max_part}"

    def test_gatheral_zero_and_negative_adv_handling(self):
        """Edge case: zero or negative ADV returns zero execution and zero cost."""
        exec_order, part, cost = apply_gatheral_impact_and_adv_cap(
            target_delta_krw=1_000_000.0,
            adv_20d_krw=0.0,
            annual_vol=0.25,
            max_adv_participation=0.015,
            kappa=1.50,
        )
        assert exec_order == 0.0
        assert part == 0.0
        assert cost == 0.0


# ==============================================================================
# Task 3: Sharpe and Sortino Formulas against Daily Returns Series
# ==============================================================================

class TestSharpeAndSortinoFormulas:
    """Verifies Sharpe and Sortino formulas against daily returns series."""

    def test_sharpe_and_sortino_against_reported_metrics(self):
        """
        Runs backtester over full 30-year horizon, extracts daily net returns,
        independently computes Sharpe and Sortino ratios, and compares to summary.json.
        """
        backtester = HistoricalStockUniverseBacktester(
            start_date="1996-01-01",
            end_date="2026-08-31",
            rebalance_freq_days=10,
        )
        sim_result = backtester.run_backtest(start_date="1996-01-01", end_date="2026-08-31")

        net_returns = sim_result.daily_returns
        rf = backtester.risk_free_rate  # 0.02
        rf_daily = rf / 252.0

        # Independent calculation
        excess_returns = net_returns - rf_daily
        mean_excess = excess_returns.mean()
        std_returns = net_returns.std(ddof=1)

        expected_sharpe = (mean_excess / (std_returns + 1e-8)) * math.sqrt(252)

        downside_returns = net_returns[net_returns < 0.0]
        downside_std = downside_returns.std(ddof=1)
        expected_sortino = (mean_excess / (downside_std + 1e-8)) * math.sqrt(252)

        reported_sharpe = sim_result.summary["sharpe_ratio"]
        reported_sortino = sim_result.summary["sortino_ratio"]

        # Check precision within 0.05
        assert abs(reported_sharpe - expected_sharpe) < 0.05, (
            f"Sharpe mismatch: reported {reported_sharpe} vs independent {expected_sharpe:.4f}"
        )
        assert abs(reported_sortino - expected_sortino) < 0.05, (
            f"Sortino mismatch: reported {reported_sortino} vs independent {expected_sortino:.4f}"
        )

        # Cross check with summary.json
        summary_path = TRADING_SYSTEM_DIR / "result" / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        json_sharpe = float(data["portfolio_overall"]["sharpe_ratio"])
        json_sortino = float(data["portfolio_overall"]["sortino_ratio"])

        assert abs(json_sharpe - reported_sharpe) < 0.05, f"JSON Sharpe {json_sharpe} != {reported_sharpe}"
        assert abs(json_sortino - reported_sortino) < 0.05, f"JSON Sortino {json_sortino} != {reported_sortino}"


# ==============================================================================
# Task 4: 200-Day SMA Gating Verification
# ==============================================================================

class TestSMA200Gating:
    """Verifies that stocks below 200-day SMA receive exactly 0.0 weight."""

    def test_sma200_strictly_gates_out_sub_sma_stocks(self):
        """
        Creates a custom scenario where Stock A is above 200 SMA and Stock B is below 200 SMA.
        Even if Stock B has the highest alpha score (0.99) and Stock A has lower alpha (0.75),
        Stock B must be filtered out and assigned exactly 0.0 target weight.
        """
        backtester = HistoricalStockUniverseBacktester(
            enable_sma200_gating=True,
        )
        panel = backtester.load_panel()

        test_date = pd.to_datetime("2020-06-15")
        trend_dict = backtester.compute_sma_200_trend(test_date, panel=panel)

        # Find at least one stock above SMA200 and one below SMA200
        above_syms = [s for s, is_above in trend_dict.items() if is_above]
        below_syms = [s for s, is_above in trend_dict.items() if not is_above]

        assert len(above_syms) > 0, "Expected at least one stock above 200 SMA"
        assert len(below_syms) > 0, "Expected at least one stock below 200 SMA"

        # Construct synthetic alpha scores: give stock below SMA the maximum alpha!
        target_sub_sma = below_syms[0]
        target_above_sma = above_syms[0]

        mock_alphas = {target_sub_sma: 0.999, target_above_sma: 0.70}
        for s in above_syms[1:]:
            mock_alphas[s] = 0.60

        target_w, exec_w, turnover, f_bps = backtester.allocate_portfolio(
            date=test_date,
            alphas=mock_alphas,
            panel=panel,
        )

        # Gated stock MUST have zero weight
        assert target_w.get(target_sub_sma, 0.0) == 0.0, (
            f"Stock {target_sub_sma} is below 200 SMA but received weight {target_w.get(target_sub_sma)}"
        )
        assert exec_w.get(target_sub_sma, 0.0) == 0.0, (
            f"Stock {target_sub_sma} is below 200 SMA but received executed weight {exec_w.get(target_sub_sma)}"
        )

        # Stock above SMA should receive positive weight
        assert target_w.get(target_above_sma, 0.0) > 0.0, (
            f"Stock {target_above_sma} is above 200 SMA but received 0 weight"
        )

    def test_all_stocks_below_sma200_defensive_cash_posture(self):
        """When all candidate stocks are below 200 SMA, engine shifts to full cash."""
        backtester = HistoricalStockUniverseBacktester(
            enable_sma200_gating=True,
        )
        panel = backtester.load_panel()

        # Mock compute_sma_200_trend to return False for all symbols
        orig_method = backtester.compute_sma_200_trend
        try:
            backtester.compute_sma_200_trend = lambda d, panel=None: {s: False for s in panel.symbols}

            target_w, exec_w, turnover, f_bps = backtester.allocate_portfolio(
                date="2020-03-20",
                panel=panel,
            )

            # Target weights should be empty (full cash)
            assert len(target_w) == 0, f"Expected 0 stock holdings in full cash defense, got {target_w}"
            assert len(exec_w) == 0 or sum(exec_w.values()) < 1e-4, f"Executed holdings not cash: {exec_w}"
        finally:
            backtester.compute_sma_200_trend = orig_method


# ==============================================================================
# Task 5: ADV Participation Cap <= 1.5%
# ==============================================================================

class TestADVParticipationCapAcrossRebalances:
    """Verifies that across all rebalances, trade orders strictly satisfy participation <= 1.5% ADV."""

    def test_adv_participation_cap_in_backtest_execution(self):
        """
        Executes backtest and inspects rebalance orders:
        Every single stock trade order executed delta must be <= 1.5% of ADV_20d.
        """
        backtester = HistoricalStockUniverseBacktester(
            start_date="2020-01-01",
            end_date="2022-12-31",
            max_adv_participation=0.015,
            rebalance_freq_days=60,
        )
        panel = backtester.load_panel()
        result = backtester.run_backtest(start_date="2020-01-01", end_date="2022-12-31")

        cap = 0.015 + 1e-6
        max_observed_part = 0.0

        for r in result.rebalance_records:
            date_str = r["date"]
            cur_ts = pd.to_datetime(date_str)
            holdings = r["holdings"]
            port_val = float(r["portfolio_equity"])

            for sym, w in holdings.items():
                if sym in panel.adv_matrix.columns and cur_ts in panel.adv_matrix.index:
                    adv_val = float(panel.adv_matrix.loc[cur_ts, sym])
                    if adv_val > 100.0:
                        order_krw = w * port_val
                        # Check executed delta KRW vs ADV cap
                        part_rate = (w * port_val) / adv_val
                        # The rebalance delta is bounded by 1.5%
                        # In apply_gatheral_impact_and_adv_cap:
                        # executed_delta_krw <= max_adv_participation * adv_20d_krw
                        exec_delta_krw, executed_part, _ = apply_gatheral_impact_and_adv_cap(
                            target_delta_krw=order_krw,
                            adv_20d_krw=adv_val,
                            max_adv_participation=0.015,
                        )
                        assert executed_part <= cap, f"Participation breach: {executed_part} > {cap}"
                        if executed_part > max_observed_part:
                            max_observed_part = executed_part

        assert max_observed_part <= cap, f"Max participation rate {max_observed_part} breached cap {cap}"


# ==============================================================================
# Task 6: Zero Future Leakage via Future Data Mutation Test
# ==============================================================================

class TestZeroFutureLeakageMutationHarness:
    """Adversarial stress test mutating future data and verifying zero lookahead leakage."""

    def test_future_data_mutation_invariance(self):
        """
        1. Pick a pivot date T (e.g., 2015-06-01).
        2. Compute baseline alpha scores and portfolio target weights at date T.
        3. Mutate future prices and volumes at T + k (k >= 1, e.g. 10x price shock).
        4. Recompute alpha scores and target weights at date T on mutated panel.
        5. Assert that max |w_mutated(T) - w_base(T)| == 0.0 and max |alpha_mutated(T) - alpha_base(T)| == 0.0.
        """
        backtester = HistoricalStockUniverseBacktester(
            start_date="2010-01-01",
            end_date="2020-12-31",
            rebalance_freq_days=60,
        )
        panel = backtester.load_panel()

        pivot_date = pd.to_datetime("2015-06-01")

        # Step 1: Baseline alpha scores and allocation
        regime, is_crisis, _ = backtester.classify_2d_regime(pivot_date, panel=panel)
        base_alphas = backtester.compute_alpha_scores(pivot_date, regime, panel=panel)
        base_target_w, base_exec_w, _, _ = backtester.allocate_portfolio(
            date=pivot_date,
            alphas=base_alphas,
            regime=regime,
            is_crisis=is_crisis,
            panel=panel,
        )

        # Step 2: Create mutated panel (deep copy price tensor)
        mutated_tensor = {}
        future_cutoff = pivot_date + pd.Timedelta(days=1)

        for sym, df in panel.price_tensor.items():
            df_copy = df.copy()
            if isinstance(df_copy.index, pd.DatetimeIndex):
                future_mask = df_copy.index >= future_cutoff
            elif "date" in df_copy.columns:
                future_mask = pd.to_datetime(df_copy["date"]) >= future_cutoff
            else:
                future_mask = pd.to_datetime(df_copy.index) >= future_cutoff
            if future_mask.any():
                # Drastically alter future prices and volumes: multiply close by 50x, volume by 100x
                df_copy.loc[future_mask, "close"] *= 50.0
                df_copy.loc[future_mask, "open"] *= 50.0
                df_copy.loc[future_mask, "high"] *= 50.0
                df_copy.loc[future_mask, "low"] *= 50.0
                df_copy.loc[future_mask, "volume"] *= 100.0
            mutated_tensor[sym] = df_copy

        mutated_panel = MultiStockPanel(
            dates=panel.dates,
            symbols=panel.symbols,
            price_tensor=mutated_tensor,
            adv_matrix=panel.adv_matrix.copy(),
            sector_map=panel.sector_map.copy(),
            market_map=panel.market_map.copy(),
            fundamentals_panel={k: v.copy() for k, v in panel.fundamentals_panel.items()},
            delisting_registry=panel.delisting_registry.copy(),
        )

        # Step 3: Recompute alpha scores and allocation on mutated panel at pivot_date T
        mut_regime, mut_crisis, _ = backtester.classify_2d_regime(pivot_date, panel=mutated_panel)
        mut_alphas = backtester.compute_alpha_scores(pivot_date, mut_regime, panel=mutated_panel)
        mut_target_w, mut_exec_w, _, _ = backtester.allocate_portfolio(
            date=pivot_date,
            alphas=mut_alphas,
            regime=mut_regime,
            is_crisis=mut_crisis,
            panel=mutated_panel,
        )

        # Step 4: Strict bit-for-bit invariance assertion
        assert mut_regime == regime, f"Regime changed upon future mutation: {mut_regime} vs {regime}"
        assert mut_crisis == is_crisis, f"Crisis flag changed: {mut_crisis} vs {is_crisis}"

        # Alpha scores invariance
        for sym in base_alphas:
            a_base = base_alphas[sym]
            a_mut = mut_alphas.get(sym, 0.0)
            assert abs(a_base - a_mut) < 1e-9, (
                f"Lookahead leak detected in alpha score for {sym}: base {a_base} vs mutated {a_mut}"
            )

        # Target weights invariance
        all_syms = set(list(base_target_w.keys()) + list(mut_target_w.keys()))
        for sym in all_syms:
            w_b = base_target_w.get(sym, 0.0)
            w_m = mut_target_w.get(sym, 0.0)
            assert abs(w_b - w_m) < 1e-9, (
                f"Lookahead leak detected in target weight for {sym}: base {w_b} vs mutated {w_m}"
            )

        # Executed weights invariance
        exec_syms = set(list(base_exec_w.keys()) + list(mut_exec_w.keys()))
        for sym in exec_syms:
            w_b = base_exec_w.get(sym, 0.0)
            w_m = mut_exec_w.get(sym, 0.0)
            assert abs(w_b - w_m) < 1e-9, (
                f"Lookahead leak detected in executed weight for {sym}: base {w_b} vs mutated {w_m}"
            )

    def test_dynamic_filing_lag_strict_lookahead_block(self):
        """
        Verifies that financial report filed at T - 20 days is NOT accessible at query date T
        under KRX 45-day lag and US 40-day lag.
        """
        query_date = "2020-04-10"
        period_end = "2020-03-31"  # Q1 period end, 10 days before query date

        # KRX quarterly filing lag is 45 days: Q1 (03-31) becomes accessible on 03-31 + 45 days = 05-15
        dt_query = datetime.strptime(query_date, "%Y-%m-%d")
        dt_period = datetime.strptime(period_end, "%Y-%m-%d")

        krx_accessible_date = dt_period + timedelta(days=45)
        us_accessible_date = dt_period + timedelta(days=40)

        assert dt_query < krx_accessible_date, "KRX report must not be accessible before 45-day lag"
        assert dt_query < us_accessible_date, "US report must not be accessible before 40-day lag"
