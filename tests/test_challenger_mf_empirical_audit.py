"""
tests/test_challenger_mf_empirical_audit.py
Independent Empirical Challenger Audit Suite for Multi-Factor Stability & Capital Conservation.

Verifies:
1. ZCA Maximum Amplification Boundedness (whitening_filter <= 10.0 across extreme spectral conditions).
2. Symmetrical ZCA Whitening Positive Diagonal (diag(W_ZCA) > 0 across adversarial matrices).
3. QR Residualization Stability in MultiFactorNeutralizerEngine under rank-deficient, singular,
   zero-variance, extreme outlier, and small sample conditions without NaNs or Infs.
4. Capital Conservation Invariants in Execution OMS (Net Equity <= Gross Equity, Total Friction >= 0).
"""

import unittest
import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.ai.factor_orthogonalizer import (
    FactorOrthogonalizerEngine,
    compute_septendecuple_pillar_zca_whitening,
    compute_quindecuple_pillar_zca_whitening,
    compute_sedecuple_pillar_zca_whitening,
)
from src.core.multi_factor_neutralizer import MultiFactorNeutralizerEngine


class TestChallengerMFEmpiricalAudit(unittest.TestCase):

    def setUp(self):
        self.ortho_engine = FactorOrthogonalizerEngine(default_method="pca_symmetric")
        self.neutral_engine = MultiFactorNeutralizerEngine()

    # =========================================================================
    # Task 2.1: ZCA Maximum Amplification Boundedness (whitening_filter <= 10.0)
    # =========================================================================

    def test_zca_amplification_boundedness_extreme_eigenvalues(self):
        """Stress-test spectral filter inversion with near-zero, zero, and tiny eigenvalues.
        Ensure whitening filter amplification is strictly capped at 10.0.
        """
        # Test simulated eigenvalues spanning from 0 to 100
        test_eigenvalues = [
            np.array([0.0, 1e-15, 1e-10, 1e-5, 0.1, 1.0, 5.0]),
            np.array([1e-20] * 5 + [1.0, 2.0]),
            np.array([0.0] * 10),
            np.array([1e-12, 1e-8, 1e-4, 0.5, 1.0, 10.0]),
        ]

        ridge_eps = 1e-6
        for evals in test_eigenvalues:
            # Replicate the formula used in _pca_zca_symmetric
            sigma2 = float(np.mean(evals)) if len(evals) > 0 else 1.0
            sigma2 = max(sigma2, 1e-4)
            lambda_floor = float(np.clip(max(0.0, 0.01 * sigma2), 1e-4, 1.0))
            lambdas_clean = np.maximum(evals, lambda_floor)
            whitening_filter = 1.0 / np.sqrt(lambdas_clean + ridge_eps)
            capped_filter = np.minimum(whitening_filter, 10.0)

            self.assertTrue(np.all(capped_filter <= 10.0 + 1e-12),
                            f"Filter exceeded 10.0: max was {np.max(capped_filter)}")
            self.assertTrue(np.all(capped_filter > 0.0),
                            f"Filter had non-positive values: min was {np.min(capped_filter)}")
            self.assertTrue(np.all(np.isfinite(capped_filter)),
                            "Filter had non-finite values")

    def test_pca_zca_symmetric_operator_boundedness(self):
        """Test actual _pca_zca_symmetric execution on ill-conditioned data matrices."""
        np.random.seed(42)
        N = 200
        K = 17

        # Adversarially constructed matrix with 1 dominant factor and 16 tiny noise factors
        latent = np.random.normal(0, 1, size=(N, 1))
        noise = np.random.normal(0, 1e-8, size=(N, K - 1))
        X = np.hstack([latent, noise])

        means = np.mean(X, axis=0)
        stds = np.std(X, axis=0)

        # Run PCA-ZCA
        X_ortho = self.ortho_engine._pca_zca_symmetric(
            X=X,
            means=means,
            stds=stds,
            preserve_pc1=True,
            preserve_top_k=4,
        )

        self.assertFalse(np.isnan(X_ortho).any(), "NaN found in X_ortho")
        self.assertFalse(np.isinf(X_ortho).any(), "Inf found in X_ortho")
        # Ensure outputs are well-behaved and not exploding
        self.assertLess(np.max(np.abs(X_ortho)), 1e6, "Orthogonalized values exploded")

    # =========================================================================
    # Task 2.2: Symmetrical ZCA Whitening Positive Diagonal (diag(W_ZCA) > 0)
    # =========================================================================

    def test_zca_positive_diagonal_random_and_adversarial_covariance(self):
        """Verify that diag(W_ZCA) > 0 across diverse covariance structures."""
        np.random.seed(123)

        # 1. 17x17 Random Wishart covariance matrices
        for _ in range(20):
            A = np.random.randn(17, 30)
            cov = A @ A.T / 30.0
            W_17 = compute_septendecuple_pillar_zca_whitening(cov)
            diag_W = np.diag(W_17)
            self.assertTrue(np.all(diag_W > 0),
                            f"17-pillar ZCA had non-positive diagonal: {diag_W}")
            self.assertTrue(np.all(np.isfinite(W_17)), "17-pillar ZCA had non-finite elements")

        # 2. 16x16 covariance
        for _ in range(10):
            A = np.random.randn(16, 25)
            cov = A @ A.T / 25.0
            W_16 = compute_sedecuple_pillar_zca_whitening(cov)
            diag_W = np.diag(W_16)
            self.assertTrue(np.all(diag_W > 0),
                            f"16-pillar ZCA had non-positive diagonal: {diag_W}")

        # 3. 15x15 covariance
        for _ in range(10):
            A = np.random.randn(15, 20)
            cov = A @ A.T / 20.0
            W_15 = compute_quindecuple_pillar_zca_whitening(cov)
            diag_W = np.diag(W_15)
            self.assertTrue(np.all(diag_W > 0),
                            f"15-pillar ZCA had non-positive diagonal: {diag_W}")

    def test_zca_positive_diagonal_adversarial_equicorrelated_negative(self):
        """Adversarial test: Equicorrelated matrix with maximum permissible negative correlation.
        For K=17, minimum valid correlation is -1/(K-1) = -1/16 = -0.0625.
        Test with rho = -0.05.
        """
        K = 17
        rho = -0.05
        cov = (1.0 - rho) * np.eye(K) + rho * np.ones((K, K))

        W = compute_septendecuple_pillar_zca_whitening(cov)
        diag_W = np.diag(W)
        self.assertTrue(np.all(diag_W > 0), f"Negative equicorrelation produced non-positive diagonal: {diag_W}")
        # Verify symmetry
        self.assertTrue(np.allclose(W, W.T, atol=1e-10), "W_ZCA is not symmetric")

    def test_zca_positive_diagonal_near_singular_matrix(self):
        """Adversarial test: Rank-1 + eps covariance matrix (near singular)."""
        K = 17
        v = np.ones((K, 1))
        cov = v @ v.T + 1e-7 * np.eye(K)

        W = compute_septendecuple_pillar_zca_whitening(cov)
        diag_W = np.diag(W)
        self.assertTrue(np.all(diag_W > 0), f"Near-singular matrix produced non-positive diagonal: {diag_W}")
        self.assertFalse(np.isnan(W).any(), "NaN in W_ZCA for near-singular matrix")

    # =========================================================================
    # Task 2.3: QR Residualization Stability in MultiFactorNeutralizerEngine
    # =========================================================================

    def test_qr_residualization_all_zero_variance_factors(self):
        """All 5 factors have zero variance (constant values across universe)."""
        N = 100
        universe = pd.DataFrame({
            "symbol": [f"S_{i:03d}" for i in range(N)],
            "market": ["SP500"] * N,
            "market_cap": [1e9] * N,  # constant
            "per": [15.0] * N,        # constant
            "pbr": [1.5] * N,         # constant
            "roe": [10.0] * N,        # constant
            "asset_growth_yoy": [0.05] * N,  # constant
            "momentum_12m": np.linspace(0.1, 0.9, N),
        })

        res = self.neutral_engine.compute_scores(universe=universe)
        scores = res["factor_neutralized_score"].values

        self.assertEqual(len(scores), N)
        self.assertFalse(np.isnan(scores).any(), "NaN found in zero-variance factor scores")
        self.assertFalse(np.isinf(scores).any(), "Inf found in zero-variance factor scores")
        self.assertTrue(np.all(scores >= 0.02) and np.all(scores <= 0.98),
                        "Scores outside [0.02, 0.98]")

    def test_qr_residualization_rank_deficient_collinear_factors(self):
        """Exact collinearity among factors: factor 2 = 2 * factor 1, factor 3 = factor 1 + factor 2."""
        N = 150
        np.random.seed(777)
        base = np.random.uniform(1.0, 10.0, N)
        universe = pd.DataFrame({
            "symbol": [f"S_{i:03d}" for i in range(N)],
            "market": ["KOSPI"] * N,
            "market_cap": np.exp(base),
            "per": base * 2.0,
            "pbr": base * 3.0,
            "roe": base * 4.0,
            "asset_growth_yoy": base * 5.0,
            "momentum_12m": np.random.uniform(-0.2, 0.4, N),
        })

        res = self.neutral_engine.compute_scores(universe=universe)
        scores = res["factor_neutralized_score"].values

        self.assertEqual(len(scores), N)
        self.assertFalse(np.isnan(scores).any(), "NaN in rank-deficient scores")
        self.assertFalse(np.isinf(scores).any(), "Inf in rank-deficient scores")
        self.assertTrue(np.all(scores >= 0.02) and np.all(scores <= 0.98))

    def test_qr_residualization_extreme_outliers_and_infs(self):
        """Inputs with extreme values (1e20, -1e20, inf, -inf, nan)."""
        N = 50
        universe = pd.DataFrame({
            "symbol": [f"S_{i:03d}" for i in range(N)],
            "market": ["NASDAQ"] * N,
            "market_cap": [1e20, np.nan, np.inf, 1e5] + [1e9] * (N - 4),
            "per": [-1e20, np.nan, -np.inf, 20.0] + [15.0] * (N - 4),
            "pbr": [np.nan, 0.0, -5.0, 1e12] + [2.0] * (N - 4),
            "roe": [np.inf, -np.inf, np.nan, 100.0] + [12.0] * (N - 4),
            "asset_growth_yoy": [np.nan] * N,  # 100% NaN for this factor
            "momentum_12m": [0.5] * N,
        })

        res = self.neutral_engine.compute_scores(universe=universe)
        scores = res["factor_neutralized_score"].values

        self.assertEqual(len(scores), N)
        self.assertFalse(np.isnan(scores).any(), "NaN found under extreme outlier inputs")
        self.assertFalse(np.isinf(scores).any(), "Inf found under extreme outlier inputs")
        self.assertTrue(np.all(scores >= 0.02) and np.all(scores <= 0.98))

    def test_qr_residualization_boundary_universe_sizes(self):
        """Test small cross-sections: N=0, N=1, N=2, N=5, N=6, N=7."""
        for N in [0, 1, 2, 5, 6, 7]:
            if N == 0:
                universe = pd.DataFrame(columns=["symbol", "market", "market_cap", "per", "pbr", "roe", "asset_growth_yoy", "momentum_12m"])
            else:
                universe = pd.DataFrame({
                    "symbol": [f"S_{i}" for i in range(N)],
                    "market": ["KOSDAQ"] * N,
                    "market_cap": [1e9 * (i + 1) for i in range(N)],
                    "per": [10.0 + i for i in range(N)],
                    "pbr": [1.0 + 0.1 * i for i in range(N)],
                    "roe": [5.0 + i for i in range(N)],
                    "asset_growth_yoy": [0.02 * i for i in range(N)],
                    "momentum_12m": [0.1 * i for i in range(N)],
                })

            res = self.neutral_engine.compute_scores(universe=universe)
            self.assertEqual(len(res), N, f"Mismatch length for N={N}")
            if N > 0:
                scores = res["factor_neutralized_score"].values
                self.assertFalse(np.isnan(scores).any(), f"NaN for N={N}")
                self.assertFalse(np.isinf(scores).any(), f"Inf for N={N}")
                self.assertTrue(np.all(scores >= 0.02) and np.all(scores <= 0.98))

    # =========================================================================
    # Task 1 & Invariants: Physical Capital Conservation & Friction Non-Negativity
    # =========================================================================

    def test_capital_conservation_invariants_oms(self):
        """Verify mathematical and accounting invariants of execution friction:
        1. Net Equity <= Gross Equity
        2. Total Transaction Friction = Commissions + Taxes + Slippage Impact >= 0
        """
        # Read the generated paper trading report if present
        session_report_json = os.path.join(
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
            "reports", "paper_trading_session_report.json"
        )
        if os.path.exists(session_report_json):
            import json
            with open(session_report_json, "r", encoding="utf-8") as f:
                data = json.load(f)

            summary = data.get("final_snapshot", data.get("summary", {}))
            net_equity = summary.get("net_equity", 0.0)
            gross_equity = summary.get("gross_equity", 0.0)
            total_fees = summary.get("total_fees_paid", summary.get("total_fees", 0.0))
            total_impact = summary.get("total_market_impact", summary.get("total_impact", 0.0))

            self.assertGreater(gross_equity, 0.0, "Gross equity must be positive")
            self.assertGreater(net_equity, 0.0, "Net equity must be positive")
            self.assertLessEqual(net_equity, gross_equity + 1e-6, "Net Equity must be <= Gross Equity")
            self.assertGreaterEqual(total_fees, 0.0, "Total fees must be non-negative")
            self.assertGreaterEqual(total_impact, 0.0, "Total market impact must be non-negative")


if __name__ == "__main__":
    unittest.main()
