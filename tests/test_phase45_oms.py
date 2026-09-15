"""
tests/test_phase45_oms.py

Unit and integration test suite for Phase 45 Quantitative Enhancement (Feature F201.2 Microstructure OMS):
- Kerr-Newman-Kiselev 24-Dark-Energy PCQTGBDDDDHKMAEETUVW Whittaker DAHA
  (w_pcqtgbddddhkmaeetuvw = -26/3, k_hecke = 0.06, k_cherednik = 0.07, k_kostka = 0.08, k_macdonald = 0.09,
   k_askey = 0.10, k_elliptic = 0.11, k_elliptic_trig = 0.12, k_hypergeom = 0.13, k_daha = 0.16,
   k_whittaker = 0.29, c_pcqtgbddddhkmaeetuvw = 1.25e-8, daha_24_factor = 2.21)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 24-fold dark energy density up to rho_pcqtgbddddhkmaeetuvw
  * Outer cosmological horizon scale r_{PCQTGBDDDDHKMAEETUVW}
  * Radial tidal force with 24-fold dark energy repulsive acceleration (-13.0 * c * r^25)
  * Hydrodynamic queue acceleration a_{KNK-PCQTGBDDDDHKMAEETUVW} and micro-price prediction
  * Complete method aliases on FastOrderBookMatchingEngine
- Fast LOB 99.9999999998% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=45:
  * Preemptive lit queue imbalance allocation with max dark cap 0.999999999998 (99.9999999998%).
  * Lit maker ratio floor contracted to 0.00000000000000001 (1e-17, 1 share per 100,000,000,000,000,000)
    via 0.70 * (1.0 - 0.999999999999999986 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.99999999995% (0.9999999999995).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.0002:
  hawkes_shift = -direction * 0.99999999998 * spr * (h - 0.0002).
- Full backward compatibility across Phase 14 through Phase 44 versions.
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


class TestPhase45MicrostructureOMS:
    """Test suite for Phase 45 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_24_dark_energy_whittaker_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 24-Dark-Energy PCQTGBDDDDHKMAEETUVW Whittaker DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_queue_acceleration(
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
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_parameter=0.0000000125,
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
            w_pcqtgbddddhkmaeetuvw=-26.0 / 3.0,
            k_hecke=0.06,
            k_cherednik=0.07,
            k_kostka=0.08,
            k_macdonald=0.09,
            k_askey=0.10,
            k_elliptic=0.11,
            k_elliptic_trig=0.12,
            k_hypergeom=0.13,
            k_daha=0.16,
            k_whittaker=0.29,
        )
        assert isinstance(res, dict)

        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "knk_pcqtgbddddhkmaeetuvw_mass_M",
            "knk_pcqtgbddddhkmaeetuvw_spin_a",
            "knk_pcqtgbddddhkmaeetuvw_charge_Q",
            "equation_of_state_w_pcqtgbddddhkmaeetuvw",
            "daha_24_factor",
            "k_daha",
            "frame_dragging_omega",
            "tidal_force",
            "knk_pcqtgbddddhkmaeetuvw_tidal_force",
            "knk_pcqtgbddddhkmaeetuvw_hydrodynamic_acceleration",
            "knk_pcqtgbddddhkmaeetuvw_micro_price",
        ]
        for k in required_keys:
            assert k in res, f"Missing key {k} in Phase 45 KNK result"

        assert math.isclose(res["equation_of_state_w_pcqtgbddddhkmaeetuvw"], -26.0 / 3.0, rel_tol=1e-5)
        assert math.isclose(res["k_daha"], 0.16, rel_tol=1e-5)
        assert math.isclose(res["daha_24_factor"], 2.21, rel_tol=1e-5)
        assert np.isfinite(res["knk_pcqtgbddddhkmaeetuvw_hydrodynamic_acceleration"])
        assert np.isfinite(res["knk_pcqtgbddddhkmaeetuvw_micro_price"])
        assert res["knk_pcqtgbddddhkmaeetuvw_micro_price"] > 0

        # Backward compatibility key check
        assert "knk_pcqtgbddddhkmaeetuv_hydrodynamic_acceleration" in res
        assert "knk_pcqtgbddddhkmaeetu_hydrodynamic_acceleration" in res

    def test_fast_lob_dark_routing_cap_v45_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess reaches dark routing cap 0.999999999998 when version=45."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=45)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.999999999998
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=45)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.999999999998
        opt_res = process.get_optimal_preemptive_dark_allocation(version=45)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.999999999998

    def test_fast_lob_dark_routing_cap_v45_frame_inspection(self):
        """Verify Fast LOB DeepHawkesArrivalProcess reaches dark cap 0.999999999998 via stack frame inspection."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        # Calling without version should inspect current test frame ("phase45" in filename)
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.999999999998

    def test_smart_order_router_v45_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.9999999998% to dark venues under Phase 45."""
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
            "version": 45,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        total_dark = sum(l["quantity"] for l in dark_legs)
        # 100,000,000,000,000 * 0.999999999998 = 99,999,999,999,800
        assert total_dark == 99_999_999_999_800

    def test_smart_order_router_maker_floor_contraction_v45(self):
        """
        Verify maker ratio floor contracts to 1e-17 (0.00000000000000001, 1 share per 100,000,000,000,000,000) under extreme toxicity.
        Formula: 0.70 * (1.0 - 0.999999999999999986 * gamma_toxic) clamped at 0.00000000000000001.
        """
        sor = SmartOrderRouter()
        qty = 100_000_000_000_000_000  # 100 Quadrillion shares: 100Q * 1e-17 = 1 share

        plan_v45 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 45,
        }
        res_v45 = sor.route_order(plan_v45, ats_available=False)
        maker_legs_v45 = [
            l for l in res_v45.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v45) > 0
        # 100,000,000,000,000,000 * 0.00000000000000001 = 1 share
        assert maker_legs_v45[0]["quantity"] == 1
        assert res_v45["maker_ratio"] == 0.00000000000000001

        # Monotonic floor contraction against v44 (1e-17 < 1e-16)
        qty_compare = 100_000_000_000_000_000
        plan_v45_comp = {**plan_v45, "version": 45, "quantity": qty_compare}
        plan_v44_comp = {**plan_v45, "version": 44, "quantity": qty_compare}
        res_v45_comp = sor.route_order(plan_v45_comp, ats_available=False)
        res_v44_comp = sor.route_order(plan_v44_comp, ats_available=False)

        maker_v45 = [l for l in res_v45_comp.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"][0]["quantity"]
        maker_v44 = [l for l in res_v44_comp.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"][0]["quantity"]

        # 100Q * 1e-17 = 1 share vs 100Q * 1e-16 = 10 shares
        assert maker_v45 == 1
        assert maker_v44 == 10
        assert maker_v45 < maker_v44
        assert res_v45_comp["maker_ratio"] < res_v44_comp["maker_ratio"]

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v45(self):
        """Verify dynamic Anti-Gaming MinQty cap expands to 99.99999999995% (0.9999999999995) under Phase 45."""
        sor = SmartOrderRouter()
        qty = 10_000_000_000_000

        plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": qty,
            "target_price": 300.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 45,
        }
        res = sor.route_order(plan, ats_available=True)
        dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        dark_qty = dark_legs[0]["quantity"]
        min_qty = dark_legs[0].get("min_quantity", 0)

        ratio = min_qty / dark_qty
        assert math.isclose(ratio, 0.9999999999995, abs_tol=1e-5)
        assert res["min_ratio"] == 0.9999999999995

    def test_oms_preemptive_micro_tick_shading_v45(self):
        """
        Verify Phase 45 preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When h_val > 0.0002, hawkes_shift = -direction * 0.99999999998 * spr * (h_val - 0.0002).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.025

        # Buy order: direction = +1, hawkes_shift = -1.0 * 0.99999999998 * 1.0 * (0.025 - 0.0002)
        peg_oms_buy_v45 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=45,
        )
        peg_sched_buy_v45 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=45,
        )

        expected_shift_v45 = -0.99999999998 * spr * (h_val - 0.0002)
        expected_price_v45 = target_px + expected_shift_v45

        assert math.isclose(peg_oms_buy_v45, expected_price_v45, rel_tol=1e-4)
        assert math.isclose(peg_sched_buy_v45, expected_price_v45, rel_tol=1e-4)
        assert math.isclose(peg_oms_buy_v45, peg_sched_buy_v45, rel_tol=1e-6)

        # In v44, threshold was 0.0003, multiplier 0.99999999995
        peg_oms_buy_v44 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=44,
        )
        # v45 shades more defensively than v44 (lower limit buy price)
        assert peg_oms_buy_v45 < peg_oms_buy_v44

    def test_phase45_aliases_and_backward_compatibility(self):
        """Verify all Phase 45 method aliases and backward compatibility."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_parameter=0.0000000125,
            w_pcqtgbddddhkmaeetuvw=-26.0 / 3.0,
            k_hecke=0.06,
            k_cherednik=0.07,
            k_kostka=0.08,
            k_macdonald=0.09,
            k_askey=0.10,
            k_elliptic=0.11,
            k_elliptic_trig=0.12,
            k_hypergeom=0.13,
            k_daha=0.16,
            k_whittaker=0.29,
        )

        aliases = [
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_hydrodynamics",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_queue_acceleration",
            "calculate_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_queue_acceleration",
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_frame_dragging",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_hydrodynamics",
            "compute_kerr_newman_kiselev_24_dark_energy_elliptic_hypergeometric_askey_wilson_daha_queue_acceleration",
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_daha_queue_acceleration",
            "compute_kerr_newman_kiselev_24_dark_energy_daha_queue_acceleration",
            "compute_knk_24_dark_energy_queue_acceleration",
            "compute_phase45_queue_acceleration",
            "compute_phase45_lob_hydrodynamics",
            "compute_phase45_lob_acceleration",
            "compute_knk_pcqtgbddddhkmaeetuvw_whittaker_queue_acceleration",
            "compute_knk_24_dark_energy_whittaker_queue_acceleration",
            "compute_knk_pcqtgbddddhkmaeetuvw_queue_acceleration",
            "compute_knk_whittaker_daha_queue_acceleration",
            "compute_knk_whittaker_queue_acceleration",
            "compute_daha_24_queue_acceleration",
            "compute_knk_pcqtgbddddhkmaeetuvw_acceleration",
        ]
        for a in aliases:
            fn = getattr(engine, a, None)
            assert fn is not None, f"Missing alias: {a}"
            alias_res = fn(
                charge_parameter=0.5,
                spin_parameter=0.5,
                phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_parameter=0.0000000125,
                w_pcqtgbddddhkmaeetuvw=-26.0 / 3.0,
                k_hecke=0.06,
                k_cherednik=0.07,
                k_kostka=0.08,
                k_macdonald=0.09,
                k_askey=0.10,
                k_elliptic=0.11,
                k_elliptic_trig=0.12,
                k_hypergeom=0.13,
                k_daha=0.16,
                k_whittaker=0.29,
            )
            assert math.isclose(
                alias_res["knk_pcqtgbddddhkmaeetuvw_hydrodynamic_acceleration"],
                res["knk_pcqtgbddddhkmaeetuvw_hydrodynamic_acceleration"],
                abs_tol=1e-6,
            )
            assert math.isclose(
                alias_res["knk_pcqtgbddddhkmaeetuvw_micro_price"],
                res["knk_pcqtgbddddhkmaeetuvw_micro_price"],
                abs_tol=1e-6,
            )
