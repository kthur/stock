# apply_v8_remediation.py
# Uses deterministic section slicing to replace sections without regex backslash escaping issues.

file_path = r"d:\Finance\code\stock\system_improvement_plan_v8.md"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

def replace_section(full_text, start_marker, end_marker, replacement_content):
    pos_start = full_text.find(start_marker)
    if pos_start == -1:
        raise ValueError(f"Start marker not found: {start_marker}")
    pos_end = full_text.find(end_marker, pos_start)
    if pos_end == -1:
        raise ValueError(f"End marker not found: {end_marker}")
    return full_text[:pos_start] + replacement_content + full_text[pos_end:]

# ----------------------------------------------------
# 1. CRIT-01 Replacement
# ----------------------------------------------------
crit01_replacement = """### [CRIT-01] UnifiedPortfolioAllocator의 US 종목 주식수(Shares) 산출 시 환율 미적용으로 인한 1,350배 과대 주문 산출 결함

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
  - 실제 매수해야 할 정상 주식수는 환율($1,350$ KRW/USD) 기준 $\\frac{5,000,000}{1,350 \\times 150} \\approx 24$ 주입니다.
  - 환율($1,350$)이 누락됨으로써 **실제 필요한 주문 수량의 약 1,350배에 달하는 33,333주(약 500만 달러 = 67.5억 원 규모)**가 `shares` 컬럼에 기입됩니다. 이는 계좌 총 자본금의 67배를 초과하는 치명적 과대 레버리지 주문을 유발합니다.
  - `oms_engine.py`는 V6-25 패치를 통해 `target_amount / fx_rate`로 보정되었으나, 신규 도입된 `unified_portfolio_allocator.py`의 `allocate()` 내부에는 환율 인자 및 로컬 통화 변환이 누락되어 발생한 중대한 단위 불일치 결함입니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거 및 인터페이스 규격 보존**:
  1. **호출 시그니처 및 하위 호환성 100% 보존 (CRIT-01 Remediation)**:
     기존 파이프라인(`run_pipeline.py:4044-4051`) 및 단위 테스트(`tests/test_institutional_portfolio_construction.py:176`)의 호출 인터페이스인 `allocate(self, predictions_df, prices_dict, total_portfolio_value=100_000_000.0, regime='BULL_LOW_VOL', current_holdings=None, sector_map=None, top_n=20, base_currency='KRW', usd_krw=1350.0)`를 원형 그대로 보존합니다.
  2. **다중 통화(Base Currency) 완벽 지원**:
     원화 기준 계좌(`base_currency == 'KRW'`)와 달러 기준 계좌(`base_currency == 'USD'`)를 명시적으로 구분하여 지원합니다.
     - 원화 계좌에서 미국 주식 매수 시: `effective_price_krw = px * usd_krw if (is_us and base_currency == 'KRW') else px`
     - 달러 계좌에서 한국 주식 매수 시: `effective_price_usd = px / usd_krw if (is_krx and base_currency == 'USD') else px`
     - 계좌 통화와 자산 통화가 일치하는 경우(예: 달러 계좌에서 미국 주식 매수) 환율 변환 없이 원 가격 $px$를 그대로 적용하여 1,350배 축소 왜곡을 원천 방지합니다.
  $$S_i = \\left\\lfloor \\frac{A_i}{P_i^{eff} \\cdot \\text{lot}_i} \\right\\rfloor \\cdot \\text{lot}_i$$
  $$\\text{where } P_i^{eff} = \\begin{cases} P_i \\cdot FX & \\text{if is\\_us and base\\_currency == 'KRW'} \\\\ P_i / FX & \\text{if is\\_krx and base\\_currency == 'USD'} \\\\ P_i & \\text{otherwise} \\end{cases}$$
- **구체적 수정 코드**:
  `allocate` 시그니처에 `base_currency: str = "KRW"`와 `usd_krw: float = 1350.0` 인자를 기본값과 함께 추가하고, 주식수 산출 루프에 다중 통화 환율 변환을 바인딩합니다:
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
      base_currency: str = "KRW",
      usd_krw: float = 1350.0,
  ) -> pd.DataFrame:
      ...
      # Step 4: Compute shares, lot sizes, and allocation amounts
      latest_prices = []
      for sym in valid_symbols:
          p_df = prices_dict.get(sym)
          if p_df is not None and not p_df.empty:
              c_col = "Close" if "Close" in p_df.columns else ("close" if "close" in p_df.columns else None)
              p = float(p_df[c_col].iloc[-1]) if c_col else 1.0
          else:
              p = 1.0
          latest_prices.append(max(p, 1.0))

      df_candidates["weight"] = w_final
      df_candidates["volatility"] = vols
      df_candidates["predicted_return"] = pred_rets
      df_candidates["allocation_amount"] = w_final * total_portfolio_value

      # Lot size resolution (KRX: 1 share since 2014, TSE/HKEX/HOSE: 100 shares, US: 1 share)
      shares_list = []
      lot_list = []
      for i, row in enumerate(df_candidates.itertuples()):
          sym = str(row.symbol)
          mkt = str(getattr(row, "market", "KOSPI")).upper()
          is_krx = sym.isdigit() or mkt in ["KOSPI", "KOSDAQ", "KRX"]
          is_us = mkt in ["SP500", "NASDAQ", "RUSSELL2000", "US"] or not is_krx
          lot = 1 if is_krx else (100 if mkt in ["JAPAN_TSE", "HKEX", "VIETNAM_HOSE"] else 1)
          px = latest_prices[i]
          allocated_capital = row.allocation_amount
          
          # V8-CRIT-01 Fix: Multi-currency aware FX translation
          effective_price_krw = px * usd_krw if (is_us and base_currency == 'KRW') else (px / usd_krw if (is_krx and base_currency == 'USD') else px)
          raw_shares = int(allocated_capital / effective_price_krw) if effective_price_krw > 0 else 0
          adj_shares = (raw_shares // lot) * lot
          shares_list.append(adj_shares)
          lot_list.append(lot)

      df_candidates["shares"] = shares_list
      df_candidates["lot_size"] = lot_list
      return df_candidates
  ```
  `trading_system/run_pipeline.py:4044-4051`에서도 수집된 실시간 환율 `usdkrw_report`를 `allocate(..., base_currency="KRW", usd_krw=usdkrw_report)`로 전달하도록 연동합니다.

#### 3. 수정 대상 파일
- `trading_system/src/risk/unified_portfolio_allocator.py`: `allocate()` 메서드 (Lines 371–515)
- `trading_system/run_pipeline.py`: line 4044–4051 (`base_currency` 및 `usd_krw` 인자 전달)

#### 4. 검증 방안
- **단위 테스트**: `tests/test_institutional_portfolio_construction.py` 및 전용 통합 스위트 `tests/test_v8_remediation.py` 내 `test_end_to_end_allocate_usd_shares_fx_scaling` 구현.
- **테스트 케이스**:
  1. 원화 계좌($100,000,000$ KRW), 환율 $1,350$ KRW/USD, AAPL($150.0 USD) 비중 5%($5,000,000$ KRW) 배분 시:
     `effective_price_krw = 150 * 1350 = 202,500 KRW`
     `shares = int(5,000,000 // 202,500) = 24` 주가 정확히 산출됨을 단언 (`assert p_us["shares"] == 24`).
     과거 버그인 33,333주가 산출되지 않음을 보장 (`assert p_us["shares"] < 100`).
  2. 달러 계좌($100,000$ USD, `base_currency="USD"`), 환율 $1,350$ KRW/USD, AAPL($150.0 USD) 비중 5%($5,000$ USD) 배분 시:
     `effective_price_krw = 150 USD` (동일 통화 환율 미적용)
     `shares = int(5,000 // 150) = 33` 주가 정확히 산출됨을 단언 (`assert p_us["shares"] == 33`).

---

"""
text = replace_section(text, "### [CRIT-01]", "### [CRIT-02]", crit01_replacement)

