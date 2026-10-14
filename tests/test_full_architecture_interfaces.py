"""
test_full_architecture_interfaces.py — Architecture Contract & Public Facade Verification

Verifies the architectural integrity, clean layer decoupling, and public exports across:
1. Execution Layer (`src.execution`)
2. Risk & Portfolio Layer (`src.risk`)
3. AI & Quantitative Modeling Layer (`src.ai`)
4. Analysis & Covariance Optimization Layer (`src.analysis`)
5. Data Layer & Indicator Storage (`src.data_layer`)
6. Persistence Layer (`src.persistence`)
7. Broker Multi-Venue Connectivity Layer (`src.broker`)
8. Core Engine & Microsecond LOB Layer (`src.core`)
9. Pipeline & Strategy Executor Dynamic Registry (`src.pipeline`)
"""

import math
import numpy as np
import pandas as pd
import pytest

# 1. Execution Layer
from trading_system.src.execution import (
    ExecutionOMSEngine,
    OMSEngine,
    AlmgrenChrissScheduler,
    SmartOrderRouter,
    TradeExecutor,
    ExecResult,
    is_kill_switch_active,
    engage as engage_kill_switch,
    disengage as disengage_kill_switch,
)

# 2. Risk Layer
from trading_system.src.risk import (
    RiskManager,
    RiskLevel,
    RiskMetrics,
    UnifiedPortfolioAllocator,
    PortfolioAllocator,
    IntradayStopLossEngine,
    StopLossSignal,
    PreTradeRiskGatekeeper,
    DeltaBetaHedgeOverlay,
)

# 3. AI Layer
from trading_system.src.ai import (
    OnDevicePredictionModel,
    EnsembleScoringEngine,
    CrossSectionalScoreNormalizer,
    FactorOrthogonalizerEngine,
    FactorSuppressionEngine,
)

# 4. Analysis Layer
from trading_system.src.analysis import (
    PortfolioOptimizer,
    StrategyCoverageAnalyzer,
    shrink_covariance_matrix,
    calculate_hrp_weights,
    calculate_risk_parity_weights,
    calculate_black_litterman_weights,
    MarketRegimeDetector,
)

# 5. Data Layer
from trading_system.src.data_layer import (
    MarketIndicatorStorage,
    DarkPoolTrackerEngine,
    PointInTimeUniverse,
    DARTFundamentalFetcher,
    GlobalMarketClient,
)

# 6. Persistence Layer
from trading_system.src.persistence import (
    StockPriceDB,
    AIPredictionDB,
    TradeLogger,
)

# 7. Broker Layer
from trading_system.src.broker import (
    InteractiveBrokersConnector,
    FIXProtocolEngine,
    MultiBrokerManager,
    BrokerType,
    KiwoomConnector,
)

# 8. Core Layer
from trading_system.src.core import (
    FastLOBEngine,
    ZeroCopyRingBuffer,
    FastOrderBookMatchingEngine,
    EventDrivenEngine,
    MQFactorEngine,
)

# 9. Pipeline Layer
from trading_system.src.pipeline import (
    AlphaStrategyExecutor,
    PipelineStrategyContext,
    StrategySpec,
    StrategyExecutionResult,
    save_strategy_predictions_report,
    format_prediction_line,
    slice_top_dataframe,
)


