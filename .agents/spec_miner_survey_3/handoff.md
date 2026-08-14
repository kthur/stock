# Handoff Report: Spec Miner 3

**From**: Spec Miner 3  
**To**: Orchestrator / Parent Agent (`585de8bf-8bf3-479d-9eda-c3f262decf97`)  
**Working Directory**: `d:/Finance/code/stock/.agents/spec_miner_survey_3`  
**Handoff Type**: Soft Handoff  
**Date**: 2026-08-12  

---

## 1. Observation

1. **Microstructure Cost Model (`trading_system/src/risk/microstructure.py`)**:
   - `MicrostructureCostModel` at line 32 computes market impact via:
     `impact = self.cfg.market_impact_gamma * daily_vol * math.sqrt(participation_rate)` (line 70).
   - Currently, `daily_vol = max(0.005, volatility / math.sqrt(252.0))` uses annualized `volatility` parameter only. It does not accept intraday ATR (`atr` / `intraday_atr_pct`).
   - Transaction fees and tax rates are defined in `TransactionCostConfig` (lines 20–30): KOSPI STT `0.0018` (0.18%), US SEC `0.0000278`, base spread `0.0005` (0.05%).
2. **Portfolio Allocation Guardrails (`trading_system/src/risk/portfolio_allocator.py` & `trading_system/src/execution/oms_engine.py`)**:
   - `PortfolioAllocator.__init__` line 33 defines `default_max_weight = 0.20` (20%), and line 34 defines `default_max_sector_weight = 0.35` (35%).
   - `apply_sector_and_factor_constraints` lines 501–504 sets sector caps at 0.25 (BEAR/SIDEWAYS) or 0.35 (BULL).
   - Requirement R3 specifies single stock weight $\le 5\%$ ($0.05$) and sector weight $\le 20\%$ ($0.20$).
   - `ExecutionOMSEngine` in `trading_system/src/execution/oms_engine.py` (lines 36–73) initializes `order_plans` and `execution_logs` tables in `trade_logs.db`. It currently lacks compliance status columns or a `portfolio_compliance_logs` table for tracking single stock and sector limits.
3. **CI/CD Build Artifact Archiving (`.github/workflows/pipeline.yml`)**:
   - `pipeline.yml` runs a 5-market matrix pipeline and uploads split results (`result-SP500`, `result-KOSPI`, etc.), merged results (`merged-results`), and deploys HTML dashboard to GitHub Pages.
   - Requirement R4 asks to archive output files (`ensemble_predictions.txt`, `strategy_data_coverage_report.txt`, `index.html`) as build artifacts. `pipeline.yml` can be updated with an explicit `upload-artifact` step in `deploy-pages` with `name: build-prediction-artifacts` and `retention-days: 30`.
4. **Existing Unit Tests (`trading_system/tests/`)**:
   - `trading_system/tests/test_microstructure.py`: tests basic tax/fee rates and net expected return.
   - `trading_system/tests/test_portfolio_optimizer_and_oms.py`: tests risk parity, sector cap, order plan generation, price bounds, kill switch, share rounding, and slippage calculation.

---

## 2. Logic Chain

1. **Microstructure Enhancement**:
   - Market impact needs to adapt to intraday volatility spikes (ATR) and large order sizes relative to ADV.
   - Adding `atr: Optional[float] = None` and `price: Optional[float] = None` to `calculate_market_impact` allows substituting or scaling `daily_vol` with $\frac{\text{atr}}{\text{price}}$.
   - Adding a non-linear penalty multiplier when $\frac{\text{order\_amount}}{\text{adv}} > 0.05$ accurately reflects market depth friction.
2. **OMS & Portfolio Guardrails**:
   - To strictly align with requirement R3, `default_max_weight` in `PortfolioAllocator` must be updated from `0.20` to `0.05`, and `default_max_sector_weight` / regime caps must be capped at `0.20`.
   - `ExecutionOMSEngine` in `oms_engine.py` must create `portfolio_compliance_logs` and populate compliance fields in `order_plans` in `trade_logs.db`.
3. **CI/CD Artifact Archiving**:
   - Adding an explicit `actions/upload-artifact@v4` step in `pipeline.yml` targeting `ensemble_predictions.txt`, `strategy_data_coverage_report.txt`, and `index.html` satisfies R4 requirement.

---

## 3. Caveats

1. `PROJECT.md` references `src/core/microstructure.py`, but the actual Python file in the codebase is `trading_system/src/risk/microstructure.py`.
2. Existing unit tests in `trading_system/tests/test_portfolio_optimizer_and_oms.py` currently test `default_max_sector_weight=0.40`. When updating `PortfolioAllocator` defaults, unit tests should be updated to test both default guardrails (5% single stock, 20% sector cap) and explicit overrides.

---

## 4. Conclusion

- All specification findings, exact line numbers, architectural designs, DB schemas, workflow step updates, and test specifications have been documented in detail in `d:/Finance/code/stock/.agents/spec_miner_survey_3/report.md`.
- No code modifications were performed during this specification mining turn.

---

## 5. Verification Method

1. Inspect `d:/Finance/code/stock/.agents/spec_miner_survey_3/report.md` for full details.
2. Verify existing test baseline passes cleanly:
   `.venv/bin/pytest trading_system/tests/test_microstructure.py trading_system/tests/test_portfolio_optimizer_and_oms.py -v`
