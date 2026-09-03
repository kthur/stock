# Milestone 1 Adversarial Stress Testing Handoff Report

## Verdict: REQUEST_CHANGES

### Summary
Milestone 1 features F01, F02, F03, and F05 demonstrate high algorithmic quality in discrete scenarios (strict CRISIS string resolution without fallback, rapid 50-step oscillation stability without memory leaks, and machine-epsilon normalization drift ~ 4.44e-16).
**HOWEVER**, empirical adversarial stress testing identified a **CRITICAL CLASS-LEVEL STATE POLLUTION BUG** in `EnsembleScoringEngine`:
In `_load_tuned_regime_weights()`, `self.REGIME_2D_WEIGHTS` (a class attribute) is mutated in-place with partial 31-strategy parameters from `models/tuned_params.json`. On each successive instantiation of `EnsembleScoringEngine`, strategies 32-37 (including `overnight_gap_reversal`, `range_expansion_breakout`, etc.) are multiplied by 1 / 1.15 (approx 0.87), decaying below the required 0.005 floor by instance 7 (0.004878), and decaying to 0.002597 after 15+ calls.

---

## 1. Observation

### Empirical Test Execution
We created and executed a 33-test adversarial stress test suite in `tests/test_adversarial_m1_stress.py`:
- Command: `.venv\Scripts\pytest.exe tests/test_adversarial_m1_stress.py -v`
- Results: 32 passed, 1 failed (deterministic failure on `test_adversarial_instance_isolation_weight_decay`).

### Observed Error
Verbatim failure from pytest:
```
______________ test_adversarial_instance_isolation_weight_decay _______________
tests\test_adversarial_m1_stress.py:155: in test_adversarial_instance_isolation_weight_decay
    assert og_weight >= 0.005, (
E   AssertionError: Instance 7: overnight_gap_reversal decayed to 0.004878 (< 0.005 floor) due to class-level REGIME_2D_WEIGHTS mutation in _load_tuned_regime_weights!
E   assert 0.004878048780487791 >= 0.005
=========================== short test summary info ===========================
FAILED tests/test_adversarial_m1_stress.py::test_adversarial_instance_isolation_weight_decay - AssertionError: Instance 7: overnight_gap_reversal decayed to 0.004878 (< 0.005 floor) due to class-level REGIME_2D_WEIGHTS mutation in _load_tuned_regime_weights!
```

Furthermore, when executing `tests/test_m1_quant_enhancements.py` and `tests/test_adversarial_m1_stress.py` together in the same pytest session:
```
___ test_adversarial_degenerate_regime_posteriors[probs5-mixed_inf_finite] ____
tests\test_adversarial_m1_stress.py:69: in test_adversarial_degenerate_regime_posteriors
    assert w >= 0.005 - 1e-6, f"Weight floor violation for {strat} in {label}: {w} < 0.005"
E   AssertionError: Weight floor violation for overnight_gap_reversal in mixed_inf_finite: 0.0025974025974025822 < 0.005
```

### Exact Code Paths
1. `trading_system/src/ai/ensemble_scorer.py`:
   - Line 237: `REGIME_2D_WEIGHTS = { ... }` defined as a class-level dictionary.
   - Line 613: `self._load_tuned_regime_weights()` called in `__init__`.
   - Lines 717-724:
     ```python
     for k, v in tuned.items():
         if k in self.REGIME_2D_WEIGHTS:
             self.REGIME_2D_WEIGHTS[k].update(v)
             w_sum = sum(self.REGIME_2D_WEIGHTS[k].values())
             if w_sum > 0:
                 self.REGIME_2D_WEIGHTS[k] = {
                     strat: float(val / w_sum) for strat, val in self.REGIME_2D_WEIGHTS[k].items()
                 }
     ```
2. `trading_system/models/tuned_params.json`:
   - Lines 193-225: `regime_2d_weights` contains tuned weights for only 31 strategies (summing to ~1.00), omitting strategies 32-37 (`cross_asset_spillover`, `supply_chain_gnn`, `range_expansion_breakout`, `dual_correction`, `index_rebalance`, `overnight_gap_reversal`).

