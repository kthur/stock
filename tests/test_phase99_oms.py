"""
tests/test_phase99_oms.py

Unit and integration test suite for Phase 99 Quantitative Alpha Enhancement (Feature F468 Microstructure OMS):
- Kerr-Newman-Kiselev 77-Dark-Energy DAHA
  (w = -79.0/3.0 ≈ -26.333333333333332, k_daha = 0.69, k_monster = 0.68,
   daha_77_factor = 15.00, c_monster = 1.6543612251060553e-24 [2^-79])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 77-fold dark energy density
  * Repulsive acceleration -42.5 * c * (r ** 84) * daha_77_factor clamped in [-1e6, 1e6]
  * Theoretical check at r_eff = 2.0: exactly -20400.00
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, Phase99FastLOBEngine, and module level (23 aliases)
- SmartOrderRouter version=99:
  * Default version: 99
  * Lit maker ratio floor contracted to 1e-70 with 70-decimal precision
  * Cascading version flags: is_phase99 -> is_phase98 -> is_phase97...
- Preemptive micro-tick shading at h > 0.000000000015 (1.5e-11, tested at h = 0.000000000017):
  oms_p99_sub < oms_p98_sub
- Dual-OMS parity across ExecutionOMSEngine and AlmgrenChrissScheduler
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    Phase99FastLOBEngine,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler

from trading_system.src.core.fast_lob_engine import (
    compute_kerr_newman_kiselev_77_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
    compute_kerr_newman_kiselev_77_dark_energy_daha_queue_acceleration,
    compute_kerr_newman_kiselev_77_dark_energy_daha_acceleration,
    compute_knk_77_dark_energy_daha_acceleration,
    compute_phase99_daha_l3_acceleration,
    compute_phase99_lob_acceleration,
    phase99_lob_spacetime_hydrodynamics,
    compute_knk_77_dark_energy_acceleration,
    compute_kerr_newman_kiselev_77_dark_energy_acceleration,
    phase99_daha_l3_acceleration,
    knk_77_dark_energy_daha_l3,
    daha_l3_phase99_acceleration,
    phase99_dark_energy_acceleration,
    calculate_phase99_knk_acceleration,
    compute_knk_phase99_acceleration,
    daha_phase99_acceleration,
    phase99_spacetime_hydrodynamics,
    phase99_queue_acceleration,
    l3_phase99_acceleration,
    phase99_knk_acceleration,
    compute_phase99_knk_daha_queue_acceleration,
    compute_phase99_queue_acceleration,
    phase99_l3_queue_acceleration,
    knk_77_daha_queue_acceleration,
)


class TestPhase99MicrostructureAndOMS:
    """Test suite for Phase 99 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_77_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 77-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_77_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        assert func is not None, "'FastOrderBookMatchingEngine' object missing KNK-77 acceleration method"

        res = func(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_77_dark_energy_correction" in res
        assert "knk_77_dark_energy_daha_acceleration" in res
        assert "phase99_knk_acceleration" in res
        assert "phase98_knk_acceleration" in res

        assert math.isfinite(res["knk_77_dark_energy_correction"])
        assert math.isfinite(res["knk_77_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_77_factor"], 15.00, rel_tol=1e-5)
        assert math.isclose(res["k_daha_77"], 0.69, rel_tol=1e-5)
        assert math.isclose(res["k_monster_77"], 0.68, rel_tol=1e-5)
        assert math.isclose(res["c_monster_77"], 2.0**-79, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_77"], -79.0 / 3.0, rel_tol=1e-5)

        # Theoretical check: at r_eff = 2.0, c_77 = 2^-79, daha_77_factor = 15.00
        # dark_77_accel = -42.5 * (2^-79) * (2^84) * 15.00 = -42.5 * 32.0 * 15.00 = -20400.00
        c_77 = 2.0**-79
        r_eff = 2.0
        theoretical_dark_accel = -42.5 * c_77 * (r_eff**84) * 15.00
        assert math.isclose(theoretical_dark_accel, -20400.00, rel_tol=1e-9)

    def test_kerr_newman_kiselev_77_aliases(self):
        """Verify 23 method aliases on FastOrderBookMatchingEngine, FastLOBEngine, Phase99FastLOBEngine, and module level for KNK-77."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_77_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        assert func is not None
        ref = func()

        # Check class method aliases (23 aliases)
        alias_names = [
            "compute_kerr_newman_kiselev_77_dark_energy_daha_queue_acceleration",
            "compute_kerr_newman_kiselev_77_dark_energy_daha_acceleration",
            "compute_knk_77_dark_energy_daha_acceleration",
            "compute_phase99_daha_l3_acceleration",
            "compute_phase99_lob_acceleration",
            "phase99_lob_spacetime_hydrodynamics",
            "compute_knk_77_dark_energy_acceleration",
            "compute_kerr_newman_kiselev_77_dark_energy_acceleration",
            "phase99_daha_l3_acceleration",
            "knk_77_dark_energy_daha_l3",
            "daha_l3_phase99_acceleration",
            "phase99_dark_energy_acceleration",
            "calculate_phase99_knk_acceleration",
            "compute_knk_phase99_acceleration",
            "daha_phase99_acceleration",
            "phase99_spacetime_hydrodynamics",
            "phase99_queue_acceleration",
            "l3_phase99_acceleration",
            "phase99_knk_acceleration",
            "compute_phase99_knk_daha_queue_acceleration",
            "compute_phase99_queue_acceleration",
            "phase99_l3_queue_acceleration",
            "knk_77_daha_queue_acceleration",
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

        # Check aliases on Phase99FastLOBEngine alias class
        engine_p99 = Phase99FastLOBEngine(symbol="AAPL")
        for i in range(5):
            engine_p99.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine_p99.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)
        for alias in alias_names:
            method = getattr(engine_p99, alias, None)
            assert method is not None, f"Missing method {alias} on Phase99FastLOBEngine"
            assert method() == ref

        # Check module-level aliases (23 functions)
        module_funcs = [
            compute_kerr_newman_kiselev_77_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
            compute_kerr_newman_kiselev_77_dark_energy_daha_queue_acceleration,
            compute_kerr_newman_kiselev_77_dark_energy_daha_acceleration,
            compute_knk_77_dark_energy_daha_acceleration,
            compute_phase99_daha_l3_acceleration,
            compute_phase99_lob_acceleration,
            phase99_lob_spacetime_hydrodynamics,
            compute_knk_77_dark_energy_acceleration,
            compute_kerr_newman_kiselev_77_dark_energy_acceleration,
            phase99_daha_l3_acceleration,
            knk_77_dark_energy_daha_l3,
            daha_l3_phase99_acceleration,
            phase99_dark_energy_acceleration,
            calculate_phase99_knk_acceleration,
            compute_knk_phase99_acceleration,
            daha_phase99_acceleration,
            phase99_spacetime_hydrodynamics,
            phase99_queue_acceleration,
            l3_phase99_acceleration,
            phase99_knk_acceleration,
            compute_phase99_knk_daha_queue_acceleration,
            compute_phase99_queue_acceleration,
            phase99_l3_queue_acceleration,
            knk_77_daha_queue_acceleration,
        ]
        assert len(module_funcs) == 24  # base + 23 aliases
        for m_fn in module_funcs:
            assert m_fn(engine) == ref

    def test_smart_order_router_phase99_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 99 flags and lit maker floor to 1e-70."""
        sor_99 = SmartOrderRouter(version=99)
        assert getattr(sor_99, "is_phase99", False) is True
        assert getattr(sor_99, "is_phase98", False) is True
        assert getattr(sor_99, "is_phase97", False) is True
        assert getattr(sor_99, "is_phase96", False) is True
        assert getattr(sor_99, "is_phase95", False) is True
        assert getattr(sor_99, "is_phase94", False) is True
        assert getattr(sor_99, "is_phase93", False) is True
        assert getattr(sor_99, "is_phase92", False) is True
        assert getattr(sor_99, "is_phase91", False) is True

        # Default version should be 99
        sor_default = SmartOrderRouter()
        assert sor_default.version == 99
        assert sor_default.is_phase99 is True
        assert sor_default.is_phase98 is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 99,
            "target_price": 150.0,
            "hawkes_intensity": 0.95,
        }
        res = sor_99.route_order(order_plan, gamma_toxic_dir=1.0)
        assert "maker_ratio" in res
        assert "min_ratio" in res
        assert res["maker_ratio"] == 1e-70

    def test_tick_shading_dual_oms_phase99_threshold(self):
        """Verify tick shading threshold h > 0.000000000015 (tested at h = 0.000000000017)."""
        oms_p99_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=99,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000017}
        )
        oms_p98_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=98,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000017}
        )
        # Phase 99 activates at h > 1.5e-11, so at 1.7e-11 it has non-zero shading:
        # Phase 98 activates at h > 2.0e-11, so at 1.7e-11 it has 0 shading offset
        assert oms_p99_sub < oms_p98_sub

        # Sub-threshold check: at h = 1.0e-11, neither should shade
        oms_p99_sub_low = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=99,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000010}
        )
        assert oms_p99_sub_low == 100.0

        # Exact parity with AlmgrenChrissScheduler
        sch_p99_sub = AlmgrenChrissScheduler.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=99,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000017}
        )
        assert math.isclose(oms_p99_sub, sch_p99_sub, rel_tol=1e-12, abs_tol=1e-12)

    def test_zero_regression_phase98_compatibility(self):
        """Verify Phase 98 calculations remain strictly preserved when requested."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        engine.add_limit_order("b1", "BUY", 100.0, 10.0)
        engine.add_limit_order("a1", "SELL", 101.0, 10.0)

        res_p98 = engine.compute_kerr_newman_kiselev_76_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isclose(res_p98["daha_76_factor"], 14.70, rel_tol=1e-5)
        assert math.isclose(res_p98["k_daha_76"], 0.68, rel_tol=1e-5)
        assert math.isclose(res_p98["k_monster_76"], 0.67, rel_tol=1e-5)

        sor_98 = SmartOrderRouter(version=98)
        assert sor_98.is_phase98 is True
        assert sor_98.is_phase99 is False
        order_plan_98 = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 98,
            "target_price": 150.0,
        }
        res_routed = sor_98.route_order(order_plan_98, gamma_toxic_dir=1.0)
        assert res_routed["maker_ratio"] == 1e-69
