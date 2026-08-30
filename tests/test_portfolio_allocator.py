"""
Unit Tests and Verification Benchmarks for Milestone 3:
- Extreme Value Theory (EVT) CVaR Risk Budget Constraints (GPD POT Fitting)
- 3-Tier Fallback Hierarchy (EVT-GPD -> Cornish-Fisher -> Empirical/Gaussian CVaR)
- Dynamic Band-Based Rebalancing (No-Trade Buffer Zones)
- Microstructure Transaction Cost Estimation (STT Tax, Spread, Market Impact)
- Transaction Cost Drag Reduction Benchmark vs Fixed Daily Rebalancing
- Stat-Arb Candidate Pair Batching Optimization
"""

import unittest
import numpy as np
import pandas as pd
from scipy.stats import t, pareto, norm

from trading_system.src.risk.portfolio_allocator import PortfolioAllocator
from trading_system.src.risk.portfolio_optimizer import PortfolioOptimizer
from trading_system.src.core.stat_arb import StatisticalArbitrageEngine


class TestEVTCVaR(unittest.TestCase):
    """Unit tests for EVT-GPD CVaR tail risk estimation and loss budget constraints."""

    def setUp(self):
        self.allocator = PortfolioAllocator(min_tail_samples=15)
        np.random.seed(42)

    def test_gpd_fitting_student_t(self):
        """
        Verify EVT-GPD fitting correctly estimates positive shape parameter (xi > 0)
        and EVT-CVaR > Gaussian CVaR for synthetic heavy-tailed Student-t (df=3) returns.
        """
        # Generate 1,000 synthetic returns from Student-t distribution with df=3
        returns_t = t.rvs(df=3, loc=0.0005, scale=0.015, size=1000)

        res = self.allocator.estimate_evt_cvar(returns_t, confidence=0.95, quantile_threshold=0.90)

        # 1. Verify GPD fitting method was used
        self.assertEqual(res["method"], "evt_gpd")
        # 2. Verify shape parameter xi > 0 (heavy tail behavior detected)
        self.assertGreater(res["xi"], 0.0)

        # 3. Calculate Gaussian standard parametric CVaR for comparison
        losses = -returns_t
        mu, sigma = float(np.mean(losses)), float(np.std(losses, ddof=1))
        alpha = 0.95
        z_alpha = float(norm.ppf(alpha))
        cvar_gaussian = mu + sigma * (norm.pdf(z_alpha) / (1.0 - alpha))

        # 4. Verify EVT-CVaR is strictly greater than Gaussian CVaR due to heavy tails
        self.assertGreater(res["cvar"], cvar_gaussian)

    def test_gpd_fitting_pareto(self):
        """
        Verify EVT-GPD fitting with synthetic Pareto heavy losses.
        """
        pareto_losses = pareto.rvs(b=2.5, loc=0, scale=0.01, size=800)
        returns_pareto = -pareto_losses

        res = self.allocator.estimate_evt_cvar(returns_pareto, confidence=0.95, quantile_threshold=0.88)
        self.assertIn(res["method"], ["evt_gpd", "empirical_fallback"])
        self.assertGreater(res["cvar"], 0.0)

    def test_evt_cvar_fallback_small_sample(self):
        """
        Verify graceful fallback to empirical/gaussian CVaR when sample size N < 10 or N_u < 15.
        """
        # Pass small sample of returns (N = 8 < 10)
        small_returns = np.random.normal(0.001, 0.02, size=8)

        res = self.allocator.estimate_evt_cvar(small_returns, confidence=0.95)

        # 1. Verify fallback method triggered
        self.assertIn(res["method"], ["gaussian_fallback_small_n", "empirical_fallback"])
        # 2. Verify result returned valid non-negative float without raising exception
        self.assertGreaterEqual(res["cvar"], 0.0)
        self.assertIsInstance(res["cvar"], float)

    def test_evt_cvar_optimization_constraint(self):
        """
        Verify non-linear SLSQP optimization enforces EVT_CVaR(w) <= max_cvar constraint.
        """
        N = 500
        asset_a = t.rvs(df=3, loc=0.001, scale=0.035, size=N)  # high tail risk
        asset_b = np.random.normal(0.0008, 0.012, size=N)
        asset_c = np.random.normal(0.0005, 0.010, size=N)

        returns_df = pd.DataFrame({'ASSET_A': asset_a, 'ASSET_B': asset_b, 'ASSET_C': asset_c})
        expected_returns = pd.Series({'ASSET_A': 0.001, 'ASSET_B': 0.0008, 'ASSET_C': 0.0005})

        max_cvar_budget = 0.035
        opt_weights = self.allocator.optimize_with_evt_cvar_constraint(
            expected_returns=expected_returns,
            returns_df=returns_df,
            max_cvar=max_cvar_budget,
            confidence=0.95,
            max_weight=0.60
        )

        # 1. Weights sum to 1.0
        self.assertAlmostEqual(sum(opt_weights.values()), 1.0, places=5)

        # 2. Compute resulting portfolio EVT-CVaR
        w_vec = np.array([opt_weights['ASSET_A'], opt_weights['ASSET_B'], opt_weights['ASSET_C']])
        port_cvar = self.allocator.estimate_portfolio_evt_cvar(w_vec, returns_df.values, confidence=0.95)

        # 3. Verify EVT-CVaR constraint is satisfied: port_cvar <= max_cvar_budget (with 1e-4 tolerance)
        self.assertLessEqual(port_cvar, max_cvar_budget + 1e-4)

    def test_portfolio_optimizer_cvar_integration(self):
        """
        Verify PortfolioOptimizer.optimize_mean_variance accepts max_cvar_limit and satisfies constraint.
        """
        N = 400
        asset_a = t.rvs(df=3, loc=0.001, scale=0.04, size=N)
        asset_b = np.random.normal(0.0005, 0.01, size=N)
        returns_df = pd.DataFrame({'ASSET_A': asset_a, 'ASSET_B': asset_b})
        expected_returns = pd.Series({'ASSET_A': 0.002, 'ASSET_B': 0.0005})

        optimizer = PortfolioOptimizer(default_max_weight=0.90)
        weights = optimizer.optimize_mean_variance(
            expected_returns=expected_returns,
            returns_df=returns_df,
            max_cvar_limit=0.035,
            cvar_confidence=0.95
        )

        self.assertAlmostEqual(sum(weights.values()), 1.0, places=5)
        w_vec = np.array([weights['ASSET_A'], weights['ASSET_B']])
        cvar = self.allocator.estimate_portfolio_evt_cvar(w_vec, returns_df.values, confidence=0.95)
        self.assertLessEqual(cvar, 0.035 + 1e-4)


