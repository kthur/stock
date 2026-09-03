# -*- coding: utf-8 -*-
"""Section 2: High Priority Improvements (16 items)"""

def get_section2():
    return """## Section 2: 고위험 결함 개선 계획 (High Priority Improvements — 16건)

---

### [HIGH-01] 단위 테스트 `test_institutional_portfolio_construction.py` 내 잔존 실패(Assertion Error line 193: KRX 10주 vs 1주 규격 불일치)

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `tests/test_institutional_portfolio_construction.py:190-196`
- **실제 코드 스니펫**:
  ```python
  # tests/test_institutional_portfolio_construction.py line 190-196
  # Lot sizes: KRX = 10, US = 1
  p_krx = res[res["symbol"] == "005930"].iloc[0]
  p_us = res[res["symbol"] == "AAPL"].iloc[0]
  assert p_krx["lot_size"] == 10  # <--- FAIL: assert 1 == 10
  assert p_krx["shares"] % 10 == 0
  assert p_us["lot_size"] == 1
  ```
- **원인 및 영향 분석**:
  - KRX 종목 호가 단위가 1주 단위로 개편된 후 `unified_portfolio_allocator.py:501`은 `lot = 1 if is_krx else ...`로 정상 수정되었습니다.
  - 그러나 테스트 스위트인 `test_institutional_portfolio_construction.py`는 과거의 10주 호가 가정을 여전히 단언(assert)하고 있어, 현재 테스트 실행 시 즉각적인 실패(`assert 1 == 10`, 1 failed, 7 passed)가 발생하고 CI/CD 테스트 파이프라인의 100% 무결성을 저해합니다.

#### 2. 정량적/공학적 개선 방안
- **구체적 수정 코드**:
  최신 1주 호가 단위 규정에 맞추어 단언문을 갱신합니다:
  ```python
  p_krx = res[res["symbol"] == "005930"].iloc[0]
  p_us = res[res["symbol"] == "AAPL"].iloc[0]
  assert p_krx["lot_size"] == 1
  assert p_krx["shares"] >= 0
  assert p_us["lot_size"] == 1
  ```

#### 3. 수정 대상 파일
- `tests/test_institutional_portfolio_construction.py`: Lines 190–196

#### 4. 검증 방안
- `pytest tests/test_institutional_portfolio_construction.py` 실행 시 8개 테스트 전수 통과(100% Pass) 확인.

---

### [HIGH-02] SupplyChainEngine의 비동기 다중 시장 타임존 전일 종가 전진 충치(ffill)로 인한 미국 고객사 수익률 0.0% 소멸 버그

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/core/supply_chain.py:248-254`
- **실제 코드 스니펫**:
  ```python
  # supply_chain.py line 248-254
  close_pivot_filled = close_pivot.ffill()
  returns_1d = close_pivot_filled.pct_change(1).iloc[-1]
  returns_3d = close_pivot_filled.pct_change(3).iloc[-1]
  ```
- **원인 및 영향 분석**:
  - 한국 장마감 시점(16:00 KST, 일자 $T$)에는 미국 시장이 아직 개장하지 않아 미국 주식의 최신 행은 $T-1$일입니다.
  - `close_pivot.ffill()`이 실행되면 미국 주식의 $T$일 종가가 $T-1$일 종가로 채워집니다.
  - 직후 `pct_change(1).iloc[-1]`을 계산하면 $T$일과 $T-1$일이 동일하므로, **모든 미국 고객사(NVDA, AAPL, TSLA 등)의 1일 수익률이 0.0000%로 소멸**합니다.
  - 이로 인해 한국 반도체/부품 공급망 종목들이 미국 전방 대형주의 온기 전이 신호를 받지 못하고 매수 기회를 영구히 놓치게 됩니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거**:
  각 자산의 수익률을 공통 날짜 그리드에서 ffill하기 전에, 종목별 고유 거래일 시계열에서 먼저 1일 및 3일 수익률을 산출한 후 최신 유효 수익률을 맵핑합니다:
- **구체적 수정 코드**:
  ```python
  latest_1d_rets = {}
  latest_3d_rets = {}
  for sym, df_p in df_prices.items():
      c = df_p['Close'].dropna()
      if len(c) >= 2:
          latest_1d_rets[sym] = float(c.iloc[-1] / c.iloc[-2] - 1.0)
      if len(c) >= 4:
          latest_3d_rets[sym] = float(c.iloc[-1] / c.iloc[-4] - 1.0)
  ```

#### 3. 수정 대상 파일
- `trading_system/src/core/supply_chain.py`: `compute_scores()`

#### 4. 검증 방안
- **단위 테스트**: 미국 주식이 $T-1$일까지 +5% 상승하고 한국 주식이 $T$일까지 존재하는 모의 데이터에서 미국 고객사 수익률이 0.0%가 아닌 +5.0%로 인식됨을 검증.

---

### [HIGH-03] Gate 8 합성 인버스 헤지 종목의 단일 종목(1등) 시장 종속 편향 및 크로스마켓 트래킹 에러

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/execution/oms_engine.py:768-773`
- **실제 코드 스니펫**:
  ```python
  # oms_engine.py line 768-773
  first_market = str(top_predictions[0].get("market", "KOSPI")) if top_predictions else "KOSPI"
  hedge_info = PortfolioAllocator.compute_synthetic_inverse_hedge(
      portfolio_weights=portfolio_weights,
      market=first_market,
      regime_label=regime_label
  )
  ```
- **원인 및 영향 분석**:
  - 약세장/위기 레짐 시 전체 포트폴리오를 헤지할 인버스 ETF(`114800` vs `SH`)를 고를 때, 1위 추천 종목의 시장 하나만 보고 결정합니다.
  - 만약 포트폴리오의 90%가 한국 주식인데 1위 종목이 미국 주식인 경우, 한국 주식 포트폴리오 전체를 미국 S&P500 인버스(`SH`)로 헤지하게 되어 환율 및 시장 디커플링으로 막대한 트래킹 에러와 손실이 발생합니다.

#### 2. 정량적/공학적 개선 방안
- **구체적 수정 코드**:
  포트폴리오 비중을 시장별(KRX vs US)로 분할 집계하여 각각 독립적인 인버스 ETF 주문을 생성합니다:
  ```python
  krx_weight = sum(w for s, w in portfolio_weights.items() if s.isdigit() or str(s).endswith(('.KS', '.KQ')))
  us_weight = sum(w for s, w in portfolio_weights.items() if not (s.isdigit() or str(s).endswith(('.KS', '.KQ'))))
  
  if krx_weight > 0.05:
      # Hedge KRX portion with 114800
      ...
  if us_weight > 0.05:
      # Hedge US portion with SH or PSQ
      ...
  ```

#### 3. 수정 대상 파일
- `trading_system/src/execution/oms_engine.py`: `generate_order_plan` (Gate 8)

#### 4. 검증 방안
- **단위 테스트**: KOSPI 60%, NASDAQ 40% 혼합 포트폴리오에서 한국과 미국 인버스 ETF 주문이 각각 적정 비율로 분할 발행되는지 검증.

---

### [HIGH-04] SlippageFeedbackEngine의 단일 체결 이상치에 의한 비용 승수(8.0x) 즉시 폭발 위험

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/execution/slippage_feedback.py:186-222`
- **실제 코드 스니펫**:
  ```python
  # slippage_feedback.py line 186-222
  arr = np.clip(np.array(valid_slippages, dtype=float), -500.0, 500.0)
  med = float(np.median(arr)) if len(arr) > 0 else self.default_slippage_bps
  ...
  max_scale_cap = 8.0
  scaling = float(np.clip(avg_slip / self.default_slippage_bps, 0.5, max_scale_cap))
  ```
- **원인 및 영향 분석**:
  - `trade_logs.db`에 단 1건의 체결 기록만 있더라도 슬리피지가 50 bps가 발생하면, 표본 수 부족($N < 5$)으로 필터링 없이 `avg_slip = 50.0`이 되어 `scaling`이 즉시 최대치인 **8.0배로 폭증**합니다.
  - 전 시스템의 거래비용 추정이 8배로 치솟아 알파 허들(Gate 7.3)을 넘지 못해 모든 정상 매수가 전면 중단되는 교착 상태에 빠집니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거**:
  최소 유의 표본수($N_{min} = 10$)를 도입하고 표본수에 따른 베이지안 수축 가중치를 적용합니다:
  $$\\text{scaling}_{eff} = \\frac{N}{N + 10} \\cdot \\text{scaling}_{sample} + \\frac{10}{N + 10} \\cdot 1.0$$
- **구체적 수정 코드**:
  표본수 $N < 10$인 경우 기본 승수(1.0) 쪽으로 강하게 수축시키고 최근 60개 롤링 윈도우를 적용합니다.

#### 3. 수정 대상 파일
- `trading_system/src/execution/slippage_feedback.py`: `calculate_realized_slippage`

#### 4. 검증 방안
- **단위 테스트**: 1건의 100 bps 슬리피지 로그가 있을 때 승수가 8.0배가 아닌 1.5배 이하로 안정적으로 제어됨을 확인.

---

### [HIGH-05] run_pipeline.py 내 ARMFactorEngine 컨센서스 EPS/목표주가 수정치 피드 결손

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/run_pipeline.py:3100-3121, 3148-3153`
- **실제 코드 스니펫**:
  ```python
  # run_pipeline.py line 3100-3121
  _arm_fund[_sym] = {
      'eps_revision_pct': None,
      'tp_revision_pct': None,
      'eps_growth': _eps_g,
      'revenue_growth': _rev_g,
      'per': None,
  }
  ```
- **원인 및 영향 분석**:
  - 파이프라인에서 `eps_revision_pct`와 `tp_revision_pct`를 `None`으로 하드코딩하여 전달합니다.
  - `ARMFactorEngine`이 핵심 선행 지표인 컨센서스 상향 조정을 전혀 반영하지 못하고 과거 재무제표의 후행 성장률로 퇴보하거나 0.50 기본값으로 떨어집니다.

#### 2. 정량적/공학적 개선 방안
- `earnings_data.py`의 애널리스트 컨센서스 데이터 또는 Yahoo Finance `targetMeanPrice` vs 현재가 괴리율을 `tp_revision_pct` 프록시로 연동하여 선행 알파를 복원합니다.

#### 3. 수정 대상 파일
- `trading_system/run_pipeline.py`: line 3100–3153
- `trading_system/src/data_layer/earnings_data.py`

#### 4. 검증 방안
- 주요 종목에 대해 `tp_revision_pct`가 유효하게 공급되어 ARM 스코어가 종목별로 의미 있는 분산을 나타내는지 확인.

---

### [HIGH-06] run_pipeline.py 내 CARDFactorEngine 호출 시 sector_map 인자 누락으로 업종별 매크로 탄력도 무력화

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/run_pipeline.py:3157`, `trading_system/src/core/card_factor.py:140-188`
- **실제 코드 스니펫**:
  ```python
  # run_pipeline.py line 3157
  res = CARDFactorEngine().compute_scores(
      prices_dict=infer_data_dict,
      indicators_df=indicator_infer if 'indicator_infer' in locals() else pd.DataFrame()
  )  # sector_map is OMITTED!
  ```
- **원인 및 영향 분석**:
  - `sector_map`이 누락되어 모든 종목이 generic 'Market'(WTI 35%, FX 35%, VIX 30%)으로 분류됩니다.
  - 에너지(WTI 60%), 테크(FX 45%, VIX 40%), 유틸리티(VIX 60%) 등 업종별 고유의 거시지표 민감도가 완전히 상실됩니다.

#### 2. 정량적/공학적 개선 방안
- `run_pipeline.py`에서 `sector_map=sector_mapping`을 명시적으로 전달합니다.

#### 3. 수정 대상 파일
- `trading_system/run_pipeline.py`: line 3157

#### 4. 검증 방안
- 에너지 종목(XOM, S-Oil)에 WTI 가중치 60%가 정상 부여되는지 확인.

---

### [HIGH-07] PredictionModel 및 LATRFactorEngine의 비미국 통화(JPY, TWD, BRL 등) 환율 1.0 고정 왜곡 및 유동성 왜곡

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/ai/prediction_model.py:1396`, `trading_system/src/core/latr_factor.py:120-124`
- **실제 코드 스니펫**:
  ```python
  # prediction_model.py line 1396
  fx_conv = 1350.0 if is_krx_symbol else 1.0
  
  # latr_factor.py line 120-121
  is_kr = str(sym).isdigit() or str(sym).endswith(('.KS', '.KQ'))
  fx_norm = usdkrw_rate if is_kr else 1.0
  ```
- **원인 및 영향 분석**:
  - KRX가 아니면 모두 USD($1.0$)로 간주합니다.
  - 일본 주식(JPY $\\approx 155$)의 경우 환율 $1.0$을 적용하면 거래대금이 155배 부풀려져 Amihud 비유동성 지표가 155배 왜곡됩니다.

#### 2. 정량적/공학적 개선 방안
- 시장 티커 접미사 또는 지표 데이터프레임에서 동적 FX 딕셔너리(`usdjpy`, `usdtwd`, `eurusd` 등)를 조회하여 정확한 통화 환산을 수행합니다.

#### 3. 수정 대상 파일
- `trading_system/src/ai/prediction_model.py`: line 1396
- `trading_system/src/core/latr_factor.py`: line 120–124

#### 4. 검증 방안
- 일본 7203.T(토요타)에 대해 155 JPY/USD 환율이 적용되어 정상적인 USD 거래대금이 산출되는지 검증.

---

### [HIGH-08] `factor_suppression.py`의 `CLUSTER_MAP` 내 전략 35, 36, 37번 누락으로 2D 레짐 노이즈 억제 탈루

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/ai/factor_suppression.py:74-80`
- **원인 및 영향 분석**:
  - `CLUSTER_MAP`에 전략 35(`dual_correction`), 36(`index_rebalance`), 37(`overnight_gap_reversal`)이 누락되어 `'OTHER'`로 분류됩니다.
  - 레짐별 위험 클러스터 억제(High Volatility 시 Reversal 억제 등) 대상에서 제외되어 규제망을 벗어납니다.

#### 2. 정량적/공학적 개선 방안
- `dual_correction` $\\to$ `'REVERSAL'`, `index_rebalance` $\\to$ `'FLOW_MICRO'`, `overnight_gap_reversal` $\\to$ `'REVERSAL'`로 명시적 등록.

#### 3. 수정 대상 파일
- `trading_system/src/ai/factor_suppression.py`: `CLUSTER_MAP` (Lines 74–80)

#### 4. 검증 방안
- `tests/test_factor_suppression.py`에서 신규 전략들의 클러스터 매핑 및 레짐별 억제 계수 정상 적용 검증.

---

### [HIGH-09] `ensemble_scorer.py`의 Multi-Horizon 티어 점수 단순 산술평균으로 인한 동적 레짐 가중치 30% 희석

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/ai/ensemble_scorer.py:2504-2511, 2566`
- **실제 코드 스니펫**:
  ```python
  # ensemble_scorer.py line 2511
  return np.where(v_counts > 0, sub_sums / np.maximum(v_counts, 1), np.nan)
  ```
- **원인 및 영향 분석**:
  - Slow/Medium/Fast 티어 점수 계산 시 유효 전략들의 점수를 단순 동일 가중 산술평균합니다.
  - 앞단에서 최적화된 동적 레짐 가중치가 티어 내부에서 무시되고, 최종 점수의 30%를 차지하는 `hierarchical_score`가 동일 가중 잡음으로 희석됩니다.

#### 2. 정량적/공학적 개선 방안
- 티어 내부에서도 유효 전략별 정규화된 가중치를 곱하는 `_calc_weighted_tier_score` 함수로 개편합니다.

#### 3. 수정 대상 파일
- `trading_system/src/ai/ensemble_scorer.py`: `combine_predictions()`

#### 4. 검증 방안
- 티어 내 가중치 0.09인 전략과 0.01인 전략이 있을 때 0.09 전략에 비례하여 티어 점수가 형성되는지 검증.

---

### [HIGH-10] 단일/소수 전략 유효 종목에 대한 Bayesian Coverage Shrinkage 부재로 불완전 데이터 종목 랭킹 왜곡

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/ai/ensemble_scorer.py:2485-2496`
- **원인 및 영향 분석**:
  - 37개 중 36개가 결측되고 단 1개(예: 호재 공시 0.95점, 가중치 0.03)만 유효할 때, 가중치 재정규화(`total / 0.03`)를 거쳐 최종 0.95점이 됩니다.
  - 37개 전략 전수의 검증을 거친 0.90점 종목보다 불완전 종목이 최상위 1위로 랭크되는 역전 현상이 발생합니다.

#### 2. 정량적/공학적 개선 방안
- 유효 가중치 합계가 0.60에 미달할 경우 신뢰도를 중립(0.50)으로 베이지안 수축시킵니다:
  $$S_{\\text{final}} = \\lambda_{\\text{cov}} S_{\\text{norm}} + (1 - \\lambda_{\\text{cov}}) \\times 0.50, \\quad \\lambda_{\\text{cov}} = \\min\\left(1.0, \\frac{\\sum_{k \\in \\text{valid}} w_k}{0.60}\\right)$$

#### 3. 수정 대상 파일
- `trading_system/src/ai/ensemble_scorer.py`: `combine_predictions()` (Lines 2485–2497)

#### 4. 검증 방안
- 전략 1개만 0.95점인 종목이 전략 30개 검증 0.85점 종목보다 하위 랭크로 배치됨을 확인.

---

### [HIGH-11] 미시구조 거래비용 모델의 US 티커 온점(.) 파싱 오류(`BRK.B` 등)로 인한 국내 증권거래세(0.18%) 오과금

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/ai/ensemble_scorer.py:2801-2803, 2853-2854`
- **실제 코드 스니펫**:
  ```python
  is_us_stock = mkt_col.isin(['SP500', 'NASDAQ', 'RUSSELL2000']) | (sym_col.str.isalpha() & (sym_col.str.len() <= 5))
  ```
- **원인 및 영향 분석**:
  - `BRK.B`, `BF.B` 등 클래스 주식은 온점(`.`)이 포함되어 `isalpha()`가 False가 됩니다.
  - 시장 컬럼이 비어 있을 때 KOSPI로 오분류되어 한국 증권거래세(0.18%)가 부과되고 한국식 기준금액이 적용됩니다.

#### 2. 정량적/공학적 개선 방안
- 온점을 허용하는 정규식(`^[A-Z]{1,5}(\\.[A-Z])?$`)으로 미국 주식 판정을 완전무결하게 개선합니다.

#### 3. 수정 대상 파일
- `trading_system/src/ai/ensemble_scorer.py`: line 2802

#### 4. 검증 방안
- `BRK.B` 입력 시 `stt_tax`가 0.00003(SEC fee)으로 적용됨을 검증.

---

### [HIGH-12] 숏스퀴즈 전략의 데이터 결측 프록시 점수와 원천 점수 간 무차별 결합에 따른 랭킹 왜곡

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/core/short_interest_squeeze.py:116-160`
- **원인 및 영향 분석**:
  - 공매도 잔고 데이터가 없는 종목의 프록시 점수(0.10~0.25)와 실제 공매도 데이터가 있는 종목의 원천 점수(0.5~5.0)를 동일 컬럼에 섞은 후 백분위 랭크를 매깁니다.
  - 데이터 결측 종목이 구조적으로 무조건 하위 30%로 전락합니다.

#### 2. 정량적/공학적 개선 방안
- 공매도 데이터 부재 시 인위적 프록시 대신 진정한 결측치(`np.nan`)를 반환하여 앙상블 재정규화 메커니즘을 타도록 개선합니다.

#### 3. 수정 대상 파일
- `trading_system/src/core/short_interest_squeeze.py`: line 101–125

#### 4. 검증 방안
- 공매도 데이터 부재 종목이 `NaN`으로 안전하게 보존되는지 확인.

---

### [HIGH-13] DataValidator 일시적 이상치 가격 필터의 `pct_change(-1)` 미래 참조 룩어헤드 편향

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/persistence/database.py:448-460`
- **실제 코드 스니펫**:
  ```python
  fwd_pct = df['Close'].pct_change(-1).abs()
  rev_pct = df['Close'].pct_change(1).abs()
  spike_mask = (rev_pct > 0.40) & (fwd_pct > 0.40)
  ```
- **원인 및 영향 분석**:
  - `pct_change(-1)`은 내일 종가를 참조합니다. 온라인 실시간 스트리밍 바나 과거 시계열 정제 시 미래 데이터를 참조하여 과거 가격을 사후 변조하는 편향을 유발합니다.

#### 2. 정량적/공학적 개선 방안
- `is_historical_cleaning: bool = False` 플래그로 분리하고, 실시간 추론 시에는 인과적 롤링 중앙값/IQR 필터로 전환합니다.

#### 3. 수정 대상 파일
- `trading_system/src/persistence/database.py`: `DataValidator`

#### 4. 검증 방안
- 실시간 정제 시 시점 $t+1$의 가격 변조가 시점 $t$ 정제 결과에 영향을 주지 않음을 검증.

---

### [HIGH-14] Lead-Lag 모델 내 S&P 500과 미국 섹터 ETF 간 비대칭 시차 이동으로 인한 동시성 왜곡

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/ai/prediction_model.py:3168-3174`
- **원인 및 영향 분석**:
  - 미국 섹터 ETF(XLK, XLF)는 1일 시차를 적용(`shift(1)`)하지만, S&P 500(`^GSPC`)과 나스닥(`^IXIC`)은 시차 이동을 하지 않습니다.
  - 동일한 미국 장 운영시간에 거래되는 지표 간에 1일의 인위적 시차 왜곡이 발생합니다.

#### 2. 정량적/공학적 개선 방안
- 한국 시장 예측 시 미국 기원 모든 거시 지표 및 섹터 ETF에 일관되게 1일 시차 이동을 적용합니다.

#### 3. 수정 대상 파일
- `trading_system/src/ai/prediction_model.py`: line 3168–3174

#### 4. 검증 방안
- `^GSPC`와 `XLK`가 한국 일자 대비 동일한 1일 시차 정렬을 유지하는지 검증.

---

### [HIGH-15] PortfolioAllocator의 EVT-CVaR 폴백 최적화 시 VaR 수식 오적용으로 꼬리 위험 과소평가

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/risk/portfolio_allocator.py:680-690`
- **실제 코드 스니펫**:
  ```python
  cvar_val = float(max(0.0, - (m_ret + z_cf * s_ret)))
  ```
- **원인 및 영향 분석**:
  - 폴백 최적화 시 `cvar_val`에 대입된 수식은 Cornish-Fisher **VaR(분위수)** 계산식이며, 꼬리 손실 기댓값인 CVaR이 아닙니다.
  - 극단 손실 위험을 과소평가하여 고위험 포트폴리오를 허용하게 됩니다.

#### 2. 정량적/공학적 개선 방안
- Cornish-Fisher Expected Shortfall 적분 계수(`es_factor`)를 복원하여 정밀한 CVaR 값을 제약조건에 대입합니다.

#### 3. 수정 대상 파일
- `trading_system/src/risk/portfolio_allocator.py`: `optimize_with_evt_cvar_constraint`

#### 4. 검증 방안
- 비정규 분포에서 폴백 제약 함수의 `cvar_val`이 `var_val`보다 엄격하게 큼을 단언.

---

### [HIGH-16] Gatheral 3/2-Power 비선형 시장충격 모델의 목적함수 미반영 및 사후 휴리스틱 왜곡

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/risk/unified_portfolio_allocator.py:259-277`
- **원인 및 영향 분석**:
  - 목적함수에 충격 비용을 넣지 않고 사후에 `w * exp(-2 * impact)`를 곱한 뒤 다시 비중 합계로 재정규화(`w / sum(w)`)합니다.
  - 전 자산이 유동성 제약에 걸리면 재정규화로 인해 감쇠 효과가 상쇄되고 상한선 재배분 과정에서 비유동성 자산 비중이 다시 증가합니다.

#### 2. 정량적/공학적 개선 방안
- 목적함수에 비선형 충격 패널티를 정식 포함하거나, 시장 참여율 상한($w_i \\le w_{curr, i} + \\frac{0.05 ADV_i}{C}$)을 하드 제약으로 바인딩합니다.

#### 3. 수정 대상 파일
- `trading_system/src/risk/unified_portfolio_allocator.py`: line 259–277

#### 4. 검증 방안
- 대형 자본금 최적화 시 비유동성 자산의 주문 규모가 5% ADV 제약선을 절대 넘지 않음을 검증.
"""

if __name__ == "__main__":
    print(get_section2()[:300])
