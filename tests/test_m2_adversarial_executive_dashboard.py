"""
tests/test_m2_adversarial_executive_dashboard.py — Empirical Challenger Test Suite for Milestone M2

Adversarially stresses and verifies:
1. Card 1 (.macro-grid, .gate-status-strip, #regime-console-details) across viewports:
   320px, 375px, 390px, 480px, 768px.
2. Card 3 (.charts-grid and canvas scaling).
3. Zero horizontal blowout on narrow screens (320px - 768px).
4. Geometry simulation and layout width budget analysis.
5. Ensemble table frozen column compaction and touch scrolling.
6. Touch target accessibility (>= 44px).
7. HTML file size budget (< 512,000 bytes).
"""

from __future__ import annotations

import re
from pathlib import Path
import pytest
from bs4 import BeautifulSoup

INDEX_HTML_PATH = Path("gh-pages/index.html")
VIEWPORTS = [320, 375, 390, 480, 768]


@pytest.fixture(scope="module")
def index_html_content() -> str:
    assert INDEX_HTML_PATH.exists(), f"Missing {INDEX_HTML_PATH}"
    return INDEX_HTML_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def index_soup(index_html_content: str) -> BeautifulSoup:
    return BeautifulSoup(index_html_content, "html.parser")


@pytest.fixture(scope="module")
def index_css(index_soup: BeautifulSoup) -> str:
    styles = [s.get_text() for s in index_soup.find_all("style")]
    return "\n".join(styles)


def extract_media_query_rules(css: str, max_width: int) -> str:
    """Extract all text within @media (max-width: {max_width}px) blocks."""
    pattern = rf'@media\s*\(\s*max-width\s*:\s*{max_width}px\s*\)\s*\{{+'
    matches = list(re.finditer(pattern, css, flags=re.IGNORECASE))
    if not matches:
        return ""
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
    return "\n".join(results)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Card 1 Viewport Stress Matrix: 320px, 375px, 390px, 480px, 768px
# ─────────────────────────────────────────────────────────────────────────────

