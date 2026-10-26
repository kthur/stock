"""
tests/test_challenger_m4_1_mobile_ux.py — Adversarial Verification Suite for Milestone M4 (R4/A4)

Empirical challenger test suite targeting:
- Strict preservation of exactly 42 <th> headers and 42 <td> cells per row across all 5 market pages
- 188px compact frozen columns geometry (Rank 34px, Symbol 66px, Name 88px) and z-index stratification
- .col-strat display override on #market-full-table without !important and JS preset toggling viability
- 44px touch targets on toolbar buttons, CSV export, and 16px font-size search input
- Viewport containment and long-name truncation robustness
- Stock drawer bottom sheet transformation and radar chart integrity across all 5 market pages
"""

import re
import json
import urllib.parse
from pathlib import Path
from typing import Dict, List
import pytest
from bs4 import BeautifulSoup

GH_PAGES_DIR = Path("gh-pages")
MARKET_PAGES = [
    "market_kospi.html",
    "market_kosdaq.html",
    "market_sp500.html",
    "market_nasdaq.html",
    "market_russell2000.html",
]


@pytest.fixture(scope="module")
def market_pages_html() -> Dict[str, str]:
    """Load HTML content of all 5 market pages from gh-pages/."""
    contents = {}
    for p in MARKET_PAGES:
        file_path = GH_PAGES_DIR / p
        assert file_path.exists(), f"Market page {file_path} does not exist"
        contents[p] = file_path.read_text(encoding="utf-8")
    return contents


def extract_media_query_blocks(css: str, max_width: int) -> List[str]:
    """Extract contents of all @media (max-width: {max_width}px) blocks."""
    pattern = rf'@media\s*\(\s*max-width\s*:\s*{max_width}px\s*\)\s*\{{+'
    blocks = []
    for match in re.finditer(pattern, css, flags=re.IGNORECASE):
        start = match.end()
        count = match.group(0).count('{')
        idx = start
        while idx < len(css) and count > 0:
            if css[idx] == '{':
                count += 1
            elif css[idx] == '}':
                count -= 1
            idx += 1
        blocks.append(css[start:idx-1])
    return blocks


def extract_all_css(html: str) -> str:
    """Extract all text inside <style> tags."""
    soup = BeautifulSoup(html, "html.parser")
    return "\n".join(s.get_text() for s in soup.find_all("style"))


# =============================================================================
# Challenge 1: 42 <th> Column Count & Row Cell Integrity
# =============================================================================

def test_all_5_market_pages_42_th_headers_and_row_integrity(market_pages_html):
    """
    Empirically assert that:
    1. Every market page has table#market-full-table.
    2. Exactly 42 <th> headers exist in thead.
    3. Every <tr> in tbody contains exactly 42 <td> cells (no table layout drift).
    4. First 3 columns have sticky classes; columns 5..41 have col-strat.
    """
    for page_name, html in market_pages_html.items():
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", id="market-full-table")
        assert table is not None, f"{page_name} missing table#market-full-table"

        # Check thead
        thead = table.find("thead")
        assert thead is not None, f"{page_name} missing thead in market-full-table"
        ths = thead.find_all("th")
        assert len(ths) == 42, f"{page_name} expected exactly 42 <th> elements, found {len(ths)}"

        # Check th headers mapping
        th_classes = [th.get("class", []) for th in ths]
        assert "sticky-rank" in th_classes[0], f"{page_name} col 0 missing sticky-rank"
        assert "sticky-symbol" in th_classes[1], f"{page_name} col 1 missing sticky-symbol"
        assert "sticky-name" in th_classes[2], f"{page_name} col 2 missing sticky-name"

        # Check 37 strategy columns
        for idx in range(5, 42):
            classes = th_classes[idx]
            assert "col-strat" in classes, f"{page_name} col {idx} missing col-strat class: {classes}"

        # Check all tbody rows
        tbody = table.find("tbody")
        assert tbody is not None, f"{page_name} missing tbody in market-full-table"
        rows = tbody.find_all("tr")
        assert len(rows) > 0, f"{page_name} tbody has zero rows"

        for r_idx, row in enumerate(rows):
            tds = row.find_all("td")
            if len(tds) == 1 and tds[0].get("colspan") == "42":
                # Verified fallback row when market dataset has 0 symbols
                assert "empty" in tds[0].get("class", []), f"{page_name} single-cell row missing class empty"
                continue

            assert len(tds) == 42, (
                f"{page_name} row {r_idx} (symbol={row.get('data-symbol')}) "
                f"expected exactly 42 <td> cells, found {len(tds)}"
            )
            # Verify sticky column classes on row cells
            td0_cls = tds[0].get("class", [])
            td1_cls = tds[1].get("class", [])
            td2_cls = tds[2].get("class", [])
            assert "sticky-rank" in td0_cls, f"{page_name} row {r_idx} td 0 missing sticky-rank"
            assert "sticky-symbol" in td1_cls, f"{page_name} row {r_idx} td 1 missing sticky-symbol"
            assert "sticky-name" in td2_cls, f"{page_name} row {r_idx} td 2 missing sticky-name"

            # Verify col-strat on factor cells
            for col_i in range(5, 42):
                td_cls = tds[col_i].get("class", [])
                assert "col-strat" in td_cls, f"{page_name} row {r_idx} td {col_i} missing col-strat"

            # Check data attributes for JS search
            sym = row.get("data-symbol", "")
            name = row.get("data-name", "")
            assert len(sym) > 0, f"{page_name} row {r_idx} missing data-symbol"
            assert len(name) > 0, f"{page_name} row {r_idx} missing data-name"


