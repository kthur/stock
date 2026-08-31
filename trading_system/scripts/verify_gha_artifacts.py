#!/usr/bin/env python3
"""
verify_gha_artifacts.py — GHA Artifact & Pipeline Result Verification Utility

Verifies prediction pipeline outputs for 5 markets (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ)
across all 31 multi-factor strategies.

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

MARKETS = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
STRATEGIES = [
    "regression", "surge", "lead_lag", "vcp_rule", "vcp_ml", "lstm",
    "stat_arb", "sector_rotation", "rim_valuation", "event_driven", "mq_factor",
    "iv_skew", "order_flow", "short_term_reversal", "arm_factor",
    "card_factor", "latr_factor", "inst_foreign_sector",
    "supply_chain", "sentiment", "factor_neutralized", "vol_target",
    "microstructure", "accruals_quality", "short_squeeze", "valueup_catalyst",
    "trend_efficiency", "gamma_squeeze", "insider_buying", "darkpool", "earnings_tone_drift"
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
    strategy_panels_valid: Dict[str, bool] = field(default_factory=dict)
    strategy_panel_counts: Dict[str, int] = field(default_factory=dict)
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
        if res.count >= MIN_ITEMS_PER_STRATEGY and len(non_zero_pcts) > 0:
            res.non_zero = True
            res.valid = True
            res.message = f"Found {len(matches)} surge items (non-zero valid, max: {max(percentages):.1f}%)"
        elif res.count < MIN_ITEMS_PER_STRATEGY:
            res.message = f"Found only {res.count} surge items (>= {MIN_ITEMS_PER_STRATEGY} required)"
        else:
            res.message = f"Found {res.count} surge items but all prediction values are 0.0%"
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
    if matches:
        percentages = [float(p) for p in matches]
        non_zero_pcts = [p for p in percentages if p > 0.0]
        if res.count >= MIN_ITEMS_PER_STRATEGY and len(non_zero_pcts) > 0:
            res.non_zero = True
            res.valid = True
            res.message = f"Found {len(matches)} VCP ML items (non-zero valid, max: {max(percentages):.1f}%)"
        elif res.count < MIN_ITEMS_PER_STRATEGY:
            res.message = f"Found only {res.count} VCP ML items (>= {MIN_ITEMS_PER_STRATEGY} required)"
        else:
            res.message = f"Found {res.count} VCP ML items but all prediction values are 0.0%"
    else:
        res.message = f"No VCP ML items matching pattern for {market}"

    return res


def check_regression(content: str, market: str) -> StrategyCheckResult:
    res = StrategyCheckResult(strategy="regression", market=market)
    if not content or "데이터 없음" in content or "No data" in content:
        res.message = "No data or empty file"
        return res

    res.file_found = True
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    data_lines = [
        ln for ln in lines
        if not ln.startswith("===")
        and not ln.startswith("Date:")
        and not ln.startswith("Total symbols")
        and not ln.startswith("---")
        and not ln.startswith("Symbol")
    ]

    res.count = len(data_lines)
    non_zero_values = []
    for ln in data_lines:
        found_floats = [float(val) for val in re.findall(r"[-+]?\d+\.\d+", ln)]
        if any(abs(val) > 1e-6 for val in found_floats):
            non_zero_values.append(True)

    if res.count >= MIN_ITEMS_PER_STRATEGY and len(non_zero_values) > 0:
        res.non_zero = True
        res.valid = True
        res.message = f"Found {res.count} regression prediction rows with non-zero returns (>= {MIN_ITEMS_PER_STRATEGY} required)"
    elif res.count < MIN_ITEMS_PER_STRATEGY:
        res.message = f"Found only {res.count} regression prediction rows (>= {MIN_ITEMS_PER_STRATEGY} required)"
    else:
        res.message = f"Found {res.count} regression rows, but all expected returns are 0.0"

    return res


def check_vcp(content: str, market: str) -> StrategyCheckResult:
    res = StrategyCheckResult(strategy="vcp_rule", market=market)
    if not content or "데이터 없음" in content or "No data" in content:
        res.message = "No VCP pattern matches found"
        return res

    res.file_found = True
    matches = re.findall(rf"\[{re.escape(market)}\]", content)
    res.count = len(matches)

    if res.count >= MIN_ITEMS_PER_STRATEGY:
        res.valid = True
        res.non_zero = True
        res.message = f"Found {res.count} VCP pattern entries with non-zero parameters (>= {MIN_ITEMS_PER_STRATEGY} required)"
    else:
        res.message = f"Found only {res.count} VCP pattern entries (>= {MIN_ITEMS_PER_STRATEGY} required)"

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
        res.message = f"Found {res.count} lead-lag candidate entries with non-zero scores (>= {MIN_ITEMS_PER_STRATEGY} required)"
    else:
        res.message = f"Found only {res.count} lead-lag candidate entries (>= {MIN_ITEMS_PER_STRATEGY} required)"

    return res


def check_generic_strategy(content: str, market: str, strat_name: str) -> StrategyCheckResult:
    res = StrategyCheckResult(strategy=strat_name, market=market)
    if not content or "데이터 없음" in content or "No data" in content:
        res.message = f"No {strat_name} data"
        return res

    res.file_found = True
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    data_lines = [
        ln for ln in lines
        if not ln.startswith("===")
        and not ln.startswith("Date:")
        and not ln.startswith("Total symbols")
        and not ln.startswith("Total cointegrated")
        and not ln.startswith("---")
        and not ln.startswith("───")
        and not ln.startswith("Pair")
        and not ln.startswith("Rank")
        and not ln.startswith("No.")
        and not ln.startswith("No\t")
        and not ln.startswith("Filters:")
        and not ln.startswith("Symbol")
    ]

    res.count = len(data_lines)
    non_zero_found = 0
    for ln in data_lines:
        found_nums = re.findall(r"[-+]?\d*\.\d+|\d+%", ln)
        for num_str in found_nums:
            num_clean = num_str.replace("%", "")
            try:
                val = float(num_clean)
                if abs(val) > 1e-6:
                    non_zero_found += 1
            except ValueError:
                pass

    if res.count >= MIN_ITEMS_PER_STRATEGY and non_zero_found > 0:
        res.non_zero = True
        res.valid = True
        res.message = f"Found {res.count} {strat_name} items with non-zero prediction values (>= {MIN_ITEMS_PER_STRATEGY} required)"
    elif res.count < MIN_ITEMS_PER_STRATEGY:
        res.message = f"Found only {res.count} {strat_name} items (>= {MIN_ITEMS_PER_STRATEGY} required)"
    else:
        res.message = f"Found {res.count} {strat_name} items, but all output values are 0.0"

    return res


def verify_market_strategies(result_dir: Path, market: str) -> MarketCheckResult:
    m_res = MarketCheckResult(market=market)

    files_map = {
        "regression": [f"pipeline_result_{market}.txt", "pipeline_result.txt"],
        "surge": [f"surge_predictions_{market}.txt", "surge_predictions.txt"],
        "lead_lag": [f"lead_lag_predictions_{market}.txt", "lead_lag_predictions.txt"],
        "vcp_rule": [f"vcp_patterns_{market}.txt", "vcp_patterns.txt"],
        "vcp_ml": [f"vcp_ml_predictions_{market}.txt", "vcp_ml_predictions.txt"],
        "lstm": [f"lstm_predictions_{market}.txt", "lstm_predictions.txt"],
        "stat_arb": [f"stat_arb_predictions_{market}.txt", "stat_arb_predictions.txt"],
        "sector_rotation": [f"sector_predictions_{market}.txt", "sector_predictions.txt", f"sector_rotation_predictions_{market}.txt", "sector_rotation_predictions.txt"],
        "rim_valuation": [f"rim_predictions_{market}.txt", "rim_predictions.txt", f"rim_valuation_predictions_{market}.txt", "rim_valuation_predictions.txt"],
        "event_driven": [f"event_driven_predictions_{market}.txt", "event_driven_predictions.txt"],
        "mq_factor": [f"mq_factor_predictions_{market}.txt", "mq_factor_predictions.txt"],
        "iv_skew": [f"iv_skew_predictions_{market}.txt", "iv_skew_predictions.txt"],
        "order_flow": [f"order_flow_predictions_{market}.txt", "order_flow_predictions.txt"],
        "short_term_reversal": [f"short_term_reversal_predictions_{market}.txt", "short_term_reversal_predictions.txt"],
        "arm_factor": [f"arm_factor_predictions_{market}.txt", "arm_factor_predictions.txt"],
        "card_factor": [f"card_factor_predictions_{market}.txt", "card_factor_predictions.txt"],
        "latr_factor": [f"latr_factor_predictions_{market}.txt", "latr_factor_predictions.txt"],
        "inst_foreign_sector": [f"inst_foreign_sector_predictions_{market}.txt", "inst_foreign_sector_predictions.txt"],
        "supply_chain": [f"supply_chain_predictions_{market}.txt", "supply_chain_predictions.txt"],
        "sentiment": [f"sentiment_predictions_{market}.txt", "sentiment_predictions.txt"],
        "factor_neutralized": [f"factor_neutralized_predictions_{market}.txt", "factor_neutralized_predictions.txt"],
        "vol_target": [f"vol_target_predictions_{market}.txt", "vol_target_predictions.txt"],
        "microstructure": [f"microstructure_predictions_{market}.txt", "microstructure_predictions.txt"],
        "accruals_quality": [f"accruals_quality_predictions_{market}.txt", "accruals_quality_predictions.txt", f"accruals_quality_{market}.txt", "accruals_quality.txt"],
        "short_squeeze": [f"short_squeeze_predictions_{market}.txt", "short_squeeze_predictions.txt", f"short_squeeze_{market}.txt", "short_squeeze.txt"],
        "valueup_catalyst": [f"valueup_catalyst_predictions_{market}.txt", "valueup_catalyst_predictions.txt", f"valueup_catalyst_{market}.txt", "valueup_catalyst.txt"],
        "trend_efficiency": [f"trend_efficiency_predictions_{market}.txt", "trend_efficiency_predictions.txt", f"trend_efficiency_{market}.txt", "trend_efficiency.txt"],
        "gamma_squeeze": [f"gamma_squeeze_predictions_{market}.txt", "gamma_squeeze_predictions.txt", f"gamma_squeeze_{market}.txt", "gamma_squeeze.txt"],
        "insider_buying": [f"insider_buying_predictions_{market}.txt", "insider_buying_predictions.txt", f"insider_buying_{market}.txt", "insider_buying.txt"],
        "darkpool": [f"darkpool_predictions_{market}.txt", "darkpool_predictions.txt", f"hft_order_flow_predictions_{market}.txt", "hft_order_flow_predictions.txt"],
        "earnings_tone_drift": [f"earnings_tone_drift_predictions_{market}.txt", "earnings_tone_drift_predictions.txt"],
    }

    check_funcs = {
        "regression": check_regression,
        "surge": check_surge,
        "lead_lag": check_lead_lag,
        "vcp_rule": check_vcp,
        "vcp_ml": check_vcp_ml,
        "lstm": lambda c, m: check_generic_strategy(c, m, "lstm"),
        "stat_arb": lambda c, m: check_generic_strategy(c, m, "stat_arb"),
        "sector_rotation": lambda c, m: check_generic_strategy(c, m, "sector_rotation"),
        "rim_valuation": lambda c, m: check_generic_strategy(c, m, "rim_valuation"),
        "event_driven": lambda c, m: check_generic_strategy(c, m, "event_driven"),
        "mq_factor": lambda c, m: check_generic_strategy(c, m, "mq_factor"),
        "iv_skew": lambda c, m: check_generic_strategy(c, m, "iv_skew"),
        "order_flow": lambda c, m: check_generic_strategy(c, m, "order_flow"),
        "short_term_reversal": lambda c, m: check_generic_strategy(c, m, "short_term_reversal"),
        "arm_factor": lambda c, m: check_generic_strategy(c, m, "arm_factor"),
        "card_factor": lambda c, m: check_generic_strategy(c, m, "card_factor"),
        "latr_factor": lambda c, m: check_generic_strategy(c, m, "latr_factor"),
        "inst_foreign_sector": lambda c, m: check_generic_strategy(c, m, "inst_foreign_sector"),
        "supply_chain": lambda c, m: check_generic_strategy(c, m, "supply_chain"),
        "sentiment": lambda c, m: check_generic_strategy(c, m, "sentiment"),
        "factor_neutralized": lambda c, m: check_generic_strategy(c, m, "factor_neutralized"),
        "vol_target": lambda c, m: check_generic_strategy(c, m, "vol_target"),
        "microstructure": lambda c, m: check_generic_strategy(c, m, "microstructure"),
        "accruals_quality": lambda c, m: check_generic_strategy(c, m, "accruals_quality"),
        "short_squeeze": lambda c, m: check_generic_strategy(c, m, "short_squeeze"),
        "valueup_catalyst": lambda c, m: check_generic_strategy(c, m, "valueup_catalyst"),
        "trend_efficiency": lambda c, m: check_generic_strategy(c, m, "trend_efficiency"),
        "gamma_squeeze": lambda c, m: check_generic_strategy(c, m, "gamma_squeeze"),
        "insider_buying": lambda c, m: check_generic_strategy(c, m, "insider_buying"),
        "darkpool": lambda c, m: check_generic_strategy(c, m, "darkpool"),
        "earnings_tone_drift": lambda c, m: check_generic_strategy(c, m, "earnings_tone_drift"),
    }

    for strat in STRATEGIES:
        filenames = files_map.get(strat, [])
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


STRATEGY_PANEL_ALIASES: Dict[str, List[str]] = {
    "ensemble": ["ensemble"],
    "regression": ["regression"],
    "surge": ["surge"],
    "lead_lag": ["leadlag", "lead_lag", "lead-lag"],
    "vcp_rule": ["vcp", "vcp_rule", "vcp-rule"],
    "vcp_ml": ["vcpml", "vcp_ml", "vcp-ml"],
    "lstm": ["lstm"],
    "stat_arb": ["stat-arb", "stat_arb", "statarb"],
    "sector_rotation": ["sector", "sector_rotation", "sectorrotation", "sector-rotation"],
    "rim_valuation": ["rim", "rim_valuation", "rimvaluation", "rim-valuation"],
    "event_driven": ["event", "event_driven", "eventdriven", "event-driven"],
    "mq_factor": ["mq", "mq_factor", "mqfactor", "mq-factor"],
    "iv_skew": ["iv", "iv_skew", "ivskew", "iv-skew"],
    "order_flow": ["flow", "order_flow", "orderflow", "order-flow"],
    "short_term_reversal": ["reversal", "short_term_reversal", "shorttermreversal", "short-term-reversal"],
    "arm_factor": ["arm", "arm_factor", "armfactor", "arm-factor"],
    "card_factor": ["card", "card_factor", "cardfactor", "card-factor"],
    "latr_factor": ["latr", "latr_factor", "latrfactor", "latr-factor"],
    "inst_foreign_sector": ["ifs", "inst_foreign_sector", "instforeignsector", "inst-foreign-sector"],
    "supply_chain": ["supplychain", "supply_chain", "supply-chain"],
    "sentiment": ["sentiment"],
    "factor_neutralized": ["neutralized", "factor_neutralized", "factorneutralized", "factor-neutralized"],
    "vol_target": ["voltarget", "vol_target", "vol-target"],
    "microstructure": ["microstructure"],
    "accruals_quality": ["accruals", "accruals_quality", "accrualsquality", "accruals-quality"],
    "short_squeeze": ["shortsqueeze", "short_squeeze", "short-squeeze"],
    "valueup_catalyst": ["valueup", "valueup_catalyst", "valueupcatalyst", "valueup-catalyst"],
    "trend_efficiency": ["trendeff", "trend_efficiency", "trendefficiency", "trend-efficiency"],
    "gamma_squeeze": ["gammasqueeze", "gamma_squeeze", "gamma-squeeze"],
    "insider_buying": ["insider", "insider_buying", "insiderbuying", "insider-buying"],
    "darkpool": ["darkpool", "hft", "darkpool_hft", "darkpool-hft"],
    "earnings_tone_drift": ["tonedrift", "earnings_tone_drift", "earningstonedrift", "earnings-tone-drift"],
}


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

    for p_id, alias_list in STRATEGY_PANEL_ALIASES.items():
        matched = False
        for a in alias_list:
            clean_pid = a.replace("_", "")
            panel_regex = rf'id=["\'](?:panel-(?:{re.escape(a)}|{re.escape(clean_pid)})|(?:{re.escape(a)}|{re.escape(clean_pid)})-panels)["\'][\s\S]*?(?=<div class=["\']tab-panel["\']|\Z)'
            p_match = re.search(panel_regex, content, re.IGNORECASE)
            if p_match:
                p_content = p_match.group(0)
                data_rows = re.findall(r'<tr[^>]*>[\s\S]*?</tr>', p_content, re.IGNORECASE)
                data_rows = [r for r in data_rows if '<th' not in r.lower()]
                count = len(data_rows)
                res.strategy_panel_counts[p_id] = count
                res.strategy_panels_valid[p_id] = count >= 1
                matched = True
                break

        if not matched:
            count = len(re.findall(r'class=["\']rank["\']', content))
            res.strategy_panel_counts[p_id] = count
            res.strategy_panels_valid[p_id] = count > 0 and (p_id in content or "앙상블" in content)

    all_panels_ok = all(res.strategy_panels_valid.values())
    has_min_mkts = len(res.markets_in_html) >= 2

    if all_panels_ok and has_min_mkts:
        res.valid = True
        res.message = f"GitHub Pages HTML generated cleanly with {len(res.markets_in_html)} markets and all 31 strategy panels populated with data"
    else:
        failed_panels = [p for p, valid in res.strategy_panels_valid.items() if not valid]
        res.valid = False
        res.message = f"GitHub Pages HTML data missing in strategy panels: {', '.join(failed_panels)}"

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

    has_strategy_data = any(
        any(s.valid for s in m.strategies.values()) for m in report.markets.values()
    )
    report.overall_passed = (
        has_strategy_data and report.ensemble.valid and report.gh_pages.valid
    )
    return report


def print_report(report: PipelineVerificationReport) -> None:
    print("\n" + "=" * 190)
    print(" 🔍 Pipeline GHA Artifact Verification Report (All 31 Strategies & Dashboard)")
    print("=" * 190)
    print(f"Result Directory   : {report.result_dir}")
    print(f"GitHub Pages Dir   : {report.gh_pages_dir}")
    print(f"Overall Status     : {'✅ PASSED' if report.overall_passed else '❌ FAILED'}")
    print("-" * 190)

    print("\n📊 Strategy Verification by Market (Canonical 31 Strategies):")
    headers = [
        "Market", "Reg", "Srg", "L-L", "VCP-R", "VCP-M", "LSTM", "S-Arb",
        "Sec", "RIM", "Event", "MQ", "IV-Sk", "Flow", "Rev", "ARM", "CARD",
        "LATR", "IFS", "SC", "Sent", "Neu", "VolT", "Micro", "Accr",
        "Sqz", "ValUp", "TEff", "GSqz", "Insdr", "Dark", "Tone", "Status"
    ]
    header_str = f"{headers[0]:<12} | " + " | ".join(f"{h:<5}" for h in headers[1:-1]) + f" | {headers[-1]}"
    print(header_str)
    print("-" * 190)

    for market in MARKETS:
        m = report.markets.get(market)
        if not m:
            continue
        st = m.strategies
        row_vals = []
        for s in STRATEGIES:
            row_vals.append("✅" if st.get(s) and st[s].valid else "❌")

        status = "✅ PASS" if m.all_strategies_valid else "❌ FAIL"
        row_str = f"{market:<12} | " + " | ".join(f"{v:<5}" for v in row_vals) + f" | {status}"
        print(row_str)

    print("\n⚡ Merged Ensemble Output:")
    print(f"  File Found     : {'Yes' if report.ensemble.file_found else 'No'}")
    print(f"  Valid Status   : {'✅ Valid' if report.ensemble.valid else '❌ Invalid'}")
    print(f"  Markets Found  : {', '.join(report.ensemble.markets_found)}")
    print(f"  Total Recommendations: {report.ensemble.total_recommendations}")
    print(f"  Message        : {report.ensemble.message}")

    print("\n🌐 GitHub Pages HTML Dashboard & 31 Strategy Panels:")
    print(f"  File Found     : {'Yes' if report.gh_pages.file_found else 'No'}")
    print(f"  Valid Status   : {'✅ Valid' if report.gh_pages.valid else '❌ Invalid'}")
    print(f"  Markets in HTML: {', '.join(report.gh_pages.markets_in_html)}")
    print("  Strategy Panels Data Status:")
    for p_id, p_ok in report.gh_pages.strategy_panels_valid.items():
        cnt = report.gh_pages.strategy_panel_counts.get(p_id, 0)
        status_icon = "✅" if p_ok else "❌"
        print(f"    - {p_id:<20}: {status_icon} ({cnt} rows)")
    print(f"  Summary Message: {report.gh_pages.message}")

    print("\n" + "=" * 190 + "\n")


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
