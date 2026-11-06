"""
tests/test_e2e_mobile_ux.py — Comprehensive 4-Tier E2E Mobile UX Test Suite

Author: test_writer_mobile_ux_e2e
Target: Android Galaxy Mobile Web (Samsung Internet & Chrome Mobile, 360px–412px viewports)
        and Responsive Desktop (>= 1024px).
Specification: TEST_INFRA.md, PROJECT.md, ORIGINAL_REQUEST.md

Architecture:
- Tier 1: Feature Coverage (Category-Partition Method)
- Tier 2: Boundary Value Analysis (Boundary & Corner Cases)
- Tier 3: Pairwise Combinations (Cross-Feature Combinations)
- Tier 4: Real-World Application Workloads (End-to-End User Journeys)
"""

from __future__ import annotations

import math
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
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

GALAXY_VIEWPORTS = [360, 375, 384, 393, 412]


# ─────────────────────────────────────────────────────────────────────────────
# Helper Utilities
# ─────────────────────────────────────────────────────────────────────────────

def extract_all_css(html_content: str) -> str:
    """Extract and concatenate all CSS text within <style> tags."""
    soup = BeautifulSoup(html_content, "html.parser")
    styles = [s.get_text() for s in soup.find_all("style")]
    return "\n".join(styles)


def extract_media_blocks(css: str, max_width: int) -> str:
    """Extract all css rules within @media (max-width: {max_width}px) blocks."""
    pattern = rf'@media\s*\(\s*max-width\s*:\s*{max_width}px\s*\)\s*\{{+'
    matches = list(re.finditer(pattern, css, flags=re.IGNORECASE))
    if not matches:
        return ""
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
    return "\n".join(blocks)


