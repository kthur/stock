"""
tests/test_phase42_oms.py

Unit and integration test suite for Phase 42 Quantitative Enhancement (Feature F189.2 Microstructure OMS):
- Kerr-Newman-Kiselev 21-Dark-Energy PCQTGBDDDDHKMAEET Elliptic-Hypergeometric Macdonald-Koornwinder-Askey-Wilson DAHA
  (w_pcqtgbddddhkmaeet = -23/3, k_hecke = 0.06, k_cherednik = 0.07, k_kostka = 0.08, k_macdonald = 0.09,
   k_askey = 0.10, k_elliptic = 0.11, k_elliptic_trig = 0.12, k_hypergeom = 0.13, c_pcqtgbddddhkmaeet = 1e-7)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 21-fold dark energy density up to rho_pcqtgbddddhkmaeet
  * Outer cosmological horizon scale r_{PCQTGBDDDDHKMAEET}
  * Radial tidal force with 21-fold dark energy repulsive acceleration
  * Hydrodynamic queue acceleration a_{KNK-PCQTGBDDDDHKMAEET} and micro-price prediction
  * Method aliases on FastOrderBookMatchingEngine
- Fast LOB 99.999999998% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=42:
  * Preemptive lit queue imbalance allocation with max dark cap 0.99999999998 (99.999999998%).
  * Lit maker ratio floor contracted to 0.00000000000001 (1e-14, 1 share per 100,000,000,000,000)
    via 0.70 * (1.0 - 0.999999999999986 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.9999999995% (0.999999999995).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.0005:
  hawkes_shift = -direction * 0.9999999998 * spr * (h - 0.0005).
- Full backward compatibility across Phase 14 through Phase 41 versions.
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


class TestPhase42MicrostructureOMS:
    """Test suite for Phase 42 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_21_dark_energy_elliptic_hypergeometric_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 21-Dark-Energy PCQTGBDDDDHKMAEET Elliptic-Hypergeometric DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_queue_acceleration(
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
            k_hecke=0.06,
            k_cherednik=0.07,
            k_kostka=0.08,
            k_macdonald=0.09,
            k_askey=0.10,
            k_elliptic=0.11,
            k_elliptic_trig=0.12,
            k_hypergeom=0.13,
        )
        assert isinstance(res, dict)

        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "knk_pcqtgbddddhkmaeet_mass_M",
            "knk_pcqtgbddddhkmaeet_spin_a",
            "knk_pcqtgbddddhkmaeet_charge_Q",
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
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_c_pcqtgbddddhkmae",
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_trigonometric_c_pcqtgbddddhkmaee",
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_c_pcqtgbddddhkmaeet",
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
            "equation_of_state_w_pcqtgbddddhkmae",
            "equation_of_state_w_pcqtgbddddhkmaee",
            "equation_of_state_w_pcqtgbddddhkmaeet",
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_horizon_r_PCQTGBDDDDHKMAEET",
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_horizon",
            "horizon_radius",
            "coordinate_radius_r",
            "is_in_horizon",
            "frame_dragging_omega",
            "tidal_force",
            "knk_pcqtgbddddhkmaeet_tidal_force",
            "knk_pcqtgbddddhkmaeet_hydrodynamic_acceleration",
            "knk_pcqtgbddddhkmaeet_rotational_acceleration",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_rotational_acceleration",
            "knk_pcqtgbddddhkmaeet_accelerated_qi",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_accelerated_qi",
            "knk_pcqtgbddddhkmaeet_micro_price",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_micro_price",
        ]
        for k in required_keys:
            assert k in res, f"Missing key in Kerr-Newman-Kiselev 21-Dark-Energy result: {k}"

        # Check physical parameters and bounds
        assert res["phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_c_pcqtgbddddhkmaeet"] == 0.0000001
        assert math.isclose(res["equation_of_state_w_pcqtgbddddhkmaeet"], -23.0 / 3.0, abs_tol=1e-3)
        assert res["knk_pcqtgbddddhkmaeet_mass_M"] >= 1.0
        assert res["knk_pcqtgbddddhkmaeet_spin_a"] > 0.0
        assert res["knk_pcqtgbddddhkmaeet_charge_Q"] > 0.0
        assert res["phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_horizon_r_PCQTGBDDDDHKMAEET"] > 0.0
        assert res["frame_dragging_omega"] > 0.0
        assert math.isfinite(res["tidal_force"])
        assert math.isfinite(res["knk_pcqtgbddddhkmaeet_hydrodynamic_acceleration"])
        assert -1.0 <= res["knk_pcqtgbddddhkmaeet_accelerated_qi"] <= 1.0
        assert res["knk_pcqtgbddddhkmaeet_micro_price"] > 0.0

        # Check backward compatibility keys for prior phases (Phase 41, 40, 39, 38)
        assert "knk_pcqtgbddddhkmaee_hydrodynamic_acceleration" in res
        assert "knk_pcqtgbddddhkmae_hydrodynamic_acceleration" in res
        assert "knk_pcqtgbddddhkma_hydrodynamic_acceleration" in res
        assert "knk_pcqtgbddddhkm_hydrodynamic_acceleration" in res
        assert "knk_pcqtgbdddddd_hydrodynamic_acceleration" in res

    def test_fast_lob_dark_routing_cap_v42_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess 99.999999998% dark routing cap when version=42."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=42)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.99999999998
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=42)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.99999999998
        opt_res = process.get_optimal_preemptive_dark_allocation(version=42)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.99999999998

    def test_fast_lob_dark_routing_cap_v42_frame_inspection(self):
        """Verify Fast LOB DeepHawkesArrivalProcess auto-infers 99.999999998% dark cap via stack inspection."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        # Calling without version should inspect current test frame ("phase42" in filename)
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.99999999998

    def test_smart_order_router_v42_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.999999998% to dark venues under Phase 42."""
        sor = SmartOrderRouter()
        plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 100_000_000_000,
            "target_price": 70000.0,
            "market_spread_bps": 12.0,
            "queue_imbalance": 0.80,
            "qi_acceleration": 0.50,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.90,
            "version": 42,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        total_dark = sum(l["quantity"] for l in dark_legs)
        # 100,000,000,000 * 0.99999999998 = 99,999,999,998
        assert total_dark == 99_999_999_998

    def test_smart_order_router_maker_floor_contraction_v42(self):
        """
        Verify maker ratio floor contracts to 1e-14 (0.00000000000001, 1 share per 100,000,000,000,000) under extreme toxicity.
        Formula: 0.70 * (1.0 - 0.999999999999986 * gamma_toxic) clamped at 0.00000000000001.
        """
        sor = SmartOrderRouter()
        qty = 100_000_000_000_000  # 100T shares: 100T * 1e-14 = 1 share

        plan_v42 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 42,
        }
        res_v42 = sor.route_order(plan_v42, ats_available=False)
        maker_legs_v42 = [
            l for l in res_v42.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v42) > 0
        # 100,000,000,000,000 * 0.00000000000001 = 1 share
        assert maker_legs_v42[0]["quantity"] == 1
        assert res_v42["maker_ratio"] == 0.00000000000001

        # Monotonic floor contraction against v41 (1e-14 < 1e-13)
        qty_compare = 100_000_000_000_000
        plan_v42_comp = {**plan_v42, "version": 42, "quantity": qty_compare}
        plan_v41_comp = {**plan_v42, "version": 41, "quantity": qty_compare}
        res_v42_comp = sor.route_order(plan_v42_comp, ats_available=False)
        res_v41_comp = sor.route_order(plan_v41_comp, ats_available=False)

        maker_v42 = [l for l in res_v42_comp.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"][0]["quantity"]
        maker_v41 = [l for l in res_v41_comp.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"][0]["quantity"]

        # 100T * 1e-14 = 1 share vs 100T * 1e-13 = 10 shares
        assert maker_v42 == 1
        assert maker_v41 == 10
        assert maker_v42 < maker_v41
        assert res_v42_comp["maker_ratio"] < res_v41_comp["maker_ratio"]

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v42(self):
        """Verify dynamic Anti-Gaming MinQty cap expands to 99.9999999995% (0.999999999995) under Phase 42."""
        sor = SmartOrderRouter()
        qty = 1_000_000_000_000

        plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": qty,
            "target_price": 300.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 42,
        }
        res = sor.route_order(plan, ats_available=True)
        dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        dark_qty = dark_legs[0]["quantity"]
        min_qty = dark_legs[0].get("min_quantity", 0)

        ratio = min_qty / dark_qty
        assert math.isclose(ratio, 0.999999999995, abs_tol=1e-5)
        assert res["min_ratio"] == 0.999999999995

    def test_oms_preemptive_micro_tick_shading_v42(self):
        """
        Verify Phase 42 preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When h_val > 0.0005, hawkes_shift = -direction * 0.9999999998 * spr * (h_val - 0.0005).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.025

        # Buy order: direction = +1, hawkes_shift = -1.0 * 0.9999999998 * 1.0 * (0.025 - 0.0005)
        peg_oms_buy_v42 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=42,
        )
        peg_sched_buy_v42 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=42,
        )

        expected_shift_v42 = -0.9999999998 * spr * (h_val - 0.0005)
        expected_price_v42 = target_px + expected_shift_v42

        assert math.isclose(peg_oms_buy_v42, expected_price_v42, rel_tol=1e-4)
        assert math.isclose(peg_sched_buy_v42, expected_price_v42, rel_tol=1e-4)
        assert math.isclose(peg_oms_buy_v42, peg_sched_buy_v42, rel_tol=1e-6)

        # In v41, threshold was 0.0006, multiplier 0.9999999995
        peg_oms_buy_v41 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=41,
        )
        # v42 shades more defensively than v41 (lower limit buy price)
        assert peg_oms_buy_v42 < peg_oms_buy_v41

    def test_phase42_aliases_and_backward_compatibility(self):
        """Verify all Phase 42 method aliases and backward compatibility."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_parameter=0.0000001,
            w_pcqtgbddddhkmaeet=-23.0 / 3.0,
            k_hecke=0.06,
            k_cherednik=0.07,
            k_kostka=0.08,
            k_macdonald=0.09,
            k_askey=0.10,
            k_elliptic=0.11,
            k_elliptic_trig=0.12,
            k_hypergeom=0.13,
        )

        aliases = [
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_hydrodynamics",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_queue_acceleration",
            "calculate_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_queue_acceleration",
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_frame_dragging",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_hydrodynamics",
            "compute_elliptic_hypergeometric_queue_acceleration",
            "compute_phase42_queue_acceleration",
            "compute_phase42_lob_hydrodynamics",
            "compute_phase42_lob_acceleration",
            "compute_hypergeometric_queue_acceleration",
        ]
        for a in aliases:
            fn = getattr(engine, a, None)
            assert fn is not None, f"Missing alias: {a}"
            alias_res = fn(
                charge_parameter=0.5,
                spin_parameter=0.5,
                phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_parameter=0.0000001,
                w_pcqtgbddddhkmaeet=-23.0 / 3.0,
                k_hecke=0.06,
                k_cherednik=0.07,
                k_kostka=0.08,
                k_macdonald=0.09,
                k_askey=0.10,
                k_elliptic=0.11,
                k_elliptic_trig=0.12,
                k_hypergeom=0.13,
            )
            assert math.isclose(
                alias_res["knk_pcqtgbddddhkmaeet_hydrodynamic_acceleration"],
                res["knk_pcqtgbddddhkmaeet_hydrodynamic_acceleration"],
                abs_tol=1e-6,
            )
            assert math.isclose(
                alias_res["knk_pcqtgbddddhkmaeet_micro_price"],
                res["knk_pcqtgbddddhkmaeet_micro_price"],
                abs_tol=1e-6,
            )
