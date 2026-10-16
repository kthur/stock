"""
Data Layer Module — Market Indicators, Corporate Fundamentals, and Storage
Provides access to global market clients, FRED/ECOS data, point-in-time universe,
DART corporate filings, dark pool trackers, and SQLite WAL indicator storage.
Phase 113: Polars vectorized technical engine, DuckDB high-frequency OLAP, and streaming feature store.
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
    from src.data_layer.polars_indicator_engine import PolarsIndicatorEngine
    from src.data_layer.duckdb_analytical_engine import DuckDBAnalyticalEngine
    from src.data_layer.realtime_feature_store import RealTimeFeatureStore, MarketTick
    from src.data_layer.pcap_market_feed_processor import (
        PCAPMarketFeedProcessor,
        NASDAQITCH50Parser,
        MoldUDP64Parser,
        HardwareTimestampTracker,
        ITCHFeedPacketProcessor,
        ITCHMessage,
    )
except ImportError:
    from trading_system.src.data_layer.global_market import GlobalMarketClient
    from trading_system.src.data_layer.market_data_handler import MarketDataHandler
    from trading_system.src.data_layer.nlp_engine import NLPEngine, Sentiment
    from trading_system.src.data_layer.fred_client import FredApiClient
    from trading_system.src.data_layer.indicator_storage import MarketIndicatorStorage
    from trading_system.src.data_layer.darkpool_tracker import DarkPoolTrackerEngine
    from trading_system.src.data_layer.point_in_time_universe import PointInTimeUniverseManager
    from trading_system.src.data_layer.dart_fundamental_fetcher import DARTFundamentalFetcher
    from trading_system.src.data_layer.polars_indicator_engine import PolarsIndicatorEngine
    from trading_system.src.data_layer.duckdb_analytical_engine import DuckDBAnalyticalEngine
    from trading_system.src.data_layer.realtime_feature_store import RealTimeFeatureStore, MarketTick
    from trading_system.src.data_layer.pcap_market_feed_processor import (
        PCAPMarketFeedProcessor,
        NASDAQITCH50Parser,
        MoldUDP64Parser,
        HardwareTimestampTracker,
        ITCHFeedPacketProcessor,
        ITCHMessage,
    )

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
    "PolarsIndicatorEngine",
    "DuckDBAnalyticalEngine",
    "RealTimeFeatureStore",
    "MarketTick",
    "PCAPMarketFeedProcessor",
    "NASDAQITCH50Parser",
    "MoldUDP64Parser",
    "HardwareTimestampTracker",
    "ITCHFeedPacketProcessor",
    "ITCHMessage",
]
