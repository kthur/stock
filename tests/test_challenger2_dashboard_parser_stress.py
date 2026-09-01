"""
Adversarial Stress Test Suite for Dashboard Report Generator & Strategy Parsers (Challenger 2).

Tests:
1. Malformed/empty rim_predictions.txt, lines with N/A, -, negative discounts, extreme numbers, missing columns.
2. Missing strategy_data_coverage_report.txt with dynamic calculation fallback.
3. Empty strategy result files across all 31 strategies.
4. format_metric_cell universal edge cases (None, nan, NaN, undefined, -nan%, 0.0, inf, -inf, etc.).
5. Full HTML generation and verification of zero raw NaN/undefined cells and switchTabById JS linkage.
"""

import re
from pathlib import Path

import pytest

from trading_system.generate_report import (
    _parse_simple_strategy,
    build_strategy_health_monitor_html,
    build_tab_status_banner,
    format_metric_cell,
    parse_arm_factor,
    parse_card_factor,
    parse_darkpool,
    parse_event_driven,
    parse_factor_neutralized,
    parse_inst_foreign_sector,
    parse_iv_skew,
    parse_latr_factor,
    parse_lead_lag,
    parse_microstructure,
    parse_mq_factor,
    parse_order_flow,
    parse_rim,
    parse_sector,
    parse_sentiment,
    parse_short_term_reversal,
    parse_strategy_coverage_report,
    parse_supply_chain,
    parse_surge,
    parse_vcp_ml,
    parse_vcp,
    parse_vol_target,
    parse_accruals_quality,
    parse_short_squeeze,
    parse_valueup_catalyst,
    parse_trend_efficiency,
    parse_gamma_squeeze,
    parse_insider_buying,
    parse_earnings_tone_drift,
    parse_lstm,
    parse_stat_arb,
    parse_regression,
)


# =====================================================================
# 1. parse_rim Adversarial Stress Testing
# =====================================================================

def test_parse_rim_empty_and_whitespace():
    date, rows = parse_rim("")
    assert date == ""
    assert rows == []

    date, rows = parse_rim("   \n\n\t  \n  ")
    assert date == ""
    assert rows == []


def test_parse_rim_headers_only():
    text = """================================================================================
RIM (Residual Income Model) Intrinsic Valuation
Date: 2026-08-28 (KST)
Total symbols evaluated: 948
Filters: BPS>0, ROE>0 (Negative equity / missing fundamentals filtered)
================================================================================
Rank Symbol Name Market Price Intrinsic Discount ROE_raw ROE_adj EQ Filter RIM_Score
--------------------------------------------------------------------------------
"""
    date, rows = parse_rim(text)
    assert date == "2026-08-28 (KST)"
    assert rows == []


def test_parse_rim_na_and_hyphen_lines():
    text = """Date: 2026-08-28 (KST)
Rank Symbol Name Market Price Intrinsic Discount ROE_raw ROE_adj EQ Filter RIM_Score
--------------------------------------------------------------------------------
1 005930 삼성전자 KOSPI 60000 90000 +33.3% 12.5% 10.0% 100.0% - 85.0%
2 000660 SK하이닉스 KOSPI N/A N/A N/A N/A N/A N/A MISSING_FUNDAMENTALS N/A
3 035420 NAVER KOSPI - - - - - - CAPITAL_IMPAIRMENT -
4 051910 LG화학 KOSPI nan nan nan% nan% nan% nan% LOW_EARNINGS_QUALITY nan%
5 035720 카카오 KOSPI NaN NaN NaN% NaN% NaN% NaN% PREFERRED_SHARE NaN%
"""
    date, rows = parse_rim(text)
    assert date == "2026-08-28 (KST)"
    assert len(rows) == 5

    # Row 1: Valid
    assert rows[0].symbol == "005930"
    assert rows[0].score == "85.0%"

    # Row 2: N/A
    assert rows[1].symbol == "000660"
    assert rows[1].price == "N/A"
    assert rows[1].intrinsic_value == "N/A"
    assert rows[1].discount == "N/A"
    assert rows[1].filter_tags == "MISSING_FUNDAMENTALS"
    assert rows[1].score == "N/A"

    # Row 3: -
    assert rows[2].symbol == "035420"
    assert rows[2].price == "-"
    assert rows[2].filter_tags == "CAPITAL_IMPAIRMENT"
    assert rows[2].score == "-"

    # Row 4: nan
    assert rows[3].symbol == "051910"
    assert rows[3].filter_tags == "LOW_EARNINGS_QUALITY"

    # Row 5: NaN
    assert rows[4].symbol == "035720"
    assert rows[4].filter_tags == "PREFERRED_SHARE"


