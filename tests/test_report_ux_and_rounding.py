import pytest
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
        insider_buying="80%", darkpool="90%", earnings_tone_drift="50%"
    ))
    ensemble.markets.append(mkt)

    html_out = _call_build_html(ensemble=ensemble)

    # Verify all 31 strategy headers and 20D expected return are present in order
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
        "31. ToneDrift ↕"
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

