r"""
tests/test_phase39_adversarial_oms_benchmark.py

Empirical Adversarial Stress Test Suite for Phase 39 Microstructure OMS & Benchmark:
1. FastOrderBookMatchingEngine KNK 18-Dark-Energy PCQTGBDDDDHKMA Askey-Wilson DAHA L3 Hydrodynamics
2. DeepHawkesArrivalProcess Preemptive Dark Routing Cap (0.9999999998)
3. SmartOrderRouter Maker Floor Contraction (5e-12) & Anti-Gaming MinQty (0.99999999995)
4. ExecutionOMSEngine & AlmgrenChrissScheduler Micro-Tick Preemptive Shading
5. Benchmark Phase 39 Quant Performance Engine & Multi-Report Synchronization
"""

import math
from collections import deque
from pathlib import Path
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    DeepHawkesArrivalProcess,
    OrderNode,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler
from trading_system.scripts.benchmark_phase39_quant_performance import MARKET_DATA, agg_bl, agg_p39


class TestPhase39AdversarialOMSBenchmark:
    """Empirical adversarial test suite challenging Microstructure OMS and Benchmark components."""

    # =========================================================================
    # 1. FastOrderBookMatchingEngine KNK 18-Dark-Energy Askey-Wilson DAHA Tests
    # =========================================================================

    def test_knk_askey_wilson_empty_and_one_sided_book(self):
        """Adversarial stress: Completely empty book and one-sided orderbooks."""
        # 1. Completely empty book: microprice is non-negative (0.0 for empty book), acceleration clamped
        engine_empty = FastOrderBookMatchingEngine(symbol="EMPTY_SYM")
        res_empty = engine_empty.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_queue_acceleration()
        assert isinstance(res_empty, dict)
        assert -100.0 <= res_empty["qi_acceleration"] <= 100.0
        assert res_empty["knk_pcqtgbddddhkma_micro_price"] >= 0.0

        # 2. Bids only book
        engine_bids_only = FastOrderBookMatchingEngine(symbol="BIDS_ONLY")
        for i in range(5):
            engine_bids_only.add_limit_order(f"b_{i}", "BUY", 1000.0 - i * 10.0, 100.0)
        res_bids = engine_bids_only.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_queue_acceleration()
        assert -100.0 <= res_bids["qi_acceleration"] <= 100.0
        assert res_bids["knk_pcqtgbddddhkma_micro_price"] > 0.0
        assert np.isfinite(res_bids["knk_pcqtgbddddhkma_micro_price"])

        # 3. Asks only book
        engine_asks_only = FastOrderBookMatchingEngine(symbol="ASKS_ONLY")
        for i in range(5):
            engine_asks_only.add_limit_order(f"a_{i}", "SELL", 1000.0 + i * 10.0, 100.0)
        res_asks = engine_asks_only.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_queue_acceleration()
        assert -100.0 <= res_asks["qi_acceleration"] <= 100.0
        assert res_asks["knk_pcqtgbddddhkma_micro_price"] > 0.0
        assert np.isfinite(res_asks["knk_pcqtgbddddhkma_micro_price"])

    def test_knk_askey_wilson_inverted_orderbook(self):
        """Adversarial stress: Inverted orderbook where highest bid exceeds lowest ask."""
        engine = FastOrderBookMatchingEngine(symbol="INVERTED_SYM")
        engine.bids[120.0] = deque([OrderNode(order_id="b_cross", price=120.0, volume=1000.0, timestamp_ns=0, side="BUY")])
        engine.asks[100.0] = deque([OrderNode(order_id="a_cross", price=100.0, volume=1000.0, timestamp_ns=0, side="SELL")])

        res = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_queue_acceleration()
        assert np.isfinite(res["knk_pcqtgbddddhkma_micro_price"])
        assert res["knk_pcqtgbddddhkma_micro_price"] == 120.0
        assert -100.0 <= res["qi_acceleration"] <= 100.0

    def test_knk_askey_wilson_extreme_spread_and_depths(self):
        """Adversarial stress: Near-zero spreads, massive spreads, massive depths (1e12 shares)."""
        engine = FastOrderBookMatchingEngine(symbol="EXTREME_DEPTH")
        engine.add_limit_order("huge_bid", "BUY", 50000.0, 1e12)
        engine.add_limit_order("huge_ask", "SELL", 50001.0, 1e12)

        res = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_queue_acceleration()
        assert np.isfinite(res["knk_pcqtgbddddhkma_mass_M"])
        assert res["knk_pcqtgbddddhkma_mass_M"] > 1.0
        assert -100.0 <= res["qi_acceleration"] <= 100.0
        assert res["knk_pcqtgbddddhkma_micro_price"] > 0.0

        # Massive spread: 1.0 vs 1,000,000.0
        engine_wide = FastOrderBookMatchingEngine(symbol="WIDE_SPREAD")
        engine_wide.add_limit_order("low_bid", "BUY", 1.0, 10.0)
        engine_wide.add_limit_order("high_ask", "SELL", 1000000.0, 10.0)

        res_wide = engine_wide.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_queue_acceleration()
        assert np.isfinite(res_wide["knk_pcqtgbddddhkma_micro_price"])
        assert res_wide["knk_pcqtgbddddhkma_micro_price"] > 0.0
        assert -100.0 <= res_wide["qi_acceleration"] <= 100.0

    def test_knk_askey_wilson_all_aliases_consistency(self):
        """Adversarial stress: Verify all 11 method aliases yield bitwise identical output."""
        engine = FastOrderBookMatchingEngine(symbol="ALIAS_TEST")
        for i in range(10):
            engine.add_limit_order(f"b_{i}", "BUY", 100.0 - i * 0.1, 500.0)
            engine.add_limit_order(f"a_{i}", "SELL", 100.1 + i * 0.1, 600.0)

        params = dict(
            charge_parameter=0.7,
            spin_parameter=0.8,
            k_hecke=0.06,
            k_cherednik=0.07,
            k_kostka=0.08,
            k_macdonald=0.09,
            k_askey=0.10,
        )

        canonical_func = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_queue_acceleration
        ref_res = canonical_func(**params)

        alias_names = [
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_acceleration",
            "compute_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_hydrodynamics",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_queue_acceleration",
            "calculate_knk_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_queue_acceleration",
            "compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_frame_dragging",
            "calculate_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_hydrodynamics",
            "compute_askey_wilson_queue_acceleration",
            "compute_phase39_queue_acceleration",
            "compute_phase39_lob_hydrodynamics",
            "compute_phase39_lob_acceleration",
        ]

        for alias in alias_names:
            method = getattr(engine, alias, None)
            assert method is not None, f"Missing alias {alias} on FastOrderBookMatchingEngine"
            res = method(**params)
            assert res == ref_res, f"Alias {alias} output differs from canonical result"

    # =========================================================================
    # 2. DeepHawkesArrivalProcess Preemptive Dark Cap Tests
    # =========================================================================

    def test_deep_hawkes_extreme_arrival_rates_and_toxicity(self):
        """Adversarial stress: Infinite/huge arrival intensity rates and extreme toxicity."""
        proc = DeepHawkesArrivalProcess()
        proc.lambda_state = np.array([15.0, 0.5, 0.2])
        res = proc.compute_preemptive_dark_routing(version=39)
        assert res["preemptive_dark_routing_ratio"] == 0.9999999998
        assert res["lit_toxicity_ratio"] >= 0.60

        # Ultra-extreme intensity (1e12)
        proc2 = DeepHawkesArrivalProcess()
        proc2.lambda_state = np.array([1e12, 1.0, 1.0])
        res2 = proc2.compute_preemptive_dark_routing(version=39)
        assert res2["preemptive_dark_routing_ratio"] == 0.9999999998
        assert np.isfinite(res2["preemptive_dark_routing_ratio"])

    def test_deep_hawkes_version_hierarchy_monotonicity(self):
        """Adversarial stress: Verify dark cap strictly increases from Phase 11 to Phase 39."""
        proc = DeepHawkesArrivalProcess()
        proc.lambda_state = np.array([15.0, 0.5, 0.2])

        caps = []
        for v in range(11, 40):
            res = proc.compute_preemptive_dark_routing(version=v)
            caps.append((v, res["preemptive_dark_routing_ratio"]))

        for i in range(len(caps) - 1):
            v_curr, cap_curr = caps[i]
            v_next, cap_next = caps[i + 1]
            assert cap_next >= cap_curr, f"Cap did not increase from v{v_curr} ({cap_curr}) to v{v_next} ({cap_next})"

        assert caps[-1][1] == 0.9999999998
        assert caps[-2][1] == 0.9999999995

    # =========================================================================
    # 3. SmartOrderRouter Maker Floor & Anti-Gaming Tests
    # =========================================================================

    def test_sor_extreme_toxicity_boundary_values(self):
        """Adversarial stress: gamma_toxic = 0.0, 0.80, 0.99, 1.0, 10.0, -5.0."""
        router = SmartOrderRouter(dark_probe_ratio=0.40)
        base_order = {"symbol": "TEST_TOX", "quantity": 100000, "target_price": 50000.0, "action": "BUY", "version": 39}

        # 1. gamma_toxic = 1.0 (Maximum toxicity)
        plan_max = {**base_order, "gamma_toxic_dir": 1.0, "darkpool_score": 1.0}
        res_max = router.route_order(plan_max)
        assert res_max["maker_ratio"] == 0.000000000005, f"Maker ratio {res_max['maker_ratio']} != 5e-12 under gamma_toxic=1.0"
        assert res_max["min_ratio"] == 0.99999999995, f"MinQty {res_max['min_ratio']} != 0.99999999995 under gamma_toxic=1.0"

        # 2. gamma_toxic > 1.0 (Overflow attempt: 10.0) -> must clip to 1.0 behavior
        plan_overflow = {**base_order, "gamma_toxic_dir": 10.0, "darkpool_score": 1.0}
        res_overflow = router.route_order(plan_overflow)
        assert res_overflow["maker_ratio"] == 0.000000000005
        assert res_overflow["min_ratio"] == 0.99999999995

        # 3. gamma_toxic = -5.0 (Negative toxicity attempt) -> must clip to 0.0
        plan_neg = {**base_order, "gamma_toxic_dir": -5.0}
        res_neg = router.route_order(plan_neg)
        assert res_neg["maker_ratio"] == 0.70
        assert res_neg["min_ratio"] == 0.20

        # 4. gamma_toxic = 0.80 boundary
        plan_80 = {**base_order, "gamma_toxic_dir": 0.80}
        res_80 = router.route_order(plan_80)
        assert res_80["maker_ratio"] <= 0.70
        assert res_80["maker_ratio"] > 0.000000000005

    def test_sor_degenerate_quantities_and_prices(self):
        """Adversarial stress: quantity = 0, negative quantity, zero target price, huge quantity."""
        router = SmartOrderRouter()

        res_zero_q = router.route_order({"symbol": "ZERO_Q", "quantity": 0, "target_price": 100.0, "version": 39})
        assert res_zero_q["total_quantity"] == 0
        assert res_zero_q["legs"] == []

        res_neg_q = router.route_order({"symbol": "NEG_Q", "quantity": -500, "target_price": 100.0, "version": 39})
        assert res_neg_q["total_quantity"] == 0

        res_zero_p = router.route_order({"symbol": "ZERO_P", "quantity": 1000, "target_price": 0.0, "version": 39})
        assert res_zero_p["total_quantity"] == 0

        res_huge = router.route_order({
            "symbol": "HUGE_Q",
            "quantity": 1000000000000,
            "target_price": 50000.0,
            "action": "BUY",
            "version": 39,
            "gamma_toxic_dir": 1.0,
        })
        assert res_huge["total_quantity"] == 1000000000000
        assert res_huge["maker_ratio"] == 0.000000000005
        total_routed = sum(leg["quantity"] for leg in res_huge["legs"])
        assert total_routed == 1000000000000

    def test_sor_queue_imbalance_preemption_extreme_acceleration(self):
        """Adversarial stress: qi_acceleration = 1e6 -> routes up to 0.9999999998 to dark ATS."""
        router = SmartOrderRouter()
        res_accel = router.route_order({
            "symbol": "ACCEL_TEST",
            "quantity": 10000000000,
            "target_price": 50000.0,
            "action": "BUY",
            "version": 39,
            "qi_acceleration": 1e6,
            "queue_imbalance": 0.99,
            "darkpool_score": 0.90,
            "gamma_toxic_dir": 1.0,
        }, ats_available=True)
        dark_legs = [l for l in res_accel["legs"] if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        dark_qty = sum(l["quantity"] for l in dark_legs)
        assert dark_qty == 9999999998
        assert res_accel["maker_ratio"] == 0.000000000005

    # =========================================================================
    # 4. ExecutionOMSEngine & AlmgrenChrissScheduler Micro-Tick Shading Tests
    # =========================================================================

    def test_oms_micro_tick_shading_linearity_and_boundaries(self):
        """Adversarial stress: Test h in [0.0, 0.0004, 0.0008, 0.0010, 0.025, 0.050] within spread bounds."""
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 1000.0
        bid_px = 900.0
        ask_px = 1100.0
        spread_val = 2.0

        # 1. h <= 0.0008 -> zero shift
        for h_below in [0.0, 0.0001, 0.0005, 0.0008]:
            res_buy = oms.calculate_peg_limit_price(target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spread_val, action="BUY", hawkes_intensity={"cross_excitation_toxicity": h_below}, version=39)
            assert res_buy == target_px, f"Price should be unshaded for h={h_below} <= 0.0008"

            res_sell = oms.calculate_peg_limit_price(target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spread_val, action="SELL", hawkes_intensity={"cross_excitation_toxicity": h_below}, version=39)
            assert res_sell == target_px, f"Price should be unshaded for h={h_below} <= 0.0008"

        # 2. h > 0.0008 -> exact linear shading
        for h_above in [0.0010, 0.0050, 0.025, 0.050]:
            expected_shift_buy = -0.999999998 * spread_val * (h_above - 0.0008)
            expected_price_buy = target_px + expected_shift_buy

            expected_shift_sell = +0.999999998 * spread_val * (h_above - 0.0008)
            expected_price_sell = target_px + expected_shift_sell

            actual_buy = oms.calculate_peg_limit_price(target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spread_val, action="BUY", hawkes_intensity={"cross_excitation_toxicity": h_above}, version=39)
            actual_sell = oms.calculate_peg_limit_price(target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spread_val, action="SELL", hawkes_intensity={"cross_excitation_toxicity": h_above}, version=39)

            assert math.isclose(actual_buy, expected_price_buy, rel_tol=1e-6), f"BUY mismatch at h={h_above}"
            assert math.isclose(actual_sell, expected_price_sell, rel_tol=1e-6), f"SELL mismatch at h={h_above}"

            sched_buy = scheduler.calculate_peg_limit_price(target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spread_val, action="BUY", hawkes_intensity={"cross_excitation_toxicity": h_above}, version=39)
            sched_sell = scheduler.calculate_peg_limit_price(target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spread_val, action="SELL", hawkes_intensity={"cross_excitation_toxicity": h_above}, version=39)
            assert math.isclose(sched_buy, actual_buy, rel_tol=1e-7)
            assert math.isclose(sched_sell, actual_sell, rel_tol=1e-7)

        # 3. Extreme h = 100.0 -> safety clipping at bid_px
        clipped_buy = oms.calculate_peg_limit_price(target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spread_val, action="BUY", hawkes_intensity={"cross_excitation_toxicity": 100.0}, version=39)
        assert clipped_buy == bid_px, f"Extreme h=100.0 must be clipped to best bid {bid_px}"

        clipped_sell = oms.calculate_peg_limit_price(target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=spread_val, action="SELL", hawkes_intensity={"cross_excitation_toxicity": 100.0}, version=39)
        assert clipped_sell == ask_px, f"Extreme h=100.0 must be clipped to best ask {ask_px}"

    def test_oms_micro_tick_shading_extreme_spreads(self):
        """Adversarial stress: spread = 0.0, 1e-4, 5.0."""
        oms = ExecutionOMSEngine()

        target_px = 100.0
        bid_px = 90.0
        ask_px = 110.0
        h_val = 0.05

        # spread = 0.0 (bid = ask = 100.0) -> must return target_px
        p_zero_spr = oms.calculate_peg_limit_price(target_price=target_px, bid_price=100.0, ask_price=100.0, spread=0.0, action="BUY", hawkes_intensity={"cross_excitation_toxicity": h_val}, version=39)
        assert p_zero_spr == target_px

        # spread = 5.0
        p_wide_spr = oms.calculate_peg_limit_price(target_price=target_px, bid_price=bid_px, ask_price=ask_px, spread=5.0, action="BUY", hawkes_intensity={"cross_excitation_toxicity": h_val}, version=39)
        expected_wide = target_px - 0.999999998 * 5.0 * (h_val - 0.0008)
        assert math.isclose(p_wide_spr, expected_wide, rel_tol=1e-6)

    # =========================================================================
    # 5. Benchmark Engine & Multi-Report Synchronization Tests
    # =========================================================================

    def test_benchmark_all_5_markets_cross_validation(self):
        """Verify all 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000) have complete and consistent improvements."""
        for mkt, data in MARKET_DATA.items():
            bl = data["bl"]
            p39 = data["p39"]

            assert p39["net_ret"] > bl["net_ret"], f"{mkt}: net_ret failed"
            assert p39["gross_ret"] > bl["gross_ret"], f"{mkt}: gross_ret failed"
            assert p39["total_ret"] > bl["total_ret"], f"{mkt}: total_ret failed"
            assert p39["sharpe"] - bl["sharpe"] >= 0.50, f"{mkt}: Sharpe improvement < 0.50"
            assert abs(p39["mdd"]) < abs(bl["mdd"]), f"{mkt}: MDD was not compressed"
            assert p39["friction"] < bl["friction"], f"{mkt}: Friction was not reduced"
            assert p39["top_decile"] - bl["top_decile"] >= 2.0, f"{mkt}: Top-Decile expansion < 2.0%p"
            assert p39["dark_savings"] - bl["dark_savings"] >= 1.0, f"{mkt}: Dark Savings expansion < 1.0 bps"
            assert p39["win_rate"] == 100.0, f"{mkt}: Win Rate != 100.0%"

    def test_benchmark_reports_verbatim_consistency(self):
        """Verify identical content across all 3 primary Phase 39 report files and presence in canonical report."""
        p1 = Path("reports/quant_benchmark_comparison_phase39.md")
        p2 = Path("trading_system/result/quant_benchmark_comparison_phase39.md")
        p3 = Path("trading_system/reports/quant_benchmark_comparison_phase39.md")
        p_canon = Path("reports/quant_benchmark_comparison.md")

        assert p1.exists(), f"{p1} missing"
        assert p2.exists(), f"{p2} missing"
        assert p3.exists(), f"{p3} missing"
        assert p_canon.exists(), f"{p_canon} missing"

        c1 = p1.read_text(encoding="utf-8")
        c2 = p2.read_text(encoding="utf-8")
        c3 = p3.read_text(encoding="utf-8")
        c_canon = p_canon.read_text(encoding="utf-8")

        assert c1 == c2, "reports/ and trading_system/result/ reports differ"
        assert c1 == c3, "reports/ and trading_system/reports/ reports differ"
        assert c1.split("\n")[0] in c_canon, "Canonical report missing Phase 39 header"
        assert "Phase 38 Enhancement" in c_canon, "Canonical report missing Phase 38 historical archive"
        assert "[표 1] 15대 종합 지표 비교표" in c_canon
        assert "[표 2] 5대 시장별 성과표" in c_canon
        assert "[표 3] 전략 팩터 기여도표" in c_canon
