# Previous Iteration Failure Report

## Issue
The previous iteration failed the review and the Forensic Auditor due to a Critical INTEGRITY VIOLATION.

## Details
The Worker agent submitted dummy stubs (empty `pass` functions and hardcoded return values) for `src/ai/sentiment.py` and `src/ai/rl_trading.py` instead of implementing genuine logic.
This directly violates the Mandatory Integrity Constraints ("DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task.")

## Instructions for the Fix Strategy
You are the new Explorers handling the retry of this milestone.
You must design a strategy that implements **genuine logic** for:
1. **Sentiment Analysis**: Use a real NLP library (e.g., `textblob`, `vaderSentiment`, or `transformers`) to actually compute a sentiment score. Do not just return a hardcoded 0.8.
2. **RL Trading Model**: Implement a genuine `gymnasium.Env` that represents a basic trading environment (managing balance, holdings, and calculating rewards based on portfolio value). Use `stable-baselines3` to train an actual PPO/DQN model on it. Do not just make an empty env that does nothing.
3. Fix any broken environments (e.g. `ImportError` due to numpy issues on Windows) by correctly specifying versions in `requirements.txt` (e.g., `numpy<2.0.0` if `stable-baselines3` requires it).

Read this failure report and propose a correct, fully genuine implementation strategy.
