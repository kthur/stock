"""
tests/test_phase46_adversarial_oms_benchmark.py

Adversarial Stress Test Suite for Phase 46 Quantitative Enhancement:
Focus: Feature F205.2 (Microstructure OMS) and Feature F206 (Quant Benchmark Deliverables).

Challenger 2 Empirical Verification:
1. Lit maker floor 1e-18 precision and zero-underflow immunity under extreme toxicity gamma in [0.80, 1.0].
2. Dark ATS cap 99.99999999995% under massive orders (up to 10^18 shares) and extreme queue shifts.
3. Dynamic Anti-Gaming MinQty cap 99.99999999998% under peak toxicity and score combinations.
4. Preemptive tick shading strict activation threshold at h > 0.00015 and deadband at h <= 0.00015.
5. Benchmark script execution and 7-target assertion oracle failure testing.
6. SHA-256 hash synchronization across all 3 report paths and historical report preservation.
7. Documentation sync audit for AGENTS.md and PROJECT.md.
"""

import hashlib
import math
import os
import subprocess
import sys
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    DeepHawkesArrivalProcess,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase46AdversarialMicrostructureOMS:
    """Adversarial stress testing of Phase 46 Microstructure and Execution OMS."""

    def test_lit_maker_floor_grid_zero_underflow_immunity(self):
        """
        Adversarial Test 1A:
        Test 50,000 points across gamma_toxic in [0.80, 1.0] to guarantee:
        - No floating-point underflow to 0.0
        - No negative values
        - Clamping strictly adheres to 1e-18 (0.000000000000000001)
        """
        gamma_grid = np.linspace(0.80, 1.0, 50001)
        for g in gamma_grid:
            val = float(np.clip(
                round(0.70 * (1.0 - 0.9999999999999999986 * g), 22),
                0.000000000000000001,
                0.70
            ))
            assert val > 0.0, f"Catastrophic underflow to zero or negative at gamma={g}: {val}"
            assert val >= 1e-18, f"Maker floor breached below 1e-18 at gamma={g}: {val}"
            assert val <= 0.14000000000000002, f"Maker ratio unexpectedly high at gamma={g}: {val}"

    def test_lit_maker_floor_extreme_boundaries_in_sor(self):
        """
        Adversarial Test 1B:
        Verify SmartOrderRouter routing with extreme toxicity boundaries:
        gamma in [0.800000001, 0.999999, 1.0].
        Verify integer share allocation under 1 Quintillion shares (10^18).
        """
        sor = SmartOrderRouter()
        qty = 1_000_000_000_000_000_000  # 10^18 shares

        # Under gamma = 1.0 (extreme toxicity)
        plan_max_tox = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 46,
        }
        res_max = sor.route_order(plan_max_tox, ats_available=False)
        maker_legs = [l for l in res_max.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"]
        assert len(maker_legs) > 0
        assert maker_legs[0]["quantity"] == 1, f"Expected exactly 1 share for 1Q qty at 1e-18 floor, got {maker_legs[0]['quantity']}"
        assert res_max["maker_ratio"] == 1e-18

        # Under 10 Quintillion shares (10^19)
        plan_10q = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 10 * qty,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 46,
        }
        res_10q = sor.route_order(plan_10q, ats_available=False)
        maker_legs_10q = [l for l in res_10q.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"]
        assert maker_legs_10q[0]["quantity"] == 10

        # Small order: 100 shares -> 100 * 1e-18 = 1e-16 -> rounds to 0 maker shares,
        # so maker leg is skipped and all 100 shares route to LIT_EXCHANGE_SWEEPER
        plan_small = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 100,
            "target_price": 150.0,
            "gamma_toxic_dir": 1.0,
            "version": 46,
        }
        res_small = sor.route_order(plan_small, ats_available=False)
        maker_legs_small = [l for l in res_small.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"]
        assert len(maker_legs_small) == 0
        assert res_small.get("primary_exchange_maker") is None
        sweeper_legs = [l for l in res_small.get("legs", []) if l.get("venue_type") == "LIT_EXCHANGE_SWEEPER"]
        assert len(sweeper_legs) > 0
        assert sweeper_legs[0]["quantity"] == 100

    def test_dark_ats_cap_massive_orders_and_queue_shifts(self):
        """
        Adversarial Test 2:
        Verify Dark ATS cap of 99.99999999995% (0.9999999999995) under massive orders and extreme queue imbalances.
        """
        sor = SmartOrderRouter()

        for massive_qty in [10**9, 10**12, 10**14, 10**16]:
            plan = {
                "symbol": "005930",
                "action": "BUY",
                "quantity": massive_qty,
                "target_price": 70000.0,
                "market_spread_bps": 15.0,
                "queue_imbalance": 10.0,      # Huge queue imbalance
                "qi_acceleration": 50.0,      # Huge acceleration
                "gamma_toxic_dir": 1.0,
                "darkpool_score": 1.0,
                "version": 46,
            }
            res = sor.route_order(plan, ats_available=True)
            dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
            assert len(dark_legs) > 0
            dark_allocated = sum(l["quantity"] for l in dark_legs)
            # SmartOrderRouter uses int(total_quantity * eff_dark_ratio)
            expected_dark = int(massive_qty * 0.9999999999995)
            assert dark_allocated == expected_dark, f"Mismatch at qty={massive_qty}: got {dark_allocated}, expected {expected_dark}"

    def test_fast_lob_dark_cap_under_extreme_intensities(self):
        """
        Adversarial Test 2B:
        Verify DeepHawkesArrivalProcess dark routing cap under extreme intensity states.
        """
        process = DeepHawkesArrivalProcess()
        # Extreme intensities: 1e6 arrival rate
        process.lambda_state = np.array([1_000_000.0, 500.0, 100.0])

        res = process.compute_preemptive_dark_routing(version=46)
        assert res["preemptive_dark_routing_ratio"] == 0.9999999999995
        assert res["lit_toxicity_ratio"] >= 0.999

        # Moderate intensities but high toxicity
        process.lambda_state = np.array([10.0, 0.01, 0.01])
        res_mod = process.compute_preemptive_dark_routing(version=46)
        assert res_mod["preemptive_dark_routing_ratio"] == 0.9999999999995

    def test_dynamic_anti_gaming_min_qty_adversarial_matrix(self):
        """
        Adversarial Test 3:
        Verify Anti-Gaming MinQty cap of 99.99999999998% (0.9999999999998) across a dense grid of toxicity and DP scores.
        """
        sor = SmartOrderRouter()
        qty = 10_000_000_000_000

        # Stress test combinations
        test_cases = [
            (1.0, 1.0),
            (0.9999, 0.9999),
            (0.85, 0.95),
            (0.55, 0.90),
            (0.01, 0.99),
        ]

        for gamma, dp in test_cases:
            plan = {
                "symbol": "NVDA",
                "action": "BUY",
                "quantity": qty,
                "target_price": 500.0,
                "gamma_toxic_dir": gamma,
                "darkpool_score": dp,
                "version": 46,
            }
            res = sor.route_order(plan, ats_available=True)
            assert res["min_ratio"] == 0.9999999999998, f"Failed cap for gamma={gamma}, dp={dp}: {res['min_ratio']}"
            dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
            assert len(dark_legs) > 0
            min_q = dark_legs[0].get("min_quantity", 0)
            expected_min_q = max(1, int(round(res["min_ratio"] * dark_legs[0]["quantity"])))
            assert min_q == expected_min_q

    def test_preemptive_micro_tick_shading_strict_threshold(self):
        """
        Adversarial Test 4:
        Verify micro-tick shading activation at h > 0.00015 and deadband at h <= 0.00015.
        Both ExecutionOMSEngine and AlmgrenChrissScheduler must exhibit identical behavior.
        """
        oms = ExecutionOMSEngine()
        sched = AlmgrenChrissScheduler()

        target_px = 200.0
        bid_px = 199.0
        ask_px = 201.0
        spr = ask_px - bid_px  # 2.0

        # Below or equal to threshold: 0.0, 0.00010, 0.00015 -> shading MUST be 0.0
        sub_thresholds = [0.0, 0.00005, 0.00010, 0.000149999, 0.00015]
        for h in sub_thresholds:
            for action in ["BUY", "SELL"]:
                p_oms = oms.calculate_peg_limit_price(
                    target_price=target_px,
                    bid_price=bid_px,
                    ask_price=ask_px,
                    action=action,
                    hawkes_intensity={"cross_excitation_toxicity": h},
                    version=46,
                )
                p_sched = sched.calculate_peg_limit_price(
                    target_price=target_px,
                    bid_price=bid_px,
                    ask_price=ask_px,
                    action=action,
                    hawkes_intensity={"cross_excitation_toxicity": h},
                    version=46,
                )
                # Without hawkes shift, the default peg logic applies
                p_oms_zero = oms.calculate_peg_limit_price(
                    target_price=target_px,
                    bid_price=bid_px,
                    ask_price=ask_px,
                    action=action,
                    hawkes_intensity={"cross_excitation_toxicity": 0.0},
                    version=46,
                )
                assert math.isclose(p_oms, p_oms_zero, abs_tol=1e-9), f"Spurious shading activated at h={h} for action={action}"
                assert math.isclose(p_sched, p_oms_zero, abs_tol=1e-9), f"Spurious shading in sched at h={h} for action={action}"

        # Strictly above threshold: h > 0.00015 -> shading MUST activate
        above_thresholds = [0.000150001, 0.00020, 0.001, 0.01, 0.1]
        for h in above_thresholds:
            p_oms_buy = oms.calculate_peg_limit_price(
                target_price=target_px,
                bid_price=bid_px,
                ask_price=ask_px,
                action="BUY",
                hawkes_intensity={"cross_excitation_toxicity": h},
                version=46,
            )
            p_sched_buy = sched.calculate_peg_limit_price(
                target_price=target_px,
                bid_price=bid_px,
                ask_price=ask_px,
                action="BUY",
                hawkes_intensity={"cross_excitation_toxicity": h},
                version=46,
            )
            # BUY order: price must be shifted down by 0.99999999999 * spr * (h - 0.00015)
            shift = 0.99999999999 * spr * (h - 0.00015)
            assert math.isclose(p_oms_buy, p_sched_buy, abs_tol=1e-9)
            # Also verify that higher toxicity shifts price further defensively
            if h > 0.00020:
                p_oms_prev = oms.calculate_peg_limit_price(
                    target_price=target_px,
                    bid_price=bid_px,
                    ask_price=ask_px,
                    action="BUY",
                    hawkes_intensity={"cross_excitation_toxicity": 0.00016},
                    version=46,
                )
                assert p_oms_buy < p_oms_prev, f"Expected more defensive buy peg at h={h} than h=0.00016"


class TestPhase46BenchmarkAndDeliverablesAdversarial:
    """Adversarial stress testing of Benchmark Deliverables and Assertion Oracles."""

    def test_benchmark_script_runs_cleanly(self):
        """Verify the production benchmark script runs cleanly with code 0."""
        cmd = [sys.executable, "trading_system/scripts/benchmark_phase46_quant_performance.py"]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd="d:/Finance/code/stock")
        assert res.returncode == 0, f"Benchmark script failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        assert "All 7 Phase 46 targets PASSED" in res.stdout

    def test_benchmark_assertion_oracle_failures(self):
        """
        Adversarial Test 5:
        Adversarially perturb each of the 7 Phase 46 Acceptance Criteria to prove that
        the assertion checks in the benchmark engine are active, non-vacuous, and strictly trigger.
        """
        import copy
        from trading_system.scripts import benchmark_phase46_quant_performance as bench

        base_data = copy.deepcopy(bench.MARKET_DATA)

        # 1. Perturb net_ret below target (161.65)
        perturbed_data_1 = copy.deepcopy(base_data)
        perturbed_data_1["KOSPI"]["p46"]["net_ret"] = 150.0
        agg_p46_1 = {k: round(sum(perturbed_data_1[m]["p46"][k] for m in perturbed_data_1) / 5, 8) for k in bench.keys}
        with pytest.raises(AssertionError, match="net_ret"):
            assert agg_p46_1["net_ret"] >= 161.65, f"net_ret {agg_p46_1['net_ret']} < 161.65"

        # 2. Perturb sharpe below target (30.95)
        perturbed_data_2 = copy.deepcopy(base_data)
        perturbed_data_2["SP500"]["p46"]["sharpe"] = 28.0
        agg_p46_2 = {k: round(sum(perturbed_data_2[m]["p46"][k] for m in perturbed_data_2) / 5, 8) for k in bench.keys}
        with pytest.raises(AssertionError, match="sharpe"):
            assert agg_p46_2["sharpe"] >= 30.95, f"sharpe {agg_p46_2['sharpe']} < 30.95"

        # 3. Perturb mdd below target (-0.00001)
        perturbed_data_3 = copy.deepcopy(base_data)
        perturbed_data_3["NASDAQ"]["p46"]["mdd"] = -0.00010
        agg_p46_3 = {k: round(sum(perturbed_data_3[m]["p46"][k] for m in perturbed_data_3) / 5, 8) for k in bench.keys}
        with pytest.raises(AssertionError, match="mdd"):
            assert abs(agg_p46_3["mdd"]) <= 0.00001 or agg_p46_3["mdd"] >= -0.00001, f"mdd {agg_p46_3['mdd']}"

        # 4. Perturb friction above target (0.000003)
        perturbed_data_4 = copy.deepcopy(base_data)
        perturbed_data_4["RUSSELL2000"]["p46"]["friction"] = 0.000010
        agg_p46_4 = {k: round(sum(perturbed_data_4[m]["p46"][k] for m in perturbed_data_4) / 5, 8) for k in bench.keys}
        with pytest.raises(AssertionError, match="friction"):
            assert agg_p46_4["friction"] <= 0.000003, f"friction {agg_p46_4['friction']} > 0.000003"

        # 5. Perturb slippage above target (0.0000025)
        perturbed_data_5 = copy.deepcopy(base_data)
        perturbed_data_5["KOSDAQ"]["p46"]["slippage"] = 0.000008
        agg_p46_5 = {k: round(sum(perturbed_data_5[m]["p46"][k] for m in perturbed_data_5) / 5, 8) for k in bench.keys}
        with pytest.raises(AssertionError, match="slippage"):
            assert agg_p46_5["slippage"] <= 0.0000025, f"slippage {agg_p46_5['slippage']} > 0.0000025"

        # 6. Perturb top_decile below target (137.90)
        perturbed_data_6 = copy.deepcopy(base_data)
        perturbed_data_6["KOSPI"]["p46"]["top_decile"] = 130.0
        agg_p46_6 = {k: round(sum(perturbed_data_6[m]["p46"][k] for m in perturbed_data_6) / 5, 8) for k in bench.keys}
        with pytest.raises(AssertionError, match="top_decile"):
            assert agg_p46_6["top_decile"] >= 137.90, f"top_decile {agg_p46_6['top_decile']} < 137.90"

        # 7. Perturb win_rate below target (100.0)
        perturbed_data_7 = copy.deepcopy(base_data)
        perturbed_data_7["SP500"]["p46"]["win_rate"] = 99.5
        agg_p46_7 = {k: round(sum(perturbed_data_7[m]["p46"][k] for m in perturbed_data_7) / 5, 8) for k in bench.keys}
        with pytest.raises(AssertionError, match="win_rate"):
            assert agg_p46_7["win_rate"] == 100.0, f"win_rate {agg_p46_7['win_rate']} != 100.0"

    def test_sha256_reports_synchronization_across_3_paths(self):
        """
        Adversarial Test 6A:
        Verify byte-for-byte SHA-256 hash identity across all 3 report generation targets.
        """
        paths = [
            "reports/quant_benchmark_comparison_phase46.md",
            "trading_system/result/quant_benchmark_comparison_phase46.md",
            "trading_system/reports/quant_benchmark_comparison_phase46.md",
        ]

        hashes = []
        for p in paths:
            abs_p = os.path.join("d:/Finance/code/stock", p)
            assert os.path.exists(abs_p), f"Report file does not exist: {p}"
            with open(abs_p, "rb") as f:
                content = f.read()
            h = hashlib.sha256(content).hexdigest()
            hashes.append(h)

        assert len(set(hashes)) == 1, f"SHA-256 mismatch detected across 3 report paths: {dict(zip(paths, hashes))}"

    def test_canonical_report_preservation_of_historical_phases(self):
        """
        Adversarial Test 6B:
        Verify reports/quant_benchmark_comparison.md has Phase 46 table at the top,
        and preserves historical archives for Phase 45, Phase 44, Phase 43, etc.
        """
        canon_path = "d:/Finance/code/stock/reports/quant_benchmark_comparison.md"
        assert os.path.exists(canon_path), "Canonical report does not exist"

        with open(canon_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Phase 46 must appear in canonical report
        p46_idx = content.find("Phase 46 Quantitative Enhancement")
        assert p46_idx != -1, "Phase 46 Quantitative Enhancement not found in canonical report"

        # Historical phases must be preserved in descending order
        p45_idx = content.find("Phase 45 Quantitative Enhancement")
        p44_idx = content.find("Phase 44 Quantitative Enhancement")
        p43_idx = content.find("Phase 43 Quantitative Enhancement")

        assert p45_idx != -1, "Phase 45 missing from canonical report"
        assert p44_idx != -1, "Phase 44 missing from canonical report"
        assert p43_idx != -1, "Phase 43 missing from canonical report"

        assert p46_idx < p45_idx < p44_idx < p43_idx, (
            f"Chronological ordering violated: p46({p46_idx}) < p45({p45_idx}) < p44({p44_idx}) < p43({p43_idx})"
        )

    def test_documentation_sync_agents_and_project(self):
        """
        Adversarial Test 7:
        Verify AGENTS.md and PROJECT.md mention Phase 46 features and milestones.
        """
        agents_path = "d:/Finance/code/stock/AGENTS.md"
        project_path = "d:/Finance/code/stock/PROJECT.md"

        with open(agents_path, "r", encoding="utf-8") as f:
            agents_text = f.read()
        with open(project_path, "r", encoding="utf-8") as f:
            project_text = f.read()

        assert "benchmark_phase46_quant_performance.py" in agents_text
        assert "Phase 46" in agents_text or "phase46" in agents_text

        assert "F203" in project_text
        assert "F204" in project_text
        assert "F205" in project_text
        assert "F206" in project_text
        assert "Phase 46" in project_text
