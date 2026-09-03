import re
from trading_system.generate_report import (
    largest_remainder_round,
    build_html,
    EnsembleData,
    EnsembleRow,
    EnsembleMarket
)


def _call_build_html(ensemble=None, all_stocks_universe_json="[]"):
    if ensemble is None:
        ensemble = EnsembleData()
    return build_html(
        ensemble=ensemble,
        surge_date="2026-08-22",
        surge_sections=[],
        vcp_date="2026-08-22",
        vcp_rows=[],
        lag_date="2026-08-22",
        follower_rows=[],
        leader_rows=[],
        all_stocks_universe_json=all_stocks_universe_json
    )


def test_largest_remainder_round_basic():
    # 3 equal weights
    weights = [33.333, 33.333, 33.334]
    rounded = largest_remainder_round(weights, target_sum=100.0, decimals=1)
    assert round(sum(rounded), 1) == 100.0
    assert len(rounded) == 3


def test_largest_remainder_round_31_strategies_rounding_error_fix():
    # Simulated 31 strategy weights that would previously sum to 100.7% under simple round(x, 1)
    raw_weights = [
        3.25, 3.25, 3.25, 3.25, 3.25, 3.25, 3.25, 3.25, 3.25, 3.25,
        3.25, 3.25, 3.25, 3.25, 3.25, 3.25, 3.25, 3.25, 3.25, 3.25,
        3.25, 3.25, 3.25, 3.25, 3.25, 3.25, 3.25, 3.25, 3.25, 3.25,
        2.50
    ]
    # Simple rounding: 30 * 3.3 = 99.0 + 2.5 = 101.5%
    simple_rounded_sum = sum(round(w, 1) for w in raw_weights)
    assert simple_rounded_sum != 100.0

    # With largest remainder method:
    lrm_rounded = largest_remainder_round(raw_weights, target_sum=100.0, decimals=1)
    assert round(sum(lrm_rounded), 1) == 100.0
    assert len(lrm_rounded) == 31
    for val in lrm_rounded:
        # Check that each value is within reasonable range and has 1 decimal
        assert isinstance(val, float)
        assert round(val, 1) == val


def test_largest_remainder_round_edge_cases():
    # Empty list
    assert largest_remainder_round([]) == []

    # All zeros
    zeros = [0.0, 0.0, 0.0]
    rounded_zeros = largest_remainder_round(zeros, target_sum=100.0, decimals=1)
    assert round(sum(rounded_zeros), 1) == 100.0

    # Single element
    assert largest_remainder_round([42.0], target_sum=100.0, decimals=1) == [100.0]


def test_render_weights_html_sums_to_100():
    # Test HTML generation with 31 mock strategies
    ensemble = EnsembleData()
    weights_dict = {
        f"Strategy {i+1}": f"{3.25:.2f}%" for i in range(30)
    }
    weights_dict["Strategy 31"] = "2.50%"
    ensemble.weights = weights_dict

    html_out = _call_build_html(ensemble=ensemble)

    # Extract the rendered weights in weights-section
    # Look for spans with class "wv" (weight value)
    matches = re.findall(r'<span class="wv"[^>]*>([\d.]+)%</span>', html_out)
    assert len(matches) >= 31
    rendered_weights = [float(m) for m in matches[:31]]
    assert round(sum(rendered_weights), 1) == 100.0


def test_drawer_sticky_header_in_html():
    html_out = _call_build_html()
    # Check that stock drawer has padding adjusted and header has position:sticky; top:0;
    assert 'id="stock-drawer"' in html_out
    assert 'position:sticky; top:0;' in html_out or 'position: sticky; top: 0;' in html_out or 'position:sticky;' in html_out
    assert 'background:var(--surface);' in html_out or 'background: var(--surface);' in html_out


def test_search_universe_count_alignment_in_html():
    html_out = _call_build_html()
    # Check that universeMatchesCount logic is embedded in JavaScript
    assert 'universeMatchesCount' in html_out
    assert 'universeMatchesCount > 0 ? `🔍 ${universeMatchesCount}개 항목 일치` : \'🔍 일치하는 종목 없음\'' in html_out


