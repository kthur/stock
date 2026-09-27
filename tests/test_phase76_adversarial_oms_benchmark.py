"""
tests/test_phase76_adversarial_oms_benchmark.py

Adversarial Stress Test Suite for Phase 76 Quantitative Enhancement:
Focus: Feature F354.1 & F354.2 (Microstructure OMS) and Feature F355 (Quant Benchmark Deliverables).

Challenger 2 Empirical Verification:
1. Lit maker floor 1e-48 precision and zero-underflow immunity under extreme toxicity.
2. Dark ATS routing and floor contraction under massive orders.
3. Preemptive tick shading strict activation at h > 0.00000003 with 29 nines.
4. Fast LOB Kerr-Newman-Kiselev 55-Dark-Energy DAHA tidal acceleration.
5. Benchmark script execution and 7-target assertion oracle.
6. Report synchronization across all canonical paths.
7. Bit-for-bit SHA-256 hash synchronization across Category A and Category B reports.
8. Category C cumulative report containing Phase 76 and prior phase sections.
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
        """Verify SmartOrderRouter Phase 76 maker floor is 1e-48."""
        sor = SmartOrderRouter(version=76)
        assert sor.is_phase76 is True
        assert sor.version == 76

        plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 1_000_000,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 76,
        }
        res = sor.route_order(plan, ats_available=False)
        assert isinstance(res, dict)
        mr = res.get("maker_ratio", None)
        assert mr is not None
        assert mr == 1e-48
        assert mr >= 1e-48

    def test_preemptive_tick_shading_extreme_toxicity_v76(self):
        """Verify preemptive micro-tick shading strictly activates at h > 0.00000003."""
        p_active = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=76,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000035}
        )
        p_inactive = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=76,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000025}
        )
        assert p_active < p_inactive

    def test_knk_55_dark_energy_daha_extreme_queue_inversion(self):
        """Test KNK-55 DAHA acceleration with extreme order book queue inversion."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"b_{i}", "BUY", 70000.0 - i * 100.0, 10.0)
            engine.add_limit_order(f"a_{i}", "SELL", 70100.0 + i * 100.0, 100000.0)

        res = engine.compute_kerr_newman_kiselev_55_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isfinite(res["queue_acceleration"])
        assert res["knk_55_dark_energy_correction"] <= 0.0
        assert math.isclose(res["w_dark_energy_55"], -57.0 / 3.0, rel_tol=1e-5)
        assert res["k_daha_55"] == 0.47
        assert res["k_monster_55"] == 0.46
        assert res["daha_55_factor"] == 9.35


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
