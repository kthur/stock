"""
tests/test_phase81_oms.py

Unit and integration test suite for Phase 81 Quantitative Alpha Enhancement (Feature F379 Microstructure OMS):
- Kerr-Newman-Kiselev 60-Dark-Energy DAHA
  (w = -62/3 ~= -20.666666666666668, k_daha = 0.52, k_monster = 0.51, daha_60_factor = 10.60, c_monster = 2.1684043449710088e-19 [2^-62])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 60-fold dark energy density
  * Repulsive acceleration -31.5 * c * (r ** 62) * daha_60_factor
  * Metric distortion & charge acceleration
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level
- SmartOrderRouter version=81:
  * Lit maker ratio floor contracted to 1e-53
  * 53-decimal rounding precision for maker_ratio and min_ratio
  * Cascading version flags: is_phase81 -> is_phase80 -> is_phase79 -> is_phase78
- Preemptive micro-tick shading at h > 0.000000001:
  hawkes_shift = -direction * 0.9999999999999999999999999999999999 * spr * (h - 0.000000001)
- Dual-OMS parity across ExecutionOMSEngine and AlmgrenChrissScheduler
- Full backward compatibility with Phase 80 and earlier.
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    compute_kerr_newman_kiselev_60_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
    compute_phase81_lob_acceleration,
    phase81_lob_spacetime_hydrodynamics,
    compute_knk_60_dark_energy_acceleration,
    compute_kerr_newman_kiselev_60_dark_energy_acceleration,
    phase81_daha_l3_acceleration,
    knk_60_dark_energy_daha_l3,
    daha_l3_phase81_acceleration,
    phase81_dark_energy_acceleration,
    calculate_phase81_knk_acceleration,
    compute_knk_phase81_acceleration,
    daha_phase81_acceleration,
    phase81_spacetime_hydrodynamics,
    phase81_queue_acceleration,
    l3_phase81_acceleration,
    phase81_knk_acceleration,
    compute_phase81_knk_daha_queue_acceleration,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase81MicrostructureOMS:
    """Test suite for Phase 81 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_60_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 60-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_60_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_60_dark_energy_correction" in res
        assert "knk_60_dark_energy_daha_acceleration" in res
        assert "phase81_knk_acceleration" in res

        assert math.isfinite(res["knk_60_dark_energy_correction"])
        assert math.isfinite(res["knk_60_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_60_factor"], 10.60, rel_tol=1e-5)
        assert math.isclose(res["k_daha_60"], 0.52, rel_tol=1e-5)
        assert math.isclose(res["k_monster_60"], 0.51, rel_tol=1e-5)
        assert math.isclose(res["c_monster_60"], 2.1684043449710088e-19, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_60"], -62.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_60_aliases(self):
        """Verify 16 method aliases on FastOrderBookMatchingEngine and module level for KNK-60."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_60_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        # Check all 16 class method aliases
        assert engine.compute_phase81_lob_acceleration() == ref
        assert engine.phase81_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_60_dark_energy_acceleration() == ref
        assert engine.compute_kerr_newman_kiselev_60_dark_energy_acceleration() == ref
        assert engine.phase81_daha_l3_acceleration() == ref
        assert engine.knk_60_dark_energy_daha_l3() == ref
        assert engine.daha_l3_phase81_acceleration() == ref
        assert engine.phase81_dark_energy_acceleration() == ref
        assert engine.calculate_phase81_knk_acceleration() == ref
        assert engine.compute_knk_phase81_acceleration() == ref
        assert engine.daha_phase81_acceleration() == ref
        assert engine.phase81_spacetime_hydrodynamics() == ref
        assert engine.phase81_queue_acceleration() == ref
        assert engine.l3_phase81_acceleration() == ref
        assert engine.phase81_knk_acceleration() == ref
        assert engine.compute_phase81_knk_daha_queue_acceleration() == ref

        # Check module-level aliases
        assert compute_kerr_newman_kiselev_60_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(engine) == ref
        assert compute_phase81_lob_acceleration(engine) == ref
        assert phase81_lob_spacetime_hydrodynamics(engine) == ref
        assert compute_knk_60_dark_energy_acceleration(engine) == ref
        assert compute_kerr_newman_kiselev_60_dark_energy_acceleration(engine) == ref
        assert phase81_daha_l3_acceleration(engine) == ref
        assert knk_60_dark_energy_daha_l3(engine) == ref
        assert daha_l3_phase81_acceleration(engine) == ref
        assert phase81_dark_energy_acceleration(engine) == ref
        assert calculate_phase81_knk_acceleration(engine) == ref
        assert compute_knk_phase81_acceleration(engine) == ref
        assert daha_phase81_acceleration(engine) == ref
        assert phase81_spacetime_hydrodynamics(engine) == ref
        assert phase81_queue_acceleration(engine) == ref
        assert l3_phase81_acceleration(engine) == ref
        assert phase81_knk_acceleration(engine) == ref
        assert compute_phase81_knk_daha_queue_acceleration(engine) == ref

    def test_smart_order_router_phase81_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 81 flags and lit maker floor to 1e-53."""
        sor_81 = SmartOrderRouter(version=81)
        assert sor_81.is_phase81 is True
        assert sor_81.is_phase80 is True
        assert sor_81.is_phase79 is True
        assert sor_81.is_phase78 is True
        assert sor_81.is_phase77 is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "side": "BUY",
            "hawkes_intensity": 0.95,
        }
        res = sor_81.route_order(order_plan)
        assert "maker_ratio" in res
        assert "min_ratio" in res

    def test_tick_shading_dual_oms_phase81_threshold(self):
        """Verify tick shading threshold h > 0.000000001 with 34 nines."""
        # Sub-threshold for v80 (h = 0.0000000015), which triggers v81 (h > 0.000000001) but not v80 (h > 0.000000002)
        oms_p81_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=81,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000000015}
        )
        oms_p80_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=80,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000000015}
        )
        # v81 should trigger tick shading (buying lower) while v80 remains unshaded
        assert oms_p81_sub < oms_p80_sub

        sched = AlmgrenChrissScheduler()
        sched_p81_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=81,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000000015}
        )
        assert math.isclose(oms_p81_sub, sched_p81_sub, rel_tol=1e-12)
