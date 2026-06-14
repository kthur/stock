# Execution Context

## Base Directories
- Project Root: `d:/Finance/code/stock`
- Agent Workspace: `d:/Finance/code/stock/.agents/orchestrator_pipeline`
- Source Directory: `d:/Finance/code/stock/trading_system`
- Tests Directory: `d:/Finance/code/stock/trading_system/tests`

## Key Files to Check
- `trading_system/src/config.py`: Configuration model (`TradingConfig`).
- `trading_system/run_pipeline.py`: Consolidated pipeline runner.
- `trading_system/scripts/post_market_scoring.py`: Scoring script.
- `trading_system/trading_system.py`: Main trading system engine.
- `trading_system/telegram_bot_runner.py`: Current Telegram Bot implementation.
- `market_indicators.db`: SQLite database to write logs into (`pipeline_runs`).

## Target Files to Create / Modify
- `trading_system/orchestrator.py`: Orchestrator core & daemon class.
- `trading_system/run_orchestrator.py`: CLI trigger entrypoint.
- `trading_system/tests/test_orchestrator.py`: Orchestrator verification tests.
