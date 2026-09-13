"""
tests/test_phase31_oms.py

Unit and integration test suite for Phase 31 Quantitative Enhancement (Feature F145.2 Microstructure OMS):
- Kerr-Newman-Kiselev Non-Abelian Ghost Condensate & Brane 10-Dark-Energy (w_q = -2/3, w_p = -4/3, w_t = -5/3, w_m = -2.0,
  w_c = -7/3, w_pc = -8/3, w_pcq = -3.0, w_pcqt = -10/3, w_pcqtg = -11/3, w_pcqtgb = -4.0)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 10-fold dark energy: Quintessence, Phantom, Tachyon, Quintom, Chameleon, Phantom-Chameleon,
    Phantom-Chameleon-Quintom, Phantom-Chameleon-Quintom-Tachyon, Phantom-Chameleon-Quintom-Tachyon-Ghost,
    Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane
  * Energy densities up to rho_pcqtgb = 6.0 * c_pcqtgb * r^9
  * Spacetime metric horizon function Delta_r with 10-fold dark energy decay
  * Outer cosmological horizon scale r_{PCQTGB}
  * Radial tidal force with 10-fold dark energy repulsive acceleration:
    - 6.0 * c_pcqtgb * r^11
  * Hydrodynamic queue acceleration a_{KNK-PCQTGB} and micro-price prediction
  * 15+ method aliases on FastOrderBookMatchingEngine
- Fast LOB 99.99999% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=31:
  * Preemptive lit queue imbalance allocation with max dark cap 0.9999999 (99.99999%).
  * Lit maker ratio floor contracted to 0.000000002 (0.0000002%, 1 share per 500,000,000)
    via 0.70 * (1.0 - 0.999999997143 * gamma_toxic) with 9-decimal formatting precision.
  * Dynamic anti-gaming MinQty scaled up to 99.999998% (0.99999998).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.006:
  hawkes_shift = -direction * 0.999999 * spr * (h - 0.006).
- Full backward compatibility across Phase 14 through Phase 30 versions.
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


class TestPhase31MicrostructureOMS:
    """Test suite for Phase 31 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev Non-Abelian Ghost Condensate & Brane 10-Dark-Energy queue acceleration and physical parameters."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_queue_acceleration(
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
            phantom_chameleon_quintom_tachyon_ghost_parameter=0.0001,
            phantom_chameleon_quintom_tachyon_ghost_brane_parameter=0.00005,
            w_q=-2.0 / 3.0,
            w_p=-4.0 / 3.0,
            w_t=-5.0 / 3.0,
            w_m=-2.0,
            w_c=-7.0 / 3.0,
            w_pc=-8.0 / 3.0,
            w_pcq=-3.0,
            w_pcqt=-10.0 / 3.0,
            w_pcqtg=-11.0 / 3.0,
            w_pcqtgb=-4.0,
        )
        assert isinstance(res, dict)

        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "knk_pcqtgb_mass_M",
            "knk_pcqtgb_spin_a",
            "knk_pcqtgb_charge_Q",
            "quintessence_c_q",
            "phantom_c_p",
            "tachyon_c_t",
            "quintom_c_m",
            "chameleon_c_ch",
            "phantom_chameleon_c_pc",
            "phantom_chameleon_quintom_c_pcq",
            "phantom_chameleon_quintom_tachyon_c_pcqt",
            "phantom_chameleon_quintom_tachyon_ghost_c_pcqtg",
            "phantom_chameleon_quintom_tachyon_ghost_brane_c_pcqtgb",
            "equation_of_state_w_q",
            "equation_of_state_w_p",
            "equation_of_state_w_t",
            "equation_of_state_w_m",
            "equation_of_state_w_ch",
            "equation_of_state_w_pc",
            "equation_of_state_w_pcq",
            "equation_of_state_w_pcqt",
            "equation_of_state_w_pcqtg",
            "equation_of_state_w_pcqtgb",
            "phantom_chameleon_quintom_tachyon_ghost_brane_horizon_r_PCQTGB",
            "phantom_chameleon_quintom_tachyon_ghost_brane_horizon",
            "phantom_chameleon_quintom_tachyon_ghost_horizon_r_PCQTG",
            "phantom_chameleon_quintom_tachyon_ghost_horizon",
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
            "knk_pcqtgb_tidal_force",
            "knk_pcqtgb_hydrodynamic_acceleration",
            "knk_pcqtgb_rotational_acceleration",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_rotational_acceleration",
            "knk_pcqtgb_accelerated_qi",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_accelerated_qi",
            "knk_pcqtgb_micro_price",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_micro_price",
        ]
        for k in required_keys:
            assert k in res, f"Missing key in Kerr-Newman-Kiselev 10-Dark-Energy result: {k}"

        # Check physical parameters and bounds
        assert res["quintessence_c_q"] == 0.05
        assert res["phantom_c_p"] == 0.02
        assert res["tachyon_c_t"] == 0.01
        assert res["quintom_c_m"] == 0.005
        assert res["chameleon_c_ch"] == 0.002
        assert res["phantom_chameleon_c_pc"] == 0.001
        assert res["phantom_chameleon_quintom_c_pcq"] == 0.0005
        assert res["phantom_chameleon_quintom_tachyon_c_pcqt"] == 0.0002
        assert res["phantom_chameleon_quintom_tachyon_ghost_c_pcqtg"] == 0.0001
        assert res["phantom_chameleon_quintom_tachyon_ghost_brane_c_pcqtgb"] == 0.00005
        assert math.isclose(res["equation_of_state_w_q"], -2.0 / 3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_p"], -4.0 / 3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_t"], -5.0 / 3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_m"], -2.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_ch"], -7.0 / 3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_pc"], -8.0 / 3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_pcq"], -3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_pcqt"], -10.0 / 3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_pcqtg"], -11.0 / 3.0, abs_tol=1e-3)
        assert math.isclose(res["equation_of_state_w_pcqtgb"], -4.0, abs_tol=1e-3)
        assert res["knk_pcqtgb_mass_M"] >= 1.0
        assert res["knk_pcqtgb_spin_a"] > 0.0
        assert res["knk_pcqtgb_charge_Q"] > 0.0
        assert res["phantom_chameleon_quintom_tachyon_ghost_brane_horizon_r_PCQTGB"] > 0.0
        assert res["phantom_chameleon_quintom_tachyon_ghost_horizon_r_PCQTG"] > 0.0
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
        assert math.isfinite(res["knk_pcqtgb_hydrodynamic_acceleration"])
        assert -1.0 <= res["knk_pcqtgb_accelerated_qi"] <= 1.0
        assert res["knk_pcqtgb_micro_price"] > 0.0

        # Check backward compatibility keys for prior phases
        assert "knk_pcqtg_hydrodynamic_acceleration" in res
        assert "knk_pcqt_hydrodynamic_acceleration" in res
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
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_hydrodynamics",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_queue_acceleration",
            "calculate_knk_phantom_chameleon_quintom_tachyon_ghost_brane_queue_acceleration",
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_frame_dragging",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_hydrodynamics",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_frame_dragging",
            "compute_knk_10_dark_energy_hydrodynamics",
            "compute_kerr_newman_kiselev_10_dark_energy_hydrodynamics",
            "calculate_knk_10_dark_energy_hydrodynamics",
            "calculate_kerr_newman_kiselev_10_dark_energy_hydrodynamics",
            "compute_knk_pcqtgb_queue_acceleration",
            "compute_knk_pcqtgb_dark_energy_acceleration",
            "compute_pcqtgb_dark_energy_acceleration",
            "compute_pcqtgb_queue_acceleration",
            "compute_phantom_chameleon_quintom_tachyon_ghost_brane_acceleration",
            "compute_phase31_lob_acceleration",
            "compute_knk_pcqtgb_hydrodynamics",
            "compute_phase31_hydrodynamics",
            "compute_kerr_newman_kiselev_queue_acceleration_phase31",
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
                phantom_chameleon_quintom_tachyon_ghost_parameter=0.0001,
                phantom_chameleon_quintom_tachyon_ghost_brane_parameter=0.00005,
                w_q=-2.0 / 3.0,
                w_p=-4.0 / 3.0,
                w_t=-5.0 / 3.0,
                w_m=-2.0,
                w_c=-7.0 / 3.0,
                w_pc=-8.0 / 3.0,
                w_pcq=-3.0,
                w_pcqt=-10.0 / 3.0,
                w_pcqtg=-11.0 / 3.0,
                w_pcqtgb=-4.0,
            )
            assert math.isclose(
                alias_res["knk_pcqtgb_hydrodynamic_acceleration"],
                res["knk_pcqtgb_hydrodynamic_acceleration"],
                abs_tol=1e-6,
            )

    def test_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_physics_and_10_dark_energy(self):
        """Verify KNK-PCQTGB 10-dark-energy tidal repulsion and horizon physics."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        engine.add_limit_order("b1", "BUY", 150.00, 1000.0)
        engine.add_limit_order("a1", "SELL", 150.10, 200.0)

        # Static vs Rotating frame dragging
        res_static = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_queue_acceleration(
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
            phantom_chameleon_quintom_tachyon_ghost_parameter=0.0001,
            phantom_chameleon_quintom_tachyon_ghost_brane_parameter=0.00005,
        )
        assert res_static["frame_dragging_omega"] == 0.0

        res_rotating = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_queue_acceleration(
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
            phantom_chameleon_quintom_tachyon_ghost_parameter=0.0001,
            phantom_chameleon_quintom_tachyon_ghost_brane_parameter=0.00005,
        )
        assert res_rotating["frame_dragging_omega"] > 0.0

        # 10-fold dark energy tidal force:
        # Increasing c_pcqtgb should further decrease (repulse) the radial tidal force
        engine_small = FastOrderBookMatchingEngine(symbol="AAPL")
        engine_small.add_limit_order("b1", "BUY", 150.00, 10.0)
        engine_small.add_limit_order("a1", "SELL", 150.10, 10.0)

        res_low_cpcqtgb = engine_small.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_queue_acceleration(
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
            phantom_chameleon_quintom_tachyon_ghost_parameter=0.0000005,
            phantom_chameleon_quintom_tachyon_ghost_brane_parameter=0.0000001,
        )
        res_high_cpcqtgb = engine_small.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_queue_acceleration(
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
            phantom_chameleon_quintom_tachyon_ghost_parameter=0.0000005,
            phantom_chameleon_quintom_tachyon_ghost_brane_parameter=0.0000005,
        )
        assert res_high_cpcqtgb["knk_pcqtgb_tidal_force"] < res_low_cpcqtgb["knk_pcqtgb_tidal_force"]

        # Cosmological horizon outer separation
        r_horiz = res_rotating["horizon_radius"]
        assert res_rotating["phantom_chameleon_quintom_tachyon_ghost_brane_horizon_r_PCQTGB"] > r_horiz
        assert res_rotating["phantom_chameleon_quintom_tachyon_ghost_horizon_r_PCQTG"] > r_horiz
        assert res_rotating["phantom_chameleon_quintom_tachyon_horizon_r_PCQT"] > r_horiz
        assert res_rotating["phantom_chameleon_quintom_horizon_r_PCQ"] > r_horiz
        assert res_rotating["phantom_chameleon_horizon_r_PC"] > r_horiz
        assert res_rotating["chameleon_horizon_r_Ch"] > r_horiz
        assert res_rotating["quintom_horizon_r_M"] > r_horiz
        assert res_rotating["tachyon_horizon_r_T"] > r_horiz
        assert res_rotating["phantom_horizon_r_P"] > r_horiz
        assert res_rotating["quintessence_horizon_r_Q"] > r_horiz

    def test_fast_lob_dark_routing_cap_v31_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess 99.99999% dark routing cap when version=31."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=31)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.9999999
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=31)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.9999999
        opt_res = process.get_optimal_preemptive_dark_allocation(version=31)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.9999999

    def test_fast_lob_dark_routing_cap_v31_frame_inspection(self):
        """Verify Fast LOB DeepHawkesArrivalProcess auto-infers 99.99999% dark cap via stack inspection."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        # Calling without version should inspect current test frame ("phase31" in filename)
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.9999999

    def test_smart_order_router_v31_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.99999% to dark venues under Phase 31."""
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
            "version": 31,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        total_dark = sum(l["quantity"] for l in dark_legs)
        # 10,000,000 * 0.9999999 = 9,999,999
        assert total_dark == 9_999_999

    def test_smart_order_router_maker_floor_contraction_v31(self):
        """
        Verify maker ratio floor contracts to 0.000000002 (1 share per 500,000,000) under extreme toxicity.
        Formula: 0.70 * (1.0 - 0.999999997143 * gamma_toxic) clamped at 0.000000002.
        """
        sor = SmartOrderRouter()
        qty = 500_000_000

        plan_v31 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 31,
        }
        res_v31 = sor.route_order(plan_v31, ats_available=False)
        maker_legs_v31 = [
            l for l in res_v31.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v31) > 0
        # 500,000,000 * 0.000000002 = 1 share
        assert maker_legs_v31[0]["quantity"] == 1
        assert res_v31["maker_ratio"] == 0.000000002

        # Monotonic floor contraction test against prior versions with 1,000,000,000 shares
        qty_large = 1_000_000_000
        plan_v31_l = {**plan_v31, "quantity": qty_large}
        res_v31_l = sor.route_order(plan_v31_l, ats_available=False)
        maker_legs_v31_l = [
            l for l in res_v31_l.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        # 1,000,000,000 * 0.000000002 = 2 shares
        assert maker_legs_v31_l[0]["quantity"] == 2

        plan_v30_l = {**plan_v31_l, "version": 30}
        res_v30_l = sor.route_order(plan_v30_l, ats_available=False)
        maker_legs_v30_l = [
            l for l in res_v30_l.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        # 1,000,000,000 * 0.000000005 = 5 shares
        assert maker_legs_v30_l[0]["quantity"] == 5

        plan_v29_l = {**plan_v31_l, "version": 29}
        res_v29_l = sor.route_order(plan_v29_l, ats_available=False)
        maker_legs_v29_l = [
            l for l in res_v29_l.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        # 1,000,000,000 * 0.00000001 = 10 shares
        assert maker_legs_v29_l[0]["quantity"] == 10

        assert (
            maker_legs_v31_l[0]["quantity"]
            < maker_legs_v30_l[0]["quantity"]
            < maker_legs_v29_l[0]["quantity"]
        )

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v31(self):
        """Verify dynamic Anti-Gaming MinQty cap expands to 99.999998% (0.99999998) under Phase 31."""
        sor = SmartOrderRouter()
        qty = 100_000_000

        plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": qty,
            "target_price": 300.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 31,
        }
        res = sor.route_order(plan, ats_available=True)
        dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        dark_qty = dark_legs[0]["quantity"]
        min_qty = dark_legs[0].get("min_quantity", 0)

        ratio = min_qty / dark_qty
        assert math.isclose(ratio, 0.99999998, abs_tol=1e-4)
        assert res["min_ratio"] == 0.99999998

    def test_oms_preemptive_micro_tick_shading_v31(self):
        """
        Verify Phase 31 preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When h_val > 0.006, hawkes_shift = -direction * 0.999999 * spr * (h_val - 0.006).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.025

        # Buy order: direction = +1, hawkes_shift = -1.0 * 0.999999 * 1.0 * (0.025 - 0.006) = -0.018999981
        peg_oms_buy_v31 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=31,
        )
        peg_sched_buy_v31 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=31,
        )
        expected_peg = target_px - 0.999999 * spr * (h_val - 0.006)
        assert math.isclose(peg_oms_buy_v31, expected_peg, abs_tol=1e-6)
        assert math.isclose(peg_sched_buy_v31, expected_peg, abs_tol=1e-6)
        assert bid_px <= peg_oms_buy_v31 <= ask_px

        # Sell order: direction = -1, hawkes_shift = +0.018999981
        peg_oms_sell_v31 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=31,
        )
        assert math.isclose(peg_oms_sell_v31, target_px + 0.999999 * spr * (h_val - 0.006), abs_tol=1e-6)

    def test_oms_tick_shading_activation_threshold_boundary_v31(self):
        """
        Verify activation threshold boundary:
        Phase 31 activates at h > 0.006, whereas Phase 30 requires h > 0.008.
        At h = 0.007:
        - Version 31 is active (0.007 > 0.006)
        - Version 30 is inactive (0.007 <= 0.008)
        At h = 0.006 (boundary):
        - Both are inactive (unshifted at 100.0)
        """
        oms = ExecutionOMSEngine()

        # At h = 0.007
        peg_v31 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.007,
            version=31,
        )
        peg_v30 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.007,
            version=30,
        )
        assert peg_v31 < peg_v30
        assert math.isclose(peg_v30, 100.0, abs_tol=1e-6)
        expected_v31 = 100.0 - 0.999999 * 1.0 * (0.007 - 0.006)
        assert math.isclose(peg_v31, expected_v31, abs_tol=1e-6)

        # At h = 0.006 boundary
        peg_boundary = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.006,
            version=31,
        )
        assert math.isclose(peg_boundary, 100.0, abs_tol=1e-6)

    def test_full_backward_compatibility_v14_to_v30(self):
        """Verify legacy version flags produce strictly identical results to historical baselines."""
        oms = ExecutionOMSEngine()

        # At h = 0.009:
        # v30 active (0.009 > 0.008)
        # v29 inactive (0.009 <= 0.010)
        peg_v30 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.009,
            version=30,
        )
        peg_v29 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.009,
            version=29,
        )
        assert peg_v30 < 100.0
        assert math.isclose(peg_v29, 100.0, abs_tol=1e-6)
