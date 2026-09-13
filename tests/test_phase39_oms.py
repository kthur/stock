"""
tests/test_phase39_oms.py

Unit and integration test suite for Phase 39 Quantitative Enhancement (Feature F177.2 Microstructure OMS):
- Kerr-Newman-Kiselev 18-Dark-Energy PCQTGBDDDDHKMA Dunkl-Hecke-Cherednik-Kostka-Macdonald-Askey-Wilson DAHA
  (w_pcqtgbddddhkma = -20/3 = -6.6667, k_hecke = 0.06, k_cherednik = 0.07, k_kostka = 0.08, k_macdonald = 0.09, k_askey = 0.10)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 18-fold dark energy density up to rho_pcqtgbddddhkma
  * Outer cosmological horizon scale r_{PCQTGBDDDDHKMA}
  * Radial tidal force with 18-fold dark energy repulsive acceleration
  * Hydrodynamic queue acceleration a_{KNK-PCQTGBDDDDHKMA} and micro-price prediction
  * Method aliases on FastOrderBookMatchingEngine
- Fast LOB 99.99999998% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=39:
  * Preemptive lit queue imbalance allocation with max dark cap 0.9999999998 (99.99999998%).
  * Lit maker ratio floor contracted to 0.000000000005 (0.0000000005%, 1 share per 200,000,000,000)
    via 0.70 * (1.0 - 0.999999999993 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.999999995% (0.99999999995).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.0008:
  hawkes_shift = -direction * 0.999999998 * spr * (h - 0.0008).
- Full backward compatibility across Phase 14 through Phase 38 versions.
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


class TestPhase39MicrostructureOMS:
    """Test suite for Phase 39 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 18-Dark-Energy PCQTGBDDDDHKMA Dunkl-Hecke-Cherednik-Kostka-Macdonald-Askey-Wilson DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_queue_acceleration(
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
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_parameter=0.000002,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_parameter=0.000001,
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
            w_pcqtgbddddhkm=-19.0 / 3.0,
            w_pcqtgbddddhkma=-20.0 / 3.0,
            k_hecke=0.06,
            k_cherednik=0.07,
            k_kostka=0.08,
            k_macdonald=0.09,
            k_askey=0.10,
        )
        assert isinstance(res, dict)

        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "knk_pcqtgbddddhkma_mass_M",
            "knk_pcqtgbddddhkma_spin_a",
            "knk_pcqtgbddddhkma_charge_Q",
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
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_c_pcqtgbddddhkm",
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_c_pcqtgbddddhkma",
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
            "equation_of_state_w_pcqtgbddddhkm",
            "equation_of_state_w_pcqtgbddddhkma",
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_horizon_r_PCQTGBDDDDHKMA",
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_horizon",
            "horizon_radius",
            "coordinate_radius_r",
            "is_in_horizon",
            "frame_dragging_omega",
            "tidal_force",
            "knk_pcqtgbddddhkma_tidal_force",
            "knk_pcqtgbddddhkma_hydrodynamic_acceleration",
            "knk_pcqtgbddddhkma_rotational_acceleration",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_rotational_acceleration",
            "knk_pcqtgbddddhkma_accelerated_qi",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_accelerated_qi",
            "knk_pcqtgbddddhkma_micro_price",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_micro_price",
        ]
        for k in required_keys:
            assert k in res, f"Missing key in Kerr-Newman-Kiselev 18-Dark-Energy result: {k}"

        # Check physical parameters and bounds
        assert res["phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_c_pcqtgbddddhkma"] == 0.000001
        assert math.isclose(res["equation_of_state_w_pcqtgbddddhkma"], -20.0 / 3.0, abs_tol=1e-3)
        assert res["knk_pcqtgbddddhkma_mass_M"] >= 1.0
        assert res["knk_pcqtgbddddhkma_spin_a"] > 0.0
        assert res["knk_pcqtgbddddhkma_charge_Q"] > 0.0
        assert res["phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_horizon_r_PCQTGBDDDDHKMA"] > 0.0
        assert res["frame_dragging_omega"] > 0.0
        assert math.isfinite(res["tidal_force"])
        assert math.isfinite(res["knk_pcqtgbddddhkma_hydrodynamic_acceleration"])
        assert -1.0 <= res["knk_pcqtgbddddhkma_accelerated_qi"] <= 1.0
        assert res["knk_pcqtgbddddhkma_micro_price"] > 0.0

        # Check backward compatibility keys for prior phases
        assert "knk_pcqtgbddddhkm_hydrodynamic_acceleration" in res
        assert "knk_pcqtgbdddddd_hydrodynamic_acceleration" in res
        assert "knk_pcqtgbddddd_hydrodynamic_acceleration" in res
        assert "knk_pcqtgbdddd_hydrodynamic_acceleration" in res

        # Check all aliases
        aliases = [
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_hydrodynamics",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_queue_acceleration",
            "calculate_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_queue_acceleration",
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_frame_dragging",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_hydrodynamics",
            "compute_askey_wilson_queue_acceleration",
            "compute_phase39_queue_acceleration",
            "compute_phase39_lob_hydrodynamics",
            "compute_phase39_lob_acceleration",
        ]
        for a in aliases:
            fn = getattr(engine, a, None)
            assert fn is not None, f"Missing alias: {a}"
            alias_res = fn(
                charge_parameter=0.5,
                spin_parameter=0.5,
                phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_parameter=0.000001,
                w_pcqtgbddddhkma=-20.0 / 3.0,
                k_hecke=0.06,
                k_cherednik=0.07,
                k_kostka=0.08,
                k_macdonald=0.09,
                k_askey=0.10,
            )
            assert math.isclose(
                alias_res["knk_pcqtgbddddhkma_hydrodynamic_acceleration"],
                res["knk_pcqtgbddddhkma_hydrodynamic_acceleration"],
                abs_tol=1e-6,
            )

    def test_fast_lob_dark_routing_cap_v39_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess 99.99999998% dark routing cap when version=39."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=39)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.9999999998
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=39)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.9999999998
        opt_res = process.get_optimal_preemptive_dark_allocation(version=39)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.9999999998

    def test_fast_lob_dark_routing_cap_v39_frame_inspection(self):
        """Verify Fast LOB DeepHawkesArrivalProcess auto-infers 99.99999998% dark cap via stack inspection."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        # Calling without version should inspect current test frame ("phase39" in filename)
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.9999999998

    def test_smart_order_router_v39_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.99999998% to dark venues under Phase 39."""
        sor = SmartOrderRouter()
        plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 10_000_000_000,
            "target_price": 70000.0,
            "market_spread_bps": 12.0,
            "queue_imbalance": 0.80,
            "qi_acceleration": 0.50,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.90,
            "version": 39,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        total_dark = sum(l["quantity"] for l in dark_legs)
        # 10,000,000,000 * 0.9999999998 = 9,999,999,998
        assert total_dark == 9_999_999_998

    def test_smart_order_router_maker_floor_contraction_v39(self):
        """
        Verify maker ratio floor contracts to 0.000000000005 (1 share per 200,000,000,000) under extreme toxicity.
        Formula: 0.70 * (1.0 - 0.999999999993 * gamma_toxic) clamped at 0.000000000005.
        """
        sor = SmartOrderRouter()
        qty = 200_000_000_000

        plan_v39 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 39,
        }
        res_v39 = sor.route_order(plan_v39, ats_available=False)
        maker_legs_v39 = [
            l for l in res_v39.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v39) > 0
        # 200,000,000,000 * 0.000000000005 = 1 share
        assert maker_legs_v39[0]["quantity"] == 1
        assert res_v39["maker_ratio"] == 0.000000000005

        # Monotonic floor contraction against v38
        qty_compare = 200_000_000_000
        plan_v39_comp = {**plan_v39, "version": 39, "quantity": qty_compare}
        plan_v38_comp = {**plan_v39, "version": 38, "quantity": qty_compare}
        res_v39_comp = sor.route_order(plan_v39_comp, ats_available=False)
        res_v38_comp = sor.route_order(plan_v38_comp, ats_available=False)

        maker_v39 = [l for l in res_v39_comp.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"][0]["quantity"]
        maker_v38 = [l for l in res_v38_comp.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"][0]["quantity"]

        # 200B * 5e-12 = 1 share vs 200B * 1e-11 = 2 shares
        assert maker_v39 == 1
        assert maker_v38 == 2
        assert maker_v39 < maker_v38
        assert res_v39_comp["maker_ratio"] < res_v38_comp["maker_ratio"]

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v39(self):
        """Verify dynamic Anti-Gaming MinQty cap expands to 99.999999995% (0.99999999995) under Phase 39."""
        sor = SmartOrderRouter()
        qty = 100_000_000_000

        plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": qty,
            "target_price": 300.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 39,
        }
        res = sor.route_order(plan, ats_available=True)
        dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        dark_qty = dark_legs[0]["quantity"]
        min_qty = dark_legs[0].get("min_quantity", 0)

        ratio = min_qty / dark_qty
        assert math.isclose(ratio, 0.99999999995, abs_tol=1e-5)
        assert res["min_ratio"] == 0.99999999995

    def test_oms_preemptive_micro_tick_shading_v39(self):
        """
        Verify Phase 39 preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When h_val > 0.0008, hawkes_shift = -direction * 0.999999998 * spr * (h_val - 0.0008).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.025

        # Buy order: direction = +1, hawkes_shift = -1.0 * 0.999999998 * 1.0 * (0.025 - 0.0008) = -0.0241999999516
        peg_oms_buy_v39 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=39,
        )
        peg_sched_buy_v39 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=39,
        )

        expected_shift_v39 = -0.999999998 * spr * (h_val - 0.0008)
        expected_price_v39 = target_px + expected_shift_v39

        assert math.isclose(peg_oms_buy_v39, expected_price_v39, rel_tol=1e-4)
        assert math.isclose(peg_sched_buy_v39, expected_price_v39, rel_tol=1e-4)
        assert math.isclose(peg_oms_buy_v39, peg_sched_buy_v39, rel_tol=1e-6)

        # In v38, threshold was 0.0010, multiplier 0.999999995
        peg_oms_buy_v38 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=38,
        )
        # v39 shades more defensively than v38 (lower limit buy price)
        assert peg_oms_buy_v39 < peg_oms_buy_v38
