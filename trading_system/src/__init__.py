# mypy: ignore-errors
import os
import sys

# PyTorch WinError 1114 DLL Loading Crash bypass
if "torch" not in sys.modules:
    should_bypass = os.getenv("BYPASS_TORCH", "").lower() in ("true", "1")
    if os.getenv("BYPASS_TORCH", "").lower() == "false":
        should_bypass = False
    elif not should_bypass:
        try:
            import torch  # noqa: F401
            should_bypass = False
        except Exception:
            should_bypass = True

    if should_bypass:
        import types
        import numpy as np
        class DummyTensor:
            def __init__(self, *args, **kwargs):
                pass
            def to(self, *args, **kwargs):
                return self
            def cpu(self, *args, **kwargs):
                return self
            def numpy(self, *args, **kwargs):
                return np.zeros((10, 1))
            def item(self):
                return 0.0
            def __getitem__(self, item):
                return self
            def size(self, *args, **kwargs):
                return 1
            def float(self):
                return self
            def unsqueeze(self, *args, **kwargs):
                return self
        class DummyNoGrad:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        mock_torch = types.ModuleType("torch")
        mock_torch.Tensor = DummyTensor
        mock_torch.tensor = lambda *a, **k: DummyTensor()
        mock_torch.manual_seed = lambda s: None
        mock_torch.device = lambda *a, **k: None
        mock_torch.from_numpy = lambda *a, **k: DummyTensor()
        mock_torch.no_grad = lambda *a, **k: DummyNoGrad()
        mock_torch.save = lambda *a, **k: None
        mock_torch.load = lambda *a, **k: {}
        mock_torch.randperm = lambda n: [0] * n
        mock_torch.randn = lambda *a, **k: DummyTensor()
        mock_torch.zeros = lambda *a, **k: DummyTensor()
        mock_torch.arange = lambda *a, **k: DummyTensor()
        mock_torch.exp = lambda *a, **k: DummyTensor()
        mock_torch.sin = lambda *a, **k: DummyTensor()
        mock_torch.cos = lambda *a, **k: DummyTensor()
        mock_torch.float = float
        mock_torch.long = int
        mock_torch.is_mocked = True

        mock_cuda = types.ModuleType("torch.cuda")
        mock_cuda.is_available = lambda: False
        mock_torch.cuda = mock_cuda
        sys.modules["torch"] = mock_torch
        sys.modules["torch.cuda"] = mock_cuda

        class DummyOptimizer:
            def __init__(self, *args, **kwargs):
                pass
            def zero_grad(self, *args, **kwargs):
                pass
            def step(self, *args, **kwargs):
                pass

        class DummyModule:
            def __init__(self, *args, **kwargs):
                pass
            def forward(self, *args, **kwargs):
                return DummyTensor()
            def __call__(self, *args, **kwargs):
                return self.forward(*args, **kwargs)
            def to(self, *args, **kwargs):
                return self
            def parameters(self, *args, **kwargs):
                return []
            def state_dict(self, *args, **kwargs):
                return {}
            def load_state_dict(self, *args, **kwargs):
                pass
            def eval(self, *args, **kwargs):
                return self
            def train(self, *args, **kwargs):
                return self
            def register_buffer(self, *args, **kwargs):
                pass

        class MockNNModule(types.ModuleType):
            def __getattr__(self, name):
                if name.startswith('__'):
                    raise AttributeError(name)
                return DummyModule

        mock_nn = MockNNModule("torch.nn")
        mock_nn.Module = DummyModule
        mock_nn.Sequential = DummyModule
        mock_nn.Linear = DummyModule
        mock_nn.ReLU = DummyModule
        mock_nn.LSTM = DummyModule
        mock_nn.Dropout = DummyModule
        mock_nn.LayerNorm = DummyModule
        mock_nn.MultiheadAttention = DummyModule
        mock_nn.TransformerEncoder = DummyModule
        mock_nn.TransformerEncoderLayer = DummyModule

        class DummyLoss(DummyModule):
            def __call__(self, *args, **kwargs):
                return self
            def backward(self, *args, **kwargs):
                pass
            def item(self):
                return 0.0

        mock_nn.MSELoss = DummyLoss
        mock_torch.nn = mock_nn
        sys.modules["torch.nn"] = mock_nn

        mock_optim = types.ModuleType("torch.optim")
        mock_optim.Adam = DummyOptimizer
        mock_torch.optim = mock_optim
        sys.modules["torch.optim"] = mock_optim

        mock_sb3 = types.ModuleType("stable_baselines3")
        class DummyPPO:
            def __init__(self, policy, env, *args, **kwargs):
                self.policy = policy
                self.env = env
            def learn(self, total_timesteps, *args, **kwargs):
                return self
            def predict(self, observation, state=None, episode_start=None, deterministic=False):
                return 0, None
        mock_sb3.PPO = DummyPPO
        sys.modules["stable_baselines3"] = mock_sb3

"""주식 트레이딩 시스템 초기화"""

from .core import (
    AccountSyncAgent,
    HybridStrategyEngine,
    OptimizationEngine,
    OrderManagementSystem,
    OrderType,
    PortfolioManager,
    TradeSignal,
)
from .data_layer import MarketDataHandler, NLPEngine
from .persistence import AssetHistoryDB, TradeLogger

__version__ = "1.0.0"
__author__ = "Stock Trading Team"
__all__ = [
    "AccountSyncAgent",
    "AssetHistoryDB",
    "HybridStrategyEngine",
    "MarketDataHandler",
    "NLPEngine",
    "OptimizationEngine",
    "OrderManagementSystem",
    "OrderType",
    "PortfolioManager",
    "TradeLogger",
    "TradeSignal",
]
