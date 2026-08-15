"""
data_fetcher.py — Data Stage Pipeline Component

Handles global market indicators fetch, stock universe synchronization,
batch price prefetching into StockPriceDB, and background fundamental updates.
"""

import logging
from datetime import datetime
from typing import Any, Dict
import pandas as pd

logger = logging.getLogger(__name__)


class PipelineDataFetcher:
    """
    Data Stage Component: Fetches macro indicators, updates stock universe,
    pre-caches price data into StockPriceDB, and fetches fundamental data.
    """

    def fetch_market_indicators(self, storage: Any, cfg: Any) -> Dict[str, float]:
        """Fetch latest global macro indicators (VIX, USDKRW, TNX, ECOS, etc.)."""
        import math
        logger.info("[DataFetcher] Fetching global market indicators...")
        market_summary: Dict[str, float] = {}

        if hasattr(storage, 'get_latest_global_indicators'):
            raw_summary = storage.get_latest_global_indicators() or {}
            for k, v in raw_summary.items():
                try:
                    f = float(v)
                    if math.isfinite(f):
                        market_summary[str(k).strip()] = f
                except (ValueError, TypeError):
                    continue

        date_str = datetime.now().strftime('%Y-%m-%d')
        if hasattr(storage, 'save_indicators') and market_summary:
            try:
                storage.save_indicators(market_summary, date_str)
                logger.info(f"[DataFetcher] Saved {len(market_summary)} market indicators for date {date_str}.")
            except Exception as e:
                logger.warning(f"[DataFetcher] Failed to save market indicators: {e}")

        return market_summary

    def load_universe(self, storage: Any) -> pd.DataFrame:
        """Load or synchronize full stock universe from database."""
        logger.info("[DataFetcher] Loading stock universe...")
        universe = pd.DataFrame()
        if hasattr(storage, 'get_universe'):
            try:
                u_res = storage.get_universe()
                if isinstance(u_res, pd.DataFrame):
                    universe = u_res
            except Exception as e:
                logger.warning(f"[DataFetcher] Failed to get universe from storage: {e}")

        if universe.empty and hasattr(storage, 'update_stock_universe'):
            logger.info("[DataFetcher] Universe empty. Syncing stock universe from exchanges...")
            try:
                storage.update_stock_universe()
                u_res = storage.get_universe()
                if isinstance(u_res, pd.DataFrame):
                    universe = u_res
            except Exception as e:
                logger.warning(f"[DataFetcher] Failed to sync universe: {e}")

        if not universe.empty and 'market' not in universe.columns and 'symbol' in universe.columns:
            universe['market'] = universe['symbol'].map(lambda s: 'KOSPI' if str(s).isdigit() else 'SP500')

        logger.info(f"[DataFetcher] Universe loaded: {len(universe)} symbols.")
        return universe

    def build_symbol_market_map(self, universe: pd.DataFrame) -> Dict[str, str]:
        """Returns symbol -> market dictionary."""
        if universe is None or not isinstance(universe, pd.DataFrame) or universe.empty or 'symbol' not in universe.columns or 'market' not in universe.columns:
            return {}
        return dict(zip(universe['symbol'].astype(str), universe['market'].astype(str)))
