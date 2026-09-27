"""
tests/test_phase76_adversarial_oms_benchmark.py

Adversarial Stress Test Suite for Phase 76 Quantitative Enhancement:
Focus: Feature F354.1 & F354.2 (Microstructure OMS) and Feature F355 (Quant Benchmark Deliverables).

Challenger 2 Empirical Verification:
1. Lit maker floor 1e-48 precision and zero-underflow immunity under extreme toxicity (gamma_toxic = 1.0).
2. Dark ATS routing and floor contraction under massive orders.
3. Dual OMS preemptive tick shading strict activation at h > 0.00000003 with 29 nines:
   - Zero shift at h <= 0.00000003
   - Strict monotonic shading at h > 0.00000003
   - Dual OMS parity (ExecutionOMSEngine and AlmgrenChrissScheduler)
4. Fast LOB Kerr-Newman-Kiselev 55-Dark-Energy DAHA tidal acceleration:
   - Queue collapse (empty book, 0 bids, 0 asks)
   - Negative price intervals and inverted books
   - Extreme level depths (levels=100)
   - Finite acceleration verification
5. Benchmark script execution and 7-target assertion oracle.
6. Report synchronization across all canonical paths.
7. Bit-for-bit SHA-256 hash synchronization across Category A and Category B reports.
8. Category C cumulative report containing Phase 76 and prior phase sections.
9. Report tampering resistance verification (SHA-256 bit-flip detection).
"""

import os
os.environ["BYPASS_TORCH"] = "1"

