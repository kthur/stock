"""
test_ring_buffer.py — Unit Tests for SQLite Async Ring Buffer Queue
"""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "trading_system")))

from src.persistence.ring_buffer import SQLiteAsyncRingBuffer


class TestRingBuffer(unittest.TestCase):

    def test_async_ring_buffer_flush(self):
        flushed_items = []

        def mock_callback(batch):
            flushed_items.extend(batch)

        buffer = SQLiteAsyncRingBuffer(batch_size=5, flush_interval=0.2)
        buffer.start(mock_callback)

        buffer.push_many([1, 2, 3, 4, 5, 6, 7])
        time.sleep(0.5)
        buffer.stop()

        self.assertEqual(len(flushed_items), 7)
        self.assertEqual(flushed_items, [1, 2, 3, 4, 5, 6, 7])


if __name__ == "__main__":
    unittest.main()