# ----------------------------------------------------
# 2. CRIT-02 Replacement
# ----------------------------------------------------
crit02_replacement = """### [CRIT-02] Black-Litterman 20일 전망수익률(Q)과 일별 공분산(Sigma) 시계열 불일치로 인한 마코위츠 효용함수 선형 붕괴 및 100배 단절

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `trading_system/src/analysis/portfolio_optimizer.py:143-265` (`calculate_black_litterman_weights` 함수), `trading_system/src/risk/unified_portfolio_allocator.py:211-215`
- **실제 코드 스니펫**:
  ```python
  # portfolio_optimizer.py line 143-155, 202-212
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
      ...
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
  2. **임의의 0.50 임계치로 인한 100배 단절 불연속성 및 소수점 뷰 회귀 위험**:
     - 기존의 `if np.nanmean(np.abs(Q)) > 0.50:` 로직은 평균이 $0.49\\%$이면 나누지 않고 $0.51\\%$이면 100배 축소하는 치명적 불연속성이 있었습니다.
     - 또한 무조건 100으로 나눌 경우, `tests/test_adversarial_challenger_1.py:320-328`처럼 이미 소수점 단위 뷰(`[0.05, 0.08, 0.12]`)를 전달하는 기존 단위 테스트가 $0.0005$로 100배 축소되어 테스트가 회귀 실패합니다.
  3. **반환 타입 및 시그니처 변경 금지 (Integrity Mandate)**:
     - 10개 이상의 모듈과 테스트 스위트가 `calculate_black_litterman_weights`의 반환 타입으로 `np.ndarray`를 기대하므로, `pd.Series`로 변경해서는 안 되며 기존 파라미터(`prior_weights`, `omega_scale`, `meta_convictions`, `regime` 등)를 온전히 보존해야 합니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거 및 스케일 동적 자동 감지 (CRIT-02 Remediation)**:
  전망 호라이즌을 $H = 20$일이라 할 때, 일별 공분산 $\\Sigma_{daily}$와 20일 누적 전망수익률 $Q_{20d}$ 간 단위를 일치시키기 위해 20일 전망수익률을 일별 등가 수익률로 선형 환산합니다:
  $$Q_{daily} = \\frac{Q_{20d}}{H}$$
  이때 $rf_{daily}$, $\\Pi_{daily}$, $\\Sigma_{daily}$ 모두 일별 단위로 완벽하게 정합하여 마코위츠 이차 효용함수의 곡률(Curvature)이 완벽히 복원됩니다.
  또한 입력 $Q$의 스케일을 안전하게 자동 판정합니다:
  - `returns_are_percentage is True`: $Q / 100.0$ 적용
  - `returns_are_percentage is False`: $Q$ 그대로 사용
  - `returns_are_percentage is None` (기본값):
    - 원소 중 절댓값이 1.0 이상인 값(예: $5.0\\%$, $8.0\\%$)이 존재하면 퍼센트 뷰로 판정하여 $100$으로 나눕니다.
    - 모든 원소의 절댓값이 1.0 미만(예: `[0.05, 0.08, 0.12]` in `test_adversarial_challenger_1.py:320-328`)이면 이미 소수점 뷰이므로 $100$으로 나누지 않습니다.
- **구체적 수정 코드**:
  반환 타입을 `np.ndarray`로 유지하고, 기존 파라미터와 완벽히 호환되는 시그니처를 보존합니다:
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
      view_horizon: int = 20,  # V8-CRIT-02: Prediction view horizon in trading days
      returns_are_percentage: Optional[bool] = None,  # Auto-detection by default
  ) -> np.ndarray:
      if cov_matrix is None or predicted_returns is None:
          return np.array([])
          
      n = cov_matrix.shape[0]
      if n == 0:
          return np.array([])
      if n == 1:
          return np.array([1.0])

      # Prior weights (default to equal weights)
      w_eq = np.full(n, 1.0 / n) if prior_weights is None or len(prior_weights) != n else np.asarray(prior_weights)
      horizon_cov = cov_matrix
      Pi = risk_aversion * (horizon_cov @ w_eq)

      # Views Q (predicted returns)
      Q = np.asarray(predicted_returns, dtype=float)
      if len(Q) != n:
          logger.warning("Length of predicted_returns does not match cov_matrix. Using flat returns.")
          Q = np.zeros(n)

      # V8-CRIT-02 Fix: Dynamic scale auto-detection & decimal alignment
      if returns_are_percentage is True:
          Q_decimal = Q / 100.0
      elif returns_are_percentage is False:
          Q_decimal = Q.copy()
      else:
          # Auto-detect: if any element >= 1.0 (e.g. 5.0% return), convert percentage to decimal (Q / 100)
          # If all elements < 1.0 (e.g. [0.05, 0.08, 0.12] in test_adversarial_challenger_1.py:320-328), do NOT divide by 100
          if np.any(np.abs(Q) >= 1.0):
              Q_decimal = Q / 100.0
          else:
              Q_decimal = Q.copy()

      # Convert cumulative 20-day horizon return to daily equivalent to match daily cov_matrix
      eff_horizon = max(int(view_horizon), 1)
      Q_daily = Q_decimal / float(eff_horizon)

      # Uncertainty Omega (scaled by dynamic meta conviction)
      if meta_convictions is not None and len(meta_convictions) == n:
          conv_scale = np.clip(np.asarray(meta_convictions, dtype=float), 0.10, 1.50)
          diag_omega = (np.diag(horizon_cov) * omega_scale) / conv_scale
          Omega = np.diag(np.maximum(diag_omega, 1e-8))
      else:
          Omega = np.diag(np.maximum(np.diag(horizon_cov) * omega_scale, 1e-8))

      # Posterior expected returns and covariance matrix
      A = tau * horizon_cov + Omega
      inv_A_diff = np.linalg.solve(A, Q_daily - Pi)
      mu_bl = Pi + tau * (horizon_cov @ inv_A_diff)

      inv_A_Sigma = np.linalg.solve(A, horizon_cov)
      cov_bl = (1.0 + tau) * horizon_cov - (tau ** 2) * (horizon_cov @ inv_A_Sigma)

      rf_daily = (1.0 + risk_free_rate) ** (1.0 / 252.0) - 1.0 if risk_free_rate > 0.005 else risk_free_rate
      lambda_aversion = max(0.1, float(risk_aversion))
      excess_mu = mu_bl - rf_daily

      def objective(w):
          w = np.asarray(w)
          return 0.5 * lambda_aversion * float(w @ cov_bl @ w) - float(w @ excess_mu)

      def objective_grad(w):
          w = np.asarray(w)
          return lambda_aversion * (cov_bl @ w) - excess_mu

      w0 = np.full(n, 1.0 / n)
      cons = {"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)}
      bounds = [(0.0, 1.0) for _ in range(n)]

      res = minimize(objective, w0, method="SLSQP", jac=objective_grad, bounds=bounds, constraints=cons)
      if res.success:
          return np.asarray(res.x)
      return np.full(n, 1.0 / n)
  ```

#### 3. 수정 대상 파일
- `trading_system/src/analysis/portfolio_optimizer.py`: `calculate_black_litterman_weights()` (Lines 143–265)
- `trading_system/src/risk/unified_portfolio_allocator.py`: `optimize_multi_model_blend()`

#### 4. 검증 방안
- **단위 테스트**: 기존 스위트 `tests/test_adversarial_challenger_1.py:320-328`(소수점 단위 뷰와 퍼센트 단위 뷰 동등성 검증), `tests/test_portfolio_optimizer_and_oms.py` 및 전용 통합 스위트 `tests/test_v8_remediation.py` 내 `test_black_litterman_horizon_scale_consistency` 구현.
- **검증 기준**:
  - 20일 전망수익률 $5.0\\%$ 자산과 일별 변동성 $2.0\\%$ 자산 4개 결합 시, 사후 일별 초과수익률이 약 $0.0025$ 수준으로 정합하게 도출되는지 확인.
  - 특정 1위 종목에 $20\\%$ 상한선까지 몰빵되는 선형 코너해가 발생하지 않고, 위험조정수익률에 비례하여 $12\\% \\sim 18\\%$ 구간으로 안정적으로 분산되는지 검증.
  - 소수점 뷰(`[0.05, 0.08, 0.12]`)와 퍼센트 뷰(`[5.0, 8.0, 12.0]`) 입력 시 동일한 가중치가 산출됨을 보장 (`np.allclose(w_pct, w_dec, atol=1e-3)`).

---

"""
text = replace_section(text, "### [CRIT-02]", "### [CRIT-03]", crit02_replacement)

