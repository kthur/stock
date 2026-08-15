"""
API Circuit Breaker Utility
Prevents cascading timeouts during prolonged external API outages (e.g., yfinance rate limits / failures).
"""

import time
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

class CircuitBreakerOpenException(Exception):
    """Raised when an API call is attempted while the circuit breaker is open."""
    pass

class APICircuitBreaker:
    """
    Lightweight, thread-safe Circuit Breaker pattern implementation.
    States: CLOSED (normal), OPEN (tripped after N failures), HALF_OPEN (testing recovery after cooldown).
    """
    def __init__(self, name: str = "default", fail_max: int = 50, reset_timeout: float = 300.0):
        import math
        self.name = str(name)
        self.fail_max = max(1, int(fail_max)) if fail_max is not None else 50
        try:
            safe_timeout = float(reset_timeout) if (reset_timeout is not None and math.isfinite(float(reset_timeout))) else 300.0
        except (ValueError, TypeError):
            safe_timeout = 300.0
        self.reset_timeout = max(1.0, safe_timeout)

        self.consecutive_failures = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_state_change = time.time()

    def __call__(self, func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            return self.call(func, *args, **kwargs)
        return wrapper

    def call(self, func: Callable, *args, **kwargs) -> Any:
        now = time.time()

        # Check if OPEN circuit should transition to HALF_OPEN
        if self.state == "OPEN":
            if now - self.last_state_change > self.reset_timeout:
                logger.info(f"⚡ [CIRCUIT BREAKER: {self.name}] Transitioning from OPEN to HALF_OPEN (testing recovery)")
                self.state = "HALF_OPEN"
                self.last_state_change = now
            else:
                raise CircuitBreakerOpenException(
                    f"Circuit breaker '{self.name}' is OPEN due to {self.consecutive_failures} consecutive failures. "
                    f"Reset in {int(self.reset_timeout - (now - self.last_state_change))} seconds."
                )

        try:
            result = func(*args, **kwargs)
            # Success: reset failure count
            if self.state in ("HALF_OPEN", "OPEN"):
                logger.info(f"✅ [CIRCUIT BREAKER: {self.name}] Call succeeded! Closing circuit.")
                self.state = "CLOSED"
                self.last_state_change = now
            self.consecutive_failures = 0
            return result
        except Exception as e:
            self.consecutive_failures += 1
            logger.warning(f"⚠️ [CIRCUIT BREAKER: {self.name}] Failure #{self.consecutive_failures}/{self.fail_max}: {e}")

            if self.consecutive_failures >= self.fail_max and self.state != "OPEN":
                logger.error(f"🚨 [CIRCUIT BREAKER: {self.name}] TRIPPED TO OPEN after {self.consecutive_failures} failures.")
                self.state = "OPEN"
                self.last_state_change = now

            raise e

    def is_open(self) -> bool:
        if self.state == "OPEN":
            if time.time() - self.last_state_change > self.reset_timeout:
                self.state = "HALF_OPEN"
                self.last_state_change = time.time()
                return False
            return True
        return False


# Global default instances for yfinance and DART
yfinance_breaker = APICircuitBreaker(name="yfinance", fail_max=50, reset_timeout=300.0)
dart_breaker = APICircuitBreaker(name="dart", fail_max=30, reset_timeout=300.0)
