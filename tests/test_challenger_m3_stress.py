"""
tests/test_challenger_m3_stress.py — Adversarial Stress Test Suite for Milestone 3 (R3 Consolidation)

Tests generate_report.py and gh-pages/index.html against edge cases:
1. Missing result files (empty result dir, partial files, missing ensemble)
2. All-zero portfolios (0% weights, 0 capital, empty rows, missing portfolio file)
3. Missing market indicators (empty/None indicators, extreme values)
4. Empty coverage reports (0-byte file, malformed syntax, missing strategies)
5. Malformed JSON snapshots (corrupted backtest_summary.json, invalid types)
6. DOM element verification for all 3 consolidated cards and 31 strategy tabs.
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
import pytest

from trading_system.generate_report import (
    main as generate_report_main,
    build_html,
    build_strategy_health_monitor_html,
    parse_ensemble,
    parse_portfolio_allocation,
    parse_strategy_coverage_report,
    largest_remainder_round,
    EnsembleData,
    EnsembleMarket,
    EnsembleRow,
    PortfolioAllocationData,
    PortfolioRow,
    StrategyHealthInfo,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Stress Test: Missing result files
# ─────────────────────────────────────────────────────────────────────────────

def test_edge_case_completely_empty_result_dir():
    """generate_report.py must succeed even when result directory is completely empty."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        empty_dir = Path(tmp_dir) / "empty_results"
        empty_dir.mkdir()
        out_html = Path(tmp_dir) / "output.html"

        # Should execute without raising any uncaught exceptions
        generate_report_main(["--result-dir", str(empty_dir), "--out", str(out_html)])

        assert out_html.exists()
        content = out_html.read_text(encoding="utf-8")
        assert len(content) > 10_000
        # Check that core structure and fallback sections are present
        assert "regime-risk-card" in content
        assert "health-monitor-section" in content
        assert "panel-portfolio" in content


def test_edge_case_missing_ensemble_predictions():
    """When ensemble_predictions.txt is missing, fallback defaults should apply."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        res_dir = Path(tmp_dir) / "res"
        res_dir.mkdir()
        # Create only one strategy file, no ensemble
        (res_dir / "surge_predictions.txt").write_text("[SP500] AAPL (Apple): 25.0%\n", encoding="utf-8")
        out_html = Path(tmp_dir) / "out.html"

        generate_report_main(["--result-dir", str(res_dir), "--out", str(out_html)])
        assert out_html.exists()
        content = out_html.read_text(encoding="utf-8")
        assert "2D Market Regime &amp; Risk Gates" in content
        assert "Strategy Data Health Monitor" in content


# ─────────────────────────────────────────────────────────────────────────────
# 2. Stress Test: All-zero and malformed portfolios
# ─────────────────────────────────────────────────────────────────────────────

def test_edge_case_all_zero_portfolio_parsing():
    """All-zero portfolio weights and empty rows must trigger safe fallback without DivisionByZero."""
    zero_portfolio_text = """=== Portfolio Allocation Recommendations ===
Date: 2026-09-01 00:00
Total Capital: 0 KRW/USD
Target Horizon: 20d
Current Market Regime Detected: BEAR_HIGH_VOL (Code: 5)
Maximum Total Allocation Allowed: 0.0%

