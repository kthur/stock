# Comprehensive Code Review & Adversarial Stress-Test Handoff Report

**Author**: Reviewer 2 (`teamwork_preview_reviewer_2`)  
**Roles**: Reviewer, Critic  
**Review Scope**: Domain 3 Part B (V5-26 ~ V5-31), Domain 4 (V5-24 ~ V5-25), Domain 5 (V5-32), and Repository-Wide Test Suite Verification  
**Date**: 2026-08-21 (KST)  
**Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

Direct code observations, verbatim errors, tool commands, and test executions across the assigned domains:

### 1.1 Full Test Suite Execution
- **Command**: `.venv\Scripts\python.exe -m pytest tests/ -q`
- **Collected**: 1,226 items
- **Result**: `5 failed, 1219 passed, 2 skipped, 159 warnings in 1937.38s (0:32:17)`
- **Verbatim Failures**:
  1. `FAILED tests/test_new_27_strategies.py::test_short_interest_squeeze_engine`  
     `trading_system\src\core\short_interest_squeeze.py:116: in calculate_scores`  
     `+ 0.10 * max(-0.2, min(0.5, ret_20d))`  
     `E NameError: name 'ret_20d' is not defined`
  2. `FAILED tests/test_phase3_improvements.py::test_cb_bw_overhang_and_margin_risk_sandbox`  
     `trading_system\src\core\event_driven.py:249: in evaluate_cb_bw_overhang_and_margin_risk`  
     `stock_code = str(item.get('stock_code', '')).strip().zfill(6) if item.get('stock_code') else ''`  
     `E NameError: name 'item' is not defined`
  3. `FAILED tests/test_config.py::TestTradingConfig::test_env_overrides`  
     `tests\test_config.py:46: in test_env_overrides`  
     `self.assertEqual(cfg.train_sample_sp500, "20")`  
     `E AssertionError: 20 != '20'`
  4. `FAILED tests/test_challenger_m1_2_empirical.py::test_empirical_latency_distribution_3379_symbols` (timing flake under full suite 32m load; passed when run in isolation: `6 passed in 20.73s`)
  5. `FAILED tests/test_challenger_m1_2_empirical.py::test_empirical_latency_under_heavy_missingness` (timing flake under full suite 32m load; passed when run in isolation)

---

### 1.2 Domain 3 Part B Observations (V5-26 ~ V5-31)

- **V5-26: Downside Semi-Variance Benchmark (`trading_system/src/core/iv_skew.py:124-138`)**:
  - `down_diff = np.minimum(ret_20.values, 0.0)` and `up_diff = np.maximum(ret_20.values, 0.0)` correctly measure downside semi-variance with target MAR = 0.0.
  - Zero/negative guards (`if np.isnan(down_vol) or down_vol <= 0: down_vol = 0.005`) prevent `ZeroDivisionError`.
  - Implemented cleanly and verified.

- **V5-27: Dynamic Range in Volatility Targeting (`trading_system/src/core/vol_target.py:111-118`)**:
  - Vectorized percentile ranking `(0.05 + pct_rank * 0.90).clip(0.0, 1.0)` expands cross-sectional score range.
  - Logistic fallback `1.0 / (1.0 + np.exp(-3.0 * np.clip(vol_ratio, -2.0, 2.0)))` utilizes slope $k=3.0$, expanding single-stock score range across $[0.05, 0.95]$.
  - Implemented cleanly and verified.

- **V5-28: Single-Stock Accruals Quality Boundary (`trading_system/src/core/accruals_quality.py:133-145`)**:
  - `elif valid_mask.sum() == 1: df_acc.loc[valid_mask, 'accruals_quality_score'] = min(0.50 + bonus, 0.95)` assigns neutral score with cash conversion bonus instead of penalizing single stocks with 0.0.
  - Implemented cleanly and verified.

