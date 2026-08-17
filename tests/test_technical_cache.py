"""
test_technical_cache.py — Unit tests for DataFrameCache module
"""

import time
import unittest
import threading
from datetime import datetime, timedelta
from unittest.mock import patch
import pandas as pd

from src.utils.technical_cache import DataFrameCache


class TestDataFrameCache(unittest.TestCase):

    def setUp(self):
        self.cache = DataFrameCache(ttl=0.2, max_items=3)

    def test_cache_hit_and_miss(self):
        fetch_count = 0

        def dummy_fetcher(symbol: str, start_date: str) -> pd.DataFrame:
            nonlocal fetch_count
            fetch_count += 1
            return pd.DataFrame({"Close": [100.0, 101.0, 102.0]})

        # Miss 1: calls fetcher
        df1 = self.cache.get_or_compute("AAPL", "2023-01-01", dummy_fetcher)
        self.assertEqual(fetch_count, 1)
        self.assertIsNotNone(df1)
        self.assertEqual(len(self.cache), 1)

        # Hit 1: return cached without calling fetcher
        df2 = self.cache.get_or_compute("AAPL", "2023-01-01", dummy_fetcher)
        self.assertEqual(fetch_count, 1)
        self.assertEqual(len(df2), 3)

        # Separate key miss
        df3 = self.cache.get_or_compute("MSFT", "2023-01-01", dummy_fetcher)
        self.assertEqual(fetch_count, 2)
        self.assertEqual(len(self.cache), 2)

    def test_ttl_auto_eviction(self):
        fetch_count = 0

        def dummy_fetcher(symbol: str, start_date: str) -> pd.DataFrame:
            nonlocal fetch_count
            fetch_count += 1
            return pd.DataFrame({"Close": [50.0, 51.0]})

        # Populate cache (TTL = 0.2s)
        self.cache.get_or_compute("NVDA", "2023-01-01", dummy_fetcher)
        self.assertEqual(fetch_count, 1)
        self.assertEqual(len(self.cache), 1)

        # Sleep past TTL
        time.sleep(0.25)

        # Active eviction on get()
        self.assertIsNone(self.cache.get("NVDA", "2023-01-01"))
        self.assertEqual(len(self.cache), 0)

        # Refetch after TTL expiration
        self.cache.get_or_compute("NVDA", "2023-01-01", dummy_fetcher)
        self.assertEqual(fetch_count, 2)

    def test_explicit_evict_expired(self):
        df_dummy = pd.DataFrame({"Close": [10.0]})
        self.cache.set("A", "2023-01-01", df_dummy)
        time.sleep(0.10)
        self.cache.set("B", "2023-01-01", df_dummy)
        time.sleep(0.15)

        # Key A is expired (> 0.2s), Key B is fresh (< 0.2s)
        evicted = self.cache.evict_expired()
        self.assertEqual(evicted, 1)
        self.assertIsNone(self.cache.get("A", "2023-01-01"))
        self.assertIsNotNone(self.cache.get("B", "2023-01-01"))

    def test_lru_capacity_eviction(self):
        # max_items = 3
        df_dummy = pd.DataFrame({"Close": [1.0]})
        self.cache.set("S1", "2023-01-01", df_dummy)
        time.sleep(0.01)
        self.cache.set("S2", "2023-01-01", df_dummy)
        time.sleep(0.01)
        self.cache.set("S3", "2023-01-01", df_dummy)
        self.assertEqual(len(self.cache), 3)

        # Adding 4th item triggers LRU eviction of S1 (oldest timestamp)
        time.sleep(0.01)
        self.cache.set("S4", "2023-01-01", df_dummy)
        self.assertLessEqual(len(self.cache), 3)
        self.assertIsNone(self.cache.get("S1", "2023-01-01"))
        self.assertIsNotNone(self.cache.get("S4", "2023-01-01"))

    def test_date_change_invalidation(self):
        df_dummy = pd.DataFrame({"Close": [200.0]})
        self.cache.set("GOOG", "2023-01-01", df_dummy)
        self.assertEqual(len(self.cache), 1)

        # Simulate date change to tomorrow
        tomorrow = datetime.now().date() + timedelta(days=1)
        with patch("src.utils.technical_cache.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = tomorrow
            # Accessing cache triggers date-change invalidation
            result = self.cache.get("GOOG", "2023-01-01")
            self.assertIsNone(result)
            self.assertEqual(len(self.cache), 0)

    def test_thread_safety(self):
        cache = DataFrameCache(ttl=5.0, max_items=100)
        errors = []

        def worker(sym_id: int):
            try:
                for i in range(50):
                    sym = f"SYM_{sym_id % 5}"
                    df = pd.DataFrame({"Close": [float(i)]})
                    cache.set(sym, "2023-01-01", df)
                    cache.get(sym, "2023-01-01")
                    cache.evict_expired()
                    if i % 10 == 0:
                        cache.invalidate(sym, "2023-01-01")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Thread errors encountered: {errors}")

    def test_invalidate_and_clear(self):
        df_dummy = pd.DataFrame({"Close": [1.0]})
        self.cache.set("TSLA", "2023-01-01", df_dummy)
        self.cache.set("AMZN", "2023-01-01", df_dummy)

        self.cache.invalidate("TSLA", "2023-01-01")
        self.assertIsNone(self.cache.get("TSLA", "2023-01-01"))
        self.assertIsNotNone(self.cache.get("AMZN", "2023-01-01"))

        self.cache.clear()
        self.assertEqual(len(self.cache), 0)


if __name__ == "__main__":
    unittest.main()
