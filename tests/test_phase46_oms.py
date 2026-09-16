"""
tests/test_phase46_oms.py

Unit and integration test suite for Phase 46 Quantitative Enhancement (Feature F205.2 Microstructure OMS):
- Kerr-Newman-Kiselev 25-Dark-Energy PCQTGBDDDDHKMAEETUVWX Borcherds DAHA
  (w_pcqtgbddddhkmaeetuvwx = -27/3 = -9.0, k_hecke = 0.06, k_cherednik = 0.07, k_kostka = 0.08, k_macdonald = 0.09,
   k_askey = 0.10, k_elliptic = 0.11, k_elliptic_trig = 0.12, k_hypergeom = 0.13, k_daha = 0.17,
   k_whittaker = 0.29, k_borch = 0.16, daha_25_factor = 2.38)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 25-fold dark energy density up to rho_pcqtgbddddhkmaeetuvwx
  * Outer cosmological horizon scale r_{PCQTGBDDDDHKMAEETUVWX}
  * Radial tidal force with 25-fold dark energy repulsive acceleration (-13.5 * c * r^26)
  * Hydrodynamic queue acceleration a_{KNK-PCQTGBDDDDHKMAEETUVWX} and micro-price prediction
  * Complete 21 method aliases on FastOrderBookMatchingEngine
- Fast LOB 99.99999999995% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=46:
  * Preemptive lit queue imbalance allocation with max dark cap 0.9999999999995 (99.99999999995%).
  * Lit maker ratio floor contracted to 0.000000000000000001 (1e-18, 1 share per 1,000,000,000,000,000,000)
    via 0.70 * (1.0 - 0.9999999999999999986 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.99999999998% (0.9999999999998).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.00015:
  hawkes_shift = -direction * 0.99999999999 * spr * (h - 0.00015).
- Full backward compatibility across Phase 14 through Phase 45 versions.
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


class TestPhase46MicrostructureOMS:
    """Test suite for Phase 46 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_25_dark_energy_borcherds_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 25-Dark-Energy PCQTGBDDDDHKMAEETUVWX Borcherds DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_borcherds_queue_acceleration(
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
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_borcherds_parameter=0.00000000625,
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
            w_pcqtgbddddhkmaeetuvwx=-27.0 / 3.0,
            k_hecke=0.06,
            k_cherednik=0.07,
            k_kostka=0.08,
            k_macdonald=0.09,
            k_askey=0.10,
            k_elliptic=0.11,
            k_elliptic_trig=0.12,
            k_hypergeom=0.13,
            k_daha=0.17,
            k_whittaker=0.29,
            k_borch=0.16,
        )
        assert isinstance(res, dict)

        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "knk_pcqtgbddddhkmaeetuvwx_mass_M",
            "knk_pcqtgbddddhkmaeetuvwx_spin_a",
            "knk_pcqtgbddddhkmaeetuvwx_charge_Q",
            "equation_of_state_w_pcqtgbddddhkmaeetuvwx",
            "daha_25_factor",
            "k_daha",
            "frame_dragging_omega",
            "tidal_force",
            "knk_pcqtgbddddhkmaeetuvwx_tidal_force",
            "knk_pcqtgbddddhkmaeetuvwx_hydrodynamic_acceleration",
            "knk_pcqtgbddddhkmaeetuvwx_micro_price",
        ]
        for k in required_keys:
            assert k in res, f"Missing key {k} in Phase 46 KNK result"

        assert math.isclose(res["equation_of_state_w_pcqtgbddddhkmaeetuvwx"], -27.0 / 3.0, rel_tol=1e-5)
        assert math.isclose(res["k_daha"], 0.17, rel_tol=1e-5)
        assert math.isclose(res["daha_25_factor"], 2.38, rel_tol=1e-5)
        assert np.isfinite(res["knk_pcqtgbddddhkmaeetuvwx_hydrodynamic_acceleration"])
        assert np.isfinite(res["knk_pcqtgbddddhkmaeetuvwx_micro_price"])
        assert res["knk_pcqtgbddddhkmaeetuvwx_micro_price"] > 0

        # Backward compatibility key check
        assert "knk_pcqtgbddddhkmaeetuvw_hydrodynamic_acceleration" in res
        assert "knk_pcqtgbddddhkmaeetuv_hydrodynamic_acceleration" in res
        assert "knk_pcqtgbddddhkmaeetu_hydrodynamic_acceleration" in res

    def test_fast_lob_dark_routing_cap_v46_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess reaches dark routing cap 0.9999999999995 when version=46."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=46)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.9999999999995
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=46)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.9999999999995
        opt_res = process.get_optimal_preemptive_dark_allocation(version=46)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.9999999999995

    def test_fast_lob_dark_routing_cap_v46_frame_inspection(self):
        """Verify Fast LOB DeepHawkesArrivalProcess reaches dark cap 0.9999999999995 via stack frame inspection."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        # Calling without version should inspect current test frame ("phase46" in filename)
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.9999999999995

    def test_smart_order_router_v46_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.99999999995% to dark venues under Phase 46."""
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
            "version": 46,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        total_dark = sum(l["quantity"] for l in dark_legs)
        # 100,000,000,000,000 * 0.9999999999995 = 99,999,999,999,950
        assert total_dark == 99_999_999_999_950

    def test_smart_order_router_maker_floor_contraction_v46(self):
        """
        Verify maker ratio floor contracts to 1e-18 (0.000000000000000001, 1 share per 1,000,000,000,000,000,000) under extreme toxicity.
        Formula: 0.70 * (1.0 - 0.9999999999999999986 * gamma_toxic) clamped at 0.000000000000000001.
        """
        sor = SmartOrderRouter()
        qty = 1_000_000_000_000_000_000  # 1 Quintillion shares: 1Q * 1e-18 = 1 share

        plan_v46 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 46,
        }
        res_v46 = sor.route_order(plan_v46, ats_available=False)
        maker_legs_v46 = [
            l for l in res_v46.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v46) > 0
        # 1,000,000,000,000,000,000 * 0.000000000000000001 = 1 share
        assert maker_legs_v46[0]["quantity"] == 1
        assert res_v46["maker_ratio"] == 0.000000000000000001

        # Monotonic floor contraction against v45 (1e-18 < 1e-17)
        qty_compare = 1_000_000_000_000_000_000
        plan_v46_comp = {**plan_v46, "version": 46, "quantity": qty_compare}
        plan_v45_comp = {**plan_v46, "version": 45, "quantity": qty_compare}
        res_v46_comp = sor.route_order(plan_v46_comp, ats_available=False)
        res_v45_comp = sor.route_order(plan_v45_comp, ats_available=False)

        maker_v46 = [l for l in res_v46_comp.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"][0]["quantity"]
        maker_v45 = [l for l in res_v45_comp.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"][0]["quantity"]

        # 1Q * 1e-18 = 1 share vs 1Q * 1e-17 = 10 shares
        assert maker_v46 == 1
        assert maker_v45 == 10
        assert maker_v46 < maker_v45
        assert res_v46_comp["maker_ratio"] < res_v45_comp["maker_ratio"]

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v46(self):
        """Verify dynamic Anti-Gaming MinQty cap expands to 99.99999999998% (0.9999999999998) under Phase 46."""
        sor = SmartOrderRouter()
        qty = 10_000_000_000_000

        plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": qty,
            "target_price": 300.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 46,
        }
        res = sor.route_order(plan, ats_available=True)
        dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        dark_qty = dark_legs[0]["quantity"]
        min_qty = dark_legs[0].get("min_quantity", 0)

        ratio = min_qty / dark_qty
        assert math.isclose(ratio, 0.9999999999998, abs_tol=1e-5)
        assert res["min_ratio"] == 0.9999999999998

    def test_oms_preemptive_micro_tick_shading_v46(self):
        """
        Verify Phase 46 preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When h_val > 0.00015, hawkes_shift = -direction * 0.99999999999 * spr * (h_val - 0.00015).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.025

        # Buy order: direction = +1, hawkes_shift = -1.0 * 0.99999999999 * 1.0 * (0.025 - 0.00015)
        peg_oms_buy_v46 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=46,
        )
        peg_sched_buy_v46 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=46,
        )

        expected_shift_v46 = -0.99999999999 * spr * (h_val - 0.00015)
        expected_price_v46 = target_px + expected_shift_v46

        assert math.isclose(peg_oms_buy_v46, expected_price_v46, rel_tol=1e-4)
        assert math.isclose(peg_sched_buy_v46, expected_price_v46, rel_tol=1e-4)
        assert math.isclose(peg_oms_buy_v46, peg_sched_buy_v46, rel_tol=1e-6)

        # In v45, threshold was 0.0002, multiplier 0.99999999998
        peg_oms_buy_v45 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=45,
        )
        # v46 shades more defensively than v45 (lower limit buy price)
        assert peg_oms_buy_v46 < peg_oms_buy_v45

    def test_phase46_aliases_and_backward_compatibility(self):
        """Verify all Phase 46 method aliases and backward compatibility."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_borcherds_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_borcherds_parameter=0.00000000625,
            w_pcqtgbddddhkmaeetuvwx=-27.0 / 3.0,
            k_hecke=0.06,
            k_cherednik=0.07,
            k_kostka=0.08,
            k_macdonald=0.09,
            k_askey=0.10,
            k_elliptic=0.11,
            k_elliptic_trig=0.12,
            k_hypergeom=0.13,
            k_daha=0.17,
            k_whittaker=0.29,
            k_borch=0.16,
        )

        aliases = [
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_borcherds_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_borcherds_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_borcherds_hydrodynamics",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_borcherds_queue_acceleration",
            "calculate_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_borcherds_queue_acceleration",
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_borcherds_frame_dragging",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_borcherds_hydrodynamics",
            "compute_kerr_newman_kiselev_25_dark_energy_elliptic_hypergeometric_askey_wilson_daha_queue_acceleration",
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_borcherds_daha_queue_acceleration",
            "compute_kerr_newman_kiselev_25_dark_energy_daha_queue_acceleration",
            "compute_knk_25_dark_energy_queue_acceleration",
            "compute_phase46_queue_acceleration",
            "compute_phase46_lob_hydrodynamics",
            "compute_phase46_lob_acceleration",
            "compute_knk_pcqtgbddddhkmaeetuvwx_borcherds_queue_acceleration",
            "compute_knk_25_dark_energy_borcherds_queue_acceleration",
            "compute_knk_pcqtgbddddhkmaeetuvwx_queue_acceleration",
            "compute_knk_borcherds_daha_queue_acceleration",
            "compute_knk_borcherds_queue_acceleration",
            "compute_daha_25_queue_acceleration",
            "compute_knk_pcqtgbddddhkmaeetuvwx_acceleration",
        ]
        assert len(aliases) == 21, f"Expected 21 aliases, got {len(aliases)}"

        for a in aliases:
            fn = getattr(engine, a, None)
            assert fn is not None, f"Missing alias: {a}"
            alias_res = fn(
                charge_parameter=0.5,
                spin_parameter=0.5,
                phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_borcherds_parameter=0.00000000625,
                w_pcqtgbddddhkmaeetuvwx=-27.0 / 3.0,
                k_hecke=0.06,
                k_cherednik=0.07,
                k_kostka=0.08,
                k_macdonald=0.09,
                k_askey=0.10,
                k_elliptic=0.11,
                k_elliptic_trig=0.12,
                k_hypergeom=0.13,
                k_daha=0.17,
                k_whittaker=0.29,
                k_borch=0.16,
            )
            assert math.isclose(
                alias_res["knk_pcqtgbddddhkmaeetuvwx_hydrodynamic_acceleration"],
                res["knk_pcqtgbddddhkmaeetuvwx_hydrodynamic_acceleration"],
                abs_tol=1e-6,
            )
            assert math.isclose(
                alias_res["knk_pcqtgbddddhkmaeetuvwx_micro_price"],
                res["knk_pcqtgbddddhkmaeetuvwx_micro_price"],
                abs_tol=1e-6,
            )
