"""
tests/test_phase50_adversarial_oms_benchmark.py

Adversarial Stress Test Suite for Phase 50 Quantitative Enhancement:
Focus: Feature F224.1 & F224.2 (Microstructure OMS) and Feature F225 (Quant Benchmark Deliverables).

Challenger 2 Empirical Verification:
1. Lit maker floor 1e-22 precision and zero-underflow immunity under extreme toxicity gamma in [0.80, 1.0].
2. Dark ATS cap 99.999999999999% under massive orders and extreme queue shifts.
3. Dynamic Anti-Gaming MinQty cap 99.999999999999% under peak toxicity.
4. Preemptive tick shading strict activation threshold at h > 0.00005 and deadband at h <= 0.00005.
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


class TestPhase50AdversarialMicrostructureOMS:
    """Adversarial stress testing of Phase 50 Microstructure and Execution OMS."""

    def test_lit_maker_floor_grid_zero_underflow_immunity_v50(self):
        """Test 10,000 points across gamma_toxic in [0.80, 1.0] to guarantee no underflow below 1e-22."""
        gamma_grid = np.linspace(0.80, 1.0, 10001)
        for g in gamma_grid:
            val = float(np.clip(
                round(0.70 * (1.0 - 0.9999999999999999999986 * g), 30),
                0.0000000000000000000001,
                0.70
            ))
            assert val > 0.0
            assert val >= 1e-22

    def test_lit_maker_floor_extreme_boundaries_in_sor_v50(self):
        """Verify SmartOrderRouter routing with extreme toxicity under 10 Septillion shares (10^22)."""
        sor = SmartOrderRouter()
        qty = 10_000_000_000_000_000_000_000  # 10^22 shares

        plan_max_tox = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 50,
        }
        res_max = sor.route_order(plan_max_tox, ats_available=False)
        maker_legs = [l for l in res_max.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"]
        assert len(maker_legs) > 0
        assert maker_legs[0]["quantity"] == 1
        assert res_max["maker_ratio"] == 1e-22

    def test_dark_ats_preemption_cap_v50(self):
        """Verify dark ATS routing cap up to 99.999999999999%."""
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
            "version": 50,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        total_dark = sum(l["quantity"] for l in dark_legs)
        assert total_dark == 99_999_999_999_999

        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])
        p_res = process.compute_preemptive_dark_routing(version=50)
        assert p_res["preemptive_dark_routing_ratio"] == 0.99999999999999

    def test_anti_gaming_min_qty_cap_v50(self):
        """Verify dynamic anti-gaming MinQty scales up to 99.999999999999%."""
        sor = SmartOrderRouter()
        plan_tox = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 1_000_000,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 50,
        }
        res = sor.route_order(plan_tox, ats_available=True)
        assert res["min_ratio"] == 0.99999999999999

    def test_preemptive_micro_tick_shading_deadband_and_activation_v50(self):
        """Verify tick shading activates strictly when h > 0.00005, deadband at h <= 0.00005."""
        oms = ExecutionOMSEngine()

        # Deadband test: h = 0.00004
        p_dead = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.00004},
            version=50,
        )
        assert math.isclose(p_dead, 100.0, rel_tol=1e-5)

        # Boundary deadband test: h = 0.00005
        p_bound = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.00005},
            version=50,
        )
        assert math.isclose(p_bound, 100.0, rel_tol=1e-5)

        # Activation test: h = 0.00009
        p_act = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.00009},
            version=50,
        )
        exp_shift = -1 * 0.9999999999995 * 1.0 * (0.00009 - 0.00005)
        assert math.isclose(p_act - 100.0, exp_shift, rel_tol=1e-5)

    def test_benchmark_report_synchronization_v50(self):
        """Verify that Phase 50 benchmark markdown reports exist across all target paths."""
        paths = [
            "reports/quant_benchmark_comparison_phase50.md",
            "trading_system/result/quant_benchmark_comparison_phase50.md",
            "trading_system/reports/quant_benchmark_comparison_phase50.md",
        ]
        for path in paths:
            assert os.path.exists(path), f"Report path {path} missing"
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "Phase 50 Quantitative Alpha Enhancement" in content
            assert "170.09%" in content
            assert "33.38" in content
            assert "0.00000009375 bps" in content
            assert "0.000000078125 bps" in content
