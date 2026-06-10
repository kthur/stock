import os
import json
import pytest
import math
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# ==============================================================================
# yfinance Mocking Fixture (prevents HTTP timeouts under CODE_ONLY)
# ==============================================================================
@pytest.fixture(autouse=True)
def mock_yfinance_calls():
    """Mock yfinance.Ticker and yfinance.download globally to prevent timeouts."""
    with patch("yfinance.Ticker") as mock_ticker, \
         patch("yfinance.download") as mock_download:
        
        # Create a mock DataFrame for downloads/history
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.head.return_value = mock_df
        mock_df.tail.return_value = mock_df
        
        # Mock download return
        mock_download.return_value = mock_df
        
        # Mock Ticker instance return
        mock_instance = MagicMock()
        mock_instance.history.return_value = mock_df
        mock_instance.info = {"regularMarketPrice": 150.0, "volume": 1000000}
        mock_ticker.return_value = mock_instance
        
        yield mock_ticker, mock_download

# ==============================================================================
# Helper Classes and Functions
# ==============================================================================
class MockPriceBar:
    def __init__(self, timestamp, open_, high, low, close, volume):
        self.timestamp = timestamp
        self.open = open_
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

def generate_mock_bars(count=100, trend="flat", base_price=100.0, vol=1000000):
    bars = []
    current_time = datetime.now() - timedelta(days=count)
    for i in range(count):
        if trend == "bull":
            price = base_price + i * 0.5 + (i % 3 - 1)
        elif trend == "bear":
            price = base_price - i * 0.5 + (i % 3 - 1)
        else:
            price = base_price + (i % 5 - 2)
        
        bars.append(MockPriceBar(
            timestamp=current_time + timedelta(days=i),
            open_=price - 0.5,
            high=price + 1.0,
            low=price - 1.0,
            close=price,
            volume=vol
        ))
    return bars

# ==============================================================================
# TIER 1: FEATURE COVERAGE (HAPPY PATH - 25 Tests)
# ==============================================================================

# F1: Parameter Optimization (R1)
def test_r1_optimize_parameters_happy_path():
    """R1: optimize_parameters returns correct result structure."""
    from src.analysis.backtest import BacktestEngine
    engine = BacktestEngine(initial_capital=1000000)
    bars = generate_mock_bars(50)
    param_ranges = {"short_window": [10, 20], "long_window": [30, 40]}
    
    # Expected contract defines strategy_name argument and caching
    result = engine.optimize_parameters("AAPL", bars, param_ranges, strategy_name="MA")
    assert "best_params" in result
    assert "best_result" in result
    assert "best_return" in result

def test_r1_json_saving_happy_path():
    """R1: optimization result is saved to data/optimized_params.json."""
    from src.analysis.backtest import BacktestEngine
    engine = BacktestEngine(initial_capital=1000000)
    bars = generate_mock_bars(50)
    param_ranges = {"short_window": [10, 20], "long_window": [30, 40]}
    
    if os.path.exists("data/optimized_params.json"):
        os.remove("data/optimized_params.json")
        
    engine.optimize_parameters("AAPL", bars, param_ranges, strategy_name="MA")
    
    assert os.path.exists("data/optimized_params.json")
    with open("data/optimized_params.json", "r") as f:
        data = json.load(f)
    assert "best_params" in data
    assert "best_return" in data
    assert "sharpe_ratio" in data

def test_r1_best_params_structure():
    """R1: saved best_params contains the strategy's optimized window parameters."""
    from src.analysis.backtest import BacktestEngine
    engine = BacktestEngine(initial_capital=1000000)
    bars = generate_mock_bars(50)
    param_ranges = {"short_window": [10, 20], "long_window": [30, 40]}
    
    engine.optimize_parameters("AAPL", bars, param_ranges, strategy_name="MA")
    
    with open("data/optimized_params.json", "r") as f:
        data = json.load(f)
    best_params = data["best_params"]
    assert isinstance(best_params, dict)
    assert "short_window" in best_params
    assert "long_window" in best_params

def test_r1_caching_happy_path():
    """R1: calling optimizer a second time retrieves from data/optimized_params.json directly."""
    from src.analysis.backtest import BacktestEngine
    engine = BacktestEngine(initial_capital=1000000)
    bars = generate_mock_bars(50)
    param_ranges = {"short_window": [15], "long_window": [45]}
    
    # Run once to cache
    engine.optimize_parameters("AAPL", bars, param_ranges, strategy_name="MA")
    
    # Modify cache file to verify it is retrieved
    with open("data/optimized_params.json", "w") as f:
        json.dump({
            "best_params": {"short_window": 99, "long_window": 99},
            "best_return": 999.9,
            "sharpe_ratio": 9.9
        }, f)
        
    # Second run should read cache
    result = engine.optimize_parameters("AAPL", bars, param_ranges, strategy_name="MA")
    assert result["best_params"]["short_window"] == 99
    assert result["best_return"] == 999.9

