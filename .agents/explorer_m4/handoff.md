# Explorer M4: Microstructure, Execution Slippage, Transaction Costs & Risk Control Audit Report

## 1. Observation

Direct observations from source code inspection of `trading_system/src/ai/ensemble_scorer.py` and `trading_system/src/config.py` (and related pipeline modules):

### A. Transaction Costs, Taxes & Slippage Modeling
- **File**: `trading_system/src/ai/ensemble_scorer.py` (Lines 890–913)
  ```python
  slippage = getattr(self.config, 'slippage_krx_market_order', 0.005) if self.config is not None else 0.005

  def _get_cost_pct(row_or_sym) -> float:
      if isinstance(row_or_sym, pd.Series):
          symbol = str(row_or_sym.get('symbol', ''))
          market = str(row_or_sym.get('market', '')).upper()
      else:
          symbol = str(row_or_sym)
          market = ''

      if market == 'KONEX' or symbol.endswith('.KN'):
          return 0.0080 + slippage
      elif market == 'KOSDAQ' or symbol.endswith('.KQ'):
          return 0.0050 + slippage
      elif market == 'KOSPI' or symbol.endswith('.KS') or (symbol.isdigit() and len(symbol) == 6):
          return 0.0035 + slippage
      elif market == 'SP500' or (symbol.isalpha() and len(symbol) <= 5):
          return 0.0010 + slippage
      return 0.0010 + slippage

  cost_series = merged.apply(_get_cost_pct, axis=1)
  merged['ensemble_expected_return'] = (raw_exp_ret - cost_series * 100.0).clip(lower=0.0, upper=50.0)
  ```
- **File**: `trading_system/src/config.py` (Line 67)
  ```python
  slippage_krx_market_order: float = 0.005      # KRX 시가 슬리피지 (0.5%)
  ```
- Observation: Hardcoded transaction costs (KONEX 0.80%, KOSDAQ 0.50%, KOSPI 0.35%, SP500 0.10%) are added to a flat 0.50% slippage across all assets. Statutory Korean Securities Transaction Tax (STT: KOSPI 0.15% incl. special tax, KOSDAQ 0.18%, KONEX 0.10%) and US SEC fees ($0.0000278/dollar) / FINRA TAF fees ($0.000166/share) are not explicitly modeled or separated from commissions. STT and SEC fees are sell-side only, but `_get_cost_pct` subtracts total costs symmetrically upfront.
- Observation: Bid-ask spread `(Ask - Bid) / Price` is omitted from `ensemble_scorer.py` and `config.py`.

### B. Market Impact Estimation & Micro-Cap Execution
- **File**: `trading_system/src/ai/ensemble_scorer.py` (Lines 913 & 925–946)
  ```python
  def _is_illiquid_or_preferred(row: pd.Series) -> bool:
      sym = str(row.get('symbol', ''))
      name = str(row.get('name', ''))
      # Preferred stock check
      if name.endswith('우') or name.endswith('우B') or name.endswith('1우') or name.endswith('2우B') or name.endswith('3우B'):
          return True
      if len(sym) == 6 and sym[-1] in ['K', 'L', 'M', 'N', 'O']:
          return True
      # SPAC check
      if '스팩' in name or 'SPAC' in name.upper():
          return True
      if 'volume' in row and pd.notna(row['volume']) and float(row['volume']) <= 0:
          return True
      return False
  ```
- Observation: No market impact equation (e.g. $\Delta P / P = \gamma \cdot \sigma \sqrt{Q / ADV}$) exists in `ensemble_scorer.py`. Expected return is calculated independently of trade order size $Q$ relative to Average Daily Volume (ADV).
- Observation: `_is_illiquid_or_preferred` only screens for `volume <= 0` (zero traded shares on the day) alongside preferred stocks and SPACs. Micro-caps with nominal daily volume (e.g., 1 share or ₩50,000 turnover) pass as liquid (`False`) and receive un-penalized execution assumptions.

### C. Liquidity Filtering & Configuration Parameters
- **File**: `trading_system/src/config.py` (Lines 65–66)
  ```python
  min_daily_volume_krx: float = 5_000_000_000.0  # KRX 최소 일평균 거래대금 (50억원)
  min_daily_volume_sp500: float = 1_000_000.0   # SP500 최소 일평균 거래량 (100만 주)
  ```
- Observation: Codebase-wide ripgrep search confirms `min_daily_volume_krx` and `min_daily_volume_sp500` are defined in `config.py` but never referenced in `ensemble_scorer.py` or `run_pipeline.py`.
- **File**: `trading_system/src/ai/ensemble_scorer.py` (Lines 542–544)
  ```python
  lines.append("• Liquidity & Safety Gate:")
  lines.append("  - Zero-weighting preferred stocks (우, B), SPACs, and illiquid symbols from Top recommendations.")
  ```
