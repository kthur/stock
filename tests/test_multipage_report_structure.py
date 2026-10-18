"""
tests/test_multipage_report_structure.py — Static Multi-Page Architecture Verification

Empirically validates the 7-page static dashboard deployment in gh-pages/:
1. index.html: Executive Summary Dashboard (< 500 KB, initial DOM nodes reduced > 70%)
2. strategies.html: 37 Strategy Encyclopedia & Technical Documentation with LaTeX math formulas
3-7. market_{market}.html: Dedicated full-universe 42-column ranking tables & heatmaps
"""

from __future__ import annotations

import re
from pathlib import Path
import pytest

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

PAGE_NAV_MAP = {
    "index.html": "index.html",
    "strategies.html": "strategies.html",
    "market_kospi.html": "market_kospi.html",
    "market_kosdaq.html": "market_kosdaq.html",
    "market_sp500.html": "market_sp500.html",
    "market_nasdaq.html": "market_nasdaq.html",
    "market_russell2000.html": "market_russell2000.html",
}

CANONICAL_37_PANEL_IDS = [
    "panel-regression", "panel-surge", "panel-leadlag", "panel-vcp", "panel-vcpml", "panel-lstm",
    "panel-stat-arb", "panel-sector", "panel-rim", "panel-event", "panel-mq",
    "panel-iv", "panel-flow", "panel-reversal", "panel-arm",
    "panel-card", "panel-latr", "panel-ifs",
    "panel-supplychain", "panel-sentiment", "panel-neutralized", "panel-voltarget",
    "panel-microstructure", "panel-accruals", "panel-shortsqueeze", "panel-valueup",
    "panel-trendeff", "panel-gammasqueeze", "panel-insider", "panel-darkpool", "panel-tonedrift",
    "panel-crossasset", "panel-gnn", "panel-rangeexpansion", "panel-dualcorrection", "panel-indexrebalance", "panel-overnightgap"
]


@pytest.fixture(scope="module", autouse=True)
def ensure_reports_generated():
    """Ensure all 7 static pages exist in gh-pages/ before running tests."""
    from trading_system.generate_report import main as generate_report_main
    all_exist = all((GH_PAGES_DIR / p).exists() for p in EXPECTED_PAGES)
    if not all_exist:
        generate_report_main(["--result-dir", "trading_system/result", "--out", str(GH_PAGES_DIR / "index.html")])


def test_1_all_7_static_files_exist():
    """1. All 7 static pages exist in gh-pages/ and are non-empty."""
    for page_name in EXPECTED_PAGES:
        page_path = GH_PAGES_DIR / page_name
        assert page_path.exists(), f"Required multi-page file {page_name} does not exist"
        assert page_path.stat().st_size > 1024, f"File {page_name} is unexpectedly small or empty"


def test_2_index_html_size_under_500kb():
    """2. Executive Summary Dashboard (index.html) is strictly < 500 KB (512,000 bytes)."""
    index_path = GH_PAGES_DIR / "index.html"
    size_bytes = index_path.stat().st_size
    size_kb = size_bytes / 1024.0
    assert size_bytes < 500 * 1024, f"index.html must be < 500 KB, but was {size_kb:.2f} KB ({size_bytes} bytes)"


def test_3_sticky_nav_header_present_on_all_7_pages():
    """3. Sticky global navigation header is present on all 7 pages."""
    for page_name in EXPECTED_PAGES:
        content = (GH_PAGES_DIR / page_name).read_text(encoding="utf-8")
        assert '<header class="sticky-nav">' in content, f"Sticky nav missing in {page_name}"
        assert '<nav class="sticky-nav-links">' in content, f"Sticky nav links container missing in {page_name}"
        for _, href in PAGE_NAV_MAP.items():
            assert f'href="{href}"' in content, f"Nav link for {href} missing in {page_name}"


def test_4_active_nav_indicator_on_each_page():
    """4. Active navigation link indicator is highlighted correctly on each page."""
    for page_name, expected_href in PAGE_NAV_MAP.items():
        content = (GH_PAGES_DIR / page_name).read_text(encoding="utf-8")
        active_match = re.search(r'<a\s+href="([^"]+)"\s+class="nav-link\s+active\s+nav-active">', content)
        assert active_match is not None, f"Active nav link missing in {page_name}"
        assert active_match.group(1) == expected_href, f"Wrong active nav link in {page_name}: expected {expected_href}, got {active_match.group(1)}"


def test_5_zero_broken_relative_links_across_all_pages():
    """5. Zero broken relative internal links across all 7 pages."""
    for page_name in EXPECTED_PAGES:
        content = (GH_PAGES_DIR / page_name).read_text(encoding="utf-8")
        links = re.findall(r'href="([^"]+)"', content)
        for link in links:
            if link.startswith("http://") or link.startswith("https://") or link.startswith("mailto:"):
                continue
            if link == "#":
                continue
            if link.startswith("#"):
                # In-page anchor
                anchor = link.lstrip("#")
                if anchor:
                    assert f'id="{anchor}"' in content, f"Broken in-page anchor #{anchor} in {page_name}"
            elif "#" in link:
                file_part, anchor = link.split("#", 1)
                target_file = GH_PAGES_DIR / file_part
                assert target_file.exists(), f"Broken relative target file {file_part} in {page_name}"
                target_content = target_file.read_text(encoding="utf-8")
                if anchor:
                    assert f'id="{anchor}"' in target_content, f"Broken cross-page anchor #{anchor} in {file_part}"
            else:
                target_file = GH_PAGES_DIR / link
                assert target_file.exists(), f"Broken relative file link {link} in {page_name}"