def test_r1_different_strategy_happy_path():
    """R1: optimizes non-default strategy (e.g. RSI) and saves successfully."""
    from src.analysis.backtest import BacktestEngine
    engine = BacktestEngine(initial_capital=1000000)
    bars = generate_mock_bars(50)
    param_ranges = {"rsi_period": [10, 14], "rsi_oversold": [30]}
    
    result = engine.optimize_parameters("AAPL", bars, param_ranges, strategy_name="RSI")
    assert "best_params" in result
    assert "rsi_period" in result["best_params"]


# F2: Market Regime & Strategy Switching (R2)
def test_r2_detect_regime_bull():
    """R2: detect_regime returns 'bull' in an upward trend."""
    from src.core.strategy_engine import HybridStrategyEngine
    engine = HybridStrategyEngine()
    bars = generate_mock_bars(250, trend="bull")
    
    regime = engine.detect_regime(bars)
    assert regime in ("strong_bull", "weak_bull"), f"Expected bull regime, got {regime}"

def test_r2_detect_regime_bear():
    """R2: detect_regime returns 'bear' in a downward trend."""
    from src.core.strategy_engine import HybridStrategyEngine
    engine = HybridStrategyEngine()
    bars = generate_mock_bars(250, trend="bear")
    
    regime = engine.detect_regime(bars)
    assert regime in ("strong_bear", "weak_bear"), f"Expected bear regime, got {regime}"

def test_r2_detect_regime_sideways():
    """R2: detect_regime returns bear/sideways in flat momentum (4-regime system)."""
    from src.core.strategy_engine import HybridStrategyEngine
    engine = HybridStrategyEngine()
    bars = generate_mock_bars(250, trend="flat")
    
    regime = engine.detect_regime(bars)
    assert regime in ("weak_bear", "weak_bull"), f"Expected neutral regime, got {regime}"

def test_r2_bull_weight_adaptation():
    """R2: technical weight adapts upwards when 'bull' market regime is detected."""
    from src.core.strategy_engine import HybridStrategyEngine
    engine = HybridStrategyEngine(technical_weight=0.2)
    bars = generate_mock_bars(250, trend="bull")
    
    # Perform regime check & adaptation
    engine.detect_regime(bars)
    assert engine.technical_weight > 0.2

def test_r2_bear_sell_threshold():
    """R2: bear market regime decreases sell_threshold below 0.45 to trigger sell orders faster."""
    from src.core.strategy_engine import HybridStrategyEngine
    engine = HybridStrategyEngine(sell_threshold=0.45)
    bars = generate_mock_bars(250, trend="bear")
    
    engine.detect_regime(bars)
    assert engine.sell_threshold < 0.45


# F3: Trailing Stop (R3)
def test_r3_no_stop_loss_trigger():
    """R3: watermark/drawdown check does not trigger stop if loss is within ATR limits."""
    from trading_system import StockTradingSystem
    system = StockTradingSystem(initial_cash=1000000)
    
    # Set active position mock properties: entry=100, ATR=2, highest=115, current=112
    # Drawdown is 3 (115 - 112) < 2 * ATR (4).
    system.portfolio.add_position("AAPL", 100, 100.0)
    system.portfolio.positions["AAPL"].highest_price = 115.0
    
    signal = system._check_trailing_stop("AAPL", 112.0, atr=2.0)
    assert signal is None

def test_r3_stop_loss_trigger():
    """R3: trailing stop triggers SELL signal when drawdown exceeds ATR threshold."""
    from trading_system import StockTradingSystem
    from src.core.strategy_engine import TradeSignal
    system = StockTradingSystem(initial_cash=1000000)
    
    # entry=100, highest=115, current=106, ATR=2. Drawdown is 9 >= 2 * ATR (4).
    system.portfolio.add_position("AAPL", 100, 100.0)
    system.portfolio.positions["AAPL"].highest_price = 115.0
    
    signal = system._check_trailing_stop("AAPL", 106.0, atr=2.0)
    assert signal == TradeSignal.SELL

def test_r3_high_watermark_update():
    """R3: watermark updates when price hits new highs."""
    from trading_system import StockTradingSystem
    system = StockTradingSystem(initial_cash=1000000)
    
    system.portfolio.add_position("AAPL", 100, 100.0)
    
    # Price rises 100 -> 110 -> 120
    system._check_trailing_stop("AAPL", 110.0, atr=2.0)
    assert system.portfolio.positions["AAPL"].highest_price == 110.0
    
    system._check_trailing_stop("AAPL", 120.0, atr=2.0)
    assert system.portfolio.positions["AAPL"].highest_price == 120.0

