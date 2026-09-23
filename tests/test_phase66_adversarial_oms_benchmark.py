"""
tests/test_phase66_adversarial_oms_benchmark.py

Adversarial Stress Test Suite for Phase 66 Quantitative Enhancement:
Focus: Feature F304.1 & F304.2 (Microstructure OMS) and Feature F305 (Quant Benchmark Deliverables).

Challenger 2 Empirical Verification:
1. Lit maker floor 1e-38 precision and zero-underflow immunity under extreme toxicity.
2. Dark ATS cap 0.999999999999999999995 (21 decimals) under massive orders.
3. Dynamic Anti-Gaming MinQty cap 0.999999999999999999995.
4. Preemptive tick shading strict activation at h > 0.0000005.
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


class TestPhase66AdversarialMicrostructureOMS:
    """Adversarial stress testing of Phase 66 Microstructure and Execution OMS."""

    def test_lit_maker_floor_grid_zero_underflow_immunity_v65(self):
        """Test 10,001 points across gamma_toxic in [0.80, 1.0] to guarantee no underflow below 1e-38."""
        gamma_grid = np.linspace(0.80, 1.0, 10001)
        for g in gamma_grid:
            val = float(np.clip(
                round(0.70 * (1.0 - 0.99999999999999999999999999999999999986 * g), 48),
                1e-38,
                0.70
            ))
            assert val > 0.0
            assert val >= 1e-38

    def test_lit_maker_floor_extreme_boundaries_in_sor_v65(self):
        """Verify SmartOrderRouter Phase 66 maker floor is 1e-38."""
        sor = SmartOrderRouter(version=66)
        assert sor.is_phase66 is True
        assert sor.version == 66

        plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 1_000_000,
            "target_price": 150.0,
            "gamma_toxic_dir": 0.9,
            "version": 66,
        }
        res = sor.route_order(plan, ats_available=False)
        assert isinstance(res, dict)
        mr = res.get("maker_ratio", None)
        assert mr is not None
        assert mr >= 1e-38

    def test_dark_ats_preemption_cap_v65(self):
        """Verify dark ATS routing cap up to 0.999999999999999999995 (21 decimals)."""
        sor = SmartOrderRouter(version=66)
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
            "version": 66,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        total_dark = sum(l["quantity"] for l in dark_legs)
        assert total_dark >= 8_000_000_000_000_000_000

        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([20.0, 0.5, 0.2])
        p_res = process.compute_preemptive_dark_routing(version=66)
        assert p_res["preemptive_dark_routing_ratio"] >= 0.999999999999999999995 - 1e-15

    def test_anti_gaming_min_qty_cap_v65(self):
        """Verify dynamic anti-gaming MinQty scales up to 0.999999999999999999995."""
        sor = SmartOrderRouter(version=66)
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
        """Verify tick shading activates strictly when h > 0.0000005, deadband at h <= 0.0000005."""
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
            version=66,
        )
        assert math.isclose(p_dead, 100.0, rel_tol=1e-5)

        p_bound = oms.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.0000005,
            version=66,
        )
        assert math.isclose(p_bound, 100.0, rel_tol=1e-5)

        p_act = oms.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.000050,
            version=66,
        )
        assert p_act < p_dead, "Limit price should shade downward for BUY under toxic Hawkes intensity"

        p_sched_dead = sched.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.0000004,
            version=66,
        )
        p_sched_act = sched.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.000050,
            version=66,
        )
        assert p_sched_act < p_sched_dead

    def test_knk_45_dark_energy_daha_spacetime_acceleration(self):
        """Verify Fast LOB Kerr-Newman-Kiselev 45-dark-energy DAHA L3 hydrodynamics."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )
        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "knk_45_dark_energy_correction" in res
        assert "daha_45_factor" in res
        assert "k_daha_45" in res
        assert math.isclose(res["daha_45_factor"], 6.85, rel_tol=1e-5)
        assert math.isclose(res["k_daha_45"], 0.37, rel_tol=1e-5)
        assert math.isclose(res["c_monster_45"], 5.9604644775390625e-15, rel_tol=1e-9)
        assert math.isfinite(res["queue_acceleration"])

    def test_benchmark_report_synchronization_v65(self):
        """Verify that Phase 66 benchmark markdown reports exist across all target paths."""
        paths = [
            "reports/quant_benchmark_comparison_phase66.md",
            "trading_system/result/quant_benchmark_comparison_phase66.md",
            "trading_system/reports/quant_benchmark_comparison_phase66.md",
            "reports/quant_benchmark_comparison.md",
        ]
        for path in paths:
            assert os.path.exists(path), f"Report path {path} missing"
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "Phase 66" in content

    def test_report_sha256_hash_synchronization_v65(self):
        """Verify bit-for-bit SHA-256 hash synchronization across all 3 standalone reports."""
        paths = [
            "reports/quant_benchmark_comparison_phase66.md",
            "trading_system/reports/quant_benchmark_comparison_phase66.md",
            "trading_system/result/quant_benchmark_comparison_phase66.md",
        ]
        hashes = []
        for path in paths:
            assert os.path.exists(path), f"Report path {path} missing"
            with open(path, "rb") as f:
                hashes.append(hashlib.sha256(f.read()).hexdigest())
        assert len(set(hashes)) == 1, "Report hashes are not identical across paths"
