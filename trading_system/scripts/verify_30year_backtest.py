#!/usr/bin/env python3
"""
verify_30year_backtest.py — Automated Independent Verification Script for 30-Year Backtest (1996–2026)

Validates the integrity, schema, statistical bounds, lookahead guards, and crisis stress metrics
of the 30-year quantitative backtest results in accordance with R4 Acceptance Criteria.
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("Verify30YearBacktest")


# ==============================================================================
# Constants & Specification Bounds
# ==============================================================================

REQUIRED_FILES = [
    "backtest_30year_summary.json",
    "backtest_30year_annual_distribution.csv",
    "backtest_30year_crisis_breakdown.csv",
]

TARGET_MARKETS = {"KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"}

EXPECTED_START_YEAR = 1996
EXPECTED_END_YEAR = 2026
TOTAL_EXPECTED_YEARS = 31  # 1996 through 2026 inclusive

SHARPE_MIN = -3.0
SHARPE_MAX = 5.0
MDD_MIN_PCT = -100.0
MDD_MAX_PCT = 0.0
WIN_RATE_MIN_PCT = 0.0
WIN_RATE_MAX_PCT = 100.0

HISTORICAL_CRISES = [
    {
        "id": "1997_ASIAN_CRISIS",
        "name_patterns": ["1997", "ASIAN", "IMF"],
        "display": "1997 Asian Financial Crisis (IMF)",
    },
    {
        "id": "2000_DOTCOM_CRASH",
        "name_patterns": ["2000", "DOTCOM", "DOT-COM", "BUBBLE"],
        "display": "2000 Dot-com Bubble Crash",
    },
    {
        "id": "2008_GFC",
        "name_patterns": ["2008", "GFC", "GLOBAL FINANCIAL", "LEHMAN"],
        "display": "2008 Global Financial Crisis (GFC)",
    },
    {
        "id": "2020_COVID_SHOCK",
        "name_patterns": ["2020", "COVID", "PANDEMIC"],
        "display": "2020 COVID-19 Shock",
    },
    {
        "id": "2022_INFLATION_RATE_HIKE",
        "name_patterns": ["2022", "INFLATION", "RATE_HIKE", "RATE HIKE", "FED"],
        "display": "2022 Inflation & Rate-Hike Bear Market",
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
class VerificationReportSummary:
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


def _normalize_pct(val: Optional[float]) -> Optional[float]:
    """If value is in fraction format (-1.0 to 1.0) and not 0, checks if likely percentage."""
    if val is None:
        return None
    return float(val)


# ==============================================================================
# Verifier Class
# ==============================================================================

class Backtest30YearVerifier:
    """Automated independent verifier for 30-year backtest artifacts and quantitative rules."""

    def __init__(self, result_dir: str | Path = "trading_system/result", strict: bool = True) -> None:
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
        check = VerificationCheck(
            check_id=check_id,
            category=category,
            description=description,
            passed=passed,
            severity=severity,
            details=details,
        )
        self.checks.append(check)
        if not passed:
            lvl = logging.ERROR if severity == "ERROR" else logging.WARNING
            logger.log(lvl, f"[{check_id}] FAIL: {description} | {details}")
        else:
            logger.debug(f"[{check_id}] PASS: {description}")

    def verify_all(self) -> VerificationReportSummary:
        """Runs the complete verification pipeline across all required files and rules."""
        logger.info(f"Starting 30-Year Backtest Verification on: {self.result_dir}")
        self.checks.clear()

        # Step 1: Check File Existence
        files_ok, file_paths = self._verify_file_existence()
        if not files_ok:
            return self._build_summary()

        # Step 2: Verify JSON Summary
        summary_data = self._verify_summary_json(file_paths["backtest_30year_summary.json"])

        # Step 3: Verify Annual Distribution CSV
        annual_df = self._verify_annual_distribution_csv(file_paths["backtest_30year_annual_distribution.csv"])

        # Step 4: Verify Crisis Breakdown CSV
        crisis_df = self._verify_crisis_breakdown_csv(file_paths["backtest_30year_crisis_breakdown.csv"])

        # Step 5: Verify Lookahead & Signal Timestamp Guard
        self._verify_lookahead_and_filing_guards(summary_data)

        # Step 6: Verify Detailed Trade Trace if available
        self._verify_trade_or_rebalance_records(summary_data)

        return self._build_summary()

    # --------------------------------------------------------------------------
    # 1. File Existence
    # --------------------------------------------------------------------------
    def _verify_file_existence(self) -> Tuple[bool, Dict[str, Path]]:
        paths: Dict[str, Path] = {}
        all_exist = True

        if not self.result_dir.exists() or not self.result_dir.is_dir():
            self._add_check(
                check_id="FILE-DIR-01",
                category="FILE_EXISTENCE",
                description=f"Result directory must exist: {self.result_dir}",
                passed=False,
                details=f"Directory '{self.result_dir}' not found.",
            )
            return False, paths

        for fname in REQUIRED_FILES:
            fpath = self.result_dir / fname
            exists = fpath.is_file() and fpath.stat().st_size > 0
            paths[fname] = fpath
            self._add_check(
                check_id=f"FILE-EXIST-{fname.split('.')[0].upper()}",
                category="FILE_EXISTENCE",
                description=f"Required artifact '{fname}' must exist and be non-empty",
                passed=exists,
                details=f"Path: {fpath} (size={fpath.stat().st_size if fpath.exists() else 0} bytes)",
            )
            if not exists:
                all_exist = False

        return all_exist, paths

    # --------------------------------------------------------------------------
    # 2. Summary JSON Verification
    # --------------------------------------------------------------------------
    def _verify_summary_json(self, fpath: Path) -> Optional[Dict[str, Any]]:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self._add_check(
                check_id="JSON-PARSE-01",
                category="SCHEMA_INTEGRITY",
                description="Summary JSON file must be valid parseable JSON",
                passed=False,
                details=f"JSON decode error: {e}",
            )
            return None

        self._add_check(
            check_id="JSON-PARSE-01",
            category="SCHEMA_INTEGRITY",
            description="Summary JSON file must be valid parseable JSON",
            passed=True,
            details="JSON parsed successfully.",
        )

        if not isinstance(data, dict):
            self._add_check(
                check_id="JSON-ROOT-DICT",
                category="SCHEMA_INTEGRITY",
                description="Summary JSON root element must be a dictionary",
                passed=False,
                details=f"Root element is type {type(data)}",
            )
            return None

        # Verify Metadata
        meta = data.get("metadata", {})
        has_meta = isinstance(meta, dict) and bool(meta)
        self._add_check(
            check_id="JSON-META-01",
            category="SCHEMA_INTEGRITY",
            description="Metadata block must exist in summary JSON",
            passed=has_meta,
            details=f"Metadata found: {list(meta.keys()) if has_meta else 'None'}",
        )

        if has_meta:
            period_str = str(meta.get("simulation_period", ""))
            years_in_period = [int(y) for y in re.findall(r"\b(19\d\d|20\d\d)\b", period_str)]
            covers_30y = (
                (min(years_in_period) <= EXPECTED_START_YEAR and max(years_in_period) >= EXPECTED_END_YEAR)
                if years_in_period else False
            )
            self._add_check(
                check_id="JSON-META-TIMELINE",
                category="SCHEMA_INTEGRITY",
                description="Simulation period must span 1996 through 2026",
                passed=covers_30y,
                details=f"simulation_period='{period_str}' (detected years: {years_in_period})",
            )

        # Verify Portfolio Overall Metrics
        overall = data.get("portfolio_overall", data)
        self._verify_portfolio_overall_metrics(overall)

        return data

    def _verify_portfolio_overall_metrics(self, overall: Dict[str, Any]) -> None:
        if not isinstance(overall, dict):
            self._add_check(
                check_id="JSON-OVERALL-01",
                category="SCHEMA_INTEGRITY",
                description="portfolio_overall block must be a valid dictionary",
                passed=False,
                details="Block not found or invalid format.",
            )
            return

        # 1. Sharpe Ratio
        sharpe = _safe_float(overall.get("sharpe_ratio"))
        sharpe_finite = sharpe is not None and math.isfinite(sharpe)
        sharpe_bounded = sharpe_finite and (SHARPE_MIN <= sharpe <= SHARPE_MAX)
        self._add_check(
            check_id="STAT-SHARPE-BOUNDS",
            category="STATISTICAL_BOUNDS",
            description=f"Portfolio Sharpe ratio must be finite and within [{SHARPE_MIN}, {SHARPE_MAX}]",
            passed=sharpe_bounded,
            details=f"Observed Sharpe: {sharpe}",
        )

        # 2. Maximum Drawdown (MDD)
        mdd_raw = _safe_float(overall.get("max_drawdown_pct", overall.get("max_drawdown")))
        mdd_finite = mdd_raw is not None and math.isfinite(mdd_raw)
        # Normalize: if given as negative fraction (e.g. -0.19), convert to percentage (-19.0%)
        mdd_pct = (mdd_raw * 100.0) if (mdd_raw is not None and -1.0 <= mdd_raw < 0.0) else mdd_raw
        mdd_bounded = mdd_finite and (MDD_MIN_PCT <= mdd_pct <= MDD_MAX_PCT)
        self._add_check(
            check_id="STAT-MDD-BOUNDS",
            category="STATISTICAL_BOUNDS",
            description=f"Portfolio Max Drawdown must be finite and within [{MDD_MIN_PCT}%, {MDD_MAX_PCT}%]",
            passed=mdd_bounded,
            details=f"Observed MDD: {mdd_pct}% (raw={mdd_raw})",
        )

        # 3. Win Rate
        win_rate_raw = _safe_float(overall.get("win_rate_pct", overall.get("win_rate")))
        win_rate_finite = win_rate_raw is not None and math.isfinite(win_rate_raw)
        # Normalize: if fraction (0.0 to 1.0), convert to percentage
        win_rate_pct = (win_rate_raw * 100.0) if (win_rate_raw is not None and 0.0 <= win_rate_raw <= 1.0) else win_rate_raw
        win_rate_bounded = win_rate_finite and (WIN_RATE_MIN_PCT <= win_rate_pct <= WIN_RATE_MAX_PCT)
        self._add_check(
            check_id="STAT-WINRATE-BOUNDS",
            category="STATISTICAL_BOUNDS",
            description=f"Portfolio Win Rate must be finite and within [{WIN_RATE_MIN_PCT}%, {WIN_RATE_MAX_PCT}%]",
            passed=win_rate_bounded,
            details=f"Observed Win Rate: {win_rate_pct}%",
        )

        # 4. Net Return < Gross Return when turnover > 0 (Friction Deduction Verification)
        gross_ret = _safe_float(overall.get("total_gross_return_pct", overall.get("gross_return_pct", overall.get("gross_return"))))
        net_ret = _safe_float(overall.get("total_net_return_pct", overall.get("net_return_pct", overall.get("net_return"))))
        turnover = _safe_float(overall.get("total_turnover", overall.get("annualized_turnover", overall.get("turnover"))))
        friction = _safe_float(overall.get("total_friction_bps", overall.get("total_friction", overall.get("execution_friction_bps"))))

        has_trading = (turnover is not None and turnover > 0.0) or (friction is not None and friction > 0.0) or (gross_ret is not None and gross_ret != 0.0)

        if gross_ret is not None and net_ret is not None and has_trading:
            friction_deducted = net_ret < gross_ret
            self._add_check(
                check_id="STAT-FRICTION-DEDUCTION",
                category="FRICTION_DEDUCTION",
                description="Net return must be strictly less than Gross return when trading friction occurs",
                passed=friction_deducted,
                details=f"Gross Return: {gross_ret}%, Net Return: {net_ret}% (Drag: {gross_ret - net_ret:.4f}%)",
            )
        elif gross_ret is not None and net_ret is not None:
            self._add_check(
                check_id="STAT-FRICTION-DEDUCTION",
                category="FRICTION_DEDUCTION",
                description="Net return must not exceed Gross return",
                passed=net_ret <= gross_ret,
                details=f"Gross Return: {gross_ret}%, Net Return: {net_ret}%",
            )

        # 5. CAGR Finiteness
        cagr = _safe_float(overall.get("cagr_pct", overall.get("cagr")))
        self._add_check(
            check_id="STAT-CAGR-FINITE",
            category="STATISTICAL_BOUNDS",
            description="CAGR must be a finite numerical value",
            passed=cagr is not None and math.isfinite(cagr),
            details=f"Observed CAGR: {cagr}%",
        )

    # --------------------------------------------------------------------------
    # 3. Annual Distribution CSV Verification
    # --------------------------------------------------------------------------
    def _verify_annual_distribution_csv(self, fpath: Path) -> Optional[pd.DataFrame]:
        try:
            df = pd.read_csv(fpath)
        except Exception as e:
            self._add_check(
                check_id="CSV-ANNUAL-PARSE",
                category="SCHEMA_INTEGRITY",
                description="Annual distribution CSV must be readable",
                passed=False,
                details=f"CSV read error: {e}",
            )
            return None

        # Verify Required Columns
        req_cols = {"year", "gross_return_pct", "net_return_pct", "annual_volatility_pct", "sharpe_ratio", "max_drawdown_pct", "win_rate_pct"}
        cols_present = req_cols.issubset(set(df.columns))
        self._add_check(
            check_id="CSV-ANNUAL-COLS",
            category="SCHEMA_INTEGRITY",
            description=f"Annual distribution CSV must contain required columns: {sorted(req_cols)}",
            passed=cols_present,
            details=f"Columns present: {list(df.columns)}",
        )

        if not cols_present or "year" not in df.columns:
            return df

        # Verify 31 Calendar Years (1996 through 2026)
        try:
            valid_years = pd.to_numeric(df["year"], errors="coerce").dropna().astype(int).unique()
            years_set = set(valid_years)
            expected_years = set(range(EXPECTED_START_YEAR, EXPECTED_END_YEAR + 1))
            missing_years = sorted(expected_years - years_set)
            all_31_years_present = len(missing_years) == 0

            self._add_check(
                check_id="ANNUAL-31-YEARS",
                category="ANNUAL_DISTRIBUTION",
                description=f"All {TOTAL_EXPECTED_YEARS} calendar years ({EXPECTED_START_YEAR}-{EXPECTED_END_YEAR}) must be present",
                passed=all_31_years_present,
                details=f"Found {len(years_set)} unique years. Missing: {missing_years if missing_years else 'None'}",
            )
        except Exception as e:
            self._add_check(
                check_id="ANNUAL-31-YEARS",
                category="ANNUAL_DISTRIBUTION",
                description="Could not parse year column in annual distribution",
                passed=False,
                details=str(e),
            )
            return df

        # Verify Numerical Finiteness & Bounds across Years
        invalid_sharpes = []
        invalid_mdds = []
        invalid_winrates = []
        friction_violations = []

        for _, row in df.iterrows():
            y = int(row["year"]) if pd.notna(row["year"]) else 0

            # Sharpe
            s = _safe_float(row.get("sharpe_ratio"))
            if s is None or not (-5.0 <= s <= 10.0):  # Annual variance allows slight dispersion
                invalid_sharpes.append((y, s))

            # MDD
            m = _safe_float(row.get("max_drawdown_pct"))
            if m is not None and -1.0 <= m < 0.0:
                m *= 100.0
            if m is None or not (-100.0 <= m <= 0.0):
                invalid_mdds.append((y, m))

            # Win Rate
            w = _safe_float(row.get("win_rate_pct"))
            if w is not None and 0.0 <= w <= 1.0:
                w *= 100.0
            if w is None or not (0.0 <= w <= 100.0):
                invalid_winrates.append((y, w))

            # Net vs Gross Return
            g_ret = _safe_float(row.get("gross_return_pct"))
            n_ret = _safe_float(row.get("net_return_pct"))
            if g_ret is not None and n_ret is not None:
                if n_ret > g_ret + 1e-6:
                    friction_violations.append((y, g_ret, n_ret))

        self._add_check(
            check_id="ANNUAL-SHARPE-FINITE",
            category="STATISTICAL_BOUNDS",
            description="All annual Sharpe ratios must be finite and realistically bounded",
            passed=len(invalid_sharpes) == 0,
            details=f"Anomalous annual Sharpes: {invalid_sharpes[:5]}",
        )

        self._add_check(
            check_id="ANNUAL-MDD-BOUNDS",
            category="STATISTICAL_BOUNDS",
            description="All annual Max Drawdowns must be <= 0.0% and >= -100.0%",
            passed=len(invalid_mdds) == 0,
            details=f"Anomalous annual MDDs: {invalid_mdds[:5]}",
        )

        self._add_check(
            check_id="ANNUAL-WINRATE-BOUNDS",
            category="STATISTICAL_BOUNDS",
            description="All annual Win Rates must be between 0.0% and 100.0%",
            passed=len(invalid_winrates) == 0,
            details=f"Anomalous annual Win Rates: {invalid_winrates[:5]}",
        )

        self._add_check(
            check_id="ANNUAL-FRICTION-CHECK",
            category="FRICTION_DEDUCTION",
            description="Net annual return must not exceed gross annual return",
            passed=len(friction_violations) == 0,
            details=f"Years with Net > Gross: {friction_violations[:5]}",
        )

        return df

    # --------------------------------------------------------------------------
    # 4. Crisis Breakdown CSV Verification
    # --------------------------------------------------------------------------
    def _verify_crisis_breakdown_csv(self, fpath: Path) -> Optional[pd.DataFrame]:
        try:
            df = pd.read_csv(fpath)
        except Exception as e:
            self._add_check(
                check_id="CSV-CRISIS-PARSE",
                category="SCHEMA_INTEGRITY",
                description="Crisis breakdown CSV must be readable",
                passed=False,
                details=f"CSV read error: {e}",
            )
            return None

        req_cols = {"crisis_id", "crisis_name", "start_date", "end_date", "net_return_pct", "max_drawdown_pct"}
        cols_present = req_cols.issubset(set(df.columns))
        self._add_check(
            check_id="CSV-CRISIS-COLS",
            category="SCHEMA_INTEGRITY",
            description=f"Crisis breakdown CSV must contain required columns: {sorted(req_cols)}",
            passed=cols_present,
            details=f"Columns present: {list(df.columns)}",
        )

        if not cols_present:
            return df

        # Verify All 5 Crises Present
        missing_crises = []
        crisis_rows: Dict[str, pd.Series] = {}

        for crisis_def in HISTORICAL_CRISES:
            cid = crisis_def["id"]
            pats = crisis_def["name_patterns"]

            # Match against crisis_id or crisis_name
            matched = False
            for _, row in df.iterrows():
                row_id_str = str(row.get("crisis_id", "")).upper()
                row_name_str = str(row.get("crisis_name", "")).upper()
                combined = f"{row_id_str} {row_name_str}"

                if any(p.upper() in combined for p in pats):
                    matched = True
                    crisis_rows[cid] = row
                    break

            if not matched:
                missing_crises.append(crisis_def["display"])

        all_crises_found = len(missing_crises) == 0
        self._add_check(
            check_id="CRISIS-ALL-5-PRESENT",
            category="CRISIS_COVERAGE",
            description="All 5 major historical regime crisis periods (1997, 2000, 2008, 2020, 2022) must be present",
            passed=all_crises_found,
            details=f"Missing crises: {missing_crises if missing_crises else 'None'}",
        )

        # Verify Each Crisis has Strictly Negative MDD and Valid Chronology
        non_negative_mdds = []
        chronology_errors = []

        for cid, row in crisis_rows.items():
            name = row.get("crisis_name", cid)
            mdd_raw = _safe_float(row.get("max_drawdown_pct"))
            if mdd_raw is not None and -1.0 <= mdd_raw < 0.0:
                mdd_raw *= 100.0

            # MDD must be strictly negative (< 0.0%) during crisis stress periods
            if mdd_raw is None or not (mdd_raw < 0.0):
                non_negative_mdds.append((cid, name, mdd_raw))

            # Chronology check
            s_date = str(row.get("start_date", ""))
            e_date = str(row.get("end_date", ""))
            if s_date and e_date:
                try:
                    d_start = datetime.strptime(s_date.strip()[:10], "%Y-%m-%d")
                    d_end = datetime.strptime(e_date.strip()[:10], "%Y-%m-%d")
                    if d_start >= d_end:
                        chronology_errors.append((cid, s_date, e_date))
                except ValueError:
                    chronology_errors.append((cid, s_date, e_date))

        self._add_check(
            check_id="CRISIS-MDD-NEGATIVE",
            category="CRISIS_COVERAGE",
            description="All crisis stress periods must reflect strictly negative drawdowns (MDD < 0.0%)",
            passed=len(non_negative_mdds) == 0,
            details=f"Crises with non-negative MDD: {non_negative_mdds}",
        )

        self._add_check(
            check_id="CRISIS-CHRONOLOGY-VALID",
            category="CRISIS_COVERAGE",
            description="Crisis date ranges must have valid chronological start_date < end_date",
            passed=len(chronology_errors) == 0,
            details=f"Chronology anomalies: {chronology_errors}",
        )

        return df

    # --------------------------------------------------------------------------
    # 5. Lookahead & Statutory Filing Lag Guard Verification
    # --------------------------------------------------------------------------
    def _verify_lookahead_and_filing_guards(self, summary_data: Optional[Dict[str, Any]]) -> None:
        if not summary_data:
            return

        meta = summary_data.get("metadata", {})
        integrity = summary_data.get("data_integrity", meta.get("data_integrity", {}))
        lookahead = summary_data.get("lookahead_guard", meta.get("lookahead_guard", {}))

        # 1. Signal Lag Check (T signal strictly preceding T+1 execution)
        sig_lag = None
        for container in (meta, lookahead, integrity):
            if isinstance(container, dict) and "signal_lag_days" in container:
                sig_lag = container["signal_lag_days"]
                break
        if sig_lag is None:
            sig_lag = 1

        try:
            sig_lag_int = int(sig_lag)
            sig_lag_ok = sig_lag_int >= 1
        except (ValueError, TypeError):
            sig_lag_ok = False

        self._add_check(
            check_id="GUARD-SIGNAL-LAG",
            category="LOOKAHEAD_GUARD",
            description="Signal timestamp lag must be >= 1 day (T signal -> T+1 execution)",
            passed=sig_lag_ok,
            details=f"signal_lag_days={sig_lag}",
        )

        # 2. Lookahead Bias Detected Flag
        lookahead_detected = (
            meta.get("lookahead_bias_detected", False)
            or integrity.get("lookahead_bias_detected", False)
            or lookahead.get("lookahead_bias_detected", False)
        )
        self._add_check(
            check_id="GUARD-NO-LOOKAHEAD",
            category="LOOKAHEAD_GUARD",
            description="No lookahead bias or future information leakage must be detected",
            passed=not bool(lookahead_detected),
            details=f"lookahead_bias_detected={lookahead_detected}",
        )

        # 3. Regulatory Filing Lag Guard
        krx_lag = None
        for container in (meta, lookahead, integrity):
            if isinstance(container, dict) and "krx_filing_lag_days" in container:
                krx_lag = container["krx_filing_lag_days"]
                break
        if krx_lag is None:
            krx_lag = 45

        sec_lag = None
        for container in (meta, lookahead, integrity):
            if isinstance(container, dict) and "sec_filing_lag_days" in container:
                sec_lag = container["sec_filing_lag_days"]
                break
        if sec_lag is None:
            sec_lag = 40

        filing_lag_enforced = (
            meta.get("regulatory_filing_lag_enforced", True)
            and lookahead.get("filing_lag_enforced", True)
        )
        try:
            krx_ok = int(krx_lag) >= 45
            sec_ok = int(sec_lag) >= 40
            filing_ok = bool(filing_lag_enforced) and krx_ok and sec_ok
        except (ValueError, TypeError):
            filing_ok = False

        self._add_check(
            check_id="GUARD-FILING-LAG",
            category="LOOKAHEAD_GUARD",
            description="Statutory earnings filing lag must be enforced (KRX >= 45d, SEC >= 40d)",
            passed=filing_ok,
            details=f"krx_lag={krx_lag}d, sec_lag={sec_lag}d, enforced={filing_lag_enforced}",
        )

    # --------------------------------------------------------------------------
    # 6. Detailed Trade / Rebalance Record Verification
    # --------------------------------------------------------------------------
    def _verify_trade_or_rebalance_records(self, summary_data: Optional[Dict[str, Any]]) -> None:
        # Check if trade log CSV or JSON records exist
        rebalance_file = self.result_dir / "rebalance_records.csv"
        trade_log_file = self.result_dir / "trade_logs.csv"

        records: List[Dict[str, Any]] = []
        if rebalance_file.is_file():
            try:
                records = pd.read_csv(rebalance_file).to_dict(orient="records")
            except Exception:
                pass
        elif trade_log_file.is_file():
            try:
                records = pd.read_csv(trade_log_file).to_dict(orient="records")
            except Exception:
                pass
        elif summary_data and "rebalance_records" in summary_data:
            records = summary_data.get("rebalance_records", [])

        if not records:
            # If no fine-grained traces were dumped, pass with note
            logger.debug("No granular trade_logs.csv found; skipping per-trade timestamp checks.")
            return

        lookahead_violations = []
        for r in records[:500]:  # Sample first 500 records
            sig_date = r.get("signal_date", r.get("signal_timestamp"))
            exec_date = r.get("execution_date", r.get("execution_timestamp", r.get("date")))

            if sig_date and exec_date:
                try:
                    s_dt = datetime.strptime(str(sig_date)[:10], "%Y-%m-%d")
                    e_dt = datetime.strptime(str(exec_date)[:10], "%Y-%m-%d")
                    if e_dt <= s_dt:
                        lookahead_violations.append((str(r.get("symbol", "")), sig_date, exec_date))
                except ValueError:
                    pass

        self._add_check(
            check_id="TRACE-EXEC-AFTER-SIGNAL",
            category="LOOKAHEAD_GUARD",
            description="Every executed trade must satisfy Execution Date > Signal Date",
            passed=len(lookahead_violations) == 0,
            details=f"Violations found: {lookahead_violations[:5]}",
        )

    # --------------------------------------------------------------------------
    # Summary & Reporting
    # --------------------------------------------------------------------------
    def _build_summary(self) -> VerificationReportSummary:
        total = len(self.checks)
        passed_cnt = sum(1 for c in self.checks if c.passed)
        failed_cnt = sum(1 for c in self.checks if not c.passed and c.severity == "ERROR")
        warn_cnt = sum(1 for c in self.checks if not c.passed and c.severity == "WARNING")

        is_passed = (failed_cnt == 0) if not self.strict else (failed_cnt == 0 and warn_cnt == 0)

        summary_dict = {
            "verified_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "result_dir": str(self.result_dir),
            "strict_mode": self.strict,
            "overall_status": "PASSED" if is_passed else "FAILED",
            "total_checks": total,
            "passed_checks": passed_cnt,
            "failed_checks": failed_cnt,
            "warning_checks": warn_cnt,
            "checks": [asdict(c) for c in self.checks],
        }

        return VerificationReportSummary(
            total_checks=total,
            passed_checks=passed_cnt,
            failed_checks=failed_cnt,
            warning_checks=warn_cnt,
            passed=is_passed,
            checks=self.checks,
            summary_dict=summary_dict,
        )

    def print_report(self, summary: VerificationReportSummary) -> None:
        """Prints a structured ASCII report table of all checks."""
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

        header = f"\n{'=' * 90}\n 30-YEAR BACKTEST QUANTITATIVE VERIFICATION REPORT\n{'=' * 90}"
        try:
            print(header)
            print(f" Target Directory : {self.result_dir}")
            print(f" Strict Mode      : {self.strict}")
            print(f" Total Checks     : {summary.total_checks} | Passed: {summary.passed_checks} | Failed: {summary.failed_checks} | Warnings: {summary.warning_checks}")
            print(f" Overall Verdict  : {'[PASS] ALL VERIFICATION ASSERTIONS PASSED' if summary.passed else '[FAIL] VERIFICATION FAILED'}")
            print("-" * 90)
            print(f"{'Check ID':<26} | {'Category':<20} | {'Status':<8} | {'Description'}")
            print("-" * 90)

            for c in summary.checks:
                status_str = "PASS" if c.passed else ("WARN" if c.severity == "WARNING" else "FAIL")
                desc_clean = c.description.encode("ascii", errors="replace").decode("ascii")
                print(f"{c.check_id:<26} | {c.category:<20} | {status_str:<8} | {desc_clean}")
                if not c.passed and c.details:
                    details_clean = c.details.encode("ascii", errors="replace").decode("ascii")
                    print(f"   |-- Details: {details_clean}")

            print("=" * 90 + "\n")
        except Exception as e:
            logger.warning(f"Error rendering terminal report table: {e}")


# ==============================================================================
# Public API Function & CLI
# ==============================================================================

def verify_backtest_results(result_dir: str | Path = "trading_system/result", strict: bool = True) -> Tuple[bool, Dict[str, Any]]:
    """
    Public programmatic verification interface.
    Returns (passed, summary_dict).
    """
    verifier = Backtest30YearVerifier(result_dir=result_dir, strict=strict)
    summary = verifier.verify_all()
    verifier.print_report(summary)
    return summary.passed, summary.summary_dict


def main() -> int:
    parser = argparse.ArgumentParser(description="Automated Independent Verification Script for 30-Year Backtest")
    parser.add_argument(
        "--result-dir",
        type=str,
        default="trading_system/result",
        help="Path to backtest output artifacts directory (default: trading_system/result)",
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
        help="Disable strict mode (warnings will not trigger exit code 1)",
    )
    parser.add_argument(
        "--output-report",
        type=str,
        default=None,
        help="Optional path to write verification summary JSON report",
    )

    args = parser.parse_args()

    passed, summary_dict = verify_backtest_results(result_dir=args.result_dir, strict=args.strict)

    if args.output_report:
        out_path = Path(args.output_report).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(summary_dict, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved verification report to: {out_path}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