def test_parse_rim_extreme_and_negative_discounts():
    text = """Date: 2026-08-28
1 005930 ExtremeSurge KOSPI 100 1000000 +999900.0% 500.0% 450.0% 100.0% - 100.0%
2 000660 ExtremeOvervalued KOSPI 1000000 100 -99.9% 1.0% 1.0% 10.0% - 0.1%
3 035420 NegativeDiscount KOSPI 50000 25000 -50.0% 5.0% 5.0% 50.0% - 15.0%
4 AAPL Apple_Inc. SP500 220.5 350.8 +59.1% 35.0% 30.0% 100.0% - 92.5%
5 NVDA NVIDIA_Corp NASDAQ 125.0 110.0 -12.0% 80.0% 70.0% 90.0% - 45.0%
"""
    date, rows = parse_rim(text)
    assert date == "2026-08-28"
    assert len(rows) == 5
    assert rows[0].discount == "+999900.0%"
    assert rows[1].discount == "-99.9%"
    assert rows[2].discount == "-50.0%"
    assert rows[3].discount == "+59.1%"
    assert rows[4].discount == "-12.0%"


def test_parse_rim_9col_and_8col_fallback_formats():
    # 9-column format: Rank Symbol Name Market Price Intrinsic Discount EQ RIM_Score
    text9 = """Date: 2026-08-28
1 005930 삼성전자 KOSPI 60000 80000 +25.0% 100.0% 75.0%
2 AAPL Apple SP500 200.0 250.0 +25.0% 95.0% 80.0%
"""
    date9, rows9 = parse_rim(text9)
    assert len(rows9) == 2
    assert rows9[0].symbol == "005930"
    assert rows9[0].eq == "100.0%"
    assert rows9[0].score == "75.0%"

    # 8-column format: Rank Symbol Name Market Price Intrinsic Discount RIM_Score
    text8 = """Date: 2026-08-28
1 005930 삼성전자 KOSPI 60000 80000 +25.0% 75.0%
2 AAPL Apple SP500 200.0 250.0 +25.0% 80.0%
"""
    date8, rows8 = parse_rim(text8)
    assert len(rows8) == 2
    assert rows8[0].symbol == "005930"
    assert rows8[0].score == "75.0%"


def test_parse_rim_malformed_lines_gracefully_skipped():
    text = """Date: 2026-08-28
This is completely invalid line
1 InvalidLineWithoutEnoughColumns
2 005930 삼성전자 KOSPI 60000 90000 +33.3% 12.5% 10.0% 100.0% - 85.0%
3 Random Corrupted Data @#$%^&*
"""
    date, rows = parse_rim(text)
    assert len(rows) == 1
    assert rows[0].symbol == "005930"


# =====================================================================
# 2. Strategy Coverage Report Dynamic Fallback
# =====================================================================

def test_parse_strategy_coverage_report_missing_file_fallback():
    # When cov_text is empty, but parsed_strategies_map has entries
    mock_strategies_map = {
        "regression": [1] * 948,
        "surge": [1] * 800,
        "rim_valuation": [1] * 250,
        "stat_arb": [],  # 0 rows
        "iv_skew": [1] * 300,
    }

    tot, items = parse_strategy_coverage_report(
        cov_text="",
        parsed_strategies_map=mock_strategies_map,
        total_symbols_fallback=948
    )

    assert tot == 948
    assert len(items) in (31, 34)

    # Check regression: 948/948 = 100% -> HEALTHY
    reg = next(it for it in items if it.strategy_id == "regression")
    assert reg.valid_count == 948
    assert reg.coverage_pct == 100.0
    assert reg.status == "HEALTHY"

    # Check rim_valuation: 250/948 = 26.4% -> PARTIAL
    rim = next(it for it in items if it.strategy_id == "rim_valuation")
    assert rim.valid_count == 250
    assert 26.0 <= rim.coverage_pct <= 27.0
    assert rim.status == "PARTIAL"

    # Check stat_arb: 0/948 = 0.0% -> NO_DATA
    sa = next(it for it in items if it.strategy_id == "stat_arb")
    assert sa.valid_count == 0
    assert sa.coverage_pct == 0.0
    assert sa.status == "NO_DATA"


