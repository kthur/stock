# Financial Engineering & Quantitative Risk Audit Analysis Report

**Milestone 1 — Task 2**: Audit HRP portfolio allocation, covariance shrinkage, liquidity constraints, position sizing limits, microstructure transaction costs, and RiskManager & CrisisGating.

---

## Executive Summary

This report presents a thorough quantitative financial engineering audit of portfolio allocation models, position sizing limits, microstructure transaction friction, and macro crisis risk gating within the 18-strategy automated trading system.

### Key Audit Findings Table

| Area | Component | Implementation Status | Issues / Vulnerabilities Identified | Severity / Impact | Recommended Fix |
|---|---|---|---|---|---|
| **1. HRP Allocation & Shrinkage** | `src/analysis/portfolio_optimizer.py:230` | Implemented (scipy linkage + recursive bisection) | 1. `shrink_covariance_matrix` uses fixed constant $\alpha=0.15$ rather than Ledoit-Wolf analytical optimal intensity.<br>2. Line 304 in HRP uses inverse volatility ($1/\sigma_i$) instead of inverse variance ($1/\sigma_i^2$) for cluster weighting. | **MEDIUM** (Sub-optimal cluster variance weighting) | 1. Replace constant shrinkage with sample-variance Ledoit-Wolf formula.<br>2. Change `inv_vol_left = 1.0 / vols_left` to `inv_var_left = 1.0 / (vols_left ** 2)`. |
| **2. Position Limits & Liquidity** | `src/risk/position_sizing.py`, `pretrade_gatekeeper.py` | Implemented across multiple layers | Single-asset caps (15%), sector caps (30-35%), VIX caps, ADV limits (5%) are strictly defined, but enforcement is split across multiple modules without unified pipeline entry point. | **LOW** (Fragmentation risk) | Ensure `PreTradeRiskGatekeeper` is systematically called before order dispatch in `run_pipeline.py`. |
| **3. Microstructure Transaction Costs** | `src/ai/ensemble_scorer.py:1137`, `microstructure.py` | Implemented (STT tax, SEC fee, dynamic spread, square-root impact) | Line 1220 in `ensemble_scorer.py` computes `2.0 * clamped_spread`. Since `clamped_spread` is already the FULL bid-ask spread, multiplying by 2.0 double-counts the spread (deducts 4 half-spreads for a round-trip). | **HIGH** (Over-penalizes expected returns by 2x spread) | Change `2.0 * clamped_spread` to `1.0 * clamped_spread` (or `2.0 * half_spread`) in round-trip cost sum. |
| **4. RiskManager & CrisisGating** | `src/risk/risk_manager.py`, `run_pipeline.py:2616` | Implemented (VIX, USD/KRW, Oil, TNX composite score) | `run_pipeline.py:2643` wraps RiskManager in `try...except Exception`, which silently bypasses crisis gating if macro indicators are missing/corrupted. | **MEDIUM** (Risk bypass under missing data) | Add a safe fallback evaluation (e.g. VIX-only check) inside the except block so crisis gating is never silently skipped. |

---

## Detailed Investigation & Evidence Chain

### 1. Hierarchical Risk Parity (HRP) & Covariance Shrinkage Audit

#### 1.1 HRP Algorithm Verification
- **Code Path**: `trading_system/src/analysis/portfolio_optimizer.py`, lines 230–330.
- **Observed Implementation**:
  ```python
  230: def calculate_hrp_weights(cov_matrix: np.ndarray) -> np.ndarray:
  ...
  251:     cov_matrix = shrink_covariance_matrix(cov_matrix, shrink_factor=0.15)
  ...
  267:     dist = np.sqrt(np.maximum(0.0, 0.5 * (1.0 - corr)))
  272:     link = linkage(dist_condensed, method='single')
  285:     quasi_diag = get_quasi_diag(link, n)
  ```

