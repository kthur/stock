# Original User Request

## 2026-07-31T18:38:57+09:00

You are the Project Orchestrator for the 5 Key Institutional-Grade Quantitative Enhancements project for the Stock Trading System.

Working directory: d:\Finance\code\stock\.agents\orchestrator
Original request file: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md

Please create your workspace directory at `d:\Finance\code\stock\.agents\orchestrator`, create your `BRIEFING.md` and `plan.md`, and orchestrate subagent specialists to execute the quantitative financial engineering enhancements across all requirements (R1-R5):

### R1. Intraday Microstructure & Dynamic Stop-Loss Engine
- Implement intraday order book / price momentum tracking and dynamic stop-loss gating (-4% drop or volume spike panic detection) in `src/risk/intraday_stop_loss.py`.
- Integrate into `RiskManager` and `run_pipeline.py`.

### R2. Quad-Factor Neutral QP Portfolio Risk Optimizer
- Implement Quadratic Programming (QP) optimization in `src/strategy/quad_factor_optimizer.py` balancing Sharpe ratio while constraining Market Beta, Size, Volatility, and Momentum factor exposures close to zero, along with max 25% sector caps.

### R3. CPCV & Historical Stress Testing Engine
- Implement Combinatorial Purged Cross-Validation (CPCV) in `src/ai/cpcv_stress_tester.py` to eliminate time-series data leakage/embargo issues.
- Add historical stress testing simulating 2008 Financial Crisis, 2020 COVID panic, and 2022 Fed rate hike scenarios.

### R4. Closed-Loop Realized Slippage Execution Feedback
- Link execution logs (`trade_logs.db`) in `src/execution/slippage_feedback.py` to calculate real vs theoretical slippage.
- Dynamically update microstructure cost parameters in `src/ai/ensemble_scorer.py`.

### R5. LLM/NLP DART & SEC Filing Sentiment Engine
- Extract sentiment/tone scores from DART/SEC filings in `src/core/llm_sentiment_engine.py` using LLM/FinBERT tone analysis.
- Incorporate sentiment metrics into Event-Driven alpha factor scores in `src/core/event_driven.py`.

### Acceptance Criteria
- [ ] Pytest test suite covering all 5 new modules passes cleanly with zero failures (`.venv/bin/pytest tests/ -v`).
- [ ] Integration verification script executing `run_pipeline.py` or synthetic test runs successfully end-to-end without breaking existing 18-strategy pipeline outputs.

Instructions:
1. Break down work into clear milestones with verification steps.
2. Delegate tasks to specialized subagents or execute them carefully, ensuring unit and integration tests pass cleanly.
3. Update `progress.md` continuously as milestones progress.
4. When ALL milestones are complete and verified by pytest and integration tests, notify Sentinel with a completion report.

## 2026-07-31T19:10:26Z

Resume work at d:\Finance\code\stock\.agents\orchestrator. Read handoff.md, BRIEFING.md, ORIGINAL_REQUEST.md, and progress.md for current state.
Your parent is 63cd3448-9086-458e-945b-205d2528f68a — use this ID for all escalation and status reporting (send_message).

You are the Project Orchestrator successor (Generation 2).
Next immediate milestone: Milestone 3 (R3: CPCV & Historical Stress Testing Engine).

Please start by initializing your heartbeat timer `schedule(CronExpression="*/10 * * * *", Prompt="Heartbeat check on subagents and update progress.md")`, updating BRIEFING.md with your generation status, and dispatching `explorer_m3_1` to design Milestone 3 (CPCV & Historical Stress Testing Engine).
