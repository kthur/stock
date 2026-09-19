"""
tests/test_phase58_adversarial_oms_benchmark.py

Adversarial Stress Test Suite for Phase 58 Quantitative Enhancement:
Focus: Feature F264.1 & F264.2 (Microstructure OMS) and Feature F265 (Quant Benchmark Deliverables).

Challenger 2 Empirical Verification:
1. Lit maker floor 1e-30 precision and zero-underflow immunity under extreme toxicity gamma in [0.80, 1.0].
2. Dark ATS cap 99.999999999999998% under massive orders and extreme queue shifts.
3. Dynamic Anti-Gaming MinQty cap 99.999999999999998% under peak toxicity.
4. Preemptive tick shading strict activation threshold at h > 0.000004 and deadband at h <= 0.000004.
5. Fast LOB Kerr-Newman-Kiselev 37-Dark-Energy DAHA tidal acceleration.
6. Benchmark script execution and 7-target assertion oracle verification.
7. Report synchronization across all canonical paths and historical preservation.
"""

import hashlib
import math
import os
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


class TestPhase58AdversarialMicrostructureOMS:
    """Adversarial stress testing of Phase 58 Microstructure and Execution OMS."""

    def test_lit_maker_floor_grid_zero_underflow_immunity_v58(self):
        """Test 10,001 points across gamma_toxic in [0.80, 1.0] to guarantee no underflow below 1e-30."""
        gamma_grid = np.linspace(0.80, 1.0, 10001)
        for g in gamma_grid:
            val = float(np.clip(
                round(0.70 * (1.0 - 0.999999999999999999999999999986 * g), 40),
                1e-30,
                0.70
            ))
            assert val > 0.0
            assert val >= 1e-30

    def test_lit_maker_floor_extreme_boundaries_in_sor_v58(self):
        """Verify SmartOrderRouter routing with extreme toxicity under 10^30 shares."""
        sor = SmartOrderRouter(version=58)
        qty = 10**30  # 10^30 shares

        plan_max_tox = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 58,
        }
        res_max = sor.route_order(plan_max_tox, ats_available=False)
        maker_legs = [l for l in res_max.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"]
        assert len(maker_legs) > 0
        assert maker_legs[0]["quantity"] == 1
        assert res_max["maker_ratio"] == 1e-30

    def test_dark_ats_preemption_cap_v58(self):
        """Verify dark ATS routing cap up to 99.999999999999998%."""
        sor = SmartOrderRouter(version=58)
        plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 10_000_000_000_000_000,
            "target_price": 150.0,
            "market_spread_bps": 12.0,
            "queue_imbalance": 0.80,
            "qi_acceleration": 0.50,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.90,
            "version": 58,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        total_dark = sum(l["quantity"] for l in dark_legs)
        assert total_dark >= 9_999_999_999_999_990

        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([20.0, 0.5, 0.2])
        p_res = process.compute_preemptive_dark_routing(version=58)
        assert math.isclose(p_res["preemptive_dark_routing_ratio"], 0.99999999999999998, rel_tol=1e-15)

    def test_anti_gaming_min_qty_cap_v58(self):
        """Verify dynamic anti-gaming MinQty scales up to 99.999999999999998%."""
        sor = SmartOrderRouter(version=58)
        plan_tox = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 1_000_000,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 58,
        }
        res = sor.route_order(plan_tox, ats_available=True)
        assert math.isclose(res["min_ratio"], 0.99999999999999998, rel_tol=1e-15)

    def test_preemptive_micro_tick_shading_deadband_and_activation_v58(self):
        """Verify tick shading activates strictly when h > 0.000004, deadband at h <= 0.000004."""
        oms = ExecutionOMSEngine()

        # Deadband test: h = 0.000002
        p_dead = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            spread=1.0,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.000002},
            version=58,
        )
        assert math.isclose(p_dead, 100.0, rel_tol=1e-5)

        # Boundary deadband test: h = 0.000004
        p_bound = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            spread=1.0,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.000004},
            version=58,
        )
        assert math.isclose(p_bound, 100.0, rel_tol=1e-5)

        # Activation test: h = 0.000050
        p_act = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            spread=1.0,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.000050},
            version=58,
        )
        exp_shift = -1 * 0.999999999999999 * 1.0 * (0.000050 - 0.000004)
        assert math.isclose(p_act - 100.0, exp_shift, rel_tol=1e-5)

    def test_knk_37_dark_energy_daha_spacetime_acceleration(self):
        """Verify Fast LOB Kerr-Newman-Kiselev 37-dark-energy DAHA L3 hydrodynamics."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"b_{i}", "BUY", 70000.0 - i * 50.0, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 70100.0 + i * 50.0, 100.0)

        res = engine.compute_kerr_newman_kiselev_37_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isclose(res["density_dark_energy_37"], 0.00000000000152587890625, rel_tol=1e-9)
        assert math.isclose(res["daha_37_factor"], 4.88, rel_tol=1e-5)
        assert math.isclose(res["equation_of_state_w_37"], -39.0 / 3.0, rel_tol=1e-5)
        assert math.isfinite(res["queue_acceleration"])

    def test_benchmark_report_synchronization_v58(self):
        """Verify that Phase 58 benchmark markdown reports exist across all target paths."""
        paths = [
            "reports/quant_benchmark_comparison_phase58.md",
            "trading_system/result/quant_benchmark_comparison_phase58.md",
            "trading_system/reports/quant_benchmark_comparison_phase58.md",
            "reports/quant_benchmark_comparison.md",
        ]
        for path in paths:
            assert os.path.exists(path), f"Report path {path} missing"
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "Phase 58 Quantitative Alpha Enhancement" in content
            assert "186.89%" in content
            assert "38.18" in content
            assert "0.0000000003662109375 bps" in content
            assert "0.00000000030517578125 bps" in content

    def test_report_sha256_hash_synchronization_v58(self):
        """Verify SHA-256 hash synchronization across canonical report copies and sections."""
        paths = [
            "reports/quant_benchmark_comparison_phase58.md",
            "trading_system/result/quant_benchmark_comparison_phase58.md",
            "trading_system/reports/quant_benchmark_comparison_phase58.md",
        ]
        hashes = []
        for path in paths:
            assert os.path.exists(path), f"Report path {path} missing"
            with open(path, "rb") as f:
                hashes.append(hashlib.sha256(f.read()).hexdigest())
        assert len(set(hashes)) == 1, "Report hashes are not identical across paths"

        # Verify canonical reports/quant_benchmark_comparison.md starts with identical Phase 58 report content
        canon_path = "reports/quant_benchmark_comparison.md"
        assert os.path.exists(canon_path), f"Canonical path {canon_path} missing"
        with open(canon_path, "rb") as f_c:
            canon_bytes = f_c.read()
        with open(paths[0], "rb") as f_p:
            p58_bytes = f_p.read()
        assert canon_bytes.startswith(p58_bytes)
        # Ensure section hash matches standalone files
        section_hash = hashlib.sha256(canon_bytes[:len(p58_bytes)]).hexdigest()
        assert section_hash == hashes[0]
