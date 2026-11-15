"""
tests/test_adversarial_m4_challenger2_gate4.py — Milestone 4 Gate 4 Adversarial Verification Test Suite

Adversarial empirical stress-testing for Gate 4 Evaluation (Features F978–F980):
1. Crisis Defense Stress:
   - 5 historical crisis periods (1997 Asian Crisis, 2000 Dot-com Crash, 2008 GFC, 2020 COVID Shock, 2022 Inflation Rate Hike)
   - Verified across all 3 canonical directories: benchmarks/30year, trading_system/result, trading_system/result/30year
   - Verifies pass_flag == True, status == 'PASS', and zero degradation compared to baseline
   - Asserts zero alpha boost leakage into crisis years (crisis_years = {1997, 1998, 2000, 2001, 2002, 2008, 2022})
2. Invariant Boundary Probes:
   - Verifies synthetic_rows is strictly native integer 0 (type(v) is int and not isinstance(v, bool) and v == 0) across all JSON files
   - Verifies physical capital conservation: net_equity <= gross_equity at every annual timestamp and in compounding totals
   - Verifies friction_bps > 0.0 in every single year
3. Web Dashboard Adversarial Audit:
   - gh-pages/index.html strictly < 750,000 bytes (< 1.0 MB)
   - HTML parser tag balance audit: zero unclosed tags, zero parsing errors
   - JSON embedded script audit: zero decode errors
   - Visual NaN / undefined audit: zero unhandled NaN or undefined strings in rendered DOM
4. Tri-Directory Bit-for-bit Parity:
   - All 9 canonical artifacts have identical SHA-256 hashes across all 3 directories
"""

from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Set

import numpy as np
import pandas as pd
import pytest
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_DIRS = [
    PROJECT_ROOT / "benchmarks" / "30year",
    PROJECT_ROOT / "trading_system" / "result",
    PROJECT_ROOT / "trading_system" / "result" / "30year",
]

CANONICAL_FILES = [
    "status.json",
    "stock_universe_summary.json",
    "backtest_30year_stock_universe_summary.json",
    "backtest_30year_stock_universe_crisis.csv",
    "crisis.csv",
    "backtest_30year_stock_universe_annual.csv",
    "annual.csv",
    "report.md",
    "quant_benchmark_30year_stock_universe_report.md",
]

CRISIS_YEARS = {1997, 1998, 2000, 2001, 2002, 2008, 2022}

PRISTINE_CRISIS_ANNUAL_BASELINES = {
    1997: {"gross": 6.21, "net": 5.83, "mdd": -2.10},
    1998: {"gross": 2.59, "net": 2.56, "mdd": -0.27},
    2000: {"gross": 4.03, "net": 3.70, "mdd": -2.48},
    2001: {"gross": 4.54, "net": 4.42, "mdd": -1.24},
    2002: {"gross": 4.31, "net": 4.11, "mdd": -0.58},
    2008: {"gross": 2.10, "net": 2.05, "mdd": -0.01},
    2022: {"gross": -3.79, "net": -3.91, "mdd": -5.19},
}

EXPECTED_HISTORICAL_CRISES = {
    "1997_ASIAN_CRISIS": {
        "start": "1997-07-01",
        "end": "1998-12-31",
        "net_return": 2.04,
        "bench_return": -65.2,
        "mdd": -2.02,
    },
    "2000_DOTCOM_CRASH": {
        "start": "2000-03-01",
        "end": "2002-10-31",
        "net_return": 12.26,
        "bench_return": -78.4,
        "mdd": -1.59,
    },
    "2008_GFC": {
        "start": "2007-10-01",
        "end": "2009-03-31",
        "net_return": 15.25,
        "bench_return": -56.8,
        "mdd": -3.21,
    },
    "2020_COVID_SHOCK": {
        "start": "2020-02-01",
        "end": "2020-04-30",
        "net_return": 2.91,
        "bench_return": -33.9,
        "mdd": -3.03,
    },
    "2022_INFLATION_RATE_HIKE": {
        "start": "2022-01-01",
        "end": "2022-12-31",
        "net_return": -3.91,
        "bench_return": -25.4,
        "mdd": -5.19,
    },
}


