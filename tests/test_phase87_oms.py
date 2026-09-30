"""
tests/test_phase87_oms.py

Unit and integration test suite for Phase 87 Quantitative Alpha Enhancement (Feature F408 Microstructure OMS):
- Kerr-Newman-Kiselev 65-Dark-Energy DAHA
  (w = -67/3, k_daha = 0.57, k_monster = 0.56, daha_65_factor = 11.55, c_monster = 6.776263578034403e-21 [2^-67])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 65-fold dark energy density
  * Repulsive acceleration -34.0 * c * (r ** 67) * daha_65_factor
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level
- SmartOrderRouter version=87:
  * Lit maker ratio floor contracted to 1e-58
  * 58-decimal rounding precision for maker_ratio and min_ratio
  * Cascading version flags: is_phase87 -> is_phase86 -> is_phase85 -> is_phase84 -> is_phase82 -> is_phase81 -> is_phase80
- Preemptive micro-tick shading at h > 0.0000000003:
  hawkes_shift = -direction * 0.999999999999999999999999999999999999999 * spr * (h - 0.0000000003)
- Dual-OMS parity across ExecutionOMSEngine and AlmgrenChrissScheduler
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    compute_kerr_newman_kiselev_65_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
    compute_phase87_lob_acceleration,
    phase87_lob_spacetime_hydrodynamics,
    compute_knk_65_dark_energy_acceleration,
    compute_kerr_newman_kiselev_65_dark_energy_acceleration,
    phase87_daha_l3_acceleration,
    knk_65_dark_energy_daha_l3,
    daha_l3_phase87_acceleration,
    phase87_dark_energy_acceleration,
    calculate_phase87_knk_acceleration,
    compute_knk_phase87_acceleration,
    daha_phase87_acceleration,
    phase87_spacetime_hydrodynamics,
    phase87_queue_acceleration,
    l3_phase87_acceleration,
    phase87_knk_acceleration,
    compute_phase87_knk_daha_queue_acceleration,
    compute_phase87_queue_acceleration,
    phase87_l3_queue_acceleration,
    knk_65_daha_queue_acceleration,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase87MicrostructureOMS:
    """Test suite for Phase 87 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_65_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 65-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_65_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_65_dark_energy_correction" in res
        assert "knk_65_dark_energy_daha_acceleration" in res
        assert "phase87_knk_acceleration" in res

        assert math.isfinite(res["knk_65_dark_energy_correction"])
        assert math.isfinite(res["knk_65_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_65_factor"], 11.55, rel_tol=1e-5)
        assert math.isclose(res["k_daha_65"], 0.57, rel_tol=1e-5)
        assert math.isclose(res["k_monster_65"], 0.56, rel_tol=1e-5)
        assert math.isclose(res["c_monster_65"], 6.776263578034403e-21, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_65"], -67.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_65_aliases(self):
        """Verify 20 method aliases on FastOrderBookMatchingEngine and module level for KNK-65."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_65_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        # Check class method aliases
        assert engine.compute_phase87_lob_acceleration() == ref
        assert engine.phase87_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_65_dark_energy_acceleration() == ref
        assert engine.compute_kerr_newman_kiselev_65_dark_energy_acceleration() == ref
        assert engine.phase87_daha_l3_acceleration() == ref
        assert engine.knk_65_dark_energy_daha_l3() == ref
        assert engine.daha_l3_phase87_acceleration() == ref
        assert engine.phase87_dark_energy_acceleration() == ref
        assert engine.calculate_phase87_knk_acceleration() == ref
        assert engine.compute_knk_phase87_acceleration() == ref
        assert engine.daha_phase87_acceleration() == ref
        assert engine.phase87_spacetime_hydrodynamics() == ref
        assert engine.phase87_queue_acceleration() == ref
        assert engine.l3_phase87_acceleration() == ref
        assert engine.phase87_knk_acceleration() == ref
        assert engine.compute_phase87_knk_daha_queue_acceleration() == ref
        assert engine.compute_phase87_queue_acceleration() == ref
        assert engine.phase87_l3_queue_acceleration() == ref
        assert engine.knk_65_daha_queue_acceleration() == ref

        # Check module-level aliases
        assert compute_kerr_newman_kiselev_65_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(engine) == ref
        assert compute_phase87_lob_acceleration(engine) == ref
        assert phase87_lob_spacetime_hydrodynamics(engine) == ref
        assert compute_knk_65_dark_energy_acceleration(engine) == ref
        assert compute_kerr_newman_kiselev_65_dark_energy_acceleration(engine) == ref
        assert phase87_daha_l3_acceleration(engine) == ref
        assert knk_65_dark_energy_daha_l3(engine) == ref
        assert daha_l3_phase87_acceleration(engine) == ref
        assert phase87_dark_energy_acceleration(engine) == ref
        assert calculate_phase87_knk_acceleration(engine) == ref
        assert compute_knk_phase87_acceleration(engine) == ref
        assert daha_phase87_acceleration(engine) == ref
        assert phase87_spacetime_hydrodynamics(engine) == ref
        assert phase87_queue_acceleration(engine) == ref
        assert l3_phase87_acceleration(engine) == ref
        assert phase87_knk_acceleration(engine) == ref
        assert compute_phase87_knk_daha_queue_acceleration(engine) == ref
        assert compute_phase87_queue_acceleration(engine) == ref
        assert phase87_l3_queue_acceleration(engine) == ref
        assert knk_65_daha_queue_acceleration(engine) == ref

    def test_smart_order_router_phase87_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 87 flags and lit maker floor to 1e-58."""
        sor_87 = SmartOrderRouter(version=87)
        assert sor_87.is_phase87 is True
        assert sor_87.is_phase86 is True
        assert sor_87.is_phase85 is True
        assert sor_87.is_phase84 is True
        assert sor_87.is_phase82 is True
        assert sor_87.is_phase81 is True
        assert sor_87.is_phase80 is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 87,
            "target_price": 150.0,
            "hawkes_intensity": 0.95,
        }
        res = sor_87.route_order(order_plan, gamma_toxic_dir=1.0)
        assert "maker_ratio" in res
        assert "min_ratio" in res
        assert res["maker_ratio"] == 1e-58

    def test_tick_shading_dual_oms_phase87_threshold(self):
        """Verify tick shading threshold h > 0.0000000003 with 39 nines."""
        # Sub-threshold for v86 (h = 0.00000000035), which triggers v87 (h > 0.0000000003) but not v86 (h > 0.0000000004)
        oms_p87_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=87,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000035}
        )
        oms_p86_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=86,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000035}
        )
        assert oms_p87_sub < oms_p86_sub

        sched = AlmgrenChrissScheduler()
        sched_p87_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=87,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000000035}
        )
        assert math.isclose(oms_p87_sub, sched_p87_sub, rel_tol=1e-12)