- Observation: Rationale text in `get_regime_reasoning_summary` claims a liquidity gate filters illiquid symbols, but actual execution only zero-weights zero-volume (`volume <= 0`) symbols.

### D. Risk Management & Portfolio Sizing Integration
- **File**: `trading_system/src/risk/risk_manager.py` vs `trading_system/run_pipeline.py` & `ensemble_scorer.py`
- Observation: `RiskManager` class contains `CrisisDetector`, drawdown limits (`max_drawdown_allowed`), ATR-based dynamic stop-loss (`calculate_atr_based_stop`), trailing stop price logic, sector exposure caps (`check_sector_risk_cap`), and Kelly position sizing.
- Observation: Grep search across `run_pipeline.py` confirms `RiskManager` is never instantiated or called during main pipeline execution. Signal output in `ensemble_predictions.txt` is produced without risk manager gating, stop-loss trigger levels, or tail risk checks.
- **File**: `trading_system/src/risk/position_sizing.py` (Lines 34 & 114–250)
- Observation: `PortfolioAllocator` initializes `self.max_sector_exposure = 0.30`, but the `allocate()` method does not enforce sector exposure caps across candidate allocations.

---

## 2. Logic Chain

1. **Transaction Cost & Slippage Discrepancies**:
   - `_get_cost_pct` applies hardcoded rates (0.35% KOSPI, 0.50% KOSDAQ, 0.80% KONEX, 0.10% SP500) + fixed 0.50% slippage across all assets.
   - Korean STT tax rates (0.15% KOSPI, 0.18% KOSDAQ, 0.10% KONEX) apply only to sell transactions. Charging a symmetric flat fee on expected return upfront over-penalizes buy entries while under-estimating sell tax liability for multi-day holds.
   - For SP500 mega-caps, applying 0.50% (50 bps) market order slippage over-penalizes liquid U.S. equities (where actual slippage is < 1-2 bps). Conversely, for micro-cap KRX stocks, 50 bps under-estimates actual slippage during market orders.
   - Omitting bid-ask spread `(Ask - Bid) / Price` causes mid-price return estimates to overestimate profits for wider-spread assets.

2. **Market Impact & Micro-Cap Vulnerability**:
   - Return calculation `raw_exp_ret - cost_series * 100.0` treats execution price as invariant to trade volume.
   - Because `_is_illiquid_or_preferred` only rejects `volume <= 0`, any micro-cap stock with 1 share traded is rated as liquid and assigned equal execution efficiency as Samsung Electronics or Apple.
   - Large capital deployments (e.g. ₩100M+) into micro-cap stocks with ADV of ₩1M would cause severe market impact (pushing price by 5-20%+), rendering model expected returns unattainable in actual trading.

3. **Unenforced Liquidity Thresholds**:
   - `TradingConfig` specifies `min_daily_volume_krx` (₩5 Billion) and `min_daily_volume_sp500` (1M shares).
   - Because these parameters are completely omitted from `ensemble_scorer.py`, stocks with ₩10M turnover bypass liquidity filters and enter the Top 20 recommendations.
   - The rationale report logs claim illiquid symbols are zero-weighted, creating false operational confidence.

4. **Risk Control Bypass**:
   - `RiskManager` features (CrisisDetector, tail risk, stop-loss, max drawdown limits) are disconnected from `run_pipeline.py`.
   - `PortfolioAllocator.allocate()` lacks active sector exposure capping logic, allowing single sectors (e.g., Semiconductors) to exceed 50%+ of allocated portfolio capital.

---

## 3. Caveats

- **Scope Limits**: Investigation focused on `trading_system/src/ai/ensemble_scorer.py`, `trading_system/src/config.py`, and their interactions in `run_pipeline.py` and `src/risk/`. Individual strategy-specific feature generation modules (e.g. `iv_skew.py`, `order_flow.py`) were not audited for individual indicator calculations.
- **Assumptions**: Assumed live trading mode uses `run_pipeline.py` outputs (`ensemble_predictions.txt` and `portfolio_allocation.txt`).
- **Alternative Interpretations**: The hardcoded 0.50% slippage parameter may have been intended as a conservative aggregate proxy for spread + impact in average-liquidity stocks, but its uniform application creates structural distortions across market caps.

---

## 4. Conclusion & Vulnerability Ratings

### Vulnerability Summary Table

