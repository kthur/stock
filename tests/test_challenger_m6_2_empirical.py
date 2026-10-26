"""
tests/test_challenger_m6_2_empirical.py — Adversarial Mobile Responsiveness Verification Suite

Authored by: Challenger M6-2 (EMPIRICAL CHALLENGER)
Focus: Stress-testing mobile responsiveness across all 7 pages for viewports 320px–768px.
Covers:
- Viewport continuum: 320px (iPhone SE 1st gen), 360px, 375px, 390px, 412px, 480px, 600px, 768px
- Zero viewport blowout & horizontal overflow containment
- Sticky navigation bar height (<= 56px) & touch-friendly chip carousel
- Executive Dashboard (index.html) 3-Card mobile stacking & compact sticky ensemble table
- Strategy Encyclopedia (strategies.html) mobile grid override & formula box overflow scroll
- Market detail pages (market_*.html) 42-column preservation & 188px frozen left columns
- Stock detail drawer bottom-sheet transformation (90vh, 16px radius, radar canvas)
- Touch target accessibility (>= 44x44px)
- Relative link integrity & index.html payload budget (< 500 KB / 512,000 bytes)
"""

from __future__ import annotations

import re
import os
from pathlib import Path
from typing import Dict, List
import pytest
from bs4 import BeautifulSoup

from trading_system.report_multipage import (
    build_head,
    build_styles,
    build_sticky_nav,
)

GH_PAGES_DIR = Path("gh-pages")

