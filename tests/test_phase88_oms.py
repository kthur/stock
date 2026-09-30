"""
tests/test_phase88_oms.py

Unit and integration test suite for Phase 88 Quantitative Alpha Enhancement (Feature F413, F414 Microstructure OMS):
- Kerr-Newman-Kiselev 66-Dark-Energy DAHA
  (w = -68.0/3.0, k_daha = 0.58, k_monster = 0.57, daha_66_factor = 11.80, c_monster = 3.3881317890172014e-21 [2^-68])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 66-fold dark energy density
  * Repulsive acceleration -34.0 * c * (r ** 68) * daha_66_factor
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level
- SmartOrderRouter version=88:
  * Lit maker ratio floor contracted to 1e-59
  * 59-decimal rounding precision for maker_ratio and min_ratio
  * Cascading version flags: is_phase88 -> is_phase87 -> is_phase86 -> is_phase85 -> is_phase84 -> is_phase82 -> is_phase81 -> is_phase80
- Preemptive micro-tick shading at h > 0.0000000002:
  hawkes_shift = -direction * 0.9999999999999999999999999999999999999999 * spr * (h - 0.0000000002)
- Dual-OMS parity across ExecutionOMSEngine and AlmgrenChrissScheduler
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    compute_kerr_newman_kiselev_66_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
    compute_phase88_lob_acceleration,
    phase88_lob_spacetime_hydrodynamics,
    compute_knk_66_dark_energy_acceleration,
    compute_kerr_newman_kiselev_66_dark_energy_acceleration,
    phase88_daha_l3_acceleration,
    knk_66_dark_energy_daha_l3,
    daha_l3_phase88_acceleration,
    phase88_dark_energy_acceleration,
    calculate_phase88_knk_acceleration,
    compute_knk_phase88_acceleration,
    daha_phase88_acceleration,
    phase88_spacetime_hydrodynamics,
    phase88_queue_acceleration,
    l3_phase88_acceleration,
    phase88_knk_acceleration,
    compute_phase88_knk_daha_queue_acceleration,
    compute_phase88_queue_acceleration,
    phase88_l3_queue_acceleration,
    knk_66_daha_queue_acceleration,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase88MicrostructureOMS:
    """Test suite for Phase 88 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_66_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 66-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_66_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_66_dark_energy_correction" in res
        assert "knk_66_dark_energy_daha_acceleration" in res
        assert "phase88_knk_acceleration" in res

        assert math.isfinite(res["knk_66_dark_energy_correction"])
        assert math.isfinite(res["knk_66_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_66_factor"], 11.80, rel_tol=1e-5)
        assert math.isclose(res["k_daha_66"], 0.58, rel_tol=1e-5)
        assert math.isclose(res["k_monster_66"], 0.57, rel_tol=1e-5)
        assert math.isclose(res["c_monster_66"], 3.3881317890172014e-21, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_66"], -68.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_66_aliases(self):
        """Verify 20 method aliases on FastOrderBookMatchingEngine and module level for KNK-66."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_66_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        # Check class method aliases
        assert engine.compute_phase88_lob_acceleration() == ref
        assert engine.phase88_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_66_dark_energy_acceleration() == ref
        assert engine.compute_kerr_newman_kiselev_66_dark_energy_acceleration() == ref
        assert engine.phase88_daha_l3_acceleration() == ref
        assert engine.knk_66_dark_energy_daha_l3() == ref
        assert engine.daha_l3_phase88_acceleration() == ref
        assert engine.phase88_dark_energy_acceleration() == ref
        assert engine.calculate_phase88_knk_acceleration() == ref
        assert engine.compute_knk_phase88_acceleration() == ref
        assert engine.daha_phase88_acceleration() == ref
        assert engine.phase88_spacetime_hydrodynamics() == ref
        assert engine.phase88_queue_acceleration() == ref
        assert engine.l3_phase88_acceleration() == ref
        assert engine.phase88_knk_acceleration() == ref
        assert engine.compute_phase88_knk_daha_queue_acceleration() == ref
        assert engine.compute_phase88_queue_acceleration() == ref
        assert engine.phase88_l3_queue_acceleration() == ref
        assert engine.knk_66_daha_queue_acceleration() == ref

        # Check module-level aliases
        assert compute_kerr_newman_kiselev_66_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(engine) == ref
        assert compute_phase88_lob_acceleration(engine) == ref
        assert phase88_lob_spacetime_hydrodynamics(engine) == ref
        assert compute_knk_66_dark_energy_acceleration(engine) == ref
        assert compute_kerr_newman_kiselev_66_dark_energy_acceleration(engine) == ref
        assert phase88_daha_l3_acceleration(engine) == ref
        assert knk_66_dark_energy_daha_l3(engine) == ref
        assert daha_l3_phase88_acceleration(engine) == ref
        assert phase88_dark_energy_acceleration(engine) == ref
        assert calculate_phase88_knk_acceleration(engine) == ref
        assert compute_knk_phase88_acceleration(engine) == ref
        assert daha_phase88_acceleration(engine) == ref
        assert phase88_spacetime_hydrodynamics(engine) == ref
        assert phase88_queue_acceleration(engine) == ref
        assert l3_phase88_acceleration(engine) == ref
        assert phase88_knk_acceleration(engine) == ref
        assert compute_phase88_knk_daha_queue_acceleration(engine) == ref
        assert compute_phase88_queue_acceleration(engine) == ref
        assert phase88_l3_queue_acceleration(engine) == ref
        assert knk_66_daha_queue_acceleration(engine) == ref

    def test_smart_order_router_phase88_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 88 flags and lit maker floor to 1e-59."""
        sor_88 = SmartOrderRouter(version=88)
        assert sor_88.is_phase88 is True
        assert sor_88.is_phase87 is True
        assert sor_88.is_phase86 is True
        assert sor_88.is_phase85 is True
        assert sor_88.is_phase84 is True
        assert sor_88.is_phase82 is True
        assert sor_88.is_phase81 is True
        assert sor_88.is_phase80 is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 88,
            "target_price": 150.0,
            "hawkes_intensity": 0.95,
        }
        res = sor_88.route_order(order_plan, gamma_toxic_dir=1.0)
        assert "maker_ratio" in res
        assert "min_ratio" in res
        assert res["maker_ratio"] == 1e-59

    def test_tick_shading_dual_oms_phase88_threshold(self):
        """Verify tick shading threshold h > 0.0000000002 with 40 nines."""
        # Sub-threshold for v87 (h = 0.00000000025), which triggers v88 (h > 0.0000000002) but not v87 (h > 0.0000000003)
        oms_p88_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=88,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000025}
        )
        oms_p87_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=87,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000025}
        )
        assert oms_p88_sub < oms_p87_sub

        sched = AlmgrenChrissScheduler()
        sched_p88_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=88,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000025}
        )
        assert math.isclose(oms_p88_sub, sched_p88_sub, rel_tol=1e-12)
