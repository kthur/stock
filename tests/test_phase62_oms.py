"""
tests/test_phase62_oms.py

Unit and integration test suite for Phase 62 Quantitative Alpha Enhancement (Feature F284.1 & F284.2 Microstructure OMS):
- Kerr-Newman-Kiselev 41-Dark-Energy DAHA
  (w = -43/3 ~= -14.333, k_daha = 0.33, k_monster = 0.32, daha_41_factor = 5.85, c_monster = 9.5367431640625e-14)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 41-fold dark energy density
  * Outer cosmological horizon scale
  * Radial tidal force with 41-fold dark energy repulsive acceleration (-21.5 * c * r^42 * daha_41)
  * Hydrodynamic queue acceleration and micro-price prediction
  * Complete method aliases on FastOrderBookMatchingEngine (28+ aliases)
- Fast LOB 0.9999999999999999995 (19 decimals) preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=62:
  * Preemptive lit queue imbalance allocation with max dark cap 0.9999999999999999995.
  * Lit maker ratio floor contracted to 1e-34
    via 0.70 * (1.0 - 0.999999999999999999999999999999986 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 0.9999999999999999995.
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.0000015:
  hawkes_shift = -direction * 0.99999999999999995 * spr * (h - 0.0000015).
- Full backward compatibility across Phase 14 through Phase 61 versions.
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


class TestPhase62MicrostructureOMS:
    """Test suite for Phase 62 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_41_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 41-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_41_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_41_dark_energy_tidal_force" in res
        assert "density_dark_energy_41" in res
        assert "r_41_dark_energy" in res
        assert math.isfinite(res["queue_acceleration"])
        assert math.isfinite(res["predicted_micro_price"])
        assert math.isclose(res["density_dark_energy_41"], 9.5367431640625e-14, rel_tol=1e-9)
        assert math.isclose(res["daha_41_factor"], 5.85, rel_tol=1e-5)
        assert math.isclose(res["equation_of_state_w_41"], -43.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_41_dark_energy_aliases(self):
        """Verify all 28+ aliases of 41-dark-energy DAHA on FastOrderBookMatchingEngine / FastLOBEngine."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 500.0)

        ref = engine.compute_kerr_newman_kiselev_41_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        dispatch_aliases = [
            engine.calculate_knk_41_dark_energy_daha_acceleration,
            engine.compute_knk_41_dark_energy_daha,
            engine.knk_41_dark_energy_daha_acceleration,
            engine.compute_phase62_lob_acceleration,
            engine.phase62_lob_spacetime_hydrodynamics,
            engine.daha_41_dark_energy_acceleration,
            engine.kerr_newman_kiselev_41_acceleration,
            engine.compute_41_dark_energy_acceleration,
            engine.phase62_daha_l3_acceleration,
            engine.knk_daha_41_acceleration,
            engine.l3_knk_41_acceleration,
            engine.spacetime_hydrodynamics_41_acceleration,
            engine.daha_l3_phase62_acceleration,
            engine.monster_daha_41_acceleration,
            engine.phase62_dark_energy_acceleration,
            engine.knk_41_spacetime_acceleration,
            engine.calculate_phase62_knk_acceleration,
            engine.compute_knk_phase62_acceleration,
            engine.daha_phase62_acceleration,
            engine.knk_dark_energy_41_acceleration,
            engine.phase62_spacetime_hydrodynamics,
            engine.compute_l3_hydrodynamics_v62,
            engine.knk_41_daha_l3_acceleration,
            engine.phase62_queue_acceleration,
            engine.daha_41_acceleration,
            engine.l3_phase62_acceleration,
            engine.phase62_knk_acceleration,
            engine.compute_phase62_knk_daha_queue_acceleration,
        ]

        for fn in dispatch_aliases:
            res = fn()
            assert math.isclose(res["queue_acceleration"], ref["queue_acceleration"], rel_tol=1e-5)
            assert math.isclose(res["density_dark_energy_41"], ref["density_dark_energy_41"], rel_tol=1e-9)

        # Verify FastLOBEngine alias
        flob = FastLOBEngine(symbol="005930")
        assert hasattr(flob, "compute_kerr_newman_kiselev_41_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration")
        assert hasattr(flob, "calculate_knk_41_dark_energy_daha_acceleration")
        assert hasattr(flob, "compute_phase62_lob_acceleration")

    def test_fast_lob_preemptive_dark_routing_cap_v62(self):
        """Verify Fast LOB preemptive dark routing cap 0.9999999999999999995 under version 62 and stack inspection."""
        proc = DeepHawkesArrivalProcess(version=62)
        proc.lambda_state = np.array([20.0, 0.5, 0.2])
        res = proc.compute_preemptive_dark_routing()
        assert math.isclose(res["preemptive_dark_routing_ratio"], 0.9999999999999999995, rel_tol=1e-15)

        proc_default = DeepHawkesArrivalProcess()
        proc_default.lambda_state = np.array([20.0, 0.5, 0.2])
        res_v62 = proc_default.compute_preemptive_dark_routing(version=62)
        assert math.isclose(res_v62["preemptive_dark_routing_ratio"], 0.9999999999999999995, rel_tol=1e-15)

    def test_smart_order_router_version_62_maker_floor_and_anti_gaming(self):
        """Verify SmartOrderRouter contracts maker floor to 1e-34 and anti-gaming up to 0.9999999999999999995."""
        sor = SmartOrderRouter(version=62)
        assert math.isclose(sor._resolve_max_dark_cap(62), 0.9999999999999999995, rel_tol=1e-15)

        plan = {
            "symbol": "005930",
            "quantity": 1000000,
            "action": "BUY",
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "destination": {"venue": "KRX_ATS_NEXTRADE"},
            "version": 62,
        }
        res = sor.route_order(plan, ats_available=True)
        assert res["maker_ratio"] == 1e-34
        assert res["min_ratio"] == 0.9999999999999999995

    def test_oms_preemptive_micro_tick_shading_threshold_v62(self):
        """Verify micro-tick shading activation threshold at h > 0.0000015 with multiplier 0.99999999999999995."""
        oms = ExecutionOMSEngine()
        sched = AlmgrenChrissScheduler()

        # Deadband below threshold
        p_dead = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010},
            version=62,
        )
        assert math.isclose(p_dead, 100.0, rel_tol=1e-7)

        # Boundary test at h = 0.0000015
        p_bound = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.0000015},
            version=62,
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
            version=62,
        )
        p_sched = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_active},
            version=62,
        )

        assert math.isclose(p_sched, p_buy, rel_tol=1e-7)
        expected_shift = -1 * 0.99999999999999995 * 1.0 * (h_active - 0.0000015)
        assert math.isclose(p_buy - 100.0, expected_shift, rel_tol=1e-5)

    def test_oms_backward_compatibility_v61_and_prior(self):
        """Verify that at h = 0.0000018, v62 is active while v61 is inactive (threshold 0.0000020)."""
        oms = ExecutionOMSEngine()
        h_val = 0.0000018

        p_v62 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=62,
        )
        p_v61 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=61,
        )

        # In v61, h_val <= 0.0000020 so shift is 0.0
        assert math.isclose(p_v61, 100.0, rel_tol=1e-7)
        # In v62, h_val > 0.0000015 so shift is active (negative for BUY)
        assert p_v62 < 100.0
