"""
tests/test_score_normalizer.py
Comprehensive Unit and Integration Tests for CrossSectionalScoreNormalizer,
Dynamic Weight Re-normalization, and 0.50 Default Purge across all 31 Strategies.
"""

import numpy as np
import pandas as pd
import pytest

from src.ai.score_normalizer import CrossSectionalScoreNormalizer
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.core.accruals_quality import AccrualsQualityEngine
from src.core.valueup_catalyst import ValueUpCatalystEngine
from src.core.short_interest_squeeze import ShortInterestSqueezeEngine
from src.core.trend_efficiency import TrendEfficiencyEngine
from src.core.insider_buying import InsiderBuyingEngine
from src.core.earnings_tone_drift import EarningsToneDriftEngine
from src.core.iv_skew import IVSkewEngine


class TestCrossSectionalScoreNormalizer:
    """Test suite for CrossSectionalScoreNormalizer methods, properties, and edge cases."""

    def test_percentile_rank_basic(self):
        normalizer = CrossSectionalScoreNormalizer(method='percentile_rank')
        df = pd.DataFrame({
            'symbol': ['A', 'B', 'C', 'D', 'E'],
            'score1': [10.0, 20.0, 30.0, 40.0, 50.0],
            'score2': [5.0, np.nan, 15.0, 25.0, np.nan],
        })

        norm_df = normalizer.normalize_scores(df, ['score1', 'score2'])

        # Check bounds in [0.005, 0.995]
        assert (norm_df['score1'] >= 0.005).all() and (norm_df['score1'] <= 0.995).all()
        # Rank ordering preserved
        assert norm_df.loc[0, 'score1'] < norm_df.loc[1, 'score1'] < norm_df.loc[2, 'score1'] < norm_df.loc[3, 'score1'] < norm_df.loc[4, 'score1']
        # Exact ranks: (rank - 0.5) / 5 -> 0.1, 0.3, 0.5, 0.7, 0.9
        np.testing.assert_allclose(norm_df['score1'].values, [0.1, 0.3, 0.5, 0.7, 0.9], atol=1e-4)

        # NaN preservation for score2
        assert pd.isna(norm_df.loc[1, 'score2'])
        assert pd.isna(norm_df.loc[4, 'score2'])
        assert pd.notna(norm_df.loc[0, 'score2'])
        assert pd.notna(norm_df.loc[2, 'score2'])
        assert pd.notna(norm_df.loc[3, 'score2'])
        # Valid values normalized across 3 non-NaN items: 0.5/3, 1.5/3, 2.5/3 -> 0.1667, 0.5, 0.8333
        np.testing.assert_allclose(norm_df.loc[[0, 2, 3], 'score2'].values, [1.0 / 6.0, 3.0 / 6.0, 5.0 / 6.0], atol=1e-4)

    def test_winsorized_zscore_basic(self):
        normalizer = CrossSectionalScoreNormalizer(method='winsorized_zscore')
        np.random.seed(42)
        vals = np.random.normal(loc=100.0, scale=15.0, size=50)
        vals[0] = 1000.0  # extreme outlier
        vals[1] = -500.0  # extreme outlier

        df = pd.DataFrame({'symbol': [f'S{i}' for i in range(50)], 'score': vals})
        norm_df = normalizer.normalize_scores(df, ['score'])

        # Outliers should be winsorized and bounded within [0.005, 0.995]
        assert (norm_df['score'] >= 0.005).all() and (norm_df['score'] <= 0.995).all()
        # Median should be ~ 0.50
        assert 0.45 <= norm_df['score'].median() <= 0.55

    def test_uniform_variance_across_heterogeneous_distributions(self):
        """Verify that percentile rank normalizer equalizes variance across wildly disparate distributions."""
        normalizer = CrossSectionalScoreNormalizer(method='percentile_rank')
        np.random.seed(42)
        N = 100
        df = pd.DataFrame({
            'symbol': [f'S{i}' for i in range(N)],
            'exp_dist': np.random.exponential(scale=2.0, size=N),
            'skewed_prob': np.random.beta(a=0.5, b=5.0, size=N),
            'unbounded_z': np.random.normal(loc=0.0, scale=5.0, size=N),
            'large_returns': np.random.uniform(low=-0.5, high=3.0, size=N),
        })

        norm_df = normalizer.normalize_scores(df, ['exp_dist', 'skewed_prob', 'unbounded_z', 'large_returns'])

        for col in ['exp_dist', 'skewed_prob', 'unbounded_z', 'large_returns']:
            s = norm_df[col].dropna()
            assert abs(s.mean() - 0.50) < 0.02, f"Mean for {col} should be ~0.50, got {s.mean()}"
            # Standard deviation for uniform(0, 1) is 1/sqrt(12) ~ 0.2887
            assert abs(s.std() - (1.0 / np.sqrt(12.0))) < 0.03, f"Std for {col} should be ~0.2887, got {s.std()}"

    def test_market_grouping_and_fallbacks(self):
        normalizer = CrossSectionalScoreNormalizer(method='percentile_rank', min_symbols_per_market=5)
        df = pd.DataFrame({
            'symbol': [f'KR_{i}' for i in range(10)] + [f'US_{i}' for i in range(10)] + ['SMALL_1', 'SMALL_2'],
            'market': ['KOSPI'] * 10 + ['SP500'] * 10 + ['RUSSELL2000', 'RUSSELL2000'],
            'score': list(range(10)) + list(range(100, 110)) + [500, 600],
        })

        norm_df = normalizer.normalize_scores(df, ['score'], market_col='market')

        # KOSPI sub-group should be normalized from 0.05 to 0.95
        kospi_scores = norm_df[norm_df['market'] == 'KOSPI']['score'].values
        np.testing.assert_allclose(kospi_scores, np.linspace(0.05, 0.95, 10), atol=1e-4)

        # SP500 sub-group should also be normalized from 0.05 to 0.95
        sp500_scores = norm_df[norm_df['market'] == 'SP500']['score'].values
        np.testing.assert_allclose(sp500_scores, np.linspace(0.05, 0.95, 10), atol=1e-4)

        # Small market group fallback does not raise and produces valid values
        small_scores = norm_df[norm_df['market'] == 'RUSSELL2000']['score'].values
        assert len(small_scores) == 2
        assert (small_scores >= 0.005).all() and (small_scores <= 0.995).all()

    def test_edge_cases(self):
        normalizer = CrossSectionalScoreNormalizer()

        # 1. Empty dataframe
        empty_df = pd.DataFrame()
        assert normalizer.normalize_scores(empty_df, ['s1']).empty

        # 2. All NaNs
        all_nan_df = pd.DataFrame({'symbol': ['A', 'B'], 'score': [np.nan, np.nan]})
        res_nan = normalizer.normalize_scores(all_nan_df, ['score'])
        assert res_nan['score'].isna().all()

        # 3. Single valid row
        single_df = pd.DataFrame({'symbol': ['A'], 'score': [42.0]})
        res_single = normalizer.normalize_scores(single_df, ['score'])
        assert res_single.loc[0, 'score'] == 0.50

        # 4. Constant values (ties)
        ties_df = pd.DataFrame({'symbol': ['A', 'B', 'C', 'D'], 'score': [10.0, 10.0, 10.0, 10.0]})
        res_ties = normalizer.normalize_scores(ties_df, ['score'])
        assert (res_ties['score'] == 0.50).all()

        # 5. Interface contract alias normalize_cross_section
        res_alias = normalizer.normalize_cross_section(ties_df, ['score'])
        assert (res_alias['score'] == 0.50).all()


