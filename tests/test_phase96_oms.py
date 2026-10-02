"""
tests/test_phase96_oms.py

Unit and integration test suite for Phase 96 Quantitative Alpha Enhancement (Features F453 Microstructure OMS):
- Kerr-Newman-Kiselev 74-Dark-Energy DAHA
  (w = -76.0/3.0 ≈ -25.333, k_daha = 0.66, k_monster = 0.65, daha_74_factor = 14.10, c_monster = 1.3234889800848443e-23 [2^-76])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 74-fold dark energy density
  * Repulsive acceleration -39.5 * c * (r ** 78) * daha_74_factor
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level (20+ aliases)
- SmartOrderRouter version=96:
  * Lit maker ratio floor contracted to 1e-67 with 67-decimal precision
  * Cascading version flags: is_phase96 -> is_phase95 -> is_phase94 -> is_phase93...
- Preemptive micro-tick shading at h > 0.00000000004 (4.0e-11, tested at h = 0.00000000005):
  oms_p96_sub < oms_p95_sub
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
        compute_kerr_newman_kiselev_74_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
        compute_kerr_newman_kiselev_74_dark_energy_daha_queue_acceleration,
        compute_phase96_lob_acceleration,
        phase96_lob_spacetime_hydrodynamics,
        compute_knk_74_dark_energy_acceleration,
        compute_kerr_newman_kiselev_74_dark_energy_acceleration,
        phase96_daha_l3_acceleration,
        knk_74_dark_energy_daha_l3,
        daha_l3_phase96_acceleration,
        phase96_dark_energy_acceleration,
        calculate_phase96_knk_acceleration,
        compute_knk_phase96_acceleration,
        daha_phase96_acceleration,
        phase96_spacetime_hydrodynamics,
        phase96_queue_acceleration,
        l3_phase96_acceleration,
        phase96_knk_acceleration,
        compute_phase96_knk_daha_queue_acceleration,
        compute_phase96_queue_acceleration,
        phase96_l3_queue_acceleration,
        knk_74_daha_queue_acceleration,
    )
except ImportError:
    import trading_system.src.core.fast_lob_engine as _fle

    def _missing_fle(name):
        val = getattr(_fle, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'fast_lob_engine' has no Phase 96 attribute '{name}'")
        return _callable

    compute_kerr_newman_kiselev_74_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration = _missing_fle('compute_kerr_newman_kiselev_74_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration')
    compute_kerr_newman_kiselev_74_dark_energy_daha_queue_acceleration = _missing_fle('compute_kerr_newman_kiselev_74_dark_energy_daha_queue_acceleration')
    compute_phase96_lob_acceleration = _missing_fle('compute_phase96_lob_acceleration')
    phase96_lob_spacetime_hydrodynamics = _missing_fle('phase96_lob_spacetime_hydrodynamics')
    compute_knk_74_dark_energy_acceleration = _missing_fle('compute_knk_74_dark_energy_acceleration')
    compute_kerr_newman_kiselev_74_dark_energy_acceleration = _missing_fle('compute_kerr_newman_kiselev_74_dark_energy_acceleration')
    phase96_daha_l3_acceleration = _missing_fle('phase96_daha_l3_acceleration')
    knk_74_dark_energy_daha_l3 = _missing_fle('knk_74_dark_energy_daha_l3')
    daha_l3_phase96_acceleration = _missing_fle('daha_l3_phase96_acceleration')
    phase96_dark_energy_acceleration = _missing_fle('phase96_dark_energy_acceleration')
    calculate_phase96_knk_acceleration = _missing_fle('calculate_phase96_knk_acceleration')
    compute_knk_phase96_acceleration = _missing_fle('compute_knk_phase96_acceleration')
    daha_phase96_acceleration = _missing_fle('daha_phase96_acceleration')
    phase96_spacetime_hydrodynamics = _missing_fle('phase96_spacetime_hydrodynamics')
    phase96_queue_acceleration = _missing_fle('phase96_queue_acceleration')
    l3_phase96_acceleration = _missing_fle('l3_phase96_acceleration')
    phase96_knk_acceleration = _missing_fle('phase96_knk_acceleration')
    compute_phase96_knk_daha_queue_acceleration = _missing_fle('compute_phase96_knk_daha_queue_acceleration')
    compute_phase96_queue_acceleration = _missing_fle('compute_phase96_queue_acceleration')
    phase96_l3_queue_acceleration = _missing_fle('phase96_l3_queue_acceleration')
    knk_74_daha_queue_acceleration = _missing_fle('knk_74_daha_queue_acceleration')


class TestPhase96MicrostructureAndOMS:
    """Test suite for Phase 96 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_74_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 74-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_74_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        if func is None:
            raise AttributeError("'FastOrderBookMatchingEngine' object has no attribute 'compute_kerr_newman_kiselev_74_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration'")

        res = func(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_74_dark_energy_correction" in res
        assert "knk_74_dark_energy_daha_acceleration" in res
        assert "phase96_knk_acceleration" in res
        assert "phase95_knk_acceleration" in res

        assert math.isfinite(res["knk_74_dark_energy_correction"])
        assert math.isfinite(res["knk_74_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_74_factor"], 14.10, rel_tol=1e-5)
        assert math.isclose(res["k_daha_74"], 0.66, rel_tol=1e-5)
        assert math.isclose(res["k_monster_74"], 0.65, rel_tol=1e-5)
        assert math.isclose(res["c_monster_74"], 2.0**-76, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_74"], -76.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_74_aliases(self):
        """Verify 20 method aliases on FastOrderBookMatchingEngine and module level for KNK-74."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_74_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        if func is None:
            raise AttributeError("'FastOrderBookMatchingEngine' object has no attribute 'compute_kerr_newman_kiselev_74_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration'")

        ref = func()

        # Check class method aliases
        alias_names = [
            "compute_kerr_newman_kiselev_74_dark_energy_daha_queue_acceleration",
            "compute_kerr_newman_kiselev_74_dark_energy_daha_acceleration",
            "compute_knk_74_dark_energy_daha_acceleration",
            "compute_phase96_daha_l3_acceleration",
            "compute_phase96_lob_acceleration",
            "phase96_lob_spacetime_hydrodynamics",
            "compute_knk_74_dark_energy_acceleration",
            "compute_kerr_newman_kiselev_74_dark_energy_acceleration",
            "phase96_daha_l3_acceleration",
            "knk_74_dark_energy_daha_l3",
            "daha_l3_phase96_acceleration",
            "phase96_dark_energy_acceleration",
            "calculate_phase96_knk_acceleration",
            "compute_knk_phase96_acceleration",
            "daha_phase96_acceleration",
            "phase96_spacetime_hydrodynamics",
            "phase96_queue_acceleration",
            "l3_phase96_acceleration",
            "phase96_knk_acceleration",
            "compute_phase96_knk_daha_queue_acceleration",
            "compute_phase96_queue_acceleration",
            "phase96_l3_queue_acceleration",
            "knk_74_daha_queue_acceleration",
        ]
        for alias in alias_names:
            method = getattr(engine, alias, None)
            assert method is not None, f"Missing method {alias} on FastOrderBookMatchingEngine"
            assert method() == ref

        # Check module-level aliases
        module_funcs = [
            compute_kerr_newman_kiselev_74_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
            compute_kerr_newman_kiselev_74_dark_energy_daha_queue_acceleration,
            compute_phase96_lob_acceleration,
            phase96_lob_spacetime_hydrodynamics,
            compute_knk_74_dark_energy_acceleration,
            compute_kerr_newman_kiselev_74_dark_energy_acceleration,
            phase96_daha_l3_acceleration,
            knk_74_dark_energy_daha_l3,
            daha_l3_phase96_acceleration,
            phase96_dark_energy_acceleration,
            calculate_phase96_knk_acceleration,
            compute_knk_phase96_acceleration,
            daha_phase96_acceleration,
            phase96_spacetime_hydrodynamics,
            phase96_queue_acceleration,
            l3_phase96_acceleration,
            phase96_knk_acceleration,
            compute_phase96_knk_daha_queue_acceleration,
            compute_phase96_queue_acceleration,
            phase96_l3_queue_acceleration,
            knk_74_daha_queue_acceleration,
        ]
        for m_fn in module_funcs:
            assert m_fn(engine) == ref

    def test_smart_order_router_phase96_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 96 flags and lit maker floor to 1e-67."""
        sor_96 = SmartOrderRouter(version=96)
        assert getattr(sor_96, "is_phase96", False) is True
        assert getattr(sor_96, "is_phase95", False) is True
        assert getattr(sor_96, "is_phase94", False) is True
        assert getattr(sor_96, "is_phase93", False) is True
        assert getattr(sor_96, "is_phase92", False) is True
        assert getattr(sor_96, "is_phase91", False) is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 96,
            "target_price": 150.0,
            "hawkes_intensity": 0.95,
        }
        res = sor_96.route_order(order_plan, gamma_toxic_dir=1.0)
        assert "maker_ratio" in res
        assert "min_ratio" in res
        assert res["maker_ratio"] == 1e-67

    def test_tick_shading_dual_oms_phase96_threshold(self):
        """Verify tick shading threshold h > 0.00000000004 (tested at h = 0.00000000005)."""
        oms_p96_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=96,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000005}
        )
        oms_p95_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=95,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000005}
        )
        # Phase 96 activates at h > 4.0e-11, so at 5.0e-11 it has non-zero shading:
        # Phase 95 activates at h > 5.0e-11, so at 5.0e-11 it has 0 shading offset
        assert oms_p96_sub < oms_p95_sub

        sched = AlmgrenChrissScheduler()
        sched_p96_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=96,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000005}
        )
        assert math.isclose(oms_p96_sub, sched_p96_sub, rel_tol=1e-12)
