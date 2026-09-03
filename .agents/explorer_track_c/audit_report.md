# Track C Audit Report: Risk Management, Portfolio Optimization, Execution OMS & Test Blindspots

- **Target System**: 37-Strategy Integrated Stock Trading System (KRX: KOSPI, KOSDAQ / US: SP500, NASDAQ, RUSSELL2000)
- **Auditor**: Explorer Track C
- **Date**: 2026-09-03
- **Scope**:
  1. Portfolio Optimization & Allocation (`unified_portfolio_allocator.py`, `portfolio_allocator.py`, `portfolio_optimizer.py`, `turnover_optimizer.py`)
  2. Macro Risk & Crisis Detection (`risk_manager.py`)
  3. Execution OMS & Execution Scheduling (`oms_engine.py`, `almgren_chriss.py`, `slippage_feedback.py`)
  4. Comprehensive Test Suite Blindspots (1,900+ tests across `tests/`)

---

## Executive Summary

Track C 정밀 코드 감사 결과, 포트폴리오 최적화 엔진, 거시 리스크 관리, OMS 주문 집행 게이트 및 테스트 인프라 전반에서 실전 자금 운용 시 치명적 손실 또는 매매 마비를 초래할 수 있는 **5건의 Critical 결함, 5건의 High 결함, 4건의 Medium 결함**이 식별되었습니다.

가장 시급한 결함은 다음과 같습니다:
1. **US 종목 주문 수량 1,350배 폭증 버그 (`unified_portfolio_allocator.py`)**: KRW 배분 금액을 USD 주가로 나눌 때 환율 변환이 누락되어, 실제 매수해야 할 주식수보다 약 1,350배 많은 수량이 산출되는 치명적 단위 불일치.
2. **Black-Litterman 20일 전망치 vs 일별 공분산 시계열 불일치 (`portfolio_optimizer.py`)**: 20일 누적 기대수익률($Q$)과 일별 공분산($\Sigma$)의 단위 불일치로 마코위츠 이차 효용함수가 선형으로 붕괴하여 단일 종목 몰빵 코너해를 유발하고, 임의의 0.50 임계치로 인한 100배 단절 불연속성 존재.
3. **소규모 유니버스($N \le 4$) CVaR 최적화 상한선 불능 (`unified_portfolio_allocator.py`)**: 단일 종목 상한선(0.20)이 $N < 5$일 때 비중 합 1.0 등식 제약과 충돌하여 SLSQP 솔버가 100% 확률로 실패하고 역변동성 가중치로 강제 추락.
4. **USD 계좌 리밸런싱 영구 교착(Deadlock) (`turnover_optimizer.py`, `portfolio_allocator.py`)**: 50,000원 단위 임계치가 달러($100,000 USD) 계좌에 그대로 적용되어 $50,000 미만의 정상 리밸런싱이 전면 차단되는 현상.
5. **파이프라인 상 CrisisDetector 무상태(Stateless) 생성 (`run_pipeline.py`)**: 매 파이프라인 주기마다 인스턴스가 초기화되고 상태 복원이 누락되어 VIX 속도(`vix_roc`), 낙폭 가속도(`dd_speed`), 거시 Z-score가 영구히 0으로 고정되는 위험 관리 기능 마비.
6. **단위 테스트 잔존 실패 (`test_institutional_portfolio_construction.py`)**: KRX 1주 단위 변경 후 테스트의 10주 가정이 갱신되지 않아 `assert 1 == 10` 실패 잔존.

---

## 1. Critical Priority Issues (치명적 결함)

### [CRITICAL-01] UnifiedPortfolioAllocator의 US 종목 주식수(Shares) 산출 시 환율 미적용으로 인한 1,350배 과대 주문 산출 결함

