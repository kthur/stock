"""
DQN-based Reinforcement Learning Trading Agent.
Uses pure PyTorch — no stable-baselines3 dependency.
"""

import random
import math
from collections import deque
from typing import List, Tuple, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim


# ─── Trading Environment ──────────────────────────────────────────────────────

class TradingEnvironment:
    """
    A simple stock trading environment.

    State space: [current_price_norm, position, unrealized_pnl_norm]
    Action space: 0=hold, 1=buy, 2=sell
    """

    def __init__(self, prices: list):
        """
        Args:
            prices: List of historical prices (floats/ints).
        """
        if len(prices) < 2:
            raise ValueError("prices must have at least 2 data points")
        self.prices = np.array(prices, dtype=np.float32)
        self._price_mean = float(np.mean(self.prices))
        self._price_std = float(np.std(self.prices)) or 1.0
        self.n_steps = len(self.prices)
        self.state_dim = 3   # price_norm, position, unrealized_pnl_norm
        self.action_dim = 3  # hold, buy, sell

        self._step_idx: int = 0
        self._position: float = 0.0      # 0=flat, 1=long
        self._entry_price: float = 0.0
        self._done: bool = False

    # ------------------------------------------------------------------
    def _get_state(self) -> np.ndarray:
        price = self.prices[self._step_idx]
        price_norm = (price - self._price_mean) / self._price_std

        if self._position > 0 and self._entry_price > 0:
            pnl = (price - self._entry_price) / self._entry_price
        else:
            pnl = 0.0

        return np.array([price_norm, self._position, pnl], dtype=np.float32)

    def reset(self) -> np.ndarray:
        """Reset environment to initial state, return initial observation."""
        self._step_idx = 0
        self._position = 0.0
        self._entry_price = 0.0
        self._done = False
        return self._get_state()

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, dict]:
        """
        Execute an action and advance the environment by one step.

        Args:
            action: 0=hold, 1=buy, 2=sell

        Returns:
            (next_state, reward, done, info)
        """
        if self._done:
            raise RuntimeError("Episode is done. Call reset() first.")

        current_price = self.prices[self._step_idx]
        reward = 0.0
        info: dict = {"action": action, "price": float(current_price)}

        # Execute action
        if action == 1:   # BUY
            if self._position == 0:
                self._position = 1.0
                self._entry_price = current_price
                reward = -0.001  # small transaction cost
        elif action == 2:  # SELL
            if self._position > 0 and self._entry_price > 0:
                pnl_pct = (current_price - self._entry_price) / self._entry_price
                reward = pnl_pct * 10.0  # scale reward
                self._position = 0.0
                self._entry_price = 0.0
                info["pnl_pct"] = pnl_pct
        # action == 0: HOLD — reward is unrealized PnL change if in position

        if self._position > 0 and action == 0:
            # Small reward/penalty for holding based on price direction
            if self._step_idx + 1 < self.n_steps:
                next_price = self.prices[self._step_idx + 1]
                reward = (next_price - current_price) / current_price * 5.0

        # Advance step
        self._step_idx += 1
        if self._step_idx >= self.n_steps - 1:
            # Force close position at end
            if self._position > 0 and self._entry_price > 0:
                last_price = self.prices[-1]
                pnl_pct = (last_price - self._entry_price) / self._entry_price
                reward += pnl_pct * 10.0
                self._position = 0.0
            self._done = True

        next_state = self._get_state()
        return next_state, float(reward), self._done, info


# ─── Replay Memory ────────────────────────────────────────────────────────────

class ReplayBuffer:
    """Experience replay buffer for DQN."""

    def __init__(self, capacity: int = 10_000):
        self.buffer: deque = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int):
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            np.array(states, dtype=np.float32),
            np.array(actions, dtype=np.int64),
            np.array(rewards, dtype=np.float32),
            np.array(next_states, dtype=np.float32),
            np.array(dones, dtype=np.float32),
        )

    def __len__(self):
        return len(self.buffer)


# ─── DQN Network ─────────────────────────────────────────────────────────────

