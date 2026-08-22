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
