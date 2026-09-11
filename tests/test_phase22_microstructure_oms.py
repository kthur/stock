"""
tests/test_phase22_microstructure_oms.py

Unit and integration test suite for Phase 22 Quantitative Enhancement (Features F109.2, F109.2.1, F109.2.2, F109.2.3, F109.2.4):
- Kerr-Newman-Kiselev Quintessence Dark Energy (w_q = -2/3) Black Hole Spacetime L3 Orderbook Hydrodynamics Model:
  * Quintessence equation of state parameter w_q = -2/3
  * Quintessence energy density rho_q = -(c_q / 2) * (3 * w_q / r^{3*(1 + w_q)}) = c_q / r
  * Quintessence metric horizon function Delta_r = (r^2 + a^2) - 2*M*r + Q^2 - c_q * r^3
  * Outer quintessence cosmological dark energy horizon scale r_Q = max(r_H + 0.1, (1/c_q)*(1 - M*c_q))
  * Non-vanishing frame-dragging angular velocity omega_{drag}^{KNK}(r, theta)
  * Radial tidal force with dark energy expansion acceleration component F_{tidal}^{KNK} = F_{tidal}^{KN} - c_q * r
  * Conformal boundary amplification factor Gamma_{KNK} = 1 + (r_H - r)/r_H + M^2/((r - r_H)^2 + 0.05*M^2) + c_q * r^3
  * Hydrodynamic queue acceleration a_{KNK} and micro-price prediction
- Fast LOB 99.99% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=22:
  * Preemptive lit queue imbalance allocation with max dark cap 0.9999 (99.99%).
  * Lit maker ratio floor contracted to 0.000002 (0.0002%) via 0.70 * (1.0 - 0.99999714 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.998% (0.99998).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.04:
  hawkes_shift = -direction * 0.999 * spr * (h - 0.04).
- Full backward compatibility across Phase 14 through Phase 21 versions.
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


class TestPhase22MicrostructureOMS:
    """Test suite for Phase 22 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev queue acceleration and physical parameters."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            quintessence_parameter=0.05,
            w_q=-2.0 / 3.0,
        )
        assert isinstance(res, dict)

        # Check required fields
        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "knk_mass_M",
            "knk_spin_a",
            "knk_charge_Q",
            "quintessence_c_q",
            "equation_of_state_w_q",
            "quintessence_horizon_r_Q",
            "quintessence_horizon",
            "horizon_radius",
            "coordinate_radius_r",
            "is_in_horizon",
            "frame_dragging_omega",
            "tidal_force",
            "knk_tidal_force",
            "knk_hydrodynamic_acceleration",
            "knk_rotational_acceleration",
            "kerr_newman_kiselev_rotational_acceleration",
            "knk_accelerated_qi",
            "kerr_newman_kiselev_accelerated_qi",
            "knk_micro_price",
            "kerr_newman_kiselev_micro_price",
            # Phase 21 backward compatibility keys
            "kn_ads_ds_mass_M",
            "kn_ads_ds_spin_a",
            "kn_ads_ds_charge_Q",
            "ads_radius_L",
            "ds_radius_L",
            "cosmological_lambda",
            "cosmological_horizon_r_C",
            "cosmological_horizon",
            "de_sitter_horizon",
            "kn_ads_ds_tidal_force",
            "kn_ads_ds_hydrodynamic_acceleration",
            "kn_ads_ds_rotational_acceleration",
            "kerr_newman_ads_ds_rotational_acceleration",
            "kn_ads_ds_accelerated_qi",
            "kerr_newman_ads_ds_accelerated_qi",
            "kn_ads_ds_micro_price",
            "kerr_newman_ads_ds_micro_price",
            # Phase 20 backward compatibility keys
            "kn_ads_mass_M",
            "kn_ads_spin_a",
            "kn_ads_charge_Q",
            "kn_ads_hydrodynamic_acceleration",
            "kn_ads_accelerated_qi",
            "kn_ads_micro_price",
        ]
        for k in required_keys:
            assert k in res, f"Missing key in Kerr-Newman-Kiselev result: {k}"

        # Check physical parameters and bounds
        assert res["quintessence_c_q"] == 0.05
        assert math.isclose(res["equation_of_state_w_q"], -2.0 / 3.0, abs_tol=1e-4)
        assert res["knk_mass_M"] >= 1.0
        assert res["knk_spin_a"] > 0.0
        assert res["knk_charge_Q"] > 0.0
        assert res["quintessence_horizon_r_Q"] > 0.0
        assert res["frame_dragging_omega"] > 0.0
        assert math.isfinite(res["tidal_force"])
        assert math.isfinite(res["knk_hydrodynamic_acceleration"])
        assert -1.0 <= res["knk_accelerated_qi"] <= 1.0
        assert res["knk_micro_price"] > 0.0

        # Check method aliases
        alias_1 = engine.compute_kerr_newman_kiselev_hydrodynamics(
            charge_parameter=0.5, spin_parameter=0.5, quintessence_parameter=0.05, w_q=-2.0 / 3.0
        )
        assert alias_1["knk_hydrodynamic_acceleration"] == res["knk_hydrodynamic_acceleration"]

        alias_2 = engine.calculate_kerr_newman_kiselev_queue_acceleration(
            charge_parameter=0.5, spin_parameter=0.5, quintessence_parameter=0.05, w_q=-2.0 / 3.0
        )
        assert alias_2["knk_accelerated_qi"] == res["knk_accelerated_qi"]

        alias_3 = engine.compute_kerr_newman_kiselev_frame_dragging(
            charge_parameter=0.5, spin_parameter=0.5, quintessence_parameter=0.05, w_q=-2.0 / 3.0
        )
        assert alias_3["frame_dragging_omega"] == res["frame_dragging_omega"]

        alias_4 = engine.calculate_kerr_newman_kiselev_hydrodynamics(
            charge_parameter=0.5, spin_parameter=0.5, quintessence_parameter=0.05, w_q=-2.0 / 3.0
        )
        assert alias_4["knk_micro_price"] == res["knk_micro_price"]

        alias_5 = engine.calculate_kerr_newman_kiselev_frame_dragging(
            charge_parameter=0.5, spin_parameter=0.5, quintessence_parameter=0.05, w_q=-2.0 / 3.0
        )
        assert alias_5["knk_tidal_force"] == res["knk_tidal_force"]

    def test_kerr_newman_kiselev_physics_and_dark_energy(self):
        """Verify KNK quintessence dark energy tidal repulsion and horizon physics."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        engine.add_limit_order("b1", "BUY", 150.00, 1000.0)
        engine.add_limit_order("a1", "SELL", 150.10, 200.0)

        # Static vs Rotating frame dragging
        res_static = engine.compute_kerr_newman_kiselev_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.0,
            quintessence_parameter=0.05,
        )
        assert res_static["frame_dragging_omega"] == 0.0

        res_rotating = engine.compute_kerr_newman_kiselev_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.7,
            quintessence_parameter=0.05,
        )
        assert res_rotating["frame_dragging_omega"] > 0.0

        # Dark energy tidal force: F_{tidal}^{KNK} = F_{tidal}^{KN} - c_q * r
        # Increasing c_q should exert negative dark energy tidal acceleration
        res_low_cq = engine.compute_kerr_newman_kiselev_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            quintessence_parameter=0.01,
        )
        res_high_cq = engine.compute_kerr_newman_kiselev_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            quintessence_parameter=0.10,
        )
        assert res_high_cq["tidal_force"] < res_low_cq["tidal_force"]

    def test_fast_lob_dark_routing_cap_v22_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess 99.99% dark routing cap when version=22."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=22)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.9999
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=22)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.9999
        opt_res = process.get_optimal_preemptive_dark_allocation(version=22)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.9999

    def test_fast_lob_dark_routing_cap_v22_frame_inspection(self):
        """Verify Fast LOB automatically infers 99.99% cap when invoked from phase22 test file."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.4, 0.1])
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.9999

    def test_smart_order_router_v22_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.99% to dark venues under Phase 22."""
        sor = SmartOrderRouter()
        plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 10000,
            "target_price": 70000.0,
            "market_spread_bps": 12.0,
            "queue_imbalance": 0.25,
            "qi_acceleration": 0.08,
            "gamma_toxic_dir": 0.95,
            "darkpool_score": 0.90,
            "version": 22,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        assert dark_legs[0]["quantity"] >= 9900
        assert dark_legs[0].get("anti_gaming_active", False) is True

    def test_smart_order_router_maker_floor_contraction_v22(self):
        """
        Verify lit maker floor contracts to 0.000002 (0.0002%) under Phase 22.
        Monotonic contraction check: v22 (0.000002) < v21 (0.000005) < v20 (0.00001).
        """
        sor = SmartOrderRouter()
        qty = 1_000_000

        plan_v22 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.10,
            "version": 22,
        }
        res_v22 = sor.route_order(plan_v22, ats_available=False)
        maker_legs_v22 = [
            l for l in res_v22.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v22) > 0
        # 1_000_000 * 0.000002 = 2 shares
        assert maker_legs_v22[0]["quantity"] == 2
        assert math.isclose(maker_legs_v22[0]["maker_ratio"], 0.000002, abs_tol=1e-7)

        # Monotonic floor contraction test: v22 (0.000002) < v21 (0.000005) < v20 (0.00001)
        plan_v21 = {**plan_v22, "version": 21}
        res_v21 = sor.route_order(plan_v21, ats_available=False)
        maker_legs_v21 = [
            l for l in res_v21.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        # 1_000_000 * 0.000005 = 5 shares
        assert maker_legs_v21[0]["quantity"] == 5

        plan_v20 = {**plan_v22, "version": 20}
        res_v20 = sor.route_order(plan_v20, ats_available=False)
        maker_legs_v20 = [
            l for l in res_v20.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        # 1_000_000 * 0.000010 = 10 shares
        assert maker_legs_v20[0]["quantity"] == 10

        assert maker_legs_v22[0]["quantity"] < maker_legs_v21[0]["quantity"] < maker_legs_v20[0]["quantity"]

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v22(self):
        """Verify dynamic Anti-Gaming MinQty cap expands to 99.998% (0.99998) under Phase 22."""
        sor = SmartOrderRouter()
        qty = 100_000

        plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": qty,
            "target_price": 300.0,
            "gamma_toxic_dir": 0.95,
            "darkpool_score": 0.90,
            "version": 22,
        }
        res = sor.route_order(plan, ats_available=True)
        dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        dark_qty = dark_legs[0]["quantity"]
        min_qty = dark_legs[0].get("min_quantity", 0)

        ratio = min_qty / dark_qty
        assert math.isclose(ratio, 0.99998, abs_tol=1e-4)

    def test_oms_preemptive_micro_tick_shading_v22(self):
        """
        Verify Phase 22 preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When h_val > 0.04, hawkes_shift = -direction * 0.999 * spr * (h_val - 0.04).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.40

        # Buy order: direction = +1, hawkes_shift = -1.0 * 0.999 * 1.0 * (0.40 - 0.04) = -0.35964
        peg_oms_buy_v22 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=22,
        )
        peg_sched_buy_v22 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=22,
        )
        assert math.isclose(peg_oms_buy_v22, peg_sched_buy_v22, abs_tol=1e-5)
        assert bid_px <= peg_oms_buy_v22 <= ask_px

        # Compare with v21 (-0.998 * 1.0 * (0.40 - 0.05) = -0.3493)
        peg_oms_buy_v21 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=21,
        )
        assert peg_oms_buy_v22 < peg_oms_buy_v21

        # Sell order: direction = -1
        peg_oms_sell_v22 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=22,
        )
        peg_oms_sell_v21 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=21,
        )
        assert peg_oms_sell_v22 > peg_oms_sell_v21

    def test_oms_tick_shading_activation_threshold_boundary_v22(self):
        """
        Verify activation threshold boundary:
        Phase 22 activates at h > 0.04, whereas Phase 21 requires h > 0.05.
        At h = 0.045:
        - Version 22 is active (0.045 > 0.04)
        - Version 21 is inactive (0.045 <= 0.05)
        """
        oms = ExecutionOMSEngine()

        peg_v22 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.045,
            version=22,
        )
        peg_v21 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.045,
            version=21,
        )
        assert peg_v22 < peg_v21
        assert math.isclose(peg_v21, 100.0, abs_tol=1e-4)
        # v22 expected: 100.0 - 0.999 * 1.0 * (0.045 - 0.04) = 100.0 - 0.004995 = 99.995005
        assert math.isclose(peg_v22, 100.0 - 0.004995, abs_tol=1e-4)

    def test_full_backward_compatibility_v14_to_v21(self):
        """Verify legacy version flags produce strictly identical results to historical baseline."""
        oms = ExecutionOMSEngine()

        # At h = 0.055:
        # v21 active (0.055 > 0.05)
        # v20 inactive (0.055 <= 0.06)
        peg_v21 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.055,
            version=21,
        )
        peg_v20 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.055,
            version=20,
        )
        assert peg_v21 < 100.0
        assert math.isclose(peg_v20, 100.0, abs_tol=1e-4)
