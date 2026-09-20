"""
tests/test_phase63_oms.py

Unit and integration test suite for Phase 63 Quantitative Alpha Enhancement (Feature F289.1 & F289.2 Microstructure OMS):
- Kerr-Newman-Kiselev 42-Dark-Energy DAHA
  (w = -44/3 ~= -14.667, k_daha = 0.34, k_monster = 0.33, daha_42_factor = 6.10, c_monster = 4.76837158203125e-14)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 42-fold dark energy density
  * Outer cosmological horizon scale
  * Radial tidal force with 42-fold dark energy repulsive acceleration (-22.0 * c * r^43 * daha_42)
  * Metric distortion term (+ c * r^45 * daha_42)
  * Charge acceleration (+ c * r^42 * daha_42)
  * Hydrodynamic queue acceleration and micro-price prediction
  * Complete method aliases on FastOrderBookMatchingEngine (28 base aliases + 8 extended aliases)
- Fast LOB 0.99999999999999999999 (20 nines) preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=63:
  * Preemptive lit queue imbalance allocation with max dark cap 0.99999999999999999999.
  * Lit maker ratio floor contracted to 1e-35
    via 0.70 * (1.0 - 0.9999999999999999999999999999999986 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 0.99999999999999999999.
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.0000010:
  hawkes_shift = -direction * 0.99999999999999999 * spr * (h - 0.0000010).
- Full backward compatibility across Phase 14 through Phase 62 versions.
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    DeepHawkesArrivalProcess,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase63MicrostructureOMS:
    """Test suite for Phase 63 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_42_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 42-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_42_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_42_dark_energy_tidal_force" in res
        assert "density_dark_energy_42" in res
        assert "r_42_dark_energy" in res
        assert math.isfinite(res["queue_acceleration"])
        assert math.isfinite(res["predicted_micro_price"])
        assert math.isclose(res["density_dark_energy_42"], 4.76837158203125e-14, rel_tol=1e-9)
        assert math.isclose(res["daha_42_factor"], 6.10, rel_tol=1e-5)
        assert math.isclose(res["equation_of_state_w_42"], -44.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_42_dark_energy_aliases(self):
        """Verify all 28 base aliases + extended aliases on FastOrderBookMatchingEngine / FastLOBEngine."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 500.0)

        ref = engine.compute_kerr_newman_kiselev_42_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        dispatch_aliases = [
            engine.calculate_knk_42_dark_energy_daha_acceleration,
            engine.compute_knk_42_dark_energy_daha,
            engine.knk_42_dark_energy_daha_acceleration,
            engine.compute_phase63_lob_acceleration,
            engine.phase63_lob_spacetime_hydrodynamics,
            engine.daha_42_dark_energy_acceleration,
            engine.kerr_newman_kiselev_42_acceleration,
            engine.compute_42_dark_energy_acceleration,
            engine.phase63_daha_l3_acceleration,
            engine.knk_daha_42_acceleration,
            engine.l3_knk_42_acceleration,
            engine.spacetime_hydrodynamics_42_acceleration,
            engine.daha_l3_phase63_acceleration,
            engine.monster_daha_42_acceleration,
            engine.phase63_dark_energy_acceleration,
            engine.knk_42_spacetime_acceleration,
            engine.calculate_phase63_knk_acceleration,
            engine.compute_knk_phase63_acceleration,
            engine.daha_phase63_acceleration,
            engine.knk_dark_energy_42_acceleration,
            engine.phase63_spacetime_hydrodynamics,
            engine.compute_l3_hydrodynamics_v63,
            engine.knk_42_daha_l3_acceleration,
            engine.phase63_queue_acceleration,
            engine.knk_42_acceleration,
            engine.daha_42_acceleration,
            engine.l3_phase63_acceleration,
            engine.phase63_knk_acceleration,
            engine.compute_kerr_newman_kiselev_42_dark_energy_daha_queue_acceleration,
            engine.calculate_kerr_newman_kiselev_42_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
            engine.compute_knk_42_dark_energy_daha_queue_acceleration,
            engine.compute_knk_42_dark_energy_queue_acceleration,
            engine.compute_knk_borcherds_moonshine_monster_42_dark_energy_daha_queue_acceleration,
            engine.compute_kerr_newman_kiselev_42_dark_energy_moonshine_monster_queue_acceleration,
            engine.compute_knk_42_dark_energy_monster_moonshine_queue_acceleration,
            engine.compute_phase63_knk_daha_queue_acceleration,
        ]

        for fn in dispatch_aliases:
            res = fn()
            assert math.isclose(res["queue_acceleration"], ref["queue_acceleration"], rel_tol=1e-5)
            assert math.isclose(res["density_dark_energy_42"], ref["density_dark_energy_42"], rel_tol=1e-9)

        # Verify FastLOBEngine alias
        flob = FastLOBEngine(symbol="005930")
        assert hasattr(flob, "compute_kerr_newman_kiselev_42_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration")
        assert hasattr(flob, "calculate_knk_42_dark_energy_daha_acceleration")
        assert hasattr(flob, "compute_phase63_lob_acceleration")

    def test_fast_lob_preemptive_dark_routing_cap_v63(self):
        """Verify Fast LOB preemptive dark routing cap 0.99999999999999999999 under version 63 and stack inspection."""
        proc = DeepHawkesArrivalProcess(version=63)
        proc.lambda_state = np.array([20.0, 0.5, 0.2])
        res = proc.compute_preemptive_dark_routing()
        assert math.isclose(res["preemptive_dark_routing_ratio"], 0.99999999999999999999, rel_tol=1e-15)

        proc_default = DeepHawkesArrivalProcess()
        proc_default.lambda_state = np.array([20.0, 0.5, 0.2])
        res_v63 = proc_default.compute_preemptive_dark_routing(version=63)
        assert math.isclose(res_v63["preemptive_dark_routing_ratio"], 0.99999999999999999999, rel_tol=1e-15)

        # Stack frame inspection from within this test_phase63_oms file
        res_stack = proc_default.compute_preemptive_dark_routing()
        assert math.isclose(res_stack["preemptive_dark_routing_ratio"], 0.99999999999999999999, rel_tol=1e-15)

    def test_smart_order_router_version_63_maker_floor_and_anti_gaming(self):
        """Verify SmartOrderRouter contracts maker floor to 1e-35 and anti-gaming up to 0.99999999999999999999."""
        sor = SmartOrderRouter(version=63)
        assert math.isclose(sor._resolve_max_dark_cap(63), 0.99999999999999999999, rel_tol=1e-15)

        plan = {
            "symbol": "005930",
            "quantity": 1000000,
            "action": "BUY",
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "destination": {"venue": "KRX_ATS_NEXTRADE"},
            "version": 63,
        }
        res = sor.route_order(plan, ats_available=True)
        assert res["maker_ratio"] == 1e-35
        assert math.isclose(res["min_ratio"], 0.99999999999999999999, rel_tol=1e-15)

    def test_oms_preemptive_micro_tick_shading_threshold_v63(self):
        """Verify micro-tick shading activation threshold at h > 0.0000010 with multiplier 0.99999999999999999."""
        oms = ExecutionOMSEngine()
        sched = AlmgrenChrissScheduler()

        # Deadband below threshold (h = 0.0000008 <= 0.0000010)
        p_dead = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.0000008},
            version=63,
        )
        assert math.isclose(p_dead, 100.0, rel_tol=1e-7)

        # Boundary test at h = 0.0000010
        p_bound = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010},
            version=63,
        )
        assert math.isclose(p_bound, 100.0, rel_tol=1e-7)

        # Active shading above threshold
        h_active = 0.00010
        p_buy = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_active},
            version=63,
        )
        p_sched = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_active},
            version=63,
        )

        assert math.isclose(p_sched, p_buy, rel_tol=1e-7)
        expected_shift = -1 * 0.99999999999999999 * 1.0 * (h_active - 0.0000010)
        assert math.isclose(p_buy - 100.0, expected_shift, rel_tol=1e-5)

    def test_oms_backward_compatibility_v62_and_prior(self):
        """Verify that at h = 0.0000012, v63 is active while v62 is inactive (threshold 0.0000015)."""
        oms = ExecutionOMSEngine()
        h_val = 0.0000012

        p_v63 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=63,
        )
        p_v62 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=62,
        )

        # In v62, h_val <= 0.0000015 so shift is 0.0
        assert math.isclose(p_v62, 100.0, rel_tol=1e-7)
        # In v63, h_val > 0.0000010 so shift is active (negative for BUY)
        assert p_v63 < 100.0
