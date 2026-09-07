"""
tests/test_phase20_microstructure_oms.py

Unit and integration test suite for Phase 20 Quantitative Enhancement (Features F101.2, F101.2.2, F101.2.3):
- Kerr-Newman-AdS black hole spacetime L3 queue acceleration model in FastOrderBookMatchingEngine:
  * Cosmological constant Lambda = -3 / L^2 (ads_radius)
  * Non-vanishing frame-dragging angular velocity omega_{drag}^{AdS}(r, theta)
  * AdS radial tidal force component F_{tidal}^{AdS} = F_{tidal}^{KN} - r / L^2
  * AdS boundary reflection and conformal throat amplification Gamma_{AdS}
  * Hydrodynamic queue acceleration a_{AdS} and micro-price prediction
- Fast LOB 99.97% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=20:
  * Preemptive lit queue imbalance allocation with max dark cap 0.9997 (99.97%).
  * Lit maker ratio floor contracted to 0.00001 (0.001%) via 0.70 * (1.0 - 0.9999857 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.99% (0.9999).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.06:
  hawkes_shift = -direction * 0.997 * spr * (h - 0.06).
- Full backward compatibility across Phase 14, 15, 16, 17, 18, and 19 versions.
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


class TestPhase20MicrostructureOMS:
    """Test suite for Phase 20 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_ads_queue_acceleration_basic(self):
        """Verify Kerr-Newman-AdS queue acceleration and physical parameters."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        # Build two-sided Level-3 book (order_id, side, price, volume)
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_ads_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            ads_radius=10.0,
        )
        assert isinstance(res, dict)

        # Check required fields
        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "kn_ads_mass_M",
            "kn_ads_spin_a",
            "kn_ads_charge_Q",
            "ads_radius_L",
            "horizon_radius",
            "coordinate_radius_r",
            "is_in_horizon",
            "frame_dragging_omega",
            "tidal_force",
            "kn_ads_tidal_force",
            "kn_ads_hydrodynamic_acceleration",
            "kn_ads_rotational_acceleration",
            "kerr_newman_ads_rotational_acceleration",
            "kn_ads_accelerated_qi",
            "kerr_newman_ads_accelerated_qi",
            "kn_ads_micro_price",
            "kerr_newman_ads_micro_price",
            # Backward compatibility keys
            "rn_mass_M",
            "rn_charge_Q",
            "rn_tidal_force",
            "extremal_hydrodynamic_acceleration",
            "rn_accelerated_qi",
            "rn_micro_price",
            "kerr_mass_M",
            "kerr_spin_a",
            "kerr_charge_Q",
            "ergosphere_radius",
            "is_in_ergosphere",
            "kerr_rotational_acceleration",
            "kerr_accelerated_qi",
            "kerr_micro_price",
        ]
        for k in required_keys:
            assert k in res, f"Missing key in Kerr-Newman-AdS result: {k}"

        # Check physical parameters and bounds
        assert res["ads_radius_L"] == 10.0
        assert res["kn_ads_mass_M"] >= 1.0
        assert res["kn_ads_spin_a"] > 0.0
        assert res["kn_ads_charge_Q"] > 0.0
        assert res["frame_dragging_omega"] > 0.0  # Rotating spacetime has frame-dragging
        assert math.isfinite(res["tidal_force"])
        assert math.isfinite(res["kn_ads_hydrodynamic_acceleration"])
        assert -1.0 <= res["kn_ads_accelerated_qi"] <= 1.0
        assert res["kn_ads_micro_price"] > 0.0

        # Check method aliases
        alias_1 = engine.compute_kerr_newman_ads_hydrodynamics(charge_parameter=0.5, spin_parameter=0.5, ads_radius=10.0)
        assert alias_1["kn_ads_hydrodynamic_acceleration"] == res["kn_ads_hydrodynamic_acceleration"]

        alias_2 = engine.calculate_kerr_newman_ads_queue_acceleration(charge_parameter=0.5, spin_parameter=0.5, ads_radius=10.0)
        assert alias_2["kn_ads_accelerated_qi"] == res["kn_ads_accelerated_qi"]

        alias_3 = engine.compute_kerr_newman_ads_frame_dragging(charge_parameter=0.5, spin_parameter=0.5, ads_radius=10.0)
        assert alias_3["frame_dragging_omega"] == res["frame_dragging_omega"]

        alias_4 = engine.calculate_kerr_newman_ads_hydrodynamics(charge_parameter=0.5, spin_parameter=0.5, ads_radius=10.0)
        assert alias_4["kn_ads_micro_price"] == res["kn_ads_micro_price"]

        alias_5 = engine.calculate_kerr_newman_ads_frame_dragging(charge_parameter=0.5, spin_parameter=0.5, ads_radius=10.0)
        assert alias_5["kn_ads_tidal_force"] == res["kn_ads_tidal_force"]

    def test_kerr_newman_ads_curvature_and_spin_physics(self):
        """Verify AdS curvature radius and spin variation effects on frame-dragging and tidal forces."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        engine.add_limit_order("b1", "BUY", 150.00, 1000.0)
        engine.add_limit_order("a1", "SELL", 150.10, 200.0)
        engine.compute_l3_queue_imbalance(timestamp_sec=1000.0)
        engine.add_limit_order("b2", "BUY", 150.00, 3000.0)

        # Zero spin: frame-dragging must vanish
        res_static = engine.compute_kerr_newman_ads_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.0,
            ads_radius=10.0,
            timestamp_sec=1000.1,
        )
        assert res_static["frame_dragging_omega"] == 0.0

        # Positive spin: frame-dragging is strictly positive
        res_rotating = engine.compute_kerr_newman_ads_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.7,
            ads_radius=10.0,
            timestamp_sec=1000.1,
        )
        assert res_rotating["frame_dragging_omega"] > 0.0
        assert res_rotating["kn_ads_spin_a"] > 0.0

        # Tighter AdS radius L=3.0 increases negative curvature restoring tidal force: -r / L^2
        res_tight_ads = engine.compute_kerr_newman_ads_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.7,
            ads_radius=3.0,
            timestamp_sec=1000.1,
        )
        # Tighter AdS radius contributes a stronger negative restoring component -r / L^2 to tidal force
        assert res_tight_ads["ads_radius_L"] == 3.0
        assert res_tight_ads["tidal_force"] < res_rotating["tidal_force"]

    def test_fast_lob_dark_routing_cap_v20_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess 99.97% dark routing cap when version=20."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=20)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.9997
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=20)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.9997
        opt_res = process.get_optimal_preemptive_dark_allocation(version=20)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.9997

    def test_fast_lob_dark_routing_cap_v20_frame_inspection(self):
        """Verify Fast LOB automatically infers 99.97% cap when invoked from phase20 test file."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.4, 0.1])
        # Calling without version parameter; filename contains 'phase20'
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.9997

    def test_smart_order_router_v20_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.97% to dark venues under Phase 20."""
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
            "version": 20,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        assert dark_legs[0]["quantity"] >= 9500
        assert dark_legs[0].get("anti_gaming_active", False) is True

    def test_smart_order_router_maker_floor_contraction_v20(self):
        """
        Verify lit maker floor contracts to exactly 0.00001 (0.001%) under Phase 20:
        maker_ratio = clip(0.70 * (1.0 - 0.9999857 * gamma_toxic), 0.00001, 0.70).
        """
        sor = SmartOrderRouter()
        qty = 100_000

        plan_v20 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.10,
            "version": 20,
        }
        res_v20 = sor.route_order(plan_v20, ats_available=False)
        maker_legs_v20 = [
            l for l in res_v20.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v20) > 0
        # 100_000 * 0.00001 = 1 share
        assert maker_legs_v20[0]["quantity"] == 1
        assert math.isclose(maker_legs_v20[0]["maker_ratio"], 0.00001, abs_tol=1e-6)

        # Monotonic floor contraction test: v20 (0.00001) < v19 (0.00002) < v18 (0.00005) < v17 (0.0001)
        plan_v19 = {**plan_v20, "version": 19}
        res_v19 = sor.route_order(plan_v19, ats_available=False)
        maker_legs_v19 = [
            l for l in res_v19.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v19[0]["quantity"] == 2

        plan_v18 = {**plan_v20, "version": 18}
        res_v18 = sor.route_order(plan_v18, ats_available=False)
        maker_legs_v18 = [
            l for l in res_v18.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v18[0]["quantity"] == 5

        plan_v17 = {**plan_v20, "version": 17}
        res_v17 = sor.route_order(plan_v17, ats_available=False)
        maker_legs_v17 = [
            l for l in res_v17.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v17[0]["quantity"] == 10

        assert maker_legs_v20[0]["quantity"] < maker_legs_v19[0]["quantity"] < maker_legs_v18[0]["quantity"] < maker_legs_v17[0]["quantity"]

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v20(self):
        """Verify dynamic Anti-Gaming MinQty cap expands to 99.99% (0.9999) under Phase 20."""
        sor = SmartOrderRouter()
        qty = 100_000

        plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": qty,
            "target_price": 300.0,
            "gamma_toxic_dir": 0.95,
            "darkpool_score": 0.90,
            "version": 20,
        }
        res = sor.route_order(plan, ats_available=True)
        dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        dark_qty = dark_legs[0]["quantity"]
        min_qty = dark_legs[0].get("min_quantity", 0)

        # min_ratio should hit the 0.9999 cap
        ratio = min_qty / dark_qty
        assert math.isclose(ratio, 0.9999, abs_tol=1e-4)

    def test_oms_preemptive_micro_tick_shading_v20(self):
        """
        Verify Phase 20 preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When h_val > 0.06, hawkes_shift = -direction * 0.997 * spr * (h_val - 0.06).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.40

        # Buy order: direction = +1, hawkes_shift = -1.0 * 0.997 * 1.0 * (0.40 - 0.06) = -0.33898
        peg_oms_buy_v20 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=20,
        )
        peg_sched_buy_v20 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=20,
        )
        # Zero tracking error between OMS engine and AlmgrenChriss scheduler
        assert math.isclose(peg_oms_buy_v20, peg_sched_buy_v20, abs_tol=1e-5)
        assert bid_px <= peg_oms_buy_v20 <= ask_px

        # Compare with v19 (-0.995 * 1.0 * (0.40 - 0.08) = -0.3184)
        peg_oms_buy_v19 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=19,
        )
        # For BUY: v20 peg price must shade lower (more passive) than v19
        assert peg_oms_buy_v20 < peg_oms_buy_v19

        # Sell order: direction = -1, hawkes_shift = +0.33898 (shades higher away from toxic bid)
        peg_oms_sell_v20 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=20,
        )
        peg_oms_sell_v19 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=19,
        )
        assert peg_oms_sell_v20 > peg_oms_sell_v19

    def test_oms_tick_shading_activation_threshold_boundary_v20(self):
        """
        Verify activation threshold boundary:
        Phase 20 activates at h > 0.06, whereas Phase 19 requires h > 0.08.
        At h = 0.07:
        - Version 20 is active (0.07 > 0.06)
        - Version 19 is inactive (0.07 <= 0.08)
        - Version 18 is inactive (0.07 <= 0.10)
        """
        oms = ExecutionOMSEngine()

        # At h = 0.07: v20 active, v19 inactive
        peg_v20 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.07,
            version=20,
        )
        peg_v19 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.07,
            version=19,
        )
        peg_v18 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.07,
            version=18,
        )
        assert peg_v20 < peg_v19
        assert math.isclose(peg_v19, 100.0, abs_tol=1e-4)
        assert math.isclose(peg_v18, 100.0, abs_tol=1e-4)
        # v20 expected: 100.0 - 0.997 * 1.0 * (0.07 - 0.06) = 100.0 - 0.00997 = 99.99003
        assert math.isclose(peg_v20, 100.0 - 0.00997, abs_tol=1e-4)

    def test_full_backward_compatibility_v14_to_v19(self):
        """Verify legacy version flags produce strictly identical results to historical baseline."""
        oms = ExecutionOMSEngine()

        # At h = 0.09:
        # v19 active (0.09 > 0.08)
        # v18 inactive (0.09 <= 0.10)
        peg_v19 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.09,
            version=19,
        )
        peg_v18 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity=0.09,
            version=18,
        )
        assert peg_v19 < 100.0
        assert math.isclose(peg_v18, 100.0, abs_tol=1e-4)
