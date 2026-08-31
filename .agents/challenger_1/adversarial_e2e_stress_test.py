"""
adversarial_e2e_stress_test.py
Adversarial stress-testing suite for verify_gha_artifacts, 31-strategy outputs, and gh-pages/index.html consolidation.
"""

import os
import re
import sys
import json
import shutil
import tempfile
import subprocess
from pathlib import Path

ROOT = Path("d:/Finance/code/stock")
PYTHON_EXE = ROOT / ".venv" / "Scripts" / "python.exe"

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

def test_verify_gha_artifacts_full_pass_and_failures():
    print("=" * 80, flush=True)
    print("1. EMPIRICAL STRESS TEST: verify_gha_artifacts.py --strict", flush=True)
    print("=" * 80, flush=True)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        res_dir = Path(tmp_dir) / "result"
        gh_dir = Path(tmp_dir) / "gh-pages"
        res_dir.mkdir()
        gh_dir.mkdir()
        
        # 1. Populate clean valid data for all 31 strategies across 5 markets
        for mkt in MARKETS:
            # regression
            (res_dir / f"pipeline_result_{mkt}.txt").write_text(
                f"Date: 2026-09-01\n" + "\n".join(f"{i+1}. SYM{i} (Company {i}): {0.05 + i*0.01:.2%}" for i in range(15)),
                encoding="utf-8"
            )
            # surge
            (res_dir / f"surge_predictions_{mkt}.txt").write_text(
                "\n".join(f"[{mkt}] SYM{i} (Company {i}): {15.0 + i:.1f}%" for i in range(15)),
                encoding="utf-8"
            )
            # lead_lag
            (res_dir / f"lead_lag_predictions_{mkt}.txt").write_text(
                "\n".join(f"[{mkt}] SYM{i} -> FOLLOWER_{i}: Score {0.85 - i*0.01:.2f}" for i in range(15)),
                encoding="utf-8"
            )
            # vcp_rule
            (res_dir / f"vcp_patterns_{mkt}.txt").write_text(
                "\n".join(f"[{mkt}] SYM{i} Contractions: 3, Vol: -45%" for i in range(15)),
                encoding="utf-8"
            )
            # vcp_ml
            (res_dir / f"vcp_ml_predictions_{mkt}.txt").write_text(
                "\n".join(f"[{mkt}] SYM{i} (Company {i}): {25.0 + i:.1f}%" for i in range(15)),
                encoding="utf-8"
            )
            # generic for remaining 26 strategies
            for s in CANONICAL_31[5:]:
                fname = f"{s}_predictions_{mkt}.txt"
                (res_dir / fname).write_text(
                    f"Date: 2026-09-01\nRank\tSymbol\tScore\n" + "\n".join(f"{i+1}\tSYM{i}\t{0.95 - i*0.02:.4f}" for i in range(15)),
                    encoding="utf-8"
                )
                
        # Ensemble
        ens_content = (
            "=== 31-Strategy Multi-Factor Ensemble ===\n"
            "Strategy Weights:\n" + "\n".join(f"  {s}: 3.2%" for s in CANONICAL_31) + "\n\n"
            "Top Recommendations:\n" +
            "\n".join(f"{i+1}   SYM{i}   [{MARKETS[i%5]}]   Company{i}   0.88   12.5%" for i in range(100))
        )
        (res_dir / "ensemble_predictions.txt").write_text(ens_content, encoding="utf-8")
        
        # gh-pages index.html with all 31 panels and 5 markets
        html_chunks = [
            "<!DOCTYPE html><html><body>",
            "<h1>Markets: SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ</h1>",
            '<div id="card-regime-risk">Regime & Risk</div>',
            '<div id="card-coverage-missingness">Coverage & Missingness</div>',
            '<div id="card-portfolio-oms">Portfolio & OMS</div>',
        ]
        # ensemble panel
        html_chunks.append('<div id="panel-ensemble"><table><tbody>')
        for i in range(20):
            html_chunks.append(f'<tr><td>{i+1}</td><td>SYM{i}</td><td>0.85</td></tr>')
        html_chunks.append('</tbody></table></div>')
        
        # 31 strategy panels
        for s in CANONICAL_31:
            clean_s = s.replace("_", "")
            html_chunks.append(f'<div id="panel-{s}"><table><tbody>')
            for i in range(10):
                html_chunks.append(f'<tr><td>{i+1}</td><td>SYM{i}</td><td>0.75</td></tr>')
            html_chunks.append('</tbody></table></div>')
        html_chunks.append("</body></html>")
        (gh_dir / "index.html").write_text("".join(html_chunks), encoding="utf-8")
        
        # Test A: Full clean valid dataset -> should exit 0
        cmd = [
            str(PYTHON_EXE),
            "trading_system/scripts/verify_gha_artifacts.py",
            "--result-dir", str(res_dir),
            "--gh-pages-dir", str(gh_dir),
            "--strict"
        ]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(f"Clean valid run exit code: {proc.returncode} (Expected: 0)", flush=True)
        assert proc.returncode == 0, f"Expected clean pass, got code {proc.returncode}\n{proc.stdout}"
        print("  -> PASSED: Clean 31-strategy artifact set validated successfully.", flush=True)
        
        # Test B: Adversarial Corruption Injections
        corruptions = [
            ("Truncated regression (<10 items)", res_dir / "pipeline_result_SP500.txt", "Date: 2026-09-01\n1. SYM0: 0.05%\n2. SYM1: 0.04%"),
            ("All-zero expected returns", res_dir / "pipeline_result_SP500.txt", "Date: 2026-09-01\n" + "\n".join(f"{i+1}. SYM{i}: 0.00%" for i in range(15))),
            ("Empty surge predictions", res_dir / "surge_predictions_NASDAQ.txt", ""),
            ("All-zero surge percentages", res_dir / "surge_predictions_NASDAQ.txt", "\n".join(f"[NASDAQ] SYM{i} (C{i}): 0.0%" for i in range(15))),
            ("Missing lead_lag file", res_dir / "lead_lag_predictions_KOSPI.txt", None),
            ("Missing darkpool strategy", res_dir / "darkpool_predictions_KOSDAQ.txt", None),
            ("Missing earnings_tone_drift strategy", res_dir / "earnings_tone_drift_predictions_RUSSELL2000.txt", None),
            ("Empty ensemble file", res_dir / "ensemble_predictions.txt", "데이터 없음"),
            ("Missing strategy panel in HTML", gh_dir / "index.html", "<html><body>SP500 NASDAQ KOSPI</body></html>"),
        ]
        
        for label, target_file, corrupt_content in corruptions:
            # Backup original
            original_content = target_file.read_text(encoding="utf-8") if target_file.exists() else None
            
            if corrupt_content is None:
                if target_file.exists():
                    target_file.unlink()
            else:
                target_file.write_text(corrupt_content, encoding="utf-8")
                
            proc_fail = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
            assert proc_fail.returncode == 1, f"Failed to catch corruption: {label} (returncode: {proc_fail.returncode})"
            print(f"  -> PASSED Catch Test: [{label}] properly rejected with exit code 1.", flush=True)
            
            # Restore
            if original_content is not None:
                target_file.write_text(original_content, encoding="utf-8")

