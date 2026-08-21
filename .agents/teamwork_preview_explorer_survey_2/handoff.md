# Handoff Report: Domain 3 Part A - 31 Strategy Engines & Data Layer (V5-13 ~ V5-23)

## 1. Observation

A forensic, multi-disciplinary code audit of Domain 3 Part A (covering Tasks V5-13 through V5-23) in the trading system repository (trading_system/src/core/... and trading_system/src/persistence/...) was conducted against the baseline requirements and the authoritative specification in system_improvement_report_v5.md.

Below are the verbatim findings, exact file paths, line numbers, and observed code defects across the 11 audited tasks:

---

### Task V5-13: trading_system/src/core/card_factor.py:130-133
- Component: Strategy #16 CARDFactorEngine
- Observed Code:
`python
stock_ret = float((c_last - c_prev) / c_prev * 100)
if np.isnan(stock_ret) or np.isinf(stock_ret):
    res_rows.append({'symbol': sym, 'card_score': 0.5})
    continue
`
- Direct Observation: res_rows is neither passed as an argument nor initialized inside compute_scores() (which uses scores = {}). Whenever stock_ret evaluates to NaN or Inf (e.g. constant price, zero historical base price, or illiquid series), line 131 executes res_rows.append(...), immediately triggering NameError: name res_rows is not defined. This raises an exception that falls into the outer except Exception as e: block at line 167.

---

### Task V5-14: trading_system/src/core/gamma_squeeze.py:55-60
- Component: Strategy #28 OptionsGammaSqueezeEngine
- Observed Code:
`python
def compute_scores(
    self,
    prices_dict: Dict[str, pd.DataFrame],
    fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
    indicators_df: Optional[pd.DataFrame] = None,
    **kwargs: Any,
) -> pd.DataFrame:
    symbols = list(prices_dict.keys()) if prices_dict else []
    return self.compute_gamma_squeeze_scores(symbols=symbols, prices_dict=prices_dict, **kwargs)

def calculate_scores(self, symbols: List[str], prices_dict: Optional[Dict[str, pd.DataFrame]] = None, **kwargs: Any) -> pd.DataFrame:
    return self.compute_gamma_squeeze_scores(symbols=symbols, prices_dict=prices_dict, **kwargs)

def compute_gamma_squeeze_scores(
    self,
    symbols: List[str],
    prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
    options_chain_dict: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
`
- Direct Observation: Both compute_scores() and calculate_scores() forward **kwargs to compute_gamma_squeeze_scores(). However, compute_gamma_squeeze_scores() does not accept **kwargs or standard keyword arguments (indicators_df, fundamentals_dict, features_df). When invoked with standard pipeline kwargs, Python raises TypeError: compute_gamma_squeeze_scores() got an unexpected keyword argument.

---

### Task V5-15: trading_system/src/core/hft_engine.py:181-194
- Component: Strategy #23 MicrostructureImbalanceEngine
- Observed Code:
`python
df_prices = kwargs.get(\x22df_prices\x22, prices_dict)
universe = kwargs.get(\x22universe\x22, kwargs.get(\x22universe_df\x22, None))
if universe is None or (isinstance(universe, pd.DataFrame) and universe.empty):
    if isinstance(fundamentals_dict, pd.DataFrame) and not fundamentals_dict.empty:
        universe = fundamentals_dict
    elif isinstance(prices_dict, pd.DataFrame) and not prices_dict.empty:
        universe = prices_dict
    else:
        universe = pd.DataFrame()

results = []
if universe.empty:
    return pd.DataFrame(columns=[\x22symbol\x22, \x22name\x22, \x22market\x22, \x22microstructure_score\x22])
`
- Direct Observation: In standard strategy execution engine.compute_scores(prices_dict) where prices_dict is Dict[str, pd.DataFrame] and universe is omitted, universe is initialized as an empty 0-row DataFrame. Line 192 immediately exits and returns an empty DataFrame pd.DataFrame(columns=[\x22symbol\x22, \x22name\x22, \x22market\x22, \x22microstructure_score\x22]), returning 0 rows despite a populated prices_dict.

