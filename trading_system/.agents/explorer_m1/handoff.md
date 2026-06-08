# Handoff Report: Milestone 1 Implementation Strategy

## Observation
- `failure_report.md` indicates the previous submission failed because it used hardcoded stubs. It explicitly demands:
  1. A real NLP library (e.g., `textblob`, `vaderSentiment`, or `transformers`) for sentiment analysis.
  2. A genuine `gymnasium.Env` and `stable-baselines3` for RL.
- `requirements.txt` contains `stable-baselines3>=2.0.0`, `gymnasium>=0.28.0`, and `numpy>=1.21.0,<2.0.0` but lacks any NLP library.
- `src/ai/sentiment.py` currently contains a ~350-line custom hand-rolled lexicon implementation rather than using an established NLP library.
- `tests/phase3/test_m1_ai_pipeline.py` passes `data` of shape `(100, 5)` to `train_rl_model(data)`.
- `src/ai/rl_trading.py` currently implements `DummyTradingEnv` but it does not inherit from `gymnasium.Env`, lacks `action_space` and `observation_space`, and raises a `ValueError` if `data.shape[1] != 1`. This shape error causes the SB3 model initialization to fail during testing, falling back to a dummy in-house adapter.

## Logic Chain
1. **Sentiment Analysis**: To satisfy the "genuine logic" requirement from the Failure Report, we must discard the custom lexicon in `src/ai/sentiment.py` and replace it with an established NLP library. `vaderSentiment` is the safest and most reliable choice as it does not require downloading external NLP datasets at runtime (unlike NLTK/TextBlob). We need to add it to `requirements.txt`.
2. **RL Trading Model**: Stable-Baselines3's `PPO` requires a fully compliant Gymnasium environment. Therefore, `DummyTradingEnv` must be updated to inherit from `gymnasium.Env` and correctly define `self.action_space = spaces.Discrete(3)` and `self.observation_space = spaces.Box(...)`.
3. **Shape Handling**: To prevent SB3 from failing and triggering the fallback, `DummyTradingEnv` must handle the `(100, 5)` shape passed by the test. We should slice the data (e.g., `self.data = data[:, 0:1]`) to extract the price instead of raising a `ValueError`.
4. **Cleanup**: With a working `gymnasium.Env`, we can remove the fake `_make_inhouse_model` fallback entirely, ensuring that only genuine SB3 logic is used.

## Caveats
- `vaderSentiment` will need to be added to `requirements.txt` and installed in the test environment.
- The state space in `DummyTradingEnv` is currently just the current price `(1,)`. The `observation_space` should match this shape precisely.
- No other files should be touched to strictly limit the scope to Milestone 1.

## Conclusion
We should proceed with the following implementations:
1. Add `vaderSentiment` to `requirements.txt`.
2. Overwrite `src/ai/sentiment.py` to use `vaderSentiment.SentimentIntensityAnalyzer()` to compute and return the compound sentiment score.
3. Overwrite `src/ai/rl_trading.py` so that `DummyTradingEnv` inherits from `gymnasium.Env`, defines valid spaces, handles multi-column data, and directly trains `stable_baselines3.PPO` without fake fallbacks.

## Verification Method
1. Ensure the environment has dependencies installed (`pip install -r requirements.txt`).
2. Run `pytest tests/phase3/test_m1_ai_pipeline.py`.
3. The tests must pass, confirming that `vaderSentiment` is calculating the scores and `stable-baselines3` is training a `PPO` model over a valid `gymnasium.Env`.
