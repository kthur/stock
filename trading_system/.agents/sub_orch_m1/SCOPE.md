# Scope: Milestone 1: AI Pipeline

## Architecture
- Module `src/ai` contains `sentiment.py` and `rl_trading.py`.
- No dependencies on other Phase 3 milestones.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | AI Pipeline | Implement Sentiment Analysis pipeline returning pos/neg score from text, and an RL model training cycle. | none | IN_PROGRESS |

## Interface Contracts
### AI Pipeline
- `analyze_sentiment(text: str) -> float`: Returns sentiment score.
- `train_rl_model(data)`: Runs a training cycle for DQN/PPO.
