"""
tests/test_phase94_oms.py

Unit and integration test suite for Phase 94 Quantitative Alpha Enhancement (Features F443 Microstructure OMS):
- Kerr-Newman-Kiselev 72-Dark-Energy DAHA
  (w = -74.0/3.0 = -24.666666666666668, k_daha = 0.64, k_monster = 0.63, daha_72_factor = 13.50, c_monster = 5.293955920339377e-23 [2^-74])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 72-fold dark energy density
  * Repulsive acceleration -37.5 * c * (r ** 74) * daha_72_factor
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level (20 aliases)
- SmartOrderRouter version=94:
  * Lit maker ratio floor contracted to 1e-65
  * Cascading version flags: is_phase94 -> is_phase93 -> is_phase92 -> is_phase91 -> is_phase90 -> is_phase89 -> is_phase88 -> is_phase87 -> is_phase86 -> is_phase85 -> is_phase84 -> is_phase82 -> is_phase81 -> is_phase80
- Preemptive micro-tick shading at h > 0.00000000006 (tested at h = 0.00000000007):
  oms_p94_sub < oms_p93_sub
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
        compute_kerr_newman_kiselev_72_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
        compute_phase94_lob_acceleration,
        phase94_lob_spacetime_hydrodynamics,
        compute_knk_72_dark_energy_acceleration,
        compute_kerr_newman_kiselev_72_dark_energy_acceleration,
        phase94_daha_l3_acceleration,
        knk_72_dark_energy_daha_l3,
        daha_l3_phase94_acceleration,
        phase94_dark_energy_acceleration,
        calculate_phase94_knk_acceleration,
        compute_knk_phase94_acceleration,
        daha_phase94_acceleration,
        phase94_spacetime_hydrodynamics,
        phase94_queue_acceleration,
        l3_phase94_acceleration,
        phase94_knk_acceleration,
        compute_phase94_knk_daha_queue_acceleration,
        compute_phase94_queue_acceleration,
        phase94_l3_queue_acceleration,
        knk_72_daha_queue_acceleration,
    )
except ImportError:
    import trading_system.src.core.fast_lob_engine as _fle

    def _missing_fle(name):
        val = getattr(_fle, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'fast_lob_engine' has no Phase 94 attribute '{name}'")
        return _callable

    compute_kerr_newman_kiselev_72_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration = _missing_fle('compute_kerr_newman_kiselev_72_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration')
    compute_phase94_lob_acceleration = _missing_fle('compute_phase94_lob_acceleration')
    phase94_lob_spacetime_hydrodynamics = _missing_fle('phase94_lob_spacetime_hydrodynamics')
    compute_knk_72_dark_energy_acceleration = _missing_fle('compute_knk_72_dark_energy_acceleration')
    compute_kerr_newman_kiselev_72_dark_energy_acceleration = _missing_fle('compute_kerr_newman_kiselev_72_dark_energy_acceleration')
    phase94_daha_l3_acceleration = _missing_fle('phase94_daha_l3_acceleration')
    knk_72_dark_energy_daha_l3 = _missing_fle('knk_72_dark_energy_daha_l3')
    daha_l3_phase94_acceleration = _missing_fle('daha_l3_phase94_acceleration')
    phase94_dark_energy_acceleration = _missing_fle('phase94_dark_energy_acceleration')
    calculate_phase94_knk_acceleration = _missing_fle('calculate_phase94_knk_acceleration')
    compute_knk_phase94_acceleration = _missing_fle('compute_knk_phase94_acceleration')
    daha_phase94_acceleration = _missing_fle('daha_phase94_acceleration')
    phase94_spacetime_hydrodynamics = _missing_fle('phase94_spacetime_hydrodynamics')
    phase94_queue_acceleration = _missing_fle('phase94_queue_acceleration')
    l3_phase94_acceleration = _missing_fle('l3_phase94_acceleration')
    phase94_knk_acceleration = _missing_fle('phase94_knk_acceleration')
    compute_phase94_knk_daha_queue_acceleration = _missing_fle('compute_phase94_knk_daha_queue_acceleration')
    compute_phase94_queue_acceleration = _missing_fle('compute_phase94_queue_acceleration')
    phase94_l3_queue_acceleration = _missing_fle('phase94_l3_queue_acceleration')
    knk_72_daha_queue_acceleration = _missing_fle('knk_72_daha_queue_acceleration')


class TestPhase94MicrostructureAndOMS:
    """Test suite for Phase 94 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_72_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 72-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_72_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        if func is None:
            raise AttributeError("'FastOrderBookMatchingEngine' object has no attribute 'compute_kerr_newman_kiselev_72_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration'")

        res = func(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_72_dark_energy_correction" in res
        assert "knk_72_dark_energy_daha_acceleration" in res
        assert "phase94_knk_acceleration" in res
        assert "phase93_knk_acceleration" in res

        assert math.isfinite(res["knk_72_dark_energy_correction"])
        assert math.isfinite(res["knk_72_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_72_factor"], 13.50, rel_tol=1e-5)
        assert math.isclose(res["k_daha_72"], 0.64, rel_tol=1e-5)
        assert math.isclose(res["k_monster_72"], 0.63, rel_tol=1e-5)
        assert math.isclose(res["c_monster_72"], 2.0**-74, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_72"], -74.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_72_aliases(self):
        """Verify 20 method aliases on FastOrderBookMatchingEngine and module level for KNK-72."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_72_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        if func is None:
            raise AttributeError("'FastOrderBookMatchingEngine' object has no attribute 'compute_kerr_newman_kiselev_72_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration'")

        ref = func()

        # Check class method aliases
        assert getattr(engine, "compute_phase94_lob_acceleration")() == ref
        assert getattr(engine, "phase94_lob_spacetime_hydrodynamics")() == ref
        assert getattr(engine, "compute_knk_72_dark_energy_acceleration")() == ref
        assert getattr(engine, "compute_kerr_newman_kiselev_72_dark_energy_acceleration")() == ref
        assert getattr(engine, "phase94_daha_l3_acceleration")() == ref
        assert getattr(engine, "knk_72_dark_energy_daha_l3")() == ref
        assert getattr(engine, "daha_l3_phase94_acceleration")() == ref
        assert getattr(engine, "phase94_dark_energy_acceleration")() == ref
        assert getattr(engine, "calculate_phase94_knk_acceleration")() == ref
        assert getattr(engine, "compute_knk_phase94_acceleration")() == ref
        assert getattr(engine, "daha_phase94_acceleration")() == ref
        assert getattr(engine, "phase94_spacetime_hydrodynamics")() == ref
        assert getattr(engine, "phase94_queue_acceleration")() == ref
        assert getattr(engine, "l3_phase94_acceleration")() == ref
        assert getattr(engine, "phase94_knk_acceleration")() == ref
        assert getattr(engine, "compute_phase94_knk_daha_queue_acceleration")() == ref
        assert getattr(engine, "compute_phase94_queue_acceleration")() == ref
        assert getattr(engine, "phase94_l3_queue_acceleration")() == ref
        assert getattr(engine, "knk_72_daha_queue_acceleration")() == ref

        # Check module-level aliases
        assert compute_kerr_newman_kiselev_72_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(engine) == ref
        assert compute_phase94_lob_acceleration(engine) == ref
        assert phase94_lob_spacetime_hydrodynamics(engine) == ref
        assert compute_knk_72_dark_energy_acceleration(engine) == ref
        assert compute_kerr_newman_kiselev_72_dark_energy_acceleration(engine) == ref
        assert phase94_daha_l3_acceleration(engine) == ref
        assert knk_72_dark_energy_daha_l3(engine) == ref
        assert daha_l3_phase94_acceleration(engine) == ref
        assert phase94_dark_energy_acceleration(engine) == ref
        assert calculate_phase94_knk_acceleration(engine) == ref
        assert compute_knk_phase94_acceleration(engine) == ref
        assert daha_phase94_acceleration(engine) == ref
        assert phase94_spacetime_hydrodynamics(engine) == ref
        assert phase94_queue_acceleration(engine) == ref
        assert l3_phase94_acceleration(engine) == ref
        assert phase94_knk_acceleration(engine) == ref
        assert compute_phase94_knk_daha_queue_acceleration(engine) == ref
        assert compute_phase94_queue_acceleration(engine) == ref
        assert phase94_l3_queue_acceleration(engine) == ref
        assert knk_72_daha_queue_acceleration(engine) == ref

    def test_smart_order_router_phase94_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 94 flags and lit maker floor to 1e-65."""
        sor_94 = SmartOrderRouter(version=94)
        assert getattr(sor_94, "is_phase94", False) is True
        assert getattr(sor_94, "is_phase93", False) is True
        assert getattr(sor_94, "is_phase92", False) is True
        assert getattr(sor_94, "is_phase91", False) is True
        assert getattr(sor_94, "is_phase90", False) is True
        assert getattr(sor_94, "is_phase89", False) is True
        assert getattr(sor_94, "is_phase88", False) is True
        assert getattr(sor_94, "is_phase87", False) is True
        assert getattr(sor_94, "is_phase86", False) is True
        assert getattr(sor_94, "is_phase85", False) is True
        assert getattr(sor_94, "is_phase84", False) is True
        assert getattr(sor_94, "is_phase82", False) is True
        assert getattr(sor_94, "is_phase81", False) is True
        assert getattr(sor_94, "is_phase80", False) is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 94,
            "target_price": 150.0,
            "hawkes_intensity": 0.95,
        }
        res = sor_94.route_order(order_plan, gamma_toxic_dir=1.0)
        assert "maker_ratio" in res
        assert "min_ratio" in res
        assert res["maker_ratio"] == 1e-65

    def test_tick_shading_dual_oms_phase94_threshold(self):
        """Verify tick shading threshold h > 0.00000000006 (tested at h = 0.00000000007)."""
        # Sub-threshold for v93 (h = 0.00000000007), which triggers v94 (h > 0.00000000006) but not v93 (h > 0.00000000007)
        oms_p94_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=94,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000007}
        )
        oms_p93_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=93,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000007}
        )
        assert oms_p94_sub < oms_p93_sub

        sched = AlmgrenChrissScheduler()
        sched_p94_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=94,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000007}
        )
        assert math.isclose(oms_p94_sub, sched_p94_sub, rel_tol=1e-12)
