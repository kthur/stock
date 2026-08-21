# Forensic Integrity Audit Report: V5.0 (V5-01 ~ V5-32)

**Auditor**: Forensic Auditor 1 (.agents/teamwork_preview_auditor_1/)
**Target Work Product**: trading_system/ Full Codebase (Tasks V5-01 through V5-32)
**Integrity Mode**: Demo Mode (Strict Forensic Standard)
**Date**: 2026-08-21 (KST)
**Authoritative Verdict**: INTEGRITY VIOLATION (REJECTED)

---

## Executive Summary

An exhaustive forensic integrity audit was conducted across all 32 tasks (V5-01 ~ V5-32) defined in system_improvement_report_v5.md and mandated by ORIGINAL_REQUEST.md.

### Forensic Check Summary:
1. Hardcoded Test Results / Static Mocks: PASS (Zero hardcoded symbol checks or mock bypasses detected).
2. Facade Implementations: PASS (Genuine mathematical models implemented across all modules).
3. Algorithmic Authenticity: PASS (29 of 32 tasks implemented with authentic numerical formulations).
4. Behavioral & Runtime Verification: FAIL (Test execution failed with 3 failing tests: 2 runtime NameError crashes in core strategy execution and 1 regression test type assertion).

Under the forensic integrity rule ('If ANY check fails, the verdict is INTEGRITY VIOLATION and the work product MUST be rejected'), the work product is rejected until the runtime defects are rectified.

---

## 1. Observation

### 1.1 Verbatim Runtime Test Failures (3 Failing Tests out of 1,242)

Full regression suite execution (.venv/Scripts/python.exe -m pytest tests/ -q) yielded 3 failures:

1. V5-16 short_interest_squeeze.py (line 116):
   NameError: name 'ret_20d' is not defined in calculate_scores()
   ret_20d was referenced on line 116 without being defined from c_series.

2. V5-20 event_driven.py (line 249):
   NameError: name 'item' is not defined in evaluate_cb_bw_overhang_and_margin_risk()
   The 'for item in eff_filings:' loop header was omitted after 'if eff_filings:'.

3. V5-31 config.py (tests/test_config.py:46):
   AssertionError: 20 != '20'
   V5-31 converted train_sample_sp500 to integer, breaking legacy string assertion.

---

## 2. Logic Chain

1. Examined all 32 task implementations across 15 core files. Domain 1 (V5-01~06), Domain 2 (V5-07~12), Domain 4 (V5-24~25), Domain 5 (V5-32) are 100% verified and authentic.
2. In Domain 3, Worker M3 introduced two syntax/runtime bugs in short_interest_squeeze.py and event_driven.py.
3. The delivery of broken code that crashes during execution violates the Acceptance Criteria (R2: 100% test pass rate).
4. Therefore, the authoritative verdict is INTEGRITY VIOLATION.

---

## 3. Caveats

- No malicious intent: the violation is strictly due to runtime syntax bugs (unbound variables), not mocking.
- 29/32 tasks are completely clean and verified.
- Remediation requires exactly 2 lines in short_interest_squeeze.py and 1 line in event_driven.py.

---

## 4. Conclusion

- Authoritative Verdict: INTEGRITY VIOLATION (REJECTED)
- Required Remediation:
  1. In short_interest_squeeze.py: Define ret_20d before computing proxy_score.
  2. In event_driven.py: Add 'for item in eff_filings:' on line 249.
  3. In test_config.py: Update assertion to integer 20.

---

## 5. Verification Method

`ash
.venv/Scripts/python.exe -m pytest tests/test_new_27_strategies.py::test_short_interest_squeeze_engine -v
.venv/Scripts/python.exe -m pytest tests/test_phase3_improvements.py::test_cb_bw_overhang_and_margin_risk_sandbox -v
.venv/Scripts/python.exe -m pytest tests/test_config.py::TestTradingConfig::test_env_overrides -v
`

## 6. Comprehensive 32-Task Master Status Table

