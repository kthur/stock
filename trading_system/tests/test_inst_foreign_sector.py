"""
Tests for InstForeignSectorEngine
"""

import pytest
import pandas as pd
import numpy as np
from src.core.inst_foreign_sector import InstForeignSectorEngine

def test_inst_foreign_sector_engine_basic():
    engine = InstForeignSectorEngine(accumulation_days=40)
    
    # Generate synthetic price data for 4 symbols
    np.random.seed(42)
    dates = pd.date_range('2026-01-01', periods=60, freq='D')
    
    prices_dict = {}
    for sym in ['005930', '000660', '035420', '035720']:
        ret = np.random.normal(0.001, 0.02, size=60)
        price = 10000 * np.exp(np.cumsum(ret))
        volume = np.random.randint(10000, 50000, size=60)
        df = pd.DataFrame({'Close': price, 'Volume': volume}, index=dates)
        prices_dict[sym] = df

    sector_mapping = {
        '005930': 'Semiconductors',
        '000660': 'Semiconductors',
        '035420': 'Internet',
        '035720': 'Internet',
    }

    res = engine.compute_scores(prices_dict, sector_mapping=sector_mapping)

    assert not res.empty
    assert len(res) == 4
    assert 'symbol' in res.columns
    assert 'inst_foreign_sector_score' in res.columns
    assert 'foreign_acc_score' in res.columns
    assert 'trust_acc_score' in res.columns
    assert 'accumulation_score' in res.columns
    assert 'sector_corr_score' in res.columns

    # Verify separate calculations functionality
    assert np.all(res['foreign_acc_score'] >= 0.0)
    assert np.all(res['trust_acc_score'] >= 0.0)

    # Verify score bounds [0.0, 1.0]
    scores = res['inst_foreign_sector_score'].values
    assert np.all(scores >= 0.0) and np.all(scores <= 1.0)
