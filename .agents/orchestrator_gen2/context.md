# Context Reference

## System Overview
- **Main configuration**: `trading_system/src/config.py`
- **Main UI/Dashboard**: `trading_system/src/web/dashboard.py` (and `trading_system/run_dashboard.py`)
- **Test suite**: `trading_system/tests/`
- **SQLite Database**: `market_indicators.db` (containing daily stock rankings/scores)
- **Prediction Modules**: `OnDevicePredictionModel`, `macro_predictor.py`, training scripts (in `trading_system/src` or related paths)
- **Strategy Engine**: `HybridStrategyEngine` and `post_market_scoring.py`

## Current Goal (Follow-up Request)
- Incorporate market capitalization, trading volume, and floating shares, using overall market benchmarks to predict prices.
- R1: Market Cap, Volume, and Floating Shares Feature Engineering
- R2: Price Prediction Model Update
- R3: Strategy Engine & Post-Market Scoring updates
- R4: Documentation & Test Updates