def test_parse_strategy_coverage_report_total_empty_fallback():
    # Both cov_text is empty and parsed_strategies_map is None
    tot, items = parse_strategy_coverage_report(
        cov_text="",
        parsed_strategies_map=None,
        total_symbols_fallback=500
    )
    assert tot == 500
    assert len(items) in (31, 34)
    for it in items:
        assert it.valid_count == 0
        assert it.missing_count == 500
        assert it.coverage_pct == 0.0
        assert it.status == "NO_DATA"

    # Verify build_strategy_health_monitor_html works with 0% data
    html_card = build_strategy_health_monitor_html(tot, items)
    assert '<div class="health-monitor-section">' in html_card
    assert '미비 31' in html_card or '0.0%' in html_card


# =====================================================================
# 3. Universal Cell Sanitizer: format_metric_cell Edge Cases
# =====================================================================

@pytest.mark.parametrize("edge_input", [
    None,
    "nan",
    "NaN",
    "NAN",
    " nan ",
    "undefined",
    "Undefined",
    "null",
    "Null",
    "",
    " ",
    "-",
    "nan%",
    "NaN%",
    float("nan"),
])
def test_format_metric_cell_invalid_inputs_all_kinds(edge_input):
    for kind in ["score", "pct", "currency", "text", "badge", "int"]:
        out = format_metric_cell(edge_input, kind=kind)
        assert isinstance(out, str)
        assert len(out) > 0
        assert '<span class="badge-na">' in out
        assert "undefined" not in out.lower()


@pytest.mark.parametrize("signed_nan", ["-nan%", "+nan%", "-nan", "+nan"])
def test_format_metric_cell_signed_nan_handled_without_crash(signed_nan):
    # Verify signed nan strings do not throw uncaught exceptions
    for kind in ["score", "pct", "currency", "text", "badge", "int"]:
        out = format_metric_cell(signed_nan, kind=kind)
        assert isinstance(out, str)
        assert len(out) > 0


def test_format_metric_cell_zero_and_infinite():
    # Zero should be valid formatted output, not N/A
    out_zero_score = format_metric_cell(0.0, kind="score")
    assert '<span class="">0.0%</span>' in out_zero_score or '0.0%' in out_zero_score

    out_zero_pct = format_metric_cell(0.0, kind="pct")
    assert '0.0%' in out_zero_pct

    out_zero_curr = format_metric_cell(0.0, kind="currency")
    assert '0' in out_zero_curr

    # Infs
    out_pos_inf = format_metric_cell(float("inf"), kind="score")
    assert isinstance(out_pos_inf, str)

    out_neg_inf = format_metric_cell(float("-inf"), kind="pct")
    assert isinstance(out_neg_inf, str)


def test_format_metric_cell_explicit_badges():
    # Needs data badge
    out1 = format_metric_cell("데이터 수집필요 (US 옵션체인)")
    assert '<span class="badge-need-data">' in out1

    # Filtered badge
    out2 = format_metric_cell("MISSING_FUNDAMENTALS")
    assert '<span class="badge-filtered">' in out2

    out3 = format_metric_cell("자본잠식/BPS음수")
    assert '<span class="badge-filtered">' in out3

    # Fallback badge
    out4 = format_metric_cell("섹터중립대체")
    assert '<span class="badge-fallback">' in out4


# =====================================================================
# 4. Strategy Parsers Empty Files Across All 31 Strategies
# =====================================================================

def test_all_31_strategy_parsers_on_empty_input():
    empty_str = ""
    # Test simple strategy parser
    d, rows = _parse_simple_strategy(empty_str, "score")
    assert d == "" and rows == []

    # Test all specific parsers
    assert parse_surge(empty_str) == ("", [])
    assert parse_vcp(empty_str) == ("", [])
    assert parse_vcp_ml(empty_str) == ("", [])
    assert parse_lead_lag(empty_str) == ("", [], [])
    assert parse_sector(empty_str) == ("", [])
    assert parse_rim(empty_str) == ("", [])
    assert parse_event_driven(empty_str) == ("", [])
    assert parse_mq_factor(empty_str) == ("", [])
    assert parse_iv_skew(empty_str) == ("", [])
    assert parse_order_flow(empty_str) == ("", [])
    assert parse_short_term_reversal(empty_str) == ("", [])
    assert parse_arm_factor(empty_str) == ("", [])
    assert parse_card_factor(empty_str) == ("", [])
    assert parse_latr_factor(empty_str) == ("", [])
    assert parse_inst_foreign_sector(empty_str) == ("", [])
    assert parse_supply_chain(empty_str) == ("", [])
    assert parse_sentiment(empty_str) == ("", [])
    assert parse_factor_neutralized(empty_str) == ("", [])
    assert parse_vol_target(empty_str) == ("", [])
    assert parse_microstructure(empty_str) == ("", [])
    assert parse_accruals_quality(empty_str) == ("", [])
    assert parse_short_squeeze(empty_str) == ("", [])
    assert parse_valueup_catalyst(empty_str) == ("", [])
    assert parse_trend_efficiency(empty_str) == ("", [])
    assert parse_gamma_squeeze(empty_str) == ("", [])
    assert parse_insider_buying(empty_str) == ("", [])
    assert parse_darkpool(empty_str) == ("", [])
    assert parse_earnings_tone_drift(empty_str) == ("", [])
    assert parse_lstm(empty_str) == ("", [])
    assert parse_stat_arb(empty_str) == ("", [])
    assert parse_regression(empty_str) == ("", [])


