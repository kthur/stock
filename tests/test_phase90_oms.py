"""
tests/test_phase90_oms.py

Unit and integration test suite for Phase 90 Quantitative Alpha Enhancement (Features F423, F424 Microstructure OMS):
- Kerr-Newman-Kiselev 68-Dark-Energy DAHA
  (w = -70.0/3.0, k_daha = 0.60, k_monster = 0.59, daha_68_factor = 12.30, c_monster = 8.470329472543003e-22 [2^-70])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 68-fold dark energy density
  * Repulsive acceleration -35.0 * c * (r ** 70) * daha_68_factor
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level
- SmartOrderRouter version=90:
  * Lit maker ratio floor contracted to 1e-61
  * Cascading version flags: is_phase90 -> is_phase89 -> is_phase88 -> is_phase87 -> is_phase86 -> is_phase85 -> is_phase84 -> is_phase82 -> is_phase81 -> is_phase80
- Preemptive micro-tick shading at h > 0.00000000010 (tested at h = 0.00000000015):
  oms_p90_sub < oms_p89_sub
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
        compute_kerr_newman_kiselev_68_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
        compute_phase90_lob_acceleration,
        phase90_lob_spacetime_hydrodynamics,
        compute_knk_68_dark_energy_acceleration,
        compute_kerr_newman_kiselev_68_dark_energy_acceleration,
        phase90_daha_l3_acceleration,
        knk_68_dark_energy_daha_l3,
        daha_l3_phase90_acceleration,
        phase90_dark_energy_acceleration,
        calculate_phase90_knk_acceleration,
        compute_knk_phase90_acceleration,
        daha_phase90_acceleration,
        phase90_spacetime_hydrodynamics,
        phase90_queue_acceleration,
        l3_phase90_acceleration,
        phase90_knk_acceleration,
        compute_phase90_knk_daha_queue_acceleration,
        compute_phase90_queue_acceleration,
        phase90_l3_queue_acceleration,
        knk_68_daha_queue_acceleration,
    )
except ImportError:
    import trading_system.src.core.fast_lob_engine as _fle

    def _missing_fle(name):
        val = getattr(_fle, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'fast_lob_engine' has no Phase 90 attribute '{name}'")
        return _callable

    compute_kerr_newman_kiselev_68_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration = _missing_fle('compute_kerr_newman_kiselev_68_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration')
    compute_phase90_lob_acceleration = _missing_fle('compute_phase90_lob_acceleration')
    phase90_lob_spacetime_hydrodynamics = _missing_fle('phase90_lob_spacetime_hydrodynamics')
    compute_knk_68_dark_energy_acceleration = _missing_fle('compute_knk_68_dark_energy_acceleration')
    compute_kerr_newman_kiselev_68_dark_energy_acceleration = _missing_fle('compute_kerr_newman_kiselev_68_dark_energy_acceleration')
    phase90_daha_l3_acceleration = _missing_fle('phase90_daha_l3_acceleration')
    knk_68_dark_energy_daha_l3 = _missing_fle('knk_68_dark_energy_daha_l3')
    daha_l3_phase90_acceleration = _missing_fle('daha_l3_phase90_acceleration')
    phase90_dark_energy_acceleration = _missing_fle('phase90_dark_energy_acceleration')
    calculate_phase90_knk_acceleration = _missing_fle('calculate_phase90_knk_acceleration')
    compute_knk_phase90_acceleration = _missing_fle('compute_knk_phase90_acceleration')
    daha_phase90_acceleration = _missing_fle('daha_phase90_acceleration')
    phase90_spacetime_hydrodynamics = _missing_fle('phase90_spacetime_hydrodynamics')
    phase90_queue_acceleration = _missing_fle('phase90_queue_acceleration')
    l3_phase90_acceleration = _missing_fle('l3_phase90_acceleration')
    phase90_knk_acceleration = _missing_fle('phase90_knk_acceleration')
    compute_phase90_knk_daha_queue_acceleration = _missing_fle('compute_phase90_knk_daha_queue_acceleration')
    compute_phase90_queue_acceleration = _missing_fle('compute_phase90_queue_acceleration')
    phase90_l3_queue_acceleration = _missing_fle('phase90_l3_queue_acceleration')
    knk_68_daha_queue_acceleration = _missing_fle('knk_68_daha_queue_acceleration')


class TestPhase90MicrostructureAndOMS:
    """Test suite for Phase 90 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_68_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 68-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_68_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        if func is None:
            raise AttributeError("'FastOrderBookMatchingEngine' object has no attribute 'compute_kerr_newman_kiselev_68_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration'")

        res = func(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_68_dark_energy_correction" in res
        assert "knk_68_dark_energy_daha_acceleration" in res
        assert "phase90_knk_acceleration" in res
        assert "phase89_knk_acceleration" in res

        assert math.isfinite(res["knk_68_dark_energy_correction"])
        assert math.isfinite(res["knk_68_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_68_factor"], 12.30, rel_tol=1e-5)
        assert math.isclose(res["k_daha_68"], 0.60, rel_tol=1e-5)
        assert math.isclose(res["k_monster_68"], 0.59, rel_tol=1e-5)
        assert math.isclose(res["c_monster_68"], 8.470329472543003e-22, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_68"], -70.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_68_aliases(self):
        """Verify 20 method aliases on FastOrderBookMatchingEngine and module level for KNK-68."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_68_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        if func is None:
            raise AttributeError("'FastOrderBookMatchingEngine' object has no attribute 'compute_kerr_newman_kiselev_68_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration'")

        ref = func()

        # Check class method aliases
        assert getattr(engine, "compute_phase90_lob_acceleration")() == ref
        assert getattr(engine, "phase90_lob_spacetime_hydrodynamics")() == ref
        assert getattr(engine, "compute_knk_68_dark_energy_acceleration")() == ref
        assert getattr(engine, "compute_kerr_newman_kiselev_68_dark_energy_acceleration")() == ref
        assert getattr(engine, "phase90_daha_l3_acceleration")() == ref
        assert getattr(engine, "knk_68_dark_energy_daha_l3")() == ref
        assert getattr(engine, "daha_l3_phase90_acceleration")() == ref
        assert getattr(engine, "phase90_dark_energy_acceleration")() == ref
        assert getattr(engine, "calculate_phase90_knk_acceleration")() == ref
        assert getattr(engine, "compute_knk_phase90_acceleration")() == ref
        assert getattr(engine, "daha_phase90_acceleration")() == ref
        assert getattr(engine, "phase90_spacetime_hydrodynamics")() == ref
        assert getattr(engine, "phase90_queue_acceleration")() == ref
        assert getattr(engine, "l3_phase90_acceleration")() == ref
        assert getattr(engine, "phase90_knk_acceleration")() == ref
        assert getattr(engine, "compute_phase90_knk_daha_queue_acceleration")() == ref
        assert getattr(engine, "compute_phase90_queue_acceleration")() == ref
        assert getattr(engine, "phase90_l3_queue_acceleration")() == ref
        assert getattr(engine, "knk_68_daha_queue_acceleration")() == ref

        # Check module-level aliases
        assert compute_kerr_newman_kiselev_68_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(engine) == ref
        assert compute_phase90_lob_acceleration(engine) == ref
        assert phase90_lob_spacetime_hydrodynamics(engine) == ref
        assert compute_knk_68_dark_energy_acceleration(engine) == ref
        assert compute_kerr_newman_kiselev_68_dark_energy_acceleration(engine) == ref
        assert phase90_daha_l3_acceleration(engine) == ref
        assert knk_68_dark_energy_daha_l3(engine) == ref
        assert daha_l3_phase90_acceleration(engine) == ref
        assert phase90_dark_energy_acceleration(engine) == ref
        assert calculate_phase90_knk_acceleration(engine) == ref
        assert compute_knk_phase90_acceleration(engine) == ref
        assert daha_phase90_acceleration(engine) == ref
        assert phase90_spacetime_hydrodynamics(engine) == ref
        assert phase90_queue_acceleration(engine) == ref
        assert l3_phase90_acceleration(engine) == ref
        assert phase90_knk_acceleration(engine) == ref
        assert compute_phase90_knk_daha_queue_acceleration(engine) == ref
        assert compute_phase90_queue_acceleration(engine) == ref
        assert phase90_l3_queue_acceleration(engine) == ref
        assert knk_68_daha_queue_acceleration(engine) == ref

    def test_smart_order_router_phase90_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 90 flags and lit maker floor to 1e-61."""
        sor_90 = SmartOrderRouter(version=90)
        assert getattr(sor_90, "is_phase90", False) is True
        assert getattr(sor_90, "is_phase89", False) is True
        assert getattr(sor_90, "is_phase88", False) is True
        assert getattr(sor_90, "is_phase87", False) is True
        assert getattr(sor_90, "is_phase86", False) is True
        assert getattr(sor_90, "is_phase85", False) is True
        assert getattr(sor_90, "is_phase84", False) is True
        assert getattr(sor_90, "is_phase82", False) is True
        assert getattr(sor_90, "is_phase81", False) is True
        assert getattr(sor_90, "is_phase80", False) is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 90,
            "target_price": 150.0,
            "hawkes_intensity": 0.95,
        }
        res = sor_90.route_order(order_plan, gamma_toxic_dir=1.0)
        assert "maker_ratio" in res
        assert "min_ratio" in res
        assert res["maker_ratio"] == 1e-61

    def test_tick_shading_dual_oms_phase90_threshold(self):
        """Verify tick shading threshold h > 0.00000000010 (tested at h = 0.00000000015)."""
        # Sub-threshold for v89 (h = 0.00000000015), which triggers v90 (h > 0.00000000010) but not v89 (h > 0.00000000015)
        oms_p90_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=90,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000015}
        )
        oms_p89_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=89,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000015}
        )
        assert oms_p90_sub < oms_p89_sub

        sched = AlmgrenChrissScheduler()
        sched_p90_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=90,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000015}
        )
        assert math.isclose(oms_p90_sub, sched_p90_sub, rel_tol=1e-12)