---

### Task V5-16: trading_system/src/core/short_interest_squeeze.py:114-126
- Component: Strategy #25 ShortInterestSqueezeEngine
- Observed Code:
`python
# Explicit Data Path:
raw_squeeze = float(short_ratio) * float(dtc) * (1.0 + max(0.0, float(ret_5d) * 3.0)) * ignite_mult * borrow_fee_drag
results[sym_str] = raw_squeeze

# Fallback Proxy Path (missing short data):
proxy_score = float(vol_surge * np.clip(1.0 + ret_5d * 3.0 + ret_20d * 1.5, 0.2, 4.0))
results[sym_str] = proxy_score

# Normalization:
ranks = df_out.loc[valid_mask, \x27raw_score\x27].rank(pct=True, ascending=True).clip(0.02, 0.98)
`
- Direct Observation: raw_squeeze evaluates to [0.05, 0.40] for typical short ratios (e.g. 0.05 to 0.15) and DTC (e.g. 2.0 to 4.0). In contrast, proxy_score ranges from 1.0 to 4.0+. In a mixed universe where some tickers have explicit short interest data and others fallback, computing .rank(pct=True) on raw_score ranks all fallback stocks at the top percentiles above authentic high short interest equities, inverting cross-sectional rankings.

---

### Task V5-17: trading_system/src/core/cross_border_lead_lag.py:59-93
- Component: Strategy #3 CrossBorderLeadLagEngine
- Observed Code:
`python
if not us_returns:
    avg_us_tech_ret = 0.0  # Neutral default (no phantom momentum)
else:
    avg_us_tech_ret = float(np.mean(list(us_returns.values())))
...
leader_rets = [us_returns.get(leader_sym, avg_us_tech_ret) for leader_sym in leaders]
mean_leader_ret = float(np.mean(leader_rets))

# Lag divergence: US leader rose but KR stock hasn\x27t caught up yet -> Buying Opportunity
lag_divergence = mean_leader_ret - (kr_5d_ret * 0.2)
score = 1.0 / (1.0 + np.exp(-lag_divergence * 15.0))
scores[sym] = float(np.clip(score, 0.0, 1.0))
`
- Direct Observation: In split-runner execution (e.g., KOSPI/KOSDAQ split market runs), prices_dict contains only Korean equities. us_returns is empty, setting mean_leader_ret = 0.0. The lag divergence evaluates to -0.20 * kr_ret_5d. Consequently, Korean stocks with strong upward momentum (e.g. +10% 5-day gain) receive a penalized score of 0.425 < 0.50, inverting momentum into a contrarian penalty.

---

### Task V5-18: trading_system/src/core/order_flow.py:103-108
- Component: Strategy #13 OrderFlowEngine
- Observed Code:
`python
obv_slice = (np.sign(ret.tail(20)) * vol_sub.tail(20)).cumsum()
obv_trend = float((obv_slice.iloc[-1] - obv_slice.iloc[-10]) / (abs(obv_slice.iloc[-10]) + 1e-6)) if len(obv_slice) >= 10 else 0.0
`
- Direct Observation: obv_slice is computed as .cumsum() on a 20-bar window. At bar index -10, cumulative volume can cross zero or be small (e.g. 0 to 10 shares). Dividing an absolute 10-day volume shift (e.g. 5,000,000 shares) by approx 10^-6 produces an obv_trend of +/- 5,000,000.0, saturating np.clip(0.5 + obv_trend * 0.1, 0.0, 1.0) to 1.0 or 0.0 regardless of actual underlying flow.

---