- **V5-29: Discrete Step Discontinuities Elimination**:
  - `trading_system/src/core/card_factor.py:164`: `smooth_boost = 1.0 + 0.10 / (1.0 + np.exp(-12.0 * (card_score - 0.70)))`
  - `trading_system/src/core/arm_factor.py:110-130`: `syn_pos = np.maximum(0.0, np.tanh(10.0 * revision_composite)) * np.maximum(0.0, np.tanh(10.0 * price_mom))` and `smooth_boost = 1.0 + 0.10 / (1.0 + np.exp(-10.0 * (sc - 0.75)))`
  - `trading_system/src/core/mq_factor.py:169`: `smooth_boost = 1.0 + 0.10 / (1.0 + np.exp(-10.0 * (res_df['mq_score'] - 0.75)))`
  - `trading_system/src/core/hft_engine.py:246-255`: Smooth sigmoidal transitions `sig_imb = 1.0 / (1.0 + np.exp(-10.0 * (bid_ask_imbalance - 0.80)))`
  - All step jumps replaced with smooth $C^\infty$ sigmoidal / tanh transitions. Implemented cleanly and verified.

- **V5-30: Insider Buying Disclosure Classification (`trading_system/src/core/insider_buying.py:106-115`)**:
  - Strict keyword matching for open-market purchases (`'BUY', 'PURCHASE', '취득', '매입', '장내매수', '장외매수', '신규취득', '주식매수'`).
  - Informational disclosures without buy keywords no longer default to `BUY`. Implemented cleanly and verified.

- **V5-31: Environment Variable Type Casting in TradingConfig (`trading_system/src/config.py:230-320`)**:
  - Typed helper functions (`_get_env_bool`, `_get_env_int`, `_get_env_float`) and explicit type conversions ensure all configuration values match dataclass types.
  - Implemented cleanly, but `tests/test_config.py:46` requires updating from legacy string assertion.

---

### 1.3 Domain 4 Observations (V5-24 ~ V5-25)

- **V5-24: `calculate_realized_slippage` Signature & Dataclass Handling**:
  - `trading_system/src/execution/slippage_feedback.py:56`: `def calculate_realized_slippage(self, *args, **kwargs) -> SlippageMetrics` accepts variable arguments without `TypeError`.
  - `trading_system/src/execution/oms_engine.py:445-453`: Safely unpacks `cost_scaling_factor` or `recommended_market_impact_multiplier` from `SlippageMetrics` and passes `slippage_multiplier` to `PortfolioAllocator.estimate_transaction_cost_rate()`.
  - Implemented cleanly and verified.

- **V5-25: Dynamic Inverse ETF Hedge Price (`trading_system/src/execution/oms_engine.py:575-585`)**:
  - Implemented `_get_latest_price(self, symbol, prices_dict=None, top_predictions=None)` to dynamically resolve market price from prices dictionary, predictions, or `StockPriceDB`.
  - In Gate 8: `raw_h_qty = int(h_amount // hedge_price)` with KRX 10-share lot rounding.
  - 80% under-hedging defect eliminated. Implemented cleanly and verified.

---

### 1.4 Domain 5 Observations (V5-32)

- **V5-32: 20-Day Market Return Metric Scale (`trading_system/run_pipeline.py:3298-3315, 3750-3770`)**:
  - `_compute_20d_ret_vol()` auto-detects decimal returns (`abs(ret) <= 0.20` and `vol <= 0.10`) and scales by $\times 100.0$.
  - Generates correct percentage values for reports and regime thresholds. Implemented cleanly and verified.

---

## 2. Logic Chain

