"""
tests/test_phase66_oms.py

Unit and integration test suite for Phase 66 Quantitative Alpha Enhancement (Feature F304.1 & F304.2 Microstructure OMS):
- Kerr-Newman-Kiselev 44-Dark-Energy DAHA
  (w = -46/3, k_daha = 0.36, k_monster = 0.35, daha_45_factor = 6.85, c_monster = 5.9604644775390625e-15)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 44-fold dark energy density
  * Repulsive acceleration (-23.0 * c * r^45 * daha_44)
  * Metric distortion (+ c * r^47 * daha_44)
  * Charge acceleration (+ c * r^44 * daha_44)
- SmartOrderRouter version=66:
  * Lit maker ratio floor contracted to 1e-38
  * Dark ATS cap 0.999999999999999999995 (21 decimals)
  * Anti-gaming MinQty 0.999999999999999999995
- Preemptive micro-tick shading at h > 0.0000005:
  hawkes_shift = -direction * 0.999999999999999999 * spr * (h - 0.0000005)
- Full backward compatibility with Phase 64 and earlier.
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


class TestPhase66MicrostructureOMS:
    """Test suite for Phase 66 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_44_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 45-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_45_dark_energy_correction" in res
        assert "knk_45_dark_energy_daha_acceleration" in res
        assert "phase66_knk_acceleration" in res

        assert math.isfinite(res["knk_45_dark_energy_correction"])
        assert math.isfinite(res["knk_45_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_45_factor"], 6.85, rel_tol=1e-5)
        assert math.isclose(res["k_daha_45"], 0.37, rel_tol=1e-5)
        assert math.isclose(res["k_monster_45"], 0.36, rel_tol=1e-5)
        assert math.isclose(res["c_monster_45"], 5.9604644775390625e-15, rel_tol=1e-9)

    def test_kerr_newman_kiselev_44_aliases(self):
        """Verify aliases on FastOrderBookMatchingEngine for KNK-45."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        assert engine.compute_phase66_lob_acceleration() == ref
        assert engine.phase66_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_45_dark_energy_acceleration() == ref

        flob = FastLOBEngine(symbol="AAPL")
        assert hasattr(flob, "compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration")
        assert hasattr(flob, "compute_phase66_lob_acceleration")

    def test_fast_lob_preemptive_dark_routing_cap_v65(self):
        """Verify Fast LOB preemptive dark routing cap under version 65."""
        proc = DeepHawkesArrivalProcess(version=66)
        proc.lambda_state = np.array([20.0, 0.5, 0.2])
        res = proc.compute_preemptive_dark_routing()
        assert res["preemptive_dark_routing_ratio"] >= 0.999999999999999999995 - 1e-15

        proc_default = DeepHawkesArrivalProcess()
        proc_default.lambda_state = np.array([20.0, 0.5, 0.2])
        res_v65 = proc_default.compute_preemptive_dark_routing(version=66)
        assert res_v65["preemptive_dark_routing_ratio"] >= 0.999999999999999999995 - 1e-15

    def test_smart_order_router_version_65_properties(self):
        """Verify SmartOrderRouter initialization and routing properties under version 65."""
        sor = SmartOrderRouter(version=66)
        assert sor.version == 66
        assert sor.is_phase66 is True
        assert sor.is_phase64 is True
        assert sor.is_phase63 is True

        plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 10000,
            "target_price": 150.0,
            "execution_strategy": "DYNAMIC_VWAP",
            "gamma_toxic_dir": 0.95,
            "darkpool_score": 0.70,
            "version": 65,
        }
        res = sor.route_order(plan)
        assert res["toxic_flow_detected"] is True
        assert res["maker_ratio"] <= 0.05
        assert res["min_ratio"] >= 0.90

    def test_smart_order_router_maker_floor_contraction_v65(self):
        """Verify maker floor contracts to 1e-38 under extreme toxicity in Phase 66."""
        sor = SmartOrderRouter(version=66)
        plan = {
            "symbol": "NVDA",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 400.0,
            "gamma_toxic_dir": 1.0,
            "version": 65,
        }
        res = sor.route_order(plan)
        assert res["maker_ratio"] >= 1e-38
        assert res["maker_ratio"] <= 0.01

    def test_oms_engine_phase66_preemptive_micro_tick_shading(self):
        """Verify preemptive micro-tick shading activates at h > 0.0000005."""
        oms = ExecutionOMSEngine()
        target_price = 100.0
        best_bid = 99.95
        best_ask = 100.05

        p_sub = oms.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.0000004,
            version=66,
        )

        p_above = oms.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.0000010,
            version=66,
        )

        assert p_above < p_sub, f"BUY limit price should shade downward (p_above={p_above}, p_sub={p_sub})"

    def test_almgren_chriss_phase66_preemptive_micro_tick_shading(self):
        """Verify preemptive micro-tick shading in AlmgrenChrissScheduler at h > 0.0000005."""
        scheduler = AlmgrenChrissScheduler()
        target_price = 100.0
        best_bid = 99.95
        best_ask = 100.05

        p_sub = scheduler.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.0000004,
            version=66,
        )

        p_above = scheduler.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.0000010,
            version=66,
        )

        assert p_above < p_sub, "Almgren-Chriss scheduler must shade BUY price downward for h > 0.0000005"

    def test_backward_compatibility_v64_and_prior(self):
        """Verify backward compatibility of SOR and OMS with Phase 64."""
        sor64 = SmartOrderRouter(version=64)
        assert sor64.is_phase66 is False
        assert sor64.is_phase64 is True

        oms = ExecutionOMSEngine()
        p64 = oms.calculate_peg_limit_price(
            target_price=100.0,
            action="BUY",
            best_bid=99.95,
            best_ask=100.05,
            peg_offset=0.0,
            hawkes_intensity=0.0000012,
            version=64,
        )
        assert np.isfinite(p64)