No. Symbol    Name    Market    Return    Volatility  Weight    Amount
-----------------------------------------------------------------------
-----------------------------------------------------------------------
Allocated Capital: 0.00% (   0)
Remaining Cash   : 100.00% (   0)
"""
    ens = EnsembleData()
    pdata = parse_portfolio_allocation(zero_portfolio_text, ens)
    # When text has no rows, self-healing fallback ensures valid portfolio allocation data
    assert pdata.allocated_capital_pct == "50.00%"
    assert pdata.remaining_cash_pct == "50.00%"
    assert len(pdata.rows) == 10

    # Build HTML with fallback portfolio
    html_out = build_html(
        ensemble=ens,
        surge_date="2026-09-01",
        surge_sections=[],
        vcp_date="2026-09-01",
        vcp_rows=[],
        lag_date="2026-09-01",
        follower_rows=[],
        leader_rows=[],
        portfolio_data=pdata
    )
    assert "panel-portfolio" in html_out
    assert "hrpDonutChart" in html_out



def test_edge_case_zero_weight_allocations_in_rows():
    """Portfolio rows with 0.0% weight must render safely."""
    pdata = PortfolioAllocationData(
        total_capital="100,000,000 KRW",
        allocated_capital_pct="0.0%",
        remaining_cash_pct="100.0%",
        rows=[
            PortfolioRow(
                rank=1,
                symbol="005930",
                name="삼성전자",
                market="KOSPI",
                expected_return="0.0%",
                volatility="0.0%",
                weight="0.0%",
                amount="0"
            )
        ]
    )
    html_out = build_html(
        ensemble=EnsembleData(),
        surge_date="2026-09-01",
        surge_sections=[],
        vcp_date="2026-09-01",
        vcp_rows=[],
        lag_date="2026-09-01",
        follower_rows=[],
        leader_rows=[],
        portfolio_data=pdata
    )
    assert "삼성전자" in html_out
    assert "HOLD" in html_out or "BUY" in html_out


# ─────────────────────────────────────────────────────────────────────────────
# 3. Stress Test: Missing market indicators & extreme values
# ─────────────────────────────────────────────────────────────────────────────

def test_edge_case_missing_and_extreme_indicators():
    """Missing or extreme indicator values must be handled gracefully."""
    ens = EnsembleData(
        date="2026-09-01",
        regime="EXTREME_CRISIS_SHOCK",
        regime_code=99,
        vix="95.5",
        us10y="-0.50%",
        kr10y="15.80%",
        usdkrw="2,500.00",
        sp500_return="-35.2%",
        wti="180.50",
        gold="4,500.00",
        max_allocation="0.0%"
    )
    html_out = build_html(
        ensemble=ens,
        surge_date="2026-09-01",
        surge_sections=[],
        vcp_date="2026-09-01",
        vcp_rows=[],
        lag_date="2026-09-01",
        follower_rows=[],
        leader_rows=[]
    )
    assert "95.5" in html_out
    assert "-0.50%" in html_out
    assert "2,500.00" in html_out
    assert "regime-risk-card" in html_out


# ─────────────────────────────────────────────────────────────────────────────
# 4. Stress Test: Empty or corrupted coverage reports
# ─────────────────────────────────────────────────────────────────────────────

def test_edge_case_empty_and_corrupted_coverage_reports():
    """Empty or garbage coverage report text must fall back to dynamic strategy calculation."""
    # Test 1: Empty string
    tot, items = parse_strategy_coverage_report("", {}, 100)
    assert len(items) == 31
    assert tot == 100

    # Test 2: Garbage text
    garbage = "RANDOM GARBAGE DATA WITH NO STRUCTURE %%% $$$\n\nINVALID LINE"
    tot2, items2 = parse_strategy_coverage_report(garbage, {}, 100)
    assert len(items2) == 31

    # Test 3: Build HTML with empty coverage
    h_html = build_strategy_health_monitor_html(tot, items)
    assert "health-monitor-section" in h_html
    assert "filterHealthCards" in h_html


# ─────────────────────────────────────────────────────────────────────────────
# 5. Stress Test: Malformed JSON snapshots and backtest summary
# ─────────────────────────────────────────────────────────────────────────────

def test_edge_case_malformed_backtest_summary():
    """Corrupted backtest_summary.json must not crash report generation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        res_dir = Path(tmp_dir) / "res"
        res_dir.mkdir()
        out_html = Path(tmp_dir) / "out.html"

        # Case A: Invalid JSON syntax
        (res_dir / "backtest_summary.json").write_text("{ unclosed json: 123", encoding="utf-8")
        generate_report_main(["--result-dir", str(res_dir), "--out", str(out_html)])
        assert out_html.exists()

        # Case B: Valid JSON but unexpected structure (string instead of dict)
        (res_dir / "backtest_summary.json").write_text(json.dumps("UNEXPECTED_STRING"), encoding="utf-8")
        generate_report_main(["--result-dir", str(res_dir), "--out", str(out_html)])
        assert out_html.exists()

        # Case C: Valid JSON with nulls and wrong types
        (res_dir / "backtest_summary.json").write_text(json.dumps({
            "insufficient_data": False,
            "strategies": {
                "regression": {"sharpe_ratio": "NOT_A_NUMBER", "max_drawdown_pct": None}
            }
        }), encoding="utf-8")
        generate_report_main(["--result-dir", str(res_dir), "--out", str(out_html)])
        assert out_html.exists()