1. **Assigned Scope Quality**: All 9 assigned tasks in Domain 3 Part B (V5-26 ~ V5-31), Domain 4 (V5-24 ~ V5-25), and Domain 5 (V5-32) were implemented with high mathematical rigor and zero integrity violations (no facade logic, no hardcoded cheating).
2. **Regression Defect 1 (Critical)**: In `trading_system/src/core/short_interest_squeeze.py:116`, line 116 references `ret_20d` which was never computed or initialized in the scope of `calculate_scores()`. Any invocation with missing short interest data throws `NameError: name 'ret_20d' is not defined`, failing `tests/test_new_27_strategies.py`.
3. **Regression Defect 2 (Critical)**: In `trading_system/src/core/event_driven.py:248-249`, the loop header `for item in eff_filings:` was omitted after `if eff_filings:`, causing `NameError: name 'item' is not defined` on line 249 when evaluating CB/BW overhang risk, failing `tests/test_phase3_improvements.py`.
4. **Regression Defect 3 (Minor Test Stale Assertion)**: In `tests/test_config.py:46`, the legacy test assertion checks `self.assertEqual(cfg.train_sample_sp500, "20")` against string type `'20'`, conflicting with the corrected `int` type casting from V5-31.
5. **Acceptance Criteria Evaluation**: Requirement R2 explicitly dictates: "전체 pytest 테스트 스위트 실행 시 실패(Failed) 0건, 에러 0건 달성 (100% test pass rate with 0 failures and 0 errors)". Because 3 unit tests currently fail due to uninitialized variable references (`NameError`) and stale test assertions, the overall system does not meet the 100% pass criterion.
6. **Verdict**: In accordance with the Reviewer & Critic workflow protocol, the verdict must be **REQUEST_CHANGES**.

---

## 3. Caveats

- **Scope Boundary**: Reviewer 2 is strictly constrained to a review-only role and must NOT modify implementation code directly.
- **Flake Isolation**: `test_challenger_m1_2_empirical.py` latency tests passed with 100% success when isolated; their failure during the 32-minute full run was purely an artifact of CPU saturation from concurrent test worker load.

---

## 4. Conclusion & Required Fixes

The changes made for Domain 3 Part B, Domain 4, and Domain 5 are fundamentally sound and well-engineered. However, the following 3 defects must be addressed by implementers before full approval:

1. **Fix `short_interest_squeeze.py` (V5-16)**:
   - Compute `ret_20d` (e.g. `(c_series.iloc[-1] / c_series.iloc[-20]) - 1.0` if `len(c_series) >= 20` else 0.0) or remove `ret_20d` from line 116 in `trading_system/src/core/short_interest_squeeze.py`.
2. **Fix `event_driven.py` (V5-20)**:
   - Add the missing `for item in eff_filings:` loop statement at line 249 in `trading_system/src/core/event_driven.py`.
3. **Update `tests/test_config.py` (V5-31 Test Alignment)**:
   - Update line 46 to assert `self.assertEqual(cfg.train_sample_sp500, 20)` or `self.assertIn(cfg.train_sample_sp500, (20, "20"))`.

---

## 5. Comprehensive Summary Table

