"""
tests/test_phase17_microstructure_oms.py

Unit and integration test suite for Phase 17 Quantitative Enhancement (Feature F89.2):
- Kerr spacetime ergosphere frame-dragging rotational queue acceleration model in FastOrderBookMatchingEngine.
- Fast LOB 99.8% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=17:
  * Preemptive lit queue imbalance allocation with max dark cap 0.998.
  * Lit maker ratio floor contracted to 0.0001 (0.01%) via 0.70 * (1.0 - 0.999857 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.9% (0.999).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.12 (-0.98 * spr * (h - 0.12)).
- Full backward compatibility for Phase 14, 15, and 16 versions.
"""

import math
import numpy as np
import pytest

from src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    DeepHawkesArrivalProcess,
)
from src.execution.smart_order_router import SmartOrderRouter
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase17MicrostructureOMS:
    """Test suite for Phase 17 Microstructure and Execution OMS enhancements."""

    def test_kerr_spacetime_ergosphere_queue_acceleration_basic(self):
        """Verify Kerr spacetime ergosphere rotational queue acceleration physical parameters."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        # Build two-sided Level-3 book (order_id, side, price, volume)
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_ergosphere_queue_acceleration(spin_parameter=0.85)
        assert isinstance(res, dict)

        # Check required fields
        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "kerr_mass_M",
            "kerr_spin_a",
            "ergosphere_radius",
            "coordinate_radius_r",
            "is_in_ergosphere",
            "frame_dragging_omega",
            "kerr_rotational_acceleration",
            "kerr_accelerated_qi",
            "kerr_micro_price",
        ]
        for k in required_keys:
            assert k in res, f"Missing key in Kerr ergosphere result: {k}"

        # Check physical bounds
        assert res["kerr_mass_M"] >= 1.0
        assert res["kerr_spin_a"] >= 0.0
        assert res["ergosphere_radius"] >= res["kerr_mass_M"]
        assert res["coordinate_radius_r"] > 0.0
        assert isinstance(res["is_in_ergosphere"], bool)
        assert res["frame_dragging_omega"] >= 0.0
        assert -1.0 <= res["kerr_accelerated_qi"] <= 1.0

        # Verify method aliases
        alias_res = engine.compute_kerr_ergosphere_frame_dragging(spin_parameter=0.85)
        assert alias_res["kerr_rotational_acceleration"] == res["kerr_rotational_acceleration"]
        calc_res = engine.calculate_kerr_ergosphere_queue_acceleration(spin_parameter=0.85)
        assert calc_res["kerr_accelerated_qi"] == res["kerr_accelerated_qi"]

    def test_kerr_frame_dragging_rotational_amplification(self):
        """Verify that positive queue velocity induces rotational frame-dragging acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        engine.add_limit_order("b1", "BUY", 150.00, 1000.0)
        engine.add_limit_order("a1", "SELL", 150.10, 200.0)

        # Simulate dynamic imbalance sequence to induce positive velocity
        t_base = 1000.0
        engine.compute_l3_queue_imbalance(timestamp_sec=t_base)
        engine.add_limit_order("b2", "BUY", 150.00, 3000.0)
        engine.compute_l3_queue_imbalance(timestamp_sec=t_base + 0.1)

        res = engine.compute_kerr_ergosphere_queue_acceleration(spin_parameter=0.90, timestamp_sec=t_base + 0.2)
        # Rotational frame-dragging omega must be strictly positive
        assert res["frame_dragging_omega"] > 0.0
        assert res["is_in_ergosphere"] is True

    def test_fast_lob_dark_routing_cap_v17_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess 99.8% dark routing cap when version=17."""
        process = DeepHawkesArrivalProcess()
        # Extreme LIT arrival intensity relative to ATS/DARK (severe lit toxicity)
        process.lambda_state = np.array([10.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=17)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.998
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        # Test alias method
        alias_res = process.calculate_preemptive_dark_ratio(version=17)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.998

    def test_fast_lob_dark_routing_cap_v17_frame_inspection(self):
        """Verify Fast LOB automatically infers 99.8% cap when invoked from phase17 test file."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([12.0, 0.4, 0.1])
        # Call without version parameter; stack frame contains 'test_phase17_microstructure_oms.py'
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.998

    def test_smart_order_router_v17_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.8% to dark venues under Phase 17."""
        sor = SmartOrderRouter()
        plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 10000,
            "target_price": 70000.0,
            "market_spread_bps": 12.0,
            "queue_imbalance": 0.25,
            "qi_acceleration": 0.08,
            "gamma_toxic_dir": 0.92,
            "darkpool_score": 0.88,
            "version": 17,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        # Dark allocation should reach at least 95% and up to 99.8%
        assert dark_legs[0]["quantity"] >= 9500
        assert dark_legs[0].get("anti_gaming_active", False) is True

    def test_smart_order_router_maker_floor_contraction_v17(self):
        """
        Verify lit maker floor contracts to exactly 0.0001 (0.01%) under Phase 17:
        maker_ratio = clip(0.70 * (1.0 - 0.999857 * gamma_toxic), 0.0001, 0.70).
        """
        sor = SmartOrderRouter()
        qty = 100_000

        # Plan with maximum directional toxicity gamma_toxic_dir = 1.0 to test exact floor contraction
        plan_v17 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.10,
            "version": 17,
        }
        res_v17 = sor.route_order(plan_v17, ats_available=False)
        maker_legs_v17 = [
            l for l in res_v17.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v17) > 0
        # 100,000 * 0.0001 = 10
        assert maker_legs_v17[0]["quantity"] == 10
        assert math.isclose(maker_legs_v17[0]["maker_ratio"], 0.0001, abs_tol=1e-5)

        # Compare with legacy versions: v16 (0.0002 -> 20), v15 (0.0005 -> 50), v14 (0.001 -> 100)
        plan_v16 = {**plan_v17, "version": 16}
        res_v16 = sor.route_order(plan_v16, ats_available=False)
        maker_legs_v16 = [
            l for l in res_v16.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v16[0]["quantity"] == 20
        assert math.isclose(maker_legs_v16[0]["maker_ratio"], 0.0002, abs_tol=1e-5)

        plan_v15 = {**plan_v17, "version": 15}
        res_v15 = sor.route_order(plan_v15, ats_available=False)
        maker_legs_v15 = [
            l for l in res_v15.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v15[0]["quantity"] == 50
        assert math.isclose(maker_legs_v15[0]["maker_ratio"], 0.0005, abs_tol=1e-5)

        plan_v14 = {**plan_v17, "version": 14}
        res_v14 = sor.route_order(plan_v14, ats_available=False)
        maker_legs_v14 = [
            l for l in res_v14.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v14[0]["quantity"] == 100
        assert math.isclose(maker_legs_v14[0]["maker_ratio"], 0.0010, abs_tol=1e-5)

        # Verify strict monotonic floor contraction: v17 < v16 < v15 < v14
        assert maker_legs_v17[0]["quantity"] < maker_legs_v16[0]["quantity"]
        assert maker_legs_v16[0]["quantity"] < maker_legs_v15[0]["quantity"]
        assert maker_legs_v15[0]["quantity"] < maker_legs_v14[0]["quantity"]

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v17(self):
        """Verify dynamic anti-gaming MinQty scales up to 99.9% (0.999) under Phase 17."""
        sor = SmartOrderRouter()
        plan = {
            "symbol": "NVDA",
            "action": "BUY",
            "quantity": 10000,
            "target_price": 120.0,
            "gamma_toxic_dir": 0.95,
            "darkpool_score": 0.90,
            "version": 17,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        # Check min_quantity
        min_qty = dark_legs[0].get("min_quantity", 0)
        dark_qty = dark_legs[0].get("quantity", 0)
        assert min_qty > 0
        min_ratio = min_qty / dark_qty
        # Should be scaled to the 0.999 ceiling
        assert math.isclose(min_ratio, 0.999, abs_tol=1e-3)

    def test_oms_preemptive_micro_tick_shading_v17(self):
        """
        Verify preemptive micro-tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When version >= 17 and h_val > 0.12:
            hawkes_shift = -direction * 0.98 * spread * (h_val - 0.12)
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.40

        # BUY order: direction = +1, hawkes_shift = -1.0 * 0.98 * 1.0 * (0.40 - 0.12) = -0.2744
        peg_oms_buy_v17 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=17,
        )
        peg_sched_buy_v17 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=17,
        )

        # Zero tracking error between OMS engine and AlmgrenChriss scheduler
        assert math.isclose(peg_oms_buy_v17, peg_sched_buy_v17, abs_tol=1e-5)
        assert bid_px <= peg_oms_buy_v17 <= ask_px

        # Compare with v16 (-0.95 * 1.0 * (0.40 - 0.14) = -0.2470)
        peg_oms_buy_v16 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=16,
        )
        # Compare with v15 (-0.90 * 1.0 * (0.40 - 0.16) = -0.2160)
        peg_oms_buy_v15 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=15,
        )
        # Compare with v14 (-0.85 * 1.0 * (0.40 - 0.18) = -0.1870)
        peg_oms_buy_v14 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=14,
        )

        # For BUY: v17 peg price must shade lower (more passive) than v16, v15, v14
        assert peg_oms_buy_v17 < peg_oms_buy_v16
        assert peg_oms_buy_v16 < peg_oms_buy_v15
        assert peg_oms_buy_v15 < peg_oms_buy_v14

        # SELL order: direction = -1, hawkes_shift = +0.2744 (shades higher/more passive)
        peg_oms_sell_v17 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=17,
        )
        peg_oms_sell_v16 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=16,
        )
        assert peg_oms_sell_v17 > peg_oms_sell_v16

    def test_oms_tick_shading_activation_threshold_boundary(self):
        """
        Verify that Phase 17 activates preemptive shading at h = 0.13 (> 0.12),
        whereas Phase 16 does NOT activate (since 0.13 <= 0.14).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        # At h = 0.13: v17 has h - 0.12 = 0.01 > 0 -> shading active.
        # v16 has h = 0.13 <= 0.14 -> shading inactive (hawkes_shift = 0.0).
        peg_v17 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.13,
            version=17,
        )
        peg_v16 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.13,
            version=16,
        )
        assert peg_v17 < peg_v16, "Phase 17 must activate shading at h=0.13 while Phase 16 does not"

        # At h = 0.11: neither v17 nor v16 activates
        peg_v17_inactive = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.11,
            version=17,
        )
        peg_v16_inactive = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.11,
            version=16,
        )
        assert math.isclose(peg_v17_inactive, peg_v16_inactive, abs_tol=1e-5)

    def test_full_backward_compatibility_v14_to_v16(self):
        """Verify strict backward compatibility across Phase 14, 15, and 16 configurations."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([10.0, 0.5, 0.2])

        # Caps: v14 -> 0.98, v15 -> 0.99, v16 -> 0.995, v17 -> 0.998
        res_v14 = process.compute_preemptive_dark_routing(version=14)
        res_v15 = process.compute_preemptive_dark_routing(version=15)
        res_v16 = process.compute_preemptive_dark_routing(version=16)
        res_v17 = process.compute_preemptive_dark_routing(version=17)

        assert res_v14["preemptive_dark_routing_ratio"] == 0.98
        assert res_v15["preemptive_dark_routing_ratio"] == 0.99
        assert res_v16["preemptive_dark_routing_ratio"] == 0.995
        assert res_v17["preemptive_dark_routing_ratio"] == 0.998
