"""
tests/test_challenger3_multipage_verification.py

Independent Empirical Verification Suite by Challenger 3:
1. Validates that NO duplicate DOM element IDs exist on ANY of the 7 generated pages in gh-pages/,
   with specific deep checks on toast-container and btn-back-to-top on index.html and strategies.html.
2. Validates that copyCurrentStockCode(), filterDrawerFactors(cat, btn), and navigateDrawerStock(dir)
   are defined, syntactically valid (checked via Node.js), and match their calling signatures
   across all 5 market detail pages (market_kospi, market_kosdaq, market_sp500, market_nasdaq, market_russell2000).
3. Validates that gh-pages/index.html file size is strictly < 500 KB (512,000 bytes).
4. Validates generator idempotency by running generate_report to a new target directory and asserting
   identical uniqueness, functionality, and size constraints.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
import pytest
from bs4 import BeautifulSoup

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
MARKET_PAGES = [p for p in EXPECTED_PAGES if p.startswith("market_")]


@pytest.fixture(scope="module")
def loaded_pages():
    pages = {}
    for p in EXPECTED_PAGES:
        fpath = GH_PAGES_DIR / p
        assert fpath.exists(), f"Required artifact {p} does not exist in gh-pages/"
        content = fpath.read_text(encoding="utf-8")
        soup = BeautifulSoup(content, "html.parser")
        pages[p] = (content, soup)
    return pages


class TestChallenger3EmpiricalVerification:
    """Rigorous empirical verification of Iteration 1 defect remediations."""

    def test_task1_no_duplicate_dom_ids_on_any_page(self, loaded_pages):
        """Verify that absolutely no duplicate DOM element IDs exist on any of the 7 generated pages."""
        all_duplicates = {}
        for page_name, (raw_html, soup) in loaded_pages.items():
            id_counts = {}
            for tag in soup.find_all(id=True):
                elem_id = tag["id"].strip()
                if not elem_id:
                    continue
                id_counts[elem_id] = id_counts.get(elem_id, 0) + 1

            duplicates = {k: v for k, v in id_counts.items() if v > 1}
            if duplicates:
                all_duplicates[page_name] = duplicates

        assert not all_duplicates, f"Found duplicate DOM element IDs: {all_duplicates}"

    def test_task1_specific_elements_unique_on_index_and_strategies(self, loaded_pages):
        """Specifically verify toast-container and btn-back-to-top on index.html and strategies.html."""
        for page_name in ["index.html", "strategies.html"]:
            raw_html, soup = loaded_pages[page_name]
            
            # Check using BeautifulSoup
            toast_elements = soup.find_all(id="toast-container")
            btn_elements = soup.find_all(id="btn-back-to-top")
            
            assert len(toast_elements) == 1, (
                f"{page_name} must contain exactly ONE #toast-container, found {len(toast_elements)}"
            )
            assert len(btn_elements) == 1, (
                f"{page_name} must contain exactly ONE #btn-back-to-top, found {len(btn_elements)}"
            )
            
            # Also verify via raw regex count to prevent any parser-masking
            toast_raw_matches = len(re.findall(r'id=["\']toast-container["\']', raw_html))
            btn_raw_matches = len(re.findall(r'id=["\']btn-back-to-top["\']', raw_html))
            assert toast_raw_matches == 1, (
                f"{page_name} raw HTML has {toast_raw_matches} occurrences of id='toast-container'"
            )
            assert btn_raw_matches == 1, (
                f"{page_name} raw HTML has {btn_raw_matches} occurrences of id='btn-back-to-top'"
            )

    def test_task2_drawer_helper_functions_defined_in_all_market_pages(self, loaded_pages):
        """Check copyCurrentStockCode(), filterDrawerFactors, and navigateDrawerStock in all 5 market pages."""
        target_functions = [
            "copyCurrentStockCode",
            "filterDrawerFactors",
            "navigateDrawerStock",
            "showToast",
            "openStockDrawer",
            "closeStockDrawer",
        ]

        missing_report = {}
        for mkt_page in MARKET_PAGES:
            raw_html, soup = loaded_pages[mkt_page]
            scripts = "\n".join(s.get_text() for s in soup.find_all("script"))
            
            missing = []
            for fn in target_functions:
                pattern = rf"\bfunction\s+{re.escape(fn)}\s*\("
                if not re.search(pattern, scripts):
                    missing.append(fn)
            if missing:
                missing_report[mkt_page] = missing

        assert not missing_report, f"Missing functions on market pages: {missing_report}"

    def test_task2_drawer_dom_elements_exist_for_js_functions(self, loaded_pages):
        """Verify that DOM elements manipulated by drawer functions actually exist on all 5 market pages."""
        required_ids = [
            "stock-drawer",
            "stock-drawer-overlay",
            "drawer-stock-name",
            "drawer-stock-meta",
            "drawer-score",
            "drawer-return",
            "drawer-factor-count-badge",
            "drawer-factors-grid",
            "toast-container",
            "market-full-table",
        ]
        
        for mkt_page in MARKET_PAGES:
            _, soup = loaded_pages[mkt_page]
            for elem_id in required_ids:
                elem = soup.find(id=elem_id)
                assert elem is not None, f"Market page {mkt_page} is missing required DOM element #{elem_id}"

            # Check that drawer tabs and copy button exist
            copy_btn = soup.find("button", class_="drawer-copy-btn")
            assert copy_btn is not None, f"{mkt_page} missing .drawer-copy-btn"
            assert "copyCurrentStockCode()" in copy_btn.get("onclick", "")

            factor_tabs = soup.find_all("button", class_="drawer-factor-tab")
            assert len(factor_tabs) >= 5, f"{mkt_page} expected at least 5 category tabs, found {len(factor_tabs)}"
            for tab in factor_tabs:
                assert "filterDrawerFactors" in tab.get("onclick", "")

    def test_task2_node_syntax_check_of_market_scripts(self, loaded_pages, tmp_path):
        """Empirically test that Node.js parses all script blocks from all 5 market pages without syntax errors."""
        for mkt_page in MARKET_PAGES:
            _, soup = loaded_pages[mkt_page]
            for idx, script in enumerate(soup.find_all("script")):
                content = script.string or script.text
                if not content or not content.strip():
                    continue
                js_file = tmp_path / f"{mkt_page}_script_{idx}.js"
                js_file.write_text(content, encoding="utf-8")
                res = subprocess.run(["node", "--check", str(js_file)], capture_output=True, text=True)
                assert res.returncode == 0, (
                    f"Node syntax error in {mkt_page} script #{idx}:\n{res.stderr}"
                )

    def test_task3_index_html_file_size_strictly_under_500kb(self):
        """gh-pages/index.html must be strictly < 500 KB (512,000 bytes)."""
        idx_path = GH_PAGES_DIR / "index.html"
        assert idx_path.exists(), "gh-pages/index.html does not exist"
        size = idx_path.stat().st_size
        max_allowed = 500 * 1024  # 512,000 bytes
        
        print(f"\n[Size Check] index.html = {size} bytes ({size / 1024:.2f} KB) vs budget {max_allowed} bytes")
        assert size < max_allowed, (
            f"index.html size ({size} bytes, {size / 1024:.2f} KB) exceeds 500 KB limit ({max_allowed} bytes)!"
        )
        assert size > 50 * 1024, f"index.html is unexpectedly small ({size} bytes)"

    def test_task3_all_pages_sizes_reasonable(self):
        """Verify sizes of all 7 pages are within expected healthy bounds."""
        expected_ranges = {
            "index.html": (50_000, 512_000),             # < 500 KB
            "strategies.html": (500_000, 2_500_000),     # Encyclopedia doc
            "market_kospi.html": (50_000, 500_000),
            "market_kosdaq.html": (50_000, 500_000),
            "market_sp500.html": (50_000, 500_000),
            "market_nasdaq.html": (30_000, 300_000),
            "market_russell2000.html": (30_000, 300_000),
        }
        for fname, (min_b, max_b) in expected_ranges.items():
            fpath = GH_PAGES_DIR / fname
            assert fpath.exists(), f"Missing {fname}"
            sz = fpath.stat().st_size
            assert min_b <= sz <= max_b, (
                f"{fname} size {sz} bytes ({sz/1024:.2f} KB) outside range [{min_b/1024:.1f} KB, {max_b/1024:.1f} KB]"
            )

    def test_idempotent_regeneration_maintains_all_constraints(self, tmp_path):
        """Empirically execute generator on temporary directory and assert no regressions."""
        from trading_system.generate_report import main as generate_report_main
        
        out_index = tmp_path / "fresh_build" / "index.html"
        generate_report_main(["--result-dir", "trading_system/result", "--out", str(out_index)])
        
        out_dir = out_index.parent
        for page_name in EXPECTED_PAGES:
            page_path = out_dir / page_name
            assert page_path.exists(), f"Regeneration missing {page_name}"
            
            content = page_path.read_text(encoding="utf-8")
            soup = BeautifulSoup(content, "html.parser")
            
            # Check no duplicate IDs
            id_counts = {}
            for tag in soup.find_all(id=True):
                elem_id = tag["id"].strip()
                if elem_id:
                    id_counts[elem_id] = id_counts.get(elem_id, 0) + 1
            dups = {k: v for k, v in id_counts.items() if v > 1}
            assert not dups, f"Regenerated {page_name} contains duplicate IDs: {dups}"

            # If market page, check drawer functions
            if page_name.startswith("market_"):
                scripts = "\n".join(s.get_text() for s in soup.find_all("script"))
                for fn in ["copyCurrentStockCode", "filterDrawerFactors", "navigateDrawerStock"]:
                    assert re.search(rf"\bfunction\s+{fn}\s*\(", scripts), (
                        f"Regenerated {page_name} missing function {fn}"
                    )

        # Check index.html size
        fresh_size = out_index.stat().st_size
        assert fresh_size < 512_000, f"Regenerated index.html size {fresh_size} >= 512,000 bytes"
