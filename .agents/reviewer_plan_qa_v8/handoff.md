# Handoff Report — Reviewer 2 (Plan QA v8)

- **Review Target**: `system_improvement_plan_v8.md`
- **Reviewer**: Reviewer 2 (Roles: Quality Reviewer, Adversarial Critic)
- **Date**: 2026-09-03
- **Verdict**: 🛑 **REQUEST_CHANGES**

---

## 1. Observation

1. **Active Test Suite Failure in `tests/test_institutional_portfolio_construction.py:193`**:
   - Command: `.venv\Scripts\python.exe -m pytest tests/test_institutional_portfolio_construction.py`
   - Result:
     ```
     FAILED tests/test_institutional_portfolio_construction.py::TestUnifiedPortfolioAllocatorEndToEnd::test_end_to_end_allocate
     tests\test_institutional_portfolio_construction.py:193: in test_end_to_end_allocate
         assert p_krx["lot_size"] == 10
     E   assert 1 == 10
     ========================= 1 failed, 7 passed in 9.64s =========================
     ```
   - Observed code in `tests/test_institutional_portfolio_construction.py:190-196`:
     ```python
     190:         # Lot sizes: KRX = 10, US = 1
     191:         p_krx = res[res["symbol"] == "005930"].iloc[0]
     192:         p_us = res[res["symbol"] == "AAPL"].iloc[0]
     193:         assert p_krx["lot_size"] == 10
     194:         assert p_krx["shares"] % 10 == 0
     195:         assert p_us["lot_size"] == 1
     ```

2. **CRIT-01 Concrete Implementation vs Actual Method Signature**:
   - In `system_improvement_plan_v8.md:118-128`:
     ```python
     def allocate(
         self,
         df_candidates: pd.DataFrame,
         returns_history: pd.DataFrame,
         total_portfolio_value: float,
         current_weights: Optional[Dict[str, float]] = None,
         market_regime: str = "NEUTRAL",
         macro_crisis_level: str = "NORMAL",
         latest_prices: Optional[List[float]] = None,
         usdkrw_rate: float = 1350.0,
     ) -> pd.DataFrame:
     ```
   - In `trading_system/src/risk/unified_portfolio_allocator.py:371-380`:
     ```python
     def allocate(
         self,
         predictions_df: pd.DataFrame,
         prices_dict: Dict[str, pd.DataFrame],
         total_portfolio_value: float = 100_000_000.0,
         regime: Optional[str] = "BULL_LOW_VOL",
         current_holdings: Optional[Dict[str, Dict[str, Any]]] = None,
         sector_map: Optional[Dict[str, str]] = None,
         top_n: int = 20,
     ) -> pd.DataFrame:
     ```
   - In `trading_system/run_pipeline.py:4044-4051`:
     ```python
     unified_alloc_df = unified_allocator.allocate(
         predictions_df=ensemble_df_merged,
         prices_dict=infer_data_dict,
         total_portfolio_value=getattr(cfg, 'portfolio_capital_krw', 100_000_000.0),
         regime=current_2d_regime if 'current_2d_regime' in locals() else "BULL_LOW_VOL",
         current_holdings=curr_holdings_dict,
         top_n=30
     )
     ```
   - `latest_prices` is not an external input; it is extracted dynamically inside `allocate()` at lines 479-487 from `prices_dict`.

3. **CRIT-02 Concrete Implementation vs Existing Codebase & Tests**:
   - In `system_improvement_plan_v8.md:208-222`:
     The plan redefines `calculate_black_litterman_weights` with return type `pd.Series` and parameters `(cov_matrix, predicted_returns, market_caps, risk_aversion, tau, view_confidence, risk_free_rate, symbols, sectors, max_single_stock_weight, max_sector_weight, view_horizon=20, returns_are_percentage=True)`.
   - In `trading_system/src/analysis/portfolio_optimizer.py:143-155`:
     The function signature is `(cov_matrix: np.ndarray, predicted_returns: np.ndarray, prior_weights=None, risk_aversion=2.5, tau=0.05, omega_scale=0.1, risk_free_rate=0.02, meta_convictions=None, symbols=None, sectors=None, regime=None) -> np.ndarray`.
   - In `tests/test_adversarial_challenger_1.py:320-328`:
     ```python
     views_pct = [5.0, 8.0, 12.0]     # Percentage units
     views_dec = [0.05, 0.08, 0.12]   # Decimal units
     w_pct = calculate_black_litterman_weights(cov, views_pct)
     w_dec = calculate_black_litterman_weights(cov, views_dec)
     assert np.allclose(w_pct, w_dec, atol=1e-3)
     ```
     Under the plan's proposed code, `returns_are_percentage: bool = True` divides `Q` by 100 unconditionally, so `views_dec` becomes `[0.0005, 0.0008, 0.0012]`, which causes `test_percentage_vs_decimal_view_scale_alignment` to fail.