- **Analysis of Covariance Shrinkage**:
  - `shrink_covariance_matrix` (`portfolio_optimizer.py:216-227`):
    ```python
    def shrink_covariance_matrix(cov_matrix: np.ndarray, shrink_factor: float = 0.15) -> np.ndarray:
        diag_target = np.diag(np.diag(cov_matrix))
        shrunk_cov = (1.0 - shrink_factor) * cov_matrix + shrink_factor * diag_target
        return shrunk_cov
    ```
  - **Finding**: The function uses a fixed linear shrinkage parameter ($\alpha = 0.15$) towards a diagonal variance matrix. While effective at ensuring positive definiteness and dampening off-diagonal noise, it is a constant heuristic rather than Ledoit & Wolf's (2004) analytical optimal shrinkage intensity $\delta^*$, which dynamically estimates $\delta^*$ based on sample covariance asymptotics.

- **Analysis of Recursive Bisection (Lopez de Prado 2016)**:
  - Lines 303–317:
    ```python
    cov_left = cov_matrix[np.ix_(c_left, c_left)]
    vols_left = np.maximum(np.sqrt(np.diag(cov_left)), 1e-8)
    inv_vol_left = 1.0 / vols_left  # <--- INACCURACY: Should be inverse VARIANCE
    w_left = inv_vol_left / np.sum(inv_vol_left)
    var_left = float(w_left @ cov_left @ w_left)
    ```
  - **Finding**: Marcos Lopez de Prado's HRP paper ("Building Diversified Portfolios that Outperform Out-of-Sample", JPM 2016, Section 3.3) specifies that cluster variance $V_L = \mathbf{w}_L^T \mathbf{\Sigma}_L \mathbf{w}_L$ must be computed using inverse-variance weights $\mathbf{w}_L = \frac{\text{diag}(\mathbf{\Sigma}_L)^{-1}}{\text{trace}(\text{diag}(\mathbf{\Sigma}_L)^{-1})}$.
  - In line 304, the code uses `inv_vol_left = 1.0 / vols_left` ($1/\sigma_i$, inverse volatility). This under-penalizes high-variance assets within a cluster relative to true inverse-variance ($1/\sigma_i^2$) weighting.

- **HRP Integration in Portfolio Allocation**:
  - `trading_system/src/risk/position_sizing.py:268-297`:
    `calculate_hrp_weights` is called when `use_hrp=True`. Returns matrix is padded safely (`fillna(mean)`), covariance matrix is calculated, and weights are multiplied by `market_budget * max_total_allocation`.
    Line 325 properly renormalizes weights after Top-N candidate selection (`current_hrp_sum -> max_total_allocation`).

---

### 2. Position Sizing Limits, Sector Exposure & Liquidity Constraints Audit

#### 2.1 Single-Asset Caps & Position Limits
- **PreTradeRiskGatekeeper** (`src/risk/pretrade_gatekeeper.py:66`):
  Enforces `max_single_stock_weight = 0.15` (15%). Clamps orders exceeding 15% of portfolio value.
- **PortfolioAllocator** (`src/risk/position_sizing.py:349`):
  Enforces `df_candidates['weight'] = df_candidates['weight'].clip(upper=self.max_single_position)` (default 15%).
- **RiskManager VIX Risk-Off Gating** (`src/risk/risk_manager.py:763-774` & `859-863`):
  Dynamic VIX caps:
  - VIX > 30: max position size capped at 15% of portfolio
  - VIX > 25: max position size capped at 30% of portfolio
  - VIX > 20: max position size capped at 50% of portfolio
  - VIX <= 20: 100% position limit (no extra VIX cap)

#### 2.2 Sector Neutrality & Exposure Limits
- **PortfolioOptimizer Sector Constraint** (`src/risk/portfolio_optimizer.py:157-237`):
  `apply_factor_and_sector_constraints` iteratively caps sector exposures at `max_sector_weight` (default 35%), scales down overflowing sectors, and scales up eligible under-allocated sectors without exceeding caps.
- **PortfolioAllocator Sector Cap** (`src/risk/position_sizing.py:360-370`):
  Aggregates sector totals and scales down any sector exceeding `max_sector_exposure` (default 30%).

