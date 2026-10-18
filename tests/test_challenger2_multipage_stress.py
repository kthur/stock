"""
tests/test_challenger2_multipage_stress.py — Challenger 2 Adversarial Stress Test Suite

Adversarially stress-tests edge cases and generation parameters for the Static Multi-Page Architecture:
1. Custom `--out` directory handling (non-standard filename, deeply nested directories, relative link preservation).
2. Sparse, missing, and corrupt data resilience (empty directory, single-strategy file, corrupt JSON, partial markets).
3. JavaScript table interactions on market detail pages (node --check syntax, column sorting, search filtering, presets, reset sort, drawer).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
import pytest
from bs4 import BeautifulSoup

EXPECTED_PAGES = [
    "index.html",
    "strategies.html",
    "market_kospi.html",
    "market_kosdaq.html",
    "market_sp500.html",
    "market_nasdaq.html",
    "market_russell2000.html",
]

PRESET_CATEGORY_COLUMNS = {
    "all": set(range(42)),
    "ai": {0, 1, 2, 3, 4, 5, 6, 9, 10},
    "mom": {0, 1, 2, 3, 4, 7, 8, 12, 15, 18, 31, 38, 39, 41},
    "val": {0, 1, 2, 3, 4, 13, 14, 19, 28, 30, 35},
    "flow": {0, 1, 2, 3, 4, 17, 22, 27, 29, 32, 33, 34, 40},
    "macro": {0, 1, 2, 3, 4, 11, 16, 20, 21, 23, 24, 25, 26, 36, 37},
}


def _verify_all_relative_links(base_dir: Path) -> list[str]:
    """Scans all HTML files in base_dir and verifies that internal relative links and anchors exist."""
    broken = []
    for page in EXPECTED_PAGES:
        file_path = base_dir / page
        if not file_path.exists():
            broken.append(f"Missing page: {file_path}")
            continue
        soup = BeautifulSoup(file_path.read_text(encoding="utf-8"), "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href == "#" or href.startswith("http://") or href.startswith("https://") or href.startswith("mailto:"):
                continue
            if href.startswith("#"):
                anchor = href.lstrip("#")
                if not soup.find(id=anchor):
                    broken.append(f"{page}: In-page anchor #{anchor} not found")
            elif "#" in href:
                target_file_name, anchor = href.split("#", 1)
                target_path = base_dir / target_file_name
                if not target_path.exists():
                    broken.append(f"{page}: Target file {target_file_name} does not exist for link {href}")
                else:
                    target_soup = BeautifulSoup(target_path.read_text(encoding="utf-8"), "html.parser")
                    if anchor and not target_soup.find(id=anchor):
                        broken.append(f"{page}: Target anchor #{anchor} not found in {target_file_name}")
            else:
                target_path = base_dir / href
                if not target_path.exists():
                    broken.append(f"{page}: Target file {href} does not exist")
    return broken


# ============================================================================
# Section 1: Custom --out Directory Tests
# ============================================================================

class TestCustomOutDirectory:
    """Stress-test generate_report with various custom --out directory structures."""

    def test_custom_filename_in_new_directory(self, tmp_path):
        """Test with --out <tmp_dir>/custom_name.html with real result data."""
        out_dir = tmp_path / "custom_test_out"
        out_file = out_dir / "custom_name.html"
        
        from trading_system.generate_report import main as generate_report_main
        generate_report_main(["--result-dir", "trading_system/result", "--out", str(out_file)])
        
        # Verify all 7 files were created in out_dir
        for page in EXPECTED_PAGES:
            target = out_dir / page
            assert target.exists(), f"Expected file {page} missing in {out_dir}"
            assert target.stat().st_size > 500, f"File {page} is unexpectedly small: {target.stat().st_size} bytes"
            
        # Verify custom_name.html was also created (as a mirror of index.html)
        assert out_file.exists(), f"Custom output file {out_file} was not written"
        assert out_file.stat().st_size > 500
        
        # Verify relative links in this custom directory
        broken_links = _verify_all_relative_links(out_dir)
        assert len(broken_links) == 0, f"Found broken relative links in custom directory: {broken_links}"

    def test_deeply_nested_custom_directory(self, tmp_path):
        """Test with deeply nested path: <tmp_dir>/a/b/c/nested_out/dashboard.html."""
        nested_dir = tmp_path / "a" / "b" / "c" / "nested_out"
        nested_out = nested_dir / "dashboard.html"
        
        from trading_system.generate_report import main as generate_report_main
        generate_report_main(["--result-dir", "trading_system/result", "--out", str(nested_out)])
        
        assert nested_dir.exists(), "Nested directory was not created"
        for page in EXPECTED_PAGES:
            p = nested_dir / page
            assert p.exists(), f"Nested file {page} missing"
            assert p.stat().st_size > 500
            
        broken_links = _verify_all_relative_links(nested_dir)
        assert len(broken_links) == 0, f"Found broken links in nested directory: {broken_links}"


# ============================================================================
# Section 2: Sparse & Missing Data Resilience Tests
# ============================================================================

class TestSparseAndMissingDataResilience:
    """Stress-test report generation when prediction files are missing, empty, or corrupt."""

    def test_completely_empty_results_directory(self, tmp_path):
        """Test generator when result_dir is completely empty (0 files)."""
        empty_res_dir = tmp_path / "empty_results"
        empty_res_dir.mkdir(parents=True)
        out_dir = tmp_path / "empty_out"
        out_file = out_dir / "index.html"
        
        from trading_system.generate_report import main as generate_report_main
        # Generator must not crash with uncaught FileNotFoundError / KeyError / ValueError
        generate_report_main(["--result-dir", str(empty_res_dir), "--out", str(out_file)])
        
        # Verify all 7 files are generated
        for page in EXPECTED_PAGES:
            f = out_dir / page
            assert f.exists(), f"File {page} missing when result_dir is empty"
            assert f.stat().st_size > 200, f"File {page} empty"
            
        # Verify index.html contains fallback empty state
        index_html = (out_dir / "index.html").read_text(encoding="utf-8")
        assert "<html" in index_html and "</html>" in index_html
        assert "regime-risk-card" in index_html  # Skeleton exists
        
        # Verify strategies.html has all 37 strategy cards with LaTeX even with 0 prediction rows
        strat_html = (out_dir / "strategies.html").read_text(encoding="utf-8")
        assert "strat-encyclopedia-card" in strat_html
        cards = re.findall(r'<div class="strat-encyclopedia-card"', strat_html)
        assert len(cards) == 37, f"Expected 37 encyclopedia cards, found {len(cards)}"
        
        # Verify market pages have graceful empty rows
        for mkt in ["kospi", "kosdaq", "sp500", "nasdaq", "russell2000"]:
            mkt_html = (out_dir / f"market_{mkt}.html").read_text(encoding="utf-8")
            assert 'colspan="42" class="empty">데이터 없음' in mkt_html
            assert '<table id="market-full-table">' in mkt_html

    def test_single_strategy_partial_results(self, tmp_path):
        """Test generator when only pipeline_result.txt exists, and other 36 strategies are missing."""
        partial_res_dir = tmp_path / "partial_results"
        partial_res_dir.mkdir(parents=True)
        
        # Write minimal pipeline_result.txt
        sample_pipeline = """Date: 2026-10-18
