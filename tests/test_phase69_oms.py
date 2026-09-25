"""
tests/test_phase69_oms.py

Unit and integration test suite for Phase 69 Quantitative Alpha Enhancement (Feature F319.1 & F319.2 Microstructure OMS):
- Kerr-Newman-Kiselev 48-Dark-Energy DAHA
  (w = -50/3, k_daha = 0.40, k_monster = 0.39, daha_48_factor = 7.60, c_monster = 8.881784197001252e-16)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 48-fold dark energy density
  * Repulsive acceleration -25.0 * c * (r ** 50) * daha_48_factor
  * Metric distortion
  * Charge acceleration
- SmartOrderRouter version=69:
  * Lit maker ratio floor contracted to 1e-41
  * Dark ATS cap 0.9999999999999999999995 (22 decimals)
  * Anti-gaming MinQty 0.9999999999999999999995
- Preemptive micro-tick shading at h > 0.0000002:
  hawkes_shift = -direction * 0.9999999999999999999999 * spr * (h - 0.0000002)
- Full backward compatibility with Phase 68 and earlier.
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


class TestPhase69MicrostructureOMS:
    """Test suite for Phase 69 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_48_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 48-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_48_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_48_dark_energy_correction" in res
        assert "knk_48_dark_energy_daha_acceleration" in res
        assert "phase69_knk_acceleration" in res

        assert math.isfinite(res["knk_48_dark_energy_correction"])
        assert math.isfinite(res["knk_48_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_48_factor"], 7.60, rel_tol=1e-5)
        assert math.isclose(res["k_daha_48"], 0.40, rel_tol=1e-5)
        assert math.isclose(res["k_monster_48"], 0.39, rel_tol=1e-5)
        assert math.isclose(res["c_monster_48"], 8.881784197001252e-16, rel_tol=1e-9)

    def test_kerr_newman_kiselev_48_aliases(self):
        """Verify aliases on FastOrderBookMatchingEngine for KNK-48."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_48_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        assert engine.compute_phase69_lob_acceleration() == ref
        assert engine.phase69_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_48_dark_energy_acceleration() == ref

        flob = FastLOBEngine(symbol="AAPL")
        assert hasattr(flob, "compute_kerr_newman_kiselev_48_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration")
        assert hasattr(flob, "compute_phase69_lob_acceleration")

    def test_fast_lob_preemptive_dark_routing_cap_v69(self):
        """Verify Fast LOB preemptive dark routing cap under version 69."""
        proc = DeepHawkesArrivalProcess(version=69)
        proc.lambda_state = np.array([20.0, 0.5, 0.2])
        res = proc.compute_preemptive_dark_routing()
        assert res["preemptive_dark_routing_ratio"] >= 0.9999999999999999999995 - 1e-15

        proc_default = DeepHawkesArrivalProcess()
        proc_default.lambda_state = np.array([20.0, 0.5, 0.2])
        res_v69 = proc_default.compute_preemptive_dark_routing(version=69)
        assert res_v69["preemptive_dark_routing_ratio"] >= 0.9999999999999999999995 - 1e-15

    def test_smart_order_router_version_69_properties(self):
        """Verify SmartOrderRouter initialization and routing properties under version 69."""
        sor = SmartOrderRouter(version=69)
        assert sor.version == 69
        assert sor.is_phase69 is True
        assert sor.is_phase68 is True
        assert sor.is_phase67 is True
        assert sor.is_phase66 is True

        order_plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 69,
        }
        res = sor.route_order(order_plan)
        assert res["maker_ratio"] >= 1e-41
        assert res["maker_ratio"] <= 1e-35

    def test_oms_and_scheduler_phase69_shading(self):
        """Verify ExecutionOMSEngine and AlmgrenChrissScheduler preemptive micro-tick shading under Phase 69."""
        oms_p69 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=69,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        oms_p68 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=68,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert oms_p69 <= oms_p68

        sched = AlmgrenChrissScheduler()
        sched_p69 = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=69,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert sched_p69 <= oms_p68

    def test_strict_backward_compatibility_v68_and_prior(self):
        """Verify strict backward compatibility with Phase 68 and earlier versions."""
        sor68 = SmartOrderRouter(version=68)
        assert sor68.is_phase68 is True
        assert sor68.is_phase69 is False

        sor67 = SmartOrderRouter(version=67)
        assert sor67.is_phase67 is True
        assert sor67.is_phase68 is False
        assert sor67.is_phase69 is False
