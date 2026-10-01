"""
tests/test_phase91_oms.py

Unit and integration test suite for Phase 91 Quantitative Alpha Enhancement (Features F428 Microstructure OMS):
- Kerr-Newman-Kiselev 69-Dark-Energy DAHA
  (w = -71.0/3.0, k_daha = 0.61, k_monster = 0.60, daha_69_factor = 12.60, c_monster = 4.235164736271502e-22 [2^-71])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 69-fold dark energy density
  * Repulsive acceleration -36.0 * c * (r ** 71) * daha_69_factor
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level
- SmartOrderRouter version=91:
  * Lit maker ratio floor contracted to 1e-62
  * Cascading version flags: is_phase91 -> is_phase90 -> is_phase89 -> is_phase88 -> is_phase87 -> is_phase86 -> is_phase85 -> is_phase84 -> is_phase82 -> is_phase81 -> is_phase80
- Preemptive micro-tick shading at h > 0.00000000009 (tested at h = 0.00000000010):
  oms_p91_sub < oms_p90_sub
- Dual-OMS parity across ExecutionOMSEngine and AlmgrenChrissScheduler
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler

try:
    from trading_system.src.core.fast_lob_engine import (
        compute_kerr_newman_kiselev_69_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
        compute_phase91_lob_acceleration,
        phase91_lob_spacetime_hydrodynamics,
        compute_knk_69_dark_energy_acceleration,
        compute_kerr_newman_kiselev_69_dark_energy_acceleration,
        phase91_daha_l3_acceleration,
        knk_69_dark_energy_daha_l3,
        daha_l3_phase91_acceleration,
        phase91_dark_energy_acceleration,
        calculate_phase91_knk_acceleration,
        compute_knk_phase91_acceleration,
        daha_phase91_acceleration,
        phase91_spacetime_hydrodynamics,
        phase91_queue_acceleration,
        l3_phase91_acceleration,
        phase91_knk_acceleration,
        compute_phase91_knk_daha_queue_acceleration,
        compute_phase91_queue_acceleration,
        phase91_l3_queue_acceleration,
        knk_69_daha_queue_acceleration,
    )
except ImportError:
    import trading_system.src.core.fast_lob_engine as _fle

    def _missing_fle(name):
        val = getattr(_fle, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'fast_lob_engine' has no Phase 91 attribute '{name}'")
        return _callable

    compute_kerr_newman_kiselev_69_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration = _missing_fle('compute_kerr_newman_kiselev_69_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration')
    compute_phase91_lob_acceleration = _missing_fle('compute_phase91_lob_acceleration')
    phase91_lob_spacetime_hydrodynamics = _missing_fle('phase91_lob_spacetime_hydrodynamics')
    compute_knk_69_dark_energy_acceleration = _missing_fle('compute_knk_69_dark_energy_acceleration')
    compute_kerr_newman_kiselev_69_dark_energy_acceleration = _missing_fle('compute_kerr_newman_kiselev_69_dark_energy_acceleration')
    phase91_daha_l3_acceleration = _missing_fle('phase91_daha_l3_acceleration')
    knk_69_dark_energy_daha_l3 = _missing_fle('knk_69_dark_energy_daha_l3')
    daha_l3_phase91_acceleration = _missing_fle('daha_l3_phase91_acceleration')
    phase91_dark_energy_acceleration = _missing_fle('phase91_dark_energy_acceleration')
    calculate_phase91_knk_acceleration = _missing_fle('calculate_phase91_knk_acceleration')
    compute_knk_phase91_acceleration = _missing_fle('compute_knk_phase91_acceleration')
    daha_phase91_acceleration = _missing_fle('daha_phase91_acceleration')
    phase91_spacetime_hydrodynamics = _missing_fle('phase91_spacetime_hydrodynamics')
    phase91_queue_acceleration = _missing_fle('phase91_queue_acceleration')
    l3_phase91_acceleration = _missing_fle('l3_phase91_acceleration')
    phase91_knk_acceleration = _missing_fle('phase91_knk_acceleration')
    compute_phase91_knk_daha_queue_acceleration = _missing_fle('compute_phase91_knk_daha_queue_acceleration')
    compute_phase91_queue_acceleration = _missing_fle('compute_phase91_queue_acceleration')
    phase91_l3_queue_acceleration = _missing_fle('phase91_l3_queue_acceleration')
    knk_69_daha_queue_acceleration = _missing_fle('knk_69_daha_queue_acceleration')


class TestPhase91MicrostructureAndOMS:
    """Test suite for Phase 91 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_69_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 69-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_69_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        if func is None:
            raise AttributeError("'FastOrderBookMatchingEngine' object has no attribute 'compute_kerr_newman_kiselev_69_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration'")

        res = func(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_69_dark_energy_correction" in res
        assert "knk_69_dark_energy_daha_acceleration" in res
        assert "phase91_knk_acceleration" in res
        assert "phase90_knk_acceleration" in res

        assert math.isfinite(res["knk_69_dark_energy_correction"])
        assert math.isfinite(res["knk_69_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_69_factor"], 12.60, rel_tol=1e-5)
        assert math.isclose(res["k_daha_69"], 0.61, rel_tol=1e-5)
        assert math.isclose(res["k_monster_69"], 0.60, rel_tol=1e-5)
        assert math.isclose(res["c_monster_69"], 4.235164736271502e-22, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_69"], -71.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_69_aliases(self):
        """Verify 20 method aliases on FastOrderBookMatchingEngine and module level for KNK-69."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_69_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        if func is None:
            raise AttributeError("'FastOrderBookMatchingEngine' object has no attribute 'compute_kerr_newman_kiselev_69_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration'")

        ref = func()

        # Check class method aliases
        assert getattr(engine, "compute_phase91_lob_acceleration")() == ref
        assert getattr(engine, "phase91_lob_spacetime_hydrodynamics")() == ref
        assert getattr(engine, "compute_knk_69_dark_energy_acceleration")() == ref
        assert getattr(engine, "compute_kerr_newman_kiselev_69_dark_energy_acceleration")() == ref
        assert getattr(engine, "phase91_daha_l3_acceleration")() == ref
        assert getattr(engine, "knk_69_dark_energy_daha_l3")() == ref
        assert getattr(engine, "daha_l3_phase91_acceleration")() == ref
        assert getattr(engine, "phase91_dark_energy_acceleration")() == ref
        assert getattr(engine, "calculate_phase91_knk_acceleration")() == ref
        assert getattr(engine, "compute_knk_phase91_acceleration")() == ref
        assert getattr(engine, "daha_phase91_acceleration")() == ref
        assert getattr(engine, "phase91_spacetime_hydrodynamics")() == ref
        assert getattr(engine, "phase91_queue_acceleration")() == ref
        assert getattr(engine, "l3_phase91_acceleration")() == ref
        assert getattr(engine, "phase91_knk_acceleration")() == ref
        assert getattr(engine, "compute_phase91_knk_daha_queue_acceleration")() == ref
        assert getattr(engine, "compute_phase91_queue_acceleration")() == ref
        assert getattr(engine, "phase91_l3_queue_acceleration")() == ref
        assert getattr(engine, "knk_69_daha_queue_acceleration")() == ref

        # Check module-level aliases
        assert compute_kerr_newman_kiselev_69_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(engine) == ref
        assert compute_phase91_lob_acceleration(engine) == ref
        assert phase91_lob_spacetime_hydrodynamics(engine) == ref
        assert compute_knk_69_dark_energy_acceleration(engine) == ref
        assert compute_kerr_newman_kiselev_69_dark_energy_acceleration(engine) == ref
        assert phase91_daha_l3_acceleration(engine) == ref
        assert knk_69_dark_energy_daha_l3(engine) == ref
        assert daha_l3_phase91_acceleration(engine) == ref
        assert phase91_dark_energy_acceleration(engine) == ref
        assert calculate_phase91_knk_acceleration(engine) == ref
        assert compute_knk_phase91_acceleration(engine) == ref
        assert daha_phase91_acceleration(engine) == ref
        assert phase91_spacetime_hydrodynamics(engine) == ref
        assert phase91_queue_acceleration(engine) == ref
        assert l3_phase91_acceleration(engine) == ref
        assert phase91_knk_acceleration(engine) == ref
        assert compute_phase91_knk_daha_queue_acceleration(engine) == ref
        assert compute_phase91_queue_acceleration(engine) == ref
        assert phase91_l3_queue_acceleration(engine) == ref
        assert knk_69_daha_queue_acceleration(engine) == ref

    def test_smart_order_router_phase91_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 91 flags and lit maker floor to 1e-62."""
        sor_91 = SmartOrderRouter(version=91)
        assert getattr(sor_91, "is_phase91", False) is True
        assert getattr(sor_91, "is_phase90", False) is True
        assert getattr(sor_91, "is_phase89", False) is True
        assert getattr(sor_91, "is_phase88", False) is True
        assert getattr(sor_91, "is_phase87", False) is True
        assert getattr(sor_91, "is_phase86", False) is True
        assert getattr(sor_91, "is_phase85", False) is True
        assert getattr(sor_91, "is_phase84", False) is True
        assert getattr(sor_91, "is_phase82", False) is True
        assert getattr(sor_91, "is_phase81", False) is True
        assert getattr(sor_91, "is_phase80", False) is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 91,
            "target_price": 150.0,
            "hawkes_intensity": 0.95,
        }
        res = sor_91.route_order(order_plan, gamma_toxic_dir=1.0)
        assert "maker_ratio" in res
        assert "min_ratio" in res
        assert res["maker_ratio"] == 1e-62

    def test_tick_shading_dual_oms_phase91_threshold(self):
        """Verify tick shading threshold h > 0.00000000009 (tested at h = 0.00000000010)."""
        # Sub-threshold for v90 (h = 0.00000000010), which triggers v91 (h > 0.00000000009) but not v90 (h > 0.00000000010)
        oms_p91_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=91,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000010}
        )
        oms_p90_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=90,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000010}
        )
        assert oms_p91_sub < oms_p90_sub

        sched = AlmgrenChrissScheduler()
        sched_p91_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=91,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000010}
        )
        assert math.isclose(oms_p91_sub, sched_p91_sub, rel_tol=1e-12)
