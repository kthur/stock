"""
tests/test_phase17_challenger_stress_oms_benchmark.py

Adversarial Stress Test Suite for Phase 17 Quant Enhancement:
- Feature F89.2: Microstructure OMS
  * Kerr spacetime ergosphere rotational queue acceleration across extreme spin parameters a -> M and r -> r_E.
  * SmartOrderRouter under 100% lit toxicity (gamma_toxic = 1.0) verifying maker floor is strictly bounded to 0.0001 and dark allocation reaches 0.998.
  * Preemptive micro-tick shading under extreme spreads and Hawkes intensities (h > 10.0), checking clipping within bid-ask bounds.
- Feature F90: 5-Market Quantitative Benchmark Engine
  * Benchmark engine under perturbed market weights, zero weights, and random metric profiles.

Author: Challenger 2 (Empirical Challenger)
"""

import math
import random
import numpy as np
import pytest

from src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    DeepHawkesArrivalProcess,
)
from src.execution.smart_order_router import SmartOrderRouter
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler

from trading_system.scripts.benchmark_phase17_quant_performance import (
    Phase17QuantBenchmarkEngine,
    compute_aggregate_metrics,
    QuantitativeMetrics,
    BENCHMARK_PROFILES,
    MARKET_WEIGHTS,
    generate_phase17_markdown_report,
)