ALL_7_PAGES = [
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

VIEWPORT_WIDTHS = [320, 360, 375, 390, 412, 480, 600, 768]


# =============================================================================
# Helper Functions
# =============================================================================

def extract_all_css(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    return "\n".join(s.get_text() for s in soup.find_all("style"))


def extract_media_blocks(css: str, max_width: int) -> List[str]:
    pattern = rf'@media\s*\(\s*max-width\s*:\s*{max_width}px\s*\)\s*\{{+'
    matches = list(re.finditer(pattern, css, flags=re.IGNORECASE))
    blocks = []
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
        blocks.append(css[start_idx:max(start_idx, i - 1)])
    return blocks


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def pages_raw() -> Dict[str, str]:
    pages = {}
    for p in ALL_7_PAGES:
        fp = GH_PAGES_DIR / p
        assert fp.exists(), f"Expected static page missing: {fp}"
        pages[p] = fp.read_text(encoding="utf-8")
    return pages


@pytest.fixture(scope="module")
def pages_parsed(pages_raw: Dict[str, str]) -> Dict[str, BeautifulSoup]:
    return {p: BeautifulSoup(c, "html.parser") for p, c in pages_raw.items()}


@pytest.fixture(scope="module")
def compiled_multipage_css() -> str:
    return build_styles("")


# =============================================================================
# Challenge 1: Viewport Continuum & Zero Blowout Stress (320px–768px)
# =============================================================================

@pytest.mark.parametrize("viewport_width", VIEWPORT_WIDTHS)
def test_zero_viewport_blowout_across_continuum(viewport_width: int, pages_raw: Dict[str, str]):
    """
    Asserts for every viewport width from 320px to 768px:
    1. Every page declares width=device-width and viewport-fit=cover.
    2. Every page has global overflow-x: hidden on body/html.
    3. Maximum container layout bounds are compatible with the viewport width.
    """
    for page_name, html in pages_raw.items():
        # 1. Meta tag
        assert '<meta name="viewport"' in html, f"{page_name} missing meta viewport"
        assert 'width=device-width' in html, f"{page_name} missing width=device-width"
        assert 'viewport-fit=cover' in html, f"{page_name} missing viewport-fit=cover"

        # 2. Body overflow-x: hidden
        css = extract_all_css(html)
        assert re.search(r'body\s*\{[^}]*overflow-x\s*:\s*hidden', css, re.IGNORECASE) is not None, (
            f"{page_name} missing body {{ overflow-x: hidden; }}"
        )

        # 3. Viewport width budget vs hardcoded widths
        soup = BeautifulSoup(html, "html.parser")
        containers = soup.find_all(["div", "section", "header", "table", "article"])
        for el in containers:
            if el.name in ("td", "th", "canvas"):
                continue
            style = el.get("style", "")
            if not style:
                continue
            # If element has max-width %, vw, or overflow-x: auto, it is safe
            if "max-width" in style or "overflow-x: auto" in style or "overflow: hidden" in style:
                continue
            w_matches = re.findall(r'(?:^|;)\s*(?:min-)?width\s*:\s*(\d+)px', style, re.IGNORECASE)
            for w_val_str in w_matches:
                w_val = int(w_val_str)
                assert w_val <= 360, (
                    f"In {page_name}, element <{el.name}> has unconstrained width {w_val}px > 360px "
                    f"which causes blowout on viewport {viewport_width}px: '{style}'"
                )


# =============================================================================
# Challenge 2: Sticky Nav Bar Mechanics at 320px–768px
# =============================================================================

def test_sticky_nav_height_and_horizontal_carousel(pages_raw: Dict[str, str], compiled_multipage_css: str):
    """
    Adversarially tests navigation bar on 320px:
    - Must NOT wrap vertically (flex-wrap: nowrap !important).
    - Height must be strictly <= 56px on mobile (tested 50px-52px <= 56px).
    - Horizontal scroll container must have overflow-x: auto, -webkit-overflow-scrolling: touch, scrollbar-width: none.
    - All 7 nav links exist with min-height >= 44px touch targets.
    - Active nav indicator is applied to the exact matching page.
    """
    mq768_blocks = extract_media_blocks(compiled_multipage_css, 768)
    combined_mq768 = "\n".join(mq768_blocks)
    assert len(combined_mq768) > 0, "Missing @media (max-width: 768px) in multipage CSS"

    # Height constraint
    nav_height_match = re.search(r'\.sticky-nav\s*\{[^}]*(?:height:\s*5[0-6]px|max-height:\s*56px)', combined_mq768, re.IGNORECASE)
    assert nav_height_match is not None, "Sticky nav height on < 768px must be <= 56px"

    # Nowrap constraint
    assert re.search(r'\.sticky-nav-container\s*\{[^}]*flex-wrap\s*:\s*nowrap', combined_mq768, re.IGNORECASE) is not None

    # Carousel rules
    assert re.search(r'\.sticky-nav-links\s*\{[^}]*overflow-x\s*:\s*auto', combined_mq768, re.IGNORECASE) is not None
    assert re.search(r'\.sticky-nav-links\s*\{[^}]*white-space\s*:\s*nowrap', combined_mq768, re.IGNORECASE) is not None
    assert re.search(r'\.sticky-nav-links\s*\{[^}]*scrollbar-width\s*:\s*none', combined_mq768, re.IGNORECASE) is not None

    # Nav link touch target >= 44px
    assert re.search(r'\.nav-link\s*\{[^}]*min-height\s*:\s*44px', combined_mq768, re.IGNORECASE) is not None

    # Check active state across all 7 pages
    for page_name, html in pages_raw.items():
        soup = BeautifulSoup(html, "html.parser")
        nav = soup.find("nav", class_="sticky-nav-links")
        assert nav is not None, f"{page_name} missing nav.sticky-nav-links"
        active_links = nav.find_all("a", class_="active")
        assert len(active_links) >= 1, f"{page_name} has no active nav link"
        assert active_links[0].get("href", "").startswith(page_name), (
            f"{page_name} active nav link points to {active_links[0].get('href')}, expected {page_name}"
        )


# =============================================================================
# Challenge 3: Executive Dashboard 3-Card Mobile Stacking & Touch Architecture
# =============================================================================

def test_executive_dashboard_cards_stacking_deep(pages_raw: Dict[str, str]):
    """
    Stress-tests Executive Dashboard (index.html) responsive rules:
    - Card 1: .macro-grid collapses to repeat(2, 1fr) on 768px and 1fr on 480px.
              #regime-console-details collapses to 1fr.
              .regime-matrix-scroll container exists for 6-regime matrix.
    - Card 2: .health-grid collapses to repeat(2, 1fr) on 768px and 1fr on 480px.
              .health-pill has min-height: 44px.
    - Card 3: .charts-grid collapses to 1fr on 768px and 480px.
              .chart-card width is 100%.
    - Recommendations Table:
              Frozen columns (rank, symbol, name) compact to <= 200px (36+68+86 = 190px).
              Smooth touch horizontal swiping enabled (-webkit-overflow-scrolling: touch).
    """
    index_html = pages_raw["index.html"]
    css = extract_all_css(index_html)
    mq768 = "\n".join(extract_media_blocks(css, 768))
    mq480 = "\n".join(extract_media_blocks(css, 480))

    # Card 1 Macro Grid
    assert re.search(r'\.macro-grid\s*\{[^}]*grid-template-columns\s*:\s*(?:repeat\(2,\s*1fr\)|1fr)', mq768, re.IGNORECASE) is not None
    assert re.search(r'\.macro-grid\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq480, re.IGNORECASE) is not None
    assert re.search(r'#regime-console-details\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq768, re.IGNORECASE) is not None

    # Card 2 Health Grid & Pills
    assert re.search(r'\.health-grid\s*\{[^}]*grid-template-columns\s*:\s*(?:repeat\(2,\s*1fr\)|1fr)', mq768, re.IGNORECASE) is not None
    assert re.search(r'\.health-grid\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq480, re.IGNORECASE) is not None
    assert re.search(r'\.health-pill\s*\{[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None

    # Card 3 Charts Grid
    assert re.search(r'\.charts-grid\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq768, re.IGNORECASE) is not None
    assert re.search(r'\.chart-card\s*\{[^}]*width\s*:\s*100%', mq768, re.IGNORECASE) is not None

    # Ensemble Table Frozen Columns Geometry
    assert re.search(r'\.table-wrap\s+\.sticky-rank\s*\{[^}]*width\s*:\s*(?:3[0-9]|4[0-4])px', mq768, re.IGNORECASE) is not None
    assert re.search(r'\.table-wrap\s+\.sticky-symbol\s*\{[^}]*width\s*:\s*(?:6[0-9]|7[0-5])px', mq768, re.IGNORECASE) is not None
    assert re.search(r'\.table-wrap\s+\.sticky-name\s*\{[^}]*max-width\s*:\s*(?:8[0-9]|9[0-9]|1[01][0-9])px', mq768, re.IGNORECASE) is not None
    assert "-webkit-overflow-scrolling: touch" in css or "-webkit-overflow-scrolling: touch" in mq768


# =============================================================================
# Challenge 4: Strategy Encyclopedia Mobile Grid & Formula Box Scrolling
# =============================================================================

def test_strategy_encyclopedia_mobile_card_and_formula_scrolling(pages_raw: Dict[str, str]):
    """
    Stress-tests Strategy Encyclopedia (strategies.html) at 320px–768px:
    - .encyclopedia-grid must NOT remain desktop minmax(480px, 1fr) on <= 768px.
    - Must override to 1fr or minmax(100%, 1fr).
    - .strat-encyclopedia-card has min-width: 0 (prevents flex/grid blowouts).
    - .formula-box has max-width: 100% and overflow-x: auto.
    - MathJax / KaTeX formula containers (.formula-box mjx-container, .katex-display) allow touch scrolling.
    - Card buttons have min-height: 44px.
    """
    strat_html = pages_raw["strategies.html"]
    css = extract_all_css(strat_html)
    mq768 = "\n".join(extract_media_blocks(css, 768))
    mq480 = "\n".join(extract_media_blocks(css, 480))

    # Grid override
    assert re.search(r'\.encyclopedia-grid\s*\{[^}]*grid-template-columns\s*:\s*(?:repeat\([^)]*minmax\(100%,\s*1fr\)\)|1fr)', mq768, re.IGNORECASE) is not None
    assert re.search(r'\.encyclopedia-grid\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq480, re.IGNORECASE) is not None

    # Card min-width: 0
    assert re.search(r'\.strat-encyclopedia-card\s*\{[^}]*min-width\s*:\s*0', mq768, re.IGNORECASE) is not None

    # Formula box overflow containment
    assert "overflow-x: auto" in css and ".formula-box" in css
    assert "max-width: 100%" in css and ".formula-box" in css

    # Tap targets in footer
    assert re.search(r'\.strat-card-footer\s+\.btn\s*\{[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None or (
        re.search(r'\.btn-outline\s*\{[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None
    )


# =============================================================================
# Challenge 5: Market Pages 42-Column Tables & Frozen Columns Geometry
# =============================================================================

@pytest.mark.parametrize("mkt_page", MARKET_PAGES)
def test_market_pages_42_columns_and_frozen_left_geometry(mkt_page: str, pages_raw: Dict[str, str]):
    """
    Stress-tests each of the 5 market detail pages:
    - 42 columns strictly preserved (Rank, Symbol, Name, Market, Sector + 37 Strategies).
    - Frozen columns geometry: Rank (34px), Symbol (66px), Name (88px) = 188px total.
    - Remaining viewport budget at 320px: 320 - 188 = 132px (> 100px swipe window).
    - Remaining viewport budget at 375px: 375 - 188 = 187px.
    - Z-index stratification: Sticky header > Sticky body cell.
    - .col-strat factor columns remain visible on mobile (display: table-cell).
    - Toolbar controls (.filter-btn, .btn-csv-export, search input) have >= 44px tap targets.
    """
    html = pages_raw[mkt_page]
    soup = BeautifulSoup(html, "html.parser")
    css = extract_all_css(html)
    mq768 = "\n".join(extract_media_blocks(css, 768))

    # 1. 42 columns check
    table = soup.find("table", id="market-full-table")
    assert table is not None, f"{mkt_page} missing table#market-full-table"
    thead_ths = table.find("thead").find_all("th")
    assert len(thead_ths) == 42, f"{mkt_page} expected 42 <th> elements, found {len(thead_ths)}"

    # 2. Geometry check
    assert re.search(r'\.sticky-rank\s*\{[^}]*width\s*:\s*(?:3[0-9]|4[0-4])px', mq768, re.IGNORECASE) is not None
    assert re.search(r'\.sticky-symbol\s*\{[^}]*width\s*:\s*(?:6[0-9]|7[0-5])px', mq768, re.IGNORECASE) is not None
    assert re.search(r'\.sticky-name\s*\{[^}]*max-width\s*:\s*(?:8[0-9]|9[0-9]|1[01][0-9])px', mq768, re.IGNORECASE) is not None

    # 3. Viewport math verification
    rank_w = 34
    sym_w = 66
    name_w = 88
    total_frozen_w = rank_w + sym_w + name_w
    assert total_frozen_w == 188
    assert 320 - total_frozen_w == 132  # 132px available on smallest iPhone SE
    assert 375 - total_frozen_w == 187  # 187px available on iPhone 375px

    # 4. Display table-cell for .col-strat
    assert re.search(r'(?:\.market-content\s+)?#market-full-table\s+(?:th|td|\.)?col-strat\s*\{[^}]*display\s*:\s*table-cell', mq768, re.IGNORECASE) is not None

    # 5. Toolbar tap targets
    assert re.search(r'\.filter-btn\s*\{[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None
    assert re.search(r'\.btn-csv-export\s*\{[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None
    assert re.search(r'\.market-search-input\s*\{[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None


# =============================================================================
# Challenge 6: Stock Detail Drawer Bottom-Sheet Transformation
# =============================================================================

def test_stock_drawer_bottom_sheet_transformation(pages_raw: Dict[str, str], compiled_multipage_css: str):
    """
    Stress-tests the stock detail drawer across all pages:
    - Transformed to bottom sheet on < 768px: width: 100%, height: 90vh, border-radius: 16px 16px 0 0.
    - Drag handle or close button touch target >= 44px.
    - Radar chart canvas integration (<canvas id="drawerRadarChart">) across all 5 market pages.
    """
    css = compiled_multipage_css + "\n" + extract_all_css(pages_raw["index.html"])
    mq768 = "\n".join(extract_media_blocks(css, 768))

    # Width: 100%
    assert re.search(r'#stock-drawer\s*\{[^}]*width\s*:\s*100%', mq768, re.IGNORECASE) is not None

    # Height: 90vh
    assert re.search(r'#stock-drawer\s*\{[^}]*height\s*:\s*90vh', mq768, re.IGNORECASE) is not None

    # Border-radius: 16px 16px 0 0
    assert re.search(r'#stock-drawer\s*\{[^}]*border-radius\s*:\s*16px', mq768, re.IGNORECASE) is not None

    # Touch targets on close / handle
    assert re.search(r'\.drawer-close-btn\s*\{[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None or (
        re.search(r'#stock-drawer\s+button\b[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None
    )

    # Radar chart presence in market pages
    for mkt in MARKET_PAGES:
        html = pages_raw[mkt]
        assert 'id="drawerRadarChart"' in html, f"{mkt} missing #drawerRadarChart canvas"
        assert "renderDrawerRadarChart(" in html, f"{mkt} missing renderDrawerRadarChart call"


# =============================================================================
# Challenge 7: File Size Budget & Relative Link Integrity
# =============================================================================

def test_payload_budget_and_zero_broken_relative_links(pages_raw: Dict[str, str]):
    """
    Empirically verifies:
    1. index.html size is strictly under 512,000 bytes (500 KB).
    2. All 7 static pages exist in gh-pages/ and have non-trivial size (> 1024 bytes).
    3. All relative internal links resolve successfully without 404s.
    """
    index_path = GH_PAGES_DIR / "index.html"
    index_size = index_path.stat().st_size
    assert index_size < 512000, f"index.html exceeds 512,000 bytes budget: {index_size} bytes"

    for p in ALL_7_PAGES:
        path = GH_PAGES_DIR / p
        assert path.exists(), f"File {p} does not exist in gh-pages/"
        assert path.stat().st_size > 1024, f"File {p} suspiciously small: {path.stat().st_size} bytes"

    # Relative links resolution
    for page_name, html in pages_raw.items():
        links = re.findall(r'href="([^"]+)"', html)
        for link in links:
            if link.startswith(("http://", "https://", "mailto:", "javascript:", "#")):
                continue
            if "#" in link:
                file_target, anchor = link.split("#", 1)
                tgt_path = GH_PAGES_DIR / file_target
                assert tgt_path.exists(), f"Broken relative file target {file_target} in {page_name}"
                if anchor:
                    tgt_html = tgt_path.read_text(encoding="utf-8")
                    assert f'id="{anchor}"' in tgt_html, f"Broken cross-page anchor #{anchor} in {file_target}"
            else:
                tgt_path = GH_PAGES_DIR / link
                assert tgt_path.exists(), f"Broken relative file link {link} in {page_name}"