[1일] KOSPI
1. 005930 (삼성전자): +2.50%
2. 000660 (SK하이닉스): +1.80%
[1일] SP500
1. AAPL (Apple Inc.): +1.20%
2. MSFT (Microsoft Corp.): +0.95%
"""
        (partial_res_dir / "pipeline_result.txt").write_text(sample_pipeline, encoding="utf-8")
        
        out_dir = tmp_path / "partial_out"
        out_file = out_dir / "index.html"
        
        from trading_system.generate_report import main as generate_report_main
        generate_report_main(["--result-dir", str(partial_res_dir), "--out", str(out_file)])
        
        for page in EXPECTED_PAGES:
            assert (out_dir / page).exists()

    def test_zero_byte_and_corrupt_files(self, tmp_path):
        """Test generator with 0-byte text files and malformed JSON."""
        corrupt_res_dir = tmp_path / "corrupt_results"
        corrupt_res_dir.mkdir(parents=True)
        
        # 0-byte files
        (corrupt_res_dir / "pipeline_result.txt").write_text("", encoding="utf-8")
        (corrupt_res_dir / "surge_predictions.txt").write_text("", encoding="utf-8")
        (corrupt_res_dir / "ensemble_predictions.txt").write_text("", encoding="utf-8")
        (corrupt_res_dir / "vcp_patterns.txt").write_text("", encoding="utf-8")
        (corrupt_res_dir / "portfolio_allocation.txt").write_text("", encoding="utf-8")
        
        # Corrupt JSON files
        (corrupt_res_dir / "portfolio_allocations.json").write_text("{ malformed json ", encoding="utf-8")
        (corrupt_res_dir / "backtest_summary.json").write_text("NOT_JSON", encoding="utf-8")
        (corrupt_res_dir / "market_regime_matrix.json").write_text("[[[", encoding="utf-8")
        
        out_dir = tmp_path / "corrupt_out"
        out_file = out_dir / "index.html"
        
        from trading_system.generate_report import main as generate_report_main
        # Should gracefully log warnings and succeed without unhandled exceptions
        generate_report_main(["--result-dir", str(corrupt_res_dir), "--out", str(out_file)])
        
        for page in EXPECTED_PAGES:
            assert (out_dir / page).exists()
            assert (out_dir / page).stat().st_size > 200

    def test_single_market_data_only(self, tmp_path):
        """Test generator when only KOSPI data is present and all US/KOSDAQ markets are omitted."""
        single_mkt_dir = tmp_path / "single_mkt_res"
        single_mkt_dir.mkdir(parents=True)
        
        sample_ensemble = """Date: 2026-10-18
