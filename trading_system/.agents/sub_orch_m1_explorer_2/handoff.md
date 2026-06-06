# Handoff Report: Milestone 1 AI Pipeline Strategy

## 1. Observation
- **Scope & Interface Contracts (`SCOPE.md`, `PROJECT.md`)**:
  - `src/ai/sentiment.py` must expose `analyze_sentiment(text: str) -> float`.
  - `src/ai/rl_trading.py` must expose `train_rl_model(data)`.
- **Acceptance Criteria (AC) (`original_prompt.md`)**:
  - **Sentiment Analysis**: Must execute without errors when given dummy text and return a positive/negative score.
  - **RL Trading**: Must successfully complete at least 1 training cycle using `stable-baselines3` or `PyTorch` with dummy price data.
- **Dependencies (`requirements.txt`)**: 
  - The project currently lacks RL libraries like `stable-baselines3`, `gymnasium`, or `torch`.
- **Existing Code**: 
  - `src/ai/llm_integration.py` exists and has an `LLMEngine` with a `_simulate_response()` method to handle missing API keys gracefully.

## 2. Logic Chain
1. **Dependency Management**: To fulfill the RL AC using `stable-baselines3` (which is highly recommended for quick RL scaffolding), the implementer must first add `stable-baselines3` and `gymnasium` to `requirements.txt`.
2. **`rl_trading.py` Implementation Strategy**:
   - Since `stable-baselines3` algorithms (like PPO/DQN) expect a Gym environment, the implementer should define a minimal custom `DummyTradingEnv(gymnasium.Env)` within `rl_trading.py`. This environment should take the `data` (e.g., a 1D price array) and implement `step()` (handling buy/sell/hold actions to compute reward) and `reset()`.
   - `train_rl_model(data)` should instantiate this environment and execute `stable-baselines3.PPO("MlpPolicy", env).learn(total_timesteps=100)`. A small `total_timesteps` ensures the function completes the required 1 cycle quickly for the test.
3. **`sentiment.py` Implementation Strategy**:
   - Implement `analyze_sentiment(text: str) -> float`.
   - To pass the AC robustly without real API calls or keys in CI/tests, implement a lightweight heuristic fallback. For example, returning `1.0` if "good" is in text, `-1.0` if "bad", else `0.0`.
   - Alternatively, it can hook into the existing `LLMEngine` from `llm_integration.py` but MUST ensure it uses a simulated response or gracefully catches errors to guarantee that passing "dummy text" never fails. 

## 3. Caveats
- **Missing Dependencies**: Adding `stable-baselines3` and `gymnasium` to `requirements.txt` modifies the project's environment. The implementer must ensure the `test` infrastructure installs these before running tests.
- **Data Format**: `train_rl_model` should accept basic Python `list` or `numpy.ndarray` for the `data` parameter to make writing tests straightforward.
- **LLM API Limits**: `sentiment.py` must avoid network timeouts or missing API key errors during tests. Fallback/mocking is mandatory.

## 4. Conclusion
- **`src/ai/sentiment.py`**: Implement `analyze_sentiment(text: str) -> float` utilizing a mock/heuristic for tests to guarantee no errors with dummy text, while reserving real LLM API calls for production use.
- **`src/ai/rl_trading.py`**: Add `stable-baselines3` and `gymnasium` to `requirements.txt`. Implement a `DummyTradingEnv` and use `stable-baselines3.PPO` inside `train_rl_model(data)` to run a short learning cycle.

## 5. Verification Method
The implementer should write tests in a new file, e.g., `tests/phase3/test_ai_pipeline.py`:
1. `test_sentiment_analysis()`: 
   ```python
   from src.ai.sentiment import analyze_sentiment
   score = analyze_sentiment("dummy text")
   assert isinstance(score, float)
   ```
2. `test_rl_training()`:
   ```python
   from src.ai.rl_trading import train_rl_model
   import numpy as np
   data = np.linspace(100, 150, 50).tolist()
   train_rl_model(data) # Should not raise any exceptions
   ```
Run `pytest tests/phase3/` to confirm the Acceptance Criteria are fulfilled.