def test_r3_multiple_symbols_stop():
    """R3: system tracks watermarks and trailing stops independently for multiple symbols."""
    from trading_system import StockTradingSystem
    from src.core.strategy_engine import TradeSignal
    system = StockTradingSystem(initial_cash=1000000)
    
    system.portfolio.add_position("AAPL", 100, 100.0)
    system.portfolio.add_position("MSFT", 100, 200.0)
    
    # AAPL rises to 110 (watermark AAPL = 110)
    system._check_trailing_stop("AAPL", 110.0, atr=2.0)
    # MSFT falls to 190 (watermark MSFT = 200)
    system._check_trailing_stop("MSFT", 190.0, atr=2.0)
    
    assert system.portfolio.positions["AAPL"].highest_price == 110.0
    assert system.portfolio.positions["MSFT"].highest_price == 200.0
    
    # AAPL drops to 105 (no trigger, drawdown 5 < 2*ATR=4) - wait, drawdown 5 >= 4!
    # Let's say ATR is 3 (2*ATR = 6). Drawdown 5 < 6.
    sig_aapl = system._check_trailing_stop("AAPL", 106.0, atr=3.0)
    # MSFT drops to 190 (drawdown 10 >= 2*ATR=8, trigger)
    sig_msft = system._check_trailing_stop("MSFT", 190.0, atr=4.0)
    
    assert sig_aapl is None
    assert sig_msft == TradeSignal.SELL

def test_r3_stop_loss_after_rebound():
    """R3: stop loss triggers correctly after a rebound and subsequent drop."""
    from trading_system import StockTradingSystem
    from src.core.strategy_engine import TradeSignal
    system = StockTradingSystem(initial_cash=1000000)
    system.portfolio.add_position("AAPL", 100, 100.0)
    
    # Rise to 110
    system._check_trailing_stop("AAPL", 110.0, atr=2.0)
    # Rebound slightly to 108 (no trigger)
    assert system._check_trailing_stop("AAPL", 108.0, atr=2.0) is None
    # Rise to 120 (new watermark)
    system._check_trailing_stop("AAPL", 120.0, atr=2.0)
    assert system.portfolio.positions["AAPL"].highest_price == 120.0
    # Drop to 115 (triggers, drawdown 5 >= 2*ATR=4)
    assert system._check_trailing_stop("AAPL", 115.0, atr=2.0) == TradeSignal.SELL


# F4: Stock Screener (R4)
def test_r4_screener_dummy_conditions():
    """R4: screen with relaxed conditions returns whole universe."""
    from src.analysis.screener import StockScreener
    screener = StockScreener(min_volume=0, min_rsi=0, max_rsi=100)
    universe = ["AAPL", "MSFT", "GOOG"]
    
    selected = screener.screen(universe)
    assert set(selected) == set(universe)

def test_r4_screener_config_load():
    """R4: screener loads configuration constraints correctly."""
    from src.analysis.screener import StockScreener
    # Create temp config
    config_path = "screener_config.json"
    with open(config_path, "w") as f:
        json.dump({"min_volume": 500000, "min_rsi": 30, "max_rsi": 70}, f)
        
    try:
        screener = StockScreener(config_path=config_path)
        assert screener.min_volume == 500000
        assert screener.min_rsi == 30
    finally:
        if os.path.exists(config_path):
            os.remove(config_path)

def test_r4_screener_rsi_filter():
    """R4: filters out stocks outside the configured RSI bounds."""
    from src.analysis.screener import StockScreener
    screener = StockScreener(min_rsi=30, max_rsi=70)
    
    # We will mock yfinance to return high RSI for MSFT (e.g. 80) and normal for AAPL (50)
    # This mock handles internal screener calls.
    with patch.object(screener, "_calculate_rsi", side_effect=lambda sym: 80.0 if sym == "MSFT" else 50.0):
        selected = screener.screen(["AAPL", "MSFT"])
        assert "AAPL" in selected
        assert "MSFT" not in selected

def test_r4_screener_volume_filter():
    """R4: filters out stocks with volume below threshold."""
    from src.analysis.screener import StockScreener
    screener = StockScreener(min_volume=1000000)
    
    with patch.object(screener, "_get_average_volume", side_effect=lambda sym: 500000 if sym == "MSFT" else 2000000):
        selected = screener.screen(["AAPL", "MSFT"])
        assert "AAPL" in selected
        assert "MSFT" not in selected

