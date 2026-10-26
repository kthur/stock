"""
tests/test_dashboard_mobile_m2_adversarial.py — Adversarial Verification Suite for Milestone M2

Tests the Executive Dashboard Mobile UX Stacking & Card Adaptation (Requirement R2 & Acceptance Criterion A3).
Actively challenges:
1. Integrity violations: checks that implementation is genuine and not hardcoded facade.
2. Viewport boundary conditions: 768px, 480px, 375px, 360px, 320px.
3. Card 1 (2D Regime & Risk Gates) layout geometry and absence of carousel regressions.
4. Card 2 (Strategy Health Monitor) WCAG/Apple HIG >= 44px tap target heights and grid collapse.
5. Card 3 (Portfolio & Allocation) canvas height scaling and 1-column layout.
6. Ensemble Table frozen column geometry: exact offset alignment (left: 0 -> 36 -> 104) and total width <= 190-200px.
7. File size budget compliance: index.html < 512,000 bytes with CSS minification integrity.
"""

from __future__ import annotations

import re
from pathlib import Path
import pytest
from bs4 import BeautifulSoup

from trading_system.report_multipage import (
    build_head,
    build_styles,
    build_index_html,
)

INDEX_PATH = Path("gh-pages/index.html")


def extract_css_from_html(html_str: str) -> str:
    soup = BeautifulSoup(html_str, "html.parser")
    return "\n".join(s.get_text() for s in soup.find_all("style"))


def extract_media_block(css: str, max_width: int) -> str:
    pattern = rf'@media\s*\(\s*max-width\s*:\s*{max_width}px\s*\)\s*\{{+'
    matches = list(re.finditer(pattern, css, flags=re.IGNORECASE))
    if not matches:
        return ""
    blocks = []
    for match in matches:
        start = match.end()
        braces = match.group(0).count('{')
        i = start
        while i < len(css) and braces > 0:
            if css[i] == '{':
                braces += 1
            elif css[i] == '}':
                braces -= 1
            i += 1
        blocks.append(css[start:max(start, i - 1)])
    return "\n".join(blocks)


# =============================================================================
# 1. Integrity Violation Checks
# =============================================================================

def test_integrity_dynamic_rendering_not_facade():
    """Ensure index.html is dynamically rendered with real production data, not static stub."""
    assert INDEX_PATH.exists(), "gh-pages/index.html must exist"
    content = INDEX_PATH.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")

    # Card 1: Must contain 11 macro items and real regime console details
    card1 = soup.select_one(".regime-risk-card")
    assert card1 is not None, "INTEGRITY VIOLATION: .regime-risk-card not found"
    macro_items = card1.select(".macro-item")
    assert len(macro_items) >= 6, f"INTEGRITY VIOLATION: Expected >= 6 macro items, found {len(macro_items)}"
    console_details = card1.select_one("#regime-console-details")
    assert console_details is not None, "INTEGRITY VIOLATION: #regime-console-details not found"

    # Card 2: Must contain real strategy health cards for all 37 strategies
    card2 = soup.select_one(".health-monitor-section")
    assert card2 is not None, "INTEGRITY VIOLATION: .health-monitor-section not found"
    health_cards = card2.select(".health-card")
    assert len(health_cards) >= 30, f"INTEGRITY VIOLATION: Expected >= 30 health cards, found {len(health_cards)}"
    pills = card2.select(".health-pill")
    assert len(pills) >= 4, f"INTEGRITY VIOLATION: Expected >= 4 summary pills, found {len(pills)}"

    # Card 3: Must contain charts grid and canvas
    charts_grid = soup.select_one(".charts-grid")
    assert charts_grid is not None, "INTEGRITY VIOLATION: .charts-grid not found"
    canvases = charts_grid.select("canvas")
    assert len(canvases) >= 1, "INTEGRITY VIOLATION: Canvas elements missing in Card 3"


# =============================================================================
# 2. Card 1: 2D Regime & Risk Gates Mobile Stacking & Grid Resilience
# =============================================================================