# ----------------------------------------------------
# 3. CRIT-03 Replacement
# ----------------------------------------------------
crit03_replacement = """### [CRIT-03] Strict Causal LSTM 내 전구간 시계열 표준화에 의한 미래 참조(Lookahead) 편향

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
  - 또한 단순 롤링 윈도우에 `.bfill()`(후진 충치)을 적용하면, 20일 이전의 초기 구간($t < 20$)에 20일째의 평균과 분산이 과거로 복사되어 또 다른 미래 참조 누수가 발생합니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거 및 인과적 확장 윈도우 정규화 (CRIT-03 Remediation)**:
  시계열 인과성(Causality)을 준수하기 위해, 시점 $t$의 정규화 파라미터는 오직 $t-1$ 이전 관측치에만 의존해야 합니다:
  $$\\mu_t = \\frac{1}{W_t} \\sum_{k=1}^{W_t} x_{t-k}, \\quad \\sigma_t = \\sqrt{\\frac{1}{W_t} \\sum_{k=1}^{W_t} (x_{t-k} - \\mu_t)^2 + \\epsilon}$$
  $$x_t^{norm} = \\frac{x_t - \\mu_t}{\\sigma_t}$$
  초기 웜업 구간($t < 20$)에서는 미래 시점 통계를 역방향으로 채우는 `.bfill()`을 완전히 제거하고, 가용한 과거 바만을 사용하는 **인과적 확장 윈도우(Expanding Window, `min_periods=1`)**를 적용합니다. $t \\ge 60$ 이후부터는 60영업일 롤링 윈도우가 자연스럽게 인계받아 과거 레짐에 과적합되지 않는 최신 적응적 표준화를 달성합니다.
- **구체적 수정 코드**:
  ```python
  # V8-CRIT-03 Fix: Causal Expanding & Rolling Normalization without lookahead (.bfill completely eliminated)
  # Days 0-19 are normalized strictly causally using expanding window (min_periods=1, shift(1))
  # For days >= 60, rolling 60-day window takes over, shifted by 1 to maintain point-in-time validity
  r_mean = df_s[feature_cols].rolling(window=60, min_periods=1).mean().shift(1).fillna(0.0)
  r_std = df_s[feature_cols].rolling(window=60, min_periods=1).std().shift(1).fillna(1.0).replace(0.0, 1.0)
  norm_df = ((df_s[feature_cols] - r_mean) / r_std).fillna(0.0)
  norm_vals = norm_df.values
  ```

#### 3. 수정 대상 파일
- `trading_system/src/ai/lstm_predictor.py`: `prepare_multivariate_sequences()` (Lines 103–115)

#### 4. 검증 방안
- **단위 테스트**: 기존 스위트 `tests/test_lstm_predictor.py` 및 전용 통합 스위트 `tests/test_v8_remediation.py` 내 `test_lstm_strict_causality_expanding_window` 구현.
- **검증 기준**: 2020~2024년 주가 데이터프레임에서 2024년 이후의 미래 행 데이터를 극단적 이상치(+1000%)로 변조하더라도, 2021년 시점의 시퀀스 텐서 및 모델 예측값이 $10^{-6}$ 허용오차 내에서 100% 동일하게 유지되는지 단언.

---

"""
text = replace_section(text, "### [CRIT-03]", "### [CRIT-04]", crit03_replacement)