- **현황 및 문제점**:
  - 파일 및 위치: `trading_system/src/risk/unified_portfolio_allocator.py:494-506` (`allocate`)
  ```python
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
  - `alloc_amt`는 `w_final * total_portfolio_value`로 산출되어 **원화(KRW)** 단위입니다(예: 총자본 1억원 중 5% 배분 시 5,000,000 KRW).
  - 반면 미국 주식(AAPL, MSFT 등)의 `latest_prices[i]`는 **달러(USD)** 단위입니다(예: AAPL = $150.0).
  - 결과적으로 `raw_shares = int(5,000,000 // 150) = 33,333 주`가 산출됩니다.
  - 실제 필요한 정상 주문 수량은 약 24주($3,703.70 / $150)이나, 환율(1,350 KRW/USD)이 적용되지 않아 **33,333주 (약 500만 달러 = 67.5억원 규모)**로 계산되어 포트폴리오 자본금의 67배를 초과하는 비현실적인 주식수가 `unified_alloc_df['shares']`에 기입됩니다.
  - `oms_engine.py`는 과거 V6-25 패치를 통해 `effective_target_amount = target_amount / fx_rate`로 보정되었으나, 신규 도입된 포트폴리오 최적화기인 `unified_portfolio_allocator.py`의 `allocate` 메서드에는 환율 인자가 누락되어 심각한 단위 불일치가 발생합니다.

- **정량적/공학적 개선 방안**:
  - `allocate()` 메서드 시그니처에 `usdkrw_rate: float = 1350.0` 인자를 추가합니다.
  - 종목의 시장(`market`) 또는 통화(`currency`)가 KRX가 아닌 해외 주식인 경우 로컬 배분 금액을 `alloc_amt_local = alloc_amt / max(usdkrw_rate, 1.0)`으로 변환한 후 주식수를 계산합니다.
  ```python
  is_us = mkt in ["SP500", "NASDAQ", "RUSSELL2000", "US"] or not is_krx
  alloc_amt_local = (alloc_amt / max(usdkrw_rate, 1.0)) if is_us else alloc_amt
  raw_shares = int(alloc_amt_local // px) if px > 0 else 0
  ```

- **수정 대상 파일**:
  - `trading_system/src/risk/unified_portfolio_allocator.py`: `allocate`
  - `trading_system/run_pipeline.py`: line 4044-4051 (`usdkrw_rate` 인자 전달)

- **검증 방안**:
  - 1억원 자본금 포트폴리오에서 AAPL($150)에 5% 배분 시, 환율 1,350원 기준 `shares == 24`주, `allocation_amount == 5,000,000원`이 정확히 계산되는지 단위 테스트(`tests/test_institutional_portfolio_construction.py`)를 통해 검증.

---

### [CRITICAL-02] Black-Litterman 20일 전망수익률(Q)과 일별 공분산(Sigma) 시계열 불일치로 인한 마코위츠 효용함수 선형 붕괴

- **현황 및 문제점**:
  - 파일 및 위치: `trading_system/src/analysis/portfolio_optimizer.py:202-255` (`calculate_black_litterman_weights`)
  ```python
  # Prior returns Pi: Pi = delta * Sigma @ w_eq
  horizon_cov = cov_matrix
  Pi = risk_aversion * (horizon_cov @ w_eq)

  # Views Q (predicted returns)
  Q = np.asarray(predicted_returns, dtype=float)
  if len(Q) != n:
      logger.warning("Length of predicted_returns does not match cov_matrix. Using flat returns.")
      Q = np.zeros(n)
  # Normalize units: if Q is in percentage (> 0.5 mean), scale to decimal matching Pi
  if np.nanmean(np.abs(Q)) > 0.50:
      Q = Q / 100.0
  ...
  # Smooth strictly convex Markowitz-Black-Litterman Quadratic Utility:
  # min_w 0.5 * lambda * w^T Sigma_BL w - w^T (mu_BL - rf)
  excess_mu = mu_bl - rf_daily

  def objective(w):
      w = np.asarray(w)
      return 0.5 * lambda_aversion * float(w @ cov_bl @ w) - float(w @ excess_mu)
  ```
  - **시계열 호라이즌 불일치**:
    - `cov_matrix`는 일별 주가 변화율(`pct_change()`)로 산출된 **일별 공분산**($\Sigma \sim 0.0004$)입니다.
    - 이에 따라 균형 사전수익률 $\Pi = \delta \Sigma w_{eq}$ 역시 **일별 기대수익률**($\sim 0.0004 = 0.04\%$/day)입니다.
    - 반면 `predicted_returns`는 앙상블 파이프라인의 `ensemble_expected_return` (즉 **20일 누적 기대수익률**, 예: 5.0 = 5.0%)이 그대로 전달됩니다.
    - `if np.nanmean(np.abs(Q)) > 0.50: Q = Q / 100.0` 처리를 거쳐 $Q = 0.050$이 되지만, 이는 **20일치 누적 수익률**입니다. 일별 수익률로 환산하면 $0.050 / 20 = 0.0025$이어야 합니다.
    - $Q$가 일별로 환산되지 않고 일별 $\Pi$와 결합되면서, $Q - \Pi \approx 0.050 - 0.0004 = 0.0496$이 되어 전망 알파가 실제보다 20배 과대 반영됩니다.
    - 이후 마코위츠 효용함수에서 일별 분산 페널티 $\frac{\lambda}{2} w^\top \Sigma w \approx 0.5 \times 2.5 \times 0.0004 = 0.0005$인 반면, 선형 수익률 항 $w^\top (\mu - rf) \approx 0.050$이 되어 **수익률 항이 위험 페널티보다 100배 지배**하게 됩니다.
    - 그 결과 분산투자 효과가 완전히 상실되고, 가장 높은 예측치를 가진 종목에 단일 종목 한도(`max_single_stock_weight`)까지 채우는 **선형 코너해(Linear Corner Solution)**로 변질됩니다.
  - **0.50 임계치에 의한 100배 단절 불연속성**:
    - `if np.nanmean(np.abs(Q)) > 0.50:` 로직으로 인해, 평균 수익률 예측치가 0.49%인 경우 나눗셈이 수행되지 않아 0.49(49% 수익률)로 간주되고, 0.51%인 경우 0.0051(0.51%)로 100배 축소되는 임의의 불연속성이 존재합니다.

- **정량적/공학적 개선 방안**:
  - `calculate_black_litterman_weights`에 `view_horizon: int = 20` 인자를 추가합니다.
  - 전망수익률 $Q$가 퍼센트 단위일 경우 $Q_{daily} = Q / (view\_horizon \times 100.0)$으로 정규화하여 일별 공분산 $\Sigma$, 사전수익률 $\Pi$, 일별 무위험이자율 $rf_{daily}$와 단위를 완벽히 통일합니다.
  - 또는 공분산 행렬을 20일 기준 $\Sigma_{20} = view\_horizon \times \Sigma_{daily}$로 스케일 업하여 20일 관점에서 마코위츠 최적화를 수행합니다.

- **수정 대상 파일**:
  - `trading_system/src/analysis/portfolio_optimizer.py`: `calculate_black_litterman_weights`
  - `trading_system/src/risk/unified_portfolio_allocator.py`: `optimize_multi_model_blend`

- **검증 방안**:
  - 20일 앙상블 기대수익률 5% 종목과 일별 변동성 2% 종목 결합 시, 사후 일별 기대수익률이 정합하게 스케일링되고, 특정 종목 코너해가 아닌 위험 대비 초과수익에 비례하는 분산 포트폴리오 가중치가 산출되는지 확인하는 수학적 검증 테스트 구현.

---

### [CRITICAL-03] UnifiedPortfolioAllocator의 소규모 유니버스(N < 5) CVaR 최적화 경계조건 불능 및 강제 추락

- **현황 및 문제점**:
  - 파일 및 위치: `trading_system/src/risk/unified_portfolio_allocator.py:136-166` (`calculate_cvar_weights`)
  ```python
  def constr_sum_w(var):
      return float(np.sum(var[:n]) - 1.0)

  bounds = [(0.0, self.max_single_weight) for _ in range(n)] + [(None, None)] + [(0.0, None) for _ in range(T)]

  # Linear constraint for tail loss: u_t + R_t @ w + gamma >= 0
  def constr_tail_losses(var):
      w = var[:n]
      gamma = var[n]
      u = var[n + 1:]
      return u + (R @ w) + gamma
  ```
  - 기본값 `self.max_single_weight = 0.20`입니다.
  - 후보 종목수 $n$이 4개 이하인 경우($n \le 4$), 모든 종목에 상한선까지 최대로 부여해도 $\sum_{i=1}^n w_i \le 4 \times 0.20 = 0.80 < 1.0$입니다.
  - 제약조건 `sum(w) == 1.0`을 만족할 수 있는 실현 가능 영역(Feasible Region)이 존재하지 않아, SLSQP 최적화가 **100% 확률로 실패**합니다.
  - 실패 시 즉시 line 170의 `Fallback to inverse volatility`로 강제 추락하여, Rockafellar-Uryasev CVaR 꼬리위험 최소화 모델이 완전히 무력화됩니다.
  - `apply_portfolio_constraints`는 `cap_weight = max_single_stock_weight if (n * max_single_stock_weight > 1.0) else 1.0`로 완충하고 있으나, `calculate_cvar_weights`에는 이 상한선 동적 조정 처리가 누락되어 있습니다.

- **정량적/공학적 개선 방안**:
  - 유니버스 종목수 $n$에 대해 상한선 제약을 `eff_max_w = max(self.max_single_weight, 1.05 / n)`로 동적으로 설정하여, 작은 유니버스에서도 합계 1.0 등식 제약이 항상 만족되도록 보장합니다.
  ```python
  eff_max_w = max(self.max_single_weight, 1.05 / max(n, 1))
  bounds = [(0.0, eff_max_w) for _ in range(n)] + [(None, None)] + [(0.0, None) for _ in range(T)]
  ```

- **수정 대상 파일**:
  - `trading_system/src/risk/unified_portfolio_allocator.py`: `calculate_cvar_weights`

- **검증 방안**:
  - $n = 2, 3, 4$ 종목 유니버스로 `calculate_cvar_weights` 호출 시 SLSQP가 실패하지 않고, `res.success == True`로 꼬리 손실 최소화 가중치(합계 1.0)를 산출하는 단위 테스트 작성.

---

### [CRITICAL-04] TurnoverOptimizer 및 PortfolioAllocator의 USD 계좌 금액 기준(KRW 50,000) 오적용에 의한 리밸런싱 영구 교착(Deadlock)

- **현황 및 문제점**:
  - 파일 및 위치:
    1. `trading_system/src/execution/turnover_optimizer.py:75`
    ```python
    is_full_exit = (raw_w == 0.0 and curr_w > 0.0)
    is_fresh_entry = (curr_w == 0.0 and raw_w > 0.0)
    if not is_full_exit and not is_fresh_entry and (weight_delta < self.turnover_threshold_pct or amount_delta < self.min_rebalance_delta_krw):
        final_w = curr_w
        action = "HOLD"
    ```
    2. `trading_system/src/risk/portfolio_allocator.py:1297-1301`
    ```python
    # R9-2 Fix: Account scale-aware buffer band to suppress uneconomical tiny fraction rebalances
    min_trade_krw = 50_000.0
    min_weight_delta = min_trade_krw / max(1_000_000.0, portfolio_value) if portfolio_value > 0 else 0.001
    delta_i = max(delta_i, min_weight_delta)
    if w_targ > 0.0:
        delta_i = min(delta_i, max(w_targ * 0.40, min_weight_delta))
    ```
  - **TurnoverOptimizer 교착**:
    - `min_rebalance_delta_krw`의 기본값은 50,000.0원입니다.
    - 미국 포트폴리오를 운용하여 `total_capital = 100,000.0` (USD 단위)로 전달되는 경우, 10%의 비중 리밸런싱 주문 금액은 `amount_delta = 0.10 * 100,000 = $10,000`입니다.
    - 하지만 $10,000 < 50,000$ 조건이 참(True)이 되어, 10%($10,000) 규모의 막대한 포트폴리오 조정이 무조건 `HOLD` 처리되어 실행되지 않습니다. 심지어 40% 조정($40,000 < 50,000)까지도 차단됩니다.
  - **PortfolioAllocator 교착**:
    - `portfolio_value = 100,000` (USD) 전달 시, `min_weight_delta = 50,000 / 100,000 = 0.50` (50% 버퍼 밴드!)가 산출됩니다.
    - 그 결과 버퍼 밴드가 $[w_{target} - 0.50, w_{target} + 0.50]$으로 비정상 확대되어, 비중 변동이 50% 미만인 모든 종목의 리밸런싱이 영구히 억제됩니다.

- **정량적/공학적 개선 방안**:
  - 포트폴리오 자본금의 통화(`currency`) 또는 시장(`market`) 인자를 인식하여, USD 계좌인 경우 `min_trade_amount = 50.0` (USD)로 변환하거나, 환율(`usdkrw_rate`)을 나누어 `min_rebalance_delta = 50000.0 / fx_rate`로 스케일링합니다.
  - 또는 비중 제약과 절대금액 제약을 `or`가 아닌 `and` 조건 또는 포트폴리오 자본금 대비 상대 비율로만 안전하게 평가하도록 수정합니다.

- **수정 대상 파일**:
  - `trading_system/src/execution/turnover_optimizer.py`: `optimize_allocations`
  - `trading_system/src/risk/portfolio_allocator.py`: `compute_portfolio_rebalance`

- **검증 방안**:
  - $100,000 USD 규모의 미국 주식 계좌에서 8% 비중 조정 시 `HOLD`로 차단되지 않고 정상적인 `BUY`/`SELL` 주문이 생성되는지 검증하는 단위 테스트 작성.

---

### [CRITICAL-05] 파이프라인 상 CrisisDetector 무상태(Stateless) 생성으로 인한 VIX Velocity / Drawdown Speed / Macro Z-Score 영구 0 결함

- **현황 및 문제점**:
  - 파일 및 위치: `trading_system/run_pipeline.py:3696-3715`
  ```python
  # ── RiskManager & CrisisDetector Integration ──
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
  - `run_pipeline.py` 실행 시마다 항상 `crisis_detector = CrisisDetector(risk_mgr)`를 통해 새로운 빈 객체를 인스턴스화합니다.
  - `CrisisDetector` 클래스 내부에는 상태 파일 저장/복원 로직(`save_state`, `load_state`)이 구현되어 있음에도 불구하고, 파이프라인에서 **`load_state()`를 전혀 호출하지 않습니다.**
  - 이로 인해 `_vix_history`, `_dd_history`, `_oil_history`, `_usdkrw_history` 등 내부 큐의 길이가 **항상 1**로 유지됩니다.
  - `_score_vix` (line 323): `len(self._vix_history) >= 5`가 항상 거짓(False)이 되어 **VIX 속도(`vix_roc`)가 영구히 0.0**으로 계산됩니다.
  - `_score_drawdown` (line 333): `len(self._dd_history) >= 5`가 항상 거짓(False)이 되어 **낙폭 속도(`dd_speed`)가 영구히 0.0**으로 계산됩니다.
  - `_score_macro` (line 370): 거시 지표 롤링 표본 길이가 1이므로 표준편차가 0이 되어 **롤링 Z-Score 위험 점수가 사실상 무력화**됩니다.
  - 지정학적 유가 충격 부스터 (`len(self._oil_history) >= 4`) 역시 절대로 발동되지 못합니다.
  - 실행 후 `save_state()`도 호출하지 않아 `models/crisis_state.json` 파일이 영구히 생성되지 않는 무상태(Stateless) 루프에 갇혀 있습니다.

- **정량적/공학적 개선 방안**:
  - `run_pipeline.py`에서 `crisis_detector.load_state()`를 호출하여 이전 상태를 복원합니다.
  - 콜드 스타트(상태 파일 부재) 시에는 파이프라인에서 이미 수집된 `indicator_infer` 또는 `indicator_train`의 과거 60일 시계열(VIX, USD/KRW, WTI, TNX)을 `CrisisDetector`의 내부 큐에 일괄 주입(Warm-up)합니다.
  - 평가 완료 후 `crisis_detector.save_state()`를 반드시 호출하여 상태를 지속 영속화합니다.

- **수정 대상 파일**:
  - `trading_system/run_pipeline.py`: line 3696-3715
  - `trading_system/src/risk/risk_manager.py`: `CrisisDetector.seed_history_from_dataframe` 신설

- **검증 방안**:
  - 파이프라인 실행 시 과거 20일 지표가 `CrisisDetector`에 주입되어 `_vix_history` 길이가 20 이상 확보되고, VIX 5일 급등 시 `vix_roc`가 정상적으로 양수 가산되어 위기 단계가 민감하게 승격되는지 검증.

---

## 2. High Priority Issues (고위험 결함)

### [HIGH-01] Gate 8 합성 인버스 헤지 종목의 단일 종목(1등) 종속 편향 및 크로스마켓 트래킹 에러

- **현황 및 문제점**:
  - 파일 및 위치: `trading_system/src/execution/oms_engine.py:768-773`
  ```python
  # Gate 8: Synthetic Beta Inverse Hedge Overlay (Bear / Crisis regime)
  if "BEAR" in str(regime_label).upper() or "CRISIS" in str(regime_label).upper():
      try:
          from src.risk.portfolio_allocator import PortfolioAllocator
          first_market = str(top_predictions[0].get("market", "KOSPI")) if top_predictions else "KOSPI"
          hedge_info = PortfolioAllocator.compute_synthetic_inverse_hedge(
              portfolio_weights=portfolio_weights,
              market=first_market,
              regime_label=regime_label
          )
  ```
  - 약세장/위기 레짐 진입 시 포트폴리오의 베타를 헤지하기 위한 인버스 ETF(KODEX 200 선물인버스2X `114800` vs S&P500 `SH` vs 나스닥 `PSQ`)를 선택할 때, **`top_predictions[0]`의 시장 하나만으로 전체 포트폴리오의 헤지 종목을 결정**합니다.
  - 만약 포트폴리오의 90%가 한국 KOSPI 주식인데, 1위 추천 종목이 우연히 미국 주식(SP500)인 경우, 한국 주식 포트폴리오를 미국 S&P500 인버스 ETF(`SH`)로 헤지하게 됩니다.
  - 이로 인해 원/달러 환율 변동 위험과 한국-미국 시장 간 디커플링으로 인한 막대한 트래킹 에러 및 손실이 유발됩니다.

- **정량적/공학적 개선 방안**:
  - `portfolio_weights`에 포함된 종목들의 시장별 비중(KRX 총 가중치 vs US 총 가중치)을 집계합니다.
  - 한국 주식 비중에는 `114800`(KODEX 인버스2X)을, 미국 주식 비중에는 `SH`/`PSQ`를 각각 분할 매칭하여 멀티 헤지 주문을 생성하거나, 가중치 기준 지배적인 시장(Dominant Market)의 인버스를 채택하도록 수정합니다.

- **수정 대상 파일**:
  - `trading_system/src/execution/oms_engine.py:generate_order_plan` (Gate 8)

- **검증 방안**:
  - KOSPI 60%, NASDAQ 40% 혼합 포트폴리오를 Bear 레짐에서 주문 생성 시, 1위 종목 시장과 무관하게 한국 시장과 미국 시장 각각에 상응하는 인버스 헤지 주문이 독립적으로 생성되는지 검증.

---

### [HIGH-02] SlippageFeedbackEngine의 단일 체결 이상치에 의한 비용 승수(8.0x) 즉시 폭발 위험

- **현황 및 문제점**:
  - 파일 및 위치: `trading_system/src/execution/slippage_feedback.py:186-222`
  ```python
  arr = np.clip(np.array(valid_slippages, dtype=float), -500.0, 500.0)
  med = float(np.median(arr)) if len(arr) > 0 else self.default_slippage_bps
  ...
  # V7-22: Dynamic slippage scaling cap up to 8.0x for illiquid micro-cap protection
  max_scale_cap = 8.0
  scaling = float(np.clip(avg_slip / self.default_slippage_bps, 0.5, max_scale_cap)) if self.default_slippage_bps > 0 else 1.0
  ```
  - `trade_logs.db`에 단 1건의 체결 기록만 존재하더라도(`len(valid_slippages) == 1`), 해당 체결에서 50 bps의 슬리피지가 발생했을 경우:
    - 표본수가 5 미만이므로 MAD 필터링을 건너뛰고 `avg_slip = 50.0`이 됩니다.
    - `scaling = 50.0 / 5.0 = 10.0 -> clip(..., 0.5, 8.0) = 8.0`이 됩니다.
  - 단 1건의 일시적 체결 불량이나 이상치 로그만으로 전 시스템의 마찰비용 추정치가 **최대 상한인 8배로 즉시 폭증**합니다.
  - 이로 인해 앙상블 점수 감산 및 Gate 7.3(알파 허들 체크)에서 모든 전략 종목이 허들을 넘지 못해 신규 매수가 전면 중단되는 시스템 마비가 발생합니다.
  - 또한 수개월 전의 오래된 체결 로그를 시간 감쇠 없이 단순 평균하여 최신 시장 여건을 적절히 반영하지 못합니다.

- **정량적/공학적 개선 방안**:
  - 최소 신뢰 표본 수($N_{min} = 10$)를 도입하여 $N < 10$인 경우 기본 승수(1.0)를 유지하거나, 표본수에 따른 베이지안 수축 가중치를 적용합니다:
    $$\text{scaling}_{eff} = \frac{N}{N + 10} \cdot \text{scaling}_{sample} + \frac{10}{N + 10} \cdot 1.0$$
  - 최근 60개 체결로 롤링 윈도우를 제한하거나 지수 가중 이동평균(EMA)을 적용합니다.

- **수정 대상 파일**:
  - `trading_system/src/execution/slippage_feedback.py:calculate_realized_slippage`

- **검증 방안**:
  - 체결 로그가 1건(100 bps)만 존재하는 상태에서 `calculate_realized_slippage()` 호출 시, 승수가 8.0x로 튀지 않고 1.0~1.5x 수준으로 안정적으로 억제되는지 검증.

---

### [HIGH-03] PortfolioAllocator의 EVT-CVaR 폴백 최적화 시 VaR 수식 오적용

- **현황 및 문제점**:
  - 파일 및 위치: `trading_system/src/risk/portfolio_allocator.py:680-690` (`optimize_with_evt_cvar_constraint`)
  ```python
  z_alpha = -1.6448536269514722
  z_cf = (
      z_alpha
      + (z_alpha**2 - 1.0) * skew_c / 6.0
      + (z_alpha**3 - 3.0 * z_alpha) * kurt_c / 24.0
      - (2.0 * z_alpha**3 - 5.0 * z_alpha) * (skew_c**2) / 36.0
  )
  cvar_val = float(max(0.0, - (m_ret + z_cf * s_ret)))
  ```
  - SLSQP 1차 최적화 실패 시 코니시-피셔(Cornish-Fisher) 이차 계획법으로 폴백하면서, `cvar_val` 변수에 `-(m_ret + z_cf * s_ret)`를 대입하고 있습니다.
  - 이는 Cornish-Fisher **분위수(VaR)** 계산식이며, 분위수 너머 꼬리 손실의 기댓값인 **CVaR(Expected Shortfall)**가 아닙니다.
  - `estimate_evt_cvar` line 477-479에 구현된 `es_factor` 적분 항이 누락되어, 폴백 최적화기가 CVaR 한도가 아닌 VaR 한도로 제약하여 꼬리 위험을 과소평가하게 됩니다.

- **정량적/공학적 개선 방안**:
  - Cornish-Fisher의 Expected Shortfall 적분 보정 계수(`es_factor`)를 복원하여:
    $$\text{CVaR} = \mu + \sigma \cdot \frac{\phi(z_\alpha)}{1 - \alpha} \left( 1 + \frac{S}{6} z_\alpha^3 + \frac{K}{24} (z_\alpha^4 - 2z_\alpha^2 - 1) \right)$$
    수식을 적용하여 실제 CVaR 값을 제약조건 함수 `std_cvar_constraint`에 반환하도록 개선합니다.

- **수정 대상 파일**:
  - `trading_system/src/risk/portfolio_allocator.py`: `optimize_with_evt_cvar_constraint`

- **검증 방안**:
  - 동일한 왜도/첨도를 가진 비정규 분포에서 폴백 제약 함수의 `cvar_val`이 `var_val`보다 수학적으로 엄격하게 큼을 확인하는 단위 테스트.

---

### [HIGH-04] Gatheral 3/2-Power 시장충격 모델의 목적함수 패널티 미반영 및 사후 휴리스틱 왜곡

- **현황 및 문제점**:
  - 파일 및 위치: `trading_system/src/risk/unified_portfolio_allocator.py:259-277`
  ```python
  # 5. Non-Linear 3/2-Power Market Impact Adjustment (Gatheral & Almgren-Chriss)
  if advs is not None and len(advs) == n and total_capital > 0:
      ...
      impact_penalties = 1.0 * vols * (participation_ratios ** 1.5)

      # Dampen weight of illiquid assets where impact penalty exceeds alpha
      damp_factors = np.exp(-2.0 * np.minimum(impact_penalties, 20.0))
      w_damped = w_blended * damp_factors
      s_damp = np.sum(w_damped)
      if s_damp > 0:
          w_blended = w_damped / s_damp
  ```
  - AGENTS.md 및 모듈 독스트링에는 "Gatheral 3/2승 비선형 시장충격 패널티 목적함수"라고 명시되어 있으나, 실제 코드는 목적함수가 아닌 단순 사후 감쇠 휴리스틱(`w * exp(-2 * impact)`)입니다.
  - 감쇠 후 `w_blended = w_damped / s_damp`로 재정규화하기 때문에, 모든 자산이 유동성 제약에 직면할 경우 합계로 나누면서 감쇠 효과가 무효화됩니다.
  - 더욱이 직후 `apply_portfolio_constraints`가 실행되면서 상한선 초과분이 다른 종목으로 재분배되어 유동성 감쇠 효과가 무작위로 교란됩니다.

- **정량적/공학적 개선 방안**:
  - Almgren-Chriss / Gatheral 3/2승 시장충격 비용을 명시적 SLSQP 목적함수 $J(w) = w^\top \mu - \frac{\lambda}{2} w^\top \Sigma w - \sum_i \eta_i \sigma_i \left( \frac{|\Delta w_i| C}{ADV_i} \right)^{1.5}$로 최적화하거나,
  - 시장 참여율 상한을 하드 제약조건 $w_i \le w_{curr, i} + \frac{0.05 \cdot ADV_i}{C}$으로 바인딩하여 유동성 초과 주문을 물리적으로 차단합니다.

- **수정 대상 파일**:
  - `trading_system/src/risk/unified_portfolio_allocator.py`: `optimize_multi_model_blend`

- **검증 방안**:
  - 대형 자본금(1000억원) 테스트에서 일평균 거래대금(ADV)이 극히 작은 종목의 비중이 5% ADV 제약선 이하로 엄밀히 제한되는지 검증.

---

### [HIGH-05] 단위 테스트 `test_institutional_portfolio_construction.py` 내 잔존 실패(Assertion Error)

- **현황 및 문제점**:
  - 파일 및 위치: `tests/test_institutional_portfolio_construction.py:193`
  ```python
  # Lot sizes: KRX = 10, US = 1
  p_krx = res[res["symbol"] == "005930"].iloc[0]
  p_us = res[res["symbol"] == "AAPL"].iloc[0]
  assert p_krx["lot_size"] == 10  # <--- FAIL: assert 1 == 10
  assert p_krx["shares"] % 10 == 0
  assert p_us["lot_size"] == 1
  ```
  - KRX 종목 호가 단위가 1주 단위로 개편된 후 `unified_portfolio_allocator.py:501`은 `lot = 1 if is_krx else ...`로 정상 수정되었습니다.
  - 그러나 `tests/test_institutional_portfolio_construction.py`는 과거의 10주 호가 가정을 여전히 단언(assert)하고 있어, 현재 테스트 스위트 실행 시 즉각적인 테스트 실패(`assert 1 == 10`)가 발생합니다.

- **정량적/공학적 개선 방안**:
  - `tests/test_institutional_portfolio_construction.py` line 190-195를 최신 1주 호가 단위 규정에 맞게 `assert p_krx["lot_size"] == 1`로 수정합니다.

- **수정 대상 파일**:
  - `tests/test_institutional_portfolio_construction.py`

- **검증 방안**:
  - `pytest tests/test_institutional_portfolio_construction.py` 실행 시 8개 테스트 항목 100% 통과 확인.

---

## 3. Medium Priority Issues (중위험 개선 과제)

### [MEDIUM-01] VIX Term Structure (기간구조) 역전(Backwardation) 게이트 부재

- **현황 및 문제점**:
  - `AGENTS.md` 및 파이프라인 명세에는 "VIX 기간구조 완충 및 속도 게이트"가 명시되어 있으나, 실제 `risk_manager.py` 및 `run_pipeline.py`에는 VIX 기간구조(VIX vs VIX3M 스프레드, 또는 VIX9D vs VIX 역전 비율) 평가 로직이 구현되어 있지 않습니다.

- **정량적/공학적 개선 방안**:
  - 단기 공포(VIX)가 중기 변동성(VIX3M 또는 60일 이동평균)을 초과하는 백워데이션($\text{VIX} / \text{SMA}(\text{VIX}, 60) > 1.15$) 발생 시, 위기 점수를 가산하는 `_score_vix_term_structure()` 메서드를 `CrisisDetector`에 구현합니다.

- **수정 대상 파일**:
  - `trading_system/src/risk/risk_manager.py`: `CrisisDetector`

- **검증 방안**:
  - VIX가 22이지만 60일 평균 대비 20% 이상 백워데이션 역전 발생 시 조기 방어 모드가 작동하는지 검증.

---

### [MEDIUM-02] HERC 알고리즘 내 포트폴리오 상한선 하드코딩(0.20 / 0.35)

- **현황 및 문제점**:
  - 파일 및 위치: `trading_system/src/analysis/portfolio_optimizer.py:630-636` (`calculate_herc_weights`)
  ```python
  herc_w = cluster_weights / sum_w
  return apply_portfolio_constraints(
      herc_w,
      symbols=symbols,
      sectors=sectors,
      max_single_stock_weight=0.20,
      max_sector_weight=0.35
  )
  ```
  - 호출자(`UnifiedPortfolioAllocator`)가 설정한 `self.max_single_weight` 및 `self.max_sector_weight` 인자가 `calculate_herc_weights`로 전달되지 않고, 내부에서 0.20과 0.35로 고정 하드코딩되어 있습니다.

- **정량적/공학적 개선 방안**:
  - `calculate_herc_weights` 시그니처에 `max_single_stock_weight: float = 0.20, max_sector_weight: float = 0.35` 인자를 추가하여 호출자의 제약조건을 위임받도록 수정합니다.

- **수정 대상 파일**:
  - `trading_system/src/analysis/portfolio_optimizer.py`: `calculate_herc_weights`
  - `trading_system/src/risk/unified_portfolio_allocator.py`: line 221

- **검증 방안**:
  - `max_single_stock_weight=0.10` 지정 시 HERC 결과 가중치가 10% 이하로 엄격히 제한되는지 검증.

---

### [MEDIUM-03] Almgren-Chriss 트랜치 분할 시 잔여 수량 음수 클램핑 불일치

- **현황 및 문제점**:
  - 파일 및 위치: `trading_system/src/execution/oms_engine.py:1421-1425` (`GatheralMarketImpactKernel`)
  ```python
  alloc = np.round(norm_weights * total_quantity).astype(int)
  diff_total = total_quantity - int(np.sum(alloc))
  if diff_total != 0:
      alloc[0] += diff_total
  return [int(max(0, x)) for x in alloc]
  ```
  - `diff_total`이 음수이고 첫 트랜치 `alloc[0]`보다 절대값이 큰 경우, `alloc[0]`이 음수가 된 후 `max(0, x)`로 0 처리되면서 최종 트랜치 합계가 `total_quantity`와 불일치하게 됩니다.

- **정량적/공학적 개선 방안**:
  - `AlmgrenChrissScheduler`와 동일하게 역순 루프를 돌며 트랜치 잔여 수량을 안전하게 차감하도록 개선합니다.

- **수정 대상 파일**:
  - `trading_system/src/execution/oms_engine.py`: `GatheralMarketImpactKernel.compute_optimal_gatheral_slices`

- **검증 방안**:
  - 임의의 수량 및 분할수(예: quantity=1, n_slices=6)에서 모든 트랜치가 0 이상이며 합계가 정확히 `total_quantity`와 일치하는지 검증.

---

### [MEDIUM-04] 단위 테스트 스위트의 매크로/극단상황 사각지대(Blindspots)

- **현황 및 문제점**:
  - `test_black_litterman.py`: 2개 자산 토이 행렬만 테스트하며, 공분산 특이값(Singular/Rank-deficient), 음수 기대수익률, 대규모 유니버스 테스트가 누락됨.
  - `test_risk_manager.py`: `_vix_history`를 수동으로 6개 채워 넣는 방식으로만 테스트되어, 실전 파이프라인에서 발생하는 콜드 스타트 무상태 버그를 전혀 감지하지 못함.
  - 5개 시장(KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000) 통합 환율/통화 혼합 포트폴리오의 실전 엔드투엔드 리밸런싱 통합 테스트 부재.

- **정량적/공학적 개선 방안**:
  - `tests/test_track_c_institutional_stress.py`를 신설하여 통화 혼합 리밸런싱, 무상태 파이프라인 방어, 특이 공분산 BL, 소규모 유니버스 CVaR, VIX 갭 점프 시나리오를 전수 포괄하는 통합 테스트 스위트를 구축합니다.

- **수정 대상 파일**:
  - `tests/test_track_c_institutional_stress.py` 신설

- **검증 방안**:
  - 신설 스트레스 테스트 스위트 전수 실행 및 100% Pass 확인.

---

## 4. Track C Issue Matrix Summary

| ID | 중요도 | 영역 | 파일 및 위치 | 핵심 내용 |
|---|---|---|---|---|
| **CRITICAL-01** | 🔴 Critical | Portfolio Allocator | `src/risk/unified_portfolio_allocator.py:494` | US 종목 주식수 산출 시 환율 미적용으로 1,350배 과대 주문 발생 |
| **CRITICAL-02** | 🔴 Critical | Portfolio Optimizer | `src/analysis/portfolio_optimizer.py:202` | BL 20일 전망치(Q) vs 일별 공분산 단위 불일치로 효용함수 선형 붕괴 및 100배 단절 |
| **CRITICAL-03** | 🔴 Critical | Portfolio Allocator | `src/risk/unified_portfolio_allocator.py:136` | 소규모 유니버스($N \le 4$) CVaR 상한선 제약 불능으로 솔버 100% 실패 |
| **CRITICAL-04** | 🔴 Critical | Execution / Risk | `turnover_optimizer.py:75`, `portfolio_allocator.py:1297` | USD 계좌 금액 기준(KRW 50,000) 오적용에 의한 리밸런싱 영구 교착 |
| **CRITICAL-05** | 🔴 Critical | Macro Risk | `trading_system/run_pipeline.py:3698` | CrisisDetector 무상태 생성으로 VIX 속도/낙폭 속도/거시 Z-score 영구 0 결함 |
| **HIGH-01** | 🟠 High | Execution OMS | `src/execution/oms_engine.py:768` | Gate 8 합성 인버스 헤지 종목의 1위 종목 시장 종속 편향 |
| **HIGH-02** | 🟠 High | Execution OMS | `src/execution/slippage_feedback.py:186` | 슬리피지 피드백 1건 체결 이상치에 의한 비용 승수(8.0x) 폭발 |
| **HIGH-03** | 🟠 High | Risk Allocator | `src/risk/portfolio_allocator.py:680` | EVT-CVaR 폴백 최적화 시 VaR 수식 오적용으로 꼬리 위험 과소평가 |
| **HIGH-04** | 🟠 High | Portfolio Allocator | `src/risk/unified_portfolio_allocator.py:259` | Gatheral 3/2승 시장충격 목적함수 미반영 및 사후 휴리스틱 상쇄 |
| **HIGH-05** | 🟠 High | Test Suite | `tests/test_institutional_portfolio_construction.py:193` | KRX 호가 단위 1주 개편 후 테스트 단언 잔존 실패 (`assert 1 == 10`) |
| **MEDIUM-01** | 🟡 Medium | Macro Risk | `src/risk/risk_manager.py:CrisisDetector` | VIX Term Structure 기간구조 역전(Backwardation) 게이트 부재 |
| **MEDIUM-02** | 🟡 Medium | Portfolio Optimizer | `src/analysis/portfolio_optimizer.py:630` | HERC 알고리즘 내 포트폴리오 상한선 하드코딩(0.20 / 0.35) |
| **MEDIUM-03** | 🟡 Medium | Execution OMS | `src/execution/oms_engine.py:1424` | Almgren-Chriss 트랜치 분할 시 잔여 수량 음수 클램핑 누락 |
| **MEDIUM-04** | 🟡 Medium | Test Suite | `tests/` 전반 | 다중 통화 혼합 포트폴리오 및 무상태 파이프라인 통합 테스트 사각지대 |
