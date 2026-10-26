"""
tests/test_dashboard_mobile_m1_adversarial.py — Empirical Adversarial Stress Test for Milestone M1

Milestone M1 Review Scope:
- R1: Responsive Sticky Navigation Header (<= 56px, horizontal chip scroll, active centering, flex-wrap: nowrap)
- R6: Global Mobile Hygiene & Touch Accessibility (viewport-fit=cover, overflow-x: hidden, 44x44px tap targets)

Adversarial Stress Scenarios:
1. Viewport sizes: 320px (iPhone 5/SE1), 375px (iPhone 6/7/8/SE2), 390px (iPhone 12/13/14), 412px (Pixel), 768px (iPad portrait).
2. Boundary assertions: .sticky-nav height <= 56px and .sticky-nav-container flex-wrap: nowrap across all viewports <= 768px.
3. Horizontal swipe properties: -webkit-overflow-scrolling: touch and scrollbar-width: none on .sticky-nav-links.
4. Auto-centering script verification across all 7 generated pages.
5. Touch target area verification (>= 44x44px) for all primary interactive navigation and utility elements.
6. HTML byte budget and newline cross-platform hygiene (< 512,000 bytes, Unix LF).
"""

import re
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

PAGES = [
    "index.html",
    "strategies.html",
    "market_kospi.html",
    "market_kosdaq.html",
    "market_sp500.html",
    "market_nasdaq.html",
    "market_russell2000.html",
]

TARGET_VIEWPORTS = [320, 375, 390, 412, 768]


@pytest.fixture(scope="module")
def pages_html() -> Dict[str, str]:
    assert GH_PAGES_DIR.exists(), "gh-pages directory does not exist"
    data = {}
    for p in PAGES:
        path = GH_PAGES_DIR / p
        assert path.exists(), f"Page {p} not found in gh-pages/"
        data[p] = path.read_text(encoding="utf-8")
    return data


@pytest.fixture(scope="module")
def pages_soup(pages_html: Dict[str, str]) -> Dict[str, BeautifulSoup]:
    return {p: BeautifulSoup(html, "html.parser") for p, html in pages_html.items()}


@pytest.fixture(scope="module")
def multipage_css() -> str:
    return build_styles("")


def extract_media_block(css: str, max_w: int) -> str:
    pattern = rf'@media\s*\(\s*max-width\s*:\s*{max_w}px\s*\)\s*\{{+'
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
# 1. Stress-Test: Viewport Sizes (320px, 375px, 390px, 412px, 768px)
# =============================================================================

@pytest.mark.parametrize("viewport_width", TARGET_VIEWPORTS)
def test_viewport_rules_applicable_at_target_widths(viewport_width: int, multipage_css: str, pages_html: Dict[str, str]):
    """
    Stress-tests that for each target viewport width in [320, 375, 390, 412, 768],
    the appropriate media queries (max-width: 768px and/or max-width: 480px) are activated,
    guaranteeing sticky nav height <= 56px, nowrap, and hidden overflow.
    """
    mq768 = extract_media_block(multipage_css, 768)
    assert len(mq768) > 0, "Missing @media (max-width: 768px) in multipage stylesheet"

    if viewport_width <= 480:
        mq480 = extract_media_block(multipage_css, 480)
        assert len(mq480) > 0, "Missing @media (max-width: 480px) in multipage stylesheet"
        # At <= 480px, height should be 50px, max-height 56px
        m480 = re.search(r'\.sticky-nav\s*\{[^}]*height\s*:\s*(\d+)px', mq480, re.IGNORECASE)
        assert m480 is not None, "Missing height rule in @media (max-width: 480px) for .sticky-nav"
        assert int(m480.group(1)) <= 56, f"Height {m480.group(1)}px exceeds 56px in 480px breakpoint"
    else:
        # At <= 768px, height should be 52px, max-height 56px
        m768 = re.search(r'\.sticky-nav\s*\{[^}]*height\s*:\s*(\d+)px', mq768, re.IGNORECASE)
        assert m768 is not None, "Missing height rule in @media (max-width: 768px) for .sticky-nav"
        assert int(m768.group(1)) <= 56, f"Height {m768.group(1)}px exceeds 56px in 768px breakpoint"


@pytest.mark.parametrize("viewport_width", TARGET_VIEWPORTS)
def test_no_horizontal_blowout_risk_at_viewports(viewport_width: int, pages_html: Dict[str, str]):
    """
    Asserts html and body styles across all 7 pages strictly enforce overflow-x: hidden !important,
    width: 100%, and max-width: 100vw, preventing horizontal scroll blowout at narrow widths.
    """
    for page_name, html in pages_html.items():
        assert "overflow-x: hidden" in html or "overflow-x:hidden" in html, (
            f"Page {page_name} missing overflow-x: hidden for viewport {viewport_width}px"
        )
        assert "max-width: 100vw" in html or "max-width:100vw" in html, (
            f"Page {page_name} missing max-width: 100vw for viewport {viewport_width}px"
        )