def test_r4_screener_52week_filter():
    """R4: filters out stocks too far from 52-week high."""
    from src.analysis.screener import StockScreener
    screener = StockScreener(max_distance_from_high=0.10) # max 10% below high
    
    # AAPL: current=95, high=100 (5% below, keep)
    # MSFT: current=80, high=100 (20% below, filter out)
    def mock_prices(sym):
        if sym == "AAPL":
            return {"current": 95.0, "52week_high": 100.0}
        return {"current": 80.0, "52week_high": 100.0}
        
    with patch.object(screener, "_get_52week_prices", side_effect=mock_prices):
        selected = screener.screen(["AAPL", "MSFT"])
        assert "AAPL" in selected
        assert "MSFT" not in selected


# F5: Dash Dashboard (R5)
def test_r5_dashboard_server_instance():
    """R5: dashboard exposes app.server Flask instance."""
    from src.web.dashboard import app
    import flask
    assert hasattr(app, "server")
    assert isinstance(app.server, flask.Flask)

def test_r5_dashboard_layout_tabs():
    """R5: dashboard layout contains the 3 required tabs."""
    from src.web.dashboard import app
    layout = app.layout
    # Search layout for Tab IDs
    layout_str = str(layout)
    assert "performance-tab" in layout_str or "Strategy Performance" in layout_str
    assert "pnl-tab" in layout_str or "Real-time" in layout_str
    assert "backtest-tab" in layout_str or "Backtest" in layout_str

def test_r5_dashboard_performance_tab_components():
    """R5: performance tab contains comparison Chart/Graph."""
    from src.web.dashboard import app
    layout_str = str(app.layout)
    # Must contain Graph or Chart component
    assert "Graph" in layout_str
    assert "performance-comparison-chart" in layout_str

def test_r5_dashboard_pnl_tab_components():
    """R5: P&L tab contains portfolio DataTable or HTML Table."""
    from src.web.dashboard import app
    layout_str = str(app.layout)
    assert "DataTable" in layout_str or "pnl-status-table" in layout_str

def test_r5_dashboard_backtest_viewer_components():
    """R5: backtest viewer tab contains symbol selection dropdown and interactive curve chart."""
    from src.web.dashboard import app
    layout_str = str(app.layout)
    assert "Dropdown" in layout_str
    assert "backtest-symbol-dropdown" in layout_str
    assert "backtest-curve-chart" in layout_str


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (25 Tests)
# ==============================================================================

# F1: Parameter Optimization
def test_r1_empty_price_bars():
    """R1 boundary: empty bars list raises ValueError."""
    from src.analysis.backtest import BacktestEngine
    engine = BacktestEngine(initial_capital=1000000)
    with pytest.raises(ValueError):
        engine.optimize_parameters("AAPL", [], {"short_window": [10]})

def test_r1_single_price_bar():
    """R1 boundary: handles single price bar gracefully by returning defaults."""
    from src.analysis.backtest import BacktestEngine
    engine = BacktestEngine(initial_capital=1000000)
    bars = generate_mock_bars(1)
    
    result = engine.optimize_parameters("AAPL", bars, {"short_window": [5]})
    assert result["best_params"] is not None

def test_r1_invalid_param_ranges():
    """R1 boundary: empty ranges dict defaults to standard configurations."""
    from src.analysis.backtest import BacktestEngine
    engine = BacktestEngine(initial_capital=1000000)
    bars = generate_mock_bars(10)
    
    result = engine.optimize_parameters("AAPL", bars, {})
    assert "best_params" in result
    assert len(result["best_params"]) > 0

def test_r1_missing_json_directory():
    """R1 boundary: saves JSON successfully even if data/ directory does not exist."""
    from src.analysis.backtest import BacktestEngine
    engine = BacktestEngine(initial_capital=1000000)
    bars = generate_mock_bars(10)
    
    import shutil
    if os.path.exists("data"):
        # Temporary rename
        shutil.move("data", "data_temp_backup")
        
    try:
        engine.optimize_parameters("AAPL", bars, {"short_window": [5]}, strategy_name="MA")
        assert os.path.exists("data/optimized_params.json")
    finally:
        if os.path.exists("data_temp_backup"):
            if os.path.exists("data"):
                shutil.rmtree("data")
            shutil.move("data_temp_backup", "data")

def test_r1_extreme_parameters():
    """R1 boundary: large or negative parameter limits do not raise division by zero."""
    from src.analysis.backtest import BacktestEngine
    engine = BacktestEngine(initial_capital=1000000)
    bars = generate_mock_bars(20)
    
    # Pass negative window parameters, should handle or filter out gracefully
    result = engine.optimize_parameters("AAPL", bars, {"short_window": [-5, 5000]})
    assert result["best_params"] is not None