class TestStrategyEnginesPurge050:
    """Verify that strategy engines return genuine NaNs for missing data instead of 0.50."""

    def test_accruals_quality_returns_nan_on_missing_fundamentals(self):
        engine = AccrualsQualityEngine()
        df = engine.calculate_scores(['SYM1', 'SYM2'], features_df=None)
        assert len(df) == 2
        assert df['accruals_quality_score'].isna().all(), "Should return NaN when fundamentals are missing"

    def test_valueup_catalyst_returns_nan_on_missing_data(self):
        engine = ValueUpCatalystEngine()
        df = engine.calculate_scores(['SYM1', 'SYM2'], features_df=None)
        assert len(df) == 2
        assert df['valueup_catalyst_score'].isna().all(), "Should return NaN when PBR/financials are missing"

    def test_short_interest_squeeze_returns_nan_on_missing_data(self):
        engine = ShortInterestSqueezeEngine()
        df = engine.calculate_scores(['SYM1', 'SYM2'], prices_dict=None, features_df=None)
        assert len(df) == 2
        assert df['short_squeeze_score'].isna().all(), "Should return NaN when short data & prices are missing"

    def test_trend_efficiency_returns_nan_on_insufficient_prices(self):
        engine = TrendEfficiencyEngine()
        # Short price history < 21 days
        short_prices = {'SYM1': pd.DataFrame({'close': [10.0] * 5})}
        df = engine.calculate_scores(['SYM1'], prices_dict=short_prices)
        assert df['trend_efficiency_score'].isna().all(), "Should return NaN when price history is < 21 bars"

    def test_insider_buying_returns_nan_on_missing_filings(self):
        engine = InsiderBuyingEngine()
        df = engine.compute_insider_buying_scores(['005930', '000660'], insider_filings=None)
        assert df['insider_buying_score'].isna().all(), "Should return NaN for symbols with zero insider filings"

    def test_earnings_tone_drift_returns_nan_on_missing_transcripts(self):
        engine = EarningsToneDriftEngine()
        df = engine.compute_tone_drift_scores(['AAPL', 'MSFT'], transcript_map=None)
        assert df['earnings_tone_drift_score'].isna().all(), "Should return NaN when transcript map is missing"

    def test_iv_skew_returns_nan_on_missing_data(self):
        engine = IVSkewEngine()
        df = engine.compute_iv_skew_scores(['SYM1', 'SYM2'], prices_dict=None)
        assert df['iv_skew_score'].isna().all(), "Should return NaN when price and option data are missing"


