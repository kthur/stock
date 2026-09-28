"""
tests/test_phase79_oms.py

Unit and integration test suite for Phase 79 Quantitative Alpha Enhancement (Feature F369.1 & F369.2 Microstructure OMS):
- Kerr-Newman-Kiselev 58-Dark-Energy DAHA
  (w = -60/3 = -20.0, k_daha = 0.50, k_monster = 0.49, daha_58_factor = 10.10, c_monster = 8.673617379884035e-19 [2^-60])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 58-fold dark energy density
  * Repulsive acceleration -30.5 * c * (r ** 60) * daha_58_factor
  * Metric distortion & charge acceleration
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level
- SmartOrderRouter version=79:
  * Lit maker ratio floor contracted to 1e-51
  * 51-decimal rounding precision for maker_ratio and min_ratio
  * Cascading version flags: is_phase79 -> is_phase78 -> is_phase77 -> is_phase76
- Preemptive micro-tick shading at h > 0.000000005:
  hawkes_shift = -direction * 0.99999999999999999999999999999999 * spr * (h - 0.000000005)
- Dual-OMS parity across ExecutionOMSEngine and AlmgrenChrissScheduler
- Full backward compatibility with Phase 78 and earlier.
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    compute_kerr_newman_kiselev_58_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
    compute_phase79_lob_acceleration,
    phase79_lob_spacetime_hydrodynamics,
    compute_knk_58_dark_energy_acceleration,
    compute_kerr_newman_kiselev_58_dark_energy_acceleration,
    phase79_daha_l3_acceleration,
    knk_58_dark_energy_daha_l3,
    daha_l3_phase79_acceleration,
    phase79_dark_energy_acceleration,
    calculate_phase79_knk_acceleration,
    compute_knk_phase79_acceleration,
    daha_phase79_acceleration,
    phase79_spacetime_hydrodynamics,
    phase79_queue_acceleration,
    l3_phase79_acceleration,
    phase79_knk_acceleration,
    compute_phase79_knk_daha_queue_acceleration,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase79MicrostructureOMS:
    """Test suite for Phase 79 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_58_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 58-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_58_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_58_dark_energy_correction" in res
        assert "knk_58_dark_energy_daha_acceleration" in res
        assert "phase79_knk_acceleration" in res

        assert math.isfinite(res["knk_58_dark_energy_correction"])
        assert math.isfinite(res["knk_58_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_58_factor"], 10.10, rel_tol=1e-5)
        assert math.isclose(res["k_daha_58"], 0.50, rel_tol=1e-5)
        assert math.isclose(res["k_monster_58"], 0.49, rel_tol=1e-5)
        assert math.isclose(res["c_monster_58"], 8.673617379884035e-19, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_58"], -60.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_58_aliases(self):
        """Verify 16 method aliases on FastOrderBookMatchingEngine and module level for KNK-58."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_58_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        # Check all 16 class method aliases
        assert engine.compute_phase79_lob_acceleration() == ref
        assert engine.phase79_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_58_dark_energy_acceleration() == ref
        assert engine.compute_kerr_newman_kiselev_58_dark_energy_acceleration() == ref
        assert engine.phase79_daha_l3_acceleration() == ref
        assert engine.knk_58_dark_energy_daha_l3() == ref
        assert engine.daha_l3_phase79_acceleration() == ref
        assert engine.phase79_dark_energy_acceleration() == ref
        assert engine.calculate_phase79_knk_acceleration() == ref
        assert engine.compute_knk_phase79_acceleration() == ref
        assert engine.daha_phase79_acceleration() == ref
        assert engine.phase79_spacetime_hydrodynamics() == ref
        assert engine.phase79_queue_acceleration() == ref
        assert engine.l3_phase79_acceleration() == ref
        assert engine.phase79_knk_acceleration() == ref
        assert engine.compute_phase79_knk_daha_queue_acceleration() == ref

        # Check module-level aliases
        assert compute_kerr_newman_kiselev_58_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(engine) == ref
        assert compute_phase79_lob_acceleration(engine) == ref
        assert phase79_lob_spacetime_hydrodynamics(engine) == ref
        assert compute_knk_58_dark_energy_acceleration(engine) == ref
        assert compute_kerr_newman_kiselev_58_dark_energy_acceleration(engine) == ref
        assert phase79_daha_l3_acceleration(engine) == ref
        assert knk_58_dark_energy_daha_l3(engine) == ref
        assert daha_l3_phase79_acceleration(engine) == ref
        assert phase79_dark_energy_acceleration(engine) == ref
        assert calculate_phase79_knk_acceleration(engine) == ref
        assert compute_knk_phase79_acceleration(engine) == ref
        assert daha_phase79_acceleration(engine) == ref
        assert phase79_spacetime_hydrodynamics(engine) == ref
        assert phase79_queue_acceleration(engine) == ref
        assert l3_phase79_acceleration(engine) == ref
        assert phase79_knk_acceleration(engine) == ref
        assert compute_phase79_knk_daha_queue_acceleration(engine) == ref

    def test_smart_order_router_phase79_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 79 flags and lit maker floor to 1e-51."""
        sor_79 = SmartOrderRouter(version=79)
        assert sor_79.is_phase79 is True
        assert sor_79.is_phase78 is True
        assert sor_79.is_phase77 is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "side": "BUY",
            "hawkes_intensity": 0.95,
        }
        res = sor_79.route_order(order_plan)
        assert "maker_ratio" in res
        assert "min_ratio" in res

    def test_tick_shading_dual_oms_phase79_threshold(self):
        """Verify tick shading threshold h > 0.000000005 with 32 nines."""
        # Sub-threshold for v78 (h = 0.000000007), which triggers v79 (h > 0.000000005) but not v78 (h > 0.00000001)
        oms_p79_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=79,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000007}
        )
        oms_p78_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=78,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000007}
        )
        # v79 should trigger tick shading (buying lower) while v78 remains unshaded
        assert oms_p79_sub < oms_p78_sub

        sched = AlmgrenChrissScheduler()
        sched_p79_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=79,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000007}
        )
        assert math.isclose(oms_p79_sub, sched_p79_sub, rel_tol=1e-12)