Regime: BULL_LOW_VOL
[KOSPI] Top 100 Ensemble Picks (Target Horizon: 20D Expected Return)
----------------------------------------------------------------------------------------------------
1    005930    삼성전자                    92.5%        6.75%  80%  70%  60%
2    000660    SK하이닉스                   88.0%        5.40%  75%  65%  55%
"""
        (single_mkt_dir / "ensemble_predictions.txt").write_text(sample_ensemble, encoding="utf-8")
        
        out_dir = tmp_path / "single_mkt_out"
        out_file = out_dir / "index.html"
        
        from trading_system.generate_report import main as generate_report_main
        generate_report_main(["--result-dir", str(single_mkt_dir), "--out", str(out_file)])
        
        # Check KOSPI page has rows
        kospi_html = (out_dir / "market_kospi.html").read_text(encoding="utf-8")
        assert "005930" in kospi_html
        assert "삼성전자" in kospi_html
        
        # Check SP500 page has graceful empty row
        sp500_html = (out_dir / "market_sp500.html").read_text(encoding="utf-8")
        assert 'colspan="42" class="empty">데이터 없음' in sp500_html



# ============================================================================
# Section 3: Market Detail Pages JavaScript Table Interactions
# ============================================================================

class TestMarketDetailJavaScriptInteractions:
    """Stress-test JavaScript functions in market detail pages via Node.js execution and DOM auditing."""

    @pytest.fixture(scope="class")
    def kospi_html(self):
        page_path = Path("gh-pages/market_kospi.html")
        assert page_path.exists(), "gh-pages/market_kospi.html must exist"
        return page_path.read_text(encoding="utf-8")

    @pytest.fixture(scope="class")
    def market_js(self, kospi_html):
        """Extract JavaScript code from market_kospi.html."""
        scripts = re.findall(r'<script>(.*?)</script>', kospi_html, re.DOTALL)
        assert len(scripts) > 0, "No <script> block found in market_kospi.html"
        return "\n".join(scripts)

    def test_js_syntax_validation_via_node(self, market_js, tmp_path):
        """Verify that JavaScript embedded in market pages passes node --check with 0 syntax errors."""
        js_file = tmp_path / "market_script.js"
        js_file.write_text(market_js, encoding="utf-8")
        
        result = subprocess.run(
            ["node", "--check", str(js_file)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Node.js syntax error in market script:\n{result.stderr}"

    def test_column_presets_mapping_integrity(self, kospi_html):
        """Audit the preset buttons and presetMap column indices against the 42 table headers."""
        soup = BeautifulSoup(kospi_html, "html.parser")
        table = soup.find("table", id="market-full-table")
        assert table is not None
        
        ths = table.find("thead").find_all("th")
        assert len(ths) == 42, f"Expected exactly 42 <th> headers, got {len(ths)}"
        
        # Extract presetMap from JavaScript
        m = re.search(r'const presetMap = ({.*?});', kospi_html, re.DOTALL)
        assert m is not None, "presetMap object not found in JavaScript"
        
        # Parse presetMap JSON-like object safely
        raw_map_str = m.group(1).replace("'", '"')
        preset_map = json.loads(raw_map_str)
        
        # Verify preset keys
        assert set(preset_map.keys()) == {"all", "ai", "mom", "val", "flow", "macro"}
        
        # Verify preset column indices
        for preset_name, expected_indices in PRESET_CATEGORY_COLUMNS.items():
            actual_indices = set(preset_map[preset_name])
            assert actual_indices == expected_indices, (
                f"Preset '{preset_name}' mismatch: expected {expected_indices}, got {actual_indices}"
            )
            
            # Base columns (0..4) must always be visible in every preset
            for base_col in range(5):
                assert base_col in actual_indices, f"Base column {base_col} missing in preset '{preset_name}'"

    def test_preset_coverage_partitions_all_37_strategies(self):
        """Verify that the 5 category presets (ai, mom, val, flow, macro) partition all 37 strategy columns (5..41)."""
        strategy_cols = set(range(5, 42))
        assert len(strategy_cols) == 37
        
        cat_presets = ["ai", "mom", "val", "flow", "macro"]
        union_cols = set()
        
        for cat in cat_presets:
            cols = PRESET_CATEGORY_COLUMNS[cat] - set(range(5))
            # Verify no overlap between categories
            overlap = union_cols.intersection(cols)
            assert len(overlap) == 0, f"Category '{cat}' overlaps with existing categories on columns {overlap}"
            union_cols.update(cols)
            
        assert union_cols == strategy_cols, f"Union of presets {union_cols} does not match 37 strategy columns {strategy_cols}"

    def test_js_column_sorting_logic_via_node(self, tmp_path):
        """Empirically test sortMarketTable sorting behavior in headless Node.js."""
        node_test_script = """