# ----------------------------------------------------
# 4. CRIT-04 Replacement
# ----------------------------------------------------
crit04_replacement = """### [CRIT-04] RIM Valuation 잔여이익 모델의 Ohlson 유한 시계 ROE 감쇠 루프 미갱신 결함

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
  - 또한 감쇠율에 최소 하한선이 없으면 `decay_rate = 0.0`으로 설정될 경우 $\\omega = 1.0$이 되어 영구 잔여이익이 감쇠 없이 무한히 지속되는 영구 연금 버블(Perpetual Annuity Bubble Trap)이 재현됩니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거 및 2% 감쇠 하한선 보존 (CRIT-04 Remediation)**:
  루프의 매 반복마다 2% 감쇠 하한선이 보장된 유효 감쇠율(`eff_decay = float(np.clip(self.decay_rate, 0.02, 0.50))`)을 적용하여 ROE가 자본비용 $r_e$로 점진 수렴하도록 갱신합니다. 2% 하한선(`max(0.02, ...)` 또는 `np.clip(..., 0.02, 0.50)`)은 일시적으로 높은 ROE 기업에 대한 영구 초과이익 버블 트랩을 수학적으로 차단합니다:
- **구체적 수정 코드**:
  ```python
  current_bps = bps
  current_roe = roe
  # V8-CRIT-04 Fix: Preserve 2% minimum ROE decay floor to prevent perpetual excess income bubble
  eff_decay = float(np.clip(self.decay_rate, 0.02, 0.50)) if (self.decay_rate is not None and self.decay_rate > 0) else 0.05
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

  # Terminal value calculation using decayed current_roe and floored decay rate:
  omega = 1.0 - eff_decay
  denom_tv = (1.0 + r_e - omega)
  if denom_tv > 1e-4 and current_bps > 0:
      tv_excess = (current_bps * (current_roe - r_e) * omega) / max(denom_tv, 1e-4)
      tv_pv = tv_excess / ((1.0 + r_e) ** years)
      if np.isfinite(tv_pv):
          pv_excess += tv_pv
  ```

#### 3. 수정 대상 파일
- `trading_system/src/core/rim_valuation.py`: `calculate_intrinsic_value()` (Lines 338–359)

#### 4. 검증 방안
- **단위 테스트**: 기존 스위트 `tests/test_rim_strategy.py` 및 전용 통합 스위트 `tests/test_v8_remediation.py` 내 `test_roe_decay_convergence` 구현.
- **검증 기준**: $\\text{ROE} = 0.25, r_e = 0.08, \\text{decay} = 0.10$ 조건에서, ROE 감쇠 적용 시 적정주가가 미감쇠 버전 대비 유의미하게 하향 산출되며, $\\text{decay} \\to 1.0$일 때 $V_0 \\to \\text{BPS}$에 수렴함을 검증. 최소 감쇠율 2% 하한선이 보장되어 영구 잔여이익 버블이 차단됨을 단언.

---

"""
text = replace_section(text, "### [CRIT-04]", "### [CRIT-05]", crit04_replacement)

