# Comprehensive Quality & Adversarial Review Report (Reviewer 2)

- **Review Target**: `system_improvement_plan_v8.md` (37-Strategy Trading System Improvement Plan v8)
- **Reviewer**: Reviewer 2 (Roles: Quality Reviewer, Adversarial Critic)
- **Date**: 2026-09-03
- **Repository**: `d:\Finance\code\stock`
- **Verdict**: 🛑 **REQUEST_CHANGES** (Actionable Engineering Revisions Required)

---

## Executive Summary & Verdict Rationale

`system_improvement_plan_v8.md` is an exceptionally comprehensive, rigorous, and technically sophisticated document that correctly identifies **13 critical flaws, 16 high-priority flaws, and 14 medium-priority flaws** across the 37-strategy pipeline. The plan demonstrates profound quantitative domain expertise in detecting:
- **CRIT-01**: US stock sizing missing FX rate division (1,350x leverage blowup).
- **CRIT-02**: Black-Litterman 20-day return view vs. daily covariance scale divergence (100x linear utility collapse).
- **CRIT-03**: Strict Causal LSTM global normalization lookahead leakage.
- **CRIT-04**: RIM valuation Ohlson ROE decay loop missing update.
- **CRIT-05**: Strategies 32~37 score omission from SQLite database tables and INSERT queries.
- **CRIT-06**: UnifiedPortfolioAllocator CVaR solver infeasibility for small universes ($N \le 4$).
- **CRIT-07**: USD account KRW 50,000 threshold deadlock in rebalancing.
- **CRIT-08**: CrisisDetector stateless initialization in `run_pipeline.py`.
- **CRIT-09**: `.dropna()` on 37 strategies silently disabling Löwdin orthogonalization.
- **CRIT-10**: DarkPool adapter instantiating Microstructure engine (100% duplicate).
- **CRIT-11**: ZCA whitening missing PC1 consensus alpha preservation code.
- **CRIT-12**: CARD factor double-negative sign on OLS VIX shock.
- **CRIT-13**: Annual 12M financial reports 90-day filing lag missing.
- **HIGH-01**: Active unit test failure in `tests/test_institutional_portfolio_construction.py:193`.

### Why the Verdict is REQUEST_CHANGES:
Despite the plan's outstanding diagnostic accuracy, the document claims to be **"Approved for Implementation (즉시 실행 가능한 엔지니어링 마스터 플랜)"**. In an adversarial audit of the proposed code changes against the existing codebase (1,900+ tests in `tests/`), **two Critical Signature/Type Discrepancies** and **two Major Test Specification Defects** were uncovered:

1. **[CRITICAL] CRIT-01 Method Signature & Calling Convention Breakage**:
   The plan proposes replacing `allocate()` in `unified_portfolio_allocator.py` with a signature that does not match the actual method (`(predictions_df, prices_dict, ...)` vs proposed `(df_candidates, returns_history, ...)`). If implemented as written, callers (`run_pipeline.py:4044` and `test_institutional_portfolio_construction.py:176`) will immediately crash with `TypeError: allocate() got an unexpected keyword argument 'predictions_df'`.
2. **[CRITICAL] CRIT-02 Signature Mutation, Type Inversion, and Backward-Incompatible View Normalization**:
   The plan changes `calculate_black_litterman_weights` in `portfolio_optimizer.py` from returning `np.ndarray` to returning `pd.Series`, replaces existing parameters (`prior_weights, omega_scale, meta_convictions, regime`), and forces `returns_are_percentage: bool = True`. This breaks over 10 existing test files and modules that expect `np.ndarray`. Specifically, existing test `tests/test_adversarial_challenger_1.py:320-328` (`test_percentage_vs_decimal_view_scale_alignment`) passes decimal views `[0.05, 0.08, 0.12]` without `returns_are_percentage=False`; under the plan's proposed code, it will divide decimal views by 100, causing an immediate regression test failure.
3. **[MAJOR] HIGH-01 Active Failure Remediation Checklist Incompleteness**:
   In `test_institutional_portfolio_construction.py:190-196`, line 193 is `assert p_krx["lot_size"] == 10` and line 194 is `assert p_krx["shares"] % 10 == 0`. The plan updates line 194 in code snippet lines 789-794, but throughout the roadmap checklists (lines 1480, 1536, 1583, 1610, 1632) it only instructs fixing line 193. If an implementer follows the checklists, line 194 will immediately fail.
4. **[MAJOR] Phantom / Non-Existent Test File Paths**:
   The plan references non-existent test files (`tests/test_rim_valuation.py`, `tests/test_portfolio_optimizer.py`, `tests/test_factor_suppression.py`, `tests/test_card_factor.py`) rather than the actual test suites in the repository (`tests/test_rim_strategy.py`, `tests/test_portfolio_optimizer_and_oms.py`, etc.).

---

## Detailed Audit Findings

### Audit Focus 1: Backward Compatibility & Test Suite Integrity

