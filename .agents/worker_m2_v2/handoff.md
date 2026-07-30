# Handoff Report: Core Improvements & Code Architecture Proposals (Requirement R2)

**Agent**: Worker M2 v2 (Core Improvements & Code Architecture Specialist)  
**Working Directory**: `d:\Finance\code\stock\.agents\worker_m2_v2`  
**Target Output File**: `d:\Finance\code\stock\.agents\worker_m2_v2\handoff.md`  
**Status**: Completed  

---

## 1. Observation

A comprehensive forensic examination of the stock trading system codebase (`trading_system/src/core/`, `trading_system/src/ai/`, `trading_system/src/data_layer/`, `trading_system/src/persistence/`, `src/risk/`, `src/execution/`, and `trading_system/src/config.py`) revealed several critical quantitative vulnerabilities, data lookahead biases, scale disparities, thread-safety bottlenecks, and missing architectural integrations under Requirement R2.

### 1.1 Strategy & Quant Flaws
1. **Stat-Arb Cointegration (`trading_system/src/core/stat_arb.py`)**:
   - Lines 48–57: ADF $p$-value calculation uses a coarse step function:
     ```python
     if t_stat < -3.90: p_val = 0.01
     elif t_stat < -3.34: p_val = 0.03
     elif t_stat < -2.86: p_val = 0.05
     elif t_stat < -2.57: p_val = 0.09
     else: p_val = 0.50
     ```
     This step function produces non-continuous $p$-values, distorting true statistical significance.
   - Line 226–237: Benjamini-Hochberg False Discovery Rate (FDR) procedure pre-sorts `found_pairs` by `abs(z_score)` rather than ascending order of ADF $p$-values ($P_{(1)} \le P_{(2)} \le \dots \le P_{(m)}$). This violates standard BH FDR step-up ordering, leading to invalid false positive filtering.
2. **RIM Valuation (`trading_system/src/core/rim_valuation.py`)**:
   - Line 90: Returns `bps + pv_excess` over a finite horizon $N=8$ without incorporating explicit terminal equity valuation ($PV_{terminal} = \frac{BPS_N}{(1+r_e)^N}$).
   - Line 85: `retention = self.retention_ratio if net_income > 0 else 1.0`. When historical dividend payout ratios ($D / NI$) are calculated under negative net income ($NI < 0$), dividend payout ratio produces negative retention rates ($1 - D/NI$), improperly inflating or deflating future book value.
3. **LATR Factor (`trading_system/src/core/latr_factor.py`)**:
   - Line 53: `latr_score = ((1.0 - dd_pct) * 0.4) + (min(vol_surge, 3.0) * 0.4) - (abs(tail_risk) * 0.2)`. The 52-week drawdown penalty and 5% lower-quantile tail risk penalty were combined with positive offset constants rather than explicit inverted penalties ($-0.4 \times DD_{pct}$ and $-0.2 \times |TailRisk_{5\%}|$).
4. **CARD Factor (`trading_system/src/core/card_factor.py`)**:
   - Lines 44–50: Direct arithmetic comparison between 5-day stock return percentage (`stock_ret` e.g., $-5.0$) and unnormalized macro indicators (`usdkrw_chg` e.g., $+15.0$ KRW, `vix_val` e.g., $+2.5$ points): `macro_impact = (usdkrw_chg * 0.3) + (wti_chg * 0.3) + (vix_val * 0.4)`. Combining raw series of completely different units/scales creates severe scale distortion.
5. **Event-Driven Momentum (`trading_system/src/core/event_driven.py`)**:
   - Lines 98–101: `matched = (stock_code and stock_code == sym_clean) or (corp_code and (corp_code == sym_clean or corp_code.endswith(sym_clean) or corp_code == sym))`. OpenDART 8-digit `corp_code` (e.g., `00126380`) does not match 6-digit stock ticker `stock_code` (e.g., `005930`). Comparing `corp_code == sym_clean` causes lookup failures.
   - Line 142: `continuous_boost = np.clip(0.05 * (v_ratio - 1.0) + 0.10 * ret_5d, -0.2, 0.4)`. If volume surges ($v\_ratio = 5.0$) during a price crash ($ret_{5d} = -0.15$), the formula yields a positive boost ($+0.185$), rewarding panic selling crashes.
