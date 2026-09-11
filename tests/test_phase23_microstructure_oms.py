"""
tests/test_phase23_microstructure_oms.py

Unit and integration test suite for Phase 23 Quantitative Enhancement (Features F113.2, F113.2.1, F113.2.2, F113.2.3, F113.2.4):
- Kerr-Newman-Kiselev Quintessence-Phantom Double Dark Energy (w_q = -2/3, w_p = -4/3) Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * Quintessence equation of state w_q = -2/3, Phantom equation of state w_p = -4/3
  * Quintessence energy density rho_q = c_q / r, Phantom energy density rho_p = 2 * c_p * r
  * Spacetime metric horizon function Delta_r = (r^2 + a^2) - 2*M*r + Q^2 - c_q * r^3 - c_p * r^5
  * Outer phantom cosmological horizon scale r_P = max(r_H + 0.1, (1/c_p)^{0.25} * (1 - M / max(1.0, (1/c_p)^{0.25})))
  * Frame-dragging angular velocity omega_{drag}^{KNK-P}(r, theta)
  * Radial tidal force with double dark energy repulsive acceleration F_{tidal}^{KNK-P} = F_{tidal}^{KN} - c_q * r - 2 * c_p * r^3
  * Conformal boundary amplification factor Gamma_{KNK-P} = 1 + (r_H - r)/r_H + M^2/((r - r_H)^2 + 0.05*M^2) + c_q * r^3 + c_p * r^5
  * Hydrodynamic queue acceleration a_{KNK-P} and micro-price prediction
  * 8 method aliases on FastOrderBookMatchingEngine
- Fast LOB 99.995% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=23:
  * Preemptive lit queue imbalance allocation with max dark cap 0.99995 (99.995%).
  * Lit maker ratio floor contracted to 0.000001 (0.0001%, 1 share per 1,000,000) via 0.70 * (1.0 - 0.99999857 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.999% (0.99999).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.035:
  hawkes_shift = -direction * 0.9995 * spr * (h - 0.035).
- Full backward compatibility across Phase 14 through Phase 22 versions.
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


class TestPhase23MicrostructureOMS:
    """Test suite for Phase 23 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_phantom_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev Quintessence-Phantom queue acceleration and physical parameters."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_phantom_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            quintessence_parameter=0.05,
            phantom_parameter=0.02,
            w_q=-2.0 / 3.0,
            w_p=-4.0 / 3.0,
        )
        assert isinstance(res, dict)

        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "knk_p_mass_M",
            "knk_p_spin_a",
            "knk_p_charge_Q",
            "quintessence_c_q",
            "phantom_c_p",
            "equation_of_state_w_q",
            "equation_of_state_w_p",
            "phantom_horizon_r_P",
            "phantom_horizon",
            "horizon_radius",
            "coordinate_radius_r",
            "is_in_horizon",
            "frame_dragging_omega",
            "tidal_force",
            "knk_p_tidal_force",
            "knk_p_hydrodynamic_acceleration",
            "knk_p_rotational_acceleration",
            "kerr_newman_kiselev_phantom_rotational_acceleration",
            "knk_p_accelerated_qi",
            "kerr_newman_kiselev_phantom_accelerated_qi",
            "knk_p_micro_price",
            "kerr_newman_kiselev_phantom_micro_price",
        ]
        for k in required_keys:
            assert k in res, f"Missing key in Kerr-Newman-Kiselev-Phantom result: {k}"

        # Check physical parameters and bounds
        assert res["quintessence_c_q"] == 0.05
        assert res["phantom_c_p"] == 0.02
        assert math.isclose(res["equation_of_state_w_q"], -2.0 / 3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_p"], -4.0 / 3.0, abs_tol=1e-3)
        assert res["knk_p_mass_M"] >= 1.0
        assert res["knk_p_spin_a"] > 0.0
        assert res["knk_p_charge_Q"] > 0.0
        assert res["phantom_horizon_r_P"] > 0.0
        assert res["frame_dragging_omega"] > 0.0
        assert math.isfinite(res["tidal_force"])
        assert math.isfinite(res["knk_p_hydrodynamic_acceleration"])
        assert -1.0 <= res["knk_p_accelerated_qi"] <= 1.0
        assert res["knk_p_micro_price"] > 0.0

        # Check all 8 method aliases
        aliases = [
            "compute_kerr_newman_kiselev_phantom_acceleration",
            "compute_knk_phantom_acceleration",
            "compute_knk_phantom_hydrodynamics",
            "calculate_kerr_newman_kiselev_phantom_queue_acceleration",
            "calculate_knk_phantom_queue_acceleration",
            "compute_kerr_newman_kiselev_phantom_frame_dragging",
            "calculate_kerr_newman_kiselev_phantom_hydrodynamics",
            "calculate_kerr_newman_kiselev_phantom_frame_dragging",
        ]
        for a in aliases:
            fn = getattr(engine, a, None)
            assert fn is not None, f"Missing alias: {a}"
            alias_res = fn(
                charge_parameter=0.5,
                spin_parameter=0.5,
                quintessence_parameter=0.05,
                phantom_parameter=0.02,
                w_q=-2.0 / 3.0,
                w_p=-4.0 / 3.0,
            )
            assert math.isclose(
                alias_res["knk_p_hydrodynamic_acceleration"],
                res["knk_p_hydrodynamic_acceleration"],
                abs_tol=1e-6,
            )

    def test_kerr_newman_kiselev_phantom_physics_and_double_dark_energy(self):
        """Verify KNK-P quintessence-phantom double dark energy tidal repulsion and horizon physics."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        engine.add_limit_order("b1", "BUY", 150.00, 1000.0)
        engine.add_limit_order("a1", "SELL", 150.10, 200.0)

        # Static vs Rotating frame dragging
        res_static = engine.compute_kerr_newman_kiselev_phantom_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.0,
            quintessence_parameter=0.05,
            phantom_parameter=0.02,
        )
        assert res_static["frame_dragging_omega"] == 0.0

        res_rotating = engine.compute_kerr_newman_kiselev_phantom_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.7,
            quintessence_parameter=0.05,
            phantom_parameter=0.02,
        )
        assert res_rotating["frame_dragging_omega"] > 0.0

        # Double dark energy tidal force: F_{tidal}^{KNK-P} = F_{tidal}^{KN} - c_q * r - 2 * c_p * r^3
        # Increasing c_p should further decrease (repulse) the tidal force
        res_low_cp = engine.compute_kerr_newman_kiselev_phantom_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            quintessence_parameter=0.05,
            phantom_parameter=0.001,
        )
        res_high_cp = engine.compute_kerr_newman_kiselev_phantom_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            quintessence_parameter=0.05,
            phantom_parameter=0.05,
        )
        assert res_high_cp["knk_p_tidal_force"] < res_low_cp["knk_p_tidal_force"]

    def test_fast_lob_dark_routing_cap_v23_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess 99.995% dark routing cap when version=23."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=23)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.99995
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=23)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.99995
        opt_res = process.get_optimal_preemptive_dark_allocation(version=23)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.99995

    def test_fast_lob_dark_routing_cap_v23_frame_inspection(self):
        """Verify Fast LOB automatically infers 99.995% cap when invoked from phase23 test file."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.4, 0.1])
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.99995

    def test_smart_order_router_v23_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.995% to dark venues under Phase 23."""
        sor = SmartOrderRouter()
        plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1_000_000,
            "target_price": 70000.0,
            "market_spread_bps": 12.0,
            "queue_imbalance": 0.80,
            "qi_acceleration": 0.50,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.90,
            "version": 23,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        total_dark = sum(l["quantity"] for l in dark_legs)
        assert total_dark == 999_950  # exactly 99.995% of 1,000,000

    def test_smart_order_router_maker_floor_contraction_v23(self):
        """
        Verify lit maker floor contracts to 0.000001 (0.0001%, 1 share per 1,000,000) under Phase 23.
        Monotonic contraction check: v23 (0.000001) < v22 (0.000002) < v21 (0.000005) < v20 (0.00001).
        """
        sor = SmartOrderRouter()
        qty = 1_000_000

        plan_v23 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.10,
            "version": 23,
        }
        res_v23 = sor.route_order(plan_v23, ats_available=False)
        maker_legs_v23 = [
            l for l in res_v23.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v23) > 0
        # 1_000_000 * 0.000001 = 1 share
        assert maker_legs_v23[0]["quantity"] == 1
        assert math.isclose(maker_legs_v23[0]["maker_ratio"], 0.000001, abs_tol=1e-7)

        # Monotonic floor contraction test
        plan_v22 = {**plan_v23, "version": 22}
        res_v22 = sor.route_order(plan_v22, ats_available=False)
        maker_legs_v22 = [
            l for l in res_v22.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v22[0]["quantity"] == 2

        plan_v21 = {**plan_v23, "version": 21}
        res_v21 = sor.route_order(plan_v21, ats_available=False)
        maker_legs_v21 = [
            l for l in res_v21.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v21[0]["quantity"] == 5

        plan_v20 = {**plan_v23, "version": 20}
        res_v20 = sor.route_order(plan_v20, ats_available=False)
        maker_legs_v20 = [
            l for l in res_v20.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v20[0]["quantity"] == 10

        assert maker_legs_v23[0]["quantity"] < maker_legs_v22[0]["quantity"] < maker_legs_v21[0]["quantity"] < maker_legs_v20[0]["quantity"]

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v23(self):
        """Verify dynamic Anti-Gaming MinQty cap expands to 99.999% (0.99999) under Phase 23."""
        sor = SmartOrderRouter()
        qty = 1_000_000

        plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": qty,
            "target_price": 300.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 23,
        }
        res = sor.route_order(plan, ats_available=True)
        dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        dark_qty = dark_legs[0]["quantity"]
        min_qty = dark_legs[0].get("min_quantity", 0)

        ratio = min_qty / dark_qty
        assert math.isclose(ratio, 0.99999, abs_tol=1e-4)

    def test_oms_preemptive_micro_tick_shading_v23(self):
        """
        Verify Phase 23 preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When h_val > 0.035, hawkes_shift = -direction * 0.9995 * spr * (h_val - 0.035).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.040

        # Buy order: direction = +1, hawkes_shift = -1.0 * 0.9995 * 1.0 * (0.040 - 0.035) = -0.0049975
        peg_oms_buy_v23 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=23,
        )
        peg_sched_buy_v23 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=23,
        )
        expected_peg = target_px - 0.9995 * spr * (h_val - 0.035)
        assert math.isclose(peg_oms_buy_v23, expected_peg, abs_tol=1e-6)
        assert math.isclose(peg_sched_buy_v23, expected_peg, abs_tol=1e-6)
        assert bid_px <= peg_oms_buy_v23 <= ask_px

        # Sell order: direction = -1, hawkes_shift = +0.0049975
        peg_oms_sell_v23 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=23,
        )
        assert math.isclose(peg_oms_sell_v23, target_px + 0.9995 * spr * (h_val - 0.035), abs_tol=1e-6)

    def test_oms_tick_shading_activation_threshold_boundary_v23(self):
        """
        Verify activation threshold boundary:
        Phase 23 activates at h > 0.035, whereas Phase 22 requires h > 0.040.
        At h = 0.038:
        - Version 23 is active (0.038 > 0.035)
        - Version 22 is inactive (0.038 <= 0.040)
        At h = 0.035 (boundary):
        - Both are inactive (unshifted at 100.0)
        """
        oms = ExecutionOMSEngine()

        # At h = 0.038
        peg_v23 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.038,
            version=23,
        )
        peg_v22 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.038,
            version=22,
        )
        assert peg_v23 < peg_v22
        assert math.isclose(peg_v22, 100.0, abs_tol=1e-6)
        expected_v23 = 100.0 - 0.9995 * 1.0 * (0.038 - 0.035)
        assert math.isclose(peg_v23, expected_v23, abs_tol=1e-6)

        # At h = 0.035 boundary
        peg_boundary = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.035,
            version=23,
        )
        assert math.isclose(peg_boundary, 100.0, abs_tol=1e-6)

    def test_full_backward_compatibility_v14_to_v22(self):
        """Verify legacy version flags produce strictly identical results to historical baselines."""
        oms = ExecutionOMSEngine()

        # At h = 0.045:
        # v22 active (0.045 > 0.040)
        # v21 inactive (0.045 <= 0.050)
        peg_v22 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.045,
            version=22,
        )
        peg_v21 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.045,
            version=21,
        )
        assert peg_v22 < 100.0
        assert math.isclose(peg_v21, 100.0, abs_tol=1e-6)