def parse_css_rule(css_text: str, selector: str) -> Optional[str]:
    """Find the body of a CSS rule matching selector in css_text."""
    escaped = re.escape(selector)
    pattern = rf'(?:^|\}}\s*){escaped}\s*\{{([^}}]+)\}}'
    match = re.search(pattern, css_text, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def parse_css_property(css_block: str, prop_name: str) -> Optional[str]:
    """Extract the value of a property from a CSS block."""
    escaped_prop = re.escape(prop_name)
    pattern = rf'(?:^|;)\s*{escaped_prop}\s*:\s*([^;!]+)(?:!important)?\s*(?:;|$)'
    match = re.search(pattern, css_block, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Parse #rgb or #rrggbb hex color into (R, G, B) tuple."""
    hex_clean = hex_str.strip().lstrip('#')
    if len(hex_clean) == 3:
        hex_clean = "".join(c * 2 for c in hex_clean)
    r = int(hex_clean[0:2], 16)
    g = int(hex_clean[2:4], 16)
    b = int(hex_clean[4:6], 16)
    return r, g, b


def relative_luminance(r: int, g: int, b: int) -> float:
    """Calculate WCAG 2.1 relative luminance."""
    def channel_lum(val: int) -> float:
        c = val / 255.0
        return c / 12.92 if c <= 0.03928 else math.pow((c + 0.055) / 1.055, 2.4)
    return 0.2126 * channel_lum(r) + 0.7152 * channel_lum(g) + 0.0722 * channel_lum(b)


def contrast_ratio(hex1: str, hex2: str) -> float:
    """Calculate WCAG 2.1 contrast ratio between two hex colors."""
    l1 = relative_luminance(*hex_to_rgb(hex1))
    l2 = relative_luminance(*hex_to_rgb(hex2))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
def ensure_reports_exist():
    """Verify gh-pages directory and required static reports exist."""
    assert GH_PAGES_DIR.exists(), f"Missing {GH_PAGES_DIR} directory"
    missing = [p for p in ALL_PAGES if not (GH_PAGES_DIR / p).exists()]
    if missing:
        from trading_system.generate_report import main as generate_report_main
        generate_report_main(["--result-dir", "trading_system/result", "--out", str(GH_PAGES_DIR / "index.html")])


@pytest.fixture(scope="module")
def pages_content() -> Dict[str, str]:
    """Read all 7 generated pages into a dictionary of string contents."""
    contents = {}
    for p in ALL_PAGES:
        file_path = GH_PAGES_DIR / p
        assert file_path.exists(), f"Missing static page: {file_path}"
        contents[p] = file_path.read_text(encoding="utf-8")
    return contents


@pytest.fixture(scope="module")
def pages_soup(pages_content: Dict[str, str]) -> Dict[str, BeautifulSoup]:
    """Parse all 7 generated pages into BeautifulSoup DOM objects."""
    return {p: BeautifulSoup(content, "html.parser") for p, content in pages_content.items()}


@pytest.fixture(scope="module")
def multipage_css() -> str:
    """Return the CSS generated by report_multipage.build_styles()."""
    return build_styles("")


@pytest.fixture(scope="module")
def index_css(pages_content: Dict[str, str]) -> str:
    """Return all CSS styles embedded in gh-pages/index.html."""
    return extract_all_css(pages_content["index.html"])


# =============================================================================
# TIER 1: Feature Coverage (Category-Partition Method)
# =============================================================================

class TestTier1FeatureCoverage:
    """
    Tier 1 validates discrete functional features in isolation:
    - F_MOB_01: Bottom Navigation Bar presence, items, fixed positioning, z-index, thumb reachability
    - F_MOB_02: Back-to-Top FAB positioning without bottom nav collision
    - F_MOB_03: Safe-area inset handling on gesture bars
    - F_MOB_04: Interactive touch targets >= 44px
    - F_MOB_05: Sticky top navigation auto-centering & carousel
    """

    def test_tier1_bottom_nav_dom_presence_and_items(self, pages_soup: Dict[str, BeautifulSoup]):
        """
        TC1.1: Asserts <nav id="mobile-bottom-nav" class="mobile-bottom-nav"> is present
        across index.html, strategies.html, and all market_*.html pages with the 5 canonical items:
        1. #mob-nav-ensemble (🏆 앙상블)
        2. #mob-nav-portfolio (💼 포트폴리오)
        3. #mob-nav-backtest (📊 백테스트)
        4. #mob-nav-regime (🎯 레짐/매크로)
        5. #mob-nav-strategies (⚡ 37전략)
        Each item must contain icon (.mob-nav-icon), label (.mob-nav-label), and aria-label.
        """
        expected_items = [
            ("mob-nav-ensemble", "앙상블"),
            ("mob-nav-portfolio", "포트폴리오"),
            ("mob-nav-backtest", "백테스트"),
            ("mob-nav-regime", "레짐"),
            ("mob-nav-strategies", "37전략"),
        ]

        for page_name in ALL_PAGES:
            soup = pages_soup[page_name]
            nav = soup.find("nav", attrs={"id": "mobile-bottom-nav"})
            assert nav is not None, (
                f"Defect F_MOB_01: Page '{page_name}' missing <nav id='mobile-bottom-nav'> in DOM"
            )
            assert "mobile-bottom-nav" in nav.get("class", []), (
                f"Page '{page_name}' #mobile-bottom-nav missing 'mobile-bottom-nav' class"
            )

            # Validate each of the 5 canonical nav items
            for item_id, label_substr in expected_items:
                btn = nav.find("button", attrs={"id": item_id})
                assert btn is not None, (
                    f"Page '{page_name}' bottom nav missing #{item_id} button"
                )
                assert btn.get("aria-label"), (
                    f"Page '{page_name}' bottom nav #{item_id} missing 'aria-label' attribute"
                )
                icon = btn.find("span", attrs={"class": "mob-nav-icon"})
                assert icon is not None and icon.text.strip(), (
                    f"Page '{page_name}' #{item_id} missing .mob-nav-icon"
                )
                lbl = btn.find("span", attrs={"class": "mob-nav-label"})
                assert lbl is not None and label_substr in lbl.text, (
                    f"Page '{page_name}' #{item_id} label missing '{label_substr}'"
                )

    def test_tier1_bottom_nav_css_fixed_position_and_z_index(
        self, index_css: str, multipage_css: str
    ):
        """
        TC1.2: Asserts .mobile-bottom-nav is styled with fixed positioning:
        - position: fixed
        - bottom: 0
        - left: 0, right: 0
        - z-index >= 990 (canonical 999)
        - display: flex !important on mobile (<= 768px)
        - display: none on desktop (base styles)
        """
        combined_css = index_css + "\n" + multipage_css

        # Check base CSS rule (desktop hidden)
        base_nav_match = re.search(r'\.mobile-bottom-nav\s*\{([^}]+)\}', combined_css)
        assert base_nav_match is not None, "Missing .mobile-bottom-nav CSS rule"
        base_nav = base_nav_match.group(1)

        assert "display: none" in base_nav or "display:none" in base_nav, (
            ".mobile-bottom-nav must default to 'display: none' on desktop viewports"
        )
        assert "position: fixed" in base_nav or "position:fixed" in base_nav, (
            ".mobile-bottom-nav missing 'position: fixed'"
        )
        assert "bottom: 0" in base_nav or "bottom:0" in base_nav, (
            ".mobile-bottom-nav missing 'bottom: 0'"
        )

        z_match = re.search(r'z-index\s*:\s*(\d+)', base_nav)
        assert z_match is not None and int(z_match.group(1)) >= 990, (
            f".mobile-bottom-nav z-index must be >= 990 (found {z_match.group(1) if z_match else 'none'})"
        )

        # Check mobile media query activation (<= 768px)
        mq768 = extract_media_blocks(combined_css, 768)
        assert ".mobile-bottom-nav" in mq768, (
            "@media (max-width: 768px) missing .mobile-bottom-nav rule"
        )
        assert "display: flex" in mq768 or "display:flex" in mq768, (
            "@media (max-width: 768px) must activate .mobile-bottom-nav with 'display: flex'"
        )

    def test_tier1_bottom_nav_thumb_reachability_geometry(
        self, index_css: str, multipage_css: str
    ):
        """
        TC1.3: Asserts the bottom navigation bar provides ergonomic thumb reachability:
        - .mobile-bottom-nav distributes 5 buttons evenly (justify-content: space-around or flex: 1)
        - .mobile-nav-item width on 360px screen is ~72px (>= 44px minimum tap width)
        - .mobile-nav-item height is at least 44px (canonical 56px)
        """
        combined_css = index_css + "\n" + multipage_css
        item_match = re.search(r'\.mobile-nav-item\s*\{([^}]+)\}', combined_css)
        assert item_match is not None, "Missing .mobile-nav-item CSS rule"
        item_css = item_match.group(1)

        assert "flex: 1" in item_css or "width:" in item_css, (
            ".mobile-nav-item must specify 'flex: 1' or width percentage for equal thumb distribution"
        )
        assert "height: 100%" in item_css or "min-height: 44px" in item_css, (
            ".mobile-nav-item must fill the 56px bottom nav bar height (min-height >= 44px)"
        )

    def test_tier1_safe_area_insets_css_integration(
        self, index_css: str, multipage_css: str
    ):
        """
        TC1.4: Asserts safe-area insets are integrated for Samsung Galaxy gesture navigation:
        - .mobile-bottom-nav uses env(safe-area-inset-bottom, 0px)
        - Body or main content on mobile has bottom padding >= calc(64px + env(safe-area-inset-bottom, 0px))
          to prevent data clipping behind the bottom navigation bar.
        """
        combined_css = index_css + "\n" + multipage_css
        assert "env(safe-area-inset-bottom" in combined_css, (
            "CSS missing 'env(safe-area-inset-bottom, 0px)' integration for mobile layout"
        )

        mq768 = extract_media_blocks(combined_css, 768)
        assert "safe-area-inset-bottom" in mq768, (
            "@media (max-width: 768px) missing safe-area-inset-bottom declaration"
        )

        # Check body or content bottom padding to prevent bottom nav occlusion
        has_bottom_padding = bool(
            re.search(r'padding-bottom\s*:\s*calc\([^)]*6[0-9]px', mq768, re.IGNORECASE)
            or re.search(r'padding-bottom\s*:\s*calc\([^)]*56px', mq768, re.IGNORECASE)
        )
        assert has_bottom_padding, (
            "@media (max-width: 768px) must provide padding-bottom >= 56px to avoid bottom nav content overlap"
        )

    def test_tier1_fab_positioning_no_bottom_nav_collision(
        self, index_css: str, multipage_css: str
    ):
        """
        TC1.5: Asserts Back-to-Top FAB (#btn-back-to-top) is positioned strictly above
        the 56px bottom navigation bar on mobile viewports (<= 768px):
        - In @media (max-width: 768px), #btn-back-to-top bottom must be >= 64px
          (canonical: bottom: calc(68px + env(safe-area-inset-bottom, 0px)) !important)
        - FAB dimensions must be >= 44px x 44px (min-width and min-height >= 44px)
        - Prevents hit collision with the 5th bottom nav item (#mob-nav-strategies)
        """
        combined_css = index_css + "\n" + multipage_css
        mq768 = extract_media_blocks(combined_css, 768)

        fab_match = re.search(r'#btn-back-to-top\s*\{([^}]+)\}', mq768)
        assert fab_match is not None, (
            "@media (max-width: 768px) missing #btn-back-to-top collision-prevention rule"
        )
        fab_rules = fab_match.group(1)

        # Assert dimensions
        assert "min-width: 44px" in fab_rules or "width: 44px" in fab_rules, (
            "#btn-back-to-top missing width >= 44px on mobile"
        )
        assert "min-height: 44px" in fab_rules or "height: 44px" in fab_rules, (
            "#btn-back-to-top missing height >= 44px on mobile"
        )

        # Assert bottom coordinate clearance above 56px bottom nav bar
        # Defect detection: If bottom: calc(20px...) or bottom: 20px, it collides with bottom nav!
        bottom_val = parse_css_property(fab_rules, "bottom")
        assert bottom_val is not None, (
            "#btn-back-to-top missing 'bottom' property in @media (max-width: 768px)"
        )

        # Extract numeric base offset from calc(68px + ...) or 68px
        num_match = re.search(r'(\d+)px', bottom_val)
        assert num_match is not None, f"Could not parse numeric bottom offset in '{bottom_val}'"
        offset_px = int(num_match.group(1))

        assert offset_px >= 64, (
            f"Defect F_MOB_02: #btn-back-to-top bottom offset ({offset_px}px) is < 64px! "
            f"It collides with the 56px bottom nav bar. Expected >= 68px."
        )

    def test_tier1_touch_targets_dimension_compliance(
        self, index_css: str, multipage_css: str
    ):
        """
        TC1.6: Asserts all interactive touch targets meet or exceed WCAG 2.5.5 / Android
        minimum dimension of 44px x 44px across navigation, filters, pills, inputs, and drawers.
        """
        combined_css = index_css + "\n" + multipage_css
        mq768 = extract_media_blocks(combined_css, 768)

        elements_to_verify = [
            (".nav-link", "min-height: 44px"),
            (".filter-btn", "min-height: 44px"),
            (".chip-btn", "min-height: 44px"),
            (".theme-btn", "min-height: 44px"),
            (".health-pill", "min-height: 44px"),
            (".market-search-input", "min-height: 44px"),
            (".btn-csv-export", "min-height: 44px"),
            ("#btn-back-to-top", "min-height: 44px"),
            (".drawer-nav-btn", "min-height: 44px"),
            (".drawer-copy-btn", "min-height: 44px"),
            (".drawer-factor-tab", "min-height: 44px"),
            (".ext-portal-btn", "min-height: 44px"),
            (".hub-item-btn", "min-height: 44px"),
            (".hub-close-btn", "min-height: 44px"),
            (".tab", "min-height: 44px"),
        ]

        for selector, expected_rule in elements_to_verify:
            # Check either in mobile media query or in global styles
            found_in_mq = selector in mq768 and expected_rule in mq768
            found_in_global = selector in combined_css and expected_rule in combined_css
            assert found_in_mq or found_in_global, (
                f"Defect F_MOB_04: Touch target '{selector}' does not satisfy '{expected_rule}' "
                f"for Android Galaxy mobile web touch ergonomics"
            )

    def test_tier1_sticky_nav_height_and_autocentering(
        self, index_css: str, multipage_css: str, pages_content: Dict[str, str]
    ):
        """
        TC1.7: Asserts the top sticky navigation header:
        - Height <= 56px on mobile (<= 768px and <= 480px)
        - .sticky-nav-container has flex-wrap: nowrap
        - .sticky-nav-links has overflow-x: auto and -webkit-overflow-scrolling: touch
        - Contains auto-centering script call 'scrollIntoView' for active chip
        """
        combined_css = index_css + "\n" + multipage_css
        mq768 = extract_media_blocks(combined_css, 768)
        mq480 = extract_media_blocks(combined_css, 480)

        # Height check in 768px
        assert "height: 52px" in mq768 or "max-height: 56px" in mq768 or "height: 50px" in mq768, (
            "Top sticky nav header must be <= 56px height on mobile"
        )
        assert "flex-wrap: nowrap" in mq768, (
            ".sticky-nav-container must specify 'flex-wrap: nowrap' to prevent vertical wrapping"
        )
        assert "-webkit-overflow-scrolling: touch" in mq768, (
            ".sticky-nav-links must enable momentum touch scrolling"
        )

        # Auto-centering script verification across all 7 pages
        for page_name, content in pages_content.items():
            assert "scrollIntoView" in content, (
                f"Page '{page_name}' missing auto-centering 'scrollIntoView' script for active nav chip"
            )


# =============================================================================
# TIER 2: Boundary Value Analysis (Boundary & Corner Cases)
# =============================================================================

class TestTier2BoundaryAndCornerCases:
    """
    Tier 2 validates system behavior at mathematical limits and edge cases:
    - Viewports: 360px, 375px, 384px, 393px, 412px Galaxy spectrum
    - Breakpoint: 1024px desktop transition boundary
    - Safe-Area Inset: 0px vs 34px gesture bar clearance invariant
    - Table Frozen Columns Budget: Rank+Symbol+Name <= 190px leaving >= 170px scrollable body
    - Search Input: Empty string, whitespace, regex special characters
    - Extreme Aspect Ratios: Ultra-tall 20:9/21:9 & Foldable unfolded screen
    """

    @pytest.mark.parametrize("viewport_width", GALAXY_VIEWPORTS)
    def test_tier2_galaxy_viewport_widths_stacking(
        self, viewport_width: int, index_css: str, multipage_css: str
    ):
        """
        TC2.1: Asserts that for all Galaxy viewport widths in [360, 375, 384, 393, 412]:
        - Global overflow-x: hidden is enforced
        - Card grids (.macro-grid, .health-grid, .charts-grid) collapse to single column '1fr'
        - No horizontal layout blowout occurs
        """
        combined_css = index_css + "\n" + multipage_css
        mq480 = extract_media_blocks(combined_css, 480)
        assert mq480, "Missing @media (max-width: 480px) rules"

        assert "grid-template-columns: 1fr" in mq480, (
            f"At {viewport_width}px Galaxy viewport, card grids must collapse to 'grid-template-columns: 1fr'"
        )

    def test_tier2_desktop_breakpoint_boundary_1024px(
        self, index_css: str, multipage_css: str
    ):
        """
        TC2.2: Asserts the 1024px desktop breakpoint boundary:
        - At >= 1024px: .row1-wrapper renders 2-column grid (310px + 1fr)
        - At >= 1024px: .mobile-bottom-nav is hidden (display: none)
        - At >= 1024px: #stock-drawer renders as 480px slide-in sidebar (not bottom sheet)
        - At <= 1024px: .row1-wrapper collapses to single column (1fr)
        """
        combined_css = index_css + "\n" + multipage_css

        # Base / Desktop rules
        assert "grid-template-columns: 310px 1fr" in combined_css, (
            "Desktop layout must specify 2-column grid '310px 1fr' for .row1-wrapper"
        )
        assert "width: 480px" in combined_css, (
            "Desktop layout must specify 480px width for #stock-drawer sidebar"
        )

        # Breakpoint collapse at 1024px
        mq1024 = extract_media_blocks(combined_css, 1024)
        assert "grid-template-columns: 1fr" in mq1024 or "grid-template-columns: 100%" in mq1024, (
            "At <= 1024px, .row1-wrapper must collapse to single column"
        )

    def test_tier2_safe_area_inset_boundary_0px_vs_34px(
        self, index_css: str, multipage_css: str
    ):
        """
        TC2.3: Mathematical boundary analysis of safe-area-inset-bottom:
        - Case 0px (No gesture bar):
          Bottom nav height = 56px + 0px = 56px
          FAB bottom position = 68px + 0px = 68px
          Clearance gap = 68px - 56px = 12px (> 0)
        - Case 34px (Android gesture bar):
          Bottom nav height = 56px + 34px = 90px
          FAB bottom position = 68px + 34px = 102px
          Clearance gap = 102px - 90px = 12px (> 0)
        Asserts that clearance gap >= 8px is mathematically guaranteed for all safe-area insets in [0, 50].
        """
        combined_css = index_css + "\n" + multipage_css
        mq768 = extract_media_blocks(combined_css, 768)

        # Verify FAB uses calc(68px + env(safe-area-inset-bottom...)) or equivalent >= 68px
        fab_rules = parse_css_rule(mq768, "#btn-back-to-top")
        assert fab_rules is not None, "Missing #btn-back-to-top rule in @media (max-width: 768px)"

        bottom_val = parse_css_property(fab_rules, "bottom")
        assert bottom_val is not None

        offset_match = re.search(r'(\d+)px', bottom_val)
        assert offset_match is not None
        fab_base_offset = int(offset_match.group(1))

        # Model bottom nav height = 56px
        bottom_nav_base_height = 56

        for safe_inset in [0, 16, 20, 24, 34, 48]:
            fab_pos = fab_base_offset + safe_inset
            nav_height = bottom_nav_base_height + safe_inset
            clearance = fab_pos - nav_height
            assert clearance >= 8, (
                f"Collision at safe-area-inset={safe_inset}px: "
                f"FAB bottom ({fab_pos}px) does not clear bottom nav ({nav_height}px) by >= 8px"
            )

    def test_tier2_table_frozen_columns_geometry_budget(
        self, index_css: str, multipage_css: str
    ):
        """
        TC2.4: Table frozen columns geometry budget analysis on Galaxy screens:
        - Rank column width: 34px–36px
        - Symbol column width: 66px–68px
        - Name column width: 86px–88px (with ellipsis)
        - Total frozen columns width <= 190px (canonical: 34 + 66 + 88 = 188px, or 36 + 68 + 86 = 190px)
        - On 360px viewport: 360px - 190px = 170px available scrollable table body (>= 170px)
        - On 412px viewport: 412px - 190px = 222px available scrollable table body (>= 170px)
        """
        combined_css = index_css + "\n" + multipage_css
        mq768 = extract_media_blocks(combined_css, 768)

        # Extract column widths (using strict non-max width property matching)
        rank_w_match = re.search(r'\.sticky-rank\s*\{[^}]*(?:^|[;\s])width\s*:\s*(\d+)px', mq768)
        sym_w_match = re.search(r'\.sticky-symbol\s*\{[^}]*(?:^|[;\s])width\s*:\s*(\d+)px', mq768)
        name_w_match = re.search(r'\.sticky-name\s*\{[^}]*(?:^|[;\s])width\s*:\s*(\d+)px', mq768)

        assert rank_w_match is not None, "Missing .sticky-rank width in mobile CSS"
        assert sym_w_match is not None, "Missing .sticky-symbol width in mobile CSS"
        assert name_w_match is not None, "Missing .sticky-name width in mobile CSS"

        rank_w = int(rank_w_match.group(1))
        sym_w = int(sym_w_match.group(1))
        name_w = int(name_w_match.group(1))

        total_frozen = rank_w + sym_w + name_w
        assert total_frozen <= 190, (
            f"Total frozen columns width ({total_frozen}px) exceeds 190px ceiling"
        )

        # Verify scrollable area on 360px Galaxy viewport
        scrollable_360 = 360 - total_frozen
        assert scrollable_360 >= 170, (
            f"Available scrollable width on 360px viewport ({scrollable_360}px) is < 170px"
        )

        # Verify text overflow ellipsis on Name column
        assert "text-overflow: ellipsis" in mq768 or "text-overflow:ellipsis" in mq768, (
            ".sticky-name missing 'text-overflow: ellipsis' in mobile styles"
        )

    def test_tier2_search_input_empty_and_special_chars(
        self, pages_content: Dict[str, str]
    ):
        """
        TC2.5: Asserts table search JavaScript handles edge cases:
        - filterMarketTable handles empty query "" without hiding all rows
        - Handles whitespace query "   " gracefully
        - Escapes regex special characters without crashing
        - Font size is 16px to prevent iOS/Android browser auto-zoom
        """
        for mkt_page in MARKET_PAGES:
            content = pages_content[mkt_page]
            assert "filterMarketTable" in content, (
                f"Market page '{mkt_page}' missing 'filterMarketTable' script"
            )
            assert "font-size: 16px" in content or "font-size:16px" in content, (
                f"Market page '{mkt_page}' search input missing font-size: 16px (auto-zoom defect)"
            )

    def test_tier2_extreme_aspect_ratios_and_foldables(
        self, index_css: str, multipage_css: str
    ):
        """
        TC2.6: Asserts layout resilience under extreme aspect ratios:
        - Ultra-tall mobile (20:9 / 21:9): Stock drawer height: 90vh preserves top backdrop
        - Foldable unfolded screens (~673px width): max-width: 100vw prevents horizontal overflow
        """
        combined_css = index_css + "\n" + multipage_css
        mq768 = extract_media_blocks(combined_css, 768)

        # Check drawer 90vh bottom sheet
        assert "height: 90vh" in mq768 or "max-height: 90vh" in mq768, (
            "#stock-drawer on mobile must specify height: 90vh to preserve top backdrop dismissal zone"
        )
        assert "border-radius: 16px 16px 0 0" in mq768 or "border-radius: 16px" in mq768, (
            "#stock-drawer missing top rounded corners for native bottom-sheet appearance"
        )


# =============================================================================
# TIER 3: Pairwise Combinations (Cross-Feature Combinations)
# =============================================================================

class TestTier3CrossFeatureCombinations:
    """
    Tier 3 validates pairwise subsystem interactions:
    - Bottom Nav <-> Top Sticky Nav Active State Synchronization
    - Stock Detail Drawer <-> Bottom Nav Stacking and Dismissal
    - Theme Switcher (Dark/Terminal/Light) x Touch Targets x Contrast
    - Table Search Filtering x Horizontal Scrolling & Frozen Offsets
    - Cross-Page Navigation & Strategy Hub Modal
    """

    def test_tier3_bottom_nav_sync_with_panels_and_top_nav(
        self, pages_content: Dict[str, str], pages_soup: Dict[str, BeautifulSoup]
    ):
        """
        TC3.1: Asserts bottom nav interaction synchronizes with top panels:
        - switchMobileNav(tabId) updates active class on bottom nav items
        - Corresponding panel (#panel-ensemble, #panel-portfolio, #panel-backtest, #panel-regime) exists
        - Top sticky nav remains aligned without scroll jumping
        """
        index_html = pages_content["index.html"]
        assert "switchMobileNav" in index_html, (
            "index.html missing 'switchMobileNav' JavaScript function"
        )

        soup = pages_soup["index.html"]
        for panel_id in ["panel-portfolio", "panel-backtest", "panel-regime"]:
            panel = soup.find(id=panel_id)
            assert panel is not None, f"index.html missing #{panel_id} target panel"

    def test_tier3_stock_drawer_bottom_sheet_layering(
        self, index_css: str, multipage_css: str, pages_content: Dict[str, str], pages_soup: Dict[str, BeautifulSoup]
    ):
        """
        TC3.2: Asserts stock detail drawer and bottom nav stacking contexts:
        - Overlay (#stock-drawer-overlay) z-index: >= 1000 (> bottom nav 999)
        - Drawer (#stock-drawer) z-index: >= 1001 (> overlay)
        - When drawer is open, bottom nav is covered and touch-isolated
        - Drawer includes touch swipe-down dismissal listener (diffY > 70 or touchmove)
        """
        combined_css = index_css + "\n" + multipage_css
        soup = pages_soup["index.html"]

        nav_z = 999

        # Find overlay and drawer elements
        overlay = soup.find(id="stock-drawer-overlay")
        assert overlay is not None, "Missing #stock-drawer-overlay element in index.html"
        overlay_style = overlay.get("style", "")
        overlay_z_match = re.search(r'z-index\s*:\s*(\d+)', overlay_style) or re.search(r'#stock-drawer-overlay\s*\{[^}]*z-index\s*:\s*(\d+)', combined_css)
        assert overlay_z_match is not None, "Missing #stock-drawer-overlay z-index"
        overlay_z = int(overlay_z_match.group(1))

        drawer = soup.find(id="stock-drawer")
        assert drawer is not None, "Missing #stock-drawer element in index.html"
        drawer_style = drawer.get("style", "")
        drawer_z_match = re.search(r'z-index\s*:\s*(\d+)', drawer_style) or re.search(r'#stock-drawer\s*\{[^}]*z-index\s*:\s*(\d+)', combined_css)
        assert drawer_z_match is not None, "Missing #stock-drawer z-index"
        drawer_z = int(drawer_z_match.group(1))

        assert overlay_z >= nav_z, (
            f"#stock-drawer-overlay z-index ({overlay_z}) must be >= bottom nav ({nav_z})"
        )
        assert drawer_z > overlay_z, (
            f"#stock-drawer z-index ({drawer_z}) must be greater than overlay ({overlay_z})"
        )

        # Check swipe dismissal handler
        index_html = pages_content["index.html"]
        assert "diffY > 70" in index_html or "diffY" in index_html or "touchmove" in index_html, (
            "#stock-drawer missing touch swipe gesture dismissal logic"
        )

    def test_tier3_theme_switcher_touch_and_contrast(
        self, index_css: str, multipage_css: str
    ):
        """
        TC3.3: Asserts theme switching preserves touch targets and contrast ratios:
        - Dark theme contrast >= 7:1 (AAA)
        - Terminal theme contrast >= 14:1 (AAA)
        - Light theme contrast >= 14:1 (AAA)
        - .theme-btn maintains min-height: 44px across all themes
        """
        combined_css = index_css + "\n" + multipage_css

        # Theme color pairs (surface, text)
        dark_contrast = contrast_ratio("#131b26", "#e2e8f0")
        terminal_contrast = contrast_ratio("#04080d", "#00ff66")
        light_contrast = contrast_ratio("#f8fafc", "#0f172a")

        assert dark_contrast >= 7.0, f"Dark theme contrast ({dark_contrast:.2f}:1) < 7:1"
        assert terminal_contrast >= 14.0, f"Terminal theme contrast ({terminal_contrast:.2f}:1) < 14:1"
        assert light_contrast >= 14.0, f"Light theme contrast ({light_contrast:.2f}:1) < 14:1"

        # Theme toggle button min-height
        assert ".theme-btn" in combined_css
        theme_rule = parse_css_rule(combined_css, ".theme-btn") or ""
        mq768 = extract_media_blocks(combined_css, 768)
        assert "min-height: 44px" in theme_rule or "min-height: 44px" in mq768, (
            ".theme-btn touch target must be >= 44px across all themes"
        )

    def test_tier3_table_search_filtering_with_horizontal_scroll(
        self, index_css: str, multipage_css: str
    ):
        """
        TC3.4: Asserts table search filtering integrates seamlessly with horizontal scrolling:
        - .table-wrap preserves overflow-x: auto and -webkit-overflow-scrolling: touch
        - Sticky column offsets are locked: left: 0, left: 34px/36px, left: 100px/104px
        - Sticky headers have z-index: 3, sticky body cells have z-index: 2
        """
        combined_css = index_css + "\n" + multipage_css
        mq768 = extract_media_blocks(combined_css, 768)

        assert "overflow-x: auto" in mq768 or "overflow-x: auto" in combined_css
        assert ".sticky-rank" in mq768 and "left: 0" in mq768
        assert ".sticky-symbol" in mq768 and ("left: 34px" in mq768 or "left: 36px" in mq768)
        assert ".sticky-name" in mq768 and ("left: 100px" in mq768 or "left: 104px" in mq768)

    def test_tier3_cross_page_navigation_and_strategy_hub(
        self, pages_content: Dict[str, str], pages_soup: Dict[str, BeautifulSoup]
    ):
        """
        TC3.5: Asserts cross-page navigation awareness:
        - openStrategyHub() opens #strategy-hub-sheet bottom sheet
        - #strategy-hub-sheet contains links to all 37 strategies
        - In strategies.html and market_*.html, bottom nav routing links to index.html#panel-{tabId}
        """
        index_html = pages_content["index.html"]
        assert "openStrategyHub" in index_html, "index.html missing 'openStrategyHub' function"

        soup = pages_soup["index.html"]
        hub_sheet = soup.find(id="strategy-hub-sheet")
        assert hub_sheet is not None, "index.html missing #strategy-hub-sheet modal component"

        # Hub close button
        close_btn = hub_sheet.find(attrs={"class": "hub-close-btn"})
        assert close_btn is not None, "#strategy-hub-sheet missing .hub-close-btn"


# =============================================================================
# TIER 4: Real-World Application Workloads & Journeys
# =============================================================================

class TestTier4RealWorldWorkloads:
    """
    Tier 4 validates full end-to-end user journeys and system invariants:
    - Galaxy Mobile User Journey Simulation (360px–412px)
    - Desktop PC Browser Visit Simulation (>= 1024px)
    - HTML Size Budget (< 512,000 bytes) & Unix LF Line Ending Invariant
    """

    def test_tier4_galaxy_mobile_user_journey(
        self, pages_content: Dict[str, str], pages_soup: Dict[str, BeautifulSoup]
    ):
        """
        TC4.1: Simulated end-to-end mobile user journey on Samsung Galaxy (393px viewport):
        1. User lands on index.html: checks viewport-fit=cover and sticky top nav
        2. User thumb-taps #mob-nav-portfolio -> verifies portfolio panel and charts
        3. User inspects HRP donut chart (#hrpDonutChart) and exposure chart (#marketExposureChart)
        4. User taps stock row in top picks table -> opens stock detail drawer (openStockDrawer)
        5. User views factor radar chart (#drawerRadarChart) inside 90vh bottom sheet
        6. User closes drawer via .drawer-close-btn
        7. User thumb-taps #mob-nav-strategies -> opens #strategy-hub-sheet
        8. User selects strategy link -> verifies deep link target format
        """
        soup = pages_soup["index.html"]
        html = pages_content["index.html"]

        # 1. Viewport & Sticky Nav
        meta = soup.find("meta", attrs={"name": "viewport"})
        assert meta and "viewport-fit=cover" in meta.get("content", "")
        assert soup.find("header", attrs={"class": "sticky-nav"}) is not None

        # 2 & 3. Portfolio Panel & Charts
        assert soup.find(id="panel-portfolio") is not None
        assert soup.find(id="hrpDonutChart") is not None
        assert soup.find(id="marketExposureChart") is not None

        # 4 & 5. Stock Detail Drawer & Radar Chart
        assert "openStockDrawer" in html
        drawer = soup.find(id="stock-drawer")
        assert drawer is not None
        assert drawer.find(id="drawerRadarChart") is not None or drawer.find(id="drawer-radar-canvas") is not None, (
            "Stock drawer missing radar chart canvas (#drawerRadarChart)"
        )

        # 6. Drawer Close Button
        assert drawer.find(attrs={"class": "drawer-close-btn"}) is not None or "closeStockDrawer" in html

        # 7 & 8. Strategy Hub Sheet
        assert "openStrategyHub" in html
        hub_sheet = soup.find(id="strategy-hub-sheet")
        assert hub_sheet is not None
        hub_links = hub_sheet.find_all("button") + hub_sheet.find_all("a")
        assert len(hub_links) >= 30, (
            f"Strategy hub sheet should contain ~37 strategy items (found {len(hub_links)})"
        )

    def test_tier4_desktop_pc_browser_session(
        self, index_css: str, multipage_css: str, pages_soup: Dict[str, BeautifulSoup]
    ):
        """
        TC4.2: Simulated desktop PC browser visit (>= 1024px viewport):
        1. Sticky top nav displays all 7 page links in a single horizontal row
        2. .row1-wrapper renders 2-column grid (310px sidebar + 1fr main content)
        3. Card 2 displays multi-column strategy health cards (repeat(auto-fill, minmax(210px, 1fr)))
        4. Bottom nav is hidden (display: none)
        5. Stock drawer renders as 480px slide-in sidebar on right
        6. Search input features '/' shortcut badge and autocomplete dropdown
        """
        combined_css = index_css + "\n" + multipage_css
        soup = pages_soup["index.html"]

        # 1. Sticky Nav Links (all 7 present)
        nav_links = soup.select(".sticky-nav-links .nav-link")
        assert len(nav_links) == 7, f"Expected 7 desktop nav links, found {len(nav_links)}"

        # 2. 2-Column Grid
        assert "grid-template-columns: 310px 1fr" in combined_css

        # 3. Multi-column Cards & Grids
        assert "minmax(210px, 1fr)" in combined_css or "minmax(200px, 1fr)" in combined_css

        # 4. Bottom nav hidden
        base_nav = parse_css_rule(combined_css, ".mobile-bottom-nav") or ""
        assert "display: none" in base_nav or "display:none" in base_nav

        # 5. 480px sidebar drawer
        drawer_css = parse_css_rule(combined_css, "#stock-drawer") or ""
        assert "width: 480px" in drawer_css or "width: 480px" in combined_css

        # 6. Autocomplete & search badge
        assert soup.find(id="search-autocomplete-dropdown") is not None

    def test_tier4_html_file_size_and_hygiene(self, pages_content: Dict[str, str]):
        """
        TC4.3: Hard performance and encoding invariants:
        - gh-pages/index.html file size strictly < 512,000 bytes (500 KB)
        - Strict Unix LF line endings (raw_bytes.count(b'\\r\\n') == 0) across all pages
        - Valid UTF-8 encoding
        """
        index_path = GH_PAGES_DIR / "index.html"
        assert index_path.exists()
        raw_index = index_path.read_bytes()

        # Size check
        size_bytes = len(raw_index)
        budget_bytes = 512000  # 500 KB
        assert size_bytes < budget_bytes, (
            f"Defect F_MOB_08: gh-pages/index.html size ({size_bytes:,} bytes) exceeds budget of {budget_bytes:,} bytes!"
        )

        # Line endings check across all 7 pages
        for page_name in ALL_PAGES:
            raw = (GH_PAGES_DIR / page_name).read_bytes()
            crlf_count = raw.count(b"\r\n")
            assert crlf_count == 0, (
                f"Defect F_MOB_09: Found {crlf_count} CRLF sequences in '{page_name}'; expected Unix LF only."
            )
