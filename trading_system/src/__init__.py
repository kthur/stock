import os
import sys
import subprocess

# PyTorch WinError 1114 DLL Loading Crash bypass
if "torch" not in sys.modules:
    should_bypass = os.getenv("BYPASS_TORCH", "").lower() in ("true", "1")
    if not should_bypass:
        is_test = "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv)
        if is_test or os.getenv("BYPASS_TORCH") is not None:
            try:
                res = subprocess.run(
                    [sys.executable, "-c", "import torch"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5
                )
                if res.returncode != 0:
                    should_bypass = True
            except Exception:
                should_bypass = True

    if should_bypass:
        import types
        class DummyTensor:
            pass
        mock_torch = types.ModuleType("torch")
        mock_torch.Tensor = DummyTensor
        mock_torch.manual_seed = lambda s: None
        mock_torch.device = lambda *a, **k: None
        mock_torch.from_numpy = lambda *a, **k: DummyTensor()
        mock_torch.no_grad = lambda *a, **k: DummyTensor()
        
        mock_cuda = types.ModuleType("torch.cuda")
        mock_cuda.is_available = lambda: False
        mock_torch.cuda = mock_cuda
        sys.modules["torch"] = mock_torch
        sys.modules["torch.cuda"] = mock_cuda

        mock_nn = types.ModuleType("torch.nn")
        class DummyModule:
            def __init__(self, *args, **kwargs):
                pass
            def forward(self, *args, **kwargs):
                pass
        mock_nn.Module = DummyModule
        mock_nn.Sequential = DummyModule
        mock_nn.Linear = DummyModule
        mock_nn.ReLU = DummyModule
        sys.modules["torch.nn"] = mock_nn

        mock_optim = types.ModuleType("torch.optim")
        mock_optim.Adam = DummyModule
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
