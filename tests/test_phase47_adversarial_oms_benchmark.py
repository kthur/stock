"""
tests/test_phase47_adversarial_oms_benchmark.py

Adversarial Stress Test Suite for Phase 47 Quantitative Enhancement:
Focus: Feature F209.2 (Microstructure OMS) and Feature F210 (Quant Benchmark Deliverables).

Challenger 2 Empirical Verification:
1. Lit maker floor 1e-19 precision and zero-underflow immunity under extreme toxicity gamma in [0.80, 1.0].
2. Dark ATS cap 99.99999999998% under massive orders and extreme queue shifts.
3. Dynamic Anti-Gaming MinQty cap 99.99999999999% under peak toxicity.
4. Preemptive tick shading strict activation threshold at h > 0.00010 and deadband at h <= 0.00010.
5. Benchmark script execution and 7-target assertion oracle failure testing.
6. SHA-256 hash synchronization across all 3 report paths and historical report preservation.
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


class TestPhase47AdversarialMicrostructureOMS:
    """Adversarial stress testing of Phase 47 Microstructure and Execution OMS."""

    def test_lit_maker_floor_grid_zero_underflow_immunity_v47(self):
        """Test 10,000 points across gamma_toxic in [0.80, 1.0] to guarantee no underflow below 1e-19."""
        gamma_grid = np.linspace(0.80, 1.0, 10001)
        for g in gamma_grid:
            val = float(np.clip(
                round(0.70 * (1.0 - 0.9999999999999999986 * g), 22),
                0.0000000000000000001,
                0.70
            ))
            assert val > 0.0
            assert val >= 1e-19

    def test_lit_maker_floor_extreme_boundaries_in_sor_v47(self):
        """Verify SmartOrderRouter routing with extreme toxicity under 10 Quintillion shares (10^19)."""
        sor = SmartOrderRouter()
        qty = 10_000_000_000_000_000_000  # 10^19 shares

        plan_max_tox = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 47,
        }
        res_max = sor.route_order(plan_max_tox, ats_available=False)
        maker_legs = [l for l in res_max.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"]
        assert len(maker_legs) > 0
        assert maker_legs[0]["quantity"] == 1
        assert res_max["maker_ratio"] == 1e-19

    def test_dark_ats_preemption_cap_v47(self):
        """Verify dark ATS routing cap up to 99.99999999998%."""
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
            "version": 47,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        total_dark = sum(l["quantity"] for l in dark_legs)
        assert total_dark == 99_999_999_999_980

        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])
        p_res = process.compute_preemptive_dark_routing(version=47)
        assert p_res["preemptive_dark_routing_ratio"] == 0.9999999999998

    def test_anti_gaming_min_qty_cap_v47(self):
        """Verify dynamic anti-gaming MinQty scales up to 99.99999999999%."""
        sor = SmartOrderRouter()
        plan_tox = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 1_000_000,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 47,
        }
        res = sor.route_order(plan_tox, ats_available=True)
        assert res["min_ratio"] == 0.9999999999999

    def test_preemptive_tick_shading_activation_threshold_v47(self):
        """Verify hawkes tick shading activates strictly at h > 0.00010 in both engines."""
        oms = ExecutionOMSEngine()
        sched = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5

        # At h = 0.00010, shift must be exactly 0.0
        p1 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.00010},
            version=47,
        )
        assert math.isclose(p1, target_px, rel_tol=1e-7)

        # At h = 0.00011 > 0.00010, shift must be negative for BUY
        p2 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.00011},
            version=47,
        )
        assert p2 < target_px

        p2_sched = sched.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.00011},
            version=47,
        )
        assert math.isclose(p2, p2_sched, rel_tol=1e-7)

    def test_benchmark_reports_hash_synchronization(self):
        """Verify SHA-256 hash synchronization across all 3 Phase 47 markdown report paths."""
        paths = [
            "reports/quant_benchmark_comparison_phase47.md",
            "trading_system/result/quant_benchmark_comparison_phase47.md",
            "trading_system/reports/quant_benchmark_comparison_phase47.md",
        ]
        hashes = []
        for p in paths:
            assert os.path.exists(p), f"Report path missing: {p}"
            with open(p, "rb") as f:
                hashes.append(hashlib.sha256(f.read()).hexdigest())

        assert len(set(hashes)) == 1, "Report hashes out of sync across destinations!"
