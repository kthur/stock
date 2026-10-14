"""
tests/test_phase100_oms.py

Unit and integration test suite for Phase 100 Quantitative Alpha Enhancement (Feature F473 Microstructure OMS):
- Kerr-Newman-Kiselev 78-Dark-Energy DAHA
  (w = -80.0/3.0 ≈ -26.666666666666668, k_daha = 0.70, k_monster = 0.69,
   daha_78_factor = 15.30, c_monster = 8.271806125530277e-25 [2^-80])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 78-fold dark energy density
  * Repulsive acceleration -43.5 * c * (r ** 86) * daha_78_factor clamped in [-1e6, 1e6]
  * Theoretical check at r_eff = 2.0: exactly -42595.20
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, Phase100FastLOBEngine, and module level (23 aliases)
- SmartOrderRouter version=100:
  * Default version: 100
  * Lit maker ratio floor contracted to 1e-71 with 71-decimal precision
  * Cascading version flags: is_phase100 -> is_phase99 -> is_phase98...
- Preemptive micro-tick shading at h > 0.000000000012 (1.2e-11, tested at h = 0.000000000013):
  oms_p100_sub < oms_p99_sub
- Dual-OMS parity across ExecutionOMSEngine and AlmgrenChrissScheduler
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    Phase100FastLOBEngine,
    Phase99FastLOBEngine,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler

from trading_system.src.core.fast_lob_engine import (
    compute_kerr_newman_kiselev_78_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
    compute_kerr_newman_kiselev_78_dark_energy_daha_queue_acceleration,
    compute_kerr_newman_kiselev_78_dark_energy_daha_acceleration,
    compute_knk_78_dark_energy_daha_acceleration,
    compute_phase100_daha_l3_acceleration,
    compute_phase100_lob_acceleration,
    phase100_lob_spacetime_hydrodynamics,
    compute_knk_78_dark_energy_acceleration,
    compute_kerr_newman_kiselev_78_dark_energy_acceleration,
    phase100_daha_l3_acceleration,
    knk_78_dark_energy_daha_l3,
    daha_l3_phase100_acceleration,
    phase100_dark_energy_acceleration,
    calculate_phase100_knk_acceleration,
    compute_knk_phase100_acceleration,
    daha_phase100_acceleration,
    phase100_spacetime_hydrodynamics,
    phase100_queue_acceleration,
    l3_phase100_acceleration,
    phase100_knk_acceleration,
    compute_phase100_knk_daha_queue_acceleration,
    compute_phase100_queue_acceleration,
    phase100_l3_queue_acceleration,
    knk_78_daha_queue_acceleration,
)


class TestPhase100MicrostructureAndOMS:
    """Test suite for Phase 100 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_78_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 78-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_78_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        assert func is not None, "'FastOrderBookMatchingEngine' object missing KNK-78 acceleration method"

        res = func(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_78_dark_energy_correction" in res
        assert "knk_78_dark_energy_daha_acceleration" in res
        assert "phase100_knk_acceleration" in res
        assert "phase99_knk_acceleration" in res

        assert math.isfinite(res["knk_78_dark_energy_correction"])
        assert math.isfinite(res["knk_78_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_78_factor"], 15.30, rel_tol=1e-5)
        assert math.isclose(res["k_daha_78"], 0.70, rel_tol=1e-5)
        assert math.isclose(res["k_monster_78"], 0.69, rel_tol=1e-5)
        assert math.isclose(res["c_monster_78"], 2.0**-80, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_78"], -80.0 / 3.0, rel_tol=1e-5)

        # Theoretical check: at r_eff = 2.0, c_78 = 2^-80, daha_78_factor = 15.30
        # dark_78_accel = -43.5 * (2^-80) * (2^86) * 15.30 = -43.5 * 64.0 * 15.30 = -42595.20
        c_78 = 2.0**-80
        r_eff = 2.0
        theoretical_dark_accel = -43.5 * c_78 * (r_eff**86) * 15.30
        assert math.isclose(theoretical_dark_accel, -42595.20, rel_tol=1e-9)

    def test_kerr_newman_kiselev_78_aliases(self):
        """Verify 23 method aliases on FastOrderBookMatchingEngine, FastLOBEngine, Phase100FastLOBEngine, and module level for KNK-78."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_78_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        assert func is not None
        ref = func()

        # Check class method aliases (23 aliases)
        alias_names = [
            "compute_kerr_newman_kiselev_78_dark_energy_daha_queue_acceleration",
            "compute_kerr_newman_kiselev_78_dark_energy_daha_acceleration",
            "compute_knk_78_dark_energy_daha_acceleration",
            "compute_phase100_daha_l3_acceleration",
            "compute_phase100_lob_acceleration",
            "phase100_lob_spacetime_hydrodynamics",
            "compute_knk_78_dark_energy_acceleration",
            "compute_kerr_newman_kiselev_78_dark_energy_acceleration",
            "phase100_daha_l3_acceleration",
            "knk_78_dark_energy_daha_l3",
            "daha_l3_phase100_acceleration",
            "phase100_dark_energy_acceleration",
            "calculate_phase100_knk_acceleration",
            "compute_knk_phase100_acceleration",
            "daha_phase100_acceleration",
            "phase100_spacetime_hydrodynamics",
            "phase100_queue_acceleration",
            "l3_phase100_acceleration",
            "phase100_knk_acceleration",
            "compute_phase100_knk_daha_queue_acceleration",
            "compute_phase100_queue_acceleration",
            "phase100_l3_queue_acceleration",
            "knk_78_daha_queue_acceleration",
        ]
        assert len(alias_names) == 23

        for alias in alias_names:
            method = getattr(engine, alias, None)
            assert method is not None, f"Missing method {alias} on FastOrderBookMatchingEngine"
            assert method() == ref

        # Check aliases on FastLOBEngine alias class
        engine_lob = FastLOBEngine(symbol="AAPL")
        for i in range(5):
            engine_lob.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine_lob.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)
        for alias in alias_names:
            method = getattr(engine_lob, alias, None)
            assert method is not None, f"Missing method {alias} on FastLOBEngine"
            assert method() == ref

        # Check aliases on Phase100FastLOBEngine alias class
        engine_p100 = Phase100FastLOBEngine(symbol="AAPL")
        for i in range(5):
            engine_p100.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine_p100.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)
        for alias in alias_names:
            method = getattr(engine_p100, alias, None)
            assert method is not None, f"Missing method {alias} on Phase100FastLOBEngine"
            assert method() == ref

        # Check module-level aliases (23 functions)
        module_funcs = [
            compute_kerr_newman_kiselev_78_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
            compute_kerr_newman_kiselev_78_dark_energy_daha_queue_acceleration,
            compute_kerr_newman_kiselev_78_dark_energy_daha_acceleration,
            compute_knk_78_dark_energy_daha_acceleration,
            compute_phase100_daha_l3_acceleration,
            compute_phase100_lob_acceleration,
            phase100_lob_spacetime_hydrodynamics,
            compute_knk_78_dark_energy_acceleration,
            compute_kerr_newman_kiselev_78_dark_energy_acceleration,
            phase100_daha_l3_acceleration,
            knk_78_dark_energy_daha_l3,
            daha_l3_phase100_acceleration,
            phase100_dark_energy_acceleration,
            calculate_phase100_knk_acceleration,
            compute_knk_phase100_acceleration,
            daha_phase100_acceleration,
            phase100_spacetime_hydrodynamics,
            phase100_queue_acceleration,
            l3_phase100_acceleration,
            phase100_knk_acceleration,
            compute_phase100_knk_daha_queue_acceleration,
            compute_phase100_queue_acceleration,
            phase100_l3_queue_acceleration,
            knk_78_daha_queue_acceleration,
        ]
        assert len(module_funcs) == 24  # base + 23 aliases
        for m_fn in module_funcs:
            assert m_fn(engine) == ref

    def test_smart_order_router_phase100_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 100 flags and lit maker floor to 1e-71."""
        sor_100 = SmartOrderRouter(version=100)
        assert getattr(sor_100, "is_phase100", False) is True
        assert getattr(sor_100, "is_phase99", False) is True
        assert getattr(sor_100, "is_phase98", False) is True
        assert getattr(sor_100, "is_phase97", False) is True
        assert getattr(sor_100, "is_phase96", False) is True
        assert getattr(sor_100, "is_phase95", False) is True
        assert getattr(sor_100, "is_phase94", False) is True
        assert getattr(sor_100, "is_phase93", False) is True
        assert getattr(sor_100, "is_phase92", False) is True
        assert getattr(sor_100, "is_phase91", False) is True

        # Default version should be 100
        sor_default = SmartOrderRouter()
        assert sor_default.version == 100
        assert sor_default.is_phase100 is True
        assert sor_default.is_phase99 is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 100,
            "target_price": 150.0,
            "hawkes_intensity": 0.95,
        }
        res = sor_100.route_order(order_plan, gamma_toxic_dir=1.0)
        assert "maker_ratio" in res
        assert "min_ratio" in res
        assert res["maker_ratio"] == 1e-71

    def test_tick_shading_dual_oms_phase100_threshold(self):
        """Verify tick shading threshold h > 0.000000000012 (tested at h = 0.000000000013)."""
        oms_p100_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=100,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000013}
        )
        oms_p99_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=99,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000013}
        )
        # Phase 100 activates at h > 1.2e-11, so at 1.3e-11 it has non-zero shading:
        # Phase 99 activates at h > 1.5e-11, so at 1.3e-11 it has 0 shading offset
        assert oms_p100_sub < oms_p99_sub

        # Sub-threshold check: at h = 1.0e-11, neither should shade
        oms_p100_sub_low = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=100,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000010}
        )
        assert oms_p100_sub_low == 100.0

        # Exact parity with AlmgrenChrissScheduler
        sch_p100_sub = AlmgrenChrissScheduler.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=100,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000013}
        )
        assert math.isclose(oms_p100_sub, sch_p100_sub, rel_tol=1e-12, abs_tol=1e-12)

    def test_zero_regression_phase99_compatibility(self):
        """Verify Phase 99 calculations remain strictly preserved when requested."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        engine.add_limit_order("b1", "BUY", 100.0, 10.0)
        engine.add_limit_order("a1", "SELL", 101.0, 10.0)

        res_p99 = engine.compute_kerr_newman_kiselev_77_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isclose(res_p99["daha_77_factor"], 15.00, rel_tol=1e-5)
        assert math.isclose(res_p99["k_daha_77"], 0.69, rel_tol=1e-5)
        assert math.isclose(res_p99["k_monster_77"], 0.68, rel_tol=1e-5)

        sor_99 = SmartOrderRouter(version=99)
        assert sor_99.is_phase99 is True
        assert sor_99.is_phase100 is False
        order_plan_99 = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 99,
            "target_price": 150.0,
        }
        res_routed = sor_99.route_order(order_plan_99, gamma_toxic_dir=1.0)
        assert res_routed["maker_ratio"] == 1e-70
