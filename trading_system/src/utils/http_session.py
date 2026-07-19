"""Centralized HTTP session and User-Agent configuration helper."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_GLOBAL_SESSION = None
_GLOBAL_PATCHED = False


def get_configured_session() -> requests.Session:
    """Return a configured requests.Session with custom headers, connection pooling, and retry strategy."""
    global _GLOBAL_SESSION
    if _GLOBAL_SESSION is None:
        session = requests.Session()
        session.headers.update({
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
            "Connection": "keep-alive"
        })
        retry_strategy = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=retry_strategy
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        _GLOBAL_SESSION = session
    return _GLOBAL_SESSION


def setup_global_http_headers() -> None:
    """Inject browser User-Agent default headers into all requests.Session instances globally."""
    global _GLOBAL_PATCHED
    if _GLOBAL_PATCHED:
        return
    
    # Initialize configured session instance first
    get_configured_session()

    original_init = requests.Session.__init__

    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.headers.update({
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
        })

    requests.Session.__init__ = new_init  # type: ignore[method-assign]
    _GLOBAL_PATCHED = True
