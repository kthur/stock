# Project Plan - Fundamental Data Integration

## Objective
Incorporate fundamental data (Revenue, Operating Income, Dividends) and features (`operating_margin`, `revenue_to_market_cap`, `dividend_yield`) into:
1. Stock prediction models (`OnDevicePredictionModel`, `macro_predictor.py`, etc.)
2. Feature engineering pipelines
3. Strategy engine (`HybridStrategyEngine`)
4. Database schemas (new table `stock_fundamentals` in `market_indicators.db`)
5. Documentation (`docs/SYSTEM_ARCHITECTURE.md`)
6. Tests (ensure everything passes and new features are tested)

## Planned Milestones

### Milestone 1: Database Schema & Feature Engineering
- Create `stock_fundamentals` table in `market_indicators.db` with CRUD operations support.
- Implement API fetching (e.g. `yfinance`/`FinanceDataReader`) with deterministic offline mock/fallback support via `FallbackMetadataDict`.
- Compute three new fundamental features:
  1. `operating_margin` = Operating Income / Revenue
  2. `revenue_to_market_cap` = Revenue / Market Cap
  3. `dividend_yield` = Dividend Per Share / Close Price (or direct yield)

### Milestone 2: Price Prediction Model Update
- Modify `OnDevicePredictionModel`, training pipelines, and `macro_predictor.py` to support the new 12-feature model schema.
- Update XGBoost prediction configuration/parameters.

### Milestone 3: Strategy Engine & Post-Market Scoring updates
- Update `HybridStrategyEngine` and `post_market_scoring.py` to leverage the updated prediction models and features in technical scoring and allocation rules.

### Milestone 4: Documentation & Test Updates
- Update system architecture in `docs/SYSTEM_ARCHITECTURE.md`.
- Implement unit/integration tests to verify feature calculations, model prediction, and scoring pipeline.
- Verify the entire pytest suite passes.

## Verification Protocol
For each milestone:
1. Dispatch Explorer to analyze and propose strategy.
2. Dispatch Worker to implement changes, run build/tests.
3. Dispatch Reviewer, Challenger, and Auditor to inspect, stress test, and verify integrity.
4. Gate checklist: All tests pass, reviews clear, auditor clean.
