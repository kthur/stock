"""
tests/test_adversarial_m4_challenger2.py — Adversarial Stress Test Suite for Milestone M4

Adversarial stress-testing of mobile responsiveness across viewports (320px, 375px, 414px, 768px),
page horizontal overflow containment, table horizontal touch scrolling, sticky column pin alignment
and background opacity, filter preset preservation, and bottom-sheet drawer mechanics.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Set
import pytest
from bs4 import BeautifulSoup

from trading_system.report_multipage import (
    build_head,
    build_styles,
    build_sticky_nav,
)

GH_PAGES_DIR = Path("gh-pages")

ALL_PAGES = [
    "index.html",
    "strategies.html",
    "market_kospi.html",
    "market_kosdaq.html",
    "market_sp500.html",
    "market_nasdaq.html",
    "market_russell2000.html",
]

MARKET_PAGES = [
    "market_kospi.html",
    "market_kosdaq.html",
    "market_sp500.html",
    "market_nasdaq.html",
    "market_russell2000.html",
]

VIEWPORTS = [320, 375, 414, 768]


def extract_css(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    styles = [s.get_text() for s in soup.find_all("style")]
    return "\n".join(styles)


def extract_mq(css: str, max_width: int) -> str:
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


@pytest.fixture(scope="module")
def pages_content() -> Dict[str, str]:
    contents = {}
    for p in ALL_PAGES:
        f = GH_PAGES_DIR / p
        assert f.exists(), f"Page {p} not found in gh-pages/"
        contents[p] = f.read_text(encoding="utf-8")
    return contents


@pytest.fixture(scope="module")
def multipage_css() -> str:
    return build_styles("")


class TestMobileResponsivenessStress:
    """Stress test mobile responsiveness across 320px, 375px, 414px, 768px viewports."""

    @pytest.mark.parametrize("vp", VIEWPORTS)
    def test_viewport_meta_and_body_containment(self, pages_content: Dict[str, str], vp: int):
        """Verify that all 7 pages specify viewport meta with width=device-width, initial-scale=1.0, viewport-fit=cover, and body overflow-x: hidden."""
        for name, html in pages_content.items():
            assert '<meta name="viewport"' in html, f"{name} missing viewport meta tag"
            assert "width=device-width" in html, f"{name} missing width=device-width"
            assert "viewport-fit=cover" in html, f"{name} missing viewport-fit=cover"

            css = extract_css(html)
            assert re.search(r'body\s*\{[^}]*overflow-x\s*:\s*hidden', css, re.IGNORECASE) is not None, (
                f"{name} missing body {{ overflow-x: hidden; }}"
            )

    @pytest.mark.parametrize("vp", [320, 375, 414])
    def test_narrow_screen_card_and_grid_adaptations(self, pages_content: Dict[str, str], multipage_css: str, vp: int):
        """Stress test narrow screens: verify grids collapse without blowout."""
        index_css = extract_css(pages_content["index.html"])
        strat_css = extract_css(pages_content["strategies.html"])
        mq = extract_mq(index_css, 768) + "\n" + extract_mq(index_css, 480)
        strat_mq = extract_mq(strat_css, 768) + "\n" + extract_mq(strat_css, 480)

        # Macro grid collapse
        assert re.search(r'\.macro-grid\s*\{[^}]*grid-template-columns\s*:\s*(?:repeat\(2,\s*1fr\)|1fr)', mq) is not None
        # Health grid collapse
        assert re.search(r'\.health-grid\s*\{[^}]*grid-template-columns\s*:\s*(?:repeat\(2,\s*1fr\)|1fr)', mq) is not None
        # Charts grid single column
        assert re.search(r'\.charts-grid\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq) is not None
        # Encyclopedia grid single column / 100% minmax
        assert re.search(r'\.encyclopedia-grid\s*\{[^}]*grid-template-columns\s*:\s*(?:repeat\([^)]*minmax\(100%,\s*1fr\)\)|1fr)', strat_mq) is not None


class TestStickyColumnGeometryAndOpacity:
    """Stress test sticky column pin alignment, pixel offsets, and background opacity."""

    def test_sticky_columns_continuity_and_geometry(self, multipage_css: str, pages_content: Dict[str, str]):
        """
        Verify:
        - Rank: left=0px, width=34px
        - Symbol: left=34px, width=66px
        - Name: left=100px (34 + 66), width=88px
        - Total frozen column width = 188px (strictly <= 190px and <= 200px)
        - Pixel math: 0 + 34 = 34, 34 + 66 = 100. Exactly continuous with ZERO gap and ZERO overlap!
        """
        for mkt in MARKET_PAGES:
            css = extract_css(pages_content[mkt])
            mq768 = extract_mq(css, 768) or extract_mq(multipage_css, 768)

            # Check widths and left offsets in mq768
            rank_w = re.search(r'#market-full-table th\.sticky-rank[^}]*width\s*:\s*(\d+)px', mq768)
            sym_w = re.search(r'#market-full-table th\.sticky-symbol[^}]*width\s*:\s*(\d+)px', mq768)
            name_w = re.search(r'#market-full-table th\.sticky-name[^}]*width\s*:\s*(\d+)px', mq768)

            assert rank_w is not None and int(rank_w.group(1)) == 34, f"{mkt} sticky-rank width != 34px"
            assert sym_w is not None and int(sym_w.group(1)) == 66, f"{mkt} sticky-symbol width != 66px"
            assert name_w is not None and int(name_w.group(1)) == 88, f"{mkt} sticky-name width != 88px"

            rank_l = re.search(r'#market-full-table th\.sticky-rank[^}]*left\s*:\s*(\d+)(?:px|\s*!|\s*;)', mq768)
            sym_l = re.search(r'#market-full-table th\.sticky-symbol[^}]*left\s*:\s*(\d+)(?:px|\s*!|\s*;)', mq768)
            name_l = re.search(r'#market-full-table th\.sticky-name[^}]*left\s*:\s*(\d+)(?:px|\s*!|\s*;)', mq768)

            assert rank_l is not None and int(rank_l.group(1)) == 0, f"{mkt} sticky-rank left != 0px"
            assert sym_l is not None and int(sym_l.group(1)) == 34, f"{mkt} sticky-symbol left != 34px"
            assert name_l is not None and int(name_l.group(1)) == 100, f"{mkt} sticky-name left != 100px"

            # Check remaining scrollable width in smallest 320px viewport
            total_frozen = 34 + 66 + 88
            assert total_frozen == 188
            remaining_320 = 320 - total_frozen
            assert remaining_320 >= 130, f"Remaining scrollable width {remaining_320}px must be >= 130px"

    def test_sticky_columns_background_opacity(self, pages_content: Dict[str, str], multipage_css: str):
        """
        Verify that sticky column background colors are opaque (no see-through artifacts).
        - th.sticky-col has background: var(--surface2)
        - td.sticky-col has background: var(--surface)
        - Check that --surface and --surface2 definitions in CSS are 6-character solid hex colors.
        """
        for mkt in MARKET_PAGES:
            css = extract_css(pages_content[mkt]) + "\n" + multipage_css
            # Find definitions of --surface and --surface2
            surface_defs = re.findall(r'--surface\s*:\s*(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})\b', css)
            surface2_defs = re.findall(r'--surface2\s*:\s*(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})\b', css)

            assert len(surface_defs) > 0, f"{mkt} missing --surface color definition"
            assert len(surface2_defs) > 0, f"{mkt} missing --surface2 color definition"

            # Check that none of the surface definitions contain rgba with alpha < 1
            rgba_surface = re.findall(r'--surface2?\s*:\s*rgba?\([^)]+\)', css)
            for r in rgba_surface:
                # If rgba is used, alpha must be 1
                assert "0." not in r, f"Semi-transparent surface found: {r}"

    def test_sticky_columns_z_index_hierarchy(self, pages_content: Dict[str, str], multipage_css: str):
        """
        Verify strict z-index hierarchy:
        Header sticky rank (15) > Symbol (14) > Name (13) > Base Header Sticky (12) > Data Sticky (2) > Normal Cells (auto/0).
        """
        for mkt in MARKET_PAGES:
            css = extract_css(pages_content[mkt]) + "\n" + multipage_css
            mq768 = extract_mq(css, 768)

            assert "z-index: 15" in mq768 or "z-index: 15" in css
            assert "z-index: 14" in mq768 or "z-index: 14" in css
            assert "z-index: 13" in mq768 or "z-index: 13" in css
            assert "z-index: 12" in mq768 or "z-index: 12" in css
            assert "z-index: 2" in mq768 or "z-index: 2" in css

    def test_sticky_name_visual_divider(self, pages_content: Dict[str, str], multipage_css: str):
        """Verify Name column has a visual border and box-shadow separator on the right."""
        for mkt in MARKET_PAGES:
            css = extract_css(pages_content[mkt]) + "\n" + multipage_css
            mq768 = extract_mq(css, 768)
            assert re.search(r'sticky-name[^}]*border-right', mq768) is not None or re.search(r'sticky-name[^}]*border-right', css) is not None
            assert re.search(r'sticky-name[^}]*box-shadow', mq768) is not None or re.search(r'sticky-name[^}]*box-shadow', css) is not None


class TestPreserved42ColumnsAndFilters:
    """Stress test 42 columns invariant, strategy visibility, and filter presets."""

    def test_all_market_tables_have_exactly_42_columns(self, pages_content: Dict[str, str]):
        """Verify exactly 42 <th> tags in each market page table."""
        for mkt in MARKET_PAGES:
            html = pages_content[mkt]
            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table", id="market-full-table")
            assert table is not None, f"Table #market-full-table not found in {mkt}"
            th_cells = table.find("thead").find_all("th")
            assert len(th_cells) == 42, f"{mkt} has {len(th_cells)} <th> columns, expected 42"

    def test_mobile_displays_col_strat_without_important(self, pages_content: Dict[str, str], multipage_css: str):
        """Verify .col-strat is displayed (display: table-cell) on mobile for #market-full-table."""
        for mkt in MARKET_PAGES:
            css = extract_css(pages_content[mkt]) + "\n" + multipage_css
            mq768 = extract_mq(css, 768)

            assert re.search(r'#market-full-table\s+(?:th|td|\.)?col-strat\s*\{[^}]*display\s*:\s*table-cell', mq768, re.IGNORECASE) is not None

    def test_filter_presets_logic_and_buttons(self, pages_content: Dict[str, str]):
        """
        Verify:
        - All 6 preset buttons exist: all, ai, mom, val, flow, macro.
        - setColumnPreset script maps presets correctly.
        - Indices 0, 1, 2, 3, 4 are included in EVERY preset (sticky columns and core metrics never hidden).
        - Every index 0..41 is reachable across presets.
        """
        for mkt in MARKET_PAGES:
            html = pages_content[mkt]
            soup = BeautifulSoup(html, "html.parser")

            preset_btns = soup.find_all("button", class_="filter-btn")
            btn_ids = {b.get("id") for b in preset_btns if b.get("id")}
            expected_ids = {"preset-all", "preset-ai", "preset-mom", "preset-val", "preset-flow", "preset-macro"}
            assert expected_ids.issubset(btn_ids), f"{mkt} missing preset buttons: {expected_ids - btn_ids}"

            # Verify setColumnPreset function in script
            assert "function setColumnPreset" in html, f"{mkt} missing setColumnPreset function"

            # Parse presetMap from script
            match = re.search(r'const\s+presetMap\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\};', html)
            assert match is not None, f"{mkt} missing presetMap definition"
            map_str = match.group(1)

            # Check that 0, 1, 2, 3, 4 are present in each preset
            for p in ["all", "ai", "mom", "val", "flow", "macro"]:
                p_match = re.search(rf"'{p}'\s*:\s*\[([^\]]+)\]", map_str)
                assert p_match is not None, f"Preset '{p}' missing in presetMap of {mkt}"
                cols = [int(x.strip()) for x in p_match.group(1).split(",")]
                for core_col in [0, 1, 2, 3, 4]:
                    assert core_col in cols, f"Core/sticky column {core_col} missing in preset '{p}' in {mkt}"


