# Handoff Report: Milestone 1 AI Pipeline Integrity Fix Strategy

## 1. Observation
- `src/ai/sentiment.py` currently implements sentiment analysis using a manual lexicon dictionary (357 lines of code). The failure report specifically mandates: "Use a real NLP library (e.g., textblob, vaderSentiment, or transformers) to actually compute a sentiment score."
- `requirements.txt` does not include `vaderSentiment`, `textblob`, or `transformers`.
- `src/ai/rl_trading.py` defines `DummyTradingEnv` but it does not inherit from `gymnasium.Env` and lacks the mandatory properties `self.observation_space` and `self.action_space`.
- `tests/phase3/test_m1_ai_pipeline.py` tests `train_rl_model` by passing dummy data with shape `(100, 5)`. However, `DummyTradingEnv.__init__` in `src/ai/rl_trading.py` throws a `ValueError` if `data.shape[1] != 1`.
- The failure report mandates: "Implement a genuine `gymnasium.Env`... Use `stable-baselines3` to train an actual PPO/DQN model on it... Fix any broken environments by correctly specifying versions in `requirements.txt`."
- `requirements.txt` already specifies `stable-baselines3>=2.0.0`, `gymnasium>=0.28.0`, and `numpy>=1.21.0,<2.0.0`, satisfying the package version constraint.

## 2. Logic Chain
- **Sentiment Analysis**: To satisfy the integrity constraint, we must discard the manual lexicon approach and integrate a real NLP library. Adding `vaderSentiment` to `requirements.txt` and using its `SentimentIntensityAnalyzer.polarity_scores(text)['compound']` is the most straightforward genuine implementation.
- **RL Trading Model (Env)**: For `stable-baselines3` to accept an environment, it MUST inherit from `gymnasium.Env` and define `observation_space` and `action_space`. We must import `gymnasium` and `gymnasium.spaces`, and set:
  - `self.action_space = spaces.Discrete(3)` (0: hold, 1: buy, 2: sell).
  - `self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(data.shape[1],), dtype=np.float32)`.
- **RL Trading Model (Data Shape)**: To prevent `ValueError` during the test, `DummyTradingEnv` must dynamically handle `data.shape[1]` instead of hardcoding validation for shape `(n, 1)`. The `_obs()` method should return `self.data[self.index]` (the entire row). For the reward calculation, it can use the first column `self.data[self.index, 0]` as the price.
- **RL Trading Model (Training)**: `train_rl_model` must instantiate `PPO("MlpPolicy", env, ...)` and call `learn()` as it currently attempts, but without the environment crashing.

## 3. Caveats
- `vaderSentiment` needs to be installed in the environment for tests to pass. The implementer must run `pip install -r requirements.txt` after updating the file.
- We assume `tests/phase3/test_m1_ai_pipeline.py` uses `pytest`. The `DummyTradingEnv` step must return exactly 5 values: `obs, reward, terminated, truncated, info`. It currently does, but must maintain this after subclassing `gymnasium.Env`.

## 4. Conclusion
The implementation strategy to resolve the integrity violation is:
1. **requirements.txt**: Add `vaderSentiment`.
2. **src/ai/sentiment.py**: Replace the manual lexicon logic with `vaderSentiment.SentimentIntensityAnalyzer`.
3. **src/ai/rl_trading.py**:
   - Subclass `gymnasium.Env` for `DummyTradingEnv`.
   - Add `self.observation_space = spaces.Box(...)` and `self.action_space = spaces.Discrete(3)`.
   - Update `DummyTradingEnv` to accept data of any feature size `(n, m)` and use `data.shape[1]` for the observation space shape, using column 0 as the price.
   - Keep the `stable-baselines3` PPO training logic in `train_rl_model`.

## 5. Verification Method
- **Verification Commands**:
  1. `pytest tests/phase3/test_m1_ai_pipeline.py` - should pass without errors.
- **Files to Inspect**: 
  - `src/ai/sentiment.py` must import and use `vaderSentiment`.
  - `src/ai/rl_trading.py` must import `gymnasium`, subclass `gymnasium.Env`, and define spaces.
  - `requirements.txt` must contain `vaderSentiment`.
