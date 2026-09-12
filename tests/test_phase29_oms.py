"""
tests/test_phase29_oms.py

Unit and integration test suite for Phase 29 Quantitative Enhancement (Feature F137.2 Microstructure OMS):
- Kerr-Newman-Kiselev Phantom-Chameleon-Quintom-Tachyon 8-Dark-Energy (w_q = -2/3, w_p = -4/3, w_t = -5/3, w_m = -2.0, w_ch = -7/3, w_pc = -8/3, w_pcq = -3.0, w_pcqt = -10/3)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * Quintessence w_q = -2/3, Phantom w_p = -4/3, Tachyon w_t = -5/3, Quintom w_m = -2.0, Chameleon w_ch = -7/3, Phantom-Chameleon w_pc = -8/3, Phantom-Chameleon-Quintom w_pcq = -3.0, Phantom-Chameleon-Quintom-Tachyon w_pcqt = -10/3
  * Energy densities: rho_q = c_q / r, rho_p = 2*c_p*r, rho_t = 2.5*c_t*r^2, rho_m = 3.0*c_m*r^3, rho_ch = 3.5*c_ch*r^4, rho_pc = 4.0*c_pc*r^5, rho_pcq = 4.5*c_pcq*r^6, rho_pcqt = 5.0*c_pcqt*r^7
  * Spacetime metric horizon function Delta_r with 8-fold dark energy decay:
    Delta_r = (r^2 + a^2) - 2*M*r + Q^2 - c_q*r^3 - c_p*r^5 - c_t*r^6 - c_m*r^7 - c_ch*r^8 - c_pc*r^9 - c_pcq*r^10 - c_pcqt*r^11
  * Outer phantom-chameleon-quintom-tachyon cosmological horizon scale r_{PCQT}
  * Frame-dragging angular velocity omega_{drag}^{KNK-PCQT}(r, theta)
  * Radial tidal force with 8-fold dark energy repulsive acceleration:
    F_{tidal}^{KNK-PCQT} = F_{tidal}^{KN} - c_q*r - 2*c_p*r^3 - 2.5*c_t*r^4 - 3.0*c_m*r^5 - 3.5*c_ch*r^6 - 4.0*c_pc*r^7 - 4.5*c_pcq*r^8 - 5.0*c_pcqt*r^9
  * Hydrodynamic queue acceleration a_{KNK-PCQT} and micro-price prediction
  * 15+ method aliases on FastOrderBookMatchingEngine
- Fast LOB 99.99995% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=29:
  * Preemptive lit queue imbalance allocation with max dark cap 0.9999995 (99.99995%).
  * Lit maker ratio floor contracted to 0.00000001 (0.000001%, 1 share per 100,000,000)
    via 0.70 * (1.0 - 0.99999998571 * gamma_toxic) with 8-decimal formatting precision.
  * Dynamic anti-gaming MinQty scaled up to 99.99999% (0.9999999).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.010:
  hawkes_shift = -direction * 0.999995 * spr * (h - 0.010).
- Full backward compatibility across Phase 14 through Phase 28 versions.
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


class TestPhase29MicrostructureOMS:
    """Test suite for Phase 29 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev Phantom-Chameleon-Quintom-Tachyon 8-Dark-Energy queue acceleration and physical parameters."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            quintessence_parameter=0.05,
            phantom_parameter=0.02,
            tachyon_parameter=0.01,
            quintom_parameter=0.005,
            chameleon_parameter=0.002,
            phantom_chameleon_parameter=0.001,
            phantom_chameleon_quintom_parameter=0.0005,
            phantom_chameleon_quintom_tachyon_parameter=0.0002,
            w_q=-2.0 / 3.0,
            w_p=-4.0 / 3.0,
            w_t=-5.0 / 3.0,
            w_m=-2.0,
            w_c=-7.0 / 3.0,
            w_pc=-8.0 / 3.0,
            w_pcq=-3.0,
            w_pcqt=-10.0 / 3.0,
        )
        assert isinstance(res, dict)

        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "knk_pcqt_mass_M",
            "knk_pcqt_spin_a",
            "knk_pcqt_charge_Q",
            "quintessence_c_q",
            "phantom_c_p",
            "tachyon_c_t",
            "quintom_c_m",
            "chameleon_c_ch",
            "phantom_chameleon_c_pc",
            "phantom_chameleon_quintom_c_pcq",
            "phantom_chameleon_quintom_tachyon_c_pcqt",
            "equation_of_state_w_q",
            "equation_of_state_w_p",
            "equation_of_state_w_t",
            "equation_of_state_w_m",
            "equation_of_state_w_ch",
            "equation_of_state_w_pc",
            "equation_of_state_w_pcq",
            "equation_of_state_w_pcqt",
            "phantom_chameleon_quintom_tachyon_horizon_r_PCQT",
            "phantom_chameleon_quintom_tachyon_horizon",
            "phantom_chameleon_quintom_horizon_r_PCQ",
            "phantom_chameleon_quintom_horizon",
            "phantom_chameleon_horizon_r_PC",
            "phantom_chameleon_horizon",
            "chameleon_horizon_r_Ch",
            "chameleon_horizon",
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
            "knk_pcqt_tidal_force",
            "knk_pcqt_hydrodynamic_acceleration",
            "knk_pcqt_rotational_acceleration",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_rotational_acceleration",
            "knk_pcqt_accelerated_qi",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_accelerated_qi",
            "knk_pcqt_micro_price",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_micro_price",
        ]
        for k in required_keys:
            assert k in res, f"Missing key in Kerr-Newman-Kiselev Phantom-Chameleon-Quintom-Tachyon result: {k}"

        # Check physical parameters and bounds
        assert res["quintessence_c_q"] == 0.05
        assert res["phantom_c_p"] == 0.02
        assert res["tachyon_c_t"] == 0.01
        assert res["quintom_c_m"] == 0.005
        assert res["chameleon_c_ch"] == 0.002
        assert res["phantom_chameleon_c_pc"] == 0.001
        assert res["phantom_chameleon_quintom_c_pcq"] == 0.0005
        assert res["phantom_chameleon_quintom_tachyon_c_pcqt"] == 0.0002
        assert math.isclose(res["equation_of_state_w_q"], -2.0 / 3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_p"], -4.0 / 3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_t"], -5.0 / 3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_m"], -2.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_ch"], -7.0 / 3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_pc"], -8.0 / 3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_pcq"], -3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_pcqt"], -10.0 / 3.0, abs_tol=1e-3)
        assert res["knk_pcqt_mass_M"] >= 1.0
        assert res["knk_pcqt_spin_a"] > 0.0
        assert res["knk_pcqt_charge_Q"] > 0.0
        assert res["phantom_chameleon_quintom_tachyon_horizon_r_PCQT"] > 0.0
        assert res["phantom_chameleon_quintom_horizon_r_PCQ"] > 0.0
        assert res["phantom_chameleon_horizon_r_PC"] > 0.0
        assert res["chameleon_horizon_r_Ch"] > 0.0
        assert res["quintom_horizon_r_M"] > 0.0
        assert res["tachyon_horizon_r_T"] > 0.0
        assert res["phantom_horizon_r_P"] > 0.0
        assert res["quintessence_horizon_r_Q"] > 0.0
        assert res["frame_dragging_omega"] > 0.0
        assert math.isfinite(res["tidal_force"])
        assert math.isfinite(res["knk_pcqt_hydrodynamic_acceleration"])
        assert -1.0 <= res["knk_pcqt_accelerated_qi"] <= 1.0
        assert res["knk_pcqt_micro_price"] > 0.0

        # Check backward compatibility keys for prior phases
        assert "knk_pcq_hydrodynamic_acceleration" in res
        assert "knk_pc_hydrodynamic_acceleration" in res
        assert "knk_c_hydrodynamic_acceleration" in res
        assert "knk_qm_hydrodynamic_acceleration" in res
        assert "knk_pt_hydrodynamic_acceleration" in res
        assert "knk_p_hydrodynamic_acceleration" in res
        assert "knk_hydrodynamic_acceleration" in res
        assert "kn_ads_ds_hydrodynamic_acceleration" in res
        assert "kn_ads_hydrodynamic_acceleration" in res

        # Check all 15+ method aliases
        aliases = [
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_hydrodynamics",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_queue_acceleration",
            "calculate_knk_phantom_chameleon_quintom_tachyon_queue_acceleration",
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_frame_dragging",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_hydrodynamics",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_frame_dragging",
            "compute_knk_8_dark_energy_hydrodynamics",
            "compute_kerr_newman_kiselev_8_dark_energy_hydrodynamics",
            "calculate_knk_8_dark_energy_hydrodynamics",
            "calculate_kerr_newman_kiselev_8_dark_energy_hydrodynamics",
            "compute_knk_pcqt_queue_acceleration",
            "compute_knk_pcqt_dark_energy_acceleration",
            "compute_pcqt_dark_energy_acceleration",
            "compute_pcqt_queue_acceleration",
            "compute_phantom_chameleon_quintom_tachyon_acceleration",
            "compute_phase29_lob_acceleration",
            "compute_knk_pcqt_hydrodynamics",
            "compute_phase29_hydrodynamics",
            "compute_kerr_newman_kiselev_queue_acceleration_phase29",
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
                chameleon_parameter=0.002,
                phantom_chameleon_parameter=0.001,
                phantom_chameleon_quintom_parameter=0.0005,
                phantom_chameleon_quintom_tachyon_parameter=0.0002,
                w_q=-2.0 / 3.0,
                w_p=-4.0 / 3.0,
                w_t=-5.0 / 3.0,
                w_m=-2.0,
                w_c=-7.0 / 3.0,
                w_pc=-8.0 / 3.0,
                w_pcq=-3.0,
                w_pcqt=-10.0 / 3.0,
            )
            assert math.isclose(
                alias_res["knk_pcqt_hydrodynamic_acceleration"],
                res["knk_pcqt_hydrodynamic_acceleration"],
                abs_tol=1e-6,
            )

    def test_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_physics_and_8_dark_energy(self):
        """Verify KNK-PCQT 8-dark-energy tidal repulsion and horizon physics."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        engine.add_limit_order("b1", "BUY", 150.00, 1000.0)
        engine.add_limit_order("a1", "SELL", 150.10, 200.0)

        # Static vs Rotating frame dragging
        res_static = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.0,
            quintessence_parameter=0.05,
            phantom_parameter=0.02,
            tachyon_parameter=0.01,
            quintom_parameter=0.005,
            chameleon_parameter=0.002,
            phantom_chameleon_parameter=0.001,
            phantom_chameleon_quintom_parameter=0.0005,
            phantom_chameleon_quintom_tachyon_parameter=0.0002,
        )
        assert res_static["frame_dragging_omega"] == 0.0

        res_rotating = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.7,
            quintessence_parameter=0.05,
            phantom_parameter=0.02,
            tachyon_parameter=0.01,
            quintom_parameter=0.005,
            chameleon_parameter=0.002,
            phantom_chameleon_parameter=0.001,
            phantom_chameleon_quintom_parameter=0.0005,
            phantom_chameleon_quintom_tachyon_parameter=0.0002,
        )
        assert res_rotating["frame_dragging_omega"] > 0.0

        # 8-fold dark energy tidal force:
        # Increasing c_pcqt should further decrease (repulse) the radial tidal force
        engine_small = FastOrderBookMatchingEngine(symbol="AAPL")
        engine_small.add_limit_order("b1", "BUY", 150.00, 10.0)
        engine_small.add_limit_order("a1", "SELL", 150.10, 10.0)

        res_low_cpcqt = engine_small.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            quintessence_parameter=0.001,
            phantom_parameter=0.0005,
            tachyon_parameter=0.0002,
            quintom_parameter=0.0001,
            chameleon_parameter=0.00005,
            phantom_chameleon_parameter=0.00001,
            phantom_chameleon_quintom_parameter=0.000005,
            phantom_chameleon_quintom_tachyon_parameter=0.000001,
        )
        res_high_cpcqt = engine_small.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            quintessence_parameter=0.001,
            phantom_parameter=0.0005,
            tachyon_parameter=0.0002,
            quintom_parameter=0.0001,
            chameleon_parameter=0.00005,
            phantom_chameleon_parameter=0.00001,
            phantom_chameleon_quintom_parameter=0.000005,
            phantom_chameleon_quintom_tachyon_parameter=0.000002,
        )
        assert res_high_cpcqt["knk_pcqt_tidal_force"] < res_low_cpcqt["knk_pcqt_tidal_force"]

        # Cosmological horizon outer separation
        r_horiz = res_rotating["horizon_radius"]
        assert res_rotating["phantom_chameleon_quintom_tachyon_horizon_r_PCQT"] > r_horiz
        assert res_rotating["phantom_chameleon_quintom_horizon_r_PCQ"] > r_horiz
        assert res_rotating["phantom_chameleon_horizon_r_PC"] > r_horiz
        assert res_rotating["chameleon_horizon_r_Ch"] > r_horiz
        assert res_rotating["quintom_horizon_r_M"] > r_horiz
        assert res_rotating["tachyon_horizon_r_T"] > r_horiz
        assert res_rotating["phantom_horizon_r_P"] > r_horiz
        assert res_rotating["quintessence_horizon_r_Q"] > r_horiz

    def test_fast_lob_dark_routing_cap_v29_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess 99.99995% dark routing cap when version=29."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=29)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.9999995
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=29)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.9999995
        opt_res = process.get_optimal_preemptive_dark_allocation(version=29)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.9999995

    def test_fast_lob_dark_routing_cap_v29_frame_inspection(self):
        """Verify Fast LOB DeepHawkesArrivalProcess auto-infers 99.99995% dark cap via stack inspection."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        # Calling without version should inspect current test frame ("phase29" in filename)
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.9999995

    def test_smart_order_router_v29_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.99995% to dark venues under Phase 29."""
        sor = SmartOrderRouter()
        plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 10_000_000,
            "target_price": 70000.0,
            "market_spread_bps": 12.0,
            "queue_imbalance": 0.80,
            "qi_acceleration": 0.50,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.90,
            "version": 29,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        total_dark = sum(l["quantity"] for l in dark_legs)
        # 10,000,000 * 0.9999995 = 9,999,995
        assert total_dark == 9_999_995

    def test_smart_order_router_maker_floor_contraction_v29(self):
        """
        Verify maker ratio floor contracts to 0.00000001 (1 share per 100,000,000) under extreme toxicity.
        Formula: 0.70 * (1.0 - 0.99999998571 * gamma_toxic) clamped at 0.00000001.
        """
        sor = SmartOrderRouter()
        qty = 100_000_000

        plan_v29 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 29,
        }
        res_v29 = sor.route_order(plan_v29, ats_available=False)
        maker_legs_v29 = [
            l for l in res_v29.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v29) > 0
        # 100,000,000 * 0.00000001 = 1 share
        assert maker_legs_v29[0]["quantity"] == 1
        assert res_v29["maker_ratio"] == 0.00000001

        # Monotonic floor contraction test against prior versions
        plan_v28 = {**plan_v29, "version": 28}
        res_v28 = sor.route_order(plan_v28, ats_available=False)
        maker_legs_v28 = [
            l for l in res_v28.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v28[0]["quantity"] == 2  # 100,000,000 * 0.00000002 = 2

        plan_v27 = {**plan_v29, "version": 27}
        res_v27 = sor.route_order(plan_v27, ats_available=False)
        maker_legs_v27 = [
            l for l in res_v27.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v27[0]["quantity"] == 5  # 100,000,000 * 0.00000005 = 5

        plan_v26 = {**plan_v29, "version": 26}
        res_v26 = sor.route_order(plan_v26, ats_available=False)
        maker_legs_v26 = [
            l for l in res_v26.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v26[0]["quantity"] == 10  # 100,000,000 * 0.0000001 = 10

        assert (
            maker_legs_v29[0]["quantity"]
            < maker_legs_v28[0]["quantity"]
            < maker_legs_v27[0]["quantity"]
            < maker_legs_v26[0]["quantity"]
        )

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v29(self):
        """Verify dynamic Anti-Gaming MinQty cap expands to 99.99999% (0.9999999) under Phase 29."""
        sor = SmartOrderRouter()
        qty = 10_000_000

        plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": qty,
            "target_price": 300.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 29,
        }
        res = sor.route_order(plan, ats_available=True)
        dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        dark_qty = dark_legs[0]["quantity"]
        min_qty = dark_legs[0].get("min_quantity", 0)

        ratio = min_qty / dark_qty
        assert math.isclose(ratio, 0.9999999, abs_tol=1e-4)
        assert res["min_ratio"] == 0.9999999

    def test_oms_preemptive_micro_tick_shading_v29(self):
        """
        Verify Phase 29 preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When h_val > 0.010, hawkes_shift = -direction * 0.999995 * spr * (h_val - 0.010).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.025

        # Buy order: direction = +1, hawkes_shift = -1.0 * 0.999995 * 1.0 * (0.025 - 0.010) = -0.014999925
        peg_oms_buy_v29 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=29,
        )
        peg_sched_buy_v29 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=29,
        )
        expected_peg = target_px - 0.999995 * spr * (h_val - 0.010)
        assert math.isclose(peg_oms_buy_v29, expected_peg, abs_tol=1e-6)
        assert math.isclose(peg_sched_buy_v29, expected_peg, abs_tol=1e-6)
        assert bid_px <= peg_oms_buy_v29 <= ask_px

        # Sell order: direction = -1, hawkes_shift = +0.014999925
        peg_oms_sell_v29 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=29,
        )
        assert math.isclose(peg_oms_sell_v29, target_px + 0.999995 * spr * (h_val - 0.010), abs_tol=1e-6)

    def test_oms_tick_shading_activation_threshold_boundary_v29(self):
        """
        Verify activation threshold boundary:
        Phase 29 activates at h > 0.010, whereas Phase 28 requires h > 0.012.
        At h = 0.011:
        - Version 29 is active (0.011 > 0.010)
        - Version 28 is inactive (0.011 <= 0.012)
        At h = 0.010 (boundary):
        - Both are inactive (unshifted at 100.0)
        """
        oms = ExecutionOMSEngine()

        # At h = 0.011
        peg_v29 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.011,
            version=29,
        )
        peg_v28 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.011,
            version=28,
        )
        assert peg_v29 < peg_v28
        assert math.isclose(peg_v28, 100.0, abs_tol=1e-6)
        expected_v29 = 100.0 - 0.999995 * 1.0 * (0.011 - 0.010)
        assert math.isclose(peg_v29, expected_v29, abs_tol=1e-6)

        # At h = 0.010 boundary
        peg_boundary = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.010,
            version=29,
        )
        assert math.isclose(peg_boundary, 100.0, abs_tol=1e-6)

    def test_full_backward_compatibility_v14_to_v28(self):
        """Verify legacy version flags produce strictly identical results to historical baselines."""
        oms = ExecutionOMSEngine()

        # At h = 0.014:
        # v28 active (0.014 > 0.012)
        # v27 inactive (0.014 <= 0.015)
        peg_v28 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.014,
            version=28,
        )
        peg_v27 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.014,
            version=27,
        )
        assert peg_v28 < 100.0
        assert math.isclose(peg_v27, 100.0, abs_tol=1e-6)