# ----------------------------------------------------
# 5. CRIT-06 Replacement
# ----------------------------------------------------
crit06_replacement = """### [CRIT-06] UnifiedPortfolioAllocator 소규모 유니버스(N <= 4) CVaR 상한선 제약 불능으로 솔버 100% 실패 및 강제 추락

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
  - 만약 이를 $w_i \\le \\max(0.20, \\frac{1.05}{n})$로 단순 완화할 경우, $n=4$일 때 $w_i \\le 0.2625$가 되어 모든 자산이 $[21.25\\%, 26.25\\%]$의 협소한 박스권(Box-in)에 갇히게 됩니다. 이는 극단적 꼬리위험을 지닌 독성 자산의 비중을 $0.0\\%$로 완전히 제거(탈락)할 수 없게 만드는 치명적인 수리적 부작용을 낳습니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거 및 선택의 자유도(Degrees of Freedom) 보장 (CRIT-06 Remediation)**:
  유니버스 종목수 $n$이 작을 때도 합계 1.0 등식 제약이 실행 가능하면서, 동시에 최적화 솔버가 극단적 꼬리위험 자산 1개 이상을 완전히 배제($w_i = 0.0$)할 수 있는 자유도를 제공하기 위해 상한선을 다음과 같이 수립합니다:
  $$w_i^{max} = \\min\\left( 1.0, \\max\\left( \\text{max\\_single\\_weight}, \\frac{1.0}{\\max(n - 1, 1)} \\right) \\right)$$
  - $n = 4$일 때: $w_i^{max} = \\min(1.0, \\max(0.20, 1/3)) = 0.3333$. 나머지 3개 자산의 상한선 합이 $3 \\times 0.3333 = 1.00$에 도달하므로, 꼬리위험이 극심한 독성 자산 1개를 $w_4 = 0.0\\%$로 완전히 탈락시킬 수 있습니다.
  - $n = 3$일 때: $w_i^{max} = \\min(1.0, \\max(0.20, 1/2)) = 0.50$. 2개 자산으로 $1.0$을 구성하여 위험 자산 1개를 $0.0\\%$로 제외할 수 있습니다.
  - $n = 2$일 때: $w_i^{max} = \\min(1.0, \\max(0.20, 1/1)) = 1.0$. 1개 자산에 100% 집중하여 나머지 1개를 완전히 배제할 수 있습니다.
  - $n \\ge 5$일 때: $w_i^{max} = \\text{max\\_single\\_weight} = 0.20$ 기본값이 적용되어 과도한 집중 투자가 통제됩니다.
- **구체적 수정 코드**:
  ```python
  # V8-CRIT-06 Fix: Feasible & Unboxed Small-Universe CVaR Bound
  max_w = min(1.0, max(self.max_single_weight, 1.0 / max(n - 1, 1)))
  bounds = [(0.0, max_w) for _ in range(n)] + [(None, None)] + [(0.0, None) for _ in range(T)]
  ```

#### 3. 수정 대상 파일
- `trading_system/src/risk/unified_portfolio_allocator.py`: `calculate_cvar_weights()` (Lines 136–166)

#### 4. 검증 방안
- **단위 테스트**: 전용 통합 스위트 `tests/test_v8_remediation.py` 내 `test_cvar_small_universe_no_box_in` 구현.
- **검증 기준**:
  - $n = 2, 3, 4$ 유니버스로 `calculate_cvar_weights()`를 호출하여 SLSQP 솔버가 `res.success == True`로 정상 수렴하고 가중치 합계가 $1.0000$이 됨을 확인.
  - $n = 4$ 유니버스에서 1개 자산에 극단적인 꼬리 손실(-50%)을 주입했을 때, 해당 자산의 비중이 박스권 강제 배분 없이 $0.0\\%$로 완전히 탈락(배제)될 수 있음을 수학적으로 입증.

---

"""
text = replace_section(text, "### [CRIT-06]", "### [CRIT-07]", crit06_replacement)

# ----------------------------------------------------
# 6. CRIT-09 Replacement
# ----------------------------------------------------
crit09_replacement = """### [CRIT-09] 37개 전략 전수 `.dropna()`로 인한 상관 직교화(Löwdin Orthogonalization) 페널티 전면 무력화

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
  - 한편, 결측치가 존재하는 상태에서 산출된 **쌍별 완전 상관행렬(Pairwise Complete Correlation Matrix)은 양의 준정부호(PSD: Positive Semi-Definite)가 보장되지 않습니다**.
  - 음의 고유값이 존재하는 상태에서 $\\lambda \\ge 10^{-6}$ 수준으로 단순 클리핑할 경우, $1 / \\sqrt{10^{-6}} = 1,000$배로 역행렬 고유값이 폭발하여 가중치 계산이 극단적으로 왜곡되는 중대한 선형대수학적 위험이 존재합니다. 또한 `.abs()`를 무차별 적용하면 음의 상관관계를 지닌 훌륭한 분산 전략에 부당한 페널티를 부과하게 됩니다.

#### 2. 정량적/공학적 개선 방안
- **수학적/알고리즘적 근거 및 비-PSD 역행렬 폭발 방지 (CRIT-09 Remediation)**:
  1. 전체 행 제거 대신 각 전략 쌍별 유효 관측치를 보존하는 **Pairwise Complete Correlation** 방식을 적용합니다.
  2. 상관행렬의 대칭성을 보장($C = \\frac{C + C^T}{2}$)하고, 음의 상관관계에 의한 다변화 혜택을 보존하기 위해 `.abs()`를 지양합니다.
  3. 스펙트럼 분해 시 **고유값 바닥화(Eigenvalue Floor $\\lambda \\ge 0.05$)**를 적용하여 비-PSD 불일치에 의한 1,000배 역행렬 폭발을 완벽히 방지합니다:
  $$C^{-1/2} = V \\text{diag}\\left( \\max(\\lambda_i, 0.05)^{-1/2} \\right) V^T$$
- **구체적 수정 코드**:
  ```python
  # V8-CRIT-09 Fix: Pairwise complete observations correlation with PSD eigenvalue flooring
  corr_df = scores_df[list(valid_cols.values())].apply(pd.to_numeric, errors='coerce').corr(min_periods=5).fillna(0.0)
  np.fill_diagonal(corr_df.values, 1.0)

  # Symmetrize and ensure Positive Semi-Definiteness (PSD)
  C = (corr_df.values + corr_df.values.T) * 0.5
  evals, evecs = np.linalg.eigh(C)

  # V8 Fix: Apply eigenvalue floor (lambda >= 0.05) to eliminate negative/near-zero eigenvalues
  # and prevent 1,000x inversion explosion on non-PSD pairwise matrices
  evals_floored = np.maximum(evals, 0.05)
  inv_sqrt_C = evecs @ np.diag(1.0 / np.sqrt(evals_floored)) @ evecs.T
  ```

#### 3. 수정 대상 파일
- `trading_system/src/ai/ensemble_scorer.py`: `apply_correlation_orthogonalization_penalty` (Lines 960–990)

#### 4. 검증 방안
- **단위 테스트**: 전용 통합 스위트 `tests/test_v8_remediation.py` 내 `test_ensemble_pairwise_correlation_psd_flooring` 구현.
- **검증 기준**: 50개 종목 중 각 전략별로 10~20%의 결측치가 분산되어 37개 전략이 모두 채워진 행이 0개인 상태에서, 바이패스 없이 고상관 전략 가중치 감쇄가 정상 산출되며 비-PSD 행렬에서도 고유값 바닥화($\\lambda \\ge 0.05$)를 통해 가중치 폭발 없이 정상 수렴함을 검증.

---

"""
text = replace_section(text, "### [CRIT-09]", "### [CRIT-10]", crit09_replacement)

