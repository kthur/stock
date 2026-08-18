"""Unit tests for Strategy #32: Overnight Gap Reversal Engine."""

import pytest
import pandas as pd
import numpy as np
from src.core.overnight_gap_reversal import OvernightGapReversalEngine


def test_overnight_gap_reversal_downward_bounce():
    engine = OvernightGapReversalEngine()

    dates = pd.date_range("2026-01-01", periods=20, freq="B")
    # Base price around 100
    prices = np.linspace(98, 102, 20)
    
    # Create downward gap on the last day: prev close = 100, today open = 95 (-5%), today close = 97 (recovering)
    df = pd.DataFrame({
        'Open': prices,
        'High': prices + 1.0,
        'Low': prices - 1.0,
        'Close': prices,
        'Volume': np.full(20, 1000000)
    }, index=dates)

    df.loc[dates[-2], 'Close'] = 100.0
    df.loc[dates[-1], 'Open'] = 95.0
    df.loc[dates[-1], 'High'] = 98.0
    df.loc[dates[-1], 'Low'] = 94.0
    df.loc[dates[-1], 'Close'] = 97.0

    prices_dict = {'AAPL': df}
    scores_df = engine.calculate_scores(['AAPL'], prices_dict=prices_dict)

    assert not scores_df.empty
    assert 'overnight_gap_score' in scores_df.columns
    score = scores_df.loc[scores_df['symbol'] == 'AAPL', 'overnight_gap_score'].iloc[0]
    # Downward gap with recovery should produce a bullish mean-reversion score (> 0.50)
    assert score > 0.55


def test_overnight_gap_reversal_upward_exhaustion():
    engine = OvernightGapReversalEngine()

    dates = pd.date_range("2026-01-01", periods=20, freq="B")
    prices = np.linspace(98, 102, 20)

    # Create large upward gap with intraday fade: prev close = 100, open = 108 (+8%), close = 104 (fading)
    df = pd.DataFrame({
        'Open': prices,
        'High': prices + 1.0,
        'Low': prices - 1.0,
        'Close': prices,
        'Volume': np.full(20, 1000000)
    }, index=dates)

    df.loc[dates[-2], 'Close'] = 100.0
    df.loc[dates[-1], 'Open'] = 108.0
    df.loc[dates[-1], 'High'] = 109.0
    df.loc[dates[-1], 'Low'] = 103.0
    df.loc[dates[-1], 'Close'] = 104.0

    prices_dict = {'TSLA': df}
    scores_df = engine.calculate_scores(['TSLA'], prices_dict=prices_dict)

    assert not scores_df.empty
    score = scores_df.loc[scores_df['symbol'] == 'TSLA', 'overnight_gap_score'].iloc[0]
    # Upward gap with fade should produce a lower/bearish score (< 0.50)
    assert score < 0.45


def test_overnight_gap_reversal_empty_fallback():
    engine = OvernightGapReversalEngine()
    scores_df = engine.calculate_scores(['EMPTY'], prices_dict={})
    assert not scores_df.empty
    assert scores_df.iloc[0]['overnight_gap_score'] == 0.50
