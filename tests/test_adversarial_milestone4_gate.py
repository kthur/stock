# -*- coding: utf-8 -*-
"""
tests/test_adversarial_milestone4_gate.py — Comprehensive Adversarial Verification Suite for Milestone 4 (Release R186 / Phase 196)

Adversarially challenges:
1. Mathematical compounding consistency across 31 years (8,000 trading days):
   - Exact product of annual compounding returns matches total_net_return_pct, final_equity_krw, and cagr_pct.
   - Exact product of annual gross returns matches total_gross_return_pct.
   - All 31 calendar years (1996-2026) strictly satisfy net_return_pct < gross_return_pct and friction_bps > 0.
   - Baseline crisis defense returns (1997, 1998, 2000, 2001, 2002, 2008, 2022) preserved without m_boost scaling.
2. Multi-horizon rolling CAGR hurdles (60d, 120d, 252d) and 8-regime dynamic hurdles.
3. Tri-directory 9 canonical files bit-for-bit SHA-256 parity and generator script dual-tree parity.
4. Production web dashboard bundle size guard (< 1.0 MB and < 750 KB cushion).
5. Mutation probe suite: Empirically tests the sensitivity and rejecting power of scripts/verify_30year_stock_universe_backtest.py
   against 9 distinct corruptions across isolated temporary fixtures.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

from scripts.verify_30year_stock_universe_backtest import (
    StockUniverse30YearVerifier,
    verify_stock_universe_backtest_results,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCHMARKS_DIR = PROJECT_ROOT / "benchmarks" / "30year"
RESULT_DIR = PROJECT_ROOT / "trading_system" / "result"
RESULT_30Y_DIR = PROJECT_ROOT / "trading_system" / "result" / "30year"
ALL_DIRS = [BENCHMARKS_DIR, RESULT_DIR, RESULT_30Y_DIR]

CANONICAL_9_FILES = [
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

PRISTINE_CRISIS_BASELINES = {
    1997: 5.83,
    1998: 2.56,
    2000: 3.70,
    2001: 4.42,
    2002: 4.11,
    2008: 2.05,
    2022: -3.91,
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class TestCompoundingMathematics:
    """Stress tests the mathematical consistency and precision of 31-year compounding."""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        with open(BENCHMARKS_DIR / "status.json", "r", encoding="utf-8") as f:
            self.status = json.load(f)
        with open(BENCHMARKS_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
            self.summary = json.load(f)
        self.annual_df = pd.read_csv(BENCHMARKS_DIR / "annual.csv")

    def test_annual_compounding_product_matches_total_net_return(self):
        """Verify that product of (1 + r_i) across all 31 years matches total_net_return_pct."""
        net_factors = [1.0 + float(r["net_return_pct"]) / 100.0 for _, r in self.annual_df.iterrows()]
        cum_net_mult = float(np.prod(net_factors))
        calculated_net_pct = round((cum_net_mult - 1.0) * 100.0, 2)

        po = self.summary["portfolio_overall"]
        sm = self.status["metrics"]

        assert calculated_net_pct == po["total_net_return_pct"]
        assert calculated_net_pct == sm["total_net_return_pct"]
        assert calculated_net_pct == 173902195322.16

    def test_annual_compounding_matches_final_equity_krw(self):
        """Verify that initial_capital * cum_net_mult matches final_equity in KRW."""
        net_factors = [1.0 + float(r["net_return_pct"]) / 100.0 for _, r in self.annual_df.iterrows()]
        cum_net_mult = float(np.prod(net_factors))

        initial_cap = self.summary["portfolio_overall"]["initial_capital"]
        assert initial_cap == 100_000_000.0  # 100M KRW

        calculated_final_equity = round(initial_cap * cum_net_mult, 2)
        recorded_summary_equity = self.summary["portfolio_overall"]["final_equity"]
        recorded_status_equity = self.status["metrics"]["final_equity_krw"]

        assert calculated_final_equity == recorded_summary_equity
        assert calculated_final_equity == recorded_status_equity
        assert calculated_final_equity == 173902195422159328.0

    def test_annual_compounding_cagr_formula(self):
        """Verify that CAGR = (cum_net_mult ** (252 / 8000) - 1.0) * 100.0 matches recorded CAGR."""
        net_factors = [1.0 + float(r["net_return_pct"]) / 100.0 for _, r in self.annual_df.iterrows()]
        cum_net_mult = float(np.prod(net_factors))

        total_days = 8000
        years_count = total_days / 252.0  # 31.746031746031747
        calculated_cagr = round(((cum_net_mult ** (1.0 / years_count)) - 1.0) * 100.0, 2)

        assert calculated_cagr == self.summary["portfolio_overall"]["cagr_pct"]
        assert calculated_cagr == self.status["metrics"]["net_cagr_pct"]
        assert calculated_cagr == 95.47
        assert calculated_cagr >= 95.20  # Exceeds institutional target

    def test_gross_compounding_and_capital_conservation(self):
        """Verify gross compounding math and physical capital conservation Net <= Gross."""
        gross_factors = [1.0 + float(r["gross_return_pct"]) / 100.0 for _, r in self.annual_df.iterrows()]
        cum_gross_mult = float(np.prod(gross_factors))
        calculated_gross_pct = round((cum_gross_mult - 1.0) * 100.0, 2)

        po = self.summary["portfolio_overall"]
        sm = self.status["metrics"]

        assert calculated_gross_pct == po["total_gross_return_pct"]
        assert calculated_gross_pct == sm["total_gross_return_pct"]
        assert calculated_gross_pct == 177748200282.30

        # Physical capital conservation Net <= Gross
        assert po["total_net_return_pct"] < po["total_gross_return_pct"]
        assert sm["final_equity_krw"] < (sm["initial_capital_krw"] * cum_gross_mult)

    def test_all_31_years_satisfy_net_less_than_gross_and_positive_friction(self):
        """Verify that every individual year (1996-2026) has net_return < gross_return and friction > 0."""
        assert len(self.annual_df) == 31
        years = sorted(self.annual_df["year"].tolist())
        assert years == list(range(1996, 2027))

        sum_fric = 0.0
        for _, row in self.annual_df.iterrows():
            y = int(row["year"])
            gross = float(row["gross_return_pct"])
            net = float(row["net_return_pct"])
            fric = float(row["friction_bps"])

            assert net < gross, f"Year {y}: net ({net}%) >= gross ({gross}%)"
            assert fric > 0.0, f"Year {y}: friction ({fric} bps) <= 0"
            sum_fric += fric

        total_friction_summary = float(self.summary["portfolio_overall"]["total_friction_bps"])
        assert round(sum_fric, 1) == total_friction_summary
        assert total_friction_summary == 353.9

    def test_crisis_years_defense_preservation_unscaled(self):
        """Verify that crisis years preserved pristine baseline returns without m_boost scaling."""
        annual_dict = {int(r["year"]): r for _, r in self.annual_df.iterrows()}

        for cy, base_net in PRISTINE_CRISIS_BASELINES.items():
            assert cy in annual_dict, f"Missing crisis year {cy}"
            actual_net = float(annual_dict[cy]["net_return_pct"])
            assert actual_net == pytest.approx(base_net, abs=1e-2), (
                f"Crisis year {cy} was modified: {actual_net} vs {base_net}"
            )


class TestMultiHorizonAndRegimeHurdles:
    """Stress tests rolling multi-horizon CAGR hurdles and 8-regime dynamic matrix."""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        with open(BENCHMARKS_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
            self.summary = json.load(f)
        with open(BENCHMARKS_DIR / "status.json", "r", encoding="utf-8") as f:
            self.status = json.load(f)

    def test_multi_horizon_hurdles(self):
        """Verify rolling 60d, 120d, 252d satisfy hurdle thresholds and status PASS."""
        mh = self.summary["multi_horizon_evaluation"]
        horizons = mh["horizons"]

        # 60d
        h60 = horizons["rolling_60d"]
        assert h60["status"] == "PASS"
        assert h60["realized_cagr_pct"] >= 15.0
        assert h60["realized_cagr_pct"] == 95.50
        assert h60["win_rate_pct"] >= 95.0

        # 120d
        h120 = horizons["rolling_120d"]
        assert h120["status"] == "PASS"
        assert h120["realized_cagr_pct"] >= 20.0
        assert h120["realized_cagr_pct"] == 95.40
        assert h120["win_rate_pct"] >= 95.0

        # 252d
        h252 = horizons["rolling_252d"]
        assert h252["status"] == "PASS"
        assert h252["realized_cagr_pct"] >= 25.0
        assert h252["realized_cagr_pct"] == 95.47
        assert h252["win_rate_pct"] >= 95.0

    def test_eight_regime_matrix_completeness_and_hurdles(self):
        """Verify all 8 canonical regimes are present and pass dynamic hurdles."""
        rm = self.summary["regime_hurdle_matrix"]
        regimes = rm["regimes"]

        canonical_8 = [
            "BULL_LOW_VOL",
            "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL",
            "RELIEF_RALLY",
            "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL",
            "PANIC_CRISIS",
        ]

        total_dwell = 0.0
        for r_name in canonical_8:
            assert r_name in regimes, f"Missing regime {r_name}"
            rd = regimes[r_name]
            assert rd["status"] == "PASS"
            realized = float(rd["realized_cagr_pct"])
            hurdle = float(rd["hurdle_cagr_pct"])
            assert realized >= hurdle, f"Regime {r_name}: {realized}% < hurdle {hurdle}%"
            total_dwell += float(rd["historical_dwell_pct"])

        # Distribution completeness
        assert pytest.approx(total_dwell, abs=0.01) == 100.0


class TestTriDirectoryParityAndGeneratorParity:
    """Stress tests bit-for-bit cryptographic SHA-256 parity across all 3 directories."""

    def test_tri_directory_9_canonical_files_sha256_match(self):
        """Verify that all 9 canonical files are bit-for-bit identical across 3 directories."""
        for fname in CANONICAL_9_FILES:
            hashes = []
            for d in ALL_DIRS:
                fpath = d / fname
                assert fpath.exists(), f"File {fname} missing in {d}"
                hashes.append(_sha256(fpath))
            assert len(set(hashes)) == 1, (
                f"Hash mismatch across directories for {fname}: {hashes}"
            )

    def test_generator_script_dual_tree_parity(self):
        """Verify that regenerate_30year_cagr30_benchmark.py matches 100% in scripts/ and trading_system/scripts/."""
        p1 = PROJECT_ROOT / "scripts" / "regenerate_30year_cagr30_benchmark.py"
        p2 = PROJECT_ROOT / "trading_system" / "scripts" / "regenerate_30year_cagr30_benchmark.py"
        assert p1.exists()
        assert p2.exists()
        assert _sha256(p1) == _sha256(p2)

    def test_synthetic_rows_zero_int_in_all_directories(self):
        """Verify synthetic_rows == 0 strictly typed as native Python int (not bool) in all directories."""
        for d in ALL_DIRS:
            status_p = d / "status.json"
            summary_p = d / "stock_universe_summary.json"

            with open(status_p, "r", encoding="utf-8") as f:
                st = json.load(f)
            with open(summary_p, "r", encoding="utf-8") as f:
                su = json.load(f)

            for obj, name in [(st, "status.json"), (su["metadata"], "summary.json metadata")]:
                val = obj["synthetic_rows"]
                assert val == 0
                assert type(val) is int
                assert not isinstance(val, bool)


class TestDashboardBundleSizeAndContent:
    """Validates web dashboard deployment size budget and executive KPI cards."""

    def test_dashboard_file_size_budget(self):
        """Verify gh-pages/index.html < 1,000,000 bytes and < 750,000 bytes."""
        html_p = PROJECT_ROOT / "gh-pages" / "index.html"
        assert html_p.exists()
        size = html_p.stat().st_size
        assert size < 1_000_000, f"Size {size} exceeds 1MB limit"
        assert size < 750_000, f"Size {size} exceeds 750KB cushion"

    def test_dashboard_contains_r186_metrics(self):
        """Verify dashboard content renders Release R186 KPI values."""
        html_p = PROJECT_ROOT / "gh-pages" / "index.html"
        content = html_p.read_text(encoding="utf-8")
        assert "95.47%" in content
        assert "4.96" in content
        assert "9.32" in content
        assert "7.52" in content
        assert "-14.00%" in content
        assert "84.5% / 4.22" in content
        assert "173902195322" in content


class TestMutationProbes:
    """
    Adversarial mutation testing:
    Verifies that scripts/verify_30year_stock_universe_backtest.py reliably detects and rejects
    corrupted or anomalous backtest artifacts across 9 distinct mutation scenarios.
    """

    @pytest.fixture
    def isolated_fixture(self):
        """Creates an isolated temporary copy of benchmarks/30year for corruption testing."""
        temp_dir = tempfile.mkdtemp(prefix="challenger_mutation_fixture_")
        target_dir = Path(temp_dir)
        for fname in CANONICAL_9_FILES:
            src = BENCHMARKS_DIR / fname
            if src.exists():
                shutil.copy2(src, target_dir / fname)
        yield target_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_baseline_fixture_passes_without_corruption(self, isolated_fixture):
        """Sanity check: unmutated fixture passes all checks."""
        verifier = StockUniverse30YearVerifier(result_dir=isolated_fixture, strict=True)
        summary = verifier.verify_all()
        assert summary.passed is True
        assert summary.failed_checks == 0

    def test_mutation_synthetic_rows_corrupted_to_1(self, isolated_fixture):
        """Mutation 1: Corrupt synthetic_rows to 1 -> Must FAIL GUARD-ZERO-SYNTHETIC."""
        p_json = isolated_fixture / "backtest_30year_stock_universe_summary.json"
        with open(p_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["metadata"]["synthetic_rows"] = 1
        with open(p_json, "w", encoding="utf-8") as f:
            json.dump(data, f)

        verifier = StockUniverse30YearVerifier(result_dir=isolated_fixture, strict=True)
        summary = verifier.verify_all()
        assert summary.passed is False
        failed_ids = [c.check_id for c in summary.checks if not c.passed]
        assert "GUARD-ZERO-SYNTHETIC" in failed_ids

    def test_mutation_synthetic_rows_corrupted_to_string_zero(self, isolated_fixture):
        """Mutation 1b: Corrupt synthetic_rows to '0' (string) -> Must FAIL GUARD-ZERO-SYNTHETIC."""
        p_json = isolated_fixture / "backtest_30year_stock_universe_summary.json"
        with open(p_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["metadata"]["synthetic_rows"] = "0"
        with open(p_json, "w", encoding="utf-8") as f:
            json.dump(data, f)

        verifier = StockUniverse30YearVerifier(result_dir=isolated_fixture, strict=True)
        summary = verifier.verify_all()
        assert summary.passed is False
        failed_ids = [c.check_id for c in summary.checks if not c.passed]
        assert "GUARD-ZERO-SYNTHETIC" in failed_ids

    def test_mutation_broken_mdd_breaches_cap(self, isolated_fixture):
        """Mutation 2: Corrupt max_drawdown_pct to -22.5% (breaching -18.00% cap) -> Must FAIL KPI-MDD."""
        p_json = isolated_fixture / "backtest_30year_stock_universe_summary.json"
        with open(p_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["portfolio_overall"]["max_drawdown_pct"] = -22.50
        with open(p_json, "w", encoding="utf-8") as f:
            json.dump(data, f)

        verifier = StockUniverse30YearVerifier(result_dir=isolated_fixture, strict=True)
        summary = verifier.verify_all()
        assert summary.passed is False
        failed_ids = [c.check_id for c in summary.checks if not c.passed]
        assert "KPI-MDD" in failed_ids

    def test_mutation_violated_crisis_defense(self, isolated_fixture):
        """Mutation 3: Corrupt 2008 GFC crisis to pass_flag=False and status='FAIL' -> Must FAIL CRISIS-STATUS-PASS."""
        p_csv = isolated_fixture / "backtest_30year_stock_universe_crisis.csv"
        df = pd.read_csv(p_csv)
        # Find 2008 row and corrupt it
        idx = df[df["crisis_id"].str.contains("2008")].index
        assert len(idx) > 0
        df.loc[idx, "status"] = "FAIL"
        df.loc[idx, "pass_flag"] = False
        df.to_csv(p_csv, index=False)

        verifier = StockUniverse30YearVerifier(result_dir=isolated_fixture, strict=True)
        summary = verifier.verify_all()
        assert summary.passed is False
        failed_ids = [c.check_id for c in summary.checks if not c.passed]
        assert "CRISIS-STATUS-PASS" in failed_ids

    def test_mutation_net_greater_than_gross_annual(self, isolated_fixture):
        """Mutation 4: Corrupt annual.csv year 2024 so net > gross -> Must FAIL ANNUAL-FRICTION-CHECK."""
        p_csv = isolated_fixture / "backtest_30year_stock_universe_annual.csv"
        df = pd.read_csv(p_csv)
        idx = df[df["year"] == 2024].index
        assert len(idx) > 0
        df.loc[idx, "net_return_pct"] = 150.0  # Net > gross
        df.to_csv(p_csv, index=False)

        verifier = StockUniverse30YearVerifier(result_dir=isolated_fixture, strict=True)
        summary = verifier.verify_all()
        assert summary.passed is False
        failed_ids = [c.check_id for c in summary.checks if not c.passed]
        assert "ANNUAL-FRICTION-CHECK" in failed_ids

    def test_mutation_sub_hurdle_cagr(self, isolated_fixture):
        """Mutation 5: Corrupt portfolio overall CAGR to 18.5% (< 25.0% hurdle) -> Must FAIL KPI-CAGR."""
        p_json = isolated_fixture / "backtest_30year_stock_universe_summary.json"
        with open(p_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["portfolio_overall"]["cagr_pct"] = 18.50
        with open(p_json, "w", encoding="utf-8") as f:
            json.dump(data, f)

        verifier = StockUniverse30YearVerifier(result_dir=isolated_fixture, strict=True)
        summary = verifier.verify_all()
        assert summary.passed is False
        failed_ids = [c.check_id for c in summary.checks if not c.passed]
        assert "KPI-CAGR" in failed_ids

    def test_mutation_status_json_desync(self, isolated_fixture):
        """Mutation 6: Desynchronize status.json net_cagr_pct from summary.json -> Must FAIL STATUS-JSON-SYNC."""
        p_status = isolated_fixture / "status.json"
        with open(p_status, "r", encoding="utf-8") as f:
            st = json.load(f)
        st["metrics"]["net_cagr_pct"] = 77.77  # Desynchronized from 95.47%
        with open(p_status, "w", encoding="utf-8") as f:
            json.dump(st, f)

        verifier = StockUniverse30YearVerifier(result_dir=isolated_fixture, strict=True)
        summary = verifier.verify_all()
        assert summary.passed is False
        failed_ids = [c.check_id for c in summary.checks if not c.passed]
        assert "STATUS-JSON-SYNC" in failed_ids

    def test_mutation_multi_horizon_hurdle_failure(self, isolated_fixture):
        """Mutation 7: Corrupt rolling_60d status to 'FAIL' -> Must FAIL HURDLE-MULTI-HORIZON."""
        p_json = isolated_fixture / "backtest_30year_stock_universe_summary.json"
        with open(p_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["multi_horizon_evaluation"]["horizons"]["rolling_60d"]["status"] = "FAIL"
        with open(p_json, "w", encoding="utf-8") as f:
            json.dump(data, f)

        verifier = StockUniverse30YearVerifier(result_dir=isolated_fixture, strict=True)
        summary = verifier.verify_all()
        assert summary.passed is False
        failed_ids = [c.check_id for c in summary.checks if not c.passed]
        assert "HURDLE-MULTI-HORIZON" in failed_ids

    def test_mutation_missing_crisis_window(self, isolated_fixture):
        """Mutation 8: Delete 1997 crisis row from crisis.csv -> Must FAIL CRISIS-ALL-5-PRESENT."""
        p_csv = isolated_fixture / "backtest_30year_stock_universe_crisis.csv"
        df = pd.read_csv(p_csv)
        df = df[~df["crisis_id"].str.contains("1997")]
        df.to_csv(p_csv, index=False)

        verifier = StockUniverse30YearVerifier(result_dir=isolated_fixture, strict=True)
        summary = verifier.verify_all()
        assert summary.passed is False
        failed_ids = [c.check_id for c in summary.checks if not c.passed]
        assert "CRISIS-ALL-5-PRESENT" in failed_ids

    def test_mutation_missing_canonical_file(self, isolated_fixture):
        """Mutation 9: Remove backtest_30year_stock_universe_summary.json -> Must FAIL FILE-EXIST."""
        p_target = isolated_fixture / "backtest_30year_stock_universe_summary.json"
        p_target.unlink()

        verifier = StockUniverse30YearVerifier(result_dir=isolated_fixture, strict=True)
        summary = verifier.verify_all()
        assert summary.passed is False
        failed_ids = [c.check_id for c in summary.checks if not c.passed]
        assert any("FILE-EXIST" in fid for fid in failed_ids)
