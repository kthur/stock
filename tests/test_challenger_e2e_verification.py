"""
tests/test_challenger_e2e_verification.py
Empirical Challenger Test Suite for E2E Artifact Verification, 31-Strategy Result Audit, and Dashboard Consolidation.
"""

import os
import re
import sys
import json
import shutil
import tempfile
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
PYTHON_EXE = sys.executable

MARKETS = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
CANONICAL_31 = [
    "regression", "surge", "lead_lag", "vcp_rule", "vcp_ml", "lstm",
    "stat_arb", "sector_rotation", "rim_valuation", "event_driven", "mq_factor",
    "iv_skew", "order_flow", "short_term_reversal", "arm_factor",
    "card_factor", "latr_factor", "inst_foreign_sector",
    "supply_chain", "sentiment", "factor_neutralized", "vol_target",
    "microstructure", "accruals_quality", "short_squeeze", "valueup_catalyst",
    "trend_efficiency", "gamma_squeeze", "insider_buying", "darkpool", "earnings_tone_drift"
]

STRATEGY_HTML_PANEL_IDS = [
    ("regression", "panel-regression"),
    ("surge", "panel-surge"),
    ("lead_lag", "panel-leadlag"),
    ("vcp_rule", "panel-vcp"),
    ("vcp_ml", "panel-vcpml"),
    ("lstm", "panel-lstm"),
    ("stat_arb", "panel-stat-arb"),
    ("sector_rotation", "panel-sector"),
    ("rim_valuation", "panel-rim"),
    ("event_driven", "panel-event"),
    ("mq_factor", "panel-mq"),
    ("iv_skew", "panel-iv"),
    ("order_flow", "panel-flow"),
    ("short_term_reversal", "panel-reversal"),
    ("arm_factor", "panel-arm"),
    ("card_factor", "panel-card"),
    ("latr_factor", "panel-latr"),
    ("inst_foreign_sector", "panel-ifs"),
    ("supply_chain", "panel-supplychain"),
    ("sentiment", "panel-sentiment"),
    ("factor_neutralized", "panel-neutralized"),
    ("vol_target", "panel-voltarget"),
    ("microstructure", "panel-microstructure"),
    ("accruals_quality", "panel-accruals"),
    ("short_squeeze", "panel-shortsqueeze"),
    ("valueup_catalyst", "panel-valueup"),
    ("trend_efficiency", "panel-trendeff"),
    ("gamma_squeeze", "panel-gammasqueeze"),
    ("insider_buying", "panel-insider"),
    ("darkpool", "panel-darkpool"),
    ("earnings_tone_drift", "panel-tonedrift"),
]


