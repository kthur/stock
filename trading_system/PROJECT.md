# Project: Phase 3 Trading System

## Architecture
- **src/ai**: Contains Reinforcement Learning (RL) components (`stable-baselines3` or PyTorch) and LLM-based Sentiment Analysis.
- **src/strategy**: Contains Asset Allocation logics (dynamically redistributing weights).
- **src/broker**: Contains Broker interfaces and implementations (e.g., `RealBroker` for Korea Investment / Kiwoom).
- **src/utils**: Contains utilities, including the PDF Report generation.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | AI Pipeline | Implement Sentiment Analysis pipeline returning pos/neg score from text, and an RL model training cycle. | none | IN_PROGRESS |
| 2 | Asset Allocation | Implement Asset Allocation logic ensuring 100% total weight distribution across given assets. | none | IN_PROGRESS |
| 3 | Broker & Reporting | Implement `RealBroker` with `connect()` and `submit_order()`, and a PDF generation function from mock trade data. | none | IN_PROGRESS |

## Interface Contracts
### AI Pipeline
- `analyze_sentiment(text: str) -> float`: Returns sentiment score.
- `train_rl_model(data)`: Runs a training cycle for DQN/PPO.

### Asset Allocation
- `allocate_assets(prices_dict: dict) -> dict`: Returns normalized weights summing to 1.0.

### Broker
- `RealBroker.connect()`: Establishes connection mock.
- `RealBroker.submit_order(...)`: Submits a dummy order.

### Reporting
- `generate_pdf_report(trade_data: list, file_path: str)`: Creates a `.pdf` file.

## Code Layout
- `src/ai/sentiment.py`: Sentiment Analysis logic.
- `src/ai/rl_trading.py`: RL Training script.
- `src/strategy/allocation.py`: Asset allocation algorithm.
- `src/broker/real_broker.py`: RealBroker API connection skeleton.
- `src/utils/report.py`: PDF report generator.
- `tests/phase3/`: Automated test cases for verifying Acceptance Criteria.