# F2: Market Regime & Strategy Switching
def test_r2_detect_regime_insufficient_bars():
    """R2 boundary: fallback to 'weak_bear' when bars count is less than 200."""
    from src.core.strategy_engine import HybridStrategyEngine
    engine = HybridStrategyEngine()
    bars = generate_mock_bars(50, trend="bull") # Less than 200
    
    regime = engine.detect_regime(bars)
    assert regime == "weak_bear"

def test_r2_detect_regime_constant_price():
    """R2 boundary: constant price data handles ROC/ATR calculations without division-by-zero."""
    from src.core.strategy_engine import HybridStrategyEngine
    engine = HybridStrategyEngine()
    
    # Generate flat bars where high=low=close=open
    bars = []
    current_time = datetime.now()
    for i in range(250):
        bars.append(MockPriceBar(current_time + timedelta(days=i), 100.0, 100.0, 100.0, 100.0, 1000000))
        
    regime = engine.detect_regime(bars)
    assert regime in ("weak_bear", "weak_bull"), f"Expected neutral regime, got {regime}"

def test_r2_detect_regime_missing_fields():
    """R2 boundary: bars missing crucial high/low fields raise ValueError."""
    from src.core.strategy_engine import HybridStrategyEngine
    engine = HybridStrategyEngine()
    
    # Bar without low/high
    bars = [MockPriceBar(datetime.now(), 100.0, None, None, 100.0, 1000000)]
    with pytest.raises(ValueError):
        engine.detect_regime(bars)

def test_r2_weight_adaptation_bounds():
    """R2 boundary: dynamic weights stay within [0.0, 1.0] and sum to exactly 1.0 after normalization."""
    from src.core.strategy_engine import HybridStrategyEngine
    engine = HybridStrategyEngine(
        sentiment_weight=9.0, # Initial out of bounds
        technical_weight=1.0,
        ml_weight=0.0,
        rl_weight=0.0,
        darkpool_weight=0.0,
        llm_weight=0.0,
        global_market_weight=0.0,
        cash_ratio_weight=0.0,
        macro_weight=0.0
    )
    # Trigger normalization/regime adaptation
    bars = generate_mock_bars(250, trend="bull")
    engine.detect_regime(bars)
    
    weights = [
        engine.sentiment_weight, engine.technical_weight, engine.ml_weight,
        engine.rl_weight, engine.darkpool_weight, engine.llm_weight
    ]
    for w in weights:
        assert 0.0 <= w <= 1.0
    assert abs(sum(weights) - 1.0) < 1e-6

def test_r2_extreme_regime_transition():
    """R2 boundary: instant switch from bull trend to bear trend updates regime immediately."""
    from src.core.strategy_engine import HybridStrategyEngine
    engine = HybridStrategyEngine()
    
    # 200 bull bars followed by 200 bear bars
    bars = generate_mock_bars(200, trend="bull") + generate_mock_bars(200, trend="bear")
    regime = engine.detect_regime(bars)
    assert regime in ("strong_bear", "weak_bear") # Last trend dominates


# F3: Trailing Stop
def test_r3_atr_zero():
    """R3 boundary: ATR=0 is handled gracefully (defaults to no trailing stop or fixed stop)."""
    from trading_system import StockTradingSystem
    system = StockTradingSystem(initial_cash=1000000)
    system.portfolio.add_position("AAPL", 100, 100.0)
    system.portfolio.positions["AAPL"].highest_price = 110.0
    
    # ATR = 0
    signal = system._check_trailing_stop("AAPL", 105.0, atr=0.0)
    assert signal is None

def test_r3_price_zero():
    """R3 boundary: current price of 0 triggers trailing stop immediately."""
    from trading_system import StockTradingSystem
    from src.core.strategy_engine import TradeSignal
    system = StockTradingSystem(initial_cash=1000000)
    system.portfolio.add_position("AAPL", 100, 100.0)
    system.portfolio.positions["AAPL"].highest_price = 100.0
    
    signal = system._check_trailing_stop("AAPL", 0.0, atr=2.0)
    assert signal == TradeSignal.SELL

def test_r3_no_active_position():
    """R3 boundary: check trailing stop for non-existent holding returns None."""
    from trading_system import StockTradingSystem
    system = StockTradingSystem(initial_cash=1000000)
    
    signal = system._check_trailing_stop("AAPL", 150.0, atr=2.0)
    assert signal is None