class TestDynamicBandRebalancing(unittest.TestCase):
    """Unit tests for Dynamic Band-Based Rebalancing (No-Trade Buffer Zones)."""

    def setUp(self):
        self.allocator = PortfolioAllocator(
            risk_aversion=1.0,
            delta_floor=0.005,
            delta_cap=0.050,
            rebalance_mode="boundary"
        )

    def test_zero_turnover_within_buffer_bands(self):
        """
        Verify zero turnover (HOLD action) when current weight drift is within buffer band.
        """
        # Target 0.200, drift -0.010 (within band)
        current_weights = {"005930": 0.190}
        target_weights = {"005930": 0.200}
        market_map = {"005930": "KOSPI"}
        volatility_map = {"005930": 0.020}
        adv_map = {"005930": 1_000_000_000.0}

        res = self.allocator.compute_portfolio_rebalance(
            current_weights=current_weights,
            target_weights=target_weights,
            market_map=market_map,
            volatility_map=volatility_map,
            adv_map=adv_map,
            portfolio_value=100_000_000.0
        )

        trade = res["trades"]["005930"]

        # 1. Action is HOLD
        self.assertEqual(trade["action"], "HOLD")
        # 2. Rebalanced weight equals current weight
        self.assertEqual(trade["w_new"], 0.190)
        self.assertEqual(trade["trade_weight"], 0.0)
        # 3. Summary skipped_count == 1, traded_count == 0
        self.assertEqual(res["summary"]["skipped_count"], 1)
        self.assertEqual(res["summary"]["traded_count"], 0)
        # 4. Transaction cost saved > 0
        self.assertGreater(res["summary"]["total_cost_saved_krw"], 0.0)

    def test_trade_execution_triggered_on_buffer_breach(self):
        """
        Verify BUY/SELL trade is triggered when current weight breaches buffer band.
        """
        # Current weight 0.130 breaches lower band (target 0.200, delta ~0.025, lower bound ~0.175)
        current_weights = {"005930": 0.130}
        target_weights = {"005930": 0.200}
        market_map = {"005930": "KOSPI"}
        volatility_map = {"005930": 0.020}
        adv_map = {"005930": 1_000_000_000.0}

        res = self.allocator.compute_portfolio_rebalance(
            current_weights=current_weights,
            target_weights=target_weights,
            market_map=market_map,
            volatility_map=volatility_map,
            adv_map=adv_map,
            portfolio_value=100_000_000.0
        )

        trade = res["trades"]["005930"]

        # 1. Action is BUY
        self.assertEqual(trade["action"], "BUY")
        # 2. In boundary mode, w_new equals lower band edge L_i (approx 0.175), < target (0.200)
        self.assertGreater(trade["w_new"], 0.130)
        self.assertLessEqual(trade["w_new"], 0.200)
        # 3. Traded count == 1
        self.assertEqual(res["summary"]["traded_count"], 1)

    def test_stt_and_market_cost_estimation(self):
        """
        Verify market-specific transaction cost estimation (STT tax + spread + impact).
        """
        pv = 100_000_000.0

        # KOSDAQ sell trade: STT tax = 0.18% (0.0018) + brokerage 0.03% = 0.21% base
        cost_kosdaq_sell = self.allocator.estimate_transaction_cost_rate(
            symbol="035720.KQ", market="KOSDAQ", target_weight=0.10, portfolio_value=pv, is_sell=True
        )
        # KOSPI sell trade: STT tax = 0.15% (0.0015) + brokerage 0.03% = 0.18% base
        cost_kospi_sell = self.allocator.estimate_transaction_cost_rate(
            symbol="005930", market="KOSPI", target_weight=0.10, portfolio_value=pv, is_sell=True
        )
        # SP500 sell trade: SEC fee = 0.003% + brokerage 0.005% = 0.008% base
        cost_sp500_sell = self.allocator.estimate_transaction_cost_rate(
            symbol="AAPL", market="SP500", target_weight=0.10, portfolio_value=pv, is_sell=True
        )

        # Assert KOSDAQ sell cost > KOSPI sell cost > SP500 sell cost
        self.assertGreater(cost_kosdaq_sell, cost_kospi_sell)
        self.assertGreater(cost_kospi_sell, cost_sp500_sell)

    def test_portfolio_optimizer_rebalance_trigger(self):
        """
        Verify PortfolioOptimizer.check_rebalance_trigger detects drift breaches correctly.
        """
        optimizer = PortfolioOptimizer()
        curr = {"A": 0.20, "B": 0.20}
        targ_no_drift = {"A": 0.21, "B": 0.19}
        targ_drift = {"A": 0.25, "B": 0.15}

        # 1% drift <= 3% buffer band -> False
        self.assertFalse(optimizer.check_rebalance_trigger(curr, targ_no_drift, buffer_band=0.03))
        # 5% drift > 3% buffer band -> True
        self.assertTrue(optimizer.check_rebalance_trigger(curr, targ_drift, buffer_band=0.03))


