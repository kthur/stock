# Asset Allocation Implementation Strategy

## Observation
- The interface contracts in `d:/Finance/code/stock/trading_system/PROJECT.md` and `SCOPE.md` specify an `allocate_assets(prices_dict: dict) -> dict` function that must return normalized weights summing exactly to 1.0.
- `src/strategy/allocation.py` and `tests/phase3/test_allocation.py` do not currently exist.
- The user requirements ask to handle edge cases such as empty dictionaries, and 0 or negative prices.

## Logic Chain
1. **Handling Edge Cases**: 
   - An empty `prices_dict` should immediately return an empty dictionary `{}`.
   - Negative or zero prices are invalid for a long-only stock allocation based on prices. The logic should filter out any key-value pairs where `price <= 0`. If no assets remain after filtering, it should return `{}`.
2. **Normalizing Inputs**:
   - Compute the total sum of all strictly positive prices.
   - To find the weight of each asset, divide its price by the `total_price`.
3. **Ensuring Exact 1.0 Sum**:
   - Floating-point arithmetic may lead to a sum like `0.9999999999999999`. 
   - To guarantee the sum is exactly `1.0`, we can assign the mathematically calculated weights for the first `N-1` assets, keep a running total, and assign `1.0 - running_sum` to the very last asset.

### Proposed Code for `src/strategy/allocation.py`
```python
def allocate_assets(prices_dict: dict) -> dict:
    if not prices_dict:
        return {}
    
    # Filter out prices <= 0
    valid_assets = {k: v for k, v in prices_dict.items() if v > 0}
    if not valid_assets:
        return {}
        
    total_price = sum(valid_assets.values())
    weights = {}
    
    assets = list(valid_assets.keys())
    running_sum = 0.0
    
    # Process all but the last asset
    for asset in assets[:-1]:
        weight = valid_assets[asset] / total_price
        weights[asset] = weight
        running_sum += weight
        
    # Last asset gets the exact remainder to ensure sum == 1.0
    weights[assets[-1]] = 1.0 - running_sum
    
    return weights
```

### Proposed Tests for `tests/phase3/test_allocation.py`
```python
import pytest
from src.strategy.allocation import allocate_assets

def test_allocate_assets_normal():
    prices = {"AAPL": 150.0, "MSFT": 300.0}
    weights = allocate_assets(prices)
    assert weights["AAPL"] == 150.0 / 450.0
    assert weights["MSFT"] == 300.0 / 450.0
    assert sum(weights.values()) == 1.0

def test_allocate_assets_with_zero_and_negative():
    prices = {"AAPL": 150.0, "BAD": 0.0, "WORSE": -10.0}
    weights = allocate_assets(prices)
    assert "BAD" not in weights
    assert "WORSE" not in weights
    assert weights["AAPL"] == 1.0
    assert sum(weights.values()) == 1.0

def test_allocate_assets_empty_or_all_invalid():
    assert allocate_assets({}) == {}
    assert allocate_assets({"BAD": 0.0, "WORSE": -5.0}) == {}

def test_allocate_assets_float_precision():
    # 3 assets with equal price will result in 1/3 (0.3333...)
    prices = {"A": 100.0, "B": 100.0, "C": 100.0}
    weights = allocate_assets(prices)
    # Validate the exact sum matches 1.0
    assert sum(weights.values()) == 1.0
    # Values might be slightly adjusted for the last one but should be close
    assert abs(weights["A"] - 0.3333333333333333) < 1e-9
    assert abs(weights["C"] - 0.3333333333333333) < 1e-9
```

## Caveats
- Assuming a price-weighted allocation strategy based on the parameter `prices_dict: dict`. If the system requires equal weighting regardless of price or an inverse-volatility weighting, the logic will need adjustment. 
- Returning `{}` for empty inputs or negative-only prices assumes the downstream system handles empty allocations gracefully.

## Conclusion
The implementation of `allocate_assets` should apply price-weighted normalization, gracefully filter out non-positive prices, and enforce exact floating-point `1.0` sum using remainder assignment. Test coverage should explicitly cover precision guarantees and edge cases.

## Verification Method
1. Create the respective files (`src/strategy/allocation.py` and `tests/phase3/test_allocation.py`) using the proposed logic.
2. Run `pytest tests/phase3/test_allocation.py` to confirm tests pass, verifying exact 1.0 summations and edge cases.
