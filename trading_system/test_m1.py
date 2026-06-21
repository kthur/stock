import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.ai.sentiment import analyze_sentiment
from src.ai.rl_trading import train_rl_model

def test_sentiment():
    print("Testing sentiment...")
    score = analyze_sentiment("This is a good stock")
    print(f"Score for 'This is a good stock': {score}")
    assert isinstance(score, float)

    score2 = analyze_sentiment("This is a terrible stock")
    print(f"Score for 'This is a terrible stock': {score2}")

def test_rl():
    print("Testing RL...")
    data = [100, 101, 102, 105, 103, 100]
    model = train_rl_model(data)
    print("RL Model trained successfully:", model)

if __name__ == "__main__":
    test_sentiment()
    test_rl()
    print("All tests passed.")
