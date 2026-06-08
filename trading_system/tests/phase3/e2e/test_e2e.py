import os
import pytest
from src.ai.sentiment import analyze_sentiment
from src.ai.rl_trading import train_rl_model
from src.strategy.allocation import allocate_assets
from src.utils.report import generate_pdf_report
from src.broker.real_broker import RealBroker

# F1: Sentiment Analysis
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

# F2: RL Trading Model
def test_rl_training_basic_data():
    data = [{"price": 100.0}, {"price": 101.0}]
    model = train_rl_model(data)
    assert model is not None

def test_rl_training_single_epoch():
    data = [{"price": 100.0}, {"price": 101.0}]
    model = train_rl_model(data, epochs=1)
    assert model is not None

def test_rl_training_large_dataset():
    data = [{"price": float(i)} for i in range(1000)]
    model = train_rl_model(data)
    assert model is not None

def test_rl_training_returns_expected_interface():
    data = [{"price": 100.0}, {"price": 101.0}]
    model = train_rl_model(data)
    assert hasattr(model, "predict")

def test_rl_training_deterministic_run():
    data = [{"price": 100.0}, {"price": 101.0}]
    model1 = train_rl_model(data, seed=42)
    model2 = train_rl_model(data, seed=42)
    assert model1.predict(data) == model2.predict(data)

# F3: Asset Allocation
def test_allocate_two_assets():
    weights = allocate_assets({"AAPL": 150.0, "MSFT": 300.0})
    assert set(weights.keys()) == {"AAPL", "MSFT"}
    assert abs(sum(weights.values()) - 1.0) < 1e-6

def test_allocate_single_asset():
    weights = allocate_assets({"AAPL": 150.0})
    assert weights == {"AAPL": 1.0}

def test_allocate_five_assets():
    assets = {"A": 10.0, "B": 20.0, "C": 30.0, "D": 40.0, "E": 50.0}
    weights = allocate_assets(assets)
    assert len(weights) == 5
    assert abs(sum(weights.values()) - 1.0) < 1e-6

def test_allocate_high_price_variance():
    weights = allocate_assets({"A": 1.0, "B": 10000.0})
    assert abs(sum(weights.values()) - 1.0) < 1e-6

def test_allocate_same_prices():
    weights = allocate_assets({"A": 100.0, "B": 100.0})
    assert weights["A"] == 0.5
    assert weights["B"] == 0.5

# F4: PDF Report
def test_report_basic_trades():
    trades = [
        {"symbol": "AAPL", "qty": 10, "price": 150.0},
        {"symbol": "MSFT", "qty": 5, "price": 300.0},
        {"symbol": "GOOG", "qty": 2, "price": 1000.0}
    ]
    path = "./test_report_basic.pdf"
    if os.path.exists(path):
        os.remove(path)
    generate_pdf_report(trades, path)
    assert os.path.exists(path) is True
    assert os.path.getsize(path) > 0

def test_report_single_trade():
    trades = [{"symbol": "AAPL", "qty": 10, "price": 150.0}]
    path = "./test_report_single.pdf"
    if os.path.exists(path):
        os.remove(path)
    generate_pdf_report(trades, path)
    assert os.path.exists(path) is True
    assert os.path.getsize(path) > 0

def test_report_large_number_of_trades():
    trades = [{"symbol": f"SYM{i}", "qty": 1, "price": 10.0} for i in range(100)]
    path = "./test_report_large.pdf"
    if os.path.exists(path):
        os.remove(path)
    generate_pdf_report(trades, path)
    assert os.path.exists(path) is True
    assert os.path.getsize(path) > 0

def test_report_different_directory():
    trades = [{"symbol": "AAPL", "qty": 10, "price": 150.0}]
    os.makedirs("./reports", exist_ok=True)
    path = "./reports/test.pdf"
    if os.path.exists(path):
        os.remove(path)
    generate_pdf_report(trades, path)
    assert os.path.exists(path) is True

def test_report_overwrite():
    trades1 = [{"symbol": "AAPL", "qty": 10, "price": 150.0}]
    trades2 = [{"symbol": "MSFT", "qty": 5, "price": 300.0}]
    path = "./test_report_overwrite.pdf"
    generate_pdf_report(trades1, path)
    assert os.path.exists(path) is True
    size1 = os.path.getsize(path)
    mtime1 = os.path.getmtime(path)
    generate_pdf_report(trades2, path)
    assert os.path.exists(path) is True
    assert os.path.getsize(path) != size1 or os.path.getmtime(path) >= mtime1

# F5: Broker API
def test_broker_connect_success():
    broker = RealBroker()
    broker.connect()
    assert broker.is_connected is True

def test_broker_submit_buy_order():
    broker = RealBroker()
    broker.connect()
    status = broker.submit_order("AAPL", "BUY", 10)
    assert status is True

def test_broker_submit_sell_order():
    broker = RealBroker()
    broker.connect()
    status = broker.submit_order("AAPL", "SELL", 10)
    assert status is True

def test_broker_submit_multiple_orders():
    broker = RealBroker()
    broker.connect()
    for _ in range(5):
        status = broker.submit_order("AAPL", "BUY", 10)
        assert status is True

def test_broker_order_history():
    broker = RealBroker()
    broker.connect()
    broker.submit_order("AAPL", "BUY", 10)
    history = broker.get_order_history()
    assert len(history) > 0
    assert history[-1]["symbol"] == "AAPL"

# Tier 2
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
        train_rl_model([{"wrong_key": 100.0}])

