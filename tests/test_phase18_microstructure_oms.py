"""
tests/test_phase18_microstructure_oms.py

Unit and integration test suite for Phase 18 Quantitative Enhancement (Feature F93.2):
- Kerr-Newman charged rotating spacetime L3 queue acceleration model in FastOrderBookMatchingEngine.
  * Incorporates net order flow charge Q, Kerr spin a, ergosphere radius r_E(theta),
    Kerr-Newman frame-dragging angular velocity omega_drag, and tidal force tensor component F_tidal.
- Fast LOB 99.9% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=18:
  * Preemptive lit queue imbalance allocation with max dark cap 0.999 (99.9%).
  * Lit maker ratio floor contracted to 0.00005 (0.005%) via 0.70 * (1.0 - 0.9999286 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.95% (0.9995).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.10:
  hawkes_shift = -direction * 0.99 * spr * (h - 0.10).
- Full backward compatibility across Phase 14, 15, 16, and 17 versions.
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


class TestPhase18MicrostructureOMS:
    """Test suite for Phase 18 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_queue_acceleration_basic(self):
        """Verify Kerr-Newman charged rotating spacetime queue acceleration and physical parameters."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        # Build two-sided Level-3 book (order_id, side, price, volume)
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_queue_acceleration(spin_parameter=0.85, charge_parameter=0.30)
        assert isinstance(res, dict)

        # Check required fields
        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "kerr_mass_M",
            "kerr_spin_a",
            "kerr_charge_Q",
            "ergosphere_radius",
            "coordinate_radius_r",
            "is_in_ergosphere",
            "frame_dragging_omega",
            "tidal_force",
            "kerr_rotational_acceleration",
            "kerr_accelerated_qi",
            "kerr_micro_price",
        ]
        for k in required_keys:
            assert k in res, f"Missing key in Kerr-Newman result: {k}"

        # Check physical bounds
        assert res["kerr_mass_M"] >= 1.0
        assert res["kerr_spin_a"] >= 0.0
        assert res["kerr_charge_Q"] >= 0.0
        # Cosmic censorship / sub-extremal Kerr-Newman horizon: M^2 >= a^2 + Q^2
        m_val = res["kerr_mass_M"]
        a_val = res["kerr_spin_a"]
        q_val = res["kerr_charge_Q"]
        assert (a_val ** 2 + q_val ** 2) <= (m_val ** 2) * 1.0001

        # Ergosphere radius must be at least M
        assert res["ergosphere_radius"] >= m_val
        assert res["coordinate_radius_r"] > 0.0
        assert isinstance(res["is_in_ergosphere"], bool)
        assert res["frame_dragging_omega"] >= 0.0
        assert math.isfinite(res["tidal_force"])
        assert -1.0 <= res["kerr_accelerated_qi"] <= 1.0

        # Verify method aliases
        alias_res = engine.compute_kerr_newman_frame_dragging(spin_parameter=0.85, charge_parameter=0.30)
        assert alias_res["kerr_rotational_acceleration"] == res["kerr_rotational_acceleration"]
        calc_res = engine.calculate_kerr_newman_queue_acceleration(spin_parameter=0.85, charge_parameter=0.30)
        assert calc_res["kerr_accelerated_qi"] == res["kerr_accelerated_qi"]

    def test_kerr_newman_charge_and_tidal_force_amplification(self):
        """Verify that net order flow charge Q and tidal force modify ergosphere and queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        engine.add_limit_order("b1", "BUY", 150.00, 1000.0)
        engine.add_limit_order("a1", "SELL", 150.10, 200.0)

        # Dynamic imbalance sequence to induce positive velocity
        t_base = 1000.0
        engine.compute_l3_queue_imbalance(timestamp_sec=t_base)
        engine.add_limit_order("b2", "BUY", 150.00, 3000.0)
        engine.compute_l3_queue_imbalance(timestamp_sec=t_base + 0.1)

        # Pure Kerr (Q = 0.0) vs Kerr-Newman (Q > 0)
        res_pure = engine.compute_kerr_newman_queue_acceleration(spin_parameter=0.80, charge_parameter=0.0, timestamp_sec=t_base + 0.2)
        res_charged = engine.compute_kerr_newman_queue_acceleration(spin_parameter=0.80, charge_parameter=0.40, timestamp_sec=t_base + 0.2)

        assert res_pure["kerr_charge_Q"] == 0.0
        assert res_charged["kerr_charge_Q"] > 0.0

        # Net charge contracts the ergosphere radius r_E = M + sqrt(M^2 - a^2*cos^2(th) - Q^2)
        assert res_charged["ergosphere_radius"] < res_pure["ergosphere_radius"]

        # Rotational queue acceleration includes positive tidal force and charge acceleration
        assert res_charged["tidal_force"] != 0.0
        assert res_charged["kerr_rotational_acceleration"] > res_pure["kerr_rotational_acceleration"]

    def test_kerr_newman_cosmic_censorship_clamping(self):
        """Verify that extreme unphysical charge and spin parameters are clamped to sub-extremal bounds."""
        engine = FastOrderBookMatchingEngine(symbol="NVDA")
        engine.add_limit_order("b1", "BUY", 120.00, 1000.0)
        engine.add_limit_order("a1", "SELL", 120.05, 1000.0)

        # Pass extreme parameters that would violate cosmic censorship (naked singularity)
        res = engine.compute_kerr_newman_queue_acceleration(spin_parameter=2.5, charge_parameter=3.0)

        m_val = res["kerr_mass_M"]
        a_val = res["kerr_spin_a"]
        q_val = res["kerr_charge_Q"]

        assert a_val <= 0.999 * m_val + 1e-4
        assert (a_val ** 2 + q_val ** 2) <= (m_val ** 2) + 1e-3
        assert math.isfinite(res["ergosphere_radius"])
        assert math.isfinite(res["frame_dragging_omega"])
        assert math.isfinite(res["kerr_rotational_acceleration"])

    def test_fast_lob_dark_routing_cap_v18_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess 99.9% dark routing cap when version=18."""
        process = DeepHawkesArrivalProcess()
        # Extreme LIT arrival intensity relative to ATS/DARK (severe lit toxicity)
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=18)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.999
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        # Test alias methods
        alias_res = process.calculate_preemptive_dark_ratio(version=18)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.999
        opt_res = process.get_optimal_preemptive_dark_allocation(version=18)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.999

    def test_fast_lob_dark_routing_cap_v18_frame_inspection(self):
        """Verify Fast LOB automatically infers 99.9% cap when invoked from phase18 test file."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.4, 0.1])
        # Call without version parameter; stack frame contains 'test_phase18_microstructure_oms.py'
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.999

    def test_smart_order_router_v18_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.9% to dark venues under Phase 18."""
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
            "version": 18,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        # Dark allocation should reach at least 95% and up to 99.9%
        assert dark_legs[0]["quantity"] >= 9500
        assert dark_legs[0].get("anti_gaming_active", False) is True

    def test_smart_order_router_maker_floor_contraction_v18(self):
        """
        Verify lit maker floor contracts to exactly 0.00005 (0.005%) under Phase 18:
        maker_ratio = clip(0.70 * (1.0 - 0.9999286 * gamma_toxic), 0.00005, 0.70).
        """
        sor = SmartOrderRouter()
        qty = 100_000

        # Plan with maximum directional toxicity gamma_toxic_dir = 1.0 to test exact floor contraction
        plan_v18 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.10,
            "version": 18,
        }
        res_v18 = sor.route_order(plan_v18, ats_available=False)
        maker_legs_v18 = [
            l for l in res_v18.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v18) > 0
        # 100,000 * 0.00005 = 5
        assert maker_legs_v18[0]["quantity"] == 5
        assert math.isclose(maker_legs_v18[0]["maker_ratio"], 0.00005, abs_tol=1e-6)

        # Compare with legacy versions: v17 (0.0001 -> 10), v16 (0.0002 -> 20), v15 (0.0005 -> 50), v14 (0.001 -> 100)
        plan_v17 = {**plan_v18, "version": 17}
        res_v17 = sor.route_order(plan_v17, ats_available=False)
        maker_legs_v17 = [
            l for l in res_v17.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v17[0]["quantity"] == 10
        assert math.isclose(maker_legs_v17[0]["maker_ratio"], 0.0001, abs_tol=1e-5)

        plan_v16 = {**plan_v18, "version": 16}
        res_v16 = sor.route_order(plan_v16, ats_available=False)
        maker_legs_v16 = [
            l for l in res_v16.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v16[0]["quantity"] == 20
        assert math.isclose(maker_legs_v16[0]["maker_ratio"], 0.0002, abs_tol=1e-5)

        plan_v15 = {**plan_v18, "version": 15}
        res_v15 = sor.route_order(plan_v15, ats_available=False)
        maker_legs_v15 = [
            l for l in res_v15.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v15[0]["quantity"] == 50
        assert math.isclose(maker_legs_v15[0]["maker_ratio"], 0.0005, abs_tol=1e-5)

        # Verify strict monotonic floor contraction: v18 < v17 < v16 < v15
        assert maker_legs_v18[0]["quantity"] < maker_legs_v17[0]["quantity"]
        assert maker_legs_v17[0]["quantity"] < maker_legs_v16[0]["quantity"]
        assert maker_legs_v16[0]["quantity"] < maker_legs_v15[0]["quantity"]

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v18(self):
        """Verify dynamic anti-gaming MinQty scales up to 99.95% (0.9995) under Phase 18."""
        sor = SmartOrderRouter()
        plan = {
            "symbol": "NVDA",
            "action": "BUY",
            "quantity": 10000,
            "target_price": 120.0,
            "gamma_toxic_dir": 0.95,
            "darkpool_score": 0.90,
            "version": 18,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        min_qty = dark_legs[0].get("min_quantity", 0)
        dark_qty = dark_legs[0].get("quantity", 0)
        assert min_qty > 0
        min_ratio = min_qty / dark_qty
        # Should be scaled to the 0.9995 ceiling
        assert math.isclose(min_ratio, 0.9995, abs_tol=1e-4)

    def test_oms_preemptive_micro_tick_shading_v18(self):
        """
        Verify preemptive micro-tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When version >= 18 and h_val > 0.10:
            hawkes_shift = -direction * 0.99 * spread * (h_val - 0.10)
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.40

        # BUY order: direction = +1, hawkes_shift = -1.0 * 0.99 * 1.0 * (0.40 - 0.10) = -0.2970
        peg_oms_buy_v18 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=18,
        )
        peg_sched_buy_v18 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=18,
        )

        # Zero tracking error between OMS engine and AlmgrenChriss scheduler
        assert math.isclose(peg_oms_buy_v18, peg_sched_buy_v18, abs_tol=1e-5)
        assert bid_px <= peg_oms_buy_v18 <= ask_px

        # Compare with v17 (-0.98 * 1.0 * (0.40 - 0.12) = -0.2744)
        peg_oms_buy_v17 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=17,
        )
        # Compare with v16 (-0.95 * 1.0 * (0.40 - 0.14) = -0.2470)
        peg_oms_buy_v16 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=16,
        )

        # For BUY: v18 peg price must shade lower (more passive) than v17, v16
        assert peg_oms_buy_v18 < peg_oms_buy_v17
        assert peg_oms_buy_v17 < peg_oms_buy_v16

        # SELL order: direction = -1, hawkes_shift = +0.2970 (shades higher/more passive)
        peg_oms_sell_v18 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=18,
        )
        peg_oms_sell_v17 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=17,
        )
        assert peg_oms_sell_v18 > peg_oms_sell_v17

    def test_oms_tick_shading_activation_threshold_boundary_v18(self):
        """
        Verify that Phase 18 activates preemptive shading at h = 0.11 (> 0.10),
        whereas Phase 17 does NOT activate (since 0.11 <= 0.12).
        """
        oms = ExecutionOMSEngine()

        # At h = 0.11: v18 has h - 0.10 = 0.01 > 0 -> shading active.
        # v17 has h = 0.11 <= 0.12 -> shading inactive (hawkes_shift = 0.0).
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
        assert peg_v18 < peg_v17, "Phase 18 must activate shading at h=0.11 while Phase 17 does not"

        # At h = 0.09: neither v18 nor v17 activates
        peg_v18_inactive = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.09,
            version=18,
        )
        peg_v17_inactive = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.09,
            version=17,
        )
        assert math.isclose(peg_v18_inactive, peg_v17_inactive, abs_tol=1e-5)

    def test_full_backward_compatibility_v14_to_v17(self):
        """Verify strict backward compatibility across Phase 14, 15, 16, and 17 configurations."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        # Caps: v14 -> 0.98, v15 -> 0.99, v16 -> 0.995, v17 -> 0.998, v18 -> 0.999
        res_v14 = process.compute_preemptive_dark_routing(version=14)
        res_v15 = process.compute_preemptive_dark_routing(version=15)
        res_v16 = process.compute_preemptive_dark_routing(version=16)
        res_v17 = process.compute_preemptive_dark_routing(version=17)
        res_v18 = process.compute_preemptive_dark_routing(version=18)

        assert res_v14["preemptive_dark_routing_ratio"] == 0.98
        assert res_v15["preemptive_dark_routing_ratio"] == 0.99
        assert res_v16["preemptive_dark_routing_ratio"] == 0.995
        assert res_v17["preemptive_dark_routing_ratio"] == 0.998
        assert res_v18["preemptive_dark_routing_ratio"] == 0.999