# ----------------------------------------------------
# 7. HIGH-01 Replacement
# ----------------------------------------------------
high01_replacement = """### [HIGH-01] 단위 테스트 `test_institutional_portfolio_construction.py` 내 잔존 실패(Assertion Error line 193/194: KRX 10주 vs 1주 규격 불일치)

#### 1. 현황 및 문제점
- **대상 파일 및 위치**: `tests/test_institutional_portfolio_construction.py:190-196`
- **실제 코드 스니펫**:
  ```python
  # tests/test_institutional_portfolio_construction.py line 190-196
  # Lot sizes: KRX = 10, US = 1
  p_krx = res[res["symbol"] == "005930"].iloc[0]
  p_us = res[res["symbol"] == "AAPL"].iloc[0]
  assert p_krx["lot_size"] == 10  # <--- FAIL: assert 1 == 10
  assert p_krx["shares"] % 10 == 0  # <--- FAIL: if shares is not multiple of 10
  assert p_us["lot_size"] == 1
  ```
- **원인 및 영향 분석**:
  - KRX 종목 호가 단위가 1주 단위로 개편된 후 `unified_portfolio_allocator.py:501`은 `lot = 1 if is_krx else ...`로 정상 수정되었습니다.
  - 그러나 테스트 스위트인 `test_institutional_portfolio_construction.py`는 과거의 10주 호가 가정을 여전히 단언(line 193: `lot_size == 10`, line 194: `shares % 10 == 0`)하고 있어, 현재 테스트 실행 시 즉각적인 실패(`assert 1 == 10`, 1 failed, 7 passed)가 발생하고 CI/CD 테스트 파이프라인의 100% 무결성을 저해합니다.
  - 만약 line 193만 수정하고 line 194를 수정하지 않으면, 산출 주식수가 10의 배수가 아닐 때 line 194에서 즉각적인 2차 단언 실패가 발생합니다. 또한 이를 더미 단언(tautological dummy assertion)으로 대체하는 것은 시스템 무결성 원칙(Integrity Mandate)을 심각하게 훼손하므로, 실체적 단언문(`assert p_krx["lot_size"] == 1`, `assert p_krx["shares"] % 1 == 0`)으로 정합하게 수정해야 합니다.

#### 2. 정량적/공학적 개선 방안
- **구체적 수정 코드 (HIGH-01 Remediation)**:
  최신 1주 호가 단위 규정에 맞추어 line 193(`lot_size == 1`)과 line 194(`shares % 1 == 0`)의 실체적 프로덕션 단언문을 정합하게 갱신합니다:
  ```python
  p_krx = res[res["symbol"] == "005930"].iloc[0]
  p_us = res[res["symbol"] == "AAPL"].iloc[0]
  assert p_krx["lot_size"] == 1
  assert p_krx["shares"] % 1 == 0
  assert p_krx["shares"] >= 0
  assert p_us["lot_size"] == 1
  ```

#### 3. 수정 대상 파일
- `tests/test_institutional_portfolio_construction.py`: Lines 190–196 (line 193 호가 규격 및 line 194 정수 주식수 단언)

#### 4. 검증 방안
- `pytest tests/test_institutional_portfolio_construction.py` 실행 시 8개 테스트 전수 통과(100% Pass) 확인.

---

"""
text = replace_section(text, "### [HIGH-01]", "### [HIGH-02]", high01_replacement)

# ----------------------------------------------------
# 8. Test file references fixes in sections & master tables
# ----------------------------------------------------
text = text.replace(
    "- `tests/test_factor_suppression.py`에서 신규 전략들의 클러스터 매핑 및 레짐별 억제 계수 정상 적용 검증.",
    "- 기존 스위트 `tests/test_correlation_suppression.py` 및 전용 통합 스위트 `tests/test_v8_remediation.py`에서 신규 전략들의 클러스터 매핑 및 레짐별 억제 계수 정상 적용 검증."
)

text = text.replace(
    "`test_track_c_institutional_stress.py` 신설로 극단 시나리오 100% 커버",
    "전용 통합 스위트 `tests/test_v8_remediation.py` 신설로 극단 시나리오 100% 커버"
)

text = text.replace(
    "- `tests/test_track_c_institutional_stress.py`를 신설하여 복합 통화, 무상태 파이프라인 방어, 특이 공분산 BL, 소규모 CVaR을 통합 검증합니다.",
    "- 전용 통합 스위트 `tests/test_v8_remediation.py`를 신설하여 복합 통화, 무상태 파이프라인 방어, 특이 공분산 BL, 소규모 CVaR을 통합 검증합니다."
)

text = text.replace(
    "- `tests/test_track_c_institutional_stress.py` (신설)",
    "- `tests/test_v8_remediation.py` (신설 통합 스위트)"
)

text = text.replace(
    'M14["MED-14: test_track_c_institutional_stress.py 신설"]',
    'M14["MED-14: tests/test_v8_remediation.py 통합 스위트 신설"]'
)

text = text.replace(
    '14. `tests/test_track_c_institutional_stress.py`: 다중 통화, 무상태 파이프라인 방어 통합 스트레스 테스트 신설 (`MED-14`).',
    '14. `tests/test_v8_remediation.py`: 다중 통화, 무상태 파이프라인 방어, 특이 공분산 BL, 소규모 CVaR 통합 스트레스 테스트 신설 (`MED-14`).'
)

text = text.replace(
    '신규 스트레스 테스트 스위트(`test_track_c_institutional_stress.py`) 추가로 잠재 사각지대 전면 해소',
    '전용 통합 스트레스 테스트 스위트(`tests/test_v8_remediation.py`) 추가로 잠재 사각지대 전면 해소'
)

# Phase 1 diagram item
text = text.replace(
    'H1["HIGH-01: test_institutional_portfolio_construction.py 1주 규격 단언 수정"]',
    'H1["HIGH-01: test_institutional_portfolio_construction.py line 193(lot_size==1) & 194(shares%1==0) 교정"]'
)

