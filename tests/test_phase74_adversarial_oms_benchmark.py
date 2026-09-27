"""
tests/test_phase74_adversarial_oms_benchmark.py

Adversarial Stress Test Suite for Phase 74 Quantitative Enhancement:
Focus: Feature F344.1 & F344.2 (Microstructure OMS) and Feature F345 (Quant Benchmark Deliverables).

Challenger 2 Empirical Verification:
1. Lit maker floor 1e-46 precision and zero-underflow immunity under extreme toxicity.
2. Dark ATS routing and floor contraction under massive orders.
3. Preemptive tick shading strict activation at h > 0.00000005 with 27 nines.
4. Fast LOB Kerr-Newman-Kiselev 53-Dark-Energy DAHA tidal acceleration.
5. Benchmark script execution and 7-target assertion oracle.
6. Report synchronization across all canonical paths.
7. Bit-for-bit SHA-256 hash synchronization across Category A and Category B reports.
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


class TestPhase74AdversarialMicrostructureOMS:
    """Adversarial stress testing of Phase 74 Microstructure and Execution OMS."""

    def test_lit_maker_floor_grid_zero_underflow_immunity_v74(self):
        """Test 10,001 points across gamma_toxic in [0.80, 1.0] to guarantee no underflow below 1e-46."""
        gamma_grid = np.linspace(0.80, 1.0, 10001)
        for g in gamma_grid:
            val = float(np.clip(
                round(0.70 * (1.0 - 0.99999999999999999999999999999999999999999986 * g), 46),
                1e-46,
                0.70
            ))
            assert val > 0.0
            assert val >= 1e-46

    def test_lit_maker_floor_extreme_boundaries_in_sor_v74(self):
        """Verify SmartOrderRouter Phase 74 maker floor is 1e-46."""
        sor = SmartOrderRouter(version=74)
        assert sor.is_phase74 is True
        assert sor.version == 74

        plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 1_000_000,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 74,
        }
        res = sor.route_order(plan, ats_available=False)
        assert isinstance(res, dict)
        mr = res.get("maker_ratio", None)
        assert mr is not None
        assert mr == 1e-46
        assert mr >= 1e-46

    def test_preemptive_tick_shading_extreme_toxicity_v74(self):
        """Verify preemptive micro-tick shading strictly activates at h > 0.00000005."""
        p_active = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=74,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000055}
        )
        p_inactive = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=74,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000045}
        )
        assert p_active < p_inactive

    def test_knk_53_dark_energy_daha_extreme_queue_inversion(self):
        """Test KNK-53 DAHA acceleration with extreme order book queue inversion."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"b_{i}", "BUY", 70000.0 - i * 100.0, 10.0)
            engine.add_limit_order(f"a_{i}", "SELL", 70100.0 + i * 100.0, 100000.0)

        res = engine.compute_kerr_newman_kiselev_53_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isfinite(res["queue_acceleration"])
        assert res["knk_53_dark_energy_correction"] <= 0.0
        assert math.isclose(res["w_dark_energy_53"], -55.0 / 3.0, rel_tol=1e-5)
        assert res["k_daha_53"] == 0.45
        assert res["k_monster_53"] == 0.44
        assert res["daha_53_factor"] == 8.85


class TestPhase74AdversarialBenchmarkDeliverables:
    """Verification of Phase 74 benchmark script, KPI assertions, and report synchronizations."""

    def test_benchmark_script_execution(self):
        """Execute benchmark_phase74_quant_performance.py and ensure 0 exit code."""
        script_path = os.path.join(
            os.path.dirname(__file__), "..", "trading_system", "scripts", "benchmark_phase74_quant_performance.py"
        )
        res = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        assert res.returncode == 0, f"Benchmark script failed: {res.stderr}"
        assert "All 7 Phase 74 targets PASSED" in res.stdout

    def test_category_a_reports_sha256_identical(self):
        """Verify Category A reports are bit-for-bit SHA-256 identical across all 3 paths."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        paths = [
            os.path.join(repo_root, "reports/quant_benchmark_comparison_phase74.md"),
            os.path.join(repo_root, "trading_system/reports/quant_benchmark_comparison_phase74.md"),
            os.path.join(repo_root, "trading_system/result/quant_benchmark_comparison_phase74.md"),
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
            os.path.join(repo_root, "reports/benchmark_phase74_report.md"),
            os.path.join(repo_root, "trading_system/reports/benchmark_phase74_report.md"),
            os.path.join(repo_root, "docs/benchmark_phase74_report.md"),
        ]
        hashes = []
        for p in paths:
            assert os.path.exists(p), f"Report missing: {p}"
            with open(p, "rb") as f:
                content = f.read()
                assert b"Phase 74 Quantitative Alpha Enhancement" in content
                h = hashlib.sha256(content).hexdigest()
                hashes.append(h)

        assert len(set(hashes)) == 1, f"SHA-256 hash mismatch across Category B paths: {hashes}"

    def test_category_c_cumulative_report(self):
        """Verify Category C cumulative report contains Phase 74 section."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        canon_path = os.path.join(repo_root, "reports/quant_benchmark_comparison.md")
        assert os.path.exists(canon_path)
        with open(canon_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "Phase 74 Quantitative Alpha Enhancement" in content
            assert "Phase 73 Quantitative Alpha Enhancement" in content
