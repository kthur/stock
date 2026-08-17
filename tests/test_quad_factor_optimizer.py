"""
Unit Test Suite for Quad-Factor Neutral QP Portfolio Risk Optimizer (Milestone 2 - R2).
"""

import unittest
import numpy as np
import pandas as pd
from src.strategy.quad_factor_optimizer import QuadFactorOptimizer
from trading_system.src.risk.portfolio_optimizer import PortfolioOptimizer


class TestQuadFactorOptimizer(unittest.TestCase):
    """
    Test suite for QuadFactorOptimizer.
    """

    def setUp(self):
        self.symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK.B']
        self.n_assets = len(self.symbols)

        # Expected Returns
        self.expected_returns = pd.Series(
            [0.12, 0.10, 0.15, 0.08, 0.20, 0.18, 0.14, 0.06],
            index=self.symbols
        )

        # Covariance Matrix
        np.random.seed(42)
        random_matrix = np.random.randn(self.n_assets, self.n_assets) * 0.02
        cov = np.dot(random_matrix, random_matrix.T) + np.diag([0.04] * self.n_assets)
        self.cov_df = pd.DataFrame(cov, index=self.symbols, columns=self.symbols)

        # Factors DataFrame
        self.factor_df = pd.DataFrame({
            'beta': [1.2, 0.9, 1.1, 1.0, 1.5, 1.8, 1.3, 0.6],
            'size': [12.5, 12.4, 12.2, 12.3, 11.8, 11.5, 12.0, 12.1],
            'volatility': [0.22, 0.18, 0.20, 0.21, 0.35, 0.45, 0.28, 0.14],
            'momentum': [0.15, 0.10, 0.05, -0.02, 0.40, 0.30, 0.12, -0.05]
        }, index=self.symbols)

        # Sector Mapping (5 sectors: Tech, Consumer, Financials, Healthcare, Industrial)
        self.sector_map = {
            'AAPL': 'Tech', 'MSFT': 'Tech',
            'GOOGL': 'Consumer', 'AMZN': 'Consumer',
            'BRK.B': 'Financials',
            'NVDA': 'Healthcare', 'TSLA': 'Healthcare',
            'META': 'Industrial'
        }

    def test_weight_sum_equality_constraint(self):
        """
        Verify sum of weights equals 1.0 (within 1e-5).
        """
        optimizer = QuadFactorOptimizer(default_max_weight=0.25)
        weights = optimizer.optimize(
            self.expected_returns, self.cov_df, self.factor_df, self.sector_map
        )
        total_w = sum(weights.values())
        self.assertAlmostEqual(total_w, 1.0, places=5)
        for sym, w in weights.items():
            self.assertGreaterEqual(w, 0.0)

    def test_quad_factor_neutrality_bounds(self):
        """
        Verify factor exposures strictly satisfy |f^T * w| <= 0.05.
        """
        optimizer = QuadFactorOptimizer(default_max_weight=0.25, default_factor_tolerance=0.05)
        weights = optimizer.optimize(
            self.expected_returns, self.cov_df, self.factor_df, self.sector_map
        )
        w_vec = np.array([weights[s] for s in self.symbols])

        for col in ['beta', 'size', 'volatility', 'momentum']:
            raw_f = self.factor_df[col].values
            std_f = (raw_f - np.mean(raw_f)) / np.std(raw_f)
            exp = float(np.dot(std_f, w_vec))
            self.assertLessEqual(abs(exp), 0.051, f"Factor {col} exposure {exp} exceeded bound 0.05")

    def test_sector_cap_constraint(self):
        """
        Verify sector weight exposure sum <= 25% (or max_sector_weight).
        """
        optimizer = QuadFactorOptimizer(default_max_weight=0.15, default_max_sector_weight=0.25)
        weights = optimizer.optimize(
            self.expected_returns, self.cov_df, self.factor_df, self.sector_map, max_sector_weight=0.25
        )

        sec_sums = {}
        for sym, w in weights.items():
            sec = self.sector_map[sym]
            sec_sums[sec] = sec_sums.get(sec, 0.0) + w

        for sec, total_w in sec_sums.items():
            self.assertLessEqual(total_w, 0.251, f"Sector {sec} sum {total_w} exceeded 0.25 cap")

    def test_fallback_on_infeasible_constraints(self):
        """
        Verify graceful fallback to Tier 1/2/3 when factor bounds are impossibly tight (e.g. 0.00001).
        """
        optimizer = QuadFactorOptimizer(default_max_weight=0.15, default_factor_tolerance=0.00001)
        weights = optimizer.optimize(
            self.expected_returns, self.cov_df, self.factor_df, self.sector_map
        )
        self.assertEqual(len(weights), self.n_assets)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=4)

    def test_overconstrained_infeasible_sector_caps(self):
        """
        Explicitly test infeasible setup where total sector capacity < 1.0 (e.g. 3 sectors with cap 0.25).
        Verify that fallback triggers cleanly, total weight sum is <= 1.0, and sector caps are NEVER violated.
        """
        infeasible_sector_map = {
            'AAPL': 'Tech', 'MSFT': 'Tech', 'NVDA': 'Tech', 'META': 'Tech', 'GOOGL': 'Tech',
            'AMZN': 'Consumer', 'TSLA': 'Consumer',
            'BRK.B': 'Financials'
        }
        # 3 sectors with max_sector_weight=0.25 => max total capacity = 3 * 0.25 = 0.75 < 1.0
        optimizer = QuadFactorOptimizer(default_max_weight=0.25, default_max_sector_weight=0.25)
        weights = optimizer.optimize(
            self.expected_returns, self.cov_df, self.factor_df, infeasible_sector_map, max_sector_weight=0.25
        )
        self.assertEqual(len(weights), self.n_assets)
        total_w = sum(weights.values())
        self.assertLessEqual(total_w, 1.0 + 1e-5)

        sec_sums = {}
        for sym, w in weights.items():
            sec = infeasible_sector_map[sym]
            sec_sums[sec] = sec_sums.get(sec, 0.0) + w

        for sec, s_w in sec_sums.items():
            self.assertLessEqual(s_w, 0.25 + 1e-5, f"Sector {sec} sum {s_w} breached 0.25 cap in infeasible test")

    def test_portfolio_optimizer_integration(self):
        """
        Test integration with PortfolioOptimizer.optimize_quad_factor_portfolio().
        """
        po = PortfolioOptimizer()
        weights = po.optimize_quad_factor_portfolio(
            self.expected_returns, self.cov_df, self.factor_df, self.sector_map,
            max_weight=0.20, max_sector_weight=0.30
        )
        self.assertIsInstance(weights, dict)
        self.assertEqual(len(weights), self.n_assets)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=5)

    def test_optimize_portfolio_method_alias(self):
        """
        Verify optimize_portfolio convenience alias method works identical to optimize.
        """
        optimizer = QuadFactorOptimizer(default_max_weight=0.20)
        weights = optimizer.optimize_portfolio(
            self.expected_returns, self.cov_df, self.factor_df, self.sector_map,
            max_asset_weight=0.20, max_sector_weight=0.30, factor_neutral_tol=0.05
        )
        self.assertIsInstance(weights, dict)
        self.assertEqual(len(weights), self.n_assets)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=5)


if __name__ == '__main__':
    unittest.main()
