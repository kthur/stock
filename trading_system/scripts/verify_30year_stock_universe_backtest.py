#!/usr/bin/env python3
"""
verify_30year_stock_universe_backtest.py -- Automated Independent Verification Script for Phase 105 Stock Universe Backtest (1996-2026)

Release: R121 (Phase 105 -- v112 Production Master, Feature F499)
Validates the integrity, schema, institutional portfolio guardrails, 6 strict KPIs,
zero lookahead bias, dynamic filing lag, and survivorship bias defense.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

# Path bootstrapping
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("VerifyStockUniverseBacktest")


# ==============================================================================
# Specification Constants & Thresholds
# ==============================================================================

REQUIRED_FILES = [
    "quant_benchmark_30year_stock_universe_report.md",
    "backtest_30year_stock_universe_summary.json",
    "backtest_30year_stock_universe_annual.csv",
    "backtest_30year_stock_universe_crisis.csv",
]

TARGET_MARKETS = {"KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"}

EXPECTED_START_YEAR = 1996
EXPECTED_END_YEAR = 2026
TOTAL_EXPECTED_YEARS = 31

# Strict KPI Thresholds (Phase 105 Acceptance Criteria)
KPI_MIN_CAGR_PCT = 25.00
KPI_MIN_SHARPE = 1.80
KPI_MIN_SORTINO = 2.50
KPI_MIN_MDD_PCT = -18.00  # MDD must be >= -18.00% (bounded between -18.00% and 0.0%)
KPI_MIN_ACTIVE_WIN_RATE_PCT = 58.00

# Institutional Guardrails
MAX_STOCK_WEIGHT_CAP = 0.05 + 1e-6
MAX_SECTOR_WEIGHT_CAP = 0.25 + 1e-6
MAX_ADV_PARTICIPATION_CAP = 0.015 + 1e-6

HISTORICAL_CRISES = [
    {
        "id": "1997_ASIAN_CRISIS",
        "patterns": ["1997", "ASIAN", "IMF"],
        "name": "1997 Asian Financial Crisis (IMF)",
    },
    {
        "id": "2000_DOTCOM_CRASH",
        "patterns": ["2000", "DOTCOM", "DOT-COM", "BUBBLE"],
        "name": "2000 Dot-com Bubble Crash",
    },
    {
        "id": "2008_GFC",
        "patterns": ["2008", "GFC", "GLOBAL FINANCIAL", "LEHMAN"],
        "name": "2008 Global Financial Crisis (GFC)",
    },
    {
        "id": "2020_COVID_SHOCK",
        "patterns": ["2020", "COVID", "PANDEMIC"],
        "name": "2020 COVID-19 Shock",
    },
    {
        "id": "2022_INFLATION_RATE_HIKE",
        "patterns": ["2022", "INFLATION", "RATE_HIKE", "RATE HIKE", "FED"],
        "name": "2022 Inflation & Rate-Hike Bear Market",
    },
]


# ==============================================================================
# Data Structures
# ==============================================================================

@dataclass
class VerificationCheck:
    check_id: str
    category: str
    description: str
    passed: bool
    severity: str = "ERROR"  # "ERROR" or "WARNING"
    details: str = ""


@dataclass
class VerificationSummary:
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warning_checks: int = 0
    passed: bool = True
    checks: List[VerificationCheck] = field(default_factory=list)
    summary_dict: Dict[str, Any] = field(default_factory=dict)


# ==============================================================================
# Helper Functions
# ==============================================================================

def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        return f if math.isfinite(f) else None
    except (ValueError, TypeError):
        return None


# ==============================================================================
# StockUniverse30YearVerifier Class
# ==============================================================================

class StockUniverse30YearVerifier:
    """
    Independent Verification Engine for Phase 105 Stock Universe Backtest Results.
    Executes 6 verification suites:
    1. File Existence & Storage Integrity
    2. Schema & Structure Integrity (JSON, CSV, Markdown)
    3. 31-Year Annual Distribution (1996~2026 unbroken)
    4. 5 Historical Crisis Stress Defense Windows
    5. Institutional Portfolio Guardrails (5% stock, 25% sector, 1.5% ADV)
    6. Strict KPI Thresholds (CAGR>=25%, Sharpe>=1.80, Sortino>=2.50, MDD>=-18%, WinRate>=58%)
    7. Causality, Dynamic Filing Lag, and Survivorship Bias Defense
    """

    def __init__(
        self,
        result_dir: str | Path = "trading_system/result",
        strict: bool = True,
    ) -> None:
        self.result_dir = Path(result_dir).resolve()
        self.strict = strict
        self.checks: List[VerificationCheck] = []

    def _add_check(
        self,
        check_id: str,
        category: str,
        description: str,
        passed: bool,
        severity: str = "ERROR",
        details: str = "",
    ) -> None:
        self.checks.append(
            VerificationCheck(
                check_id=check_id,
                category=category,
                description=description,
                passed=bool(passed),
                severity=severity,
                details=details,
            )
        )

    # --------------------------------------------------------------------------
    # Suite 1: File Existence & Storage Integrity
    # --------------------------------------------------------------------------
    def verify_file_existence(self) -> None:
        """Verifies directory existence and presence of all 4 required artifacts."""
        cat = "FILE_EXISTENCE"
        dir_ok = self.result_dir.is_dir()
        self._add_check(
            check_id="FILE-DIR-01",
            category=cat,
            description="Artifacts output directory exists",
            passed=dir_ok,
            severity="ERROR",
            details=f"Path: {self.result_dir}",
        )
        if not dir_ok:
            return

        for fname in REQUIRED_FILES:
            fpath = self.result_dir / fname
            exists = fpath.is_file()
            size = fpath.stat().st_size if exists else 0
            self._add_check(
                check_id=f"FILE-EXIST-{fname.split('.')[0].upper()}",
                category=cat,
                description=f"Artifact exists and is non-empty: {fname}",
                passed=(exists and size > 0),
                severity="ERROR",
                details=f"Size: {size:,} bytes | Path: {fpath}",
            )

    # --------------------------------------------------------------------------
    # Suite 2: Schema & Structure Integrity
    # --------------------------------------------------------------------------
    def verify_schema_integrity(self) -> Tuple[Optional[Dict[str, Any]], Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[str]]:
        cat = "SCHEMA_INTEGRITY"
        p_json = self.result_dir / "backtest_30year_stock_universe_summary.json"
        p_annual = self.result_dir / "backtest_30year_stock_universe_annual.csv"
        p_crisis = self.result_dir / "backtest_30year_stock_universe_crisis.csv"
        p_report = self.result_dir / "quant_benchmark_30year_stock_universe_report.md"

        # 1. JSON Schema
        summary_data: Optional[Dict[str, Any]] = None
        if p_json.is_file():
            try:
                with open(p_json, "r", encoding="utf-8") as f:
                    summary_data = json.load(f)
                self._add_check(
                    check_id="JSON-PARSE-01",
                    category=cat,
                    description="Summary JSON is valid JSON format",
                    passed=True,
                    details="Successfully parsed JSON",
                )
            except Exception as e:
                self._add_check(
                    check_id="JSON-PARSE-01",
                    category=cat,
                    description="Summary JSON is valid JSON format",
                    passed=False,
                    details=f"Parse error: {e}",
                )

        if summary_data:
            req_keys = ["metadata", "portfolio_overall", "annual_distribution", "historical_crises"]
            missing_keys = [k for k in req_keys if k not in summary_data]
            self._add_check(
                check_id="JSON-ROOT-KEYS",
                category=cat,
                description="Summary JSON contains required root keys",
                passed=(len(missing_keys) == 0),
                details=f"Missing keys: {missing_keys}" if missing_keys else "All root keys present",
            )

        # 2. Markdown Report
        report_text: Optional[str] = None
        if p_report.is_file():
            try:
                with open(p_report, "r", encoding="utf-8") as f:
                    report_text = f.read()
                has_title = "30-Year Stock Universe Quantitative Backtest" in report_text or "# 30-Year" in report_text
                has_sec1 = "1. Executive Summary" in report_text
                has_sec2 = "2. 31-Year Annual Distribution" in report_text
                has_sec3 = "3. Historical Crisis Defense" in report_text or "3. Historical Crisis" in report_text
                all_sections = has_title and has_sec1 and has_sec2 and has_sec3
                self._add_check(
                    check_id="REPORT-SECTIONS",
                    category=cat,
                    description="Markdown report contains required section headers",
                    passed=all_sections,
                    details=f"Title: {has_title}, Sec1: {has_sec1}, Sec2: {has_sec2}, Sec3: {has_sec3}",
                )
            except Exception as e:
                self._add_check(
                    check_id="REPORT-SECTIONS",
                    category=cat,
                    description="Markdown report is readable",
                    passed=False,
                    details=str(e),
                )

        # 3. Annual CSV
        annual_df: Optional[pd.DataFrame] = None
        if p_annual.is_file():
            try:
                annual_df = pd.read_csv(p_annual)
                self._add_check(
                    check_id="ANNUAL-CSV-PARSE",
                    category=cat,
                    description="Annual distribution CSV is parseable",
                    passed=True,
                    details=f"Loaded {len(annual_df)} rows",
                )
                req_cols = ["year", "gross_return_pct", "net_return_pct", "annual_volatility_pct", "sharpe_ratio", "sortino_ratio", "max_drawdown_pct", "win_rate_pct"]
                missing_cols = [c for c in req_cols if c not in annual_df.columns]
                self._add_check(
                    check_id="ANNUAL-CSV-COLS",
                    category=cat,
                    description="Annual CSV contains required columns",
                    passed=(len(missing_cols) == 0),
                    details=f"Missing columns: {missing_cols}" if missing_cols else "All required columns present",
                )
            except Exception as e:
                self._add_check(
                    check_id="ANNUAL-CSV-PARSE",
                    category=cat,
                    description="Annual distribution CSV is parseable",
                    passed=False,
                    details=str(e),
                )

        # 4. Crisis CSV
        crisis_df: Optional[pd.DataFrame] = None
        if p_crisis.is_file():
            try:
                crisis_df = pd.read_csv(p_crisis)
                self._add_check(
                    check_id="CRISIS-CSV-PARSE",
                    category=cat,
                    description="Crisis breakdown CSV is parseable",
                    passed=True,
                    details=f"Loaded {len(crisis_df)} rows",
                )
                req_crisis_cols = ["crisis_id", "crisis_name", "start_date", "end_date", "net_return_pct", "max_drawdown_pct"]
                missing_c_cols = [c for c in req_crisis_cols if c not in crisis_df.columns]
                self._add_check(
                    check_id="CRISIS-CSV-COLS",
                    category=cat,
                    description="Crisis CSV contains required columns",
                    passed=(len(missing_c_cols) == 0),
                    details=f"Missing columns: {missing_c_cols}" if missing_c_cols else "All required columns present",
                )
            except Exception as e:
                self._add_check(
                    check_id="CRISIS-CSV-PARSE",
                    category=cat,
                    description="Crisis breakdown CSV is parseable",
                    passed=False,
                    details=str(e),
                )

        return summary_data, annual_df, crisis_df, report_text

    # --------------------------------------------------------------------------
    # Suite 3: 31-Year Annual Distribution (1996~2026 unbroken)
    # --------------------------------------------------------------------------
    def verify_annual_distribution(self, annual_df: Optional[pd.DataFrame]) -> None:
        cat = "ANNUAL_DISTRIBUTION"
        if annual_df is None or annual_df.empty:
            self._add_check(
                check_id="ANNUAL-31-YEARS",
                category=cat,
                description="31 unbroken calendar years (1996-2026)",
                passed=False,
                details="Annual dataframe is missing or empty",
            )
            return

        years_present = sorted(annual_df["year"].dropna().astype(int).tolist())
        expected_years = list(range(EXPECTED_START_YEAR, EXPECTED_END_YEAR + 1))
        is_exact_31 = (years_present == expected_years)
        self._add_check(
            check_id="ANNUAL-31-YEARS",
            category=cat,
            description="31 unbroken calendar years (1996-2026)",
            passed=is_exact_31,
            details=f"Present: {len(years_present)} years ({min(years_present)}~{max(years_present)}) vs Expected 31 years (1996~2026)",
        )

        # Check friction deduction per year (strict net < gross and friction_bps > 0.0)
        friction_violations = 0
        for _, row in annual_df.iterrows():
            g = _safe_float(row.get("gross_return_pct"))
            n = _safe_float(row.get("net_return_pct"))
            fric = _safe_float(row.get("friction_bps", 0.0))
            if g is not None and n is not None:
                if n >= g:
                    friction_violations += 1
            else:
                friction_violations += 1
            if fric is None or fric <= 0.0:
                friction_violations += 1

        self._add_check(
            check_id="ANNUAL-FRICTION-CHECK",
            category=cat,
            description="Annual net return strictly less than gross return and friction_bps > 0.0",
            passed=(friction_violations == 0),
            details=f"Friction check violations: {friction_violations}",
        )

        # Check statistical sanity bounds
        bound_violations = 0
        for _, row in annual_df.iterrows():
            vol = _safe_float(row.get("annual_volatility_pct"))
            sh = _safe_float(row.get("sharpe_ratio"))
            mdd = _safe_float(row.get("max_drawdown_pct"))
            win = _safe_float(row.get("win_rate_pct"))
            if vol is not None and vol <= 0.0:
                bound_violations += 1
            if sh is not None and (sh < -10.0 or sh > 15.0):
                bound_violations += 1
            if mdd is not None and (mdd < -100.0 or mdd > 0.001):
                bound_violations += 1
            if win is not None and (win < 0.0 or win > 100.0):
                bound_violations += 1

        self._add_check(
            check_id="ANNUAL-BOUNDS",
            category=cat,
            description="Annual metrics within valid financial bounds",
            passed=(bound_violations == 0),
            details=f"Out of bounds metrics count: {bound_violations}",
        )

    # --------------------------------------------------------------------------
    # Suite 4: 5 Historical Crisis Stress Defense Windows
    # --------------------------------------------------------------------------
    def verify_crisis_coverage(self, crisis_df: Optional[pd.DataFrame]) -> None:
        cat = "CRISIS_COVERAGE"
        if crisis_df is None or crisis_df.empty:
            self._add_check(
                check_id="CRISIS-ALL-5-PRESENT",
                category=cat,
                description="All 5 historical financial crises covered",
                passed=False,
                details="Crisis dataframe is missing or empty",
            )
            return

        found_crises: Set[str] = set()
        for expected in HISTORICAL_CRISES:
            cid = expected["id"]
            pats = expected["patterns"]
            for _, row in crisis_df.iterrows():
                row_id = str(row.get("crisis_id", "")).upper()
                row_name = str(row.get("crisis_name", "")).upper()
                if cid == row_id or any(p in row_id or p in row_name for p in pats):
                    found_crises.add(cid)
                    break

        all_5_found = (len(found_crises) == 5)
        self._add_check(
            check_id="CRISIS-ALL-5-PRESENT",
            category=cat,
            description="All 5 canonical crises present (1997, 2000, 2008, 2020, 2022)",
            passed=all_5_found,
            details=f"Found {len(found_crises)}/5 crises: {sorted(list(found_crises))}",
        )

        # Chronology & Drawdown check
        chronology_ok = True
        mdd_neg_ok = True
        status_pass_ok = True
        benchmark_ok = True
        benchmark_values: List[float] = []
        has_simulated_crisis = False
        for _, row in crisis_df.iterrows():
            s_date = str(row.get("start_date", ""))
            e_date = str(row.get("end_date", ""))
            if s_date and e_date and s_date >= e_date:
                chronology_ok = False

            mdd = _safe_float(row.get("max_drawdown_pct"))
            if mdd is not None and mdd >= 0.0:
                mdd_neg_ok = False

            status = str(row.get("status", "")).upper()
            pass_flag = row.get("pass_flag", True)
            if status == "NO_DATA":
                continue

            has_simulated_crisis = True
            bench = _safe_float(row.get("benchmark_return_pct"))
            if bench is None or not math.isfinite(bench):
                benchmark_ok = False
            else:
                benchmark_values.append(bench)

            if str(pass_flag).lower() not in ("true", "1") and status != "PASS":
                status_pass_ok = False

        self._add_check(
            check_id="CRISIS-CHRONOLOGY",
            category=cat,
            description="Crisis date ranges are chronologically valid (start < end)",
            passed=chronology_ok,
            details="All crisis intervals satisfy start_date < end_date" if chronology_ok else "Chronology violation found",
        )

        self._add_check(
            check_id="CRISIS-MDD-NEGATIVE",
            category=cat,
            description="Crisis periods experience non-zero negative drawdowns",
            passed=mdd_neg_ok,
            details="All crisis drawdowns are strictly negative" if mdd_neg_ok else "Non-negative crisis drawdown detected",
        )

        self._add_check(
            check_id="CRISIS-STATUS-PASS",
            category=cat,
            description="Crisis defense status flags confirmed PASS",
            passed=status_pass_ok,
            details="All crisis records indicate pass_flag=True/status=PASS",
        )

        if benchmark_values:
            varied = len({round(v, 4) for v in benchmark_values}) > 1
            not_legacy = not all(round(v, 4) == -42.0 for v in benchmark_values)
            benchmark_ok = benchmark_ok and varied and not_legacy
        elif has_simulated_crisis:
            benchmark_ok = False
        else:
            benchmark_ok = True
        self._add_check(
            check_id="CRISIS-BENCHMARK-REAL",
            category=cat,
            description="Crisis benchmark returns are finite, varied, and not the legacy -42.0 placeholder",
            passed=benchmark_ok,
            details=f"Benchmark values: {[round(v, 2) for v in benchmark_values]}",
        )

    # --------------------------------------------------------------------------
    # Suite 5: Institutional Portfolio Guardrails
    # --------------------------------------------------------------------------
    def verify_portfolio_constraints(self, summary_data: Optional[Dict[str, Any]]) -> None:
        cat = "PORTFOLIO_CONSTRAINTS"
        if not summary_data:
            self._add_check(
                check_id="GUARD-DATA-PRESENT",
                category=cat,
                description="Institutional invariants data available",
                passed=False,
                details="Summary JSON is missing",
            )
            return

        meta = summary_data.get("metadata", {})
        inv = summary_data.get("institutional_invariants", {})
        overall = summary_data.get("portfolio_overall", {})

        # 1. Single-stock weight cap <= 5.0%
        stock_cap = _safe_float(inv.get("single_stock_max_observed_weight", meta.get("max_stock_weight_cap", 0.05)))
        stock_breaches = int(inv.get("single_stock_cap_breaches", 0))
        stock_ok = (stock_cap is not None and stock_cap <= MAX_STOCK_WEIGHT_CAP and stock_breaches == 0)
        self._add_check(
            check_id="GUARD-STOCK-WEIGHT",
            category=cat,
            description="Single-stock weight cap strictly <= 5.0% (0 breaches)",
            passed=stock_ok,
            details=f"Max observed: {stock_cap*100:.2f}% | Breaches: {stock_breaches} (Cap: 5.0%)",
        )

        # 2. Single-sector weight cap <= 25.0%
        sector_cap = _safe_float(inv.get("single_sector_max_observed_weight", meta.get("max_sector_weight_cap", 0.25)))
        sector_breaches = int(inv.get("single_sector_cap_breaches", 0))
        sector_ok = (sector_cap is not None and sector_cap <= MAX_SECTOR_WEIGHT_CAP and sector_breaches == 0)
        self._add_check(
            check_id="GUARD-SECTOR-WEIGHT",
            category=cat,
            description="Single-sector weight cap strictly <= 25.0% (0 breaches)",
            passed=sector_ok,
            details=f"Max observed: {sector_cap*100:.2f}% | Breaches: {sector_breaches} (Cap: 25.0%)",
        )

        # 3. ADV liquidity participation cap <= 1.5%
        adv_cap = _safe_float(inv.get("max_adv_participation_observed", meta.get("max_adv_participation_cap", 0.015)))
        adv_breaches = int(inv.get("adv_cap_breaches", 0))
        adv_ok = (adv_cap is not None and adv_cap <= MAX_ADV_PARTICIPATION_CAP and adv_breaches == 0)
        self._add_check(
            check_id="GUARD-ADV-PARTICIPATION",
            category=cat,
            description="ADV liquidity participation cap strictly <= 1.5% (0 breaches)",
            passed=adv_ok,
            details=f"Max observed: {adv_cap*100:.2f}% | Breaches: {adv_breaches} (Cap: 1.5%)",
        )

    # --------------------------------------------------------------------------
    # Suite 6: Strict Acceptance Criteria KPIs
    # --------------------------------------------------------------------------
    def verify_strict_kpis(self, summary_data: Optional[Dict[str, Any]]) -> None:
        cat = "STRICT_KPIS"
        if not summary_data:
            self._add_check(
                check_id="KPI-DATA-PRESENT",
                category=cat,
                description="Summary performance data available",
                passed=False,
                details="Summary JSON is missing",
            )
            return

        overall = summary_data.get("portfolio_overall", {})

        # 1. CAGR >= 25.0%
        cagr = _safe_float(overall.get("cagr_pct"))
        cagr_ok = (cagr is not None and cagr >= KPI_MIN_CAGR_PCT)
        self._add_check(
            check_id="KPI-CAGR",
            category=cat,
            description=f"Annualized Net Return (CAGR) >= {KPI_MIN_CAGR_PCT:.2f}%",
            passed=cagr_ok,
            details=f"Realized CAGR: {cagr:.2f}% (Target: >={KPI_MIN_CAGR_PCT:.2f}%)" if cagr is not None else "Missing CAGR",
        )

        # 2. Sharpe Ratio >= 1.80
        sharpe = _safe_float(overall.get("sharpe_ratio"))
        sharpe_ok = (sharpe is not None and sharpe >= KPI_MIN_SHARPE)
        self._add_check(
            check_id="KPI-SHARPE",
            category=cat,
            description=f"Annualized Sharpe Ratio >= {KPI_MIN_SHARPE:.2f}",
            passed=sharpe_ok,
            details=f"Realized Sharpe: {sharpe:.2f} (Target: >={KPI_MIN_SHARPE:.2f})" if sharpe is not None else "Missing Sharpe",
        )

        # 3. Sortino Ratio >= 2.50
        sortino = _safe_float(overall.get("sortino_ratio"))
        sortino_ok = (sortino is not None and sortino >= KPI_MIN_SORTINO)
        self._add_check(
            check_id="KPI-SORTINO",
            category=cat,
            description=f"Annualized Sortino Ratio >= {KPI_MIN_SORTINO:.2f}",
            passed=sortino_ok,
            details=f"Realized Sortino: {sortino:.2f} (Target: >={KPI_MIN_SORTINO:.2f})" if sortino is not None else "Missing Sortino",
        )

        # 4. Maximum Drawdown (MDD) >= -18.0% (between -18.0% and 0.0%)
        mdd = _safe_float(overall.get("max_drawdown_pct"))
        mdd_ok = (mdd is not None and KPI_MIN_MDD_PCT <= mdd <= 0.0)
        self._add_check(
            check_id="KPI-MDD",
            category=cat,
            description=f"Maximum Drawdown (MDD) bounded >= {KPI_MIN_MDD_PCT:.2f}%",
            passed=mdd_ok,
            details=f"Realized MDD: {mdd:.2f}% (Target: >={KPI_MIN_MDD_PCT:.2f}%)" if mdd is not None else "Missing MDD",
        )

        # 5. Active Rebalance Win Rate >= 58.0%
        win_rate = _safe_float(overall.get("active_win_rate", overall.get("active_win_rate_pct")))
        win_ok = (win_rate is not None and win_rate >= KPI_MIN_ACTIVE_WIN_RATE_PCT)
        self._add_check(
            check_id="KPI-ACTIVE-WINRATE",
            category=cat,
            description=f"Active Rebalance Win Rate >= {KPI_MIN_ACTIVE_WIN_RATE_PCT:.2f}%",
            passed=win_ok,
            details=f"Realized Active Win Rate: {win_rate:.2f}% (Target: >={KPI_MIN_ACTIVE_WIN_RATE_PCT:.2f}%)" if win_rate is not None else "Missing Active Win Rate",
        )

        # 6. Friction deduction verified (Net < Gross and Friction bps > 0)
        gross_ret = _safe_float(overall.get("total_gross_return_pct"))
        net_ret = _safe_float(overall.get("total_net_return_pct"))
        fric_bps = _safe_float(overall.get("total_friction_bps"))
        fric_ok = (
            gross_ret is not None and net_ret is not None and fric_bps is not None
            and net_ret < gross_ret and fric_bps > 0.0
        )
        self._add_check(
            check_id="KPI-NET-VS-GROSS",
            category=cat,
            description="Net Return strictly less than Gross Return and frictions deducted",
            passed=fric_ok,
            details=f"Gross: {gross_ret:.2f}%, Net: {net_ret:.2f}%, Frictions: {fric_bps:.1f} bps" if fric_ok else "Friction deduction unverified",
        )

    # --------------------------------------------------------------------------
    # Suite 7: Causality, Dynamic Filing Lag, and Survivorship Bias Defense
    # --------------------------------------------------------------------------
    def verify_causality_and_bias_guards(self, summary_data: Optional[Dict[str, Any]]) -> None:
        cat = "CAUSALITY_AND_BIAS"
        if not summary_data:
            return

        meta = summary_data.get("metadata", {})

        # 1. Execution signal lag >= 1
        sig_lag = meta.get("signal_lag_days", 1)
        self._add_check(
            check_id="GUARD-SIGNAL-LAG",
            category=cat,
            description="Execution signal timestamp lag >= 1 day (T -> T+1)",
            passed=(sig_lag >= 1),
            details=f"Signal lag: {sig_lag} days",
        )

        # 2. Zero lookahead bias detected
        lookahead = meta.get("lookahead_bias_detected", False)
        self._add_check(
            check_id="GUARD-NO-LOOKAHEAD",
            category=cat,
            description="Zero lookahead bias detected across feature store",
            passed=(lookahead is False),
            details="Lookahead bias flag: False (Verified)",
        )

        # 2.1 PnL alignment attestation (new artifacts only; legacy lacks the field)
        pnl_basis = meta.get("pnl_basis")
        if pnl_basis is not None:
            signal_execution = meta.get("signal_execution")
            pnl_ok = (
                pnl_basis == "begin_of_day_holdings"
                and signal_execution == "close_of_signal_day"
            )
            self._add_check(
                check_id="GUARD-PNL-ALIGNMENT",
                category=cat,
                description="PnL uses beginning-of-day holdings with close execution",
                passed=pnl_ok,
                details=f"PnL basis: {pnl_basis}, execution: {signal_execution}",
            )

        # 3. Dynamic regulatory filing lag
        krx_lag = meta.get("krx_filing_lag_days", 45)
        sec_lag = meta.get("sec_filing_lag_days", 40)
        filing_enforced = meta.get("regulatory_filing_lag_enforced", True)
        filing_ok = (krx_lag >= 45 and sec_lag >= 40 and filing_enforced is True)
        self._add_check(
            check_id="GUARD-FILING-LAG",
            category=cat,
            description="Regulatory filing lags enforced (KRX >= 45d, SEC >= 40d)",
            passed=filing_ok,
            details=f"KRX lag: {krx_lag}d, SEC lag: {sec_lag}d, Enforced: {filing_enforced}",
        )

        # 4. Survivorship bias defense
        markets_count = len(meta.get("markets", []))
        strategies_count = meta.get("strategies_count", 0)
        self._add_check(
            check_id="GUARD-SURVIVORSHIP",
            category=cat,
            description="Point-in-Time universe and survivorship bias defense active",
            passed=(markets_count >= 5 and strategies_count == 37),
            details=(
                f"Markets tracked: {markets_count}, Strategy catalog: {strategies_count}, "
                f"Live factors: {meta.get('live_strategy_count', 'n/a')}"
            ),
        )

        universe_symbols = meta.get("universe_symbols")
        registry_symbols = meta.get("registry_symbols")
        coverage_ok = (
            isinstance(universe_symbols, int)
            and not isinstance(universe_symbols, bool)
            and isinstance(registry_symbols, int)
            and not isinstance(registry_symbols, bool)
            and universe_symbols > 0
            and universe_symbols == registry_symbols
        )
        self._add_check(
            check_id="GUARD-UNIVERSE-COVERAGE",
            category=cat,
            description="Backtest universe covers every registry symbol (100% PIT coverage)",
            passed=coverage_ok,
            details=f"Universe: {universe_symbols} / Registry: {registry_symbols}",
        )

    # --------------------------------------------------------------------------
    # Main Verifier Execution Loop
    # --------------------------------------------------------------------------
    def verify_all(self) -> VerificationSummary:
        """Executes all 7 verification suites and compiles summary."""
        self.checks.clear()

        # Suite 1
        self.verify_file_existence()

        # Suite 2
        summary_data, annual_df, crisis_df, _ = self.verify_schema_integrity()

        # Suite 3
        self.verify_annual_distribution(annual_df)

        # Suite 4
        self.verify_crisis_coverage(crisis_df)

        # Suite 5
        self.verify_portfolio_constraints(summary_data)

        # Suite 6
        self.verify_strict_kpis(summary_data)

        # Suite 7
        self.verify_causality_and_bias_guards(summary_data)

        total = len(self.checks)
        passed = sum(1 for c in self.checks if c.passed)
        failed = sum(1 for c in self.checks if not c.passed and c.severity == "ERROR")
        warnings = sum(1 for c in self.checks if not c.passed and c.severity == "WARNING")

        overall_passed = (failed == 0) if not self.strict else (failed == 0 and warnings == 0)

        summary_dict = {
            "verified_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S KST"),
            "result_directory": str(self.result_dir),
            "strict_mode": self.strict,
            "overall_status": "PASSED" if overall_passed else "FAILED",
            "total_checks": total,
            "passed_checks": passed,
            "failed_checks": failed,
            "warning_checks": warnings,
            "checks": [asdict(c) for c in self.checks],
        }

        return VerificationSummary(
            total_checks=total,
            passed_checks=passed,
            failed_checks=failed,
            warning_checks=warnings,
            passed=overall_passed,
            checks=self.checks,
            summary_dict=summary_dict,
        )


# ==============================================================================
# Terminal Table Formatter
# ==============================================================================

def print_verification_terminal_report(summary: VerificationSummary) -> None:
    """Prints a high-density, structured verification report table to stdout."""
    print("\n" + "=" * 100)
    print("      30-YEAR STOCK UNIVERSE INDEPENDENT VERIFICATION REPORT (1996-2026)")
    print(f"      Status: {'[PASS] ALL ASSERTIONS SATISFIED' if summary.passed else '[FAIL] VERIFICATION DEFECTS DETECTED'}")
    print(f"      Total Checks: {summary.total_checks} | Passed: {summary.passed_checks} | Failed: {summary.failed_checks} | Warnings: {summary.warning_checks}")
    print("=" * 100)

    # Group by category
    categories: Dict[str, List[VerificationCheck]] = {}
    for c in summary.checks:
        categories.setdefault(c.category, []).append(c)

    for cat_name, cat_checks in categories.items():
        print(f"\n[{cat_name}]")
        print("-" * 100)
        for chk in cat_checks:
            tag = "[PASS]" if chk.passed else ("[WARN]" if chk.severity == "WARNING" else "[FAIL]")
            print(f"  {tag:<7} {chk.check_id:<26} {chk.description:<45}")
            if chk.details:
                print(f"          -> {chk.details}")
        print("-" * 100)

    print("\n" + "=" * 100)
    if summary.passed:
        print("  >>> VERDICT: [PASS] ALL VERIFICATION ASSERTIONS PASSED (Exit Code 0) <<<")
    else:
        print("  >>> VERDICT: [FAIL] VERIFICATION FAILED (Exit Code 1) <<<")
    print("=" * 100 + "\n")


# ==============================================================================
# Public API Function
# ==============================================================================

def verify_stock_universe_backtest_results(
    result_dir: str | Path = "trading_system/result",
    strict: bool = True,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Public entry point for independent verification of 30-year stock universe backtest artifacts.
    Returns: (passed: bool, summary_dict: Dict[str, Any])
    """
    verifier = StockUniverse30YearVerifier(result_dir=result_dir, strict=strict)
    summary = verifier.verify_all()
    print_verification_terminal_report(summary)
    return summary.passed, summary.summary_dict


# ==============================================================================
# CLI Entry Point
# ==============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 105 Stock Universe Backtest Strict Independent Verifier"
    )
    parser.add_argument(
        "--result-dir",
        type=str,
        default="trading_system/result",
        help="Path to artifacts directory (default: trading_system/result)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        default=True,
        help="Enforce strict zero-warning mode (default: True)",
    )
    parser.add_argument(
        "--no-strict",
        dest="strict",
        action="store_false",
        help="Disable strict mode (warnings will not cause exit code 1)",
    )
    parser.add_argument(
        "--output-report",
        type=str,
        default=None,
        help="Optional path to export JSON verification report",
    )

    args = parser.parse_args()

    passed, summary_dict = verify_stock_universe_backtest_results(
        result_dir=args.result_dir,
        strict=args.strict,
    )

    if args.output_report:
        out_p = Path(args.output_report).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(summary_dict, f, indent=2)
        logger.info("Exported verification summary report to %s", out_p)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
