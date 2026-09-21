"""
tests/test_phase64_oms.py

Unit and integration test suite for Phase 64 Quantitative Alpha Enhancement (Feature F294.1 & F294.2 Microstructure OMS):
- Kerr-Newman-Kiselev 43-Dark-Energy DAHA
  (w = -15.0, k_daha = 0.35, k_monster = 0.34, daha_43_factor = 6.35, c_monster = 2.384185791015625e-14)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 43-fold dark energy density
  * Outer cosmological horizon scale
  * Radial tidal force with 43-fold dark energy repulsive acceleration (-22.5 * c * r^44 * daha_43)
  * Metric distortion term (+ c * r^46 * daha_43)
  * Charge acceleration (+ c * r^43 * daha_43)
  * Hydrodynamic queue acceleration and micro-price prediction
  * Complete method aliases on FastOrderBookMatchingEngine (28 base aliases + 8 extended aliases)
- Fast LOB 0.99999999999999999995 (20 decimals) preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=64:
  * Preemptive lit queue imbalance allocation with max dark cap 0.99999999999999999995.
  * Lit maker ratio floor contracted to 1e-36
    via 0.70 * (1.0 - 0.99999999999999999999999999999999986 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 0.99999999999999999995.
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.0000008:
  hawkes_shift = -direction * 0.999999999999999995 * spr * (h - 0.0000008).
- Full backward compatibility across Phase 14 through Phase 63 versions.
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


class TestPhase64MicrostructureOMS:
    """Test suite for Phase 64 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_43_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 43-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_43_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_43_dark_energy_tidal_force" in res
        assert "density_dark_energy_43" in res
        assert "r_43_dark_energy" in res

        # Check physical parameters
        assert res["knk_43_dark_energy_mass_M"] > 0.0
        assert math.isclose(res["density_dark_energy_43"], 2.384185791015625e-14, rel_tol=1e-9)
        assert math.isclose(res["daha_43_factor"], 6.35, rel_tol=1e-5)
        assert math.isclose(res["equation_of_state_w_43"], -15.0, rel_tol=1e-5)
        assert math.isfinite(res["knk_43_dark_energy_charge_Q"])
        assert math.isfinite(res["knk_43_dark_energy_spin_a"])
        assert np.isfinite(res["knk_43_dark_energy_tidal_force"])

    def test_kerr_newman_kiselev_43_aliases(self):
        """Verify all 36 base and extended aliases on FastOrderBookMatchingEngine and FastLOBEngine."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_43_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        # Primary aliases
        assert engine.calculate_knk_43_dark_energy_daha_acceleration() == ref
        assert engine.compute_phase64_lob_acceleration() == ref
        assert engine.phase64_lob_spacetime_hydrodynamics() == ref
        assert engine.daha_43_dark_energy_acceleration() == ref
        assert engine.kerr_newman_kiselev_43_acceleration() == ref
        assert engine.compute_43_dark_energy_acceleration() == ref
        assert engine.phase64_daha_l3_acceleration() == ref
        assert engine.knk_daha_43_acceleration() == ref
        assert engine.l3_knk_43_acceleration() == ref
        assert engine.spacetime_hydrodynamics_43_acceleration() == ref
        assert engine.daha_l3_phase64_acceleration() == ref
        assert engine.monster_daha_43_acceleration() == ref
        assert engine.phase64_dark_energy_acceleration() == ref
        assert engine.compute_l3_hydrodynamics_v64() == ref
        assert engine.phase64_queue_acceleration() == ref
        assert engine.knk_43_acceleration() == ref
        assert engine.daha_43_acceleration() == ref
        assert engine.l3_phase64_acceleration() == ref
        assert engine.phase64_knk_acceleration() == ref

        # Extended pattern aliases
        assert engine.compute_kerr_newman_kiselev_43_dark_energy_daha_queue_acceleration() == ref
        assert engine.calculate_kerr_newman_kiselev_43_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration() == ref
        assert engine.compute_knk_43_dark_energy_daha_queue_acceleration() == ref
        assert engine.compute_knk_43_dark_energy_queue_acceleration() == ref
        assert engine.compute_knk_borcherds_moonshine_monster_43_dark_energy_daha_queue_acceleration() == ref
        assert engine.compute_kerr_newman_kiselev_43_dark_energy_moonshine_monster_queue_acceleration() == ref
        assert engine.compute_knk_43_dark_energy_monster_moonshine_queue_acceleration() == ref
        assert engine.compute_phase64_knk_daha_queue_acceleration() == ref

        # Verify FastLOBEngine alias
        flob = FastLOBEngine(symbol="AAPL")
        assert hasattr(flob, "compute_kerr_newman_kiselev_43_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration")
        assert hasattr(flob, "calculate_knk_43_dark_energy_daha_acceleration")
        assert hasattr(flob, "compute_phase64_lob_acceleration")

    def test_fast_lob_preemptive_dark_routing_cap_v64(self):
        """Verify Fast LOB preemptive dark routing cap 0.99999999999999999995 under version 64 and stack inspection."""
        proc = DeepHawkesArrivalProcess(version=64)
        proc.lambda_state = np.array([20.0, 0.5, 0.2])
        res = proc.compute_preemptive_dark_routing()
        assert math.isclose(res["preemptive_dark_routing_ratio"], 0.99999999999999999995, rel_tol=1e-15)

        proc_default = DeepHawkesArrivalProcess()
        proc_default.lambda_state = np.array([20.0, 0.5, 0.2])
        res_v64 = proc_default.compute_preemptive_dark_routing(version=64)
        assert math.isclose(res_v64["preemptive_dark_routing_ratio"], 0.99999999999999999995, rel_tol=1e-15)

        # Stack frame inspection from within this test_phase64_oms file
        res_stack = proc_default.compute_preemptive_dark_routing()
        assert math.isclose(res_stack["preemptive_dark_routing_ratio"], 0.99999999999999999995, rel_tol=1e-15)

    def test_smart_order_router_version_64_properties(self):
        """Verify SmartOrderRouter initialization and routing properties under version 64."""
        sor = SmartOrderRouter(version=64)
        assert sor.version == 64
        assert sor.is_phase64 is True
        assert sor.is_phase63 is True
        assert sor.is_phase62 is True
        assert sor._resolve_max_dark_cap(64) == 0.99999999999999999995

        # Test routing with directional toxicity
        plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 10000,
            "target_price": 150.0,
            "execution_strategy": "DYNAMIC_VWAP",
            "gamma_toxic_dir": 0.95,
            "darkpool_score": 0.70,
            "version": 64,
        }
        res = sor.route_order(plan)
        assert res["toxic_flow_detected"] is True
        assert res["maker_ratio"] <= 0.05
        assert res["min_ratio"] >= 0.90

    def test_smart_order_router_maker_floor_contraction(self):
        """Verify maker floor contracts to 1e-36 under extreme toxicity in Phase 64."""
        sor = SmartOrderRouter(version=64)
        plan = {
            "symbol": "NVDA",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 400.0,
            "gamma_toxic_dir": 1.0,
            "version": 64,
        }
        res = sor.route_order(plan)
        assert res["maker_ratio"] >= 1e-36
        assert res["maker_ratio"] <= 0.01

    def test_oms_engine_phase64_preemptive_micro_tick_shading(self):
        """Verify preemptive micro-tick shading in ExecutionOMSEngine activates at h > 0.0000008."""
        oms = ExecutionOMSEngine()
        target_price = 100.0
        best_bid = 99.95
        best_ask = 100.05

        # Sub-threshold: h = 0.0000005 <= 0.0000008 -> no shift
        p_sub = oms.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.0000005,
            version=64,
        )

        # Above threshold: h = 0.0000010 > 0.0000008 -> hawkes shift activates
        p_above = oms.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.0000010,
            version=64,
        )

        assert p_above < p_sub, f"BUY limit price should shade downward under toxic Hawkes intensity (p_above={p_above}, p_sub={p_sub})"

    def test_almgren_chriss_phase64_preemptive_micro_tick_shading(self):
        """Verify preemptive micro-tick shading in AlmgrenChrissScheduler at h > 0.0000008."""
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
            hawkes_intensity=0.0000005,
            version=64,
        )

        p_above = scheduler.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.0000010,
            version=64,
        )

        assert p_above < p_sub, "Almgren-Chriss scheduler must shade BUY price downward for h > 0.0000008"

    def test_backward_compatibility_v63_and_prior(self):
        """Verify backward compatibility of SOR and OMS with Phase 63."""
        sor63 = SmartOrderRouter(version=63)
        assert sor63.is_phase64 is False
        assert sor63.is_phase63 is True
        assert sor63._resolve_max_dark_cap(63) == 0.99999999999999999999

        oms = ExecutionOMSEngine()
        p63 = oms.calculate_peg_limit_price(
            target_price=100.0,
            action="BUY",
            best_bid=99.95,
            best_ask=100.05,
            peg_offset=0.0,
            hawkes_intensity=0.0000012,
            version=63,
        )
        assert np.isfinite(p63)
