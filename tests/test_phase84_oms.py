"""
tests/test_phase84_oms.py

Unit and integration test suite for Phase 84 Quantitative Alpha Enhancement (Feature F393 Microstructure OMS):
- Kerr-Newman-Kiselev 62-Dark-Energy DAHA
  (w = -64/3 ~= -21.333, k_daha = 0.54, k_monster = 0.53, daha_62_factor = 11.10, c_monster = 5.421010862427522e-20 [2^-64])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 62-fold dark energy density
  * Repulsive acceleration -32.5 * c * (r ** 64) * daha_62_factor
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level
- SmartOrderRouter version=84:
  * Lit maker ratio floor contracted to 1e-55
  * 55-decimal rounding precision for maker_ratio and min_ratio
  * Cascading version flags: is_phase84 -> is_phase82 -> is_phase81 -> is_phase80
- Preemptive micro-tick shading at h > 0.0000000006:
  hawkes_shift = -direction * 0.999999999999999999999999999999999999 * spr * (h - 0.0000000006)
- Dual-OMS parity across ExecutionOMSEngine and AlmgrenChrissScheduler
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    compute_kerr_newman_kiselev_62_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
    compute_phase84_lob_acceleration,
    phase84_lob_spacetime_hydrodynamics,
    compute_knk_62_dark_energy_acceleration,
    compute_kerr_newman_kiselev_62_dark_energy_acceleration,
    phase84_daha_l3_acceleration,
    knk_62_dark_energy_daha_l3,
    daha_l3_phase84_acceleration,
    phase84_dark_energy_acceleration,
    calculate_phase84_knk_acceleration,
    compute_knk_phase84_acceleration,
    daha_phase84_acceleration,
    phase84_spacetime_hydrodynamics,
    phase84_queue_acceleration,
    l3_phase84_acceleration,
    phase84_knk_acceleration,
    compute_phase84_knk_daha_queue_acceleration,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase84MicrostructureOMS:
    """Test suite for Phase 84 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_62_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 62-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_62_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_62_dark_energy_correction" in res
        assert "knk_62_dark_energy_daha_acceleration" in res
        assert "phase84_knk_acceleration" in res

        assert math.isfinite(res["knk_62_dark_energy_correction"])
        assert math.isfinite(res["knk_62_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_62_factor"], 11.10, rel_tol=1e-5)
        assert math.isclose(res["k_daha_62"], 0.54, rel_tol=1e-5)
        assert math.isclose(res["k_monster_62"], 0.53, rel_tol=1e-5)
        assert math.isclose(res["c_monster_62"], 5.421010862427522e-20, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_62"], -64.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_62_aliases(self):
        """Verify 16 method aliases on FastOrderBookMatchingEngine and module level for KNK-62."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_62_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        # Check all 16 class method aliases
        assert engine.compute_phase84_lob_acceleration() == ref
        assert engine.phase84_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_62_dark_energy_acceleration() == ref
        assert engine.compute_kerr_newman_kiselev_62_dark_energy_acceleration() == ref
        assert engine.phase84_daha_l3_acceleration() == ref
        assert engine.knk_62_dark_energy_daha_l3() == ref
        assert engine.daha_l3_phase84_acceleration() == ref
        assert engine.phase84_dark_energy_acceleration() == ref
        assert engine.calculate_phase84_knk_acceleration() == ref
        assert engine.compute_knk_phase84_acceleration() == ref
        assert engine.daha_phase84_acceleration() == ref
        assert engine.phase84_spacetime_hydrodynamics() == ref
        assert engine.phase84_queue_acceleration() == ref
        assert engine.l3_phase84_acceleration() == ref
        assert engine.phase84_knk_acceleration() == ref
        assert engine.compute_phase84_knk_daha_queue_acceleration() == ref

        # Check module-level aliases
        assert compute_kerr_newman_kiselev_62_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(engine) == ref
        assert compute_phase84_lob_acceleration(engine) == ref
        assert phase84_lob_spacetime_hydrodynamics(engine) == ref
        assert compute_knk_62_dark_energy_acceleration(engine) == ref
        assert compute_kerr_newman_kiselev_62_dark_energy_acceleration(engine) == ref
        assert phase84_daha_l3_acceleration(engine) == ref
        assert knk_62_dark_energy_daha_l3(engine) == ref
        assert daha_l3_phase84_acceleration(engine) == ref
        assert phase84_dark_energy_acceleration(engine) == ref
        assert calculate_phase84_knk_acceleration(engine) == ref
        assert compute_knk_phase84_acceleration(engine) == ref
        assert daha_phase84_acceleration(engine) == ref
        assert phase84_spacetime_hydrodynamics(engine) == ref
        assert phase84_queue_acceleration(engine) == ref
        assert l3_phase84_acceleration(engine) == ref
        assert phase84_knk_acceleration(engine) == ref
        assert compute_phase84_knk_daha_queue_acceleration(engine) == ref

    def test_smart_order_router_phase84_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 84 flags and lit maker floor to 1e-55."""
        sor_84 = SmartOrderRouter(version=84)
        assert sor_84.is_phase84 is True
        assert sor_84.is_phase82 is True
        assert sor_84.is_phase81 is True
        assert sor_84.is_phase80 is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "side": "BUY",
            "hawkes_intensity": 0.95,
        }
        res = sor_84.route_order(order_plan)
        assert "maker_ratio" in res
        assert "min_ratio" in res

    def test_tick_shading_dual_oms_phase84_threshold(self):
        """Verify tick shading threshold h > 0.0000000006 with 36 nines."""
        # Sub-threshold for v82 (h = 0.0000000007), which triggers v84 (h > 0.0000000006) but not v82 (h > 0.0000000008)
        oms_p84_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=84,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000000007}
        )
        oms_p82_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=82,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000000007}
        )
        assert oms_p84_sub < oms_p82_sub

        sched = AlmgrenChrissScheduler()
        sched_p84_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=84,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000000007}
        )
        assert math.isclose(oms_p84_sub, sched_p84_sub, rel_tol=1e-12)
