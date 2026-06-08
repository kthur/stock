# Worker Instructions: Milestone 1 AI Pipeline

You are implementing Milestone 1: AI Pipeline.

## Critical Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Tasks
1. **Dependencies**: Update `requirements.txt` to include `transformers`, `torch`, `stable-baselines3`, `gymnasium`, and `numpy<2.0.0`. Do NOT remove existing dependencies. (This fixes Windows Numpy import errors).
2. **Sentiment Analysis (`src/ai/sentiment.py`)**:
   - Implement `analyze_sentiment(text: str) -> float`.
   - Must use `transformers.pipeline("sentiment-analysis")` (e.g., the default distilbert model).
   - Convert the output (e.g. POSITIVE/NEGATIVE) to a float score (e.g. 0.0 to 1.0 or -1.0 to 1.0) and return it.
   - Do NOT just return a hardcoded float.

3. **RL Trading Model (`src/ai/rl_trading.py`)**:
   - Implement `train_rl_model(data)`.
   - Must define a custom `TradingEnv(gymnasium.Env)` that tracks portfolio balance/holdings and calculates rewards based on the provided price data.
   - Action space should be Discrete(3) (buy, hold, sell) or similar.
   - Observation space should be Box (prices/balances).
   - Instantiate `stable_baselines3.PPO` with this environment.
   - Call `model.learn(total_timesteps=100)` or similar small number to complete 1 training cycle genuinely on the data.

4. **Testing**: 
   - After implementing, you MUST run tests or write a script to verify that:
     a) `analyze_sentiment("This is a good stock")` runs and returns a float.
     b) `train_rl_model([100, 101, 102, 105, 103, 100])` (or similar mock data) completes a training cycle without error.
   - Record your findings and commands used in your `handoff.md`.