### Task V5-19: trading_system/src/core/rim_valuation.py:317-328
- Component: Strategy #9 RIMValuationEngine
- Observed Code:
`python
# Transform Discount Ratio to Percentile Score [0.0, 1.0] per Market with boundary clipping
df[\x27rim_score\x27] = df.groupby(\x27market\x27)[\x27discount_ratio\x27].rank(pct=True, ascending=True).clip(0.02, 0.98).fillna(0.5)
...
invalid_mask = df[\x27rim_filter_reason\x27].isin([\x27LOW_EARNINGS_QUALITY\x27, \x27PREFERRED_SHARE\x27, \x27OPERATING_LOSS\x27])
...
if invalid_mask.any():
    df.loc[invalid_mask, [\x27rim_score\x27, \x27discount_ratio\x27, \x27intrinsic_value\x27]] = np.nan
`
- Direct Observation: Percentile ranking df.groupby(\x27market\x27)[\x27discount_ratio\x27].rank(...) is performed at line 317 BEFORE invalid_mask zeroes out distressed/disqualified companies at line 328. Distressed stocks with negative equity, operating loss, or low quality participate in the ranking calculation, skewing and polluting the cross-sectional percentile scores of valid, solvent companies.

---

### Task V5-20: trading_system/src/core/event_driven.py:150-160, 245-255
- Component: Strategy #10 EventDrivenEngine
- Observed Code:
`python
stock_code = str(item.get(\x27stock_code\x27, \x27\x27)).strip().zfill(6) if item.get(\x27stock_code\x27) else \x27\x27
corp_code = str(item.get(\x27corp_code\x27, \x27\x27)).strip()
...
matched = (stock_code and stock_code == sym_clean) or (corp_code and (corp_code == sym_clean or corp_code == sym))
`
- Direct Observation: In OpenDART filings, corp_code is an internal 8-digit identifier (e.g. \x2700126380\x27), while KRX stock tickers sym are 6-digit exchange codes (\x27005930\x27). If stock_code is omitted in the disclosure payload, direct string comparison corp_code == sym_clean never matches, resulting in true regulatory disclosure catalysts being dropped to default neutral (0.50).

---

### Task V5-21: trading_system/src/core/multi_factor_neutralizer.py:273-286
- Component: Strategy #21 MultiFactorNeutralizerEngine
- Observed Code:
`python
if N_m >= 6:
    try:
        Q_m, _ = np.linalg.qr(X_m, mode=\x22reduced\x22)
        proj_coef = np.dot(Q_m.T, y_m)
        y_pred = np.dot(Q_m, proj_coef)
        residual = y_m - y_pred
    except Exception as e:
        logger.warning(f\x22QR decomposition failed for market {mkt}: {e}\x22)
        residual = y_m - np.mean(y_m)
else:
    residual = y_m - np.mean(y_m)
`
- Direct Observation: For cross-sectional subsets with N_m < 6 (such as isolated market partitions, custom pools, or small sectors) or when QR decomposition encounters numerical ill-conditioning, the code bypasses factor neutralization completely and sets residual = y_m - np.mean(y_m). This leaves 100% of raw factor exposures un-neutralized, violating the style neutrality SLA (|rho| < 0.15).

---

### Task V5-22: trading_system/src/persistence/database.py:437-459
- Component: Data Ingestion & Persistence DataValidator / StockPriceDB
- Observed Code:
`python
split_candidates = (close.pct_change() < -0.25) & (~transient_spikes)
if split_candidates.any():
    split_dates = split_candidates[split_candidates].index
    for date in split_dates:
        ...
        if prev_close > 0:
            ratio = curr_close / prev_close
            logger.warning(f\x22Detected stock split around {date} with ratio {ratio:.4f}. Adjusting historical data.\x22)
            for col in [\x27Open\x27, \x27High\x27, \x27Low\x27, \x27Close\x27]:
                if col in df_clean.columns:
                    df_clean.iloc[:idx, df_clean.columns.get_loc(col)] *= ratio
            if \x27Volume\x27 in df_clean.columns:
                df_clean.iloc[:idx, df_clean.columns.get_loc(\x27Volume\x27)] /= ratio
`
- Direct Observation: Any single-day price decline > 25% that does not immediately bounce back is flagged as a stock split. During broad market crashes, severe overnight gap-downs, or corporate crises, ratio = curr_close / prev_close (e.g. 0.50 for a 50% drop) permanently rewrites SQLite historical price records, cutting historical prices in half and multiplying historical volume, permanently corrupting time-series features and historical prices.

