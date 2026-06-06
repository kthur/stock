import math

def allocate_assets(prices_dict: dict) -> dict:
    """
    Allocate weights proportionally based on valid prices.
    Assets with price <= 0 or invalid (NaN, Inf) are filtered out.
    Weights sum exactly to 1.0.
    """
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
    
    # Ensure exact sum of 1.0 by adjusting the last weight
    keys = list(weights.keys())
    if len(keys) > 0:
        sum_except_last = sum(weights[k] for k in keys[:-1])
        weights[keys[-1]] = 1.0 - sum_except_last
        
    return weights