### Empirical Metrics
From `test_empirical_performance_benchmark`:
- Iterations: 200
- Base Weights Mean Latency: **5.7296 ms** (includes StrategyRegistry module auto-discovery)
- Dynamic Weights Mean Latency: **7.1361 ms**
- Dynamic Weights P95 Latency: **9.0781 ms**
- Dynamic Weights P99 Latency: **11.2852 ms** (well below 60.0 ms SLA)
- Max Normalization Drift: **4.44089210e-16** (strictly machine epsilon, <= 1e-5)
- Max Weight Delta: **0.0925** (well below 0.1500 runaway limit; smooth TV-smoothing evolution)

---

## 2. Logic Chain

1. **Step 1 (Class Attribute Sharing)**: `EnsembleScoringEngine.REGIME_2D_WEIGHTS` is bound to the class namespace. Without an explicit instance copy `self.REGIME_2D_WEIGHTS = {k: dict(v) for k, v in self.__class__.REGIME_2D_WEIGHTS.items()}` in `__init__`, all references access and mutate the same dictionary in memory.
2. **Step 2 (Partial JSON Parameter Injection)**: `models/tuned_params.json` was generated under a 31-strategy configuration. It does not define weights for strategies 32 through 37.
3. **Step 3 (Successive Re-Normalization Shrinkage)**:
   - On instance 1, `self.REGIME_2D_WEIGHTS[k].update(v)` sets the 31 tuned strategies to raw values summing to approx 1.00. The untuned strategies 32-37 retain their original base weights (sum approx 0.15). The total sum becomes 1.15, so each untuned strategy is scaled by 1 / 1.15 = 0.8696 (`overnight_gap_reversal`: 0.01 -> 0.008696).
   - On instance 2, `update(v)` resets the 31 strategies to raw values (sum 1.00), while strategies 32-37 start from their already shrunken values (0.008696). They are scaled by 1 / 1.15 again (0.008696 -> 0.007562).
   - By instance 7, `overnight_gap_reversal` decays to 0.004878 < 0.005000, violating the weight floor contract.
   - In continuous daemon runs or multi-market batch passes where `EnsembleScoringEngine` is re-instantiated, strategies 32-37 progressively vanish toward zero alpha.
4. **Step 4 (Empirical Fix Verification)**:
   Testing with instance-isolated copying in `__init__`:
   ```python
   self.REGIME_2D_WEIGHTS = {k: dict(v) for k, v in self.__class__.REGIME_2D_WEIGHTS.items()}
   ```
   completely eliminated the decay: 10 consecutive instantiations held `overnight_gap_reversal` rock-solid at `0.008696` with total sum `1.000000`.

---

## 3. Caveats

- In a fresh Python process where `EnsembleScoringEngine` is instantiated only 1-3 times, the bug does not immediately breach the 0.005 floor; it only breaches after >= 7 instantiations in the same process (such as in a test runner, multi-market batch runner, or continuous daemon).
- The standalone strategy `opening_auction_arbitrage` has base weight 0.0 by design in `StrategyRegistry` and is not active in the 37-factor core.
- All other tests for F01, F02, F03, and F05 (including 10 CRISIS string variants and rapid 50-step regime switching across VIX 5.0 to 80.0) passed with zero errors.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

Worker M1 must apply a small, targeted fix to `trading_system/src/ai/ensemble_scorer.py`:
In `EnsembleScoringEngine.__init__`, make `self.REGIME_2D_WEIGHTS` an instance-level dictionary copy before loading tuned weights:
```python
self.REGIME_2D_WEIGHTS = {k: dict(v) for k, v in self.__class__.REGIME_2D_WEIGHTS.items()}
```
Additionally, `_load_tuned_regime_weights()` should ensure untuned strategies are not repeatedly deflated if tuned weights are updated.

---

## 5. Verification Method

### How to Independently Verify the Defect and Fix
1. Run the new adversarial stress test suite:
   ```bash
   .venv\Scripts\pytest.exe tests/test_adversarial_m1_stress.py -v -k "test_adversarial_instance_isolation_weight_decay"
   ```
   Expected: **FAIL** (shows decay to 0.004878 on instance 7).

2. Apply the one-line instance isolation fix in `trading_system/src/ai/ensemble_scorer.py`:
   ```python
   self.REGIME_2D_WEIGHTS = {k: dict(v) for k, v in self.__class__.REGIME_2D_WEIGHTS.items()}
   ```

3. Re-run the full combined suite:
   ```bash
   .venv\Scripts\pytest.exe tests/test_m1_quant_enhancements.py tests/test_adversarial_m1_stress.py -v
   ```
   Expected: **47 passed in ~30s (100% PASS)**.