def test_audit_31_strategy_results():
    print("\n" + "=" * 80, flush=True)
    print("2. AUDIT OF CURRENT trading_system/result/*.txt", flush=True)
    print("=" * 80, flush=True)
    res_dir = ROOT / "trading_system" / "result"
    
    files_map = {
        "regression": "pipeline_result.txt",
        "surge": "surge_predictions.txt",
        "lead_lag": "lead_lag_predictions.txt",
        "vcp_rule": "vcp_patterns.txt",
        "vcp_ml": "vcp_ml_predictions.txt",
        "lstm": "lstm_predictions.txt",
        "stat_arb": "stat_arb_predictions.txt",
        "sector_rotation": "sector_predictions.txt",
        "rim_valuation": "rim_predictions.txt",
        "event_driven": "event_driven_predictions.txt",
        "mq_factor": "mq_factor_predictions.txt",
        "iv_skew": "iv_skew_predictions.txt",
        "order_flow": "order_flow_predictions.txt",
        "short_term_reversal": "short_term_reversal_predictions.txt",
        "arm_factor": "arm_factor_predictions.txt",
        "card_factor": "card_factor_predictions.txt",
        "latr_factor": "latr_factor_predictions.txt",
        "inst_foreign_sector": "inst_foreign_sector_predictions.txt",
        "supply_chain": "supply_chain_predictions.txt",
        "sentiment": "sentiment_predictions.txt",
        "factor_neutralized": "factor_neutralized_predictions.txt",
        "vol_target": "vol_target_predictions.txt",
        "microstructure": "microstructure_predictions.txt",
        "accruals_quality": "accruals_quality_predictions.txt",
        "short_squeeze": "short_squeeze_predictions.txt",
        "valueup_catalyst": "valueup_catalyst_predictions.txt",
        "trend_efficiency": "trend_efficiency_predictions.txt",
        "gamma_squeeze": "gamma_squeeze_predictions.txt",
        "insider_buying": "insider_buying_predictions.txt",
        "darkpool": "darkpool_predictions.txt",
        "earnings_tone_drift": "earnings_tone_drift_predictions.txt",
    }
    
    for idx, (s, fname) in enumerate(files_map.items(), 1):
        fpath = res_dir / fname
        if not fpath.exists():
            print(f"{idx:02d}. {s:<22} | ❌ FILE MISSING: {fname}", flush=True)
            continue
        content = fpath.read_text(encoding="utf-8", errors="replace")
        lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
        data_lines = [ln for ln in lines if not ln.startswith("===") and not ln.startswith("---") and not ln.startswith("Date:")]
        print(f"{idx:02d}. {s:<22} | File: {fname:<36} | Size: {len(content):<6} B | Total Lines: {len(lines):<4} | Data Lines: {len(data_lines):<4}", flush=True)

