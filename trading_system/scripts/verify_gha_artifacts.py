#!/usr/bin/env python3
"""
verify_gha_artifacts.py — GHA Artifact & Pipeline Result Verification Utility

Verifies prediction pipeline outputs for 4 markets (SP500, KOSPI, KOSDAQ, KONEX)
across 5 key strategies:
1. Surge Classifier
2. VCP ML Predictor
3. XGBoost Regression
4. VCP Rule Pattern Detector
5. Lead-Lag Matrix

Also verifies:
- Merged Ensemble Predictions (`ensemble_predictions.txt`)
- GitHub Pages HTML Dashboard (`index.html`)

Usage:
    python trading_system/scripts/verify_gha_artifacts.py --result-dir trading_system/result --gh-pages-dir gh-pages
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

MARKETS = ["SP500", "KOSPI", "KOSDAQ", "KONEX"]
STRATEGIES = [
    "surge", "vcp_ml", "regression", "vcp", "lead_lag", "lstm",
    "stat_arb", "sector", "rim", "event_driven", "mq_factor",
    "iv_skew", "order_flow", "short_term_reversal"
]


@dataclass
class StrategyCheckResult:
    strategy: str
    market: str
    file_found: bool = False
    valid: bool = False
    count: int = 0
    non_zero: bool = False
    message: str = ""


@dataclass
class MarketCheckResult:
    market: str
    strategies: Dict[str, StrategyCheckResult] = field(default_factory=dict)
    all_strategies_valid: bool = False


@dataclass
class EnsembleCheckResult:
    file_found: bool = False
    valid: bool = False
    markets_found: List[str] = field(default_factory=list)
    strategy_weights: Dict[str, float] = field(default_factory=dict)
    total_recommendations: int = 0
    message: str = ""


@dataclass
class GhPagesCheckResult:
    file_found: bool = False
    valid: bool = False
    markets_in_html: List[str] = field(default_factory=list)
    has_ensemble_table: bool = False
    has_surge_card: bool = False
    has_vcp_card: bool = False
    has_reg_card: bool = False
    has_lead_lag_card: bool = False
    message: str = ""


@dataclass
class PipelineVerificationReport:
    timestamp: str = ""
    result_dir: str = ""
    gh_pages_dir: str = ""
    markets: Dict[str, MarketCheckResult] = field(default_factory=dict)
    ensemble: EnsembleCheckResult = field(default_factory=EnsembleCheckResult)
    gh_pages: GhPagesCheckResult = field(default_factory=GhPagesCheckResult)
    overall_passed: bool = False


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8").replace("\r\n", "\n")
    except Exception:
        try:
            return path.read_text(encoding="cp949").replace("\r\n", "\n")
        except Exception:
            return path.read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n")


MIN_ITEMS_PER_STRATEGY = 10


def check_surge(content: str, market: str) -> StrategyCheckResult:
    res = StrategyCheckResult(strategy="surge", market=market)
    if not content or "데이터 없음" in content or "No data" in content:
        res.message = "No data or empty section"
        return res

    res.file_found = True
    pattern = rf"\[{re.escape(market)}\]\s+[\w\d_.-]+\s*\([^)]+\):\s*([\d.]+)%"
    matches = re.findall(pattern, content)

    if not matches:
        pattern2 = rf"\d+\.\s+\[{re.escape(market)}\].*?:\s*([\d.]+)%"
        matches = re.findall(pattern2, content)

    res.count = len(matches)
    if matches:
        percentages = [float(p) for p in matches]
        non_zero_pcts = [p for p in percentages if p > 0.0]
        if res.count >= MIN_ITEMS_PER_STRATEGY and non_zero_pcts:
            res.non_zero = True
            res.valid = True
            res.message = f"Found {len(matches)} surge items (>= 10 required, max: {max(percentages):.1f}%)"
        else:
            res.message = f"Found only {res.count} surge items (>= 10 required)"
    else:
        res.message = "No surge entries matching pattern"

    return res


def check_vcp_ml(content: str, market: str) -> StrategyCheckResult:
    res = StrategyCheckResult(strategy="vcp_ml", market=market)
    if not content or "데이터 없음" in content or "No data" in content:
        res.message = "No data or empty section"
        return res

    res.file_found = True
    pattern = rf"\[{re.escape(market)}\]\s+[\w\d_.-]+\s*\([^)]+\):\s*([\d.]+)%"
    matches = re.findall(pattern, content)

    res.count = len(matches)
    if res.count >= MIN_ITEMS_PER_STRATEGY:
        percentages = [float(p) for p in matches]
        res.non_zero = True
        res.valid = True
        res.message = f"Found {len(matches)} VCP ML items (>= 10 required)"
    else:
        res.message = f"Found only {res.count} VCP ML items (>= 10 required)"

    return res


def check_regression(content: str, market: str) -> StrategyCheckResult:
    res = StrategyCheckResult(strategy="regression", market=market)
    if not content or "데이터 없음" in content or "No data" in content:
        res.message = "No data or empty file"
        return res

    res.file_found = True
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    data_lines = [ln for ln in lines if not ln.startswith("===") and not ln.startswith("Date:") and not ln.startswith("Total symbols:")]

    res.count = len(data_lines)
    if res.count >= MIN_ITEMS_PER_STRATEGY:
        res.non_zero = True
        res.valid = True
        res.message = f"Found {res.count} regression prediction rows (>= 10 required)"
    else:
        res.message = f"Found only {res.count} regression prediction rows (>= 10 required)"

    return res


def check_vcp(content: str, market: str) -> StrategyCheckResult:
    res = StrategyCheckResult(strategy="vcp", market=market)
    if not content or "데이터 없음" in content or "No data" in content:
        res.message = "No VCP pattern matches found"
        return res

    res.file_found = True
    matches = re.findall(rf"\[{re.escape(market)}\]", content)
    res.count = len(matches)

    if res.count >= MIN_ITEMS_PER_STRATEGY:
        res.valid = True
        res.non_zero = True
        res.message = f"Found {res.count} VCP pattern entries (>= 10 required)"
    else:
        res.message = f"Found only {res.count} VCP pattern entries (>= 10 required)"

    return res


def check_lead_lag(content: str, market: str) -> StrategyCheckResult:
    res = StrategyCheckResult(strategy="lead_lag", market=market)
    if not content or "데이터 없음" in content or "No data" in content:
        res.message = "No lead-lag data"
        return res

    res.file_found = True
    matches = re.findall(rf"\[{re.escape(market)}\]", content)
    res.count = len(matches)

    if res.count >= MIN_ITEMS_PER_STRATEGY:
        res.valid = True
        res.non_zero = True
        res.message = f"Found {res.count} lead-lag candidate entries (>= 10 required)"
    else:
        res.message = f"Found only {res.count} lead-lag candidate entries (>= 10 required)"

    return res


def check_generic_strategy(content: str, market: str, strat_name: str) -> StrategyCheckResult:
    res = StrategyCheckResult(strategy=strat_name, market=market)
    if not content or "데이터 없음" in content or "No data" in content:
        res.message = f"No {strat_name} data"
        return res

    res.file_found = True
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    data_lines = [ln for ln in lines if not ln.startswith("===") and not ln.startswith("Date:") and not ln.startswith("Total symbols:") and not ln.startswith("---") and not ln.startswith("Pair")]

    res.count = len(data_lines)
    if res.count >= MIN_ITEMS_PER_STRATEGY:
        res.non_zero = True
        res.valid = True
        res.message = f"Found {res.count} {strat_name} prediction items (>= 10 required)"
    else:
        res.message = f"Found only {res.count} {strat_name} prediction items (>= 10 required)"

    return res


def verify_market_strategies(result_dir: Path, market: str) -> MarketCheckResult:
    m_res = MarketCheckResult(market=market)

    files_map = {
        "surge": [f"surge_predictions_{market}.txt", "surge_predictions.txt"],
        "vcp_ml": [f"vcp_ml_predictions_{market}.txt", "vcp_ml_predictions.txt"],
        "regression": [f"pipeline_result_{market}.txt", "pipeline_result.txt"],
        "vcp": [f"vcp_patterns_{market}.txt", "vcp_patterns.txt"],
        "lead_lag": [f"lead_lag_predictions_{market}.txt", "lead_lag_predictions.txt"],
        "lstm": [f"lstm_predictions_{market}.txt", "lstm_predictions.txt"],
        "stat_arb": [f"stat_arb_predictions_{market}.txt", "stat_arb_predictions.txt"],
        "sector": [f"sector_predictions_{market}.txt", "sector_predictions.txt"],
        "rim": [f"rim_predictions_{market}.txt", "rim_predictions.txt"],
        "event_driven": [f"event_driven_predictions_{market}.txt", "event_driven_predictions.txt"],
        "mq_factor": [f"mq_factor_predictions_{market}.txt", "mq_factor_predictions.txt"],
        "iv_skew": [f"iv_skew_predictions_{market}.txt", "iv_skew_predictions.txt"],
        "order_flow": [f"order_flow_predictions_{market}.txt", "order_flow_predictions.txt"],
        "short_term_reversal": [f"short_term_reversal_predictions_{market}.txt", "short_term_reversal_predictions.txt"],
    }

    check_funcs = {
        "surge": check_surge,
        "vcp_ml": check_vcp_ml,
        "regression": check_regression,
        "vcp": check_vcp,
        "lead_lag": check_lead_lag,
        "lstm": lambda c, m: check_generic_strategy(c, m, "lstm"),
        "stat_arb": lambda c, m: check_generic_strategy(c, m, "stat_arb"),
        "sector": lambda c, m: check_generic_strategy(c, m, "sector"),
        "rim": lambda c, m: check_generic_strategy(c, m, "rim"),
        "event_driven": lambda c, m: check_generic_strategy(c, m, "event_driven"),
        "mq_factor": lambda c, m: check_generic_strategy(c, m, "mq_factor"),
        "iv_skew": lambda c, m: check_generic_strategy(c, m, "iv_skew"),
        "order_flow": lambda c, m: check_generic_strategy(c, m, "order_flow"),
        "short_term_reversal": lambda c, m: check_generic_strategy(c, m, "short_term_reversal"),
    }

    for strat, filenames in files_map.items():
        content = ""
        for fname in filenames:
            fpath = result_dir / fname
            if fpath.exists():
                c = _read_text(fpath)
                if c.strip():
                    content = c
                    break

        func = check_funcs[strat]
        s_res = func(content, market)
        m_res.strategies[strat] = s_res

    m_res.all_strategies_valid = all(s.valid for s in m_res.strategies.values())
    return m_res


def verify_ensemble(result_dir: Path) -> EnsembleCheckResult:
    res = EnsembleCheckResult()
    ens_path = result_dir / "ensemble_predictions.txt"
    content = _read_text(ens_path)

    if not content or "데이터 없음" in content:
        res.message = "ensemble_predictions.txt missing or empty"
        return res

    res.file_found = True

    weight_matches = re.findall(r"^\s*([\w\s&()-]+?)\s*:\s*([\d.]+)%", content, re.MULTILINE)
    for name, weight in weight_matches:
        res.strategy_weights[name.strip()] = float(weight)

    found_mkts = []
    for mkt in MARKETS:
        if f"[{mkt}]" in content:
            found_mkts.append(mkt)

    res.markets_found = found_mkts
    rows = re.findall(r"^\d+\s+[\w\d_.-]+", content, re.MULTILINE)
    res.total_recommendations = len(rows)

    if found_mkts and res.total_recommendations > 0:
        res.valid = True
        res.message = f"Ensemble updated with {len(found_mkts)} markets and {res.total_recommendations} picks"
    else:
        res.message = f"Ensemble partially updated (markets: {found_mkts}, picks: {res.total_recommendations})"

    return res


def verify_gh_pages(gh_pages_dir: Path) -> GhPagesCheckResult:
    res = GhPagesCheckResult()
    html_path = gh_pages_dir / "index.html"
    content = _read_text(html_path)

    if not content:
        res.message = "index.html missing or empty"
        return res

    res.file_found = True

    for mkt in MARKETS:
        if mkt in content:
            res.markets_in_html.append(mkt)

    res.has_ensemble_table = "Ensemble" in content or "앙상블" in content
    res.has_surge_card = "Surge" in content or "급등" in content
    res.has_vcp_card = "VCP" in content
    res.has_reg_card = "Regression" in content or "회귀" in content or "수익률" in content
    res.has_lead_lag_card = "Lead-Lag" in content or "리드-랙" in content

    if res.has_ensemble_table and len(res.markets_in_html) >= 2:
        res.valid = True
        res.message = f"GitHub Pages HTML generated cleanly with {len(res.markets_in_html)} markets"
    else:
        res.message = "GitHub Pages HTML missing key sections or markets"

    return res


def run_verification(result_dir: Path, gh_pages_dir: Path) -> PipelineVerificationReport:
    report = PipelineVerificationReport(
        result_dir=str(result_dir.resolve()),
        gh_pages_dir=str(gh_pages_dir.resolve()),
    )

    all_markets_valid = True
    for market in MARKETS:
        m_res = verify_market_strategies(result_dir, market)
        report.markets[market] = m_res
        if not m_res.all_strategies_valid:
            all_markets_valid = False

    report.ensemble = verify_ensemble(result_dir)
    report.gh_pages = verify_gh_pages(gh_pages_dir)

    report.overall_passed = (
        all_markets_valid and report.ensemble.valid and report.gh_pages.valid
    )
    return report


def print_report(report: PipelineVerificationReport) -> None:
    print("\n" + "=" * 110)
    print(" 🔍 Pipeline GHA Artifact Verification Report (14 Strategies & Dashboard)")
    print("=" * 110)
    print(f"Result Directory   : {report.result_dir}")
    print(f"GitHub Pages Dir   : {report.gh_pages_dir}")
    print(f"Overall Status     : {'✅ PASSED' if report.overall_passed else '❌ FAILED'}")
    print("-" * 110)

    print("\n📊 Strategy Verification by Market:")
    headers = ["Market", "Srg", "VCP-M", "Reg", "VCP-R", "L-L", "LSTM", "S-Arb", "Sec", "RIM", "Event", "MQ", "IV-Sk", "Flow", "Rev", "Status"]
    header_str = f"{headers[0]:<8} | " + " | ".join(f"{h:<5}" for h in headers[1:-1]) + f" | {headers[-1]}"
    print(header_str)
    print("-" * 110)

    for market in MARKETS:
        m = report.markets.get(market)
        if not m:
            continue
        st = m.strategies
        row_vals = []
        for s in STRATEGIES:
            row_vals.append("✅" if st.get(s) and st[s].valid else "❌")

        status = "✅ PASS" if m.all_strategies_valid else "❌ FAIL"
        row_str = f"{market:<8} | " + " | ".join(f"{v:<5}" for v in row_vals) + f" | {status}"
        print(row_str)

    print("\n⚡ Merged Ensemble Output:")
    print(f"  File Found     : {'Yes' if report.ensemble.file_found else 'No'}")
    print(f"  Valid Status   : {'✅ Valid' if report.ensemble.valid else '❌ Invalid'}")
    print(f"  Markets Found  : {', '.join(report.ensemble.markets_found)}")
    print(f"  Total Recommendations: {report.ensemble.total_recommendations}")
    print(f"  Message        : {report.ensemble.message}")

    print("\n🌐 GitHub Pages HTML Dashboard:")
    print(f"  File Found     : {'Yes' if report.gh_pages.file_found else 'No'}")
    print(f"  Valid Status   : {'✅ Valid' if report.gh_pages.valid else '❌ Invalid'}")
    print(f"  Markets in HTML: {', '.join(report.gh_pages.markets_in_html)}")
    print(f"  Message        : {report.gh_pages.message}")

    print("\n" + "=" * 110 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Verify pipeline outputs and GitHub Pages artifacts.")
    parser.add_argument("--result-dir", type=str, default="trading_system/result", help="Path to result directory")
    parser.add_argument("--gh-pages-dir", type=str, default="gh-pages", help="Path to gh-pages directory")
    parser.add_argument("--strict", action="store_true", help="Exit with code 1 if verification fails")
    parser.add_argument("--json", action="store_true", help="Output JSON report")

    args = parser.parse_args()

    result_dir = Path(args.result_dir)
    gh_pages_dir = Path(args.gh_pages_dir)

    report = run_verification(result_dir, gh_pages_dir)

    if args.json:
        data = asdict(report)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print_report(report)

    if args.strict and not report.overall_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
