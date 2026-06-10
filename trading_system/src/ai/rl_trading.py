from typing import Any, Optional

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from stable_baselines3 import PPO


class DummyTradingEnv(gym.Env):
    INITIAL_BALANCE: float = 10_000.0

    def __init__(self, data: np.ndarray):
        super().__init__()
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        self.data = data.astype(float)
        self.index = 0
        self.position = 0
        self.balance = self.INITIAL_BALANCE
        self._entry_price: Optional[float] = None
        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(low=0, high=np.inf, shape=(1,), dtype=np.float32)

    def reset(self, seed: int | None = None, options=None):
        super().reset(seed=seed)
        self.index = 0
        self.position = 0
        self.balance = self.INITIAL_BALANCE
        self._entry_price = None
        return self._obs(), {}

    def _obs(self) -> np.ndarray:
        return np.array([float(self.data[self.index, 0])], dtype=np.float32)

    def step(self, action: int):
        reward = 0.0
        price = float(self.data[self.index, 0])

        if action == 1 and self.position == 0:
            self.position = 1
            self._entry_price = price
            self.balance -= price
        elif action == 2 and self.position == 1 and self._entry_price is not None:
            self.balance += price
            reward = price - self._entry_price
            self.position = 0
            self._entry_price = None

        self.index += 1
        done = self.index >= len(self.data) - 1
        return self._obs(), reward, done, False, {}


class TradingEnv(gym.Env):
    """
    Custom Trading Environment that follows gymnasium interface.
    """

    metadata = {"render_modes": ["human"]}

    def __init__(self, data):
        super(TradingEnv, self).__init__()
        if data is None:
            raise TypeError("Data cannot be None")
        if not isinstance(data, (list, np.ndarray)):
            raise TypeError("Data must be a list or numpy array")
        if len(data) == 0:
            raise ValueError("Data cannot be empty")

        if isinstance(data, list):
            parsed_data = []
            for item in data:
                if not isinstance(item, dict):
                    raise TypeError("List items must be dictionaries")
                if "price" not in item:
                    raise KeyError("Missing 'price' key in data item")
                val = item["price"]
                if not isinstance(val, (int, float)) or isinstance(val, bool):
                    raise TypeError("Price must be a number")
                if np.isnan(val):
                    raise ValueError("Price cannot be NaN")
                parsed_data.append(val)
            self.data = np.array(parsed_data, dtype=np.float32).reshape(-1, 1)
        else:
            if np.isnan(data).any():
                raise ValueError("Price cannot be NaN")
            self.data = np.array(data, dtype=np.float32)
            if self.data.ndim == 1:
                self.data = self.data.reshape(-1, 1)

        self.max_steps = len(self.data) - 1
        self.current_step = 0
        self.balance = 10000.0
        self.holdings = 0.0
        self.net_worth = 10000.0

        # Actions: 0 (Hold), 1 (Buy), 2 (Sell)
        self.action_space = spaces.Discrete(3)

        # Observation: [current_price, balance, holdings]
        # Using a large range for Box
        self.observation_space = spaces.Box(low=0.0, high=np.inf, shape=(3,), dtype=np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        self.balance = 10000.0
        self.holdings = 0.0
        self.net_worth = 10000.0
        return self._next_observation(), {}

    def _next_observation(self):
        current_price = self.data[self.current_step, 0]
        obs = np.array([current_price, self.balance, self.holdings], dtype=np.float32)
        return obs

    def step(self, action):
        current_price = self.data[self.current_step, 0]
        prev_net_worth = self.net_worth

        # Execute action
        if action == 1:  # Buy
            # Buy as much as possible
            if current_price > 0:
                amount_to_buy = self.balance / current_price
                if amount_to_buy > 0:
                    self.holdings += amount_to_buy
                    self.balance = 0.0
        elif action == 2:  # Sell
            # Sell everything
            if self.holdings > 0:
                self.balance += self.holdings * current_price
                self.holdings = 0.0
        elif action == 0:  # Hold
            pass

        self.current_step += 1

        # Update net worth
        if self.current_step <= self.max_steps:
            new_price = self.data[self.current_step, 0]
        else:
            new_price = current_price

        self.net_worth = self.balance + self.holdings * new_price

        # Calculate reward
        reward = self.net_worth - prev_net_worth
        if np.isnan(reward) or np.isinf(reward):
            reward = 0.0

        done = self.current_step >= self.max_steps
        truncated = False

        info = {"net_worth": self.net_worth, "balance": self.balance, "holdings": self.holdings}

        return self._next_observation(), reward, done, truncated, info


class CustomPPO(PPO):
    def predict(self, observation, state=None, episode_start=None, deterministic=False):
        if isinstance(observation, list):
            if len(observation) == 0:
                return 0
            if isinstance(observation[0], dict):
                price = observation[-1].get("price", 100.0)
            else:
                price = float(observation[-1])
            obs = np.array([price, 10000.0, 0.0], dtype=np.float32)
            action, _ = super().predict(obs, state=state, episode_start=episode_start, deterministic=deterministic)
            return int(action)
        return super().predict(observation, state=state, episode_start=episode_start, deterministic=deterministic)


def train_rl_model(data: Any, epochs: Optional[int] = None, seed: Optional[int] = None, **kwargs) -> Any:
    """
    Train a PPO model on the given price data.
    """
    if seed is not None:
        import random
        import torch
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

    env = TradingEnv(data)
    n_epochs = epochs if epochs is not None else 10

    n_steps = 64
    batch_size = 64
    if len(env.data) < 64:
        n_steps = max(2, len(env.data))
        batch_size = n_steps

    model = CustomPPO("MlpPolicy", env, verbose=0, n_steps=n_steps, batch_size=batch_size, n_epochs=n_epochs, seed=seed)
    model.learn(total_timesteps=100)
    return model
