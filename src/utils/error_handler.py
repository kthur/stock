"""Error Handling - 예외 처리 및 복구"""

import asyncio
import logging
import threading
import time
from collections import deque
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import datetime
from enum import Enum
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """에러 심각도"""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorHandler:
    """에러 핸들링 시스템"""

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        초기화

        Args:
            max_retries: 최대 재시도 횟수
            retry_delay: 재시도 지연 시간 (초)
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.error_history: deque = deque(maxlen=500)
        self.logger = logger
        self.error_callbacks: List[Callable] = []
        self.recovery_enabled = True
        self._circuit_states: dict = {}
        self._circuit_lock = threading.Lock()

    def retry_with_exponential_backoff(self, func: Callable, *args, **kwargs) -> Any:
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Attempting {func.__name__} (attempt {attempt + 1}/{self.max_retries})")
                return func(*args, **kwargs)
            except Exception as e:
                wait_time = self.retry_delay * (2**attempt)
                if attempt < self.max_retries - 1:
                    self.logger.warning(f"Error in {func.__name__}: {e}. Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Failed after {self.max_retries} retries: {e}")
                    self._record_error(func.__name__, e, ErrorSeverity.ERROR)
                    raise

    async def async_retry_with_exponential_backoff(self, func: Callable, *args, **kwargs) -> Any:
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Attempting {func.__name__} (attempt {attempt + 1}/{self.max_retries})")
                return await func(*args, **kwargs)
            except Exception as e:
                wait_time = self.retry_delay * (2**attempt)
                if attempt < self.max_retries - 1:
                    self.logger.warning(f"Error in {func.__name__}: {e}. Retrying in {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"Failed after {self.max_retries} retries: {e}")
                    self._record_error(func.__name__, e, ErrorSeverity.ERROR)
                    raise

    def validate_data(self, data: Any, validator: Callable) -> bool:
        """
        데이터 검증

        Args:
            data: 검증할 데이터
            validator: 검증 함수

        Returns:
            검증 결과
        """
        try:
            result = bool(validator(data))
            if not result:
                self.logger.warning(f"Data validation failed: {data}")
                self._record_error("data_validation", Exception("Validation failed"), ErrorSeverity.WARNING)
            return result
        except Exception as e:
            self.logger.error(f"Validation error: {e!s}")
            self._record_error("data_validation", e, ErrorSeverity.ERROR)
            return False

    def handle_transaction(self, transaction_func: Callable, rollback_func: Callable, *args, **kwargs) -> bool:
        """
        트랜잭션 처리 (commit/rollback)

        Args:
            transaction_func: 트랜잭션 함수
            rollback_func: 롤백 함수
            *args: 트랜잭션 함수의 인수
            **kwargs: 트랜잭션 함수의 키워드 인수

        Returns:
            성공 여부
        """
        try:
            self.logger.info(f"Starting transaction: {transaction_func.__name__}")
            transaction_func(*args, **kwargs)
            self.logger.info(f"Transaction committed: {transaction_func.__name__}")
            return True

        except Exception as e:
            self.logger.error(f"Transaction failed: {e!s}. Rolling back...")

            try:
                rollback_func()
                self.logger.info("Rollback successful")
            except Exception as rollback_error:
                self.logger.critical(f"Rollback failed: {rollback_error!s}")
                self._record_error("rollback", rollback_error, ErrorSeverity.CRITICAL)
                return False

            self._record_error(transaction_func.__name__, e, ErrorSeverity.ERROR)
            return False

    def circuit_breaker(
        self, func: Callable, *args, failure_threshold: int = 5, recovery_timeout: int = 60, **kwargs
    ) -> Optional[Any]:
        """
        Circuit Breaker 패턴

        Args:
            func: 실행할 함수
            *args: 함수의 위치 인수
            failure_threshold: 실패 임계값
            recovery_timeout: 복구 타임아웃 (초)
            **kwargs: 함수의 키워드 인수

        Returns:
            함수의 반환값 또는 None
        """
        func_key = id(func)
        with self._circuit_lock:
            if func_key not in self._circuit_states:
                self._circuit_states[func_key] = {"state": "closed", "failure_count": 0, "last_failure_time": None}
            state = self._circuit_states[func_key]

            if state["state"] == "open":
                if state["last_failure_time"]:
                    elapsed = (datetime.now() - state["last_failure_time"]).total_seconds()
                    if elapsed > recovery_timeout:
                        self.logger.info(f"Circuit breaker for {func.__name__} entering half-open state")
                        state["state"] = "half-open"
                        state["failure_count"] = 0
                    else:
                        self.logger.warning(f"Circuit breaker open for {func.__name__}")
                        return None

        try:
            result = func(*args, **kwargs)

            with self._circuit_lock:
                if state["state"] == "half-open":
                    self.logger.info(f"Circuit breaker for {func.__name__} closing")
                    state["state"] = "closed"
                    state["failure_count"] = 0

            return result

        except Exception as e:
            with self._circuit_lock:
                state["failure_count"] += 1
                state["last_failure_time"] = datetime.now()

            self.logger.error(f"Function {func.__name__} failed: {e!s}")

            with self._circuit_lock:
                if state["failure_count"] >= failure_threshold:
                    state["state"] = "open"
                    self.logger.critical(f"Circuit breaker opened for {func.__name__}")
                    self._record_error(func.__name__, e, ErrorSeverity.CRITICAL)

            return None

    def timeout(self, func: Callable, timeout_seconds: float, *args, **kwargs) -> Optional[Any]:
        """
        타임아웃 처리 (Windows/Unix 크로스 플랫폼 지원)

        Args:
            func: 실행할 함수
            timeout_seconds: 타임아웃 시간 (초)
            *args: 함수의 위치 인수
            **kwargs: 함수의 키워드 인수

        Returns:
            함수의 반환값 또는 None
        """
        import math
        try:
            safe_timeout = float(timeout_seconds) if (timeout_seconds is not None and math.isfinite(float(timeout_seconds))) else 30.0
        except (ValueError, TypeError):
            safe_timeout = 30.0
        safe_timeout = max(0.1, safe_timeout)

        result_future: Future = Future()

        def target():
            try:
                result = func(*args, **kwargs)
                result_future.set_result(result)
            except Exception as e:
                result_future.set_exception(e)

        thread = threading.Thread(target=target, daemon=True)
        thread.start()

        try:
            return result_future.result(timeout=safe_timeout)
        except FutureTimeoutError:
            error_msg = f"Function {func.__name__} timed out after {safe_timeout} seconds"
            self.logger.error(error_msg)
            self._record_error(func.__name__, TimeoutError(error_msg), ErrorSeverity.ERROR)
            return None
        except Exception as e:
            self.logger.error(f"Error in {func.__name__}: {e!s}")
            self._record_error(func.__name__, e, ErrorSeverity.ERROR)
            return None

    def register_error_callback(self, callback: Callable):
        """에러 콜백 등록"""
        self.error_callbacks.append(callback)
        self.logger.info(f"Error callback registered: {callback.__name__}")

    def _record_error(self, source: str, error: Exception, severity: ErrorSeverity):
        """에러 기록"""
        record = {
            "source": source,
            "error": str(error),
            "error_type": type(error).__name__,
            "severity": severity.value,
            "timestamp": datetime.now(),
        }

        self.error_history.append(record)

        # 콜백 실행
        for callback in self.error_callbacks:
            try:
                callback(record)
            except Exception as e:
                self.logger.error(f"Error callback failed: {e!s}")

    def get_error_history(self, limit: int = 100) -> List[dict]:
        """에러 이력 조회"""
        return list(self.error_history)[-limit:]

    def get_errors_by_severity(self, severity: ErrorSeverity) -> List[dict]:
        """심각도별 에러 조회"""
        return [e for e in self.error_history if e["severity"] == severity.value]

    def clear_error_history(self):
        """에러 이력 초기화"""
        self.error_history.clear()
        self.logger.info("Error history cleared")

    def get_error_summary(self) -> dict:
        """에러 요약"""
        return {
            "total_errors": len(self.error_history),
            "critical": len(self.get_errors_by_severity(ErrorSeverity.CRITICAL)),
            "errors": len(self.get_errors_by_severity(ErrorSeverity.ERROR)),
            "warnings": len(self.get_errors_by_severity(ErrorSeverity.WARNING)),
            "recovery_enabled": self.recovery_enabled,
            "timestamp": datetime.now().isoformat(),
        }


def safe_strategy_execute(strategy_name: str, func: Callable, *args, **kwargs) -> Any:
    """
    Executes a strategy function inside a safety isolation wrapper.
    If an unhandled exception occurs, logs the error trace and returns an empty DataFrame or fallback,
    preventing pipeline crashes and allowing the ensemble to proceed.
    """
    import pandas as pd
    try:
        res = func(*args, **kwargs)
        if isinstance(res, pd.DataFrame):
            logger.info(f"✅ Strategy '{strategy_name}' executed successfully ({len(res)} predictions).")
            return res
        elif res is not None:
            logger.info(f"✅ Strategy '{strategy_name}' executed successfully.")
            return res
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"❌ Strategy '{strategy_name}' FAILED with exception: {e}", exc_info=True)
        return pd.DataFrame()