def test_ensemble_table_headers_31_strategies_alignment():
    ensemble = EnsembleData()
    mkt = EnsembleMarket(market="KOSPI")
    mkt.rows.append(EnsembleRow(
        rank=1, symbol="005930", name="삼성전자", score="85.0%", expected_return="15.0%",
        reg="50%", surge="40%", lead_lag="30%", vcp_rule="20%", vcp_ml="10%",
        lstm="50%", stat_arb="60%", sector_rotation="70%", rim_valuation="80%",
        event_driven="90%", mq_factor="50%", iv_skew="40%", order_flow="30%",
        short_term_reversal="20%", arm_factor="10%", card_factor="50%",
        latr_factor="60%", inst_foreign_sector="70%", supply_chain="80%",
        sentiment="90%", factor_neutralized="50%", vol_target="40%",
        microstructure="30%", accruals_quality="20%", short_squeeze="10%",
        valueup_catalyst="50%", trend_efficiency="60%", gamma_squeeze="70%",
        insider_buying="80%", darkpool="90%", earnings_tone_drift="50%",
        cross_asset_spillover="60%", supply_chain_gnn="70%", range_expansion="80%"
    ))
    ensemble.markets.append(mkt)

    html_out = _call_build_html(ensemble=ensemble)

    # Verify all 34 strategy headers and 20D expected return are present in order
    headers_expected = [
        "순위 ↕", "종목코드 ↕", "종목명 ↕", "앙상블 ↕", "20D 예상수익률 ↕",
        "1. Reg ↕", "2. Surge ↕", "3. L-L ↕", "4. VCP-R ↕", "5. VCP-M ↕",
        "6. Strict LSTM ↕" if "6. Strict LSTM ↕" in html_out else "6. LSTM ↕",
        "7. S-Arb ↕", "8. Sec-R ↕", "9. RIM ↕", "10. Event ↕",
        "11. MQ ↕", "12. IV-Sk ↕", "13. Flow ↕", "14. Rev ↕",
        "15. ARM ↕", "16. CARD ↕", "17. LATR ↕", "18. I&amp;F ↕",
        "19. Supply ↕", "20. NLP ↕", "21. Neutral ↕", "22. Vol-T ↕",
        "23. Micro ↕", "24. Accrual ↕", "25. S-Sq ↕", "26. ValueUp ↕",
        "27. TrendEff ↕", "28. GammaSq ↕", "29. Insider ↕", "30. Darkpool ↕",
        "31. ToneDrift ↕", "32. CAS ↕", "33. GNN ↕", "34. REB ↕"
    ]
    for h in headers_expected:
        assert h in html_out, f"Missing header: {h}"


def test_parse_regression_embedded_horizon():
    from trading_system.generate_report import parse_regression
    sample_text = """=== Full Pipeline Inference Results (Merged) ===
Date: 2026-08-23 01:29

--- SP500 TOP 3 (Horizon: 1d) ---
  1. SATS (EchoStar): +5.00%
  2. CAG (Conagra Brands): +4.00%
--- KOSPI TOP 2 (Horizon: 5d) ---
  1. 057050 (현대홈쇼핑): +2.50%
"""
    date, sections = parse_regression(sample_text)
    assert date == "2026-08-23 01:29"
    assert len(sections) == 2
    assert sections[0].market == "SP500"
    assert sections[0].horizon == "1d"
    assert len(sections[0].rows) == 2
    assert sections[0].rows[0].symbol == "SATS"
    assert sections[0].rows[0].expected_return == "+5.00%"

    assert sections[1].market == "KOSPI"
    assert sections[1].horizon == "5d"
    assert len(sections[1].rows) == 1
    assert sections[1].rows[0].symbol == "057050"


def test_parse_sector_multi_word_name_and_markets():
    from trading_system.generate_report import parse_sector
    sample_text = """=== Sector Rotation Momentum & Macro Sensitivity Report ===
Date: 2026-08-23 01:29 KST

1    CAG       Conagra Brands      SP500                                       61.7%
2    EA        Electronic Arts     SP500     Consumer Discretionary            58.3%
3    057050    현대홈쇼핑               KOSPI     Consumer Discretionary            65.0%
"""
    date, rows = parse_sector(sample_text)
    assert len(rows) == 3
    assert rows[0].symbol == "CAG"
    assert rows[0].name == "Conagra Brands"
    assert rows[0].market == "SP500"
    assert rows[0].score == "61.7%"

    assert rows[1].symbol == "EA"
    assert rows[1].name == "Electronic Arts"
    assert rows[1].market == "SP500"
    assert rows[1].sector == "Consumer Discretionary"

    assert rows[2].symbol == "057050"
    assert rows[2].name == "현대홈쇼핑"
    assert rows[2].market == "KOSPI"