4. **Phantom Test File Names in Plan**:
   - `tests/test_rim_valuation.py` cited in line 380 and line 1586 does not exist; actual test file is `tests/test_rim_strategy.py`.
   - `tests/test_portfolio_optimizer.py` cited in line 271 does not exist; actual test file is `tests/test_portfolio_optimizer_and_oms.py`.
   - `tests/test_factor_suppression.py` cited in line 1019 does not exist; actual test file is `tests/test_correlation_suppression.py`.
   - `tests/test_card_factor.py` cited in line 1593 does not exist; actual tests are in `tests/test_phase2_quant_world_class_improvements.py`.

5. **OMS 8 Gates & Operational Safeguards**:
   - `HIGH-03` (Gate 8 inverse hedge multi-market split) is verified at `oms_engine.py:768-773`.
   - `HIGH-04` (Slippage feedback 8x explosion on single trade) is verified at `slippage_feedback.py:198-220` and `oms_engine.py:367`.
   - `CRIT-07` (USD 50,000 threshold deadlock) is verified at `turnover_optimizer.py:75` and `portfolio_allocator.py:1297-1301`.
   - `CRIT-08` (CrisisDetector stateless initialization) is verified at `run_pipeline.py:3698` and `risk_manager.py:142-188`.

---

## 2. Logic Chain

1. **Premise**: `system_improvement_plan_v8.md` claims to be an "Approved for Implementation" master engineering document whose concrete code and roadmaps can be executed directly by implementers.
2. **Observation -> Deduction (CRIT-01)**:
   - Observation 2 proves that the concrete code in CRIT-01 alters `UnifiedPortfolioAllocator.allocate` to an incompatible signature.
   - If an implementer applies this snippet, `run_pipeline.py:4044` and `test_institutional_portfolio_construction.py:176` will crash on execution.
   - Therefore, the plan currently introduces a critical regression in its own proposed implementation.
3. **Observation -> Deduction (CRIT-02)**:
   - Observation 3 proves that changing `calculate_black_litterman_weights` to return `pd.Series` breaks existing callers that expect `np.ndarray`.
   - Unconditionally setting `returns_are_percentage = True` breaks `tests/test_adversarial_challenger_1.py:320-328` by scaling decimal views down twice.
   - Therefore, CRIT-02 as written violates the 100% backward compatibility mandate.
4. **Observation -> Deduction (HIGH-01)**:
   - When KRX lot size is changed from 10 to 1, `raw_shares` is no longer a multiple of 10.
   - If only line 193 is changed to `assert p_krx["lot_size"] == 1`, line 194 (`assert p_krx["shares"] % 10 == 0`) will fail.
   - Because the plan's checklists only mention line 193, there is a high risk of partial implementation leaving the test failing.
5. **Observation -> Deduction (Phantom Files & Coupling)**:
   - Non-existent test file paths prevent automated verification.
   - Spreading modifications to `ensemble_scorer.py`, `unified_portfolio_allocator.py`, and `risk_manager.py` across Days 1, 2, and 3 introduces unnecessary code churn and regression risk.
6. **Conclusion**:
   - Because the plan is 90% brilliant in diagnosis but contains critical flaws in its concrete implementation snippets and checklists that would break the system if executed, the verdict must be **REQUEST_CHANGES** with specific remediation items.

---

## 3. Caveats

- No code in the repository was modified during this review (strict adherence to Reviewer role constraints).
- Live execution of the full 1,900+ test suite takes 15~20 minutes; targeted test execution was performed on affected suites (`test_institutional_portfolio_construction.py`, `test_black_litterman.py`, `test_adversarial_challenger_1.py`).
- The underlying mathematical and financial logic of all 43 issues is sound; the issues are strictly in the plan's concrete code specifications, backward compatibility guarantees, and file mapping.

---

## 4. Conclusion

- **Verdict**: 🛑 **REQUEST_CHANGES**
- **Required Changes**:
  1. Fix CRIT-01 snippet to preserve `UnifiedPortfolioAllocator.allocate` signature and add `usdkrw_rate: float = 1350.0`.
  2. Fix CRIT-02 snippet to return `np.ndarray`, retain all existing arguments, and maintain dynamic percentage/decimal view detection when unspecified.
  3. Update all HIGH-01 checklists to specify updating both line 193 (`lot_size == 1`) and line 194 (`shares >= 0`).
  4. Fix all phantom test file paths in the verification plan and matrix.
  5. Bundle coupled module fixes into coherent phases (e.g. `CRIT-08` + `MED-11`).

---

## 5. Verification Method

To verify whether the issues reported here have been rectified in an updated plan:
1. Inspect `system_improvement_plan_v8.md` lines 118-128 and confirm `UnifiedPortfolioAllocator.allocate` retains `predictions_df, prices_dict`.
2. Inspect `system_improvement_plan_v8.md` lines 208-264 and confirm `calculate_black_litterman_weights` returns `np.ndarray` and supports both decimal and percentage views.
3. Inspect `tests/test_institutional_portfolio_construction.py:190-196` and confirm both lines 193 and 194 are covered.
4. Run:
   ```bash
   .venv\Scripts\python.exe -m pytest tests/test_institutional_portfolio_construction.py
   .venv\Scripts\python.exe -m pytest tests/test_black_litterman.py tests/test_adversarial_challenger_1.py
   ```
5. Invalidation Condition: If the plan is implemented with the current snippet in CRIT-01, running `test_institutional_portfolio_construction.py` will fail with `TypeError`.
