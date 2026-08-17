import math
from src.strategy.allocation import allocate_assets

def test_allocate_assets_normal():
    prices = {"AAPL": 150.0, "GOOGL": 250.0, "MSFT": 100.0}
    weights = allocate_assets(prices)

    assert len(weights) == 3
    assert math.isclose(weights["MSFT"], 100.0 / 500.0)
    assert weights["AAPL"] == 150.0 / 500.0
    assert weights["GOOGL"] == 250.0 / 500.0
    assert sum(weights.values()) == 1.0

def test_allocate_assets_empty():
    assert allocate_assets({}) == {}

def test_allocate_assets_negative_and_zero_prices():
    prices = {"AAPL": 150.0, "BAD1": -50.0, "BAD2": 0.0}
    weights = allocate_assets(prices)

    assert len(weights) == 1
    assert "AAPL" in weights
    assert weights["AAPL"] == 1.0

def test_allocate_assets_all_invalid():
    prices = {"BAD1": -50.0, "BAD2": 0.0}
    assert allocate_assets(prices) == {}

def test_allocate_assets_nan_and_inf_prices():
    prices = {"AAPL": 150.0, "BAD_INF": float('inf'), "BAD_NAN": float('nan'), "BAD_STR": "invalid"}
    weights = allocate_assets(prices)

    assert len(weights) == 1
    assert "AAPL" in weights
    assert weights["AAPL"] == 1.0

def test_allocate_assets_floating_point_edge_case():
    # Example where weights sum to slightly less or more than 1.0 due to precision
    # 3 assets with equal price
    prices = {"A": 10.0, "B": 10.0, "C": 10.0}
    weights = allocate_assets(prices)

    assert len(weights) == 3
    assert sum(weights.values()) == 1.0

    # 7 is a good divisor to test float precision
    prices7 = {str(i): 1.0 for i in range(7)}
    weights7 = allocate_assets(prices7)

    assert sum(weights7.values()) == 1.0

    prices_weird = {"A": 0.1, "B": 0.2}
    weights_weird = allocate_assets(prices_weird)
    assert sum(weights_weird.values()) == 1.0

    # Exact precision test for left-to-right insertion order sum correction
    # With 3 elements and weights 1/3, the last one should compensate.
    prices_prec = {"X": 1.0, "Y": 1.0, "Z": 1.0}
    weights_prec = allocate_assets(prices_prec)
    assert weights_prec["X"] == 1.0 / 3.0
    assert weights_prec["Y"] == 1.0 / 3.0
    # Z should be exactly 1.0 - (X + Y)
    assert weights_prec["Z"] == 1.0 - (weights_prec["X"] + weights_prec["Y"])
    assert sum(weights_prec.values()) == 1.0