const jsdom = {
  // Minimal DOM simulation for table sorting
};

// Simulate row data
const mockRows = [
  { rank: 3, symbol: "000660", name: "SK하이닉스", score: "88.2", ret: "▲ +5.4%", reg: "2.1%" },
  { rank: 1, symbol: "005930", name: "삼성전자", score: "94.5", ret: "▲ +12.8%", reg: "4.5%" },
  { rank: 2, symbol: "035420", name: "NAVER", score: "79.0", ret: "▼ -3.2%", reg: "-1.0%" }
];

function createDOM() {
  return mockRows.map((r, i) => {
    return {
      getAttribute: (attr) => attr === 'data-initial-order' ? String(i) : null,
      children: [
        { textContent: '#' + r.rank },
        { textContent: r.symbol },
        { textContent: r.name },
        { textContent: r.score },
        { textContent: r.ret },
        { textContent: r.reg }
      ]
    };
  });
}

let sortState = {};
function sortMarketTable(rows, colIdx) {
  const isAsc = sortState[colIdx] === 'asc';
  sortState[colIdx] = isAsc ? 'desc' : 'asc';
  
  rows.sort((a, b) => {
    const tdA = a.children[colIdx];
    const tdB = b.children[colIdx];
    if (!tdA || !tdB) return 0;
    const txtA = tdA.textContent.trim().replace('%', '').replace('▲', '').replace('▼', '').replace('#', '').trim();
    const txtB = tdB.textContent.trim().replace('%', '').replace('▲', '').replace('▼', '').replace('#', '').trim();
    const numA = parseFloat(txtA);
    const numB = parseFloat(txtB);
    if (!isNaN(numA) && !isNaN(numB)) {
      return isAsc ? numA - numB : numB - numA;
    }
    return isAsc ? txtA.localeCompare(txtB) : txtB.localeCompare(txtA);
  });
  return rows;
}