class QNetwork(nn.Module):
    """Deep Q-Network: state_dim -> [64, 64] -> action_dim."""

    def __init__(self, state_dim: int, action_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# ─── DQN Agent ────────────────────────────────────────────────────────────────

class DQNAgent:
    """
    DQN Agent with experience replay and target network.

    Args:
        state_dim: Dimensionality of observation space.
        action_dim: Number of discrete actions.
        lr: Learning rate.
        gamma: Discount factor.
        epsilon_start: Initial exploration rate.
        epsilon_end: Minimum exploration rate.
        epsilon_decay: Decay steps for epsilon.
        batch_size: Batch size for training updates.
        target_update_freq: Steps between target network updates.
    """

    def __init__(
        self,
        state_dim: int = 3,
        action_dim: int = 3,
        lr: float = 1e-3,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.05,
        epsilon_decay: int = 500,
        batch_size: int = 32,
        target_update_freq: int = 50,
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon_start = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq

        self.device = torch.device("cpu")  # keep lightweight

        # Networks
        self.q_net = QNetwork(state_dim, action_dim).to(self.device)
        self.target_net = QNetwork(state_dim, action_dim).to(self.device)
        self.target_net.load_state_dict(self.q_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.q_net.parameters(), lr=lr)
        self.loss_fn = nn.SmoothL1Loss()

        self.replay_buffer = ReplayBuffer()
        self.steps_done = 0
        self.last_loss: float = 0.0

    # ------------------------------------------------------------------
    def _epsilon(self) -> float:
        """Current epsilon using exponential decay."""
        return self.epsilon_end + (self.epsilon_start - self.epsilon_end) * \
               math.exp(-1.0 * self.steps_done / self.epsilon_decay)

    def select_action(self, state: np.ndarray) -> int:
        """
        Select action using epsilon-greedy policy.

        Args:
            state: Current environment state as numpy array.

        Returns:
            int: Selected action index.
        """
        eps = self._epsilon()
        self.steps_done += 1

        if random.random() < eps:
            return random.randrange(self.action_dim)

        state_t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            q_values = self.q_net(state_t)
        return int(q_values.argmax(dim=1).item())

    def _update(self) -> Optional[float]:
        """Perform one gradient update step. Returns loss or None."""
        if len(self.replay_buffer) < self.batch_size:
            return None

        states, actions, rewards, next_states, dones = self.replay_buffer.sample(self.batch_size)

        states_t = torch.FloatTensor(states).to(self.device)
        actions_t = torch.LongTensor(actions).to(self.device)
        rewards_t = torch.FloatTensor(rewards).to(self.device)
        next_states_t = torch.FloatTensor(next_states).to(self.device)
        dones_t = torch.FloatTensor(dones).to(self.device)

        # Current Q values
        current_q = self.q_net(states_t).gather(1, actions_t.unsqueeze(1)).squeeze(1)

        # Target Q values (Bellman)
        with torch.no_grad():
            next_q = self.target_net(next_states_t).max(dim=1)[0]
            target_q = rewards_t + self.gamma * next_q * (1.0 - dones_t)

        loss = self.loss_fn(current_q, target_q)
        self.optimizer.zero_grad()
        loss.backward()
        # Gradient clipping for stability
        torch.nn.utils.clip_grad_norm_(self.q_net.parameters(), 1.0)
        self.optimizer.step()

        # Update target network periodically
        if self.steps_done % self.target_update_freq == 0:
            self.target_net.load_state_dict(self.q_net.state_dict())

        return float(loss.item())

    def train(self, env: TradingEnvironment, episodes: int = 5) -> List[float]:
        """
        Train the agent on the given environment.

        Args:
            env: TradingEnvironment instance.
            episodes: Number of training episodes.

        Returns:
            List of total rewards per episode.
        """
        episode_rewards: List[float] = []

        for ep in range(episodes):
            state = env.reset()
            total_reward = 0.0
            done = False

            while not done:
                action = self.select_action(state)
                next_state, reward, done, _ = env.step(action)
                self.replay_buffer.push(state, action, reward, next_state, float(done))
                state = next_state
                total_reward += reward

                loss = self._update()
                if loss is not None:
                    self.last_loss = loss

            episode_rewards.append(total_reward)

        return episode_rewards


# ─── Top-level training function ─────────────────────────────────────────────

def train_rl_model(data: list = None) -> dict:
    """
    Train a DQN trading agent.

    Args:
        data: Optional list of price data. If None, generates synthetic random prices.

    Returns:
        dict with keys:
            'episodes': int — number of episodes completed
            'rewards': list of float — reward per episode
            'final_loss': float — last recorded training loss
    """
    if data is None or len(data) == 0:
        # Generate synthetic random walk prices
        rng = np.random.RandomState(42)
        n = 100
        returns = rng.randn(n) * 0.01
        prices = [100.0]
        for r in returns:
            prices.append(prices[-1] * (1 + r))
        data = prices

    env = TradingEnvironment(prices=data)
    agent = DQNAgent(
        state_dim=env.state_dim,
        action_dim=env.action_dim,
        lr=1e-3,
        gamma=0.95,
        epsilon_start=1.0,
        epsilon_end=0.1,
        epsilon_decay=200,
        batch_size=16,
        target_update_freq=20,
    )

    n_episodes = 5
    rewards = agent.train(env, episodes=n_episodes)

    return {
        "episodes": len(rewards),
        "rewards": [round(r, 4) for r in rewards],
        "final_loss": round(agent.last_loss, 6),
    }