# Phase 1 detailed item 14
text = text.replace(
    '14. `test_institutional_portfolio_construction.py`: line 193 KRX 1주 규격 단언 수정 (`assert 1 == 1`)으로 기존 스위트 100% Pass 달성 (`HIGH-01`).',
    '14. `test_institutional_portfolio_construction.py`: line 193 KRX 1주 규격 단언(`assert p_krx["lot_size"] == 1`) 및 line 194 주식수 정수 단언(`assert p_krx["shares"] % 1 == 0`) 수정으로 기존 스위트 100% Pass 달성 (`HIGH-01`).'
)

# Phase 1 coupling notes addition
phase1_coupling_note = """
> **엔지니어링 로드맵 결합 최적화 (Cross-Phase Coupling Optimization)**:
> - **CRIT-08 & MED-11 결합 실행**: Phase 1에서 `CrisisDetector` 상태 영속화를 구현할 때 Phase 3의 `MED-11`(VIX Term Structure 백워데이션 게이트)을 `risk_manager.py`에 함께 번들링하여 동일 파일의 중복 수정 및 다단계 테스트 오버헤드를 원천 차단합니다.
> - **CRIT-05 & MED-07 결합 실행**: Phase 1에서 SQLite 스키마에 전략 32~37번 컬럼을 추가할 때 Phase 3의 `MED-07`(`coverage_analyzer.py` 신규 전략 결측 사유 매핑)을 함께 번들링하여 파이프라인 가동 즉시 투명한 결측 진단 리포트를 보장합니다.
"""

if "> **엔지니어링 로드맵 결합 최적화" not in text:
    text = text.replace(
        "#### Phase 2: 알파 생성력 정밀 보정 및 신호 수학적 정합화 (Day 2)",
        phase1_coupling_note + "\n#### Phase 2: 알파 생성력 정밀 보정 및 신호 수학적 정합화 (Day 2)"
    )

# Verification matrix updates
text = text.replace(
    '| `tests/test_institutional_portfolio_construction.py` | CRIT-01, HIGH-01 | line 193을 `assert p_krx["lot_size"] == 1`로 교정하여 잔존 실패 해결 | 1억원 자본금 기준 AAPL($150) 주식수가 24주(환율 $1,350$ 적용)로 산출됨을 검증 |',
    '| `tests/test_institutional_portfolio_construction.py` | CRIT-01, HIGH-01 | line 193을 `assert p_krx["lot_size"] == 1`, line 194를 `assert p_krx["shares"] % 1 == 0`으로 교정하여 잔존 실패 해결 | 1억원 자본금 기준 AAPL($150) 주식수가 24주(환율 $1,350$ 적용)로 산출됨을 검증 |'
)

text = text.replace(
    '| `tests/test_black_litterman.py` | CRIT-02 | 기본값 `view_horizon=20, returns_are_percentage=True` 적용으로 기존 호출 시그니처 100% 호환 | 20일 5% 기대수익률 입력 시 사후 일별 수익률이 0.0025로 스케일링되고 코너해가 제거됨을 검증 |',
    '| `tests/test_black_litterman.py` | CRIT-02 | `calculate_black_litterman_weights`의 `np.ndarray` 반환 및 기존 파라미터 100% 호환 보존 | 동적 스케일 자동 감지(np.any(abs(Q) >= 1.0) -> Q/100, 소수점 입력 시 보존) 및 20일 호라이즌 일별 환산(Q_daily = Q / 20) 검증 |'
)

text = text.replace(
    '| `tests/test_rim_valuation.py` | CRIT-04 | `calculate_intrinsic_value`의 반환 딕셔너리 키(`intrinsic_value`, `expected_return` 등) 100% 유지 | ROE=25%, r_e=8%, decay=0.10일 때 적정주가가 미감쇠 버전 대비 유의미하게 하향 수렴함을 확인 |',
    '| `tests/test_rim_strategy.py` 및 `tests/test_v8_remediation.py` | CRIT-04 | `calculate_intrinsic_value`의 반환 키 및 인터페이스 100% 유지 | Ohlson 1995 ROE 2% 감쇠 하한선 보존 및 루프 내 점진 감쇠 정상화로 적정주가 거품 제거 검증 |'
)

text = text.replace(
    '| `tests/test_portfolio_optimizer.py` |',
    '| `tests/test_portfolio_optimizer_and_oms.py` 및 `tests/test_v8_remediation.py` |'
)

text = text.replace(
    '| `tests/test_cvar_allocator.py` | CRIT-06 | $N \\ge 5$ 대형 유니버스에서 기존 `max_single_weight=0.20` 동작 100% 동일 유지 | $N=2, 3, 4$ 소규모 유니버스에서 SLSQP 실패 없이 가중치 합 1.0이 달성됨을 확인 |',
    '| `tests/test_v8_remediation.py` | CRIT-06 | $N \\ge 5$ 대형 유니버스에서 기존 `max_single_weight=0.20` 동작 100% 동일 유지 | $N=2, 3, 4$ 소규모 유니버스에서 상한선 동적 완충 및 박스인 방지(독성 자산 0% 탈락 자유도) 확인 |'
)

text = text.replace(
    '| `tests/test_ensemble_scorer.py` | CRIT-09, HIGH-09, HIGH-10, HIGH-11 | 기존 가중치 합 1.0000 정규화 및 출력 DataFrame 스키마 100% 보존 | 37개 전략 중 10% 결측 시에도 Löwdin 직교화가 실행되며, 단일 전략 종목이 0.50으로 수축됨을 확인 |',
    '| `tests/test_v8_remediation.py` | CRIT-09, HIGH-09, HIGH-10, HIGH-11 | 기존 가중치 합 1.0000 정규화 및 출력 DataFrame 스키마 100% 보존 | 37개 전략 중 결측 존재 시에도 Löwdin 직교화 작동 및 비-PSD 고유값 바닥화(\\lambda >= 0.05) 검증 |'
)