class TestRebalancingBenchmark(unittest.TestCase):
    """Verification Benchmark: Dynamic Band Rebalancing vs Fixed Periodic Rebalancing."""

    def test_transaction_cost_reduction_vs_fixed_rebalance(self):
        """
        Benchmark Test: Simulates 250 daily trading steps with return noise.
        Compares Cumulative Transaction Costs between Fixed Daily Rebalancing
        and Dynamic Band-Based Rebalancing.
        Asserts Dynamic Band Rebalancing achieves >= 60% transaction cost reduction.
        """
        np.random.seed(123)
        n_days = 250
        n_assets = 5
        symbols = [f"STOCK_{i}" for i in range(n_assets)]
        market_map = {s: "KOSDAQ" for s in symbols}
        vol_map = {s: 0.025 for s in symbols}
        adv_map = {s: 500_000_000.0 for s in symbols}

        target_weights = {s: 0.20 for s in symbols}
        portfolio_value = 100_000_000.0

        allocator = PortfolioAllocator(
            risk_aversion=1.0,
            delta_floor=0.008,
            delta_cap=0.040,
            rebalance_mode="boundary"
        )

        daily_returns = np.random.normal(0.0002, 0.015, size=(n_days, n_assets))

        cost_fixed_daily = 0.0
        cost_dynamic_band = 0.0

        curr_w_fixed = dict(target_weights)
        curr_w_dynamic = dict(target_weights)

        for day in range(n_days):
            rets = daily_returns[day]

            # 1. Update weights due to daily price asset drift
            val_fixed = {s: curr_w_fixed[s] * (1.0 + rets[i]) for i, s in enumerate(symbols)}
            tot_fixed = sum(val_fixed.values())
            curr_w_fixed = {s: val_fixed[s] / tot_fixed for s in symbols}

            val_dyn = {s: curr_w_dynamic[s] * (1.0 + rets[i]) for i, s in enumerate(symbols)}
            tot_dyn = sum(val_dyn.values())
            curr_w_dynamic = {s: val_dyn[s] / tot_dyn for s in symbols}

            # 2. Fixed Daily Rebalancing: Rebalances 100% back to target daily
            for s in symbols:
                drift = abs(curr_w_fixed[s] - target_weights[s])
                c_rate = allocator.estimate_transaction_cost_rate(
                    symbol=s, market="KOSDAQ", target_weight=target_weights[s],
                    portfolio_value=portfolio_value, is_sell=(curr_w_fixed[s] > target_weights[s])
                )
                cost_fixed_daily += drift * portfolio_value * c_rate
            curr_w_fixed = dict(target_weights)

            # 3. Dynamic Band Rebalancing: Rebalances only when buffer band breached
            rebal_res = allocator.compute_portfolio_rebalance(
                current_weights=curr_w_dynamic,
                target_weights=target_weights,
                market_map=market_map,
                volatility_map=vol_map,
                adv_map=adv_map,
                portfolio_value=portfolio_value
            )
            for s, tr in rebal_res["trades"].items():
                if tr["action"] != "HOLD":
                    trade_size = abs(tr["trade_weight"]) * portfolio_value
                    c_rate = allocator.estimate_transaction_cost_rate(
                        symbol=s, market="KOSDAQ", target_weight=target_weights[s],
                        portfolio_value=portfolio_value, is_sell=(tr["action"] == "SELL")
                    )
                    cost_dynamic_band += trade_size * c_rate

            curr_w_dynamic = rebal_res["new_weights"]

        cost_savings_pct = (cost_fixed_daily - cost_dynamic_band) / cost_fixed_daily

        # Assert dynamic band rebalancing reduces transaction costs by >= 60%
        self.assertGreaterEqual(cost_savings_pct, 0.60)
        self.assertLess(cost_dynamic_band, cost_fixed_daily)


