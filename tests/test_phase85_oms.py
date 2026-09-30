"""
tests/test_phase85_oms.py

Unit and integration test suite for Phase 85 Quantitative Alpha Enhancement (Feature F398 Microstructure OMS):
- Kerr-Newman-Kiselev 63-Dark-Energy DAHA
  (w = -65/3 ~= -21.667, k_daha = 0.55, k_monster = 0.54, daha_63_factor = 11.20, c_monster = 2.710505431213761e-20 [2^-65])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 63-fold dark energy density
  * Repulsive acceleration -33.0 * c * (r ** 65) * daha_63_factor
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level
- SmartOrderRouter version=85:
  * Lit maker ratio floor contracted to 1e-56
  * 56-decimal rounding precision for maker_ratio and min_ratio
  * Cascading version flags: is_phase85 -> is_phase84 -> is_phase82 -> is_phase81 -> is_phase80
- Preemptive micro-tick shading at h > 0.0000000005:
  hawkes_shift = -direction * 0.9999999999999999999999999999999999999 * spr * (h - 0.0000000005)
- Dual-OMS parity across ExecutionOMSEngine and AlmgrenChrissScheduler
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    compute_kerr_newman_kiselev_63_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
    compute_phase85_lob_acceleration,
    phase85_lob_spacetime_hydrodynamics,
    compute_knk_63_dark_energy_acceleration,
    compute_kerr_newman_kiselev_63_dark_energy_acceleration,
    phase85_daha_l3_acceleration,
    knk_63_dark_energy_daha_l3,
    daha_l3_phase85_acceleration,
    phase85_dark_energy_acceleration,
    calculate_phase85_knk_acceleration,
    compute_knk_phase85_acceleration,
    daha_phase85_acceleration,
    phase85_spacetime_hydrodynamics,
    phase85_queue_acceleration,
    l3_phase85_acceleration,
    phase85_knk_acceleration,
    compute_phase85_knk_daha_queue_acceleration,
    compute_phase85_queue_acceleration,
    phase85_l3_queue_acceleration,
    knk_63_daha_queue_acceleration,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase85MicrostructureOMS:
    """Test suite for Phase 85 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_63_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 63-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_63_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_63_dark_energy_correction" in res
        assert "knk_63_dark_energy_daha_acceleration" in res
        assert "phase85_knk_acceleration" in res

        assert math.isfinite(res["knk_63_dark_energy_correction"])
        assert math.isfinite(res["knk_63_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_63_factor"], 11.20, rel_tol=1e-5)
        assert math.isclose(res["k_daha_63"], 0.55, rel_tol=1e-5)
        assert math.isclose(res["k_monster_63"], 0.54, rel_tol=1e-5)
        assert math.isclose(res["c_monster_63"], 2.710505431213761e-20, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_63"], -65.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_63_aliases(self):
        """Verify 20 method aliases on FastOrderBookMatchingEngine and module level for KNK-63."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_63_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        # Check class method aliases
        assert engine.compute_phase85_lob_acceleration() == ref
        assert engine.phase85_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_63_dark_energy_acceleration() == ref
        assert engine.compute_kerr_newman_kiselev_63_dark_energy_acceleration() == ref
        assert engine.phase85_daha_l3_acceleration() == ref
        assert engine.knk_63_dark_energy_daha_l3() == ref
        assert engine.daha_l3_phase85_acceleration() == ref
        assert engine.phase85_dark_energy_acceleration() == ref
        assert engine.calculate_phase85_knk_acceleration() == ref
        assert engine.compute_knk_phase85_acceleration() == ref
        assert engine.daha_phase85_acceleration() == ref
        assert engine.phase85_spacetime_hydrodynamics() == ref
        assert engine.phase85_queue_acceleration() == ref
        assert engine.l3_phase85_acceleration() == ref
        assert engine.phase85_knk_acceleration() == ref
        assert engine.compute_phase85_knk_daha_queue_acceleration() == ref
        assert engine.compute_phase85_queue_acceleration() == ref
        assert engine.phase85_l3_queue_acceleration() == ref
        assert engine.knk_63_daha_queue_acceleration() == ref

        # Check module-level aliases
        assert compute_kerr_newman_kiselev_63_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(engine) == ref
        assert compute_phase85_lob_acceleration(engine) == ref
        assert phase85_lob_spacetime_hydrodynamics(engine) == ref
        assert compute_knk_63_dark_energy_acceleration(engine) == ref
        assert compute_kerr_newman_kiselev_63_dark_energy_acceleration(engine) == ref
        assert phase85_daha_l3_acceleration(engine) == ref
        assert knk_63_dark_energy_daha_l3(engine) == ref
        assert daha_l3_phase85_acceleration(engine) == ref
        assert phase85_dark_energy_acceleration(engine) == ref
        assert calculate_phase85_knk_acceleration(engine) == ref
        assert compute_knk_phase85_acceleration(engine) == ref
        assert daha_phase85_acceleration(engine) == ref
        assert phase85_spacetime_hydrodynamics(engine) == ref
        assert phase85_queue_acceleration(engine) == ref
        assert l3_phase85_acceleration(engine) == ref
        assert phase85_knk_acceleration(engine) == ref
        assert compute_phase85_knk_daha_queue_acceleration(engine) == ref
        assert compute_phase85_queue_acceleration(engine) == ref
        assert phase85_l3_queue_acceleration(engine) == ref
        assert knk_63_daha_queue_acceleration(engine) == ref

    def test_smart_order_router_phase85_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 85 flags and lit maker floor to 1e-56."""
        sor_85 = SmartOrderRouter(version=85)
        assert sor_85.is_phase85 is True
        assert sor_85.is_phase84 is True
        assert sor_85.is_phase82 is True
        assert sor_85.is_phase81 is True
        assert sor_85.is_phase80 is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 85,
            "target_price": 150.0,
            "hawkes_intensity": 0.95,
        }
        res = sor_85.route_order(order_plan, gamma_toxic_dir=1.0)
        assert "maker_ratio" in res
        assert "min_ratio" in res
        assert res["maker_ratio"] == 1e-56

    def test_tick_shading_dual_oms_phase85_threshold(self):
        """Verify tick shading threshold h > 0.0000000005 with 37 nines."""
        # Sub-threshold for v84 (h = 0.00000000055), which triggers v85 (h > 0.0000000005) but not v84 (h > 0.0000000006)
        oms_p85_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=85,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000055}
        )
        oms_p84_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=84,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000055}
        )
        assert oms_p85_sub < oms_p84_sub

        sched = AlmgrenChrissScheduler()
        sched_p85_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=85,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000055}
        )
        assert math.isclose(oms_p85_sub, sched_p85_sub, rel_tol=1e-12)
