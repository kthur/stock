"""Unit tests for DARTCorpMapper (Phase 3-A: corp_code bug fix)"""

import json
import zipfile
import io
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.data_layer.dart_corp_mapper import DARTCorpMapper


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_zip_xml(entries: list[dict]) -> bytes:
    """Build a fake CORPCODE.xml ZIP in memory."""
    lines = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>", "<result>"]
    for e in entries:
        lines.append("<list>")
        lines.append(f"  <corp_code>{e['corp_code']}</corp_code>")
        lines.append(f"  <corp_name>{e.get('corp_name', 'Test Corp')}</corp_name>")
        lines.append(f"  <stock_code>{e['stock_code']}</stock_code>")
        lines.append("</list>")
    lines.append("</result>")
    xml_bytes = "\n".join(lines).encode("utf-8")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("CORPCODE.xml", xml_bytes)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDARTCorpMapper:

    def test_get_corp_code_no_api_key_no_cache(self, tmp_path):
        """Without API key and no cache, mapper should return None for any symbol."""
        mapper = DARTCorpMapper(api_key="", cache_path=str(tmp_path / "missing.json"))
        result = mapper.get_corp_code("005930")
        assert result is None

    def test_download_and_build_mapping(self, tmp_path):
        """Mapper should correctly parse CORPCODE.xml ZIP and resolve stock_code → corp_code."""
        entries = [
            {"corp_code": "00126380", "stock_code": "005930", "corp_name": "삼성전자"},
            {"corp_code": "00164779", "stock_code": "000660", "corp_name": "SK하이닉스"},
        ]
        zip_bytes = _make_zip_xml(entries)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = zip_bytes
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            mapper = DARTCorpMapper(api_key="dummy_key", cache_path=str(tmp_path / "test_cache.json"))
            assert mapper.get_corp_code("005930") == "00126380"
            assert mapper.get_corp_code("000660") == "00164779"
            assert mapper.get_corp_code("999999") is None

    def test_cache_roundtrip(self, tmp_path):
        """Mapping saved to cache should be loadable without a network call."""
        entries = [{"corp_code": "00126380", "stock_code": "005930"}]
        zip_bytes = _make_zip_xml(entries)
        cache_path = tmp_path / "cache.json"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = zip_bytes
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            mapper1 = DARTCorpMapper(api_key="dummy_key", cache_path=str(cache_path))
            assert mapper1.get_corp_code("005930") == "00126380"

        # Load from cache only (no API key)
        mapper2 = DARTCorpMapper(api_key="", cache_path=str(cache_path))
        assert mapper2.get_corp_code("005930") == "00126380"

    def test_stale_cache_triggers_refresh(self, tmp_path):
        """A cache older than _REFRESH_DAYS should trigger a new download."""
        from datetime import datetime, timedelta

        cache_path = tmp_path / "stale.json"
        # Write a cache with an old mtime
        cache_path.write_text(
            json.dumps({"updated_at": "2020-01-01T00:00:00", "mapping": {"005930": "99999999"}}),
            encoding="utf-8",
        )
        # Backdate the file modification time by 10 days
        old_mtime = (datetime.now() - timedelta(days=10)).timestamp()
        os.utime(str(cache_path), (old_mtime, old_mtime))

        entries = [{"corp_code": "00126380", "stock_code": "005930"}]
        zip_bytes = _make_zip_xml(entries)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = zip_bytes
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            mapper = DARTCorpMapper(api_key="dummy_key", cache_path=str(cache_path))
            # Should have downloaded fresh data, overwriting stale "99999999"
            assert mapper.get_corp_code("005930") == "00126380"

    def test_dart_news_fetcher_uses_corp_code_not_zfill(self, tmp_path):
        """DARTNewsFetcher must NOT pass symbol.zfill(8) as corp_code; must use DARTCorpMapper."""
        from src.data_layer.dart_news_fetcher import DARTNewsFetcher

        # Mapper returns correct corp_code
        mapper = DARTCorpMapper(api_key="", cache_path=str(tmp_path / "nc.json"))
        mapper._mapping = {"005930": "00126380"}
        mapper._loaded = True

        fetcher = DARTNewsFetcher(api_key="dummy_key", corp_mapper=mapper)

        captured_params = {}

        def mock_get(url, params=None, timeout=None):
            captured_params.update(params or {})
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"status": "000", "list": []}
            return mock_resp

        with patch("requests.get", side_effect=mock_get):
            fetcher.fetch_dart_disclosures("005930")

        # Must use real DART corp_code, not "00005930" (zfill(8) of "005930")
        assert captured_params.get("corp_code") == "00126380", (
            f"Expected '00126380' but got '{captured_params.get('corp_code')}'. "
            "Bug: fetcher is still using symbol.zfill(8) instead of DARTCorpMapper!"
        )

    def test_negation_context_suppresses_false_positive(self):
        """Keyword in negation context (e.g., '계획 없음') should NOT trigger risk."""
        from src.data_layer.dart_news_fetcher import DARTNewsFetcher

        fetcher = DARTNewsFetcher(api_key="")

        # Should NOT be detected as risk
        assert fetcher._match_risk_keyword("유상증자 계획 없음") is None
        assert fetcher._match_risk_keyword("횡령 무혐의 결정") is None
        assert fetcher._match_risk_keyword("소송 기각 판결") is None

        # Should be detected as risk (no negation)
        assert fetcher._match_risk_keyword("유상증자 결정 공시") == "유상증자"
        assert fetcher._match_risk_keyword("횡령 혐의로 임원 구속") == "횡령"
