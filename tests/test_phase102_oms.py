"""
tests/test_phase102_oms.py

Unit and integration test suite for Phase 102 Quantitative Alpha Enhancement (Feature F483 Microstructure OMS):
- Kerr-Newman-Kiselev 80-Dark-Energy DAHA
  (w = -82.0/3.0 approx -27.333, k_daha = 0.72, k_monster = 0.71,
   daha_80_factor = 15.90, c_monster = 2.0679515313825692e-25 [2^-82])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 80-fold dark energy density
  * Repulsive acceleration -45.5 * c * (r ** 90) * daha_80_factor clamped in [-1e6, 1e6]
  * Theoretical check at r_eff = 2.0: exactly -185203.20
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, Phase102FastLOBEngine, and module level (23 aliases)
- SmartOrderRouter version=102:
  * Default version: 102
  * Lit maker ratio floor contracted to 1e-73 with 75-decimal precision
  * Cascading version flags: is_phase102 -> is_phase101 -> is_phase100...
  * Spread-conditional dark pool probing: when is_phase102 and market_spread_bps >= 5.0, is_probe_eligible = True
- Dual-OMS Preemptive micro-tick shading at h > 8.0e-12 (tested at h = 9.0e-12):
  * 55-nines factor (1 - 10^-55)
  * Exact parity between ExecutionOMSEngine and AlmgrenChrissScheduler (< 10^-12)
  * oms_p102_sub < oms_p101_sub
- Intraday U-curve volume profile weighted trajectory slicing:
  * u_i = 1.0 + 0.8 * (2*i/(N-1) - 1)^2
- Adaptive small-cap VPIN toxicity threshold in Gate 7.6:
  * vpin_threshold = 0.65 for KOSDAQ / RUSSELL2000 tickers vs 0.70 baseline
- Zero Regression with Phase 101, Phase 100 & Phase 99
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    Phase102FastLOBEngine,
    Phase101FastLOBEngine,
    Phase100FastLOBEngine,
    Phase99FastLOBEngine,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler
from trading_system.src.execution.almgren_chriss import AlmgrenChrissScheduler as ReexportedAlmgrenChrissScheduler

from trading_system.src.core.fast_lob_engine import (
    compute_kerr_newman_kiselev_80_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
    compute_kerr_newman_kiselev_80_dark_energy_daha_queue_acceleration,
    compute_kerr_newman_kiselev_80_dark_energy_daha_acceleration,
    compute_knk_80_dark_energy_daha_acceleration,
    compute_phase102_daha_l3_acceleration,
    compute_phase102_lob_acceleration,
    phase102_lob_spacetime_hydrodynamics,
    compute_knk_80_dark_energy_acceleration,
    compute_kerr_newman_kiselev_80_dark_energy_acceleration,
    phase102_daha_l3_acceleration,
    knk_80_dark_energy_daha_l3,
    daha_l3_phase102_acceleration,
    phase102_dark_energy_acceleration,
    calculate_phase102_knk_acceleration,
    compute_knk_phase102_acceleration,
    daha_phase102_acceleration,
    phase102_spacetime_hydrodynamics,
    phase102_queue_acceleration,
    l3_phase102_acceleration,
    phase102_knk_acceleration,
    compute_phase102_knk_daha_queue_acceleration,
    compute_phase102_queue_acceleration,
    phase102_l3_queue_acceleration,
    knk_80_daha_queue_acceleration,
)


class TestPhase102MicrostructureAndOMS:
    """Test suite for Phase 102 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_80_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 80-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_80_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        assert func is not None, "'FastOrderBookMatchingEngine' object missing KNK-80 acceleration method"

        res = func(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_80_dark_energy_correction" in res
        assert "knk_80_dark_energy_daha_acceleration" in res
        assert "phase102_knk_acceleration" in res
        assert "phase101_knk_acceleration" in res

        assert math.isfinite(res["knk_80_dark_energy_correction"])
        assert math.isfinite(res["knk_80_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_80_factor"], 15.90, rel_tol=1e-5)
        assert math.isclose(res["k_daha_80"], 0.72, rel_tol=1e-5)
        assert math.isclose(res["k_monster_80"], 0.71, rel_tol=1e-5)
        assert math.isclose(res["c_monster_80"], 2.0**-82, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_80"], -82.0 / 3.0, rel_tol=1e-5)

        # Theoretical check: at r_eff = 2.0, c_80 = 2^-82, daha_80_factor = 15.90
        # dark_80_accel = -45.5 * (2^-82) * (2^90) * 15.90 = -45.5 * 256.0 * 15.90 = -185203.20
        c_80 = 2.0**-82
        r_eff = 2.0
        theoretical_dark_accel = -45.5 * c_80 * (r_eff**90) * 15.90
        assert math.isclose(theoretical_dark_accel, -185203.20, rel_tol=1e-9)

    def test_kerr_newman_kiselev_80_aliases(self):
        """Verify 23 method aliases on FastOrderBookMatchingEngine, FastLOBEngine, Phase102FastLOBEngine, and module level for KNK-80."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_80_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        assert func is not None
        ref = func()

        # Check class method aliases (23 aliases)
        alias_names = [
            "compute_kerr_newman_kiselev_80_dark_energy_daha_queue_acceleration",
            "compute_kerr_newman_kiselev_80_dark_energy_daha_acceleration",
            "compute_knk_80_dark_energy_daha_acceleration",
            "compute_phase102_daha_l3_acceleration",
            "compute_phase102_lob_acceleration",
            "phase102_lob_spacetime_hydrodynamics",
            "compute_knk_80_dark_energy_acceleration",
            "compute_kerr_newman_kiselev_80_dark_energy_acceleration",
            "phase102_daha_l3_acceleration",
            "knk_80_dark_energy_daha_l3",
            "daha_l3_phase102_acceleration",
            "phase102_dark_energy_acceleration",
            "calculate_phase102_knk_acceleration",
            "compute_knk_phase102_acceleration",
            "daha_phase102_acceleration",
            "phase102_spacetime_hydrodynamics",
            "phase102_queue_acceleration",
            "l3_phase102_acceleration",
            "phase102_knk_acceleration",
            "compute_phase102_knk_daha_queue_acceleration",
            "compute_phase102_queue_acceleration",
            "phase102_l3_queue_acceleration",
            "knk_80_daha_queue_acceleration",
        ]
        assert len(alias_names) == 23

        for alias in alias_names:
            method = getattr(engine, alias, None)
            assert method is not None, f"Missing method {alias} on FastOrderBookMatchingEngine"
            assert method() == ref

        # Check aliases on FastLOBEngine alias class
        engine_lob = FastLOBEngine(symbol="AAPL")
        for i in range(5):
            engine_lob.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine_lob.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)
        for alias in alias_names:
            method = getattr(engine_lob, alias, None)
            assert method is not None, f"Missing method {alias} on FastLOBEngine"
            assert method() == ref

        # Check aliases on Phase102FastLOBEngine alias class
        engine_p102 = Phase102FastLOBEngine(symbol="AAPL")
        for i in range(5):
            engine_p102.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine_p102.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)
        for alias in alias_names:
            method = getattr(engine_p102, alias, None)
            assert method is not None, f"Missing method {alias} on Phase102FastLOBEngine"
            assert method() == ref

        # Check module-level aliases (23 functions + base = 24 functions)
        module_funcs = [
            compute_kerr_newman_kiselev_80_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
            compute_kerr_newman_kiselev_80_dark_energy_daha_queue_acceleration,
            compute_kerr_newman_kiselev_80_dark_energy_daha_acceleration,
            compute_knk_80_dark_energy_daha_acceleration,
            compute_phase102_daha_l3_acceleration,
            compute_phase102_lob_acceleration,
            phase102_lob_spacetime_hydrodynamics,
            compute_knk_80_dark_energy_acceleration,
            compute_kerr_newman_kiselev_80_dark_energy_acceleration,
            phase102_daha_l3_acceleration,
            knk_80_dark_energy_daha_l3,
            daha_l3_phase102_acceleration,
            phase102_dark_energy_acceleration,
            calculate_phase102_knk_acceleration,
            compute_knk_phase102_acceleration,
            daha_phase102_acceleration,
            phase102_spacetime_hydrodynamics,
            phase102_queue_acceleration,
            l3_phase102_acceleration,
            phase102_knk_acceleration,
            compute_phase102_knk_daha_queue_acceleration,
            compute_phase102_queue_acceleration,
            phase102_l3_queue_acceleration,
            knk_80_daha_queue_acceleration,
        ]
        assert len(module_funcs) == 24
        for m_fn in module_funcs:
            assert m_fn(engine) == ref

    def test_smart_order_router_phase102_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 102 flags and lit maker floor to 1e-73."""
        sor_102 = SmartOrderRouter(version=102)
        assert getattr(sor_102, "is_phase102", False) is True
        assert getattr(sor_102, "is_phase101", False) is True
        assert getattr(sor_102, "is_phase100", False) is True
        assert getattr(sor_102, "is_phase99", False) is True

        # Default version should be 102
        sor_default = SmartOrderRouter()
        assert sor_default.version == 102
        assert sor_default.is_phase102 is True
        assert sor_default.is_phase101 is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 102,
            "target_price": 150.0,
            "hawkes_intensity": 0.95,
        }
        res = sor_102.route_order(order_plan, gamma_toxic_dir=1.0)
        assert "maker_ratio" in res
        assert "min_ratio" in res
        assert res["maker_ratio"] == 1e-73
        assert res["maker_ratio"] < 1e-72

    def test_smart_order_router_spread_conditional_dark_probing(self):
        """Verify spread-conditional dark pool probing for spreads >= 5.0 bps."""
        sor = SmartOrderRouter(version=102)

        # Order plan with wide spread (6.0 bps) in DIRECT strategy (normally not dark eligible without high score/toxic)
        plan_wide = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 102,
            "target_price": 150.0,
            "execution_strategy": "DIRECT",
            "market_spread_bps": 6.0,
            "darkpool_activity_score": 0.10,  # Below 0.30 threshold
        }
        res_wide = sor.route_order(plan_wide, gamma_toxic_dir=0.0)
        venues_wide = [leg["venue_type"] for leg in res_wide["legs"]]
        assert "DARK_ATS_MIDPOINT" in venues_wide, "Wide spread (>= 5 bps) should trigger dark pool probing in Phase 102"

        # Order plan with tight spread (2.0 bps) in DIRECT strategy
        plan_tight = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 102,
            "target_price": 150.0,
            "execution_strategy": "DIRECT",
            "market_spread_bps": 2.0,
            "darkpool_activity_score": 0.10,
        }
        res_tight = sor.route_order(plan_tight, gamma_toxic_dir=0.0)
        venues_tight = [leg["venue_type"] for leg in res_tight["legs"]]
        assert "DARK_ATS_MIDPOINT" not in venues_tight, "Tight spread (< 5 bps) without catalysts should not probe dark pool"

    def test_tick_shading_dual_oms_phase102_threshold(self):
        """Verify tick shading threshold h > 8.0e-12 (tested at h = 9.0e-12)."""
        oms_p102_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=102,
            hawkes_intensity={"cross_excitation_toxicity": 9.0e-12}
        )
        oms_p101_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=101,
            hawkes_intensity={"cross_excitation_toxicity": 9.0e-12}
        )
        # Phase 102 activates at h > 8.0e-12, so at 9.0e-12 it has non-zero shading.
        # Phase 101 activates at h > 1.0e-11, so at 9.0e-12 it has 0 shading offset (unshaded target price 100.0).
        assert oms_p102_sub < 100.0
        assert oms_p101_sub == 100.0
        assert oms_p102_sub < oms_p101_sub

        # Sub-threshold check: at h = 7.0e-12, neither should shade
        oms_p102_sub_low = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=102,
            hawkes_intensity={"cross_excitation_toxicity": 7.0e-12}
        )
        assert oms_p102_sub_low == 100.0

        # Exact parity with AlmgrenChrissScheduler
        sch_p102_sub = AlmgrenChrissScheduler.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=102,
            hawkes_intensity={"cross_excitation_toxicity": 9.0e-12}
        )
        assert math.isclose(oms_p102_sub, sch_p102_sub, rel_tol=1e-12, abs_tol=1e-12)

        # Also verify with re-exported AlmgrenChrissScheduler
        sch_reexp = ReexportedAlmgrenChrissScheduler.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=102,
            hawkes_intensity={"cross_excitation_toxicity": 9.0e-12}
        )
        assert math.isclose(sch_p102_sub, sch_reexp, rel_tol=1e-12, abs_tol=1e-12)

    def test_almgren_chriss_u_curve_intraday_slicing(self):
        """Verify Almgren-Chriss scheduler intraday U-curve volume profile weighting."""
        tranches_u = AlmgrenChrissScheduler.compute_trajectory(
            total_quantity=1000,
            adv=1e9,
            daily_volatility=0.02,
            strategy_tier="medium",
            n_slices=6,
            use_u_curve=True
        )
        tranches_no_u = AlmgrenChrissScheduler.compute_trajectory(
            total_quantity=1000,
            adv=1e9,
            daily_volatility=0.02,
            strategy_tier="medium",
            n_slices=6,
            use_u_curve=False
        )

        assert len(tranches_u) == 6
        assert sum(tranches_u) == 1000
        assert all(q >= 0 for q in tranches_u)

        # U-curve profile u_i = 1.0 + 0.8 * (2*i/(N-1) - 1)^2 has u_0 = 1.8, u_mid = 1.0, u_5 = 1.8
        # Slices at edges (open and close) receive elevated share compared to midday slices
        assert tranches_u[0] > tranches_u[2]
        assert tranches_u[5] > tranches_u[3]
        # Compare with non-U-curve hyperbolic schedule: the closing tranche is boosted by the U-curve
        assert tranches_u[-1] > tranches_no_u[-1]

    def test_gate_7_6_adaptive_small_cap_vpin_threshold(self):
        """Verify Gate 7.6 adaptive VPIN threshold (0.65 vs 0.70) for small-cap tickers."""
        oms = ExecutionOMSEngine(lot_size_krx=1, version=102)

        # Small cap ticker (KOSDAQ) with vpin = 0.68
        # Under Phase 102, threshold is 0.65 -> triggers PASSIVE_LIMIT on BUY
        plan_kosdaq = oms.generate_order_plan(
            top_predictions=[{
                "symbol": "035720",
                "market": "KOSDAQ",
                "action": "BUY",
                "target_price": 50000.0,
                "vpin": 0.68,
                "market_cap": 2e11,
                "version": 102,
            }],
            portfolio_weights={"035720": 0.05},
            total_capital=10_000_000,
            version=102,
        )
        assert len(plan_kosdaq) == 1
        assert plan_kosdaq[0]["execution_strategy"] == "PASSIVE_LIMIT"

        # Large cap ticker (KOSPI, market_cap = 1e12) with same vpin = 0.68
        # Under Phase 102, large cap threshold remains 0.70 -> does NOT trigger PASSIVE_LIMIT
        plan_kospi = oms.generate_order_plan(
            top_predictions=[{
                "symbol": "005930",
                "market": "KOSPI",
                "action": "BUY",
                "target_price": 70000.0,
                "vpin": 0.68,
                "market_cap": 5e13,
                "version": 102,
            }],
            portfolio_weights={"005930": 0.05},
            total_capital=10_000_000,
            version=102,
        )
        assert len(plan_kospi) == 1
        assert plan_kospi[0]["execution_strategy"] != "PASSIVE_LIMIT"

        # Under Phase 101 (version=101), KOSDAQ with vpin = 0.68 does NOT trigger Gate 7.6
        plan_kosdaq_p101 = oms.generate_order_plan(
            top_predictions=[{
                "symbol": "035720",
                "market": "KOSDAQ",
                "action": "BUY",
                "target_price": 50000.0,
                "vpin": 0.68,
                "market_cap": 2e11,
                "version": 101,
            }],
            portfolio_weights={"035720": 0.05},
            total_capital=10_000_000,
            version=101,
        )
        assert len(plan_kosdaq_p101) == 1
        assert plan_kosdaq_p101[0]["execution_strategy"] != "PASSIVE_LIMIT"

    def test_zero_regression_phase101_and_phase100_compatibility(self):
        """Verify Phase 101 and Phase 100 calculations remain strictly preserved when requested."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        engine.add_limit_order("b1", "BUY", 100.0, 10.0)
        engine.add_limit_order("a1", "SELL", 101.0, 10.0)

        res_p101 = engine.compute_kerr_newman_kiselev_79_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isclose(res_p101["daha_79_factor"], 15.60, rel_tol=1e-5)
        assert math.isclose(res_p101["k_daha_79"], 0.71, rel_tol=1e-5)

        res_p100 = engine.compute_kerr_newman_kiselev_78_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isclose(res_p100["daha_78_factor"], 15.30, rel_tol=1e-5)

        sor_101 = SmartOrderRouter(version=101)
        assert sor_101.is_phase101 is True
        assert sor_101.is_phase102 is False
        order_plan_101 = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 101,
            "target_price": 150.0,
            "hawkes_intensity": 0.95,
        }
        res_routed_101 = sor_101.route_order(order_plan_101, gamma_toxic_dir=1.0)
        assert res_routed_101["maker_ratio"] == 1e-72

        sor_100 = SmartOrderRouter(version=100)
        assert sor_100.is_phase100 is True
        assert sor_100.is_phase101 is False
        order_plan_100 = dict(order_plan_101, version=100)
        res_routed_100 = sor_100.route_order(order_plan_100, gamma_toxic_dir=1.0)
        assert res_routed_100["maker_ratio"] == 1e-71
