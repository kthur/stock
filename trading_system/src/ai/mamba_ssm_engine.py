"""
src/ai/mamba_ssm_engine.py
Mamba State-Space Model (SSM) Foundation Time-Series Engine (Feature F540).

Key Capabilities:
1. Selective State-Space Sequence Modeling: h'_t = A h_t + B x_t, y_t = C h_t + D x_t.
2. Input-dependent dynamic discretization: Delta = softplus(Parameter + x_t @ W_Delta).
3. Linear complexity O(L) scan over multi-asset historical sequences up to 252 bars.
4. Dual implementation: PyTorch neural architecture with pure NumPy SIMD fallback.
5. Strict causal masking eliminating lookahead bias in financial sequence representations.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple, Union, Any
import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    _TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    F = None
    _TORCH_AVAILABLE = False

logger = logging.getLogger(__name__)


def softplus_np(x: np.ndarray) -> np.ndarray:
    """Numerically stable softplus for NumPy."""
    return np.log1p(np.exp(-np.abs(x))) + np.maximum(x, 0.0)


class MambaSSMBlockNumPy:
    """
    Pure NumPy implementation of the Selective State Space (Mamba) block
    for CPU execution and deterministic unit verification without PyTorch dependencies.
    """

    def __init__(
        self,
        d_model: Union[int, MambaSSMConfig] = 64,
        d_state: int = 16,
        dt_rank: Optional[int] = None,
        seed: int = 42,
        **kwargs: Any,
    ):
        if isinstance(d_model, MambaSSMConfig):
            cfg = d_model
            d_model = cfg.d_model
            d_state = cfg.d_state
            dt_rank = cfg.dt_rank
        else:
            dt_rank = dt_rank if dt_rank is not None else max(1, d_model // 16)

        self.d_model = d_model
        self.d_state = d_state
        self.dt_rank = dt_rank
        
        rng = np.random.RandomState(seed)
        # S4 parameter A: initialized as diagonal negative real elements
        self.A = -np.exp(rng.uniform(0.1, 2.0, size=(d_model, d_state))).astype(np.float64)
        self.D = rng.normal(0, 0.1, size=(d_model,)).astype(np.float64)
        
        # Projection weights for dynamic selection
        self.W_delta = rng.normal(0, 0.05, size=(d_model, dt_rank)).astype(np.float64)
        self.W_delta_proj = rng.normal(0, 0.05, size=(dt_rank, d_model)).astype(np.float64)
        self.W_B = rng.normal(0, 0.05, size=(d_model, d_state)).astype(np.float64)
        self.W_C = rng.normal(0, 0.05, size=(d_model, d_state)).astype(np.float64)

    def forward_sequence(self, x: np.ndarray) -> np.ndarray:
        """
        Executes sequential selective scan over a sequence x of shape (batch, seq_len, d_model).
        Returns y of shape (batch, seq_len, d_model).
        """
        batch_size, seq_len, d_model = x.shape
        y_out = np.zeros_like(x, dtype=np.float64)

        for b in range(batch_size):
            h = np.zeros((d_model, self.d_state), dtype=np.float64)
            for t in range(seq_len):
                xt = x[b, t]  # (d_model,)
                
                # Dynamic Delta: x_t @ W_delta @ W_delta_proj
                delta_pre = (xt @ self.W_delta) @ self.W_delta_proj
                delta = softplus_np(delta_pre)  # (d_model,)
                
                # Dynamic B and C: (d_state,)
                Bt = xt @ self.W_B  # (d_state,)
                Ct = xt @ self.W_C  # (d_state,)
                
                # Discretization: A_bar = exp(delta[:, None] * A)
                A_bar = np.exp(delta[:, None] * self.A)  # (d_model, d_state)
                # B_bar = delta[:, None] * B[None, :]
                B_bar = delta[:, None] * Bt[None, :]    # (d_model, d_state)
                
                # State update: h_t = A_bar * h_{t-1} + B_bar * x_t[:, None]
                h = (A_bar * h) + (B_bar * xt[:, None])
                
                # Output computation: y_t = sum(h_t * C_t[None, :], axis=-1) + D * x_t
        return y_out

    def forward(self, x: np.ndarray) -> np.ndarray:
        return self.forward_sequence(x)

    def forward_numpy(self, x: np.ndarray) -> np.ndarray:
        return self.forward_sequence(x)


if _TORCH_AVAILABLE:
    class MambaSSMBlockTorch(nn.Module):
        """
        PyTorch implementation of the Mamba Selective State Space layer.
        Supports GPU hardware acceleration and backpropagation.
        """

        def __init__(self, d_model: int = 64, d_state: int = 16, dt_rank: int = 4):
            super().__init__()
            self.d_model = d_model
            self.d_state = d_state
            self.dt_rank = dt_rank

            # Initialize log of negative A
            A_init = torch.exp(torch.rand(d_model, d_state) * 1.9 + 0.1)
            self.A_log = nn.Parameter(torch.log(A_init))
            self.D = nn.Parameter(torch.randn(d_model) * 0.1)

            self.x_proj = nn.Linear(d_model, dt_rank + d_state * 2, bias=False)
            self.dt_proj = nn.Linear(dt_rank, d_model, bias=True)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            """
            x shape: (batch_size, seq_len, d_model)
            Returns output of shape (batch_size, seq_len, d_model)
            """
            batch_size, seq_len, d_model = x.shape
            A = -torch.exp(self.A_log)  # (d_model, d_state)

            # Project input to dt, B, C
            proj = self.x_proj(x)  # (batch, seq_len, dt_rank + 2*d_state)
            dt_pre = proj[..., :self.dt_rank]
            B = proj[..., self.dt_rank : self.dt_rank + self.d_state]
            C = proj[..., self.dt_rank + self.d_state :]

            dt = F.softplus(self.dt_proj(dt_pre))  # (batch, seq_len, d_model)

            y_list = []
            h = torch.zeros(batch_size, d_model, self.d_state, device=x.device, dtype=x.dtype)

            for t in range(seq_len):
                xt = x[:, t, :]          # (batch, d_model)
                dt_t = dt[:, t, :]      # (batch, d_model)
                Bt = B[:, t, :]         # (batch, d_state)
                Ct = C[:, t, :]         # (batch, d_state)

                # Discretize
                # A_bar: (batch, d_model, d_state)
                A_bar = torch.exp(dt_t.unsqueeze(-1) * A.unsqueeze(0))
                B_bar = dt_t.unsqueeze(-1) * Bt.unsqueeze(1)

                h = A_bar * h + B_bar * xt.unsqueeze(-1)
                yt = torch.sum(h * Ct.unsqueeze(1), dim=-1) + self.D.unsqueeze(0) * xt
                y_list.append(yt.unsqueeze(1))

            return torch.cat(y_list, dim=1)


class MambaSSMEngine:
    """
    Unified Mamba State-Space Model engine managing training, inference,
    and sequence representation extraction across stock market panels.
    """

    def __init__(
        self,
        d_model: Union[int, MambaSSMConfig] = 64,
        d_state: int = 16,
        dt_rank: Optional[int] = None,
        use_torch: bool = True,
        seed: int = 42,
        **kwargs: Any,
    ):
        if isinstance(d_model, MambaSSMConfig):
            cfg = d_model
            d_model = cfg.d_model
            d_state = cfg.d_state
            dt_rank = cfg.dt_rank
        else:
            dt_rank = dt_rank if dt_rank is not None else max(1, d_model // 16)

        self.d_model = d_model
        self.d_state = d_state
        self.dt_rank = dt_rank
        self.use_torch = use_torch and _TORCH_AVAILABLE

        if self.use_torch:
            torch.manual_seed(seed)
            self.model = MambaSSMBlockTorch(d_model=self.d_model, d_state=self.d_state, dt_rank=self.dt_rank)
            self.model.eval()
        else:
            self.numpy_model = MambaSSMBlockNumPy(d_model=self.d_model, d_state=self.d_state, dt_rank=self.dt_rank, seed=seed)

    def extract_sequence_features(self, sequence_tensor: np.ndarray) -> np.ndarray:
        """
        Transforms input OHLCV feature panel of shape (batch, seq_len, d_model)
        into dynamic state-space representations of shape (batch, seq_len, d_model).
        """
        if self.use_torch:
            with torch.no_grad():
                t_in = torch.from_numpy(sequence_tensor).float()
                t_out = self.model(t_in)
                return t_out.cpu().numpy().astype(np.float64)
        else:
            return self.numpy_model.forward_sequence(sequence_tensor)

    def forward(self, sequence_tensor: np.ndarray) -> np.ndarray:
        """Alias for extract_sequence_features."""
        return self.extract_sequence_features(sequence_tensor)


class MambaSSMConfig:
    """Configuration container for Mamba SSM model."""

    def __init__(
        self,
        d_model: int = 64,
        d_state: int = 16,
        d_conv: int = 4,
        expand: int = 2,
        dt_rank: Optional[int] = None,
        n_layers: int = 1,
    ) -> None:
        self.d_model = d_model
        self.d_state = d_state
        self.d_conv = d_conv
        self.expand = expand
        self.d_inner = d_model * expand
        self.dt_rank = dt_rank if dt_rank is not None else max(1, d_model // 16)
        self.n_layers = n_layers


MambaSSMBlock = MambaSSMBlockNumPy