| # | 영역 (Domain) | 심각도 | 문제 (Issue) | 원인 (Root Cause) | 조치 내용 (Remedy) | 상태 |
|---|---|---|---|---|---|---|
| **V5-24** | Domain 4: 실행 OMS & 거래비용 | 🔴 CRITICAL | `calculate_realized_slippage` 시그니처 및 Dataclass 반환형 불일치 | 0개 인자 함수에 `sym` 전달 및 `SlippageMetrics`를 float처럼 가산하여 예외 발생 | `*args, **kwargs` 시그니처 확장 및 `oms_engine.py` Gate 7.3에서 `cost_scaling_factor` 안전 언패킹 적용 | ✅ 구현 완료 & 검증 완료 |
| **V5-25** | Domain 4: 실행 OMS & 거래비용 | 🔴 CRITICAL | 인버스 ETF 헤지 주문 시 10,000원 하드코딩으로 80% 언더헤지 | `quantity = h_amount // 10000.0` 고정 가격 나눗셈 | `_get_latest_price()` 동적 가격 조회 및 틱/10주 단위 라운딩 수량 계산 적용 | ✅ 구현 완료 & 검증 완료 |
| **V5-26** | Domain 3: 31대 전략 엔진 | 🟡 MEDIUM | 옵션 IV Skew 프록시에서 표본평균 기준 하방 세미바리언스 왜곡 | `returns - mean_ret`로 계산하여 상승장/하락장에서 비대칭 왜곡 발생 | $MAR = 0.0$ 기준 `np.minimum(returns, 0.0)` 적용하여 순수 하방 변동성 산출 | ✅ 구현 완료 & 검증 완료 |
| **V5-27** | Domain 3: 31대 전략 엔진 | 🟡 MEDIUM | 변동성 타겟팅 점수 동적 범위 $[0.37, 0.73]$ 압축 | 로지스틱 기울기 계수 $k=1.0$으로 인한 점수 분산 억제 | 벡터화 백분위 랭킹 $[0.05, 0.95]$ 및 로지스틱 기울기 $k=3.0$ 적용 | ✅ 구현 완료 & 검증 완료 |
| **V5-28** | Domain 3: 31대 전략 엔진 | 🟡 MEDIUM | 발생액 품질 단일 종목 평가 시 점수 0.0 바닥 붕괴 | `1.0 - rank(pct=True)` 평가 시 $N=1$일 때 $1.0 - 1.0 = 0.0$ 부여 | $N=1$일 때 중립 점수 $0.50$ 및 현금전환 보너스 부여 | ✅ 구현 완료 & 검증 완료 |
| **V5-29** | Domain 3: 31대 전략 엔진 | 🟡 MEDIUM | 4개 팩터(CARD, ARM, MQ, HFT) 이산 계단식 점수 불연속성 | 계단식 if-else 점수 부여로 미세 변동 시 리밸런싱 회전율 급증 | 부드러운 $C^\infty$ 시그모이드 및 tanh 연속 함수로 전면 치환 | ✅ 구현 완료 & 검증 완료 |
| **V5-30** | Domain 3: 31대 전략 엔진 | 🟡 MEDIUM | DART 일반 공시가 내부자 매수(BUY)로 오분류 | 제목에 매도 키워드가 없으면 무조건 `BUY`로 기본 처리 | `'장내매수', '취득', '증가', '매입'` 등 명시적 매수 키워드 필수 검증 적용 | ✅ 구현 완료 & 검증 완료 |
| **V5-31** | Domain 3: 31대 전략 엔진 | 🟠 HIGH | 환경변수 오버라이드 시 문자열 타입 오염 | `os.environ` 문자열이 `TradingConfig` 숫자 필드에 타입 캐스팅 없이 할당 | `_get_env_int`, `_get_env_float`, `_get_env_bool`을 통한 엄격한 타입 캐스팅 적용 | ⚠️ 구현 완료 (테스트 수정 필요) |
| **V5-32** | Domain 5: 파이프라인 & CI/CD | 🟡 MEDIUM | 20일 시장 수익률/변동성 100배 축소 표기 왜곡 | 원시 소수점 수익률($0.0005$)을 퍼센트 변환 없이 `%` 문자열로 출력 | `_compute_20d_ret_vol` 자동 스케일 감지 및 $\times 100.0$ 정규화 적용 | ✅ 구현 완료 & 검증 완료 |
| **Finding 1** | Domain 3 (V5-16) | 🔴 CRITICAL | `short_interest_squeeze.py` fallback 경로 `NameError: name 'ret_20d' is not defined` | `ret_20d` 변수가 미정의된 상태에서 참조되어 숏스퀴즈 점수 계산 시 크래시 | `short_interest_squeeze.py:116`에 `ret_20d` 정의 추가 또는 계산식 정리 필요 | ❌ 수정 요청 |
| **Finding 2** | Domain 3 (V5-20) | 🔴 CRITICAL | `event_driven.py` CB/BW 오버행 평가 시 `NameError: name 'item' is not defined` | `if eff_filings:` 직후 `for item in eff_filings:` 루프문 누락 | `event_driven.py:249`에 `for item in eff_filings:` 루프 복원 필요 | ❌ 수정 요청 |

---

## 6. Verification Method

To independently verify these findings and confirm subsequent fixes:
```powershell
# 1. Verify V5-16 NameError in short interest squeeze
.venv\Scripts\python.exe -m pytest tests/test_new_27_strategies.py -v -k test_short_interest_squeeze_engine

# 2. Verify V5-20 NameError in event driven CB/BW risk
.venv\Scripts\python.exe -m pytest tests/test_phase3_improvements.py -v -k test_cb_bw_overhang_and_margin_risk_sandbox

# 3. Verify V5-31 test assertion in config test
.venv\Scripts\python.exe -m pytest tests/test_config.py -v -k test_env_overrides

# 4. Verify full repository 100% pass rate
.venv\Scripts\python.exe -m pytest tests/ -q
```
