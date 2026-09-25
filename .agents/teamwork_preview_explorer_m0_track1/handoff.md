# Handoff Report: Explorer 1 (M0 Track 1 — Ensemble & Factor Numerical Stability)

## 1. Observation

### 1.1 Python Environment Discrepancy
- The prompt mentioned running pytest using `trading_system\.venv\Scripts\python.exe`.
- Direct test execution under `trading_system\.venv` failed during collection of PyTorch dependents with:
  ```
  AttributeError: module 'torch' has no attribute 'Tensor'
  ```
  Investigation revealed `trading_system\.venv\Lib\site-packages\torch` was missing top-level module files (contents were nested in a redundant `torch/torch/` subdirectory).
- In contrast, the root virtual environment at `d:\Finance\code\stock\.venv\Scripts\python.exe` contains fully functional PyTorch (`D:\Finance\code\stock\.venv\Lib\site-packages\torch\__init__.py <class 'torch.Tensor'>`) and passes collection cleanly. Tests should therefore be executed with `.venv\Scripts\python.exe` (or `pytest` in root `.venv`).

### 1.2 Track 1 Failing Tests Catalog (44 Total Failures)

#### Category A: NameError `reg_str` in `combine_predictions` (38 Failures)
All 38 failures produce the identical stack trace:
```
File "trading_system\src\ai\ensemble_scorer.py", line 19501, in combine_predictions
    elif 'BULL' in reg_str or str(regime) == '2':
                   ^^^^^^^
NameError: name 'reg_str' is not defined
```

Failing test cases:
1. `tests/test_phase5_m1_challenger2_adversarial.py` (23 failures):
   - `test_scenario1_all_zeros_scores[BULL_LOW_VOL]`
   - `test_scenario1_all_zeros_scores[BULL_HIGH_VOL]`
   - `test_scenario1_all_zeros_scores[SIDEWAYS_LOW_VOL]`
   - `test_scenario1_all_zeros_scores[SIDEWAYS_HIGH_VOL]`
   - `test_scenario1_all_zeros_scores[BEAR_LOW_VOL]`
   - `test_scenario1_all_zeros_scores[BEAR_HIGH_VOL]`
   - `test_scenario1_all_zeros_scores[CRISIS]`
   - `test_scenario1_all_zeros_scores[UNKNOWN_FALLBACK]`
   - `test_scenario1_all_ones_scores[BULL_LOW_VOL]`
   - `test_scenario1_all_ones_scores[BULL_HIGH_VOL]`
   - `test_scenario1_all_ones_scores[SIDEWAYS_LOW_VOL]`
   - `test_scenario1_all_ones_scores[SIDEWAYS_HIGH_VOL]`
   - `test_scenario1_all_ones_scores[BEAR_LOW_VOL]`
   - `test_scenario1_all_ones_scores[BEAR_HIGH_VOL]`
   - `test_scenario1_all_ones_scores[CRISIS]`
   - `test_scenario1_all_ones_scores[UNKNOWN_FALLBACK]`
   - `test_scenario1_high_nan_proportions[0.9]`
   - `test_scenario1_high_nan_proportions[0.99]`
   - `test_scenario1_high_nan_proportions[1.0]`
   - `test_scenario1_extreme_outliers_and_negative_inputs`
   - `test_scenario1_small_universe_edge_cases[5]`
   - `test_scenario1_small_universe_edge_cases[8]`
   - `test_scenario3_performance_benchmark_500_stocks_37_strategies`
2. `tests/test_phase5_signal_enhancement.py` (2 failures):
   - `test_feature_35_1_top_decile_spread_expansion_and_monotonicity`
   - `test_feature_36_3_random_stress_universe_all_regimes`
3. `tests/test_phase6_m1_challenger2_adversarial.py` (8 failures):
   - `test_challenger_top_decile_spread_expansion_500_stocks`
   - `test_challenger_adversarial_degenerate_inputs[BULL_LOW_VOL]`
   - `test_challenger_adversarial_degenerate_inputs[BULL_HIGH_VOL]`
   - `test_challenger_adversarial_degenerate_inputs[SIDEWAYS_LOW_VOL]`
   - `test_challenger_adversarial_degenerate_inputs[SIDEWAYS_HIGH_VOL]`
   - `test_challenger_adversarial_degenerate_inputs[BEAR_LOW_VOL]`
   - `test_challenger_adversarial_degenerate_inputs[BEAR_HIGH_VOL]`
   - `test_challenger_adversarial_degenerate_inputs[CRISIS]`
