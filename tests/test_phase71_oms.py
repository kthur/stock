"""
tests/test_phase71_oms.py

Unit and integration test suite for Phase 71 Quantitative Alpha Enhancement (Feature F329.1 & F329.2 Microstructure OMS):
- Kerr-Newman-Kiselev 50-Dark-Energy DAHA
  (w = -52/3, k_daha = 0.42, k_monster = 0.41, daha_50_factor = 8.10, c_monster = 2.220446049250313e-16)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 50-fold dark energy density
  * Repulsive acceleration -26.5 * c * (r ** 52) * daha_50_factor
  * Metric distortion
  * Charge acceleration
- SmartOrderRouter version=71:
  * Lit maker ratio floor contracted to 1e-43
  * Dark ATS cap 0.999999999999999999999995 (24 decimals)
  * Anti-gaming MinQty 0.999999999999999999999995
- Preemptive micro-tick shading at h > 0.00000010:
  hawkes_shift = -direction * 0.999999999999999999999999 * spr * (h - 0.00000010)
- Full backward compatibility with Phase 70 and earlier.
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


class TestPhase71MicrostructureOMS:
    """Test suite for Phase 71 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_50_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 50-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_50_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_50_dark_energy_correction" in res
        assert "knk_50_dark_energy_daha_acceleration" in res
        assert "phase71_knk_acceleration" in res

        assert math.isfinite(res["knk_50_dark_energy_correction"])
        assert math.isfinite(res["knk_50_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_50_factor"], 8.10, rel_tol=1e-5)
        assert math.isclose(res["k_daha_50"], 0.42, rel_tol=1e-5)
        assert math.isclose(res["k_monster_50"], 0.41, rel_tol=1e-5)
        assert math.isclose(res["c_monster_50"], 2.220446049250313e-16, rel_tol=1e-9)

    def test_kerr_newman_kiselev_50_aliases(self):
        """Verify aliases on FastOrderBookMatchingEngine for KNK-50."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_50_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        assert engine.compute_phase71_lob_acceleration() == ref
        assert engine.phase71_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_50_dark_energy_acceleration() == ref

        flob = FastLOBEngine(symbol="AAPL")
        assert hasattr(flob, "compute_kerr_newman_kiselev_50_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration")
        assert hasattr(flob, "compute_phase71_lob_acceleration")

    def test_fast_lob_preemptive_dark_routing_cap_v71(self):
        """Verify Fast LOB preemptive dark routing cap under version 71."""
        proc = DeepHawkesArrivalProcess(version=71)
        proc.lambda_state = np.array([20.0, 0.5, 0.2])
        res = proc.compute_preemptive_dark_routing()
        assert res["preemptive_dark_routing_ratio"] >= 0.999999999999999999999995 - 1e-15

        proc_default = DeepHawkesArrivalProcess()
        proc_default.lambda_state = np.array([20.0, 0.5, 0.2])
        res_v71 = proc_default.compute_preemptive_dark_routing(version=71)
        assert res_v71["preemptive_dark_routing_ratio"] >= 0.999999999999999999999995 - 1e-15

    def test_smart_order_router_version_71_properties(self):
        """Verify SmartOrderRouter initialization and routing properties under version 71."""
        sor = SmartOrderRouter(version=71)
        assert sor.version == 71
        assert sor.is_phase71 is True
        assert sor.is_phase70 is True
        assert sor.is_phase69 is True
        assert sor.is_phase68 is True
        assert sor.is_phase67 is True

        order_plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 71,
        }
        res = sor.route_order(order_plan)
        assert res["maker_ratio"] >= 1e-43
        assert res["maker_ratio"] <= 1e-35

    def test_oms_and_scheduler_phase71_shading(self):
        """Verify ExecutionOMSEngine and AlmgrenChrissScheduler preemptive micro-tick shading under Phase 71."""
        oms_p71 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=71,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        oms_p70 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=70,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert oms_p71 <= oms_p70

        sched = AlmgrenChrissScheduler()
        sched_p71 = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=71,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert sched_p71 <= oms_p70

    def test_strict_backward_compatibility_v70_and_prior(self):
        """Verify strict backward compatibility with Phase 70 and earlier versions."""
        sor70 = SmartOrderRouter(version=70)
        assert sor70.is_phase70 is True
        assert sor70.is_phase71 is False

        sor69 = SmartOrderRouter(version=69)
        assert sor69.is_phase69 is True
        assert sor69.is_phase70 is False
        assert sor69.is_phase71 is False
