import time
import threading
import logging
import asyncio
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class GlobalRateLimiter:
    """
    Thread-safe & Async-safe Host-Aware Token Bucket Rate Limiter.
    Enforces independent burst and sustained rate limits across different external APIs
    (Yahoo, FRED, ECOS, DART, etc.) without head-of-line serial blocking.
    """
    DEFAULT_RATES = {
        'yahoo': {'rate': 5.0, 'capacity': 10.0},     # 5 req/s, burst up to 10
        'fred': {'rate': 10.0, 'capacity': 20.0},     # 10 req/s, burst up to 20
        'ecos': {'rate': 8.0, 'capacity': 15.0},      # 8 req/s, burst up to 15
        'dart': {'rate': 4.0, 'capacity': 8.0},       # 4 req/s, burst up to 8
        'default': {'rate': 3.0, 'capacity': 6.0},    # 3 req/s safe fallback
    }

    def __init__(self, min_interval_seconds: float = 0.33, rates: Optional[Dict] = None):
        self.lock = threading.Lock()
        self.rates = {k: dict(v) for k, v in self.DEFAULT_RATES.items()}
        if rates:
            self.rates.update(rates)

        # If a custom min_interval_seconds is provided and differs from default, adjust 'default'
        if min_interval_seconds > 0:
            default_rate = 1.0 / max(0.01, float(min_interval_seconds))
            self.rates['default'] = {'rate': default_rate, 'capacity': max(2.0, default_rate * 2.0)}

        self._tokens: Dict[str, float] = {}
        self._last_time: Dict[str, float] = {}

    @property
    def min_interval(self) -> float:
        default_rate = self.rates.get('default', {}).get('rate', 3.0)
        return 1.0 / max(default_rate, 1e-4)

    @min_interval.setter
    def min_interval(self, val: float):
        if val > 0:
            default_rate = 1.0 / float(val)
            self.rates['default'] = {'rate': default_rate, 'capacity': 1.0}
            self.rates['yahoo'] = {'rate': default_rate, 'capacity': 1.0}
            with self.lock:
                self._tokens.clear()

    def _get_host_key(self, source: str = 'default') -> str:
        s = str(source).lower()
        for key in ['yahoo', 'fred', 'ecos', 'dart']:
            if key in s:
                return key
        return 'default'

    def wait(self, source: str = 'default') -> None:
        key = self._get_host_key(source)
        cfg = self.rates.get(key, self.rates['default'])
        rate, capacity = cfg['rate'], cfg['capacity']

        sleep_time = 0.0
        with self.lock:
            now = time.time()
            if key not in self._last_time or key not in self._tokens:
                self._tokens[key] = capacity
                self._last_time[key] = now

            elapsed = max(0.0, now - self._last_time[key])
            self._tokens[key] = min(capacity, self._tokens[key] + elapsed * rate)
            self._last_time[key] = now

            self._tokens[key] -= 1.0
            if self._tokens[key] < 0.0:
                sleep_time = -self._tokens[key] / max(0.01, rate)

        if sleep_time > 0:
            logger.debug(f"GlobalRateLimiter[{key}]: Sleeping {sleep_time:.2f}s to respect rate limit")
            time.sleep(sleep_time)

    async def async_wait(self, source: str = 'default') -> None:
        """Asynchronously and thread-safely wait for token availability."""
        key = self._get_host_key(source)
        cfg = self.rates.get(key, self.rates['default'])
        rate, capacity = cfg['rate'], cfg['capacity']

        sleep_time = 0.0
        with self.lock:
            now = time.time()
            if key not in self._last_time or key not in self._tokens:
                self._tokens[key] = capacity
                self._last_time[key] = now

            elapsed = max(0.0, now - self._last_time[key])
            self._tokens[key] = min(capacity, self._tokens[key] + elapsed * rate)
            self._last_time[key] = now

            if self._tokens[key] >= 1.0:
                self._tokens[key] -= 1.0
                return
            else:
                sleep_time = (1.0 - self._tokens[key]) / max(0.1, rate)
                self._tokens[key] = 0.0

        if sleep_time > 0:
            logger.debug(f"GlobalRateLimiter[{key}]: Async sleeping {sleep_time:.2f}s to respect rate limit")
            await asyncio.sleep(sleep_time)

HostTokenBucketRateLimiter = GlobalRateLimiter
_rate_limiter = GlobalRateLimiter()

def get_global_rate_limiter() -> GlobalRateLimiter:
    return _rate_limiter