#### Finding 1.1 [Critical]: CRIT-01 Concrete Code Signature Inconsistency with `UnifiedPortfolioAllocator.allocate`
- **Location in Plan**: `system_improvement_plan_v8.md:118-128`
- **Location in Codebase**: `trading_system/src/risk/unified_portfolio_allocator.py:371-380`, `trading_system/run_pipeline.py:4044-4051`
- **Observation**:
  - Codebase signature:
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
  - Plan's proposed snippet:
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
  - In addition, `latest_prices` is built internally inside `allocate()` at lines 479-488 from `prices_dict`, so passing it from outside is both redundant and contradictory.
- **Impact**: If a developer replaces the signature as proposed, the entire pipeline and test suite will fail on import/call.
- **Required Fix**: Update the plan's concrete code snippet to preserve the exact existing signature and add `usdkrw_rate: float = 1350.0` as an optional keyword parameter:
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
      usdkrw_rate: float = 1350.0,  # V8 Fix
  ) -> pd.DataFrame:
  ```

#### Finding 1.2 [Critical]: CRIT-02 `calculate_black_litterman_weights` Signature Mutation & Test Regression
- **Location in Plan**: `system_improvement_plan_v8.md:208-264`
- **Location in Codebase**: `trading_system/src/analysis/portfolio_optimizer.py:143-155`
- **Observation**:
  - Codebase signature:
    ```python
    def calculate_black_litterman_weights(
        cov_matrix: np.ndarray,
        predicted_returns: np.ndarray,
        prior_weights: np.ndarray | None = None,
        risk_aversion: float = 2.5,
        tau: float = 0.05,
        omega_scale: float = 0.1,
        risk_free_rate: float = 0.02,
        meta_convictions: np.ndarray | None = None,
        symbols: Optional[list] = None,
        sectors: Optional[list] = None,
        regime: Optional[Any] = None,
    ) -> np.ndarray:
    ```
  - The plan changes this to return `pd.Series`, discards `prior_weights, omega_scale, meta_convictions, regime`, and adds `market_caps, view_confidence, max_single_stock_weight, max_sector_weight`.
  - Over 10 test files (`test_adversarial_challenger_1.py`, `test_black_litterman.py`, `test_challenger_portfolio_stress.py`, etc.) and modules (`unified_portfolio_allocator.py:204`, `position_sizing.py:623`, `asset_allocation.py:253`) call this function expecting an `np.ndarray`.
  - Furthermore, in `tests/test_adversarial_challenger_1.py:320-328`:
    ```python
    views_pct = [5.0, 8.0, 12.0]     # Percentage units
    views_dec = [0.05, 0.08, 0.12]   # Decimal units
    w_pct = calculate_black_litterman_weights(cov, views_pct)
    w_dec = calculate_black_litterman_weights(cov, views_dec)
    assert np.allclose(w_pct, w_dec, atol=1e-3)
    ```
    The plan proposes:
    ```python
    if returns_are_percentage:
        Q_decimal = Q / 100.0
    else:
        Q_decimal = Q.copy()
    ```
    Because `returns_are_percentage` defaults to `True`, `w_dec` will divide `[0.05, 0.08, 0.12]` by 100, resulting in `[0.0005, 0.0008, 0.0012]`, causing `test_percentage_vs_decimal_view_scale_alignment` to fail!
- **Impact**: Severe backward compatibility breakage across multiple existing test suites and optimization callers.
- **Required Fix**:
  1. Retain `np.ndarray` return type.
  2. Keep all existing parameters (`prior_weights`, `omega_scale`, `meta_convictions`, `regime`) intact.
  3. Add `view_horizon: int = 20` and `returns_are_percentage: Optional[bool] = None`.
  4. If `returns_are_percentage is None`, retain the dynamic unit normalization (`if np.nanmean(np.abs(Q)) > 0.50: Q = Q / 100.0`) so both percentage and decimal view inputs continue to produce identical weights.

#### Finding 1.3 [Major]: HIGH-01 Active Failure Remediation Checklist Incompleteness
- **Location in Plan**: Lines 789-794 vs lines 1480, 1536, 1583, 1610, 1632
- **Location in Codebase**: `tests/test_institutional_portfolio_construction.py:190-196`
- **Observation**:
  - The live test execution currently fails:
    `FAILED tests/test_institutional_portfolio_construction.py::TestUnifiedPortfolioAllocatorEndToEnd::test_end_to_end_allocate`
    `assert p_krx["lot_size"] == 10`
    `E   assert 1 == 10`
  - In lines 789-794, the plan correctly shows updating both lines 193 and 194:
    ```python
    assert p_krx["lot_size"] == 1
    assert p_krx["shares"] >= 0  # Replaces assert p_krx["shares"] % 10 == 0
    ```
  - However, in all summary checklists (Phase 1 summary line 1480, Phase 1 details line 1536, Verification matrix line 1583, Scorecard line 1610, Checklist line 1632), the text only states: `line 193 KRX 1주 규격 단언 수정 (assert 1 == 10 -> assert 1 == 1)`.
  - If a developer updates only line 193, line 194 (`assert p_krx["shares"] % 10 == 0`) will fail whenever `raw_shares` is not a multiple of 10.
- **Required Fix**: Explicitly state across all checklists that lines 193 AND 194 must both be updated.

#### Finding 1.4 [Major]: Phantom Test File References in Verification Plan
- **Location in Plan**: Lines 271, 380, 1019, 1586, 1593
- **Observation**:
  - `tests/test_rim_valuation.py` does not exist (actual: `tests/test_rim_strategy.py`).
  - `tests/test_portfolio_optimizer.py` does not exist (actual: `tests/test_portfolio_optimizer_and_oms.py`).
  - `tests/test_factor_suppression.py` does not exist (actual: `tests/test_correlation_suppression.py`).
  - `tests/test_card_factor.py` does not exist (actual: `tests/test_phase2_quant_world_class_improvements.py`).
- **Required Fix**: Update all test references in the plan to specify the actual existing test file or explicitly state that a new test file will be created.

---

### Audit Focus 2: Execution Safety & Operational Robustness

| Component | Audit Check | Plan Assessment | Status |
|---|---|---|---|
| **Gate 1~7 Safety Gates** | Capital limits, liquidity checks, min trading hurdles | Properly preserved; no regressions introduced. | ✅ Robust |
| **Gate 8 Inverse Hedge** | Multi-market hedge allocation (`HIGH-03`) | Plan correctly resolves the single-market #1 pick bias by splitting KRX (`114800`) and US (`SH`/`PSQ`) proportionally. | ✅ Excellent |
| **Foreign Asset Sizing** | Currency conversion in share calculation (`CRIT-01`) | Concept is 100% correct; solves 1,350x over-allocation. (Must align method signature). | ⚠️ Needs Signature Fix |
| **USD Buffer Bands** | Rebalancing deadlock in USD accounts (`CRIT-07`) | Plan correctly adds account currency detection, replacing 50,000 KRW with $50 USD. | ✅ Robust |
| **Slippage Feedback** | Outlier resistance and parameter stability (`HIGH-04`) | Plan applies Bayesian shrinkage $\frac{N}{N+10}\text{slip} + \frac{10}{N+10}\text{default}$, preventing 8.0x blowout on $N=1$. | ✅ Excellent |
| **Almgren-Chriss Slicing** | Remainder subtraction clamping (`MED-13`) | Reverse iteration loop prevents negative slice counts. | ✅ Robust |

---

### Audit Focus 3: Actionability & Roadmapping

#### Finding 3.1: Cross-Phase File Churn & Coupling Risks
The 3-phase roadmap is organized by defect priority (Critical $\to$ High $\to$ Medium), but this creates high file churn across phases:
- `ensemble_scorer.py`: modified in Day 1 (CRIT-09), Day 2 (HIGH-09, HIGH-10, HIGH-11), Day 3 (MED-10).
- `unified_portfolio_allocator.py`: modified in Day 1 (CRIT-01, CRIT-06), Day 2 (HIGH-16).
- `risk_manager.py`: modified in Day 1 (CRIT-08), Day 3 (MED-11).
- `database.py`: modified in Day 2 (HIGH-13), Day 3 (MED-01).

#### Finding 3.2: Logical Dependency Misalignment
- **CRIT-08 & MED-11**: Modifying `CrisisDetector` in Phase 1 for state persistence, then re-opening it in Phase 3 for VIX backwardation, creates redundant testing. `MED-11` should be implemented alongside `CRIT-08`.
- **CRIT-05 & MED-07**: `CRIT-05` adds DB columns for Strategies 32~37 in Phase 1, but `coverage_analyzer.py` mapping (`MED-07`) is deferred to Phase 3, leading to unmapped missingness reasons in `strategy_data_coverage_report.txt` during Phase 1 & 2.

---

## Required Remediation Actions for Approval

To achieve `APPROVE`, `system_improvement_plan_v8.md` must incorporate the following revisions:

1. **Fix CRIT-01 Concrete Implementation**:
   Align the `allocate()` signature in `unified_portfolio_allocator.py` with its actual definition:
   `(self, predictions_df, prices_dict, total_portfolio_value=100_000_000.0, regime="BULL_LOW_VOL", current_holdings=None, sector_map=None, top_n=20, usdkrw_rate: float = 1350.0)`.
2. **Fix CRIT-02 Signature and Scale-Handling**:
   - Retain `np.ndarray` as return type and keep `prior_weights, omega_scale, meta_convictions, regime`.
   - Preserve dynamic percentage/decimal view detection when `returns_are_percentage` is not explicitly specified, ensuring `test_adversarial_challenger_1.py:320-328` continues to pass.
3. **Update HIGH-01 Checklists**:
   Explicitly specify updating both line 193 (`lot_size == 1`) and line 194 (`shares >= 0`) across all checklist tables.
4. **Correct Test File Paths**:
   Change `tests/test_rim_valuation.py` $\to$ `tests/test_rim_strategy.py`, `tests/test_portfolio_optimizer.py` $\to$ `tests/test_portfolio_optimizer_and_oms.py`, etc., or explicitly label newly proposed test files.
5. **Optimize Roadmap Bundling**:
   Group tightly coupled fixes (e.g., `CRIT-08` + `MED-11`, `CRIT-05` + `MED-07`) into the same phase to prevent redundant code churn.