---

### Task V5-23: trading_system/src/core/short_term_reversal.py:71-79
- Component: Strategy #14 ShortTermReversalEngine
- Observed Code:
`python
df_sorted = df.sort_index(ascending=True) if hasattr(df.index, \x27is_monotonic_increasing\x27) and not df.index.is_monotonic_increasing else df
close = df_sorted[\x27Close\x27]
if isinstance(close, pd.DataFrame):
    close = close.iloc[:, 0]
close = close.dropna()
if len(close) >= 20:
    valid_cols[sym] = close
`
- Direct Observation: Line 72 hardcodes uppercase \x27Close\x27. If input price DataFrames use lowercase column names (\x27close\x27), df_sorted[\x27Close\x27] raises KeyError: \x27Close\x27. The exception is caught by the inner except Exception: block, silently omitting valid symbols. If all tickers have lowercase column names, valid_cols is empty and the engine returns a 0-row DataFrame.

---

## 2. Logic Chain

The step-by-step reasoning tracing observations to required architectural and algorithmic fixes:

`
[Observation V5-13: card_factor.py:131]
  -> scores is dict, res_rows is undefined
  -> NaN/Inf stock_ret triggers NameError
  -> Fix: replace res_rows.append with scores[sym] = 0.5

[Observation V5-14: gamma_squeeze.py:55-60]
  -> callers forward **kwargs (fundamentals_dict, indicators_df)
  -> compute_gamma_squeeze_scores lacks **kwargs parameter
  -> Fix: add **kwargs: Any to signature and safely extract options_chain_dict

[Observation V5-15: hft_engine.py:181-194]
  -> standard compute_scores(prices_dict) lacks explicit universe df
  -> universe initialized as empty DataFrame, triggering early 0-row return
  -> Fix: synthesize universe DataFrame from prices_dict.keys() when universe is None/empty

[Observation V5-16: short_interest_squeeze.py:114-126]
  -> explicit formula evaluates to [0.05, 0.40], proxy formula evaluates to [1.0, 4.0+]
  -> rank(pct=True) ranks all fallback tickers above authentic short squeeze targets
  -> Fix: rescale proxy score equation to [0.0, 0.50] dynamic range matching explicit path

[Observation V5-17: cross_border_lead_lag.py:59-93]
  -> split-runner lacks US tech leaders, setting us_returns = {}
  -> lag_divergence = 0.0 - 0.20 * kr_5d_ret penalizes winning Korean stocks (momentum inverted)
  -> Fix: if not us_returns, query db_storage or assign neutral score (0.50) without penalty

[Observation V5-18: order_flow.py:103-108]
  -> 10-day OBV delta divided by |OBV_{t-10}| which can be near zero
  -> division-by-zero blows up obv_trend to millions and saturates score
  -> Fix: normalize OBV delta by 10-day sum of traded volume: max(vol_10d_sum, 1.0)

[Observation V5-19: rim_valuation.py:317-328]
  -> discount_ratio ranked across universe before invalid_mask is applied
  -> distressed companies (operating loss, negative equity) pollute rank percentiles
  -> Fix: invalidate discount_ratio and intrinsic_value for invalid_mask before .rank(pct=True)

[Observation V5-20: event_driven.py:150-160, 245-255]
  -> OpenDART corp_code is 8 digits, KRX ticker is 6 digits; direct equality fails
  -> filings without stock_code fail to match target symbols
  -> Fix: use stock_code when present, or map corp_code via DARTCorpMapper / corp_code cache

[Observation V5-21: multi_factor_neutralizer.py:273-286]
  -> N_m < 6 or singular QR skips neutralization and uses raw y_m - mean(y_m)
  -> style neutrality SLA (|rho| < 0.15) violated for small market segments
  -> Fix: use Ridge regression for ill-conditioned QR, and SVD pseudoinverse pinv(X_m) for N_m < 6

[Observation V5-22: database.py:437-459]
  -> any price drop > 25% permanently modifies historical price/volume as a stock split
  -> severe market crashes and gap-downs permanently corrupt SQLite price history
  -> Fix: require volume surge confirmation (vol_ratio >= 1.5) and validate split ratio bounds

[Observation V5-23: short_term_reversal.py:71-79]
  -> hardcoded df[\x27Close\x27] fails on lowercase df[\x27close\x27] with KeyError
  -> valid symbols silently dropped from scoring
  -> Fix: case-insensitive column resolution checking \x27Close\x27 and \x27close\x27
`

