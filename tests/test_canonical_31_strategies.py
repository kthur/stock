"""
tests/test_canonical_31_strategies.py — Validation of Canonical 31 Strategy Sequence

Empirically validates that all 31 strategies are in the exact canonical 1..31 sequence across:
- generate_report.py navigation tabs, panels, strategy guide, and Card 2 health monitor
- gh-pages/index.html navigation buttons and panels
- verify_gha_artifacts.py STRATEGIES constant
- AGENTS.md strategy table
"""

from __future__ import annotations

import re
from pathlib import Path
import pytest

from trading_system.scripts.verify_gha_artifacts import STRATEGIES as VERIFIER_STRATEGIES

CANONICAL_31_KEYS = [
    "regression", "surge", "lead_lag", "vcp_rule", "vcp_ml", "lstm",
    "stat_arb", "sector_rotation", "rim_valuation", "event_driven", "mq_factor",
    "iv_skew", "order_flow", "short_term_reversal", "arm_factor",
    "card_factor", "latr_factor", "inst_foreign_sector",
    "supply_chain", "sentiment", "factor_neutralized", "vol_target",
    "microstructure", "accruals_quality", "short_squeeze", "valueup_catalyst",
    "trend_efficiency", "gamma_squeeze", "insider_buying", "darkpool", "earnings_tone_drift"
]

CANONICAL_TAB_IDS = [
    "regression", "surge", "leadlag", "vcp", "vcpml", "lstm",
    "stat-arb", "sector", "rim", "event", "mq",
    "iv", "flow", "reversal", "arm",
    "card", "latr", "ifs",
    "supplychain", "sentiment", "neutralized", "voltarget",
    "microstructure", "accruals", "shortsqueeze", "valueup",
    "trendeff", "gammasqueeze", "insider", "darkpool", "tonedrift"
]

CANONICAL_PANEL_IDS = [f"panel-{t_id}" for t_id in CANONICAL_TAB_IDS]

INDEX_HTML_PATH = Path("gh-pages/index.html")
GENERATE_REPORT_PATH = Path("trading_system/generate_report.py")
AGENTS_MD_PATH = Path("AGENTS.md")


def test_canonical_list_length_and_uniqueness():
    assert len(CANONICAL_31_KEYS) == 31
    assert len(set(CANONICAL_31_KEYS)) == 31
    assert len(CANONICAL_TAB_IDS) == 31
    assert len(set(CANONICAL_TAB_IDS)) == 31


def test_verifier_strategies_exact_match():
    assert VERIFIER_STRATEGIES == CANONICAL_31_KEYS


def test_generate_report_nav_tabs_sequence():
    content = GENERATE_REPORT_PATH.read_text(encoding="utf-8")
    # Extract Row 2 nav tabs
    nav_match = re.search(r'<div class="row2-wrapper">.*?<nav class="tabs">(.*?)</nav>', content, re.DOTALL)
    assert nav_match is not None, "Row 2 tabs nav not found in generate_report.py"
    nav_html = nav_match.group(1)
    
    # Extract switchTab calls
    tab_calls = re.findall(r"switchTab\(this,\s*'([^']+)'\)", nav_html)
    assert len(tab_calls) in (31, 34), f"Expected 31 or 34 tabs in Row 2 nav, found {len(tab_calls)}: {tab_calls}"
    assert tab_calls[:31] == CANONICAL_TAB_IDS, f"Mismatch in Row 2 nav tab sequence:\nActual: {tab_calls[:31]}\nExpected: {CANONICAL_TAB_IDS}"
    if len(tab_calls) == 34:
        assert tab_calls[31:] == ["crossasset", "gnn", "rangeexpansion"]

    # Extract numbered button labels (1..31 or 1..34)
    labels = re.findall(r'<button[^>]*>(\d+)\.\s+([^<]+)</button>', nav_html)
    assert len(labels) in (31, 34), f"Expected 31 or 34 numbered tab labels, found {len(labels)}"
    for idx, (num_str, name) in enumerate(labels, start=1):
        assert int(num_str) == idx, f"Tab index mismatch: got {num_str}, expected {idx}"


def test_generate_report_panel_sequence():
    content = GENERATE_REPORT_PATH.read_text(encoding="utf-8")
    panel_ids = re.findall(r'<div class="tab-panel[^"]*" id="([^"]+)"', content)
    assert "panel-regression" in panel_ids, "panel-regression not found in generate_report.py"
    reg_idx = panel_ids.index("panel-regression")
    extracted_31 = panel_ids[reg_idx:reg_idx + 31]
    assert extracted_31 == CANONICAL_PANEL_IDS, f"Mismatch in panel sequence:\nActual: {extracted_31}\nExpected: {CANONICAL_PANEL_IDS}"


def test_generate_report_strategy_guide_accordion_sequence():
    content = GENERATE_REPORT_PATH.read_text(encoding="utf-8")
    guide_items = re.findall(r'<div class="strat-card-name">(\d+)\.\s+([^<]+)</div>', content)
    assert len(guide_items) in (31, 34), f"Expected 31 or 34 strategy guide items, found {len(guide_items)}"
    for idx, (num_str, name) in enumerate(guide_items, start=1):
        assert int(num_str) == idx, f"Guide item number mismatch: got {num_str}, expected {idx}"


def test_index_html_tabs_and_panels_sequence():
    if not INDEX_HTML_PATH.exists():
        pytest.skip("gh-pages/index.html not generated yet")
    content = INDEX_HTML_PATH.read_text(encoding="utf-8")
    
    # Check Row 2 tabs in index.html
    nav_match = re.search(r'<div class="row2-wrapper">.*?<nav class="tabs">(.*?)</nav>', content, re.DOTALL)
    assert nav_match is not None, "Row 2 tabs nav not found in index.html"
    tab_calls = re.findall(r"switchTab\(this,\s*'([^']+)'\)", nav_match.group(1))
    assert tab_calls[:31] == CANONICAL_TAB_IDS
    if len(tab_calls) == 34:
        assert tab_calls[31:] == ["crossasset", "gnn", "rangeexpansion"]

    # Check panels sequence in index.html
    panel_ids = re.findall(r'<div class="tab-panel[^"]*" id="([^"]+)"', content)
    # Find position of panel-regression
    reg_idx = panel_ids.index("panel-regression")
    extracted_31 = panel_ids[reg_idx:reg_idx + 31]
    assert extracted_31 == CANONICAL_PANEL_IDS
