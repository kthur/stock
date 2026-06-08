import math

def allocate_assets(prices_dict: dict) -> dict:
    if not prices_dict:
        return {}
    valid_prices = {
        k: v for k, v in prices_dict.items() 
        if isinstance(v, (int, float)) and math.isfinite(v) and v > 0
    }
    if not valid_prices:
        return {}
    total_price = sum(valid_prices.values())
    weights = {k: v / total_price for k, v in valid_prices.items()}
    keys = list(weights.keys())
    if len(keys) > 0:
        sum_except_last = sum(weights[k] for k in keys[:-1])
        weights[keys[-1]] = 1.0 - sum_except_last
    return weights

print(allocate_assets({"A": 10.0, "B": 10.0, "C": 10.0}))
print(allocate_assets({"AAPL": 150.0, "BAD_INF": float('inf'), "BAD_NAN": float('nan'), "BAD_STR": "invalid"}))