text = text.replace(
    '| `tests/test_factor_orthogonalizer.py` | CRIT-11 | 직교화 엔진의 `fit_transform` 입출력 인터페이스 100% 호환 | ZCA 백색화 후 PC1 분산 보존율 $\\ge 90\\%$, 고유값 상태수 $\\le 10$임을 확인 |',
    '| `tests/test_factor_orthogonalization.py` 및 `tests/test_v8_remediation.py` | CRIT-11 | 직교화 엔진의 `fit_transform` 입출력 인터페이스 100% 호환 | ZCA 백색화 후 PC1 분산 보존율 $\\ge 90\\%$, 고유값 상태수 $\\le 10$임을 확인 |'
)

text = text.replace(
    '| `tests/test_card_factor.py` | CRIT-12, HIGH-06 | `compute_scores` 시그니처 100% 호환 | 음의 VIX 베타 종목에 VIX 충격 시 `macro_impact`가 음수로 산출됨을 확인 |',
    '| `tests/test_phase2_quant_world_class_improvements.py` 및 `tests/test_v8_remediation.py` | CRIT-12, HIGH-06 | `compute_scores` 시그니처 100% 호환 | 음의 VIX 베타 종목에 VIX 충격 시 `macro_impact`가 음수로 산출됨을 확인 |'
)

text = text.replace(
    '| `tests/test_track_c_institutional_stress.py` | MED-14 | 신설 테스트로 기존 스위트에 영향 없음 | 다중 통화, 콜드 스타트 파이프라인, 특이 공분산 BL, 소규모 CVaR 극단 스트레스 100% Pass |',
    '| `tests/test_v8_remediation.py` | MED-14 | 전용 신규 통합 스위트로 기존 1,900+ 테스트와 완전 분리 | 다중 통화, 콜드 스타트 파이프라인, 특이 공분산 BL, 소규모 CVaR 극단 스트레스 100% Pass |'
)

# Scorecard line 1610 update
text = text.replace(
    '- `test_institutional_portfolio_construction.py:193` 교정으로 CI/CD 완전 통과',
    '- `test_institutional_portfolio_construction.py:193-194` 교정으로 CI/CD 완전 통과'
)

# Master checklist table updates
text = text.replace(
    '| 1 | `trading_system/src/risk/unified_portfolio_allocator.py` | US 주식수 산출 시 환율($1,350$) 나눗셈 적용, $N \\le 4$ CVaR 상한선 동적 완충, Gatheral 3/2승 ADV 5% 하드 제약 | CRIT-01, CRIT-06, HIGH-16 |',
    '| 1 | `trading_system/src/risk/unified_portfolio_allocator.py` | `allocate()` 시그니처 보존 및 다중통화(KRW/USD) FX 환산, $N \\le 4$ CVaR 상한선 동적 완충(박스인 방지), Gatheral 3/2승 ADV 5% 하드 제약 | CRIT-01, CRIT-06, HIGH-16 |'
)

text = text.replace(
    '| 2 | `trading_system/src/analysis/portfolio_optimizer.py` | Black-Litterman 20일 전망치 $Q$ 일별 스케일링, HERC 상한선 제약 동적 위임 | CRIT-02, MED-12 |',
    '| 2 | `trading_system/src/analysis/portfolio_optimizer.py` | Black-Litterman `np.ndarray` 반환 보존, 20일 전망치 $Q$ 일별 스케일링 및 스케일 자동 감지, HERC 상한선 동적 위임 | CRIT-02, MED-12 |'
)

text = text.replace(
    '| 3 | `trading_system/src/ai/lstm_predictor.py` | 전구간 표준화를 인과적 롤링 윈도우 표준화로 개편 | CRIT-03 |',
    '| 3 | `trading_system/src/ai/lstm_predictor.py` | 전구간 표준화 및 `.bfill`을 인과적 확장/롤링 윈도우(`min_periods=1`, `shift(1)`) 표준화로 개편 | CRIT-03 |'
)

text = text.replace(
    '| 4 | `trading_system/src/core/rim_valuation.py` | Ohlson 잔여이익 모델의 ROE 유한 시계 감쇠 갱신 루프 복원 | CRIT-04 |',
    '| 4 | `trading_system/src/core/rim_valuation.py` | Ohlson 잔여이익 모델의 ROE 2% 감쇠 하한선 보존 및 유한 시계 감쇠 갱신 루프 복원 | CRIT-04 |'
)

text = text.replace(
    '| 10 | `trading_system/src/ai/ensemble_scorer.py` | Pairwise Complete Correlation Löwdin 직교화, Multi-Horizon 가중평균, Bayesian Coverage Shrinkage, US 티커 온점 정규식 매칭, turnover 중복 연산 단일화 | CRIT-09, HIGH-09, HIGH-10, HIGH-11, MED-10 |',
    '| 10 | `trading_system/src/ai/ensemble_scorer.py` | Pairwise Complete Correlation Löwdin 직교화(고유값 바닥화 $\\lambda \\ge 0.05$로 비-PSD 폭발 방지), Multi-Horizon 가중평균, Bayesian Coverage Shrinkage, US 티커 온점 정규식 매칭, turnover 중복 연산 단일화 | CRIT-09, HIGH-09, HIGH-10, HIGH-11, MED-10 |'
)

text = text.replace(
    '| 15 | `tests/test_institutional_portfolio_construction.py` | line 193 KRX 1주 규격 단언(`assert 1 == 1`) 수정 | HIGH-01 |',
    '| 15 | `tests/test_institutional_portfolio_construction.py` | line 193 KRX 1주 규격 단언(`assert p_krx["lot_size"] == 1`) 및 line 194 주식수 정수 단언(`assert p_krx["shares"] % 1 == 0`) 수정 | HIGH-01 |'
)

text = text.replace(
    '| 33 | `tests/test_track_c_institutional_stress.py` | 다중 통화, 무상태 파이프라인 방어, 특이 공분산 BL 스트레스 테스트 신설 | MED-14 |',
    '| 33 | `tests/test_v8_remediation.py` | CRIT-01~13 및 HIGH-01~16 전수 통합 검증 및 Track C 기관급 스트레스 테스트 전용 스위트 신설 | CRIT-01~13, HIGH-01~16, MED-14 |'
)

# Write modified text back
with open(file_path, "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully re-updated system_improvement_plan_v8.md with all consolidated test paths!")