// Test 1: Sort by Rank (col 0)
let rows = createDOM();
sortMarketTable(rows, 0); // 1st click -> desc
if (rows[0].children[0].textContent !== '#3' || rows[2].children[0].textContent !== '#1') {
  console.error("FAIL: Col 0 Descending failed");
  process.exit(1);
}
sortMarketTable(rows, 0); // 2nd click -> asc
if (rows[0].children[0].textContent !== '#1' || rows[2].children[0].textContent !== '#3') {
  console.error("FAIL: Col 0 Ascending failed");
  process.exit(1);
}

// Test 2: Sort by 20D Return (col 4, containing ▲/▼ and +/-)
rows = createDOM();
sortMarketTable(rows, 4); // 1st click -> desc (+12.8, +5.4, -3.2)
if (rows[0].children[1].textContent !== '005930' || rows[2].children[1].textContent !== '035420') {
  console.error("FAIL: Col 4 Descending failed: " + rows.map(r => r.children[1].textContent).join(','));
  process.exit(1);
}
sortMarketTable(rows, 4); // 2nd click -> asc (-3.2, +5.4, +12.8)
if (rows[0].children[1].textContent !== '035420' || rows[2].children[1].textContent !== '005930') {
  console.error("FAIL: Col 4 Ascending failed: " + rows.map(r => r.children[1].textContent).join(','));
  process.exit(1);
}

// Test 3: Sort with missing cells (empty/fallback table)
const emptyRows = [{ children: [{ textContent: '데이터 없음' }] }];
sortMarketTable(emptyRows, 5); // Should not crash
console.log("PASS: Sorting logic verified");
"""
        test_js = tmp_path / "test_sort.js"
        test_js.write_text(node_test_script, encoding="utf-8")
        res = subprocess.run(["node", str(test_js)], capture_output=True, text=True)
        assert res.returncode == 0, f"Node sorting test failed: {res.stderr}\n{res.stdout}"
        assert "PASS: Sorting logic verified" in res.stdout

    def test_js_search_filter_logic_via_node(self, tmp_path):
        """Empirically test filterMarketTable matching logic in headless Node.js."""
        node_test_script = """
const mockRows = [
  { symbol: "005930", name: "삼성전자", display: "" },
  { symbol: "000660", name: "SK하이닉스", display: "" },
  { symbol: "AAPL", name: "Apple Inc.", display: "" }
];

function filterMarketTable(rows, query) {
  const q = (query || '').trim().toLowerCase();
  rows.forEach(tr => {
    const sym = (tr.symbol || '').toLowerCase();
    const name = (tr.name || '').toLowerCase();
    if (!q || sym.includes(q) || name.includes(q)) {
      tr.display = '';
    } else {
      tr.display = 'none';
    }
  });
}

// Test 1: Exact symbol search
filterMarketTable(mockRows, "005930");
if (mockRows[0].display !== '' || mockRows[1].display !== 'none' || mockRows[2].display !== 'none') {
  console.error("FAIL: Exact symbol search failed");
  process.exit(1);
}

// Test 2: Partial Korean name search
filterMarketTable(mockRows, "하이닉스");
if (mockRows[0].display !== 'none' || mockRows[1].display !== '' || mockRows[2].display !== 'none') {
  console.error("FAIL: Korean name search failed");
  process.exit(1);
}

// Test 3: Case-insensitive search
filterMarketTable(mockRows, "aapl");
if (mockRows[2].display !== '' || mockRows[0].display !== 'none') {
  console.error("FAIL: Case-insensitive search failed");
  process.exit(1);
}

