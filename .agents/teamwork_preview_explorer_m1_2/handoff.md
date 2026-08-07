# Handoff Report: HRP, Risk Management & Microstructure Transaction Cost Audit

**Agent Folder**: `.agents/teamwork_preview_explorer_m1_2/`
**Milestone**: Milestone 1 (Financial Engineering & Quantitative Risk Audit)

---

## 1. Observation

Direct observations from codebase inspection across `src/analysis/portfolio_optimizer.py`, `src/risk/portfolio_allocator.py`, `src/risk/position_sizing.py`, `src/risk/pretrade_gatekeeper.py`, `src/risk/microstructure.py`, `src/risk/risk_manager.py`, `src/ai/ensemble_scorer.py`, and `trading_system/run_pipeline.py`:

1. **HRP Implementation & Cluster Variance Formula**:
   - File: `trading_system/src/analysis/portfolio_optimizer.py`, lines 303–317.
   - Quote:
     ```python
     303: cov_left = cov_matrix[np.ix_(c_left, c_left)]
     304: vols_left = np.maximum(np.sqrt(np.diag(cov_left)), 1e-8)
     305: inv_vol_left = 1.0 / vols_left
     306: w_left = inv_vol_left / np.sum(inv_vol_left)
     307: var_left = float(w_left @ cov_left @ w_left)
     ```
   - In line 305, cluster weighting uses `1.0 / vols_left` ($1/\sigma_i$, inverse volatility) rather than inverse variance ($1/\sigma_i^2$).
   - Covariance shrinkage in line 251 calls `shrink_covariance_matrix(cov_matrix, shrink_factor=0.15)`, which applies a constant linear shrinkage parameter $\alpha=0.15$ towards diagonal variance target rather than analytical optimal Ledoit-Wolf intensity $\delta^*$.

2. **Position Sizing, Sector Caps & ADV Limits**:
   - Single-asset caps: `PreTradeRiskGatekeeper` (`pretrade_gatekeeper.py:66`) clamps at `0.15` (15%). `PortfolioAllocator` (`position_sizing.py:349`) clamps at `0.15`. `RiskManager` (`risk_manager.py:860`) clamps dynamically based on VIX (15% for VIX>30, 30% for VIX>25, 50% for VIX>20).
   - Sector caps: `PortfolioOptimizer` (`portfolio_optimizer.py:157-237`) iteratively caps sectors at `0.35` (35%). `PortfolioAllocator` (`position_sizing.py:360-370`) caps sector totals at `0.30` (30%).
   - ADV volume limits: `PreTradeRiskGatekeeper` (`pretrade_gatekeeper.py:73-88`) rejects/resizes orders exceeding 5% of 20d ADV. `EnsembleScoringEngine` (`ensemble_scorer.py:1238-1271`) sets scores to 0.0 for preferred stocks, SPACs, and names with turnover < 10% of minimum threshold.

3. **Microstructure Transaction Cost Formula Discrepancy**:
   - File: `trading_system/src/ai/ensemble_scorer.py`, line 1220.
   - Quote:
     ```python
     1205: dynamic_spread = base_spread * (adv_ratio ** 0.25) * (vol_ratio ** 0.50)
     1206: clamped_spread = min(max(dynamic_spread, spread_min), spread_max)
     ...
     1220: raw_total_cost = stt_tax + brokerage_fee + (2.0 * clamped_spread) + (2.0 * impact_one_way)
     ```
   - `clamped_spread` is calculated from `base_spread` (e.g. 0.0006 for KOSPI = 6 bps), which is already the FULL bid-ask spread. Line 1220 multiplies `clamped_spread` by 2.0, deducting 2 full spreads (4 half-spreads, e.g., 12 bps for KOSPI) for a round-trip trade instead of 1 full spread (2 half-spreads).

4. **RiskManager & CrisisDetector Pipeline Gating**:
   - File: `trading_system/src/risk/risk_manager.py`, lines 78–297 (`CrisisDetector.evaluate()`), and `trading_system/run_pipeline.py`, lines 2616–2644.
   - Quote:
     ```python
     2628: if crisis_lvl in [CrisisLevel.SEVERE, CrisisLevel.ACTIVE]:
     2629:     logger.warning(f"[RISK MANAGER] Crisis Level {crisis_lvl.value} active! Scaling down ensemble expected returns.")
     2630:     scale_factor = 0.5 if crisis_lvl == CrisisLevel.ACTIVE else 0.0
     2631:     ensemble_df['ensemble_expected_return'] = ensemble_df['ensemble_expected_return'] * scale_factor
     2632:     if crisis_lvl == CrisisLevel.SEVERE:
     2633:         ensemble_df['ensemble_score'] = 0.0
     ...
     2643: except Exception as _rm_e:
     2644:     logger.warning(f"RiskManager evaluation skipped: {_rm_e}")
     ```
   - Composite crisis evaluation incorporates VIX, USD/KRW, WTI Crude, ^TNX 10Y Yield, DXY Dollar Index, Drawdown, and Market Volume Spikes.
   - Active crisis levels scale down returns by 50% (ACTIVE) or zero out returns/scores (SEVERE). However, wrapping the evaluation in a generic `try...except Exception` block in `run_pipeline.py:2643` allows silent bypass if macro inputs contain unexpected formats or missing values.

