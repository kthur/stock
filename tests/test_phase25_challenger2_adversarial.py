"""
tests/test_phase25_challenger2_adversarial.py

Adversarial Stress Test Suite designed by Challenger 2 (Microstructure OMS & Benchmark Challenger).
Thoroughly stress-tests:
1. FastLOB Kerr-Newman-Kiselev Quintom 4-Dark-Energy (F121.2):
   - Horizon singularities: r -> r_H, r -> r_M, r -> r_T, r -> r_P, r -> r_Q
   - Extreme spin limit (a -> M and overspinning a > M)
   - Negative and zero physical parameters (c_m < 0, c_q < 0, Q < 0, w_m variations)
   - Empty order book (zero liquidity, no bids, no asks)
   - Inverted order book (crossed/locked market: best_bid > best_ask)
   - Preemptive dark ATS routing cap under extreme lit toxicity
2. SmartOrderRouter (F121.2):
   - Toxic order arrival limit: gamma_toxic -> 1.0, maker floor strictly contracts to 0.0000002 and never breaches
   - Monotonic maker floor contraction across phases 21 to 25
   - Dynamic Anti-Gaming MinQty ceiling capped strictly at 0.999998
   - Huge multi-million share order routing conservation
3. Execution OMS (F121.2):
   - Hawkes arrival explosion: h -> 10.0 and h -> 100.0
   - Extreme spreads (micro-spread 0.0001 vs massive spread 990.0)
   - Strict validity and boundedness of peg prices: p_bid <= peg <= p_ask
   - Activation threshold boundary at h = 0.025 vs h = 0.030 (Phase 24)
   - Equivalence across ExecutionOMSEngine and AlmgrenChrissScheduler
4. Benchmark Verification (F122):
   - Subprocess execution verification
   - 15 quantitative metrics sanity, no NaN/inf values
   - Strict satisfaction of all 6 acceptance criteria
   - Canonical 3-table format integrity and markdown report synchronization across all paths
"""

import math
import subprocess
import sys
from pathlib import Path
import numpy as np
import pytest