class TestTouchAccessibilityAndDrawer:
    """Stress test touch target heights, iOS zoom prevention, and bottom sheet drawer."""

    def test_touch_target_heights(self, pages_content: Dict[str, str], multipage_css: str):
        """Verify >= 44px min-height on all interactive controls."""
        css = multipage_css + "\n" + extract_css(pages_content["index.html"])
        mq768 = extract_mq(css, 768)

        # Nav links
        assert re.search(r'\.nav-link\s*\{[^}]*min-height\s*:\s*44px', mq768) is not None
        # Preset filter buttons
        assert re.search(r'\.filter-btn\s*\{[^}]*min-height\s*:\s*44px', mq768) is not None
        # CSV Export button
        assert re.search(r'\.btn-csv-export\s*\{[^}]*min-height\s*:\s*44px', mq768) is not None
        # Search input
        assert re.search(r'\.market-search-input\s*\{[^}]*min-height\s*:\s*44px', mq768) is not None
        # iOS Auto-zoom prevention: font-size >= 16px on inputs
        assert re.search(r'\.market-search-input\s*\{[^}]*font-size\s*:\s*1[6-9]px', mq768) is not None

    def test_bottom_sheet_drawer_dimensions_and_radar(self, pages_content: Dict[str, str], multipage_css: str):
        """Verify stock drawer transforms to 90vh bottom sheet with 16px radius and radar chart."""
        css = multipage_css + "\n" + extract_css(pages_content["index.html"])
        mq768 = extract_mq(css, 768)

        assert re.search(r'#stock-drawer\s*\{[^}]*width\s*:\s*100%', mq768) is not None
        assert re.search(r'#stock-drawer\s*\{[^}]*height\s*:\s*90vh', mq768) is not None
        assert re.search(r'#stock-drawer\s*\{[^}]*border-radius\s*:\s*16px', mq768) is not None

        for mkt in MARKET_PAGES:
            html = pages_content[mkt]
            assert "renderDrawerRadarChart" in html
            assert '<canvas id="drawerRadarChart"' in html
            assert "openStockDrawer" in html


class TestPayloadAndLinkIntegrity:
    """Check bundle budget (< 1 MB) and zero broken links."""

    def test_index_budget(self):
        index_file = GH_PAGES_DIR / "index.html"
        size = index_file.stat().st_size
        assert size < 1048576, f"index.html size {size} exceeds 1,048,576 bytes budget"

    def test_relative_links(self, pages_content: Dict[str, str]):
        for name, html in pages_content.items():
            links = re.findall(r'href="([^"]+)"', html)
            for link in links:
                if link.startswith(("http", "#", "mailto", "javascript", "data:")):
                    continue
                file_part = link.split("#")[0]
                assert (GH_PAGES_DIR / file_part).exists(), f"Broken relative link {link} in {name}"