#### 2.3 Liquidity & ADV Volume Rules
- **Pre-Trade ADV Limit** (`src/risk/pretrade_gatekeeper.py:73-88`):
  Rejects or resizes any order where `order_size_shares / avg_daily_volume_20d > max_order_adv_pct` (default 5% of 20d ADV). Automatically scales order size down to `max_shares = int(20d_ADV * 0.05)`.
- **Ensemble Scorer Liquidity Gate** (`src/ai/ensemble_scorer.py:1238-1271`):
  Filters out preferred stocks (`우`, `우B`), SPACs (`스팩`, `SPAC`), zero volume names, and illiquid stocks whose turnover is less than 10% of minimum market turnover (`min_daily_volume_krx`, `min_daily_volume_sp500`). Sets `ensemble_score` and `ensemble_expected_return` to 0.0.

---

### 3. Microstructure Transaction Cost Model Audit

#### 3.1 Model Structure
The codebase implements a 3-part microstructure cost model across `ensemble_scorer.py`, `microstructure.py`, and `portfolio_allocator.py`:
$$\text{Total Friction} = \text{Tax \& Fees} + \text{Bid-Ask Spread Cost} + \text{Market Impact Cost}$$

1. **Tax & Fees Schedule**:
   - **KRX KOSDAQ**: STT Tax 0.18% (`0.0018`) + Brokerage fee 0.03% (`0.0003`).
   - **KRX KOSPI**: STT Tax 0.15% (`0.0015`) + Brokerage fee 0.03% (`0.0003`).
   - **US (SP500 / NASDAQ / RUSSELL2000)**: SEC Fee 0.003% (`0.00003`) + Brokerage fee 0.005% (`0.00005`).

2. **Dynamic Bid-Ask Spread Model**:
   $$\text{Spread}_i = \text{BaseSpread} \times \left(\frac{\text{ADV}_{\text{ref}}}{\text{ADV}_i}\right)^{0.25} \times \left(\frac{\sigma_i}{\sigma_0}\right)^{0.50}$$
   Clamped within `[spread_min, spread_max]`.
   Base Spreads: KOSPI = 0.06%, KOSDAQ = 0.10%, NASDAQ = 0.03%, RUSSELL2000 = 0.08%, SP500 = 0.02%.

3. **Square-Root Market Impact (Kyle / Almgren-Chriss)**:
   $$\text{Impact}_{\text{one-way}} = \gamma \times \sigma_i \times \left(\frac{Q}{\text{ADV}}\right)^\alpha$$
   Participation Overflow Penalty: If $\frac{Q}{\text{ADV}} > 10\%$, adds $+ 0.50 \times \left(\frac{Q}{\text{ADV}} - 0.10\right)$.

#### 3.2 Double-Spread Deduction Bug in `ensemble_scorer.py`
- **Code Reference**: `trading_system/src/ai/ensemble_scorer.py`, line 1220:
  ```python
  1205: dynamic_spread = base_spread * (adv_ratio ** 0.25) * (vol_ratio ** 0.50)
  1206: clamped_spread = min(max(dynamic_spread, spread_min), spread_max)
  ...
  1220: raw_total_cost = stt_tax + brokerage_fee + (2.0 * clamped_spread) + (2.0 * impact_one_way)
  1221: cost_scaling = getattr(self, 'cost_scaling_factor', 1.0)
  1222: total_cost_pct = raw_total_cost * cost_scaling
  1226: merged['ensemble_expected_return'] = (raw_exp_ret - cost_series * 100.0).clip(lower=0.0, upper=50.0)
  ```