class TestKerrSpacetimeErgosphereAdversarialStress:
    """Stress tests for Kerr spacetime ergosphere rotational queue acceleration."""

    def test_kerr_schwarzschild_static_limit(self):
        """When spin parameter a = 0.0, frame-dragging omega must strictly vanish."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 70000.0 - i * 50.0, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 70100.0 + i * 50.0, 100.0)

        res = engine.compute_kerr_ergosphere_queue_acceleration(spin_parameter=0.0)
        assert res["kerr_spin_a"] == 0.0
        assert res["frame_dragging_omega"] == 0.0
        # When omega=0, rotational acceleration equals classical queue acceleration
        assert math.isclose(res["kerr_rotational_acceleration"], res["qi_acceleration"], abs_tol=1e-5)

    def test_kerr_extreme_spin_parameters_boundary(self):
        """
        Adversarial test across extreme spin parameters a -> M, a = M, a > M (naked singularity candidate),
        and negative spin parameters. Verifies spin parameter is strictly clipped to [0, 0.999 * M].
        """
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 70000.0 - i * 50.0, 200.0)
            engine.add_limit_order(f"a_{i}", "SELL", 70100.0 + i * 50.0, 200.0)

        extreme_spins = [0.999, 1.0, 1.5, 10.0, 1000.0, -0.999, -1.0, -100.0]
        for spin in extreme_spins:
            res = engine.compute_kerr_ergosphere_queue_acceleration(spin_parameter=spin)
            M = res["kerr_mass_M"]
            a = res["kerr_spin_a"]
            # Spin a must strictly never exceed 0.999 * M
            assert 0.0 <= a <= 0.999 * M + 1e-6
            assert res["frame_dragging_omega"] >= 0.0
            assert math.isfinite(res["frame_dragging_omega"])
            assert -100.0 <= res["kerr_rotational_acceleration"] <= 100.0
            assert -1.0 <= res["kerr_accelerated_qi"] <= 1.0
            assert math.isfinite(res["kerr_micro_price"])

    def test_kerr_ergosphere_boundary_limit_r_to_rE(self):
        """
        Boundary condition r -> r_E:
        When qi = 0, r_coord = M.
        When a -> M and theta = 0 (pole), r_E = M + sqrt(M^2 - a^2) -> M.
        Verify that as r_coord -> r_E, drag_amp remains finite and does not divide by zero or diverge.
        """
        engine = FastOrderBookMatchingEngine(symbol="005930")
        # Perfectly balanced book so qi_l3 = 0.0
        engine.add_limit_order("b1", "BUY", 100.0, 500.0)
        engine.add_limit_order("a1", "SELL", 100.2, 500.0)

        # Spin very close to 1.0, theta = 0 (polar)
        res = engine.compute_kerr_ergosphere_queue_acceleration(spin_parameter=0.999, theta=0.0)
        M = res["kerr_mass_M"]
        r = res["coordinate_radius_r"]
        r_E = res["ergosphere_radius"]

        # r_coord is M * (1 - 0.5 * 0) = M
        assert math.isclose(r, M, rel_tol=1e-3)
        # r_E at theta=0 with a = 0.999M is M + sqrt(1 - 0.999^2)*M = M + 0.0447*M
        assert r_E >= r
        assert res["is_in_ergosphere"] is True
        assert math.isfinite(res["frame_dragging_omega"])
        assert -100.0 <= res["kerr_rotational_acceleration"] <= 100.0

    def test_kerr_angle_theta_variation_equatorial_vs_polar(self):
        """
        At equator (theta = pi/2), r_E = 2*M, maximum ergosphere volume.
        At pole (theta = 0), r_E = M + sqrt(M^2 - a^2).
        Verify ergosphere radius and frame dragging across angles in [-pi, pi].
        """
        engine = FastOrderBookMatchingEngine(symbol="NVDA")
        engine.add_limit_order("b1", "BUY", 120.0, 1000.0)
        engine.add_limit_order("a1", "SELL", 120.5, 800.0)

        thetas = [0.0, math.pi / 6.0, math.pi / 4.0, math.pi / 3.0, math.pi / 2.0, -math.pi / 2.0, math.pi]
        for th in thetas:
            res = engine.compute_kerr_ergosphere_queue_acceleration(spin_parameter=0.85, theta=th)
            M = res["kerr_mass_M"]
            r_E = res["ergosphere_radius"]
            # At theta = pi/2, r_E must equal exactly 2.0 * M
            if math.isclose(abs(th), math.pi / 2.0, abs_tol=1e-5):
                assert math.isclose(r_E, 2.0 * M, abs_tol=1e-3)
            # r_E must always be between M and 2*M
            assert M <= r_E <= 2.0 * M + 1e-4

    def test_kerr_extreme_order_volume_and_depth(self):
        """Stress test with astronomical depth (log1p scaling) and empty/near-empty book."""
        # Astronomical depth
        engine_huge = FastOrderBookMatchingEngine(symbol="HUGE")
        engine_huge.add_limit_order("b1", "BUY", 1000.0, 1e12)
        engine_huge.add_limit_order("a1", "SELL", 1001.0, 1e12)
        res_huge = engine_huge.compute_kerr_ergosphere_queue_acceleration(spin_parameter=0.95)
        assert res_huge["kerr_mass_M"] > 20.0
        assert math.isfinite(res_huge["frame_dragging_omega"])
        assert -1.0 <= res_huge["kerr_accelerated_qi"] <= 1.0

        # Small depth
        engine_small = FastOrderBookMatchingEngine(symbol="SMALL")
        engine_small.add_limit_order("b1", "BUY", 10.0, 0.001)
        engine_small.add_limit_order("a1", "SELL", 10.1, 0.001)
        res_small = engine_small.compute_kerr_ergosphere_queue_acceleration(spin_parameter=0.95)
        assert res_small["kerr_mass_M"] >= 1.0
        assert math.isfinite(res_small["frame_dragging_omega"])


class TestSmartOrderRouterToxicityStress:
    """Stress tests for SmartOrderRouter under 100% lit toxicity and high queue acceleration."""

    def test_maker_floor_strictly_bounded_directional_toxicity(self):
        """
        Under 100% directional toxicity (gamma_toxic_dir = 1.0 and extreme 2.0),
        the lit maker ratio floor must contract to strictly 0.0001 under Phase 17.
        """
        sor = SmartOrderRouter()
        for g_tox in [1.0, 1.05, 5.0]:
            plan = {
                "symbol": "AAPL",
                "action": "BUY",
                "quantity": 100_000,
                "target_price": 150.0,
                "gamma_toxic_dir": g_tox,
                "version": 17,
            }
            res = sor.route_order(plan, ats_available=False)
            assert res["gamma_toxic"] == 1.0
            assert math.isclose(res["maker_ratio"], 0.0001, abs_tol=1e-5)

            # Check legs: maker leg quantity should be 100,000 * 0.0001 = 10
            maker_leg = res["primary_exchange_maker"]
            assert maker_leg is not None
            assert maker_leg["quantity"] == 10
            assert math.isclose(maker_leg["maker_ratio"], 0.0001, abs_tol=1e-5)

    def test_maker_floor_strictly_bounded_hawkes_toxicity(self):
        """
        Under extreme Hawkes buy/sell arrival divergence generating 100% toxicity,
        maker ratio floor must strictly contract to 0.0001.
        """
        sor = SmartOrderRouter()
        plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 100_000,
            "target_price": 150.0,
            # For BUY, toxic flow is ask sweeps: hawkes_sell is high
            "hawkes_buy": 0.5,
            "hawkes_sell": 10.0,
            "version": 17,
        }
        res = sor.route_order(plan, ats_available=False)
        assert res["gamma_toxic"] == 1.0
        assert math.isclose(res["maker_ratio"], 0.0001, abs_tol=1e-5)

    def test_maker_floor_strictly_bounded_cross_asset_toxicity(self):
        """
        Under cross-asset toxicity blending with cross_asset_toxicity = 1.0 and gamma_toxic_dir = 1.0,
        maker ratio floor must strictly contract to 0.0001.
        """
        sor = SmartOrderRouter()
        plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 50_000,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "cross_asset_toxicity": 1.0,
            "version": 17,
        }
        res = sor.route_order(plan, ats_available=False)
        assert res["gamma_toxic"] == 1.0
        assert math.isclose(res["maker_ratio"], 0.0001, abs_tol=1e-5)

    def test_dark_allocation_reaches_998_cap(self):
        """
        Under extreme queue imbalance, acceleration, and darkpool score,
        dark allocation must saturate at exactly 0.998 (99.8%) and not exceed it.
        """
        sor = SmartOrderRouter()
        plan = {
            "symbol": "NVDA",
            "action": "BUY",
            "quantity": 100_000,
            "target_price": 120.0,
            "queue_imbalance": 0.95,
            "qi_acceleration": 0.50,
            "darkpool_score": 0.99,
            "gamma_toxic_dir": 0.95,
            "version": 17,
        }
        res = sor.route_order(plan, ats_available=True)
        assert res["effective_dark_ratio"] == 0.998

        dark_leg = res["dark_ats_midpoint"]
        assert dark_leg is not None
        # 100,000 * 0.998 = 99,800 shares to dark ATS
        assert dark_leg["quantity"] == 99800

        # Residual 200 shares to lit venues
        lit_legs = [l for l in res["legs"] if "DARK" not in l["venue_type"]]
        lit_qty_sum = sum(l["quantity"] for l in lit_legs)
        assert lit_qty_sum == 200

    def test_dynamic_anti_gaming_min_qty_cap(self):
        """
        Under 100% toxicity and high institutional accumulation,
        anti-gaming MinQty ratio must saturate at exactly 0.999 (99.9%).
        """
        sor = SmartOrderRouter()
        plan = {
            "symbol": "TSLA",
            "action": "BUY",
            "quantity": 100_000,
            "target_price": 200.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "is_accumulation": True,
            "version": 17,
        }
        res = sor.route_order(plan, ats_available=True)
        assert res["min_ratio"] == 0.999
        dark_leg = res["dark_ats_midpoint"]
        assert dark_leg is not None
        assert dark_leg["min_quantity"] == int(dark_leg["quantity"] * 0.999)

    def test_non_toxic_regime_maker_floor_unconstrained(self):
        """
        Under benign market conditions (gamma_toxic <= 0.50),
        maker ratio should NOT be compressed to 0.0001, capturing passive rebates.
        """
        sor = SmartOrderRouter()
        plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 10_000,
            "target_price": 150.0,
            "gamma_toxic_dir": 0.10,
            "version": 17,
        }
        res = sor.route_order(plan, ats_available=False)
        assert res["maker_ratio"] > 0.50


class TestPreemptiveMicroTickShadingStress:
    """Stress tests for preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler."""

    @pytest.mark.parametrize("h_val", [1.0, 5.0, 10.0, 50.0, 100.0, 1000.0])
    @pytest.mark.parametrize("spread", [0.05, 1.0, 10.0, 500.0])
    def test_extreme_hawkes_and_spread_bounds_buy(self, h_val, spread):
        """
        Under extreme Hawkes intensity h and various spreads,
        BUY peg price must be shaded downwards (passive) and strictly clamped within [bid_price, ask_price].
        When h_val is extreme (h > 10.0 and spread is passed), the price hits the bid floor without breaking it.
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        mid = 1000.0
        bid = mid - spread / 2.0
        ask = mid + spread / 2.0

        p_oms = oms.calculate_peg_limit_price(
            target_price=mid,
            bid_price=bid,
            ask_price=ask,
            spread=spread,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=17,
        )
        p_sched = scheduler.calculate_peg_limit_price(
            target_price=mid,
            bid_price=bid,
            ask_price=ask,
            spread=spread,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=17,
        )

        # 1. Must be strictly clamped within [bid, ask]
        assert bid <= p_oms <= ask
        assert bid <= p_sched <= ask

        # 2. Must be shaded downwards relative to mid price
        assert p_oms <= mid
        assert p_sched <= mid

        # 3. Under extreme intensity (h >= 10.0), shading drives BUY limit price directly to the bid floor
        if h_val >= 10.0:
            assert math.isclose(p_oms, bid, abs_tol=1e-4)
            assert math.isclose(p_sched, bid, abs_tol=1e-4)

        # 4. Perfect symmetry and consistency between OMS and Scheduler
        assert math.isclose(p_oms, p_sched, abs_tol=1e-6)

    @pytest.mark.parametrize("h_val", [1.0, 5.0, 10.0, 50.0, 100.0, 1000.0])
    @pytest.mark.parametrize("spread", [0.05, 1.0, 10.0, 500.0])
    def test_extreme_hawkes_and_spread_bounds_sell(self, h_val, spread):
        """
        Under extreme Hawkes intensity h and various spreads,
        SELL peg price must be shaded upwards (passive) and strictly clamped within [bid_price, ask_price].
        When h_val is extreme (h > 10.0 and spread is passed), the price hits the ask ceiling without breaking it.
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        mid = 1000.0
        bid = mid - spread / 2.0
        ask = mid + spread / 2.0

        p_oms = oms.calculate_peg_limit_price(
            target_price=mid,
            bid_price=bid,
            ask_price=ask,
            spread=spread,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=17,
        )
        p_sched = scheduler.calculate_peg_limit_price(
            target_price=mid,
            bid_price=bid,
            ask_price=ask,
            spread=spread,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=17,
        )

        # 1. Must be strictly clamped within [bid, ask]
        assert bid <= p_oms <= ask
        assert bid <= p_sched <= ask

        # 2. Must be shaded upwards relative to mid price
        assert p_oms >= mid
        assert p_sched >= mid

        # 3. Under extreme intensity (h >= 10.0), shading drives SELL limit price directly to the ask ceiling
        if h_val >= 10.0:
            assert math.isclose(p_oms, ask, abs_tol=1e-4)
            assert math.isclose(p_sched, ask, abs_tol=1e-4)

        # 4. Perfect symmetry and consistency between OMS and Scheduler
        assert math.isclose(p_oms, p_sched, abs_tol=1e-6)

    def test_hawkes_threshold_inactivity_boundary(self):
        """
        Hawkes intensity <= 0.12 must generate exactly zero shading offset.
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        bid, ask, target = 99.0, 101.0, 100.0

        # Exactly at threshold 0.12
        p_at_threshold = oms.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=2.0, action="BUY",
            hawkes_intensity=0.12, version=17,
        )
        # Below threshold 0.10
        p_below_threshold = oms.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=2.0, action="BUY",
            hawkes_intensity=0.10, version=17,
        )
        # Zero intensity
        p_zero = oms.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=2.0, action="BUY",
            hawkes_intensity=0.0, version=17,
        )

        assert math.isclose(p_at_threshold, p_below_threshold, abs_tol=1e-6)
        assert math.isclose(p_at_threshold, p_zero, abs_tol=1e-6)

    def test_inverted_market_and_zero_spread_edge_cases(self):
        """
        Adversarial order book edge cases:
        1. Inverted market where bid > ask (crossed book)
        2. Zero spread where bid == ask
        """
        oms = ExecutionOMSEngine()

        # Inverted book
        p_inv = oms.calculate_peg_limit_price(
            target_price=100.0, bid_price=101.0, ask_price=99.0, spread=2.0, action="BUY",
            hawkes_intensity=5.0, version=17,
        )
        assert 99.0 <= p_inv <= 101.0

        # Zero spread
        p_zero_spr = oms.calculate_peg_limit_price(
            target_price=100.0, bid_price=100.0, ask_price=100.0, spread=0.0, action="BUY",
            hawkes_intensity=5.0, version=17,
        )
        assert math.isclose(p_zero_spr, 100.0, abs_tol=1e-6)