6. **Lead-Lag Matrix (`trading_system/src/ai/prediction_model.py`)**:
   - Lines 2460–2465: US ETF series (`XLK`, `XLF`, `XLV`, `XLE`) were shifted by $+1$ day, but US single stock leaders (e.g., AAPL, MSFT, NVDA) and market indices (`^GSPC`) when evaluated against KOSPI/KOSDAQ targets were not systematically aligned across timezone boundaries (+1 calendar day shift into KST space), creating a 15-hour lookahead / alignment mismatch.
7. **Strict Causal LSTM (`trading_system/src/ai/lstm_predictor.py`)**:
   - Lines 25, 44: `LSTMNetwork` accepts single-feature scalar returns (`input_size = 1`) without multi-feature technical/volume inputs and lacks rolling sequence z-score normalization computed strictly causally up to time $t$.
8. **VCP Rule & ML (`trading_system/src/ai/vcp_detector.py` & `vcp_ml_predictor.py`)**:
   - `vcp_detector.py` lines 116–119: Asymmetric window slices (5d, 10d, 20d, 25d) skew `max(range_pct)` comparisons across non-equal time horizons.
   - `vcp_ml_predictor.py` lines 369–375: Train/validation split uses a simple 80/20 date cutoff without purging overlapping lookback windows within 20 days of the split boundary, introducing target data leakage.
9. **Missing Strategy Restoration**:
   - `arm_factor`, `card_factor`, and `latr_factor` were missing from default strategy base weights, pipeline dataframe merges, and Coverage Analyzer column mappings (`col_map` in `coverage_analyzer.py`).

### 1.2 Microstructure & System Architecture Vulnerabilities
1. **Transaction Cost Modeling**: Existing pipeline lacked an order book market impact model combining bid-ask spread half-width, market impact coefficient, Securities Transaction Tax (STT), and fixed fees.
2. **SQLite WAL Concurrency**: High-concurrency multithreaded writes in `indicator_storage.py` and `database.py` occasionally hit `database is locked` errors due to missing execution locks and default low busy timeouts.
3. **Memory & Concurrency**: Large-scale feature extraction for 3,379 symbols under pure ThreadPoolExecutor causes memory bloat and GIL contention; downcasting monetary values to `float32` causes precision loss in trillion-KRW market caps.
4. **Advanced Core Architecture**: `RiskManager` crisis gating was not wired directly to dynamic strategy weights in `run_pipeline.py`; Portfolio Optimization lacked Risk Parity (ERC) and Ledoit-Wolf Covariance Shrinkage; OMS scheduler lacked trade log tracking error and slippage monitoring.

---

## 2. Logic Chain

1. **Quant & Strategy Reasoning**:
   - Cointegration residual stationary testing requires continuous $p$-values calculated via MacKinnon response surface regressions (`statsmodels.tsa.stattools.adfuller`) rather than step functions. Benjamini-Hochberg FDR requires sorting $p$-values ascending ($P_{(1)} \le P_{(2)} \le \dots \le P_{(m)}$) to evaluate $P_{(i)} \le \frac{i}{m} Q$, guaranteeing upper bound control on false discoveries.
   - Clean Surplus Accounting dictates $V_0 = BPS_0 + \sum_{t=1}^N \frac{RI_t}{(1+r_e)^t} + \frac{BPS_N}{(1+r_e)^N}$. Incorporating terminal book value discounted at rate $(1+r_e)^N$ grounds finite-horizon valuations. Clamping payout ratio when $NI < 0$ prevents negative retained earnings calculation artifacts.
   - Normalizing macro inputs ($Z_{macro} = w_1 Z_{USDKRW} + w_2 Z_{WTI} + w_3 Z_{VIX}$) and stock returns ($Z_{stock}$) via rolling 60-day Z-scores converts heterogeneous quantities into stationary, unitless random variables, ensuring mathematically valid divergence calculation.
   - OpenDART corporate codes are 8-digit unique IDs requiring a strict mapping dictionary (`corp_code_map`) to translate to 6-digit stock symbols (`stock_code`).
   - Aligning US market close (05:00 KST day $T+1$) with KOSPI opening (09:00 KST day $T+1$) requires shifting all US market date indices forward by $+1$ calendar day in KST space.

