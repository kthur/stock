"""
src/utils/metrics_collector.py
==============================
Distributed Metrics & Telemetry Aggregator with Prometheus Format.
Feature F588 - Phase 123 (Release R139 / v130 Production Master).

Features:
  1. Thread-safe Counters, Gauges, and Histograms with multidimensional labels
  2. Latency timer context managers and function decorators
  3. Real-time percentile approximations (P50, P90, P99)
  4. Native Prometheus text-based exposition exporter (to_prometheus_format)
  5. Zero external daemon requirement, completely self-contained
"""

from __future__ import annotations

import contextlib
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

VERSION: int = 123
RELEASE: str = "R139"
FEATURE: str = "F588"


class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


def _format_labels(labels: Dict[str, str]) -> str:
    if not labels:
        return ""
    items = [f'{k}="{v}"' for k, v in sorted(labels.items())]
    return "{" + ",".join(items) + "}"


class MetricsCollector:
    """
    In-process high-performance metrics aggregator.
    Tracks pipeline throughput, execution latencies, portfolio drawdown, and win rates.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = {}
        self._gauges: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = {}
        self._histograms: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], List[float]] = {}

    def _normalize_labels(self, labels: Optional[Dict[str, str]]) -> Tuple[Tuple[str, str], ...]:
        if not labels:
            return ()
        return tuple(sorted((str(k), str(v)) for k, v in labels.items()))

    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        key = (name, self._normalize_labels(labels))
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        key = (name, self._normalize_labels(labels))
        with self._lock:
            self._gauges[key] = float(value)

    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        key = (name, self._normalize_labels(labels))
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(float(value))
            # Keep bounded window
            if len(self._histograms[key]) > 5000:
                self._histograms[key] = self._histograms[key][-5000:]

    @contextlib.contextmanager
    def time_block(self, name: str, labels: Optional[Dict[str, str]] = None) -> Generator[None, None, None]:
        t0 = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            self.observe_histogram(name, elapsed_ms, labels=labels)

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        key = (name, self._normalize_labels(labels))
        with self._lock:
            return self._counters.get(key, 0.0)

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        key = (name, self._normalize_labels(labels))
        with self._lock:
            return self._gauges.get(key)

    def get_histogram_percentiles(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        percentiles: Tuple[float, ...] = (50.0, 90.0, 99.0),
    ) -> Dict[str, float]:
        key = (name, self._normalize_labels(labels))
        with self._lock:
            vals = self._histograms.get(key, [])
            if not vals:
                return {f"p{int(p)}": 0.0 for p in percentiles}
            res = {}
            for p in percentiles:
                res[f"p{int(p)}"] = float(np.percentile(vals, p))
            return res

    def to_prometheus_format(self) -> str:
        """Serializes all collected metrics into standard Prometheus exposition format."""
        lines: List[str] = [
            f"# Stock Quant Telemetry Metrics (Phase {VERSION} / {RELEASE})",
        ]
        with self._lock:
            # Counters
            for (name, label_pairs), val in self._counters.items():
                lbl_dict = dict(label_pairs)
                lbl_str = _format_labels(lbl_dict)
                lines.append(f"{name}_total{lbl_str} {val}")

            # Gauges
            for (name, label_pairs), val in self._gauges.items():
                lbl_dict = dict(label_pairs)
                lbl_str = _format_labels(lbl_dict)
                lines.append(f"{name}{lbl_str} {val}")

            # Histograms (count, sum, p50, p90, p99)
            for (name, label_pairs), vals in self._histograms.items():
                if not vals:
                    continue
                lbl_dict = dict(label_pairs)
                lbl_str = _format_labels(lbl_dict)
                lines.append(f"{name}_count{lbl_str} {len(vals)}")
                lines.append(f"{name}_sum{lbl_str} {sum(vals)}")
                p50 = float(np.percentile(vals, 50))
                p99 = float(np.percentile(vals, 99))
                lbl_p50 = dict(label_pairs)
                lbl_p50["quantile"] = "0.5"
                lbl_p99 = dict(label_pairs)
                lbl_p99["quantile"] = "0.99"
                lines.append(f"{name}{_format_labels(lbl_p50)} {p50}")
                lines.append(f"{name}{_format_labels(lbl_p99)} {p99}")

        return "\n".join(lines) + "\n"


# Global singleton instance
DEFAULT_METRICS_COLLECTOR = MetricsCollector()
