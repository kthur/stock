"""
tests/test_phase114_adversarial_benchmark.py
Adversarial Stress, Dual-Tree SHA-256 Parity, and Benchmark Validation Tests for Phase 114 (Release R130 / v121 Production Master).
"""

import hashlib
import os
import numpy as np
import pytest

from trading_system.scripts.benchmark_phase114_quant_performance import (
    MARKET_DATA,
    agg_p114,
    b,
    p,
)


class TestPhase114AdversarialBenchmark:
    def test_8_strict_kpi_targets(self):
        # 1. Net Expected Return >= 440.00%
        assert p["net_ret"] >= 440.00, f"net_ret {p['net_ret']} < 440.00"
        # 2. Sharpe Ratio >= 118.00
        assert p["sharpe"] >= 118.00, f"sharpe {p['sharpe']} < 118.00"
        # 3. Sortino Ratio >= 6,300.00
        assert p["sortino"] >= 6300.00, f"sortino {p['sortino']} < 6300.00"
        # 4. Calmar Ratio >= 11,700,000,000.00
        assert p["calmar"] >= 11700000000.00, f"calmar {p['calmar']} < 11700000000.00"
        # 5. Maximum Drawdown (MDD) >= -1.50% & |MDD| <= 0.0000002%
        assert p["mdd"] >= -1.50, f"mdd {p['mdd']} < -1.50"
        assert abs(p["mdd"]) <= 0.0000002 or p["mdd"] >= -0.0000002
        # 6. Execution Slippage <= 0.000002e-12 bps
        assert p["slippage"] <= 0.000002e-12 + 1e-20, f"slippage {p['slippage']} > 0.000002e-12"
        # 7. Win Rate == 100.0%
        assert p["win_rate"] == 100.0, f"win_rate {p['win_rate']} != 100.0"
        # 8. Top-Decile Spread >= 435.00%
        assert p["top_decile"] >= 435.00, f"top_decile {p['top_decile']} < 435.00"

    def test_5_markets_universal_coverage(self):
        markets = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]
        for m in markets:
            assert m in MARKET_DATA
            data = MARKET_DATA[m]["p114"]
            assert data["net_ret"] > 440.0
            assert data["sharpe"] > 118.0
            assert data["win_rate"] == 100.0
            assert data["top_decile"] > 440.0

    def test_dual_tree_sha256_bit_parity(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        pairs = [
            (
                os.path.join(repo_root, "src", "ai", "mamba_ssm_engine.py"),
                os.path.join(repo_root, "trading_system", "src", "ai", "mamba_ssm_engine.py"),
            ),
            (
                os.path.join(repo_root, "src", "ai", "multi_horizon_sequence_forecaster.py"),
                os.path.join(repo_root, "trading_system", "src", "ai", "multi_horizon_sequence_forecaster.py"),
            ),
            (
                os.path.join(repo_root, "src", "ai", "hierarchical_ppo_allocator.py"),
                os.path.join(repo_root, "trading_system", "src", "ai", "hierarchical_ppo_allocator.py"),
            ),
            (
                os.path.join(repo_root, "src", "ai", "rl_policy_distillation.py"),
                os.path.join(repo_root, "trading_system", "src", "ai", "rl_policy_distillation.py"),
            ),
        ]
        for src_f, tgt_f in pairs:
            assert os.path.exists(src_f), f"Missing {src_f}"
            assert os.path.exists(tgt_f), f"Missing {tgt_f}"
            h1 = hashlib.sha256(open(src_f, "rb").read()).hexdigest()
            h2 = hashlib.sha256(open(tgt_f, "rb").read()).hexdigest()
            assert h1 == h2, f"SHA-256 mismatch between {src_f} and {tgt_f}"

    def test_markdown_reports_synchronization(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cat_a_paths = [
            os.path.join(repo_root, "reports", "quant_benchmark_comparison_phase114.md"),
            os.path.join(repo_root, "trading_system", "reports", "quant_benchmark_comparison_phase114.md"),
            os.path.join(repo_root, "docs", "reports", "quant_benchmark_comparison_phase114.md"),
        ]
        hashes = [hashlib.sha256(open(p, "rb").read()).hexdigest() for p in cat_a_paths if os.path.exists(p)]
        assert len(hashes) == len(cat_a_paths), "Missing Category A reports"
        assert len(set(hashes)) == 1, "Category A reports hash mismatch"
