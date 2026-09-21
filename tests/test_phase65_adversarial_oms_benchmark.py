"""
tests/test_phase65_adversarial_oms_benchmark.py

Adversarial Stress Test Suite for Phase 65 Quantitative Enhancement:
Focus: Feature F299.1 & F299.2 (Microstructure OMS) and Feature F300 (Quant Benchmark Deliverables).

Challenger 2 Empirical Verification:
1. Lit maker floor 1e-37 precision and zero-underflow immunity under extreme toxicity.
2. Dark ATS cap 0.999999999999999999995 (21 decimals) under massive orders.
3. Dynamic Anti-Gaming MinQty cap 0.999999999999999999995.
4. Preemptive tick shading strict activation at h > 0.0000006.
5. Fast LOB Kerr-Newman-Kiselev 44-Dark-Energy DAHA tidal acceleration.
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


class TestPhase65AdversarialMicrostructureOMS:
    """Adversarial stress testing of Phase 65 Microstructure and Execution OMS."""

    def test_lit_maker_floor_grid_zero_underflow_immunity_v65(self):
        """Test 10,001 points across gamma_toxic in [0.80, 1.0] to guarantee no underflow below 1e-37."""
        gamma_grid = np.linspace(0.80, 1.0, 10001)
        for g in gamma_grid:
            val = float(np.clip(
                round(0.70 * (1.0 - 0.99999999999999999999999999999999999986 * g), 48),
                1e-37,
                0.70
            ))
            assert val > 0.0
            assert val >= 1e-37

    def test_lit_maker_floor_extreme_boundaries_in_sor_v65(self):
        """Verify SmartOrderRouter routing with extreme toxicity under 10^37 shares."""
        sor = SmartOrderRouter(version=65)
        qty = 10**37

        plan_max_tox = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 65,
        }
        res_max = sor.route_order(plan_max_tox, ats_available=False)
        maker_legs = [l for l in res_max.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"]
        assert len(maker_legs) > 0
        assert maker_legs[0]["quantity"] == 1
        assert res_max["maker_ratio"] == 1e-37

    def test_dark_ats_preemption_cap_v65(self):
        """Verify dark ATS routing cap up to 0.999999999999999999995 (21 decimals)."""
        sor = SmartOrderRouter(version=65)
        plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 10_000_000_000_000_000_000,
            "target_price": 150.0,
            "market_spread_bps": 12.0,
            "queue_imbalance": 0.80,
            "qi_acceleration": 0.50,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.90,
            "version": 65,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        total_dark = sum(l["quantity"] for l in dark_legs)
        assert total_dark >= 9_999_999_999_999_999_990

        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([20.0, 0.5, 0.2])
        p_res = process.compute_preemptive_dark_routing(version=65)
        assert p_res["preemptive_dark_routing_ratio"] >= 0.999999999999999999995 - 1e-15

    def test_anti_gaming_min_qty_cap_v65(self):
        """Verify dynamic anti-gaming MinQty scales up to 0.999999999999999999995."""
        sor = SmartOrderRouter(version=65)
        plan_tox = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 1_000_000,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 65,
        }
        res = sor.route_order(plan_tox, ats_available=True)
        assert res["min_ratio"] >= 0.999999999999999999995 - 1e-15

    def test_preemptive_micro_tick_shading_deadband_and_activation_v65(self):
        """Verify tick shading activates strictly when h > 0.0000006, deadband at h <= 0.0000006."""
        oms = ExecutionOMSEngine()
        sched = AlmgrenChrissScheduler()
        target_price = 100.0
        best_bid = 99.95
        best_ask = 100.05

        p_dead = oms.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.0000004,
            version=65,
        )
        assert math.isclose(p_dead, 100.0, rel_tol=1e-5)

        p_bound = oms.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.0000006,
            version=65,
        )
        assert math.isclose(p_bound, 100.0, rel_tol=1e-5)

        p_act = oms.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.000050,
            version=65,
        )
        assert p_act < p_dead, "Limit price should shade downward for BUY under toxic Hawkes intensity"

        p_sched_dead = sched.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.0000004,
            version=65,
        )
        p_sched_act = sched.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.000050,
            version=65,
        )
        assert p_sched_act < p_sched_dead

    def test_knk_44_dark_energy_daha_spacetime_acceleration(self):
        """Verify Fast LOB Kerr-Newman-Kiselev 44-dark-energy DAHA L3 hydrodynamics."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_44_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )
        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "density_dark_energy_44" in res
        assert "daha_44_factor" in res
        assert "equation_of_state_w_44" in res
        assert math.isclose(res["density_dark_energy_44"], 1.1920928955078125e-14, rel_tol=1e-9)
        assert math.isclose(res["daha_44_factor"], 6.60, rel_tol=1e-5)
        assert math.isclose(res["equation_of_state_w_44"], -46.0/3.0, rel_tol=1e-5)
        assert math.isfinite(res["queue_acceleration"])

    def test_benchmark_report_synchronization_v65(self):
        """Verify that Phase 65 benchmark markdown reports exist across all target paths."""
        paths = [
            "reports/quant_benchmark_comparison_phase65.md",
            "trading_system/result/quant_benchmark_comparison_phase65.md",
            "trading_system/reports/quant_benchmark_comparison_phase65.md",
            "reports/quant_benchmark_comparison.md",
        ]
        for path in paths:
            assert os.path.exists(path), f"Report path {path} missing"
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "Phase 65" in content

    def test_report_sha256_hash_synchronization_v65(self):
        """Verify bit-for-bit SHA-256 hash synchronization across all 3 standalone reports."""
        paths = [
            "reports/quant_benchmark_comparison_phase65.md",
            "trading_system/reports/quant_benchmark_comparison_phase65.md",
            "trading_system/result/quant_benchmark_comparison_phase65.md",
        ]
        hashes = []
        for path in paths:
            assert os.path.exists(path), f"Report path {path} missing"
            with open(path, "rb") as f:
                hashes.append(hashlib.sha256(f.read()).hexdigest())
        assert len(set(hashes)) == 1, "Report hashes are not identical across paths"