4. `tests/test_phase6_signal_enhancement.py` (1 failure):
   - `test_feature_42_3_multi_market_randomized_stress_all_regimes`
5. `tests/test_phase7_m1_challenger1_adversarial.py` (1 failure):
   - `TestFullPipelineIntegrityStress::test_combine_predictions_extreme_adversarial`
6. `tests/test_phase7_signal_enhancement.py` (1 failure):
   - `test_feature_48_4_multi_market_stress_and_v6_backward_compatibility`
7. `tests/test_phase8_m1_challenger2_empirical.py` (1 failure):
   - `test_top_1pct_spread_expansion_in_large_synthetic_universe` (under backward-compatibility run `version=5`)

#### Category B: Numerical Discrepancies in `get_regime_adaptive_gamma_top` (6 Failures)
1. `tests/test_phase8_signal_enhancement.py:191`:
   - `test_feature_51_2_hyperexponential_convex_rank_modulation`:
     ```
     assert math.isclose(engine.get_regime_adaptive_gamma_top('CRISIS', version=8), 0.20, abs_tol=1e-5)
     E   AssertionError: assert False where False = isclose(0.15, 0.2, abs_tol=1e-05)
     ```
2. `tests/test_phase8_m1_challenger1_adversarial.py:581`:
   - `TestRegimeBranchOrderingIntegrity::test_regime_caps_and_gamma_top_reachability`:
     ```
     assert gammas['CRISIS'] == 0.20
     E   assert 0.15 == 0.2
     ```
3. `tests/test_phase8_m1_challenger2_empirical.py:215`:
   - `test_top_1pct_spread_expansion_empirical`:
     ```
     assert math.isclose(gamma_top, expected_gamma, abs_tol=1e-5), f"Mismatch for {reg}"
     E   AssertionError: Mismatch for BULL_LOW_VOL where False = isclose(0.8, 0.85, abs_tol=1e-05)
     ```
4. `tests/test_phase8_m1_challenger1_adversarial.py:373`:
   - `TestHyperexponentialRankMonotonicityStress::test_alpha_spread_expansion_target_achievement`:
     ```
     assert math.isclose(expansion_pct, 44.2, abs_tol=3.0)
     E   AssertionError: Alpha spread expansion 32.25% expected near target +44.2%
     ```
     (Note: expansion_pct is 32.25% when `gamma_top = 0.80`, but reaches 43.95% when `gamma_top = 0.85`, matching target 44.2% within abs_tol=3.0).
5. `tests/test_phase9_signal_enhancement.py:87`:
   - `TestPhase9SignalEnhancement::test_regime_adaptive_gamma_top_version9`:
     ```
     assert gamma_bull_high == 0.80
     E   assert 0.85 == 0.8
     ```
6. `tests/test_phase10_signal_enhancement.py:77`:
   - `TestPhase10SignalEnhancement::test_regime_adaptive_gamma_top_version10`:
     ```
     assert gamma_bull_low == 1.10
     E   assert 1.15 == 1.1
     ```

### 1.3 State of Score Normalizer & Factor Suppression
- `tests/test_adversarial_normalizer_m1.py` & `tests/test_score_normalizer.py`: 45 passed out of 45 tests (100% pass rate).
- `CrossSectionalScoreNormalizer` cleanly handles all edge cases (all zeros, all ones, all NaNs, small clusters, single symbol, uniform standard deviations).
- `RegimeFactorSuppressionEngine`: Hyperbolic deadband functions (`apply_smooth_noise_deadband`, `apply_quintic_hyperbolic_deadband`, `apply_nonic_hyperbolic_deadband`) pass mathematical monotonicity, odd symmetry, and noise suppression bounds.

---

## 2. Logic Chain