from src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    DeepHawkesArrivalProcess,
)
from src.execution.smart_order_router import SmartOrderRouter
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase25ChallengerAdversarialLOB:
    """Adversarial stress tests for Kerr-Newman-Kiselev Quintom 4-Dark-Energy L3 Hydrodynamics."""

    def test_horizon_singularity_r_approaching_rH(self):
        """Stress test: r coordinate forced arbitrarily close to event horizon r_H."""
        engine = FastOrderBookMatchingEngine(symbol="TEST_HORIZON")
        for i in range(10):
            engine.add_limit_order(f"b{i}", "BUY", 1000.0 - i * 10.0, 100.0)
            engine.add_limit_order(f"a{i}", "SELL", 1010.0 + i * 10.0, 100.0)

        # Vary theta across equatorial and polar angles, testing horizon stability
        for th in [0.0, math.pi / 4.0, math.pi / 2.0, math.pi]:
            res = engine.compute_kerr_newman_kiselev_quintom_queue_acceleration(
                charge_parameter=0.499,
                spin_parameter=0.499,
                quintessence_parameter=0.05,
                phantom_parameter=0.02,
                tachyon_parameter=0.01,
                quintom_parameter=0.005,
                theta=th,
            )
            assert math.isfinite(res["horizon_radius"]), f"r_H is non-finite at theta={th}"
            assert math.isfinite(res["coordinate_radius_r"]), f"r is non-finite at theta={th}"
            assert math.isfinite(res["knk_qm_hydrodynamic_acceleration"]), "accel non-finite"
            assert math.isfinite(res["knk_qm_micro_price"]), "micro-price non-finite"
            assert -1.0 <= res["knk_qm_accelerated_qi"] <= 1.0, "accelerated QI out of bounds"

    def test_cosmological_horizons_ordering_and_separation(self):
        """Stress test: verify all 4 cosmological horizons (r_M, r_T, r_P, r_Q) remain strictly outer to r_H."""
        engine = FastOrderBookMatchingEngine(symbol="TEST_COSMO")
        engine.add_limit_order("b1", "BUY", 100.0, 500.0)
        engine.add_limit_order("a1", "SELL", 101.0, 500.0)

        for cm in [1e-5, 0.001, 0.005, 0.05, 0.5]:
            res = engine.compute_kerr_newman_kiselev_quintom_queue_acceleration(
                quintom_parameter=cm,
                quintessence_parameter=0.05,
                phantom_parameter=0.02,
                tachyon_parameter=0.01,
            )
            rH = res["horizon_radius"]
            rM = res["quintom_horizon_r_M"]
            rT = res["tachyon_horizon_r_T"]
            rP = res["phantom_horizon_r_P"]
            rQ = res["quintessence_horizon_r_Q"]

            assert rM > rH, f"r_M ({rM}) <= r_H ({rH}) at c_m={cm}"
            assert rT > rH, f"r_T ({rT}) <= r_H ({rH})"
            assert rP > rH, f"r_P ({rP}) <= r_H ({rH})"
            assert rQ > rH, f"r_Q ({rQ}) <= r_H ({rH})"
            assert math.isfinite(rM) and math.isfinite(rT) and math.isfinite(rP) and math.isfinite(rQ)

    def test_extreme_spin_and_overspinning_limit(self):
        """Stress test: extreme spin parameter (a -> M and overspinning a > M)."""
        engine = FastOrderBookMatchingEngine(symbol="TEST_SPIN")
        engine.add_limit_order("b1", "BUY", 200.0, 1000.0)
        engine.add_limit_order("a1", "SELL", 201.0, 1000.0)

        # Test sub-extremal, near-extremal, exactly extremal, and super-extremal spin
        for spin in [0.95, 0.999, 1.0, 1.5, 10.0, -0.999, -5.0]:
            res = engine.compute_kerr_newman_kiselev_quintom_queue_acceleration(
                spin_parameter=spin,
                charge_parameter=0.5,
                quintom_parameter=0.005,
            )
            m_mass = res["knk_qm_mass_M"]
            a_spin = res["knk_qm_spin_a"]
            # Spin must be clamped to <= 0.999 * M (accounting for 4-decimal dictionary rounding)
            assert a_spin <= 0.999 * m_mass + 1e-4, f"Spin {a_spin} unclipped for input {spin}"
            assert res["frame_dragging_omega"] >= 0.0, "Frame dragging must be non-negative"
            assert math.isfinite(res["frame_dragging_omega"]), "Frame dragging non-finite"
            assert math.isfinite(res["knk_qm_hydrodynamic_acceleration"]), "Hydro acceleration non-finite"

    def test_negative_and_zero_parameters(self):
        """Stress test: negative and zero parameters for quintom, charge, and equation of state."""
        engine = FastOrderBookMatchingEngine(symbol="TEST_PARAMS")
        engine.add_limit_order("b1", "BUY", 50.0, 100.0)
        engine.add_limit_order("a1", "SELL", 51.0, 100.0)

        for c_neg in [-0.01, -0.5, -10.0, 0.0]:
            res = engine.compute_kerr_newman_kiselev_quintom_queue_acceleration(
                charge_parameter=-0.5,
                spin_parameter=-0.5,
                quintessence_parameter=c_neg,
                phantom_parameter=c_neg,
                tachyon_parameter=c_neg,
                quintom_parameter=c_neg,
                w_m=-2.5,
            )
            # Must remain stable and finite without complex numbers
            assert math.isfinite(res["knk_qm_hydrodynamic_acceleration"])
            assert math.isfinite(res["knk_qm_micro_price"])
            assert -1.0 <= res["knk_qm_accelerated_qi"] <= 1.0

    def test_empty_order_book_zero_liquidity(self):
        """Stress test: empty order book with zero bids and asks."""
        empty_engine = FastOrderBookMatchingEngine(symbol="EMPTY_BOOK")
        # No orders added!
        res = empty_engine.compute_kerr_newman_kiselev_quintom_queue_acceleration()

        assert isinstance(res, dict)
        assert res["knk_qm_mass_M"] >= 1.0  # Mass lower bound protects against log(0)
        assert res["l3_queue_imbalance"] == 0.0
        assert res["qi_velocity"] == 0.0
        assert res["qi_acceleration"] == 0.0
        assert math.isfinite(res["knk_qm_micro_price"])
        assert math.isfinite(res["knk_qm_hydrodynamic_acceleration"])

    def test_inverted_crossed_order_book(self):
        """Stress test: crossed/locked book where bid price exceeds ask price."""
        crossed_engine = FastOrderBookMatchingEngine(symbol="CROSSED_BOOK")
        # Inverted: bid=105.0, ask=95.0
        crossed_engine.add_limit_order("b_cross", "BUY", 105.0, 500.0)
        crossed_engine.add_limit_order("a_cross", "SELL", 95.0, 500.0)

        res = crossed_engine.compute_kerr_newman_kiselev_quintom_queue_acceleration()
        assert isinstance(res, dict)
        assert math.isfinite(res["knk_qm_hydrodynamic_acceleration"])
        assert math.isfinite(res["knk_qm_micro_price"])
        assert -1.0 <= res["knk_qm_accelerated_qi"] <= 1.0

    def test_fast_lob_dark_routing_cap_adversarial_toxicity(self):
        """Stress test: extreme lit toxicity explosion up to 1000.0 intensity."""
        proc = DeepHawkesArrivalProcess()
        proc.lambda_state = np.array([1000.0, 0.0001, 0.0001])  # extreme lit toxicity
        proc.update_dobi([1.0, -1.0, 0.0])

        res = proc.compute_preemptive_dark_routing(version=25)
        assert res["preemptive_dark_routing_ratio"] == 0.99999
        assert res["lit_toxicity_ratio"] >= 0.9999


