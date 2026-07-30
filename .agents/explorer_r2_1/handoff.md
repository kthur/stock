# Handoff Report — Explorer 2 (Requirement R2: Precision Order Book Market Impact Cost Modeling)

## 1. Observation
- **Configuration Analysis (`trading_system/src/config.py`)**:
  - `TradingConfig` defines `slippage_krx_market_order: float = 0.005`, `min_daily_volume_krx: float = 5_000_000_000.0`, and `min_daily_volume_sp500: float = 1_000_000.0` (lines 65–67).
  - No configuration fields exist for order size hypothesis ($Q$), market impact square-root coefficients ($Y$), base bid-ask spreads ($S_{base}$), or volatility sensitivity ($\sigma$).

- **Cost Function in `EnsembleScoringEngine` (`trading_system/src/ai/ensemble_scorer.py`)**:
  - Inside `combine_predictions` (lines 928–948), cost calculation relies on local function `_get_cost_pct`:
    ```python
    # Market impact penalty based on liquidity (higher impact for low turnover)
    impact_penalty = 0.005 if turnover < 100_000_000 else (0.002 if turnover < 1_000_000_000 else 0.0)

    if market == 'KONEX' or symbol.endswith('.KN'):
        return 0.0010 + 0.0010 + base_slippage + impact_penalty  # STT 0.10% + Spread 0.10%
    elif market == 'KOSDAQ' or symbol.endswith('.KQ'):
        return 0.0018 + 0.0015 + base_slippage + impact_penalty  # STT 0.18% + Spread 0.15%
    elif market == 'KOSPI' or symbol.endswith('.KS') or (symbol.isdigit() and len(symbol) == 6):
        return 0.0015 + 0.0008 + base_slippage + impact_penalty  # STT 0.15% + Spread 0.08%
    elif market == 'SP500' or (symbol.isalpha() and len(symbol) <= 5):
        return 0.0003 + 0.0003 + (base_slippage * 0.2) + impact_penalty  # SEC fee + Tight US spread
    return 0.0020 + base_slippage + impact_penalty
    ```
  - **Defect 1**: Static hardcoded constants for bid-ask spread (KOSPI 0.08%, KOSDAQ 0.15%, KONEX 0.10%, SP500 0.03%) regardless of stock turnover or volatility.
  - **Defect 2**: Coarse 2-tier step-function penalty (`impact_penalty` = 0.005 for turnover < 100M KRW, 0.002 for turnover < 1B KRW, 0.0 for >= 1B KRW) causing artificial cost cliffs.
  - **Defect 3**: Total absence of order size hypothesis ($Q$) and square-root market impact scaling ($I \propto \sqrt{Q / ADV}$).
  - **Defect 4**: Volatility ($\sigma$) is ignored during execution cost estimation.

- **Existing Test Coverage (`trading_system/tests/test_r1_ensemble_regime_fixes.py`)**:
  - `test_transaction_costs_and_slippage_all_markets` (lines 85–120) verifies flat rates:
    - KOSPI: 0.35% + 0.5% = 0.85% (net expected return 24.15%)
    - KOSDAQ: 0.50% + 0.5% = 1.00% (net expected return 24.00%)
    - KONEX: 0.80% + 0.5% = 1.30% (net expected return 23.70%)
    - SP500: 0.10% + 0.5% = 0.60% (net expected return 24.40%)

---

## 2. Logic Chain
1. **Observation 1 & 2** reveal that current cost deductions use fixed static rates and step-function penalties rather than a continuous market microstructure formulation.
2. In real equity markets, bid-ask spread and market impact scale continuously with stock turnover ($ADV$) and daily price volatility ($\sigma$).
3. Placing trades of size $Q$ incurs price impact following the Kyle / Almgren-Chriss Square-Root Law:
   $$I_{impact} = Y \cdot \sigma \cdot \sqrt{\frac{Q}{ADV}}$$
4. Adding order size parameters ($Q_{KRX} = 50\text{M KRW}$, $Q_{SP500} = \$50\text{K USD}$) and empirical market impact coefficients ($Y_{KRX} = 0.75$, $Y_{SP500} = 0.50$) to `TradingConfig` enables dynamic, quantitative cost estimation across all 3,379 symbols.
5. Updating `_get_cost_pct` in `EnsembleScoringEngine` to compute:
   - Dynamic Spread: $\text{Spread}_{\%} = S_{base} \cdot (ADV_{ref} / ADV)^{0.25} \cdot (\sigma / 0.02)^{0.50}$ (clamped to market bounds)
   - One-Way Market Impact: $I_{impact,\%} = Y \cdot \sigma \cdot \sqrt{Q / ADV} + \text{Penalty}_{Q/ADV > 0.10}$
   - Total Friction: $\text{STT}_{\text{sell}} + \text{Fee}_{\text{broker}} + \text{Spread}_{\%} + 2 \cdot I_{impact,\%}$
   replaces static guesses with financial rigor.
6. Creating a new test file `trading_system/tests/test_order_book_market_impact.py` guarantees square-root scaling, volatility sensitivity, and participation rate overflow behavior.

---

## 3. Caveats
- **Historical Volatility Availability**: If `volatility_20d` is missing in the row DataFrame, `_get_cost_pct` falls back to default daily volatility ($0.020$ for KRX, $0.015$ for SP500).
- **Intraday Order Book Depth**: Tick-level L2/L3 order book depth is not fetched; the square-root model serves as the industry standard proxy for order book depth.

---

## 4. Conclusion
The precision order book market impact cost model has been fully designed and documented in `D:\Finance\code\stock\.agents\explorer_r2_1\analysis_r2.md`. Implementing this model requires:
1. Adding order size ($Q$), market impact coefficient ($Y$), and base spread parameters to `TradingConfig` (`trading_system/src/config.py`).
2. Upgrading `_get_cost_pct` and `get_regime_reasoning_summary` in `EnsembleScoringEngine` (`trading_system/src/ai/ensemble_scorer.py`).
3. Adding unit tests in `trading_system/tests/test_order_book_market_impact.py`.

---

## 5. Verification Method
1. **File Inspection**:
   - Inspect `D:\Finance\code\stock\.agents\explorer_r2_1\analysis_r2.md` for complete formulas, config changes, and implementation snippets.
2. **Pytest Execution**:
   - Run existing unit tests to confirm environment sanity:
     ```powershell
     .venv\Scripts\python.exe -m pytest trading_system/tests/test_r1_ensemble_regime_fixes.py -v
     ```
   - Upon implementation by the Implementer agent, execute the new test suite:
     ```powershell
     .venv\Scripts\python.exe -m pytest trading_system/tests/test_order_book_market_impact.py -v
     ```
3. **Invalidation Conditions**:
   - If market impact does not increase when order size $Q$ increases relative to $ADV$.
   - If low turnover stocks receive lower bid-ask spread cost than high turnover stocks.
   - If `TradingConfig` does not allow overriding $Q$ via environment variables `ORDER_SIZE_KRX` / `ORDER_SIZE_SP500`.
