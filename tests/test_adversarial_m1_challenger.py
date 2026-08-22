"""
tests/test_adversarial_m1_challenger.py
Adversarial Empirical Stress Testing for Milestone 1 (R1).
Author: challenger_m1_2 (teamwork_preview_challenger)

Tests:
1. 0 strategies available for a ticker: handles all-NaN gracefully without crashing (N=1, N=5, N=50).
2. 1 out of 31 strategies available: active weight equals 1.0 (100%) exactly across all 31 individual strategies.
3. 30 out of 31 strategies missing: verify no 0.50 default value is injected into the scoring equation.
4. Strategy engines (accruals_quality, valueup_catalyst, short_interest_squeeze, trend_efficiency,
   insider_buying, earnings_tone_drift, iv_skew) return genuine np.nan on missing data instead of 0.50.
5. Boundary conditions: empty DataFrames, None parameters, extreme values, mixed sparsity matrices.
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.ensemble_scorer import EnsembleScoringEngine
from trading_system.src.ai.score_normalizer import CrossSectionalScoreNormalizer

# Strategy engines
from trading_system.src.core.accruals_quality import AccrualsQualityEngine
from trading_system.src.core.valueup_catalyst import ValueUpCatalystEngine
from trading_system.src.core.short_interest_squeeze import ShortInterestSqueezeEngine
from trading_system.src.core.trend_efficiency import TrendEfficiencyEngine
from trading_system.src.core.insider_buying import InsiderBuyingEngine
from trading_system.src.core.earnings_tone_drift import EarningsToneDriftEngine
from trading_system.src.core.iv_skew import IVSkewEngine


ALL_31_STRATEGY_COLS = [
    ('regression', 'reg_score', 'reg_df'),
    ('surge', 'surge_score', 's_df'),
    ('lead_lag', 'll_score', 'll_df'),
    ('vcp_rule', 'vcp_rule_score', 'v_rule_df'),
    ('vcp_ml', 'vcp_ml_score', 'vcp_ml_df'),
    ('lstm', 'lstm_score', 'lstm_df'),
    ('stat_arb', 'stat_arb_score', 'stat_arb_df'),
    ('sector_rotation', 'sector_score', 'sector_df'),
    ('rim_valuation', 'rim_score', 'rim_df'),
    ('event_driven', 'event_score', 'event_df'),
    ('mq_factor', 'mq_score', 'mq_df'),
    ('iv_skew', 'iv_skew_score', 'iv_skew_df'),
    ('order_flow', 'order_flow_score', 'order_flow_df'),
    ('short_term_reversal', 'reversal_score', 'reversal_df'),
    ('arm_factor', 'arm_score', 'arm_df'),
    ('card_factor', 'card_score', 'card_df'),
    ('latr_factor', 'latr_score', 'latr_df'),
    ('inst_foreign_sector', 'inst_foreign_sector_score', 'inst_foreign_sector_df'),
    ('supply_chain', 'supply_chain_score', 'supply_chain_df'),
    ('sentiment', 'sentiment_score', 'sentiment_df'),
    ('factor_neutralized', 'factor_neutralized_score', 'factor_neutralized_df'),
    ('vol_target', 'vol_target_score', 'vol_target_df'),
    ('microstructure', 'microstructure_score', 'microstructure_df'),
    ('accruals_quality', 'accruals_quality_score', 'accruals_quality_df'),
    ('short_squeeze', 'short_squeeze_score', 'short_squeeze_df'),
    ('valueup_catalyst', 'valueup_catalyst_score', 'valueup_catalyst_df'),
    ('trend_efficiency', 'trend_efficiency_score', 'trend_efficiency_df'),
    ('gamma_squeeze', 'gamma_squeeze_score', 'gamma_squeeze_df'),
    ('insider_buying', 'insider_buying_score', 'insider_buying_df'),
    ('darkpool', 'darkpool_score', 'darkpool_df'),
    ('earnings_tone_drift', 'earnings_tone_drift_score', 'earnings_tone_drift_df'),
]


class TestAdversarialZeroAndSingleStrategy:
    """Stress tests 0-strategy and single-strategy handling in EnsembleScoringEngine."""

    @pytest.fixture
    def engine(self):
        eng = EnsembleScoringEngine()
        eng.score_normalizer = CrossSectionalScoreNormalizer(method='percentile_rank')
        return eng

    def test_zero_strategies_all_nan_single_ticker(self, engine):
        """0 strategies available for 1 ticker: must return valid DataFrame, score 0.0, no crash."""
        df_empty = pd.DataFrame({'symbol': ['AAPL']})
        # Pass empty strategy df
        result = engine.combine_predictions(reg_df=df_empty)
        assert not result.empty
        assert 'ensemble_score' in result.columns
        assert float(result.loc[result['symbol'] == 'AAPL', 'ensemble_score'].iloc[0]) == 0.0

    def test_zero_strategies_all_nan_multi_ticker(self, engine):
        """0 strategies available for multiple tickers (N=10): all get score 0.0 without crashing."""
        symbols = [f"SYM_{i:03d}" for i in range(10)]
        df_in = pd.DataFrame({'symbol': symbols})
        result = engine.combine_predictions(reg_df=df_in)
        assert len(result) == 10
        assert (result['ensemble_score'] == 0.0).all()

    def test_single_strategy_active_weight_is_100_percent_for_all_31_strategies(self, engine):
        """Each of the 31 strategies when isolated (1 available, 30 missing) must receive 100% active weight."""
        for strat_name, score_col, arg_name in ALL_31_STRATEGY_COLS:
            test_val = 0.85
            strat_df = pd.DataFrame({'symbol': ['TEST_SYM'], score_col: [test_val]})
            kwargs = {arg_name: strat_df}
            res = engine.combine_predictions(**kwargs)
            assert not res.empty, f"Strategy {strat_name} returned empty result"
            score = float(res['ensemble_score'].iloc[0])
            assert score > 0.0, f"Strategy {strat_name} produced 0.0 score"
            assert not np.isnan(score), f"Strategy {strat_name} produced NaN ensemble score"

            # Check mathematical linear score before coverage penalty by comparing with custom weights
            custom_weights = {strat_name: 0.05}  # Only 5% base weight
            res_w = engine.combine_predictions(weights=custom_weights, **kwargs)
            score_w = float(res_w['ensemble_score'].iloc[0])
            # Weight re-normalization means base weight 0.05 vs default weight should produce identical re-normalized weight (1.0)
            assert abs(score - score_w) < 1e-6, f"Weight re-normalization failed for {strat_name}: {score} != {score_w}"

    def test_no_050_default_injected_when_30_strategies_missing(self, engine):
        """When 30 out of 31 strategies are missing, verify that 0.50 default is NEVER injected.
        If 0.50 were injected for missing strategies:
        Combined score would be ~ (0.90 * w_1 + 30 * 0.50 * w_k) / sum(w) ~= 0.50 + epsilon.
        With dynamic zero-weighting:
        The active score directly reflects the 1 available strategy (0.90), scaled only by explicit coverage penalty.
        """
        # Test with high score 0.90
        strat_df_high = pd.DataFrame({'symbol': ['SYM_HIGH'], 'reg_score': [0.90]})
        res_high = engine.combine_predictions(reg_df=strat_df_high)
        score_high = float(res_high['ensemble_score'].iloc[0])

        # Test with low score 0.10
        strat_df_low = pd.DataFrame({'symbol': ['SYM_LOW'], 'reg_score': [0.10]})
        res_low = engine.combine_predictions(reg_df=strat_df_low)
        score_low = float(res_low['ensemble_score'].iloc[0])

        # Ratio of score_high / score_low should be exactly 0.90 / 0.10 = 9.0
        ratio = score_high / max(score_low, 1e-6)
        assert ratio > 8.0, f"Expected ratio ~9.0 for zero-weighted missing strategies, got {ratio:.4f} (indicates 0.50 leakage!)"
        assert abs(score_high - 0.5129) > 0.10, "Score high is suspiciously close to 0.50-injected value!"


class TestAdversarialStrategyEnginesPurge050:
    """Stress tests individual strategy engines to verify authentic np.nan return on missing data."""

    def test_accruals_quality_missing_data_returns_nan(self):
        engine = AccrualsQualityEngine()
        # Case A: Empty symbols
        assert engine.calculate_scores([]).empty

        # Case B: Symbols with None / empty features
        res1 = engine.calculate_scores(['005930', 'AAPL'], features_df=None)
        assert res1['accruals_quality_score'].isna().all()
        assert not (res1['accruals_quality_score'] == 0.50).any()

        # Case C: Symbols with empty dict
        res2 = engine.calculate_scores(['005930', 'AAPL'], features_df={'005930': {}, 'AAPL': {}})
        assert res2['accruals_quality_score'].isna().all()

        # Case D: Mixed - one symbol has valid OCF/NetIncome, one symbol missing
        valid_fund = {
            '005930': {'net_income': 1000, 'operating_cash_flow': 1500, 'total_assets': 10000},
            '000660': {}  # missing
        }
        res3 = engine.calculate_scores(['005930', '000660'], features_df=valid_fund)
        res3_map = dict(zip(res3['symbol'], res3['accruals_quality_score']))
        assert pd.notna(res3_map['005930'])
        assert pd.isna(res3_map['000660'])
        assert not res3_map['000660'] == 0.50

    def test_valueup_catalyst_missing_data_returns_nan(self):
        engine = ValueUpCatalystEngine()
        # Case A: Empty symbols
        assert engine.calculate_scores([]).empty

        # Case B: Missing features_df
        res1 = engine.calculate_scores(['005930', 'MSFT'], features_df=None)
        assert res1['valueup_catalyst_score'].isna().all()
        assert not (res1['valueup_catalyst_score'] == 0.50).any()

        # Case C: Empty dict
        res2 = engine.calculate_scores(['005930', 'MSFT'], features_df={'005930': {}, 'MSFT': {}})
        assert res2['valueup_catalyst_score'].isna().all()

        # Case D: Mixed - one symbol valid PBR, one symbol missing
        fund = {
            '005930': {'pbr': 0.8, 'cash': 500, 'market_cap': 2000, 'dividend_yield': 3.0, 'roe': 0.12},
            '000660': {}
        }
        res3 = engine.calculate_scores(['005930', '000660'], features_df=fund)
        res3_map = dict(zip(res3['symbol'], res3['valueup_catalyst_score']))
        assert pd.notna(res3_map['005930'])
        assert pd.isna(res3_map['000660'])

    def test_short_interest_squeeze_missing_data_returns_nan(self):
        engine = ShortInterestSqueezeEngine()
        # Case A: Empty symbols
        assert engine.calculate_scores([]).empty

        # Case B: No prices and no short data
        res1 = engine.calculate_scores(['SYM1', 'SYM2'], prices_dict=None, features_df=None)
        assert res1['short_squeeze_score'].isna().all()
        assert not (res1['short_squeeze_score'] == 0.50).any()

        # Case C: Mixed - one symbol has short data, one symbol missing
        fund = {'SYM1': {'short_ratio': 0.25, 'days_to_cover': 5.0}}
        res2 = engine.calculate_scores(['SYM1', 'SYM2'], prices_dict=None, features_df=fund)
        res2_map = dict(zip(res2['symbol'], res2['short_squeeze_score']))
        assert pd.notna(res2_map['SYM1'])
        assert pd.isna(res2_map['SYM2'])

    def test_trend_efficiency_missing_data_returns_nan(self):
        engine = TrendEfficiencyEngine()
        # Case A: Empty symbols
        assert engine.calculate_scores([]).empty

        # Case B: Missing prices_dict
        res1 = engine.calculate_scores(['SYM1', 'SYM2'], prices_dict=None)
        assert res1['trend_efficiency_score'].isna().all()
        assert not (res1['trend_efficiency_score'] == 0.50).any()

        # Case C: Insufficient price history (< 21 bars)
        short_df = pd.DataFrame({'close': [100.0] * 10})
        res2 = engine.calculate_scores(['SYM1'], prices_dict={'SYM1': short_df})
        assert res2['trend_efficiency_score'].isna().all()

        # Case D: Mixed - one with 30 bars, one with 5 bars
        valid_df = pd.DataFrame({'close': np.linspace(100, 150, 30)})
        res3 = engine.calculate_scores(['SYM1', 'SYM2'], prices_dict={'SYM1': valid_df, 'SYM2': short_df})
        res3_map = dict(zip(res3['symbol'], res3['trend_efficiency_score']))
        assert pd.notna(res3_map['SYM1'])
        assert pd.isna(res3_map['SYM2'])

    def test_insider_buying_missing_data_returns_nan(self):
        engine = InsiderBuyingEngine()
        # Case A: Empty symbols
        assert engine.compute_insider_buying_scores([]).empty

        # Case B: No insider filings
        res1 = engine.compute_insider_buying_scores(['005930', 'AAPL'], insider_filings=None)
        assert res1['insider_buying_score'].isna().all()
        assert not (res1['insider_buying_score'] == 0.50).any()

        # Case C: Empty filings list
        res2 = engine.compute_insider_buying_scores(['005930', 'AAPL'], insider_filings=[])
        assert res2['insider_buying_score'].isna().all()

        # Case D: Mixed - one matching filing, one missing
        filings = [{'stock_code': '005930', 'report_nm': '장내매수', 'trans_type': 'BUY', 'insider_role': 'CEO'}]
        res3 = engine.compute_insider_buying_scores(['005930', '000660'], insider_filings=filings)
        res3_map = dict(zip(res3['symbol'], res3['insider_buying_score']))
        assert pd.notna(res3_map['005930'])
        assert pd.isna(res3_map['000660'])

    def test_earnings_tone_drift_missing_data_returns_nan(self):
        engine = EarningsToneDriftEngine()
        # Case A: Empty symbols
        assert engine.compute_tone_drift_scores([]).empty

        # Case B: No transcript map
        res1 = engine.compute_tone_drift_scores(['005930', 'AAPL'], transcript_map=None)
        assert res1['earnings_tone_drift_score'].isna().all()
        assert not (res1['earnings_tone_drift_score'] == 0.50).any()

        # Case C: Empty transcript map
        res2 = engine.compute_tone_drift_scores(['005930', 'AAPL'], transcript_map={})
        assert res2['earnings_tone_drift_score'].isna().all()

        # Case D: Mixed - one with transcript, one missing
        tm = {'005930': {'previous_quarter_tone': 0.40, 'current_quarter_tone': 0.70, 'confidence': 0.90}}
        res3 = engine.compute_tone_drift_scores(['005930', '000660'], transcript_map=tm)
        res3_map = dict(zip(res3['symbol'], res3['earnings_tone_drift_score']))
        assert pd.notna(res3_map['005930'])
        assert pd.isna(res3_map['000660'])

    def test_iv_skew_missing_data_returns_nan(self):
        engine = IVSkewEngine()
        # Case A: Empty symbols
        assert engine.compute_iv_skew_scores([]).empty

        # Case B: No prices and no options data
        res1 = engine.compute_iv_skew_scores(['AAPL', '005930'], prices_dict=None)
        assert res1['iv_skew_score'].isna().all()
        assert not (res1['iv_skew_score'] == 0.50).any()

        # Case C: Insufficient price history (< 20 bars)
        short_df = pd.DataFrame({'Close': [100.0] * 10})
        res2 = engine.compute_iv_skew_scores(['AAPL'], prices_dict={'AAPL': short_df})
        assert res2['iv_skew_score'].isna().all()

        # Case D: Mixed - one with 25 bars, one missing
        valid_df = pd.DataFrame({'Close': np.random.uniform(90, 110, 25)})
        res3 = engine.compute_iv_skew_scores(['AAPL', 'MSFT'], prices_dict={'AAPL': valid_df})
        res3_map = dict(zip(res3['symbol'], res3['iv_skew_score']))
        assert pd.notna(res3_map['AAPL'])
        assert pd.isna(res3_map['MSFT'])


class TestCrossSectionalScoreNormalizerPreservation:
    """Verifies that CrossSectionalScoreNormalizer strictly preserves NaNs and normalizes properly."""

    def test_normalizer_strictly_preserves_nans(self):
        normalizer = CrossSectionalScoreNormalizer(method='percentile_rank')
        df = pd.DataFrame({
            'symbol': ['A', 'B', 'C', 'D', 'E', 'F'],
            'market': ['US', 'US', 'US', 'US', 'US', 'US'],
            'score1': [0.1, np.nan, 0.5, 0.9, np.nan, 0.3],
            'score2': [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
        })
        norm_df = normalizer.normalize_scores(df, strategy_cols=['score1', 'score2'], market_col='market')

        # score1: NaN rows must remain NaN
        assert pd.isna(norm_df.loc[1, 'score1'])
        assert pd.isna(norm_df.loc[4, 'score1'])
        # Valid rows must be normalized in [0.005, 0.995]
        for idx in [0, 2, 3, 5]:
            assert 0.005 <= norm_df.loc[idx, 'score1'] <= 0.995

        # score2: all NaN must remain all NaN
        assert norm_df['score2'].isna().all()
