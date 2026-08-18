import os
import sys
import unittest
import numpy as np
import pandas as pd

# Add src and trading_system paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.risk.portfolio_allocator import PortfolioAllocator
from src.risk.portfolio_optimizer import PortfolioOptimizer
from src.execution.oms_engine import ExecutionOMSEngine


class TestWorldClassQuantEnhancements(unittest.TestCase):

    def setUp(self):
        self.ortho_engine = FactorOrthogonalizerEngine(default_method='pca_symmetric')
        self.ensemble_scorer = EnsembleScoringEngine()
        self.allocator = PortfolioAllocator(default_max_weight=0.25, risk_aversion=1.5)
        self.optimizer = PortfolioOptimizer(default_max_weight=0.25)
        self.oms = ExecutionOMSEngine(db_path=":memory:")

    # -------------------------------------------------------------------------
    # 1. Factor Orthogonalization: Sigmoid-Tanh Dispersion-Preserving Scaling
    # -------------------------------------------------------------------------
    def test_dispersion_preserving_orthogonalization(self):
        """Verify Sigmoid-Tanh dispersion-preserving orthogonalization preserves non-uniformity and decorrelates."""
        np.random.seed(42)
        n_symbols = 200
        latent = np.random.normal(0, 1, size=n_symbols)
        cols = ['strat_a', 'strat_b', 'strat_c', 'strat_d']
        data = {'symbol': [f"SYM_{i:04d}" for i in range(n_symbols)]}
        for c in cols:
            noise = np.random.normal(0, 1, size=n_symbols)
            raw = 0.8 * latent + 0.6 * noise
            data[c] = 1.0 / (1.0 + np.exp(-raw))

        df = pd.DataFrame(data)

        # Standard rank-based orthogonalization
        df_rank = self.ortho_engine.orthogonalize(df, cols, method='pca_symmetric', scaling_method='rank')
        # Dispersion-preserving orthogonalization
        df_disp = self.ortho_engine.orthogonalize(df, cols, method='pca_symmetric', scaling_method='dispersion')

        # Check bounds
        for c in cols:
            self.assertTrue((df_disp[c] >= 0.0).all())
            self.assertTrue((df_disp[c] <= 1.0).all())

        # Check decorrelation: correlation matrix off-diagonals should be small
        corr_disp = df_disp[cols].corr().values
        off_diag = corr_disp[~np.eye(len(cols), dtype=bool)]
        self.assertLess(float(np.mean(np.abs(off_diag))), 0.35)

        # Check dispersion standard deviation is healthy (> 0.05)
        for c in cols:
            self.assertGreater(float(df_disp[c].std()), 0.05)

    # -------------------------------------------------------------------------
    # 2. Dynamic Sharpe Reweighting: Smooth Continuous Downside Attenuation
    # -------------------------------------------------------------------------
    def test_smooth_downside_dynamic_sharpe_weighting(self):
        """Verify smooth continuous downside attenuation does not cause sharp cliff drop to 0% when requested."""
        sharpes = {'regression': 1.2, 'surge': -0.55, 'stat_arb': 0.8}
        # Hard pruning mode (default) -> surge is 0.0
        w_hard = self.ensemble_scorer.compute_dynamic_weights_from_sharpe(
            sharpes, regime='SIDEWAYS_LOW_VOL', smooth_downside_mode=False
        )
        self.assertEqual(w_hard.get('surge', 0.0), 0.0)

        # Smooth downside attenuation mode -> surge is > 0.0 but significantly dampened
        w_smooth = self.ensemble_scorer.compute_dynamic_weights_from_sharpe(
            sharpes, regime='SIDEWAYS_LOW_VOL', smooth_downside_mode=True
        )
        self.assertGreater(w_smooth.get('surge', 0.0), 0.0)
        self.assertLess(w_smooth.get('surge', 0.0), w_smooth.get('stat_arb', 0.0))
        self.assertAlmostEqual(sum(w_smooth.values()), 1.0, places=5)

    # -------------------------------------------------------------------------
    # 3. Portfolio Allocator: Turnover-Regularized Convex Optimization
    # -------------------------------------------------------------------------
    def test_turnover_regularized_portfolio_optimization(self):
        """Verify turnover regularization suppresses churning towards previous weights."""
        np.random.seed(101)
        symbols = ['005930', '000660', '035420', '051910', '005380']
        n_obs = 60
        returns_dict = {sym: np.random.normal(0.001, 0.02, n_obs) for sym in symbols}
        returns_df = pd.DataFrame(returns_dict)

        expected_returns = pd.Series({
            '005930': 0.05,
            '000660': 0.08,
            '035420': 0.03,
            '051910': 0.02,
            '005380': 0.04
        })

        # Previous portfolio concentrated in 005930 and 035420
        prev_weights = {'005930': 0.40, '000660': 0.10, '035420': 0.30, '051910': 0.10, '005380': 0.10}

        # Optimization without turnover penalty
        w_unconstrained = self.allocator.optimize_turnover_regularized_portfolio(
            expected_returns=expected_returns,
            returns_df=returns_df,
            previous_weights=prev_weights,
            turnover_penalty_l1=0.0,
            turnover_penalty_l2=0.0,
            max_weight=0.35
        )

        # Optimization with turnover penalty
        w_regularized = self.allocator.optimize_turnover_regularized_portfolio(
            expected_returns=expected_returns,
            returns_df=returns_df,
            previous_weights=prev_weights,
            turnover_penalty_l1=0.20,
            turnover_penalty_l2=0.10,
            max_weight=0.35
        )

        # Calculate turnovers
        t_unconstrained = sum(abs(w_unconstrained[s] - prev_weights[s]) for s in symbols)
        t_regularized = sum(abs(w_regularized[s] - prev_weights[s]) for s in symbols)

        # Regularized turnover should be strictly lower than unconstrained
        self.assertLess(t_regularized, t_unconstrained)
        self.assertAlmostEqual(sum(w_regularized.values()), 1.0, places=5)

    # -------------------------------------------------------------------------
    # 4. Portfolio Optimizer: Mean-Variance Turnover Regularization
    # -------------------------------------------------------------------------
    def test_mvo_turnover_penalty(self):
        """Verify PortfolioOptimizer.optimize_mean_variance penalizes turnover."""
        np.random.seed(202)
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
        returns_df = pd.DataFrame({s: np.random.normal(0.001, 0.015, 50) for s in symbols})
        exp_rets = pd.Series({'AAPL': 0.12, 'MSFT': 0.05, 'GOOGL': 0.04, 'AMZN': 0.02})
        prev_w = {'AAPL': 0.10, 'MSFT': 0.40, 'GOOGL': 0.30, 'AMZN': 0.20}

        w_no_penalty = self.optimizer.optimize_mean_variance(
            exp_rets, returns_df, max_weight=0.50, turnover_penalty=0.0
        )
        w_with_penalty = self.optimizer.optimize_mean_variance(
            exp_rets, returns_df, max_weight=0.50, previous_weights=prev_w, turnover_penalty=0.15
        )

        turnover_0 = sum(abs(w_no_penalty[s] - prev_w[s]) for s in symbols)
        turnover_pen = sum(abs(w_with_penalty[s] - prev_w[s]) for s in symbols)
        self.assertLessEqual(turnover_pen, turnover_0)

    # -------------------------------------------------------------------------
    # 5. Execution OMS: Exchange Tick Size Grid Compliance (KRX & US)
    # -------------------------------------------------------------------------
    def test_krx_and_us_tick_size_grid(self):
        """Verify KRX 7-tier tick sizes and US cent/sub-penny tick rules."""
        # KRX (<2,000 KRW -> 1 KRW tick)
        self.assertEqual(ExecutionOMSEngine.round_to_tick_size(1452.3, "KOSPI"), 1452.0)
        # KRX (2,000 ~ 5,000 KRW -> 5 KRW tick)
        self.assertEqual(ExecutionOMSEngine.round_to_tick_size(3452.3, "KOSPI"), 3450.0)
        self.assertEqual(ExecutionOMSEngine.round_to_tick_size(3453.8, "KOSPI"), 3455.0)
        # KRX (5,000 ~ 20,000 KRW -> 10 KRW tick)
        self.assertEqual(ExecutionOMSEngine.round_to_tick_size(12347.0, "KOSPI"), 12350.0)
        # KRX (20,000 ~ 50,000 KRW -> 50 KRW tick)
        self.assertEqual(ExecutionOMSEngine.round_to_tick_size(34520.0, "KOSDAQ"), 34500.0)
        self.assertEqual(ExecutionOMSEngine.round_to_tick_size(34535.0, "KOSDAQ"), 34550.0)
        # KRX (50,000 ~ 200,000 KRW -> 100 KRW tick)
        self.assertEqual(ExecutionOMSEngine.round_to_tick_size(78940.0, "KOSPI"), 78900.0)
        self.assertEqual(ExecutionOMSEngine.round_to_tick_size(78960.0, "KOSPI"), 79000.0)
        # KRX (200,000 ~ 500,000 KRW -> 500 KRW tick)
        self.assertEqual(ExecutionOMSEngine.round_to_tick_size(245200.0, "KOSPI"), 245000.0)
        self.assertEqual(ExecutionOMSEngine.round_to_tick_size(245350.0, "KOSPI"), 245500.0)
        # KRX (>= 500,000 KRW -> 1,000 KRW tick)
        self.assertEqual(ExecutionOMSEngine.round_to_tick_size(684400.0, "KOSPI"), 684000.0)
        self.assertEqual(ExecutionOMSEngine.round_to_tick_size(684600.0, "KOSPI"), 685000.0)

        # US (>= $1.00 -> $0.01 cent tick)
        self.assertEqual(ExecutionOMSEngine.round_to_tick_size(145.2384, "SP500"), 145.24)
        # US (< $1.00 -> $0.0001 sub-penny tick)
        self.assertEqual(ExecutionOMSEngine.round_to_tick_size(0.45678, "NASDAQ"), 0.4568)

    def test_order_plan_generation_with_tick_sizes(self):
        """Verify generate_order_plan produces tick-rounded prices."""
        top_preds = [
            {
                "symbol": "005930",
                "name": "삼성전자",
                "market": "KOSPI",
                "close_price": 78940.0,
                "target_price": 78940.0,
                "expected_return": 15.0
            },
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "market": "SP500",
                "close_price": 224.5678,
                "target_price": 224.5678,
                "expected_return": 12.0
            }
        ]
        portfolio_weights = {"005930": 0.20, "AAPL": 0.15}

        plans = self.oms.generate_order_plan(
            top_predictions=top_preds,
            portfolio_weights=portfolio_weights,
            total_capital=100000000.0,
            crisis_level="NORMAL"
        )

        self.assertGreater(len(plans), 0)
        for p in plans:
            if p["symbol"] == "005930":
                # Must be rounded to 100 KRW tick (78,900 KRW)
                self.assertEqual(p["target_price"], 78900.0)
            elif p["symbol"] == "AAPL":
                # Must be rounded to 0.01 USD tick (224.57 USD)
                self.assertEqual(p["target_price"], 224.57)


if __name__ == "__main__":
    unittest.main()
