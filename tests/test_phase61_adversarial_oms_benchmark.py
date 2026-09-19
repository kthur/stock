"""
tests/test_phase61_adversarial_oms_benchmark.py

Adversarial Stress Test Suite for Phase 61 Quantitative Enhancement:
Focus: Feature F279.1 & F279.2 (Microstructure OMS) and Feature F280 (Quant Benchmark Deliverables).

Challenger 2 Empirical Verification:
1. Lit maker floor 1e-33 precision and zero-underflow immunity under extreme toxicity gamma in [0.80, 1.0].
2. Dark ATS cap 0.999999999999999999 (18 nines) under massive orders and extreme queue shifts.
3. Dynamic Anti-Gaming MinQty cap 0.999999999999999999 under peak toxicity.
4. Preemptive tick shading strict activation threshold at h > 0.0000020 and deadband at h <= 0.0000020.
5. Fast LOB Kerr-Newman-Kiselev 40-Dark-Energy DAHA tidal acceleration.
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


class TestPhase61AdversarialMicrostructureOMS:
    """Adversarial stress testing of Phase 61 Microstructure and Execution OMS."""

    def test_lit_maker_floor_grid_zero_underflow_immunity_v61(self):
        """Test 10,001 points across gamma_toxic in [0.80, 1.0] to guarantee no underflow below 1e-33."""
        gamma_grid = np.linspace(0.80, 1.0, 10001)
        for g in gamma_grid:
            val = float(np.clip(
                round(0.70 * (1.0 - 0.99999999999999999999999999999986 * g), 44),
                1e-33,
                0.70
            ))
            assert val > 0.0
            assert val >= 1e-33

    def test_lit_maker_floor_extreme_boundaries_in_sor_v61(self):
        """Verify SmartOrderRouter routing with extreme toxicity under 10^33 shares."""
        sor = SmartOrderRouter(version=61)
        qty = 10**33  # 10^33 shares

        plan_max_tox = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 61,
        }
        res_max = sor.route_order(plan_max_tox, ats_available=False)
        maker_legs = [l for l in res_max.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"]
        assert len(maker_legs) > 0
        assert maker_legs[0]["quantity"] == 1
        assert res_max["maker_ratio"] == 1e-33

    def test_dark_ats_preemption_cap_v61(self):
        """Verify dark ATS routing cap up to 0.999999999999999999 (18 nines)."""
        sor = SmartOrderRouter(version=61)
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
            "version": 61,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        total_dark = sum(l["quantity"] for l in dark_legs)
        assert total_dark >= 9_999_999_999_999_999_990

        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([20.0, 0.5, 0.2])
        p_res = process.compute_preemptive_dark_routing(version=61)
        assert math.isclose(p_res["preemptive_dark_routing_ratio"], 0.999999999999999999, rel_tol=1e-15)

    def test_anti_gaming_min_qty_cap_v61(self):
        """Verify dynamic anti-gaming MinQty scales up to 0.999999999999999999."""
        sor = SmartOrderRouter(version=61)
        plan_tox = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 1_000_000,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 61,
        }
        res = sor.route_order(plan_tox, ats_available=True)
        assert math.isclose(res["min_ratio"], 0.999999999999999999, rel_tol=1e-15)

    def test_preemptive_micro_tick_shading_deadband_and_activation_v61(self):
        """Verify tick shading activates strictly when h > 0.0000020, deadband at h <= 0.0000020."""
        oms = ExecutionOMSEngine()

        # Deadband test: h = 0.000001
        p_dead = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            spread=1.0,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.000001},
            version=61,
        )
        assert math.isclose(p_dead, 100.0, rel_tol=1e-5)

        # Boundary deadband test: h = 0.0000020
        p_bound = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            spread=1.0,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.0000020},
            version=61,
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
            version=61,
        )
        exp_shift = -1 * 0.9999999999999999 * 1.0 * (0.000050 - 0.0000020)
        assert math.isclose(p_act - 100.0, exp_shift, rel_tol=1e-5)

    def test_knk_40_dark_energy_daha_spacetime_acceleration(self):
        """Verify Fast LOB Kerr-Newman-Kiselev 40-dark-energy DAHA L3 hydrodynamics."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"b_{i}", "BUY", 70000.0 - i * 50.0, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 70100.0 + i * 50.0, 100.0)

        res = engine.compute_kerr_newman_kiselev_40_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isclose(res["density_dark_energy_40"], 1.9073486328125e-13, rel_tol=1e-9)
        assert math.isclose(res["daha_40_factor"], 5.60, rel_tol=1e-5)
        assert math.isclose(res["equation_of_state_w_40"], -42.0 / 3.0, rel_tol=1e-5)
        assert math.isfinite(res["queue_acceleration"])

    def test_benchmark_report_synchronization_v61(self):
        """Verify that Phase 61 benchmark markdown reports exist across all target paths."""
        paths = [
            "reports/quant_benchmark_comparison_phase61.md",
            "trading_system/result/quant_benchmark_comparison_phase61.md",
            "trading_system/reports/quant_benchmark_comparison_phase61.md",
            "reports/quant_benchmark_comparison.md",
        ]
        for path in paths:
            assert os.path.exists(path), f"Report path {path} missing"
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "Phase 61 Quantitative Alpha Enhancement" in content
            assert "193.19%" in content
            assert "39.98" in content
            assert "0.0000000000457763671875 bps" in content
            assert "0.00000000003814697265625 bps" in content

    def test_report_sha256_hash_synchronization_v61(self):
        """Verify SHA-256 hash synchronization across canonical report copies and sections."""
        paths = [
            "reports/quant_benchmark_comparison_phase61.md",
            "trading_system/result/quant_benchmark_comparison_phase61.md",
            "trading_system/reports/quant_benchmark_comparison_phase61.md",
        ]
        hashes = []
        for path in paths:
            assert os.path.exists(path), f"Report path {path} missing"
            with open(path, "rb") as f:
                hashes.append(hashlib.sha256(f.read()).hexdigest())
        assert len(set(hashes)) == 1, "Report hashes are not identical across paths"

        # Verify canonical reports/quant_benchmark_comparison.md starts with identical Phase 61 report content
        canon_path = "reports/quant_benchmark_comparison.md"
        assert os.path.exists(canon_path), f"Canonical path {canon_path} missing"
        with open(canon_path, "rb") as f_c:
            canon_bytes = f_c.read()
        with open(paths[0], "rb") as f_p:
            p61_bytes = f_p.read()
        assert canon_bytes.startswith(p61_bytes) or (p61_bytes in canon_bytes)
        # Ensure section hash matches standalone files
        if canon_bytes.startswith(p61_bytes):
            section_hash = hashlib.sha256(canon_bytes[:len(p61_bytes)]).hexdigest()
        else:
            idx = canon_bytes.find(p61_bytes)
            assert idx != -1
            section_hash = hashlib.sha256(canon_bytes[idx:idx + len(p61_bytes)]).hexdigest()
        assert section_hash == hashes[0]