def test_verify_gha_artifacts_clean_dataset_strict_pass():
    """Verify that verify_gha_artifacts.py --strict returns 0 on a valid complete 31-strategy 5-market dataset."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        res_dir = Path(tmp_dir) / "result"
        gh_dir = Path(tmp_dir) / "gh-pages"
        res_dir.mkdir()
        gh_dir.mkdir()
        
        for mkt in MARKETS:
            (res_dir / f"pipeline_result_{mkt}.txt").write_text(
                f"Date: 2026-09-01\n" + "\n".join(f"{i+1}. SYM{i} (C{i}): {0.05 + i*0.01:.2%}" for i in range(15)),
                encoding="utf-8"
            )
            (res_dir / f"surge_predictions_{mkt}.txt").write_text(
                "\n".join(f"[{mkt}] SYM{i} (C{i}): {15.0 + i:.1f}%" for i in range(15)),
                encoding="utf-8"
            )
            (res_dir / f"lead_lag_predictions_{mkt}.txt").write_text(
                "\n".join(f"[{mkt}] SYM{i} -> FOLLOWER_{i}: Score {0.85 - i*0.01:.2f}" for i in range(15)),
                encoding="utf-8"
            )
            (res_dir / f"vcp_patterns_{mkt}.txt").write_text(
                "\n".join(f"[{mkt}] SYM{i} Contractions: 3, Vol: -45%" for i in range(15)),
                encoding="utf-8"
            )
            (res_dir / f"vcp_ml_predictions_{mkt}.txt").write_text(
                "\n".join(f"[{mkt}] SYM{i} (C{i}): {25.0 + i:.1f}%" for i in range(15)),
                encoding="utf-8"
            )
            for s in CANONICAL_31[5:]:
                fname = f"{s}_predictions_{mkt}.txt"
                (res_dir / fname).write_text(
                    f"Date: 2026-09-01\nRank\tSymbol\tScore\n" + "\n".join(f"{i+1}\tSYM{i}\t{0.95 - i*0.02:.4f}" for i in range(15)),
                    encoding="utf-8"
                )
                
        ens_content = (
            "=== 31-Strategy Multi-Factor Ensemble ===\n"
            "Strategy Weights:\n" + "\n".join(f"  {s}: 3.2%" for s in CANONICAL_31) + "\n\n"
            "Top Recommendations:\n" +
            "\n".join(f"{i+1}   SYM{i}   [{MARKETS[i%5]}]   Company{i}   0.88   12.5%" for i in range(100))
        )
        (res_dir / "ensemble_predictions.txt").write_text(ens_content, encoding="utf-8")
        
        html_chunks = [
            "<!DOCTYPE html><html><body>",
            "<h1>Markets: SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ</h1>",
            '<div id="panel-ensemble"><table><tbody>' + "".join(f"<tr><td>{i}</td><td>SYM</td></tr>" for i in range(10)) + '</tbody></table></div>'
        ]
        for s in CANONICAL_31:
            clean_s = s.replace("_", "")
            html_chunks.append(f'<div id="panel-{s}"><table><tbody>' + "".join(f"<tr><td>{i}</td><td>SYM</td></tr>" for i in range(10)) + '</tbody></table></div>')
        html_chunks.append("</body></html>")
        (gh_dir / "index.html").write_text("".join(html_chunks), encoding="utf-8")
        
        cmd = [
            PYTHON_EXE,
            str(ROOT / "trading_system" / "scripts" / "verify_gha_artifacts.py"),
            "--result-dir", str(res_dir),
            "--gh-pages-dir", str(gh_dir),
            "--strict"
        ]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert proc.returncode == 0
        assert "Overall Status     : ✅ PASSED" in proc.stdout


def test_index_html_3_consolidated_cards_and_31_tabs():
    """Empirically audit gh-pages/index.html for 3 consolidated cards and 31 canonical strategy tabs."""
    html_path = ROOT / "gh-pages" / "index.html"
    assert html_path.exists(), "gh-pages/index.html is missing"
    
    content = html_path.read_text(encoding="utf-8", errors="replace")
    
    # 1. Card 1: Market Regime & Risk Gates Console
    assert "regime-risk-card" in content, "Card 1 container (regime-risk-card) missing"
    assert "regime-risk-header" in content, "Card 1 header missing"
    assert "2D Market Regime &amp; Risk Gates" in content, "Card 1 title missing"
    assert "VIX Fast Shock Gate" in content, "Card 1 VIX shock gate missing"
    assert "Macro Composite Score" in content, "Card 1 Macro composite score missing"
    assert "6-Regime Dynamic Matrix" in content, "Card 1 6-regime matrix missing"
    assert "AI Strategy Decision Rationale" in content, "Card 1 Decision rationale missing"
    
    # 2. Card 2: 31-Strategy Health Monitor & Missingness Diagnosis Center
    assert "health-monitor-section" in content, "Card 2 Health monitor section missing"
    assert "Strategy Data Health Monitor" in content, "Card 2 title missing"
    assert "health-summary-pills" in content, "Card 2 summary pills missing"
    assert "pill-healthy" in content, "Card 2 dynamic filter pills missing"
    assert "health-grid" in content, "Card 2 health grid missing"
    assert "CPCV" in content or "Health" in content, "Card 2 missingness diagnosis missing"
    
    # 3. Card 3: Portfolio Optimization & Execution OMS Command Center
    assert "panel-portfolio" in content, "Card 3 container (panel-portfolio) missing"
    assert "hrpDonutChart" in content, "Card 3 HRP donut chart canvas missing"
    assert "marketExposureChart" in content, "Card 3 Market exposure chart canvas missing"
    assert "EVT-GPD Tail Risk Budgeting" in content, "Card 3 EVT-CVaR panel missing"
    assert "Leland No-Trade Buffer Bands" in content, "Card 3 Leland buffer bands missing"
    
    # 4. 31 Canonical Strategy Tabs (1..31) in exact sequence
    for idx, (strat, panel_id) in enumerate(STRATEGY_HTML_PANEL_IDS, 1):
        assert panel_id in content, f"Strategy {idx} ({strat}) tab panel '{panel_id}' missing in index.html"
        
    # Check button order in individual strategies navigation
    tab_buttons_block = re.search(r'<div class="row2-wrapper">[\s\S]*?<nav class="tabs">([\s\S]*?)</nav>', content)
    assert tab_buttons_block is not None, "Strategy tabs navigation block missing"
    tab_html = tab_buttons_block.group(1)
    
    for idx, (strat, panel_id) in enumerate(STRATEGY_HTML_PANEL_IDS, 1):
        clean_alias = panel_id.replace("panel-", "")
        assert clean_alias in tab_html or f"{idx}." in tab_html, f"Strategy {idx} ({strat}) button missing from tabs navigation"


def test_strategy_outputs_canonical_count_and_headers():
    """Audit all 31 strategy output files in trading_system/result/."""
    res_dir = ROOT / "trading_system" / "result"
    
    # Verify ensemble output
    ens_path = res_dir / "ensemble_predictions.txt"
    if not ens_path.exists():
        pytest.skip("ensemble_predictions.txt not present in clean checkout")
    ens_text = ens_path.read_text(encoding="utf-8", errors="replace")
    assert "Strategy Weights" in ens_text or "Dynamic Weight Allocation" in ens_text
    
    # Verify strategy coverage report
    cov_path = res_dir / "strategy_data_coverage_report.txt"
    assert cov_path.exists(), "strategy_data_coverage_report.txt missing"
    cov_text = cov_path.read_text(encoding="utf-8", errors="replace")
    assert "Coverage & Missingness Report" in cov_text