2. **Microstructure & Transaction Cost Reasoning**:
   - The Almgren-Chriss / Square-Root law states that market impact scales with relative order size to Average Daily Volume (ADV) raised to power $\alpha \approx 0.5$, scaled by daily volatility $\sigma_{daily}$.
   - Total transaction cost model:
     $$Cost_{total} = Fee_{flat} + STT_{sell\_only} + \frac{Spread}{2} + \gamma \cdot \left(\frac{OrderSize}{ADV}\right)^\alpha \cdot \sigma_{daily}$$

3. **System Architecture Reasoning**:
   - SQLite WAL mode allows concurrent readers and one writer. Wrapping DB connections with `busy_timeout=30000` (30 seconds), `synchronous=NORMAL`, and an explicit `threading.Lock()` mutex around write transactions guarantees thread safety.
   - ProcessPoolExecutor bypasses Python's GIL for CPU-intensive feature calculation. Retaining `float64` for high monetary values (market cap, daily turnover) prevents numeric overflow and rounding degradation.

4. **Advanced Core Architecture Reasoning**:
   - Dynamic 2D Market Crisis Gating evaluates macro crisis indicators (VIX, TNX, USDKRW, Yield Spread) to suppress high-risk directional factors during market panics.
   - Risk Parity allocation equalizes marginal risk contributions:
     $$\min_w \sum_{i,j=1}^N \left( w_i (\Sigma w)_i - w_j (\Sigma w)_j \right)^2 \quad \text{s.t. } \sum w_i = 1, w_i \ge 0$$
   - Ledoit-Wolf Shrinkage $\Sigma_{shrunk} = \delta F + (1-\delta) S$ stabilizes sample covariance matrix $S$ against identity/constant variance target $F$.

---

## 3. Caveats

1. **Data Scope**: Daily OHLCV price series are assumed. High-frequency tick data modeling is outside the daily pipeline scope.
2. **Tax & Fee Regulations**: Korean Securities Transaction Tax (STT) rate is modeled at 0.18% for sell orders on KOSPI/KOSDAQ.
3. **OpenDART Rate Limits**: OpenDART API calls must use local caching of `CORPCODE.xml` to stay within daily request quotas.
4. **Execution Simulation**: OMS execution assumes TWAP/VWAP execution slicing during market hours.

---

## 4. Conclusion & Technical Specifications

This section presents the detailed, actionable code improvement proposals and technical specifications addressing all diagnosed vulnerabilities in Requirement R2.

---

### Module 1: Strategy & Quant Fixes

#### 1.1 Stat-Arb Cointegration: OLS Log-Prices, MacKinnon $p$-Surface & FDR Sorting Fix
- **Target File**: `trading_system/src/core/stat_arb.py`
- **Specification**:
  1. **OLS on Log Prices**: Fit price series using natural log $\ln(P_t)$ to maintain scale invariance across arbitrary asset prices.
  2. **Continuous MacKinnon $p$-Value**: Replace step function `_estimate_adf_pvalue` with `statsmodels.tsa.stattools.adfuller` or continuous MacKinnon response surface regression formula:
     ```python
     from statsmodels.tsa.stattools import adfuller

     def _estimate_adf_pvalue_mackinnon(residuals: np.ndarray) -> Tuple[float, float]:
         if len(residuals) < 15:
             return 0.0, 1.0
         try:
             # autolags='AIC' for optimal lag selection
             res = adfuller(residuals, autolag='AIC', maxlag=int(12 * (len(residuals) / 100)**0.25))
             t_stat = float(res[0])
             p_val = float(res[1])
             return t_stat, p_val
         except Exception:
             return 0.0, 1.0
     ```
  3. **Correct BH-FDR Ordering**: Pre-sort pairs ascending by $p$-value before computing false discovery rate cutoff $k = \max \{ i : P_{(i)} \le \frac{i}{m} Q \}$:
     ```python
     def apply_bh_fdr_correction(found_pairs: List[Dict[str, Any]], max_qvalue: float = 0.10) -> List[Dict[str, Any]]:
         if not found_pairs:
             return []
         # 1. Sort strictly ascending by ADF p-value
         found_pairs.sort(key=lambda x: x['adf_pvalue'])
         m = len(found_pairs)
         pvals = [p['adf_pvalue'] for p in found_pairs]
         
         # 2. Compute BH critical threshold k
         max_k = 0
         for i, p in enumerate(pvals, start=1):
             threshold = (i / m) * max_qvalue
             if p <= threshold:
                 max_k = i

         if max_k > 0:
             passed = found_pairs[:max_k]
         else:
             passed = [found_pairs[0]] if found_pairs[0]['adf_pvalue'] <= max_qvalue else []
         
         # 3. Post-sort active candidates by absolute z-score magnitude for signal prioritization
         passed.sort(key=lambda x: abs(x['z_score']), reverse=True)
         return passed
     ```

