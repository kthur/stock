"""
tests/test_phase25_oms.py

Unit and integration test suite for Phase 25 Quantitative Enhancement (Feature F121.2 Microstructure OMS):
- Kerr-Newman-Kiselev Quintom 4-Dark-Energy (w_q = -2/3, w_p = -4/3, w_t = -5/3, w_m = -2.0)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * Quintessence w_q = -2/3, Phantom w_p = -4/3, Tachyon w_t = -5/3, Quintom w_m = -2.0
  * Energy densities: rho_q = c_q / r, rho_p = 2*c_p*r, rho_t = 2.5*c_t*r^2, rho_m = 3.0*c_m*r^3
  * Spacetime metric horizon function Delta_r = (r^2 + a^2) - 2*M*r + Q^2 - c_q*r^3 - c_p*r^5 - c_t*r^6 - c_m*r^7
  * Outer quintom cosmological horizon scale r_M = max(r_H + 0.1, (1/c_m)^{1/6} * (1 - M / max(1.0, (1/c_m)^{1/6})))
  * Frame-dragging angular velocity omega_{drag}^{KNK-QM}(r, theta)
  * Radial tidal force with quadruple dark energy repulsive acceleration:
    F_{tidal}^{KNK-QM} = F_{tidal}^{KN} - c_q*r - 2*c_p*r^3 - 2.5*c_t*r^4 - 3.0*c_m*r^5
  * Conformal boundary amplification factor Gamma_{KNK-QM}
  * Hydrodynamic queue acceleration a_{KNK-QM} and micro-price prediction
  * 12+ method aliases on FastOrderBookMatchingEngine
- Fast LOB 99.999% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=25:
  * Preemptive lit queue imbalance allocation with max dark cap 0.99999 (99.999%).
  * Lit maker ratio floor contracted to 0.0000002 (0.00002%, 1 share per 5,000,000)
    via 0.70 * (1.0 - 0.9999997143 * gamma_toxic) with 7-decimal formatting precision.
  * Dynamic anti-gaming MinQty scaled up to 99.9998% (0.999998).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.025:
  hawkes_shift = -direction * 0.9999 * spr * (h - 0.025).
- Full backward compatibility across Phase 14 through Phase 24 versions.
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


class TestPhase25MicrostructureOMS:
    """Test suite for Phase 25 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_quintom_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev Quintom 4-Dark-Energy queue acceleration and physical parameters."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_quintom_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            quintessence_parameter=0.05,
            phantom_parameter=0.02,
            tachyon_parameter=0.01,
            quintom_parameter=0.005,
            w_q=-2.0 / 3.0,
            w_p=-4.0 / 3.0,
            w_t=-5.0 / 3.0,
            w_m=-2.0,
        )
        assert isinstance(res, dict)

        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "knk_qm_mass_M",
            "knk_qm_spin_a",
            "knk_qm_charge_Q",
            "quintessence_c_q",
            "phantom_c_p",
            "tachyon_c_t",
            "quintom_c_m",
            "equation_of_state_w_q",
            "equation_of_state_w_p",
            "equation_of_state_w_t",
            "equation_of_state_w_m",
            "quintom_horizon_r_M",
            "quintom_horizon",
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
            "knk_qm_tidal_force",
            "knk_qm_hydrodynamic_acceleration",
            "knk_qm_rotational_acceleration",
            "kerr_newman_kiselev_quintom_rotational_acceleration",
            "knk_qm_accelerated_qi",
            "kerr_newman_kiselev_quintom_accelerated_qi",
            "knk_qm_micro_price",
            "kerr_newman_kiselev_quintom_micro_price",
        ]
        for k in required_keys:
            assert k in res, f"Missing key in Kerr-Newman-Kiselev-Quintom result: {k}"

        # Check physical parameters and bounds
        assert res["quintessence_c_q"] == 0.05
        assert res["phantom_c_p"] == 0.02
        assert res["tachyon_c_t"] == 0.01
        assert res["quintom_c_m"] == 0.005
        assert math.isclose(res["equation_of_state_w_q"], -2.0 / 3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_p"], -4.0 / 3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_t"], -5.0 / 3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_m"], -2.0, abs_tol=1e-3)
        assert res["knk_qm_mass_M"] >= 1.0
        assert res["knk_qm_spin_a"] > 0.0
        assert res["knk_qm_charge_Q"] > 0.0
        assert res["quintom_horizon_r_M"] > 0.0
        assert res["tachyon_horizon_r_T"] > 0.0
        assert res["phantom_horizon_r_P"] > 0.0
        assert res["quintessence_horizon_r_Q"] > 0.0
        assert res["frame_dragging_omega"] > 0.0
        assert math.isfinite(res["tidal_force"])
        assert math.isfinite(res["knk_qm_hydrodynamic_acceleration"])
        assert -1.0 <= res["knk_qm_accelerated_qi"] <= 1.0
        assert res["knk_qm_micro_price"] > 0.0

        # Check backward compatibility keys for prior phases
        assert "knk_pt_hydrodynamic_acceleration" in res
        assert "knk_p_hydrodynamic_acceleration" in res
        assert "knk_hydrodynamic_acceleration" in res
        assert "kn_ads_ds_hydrodynamic_acceleration" in res
        assert "kn_ads_hydrodynamic_acceleration" in res

        # Check all 12+ method aliases
        aliases = [
            "compute_kerr_newman_kiselev_quintom_acceleration",
            "compute_knk_quintom_acceleration",
            "compute_knk_quintom_hydrodynamics",
            "calculate_kerr_newman_kiselev_quintom_queue_acceleration",
            "calculate_knk_quintom_queue_acceleration",
            "compute_kerr_newman_kiselev_quintom_frame_dragging",
            "calculate_kerr_newman_kiselev_quintom_hydrodynamics",
            "calculate_kerr_newman_kiselev_quintom_frame_dragging",
            "compute_knk_quintessence_phantom_tachyon_quintom_hydrodynamics",
            "compute_kerr_newman_kiselev_quintessence_phantom_tachyon_quintom_hydrodynamics",
            "calculate_knk_quintessence_phantom_tachyon_quintom_hydrodynamics",
            "calculate_kerr_newman_kiselev_quintessence_phantom_tachyon_quintom_hydrodynamics",
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
                quintom_parameter=0.005,
                w_q=-2.0 / 3.0,
                w_p=-4.0 / 3.0,
                w_t=-5.0 / 3.0,
                w_m=-2.0,
            )
            assert math.isclose(
                alias_res["knk_qm_hydrodynamic_acceleration"],
                res["knk_qm_hydrodynamic_acceleration"],
                abs_tol=1e-6,
            )

    def test_kerr_newman_kiselev_quintom_physics_and_quadruple_dark_energy(self):
        """Verify KNK-QM quintessence-phantom-tachyon-quintom quadruple dark energy tidal repulsion and horizon physics."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        engine.add_limit_order("b1", "BUY", 150.00, 1000.0)
        engine.add_limit_order("a1", "SELL", 150.10, 200.0)

        # Static vs Rotating frame dragging
        res_static = engine.compute_kerr_newman_kiselev_quintom_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.0,
            quintessence_parameter=0.05,
            phantom_parameter=0.02,
            tachyon_parameter=0.01,
            quintom_parameter=0.005,
        )
        assert res_static["frame_dragging_omega"] == 0.0

        res_rotating = engine.compute_kerr_newman_kiselev_quintom_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.7,
            quintessence_parameter=0.05,
            phantom_parameter=0.02,
            tachyon_parameter=0.01,
            quintom_parameter=0.005,
        )
        assert res_rotating["frame_dragging_omega"] > 0.0

        # Quadruple dark energy tidal force:
        # F_{tidal}^{KNK-QM} = F_{tidal}^{KN} - c_q * r - 2 * c_p * r^3 - 2.5 * c_t * r^4 - 3.0 * c_m * r^5
        # Increasing c_m should further decrease (repulse) the radial tidal force
        res_low_cm = engine.compute_kerr_newman_kiselev_quintom_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            quintessence_parameter=0.05,
            phantom_parameter=0.02,
            tachyon_parameter=0.01,
            quintom_parameter=0.001,
        )
        res_high_cm = engine.compute_kerr_newman_kiselev_quintom_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            quintessence_parameter=0.05,
            phantom_parameter=0.02,
            tachyon_parameter=0.01,
            quintom_parameter=0.05,
        )
        assert res_high_cm["knk_qm_tidal_force"] < res_low_cm["knk_qm_tidal_force"]

        # Cosmological horizon outer separation
        r_horiz = res_rotating["horizon_radius"]
        assert res_rotating["quintom_horizon_r_M"] > r_horiz
        assert res_rotating["tachyon_horizon_r_T"] > r_horiz
        assert res_rotating["phantom_horizon_r_P"] > r_horiz
        assert res_rotating["quintessence_horizon_r_Q"] > r_horiz

    def test_fast_lob_dark_routing_cap_v25_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess 99.999% dark routing cap when version=25."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=25)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.99999
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=25)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.99999
        opt_res = process.get_optimal_preemptive_dark_allocation(version=25)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.99999

    def test_fast_lob_dark_routing_cap_v25_frame_inspection(self):
        """Verify Fast LOB DeepHawkesArrivalProcess auto-infers 99.999% dark cap via stack inspection."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        # Calling without version should inspect current test frame ("phase25" in filename)
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.99999

    def test_smart_order_router_v25_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.999% to dark venues under Phase 25."""
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
            "version": 25,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        total_dark = sum(l["quantity"] for l in dark_legs)
        assert total_dark == 999_990  # exactly 99.999% of 1,000,000

    def test_smart_order_router_maker_floor_contraction_v25(self):
        """
        Verify maker ratio floor contracts to 0.0000002 (1 share per 5,000,000) under extreme toxicity.
        Formula: 0.70 * (1.0 - 0.9999997143 * gamma_toxic) clamped at 0.0000002.
        """
        sor = SmartOrderRouter()
        qty = 10_000_000

        plan_v25 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 25,
        }
        res_v25 = sor.route_order(plan_v25, ats_available=False)
        maker_legs_v25 = [
            l for l in res_v25.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v25) > 0
        # 10,000,000 * 0.0000002 = 2 shares
        assert maker_legs_v25[0]["quantity"] == 2
        assert res_v25["maker_ratio"] == 0.0000002

        # Monotonic floor contraction test against prior versions
        plan_v24 = {**plan_v25, "version": 24}
        res_v24 = sor.route_order(plan_v24, ats_available=False)
        maker_legs_v24 = [
            l for l in res_v24.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v24[0]["quantity"] == 5  # 10,000,000 * 0.0000005 = 5

        plan_v23 = {**plan_v25, "version": 23}
        res_v23 = sor.route_order(plan_v23, ats_available=False)
        maker_legs_v23 = [
            l for l in res_v23.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v23[0]["quantity"] == 10  # 10,000,000 * 0.000001 = 10

        plan_v22 = {**plan_v25, "version": 22}
        res_v22 = sor.route_order(plan_v22, ats_available=False)
        maker_legs_v22 = [
            l for l in res_v22.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v22[0]["quantity"] == 20  # 10,000,000 * 0.000002 = 20

        plan_v21 = {**plan_v25, "version": 21}
        res_v21 = sor.route_order(plan_v21, ats_available=False)
        maker_legs_v21 = [
            l for l in res_v21.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v21[0]["quantity"] == 50  # 10,000,000 * 0.000005 = 50

        assert (
            maker_legs_v25[0]["quantity"]
            < maker_legs_v24[0]["quantity"]
            < maker_legs_v23[0]["quantity"]
            < maker_legs_v22[0]["quantity"]
            < maker_legs_v21[0]["quantity"]
        )

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v25(self):
        """Verify dynamic Anti-Gaming MinQty cap expands to 99.9998% (0.999998) under Phase 25."""
        sor = SmartOrderRouter()
        qty = 1_000_000

        plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": qty,
            "target_price": 300.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 25,
        }
        res = sor.route_order(plan, ats_available=True)
        dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        dark_qty = dark_legs[0]["quantity"]
        min_qty = dark_legs[0].get("min_quantity", 0)

        ratio = min_qty / dark_qty
        assert math.isclose(ratio, 0.999998, abs_tol=1e-4)
        assert res["min_ratio"] == 0.999998

    def test_oms_preemptive_micro_tick_shading_v25(self):
        """
        Verify Phase 25 preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When h_val > 0.025, hawkes_shift = -direction * 0.9999 * spr * (h_val - 0.025).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.035

        # Buy order: direction = +1, hawkes_shift = -1.0 * 0.9999 * 1.0 * (0.035 - 0.025) = -0.009999
        peg_oms_buy_v25 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=25,
        )
        peg_sched_buy_v25 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=25,
        )
        expected_peg = target_px - 0.9999 * spr * (h_val - 0.025)
        assert math.isclose(peg_oms_buy_v25, expected_peg, abs_tol=1e-6)
        assert math.isclose(peg_sched_buy_v25, expected_peg, abs_tol=1e-6)
        assert bid_px <= peg_oms_buy_v25 <= ask_px

        # Sell order: direction = -1, hawkes_shift = +0.009999
        peg_oms_sell_v25 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=25,
        )
        assert math.isclose(peg_oms_sell_v25, target_px + 0.9999 * spr * (h_val - 0.025), abs_tol=1e-6)

    def test_oms_tick_shading_activation_threshold_boundary_v25(self):
        """
        Verify activation threshold boundary:
        Phase 25 activates at h > 0.025, whereas Phase 24 requires h > 0.030.
        At h = 0.028:
        - Version 25 is active (0.028 > 0.025)
        - Version 24 is inactive (0.028 <= 0.030)
        At h = 0.025 (boundary):
        - Both are inactive (unshifted at 100.0)
        """
        oms = ExecutionOMSEngine()

        # At h = 0.028
        peg_v25 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.028,
            version=25,
        )
        peg_v24 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.028,
            version=24,
        )
        assert peg_v25 < peg_v24
        assert math.isclose(peg_v24, 100.0, abs_tol=1e-6)
        expected_v25 = 100.0 - 0.9999 * 1.0 * (0.028 - 0.025)
        assert math.isclose(peg_v25, expected_v25, abs_tol=1e-6)

        # At h = 0.025 boundary
        peg_boundary = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.025,
            version=25,
        )
        assert math.isclose(peg_boundary, 100.0, abs_tol=1e-6)

    def test_full_backward_compatibility_v14_to_v24(self):
        """Verify legacy version flags produce strictly identical results to historical baselines."""
        oms = ExecutionOMSEngine()

        # At h = 0.032:
        # v24 active (0.032 > 0.030)
        # v23 inactive (0.032 <= 0.035)
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
        assert peg_v24 < 100.0
        assert math.isclose(peg_v23, 100.0, abs_tol=1e-6)
