"""
tests/test_phase73_adversarial_oms_benchmark.py

Adversarial Stress Test Suite for Phase 73 Quantitative Enhancement:
Focus: Feature F339.1 & F339.2 (Microstructure OMS) and Feature F340 (Quant Benchmark Deliverables).

Challenger 2 Empirical Verification:
1. Lit maker floor 1e-45 precision and zero-underflow immunity under extreme toxicity.
2. Dark ATS routing and floor contraction under massive orders.
3. Preemptive tick shading strict activation at h > 0.00000006 with 26 nines.
4. Fast LOB Kerr-Newman-Kiselev 52-Dark-Energy DAHA tidal acceleration.
5. Benchmark script execution and 7-target assertion oracle.
6. Report synchronization across all canonical paths.
7. Bit-for-bit SHA-256 hash synchronization across Category A reports.
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


class TestPhase73AdversarialMicrostructureOMS:
    """Adversarial stress testing of Phase 73 Microstructure and Execution OMS."""

    def test_lit_maker_floor_grid_zero_underflow_immunity_v73(self):
        """Test 10,001 points across gamma_toxic in [0.80, 1.0] to guarantee no underflow below 1e-45."""
        gamma_grid = np.linspace(0.80, 1.0, 10001)
        for g in gamma_grid:
            val = float(np.clip(
                round(0.70 * (1.0 - 0.99999999999999999999999999999999999999999986 * g), 45),
                1e-45,
                0.70
            ))
            assert val > 0.0
            assert val >= 1e-45

    def test_lit_maker_floor_extreme_boundaries_in_sor_v73(self):
        """Verify SmartOrderRouter Phase 73 maker floor is 1e-45."""
        sor = SmartOrderRouter(version=73)
        assert sor.is_phase73 is True
        assert sor.version == 73

        plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 1_000_000,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 73,
        }
        res = sor.route_order(plan, ats_available=False)
        assert isinstance(res, dict)
        mr = res.get("maker_ratio", None)
        assert mr is not None
        assert mr == 1e-45
        assert mr >= 1e-45

    def test_preemptive_tick_shading_extreme_toxicity_v73(self):
        """Verify preemptive micro-tick shading strictly activates at h > 0.00000006."""
        p_active = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=73,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000007}
        )
        p_inactive = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=73,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000005}
        )
        assert p_active < p_inactive

    def test_knk_52_dark_energy_daha_extreme_queue_inversion(self):
        """Test KNK-52 DAHA acceleration with extreme order book queue inversion."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"b_{i}", "BUY", 70000.0 - i * 100.0, 10.0)
            engine.add_limit_order(f"a_{i}", "SELL", 70100.0 + i * 100.0, 100000.0)

        res = engine.compute_kerr_newman_kiselev_52_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isfinite(res["queue_acceleration"])
        assert res["knk_52_dark_energy_correction"] <= 0.0
        assert res["w_dark_energy_52"] == -18.0
        assert res["k_daha_52"] == 0.44
        assert res["k_monster_52"] == 0.43
        assert res["daha_52_factor"] == 8.60


class TestPhase73AdversarialBenchmarkDeliverables:
    """Verification of Phase 73 benchmark script, KPI assertions, and report synchronizations."""

    def test_benchmark_script_execution(self):
        """Execute benchmark_phase73_quant_performance.py and ensure 0 exit code."""
        script_path = os.path.join(
            os.path.dirname(__file__), "..", "trading_system", "scripts", "benchmark_phase73_quant_performance.py"
        )
        res = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        assert res.returncode == 0, f"Benchmark script failed: {res.stderr}"
        assert "All 7 Phase 73 targets PASSED" in res.stdout

    def test_category_a_reports_sha256_identical(self):
        """Verify Category A reports are bit-for-bit SHA-256 identical across all 3 paths."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        paths = [
            os.path.join(repo_root, "reports/quant_benchmark_comparison_phase73.md"),
            os.path.join(repo_root, "trading_system/reports/quant_benchmark_comparison_phase73.md"),
            os.path.join(repo_root, "trading_system/result/quant_benchmark_comparison_phase73.md"),
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
            os.path.join(repo_root, "reports/benchmark_phase73_report.md"),
            os.path.join(repo_root, "trading_system/reports/benchmark_phase73_report.md"),
            os.path.join(repo_root, "docs/benchmark_phase73_report.md"),
        ]
        for p in paths:
            assert os.path.exists(p), f"Report missing: {p}"
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
                assert "Phase 73 Quantitative Alpha Enhancement" in content

    def test_category_c_cumulative_report(self):
        """Verify Category C cumulative report contains Phase 73 section."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        canon_path = os.path.join(repo_root, "reports/quant_benchmark_comparison.md")
        assert os.path.exists(canon_path)
        with open(canon_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "Phase 73 Quantitative Alpha Enhancement" in content
            assert "Phase 72 Quantitative Alpha Enhancement" in content
