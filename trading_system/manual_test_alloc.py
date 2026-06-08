from src.strategy.allocation import allocate_assets
import sys
import traceback

def run_tests():
    try:
        prices = {"AAPL": 150.0, "GOOGL": 250.0, "MSFT": 100.0}
        weights = allocate_assets(prices)
        assert len(weights) == 3
        assert sum(weights.values()) == 1.0
        
        weights = allocate_assets({})
        assert weights == {}
        
        prices = {"AAPL": 150.0, "BAD1": -50.0, "BAD2": 0.0}
        weights = allocate_assets(prices)
        assert len(weights) == 1
        assert weights["AAPL"] == 1.0
        
        prices = {"BAD1": -50.0, "BAD2": 0.0}
        assert allocate_assets(prices) == {}
        
        prices = {"AAPL": 150.0, "BAD_INF": float('inf'), "BAD_NAN": float('nan'), "BAD_STR": "invalid"}
        weights = allocate_assets(prices)
        assert len(weights) == 1
        assert weights["AAPL"] == 1.0
        
        prices = {"A": 10.0, "B": 10.0, "C": 10.0}
        weights = allocate_assets(prices)
        assert len(weights) == 3
        assert sum(weights.values()) == 1.0
        
        prices7 = {str(i): 1.0 for i in range(7)}
        weights7 = allocate_assets(prices7)
        assert sum(weights7.values()) == 1.0
        
        prices_prec = {"X": 1.0, "Y": 1.0, "Z": 1.0}
        weights_prec = allocate_assets(prices_prec)
        assert weights_prec["Z"] == 1.0 - (weights_prec["X"] + weights_prec["Y"])
        assert sum(weights_prec.values()) == 1.0
        print("All tests passed.")
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    run_tests()
