import math

def allocate_assets(prices_dict: dict, strict: bool = False) -> dict:
    """
    Allocate weights proportionally based on valid prices.
    Assets with price <= 0 or invalid (NaN, Inf) are filtered out.
    Weights sum exactly to 1.0.
    """
    if prices_dict is None:
        raise TypeError("Input cannot be None")
    if not isinstance(prices_dict, dict):
        raise TypeError("Input must be a dictionary")

    if strict:
        if not prices_dict:
            raise ValueError("Input dictionary cannot be empty")
        for k, v in prices_dict.items():
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise TypeError(f"Price for {k} must be a number")
            if not math.isfinite(v):
                raise ValueError(f"Price for {k} must be finite")
            if v < 0:
                raise ValueError(f"Price for {k} cannot be negative")
            if v == 0:
                raise ValueError(f"Price for {k} cannot be zero")

    valid_prices = {}
    for k, v in prices_dict.items():
        if isinstance(v, bool):
            continue
        if not isinstance(v, (int, float)):
            continue
        if not math.isfinite(v):
            continue
        if v <= 0:
            continue
        valid_prices[k] = v

    if not valid_prices:
        return {}

    total_price = sum(valid_prices.values())
    weights = {k: v / total_price for k, v in valid_prices.items()}

    # Ensure exact sum of 1.0 by adjusting the last weight
    keys = list(weights.keys())
    if len(keys) > 0:
        sum_except_last = sum(weights[k] for k in keys[:-1])
        weights[keys[-1]] = 1.0 - sum_except_last

    return weights
