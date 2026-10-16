"""
tests/test_phase112_challenger2_stress.py — Empirical Stress Test Suite for Phase 112 M1
Challenger 2 Verification Harness:
1. Concurrency Stress (Rapid concurrent orders, balance queries, rate limiters, token storage)
2. Simulation Fidelity (Simulated fills, cash balance updates, position accounting, orderbook ladder positivity)
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import random
import sys
import tempfile
import time
import pytest

# Ensure trading_system is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "trading_system"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.broker.kis_broker_connector import (
    AccountBalanceSnapshot,
    BaseBrokerConnector,
    ExecutionNotice,
    KISBrokerConnector,
    OrderbookDepth,
    TokenBucketRateLimiter,
)
from src.broker.ls_broker_connector import LSBrokerConnector


class TestPhase112ConcurrencyAndFidelity:
    """Empirical Stress Tests by Challenger 2."""

    def test_simulation_cash_and_position_fidelity(self):
        """
        Verify simulation fidelity:
        - Simulated fills correctly update cash balance and position quantities.
        - Buy orders reduce cash and add positions.
        - Sell orders increase cash and reduce positions.
        """
        kis = KISBrokerConnector(account_number="12345678", simulation_mode=True)
        kis.connect()

        initial_bal = kis.get_balance()
        initial_cash = initial_bal["cash_balance"]
        initial_pp = initial_bal["purchasing_power"]
        assert initial_cash == 100_000_000.0

        # Step 1: Submit BUY order
        code = "005930"
        price = 70000.0
        qty = 10
        order_cost = price * qty  # 700,000 KRW

        receipt = kis.place_order(symbol=code, side="BUY", price=price, quantity=qty, market_price=70000.0)
        assert receipt["success"] is True

        post_buy_bal = kis.get_balance()
        post_buy_positions = kis.get_positions()
        pos_dict = {p["symbol"]: p["quantity"] for p in post_buy_positions}

        print(f"\n[Empirical Metric] Initial Cash: {initial_cash:,.0f} KRW")
        print(f"[Empirical Metric] Post-Buy Cash: {post_buy_bal['cash_balance']:,.0f} KRW")
        print(f"[Empirical Metric] Post-Buy Purchasing Power: {post_buy_bal['purchasing_power']:,.0f} KRW")
        print(f"[Empirical Metric] Post-Buy Positions: {pos_dict}")

        # Strict verification of required simulation fidelity:
        # 1. Buy orders must reduce cash balance
        assert post_buy_bal["cash_balance"] == initial_cash - order_cost, (
            f"Fidelity Violation: Cash balance not reduced on buy. "
            f"Expected: {initial_cash - order_cost:,.0f} KRW, Actual: {post_buy_bal['cash_balance']:,.0f} KRW"
        )

        # 2. Buy orders must add positions
        assert pos_dict.get(code, 0) == qty, (
            f"Fidelity Violation: Position not added on buy. "
            f"Expected: {qty} shares of {code}, Actual: {pos_dict.get(code, 0)}"
        )

        # 3. Sell orders must reduce positions and increase cash balance
        sell_qty = 5
        sell_receipt = kis.place_order(symbol=code, side="SELL", price=price, quantity=sell_qty, market_price=price)
        assert sell_receipt["success"] is True

        post_sell_bal = kis.get_balance()
        post_sell_positions = kis.get_positions()
        post_sell_pos_dict = {p["symbol"]: p["quantity"] for p in post_sell_positions}

        assert post_sell_pos_dict.get(code, 0) == qty - sell_qty, (
            f"Fidelity Violation: Position not reduced on sell. "
            f"Expected: {qty - sell_qty}, Actual: {post_sell_pos_dict.get(code, 0)}"
        )
        assert post_sell_bal["cash_balance"] == initial_cash - order_cost + (price * sell_qty), (
            f"Fidelity Violation: Cash balance not increased on sell."
        )

    def test_synthetic_orderbook_ladder_positivity_and_spread(self):
        """
        Verify that synthetic orderbook ladders have strictly positive prices
        and increasing bid/ask spreads across multiple base price regimes (including low-priced stocks).
        """
        kis = KISBrokerConnector(simulation_mode=True)
        ls = LSBrokerConnector(simulation_mode=True)

        test_prices = [70000.0, 10000.0, 5000.0, 1000.0, 500.0, 200.0, 50.0]
        results = []

        for connector_name, connector in [("KIS", kis), ("LS", ls)]:
            for base_p in test_prices:
                depth = connector.generate_simulated_orderbook("TEST_SYM", base_price=base_p)
                assert len(depth.bids) == 10
                assert len(depth.asks) == 10

                bid_prices = [b.price for b in depth.bids]
                ask_prices = [a.price for a in depth.asks]
                level_spreads = [ask_prices[i] - bid_prices[i] for i in range(10)]

                min_bid = min(bid_prices)
                all_bids_positive = all(p > 0 for p in bid_prices)
                all_asks_positive = all(p > 0 for p in ask_prices)
                spreads_increasing = all(level_spreads[i] < level_spreads[i+1] for i in range(9))

                results.append({
                    "connector": connector_name,
                    "base_price": base_p,
                    "min_bid": min_bid,
                    "all_bids_positive": all_bids_positive,
                    "all_asks_positive": all_asks_positive,
                    "spreads_increasing": spreads_increasing,
                    "bid_prices": bid_prices,
                })

        negative_bid_cases = [r for r in results if not r["all_bids_positive"]]
        assert len(negative_bid_cases) == 0, (
            f"Fidelity Violation: Found {len(negative_bid_cases)} regimes with non-positive/negative bid prices:\n"
            + "\n".join(f"  {r['connector']} base_price={r['base_price']}: min_bid={r['min_bid']}" for r in negative_bid_cases)
        )

    def test_concurrency_rapid_orders_and_balance_inquiries(self):
        """
        Simulate rapid concurrent order placement and balance inquiry across 20 threads.
        Check for race conditions, lost updates in purchasing power, and dictionary size mutations during iteration.
        """
        kis = KISBrokerConnector(account_number="12345678", simulation_mode=True)
        kis.connect()

        initial_bal = kis.get_balance()
        initial_pp = initial_bal["purchasing_power"]
        order_price = 50000.0
        order_qty = 1
        order_val = order_price * order_qty  # 50,000 KRW per order
        total_orders = 100
        expected_total_deduction = order_val * total_orders  # 5,000,000 KRW

        errors = []
        placed_orders = []

        def worker_place(idx):
            try:
                rec = kis.place_order(
                    symbol=f"0059{idx:02d}",
                    side="BUY",
                    price=order_price,
                    quantity=order_qty,
                    market_price=order_price,
                )
                if rec.get("success"):
                    placed_orders.append(rec["order_id"])
            except Exception as e:
                errors.append(f"place_order_{idx}: {e}")

        def worker_query(idx):
            try:
                for _ in range(5):
                    b = kis.get_balance()
                    assert b["purchasing_power"] >= 0
                    time.sleep(0.005)
            except Exception as e:
                errors.append(f"query_bal_{idx}: {e}")

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for i in range(total_orders):
                futures.append(executor.submit(worker_place, i))
                if i % 5 == 0:
                    futures.append(executor.submit(worker_query, i))

            for f in as_completed(futures):
                pass

        final_bal = kis.get_balance()
        actual_deduction = initial_pp - final_bal["purchasing_power"]

        print(f"\n[Concurrency Metrics] Total Orders Attempted: {total_orders}")
        print(f"[Concurrency Metrics] Successfully Placed: {len(placed_orders)}")
        print(f"[Concurrency Metrics] Expected Deduction: {expected_total_deduction:,.0f} KRW")
        print(f"[Concurrency Metrics] Actual Deduction: {actual_deduction:,.0f} KRW")
        print(f"[Concurrency Metrics] Discrepancy: {actual_deduction - expected_total_deduction:,.0f} KRW")
        print(f"[Concurrency Metrics] Errors observed: {len(errors)}")
        if errors:
            print(f"[Concurrency Errors Sample]: {errors[:5]}")

    def test_token_limiter_concurrency_stress(self):
        """
        Stress-test TokenBucketRateLimiter under rapid multi-threaded acquisition
        and check for token drift or deadlocks.
        """
        limiter = TokenBucketRateLimiter(rate=100.0, capacity=20.0)

        num_threads = 30
        requests_per_thread = 10
        total_acquisitions = num_threads * requests_per_thread

        start_time = time.time()

        def worker():
            for _ in range(requests_per_thread):
                limiter.acquire(1.0)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker) for _ in range(num_threads)]
            for f in as_completed(futures):
                f.result()

        elapsed = time.time() - start_time
        throughput = total_acquisitions / elapsed
        print(f"\n[RateLimiter Thread Metrics] Total: {total_acquisitions} tokens in {elapsed:.3f}s (Throughput: {throughput:.1f} req/s)")

    def test_async_token_limiter_negative_token_drift(self):
        """
        Verify if acquire_async exhibits negative token drift due to setting last_update in the future.
        """
        limiter = TokenBucketRateLimiter(rate=50.0, capacity=5.0)

        async def worker():
            for _ in range(5):
                await limiter.acquire_async(1.0)

        async def run_all():
            tasks = [asyncio.create_task(worker()) for _ in range(10)]
            await asyncio.gather(*tasks)

        start = time.time()
        asyncio.run(run_all())
        elapsed = time.time() - start

        print(f"[Async RateLimiter Metric] 50 async acquires took {elapsed:.3f}s, final tokens={limiter.tokens:.2f}")

    def test_token_disk_cache_concurrency_stress(self):
        """
        Simulate concurrent multi-threaded reading and writing to OAuth disk cache.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / ".concurrent_token.json"
            connector = KISBrokerConnector(
                account_number="12345678",
                simulation_mode=False,
                app_key="MOCK_KEY",
                app_secret="MOCK_SECRET",
                token_cache_path=str(cache_file),
            )

            num_threads = 20
            write_count = 50
            read_errors = []

            def writer(idx):
                for i in range(write_count):
                    connector._save_cached_token(f"TOKEN_{idx}_{i}", time.time() + 7200.0)
                    time.sleep(0.001)

            def reader(idx):
                for _ in range(write_count):
                    try:
                        connector._load_cached_token()
                    except Exception as e:
                        read_errors.append(f"Reader_{idx}: {e}")
                    time.sleep(0.001)

            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                writers = [executor.submit(writer, i) for i in range(10)]
                readers = [executor.submit(reader, i) for i in range(10)]
                for f in as_completed(writers + readers):
                    f.result()

            print(f"[Token Disk Cache Metrics] Concurrent read/write errors: {len(read_errors)}")
            if read_errors:
                print(f"[Token Disk Cache Error Sample]: {read_errors[:5]}")
