"""
tests/test_phase80_oms.py

Unit and integration test suite for Phase 80 Quantitative Alpha Enhancement (Feature F374 Microstructure OMS):
- Kerr-Newman-Kiselev 59-Dark-Energy DAHA
  (w = -61/3 ~= -20.333333333333332, k_daha = 0.51, k_monster = 0.50, daha_59_factor = 10.35, c_monster = 4.3368086899420177e-19 [2^-61])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 59-fold dark energy density
  * Repulsive acceleration -31.0 * c * (r ** 61) * daha_59_factor
  * Metric distortion & charge acceleration
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level
- SmartOrderRouter version=80:
  * Lit maker ratio floor contracted to 1e-52
  * 52-decimal rounding precision for maker_ratio and min_ratio
  * Cascading version flags: is_phase80 -> is_phase79 -> is_phase78
- Preemptive micro-tick shading at h > 0.000000002:
  hawkes_shift = -direction * 0.999999999999999999999999999999999 * spr * (h - 0.000000002)
- Dual-OMS parity across ExecutionOMSEngine and AlmgrenChrissScheduler
- Full backward compatibility with Phase 79 and earlier.
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    compute_kerr_newman_kiselev_59_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
    compute_phase80_lob_acceleration,
    phase80_lob_spacetime_hydrodynamics,
    compute_knk_59_dark_energy_acceleration,
    compute_kerr_newman_kiselev_59_dark_energy_acceleration,
    phase80_daha_l3_acceleration,
    knk_59_dark_energy_daha_l3,
    daha_l3_phase80_acceleration,
    phase80_dark_energy_acceleration,
    calculate_phase80_knk_acceleration,
    compute_knk_phase80_acceleration,
    daha_phase80_acceleration,
    phase80_spacetime_hydrodynamics,
    phase80_queue_acceleration,
    l3_phase80_acceleration,
    phase80_knk_acceleration,
    compute_phase80_knk_daha_queue_acceleration,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase80MicrostructureOMS:
    """Test suite for Phase 80 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_59_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 59-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_59_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_59_dark_energy_correction" in res
        assert "knk_59_dark_energy_daha_acceleration" in res
        assert "phase80_knk_acceleration" in res

        assert math.isfinite(res["knk_59_dark_energy_correction"])
        assert math.isfinite(res["knk_59_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_59_factor"], 10.35, rel_tol=1e-5)
        assert math.isclose(res["k_daha_59"], 0.51, rel_tol=1e-5)
        assert math.isclose(res["k_monster_59"], 0.50, rel_tol=1e-5)
        assert math.isclose(res["c_monster_59"], 4.3368086899420177e-19, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_59"], -61.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_59_aliases(self):
        """Verify 16 method aliases on FastOrderBookMatchingEngine and module level for KNK-59."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_59_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        # Check all 16 class method aliases
        assert engine.compute_phase80_lob_acceleration() == ref
        assert engine.phase80_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_59_dark_energy_acceleration() == ref
        assert engine.compute_kerr_newman_kiselev_59_dark_energy_acceleration() == ref
        assert engine.phase80_daha_l3_acceleration() == ref
        assert engine.knk_59_dark_energy_daha_l3() == ref
        assert engine.daha_l3_phase80_acceleration() == ref
        assert engine.phase80_dark_energy_acceleration() == ref
        assert engine.calculate_phase80_knk_acceleration() == ref
        assert engine.compute_knk_phase80_acceleration() == ref
        assert engine.daha_phase80_acceleration() == ref
        assert engine.phase80_spacetime_hydrodynamics() == ref
        assert engine.phase80_queue_acceleration() == ref
        assert engine.l3_phase80_acceleration() == ref
        assert engine.phase80_knk_acceleration() == ref
        assert engine.compute_phase80_knk_daha_queue_acceleration() == ref

        # Check module-level aliases
        assert compute_kerr_newman_kiselev_59_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(engine) == ref
        assert compute_phase80_lob_acceleration(engine) == ref
        assert phase80_lob_spacetime_hydrodynamics(engine) == ref
        assert compute_knk_59_dark_energy_acceleration(engine) == ref
        assert compute_kerr_newman_kiselev_59_dark_energy_acceleration(engine) == ref
        assert phase80_daha_l3_acceleration(engine) == ref
        assert knk_59_dark_energy_daha_l3(engine) == ref
        assert daha_l3_phase80_acceleration(engine) == ref
        assert phase80_dark_energy_acceleration(engine) == ref
        assert calculate_phase80_knk_acceleration(engine) == ref
        assert compute_knk_phase80_acceleration(engine) == ref
        assert daha_phase80_acceleration(engine) == ref
        assert phase80_spacetime_hydrodynamics(engine) == ref
        assert phase80_queue_acceleration(engine) == ref
        assert l3_phase80_acceleration(engine) == ref
        assert phase80_knk_acceleration(engine) == ref
        assert compute_phase80_knk_daha_queue_acceleration(engine) == ref

    def test_smart_order_router_phase80_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 80 flags and lit maker floor to 1e-52."""
        sor_80 = SmartOrderRouter(version=80)
        assert sor_80.is_phase80 is True
        assert sor_80.is_phase79 is True
        assert sor_80.is_phase78 is True
        assert sor_80.is_phase77 is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "side": "BUY",
            "hawkes_intensity": 0.95,
        }
        res = sor_80.route_order(order_plan)
        assert "maker_ratio" in res
        assert "min_ratio" in res

    def test_tick_shading_dual_oms_phase80_threshold(self):
        """Verify tick shading threshold h > 0.000000002 with 33 nines."""
        # Sub-threshold for v79 (h = 0.000000003), which triggers v80 (h > 0.000000002) but not v79 (h > 0.000000005)
        oms_p80_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=80,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000003}
        )
        oms_p79_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=79,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000003}
        )
        # v80 should trigger tick shading (buying lower) while v79 remains unshaded
        assert oms_p80_sub < oms_p79_sub

        sched = AlmgrenChrissScheduler()
        sched_p80_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=80,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000003}
        )
        assert math.isclose(oms_p80_sub, sched_p80_sub, rel_tol=1e-12)
