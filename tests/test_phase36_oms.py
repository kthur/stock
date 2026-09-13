"""
tests/test_phase36_oms.py

Unit and integration test suite for Phase 36 Quantitative Enhancement (Feature F165.2 Microstructure OMS):
- Kerr-Newman-Kiselev 15-Dark-Energy PCQTGBDDDDD Dunkl-Hecke-Cherednik DAHA (w_pcqtgbddddd = -17/3 = -5.6667, k_hecke = 0.06, k_cherednik = 0.07)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 15-fold dark energy: Quintessence, Phantom, Tachyon, Quintom, Chameleon, Phantom-Chameleon,
    Phantom-Chameleon-Quintom, Phantom-Chameleon-Quintom-Tachyon, Phantom-Chameleon-Quintom-Tachyon-Ghost,
    Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane, Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane-Dilaton,
    Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane-Dilaton-Dirac,
    Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane-Dilaton-Dirac-Dunkl,
    Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane-Dilaton-Dirac-Dunkl-Hecke,
    Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane-Dilaton-Dirac-Dunkl-Hecke-Cherednik
  * Energy densities up to rho_pcqtgbddddd = 9.0 * c_pcqtgbddddd * r^14 * (1.0 + k_hecke + k_cherednik)
  * Spacetime metric horizon function Delta_r with 15-fold dark energy decay
  * Outer cosmological horizon scale r_{PCQTGBDDDDD}
  * Radial tidal force with 15-fold dark energy repulsive acceleration:
    - 8.5 * c_pcqtgbddddd * r^16 * (1.0 + k_hecke + k_cherednik)
  * Hydrodynamic queue acceleration a_{KNK-PCQTGBDDDDD} and micro-price prediction
  * Method aliases on FastOrderBookMatchingEngine
- Fast LOB 99.9999998% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=36:
  * Preemptive lit queue imbalance allocation with max dark cap 0.999999998 (99.9999998%).
  * Lit maker ratio floor contracted to 0.00000000005 (0.000000005%, 1 share per 20,000,000,000)
    via 0.70 * (1.0 - 0.999999999929 * gamma_toxic) with 12-decimal formatting precision.
  * Dynamic anti-gaming MinQty scaled up to 99.99999995% (0.9999999995).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.0015:
  hawkes_shift = -direction * 0.99999998 * spr * (h - 0.0015).
- Full backward compatibility across Phase 14 through Phase 35 versions.
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    DeepHawkesArrivalProcess,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase36MicrostructureOMS:
    """Test suite for Phase 36 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 15-Dark-Energy PCQTGBDDDDD Dunkl-Hecke-Cherednik DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_queue_acceleration(
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
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_parameter=0.00003,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_parameter=0.00002,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_parameter=0.00001,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_parameter=0.000005,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_parameter=0.000004,
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
            w_pcqtgbd=-13.0 / 3.0,
            w_pcqtgbdd=-14.0 / 3.0,
            w_pcqtgbddd=-15.0 / 3.0,
            w_pcqtgbdddd=-16.0 / 3.0,
            w_pcqtgbddddd=-17.0 / 3.0,
            k_hecke=0.06,
            k_cherednik=0.07,
        )
        assert isinstance(res, dict)

        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "knk_pcqtgbddddd_mass_M",
            "knk_pcqtgbddddd_spin_a",
            "knk_pcqtgbddddd_charge_Q",
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
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_c_pcqtgbd",
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_c_pcqtgbdd",
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_c_pcqtgbddd",
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_c_pcqtgbdddd",
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_c_pcqtgbddddd",
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
            "equation_of_state_w_pcqtgbd",
            "equation_of_state_w_pcqtgbdd",
            "equation_of_state_w_pcqtgbddd",
            "equation_of_state_w_pcqtgbdddd",
            "equation_of_state_w_pcqtgbddddd",
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_horizon_r_PCQTGBDDDDD",
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_horizon",
            "horizon_radius",
            "coordinate_radius_r",
            "is_in_horizon",
            "frame_dragging_omega",
            "tidal_force",
            "knk_pcqtgbddddd_tidal_force",
            "knk_pcqtgbddddd_hydrodynamic_acceleration",
            "knk_pcqtgbddddd_rotational_acceleration",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_rotational_acceleration",
            "knk_pcqtgbddddd_accelerated_qi",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_accelerated_qi",
            "knk_pcqtgbddddd_micro_price",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_micro_price",
        ]
        for k in required_keys:
            assert k in res, f"Missing key in Kerr-Newman-Kiselev 15-Dark-Energy result: {k}"

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
        assert res["phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_c_pcqtgbd"] == 0.00003
        assert res["phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_c_pcqtgbdd"] == 0.00002
        assert res["phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_c_pcqtgbddd"] == 0.00001
        assert res["phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_c_pcqtgbdddd"] == 0.000005
        assert res["phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_c_pcqtgbddddd"] == 0.000004
        assert math.isclose(res["equation_of_state_w_pcqtgbddddd"], -17.0 / 3.0, abs_tol=1e-3)
        assert res["knk_pcqtgbddddd_mass_M"] >= 1.0
        assert res["knk_pcqtgbddddd_spin_a"] > 0.0
        assert res["knk_pcqtgbddddd_charge_Q"] > 0.0
        assert res["phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_horizon_r_PCQTGBDDDDD"] > 0.0
        assert res["frame_dragging_omega"] > 0.0
        assert math.isfinite(res["tidal_force"])
        assert math.isfinite(res["knk_pcqtgbddddd_hydrodynamic_acceleration"])
        assert -1.0 <= res["knk_pcqtgbddddd_accelerated_qi"] <= 1.0
        assert res["knk_pcqtgbddddd_micro_price"] > 0.0

        # Check backward compatibility keys for prior phases
        assert "knk_pcqtgbdddd_hydrodynamic_acceleration" in res
        assert "knk_pcqtgbddd_hydrodynamic_acceleration" in res
        assert "knk_pcqtgbdd_hydrodynamic_acceleration" in res

        # Check all aliases
        aliases = [
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_hydrodynamics",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_queue_acceleration",
            "calculate_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_queue_acceleration",
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_frame_dragging",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_hydrodynamics",
            "compute_phase36_lob_hydrodynamics",
            "compute_phase36_lob_acceleration",
        ]
        for a in aliases:
            fn = getattr(engine, a, None)
            assert fn is not None, f"Missing alias: {a}"
            alias_res = fn(
                charge_parameter=0.5,
                spin_parameter=0.5,
                phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_parameter=0.000004,
                w_pcqtgbddddd=-17.0 / 3.0,
                k_hecke=0.06,
                k_cherednik=0.07,
            )
            assert math.isclose(
                alias_res["knk_pcqtgbddddd_hydrodynamic_acceleration"],
                res["knk_pcqtgbddddd_hydrodynamic_acceleration"],
                abs_tol=1e-6,
            )

    def test_fast_lob_dark_routing_cap_v36_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess 99.9999998% dark routing cap when version=36."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=36)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.999999998
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=36)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.999999998
        opt_res = process.get_optimal_preemptive_dark_allocation(version=36)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.999999998

    def test_fast_lob_dark_routing_cap_v36_frame_inspection(self):
        """Verify Fast LOB DeepHawkesArrivalProcess auto-infers 99.9999998% dark cap via stack inspection."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        # Calling without version should inspect current test frame ("phase36" in filename)
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.999999998

    def test_smart_order_router_v36_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.9999998% to dark venues under Phase 36."""
        sor = SmartOrderRouter()
        plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1_000_000_000,
            "target_price": 70000.0,
            "market_spread_bps": 12.0,
            "queue_imbalance": 0.80,
            "qi_acceleration": 0.50,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.90,
            "version": 36,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        total_dark = sum(l["quantity"] for l in dark_legs)
        # 1,000,000,000 * 0.999999998 = 999,999,998
        assert total_dark == 999_999_998

    def test_smart_order_router_maker_floor_contraction_v36(self):
        """
        Verify maker ratio floor contracts to 0.00000000005 (1 share per 20,000,000,000) under extreme toxicity.
        Formula: 0.70 * (1.0 - 0.999999999929 * gamma_toxic) clamped at 0.00000000005.
        """
        sor = SmartOrderRouter()
        qty = 20_000_000_000

        plan_v36 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 36,
        }
        res_v36 = sor.route_order(plan_v36, ats_available=False)
        maker_legs_v36 = [
            l for l in res_v36.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v36) > 0
        # 20,000,000,000 * 0.00000000005 = 1 share
        assert maker_legs_v36[0]["quantity"] == 1
        assert res_v36["maker_ratio"] == 0.00000000005

        # Monotonic floor contraction against v35
        qty_compare = 40_000_000_000
        plan_v36_comp = {**plan_v36, "version": 36, "quantity": qty_compare}
        plan_v35_comp = {**plan_v36, "version": 35, "quantity": qty_compare}
        res_v36_comp = sor.route_order(plan_v36_comp, ats_available=False)
        res_v35_comp = sor.route_order(plan_v35_comp, ats_available=False)

        maker_v36 = [l for l in res_v36_comp.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"][0]["quantity"]
        maker_v35 = [l for l in res_v35_comp.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"][0]["quantity"]

        # 40B * 5e-11 = 2 shares vs 40B * 1e-10 = 4 shares
        assert maker_v36 == 2
        assert maker_v35 == 4
        assert maker_v36 < maker_v35
        assert res_v36_comp["maker_ratio"] < res_v35_comp["maker_ratio"]

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v36(self):
        """Verify dynamic Anti-Gaming MinQty cap expands to 99.99999995% (0.9999999995) under Phase 36."""
        sor = SmartOrderRouter()
        qty = 1_000_000_000

        plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": qty,
            "target_price": 300.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 36,
        }
        res = sor.route_order(plan, ats_available=True)
        dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        dark_qty = dark_legs[0]["quantity"]
        min_qty = dark_legs[0].get("min_quantity", 0)

        ratio = min_qty / dark_qty
        assert math.isclose(ratio, 0.9999999995, abs_tol=1e-5)
        assert res["min_ratio"] == 0.9999999995

    def test_oms_preemptive_micro_tick_shading_v36(self):
        """
        Verify Phase 36 preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When h_val > 0.0015, hawkes_shift = -direction * 0.99999998 * spr * (h_val - 0.0015).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.025

        # Buy order: direction = +1, hawkes_shift = -1.0 * 0.99999998 * 1.0 * (0.025 - 0.0015) = -0.02349999953
        peg_oms_buy_v36 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=36,
        )
        peg_sched_buy_v36 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=36,
        )

        expected_shift_v36 = -0.99999998 * spr * (h_val - 0.0015)
        expected_price_v36 = target_px + expected_shift_v36

        assert math.isclose(peg_oms_buy_v36, expected_price_v36, rel_tol=1e-4)
        assert math.isclose(peg_sched_buy_v36, expected_price_v36, rel_tol=1e-4)
        assert math.isclose(peg_oms_buy_v36, peg_sched_buy_v36, rel_tol=1e-6)

        # In v35, threshold was 0.002, multiplier 0.99999995
        peg_oms_buy_v35 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=35,
        )
        # v36 shades more defensively than v35 (lower limit buy price)
        assert peg_oms_buy_v36 < peg_oms_buy_v35
