import os
import sys
import time
import unittest
import numpy as np
import pandas as pd

# Add paths to sys.path for robust imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


class TestFactorOrthogonalization(unittest.TestCase):

    def setUp(self):
        self.engine = FactorOrthogonalizerEngine(default_method='pca_symmetric')
        self.strategy_cols = [
            'reg_score', 'surge_score', 'll_score', 'vcp_rule_score', 'vcp_ml_score',
            'lstm_score', 'stat_arb_score', 'sector_score', 'rim_score', 'event_score',
            'mq_score', 'iv_skew_score', 'order_flow_score', 'reversal_score',
            'arm_score', 'card_score', 'latr_score'
        ]

    def _make_correlated_score_df(self, n_symbols: int = 500, base_corr: float = 0.75, seed: int = 42) -> pd.DataFrame:
        np.random.seed(seed)
        latent = np.random.normal(0, 1, size=n_symbols)
        data = {'symbol': [f"SYM_{i:04d}" for i in range(n_symbols)]}

        for col in self.strategy_cols:
            noise = np.random.normal(0, 1, size=n_symbols)
            raw = np.sqrt(base_corr) * latent + np.sqrt(1.0 - base_corr) * noise
            data[col] = 1.0 / (1.0 + np.exp(-raw))

        return pd.DataFrame(data)

    def test_gram_schmidt_orthogonality(self):
        """Verify Gram-Schmidt decorrelation produces low pairwise correlation."""
        df = self._make_correlated_score_df(n_symbols=500, base_corr=0.75)
        ortho_df = self.engine.orthogonalize(df, self.strategy_cols, method='gram_schmidt')

        X_ortho = ortho_df[self.strategy_cols].values
        corr_matrix = np.corrcoef(X_ortho, rowvar=False)

        # Off-diagonal elements
        K = len(self.strategy_cols)
        off_diag_mask = ~np.eye(K, dtype=bool)
        mean_off_diag = np.mean(np.abs(corr_matrix[off_diag_mask]))

        # Mean correlation should be reduced below 0.30
        self.assertLess(mean_off_diag, 0.30)

    def test_pca_variance_preservation(self):
        """Verify PCA ZCA decorrelation preserves score bounds and structural variation."""
        df = self._make_correlated_score_df(n_symbols=500, base_corr=0.75)
        ortho_df = self.engine.orthogonalize(df, self.strategy_cols, method='pca_symmetric')

        X_ortho = ortho_df[self.strategy_cols].values
        self.assertTrue(np.all(X_ortho >= 0.0))
        self.assertTrue(np.all(X_ortho <= 1.0))
        self.assertEqual(X_ortho.shape, (500, 17))

    def test_cross_strategy_correlation_reduction(self):
        """Primary M2 R2 SLA Test: Verifies reduced cross-strategy correlation < 0.30."""
        df = self._make_correlated_score_df(n_symbols=500, base_corr=0.80)

        # Compute raw correlation
        X_raw = df[self.strategy_cols].values
        raw_corr = np.corrcoef(X_raw, rowvar=False)
        K = len(self.strategy_cols)
        off_diag_mask = ~np.eye(K, dtype=bool)
        raw_mean_corr = np.mean(np.abs(raw_corr[off_diag_mask]))
        self.assertGreater(raw_mean_corr, 0.65)

        # Apply decorrelation
        ortho_df = self.engine.orthogonalize(df, self.strategy_cols, method='pca_symmetric')
        X_ortho = ortho_df[self.strategy_cols].values
        ortho_corr = np.corrcoef(X_ortho, rowvar=False)
        ortho_mean_corr = np.mean(np.abs(ortho_corr[off_diag_mask]))

        self.assertLess(ortho_mean_corr, 0.30)

    def test_score_range_and_rank_preservation(self):
        """Verify score bounds [0.0, 1.0] and rank preservation (Spearman rho >= 0.70)."""
        df = self._make_correlated_score_df(n_symbols=500, base_corr=0.70)
        ortho_df = self.engine.orthogonalize(df, self.strategy_cols, method='pca_symmetric')

        X_raw = df[self.strategy_cols].values
        X_ortho = ortho_df[self.strategy_cols].values

        self.assertGreaterEqual(float(np.min(X_ortho)), 0.0)
        self.assertLessEqual(float(np.max(X_ortho)), 1.0)

        # Spearman rank correlation between raw sum score and ortho sum score
        raw_sum = np.sum(X_raw, axis=1)
        ortho_sum = np.sum(X_ortho, axis=1)
        rank_corr = pd.Series(raw_sum).corr(pd.Series(ortho_sum), method='spearman')
        self.assertGreaterEqual(rank_corr, 0.70)

    def test_orthogonalization_edge_cases(self):
        """Verify robustness to NaNs, constant columns, duplicate columns, and small N."""
        # 1. NaNs in input
        df_nan = self._make_correlated_score_df(n_symbols=50, base_corr=0.5)
        df_nan.loc[0:5, 'reg_score'] = np.nan
        res_nan = self.engine.orthogonalize(df_nan, self.strategy_cols)
        self.assertTrue(np.isnan(res_nan.loc[0, 'reg_score']))
        self.assertFalse(np.isnan(res_nan.loc[10, 'reg_score']))

        # 2. Constant column
        df_const = self._make_correlated_score_df(n_symbols=50, base_corr=0.5)
        df_const['surge_score'] = 0.5
        res_const = self.engine.orthogonalize(df_const, self.strategy_cols)
        self.assertEqual(len(res_const), 50)

        # 3. Small N = 5
        df_small = self._make_correlated_score_df(n_symbols=5, base_corr=0.5)
        res_small = self.engine.orthogonalize(df_small, self.strategy_cols)
        self.assertEqual(len(res_small), 5)

        # 4. Duplicate columns (rank deficient)
        df_dup = self._make_correlated_score_df(n_symbols=50, base_corr=0.5)
        df_dup['lstm_score'] = df_dup['reg_score'].copy()
        res_dup = self.engine.orthogonalize(df_dup, self.strategy_cols)
        self.assertEqual(len(res_dup), 50)

    def test_benchmark_orthogonalization_latency(self):
        """Benchmark latency of factor decorrelation for 3,379 symbols x 17 strategies (< 50 ms)."""
        df = self._make_correlated_score_df(n_symbols=3379, base_corr=0.75)
        t0 = time.perf_counter()
        res = self.engine.orthogonalize(df, self.strategy_cols, method='pca_symmetric')
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(len(res), 3379)
        self.assertLess(elapsed_ms, 50.0)


if __name__ == '__main__':
    unittest.main()
