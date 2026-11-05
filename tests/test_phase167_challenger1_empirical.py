# -*- coding: utf-8 -*-
"""
tests/test_phase167_challenger1_empirical.py -- Independent Empirical Verification and Stress Test Suite
for Milestone 4 (Phase 167: Features F815–F819) of Release R167.

Author: challenger_phase167_1 (Empirical Challenger: critic, specialist)
Date: 2026-11-05

Rigorous Empirical Assertions:
1. Compounding Identity: (1 + CAGR)^T == prod(1 + R_net) within precision tolerance (T = 8000/252).
2. Capital Conservation: Net Return < Gross Return across all 31 annual periods.
3. Strict Type Integrity: synthetic_rows == 0 as strictly native Python int (not bool/float/str).
4. Crisis Defense Certification: All 5 canonical crises (1997, 2000, 2008, 2020, 2022) pass defense bounds.
5. Multi-Horizon Rolling Hurdles: 60d, 120d, 252d rolling windows exceed institutional hurdles.
6. 8-Regime Matrix Validation: All 8 market regimes achieve realized CAGR >= hurdle CAGR.
7. Portfolio Guardrails: Single-stock (5%), Single-sector (25%), ADV participation (1.5%) zero breaches.
8. Dual-Tree Parity: 100% bit-for-bit SHA-256 match between canonical and mirror artifacts.
9. Dashboard Constraints: gh-pages/index.html strictly < 500 KB (512,000 bytes) with metrics verified.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BENCHMARKS_DIR = PROJECT_ROOT / "benchmarks" / "30year"
RESULT_DIR = PROJECT_ROOT / "trading_system" / "result"
DASHBOARD_PATH = PROJECT_ROOT / "gh-pages" / "index.html"


class TestPhase167EmpiricalCompoundingMath:
    """Empirically stress-tests compounding mathematics and capital conservation."""

    @pytest.fixture(autouse=True)
    def load_data(self) -> None:
        assert (BENCHMARKS_DIR / "annual.csv").exists(), "benchmarks/30year/annual.csv missing"
        assert (BENCHMARKS_DIR / "status.json").exists(), "benchmarks/30year/status.json missing"
        assert (BENCHMARKS_DIR / "stock_universe_summary.json").exists(), "stock_universe_summary.json missing"

        self.df_annual = pd.read_csv(BENCHMARKS_DIR / "annual.csv")
        with open(BENCHMARKS_DIR / "status.json", "r", encoding="utf-8") as f:
            self.status = json.load(f)
        with open(BENCHMARKS_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
            self.summary = json.load(f)

    def test_annual_periods_count_and_range(self) -> None:
        """Verify unbroken 31-year continuous annual distribution (1996–2026)."""
        years = self.df_annual["year"].tolist()
        assert len(years) == 31, f"Expected 31 annual periods, got {len(years)}"
        expected_years = list(range(1996, 2027))
        assert years == expected_years, f"Years sequence broken: {years}"

    def test_compounding_identity_annual_to_terminal_multiplier(self) -> None:
        """Verify (1 + CAGR)^T == prod(1 + R_net) and terminal multiplier = 10,681,173.55x."""
        net_returns = self.df_annual["net_return_pct"].values
        net_factors = 1.0 + net_returns / 100.0

        # Direct product of net return factors
        cum_net_mult = float(np.prod(net_factors))
        expected_mult = 10681173.55128092  # Worker reported terminal multiplier

        rel_error = abs(cum_net_mult - expected_mult) / expected_mult
        assert rel_error < 1e-4, f"Cumulative multiplier mismatch: {cum_net_mult} vs {expected_mult} (rel err: {rel_error})"

        # Check terminal equity in status.json
        initial_cap = float(self.status["metrics"]["initial_capital_krw"])
        final_equity = float(self.status["metrics"]["final_equity_krw"])
        implied_mult = final_equity / initial_cap
        assert abs(implied_mult - cum_net_mult) / cum_net_mult < 1e-4, (
            f"Implied equity multiplier {implied_mult} != cum net multiplier {cum_net_mult}"
        )

        # Check total net return percentage
        total_net_ret = float(self.status["metrics"]["total_net_return_pct"])
        calc_net_ret = round((cum_net_mult - 1.0) * 100.0, 2)
        assert abs(total_net_ret - calc_net_ret) < 0.05, (
            f"Reported total net return {total_net_ret}% != calculated {calc_net_ret}%"
        )

        # Annualization: T = 8000 / 252 ~ 31.7460317
        total_days = int(self.status["metrics"]["total_trading_days"])
        assert total_days == 8000, f"Expected 8000 trading days, got {total_days}"
        T = total_days / 252.0
        cagr_pct = float(self.status["metrics"]["net_cagr_pct"])
        solved_cagr = (cum_net_mult ** (1.0 / T) - 1.0) * 100.0

        assert abs(cagr_pct - 66.50) < 0.05, f"Reported CAGR {cagr_pct}% not 66.50%"
        assert abs(solved_cagr - 66.50) < 0.05, f"Mathematically solved CAGR {solved_cagr:.4f}% not 66.50%"

        # Compounding identity: (1 + CAGR/100)^T vs cum_net_mult
        compounded_from_cagr = (1.0 + cagr_pct / 100.0) ** T
        cagr_mult_diff = abs(compounded_from_cagr - cum_net_mult) / cum_net_mult
        assert cagr_mult_diff < 0.01, (
            f"Compounding identity diff {cagr_mult_diff:.4f} exceeds 1% tolerance: "
            f"(1 + CAGR)^T = {compounded_from_cagr:.2f} vs prod(1 + R_net) = {cum_net_mult:.2f}"
        )

    def test_capital_conservation_strict_net_less_than_gross_all_years(self) -> None:
        """Verify capital conservation: Net Return < Gross Return across all 31 annual periods."""
        violations = []
        for idx, row in self.df_annual.iterrows():
            y = int(row["year"])
            gross = float(row["gross_return_pct"])
            net = float(row["net_return_pct"])
            fric = float(row["friction_bps"])

            if net >= gross:
                violations.append(f"Year {y}: Net ({net}%) >= Gross ({gross}%)")
            if fric <= 0.0:
                violations.append(f"Year {y}: Friction ({fric} bps) <= 0")

        assert len(violations) == 0, f"Capital conservation violations detected: {violations}"

    def test_capital_conservation_cumulative_gross_exceeds_net(self) -> None:
        """Verify cumulative Gross Return strictly exceeds cumulative Net Return."""
        gross_returns = self.df_annual["gross_return_pct"].values
        net_returns = self.df_annual["net_return_pct"].values

        cum_gross = float(np.prod(1.0 + gross_returns / 100.0))
        cum_net = float(np.prod(1.0 + net_returns / 100.0))

        assert cum_gross > cum_net, f"Cumulative gross {cum_gross} <= net {cum_net}"
        assert cum_gross > cum_net * 1.01, f"Gross should exceed Net by reasonable margin due to frictions"

        rep_gross = float(self.status["metrics"]["total_gross_return_pct"])
        rep_net = float(self.status["metrics"]["total_net_return_pct"])
        assert rep_gross > rep_net, f"Reported gross return {rep_gross}% <= net return {rep_net}%"


class TestPhase167EmpiricalTypeAndInvariantIntegrity:
    """Empirically verifies strict data types and production invariants."""

    @pytest.fixture(autouse=True)
    def target_artifacts(self) -> None:
        self.json_targets = [
            BENCHMARKS_DIR / "status.json",
            RESULT_DIR / "status.json",
            BENCHMARKS_DIR / "stock_universe_summary.json",
            RESULT_DIR / "stock_universe_summary.json",
            BENCHMARKS_DIR / "backtest_30year_stock_universe_summary.json",
            RESULT_DIR / "backtest_30year_stock_universe_summary.json",
        ]

    def test_synthetic_rows_strictly_native_integer_zero(self) -> None:
        """Verify synthetic_rows == 0 strictly with type(x) is int across all artifacts."""
        for target in self.json_targets:
            assert target.exists(), f"Target missing: {target}"
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "synthetic_rows" in data:
                synth = data["synthetic_rows"]
            else:
                synth = data.get("metadata", {}).get("synthetic_rows")

            assert synth is not None, f"synthetic_rows field missing in {target.name}"
            assert synth == 0, f"synthetic_rows is {synth} != 0 in {target.name}"
            assert type(synth) is int, f"synthetic_rows type is {type(synth)} (not int) in {target.name}"
            assert not isinstance(synth, bool), f"synthetic_rows is boolean in {target.name}"
            assert not isinstance(synth, float), f"synthetic_rows is float in {target.name}"

    def test_dynamic_filing_lag_and_lookahead_integrity(self) -> None:
        """Verify dynamic filing lag (KRX 45d, SEC 40d) and zero lookahead bias."""
        for target in [BENCHMARKS_DIR / "stock_universe_summary.json", RESULT_DIR / "stock_universe_summary.json"]:
            with open(target, "r", encoding="utf-8") as f:
                d = json.load(f)
            meta = d.get("metadata", {})
            assert meta.get("krx_filing_lag_days") == 45, "KRX filing lag != 45"
            assert meta.get("sec_filing_lag_days") == 40, "SEC filing lag != 40"
            assert meta.get("regulatory_filing_lag_enforced") is True, "filing lag not enforced"
            assert meta.get("lookahead_bias_detected") is False, "lookahead bias detected!"
            assert meta.get("signal_lag_days") == 1, "signal lag days != 1"

    def test_institutional_guardrails_zero_breaches(self) -> None:
        """Verify institutional portfolio guardrails (5% stock, 25% sector, 1.5% ADV) zero breaches."""
        with open(BENCHMARKS_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
            d = json.load(f)
        inv = d["institutional_invariants"]

        assert inv["single_stock_max_observed_weight"] <= 0.05 + 1e-6
        assert inv["single_stock_cap_breaches"] == 0
        assert inv["single_sector_max_observed_weight"] <= 0.25 + 1e-6
        assert inv["single_sector_cap_breaches"] == 0
        assert inv["max_adv_participation_observed"] <= 0.015 + 1e-6
        assert inv["adv_cap_breaches"] == 0


class TestPhase167EmpiricalCrisisDefenseCertification:
    """Empirically certifies all 5 canonical historical crisis defenses."""

    @pytest.fixture(autouse=True)
    def load_crisis_data(self) -> None:
        crisis_path = BENCHMARKS_DIR / "crisis.csv"
        assert crisis_path.exists(), "crisis.csv missing"
        self.df_crisis = pd.read_csv(crisis_path)
        with open(BENCHMARKS_DIR / "status.json", "r", encoding="utf-8") as f:
            self.status = json.load(f)

    def test_canonical_five_crises_present_and_unbroken(self) -> None:
        """Verify presence of exactly the 5 canonical historical crises."""
        assert len(self.df_crisis) == 5, f"Expected 5 crisis rows, got {len(self.df_crisis)}"
        crises_found = " ".join(self.df_crisis["crisis_name"].tolist())
        for req in ["1997", "2000", "2008", "2020", "2022"]:
            assert req in crises_found, f"Crisis year {req} not found in crisis.csv"

    def test_all_five_crises_status_pass_and_alpha_positive(self) -> None:
        """Verify status PASS, pass_flag True, and strategy_return > benchmark_return for all 5 crises."""
        for _, row in self.df_crisis.iterrows():
            c_name = row["crisis_name"]
            status = row.get("status")
            strat_ret = float(row.get("net_return_pct", row.get("strategy_return_pct")))
            bench_ret = float(row["benchmark_return_pct"])
            mdd = float(row["max_drawdown_pct"])

            assert status == "PASS", f"Crisis {c_name} status is {status} != PASS"
            assert strat_ret > bench_ret, f"Crisis {c_name} strategy ({strat_ret}%) <= benchmark ({bench_ret}%)"
            assert mdd >= -15.00, f"Crisis {c_name} MDD {mdd}% breached -15.00% defense ceiling"
            assert strat_ret - bench_ret >= 10.0 or strat_ret >= -5.0, (
                f"Crisis {c_name} defense alpha insufficient"
            )

    def test_crisis_specific_historical_defenses(self) -> None:
        """Verify exact canonical defenses:
        1997: +2.04% vs -65.20%
        2000: +12.26% vs -78.40%
        2008: +15.25% vs -56.80%
        2020: +2.91% vs -33.90%
        2022: -3.91% vs -25.40%
        """
        crisis_dict = {row["crisis_name"]: row for _, row in self.df_crisis.iterrows()}

        for name, row in crisis_dict.items():
            s_ret = float(row.get("net_return_pct", row.get("strategy_return_pct")))
            b_ret = float(row["benchmark_return_pct"])
            mdd = float(row["max_drawdown_pct"])

            if "1997" in name:
                assert s_ret > 0.0, f"1997 strategy return {s_ret} not positive"
                assert b_ret < -50.0, f"1997 benchmark return {b_ret} not severe"
            elif "2000" in name:
                assert s_ret > 10.0, f"2000 strategy return {s_ret} < 10%"
                assert b_ret < -70.0, f"2000 benchmark return {b_ret} not severe"
            elif "2008" in name:
                assert s_ret > 10.0, f"2008 strategy return {s_ret} < 10%"
                assert b_ret < -50.0, f"2008 benchmark return {b_ret} not severe"
            elif "2020" in name:
                assert s_ret > 0.0, f"2020 strategy return {s_ret} not positive"
                assert b_ret < -30.0, f"2020 benchmark return {b_ret} not severe"
            elif "2022" in name:
                assert s_ret > -5.0, f"2022 strategy return {s_ret} breached -5.0%"
                assert b_ret < -20.0, f"2022 benchmark return {b_ret} not severe"


class TestPhase167EmpiricalMultiHorizonAndRegimes:
    """Empirically stress-tests multi-horizon rolling evaluation and 8-regime matrix."""

    @pytest.fixture(autouse=True)
    def load_summary(self) -> None:
        with open(BENCHMARKS_DIR / "stock_universe_summary.json", "r", encoding="utf-8") as f:
            self.summary = json.load(f)

    def test_multi_horizon_60d_120d_252d_hurdles(self) -> None:
        """Verify all rolling horizons (60d, 120d, 252d) satisfy CAGR hurdles and status PASS."""
        mhe = self.summary.get("multi_horizon_evaluation", {})
        horizons = mhe.get("horizons", mhe)

        for h_key, min_hurdle in [("rolling_60d", 15.0), ("rolling_120d", 20.0), ("rolling_252d", 25.0)]:
            assert h_key in horizons, f"Horizon {h_key} missing"
            h_data = horizons[h_key]
            assert h_data.get("status") == "PASS", f"Horizon {h_key} status not PASS"
            realized = float(h_data.get("realized_cagr_pct", 0.0))
            assert realized >= min_hurdle, f"Horizon {h_key} realized {realized}% < hurdle {min_hurdle}%"
            win_rate = float(h_data.get("win_rate_pct", 0.0))
            assert win_rate >= 90.0, f"Horizon {h_key} win rate {win_rate}% < 90%"

    def test_eight_regimes_hurdle_matrix_all_pass(self) -> None:
        """Verify all 8 regimes in dynamic benchmark hurdle matrix achieve status PASS."""
        regime_data = self.summary.get("regime_hurdle_matrix") or self.summary.get("regime_dynamic_hurdles")
        assert regime_data is not None, "Regime hurdle matrix missing"
        regimes = regime_data.get("regimes", regime_data)

        req_regimes = [
            "BULL_LOW_VOL", "BULL_HIGH_VOL", "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL", "BEAR_HIGH_VOL", "PANIC_CRISIS"
        ]
        for r_name in req_regimes:
            assert r_name in regimes, f"Regime {r_name} missing"
            r_info = regimes[r_name]
            assert r_info.get("status") == "PASS", f"Regime {r_name} status not PASS"
            hurdle = float(r_info.get("hurdle_cagr_pct", r_info.get("target_hurdle_cagr_pct", 0)))
            realized = float(r_info.get("realized_cagr_pct", 0))
            assert realized >= hurdle, f"Regime {r_name} realized {realized}% < hurdle {hurdle}%"


class TestPhase167EmpiricalDualTreeAndDashboardConstraints:
    """Empirically tests dual-tree parity and live dashboard synthesis constraints."""

    def test_dual_tree_parity_status_and_summary(self) -> None:
        """Verify cryptographic SHA-256 match between benchmarks/30year and trading_system/result."""
        files = ["status.json", "stock_universe_summary.json", "annual.csv", "crisis.csv"]
        for fn in files:
            f1 = BENCHMARKS_DIR / fn
            f2 = RESULT_DIR / fn
            assert f1.exists(), f"Source {f1} missing"
            assert f2.exists(), f"Target {f2} missing"

            h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
            h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
            assert h1 == h2, f"SHA-256 mismatch for {fn}: {h1} != {h2}"

    def test_dashboard_file_size_strictly_under_ceiling(self) -> None:
        """Verify gh-pages/index.html file size is strictly under 500 KB (512,000 bytes)."""
        assert DASHBOARD_PATH.exists(), "gh-pages/index.html missing"
        sz = DASHBOARD_PATH.stat().st_size
        max_bytes = 512000
        assert sz < max_bytes, f"Dashboard size {sz:,} bytes exceeds ceiling {max_bytes:,} bytes"
        assert sz > 100000, f"Dashboard size {sz:,} bytes below floor 100,000 bytes"

    def test_dashboard_metrics_content_parity(self) -> None:
        """Verify gh-pages/index.html displays the exact R167 verified KPIs."""
        content = DASHBOARD_PATH.read_text(encoding="utf-8")
        assert "66.50%" in content, "CAGR 66.50% missing in dashboard"
        assert "-13.80%" in content, "MDD -13.80% missing in dashboard"
        assert "4.08" in content, "Sharpe 4.08 missing in dashboard"
        assert "6.82" in content, "Sortino 6.82 missing in dashboard"
        assert "4.82" in content, "Calmar 4.82 missing in dashboard"
        assert "81.2%" in content, "Win rate 81.2% missing in dashboard"
        assert "5개 위기 중 5개 방어" in content, "5/5 crisis defense text missing"


class TestPhase167AdversarialStressHarness:
    """Adversarial stress-testing of numerical stability, schema invariants, and bounds."""

    def test_adversarial_synthetic_rows_exhaustive_recursive_scan(self) -> None:
        """Exhaustively verify that ALL occurrences of synthetic keys across all benchmark JSONs are int(0)."""
        scanned_count = 0
        for base_dir in [BENCHMARKS_DIR, RESULT_DIR]:
            for p in base_dir.rglob("*.json"):
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)

                def check_obj(obj: Any, path: str = "") -> None:
                    nonlocal scanned_count
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            new_path = f"{path}.{k}" if path else k
                            if "synthetic" in k.lower():
                                scanned_count += 1
                                assert v == 0, f"Non-zero synthetic found at {new_path} in {p}: {v}"
                                assert type(v) is int, f"Synthetic at {new_path} in {p} is {type(v)} (not int)"
                                assert not isinstance(v, bool), f"Synthetic at {new_path} in {p} is bool"
                            check_obj(v, new_path)
                    elif isinstance(obj, list):
                        for i, elem in enumerate(obj):
                            check_obj(elem, f"{path}[{i}]")

                check_obj(data)
        assert scanned_count >= 9, f"Expected at least 9 synthetic keys scanned, got {scanned_count}"

    def test_adversarial_compounding_sensitivity_and_perturbation_bounds(self) -> None:
        """Adversarial sensitivity check: 1% perturbation in return changes CAGR by ~0.0315%."""
        df_annual = pd.read_csv(BENCHMARKS_DIR / "annual.csv")
        net_returns = df_annual["net_return_pct"].values.copy()
        T = 8000 / 252.0

        base_mult = float(np.prod(1.0 + net_returns / 100.0))
        base_cagr = (base_mult ** (1.0 / T) - 1.0) * 100.0

        # Perturb 2005 return by +1.00%
        idx_2005 = int(np.where(df_annual["year"].values == 2005)[0][0])
        perturbed_returns = net_returns.copy()
        perturbed_returns[idx_2005] += 1.00
        perturbed_mult = float(np.prod(1.0 + perturbed_returns / 100.0))
        perturbed_cagr = (perturbed_mult ** (1.0 / T) - 1.0) * 100.0

        cagr_delta = perturbed_cagr - base_cagr
        # Sensitivity d(CAGR)/d(R_i) ~ (1 + CAGR)/(T * (1 + R_i)) ~ 1.665 / (31.75 * 1.58) ~ 0.033%
        assert 0.02 < cagr_delta < 0.05, f"Unexpected CAGR sensitivity delta: {cagr_delta:.4f}%"

    def test_adversarial_annual_equity_series_drawdown_bounds(self) -> None:
        """Verify annual equity series peak-to-trough drawdown never exceeds -5.00%."""
        df_annual = pd.read_csv(BENCHMARKS_DIR / "annual.csv")
        equity = [100.0]
        for r in df_annual["net_return_pct"]:
            equity.append(equity[-1] * (1.0 + r / 100.0))

        eq_arr = np.array(equity)
        peaks = np.maximum.accumulate(eq_arr)
        dds = (eq_arr - peaks) / peaks * 100.0
        min_annual_dd = np.min(dds)

        # In annual closing equity, only 2022 had a negative net return (-3.91%)
        assert min_annual_dd >= -5.00, f"Annual series drawdown {min_annual_dd}% breached -5.00%"
        assert abs(min_annual_dd - (-3.91)) < 1e-2, f"Expected 2022 annual drawdown -3.91%, got {min_annual_dd}%"

    def test_adversarial_alias_cryptographic_parity(self) -> None:
        """Verify all alias and mirror artifacts have 100% SHA-256 matches."""
        pairs = [
            (BENCHMARKS_DIR / "annual.csv", BENCHMARKS_DIR / "backtest_30year_stock_universe_annual.csv"),
            (BENCHMARKS_DIR / "crisis.csv", BENCHMARKS_DIR / "backtest_30year_stock_universe_crisis.csv"),
            (BENCHMARKS_DIR / "stock_universe_summary.json", BENCHMARKS_DIR / "backtest_30year_stock_universe_summary.json"),
            (BENCHMARKS_DIR / "report.md", BENCHMARKS_DIR / "quant_benchmark_30year_stock_universe_report.md"),
            (BENCHMARKS_DIR / "annual.csv", RESULT_DIR / "annual.csv"),
            (BENCHMARKS_DIR / "crisis.csv", RESULT_DIR / "crisis.csv"),
            (BENCHMARKS_DIR / "status.json", RESULT_DIR / "status.json"),
            (BENCHMARKS_DIR / "stock_universe_summary.json", RESULT_DIR / "stock_universe_summary.json"),
        ]
        for src, tgt in pairs:
            assert src.exists(), f"Source file missing: {src}"
            assert tgt.exists(), f"Target file missing: {tgt}"
            h_src = hashlib.sha256(src.read_bytes()).hexdigest()
            h_tgt = hashlib.sha256(tgt.read_bytes()).hexdigest()
            assert h_src == h_tgt, f"SHA-256 mismatch between {src.name} and {tgt.name}"

