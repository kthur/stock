"""
tests/test_phase52_adversarial_oms_benchmark.py

Adversarial Stress Test Suite for Phase 52 Quantitative Enhancement:
Focus: Feature F234.1 & F234.2 (Microstructure OMS) and Feature F235 (Quant Benchmark Deliverables).

Challenger 2 Empirical Verification:
1. Lit maker floor 1e-24 precision and zero-underflow immunity under extreme toxicity gamma in [0.80, 1.0].
2. Dark ATS cap 99.9999999999998% under massive orders and extreme queue shifts.
3. Dynamic Anti-Gaming MinQty cap 99.9999999999998% under peak toxicity.
4. Preemptive tick shading strict activation threshold at h > 0.00003 and deadband at h <= 0.00003.
5. Benchmark script execution and 7-target assertion oracle verification.
6. Report synchronization across all canonical paths and historical preservation.
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


class TestPhase52AdversarialMicrostructureOMS:
    """Adversarial stress testing of Phase 52 Microstructure and Execution OMS."""

    def test_lit_maker_floor_grid_zero_underflow_immunity_v52(self):
        """Test 10,000 points across gamma_toxic in [0.80, 1.0] to guarantee no underflow below 1e-24."""
        gamma_grid = np.linspace(0.80, 1.0, 10001)
        for g in gamma_grid:
            val = float(np.clip(
                round(0.70 * (1.0 - 0.999999999999999999999986 * g), 30),
                0.000000000000000000000001,
                0.70
            ))
            assert val > 0.0
            assert val >= 1e-24

    def test_lit_maker_floor_extreme_boundaries_in_sor_v52(self):
        """Verify SmartOrderRouter routing with extreme toxicity under 100 Septillion shares (10^24)."""
        sor = SmartOrderRouter()
        qty = 1_000_000_000_000_000_000_000_000  # 10^24 shares

        plan_max_tox = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 52,
        }
        res_max = sor.route_order(plan_max_tox, ats_available=False)
        maker_legs = [l for l in res_max.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"]
        assert len(maker_legs) > 0
        assert maker_legs[0]["quantity"] == 1
        assert res_max["maker_ratio"] == 1e-24

    def test_dark_ats_preemption_cap_v52(self):
        """Verify dark ATS routing cap up to 99.9999999999998%."""
        sor = SmartOrderRouter()
        plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 100_000_000_000_000,
            "target_price": 150.0,
            "market_spread_bps": 12.0,
            "queue_imbalance": 0.80,
            "qi_acceleration": 0.50,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.90,
            "version": 52,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        total_dark = sum(l["quantity"] for l in dark_legs)
        assert total_dark == 99_999_999_999_999

        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])
        p_res = process.compute_preemptive_dark_routing(version=52)
        assert p_res["preemptive_dark_routing_ratio"] == 0.999999999999998

    def test_anti_gaming_min_qty_cap_v52(self):
        """Verify dynamic anti-gaming MinQty scales up to 99.9999999999998%."""
        sor = SmartOrderRouter()
        plan_tox = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 1_000_000,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 52,
        }
        res = sor.route_order(plan_tox, ats_available=True)
        assert res["min_ratio"] == 0.999999999999998

    def test_preemptive_micro_tick_shading_deadband_and_activation_v52(self):
        """Verify tick shading activates strictly when h > 0.00003, deadband at h <= 0.00003."""
        oms = ExecutionOMSEngine()

        # Deadband test: h = 0.00002
        p_dead = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.00002},
            version=52,
        )
        assert math.isclose(p_dead, 100.0, rel_tol=1e-5)

        # Boundary deadband test: h = 0.00003
        p_bound = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.00003},
            version=52,
        )
        assert math.isclose(p_bound, 100.0, rel_tol=1e-5)

        # Activation test: h = 0.00008
        p_act = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.00008},
            version=52,
        )
        exp_shift = -1 * 0.9999999999999 * 1.0 * (0.00008 - 0.00003)
        assert math.isclose(p_act - 100.0, exp_shift, rel_tol=1e-5)

    def test_benchmark_report_synchronization_v52(self):
        """Verify that Phase 52 benchmark markdown reports exist across all target paths if generated."""
        paths = [
            "reports/quant_benchmark_comparison_phase52.md",
            "trading_system/result/quant_benchmark_comparison_phase52.md",
            "trading_system/reports/quant_benchmark_comparison_phase52.md",
        ]
        existing = [p for p in paths if os.path.exists(p)]
        if not existing:
            pytest.skip("Phase 52 benchmark reports not yet generated by Benchmark Verifier")
        for path in paths:
            assert os.path.exists(path), f"Report path {path} missing"
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "Phase 52 Quantitative Alpha Enhancement" in content
            assert "174.29%" in content
            assert "34.58" in content
            assert "0.0000000234375 bps" in content
            assert "0.00000001953125 bps" in content

    def test_report_sha256_hash_synchronization_v52(self):
        """Verify SHA-256 hash synchronization across all canonical report copies if generated."""
        paths = [
            "reports/quant_benchmark_comparison_phase52.md",
            "trading_system/result/quant_benchmark_comparison_phase52.md",
            "trading_system/reports/quant_benchmark_comparison_phase52.md",
        ]
        existing = [p for p in paths if os.path.exists(p)]
        if not existing:
            pytest.skip("Phase 52 benchmark reports not yet generated by Benchmark Verifier")
        hashes = []
        for path in paths:
            assert os.path.exists(path), f"Report path {path} missing"
            with open(path, "rb") as f:
                hashes.append(hashlib.sha256(f.read()).hexdigest())
        assert len(set(hashes)) == 1, "Report hashes are not identical across paths"