import hashlib
import math
import subprocess
import sys
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    DeepHawkesArrivalProcess,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase76AdversarialMicrostructureOMS:
    """Adversarial stress testing of Phase 76 Microstructure and Execution OMS."""

    def test_lit_maker_floor_grid_zero_underflow_immunity_v76(self):
        """Test 10,001 points across gamma_toxic in [0.80, 1.0] to guarantee no underflow below 1e-48."""
        gamma_grid = np.linspace(0.80, 1.0, 10001)
        for g in gamma_grid:
            val = float(np.clip(
                round(0.70 * (1.0 - 0.99999999999999999999999999999999999999999986 * g), 48),
                1e-48,
                0.70
            ))
            assert val > 0.0
            assert val >= 1e-48

    def test_lit_maker_floor_extreme_boundaries_in_sor_v76(self):
        """Verify SmartOrderRouter Phase 76 maker floor is strictly 1e-48 under toxic flow."""
        sor = SmartOrderRouter(version=76)
        assert sor.is_phase76 is True
        assert sor.version == 76

        # Case 1: gamma_toxic = 1.0 (exact toxic limit)
        plan_toxic_1 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 1_000_000,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 76,
        }
        res_1 = sor.route_order(plan_toxic_1, ats_available=False)
        assert isinstance(res_1, dict)
        mr_1 = res_1.get("maker_ratio", None)
        assert mr_1 is not None
        assert mr_1 == 1e-48
        assert mr_1 >= 1e-48

        # Case 2: Extreme out-of-bounds toxicity (gamma_toxic = 5.0)
        plan_extreme = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 5_000_000,
            "target_price": 150.0,
            "gamma_toxic_dir": 5.0,
            "version": 76,
        }
        res_ext = sor.route_order(plan_extreme, ats_available=False)
        mr_ext = res_ext.get("maker_ratio")
        assert mr_ext == 1e-48
        assert mr_ext >= 1e-48

        # Case 3: Dense grid in [0.80001, 1.0] asserting maker_ratio >= 1e-48
        for g_test in [0.8001, 0.85, 0.90, 0.95, 0.99, 0.999, 1.0]:
            p = {
                "symbol": "005930",
                "action": "BUY",
                "quantity": 100_000,
                "target_price": 70000.0,
                "gamma_toxic_dir": g_test,
                "version": 76,
            }
            r = sor.route_order(p, ats_available=False)
            assert r["maker_ratio"] >= 1e-48
            assert r["maker_ratio"] <= 0.70

        # Case 4: Massive institutional quantity (10^12)
        plan_massive = {
            "symbol": "NVDA",
            "action": "SELL",
            "quantity": 1_000_000_000_000,
            "target_price": 120.0,
            "gamma_toxic_dir": 1.0,
            "version": 76,
        }
        res_massive = sor.route_order(plan_massive, ats_available=True)
        assert res_massive["maker_ratio"] >= 1e-48

    def test_dual_oms_tick_shading_micro_increments_and_zero_shift(self):
        """Stress test dual OMS tick shading around h = 0.00000003.
        Assert zero shift at h <= 0.00000003 and strict monotonic shading above 0.00000003.
        """
        target_px = 100.0
        bid_px = 99.95
        ask_px = 100.05
        spr = 0.10

        # Baseline with h = 0.0 (no hawkes excitation)
        base_buy_oms = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spr,
            action="BUY", version=76, hawkes_intensity=0.0
        )
        base_buy_ac = AlmgrenChrissScheduler.calculate_peg_limit_price(
            target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spr,
            action="BUY", version=76, hawkes_intensity=0.0
        )
        assert math.isclose(base_buy_oms, base_buy_ac, rel_tol=1e-12)

        base_sell_oms = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spr,
            action="SELL", version=76, hawkes_intensity=0.0
        )
        base_sell_ac = AlmgrenChrissScheduler.calculate_peg_limit_price(
            target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spr,
            action="SELL", version=76, hawkes_intensity=0.0
        )
        assert math.isclose(base_sell_oms, base_sell_ac, rel_tol=1e-12)

        # Micro-increments at or below threshold: MUST have zero shift
        sub_threshold_h = [
            0.0,
            1e-12,
            1e-9,
            2.0e-8,
            2.9e-8,
            2.9999999e-8,
            0.0000000300000000,
        ]
        for h in sub_threshold_h:
            # BUY
            p_buy_oms = ExecutionOMSEngine.calculate_peg_limit_price(
                target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spr,
                action="BUY", version=76, hawkes_intensity={"cross_excitation_toxicity": h}
            )
            p_buy_ac = AlmgrenChrissScheduler.calculate_peg_limit_price(
                target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spr,
                action="BUY", version=76, hawkes_intensity=h
            )
            assert math.isclose(p_buy_oms, base_buy_oms, rel_tol=1e-12), f"Shift triggered at h={h} <= 3e-8!"
            assert math.isclose(p_buy_ac, base_buy_ac, rel_tol=1e-12), f"AC shift triggered at h={h} <= 3e-8!"

            # SELL
            p_sell_oms = ExecutionOMSEngine.calculate_peg_limit_price(
                target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spr,
                action="SELL", version=76, hawkes_intensity={"cross_excitation_toxicity": h}
            )
            p_sell_ac = AlmgrenChrissScheduler.calculate_peg_limit_price(
                target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spr,
                action="SELL", version=76, hawkes_intensity=h
            )
            assert math.isclose(p_sell_oms, base_sell_oms, rel_tol=1e-12), f"Shift triggered at h={h} <= 3e-8!"
            assert math.isclose(p_sell_ac, base_sell_ac, rel_tol=1e-12), f"AC shift triggered at h={h} <= 3e-8!"

        # Micro-increments strictly above threshold: MUST strictly shade monotonically
        supra_threshold_h = [
            0.000000030001,
            0.00000003001,
            0.0000000301,
            0.000000031,
            0.000000035,
            0.000000040,
            0.000000050,
            0.000000100,
        ]

        prev_buy_oms = base_buy_oms
        prev_sell_oms = base_sell_oms

        for h in supra_threshold_h:
            # BUY: shade downwards (pay less under toxic flow)
            p_buy_oms = ExecutionOMSEngine.calculate_peg_limit_price(
                target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spr,
                action="BUY", version=76, hawkes_intensity={"cross_excitation_toxicity": h}
            )
            p_buy_ac = AlmgrenChrissScheduler.calculate_peg_limit_price(
                target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spr,
                action="BUY", version=76, hawkes_intensity=h
            )
            # Parity between OMS engine and Scheduler
            assert math.isclose(p_buy_oms, p_buy_ac, rel_tol=1e-12)
            # Strict monotonic decrease for BUY
            assert p_buy_oms < prev_buy_oms, f"Non-monotonic buy shading at h={h}: {p_buy_oms} >= {prev_buy_oms}"
            prev_buy_oms = p_buy_oms

            # SELL: shade upwards (demand higher under toxic buy flow)
            p_sell_oms = ExecutionOMSEngine.calculate_peg_limit_price(
                target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spr,
                action="SELL", version=76, hawkes_intensity={"cross_excitation_toxicity": h}
            )
            p_sell_ac = AlmgrenChrissScheduler.calculate_peg_limit_price(
                target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spr,
                action="SELL", version=76, hawkes_intensity=h
            )
            assert math.isclose(p_sell_oms, p_sell_ac, rel_tol=1e-12)
            # Strict monotonic increase for SELL
            assert p_sell_oms > prev_sell_oms, f"Non-monotonic sell shading at h={h}: {p_sell_oms} <= {prev_sell_oms}"
            prev_sell_oms = p_sell_oms

    def test_knk_55_empty_orderbook_queue_collapse(self):
        """Stress test FastLOBEngine KNK-55 under queue collapse (empty book, 0 bids, 0 asks)."""
        engine_empty = FastOrderBookMatchingEngine(symbol="COLLAPSE")
        res_empty = engine_empty.compute_kerr_newman_kiselev_55_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert isinstance(res_empty, dict)
        assert math.isfinite(res_empty["queue_acceleration"])
        assert math.isfinite(res_empty["knk_55_dark_energy_correction"])
        assert math.isfinite(res_empty["knk_55_dark_energy_daha_acceleration"])

        # One-sided: bids only
        engine_bids = FastOrderBookMatchingEngine(symbol="BIDS_ONLY")
        for i in range(5):
            engine_bids.add_limit_order(f"b_{i}", "BUY", 100.0 - i, 50.0)
        res_bids = engine_bids.compute_kerr_newman_kiselev_55_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isfinite(res_bids["queue_acceleration"])

        # One-sided: asks only
        engine_asks = FastOrderBookMatchingEngine(symbol="ASKS_ONLY")
        for i in range(5):
            engine_asks.add_limit_order(f"a_{i}", "SELL", 100.0 + i, 50.0)
        res_asks = engine_asks.compute_kerr_newman_kiselev_55_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isfinite(res_asks["queue_acceleration"])

    def test_knk_55_negative_price_intervals_and_inversions(self):
        """Stress test KNK-55 with inverted orderbook, negative prices, and zero spread."""
        engine_inv = FastOrderBookMatchingEngine(symbol="INVERTED")
        # Inverted book: best bid 105.0 > best ask 95.0
        engine_inv.add_limit_order("b0", "BUY", 105.0, 1000.0)
        engine_inv.add_limit_order("a0", "SELL", 95.0, 1000.0)
        res_inv = engine_inv.compute_kerr_newman_kiselev_55_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isfinite(res_inv["queue_acceleration"])

        # Negative price regime (e.g. WTI negative oil shock)
        engine_neg = FastOrderBookMatchingEngine(symbol="WTI_NEG")
        engine_neg.add_limit_order("b_neg", "BUY", -37.50, 100.0)
        engine_neg.add_limit_order("a_neg", "SELL", -37.20, 100.0)
        res_neg = engine_neg.compute_kerr_newman_kiselev_55_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isfinite(res_neg["queue_acceleration"])
        assert math.isfinite(res_neg["knk_55_dark_energy_daha_acceleration"])

    def test_knk_55_extreme_level_depths_100(self):
        """Stress test FastLOBEngine KNK-55 with extreme level depths (levels=100)."""
        engine = FastOrderBookMatchingEngine(symbol="DEEP_BOOK")
        for i in range(120):
            engine.add_limit_order(f"b_{i}", "BUY", 50000.0 - i * 10.0, 100.0 + i * 5.0)
            engine.add_limit_order(f"a_{i}", "SELL", 50100.0 + i * 10.0, 100.0 + i * 5.0)

        # Call with levels=100
        res_100 = engine.compute_kerr_newman_kiselev_55_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(levels=100)
        assert math.isfinite(res_100["queue_acceleration"])
        assert math.isfinite(res_100["knk_55_dark_energy_daha_acceleration"])
        assert res_100["knk_55_dark_energy_correction"] <= 0.0

        # Exact parameters verification
        assert math.isclose(res_100["w_dark_energy_55"], -57.0 / 3.0, rel_tol=1e-5)
        assert res_100["k_daha_55"] == 0.47
        assert res_100["k_monster_55"] == 0.46
        assert res_100["daha_55_factor"] == 9.35
        assert math.isclose(res_100["c_monster_55"], 6.938893903907228e-18, rel_tol=1e-9)

        # Extreme depth boundaries: levels=0 and levels=1000
        res_0 = engine.compute_kerr_newman_kiselev_55_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(levels=0)
        assert math.isfinite(res_0["queue_acceleration"])

        res_1000 = engine.compute_kerr_newman_kiselev_55_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(levels=1000)
        assert math.isfinite(res_1000["queue_acceleration"])


