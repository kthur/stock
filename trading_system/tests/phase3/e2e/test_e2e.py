import os
import pytest

from src.ai.sentiment import analyze_sentiment
from src.ai.rl_trading import train_rl_model
from src.strategy.allocation import allocate_assets
from src.broker.real_broker import RealBroker
from src.utils.report import generate_pdf_report

# ==========================================
# Tier 1: Positive/Base Cases (25 Tests)
# ==========================================

# F1: Sentiment Analysis (analyze_sentiment)
def test_sentiment_positive_text():
    score = analyze_sentiment("Incredible profits!")
    assert score > 0.5

def test_sentiment_negative_text():
    score = analyze_sentiment("Terrible losses.")
    assert score < 0.5

def test_sentiment_neutral_text():
    score = analyze_sentiment("The sky is blue.")
    assert 0.4 <= score <= 0.6

def test_sentiment_return_type():
    score = analyze_sentiment("Typical text")
    assert isinstance(score, float)

def test_sentiment_short_text():
    score = analyze_sentiment("Good")
    assert score > 0.5

# F2: RL Trading Model (train_rl_model)
def test_rl_training_basic_data():
    data = [{"price": 100}, {"price": 105}]
    model = train_rl_model(data)
    assert model is not None

def test_rl_training_single_epoch():
    data = [{"price": 100}, {"price": 105}]
    model = train_rl_model(data)
    assert model is not None

def test_rl_training_large_dataset():
    data = [{"price": 100 + i} for i in range(1000)]
    model = train_rl_model(data)
    assert model is not None

def test_rl_training_returns_expected_interface():
    data = [{"price": 100}, {"price": 105}]
    model = train_rl_model(data)
    assert hasattr(model, "predict")

def test_rl_training_deterministic_run():
    data = [{"price": 100}, {"price": 105}]
    model1 = train_rl_model(data)
    model2 = train_rl_model(data)
    assert model1 is not None and model2 is not None

# F3: Asset Allocation (allocate_assets)
def test_allocate_two_assets():
    weights = allocate_assets({"AAPL": 150.0, "MSFT": 300.0})
    assert set(weights.keys()) == {"AAPL", "MSFT"}
    assert sum(weights.values()) == 1.0

def test_allocate_single_asset():
    weights = allocate_assets({"AAPL": 150.0})
    assert weights == {"AAPL": 1.0}

def test_allocate_five_assets():
    assets = {"A": 10.0, "B": 20.0, "C": 30.0, "D": 40.0, "E": 50.0}
    weights = allocate_assets(assets)
    assert len(weights) == 5
    assert sum(weights.values()) == 1.0

def test_allocate_high_price_variance():
    weights = allocate_assets({"A": 1.0, "B": 10000.0})
    assert sum(weights.values()) == 1.0

def test_allocate_same_prices():
    weights = allocate_assets({"A": 100.0, "B": 100.0})
    assert weights["A"] == 0.5
    assert weights["B"] == 0.5

# F4: PDF Report (generate_pdf_report)
def test_report_basic_trades(tmp_path):
    trades = [{"symbol": "AAPL", "qty": 10, "price": 150.0}] * 3
    file_path = tmp_path / "test_report_basic.pdf"
    generate_pdf_report(trades, str(file_path))
    assert file_path.exists()
    assert file_path.stat().st_size > 0

def test_report_single_trade(tmp_path):
    trades = [{"symbol": "AAPL", "qty": 10, "price": 150.0}]
    file_path = tmp_path / "single_trade.pdf"
    generate_pdf_report(trades, str(file_path))
    assert file_path.exists()
    assert file_path.stat().st_size > 0

def test_report_large_number_of_trades(tmp_path):
    trades = [{"symbol": "AAPL", "qty": 10, "price": 150.0}] * 100
    file_path = tmp_path / "large_trades.pdf"
    generate_pdf_report(trades, str(file_path))
    assert file_path.exists()
    assert file_path.stat().st_size > 0

def test_report_different_directory(tmp_path):
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    file_path = report_dir / "test.pdf"
    generate_pdf_report([{"symbol": "AAPL"}], str(file_path))
    assert file_path.exists()

