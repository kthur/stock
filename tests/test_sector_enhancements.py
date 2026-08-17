import sqlite3
import numpy as np
import pandas as pd

from src.data_layer.indicator_storage import MarketIndicatorStorage
from src.core.sector_rotation import SectorRotationEngine
from src.core.stat_arb import StatisticalArbitrageEngine


def test_indicator_storage_sector_schema_and_map(tmp_path):
    db_file = str(tmp_path / "test_indicators.db")
    storage = MarketIndicatorStorage(db_path=db_file)

    # Verify migration / schema
    with sqlite3.connect(db_file) as conn:
        cursor = conn.execute("PRAGMA table_info(stock_universe)")
        cols = [row[1] for row in cursor.fetchall()]
        assert 'sector' in cols
        assert 'industry' in cols

    # Insert sample universe with sectors
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO stock_universe (symbol, name, market, sector, industry) VALUES (?, ?, ?, ?, ?)",
            ("005930", "삼성전자", "KOSPI", "전기전자", "반도체")
        )
        conn.execute(
            "INSERT OR REPLACE INTO stock_universe (symbol, name, market, sector, industry) VALUES (?, ?, ?, ?, ?)",
            ("005380", "현대차", "KOSPI", "운수장비", "자동차")
        )
        conn.commit()

    sec_map = storage.get_sector_map()
    assert sec_map.get("005930") == "전기전자"
    assert sec_map.get("005380") == "운수장비"


def test_gics_sector_normalization_and_scoring():
    engine = SectorRotationEngine()

    assert engine.normalize_sector("전기전자") == "Information Technology"
    assert engine.normalize_sector("의약품") == "Health Care"
    assert engine.normalize_sector("금융업") == "Financials"
    assert engine.normalize_sector("Unknown_Sector") == "General"

    dates = pd.date_range("2024-01-01", periods=30, freq="B")
    prices_dict = {
        '005930': pd.DataFrame({'Close': np.linspace(50000, 60000, 30)}, index=dates),
        '000660': pd.DataFrame({'Close': np.linspace(100000, 130000, 30)}, index=dates),
        '005380': pd.DataFrame({'Close': np.linspace(150000, 160000, 30)}, index=dates),
        '000100': pd.DataFrame({'Close': np.linspace(40000, 38000, 30)}, index=dates),
    }
    sector_map = {
        '005930': '전기전자',
        '000660': '전기전자',
        '005380': '운수장비',
        '000100': '의약품',
    }

    # Test scoring with sector map & regime cycle boost
    df_scores = engine.compute_sector_momentum_scores(
        prices_dict,
        sector_map=sector_map,
        regime_label="BULL_EXPANSION"
    )

    assert not df_scores.empty
    assert 'sector_score' in df_scores.columns
    # Outperforming IT sector stocks should have higher score
    semi_score = float(df_scores[df_scores['symbol'] == '000660']['sector_score'].iloc[0])
    pharma_score = float(df_scores[df_scores['symbol'] == '000100']['sector_score'].iloc[0])
    assert semi_score > pharma_score


def test_stat_arb_sector_constraint():
    sa_engine = StatisticalArbitrageEngine()

    np.random.seed(42)
    t = np.linspace(0, 10, 100)
    base_signal = np.sin(t)

    prices_dict = {
        '005930': (100 + base_signal + np.random.normal(0, 0.05, 100)).tolist(),
        '000660': (150 + 1.5 * base_signal + np.random.normal(0, 0.05, 100)).tolist(),
        '005380': (200 + 0.1 * np.cos(t) + np.random.normal(0, 0.05, 100)).tolist(),
    }
    sector_map = {
        '005930': 'Information Technology',
        '000660': 'Information Technology',
        '005380': 'Consumer Discretionary',
    }

    # Test with require_same_sector=True -> Only 005930 & 000660 candidate
    pairs_same = sa_engine.find_cointegrated_pairs(
        prices_dict,
        min_correlation=0.50,
        sector_map=sector_map,
        require_same_sector=True
    )

    for p in pairs_same:
        pair_syms = set(p['pair'])
        assert not ('005380' in pair_syms and '005930' in pair_syms)