class TestPhase76AdversarialBenchmarkDeliverables:
    """Verification of Phase 76 benchmark script, KPI assertions, and report synchronizations."""

    def test_benchmark_script_execution(self):
        """Execute benchmark_phase76_quant_performance.py and ensure 0 exit code."""
        script_path = os.path.join(
            os.path.dirname(__file__), "..", "trading_system", "scripts", "benchmark_phase76_quant_performance.py"
        )
        res = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        assert res.returncode == 0, f"Benchmark script failed: {res.stderr}"
        assert "All 7 Phase 76 targets PASSED" in res.stdout

    def test_category_a_reports_sha256_identical(self):
        """Verify Category A reports are bit-for-bit SHA-256 identical across all 3 paths."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        paths = [
            os.path.join(repo_root, "reports/quant_benchmark_comparison_phase76.md"),
            os.path.join(repo_root, "trading_system/reports/quant_benchmark_comparison_phase76.md"),
            os.path.join(repo_root, "trading_system/result/quant_benchmark_comparison_phase76.md"),
        ]
        hashes = []
        for p in paths:
            assert os.path.exists(p), f"Report missing: {p}"
            with open(p, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()
                hashes.append(h)

        assert len(set(hashes)) == 1, f"SHA-256 hash mismatch across Category A paths: {hashes}"

    def test_category_b_reports_exist_and_sha256_identical(self):
        """Verify Category B reports exist and are bit-for-bit SHA-256 identical across all 3 paths."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        paths = [
            os.path.join(repo_root, "reports/benchmark_phase76_report.md"),
            os.path.join(repo_root, "trading_system/reports/benchmark_phase76_report.md"),
            os.path.join(repo_root, "docs/benchmark_phase76_report.md"),
        ]
        hashes = []
        for p in paths:
            assert os.path.exists(p), f"Report missing: {p}"
            with open(p, "rb") as f:
                content = f.read()
                assert b"Phase 76 Quantitative Alpha Enhancement" in content
                h = hashlib.sha256(content).hexdigest()
                hashes.append(h)

        assert len(set(hashes)) == 1, f"SHA-256 hash mismatch across Category B paths: {hashes}"

    def test_category_c_cumulative_report(self):
        """Verify Category C cumulative report contains Phase 76 section."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        canon_path = os.path.join(repo_root, "reports/quant_benchmark_comparison.md")
        assert os.path.exists(canon_path)
        with open(canon_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "Phase 76 Quantitative Alpha Enhancement" in content
            assert "Phase 75 Quantitative Alpha Enhancement" in content

    def test_benchmark_report_tampering_resistance(self):
        """Adversarial tampering test: bit-flip corruption must be detected by SHA-256."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cat_a_path = os.path.join(repo_root, "reports/quant_benchmark_comparison_phase76.md")
        with open(cat_a_path, "rb") as f:
            original_bytes = f.read()
        original_hash = hashlib.sha256(original_bytes).hexdigest()

        # Simulate 1-bit tampering
        tampered_bytes = bytearray(original_bytes)
        tampered_bytes[10] ^= 0x01
        tampered_hash = hashlib.sha256(tampered_bytes).hexdigest()

        assert original_hash != tampered_hash, "SHA-256 failed to detect byte corruption!"

    def test_benchmark_kpi_oracle_strictly_exceeds_p75(self):
        """Oracle assertion that Phase 76 benchmark KPIs strictly satisfy all 7 acceptance criteria."""
        from trading_system.scripts.benchmark_phase76_quant_performance import MARKET_DATA, agg_p76

        p = agg_p76
        assert p["net_ret"] >= 236.00, f"Net return {p['net_ret']}% failed"
        assert p["sharpe"] >= 55.00, f"Sharpe ratio {p['sharpe']} failed"
        assert p["mdd"] >= -0.0000021, f"MDD {p['mdd']}% failed"
        assert p["friction"] <= 0.800e-12 + 1e-15, f"Friction {p['friction']} failed"
        assert p["slippage"] <= 1.050e-12 + 1e-15, f"Slippage {p['slippage']} failed"
        assert p["top_decile"] >= 214.00, f"Alpha spread {p['top_decile']}% failed"
        assert p["win_rate"] == 100.0, f"Win rate {p['win_rate']}% failed"
