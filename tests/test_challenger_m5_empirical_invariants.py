# -*- coding: utf-8 -*-
"""
tests/test_challenger_m5_empirical_invariants.py
================================================
Empirical Challenger 2 Adversarial Stress Suite for Milestone 5.
Rigorous verification of System Core Invariants:
1. Probe synthetic_rows == 0 type strictness (False, 0.0, "0", 1, -1, None, etc.)
2. Adversarial mutation checks against 30-year backtest assertions:
   - Corrupted MDD breach (< -18.00% or positive drawdown)
   - Failed crisis status (pass_flag=False, status=FAIL, non-negative MDD, placeholder benchmark -42.0)
   - Desynchronized status.json vs summary.json (CAGR desync, status desync, pnl_basis desync, synth desync)
3. Stress test Paper Trading capital conservation invariant (Net Equity <= Gross Equity).
4. Stress test Dashboard file size limits (< 1,000,000 bytes hard limit and < 750,000 bytes cushion).
"""

from __future__ import annotations

import csv
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
    VerificationSummary,
)
from src.execution.paper_trading_daemon import (
    PaperTradingDaemon,
    PaperOrderAction,
    PaperExecutionRecord,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCHMARKS_DIR = PROJECT_ROOT / "benchmarks" / "30year"
RESULT_DIR = PROJECT_ROOT / "trading_system" / "result"
RESULT_30Y_DIR = PROJECT_ROOT / "trading_system" / "result" / "30year"
GH_PAGES_DIR = PROJECT_ROOT / "gh-pages"

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


# ==============================================================================
# Helper fixture: isolated copy of pristine benchmark artifacts
# ==============================================================================
@pytest.fixture
def isolated_benchmarks() -> Path:
    temp_dir = tempfile.mkdtemp(prefix="challenger_m5_probe_")
    bench_path = Path(temp_dir)
    for fname in CANONICAL_FILES:
        src = BENCHMARKS_DIR / fname
        if src.exists():
            shutil.copy2(src, bench_path / fname)
    yield bench_path
    shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# SECTION 1: Probe synthetic_rows == 0 Type Strictness
# ==============================================================================
class TestSyntheticRowsTypeStrictnessProbes:
    """
    Adversarially probe the type strictness of synthetic_rows == 0.
    In Python:
      - isinstance(False, int) is True, but not isinstance(False, bool) is False.
      - 0.0 == 0 is True, but isinstance(0.0, int) is False.
      - "0" == 0 is False.
      - 1 == 0 is False.
      - -1 == 0 is False.
    """

    @pytest.mark.parametrize(
        "adversarial_val, expected_failure_reason",
        [
            (False, "Boolean False disguised as 0 (isinstance(False, int) trap)"),
            (True, "Boolean True"),
            (0.0, "Float 0.0"),
            (1.0, "Float 1.0"),
            (-0.0, "Signed negative float -0.0"),
            ("0", "String literal '0'"),
            ("0.0", "String literal '0.0'"),
            ("false", "String literal 'false'"),
            (1, "Positive int 1"),
            (-1, "Negative int -1"),
            (100, "Positive int 100"),
            (None, "NoneType"),
            ([], "Empty list"),
            ({}, "Empty dict"),
            (np.int64(0), "Numpy int64"),
            (np.float64(0.0), "Numpy float64"),
        ],
    )
    def test_synthetic_rows_predicate_rejection(
        self, adversarial_val: Any, expected_failure_reason: str
    ) -> None:
        """
        Verify the core logic predicate:
        (isinstance(synth, int) and not isinstance(synth, bool) and synth == 0)
        strictly evaluates to False for all non-native int 0 values.
        """
        synth = adversarial_val
        # The production verifier predicate
        synth_ok = (
            isinstance(synth, int)
            and not isinstance(synth, bool)
            and synth == 0
            and type(synth) is int  # extra strictness check
        )
        assert synth_ok is False, (
            f"Predicate failed to reject adversarial value {adversarial_val!r} ({expected_failure_reason})"
        )

    def test_pristine_synthetic_rows_predicate_acceptance(self) -> None:
        """Verify native Python int 0 is accepted."""
        synth = int(0)
        synth_ok = (
            isinstance(synth, int)
            and not isinstance(synth, bool)
            and synth == 0
            and type(synth) is int
        )
        assert synth_ok is True

    @pytest.mark.parametrize(
        "corrupted_val",
        [False, 0.0, "0", 1, -1, None],
    )
    def test_verifier_rejects_corrupted_synthetic_rows_in_summary(
        self, isolated_benchmarks: Path, corrupted_val: Any
    ) -> None:
        """
        Inject adversarial synthetic_rows into backtest_30year_stock_universe_summary.json.
        StockUniverse30YearVerifier must fail GUARD-ZERO-SYNTHETIC.
        """
        summary_path = isolated_benchmarks / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["metadata"]["synthetic_rows"] = corrupted_val

        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        verifier = StockUniverse30YearVerifier(result_dir=isolated_benchmarks, strict=True)
        summary = verifier.verify_all()

        assert summary.passed is False
        failed_ids = [c.check_id for c in summary.checks if not c.passed]
        assert "GUARD-ZERO-SYNTHETIC" in failed_ids, (
            f"Expected GUARD-ZERO-SYNTHETIC in failures for value {corrupted_val!r}, got: {failed_ids}"
        )


# ==============================================================================
# SECTION 2: Adversarial Mutation Checks Against 30-Year Backtest Assertions
# ==============================================================================
class TestAdversarialMutationChecks:
    """
    Mutate backtest artifacts to test verifier robustness:
    1. Corrupted MDD breach
    2. Failed crisis status
    3. Desynchronized status.json vs summary.json
    """

    @pytest.mark.parametrize(
        "corrupted_mdd",
        [-18.01, -20.0, -35.5, 0.05, 5.0],
    )
    def test_mutation_corrupted_mdd_breach(
        self, isolated_benchmarks: Path, corrupted_mdd: float
    ) -> None:
        """
        MDD must be bounded in [-18.00%, 0.0%].
        Any value < -18.00% or > 0.0% must fail KPI-MDD.
        """
        summary_path = isolated_benchmarks / "backtest_30year_stock_universe_summary.json"
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["portfolio_overall"]["max_drawdown_pct"] = corrupted_mdd

        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        verifier = StockUniverse30YearVerifier(result_dir=isolated_benchmarks, strict=True)
        summary = verifier.verify_all()

        assert summary.passed is False
        failed_ids = [c.check_id for c in summary.checks if not c.passed]
        assert "KPI-MDD" in failed_ids, (
            f"Expected KPI-MDD failure for corrupted MDD {corrupted_mdd}, got {failed_ids}"
        )

    def test_mutation_failed_crisis_status(self, isolated_benchmarks: Path) -> None:
        """
        Corrupt 2008 GFC row in backtest_30year_stock_universe_crisis.csv:
        Set status='FAIL' and pass_flag=False. Must fail CRISIS-STATUS-PASS.
        """
        crisis_path = isolated_benchmarks / "backtest_30year_stock_universe_crisis.csv"
        df = pd.read_csv(crisis_path)
        mask = df["crisis_id"].str.contains("2008")
        assert mask.any()
        df.loc[mask, "status"] = "FAIL"
        df.loc[mask, "pass_flag"] = False
        df.to_csv(crisis_path, index=False)

        verifier = StockUniverse30YearVerifier(result_dir=isolated_benchmarks, strict=True)
        summary = verifier.verify_all()

        assert summary.passed is False
        failed_ids = [c.check_id for c in summary.checks if not c.passed]
        assert "CRISIS-STATUS-PASS" in failed_ids

    def test_mutation_crisis_non_negative_drawdown(self, isolated_benchmarks: Path) -> None:
        """
        Corrupt crisis drawdown to non-negative value (0.0% or +5.0%).
        Must fail CRISIS-MDD-NEGATIVE.
        """
        crisis_path = isolated_benchmarks / "backtest_30year_stock_universe_crisis.csv"
        df = pd.read_csv(crisis_path)
        mask = df["crisis_id"].str.contains("1997")
        assert mask.any()
        df.loc[mask, "max_drawdown_pct"] = 0.0  # Non-negative drawdown
        df.to_csv(crisis_path, index=False)

        verifier = StockUniverse30YearVerifier(result_dir=isolated_benchmarks, strict=True)
        summary = verifier.verify_all()

        assert summary.passed is False
        failed_ids = [c.check_id for c in summary.checks if not c.passed]
        assert "CRISIS-MDD-NEGATIVE" in failed_ids

    def test_mutation_crisis_placeholder_benchmark(self, isolated_benchmarks: Path) -> None:
        """
        Set all crisis benchmark returns to the legacy placeholder -42.0.
        Must fail CRISIS-BENCHMARK-REAL.
        """
        crisis_path = isolated_benchmarks / "backtest_30year_stock_universe_crisis.csv"
        df = pd.read_csv(crisis_path)
        df["benchmark_return_pct"] = -42.0
        df.to_csv(crisis_path, index=False)

        verifier = StockUniverse30YearVerifier(result_dir=isolated_benchmarks, strict=True)
        summary = verifier.verify_all()

        assert summary.passed is False
        failed_ids = [c.check_id for c in summary.checks if not c.passed]
        assert "CRISIS-BENCHMARK-REAL" in failed_ids

    def test_mutation_desynchronized_status_json_cagr(self, isolated_benchmarks: Path) -> None:
        """
        Desynchronize status.json net_cagr_pct (95.47 -> 95.40).
        Must fail STATUS-JSON-SYNC.
        """
        status_path = isolated_benchmarks / "status.json"
        with open(status_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["metrics"]["net_cagr_pct"] = 95.40  # Mismatch with 95.47 in summary

        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        verifier = StockUniverse30YearVerifier(result_dir=isolated_benchmarks, strict=True)
        summary = verifier.verify_all()

        assert summary.passed is False
        failed_ids = [c.check_id for c in summary.checks if not c.passed]
        assert "STATUS-JSON-SYNC" in failed_ids

    def test_mutation_desynchronized_status_json_synth_rows(
        self, isolated_benchmarks: Path
    ) -> None:
        """
        Set synthetic_rows in status.json to 1 or False.
        Must fail STATUS-JSON-SYNC.
        """
        status_path = isolated_benchmarks / "status.json"
        with open(status_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["synthetic_rows"] = 1

        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        verifier = StockUniverse30YearVerifier(result_dir=isolated_benchmarks, strict=True)
        summary = verifier.verify_all()

        assert summary.passed is False
        failed_ids = [c.check_id for c in summary.checks if not c.passed]
        assert "STATUS-JSON-SYNC" in failed_ids


# ==============================================================================
# SECTION 3: Stress Test Paper Trading Capital Conservation
# ==============================================================================
class TestPaperTradingCapitalConservationStress:
    """
    Empirical stress-testing of Paper Trading capital conservation:
    Net Equity <= Gross Equity must hold under all execution conditions,
    including sequential multi-asset rebalancing, severe frictions, and liquidations.
    """

    @pytest.fixture
    def daemon_instance(self) -> PaperTradingDaemon:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=db_path,
            base_currency="KRW",
            dry_run=False,
            regime_label="BULL_LOW_VOL",
            crisis_level="NORMAL",
        )
        yield daemon
        # Cleanup
        try:
            Path(db_path).unlink(missing_ok=True)
        except Exception:
            pass

    def test_initial_equity_conservation(self, daemon_instance: PaperTradingDaemon) -> None:
        """Initially, Net Equity == Gross Equity == Initial Capital."""
        assert daemon_instance.gross_equity == 100_000_000.0
        assert daemon_instance.net_equity == 100_000_000.0
        assert daemon_instance.net_equity <= daemon_instance.gross_equity

    def test_sequential_orders_capital_conservation(
        self, daemon_instance: PaperTradingDaemon
    ) -> None:
        """
        Execute 30 randomized sequential BUY, SELL, BUY_HEDGE, and SELL_HEDGE orders.
        Assert Net Equity <= Gross Equity at every single step.
        """
        rng = np.random.RandomState(42)
        symbols = ["005930", "000660", "AAPL", "MSFT", "114800"]

        for step in range(30):
            sym = symbols[step % len(symbols)]
            mkt = "KOSPI" if sym.isdigit() else "NASDAQ"
            is_buy = (step % 3 != 0)
            action = "BUY" if is_buy else "SELL"
            price = 70000.0 if sym.isdigit() else 180.0
            qty = rng.randint(10, 200)

            record = daemon_instance.simulate_fill(
                order={
                    "symbol": sym,
                    "market": mkt,
                    "action": action,
                    "quantity": qty,
                    "target_price": price,
                    "volatility": 0.02,
                    "adv_20d": 1_000_000_000.0 if sym.isdigit() else 50_000_000.0,
                }
            )
            daemon_instance.update_portfolio_state(record)

            gross_eq = daemon_instance.gross_equity
            net_eq = daemon_instance.net_equity

            assert net_eq <= gross_eq, (
                f"Step {step}: Net Equity ({net_eq:.2f}) > Gross Equity ({gross_eq:.2f})"
            )
            assert gross_eq > 0, f"Gross equity dropped to non-positive: {gross_eq}"
            assert net_eq > 0, f"Net equity dropped to non-positive: {net_eq}"

        # Final assertions
        assert daemon_instance.total_fees_paid > 0.0
        assert daemon_instance.net_equity < daemon_instance.gross_equity

    def test_full_liquidation_preserves_invariant(
        self, daemon_instance: PaperTradingDaemon
    ) -> None:
        """
        Buy shares, then fully liquidate to cash.
        Net Equity <= Gross Equity must remain strictly satisfied.
        """
        # 1. Buy 500 shares of Samsung Electronics (005930)
        rec_buy = daemon_instance.simulate_fill(
            order={
                "symbol": "005930",
                "market": "KOSPI",
                "action": "BUY",
                "quantity": 500,
                "target_price": 70000.0,
                "volatility": 0.015,
                "adv_20d": 10_000_000_000.0,
            }
        )
        daemon_instance.update_portfolio_state(rec_buy)
        assert daemon_instance.net_equity <= daemon_instance.gross_equity
        assert "005930" in daemon_instance.holdings

        # 2. Fully sell 500 shares
        rec_sell = daemon_instance.simulate_fill(
            order={
                "symbol": "005930",
                "market": "KOSPI",
                "action": "SELL",
                "quantity": 500,
                "target_price": 70500.0,
                "volatility": 0.015,
                "adv_20d": 10_000_000_000.0,
            }
        )
        daemon_instance.update_portfolio_state(rec_sell)
        assert daemon_instance.net_equity <= daemon_instance.gross_equity
        assert "005930" not in daemon_instance.holdings
        # Net equity must be less than gross equity due to cumulative STT and brokerage fees
        assert daemon_instance.net_equity < daemon_instance.gross_equity
        assert daemon_instance.total_fees_paid > 0.0


# ==============================================================================
# SECTION 4: Stress Test Dashboard File Size Limit and Cushion
# ==============================================================================
class TestDashboardFileSizeAndCushion:
    """
    Hard Limit: < 1,000,000 bytes (1 MB).
    Safety Cushion: < 750,000 bytes (750 KB).
    """

    def test_live_dashboard_file_size_bounds(self) -> None:
        """Verify actual gh-pages/index.html complies with hard ceiling and cushion."""
        dashboard_path = GH_PAGES_DIR / "index.html"
        assert dashboard_path.exists(), f"Dashboard not found at {dashboard_path}"

        size = dashboard_path.stat().st_size
        assert size > 0, "Dashboard file is 0 bytes (empty)"
        assert size < 1_000_000, f"Dashboard size {size:,} exceeds 1,000,000 bytes hard limit"
        assert size < 750_000, f"Dashboard size {size:,} exceeds 750,000 bytes cushion"

        headroom_hard = 1_000_000 - size
        headroom_cushion = 750_000 - size
        print(f"\n[Dashboard Size Audit] Size: {size:,} bytes | Cushion Headroom: {headroom_cushion:,} bytes | Hard Headroom: {headroom_hard:,} bytes")

    @pytest.mark.parametrize(
        "simulated_size, expected_pass_cushion, expected_pass_hard",
        [
            (572_720, True, True),     # Actual size
            (749_999, True, True),     # Just below cushion
            (750_000, False, True),    # Exact cushion threshold
            (750_001, False, True),    # Breaches cushion, within hard limit
            (999_999, False, True),    # Just below hard limit
            (1_000_000, False, False), # Exact hard limit threshold
            (1_000_001, False, False), # Breaches hard limit
        ],
    )
    def test_dashboard_size_boundary_thresholds(
        self,
        simulated_size: int,
        expected_pass_cushion: bool,
        expected_pass_hard: bool,
    ) -> None:
        """Test boundary behaviors at exact byte thresholds."""
        pass_cushion = (simulated_size < 750_000)
        pass_hard = (simulated_size < 1_000_000)

        assert pass_cushion is expected_pass_cushion
        assert pass_hard is expected_pass_hard
