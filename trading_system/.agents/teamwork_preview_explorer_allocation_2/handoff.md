# Investigation Report: Asset Allocation Implementation Strategy

## 1. Observation
- Read `d:/Finance/code/stock/trading_system/PROJECT.md` and `.agents/sub_orch_m2/SCOPE.md`.
- Both specify the signature: `allocate_assets(prices_dict: dict) -> dict`.
- The user request explicitly demands:
  - Normalizing inputs.
  - Ensuring weights sum to exactly 1.0.
  - Handling edge cases such as 0 or negative prices, and empty dictionaries.
- Files `src/strategy/allocation.py` and `tests/phase3/test_allocation.py` do not yet exist.

## 2. Logic Chain
1. **Normalization Strategy**: Since the input is `prices_dict`, a price-weighted allocation (proportional to the asset's price) is the most direct interpretation of "normalizing inputs".
2. **Handling Empty Dictionaries**: If `prices_dict` is empty, there is nothing to allocate. Returning an empty dictionary `{}` is the safest fallback.
3. **Handling 0 or Negative Prices**: Prices <= 0 are mathematically nonsensical for price-proportional weighting. We should filter out any assets with a price <= 0. If all assets are filtered out, the function should return `{}`.
4. **Ensuring Exact 1.0 Sum**: Floating-point division can lead to sums like `0.9999999999999999`. To guarantee an exact sum of `1.0`, we calculate the residual `1.0 - sum(weights)` and add it to the asset with the largest weight. This ensures precision without violating the structural logic.

## 3. Caveats
- **Allocation Strategy Assumption**: The proposed logic implements a "price-weighted" strategy. If the user intends for `prices_dict` to simply act as a trigger for an "equal-weighted" strategy, the logic would change to `1.0 / len(valid_prices)`. However, normalizing the input values points strongly toward proportional weighting.
- **Python version**: Uses standard dictionary ordering and `max()` operations which are stable in modern Python, but tests must account for exact exact float representations.

## 4. Conclusion
Below is the proposed implementation for `src/strategy/allocation.py`:

```python
def allocate_assets(prices_dict: dict) -> dict:
    if not prices_dict:
        return {}

    # Filter out invalid prices (<= 0)
    valid_prices = {k: v for k, v in prices_dict.items() if v > 0}
    
    if not valid_prices:
        return {}

    total_price = sum(valid_prices.values())
    weights = {k: v / total_price for k, v in valid_prices.items()}

    # Ensure weights sum to exactly 1.0
    total_weight = sum(weights.values())
    if total_weight != 1.0:
        largest_asset = max(weights, key=weights.get)
        weights[largest_asset] += (1.0 - total_weight)

    return weights
```

Below is the proposed unit tests for `tests/phase3/test_allocation.py`:

```python
import pytest
from src.strategy.allocation import allocate_assets

def test_allocate_assets_normal():
    prices = {"AAPL": 150.0, "MSFT": 300.0}
    weights = allocate_assets(prices)
    assert sum(weights.values()) == 1.0
    assert weights["AAPL"] == 150.0 / 450.0
    assert weights["MSFT"] == 300.0 / 450.0

def test_allocate_assets_empty():
    assert allocate_assets({}) == {}

def test_allocate_assets_with_zero_and_negative():
    prices = {"AAPL": 150.0, "BAD": 0.0, "WORSE": -50.0}
    weights = allocate_assets(prices)
    assert sum(weights.values()) == 1.0
    assert "BAD" not in weights
    assert "WORSE" not in weights
    assert weights["AAPL"] == 1.0

def test_allocate_assets_all_invalid():
    prices = {"BAD": 0.0, "WORSE": -50.0}
    assert allocate_assets(prices) == {}

def test_allocate_assets_exact_sum_floating_point():
    # 3 assets with equal prices will result in 0.3333... weights
    # Our logic ensures the sum is exactly 1.0 by adjusting the largest element
    prices = {"A": 10.0, "B": 10.0, "C": 10.0}
    weights = allocate_assets(prices)
    assert sum(weights.values()) == 1.0
```

## 5. Verification Method
1. Write the proposed code into the respective files.
2. Run `pytest tests/phase3/test_allocation.py` to ensure all tests pass and coverage encompasses edge cases.
