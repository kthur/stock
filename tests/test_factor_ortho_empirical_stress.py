import os
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine

class TestFactorOrthoEmpiricalStress(unittest.TestCase):

    def setUp(self):
        self.pca_engine = FactorOrthogonalizerEngine(default_method='pca_symmetric')
        self.gs_engine = FactorOrthogonalizerEngine(default_method='gram_schmidt')
        self.strategy_cols = [f"strat_{i}" for i in range(17)]

    def _create_df(self, matrix: np.ndarray) -> pd.DataFrame:
        df = pd.DataFrame(matrix, columns=self.strategy_cols[:matrix.shape[1]])
        df['symbol'] = [f"SYM_{i:04d}" for i in range(len(matrix))]
        return df

    def test_perfectly_collinear_columns_pca(self):
        """Test PCA ZCA decorrelation when columns are perfectly collinear."""
        N = 100
        col0 = np.random.uniform(0.1, 0.9, N)
        matrix = np.column_stack([col0 for _ in range(17)]) # All 17 columns identical!
        cols = [f"strat_{i}" for i in range(17)]
        df = pd.DataFrame(matrix, columns=cols)
        
        # Must not crash, output values must remain in [0, 1] and be finite
        res = self.pca_engine.orthogonalize(df, cols, method='pca_symmetric')
        vals = res[cols].values
        self.assertFalse(np.isnan(vals).any())
        self.assertFalse(np.isinf(vals).any())
        self.assertTrue(np.all(vals >= 0.0) and np.all(vals <= 1.0))

    def test_perfectly_collinear_columns_gram_schmidt(self):
        """Test Gram-Schmidt decorrelation when columns are perfectly collinear."""
        N = 100
        col0 = np.random.uniform(0.1, 0.9, N)
        matrix = np.column_stack([col0 for _ in range(17)]) # All 17 columns identical!
        cols = [f"strat_{i}" for i in range(17)]
        df = pd.DataFrame(matrix, columns=cols)
        
        res = self.gs_engine.orthogonalize(df, cols, method='gram_schmidt')
        vals = res[cols].values
        self.assertFalse(np.isnan(vals).any())
        self.assertFalse(np.isinf(vals).any())
        self.assertTrue(np.all(vals >= 0.0) and np.all(vals <= 1.0))

    def test_linear_combination_collinearity(self):
        """Test collinearity where strat_2 = 0.5 * strat_0 + 0.5 * strat_1."""
        N = 100
        c0 = np.random.uniform(0, 1, N)
        c1 = np.random.uniform(0, 1, N)
        c2 = 0.5 * c0 + 0.5 * c1 # Exact linear combination
        matrix = np.column_stack([c0, c1, c2] + [np.random.uniform(0, 1, N) for _ in range(14)])
        cols = [f"strat_{i}" for i in range(17)]
        df = pd.DataFrame(matrix, columns=cols)

        for method in ['pca_symmetric', 'gram_schmidt']:
            res = self.pca_engine.orthogonalize(df, cols, method=method)
            vals = res[cols].values
            self.assertFalse(np.isnan(vals).any(), f"NaN found in {method}")
            self.assertFalse(np.isinf(vals).any(), f"Inf found in {method}")
            self.assertTrue(np.all(vals >= 0.0) and np.all(vals <= 1.0), f"Bounds violated in {method}")

    def test_singular_covariance_matrix_small_n(self):
        """Test singular covariance matrix when N < K (e.g. 5 samples, 17 strategies)."""
        N = 5
        matrix = np.random.uniform(0.1, 0.9, (N, 17))
        cols = [f"strat_{i}" for i in range(17)]
        df = pd.DataFrame(matrix, columns=cols)

        for method in ['pca_symmetric', 'gram_schmidt']:
            res = self.pca_engine.orthogonalize(df, cols, method=method)
            vals = res[cols].values
            self.assertEqual(vals.shape, (5, 17))
            self.assertFalse(np.isnan(vals).any(), f"NaN in {method} for N < K")

    def test_zero_variance_features(self):
        """Test zero-variance features (constant 0.0, constant 1.0, constant 0.5)."""
        N = 100
        matrix = np.random.uniform(0.1, 0.9, (N, 17))
        matrix[:, 0] = 0.0 # zero feature
        matrix[:, 1] = 1.0 # constant max feature
        matrix[:, 2] = 0.5 # constant mid feature
        cols = [f"strat_{i}" for i in range(17)]
        df = pd.DataFrame(matrix, columns=cols)

        for method in ['pca_symmetric', 'gram_schmidt']:
            res = self.pca_engine.orthogonalize(df, cols, method=method)
            vals = res[cols].values
            self.assertFalse(np.isnan(vals).any(), f"NaN in {method} with constant columns")
            self.assertTrue(np.all(vals >= 0.0) and np.all(vals <= 1.0))

    def test_all_zero_variance_matrix(self):
        """Test matrix where ALL features are constant 0.5."""
        N = 50
        matrix = np.full((N, 17), 0.5)
        cols = [f"strat_{i}" for i in range(17)]
        df = pd.DataFrame(matrix, columns=cols)

        for method in ['pca_symmetric', 'gram_schmidt']:
            res = self.pca_engine.orthogonalize(df, cols, method=method)
            vals = res[cols].values
            self.assertFalse(np.isnan(vals).any(), f"NaN in {method} for all constant matrix")
            self.assertTrue(np.all(vals >= 0.0) and np.all(vals <= 1.0))

    def test_random_uniform_scores(self):
        """Test decorrelation on independent uniform random scores U(0,1)."""
        N = 500
        np.random.seed(123)
        matrix = np.random.uniform(0.0, 1.0, (N, 17))
        cols = [f"strat_{i}" for i in range(17)]
        df = pd.DataFrame(matrix, columns=cols)

        # Before decorrelation
        raw_corr = np.corrcoef(matrix, rowvar=False)
        mask = ~np.eye(17, dtype=bool)

        for method in ['pca_symmetric', 'gram_schmidt']:
            res = self.pca_engine.orthogonalize(df, cols, method=method)
            vals = res[cols].values
            corr = np.corrcoef(vals, rowvar=False)
            mean_corr = np.mean(np.abs(corr[mask]))
            self.assertLess(mean_corr, 0.30, f"Decorrelated mean correlation high for {method}")
            self.assertTrue(np.all(vals >= 0.0) and np.all(vals <= 1.0))

    def test_high_correlation_uniform_scores(self):
        """Test highly correlated uniform noise."""
        N = 500
        np.random.seed(999)
        latent = np.random.uniform(0, 1, N)
        matrix = np.column_stack([0.9 * latent + 0.1 * np.random.uniform(0, 1, N) for _ in range(17)])
        cols = [f"strat_{i}" for i in range(17)]
        df = pd.DataFrame(matrix, columns=cols)

        raw_corr = np.corrcoef(matrix, rowvar=False)
        mask = ~np.eye(17, dtype=bool)
        raw_mean = np.mean(np.abs(raw_corr[mask]))
        self.assertGreater(raw_mean, 0.85)

        for method in ['pca_symmetric', 'gram_schmidt']:
            res = self.pca_engine.orthogonalize(df, cols, method=method)
            vals = res[cols].values
            corr = np.corrcoef(vals, rowvar=False)
            mean_corr = np.mean(np.abs(corr[mask]))
            self.assertLess(mean_corr, 0.30, f"Failed to suppress correlation below 0.30 in {method}")

    def test_single_row_and_single_col(self):
        """Test edge cases with N=1 or K=1."""
        df_1row = pd.DataFrame(np.random.uniform(0, 1, (1, 17)), columns=[f"strat_{i}" for i in range(17)])
        res_1row = self.pca_engine.orthogonalize(df_1row, [f"strat_{i}" for i in range(17)])
        self.assertEqual(len(res_1row), 1)

        df_1col = pd.DataFrame({'strat_0': np.random.uniform(0, 1, 50)})
        res_1col = self.pca_engine.orthogonalize(df_1col, ['strat_0'])
        self.assertEqual(len(res_1col), 50)

if __name__ == '__main__':
    unittest.main()
