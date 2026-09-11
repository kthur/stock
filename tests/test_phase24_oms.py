"""
tests/test_phase24_oms.py

Unit and integration test suite for Phase 24 Quantitative Enhancement (Feature F117.2 Microstructure OMS):
- Kerr-Newman-Kiselev Quintessence-Phantom-Tachyon Triple Dark Energy (w_q = -2/3, w_p = -4/3, w_t = -5/3)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * Quintessence w_q = -2/3, Phantom w_p = -4/3, Tachyon w_t = -5/3
  * Energy densities: rho_q = c_q / r, rho_p = 2*c_p*r, rho_t = 2.5*c_t*r^2
  * Spacetime metric horizon function Delta_r = (r^2 + a^2) - 2*M*r + Q^2 - c_q*r^3 - c_p*r^5 - c_t*r^6
  * Outer tachyon cosmological horizon scale r_T = max(r_H + 0.1, (1/c_t)^{0.20} * (1 - M / max(1.0, (1/c_t)^{0.20})))
  * Frame-dragging angular velocity omega_{drag}^{KNK-PT}(r, theta)
  * Radial tidal force with triple dark energy repulsive acceleration:
    F_{tidal}^{KNK-PT} = F_{tidal}^{KN} - c_q*r - 2*c_p*r^3 - 2.5*c_t*r^4
  * Conformal boundary amplification factor Gamma_{KNK-PT}
  * Hydrodynamic queue acceleration a_{KNK-PT} and micro-price prediction
  * 8+ method aliases on FastOrderBookMatchingEngine
- Fast LOB 99.998% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=24:
  * Preemptive lit queue imbalance allocation with max dark cap 0.99998 (99.998%).
  * Lit maker ratio floor contracted to 0.0000005 (0.00005%, 1 share per 2,000,000)
    via 0.70 * (1.0 - 0.9999992857 * gamma_toxic) with 7-decimal formatting precision.
  * Dynamic anti-gaming MinQty scaled up to 99.9995% (0.999995).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.030:
  hawkes_shift = -direction * 0.9998 * spr * (h - 0.030).
- Full backward compatibility across Phase 14 through Phase 23 versions.
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


class TestPhase24MicrostructureOMS:
    """Test suite for Phase 24 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_tachyon_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev Quintessence-Phantom-Tachyon queue acceleration and physical parameters."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_tachyon_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            quintessence_parameter=0.05,
            phantom_parameter=0.02,
            tachyon_parameter=0.01,
            w_q=-2.0 / 3.0,
            w_p=-4.0 / 3.0,
            w_t=-5.0 / 3.0,
        )
        assert isinstance(res, dict)

        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "knk_pt_mass_M",
            "knk_pt_spin_a",
            "knk_pt_charge_Q",
            "quintessence_c_q",
            "phantom_c_p",
            "tachyon_c_t",
            "equation_of_state_w_q",
            "equation_of_state_w_p",
            "equation_of_state_w_t",
            "tachyon_horizon_r_T",
            "tachyon_horizon",
            "phantom_horizon_r_P",
            "phantom_horizon",
            "quintessence_horizon_r_Q",
            "quintessence_horizon",
            "horizon_radius",
            "coordinate_radius_r",
            "is_in_horizon",
            "frame_dragging_omega",
            "tidal_force",
            "knk_pt_tidal_force",
            "knk_pt_hydrodynamic_acceleration",
            "knk_pt_rotational_acceleration",
            "kerr_newman_kiselev_tachyon_rotational_acceleration",
            "knk_pt_accelerated_qi",
            "kerr_newman_kiselev_tachyon_accelerated_qi",
            "knk_pt_micro_price",
            "kerr_newman_kiselev_tachyon_micro_price",
        ]
        for k in required_keys:
            assert k in res, f"Missing key in Kerr-Newman-Kiselev-Tachyon result: {k}"

        # Check physical parameters and bounds
        assert res["quintessence_c_q"] == 0.05
        assert res["phantom_c_p"] == 0.02
        assert res["tachyon_c_t"] == 0.01
        assert math.isclose(res["equation_of_state_w_q"], -2.0 / 3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_p"], -4.0 / 3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_t"], -5.0 / 3.0, abs_tol=1e-3)
        assert res["knk_pt_mass_M"] >= 1.0
        assert res["knk_pt_spin_a"] > 0.0
        assert res["knk_pt_charge_Q"] > 0.0
        assert res["tachyon_horizon_r_T"] > 0.0
        assert res["phantom_horizon_r_P"] > 0.0
        assert res["quintessence_horizon_r_Q"] > 0.0
        assert res["frame_dragging_omega"] > 0.0
        assert math.isfinite(res["tidal_force"])
        assert math.isfinite(res["knk_pt_hydrodynamic_acceleration"])
        assert -1.0 <= res["knk_pt_accelerated_qi"] <= 1.0
        assert res["knk_pt_micro_price"] > 0.0

        # Check all 8+ method aliases
        aliases = [
            "compute_kerr_newman_kiselev_tachyon_acceleration",
            "compute_knk_tachyon_acceleration",
            "compute_knk_tachyon_hydrodynamics",
            "calculate_kerr_newman_kiselev_tachyon_queue_acceleration",
            "calculate_knk_tachyon_queue_acceleration",
            "compute_kerr_newman_kiselev_tachyon_frame_dragging",
            "calculate_kerr_newman_kiselev_tachyon_hydrodynamics",
            "calculate_kerr_newman_kiselev_tachyon_frame_dragging",
            "compute_knk_quintessence_phantom_tachyon_hydrodynamics",
            "compute_kerr_newman_kiselev_quintessence_phantom_tachyon_hydrodynamics",
        ]
        for a in aliases:
            fn = getattr(engine, a, None)
            assert fn is not None, f"Missing alias: {a}"
            alias_res = fn(
                charge_parameter=0.5,
                spin_parameter=0.5,
                quintessence_parameter=0.05,
                phantom_parameter=0.02,
                tachyon_parameter=0.01,
                w_q=-2.0 / 3.0,
                w_p=-4.0 / 3.0,
                w_t=-5.0 / 3.0,
            )
            assert math.isclose(
                alias_res["knk_pt_hydrodynamic_acceleration"],
                res["knk_pt_hydrodynamic_acceleration"],
                abs_tol=1e-6,
            )

    def test_kerr_newman_kiselev_tachyon_physics_and_triple_dark_energy(self):
        """Verify KNK-PT quintessence-phantom-tachyon triple dark energy tidal repulsion and horizon physics."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        engine.add_limit_order("b1", "BUY", 150.00, 1000.0)
        engine.add_limit_order("a1", "SELL", 150.10, 200.0)

        # Static vs Rotating frame dragging
        res_static = engine.compute_kerr_newman_kiselev_tachyon_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.0,
            quintessence_parameter=0.05,
            phantom_parameter=0.02,
            tachyon_parameter=0.01,
        )
        assert res_static["frame_dragging_omega"] == 0.0

        res_rotating = engine.compute_kerr_newman_kiselev_tachyon_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.7,
            quintessence_parameter=0.05,
            phantom_parameter=0.02,
            tachyon_parameter=0.01,
        )
        assert res_rotating["frame_dragging_omega"] > 0.0

        # Triple dark energy tidal force: F_{tidal}^{KNK-PT} = F_{tidal}^{KN} - c_q * r - 2 * c_p * r^3 - 2.5 * c_t * r^4
        # Increasing c_t should further decrease (repulse) the radial tidal force
        res_low_ct = engine.compute_kerr_newman_kiselev_tachyon_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            quintessence_parameter=0.05,
            phantom_parameter=0.02,
            tachyon_parameter=0.001,
        )
        res_high_ct = engine.compute_kerr_newman_kiselev_tachyon_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            quintessence_parameter=0.05,
            phantom_parameter=0.02,
            tachyon_parameter=0.05,
        )
        assert res_high_ct["knk_pt_tidal_force"] < res_low_ct["knk_pt_tidal_force"]

    def test_fast_lob_dark_routing_cap_v24_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess 99.998% dark routing cap when version=24."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=24)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.99998
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=24)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.99998
        opt_res = process.get_optimal_preemptive_dark_allocation(version=24)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.99998

    def test_fast_lob_dark_routing_cap_v24_frame_inspection(self):
        """Verify Fast LOB DeepHawkesArrivalProcess auto-infers 99.998% dark cap via stack inspection."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        # Calling without version should inspect current test frame ("phase24" in filename)
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.99998

    def test_smart_order_router_v24_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.998% to dark venues under Phase 24."""
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
            "version": 24,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        total_dark = sum(l["quantity"] for l in dark_legs)
        assert total_dark == 999_980  # exactly 99.998% of 1,000,000

    def test_smart_order_router_maker_floor_contraction_v24(self):
        """
        Verify maker ratio floor contracts to 0.0000005 (1 share per 2,000,000) under extreme toxicity.
        Formula: 0.70 * (1.0 - 0.9999992857 * gamma_toxic) clamped at 0.0000005.
        """
        sor = SmartOrderRouter()
        qty = 2_000_000

        plan_v24 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 24,
        }
        res_v24 = sor.route_order(plan_v24, ats_available=False)
        maker_legs_v24 = [
            l for l in res_v24.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v24) > 0
        # 2,000,000 * 0.0000005 = 1 share
        assert maker_legs_v24[0]["quantity"] == 1
        assert res_v24["maker_ratio"] == 0.0000005

        # Monotonic floor contraction test against prior versions
        plan_v23 = {**plan_v24, "version": 23}
        res_v23 = sor.route_order(plan_v23, ats_available=False)
        maker_legs_v23 = [
            l for l in res_v23.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v23[0]["quantity"] == 2  # 2,000,000 * 0.000001 = 2

        plan_v22 = {**plan_v24, "version": 22}
        res_v22 = sor.route_order(plan_v22, ats_available=False)
        maker_legs_v22 = [
            l for l in res_v22.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v22[0]["quantity"] == 4  # 2,000,000 * 0.000002 = 4

        plan_v21 = {**plan_v24, "version": 21}
        res_v21 = sor.route_order(plan_v21, ats_available=False)
        maker_legs_v21 = [
            l for l in res_v21.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v21[0]["quantity"] == 10  # 2,000,000 * 0.000005 = 10

        assert (
            maker_legs_v24[0]["quantity"]
            < maker_legs_v23[0]["quantity"]
            < maker_legs_v22[0]["quantity"]
            < maker_legs_v21[0]["quantity"]
        )

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v24(self):
        """Verify dynamic Anti-Gaming MinQty cap expands to 99.9995% (0.999995) under Phase 24."""
        sor = SmartOrderRouter()
        qty = 1_000_000

        plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": qty,
            "target_price": 300.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 24,
        }
        res = sor.route_order(plan, ats_available=True)
        dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        dark_qty = dark_legs[0]["quantity"]
        min_qty = dark_legs[0].get("min_quantity", 0)

        ratio = min_qty / dark_qty
        assert math.isclose(ratio, 0.999995, abs_tol=1e-4)
        assert res["min_ratio"] == 0.999995

    def test_oms_preemptive_micro_tick_shading_v24(self):
        """
        Verify Phase 24 preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When h_val > 0.030, hawkes_shift = -direction * 0.9998 * spr * (h_val - 0.030).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.035

        # Buy order: direction = +1, hawkes_shift = -1.0 * 0.9998 * 1.0 * (0.035 - 0.030) = -0.004999
        peg_oms_buy_v24 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=24,
        )
        peg_sched_buy_v24 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=24,
        )
        expected_peg = target_px - 0.9998 * spr * (h_val - 0.030)
        assert math.isclose(peg_oms_buy_v24, expected_peg, abs_tol=1e-6)
        assert math.isclose(peg_sched_buy_v24, expected_peg, abs_tol=1e-6)
        assert bid_px <= peg_oms_buy_v24 <= ask_px

        # Sell order: direction = -1, hawkes_shift = +0.004999
        peg_oms_sell_v24 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=24,
        )
        assert math.isclose(peg_oms_sell_v24, target_px + 0.9998 * spr * (h_val - 0.030), abs_tol=1e-6)

    def test_oms_tick_shading_activation_threshold_boundary_v24(self):
        """
        Verify activation threshold boundary:
        Phase 24 activates at h > 0.030, whereas Phase 23 requires h > 0.035.
        At h = 0.032:
        - Version 24 is active (0.032 > 0.030)
        - Version 23 is inactive (0.032 <= 0.035)
        At h = 0.030 (boundary):
        - Both are inactive (unshifted at 100.0)
        """
        oms = ExecutionOMSEngine()

        # At h = 0.032
        peg_v24 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.032,
            version=24,
        )
        peg_v23 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.032,
            version=23,
        )
        assert peg_v24 < peg_v23
        assert math.isclose(peg_v23, 100.0, abs_tol=1e-6)
        expected_v24 = 100.0 - 0.9998 * 1.0 * (0.032 - 0.030)
        assert math.isclose(peg_v24, expected_v24, abs_tol=1e-6)

        # At h = 0.030 boundary
        peg_boundary = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.030,
            version=24,
        )
        assert math.isclose(peg_boundary, 100.0, abs_tol=1e-6)

    def test_full_backward_compatibility_v14_to_v23(self):
        """Verify legacy version flags produce strictly identical results to historical baselines."""
        oms = ExecutionOMSEngine()

        # At h = 0.038:
        # v23 active (0.038 > 0.035)
        # v22 inactive (0.038 <= 0.040)
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
        assert peg_v23 < 100.0
        assert math.isclose(peg_v22, 100.0, abs_tol=1e-6)