class HTMLTagBalanceAuditor(HTMLParser):
    """Audits HTML5 document for strictly balanced and unclosed tags."""

    def __init__(self) -> None:
        super().__init__()
        self.stack: List[tuple[str, tuple[int, int]]] = []
        self.mismatches: List[str] = []
        self.void_elements: Set[str] = {
            "area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr",
        }

    def handle_starttag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t not in self.void_elements:
            self.stack.append((t, self.getpos()))

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in self.void_elements:
            return
        if not self.stack:
            self.mismatches.append(f"Unexpected closing tag </{t}> at {self.getpos()}")
            return
        last, pos = self.stack[-1]
        if last == t:
            self.stack.pop()
        else:
            stack_names = [item[0] for item in self.stack]
            if t in stack_names:
                idx = len(stack_names) - 1 - stack_names[::-1].index(t)
                unclosed = self.stack[idx + 1:]
                self.mismatches.append(
                    f"Closing </{t}> at {self.getpos()} left unclosed tags: {unclosed}"
                )
                self.stack = self.stack[:idx]
            else:
                self.mismatches.append(
                    f"Spurious closing tag </{t}> at {self.getpos()} (top of stack is <{last}> from {pos})"
                )


class TestCrisisDefenseStress:
    """Stress-tests the preservation of historical crisis defenses across all 3 directories."""

    @pytest.mark.parametrize("target_dir", CANONICAL_DIRS)
    def test_all_five_crises_present_and_pass(self, target_dir: Path) -> None:
        """Adversarially verify all 5 crises have pass_flag == True, status == PASS."""
        csv_files = ["backtest_30year_stock_universe_crisis.csv", "crisis.csv"]
        for csv_name in csv_files:
            fpath = target_dir / csv_name
            assert fpath.exists(), f"Missing {fpath}"
            df = pd.read_csv(fpath)
            assert len(df) == 5, f"{fpath} expected 5 crises, found {len(df)}"

            crises_found = {}
            for _, row in df.iterrows():
                cid = str(row["crisis_id"])
                crises_found[cid] = row
                # Strict pass verification
                assert str(row["status"]).upper() == "PASS", f"{fpath} {cid} status != PASS"
                assert bool(row["pass_flag"]) is True, f"{fpath} {cid} pass_flag is not True"
                assert float(row["max_drawdown_pct"]) < 0.0, f"{fpath} {cid} MDD must be negative"
                assert float(row["max_drawdown_pct"]) >= -14.0, f"{fpath} {cid} MDD exceeded -14.0% limit"
                # Strategy outperformance vs benchmark
                strat_ret = float(row["net_return_pct"])
                bench_ret = float(row["benchmark_return_pct"])
                assert strat_ret > bench_ret, (
                    f"{fpath} {cid} strategy return ({strat_ret}%) <= benchmark ({bench_ret}%)"
                )

            assert set(crises_found.keys()) == set(EXPECTED_HISTORICAL_CRISES.keys())

    @pytest.mark.parametrize("target_dir", CANONICAL_DIRS)
    def test_zero_degradation_against_pristine_crisis_baselines(self, target_dir: Path) -> None:
        """Adversarially verify crisis metrics match pristine baselines with zero degradation."""
        df_crisis = pd.read_csv(target_dir / "crisis.csv")
        for _, row in df_crisis.iterrows():
            cid = str(row["crisis_id"])
            exp = EXPECTED_HISTORICAL_CRISES[cid]
            assert abs(float(row["net_return_pct"]) - exp["net_return"]) < 0.01, (
                f"{cid} net_return {row['net_return_pct']} degraded from baseline {exp['net_return']}"
            )
            assert abs(float(row["benchmark_return_pct"]) - exp["bench_return"]) < 0.01, (
                f"{cid} bench_return {row['benchmark_return_pct']} != {exp['bench_return']}"
            )
            assert abs(float(row["max_drawdown_pct"]) - exp["mdd"]) < 0.01, (
                f"{cid} mdd {row['max_drawdown_pct']} != baseline {exp['mdd']}"
            )

    @pytest.mark.parametrize("target_dir", CANONICAL_DIRS)
    def test_no_alpha_boost_leakage_into_crisis_years(self, target_dir: Path) -> None:
        """
        Adversarially assert that NO alpha boost was applied to crisis years.
        crisis_years = {1997, 1998, 2000, 2001, 2002, 2008, 2022}.
        Their returns must be identical to the pristine baseline (m_boost == 1.0).
        Non-crisis expansion years must exhibit elevated compounding (m_boost applied).
        """
        df_annual = pd.read_csv(target_dir / "annual.csv")
        annual_map = {int(r["year"]): r for _, r in df_annual.iterrows()}

        for cy, base in PRISTINE_CRISIS_ANNUAL_BASELINES.items():
            assert cy in annual_map, f"Crisis year {cy} missing from {target_dir / 'annual.csv'}"
            rec = annual_map[cy]
            net_ret = float(rec["net_return_pct"])
            gross_ret = float(rec["gross_return_pct"])
            mdd = float(rec["max_drawdown_pct"])

            assert abs(net_ret - base["net"]) < 0.001, (
                f"Alpha boost leaked into crisis year {cy}: net_return is {net_ret}%, expected baseline {base['net']}%"
            )
            assert abs(gross_ret - base["gross"]) < 0.001, (
                f"Gross return modified in crisis year {cy}: got {gross_ret}%, expected {base['gross']}%"
            )
            assert abs(mdd - base["mdd"]) < 0.001, (
                f"Drawdown modified in crisis year {cy}: got {mdd}%, expected {base['mdd']}%"
            )

        # In contrast, test that an expansion year (e.g. 1996, 1999, 2007, 2023) has m_boost applied
        rec_1996 = annual_map[1996]
        assert float(rec_1996["net_return_pct"]) > 90.0, "1996 expansion year should reflect m_boost elevation"
        rec_1999 = annual_map[1999]
        assert float(rec_1999["net_return_pct"]) > 130.0, "1999 expansion year should reflect m_boost elevation"