def test_r3_high_watermark_lower_than_entry():
    """R3 boundary: high watermark is initialized to entry price if market immediately falls."""
    from trading_system import StockTradingSystem
    system = StockTradingSystem(initial_cash=1000000)
    
    # Entry price 100. Immediate drop to 95. Watermark should be 100.
    system.portfolio.add_position("AAPL", 100, 100.0)
    system._check_trailing_stop("AAPL", 95.0, atr=2.0)
    
    assert system.portfolio.positions["AAPL"].highest_price == 100.0

def test_r3_atr_extreme_large():
    """R3 boundary: extremely high ATR value makes stop loss boundary mathematically unreachable."""
    from trading_system import StockTradingSystem
    system = StockTradingSystem(initial_cash=1000000)
    system.portfolio.add_position("AAPL", 100, 100.0)
    system.portfolio.positions["AAPL"].highest_price = 110.0
    
    # ATR is extremely large (e.g. 1000). Drawdown limit is 2 * 1000 = 2000. Price drop to 50 is safe.
    signal = system._check_trailing_stop("AAPL", 50.0, atr=1000.0)
    assert signal is None


# F4: Stock Screener
def test_r4_screener_empty_universe():
    """R4 boundary: screening an empty universe returns an empty list without crashing."""
    from src.analysis.screener import StockScreener
    screener = StockScreener(min_volume=100)
    assert screener.screen([]) == []

def test_r4_screener_missing_config():
    """R4 boundary: missing config path triggers default safe fallback limits."""
    from src.analysis.screener import StockScreener
    screener = StockScreener(config_path="non_existent_config.json")
    assert screener.min_volume > 0

def test_r4_screener_malformed_config():
    """R4 boundary: malformed JSON config raises ValueError."""
    from src.analysis.screener import StockScreener
    config_path = "malformed_config.json"
    with open(config_path, "w") as f:
        f.write("{invalid_json:")
        
    try:
        with pytest.raises(ValueError):
            StockScreener(config_path=config_path)
    finally:
        if os.path.exists(config_path):
            os.remove(config_path)

def test_r4_screener_yfinance_failure():
    """R4 boundary: screener skips symbols that raise yfinance errors instead of crashing."""
    from src.analysis.screener import StockScreener
    screener = StockScreener()
    
    # Mock yfinance to fail on MSFT
    def mock_fetch(symbol):
        if symbol == "MSFT":
            raise Exception("yfinance error")
        return MagicMock()
        
    with patch("yfinance.Ticker", side_effect=mock_fetch):
        selected = screener.screen(["AAPL", "MSFT"])
        assert "AAPL" in selected
        assert "MSFT" not in selected

def test_r4_screener_duplicate_symbols():
    """R4 boundary: universe with duplicates returns only unique selected symbols."""
    from src.analysis.screener import StockScreener
    screener = StockScreener(min_volume=0, min_rsi=0, max_rsi=100)
    
    selected = screener.screen(["AAPL", "AAPL", "MSFT", "MSFT"])
    assert len(selected) == len(set(selected))


# F5: Dash Dashboard
def test_r5_dashboard_callback_missing_inputs():
    """R5 boundary: update callbacks handle None dropdown inputs gracefully."""
    from src.web.dashboard import update_backtest_chart
    # Call callback with None input, should return empty figure dict instead of raising Exception
    fig = update_backtest_chart(None, None)
    assert isinstance(fig, dict)
    assert "data" in fig

def test_r5_dashboard_empty_positions_table():
    """R5 boundary: empty positions portfolio returns a row indicating no active holdings."""
    from src.web.dashboard import update_positions_table
    rows = update_positions_table([])
    assert len(rows) == 1
    assert "No active positions" in str(rows[0])

def test_r5_dashboard_missing_performance_data():
    """R5 boundary: dashboard comparison handles strategies with missing data gracefully."""
    from src.web.dashboard import update_performance_comparison
    # Pass empty performance dict, should return layout without throwing errors
    fig = update_performance_comparison({})
    assert isinstance(fig, dict)

def test_r5_dashboard_server_port_collision():
    """R5 boundary: web dashboard configuration permits custom port binding to resolve collisions."""
    from src.web.dashboard import DashboardServer
    server = DashboardServer(port=8888)
    assert server.port == 8888

def test_r5_dashboard_concurrent_connections():
    """R5 boundary: verify dashboard callbacks remain stateless under concurrent invocations."""
    from src.web.dashboard import update_backtest_chart
    # Consecutive calls with different symbols return distinct figures without cross-talk
    fig_aapl = update_backtest_chart("AAPL", "MA")
    fig_msft = update_backtest_chart("MSFT", "RSI")
    
    assert fig_aapl != fig_msft


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (5 Tests)
# ==============================================================================