def test_audit_gh_pages_html():
    print("\n" + "=" * 80, flush=True)
    print("3. AUDIT OF gh-pages/index.html STRUCTURE & CONSOLIDATION", flush=True)
    print("=" * 80, flush=True)
    html_path = ROOT / "gh-pages" / "index.html"
    assert html_path.exists(), "gh-pages/index.html does not exist!"
    
    content = html_path.read_text(encoding="utf-8", errors="replace")
    
    print(f"HTML Document Length: {len(content):,} chars", flush=True)
    
    # 1. Check Consolidated Cards
    print("\n[Card Consolidation Check]:", flush=True)
    # Check card 1: Market Regime & Risk Gates
    card1_regime_risk = (
        "시장 환경 & 리스크 게이트" in content or "시장 환경" in content or "macro-strip" in content or "Regime" in content
    )
    # Check card 2: Strategy Coverage & Missingness
    card2_coverage = (
        "전략 커버리지 & 결측 진단" in content or "health-monitor" in content or "전략 커버리지" in content or "Missingness" in content
    )
    # Check card 3: Portfolio Optimization & Execution OMS
    card3_portfolio_oms = (
        "포트폴리오 최적화 & 실행 OMS" in content or "포트폴리오" in content or "Portfolio" in content or "OMS" in content
    )
    
    print(f"  - Card 1 (Market Regime & Risk Gates) found: {card1_regime_risk}", flush=True)
    print(f"  - Card 2 (Strategy Coverage & Missingness) found: {card2_coverage}", flush=True)
    print(f"  - Card 3 (Portfolio Optimization & Execution OMS) found: {card3_portfolio_oms}", flush=True)
    
    # Check 3 specific unified card blocks
    print(f"  - Card 1 Header: '시장 환경 & 리스크 게이트' present: {'시장 환경 & 리스크 게이트' in content or '시장 환경' in content}", flush=True)
    print(f"  - Card 2 Header: '전략 커버리지 & 결측 진단' present: {'전략 커버리지 & 결측 진단' in content or 'Health Monitor' in content or '전략 헬스' in content}", flush=True)
    print(f"  - Card 3 Header: '포트폴리오 최적화 & 실행 OMS' present: {'포트폴리오 최적화 & 실행 OMS' in content or '포트폴리오 최적화' in content}", flush=True)
    
    # 2. Check 31 Strategy Tabs & Panels
    print("\n[31 Canonical Strategy Tabs Check]:", flush=True)
    tab_matches = re.findall(r'class=["\']tab-btn[^"\']*["\'][^>]*data-tab=["\']([^"\']+)["\']', content)
    panel_matches = re.findall(r'id=["\'](?:panel-)?([a-zA-Z0-9_-]+)["\']\s+class=["\']tab-panel', content)
    
    print(f"  Total tab button data-tabs: {len(tab_matches)} -> {tab_matches[:8]}...", flush=True)
    print(f"  Total tab-panel IDs: {len(panel_matches)} -> {panel_matches[:8]}...", flush=True)
    
    missing_tabs = []
    for s in CANONICAL_31:
        clean_s = s.replace("_", "")
        found = any(s == t or clean_s == t.replace("_", "") or s in t for t in tab_matches)
        if not found:
            found = f"panel-{s}" in content or f"panel-{clean_s}" in content or f"id=\"{s}\"" in content or f"id=\"{clean_s}\"" in content
        if not found:
            missing_tabs.append(s)
            
    print(f"  Missing Strategy Tabs/Panels: {missing_tabs if missing_tabs else 'NONE (All 31 Canonical Present)'}", flush=True)
    
    # 3. Responsive Classes & Layout Check
    print("\n[Responsive CSS / Layout Classes Check]:", flush=True)
    responsive_classes = ["macro-grid", "health-grid", "header-meta", "tab-nav", "health-card", "tooltip-wrapper"]
    for rc in responsive_classes:
        found = len(re.findall(rf'class=["\'][^"\']*\b{re.escape(rc)}\b', content))
        print(f"  - Class .{rc}: {found} occurrences", flush=True)


if __name__ == "__main__":
    test_verify_gha_artifacts_full_pass_and_failures()
    test_audit_31_strategy_results()
    test_audit_gh_pages_html()
