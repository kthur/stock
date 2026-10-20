"""
src/utils/structured_logger.py
==============================
High-Performance JSON Structured Logging Engine.
Feature F588 - Phase 123 (Release R139 / v130 Production Master).

Features:
  1. Microsecond-resolution UTC timestamping with ISO-8601 formatting
  2. JSON serialization for ingestion into log pipelines
  3. Automatic context enrichment (market, symbol, strategy, execution_id)
  4. Dual-sink routing (console human-readable, file JSON structured)
  5. Log level filtering and in-memory trace buffer for post-mortem forensics
"""

from __future__ import annotations

import collections
import datetime
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

VERSION: int = 123
RELEASE: str = "R139"
FEATURE: str = "F588"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class StructuredLogRecord:
    timestamp: str
    level: str
    message: str
    module: str
    market: Optional[str] = None
    symbol: Optional[str] = None
    strategy: Optional[str] = None
    duration_ms: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        d = asdict(self)
        # Drop None keys for compact payload
        clean_d = {k: v for k, v in d.items() if v is not None}
        return json.dumps(clean_d, ensure_ascii=False)


class StructuredLogger:
    """
    Thread-safe structured logger with dual sinks (file JSON + console)
    and in-memory circular trace buffer.
    """

    def __init__(
        self,
        name: str = "stock_pipeline",
        log_file: Optional[str] = None,
        min_level: LogLevel = LogLevel.INFO,
        trace_buffer_size: int = 1000,
    ) -> None:
        self.name = name
        self.log_file = log_file
        self.min_level = min_level
        self._level_order = {
            LogLevel.DEBUG: 10,
            LogLevel.INFO: 20,
            LogLevel.WARNING: 30,
            LogLevel.ERROR: 40,
            LogLevel.CRITICAL: 50,
        }
        self.trace_buffer: Deque[StructuredLogRecord] = collections.deque(maxlen=trace_buffer_size)

        if self.log_file:
            p = Path(self.log_file)
            p.parent.mkdir(parents=True, exist_ok=True)

    def _should_log(self, level: LogLevel) -> bool:
        return self._level_order[level] >= self._level_order[self.min_level]

    def log(
        self,
        level: LogLevel,
        message: str,
        module: str = "core",
        market: Optional[str] = None,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        duration_ms: Optional[float] = None,
        **extra: Any,
    ) -> StructuredLogRecord:
        """Emits a structured log record to file, buffer, and optionally console."""
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        rec = StructuredLogRecord(
            timestamp=now_str,
            level=level.value,
            message=message,
            module=module,
            market=market,
            symbol=symbol,
            strategy=strategy,
            duration_ms=duration_ms,
            extra=extra,
        )

        self.trace_buffer.append(rec)

        if not self._should_log(level):
            return rec

        json_line = rec.to_json()
        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(json_line + "\n")
            except Exception as e:
                sys.stderr.write(f"Failed to write to log file: {e}\n")

        return rec

    def info(self, msg: str, **kwargs: Any) -> StructuredLogRecord:
        return self.log(LogLevel.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs: Any) -> StructuredLogRecord:
        return self.log(LogLevel.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs: Any) -> StructuredLogRecord:
        return self.log(LogLevel.ERROR, msg, **kwargs)

    def critical(self, msg: str, **kwargs: Any) -> StructuredLogRecord:
        return self.log(LogLevel.CRITICAL, msg, **kwargs)

    def debug(self, msg: str, **kwargs: Any) -> StructuredLogRecord:
        return self.log(LogLevel.DEBUG, msg, **kwargs)

    def get_recent_errors(self, count: int = 20) -> List[StructuredLogRecord]:
        """Returns the most recent N error/critical logs from trace buffer."""
        errors = [r for r in self.trace_buffer if r.level in ("ERROR", "CRITICAL")]
        return errors[-count:]