- **Evidence & Discrepancy Analysis**:
  - `clamped_spread` is calculated starting from `base_spread` (e.g. `base_spread_kospi = 0.0006`, i.e., 6 bps). This is ALREADY the full bid-ask spread (the difference between Ask and Bid).
  - In line 1220, `(2.0 * clamped_spread)` doubles this full bid-ask spread!
  - For a round-trip trade (buy at Ask = $P + \frac{1}{2}S$, sell at Bid = $P - \frac{1}{2}S$), the total spread paid is exactly ONE full spread ($1.0 \times S$).
  - By multiplying `clamped_spread` by 2.0, `ensemble_scorer.py` deducts 2 full spreads (4 half-spreads, e.g., 12 bps instead of 6 bps for KOSPI), artificially depressing expected net returns of high-rank signals.

---

### 4. RiskManager & CrisisDetector Audit

#### 4.1 Crisis Indicators & Composite Scoring
- **Code Path**: `trading_system/src/risk/risk_manager.py`, lines 78–297.
- **Evaluation Mechanism**:
  `CrisisDetector.evaluate()` aggregates 5 distinct risk signals:
  1. `_score_vix(vix)`: VIX baseline 15, ROC bonus.
  2. `_score_drawdown(dd)`: Drawdown depth relative to 20% max DD + speed of drawdown.
  3. `_score_volume(volume_ratio)`: Abnormal market volume spikes (>3.0x).
  4. `_score_trend_breakdown(cache)`: Proportion of stocks with EMA20 < EMA50.
  5. `_score_macro(usdkrw, oil, tnx, dxy)`: FX devaluation (USD/KRW spike), Crude Oil ($100+), Treasury Yields (^TNX spike), US Dollar Index (DXY > 100).
- **Composite Crisis Score**:
  $$\text{Composite} = 0.25 \times S_{\text{VIX}} + 0.25 \times S_{\text{DD}} + 0.15 \times S_{\text{Vol}} + 0.10 \times S_{\text{Trend}} + 0.25 \times S_{\text{Macro}}$$
- **Crisis Classification & Actions**:
  - `CrisisLevel.SEVERE` ($\ge 0.75$): Zeroes out ensemble scores/returns, blocks new buys, mandates liquidation after 3 days. Cash target = 85%, position multiplier = 0.15x.
  - `CrisisLevel.ACTIVE` ($\ge 0.50$): Scales down expected returns by 50% (`0.50x`), cash target = 60%, position multiplier = 0.40x.
  - `CrisisLevel.WATCH` ($\ge 0.25$): Cash target = 30%, position multiplier = 0.70x.
  - `CrisisLevel.NONE` ($< 0.25$): Default posture. Cash target = 10%, position multiplier = 1.0x.

#### 4.2 Pipeline Integration & Silent Exception Vulnerability
- **Code Reference**: `trading_system/run_pipeline.py`, lines 2616–2644:
  ```python
  2616: # ── RiskManager & CrisisDetector Integration ──
  2617: try:
  2618:     from src.risk.risk_manager import RiskManager, CrisisDetector, CrisisLevel
  2619:     risk_mgr = RiskManager()
  2620:     crisis_detector = CrisisDetector(risk_mgr)
  2621:     crisis_lvl = crisis_detector.evaluate(
  2622:         vix=vix_report,
  2623:         usdkrw=usdkrw_report,
  2624:         oil=wti_report,
  2625:         tnx=us10y_report
  2626:     )
  2627:     logger.info(f"[RISK MANAGER] Current Market Crisis Level evaluated: {crisis_lvl.value}")
  2628:     if crisis_lvl in [CrisisLevel.SEVERE, CrisisLevel.ACTIVE]:
  2629:         logger.warning(f"[RISK MANAGER] Crisis Level {crisis_lvl.value} active! Scaling down ensemble expected returns.")
  2630:         scale_factor = 0.5 if crisis_lvl == CrisisLevel.ACTIVE else 0.0
  2631:         ensemble_df['ensemble_expected_return'] = ensemble_df['ensemble_expected_return'] * scale_factor
  2632:         if crisis_lvl == CrisisLevel.SEVERE:
  2633:             ensemble_df['ensemble_score'] = 0.0
  ...
  2643: except Exception as _rm_e:
  2644:     logger.warning(f"RiskManager evaluation skipped: {_rm_e}")
  ```