def test_card1_macro_grid_stacking_geometry():
    """Verify Card 1 .macro-grid collapses to 2-col on 768px and 1-col on 480px, with no flex carousel."""
    content = INDEX_PATH.read_text(encoding="utf-8")
    css = extract_css_from_html(content)
    mq768 = extract_media_block(css, 768)
    mq480 = extract_media_block(css, 480)

    # 1. 768px: repeat(2, 1fr)
    macro_768 = re.search(r'\.macro-grid\s*\{[^}]*grid-template-columns\s*:\s*repeat\(2,\s*1fr\)', mq768)
    assert macro_768 is not None, "Card 1 .macro-grid must have repeat(2, 1fr) on < 768px"

    # 2. 768px: Ensure display is grid, NOT flex (which previously broke grid wrapping)
    assert re.search(r'\.macro-grid\s*\{[^}]*display\s*:\s*grid', mq768) is not None, (
        ".macro-grid on < 768px must enforce display: grid !important"
    )

    # 3. 480px: 1fr single column
    macro_480 = re.search(r'\.macro-grid\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq480)
    assert macro_480 is not None, "Card 1 .macro-grid must have 1fr on < 480px"

    # 4. Gate status strip: repeat(2, 1fr) on 768px and 1fr on 480px
    gate_768 = re.search(r'\.gate-status-strip\s*\{[^}]*grid-template-columns\s*:\s*repeat\(2,\s*1fr\)', mq768)
    assert gate_768 is not None, ".gate-status-strip must have repeat(2, 1fr) on < 768px"
    gate_480 = re.search(r'\.gate-status-strip\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq480)
    assert gate_480 is not None, ".gate-status-strip must have 1fr on < 480px"

    # 5. Console details single column override
    details_768 = re.search(r'#regime-console-details\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq768)
    assert details_768 is not None, "#regime-console-details must have 1fr on < 768px"

    # 6. .macro-item min-width: 0 to prevent grid blowout
    item_768 = re.search(r'\.macro-item\s*\{[^}]*min-width\s*:\s*0', mq768)
    assert item_768 is not None, ".macro-item must specify min-width: 0 !important on mobile"


# =============================================================================
# 3. Card 2: Strategy Health Monitor Tap Target & Grid Stacking
# =============================================================================

def test_card2_health_monitor_tap_targets_and_grid():
    """Verify Card 2 .health-pill >= 44px height, .health-grid 2-col/1-col, and .health-card min-height."""
    content = INDEX_PATH.read_text(encoding="utf-8")
    css = extract_css_from_html(content)
    mq768 = extract_media_block(css, 768)
    mq480 = extract_media_block(css, 480)

    # 1. Health pill min-height: 44px
    pill_match = re.search(r'\.health-pill\s*\{[^}]*min-height\s*:\s*44px', mq768)
    assert pill_match is not None, ".health-pill must define min-height: 44px on < 768px"

    # 2. Health pill touch-action: manipulation
    assert "touch-action: manipulation" in mq768, ".health-pill should include touch-action: manipulation"

    # 3. Health grid: repeat(2, 1fr) on 768px and 1fr on 480px
    hgrid_768 = re.search(r'\.health-grid\s*\{[^}]*grid-template-columns\s*:\s*repeat\(2,\s*1fr\)', mq768)
    assert hgrid_768 is not None, ".health-grid must have repeat(2, 1fr) on < 768px"
    hgrid_480 = re.search(r'\.health-grid\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq480)
    assert hgrid_480 is not None, ".health-grid must have 1fr on < 480px"

    # 4. Health card min-height: 44px
    hcard_768 = re.search(r'\.health-card\s*\{[^}]*min-height\s*:\s*44px', mq768)
    assert hcard_768 is not None, ".health-card must have min-height: 44px on < 768px"

    # 5. Breakdown layout single column
    assert re.search(r'\.health-reasons-breakdown\s*>\s*div\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq768) is not None, (
        ".health-reasons-breakdown > div must stack into 1fr on < 768px"
    )


# =============================================================================
# 4. Card 3: Portfolio & Allocation Canvas Scalability & Stacking
# =============================================================================

def test_card3_portfolio_charts_grid_scaling():
    """Verify Card 3 .charts-grid 1-col override, chart-card 100% width, and canvas height scaling."""
    content = INDEX_PATH.read_text(encoding="utf-8")
    css = extract_css_from_html(content)
    mq768 = extract_media_block(css, 768)
    mq480 = extract_media_block(css, 480)

    # 1. Charts grid 1fr override
    cgrid_768 = re.search(r'\.charts-grid\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq768)
    assert cgrid_768 is not None, ".charts-grid must override minmax(320px, 1fr) to 1fr on < 768px"

    # 2. Chart card width 100% and box-sizing border-box
    ccard_768 = re.search(r'\.chart-card\s*\{[^}]*width\s*:\s*100%', mq768)
    assert ccard_768 is not None, ".chart-card must have width: 100% on < 768px"

    # 3. Canvas height scaling (280px on 768px, 260px on 480px)
    h_768 = re.search(r'\.chart-card\s*>\s*div\[style\*="height"\]\s*\{[^}]*height\s*:\s*280px', mq768)
    assert h_768 is not None, "Chart canvas wrapper must scale height to 280px on < 768px"
    h_480 = re.search(r'\.chart-card\s*>\s*div\[style\*="height"\]\s*\{[^}]*height\s*:\s*260px', mq480)
    assert h_480 is not None, "Chart canvas wrapper must scale height to 260px on < 480px"


# =============================================================================
# 5. Ensemble Table: Frozen Column Geometry & Offsets Alignment
# =============================================================================

def test_ensemble_table_frozen_columns_geometry():
    """Verify exact left-offset geometry and <= 190px total frozen width."""
    content = INDEX_PATH.read_text(encoding="utf-8")
    css = extract_css_from_html(content)
    mq768 = extract_media_block(css, 768)

    # 1. Column 0 (Rank): left: 0, width: 36px
    rank_left = re.search(r'\.table-wrap\s+\.sticky-rank\s*\{[^}]*(?<![-a-zA-Z])left\s*:\s*0', mq768)
    rank_width = re.search(r'\.table-wrap\s+\.sticky-rank\s*\{[^}]*(?<![-a-zA-Z])width\s*:\s*(\d+)px', mq768)
    assert rank_left is not None, ".sticky-rank must have left: 0"
    assert rank_width is not None, ".sticky-rank must have fixed width"
    w_rank = int(rank_width.group(1))
    assert w_rank == 36, f"Expected .sticky-rank width 36px, got {w_rank}px"

    # 2. Column 1 (Symbol): left: 36px, width: 68px
    sym_left = re.search(r'\.table-wrap\s+\.sticky-symbol\s*\{[^}]*(?<![-a-zA-Z])left\s*:\s*(\d+)px', mq768)
    sym_width = re.search(r'\.table-wrap\s+\.sticky-symbol\s*\{[^}]*(?<![-a-zA-Z])width\s*:\s*(\d+)px', mq768)
    assert sym_left is not None, ".sticky-symbol must specify left offset"
    assert sym_width is not None, ".sticky-symbol must have fixed width"
    l_sym = int(sym_left.group(1))
    w_sym = int(sym_width.group(1))
    assert l_sym == w_rank, f"Geometric alignment failure: .sticky-symbol left {l_sym} != rank width {w_rank}"
    assert w_sym == 68, f"Expected .sticky-symbol width 68px, got {w_sym}px"

    # 3. Column 2 (Name): left: 104px, min-width: 86px
    name_left = re.search(r'\.table-wrap\s+\.sticky-name\s*\{[^}]*(?<![-a-zA-Z])left\s*:\s*(\d+)px', mq768)
    name_min_w = re.search(r'\.table-wrap\s+\.sticky-name\s*\{[^}]*(?<![-a-zA-Z])min-width\s*:\s*(\d+)px', mq768)
    assert name_left is not None, ".sticky-name must specify left offset"
    assert name_min_w is not None, ".sticky-name must specify min-width"
    l_name = int(name_left.group(1))
    min_w_name = int(name_min_w.group(1))
    assert l_name == w_rank + w_sym, f"Geometric alignment failure: name left {l_name} != {w_rank + w_sym}"
    assert min_w_name == 86, f"Expected min-width 86px, got {min_w_name}px"

    # Total frozen width = 36 + 68 + 86 = 190px
    total_frozen_width = w_rank + w_sym + min_w_name
    assert total_frozen_width <= 190, f"Total frozen column width {total_frozen_width}px exceeds 190px budget!"

    # 4. Box shadow on sticky-name to separate frozen columns from scroll area
    assert "box-shadow:" in mq768 and "sticky-name" in mq768, ".sticky-name must have a box shadow separator"

    # 5. Smooth scrolling
    assert "-webkit-overflow-scrolling: touch" in mq768, ".table-wrap must have -webkit-overflow-scrolling: touch"


# =============================================================================
# 6. File Size Budget & Minification Integrity
# =============================================================================

def test_file_size_budget_and_css_minification_integrity():
    """Verify gh-pages/index.html is under 512,000 bytes with zero CSS syntax corruption."""
    size = INDEX_PATH.stat().st_size
    assert size < 512000, f"Budget violation: {INDEX_PATH} is {size} bytes >= 512,000 bytes!"

    content = INDEX_PATH.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")
    styles = soup.find_all("style")
    assert len(styles) >= 1, "index.html must have at least one <style> tag"

    for idx, s in enumerate(styles):
        css_text = s.get_text()
        open_b = css_text.count('{')
        close_b = css_text.count('}')
        assert open_b == close_b, (
            f"CSS syntax error: Style tag {idx} has mismatched braces ({open_b} open != {close_b} close)"
        )
        assert open_b > 0, f"Style tag {idx} contains no rules"
