"""
trading_system/tests/test_rim_strategy.py
Unit tests for Strategy #9 RIM (Residual Income Model) Valuation Engine & 9-Strategy Ensemble.
"""
import pandas as pd
import numpy as np
from src.core.rim_valuation import RIMValuationEngine
from src.ai.ensemble_scorer import EnsembleScoringEngine
from generate_report import parse_rim, RimRow, build_html, EnsembleData, EnsembleMarket, EnsembleRow


def test_rim_valuation_calculation():
    engine = RIMValuationEngine(default_required_return=0.08)

    # Sample stock data
    df = pd.DataFrame([
        {'symbol': '005930', 'market': 'KOSPI', 'Close': 70000.0, 'bps': 50000.0, 'roe': 0.15},   # High ROE vs r_e
        {'symbol': '000660', 'market': 'KOSPI', 'Close': 120000.0, 'bps': 80000.0, 'roe': 0.08},  # Neutral ROE = r_e
        {'symbol': '035420', 'market': 'KOSPI', 'Close': 200000.0, 'bps': 50000.0, 'roe': 0.04},  # Low ROE < r_e
    ])

    res = engine.compute_rim_scores(df)

    assert len(res) == 3
    assert 'intrinsic_value' in res.columns
    assert 'discount_ratio' in res.columns
    assert 'rim_score' in res.columns

    # Samsung 005930: BPS=50000, ROE=0.15, r_e=0.08 => V0 = 50000 * (1 + (0.15-0.08)/0.08) = 50000 * 1.875 = 93750
    # Discount = (93750 - 70000) / 70000 = +33.9%
    samsung = res[res['symbol'] == '005930'].iloc[0]
    assert np.isclose(samsung['intrinsic_value'], 93750.0)
    assert samsung['rim_score'] > 0.5  # Highest discount ratio rank in KOSPI


def test_ensemble_scorer_9_strategies():
    scorer = EnsembleScoringEngine()

    reg_df = pd.DataFrame([{'symbol': '005930', 20: 0.10}, {'symbol': 'AAPL', 20: 0.15}])
    surge_df = pd.DataFrame([{'symbol': '005930', 'surge_20d': 0.8}, {'symbol': 'AAPL', 'surge_20d': 0.9}])
    ll_df = pd.DataFrame([{'symbol': '005930', 'lead_lag_score': 0.5}, {'symbol': 'AAPL', 'lead_lag_score': 0.7}])
    vr_df = pd.DataFrame([{'symbol': '005930', 'vcp_score': 80}, {'symbol': 'AAPL', 'vcp_score': 90}])
    vml_df = pd.DataFrame([{'symbol': '005930', 'vcp_20d': 0.6}, {'symbol': 'AAPL', 'vcp_20d': 0.75}])
    lstm_df = pd.DataFrame([{'symbol': '005930', 'lstm_score': 0.7}, {'symbol': 'AAPL', 'lstm_score': 0.85}])
    sa_df = pd.DataFrame([{'symbol': '005930', 'stat_arb_score': 0.65}, {'symbol': 'AAPL', 'stat_arb_score': 0.80}])
    sec_df = pd.DataFrame([{'symbol': '005930', 'sector_score': 0.70}, {'symbol': 'AAPL', 'sector_score': 0.85}])
    rim_df = pd.DataFrame([{'symbol': '005930', 'rim_score': 0.90}, {'symbol': 'AAPL', 'rim_score': 0.95}])

    res = scorer.calculate_ensemble_score(
        regime='BEAR',
        regression_df=reg_df,
        surge_df=surge_df,
        lead_lag_df=ll_df,
        vcp_rule_df=vr_df,
        vcp_ml_df=vml_df,
        lstm_df=lstm_df,
        stat_arb_df=sa_df,
        sector_df=sec_df,
        rim_df=rim_df,
    )

    assert len(res) == 2
    assert 'rim_score' in res.columns
    assert 'ensemble_score' in res.columns
    assert (res['ensemble_score'] >= 0.0).all() and (res['ensemble_score'] <= 1.0).all()


def test_parse_rim_and_build_html():
    raw_txt = """=== Strategy 9: RIM (Residual Income Model) Valuation Predictions ===
Date: 2026-07-26 18:00
Total symbols evaluated: 2

Rank Symbol    Name                Market    Price       Intrinsic V0  Discount %  RIM Score
-----------------------------------------------------------------------------------------------
1    005930    삼성전자            KOSPI     70000.00    93750.00      +33.9%     100.0%
2    AAPL      Apple Inc.          SP500     180.00      240.00        +33.3%     50.0%
"""
    date_str, rows = parse_rim(raw_txt)

    assert date_str == "2026-07-26 18:00"
    assert len(rows) == 2
    assert isinstance(rows[0], RimRow)
    assert rows[0].symbol == "005930"
    assert rows[0].score == "100.0%"

    ensemble = EnsembleData(
        date="2026-07-26",
        regime="SIDEWAYS",
        markets=[
            EnsembleMarket(market="KOSPI", rows=[EnsembleRow(1, "005930", "삼성전자", "85%", "5.2%", "40%", "10%", "20%", "15%", "10%", "15%", "15%", "10%", "15%")]),
        ],
    )

    html = build_html(
        ensemble,
        surge_date="2026-07-26", surge_sections=[],
        vcp_date="2026-07-26", vcp_rows=[],
        lag_date="2026-07-26", follower_rows=[], leader_rows=[],
        vcp_ml_sections=[], reg_sections=[],
        portfolio_data=None,
        stat_arb_rows=[],
        sector_rows=[],
        rim_rows=rows
    )

    assert "💎 RIM Valuation" in html
    assert "#panel-rim" in html
    assert "9 Strategies" in html
