"""DART Corp Code Mapper - Resolves stock symbol (6-digit) to OpenDART corp_code (8-digit).

OpenDART uses its own 8-digit corp_code, NOT the KRX stock symbol.
This module downloads the CORPCODE.xml from OpenDART and builds a lookup table.

Cache: trading_system/dart_corp_codes.json (refreshed weekly)
"""

import io
import json
import logging
import os
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
import xml.etree.ElementTree as ET

import requests

logger = logging.getLogger(__name__)

# Default cache file location (sibling to this module)
_DEFAULT_CACHE_PATH = Path(__file__).parent / "dart_corp_codes.json"
# Refresh interval for the corp_code XML
_REFRESH_DAYS = 7
# OpenDART CORPCODE endpoint
_CORPCODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"


class DARTCorpMapper:
    """Maps KRX stock symbols (6-digit) to OpenDART 8-digit corp_code.

    Usage:
        mapper = DARTCorpMapper(api_key="your_dart_api_key")
        corp_code = mapper.get_corp_code("005930")  # → "00126380"
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_path: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("DART_API_KEY", "").strip()
        self.cache_path = Path(cache_path) if cache_path else _DEFAULT_CACHE_PATH
        self._mapping: Dict[str, str] = {}  # stock_code → corp_code
        self._loaded = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_corp_code(self, stock_symbol: str) -> Optional[str]:
        """Return OpenDART corp_code for the given KRX stock symbol, or None if not found."""
        if not stock_symbol or not isinstance(stock_symbol, (str, int)):
            return None
        self._ensure_loaded()
        clean_code = str(stock_symbol).strip().split('.')[0].zfill(6) if str(stock_symbol).strip().split('.')[0].isdigit() else str(stock_symbol).strip()
        return self._mapping.get(clean_code) or self._mapping.get(str(stock_symbol).strip())

    def refresh(self) -> bool:
        """Force-download and rebuild the mapping table from OpenDART. Returns True on success."""
        if not self.api_key:
            logger.debug("DART_API_KEY not set – skipping CORPCODE refresh.")
            return False
        return self._download_and_build()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_cache(self, allow_stale: bool = False) -> bool:
        """Load the JSON cache if it exists and is not stale. Returns True on success."""
        if not self.cache_path.exists():
            return False
        if not allow_stale:
            mtime = datetime.fromtimestamp(self.cache_path.stat().st_mtime)
            if datetime.now() - mtime > timedelta(days=_REFRESH_DAYS):
                logger.info("DARTCorpMapper: cache is stale, will refresh.")
                return False
        try:
            with self.cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            self._mapping = data.get("mapping", {})
            logger.info(
                f"DARTCorpMapper: loaded {len(self._mapping)} corp_codes from cache "
                f"({self.cache_path.name}) [stale={allow_stale}]."
            )
            return bool(self._mapping)
        except Exception as e:
            logger.warning(f"DARTCorpMapper: failed to read cache: {e}")
            return False

    def ensure_loaded(self) -> None:
        """Ensure the corp_code mapping is loaded into memory."""
        if self._loaded:
            return
        if self._load_cache():
            self._loaded = True
            return
        # Cache miss or stale – try to download
        if self.api_key and self._download_and_build():
            self._loaded = True
        else:
            # V8-MED-02 Fix: Fall back to existing stale cache if download fails or API key is missing
            if self.cache_path.exists() and self._load_cache(allow_stale=True):
                logger.warning(
                    f"DARTCorpMapper: download failed, preserved existing stale cache ({self.cache_path.name})"
                )
                self._loaded = True
            else:
                logger.warning(
                    "DARTCorpMapper: no valid cache and no API key. "
                    "corp_code resolution will fail for all symbols."
                )
                self._loaded = True  # mark as loaded to avoid repeated retries

    _ensure_loaded = ensure_loaded

    def _download_and_build(self) -> bool:
        """Download CORPCODE.xml ZIP from OpenDART, parse it, build and cache the mapping."""
        try:
            logger.info("DARTCorpMapper: downloading CORPCODE.xml from OpenDART…")
            resp = requests.get(
                _CORPCODE_URL,
                params={"crtfc_key": self.api_key},
                timeout=30,
            )
            resp.raise_for_status()

            # The response is a ZIP file containing CORPCODE.xml
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                xml_filename = next(
                    (n for n in zf.namelist() if n.lower().endswith(".xml")),
                    None,
                )
                if xml_filename is None:
                    logger.error("DARTCorpMapper: no XML file found inside ZIP.")
                    return False
                xml_bytes = zf.read(xml_filename)

            root = ET.fromstring(xml_bytes)  # nosec B314
            mapping: Dict[str, str] = {}
            for company in root.findall("list"):
                stock_code = (company.findtext("stock_code") or "").strip()
                corp_code = (company.findtext("corp_code") or "").strip()
                if stock_code and corp_code:
                    mapping[stock_code] = corp_code

            self._mapping = mapping
            self._save_cache()
            logger.info(
                f"DARTCorpMapper: built mapping table with {len(mapping)} entries."
            )
            return True

        except Exception as e:
            logger.warning(f"DARTCorpMapper: failed to download/parse CORPCODE.xml: {e}")
            return False

    def _save_cache(self):
        """Persist the mapping to the JSON cache file using atomic write."""
        tmp_path = self.cache_path.with_suffix(".tmp")
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(
                    {
                        "updated_at": datetime.now().isoformat(),
                        "count": len(self._mapping),
                        "mapping": self._mapping,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            tmp_path.replace(self.cache_path)
            logger.info(f"DARTCorpMapper: cache saved to {self.cache_path}.")
        except Exception as e:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
            logger.warning(f"DARTCorpMapper: failed to save cache: {e}")