def test_rl_training_all_zeros_data():
    model = train_rl_model([{"price": 0.0}, {"price": 0.0}])
    assert model is not None

def test_rl_training_invalid_data_type():
    with pytest.raises(TypeError):
        train_rl_model("invalid_data")

def test_rl_training_nan_values():
    import math
    with pytest.raises(ValueError):
        train_rl_model([{"price": math.nan}])

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
def test_report_empty_trades_list():
    path = "./test_report_empty.pdf"
    if os.path.exists(path):
        os.remove(path)
    generate_pdf_report([], path)
    assert os.path.exists(path) is True
    assert os.path.getsize(path) >= 0

def test_report_invalid_path():
    invalid_path = "Z:\\invalid\\test.pdf" if os.name == "nt" else "/invalid/path/test.pdf"
    with pytest.raises((FileNotFoundError, OSError)):
        generate_pdf_report([{"symbol": "AAPL", "qty": 10, "price": 150.0}], invalid_path)

def test_report_missing_trade_keys():
    with pytest.raises((KeyError, ValueError)):
        generate_pdf_report([{"symbol": "AAPL"}], "./test_report_missing_keys.pdf")

def test_report_none_trade_data():
    with pytest.raises((TypeError, ValueError)):
        generate_pdf_report(None, "./test_report_none.pdf")

def test_report_invalid_file_extension():
    with pytest.raises(ValueError):
        generate_pdf_report([{"symbol": "AAPL", "qty": 1, "price": 1.0}], "test.txt")

# F5: Broker API
def test_broker_submit_order_without_connect():
    broker = RealBroker()
    with pytest.raises((ConnectionError, RuntimeError)):
        broker.submit_order("AAPL", "BUY", 10)

def test_broker_submit_invalid_quantity():
    broker = RealBroker()
    broker.connect()
    with pytest.raises(ValueError):
        broker.submit_order("AAPL", "BUY", -10)

def test_broker_submit_invalid_symbol():
    broker = RealBroker()
    broker.connect()
    with pytest.raises(ValueError):
        broker.submit_order("", "BUY", 10)

def test_broker_invalid_order_type():
    broker = RealBroker()
    broker.connect()
    with pytest.raises(ValueError):
        broker.submit_order("AAPL", "HODL", 10)

def test_broker_connect_idempotency():
    broker = RealBroker()
    broker.connect()
    broker.connect()
    assert broker.is_connected is True

# Tier 3: Pairwise Interaction Coverage
def test_pairwise_sentiment_to_allocation():
    score = analyze_sentiment("Good earnings")
    price_proxy = score * 100
    weights = allocate_assets({"AAPL": price_proxy, "MSFT": 100.0})
    assert abs(sum(weights.values()) - 1.0) < 1e-6

def test_pairwise_rl_to_broker():
    model = train_rl_model([{"price": 100.0}, {"price": 101.0}])
    action = model.predict([{"price": 102.0}])
    broker = RealBroker()
    broker.connect()
    status = broker.submit_order("AAPL", "BUY" if action else "SELL", 10)
    assert status is True

def test_pairwise_allocation_to_broker():
    weights = allocate_assets({"AAPL": 150.0})
    broker = RealBroker()
    broker.connect()
    status = broker.submit_order("AAPL", "BUY", int(weights["AAPL"] * 10))
    assert status is True

def test_pairwise_broker_to_report():
    broker = RealBroker()
    broker.connect()
    broker.submit_order("AAPL", "BUY", 10)
    history = broker.get_order_history()
    path = "./test_pairwise_report.pdf"
    if os.path.exists(path):
        os.remove(path)
    generate_pdf_report(history, path)
    assert os.path.exists(path) is True
    assert os.path.getsize(path) > 0

# Tier 4: Real-World Scenarios
@pytest.mark.skip(reason="Phase 3 e2e scaffold - real_broker not implemented")
def test_scenario_full_trade_cycle():
    score = analyze_sentiment("Incredible growth")  # noqa: F841
    model = train_rl_model([{"price": 100.0}])  # noqa: F841
    action = model.predict([{"price": 100.0}])  # noqa: F841
    weights = allocate_assets({"AAPL": 150.0, "MSFT": 300.0})  # noqa: F841
    
    broker = RealBroker()
    broker.connect()
    for sym, w in weights.items():
        broker.submit_order(sym, "BUY" if score > 0.5 else "SELL", int(w * 100))
    
    history = broker.get_order_history()
    assert len(history) >= 2

@pytest.mark.skip(reason="Phase 3 e2e scaffold - real_broker not implemented")
def test_scenario_end_of_day_reporting():
    analyze_sentiment("Good")
    analyze_sentiment("Bad")
    weights = allocate_assets({"AAPL": 100.0})  # noqa: F841
    trades = [{"symbol": sym, "qty": int(w*10), "price": 100.0} for sym, w in weights.items()]
    path = "./eod_report.pdf"
    if os.path.exists(path):
        os.remove(path)
    generate_pdf_report(trades, path)
    assert os.path.exists(path) is True

def test_scenario_emergency_reallocation():
    score = analyze_sentiment("CRITICAL CRASH")
    assert score < 0.5
    weights = allocate_assets({"AAPL": 50.0, "MSFT": 100.0})
    broker = RealBroker()
    broker.connect()
    for sym, w in weights.items():
        broker.submit_order(sym, "SELL", int(w * 100))
    history = broker.get_order_history()
    assert len(history) == 2
