"""
St. Louis Federal Reserve Economic Data (FRED) API Client

Provides interest rate and macroeconomic indicator fetching using the official FRED API.
Specifically targets key series like:
- IRSTCI01KRM156N: Immediate Rates: Short-Term Loans / Certificates of Deposit for Korea (%)
- FEDFUNDS: Effective Federal Funds Rate (%)
- DGS10: 10-Year Treasury Constant Maturity Rate (%)
- DGS2: 2-Year Treasury Constant Maturity Rate (%)
- T10Y2Y: 10-Year Treasury Constant Maturity Minus 2-Year Treasury Constant Maturity (%)
"""

import json
import logging
import os
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, Optional
import pandas as pd


logger = logging.getLogger(__name__)

# Key FRED Series ID to Human Readable Name
FRED_SERIES_MAP: Dict[str, str] = {
    "IRSTCI01KRM156N": "Korea Short-Term Interest Rate",
    "FEDFUNDS": "US Federal Funds Effective Rate",
    "DGS10": "US 10-Year Treasury Yield",
    "DGS2": "US 2-Year Treasury Yield",
    "T10Y2Y": "US 10Y-2Y Treasury Yield Spread",
    "WALCL": "US Federal Reserve Total Assets",
}


class FredApiClient:
    """St. Louis FRED API Client for retrieving macro interest rates and economic indicators."""

    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FRED_API_KEY", "")
        if not self.api_key:
            # Attempt fallback from TradingConfig
            try:
                from src.config import TradingConfig
                cfg = TradingConfig()
                if cfg.fred_api_key:
                    self.api_key = cfg.fred_api_key
            except Exception:
                pass

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def fetch_series_observations(
        self,
        series_id: str,
        limit: int = 30,
        sort_order: str = "desc",
        observation_start: Optional[str] = None,
        max_retries: int = 3,
    ) -> pd.DataFrame:
        """Fetch historical observation series for a given FRED series ID.

        Args:
            series_id: FRED series identifier (e.g. 'IRSTCI01KRM156N', 'FEDFUNDS', 'DGS10')
            limit: Maximum number of recent observations to return
            sort_order: 'desc' (latest first) or 'asc'
            observation_start: Optional YYYY-MM-DD start date filter
            max_retries: Maximum HTTP retry attempts with backoff

        Returns:
            pd.DataFrame with Datetime index and 'value' float column.
        """
        if not self.is_configured():
            logger.warning(f"[FRED API] API key not configured; skipping request for {series_id}")
            return pd.DataFrame(columns=["value"])

        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": sort_order,
            "limit": str(limit),
        }
        if observation_start:
            params["observation_start"] = observation_start

        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"

        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (TradingSystem/1.0; FRED-Client)"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                    if resp.status != 200:
                        logger.warning(f"[FRED API] HTTP status {resp.status} for series {series_id} (attempt {attempt + 1})")
                        time.sleep(0.5 * (2 ** attempt))
                        continue

                    payload = json.loads(resp.read().decode("utf-8"))
                    obs_list = payload.get("observations", [])
                    if not obs_list:
                        logger.warning(f"[FRED API] Empty observations returned for series {series_id}")
                        return pd.DataFrame(columns=["value"])

                    records = []
                    for item in obs_list:
                        date_str = item.get("date")
                        val_str = item.get("value")
                        if date_str and val_str and val_str not in (".", "NA", "null", "None"):
                            try:
                                val_float = float(str(val_str).replace(",", ""))
                                dt = pd.to_datetime(date_str, errors='coerce')
                                if pd.notna(dt) and np.isfinite(val_float):
                                    records.append({"date": dt, "value": val_float})
                            except (ValueError, TypeError):
                                continue

                    if not records:
                        return pd.DataFrame(columns=["value"])

                    df = pd.DataFrame(records).dropna(subset=["date", "value"]).set_index("date")
                    if sort_order == "desc":
                        df = df.sort_index(ascending=True)
                    logger.info(f"[FRED API] Successfully fetched {len(df)} observations for {series_id}")
                    return df

            except Exception as e:
                logger.warning(f"[FRED API] Attempt {attempt + 1} failed for series '{series_id}': {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (2 ** attempt))
                else:
                    logger.error(f"[FRED API] All {max_retries} attempts failed for series '{series_id}': {e}")

        return pd.DataFrame(columns=["value"])

    def get_latest_rate(self, series_id: str) -> Optional[Dict[str, Any]]:
        """Fetch the most recent interest rate or indicator snapshot for a given series.

        Returns:
            Dict containing 'series_id', 'name', 'date', 'value', 'price', 'change_pct'
        """
        df = self.fetch_series_observations(series_id, limit=5, sort_order="desc")
        if df.empty or "value" not in df.columns:
            return None

        latest_val = float(df["value"].iloc[-1])
        prev_val = float(df["value"].iloc[-2]) if len(df) >= 2 else latest_val
        change_pct = ((latest_val - prev_val) / abs(prev_val) * 100.0) if prev_val != 0 else 0.0
        latest_date = df.index[-1].strftime("%Y-%m-%d") if hasattr(df.index[-1], "strftime") else str(df.index[-1])[:10]

        name = FRED_SERIES_MAP.get(series_id, series_id)
        return {
            "series_id": series_id,
            "name": name,
            "date": latest_date,
            "value": round(latest_val, 4),
            "price": round(latest_val, 4),
            "change_pct": round(change_pct, 2),
            "timestamp": datetime.now().isoformat(),
        }

    def fetch_korea_short_term_rate(self) -> Optional[Dict[str, Any]]:
        """Specific helper for IRSTCI01KRM156N (Korea Short-Term Certificates of Deposit / Loan Rate)."""
        return self.get_latest_rate("IRSTCI01KRM156N")

    def fetch_all_fred_indicators(self) -> Dict[str, Dict[str, Any]]:
        """Fetches latest snapshots for all configured FRED interest rate series concurrently in parallel."""
        results: Dict[str, Dict[str, Any]] = {}
        if not self.is_configured():
            return results

        with ThreadPoolExecutor(max_workers=min(8, len(FRED_SERIES_MAP))) as executor:
            future_to_sid = {executor.submit(self.get_latest_rate, sid): sid for sid in FRED_SERIES_MAP}
            for future in as_completed(future_to_sid):
                sid = future_to_sid[future]
                try:
                    info = future.result()
                    if info is not None:
                        results[sid] = info
                except Exception as e:
                    logger.warning(f"[FRED API] Parallel fetch error for {sid}: {e}")

        return results
