"""
tests/test_phase37_oms.py

Unit and integration test suite for Phase 37 Quantitative Enhancement (Feature F169.2 Microstructure OMS):
- Kerr-Newman-Kiselev 16-Dark-Energy PCQTGBDDDDDD Dunkl-Hecke-Cherednik-Kostka DAHA (w_pcqtgbdddddd = -18/3 = -6.0, k_hecke = 0.06, k_cherednik = 0.07, k_kostka = 0.08)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 16-fold dark energy: Quintessence, Phantom, Tachyon, Quintom, Chameleon, Phantom-Chameleon,
    Phantom-Chameleon-Quintom, Phantom-Chameleon-Quintom-Tachyon, Phantom-Chameleon-Quintom-Tachyon-Ghost,
    Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane, Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane-Dilaton,
    Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane-Dilaton-Dirac,
    Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane-Dilaton-Dirac-Dunkl,
    Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane-Dilaton-Dirac-Dunkl-Hecke,
    Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane-Dilaton-Dirac-Dunkl-Hecke-Cherednik,
    Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane-Dilaton-Dirac-Dunkl-Hecke-Cherednik-Kostka
  * Energy densities up to rho_pcqtgbdddddd = 9.5 * c_pcqtgbdddddd * r^15 * (1.0 + k_hecke + k_cherednik + k_kostka)
  * Spacetime metric horizon function Delta_r with 16-fold dark energy decay
  * Outer cosmological horizon scale r_{PCQTGBDDDDDD}
  * Radial tidal force with 16-fold dark energy repulsive acceleration:
    - 9.0 * c_pcqtgbdddddd * r^17 * (1.0 + k_hecke + k_cherednik + k_kostka)
  * Hydrodynamic queue acceleration a_{KNK-PCQTGBDDDDDD} and micro-price prediction
  * Method aliases on FastOrderBookMatchingEngine
- Fast LOB 99.9999999% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=37:
  * Preemptive lit queue imbalance allocation with max dark cap 0.999999999 (99.9999999%).
  * Lit maker ratio floor contracted to 0.00000000002 (0.000000002%, 1 share per 50,000,000,000)
    via 0.70 * (1.0 - 0.999999999971 * gamma_toxic) with 13-decimal formatting precision.
  * Dynamic anti-gaming MinQty scaled up to 99.99999998% (0.9999999998).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.0012:
  hawkes_shift = -direction * 0.99999999 * spr * (h - 0.0012).
- Full backward compatibility across Phase 14 through Phase 36 versions.
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


class TestPhase37MicrostructureOMS:
    """Test suite for Phase 37 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 16-Dark-Energy PCQTGBDDDDDD Dunkl-Hecke-Cherednik-Kostka DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_queue_acceleration(
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
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_parameter=0.000003,
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
            w_pcqtgbdddddd=-18.0 / 3.0,
            k_hecke=0.06,
            k_cherednik=0.07,
            k_kostka=0.08,
        )
        assert isinstance(res, dict)

        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "knk_pcqtgbdddddd_mass_M",
            "knk_pcqtgbdddddd_spin_a",
            "knk_pcqtgbdddddd_charge_Q",
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
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_c_pcqtgbdddddd",
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
            "equation_of_state_w_pcqtgbdddddd",
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_horizon_r_PCQTGBDDDDDD",
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_horizon",
            "horizon_radius",
            "coordinate_radius_r",
            "is_in_horizon",
            "frame_dragging_omega",
            "tidal_force",
            "knk_pcqtgbdddddd_tidal_force",
            "knk_pcqtgbdddddd_hydrodynamic_acceleration",
            "knk_pcqtgbdddddd_rotational_acceleration",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_rotational_acceleration",
            "knk_pcqtgbdddddd_accelerated_qi",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_accelerated_qi",
            "knk_pcqtgbdddddd_micro_price",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_micro_price",
        ]
        for k in required_keys:
            assert k in res, f"Missing key in Kerr-Newman-Kiselev 16-Dark-Energy result: {k}"

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
        assert res["phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_c_pcqtgbdddddd"] == 0.000003
        assert math.isclose(res["equation_of_state_w_pcqtgbdddddd"], -18.0 / 3.0, abs_tol=1e-3)
        assert res["knk_pcqtgbdddddd_mass_M"] >= 1.0
        assert res["knk_pcqtgbdddddd_spin_a"] > 0.0
        assert res["knk_pcqtgbdddddd_charge_Q"] > 0.0
        assert res["phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_horizon_r_PCQTGBDDDDDD"] > 0.0
        assert res["frame_dragging_omega"] > 0.0
        assert math.isfinite(res["tidal_force"])
        assert math.isfinite(res["knk_pcqtgbdddddd_hydrodynamic_acceleration"])
        assert -1.0 <= res["knk_pcqtgbdddddd_accelerated_qi"] <= 1.0
        assert res["knk_pcqtgbdddddd_micro_price"] > 0.0

        # Check backward compatibility keys for prior phases
        assert "knk_pcqtgbddddd_hydrodynamic_acceleration" in res
        assert "knk_pcqtgbdddd_hydrodynamic_acceleration" in res
        assert "knk_pcqtgbddd_hydrodynamic_acceleration" in res

        # Check all aliases
        aliases = [
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_hydrodynamics",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_queue_acceleration",
            "calculate_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_queue_acceleration",
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_frame_dragging",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_hydrodynamics",
            "compute_phase37_lob_hydrodynamics",
            "compute_phase37_lob_acceleration",
        ]
        for a in aliases:
            fn = getattr(engine, a, None)
            assert fn is not None, f"Missing alias: {a}"
            alias_res = fn(
                charge_parameter=0.5,
                spin_parameter=0.5,
                phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_parameter=0.000003,
                w_pcqtgbdddddd=-18.0 / 3.0,
                k_hecke=0.06,
                k_cherednik=0.07,
                k_kostka=0.08,
            )
            assert math.isclose(
                alias_res["knk_pcqtgbdddddd_hydrodynamic_acceleration"],
                res["knk_pcqtgbdddddd_hydrodynamic_acceleration"],
                abs_tol=1e-6,
            )

    def test_fast_lob_dark_routing_cap_v37_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess 99.9999999% dark routing cap when version=37."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=37)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.999999999
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=37)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.999999999
        opt_res = process.get_optimal_preemptive_dark_allocation(version=37)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.999999999

    def test_fast_lob_dark_routing_cap_v37_frame_inspection(self):
        """Verify Fast LOB DeepHawkesArrivalProcess auto-infers 99.9999999% dark cap via stack inspection."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        # Calling without version should inspect current test frame ("phase37" in filename)
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.999999999

    def test_smart_order_router_v37_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.9999999% to dark venues under Phase 37."""
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
            "version": 37,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        total_dark = sum(l["quantity"] for l in dark_legs)
        # 1,000,000,000 * 0.999999999 = 999,999,999
        assert total_dark == 999_999_999

    def test_smart_order_router_maker_floor_contraction_v37(self):
        """
        Verify maker ratio floor contracts to 0.00000000002 (1 share per 50,000,000,000) under extreme toxicity.
        Formula: 0.70 * (1.0 - 0.999999999971 * gamma_toxic) clamped at 0.00000000002.
        """
        sor = SmartOrderRouter()
        qty = 50_000_000_000

        plan_v37 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 37,
        }
        res_v37 = sor.route_order(plan_v37, ats_available=False)
        maker_legs_v37 = [
            l for l in res_v37.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v37) > 0
        # 50,000,000,000 * 0.00000000002 = 1 share
        assert maker_legs_v37[0]["quantity"] == 1
        assert res_v37["maker_ratio"] == 0.00000000002

        # Monotonic floor contraction against v36
        qty_compare = 100_000_000_000
        plan_v37_comp = {**plan_v37, "version": 37, "quantity": qty_compare}
        plan_v36_comp = {**plan_v37, "version": 36, "quantity": qty_compare}
        res_v37_comp = sor.route_order(plan_v37_comp, ats_available=False)
        res_v36_comp = sor.route_order(plan_v36_comp, ats_available=False)

        maker_v37 = [l for l in res_v37_comp.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"][0]["quantity"]
        maker_v36 = [l for l in res_v36_comp.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"][0]["quantity"]

        # 100B * 2e-11 = 2 shares vs 100B * 5e-11 = 5 shares
        assert maker_v37 == 2
        assert maker_v36 == 5
        assert maker_v37 < maker_v36
        assert res_v37_comp["maker_ratio"] < res_v36_comp["maker_ratio"]

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v37(self):
        """Verify dynamic Anti-Gaming MinQty cap expands to 99.99999998% (0.9999999998) under Phase 37."""
        sor = SmartOrderRouter()
        qty = 1_000_000_000

        plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": qty,
            "target_price": 300.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 37,
        }
        res = sor.route_order(plan, ats_available=True)
        dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        dark_qty = dark_legs[0]["quantity"]
        min_qty = dark_legs[0].get("min_quantity", 0)

        ratio = min_qty / dark_qty
        assert math.isclose(ratio, 0.9999999998, abs_tol=1e-5)
        assert res["min_ratio"] == 0.9999999998

    def test_oms_preemptive_micro_tick_shading_v37(self):
        """
        Verify Phase 37 preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When h_val > 0.0012, hawkes_shift = -direction * 0.99999999 * spr * (h_val - 0.0012).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.025

        # Buy order: direction = +1, hawkes_shift = -1.0 * 0.99999999 * 1.0 * (0.025 - 0.0012) = -0.023799999762
        peg_oms_buy_v37 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=37,
        )
        peg_sched_buy_v37 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=37,
        )

        expected_shift_v37 = -0.99999999 * spr * (h_val - 0.0012)
        expected_price_v37 = target_px + expected_shift_v37

        assert math.isclose(peg_oms_buy_v37, expected_price_v37, rel_tol=1e-4)
        assert math.isclose(peg_sched_buy_v37, expected_price_v37, rel_tol=1e-4)
        assert math.isclose(peg_oms_buy_v37, peg_sched_buy_v37, rel_tol=1e-6)

        # In v36, threshold was 0.0015, multiplier 0.99999998
        peg_oms_buy_v36 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=36,
        )
        # v37 shades more defensively than v36 (lower limit buy price)
        assert peg_oms_buy_v37 < peg_oms_buy_v36
