import time
import threading
import logging

logger = logging.getLogger(__name__)

class GlobalRateLimiter:
    """
    A thread-safe global rate limiter that enforces a minimum interval
    between consecutive network requests across all threads.
    """
    def __init__(self, min_interval_seconds: float = 1.0):
        self.min_interval = min_interval_seconds
        self.lock = threading.Lock()
        self.last_request_time = 0.0

    def wait(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_request_time
            sleep_time = self.min_interval - elapsed
            if sleep_time > 0:
                logger.debug(f"GlobalRateLimiter: Sleeping {sleep_time:.2f}s to respect rate limit")
                time.sleep(sleep_time)
            self.last_request_time = time.time()

# Singleton rate limiter instance with 1.0 second min_interval (safe default)
_rate_limiter = GlobalRateLimiter(min_interval_seconds=1.0)

def get_global_rate_limiter() -> GlobalRateLimiter:
    return _rate_limiter