class TestFullArchitectureInterfaces:
    """Verifies that all 9 architectural layers provide clean, type-safe, cohesive interfaces."""

    def test_execution_layer_facade(self):
        """Execution layer provides unified access to OMS, SOR, TradeExecutor, and KillSwitch."""
        assert ExecutionOMSEngine is not None
        assert SmartOrderRouter is not None
        assert TradeExecutor is not None
        assert callable(is_kill_switch_active)

        # Instantiate TradeExecutor with dry run
        te = TradeExecutor(dry_run=True, lot_size_krx=1)
        assert te.lot_size_krx == 1

        res = te.execute("005930", "KOSPI", "BUY", quantity=5, price=71500.0)
        assert isinstance(res, ExecResult)
        assert res.executed
        assert res.quantity == 5

    def test_risk_layer_facade(self):
        """Risk layer provides UnifiedPortfolioAllocator, StopLossEngine, and RiskManager."""
        allocator = UnifiedPortfolioAllocator(target_volatility=0.12)
        assert allocator.target_volatility == 0.12
        assert "BULL_LOW_VOL" in allocator.REGIME_OPTIMIZER_BLENDS
        assert "CRISIS" in allocator.REGIME_OPTIMIZER_BLENDS

        stop_loss = IntradayStopLossEngine(peak_drop_threshold=-0.04)
        sig = stop_loss.evaluate("005930", {"current_price": 95.0, "peak_price": 100.0, "volume": 1000})
        assert isinstance(sig, StopLossSignal)
        assert sig.triggered

    def test_ai_layer_facade(self):
        """AI layer provides PredictionModel, EnsembleScoringEngine, and Normalizer."""
        assert OnDevicePredictionModel is not None
        assert EnsembleScoringEngine is not None
        assert FactorOrthogonalizerEngine is not None

        normalizer = CrossSectionalScoreNormalizer()
        raw_scores = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0], index=["A", "B", "C", "D", "E"])
        norm_scores = normalizer.normalize(raw_scores)
        assert len(norm_scores) == 5
        assert norm_scores.min() >= 0.0
        assert norm_scores.max() <= 1.0

    def test_analysis_layer_facade(self):
        """Analysis layer provides PortfolioOptimizer, MarketRegimeDetector, and StrategyCoverageAnalyzer."""
        assert PortfolioOptimizer is not None
        assert StrategyCoverageAnalyzer is not None
        assert MarketRegimeDetector is not None
        assert callable(shrink_covariance_matrix)
        assert callable(calculate_hrp_weights)

    def test_data_layer_facade(self):
        """Data layer exports MarketIndicatorStorage, DarkPoolTracker, PointInTimeUniverse."""
        assert MarketIndicatorStorage is not None
        assert DarkPoolTrackerEngine is not None
        assert PointInTimeUniverse is not None
        assert DARTFundamentalFetcher is not None

    def test_persistence_layer_facade(self):
        """Persistence layer exports StockPriceDB and AIPredictionDB."""
        assert StockPriceDB is not None
        assert AIPredictionDB is not None
        assert TradeLogger is not None

    def test_broker_layer_facade(self):
        """Broker layer exports InteractiveBrokersConnector, FIXProtocolEngine, and MultiBrokerManager."""
        assert InteractiveBrokersConnector is not None
        assert FIXProtocolEngine is not None
        assert MultiBrokerManager is not None

        # Verify IBKR default parameters
        ib = InteractiveBrokersConnector(host="127.0.0.1", port=7497)
        assert ib.host == "127.0.0.1"
        assert ib.port == 7497

    def test_core_engine_facade(self):
        """Core layer exports FastLOBEngine, ZeroCopyRingBuffer, and matching engines."""
        assert ZeroCopyRingBuffer is not None
        assert FastOrderBookMatchingEngine is not None
        assert EventDrivenEngine is not None

        ring_buf = ZeroCopyRingBuffer(capacity=1000)
        assert len(ring_buf.prices) == 1000

    def test_pipeline_strategy_executor_declarative_registry(self):
        """Pipeline layer provides complete 37-strategy score column mapping and dynamic registration."""
        executor = AlphaStrategyExecutor()

        # Check full declarative mapping
        cols = executor.get_all_strategy_columns()
        assert len(cols) >= 37
        assert cols["regression"] == "reg_score"
        assert cols["surge"] == "surge_score"
        assert cols["lstm"] == "lstm_score"
        assert cols["overnight_gap_reversal"] == "overnight_gap_score"

        # Check spec lookup
        lstm_spec = executor.get_spec("lstm")
        assert lstm_spec is not None
        assert lstm_spec.key == "lstm"
        assert lstm_spec.file == "lstm_predictions.txt"

        # Check dynamic registration
        def custom_eval(ctx):
            return pd.DataFrame({"symbol": ["AAPL"], "custom_score": [0.99]})

        custom_spec = StrategySpec(
            key="custom_alpha",
            name="Custom Quantitative Factor",
            evaluator=custom_eval,
            col="custom_score",
            title="Strategy: Custom Alpha",
            file="custom_alpha.txt",
        )
        executor.register_strategy(custom_spec)
        assert executor.get_spec("custom_alpha") is not None
        assert executor.get_all_strategy_columns()["custom_alpha"] == "custom_score"

    def test_pipeline_prediction_reporter_format_line(self):
        """PredictionReporter provides reusable line formatter with percentage scaling."""
        # Percentage format (fraction 0.08 -> 8.0%)
        line_pct = format_prediction_line(
            rank=1,
            symbol="005930",
            name="Samsung",
            market="KOSPI",
            score=0.084,
            header_width=14,
            is_percentage=True,
        )
        assert "005930" in line_pct
        assert "Samsung" in line_pct
        assert "8.4%" in line_pct

        # Raw float format (score 3.45)
        line_raw = format_prediction_line(
            rank=2,
            symbol="NVDA",
            name="Nvidia",
            market="NASDAQ",
            score=3.45,
            header_width=14,
            is_percentage=False,
        )
        assert "NVDA" in line_raw
        assert "3.45" in line_raw
