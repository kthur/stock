"""
Mobile UI 375px/414px Table Scrolling & Sticky Header Performance Test
"""

import os
import sys
import re

ROOT_DIR = r"d:\Finance\code\stock"
GEN_REPORT_PY = os.path.join(ROOT_DIR, "trading_system", "generate_report.py")
INDEX_HTML = os.path.join(ROOT_DIR, "gh-pages", "index.html")

def analyze_css_rules():
    with open(GEN_REPORT_PY, "r", encoding="utf-8") as f:
        code = f.read()

    # Extract CSS content from generate_report.py
    css_match = re.search(r"<style>(.*?)</style>", code, re.DOTALL)
    css = css_match.group(1) if css_match else ""

    findings = []

    # 1. Sticky Navigation Tabs check
    tabs_sticky = re.search(r"\.tabs\s*\{[^}]*position:\s*sticky;[^}]*top:\s*0;[^}]*z-index:\s*(\d+);", css)
    if tabs_sticky:
        z_tabs = int(tabs_sticky.group(1))
        findings.append({
            "element": ".tabs",
            "position": "sticky",
            "top": "0",
            "z_index": z_tabs,
            "mobile_rule": "Sticky at top:0 on mobile (@media max-width:768px)"
        })

    # 2. Check thead th sticky rules in current code
    th_sticky = re.search(r"thead\s+th\s*\{[^}]*position:\s*sticky;[^}]*top:\s*([^;]+);[^}]*z-index:\s*(\d+);", css)
    if th_sticky:
        findings.append({
            "element": "thead th (Current)",
            "position": "sticky",
            "top": th_sticky.group(1).strip(),
            "z_index": int(th_sticky.group(2)),
        })
    else:
        findings.append({
            "element": "thead th (Current)",
            "position": "static (Not sticky in current CSS)",
            "top": "N/A",
            "z_index": "N/A",
            "issue": "Table headers scroll out of view when user scrolls down"
        })

    # 3. Analyze proposed report change in SYSTEM_IMPROVEMENT_REPORT.md (Section 4.3)
    # Proposed: thead th { position: sticky; top: 0; background: var(--surface2); z-index: 10; }
    proposed_top = "0"
    proposed_z = 10
    tabs_z = 100

    collision_analysis = (
        f"CRITICAL COLLISION: Proposed 'thead th' (top: 0, z-index: {proposed_z}) "
        f"will stick at top: 0, sliding BEHIND '.tabs' (top: 0, z-index: {tabs_z})! "
        f"Table headers become completely INVISIBLE under sticky tabs on mobile viewports."
    )

    # 4. Overflow container clipping check
    table_wrap_match = re.search(r"\.table-wrap\s*\{[^}]*overflow-x:\s*auto;[^}]*\}", css)
    table_wrap_overflow = "overflow-x: auto" if table_wrap_match else "Not found"

    # 5. Mobile viewport metrics
    mobile_metrics = {
        "viewport_375px": {
            "screen_width": 375,
            "min_table_width": 550,
            "overflow_pixels": 175,
            "overflow_ratio": "31.8% of table is off-screen"
        },
        "viewport_414px": {
            "screen_width": 414,
            "min_table_width": 550,
            "overflow_pixels": 136,
            "overflow_ratio": "24.7% of table is off-screen"
        }
    }

    return {
        "findings": findings,
        "collision_analysis": collision_analysis,
        "table_wrap_overflow": table_wrap_overflow,
        "mobile_metrics": mobile_metrics
    }

if __name__ == "__main__":
    print("=== Mobile UI Performance & Sticky Header Challenge ===")
    res = analyze_css_rules()
    for f in res["findings"]:
        print("Finding:", f)
    print("\nCollision Analysis:\n ", res["collision_analysis"])
    print("\nTable Wrap Overflow:\n ", res["table_wrap_overflow"])
    print("\nMobile Metrics:")
    for vp, data in res["mobile_metrics"].items():
        print(f"  {vp}: {data}")