| # | Domain | Severity | Issue | Root Cause | Remedy | Audit Status |
|---|---|---|---|---|---|---|
| **V5-01** | Domain 1: AI/ML | CRITICAL | PCA-ZCA Whitening Variance Explosion (N < K) | Zero eigenvalue clamping to 1e-6 produced 1000x amplification | Continuous ridge floor applied | VERIFIED CLEAN |
| **V5-02** | Domain 1: AI/ML | HIGH | WLS Weighting Distortion & .loc KeyError | B^T W^(1/2) B normal equation distortion | .reindex() and B_weighted^T B_weighted applied | VERIFIED CLEAN |
| **V5-03** | Domain 1: AI/ML | HIGH | CLUSTER_MAP Strategy Alias Mismatch | Active pipeline aliases fell back to OTHER | Added canonical mappings for rim, value_up, vcp, etc. | VERIFIED CLEAN |
| **V5-04** | Domain 1: AI/ML | HIGH | Sharpe Weight Bounding Floor Disconnected | _vmin_floor computed but omitted from comprehension | Integrated max(v, _vmin_floor, ...) into dict | VERIFIED CLEAN |
| **V5-05** | Domain 1: AI/ML | HIGH | Optuna VCP 4 Hyperparameters Disconnected | Sampled parameters unused in evaluation loop | Connected vol_dec_th, min_vcp_sc, dec_wt, vol_wt | VERIFIED CLEAN |
| **V5-06** | Domain 1: AI/ML | CRITICAL | Platt Scaling Domain Logit Collapse | Applied logit(p) to [0, 1] fitted model | Aligned linear domain z = coef * p + intercept | VERIFIED CLEAN |
| **V5-07** | Domain 2: Risk | HIGH | BL View Scale & Negative Return Quadratic Utility | 100x scale mismatch and Sharpe maximization on negative return | Scale auto-detect + Quadratic Utility on port_ret <= rf | VERIFIED CLEAN |
| **V5-08** | Domain 2: Risk | HIGH | Clayton Copula Non-PSD Distortion | Rank-1 11^T shift broke PSD on negative correlations | Eigendecomposition spectral projection (>= 1e-4) | VERIFIED CLEAN |
| **V5-09** | Domain 2: Risk | MEDIUM | Reverse Window Time Series CV Starvation | Reverse date indexing starved initial folds | Forward chronological expanding CV applied | VERIFIED CLEAN |
| **V5-10** | Domain 2: Risk | HIGH | HRP Zero-Variance Cluster Division-by-Zero | Zero-variance assets caused overflow and NaN | Volatility/variance floors (1e-4 / 1e-8) + alpha clip | VERIFIED CLEAN |
| **V5-11** | Domain 2: Risk | MEDIUM | TypeError on np.isnan(None) & Queue Desync | Unhandled types in ufunc and asymmetric queue appends | Type-safe isfinite check + synchronous forward-fill | VERIFIED CLEAN |
| **V5-12** | Domain 2: Risk | MEDIUM | Fundamental Schema Mismatch in Coverage | Checked raw names instead of engineered feature names | Added engineered column schema + aliases | VERIFIED CLEAN |
| **V5-13** | Domain 3: Strategy | CRITICAL | CARD Factor res_rows.append NameError | Uninitialized res_rows referenced | Replaced with scores[sym] = 0.5 | VERIFIED CLEAN |
| **V5-14** | Domain 3: Strategy | CRITICAL | Gamma Squeeze Missing **kwargs | Interface signature missing **kwargs | Added **kwargs and safe unpacking | VERIFIED CLEAN |
| **V5-15** | Domain 3: Strategy | CRITICAL | HFT Microstructure Empty DataFrame Default | Missing universe caused empty return | Synthesized universe from dict keys | VERIFIED CLEAN |
| **V5-16** | Domain 3: Strategy | CRITICAL | Short Squeeze Proxy Scale Inversion | 10-20x scale divergence vs explicit score | Normalized proxy score (ret_20d NameError found) | FAIL (NameError: ret_20d) |
| **V5-17** | Domain 3: Strategy | HIGH | Split-Runner Missing US Leader Alpha Inversion | Missing US leader data inverted alpha score | Return neutral score 0.5 on missing leader | VERIFIED CLEAN |
| **V5-18** | Domain 3: Strategy | HIGH | OBV Trend Slope Division-by-Zero | Zero cumulative volume denominator | 10-day volume sum denominator + max(., 1.0) | VERIFIED CLEAN |
| **V5-19** | Domain 3: Strategy | HIGH | RIM Distressed Companies Ranking Pollution | Ranked before NaN invalidation | Pre-invalidated discount_ratio to NaN | VERIFIED CLEAN |
| **V5-20** | Domain 3: Strategy | HIGH | DART 8-digit corp_code Direct Comparison | 8-digit corp_code compared with 6-digit ticker | zfill(6) ticker and corp_code mapping (for item bug) | FAIL (NameError: item) |
| **V5-21** | Domain 3: Strategy | HIGH | Factor Neutralizer Rank-Deficient Singular Matrix | Ill-conditioned design matrix failed QR | Ridge regression fallback (1e-4 eye) + pinv | VERIFIED CLEAN |
| **V5-22** | Domain 3: Strategy | HIGH | Stock Split Detector Severe Crash False Positive | >25% drops during crashes falsely flagged as splits | Standard split ratio + 1.25x volume confirmation | VERIFIED CLEAN |
| **V5-23** | Domain 3: Strategy | MEDIUM | Short-Term Reversal Lowercase KeyError | Fixed Close column check | Case-insensitive column search | VERIFIED CLEAN |
| **V5-24** | Domain 4: OMS | CRITICAL | Slippage Feedback TypeError & Dataclass Return | calculate_realized_slippage(sym) threw TypeError | *args, **kwargs signature + cost_scaling_factor unpack | VERIFIED CLEAN |
| **V5-25** | Domain 4: OMS | CRITICAL | Inverse ETF 10,000 KRW Hardcoding Under-Hedging | Hardcoded 10,000 KRW hedge price caused 80% under-hedging | _get_latest_price() dynamic price + exact lot sizing | VERIFIED CLEAN |
| **V5-26** | Domain 3: Strategy | MEDIUM | Options IV Skew Downside Semi-Variance Distortion | Calculated semi-variance around negative sample mean | Evaluated around zero return baseline | VERIFIED CLEAN |
| **V5-27** | Domain 3: Strategy | MEDIUM | Volatility Targeting Compressed Score Range | Score compressed in [0.212, 0.788] | Expanded dynamic score to [0.05, 0.95] | VERIFIED CLEAN |
| **V5-28** | Domain 3: Strategy | MEDIUM | Accruals Quality Single-Stock Boundary Collapse | N=1 failed percentile ranking | Dedicated N=1 neutral/bonus branch | VERIFIED CLEAN |
| **V5-29** | Domain 3: Strategy | MEDIUM | Discontinuous Piecewise Step Jumps Distortion | Step jumps distorted smooth ranking | Continuous tanh and sigmoid non-linear transforms | VERIFIED CLEAN |
| **V5-30** | Domain 3: Strategy | MEDIUM | Insider Buying Default Attribution Bias | Defaulted unknown filings to BUY | Explicit buy_keywords and sell_keywords matching | VERIFIED CLEAN |
| **V5-31** | Domain 3: Strategy | HIGH | Configuration String Type Pollution | Environment strings polluted integer config fields | Type conversions (int, str preservation) | TEST TYPE MISMATCH |
| **V5-32** | Domain 5: Pipeline | MEDIUM | 20-Day Market Return Scale Understatement | 0.0005 decimal return displayed as +0.001%/day | _compute_20d_ret_vol scale auto-detection (x100.0) | VERIFIED CLEAN |
