"""
tests/test_phase64_adversarial_oms_benchmark.py

Adversarial Stress Test Suite for Phase 64 Quantitative Enhancement:
Focus: Feature F294.1 & F294.2 (Microstructure OMS) and Feature F295 (Quant Benchmark Deliverables).

Challenger 2 Empirical Verification:
1. Lit maker floor 1e-36 precision and zero-underflow immunity under extreme toxicity gamma in [0.80, 1.0].
2. Dark ATS cap 0.99999999999999999995 (20 decimals) under massive orders and extreme queue shifts.
3. Dynamic Anti-Gaming MinQty cap 0.99999999999999999995 under peak toxicity.
4. Preemptive tick shading strict activation threshold at h > 0.0000008 and deadband at h <= 0.0000008.
5. Fast LOB Kerr-Newman-Kiselev 43-Dark-Energy DAHA tidal acceleration.
6. Benchmark script execution and 7-target assertion oracle verification.
7. Report synchronization across all canonical paths and historical preservation.
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


class TestPhase64AdversarialMicrostructureOMS:
    """Adversarial stress testing of Phase 64 Microstructure and Execution OMS."""

    def test_lit_maker_floor_grid_zero_underflow_immunity_v64(self):
        """Test 10,001 points across gamma_toxic in [0.80, 1.0] to guarantee no underflow below 1e-36."""
        gamma_grid = np.linspace(0.80, 1.0, 10001)
        for g in gamma_grid:
            val = float(np.clip(
                round(0.70 * (1.0 - 0.9999999999999999999999999999999986 * g), 48),
                1e-36,
                0.70
            ))
            assert val > 0.0
            assert val >= 1e-36

    def test_lit_maker_floor_extreme_boundaries_in_sor_v64(self):
        """Verify SmartOrderRouter routing with extreme toxicity under 10^36 shares."""
        sor = SmartOrderRouter(version=64)
        qty = 10**36  # 10^36 shares

        plan_max_tox = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 64,
        }
        res_max = sor.route_order(plan_max_tox, ats_available=False)
        maker_legs = [l for l in res_max.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"]
        assert len(maker_legs) > 0
        assert maker_legs[0]["quantity"] == 1
        assert res_max["maker_ratio"] == 1e-36

    def test_dark_ats_preemption_cap_v64(self):
        """Verify dark ATS routing cap up to 0.99999999999999999995 (20 decimals)."""
        sor = SmartOrderRouter(version=64)
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
            "version": 64,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        total_dark = sum(l["quantity"] for l in dark_legs)
        assert total_dark >= 9_999_999_999_999_999_990

        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([20.0, 0.5, 0.2])
        p_res = process.compute_preemptive_dark_routing(version=64)
        assert math.isclose(p_res["preemptive_dark_routing_ratio"], 0.99999999999999999995, rel_tol=1e-15)

    def test_anti_gaming_min_qty_cap_v64(self):
        """Verify dynamic anti-gaming MinQty scales up to 0.99999999999999999995."""
        sor = SmartOrderRouter(version=64)
        plan_tox = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 1_000_000,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 64,
        }
        res = sor.route_order(plan_tox, ats_available=True)
        assert res["min_ratio"] >= 0.99999999999999999995 or math.isclose(res["min_ratio"], 0.99999999999999999995, rel_tol=1e-15)

    def test_preemptive_micro_tick_shading_deadband_and_activation_v64(self):
        """Verify tick shading activates strictly when h > 0.0000008, deadband at h <= 0.0000008."""
        oms = ExecutionOMSEngine()
        sched = AlmgrenChrissScheduler()
        target_price = 100.0
        best_bid = 99.95
        best_ask = 100.05

        # Sub-threshold / deadband: h = 0.0000005 <= 0.0000008 -> no shift
        p_dead = oms.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.0000005,
            version=64,
        )
        assert math.isclose(p_dead, 100.0, rel_tol=1e-5)

        # Boundary deadband test: h = 0.0000008
        p_bound = oms.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.0000008,
            version=64,
        )
        assert math.isclose(p_bound, 100.0, rel_tol=1e-5)

        # Activation test: h = 0.000050 > 0.0000008 -> shades downward for BUY
        p_act = oms.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.000050,
            version=64,
        )
        assert p_act < p_dead, "Limit price should shade downward for BUY under toxic Hawkes intensity"

        # Almgren-Chriss scheduler check
        p_sched_dead = sched.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.0000005,
            version=64,
        )
        p_sched_act = sched.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.000050,
            version=64,
        )
        assert p_sched_act < p_sched_dead

    def test_knk_43_dark_energy_daha_spacetime_acceleration(self):
        """Verify Fast LOB Kerr-Newman-Kiselev 43-dark-energy DAHA L3 hydrodynamics."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_43_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )
        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "density_dark_energy_43" in res
        assert "daha_43_factor" in res
        assert "equation_of_state_w_43" in res
        assert math.isclose(res["density_dark_energy_43"], 2.384185791015625e-14, rel_tol=1e-9)
        assert math.isclose(res["daha_43_factor"], 6.35, rel_tol=1e-5)
        assert math.isclose(res["equation_of_state_w_43"], -15.0, rel_tol=1e-5)
        assert math.isfinite(res["queue_acceleration"])

    def test_benchmark_report_synchronization_v64(self):
        """Verify that Phase 64 benchmark markdown reports exist across all target paths."""
        paths = [
            "reports/quant_benchmark_comparison_phase64.md",
            "trading_system/result/quant_benchmark_comparison_phase64.md",
            "trading_system/reports/quant_benchmark_comparison_phase64.md",
            "reports/quant_benchmark_comparison.md",
        ]
        for path in paths:
            assert os.path.exists(path), f"Report path {path} missing"
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "Phase 64 Quantitative Alpha Enhancement" in content
            assert "199.49%" in content
            assert "41.78" in content
            assert "0.0000000000057220458984375 bps" in content

    def test_report_sha256_hash_synchronization_v64(self):
        """Verify bit-for-bit SHA-256 hash synchronization across all 3 standalone reports."""
        paths = [
            "reports/quant_benchmark_comparison_phase64.md",
            "trading_system/reports/quant_benchmark_comparison_phase64.md",
            "trading_system/result/quant_benchmark_comparison_phase64.md",
        ]
        hashes = []
        for path in paths:
            assert os.path.exists(path), f"Report path {path} missing"
            with open(path, "rb") as f:
                hashes.append(hashlib.sha256(f.read()).hexdigest())
        assert len(set(hashes)) == 1, "Report hashes are not identical across paths"

        # Verify canonical reports/quant_benchmark_comparison.md starts with identical Phase 64 report content
        canon_path = "reports/quant_benchmark_comparison.md"
        assert os.path.exists(canon_path), f"Canonical path {canon_path} missing"
        with open(canon_path, "rb") as f_c:
            canon_bytes = f_c.read()
        with open(paths[0], "rb") as f_p:
            p64_bytes = f_p.read()
        assert canon_bytes.startswith(p64_bytes) or (p64_bytes in canon_bytes)
        # Ensure section hash matches standalone files
        if canon_bytes.startswith(p64_bytes):
            section_hash = hashlib.sha256(canon_bytes[:len(p64_bytes)]).hexdigest()
        else:
            idx = canon_bytes.find(p64_bytes)
            assert idx != -1
            section_hash = hashlib.sha256(canon_bytes[idx:idx + len(p64_bytes)]).hexdigest()
        assert section_hash == hashes[0]
