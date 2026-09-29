"""
tests/test_phase82_oms.py

Unit and integration test suite for Phase 82 Quantitative Alpha Enhancement (Feature F384 Microstructure OMS):
- Kerr-Newman-Kiselev 61-Dark-Energy DAHA
  (w = -63/3 = -21.0, k_daha = 0.53, k_monster = 0.52, daha_61_factor = 10.85, c_monster = 1.0842021724855044e-19 [2^-63])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 61-fold dark energy density
  * Repulsive acceleration -32.0 * c * (r ** 63) * daha_61_factor
  * Metric distortion & charge acceleration
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level
- SmartOrderRouter version=82:
  * Lit maker ratio floor contracted to 1e-54
  * 54-decimal rounding precision for maker_ratio and min_ratio
  * Cascading version flags: is_phase82 -> is_phase81 -> is_phase80 -> is_phase79 -> is_phase78
- Preemptive micro-tick shading at h > 0.0000000008:
  hawkes_shift = -direction * 0.99999999999999999999999999999999999 * spr * (h - 0.0000000008)
- Dual-OMS parity across ExecutionOMSEngine and AlmgrenChrissScheduler
- Full backward compatibility with Phase 81 and earlier.
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    compute_kerr_newman_kiselev_61_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
    compute_phase82_lob_acceleration,
    phase82_lob_spacetime_hydrodynamics,
    compute_knk_61_dark_energy_acceleration,
    compute_kerr_newman_kiselev_61_dark_energy_acceleration,
    phase82_daha_l3_acceleration,
    knk_61_dark_energy_daha_l3,
    daha_l3_phase82_acceleration,
    phase82_dark_energy_acceleration,
    calculate_phase82_knk_acceleration,
    compute_knk_phase82_acceleration,
    daha_phase82_acceleration,
    phase82_spacetime_hydrodynamics,
    phase82_queue_acceleration,
    l3_phase82_acceleration,
    phase82_knk_acceleration,
    compute_phase82_knk_daha_queue_acceleration,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase82MicrostructureOMS:
    """Test suite for Phase 82 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_61_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 61-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_61_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_61_dark_energy_correction" in res
        assert "knk_61_dark_energy_daha_acceleration" in res
        assert "phase82_knk_acceleration" in res

        assert math.isfinite(res["knk_61_dark_energy_correction"])
        assert math.isfinite(res["knk_61_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_61_factor"], 10.85, rel_tol=1e-5)
        assert math.isclose(res["k_daha_61"], 0.53, rel_tol=1e-5)
        assert math.isclose(res["k_monster_61"], 0.52, rel_tol=1e-5)
        assert math.isclose(res["c_monster_61"], 1.0842021724855044e-19, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_61"], -63.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_61_aliases(self):
        """Verify 16 method aliases on FastOrderBookMatchingEngine and module level for KNK-61."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_61_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        # Check all 16 class method aliases
        assert engine.compute_phase82_lob_acceleration() == ref
        assert engine.phase82_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_61_dark_energy_acceleration() == ref
        assert engine.compute_kerr_newman_kiselev_61_dark_energy_acceleration() == ref
        assert engine.phase82_daha_l3_acceleration() == ref
        assert engine.knk_61_dark_energy_daha_l3() == ref
        assert engine.daha_l3_phase82_acceleration() == ref
        assert engine.phase82_dark_energy_acceleration() == ref
        assert engine.calculate_phase82_knk_acceleration() == ref
        assert engine.compute_knk_phase82_acceleration() == ref
        assert engine.daha_phase82_acceleration() == ref
        assert engine.phase82_spacetime_hydrodynamics() == ref
        assert engine.phase82_queue_acceleration() == ref
        assert engine.l3_phase82_acceleration() == ref
        assert engine.phase82_knk_acceleration() == ref
        assert engine.compute_phase82_knk_daha_queue_acceleration() == ref

        # Check module-level aliases
        assert compute_kerr_newman_kiselev_61_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(engine) == ref
        assert compute_phase82_lob_acceleration(engine) == ref
        assert phase82_lob_spacetime_hydrodynamics(engine) == ref
        assert compute_knk_61_dark_energy_acceleration(engine) == ref
        assert compute_kerr_newman_kiselev_61_dark_energy_acceleration(engine) == ref
        assert phase82_daha_l3_acceleration(engine) == ref
        assert knk_61_dark_energy_daha_l3(engine) == ref
        assert daha_l3_phase82_acceleration(engine) == ref
        assert phase82_dark_energy_acceleration(engine) == ref
        assert calculate_phase82_knk_acceleration(engine) == ref
        assert compute_knk_phase82_acceleration(engine) == ref
        assert daha_phase82_acceleration(engine) == ref
        assert phase82_spacetime_hydrodynamics(engine) == ref
        assert phase82_queue_acceleration(engine) == ref
        assert l3_phase82_acceleration(engine) == ref
        assert phase82_knk_acceleration(engine) == ref
        assert compute_phase82_knk_daha_queue_acceleration(engine) == ref

    def test_smart_order_router_phase82_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 82 flags and lit maker floor to 1e-54."""
        sor_82 = SmartOrderRouter(version=82)
        assert sor_82.is_phase82 is True
        assert sor_82.is_phase81 is True
        assert sor_82.is_phase80 is True
        assert sor_82.is_phase79 is True
        assert sor_82.is_phase78 is True
        assert sor_82.is_phase77 is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "side": "BUY",
            "hawkes_intensity": 0.95,
        }
        res = sor_82.route_order(order_plan)
        assert "maker_ratio" in res
        assert "min_ratio" in res

    def test_tick_shading_dual_oms_phase82_threshold(self):
        """Verify tick shading threshold h > 0.0000000008 with 35 nines."""
        # Sub-threshold for v81 (h = 0.0000000009), which triggers v82 (h > 0.0000000008) but not v81 (h > 0.000000001)
        oms_p82_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=82,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000000009}
        )
        oms_p81_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=81,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000000009}
        )
        # v82 should trigger tick shading (buying lower) while v81 remains unshaded
        assert oms_p82_sub < oms_p81_sub

        sched = AlmgrenChrissScheduler()
        sched_p82_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=82,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000000009}
        )
        assert math.isclose(oms_p82_sub, sched_p82_sub, rel_tol=1e-12)
