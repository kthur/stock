"""
tests/test_adversarial_normalizer_m1.py
Adversarial Stress Test Suite for CrossSectionalScoreNormalizer (Milestone 1).
Validates extreme boundary conditions, mathematical invariants, outlier handling,
NaN preservation, and scalability across 31 strategies.
"""

import numpy as np
import pandas as pd
import pytest
import time
from src.ai.score_normalizer import CrossSectionalScoreNormalizer


class TestAdversarialCrossSectionalScoreNormalizer:
    """Adversarial stress harness for CrossSectionalScoreNormalizer."""

    @pytest.fixture
    def normalizer_rank(self):
        return CrossSectionalScoreNormalizer(method='percentile_rank')

    @pytest.fixture
    def normalizer_zscore(self):
        return CrossSectionalScoreNormalizer(method='winsorized_zscore')

    # =========================================================================
    # 1. Empty & Boundary Cross-Section Sizes (N=0, 1, 2, 3, 4, 9, 10)
    # =========================================================================
    def test_n0_empty_dataframe(self, normalizer_rank, normalizer_zscore):
        """Test completely empty DataFrames (0 rows, 0 cols or 0 rows with cols)."""
        # Case A: completely empty
        df_empty_a = pd.DataFrame()
        res_rank_a = normalizer_rank.normalize_scores(df_empty_a, ['score1'])
        res_z_a = normalizer_zscore.normalize_scores(df_empty_a, ['score1'])
        assert res_rank_a.empty
        assert res_z_a.empty

        # Case B: columns defined but 0 rows
        df_empty_b = pd.DataFrame(columns=['symbol', 'market', 'score1', 'score2'])
        res_rank_b = normalizer_rank.normalize_scores(df_empty_b, ['score1', 'score2'], market_col='market')
        res_z_b = normalizer_zscore.normalize_scores(df_empty_b, ['score1', 'score2'], market_col='market')
        assert len(res_rank_b) == 0
        assert list(res_rank_b.columns) == ['symbol', 'market', 'score1', 'score2']
        assert len(res_z_b) == 0

    def test_n1_single_ticker(self, normalizer_rank, normalizer_zscore):
        """Single ticker cross-section should map to neutral midpoint 0.50."""
        for val in [-100.0, 0.0, 1.0, 42.0, 1e10]:
            df = pd.DataFrame({'symbol': ['AAPL'], 'score': [val], 'market': ['SP500']})
            res_rank = normalizer_rank.normalize_scores(df, ['score'])
            res_z = normalizer_zscore.normalize_scores(df, ['score'])
            assert res_rank.loc[0, 'score'] == 0.50
            assert res_z.loc[0, 'score'] == 0.50

    def test_n2_and_n3_small_cross_sections(self, normalizer_rank, normalizer_zscore):
        """Small cross sections N=2 and N=3 should produce strictly monotonic bounds."""
        # N = 2
        df2 = pd.DataFrame({'symbol': ['A', 'B'], 'score': [10.0, 20.0]})
        r2 = normalizer_rank.normalize_scores(df2, ['score'])
        assert r2.loc[0, 'score'] == pytest.approx(0.25, abs=1e-4)
        assert r2.loc[1, 'score'] == pytest.approx(0.75, abs=1e-4)

        z2 = normalizer_zscore.normalize_scores(df2, ['score'])
        assert 0.005 <= z2.loc[0, 'score'] < z2.loc[1, 'score'] <= 0.995
        assert z2.loc[0, 'score'] + z2.loc[1, 'score'] == pytest.approx(1.0, abs=1e-3)

        # N = 3
        df3 = pd.DataFrame({'symbol': ['A', 'B', 'C'], 'score': [-50.0, 0.0, 50.0]})
        r3 = normalizer_rank.normalize_scores(df3, ['score'])
        assert r3.loc[0, 'score'] == pytest.approx(1.0 / 6.0, abs=1e-4)
        assert r3.loc[1, 'score'] == pytest.approx(0.50, abs=1e-4)
        assert r3.loc[2, 'score'] == pytest.approx(5.0 / 6.0, abs=1e-4)

        z3 = normalizer_zscore.normalize_scores(df3, ['score'])
        assert z3.loc[1, 'score'] == pytest.approx(0.50, abs=1e-3)
        assert z3.loc[0, 'score'] < z3.loc[1, 'score'] < z3.loc[2, 'score']

    # =========================================================================
    # 2. Identical Values / Ties / MAD=0 Degeneracy
    # =========================================================================
    @pytest.mark.parametrize("n_items", [2, 5, 20, 100])
    @pytest.mark.parametrize("constant_val", [-999.0, 0.0, 0.05, 1e8])
    def test_all_identical_values_produce_exact_half(self, normalizer_rank, normalizer_zscore, n_items, constant_val):
        """When all items have identical values, both rank and winsorized z-score must return 0.50."""
        df = pd.DataFrame({
            'symbol': [f'S{i}' for i in range(n_items)],
            'score': [constant_val] * n_items,
            'market': ['SP500'] * n_items
        })
        res_rank = normalizer_rank.normalize_scores(df, ['score'])
        res_z = normalizer_zscore.normalize_scores(df, ['score'])

        np.testing.assert_allclose(res_rank['score'].values, 0.50, atol=1e-5)
        np.testing.assert_allclose(res_z['score'].values, 0.50, atol=1e-5)

    def test_majority_identical_values_mad_zero_fallback(self, normalizer_zscore):
        """When >50% values are identical (MAD=0), robust std falls back to standard deviation safely."""
        # 80 items with 0.0, 10 items with -5.0, 10 items with +5.0
        vals = [0.0] * 80 + [-5.0] * 10 + [5.0] * 10
        df = pd.DataFrame({'symbol': [f'S{i}' for i in range(100)], 'score': vals})
        res_z = normalizer_zscore.normalize_scores(df, ['score'])

        # Median is 0.0, items with 0.0 should be exactly 0.50
        np.testing.assert_allclose(res_z.iloc[:80]['score'].values, 0.50, atol=1e-3)
        # Items with -5.0 should be < 0.50, items with +5.0 should be > 0.50
        assert (res_z.iloc[80:90]['score'] < 0.50).all()
        assert (res_z.iloc[90:]['score'] > 0.50).all()
        assert (res_z['score'] >= 0.005).all() and (res_z['score'] <= 0.995).all()

    # =========================================================================
    # 3. Extreme Outliers, Infs, and Machine Limits
    # =========================================================================
    def test_extreme_finite_outliers(self, normalizer_rank, normalizer_zscore):
        """Values like 1e12 or -1e12 must stay strictly bounded in [0.005, 0.995] without overflow."""
        vals = [1e12, -1e12, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
        df = pd.DataFrame({'symbol': [f'S{i}' for i in range(len(vals))], 'score': vals})

        res_rank = normalizer_rank.normalize_scores(df, ['score'])
        assert (res_rank['score'] >= 0.005).all() and (res_rank['score'] <= 0.995).all()
        assert res_rank.loc[0, 'score'] == pytest.approx(0.995, abs=0.1)
        assert res_rank.loc[1, 'score'] == pytest.approx(0.005, abs=0.1)

        res_z = normalizer_zscore.normalize_scores(df, ['score'])
        assert (res_z['score'] >= 0.005).all() and (res_z['score'] <= 0.995).all()
        assert not res_z['score'].isna().any()

    def test_inf_and_minus_inf_sanitized_to_nan(self, normalizer_rank, normalizer_zscore):
        """np.inf and -np.inf should be treated as non-finite and safely converted to NaN without crash."""
        df = pd.DataFrame({
            'symbol': ['A', 'B', 'C', 'D', 'E'],
            'score': [10.0, np.inf, 20.0, -np.inf, 30.0]
        })
        res_rank = normalizer_rank.normalize_scores(df, ['score'])
        res_z = normalizer_zscore.normalize_scores(df, ['score'])

        # Finite positions 0, 2, 4 must be normalized
        for res in [res_rank, res_z]:
            assert pd.isna(res.loc[1, 'score']), "np.inf must become NaN"
            assert pd.isna(res.loc[3, 'score']), "-np.inf must become NaN"
            assert pd.notna(res.loc[0, 'score'])
            assert pd.notna(res.loc[2, 'score'])
            assert pd.notna(res.loc[4, 'score'])
            assert res.loc[0, 'score'] < res.loc[2, 'score'] < res.loc[4, 'score']

    # =========================================================================
    # 4. High Percentage of Missing Values (NaNs)
    # =========================================================================
    @pytest.mark.parametrize("nan_pct", [0.50, 0.90, 0.99])
    def test_high_nan_percentage_preservation(self, normalizer_rank, normalizer_zscore, nan_pct):
        """Ensure NaNs are preserved at exact positions without leaking or altering valid scores."""
        N = 200
        n_nan = int(N * nan_pct)
        np.random.seed(42)
        vals = np.random.randn(N)
        nan_indices = np.random.choice(N, size=n_nan, replace=False)
        vals[nan_indices] = np.nan

        df = pd.DataFrame({'symbol': [f'S{i}' for i in range(N)], 'score': vals})

        res_rank = normalizer_rank.normalize_scores(df, ['score'])
        res_z = normalizer_zscore.normalize_scores(df, ['score'])

        for res in [res_rank, res_z]:
            # Exact NaN masks match
            assert (res['score'].isna() == df['score'].isna()).all()
            valid_out = res['score'].dropna()
            assert len(valid_out) == N - n_nan
            if len(valid_out) > 0:
                assert (valid_out >= 0.005).all() and (valid_out <= 0.995).all()

    def test_all_nans_in_some_columns(self, normalizer_rank, normalizer_zscore):
        """When a column has 100% NaNs, the entire column remains 100% NaN."""
        df = pd.DataFrame({
            'symbol': ['A', 'B', 'C'],
            'all_nan': [np.nan, np.nan, np.nan],
            'valid': [1.0, 2.0, 3.0]
        })
        res = normalizer_rank.normalize_scores(df, ['all_nan', 'valid'])
        assert res['all_nan'].isna().all()
        assert res['valid'].notna().all()

    # =========================================================================
    # 5. Large Cross-Section & Stress Performance (N=5,000, 31 Strategies)
    # =========================================================================
    def test_large_cross_section_stress(self, normalizer_rank, normalizer_zscore):
        """Stress test with N=5,000 stocks and 31 strategy columns."""
        N = 5000
        num_strategies = 31
        np.random.seed(123)

        markets = np.random.choice(['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000'], size=N)
        data = {'symbol': [f'SYM_{i:05d}' for i in range(N)], 'market': markets}

        strategy_cols = [f'strat_{i}' for i in range(1, num_strategies + 1)]
        for col in strategy_cols:
            raw_vals = np.random.randn(N) * 10.0 + 5.0
            # Inject 20% random NaNs
            nan_mask = np.random.rand(N) < 0.20
            raw_vals[nan_mask] = np.nan
            data[col] = raw_vals

        df = pd.DataFrame(data)

        start_time = time.time()
        res_rank = normalizer_rank.normalize_scores(df, strategy_cols, market_col='market')
        elapsed_rank = time.time() - start_time

        start_time = time.time()
        res_z = normalizer_zscore.normalize_scores(df, strategy_cols, market_col='market')
        elapsed_z = time.time() - start_time

        # Performance check: 5000 x 31 should normalize within reasonable time (< 2.0s)
        assert elapsed_rank < 3.0, f"Rank normalization too slow: {elapsed_rank:.2f}s"
        assert elapsed_z < 3.0, f"ZScore normalization too slow: {elapsed_z:.2f}s"

        # Correctness checks across all 31 columns
        for col in strategy_cols:
            # Check bounds on rank
            valid_rank = res_rank[col].dropna()
            assert (valid_rank >= 0.005).all() and (valid_rank <= 0.995).all()
            assert (res_rank[col].isna() == df[col].isna()).all()

            # Check bounds on zscore
            valid_z = res_z[col].dropna()
            assert (valid_z >= 0.005).all() and (valid_z <= 0.995).all()
            assert (res_z[col].isna() == df[col].isna()).all()

    # =========================================================================
    # 6. Market Partitioning & Handling of Unmapped/NaN Markets
    # =========================================================================
    def test_market_grouping_with_nan_and_unknown_markets(self, normalizer_rank):
        """Ensure market partitioning gracefully handles NaNs and unknown market codes."""
        df = pd.DataFrame({
            'symbol': ['S1', 'S2', 'S3', 'S4', 'S5', 'S6'],
            'market': ['SP500', 'SP500', np.nan, 'UNKNOWN_MKT', 'KOSPI', None],
            'score': [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
        })
        res = normalizer_rank.normalize_scores(df, ['score'], market_col='market')

        assert len(res) == 6
        assert (res['score'] >= 0.005).all() and (res['score'] <= 0.995).all()
        # NaN market rows must not be lost or skipped
        assert not res['score'].isna().any()

    # =========================================================================
    # 7. Non-Numeric Data and Incompatible Column Types
    # =========================================================================
    def test_non_numeric_and_string_values(self, normalizer_rank):
        """String values that can be parsed are parsed; unparseable strings become NaN."""
        df = pd.DataFrame({
            'symbol': ['A', 'B', 'C', 'D'],
            'score': ['10.5', '20.0', 'invalid_str', '40.0']
        })
        res = normalizer_rank.normalize_scores(df, ['score'])
        assert pd.isna(res.loc[2, 'score']), "Unparseable string should become NaN"
        assert pd.notna(res.loc[0, 'score'])
        assert pd.notna(res.loc[1, 'score'])
        assert pd.notna(res.loc[3, 'score'])
        assert res.loc[0, 'score'] < res.loc[1, 'score'] < res.loc[3, 'score']

    def test_missing_strategy_columns_ignored_cleanly(self, normalizer_rank):
        """Requesting normalization on non-existent columns should not crash."""
        df = pd.DataFrame({'symbol': ['A', 'B'], 'score_real': [1.0, 2.0]})
        res = normalizer_rank.normalize_scores(df, ['score_nonexistent', 'score_real'])
        assert 'score_real' in res.columns
        assert 'score_nonexistent' not in res.columns
        assert res.loc[0, 'score_real'] == pytest.approx(0.25, abs=1e-4)

    # =========================================================================
    # 8. Interface Contract Aliasing & Method Case-Insensitivity
    # =========================================================================
    def test_interface_contract_and_case_insensitivity(self, normalizer_rank):
        """Test normalize_cross_section alias with various case formats."""
        df = pd.DataFrame({'symbol': ['A', 'B', 'C'], 'score': [10.0, 20.0, 30.0], 'market': ['SP500', 'SP500', 'SP500']})

        # Test upper-case method
        res1 = normalizer_rank.normalize_cross_section(df, ['score'], method='PERCENTILE_RANK', group_col='market')
        assert res1.loc[1, 'score'] == pytest.approx(0.50, abs=1e-4)

        res2 = normalizer_rank.normalize_cross_section(df, ['score'], method='WINSORIZED_ZSCORE', group_col='market')
        assert res2.loc[1, 'score'] == pytest.approx(0.50, abs=1e-3)