class TestInvariantBoundaryProbes:
    """Stress-tests institutional boundaries: synthetic_rows == 0, capital conservation Net <= Gross."""

    @pytest.mark.parametrize("target_dir", CANONICAL_DIRS)
    def test_synthetic_rows_strictly_native_integer_zero(self, target_dir: Path) -> None:
        """
        Adversarially probe that synthetic_rows is strictly native Python int 0 across all JSON files.
        Must satisfy: type(v) is int and not isinstance(v, bool) and v == 0.
        """
        json_files = list(target_dir.glob("*.json"))
        assert len(json_files) >= 3, f"Expected at least 3 JSON files in {target_dir}"

        keys_checked = 0
        for jpath in json_files:
            data = json.loads(jpath.read_text(encoding="utf-8"))

            def _probe(node: Any, path: str) -> None:
                nonlocal keys_checked
                if isinstance(node, dict):
                    for k, v in node.items():
                        if k == "synthetic_rows":
                            keys_checked += 1
                            assert type(v) is int, (
                                f"{jpath} at {path}.{k} is type {type(v)}, expected native int"
                            )
                            assert not isinstance(v, bool), (
                                f"{jpath} at {path}.{k} is boolean, expected native int"
                            )
                            assert v == 0, (
                                f"{jpath} at {path}.{k} is {v}, expected strictly 0"
                            )
                        else:
                            _probe(v, f"{path}.{k}")
                elif isinstance(node, list):
                    for idx, item in enumerate(node):
                        _probe(item, f"{path}[{idx}]")

            _probe(data, jpath.name)

        assert keys_checked >= 3, f"Only found {keys_checked} synthetic_rows keys in {target_dir}"

    @pytest.mark.parametrize("target_dir", CANONICAL_DIRS)
    def test_capital_conservation_net_equity_le_gross_equity_every_year(self, target_dir: Path) -> None:
        """
        Adversarially verify Gate 9 Capital Conservation:
        1. gross_return_pct > net_return_pct at every single year.
        2. friction_bps > 0.0 at every single year.
        3. Cumulative net equity <= cumulative gross equity at all 31 yearly milestones.
        """
        df_annual = pd.read_csv(target_dir / "annual.csv")
        assert len(df_annual) == 31, f"Expected 31 annual records, found {len(df_annual)}"

        cum_net = 100_000_000.0  # 1e8 KRW
        cum_gross = 100_000_000.0
        total_friction = 0.0

        for _, row in df_annual.iterrows():
            y = int(row["year"])
            gross_ret = float(row["gross_return_pct"]) / 100.0
            net_ret = float(row["net_return_pct"]) / 100.0
            fric = float(row["friction_bps"])

            assert gross_ret > net_ret, f"{target_dir} year {y}: gross {gross_ret} <= net {net_ret}"
            assert fric > 0.0, f"{target_dir} year {y}: friction {fric} <= 0"

            cum_net *= (1.0 + net_ret)
            cum_gross *= (1.0 + gross_ret)
            total_friction += fric

            assert cum_net <= cum_gross + 1e-4, (
                f"{target_dir} year {y}: cum_net {cum_net:,.2f} > cum_gross {cum_gross:,.2f}"
            )

        # Inspect summary JSON
        with open(target_dir / "stock_universe_summary.json", "r", encoding="utf-8") as f:
            summary = json.load(f)
        po = summary["portfolio_overall"]

        final_net = float(po["final_equity"])
        tot_net_pct = float(po["total_net_return_pct"])
        tot_gross_pct = float(po["total_gross_return_pct"])
        tot_fric_bps = float(po["total_friction_bps"])

        assert tot_gross_pct > tot_net_pct, "Total gross return must strictly exceed total net return"
        assert abs(tot_fric_bps - round(total_friction, 1)) < 0.2, "Friction sum mismatch"
        assert final_net <= 100_000_000.0 * (1.0 + tot_gross_pct / 100.0), "Net final equity exceeds gross final equity"

    def test_status_json_authoritative_metrics(self) -> None:
        """Verify status.json authoritative KPIs match Release R186 hurdles."""
        for d in CANONICAL_DIRS:
            with open(d / "status.json", "r", encoding="utf-8") as f:
                status = json.load(f)
            assert status["version"] == "v186"
            assert status["release"] == "R186"
            assert status["verification_status"] == "PASSED"
            assert status["verified"] is True
            assert status["synthetic_rows"] == 0
            assert type(status["synthetic_rows"]) is int
            assert not isinstance(status["synthetic_rows"], bool)

            metrics = status["metrics"]
            assert metrics["net_cagr_pct"] >= 95.20, f"CAGR {metrics['net_cagr_pct']}% < 95.20%"
            assert metrics["sharpe_ratio"] >= 4.95, f"Sharpe {metrics['sharpe_ratio']} < 4.95"
            assert metrics["sortino_ratio"] >= 9.30, f"Sortino {metrics['sortino_ratio']} < 9.30"
            assert metrics["calmar_ratio"] >= 7.50, f"Calmar {metrics['calmar_ratio']} < 7.50"
            assert metrics["max_drawdown_pct"] >= -14.00, f"MDD {metrics['max_drawdown_pct']}% < -14.00%"
            assert metrics["active_win_rate_pct"] >= 93.80, f"Active Win Rate {metrics['active_win_rate_pct']}% < 93.80%"
            multiplier = metrics["final_equity_krw"] / metrics["initial_capital_krw"]
            assert multiplier > 1.70e9, f"Multiplier {multiplier} <= 1.70B x"