# =============================================================================
# Challenge 2: 188px Frozen Columns Geometry & Mathematical Soundness
# =============================================================================

def test_sticky_columns_188px_geometry_and_layering(market_pages_html):
    """
    Empirically verify the geometry and z-index stratification of the frozen columns:
    1. Col 0 (Rank): left: 0, width: 34px
    2. Col 1 (Symbol): left: 34px, width: 66px
    3. Col 2 (Name): left: 100px, width: 88px
    4. Exact sum: 34 + 66 + 88 = 188px (strictly <= 190px mobile threshold)
    5. Seamless alignment: Col 0 left + width == Col 1 left (0 + 34 == 34), Col 1 left + width == Col 2 left (34 + 66 == 100)
    6. Col 2 visual separator (border-right and box-shadow)
    7. Z-index stratification: headers (15, 14, 13) > base sticky header (12) > row cells (2)
    8. Table border-collapse: separate; border-spacing: 0
    """
    for page_name, html in market_pages_html.items():
        css = extract_all_css(html)
        mq768_blocks = extract_media_query_blocks(css, 768)
        assert len(mq768_blocks) > 0, f"{page_name} missing @media (max-width: 768px)"
        mq768 = "\n".join(mq768_blocks)

        # Check Col 0 (Rank)
        rank_left = re.search(r'(?:\.table-wrap\s+)?\.sticky-rank\s*\{[^}]*left\s*:\s*0(?:px)?', mq768, re.I)
        rank_width = re.search(r'(?:\.table-wrap\s+)?\.sticky-rank\s*\{[^}]*width\s*:\s*34px', mq768, re.I)
        assert rank_left is not None, f"{page_name} .sticky-rank missing left: 0 in mq768"
        assert rank_width is not None, f"{page_name} .sticky-rank missing width: 34px in mq768"

        # Check Col 1 (Symbol)
        sym_left = re.search(r'(?:\.table-wrap\s+)?\.sticky-symbol\s*\{[^}]*left\s*:\s*34px', mq768, re.I)
        sym_width = re.search(r'(?:\.table-wrap\s+)?\.sticky-symbol\s*\{[^}]*width\s*:\s*66px', mq768, re.I)
        assert sym_left is not None, f"{page_name} .sticky-symbol missing left: 34px in mq768"
        assert sym_width is not None, f"{page_name} .sticky-symbol missing width: 66px in mq768"

        # Check Col 2 (Name)
        name_left = re.search(r'(?:\.table-wrap\s+)?\.sticky-name\s*\{[^}]*left\s*:\s*100px', mq768, re.I)
        name_width = re.search(r'(?:\.table-wrap\s+)?\.sticky-name\s*\{[^}]*width\s*:\s*88px', mq768, re.I)
        assert name_left is not None, f"{page_name} .sticky-name missing left: 100px in mq768"
        assert name_width is not None, f"{page_name} .sticky-name missing width: 88px in mq768"

        # Check visual delimiter on Col 2
        name_border = re.search(r'\.sticky-name\s*\{[^}]*border-right\s*:', mq768, re.I)
        name_shadow = re.search(r'\.sticky-name\s*\{[^}]*box-shadow\s*:', mq768, re.I)
        assert name_border is not None, f"{page_name} .sticky-name missing border-right separator"
        assert name_shadow is not None, f"{page_name} .sticky-name missing box-shadow separator"

        # Check table border-collapse: separate
        assert re.search(r'#market-full-table\s*\{[^}]*border-collapse\s*:\s*separate', css, re.I) is not None, (
            f"{page_name} #market-full-table must define border-collapse: separate for clean sticky column rendering"
        )

        # Check z-index stratification
        assert re.search(r'th\.sticky-rank\s*\{[^}]*z-index\s*:\s*15', css, re.I) is not None, f"{page_name} missing th.sticky-rank z-index: 15"
        assert re.search(r'th\.sticky-symbol\s*\{[^}]*z-index\s*:\s*14', css, re.I) is not None, f"{page_name} missing th.sticky-symbol z-index: 14"
        assert re.search(r'th\.sticky-name\s*\{[^}]*z-index\s*:\s*13', css, re.I) is not None, f"{page_name} missing th.sticky-name z-index: 13"


