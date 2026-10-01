"""
tests/test_phase89_oms.py

Unit and integration test suite for Phase 89 Quantitative Alpha Enhancement (Feature F418 Microstructure OMS):
- Kerr-Newman-Kiselev 67-Dark-Energy DAHA
  (w = -69.0/3.0 = -23.0, k_daha = 0.59, k_monster = 0.58, daha_67_factor = 12.05, c_monster = 1.6940658945086007e-21 [2^-69])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 67-fold dark energy density
  * Repulsive acceleration -35.0 * c * (r ** 69) * daha_67_factor
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level
- SmartOrderRouter version=89:
  * Lit maker ratio floor contracted to 1e-60
  * 60-decimal rounding precision for maker_ratio and min_ratio
  * Cascading version flags: is_phase89 -> is_phase88 -> is_phase87 -> is_phase86 -> is_phase85 -> is_phase84 -> is_phase82 -> is_phase81 -> is_phase80
- Preemptive micro-tick shading at h > 0.00000000015:
  hawkes_shift = -direction * 0.99999999999999999999999999999999999999999 * spr * (h - 0.00000000015)
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
        compute_kerr_newman_kiselev_67_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
        compute_phase89_lob_acceleration,
        phase89_lob_spacetime_hydrodynamics,
        compute_knk_67_dark_energy_acceleration,
        compute_kerr_newman_kiselev_67_dark_energy_acceleration,
        phase89_daha_l3_acceleration,
        knk_67_dark_energy_daha_l3,
        daha_l3_phase89_acceleration,
        phase89_dark_energy_acceleration,
        calculate_phase89_knk_acceleration,
        compute_knk_phase89_acceleration,
        daha_phase89_acceleration,
        phase89_spacetime_hydrodynamics,
        phase89_queue_acceleration,
        l3_phase89_acceleration,
        phase89_knk_acceleration,
        compute_phase89_knk_daha_queue_acceleration,
        compute_phase89_queue_acceleration,
        phase89_l3_queue_acceleration,
        knk_67_daha_queue_acceleration,
    )
except ImportError:
    import trading_system.src.core.fast_lob_engine as _fle

    def _missing_fle(name):
        val = getattr(_fle, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'fast_lob_engine' has no Phase 89 attribute '{name}'")
        return _callable

    compute_kerr_newman_kiselev_67_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration = _missing_fle('compute_kerr_newman_kiselev_67_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration')
    compute_phase89_lob_acceleration = _missing_fle('compute_phase89_lob_acceleration')
    phase89_lob_spacetime_hydrodynamics = _missing_fle('phase89_lob_spacetime_hydrodynamics')
    compute_knk_67_dark_energy_acceleration = _missing_fle('compute_knk_67_dark_energy_acceleration')
    compute_kerr_newman_kiselev_67_dark_energy_acceleration = _missing_fle('compute_kerr_newman_kiselev_67_dark_energy_acceleration')
    phase89_daha_l3_acceleration = _missing_fle('phase89_daha_l3_acceleration')
    knk_67_dark_energy_daha_l3 = _missing_fle('knk_67_dark_energy_daha_l3')
    daha_l3_phase89_acceleration = _missing_fle('daha_l3_phase89_acceleration')
    phase89_dark_energy_acceleration = _missing_fle('phase89_dark_energy_acceleration')
    calculate_phase89_knk_acceleration = _missing_fle('calculate_phase89_knk_acceleration')
    compute_knk_phase89_acceleration = _missing_fle('compute_knk_phase89_acceleration')
    daha_phase89_acceleration = _missing_fle('daha_phase89_acceleration')
    phase89_spacetime_hydrodynamics = _missing_fle('phase89_spacetime_hydrodynamics')
    phase89_queue_acceleration = _missing_fle('phase89_queue_acceleration')
    l3_phase89_acceleration = _missing_fle('l3_phase89_acceleration')
    phase89_knk_acceleration = _missing_fle('phase89_knk_acceleration')
    compute_phase89_knk_daha_queue_acceleration = _missing_fle('compute_phase89_knk_daha_queue_acceleration')
    compute_phase89_queue_acceleration = _missing_fle('compute_phase89_queue_acceleration')
    phase89_l3_queue_acceleration = _missing_fle('phase89_l3_queue_acceleration')
    knk_67_daha_queue_acceleration = _missing_fle('knk_67_daha_queue_acceleration')


class TestPhase89MicrostructureAndOMS:
    """Test suite for Phase 89 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_67_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 67-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_67_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        if func is None:
            raise AttributeError("'FastOrderBookMatchingEngine' object has no attribute 'compute_kerr_newman_kiselev_67_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration'")

        res = func(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_67_dark_energy_correction" in res
        assert "knk_67_dark_energy_daha_acceleration" in res
        assert "phase89_knk_acceleration" in res
        assert "phase88_knk_acceleration" in res

        assert math.isfinite(res["knk_67_dark_energy_correction"])
        assert math.isfinite(res["knk_67_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_67_factor"], 12.05, rel_tol=1e-5)
        assert math.isclose(res["k_daha_67"], 0.59, rel_tol=1e-5)
        assert math.isclose(res["k_monster_67"], 0.58, rel_tol=1e-5)
        assert math.isclose(res["c_monster_67"], 1.6940658945086007e-21, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_67"], -69.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_67_aliases(self):
        """Verify 20 method aliases on FastOrderBookMatchingEngine and module level for KNK-67."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_67_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        if func is None:
            raise AttributeError("'FastOrderBookMatchingEngine' object has no attribute 'compute_kerr_newman_kiselev_67_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration'")

        ref = func()

        # Check class method aliases
        assert getattr(engine, "compute_phase89_lob_acceleration")() == ref
        assert getattr(engine, "phase89_lob_spacetime_hydrodynamics")() == ref
        assert getattr(engine, "compute_knk_67_dark_energy_acceleration")() == ref
        assert getattr(engine, "compute_kerr_newman_kiselev_67_dark_energy_acceleration")() == ref
        assert getattr(engine, "phase89_daha_l3_acceleration")() == ref
        assert getattr(engine, "knk_67_dark_energy_daha_l3")() == ref
        assert getattr(engine, "daha_l3_phase89_acceleration")() == ref
        assert getattr(engine, "phase89_dark_energy_acceleration")() == ref
        assert getattr(engine, "calculate_phase89_knk_acceleration")() == ref
        assert getattr(engine, "compute_knk_phase89_acceleration")() == ref
        assert getattr(engine, "daha_phase89_acceleration")() == ref
        assert getattr(engine, "phase89_spacetime_hydrodynamics")() == ref
        assert getattr(engine, "phase89_queue_acceleration")() == ref
        assert getattr(engine, "l3_phase89_acceleration")() == ref
        assert getattr(engine, "phase89_knk_acceleration")() == ref
        assert getattr(engine, "compute_phase89_knk_daha_queue_acceleration")() == ref
        assert getattr(engine, "compute_phase89_queue_acceleration")() == ref
        assert getattr(engine, "phase89_l3_queue_acceleration")() == ref
        assert getattr(engine, "knk_67_daha_queue_acceleration")() == ref

        # Check module-level aliases
        assert compute_kerr_newman_kiselev_67_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(engine) == ref
        assert compute_phase89_lob_acceleration(engine) == ref
        assert phase89_lob_spacetime_hydrodynamics(engine) == ref
        assert compute_knk_67_dark_energy_acceleration(engine) == ref
        assert compute_kerr_newman_kiselev_67_dark_energy_acceleration(engine) == ref
        assert phase89_daha_l3_acceleration(engine) == ref
        assert knk_67_dark_energy_daha_l3(engine) == ref
        assert daha_l3_phase89_acceleration(engine) == ref
        assert phase89_dark_energy_acceleration(engine) == ref
        assert calculate_phase89_knk_acceleration(engine) == ref
        assert compute_knk_phase89_acceleration(engine) == ref
        assert daha_phase89_acceleration(engine) == ref
        assert phase89_spacetime_hydrodynamics(engine) == ref
        assert phase89_queue_acceleration(engine) == ref
        assert l3_phase89_acceleration(engine) == ref
        assert phase89_knk_acceleration(engine) == ref
        assert compute_phase89_knk_daha_queue_acceleration(engine) == ref
        assert compute_phase89_queue_acceleration(engine) == ref
        assert phase89_l3_queue_acceleration(engine) == ref
        assert knk_67_daha_queue_acceleration(engine) == ref

    def test_smart_order_router_phase89_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 89 flags and lit maker floor to 1e-60."""
        sor_89 = SmartOrderRouter(version=89)
        assert getattr(sor_89, "is_phase89", False) is True
        assert getattr(sor_89, "is_phase88", False) is True
        assert getattr(sor_89, "is_phase87", False) is True
        assert getattr(sor_89, "is_phase86", False) is True
        assert getattr(sor_89, "is_phase85", False) is True
        assert getattr(sor_89, "is_phase84", False) is True
        assert getattr(sor_89, "is_phase82", False) is True
        assert getattr(sor_89, "is_phase81", False) is True
        assert getattr(sor_89, "is_phase80", False) is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 89,
            "target_price": 150.0,
            "hawkes_intensity": 0.95,
        }
        res = sor_89.route_order(order_plan, gamma_toxic_dir=1.0)
        assert "maker_ratio" in res
        assert "min_ratio" in res
        assert res["maker_ratio"] == 1e-60

    def test_tick_shading_dual_oms_phase89_threshold(self):
        """Verify tick shading threshold h > 0.00000000015 with 41 nines."""
        # Sub-threshold for v88 (h = 0.00000000018), which triggers v89 (h > 0.00000000015) but not v88 (h > 0.0000000002)
        oms_p89_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=89,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000018}
        )
        oms_p88_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=88,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000018}
        )
        assert oms_p89_sub < oms_p88_sub

        sched = AlmgrenChrissScheduler()
        sched_p89_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=89,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000018}
        )
        assert math.isclose(oms_p89_sub, sched_p89_sub, rel_tol=1e-12)
