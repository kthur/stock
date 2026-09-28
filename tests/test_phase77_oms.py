"""
tests/test_phase77_oms.py

Unit and integration test suite for Phase 77 Quantitative Alpha Enhancement (Feature F359.1 & F359.2 Microstructure OMS):
- Kerr-Newman-Kiselev 56-Dark-Energy DAHA
  (w = -58/3 ≈ -19.333333333333332, k_daha = 0.48, k_monster = 0.47, daha_56_factor = 9.60, c_monster = 3.469446951953614e-18 [2^-58])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 56-fold dark energy density
  * Repulsive acceleration -29.5 * c * (r ** 58) * daha_56_factor
  * Metric distortion & charge acceleration
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, and module level
- SmartOrderRouter version=77:
  * Lit maker ratio floor contracted to 1e-49
  * 49-decimal rounding precision for maker_ratio and min_ratio
  * Cascading version flags: is_phase77 -> is_phase76 -> is_phase75 -> is_phase74
- Preemptive micro-tick shading at h > 0.00000002:
  hawkes_shift = -direction * 0.999999999999999999999999999999 * spr * (h - 0.00000002)
- Dual-OMS parity across ExecutionOMSEngine and AlmgrenChrissScheduler
- Full backward compatibility with Phase 76 and earlier.
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    compute_kerr_newman_kiselev_56_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
    compute_phase77_lob_acceleration,
    phase77_lob_spacetime_hydrodynamics,
    compute_knk_56_dark_energy_acceleration,
    compute_kerr_newman_kiselev_56_dark_energy_acceleration,
    phase77_daha_l3_acceleration,
    knk_56_dark_energy_daha_l3,
    daha_l3_phase77_acceleration,
    phase77_dark_energy_acceleration,
    calculate_phase77_knk_acceleration,
    compute_knk_phase77_acceleration,
    daha_phase77_acceleration,
    phase77_spacetime_hydrodynamics,
    phase77_queue_acceleration,
    l3_phase77_acceleration,
    phase77_knk_acceleration,
    compute_phase77_knk_daha_queue_acceleration,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase77MicrostructureOMS:
    """Test suite for Phase 77 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_56_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 56-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_56_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_56_dark_energy_correction" in res
        assert "knk_56_dark_energy_daha_acceleration" in res
        assert "phase77_knk_acceleration" in res

        assert math.isfinite(res["knk_56_dark_energy_correction"])
        assert math.isfinite(res["knk_56_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_56_factor"], 9.60, rel_tol=1e-5)
        assert math.isclose(res["k_daha_56"], 0.48, rel_tol=1e-5)
        assert math.isclose(res["k_monster_56"], 0.47, rel_tol=1e-5)
        assert math.isclose(res["c_monster_56"], 3.469446951953614e-18, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_56"], -58.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_56_aliases(self):
        """Verify 16 method aliases on FastOrderBookMatchingEngine and module level for KNK-56."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_56_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        # Check all 16 class method aliases
        assert engine.compute_phase77_lob_acceleration() == ref
        assert engine.phase77_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_56_dark_energy_acceleration() == ref
        assert engine.compute_kerr_newman_kiselev_56_dark_energy_acceleration() == ref
        assert engine.phase77_daha_l3_acceleration() == ref
        assert engine.knk_56_dark_energy_daha_l3() == ref
        assert engine.daha_l3_phase77_acceleration() == ref
        assert engine.phase77_dark_energy_acceleration() == ref
        assert engine.calculate_phase77_knk_acceleration() == ref
        assert engine.compute_knk_phase77_acceleration() == ref
        assert engine.daha_phase77_acceleration() == ref
        assert engine.phase77_spacetime_hydrodynamics() == ref
        assert engine.phase77_queue_acceleration() == ref
        assert engine.l3_phase77_acceleration() == ref
        assert engine.phase77_knk_acceleration() == ref
        assert engine.compute_phase77_knk_daha_queue_acceleration() == ref

        # Check FastLOBEngine alias
        flob = FastLOBEngine(symbol="AAPL")
        assert hasattr(flob, "compute_kerr_newman_kiselev_56_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration")
        assert hasattr(flob, "compute_phase77_lob_acceleration")
        assert hasattr(flob, "phase77_queue_acceleration")

        # Check module-level function and 16 module aliases
        mod_ref = compute_kerr_newman_kiselev_56_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(engine=engine)
        assert mod_ref == ref
        assert compute_phase77_lob_acceleration(engine=engine) == ref
        assert phase77_lob_spacetime_hydrodynamics(engine=engine) == ref
        assert compute_knk_56_dark_energy_acceleration(engine=engine) == ref
        assert compute_kerr_newman_kiselev_56_dark_energy_acceleration(engine=engine) == ref
        assert phase77_daha_l3_acceleration(engine=engine) == ref
        assert knk_56_dark_energy_daha_l3(engine=engine) == ref
        assert daha_l3_phase77_acceleration(engine=engine) == ref
        assert phase77_dark_energy_acceleration(engine=engine) == ref
        assert calculate_phase77_knk_acceleration(engine=engine) == ref
        assert compute_knk_phase77_acceleration(engine=engine) == ref
        assert daha_phase77_acceleration(engine=engine) == ref
        assert phase77_spacetime_hydrodynamics(engine=engine) == ref
        assert phase77_queue_acceleration(engine=engine) == ref
        assert l3_phase77_acceleration(engine=engine) == ref
        assert phase77_knk_acceleration(engine=engine) == ref
        assert compute_phase77_knk_daha_queue_acceleration(engine=engine) == ref

    def test_smart_order_router_version_77_properties(self):
        """Verify SmartOrderRouter initialization and routing properties under version 77."""
        sor = SmartOrderRouter(version=77)
        assert sor.version == 77
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
            "version": 77,
        }
        res = sor.route_order(order_plan)
        assert res["maker_ratio"] >= 1e-49
        assert res["maker_ratio"] <= 1e-35

    def test_smart_order_router_phase77_floor_contraction(self):
        """Verify Phase 77 lit maker floor contracts to 1e-49 vs 1e-48 in Phase 76 and 1e-47 in Phase 75."""
        sor77 = SmartOrderRouter(version=77)
        sor76 = SmartOrderRouter(version=76)
        sor75 = SmartOrderRouter(version=75)

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
        order_plan_75 = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 75,
        }

        res77 = sor77.route_order(order_plan_77)
        res76 = sor76.route_order(order_plan_76)
        res75 = sor75.route_order(order_plan_75)

        assert res77["maker_ratio"] == 1e-49
        assert res76["maker_ratio"] == 1e-48
        assert res75["maker_ratio"] == 1e-47
        assert res77["maker_ratio"] < res76["maker_ratio"] < res75["maker_ratio"]

    def test_oms_and_scheduler_phase77_shading(self):
        """Verify ExecutionOMSEngine and AlmgrenChrissScheduler preemptive micro-tick shading under Phase 77."""
        # Test sub-threshold for v76 (h = 0.000000025), which triggers v77 (h > 0.00000002) but not v76 (h > 0.00000003)
        oms_p77_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=77,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000025}
        )
        oms_p76_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=76,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000025}
        )
        # v77 should trigger tick shading (buying lower) while v76 remains unshaded
        assert oms_p77_sub < oms_p76_sub

        # Test above-threshold for both (h = 0.0000010)
        oms_p77 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=77,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        oms_p76 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=76,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert oms_p77 <= oms_p76

        sched = AlmgrenChrissScheduler()
        sched_p77_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=77,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000025}
        )
        sched_p76_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=76,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000025}
        )
        assert sched_p77_sub < sched_p76_sub

        sched_p77 = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=77,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert sched_p77 <= oms_p76

    def test_strict_backward_compatibility_v76_and_prior(self):
        """Verify strict backward compatibility with Phase 76 and earlier versions."""
        sor76 = SmartOrderRouter(version=76)
        assert sor76.is_phase76 is True
        assert sor76.is_phase77 is False

        sor75 = SmartOrderRouter(version=75)
        assert sor75.is_phase75 is True
        assert sor75.is_phase76 is False
        assert sor75.is_phase77 is False

        sor74 = SmartOrderRouter(version=74)
        assert sor74.is_phase74 is True
        assert sor74.is_phase75 is False
        assert sor74.is_phase76 is False
        assert sor74.is_phase77 is False

        # Phase 76 unshaded behavior preserved for toxicity below v76 threshold (h = 0.000000025)
        unshaded_p76 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=76,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000025}
        )
        baseline_p76 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=76,
            hawkes_intensity={"cross_excitation_toxicity": 0.0}
        )
        assert math.isclose(unshaded_p76, baseline_p76, rel_tol=1e-7)

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

    def test_fast_lob_dark_energy_numerical_stability(self):
        """Verify numerical stability of KNK-56 Dark Energy DAHA under extreme queue sizes."""
        engine = FastOrderBookMatchingEngine(symbol="TSLA")
        engine.add_limit_order("bid_1", "BUY", 200.0, 1e8)
        engine.add_limit_order("ask_1", "SELL", 200.1, 1e-3)

        res = engine.compute_kerr_newman_kiselev_56_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.99,
            spin_parameter=0.99,
        )
        assert math.isfinite(res["knk_56_dark_energy_correction"])
        assert math.isfinite(res["knk_56_dark_energy_daha_acceleration"])
        assert -1e6 <= res["knk_56_dark_energy_correction"] <= 1e6
