import math

def allocate_assets(prices_dict: dict) -> dict:
    if not prices_dict:
        return {}

    valid_prices = {}
    for k, v in prices_dict.items():
        if isinstance(v, (int, float)) and v > 0 and not math.isinf(v) and not math.isnan(v):
            valid_prices[k] = v

    if not valid_prices:
        return {}

    total_price = sum(valid_prices.values())

    weights = {}
    items = list(valid_prices.items())

    for i, (k, v) in enumerate(items):
        if i == len(items) - 1:
            weights[k] = 1.0 - sum(weights.values())
        else:
            weights[k] = v / total_price

    return weights

if __name__ == "__main__":
    prices = {"AAPL": 150.0, "GOOGL": float('inf'), "MSFT": float('nan'), "BAD": -50.0, "ZERO": 0.0}
    w = allocate_assets(prices)
    print("Test 1 (inf/nan filter):", w, "Sum:", sum(w.values()))

    prices2 = {"A": 10.0, "B": 10.0, "C": 10.0}
    w2 = allocate_assets(prices2)
    print("Test 2 (precision):", w2, "Sum:", sum(w2.values()) == 1.0)

    import random
    prices3 = {str(i): random.random() for i in range(15)}
    w3 = allocate_assets(prices3)
    print("Test 3 (random precision): Sum exactly 1.0?", sum(w3.values()) == 1.0)
