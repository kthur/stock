# AI Pipeline Implementation Strategy (Milestone 1)

## Observation
- `PROJECT.md` and `SCOPE.md` require the implementation of an AI Pipeline for Phase 3, comprising `src/ai/sentiment.py` and `src/ai/rl_trading.py`.
- The Acceptable Criteria states:
  1. **Sentiment Analysis**: `analyze_sentiment(text: str) -> float` returns a positive/negative score from dummy text without errors.
  2. **RL Model**: `train_rl_model(data)` completes at least 1 training cycle using `stable-baselines3` or `PyTorch` with mock price data.
- The `requirements.txt` includes `openai` and `google-generativeai` but lacks RL frameworks like `stable-baselines3`, `gymnasium`, or `torch`.
- Currently, `src/ai/sentiment.py` and `src/ai/rl_trading.py` do not exist.
- Directory `tests/phase3/` does not exist or is empty.

## Logic Chain
1. **RL Environment Setup**: To meet the RL training cycle AC, the simplest and most compliant approach is using `stable-baselines3` with PPO or DQN. This requires adding `stable-baselines3` and `gymnasium` to `requirements.txt`.
2. **train_rl_model Implementation**: We need to wrap the provided `data` in a custom `gymnasium.Env` (e.g., `DummyTradingEnv`), then instantiate a `PPO` model and call `model.learn(total_timesteps=len(data))` to successfully execute a training cycle.
3. **analyze_sentiment Implementation**: The AC specifically asks for a script returning a score for a dummy text. Even though it's an "LLM sentiment analysis" pipeline, relying on actual LLM calls (OpenAI/Gemini) during unit tests without guaranteed API keys will cause exceptions. Therefore, `sentiment.py` should either:
   - Provide a dummy fallback scoring logic for tests (e.g., keyword-based heuristic returning `0.8` for "good"/"긍정", `-0.8` for "bad"/"부정").
   - Include the API connection skeleton but bypass it with dummy data during tests.
4. **Testing Phase 3**: Both functions must have automated tests in `tests/phase3/test_m1_ai_pipeline.py` to independently verify they meet the Acceptance Criteria.

## Caveats
- No LLM API keys are expected to be available during testing. A robust test mock or dummy logic is strongly recommended.
- PyTorch can be heavy to install in some CI environments, but since `stable-baselines3` depends on it, it must be added to requirements.

## Conclusion
- **Implementation Strategy**:
  - Update `requirements.txt` to include `stable-baselines3`, `gymnasium`.
  - Create `src/ai/sentiment.py` implementing `analyze_sentiment(text: str) -> float` with an LLM prompt skeleton and a dummy logic fallback for unit testing.
  - Create `src/ai/rl_trading.py` implementing `train_rl_model(data)` utilizing a custom `gymnasium.Env` and `stable-baselines3.PPO` for a simple training run.
  - Implement unit tests in `tests/phase3/test_m1_ai_pipeline.py`.

## Verification Method
- Execute `pytest tests/phase3/test_m1_ai_pipeline.py` (after implementation).
- The tests should pass, ensuring both `analyze_sentiment` returns a float score and `train_rl_model` finishes its cycle without throwing exceptions.
