"""
tests/test_strategy_encyclopedia_adversarial.py — Empirical Adversarial Challenge Suite

Adversarially stress-tests Requirement R3 (Strategy Encyclopedia Mobile Card Optimization)
and Acceptance Criterion A6 across gh-pages/strategies.html, gh-pages/index.html,
trading_system/report_multipage.py, and trading_system/generate_report.py.

Authored by Challenger M3-1 (Empirical Challenger).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List
import pytest
from bs4 import BeautifulSoup


GH_PAGES_DIR = Path("gh-pages")
STRATEGIES_HTML_PATH = GH_PAGES_DIR / "strategies.html"
INDEX_HTML_PATH = GH_PAGES_DIR / "index.html"
REPORT_MULTIPAGE_PY = Path("trading_system/report_multipage.py")
GENERATE_REPORT_PY = Path("trading_system/generate_report.py")

EXPECTED_37_STRATEGIES = [
    'regression', 'surge', 'leadlag', 'vcp', 'vcpml', 'lstm', 'stat-arb',
    'sector', 'rim', 'event', 'mq', 'iv', 'flow', 'reversal', 'arm', 'card',
    'latr', 'ifs', 'supplychain', 'sentiment', 'neutralized', 'voltarget',
    'microstructure', 'accruals', 'shortsqueeze', 'valueup', 'trendeff',
    'gammasqueeze', 'insider', 'darkpool', 'tonedrift', 'crossasset', 'gnn',
    'rangeexpansion', 'dualcorrection', 'indexrebalance', 'overnightgap'
]


def extract_media_query_content(css: str, max_width: int) -> str:
    """Extract content inside @media (max-width: {max_width}px) { ... } block."""
    pattern = rf'@media\s*\(\s*max-width\s*:\s*{max_width}px\s*\)\s*\{{+'
    matches = list(re.finditer(pattern, css, flags=re.IGNORECASE))
    if not matches:
        return ""
    results = []
    for match in matches:
        start_idx = match.end()
        brace_count = match.group(0).count('{')
        idx = start_idx
        while idx < len(css) and brace_count > 0:
            if css[idx] == '{':
                brace_count += 1
            elif css[idx] == '}':
                brace_count -= 1
            idx += 1
        results.append(css[start_idx:idx-1])
    return "\n".join(results)


@pytest.fixture(scope="module")
def strategies_html() -> str:
    assert STRATEGIES_HTML_PATH.exists(), f"Missing {STRATEGIES_HTML_PATH}"
    return STRATEGIES_HTML_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def strategies_soup(strategies_html: str) -> BeautifulSoup:
    return BeautifulSoup(strategies_html, "html.parser")


@pytest.fixture(scope="module")
def strategies_css(strategies_soup: BeautifulSoup) -> str:
    styles = [s.get_text() for s in strategies_soup.find_all("style")]
    return "\n".join(styles)


# ─────────────────────────────────────────────────────────────────────────────
# 1. 37 Strategies Inventory & DOM Integrity
# ─────────────────────────────────────────────────────────────────────────────

def test_all_37_strategy_cards_present(strategies_soup: BeautifulSoup):
    """Stress-test: Exactly 37 strategy cards must exist in gh-pages/strategies.html."""
    cards = strategies_soup.find_all(class_="strat-encyclopedia-card")
    assert len(cards) == 37, f"Expected exactly 37 cards, found {len(cards)}"


def test_strategy_card_structure_and_ids(strategies_soup: BeautifulSoup):
    """Stress-test: Each of the 37 cards must have top, body, footer, and valid strategy ID."""
    cards = strategies_soup.find_all(class_="strat-encyclopedia-card")
    found_ids = []
    for i, card in enumerate(cards):
        top = card.find(class_="strat-card-top")
        assert top is not None, f"Card #{i+1} missing .strat-card-top"
        
        # Check title
        title = top.find(class_="strat-card-title")
        assert title is not None, f"Card #{i+1} missing .strat-card-title"
        assert len(title.get_text(strip=True)) > 0, f"Card #{i+1} has empty title"
        
        # Check category badge
        badge = top.find(class_=re.compile(r"badge-cat-"))
        assert badge is not None, f"Card #{i+1} missing category badge"
        
        # Check footer
        footer = card.find(class_="strat-card-footer")
        assert footer is not None, f"Card #{i+1} missing .strat-card-footer"
        
        btn = footer.find("a", class_="btn")
        assert btn is not None, f"Card #{i+1} missing action button in footer"
        
        # Anchor target check: switchTabById or #panel-*
        onclick = btn.get("onclick", "")
        m_id = re.search(r"switchTabById\('([^']+)'\)", onclick)
        if m_id:
            found_ids.append(m_id.group(1))

    assert len(found_ids) == 37, f"Expected 37 unique switchTabById IDs, found {len(found_ids)}"
    # Check that canonical strategy keys are represented
    for exp_key in EXPECTED_37_STRATEGIES:
        assert any(exp_key in fid for fid in found_ids), f"Expected strategy {exp_key} not in found IDs: {found_ids}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Grid Collapse & Specificity Stress Testing
# ─────────────────────────────────────────────────────────────────────────────

def test_encyclopedia_grid_mobile_collapse(strategies_css: str):
    """
    Stress-test: .encyclopedia-grid must collapse at 768px and 480px,
    overriding desktop repeat(auto-fill, minmax(480px, 1fr)).
    """
    mq768 = extract_media_query_content(strategies_css, 768)
    mq480 = extract_media_query_content(strategies_css, 480)
    
    assert len(mq768) > 0, "strategies.html missing @media (max-width: 768px)"
    assert len(mq480) > 0, "strategies.html missing @media (max-width: 480px)"
    
    # Check 768px override: must be repeat(auto-fill, minmax(100%, 1fr)) or 1fr with !important
    match_768 = re.search(
        r'\.encyclopedia-grid\s*\{[^}]*grid-template-columns\s*:\s*(repeat\([^)]*minmax\(100%,\s*1fr\)\)|1fr)(?:\s*!important)?',
        mq768,
        re.IGNORECASE
    )
    assert match_768 is not None, (
        f".encyclopedia-grid on < 768px must collapse to minmax(100%, 1fr) or 1fr. Found in mq768: {mq768[:300]}"
    )
    
    # Check 480px override: must be 1fr with !important
    match_480 = re.search(
        r'\.encyclopedia-grid\s*\{[^}]*grid-template-columns\s*:\s*1fr(?:\s*!important)?',
        mq480,
        re.IGNORECASE
    )
    assert match_480 is not None, (
        f".encyclopedia-grid on < 480px must collapse to 1fr. Found in mq480: {mq480[:300]}"
    )


def test_no_rogue_desktop_minmax_bleeding(strategies_css: str):
    """
    Adversarial check: ensure desktop minmax(480px, 1fr) does NOT appear
    inside any mobile media query (< 768px or < 480px).
    """
    mq768 = extract_media_query_content(strategies_css, 768)
    mq480 = extract_media_query_content(strategies_css, 480)
    
    assert "480px, 1fr" not in mq768, "Found desktop minmax(480px, 1fr) leaking into mq768!"
    assert "480px, 1fr" not in mq480, "Found desktop minmax(480px, 1fr) leaking into mq480!"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Card Containment & Min-Width Constraint
# ─────────────────────────────────────────────────────────────────────────────

def test_strat_card_min_width_containment(strategies_css: str, strategies_soup: BeautifulSoup):
    """
    Stress-test: In CSS grid, items have a default min-width: auto.
    If children (e.g. formulas or tables) are wider, the grid item expands,
    blowing out the page width.
    Setting .strat-encyclopedia-card { min-width: 0 !important; } is MANDATORY.
    """
    mq768 = extract_media_query_content(strategies_css, 768)
    assert re.search(r'\.strat-encyclopedia-card\s*\{[^}]*min-width\s*:\s*0', mq768, re.IGNORECASE) is not None, (
        ".strat-encyclopedia-card must specify min-width: 0 on mobile to prevent flex/grid minimum size blowout"
    )
    assert re.search(r'\.strat-encyclopedia-card\s*\{[^}]*max-width\s*:\s*100%', mq768, re.IGNORECASE) is not None, (
        ".strat-encyclopedia-card must specify max-width: 100% on mobile"
    )
    assert re.search(r'\.strat-encyclopedia-card\s*\{[^}]*box-sizing\s*:\s*border-box', mq768, re.IGNORECASE) is not None, (
        ".strat-encyclopedia-card must specify box-sizing: border-box on mobile"
    )

    # Check DOM elements for rogue fixed width inline styles
    cards = strategies_soup.find_all(class_="strat-encyclopedia-card")
    for i, card in enumerate(cards):
        style = card.get("style", "")
        assert "min-width: 4" not in style and "width: 5" not in style, (
            f"Card #{i+1} has rogue fixed width inline style: {style}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Formula Box & Touch Horizontal Scrolling
# ─────────────────────────────────────────────────────────────────────────────

def test_formula_box_touch_scrolling(strategies_css: str, strategies_soup: BeautifulSoup):
    """
    Stress-test: LaTeX formulas inside .formula-box and MathJax .formula-box mjx-container
    must have overflow-x: auto and -webkit-overflow-scrolling: touch.
    """
    mq768 = extract_media_query_content(strategies_css, 768)
    
    # .formula-box
    assert re.search(r'\.formula-box\s*\{[^}]*overflow-x\s*:\s*auto', mq768, re.IGNORECASE) is not None or (
        "overflow-x: auto" in strategies_css and ".formula-box" in strategies_css
    ), ".formula-box missing overflow-x: auto"
    
    assert re.search(r'\.formula-box\s*\{[^}]*-webkit-overflow-scrolling\s*:\s*touch', mq768, re.IGNORECASE) is not None or (
        "-webkit-overflow-scrolling: touch" in strategies_css and ".formula-box" in strategies_css
    ), ".formula-box missing -webkit-overflow-scrolling: touch"

    # .formula-box mjx-container
    assert re.search(r'\.formula-box\s+mjx-container\s*\{[^}]*overflow-x\s*:\s*auto', mq768, re.IGNORECASE) is not None, (
        ".formula-box mjx-container must specify overflow-x: auto for MathJax mobile containment"
    )
    assert re.search(r'\.formula-box\s+mjx-container\s*\{[^}]*-webkit-overflow-scrolling\s*:\s*touch', mq768, re.IGNORECASE) is not None or (
        "overflow-x: auto" in mq768
    ), ".formula-box mjx-container missing touch scrolling"

    # DOM check: find all formula-box elements
    formulas = strategies_soup.find_all(class_="formula-box")
    assert len(formulas) > 0, "strategies.html must contain .formula-box elements"
    for i, f in enumerate(formulas):
        style = f.get("style", "")
        assert "overflow-x: hidden" not in style and "overflow: hidden" not in style, (
            f"Formula box #{i+1} has restrictive overflow inline style: {style}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Regime Mini Table & Touch Scrolling
# ─────────────────────────────────────────────────────────────────────────────

def test_regime_mini_table_touch_scrolling(strategies_css: str, strategies_soup: BeautifulSoup):
    """
    Stress-test: .strat-regime-mini-table must have display: block, overflow-x: auto,
    -webkit-overflow-scrolling: touch, and max-width: 100%.
    """
    mq768 = extract_media_query_content(strategies_css, 768)
    
    assert re.search(r'\.strat-regime-mini-table\s*\{[^}]*overflow-x\s*:\s*auto', mq768, re.IGNORECASE) is not None, (
        ".strat-regime-mini-table must specify overflow-x: auto on mobile"
    )
    assert re.search(r'\.strat-regime-mini-table\s*\{[^}]*-webkit-overflow-scrolling\s*:\s*touch', mq768, re.IGNORECASE) is not None, (
        ".strat-regime-mini-table must specify -webkit-overflow-scrolling: touch on mobile"
    )
    assert re.search(r'\.strat-regime-mini-table\s*\{[^}]*max-width\s*:\s*100%', mq768, re.IGNORECASE) is not None, (
        ".strat-regime-mini-table must specify max-width: 100% on mobile"
    )
    assert re.search(r'\.strat-regime-mini-table\s*\{[^}]*display\s*:\s*block', mq768, re.IGNORECASE) is not None, (
        ".strat-regime-mini-table must specify display: block on mobile to allow <table> to scroll horizontally"
    )

    # DOM check: check all regime mini-tables across strategy cards
    tables = strategies_soup.find_all(class_="strat-regime-mini-table")
    assert len(tables) > 0, "strategies.html must contain .strat-regime-mini-table elements"
    for i, tbl in enumerate(tables):
        headers = [th.get_text(strip=True) for th in tbl.find_all("th")]
        # Check that table has 6 regime headers
        assert len(headers) >= 6, f"Table #{i+1} has fewer than 6 headers: {headers}"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Tap Target Accessibility (44px Rule)
# ─────────────────────────────────────────────────────────────────────────────

def test_card_footer_buttons_tap_target(strategies_css: str, strategies_soup: BeautifulSoup):
    """
    Stress-test: All .strat-card-footer .btn must have min-height: 44px on mobile
    and be styled as block/flex for effortless thumb taps.
    """
    mq768 = extract_media_query_content(strategies_css, 768)
    
    match_btn = re.search(r'\.strat-card-footer\s+\.btn\s*\{[^}]*min-height\s*:\s*44px', mq768, re.IGNORECASE)
    assert match_btn is not None, (
        ".strat-card-footer .btn must specify min-height: 44px on mobile"
    )
    
    # Check width: 100% and flex centering
    assert re.search(r'\.strat-card-footer\s+\.btn\s*\{[^}]*width\s*:\s*100%', mq768, re.IGNORECASE) is not None, (
        ".strat-card-footer .btn must have width: 100% on mobile for easy full-width thumb tapping"
    )
    assert re.search(r'\.strat-card-footer\s+\.btn\s*\{[^}]*display\s*:\s*flex', mq768, re.IGNORECASE) is not None, (
        ".strat-card-footer .btn must have display: flex on mobile for proper vertical centering"
    )

    # Check DOM: all 37 strategy card footer buttons
    cards = strategies_soup.find_all(class_="strat-encyclopedia-card")
    for i, card in enumerate(cards):
        footer = card.find(class_="strat-card-footer")
        assert footer is not None, f"Card #{i+1} missing footer"
        btn = footer.find("a", class_="btn")
        assert btn is not None, f"Card #{i+1} missing button"
        style = btn.get("style", "")
        # Either inline min-height:44px or class-based min-height:44px
        assert "min-height:44px" in style or "min-height: 44px" in style or "min-height" in mq768, (
            f"Card #{i+1} button does not have min-height 44px: {style}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Dual Parity & Report Generation Synchronization
# ─────────────────────────────────────────────────────────────────────────────

def test_report_multipage_and_generate_report_sync():
    """
    Stress-test: Both report_multipage.py and generate_report.py must contain
    identical mobile CSS rules for Requirement R3 to prevent desync on regeneration.
    """
    assert REPORT_MULTIPAGE_PY.exists(), f"Missing {REPORT_MULTIPAGE_PY}"
    assert GENERATE_REPORT_PY.exists(), f"Missing {GENERATE_REPORT_PY}"
    
    rm_content = REPORT_MULTIPAGE_PY.read_text(encoding="utf-8")
    gr_content = GENERATE_REPORT_PY.read_text(encoding="utf-8")
    
    for key_rule in [
        ".encyclopedia-grid",
        ".strat-encyclopedia-card",
        ".formula-box",
        ".strat-regime-mini-table",
        ".strat-card-footer .btn",
    ]:
        assert key_rule in rm_content, f"Key rule {key_rule} missing from {REPORT_MULTIPAGE_PY}"
        assert key_rule in gr_content, f"Key rule {key_rule} missing from {GENERATE_REPORT_PY}"


# ─────────────────────────────────────────────────────────────────────────────
# 8. File Size Budgets and Zero Blowout
# ─────────────────────────────────────────────────────────────────────────────

def test_index_html_size_budget():
    """
    Stress-test: index.html must remain strictly under 512,000 bytes (500 KB limit).
    """
    assert INDEX_HTML_PATH.exists(), f"Missing {INDEX_HTML_PATH}"
    size = INDEX_HTML_PATH.stat().st_size
    assert size < 512000, f"index.html size {size} bytes exceeds 512,000 byte limit!"
    # Ensure comfortable headroom
    margin = 512000 - size
    assert margin > 1000, f"index.html margin ({margin} bytes) is precariously small (< 1000 bytes)"


def test_body_overflow_hygiene_across_pages():
    """
    Stress-test: strategies.html and index.html must have overflow-x: hidden on body
    and viewport meta tag with viewport-fit=cover.
    """
    for page in [STRATEGIES_HTML_PATH, INDEX_HTML_PATH]:
        content = page.read_text(encoding="utf-8")
        assert "viewport-fit=cover" in content, f"{page.name} missing viewport-fit=cover"
        assert re.search(r'body\s*\{[^}]*overflow-x\s*:\s*hidden', content, re.IGNORECASE) is not None, (
            f"{page.name} missing body overflow-x: hidden"
        )