def test_format_metric_cell_nan_sanitization():
    from trading_system.generate_report import format_metric_cell
    # Null and NaN cases
    assert "badge-na" in format_metric_cell(None)
    assert "badge-na" in format_metric_cell("nan")
    assert "badge-na" in format_metric_cell("NaN")
    assert "badge-na" in format_metric_cell("nan%")
    assert "badge-na" in format_metric_cell("None")
    assert "badge-na" in format_metric_cell("undefined")
    assert "badge-na" in format_metric_cell("null")
    assert "badge-na" in format_metric_cell("")
    assert "badge-na" in format_metric_cell("-")

    # Semantic badges
    assert "badge-need-data" in format_metric_cell("데이터 수집필요")
    assert "badge-filtered" in format_metric_cell("재무데이터미비")
    assert "badge-filtered" in format_metric_cell("MISSING_FUNDAMENTALS")
    assert "badge-fallback" in format_metric_cell("기본값")

    # Numeric and pct formatting
    score_cell = format_metric_cell("75.4%", kind="score")
    assert "75.4%" in score_cell
    assert "pos" in score_cell

    curr_cell = format_metric_cell(125000, kind="currency")
    assert curr_cell == "125,000"


def test_parse_strategy_coverage_report_full():
    from trading_system.generate_report import parse_strategy_coverage_report
    sample_report = """
================================================================================
34-Strategy Data Coverage & Missingness Audit Report (2026-08-29)
================================================================================
Total Evaluated Symbols: 948

[Strategy Coverage Summary]
--------------------------------------------------------------------------------
Strategy ID                    Valid   Missing   Coverage   Primary Reason / Notes
--------------------------------------------------------------------------------
regression                       948         0     100.0%   None (100% Valid)
surge                            948         0     100.0%   None (100% Valid)
rim_valuation                      0       948       0.0%   NO_FUNDAMENTAL_DATA
stat_arb                           0       948       0.0%   NO_COINTEGRATED_PAIR
================================================================================
"""
    tot, items = parse_strategy_coverage_report(sample_report)
    assert tot == 948
    assert len(items) == 37

    reg_item = next(i for i in items if i.strategy_id == "regression")
    assert reg_item.status == "HEALTHY"
    assert reg_item.valid_count == 948
    assert reg_item.coverage_pct == 100.0

    rim_item = next(i for i in items if i.strategy_id == "rim_valuation")
    assert rim_item.status == "NO_DATA"
    assert rim_item.primary_reason == "NO_FUNDAMENTAL_DATA"
    assert "재무제표" in rim_item.reason_label_ko


def test_build_strategy_health_monitor_html():
    from trading_system.generate_report import build_strategy_health_monitor_html, StrategyHealthInfo
    sample_items = [
        StrategyHealthInfo("regression", 1, "XGBoost 회귀", "AI", "regression", 948, 0, 100.0, "HEALTHY", "None", "정상"),
        StrategyHealthInfo("rim_valuation", 9, "RIM Valuation", "가치", "rim", 0, 948, 0.0, "NO_DATA", "NO_FUNDAMENTAL_DATA", "재무미비"),
    ]
    html = build_strategy_health_monitor_html(948, sample_items)
    assert "health-monitor-section" in html
    assert "Strategy Data Health Monitor" in html
    assert "pill-healthy" in html
    assert "switchTabById('regression')" in html
    assert "switchTabById('rim')" in html


def test_build_tab_status_banner():
    from trading_system.generate_report import build_tab_status_banner
    banner_empty = build_tab_status_banner("Test Strategy", "KOSPI", "empty", "NO_FUNDAMENTAL_DATA")
    assert "strategy-status-banner" in banner_empty
    assert "banner-warning" in banner_empty
    assert "NO_FUNDAMENTAL_DATA" in banner_empty

    banner_stat_arb = build_tab_status_banner("Stat-Arb", "전체", "no_pairs")
    assert "banner-info" in banner_stat_arb
    assert "공적분 페어" in banner_stat_arb


