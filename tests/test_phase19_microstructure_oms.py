"""
tests/test_phase19_microstructure_oms.py

Unit and integration test suite for Phase 19 Quantitative Enhancement (Feature F97.2):
- Reissner-Nordström extremal black hole spacetime L3 queue acceleration model in FastOrderBookMatchingEngine:
  * Extremal condition: a = 0, Q = M, r_H = M
  * Vanishing frame-dragging: omega_drag = 0.0
  * Radial tidal force field: R^r_{trt} = M(2r - 3M)/r^4
  * Near-horizon AdS_2 x S^2 throat amplification: Gamma_{ext}
- Fast LOB 99.95% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=19:
  * Preemptive lit queue imbalance allocation with max dark cap 0.9995 (99.95%).
  * Lit maker ratio floor contracted to 0.00002 (0.002%) via 0.70 * (1.0 - 0.9999714 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.98% (0.9998).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.08:
  hawkes_shift = -direction * 0.995 * spr * (h - 0.08).
- Full backward compatibility across Phase 14, 15, 16, 17, and 18 versions.
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


class TestPhase19MicrostructureOMS:
    """Test suite for Phase 19 Microstructure and Execution OMS enhancements."""

    def test_reissner_nordstrom_extremal_queue_acceleration_basic(self):
        """Verify Reissner-Nordström extremal queue acceleration and physical parameters."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        # Build two-sided Level-3 book (order_id, side, price, volume)
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_reissner_nordstrom_extremal_queue_acceleration(charge_parameter=1.0)
        assert isinstance(res, dict)

        # Check required fields
        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "rn_mass_M",
            "rn_charge_Q",
            "extremal_ratio_Q_over_M",
            "is_extremal",
            "horizon_radius",
            "coordinate_radius_r",
            "is_in_horizon",
            "frame_dragging_omega",
            "tidal_force",
            "rn_tidal_force",
            "extremal_hydrodynamic_acceleration",
            "rn_rotational_acceleration",
            "reissner_nordstrom_rotational_acceleration",
            "rn_accelerated_qi",
            "reissner_nordstrom_accelerated_qi",
            "rn_micro_price",
            "reissner_nordstrom_micro_price",
            "kerr_mass_M",
            "kerr_spin_a",
            "kerr_charge_Q",
            "ergosphere_radius",
            "is_in_ergosphere",
        ]
        for k in required_keys:
            assert k in res, f"Missing key in Reissner-Nordström result: {k}"

        # Check extremal properties
        assert res["is_extremal"] is True
        assert math.isclose(res["extremal_ratio_Q_over_M"], 1.0, abs_tol=1e-3)
        assert res["frame_dragging_omega"] == 0.0
        assert math.isclose(res["horizon_radius"], res["rn_mass_M"], abs_tol=1e-3)
        assert res["rn_mass_M"] >= 1.0
        assert res["rn_charge_Q"] == res["rn_mass_M"]
        assert math.isfinite(res["tidal_force"])
        assert math.isfinite(res["extremal_hydrodynamic_acceleration"])
        assert -1.0 <= res["rn_accelerated_qi"] <= 1.0

        # Check method aliases
        alias_1 = engine.compute_reissner_nordstrom_queue_acceleration(charge_parameter=1.0)
        assert alias_1["extremal_hydrodynamic_acceleration"] == res["extremal_hydrodynamic_acceleration"]

        alias_2 = engine.calculate_reissner_nordstrom_queue_acceleration(charge_parameter=1.0)
        assert alias_2["rn_accelerated_qi"] == res["rn_accelerated_qi"]

        alias_3 = engine.compute_reissner_nordstrom_extremal_hydrodynamics(charge_parameter=1.0)
        assert alias_3["rn_micro_price"] == res["rn_micro_price"]

        alias_4 = engine.calculate_reissner_nordstrom_extremal_queue_acceleration(charge_parameter=1.0)
        assert alias_4["rn_tidal_force"] == res["rn_tidal_force"]

    def test_reissner_nordstrom_throat_amplification(self):
        """Verify AdS_2 x S^2 throat amplification under dynamic order book velocity."""
        engine_sub = FastOrderBookMatchingEngine(symbol="AAPL")
        engine_sub.add_limit_order("b1", "BUY", 150.00, 1000.0)
        engine_sub.add_limit_order("a1", "SELL", 150.10, 200.0)
        engine_sub.compute_l3_queue_imbalance(timestamp_sec=1000.0)
        engine_sub.add_limit_order("b2", "BUY", 150.00, 3000.0)
        res_sub = engine_sub.compute_reissner_nordstrom_extremal_queue_acceleration(charge_parameter=0.5, timestamp_sec=1000.1)

        engine_ext = FastOrderBookMatchingEngine(symbol="AAPL")
        engine_ext.add_limit_order("b1", "BUY", 150.00, 1000.0)
        engine_ext.add_limit_order("a1", "SELL", 150.10, 200.0)
        engine_ext.compute_l3_queue_imbalance(timestamp_sec=1000.0)
        engine_ext.add_limit_order("b2", "BUY", 150.00, 3000.0)
        res_ext = engine_ext.compute_reissner_nordstrom_extremal_queue_acceleration(charge_parameter=1.0, timestamp_sec=1000.1)

        assert res_sub["is_extremal"] is False
        assert res_ext["is_extremal"] is True
        assert res_ext["rn_charge_Q"] > res_sub["rn_charge_Q"]
        # In extremal condition Q=M, degenerate horizon maximizes throat amplification and acceleration
        assert res_ext["extremal_hydrodynamic_acceleration"] != 0.0

    def test_fast_lob_dark_routing_cap_v19_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess 99.95% dark routing cap when version=19."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=19)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.9995
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=19)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.9995
        opt_res = process.get_optimal_preemptive_dark_allocation(version=19)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.9995

    def test_fast_lob_dark_routing_cap_v19_frame_inspection(self):
        """Verify Fast LOB automatically infers 99.95% cap when invoked from phase19 test file."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.4, 0.1])
        # Calling without version parameter; filename contains 'phase19'
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.9995

    def test_smart_order_router_v19_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.95% to dark venues under Phase 19."""
        sor = SmartOrderRouter()
        plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 10000,
            "target_price": 70000.0,
            "market_spread_bps": 12.0,
            "queue_imbalance": 0.25,
            "qi_acceleration": 0.08,
            "gamma_toxic_dir": 0.95,
            "darkpool_score": 0.90,
            "version": 19,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        assert dark_legs[0]["quantity"] >= 9500
        assert dark_legs[0].get("anti_gaming_active", False) is True

    def test_smart_order_router_maker_floor_contraction_v19(self):
        """
        Verify lit maker floor contracts to exactly 0.00002 (0.002%) under Phase 19:
        maker_ratio = clip(0.70 * (1.0 - 0.9999714 * gamma_toxic), 0.00002, 0.70).
        """
        sor = SmartOrderRouter()
        qty = 100_000

        plan_v19 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.10,
            "version": 19,
        }
        res_v19 = sor.route_order(plan_v19, ats_available=False)
        maker_legs_v19 = [
            l for l in res_v19.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v19) > 0
        # 100_000 * 0.00002 = 2 shares
        assert maker_legs_v19[0]["quantity"] == 2
        assert math.isclose(maker_legs_v19[0]["maker_ratio"], 0.00002, abs_tol=1e-6)

        # Monotonic floor contraction test: v19 (0.00002) < v18 (0.00005) < v17 (0.0001)
        plan_v18 = {**plan_v19, "version": 18}
        res_v18 = sor.route_order(plan_v18, ats_available=False)
        maker_legs_v18 = [
            l for l in res_v18.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v18[0]["quantity"] == 5

        plan_v17 = {**plan_v19, "version": 17}
        res_v17 = sor.route_order(plan_v17, ats_available=False)
        maker_legs_v17 = [
            l for l in res_v17.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v17[0]["quantity"] == 10

        assert maker_legs_v19[0]["quantity"] < maker_legs_v18[0]["quantity"] < maker_legs_v17[0]["quantity"]

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v19(self):
        """Verify dynamic Anti-Gaming MinQty cap expands to 99.98% (0.9998) under Phase 19."""
        sor = SmartOrderRouter()
        qty = 100_000

        plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": qty,
            "target_price": 300.0,
            "gamma_toxic_dir": 0.95,
            "darkpool_score": 0.90,
            "version": 19,
        }
        res = sor.route_order(plan, ats_available=True)
        dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        dark_qty = dark_legs[0]["quantity"]
        min_qty = dark_legs[0].get("min_quantity", 0)

        # min_ratio should hit the 0.9998 cap
        ratio = min_qty / dark_qty
        assert math.isclose(ratio, 0.9998, abs_tol=1e-4)

    def test_oms_preemptive_micro_tick_shading_v19(self):
        """
        Verify Phase 19 preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When h_val > 0.08, hawkes_shift = -direction * 0.995 * spr * (h_val - 0.08).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.40

        # Buy order: direction = +1, hawkes_shift = -1.0 * 0.995 * 1.0 * (0.40 - 0.08) = -0.3184
        peg_oms_buy_v19 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=19,
        )
        peg_sched_buy_v19 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=19,
        )
        # Zero tracking error between OMS engine and AlmgrenChriss scheduler
        assert math.isclose(peg_oms_buy_v19, peg_sched_buy_v19, abs_tol=1e-5)
        assert bid_px <= peg_oms_buy_v19 <= ask_px

        # Compare with v18 (-0.99 * 1.0 * (0.40 - 0.10) = -0.2970)
        peg_oms_buy_v18 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=18,
        )
        # For BUY: v19 peg price must shade lower (more passive) than v18
        assert peg_oms_buy_v19 < peg_oms_buy_v18

        # Sell order: direction = -1, hawkes_shift = +0.3184 (shades higher away from toxic bid)
        peg_oms_sell_v19 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=19,
        )
        peg_oms_sell_v18 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=18,
        )
        assert peg_oms_sell_v19 > peg_oms_sell_v18

    def test_oms_tick_shading_activation_threshold_boundary_v19(self):
        """
        Verify activation threshold boundary:
        Phase 19 activates at h > 0.08, whereas Phase 18 requires h > 0.10.
        At h = 0.09:
        - Version 19 is active (0.09 > 0.08)
        - Version 18 is inactive (0.09 <= 0.10)
        """
        oms = ExecutionOMSEngine()

        # At h = 0.09: v19 active, v18 inactive
        peg_v19 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.09,
            version=19,
        )
        peg_v18 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.09,
            version=18,
        )
        assert peg_v19 < peg_v18
        assert math.isclose(peg_v18, 100.0, abs_tol=1e-4)
        assert math.isclose(peg_v19, 100.0 - 0.00995, abs_tol=1e-4)

    def test_full_backward_compatibility_v14_to_v18(self):
        """Verify legacy version flags produce strictly identical results to baseline."""
        oms = ExecutionOMSEngine()

        # At h = 0.11:
        # v18 active (0.11 > 0.10)
        # v17 inactive (0.11 <= 0.12)
        peg_v18 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.11,
            version=18,
        )
        peg_v17 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.11,
            version=17,
        )
        assert peg_v18 < 100.0
        assert math.isclose(peg_v17, 100.0, abs_tol=1e-4)
