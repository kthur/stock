"""
tests/test_kst_and_coverage_reasoning.py
Unit tests for:
1. KST timezone (Asia/Seoul) formatting
2. Regime & Strategy decision rationale generation in EnsembleScoringEngine
3. StrategyCoverageAnalyzer coverage & missingness analysis
4. HTML Dashboard (generate_report.py) 14-strategy integration
"""
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.analysis.coverage_analyzer import StrategyCoverageAnalyzer
from generate_report import EnsembleData, EnsembleMarket, EnsembleRow, build_html


def test_kst_timezone_format():
    KST = timezone(timedelta(hours=9))
    now_kst = datetime.now(KST)
    formatted = now_kst.strftime('%Y-%m-%d %H:%M KST')
    assert "KST" in formatted
    assert formatted.startswith("202")  # 202x year


def test_regime_reasoning_summary():
    scorer = EnsembleScoringEngine()
    rolling_sharpes = {'regression': 1.2, 'surge': 0.5, 'stat_arb': 1.8}
    summary = scorer.get_regime_reasoning_summary('BULL_LOW_VOL', rolling_sharpes=rolling_sharpes)

    assert "[2D Market Regime & Strategy Decision Rationale]" in summary
    assert "BULL_LOW_VOL" in summary
    assert "BULL" in summary
    assert "LOW_VOL" in summary
    assert "regression" in summary
    assert "stat_arb" in summary


def test_strategy_coverage_analyzer():
    analyzer = StrategyCoverageAnalyzer()

    # Build mock ensemble_df with 14 strategy score columns
    df = pd.DataFrame({
        'symbol': ['005930.KS', '000660.KS', 'AAPL', 'MSFT'],
        'reg_score': [0.8, 0.6, 0.9, np.nan],
        'surge_score': [0.7, 0.4, 0.8, 0.2],
        'll_score': [0.5, 0.5, 0.6, 0.4],
        'vcp_rule_score': [0.0, 0.0, 1.0, 0.0],
        'vcp_ml_score': [0.6, 0.3, 0.7, 0.1],
        'lstm_score': [0.5, 0.5, 0.5, 0.5],
        'stat_arb_score': [0.0, 1.0, 0.0, 0.0],
        'sector_score': [0.8, 0.7, 0.6, 0.5],
        'rim_score': [0.9, np.nan, 0.8, np.nan],
        'event_score': [0.5, 0.5, 0.8, 0.5],
        'mq_score': [0.7, 0.6, 0.8, 0.5],
        'iv_skew_score': [0.5, 0.5, 0.7, 0.6],
        'order_flow_score': [0.6, 0.5, 0.7, 0.4],
        'reversal_score': [0.4, 0.3, 0.6, 0.2],
        'ensemble_score': [0.75, 0.55, 0.82, 0.40],
        'ensemble_expected_return': [15.0, 10.0, 18.0, 5.0],
    })

    result = analyzer.analyze_coverage(df)
    assert result['total_symbols'] == 4
    assert 'strategies' in result
    assert 'rim_valuation' in result['strategies']
    assert result['strategies']['rim_valuation']['valid_count'] == 2

    report_text = analyzer.generate_coverage_report(result, date_str="2026-07-26 22:50 KST")
    assert "=== 18-Strategy Data Coverage & Missingness Report ===" in report_text
    assert "rim_valuation" in report_text


def test_generate_report_14_strategies():
    ens = EnsembleData(
        date="2026-07-26 22:50 KST",
        regime="BULL_LOW_VOL",
        decision_rationale="• Selected 2D Regime State: BULL_LOW_VOL\n  - Market Trend Rationale: Upward momentum trend confirmed.",
        weights={"XGBoost Regression": "15.0%", "Surge Classifier": "20.0%"}
    )
    mkt = EnsembleMarket(market="SP500")
    mkt.rows.append(EnsembleRow(
        rank=1, symbol="AAPL", name="Apple Inc",
        score="85.0%", expected_return="18.50%",
        reg="80%", surge="90%", lead_lag="70%", vcp_rule="60%", vcp_ml="85%",
        lstm="75%", stat_arb="50%", sector_rotation="80%", rim_valuation="70%",
        event_driven="85%", mq_factor="80%", iv_skew="75%", order_flow="70%", short_term_reversal="65%"
    ))
    ens.markets.append(mkt)

    html = build_html(
        ensemble=ens,
        surge_date="", surge_sections=[],
        vcp_date="", vcp_rows=[],
        lag_date="", follower_rows=[], leader_rows=[]
    )

    assert ("2D Regime &amp; Strategy Rationale" in html) or ("2D Regime & Strategy Rationale" in html) or ("2D Regime &amp; Strategy Decision Rationale" in html) or ("2D Regime & Strategy Decision Rationale" in html)
    assert "AAPL" in html
    assert "KST" in html
