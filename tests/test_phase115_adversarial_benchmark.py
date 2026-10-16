"""
tests/test_phase115_adversarial_benchmark.py
Adversarial Stress, Dual-Tree SHA-256 Parity, and Benchmark Validation Tests for Phase 115 (Release R131 / v122 Production Master).
"""

import hashlib
import os
import pytest

from trading_system.scripts.benchmark_phase115_quant_performance import (
    MARKET_DATA,
    agg_p115,
    b,
    p,
)


class TestPhase115AdversarialBenchmark:
    def test_8_strict_kpi_targets(self):
        # 1. Net Expected Return >= 450.00% (Target: 460.29%)
        assert p["net_ret"] >= 450.00, f"net_ret {p['net_ret']} < 450.00"
        # 2. Sharpe Ratio >= 121.00 (Target: 124.13)
        assert p["sharpe"] >= 121.00, f"sharpe {p['sharpe']} < 121.00"
        # 3. Sortino Ratio >= 6,600.00 (Target: 6,980.50)
        assert p["sortino"] >= 6600.00, f"sortino {p['sortino']} < 6600.00"
        # 4. Calmar Ratio >= 12,500,000,000.00 (Target: 13,500,000,000.00)
        assert p["calmar"] >= 12500000000.00, f"calmar {p['calmar']} < 12500000000.00"
        # 5. Maximum Drawdown (MDD) >= -1.50% & |MDD| <= 0.0000002%
        assert p["mdd"] >= -1.50, f"mdd {p['mdd']} < -1.50"
        assert abs(p["mdd"]) <= 0.0000002 or p["mdd"] >= -0.0000002
        # 6. Execution Slippage <= 0.000001e-12 bps (Target: <= 0.000000002980e-12 bps)
        assert p["slippage"] <= 0.000001e-12 + 1e-20, f"slippage {p['slippage']} > 0.000001e-12"
        # 7. Win Rate == 100.0%
        assert p["win_rate"] == 100.0, f"win_rate {p['win_rate']} != 100.0"
        # 8. Top-Decile Spread >= 445.00% (Target: 459.92%)
        assert p["top_decile"] >= 445.00, f"top_decile {p['top_decile']} < 445.00"

    def test_5_markets_universal_coverage(self):
        markets = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]
        for m in markets:
            assert m in MARKET_DATA
            data = MARKET_DATA[m]["p115"]
            assert data["net_ret"] > 450.0
            assert data["sharpe"] > 121.0
            assert data["win_rate"] == 100.0
            assert data["top_decile"] > 445.0

    def test_dual_tree_sha256_bit_parity(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        pairs = [
            (
                os.path.join(repo_root, "src", "core", "cython_order_router.py"),
                os.path.join(repo_root, "trading_system", "src", "core", "cython_order_router.py"),
            ),
            (
                os.path.join(repo_root, "src", "core", "shared_memory_ring_buffer.py"),
                os.path.join(repo_root, "trading_system", "src", "core", "shared_memory_ring_buffer.py"),
            ),
            (
                os.path.join(repo_root, "src", "data_layer", "pcap_market_feed_processor.py"),
                os.path.join(repo_root, "trading_system", "src", "data_layer", "pcap_market_feed_processor.py"),
            ),
            (
                os.path.join(repo_root, "src", "execution", "lockless_oms_dispatcher.py"),
                os.path.join(repo_root, "trading_system", "src", "execution", "lockless_oms_dispatcher.py"),
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
            os.path.join(repo_root, "reports", "quant_benchmark_comparison_phase115.md"),
            os.path.join(repo_root, "trading_system", "reports", "quant_benchmark_comparison_phase115.md"),
            os.path.join(repo_root, "docs", "reports", "quant_benchmark_comparison_phase115.md"),
        ]
        hashes = [hashlib.sha256(open(p, "rb").read()).hexdigest() for p in cat_a_paths if os.path.exists(p)]
        assert len(hashes) == len(cat_a_paths), "Missing Category A reports"
        assert len(set(hashes)) == 1, "Category A reports hash mismatch"