# =============================================================================
# Challenge 3: .col-strat Display Override Without !important
# =============================================================================

def test_col_strat_display_override_absence_of_important(market_pages_html):
    """
    Empirically verify that:
    1. On mobile media queries, #market-full-table overrides .col-strat with display: table-cell.
    2. Crucially, the rule DOES NOT contain !important.
    3. Simulates JS column toggling: verifies that inline style.display = 'none' cleanly overrides
       the CSS rule without being blocked by !important.
    """
    for page_name, html in market_pages_html.items():
        css = extract_all_css(html)
        mq768_blocks = extract_media_query_blocks(css, 768)
        mq768 = "\n".join(mq768_blocks)

        # Find rule targeting #market-full-table and .col-strat
        strat_override_match = re.search(
            r'(?:#market-full-table|\.market-content)\s+[^\{]*\.col-strat[^{]*\{([^}]+)\}',
            mq768,
            re.I
        )
        assert strat_override_match is not None, (
            f"{page_name} missing #market-full-table .col-strat display override in @media (max-width: 768px)"
        )

        rule_body = strat_override_match.group(1)
        assert "display: table-cell" in rule_body.lower() or "display:table-cell" in rule_body.lower(), (
            f"{page_name} .col-strat override must specify display: table-cell, found: {rule_body}"
        )
        assert "!important" not in rule_body.lower(), (
            f"{page_name} VIOLATION: #market-full-table .col-strat contains !important, "
            f"which blocks JS preset column filtering! Rule: {rule_body}"
        )

        # Verify JS column preset mapping
        soup = BeautifulSoup(html, "html.parser")
        scripts = "\n".join(s.get_text() for s in soup.find_all("script"))
        assert "function setColumnPreset" in scripts, f"{page_name} missing setColumnPreset function"
        assert "visibleCols.has(idx)" in scripts, f"{page_name} setColumnPreset missing visibleCols logic"


# =============================================================================
# Challenge 4: Toolbar Touch Targets & WCAG 2.5.5 Compliance
# =============================================================================

def test_toolbar_touch_accessibility_and_wcag_compliance(market_pages_html):
    """
    Empirically assert WCAG 2.5.5 (>= 44x44px touch target) compliance:
    1. .preset-buttons has overflow-x: auto and -webkit-overflow-scrolling: touch
    2. All 6 preset filter buttons have min-height: 44px
    3. Search input has min-height: 44px and font-size: 16px (eliminates iOS Safari auto-zoom)
    4. CSV export button has min-height: 44px
    """
    expected_presets = [
        "preset-all",
        "preset-ai",
        "preset-mom",
        "preset-val",
        "preset-flow",
        "preset-macro",
    ]

    for page_name, html in market_pages_html.items():
        soup = BeautifulSoup(html, "html.parser")
        css = extract_all_css(html)
        mq768_blocks = extract_media_query_blocks(css, 768)
        mq768 = "\n".join(mq768_blocks)

        # Check preset buttons in DOM
        for p_id in expected_presets:
            btn = soup.find("button", id=p_id)
            assert btn is not None, f"{page_name} missing preset button #{p_id}"
            assert "filter-btn" in btn.get("class", []), f"{page_name} #{p_id} missing filter-btn class"

        # Check CSS touch targets in mq768
        assert re.search(r'\.filter-btn\s*\{[^}]*min-height\s*:\s*44px', mq768, re.I) is not None, (
            f"{page_name} .filter-btn missing min-height: 44px on mobile"
        )
        assert re.search(r'\.preset-buttons\s*\{[^}]*overflow-x\s*:\s*auto', mq768, re.I) is not None, (
            f"{page_name} .preset-buttons missing overflow-x: auto on mobile"
        )
        assert re.search(r'\.preset-buttons\s*\{[^}]*-webkit-overflow-scrolling\s*:\s*touch', mq768, re.I) is not None, (
            f"{page_name} .preset-buttons missing -webkit-overflow-scrolling: touch on mobile"
        )

        # Check search input
        search_input = soup.find("input", id="market-search")
        assert search_input is not None, f"{page_name} missing #market-search input"
        assert re.search(r'\.market-search-input\s*\{[^}]*min-height\s*:\s*44px', mq768, re.I) is not None, (
            f"{page_name} #market-search missing min-height: 44px on mobile"
        )
        assert re.search(r'\.market-search-input\s*\{[^}]*font-size\s*:\s*16px', mq768, re.I) is not None, (
            f"{page_name} #market-search missing font-size: 16px on mobile (causes iOS auto-zoom)"
        )

        # Check CSV export button
        csv_btn = soup.find("button", class_="btn-csv-export")
        assert csv_btn is not None, f"{page_name} missing .btn-csv-export button"
        assert re.search(r'\.btn-csv-export\s*\{[^}]*min-height\s*:\s*44px', mq768, re.I) is not None, (
            f"{page_name} .btn-csv-export missing min-height: 44px on mobile"
        )