def test_r1_r2_combination():
    """F1 + F2: optimization parameters are cached, and regime switching adapts weights properly in tandem."""
    from src.analysis.backtest import BacktestEngine
    from src.core.strategy_engine import HybridStrategyEngine
    
    engine_opt = BacktestEngine()
    engine_reg = HybridStrategyEngine()
    bars = generate_mock_bars(250, trend="bull")
    
    # Optimize parameters
    opt_result = engine_opt.optimize_parameters("AAPL", bars, {"short_window": [10, 20]}, strategy_name="MA")
    best_short = opt_result["best_params"]["short_window"]
    
    # Use best parameters inside strategy engine regime check
    engine_reg.set_strategy_parameters("MA", {"short_window": best_short})
    regime = engine_reg.detect_regime(bars)
    
    assert regime in ("strong_bull", "weak_bull")
    assert engine_reg.technical_weight > 0.2

def test_r2_r3_combination():
    """F2 + F3: bear regime switches sell_threshold lower, interacting with trailing stop to exit safely."""
    from trading_system import StockTradingSystem
    from src.core.strategy_engine import TradeSignal
    system = StockTradingSystem(initial_cash=1000000)
    
    # 1. Bear market regime detected -> adjusts system strategy Engine sell_threshold
    bear_bars = generate_mock_bars(250, trend="bear")
    system.strategy_engine.detect_regime(bear_bars)
    
    # 2. Assert lower threshold (e.g. sell_threshold < 0.45)
    assert system.strategy_engine.sell_threshold < 0.45
    
    # 3. Trailing stop check matches or triggers exit order due to tight thresholds
    system.portfolio.add_position("AAPL", 100, 100.0)
    system.portfolio.positions["AAPL"].highest_price = 102.0
    
    # Even a small drop triggers sell signal due to combined bear regime constraints
    signal = system._check_trailing_stop("AAPL", 99.0, atr=1.0)
    assert signal == TradeSignal.SELL

def test_r3_r4_combination():
    """F3 + F4: screener filters stock list, which is then traded, tracking trailing stops independently."""
    from src.analysis.screener import StockScreener
    from trading_system import StockTradingSystem
    from src.core.strategy_engine import TradeSignal
    
    screener = StockScreener(min_volume=100000)
    system = StockTradingSystem()
    
    # 1. Screen universe
    selected = screener.screen(["AAPL", "MSFT"])
    assert len(selected) > 0
    
    # 2. Buy screened stocks
    for sym in selected:
        system.portfolio.add_position(sym, 10, 100.0)
        
    # 3. Check stop loss updates
    for sym in selected:
        sig = system._check_trailing_stop(sym, 90.0, atr=2.0)
        assert sig == TradeSignal.SELL

def test_r4_r1_combination():
    """F4 + F1: screener filters candidate universe, and optimization runs specifically on those candidates."""
    from src.analysis.screener import StockScreener
    from src.analysis.backtest import BacktestEngine
    
    screener = StockScreener(min_volume=1000000)
    engine = BacktestEngine()
    bars = generate_mock_bars(50)
    
    candidates = screener.screen(["AAPL", "MSFT"])
    
    # Run optimization on selected candidates
    for sym in candidates:
        res = engine.optimize_parameters(sym, bars, {"short_window": [10]}, strategy_name="MA")
        assert "best_params" in res

def test_r1_r5_combination():
    """F1 + F5: optimized parameter caching output is rendered inside the Dash Dashboard."""
    from src.analysis.backtest import BacktestEngine
    from src.web.dashboard import app
    
    engine = BacktestEngine()
    bars = generate_mock_bars(50)
    
    # Run and cache optimization
    engine.optimize_parameters("AAPL", bars, {"short_window": [12]}, strategy_name="MA")
    
    # Dashboard loads cache structure
    layout_str = str(app.layout)
    assert "optimized-cache-viewer" in layout_str


# ==============================================================================
# TIER 4: REAL-WORLD WORKLOADS (5 Tests)
# ==============================================================================

def test_tier4_full_regime_cycle_workload():
    """Tier 4: simulates full market regime lifecycle updates (Bull -> Bear -> Sideways)."""
    from src.core.strategy_engine import HybridStrategyEngine
    engine = HybridStrategyEngine()
    
    # Bull phase
    bull_bars = generate_mock_bars(250, trend="bull")
    regime = engine.detect_regime(bull_bars)
    assert regime in ("strong_bull", "weak_bull")
    w_bull = engine.technical_weight
    
    # Transition to Bear phase
    bear_bars = generate_mock_bars(250, trend="bear")
    regime = engine.detect_regime(bear_bars)
    assert regime in ("strong_bear", "weak_bear")
    w_bear = engine.technical_weight
    
    # Transition to Sideways
    flat_bars = generate_mock_bars(250, trend="flat")
    regime = engine.detect_regime(flat_bars)
    assert regime in ("weak_bear", "weak_bull"), f"Expected neutral regime, got {regime}"
    
    assert w_bull != w_bear

