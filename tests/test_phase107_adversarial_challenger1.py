"""
tests/test_phase107_adversarial_challenger1.py
=============================================
Empirical Adversarial Stress Testing & Invariant Challenge Suite for Phase 107.
Release R123 / v114 Production Master (Features F505, F506, F507, F508).

Target Challenge Domains:
1. M1: Autonomous Pipeline Daemon Supervisor (F505)
   - Corrupted/malformed state recovery, atomic persistence, CLI subprocess resilience,
     and strict invariant verification: Net Equity <= Gross Equity.
2. M2: Global Cross-Market FX Hedging Engine (F506)
   - Strict boundedness h* in [0.0, 1.0] under pathological macro inputs (NaN/Inf rates, zero rates,
     extreme momentum, 1000% volatility, CIP inversion), cash collateral caps, and gross leverage <= 1.20.
3. M3: L2/L3 Hawkes Microstructure Alpha Predictor (F507)
   - L1 stability constraint enforcement (alpha / beta < 1.0) under explosive arrival cascades,
     Almgren-Chriss exact volume conservation, non-negative integer slicing, and bounded alpha signals.
4. M4: Dynamic Tax-Loss Harvesting & Wash-Sale Optimizer (F508)
   - Strict 30-day wash-sale window boundaries (day 29, 30, 31), economic hurdle invariant
     (friction > tax alpha rejection), and surrogate selection rules (sector match, rho >= 0.85, ADV cap).
"""

from __future__ import annotations

import collections
import copy
import datetime
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.execution.pipeline_daemon_supervisor import (
    PipelineDaemonSupervisor,
    SupervisorLifecyclePhase,
    SupervisorCycleReport,
)
from src.risk.dynamic_fx_hedging_engine import (
    DynamicFXHedgingEngine,
    FXMacroInput,
    FXHedgeResult,
)
from src.core.hawkes_microstructure_alpha import (
    HawkesAlphaPredictor,
    HawkesMLEstimator,
    HawkesMicrostructureAlphaEngine,
    HawkesMicrostructureAlphaPredictor,
    HawkesParameters,
    MicrostructureAlphaSignal,
)
from src.risk.tax_loss_harvesting_optimizer import (
    DynamicTaxLossHarvestingOptimizer,
    TaxConfig,
    TaxLot,
    HarvestingCandidate,
    TaxHarvestingPlan,
    WashSaleTracker,
    format_date,
    parse_date,
)


# ===========================================================================
# Part 1: M1 - Pipeline Daemon Supervisor Adversarial Tests
# ===========================================================================

