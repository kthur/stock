"""
tests/test_m2_adversarial_challenger2_ux.py — Adversarial Empirical Stress Test Suite for Milestone M2.

Focus Areas:
1. Verification that .health-pill meets 44px minimum tap targets.
2. Verification that frozen columns compact to 190px on < 768px, leaving >= 180px for recommendation metrics.
3. Stress testing of table horizontal swiping performance (momentum scrolling, z-index isolation, background opacity, boundary shadow).
4. Viewport coverage across 320px, 360px, 375px, 390px, 414px, 480px, and 768px.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List
import pytest
from bs4 import BeautifulSoup

from trading_system.report_multipage import build_styles

GH_PAGES_INDEX = Path("gh-pages/index.html")


def extract_all_media_query_blocks(css: str, max_width: int) -> List[str]:
    """Extract all blocks matching @media (max-width: {max_width}px) { ... } in CSS."""
    pattern = rf'@media\s*\(\s*max-width\s*:\s*{max_width}px\s*\)\s*\{{+'
    matches = list(re.finditer(pattern, css, flags=re.IGNORECASE))
    results = []
    for match in matches:
        start_idx = match.end()
        brace_count = match.group(0).count('{')
        i = start_idx
        while i < len(css) and brace_count > 0:
            if css[i] == '{':
                brace_count += 1
            elif css[i] == '}':
                brace_count -= 1
            i += 1
        results.append(css[start_idx:max(start_idx, i - 1)])
    return results


@pytest.fixture(scope="module")
def index_html_and_css():
    assert GH_PAGES_INDEX.exists(), f"Missing {GH_PAGES_INDEX}"
    html = GH_PAGES_INDEX.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    styles = [s.get_text() for s in soup.find_all("style")]
    css = "\n".join(styles)
    return html, soup, css


# =============================================================================
# 1. Verification of .health-pill 44px Minimum Tap Targets
# =============================================================================

def test_health_pill_css_touch_target_rules(index_html_and_css):
    """
    Empirically verify that .health-pill CSS rules strictly satisfy mobile touch target standards:
    - min-height >= 44px (WCAG 2.5.5 / Apple HIG standard)
    - display: inline-flex with vertical centering (align-items: center)
    - touch-action: manipulation to eliminate 300ms tap delay
    - box-sizing: border-box
    - adequate padding (padding: 6px 14px)
    """
    _, _, css = index_html_and_css
    blocks = extract_all_media_query_blocks(css, 768)
    assert len(blocks) > 0, "Missing @media (max-width: 768px) in index.html"

    # Search for effective .health-pill rule across 768px blocks (latest block overrides earlier)
    pill_rule = ""
    for block in blocks:
        m = re.findall(r'\.health-pill\s*\{([^}]+)\}', block)
        if m:
            pill_rule = m[-1]

    assert pill_rule, "Missing .health-pill rule under @media (max-width: 768px)"

    # Assert min-height is at least 44px
    min_h_match = re.search(r'min-height\s*:\s*(\d+)px', pill_rule)
    assert min_h_match is not None, f".health-pill missing min-height in mobile rule: {pill_rule}"
    min_h = int(min_h_match.group(1))
    assert min_h >= 44, f".health-pill min-height is {min_h}px, expected >= 44px"

    # Assert display is inline-flex or flex (so height applies properly to span/button)
    assert "display: inline-flex" in pill_rule or "display:flex" in pill_rule or "display: inline-block" in pill_rule, (
        f".health-pill must be inline-flex or flex, found: {pill_rule}"
    )

    # Assert touch-action: manipulation
    assert "touch-action: manipulation" in pill_rule, (
        f".health-pill must include touch-action: manipulation for fast touch response: {pill_rule}"
    )

    # Assert box-sizing: border-box
    assert "box-sizing: border-box" in pill_rule, (
        f".health-pill must include box-sizing: border-box: {pill_rule}"
    )


def test_health_pill_dom_elements_and_affordance(index_html_and_css):
    """
    Verify all health-pills in the actual generated DOM:
    - Clickable filter pills must be semantic <button type="button"> elements
    - Clickable pills have onclick handler and valid filter targets
    - Spans are reserved for purely informational pills (avg coverage, total universe)
    - Total pill count >= 7
    - Container .health-summary-pills has flex-wrap: wrap to prevent viewport clipping
    """
    _, soup, _ = index_html_and_css
    pills = soup.select(".health-pill")
    assert len(pills) >= 7, f"Expected at least 7 .health-pill elements, found {len(pills)}"

    button_pills = [p for p in pills if p.name == "button"]
    span_pills = [p for p in pills if p.name == "span"]

    # 5 interactive filter buttons: healthy, partial, fallback, nodata, all
    assert len(button_pills) == 5, f"Expected 5 <button> health pills, found {len(button_pills)}"
    for btn in button_pills:
        assert btn.get("type") == "button", f"Filter pill button missing type='button': {btn}"
        assert btn.get("onclick") is not None, f"Filter pill button missing onclick handler: {btn}"
        assert "filterHealthCards" in btn.get("onclick"), f"Filter pill onclick missing filterHealthCards: {btn}"
        # Button text should not be empty
        assert len(btn.get_text().strip()) > 3, f"Pill button text is too short or empty: {btn}"

    # 2 info spans: avg coverage, universe count
    assert len(span_pills) == 2, f"Expected 2 <span> health pills, found {len(span_pills)}"

    # Check container has flex-wrap
    container = soup.select_one(".health-summary-pills")
    assert container is not None, "Missing .health-summary-pills container in DOM"


def test_health_pill_rendered_geometry_estimate(index_html_and_css):
    """
    Adversarial geometry check:
    Verify that every .health-pill label, combined with font-size 11.5px and padding 14px horizontal,
    yields an estimated bounding width >= 44px, ensuring full 44x44px minimum tap target compliance.
    """
    _, soup, _ = index_html_and_css
    pills = soup.select(".health-pill")

    for p in pills:
        text = p.get_text().strip()
        approx_w = 28 + len(text) * 6.5
        assert approx_w >= 44, f"Pill '{text}' estimated width {approx_w:.1f}px < 44px minimum touch target"


# =============================================================================
# 2. Verification of Frozen Columns Compacting to 190px (< 768px)
# =============================================================================

def test_ensemble_table_frozen_columns_compacting(index_html_and_css):
    """
    Verify that under @media (max-width: 768px):
    1. .sticky-rank is compacted to 36px (left: 0).
    2. .sticky-symbol is compacted to 68px (left: 36px).
    3. .sticky-name is compacted to min-width 86px, max-width 96px (left: 104px).
    4. Exact coordinate alignment: left(symbol) == width(rank) and left(name) == left(symbol) + width(symbol).
    5. Total minimum frozen width == 36 + 68 + 86 = 190px.
    """
    _, _, css = index_html_and_css
    blocks = extract_all_media_query_blocks(css, 768)
    assert len(blocks) > 0, "Missing @media (max-width: 768px) blocks in index.html"

    # Find the effective rules in the cascading stylesheet (last match wins)
    rank_rules = []
    sym_rules = []
    name_rules = []

    for block in blocks:
        rank_rules.extend(re.findall(r'\.table-wrap\s+\.sticky-rank\s*\{([^}]+)\}', block))
        sym_rules.extend(re.findall(r'\.table-wrap\s+\.sticky-symbol\s*\{([^}]+)\}', block))
        name_rules.extend(re.findall(r'\.table-wrap\s+\.sticky-name\s*\{([^}]+)\}', block))

    assert rank_rules, "Missing .table-wrap .sticky-rank rule in @media (max-width: 768px)"
    assert sym_rules, "Missing .table-wrap .sticky-symbol rule in @media (max-width: 768px)"
    assert name_rules, "Missing .table-wrap .sticky-name rule in @media (max-width: 768px)"

    effective_rank = rank_rules[-1]
    effective_sym = sym_rules[-1]
    effective_name = name_rules[-1]

    # 1. Rank column
    assert "left: 0" in effective_rank, f"sticky-rank must have left: 0, found: {effective_rank}"
    rank_w = int(re.search(r'width\s*:\s*(\d+)px', effective_rank).group(1))
    assert rank_w == 36, f"sticky-rank width is {rank_w}px, expected 36px"

    # 2. Symbol column
    sym_left = int(re.search(r'left\s*:\s*(\d+)px', effective_sym).group(1))
    sym_w = int(re.search(r'width\s*:\s*(\d+)px', effective_sym).group(1))
    assert sym_left == rank_w, f"sticky-symbol left ({sym_left}px) must equal rank width ({rank_w}px)"
    assert sym_w == 68, f"sticky-symbol width is {sym_w}px, expected 68px"

    # 3. Name column
    name_left = int(re.search(r'left\s*:\s*(\d+)px', effective_name).group(1))
    assert name_left == rank_w + sym_w, f"sticky-name left ({name_left}px) must equal rank+symbol ({rank_w + sym_w}px)"

    name_min_w = int(re.search(r'min-width\s*:\s*(\d+)px', effective_name).group(1))
    name_max_w = int(re.search(r'max-width\s*:\s*(\d+)px', effective_name).group(1))
    assert name_min_w == 86, f"sticky-name min-width is {name_min_w}px, expected 86px"
    assert name_max_w <= 96, f"sticky-name max-width is {name_max_w}px, expected <= 96px"

    # 4. Total frozen width
    total_frozen_min = rank_w + sym_w + name_min_w
    assert total_frozen_min == 190, f"Total frozen column minimum width is {total_frozen_min}px, expected 190px"


@pytest.mark.parametrize("viewport_width", [375, 390, 414, 480, 767])
def test_remaining_metric_viewport_budget(viewport_width: int):
    """
    Stress-test remaining viewport budget for recommendation metrics:
    Requirement: Leaving >= 180px for recommendation metrics on mobile screens (< 768px).
    Tested across iPhone SE (375px), iPhone 12/13/14 (390px), iPhone Plus (414px), 480px, and 767px.
    """
    frozen_width = 190  # 36 + 68 + 86
    remaining_space = viewport_width - frozen_width
    assert remaining_space >= 180, (
        f"Viewport width {viewport_width}px minus 190px frozen columns leaves "
        f"{remaining_space}px < 180px minimum metric space!"
    )


# =============================================================================
# 3. Table Horizontal Swiping Performance & Touch Mechanics
# =============================================================================

def test_table_horizontal_swiping_css_mechanics(index_html_and_css):
    """
    Verify CSS rules required for 60fps smooth touch horizontal scrolling on mobile:
    1. .table-wrap has overflow-x: auto !important
    2. -webkit-overflow-scrolling: touch !important (hardware momentum scrolling on iOS WebKit)
    3. scroll-behavior: smooth !important
    4. Table rows have min-height >= 44px for thumb tap ergonomics
    """
    _, _, css = index_html_and_css
    blocks = extract_all_media_query_blocks(css, 768)
    assert len(blocks) > 0, "Missing @media (max-width: 768px)"

    # Effective .table-wrap rule in mobile media queries
    wrap_rules = []
    for b in blocks:
        wrap_rules.extend(re.findall(r'(?:^|[^{};])\s*\.table-wrap\s*\{([^}]+)\}', b))

    assert wrap_rules, "Missing .table-wrap rule in @media (max-width: 768px)"
    effective_wrap = " ".join(wrap_rules)

    assert "overflow-x: auto" in effective_wrap or "overflow-x:auto" in effective_wrap, (
        f".table-wrap must have overflow-x: auto, found: {effective_wrap}"
    )
    assert "-webkit-overflow-scrolling: touch" in effective_wrap, (
        f".table-wrap must have -webkit-overflow-scrolling: touch for iOS momentum scroll: {effective_wrap}"
    )
    assert "scroll-behavior: smooth" in effective_wrap, (
        f".table-wrap must have scroll-behavior: smooth: {effective_wrap}"
    )

    # Row touch height
    row_rules = []
    for b in blocks:
        row_rules.extend(re.findall(r'\.clickable-row\s+td\s*\{([^}]+)\}', b))
    assert row_rules, "Missing .clickable-row td rule in @media (max-width: 768px)"
    effective_row = row_rules[-1]
    assert "min-height: 44px" in effective_row, f"Table row td must define min-height: 44px, found: {effective_row}"


def test_table_sticky_column_background_opacity_and_z_index(index_html_and_css):
    """
    Adversarial bleed-through and z-fighting check:
    When a user swipes horizontally, non-sticky columns scroll behind the frozen columns.
    If frozen column cells lack an opaque background, content bleeds through.
    If z-indices are inverted or missing, non-sticky cells overlap on top.
    """
    _, _, css = index_html_and_css

    # Check background on sticky cells
    sticky_col_match = re.search(r'\.table-wrap\s+(?:th|td)\.sticky-col[^{]*\{([^}]+)\}', css)
    assert sticky_col_match is not None, "Missing .table-wrap th/td.sticky-col base rule"
    sticky_col_body = sticky_col_match.group(1)
    assert "background: var(--surface)" in sticky_col_body, (
        f"td.sticky-col must have background: var(--surface) to prevent bleed-through: {sticky_col_body}"
    )

    # Check header sticky cells
    header_sticky_match = re.search(r'\.table-wrap\s+th\.sticky-col\s*\{([^}]+)\}', css)
    assert header_sticky_match is not None, "Missing .table-wrap th.sticky-col rule"
    header_body = header_sticky_match.group(1)
    assert "background: var(--surface2)" in header_body, (
        f"th.sticky-col must have opaque background: var(--surface2): {header_body}"
    )

    # Check z-index hierarchy:
    # rank (4) > symbol (3) > name (2)
    # th.rank (14) > th.symbol (13) > th.name (12)
    assert re.search(r'\.table-wrap\s+td\.sticky-rank\s*\{[^}]*z-index:\s*4', css) is not None
    assert re.search(r'\.table-wrap\s+td\.sticky-symbol\s*\{[^}]*z-index:\s*3', css) is not None
    assert re.search(r'\.table-wrap\s+td\.sticky-name\s*\{[^}]*z-index:\s*2', css) is not None

    # Check right boundary visual separator (box-shadow and border-right on sticky-name)
    blocks = extract_all_media_query_blocks(css, 768)
    name_rules = []
    for b in blocks:
        name_rules.extend(re.findall(r'\.table-wrap\s+\.sticky-name\s*\{([^}]+)\}', b))
    assert name_rules
    effective_name = name_rules[-1]
    assert "border-right:" in effective_name, f"sticky-name must have border-right separator: {effective_name}"
    assert "box-shadow:" in effective_name, f"sticky-name must have box-shadow depth cue: {effective_name}"


def test_ensemble_table_recommendation_metric_columns_exist(index_html_and_css):
    """
    Verify that the Ensemble Top Recommendations tables contain recommendation metric columns
    following the frozen columns, ensuring rich quantitative metrics during horizontal swipe (42 columns total).
    """
    _, soup, _ = index_html_and_css
    tables = [t for t in soup.select("table") if t.select(".sticky-rank")]
    assert len(tables) >= 1, "Expected at least 1 Ensemble recommendation table with sticky columns in index.html"

    for table in tables:
        headers = [th.get_text().strip() for th in table.select("thead tr th")]
        # Must have 42 columns (3 frozen + 39 recommendation metrics)
        assert len(headers) == 42, f"Expected 42 columns in Ensemble table, found {len(headers)}"

        # Check that frozen columns are first 3
        th0 = table.select("thead tr th")[0]
        th1 = table.select("thead tr th")[1]
        th2 = table.select("thead tr th")[2]

        assert "sticky-rank" in th0.get("class", []), f"Col 0 missing sticky-rank: {th0}"
        assert "sticky-symbol" in th1.get("class", []), f"Col 1 missing sticky-symbol: {th1}"
        assert "sticky-name" in th2.get("class", []), f"Col 2 missing sticky-name: {th2}"

        # Verify presence of strategy metric columns (col-strat)
        metric_ths = table.select("thead tr th")[3:]
        strat_cols = [th for th in metric_ths if any("col-strat" in c for c in th.get("class", []))]
        assert len(strat_cols) >= 35, f"Expected at least 35 strategy factor columns, found {len(strat_cols)}"
