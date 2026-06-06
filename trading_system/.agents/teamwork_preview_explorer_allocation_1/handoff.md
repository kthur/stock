# Handoff: Asset Allocation Implementation Strategy

## 1. Observation
- The project documentation (`PROJECT.md` and `SCOPE.md`) specifies an asset allocation module at `src/strategy/allocation.py`.
- The required interface is `allocate_assets(prices_dict: dict) -> dict`, which must return normalized weights summing to exactly 1.0.
- The prompt highlights edge cases that must be handled: 0 or negative prices, empty dictionary, and ensuring the sum is exactly 1.0 (to account for floating-point inaccuracies).
- A search of the codebase (`(?i)allocate|allocation`) confirms that `src/strategy/allocation.py` and `tests/phase3/test_allocation.py` do not yet exist, so this will be a new implementation.

## 2. Logic Chain
- **Empty Input:** If `prices_dict` is empty, there are no assets to allocate. Returning an empty dictionary `{}` is the safest approach, as distributing 1.0 across 0 assets is mathematically impossible.
- **Negative and Zero Prices:** In long-only portfolio allocation (typical context unless shorting is explicitly supported), negative or zero prices are invalid. They should be clamped to `0.0`. Their final weight will be `0.0`.
- **All Valid Prices <= 0:** If the total sum of valid prices is `0` (e.g. all prices are `0` or negative), we cannot compute a proportional weight (`price / total`). The most robust fallback is an equal-weight distribution (`1.0 / len(prices_dict)`) across all given assets.
- **Normal Allocation:** Calculate each asset's weight as `price / total_price`.
- **Exact 1.0 Summation:** Due to floating-point representation, the sum of weights (like `1/3 + 1/3 + 1/3 = 0.9999999999999999`) may not be exactly `1.0`. To fix this, we find the asset with the largest weight and add the residual difference (`1.0 - actual_sum`) to it. This guarantees exactly `1.0` sum while minimizing the relative impact on the largest position.

## 3. Caveats
- This strategy assumes a price-weighted allocation (i.e., weight is proportional to the price value in the dictionary). If `prices_dict` actually contains *scores* or *target values*, the mathematical normalization logic remains identically applicable.
- The floating-point adjustment modifies the largest weight. In extreme cases where all weights are equal (e.g., three assets of price 10), the first maximum found will absorb the tiny error. This is standard practice but slightly breaks perfect symmetry at the floating-point precision level.

## 4. Conclusion
The implementation should be placed in `src/strategy/allocation.py` and structured as follows:

```python
def allocate_assets(prices_dict: dict) -> dict:
    """
    Returns normalized weights summing to exactly 1.0 based on input prices.
    Handles empty dictionaries, negative/zero prices, and floating-point errors.
    """
    if not prices_dict:
        return {}

    # Clamp negative/zero prices to 0.0
    valid_prices = {k: max(0.0, float(v)) for k, v in prices_dict.items()}
    total = sum(valid_prices.values())

    if total == 0:
        # Fallback: if no positive prices exist, distribute equally
        n = len(prices_dict)
        return {k: 1.0 / n for k in prices_dict.keys()}

    weights = {k: v / total for k, v in valid_prices.items()}

    # Ensure weights sum exactly to 1.0 to handle floating point precision
    actual_sum = sum(weights.values())
    if actual_sum != 1.0:
        max_key = max(weights, key=weights.get)
        weights[max_key] += (1.0 - actual_sum)

    return weights
```

**Proposed Unit Tests for `tests/phase3/test_allocation.py`:**
```python
import pytest
from src.strategy.allocation import allocate_assets

def test_allocate_assets_normal():
    prices = {"AAPL": 150.0, "MSFT": 300.0, "GOOGL": 50.0}
    weights = allocate_assets(prices)
    assert sum(weights.values()) == 1.0
    assert weights["MSFT"] == 0.6  # 300 / 500
    assert weights["AAPL"] == 0.3  # 150 / 500
    assert weights["GOOGL"] == 0.1 # 50 / 500

def test_allocate_assets_empty():
    assert allocate_assets({}) == {}

def test_allocate_assets_with_zero_and_negative():
    prices = {"A": 100.0, "B": 0.0, "C": -50.0}
    weights = allocate_assets(prices)
    assert sum(weights.values()) == 1.0
    assert weights["A"] == 1.0
    assert weights["B"] == 0.0
    assert weights["C"] == 0.0

def test_allocate_assets_all_zero_or_negative():
    prices = {"A": 0.0, "B": -10.0}
    weights = allocate_assets(prices)
    assert sum(weights.values()) == 1.0
    assert weights["A"] == 0.5
    assert weights["B"] == 0.5

def test_allocate_assets_floating_point_exact_one():
    prices = {"A": 10.0, "B": 10.0, "C": 10.0}
    weights = allocate_assets(prices)
    assert sum(weights.values()) == 1.0
```

## 5. Verification Method
- Implement the code in `src/strategy/allocation.py`.
- Implement the tests in `tests/phase3/test_allocation.py`.
- Run `pytest tests/phase3/test_allocation.py` to confirm all edge cases (empty, negative, floating point precision) pass.
