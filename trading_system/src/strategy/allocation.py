def allocate_assets(prices_dict: dict) -> dict:
    """
    Allocate weights proportionally based on valid prices.
    Assets with price <= 0 are filtered out.
    Weights sum exactly to 1.0. If the sum differs from 1.0 due to float
    precision, the remainder is added to the asset with the largest weight.
    """
    if not prices_dict:
        return {}

    valid_prices = {k: v for k, v in prices_dict.items() if v > 0}
    
    if not valid_prices:
        return {}
        
    total_price = sum(valid_prices.values())
    
    weights = {k: v / total_price for k, v in valid_prices.items()}
    
    # Ensure exact sum of 1.0 by adjusting the largest weight
    total_weight = sum(weights.values())
    remainder = 1.0 - total_weight
    
    if remainder != 0.0:
        # Find the asset with the largest weight
        # In case of tie, max will return the first one based on dict iteration order
        # or we could sort by weight then key. max() with key function works well.
        largest_asset = max(weights, key=lambda k: weights[k])
        weights[largest_asset] += remainder
        
    return weights