---

## 3. Caveats

1. Test Suite Isolation: Tests must be written and verified in isolated test modules without modifying active production pipelines during investigation.
2. Data Model Compatibility: DARTCorpMapper requires an existing cache file or mock fallback when network/API keys are absent in offline test environments.
3. Database Migration Safety: The DataValidator stock split guard operates on in-memory and ingestion pipelines; existing clean database rows are uncorrupted when volume guards are enforced.
4. Scope Demarcation: This report focuses exclusively on Domain 3 Part A (Tasks V5-13 through V5-23). Domain 1 (AI/ML), Domain 2 (Portfolio/Risk), Domain 3 Part B (V5-26 to V5-31), Domain 4 (OMS), and Domain 5 (CI/CD) are surveyed by peer explorers.

---

## 4. Conclusion & Concrete Implementation Specifications

The 11 tasks in Domain 3 Part A are fully surveyed, analyzed, and mapped to concrete source code modifications and test specifications:

### Detailed Summary Table for Tasks V5-13 ~ V5-23:

| # | Task ID | Target File & Line | Severity | Issue Summary | Root Cause | Exact Remedy |
|---|---|---|---|---|---|---|
| 1 | V5-13 | src/core/card_factor.py:131 | CRITICAL | res_rows.append NameError | res_rows is undefined in compute_scores() | Replace res_rows.append(...) with scores[sym] = 0.5 |
| 2 | V5-14 | src/core/gamma_squeeze.py:55-60 | CRITICAL | Missing **kwargs in method | compute_gamma_squeeze_scores lacks **kwargs in signature | Add **kwargs: Any to signature and extract options_chain_dict=kwargs.get(\x27options_chain_dict\x27) |
| 3 | V5-15 | src/core/hft_engine.py:181-194 | CRITICAL | Empty DataFrame on standard call | universe initialized as empty DataFrame when omitted | Synthesize universe DataFrame from prices_dict.keys() |
| 4 | V5-16 | src/core/short_interest_squeeze.py:114-126 | CRITICAL | 10x-20x scale divergence | Fallback proxy scale (1.0 - 4.0) dominates explicit scale (0.05 - 0.40) | Rescale fallback proxy formula to match [0.0, 0.50] range |
| 5 | V5-17 | src/core/cross_border_lead_lag.py:59-93 | HIGH | Lead-Lag alpha inverted in split run | Empty us_returns turns equation into contrarian penalty against KR momentum | If not us_returns, query db_storage or assign neutral score 0.50 |
| 6 | V5-18 | src/core/order_flow.py:103-108 | HIGH | OBV trend slope division by ~0 | Dividing OBV delta by near-zero unanchored cumulative volume | Normalize OBV delta by 10-day sum of traded volume: max(vol_10d_sum, 1.0) |
| 7 | V5-19 | src/core/rim_valuation.py:317-328 | HIGH | Distressed stocks pollute rankings | discount_ratio ranked before invalidation mask is applied | Invalidate discount_ratio / intrinsic_value before .rank(pct=True) |
| 8 | V5-20 | src/core/event_driven.py:150-160, 245-255 | HIGH | 8-digit corp_code vs 6-digit ticker | Direct equality check corp_code == sym never matches | Match stock_code.zfill(6) or resolve corp_code via DARTCorpMapper |
| 9 | V5-21 | src/core/multi_factor_neutralizer.py:273-286 | HIGH | Factor neutralization skipped for N < 6 | Ill-conditioned / small N_m falls back to un-neutralized y - mean(y) | Apply Ridge regression fallback and SVD pseudoinverse np.linalg.pinv(X_m) |
| 10 | V5-22 | src/persistence/database.py:437-459 | HIGH | Market crashes misclassified as splits | Any drop > 25% triggers price halving without volume confirmation | Require volume surge confirmation (vol_ratio >= 1.5) and validate split bounds |
| 11 | V5-23 | src/core/short_term_reversal.py:71-79 | MEDIUM | KeyError: \x27Close\x27 on lowercase column | df_sorted[\x27Close\x27] hardcoded uppercase | Resolve column case-insensitively (\x27Close\x27 or \x27close\x27) |