#### 1.2 RIM Valuation: Terminal Value Formula & Negative Net Income Payout Guard
- **Target File**: `trading_system/src/core/rim_valuation.py`
- **Specification**:
  1. **Finite Horizon with Discounted Terminal Equity Value**:
     Clean Surplus Residual Income Formula:
     $$V_0 = BPS_0 + \sum_{t=1}^N \frac{BPS_{t-1} \cdot (ROE_t - r_e)}{(1+r_e)^t} + \frac{BPS_N}{(1+r_e)^N}$$
     ```python
     def calculate_intrinsic_value(self, bps: float, roe: float, required_return: Optional[float] = None, years: int = 8) -> float:
         r_e = required_return if (required_return is not None and required_return > 0) else self.default_required_return
         if np.isnan(bps) or bps <= 0:
             return np.nan
         if np.isnan(roe):
             roe = r_e

         pv_excess = 0.0
         current_bps = bps
         current_roe = roe

         for t in range(1, years + 1):
             net_income = current_bps * current_roe
             excess_income = current_bps * (current_roe - r_e)
             pv_excess += excess_income / ((1.0 + r_e) ** t)
             
             # Guard retention ratio under negative net income (losses)
             retention = self.retention_ratio if net_income > 0 else 1.0
             current_bps += net_income * retention
             current_roe = r_e + (current_roe - r_e) * (1.0 - self.decay_rate)

         # Add terminal discounted book value at year N
         pv_terminal_bps = current_bps / ((1.0 + r_e) ** years)
         
         # Full clean surplus intrinsic value
         v0 = bps + pv_excess + (pv_terminal_bps - bps / ((1.0 + r_e) ** years))
         return float(v0)
     ```

#### 1.3 LATR Factor: Drawdown & Tail Risk Inversion Formula
- **Target File**: `trading_system/src/core/latr_factor.py`
- **Specification**:
  - Invert drawdown penalty and tail risk penalty explicitly:
    $$LATR_{raw} = -0.4 \times DD_{pct} + 0.4 \times \min(VolSurge, 3.0) - 0.2 \times |TailRisk_{5\%}|$$
    ```python
    dd_pct = (high_52w - curr_price) / high_52w if high_52w > 0 else 0.0
    vol_surge = (vol_5d / (vol_20d + 1e-5))
    daily_rets = close.pct_change().tail(window).dropna()
    tail_risk_5pct = abs(float(np.percentile(daily_rets, 5))) if len(daily_rets) >= 20 else 0.03

    # Explicit inverted penalty scoring
    latr_raw = (-0.4 * dd_pct) + (0.4 * min(vol_surge, 3.0)) - (0.2 * tail_risk_5pct)
    ```

#### 1.4 CARD Factor: Rolling Z-Score Normalization
- **Target File**: `trading_system/src/core/card_factor.py`
- **Specification**:
  - Compute 60-day rolling Z-scores for stock 5-day return ($Z_{stock}$) and macro factor returns ($Z_{macro}$):
    ```python
    def _compute_rolling_zscore(series: pd.Series, window: int = 60) -> float:
        if len(series) < window:
            std = series.std()
            return (series.iloc[-1] - series.mean()) / (std if std > 1e-6 else 1.0)
        roll = series.tail(window)
        std = roll.std()
        return float((series.iloc[-1] - roll.mean()) / (std if std > 1e-6 else 1.0))

    # In compute_scores:
    z_usdkrw = _compute_rolling_zscore(indicator_df['usdkrw_change'])
    z_wti = _compute_rolling_zscore(indicator_df['wti_change'])
    z_vix = _compute_rolling_zscore(indicator_df['vix_change'])

    z_macro = (0.3 * z_usdkrw) + (0.3 * z_wti) + (0.4 * z_vix)
    stock_5d_rets = close.pct_change(5).dropna()
    z_stock = _compute_rolling_zscore(stock_5d_rets)

    divergence = z_stock - z_macro
    card_score = 1.0 / (1.0 + np.exp(divergence)) # Sigmoid mapping [0, 1]
    ```