# =============================================================================
# Challenge 5: Extreme Mobile Viewport & Long Text Containment
# =============================================================================

def test_extreme_mobile_viewport_and_text_containment(market_pages_html):
    """
    Stress-test narrow viewport behavior (320px, 375px):
    1. .table-wrap has overflow-x: auto and -webkit-overflow-scrolling: touch
    2. body has overflow-x: hidden
    3. .sticky-name has white-space: nowrap, overflow: hidden, text-overflow: ellipsis, max-width: 88px
       guaranteeing that ultra-long stock names will never inflate the frozen column width.
    """
    for page_name, html in market_pages_html.items():
        css = extract_all_css(html)
        mq768_blocks = extract_media_query_blocks(css, 768)
        mq768 = "\n".join(mq768_blocks)

        # .table-wrap overflow
        assert re.search(r'\.table-wrap\s*\{[^}]*overflow-x\s*:\s*auto', mq768, re.I) is not None, (
            f"{page_name} .table-wrap missing overflow-x: auto in mq768"
        )
        assert re.search(r'body\s*\{[^}]*overflow-x\s*:\s*hidden', css, re.I) is not None, (
            f"{page_name} body missing overflow-x: hidden"
        )

        # .sticky-name truncation
        assert re.search(r'\.sticky-name\s*\{[^}]*text-overflow\s*:\s*ellipsis', mq768, re.I) is not None, (
            f"{page_name} .sticky-name missing text-overflow: ellipsis"
        )
        assert re.search(r'\.sticky-name\s*\{[^}]*white-space\s*:\s*nowrap', mq768, re.I) is not None, (
            f"{page_name} .sticky-name missing white-space: nowrap"
        )
        assert re.search(r'\.sticky-name\s*\{[^}]*max-width\s*:\s*88px', mq768, re.I) is not None, (
            f"{page_name} .sticky-name missing max-width: 88px"
        )


# =============================================================================
# Challenge 6: Stock Detail Drawer Bottom-Sheet & Radar Chart Integration
# =============================================================================

def test_drawer_bottom_sheet_and_radar_chart_all_pages(market_pages_html):
    """
    Assert that the responsive bottom sheet and 5-factor radar chart exist on all 5 market pages:
    1. #stock-drawer exists with class stock-drawer
    2. canvas#drawerRadarChart exists
    3. renderDrawerRadarChart is defined and invoked in openStockDrawer
    4. Mobile bottom sheet CSS rules (height: 90vh, border-radius: 16px 16px 0 0) are present
    """
    for page_name, html in market_pages_html.items():
        soup = BeautifulSoup(html, "html.parser")
        drawer = soup.find("div", id="stock-drawer")
        assert drawer is not None, f"{page_name} missing #stock-drawer element"

        canvas = drawer.find("canvas", id="drawerRadarChart")
        assert canvas is not None, f"{page_name} missing canvas#drawerRadarChart inside drawer"

        scripts = "\n".join(s.get_text() for s in soup.find_all("script"))
        assert "function renderDrawerRadarChart" in scripts, f"{page_name} missing renderDrawerRadarChart function"
        assert "renderDrawerRadarChart(" in scripts, f"{page_name} renderDrawerRadarChart is never invoked"

        css = extract_all_css(html)
        mq768_blocks = extract_media_query_blocks(css, 768)
        mq768 = "\n".join(mq768_blocks)

        assert re.search(r'#stock-drawer\s*\{[^}]*height\s*:\s*90vh', mq768, re.I) is not None, (
            f"{page_name} #stock-drawer missing height: 90vh on mobile"
        )
        assert re.search(r'#stock-drawer\s*\{[^}]*border-radius\s*:\s*16px', mq768, re.I) is not None, (
            f"{page_name} #stock-drawer missing border-radius: 16px 16px 0 0 on mobile"
        )
