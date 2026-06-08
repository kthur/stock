# Asset Allocation Investigation Handoff

## 1. Observation
1. In `src/strategy/allocation.py`, `allocate_assets(prices_dict)` currently determines weights with `w = v / total_price`. It attempts to fix precision by adding `1.0 - sum(weights.values())` to the largest weight after all weights are calculated.
2. Python's `sum()` adds values sequentially left-to-right. Due to floating-point non-associativity, modifying an arbitrary element in the middle of a list (like the "largest weight") means `sum(weights.values())` will evaluate as `(sum_before + adjusted_val) + sum_after`. This re-orders the additions compared to `1.0 - sum(original_weights)`, which introduces tiny precision errors, failing strict `== 1.0` checks.
3. If an input price is `float('inf')`, `v > 0` returns `True`. The `total_price` becomes `inf`. `inf / inf` evaluates to `NaN` for that asset, and `finite / inf` evaluates to `0.0`. This results in `NaN` weights.

## 2. Logic Chain
1. To guarantee `sum(weights.values()) == 1.0` with Python's standard `sum()`, we must ensure that the arithmetic sequence precisely matches `a + (1.0 - a) == 1.0`. 
2. Because Python 3.7+ dictionaries maintain insertion order, we can iterate over the valid items and populate the `weights` dictionary in order.
3. For all items except the last one, we calculate the weight normally: `v / total_price`.
4. For the **last item**, we calculate its weight as `1.0 - sum(weights.values())`. 
5. When `sum(weights.values())` is called on the final dictionary, it will sequentially sum all the earlier weights (resulting in the exact same float value `S`), and then add the final element `1.0 - S`. By IEEE 754 standards, `S + (1.0 - S)` perfectly rounds back to `1.0`.
6. To fix the `NaN` issue, we must strictly filter out `inf` and `NaN` values during the initial valid price comprehension using `math.isinf()` and `math.isnan()`. 

## 3. Caveats
- This assumes Python 3.7+ where dictionary iteration order is guaranteed to follow insertion order.
- It assumes `total_price > 0`. If all prices are filtered out (e.g., all were `inf` or `<= 0`), the function correctly returns an empty dict `{}` and avoids division by zero.
- Very small weights may still undergo precision loss individually, but the sum will strictly equal `1.0`.

## 4. Conclusion
The implementation of `allocate_assets` should be updated to strictly filter out `NaN` and `inf`, and the float precision fix should apply `1.0 - sum(previous_weights)` exclusively to the **last** inserted weight, mirroring Python's `sum()` evaluation order.

Proposed implementation:
```python
import math

def allocate_assets(prices_dict: dict) -> dict:
    if not prices_dict:
        return {}

    # Filter out invalid prices (<= 0, inf, NaN)
    valid_prices = {}
    for k, v in prices_dict.items():
        if isinstance(v, (int, float)) and v > 0 and not math.isinf(v) and not math.isnan(v):
            valid_prices[k] = float(v)
            
    if not valid_prices:
        return {}
        
    total_price = sum(valid_prices.values())
    
    weights = {}
    items = list(valid_prices.items())
    
    for i, (k, v) in enumerate(items):
        if i == len(items) - 1:
            # Last item exactly compensates for the sum of all previous items
            weights[k] = 1.0 - sum(weights.values())
        else:
            weights[k] = v / total_price
            
    return weights
```

## 5. Verification Method
- **Float precision**: Run a loop generating random floats for prices. Call the updated `allocate_assets`. Assert `sum(weights.values()) == 1.0` strictly using `==`.
- **NaN/inf filter**: Pass `{"A": float('inf'), "B": float('nan'), "C": 100.0, "D": -50}`. Assert the result is `{"C": 1.0}`.
- **Tests**: Re-run the existing `pytest tests/phase3/test_allocation.py` to ensure backwards compatibility.
