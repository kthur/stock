"""
Empirical Forensic Stress Test for merge_predictions.py
Auditor: auditor_m2
"""
import os
import sys
import tempfile
import json
from pathlib import Path

# Add project root and trading_system
root = Path(r"d:\Finance\code\stock")
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "trading_system"))

from merge_predictions import (
    discover_target_markets,
    _extract_ensemble_market_section,
    merge_ensemble_predictions,
    merge_generic_strategy_files,
    merge_portfolio_allocation,
    merge_backtest_summary,
    merge_coverage_report,
    merge_surge_predictions,
    merge_vcp_ml_predictions,
    merge_vcp_patterns,
    merge_lead_lag_predictions,
    merge_pipeline_result,
    KNOWN_MARKETS,
    ALL_31_STRATEGIES
)

def run_stress_tests():
    print("=== STARTING ADVERSARIAL INTEGRITY FORENSICS AUDIT ===")
    failures = []

    # Test 1: Complex multi-part market names & directory discovery
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        result_dir = base_dir / "result"
        result_dir.mkdir(parents=True)
        artifacts_in = base_dir / "artifacts_in"
        artifacts_in.mkdir()

        # Mixed directory patterns
        (artifacts_in / "result_KOSPI").mkdir()
        (artifacts_in / "result_KOSPI" / "pipeline_result_KOSPI.txt").write_text("data", encoding="utf-8")
        
        (artifacts_in / "result-SP500").mkdir()
        (artifacts_in / "result-SP500" / "surge_predictions_SP500.txt").write_text("data", encoding="utf-8")

        (artifacts_in / "result_split_NASDAQ").mkdir()
        (artifacts_in / "result_split_NASDAQ" / "ensemble_predictions_NASDAQ.txt").write_text("data", encoding="utf-8")

        (base_dir / "market_RUSSELL2000").mkdir()
        (base_dir / "market_RUSSELL2000" / "rim_predictions_RUSSELL2000.txt").write_text("data", encoding="utf-8")

        # Multi-probe in result_dir
        (result_dir / "sentiment_predictions_KOSDAQ.txt").write_text("data", encoding="utf-8")
        (result_dir / "sentiment_predictions_CHINA_SZSE.txt").write_text("data", encoding="utf-8")
        (result_dir / "factor_neutralized_predictions_JAPAN_TSE.txt").write_text("data", encoding="utf-8")

        # Utility files to exclude
        (result_dir / "portfolio_allocation_black_litterman.txt").write_text("data", encoding="utf-8")
        (result_dir / "run_comparison.txt").write_text("data", encoding="utf-8")
        (result_dir / "strategy_attribution_report.txt").write_text("data", encoding="utf-8")
        (result_dir / "strategy_data_coverage_report.txt").write_text("data", encoding="utf-8")

        discovered = discover_target_markets(base_dir, result_dir)
        print(f"[Check 1] Discovered markets: {list(discovered.keys())}")

        expected_present = ["KOSPI", "SP500", "NASDAQ", "RUSSELL2000", "KOSDAQ", "CHINA_SZSE", "JAPAN_TSE"]
        for exp in expected_present:
            if exp not in discovered:
                failures.append(f"Check 1 Failed: Expected market {exp} not discovered")

        expected_excluded = ["BLACK_LITTERMAN", "LITTERMAN", "COMPARISON", "REPORT", "ALLOCATION"]
        for exc in expected_excluded:
            if exc in discovered:
                failures.append(f"Check 1 Failed: Excluded name {exc} was discovered as market")

    # Test 2: Stress testing _extract_ensemble_market_section with adversarial headers/footers
    print("\n[Check 2] Testing adversarial section extraction...")
    content_raw = (
        "=== Dynamic Multi-Strategy Ensemble Predictions (31 Strategies) ===\n"
        "Date: 2026-08-29 23:00 KST\n\n"
        "--- Executive Summary ---\n"
        "Regime: BULL\n\n"
        "--- Applied Global Strategy Weights ---\n"
        "XGBoost: 20.0%\n\n"
        "=========================================\n"
        "[SP500] Top 100 Ensemble Picks (Target Horizon: 20D Expected Return)\n"
        "=========================================\n"
        "Rank Symbol Name Score ExpectedReturn\n"
        "-------------------------------------\n"
        "1    AAPL   Apple 98.0% +25.0%\n"
        "2    MSFT   Microsoft 94.0% +21.0%\n\n"
        "-----------------------------------------\n"
        "[KOSPI] Top 100 Ensemble Picks\n"
        "-----------------------------------------\n"
        "Rank Symbol Name Score ExpectedReturn\n"
        "-------------------------------------\n"
        "1    005930 삼성전자 92.0% +18.0%\n\n"
        "--- Data Quality Notes (auto-detected) ---\n"
        "- Missing filings: 2%\n"
        "- Stale quotes: 0%\n"
    )

    sec_sp500 = _extract_ensemble_market_section(content_raw, "SP500")
    sec_kospi = _extract_ensemble_market_section(content_raw, "KOSPI")

    if "AAPL" not in sec_sp500 or "MSFT" not in sec_sp500:
        failures.append("Check 2 Failed: SP500 section did not capture rows")
    if "005930" in sec_sp500:
        failures.append("Check 2 Failed: SP500 section swallowed KOSPI data")
    if "Executive Summary" in sec_sp500:
        failures.append("Check 2 Failed: SP500 section swallowed Executive Summary")
    if "Data Quality Notes" in sec_kospi:
        failures.append("Check 2 Failed: KOSPI section swallowed Data Quality Notes footer")
    if "005930" not in sec_kospi or "삼성전자" not in sec_kospi:
        failures.append("Check 2 Failed: KOSPI section missing rows or Korean text")

    # Test 3: Stress testing Portfolio Allocation weight re-normalization & arithmetic consistency
    print("\n[Check 3] Testing Portfolio Allocation re-normalization...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        result_dir = base_dir / "result"
        result_dir.mkdir(parents=True)

        target_dirs = {}
        # Simulate 5 markets each allocating 30% = 150% total (overflows 85% max allowed)
        markets = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]
        for mkt in markets:
            d = base_dir / f"result_{mkt}"
            d.mkdir()
            target_dirs[mkt] = d
            alloc_content = (
                "=== Portfolio Allocation Recommendations (Ensemble HRP) ===\n"
                "Date: 2026-08-29 23:00 KST\n"
                "Total Capital: 100,000,000 KRW\n"
                "Target Horizon: 20d\n\n"
                "Current Market Regime Detected: BULL_EXPANSION\n"
                "Maximum Total Allocation Allowed: 85.0%\n\n"
                "No.  Symbol       Name                 Market         Return     Volatility   Weight     Amount\n"
                "------------------------------------------------------------------------------------------------\n"
                f"1    {mkt}_SYM1   Stock_{mkt}_1        {mkt:<14}  15.00%     12.00%       20.00%     20,000,000\n"
                f"2    {mkt}_SYM2   Stock_{mkt}_2        {mkt:<14}  12.00%     14.00%       10.00%     10,000,000\n"
                "------------------------------------------------------------------------------------------------\n"
                "Allocated Capital: 30.00% (    30,000,000)\n"
                "Remaining Cash   : 70.00% (    70,000,000)\n"
            )
            (d / f"portfolio_allocation_{mkt}.txt").write_text(alloc_content, encoding="utf-8")

        merge_portfolio_allocation(result_dir, target_dirs)
        merged_alloc = result_dir / "portfolio_allocation.txt"
        if not merged_alloc.exists():
            failures.append("Check 3 Failed: portfolio_allocation.txt not created")
        else:
            txt = merged_alloc.read_text(encoding="utf-8")
            print("Merged Portfolio Summary:")
            for line in txt.splitlines():
                if "Allocated Capital:" in line or "Remaining Cash" in line or "Maximum Total" in line:
                    print("  ", line)
            
            # Check weight capping
            import re
            m_alloc = re.search(r"Allocated Capital:\s*([\d.]+)%\s*\(\s*([\d,]+)\)", txt)
            m_cash = re.search(r"Remaining Cash\s*:\s*([\d.]+)%\s*\(\s*([\d,]+)\)", txt)
            if not m_alloc or not m_cash:
                failures.append("Check 3 Failed: Allocated Capital / Remaining Cash lines missing")
            else:
                alloc_pct = float(m_alloc.group(1))
                cash_pct = float(m_cash.group(1))
                alloc_amt = int(m_alloc.group(2).replace(",", ""))
                cash_amt = int(m_cash.group(2).replace(",", ""))

                if alloc_pct > 85.01:
                    failures.append(f"Check 3 Failed: Allocated weight {alloc_pct}% exceeded max allowed 85%")
                if round(alloc_pct + cash_pct, 1) != 100.0:
                    failures.append(f"Check 3 Failed: Sum of pct {alloc_pct + cash_pct} != 100%")
                if alloc_amt + cash_amt != 100000000:
                    failures.append(f"Check 3 Failed: Sum of amounts {alloc_amt + cash_amt} != 100,000,000")

    # Test 4: Backtest summary merge precedence
    print("\n[Check 4] Testing Backtest Summary merge precedence...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        result_dir = base_dir / "result"
        result_dir.mkdir(parents=True)
        target_dirs = {}

        d1 = base_dir / "result_KOSPI"
        d1.mkdir()
        target_dirs["KOSPI"] = d1
        (d1 / "backtest_summary_KOSPI.json").write_text(json.dumps({
            "updated_at": "2026-08-29T10:00:00Z",
            "strategies": {},
            "status": "insufficient_data"
        }), encoding="utf-8")

        d2 = base_dir / "result_SP500"
        d2.mkdir()
        target_dirs["SP500"] = d2
        (d2 / "backtest_summary_SP500.json").write_text(json.dumps({
            "updated_at": "2026-08-29T09:00:00Z",
            "strategies": {"surge": {"win_rate": 0.65, "cagr": 0.28}},
            "status": "active"
        }), encoding="utf-8")

        merge_backtest_summary(result_dir, target_dirs)
        merged_bs = result_dir / "backtest_summary.json"
        if not merged_bs.exists():
            failures.append("Check 4 Failed: backtest_summary.json not merged")
        else:
            data = json.loads(merged_bs.read_text(encoding="utf-8"))
            if not data.get("strategies"):
                failures.append("Check 4 Failed: Merge did not prioritize summary with realized strategy data")
            else:
                print(f"  Merged backtest summary chosen from market: {data.get('market')}")

    # Test 5: All 31 Strategies merge completeness test
    print("\n[Check 5] Testing All 31 Strategy names in ALL_31_STRATEGIES...")
    if len(ALL_31_STRATEGIES) != 31:
        failures.append(f"Check 5 Failed: Expected 31 strategies in ALL_31_STRATEGIES, found {len(ALL_31_STRATEGIES)}")
    else:
        print(f"  ALL_31_STRATEGIES count = {len(ALL_31_STRATEGIES)} (Verified)")

    print("\n=== FORENSIC TEST RESULTS ===")
    if failures:
        print(f"FAILED: {len(failures)} issues found:")
        for f in failures:
            print(f"  - {f}")
        return False
    else:
        print("ALL ADVERSARIAL INTEGRITY CHECKS PASSED CLEANLY (100% PASS)")
        return True

if __name__ == "__main__":
    success = run_stress_tests()
    sys.exit(0 if success else 1)
