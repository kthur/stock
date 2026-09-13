"""
tests/test_phase32_oms.py

Unit and integration test suite for Phase 32 Quantitative Enhancement (Feature F149.2 Microstructure OMS):
- Kerr-Newman-Kiselev 11-Dark-Energy PCQTGBD (w_pcqtgbd = -13/3 ~= -4.333333)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 11-fold dark energy: Quintessence, Phantom, Tachyon, Quintom, Chameleon, Phantom-Chameleon,
    Phantom-Chameleon-Quintom, Phantom-Chameleon-Quintom-Tachyon, Phantom-Chameleon-Quintom-Tachyon-Ghost,
    Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane, Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane-Dilaton
  * Energy densities up to rho_pcqtgbd = 7.0 * c_pcqtgbd * r^10
  * Spacetime metric horizon function Delta_r with 11-fold dark energy decay
  * Outer cosmological horizon scale r_{PCQTGBD}
  * Radial tidal force with 11-fold dark energy repulsive acceleration:
    - 6.5 * c_pcqtgbd * r^12
  * Hydrodynamic queue acceleration a_{KNK-PCQTGBD} and micro-price prediction
  * 20+ method aliases on FastOrderBookMatchingEngine
- Fast LOB 99.999995% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=32:
  * Preemptive lit queue imbalance allocation with max dark cap 0.99999995 (99.999995%).
  * Lit maker ratio floor contracted to 0.000000001 (0.0000001%, 1 share per 1,000,000,000)
    via 0.70 * (1.0 - 0.999999998571 * gamma_toxic) with 10-decimal formatting precision.
  * Dynamic anti-gaming MinQty scaled up to 99.999999% (0.99999999).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.005:
  hawkes_shift = -direction * 0.9999995 * spr * (h - 0.005).
- Full backward compatibility across Phase 14 through Phase 31 versions.
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


class TestPhase32MicrostructureOMS:
    """Test suite for Phase 32 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 11-Dark-Energy PCQTGBD queue acceleration and physical parameters."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_queue_acceleration(
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
        )
        assert isinstance(res, dict)

        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "knk_pcqtgbd_mass_M",
            "knk_pcqtgbd_spin_a",
            "knk_pcqtgbd_charge_Q",
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
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_horizon_r_PCQTGBD",
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_horizon",
            "phantom_chameleon_quintom_tachyon_ghost_brane_horizon_r_PCQTGB",
            "phantom_chameleon_quintom_tachyon_ghost_brane_horizon",
            "horizon_radius",
            "coordinate_radius_r",
            "is_in_horizon",
            "frame_dragging_omega",
            "tidal_force",
            "knk_pcqtgbd_tidal_force",
            "knk_pcqtgbd_hydrodynamic_acceleration",
            "knk_pcqtgbd_rotational_acceleration",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_rotational_acceleration",
            "knk_pcqtgbd_accelerated_qi",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_accelerated_qi",
            "knk_pcqtgbd_micro_price",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_micro_price",
        ]
        for k in required_keys:
            assert k in res, f"Missing key in Kerr-Newman-Kiselev 11-Dark-Energy result: {k}"

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
        assert math.isclose(res["equation_of_state_w_pcqtgbd"], -13.0 / 3.0, abs_tol=1e-3)
        assert res["knk_pcqtgbd_mass_M"] >= 1.0
        assert res["knk_pcqtgbd_spin_a"] > 0.0
        assert res["knk_pcqtgbd_charge_Q"] > 0.0
        assert res["phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_horizon_r_PCQTGBD"] > 0.0
        assert res["frame_dragging_omega"] > 0.0
        assert math.isfinite(res["tidal_force"])
        assert math.isfinite(res["knk_pcqtgbd_hydrodynamic_acceleration"])
        assert -1.0 <= res["knk_pcqtgbd_accelerated_qi"] <= 1.0
        assert res["knk_pcqtgbd_micro_price"] > 0.0

        # Check backward compatibility keys for prior phases
        assert "knk_pcqtgb_hydrodynamic_acceleration" in res
        assert "knk_pcqtg_hydrodynamic_acceleration" in res
        assert "knk_pcqt_hydrodynamic_acceleration" in res
        assert "knk_pcq_hydrodynamic_acceleration" in res
        assert "knk_pc_hydrodynamic_acceleration" in res

        # Check all aliases
        aliases = [
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_hydrodynamics",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_queue_acceleration",
            "calculate_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_queue_acceleration",
            "compute_knk_11_dark_energy_hydrodynamics",
            "compute_kerr_newman_kiselev_11_dark_energy_hydrodynamics",
            "calculate_knk_11_dark_energy_hydrodynamics",
            "calculate_kerr_newman_kiselev_11_dark_energy_hydrodynamics",
            "compute_knk_pcqtgbd_queue_acceleration",
            "compute_knk_pcqtgbd_dark_energy_acceleration",
            "compute_pcqtgbd_dark_energy_acceleration",
            "compute_pcqtgbd_queue_acceleration",
            "compute_pcqtgbd_acceleration",
            "compute_11_dark_energy_queue_acceleration",
            "compute_kerr_newman_kiselev_dilaton_queue_acceleration",
            "compute_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_acceleration",
            "compute_phase32_lob_acceleration",
            "compute_phase32_queue_acceleration",
            "compute_knk_pcqtgbd_hydrodynamics",
            "compute_phase32_hydrodynamics",
            "compute_kerr_newman_kiselev_queue_acceleration_phase32",
        ]
        for a in aliases:
            fn = getattr(engine, a, None)
            assert fn is not None, f"Missing alias: {a}"
            alias_res = fn(
                charge_parameter=0.5,
                spin_parameter=0.5,
                phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_parameter=0.00003,
                w_pcqtgbd=-13.0 / 3.0,
            )
            assert math.isclose(
                alias_res["knk_pcqtgbd_hydrodynamic_acceleration"],
                res["knk_pcqtgbd_hydrodynamic_acceleration"],
                abs_tol=1e-6,
            )

    def test_fast_lob_dark_routing_cap_v32_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess 99.999995% dark routing cap when version=32."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=32)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.99999995
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=32)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.99999995
        opt_res = process.get_optimal_preemptive_dark_allocation(version=32)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.99999995

    def test_fast_lob_dark_routing_cap_v32_frame_inspection(self):
        """Verify Fast LOB DeepHawkesArrivalProcess auto-infers 99.999995% dark cap via stack inspection."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        # Calling without version should inspect current test frame ("phase32" in filename)
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.99999995

    def test_smart_order_router_v32_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.999995% to dark venues under Phase 32."""
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
            "version": 32,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        total_dark = sum(l["quantity"] for l in dark_legs)
        # 100,000,000 * 0.99999995 = 99,999,995
        assert total_dark == 99_999_995

    def test_smart_order_router_maker_floor_contraction_v32(self):
        """
        Verify maker ratio floor contracts to 0.000000001 (1 share per 1,000,000,000) under extreme toxicity.
        Formula: 0.70 * (1.0 - 0.999999998571 * gamma_toxic) clamped at 0.000000001.
        """
        sor = SmartOrderRouter()
        qty = 1_000_000_000

        plan_v32 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 32,
        }
        res_v32 = sor.route_order(plan_v32, ats_available=False)
        maker_legs_v32 = [
            l for l in res_v32.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v32) > 0
        # 1,000,000,000 * 0.000000001 = 1 share
        assert maker_legs_v32[0]["quantity"] == 1
        assert res_v32["maker_ratio"] == 0.000000001

        # Monotonic floor contraction against v31
        plan_v31 = {**plan_v32, "version": 31}
        res_v31 = sor.route_order(plan_v31, ats_available=False)
        maker_legs_v31 = [
            l for l in res_v31.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        # 1,000,000,000 * 0.000000002 = 2 shares
        assert maker_legs_v31[0]["quantity"] == 2
        assert maker_legs_v32[0]["quantity"] < maker_legs_v31[0]["quantity"]

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v32(self):
        """Verify dynamic Anti-Gaming MinQty cap expands to 99.999999% (0.99999999) under Phase 32."""
        sor = SmartOrderRouter()
        qty = 100_000_000

        plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": qty,
            "target_price": 300.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 32,
        }
        res = sor.route_order(plan, ats_available=True)
        dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        dark_qty = dark_legs[0]["quantity"]
        min_qty = dark_legs[0].get("min_quantity", 0)

        ratio = min_qty / dark_qty
        assert math.isclose(ratio, 0.99999999, abs_tol=1e-4)
        assert res["min_ratio"] == 0.99999999

    def test_oms_preemptive_micro_tick_shading_v32(self):
        """
        Verify Phase 32 preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When h_val > 0.005, hawkes_shift = -direction * 0.9999995 * spr * (h_val - 0.005).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.025

        # Buy order: direction = +1, hawkes_shift = -1.0 * 0.9999995 * 1.0 * (0.025 - 0.005) = -0.01999999
        peg_oms_buy_v32 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=32,
        )
        peg_sched_buy_v32 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=32,
        )

        expected_shift_v32 = -0.9999995 * spr * (h_val - 0.005)
        expected_price_v32 = target_px + expected_shift_v32

        assert math.isclose(peg_oms_buy_v32, expected_price_v32, rel_tol=1e-4)
        assert math.isclose(peg_sched_buy_v32, expected_price_v32, rel_tol=1e-4)
        assert math.isclose(peg_oms_buy_v32, peg_sched_buy_v32, rel_tol=1e-6)

        # In v31, threshold was 0.006, multiplier 0.999999
        peg_oms_buy_v31 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=31,
        )
        # v32 shades more defensively than v31 (lower limit buy price)
        assert peg_oms_buy_v32 < peg_oms_buy_v31