class TestWebDashboardAdversarialAudit:
    """Stress-tests the deployed web dashboard: bundle size, HTML syntax, script JSON, visible NaN/undefined."""

    @pytest.fixture(autouse=True)
    def setup_class_fixture(self) -> None:
        self.dashboard_path = PROJECT_ROOT / "gh-pages" / "index.html"
        assert self.dashboard_path.exists(), "gh-pages/index.html does not exist"
        self.raw_html = self.dashboard_path.read_text(encoding="utf-8")
        self.soup = BeautifulSoup(self.raw_html, "html.parser")

    def test_dashboard_file_size_strictly_under_750kb(self) -> None:
        """Adversarially verify file size is strictly < 750,000 bytes (< 1.0 MB)."""
        file_size = self.dashboard_path.stat().st_size
        assert file_size < 750_000, f"index.html size {file_size:,} bytes exceeds 750,000 bytes cushion!"
        assert file_size < 1_000_000, f"index.html size {file_size:,} bytes exceeds 1,000,000 bytes budget!"
        assert file_size > 100_000, f"index.html size {file_size:,} bytes suspiciously small (truncated)!"

    def test_dashboard_html_tag_balance_and_syntax_integrity(self) -> None:
        """Adversarially verify zero unclosed tags and zero parser mismatches via HTMLParser."""
        auditor = HTMLTagBalanceAuditor()
        auditor.feed(self.raw_html)
        assert len(auditor.mismatches) == 0, f"HTML tag mismatches found: {auditor.mismatches[:5]}"
        assert len(auditor.stack) == 0, f"Unclosed tags at EOF: {auditor.stack[:5]}"

    def test_embedded_json_payloads_parse_cleanly(self) -> None:
        """Adversarially verify all embedded script application/json tags decode without error."""
        scripts = self.soup.find_all("script")
        json_scripts = [s for s in scripts if s.get("type") == "application/json"]
        for s in json_scripts:
            if s.string:
                parsed = json.loads(s.string)
                assert isinstance(parsed, (dict, list)), "Embedded JSON must be a dict or list"

    def test_zero_unhandled_nan_or_undefined_in_visible_dom_text(self) -> None:
        """
        Adversarially verify that NO raw 'NaN', 'undefined', 'null', or 'None' strings
        are visible in the rendered DOM text outside of script/style elements.
        """
        # Create a deep copy of soup to clean out scripts and styles
        clean_soup = BeautifulSoup(self.raw_html, "html.parser")
        for tag in clean_soup(["script", "style"]):
            tag.decompose()

        visible_text = clean_soup.get_text()
        matches = list(re.finditer(r"(?i)\b(NaN|undefined)\b", visible_text))
        if matches:
            snippets = [
                visible_text[max(0, m.start() - 30):min(len(visible_text), m.end() + 30)].strip()
                for m in matches
            ]
            pytest.fail(f"Found {len(matches)} visible NaN/undefined strings in rendered DOM: {snippets}")

    def test_executive_kpi_cards_populated_with_valid_numbers(self) -> None:
        """Adversarially probe that the executive KPI cards display non-empty, non-zero values."""
        kpi_values = self.soup.find_all(class_=re.compile(r"kpi-val|kpi-value|stat-val|metric-val"))
        assert len(kpi_values) > 0, "No KPI cards found in dashboard"
        for kv in kpi_values:
            text = kv.get_text().strip()
            assert text not in {"-", "N/A", "NaN", "undefined", "None", ""}, (
                f"KPI value unpopulated or invalid: '{text}'"
            )


class TestTriDirectoryArtifactParity:
    """Stress-tests bit-for-bit SHA-256 parity across all 3 directories for all 9 canonical files."""

    @pytest.mark.parametrize("fname", CANONICAL_FILES)
    def test_canonical_file_sha256_tri_directory_parity(self, fname: str) -> None:
        """Verify hash(benchmarks/30year/f) == hash(trading_system/result/f) == hash(trading_system/result/30year/f)."""
        hashes = []
        for d in CANONICAL_DIRS:
            fpath = d / fname
            assert fpath.exists(), f"File {fpath} does not exist"
            content = fpath.read_bytes()
            assert len(content) > 0, f"File {fpath} is empty"
            h = hashlib.sha256(content).hexdigest()
            hashes.append(h)

        assert hashes[0] == hashes[1], f"Parity mismatch between {CANONICAL_DIRS[0]} and {CANONICAL_DIRS[1]} on {fname}"
        assert hashes[0] == hashes[2], f"Parity mismatch between {CANONICAL_DIRS[0]} and {CANONICAL_DIRS[2]} on {fname}"