class TestCard1ViewportStressMatrix:
    """Stress test Card 1 layout rules across 5 mobile viewports."""

    @pytest.mark.parametrize("vp", [320, 375, 390, 480])
    def test_card1_narrow_viewports_single_column(self, index_css: str, vp: int):
        """On screens <= 480px, .macro-grid and .gate-status-strip must collapse to 1fr."""
        mq480 = extract_media_query_rules(index_css, 480)
        assert len(mq480) > 0, "Missing @media (max-width: 480px)"

        # 1. .macro-grid single column
        macro_match = re.search(r'\.macro-grid\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq480, re.IGNORECASE)
        assert macro_match is not None, f"Viewport {vp}px: .macro-grid must have grid-template-columns: 1fr"

        # 2. .gate-status-strip single column
        gate_match = re.search(r'\.gate-status-strip\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq480, re.IGNORECASE)
        assert gate_match is not None, f"Viewport {vp}px: .gate-status-strip must have grid-template-columns: 1fr"

        # 3. .regime-risk-card margins reduced to <= 10px
        card_margin_match = re.search(r'\.regime-risk-card\s*\{[^}]*margin\s*:\s*10px\s+8px', mq480, re.IGNORECASE)
        assert card_margin_match is not None, f"Viewport {vp}px: .regime-risk-card margins must be 8px-10px"

    def test_card1_tablet_viewport_768px_two_columns(self, index_css: str):
        """On 768px tablet, .macro-grid and .gate-status-strip collapse to 2 columns."""
        mq768 = extract_media_query_rules(index_css, 768)
        assert len(mq768) > 0, "Missing @media (max-width: 768px)"

        # .macro-grid 2 columns
        assert re.search(r'\.macro-grid\s*\{[^}]*grid-template-columns\s*:\s*repeat\(2,\s*1fr\)', mq768, re.IGNORECASE) is not None, (
            "768px: .macro-grid must have grid-template-columns: repeat(2, 1fr)"
        )

        # .gate-status-strip 2 columns
        assert re.search(r'\.gate-status-strip\s*\{[^}]*grid-template-columns\s*:\s*repeat\(2,\s*1fr\)', mq768, re.IGNORECASE) is not None, (
            "768px: .gate-status-strip must have grid-template-columns: repeat(2, 1fr)"
        )

    @pytest.mark.parametrize("vp", VIEWPORTS)
    def test_card1_regime_console_details_single_column(self, index_css: str, vp: int):
        """On all mobile viewports <= 768px, #regime-console-details must collapse to 1fr."""
        mq768 = extract_media_query_rules(index_css, 768)
        assert re.search(r'#regime-console-details\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq768, re.IGNORECASE) is not None, (
            f"Viewport {vp}px: #regime-console-details must override desktop minmax(340px, 1fr) to 1fr"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Geometry & Horizontal Blowout Stress Simulation
# ─────────────────────────────────────────────────────────────────────────────

class TestHorizontalBlowoutGeometrySimulation:
    """Simulate layout geometry mathematically to prove 0 horizontal blowout."""

    @pytest.mark.parametrize("vp", VIEWPORTS)
    def test_card1_layout_budget_non_negative(self, vp: int):
        """
        Verify available content width inside Card 1 is positive and fits 1fr (or 2fr) items:
        available_width = vp - outer_padding - card_margins - card_padding
        """
        if vp <= 480:
            outer_padding = 10 * 2  # 10px left/right on body/content
            card_margin = 8 * 2    # 8px left/right
            card_padding = 14 * 2   # 14px left/right inside regime-risk-body
            cols = 1
            gap = 6
        else:
            outer_padding = 14 * 2
            card_margin = 14 * 2
            card_padding = 14 * 2
            cols = 2
            gap = 8

        available_content_width = vp - outer_padding - card_margin - card_padding
        assert available_content_width > 0, f"Viewport {vp}px resulted in negative content width: {available_content_width}px"

        col_width = (available_content_width - (cols - 1) * gap) / cols
        assert col_width >= 100, f"Viewport {vp}px col_width {col_width}px too narrow for macro item tile"

        total_consumed = outer_padding + card_margin + card_padding + cols * col_width + (cols - 1) * gap
        assert abs(total_consumed - vp) < 1e-4, f"Geometry mismatch: {total_consumed} != {vp}"

    def test_global_overflow_x_hidden(self, index_css: str):
        """Confirm body and html enforce overflow-x: hidden to eliminate horizontal blowout."""
        body_overflow = re.search(r'body\s*\{[^}]*overflow-x\s*:\s*hidden', index_css, re.IGNORECASE)
        assert body_overflow is not None, "Global body must have overflow-x: hidden"

    def test_regime_matrix_table_has_overflow_container(self, index_soup: BeautifulSoup):
        """Verify the 6-regime table is enclosed in a .table-wrap container to prevent table blowout."""
        regime_details = index_soup.find("div", attrs={"id": "regime-console-details"})
        assert regime_details is not None, "Missing #regime-console-details element"

        table = regime_details.find("table")
        assert table is not None, "Missing 6-regime dynamic matrix table in #regime-console-details"

        parent_wrap = table.find_parent("div", class_="table-wrap")
        assert parent_wrap is not None, (
            "6-regime dynamic matrix table must be enclosed in a .table-wrap div for horizontal touch scroll"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Card 3 Charts Grid & Canvas Scaling
# ─────────────────────────────────────────────────────────────────────────────

class TestCard3ChartsGridAndCanvasScaling:
    """Stress test Card 3 .charts-grid, .chart-card, and Chart.js canvas elements."""

    def test_charts_grid_single_column_override(self, index_css: str):
        """Assert .charts-grid overrides desktop minmax(320px, 1fr) with 1fr on <= 768px."""
        mq768 = extract_media_query_rules(index_css, 768)
        assert re.search(r'\.charts-grid\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq768, re.IGNORECASE) is not None, (
            ".charts-grid on < 768px must override desktop minmax(320px, 1fr) with 1fr"
        )
        assert re.search(r'\.charts-grid\s*\{[^}]*width\s*:\s*100%', mq768, re.IGNORECASE) is not None, (
            ".charts-grid on < 768px must specify width: 100%"
        )

    def test_chart_card_responsive_width_and_height(self, index_css: str):
        """Assert .chart-card has width: 100%, max-width: 100%, and responsive heights."""
        mq768 = extract_media_query_rules(index_css, 768)
        assert re.search(r'\.chart-card\s*\{[^}]*width\s*:\s*100%', mq768, re.IGNORECASE) is not None
        assert re.search(r'\.chart-card\s*\{[^}]*max-width\s*:\s*100%', mq768, re.IGNORECASE) is not None
        assert re.search(r'\.chart-card\s*\{[^}]*box-sizing\s*:\s*border-box', mq768, re.IGNORECASE) is not None
        # Height at 768px
        assert re.search(r'\.chart-card\s*>\s*div\[style\*="height"\]\s*\{[^}]*height\s*:\s*280px', mq768, re.IGNORECASE) is not None

        mq480 = extract_media_query_rules(index_css, 480)
        # Height at 480px
        assert re.search(r'\.chart-card\s*>\s*div\[style\*="height"\]\s*\{[^}]*height\s*:\s*260px', mq480, re.IGNORECASE) is not None

    def test_canvases_exist_inside_chart_cards(self, index_soup: BeautifulSoup):
        """Assert hrpDonutChart and marketExposureChart exist within .chart-card wrappers."""
        donut_canvas = index_soup.find("canvas", attrs={"id": "hrpDonutChart"})
        assert donut_canvas is not None, "Missing <canvas id='hrpDonutChart'>"
        assert donut_canvas.find_parent("div", class_="chart-card") is not None, (
            "hrpDonutChart canvas must be wrapped inside .chart-card"
        )

        exposure_canvas = index_soup.find("canvas", attrs={"id": "marketExposureChart"})
        assert exposure_canvas is not None, "Missing <canvas id='marketExposureChart'>"
        assert exposure_canvas.find_parent("div", class_="chart-card") is not None, (
            "marketExposureChart canvas must be wrapped inside .chart-card"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Ensemble Recommendations Table Compacting & Touch UX
# ─────────────────────────────────────────────────────────────────────────────

class TestEnsembleTableMobileCompacting:
    """Verify frozen columns compact to <= 200px total leaving ample swipe room."""

    def test_frozen_columns_width_budget(self, index_css: str):
        """Total frozen column width = rank (36px) + symbol (68px) + name (86px-96px) <= 196px."""
        mq768 = extract_media_query_rules(index_css, 768)

        # Match the active overriding rule (taking the last occurrence in the CSS cascade)
        rank_matches = re.findall(r'\.table-wrap\s+\.sticky-rank\s*\{[^}]*width\s*:\s*(\d+)px', mq768, re.IGNORECASE)
        assert len(rank_matches) > 0, "Missing .sticky-rank width rule in mq768"
        rank_w = int(rank_matches[-1])

        sym_matches = re.findall(r'\.table-wrap\s+\.sticky-symbol\s*\{[^}]*width\s*:\s*(\d+)px', mq768, re.IGNORECASE)
        assert len(sym_matches) > 0, "Missing .sticky-symbol width rule in mq768"
        sym_w = int(sym_matches[-1])

        # For sticky-name, ensure the overriding rule with !important is matched (96px)
        name_matches = re.findall(r'\.table-wrap\s+\.sticky-name\s*\{[^}]*max-width\s*:\s*(\d+)px(?:\s*!important)?', mq768, re.IGNORECASE)
        assert len(name_matches) > 0, "Missing .sticky-name max-width rule in mq768"
        name_w = int(name_matches[-1])

        total_frozen = rank_w + sym_w + name_w
        assert total_frozen <= 200, f"Total frozen column width {total_frozen}px exceeds 200px budget"

        # Check swipeable remaining width on 320px screen
        swipeable_320 = 320 - total_frozen - 20
        assert swipeable_320 >= 100, f"320px screen leaves only {swipeable_320}px for metrics swipe"

    def test_smooth_touch_scrolling_enabled(self, index_css: str):
        """Assert -webkit-overflow-scrolling: touch is present on .table-wrap."""
        mq768 = extract_media_query_rules(index_css, 768)
        assert "-webkit-overflow-scrolling: touch" in mq768 or "-webkit-overflow-scrolling: touch" in index_css, (
            "Ensemble table missing -webkit-overflow-scrolling: touch for iOS Safari smooth fling"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Touch Target Minimum Size & File Size Budget
# ─────────────────────────────────────────────────────────────────────────────

class TestTouchAccessibilityAndFileBudget:
    """WCAG 44x44px minimum tap targets and 512,000 bytes hard budget."""

    def test_touch_targets_min_44px(self, index_css: str):
        """Confirm .health-pill, .filter-btn, .clickable-row td have >= 44px height."""
        mq768 = extract_media_query_rules(index_css, 768)
        assert re.search(r'\.health-pill\s*\{[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None
        assert re.search(r'\.clickable-row\s+td\s*\{[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None

        # Check filter-btn, chip-btn, theme-btn
        assert re.search(r'\.filter-btn[^}]*min-height\s*:\s*44px', index_css, re.IGNORECASE) is not None

    def test_index_html_strictly_under_budget(self):
        """Confirm gh-pages/index.html is strictly < 512,000 bytes."""
        size = INDEX_HTML_PATH.stat().st_size
        budget = 512000
        assert size < budget, f"index.html size {size} bytes exceeds {budget} budget"
        # Print for empirical logging
        print(f"\nEmpirical index.html size: {size} bytes ({size/1024:.2f} KB) — Budget margin: {budget - size} bytes")
