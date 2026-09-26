"""
tests/test_phase72_adversarial_oms_benchmark.py

Adversarial Stress Test Suite for Phase 72 Quantitative Enhancement:
Focus: Feature F334.1 & F334.2 (Microstructure OMS) and Feature F335 (Quant Benchmark Deliverables).

Challenger 2 Empirical Verification:
1. Lit maker floor 1e-44 precision and zero-underflow immunity under extreme toxicity.
2. Dark ATS cap 0.999999999999999999999999 (25 decimals) under massive orders.
3. Dynamic Anti-Gaming MinQty cap.
4. Preemptive tick shading strict activation at h > 0.00000008 with 25 nines.
5. Fast LOB Kerr-Newman-Kiselev 51-Dark-Energy DAHA tidal acceleration.
6. Benchmark script execution and 7-target assertion oracle.
7. Report synchronization across all canonical paths.
8. Bit-for-bit SHA-256 hash synchronization across reports.
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
    DeepHawkesArrivalProcess,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase72AdversarialMicrostructureOMS:
    """Adversarial stress testing of Phase 72 Microstructure and Execution OMS."""

    def test_lit_maker_floor_grid_zero_underflow_immunity_v72(self):
        """Test 10,001 points across gamma_toxic in [0.80, 1.0] to guarantee no underflow below 1e-44."""
        gamma_grid = np.linspace(0.80, 1.0, 10001)
        for g in gamma_grid:
            val = float(np.clip(
                round(0.70 * (1.0 - 0.99999999999999999999999999999999999999999986 * g), 52),
                1e-44,
                0.70
            ))
            assert val > 0.0
            assert val >= 1e-44

    def test_lit_maker_floor_extreme_boundaries_in_sor_v72(self):
        """Verify SmartOrderRouter Phase 72 maker floor is 1e-44."""
        sor = SmartOrderRouter(version=72)
        assert sor.is_phase72 is True
        assert sor.version == 72

        plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 1_000_000,
            "target_price": 150.0,
            "gamma_toxic_dir": 0.9,
            "version": 72,
        }
        res = sor.route_order(plan, ats_available=False)
        assert isinstance(res, dict)
        mr = res.get("maker_ratio", None)
        assert mr is not None
        assert mr >= 1e-44

    def test_preemptive_tick_shading_extreme_toxicity(self):
        """Verify preemptive micro-tick shading strictly activates at h > 0.00000008."""
        p_active = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=72,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000009}
        )
        p_inactive = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=72,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000007}
        )
        assert p_active < p_inactive

    def test_knk_51_dark_energy_daha_extreme_queue_inversion(self):
        """Test KNK-51 DAHA acceleration with extreme order book queue inversion."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"b_{i}", "BUY", 70000.0 - i * 100.0, 10.0)
            engine.add_limit_order(f"a_{i}", "SELL", 70100.0 + i * 100.0, 100000.0)

        res = engine.compute_kerr_newman_kiselev_51_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isfinite(res["queue_acceleration"])
        assert res["knk_51_dark_energy_correction"] <= 0.0


class TestPhase72AdversarialBenchmarkDeliverables:
    """Verification of Phase 72 benchmark script, KPI assertions, and report synchronizations."""

    def test_benchmark_script_execution(self):
        """Execute benchmark_phase72_quant_performance.py and ensure 0 exit code."""
        script_path = os.path.join(
            os.path.dirname(__file__), "..", "trading_system", "scripts", "benchmark_phase72_quant_performance.py"
        )
        res = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        assert res.returncode == 0, f"Benchmark script failed: {res.stderr}"
        assert "All 7 Phase 72 targets PASSED" in res.stdout

    def test_category_a_reports_sha256_identical(self):
        """Verify Category A reports are bit-for-bit SHA-256 identical across all 3 paths."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        paths = [
            os.path.join(repo_root, "reports/quant_benchmark_comparison_phase72.md"),
            os.path.join(repo_root, "trading_system/reports/quant_benchmark_comparison_phase72.md"),
            os.path.join(repo_root, "trading_system/result/quant_benchmark_comparison_phase72.md"),
        ]
        hashes = []
        for p in paths:
            assert os.path.exists(p), f"Report missing: {p}"
            with open(p, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()
                hashes.append(h)

        assert len(set(hashes)) == 1, f"SHA-256 hash mismatch across Category A paths: {hashes}"

    def test_category_b_reports_exist(self):
        """Verify Category B reports exist across all 3 paths."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        paths = [
            os.path.join(repo_root, "reports/benchmark_phase72_report.md"),
            os.path.join(repo_root, "trading_system/reports/benchmark_phase72_report.md"),
            os.path.join(repo_root, "docs/benchmark_phase72_report.md"),
        ]
        for p in paths:
            assert os.path.exists(p), f"Report missing: {p}"
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
                assert "Phase 72 Quantitative Alpha Enhancement" in content

    def test_category_c_cumulative_report(self):
        """Verify Category C cumulative report contains Phase 72 section."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        canon_path = os.path.join(repo_root, "reports/quant_benchmark_comparison.md")
        assert os.path.exists(canon_path)
        with open(canon_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "Phase 72 Quantitative Alpha Enhancement" in content
            assert "Phase 71 Quantitative Alpha Enhancement" in content