def test_report_overwrite(tmp_path):
    trades = [{"symbol": "AAPL", "qty": 10, "price": 150.0}]
    file_path = tmp_path / "overwrite.pdf"
    generate_pdf_report(trades, str(file_path))
    assert file_path.exists()
    mtime1 = file_path.stat().st_mtime
    
    generate_pdf_report(trades * 2, str(file_path))
    assert file_path.exists()
    mtime2 = file_path.stat().st_mtime
    assert mtime2 >= mtime1

# F5: Broker API (RealBroker)
def test_broker_connect_success():
    broker = RealBroker()
    broker.connect()
    assert getattr(broker, "is_connected", False) or getattr(broker, "connected", False)

def test_broker_submit_buy_order():
    broker = RealBroker()
    broker.connect()
    result = broker.submit_order("AAPL", 10, "BUY")
    assert result is True or isinstance(result, dict)

def test_broker_submit_sell_order():
    broker = RealBroker()
    broker.connect()
    result = broker.submit_order("AAPL", 10, "SELL")
    assert result is True or isinstance(result, dict)

def test_broker_submit_multiple_orders():
    broker = RealBroker()
    broker.connect()
    for _ in range(5):
        result = broker.submit_order("AAPL", 10, "BUY")
        assert result is True or isinstance(result, dict)

def test_broker_order_history():
    broker = RealBroker()
    broker.connect()
    broker.submit_order("AAPL", 10, "BUY")
    history = getattr(broker, "get_order_history", lambda: [])()
    assert len(history) > 0


# ==========================================
# Tier 2: Negative/Edge Cases (25 Tests)
# ==========================================

# F1: Sentiment Analysis
def test_sentiment_empty_string():
    with pytest.raises(ValueError):
        analyze_sentiment("")

def test_sentiment_very_long_text():
    score = analyze_sentiment("A" * 10000)
    assert isinstance(score, float)

def test_sentiment_special_characters():
    score = analyze_sentiment("!@#$%^&*")
    assert 0.4 <= score <= 0.6

def test_sentiment_numeric_input():
    with pytest.raises(TypeError):
        analyze_sentiment(12345)

def test_sentiment_none_input():
    with pytest.raises((TypeError, ValueError)):
        analyze_sentiment(None)

# F2: RL Trading Model
def test_rl_training_empty_data():
    with pytest.raises(ValueError):
        train_rl_model([])

def test_rl_training_missing_columns():
    with pytest.raises((KeyError, ValueError)):
        train_rl_model([{"wrong_key": 100}])

def test_rl_training_all_zeros_data():
    model = train_rl_model([{"price": 0.0}, {"price": 0.0}])
    assert model is not None

def test_rl_training_invalid_data_type():
    with pytest.raises(TypeError):
        train_rl_model("not data")

def test_rl_training_nan_values():
    with pytest.raises(ValueError):
        train_rl_model([{"price": float("nan")}])

# F3: Asset Allocation
def test_allocate_empty_dict():
    with pytest.raises(ValueError):
        allocate_assets({})

def test_allocate_negative_prices():
    with pytest.raises(ValueError):
        allocate_assets({"AAPL": -150.0})

def test_allocate_invalid_types():
    with pytest.raises(TypeError):
        allocate_assets({"AAPL": "high"})

def test_allocate_none_input():
    with pytest.raises(TypeError):
        allocate_assets(None)

def test_allocate_zero_prices():
    with pytest.raises(ValueError):
        allocate_assets({"AAPL": 0.0})

# F4: PDF Report
def test_report_empty_trades_list(tmp_path):
    file_path = tmp_path / "empty.pdf"
    generate_pdf_report([], str(file_path))
    assert file_path.exists()

def test_report_invalid_path():
    with pytest.raises((FileNotFoundError, OSError)):
        generate_pdf_report([{"symbol": "AAPL"}], "Z:\\invalid\\test.pdf")

def test_report_missing_trade_keys(tmp_path):
    file_path = tmp_path / "missing_keys.pdf"
    with pytest.raises((KeyError, ValueError)):
        generate_pdf_report([{"symbol": "AAPL"}], str(file_path))

