# Asset Allocation Fix Investigation

## 1. Observation
- `src/strategy/allocation.py` contains `allocate_assets(prices_dict: dict) -> dict`.
- The current implementation filters prices via `v > 0`. `float('inf')` passes `v > 0`, leading to `total_price = inf` and `v / total_price = NaN`, meaning weights become `NaN`.
- The current floating point sum correction method adjusts the largest weight by adding `1.0 - sum(weights.values())`. However, Python's `sum()` evaluates floating point addition strictly left-to-right (`((a + b) + c)`). Adding the remainder to an arbitrary element in the middle of the dictionary breaks the associativity, such that `sum(new_weights)` might not perfectly equal `1.0` due to floating point error accumulation on the re-ordered calculation.

## 2. Logic Chain
- To correctly handle `inf` and `NaN`, the filtering condition `v > 0` must be expanded to include a check for finiteness. We can use `math.isfinite(v)`. Checking `isinstance(v, (int, float))` and `math.isfinite(v)` and `v > 0` correctly filters out `inf`, `NaN`, and negative values.
- To perfectly guarantee that `sum(weights.values()) == 1.0` without associativity issues, the mathematical property `X + (1.0 - X) == 1.0` in IEEE 754 (round-to-nearest-even) can be exploited. We can set the weight of the *last* element in the dictionary strictly to `1.0 - sum(all_other_weights)`. Since `sum(weights.values())` iterates in dictionary insertion order, the final step evaluated inside `sum` will be exactly `sum(all_other_weights) + (1.0 - sum(all_other_weights))`, which yields exactly `1.0`.

## 3. Caveats
- Setting the last element's weight to `1.0 - sum(others)` places all the remainder adjustment onto the last element instead of the largest element. This remainder is extremely small (on the order of `1e-16`), so it does not meaningfully affect the weight distribution.
- Requires adding `import math` to the file.

## 4. Conclusion
The implementation of `allocate_assets` should be updated as follows:

```python
import math

def allocate_assets(prices_dict: dict) -> dict:
    """
    Allocate weights proportionally based on valid prices.
    Assets with price <= 0, inf, or NaN are filtered out.
    Weights sum exactly to 1.0. 
    """
    if not prices_dict:
        return {}

    # Filter out invalid prices
    valid_prices = {k: v for k, v in prices_dict.items() 
                    if isinstance(v, (int, float)) and math.isfinite(v) and v > 0}
    
    if not valid_prices:
        return {}
        
    total_price = sum(valid_prices.values())
    
    weights = {k: v / total_price for k, v in valid_prices.items()}
    
    # Ensure exact sum of 1.0 by adjusting the last weight
    keys = list(weights.keys())
    if keys:
        last_key = keys[-1]
        sum_except_last = sum(weights[k] for k in keys[:-1])
        weights[last_key] = 1.0 - sum_except_last
        
    return weights
```

## 5. Verification Method
- Execute the test suite for `src/strategy/allocation.py` and run tests `tests/phase3/test_allocation.py`, specifically checking test inputs with `float('inf')` and `float('nan')` to confirm they are safely ignored.
- Use property-based testing (e.g. random floats over 100,000 iterations) passing through `allocate_assets` to confirm that `sum(result.values()) == 1.0` exactly holds 100% of the time (verified with a Python script during investigation).
