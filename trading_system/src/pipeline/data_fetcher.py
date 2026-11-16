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
        from datetime import timezone, timedelta
        kst = timezone(timedelta(hours=9))
        date_str = datetime.now(kst).strftime('%Y-%m-%d')
        logger.info("[DataFetcher] Fetching global market indicators...")
        market_summary: Dict[str, float] = {}

        # 1. Primary: Attempt live market indicator collection via GlobalMarketClient
        try:
            from src.data_layer.global_market import GlobalMarketClient
            client = GlobalMarketClient()
            summary = client.get_summary()
            if hasattr(storage, 'save_indicators') and summary:
                storage.save_indicators(summary, date_str)
        except Exception as e:
            logger.warning(f"[DataFetcher] Live GlobalMarketClient fetch failed: {e}. Falling back to DB cache.")

        # 2. Retrieve latest available indicators from storage (populated either by live fetch or prior cache)
        if hasattr(storage, 'get_latest_global_indicators'):
            raw_summary = storage.get_latest_global_indicators() or {}
            for k, v in raw_summary.items():
                try:
                    f = float(v)
                    if math.isfinite(f):
                        market_summary[str(k).strip()] = f
                except (ValueError, TypeError):
                    continue

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