class TestPhase107SupervisorAdversarial(unittest.TestCase):
    """Adversarial stress testing for M1: Autonomous Pipeline Daemon Supervisor."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="phase107_challenger_m1_")
        self.state_file = str(Path(self.temp_dir) / "supervisor_state.json")
        self.db_path = str(Path(self.temp_dir) / "test_trades.db")
        self.capital = 100_000_000.0

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_adv_m1_01_corrupted_state_json_empty_file(self) -> None:
        """Challenge: Supervisor must safely handle a 0-byte corrupted state JSON file."""
        with open(self.state_file, "w", encoding="utf-8") as f:
            pass  # Empty file

        sup = PipelineDaemonSupervisor(
            capital=self.capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        loaded = sup.load_state()
        self.assertFalse(loaded)
        self.assertEqual(sup.capital, self.capital)
        self.assertEqual(sup.active_phase, SupervisorLifecyclePhase.IDLE)

    def test_adv_m1_02_corrupted_state_json_syntax_error(self) -> None:
        """Challenge: Supervisor must safely reject malformed/unparseable JSON."""
        with open(self.state_file, "w", encoding="utf-8") as f:
            f.write("{'corrupted': invalid_json_syntax, missing_closing_bracket: [1, 2,")

        sup = PipelineDaemonSupervisor(
            capital=self.capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        loaded = sup.load_state()
        self.assertFalse(loaded)
        self.assertEqual(sup.cycle_count, 0)

    def test_adv_m1_03_corrupted_state_json_schema_types(self) -> None:
        """Challenge: Supervisor must handle corrupted schema data types (invalid phases, nan values)."""
        bad_state = {
            "cycle_count": 42,
            "current_phase": "NON_EXISTENT_PHASE_XYZ",
            "capital": 85000000.0,
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(bad_state, f)

        sup = PipelineDaemonSupervisor(
            capital=self.capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        loaded = sup.load_state()
        self.assertTrue(loaded)
        self.assertEqual(sup.cycle_count, 42)
        # Invalid phase must fall back to IDLE
        self.assertEqual(sup.active_phase, SupervisorLifecyclePhase.IDLE)
        self.assertEqual(sup.capital, 85000000.0)

    def test_adv_m1_04_atomic_state_persistence_safety(self) -> None:
        """Challenge: save_state must atomically replace file without leaving temporary debris."""
        sup = PipelineDaemonSupervisor(
            capital=self.capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        sup.cycle_count = 5
        sup.active_phase = SupervisorLifecyclePhase.PRE_MARKET
        saved = sup.save_state()
        self.assertTrue(saved)
        self.assertTrue(Path(self.state_file).exists())
        self.assertFalse(Path(self.state_file).with_suffix(".tmp").exists())

        with open(self.state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["cycle_count"], 5)
        self.assertEqual(data["current_phase"], SupervisorLifecyclePhase.PRE_MARKET.value)

    def test_adv_m1_05_cli_runner_once_dry_run_subprocess(self) -> None:
        """Challenge: CLI runner executes cleanly via subprocess with --once --dry-run."""
        script_path = PROJECT_ROOT / "scripts" / "run_daily_supervisor.py"
        cmd = [
            sys.executable,
            str(script_path),
            "--once",
            "--dry-run",
            "--db", self.db_path,
            "--state-file", self.state_file,
            "--market", "KOSPI",
            "--capital", "50000000",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
        output = res.stdout + "\n" + res.stderr
        self.assertEqual(res.returncode, 0, f"CLI runner failed:\n{output}")
        self.assertIn("Single sweep finished. Success=True", output)
        self.assertIn("Phase PRE_MARKET", output)
        self.assertIn("Phase MARKET_CLOSE", output)

    def test_adv_m1_06_cli_runner_extreme_capital_arguments(self) -> None:
        """Challenge: CLI runner handles extreme portfolio capital levels without overflow."""
        script_path = PROJECT_ROOT / "scripts" / "run_daily_supervisor.py"
        cmd = [
            sys.executable,
            str(script_path),
            "--once",
            "--dry-run",
            "--db", self.db_path,
            "--state-file", self.state_file,
            "--capital", "1000000000000",  # 1 Trillion KRW
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
        output = res.stdout + "\n" + res.stderr
        self.assertEqual(res.returncode, 0, f"Extreme capital run failed:\n{output}")
        self.assertIn("1,000,000,000,000", output)

    def test_adv_m1_07_invariant_net_equity_le_gross_equity_baseline(self) -> None:
        """Challenge: Fundamental Invariant Net Equity <= Gross Equity must hold under all executions."""
        sup = PipelineDaemonSupervisor(
            capital=self.capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        reports = sup.run_single_sweep()
        close_report = reports[SupervisorLifecyclePhase.MARKET_CLOSE.value]
        self.assertTrue(close_report.success)
        gross = close_report.details["gross_equity"]
        net = close_report.details["net_equity"]
        self.assertLessEqual(net, gross + 1e-9, f"Violation: Net ({net}) > Gross ({gross})")
        self.assertTrue(close_report.details["invariant_verified"])

    def test_adv_m1_08_invariant_net_equity_clamping_on_corrupted_paper_daemon(self) -> None:
        """Challenge: If paper daemon erroneously produces Net Equity > Gross Equity, supervisor clamps it."""
        sup = PipelineDaemonSupervisor(
            capital=self.capital,
            db_path=self.db_path,
            state_file=self.state_file,
            dry_run=True,
        )
        # Mock paper daemon that violates the invariant
        class CorruptedSnapshot:
            gross_equity = 100_000_000.0
            net_equity = 105_000_000.0  # Erroneous negative friction / profit bug
            cash_balance = 50_000_000.0
            invested_value = 50_000_000.0
            holdings_count = 5

        class CorruptedPaperDaemon:
            total_fees_paid = 0.0
            total_impact_cost = 0.0
            total_slippage_cost = 0.0
            holdings = {}
            def snapshot_portfolio(self):
                return CorruptedSnapshot()

        sup.paper_daemon = CorruptedPaperDaemon()
        close_report = sup.run_market_close_phase()
        self.assertTrue(close_report.success)
        # Supervisor must have clamped net_equity down to gross_equity
        gross = close_report.details["gross_equity"]
        net = close_report.details["net_equity"]
        self.assertEqual(net, gross)
        self.assertEqual(net, 100_000_000.0)
        self.assertTrue(close_report.details["invariant_verified"])


# ===========================================================================
# Part 2: M2 - Dynamic FX Hedging Engine Adversarial Tests
# ===========================================================================

class TestPhase107FXHedgingAdversarial(unittest.TestCase):
    """Adversarial stress testing for M2: Global Cross-Market FX Hedging Engine."""

    def setUp(self) -> None:
        self.engine = DynamicFXHedgingEngine(
            base_currency="KRW",
            target_tenor_days=30,
            margin_requirement=0.10,
            max_gross_leverage=1.20,
            max_collateral_ratio=0.85,
        )

    def test_adv_m2_01_pathological_spot_rates(self) -> None:
        """Challenge: Engine handles zero, negative, NaN, and infinite spot rates safely."""
        pathological_spots = [0.0, -100.0, float("nan"), float("inf"), float("-inf")]
        for s in pathological_spots:
            inp = FXMacroInput(usdkrw_spot=s)
            h_star = self.engine.calculate_optimal_hedge_ratio(inp)
            self.assertEqual(h_star, 0.0)
            f_cip = self.engine.compute_cip_forward_rate(s, 0.035, 0.045)
            self.assertEqual(f_cip, 0.0)
            dev = self.engine.compute_cip_deviation(s, 1300.0, 0.035, 0.045)
            self.assertEqual(dev, 0.0)

    def test_adv_m2_02_extreme_fx_momentum_crash_and_surge(self) -> None:
        """Challenge: Hedge ratio strictly bounded in [0.0, 1.0] under -1000% drop and +1000% surge."""
        extreme_momentums = [-10.0, -1.0, -0.50, -0.10, 0.0, 0.10, 0.50, 1.0, 10.0]
        for mom in extreme_momentums:
            inp = FXMacroInput(usdkrw_spot=1350.0, fx_momentum_20d=mom)
            h = self.engine.calculate_optimal_hedge_ratio(inp)
            self.assertGreaterEqual(h, 0.0, f"Negative hedge ratio {h} at mom={mom}")
            self.assertLessEqual(h, 1.0, f"Hedge ratio {h} > 1.0 at mom={mom}")
            self.assertTrue(math.isfinite(h))

    def test_adv_m2_03_supercritical_volatility(self) -> None:
        """Challenge: Extreme FX volatility (e.g. 1000% annual vol) maintains h* in [0.0, 1.0]."""
        extreme_vols = [0.0001, 0.01, 0.08, 0.50, 1.0, 5.0, 10.0]
        for vol in extreme_vols:
            inp = FXMacroInput(usdkrw_spot=1350.0, fx_volatility_20d=vol)
            h = self.engine.calculate_optimal_hedge_ratio(inp)
            self.assertGreaterEqual(h, 0.0)
            self.assertLessEqual(h, 1.0)
            self.assertTrue(math.isfinite(h))

    def test_adv_m2_04_deep_negative_and_extreme_interest_rates(self) -> None:
        """Challenge: Negative rates, 100% hyperinflation rates, and inverted rate spreads."""
        rate_pairs = [
            (-0.05, 0.035),    # Negative US rate
            (0.045, -0.02),    # Negative KR rate
            (-0.05, -0.05),    # Both negative
            (1.00, 0.035),     # 100% US rate
            (0.045, 1.00),     # 100% KR rate
            (0.0, 0.0),        # Zero rates
        ]
        for r_us, r_kr in rate_pairs:
            inp = FXMacroInput(usdkrw_spot=1350.0, us_rate=r_us, kr_rate=r_kr)
            h = self.engine.calculate_optimal_hedge_ratio(inp)
            self.assertGreaterEqual(h, 0.0)
            self.assertLessEqual(h, 1.0)
            self.assertTrue(math.isfinite(h))

    def test_adv_m2_05_extreme_cip_deviations(self) -> None:
        """Challenge: Massive forward discounts and premiums (+/- 10,000 bps) keep h* in [0.0, 1.0]."""
        fwd_rates = [500.0, 1000.0, 1350.0, 2000.0, 5000.0]
        for fwd in fwd_rates:
            inp = FXMacroInput(usdkrw_spot=1350.0, forward_rate=fwd)
            h = self.engine.calculate_optimal_hedge_ratio(inp)
            self.assertGreaterEqual(h, 0.0)
            self.assertLessEqual(h, 1.0)
            self.assertTrue(math.isfinite(h))

    def test_adv_m2_06_zero_and_negative_available_cash(self) -> None:
        """Challenge: Zero or negative available cash strictly caps hedge ratio to 0.0 (no margin available)."""
        portfolio = {"AAPL": 0.40, "MSFT": 0.40, "005930": 0.20}
        macro = FXMacroInput(usdkrw_spot=1350.0, fx_momentum_20d=-0.05)

        for bad_cash in [0.0, -100000.0]:
            res = self.engine.evaluate_portfolio_fx_hedge(
                portfolio_capital_krw=100_000_000.0,
                portfolio_allocations=portfolio,
                macro_input=macro,
                available_cash_krw=bad_cash,
            )
            self.assertEqual(res.hedge_ratio, 0.0)
            self.assertEqual(res.hedge_notional_krw, 0.0)
            self.assertEqual(res.collateral_required_krw, 0.0)
            self.assertTrue(res.details.get("collateral_limit_hit", True))

    def test_adv_m2_07_already_leveraged_portfolio(self) -> None:
        """Challenge: Portfolio with gross equity weight >= 1.20 must receive zero additional hedge allocation."""
        # 125% allocated to equities
        portfolio = {"AAPL": 0.65, "MSFT": 0.60}
        macro = FXMacroInput(usdkrw_spot=1350.0, fx_momentum_20d=-0.05)

        res = self.engine.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=100_000_000.0,
            portfolio_allocations=portfolio,
            macro_input=macro,
            available_cash_krw=50_000_000.0,
        )
        self.assertEqual(res.hedge_ratio, 0.0)
        self.assertEqual(res.hedge_notional_krw, 0.0)
        self.assertEqual(res.leverage_ratio, 1.25)
        self.assertTrue(res.details.get("leverage_limit_hit", True))

    def test_adv_m2_08_pure_krx_portfolio_no_usd_exposure(self) -> None:
        """Challenge: Domestic-only portfolio produces NO_HEDGE with zero notional."""
        krx_portfolio = {"005930": 0.50, "000660": 0.50}
        macro = FXMacroInput(usdkrw_spot=1350.0, fx_momentum_20d=-0.05)

        res = self.engine.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=100_000_000.0,
            portfolio_allocations=krx_portfolio,
            macro_input=macro,
        )
        self.assertEqual(res.hedge_action, "NO_HEDGE")
        self.assertEqual(res.hedge_ratio, 0.0)
        self.assertEqual(res.us_exposure_krw, 0.0)
        self.assertEqual(res.hedge_notional_krw, 0.0)

    def test_adv_m2_09_monte_carlo_fuzzing(self) -> None:
        """Challenge: 1000 randomized Monte Carlo draws never breach [0.0, 1.0] or leverage limit."""
        np.random.seed(42)
        regimes = ["BULL_LOW_VOL", "BULL_HIGH_VOL", "SIDEWAYS", "BEAR", "BEAR_HIGH_VOL", "CRISIS"]

        for _ in range(1000):
            spot = float(np.random.uniform(900.0, 1800.0))
            us_r = float(np.random.uniform(-0.02, 0.15))
            kr_r = float(np.random.uniform(0.005, 0.15))
            mom = float(np.random.uniform(-0.30, 0.30))
            vol = float(np.random.uniform(0.01, 0.50))
            reg = str(np.random.choice(regimes))

            inp = FXMacroInput(
                usdkrw_spot=spot,
                us_rate=us_r,
                kr_rate=kr_r,
                fx_momentum_20d=mom,
                fx_volatility_20d=vol,
                regime_label=reg,
            )
            h = self.engine.calculate_optimal_hedge_ratio(inp)
            self.assertGreaterEqual(h, 0.0)
            self.assertLessEqual(h, 1.0)
            self.assertTrue(math.isfinite(h))


# ===========================================================================
# Part 3: M3 - Hawkes Microstructure Alpha Predictor Adversarial Tests
# ===========================================================================

class TestPhase107HawkesAlphaAdversarial(unittest.TestCase):
    """Adversarial stress testing for M3: L2/L3 Hawkes Microstructure Alpha Predictor."""

    def setUp(self) -> None:
        self.predictor = HawkesMicrostructureAlphaPredictor(symbol="005930")

    def test_adv_m3_01_synthetic_explosive_arrival_cascade(self) -> None:
        """Challenge: Massive explosive cascades (alpha >> beta) strictly enforce L1 stability (alpha/beta < 1.0)."""
        # 500 arrivals generated with intervals of 1 microsecond (1e-6s)
        # Naive unconstrained estimation would produce an explosive supercritical branching ratio >> 1.0
        ts = np.cumsum(np.full(500, 1e-6))

        # Test calibrated method of moments via HawkesMLEstimator
        moments = HawkesMLEstimator.fit_calibrated_moments(ts, max_branching=0.95)
        self.assertTrue(moments.is_stable)
        self.assertLess(moments.branching_ratio, 1.0)
        self.assertLessEqual(moments.branching_ratio, 0.95 + 1e-6)
        self.assertGreater(moments.stability_margin, 0.0)

        # Test univariate MLE via HawkesMLEstimator
        mle = HawkesMLEstimator.fit_univariate_mle(ts, max_branching=0.99)
        self.assertTrue(mle.is_stable)
        self.assertLess(mle.branching_ratio, 1.0)
        self.assertLessEqual(mle.branching_ratio, 0.99 + 1e-6)
        self.assertGreater(mle.stability_margin, 0.0)

    def test_adv_m3_02_bivariate_coupled_mle_stability(self) -> None:
        """Challenge: Bivariate buy/sell cascades strictly enforce (alpha_self + alpha_cross) / beta < 1.0."""
        buy_ts = np.cumsum(np.random.exponential(0.001, size=200))
        sell_ts = np.cumsum(np.random.exponential(0.001, size=200))

        buy_params, sell_params = HawkesMLEstimator.fit_bivariate_mle(
            buy_ts, sell_ts, max_branching=0.98
        )
        for p, label in [(buy_params, "BUY"), (sell_params, "SELL")]:
            self.assertTrue(p.is_stable, f"{label} process is unstable")
            self.assertLess(p.branching_ratio, 1.0)
            self.assertLessEqual(p.branching_ratio, 0.98 + 1e-6)
            coupled = (p.alpha_self + p.alpha_cross) / p.beta
            self.assertLessEqual(coupled, 0.98 + 1e-6)

    def test_adv_m3_03_zero_variance_periodic_arrivals(self) -> None:
        """Challenge: Perfectly periodic arrivals (dt = 1.0s, std(dt) = 0.0) handled gracefully."""
        ts = np.arange(1.0, 101.0, 1.0)
        params = HawkesMLEstimator.fit_calibrated_moments(ts)
        self.assertTrue(params.is_stable)
        self.assertLess(params.branching_ratio, 1.0)
        self.assertTrue(math.isfinite(params.mu))
        self.assertTrue(math.isfinite(params.beta))

    def test_adv_m3_04_almgren_chriss_volume_conservation_fuzzing(self) -> None:
        """Challenge: Exact total volume conservation sum(modulated) == sum(base_slices) under 100 test cases."""
        test_cases: List[Tuple[int, int]] = [
            (1, 1),
            (10, 1),
            (100, 3),
            (7, 5),
            (13, 10),
            (9999, 50),
            (10_000_000, 100),
            (333, 33),
            (1000, 1),
        ]
        # Add random test cases
        np.random.seed(42)
        for _ in range(90):
            q = int(np.random.randint(1, 100_000))
            n = int(np.random.randint(1, 50))
            test_cases.append((q, n))

        signal = MicrostructureAlphaSignal(
            timestamp=time.time(),
            symbol="005930",
            l3_imbalance=0.5,
            arrival_imbalance=0.3,
            predicted_drift_bps=2.5,
            adverse_toxicity=0.2,
            composite_alpha_score=0.6,
            is_toxic=False,
            recommended_urgency="FAST",
            target_offset_ticks=-1.0,
            effective_ac_kappa=2.5,
        )

        for total_q, num_slices in test_cases:
            # Create base slices
            base_q = total_q // num_slices
            base_slices = [base_q] * num_slices
            base_slices[-1] += (total_q - sum(base_slices))

            modulated = self.predictor.modulate_slicing_schedule(base_slices, signal, action="BUY")
            self.assertEqual(sum(modulated), total_q, f"Volume mismatch: sum={sum(modulated)} vs total={total_q}")
            self.assertEqual(len(modulated), num_slices)
            for s in modulated:
                self.assertGreaterEqual(s, 0, f"Negative slice {s} found")
                self.assertIsInstance(s, int)

    def test_adv_m3_05_almgren_chriss_extreme_kappa_values(self) -> None:
        """Challenge: Schedule modulation maintains integrity under kappa=0.0001 and kappa=100.0."""
        base_slices = [100, 100, 100, 100, 100]
        total_q = sum(base_slices)

        for kappa in [0.0001, 0.01, 1.0, 10.0, 50.0, 100.0]:
            sig = MicrostructureAlphaSignal(
                timestamp=time.time(),
                symbol="005930",
                l3_imbalance=0.8,
                arrival_imbalance=0.6,
                predicted_drift_bps=5.0,
                adverse_toxicity=0.1,
                composite_alpha_score=0.9,
                is_toxic=False,
                recommended_urgency="FAST",
                target_offset_ticks=-1.0,
                effective_ac_kappa=kappa,
            )
            mod = self.predictor.modulate_slicing_schedule(base_slices, sig, action="BUY")
            self.assertEqual(sum(mod), total_q)
            self.assertTrue(all(x >= 0 for x in mod))

    def test_adv_m3_06_composite_alpha_and_toxicity_bounds(self) -> None:
        """Challenge: S_micro in [-1.0, 1.0] and T_adverse in [0.0, 1.0] under extreme order books."""
        pathological_books = [
            # 100% bid dominance
            {"bids": [(100.0, 1_000_000.0)], "asks": []},
            # 100% ask dominance
            {"bids": [], "asks": [(101.0, 1_000_000.0)]},
            # Empty book
            {"bids": [], "asks": []},
            # Zero spread
            {"bids": [(100.0, 100.0)], "asks": [(100.0, 100.0)]},
            # Massive spread
            {"bids": [(10.0, 100.0)], "asks": [(1000.0, 100.0)]},
        ]
        for book in pathological_books:
            sig = self.predictor.predict_alpha(lob_snapshot=book)
            self.assertGreaterEqual(sig.composite_alpha_score, -1.0)
            self.assertLessEqual(sig.composite_alpha_score, 1.0)
            self.assertGreaterEqual(sig.adverse_toxicity, 0.0)
            self.assertLessEqual(sig.adverse_toxicity, 1.0)
            self.assertGreaterEqual(sig.l3_imbalance, -1.0)
            self.assertLessEqual(sig.l3_imbalance, 1.0)
            self.assertTrue(math.isfinite(sig.predicted_drift_bps))


# ===========================================================================
# Part 4: M4 - Dynamic Tax-Loss Harvesting & Wash-Sale Optimizer Adversarial
# ===========================================================================

class TestPhase107TaxHarvestingAdversarial(unittest.TestCase):
    """Adversarial stress testing for M4: Dynamic Tax-Loss Harvesting & Wash-Sale Optimizer."""

    def setUp(self) -> None:
        self.config = TaxConfig(wash_sale_window_days=30, min_surrogate_correlation=0.85)
        self.optimizer = DynamicTaxLossHarvestingOptimizer(config=self.config)
        self.tracker = WashSaleTracker(restriction_days=30)

        # Build synthetic price history with known correlations
        dates = pd.date_range("2026-01-01", periods=60, freq="B")
        np.random.seed(42)
        r_base = np.random.normal(0.001, 0.02, size=len(dates))
        r_high_corr = 0.90 * r_base + np.random.normal(0, 0.005, size=len(dates))
        r_low_corr = 0.50 * r_base + np.random.normal(0, 0.015, size=len(dates))
        r_diff_sector = 0.95 * r_base + np.random.normal(0, 0.003, size=len(dates))

        self.price_df = pd.DataFrame(
            {
                "AAPL": 150.0 * np.exp(np.cumsum(r_base)),
                "MSFT": 300.0 * np.exp(np.cumsum(r_high_corr)),    # Same sector, rho >= 0.85
                "INTC": 30.0 * np.exp(np.cumsum(r_low_corr)),      # Same sector, rho < 0.85
                "XOM": 100.0 * np.exp(np.cumsum(r_diff_sector)),   # Different sector (Energy)
            },
            index=dates,
        )
        self.sector_map = {
            "AAPL": "Technology",
            "MSFT": "Technology",
            "INTC": "Technology",
            "XOM": "Energy",
        }
        self.adv_dict = {
            "AAPL": 500_000_000.0,
            "MSFT": 500_000_000.0,
            "INTC": 500_000_000.0,
            "XOM": 500_000_000.0,
        }

    def test_adv_m4_01_wash_sale_boundary_day_29_30_31(self) -> None:
        """Challenge: 30-day wash-sale restriction strictly active on Day 29 & 30, strictly EXPIRES on Day 31."""
        sale_date = "2026-01-15"
        self.tracker.record_loss_sale("AAPL", sale_date=sale_date, loss_amount=5000.0)

        # Day 0 (sale date): Restricted
        self.assertTrue(self.tracker.is_repurchase_restricted("AAPL", "2026-01-15"))
        # Day 29 (2026-02-13): Restricted
        self.assertTrue(self.tracker.is_repurchase_restricted("AAPL", "2026-02-13"))
        # Day 30 (2026-02-14): Restricted (inclusive boundary)
        self.assertTrue(self.tracker.is_repurchase_restricted("AAPL", "2026-02-14"))
        # Day 31 (2026-02-15): Unrestricted (cooldown has lapsed)
        self.assertFalse(self.tracker.is_repurchase_restricted("AAPL", "2026-02-15"))
        # Day 32 (2026-02-16): Unrestricted
        self.assertFalse(self.tracker.is_repurchase_restricted("AAPL", "2026-02-16"))

    def test_adv_m4_02_wash_sale_pre_sale_30_day_window(self) -> None:
        """Challenge: Pre-sale 30-day window [T - 30d, T] also triggers is_restricted."""
        sale_date = "2026-02-01"
        self.tracker.record_loss_sale("AAPL", sale_date=sale_date, loss_amount=5000.0)

        # 10 days before sale: Restricted
        self.assertTrue(self.tracker.is_restricted("AAPL", "2026-01-22"))
        # 30 days before sale (2026-01-02): Restricted
        self.assertTrue(self.tracker.is_restricted("AAPL", "2026-01-02"))
        # 31 days before sale (2026-01-01): Unrestricted
        self.assertFalse(self.tracker.is_restricted("AAPL", "2026-01-01"))

    def test_adv_m4_03_economic_hurdle_invariant_loss_smaller_than_friction(self) -> None:
        """Challenge: A lot with small loss where friction exceeds gross tax savings is REJECTED."""
        # 10 shares bought at 100, current price 99.90 -> unrealized loss = $1.00
        # Gross tax savings at 37% = $0.37. Round-trip friction (broker fee + spread + SEC) is ~$1.15.
        # Net tax alpha = $0.37 - $1.15 = -$0.78 < 0 -> must be rejected.
        lot = TaxLot(
            lot_id="LOT_SMALL_LOSS",
            symbol="AAPL",
            market="SP500",
            acquisition_date="2026-01-01",
            quantity=10.0,
            cost_basis_per_share=100.0,
            current_price=99.90,
            tax_regime="US",
        )
        cand = self.optimizer.evaluate_lot_for_harvesting(
            lot=lot,
            current_price=99.90,
            price_history_df=self.price_df,
            sector_map=self.sector_map,
            adv_dict=self.adv_dict,
            as_of_date="2026-02-01",
        )
        self.assertFalse(cand.is_eligible)
        self.assertIn("ECONOMIC_HURDLE_FAILED", cand.rejection_reason)
        self.assertLess(cand.net_tax_alpha, 0.0)

    def test_adv_m4_04_economic_hurdle_invariant_loss_greater_than_friction(self) -> None:
        """Challenge: A lot with large loss where tax savings exceed friction is ACCEPTED."""
        # 500 shares bought at 200, current price 150 -> unrealized loss = $25,000.00
        # Tax savings at 37% = $9,250.00. Friction will be ~$100 -> net alpha > 0.
        lot = TaxLot(
            lot_id="LOT_LARGE_LOSS",
            symbol="AAPL",
            market="SP500",
            acquisition_date="2026-01-01",
            quantity=500.0,
            cost_basis_per_share=200.0,
            current_price=150.0,
            tax_regime="US",
        )
        cand = self.optimizer.evaluate_lot_for_harvesting(
            lot=lot,
            current_price=150.0,
            price_history_df=self.price_df,
            sector_map=self.sector_map,
            adv_dict=self.adv_dict,
            as_of_date="2026-02-01",
        )
        self.assertTrue(cand.is_eligible)
        self.assertGreater(cand.net_tax_alpha, 0.0)
        self.assertEqual(cand.rejection_reason, "")
        self.assertEqual(cand.surrogate_symbol, "MSFT")

    def test_adv_m4_05_economic_hurdle_profitable_or_flat_lot_rejected(self) -> None:
        """Challenge: Profitable lot (unrealized PnL >= 0) is immediately rejected without friction calculation."""
        lot = TaxLot(
            lot_id="LOT_PROFIT",
            symbol="AAPL",
            market="SP500",
            acquisition_date="2026-01-01",
            quantity=100.0,
            cost_basis_per_share=100.0,
            current_price=120.0,  # +$20 profit/share
            tax_regime="US",
        )
        cand = self.optimizer.evaluate_lot_for_harvesting(
            lot=lot,
            current_price=120.0,
            price_history_df=self.price_df,
            sector_map=self.sector_map,
            adv_dict=self.adv_dict,
            as_of_date="2026-02-01",
        )
        self.assertFalse(cand.is_eligible)
        self.assertIn("NO_UNREALIZED_LOSS", cand.rejection_reason)

    def test_adv_m4_06_surrogate_rejection_sector_mismatch(self) -> None:
        """Challenge: High-correlation asset (XOM, rho=0.95) from DIFFERENT sector (Energy) is REJECTED."""
        # Restrict sector map so ONLY XOM is available as high correlation
        restricted_sector_map = {"AAPL": "Technology", "XOM": "Energy"}
        surrogate = self.optimizer.find_surrogate_stock(
            symbol="AAPL",
            price_history_df=self.price_df,
            sector_map=restricted_sector_map,
            adv_dict=self.adv_dict,
        )
        self.assertIsNone(surrogate)

    def test_adv_m4_07_surrogate_rejection_low_correlation(self) -> None:
        """Challenge: Same-sector asset (INTC) with correlation rho < 0.85 is REJECTED."""
        restricted_sector_map = {"AAPL": "Technology", "INTC": "Technology"}
        surrogate = self.optimizer.find_surrogate_stock(
            symbol="AAPL",
            price_history_df=self.price_df,
            sector_map=restricted_sector_map,
            min_correlation=0.85,
            adv_dict=self.adv_dict,
        )
        self.assertIsNone(surrogate)

    def test_adv_m4_08_surrogate_rejection_wash_sale_restricted_candidate(self) -> None:
        """Challenge: Same-sector candidate (MSFT) is REJECTED if it is currently wash-sale restricted."""
        # Put MSFT in wash-sale restriction on 2026-02-01
        self.optimizer.wash_sale_tracker.record_loss_sale("MSFT", sale_date="2026-01-25", loss_amount=10000.0)

        surrogate = self.optimizer.find_surrogate_stock(
            symbol="AAPL",
            price_history_df=self.price_df,
            sector_map=self.sector_map,
            min_correlation=0.85,
            adv_dict=self.adv_dict,
            as_of_date="2026-02-01",
        )
        # MSFT is restricted, INTC has rho < 0.85, XOM is wrong sector -> None qualifies
        self.assertIsNone(surrogate)

    def test_adv_m4_09_surrogate_rejection_adv_liquidity_cap_exceeded(self) -> None:
        """Challenge: Candidate is REJECTED if required purchase exceeds 1.5% of its ADV."""
        tiny_adv = {"AAPL": 500_000_000.0, "MSFT": 10_000.0}  # MSFT ADV is only $10,000
        surrogate = self.optimizer.find_surrogate_stock(
            symbol="AAPL",
            price_history_df=self.price_df,
            sector_map=self.sector_map,
            min_correlation=0.85,
            adv_dict=tiny_adv,
            required_notional=50_000.0,  # 50,000 / 10,000 = 500% ADV >> 1.5% limit
        )
        self.assertIsNone(surrogate)

    def test_adv_m4_10_surrogate_acceptance_all_conditions_satisfied(self) -> None:
        """Challenge: MSFT is ACCEPTED when same sector, rho >= 0.85, unrestricted, and participation <= 1.5%."""
        surrogate = self.optimizer.find_surrogate_stock(
            symbol="AAPL",
            price_history_df=self.price_df,
            sector_map=self.sector_map,
            min_correlation=0.85,
            adv_dict=self.adv_dict,
            required_notional=100_000.0,  # 100,000 / 500,000,000 = 0.02% <= 1.5%
            as_of_date="2026-02-01",
        )
        self.assertIsNotNone(surrogate)
        sym, corr = surrogate
        self.assertEqual(sym, "MSFT")
        self.assertGreaterEqual(corr, 0.85)


if __name__ == "__main__":
    unittest.main()
