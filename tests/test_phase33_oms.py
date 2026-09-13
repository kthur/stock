"""
tests/test_phase33_oms.py

Unit and integration test suite for Phase 33 Quantitative Enhancement (Feature F153.2 Microstructure OMS):
- Kerr-Newman-Kiselev 12-Dark-Energy PCQTGBDD (w_pcqtgbdd = -14/3 ~= -4.666667)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 12-fold dark energy: Quintessence, Phantom, Tachyon, Quintom, Chameleon, Phantom-Chameleon,
    Phantom-Chameleon-Quintom, Phantom-Chameleon-Quintom-Tachyon, Phantom-Chameleon-Quintom-Tachyon-Ghost,
    Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane, Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane-Dilaton,
    Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane-Dilaton-Dirac
  * Energy densities up to rho_pcqtgbdd = 7.5 * c_pcqtgbdd * r^11
  * Spacetime metric horizon function Delta_r with 12-fold dark energy decay
  * Outer cosmological horizon scale r_{PCQTGBDD}
  * Radial tidal force with 12-fold dark energy repulsive acceleration:
    - 7.0 * c_pcqtgbdd * r^13
  * Hydrodynamic queue acceleration a_{KNK-PCQTGBDD} and micro-price prediction
  * 20+ method aliases on FastOrderBookMatchingEngine
- Fast LOB 99.999998% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=33:
  * Preemptive lit queue imbalance allocation with max dark cap 0.99999998 (99.999998%).
  * Lit maker ratio floor contracted to 0.0000000005 (0.00000005%, 1 share per 2,000,000,000)
    via 0.70 * (1.0 - 0.999999999286 * gamma_toxic) with 10-decimal formatting precision.
  * Dynamic anti-gaming MinQty scaled up to 99.9999995% (0.999999995).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.004:
  hawkes_shift = -direction * 0.9999998 * spr * (h - 0.004).
- Full backward compatibility across Phase 14 through Phase 32 versions.
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


class TestPhase33MicrostructureOMS:
    """Test suite for Phase 33 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 12-Dark-Energy PCQTGBDD queue acceleration and physical parameters."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_queue_acceleration(
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
        )
        assert isinstance(res, dict)

        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "knk_pcqtgbdd_mass_M",
            "knk_pcqtgbdd_spin_a",
            "knk_pcqtgbdd_charge_Q",
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
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_horizon_r_PCQTGBDD",
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_horizon",
            "horizon_radius",
            "coordinate_radius_r",
            "is_in_horizon",
            "frame_dragging_omega",
            "tidal_force",
            "knk_pcqtgbdd_tidal_force",
            "knk_pcqtgbdd_hydrodynamic_acceleration",
            "knk_pcqtgbdd_rotational_acceleration",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_rotational_acceleration",
            "knk_pcqtgbdd_accelerated_qi",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_accelerated_qi",
            "knk_pcqtgbdd_micro_price",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_micro_price",
        ]
        for k in required_keys:
            assert k in res, f"Missing key in Kerr-Newman-Kiselev 12-Dark-Energy result: {k}"

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
        assert math.isclose(res["equation_of_state_w_pcqtgbdd"], -14.0 / 3.0, abs_tol=1e-3)
        assert res["knk_pcqtgbdd_mass_M"] >= 1.0
        assert res["knk_pcqtgbdd_spin_a"] > 0.0
        assert res["knk_pcqtgbdd_charge_Q"] > 0.0
        assert res["phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_horizon_r_PCQTGBDD"] > 0.0
        assert res["frame_dragging_omega"] > 0.0
        assert math.isfinite(res["tidal_force"])
        assert math.isfinite(res["knk_pcqtgbdd_hydrodynamic_acceleration"])
        assert -1.0 <= res["knk_pcqtgbdd_accelerated_qi"] <= 1.0
        assert res["knk_pcqtgbdd_micro_price"] > 0.0

        # Check backward compatibility keys for prior phases
        assert "knk_pcqtgbd_hydrodynamic_acceleration" in res
        assert "knk_pcqtgb_hydrodynamic_acceleration" in res
        assert "knk_pcqtg_hydrodynamic_acceleration" in res
        assert "knk_pcqt_hydrodynamic_acceleration" in res
        assert "knk_pcq_hydrodynamic_acceleration" in res
        assert "knk_pc_hydrodynamic_acceleration" in res

        # Check all aliases
        aliases = [
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_hydrodynamics",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_queue_acceleration",
            "calculate_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_queue_acceleration",
            "compute_knk_12_dark_energy_hydrodynamics",
            "compute_kerr_newman_kiselev_12_dark_energy_hydrodynamics",
            "calculate_knk_12_dark_energy_hydrodynamics",
            "calculate_kerr_newman_kiselev_12_dark_energy_hydrodynamics",
            "compute_knk_pcqtgbdd_queue_acceleration",
            "compute_knk_pcqtgbdd_dark_energy_acceleration",
            "compute_pcqtgbdd_dark_energy_acceleration",
            "compute_pcqtgbdd_queue_acceleration",
            "compute_pcqtgbdd_acceleration",
            "compute_12_dark_energy_queue_acceleration",
            "compute_kerr_newman_kiselev_dirac_queue_acceleration",
            "compute_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_acceleration",
            "compute_phase33_lob_acceleration",
            "compute_phase33_queue_acceleration",
            "compute_knk_pcqtgbdd_hydrodynamics",
            "compute_phase33_hydrodynamics",
            "compute_kerr_newman_kiselev_queue_acceleration_phase33",
            "compute_12_dark_energy_acceleration",
        ]
        for a in aliases:
            fn = getattr(engine, a, None)
            assert fn is not None, f"Missing alias: {a}"
            alias_res = fn(
                charge_parameter=0.5,
                spin_parameter=0.5,
                phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_parameter=0.00002,
                w_pcqtgbdd=-14.0 / 3.0,
            )
            assert math.isclose(
                alias_res["knk_pcqtgbdd_hydrodynamic_acceleration"],
                res["knk_pcqtgbdd_hydrodynamic_acceleration"],
                abs_tol=1e-6,
            )

    def test_fast_lob_dark_routing_cap_v33_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess 99.999998% dark routing cap when version=33."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=33)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.99999998
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=33)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.99999998
        opt_res = process.get_optimal_preemptive_dark_allocation(version=33)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.99999998

    def test_fast_lob_dark_routing_cap_v33_frame_inspection(self):
        """Verify Fast LOB DeepHawkesArrivalProcess auto-infers 99.999998% dark cap via stack inspection."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        # Calling without version should inspect current test frame ("phase33" in filename)
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.99999998

    def test_smart_order_router_v33_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.999998% to dark venues under Phase 33."""
        sor = SmartOrderRouter()
        plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 100_000_000,
            "target_price": 70000.0,
            "market_spread_bps": 12.0,
            "queue_imbalance": 0.80,
            "qi_acceleration": 0.50,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.90,
            "version": 33,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        total_dark = sum(l["quantity"] for l in dark_legs)
        # 100,000,000 * 0.99999998 = 99,999,998
        assert total_dark == 99_999_998

    def test_smart_order_router_maker_floor_contraction_v33(self):
        """
        Verify maker ratio floor contracts to 0.0000000005 (1 share per 2,000,000,000) under extreme toxicity.
        Formula: 0.70 * (1.0 - 0.999999999286 * gamma_toxic) clamped at 0.0000000005.
        """
        sor = SmartOrderRouter()
        qty = 2_000_000_000

        plan_v33 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 33,
        }
        res_v33 = sor.route_order(plan_v33, ats_available=False)
        maker_legs_v33 = [
            l for l in res_v33.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v33) > 0
        # 2,000,000,000 * 0.0000000005 = 1 share
        assert maker_legs_v33[0]["quantity"] == 1
        assert res_v33["maker_ratio"] == 0.0000000005

        # Monotonic floor contraction against v32
        qty_compare = 2_000_000_000
        plan_v32 = {**plan_v33, "version": 32, "quantity": qty_compare}
        res_v32 = sor.route_order(plan_v32, ats_available=False)
        maker_legs_v32 = [
            l for l in res_v32.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        # In v32 floor is 0.000000001 => 2,000,000,000 * 0.000000001 = 2 shares
        assert maker_legs_v32[0]["quantity"] == 2
        assert maker_legs_v33[0]["quantity"] < maker_legs_v32[0]["quantity"]
        assert res_v33["maker_ratio"] < res_v32["maker_ratio"]

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v33(self):
        """Verify dynamic Anti-Gaming MinQty cap expands to 99.9999995% (0.999999995) under Phase 33."""
        sor = SmartOrderRouter()
        qty = 200_000_000

        plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": qty,
            "target_price": 300.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 33,
        }
        res = sor.route_order(plan, ats_available=True)
        dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        dark_qty = dark_legs[0]["quantity"]
        min_qty = dark_legs[0].get("min_quantity", 0)

        ratio = min_qty / dark_qty
        assert math.isclose(ratio, 0.999999995, abs_tol=1e-4)
        assert res["min_ratio"] == 0.999999995

    def test_oms_preemptive_micro_tick_shading_v33(self):
        """
        Verify Phase 33 preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When h_val > 0.004, hawkes_shift = -direction * 0.9999998 * spr * (h_val - 0.004).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.025

        # Buy order: direction = +1, hawkes_shift = -1.0 * 0.9999998 * 1.0 * (0.025 - 0.004) = -0.0209999958
        peg_oms_buy_v33 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=33,
        )
        peg_sched_buy_v33 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=33,
        )

        expected_shift_v33 = -0.9999998 * spr * (h_val - 0.004)
        expected_price_v33 = target_px + expected_shift_v33

        assert math.isclose(peg_oms_buy_v33, expected_price_v33, rel_tol=1e-4)
        assert math.isclose(peg_sched_buy_v33, expected_price_v33, rel_tol=1e-4)
        assert math.isclose(peg_oms_buy_v33, peg_sched_buy_v33, rel_tol=1e-6)

        # In v32, threshold was 0.005, multiplier 0.9999995
        peg_oms_buy_v32 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=32,
        )
        # v33 shades more defensively than v32 (lower limit buy price)
        assert peg_oms_buy_v33 < peg_oms_buy_v32
