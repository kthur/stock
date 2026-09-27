"""
tests/test_phase74_oms.py

Unit and integration test suite for Phase 74 Quantitative Alpha Enhancement (Feature F344.1 & F344.2 Microstructure OMS):
- Kerr-Newman-Kiselev 53-Dark-Energy DAHA
  (w = -55/3 = -18.333333333333332, k_daha = 0.45, k_monster = 0.44, daha_53_factor = 8.85, c_monster = 2.7755575615628914e-17 [2^-55])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 53-fold dark energy density
  * Repulsive acceleration -27.5 * c * (r ** 55) * daha_53_factor
  * Metric distortion
  * Charge acceleration
  * Method aliases on FastOrderBookMatchingEngine and FastLOBEngine
- SmartOrderRouter version=74:
  * Lit maker ratio floor contracted to 1e-46
  * 46-decimal rounding precision for maker_ratio and min_ratio
  * Cascading version flags: is_phase74 -> is_phase73 -> is_phase72
- Preemptive micro-tick shading at h > 0.00000005:
  hawkes_shift = -direction * 0.999999999999999999999999999 * spr * (h - 0.00000005)
- Full backward compatibility with Phase 73 and earlier.
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


class TestPhase74MicrostructureOMS:
    """Test suite for Phase 74 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_53_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 53-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_53_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_53_dark_energy_correction" in res
        assert "knk_53_dark_energy_daha_acceleration" in res
        assert "phase74_knk_acceleration" in res

        assert math.isfinite(res["knk_53_dark_energy_correction"])
        assert math.isfinite(res["knk_53_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_53_factor"], 8.85, rel_tol=1e-5)
        assert math.isclose(res["k_daha_53"], 0.45, rel_tol=1e-5)
        assert math.isclose(res["k_monster_53"], 0.44, rel_tol=1e-5)
        assert math.isclose(res["c_monster_53"], 2.7755575615628914e-17, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_53"], -55.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_53_aliases(self):
        """Verify aliases on FastOrderBookMatchingEngine for KNK-53."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_53_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        assert engine.compute_phase74_lob_acceleration() == ref
        assert engine.phase74_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_53_dark_energy_acceleration() == ref
        assert engine.compute_kerr_newman_kiselev_53_dark_energy_acceleration() == ref
        assert engine.phase74_daha_l3_acceleration() == ref
        assert engine.knk_53_dark_energy_daha_l3() == ref
        assert engine.daha_l3_phase74_acceleration() == ref
        assert engine.phase74_dark_energy_acceleration() == ref
        assert engine.calculate_phase74_knk_acceleration() == ref
        assert engine.compute_knk_phase74_acceleration() == ref
        assert engine.daha_phase74_acceleration() == ref
        assert engine.phase74_spacetime_hydrodynamics() == ref
        assert engine.phase74_queue_acceleration() == ref
        assert engine.l3_phase74_acceleration() == ref
        assert engine.phase74_knk_acceleration() == ref
        assert engine.compute_phase74_knk_daha_queue_acceleration() == ref

        flob = FastLOBEngine(symbol="AAPL")
        assert hasattr(flob, "compute_kerr_newman_kiselev_53_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration")
        assert hasattr(flob, "compute_phase74_lob_acceleration")
        assert hasattr(flob, "phase74_queue_acceleration")

    def test_smart_order_router_version_74_properties(self):
        """Verify SmartOrderRouter initialization and routing properties under version 74."""
        sor = SmartOrderRouter(version=74)
        assert sor.version == 74
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
            "version": 74,
        }
        res = sor.route_order(order_plan)
        assert res["maker_ratio"] >= 1e-46
        assert res["maker_ratio"] <= 1e-35

    def test_smart_order_router_phase74_floor_contraction(self):
        """Verify Phase 74 lit maker floor contracts to 1e-46 vs 1e-45 in Phase 73."""
        sor74 = SmartOrderRouter(version=74)
        sor73 = SmartOrderRouter(version=73)

        order_plan_74 = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 74,
        }
        order_plan_73 = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 73,
        }

        res74 = sor74.route_order(order_plan_74)
        res73 = sor73.route_order(order_plan_73)

        assert res74["maker_ratio"] == 1e-46
        assert res73["maker_ratio"] == 1e-45
        assert res74["maker_ratio"] < res73["maker_ratio"]

    def test_oms_and_scheduler_phase74_shading(self):
        """Verify ExecutionOMSEngine and AlmgrenChrissScheduler preemptive micro-tick shading under Phase 74."""
        # Test sub-threshold for v73 (h = 0.000000055), which triggers v74 (h > 0.00000005)
        oms_p74_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=74,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000055}
        )
        oms_p73_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=73,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000055}
        )
        # v74 should trigger tick shading (buying lower) while v73 remains unshaded
        assert oms_p74_sub < oms_p73_sub

        # Test above-threshold for both (h = 0.0000010)
        oms_p74 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=74,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        oms_p73 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=73,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert oms_p74 <= oms_p73

        sched = AlmgrenChrissScheduler()
        sched_p74_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=74,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000055}
        )
        sched_p73_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=73,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000055}
        )
        assert sched_p74_sub < sched_p73_sub

        sched_p74 = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=74,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert sched_p74 <= oms_p73

    def test_strict_backward_compatibility_v73_and_prior(self):
        """Verify strict backward compatibility with Phase 73 and earlier versions."""
        sor73 = SmartOrderRouter(version=73)
        assert sor73.is_phase73 is True
        assert sor73.is_phase74 is False

        sor72 = SmartOrderRouter(version=72)
        assert sor72.is_phase72 is True
        assert sor72.is_phase73 is False
        assert sor72.is_phase74 is False

        sor71 = SmartOrderRouter(version=71)
        assert sor71.is_phase71 is True
        assert sor71.is_phase72 is False
        assert sor71.is_phase73 is False
        assert sor71.is_phase74 is False

        # Phase 73 unshaded behavior preserved
        unshaded_p73 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=73,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000055}
        )
        baseline_p73 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=73,
            hawkes_intensity={"cross_excitation_toxicity": 0.0}
        )
        assert math.isclose(unshaded_p73, baseline_p73, rel_tol=1e-7)

    def test_fast_lob_dark_energy_numerical_stability(self):
        """Verify numerical stability of KNK-53 Dark Energy DAHA under extreme queue sizes."""
        engine = FastOrderBookMatchingEngine(symbol="TSLA")
        engine.add_limit_order("bid_1", "BUY", 200.0, 1e8)
        engine.add_limit_order("ask_1", "SELL", 200.1, 1e-3)

        res = engine.compute_kerr_newman_kiselev_53_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.99,
            spin_parameter=0.99,
        )
        assert math.isfinite(res["knk_53_dark_energy_correction"])
        assert math.isfinite(res["knk_53_dark_energy_daha_acceleration"])
        assert -1e6 <= res["knk_53_dark_energy_correction"] <= 1e6
