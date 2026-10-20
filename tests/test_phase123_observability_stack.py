"""
tests/test_phase123_observability_stack.py
==========================================
Verification Test Suite for:
Structured Observability & Telemetry Collector Stack (Feature F588).
Phase 123 (Release R139 / v130 Production Master).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.utils.structured_logger import (
    VERSION,
    RELEASE,
    FEATURE,
    LogLevel,
    StructuredLogRecord,
    StructuredLogger,
)
from src.utils.metrics_collector import (
    MetricsCollector,
    MetricType,
    DEFAULT_METRICS_COLLECTOR,
)
from src.utils.health_checker import (
    ComponentHealth,
    HealthCheckItem,
    HealthChecker,
    SystemHealthReport,
)


class TestPhase123ObservabilityStack:
    """Comprehensive test suite for Feature F588."""

    def test_tc01_version_and_metadata(self):
        """Verifies metadata constants."""
        assert VERSION == 123
        assert RELEASE == "R139"
        assert FEATURE == "F588"

    def test_tc02_dual_tree_sha256_parity_logger(self):
        """Verifies 100% bit-for-bit SHA-256 parity for structured_logger.py."""
        f1 = PROJECT_ROOT / "src" / "utils" / "structured_logger.py"
        f2 = TRADING_SYSTEM_DIR / "src" / "utils" / "structured_logger.py"
        assert f1.exists(), f"File {f1} does not exist"
        assert f2.exists(), f"File {f2} does not exist"
        h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
        assert h1 == h2, f"SHA-256 mismatch: {h1} != {h2}"

    def test_tc03_dual_tree_sha256_parity_metrics(self):
        """Verifies 100% bit-for-bit SHA-256 parity for metrics_collector.py."""
        f1 = PROJECT_ROOT / "src" / "utils" / "metrics_collector.py"
        f2 = TRADING_SYSTEM_DIR / "src" / "utils" / "metrics_collector.py"
        assert f1.exists(), f"File {f1} does not exist"
        assert f2.exists(), f"File {f2} does not exist"
        h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
        assert h1 == h2, f"SHA-256 mismatch: {h1} != {h2}"

    def test_tc04_dual_tree_sha256_parity_health(self):
        """Verifies 100% bit-for-bit SHA-256 parity for health_checker.py."""
        f1 = PROJECT_ROOT / "src" / "utils" / "health_checker.py"
        f2 = TRADING_SYSTEM_DIR / "src" / "utils" / "health_checker.py"
        assert f1.exists(), f"File {f1} does not exist"
        assert f2.exists(), f"File {f2} does not exist"
        h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
        assert h1 == h2, f"SHA-256 mismatch: {h1} != {h2}"

    def test_tc05_package_exports(self):
        """Verifies exports from src.utils package."""
        import src.utils as utils_pkg
        assert hasattr(utils_pkg, "StructuredLogger")
        assert hasattr(utils_pkg, "MetricsCollector")
        assert hasattr(utils_pkg, "HealthChecker")

    def test_tc06_structured_logger_json_serialization(self):
        """Verifies structured log record JSON serialization format."""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            s_logger = StructuredLogger(log_file=tmp_path, min_level=LogLevel.DEBUG)
            rec = s_logger.info(
                "Execution dispatch complete",
                module="execution_oms",
                market="KOSPI",
                symbol="005930.KS",
                strategy="vcp_ml",
                duration_ms=4.5,
                order_id=98765,
            )
            assert rec.level == "INFO"
            assert rec.market == "KOSPI"
            assert rec.duration_ms == 4.5

            # Read back file content
            with open(tmp_path, "r", encoding="utf-8") as f:
                line = f.readline()
                data = json.loads(line)
                assert data["message"] == "Execution dispatch complete"
                assert data["module"] == "execution_oms"
                assert data["extra"]["order_id"] == 98765
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_tc07_structured_logger_trace_buffer(self):
        """Verifies trace buffer captures records and retrieves recent errors."""
        s_logger = StructuredLogger(min_level=LogLevel.INFO, trace_buffer_size=10)
        s_logger.info("Normal startup")
        s_logger.error("Order routing rejection", module="broker")
        s_logger.critical("Circuit breaker triggered", module="risk")

        errors = s_logger.get_recent_errors(5)
        assert len(errors) == 2
        assert errors[0].level == "ERROR"
        assert errors[1].level == "CRITICAL"

    def test_tc08_metrics_collector_counter_and_gauge(self):
        """Verifies thread-safe counters and gauges with multi-labels."""
        mc = MetricsCollector()
        labels = {"market": "SP500", "strategy": "regression"}
        mc.increment_counter("trades_executed", 1.0, labels=labels)
        mc.increment_counter("trades_executed", 2.0, labels=labels)
        assert mc.get_counter("trades_executed", labels=labels) == 3.0

        mc.set_gauge("portfolio_nav", 105000000.0, labels={"currency": "KRW"})
        assert mc.get_gauge("portfolio_nav", labels={"currency": "KRW"}) == 105000000.0

    def test_tc09_metrics_collector_timer_and_histogram(self):
        """Verifies histogram latency percentile calculation and timer context."""
        mc = MetricsCollector()
        labels = {"endpoint": "predict"}
        with mc.time_block("pipeline_step_latency_ms", labels=labels):
            time.sleep(0.01)

        pcts = mc.get_histogram_percentiles("pipeline_step_latency_ms", labels=labels)
        assert "p50" in pcts
        assert "p99" in pcts
        assert pcts["p50"] >= 5.0  # Slept at least 10ms

    def test_tc10_prometheus_exposition_export(self):
        """Verifies Prometheus text output format adheres to standard."""
        mc = MetricsCollector()
        mc.increment_counter("orders_total", 5.0, labels={"venue": "KRX"})
        mc.set_gauge("win_rate", 1.0, labels={"market": "GLOBAL"})
        prom_text = mc.to_prometheus_format()
        assert "orders_total_total{venue=\"KRX\"} 5.0" in prom_text
        assert "win_rate{market=\"GLOBAL\"} 1.0" in prom_text

    def test_tc11_health_checker_disk_and_db(self):
        """Verifies health checker evaluates disk space and SQLite connectivity."""
        hc = HealthChecker(db_paths=[":memory:"])
        report = hc.run_all_checks()
        assert isinstance(report, SystemHealthReport)
        assert report.version == 123
        assert report.total_components >= 2
        assert report.is_operational() is True

    def test_tc12_health_checker_component_registration(self):
        """Verifies registering degraded/critical components alters overall status."""
        hc = HealthChecker()
        hc.register_component_status("feed_handler", ComponentHealth.DEGRADED, "Heartbeat delayed by 500ms")
        report = hc.run_all_checks()
        assert report.overall_status == ComponentHealth.DEGRADED
        assert report.degraded_components >= 1

        hc.register_component_status("broker_gateway", ComponentHealth.CRITICAL, "Socket connection dropped")
        crit_report = hc.run_all_checks()
        assert crit_report.overall_status == ComponentHealth.CRITICAL
        assert crit_report.is_operational() is False

    def test_tc13_health_report_serialization(self):
        """Verifies system health report JSON serialization."""
        hc = HealthChecker(db_paths=[":memory:"])
        report = hc.run_all_checks()
        data = json.loads(report.to_json())
        assert data["version"] == 123
        assert data["release"] == "R139"
        assert "overall_status" in data
        assert isinstance(data["checks"], list)
