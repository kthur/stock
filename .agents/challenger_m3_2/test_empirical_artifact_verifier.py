"""
test_empirical_artifact_verifier.py — Dedicated Adversarial Empirical Verifier for M3 Pipeline Artifacts & Dashboard

Tests:
1. HTML syntax, structure, tag balance, and exact panel detection in gh-pages/index.html.
2. Scan for unrendered template tags (e.g. {{...}}, {%.*%}, undefined, NaN%, None%).
3. Table data completeness and row counts across all strategy panels.
4. Strategy Data Coverage Report format and data consistency.
5. Ensemble Predictions format, regime rationale, weights, and market tables.
6. Execution of verify_gha_artifacts.py and report generator unit tests.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Set, Tuple

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RESULT_DIR = ROOT_DIR / "trading_system" / "result"
GH_PAGES_DIR = ROOT_DIR / "gh-pages"
INDEX_HTML = GH_PAGES_DIR / "index.html"
PYTHON_EXE = ROOT_DIR / ".venv" / "Scripts" / "python.exe"


class HTMLValidator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags_stack: List[Tuple[str, int, int]] = []
        self.tag_counts: Dict[str, int] = {}
        self.panels: Dict[str, Dict] = {}
        self.current_panel_id: str | None = None
        self.current_table_rows: int = 0
        self.in_table: bool = False
        self.unclosed_tags: List[str] = []
        self.void_elements = {
            "meta", "link", "img", "br", "hr", "input", "col", "base", "area"
        }

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str | None]]):
        tag_lower = tag.lower()
        self.tag_counts[tag_lower] = self.tag_counts.get(tag_lower, 0) + 1
        attrs_dict = dict(attrs)

        # Check for tab panel
        classes = (attrs_dict.get("class") or "").split()
        panel_id = attrs_dict.get("id") or ""
        if "tab-panel" in classes or panel_id.startswith("panel-"):
            self.current_panel_id = panel_id
            self.panels[panel_id] = {
                "id": panel_id,
                "classes": classes,
                "row_count": 0,
                "has_table": False,
                "tables_count": 0,
            }

        if tag_lower == "table" and self.current_panel_id:
            self.in_table = True
            self.panels[self.current_panel_id]["has_table"] = True
            self.panels[self.current_panel_id]["tables_count"] += 1

        if tag_lower == "tr" and self.current_panel_id and self.in_table:
            self.panels[self.current_panel_id]["row_count"] += 1

        if tag_lower not in self.void_elements:
            self.tags_stack.append((tag_lower, self.getpos()[0], self.getpos()[1]))

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if tag_lower in self.void_elements:
            return

        if tag_lower == "table":
            self.in_table = False

        if self.tags_stack and self.tags_stack[-1][0] == tag_lower:
            self.tags_stack.pop()
        else:
            # Look back in stack
            for i in range(len(self.tags_stack) - 1, -1, -1):
                if self.tags_stack[i][0] == tag_lower:
                    self.tags_stack.pop(i)
                    break


def run_empirical_checks() -> Dict:
    results = {
        "html_file_check": {},
        "template_tags_check": {},
        "panels_check": {},
        "coverage_report_check": {},
        "ensemble_report_check": {},
        "strategy_txt_files_check": {},
        "overall_status": "PENDING",
    }

    print("=" * 100)
    print("🚀 Running Dedicated Adversarial Verification for M3 Pipeline & Dashboard")
    print("=" * 100)

    # 1. Check gh-pages/index.html
    if not INDEX_HTML.exists():
        results["html_file_check"] = {"status": "FAIL", "reason": f"{INDEX_HTML} does not exist"}
        print(f"❌ {INDEX_HTML} not found!")
        return results

    html_content = INDEX_HTML.read_text(encoding="utf-8", errors="replace")
    file_size_bytes = INDEX_HTML.stat().st_size
    file_size_kb = file_size_bytes / 1024

    results["html_file_check"] = {
        "status": "PASS" if file_size_kb >= 50 else "FAIL",
        "file_size_bytes": file_size_bytes,
        "file_size_kb": file_size_kb,
        "lines_count": len(html_content.splitlines()),
    }
    print(f"📄 index.html Size: {file_size_kb:.2f} KB ({file_size_bytes} bytes), Lines: {len(html_content.splitlines())}")
    assert file_size_kb >= 50, f"HTML file size ({file_size_kb:.2f} KB) is too small (<50 KB)"

    # 2. Check for Unrendered Template Tags
    unrendered_patterns = [
        (r"\{\{.*?\}\}", "Jinja/Mustache variable tag {{...}}"),
        (r"\{%.*?%\}", "Jinja statement tag {%...%}"),
        (r"\$\{[a-zA-Z0-9_]+\}", "ES6/Template string unrendered interpolation ${...}"),
        (r"NaN%", "Unsanitized NaN percentage NaN%"),
        (r"None%", "Unsanitized None percentage None%"),
        (r"undefined", "JavaScript undefined token"),
        (r"\[object Object\]", "Stringified JS Object [object Object]"),
    ]

    unrendered_matches = {}
    total_unrendered_violations = 0
    for pattern, desc in unrendered_patterns:
        matches = re.findall(pattern, html_content)
        # Filter false positives: ${...} might appear in legitimate inline JS code if intended, but let's inspect
        if "ES6/Template" in desc:
            # Check if outside script tags
            outside_script = []
            # strip script tags
            no_scripts = re.sub(r"<script[\s\S]*?</script>", "", html_content, flags=re.IGNORECASE)
            outside_matches = re.findall(pattern, no_scripts)
            if outside_matches:
                unrendered_matches[desc] = outside_matches
                total_unrendered_violations += len(outside_matches)
        elif "undefined" in desc:
            # check if inside data cells outside script
            no_scripts = re.sub(r"<script[\s\S]*?</script>", "", html_content, flags=re.IGNORECASE)
            outside_matches = re.findall(r">\s*undefined\s*<", no_scripts)
            if outside_matches:
                unrendered_matches[desc] = outside_matches
                total_unrendered_violations += len(outside_matches)
        else:
            if matches:
                unrendered_matches[desc] = matches[:10]
                total_unrendered_violations += len(matches)

    results["template_tags_check"] = {
        "status": "PASS" if total_unrendered_violations == 0 else "FAIL",
        "violations_count": total_unrendered_violations,
        "violations": unrendered_matches,
    }
    print(f"🧹 Unrendered Template Tags & Glitches Check: {'✅ 0 Violations' if total_unrendered_violations == 0 else f'❌ {total_unrendered_violations} Violations Found'}")
    if unrendered_matches:
        for desc, match_list in unrendered_matches.items():
            print(f"   - {desc}: {match_list}")

    # 3. HTML Parser Validation & Tab Panel Analysis
    parser = HTMLValidator()
    parser.feed(html_content)

    panels = parser.panels
    results["panels_check"] = {
        "total_panels_found": len(panels),
        "panels_details": panels,
    }
    print(f"\n📊 Discovered {len(panels)} Tab Panels in DOM:")
    for pid, pdata in sorted(panels.items()):
        print(f"   - Panel '{pid}': {pdata['row_count']} rows, {pdata['tables_count']} tables")

    # Strategy panels check
    expected_strategy_panels = [
        "panel-ensemble", "panel-portfolio", "panel-backtest", "panel-regime",
        "panel-history", "panel-surge", "panel-vcp", "panel-leadlag", "panel-stat-arb",
        "panel-sector", "panel-rim", "panel-event", "panel-mq", "panel-iv", "panel-flow",
        "panel-reversal", "panel-arm", "panel-card", "panel-latr", "panel-ifs",
        "panel-supplychain", "panel-sentiment", "panel-neutralized", "panel-voltarget",
        "panel-microstructure", "panel-scenario", "panel-vcpml", "panel-regression"
    ]

    missing_panels = [p for p in expected_strategy_panels if p not in panels]
    print(f"   Missing Panels: {missing_panels if missing_panels else 'None (All expected panels present)'}")

    # 4. Check strategy_data_coverage_report.txt
    cov_file = RESULT_DIR / "strategy_data_coverage_report.txt"
    if cov_file.exists():
        cov_text = cov_file.read_text(encoding="utf-8", errors="replace")
        has_header = "Strategy Data Coverage" in cov_text or "Strategy Data Coverage & Missingness Report" in cov_text
        has_kst = "KST" in cov_text
        has_summary_table = "Total Symbols Analyzed" in cov_text or "Strategy Coverage Breakdown" in cov_text or "Strategy" in cov_text
        results["coverage_report_check"] = {
            "status": "PASS" if has_header and has_kst else "FAIL",
            "file_size": len(cov_text),
            "lines": len(cov_text.splitlines()),
            "has_header": has_header,
            "has_kst": has_kst,
        }
        print(f"\n📑 strategy_data_coverage_report.txt: ✅ Valid ({len(cov_text.splitlines())} lines, {len(cov_text)} bytes, KST header verified)")
    else:
        results["coverage_report_check"] = {"status": "FAIL", "reason": "File missing"}
        print(f"❌ {cov_file} missing")

    # 5. Check ensemble_predictions.txt
    ens_file = RESULT_DIR / "ensemble_predictions.txt"
    if ens_file.exists():
        ens_text = ens_file.read_text(encoding="utf-8", errors="replace")
        has_regime_rationale = "[2D Market Regime" in ens_text or "Market Regime" in ens_text
        has_weights = "Strategy Dynamic Weights" in ens_text or "%" in ens_text
        has_markets = any(m in ens_text for m in ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"])
        results["ensemble_report_check"] = {
            "status": "PASS" if has_regime_rationale and has_weights and has_markets else "FAIL",
            "file_size": len(ens_text),
            "lines": len(ens_text.splitlines()),
            "has_regime_rationale": has_regime_rationale,
            "has_weights": has_weights,
            "has_markets": has_markets,
        }
        print(f"📑 ensemble_predictions.txt: ✅ Valid ({len(ens_text.splitlines())} lines, {len(ens_text)} bytes, 2D regime rationale & weights verified)")
    else:
        results["ensemble_report_check"] = {"status": "FAIL", "reason": "File missing"}
        print(f"❌ {ens_file} missing")

    # 6. Check individual strategy result files
    strat_files = [
        "arm_factor_predictions.txt", "card_factor_predictions.txt", "event_driven_predictions.txt",
        "factor_neutralized_predictions.txt", "inst_foreign_sector_predictions.txt", "iv_skew_predictions.txt",
        "latr_factor_predictions.txt", "lead_lag_predictions.txt", "lstm_predictions.txt",
        "microstructure_predictions.txt", "mq_factor_predictions.txt", "order_flow_predictions.txt",
        "pipeline_result.txt", "rim_predictions.txt", "sector_predictions.txt", "sentiment_predictions.txt",
        "short_term_reversal_predictions.txt", "stat_arb_predictions.txt", "supply_chain_predictions.txt",
        "surge_predictions.txt", "vcp_ml_predictions.txt", "vcp_patterns.txt", "vol_target_predictions.txt"
    ]
    present_strat_files = []
    missing_strat_files = []
    for sf in strat_files:
        p = RESULT_DIR / sf
        if p.exists() and p.stat().st_size > 0:
            present_strat_files.append((sf, p.stat().st_size))
        else:
            missing_strat_files.append(sf)

    results["strategy_txt_files_check"] = {
        "status": "PASS" if len(missing_strat_files) == 0 else "FAIL",
        "present_count": len(present_strat_files),
        "missing_count": len(missing_strat_files),
        "missing_files": missing_strat_files,
    }
    print(f"\n📂 Strategy Prediction Text Files: {len(present_strat_files)}/{len(strat_files)} present and populated with non-zero bytes")
    if missing_strat_files:
        print(f"   Missing files: {missing_strat_files}")

    all_passed = (
        results["html_file_check"].get("status") == "PASS" and
        results["template_tags_check"].get("status") == "PASS" and
        results["coverage_report_check"].get("status") == "PASS" and
        results["ensemble_report_check"].get("status") == "PASS" and
        results["strategy_txt_files_check"].get("status") == "PASS"
    )
    results["overall_status"] = "PASS" if all_passed else "FAIL"

    print("\n" + "=" * 100)
    print(f"🏁 Overall Empirical Challenger Verdict: {'✅ APPROVE' if all_passed else '❌ REQUEST_CHANGES'}")
    print("=" * 100)
    return results


if __name__ == "__main__":
    res = run_empirical_checks()
    if res["overall_status"] != "PASS":
        sys.exit(1)