| ID | Severity | Target File & Lines | Category | Description |
|---|---|---|---|---|
| **M4-V1** | **HIGH** | `ensemble_scorer.py`:890–913, `config.py`:67 | Transaction Costs | Hardcoded fixed fee deductions ignore statutory Korean STT (KOSPI 0.15%, KOSDAQ 0.18%, KONEX 0.10%) and US SEC/FINRA fees, applying symmetric upfront deductions instead of sell-side tax modeling. |
| **M4-V2** | **HIGH** | `ensemble_scorer.py`:890–913, `config.py`:63–68 | Slippage & Spread | Complete omission of bid-ask spread modeling `(Ask - Bid) / Price`, leading to overstated expected returns on wide-spread assets. |
| **M4-V3** | **MEDIUM** | `config.py`:67, `ensemble_scorer.py`:892,903–909 | Slippage | Static 0.50% market order slippage applied uniformly to mega-cap SP500 (over-penalizing by ~50x) and micro-caps (under-estimating impact). |
| **M4-V4** | **HIGH** | `ensemble_scorer.py`:885–913 | Market Impact | Omission of position size relative to ADV ($Q / ADV$) market impact estimation; assumes infinite market depth. |
| **M4-V5** | **HIGH** | `ensemble_scorer.py`:925–946 | Micro-cap Penalty | Flawed `_is_illiquid_or_preferred` filter only checks `volume <= 0`, allowing micro-caps with near-zero turnover to populate Top 20 recommendations without penalties. |
| **M4-V6** | **HIGH** | `config.py`:65–66, `ensemble_scorer.py`:925–946 | Liquidity Filter | `min_daily_volume_krx` (₩5B) and `min_daily_volume_sp500` (1M shares) are dead parameters, never enforced in prediction output. |
| **M4-V7** | **MEDIUM** | `ensemble_scorer.py`:542–544 | Rationale Logging | Decision rationale logs report that illiquid symbols are zero-weighted based on turnover, which is factually inaccurate given `volume <= 0` implementation. |
| **M4-V8** | **HIGH** | `risk_manager.py` vs `run_pipeline.py` | Risk Controls | Complete disconnection/bypass of `RiskManager` (CrisisDetector, tail risk controls, max drawdown, ATR stop-loss) during pipeline execution. |
| **M4-V9** | **MEDIUM** | `position_sizing.py`:34,114–250 | Portfolio Controls | `max_sector_exposure` (30%) parameter in `PortfolioAllocator` is un-enforced during candidate allocation, risking heavy sector concentration. |
| **M4-V10** | **MEDIUM** | `config.py`:64, `ensemble_scorer.py`:260,887 | Portfolio Controls | Linear scaling of ensemble scores to return proxy without risk-adjusted drawdown or tail-risk (CVaR) discounting. |

---

## 5. Verification Method

To independently verify these findings:

1. **Verify Unused Config Liquidity Thresholds (M4-V6)**:
   Run grep across the codebase for `min_daily_volume`:
   ```bash
   .venv/bin/python -c "import git, re, pathlib; text = pathlib.Path('trading_system').glob('**/*.py'); print([(f, line) for f in text for line in f.read_text(encoding='utf-8', errors='ignore').splitlines() if 'min_daily_volume' in line])"
   ```
   *Expected Result*: Output only shows definitions in `trading_system/src/config.py`. Zero references exist in `ensemble_scorer.py` or `run_pipeline.py`.

2. **Verify Micro-Cap Execution & Volume Gate Behavior (M4-V5)**:
   Inspect `trading_system/src/ai/ensemble_scorer.py` lines 925–946 using `view_file`. Confirm that `_is_illiquid_or_preferred` checks `float(row['volume']) <= 0` and does not apply `min_daily_volume_krx` or `min_daily_volume_sp500`.

3. **Verify Fixed Fee & Tax Deduction Implementation (M4-V1, M4-V2, M4-V3)**:
   Inspect `trading_system/src/ai/ensemble_scorer.py` lines 890–913. Confirm `_get_cost_pct` returns fixed constants (`0.0080`, `0.0050`, `0.0035`, `0.0010`) + `slippage` (0.005), without bid-ask spread or sell-side STT tax distinction.

4. **Verify RiskManager Pipeline Disconnection (M4-V8)**:
   Run grep for `RiskManager` across `trading_system/run_pipeline.py`:
   ```bash
   grep -n "RiskManager" trading_system/run_pipeline.py
   ```
   *Expected Result*: No matches found.

5. **Run Suite Tests**:
   Execute standard project unit tests to confirm repository state:
   ```bash
   .venv/bin/pytest trading_system/tests/ -v
   ```