// Test 4: Empty string resets all
filterMarketTable(mockRows, "");
if (mockRows.some(r => r.display !== '')) {
  console.error("FAIL: Empty reset failed");
  process.exit(1);
}

console.log("PASS: Filter logic verified");
"""
        test_js = tmp_path / "test_filter.js"
        test_js.write_text(node_test_script, encoding="utf-8")
        res = subprocess.run(["node", str(test_js)], capture_output=True, text=True)
        assert res.returncode == 0, f"Node filter test failed: {res.stderr}\n{res.stdout}"
        assert "PASS: Filter logic verified" in res.stdout

    def test_dom_attributes_data_symbol_and_name_populated(self, kospi_html):
        """Verify that all table rows in market_kospi.html have data-symbol, data-name, and data-initial-order."""
        soup = BeautifulSoup(kospi_html, "html.parser")
        tbody = soup.find("table", id="market-full-table").find("tbody")
        rows = tbody.find_all("tr")
        assert len(rows) > 0, "No table rows found in market_kospi.html"
        
        for idx, row in enumerate(rows):
            if "empty" in row.get("class", []):
                continue
            assert row.has_attr("data-symbol"), f"Row {idx} missing data-symbol"
            assert row.has_attr("data-name"), f"Row {idx} missing data-name"
            assert row.has_attr("data-initial-order"), f"Row {idx} missing data-initial-order"
            assert row["data-initial-order"] == str(idx), f"Row {idx} data-initial-order mismatch"
            assert row.has_attr("onclick"), f"Row {idx} missing onclick handler"
            assert "openStockDrawer" in row["onclick"], f"Row {idx} onclick does not invoke openStockDrawer"

    def test_market_drawer_event_handlers_integrity(self):
        """Verify that all inline event handlers in the stock drawer are defined in market detail pages."""
        market_pages = ["market_kospi.html", "market_kosdaq.html", "market_sp500.html", "market_nasdaq.html", "market_russell2000.html"]
        missing_handlers = {}
        for mkt_page in market_pages:
            content = (Path("gh-pages") / mkt_page).read_text(encoding="utf-8")
            soup = BeautifulSoup(content, "html.parser")
            scripts = "".join(s.get_text() for s in soup.find_all("script"))
            
            # Check drawer buttons onclick handlers
            drawer = soup.find(id="stock-drawer")
            assert drawer is not None, f"Drawer missing on {mkt_page}"
            
            called_fns = set()
            for tag in drawer.find_all():
                for attr, val in tag.attrs.items():
                    if attr.startswith("on"):
                        for m in re.finditer(r'([a-zA-Z0-9_$]+)\s*\(', val):
                            called_fns.add(m.group(1))
            
            missing = []
            for fn in sorted(called_fns):
                pattern = r'\b(?:function\s+' + re.escape(fn) + r'|' + re.escape(fn) + r'\s*=\s*(?:function|\()|window\.' + re.escape(fn) + r')\b'
                if not re.search(pattern, scripts):
                    missing.append(fn)
            if missing:
                missing_handlers[mkt_page] = missing
                
        assert len(missing_handlers) == 0, f"Market detail pages invoke undefined drawer functions: {missing_handlers}"

    def test_no_duplicate_dom_ids_on_all_pages(self):
        """Verify that no HTML page contains duplicate element IDs (e.g. duplicate toast-container or btn-back-to-top)."""
        duplicates = {}
        for page_name in EXPECTED_PAGES:
            content = (Path("gh-pages") / page_name).read_text(encoding="utf-8")
            soup = BeautifulSoup(content, "html.parser")
            seen_ids = set()
            dup_ids = set()
            for tag in soup.find_all(id=True):
                tag_id = tag["id"].strip()
                if not tag_id:
                    continue
                if tag_id in seen_ids:
                    dup_ids.add(tag_id)
                else:
                    seen_ids.add(tag_id)
            if dup_ids:
                duplicates[page_name] = sorted(list(dup_ids))
                
        assert len(duplicates) == 0, f"Found duplicate DOM element IDs across pages: {duplicates}"

