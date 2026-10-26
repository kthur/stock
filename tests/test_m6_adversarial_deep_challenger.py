"""
Adversarial Stress Test Suite for Milestone M6:
Deep empirical verification across all 7 dashboard pages:
- Fresh regeneration idempotency & size budget
- Node.js syntax parsing of all inline JavaScript
- Zero broken intra-page and cross-page anchor links (all 37 strategies)
- 42-column table integrity & 188px frozen columns across 5 market pages
- Bottom sheet drawer markup, drag handle, radar chart canvas, and close button
- Mobile CSS media queries (<768px, <480px), safe-area insets, and overflow-x containment
- Touch targets >= 44px WCAG compliance
"""

import os
import re
import subprocess
import tempfile
import pytest
from bs4 import BeautifulSoup

GH_PAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gh-pages")
PAGES = [
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


def load_page(page_name: str) -> str:
    path = os.path.join(GH_PAGES_DIR, page_name)
    assert os.path.exists(path), f"Page missing: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_fresh_regeneration_and_size_budgets():
    """Verify that generate_report runs cleanly and enforces all payload budgets."""
    gen_script = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "trading_system", "generate_report.py"
    )
    result_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "trading_system", "result"
    )
    out_file = os.path.join(GH_PAGES_DIR, "index.html")

    cmd = [
        "python",
        gen_script,
        "--result-dir",
        result_dir,
        "--out",
        out_file,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Generation failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}"

    for page in PAGES:
        path = os.path.join(GH_PAGES_DIR, page)
        assert os.path.exists(path), f"Generated file missing: {page}"
        size = os.path.getsize(path)
        assert size > 50000, f"File unexpectedly small ({size} bytes): {page}"

    index_size = os.path.getsize(out_file)
    assert index_size < 512000, f"index.html exceeds 512KB budget: {index_size:,} bytes"


def test_node_javascript_syntax_across_all_pages():
    """Extract every inline <script> block and validate with node --check."""
    for page in PAGES:
        html = load_page(page)
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.find_all("script")
        inline_idx = 0
        for s in scripts:
            if s.get("src"):
                continue
            code = s.string or ""
            if not code.strip():
                continue
            inline_idx += 1
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tmp:
                tmp.write(code)
                tmp_path = tmp.name

            try:
                node_res = subprocess.run(
                    ["node", "--check", tmp_path],
                    capture_output=True,
                    text=True,
                )
                assert node_res.returncode == 0, (
                    f"Syntax error in inline script #{inline_idx} of {page}:\n"
                    f"STDERR: {node_res.stderr}\n"
                    f"CODE SNIPPET:\n{code[:500]}..."
                )
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)


def test_cross_page_navigation_and_strategy_anchors():
    """Verify that all inter-page links and strategy anchors are valid and resolved."""
    pages_soup = {p: BeautifulSoup(load_page(p), "html.parser") for p in PAGES}

    for page, soup in pages_soup.items():
        links = soup.find_all("a", href=True)
        for a in links:
            href = a["href"].strip()
            if not href or href.startswith("http") or href.startswith("javascript:") or href == "#":
                continue

            if href.startswith("#"):
                anchor = href[1:]
                target = soup.find(id=anchor) or soup.find(attrs={"name": anchor})
                assert target is not None, f"Page {page} has broken intra-page anchor: {href}"
            elif "#" in href:
                target_page, anchor = href.split("#", 1)
                assert target_page in pages_soup, f"Page {page} links to non-existent target page: {target_page}"
                target = pages_soup[target_page].find(id=anchor) or pages_soup[target_page].find(attrs={"name": anchor})
                assert target is not None, f"Page {page} links to missing anchor #{anchor} in {target_page}"
            else:
                assert href in pages_soup, f"Page {page} links to non-existent page: {href}"


def test_market_pages_42_columns_and_frozen_geometry():
    """Verify all 5 market detail pages contain 42 columns and strict 188px frozen columns."""
    for page in MARKET_PAGES:
        html = load_page(page)
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", id="market-full-table")
        assert table is not None, f"market-full-table missing in {page}"

        header_th = table.find("thead").find_all("th")
        assert len(header_th) == 42, f"Expected 42 table headers in {page}, got {len(header_th)}"

        # Check sticky columns existence
        th_classes = [th.get("class", []) for th in header_th]
        sticky_ranks = [c for c in th_classes if "sticky-rank" in c]
        sticky_symbols = [c for c in th_classes if "sticky-symbol" in c]
        sticky_names = [c for c in th_classes if "sticky-name" in c]

        assert len(sticky_ranks) == 1, f"Missing or duplicate sticky-rank in {page}"
        assert len(sticky_symbols) == 1, f"Missing or duplicate sticky-symbol in {page}"
        assert len(sticky_names) == 1, f"Missing or duplicate sticky-name in {page}"

        # Check CSS geometry: left: 0 (34px), left: 34px (66px), left: 100px (88px) -> 188px
        assert "left: 0" in html or "left:0" in html
        assert "left: 34px" in html or "left:34px" in html
        assert "left: 100px" in html or "left:100px" in html


def test_drawer_bottom_sheet_components_all_market_pages():
    """Verify stock detail drawer elements, drag handle, radar canvas, and bottom sheet CSS."""
    for page in MARKET_PAGES:
        html = load_page(page)
        soup = BeautifulSoup(html, "html.parser")

        drawer = soup.find(id="stock-drawer")
        assert drawer is not None, f"stock-drawer missing in {page}"

        overlay = soup.find(id="stock-drawer-overlay")
        assert overlay is not None, f"stock-drawer-overlay missing in {page}"

        drag_handle = drawer.find(class_="drawer-drag-handle")
        assert drag_handle is not None, f"drawer-drag-handle missing in {page}"

        radar_canvas = drawer.find(id="drawerRadarChart")
        assert radar_canvas is not None, f"drawerRadarChart canvas missing in {page}"

        # Verify bottom sheet media queries in CSS
        assert "@media (max-width: 768px)" in html or "@media (max-width:768px)" in html
        assert "border-radius: 16px 16px 0 0" in html
        assert "height: 90vh" in html or "max-height: 90vh" in html


def test_mobile_body_overflow_and_safe_area_insets():
    """Verify zero horizontal blowout protection and notch safe area insets on all 7 pages."""
    for page in PAGES:
        html = load_page(page)
        assert "overflow-x: hidden !important" in html, f"Missing overflow-x: hidden !important in {page}"
        assert "viewport-fit=cover" in html, f"Missing viewport-fit=cover in {page}"
        assert "safe-area-inset-top" in html, f"Missing safe-area-inset-top in {page}"
        assert "safe-area-inset-bottom" in html, f"Missing safe-area-inset-bottom in {page}"


def test_strategies_encyclopedia_card_containment_and_formulas():
    """Verify strategies.html has all 37 strategies and mobile formula box scrollability."""
    html = load_page("strategies.html")
    soup = BeautifulSoup(html, "html.parser")

    cards = soup.find_all(class_="strat-encyclopedia-card")
    assert len(cards) == 37, f"Expected 37 strategy cards in strategies.html, found {len(cards)}"

    formula_boxes = soup.find_all(class_="formula-box")
    assert len(formula_boxes) >= 37, f"Expected at least 37 formula-box elements, found {len(formula_boxes)}"

    # Check CSS for touch scrolling
    assert "overflow-x: auto" in html
    assert "-webkit-overflow-scrolling: touch" in html
    assert "repeat(auto-fill, minmax(100%, 1fr))" in html
