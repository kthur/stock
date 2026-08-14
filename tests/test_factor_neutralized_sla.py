"""
tests/test_factor_neutralized_sla.py — SLA Test Suite for Strategy 21 (Multi-Factor Neutralizer)

Asserts:
1. Hard Factor Correlation SLA Gate: Pearson |rho| < 0.15 across all 5 Fama-French factors (Size, Value, Profitability, Investment, Momentum).
2. Universe Coverage SLA: >= 95% valid scores across 3,379 symbols under heavy missing data (up to 80% missing fundamentals).
3. Robust Imputation: Market-aware median imputation and momentum fallback.
4. Edge Case Stability: Small universes (N=5, 10), constant features, extreme outliers.
5. Contract Compliance: DataFrame schema, column aliases, descending score ordering.
6. High-Throughput Performance: Execution latency < 50ms for 3,379 symbols.
"""

import os
import sys
import time
import unittest
import numpy as np
import pandas as pd

# Add paths to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trading_system.src.core.multi_factor_neutralizer import MultiFactorNeutralizerEngine


class TestFactorNeutralizedSLA(unittest.TestCase):

    def setUp(self):
        self.engine = MultiFactorNeutralizerEngine()
        self.factor_names = ['market_cap', 'per', 'roe', 'asset_growth_yoy', 'momentum_12m']

    def _generate_synthetic_universe(
        self,
        n_symbols: int = 3379,
        factor_loading: float = 0.80,
        missing_rate: float = 0.0,
        seed: int = 42
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Generates synthetic universe DataFrame and raw_scores DataFrame with known factor exposures.
        """
        np.random.seed(seed)
        symbols = [f"SYM_{i:04d}" for i in range(n_symbols)]
        markets = np.random.choice(['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000'], size=n_symbols)

        # Generate 5 Fama-French style factors
        size_raw = np.exp(np.random.normal(25.0, 1.5, size=n_symbols)) # Market cap
        per_raw = np.random.choice([1.0, -1.0], size=n_symbols, p=[0.85, 0.15]) * np.random.uniform(5.0, 60.0, size=n_symbols)
        ep_yield_raw = np.where(per_raw > 0, 1.0 / per_raw, -1.0 / np.abs(per_raw))
        roe_raw = np.random.normal(12.0, 8.0, size=n_symbols)
        cma_raw = np.random.normal(0.08, 0.15, size=n_symbols)
        mom_raw = np.random.normal(0.10, 0.25, size=n_symbols)

        # Generate heavily factor-correlated raw strategy score
        z_size = (np.log(size_raw) - np.mean(np.log(size_raw))) / np.std(np.log(size_raw))
        z_val = (ep_yield_raw - np.mean(ep_yield_raw)) / np.std(ep_yield_raw)
        z_prof = (roe_raw - np.mean(roe_raw)) / np.std(roe_raw)
        z_cma = (cma_raw - np.mean(cma_raw)) / np.std(cma_raw)
        z_mom = (mom_raw - np.mean(mom_raw)) / np.std(mom_raw)

        factor_composite = (0.4 * z_size + 0.3 * z_val + 0.3 * z_prof + 0.2 * z_cma + 0.5 * z_mom) / np.sqrt(0.4**2 + 0.3**2 + 0.3**2 + 0.2**2 + 0.5**2)
        noise = np.random.normal(0, 1, size=n_symbols)
        raw_latent = factor_loading * factor_composite + np.sqrt(max(0.0, 1.0 - factor_loading**2)) * noise
        raw_scores_val = 1.0 / (1.0 + np.exp(-raw_latent)) # Sigmoid to [0, 1]

        universe_df = pd.DataFrame({
            'symbol': symbols,
            'name': [f"Name_{s}" for s in symbols],
            'market': markets,
            'market_cap': size_raw,
            'per': per_raw,
            'roe': roe_raw,
            'asset_growth_yoy': cma_raw,
            'momentum_12m': mom_raw,
        })

        raw_scores_df = pd.DataFrame({
            'symbol': symbols,
            'score': raw_scores_val,
        })

        # Inject missingness if requested
        if missing_rate > 0.0:
            for col in ['per', 'roe', 'asset_growth_yoy', 'momentum_12m']:
                mask = np.random.uniform(0, 1, size=n_symbols) < missing_rate
                universe_df.loc[mask, col] = np.nan
            # Market cap missingness
            cap_mask = np.random.uniform(0, 1, size=n_symbols) < (missing_rate * 0.5)
            universe_df.loc[cap_mask, 'market_cap'] = np.nan

        return universe_df, raw_scores_df

    # =========================================================================
    # Tier 1: Hard Factor Correlation SLA Gate (|rho| < 0.15)
    # =========================================================================

    def test_unconditional_factor_decorrelation_sla(self):
        """Verify Pearson |rho| < 0.15 unconditionally across all 5 Fama-French factors."""
        universe_df, raw_scores_df = self._generate_synthetic_universe(n_symbols=3379, factor_loading=0.85)

        res_df = self.engine.compute_scores(universe=universe_df, raw_scores=raw_scores_df)
        self.assertFalse(res_df.empty, "Output DataFrame must not be empty.")
        self.assertIn("factor_neutralized_score", res_df.columns)

        # Merge results with factor metrics to compute cross-sectional Pearson correlation
        eval_df = pd.merge(universe_df, res_df[['symbol', 'factor_neutralized_score']], on='symbol')
        eval_df = eval_df.dropna(subset=['factor_neutralized_score'])

        neut_score = eval_df['factor_neutralized_score']

        # 1. Size (log cap)
        log_cap = np.log(eval_df['market_cap'].clip(lower=1e8))
        rho_size = abs(neut_score.corr(log_cap))
        self.assertLess(rho_size, 0.15, f"Size correlation SLA violated: |rho|={rho_size:.4f} >= 0.15")

        # 2. Value (E/P yield)
        ep_yield = np.where(eval_df['per'] > 0, 1.0 / eval_df['per'], -1.0 / np.abs(eval_df['per']))
        rho_val = abs(neut_score.corr(pd.Series(ep_yield, index=eval_df.index)))
        self.assertLess(rho_val, 0.15, f"Value correlation SLA violated: |rho|={rho_val:.4f} >= 0.15")

        # 3. Profitability (ROE)
        rho_prof = abs(neut_score.corr(eval_df['roe']))
        self.assertLess(rho_prof, 0.15, f"Profitability correlation SLA violated: |rho|={rho_prof:.4f} >= 0.15")

        # 4. Investment (Asset Growth)
        rho_cma = abs(neut_score.corr(eval_df['asset_growth_yoy']))
        self.assertLess(rho_cma, 0.15, f"Investment correlation SLA violated: |rho|={rho_cma:.4f} >= 0.15")

        # 5. Momentum (12M Momentum)
        rho_mom = abs(neut_score.corr(eval_df['momentum_12m']))
        self.assertLess(rho_mom, 0.15, f"Momentum correlation SLA violated: |rho|={rho_mom:.4f} >= 0.15")

    def test_maximum_factor_correlation_envelope(self):
        """Stress test with 95% extreme factor collinearity to assert max |rho| < 0.15."""
        universe_df, raw_scores_df = self._generate_synthetic_universe(n_symbols=1000, factor_loading=0.95)
        res_df = self.engine.compute_scores(universe=universe_df, raw_scores=raw_scores_df)

        eval_df = pd.merge(universe_df, res_df[['symbol', 'factor_neutralized_score']], on='symbol').dropna()
        neut_score = eval_df['factor_neutralized_score']

        ep_yield = np.where(eval_df['per'] > 0, 1.0 / eval_df['per'], -1.0 / np.abs(eval_df['per']))
        corrs = [
            abs(neut_score.corr(np.log(eval_df['market_cap'].clip(lower=1e8)))),
            abs(neut_score.corr(pd.Series(ep_yield, index=eval_df.index))),
            abs(neut_score.corr(eval_df['roe'])),
            abs(neut_score.corr(eval_df['asset_growth_yoy'])),
            abs(neut_score.corr(eval_df['momentum_12m'])),
        ]
        max_rho = max(corrs)
        self.assertLess(max_rho, 0.15, f"Envelope SLA violated: max |rho|={max_rho:.4f} >= 0.15")

    # =========================================================================
    # Tier 2: Missing Data & Universe Coverage SLA (>= 95%)
    # =========================================================================

    def test_coverage_under_80pct_missing_fundamentals(self):
        """Assert >= 95% valid scores even when 80% of fundamentals are missing."""
        n_symbols = 3379
        universe_df, raw_scores_df = self._generate_synthetic_universe(
            n_symbols=n_symbols, factor_loading=0.70, missing_rate=0.80
        )

        res_df = self.engine.compute_scores(universe=universe_df, raw_scores=raw_scores_df)
        self.assertFalse(res_df.empty)

        valid_count = res_df['factor_neutralized_score'].notna().sum()
        coverage_pct = (valid_count / n_symbols) * 100.0

        self.assertGreaterEqual(
            coverage_pct, 95.0,
            f"Coverage SLA violated under 80% missingness: {coverage_pct:.2f}% < 95.0%"
        )

    def test_missing_raw_scores_graceful_fallback(self):
        """Verify engine falls back to momentum residualization or returns valid default when raw_scores is None."""
        universe_df, _ = self._generate_synthetic_universe(n_symbols=500, missing_rate=0.10)

        # Pass universe with prices/momentum but raw_scores=None
        res_df = self.engine.compute_scores(universe=universe_df, raw_scores=None)
        self.assertFalse(res_df.empty)
        valid_scores = res_df['factor_neutralized_score'].dropna()
        self.assertGreaterEqual(len(valid_scores) / len(universe_df), 0.95)

    # =========================================================================
    # Tier 3: Small-Universe & Singularity Edge Cases
    # =========================================================================

    def test_small_universe_subsets(self):
        """Verify execution stability when N <= 10 (rank deficiency / small sample)."""
        for n in [5, 10, 20]:
            universe_df, raw_scores_df = self._generate_synthetic_universe(n_symbols=n, seed=n)
            res_df = self.engine.compute_scores(universe=universe_df, raw_scores=raw_scores_df)

            self.assertEqual(len(res_df), n, f"Output length mismatch for N={n}")
            vals = res_df['factor_neutralized_score'].values
            self.assertFalse(np.isnan(vals).any(), f"NaN detected in small universe N={n}")
            self.assertTrue(np.all((vals >= 0.0) & (vals <= 1.0)), f"Bounds violated in small universe N={n}")

    def test_zero_variance_and_constant_factors(self):
        """Verify engine does not crash or emit NaNs when factors have zero variance (constant columns)."""
        universe_df, raw_scores_df = self._generate_synthetic_universe(n_symbols=100)
        universe_df['roe'] = 10.0 # Zero variance
        universe_df['per'] = 15.0 # Zero variance

        res_df = self.engine.compute_scores(universe=universe_df, raw_scores=raw_scores_df)
        vals = res_df['factor_neutralized_score'].values
        self.assertFalse(np.isnan(vals).any(), "NaN produced on zero variance factors.")
        self.assertTrue(np.all((vals >= 0.0) & (vals <= 1.0)))

    def test_extreme_outliers_and_negative_fundamentals(self):
        """Verify stability with extreme outliers (PER=100,000, market cap=1 KRW, negative ROE=-500%)."""
        universe_df, raw_scores_df = self._generate_synthetic_universe(n_symbols=200)
        universe_df.loc[0, 'per'] = 100000.0
        universe_df.loc[1, 'per'] = -50000.0
        universe_df.loc[2, 'market_cap'] = 1.0
        universe_df.loc[3, 'roe'] = -500.0

        res_df = self.engine.compute_scores(universe=universe_df, raw_scores=raw_scores_df)
        vals = res_df['factor_neutralized_score'].values
        self.assertFalse(np.isinf(vals).any(), "Inf produced on extreme outliers.")
        self.assertFalse(np.isnan(vals).any(), "NaN produced on extreme outliers.")

    # =========================================================================
    # Tier 4: Interface Contract & Output Schema Compliance
    # =========================================================================

    def test_positional_and_keyword_argument_binding(self):
        """Verify engine accepts universe both positionally and via kwargs (run_pipeline.py compatibility)."""
        universe_df, raw_scores_df = self._generate_synthetic_universe(n_symbols=100)

        # 1. Positional argument (as invoked in run_pipeline.py:2869)
        res_pos = self.engine.compute_scores(universe_df, raw_scores=raw_scores_df)
        self.assertFalse(res_pos.empty, "Positional call returned empty DataFrame.")
        self.assertIn('factor_neutralized_score', res_pos.columns)

        # 2. Keyword argument
        res_kw = self.engine.compute_scores(universe=universe_df, raw_scores=raw_scores_df)
        self.assertFalse(res_kw.empty, "Keyword call returned empty DataFrame.")

        # Both must produce identical results
        np.testing.assert_allclose(
            res_pos['factor_neutralized_score'].values,
            res_kw['factor_neutralized_score'].values,
            rtol=1e-5
        )

    def test_schema_column_aliases_and_sorting(self):
        """Verify output schema includes neutralized_score alias and is sorted descending."""
        universe_df, raw_scores_df = self._generate_synthetic_universe(n_symbols=100)
        res_df = self.engine.compute_scores(universe_df, raw_scores=raw_scores_df)

        required_cols = ['symbol', 'name', 'market', 'factor_neutralized_score', 'neutralized_score']
        for col in required_cols:
            self.assertIn(col, res_df.columns, f"Missing required column: {col}")

        # Check descending order
        scores = res_df['factor_neutralized_score'].values
        self.assertTrue(np.all(scores[:-1] >= scores[1:]), "Results must be sorted descending by score.")

    # =========================================================================
    # Tier 5: Rank Preservation & Signal Fidelity
    # =========================================================================

    def test_spearman_rank_correlation_preservation(self):
        """Verify idiosyncratic alpha rank is preserved after factor neutralization (Spearman rho >= 0.65)."""
        universe_df, raw_scores_df = self._generate_synthetic_universe(n_symbols=500, factor_loading=0.50)
        res_df = self.engine.compute_scores(universe=universe_df, raw_scores=raw_scores_df)

        merged = pd.merge(raw_scores_df, res_df, on='symbol').dropna()
        rank_corr = merged['score'].corr(merged['factor_neutralized_score'], method='spearman')

        self.assertGreaterEqual(
            rank_corr, 0.65,
            f"Rank correlation preservation violated: {rank_corr:.4f} < 0.65"
        )

    # =========================================================================
    # Tier 6: High-Throughput Latency SLA (< 50ms for 3,379 symbols)
    # =========================================================================

    def test_benchmark_3379_symbols_latency_sla(self):
        """Verify full 3,379 universe execution time is < 50 ms."""
        universe_df, raw_scores_df = self._generate_synthetic_universe(n_symbols=3379, factor_loading=0.75)

        # Warmup
        _ = self.engine.compute_scores(universe_df, raw_scores=raw_scores_df)

        t0 = time.perf_counter()
        res_df = self.engine.compute_scores(universe_df, raw_scores=raw_scores_df)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(len(res_df), 3379)
        self.assertLess(
            elapsed_ms, 50.0,
            f"Latency SLA violated: {elapsed_ms:.2f} ms >= 50.0 ms"
        )


if __name__ == '__main__':
    unittest.main()