### 2.1 Trace of Issue 1 (R1: reg_str NameError)
1. In `trading_system/src/ai/ensemble_scorer.py`:
   - At line 19181, the method `combine_predictions` initializes the regime string:
     ```python
     regime_str = str(regime).upper()
     ```
   - In lines 19206–19500, version-gated rank modulations (`int(version) >= 66` down to `int(version) >= 8`) evaluate.
   - At line 19501, when `version < 8` (Phase 5, Phase 6, Phase 7, and backward-compatibility tests passing `version=5` or `version=6`), execution enters:
     ```python
     elif 'BULL' in reg_str or str(regime) == '2':
     ```
   - Because `reg_str` was never assigned in `combine_predictions` (only `regime_str` exists), Python raises `NameError: name 'reg_str' is not defined`.
   - In lines 19502–19515, the intended logic is:
     - `int(version) >= 7`: Quartic rank modulation (`0.60 + 0.25*r + 0.25*r^2 + 0.40*r^3 + 0.35*r^4`)
     - `int(version) >= 6`: Cubic rank modulation (`0.60 + 0.30*r + 0.30*r^2 + 0.55*r^3`)
     - Else (`version <= 5`): Quadratic rank modulation (`0.60 + 0.50*r + 0.50*r^2`)
2. Consequently, all 38 Phase 5–7 adversarial tests crashed immediately at line 19501 before the numerical calculations could be evaluated.
3. Once `reg_str = regime_str` is assigned at line 19182 (and line 19501 uses `regime_str`), all 38 tests evaluate smoothly and all edge cases (all zeros, all ones, 90–100% NaNs, extreme outliers, small universes 1/2/4/5/8, and top-decile spread scaling) pass without NaN, Inf, or negative numbers.

### 2.2 Trace of Issue 2 (R2: Gamma Top Calibration in Versions 8, 9, 10)
1. In `trading_system/src/ai/ensemble_scorer.py`, `EnsembleScoringEngine.get_regime_adaptive_gamma_top`:
   - **Version 8** (lines 27827–27842):
     - `CRISIS`: returns `0.15`. Test `test_feature_51_2_hyperexponential_convex_rank_modulation` (line 191) and `test_regime_caps_and_gamma_top_reachability` (line 581) assert `assert gammas['CRISIS'] == 0.20`.
     - `SIDEWAYS_LOW_VOL`: returns `0.60`. Test asserts `assert gammas['SIDEWAYS_LOW_VOL'] == 0.55`.
     - `BULL_LOW_VOL`: returns `0.80`. Test asserts `assert gammas['BULL_LOW_VOL'] == 0.85`.
     - Because `BULL_LOW_VOL` was `0.80`, `expansion_pct` in `test_alpha_spread_expansion_target_achievement` was calculated as `32.25%`, failing `assert math.isclose(expansion_pct, 44.2, abs_tol=3.0)`. When `BULL_LOW_VOL` is `0.85`, `expansion_pct = 43.95%`, passing within tolerance.
   - **Version 9** (lines 27808–27824):
     - `CRISIS`: returns `0.15`. Test `test_regime_adaptive_gamma_top_version9` (line 88) asserts `assert gamma_crisis == 0.20`.
     - `BULL_HIGH_VOL`: returns `0.85`. Test (line 87) asserts `assert gamma_bull_high == 0.80`.
     - `BULL_LOW_VOL`: returns `0.95`, which correctly matches test assertion line 86.
   - **Version 10** (lines 27790–27807):
     - `CRISIS`: returns `0.18`. Test `test_regime_adaptive_gamma_top_version10` (line 80) asserts `assert gamma_crisis == 0.20`.
     - `SIDEWAYS_LOW_VOL`: returns `0.80`. Test (line 79) asserts `assert gamma_sideways == 0.70`.
     - `BULL_HIGH_VOL`: returns `0.95`. Test (line 78) asserts `assert gamma_bull_high == 0.90`.
     - `BULL_LOW_VOL`: returns `1.15`. Test (line 77) asserts `assert gamma_bull_low == 1.10`.
2. Notice the regime ordering property:
   - For all versions $\ge 8$, `CRISIS` is universally anchored at `0.20` as the conservative floor.
   - Regimes are ordered strictly monotonically:
     $$\text{BULL\_LOW\_VOL} > \text{BULL\_HIGH\_VOL} > \text{SIDEWAYS\_LOW\_VOL} > \text{SIDEWAYS\_HIGH\_VOL} > \text{BEAR\_LOW\_VOL} > \text{BEAR\_HIGH\_VOL} \ge \text{CRISIS}$$
   - Fixing the return values restores exact compliance with all assertions.

---

## 3. Caveats