#### 1.5 Event-Driven: Exact OpenDART Corp Code Mapping & Crash Volume Surge Penalty
- **Target File**: `trading_system/src/core/event_driven.py`
- **Specification**:
  1. **Exact OpenDART `corp_code` Mapping**:
     Use `dart_corp_mapper` dictionary (8-digit `corp_code` $\leftrightarrow$ 6-digit `stock_code`) for zero-mismatch disclosure lookups:
     ```python
     def match_symbol(corp_code: str, stock_code: str, corp_map: Dict[str, str]) -> Optional[str]:
         if stock_code and stock_code.strip():
             return stock_code.strip().zfill(6)
         if corp_code and corp_code.strip() in corp_map:
             return corp_map[corp_code.strip()].zfill(6)
         return None
     ```
  2. **Penalize Volume Surge on Price Crash**:
     When 5-day price return $ret_{5d} < 0$, volume surge indicates institutional dumping / panic selling:
     ```python
     ret_5d = float((c.iloc[-1] / c.iloc[-5]) - 1.0)
     v_ratio = (cur_vol / avg_vol) if avg_vol > 0 else 1.0
     
     if ret_5d >= 0:
         continuous_boost = 0.05 * (v_ratio - 1.0) + 0.10 * ret_5d
     else:
         # Negative return -> volume surge penalizes event score
         continuous_boost = -0.08 * (v_ratio - 1.0) + 0.10 * ret_5d

     continuous_boost = float(np.clip(continuous_boost, -0.35, 0.40))
     scores_map[sym] = float(np.clip(scores_map[sym] + continuous_boost, 0.0, 1.0))
     ```

#### 1.6 Lead-Lag: US Market Date Shift (+1 Calendar Day in KST Space)
- **Target File**: `trading_system/src/ai/prediction_model.py`
- **Specification**:
  - Shift all US leaders (US ETFs `XLK`, `XLF`, `XLV`, `XLE`, US benchmark `^GSPC`, and US stocks) by $+1$ calendar day when building correlation matrices against KST targets:
    ```python
    us_symbols = {sym for sym in ret_pivot.columns if not OnDevicePredictionModel.is_krx_symbol(sym)}
    for sym in us_symbols:
        ret_pivot[sym] = ret_pivot[sym].shift(1) # +1 day shift to KST calendar space
    ```

#### 1.7 Strict Causal LSTM: Multi-Feature Input with Rolling Causal Z-Score Normalization
- **Target File**: `trading_system/src/ai/lstm_predictor.py`
- **Specification**:
  - Accept multi-feature matrix inputs (`input_size = 5`: `['ret_1d', 'norm_volume', 'vol_20d', 'rsi_14', 'macd_hist_norm']`).
  - Apply strictly causal rolling sequence z-score normalization ($\mu_{1..t}$, $\sigma_{1..t}$) without future lookahead:
    ```python
    def causal_sequence_normalize(X_seq: np.ndarray) -> np.ndarray:
        # X_seq shape: (batch, seq_len, num_features)
        normalized = np.zeros_like(X_seq)
        for t in range(X_seq.shape[1]):
            cum_mean = np.mean(X_seq[:, :t+1, :], axis=1, keepdims=True)
            cum_std = np.std(X_seq[:, :t+1, :], axis=1, keepdims=True) + 1e-8
            normalized[:, t, :] = (X_seq[:, t, :] - cum_mean[:, 0, :]) / cum_std[:, 0, :]
        return normalized
    ```