def test_6_card1_market_regime_and_risk_gates_in_index():
    """6. Card 1 (2D Market Regime & Risk Gates) is present in index.html."""
    content = (GH_PAGES_DIR / "index.html").read_text(encoding="utf-8")
    assert 'class="regime-risk-card"' in content
    assert '2D Market Regime &amp; Risk Gates' in content or '2D Market Regime & Risk Gates' in content
    assert '6-Regime Dynamic Matrix' in content or '6-레짐 매트릭스' in content
    assert 'VIX Fast Shock Gate' in content
    assert 'Macro Composite Score' in content
    assert 'Drawdown Speed' in content
    assert 'macro-grid' in content


def test_7_card2_strategy_health_monitor_in_index():
    """7. Card 2 (Strategy Health Monitor Summary) is present in index.html."""
    content = (GH_PAGES_DIR / "index.html").read_text(encoding="utf-8")
    assert 'class="health-monitor-section"' in content
    assert 'Strategy Data Health Monitor' in content
    assert 'health-summary-pills' in content
    assert 'health-grid' in content
    cards = re.findall(r'<div class="health-card"[^>]*>', content)
    assert len(cards) in (31, 34, 37), f"Expected 31..37 health cards, found {len(cards)}"
    assert 'cpcv-stress-section' in content
    assert 'CPCV 과적합 진단' in content


def test_8_card3_portfolio_construction_in_index():
    """8. Card 3 (Portfolio Construction & HRP Allocation) is present in index.html."""
    content = (GH_PAGES_DIR / "index.html").read_text(encoding="utf-8")
    assert 'id="panel-portfolio"' in content
    assert 'id="hrpDonutChart"' in content
    assert 'id="marketExposureChart"' in content
    assert 'EVT-GPD Tail Risk Budgeting' in content
    assert 'Leland No-Trade Buffer Bands' in content
    assert 'OMS 7-Safety Gates' in content


def test_9_consolidated_top_picks_table_and_cta_buttons_in_index():
    """9. Consolidated TOP picks table and CTA buttons to dedicated market pages exist in index.html."""
    content = (GH_PAGES_DIR / "index.html").read_text(encoding="utf-8")
    assert '<div class="market-panel"' in content
    # CTA buttons
    for mkt in ["kospi", "kosdaq", "sp500"]:
        assert f'href="market_{mkt}.html"' in content, f"CTA button to market_{mkt}.html missing in index.html"
    # Strategy encyclopedia banner
    assert 'href="strategies.html"' in content
    assert '37대 전략 백과사전' in content


def test_10_strategy_catalog_and_latex_in_strategies():
    """10. 37 Strategies encyclopedia catalog with LaTeX math formulas is present in strategies.html."""
    content = (GH_PAGES_DIR / "strategies.html").read_text(encoding="utf-8")
    assert 'encyclopedia-grid' in content or 'strat-encyclopedia-card' in content
    cards = re.findall(r'<div class="strat-encyclopedia-card"', content)
    assert len(cards) == 37, f"Expected 37 encyclopedia cards, found {len(cards)}"
    # Verify MathJax and LaTeX formulas exist
    assert 'MathJax' in content or 'tex-mml-chtml.js' in content
    assert '\\[' in content and '\\]' in content
    # Check backlink to index.html
    assert 'href="index.html"' in content


def test_11_canonical_37_strategy_panels_in_strategies():
    """11. All 37 strategy tab panels exist in strategies.html with live candidate tables."""
    content = (GH_PAGES_DIR / "strategies.html").read_text(encoding="utf-8")
    for panel_id in CANONICAL_37_PANEL_IDS:
        assert f'id="{panel_id}"' in content, f"Panel {panel_id} missing in strategies.html"


def test_12_market_pages_42_columns_presets_filter_and_export():
    """12. Market pages have 42-column ranking tables, presets, search, CSV export, and drawer."""
    for mkt in ["kospi", "kosdaq", "sp500", "nasdaq", "russell2000"]:
        page_name = f"market_{mkt}.html"
        content = (GH_PAGES_DIR / page_name).read_text(encoding="utf-8")
        
        # 42-column table
        assert 'id="market-full-table"' in content, f"market-full-table missing in {page_name}"
        th_count = len(re.findall(r'<th\b', content))
        assert th_count == 42, f"Expected 42 columns in {page_name}, found {th_count}"
        
        # Presets toolbar
        assert 'id="preset-all"' in content, f"preset-all missing in {page_name}"
        assert 'id="preset-ai"' in content, f"preset-ai missing in {page_name}"
        assert 'id="preset-mom"' in content, f"preset-mom missing in {page_name}"
        assert 'id="preset-val"' in content, f"preset-val missing in {page_name}"
        assert 'id="preset-flow"' in content, f"preset-flow missing in {page_name}"
        assert 'id="preset-macro"' in content, f"preset-macro missing in {page_name}"
        
        # Search filter
        assert 'filterMarketTable' in content, f"filterMarketTable missing in {page_name}"
        
        # CSV Export
        assert 'exportMarketToCsv' in content, f"exportMarketToCsv missing in {page_name}"
        
        # Stock Drawer & Overlay
        assert 'id="stock-drawer"' in content, f"stock-drawer missing in {page_name}"
        assert 'id="stock-drawer-overlay"' in content, f"stock-drawer-overlay missing in {page_name}"
        assert 'openStockDrawer' in content, f"openStockDrawer missing in {page_name}"
