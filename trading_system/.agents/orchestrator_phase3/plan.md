# Phase 3 Orchestrator Plan
Created: 2026-06-06T19:59:00+09:00

## Mission
Implement 5 Phase 3 deliverables for the stock trading system.

## Environment Assessment
- Python venv: d:/Finance/code/stock/trading_system/.venv
- Available: numpy 1.26.4, torch 2.12.0, scikit-learn 1.9.0, scipy 1.17.1
- Missing: reportlab, fpdf2 (need to install one)

## Existing Code Status
- src/ai/sentiment.py: STUB (3 lines, just `pass`)
- src/ai/rl_trading.py: STUB (3 lines, just `pass`)
- src/broker/real_broker.py: BASIC (29 lines, connect/submit_order mocked but needs abstract base + Korean broker support)
- src/strategy/allocation.py: BASIC (32 lines, only proportional allocation, needs equal weight/risk parity/momentum)
- src/utils/report_generator.py: EXISTS (88 lines, has reportlab PDF gen) - need pdf_report.py

## Deliverables Plan

### 1. src/ai/sentiment.py (IMPLEMENT FROM SCRATCH)
- Use keyword-based + simple NLP approach (no external API needed)
- Return positive/negative float score
- No heavy dependencies

### 2. src/ai/rl_trader.py (NEW FILE)
- Pure PyTorch DQN implementation
- Stock trading environment class
- Training loop with random price data
- Must complete 1+ training cycle

### 3. src/strategy/asset_allocation.py (NEW FILE)
- Equal weight, risk parity, momentum strategies
- Given 3+ stocks with price data, weights sum to 100%
- Build on / separate from existing allocation.py

### 4. src/utils/pdf_report.py (NEW FILE)
- Install reportlab first
- Generate PDF from backtest results + trade journal
- Must save .pdf file to disk

### 5. src/broker/real_broker.py (ENHANCE EXISTING)
- Add abstract Broker base class
- RealBroker with Korean broker support (Korea Investment & Securities / Kiwoom)
- connect() and submit_order() must work without exceptions

## Strategy
- Single Worker agent implements all 5 deliverables
- Worker also runs verification tests
- Reviewer checks correctness
