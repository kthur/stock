# -*- coding: utf-8 -*-
"""Section 1: Critical Priority Improvements (13 items)"""

def get_section1():
    return """## Section 1: 치명적 결함 개선 계획 (Critical Priority Improvements — 13건)

---

### [CRIT-01] UnifiedPortfolioAllocator의 US 종목 주식수(Shares) 산출 시 환율 미적용으로 인한 1,350배 과대 주문 산출 결함

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/risk/unified_portfolio_allocator.py:494-506` (`allocate` 메서드), `trading_system/run_pipeline.py:4044-4051`
- **실제 코드 스니펫**:
  ```python
  # unified_portfolio_allocator.py line 494-506
  # Lot size resolution (KRX: 1 share since 2014, TSE/HKEX/HOSE: 100 shares, US: 1 share)
  shares_list = []
  lot_list = []
  for i, row in enumerate(df_candidates.itertuples()):
      sym = str(row.symbol)
      mkt = str(getattr(row, "market", "KOSPI")).upper()
      is_krx = sym.isdigit() or mkt in ["KOSPI", "KOSDAQ", "KRX"]
      lot = 1 if is_krx else (100 if mkt in ["JAPAN_TSE", "HKEX", "VIETNAM_HOSE"] else 1)
      px = latest_prices[i]
      alloc_amt = row.allocation_amount
      raw_shares = int(alloc_amt // px) if px > 0 else 0
      adj_shares = (raw_shares // lot) * lot
      shares_list.append(adj_shares)
      lot_list.append(lot)
  ```
- **원인 및 영향 분석**:
  - `alloc_amt`는 `w_final * total_portfolio_value`로 계산되어 기본 운용 통화인 **원화(KRW)** 단위를 가집니다. 예를 들어 총 운용자금 1억 원($100,000,000$ KRW) 포트폴리오에서 비중 5%를 배분받은 종목의 `alloc_amt`는 $5,000,000$ KRW입니다.
  - 반면 미국 주식(AAPL, NVDA, MSFT 등)의 현재가 `px`는 **달러(USD)** 단위($150.0 USD)입니다.
  - 위 코드는 환율 변환 없이 `raw_shares = int(5,000,000 // 150) = 33,333` 주로 산출합니다.
  - 실제 매수해야 할 정상 주식수는 환율($1,350$ KRW/USD) 기준 $\frac{5,000,000}{1,350 \times 150} \approx 24$ 주입니다.
  - 환율($1,350$)이 누락됨으로써 **실제 필요한 주문 수량의 약 1,350배에 달하는 33,333주(약 500만 달러 = 67.5억 원 규모)**가 `shares` 컬럼에 기입됩니다. 이는 계좌 총 자본금의 67배를 초과하는 치명적 과대 레버리지 주문을 유발합니다.
  - `oms_engine.py`는 V6-25 패치를 통해 `target_amount / fx_rate`로 보정되었으나, 신규 도입된 `unified_portfolio_allocator.py`의 `allocate()` 내부에는 환율 인자 및 로컬 통화 변환이 누락되어 발생한 중대한 단위 불일치 결함입니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거**:
  각 자산 $i$의 로컬 통화 기준 가격을 $P_i^{local}$, 기준 통화(KRW) 기준 배분 금액을 $A_i^{KRW}$, 통화 환율을 $FX_i$ ($1$ USD당 KRW 환율, 예: $1,350.0$)라 할 때, 로컬 주문 수량 $S_i$는 다음과 같이 정의되어야 합니다:
  $$A_i^{local} = \\begin{cases} A_i^{KRW} / FX_i & \\text{if asset is traded in USD} \\\\ A_i^{KRW} & \\text{if asset is traded in KRW} \\end{cases}$$
  $$S_i = \\left\\lfloor \\frac{A_i^{local}}{P_i^{local} \\cdot \\text{lot}_i} \\right\\rfloor \\cdot \\text{lot}_i$$
- **구체적 수정 코드**:
  `allocate` 시그니처에 `usdkrw_rate: float = 1350.0` 인자를 명시적으로 추가하고, 시장 구분에 따라 로컬 배분 금액을 환산합니다:
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
      usdkrw_rate: float = 1350.0,  # V8-CRIT-01: Explicit USD/KRW FX Rate
  ) -> pd.DataFrame:
      ...
      for i, row in enumerate(df_candidates.itertuples()):
          sym = str(row.symbol)
          mkt = str(getattr(row, "market", "KOSPI")).upper()
          is_krx = sym.isdigit() or mkt in ["KOSPI", "KOSDAQ", "KRX"]
          lot = 1 if is_krx else (100 if mkt in ["JAPAN_TSE", "HKEX", "VIETNAM_HOSE"] else 1)
          px = latest_prices[i]
          alloc_amt_krw = row.allocation_amount
          
          # V8 Fix: Convert KRW allocation amount to local currency before dividing by price
          is_us = mkt in ["SP500", "NASDAQ", "RUSSELL2000", "US"] or not is_krx
          fx = max(usdkrw_rate, 1.0) if is_us else 1.0
          alloc_amt_local = alloc_amt_krw / fx
          
          raw_shares = int(alloc_amt_local // px) if px > 0 else 0
          adj_shares = (raw_shares // lot) * lot
          shares_list.append(adj_shares)
          lot_list.append(lot)
  ```
  `trading_system/run_pipeline.py:4044-4051`에서도 파이프라인에서 수집된 실제 실시간 환율 `usdkrw_report`를 `allocate()`에 전달하도록 연동합니다.

#### 3. 수정 대상 파일
- `trading_system/src/risk/unified_portfolio_allocator.py`: `allocate()` 메서드 (Lines 430–515)
- `trading_system/run_pipeline.py`: line 4044–4051 (`usdkrw_rate` 인자 전달)

#### 4. 검증 방안
- **단위 테스트**: `tests/test_institutional_portfolio_construction.py` 내 `test_end_to_end_allocate_usd_shares_fx_scaling` 구현.
- **테스트 케이스**: 총 자본금 1억 원($100,000,000$ KRW), 환율 $1,350$ KRW/USD, AAPL($150.0 USD) 비중 5% 배분 시:
  - `alloc_amt_local = 5,000,000 / 1,350 = 3,703.70 USD`
  - `shares = int(3,703.70 // 150) = 24` 주가 정확히 산출되는지 단언 (`assert p_us["shares"] == 24`).
  - 과거 버그인 33,333주가 산출되지 않음을 보장 (`assert p_us["shares"] < 100`).

---

### [CRIT-02] Black-Litterman 20일 전망수익률(Q)과 일별 공분산(Sigma) 시계열 불일치로 인한 마코위츠 효용함수 선형 붕괴 및 100배 단절

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/analysis/portfolio_optimizer.py:202-255` (`calculate_black_litterman_weights` 함수), `trading_system/src/risk/unified_portfolio_allocator.py:211-215`
- **실제 코드 스니펫**:
  ```python
  # portfolio_optimizer.py line 202-212, 240-255
  # Prior returns Pi: Pi = delta * Sigma @ w_eq
  horizon_cov = cov_matrix  # Daily covariance matrix (~0.0004)
  Pi = risk_aversion * (horizon_cov @ w_eq)  # Daily equilibrium returns (~0.04%/day)

  # Views Q (predicted returns)
  Q = np.asarray(predicted_returns, dtype=float)
  if len(Q) != n:
      Q = np.zeros(n)
  # Normalize units: if Q is in percentage (> 0.5 mean), scale to decimal matching Pi
  if np.nanmean(np.abs(Q)) > 0.50:
      Q = Q / 100.0
  ...
  # Markowitz Quadratic Utility Optimization:
  excess_mu = mu_bl - rf_daily
  def objective(w):
      w = np.asarray(w)
      return 0.5 * lambda_aversion * float(w @ cov_bl @ w) - float(w @ excess_mu)
  ```
- **원인 및 영향 분석**:
  1. **호라이즌 단위 불일치에 의한 마코위츠 효용함수 선형 붕괴**:
     - `cov_matrix`는 일별 주가 수익률로 추정된 **일별 공분산 행렬**($\\Sigma_{daily} \\approx 0.0004$)입니다.
     - 따라서 사전 균형수익률 $\\Pi = \\delta \\Sigma_{daily} w_{eq}$ 역시 **일별 수익률**($\\approx 0.04\\%$/day)입니다.
     - 반면 파이프라인에서 전달되는 `predicted_returns`는 앙상블 엔진의 `ensemble_expected_return`으로, 이는 **20일 누적 기대수익률**(예: $5.0\\% = 0.05$)입니다.
     - `Q / 100.0` 처리를 거쳐 $Q = 0.05$가 되지만, 이는 20일치 수익률이므로 일별 수익률로 환산하면 $\\frac{0.05}{20} = 0.0025$여야 합니다.
     - $Q$가 20일치 누적값 그대로 일별 $\\Pi$와 결합되면 사후 기대수익률 $\\mu_{BL} \\approx 0.05$가 됩니다.
     - 이차 효용함수에서 분산 페널티 $\\frac{\\lambda}{2} w^T \\Sigma_{BL} w \\approx 0.5 \\times 2.5 \\times 0.0004 = 0.0005$인 반면, 선형 수익률 항 $w^T (\\mu_{BL} - rf) \\approx 0.050$이 되어 **선형 수익률 항이 이차 위험 페널티보다 100배 지배**하게 됩니다.
     - 그 결과 최적화 목적함수가 선형 계획법으로 붕괴하여, 기대수익률 1위 종목에 단일 종목 한도(`max_single_stock_weight`)까지 채우는 **선형 코너해(Linear Corner Solution)**가 발생하고 포트폴리오 다변화 효과가 원천 상실됩니다.
  2. **임의의 0.50 임계치로 인한 100배 단절 불연속성**:
     - `if np.nanmean(np.abs(Q)) > 0.50:` 로직에 의해, 평균 예측수익률이 $0.49\\%$이면 나누지 않아 $0.49$($49\\%$ 수익률)로 인식되고, $0.51\\%$이면 $0.0051$($0.51\\%$)로 100배 축소되는 수학적 불연속성이 존재합니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거**:
  전망 호라이즌을 $H = 20$일이라 할 때, 일별 공분산 $\\Sigma_{daily}$와 20일 누적 전망수익률 $Q_{20d}$ 간 단위를 일치시키는 방법은 두 가지입니다:
  - 방법 1 (일별 환산): $Q_{daily} = \\frac{Q_{20d}}{H}$. 이때 $rf_{daily}$, $\\Pi_{daily}$, $\\Sigma_{daily}$ 모두 일별로 정합합니다.
  - 방법 2 (20일 호라이즌 스케일업): $\\Sigma_{H} = H \\cdot \\Sigma_{daily}$, $\\Pi_H = H \\cdot \\Pi_{daily}$, $rf_H = H \\cdot rf_{daily}$.
  안정성을 위해 함수 인자로 `view_horizon: int = 20`과 `returns_are_percentage: Optional[bool] = None`을 도입하여 단위를 명시적으로 정규화합니다.
- **구체적 수정 코드**:
  ```python
  def calculate_black_litterman_weights(
      cov_matrix: pd.DataFrame,
      predicted_returns: Union[pd.Series, np.ndarray, list],
      market_caps: Optional[Union[pd.Series, np.ndarray, list]] = None,
      risk_aversion: float = 2.5,
      tau: float = 0.05,
      view_confidence: Optional[Union[pd.Series, np.ndarray, list]] = None,
      risk_free_rate: float = 0.035,
      symbols: Optional[List[str]] = None,
      sectors: Optional[List[str]] = None,
      max_single_stock_weight: float = 0.20,
      max_sector_weight: float = 0.35,
      view_horizon: int = 20,  # V8-CRIT-02: Prediction view horizon in trading days
      returns_are_percentage: bool = True,
  ) -> pd.Series:
      ...
      Q = np.asarray(predicted_returns, dtype=float)
      if len(Q) != n:
          Q = np.zeros(n)
          
      # V8 Fix: Rigorous unit conversion without cliff threshold
      if returns_are_percentage:
          Q_decimal = Q / 100.0
      else:
          Q_decimal = Q.copy()
          
      # Convert cumulative H-day return view into daily equivalent return matching daily cov_matrix
      eff_horizon = max(int(view_horizon), 1)
      Q_daily = Q_decimal / float(eff_horizon)
      
      # Scale daily covariance and prior
      rf_daily = float((1.0 + risk_free_rate) ** (1.0 / 252.0) - 1.0)
      Pi_daily = risk_aversion * (cov_matrix.values @ w_eq)
      
      # Black-Litterman Master Formula with scale-consistent inputs
      # P = I (identity matrix for absolute stock-level views)
      # Omega = diag(P (tau * Sigma) P^T) / confidence
      omega = np.diag(np.diag(tau * cov_matrix.values))
      if view_confidence is not None:
          conf = np.clip(np.asarray(view_confidence, dtype=float), 0.05, 1.0)
          omega = np.diag(np.diag(omega) / conf)
          
      inv_tau_sigma = np.linalg.pinv(tau * cov_matrix.values)
      inv_omega = np.linalg.pinv(omega)
      
      post_cov_inv = inv_tau_sigma + inv_omega
      post_cov = np.linalg.pinv(post_cov_inv)
      post_mu_daily = post_cov @ (inv_tau_sigma @ Pi_daily + inv_omega @ Q_daily)
      cov_bl = cov_matrix.values + post_cov
      
      # Optimization with scale-consistent daily objective
      excess_mu = post_mu_daily - rf_daily
      def objective(w):
          w = np.asarray(w)
          # Balanced utility: 0.5 * lambda * w^T Sigma w - w^T (mu - rf)
          return 0.5 * risk_aversion * float(w @ cov_bl @ w) - float(w @ excess_mu)
  ```

#### 3. 수정 대상 파일
- `trading_system/src/analysis/portfolio_optimizer.py`: `calculate_black_litterman_weights()`
- `trading_system/src/risk/unified_portfolio_allocator.py`: `optimize_multi_model_blend()`

#### 4. 검증 방안
- **단위 테스트**: `tests/test_portfolio_optimizer.py` 내 `test_black_litterman_horizon_scale_consistency` 작성.
- **검증 기준**:
  - 20일 전망수익률 $5.0\\%$ 자산과 일별 변동성 $2.0\\%$ 자산 4개 결합 시, 사후 일별 초과수익률이 약 $0.0025$ 수준으로 정합하게 도출되는지 확인.
  - 특정 1위 종목에 $20\\%$ 상한선까지 몰빵되는 선형 코너해가 발생하지 않고, 위험조정수익률에 비례하여 $12\\% \\sim 18\\%$ 구간으로 안정적으로 분산되는지 검증.

---

### [CRIT-03] Strict Causal LSTM 내 전구간 시계열 표준화에 의한 미래 참조(Lookahead) 편향

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/ai/lstm_predictor.py:106-112` (`prepare_multivariate_sequences` 메서드)
- **실제 코드 스니펫**:
  ```python
  # lstm_predictor.py line 106-112
  for sym, df_s in stock_data.items():
      ...
      vals = df_s[feature_cols].values  # Entire multi-year historical series up to date T
      # Global series mean/std across entire history
      s_mean = np.nanmean(vals, axis=0)
      s_std = np.nanstd(vals, axis=0)
      s_std = np.where(s_std < 1e-6, 1.0, s_std)
      norm_vals = (vals - s_mean) / s_std
  ```
- **원인 및 영향 분석**:
  - `LSTMPredictor`는 "Strict Causal LSTM"을 표방하고 있으나, 입력 텐서 시퀀스를 생성할 때 종목별 전체 데이터프레임의 전체 구간에 대해 단일 평균(`s_mean`)과 표준편차(`s_std`)를 산출합니다.
  - 2021년 과거 시점의 시퀀스 $t$를 생성할 때, 2024~2026년의 미래 주가 수준, 레짐 변화, 변동성 통계가 `s_mean`과 `s_std`에 반영되어 과거 텐서에 누수(Data Leakage)됩니다.
  - 이로 인해 Walk-Forward 교차 검증에서 인위적으로 높은 적합도가 산출되고, 미래를 알지 못하는 실전 런타임 추론에서는 심각한 성능 저하(Train-Serve Distribution Shift)가 발생합니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거**:
  시계열 인과성(Causality)을 준수하기 위해, 시점 $t$의 정규화 파라미터는 오직 $t$ 이전 관측치에만 의존해야 합니다:
  $$\\mu_t = \\frac{1}{W} \\sum_{k=1}^{W} x_{t-k}, \\quad \\sigma_t = \\sqrt{\\frac{1}{W} \\sum_{k=1}^{W} (x_{t-k} - \\mu_t)^2 + \\epsilon}$$
  $$x_t^{norm} = \\frac{x_t - \\mu_t}{\\sigma_t}$$
- **구체적 수정 코드**:
  과거 60영업일 롤링 윈도우 인과 표준화기(`RollingCausalNormalizer`)를 적용하거나, `shift(1)`을 적용한 롤링 통계량으로 정규화합니다:
  ```python
  # Causal Rolling Standardization preserving strict point-in-time validity
  r_mean = df_s[feature_cols].rolling(window=60, min_periods=20).mean().shift(1)
  r_std = df_s[feature_cols].rolling(window=60, min_periods=20).std().shift(1)
  r_std = r_std.fillna(1.0).replace(0.0, 1.0)
  norm_df = ((df_s[feature_cols] - r_mean) / r_std).bfill().fillna(0.0)
  norm_vals = norm_df.values
  ```

#### 3. 수정 대상 파일
- `trading_system/src/ai/lstm_predictor.py`: `prepare_multivariate_sequences()`

#### 4. 검증 방안
- **단위 테스트**: `tests/test_lstm_causality.py` 신설.
- **검증 기준**: 2020~2024년 주가 데이터프레임에서 2024년 이후의 미래 행 데이터를 극단적 이상치(+1000%)로 변조하더라도, 2021년 시점의 시퀀스 텐서 및 모델 예측값이 $10^{-6}$ 허용오차 내에서 100% 동일하게 유지되는지 단언.

---

### [CRIT-04] RIM Valuation 잔여이익 모델의 Ohlson 유한 시계 ROE 감쇠 루프 미갱신 결함

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/core/rim_valuation.py:338-359` (`calculate_intrinsic_value` 메서드)
- **실제 코드 스니펫**:
  ```python
  # rim_valuation.py line 338-359
  current_bps = bps
  current_roe = roe  # Initialized once outside loop
  for t in range(1, years + 1):
      if current_bps <= 0.0:
          excess_income = 0.0
          current_bps = 0.0
      else:
          net_income = current_bps * current_roe
          excess_income = current_bps * (current_roe - r_e)
          retention = self.retention_ratio if net_income > 0 else 1.0
          current_bps += net_income * retention
      pv_excess += excess_income / ((1.0 + r_e) ** t)
  # Terminal value calculation uses un-decayed current_roe:
  tv_excess = (current_bps * (current_roe - r_e) * omega) / max(denom_tv, 1e-4)
  ```
- **원인 및 영향 분석**:
  - Ohlson(1995) 잔여이익 모델(RIM)의 핵심 원리는 기업의 초과이익(ROE - $r_e$)이 경쟁과 자본 유입으로 인해 시간 경과에 따라 할인율($r_e$)로 점진적으로 회귀(Decay)한다는 것입니다:
    $$\\text{ROE}_t = r_e + (\\text{ROE}_{t-1} - r_e) \\times (1 - \\text{decay\\_rate})$$
  - 그러나 위 코드에서는 루프 내부에서 `current_roe`를 갱신하는 코드가 **완전히 누락**되어 있습니다.
  - 이로 인해 초기 ROE가 25%인 고수익 기업의 경우, 8년 예측 기간 전체는 물론 영구 잔여가치(Terminal Value) 계산 시점까지도 25% ROE가 영구 불변으로 유지됩니다.
  - 더욱이 유보이익 복리 누적으로 BPS가 8년간 3배 이상 폭증하고 여기에 25% 초과이익률이 곱해져, 기업의 본질가치($V_0$)가 실제보다 300%~500% 이상 비정상적으로 과대평가(거품)되어 산출됩니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거**:
  루프의 매 반복마다 유효 감쇠율(`eff_decay = np.clip(decay_rate, 0.0, 0.50)`)을 적용하여 ROE가 자본비용 $r_e$로 점진 수렴하도록 갱신합니다:
- **구체적 수정 코드**:
  ```python
  current_bps = bps
  current_roe = roe
  eff_decay = float(np.clip(self.decay_rate, 0.0, 0.50))
  for t in range(1, years + 1):
      if current_bps <= 0.0:
          excess_income = 0.0
          current_bps = 0.0
          current_roe = r_e
      else:
          net_income = current_bps * current_roe
          excess_income = current_bps * (current_roe - r_e)
          retention = self.retention_ratio if net_income > 0 else 1.0
          current_bps += net_income * retention
          # V8 Fix: Decay ROE toward required return on equity (r_e)
          current_roe = r_e + (current_roe - r_e) * (1.0 - eff_decay)
      pv_excess += excess_income / ((1.0 + r_e) ** t)
  ```

#### 3. 수정 대상 파일
- `trading_system/src/core/rim_valuation.py`: `calculate_intrinsic_value()` (Lines 338–359)

#### 4. 검증 방안
- **단위 테스트**: `tests/test_rim_valuation.py` 내 `test_roe_decay_convergence` 작성.
- **검증 기준**: $\\text{ROE} = 0.25, r_e = 0.08, \\text{decay} = 0.10$ 조건에서, ROE 감쇠 적용 시 적정주가가 미감쇠 버전 대비 유의미하게 하향 산출되며, $\\text{decay} \\to 1.0$일 때 $V_0 \\to \\text{BPS}$에 수렴함을 검증.

---

### [CRIT-05] SQLite 저장소 스키마 절단으로 인한 32~37번 전략 점수 영구 탈루

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/data_layer/indicator_storage.py:341-395, 483-515, 1206-1260, 1563-1612`
- **실제 코드 스니펫**:
  ```python
  # indicator_storage.py line 341-395
  cursor.execute('''
      CREATE TABLE IF NOT EXISTS ensemble_predictions (
          symbol TEXT NOT NULL,
          date TEXT NOT NULL,
          ...
          darkpool_score REAL,
          earnings_tone_drift_score REAL,  -- Strategy 31 is the last column!
          ensemble_score REAL,
          ...
          PRIMARY KEY (symbol, date)
      )
  ''')
  ```
- **원인 및 영향 분석**:
  - `ensemble_predictions` 및 `ensemble_prediction_history` 테이블 생성 스키마가 전략 31번(`earnings_tone_drift_score`)까지만 작성되어 있습니다.
  - 신규 도입된 전략 32~37번:
    - Strategy 32: `cross_asset_spillover_score`
    - Strategy 33: `supply_chain_gnn_score`
    - Strategy 34: `range_expansion_score`
    - Strategy 35: `dual_correction_score`
    - Strategy 36: `index_rebalance_score`
    - Strategy 37: `overnight_gap_score`
  - 이 6개 컬럼이 테이블 정의에 누락되어 있고, `save_ensemble_predictions()` 및 `save_ensemble_history()`의 `INSERT INTO` 쿼리문 및 파라미터 튜플에도 포함되어 있지 않습니다.
  - 그 결과 `run_pipeline.py`가 37개 전략 점수를 정상 산출하더라도, DB에 저장되는 순간 6개 전략 점수가 조용히 유실(Dropped)되어 사후 백테스트 및 모델 검증이 불가능해집니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거**:
  시스템의 37개 전략 점수는 완전한 시계열 일관성을 유지해야 하므로, DB 스키마 및 마이그레이션 루틴에서 32~37번 전략 컬럼을 반드시 명시적으로 추가하고 영속화해야 합니다.
- **구체적 수정 코드**:
  1. `_init_db()` 내 테이블 생성 구문에 6개 컬럼 추가.
  2. 기존 DB 인스턴스를 위한 무중단 마이그레이션(`ALTER TABLE ADD COLUMN`) 자동 실행 로직 추가:
  ```python
  v8_new_cols = [
      ("cross_asset_spillover_score", "REAL"),
      ("supply_chain_gnn_score", "REAL"),
      ("range_expansion_score", "REAL"),
      ("dual_correction_score", "REAL"),
      ("index_rebalance_score", "REAL"),
      ("overnight_gap_score", "REAL"),
  ]
  for table in ["ensemble_predictions", "ensemble_prediction_history"]:
      for col_name, col_type in v8_new_cols:
          try:
              cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
          except sqlite3.OperationalError:
              pass  # Already exists
  ```
  3. `save_ensemble_predictions` 및 `save_ensemble_history`의 INSERT 컬럼 및 파라미터를 37개 전략 전수로 확장.

#### 3. 수정 대상 파일
- `trading_system/src/data_layer/indicator_storage.py`: `_init_db`, `save_ensemble_predictions`, `save_ensemble_history`

#### 4. 검증 방안
- **단위 테스트**: `tests/test_indicator_storage.py` 내 `test_save_and_load_37_strategies_schema` 작성.
- **검증 기준**: 37개 전략 점수가 채워진 더미 데이터프레임을 저장한 후 `SELECT *`로 조회하여 6개 신규 컬럼이 정상적으로 조회되며 값이 일치하는지 확인.

---

### [CRIT-06] UnifiedPortfolioAllocator 소규모 유니버스(N <= 4) CVaR 상한선 제약 불능으로 솔버 100% 실패 및 강제 추락

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/risk/unified_portfolio_allocator.py:136-166` (`calculate_cvar_weights` 메서드)
- **실제 코드 스니펫**:
  ```python
  # unified_portfolio_allocator.py line 136-166
  def constr_sum_w(var):
      return float(np.sum(var[:n]) - 1.0)

  bounds = [(0.0, self.max_single_weight) for _ in range(n)] + [(None, None)] + [(0.0, None) for _ in range(T)]
  ```
- **원인 및 영향 분석**:
  - 기본값 `self.max_single_weight = 0.20`($20\\%$)입니다.
  - 최적화 대상 종목수 $n$이 4개 이하인 경우($n \\le 4$), 모든 종목에 상한선까지 비중을 부여해도 합계는 최대 $4 \\times 0.20 = 0.80 < 1.0$입니다.
  - 제약조건 `sum(w) == 1.0`을 만족하는 실행 가능 영역(Feasible Set)이 공집합이 되므로, SLSQP 최적화 솔버가 **100% 확률로 최적화에 실패**합니다.
  - 실패 시 즉시 line 170의 `Fallback to inverse volatility`로 강제 추락하여, Rockafellar-Uryasev CVaR 꼬리위험 최소화 모델이 완전히 무력화됩니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거**:
  유니버스 종목수 $n$이 작을 때도 합계 1.0 등식 제약이 실행 가능하도록, 단일 종목 유효 상한선을 유니버스 크기에 연동하여 동적으로 완충합니다:
  $$w_i^{max} = \\max\\left( \\text{max\\_single\\_weight}, \\frac{1.05}{n} \\right)$$
- **구체적 수정 코드**:
  ```python
  eff_max_w = max(self.max_single_weight, 1.05 / max(n, 1))
  bounds = [(0.0, eff_max_w) for _ in range(n)] + [(None, None)] + [(0.0, None) for _ in range(T)]
  ```

#### 3. 수정 대상 파일
- `trading_system/src/risk/unified_portfolio_allocator.py`: `calculate_cvar_weights()`

#### 4. 검증 방안
- **단위 테스트**: `tests/test_cvar_allocator.py` 신설.
- **검증 기준**: $n = 2, 3, 4$ 유니버스로 `calculate_cvar_weights()`를 호출하여 SLSQP 솔버가 `res.success == True`로 정상 수렴하고 가중치 합계가 $1.0000$이 됨을 확인.

---

### [CRIT-07] TurnoverOptimizer 및 PortfolioAllocator의 USD 계좌 금액 기준(KRW 50,000) 오적용에 의한 리밸런싱 영구 교착(Deadlock)

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/execution/turnover_optimizer.py:75`, `trading_system/src/risk/portfolio_allocator.py:1297-1301`
- **실제 코드 스니펫**:
  ```python
  # turnover_optimizer.py line 75
  if not is_full_exit and not is_fresh_entry and (weight_delta < self.turnover_threshold_pct or amount_delta < self.min_rebalance_delta_krw):
      final_w = curr_w
      action = "HOLD"

  # portfolio_allocator.py line 1297-1301
  min_trade_krw = 50_000.0
  min_weight_delta = min_trade_krw / max(1_000_000.0, portfolio_value) if portfolio_value > 0 else 0.001
  delta_i = max(delta_i, min_weight_delta)
  ```
- **원인 및 영향 분석**:
  - `min_rebalance_delta_krw`의 기본값은 $50,000$ KRW입니다.
  - 미국 포트폴리오를 운용하여 `total_capital = 100,000.0` (USD 단위)가 전달되는 경우:
    - 10% 비중 조정 주문 금액은 `amount_delta = 0.10 * 100,000 = $10,000`입니다.
    - 그러나 $10,000 < 50,000$ 조건이 참(True)이 되어, 10%($10,000) 규모의 정상 리밸런싱이 무조건 `HOLD` 처리되어 주문이 차단됩니다. 심지어 40% 조정($40,000 < 50,000)도 차단됩니다.
  - `portfolio_allocator.py`에서도 `portfolio_value = 100,000` (USD) 전달 시, `min_weight_delta = 50,000 / 100,000 = 0.50` (50% 버퍼 밴드!)가 산출되어, 비중 변동이 50% 미만인 모든 정상 리밸런싱이 영구 동결되는 교착(Deadlock)이 발생합니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거**:
  포트폴리오 통화(`currency`) 또는 시장(`market`) 인자를 인식하여, USD 계좌인 경우 최소 거래 금액 임계치를 달러 기준($50.0 USD)으로 적용하거나 환율로 스케일링합니다:
  $$\\text{min\\_delta} = \\begin{cases} 50.0 & \\text{if USD} \\\\ 50,000.0 & \\text{if KRW} \\end{cases}$$
- **구체적 수정 코드**:
  ```python
  # turnover_optimizer.py
  is_usd = str(kwargs.get("currency", "KRW")).upper() == "USD"
  min_rebalance_delta = 50.0 if is_usd else self.min_rebalance_delta_krw
  if not is_full_exit and not is_fresh_entry and (weight_delta < self.turnover_threshold_pct or amount_delta < min_rebalance_delta):
      final_w = curr_w
      action = "HOLD"
  ```

#### 3. 수정 대상 파일
- `trading_system/src/execution/turnover_optimizer.py`: `optimize_allocations`
- `trading_system/src/risk/portfolio_allocator.py`: `compute_portfolio_rebalance`

#### 4. 검증 방안
- **단위 테스트**: $100,000 USD 자본금 계좌에서 8% 비중 조정 시 `HOLD`로 차단되지 않고 정상적인 `BUY`/`SELL` 주문이 생성되는지 검증.

---

### [CRIT-08] 파이프라인 상 CrisisDetector 무상태(Stateless) 생성으로 인한 VIX 속도/낙폭 속도/거시 Z-score 영구 0 결함

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/run_pipeline.py:3696-3715`, `trading_system/src/risk/risk_manager.py`
- **실제 코드 스니펫**:
  ```python
  # run_pipeline.py line 3696-3715
  try:
      from src.risk.risk_manager import RiskManager, CrisisDetector, CrisisLevel
      risk_mgr = RiskManager()
      crisis_detector = CrisisDetector(risk_mgr)
      crisis_lvl = crisis_detector.evaluate(
          vix=vix_report,
          usdkrw=usdkrw_report,
          oil=wti_report,
          tnx=us10y_report
      )
  ```
- **원인 및 영향 분석**:
  - `run_pipeline.py` 실행 시마다 항상 `CrisisDetector` 객체를 새로 생성하면서, 내부에 구현된 `load_state()`를 전혀 호출하지 않습니다.
  - 이로 인해 내부 시계열 큐(`_vix_history`, `_dd_history`, `_oil_history`)의 길이가 **항상 1**로 유지됩니다.
  - `_score_vix`: `len(self._vix_history) >= 5`가 항상 False이므로 **VIX 속도(`vix_roc`)가 영구히 0.0**입니다.
  - `_score_drawdown`: `len(self._dd_history) >= 5`가 항상 False이므로 **낙폭 속도(`dd_speed`)가 영구히 0.0**입니다.
  - `_score_macro`: 표본 수가 1이므로 표준편차가 0이 되어 **거시 Z-Score 위험 점수가 사실상 무력화**됩니다.
  - 평가 후 `save_state()`도 호출하지 않아 `models/crisis_state.json` 파일이 생성되지 않는 무상태 루프에 갇혀 있습니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거**:
  시계열 기반 위험 속도 및 가속도(ROC)를 측정하기 위해서는 최소 20영업일의 롤링 버퍼가 보존되어야 합니다.
- **구체적 수정 코드**:
  1. `CrisisDetector`에 과거 지표 데이터프레임으로부터 큐를 일괄 주입하는 `seed_history_from_dataframe()` 메서드 신설.
  2. `run_pipeline.py`에서 `load_state()`를 시도하고, 콜드 스타트 시 `indicator_infer` 시계열을 주입하며, 평가 후 `save_state()`를 호출:
  ```python
  crisis_detector = CrisisDetector(risk_mgr)
  if not crisis_detector.load_state():
      if 'indicator_infer' in locals() and not indicator_infer.empty:
          crisis_detector.seed_history_from_dataframe(indicator_infer)
  crisis_lvl = crisis_detector.evaluate(...)
  crisis_detector.save_state()
  ```

#### 3. 수정 대상 파일
- `trading_system/run_pipeline.py`: lines 3696–3715
- `trading_system/src/risk/risk_manager.py`: `CrisisDetector` 클래스

#### 4. 검증 방안
- **단위 테스트**: 파이프라인 지표 데이터 주입 후 `_vix_history` 길이가 20 이상 확보되고, VIX 5일 급등 시 `vix_roc`가 정상 양수로 계산되어 위기 단계가 민감하게 승격되는지 검증.

---

### [CRIT-09] 37개 전략 전수 `.dropna()`로 인한 상관 직교화(Löwdin Orthogonalization) 페널티 전면 무력화

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/ai/ensemble_scorer.py:967-969` (`apply_correlation_orthogonalization_penalty` 메서드)
- **실제 코드 스니펫**:
  ```python
  # ensemble_scorer.py line 967-969
  subset_df = scores_df[list(valid_cols.values())].apply(pd.to_numeric, errors='coerce').dropna()
  if len(subset_df) < 10:
      return weights
  ```
- **원인 및 영향 분석**:
  - 37대 전략 체계에서는 대안 데이터(다크풀, 옵션 IV/Gamma, 어닝콜 텍스트 톤, 공시 감성 등)의 특성상 종목별로 일부 전략 데이터가 결측(`NaN`)되는 것이 자연스럽습니다.
  - 그러나 위 코드는 37개 전략 점수 컬럼 전체에 대해 단 하나의 결측치라도 존재하면 해당 행 전체를 제거하는 `.dropna()`를 수행합니다.
  - 그 결과 37개 전략이 단 1개도 결측되지 않고 100% 채워진 종목 수가 10개 미만(`len(subset_df) < 10`)으로 떨어지게 되며, 이로 인해 Löwdin 대칭 직교화 상관 페널티 계산이 **조용히 중단(Silent Bypass)되어 원본 가중치가 그대로 반환**됩니다.
  - 고상관 전략(상관계수 > 0.65) 간의 가중치 감쇄 및 위험 분산 기능이 실전에서 전면 무력화됩니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거**:
  전체 행 제거 대신, 각 전략 쌍별 유효 관측치를 보존하는 **Pairwise Complete Correlation** 방식을 적용합니다:
- **구체적 수정 코드**:
  ```python
  # Pairwise complete observations correlation matrix
  corr_matrix = scores_df[list(valid_cols.values())].apply(pd.to_numeric, errors='coerce').corr(min_periods=5).abs().fillna(0.0)
  np.fill_diagonal(corr_matrix.values, 1.0)
  ```

#### 3. 수정 대상 파일
- `trading_system/src/ai/ensemble_scorer.py`: `apply_correlation_orthogonalization_penalty`

#### 4. 검증 방안
- **단위 테스트**: `tests/test_ensemble_correlation_penalty.py` 신설. 50개 종목 중 각 전략별로 10~20%의 결측치가 분산되어 37개 전략이 모두 채워진 행이 0개인 상태에서, 바이패스 없이 고상관 전략 가중치 감쇄가 정상 산출되는지 검증.

---

### [CRIT-10] Strategy 30(Darkpool) 어댑터의 클래스 오인스턴스화(`MicrostructureImbalanceEngine` 중복 호출) 결함

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/ai/ml_strategy_adapters.py:373-375` (`DarkPoolStrategyAdapter.compute_scores`)
- **실제 코드 스니펫**:
  ```python
  # ml_strategy_adapters.py line 373-375
  from src.core.hft_engine import MicrostructureImbalanceEngine
  engine = MicrostructureImbalanceEngine()
  res = engine.compute_scores(prices_dict=prices_dict, **kwargs)
  ```
- **원인 및 영향 분석**:
  - 전략 30번(`darkpool`)의 실제 구현체는 `src.data_layer.darkpool_tracker.DarkPoolTrackerEngine`입니다.
  - 그러나 어댑터 클래스 `DarkPoolStrategyAdapter`는 전략 23번인 `MicrostructureImbalanceEngine`(호가창 불균형 엔진)을 임포트하여 실행하고 있습니다.
  - 이로 인해 전략 레지스트리나 모듈형 파이프라인에서 전략 30번을 호출할 경우, 다크풀 블록트레이드 추적 대신 호가창 미시구조 점수가 이중으로 산출되어 전략 23번과 30번 간 상관계수가 1.0000이 되고 모델 다변화 효과가 원천 상실됩니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거**:
  다크풀 블록 거래량 및 ATS 비율을 정상 추적하기 위해 올바른 `DarkPoolTrackerEngine` 클래스를 바인딩합니다.
- **구체적 수정 코드**:
  ```python
  from src.data_layer.darkpool_tracker import DarkPoolTrackerEngine
  engine = DarkPoolTrackerEngine(config=self.config)
  res = engine.calculate_scores(symbols=list(prices_dict.keys()), prices_dict=prices_dict, **kwargs)
  ```

#### 3. 수정 대상 파일
- `trading_system/src/ai/ml_strategy_adapters.py`: `DarkPoolStrategyAdapter.compute_scores`

#### 4. 검증 방안
- **단위 테스트**: `DarkPoolStrategyAdapter` 실행 결과가 `MicrostructureImbalanceEngine`과 독립적인 신호를 산출하는지 단언.

---

### [CRIT-11] ZCA 백색화의 주성분 Consensus Alpha 파괴 (코드 미구현으로 인한 시장 공통 초과수익 65% 압축)

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/ai/factor_orthogonalizer.py:226-235` (`_pca_zca_symmetric` 메서드)
- **실제 코드 스니펫**:
  ```python
  # factor_orthogonalizer.py line 226-235
  # Multi-model consensus preservation (V7-03):
  # Do not compress the leading principal component (PC1 = shared multi-strategy consensus).
  # For lambda_max, keep whitening filter = 1.0.
  lambdas_clean = np.maximum(eigenvalues, 0.0)
  ridge_eps = float(np.clip(self.ridge_epsilon, 1e-6, 1e-3))
  whitening_filter = 1.0 / np.sqrt(lambdas_clean + ridge_eps)
  ```
- **원인 및 영향 분석**:
  - 주석에는 "선행 주성분(PC1)인 다중 전략 컨센서스를 보존하기 위해 $\\lambda_{\\max}$ 필터 = 1.0을 유지한다"고 명시되어 있으나, 실제 코드(line 233)에서는 모든 고유값에 대해 무차별적으로 $1 / \\sqrt{\\lambda + \\epsilon}$를 적용하고 있습니다.
  - 37개 전략이 공통으로 확신을 나타낼 때 PC1의 고유값은 $\\lambda_{\\max} \\approx 10$ 수준으로 커집니다. 이때 필터값은 $1 / \\sqrt{10} \\approx 0.316$이 되어 **모든 모델이 일치하여 찾아낸 공통 초과수익(Shared Alpha)을 68% 이상 강제로 압축(Damping)**합니다.
  - 반대로 극소 고유값($\\lambda \\approx 0$)에는 1,000배의 거대한 필터가 곱해져 수치 노이즈를 극단적으로 증폭시킵니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거**:
  PC1의 백색화 필터를 1.0으로 고정하고 상태수(Condition Number)를 10.0 이내로 캡핑합니다:
- **구체적 수정 코드**:
  ```python
  lambdas_clean = np.maximum(eigenvalues, 0.0)
  ridge_eps = float(np.clip(self.ridge_epsilon, 1e-6, 1e-3))
  whitening_filter = 1.0 / np.sqrt(lambdas_clean + ridge_eps)
  
  # Preserve leading consensus alpha (PC1 filter = 1.0)
  if len(whitening_filter) > 0:
      whitening_filter[-1] = 1.0
      
  # Cap maximum amplification to prevent noise explosion
  whitening_filter = np.minimum(whitening_filter, 10.0)
  ```

#### 3. 수정 대상 파일
- `trading_system/src/ai/factor_orthogonalizer.py`: `_pca_zca_symmetric`

#### 4. 검증 방안
- **단위 테스트**: 고상관 전략 신호($\\rho = 0.85$) 합성 데이터에서 백색화 후 PC1 분산 보존율 $\\ge 90\\%$, 상태수 $\\le 10$ 검증.

---

### [CRIT-12] CARDFactorEngine 내 OLS VIX 민감도 부호 역전으로 인한 폭락장을 급등으로 오판정

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/core/card_factor.py:174`
- **실제 코드 스니펫**:
  ```python
  # card_factor.py line 174
  macro_impact = (
      model.params.get('FX', 0.0) * usdkrw_chg
      + model.params.get('WTI', 0.0) * wti_chg
      - model.params.get('VIX', 0.0) * vix_pct_shock  # <-- DOUBLE NEGATIVE BUG!
  )
  ```
- **원인 및 영향 분석**:
  - OLS 회귀식에서 변동성(VIX) 상승 시 주가는 통상 하락하므로 추정 계수 $\\beta_{VIX}$는 이미 음수(예: $-0.45$)입니다.
  - 위 코드에서는 `- model.params['VIX'] * vix_pct_shock`로 음수를 한 번 더 빼줌으로써 이중 음수(Double Negative)가 발생하여 $+4.5\\%$가 됩니다.
  - 변동성이 폭등(VIX +10%)할 때 매크로 기대수익률을 양수(+4.5%)로 계산하고, 실제 주가가 폭락(-4.5%)하면 괴리율 $R - \\hat{R} = -9.0\\%$로 산출하여 극단적인 저평가로 오판하고 폭락 종목을 대거 매수하는 역발상 매수 오류를 범합니다.

#### 2. 정량적/공학적 개선 방안
- **구체적 수정 코드**:
  부호를 `+`로 정상 복원합니다:
  ```python
  macro_impact = (
      model.params.get('FX', 0.0) * usdkrw_chg
      + model.params.get('WTI', 0.0) * wti_chg
      + model.params.get('VIX', 0.0) * vix_pct_shock
  )
  ```

#### 3. 수정 대상 파일
- `trading_system/src/core/card_factor.py`: line 174

#### 4. 검증 방안
- **단위 테스트**: 음의 VIX 베타를 가진 종목에 VIX 충격 발생 시 `macro_impact`가 음수로 산출되는지 검증.

---

### [CRIT-13] 사업보고서(연간) 법정 공시 시차 90일 미반영 및 고정 45일 적용에 따른 45일치 룩어헤드 편향

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/ai/prediction_model.py:1082-1087`, `trading_system/src/data_layer/indicator_storage.py:290-310`, `trading_system/src/data_layer/earnings_data.py`
- **실제 코드 스니펫**:
  ```python
  # prediction_model.py line 1082-1087
  lag_days = 45 if is_krx else 40
  fund_df['date_available'] = fund_df['date'] + pd.to_timedelta(lag_days, unit='D')
  ```
- **원인 및 영향 분석**:
  - 한국 KRX 분기보고서 제출 기한은 45일이지만, **연간 12월 결산 사업보고서는 90일(3월 31일)**입니다. 미국 SEC 10-K도 60일입니다.
  - 모든 재무제표에 일괄 45일을 적용하면, 12월 31일 결산 감사보고서 수치가 2월 14일에 공시된 것으로 처리되어 **45일간의 미래 재무 정보가 과거 주가 학습에 누수(Lookahead Bias)**됩니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거**:
  결산 월 및 시장 구분에 따라 동적 법정 공시 시차를 적용합니다:
  $$\\text{Lag} = \\begin{cases} 90 \\text{일} & \\text{if Month} = 12 \\text{ and KRX} \\\\ 60 \\text{일} & \\text{if Month} = 12 \\text{ and US} \\\\ 45 \\text{일} & \\text{if Month} \\in \\{3, 6, 9\\} \\text{ and KRX} \\\\ 40 \\text{일} & \\text{if US 10-Q} \\end{cases}$$
- **구체적 수정 코드**:
  `stock_fundamentals` 테이블에 `date_available` 컬럼을 정식 영속화하고, `prediction_model.py`에서 결산 월 기반 동적 시차를 적용합니다.

#### 3. 수정 대상 파일
- `trading_system/src/data_layer/indicator_storage.py`: `stock_fundamentals` 스키마
- `trading_system/src/ai/prediction_model.py`: `_prepare_training_data`
- `trading_system/src/data_layer/earnings_data.py`

#### 4. 검증 방안
- **단위 테스트**: 12월 결산 재무 데이터의 `date_available`이 익년 3월 31일 이후로 설정되어 2월 주가와 결합되지 않음을 검증.
"""

if __name__ == "__main__":
    print(get_section1()[:300])
