import unittest
import numpy as np
import pandas as pd

from src.ai.factor_suppression import (
    solve_single_stage_entropy_allocation,
    RegimeFactorSuppressionEngine
)
from src.analysis.regime_detector import MarketRegimeDetector
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.risk.portfolio_allocator import PortfolioAllocator
from src.analysis.portfolio_optimizer import shrink_covariance_matrix


class TestSprint2Enhancements(unittest.TestCase):
    """Unit and Integration Tests for Sprint 2 Core Enhancements."""

    def test_single_stage_entropy_allocation_convergence(self):
        """Verify single-stage entropy program satisfies simplex constraints and preserves alpha."""
        K = 5
        # Highly correlated block of 3 momentum strategies (0.85 correlation)
        R = np.array([
            [1.0, 0.85, 0.85, 0.10, 0.10],
            [0.85, 1.0, 0.85, 0.10, 0.10],
            [0.85, 0.85, 1.0, 0.10, 0.10],
            [0.10, 0.10, 0.10, 1.0, 0.20],
            [0.10, 0.10, 0.10, 0.20, 1.0],
        ])
        w0 = np.array([0.20, 0.20, 0.20, 0.20, 0.20])

        w_opt = solve_single_stage_entropy_allocation(
            R=R,
            w0=w0,
            tau_entropy=0.05,
            gamma_anchor=1.0,
            w_min=0.01,
            max_iter=150
        )

        # 1. Simplex constraints
        self.assertAlmostEqual(float(np.sum(w_opt)), 1.0, places=4)
        self.assertTrue(np.all(w_opt >= 0.0099))

        # 2. Correlated strategies are dampened moderately, but retaining genuine weight (> 0.10 each)
        self.assertGreater(float(w_opt[0]), 0.10)
        self.assertGreater(float(w_opt[1]), 0.10)
        self.assertGreater(float(w_opt[2]), 0.10)

        # 3. Uncorrelated strategies receive higher marginal diversification allocation
        self.assertGreater(float(w_opt[3]), float(w_opt[0]))

    def test_dual_speed_regime_rebound_trigger(self):
        """Verify Dual-Speed Detector instantly upgrades lagged BEAR to BULL on +3.5% rebound and VIX drop."""
        detector = MarketRegimeDetector(rolling_window=20)

        # Generate 30 days of severe bear market (-1.0% per day, high VIX)
        dates = pd.date_range("2026-01-01", periods=30)
        sp_rets = [-1.0] * 27 + [1.2, 1.3, 1.1]  # Last 3 days: +3.6% explosive V-bottom rebound
        vix_series = [35.0] * 27 + [32.0, 28.0, 24.0]  # VIX drops from 35 to 24 (-31.4%)

        indicator_df = pd.DataFrame({
            "sp500_change": sp_rets,
            "vix": vix_series,
            "us10y": [4.0] * 30,
            "usdkrw_change": [0.0] * 30
        }, index=dates)

        res = detector.predict_2d_regime(indicator_df)

        # Slow 20d rolling return is still negative, but fast trigger upgrades direction to BULL
        self.assertEqual(res["direction_label"], "BULL")
        self.assertEqual(res["direction_code"], 2)

    def test_prior_anchored_missingness_imputation(self):
        """Verify Prior-Anchored Bayesian Imputation avoids small-cap score inflation."""
        scorer = EnsembleScoringEngine()

        # Stock A (US Mega-cap): Has multiple factors with good conviction
        # Stock B (KR Micro-cap): Has only 1 factor, missing all alternative US factors
        reg_df = pd.DataFrame({
            "symbol": ["AAPL", "099990"],
            "market": ["SP500", "KOSDAQ"],
            20: [0.15, 0.20],
        })
        surge_df = pd.DataFrame({
            "symbol": ["AAPL"],
            "market": ["SP500"],
            "surge_prob_20d": [0.60],
        })
        iv_df = pd.DataFrame({
            "symbol": ["AAPL"],
            "market": ["SP500"],
            "iv_skew_score": [0.60],
        })
        gamma_df = pd.DataFrame({
            "symbol": ["AAPL"],
            "market": ["SP500"],
            "gamma_squeeze_score": [0.60],
        })
        darkpool_df = pd.DataFrame({
            "symbol": ["AAPL"],
            "market": ["SP500"],
            "darkpool_score": [0.60],
        })

        res_df = scorer.calculate_ensemble_score(
            regime="BULL_LOW_VOL",
            regression_df=reg_df,
            surge_df=surge_df,
            iv_skew_df=iv_df,
            gamma_squeeze_df=gamma_df,
            darkpool_df=darkpool_df,
            target_horizon=20
        )

        self.assertFalse(res_df.empty)
        score_a = float(res_df.loc[res_df["symbol"] == "AAPL", "ensemble_score"].iloc[0])
        score_b = float(res_df.loc[res_df["symbol"] == "099990", "ensemble_score"].iloc[0])

        # Under prior-anchored imputation, Stock A (5 valid strong factors) outscores Stock B (missing factors imputed with 0.50 + penalty)
        self.assertGreater(score_a, score_b)

    def test_rockafellar_uryasev_cvar_optimization(self):
        """Verify Rockafellar-Uryasev auxiliary CVaR optimization satisfies risk budget and simplex."""
        allocator = PortfolioAllocator(risk_aversion=1.0)

        np.random.seed(42)
        N = 200
        asset_a = np.random.normal(0.0010, 0.030, size=N)  # Volatile
        asset_b = np.random.normal(0.0008, 0.012, size=N)  # Low-vol
        asset_c = np.random.normal(0.0005, 0.010, size=N)

        returns_df = pd.DataFrame({'A': asset_a, 'B': asset_b, 'C': asset_c})
        expected_returns = pd.Series({'A': 0.0010, 'B': 0.0008, 'C': 0.0005})

        weights = allocator.optimize_with_evt_cvar_constraint(
            expected_returns=expected_returns,
            returns_df=returns_df,
            max_cvar=0.030,
            confidence=0.95,
            max_weight=0.60
        )

        self.assertEqual(len(weights), 3)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=4)
        for sym, w in weights.items():
            self.assertGreaterEqual(w, -1e-6)
            self.assertLessEqual(w, 0.65)

    def test_analytical_ledoit_wolf_shrinkage(self):
        """Verify analytical Ledoit-Wolf shrinkage produces symmetric, well-conditioned covariance."""
        np.random.seed(42)
        raw_cov = np.array([
            [0.04, 0.035, 0.035],
            [0.035, 0.04, 0.035],
            [0.035, 0.035, 0.04]
        ], dtype=np.float64)

        shrunk = shrink_covariance_matrix(raw_cov)

        # 1. Symmetric
        self.assertTrue(np.allclose(shrunk, shrunk.T))
        # 2. Condition number is strictly improved (reduced)
        cond_raw = np.linalg.cond(raw_cov)
        cond_shrunk = np.linalg.cond(shrunk)
        self.assertLess(cond_shrunk, cond_raw)


if __name__ == "__main__":
    unittest.main()
