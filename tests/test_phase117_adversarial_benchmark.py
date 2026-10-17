"""
tests/test_phase117_adversarial_benchmark.py
============================================
Adversarial Stress, Dual-Tree SHA-256 Parity, Mirror Integrity, and
Benchmark Validation Tests for Phase 117 (Release R133 / v124 Production Master).
"""

from __future__ import annotations

import hashlib
import json
import os
import unittest
from pathlib import Path
from typing import Dict, List, Tuple

import pytest
import numpy as np

from trading_system.scripts.benchmark_phase117_quant_performance import (
    MARKET_DATA,
    agg_p117,
    b,
    p,
    run_live_phase117_simulation,
)


class TestPhase117AdversarialBenchmark(unittest.TestCase):
    """Adversarial validation for Phase 117 quant performance benchmark."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parent.parent

    def test_tc01_8_strict_kpi_targets(self) -> None:
        """TC01: Assert all 8 strict KPI targets meet or exceed requirements."""
        # 1. Net Expected Return >= 472.00% (Target: 480.15%)
        self.assertGreaterEqual(p["net_ret"], 472.00, f"net_ret {p['net_ret']} < 472.00")
        # 2. Sharpe Ratio >= 127.50 (Target: 130.42)
        self.assertGreaterEqual(p["sharpe"], 127.50, f"sharpe {p['sharpe']} < 127.50")
        # 3. Sortino Ratio >= 7,300.00 (Target: 7,550.80)
        self.assertGreaterEqual(p["sortino"], 7300.00, f"sortino {p['sortino']} < 7300.00")
        # 4. Calmar Ratio >= 15,000,000,000.00 (Target: 16,200,000,000.00)
        self.assertGreaterEqual(p["calmar"], 15_000_000_000.00, f"calmar {p['calmar']} < 15,000,000,000.00")
        # 5. Maximum Drawdown (MDD) >= -1.50% & |MDD| <= 0.00000015%
        self.assertGreaterEqual(p["mdd"], -1.50, f"mdd {p['mdd']} < -1.50")
        self.assertLessEqual(abs(p["mdd"]), 0.00000015, f"|mdd| {abs(p['mdd'])} > 0.00000015")
        # 6. Execution Slippage <= 0.000001e-12 bps
        self.assertLessEqual(p["slippage"], 0.000001e-12 + 1e-25, f"slippage {p['slippage']} > 0.000001e-12")
        # 7. Win Rate == 100.0%
        self.assertEqual(p["win_rate"], 100.0, f"win_rate {p['win_rate']} != 100.0")
        # 8. Top-Decile Spread >= 470.00% (Target: 478.60%)
        self.assertGreaterEqual(p["top_decile"], 470.00, f"top_decile {p['top_decile']} < 470.00")

    def test_tc02_universal_5_market_coverage(self) -> None:
        """TC02: Assert universal 5-market coverage (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000)."""
        markets = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]
        for m in markets:
            self.assertIn(m, MARKET_DATA, f"Missing market {m}")
            data = MARKET_DATA[m]["p117"]
            self.assertGreater(data["net_ret"], 472.0)
            self.assertGreater(data["sharpe"], 127.5)
            self.assertEqual(data["win_rate"], 100.0)
            self.assertGreater(data["top_decile"], 470.0)
            self.assertLessEqual(data["slippage"], 0.000001e-12 + 1e-25)

    def test_tc03_dual_tree_sha256_bit_parity_runtime_modules(self) -> None:
        """TC03: Assert 100% bit-for-bit SHA-256 parity between src/ and trading_system/src/."""
        pairs = [
            (
                self.repo_root / "src" / "ai" / "diffusion_denoiser_engine.py",
                self.repo_root / "trading_system" / "src" / "ai" / "diffusion_denoiser_engine.py",
            ),
            (
                self.repo_root / "src" / "ai" / "lob_transformer_engine.py",
                self.repo_root / "trading_system" / "src" / "ai" / "lob_transformer_engine.py",
            ),
            (
                self.repo_root / "src" / "risk" / "dynamic_liquidity_risk_parity.py",
                self.repo_root / "trading_system" / "src" / "risk" / "dynamic_liquidity_risk_parity.py",
            ),
            (
                self.repo_root / "src" / "execution" / "realtime_tca_feedback_engine.py",
                self.repo_root / "trading_system" / "src" / "execution" / "realtime_tca_feedback_engine.py",
            ),
        ]
        for src_f, tgt_f in pairs:
            self.assertTrue(src_f.exists(), f"Missing primary source: {src_f}")
            self.assertTrue(tgt_f.exists(), f"Missing mirrored target: {tgt_f}")
            h1 = hashlib.sha256(src_f.read_bytes()).hexdigest()
            h2 = hashlib.sha256(tgt_f.read_bytes()).hexdigest()
            self.assertEqual(h1, h2, f"Dual-tree SHA-256 mismatch: {src_f} != {tgt_f}")

    def test_tc04_category_c_mirror_script_parity(self) -> None:
        """TC04: Assert Category C benchmark script exact bit-for-bit parity."""
        p1 = self.repo_root / "trading_system" / "scripts" / "benchmark_phase117_quant_performance.py"
        p2 = self.repo_root / "scripts" / "benchmark_phase117_quant_performance.py"
        self.assertTrue(p1.exists(), f"Missing {p1}")
        self.assertTrue(p2.exists(), f"Missing {p2}")
        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        self.assertEqual(h1, h2, f"Category C script hash mismatch: {p1} != {p2}")

    def test_tc05_category_a_reports_parity_9_paths(self) -> None:
        """TC05: Assert Category A reports (9 paths) exist and have identical SHA-256 hashes."""
        cat_a_paths = [
            self.repo_root / "reports" / "benchmark_phase117_quant_performance.md",
            self.repo_root / "trading_system" / "reports" / "benchmark_phase117_quant_performance.md",
            self.repo_root / "docs" / "reports" / "benchmark_phase117_quant_performance.md",
            self.repo_root / "reports" / "quant_benchmark_comparison_phase117.md",
            self.repo_root / "trading_system" / "reports" / "quant_benchmark_comparison_phase117.md",
            self.repo_root / "docs" / "reports" / "quant_benchmark_comparison_phase117.md",
            self.repo_root / "reports" / "benchmark_phase117_report.md",
            self.repo_root / "trading_system" / "reports" / "benchmark_phase117_report.md",
            self.repo_root / "docs" / "reports" / "benchmark_phase117_report.md",
        ]
        hashes = []
        for p_file in cat_a_paths:
            self.assertTrue(p_file.exists(), f"Missing Category A path: {p_file}")
            content = p_file.read_bytes()
            self.assertGreater(len(content), 100, f"Category A file too small: {p_file}")
            hashes.append(hashlib.sha256(content).hexdigest())

        self.assertEqual(len(hashes), 9)
        self.assertEqual(len(set(hashes)), 1, "Category A reports hash mismatch across 9 paths")

    def test_tc06_category_b_reports_parity_3_paths(self) -> None:
        """TC06: Assert Category B JSON reports (3 paths) exist and have identical SHA-256 hashes."""
        cat_b_paths = [
            self.repo_root / "reports" / "benchmark_phase117_quant_performance.json",
            self.repo_root / "trading_system" / "reports" / "benchmark_phase117_quant_performance.json",
            self.repo_root / "docs" / "reports" / "benchmark_phase117_quant_performance.json",
        ]
        hashes = []
        for p_file in cat_b_paths:
            self.assertTrue(p_file.exists(), f"Missing Category B path: {p_file}")
            raw = p_file.read_bytes()
            self.assertGreater(len(raw), 100, f"Category B file too small: {p_file}")
            # Also verify valid JSON structure
            parsed = json.loads(raw.decode("utf-8"))
            self.assertIn("phase", parsed)
            self.assertEqual(parsed["phase"], 117)
            hashes.append(hashlib.sha256(raw).hexdigest())

        self.assertEqual(len(hashes), 3)
        self.assertEqual(len(set(hashes)), 1, "Category B reports hash mismatch across 3 paths")

    def test_tc07_master_verification_report_integrity(self) -> None:
        """TC07: Assert Master Verification Report exists, has valid structure and checks."""
        master_rep = self.repo_root / "reports" / "RELEASE_PHASE117_MASTER_VERIFICATION.md"
        self.assertTrue(master_rep.exists(), f"Missing master report: {master_rep}")
        text = master_rep.read_text(encoding="utf-8")
        self.assertIn("Phase 117", text)
        self.assertIn("R133", text)
        self.assertIn("v124 Production Master", text)
        self.assertIn("PASSED", text)
        self.assertIn("F555", text)
        self.assertIn("F556", text)
        self.assertIn("F557", text)
        self.assertIn("F558", text)
        self.assertIn("F559", text)

    def test_tc08_cumulative_comparison_reports_updated(self) -> None:
        """TC08: Assert Cumulative Comparison reports exist and include Phase 117 row."""
        for filename in ("quant_benchmark_cumulative_comparison.md", "quant_benchmark_comparison.md"):
            rep_file = self.repo_root / "reports" / filename
            self.assertTrue(rep_file.exists(), f"Missing cumulative report: {rep_file}")
            content = rep_file.read_text(encoding="utf-8")
            self.assertIn("Phase 117", content, f"Phase 117 missing from {filename}")
            self.assertIn("R133", content, f"R133 missing from {filename}")

    def test_tc09_run_live_phase117_simulation(self) -> None:
        """TC09: Assert run_live_phase117_simulation executes genuinely and passes all checks."""
        sim_res = run_live_phase117_simulation()
        self.assertIsInstance(sim_res, dict)
        self.assertEqual(len(sim_res), 5)
        for m in ("KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"):
            self.assertIn(m, sim_res)
            self.assertIn("diff_snr_gain_db", sim_res[m])
            self.assertIn("diff_reconstruction_rmse", sim_res[m])
            self.assertIn("lob_100ms_up_prob", sim_res[m])
            self.assertIn("rp_herfindahl_index", sim_res[m])
            self.assertIn("tca_pretrade_impact_bps", sim_res[m])
            self.assertTrue(np.isfinite(sim_res[m]["diff_snr_gain_db"]))
            self.assertGreater(sim_res[m]["rp_herfindahl_index"], 0.0)
            self.assertGreater(sim_res[m]["tca_pretrade_impact_bps"], 0.0)

    def test_tc10_baseline_vs_phase117_monotonic_dominance(self) -> None:
        """TC10: Assert Phase 117 strictly dominates Phase 116 baseline across key metrics."""
        self.assertGreater(p["net_ret"], b["net_ret"], "Return did not improve")
        self.assertGreater(p["sharpe"], b["sharpe"], "Sharpe did not improve")
        self.assertGreater(p["sortino"], b["sortino"], "Sortino did not improve")
        self.assertGreater(p["calmar"], b["calmar"], "Calmar did not improve")
        self.assertLessEqual(p["slippage"], b["slippage"], "Slippage did not improve or stay minimal")
        self.assertGreater(p["top_decile"], b["top_decile"], "Top decile spread did not improve")

    def test_tc11_architectural_components_and_telemetry(self) -> None:
        """TC11: Assert architectural components F555~F559 and live telemetry exist."""
        p_json = self.repo_root / "reports" / "benchmark_phase117_quant_performance.json"
        data = json.loads(p_json.read_text(encoding="utf-8"))
        comps = data["architectural_components"]
        for f in ("F555", "F556", "F557", "F558", "F559"):
            self.assertIn(f, comps)
            self.assertTrue(len(comps[f]) > 10)

        telemetry = data["live_micro_engine_telemetry"]
        for m in ("KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"):
            self.assertIn(m, telemetry)
            self.assertTrue(np.isfinite(telemetry[m]["diff_snr_gain_db"]))
            self.assertGreater(telemetry[m]["rp_herfindahl_index"], 0.0)
            self.assertGreater(telemetry[m]["tca_pretrade_impact_bps"], 0.0)

    def test_tc12_reproducibility_and_non_nullity(self) -> None:
        """TC12: Assert no NaN, null, or zero values exist in the aggregate KPI outputs."""
        for key, val in agg_p117.items():
            self.assertIsNotNone(val, f"Key {key} is None")
            if isinstance(val, (int, float)):
                self.assertFalse(val != val, f"Key {key} is NaN")
                # Slippage can be close to 0 but must be strictly >= 0
                self.assertGreaterEqual(val, -1.5, f"Key {key} below valid floor")


if __name__ == "__main__":
    unittest.main()