class TestBenchmarkEnginePerturbationsAndRandomProfiles:
    """Stress tests for Phase17QuantBenchmarkEngine under perturbed weights, zero weights, and random profiles."""

    def test_perturbed_weights_on_subset_markets(self):
        """
        Test benchmark aggregation under heavily skewed market weights on a subset of markets.
        (e.g., US markets: SP500, NASDAQ, RUSSELL2000).
        """
        engine = Phase17QuantBenchmarkEngine(markets=["SP500", "NASDAQ", "RUSSELL2000"])
        skewed_weights = {"SP500": 0.80, "NASDAQ": 0.15, "RUSSELL2000": 0.05}
        res = engine.run_benchmark(weights=skewed_weights)

        agg_e = res["aggregate"]["enhancement"]
        assert isinstance(agg_e, QuantitativeMetrics)

        # Since SP500 is 80% weighted, net return must be very close to SP500's net return (95.95%)
        # NASDAQ (108.70%), RUSSELL2000 (99.70%)
        # Expected: 0.80 * 95.95 + 0.15 * 108.70 + 0.05 * 99.70 = 76.76 + 16.305 + 4.985 = 98.05
        assert math.isclose(agg_e.net_return_ann_pct, 98.05, abs_tol=0.1)
        assert agg_e.sharpe_ratio >= 13.0

    def test_zero_weights_exception_or_behavior(self):
        """
        Adversarial test: what happens when all weights are 0.0?
        total_w is 0.0, so float division by zero must be raised or handled cleanly.
        """
        all_zero_weights = {"SP500": 0.0, "NASDAQ": 0.0, "KOSPI": 0.0, "KOSDAQ": 0.0, "RUSSELL2000": 0.0}
        with pytest.raises(ZeroDivisionError):
            compute_aggregate_metrics(BENCHMARK_PROFILES, weights=all_zero_weights)

    def test_single_nonzero_weight(self):
        """
        When all other weights are 0.0 except one market (e.g., KOSPI=1.0, others=0.0 on subset),
        the aggregate metric must equal that single market's metric exactly.
        """
        subset_profiles = {
            "KOSPI": BENCHMARK_PROFILES["KOSPI"],
            "KOSDAQ": BENCHMARK_PROFILES["KOSDAQ"],
        }
        weights = {"KOSPI": 1.0, "KOSDAQ": 0.0}
        agg = compute_aggregate_metrics(subset_profiles, weights=weights, mode="enhancement")

        kospi_e = BENCHMARK_PROFILES["KOSPI"]["enhancement"]
        assert math.isclose(agg.net_return_ann_pct, kospi_e.net_return_ann_pct, abs_tol=1e-2)
        assert math.isclose(agg.sharpe_ratio, kospi_e.sharpe_ratio, abs_tol=1e-2)

    def test_random_synthetic_metric_profiles_fuzzing(self):
        """
        Fuzzing test: generate 20 randomized synthetic market profiles with extreme values
        (negative returns, extreme MDD, huge Sharpe) and verify mathematical invariants.
        """
        random.seed(42)
        for trial in range(20):
            gross = round(random.uniform(-50.0, 150.0), 2)
            net = round(gross - random.uniform(0.1, 5.0), 2)
            mdd = round(-abs(random.uniform(0.01, 50.0)), 2)
            sharpe = round(random.uniform(-2.0, 20.0), 2)

            metric = QuantitativeMetrics(
                gross_return_ann_pct=gross,
                net_return_ann_pct=net,
                total_return_ann_pct=net + 0.1,
                sharpe_ratio=sharpe,
                spearman_rank_ic=round(random.uniform(-0.1, 0.6), 3),
                pearson_ic=round(random.uniform(-0.1, 0.6), 3),
                max_drawdown_pct=mdd,
                turnover_ann_pct=round(random.uniform(1.0, 100.0), 1),
                friction_cost_bps=round(random.uniform(0.1, 5.0), 2),
                top_decile_spread_pct=round(random.uniform(10.0, 90.0), 1),
                top_decile_sharpe=round(random.uniform(1.0, 20.0), 2),
                execution_slippage_bps=round(random.uniform(0.01, 2.0), 2),
                darkpool_savings_bps=round(random.uniform(10.0, 60.0), 1),
                win_rate_pct=round(random.uniform(50.0, 100.0), 1),
                profit_factor=round(random.uniform(0.5, 20.0), 2),
            )

            # Check post_init calculations
            assert math.isclose(metric.calmar_ratio, round(abs(net / mdd), 2), abs_tol=1e-2)
            if sharpe > 0:
                assert math.isclose(metric.sortino_ratio, round(sharpe * 1.977, 2), abs_tol=1e-2)
            if sharpe >= 10.5:
                assert metric.deflated_sharpe_ratio == 1.000

    def test_markdown_report_generation_with_perturbed_inputs(self):
        """
        Verify generate_phase17_markdown_report handles custom subset results
        and does not raise formatting or key errors.
        """
        engine = Phase17QuantBenchmarkEngine(markets=["SP500", "NASDAQ"])
        res = engine.run_benchmark(weights={"SP500": 0.60, "NASDAQ": 0.40})
        md = generate_phase17_markdown_report(res)

        assert isinstance(md, str)
        assert len(md) > 500
        assert "[표 1] 15대 종합 지표 비교표" in md
        assert "S&P 500" in md
        assert "NASDAQ" in md
