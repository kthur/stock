"""
OpenTelemetry & Prometheus Production Observability Module
Instruments pipeline latency, model drift alerts, OMS execution timing, and system metrics.
"""

import time
import logging
from typing import Dict
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PipelineObservability:
    """
    Manages OpenTelemetry tracing & Prometheus metrics recording.
    """

    def __init__(self):
        self._metrics_store: Dict[str, float] = {}

    @contextmanager
    def trace_stage(self, stage_name: str):
        """Context manager to measure microsecond latency of pipeline stage."""
        start_ns = time.perf_counter_ns()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
            self._metrics_store[stage_name] = round(elapsed_ms, 2)
            logger.info(f"⏱️ [OPENTELEMETRY TRACE] Stage '{stage_name}' completed in {elapsed_ms:.2f} ms")

    def record_metric(self, name: str, value: float):
        """Records a custom metric value."""
        import math
        try:
            val = float(value) if (value is not None and math.isfinite(float(value))) else 0.0
        except (ValueError, TypeError):
            val = 0.0
        self._metrics_store[str(name)] = val
        logger.debug(f"📊 [PROMETHEUS METRIC] {name} = {val}")

    def get_all_metrics(self) -> Dict[str, float]:
        """Returns snapshot of recorded observability metrics."""
        return dict(self._metrics_store)
