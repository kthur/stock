"""
tests/test_phase97_oms.py

Unit and integration test suite for Phase 97 Quantitative Alpha Enhancement (Features F458 Microstructure OMS):
- Kerr-Newman-Kiselev 75-Dark-Energy DAHA
  (w = -77.0/3.0 ≈ -25.667, k_daha = 0.67, k_monster = 0.66, daha_75_factor = 14.40, c_monster = 6.617444900424221e-24 [2^-77])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 75-fold dark energy density
  * Repulsive acceleration -40.5 * c * (r ** 80) * daha_75_factor
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level (23 aliases)
- SmartOrderRouter version=97:
  * Lit maker ratio floor contracted to 1e-68 with 68-decimal precision
  * Cascading version flags: is_phase97 -> is_phase96 -> is_phase95 -> is_phase94...
- Preemptive micro-tick shading at h > 0.00000000003 (3.0e-11, tested at h = 0.000000000035):
  oms_p97_sub < oms_p96_sub
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
    compute_kerr_newman_kiselev_75_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
    compute_kerr_newman_kiselev_75_dark_energy_daha_queue_acceleration,
    compute_kerr_newman_kiselev_75_dark_energy_daha_acceleration,
    compute_knk_75_dark_energy_daha_acceleration,
    compute_phase97_daha_l3_acceleration,
    compute_phase97_lob_acceleration,
    phase97_lob_spacetime_hydrodynamics,
    compute_knk_75_dark_energy_acceleration,
    compute_kerr_newman_kiselev_75_dark_energy_acceleration,
    phase97_daha_l3_acceleration,
    knk_75_dark_energy_daha_l3,
    daha_l3_phase97_acceleration,
    phase97_dark_energy_acceleration,
    calculate_phase97_knk_acceleration,
    compute_knk_phase97_acceleration,
    daha_phase97_acceleration,
    phase97_spacetime_hydrodynamics,
    phase97_queue_acceleration,
    l3_phase97_acceleration,
    phase97_knk_acceleration,
    compute_phase97_knk_daha_queue_acceleration,
    compute_phase97_queue_acceleration,
    phase97_l3_queue_acceleration,
    knk_75_daha_queue_acceleration,
)


class TestPhase97MicrostructureAndOMS:
    """Test suite for Phase 97 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_75_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 75-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_75_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        assert func is not None, "'FastOrderBookMatchingEngine' object missing KNK-75 acceleration method"

        res = func(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_75_dark_energy_correction" in res
        assert "knk_75_dark_energy_daha_acceleration" in res
        assert "phase97_knk_acceleration" in res
        assert "phase96_knk_acceleration" in res

        assert math.isfinite(res["knk_75_dark_energy_correction"])
        assert math.isfinite(res["knk_75_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_75_factor"], 14.40, rel_tol=1e-5)
        assert math.isclose(res["k_daha_75"], 0.67, rel_tol=1e-5)
        assert math.isclose(res["k_monster_75"], 0.66, rel_tol=1e-5)
        assert math.isclose(res["c_monster_75"], 2.0**-77, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_75"], -77.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_75_aliases(self):
        """Verify 23 method aliases on FastOrderBookMatchingEngine and module level for KNK-75."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_75_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        assert func is not None
        ref = func()

        # Check class method aliases (23 aliases)
        alias_names = [
            "compute_kerr_newman_kiselev_75_dark_energy_daha_queue_acceleration",
            "compute_kerr_newman_kiselev_75_dark_energy_daha_acceleration",
            "compute_knk_75_dark_energy_daha_acceleration",
            "compute_phase97_daha_l3_acceleration",
            "compute_phase97_lob_acceleration",
            "phase97_lob_spacetime_hydrodynamics",
            "compute_knk_75_dark_energy_acceleration",
            "compute_kerr_newman_kiselev_75_dark_energy_acceleration",
            "phase97_daha_l3_acceleration",
            "knk_75_dark_energy_daha_l3",
            "daha_l3_phase97_acceleration",
            "phase97_dark_energy_acceleration",
            "calculate_phase97_knk_acceleration",
            "compute_knk_phase97_acceleration",
            "daha_phase97_acceleration",
            "phase97_spacetime_hydrodynamics",
            "phase97_queue_acceleration",
            "l3_phase97_acceleration",
            "phase97_knk_acceleration",
            "compute_phase97_knk_daha_queue_acceleration",
            "compute_phase97_queue_acceleration",
            "phase97_l3_queue_acceleration",
            "knk_75_daha_queue_acceleration",
        ]
        for alias in alias_names:
            method = getattr(engine, alias, None)
            assert method is not None, f"Missing method {alias} on FastOrderBookMatchingEngine"
            assert method() == ref

        # Check module-level aliases (23 functions)
        module_funcs = [
            compute_kerr_newman_kiselev_75_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
            compute_kerr_newman_kiselev_75_dark_energy_daha_queue_acceleration,
            compute_kerr_newman_kiselev_75_dark_energy_daha_acceleration,
            compute_knk_75_dark_energy_daha_acceleration,
            compute_phase97_daha_l3_acceleration,
            compute_phase97_lob_acceleration,
            phase97_lob_spacetime_hydrodynamics,
            compute_knk_75_dark_energy_acceleration,
            compute_kerr_newman_kiselev_75_dark_energy_acceleration,
            phase97_daha_l3_acceleration,
            knk_75_dark_energy_daha_l3,
            daha_l3_phase97_acceleration,
            phase97_dark_energy_acceleration,
            calculate_phase97_knk_acceleration,
            compute_knk_phase97_acceleration,
            daha_phase97_acceleration,
            phase97_spacetime_hydrodynamics,
            phase97_queue_acceleration,
            l3_phase97_acceleration,
            phase97_knk_acceleration,
            compute_phase97_knk_daha_queue_acceleration,
            compute_phase97_queue_acceleration,
            phase97_l3_queue_acceleration,
            knk_75_daha_queue_acceleration,
        ]
        for m_fn in module_funcs:
            assert m_fn(engine) == ref

    def test_smart_order_router_phase97_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 97 flags and lit maker floor to 1e-68."""
        sor_97 = SmartOrderRouter(version=97)
        assert getattr(sor_97, "is_phase97", False) is True
        assert getattr(sor_97, "is_phase96", False) is True
        assert getattr(sor_97, "is_phase95", False) is True
        assert getattr(sor_97, "is_phase94", False) is True
        assert getattr(sor_97, "is_phase93", False) is True
        assert getattr(sor_97, "is_phase92", False) is True
        assert getattr(sor_97, "is_phase91", False) is True

        # Default version should be 97
        sor_default = SmartOrderRouter()
        assert sor_default.version == 97
        assert sor_default.is_phase97 is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 97,
            "target_price": 150.0,
            "hawkes_intensity": 0.95,
        }
        res = sor_97.route_order(order_plan, gamma_toxic_dir=1.0)
        assert "maker_ratio" in res
        assert "min_ratio" in res
        assert res["maker_ratio"] == 1e-68

    def test_tick_shading_dual_oms_phase97_threshold(self):
        """Verify tick shading threshold h > 0.00000000003 (tested at h = 0.000000000035)."""
        oms_p97_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=97,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000035}
        )
        oms_p96_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=96,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000035}
        )
        # Phase 97 activates at h > 3.0e-11, so at 3.5e-11 it has non-zero shading:
        # Phase 96 activates at h > 4.0e-11, so at 3.5e-11 it has 0 shading offset
        assert oms_p97_sub < oms_p96_sub

        sched = AlmgrenChrissScheduler()
        sched_p97_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=97,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000035}
        )
        assert math.isclose(oms_p97_sub, sched_p97_sub, rel_tol=1e-12)

    def test_zero_regression_phase96_compatibility(self):
        """Verify backward compatibility: Phase 96 behaviors remain intact."""
        engine = FastOrderBookMatchingEngine(symbol="MSFT")
        engine.add_limit_order("b1", "BUY", 400.0, 100.0)
        engine.add_limit_order("a1", "SELL", 400.1, 100.0)

        res_p96 = engine.compute_kerr_newman_kiselev_74_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isfinite(res_p96["knk_74_dark_energy_correction"])
        assert math.isclose(res_p96["daha_74_factor"], 14.10, rel_tol=1e-5)

        sor_96 = SmartOrderRouter(version=96)
        assert sor_96.is_phase96 is True
        assert sor_96.is_phase97 is False

        order_plan = {
            "symbol": "MSFT",
            "quantity": 100,
            "action": "BUY",
            "version": 96,
            "target_price": 400.0,
            "hawkes_intensity": 0.95,
        }
        res_sor_96 = sor_96.route_order(order_plan, gamma_toxic_dir=1.0)
        assert res_sor_96["maker_ratio"] == 1e-67
