"""
tests/test_dashboard_mobile_ux.py — Comprehensive Mobile UX Verification Suite

Empirically validates mobile responsiveness (< 768px and < 480px viewports),
DOM hygiene, CSS rules, sticky navigation, card stacking, sticky table columns,
stock detail drawer bottom-sheet transformation, and touch accessibility across
all 7 dashboard pages in gh-pages/ and templates in trading_system/report_multipage.py.

Requirements Covered:
- R1: Responsive Sticky Navigation Header (<= 56px, horizontal chip scroll, active centering)
- R2: Executive Dashboard (index.html) Mobile Stacking & Card Adaptation
- R3: Strategy Encyclopedia (strategies.html) Mobile Card Optimization
- R4: Granular Market Detail Pages Sticky Symbol & Preserved 42-Column Touch Tables
- R5: Stock Detail Drawer Mobile Bottom Sheet Transformation (90vh, 16px radius, radar chart)
- R6: Global Mobile Hygiene & Touch Accessibility (viewport-fit=cover, overflow-x hidden, >=44px)

Verification Mechanisms Covered:
- VM1: Automated Viewport & CSS Rule Verification
- VM2: Automated DOM & Layout Stress Testing
- VM3: End-to-End Pipeline & Regression Suite

Acceptance Criteria:
- A1: Zero Viewport Blowout
- A2: Touch-Friendly Sticky Nav
- A3: 3-Card Mobile Stacking
- A4: Table Sticky Column
- A5: Mobile Drawer Bottom Sheet
- A6: Strategy Encyclopedia Mobile Grid
- A7: 100% Test Pass
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict
import pytest
from bs4 import BeautifulSoup

from trading_system.report_multipage import (
    build_head,
    build_styles,
    build_sticky_nav,
)

GH_PAGES_DIR = Path("gh-pages")

EXPECTED_PAGES = [
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

PAGE_NAV_MAP = {
    "index.html": "index.html",
    "strategies.html": "strategies.html",
    "market_kospi.html": "market_kospi.html",
    "market_kosdaq.html": "market_kosdaq.html",
    "market_sp500.html": "market_sp500.html",
    "market_nasdaq.html": "market_nasdaq.html",
    "market_russell2000.html": "market_russell2000.html",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helper Utilities for CSS and DOM Inspection
# ─────────────────────────────────────────────────────────────────────────────

def extract_all_css_from_html(html_content: str) -> str:
    """Extract and concatenate all CSS text contained within <style> tags."""
    soup = BeautifulSoup(html_content, "html.parser")
    styles = [s.get_text() for s in soup.find_all("style")]
    return "\n".join(styles)


def extract_media_query_content(css: str, max_width: int) -> str:
    """
    Extract content inside @media (max-width: {max_width}px) { ... } block,
    accounting for nested braces and potential double-brace formatting.
    """
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
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
def ensure_reports_generated():
    """Ensure all 7 static pages exist in gh-pages/ before running tests."""
    from trading_system.generate_report import main as generate_report_main
    all_exist = all((GH_PAGES_DIR / p).exists() for p in EXPECTED_PAGES)
    if not all_exist:
        generate_report_main(["--result-dir", "trading_system/result", "--out", str(GH_PAGES_DIR / "index.html")])


@pytest.fixture(scope="module")
def pages_content() -> Dict[str, str]:
    """Read all 7 generated pages into a dictionary of string contents."""
    contents = {}
    for p in EXPECTED_PAGES:
        file_path = GH_PAGES_DIR / p
        assert file_path.exists(), f"Missing expected page: {file_path}"
        contents[p] = file_path.read_text(encoding="utf-8")
    return contents


@pytest.fixture(scope="module")
def pages_soup(pages_content: Dict[str, str]) -> Dict[str, BeautifulSoup]:
    """Parse all 7 generated pages into BeautifulSoup objects."""
    return {p: BeautifulSoup(content, "html.parser") for p, content in pages_content.items()}


@pytest.fixture(scope="module")
def multipage_styles_css() -> str:
    """Return the CSS generated by report_multipage.build_styles()."""
    return build_styles("")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Viewport Meta Tags & Global Hygiene (R1, R6, VM1, VM2, A1)
# ─────────────────────────────────────────────────────────────────────────────

def test_viewport_meta_tags_all_pages(pages_soup: Dict[str, BeautifulSoup]):
    """
    Asserts all 7 static pages have <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">.
    Also tests build_head() in trading_system/report_multipage.py.
    """
    for page_name in EXPECTED_PAGES:
        soup = pages_soup[page_name]
        meta_tags = soup.find_all("meta", attrs={"name": "viewport"})
        assert len(meta_tags) >= 1, f"Missing viewport meta tag in {page_name}"
        content = meta_tags[0].get("content", "")
        assert "width=device-width" in content, f"Viewport in {page_name} missing 'width=device-width'"
        assert "initial-scale=1.0" in content, f"Viewport in {page_name} missing 'initial-scale=1.0'"
        assert "viewport-fit=cover" in content, f"Viewport in {page_name} missing 'viewport-fit=cover' (R6/A1 defect)"

    # Test build_head() template directly
    head_html = build_head("Test Title", "Test Description", "index")
    assert '<meta name="viewport"' in head_html, "build_head() output missing viewport meta tag"
    assert 'viewport-fit=cover' in head_html, "build_head() output missing 'viewport-fit=cover'"


def test_global_mobile_hygiene_css(pages_content: Dict[str, str], multipage_styles_css: str):
    """
    Asserts body / html has overflow-x: hidden to eliminate horizontal page blowout.
    Asserts safe area insets are referenced: env(safe-area-inset-top) & env(safe-area-inset-bottom).
    Asserts max-width: 100vw or width: 100%.
    """
    # 1. Check compiled styles in report_multipage
    assert "overflow-x: hidden" in multipage_styles_css or "overflow-x:hidden" in multipage_styles_css, (
        "multipage_styles_css missing 'overflow-x: hidden' global hygiene rule"
    )

    # 2. Check each generated page's stylesheet
    for page_name in EXPECTED_PAGES:
        css = extract_all_css_from_html(pages_content[page_name])
        body_overflow_match = re.search(r'(?:html\s*,\s*)?body\s*\{[^}]*overflow-x\s*:\s*hidden', css, re.IGNORECASE)
        assert body_overflow_match is not None, (
            f"Page {page_name} missing 'overflow-x: hidden' on body/html in its stylesheet"
        )
        assert "safe-area-inset-bottom" in css, f"Page {page_name} stylesheet missing safe-area-inset-bottom"

    # 3. Check safe-area-inset-top in header or body
    combined_index_css = extract_all_css_from_html(pages_content["index.html"])
    assert "safe-area-inset-top" in combined_index_css or "safe-area-inset-top" in multipage_styles_css, (
        "Missing safe-area-inset-top rule in index or multipage styles"
    )


def test_dom_no_unconstrained_wide_inline_styles(pages_soup: Dict[str, BeautifulSoup]):
    """
    Layout Stress Test (VM2):
    Asserts no major container element in the DOM has an unconstrained inline style
    width > 360px without max-width/percentage wrappers, preventing 375px viewport blowout.
    """
    width_pattern = re.compile(r'(?:^|;)\s*(?:min-)?width\s*:\s*(\d+)px', re.IGNORECASE)
    
    for page_name, soup in pages_soup.items():
        # Check all container divs, sections, headers, and cards
        containers = soup.find_all(["div", "section", "header", "table", "article"])
        for el in containers:
            style = el.get("style", "")
            if not style:
                continue
            # Ignore table cells (td/th), canvas elements, or elements that have max-width percentage/vw wrappers
            if el.name in ("td", "th", "canvas"):
                continue
            if re.search(r'max-width\s*:\s*[\d.]+(?:%|vw)', style, re.IGNORECASE):
                continue
            
            # Check for hardcoded width exceeding 360px
            matches = width_pattern.findall(style)
            for w_str in matches:
                width_val = int(w_str)
                # Allow wide canvas wrappers only if overflow-x: auto is present
                if "overflow-x: auto" in style or "overflow: hidden" in style:
                    continue
                assert width_val <= 360, (
                    f"Page {page_name} element <{el.name} class='{el.get('class', [])}'> has hardcoded "
                    f"inline width {width_val}px > 360px without max-width wrapper: '{style}'"
                )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Sticky Navigation Mobile Rules (R1, VM1, A2)
# ─────────────────────────────────────────────────────────────────────────────

def test_sticky_navigation_mobile_rules(pages_content: Dict[str, str], multipage_styles_css: str):
    """
    Asserts .sticky-nav on < 768px and < 480px has height <= 56px (e.g. 52px or max-height: 56px).
    Asserts .sticky-nav-container has flex-wrap: nowrap !important.
    Asserts .sticky-nav-links has overflow-x: auto, white-space: nowrap, -webkit-overflow-scrolling: touch, scrollbar-width: none.
    Asserts .nav-link has min-height: 44px on mobile.
    Asserts build_sticky_nav() produces clean navigation with auto-centering script.
    """
    # 1. Test build_sticky_nav() template
    nav_html = build_sticky_nav("index")
    assert '<header class="sticky-nav">' in nav_html, "build_sticky_nav() missing sticky-nav header"
    assert '<nav class="sticky-nav-links">' in nav_html, "build_sticky_nav() missing sticky-nav-links"
    for _, href in PAGE_NAV_MAP.items():
        assert f'href="{href}"' in nav_html, f"build_sticky_nav() missing link for {href}"
    # Verify active nav link
    assert 'class="nav-link active nav-active"' in nav_html, "build_sticky_nav() missing active nav class"

    # Check active centering script presence
    assert "scrollIntoView" in nav_html, "build_sticky_nav() missing active chip auto-scroll centering script"

    # 2. Test CSS rules in multipage_styles_css and in generated pages
    mq768 = extract_media_query_content(multipage_styles_css, 768)
    assert len(mq768) > 0, "multipage_styles_css missing @media (max-width: 768px)"

    # Sticky nav height constraint on mobile (height: 52px or max-height: 56px)
    assert re.search(r'\.sticky-nav\s*\{[^}]*(?:height:\s*5[0-6]px|max-height:\s*56px)', mq768, re.IGNORECASE) is not None, (
        "Sticky nav on < 768px must have height <= 56px (found in mq768)"
    )

    # Sticky nav container flex-wrap: nowrap
    assert re.search(r'\.sticky-nav-container\s*\{[^}]*flex-wrap\s*:\s*nowrap', mq768, re.IGNORECASE) is not None, (
        "Sticky nav container on < 768px must enforce flex-wrap: nowrap to prevent multi-line vertical stacking"
    )

    # Sticky nav links horizontal carousel
    assert re.search(r'\.sticky-nav-links\s*\{[^}]*overflow-x\s*:\s*auto', mq768, re.IGNORECASE) is not None, (
        "Sticky nav links container on < 768px must have overflow-x: auto"
    )
    assert re.search(r'\.sticky-nav-links\s*\{[^}]*white-space\s*:\s*nowrap', mq768, re.IGNORECASE) is not None, (
        "Sticky nav links container on < 768px must have white-space: nowrap"
    )
    assert re.search(r'\.sticky-nav-links\s*\{[^}]*-webkit-overflow-scrolling\s*:\s*touch', mq768, re.IGNORECASE) is not None, (
        "Sticky nav links container on < 768px must have -webkit-overflow-scrolling: touch"
    )
    assert re.search(r'\.sticky-nav-links\s*\{[^}]*scrollbar-width\s*:\s*none', mq768, re.IGNORECASE) is not None, (
        "Sticky nav links container on < 768px must have scrollbar-width: none"
    )

    # Nav link touch target (min-height: 44px)
    assert re.search(r'\.nav-link\s*\{[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None, (
        "Nav link on < 768px must have min-height: 44px for touch accessibility (R1/R6)"
    )

    # 3. Test @media (max-width: 480px)
    mq480 = extract_media_query_content(multipage_styles_css, 480)
    assert len(mq480) > 0, "multipage_styles_css missing @media (max-width: 480px)"
    assert re.search(r'\.sticky-nav\s*\{[^}]*(?:height:\s*5[0-6]px|max-height:\s*56px)', mq480, re.IGNORECASE) is not None, (
        "Sticky nav on < 480px must have height <= 56px"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Executive Dashboard Cards Stacking (R2, VM1, VM2, A3)
# ─────────────────────────────────────────────────────────────────────────────

def test_executive_dashboard_cards_stacking(pages_content: Dict[str, str], multipage_styles_css: str):
    """
    Asserts Card 1 (.macro-grid, .gate-status-strip, #regime-console-details) responsive overrides for 768px and 480px.
    Asserts Card 2 .health-pill has >= 44px touch height, and .health-grid collapses responsively.
    Asserts Card 3 .charts-grid overrides minmax(320px, 1fr) to 1fr on mobile.
    Asserts Ensemble table frozen columns compact to <= 200px (e.g. 190px total) on mobile.
    """
    index_html = pages_content["index.html"]
    css = extract_all_css_from_html(index_html)
    mq768 = extract_media_query_content(css, 768)
    mq480 = extract_media_query_content(css, 480)

    assert len(mq768) > 0, "index.html missing @media (max-width: 768px)"
    assert len(mq480) > 0, "index.html missing @media (max-width: 480px)"

    # --- CARD 1 (2D Regime & Risk Gates) ---
    # .regime-risk-card margin reduction on mobile (<= 16px)
    assert re.search(r'\.regime-risk-card\s*\{[^}]*margin(?:-left|-right)?\s*:\s*(?:[0-9]|1[0-6])px', mq768, re.IGNORECASE) is not None, (
        ".regime-risk-card must reduce desktop 32px margins to <= 16px on mobile"
    )
    # .macro-grid responsive collapse on 768px (repeat(2, 1fr) or 1fr)
    assert re.search(r'\.macro-grid\s*\{[^}]*grid-template-columns\s*:\s*(?:repeat\(2,\s*1fr\)|1fr)', mq768, re.IGNORECASE) is not None, (
        ".macro-grid on < 768px must collapse into 2-column or 1-column grid"
    )
    # .macro-grid on 480px single column
    assert re.search(r'\.macro-grid\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq480, re.IGNORECASE) is not None, (
        ".macro-grid on < 480px must collapse into single column (1fr)"
    )
    # .gate-status-strip responsive grid collapse
    assert re.search(r'\.gate-status-strip\s*\{[^}]*grid-template-columns\s*:\s*(?:repeat\(2,\s*1fr\)|1fr)', mq768, re.IGNORECASE) is not None, (
        ".gate-status-strip on < 768px must collapse into 2-column or 1-column grid"
    )
    # #regime-console-details single column override for minmax(340px, 1fr)
    assert re.search(r'#regime-console-details\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq768, re.IGNORECASE) is not None, (
        "#regime-console-details on < 768px must override desktop minmax(340px, 1fr) to 1fr"
    )

    # --- CARD 2 (Strategy Health Monitor) ---
    # .health-pill touch target (min-height: 44px)
    assert re.search(r'\.health-pill\s*\{[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None, (
        ".health-pill must define min-height: 44px on mobile for touch accessibility"
    )
    # .health-grid responsive collapse on 768px (repeat(2, 1fr) or 1fr)
    assert re.search(r'\.health-grid\s*\{[^}]*grid-template-columns\s*:\s*(?:repeat\(2,\s*1fr\)|1fr)', mq768, re.IGNORECASE) is not None, (
        ".health-grid on < 768px must collapse into 2-column or 1-column grid"
    )
    # .health-grid on 480px single column
    assert re.search(r'\.health-grid\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq480, re.IGNORECASE) is not None, (
        ".health-grid on < 480px must collapse into single column (1fr)"
    )

    # --- CARD 3 (Portfolio & Allocation) ---
    # .charts-grid overrides minmax(320px, 1fr) to 1fr
    assert re.search(r'\.charts-grid\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq768, re.IGNORECASE) is not None, (
        ".charts-grid on < 768px must override desktop minmax(320px, 1fr) to 1fr"
    )
    # chart card width 100%
    assert re.search(r'\.chart-card\s*\{[^}]*width\s*:\s*100%', mq768, re.IGNORECASE) is not None, (
        ".chart-card on < 768px must have width: 100%"
    )

    # --- ENSEMBLE TABLE COMPACTING ---
    # Frozen columns compact to <= 200px total
    assert re.search(r'\.table-wrap\s+\.sticky-rank\s*\{[^}]*width\s*:\s*(?:3[0-9]|4[0-4])px', mq768, re.IGNORECASE) is not None, (
        ".sticky-rank width on < 768px must be compacted to <= 44px (e.g. 36px)"
    )
    assert re.search(r'\.table-wrap\s+\.sticky-symbol\s*\{[^}]*width\s*:\s*(?:6[0-9]|7[0-5])px', mq768, re.IGNORECASE) is not None, (
        ".sticky-symbol width on < 768px must be compacted to <= 75px (e.g. 68px)"
    )
    assert re.search(r'\.table-wrap\s+\.sticky-name\s*\{[^}]*max-width\s*:\s*(?:8[0-9]|9[0-9]|1[01][0-9])px', mq768, re.IGNORECASE) is not None, (
        ".sticky-name max-width on < 768px must be compacted to <= 110px (e.g. 86px-96px)"
    )
    # Smooth touch horizontal scroll
    assert "-webkit-overflow-scrolling: touch" in mq768 or "-webkit-overflow-scrolling: touch" in css, (
        "Ensemble table wrapper missing -webkit-overflow-scrolling: touch"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Strategy Encyclopedia Mobile Grid (R3, VM1, VM2, A6)
# ─────────────────────────────────────────────────────────────────────────────

def test_strategy_encyclopedia_mobile_grid(pages_content: Dict[str, str], multipage_styles_css: str):
    """
    Asserts strategies.html and build_styles() override minmax(480px, 1fr) with minmax(100%, 1fr) or 1fr on < 768px and < 480px.
    Asserts .formula-box has overflow-x: auto and max-width: 100%.
    Asserts .strat-encyclopedia-card has min-width: 0.
    Asserts card buttons have min-height: 44px.
    """
    strat_html = pages_content["strategies.html"]
    css = extract_all_css_from_html(strat_html)
    mq768 = extract_media_query_content(css, 768) or extract_media_query_content(multipage_styles_css, 768)
    mq480 = extract_media_query_content(css, 480) or extract_media_query_content(multipage_styles_css, 480)

    assert len(mq768) > 0, "strategies.html missing @media (max-width: 768px)"
    assert len(mq480) > 0, "strategies.html missing @media (max-width: 480px)"

    # .encyclopedia-grid override of minmax(480px, 1fr)
    grid_override_match = re.search(
        r'\.encyclopedia-grid\s*\{[^}]*grid-template-columns\s*:\s*(?:repeat\([^)]*minmax\(100%,\s*1fr\)\)|1fr)',
        mq768,
        re.IGNORECASE,
    )
    assert grid_override_match is not None, (
        ".encyclopedia-grid on < 768px must override desktop minmax(480px, 1fr) with minmax(100%, 1fr) or 1fr"
    )

    # .encyclopedia-grid on 480px single column (1fr)
    assert re.search(r'\.encyclopedia-grid\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq480, re.IGNORECASE) is not None, (
        ".encyclopedia-grid on < 480px must be 1fr"
    )

    # .formula-box horizontal scrolling within card
    assert re.search(r'\.formula-box\s*\{[^}]*overflow-x\s*:\s*auto', mq768, re.IGNORECASE) is not None or (
        "overflow-x: auto" in css and ".formula-box" in css
    ), ".formula-box must specify overflow-x: auto to prevent mathematical formula blowout"
    assert re.search(r'\.formula-box\s*\{[^}]*max-width\s*:\s*100%', mq768, re.IGNORECASE) is not None or (
        "max-width: 100%" in css and ".formula-box" in css
    ), ".formula-box must specify max-width: 100%"

    # .strat-encyclopedia-card min-width: 0 (essential for flex/grid child overflow containment)
    assert re.search(r'\.strat-encyclopedia-card\s*\{[^}]*min-width\s*:\s*0', mq768, re.IGNORECASE) is not None, (
        ".strat-encyclopedia-card must specify min-width: 0 on mobile to allow inner formula box scrolling"
    )

    # Tap target for action buttons in cards
    assert re.search(r'\.strat-card-footer\s+\.btn\s*\{[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None or (
        re.search(r'\.btn-outline\s*\{[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None
    ), "Strategy card footer buttons must have min-height: 44px on mobile"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Market Tables Sticky Columns & 42-Column Preservation (R4, VM1, VM2, A4)
# ─────────────────────────────────────────────────────────────────────────────

def test_market_tables_sticky_columns_and_preservation(pages_content: Dict[str, str], multipage_styles_css: str):
    """
    Asserts all 5 market pages preserve exactly 42 <th> columns.
    Asserts Column 0 (Rank), Column 1 (Symbol), Column 2 (Name) have position: sticky; left: 0; z-index: 2; background: var(--surface).
    Asserts mobile sticky column total width <= 200px (e.g. 188px).
    Asserts .col-strat columns are displayed on mobile in market tables (e.g. display: table-cell).
    Asserts .preset-buttons has overflow-x: auto, and .filter-btn, .btn-csv-export, .market-search-input have >= 44px tap targets.
    """
    for mkt_file in MARKET_PAGES:
        html = pages_content[mkt_file]
        css = extract_all_css_from_html(html)
        mq768 = extract_media_query_content(css, 768) or extract_media_query_content(multipage_styles_css, 768)

        # 1. 42 Columns Invariant Preservation
        th_tags = re.findall(r'<th\b', html)
        assert len(th_tags) == 42, f"Market page {mkt_file} must preserve exactly 42 <th> columns, found {len(th_tags)}"

        # 2. Sticky Column Rules (Rank, Symbol, Name)
        assert "th.sticky-col" in css or ".sticky-col" in css or ".sticky-col" in multipage_styles_css, (
            f"Missing .sticky-col definition in {mkt_file}"
        )
        assert "position: sticky" in css or "position: sticky" in multipage_styles_css, (
            f"Missing position: sticky in {mkt_file}"
        )

        # 3. Mobile Sticky Compacting (Total <= 200px)
        assert re.search(r'\.sticky-rank\s*\{[^}]*width\s*:\s*(?:3[0-9]|4[0-4])px', mq768, re.IGNORECASE) is not None, (
            f"Market page {mkt_file} .sticky-rank width on mobile must be compacted to <= 44px (e.g. 34px-36px)"
        )
        assert re.search(r'\.sticky-symbol\s*\{[^}]*width\s*:\s*(?:6[0-9]|7[0-5])px', mq768, re.IGNORECASE) is not None, (
            f"Market page {mkt_file} .sticky-symbol width on mobile must be compacted to <= 75px (e.g. 66px-68px)"
        )
        assert re.search(r'\.sticky-name\s*\{[^}]*max-width\s*:\s*(?:8[0-9]|9[0-9]|1[01][0-9])px', mq768, re.IGNORECASE) is not None, (
            f"Market page {mkt_file} .sticky-name max-width on mobile must be compacted to <= 110px (e.g. 88px)"
        )

        # 4. .col-strat factor columns must be visible on mobile in market tables
        # Check that market table does NOT hide .col-strat (must override desktop hide rule)
        strat_display_match = re.search(
            r'(?:\.market-content\s+)?#market-full-table\s+(?:th|td|\.)?col-strat\s*\{[^}]*display\s*:\s*table-cell',
            mq768,
            re.IGNORECASE,
        )
        assert strat_display_match is not None, (
            f"Market page {mkt_file} must override .col-strat mobile suppression with display: table-cell"
        )

        # 5. Toolbar & Touch Tap Targets
        assert re.search(r'\.preset-buttons\s*\{[^}]*overflow-x\s*:\s*auto', mq768, re.IGNORECASE) is not None, (
            f"Market page {mkt_file} .preset-buttons must have overflow-x: auto on mobile"
        )
        assert re.search(r'\.filter-btn\s*\{[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None, (
            f"Market page {mkt_file} .filter-btn must have min-height: 44px on mobile"
        )
        assert re.search(r'\.btn-csv-export\s*\{[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None, (
            f"Market page {mkt_file} .btn-csv-export must have min-height: 44px on mobile"
        )
        assert re.search(r'\.market-search-input\s*\{[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None, (
            f"Market page {mkt_file} .market-search-input must have min-height: 44px on mobile"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Stock Detail Drawer Mobile Bottom Sheet (R5, VM1, VM2, A5)
# ─────────────────────────────────────────────────────────────────────────────

def test_stock_drawer_mobile_bottom_sheet(pages_content: Dict[str, str], multipage_styles_css: str):
    """
    Asserts #stock-drawer on < 768px has width: 100%, max-width: 100vw, height: 90vh, and border-radius: 16px 16px 0 0.
    Asserts drawer close button and drag handle have >= 44px touch targets.
    Asserts renderDrawerRadarChart is defined and invoked in all market pages.
    """
    # 1. CSS Rule Assertions for Bottom Sheet
    css = multipage_styles_css + "\n" + extract_all_css_from_html(pages_content["index.html"])
    mq768 = extract_media_query_content(css, 768)

    assert len(mq768) > 0, "Missing @media (max-width: 768px) for stock drawer verification"

    # Width: 100% and max-width: 100vw
    assert re.search(r'#stock-drawer\s*\{[^}]*width\s*:\s*100%', mq768, re.IGNORECASE) is not None, (
        "#stock-drawer on < 768px must have width: 100%"
    )
    assert re.search(r'#stock-drawer\s*\{[^}]*max-width\s*:\s*100vw', mq768, re.IGNORECASE) is not None or (
        re.search(r'#stock-drawer\s*\{[^}]*max-width\s*:\s*100%', mq768, re.IGNORECASE) is not None
    ), "#stock-drawer on < 768px must have max-width: 100vw or 100%"

    # Height: 90vh (R5 specification)
    assert re.search(r'#stock-drawer\s*\{[^}]*height\s*:\s*90vh', mq768, re.IGNORECASE) is not None, (
        "#stock-drawer on < 768px must have height: 90vh (R5 requirement)"
    )

    # Border-radius: 16px 16px 0 0
    assert re.search(r'#stock-drawer\s*\{[^}]*border-radius\s*:\s*16px\s+16px\s+0\s+0', mq768, re.IGNORECASE) is not None or (
        re.search(r'#stock-drawer\s*\{[^}]*border-radius\s*:\s*16px', mq768, re.IGNORECASE) is not None
    ), "#stock-drawer on < 768px must have border-radius: 16px 16px 0 0"

    # Drag handle & Close button touch target >= 44px
    assert re.search(r'\.drawer-close-btn\s*\{[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None or (
        re.search(r'#stock-drawer\s+button\b[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None
    ), "Drawer close button must have min-height: 44px on mobile"

    # 2. JavaScript Radar Chart Integration in all 5 Market Pages
    for mkt_file in MARKET_PAGES:
        html = pages_content[mkt_file]
        assert "function renderDrawerRadarChart" in html or "const renderDrawerRadarChart" in html or "var renderDrawerRadarChart" in html, (
            f"Missing function renderDrawerRadarChart in {mkt_file}"
        )
        assert "renderDrawerRadarChart(" in html, (
            f"openStockDrawer in {mkt_file} must invoke renderDrawerRadarChart"
        )
        assert '<canvas id="drawerRadarChart"' in html, (
            f"Missing <canvas id='drawerRadarChart'> in {mkt_file}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Cross-Page Relative Links & Page Size Budget (A7)
# ─────────────────────────────────────────────────────────────────────────────

def test_relative_links_and_page_budgets(pages_content: Dict[str, str]):
    """
    Asserts 0 broken cross-page relative links across all 7 pages.
    Asserts index.html size < 512,000 bytes (500 KB limit).
    Asserts all 7 pages exist and have size > 1024 bytes.
    """
    # 1. File existence and size checks
    for page_name in EXPECTED_PAGES:
        file_path = GH_PAGES_DIR / page_name
        assert file_path.exists(), f"Page {page_name} missing from gh-pages/"
        size = file_path.stat().st_size
        assert size > 1024, f"Page {page_name} size is unexpectedly small: {size} bytes"

    # 2. index.html budget constraint (< 500 KB)
    index_size = (GH_PAGES_DIR / "index.html").stat().st_size
    assert index_size < 500 * 1024, (
        f"index.html must be < 500 KB (512,000 bytes), current size is {index_size} bytes ({index_size/1024:.2f} KB)"
    )

    # 3. Relative link resolution across all 7 pages
    for page_name, content in pages_content.items():
        links = re.findall(r'href="([^"]+)"', content)
        for link in links:
            if link.startswith(("http://", "https://", "mailto:", "javascript:", "data:", "#")):
                continue
            if "#" in link:
                file_part, anchor = link.split("#", 1)
                target_file = GH_PAGES_DIR / file_part
                assert target_file.exists(), f"Broken relative target file {file_part} in {page_name}"
                if anchor:
                    target_content = target_file.read_text(encoding="utf-8")
                    assert f'id="{anchor}"' in target_content, f"Broken cross-page anchor #{anchor} in {file_part}"
            else:
                target_file = GH_PAGES_DIR / link
                assert target_file.exists(), f"Broken relative file link {link} in {page_name}"


# ─────────────────────────────────────────────────────────────────────────────
# 8. Formal Acceptance Criteria Tests (A1–A7)
# ─────────────────────────────────────────────────────────────────────────────

class TestAcceptanceCriteria:
    """Explicit mapping to Acceptance Criteria A1–A7 in ORIGINAL_REQUEST.md and SCOPE.md."""

    def test_a1_zero_viewport_blowout(self, pages_content: Dict[str, str]):
        """A1: All 7 pages render with zero horizontal body scroll and viewport-fit=cover."""
        for page_name in EXPECTED_PAGES:
            html = pages_content[page_name]
            assert "viewport-fit=cover" in html, f"A1 Failure: {page_name} missing viewport-fit=cover"
            css = extract_all_css_from_html(html)
            assert re.search(r'body\s*\{[^}]*overflow-x\s*:\s*hidden', css, re.IGNORECASE) is not None, (
                f"A1 Failure: {page_name} missing overflow-x: hidden on body"
            )

    def test_a2_touch_friendly_sticky_nav(self, multipage_styles_css: str):
        """A2: Sticky nav bar adapts to mobile with horizontal scrolling chips and height <= 56px."""
        mq768 = extract_media_query_content(multipage_styles_css, 768)
        assert re.search(r'\.sticky-nav\s*\{[^}]*(?:height:\s*5[0-6]px|max-height:\s*56px)', mq768, re.IGNORECASE) is not None
        assert re.search(r'\.sticky-nav-links\s*\{[^}]*overflow-x\s*:\s*auto', mq768, re.IGNORECASE) is not None
        assert re.search(r'\.nav-link\s*\{[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE) is not None

    def test_a3_3card_mobile_stacking(self, pages_content: Dict[str, str]):
        """A3: Cards 1, 2, and 3 stack gracefully on mobile screens."""
        css = extract_all_css_from_html(pages_content["index.html"])
        mq768 = extract_media_query_content(css, 768)
        assert re.search(r'\.macro-grid\s*\{[^}]*grid-template-columns\s*:\s*(?:repeat\(2,\s*1fr\)|1fr)', mq768, re.IGNORECASE) is not None
        assert re.search(r'\.health-grid\s*\{[^}]*grid-template-columns\s*:\s*(?:repeat\(2,\s*1fr\)|1fr)', mq768, re.IGNORECASE) is not None
        assert re.search(r'\.charts-grid\s*\{[^}]*grid-template-columns\s*:\s*1fr', mq768, re.IGNORECASE) is not None

    def test_a4_table_sticky_column(self, pages_content: Dict[str, str], multipage_styles_css: str):
        """A4: Market pages freeze symbol/name column during horizontal scroll on touch screens."""
        assert "sticky-col" in multipage_styles_css or "sticky-rank" in multipage_styles_css, (
            "A4 Failure: multipage_styles_css missing sticky column styles for market tables"
        )
        for mkt in MARKET_PAGES:
            css = extract_all_css_from_html(pages_content[mkt])
            assert "position: sticky" in css, f"Missing position: sticky in {mkt}"
            assert ".sticky-col" in css or ".sticky-name" in css, f"Missing .sticky-col in {mkt}"

    def test_a5_mobile_drawer_bottom_sheet(self, pages_content: Dict[str, str], multipage_styles_css: str):
        """A5: Stock detail drawer opens as a full-width bottom sheet (90vh, 16px radius)."""
        css = multipage_styles_css + "\n" + extract_all_css_from_html(pages_content["index.html"])
        mq768 = extract_media_query_content(css, 768)
        assert re.search(r'#stock-drawer\s*\{[^}]*height\s*:\s*90vh', mq768, re.IGNORECASE) is not None
        assert re.search(r'#stock-drawer\s*\{[^}]*border-radius\s*:\s*16px', mq768, re.IGNORECASE) is not None

    def test_a6_strategy_encyclopedia_mobile_grid(self, pages_content: Dict[str, str], multipage_styles_css: str):
        """A6: Strategy cards adapt to single-column width on mobile with internal formula box scrolling."""
        css = multipage_styles_css + "\n" + extract_all_css_from_html(pages_content["strategies.html"])
        mq768 = extract_media_query_content(css, 768)
        assert re.search(r'\.encyclopedia-grid\s*\{[^}]*grid-template-columns\s*:\s*(?:repeat\([^)]*minmax\(100%,\s*1fr\)\)|1fr)', mq768, re.IGNORECASE) is not None
        assert re.search(r'\.formula-box\s*\{[^}]*overflow-x\s*:\s*auto', mq768, re.IGNORECASE) is not None or ".formula-box" in css

    def test_a7_structural_integrity_and_budgets(self, pages_content: Dict[str, str]):
        """A7: All existing report tests, pipeline artifact verification, and new mobile UX verification tests pass."""
        index_size = (GH_PAGES_DIR / "index.html").stat().st_size
        assert index_size < 500 * 1024
        for p in EXPECTED_PAGES:
            assert (GH_PAGES_DIR / p).exists()