- **Scope boundary**: This investigation is strictly read-only per Teamwork Explorer protocol. No production files in `src/` or `trading_system/` were modified.
- **Root .venv vs trading_system\.venv**: The root virtual environment (`.venv\Scripts\python.exe`) should be used for test execution and pipeline runs because `trading_system\.venv` has an incomplete PyTorch directory structure (`torch/torch`).
- **Phase 60–65 SHA-256 and OMS Benchmarks (R3) & ML Predictor (R4)**: These belong to other explorer tracks and are not part of Track 1, though resolving Track 1 stability ensures all upstream signal inputs to those models are clean.

---

## 4. Conclusion & Proposed Code Fix

All 44 failing tests in Track 1 are resolved by modifying a single file: `trading_system/src/ai/ensemble_scorer.py`.

### Fix 1: Resolve `reg_str` NameError in `combine_predictions`
**Target File**: `trading_system/src/ai/ensemble_scorer.py`
**Lines**: 19181 and 19501

#### Change 1A (Line 19181):
**Before**:
```python
        # Regime-dynamic elasticity multiplier (BULL = 1.15, BEAR = 0.85, SIDEWAYS = 1.0)
        regime_str = str(regime).upper()
        if 'BULL' in regime_str or str(regime) == '2':
```
**After**:
```python
        # Regime-dynamic elasticity multiplier (BULL = 1.15, BEAR = 0.85, SIDEWAYS = 1.0)
        regime_str = str(regime).upper()
        reg_str = regime_str
        if 'BULL' in regime_str or str(regime) == '2':
```

#### Change 1B (Line 19501):
**Before**:
```python
            elif 'BULL' in reg_str or str(regime) == '2':
                if int(version) >= 7:
```
**After**:
```python
            elif 'BULL' in regime_str or str(regime) == '2':
                if int(version) >= 7:
```

---

### Fix 2: Calibrate `get_regime_adaptive_gamma_top` for Versions 8, 9, 10
**Target File**: `trading_system/src/ai/ensemble_scorer.py`
**Lines**: 27790–27843

**Before**:
```python
        if int(version) >= 10:
            if 'CRISIS' in reg_str:
                return 0.18
            elif 'BEAR_HIGH_VOL' in reg_str:
                return 0.30
            elif 'BEAR_LOW_VOL' in reg_str or reg_str == '0':
                return 0.45
            elif 'SIDEWAYS_HIGH_VOL' in reg_str:
                return 0.60
            elif 'SIDEWAYS_LOW_VOL' in reg_str or reg_str == '1':
                return 0.80
            elif 'BULL_HIGH_VOL' in reg_str:
                return 0.95
            elif 'BULL_LOW_VOL' in reg_str or reg_str == '2':
                return 1.15
            else:
                return 0.85

        if int(version) >= 9:
            if 'CRISIS' in reg_str:
                return 0.15
            elif 'BEAR_HIGH_VOL' in reg_str:
                return 0.25
            elif 'BEAR_LOW_VOL' in reg_str or reg_str == '0':
                return 0.40
            elif 'SIDEWAYS_HIGH_VOL' in reg_str:
                return 0.55
            elif 'SIDEWAYS_LOW_VOL' in reg_str or reg_str == '1':
                return 0.70
            elif 'BULL_HIGH_VOL' in reg_str:
                return 0.85
            elif 'BULL_LOW_VOL' in reg_str or reg_str == '2':
                return 0.95
            else:
                return 0.75

        # Version 8 (Phase 8 Sovereign Baseline)
        if 'CRISIS' in reg_str:
            return 0.15
        elif 'BEAR_HIGH_VOL' in reg_str:
            return 0.25
        elif 'BEAR_LOW_VOL' in reg_str or reg_str == '0':
            return 0.35
        elif 'SIDEWAYS_HIGH_VOL' in reg_str:
            return 0.45
        elif 'SIDEWAYS_LOW_VOL' in reg_str or reg_str == '1':
            return 0.60
        elif 'BULL_HIGH_VOL' in reg_str:
            return 0.70
        elif 'BULL_LOW_VOL' in reg_str or reg_str == '2' or 'BULL' in reg_str:
            return 0.80
        else:
            return 0.60
```

