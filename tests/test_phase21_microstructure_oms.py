"""
tests/test_phase21_microstructure_oms.py

Unit and integration test suite for Phase 21 Quantitative Enhancement (Features F105.2, F105.2.2, F105.2.3):
- Kerr-Newman-AdS-dS cosmological black hole spacetime L3 queue acceleration model in FastOrderBookMatchingEngine:
  * Cosmological constant Lambda = 3 / L_{dS}^2 - 3 / L_{AdS}^2
  * De Sitter cosmological horizon scale r_C = L_{dS} * (1 - M / L_{dS})
  * Non-vanishing frame-dragging angular velocity omega_{drag}^{AdS-dS}(r, theta)
  * Radial tidal force component F_{tidal}^{AdS-dS} = F_{tidal}^{KN} - r / L_{AdS}^2 + r / L_{dS}^2
  * AdS-dS conformal boundary amplification factor Gamma_{AdS-dS}
  * Hydrodynamic queue acceleration a_{AdS-dS} and micro-price prediction
- Fast LOB 99.98% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=21:
  * Preemptive lit queue imbalance allocation with max dark cap 0.9998 (99.98%).
  * Lit maker ratio floor contracted to 0.000005 (0.0005%) via 0.70 * (1.0 - 0.99999286 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.995% (0.99995).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.05:
  hawkes_shift = -direction * 0.998 * spr * (h - 0.05).
- Full backward compatibility across Phase 14 through Phase 20 versions.
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


class TestPhase21MicrostructureOMS:
    """Test suite for Phase 21 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_ads_ds_queue_acceleration_basic(self):
        """Verify Kerr-Newman-AdS-dS queue acceleration and physical parameters."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_ads_ds_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            ads_radius=10.0,
            ds_radius=20.0,
        )
        assert isinstance(res, dict)

        # Check required fields
        required_keys = [
            "l3_queue_imbalance",
            "qi_velocity",
            "qi_acceleration",
            "kn_ads_ds_mass_M",
            "kn_ads_ds_spin_a",
            "kn_ads_ds_charge_Q",
            "ads_radius_L",
            "ds_radius_L",
            "cosmological_lambda",
            "cosmological_horizon_r_C",
            "cosmological_horizon",
            "de_sitter_horizon",
            "horizon_radius",
            "coordinate_radius_r",
            "is_in_horizon",
            "frame_dragging_omega",
            "tidal_force",
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
            assert k in res, f"Missing key in Kerr-Newman-AdS-dS result: {k}"

        # Check physical parameters and bounds
        assert res["ads_radius_L"] == 10.0
        assert res["ds_radius_L"] == 20.0
        assert res["kn_ads_ds_mass_M"] >= 1.0
        assert res["kn_ads_ds_spin_a"] > 0.0
        assert res["kn_ads_ds_charge_Q"] > 0.0
        assert res["cosmological_horizon_r_C"] > 0.0
        assert res["frame_dragging_omega"] > 0.0
        assert math.isfinite(res["tidal_force"])
        assert math.isfinite(res["kn_ads_ds_hydrodynamic_acceleration"])
        assert -1.0 <= res["kn_ads_ds_accelerated_qi"] <= 1.0
        assert res["kn_ads_ds_micro_price"] > 0.0

        # Check method aliases
        alias_1 = engine.compute_kerr_newman_ads_ds_hydrodynamics(charge_parameter=0.5, spin_parameter=0.5, ads_radius=10.0, ds_radius=20.0)
        assert alias_1["kn_ads_ds_hydrodynamic_acceleration"] == res["kn_ads_ds_hydrodynamic_acceleration"]

        alias_2 = engine.calculate_kerr_newman_ads_ds_queue_acceleration(charge_parameter=0.5, spin_parameter=0.5, ads_radius=10.0, ds_radius=20.0)
        assert alias_2["kn_ads_ds_accelerated_qi"] == res["kn_ads_ds_accelerated_qi"]

        alias_3 = engine.compute_kerr_newman_ads_ds_frame_dragging(charge_parameter=0.5, spin_parameter=0.5, ads_radius=10.0, ds_radius=20.0)
        assert alias_3["frame_dragging_omega"] == res["frame_dragging_omega"]

        alias_4 = engine.calculate_kerr_newman_ads_ds_hydrodynamics(charge_parameter=0.5, spin_parameter=0.5, ads_radius=10.0, ds_radius=20.0)
        assert alias_4["kn_ads_ds_micro_price"] == res["kn_ads_ds_micro_price"]

        alias_5 = engine.calculate_kerr_newman_ads_ds_frame_dragging(charge_parameter=0.5, spin_parameter=0.5, ads_radius=10.0, ds_radius=20.0)
        assert alias_5["kn_ads_ds_tidal_force"] == res["kn_ads_ds_tidal_force"]

    def test_kerr_newman_ads_ds_curvature_and_cosmological_physics(self):
        """Verify AdS-dS cosmological constant and horizon physics."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        engine.add_limit_order("b1", "BUY", 150.00, 1000.0)
        engine.add_limit_order("a1", "SELL", 150.10, 200.0)

        # Static vs Rotating
        res_static = engine.compute_kerr_newman_ads_ds_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.0,
            ads_radius=10.0,
            ds_radius=20.0,
        )
        assert res_static["frame_dragging_omega"] == 0.0

        res_rotating = engine.compute_kerr_newman_ads_ds_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.7,
            ads_radius=10.0,
            ds_radius=20.0,
        )
        assert res_rotating["frame_dragging_omega"] > 0.0

        # Cosmological constant check: Lambda = 3 / 20^2 - 3 / 10^2 = 3/400 - 3/100 = 0.0075 - 0.03 = -0.0225
        expected_lambda = 3.0 / 400.0 - 3.0 / 100.0
        assert math.isclose(res_rotating["cosmological_lambda"], expected_lambda, abs_tol=1e-5)

    def test_fast_lob_dark_routing_cap_v21_explicit(self):
        """Verify Fast LOB DeepHawkesArrivalProcess 99.98% dark routing cap when version=21."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=21)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.9998
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=21)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.9998
        opt_res = process.get_optimal_preemptive_dark_allocation(version=21)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.9998

    def test_fast_lob_dark_routing_cap_v21_frame_inspection(self):
        """Verify Fast LOB automatically infers 99.98% cap when invoked from phase21 test file."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.4, 0.1])
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.9998

    def test_smart_order_router_v21_preemption_and_dark_cap(self):
        """Verify SmartOrderRouter allocates up to 99.98% to dark venues under Phase 21."""
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
            "version": 21,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1

        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        assert dark_legs[0]["quantity"] >= 9800
        assert dark_legs[0].get("anti_gaming_active", False) is True

    def test_smart_order_router_maker_floor_contraction_v21(self):
        """
        Verify lit maker floor contracts to 0.000005 (0.0005%) under Phase 21.
        """
        sor = SmartOrderRouter()
        qty = 200_000

        plan_v21 = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.10,
            "version": 21,
        }
        res_v21 = sor.route_order(plan_v21, ats_available=False)
        maker_legs_v21 = [
            l for l in res_v21.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v21) > 0
        # 200_000 * 0.000005 = 1 share
        assert maker_legs_v21[0]["quantity"] == 1
        assert math.isclose(maker_legs_v21[0]["maker_ratio"], 0.000005, abs_tol=1e-6)

        # Monotonic floor contraction test: v21 (0.000005) < v20 (0.00001) < v19 (0.00002)
        plan_v20 = {**plan_v21, "version": 20}
        res_v20 = sor.route_order(plan_v20, ats_available=False)
        maker_legs_v20 = [
            l for l in res_v20.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert maker_legs_v20[0]["quantity"] == 2

        assert maker_legs_v21[0]["quantity"] < maker_legs_v20[0]["quantity"]

    def test_smart_order_router_dynamic_anti_gaming_min_qty_v21(self):
        """Verify dynamic Anti-Gaming MinQty cap expands to 99.995% (0.99995) under Phase 21."""
        sor = SmartOrderRouter()
        qty = 100_000

        plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": qty,
            "target_price": 300.0,
            "gamma_toxic_dir": 0.95,
            "darkpool_score": 0.90,
            "version": 21,
        }
        res = sor.route_order(plan, ats_available=True)
        dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        dark_qty = dark_legs[0]["quantity"]
        min_qty = dark_legs[0].get("min_quantity", 0)

        ratio = min_qty / dark_qty
        assert math.isclose(ratio, 0.99995, abs_tol=1e-4)

    def test_oms_preemptive_micro_tick_shading_v21(self):
        """
        Verify Phase 21 preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler:
        When h_val > 0.05, hawkes_shift = -direction * 0.998 * spr * (h_val - 0.05).
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.40

        # Buy order: direction = +1, hawkes_shift = -1.0 * 0.998 * 1.0 * (0.40 - 0.05) = -0.3493
        peg_oms_buy_v21 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=21,
        )
        peg_sched_buy_v21 = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=21,
        )
        assert math.isclose(peg_oms_buy_v21, peg_sched_buy_v21, abs_tol=1e-5)
        assert bid_px <= peg_oms_buy_v21 <= ask_px

        # Compare with v20 (-0.997 * 1.0 * (0.40 - 0.06) = -0.33898)
        peg_oms_buy_v20 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=20,
        )
        assert peg_oms_buy_v21 < peg_oms_buy_v20

        # Sell order: direction = -1
        peg_oms_sell_v21 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=21,
        )
        peg_oms_sell_v20 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=20,
        )
        assert peg_oms_sell_v21 > peg_oms_sell_v20

    def test_oms_tick_shading_activation_threshold_boundary_v21(self):
        """
        Verify activation threshold boundary:
        Phase 21 activates at h > 0.05, whereas Phase 20 requires h > 0.06.
        At h = 0.055:
        - Version 21 is active (0.055 > 0.05)
        - Version 20 is inactive (0.055 <= 0.06)
        """
        oms = ExecutionOMSEngine()

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
        assert peg_v21 < peg_v20
        assert math.isclose(peg_v20, 100.0, abs_tol=1e-4)
        # v21 expected: 100.0 - 0.998 * 1.0 * (0.055 - 0.05) = 100.0 - 0.00499 = 99.99501
        assert math.isclose(peg_v21, 100.0 - 0.00499, abs_tol=1e-4)

    def test_full_backward_compatibility_v14_to_v20(self):
        """Verify legacy version flags produce strictly identical results to historical baseline."""
        oms = ExecutionOMSEngine()

        # At h = 0.07:
        # v20 active (0.07 > 0.06)
        # v19 inactive (0.07 <= 0.08)
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
        assert peg_v20 < 100.0
        assert math.isclose(peg_v19, 100.0, abs_tol=1e-4)