- **Finding & Vulnerability**:
  Wrapping the entire RiskManager evaluation in a broad `try...except Exception` block creates a single point of silent failure: if `usdkrw_report` or `wti_report` is `None` or raises a unexpected type error inside `_score_macro`, the exception is logged as a warning, and the pipeline continues with un-gated expected returns (100% position sizing), even during an active market crash!

---

## Recommended Code Fixes

### Proposed Fix 1: Correct HRP Cluster Variance Formula & Ledoit-Wolf Shrinkage
File: `trading_system/src/analysis/portfolio_optimizer.py`

```python
# Fix in calculate_hrp_weights (lines 304 & 312)
# Replace inverse-volatility with inverse-variance:
cov_left = cov_matrix[np.ix_(c_left, c_left)]
vars_left = np.maximum(np.diag(cov_left), 1e-12)
inv_var_left = 1.0 / vars_left
w_left = inv_var_left / np.sum(inv_var_left)
var_left = float(w_left @ cov_left @ w_left)

cov_right = cov_matrix[np.ix_(c_right, c_right)]
vars_right = np.maximum(np.diag(cov_right), 1e-12)
inv_var_right = 1.0 / vars_right
w_right = inv_var_right / np.sum(inv_var_right)
var_right = float(w_right @ cov_right @ w_right)
```

### Proposed Fix 2: Correct Round-Trip Spread Cost Calculation
File: `trading_system/src/ai/ensemble_scorer.py`

```python
# Fix in _get_cost_pct (line 1220)
# Change (2.0 * clamped_spread) to (1.0 * clamped_spread) since clamped_spread is already full bid-ask spread
raw_total_cost = stt_tax + brokerage_fee + (1.0 * clamped_spread) + (2.0 * impact_one_way)
```

### Proposed Fix 3: Robust Fallback in Pipeline RiskManager Integration
File: `trading_system/run_pipeline.py`

```python
# Fix in RiskManager integration block (lines 2617-2644)
try:
    from src.risk.risk_manager import RiskManager, CrisisDetector, CrisisLevel
    risk_mgr = RiskManager()
    crisis_detector = CrisisDetector(risk_mgr)
    
    # Safe numerical conversions for macro inputs
    vix_val = float(vix_report) if pd.notna(vix_report) and vix_report > 0 else 20.0
    usdkrw_val = float(usdkrw_report) if pd.notna(usdkrw_report) and usdkrw_report > 0 else None
    oil_val = float(wti_report) if pd.notna(wti_report) and wti_report > 0 else None
    tnx_val = float(us10y_report) if pd.notna(us10y_report) and us10y_report > 0 else None
    
    crisis_lvl = crisis_detector.evaluate(
        vix=vix_val,
        usdkrw=usdkrw_val,
        oil=oil_val,
        tnx=tnx_val
    )
    logger.info(f"[RISK MANAGER] Current Market Crisis Level evaluated: {crisis_lvl.value}")
    if crisis_lvl in [CrisisLevel.SEVERE, CrisisLevel.ACTIVE]:
        logger.warning(f"[RISK MANAGER] Crisis Level {crisis_lvl.value} active! Scaling down ensemble expected returns.")
        scale_factor = 0.5 if crisis_lvl == CrisisLevel.ACTIVE else 0.0
        ensemble_df['ensemble_expected_return'] = ensemble_df['ensemble_expected_return'] * scale_factor
        if crisis_lvl == CrisisLevel.SEVERE:
            ensemble_df['ensemble_score'] = 0.0
except Exception as _rm_e:
    logger.error(f"RiskManager evaluation encountered error: {_rm_e}. Applying VIX safety fallback.")
    if 'vix_report' in locals() and vix_report >= 25.0:
        logger.warning("[RISK FALLBACK] VIX >= 25.0 detected in fallback! Applying ACTIVE crisis scaling (0.5x).")
        ensemble_df['ensemble_expected_return'] = ensemble_df['ensemble_expected_return'] * 0.5
```