---

## 5. Verification Method

To independently verify the defects and validate the proposed remedies:

### Verification Test Commands
`ash
# 1. Run all core strategy and data layer unit tests
.venv/Scripts/python.exe -m pytest tests/test_strategy_31_universe.py tests/test_new_strategies.py tests/test_strategy_edge_cases.py tests/test_factor_neutralized_sla.py tests/test_data_validator.py -v

# 2. Run full regression test suite
.venv/Scripts/python.exe -m pytest tests/ -q
`

### Proposed Targeted Unit Test Suite (tests/test_v5_domain3_part_a_survey.py)
A dedicated verification test suite validating all 11 fixes:
1. test_v5_13_card_factor_nan_stock_ret_fallback(): Feeds degenerate price series to CARDFactorEngine, asserting neutral 0.50 score without NameError.
2. test_v5_14_gamma_squeeze_arbitrary_kwargs(): Calls compute_gamma_squeeze_scores and compute_scores with arbitrary **kwargs (indicators_df, features_df), asserting successful completion.
3. test_v5_15_microstructure_default_call_non_empty(): Calls MicrostructureImbalanceEngine.compute_scores(prices_dict) directly without universe, asserting non-empty DataFrame output matching universe keys.
4. test_v5_16_short_squeeze_scale_alignment(): Verifies that authentic high short interest stocks rank higher than proxy fallback stocks with moderate volume.
5. test_v5_17_cross_border_lead_lag_split_runner_neutrality(): Asserts that Korean stocks with positive momentum receive neutral 0.50 (not < 0.50) when US leader prices are absent.
6. test_v5_18_order_flow_obv_zero_crossing_stability(): Asserts obv_trend stays bounded in [-1.0, 1.0] when 10-day cumulative volume crosses zero.
7. test_v5_19_rim_distressed_companies_do_not_distort_ranks(): Verifies that injecting distressed loss-making stocks does not shift the percentile ranks of solvent companies.
8. test_v5_20_event_driven_dart_stock_and_corp_code_matching(): Validates matching when disclosures contain 6-digit stock_code or 8-digit corp_code.
9. test_v5_21_factor_neutralizer_small_universe_ridge_svd(): Tests factor neutralization on small cross-sections (N=4, 5), asserting significant factor exposure reduction.
10. test_v5_22_stock_split_market_crash_rejection(): Passes a -40% single-day crash without volume surge, asserting prices are NOT adjusted; passes genuine split with 4x volume surge, asserting split adjustment IS performed.
11. test_v5_23_short_term_reversal_lowercase_columns(): Passes DataFrames with lowercase \x27close\x27, asserting reversal scores are calculated successfully.
