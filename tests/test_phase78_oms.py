"""
tests/test_phase78_oms.py

Unit and integration test suite for Phase 78 Quantitative Alpha Enhancement (Feature F364.1 & F364.2 Microstructure OMS):
- Kerr-Newman-Kiselev 57-Dark-Energy DAHA
  (w = -59/3 ≈ -19.666666666666668, k_daha = 0.49, k_monster = 0.48, daha_57_factor = 9.85, c_monster = 1.734723475976807e-18 [2^-59])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 57-fold dark energy density
  * Repulsive acceleration -30.0 * c * (r ** 59) * daha_57_factor
  * Metric distortion & charge acceleration
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level
- SmartOrderRouter version=78:
  * Lit maker ratio floor contracted to 1e-50
  * 50-decimal rounding precision for maker_ratio and min_ratio
  * Cascading version flags: is_phase78 -> is_phase77 -> is_phase76 -> is_phase75
- Preemptive micro-tick shading at h > 0.00000001:
  hawkes_shift = -direction * 0.9999999999999999999999999999999 * spr * (h - 0.00000001)
- Dual-OMS parity across ExecutionOMSEngine and AlmgrenChrissScheduler
- Full backward compatibility with Phase 77 and earlier.
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    compute_kerr_newman_kiselev_57_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
    compute_phase78_lob_acceleration,
    phase78_lob_spacetime_hydrodynamics,
    compute_knk_57_dark_energy_acceleration,
    compute_kerr_newman_kiselev_57_dark_energy_acceleration,
    phase78_daha_l3_acceleration,
    knk_57_dark_energy_daha_l3,
    daha_l3_phase78_acceleration,
    phase78_dark_energy_acceleration,
    calculate_phase78_knk_acceleration,
    compute_knk_phase78_acceleration,
    daha_phase78_acceleration,
    phase78_spacetime_hydrodynamics,
    phase78_queue_acceleration,
    l3_phase78_acceleration,
    phase78_knk_acceleration,
    compute_phase78_knk_daha_queue_acceleration,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase78MicrostructureOMS:
    """Test suite for Phase 78 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_57_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 57-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_57_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_57_dark_energy_correction" in res
        assert "knk_57_dark_energy_daha_acceleration" in res
        assert "phase78_knk_acceleration" in res

        assert math.isfinite(res["knk_57_dark_energy_correction"])
        assert math.isfinite(res["knk_57_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_57_factor"], 9.85, rel_tol=1e-5)
        assert math.isclose(res["k_daha_57"], 0.49, rel_tol=1e-5)
        assert math.isclose(res["k_monster_57"], 0.48, rel_tol=1e-5)
        assert math.isclose(res["c_monster_57"], 1.734723475976807e-18, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_57"], -59.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_57_aliases(self):
        """Verify 16 method aliases on FastOrderBookMatchingEngine and module level for KNK-57."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_57_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        # Check all 16 class method aliases
        assert engine.compute_phase78_lob_acceleration() == ref
        assert engine.phase78_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_57_dark_energy_acceleration() == ref
        assert engine.compute_kerr_newman_kiselev_57_dark_energy_acceleration() == ref
        assert engine.phase78_daha_l3_acceleration() == ref
        assert engine.knk_57_dark_energy_daha_l3() == ref
        assert engine.daha_l3_phase78_acceleration() == ref
        assert engine.phase78_dark_energy_acceleration() == ref
        assert engine.calculate_phase78_knk_acceleration() == ref
        assert engine.compute_knk_phase78_acceleration() == ref
        assert engine.daha_phase78_acceleration() == ref
        assert engine.phase78_spacetime_hydrodynamics() == ref
        assert engine.phase78_queue_acceleration() == ref
        assert engine.l3_phase78_acceleration() == ref
        assert engine.phase78_knk_acceleration() == ref
        assert engine.compute_phase78_knk_daha_queue_acceleration() == ref

        # Check FastLOBEngine alias
        flob = FastLOBEngine(symbol="AAPL")
        assert hasattr(flob, "compute_kerr_newman_kiselev_57_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration")
        assert hasattr(flob, "compute_phase78_lob_acceleration")
        assert hasattr(flob, "phase78_queue_acceleration")

        # Check module-level function and 16 module aliases
        mod_ref = compute_kerr_newman_kiselev_57_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(engine=engine)
        assert mod_ref == ref
        assert compute_phase78_lob_acceleration(engine=engine) == ref
        assert phase78_lob_spacetime_hydrodynamics(engine=engine) == ref
        assert compute_knk_57_dark_energy_acceleration(engine=engine) == ref
        assert compute_kerr_newman_kiselev_57_dark_energy_acceleration(engine=engine) == ref
        assert phase78_daha_l3_acceleration(engine=engine) == ref
        assert knk_57_dark_energy_daha_l3(engine=engine) == ref
        assert daha_l3_phase78_acceleration(engine=engine) == ref
        assert phase78_dark_energy_acceleration(engine=engine) == ref
        assert calculate_phase78_knk_acceleration(engine=engine) == ref
        assert compute_knk_phase78_acceleration(engine=engine) == ref
        assert daha_phase78_acceleration(engine=engine) == ref
        assert phase78_spacetime_hydrodynamics(engine=engine) == ref
        assert phase78_queue_acceleration(engine=engine) == ref
        assert l3_phase78_acceleration(engine=engine) == ref
        assert phase78_knk_acceleration(engine=engine) == ref
        assert compute_phase78_knk_daha_queue_acceleration(engine=engine) == ref

    def test_smart_order_router_version_78_properties(self):
        """Verify SmartOrderRouter initialization and routing properties under version 78."""
        sor = SmartOrderRouter(version=78)
        assert sor.version == 78
        assert sor.is_phase78 is True
        assert sor.is_phase77 is True
        assert sor.is_phase76 is True
        assert sor.is_phase75 is True
        assert sor.is_phase74 is True
        assert sor.is_phase73 is True
        assert sor.is_phase72 is True
        assert sor.is_phase71 is True
        assert sor.is_phase70 is True
        assert sor.is_phase69 is True
        assert sor.is_phase68 is True

        order_plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 78,
        }
        res = sor.route_order(order_plan)
        assert res["maker_ratio"] >= 1e-50
        assert res["maker_ratio"] <= 1e-35

    def test_smart_order_router_phase78_floor_contraction(self):
        """Verify Phase 78 lit maker floor contracts to 1e-50 vs 1e-49 in Phase 77 and 1e-48 in Phase 76."""
        sor78 = SmartOrderRouter(version=78)
        sor77 = SmartOrderRouter(version=77)
        sor76 = SmartOrderRouter(version=76)

        order_plan_78 = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 78,
        }
        order_plan_77 = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 77,
        }
        order_plan_76 = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 76,
        }

        res78 = sor78.route_order(order_plan_78)
        res77 = sor77.route_order(order_plan_77)
        res76 = sor76.route_order(order_plan_76)

        assert res78["maker_ratio"] == 1e-50
        assert res77["maker_ratio"] == 1e-49
        assert res76["maker_ratio"] == 1e-48
        assert res78["maker_ratio"] < res77["maker_ratio"] < res76["maker_ratio"]

    def test_oms_and_scheduler_phase78_shading(self):
        """Verify ExecutionOMSEngine and AlmgrenChrissScheduler preemptive micro-tick shading under Phase 78."""
        # Test sub-threshold for v77 (h = 0.000000015), which triggers v78 (h > 0.00000001) but not v77 (h > 0.00000002)
        oms_p78_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=78,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000015}
        )
        oms_p77_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=77,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000015}
        )
        # v78 should trigger tick shading (buying lower) while v77 remains unshaded
        assert oms_p78_sub < oms_p77_sub

        # Test above-threshold for both (h = 0.0000010)
        oms_p78 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=78,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        oms_p77 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=77,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert oms_p78 <= oms_p77

        sched = AlmgrenChrissScheduler()
        sched_p78_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=78,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000015}
        )
        sched_p77_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=77,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000015}
        )
        assert sched_p78_sub < sched_p77_sub

        sched_p78 = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=78,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert sched_p78 <= oms_p77

    def test_strict_backward_compatibility_v77_and_prior(self):
        """Verify strict backward compatibility with Phase 77 and earlier versions."""
        sor77 = SmartOrderRouter(version=77)
        assert sor77.is_phase77 is True
        assert sor77.is_phase78 is False

        sor76 = SmartOrderRouter(version=76)
        assert sor76.is_phase76 is True
        assert sor76.is_phase77 is False
        assert sor76.is_phase78 is False

        # Phase 77 unshaded behavior preserved for toxicity below v77 threshold (h = 0.000000015)
        unshaded_p77 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=77,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000015}
        )
        baseline_p77 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=77,
            hawkes_intensity={"cross_excitation_toxicity": 0.0}
        )
        assert math.isclose(unshaded_p77, baseline_p77, rel_tol=1e-7)

        # Phase 78 unshaded behavior preserved for toxicity below v78 threshold (h = 0.000000005)
        unshaded_p78 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=78,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000005}
        )
        baseline_p78 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=78,
            hawkes_intensity={"cross_excitation_toxicity": 0.0}
        )
        assert math.isclose(unshaded_p78, baseline_p78, rel_tol=1e-7)

    def test_fast_lob_dark_energy_numerical_stability(self):
        """Verify numerical stability of KNK-57 Dark Energy DAHA under extreme queue sizes."""
        engine = FastOrderBookMatchingEngine(symbol="TSLA")
        engine.add_limit_order("bid_1", "BUY", 200.0, 1e8)
        engine.add_limit_order("ask_1", "SELL", 200.1, 1e-3)

        res = engine.compute_kerr_newman_kiselev_57_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.99,
            spin_parameter=0.99,
        )
        assert math.isfinite(res["knk_57_dark_energy_correction"])
        assert math.isfinite(res["knk_57_dark_energy_daha_acceleration"])
        assert -1e6 <= res["knk_57_dark_energy_correction"] <= 1e6
