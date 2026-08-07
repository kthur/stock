"""
ecos_client.py — Bank of Korea (ECOS) Open API Direct Client

Direct interface to Bank of Korea Open API (http://ecos.bok.or.kr) for:
- Base Rate (한국 기준금리)
- CD 91-Day Interest Rate (CD 91일물)
- Treasury 3Y & 10Y Yields (국고채 3년/10년)
- M2 Money Supply (M2 통화량)
"""

from __future__ import annotations

import logging
import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)

# Key BOK ECOS Statistics Item Codes
ECOS_ITEM_MAP: Dict[str, Dict[str, str]] = {
    "kr_base_rate": {"stat_code": "722Y001", "item_code": "0101000", "cycle": "D", "name": "한국 기준금리"},
    "cd_91d": {"stat_code": "817Y002", "item_code": "010502000", "cycle": "D", "name": "CD 91일물 금리"},
    "ktb_3y": {"stat_code": "817Y002", "item_code": "010200000", "cycle": "D", "name": "국고채 3년 금리"},
    "ktb_10y": {"stat_code": "817Y002", "item_code": "010210000", "cycle": "D", "name": "국고채 10년 금리"},
    "m2_supply": {"stat_code": "101Y003", "item_code": "BBGA00", "cycle": "M", "name": "M2 통화량"},
}


class BOKECOSClient:
    """Bank of Korea Open API Client with FRED/FDR Fallback."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = (api_key or os.environ.get("ECOS_API_KEY", "sample")).strip()

    def fetch_statistic(self, stat_code: str, item_code: str, cycle: str = "D",
                        start_date: str = "20200101", end_date: Optional[str] = None) -> pd.DataFrame:
        """Query BOK ECOS API endpoint for specified statistic item.

        API Format: http://ecos.bok.or.kr/api/StatisticSearch/{apiKey}/json/kr/1/1000/{stat_code}/{cycle}/{start_date}/{end_date}/{item_code}
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d" if cycle == "D" else "%Y%m")

        start_str = start_date.replace("-", "")[:8 if cycle == "D" else 6]
        end_str = end_date.replace("-", "")[:8 if cycle == "D" else 6]

        url = f"http://ecos.bok.or.kr/api/StatisticSearch/{self.api_key}/json/kr/1/1000/{stat_code}/{cycle}/{start_str}/{end_str}/{item_code}"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if "StatisticSearch" in data and "row" in data["StatisticSearch"]:
                rows = data["StatisticSearch"]["row"]
                df = pd.DataFrame(rows)
                if "TIME" in df.columns and "DATA_VALUE" in df.columns:
                    df["Date"] = pd.to_datetime(df["TIME"])
                    df["Value"] = pd.to_numeric(df["DATA_VALUE"], errors="coerce")
                    df = df.dropna(subset=["Value"]).sort_values("Date").reset_index(drop=True)
                    return df[["Date", "Value"]]
        except Exception as e:
            logger.debug("[BOKECOSClient] ECOS API fetch error for %s/%s: %s", stat_code, item_code, e)

        return pd.DataFrame(columns=["Date", "Value"])

    def fetch_korea_macro_rates(self, start_date: str = "2020-01-01") -> Dict[str, pd.DataFrame]:
        """Fetch all Korea key macro interest rates with BOK ECOS API and FDR fallback."""
        results: Dict[str, pd.DataFrame] = {}

        for key, meta in ECOS_ITEM_MAP.items():
            df_ecos = self.fetch_statistic(
                stat_code=meta["stat_code"],
                item_code=meta["item_code"],
                cycle=meta["cycle"],
                start_date=start_date
            )
            if not df_ecos.empty:
                results[key] = df_ecos
                logger.info("[BOKECOSClient] Fetched %s via BOK ECOS (%d rows)", meta["name"], len(df_ecos))
            else:
                # Fallback to FDR for FRED or KRX ETF proxies
                try:
                    import FinanceDataReader as fdr
                    fred_sym = "FRED:IRSTCI01KRM156N" if key in ("kr_base_rate", "cd_91d") else "FRED:IRLTLT01KRM156N"
                    raw_fdr = fdr.DataReader(fred_sym, start=start_date)
                    if raw_fdr is not None and not raw_fdr.empty:
                        c_col = raw_fdr.columns[0]
                        df_fb = pd.DataFrame({
                            "Date": raw_fdr.index,
                            "Value": raw_fdr[c_col]
                        }).dropna().reset_index(drop=True)
                        results[key] = df_fb
                        logger.info("[BOKECOSClient] %s fetched via FDR fallback (%d rows)", meta["name"], len(df_fb))
                except Exception as fb_e:
                    logger.warning("[BOKECOSClient] Fallback failed for %s: %s", key, fb_e)

        return results