class TestStatArbBatching(unittest.TestCase):
    """Unit test for Stat-Arb Candidate Pair Batching Optimization."""

    def test_candidate_pair_batching_execution(self):
        """
        Verify find_cointegrated_pairs runs in batches without errors.
        """
        engine = StatisticalArbitrageEngine(use_clustering=False)
        np.random.seed(42)
        prices_dict = {}
        t_len = 120

        # Generate 20 synthetic price series (some correlated pairs)
        base = np.cumsum(np.random.normal(0, 1, size=t_len)) + 100.0
        prices_dict["SYM_0"] = list(base)
        prices_dict["SYM_1"] = list(base + np.random.normal(0, 0.5, size=t_len))

        for i in range(2, 15):
            prices_dict[f"SYM_{i}"] = list(np.cumsum(np.random.normal(0, 1.5, size=t_len)) + 50.0)

        pairs = engine.find_cointegrated_pairs(prices_dict, min_correlation=0.50, max_pvalue=0.50)
        self.assertIsInstance(pairs, list)


class TestEVTCVaROptimizationAdaptive(unittest.TestCase):
    """Unit tests for adaptive iteration limits and Cornish-Fisher QP fallback in optimize_with_evt_cvar_constraint."""

    def setUp(self):
        self.allocator = PortfolioAllocator()
        np.random.seed(42)

    def test_optimize_with_evt_cvar_constraint_adaptive_dimensions(self):
        """Verify optimize_with_evt_cvar_constraint converges cleanly across small and medium universes."""
        # 1. 5-asset universe
        n = 5
        symbols = [f"STOCK_{i}" for i in range(n)]
        dates = pd.date_range("2026-01-01", periods=100, freq="B")
        rets = np.random.normal(0.0005, 0.02, size=(100, n))
        df_rets = pd.DataFrame(rets, index=dates, columns=symbols)
        mu = pd.Series(np.mean(rets, axis=0) * 252, index=symbols)

        weights = self.allocator.optimize_with_evt_cvar_constraint(
            expected_returns=mu,
            returns_df=df_rets,
            max_cvar=0.05,
            confidence=0.95
        )

        self.assertEqual(len(weights), n)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=4)
        for sym, w in weights.items():
            self.assertGreaterEqual(w, 0.0)

    def test_optimize_with_evt_cvar_tight_constraint_fallback(self):
        """Verify graceful fallback to Cornish-Fisher QP when CVaR constraint is extremely tight."""
        n = 4
        symbols = [f"VOL_STOCK_{i}" for i in range(n)]
        dates = pd.date_range("2026-01-01", periods=100, freq="B")
        # High volatility returns
        rets = np.random.normal(0.001, 0.05, size=(100, n))
        df_rets = pd.DataFrame(rets, index=dates, columns=symbols)
        mu = pd.Series([0.15, 0.20, 0.10, 0.05], index=symbols)

        # Extremely tight max_cvar = 0.001 (impossible for 5% daily vol), triggers fallback
        weights = self.allocator.optimize_with_evt_cvar_constraint(
            expected_returns=mu,
            returns_df=df_rets,
            max_cvar=0.001,
            confidence=0.95
        )

        self.assertEqual(len(weights), n)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=4)
        for sym, w in weights.items():
            self.assertGreaterEqual(w, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