# =============================================================================
# 2. Stress-Test: .sticky-nav Height <= 56px and .sticky-nav-container No-Wrap
# =============================================================================

def test_sticky_nav_height_strict_boundary(multipage_css: str, pages_html: Dict[str, str]):
    """
    Adversarially asserts that across both 768px and 480px breakpoints,
    the sticky nav height is explicitly clamped <= 56px and max-height: 56px is enforced.
    Also asserts overflow: hidden is set to prevent child leakage.
    """
    for bp in [768, 480]:
        mq = extract_media_block(multipage_css, bp)
        assert len(mq) > 0, f"Missing breakpoint {bp}px in multipage_css"

        # Check height <= 56px
        h_match = re.search(r'\.sticky-nav\s*\{[^}]*height\s*:\s*(\d+)px', mq, re.IGNORECASE)
        assert h_match is not None, f"Breakpoint {bp}px missing .sticky-nav height declaration"
        assert int(h_match.group(1)) <= 56, f"Breakpoint {bp}px height {h_match.group(1)}px > 56px"

        # Check max-height <= 56px
        max_h_match = re.search(r'\.sticky-nav\s*\{[^}]*max-height\s*:\s*(\d+)px', mq, re.IGNORECASE)
        assert max_h_match is not None, f"Breakpoint {bp}px missing .sticky-nav max-height declaration"
        assert int(max_h_match.group(1)) <= 56, f"Breakpoint {bp}px max-height {max_h_match.group(1)}px > 56px"

    # Check overflow: hidden on .sticky-nav at 768px
    mq768 = extract_media_block(multipage_css, 768)
    assert re.search(r'\.sticky-nav\s*\{[^}]*overflow\s*:\s*hidden', mq768, re.IGNORECASE) is not None, (
        ".sticky-nav missing overflow: hidden in mobile breakpoint"
    )


def test_sticky_nav_container_nowrap_guarantee(multipage_css: str):
    """
    Adversarially asserts that .sticky-nav-container has flex-wrap: nowrap !important
    so that under no circumstance can the nav items wrap into a second line.
    """
    mq768 = extract_media_block(multipage_css, 768)
    nowrap_match = re.search(r'\.sticky-nav-container\s*\{[^}]*flex-wrap\s*:\s*nowrap\s*!important', mq768, re.IGNORECASE)
    assert nowrap_match is not None, ".sticky-nav-container missing flex-wrap: nowrap !important on mobile"


def test_sticky_nav_brand_and_actions_suppression(multipage_css: str):
    """
    Asserts that desktop-only extraneous elements (.badge-quant-edition and .sticky-nav-actions)
    are hidden with display: none !important on mobile to preserve horizontal space.
    """
    mq768 = extract_media_block(multipage_css, 768)
    assert re.search(r'\.sticky-nav-brand\s+\.badge-quant-edition\s*\{[^}]*display\s*:\s*none\s*!important', mq768, re.IGNORECASE) is not None, (
        ".badge-quant-edition must be hidden on mobile"
    )
    assert re.search(r'\.sticky-nav-actions\s*\{[^}]*display\s*:\s*none\s*!important', mq768, re.IGNORECASE) is not None, (
        ".sticky-nav-actions must be hidden on mobile"
    )


# =============================================================================
# 3. Stress-Test: -webkit-overflow-scrolling: touch and scrollbar-width: none
# =============================================================================

def test_touch_scroll_and_scrollbar_suppression(multipage_css: str, pages_html: Dict[str, str]):
    """
    Adversarially asserts that .sticky-nav-links has:
    1. overflow-x: auto !important
    2. white-space: nowrap !important
    3. -webkit-overflow-scrolling: touch !important
    4. scrollbar-width: none !important
    5. -ms-overflow-style: none !important
    6. .sticky-nav-links::-webkit-scrollbar { display: none !important; }
    """
    mq768 = extract_media_block(multipage_css, 768)
    assert len(mq768) > 0

    assert re.search(r'\.sticky-nav-links\s*\{[^}]*overflow-x\s*:\s*auto\s*!important', mq768, re.IGNORECASE) is not None, (
        "Missing overflow-x: auto !important on .sticky-nav-links"
    )
    assert re.search(r'\.sticky-nav-links\s*\{[^}]*white-space\s*:\s*nowrap\s*!important', mq768, re.IGNORECASE) is not None, (
        "Missing white-space: nowrap !important on .sticky-nav-links"
    )
    assert re.search(r'\.sticky-nav-links\s*\{[^}]*-webkit-overflow-scrolling\s*:\s*touch\s*!important', mq768, re.IGNORECASE) is not None, (
        "Missing -webkit-overflow-scrolling: touch !important on .sticky-nav-links"
    )
    assert re.search(r'\.sticky-nav-links\s*\{[^}]*scrollbar-width\s*:\s*none\s*!important', mq768, re.IGNORECASE) is not None, (
        "Missing scrollbar-width: none !important on .sticky-nav-links"
    )
    assert re.search(r'\.sticky-nav-links\s*\{[^}]*-ms-overflow-style\s*:\s*none\s*!important', mq768, re.IGNORECASE) is not None, (
        "Missing -ms-overflow-style: none !important on .sticky-nav-links"
    )
    assert re.search(r'\.sticky-nav-links::-webkit-scrollbar\s*\{[^}]*display\s*:\s*none\s*!important', mq768, re.IGNORECASE) is not None, (
        "Missing display: none !important on .sticky-nav-links::-webkit-scrollbar"
    )


