"""
tests/test_phase95_oms.py

Unit and integration test suite for Phase 95 Quantitative Alpha Enhancement (Features F448 Microstructure OMS):
- Kerr-Newman-Kiselev 73-Dark-Energy DAHA
  (w = -75.0/3.0 = -25.0, k_daha = 0.65, k_monster = 0.64, daha_73_factor = 13.80, c_monster = 2.6469779601696886e-23 [2^-75])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 73-fold dark energy density
  * Repulsive acceleration -38.5 * c * (r ** 76) * daha_73_factor
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level (20 aliases)
- SmartOrderRouter version=95:
  * Lit maker ratio floor contracted to 1e-66 with 66-decimal precision
  * Cascading version flags: is_phase95 -> is_phase94 -> is_phase93 -> is_phase92 -> is_phase91...
- Preemptive micro-tick shading at h > 0.00000000005 (tested at h = 0.00000000006):
  oms_p95_sub < oms_p94_sub
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
        compute_kerr_newman_kiselev_73_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
        compute_phase95_lob_acceleration,
        phase95_lob_spacetime_hydrodynamics,
        compute_knk_73_dark_energy_acceleration,
        compute_kerr_newman_kiselev_73_dark_energy_acceleration,
        phase95_daha_l3_acceleration,
        knk_73_dark_energy_daha_l3,
        daha_l3_phase95_acceleration,
        phase95_dark_energy_acceleration,
        calculate_phase95_knk_acceleration,
        compute_knk_phase95_acceleration,
        daha_phase95_acceleration,
        phase95_spacetime_hydrodynamics,
        phase95_queue_acceleration,
        l3_phase95_acceleration,
        phase95_knk_acceleration,
        compute_phase95_knk_daha_queue_acceleration,
        compute_phase95_queue_acceleration,
        phase95_l3_queue_acceleration,
        knk_73_daha_queue_acceleration,
    )
except ImportError:
    import trading_system.src.core.fast_lob_engine as _fle

    def _missing_fle(name):
        val = getattr(_fle, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'fast_lob_engine' has no Phase 95 attribute '{name}'")
        return _callable

    compute_kerr_newman_kiselev_73_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration = _missing_fle('compute_kerr_newman_kiselev_73_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration')
    compute_phase95_lob_acceleration = _missing_fle('compute_phase95_lob_acceleration')
    phase95_lob_spacetime_hydrodynamics = _missing_fle('phase95_lob_spacetime_hydrodynamics')
    compute_knk_73_dark_energy_acceleration = _missing_fle('compute_knk_73_dark_energy_acceleration')
    compute_kerr_newman_kiselev_73_dark_energy_acceleration = _missing_fle('compute_kerr_newman_kiselev_73_dark_energy_acceleration')
    phase95_daha_l3_acceleration = _missing_fle('phase95_daha_l3_acceleration')
    knk_73_dark_energy_daha_l3 = _missing_fle('knk_73_dark_energy_daha_l3')
    daha_l3_phase95_acceleration = _missing_fle('daha_l3_phase95_acceleration')
    phase95_dark_energy_acceleration = _missing_fle('phase95_dark_energy_acceleration')
    calculate_phase95_knk_acceleration = _missing_fle('calculate_phase95_knk_acceleration')
    compute_knk_phase95_acceleration = _missing_fle('compute_knk_phase95_acceleration')
    daha_phase95_acceleration = _missing_fle('daha_phase95_acceleration')
    phase95_spacetime_hydrodynamics = _missing_fle('phase95_spacetime_hydrodynamics')
    phase95_queue_acceleration = _missing_fle('phase95_queue_acceleration')
    l3_phase95_acceleration = _missing_fle('l3_phase95_acceleration')
    phase95_knk_acceleration = _missing_fle('phase95_knk_acceleration')
    compute_phase95_knk_daha_queue_acceleration = _missing_fle('compute_phase95_knk_daha_queue_acceleration')
    compute_phase95_queue_acceleration = _missing_fle('compute_phase95_queue_acceleration')
    phase95_l3_queue_acceleration = _missing_fle('phase95_l3_queue_acceleration')
    knk_73_daha_queue_acceleration = _missing_fle('knk_73_daha_queue_acceleration')


class TestPhase95MicrostructureAndOMS:
    """Test suite for Phase 95 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_73_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 73-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_73_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        if func is None:
            raise AttributeError("'FastOrderBookMatchingEngine' object has no attribute 'compute_kerr_newman_kiselev_73_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration'")

        res = func(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_73_dark_energy_correction" in res
        assert "knk_73_dark_energy_daha_acceleration" in res
        assert "phase95_knk_acceleration" in res
        assert "phase94_knk_acceleration" in res

        assert math.isfinite(res["knk_73_dark_energy_correction"])
        assert math.isfinite(res["knk_73_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_73_factor"], 13.80, rel_tol=1e-5)
        assert math.isclose(res["k_daha_73"], 0.65, rel_tol=1e-5)
        assert math.isclose(res["k_monster_73"], 0.64, rel_tol=1e-5)
        assert math.isclose(res["c_monster_73"], 2.0**-75, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_73"], -75.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_73_aliases(self):
        """Verify 20 method aliases on FastOrderBookMatchingEngine and module level for KNK-73."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_73_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        if func is None:
            raise AttributeError("'FastOrderBookMatchingEngine' object has no attribute 'compute_kerr_newman_kiselev_73_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration'")

        ref = func()

        # Check class method aliases
        assert getattr(engine, "compute_phase95_lob_acceleration")() == ref
        assert getattr(engine, "phase95_lob_spacetime_hydrodynamics")() == ref
        assert getattr(engine, "compute_knk_73_dark_energy_acceleration")() == ref
        assert getattr(engine, "compute_kerr_newman_kiselev_73_dark_energy_acceleration")() == ref
        assert getattr(engine, "phase95_daha_l3_acceleration")() == ref
        assert getattr(engine, "knk_73_dark_energy_daha_l3")() == ref
        assert getattr(engine, "daha_l3_phase95_acceleration")() == ref
        assert getattr(engine, "phase95_dark_energy_acceleration")() == ref
        assert getattr(engine, "calculate_phase95_knk_acceleration")() == ref
        assert getattr(engine, "compute_knk_phase95_acceleration")() == ref
        assert getattr(engine, "daha_phase95_acceleration")() == ref
        assert getattr(engine, "phase95_spacetime_hydrodynamics")() == ref
        assert getattr(engine, "phase95_queue_acceleration")() == ref
        assert getattr(engine, "l3_phase95_acceleration")() == ref
        assert getattr(engine, "phase95_knk_acceleration")() == ref
        assert getattr(engine, "compute_phase95_knk_daha_queue_acceleration")() == ref
        assert getattr(engine, "compute_phase95_queue_acceleration")() == ref
        assert getattr(engine, "phase95_l3_queue_acceleration")() == ref
        assert getattr(engine, "knk_73_daha_queue_acceleration")() == ref

        # Check module-level aliases
        assert compute_kerr_newman_kiselev_73_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(engine) == ref
        assert compute_phase95_lob_acceleration(engine) == ref
        assert phase95_lob_spacetime_hydrodynamics(engine) == ref
        assert compute_knk_73_dark_energy_acceleration(engine) == ref
        assert compute_kerr_newman_kiselev_73_dark_energy_acceleration(engine) == ref
        assert phase95_daha_l3_acceleration(engine) == ref
        assert knk_73_dark_energy_daha_l3(engine) == ref
        assert daha_l3_phase95_acceleration(engine) == ref
        assert phase95_dark_energy_acceleration(engine) == ref
        assert calculate_phase95_knk_acceleration(engine) == ref
        assert compute_knk_phase95_acceleration(engine) == ref
        assert daha_phase95_acceleration(engine) == ref
        assert phase95_spacetime_hydrodynamics(engine) == ref
        assert phase95_queue_acceleration(engine) == ref
        assert l3_phase95_acceleration(engine) == ref
        assert phase95_knk_acceleration(engine) == ref
        assert compute_phase95_knk_daha_queue_acceleration(engine) == ref
        assert compute_phase95_queue_acceleration(engine) == ref
        assert phase95_l3_queue_acceleration(engine) == ref
        assert knk_73_daha_queue_acceleration(engine) == ref

    def test_smart_order_router_phase95_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 95 flags and lit maker floor to 1e-66."""
        sor_95 = SmartOrderRouter(version=95)
        assert getattr(sor_95, "is_phase95", False) is True
        assert getattr(sor_95, "is_phase94", False) is True
        assert getattr(sor_95, "is_phase93", False) is True
        assert getattr(sor_95, "is_phase92", False) is True
        assert getattr(sor_95, "is_phase91", False) is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 95,
            "target_price": 150.0,
            "hawkes_intensity": 0.95,
        }
        res = sor_95.route_order(order_plan, gamma_toxic_dir=1.0)
        assert "maker_ratio" in res
        assert "min_ratio" in res
        assert res["maker_ratio"] == 1e-66

    def test_tick_shading_dual_oms_phase95_threshold(self):
        """Verify tick shading threshold h > 0.00000000005 (tested at h = 0.00000000006)."""
        oms_p95_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=95,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000006}
        )
        oms_p94_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=94,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000006}
        )
        assert oms_p95_sub < oms_p94_sub

        sched = AlmgrenChrissScheduler()
        sched_p95_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=95,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000006}
        )
        assert math.isclose(oms_p95_sub, sched_p95_sub, rel_tol=1e-12)
