"""
tests/test_phase86_oms.py

Unit and integration test suite for Phase 86 Quantitative Alpha Enhancement (Feature F403 Microstructure OMS):
- Kerr-Newman-Kiselev 64-Dark-Energy DAHA
  (w = -66/3 = -22.0, k_daha = 0.56, k_monster = 0.55, daha_64_factor = 11.30, c_monster = 1.3552527156068805e-20 [2^-66])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 64-fold dark energy density
  * Repulsive acceleration -33.5 * c * (r ** 66) * daha_64_factor
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level
- SmartOrderRouter version=86:
  * Lit maker ratio floor contracted to 1e-57
  * 57-decimal rounding precision for maker_ratio and min_ratio
  * Cascading version flags: is_phase86 -> is_phase85 -> is_phase84 -> is_phase82 -> is_phase81 -> is_phase80
- Preemptive micro-tick shading at h > 0.0000000004:
  hawkes_shift = -direction * 0.99999999999999999999999999999999999999 * spr * (h - 0.0000000004)
- Dual-OMS parity across ExecutionOMSEngine and AlmgrenChrissScheduler
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    compute_kerr_newman_kiselev_64_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
    compute_phase86_lob_acceleration,
    phase86_lob_spacetime_hydrodynamics,
    compute_knk_64_dark_energy_acceleration,
    compute_kerr_newman_kiselev_64_dark_energy_acceleration,
    phase86_daha_l3_acceleration,
    knk_64_dark_energy_daha_l3,
    daha_l3_phase86_acceleration,
    phase86_dark_energy_acceleration,
    calculate_phase86_knk_acceleration,
    compute_knk_phase86_acceleration,
    daha_phase86_acceleration,
    phase86_spacetime_hydrodynamics,
    phase86_queue_acceleration,
    l3_phase86_acceleration,
    phase86_knk_acceleration,
    compute_phase86_knk_daha_queue_acceleration,
    compute_phase86_queue_acceleration,
    phase86_l3_queue_acceleration,
    knk_64_daha_queue_acceleration,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase86MicrostructureOMS:
    """Test suite for Phase 86 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_64_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 64-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_64_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_64_dark_energy_correction" in res
        assert "knk_64_dark_energy_daha_acceleration" in res
        assert "phase86_knk_acceleration" in res

        assert math.isfinite(res["knk_64_dark_energy_correction"])
        assert math.isfinite(res["knk_64_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_64_factor"], 11.30, rel_tol=1e-5)
        assert math.isclose(res["k_daha_64"], 0.56, rel_tol=1e-5)
        assert math.isclose(res["k_monster_64"], 0.55, rel_tol=1e-5)
        assert math.isclose(res["c_monster_64"], 1.3552527156068805e-20, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_64"], -22.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_64_aliases(self):
        """Verify 20 method aliases on FastOrderBookMatchingEngine and module level for KNK-64."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_64_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        # Check class method aliases
        assert engine.compute_phase86_lob_acceleration() == ref
        assert engine.phase86_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_64_dark_energy_acceleration() == ref
        assert engine.compute_kerr_newman_kiselev_64_dark_energy_acceleration() == ref
        assert engine.phase86_daha_l3_acceleration() == ref
        assert engine.knk_64_dark_energy_daha_l3() == ref
        assert engine.daha_l3_phase86_acceleration() == ref
        assert engine.phase86_dark_energy_acceleration() == ref
        assert engine.calculate_phase86_knk_acceleration() == ref
        assert engine.compute_knk_phase86_acceleration() == ref
        assert engine.daha_phase86_acceleration() == ref
        assert engine.phase86_spacetime_hydrodynamics() == ref
        assert engine.phase86_queue_acceleration() == ref
        assert engine.l3_phase86_acceleration() == ref
        assert engine.phase86_knk_acceleration() == ref
        assert engine.compute_phase86_knk_daha_queue_acceleration() == ref
        assert engine.compute_phase86_queue_acceleration() == ref
        assert engine.phase86_l3_queue_acceleration() == ref
        assert engine.knk_64_daha_queue_acceleration() == ref

        # Check module-level aliases
        assert compute_kerr_newman_kiselev_64_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(engine) == ref
        assert compute_phase86_lob_acceleration(engine) == ref
        assert phase86_lob_spacetime_hydrodynamics(engine) == ref
        assert compute_knk_64_dark_energy_acceleration(engine) == ref
        assert compute_kerr_newman_kiselev_64_dark_energy_acceleration(engine) == ref
        assert phase86_daha_l3_acceleration(engine) == ref
        assert knk_64_dark_energy_daha_l3(engine) == ref
        assert daha_l3_phase86_acceleration(engine) == ref
        assert phase86_dark_energy_acceleration(engine) == ref
        assert calculate_phase86_knk_acceleration(engine) == ref
        assert compute_knk_phase86_acceleration(engine) == ref
        assert daha_phase86_acceleration(engine) == ref
        assert phase86_spacetime_hydrodynamics(engine) == ref
        assert phase86_queue_acceleration(engine) == ref
        assert l3_phase86_acceleration(engine) == ref
        assert phase86_knk_acceleration(engine) == ref
        assert compute_phase86_knk_daha_queue_acceleration(engine) == ref
        assert compute_phase86_queue_acceleration(engine) == ref
        assert phase86_l3_queue_acceleration(engine) == ref
        assert knk_64_daha_queue_acceleration(engine) == ref

    def test_smart_order_router_phase86_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 86 flags and lit maker floor to 1e-57."""
        sor_86 = SmartOrderRouter(version=86)
        assert sor_86.is_phase86 is True
        assert sor_86.is_phase85 is True
        assert sor_86.is_phase84 is True
        assert sor_86.is_phase82 is True
        assert sor_86.is_phase81 is True
        assert sor_86.is_phase80 is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 86,
            "target_price": 150.0,
            "hawkes_intensity": 0.95,
        }
        res = sor_86.route_order(order_plan, gamma_toxic_dir=1.0)
        assert "maker_ratio" in res
        assert "min_ratio" in res
        assert res["maker_ratio"] == 1e-57

    def test_tick_shading_dual_oms_phase86_threshold(self):
        """Verify tick shading threshold h > 0.0000000004 with 38 nines."""
        # Sub-threshold for v85 (h = 0.00000000045), which triggers v86 (h > 0.0000000004) but not v85 (h > 0.0000000005)
        oms_p86_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=86,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000045}
        )
        oms_p85_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=85,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000045}
        )
        assert oms_p86_sub < oms_p85_sub

        sched = AlmgrenChrissScheduler()
        sched_p86_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=86,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000045}
        )
        assert math.isclose(oms_p86_sub, sched_p86_sub, rel_tol=1e-12)