class TestDynamicWeightRenormalization:
    """Test dynamic zero-weighting and active weight re-normalization in EnsembleScoringEngine."""

    def test_missing_strategy_zero_weighted_and_renormalized(self):
        engine = EnsembleScoringEngine()

        # Create two stocks:
        # Stock A has high scores on 2 strategies (regression=0.90, surge=0.90) and NO data for the other 29 strategies.
        # Stock B has all 31 strategies populated with moderate scores (0.60).
        reg_df = pd.DataFrame({'symbol': ['STOCK_A', 'STOCK_B'], 'expected_return': [0.90 / 20.0, 0.60 / 20.0], 'market': ['SP500', 'SP500']})
        surge_df = pd.DataFrame({'symbol': ['STOCK_A', 'STOCK_B'], 'surge_prob_20d': [0.90, 0.60], 'market': ['SP500', 'SP500']})
        
        # All other strategies only have data for STOCK_B
        vcp_df = pd.DataFrame({'symbol': ['STOCK_B'], 'vcp_prob_20d': [0.60], 'market': ['SP500']})
        lstm_df = pd.DataFrame({'symbol': ['STOCK_B'], 'lstm_score': [0.60], 'market': ['SP500']})

        result = engine.combine_predictions(
            reg_df=reg_df,
            s_df=surge_df,
            vcp_ml_df=vcp_df,
            lstm_df=lstm_df,
            regime='BULL_LOW_VOL'
        )

        assert 'ensemble_score' in result.columns
        res_a = result[result['symbol'] == 'STOCK_A'].iloc[0]
        res_b = result[result['symbol'] == 'STOCK_B'].iloc[0]

        # STOCK_A has genuine 0.90 scores on its 2 available strategies.
        # It should NOT be dragged down to ~0.50 by missing strategies!
        assert res_a['ensemble_score'] > 0.70, f"Expected STOCK_A ensemble score > 0.70, got {res_a['ensemble_score']}"

    def test_strictly_preserves_nan_in_raw_columns(self):
        engine = EnsembleScoringEngine()
        reg_df = pd.DataFrame({'symbol': ['S1', 'S2'], 'expected_return': [0.05, 0.05], 'market': ['SP500', 'SP500']})
        # Omit all other strategy dataframes
        result = engine.combine_predictions(reg_df=reg_df, regime='BULL_LOW_VOL')

        raw_df = result.attrs.get('raw_scores', engine.raw_scores)
        # Missing strategy columns in raw_scores should either not exist or be NaN, NEVER filled with fake 0.50
        for col in ['mq_score', 'arm_score', 'card_score', 'latr_score']:
            if col in raw_df.columns:
                assert raw_df[col].isna().all(), f"Column {col} should be NaN in raw_scores when omitted from inputs"
