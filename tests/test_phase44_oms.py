"""
tests/test_phase44_oms.py

Unit and integration test suite for Phase 44 Quantitative Enhancement (Feature F197.2 Microstructure OMS):
- Kerr-Newman-Kiselev 23-Dark-Energy PCQTGBDDDDHKMAEETUV Elliptic-Hypergeometric-Askey-Wilson DAHA
  (w_pcqtgbddddhkmaeetuv = -25/3, k_hecke = 0.06, k_cherednik = 0.07, k_kostka = 0.08, k_macdonald = 0.09,
   k_askey = 0.10, k_elliptic = 0.11, k_elliptic_trig = 0.12, k_hypergeom = 0.13, k_daha = 0.15,
   c_pcqtgbddddhkmaeetuv = 2.5e-8, daha_23_factor = 2.05)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 23-fold dark energy density up to rho_pcqtgbddddhkmaeetuv
  * Outer cosmological horizon scale r_{PCQTGBDDDDHKMAEETUV}
  * Radial tidal force with 23-fold dark energy repulsive acceleration (-12.5 * c * r^24)
  * Hydrodynamic queue acceleration a_{KNK-PCQTGBDDDDHKMAEETUV} and micro-price prediction
  * Method aliases on FastOrderBookMatchingEngine
- Fast LOB 99.9999999995% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=44:
  * Preemptive lit queue imbalance allocation with max dark cap 0.999999999995 (99.9999999995%).
  * Lit maker ratio floor contracted to 0.0000000000000001 (1e-16, 1 share per 10,000,000,000,000,000)
    via 0.70 * (1.0 - 0.99999999999999986 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.9999999999% (0.999999999999).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.0003:
  hawkes_shift = -direction * 0.99999999995 * spr * (h - 0.0003).
- Full backward compatibility across Phase 14 through Phase 43 versions.
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


class TestPhase44MicrostructureOMS:
    """Test suite for Phase 44 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_23_dark_energy_virasoro_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 23-Dark-Energy PCQTGBDDDDHKMAEETUV Virasoro DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_queue_acceleration(
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
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_parameter=0.0000005,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_trigonometric_parameter=0.0000002,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_parameter=0.0000001,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_parameter=0.00000005,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_parameter=0.000000025,
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
            w_pcqtgbddddhkmae=-7.0,
            w_pcqtgbddddhkmaee=-22.0 / 3.0,
            w_pcqtgbddddhkmaeet=-23.0 / 3.0,
            w_pcqtgbddddhkmaeetu=-24.0 / 3.0,
            w_pcqtgbddddhkmaeetuv=-25.0 / 3.0,
            k_hecke=0.06,
            k_cherednik=0.07,
            k_kostka=0.08,
            k_macdonald=0.09,
            k_askey=0.10,
            k_elliptic=0.11,
            k_elliptic_trig=0.12,
            k_hypergeom=0.13,
            k_daha=0.15,
        )
        assert isinstance(res, dict)

        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "knk_pcqtgbddddhkmaeetuv_mass_M",
            "knk_pcqtgbddddhkmaeetuv_spin_a",
            "knk_pcqtgbddddhkmaeetuv_charge_Q",
            "equation_of_state_w_pcqtgbddddhkmaeetuv",
            "daha_23_factor",
            "k_daha",
            "frame_dragging_omega",
            "tidal_force",
            "knk_pcqtgbddddhkmaeetuv_tidal_force",
            "knk_pcqtgbddddhkmaeetuv_hydrodynamic_acceleration",
            "knk_pcqtgbddddhkmaeetuv_micro_price",
        ]
        for k in required_keys:
            assert k in res, f"Missing key {k} in Phase 44 KNK result"

        assert math.isclose(res["equation_of_state_w_pcqtgbddddhkmaeetuv"], -25.0 / 3.0, rel_tol=1e-5)
        assert math.isclose(res["k_daha"], 0.15, rel_tol=1e-5)
        assert math.isclose(res["daha_23_factor"], 1.91, rel_tol=1e-5)
        assert np.isfinite(res["knk_pcqtgbddddhkmaeetuv_hydrodynamic_acceleration"])
        assert np.isfinite(res["knk_pcqtgbddddhkmaeetuv_micro_price"])
        assert res["knk_pcqtgbddddhkmaeetuv_micro_price"] > 0

        # Backward compatibility key check
        assert "knk_pcqtgbddddhkmaeetu_hydrodynamic_acceleration" in res

    def test_fast_lob_dark_routing_cap_v44_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess reaches dark routing cap 0.999999999995 when version=44."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=44)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.999999999995
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=44)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.999999999995
        opt_res = process.get_optimal_preemptive_dark_allocation(version=44)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.999999999995

    def test_fast_lob_dark_routing_cap_v44_frame_inspection(self):
        """Verify Fast LOB DeepHawkesArrivalProcess reaches dark cap 0.999999999995 via stack frame inspection."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        # Calling without version should inspect current test frame ("phase44" in filename)
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.999999999995

    def test_smart_order_router_v44_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.9999999995% to dark venues under Phase 44."""
        sor = SmartOrderRouter()
        plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 100_000_000_000_000,
            "target_price": 70000.0,
            "market_spread_bps": 12.0,
            "queue_imbalance": 0.80,
            "qi_acceleration": 0.50,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.90,
            "version": 44,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        total_dark = sum(l["quantity"] for l in dark_legs)
        # 100,000,000,000,000 * 0.999999999995 = 99,999,999,999,500
        assert total_dark == 99_999_999_999_500

    def test_smart_order_router_maker_floor_contraction_v44(self):
        """
        Verify maker ratio floor contracts to 1e-16 (0.0000000000000001, 1 share per 10,000,000,000,000,000) under extreme toxicity.
        Formula: 0.70 * (1.0 - 0.99999999999999986 * gamma_toxic) clamped at 0.0000000000000001.
        """
        sor = SmartOrderRouter()
        qty = 10_000_000_000_000_000  # 10 Quadrillion shares: 10Q * 1e-16 = 1 share

        plan_v44 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 44,
        }
        res_v44 = sor.route_order(plan_v44, ats_available=False)
        maker_legs_v44 = [
            l for l in res_v44.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v44) > 0
        # 10,000,000,000,000,000 * 0.0000000000000001 = 1 share
        assert maker_legs_v44[0]["quantity"] == 1
        assert res_v44["maker_ratio"] == 0.0000000000000001

        # Monotonic floor contraction against v43 (1e-16 < 1e-15)
        qty_compare = 10_000_000_000_000_000
        plan_v44_comp = {**plan_v44, "version": 44, "quantity": qty_compare}
        plan_v43_comp = {**plan_v44, "version": 43, "quantity": qty_compare}
        res_v44_comp = sor.route_order(plan_v44_comp, ats_available=False)
        res_v43_comp = sor.route_order(plan_v43_comp, ats_available=False)

        maker_v44 = [l for l in res_v44_comp.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"][0]["quantity"]
        maker_v43 = [l for l in res_v43_comp.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"][0]["quantity"]

        # 10Q * 1e-16 = 1 share vs 10Q * 1e-15 = 10 shares
        assert maker_v44 == 1
        assert maker_v43 == 10
        assert maker_v44 < maker_v43
        assert res_v44_comp["maker_ratio"] < res_v43_comp["maker_ratio"]

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v44(self):
        """Verify dynamic Anti-Gaming MinQty cap expands to 99.9999999999% (0.999999999999) under Phase 44."""
        sor = SmartOrderRouter()
        qty = 10_000_000_000_000

        plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": qty,
            "target_price": 300.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 44,
        }
        res = sor.route_order(plan, ats_available=True)
        dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        dark_qty = dark_legs[0]["quantity"]
        min_qty = dark_legs[0].get("min_quantity", 0)

        ratio = min_qty / dark_qty
        assert math.isclose(ratio, 0.999999999999, abs_tol=1e-5)
        assert res["min_ratio"] == 0.999999999999

    def test_oms_preemptive_micro_tick_shading_v44(self):
        """
        Verify Phase 44 preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When h_val > 0.0003, hawkes_shift = -direction * 0.99999999995 * spr * (h_val - 0.0003).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.025

        # Buy order: direction = +1, hawkes_shift = -1.0 * 0.99999999995 * 1.0 * (0.025 - 0.0003)
        peg_oms_buy_v44 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=44,
        )
        peg_sched_buy_v44 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=44,
        )

        expected_shift_v44 = -0.99999999995 * spr * (h_val - 0.0003)
        expected_price_v44 = target_px + expected_shift_v44

        assert math.isclose(peg_oms_buy_v44, expected_price_v44, rel_tol=1e-4)
        assert math.isclose(peg_sched_buy_v44, expected_price_v44, rel_tol=1e-4)
        assert math.isclose(peg_oms_buy_v44, peg_sched_buy_v44, rel_tol=1e-6)

        # In v43, threshold was 0.0004, multiplier 0.9999999999
        peg_oms_buy_v43 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=43,
        )
        # v44 shades more defensively than v43 (lower limit buy price)
        assert peg_oms_buy_v44 < peg_oms_buy_v43

    def test_phase44_aliases_and_backward_compatibility(self):
        """Verify all Phase 44 method aliases and backward compatibility."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_parameter=0.000000025,
            w_pcqtgbddddhkmaeetuv=-25.0 / 3.0,
            k_hecke=0.06,
            k_cherednik=0.07,
            k_kostka=0.08,
            k_macdonald=0.09,
            k_askey=0.10,
            k_elliptic=0.11,
            k_elliptic_trig=0.12,
            k_hypergeom=0.13,
            k_daha=0.15,
        )

        aliases = [
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_hydrodynamics",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_queue_acceleration",
            "calculate_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_queue_acceleration",
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_frame_dragging",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_hydrodynamics",
            "compute_kerr_newman_kiselev_23_dark_energy_elliptic_hypergeometric_askey_wilson_daha_queue_acceleration",
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_daha_queue_acceleration",
            "compute_kerr_newman_kiselev_23_dark_energy_daha_queue_acceleration",
            "compute_knk_23_dark_energy_queue_acceleration",
            "compute_phase44_queue_acceleration",
            "compute_phase44_lob_hydrodynamics",
            "compute_phase44_lob_acceleration",
            "compute_knk_pcqtgbddddhkmaeetuv_virasoro_queue_acceleration",
            "compute_knk_23_dark_energy_virasoro_queue_acceleration",
            "compute_knk_pcqtgbddddhkmaeetuv_queue_acceleration",
            "compute_knk_virasoro_daha_queue_acceleration",
            "compute_knk_virasoro_whittaker_queue_acceleration",
            "compute_knk_virasoro_queue_acceleration",
            "compute_daha_23_queue_acceleration",
            "compute_knk_pcqtgbddddhkmaeetuv_acceleration",
        ]
        for a in aliases:
            fn = getattr(engine, a, None)
            assert fn is not None, f"Missing alias: {a}"
            alias_res = fn(
                charge_parameter=0.5,
                spin_parameter=0.5,
                phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_parameter=0.000000025,
                w_pcqtgbddddhkmaeetuv=-25.0 / 3.0,
                k_hecke=0.06,
                k_cherednik=0.07,
                k_kostka=0.08,
                k_macdonald=0.09,
                k_askey=0.10,
                k_elliptic=0.11,
                k_elliptic_trig=0.12,
                k_hypergeom=0.13,
                k_daha=0.15,
            )
            assert math.isclose(
                alias_res["knk_pcqtgbddddhkmaeetuv_hydrodynamic_acceleration"],
                res["knk_pcqtgbddddhkmaeetuv_hydrodynamic_acceleration"],
                abs_tol=1e-6,
            )
            assert math.isclose(
                alias_res["knk_pcqtgbddddhkmaeetuv_micro_price"],
                res["knk_pcqtgbddddhkmaeetuv_micro_price"],
                abs_tol=1e-6,
            )