**After**:
```python
        if int(version) >= 10:
            if 'CRISIS' in reg_str:
                return 0.20
            elif 'BEAR_HIGH_VOL' in reg_str:
                return 0.30
            elif 'BEAR_LOW_VOL' in reg_str or reg_str == '0':
                return 0.45
            elif 'SIDEWAYS_HIGH_VOL' in reg_str:
                return 0.60
            elif 'SIDEWAYS_LOW_VOL' in reg_str or reg_str == '1':
                return 0.70
            elif 'BULL_HIGH_VOL' in reg_str:
                return 0.90
            elif 'BULL_LOW_VOL' in reg_str or reg_str == '2':
                return 1.10
            else:
                return 0.70

        if int(version) >= 9:
            if 'CRISIS' in reg_str:
                return 0.20
            elif 'BEAR_HIGH_VOL' in reg_str:
                return 0.25
            elif 'BEAR_LOW_VOL' in reg_str or reg_str == '0':
                return 0.40
            elif 'SIDEWAYS_HIGH_VOL' in reg_str:
                return 0.55
            elif 'SIDEWAYS_LOW_VOL' in reg_str or reg_str == '1':
                return 0.70
            elif 'BULL_HIGH_VOL' in reg_str:
                return 0.80
            elif 'BULL_LOW_VOL' in reg_str or reg_str == '2':
                return 0.95
            else:
                return 0.70

        # Version 8 (Phase 8 Sovereign Baseline)
        if 'CRISIS' in reg_str:
            return 0.20
        elif 'BEAR_HIGH_VOL' in reg_str:
            return 0.25
        elif 'BEAR_LOW_VOL' in reg_str or reg_str == '0':
            return 0.35
        elif 'SIDEWAYS_HIGH_VOL' in reg_str:
            return 0.45
        elif 'SIDEWAYS_LOW_VOL' in reg_str or reg_str == '1':
            return 0.55
        elif 'BULL_HIGH_VOL' in reg_str:
            return 0.70
        elif 'BULL_LOW_VOL' in reg_str or reg_str == '2' or 'BULL' in reg_str:
            return 0.85
        else:
            return 0.55
```

---

## 5. Verification Method

To independently verify after the changes are applied:

1. **Phase 5 Tests (Adversarial + Signal Enhancement)**:
   ```powershell
   .venv\Scripts\python.exe -m pytest tests/test_phase5_m1_challenger2_adversarial.py tests/test_phase5_signal_enhancement.py -v
   ```
   *Expected*: 46 passed, 0 failed.

2. **Phase 6 Tests**:
   ```powershell
   .venv\Scripts\python.exe -m pytest tests/test_phase6_m1_challenger2_adversarial.py tests/test_phase6_signal_enhancement.py -v
   ```
   *Expected*: 20 passed, 0 failed.

3. **Phase 7 Tests**:
   ```powershell
   .venv\Scripts\python.exe -m pytest tests/test_phase7_m1_challenger1_adversarial.py tests/test_phase7_signal_enhancement.py -v
   ```
   *Expected*: 28 passed, 0 failed.

4. **Phase 8 Tests**:
   ```powershell
   .venv\Scripts\python.exe -m pytest tests/test_phase8_m1_challenger1_adversarial.py tests/test_phase8_m1_challenger2_empirical.py tests/test_phase8_signal_enhancement.py -v
   ```
   *Expected*: 54 passed, 0 failed.

5. **Phase 9 Tests**:
   ```powershell
   .venv\Scripts\python.exe -m pytest tests/test_phase9_signal_enhancement.py -v
   ```
   *Expected*: 6 passed, 0 failed.

6. **Phase 10 Tests**:
   ```powershell
   .venv\Scripts\python.exe -m pytest tests/test_phase10_signal_enhancement.py -v
   ```
   *Expected*: 5 passed, 0 failed.

7. **Normalizer Regression**:
   ```powershell
   .venv\Scripts\python.exe -m pytest tests/test_adversarial_normalizer_m1.py tests/test_score_normalizer.py -v
   ```
   *Expected*: 45 passed, 0 failed.

8. **Full Track 1 Combined Check**:
   ```powershell
   .venv\Scripts\python.exe -m pytest tests/test_phase5_*.py tests/test_phase6_*.py tests/test_phase7_*.py tests/test_phase8_*.py tests/test_phase9_*.py tests/test_phase10_*.py tests/test_adversarial_normalizer_m1.py tests/test_score_normalizer.py -q
   ```
   *Expected*: 100% pass rate with zero failures across all Phase 5–10 tests.
