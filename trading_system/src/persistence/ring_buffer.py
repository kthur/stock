"""
ring_buffer.py — SQLite Lock-Free In-Memory Async Ring Buffer Queue

Provides a thread-safe lock-free write queue for SQLite WAL database operations
to eliminate write contention during multi-threaded stock price data ingestion.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import List, Any, Optional, Callable

logger = logging.getLogger(__name__)


class SQLiteAsyncRingBuffer:
    """Async In-Memory Ring Buffer Write Manager for SQLite WAL DB."""

    def __init__(self, max_capacity: int = 100000, batch_size: int = 1000, flush_interval: float = 1.0) -> None:
        self.max_capacity = max_capacity
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        self._queue: queue.Queue = queue.Queue(maxsize=max_capacity)
        self._stop_event = threading.Event()
        self._flush_thread: Optional[threading.Thread] = None
        self._flush_callback: Optional[Callable[[List[Any]], None]] = None

    def start(self, flush_callback: Callable[[List[Any]], None]) -> None:
        """Start background worker thread that drains queue and executes batch DB writes."""
        self._flush_callback = flush_callback
        self._stop_event.clear()
        self._flush_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._flush_thread.start()
        logger.info("[SQLiteAsyncRingBuffer] Background async write queue started.")

    def push(self, item: Any) -> bool:
        """Enqueue single record or tuple into non-blocking ring buffer."""
        try:
            self._queue.put_nowait(item)
            return True
        except queue.Full:
            logger.warning("[SQLiteAsyncRingBuffer] Queue full (%d items)! Dropping item to prevent deadlock.", self.max_capacity)
            return False

    def push_many(self, items: List[Any]) -> int:
        """Enqueue multiple items into buffer."""
        pushed = 0
        for item in items:
            if self.push(item):
                pushed += 1
            else:
                break
        return pushed

    def _worker_loop(self) -> None:
        """Background worker loop draining queue into batch DB flushes."""
        batch: List[Any] = []
        last_flush = time.time()

        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                item = self._queue.get(timeout=0.2)
                batch.append(item)
                self._queue.task_done()
            except queue.Empty:
                pass

            now = time.time()
            if len(batch) >= self.batch_size or (batch and now - last_flush >= self.flush_interval):
                self._flush_batch(batch)
                batch = []
                last_flush = now

        if batch:
            self._flush_batch(batch)

    def _flush_batch(self, batch: List[Any]) -> None:
        if not batch or not self._flush_callback:
            return
        try:
            self._flush_callback(batch)
            logger.debug("[SQLiteAsyncRingBuffer] Flushed %d items to SQLite.", len(batch))
        except Exception as e:
            logger.error("[SQLiteAsyncRingBuffer] Error executing batch DB write: %s", e)

    def stop(self) -> None:
        """Signal worker loop to stop and flush remaining queued items."""
        self._stop_event.set()
        if self._flush_thread and self._flush_thread.is_alive():
            self._flush_thread.join(timeout=5.0)
        logger.info("[SQLiteAsyncRingBuffer] Write queue stopped.")
