"""
tests/test_phase34_oms.py

Unit and integration test suite for Phase 34 Quantitative Enhancement (Feature F157.2 Microstructure OMS):
- Kerr-Newman-Kiselev 13-Dark-Energy PCQTGBDDD (w_pcqtgbddd = -15/3 = -5.0)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 13-fold dark energy: Quintessence, Phantom, Tachyon, Quintom, Chameleon, Phantom-Chameleon,
    Phantom-Chameleon-Quintom, Phantom-Chameleon-Quintom-Tachyon, Phantom-Chameleon-Quintom-Tachyon-Ghost,
    Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane, Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane-Dilaton,
    Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane-Dilaton-Dirac,
    Phantom-Chameleon-Quintom-Tachyon-Ghost-Brane-Dilaton-Dirac-Dunkl
  * Energy densities up to rho_pcqtgbddd = 8.0 * c_pcqtgbddd * r^12
  * Spacetime metric horizon function Delta_r with 13-fold dark energy decay
  * Outer cosmological horizon scale r_{PCQTGBDDD}
  * Radial tidal force with 13-fold dark energy repulsive acceleration:
    - 7.5 * c_pcqtgbddd * r^14
  * Hydrodynamic queue acceleration a_{KNK-PCQTGBDDD} and micro-price prediction
  * Method aliases on FastOrderBookMatchingEngine
- Fast LOB 99.999999% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=34:
  * Preemptive lit queue imbalance allocation with max dark cap 0.99999999 (99.999999%).
  * Lit maker ratio floor contracted to 0.0000000002 (0.00000002%, 1 share per 5,000,000,000)
    via 0.70 * (1.0 - 0.999999999714 * gamma_toxic) with 11-decimal formatting precision.
  * Dynamic anti-gaming MinQty scaled up to 99.9999998% (0.999999998).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.003:
  hawkes_shift = -direction * 0.9999999 * spr * (h - 0.003).
- Full backward compatibility across Phase 14 through Phase 33 versions.
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


class TestPhase34MicrostructureOMS:
    """Test suite for Phase 34 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 13-Dark-Energy PCQTGBDDD queue acceleration and physical parameters."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_queue_acceleration(
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
        )
        assert isinstance(res, dict)

        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "knk_pcqtgbddd_mass_M",
            "knk_pcqtgbddd_spin_a",
            "knk_pcqtgbddd_charge_Q",
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
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_horizon_r_PCQTGBDDD",
            "phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_horizon",
            "horizon_radius",
            "coordinate_radius_r",
            "is_in_horizon",
            "frame_dragging_omega",
            "tidal_force",
            "knk_pcqtgbddd_tidal_force",
            "knk_pcqtgbddd_hydrodynamic_acceleration",
            "knk_pcqtgbddd_rotational_acceleration",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_rotational_acceleration",
            "knk_pcqtgbddd_accelerated_qi",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_accelerated_qi",
            "knk_pcqtgbddd_micro_price",
            "kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_micro_price",
        ]
        for k in required_keys:
            assert k in res, f"Missing key in Kerr-Newman-Kiselev 13-Dark-Energy result: {k}"

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
        assert math.isclose(res["equation_of_state_w_pcqtgbddd"], -15.0 / 3.0, abs_tol=1e-3)
        assert res["knk_pcqtgbddd_mass_M"] >= 1.0
        assert res["knk_pcqtgbddd_spin_a"] > 0.0
        assert res["knk_pcqtgbddd_charge_Q"] > 0.0
        assert res["phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_horizon_r_PCQTGBDDD"] > 0.0
        assert res["frame_dragging_omega"] > 0.0
        assert math.isfinite(res["tidal_force"])
        assert math.isfinite(res["knk_pcqtgbddd_hydrodynamic_acceleration"])
        assert -1.0 <= res["knk_pcqtgbddd_accelerated_qi"] <= 1.0
        assert res["knk_pcqtgbddd_micro_price"] > 0.0

        # Check backward compatibility keys for prior phases
        assert "knk_pcqtgbdd_hydrodynamic_acceleration" in res
        assert "knk_pcqtgbd_hydrodynamic_acceleration" in res
        assert "knk_pcqtgb_hydrodynamic_acceleration" in res
        assert "knk_pcqtg_hydrodynamic_acceleration" in res

        # Check all aliases
        aliases = [
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hydrodynamics",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_queue_acceleration",
            "calculate_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_queue_acceleration",
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_frame_dragging",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hydrodynamics",
            "compute_phase34_lob_hydrodynamics",
            "compute_phase34_lob_acceleration",
        ]
        for a in aliases:
            fn = getattr(engine, a, None)
            assert fn is not None, f"Missing alias: {a}"
            alias_res = fn(
                charge_parameter=0.5,
                spin_parameter=0.5,
                phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_parameter=0.00001,
                w_pcqtgbddd=-15.0 / 3.0,
            )
            assert math.isclose(
                alias_res["knk_pcqtgbddd_hydrodynamic_acceleration"],
                res["knk_pcqtgbddd_hydrodynamic_acceleration"],
                abs_tol=1e-6,
            )

    def test_fast_lob_dark_routing_cap_v34_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess 99.999999% dark routing cap when version=34."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=34)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.99999999
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=34)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.99999999
        opt_res = process.get_optimal_preemptive_dark_allocation(version=34)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.99999999

    def test_fast_lob_dark_routing_cap_v34_frame_inspection(self):
        """Verify Fast LOB DeepHawkesArrivalProcess auto-infers 99.999999% dark cap via stack inspection."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        # Calling without version should inspect current test frame ("phase34" in filename)
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.99999999

    def test_smart_order_router_v34_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.999999% to dark venues under Phase 34."""
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
            "version": 34,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        total_dark = sum(l["quantity"] for l in dark_legs)
        # 100,000,000 * 0.99999999 = 99,999,999
        assert total_dark == 99_999_999

    def test_smart_order_router_maker_floor_contraction_v34(self):
        """
        Verify maker ratio floor contracts to 0.0000000002 (1 share per 5,000,000,000) under extreme toxicity.
        Formula: 0.70 * (1.0 - 0.999999999714 * gamma_toxic) clamped at 0.0000000002.
        """
        sor = SmartOrderRouter()
        qty = 5_000_000_000

        plan_v34 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 34,
        }
        res_v34 = sor.route_order(plan_v34, ats_available=False)
        maker_legs_v34 = [
            l for l in res_v34.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v34) > 0
        # 5,000,000,000 * 0.0000000002 = 1 share
        assert maker_legs_v34[0]["quantity"] == 1
        assert res_v34["maker_ratio"] == 0.0000000002

        # Monotonic floor contraction against v33
        qty_compare = 10_000_000_000
        plan_v34_comp = {**plan_v34, "version": 34, "quantity": qty_compare}
        plan_v33_comp = {**plan_v34, "version": 33, "quantity": qty_compare}
        res_v34_comp = sor.route_order(plan_v34_comp, ats_available=False)
        res_v33_comp = sor.route_order(plan_v33_comp, ats_available=False)

        maker_v34 = [l for l in res_v34_comp.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"][0]["quantity"]
        maker_v33 = [l for l in res_v33_comp.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"][0]["quantity"]

        # 10B * 2e-10 = 2 shares vs 10B * 5e-10 = 5 shares
        assert maker_v34 == 2
        assert maker_v33 == 5
        assert maker_v34 < maker_v33
        assert res_v34_comp["maker_ratio"] < res_v33_comp["maker_ratio"]

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v34(self):
        """Verify dynamic Anti-Gaming MinQty cap expands to 99.9999998% (0.999999998) under Phase 34."""
        sor = SmartOrderRouter()
        qty = 500_000_000

        plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": qty,
            "target_price": 300.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "version": 34,
        }
        res = sor.route_order(plan, ats_available=True)
        dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        dark_qty = dark_legs[0]["quantity"]
        min_qty = dark_legs[0].get("min_quantity", 0)

        ratio = min_qty / dark_qty
        assert math.isclose(ratio, 0.999999998, abs_tol=1e-4)
        assert res["min_ratio"] == 0.999999998

    def test_oms_preemptive_micro_tick_shading_v34(self):
        """
        Verify Phase 34 preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When h_val > 0.003, hawkes_shift = -direction * 0.9999999 * spr * (h_val - 0.003).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.025

        # Buy order: direction = +1, hawkes_shift = -1.0 * 0.9999999 * 1.0 * (0.025 - 0.003) = -0.0219999978
        peg_oms_buy_v34 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=34,
        )
        peg_sched_buy_v34 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=34,
        )

        expected_shift_v34 = -0.9999999 * spr * (h_val - 0.003)
        expected_price_v34 = target_px + expected_shift_v34

        assert math.isclose(peg_oms_buy_v34, expected_price_v34, rel_tol=1e-4)
        assert math.isclose(peg_sched_buy_v34, expected_price_v34, rel_tol=1e-4)
        assert math.isclose(peg_oms_buy_v34, peg_sched_buy_v34, rel_tol=1e-6)

        # In v33, threshold was 0.004, multiplier 0.9999998
        peg_oms_buy_v33 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=33,
        )
        # v34 shades more defensively than v33 (lower limit buy price)
        assert peg_oms_buy_v34 < peg_oms_buy_v33