---

## 2. Logic Chain

1. **Premise 1**: Marcos Lopez de Prado's HRP algorithm derives cluster variance from inverse-variance weighted sub-portfolios $\mathbf{w}_L = \frac{\text{diag}(\mathbf{\Sigma}_L)^{-1}}{\text{trace}(\text{diag}(\mathbf{\Sigma}_L)^{-1})}$.
   - *Observation*: Line 305 of `portfolio_optimizer.py` uses `1.0 / vols_left` ($1/\sigma_i$), which distorts cluster variance estimation $V_L = \mathbf{w}_L^T \mathbf{\Sigma}_L \mathbf{w}_L$ by under-weighting high-volatility assets relative to true inverse variance ($1/\sigma_i^2$).
   - *Inference*: Correcting `1.0 / vols_left` to `1.0 / (vols_left ** 2)` aligns HRP with the standard mathematical formulation.

2. **Premise 2**: A round-trip equity transaction incurs 1 sell-side tax (STT or SEC fee), brokerage fees, 1 full bid-ask spread ($S = \text{Ask} - \text{Bid}$), and entry+exit market impact.
   - *Observation*: Line 1220 of `ensemble_scorer.py` calculates `raw_total_cost = stt_tax + brokerage_fee + (2.0 * clamped_spread) + (2.0 * impact_one_way)`.
   - *Inference*: Since `clamped_spread` is the full spread, multiplying by 2.0 deducts 2 full spreads (4 half-spreads). For KOSPI, this deducts 12 bps instead of 6 bps, double-counting spread drag and artificially suppressing signals of legitimate top stocks. Changing `2.0 * clamped_spread` to `1.0 * clamped_spread` fixes the over-deduction.

3. **Premise 3**: Quantitative risk controls must fail closed during market anomalies rather than failing open.
   - *Observation*: Line 2643 of `run_pipeline.py` catches all exceptions during `RiskManager` evaluation and logs `RiskManager evaluation skipped`.
   - *Inference*: If macro data fetch fails or raises a type error, crisis gating is skipped and the pipeline defaults to un-gated 100% position sizing during market crashes. Adding a VIX fallback in the `except` block ensures safety even if full macro indicators are incomplete.

---

## 3. Caveats

- **No Live Order Execution Tested**: Audit is based on static code analysis, mathematical verification, and unit test results. Live broker API execution was not triggered.
- **Constant vs. Dynamic Shrinkage**: `shrink_covariance_matrix` uses a constant shrinkage parameter $\alpha=0.15$. While stable for 60-day window matrices, a fully dynamic Ledoit-Wolf intensity calculation could provide slightly more optimal out-of-sample variance estimation for non-stationary market regimes.

---

## 4. Conclusion

- **HRP Allocation**: Correctly implements distance matrix computation, single-linkage hierarchical clustering, quasi-diagonalization, and recursive bisection, but requires a 1-line formula fix in `portfolio_optimizer.py` (changing inverse volatility $1/\sigma_i$ to inverse variance $1/\sigma_i^2$).
- **Position Sizing & Liquidity Limits**: Strictly enforced across `PreTradeRiskGatekeeper` (15% single-asset cap, 5% 20d ADV limit), `PortfolioAllocator` (30% sector cap), `RiskManager` (VIX-linked caps), and `EnsembleScoringEngine` (Liquidity Gate filtering SPACs, preferred stocks, and low turnover names).
- **Microstructure Cost Model**: Accurately includes STT tax (0.18%/0.15%), SEC fees, dynamic bid-ask spread, and square-root market impact, but double-counts the bid-ask spread in `ensemble_scorer.py:1220` (`2.0 * clamped_spread`), which should be corrected to `1.0 * clamped_spread`.
- **RiskManager & CrisisDetector**: Multi-factor macro crisis scoring (VIX, USD/KRW, Oil, TNX, DXY, Drawdown) correctly triggers defensive posturing (50% scaling on ACTIVE, 100% block on SEVERE). Robustness should be enhanced by adding a VIX fallback inside `run_pipeline.py:2643`.

---

## 5. Verification Method

To independently verify the audit findings and code behavior:

1. **Run Portfolio Optimization & Risk Tests**:
   ```bash
   .venv/bin/pytest tests/test_hrp_optimizer.py tests/phase3/test_allocation.py tests/test_config.py -v
   ```
2. **Inspect Code Locations**:
   - `trading_system/src/analysis/portfolio_optimizer.py`: Lines 230–330 (`calculate_hrp_weights`).
   - `trading_system/src/ai/ensemble_scorer.py`: Lines 1137–1230 (`_get_cost_pct` & line 1220).
   - `trading_system/src/risk/risk_manager.py`: Lines 78–297 (`CrisisDetector`).
   - `trading_system/run_pipeline.py`: Lines 2616–2644 (`RiskManager & CrisisDetector Integration`).
3. **Invalidation Conditions**:
   - The HRP finding is invalidated if $1/\sigma_i$ can be proven mathematically equivalent to $1/\sigma_i^2$ in recursive bisection (it is not; $1/\sigma_i^2$ is the minimum-variance weight solution).
   - The spread cost finding is invalidated if `clamped_spread` is defined as half-spread rather than full spread (line 1205 proves `base_spread` = 0.0006 full spread).
