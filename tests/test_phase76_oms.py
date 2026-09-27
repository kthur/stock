"""
tests/test_phase76_oms.py

Unit and integration test suite for Phase 76 Quantitative Alpha Enhancement (Feature F354.1 & F354.2 Microstructure OMS):
- Kerr-Newman-Kiselev 55-Dark-Energy DAHA
  (w = -57/3 = -19.0, k_daha = 0.47, k_monster = 0.46, daha_55_factor = 9.35, c_monster = 6.938893903907228e-18 [2^-57])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 55-fold dark energy density
  * Repulsive acceleration -29.0 * c * (r ** 57) * daha_55_factor
  * Metric distortion
  * Charge acceleration
  * Method aliases on FastOrderBookMatchingEngine and FastLOBEngine
- SmartOrderRouter version=76:
  * Lit maker ratio floor contracted to 1e-48
  * 48-decimal rounding precision for maker_ratio and min_ratio
  * Cascading version flags: is_phase76 -> is_phase75 -> is_phase74 -> is_phase73
- Preemptive micro-tick shading at h > 0.00000003:
  hawkes_shift = -direction * 0.99999999999999999999999999999 * spr * (h - 0.00000003)
- Full backward compatibility with Phase 75 and earlier.
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


class TestPhase76MicrostructureOMS:
    """Test suite for Phase 76 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_55_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 55-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_55_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_55_dark_energy_correction" in res
        assert "knk_55_dark_energy_daha_acceleration" in res
        assert "phase76_knk_acceleration" in res

        assert math.isfinite(res["knk_55_dark_energy_correction"])
        assert math.isfinite(res["knk_55_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_55_factor"], 9.35, rel_tol=1e-5)
        assert math.isclose(res["k_daha_55"], 0.47, rel_tol=1e-5)
        assert math.isclose(res["k_monster_55"], 0.46, rel_tol=1e-5)
        assert math.isclose(res["c_monster_55"], 6.938893903907228e-18, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_55"], -57.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_55_aliases(self):
        """Verify aliases on FastOrderBookMatchingEngine for KNK-55."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_55_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        assert engine.compute_phase76_lob_acceleration() == ref
        assert engine.phase76_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_55_dark_energy_acceleration() == ref
        assert engine.compute_kerr_newman_kiselev_55_dark_energy_acceleration() == ref
        assert engine.phase76_daha_l3_acceleration() == ref
        assert engine.knk_55_dark_energy_daha_l3() == ref
        assert engine.daha_l3_phase76_acceleration() == ref
        assert engine.phase76_dark_energy_acceleration() == ref
        assert engine.calculate_phase76_knk_acceleration() == ref
        assert engine.compute_knk_phase76_acceleration() == ref
        assert engine.daha_phase76_acceleration() == ref
        assert engine.phase76_spacetime_hydrodynamics() == ref
        assert engine.phase76_queue_acceleration() == ref
        assert engine.l3_phase76_acceleration() == ref
        assert engine.phase76_knk_acceleration() == ref
        assert engine.compute_phase76_knk_daha_queue_acceleration() == ref

        flob = FastLOBEngine(symbol="AAPL")
        assert hasattr(flob, "compute_kerr_newman_kiselev_55_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration")
        assert hasattr(flob, "compute_phase76_lob_acceleration")
        assert hasattr(flob, "phase76_queue_acceleration")

    def test_smart_order_router_version_76_properties(self):
        """Verify SmartOrderRouter initialization and routing properties under version 76."""
        sor = SmartOrderRouter(version=76)
        assert sor.version == 76
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
            "version": 76,
        }
        res = sor.route_order(order_plan)
        assert res["maker_ratio"] >= 1e-48
        assert res["maker_ratio"] <= 1e-35

    def test_smart_order_router_phase76_floor_contraction(self):
        """Verify Phase 76 lit maker floor contracts to 1e-48 vs 1e-47 in Phase 75."""
        sor76 = SmartOrderRouter(version=76)
        sor75 = SmartOrderRouter(version=75)

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

        res76 = sor76.route_order(order_plan_76)
        res75 = sor75.route_order(order_plan_75)

        assert res76["maker_ratio"] == 1e-48
        assert res75["maker_ratio"] == 1e-47
        assert res76["maker_ratio"] < res75["maker_ratio"]

    def test_oms_and_scheduler_phase76_shading(self):
        """Verify ExecutionOMSEngine and AlmgrenChrissScheduler preemptive micro-tick shading under Phase 76."""
        # Test sub-threshold for v75 (h = 0.000000035), which triggers v76 (h > 0.00000003)
        oms_p76_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=76,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000035}
        )
        oms_p75_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=75,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000035}
        )
        # v76 should trigger tick shading (buying lower) while v75 remains unshaded
        assert oms_p76_sub < oms_p75_sub

        # Test above-threshold for both (h = 0.0000010)
        oms_p76 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=76,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        oms_p75 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=75,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert oms_p76 <= oms_p75

        sched = AlmgrenChrissScheduler()
        sched_p76_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=76,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000035}
        )
        sched_p75_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=75,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000035}
        )
        assert sched_p76_sub < sched_p75_sub

        sched_p76 = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=76,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert sched_p76 <= oms_p75

    def test_strict_backward_compatibility_v75_and_prior(self):
        """Verify strict backward compatibility with Phase 75 and earlier versions."""
        sor75 = SmartOrderRouter(version=75)
        assert sor75.is_phase75 is True
        assert sor75.is_phase76 is False

        sor74 = SmartOrderRouter(version=74)
        assert sor74.is_phase74 is True
        assert sor74.is_phase75 is False
        assert sor74.is_phase76 is False

        sor73 = SmartOrderRouter(version=73)
        assert sor73.is_phase73 is True
        assert sor73.is_phase74 is False
        assert sor73.is_phase75 is False
        assert sor73.is_phase76 is False

        # Phase 75 unshaded behavior preserved for toxicity below v75 threshold
        unshaded_p75 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=75,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000035}
        )
        baseline_p75 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=75,
            hawkes_intensity={"cross_excitation_toxicity": 0.0}
        )
        assert math.isclose(unshaded_p75, baseline_p75, rel_tol=1e-7)

    def test_fast_lob_dark_energy_numerical_stability(self):
        """Verify numerical stability of KNK-55 Dark Energy DAHA under extreme queue sizes."""
        engine = FastOrderBookMatchingEngine(symbol="TSLA")
        engine.add_limit_order("bid_1", "BUY", 200.0, 1e8)
        engine.add_limit_order("ask_1", "SELL", 200.1, 1e-3)

        res = engine.compute_kerr_newman_kiselev_55_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.99,
            spin_parameter=0.99,
        )
        assert math.isfinite(res["knk_55_dark_energy_correction"])
        assert math.isfinite(res["knk_55_dark_energy_daha_acceleration"])
        assert -1e6 <= res["knk_55_dark_energy_correction"] <= 1e6