#### 1.8 VCP Rule & ML: Symmetric Window Bounds & Purged Group Time-Series CV
- **Target Files**: `trading_system/src/ai/vcp_detector.py` and `vcp_ml_predictor.py`
- **Specification**:
  1. **Symmetric Window Bounds (`vcp_detector.py`)**:
     Use equal 10-day window slices ($W_1 = [-10:]$, $W_2 = [-20:-10]$, $W_3 = [-30:-20]$, $W_4 = [-40:-30]$) and enforce strict contraction hierarchy $R_1 < R_2 < R_3 < R_4$:
     ```python
     r1 = float(df['range_pct'].iloc[-10:].max())
     r2 = float(df['range_pct'].iloc[-20:-10].max())
     r3 = float(df['range_pct'].iloc[-30:-20].max())
     r4 = float(df['range_pct'].iloc[-40:-30].max())
     decreasing = (r1 <= r2 * contraction_ratio) and (r2 <= r3 * contraction_ratio) and (r3 <= r4 * contraction_ratio)
     ```
  2. **Purged Group Time-Series CV (`vcp_ml_predictor.py`)**:
     Purge 20-day horizon overlaps around train/validation cutoff:
     ```python
     max_horizon_days = 20
     purge_start = cutoff - pd.Timedelta(days=max_horizon_days)
     train_idx = m_df['date'] <= purge_start
     val_idx = m_df['date'] > cutoff
     ```

#### 1.9 Missing Strategy Restoration: Ensemble Base Weights & Coverage Mapping
- **Target Files**: `trading_system/src/ai/ensemble_scorer.py`, `trading_system/src/analysis/coverage_analyzer.py`, `trading_system/run_pipeline.py`
- **Specification**:
  1. Restore `arm_factor`, `card_factor`, and `latr_factor` in base ensemble weights (`DEFAULT_WEIGHTS` / `REGIME_WEIGHTS` in `ensemble_scorer.py`).
  2. Add `arm_factor` $\to$ `arm_score`, `card_factor` $\to$ `card_score`, `latr_factor` $\to$ `latr_score` in `col_map` of `StrategyCoverageAnalyzer` (`coverage_analyzer.py`).
  3. Include strategy outputs in pipeline dataframe merges in `run_pipeline.py`.

---

### Module 2: Microstructure & Transaction Cost Modeling

#### 2.1 Almgren-Chriss Order Book Market Impact & STT Cost Model
- **Target Files**: `trading_system/src/config.py`, `trading_system/src/ai/ensemble_scorer.py`
- **Specification**:
  - Implement full cost deduction formula in `EnsembleScoringEngine`:
    $$Cost_{total} = Fee_{flat} + STT_{sell\_only} + \frac{Spread}{2} + \gamma \cdot \left(\frac{OrderSize}{ADV}\right)^\alpha \cdot \sigma_{daily}$$
    ```python
    def compute_transaction_cost(
        market: str,
        price: float,
        daily_volume_krw: float,
        daily_volatility: float,
        config: TradingConfig
    ) -> float:
        # 1. Flat Fee & Securities Transaction Tax (STT)
        fee_flat = 0.00015  # 1.5 bps broker commission
        stt_sell = 0.0018 if market in ['KOSPI', 'KOSDAQ'] else (0.0010 if market == 'KONEX' else 0.0)

        # 2. Half Bid-Ask Spread
        base_spread = {
            'KOSPI': config.base_spread_kospi,
            'KOSDAQ': config.base_spread_kosdaq,
            'KONEX': config.base_spread_konex,
            'SP500': config.base_spread_sp500
        }.get(market, 0.0010)
        half_spread = base_spread / 2.0

        # 3. Almgren-Chriss Square-Root Market Impact
        order_size = config.order_size_krw if market != 'SP500' else config.order_size_sp500
        gamma = config.market_impact_coeff_krx if market != 'SP500' else config.market_impact_coeff_sp500
        alpha = 0.5  # Square-root law exponent
        
        adv = max(daily_volume_krw, 1e5)
        participation_ratio = np.clip(order_size / adv, 1e-6, 1.0)
        market_impact = gamma * (participation_ratio ** alpha) * daily_volatility

        total_cost = fee_flat + stt_sell + half_spread + market_impact
        return float(total_cost)
    ```

#### 2.2 Liquidity & Minimum Volume Screening Engine
- **Target File**: `trading_system/run_pipeline.py`
- **Specification**:
  - Filter out stocks with 20-day Average Daily Volume (ADV) below threshold (`min_daily_volume_krx = 5,000,000,000` KRW, `min_daily_volume_sp500 = 1,000,000` shares) or price $< 1,000$ KRW ($1.00 USD) prior to prediction.