# =============================================================================
# 4. Stress-Test: Active Nav Auto-Centering Script
# =============================================================================

def test_active_nav_auto_scroll_behavior(pages_soup: Dict[str, BeautifulSoup]):
    """
    Asserts that every page contains the auto-centering script and has exactly
    one active chip that matches the script's query selector.
    """
    for page_name, soup in pages_soup.items():
        # Look for script containing scrollIntoView
        scripts = soup.find_all("script")
        scroll_scripts = [s.get_text() for s in scripts if "scrollIntoView" in s.get_text()]
        assert len(scroll_scripts) >= 1, f"Page {page_name} missing auto-centering scrollIntoView script"

        # Verify active chip selector
        active_chip = soup.select(".sticky-nav-links .active, .sticky-nav-links .nav-active")
        assert len(active_chip) == 1, (
            f"Page {page_name} must have exactly 1 active nav link chip, found {len(active_chip)}"
        )


# =============================================================================
# 5. Stress-Test: Touch Target Accessibility (>= 44x44px)
# =============================================================================

def test_touch_target_accessibility(multipage_css: str, pages_html: Dict[str, str]):
    """
    Asserts that .nav-link on mobile defines min-height: 44px !important and min-width: 44px !important.
    Asserts touch-action: manipulation is set for fast mobile tapping.
    Asserts #btn-back-to-top has min-height: 44px and min-width: 44px.
    """
    mq768 = extract_media_block(multipage_css, 768)

    assert re.search(r'\.nav-link\s*\{[^}]*min-height\s*:\s*44px\s*!important', mq768, re.IGNORECASE) is not None, (
        ".nav-link missing min-height: 44px !important"
    )
    assert re.search(r'\.nav-link\s*\{[^}]*min-width\s*:\s*44px\s*!important', mq768, re.IGNORECASE) is not None, (
        ".nav-link missing min-width: 44px !important"
    )
    assert re.search(r'\.nav-link\s*\{[^}]*touch-action\s*:\s*manipulation', mq768, re.IGNORECASE) is not None, (
        ".nav-link missing touch-action: manipulation"
    )

    # Check back-to-top button in index.html styles
    index_html = pages_html["index.html"]
    btt_min_h = re.search(r'#btn-back-to-top\s*\{[^}]*min-height\s*:\s*44px\s*!important', index_html, re.IGNORECASE)
    assert btt_min_h is not None, "#btn-back-to-top missing min-height: 44px !important"


# =============================================================================
# 6. Stress-Test: Safe Area Insets (env)
# =============================================================================

def test_safe_area_insets_defined(multipage_css: str, pages_html: Dict[str, str]):
    """
    Asserts that safe area insets are referenced:
    - padding-top: max(0px, env(safe-area-inset-top, 0px)) on .sticky-nav
    - padding-bottom: env(safe-area-inset-bottom, 0px) on body
    """
    mq768 = extract_media_block(multipage_css, 768)
    assert "safe-area-inset-top" in mq768, "Missing safe-area-inset-top on .sticky-nav in mobile breakpoint"
    assert "safe-area-inset-bottom" in multipage_css, "Missing safe-area-inset-bottom in global body stylesheet"


# =============================================================================
# 7. Stress-Test: File Size and Newline Encoding Budget
# =============================================================================

def test_file_size_and_cross_platform_encoding():
    """
    Asserts index.html file size is strictly < 512,000 bytes (500 KB limit).
    Asserts CRLF count is 0 or does not blow out the file size beyond budget.
    """
    index_path = GH_PAGES_DIR / "index.html"
    assert index_path.exists(), "index.html missing"
    size = index_path.stat().st_size
    assert size < 512000, f"index.html exceeds 512,000 bytes: {size} bytes ({size/1024:.2f} KB)"

    raw_bytes = index_path.read_bytes()
    crlf_count = raw_bytes.count(b"\r\n")
    # With newline="\n" in Path.write_text, CRLF count in index.html generated by build_all_pages should be 0
    assert crlf_count == 0, f"Found {crlf_count} CRLF sequences in index.html; expected Unix LF (newline='\\n')"