def test_tier4_screener_to_portfolio_optimization():
    """Tier 4: end-to-end workflow covering Screener -> Optimization -> Trading -> Trailing Stop checks."""
    from src.analysis.screener import StockScreener
    from src.analysis.backtest import BacktestEngine
    from trading_system import StockTradingSystem
    
    # 1. Screen
    screener = StockScreener(min_volume=500000)
    selected = screener.screen(["AAPL", "MSFT"])
    assert "AAPL" in selected
    
    # 2. Optimize
    engine = BacktestEngine()
    bars = generate_mock_bars(100)
    opt_res = engine.optimize_parameters("AAPL", bars, {"short_window": [10, 15]}, strategy_name="MA")
    best_short = opt_res["best_params"]["short_window"]
    
    # 3. Trade
    system = StockTradingSystem()
    system.portfolio.add_position("AAPL", 100, 150.0)
    
    # 4. Trailing stop checks
    sig = system._check_trailing_stop("AAPL", 140.0, atr=2.0)
    assert sig is not None # Expecting exit signal due to drop

def test_tier4_multi_strategy_dashboard_sync():
    """Tier 4: simulates parallel backtesting of multiple strategies and writing performance curves to JSON."""
    from src.analysis.backtest import BacktestEngine
    import concurrent.futures
    
    engine = BacktestEngine()
    bars = generate_mock_bars(100)
    
    strategies = ["MA", "RSI", "MACD", "Ensemble"]
    results = {}
    
    # Run backtests in parallel threadpool
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(engine.run_backtest, "AAPL", bars, engine.get_strategy_func(s)): s for s in strategies}
        for fut in concurrent.futures.as_completed(futures):
            strat = futures[fut]
            results[strat] = fut.result().equity_curve
            
    # Save results to a comparison cache file
    with open("data/strategy_comparison.json", "w") as f:
        json.dump(results, f)
        
    assert os.path.exists("data/strategy_comparison.json")
    os.remove("data/strategy_comparison.json")

def test_tier4_volatile_market_trailing_stop_onslaught():
    """Tier 4: verify trailing stop handles highly volatile feeds with large ATR peaks correctly."""
    from trading_system import StockTradingSystem
    system = StockTradingSystem()
    system.portfolio.add_position("AAPL", 100, 100.0)
    
    # Price whipsaws: 100 -> 110 -> 95 -> 120 -> 100
    # At price 110, watermark becomes 110. Drop to 95 triggers stop (drawdown 15 > 2*ATR=8)
    system._check_trailing_stop("AAPL", 110.0, atr=4.0)
    sig1 = system._check_trailing_stop("AAPL", 95.0, atr=4.0)
    assert sig1 == "SELL" # Triggered
    
    # Re-enter
    system.portfolio.add_position("AAPL", 100, 95.0)
    system.portfolio.positions["AAPL"].highest_price = 120.0
    
    # High volatility peak. Large ATR (e.g. ATR=15, drawdown limit = 30).
    # Current price drops from 120 watermark to 100 (drawdown 20 < 30). Should NOT trigger.
    sig2 = system._check_trailing_stop("AAPL", 100.0, atr=15.0)
    assert sig2 is None

def test_tier4_end_to_end_trading_session():
    """Tier 4: sets up complete StockTradingSystem with R1-R5 components active for a full simulated session."""
    from trading_system import StockTradingSystem
    from src.analysis.screener import StockScreener
    from src.core.strategy_engine import TradeSignal
    
    # 1. Initialize complete system
    system = StockTradingSystem()
    screener = StockScreener()
    
    # 2. Run daily scan
    selected = screener.screen(["AAPL", "MSFT"])
    assert "AAPL" in selected
    
    # 3. Simulate news sentiment processing
    system.nlp_engine.process_news("AAPL product launch success", "AAPL shows amazing sales numbers", "AAPL")
    assert system.news_sentiment_cache["AAPL"] > 0.0
    
    # 4. Generate signals
    bars = generate_mock_bars(200, trend="bull")
    # Simulate a market regime transition and strategy update
    system.strategy_engine.detect_regime(bars)
    
    # 5. Evaluate trailing stops
    system.portfolio.add_position("AAPL", 10, 150.0)
    sig = system._check_trailing_stop("AAPL", 142.0, atr=3.0) # Drawdown 8 >= 6
    assert sig == TradeSignal.SELL