---

### Module 3: System Architecture & Concurrency

#### 3.1 SQLite WAL Connection Manager Pool & Thread Safety
- **Target File**: `trading_system/src/data_layer/indicator_storage.py`
- **Specification**:
  - Configure thread-safe connection context manager with `busy_timeout=30000` (30 sec timeout) and `synchronous=NORMAL`:
    ```python
    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA cache_size=-50000") # 50MB cache
        try:
            yield conn
        finally:
            conn.close()
    ```

#### 3.2 Thread-Safe `StockPriceDB` Mutex Locking
- **Target File**: `trading_system/src/persistence/database.py`
- **Specification**:
  - Add `self._write_lock = threading.Lock()` around all write queries and thread-local connection instantiation in `StockPriceDB`.

#### 3.3 Memory & Concurrency Optimization
- **Target File**: `trading_system/run_pipeline.py`
- **Specification**:
  - Use `ProcessPoolExecutor` for CPU-heavy feature extraction across 3,379 symbols.
  - Call explicit `gc.collect()` and clear temporary DataFrames after training rounds.
  - Preserve `float64` for high monetary values (`market_cap`, `volume_krw`, `shares_outstanding`), downcasting only normalized non-monetary features (`rsi`, `macd`, `zscore`) to `float32`.

---

### Module 4: Advanced Core Architecture

#### 4.1 Enhanced Risk Management: Pipeline `RiskManager` Integration & 2D Market Crisis Gating
- **Target File**: `trading_system/src/risk/risk_manager.py` & `run_pipeline.py`
- **Specification**:
  - Connect `RiskManager.detect_crisis_regime()` directly into `run_pipeline.py`.
  - When Macro Crisis Level is elevated (VIX $> 30$, USDKRW $> 1400$, Yield Inversion), activate 2D Market Crisis Gating to scale down equity leverage and suppress high-beta strategies.

#### 4.2 Portfolio Optimization: Risk Parity Allocation & Ledoit-Wolf Covariance Shrinkage
- **Target File**: `src/risk/portfolio_optimizer.py`
- **Specification**:
  1. **Ledoit-Wolf Covariance Shrinkage**:
     $$\Sigma_{shrunk} = \delta F + (1-\delta) S$$
     where target $F$ is scaled identity matrix $F = \frac{\text{Tr}(S)}{N} I$.
  2. **Equal Risk Contribution (ERC) Risk Parity Optimizer**:
     Solve for portfolio weights $w$ minimizing risk variance:
     $$\min_w \sum_{i,j=1}^N \left( w_i (\Sigma w)_i - w_j (\Sigma w)_j \right)^2 \quad \text{s.t. } \sum w_i = 1, w_i \ge 0$$

#### 4.3 OMS Execution Scheduler: Sliced Orders, `trade_logs.db`, Tracking Error & Slippage Monitoring
- **Target File**: `src/execution/oms_engine.py`
- **Specification**:
  - Slice large target portfolio orders into TWAP sub-orders.
  - Log execution records to `trade_logs.db`.
  - Monitor real-time tracking error and slippage in basis points:
    $$Slippage_{bps} = \frac{P_{executed} - P_{target}}{P_{target}} \times 10,000$$

---

## 5. Verification Method

To verify all specifications, run the comprehensive project test suite using the project Python environment:

```bash
# 1. Run unit and integration tests across all modules
.venv/bin/pytest tests/ -v

# 2. Run specific strategy test cases
.venv/bin/pytest tests/test_new_5_strategies.py -v
.venv/bin/pytest tests/test_lead_lag_index.py -v
.venv/bin/pytest tests/test_order_book_market_impact.py -v
.venv/bin/pytest tests/test_database.py -v
.venv/bin/pytest tests/phase3/test_allocation.py -v

# 3. Run full pipeline verification script
.venv/bin/python trading_system/run_pipeline.py --skip-training
```

### Invalidation Conditions
- Any occurrence of `database is locked` during concurrent execution.
- Any strategy returning non-normalized scores outside $[0.0, 1.0]$ or NaN values.
- Non-zero data missingness in Coverage Analyzer report for valid symbols.
- Negative net intrinsic values in RIM Valuation engine.

---
*Report completed by Worker M2 v2.*