# ─────────────────────────────────────────────────────────────────────────────
# 6. DOM Element Verification: gh-pages/index.html & Card 1, 2, 3 + 31 Tabs
# ─────────────────────────────────────────────────────────────────────────────

def test_dom_card_1_market_regime_and_risk_gates():
    """Verify Card 1: 2D Market Regime & Risk Gates Console structure."""
    html_path = Path("gh-pages/index.html")
    assert html_path.exists(), "gh-pages/index.html must exist"
    content = html_path.read_text(encoding="utf-8")

    # Card 1 container
    assert 'class="regime-risk-card"' in content
    assert '2D Market Regime &amp; Risk Gates' in content or '2D Market Regime & Risk Gates' in content

    # Regime badges
    assert 'badge-regime-us' in content
    assert 'badge-regime-kr' in content
    assert '🛡️ Crisis: NONE' in content or 'badge-crisis-none' in content

    # Macro Grid (10 tiles)
    assert 'class="macro-grid"' in content
    assert 'S&amp;P 500 20d Ret' in content or 'S&P 500 20d Ret' in content
    assert 'VIX 공포지수' in content
    assert 'USD/KRW 환율' in content
    assert 'US 10Y 국채금리' in content
    assert 'KR 10Y 국채금리' in content
    assert 'WTI 국제유가' in content
    assert 'GLD ETF' in content
    assert '최대허용배분' in content
    assert '목표 현금비중' in content

    # Risk Defense & Gating Status Bars
    assert 'class="gate-status-strip"' in content
    assert 'VIX Fast Shock Gate' in content
    assert 'Macro Composite Score' in content
    assert 'Intraday Stop-Loss' in content

    # Collapsible 6-Regime Dynamic Matrix & Decision Rationale
    assert '6-Regime Dynamic Matrix' in content
    assert 'AI Strategy Decision Rationale' in content


def test_dom_card_2_strategy_coverage_and_health_center():
    """Verify Card 2: Strategy Coverage & Data Health Diagnostic Center."""
    html_path = Path("gh-pages/index.html")
    content = html_path.read_text(encoding="utf-8")

    # Card 2 container
    assert 'class="health-monitor-section"' in content
    assert 'Strategy Data Health Monitor' in content

    # Summary filter pills
    assert 'filterHealthCards(\'healthy\')' in content
    assert 'filterHealthCards(\'partial\')' in content
    assert 'filterHealthCards(\'fallback\')' in content
    assert 'filterHealthCards(\'nodata\')' in content
    assert 'filterHealthCards(\'all\')' in content

    # 31 health cards
    health_cards = re.findall(r'<div class="health-card"[^>]*onclick="switchTabById\(\'([^\']+)\'\)"', content)
    assert len(health_cards) == 31, f"Expected 31 health cards, got {len(health_cards)}"

    # Missingness diagnostics
    assert 'class="health-reasons-breakdown"' in content
    assert 'INSUFFICIENT_PRICE_HISTORY' in content
    assert 'NO_FUNDAMENTAL_DATA' in content
    assert 'NON_US_MARKET_SCOPE' in content
    assert 'NO_COINTEGRATED_PAIR' in content

    # CPCV Overfitting & Historical Crisis Stress Test
    assert 'class="cpcv-stress-section"' in content
    assert 'PBO: 0.00%' in content
    assert '15 Folds' in content
    assert '2008 금융위기' in content or '2008_CRISIS' in content
    assert '2020 코로나 쇼크' in content or '2020_COVID' in content
    assert '2022 금리 인상' in content or '2022_FED_HIKE' in content