# =====================================================================
# 5. Tab Status Banners & HTML Links Verification
# =====================================================================

def test_tab_status_banners_rendering():
    banner_no_pairs = build_tab_status_banner("Stat-Arb", "KOSPI", status_type="no_pairs")
    assert "통계적 유의 공적분 페어 스캔 완료" in banner_no_pairs
    assert "ADF 단위근 검정" in banner_no_pairs

    banner_us_only = build_tab_status_banner("IV Skew", "KOSPI", status_type="options_us_only")
    assert "옵션 체인 데이터 제공 범위 안내" in banner_us_only
    assert "KOSPI" in banner_us_only

    banner_empty = build_tab_status_banner("Accruals", "SP500", status_type="empty", reason_code="NO_FUNDAMENTAL_DATA")
    assert "데이터 수집 및 산출 준비 중" in banner_empty
    assert "NO_FUNDAMENTAL_DATA" in banner_empty


# =====================================================================
# 6. End-to-End Generated HTML Dashboard Assertions
# =====================================================================

def test_generated_html_report_zero_nan_and_js_integrity():
    out_html_path = Path("gh-pages/index.html")
    if not out_html_path.exists():
        pytest.skip("gh-pages/index.html does not exist yet; run report generation first.")

    content = out_html_path.read_text(encoding="utf-8")

    # 1. Assert NO raw <td[^>]*>(nan|none|undefined|null)</td> strings
    raw_nan_pattern = re.compile(r"<td[^>]*>\s*(nan|none|undefined|null|-nan%|NaN)\s*</td>", re.IGNORECASE)
    matches = raw_nan_pattern.findall(content)
    assert len(matches) == 0, f"Found raw nan/none/undefined td cells: {matches}"

    # 2. Check JavaScript switchTabById definition
    assert "function switchTabById(tabId)" in content
    assert "targetBtn.click()" in content

    # 3. Check that all 31 strategy panels and health monitor cards exist
    assert '<div class="health-monitor-section">' in content
    assert 'id="panel-ensemble"' in content
    assert 'id="panel-portfolio"' in content
    assert 'id="panel-backtest"' in content
    assert 'id="panel-regime"' in content
    assert 'id="panel-scenario"' in content
    assert 'id="panel-history"' in content
    assert 'id="panel-regression"' in content
    assert 'id="panel-surge"' in content
    assert 'id="panel-leadlag"' in content
    assert 'id="panel-vcp"' in content
    assert 'id="panel-vcpml"' in content
    assert 'id="panel-lstm"' in content
    assert 'id="panel-stat-arb"' in content
    assert 'id="panel-sector"' in content
    assert 'id="panel-rim"' in content
    assert 'id="panel-event"' in content
    assert 'id="panel-mq"' in content
    assert 'id="panel-iv"' in content
    assert 'id="panel-flow"' in content
    assert 'id="panel-reversal"' in content
    assert 'id="panel-arm"' in content
    assert 'id="panel-card"' in content
    assert 'id="panel-latr"' in content
    assert 'id="panel-ifs"' in content
    assert 'id="panel-supplychain"' in content
    assert 'id="panel-sentiment"' in content
    assert 'id="panel-neutralized"' in content
    assert 'id="panel-voltarget"' in content
    assert 'id="panel-microstructure"' in content
    assert 'id="panel-accruals"' in content
    assert 'id="panel-shortsqueeze"' in content
    assert 'id="panel-valueup"' in content
    assert 'id="panel-trendeff"' in content
    assert 'id="panel-gammasqueeze"' in content
    assert 'id="panel-insider"' in content
    assert 'id="panel-darkpool"' in content
    assert 'id="panel-tonedrift"' in content
