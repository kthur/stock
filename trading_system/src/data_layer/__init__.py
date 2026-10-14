"""
Data Layer Module — Market Indicators, Corporate Fundamentals, and Storage
Provides access to global market clients, FRED/ECOS data, point-in-time universe,
DART corporate filings, dark pool trackers, and SQLite WAL indicator storage.
"""

from __future__ import annotations

try:
    from src.data_layer.global_market import GlobalMarketClient
    from src.data_layer.market_data_handler import MarketDataHandler
    from src.data_layer.nlp_engine import NLPEngine, Sentiment
    from src.data_layer.fred_client import FredApiClient
    from src.data_layer.indicator_storage import MarketIndicatorStorage
    from src.data_layer.darkpool_tracker import DarkPoolTrackerEngine
    from src.data_layer.point_in_time_universe import PointInTimeUniverseManager
    from src.data_layer.dart_fundamental_fetcher import DARTFundamentalFetcher
except ImportError:
    from trading_system.src.data_layer.global_market import GlobalMarketClient
    from trading_system.src.data_layer.market_data_handler import MarketDataHandler
    from trading_system.src.data_layer.nlp_engine import NLPEngine, Sentiment
    from trading_system.src.data_layer.fred_client import FredApiClient
    from trading_system.src.data_layer.indicator_storage import MarketIndicatorStorage
    from trading_system.src.data_layer.darkpool_tracker import DarkPoolTrackerEngine
    from trading_system.src.data_layer.point_in_time_universe import PointInTimeUniverseManager
    from trading_system.src.data_layer.dart_fundamental_fetcher import DARTFundamentalFetcher

PointInTimeUniverse = PointInTimeUniverseManager

__all__ = [
    "GlobalMarketClient",
    "MarketDataHandler",
    "NLPEngine",
    "Sentiment",
    "FredApiClient",
    "MarketIndicatorStorage",
    "DarkPoolTrackerEngine",
    "PointInTimeUniverse",
    "PointInTimeUniverseManager",
    "DARTFundamentalFetcher",
]