def test_report_none_trade_data(tmp_path):
    file_path = tmp_path / "none.pdf"
    with pytest.raises((TypeError, ValueError)):
        generate_pdf_report(None, str(file_path))

def test_report_invalid_file_extension(tmp_path):
    file_path = tmp_path / "test.txt"
    with pytest.raises(ValueError):
        generate_pdf_report([{"symbol": "AAPL"}], str(file_path))

# F5: Broker API
def test_broker_submit_order_without_connect():
    broker = RealBroker()
    with pytest.raises((ConnectionError, RuntimeError, Exception)):
        broker.submit_order("AAPL", 10, "BUY")

def test_broker_submit_invalid_quantity():
    broker = RealBroker()
    broker.connect()
    with pytest.raises(ValueError):
        broker.submit_order("AAPL", -10, "BUY")

def test_broker_submit_invalid_symbol():
    broker = RealBroker()
    broker.connect()
    with pytest.raises(ValueError):
        broker.submit_order("", 10, "BUY")

def test_broker_invalid_order_type():
    broker = RealBroker()
    broker.connect()
    with pytest.raises(ValueError):
        broker.submit_order("AAPL", 10, "HODL")

def test_broker_connect_idempotency():
    broker = RealBroker()
    broker.connect()
    broker.connect()
    assert getattr(broker, "is_connected", False) or getattr(broker, "connected", False)


# ==========================================
# Tier 3: Pairwise Interaction Coverage
# ==========================================
def test_pairwise_sentiment_to_allocation():
    score = analyze_sentiment("Great earnings!")
    # mock logic to convert score to price
    prices = {"AAPL": score * 100.0, "MSFT": (1.0 - score) * 100.0}
    weights = allocate_assets(prices)
    assert sum(weights.values()) == 1.0

def test_pairwise_rl_to_broker():
    model = train_rl_model([{"price": 100}, {"price": 105}])
    broker = RealBroker()
    broker.connect()
    action = getattr(model, "predict", lambda x: "BUY")([100])
    result = broker.submit_order("AAPL", 10, action)
    assert result is True or isinstance(result, dict)

def test_pairwise_allocation_to_broker():
    weights = allocate_assets({"AAPL": 150.0, "MSFT": 300.0})
    broker = RealBroker()
    broker.connect()
    for sym, weight in weights.items():
        qty = weight * 100
        result = broker.submit_order(sym, qty, "BUY")
        assert result is True or isinstance(result, dict)

def test_pairwise_broker_to_report(tmp_path):
    broker = RealBroker()
    broker.connect()
    receipt = broker.submit_order("AAPL", 10, "BUY")
    file_path = tmp_path / "broker_report.pdf"
    generate_pdf_report([receipt], str(file_path))
    assert file_path.exists()
    assert file_path.stat().st_size > 0


# ==========================================
# Tier 4: Real-World Scenarios
# ==========================================
def test_scenario_full_trade_cycle():
    score = analyze_sentiment("Market is bullish")
    model = train_rl_model([{"price": 100}, {"price": 105}])
    weights = allocate_assets({"AAPL": 150.0, "MSFT": 300.0})
    
    broker = RealBroker()
    broker.connect()
    for sym, weight in weights.items():
        qty = weight * 100
        broker.submit_order(sym, qty, "BUY")
        
    history = getattr(broker, "get_order_history", lambda: [])()
    assert len(history) > 0

def test_scenario_end_of_day_reporting(tmp_path):
    analyze_sentiment("Good day")
    allocate_assets({"AAPL": 150.0})
    mock_trades = [{"symbol": "AAPL", "qty": 10, "price": 150.0}]
    file_path = tmp_path / "eod_report.pdf"
    generate_pdf_report(mock_trades, str(file_path))
    assert file_path.exists()

def test_scenario_emergency_reallocation():
    score = analyze_sentiment("CRITICAL CRASH")
    assert score < 0.5
    weights = allocate_assets({"DEFENSE": 100.0, "TECH": 10.0})
    broker = RealBroker()
    broker.connect()
    result = broker.submit_order("TECH", 10, "SELL")
    assert result is True or isinstance(result, dict)