def test_parse_rim_na_and_clean_formatting():
    from trading_system.generate_report import parse_rim
    rim_text = """
================================================================================
RIM (Residual Income Model) Intrinsic Value Analysis (2026-08-29)
================================================================================
Date: 2026-08-29
Total symbols analyzed: 948
Filters: ROE quality >= 0.04, positive equity, operating profit >= 0
--------------------------------------------------------------------------------
Rank Symbol Name Market Price Intrinsic Discount ROE(rep) ROE(adj) EQ Filter RIM_Score
--------------------------------------------------------------------------------
1    005930 삼성전자 KOSPI 60000 75000 +25.0% 12.5% 10.2% 85.0% - 75.0%
2    000660 SK하이닉스 KOSPI 180000 N/A N/A N/A N/A N/A MISSING_FUNDAMENTALS N/A
================================================================================
"""
    date, rows = parse_rim(rim_text)
    assert date == "2026-08-29"
    assert len(rows) == 2
    assert rows[0].symbol == "005930"
    assert rows[1].symbol == "000660"
    assert rows[1].intrinsic_value == "N/A"
    assert rows[1].filter_tags == "MISSING_FUNDAMENTALS"
    assert rows[1].rim_score == "N/A"


def test_34_strategies_tabs_and_panels_presence():
    html_out = _call_build_html()
    # Check that Row 2 navigation has all 34 strategy buttons
    assert "switchTab(this,'crossasset')" in html_out
    assert "switchTab(this,'gnn')" in html_out
    assert "switchTab(this,'rangeexpansion')" in html_out
    assert "32. Cross-Asset" in html_out
    assert "33. Supply Chain GNN" in html_out
    assert "34. Range Expansion" in html_out

    # Check that all 34 strategy tab panels are rendered
    assert 'id="panel-crossasset"' in html_out
    assert 'id="panel-gnn"' in html_out
    assert 'id="panel-rangeexpansion"' in html_out


def test_parse_32_33_34_strategies():
    from trading_system.generate_report import (
        parse_cross_asset_spillover,
        parse_supply_chain_gnn,
        parse_range_expansion
    )
    cas_text = """=== Strategy 35: Cross-Asset Spillover Momentum Predictions ===
Date: 2026-08-30 01:29 KST

1    005930    삼성전자    KOSPI    78.5%
"""
    cas_date, cas_rows = parse_cross_asset_spillover(cas_text)
    assert len(cas_rows) == 1
    assert cas_rows[0].symbol == "005930"
    assert cas_rows[0].score == "78.5%"

    gnn_text = """=== Strategy 36: Supply Chain GNN & Sector Flow Predictions ===
Date: 2026-08-30 01:29 KST

1    000660    SK하이닉스    KOSPI    82.0%
"""
    gnn_date, gnn_rows = parse_supply_chain_gnn(gnn_text)
    assert len(gnn_rows) == 1
    assert gnn_rows[0].symbol == "000660"
    assert gnn_rows[0].score == "82.0%"

    reb_text = """=== Strategy 37: Range Expansion Breakout Predictions ===
Date: 2026-08-30 01:29 KST

1    NVDA    NVIDIA    SP500    91.2%
"""
    reb_date, reb_rows = parse_range_expansion(reb_text)
    assert len(reb_rows) == 1
    assert reb_rows[0].symbol == "NVDA"
    assert reb_rows[0].score == "91.2%"


def test_ux_enhancements_presence():
    html_out = _call_build_html()
    # Check font scaling buttons
    assert 'id="font-scale-small"' in html_out
    assert 'id="font-scale-normal"' in html_out
    assert 'id="font-scale-large"' in html_out

    # Check watchlist quick chip & star buttons
    assert 'id="chip-watchlist"' in html_out
    assert 'btn-watchlist' in html_out
    assert 'toggleWatchlist' in html_out

    # Check column presets toolbar
    assert 'class="column-presets-group"' in html_out
    assert 'id="col-preset-all"' in html_out
    assert 'id="col-preset-ai"' in html_out
    assert 'id="col-preset-mom"' in html_out
    assert 'id="col-preset-val"' in html_out
    assert 'id="col-preset-flow"' in html_out
    assert 'id="col-preset-macro"' in html_out

    # Check table sort reset button
    assert 'class="btn-reset-sort"' in html_out
    assert 'resetTableSort()' in html_out

    # Check drawer factor tabs
    assert 'class="drawer-factor-tabs"' in html_out
    assert 'filterDrawerFactors' in html_out




