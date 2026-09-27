"""
tests/test_phase75_oms.py

Unit and integration test suite for Phase 75 Quantitative Alpha Enhancement (Feature F349.1 & F349.2 Microstructure OMS):
- Kerr-Newman-Kiselev 54-Dark-Energy DAHA
  (w = -56/3 = -18.666666666666668, k_daha = 0.46, k_monster = 0.45, daha_54_factor = 9.10, c_monster = 1.3877787807814457e-17 [2^-56])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 54-fold dark energy density
  * Repulsive acceleration -28.5 * c * (r ** 56) * daha_54_factor
  * Metric distortion
  * Charge acceleration
  * Method aliases on FastOrderBookMatchingEngine and FastLOBEngine
- SmartOrderRouter version=75:
  * Lit maker ratio floor contracted to 1e-47
  * 47-decimal rounding precision for maker_ratio and min_ratio
  * Cascading version flags: is_phase75 -> is_phase74 -> is_phase73
- Preemptive micro-tick shading at h > 0.00000004:
  hawkes_shift = -direction * 0.9999999999999999999999999999 * spr * (h - 0.00000004)
- Full backward compatibility with Phase 74 and earlier.
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    DeepHawkesArrivalProcess,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase75MicrostructureOMS:
    """Test suite for Phase 75 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_54_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 54-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_54_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_54_dark_energy_correction" in res
        assert "knk_54_dark_energy_daha_acceleration" in res
        assert "phase75_knk_acceleration" in res

        assert math.isfinite(res["knk_54_dark_energy_correction"])
        assert math.isfinite(res["knk_54_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_54_factor"], 9.10, rel_tol=1e-5)
        assert math.isclose(res["k_daha_54"], 0.46, rel_tol=1e-5)
        assert math.isclose(res["k_monster_54"], 0.45, rel_tol=1e-5)
        assert math.isclose(res["c_monster_54"], 1.3877787807814457e-17, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_54"], -56.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_54_aliases(self):
        """Verify aliases on FastOrderBookMatchingEngine for KNK-54."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_54_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        assert engine.compute_phase75_lob_acceleration() == ref
        assert engine.phase75_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_54_dark_energy_acceleration() == ref
        assert engine.compute_kerr_newman_kiselev_54_dark_energy_acceleration() == ref
        assert engine.phase75_daha_l3_acceleration() == ref
        assert engine.knk_54_dark_energy_daha_l3() == ref
        assert engine.daha_l3_phase75_acceleration() == ref
        assert engine.phase75_dark_energy_acceleration() == ref
        assert engine.calculate_phase75_knk_acceleration() == ref
        assert engine.compute_knk_phase75_acceleration() == ref
        assert engine.daha_phase75_acceleration() == ref
        assert engine.phase75_spacetime_hydrodynamics() == ref
        assert engine.phase75_queue_acceleration() == ref
        assert engine.l3_phase75_acceleration() == ref
        assert engine.phase75_knk_acceleration() == ref
        assert engine.compute_phase75_knk_daha_queue_acceleration() == ref

        flob = FastLOBEngine(symbol="AAPL")
        assert hasattr(flob, "compute_kerr_newman_kiselev_54_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration")
        assert hasattr(flob, "compute_phase75_lob_acceleration")
        assert hasattr(flob, "phase75_queue_acceleration")

    def test_smart_order_router_version_75_properties(self):
        """Verify SmartOrderRouter initialization and routing properties under version 75."""
        sor = SmartOrderRouter(version=75)
        assert sor.version == 75
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
            "version": 75,
        }
        res = sor.route_order(order_plan)
        assert res["maker_ratio"] >= 1e-47
        assert res["maker_ratio"] <= 1e-35

    def test_smart_order_router_phase75_floor_contraction(self):
        """Verify Phase 75 lit maker floor contracts to 1e-47 vs 1e-46 in Phase 74."""
        sor75 = SmartOrderRouter(version=75)
        sor74 = SmartOrderRouter(version=74)

        order_plan_75 = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 75,
        }
        order_plan_74 = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 74,
        }

        res75 = sor75.route_order(order_plan_75)
        res74 = sor74.route_order(order_plan_74)

        assert res75["maker_ratio"] == 1e-47
        assert res74["maker_ratio"] == 1e-46
        assert res75["maker_ratio"] < res74["maker_ratio"]

    def test_oms_and_scheduler_phase75_shading(self):
        """Verify ExecutionOMSEngine and AlmgrenChrissScheduler preemptive micro-tick shading under Phase 75."""
        # Test sub-threshold for v74 (h = 0.000000045), which triggers v75 (h > 0.00000004)
        oms_p75_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=75,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000045}
        )
        oms_p74_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=74,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000045}
        )
        # v75 should trigger tick shading (buying lower) while v74 remains unshaded
        assert oms_p75_sub < oms_p74_sub

        # Test above-threshold for both (h = 0.0000010)
        oms_p75 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=75,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        oms_p74 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=74,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert oms_p75 <= oms_p74

        sched = AlmgrenChrissScheduler()
        sched_p75_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=75,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000045}
        )
        sched_p74_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=74,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000045}
        )
        assert sched_p75_sub < sched_p74_sub

        sched_p75 = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=75,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert sched_p75 <= oms_p74

    def test_strict_backward_compatibility_v74_and_prior(self):
        """Verify strict backward compatibility with Phase 74 and earlier versions."""
        sor74 = SmartOrderRouter(version=74)
        assert sor74.is_phase74 is True
        assert sor74.is_phase75 is False

        sor73 = SmartOrderRouter(version=73)
        assert sor73.is_phase73 is True
        assert sor73.is_phase74 is False
        assert sor73.is_phase75 is False

        sor72 = SmartOrderRouter(version=72)
        assert sor72.is_phase72 is True
        assert sor72.is_phase73 is False
        assert sor72.is_phase74 is False
        assert sor72.is_phase75 is False

        # Phase 74 unshaded behavior preserved for toxicity below v74 threshold
        unshaded_p74 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=74,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000045}
        )
        baseline_p74 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=74,
            hawkes_intensity={"cross_excitation_toxicity": 0.0}
        )
        assert math.isclose(unshaded_p74, baseline_p74, rel_tol=1e-7)

    def test_fast_lob_dark_energy_numerical_stability(self):
        """Verify numerical stability of KNK-54 Dark Energy DAHA under extreme queue sizes."""
        engine = FastOrderBookMatchingEngine(symbol="TSLA")
        engine.add_limit_order("bid_1", "BUY", 200.0, 1e8)
        engine.add_limit_order("ask_1", "SELL", 200.1, 1e-3)

        res = engine.compute_kerr_newman_kiselev_54_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.99,
            spin_parameter=0.99,
        )
        assert math.isfinite(res["knk_54_dark_energy_correction"])
        assert math.isfinite(res["knk_54_dark_energy_daha_acceleration"])
        assert -1e6 <= res["knk_54_dark_energy_correction"] <= 1e6