def test_dom_card_3_portfolio_optimization_and_execution_oms():
    """Verify Card 3: Portfolio Optimization & Execution OMS Command Center."""
    html_path = Path("gh-pages/index.html")
    content = html_path.read_text(encoding="utf-8")

    # Panel container
    assert 'id="panel-portfolio"' in content

    # Macro Strip (7 metrics)
    assert '총 자본금' in content
    assert '투자기간' in content
    assert '배분 비중' in content
    assert '현금 잔고' in content
    assert '포트폴리오 예상수익률' in content
    assert '실현 변동성 (Vol)' in content
    assert 'Sharpe Ratio' in content

    # Allocation Charts
    assert 'id="hrpDonutChart"' in content
    assert 'id="marketExposureChart"' in content

    # EVT-GPD Tail Risk Budgeting & Leland Buffer Bands
    assert 'EVT-GPD Tail Risk Budgeting' in content
    assert '95% Parametric VaR / CVaR' in content
    assert '99% Extreme Value GPD CVaR' in content
    assert 'Leland No-Trade Buffer Bands' in content
    assert '&plusmn;2.50% Band' in content or '±2.50% Band' in content

    # Execution OMS & Slippage Feedback Map
    assert 'Execution OMS &amp; Closed-Loop Realized Slippage Map' in content or 'Execution OMS & Closed-Loop Realized Slippage Map' in content
    assert 'OMS 7-Safety Gates' in content
    assert 'trade_logs.db' in content

    # Execution Orders Table
    assert 'HRP Risk Parity Position Allocation &amp; Execution Orders' in content or 'HRP Risk Parity Position Allocation & Execution Orders' in content
    assert 'Leland 실행 상태' in content


def test_dom_row_2_canonical_31_strategy_tabs_and_panels():
    """Verify Row 2 has exactly 31 strategy tabs in canonical order 1~31 and all 31 panels exist."""
    html_path = Path("gh-pages/index.html")
    content = html_path.read_text(encoding="utf-8")

    expected_canonical_tabs = [
        ("regression", "1. Regression"),
        ("surge", "2. Surge"),
        ("leadlag", "3. Lead-Lag"),
        ("vcp", "4. VCP Rule"),
        ("vcpml", "5. VCP ML"),
        ("lstm", "6. Strict LSTM"),
        ("stat-arb", "7. Stat-Arb"),
        ("sector", "8. Sector Rotation"),
        ("rim", "9. RIM Valuation"),
        ("event", "10. Event-Driven"),
        ("mq", "11. MQ Factor"),
        ("iv", "12. Options IV Skew"),
        ("flow", "13. Order Flow"),
        ("reversal", "14. ST Reversal"),
        ("arm", "15. ARM Factor"),
        ("card", "16. CARD Factor"),
        ("latr", "17. LATR Factor"),
        ("ifs", "18. 외인/투신 수급"),
        ("supplychain", "19. Supply Chain"),
        ("sentiment", "20. NLP Sentiment"),
        ("neutralized", "21. Factor Neutralized"),
        ("voltarget", "22. Vol Targeting"),
        ("microstructure", "23. Microstructure"),
        ("accruals", "24. Accruals Quality"),
        ("shortsqueeze", "25. Short Squeeze"),
        ("valueup", "26. Value-Up Yield"),
        ("trendeff", "27. Trend Efficiency"),
        ("gammasqueeze", "28. Gamma Squeeze"),
        ("insider", "29. Insider Buying"),
        ("darkpool", "30. Darkpool"),
        ("tonedrift", "31. Tone Drift"),
    ]

    # Find strategy tab buttons in Row 2
    # Match onclick="switchTab(this,'...')"
    tab_matches = re.findall(r'<button class="tab[^"]*" onclick="switchTab\(this,\'([^\']+)\'\)">([^<]+)</button>', content)

    # Filter to only the strategy tabs (ignore main system tabs if any)
    strategy_tab_ids = [t[0] for t in expected_canonical_tabs]
    found_strategy_tabs = [t for t in tab_matches if t[0] in strategy_tab_ids]

    assert len(found_strategy_tabs) == 31, f"Expected 31 strategy tabs, found {len(found_strategy_tabs)}: {found_strategy_tabs}"

    # Verify exact canonical order 1..31
    for idx, ((actual_id, actual_label), (exp_id, exp_label_prefix)) in enumerate(zip(found_strategy_tabs, expected_canonical_tabs)):
        assert actual_id == exp_id, f"Tab index {idx+1} mismatch: expected {exp_id}, got {actual_id}"
        assert exp_label_prefix in actual_label, f"Tab index {idx+1} label mismatch: expected '{exp_label_prefix}' in '{actual_label}'"

    # Verify all 31 strategy panels exist in DOM
    for exp_id, _ in expected_canonical_tabs:
        panel_id = f'id="panel-{exp_id}"'
        assert panel_id in content, f"Expected panel {panel_id} not found in gh-pages/index.html"
