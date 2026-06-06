import pytest
import numpy as np
import os
from src.ai.sentiment import analyze_sentiment
from src.ai.rl_trading import train_rl_model, DummyTradingEnv
from stable_baselines3 import PPO

def test_analyze_sentiment():
    # Test positive sentiment
    score = analyze_sentiment("The company announced record profits and the stock is soaring! We expect good things and it will go up.")
    assert score > 0.0, f"Expected positive score, got {score}"
    
    # Test negative sentiment
    score = analyze_sentiment("Earnings were terrible and the CEO resigned, causing the stock to plummet. It's bad news and going down.")
    assert score < 0.0, f"Expected negative score, got {score}"

def test_train_rl_model():
    # Generate some dummy data
    # 100 timesteps, 5 features
    data = np.random.rand(100, 5) * 100
    
    model = train_rl_model(data)
    assert isinstance(model, PPO), "Model should be a PPO instance"
    assert model.env is not None, "Model should have an environment"
    
def test_dummy_trading_env():
    data = np.array([[100.0], [105.0], [102.0], [110.0], [108.0]])
    env = DummyTradingEnv(data)
    
    obs, info = env.reset()
    assert obs.shape == (1,)
    assert obs[0] == 100.0
    
    # Test Buy action (action 1)
    obs, reward, done, truncated, info = env.step(1)
    assert env.position == 1
    assert env.balance == 10000.0 - 100.0
    assert obs[0] == 105.0
    
    # Test Sell action (action 2)
    obs, reward, done, truncated, info = env.step(2)
    assert env.position == 0
    assert env.balance == 10000.0 - 100.0 + 105.0
    
    # Reach the end
    env.step(0) # obs will be 110.0
    obs, reward, done, truncated, info = env.step(0) # obs will be 108.0, should be done
    assert done is True