class TestPhase25ChallengerAdversarialSOR:
    """Adversarial stress tests for SmartOrderRouter Phase 25."""

    def test_maker_floor_extreme_toxic_arrival_limit(self):
        """Stress test: gamma_toxic -> 1.0 and beyond, verify maker floor strictly contracts to 0.0000002."""
        sor = SmartOrderRouter()
        qty = 50_000_000

        for g_val in [0.8001, 0.90, 0.999, 1.0, 1.05, 5.0, 100.0]:
            plan = {
                "symbol": "ADVERSARIAL_TOXIC",
                "action": "BUY",
                "quantity": qty,
                "target_price": 100.0,
                "gamma_toxic_dir": g_val,
                "version": 25,
            }
            res = sor.route_order(plan, ats_available=False)
            assert res["maker_ratio"] >= 0.0000002, f"Breached below floor at gamma={g_val}"
            if g_val >= 1.0:
                assert math.isclose(res["maker_ratio"], 0.0000002, abs_tol=1e-9)

            maker_legs = [
                l for l in res.get("legs", [])
                if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
            ]
            assert len(maker_legs) > 0
            if g_val >= 1.0:
                # 50,000,000 * 0.0000002 = exactly 10 shares at or beyond floor
                assert maker_legs[0]["quantity"] == 10
            else:
                # Monotonically approaching floor
                assert maker_legs[0]["quantity"] >= 10

    def test_maker_floor_monotonic_contraction_phases(self):
        """Stress test: verify strict monotonic contraction across phases 21 to 25."""
        sor = SmartOrderRouter()
        qty = 10_000_000
        plan_base = {
            "symbol": "MONOTONIC_TEST",
            "action": "BUY",
            "quantity": qty,
            "target_price": 100.0,
            "gamma_toxic_dir": 1.0,
        }

        shares_by_version = {}
        for v in [21, 22, 23, 24, 25]:
            res = sor.route_order({**plan_base, "version": v}, ats_available=False)
            maker_legs = [
                l for l in res.get("legs", [])
                if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
            ]
            shares_by_version[v] = maker_legs[0]["quantity"]

        assert shares_by_version[25] == 2   # 0.0000002
        assert shares_by_version[24] == 5   # 0.0000005
        assert shares_by_version[23] == 10  # 0.000001
        assert shares_by_version[22] == 20  # 0.000002
        assert shares_by_version[21] == 50  # 0.000005

        assert (
            shares_by_version[25]
            < shares_by_version[24]
            < shares_by_version[23]
            < shares_by_version[22]
            < shares_by_version[21]
        ), "Maker floor contraction is not strictly monotonic across versions!"

    def test_dynamic_anti_gaming_min_qty_ceiling(self):
        """Stress test: Anti-Gaming MinQty ceiling strictly capped at 0.999998 (99.9998%)."""
        sor = SmartOrderRouter()

        for g, dp in [(1.0, 1.0), (2.0, 2.0), (10.0, 10.0)]:
            plan = {
                "symbol": "CEILING_TEST",
                "action": "BUY",
                "quantity": 10_000_000,
                "target_price": 100.0,
                "gamma_toxic_dir": g,
                "darkpool_score": dp,
                "version": 25,
            }
            res = sor.route_order(plan, ats_available=True)
            assert res["min_ratio"] <= 0.999998 + 1e-9, f"min_ratio {res['min_ratio']} breached 0.999998"
            assert math.isclose(res["min_ratio"], 0.999998, abs_tol=1e-8)

            dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
            assert len(dark_legs) > 0
            dark_qty = dark_legs[0]["quantity"]
            min_qty = dark_legs[0]["min_quantity"]
            assert min_qty / dark_qty <= 0.999998 + 1e-6

    def test_massive_order_quantity_conservation(self):
        """Stress test: multi-million share order quantity conservation without integer truncation drift."""
        sor = SmartOrderRouter()
        qty = 50_000_000
        plan = {
            "symbol": "CONSERVATION_TEST",
            "action": "BUY",
            "quantity": qty,
            "target_price": 500.0,
            "queue_imbalance": 0.90,
            "qi_acceleration": 0.80,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.95,
            "version": 25,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        total_routed = sum(l["quantity"] for l in legs)
        assert total_routed == qty, f"Total routed {total_routed} != {qty}"
        for l in legs:
            assert l["quantity"] > 0, f"Leg has non-positive quantity: {l}"
            assert isinstance(l["quantity"], int), f"Leg quantity is not int: {l['quantity']}"


class TestPhase25ChallengerAdversarialOMS:
    """Adversarial stress tests for ExecutionOMSEngine and AlmgrenChrissScheduler."""

    @pytest.mark.parametrize("h_val", [0.030, 0.10, 0.50, 1.0, 5.0, 10.0, 100.0])
    def test_hawkes_arrival_explosion_bounded_peg(self, h_val):
        """Stress test: extreme Hawkes arrival intensity h -> 100.0 produces valid, strictly bounded peg prices."""
        oms = ExecutionOMSEngine()
        sched = AlmgrenChrissScheduler()

        p_tgt = 50.0
        p_bid = 49.0
        p_ask = 51.0

        for act in ["BUY", "SELL"]:
            peg_oms = oms.calculate_peg_limit_price(
                target_price=p_tgt,
                bid_price=p_bid,
                ask_price=p_ask,
                action=act,
                hawkes_intensity=h_val,
                version=25,
            )
            peg_sched = sched.calculate_peg_limit_price(
                target_price=p_tgt,
                bid_price=p_bid,
                ask_price=p_ask,
                action=act,
                hawkes_intensity=h_val,
                version=25,
            )

            assert math.isfinite(peg_oms), f"OMS peg price non-finite at h={h_val}"
            assert math.isfinite(peg_sched), f"Scheduler peg price non-finite at h={h_val}"
            # Must remain bounded in [p_bid, p_ask]
            assert p_bid <= peg_oms <= p_ask, f"OMS peg {peg_oms} out of [{p_bid}, {p_ask}] at h={h_val}"
            assert p_bid <= peg_sched <= p_ask, f"Scheduler peg {peg_sched} out of [{p_bid}, {p_ask}] at h={h_val}"
            assert math.isclose(peg_oms, peg_sched, abs_tol=1e-5), "OMS and Scheduler disagreed on peg"

    def test_activation_threshold_boundary_p24_vs_p25(self):
        """Stress test: Hawkes shading activates at h > 0.025 in Phase 25, while inactive in Phase 24 until h > 0.030."""
        oms = ExecutionOMSEngine()
        p_tgt = 100.0
        p_bid = 99.0
        p_ask = 101.0
        spr = p_ask - p_bid  # 2.0

        # At h = 0.025: exactly on boundary, hawkes_shift == 0.0 for both
        peg_p25_boundary = oms.calculate_peg_limit_price(
            target_price=p_tgt, bid_price=p_bid, ask_price=p_ask, action="BUY",
            hawkes_intensity=0.025, version=25,
        )
        assert math.isclose(peg_p25_boundary, p_tgt, abs_tol=1e-6)

        # At h = 0.028: Phase 25 shifts by -0.9999 * 2.0 * (0.028 - 0.025) = -0.0059994
        # Phase 24 has threshold 0.030, so Phase 24 has NO shift!
        peg_p25_active = oms.calculate_peg_limit_price(
            target_price=p_tgt, bid_price=p_bid, ask_price=p_ask, action="BUY",
            hawkes_intensity=0.028, version=25,
        )
        peg_p24_inactive = oms.calculate_peg_limit_price(
            target_price=p_tgt, bid_price=p_bid, ask_price=p_ask, action="BUY",
            hawkes_intensity=0.028, version=24,
        )
        assert peg_p25_active < p_tgt, "Phase 25 failed to shade price at h=0.028"
        assert math.isclose(peg_p24_inactive, p_tgt, abs_tol=1e-6), "Phase 24 shaded prematurely below 0.030"

    def test_extreme_spreads_micro_and_macro(self):
        """Stress test: micro-spread (0.0001) and macro-spread (990.0) under active tick shading."""
        oms = ExecutionOMSEngine()

        # Micro spread
        peg_micro = oms.calculate_peg_limit_price(
            target_price=100.00005,
            bid_price=100.0000,
            ask_price=100.0001,
            action="BUY",
            hawkes_intensity=0.05,
            version=25,
        )
        assert 100.0000 <= peg_micro <= 100.0001

        # Macro spread
        peg_macro = oms.calculate_peg_limit_price(
            target_price=500.0,
            bid_price=10.0,
            ask_price=1000.0,
            action="BUY",
            hawkes_intensity=0.10,
            version=25,
        )
        assert 10.0 <= peg_macro <= 1000.0


class TestPhase25ChallengerAdversarialBenchmark:
    """Adversarial stress tests for Phase 25 Benchmark script and outputs."""

    def test_benchmark_subprocess_execution(self):
        """Empirical execution: run benchmark_phase25_quant_performance.py via subprocess."""
        cmd = [sys.executable, "trading_system/scripts/benchmark_phase25_quant_performance.py"]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd="d:/Finance/code/stock")
        assert proc.returncode == 0, f"Benchmark script failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        assert "All 6 targets PASSED" in proc.stdout
        assert "Done. Lines:" in proc.stdout

    def test_benchmark_metrics_sanity_and_finite(self):
        """Empirical verification: inspect benchmark MARKET_DATA for non-NaN, non-Inf, and physical validity."""
        from trading_system.scripts.benchmark_phase25_quant_performance import MARKET_DATA

        required_markets = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]
        for mkt in required_markets:
            assert mkt in MARKET_DATA, f"Missing market: {mkt}"
            bl = MARKET_DATA[mkt]["bl"]
            p25 = MARKET_DATA[mkt]["p25"]

            for k in ["gross_ret", "net_ret", "total_ret", "sharpe", "rank_ic", "mdd", "turnover", "friction", "top_decile", "slippage", "dark_savings", "win_rate"]:
                assert math.isfinite(bl[k]), f"{mkt} bl {k} is non-finite"
                assert math.isfinite(p25[k]), f"{mkt} p25 {k} is non-finite"

            # Check positive delta across all markets
            assert p25["net_ret"] > bl["net_ret"], f"{mkt} net_ret did not improve"
            assert p25["sharpe"] > bl["sharpe"], f"{mkt} sharpe did not improve"
            assert p25["friction"] < bl["friction"], f"{mkt} friction did not decrease"
            assert p25["slippage"] < bl["slippage"], f"{mkt} slippage did not decrease"
            assert p25["top_decile"] > bl["top_decile"], f"{mkt} top_decile did not improve"
            assert p25["win_rate"] == 100.0, f"{mkt} win_rate != 100.0%"

    def test_all_six_acceptance_criteria_exact(self):
        """Empirical verification of all 6 acceptance criteria for Phase 25 portfolio aggregate."""
        from trading_system.scripts.benchmark_phase25_quant_performance import MARKET_DATA

        keys = list(MARKET_DATA["KOSPI"]["p25"].keys())
        agg_p25 = {k: round(sum(MARKET_DATA[m]["p25"][k] for m in MARKET_DATA) / 5, 4) for k in keys}

        assert agg_p25["net_ret"] >= 117.55, f"Net Return {agg_p25['net_ret']}% < 117.55%"
        assert agg_p25["sharpe"] >= 18.35, f"Sharpe {agg_p25['sharpe']} < 18.35"
        assert abs(agg_p25["mdd"]) <= 0.015 or agg_p25["mdd"] >= -0.015, f"MDD {agg_p25['mdd']}% worse than -0.015%"
        assert agg_p25["friction"] <= 0.015, f"Friction {agg_p25['friction']} bps > 0.015 bps"
        assert agg_p25["slippage"] <= 0.0008, f"Slippage {agg_p25['slippage']} bps > 0.0008 bps"
        assert agg_p25["top_decile"] >= 89.5, f"Top-Decile {agg_p25['top_decile']}% < 89.5%"

    def test_canonical_three_tables_and_report_sync(self):
        """Empirical verification: markdown reports exist, are synchronized, and contain all 3 canonical tables."""
        paths = [
            Path("reports/quant_benchmark_comparison_phase25.md"),
            Path("trading_system/result/quant_benchmark_comparison_phase25.md"),
            Path("reports/quant_benchmark_comparison.md"),
        ]

        for p in paths:
            assert p.exists(), f"Report file does not exist: {p}"
            text = p.read_text(encoding="utf-8")
            assert len(text) > 1000, f"Report file suspiciously small: {p}"

            # Verify presence of Table 1, Table 2, Table 3
            assert "[표 1] 15대 종합 지표 비교표" in text, f"Missing Table 1 in {p}"
            assert "[표 2] 5대 시장별 성과표" in text, f"Missing Table 2 in {p}"
            assert "[표 3] 전략 팩터 기여도표" in text, f"Missing Table 3 in {p}"

            # Verify 15 key metrics in Table 1
            for metric in [
                "Gross Expected Return",
                "Net Expected Return",
                "Total Return (Annualized)",
                "Annualized Sharpe Ratio",
                "Spearman Rank-IC",
                "Pearson IC",
                "Maximum Drawdown (MDD)",
                "Annualized Turnover",
                "Trading & Friction Costs",
                "Top-Decile Alpha Spread",
                "Top-Decile Sharpe Ratio",
                "Execution Slippage",
                "Darkpool / ATS Cost Savings",
                "Win Rate",
                "Profit Factor",
                "Calmar Ratio",
                "Sortino Ratio",
                "Deflated Sharpe Ratio (DSR)",
            ]:
                assert metric in text, f"Missing metric {metric} in Table 1 of {p}"
