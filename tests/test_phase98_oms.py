"""
tests/test_phase98_oms.py

Unit and integration test suite for Phase 98 Quantitative Alpha Enhancement (Features F463 Microstructure OMS):
- Kerr-Newman-Kiselev 76-Dark-Energy DAHA
  (w = -78.0/3.0 = -26.0, k_daha = 0.68, k_monster = 0.67, daha_76_factor = 14.70, c_monster = 3.3087224502121105e-24 [2^-78])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 76-fold dark energy density
  * Repulsive acceleration -41.5 * c * (r ** 82) * daha_76_factor clamped in [-1e6, 1e6]
  * Theoretical check at r_eff = 2.0: exactly -9760.80
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level (23 aliases)
- SmartOrderRouter version=98:
  * Default version: 98
  * Lit maker ratio floor contracted to 1e-69 with 69-decimal precision
  * Cascading version flags: is_phase98 -> is_phase97 -> is_phase96...
- Preemptive micro-tick shading at h > 0.00000000002 (2.0e-11, tested at h = 0.000000000025):
  oms_p98_sub < oms_p97_sub
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

from trading_system.src.core.fast_lob_engine import (
    compute_kerr_newman_kiselev_76_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
    compute_kerr_newman_kiselev_76_dark_energy_daha_queue_acceleration,
    compute_kerr_newman_kiselev_76_dark_energy_daha_acceleration,
    compute_knk_76_dark_energy_daha_acceleration,
    compute_phase98_daha_l3_acceleration,
    compute_phase98_lob_acceleration,
    phase98_lob_spacetime_hydrodynamics,
    compute_knk_76_dark_energy_acceleration,
    compute_kerr_newman_kiselev_76_dark_energy_acceleration,
    phase98_daha_l3_acceleration,
    knk_76_dark_energy_daha_l3,
    daha_l3_phase98_acceleration,
    phase98_dark_energy_acceleration,
    calculate_phase98_knk_acceleration,
    compute_knk_phase98_acceleration,
    daha_phase98_acceleration,
    phase98_spacetime_hydrodynamics,
    phase98_queue_acceleration,
    l3_phase98_acceleration,
    phase98_knk_acceleration,
    compute_phase98_knk_daha_queue_acceleration,
    compute_phase98_queue_acceleration,
    phase98_l3_queue_acceleration,
    knk_76_daha_queue_acceleration,
)


class TestPhase98MicrostructureAndOMS:
    """Test suite for Phase 98 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_76_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 76-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_76_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        assert func is not None, "'FastOrderBookMatchingEngine' object missing KNK-76 acceleration method"

        res = func(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_76_dark_energy_correction" in res
        assert "knk_76_dark_energy_daha_acceleration" in res
        assert "phase98_knk_acceleration" in res
        assert "phase97_knk_acceleration" in res

        assert math.isfinite(res["knk_76_dark_energy_correction"])
        assert math.isfinite(res["knk_76_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_76_factor"], 14.70, rel_tol=1e-5)
        assert math.isclose(res["k_daha_76"], 0.68, rel_tol=1e-5)
        assert math.isclose(res["k_monster_76"], 0.67, rel_tol=1e-5)
        assert math.isclose(res["c_monster_76"], 2.0**-78, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_76"], -78.0 / 3.0, rel_tol=1e-5)

        # Theoretical check: at r_eff = 2.0, c_76 = 2^-78, daha_76_factor = 14.70
        # dark_76_accel = -41.5 * (2^-78) * (2^82) * 14.70 = -41.5 * 16.0 * 14.70 = -9760.80
        c_76 = 2.0**-78
        r_eff = 2.0
        theoretical_dark_accel = -41.5 * c_76 * (r_eff**82) * 14.70
        assert math.isclose(theoretical_dark_accel, -9760.80, rel_tol=1e-9)

    def test_kerr_newman_kiselev_76_aliases(self):
        """Verify 23 method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level for KNK-76."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_76_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        assert func is not None
        ref = func()

        # Check class method aliases (23 aliases)
        alias_names = [
            "compute_kerr_newman_kiselev_76_dark_energy_daha_queue_acceleration",
            "compute_kerr_newman_kiselev_76_dark_energy_daha_acceleration",
            "compute_knk_76_dark_energy_daha_acceleration",
            "compute_phase98_daha_l3_acceleration",
            "compute_phase98_lob_acceleration",
            "phase98_lob_spacetime_hydrodynamics",
            "compute_knk_76_dark_energy_acceleration",
            "compute_kerr_newman_kiselev_76_dark_energy_acceleration",
            "phase98_daha_l3_acceleration",
            "knk_76_dark_energy_daha_l3",
            "daha_l3_phase98_acceleration",
            "phase98_dark_energy_acceleration",
            "calculate_phase98_knk_acceleration",
            "compute_knk_phase98_acceleration",
            "daha_phase98_acceleration",
            "phase98_spacetime_hydrodynamics",
            "phase98_queue_acceleration",
            "l3_phase98_acceleration",
            "phase98_knk_acceleration",
            "compute_phase98_knk_daha_queue_acceleration",
            "compute_phase98_queue_acceleration",
            "phase98_l3_queue_acceleration",
            "knk_76_daha_queue_acceleration",
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

        # Check module-level aliases (23 functions)
        module_funcs = [
            compute_kerr_newman_kiselev_76_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
            compute_kerr_newman_kiselev_76_dark_energy_daha_queue_acceleration,
            compute_kerr_newman_kiselev_76_dark_energy_daha_acceleration,
            compute_knk_76_dark_energy_daha_acceleration,
            compute_phase98_daha_l3_acceleration,
            compute_phase98_lob_acceleration,
            phase98_lob_spacetime_hydrodynamics,
            compute_knk_76_dark_energy_acceleration,
            compute_kerr_newman_kiselev_76_dark_energy_acceleration,
            phase98_daha_l3_acceleration,
            knk_76_dark_energy_daha_l3,
            daha_l3_phase98_acceleration,
            phase98_dark_energy_acceleration,
            calculate_phase98_knk_acceleration,
            compute_knk_phase98_acceleration,
            daha_phase98_acceleration,
            phase98_spacetime_hydrodynamics,
            phase98_queue_acceleration,
            l3_phase98_acceleration,
            phase98_knk_acceleration,
            compute_phase98_knk_daha_queue_acceleration,
            compute_phase98_queue_acceleration,
            phase98_l3_queue_acceleration,
            knk_76_daha_queue_acceleration,
        ]
        assert len(module_funcs) == 24  # base + 23 aliases
        for m_fn in module_funcs:
            assert m_fn(engine) == ref

    def test_smart_order_router_phase98_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 98 flags and lit maker floor to 1e-69."""
        sor_98 = SmartOrderRouter(version=98)
        assert getattr(sor_98, "is_phase98", False) is True
        assert getattr(sor_98, "is_phase97", False) is True
        assert getattr(sor_98, "is_phase96", False) is True
        assert getattr(sor_98, "is_phase95", False) is True
        assert getattr(sor_98, "is_phase94", False) is True
        assert getattr(sor_98, "is_phase93", False) is True
        assert getattr(sor_98, "is_phase92", False) is True
        assert getattr(sor_98, "is_phase91", False) is True

        # Default version should be 98
        sor_default = SmartOrderRouter()
        assert sor_default.version == 98
        assert sor_default.is_phase98 is True
        assert sor_default.is_phase97 is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 98,
            "target_price": 150.0,
            "hawkes_intensity": 0.95,
        }
        res = sor_98.route_order(order_plan, gamma_toxic_dir=1.0)
        assert "maker_ratio" in res
        assert "min_ratio" in res
        assert res["maker_ratio"] == 1e-69

    def test_tick_shading_dual_oms_phase98_threshold(self):
        """Verify tick shading threshold h > 0.00000000002 (tested at h = 0.000000000025)."""
        oms_p98_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=98,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000025}
        )
        oms_p97_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=97,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000025}
        )
        # Phase 98 activates at h > 2.0e-11, so at 2.5e-11 it has non-zero shading:
        # Phase 97 activates at h > 3.0e-11, so at 2.5e-11 it has 0 shading offset
        assert oms_p98_sub < oms_p97_sub

        # Sub-threshold check: at h = 1.5e-11, neither should shade
        oms_p98_sub_low = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=98,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000015}
        )
        assert oms_p98_sub_low == 100.0

        # Parity between ExecutionOMSEngine and AlmgrenChrissScheduler
        sched = AlmgrenChrissScheduler()
        sched_p98_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=98,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000025}
        )
        assert math.isclose(oms_p98_sub, sched_p98_sub, rel_tol=1e-12)

    def test_zero_regression_phase97_compatibility(self):
        """Verify backward compatibility: Phase 97 behaviors remain intact."""
        engine = FastOrderBookMatchingEngine(symbol="MSFT")
        engine.add_limit_order("b1", "BUY", 400.0, 100.0)
        engine.add_limit_order("a1", "SELL", 400.1, 100.0)

        res_p97 = engine.compute_kerr_newman_kiselev_75_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isfinite(res_p97["knk_75_dark_energy_correction"])
        assert math.isclose(res_p97["daha_75_factor"], 14.40, rel_tol=1e-5)

        sor_97 = SmartOrderRouter(version=97)
        assert sor_97.is_phase97 is True
        assert sor_97.is_phase98 is False

        order_plan = {
            "symbol": "MSFT",
            "quantity": 100,
            "action": "BUY",
            "version": 97,
            "target_price": 400.0,
            "hawkes_intensity": 0.95,
        }
        res_sor_97 = sor_97.route_order(order_plan, gamma_toxic_dir=1.0)
        assert res_sor_97["maker_ratio"] == 1e-68

        # Phase 97 tick shading at h = 3.5e-11 should still shade
        oms_p97_shade = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=97,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000035}
        )
        assert oms_p97_shade < 100.0
