"""Multi-Horizon Continuous Sequence Forecaster (Feature F541)

Implements continuous multi-horizon returns forecasting across 1D, 5D, 20D, and 60D horizons
with epistemic & aleatoric uncertainty quantile intervals (P10, P50, P90), pinball loss,
and conformal prediction intervals for non-stationary market dynamics.
Supports seamless integration with Mamba SSM representations and pure NumPy CPU fallback.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    F = None
    TORCH_AVAILABLE = False


@dataclass
class MultiHorizonForecastOutput:
    """Structured output container for multi-horizon quantile predictions."""

    horizons: Tuple[int, ...]
    quantiles: Tuple[float, ...] = (0.1, 0.5, 0.9)
    # Mapping horizon (int) -> Dict[str, np.ndarray] with keys: 'p10', 'p50', 'p90', 'aleatoric_std', 'epistemic_std'
    predictions: Dict[int, Dict[str, np.ndarray]] = field(default_factory=dict)
    conformal_intervals: Dict[int, Dict[str, np.ndarray]] = field(default_factory=dict)
    summary_metrics: Dict[str, float] = field(default_factory=dict)


class ConformalQuantileCalibrator:
    """Conformal prediction calibrator for coverage guarantees on non-stationary financial series."""

    def __init__(self, target_coverage: float = 0.80) -> None:
        """Target coverage 0.80 corresponds to symmetric 10% lower & 10% upper tails (P10 to P90)."""
        self.target_coverage = target_coverage
        self.alpha = 1.0 - target_coverage
        self.q_hat: Dict[int, float] = {}

    def fit(
        self,
        val_predictions: Dict[int, Dict[str, np.ndarray]],
        val_targets: Dict[int, np.ndarray],
    ) -> Dict[int, float]:
        """Compute conformal conformity correction factor q_hat per horizon using split-conformal quantile calibration."""
        for h, preds in val_predictions.items():
            if h not in val_targets:
                continue
            y = val_targets[h]
            y_lower = preds["p10"]
            y_upper = preds["p90"]

            # Nonconformity score E_i = max(y_lower - y, y - y_upper)
            nonconformity = np.maximum(y_lower - y, y - y_upper)
            n = len(nonconformity)
            if n == 0:
                self.q_hat[h] = 0.0
                continue

            # Finite-sample (1 - alpha) * (1 + 1/n) empirical quantile
            p_level = min(1.0, math.ceil((n + 1) * (1.0 - self.alpha)) / n)
            q_val = float(np.quantile(nonconformity, p_level, method="higher" if hasattr(np, "quantile") else "nearest"))
            self.q_hat[h] = max(0.0, q_val)
        return self.q_hat

    def calibrate(
        self, raw_predictions: Dict[int, Dict[str, np.ndarray]]
    ) -> Dict[int, Dict[str, np.ndarray]]:
        """Apply conformal correction to raw P10/P90 quantile intervals."""
        calibrated: Dict[int, Dict[str, np.ndarray]] = {}
        for h, preds in raw_predictions.items():
            q_offset = self.q_hat.get(h, 0.0)
            calibrated[h] = {
                "p10": preds["p10"] - q_offset,
                "p50": preds["p50"].copy(),
                "p90": preds["p90"] + q_offset,
                "aleatoric_std": np.maximum(1e-6, (preds["p90"] - preds["p10"] + 2.0 * q_offset) / 2.5631),
                "epistemic_std": preds.get("epistemic_std", np.zeros_like(preds["p50"])),
            }
        return calibrated


if TORCH_AVAILABLE:

    class _PyTorchMultiHorizonHead(nn.Module):
        """PyTorch Multi-Horizon Quantile MLP Regression Head."""

        def __init__(
            self,
            d_model: int = 128,
            hidden_dim: int = 256,
            horizons: Tuple[int, ...] = (1, 5, 20, 60),
            quantiles: Tuple[float, ...] = (0.1, 0.5, 0.9),
            dropout: float = 0.1,
        ) -> None:
            super().__init__()
            self.d_model = d_model
            self.horizons = horizons
            self.quantiles = quantiles
            self.dropout_rate = dropout

            self.shared_trunk = nn.Sequential(
                nn.Linear(d_model, hidden_dim),
                nn.LayerNorm(hidden_dim),
                nn.SiLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim, hidden_dim // 2),
                nn.SiLU(),
            )

            # Per-horizon specialized quantile prediction branches
            self.heads = nn.ModuleDict()
            for h in horizons:
                self.heads[str(h)] = nn.Linear(hidden_dim // 2, len(quantiles))

        def forward(self, x: torch.Tensor) -> Dict[int, torch.Tensor]:
            """Forward pass through shared trunk and horizon-specific heads.

            Args:
                x: Tensor of shape (batch, d_model) representing sequence embedding.

            Returns:
                Dict mapping horizon -> (batch, num_quantiles)
            """
            feat = self.shared_trunk(x)
            outputs = {}
            for h in self.horizons:
                outputs[h] = self.heads[str(h)](feat)
            return outputs


class MultiHorizonSequenceForecaster:
    """Production Multi-Horizon Continuous Sequence Forecaster with Uncertainty Bounds (F541).

    Estimates asset price return distributions over multiple forward trading horizons
    (1D, 5D, 20D, 60D) while quantifying aleatoric (data noise) and epistemic (model) uncertainty.
    """

    def __init__(
        self,
        d_model: int = 128,
        hidden_dim: int = 256,
        horizons: Tuple[int, ...] = (1, 5, 20, 60),
        quantiles: Tuple[float, ...] = (0.1, 0.5, 0.9),
        dropout: float = 0.1,
        target_coverage: float = 0.80,
        use_torch: bool = True,
        seed: int = 42,
    ) -> None:
        self.d_model = d_model
        self.hidden_dim = hidden_dim
        self.horizons = horizons
        self.quantiles = quantiles
        self.dropout = dropout
        self.target_coverage = target_coverage
        self.rng = np.random.default_rng(seed)
        self.calibrator = ConformalQuantileCalibrator(target_coverage=target_coverage)

        self._use_torch = bool(use_torch and TORCH_AVAILABLE)
        if self._use_torch:
            torch.manual_seed(seed)
            self._model = _PyTorchMultiHorizonHead(
                d_model=d_model,
                hidden_dim=hidden_dim,
                horizons=horizons,
                quantiles=quantiles,
                dropout=dropout,
            )
            self._model.eval()
        else:
            self._model = None
            self._init_numpy_weights()

    def _init_numpy_weights(self) -> None:
        """Initialize lightweight NumPy feedforward weights for SIMD/CPU inference."""
        scale1 = math.sqrt(2.0 / (self.d_model + self.hidden_dim))
        self._w1 = self.rng.normal(0.0, scale1, (self.d_model, self.hidden_dim)).astype(np.float32)
        self._b1 = np.zeros(self.hidden_dim, dtype=np.float32)

        h_half = self.hidden_dim // 2
        scale2 = math.sqrt(2.0 / (self.hidden_dim + h_half))
        self._w2 = self.rng.normal(0.0, scale2, (self.hidden_dim, h_half)).astype(np.float32)
        self._b2 = np.zeros(h_half, dtype=np.float32)

        self._w_heads: Dict[int, np.ndarray] = {}
        self._b_heads: Dict[int, np.ndarray] = {}
        for h in self.horizons:
            scale_h = math.sqrt(2.0 / (h_half + len(self.quantiles)))
            # Initialize with small positive slope for horizons
            w = self.rng.normal(0.0, scale_h, (h_half, len(self.quantiles))).astype(np.float32)
            # Default bias offsets for quantiles P10, P50, P90
            b = np.array([-0.015 * math.sqrt(h), 0.002 * h, 0.018 * math.sqrt(h)], dtype=np.float32)
            self._w_heads[h] = w
            self._b_heads[h] = b

    def _silu(self, x: np.ndarray) -> np.ndarray:
        return x / (1.0 + np.exp(-np.clip(x, -20.0, 20.0)))

    def _numpy_forward(
        self, x: np.ndarray, mc_dropout: bool = False
    ) -> Dict[int, np.ndarray]:
        """Pure NumPy vectorized forward pass."""
        if x.ndim == 1:
            x = x.reshape(1, -1)
        z1 = np.dot(x, self._w1) + self._b1
        a1 = self._silu(z1)
        if mc_dropout and self.dropout > 0:
            mask = self.rng.binomial(1, 1.0 - self.dropout, size=a1.shape) / (1.0 - self.dropout)
            a1 = a1 * mask
        z2 = np.dot(a1, self._w2) + self._b2
        a2 = self._silu(z2)

        out = {}
        for h in self.horizons:
            raw = np.dot(a2, self._w_heads[h]) + self._b_heads[h]
            # Ensure quantile monotonicity: P10 <= P50 <= P90
            sorted_quantiles = np.sort(raw, axis=-1)
            out[h] = sorted_quantiles
        return out

    def predict(
        self,
        embeddings: Union[np.ndarray, "torch.Tensor"],
        mc_passes: int = 5,
        apply_conformal: bool = True,
    ) -> MultiHorizonForecastOutput:
        """Generate multi-horizon forecasts with aleatoric and epistemic uncertainties.

        Args:
            embeddings: Sequence embeddings of shape (batch, d_model) or (batch, seq_len, d_model).
            mc_passes: Number of Monte Carlo stochastic passes for epistemic uncertainty.
            apply_conformal: Whether to apply fitted conformal calibration bounds.

        Returns:
            MultiHorizonForecastOutput container.
        """
        # Pool temporal sequence if shape is 3D (B, L, D) -> Take last token or mean pool
        if isinstance(embeddings, np.ndarray):
            if embeddings.ndim == 3:
                x_np = embeddings[:, -1, :].astype(np.float32)
            else:
                x_np = embeddings.astype(np.float32)
        else:
            if embeddings.ndim == 3:
                x_tensor = embeddings[:, -1, :].float()
            else:
                x_tensor = embeddings.float()
            x_np = x_tensor.detach().cpu().numpy()

        raw_preds: Dict[int, Dict[str, np.ndarray]] = {}

        if self._use_torch and TORCH_AVAILABLE:
            x_t = torch.from_numpy(x_np)
            # MC passes with train mode active for dropout
            if mc_passes > 1:
                self._model.train()
                samples = {h: [] for h in self.horizons}
                with torch.no_grad():
                    for _ in range(mc_passes):
                        out_dict = self._model(x_t)
                        for h in self.horizons:
                            samples[h].append(out_dict[h].detach().cpu().numpy())
                self._model.eval()

                for h in self.horizons:
                    arr = np.stack(samples[h], axis=0)  # (mc_passes, B, 3)
                    arr_sorted = np.sort(arr, axis=-1)  # enforce monotonicity
                    mean_quantiles = np.mean(arr_sorted, axis=0)  # (B, 3)
                    p10 = mean_quantiles[:, 0]
                    p50 = mean_quantiles[:, 1]
                    p90 = mean_quantiles[:, 2]
                    epistemic = np.std(arr_sorted[:, :, 1], axis=0)  # uncertainty of median
                    aleatoric = np.maximum(1e-6, (p90 - p10) / 2.5631)
                    raw_preds[h] = {
                        "p10": p10,
                        "p50": p50,
                        "p90": p90,
                        "aleatoric_std": aleatoric,
                        "epistemic_std": epistemic,
                    }
            else:
                self._model.eval()
                with torch.no_grad():
                    out_dict = self._model(x_t)
                for h in self.horizons:
                    q = np.sort(out_dict[h].detach().cpu().numpy(), axis=-1)
                    p10, p50, p90 = q[:, 0], q[:, 1], q[:, 2]
                    raw_preds[h] = {
                        "p10": p10,
                        "p50": p50,
                        "p90": p90,
                        "aleatoric_std": np.maximum(1e-6, (p90 - p10) / 2.5631),
                        "epistemic_std": np.zeros_like(p50),
                    }
        else:
            # Pure NumPy branch
            if mc_passes > 1:
                samples = {h: [] for h in self.horizons}
                for _ in range(mc_passes):
                    out_dict = self._numpy_forward(x_np, mc_dropout=True)
                    for h in self.horizons:
                        samples[h].append(out_dict[h])
                for h in self.horizons:
                    arr = np.stack(samples[h], axis=0)  # (mc_passes, B, 3)
                    mean_quantiles = np.mean(arr, axis=0)
                    p10 = mean_quantiles[:, 0]
                    p50 = mean_quantiles[:, 1]
                    p90 = mean_quantiles[:, 2]
                    epistemic = np.std(arr[:, :, 1], axis=0)
                    aleatoric = np.maximum(1e-6, (p90 - p10) / 2.5631)
                    raw_preds[h] = {
                        "p10": p10,
                        "p50": p50,
                        "p90": p90,
                        "aleatoric_std": aleatoric,
                        "epistemic_std": epistemic,
                    }
            else:
                out_dict = self._numpy_forward(x_np, mc_dropout=False)
                for h in self.horizons:
                    q = out_dict[h]
                    p10, p50, p90 = q[:, 0], q[:, 1], q[:, 2]
                    raw_preds[h] = {
                        "p10": p10,
                        "p50": p50,
                        "p90": p90,
                        "aleatoric_std": np.maximum(1e-6, (p90 - p10) / 2.5631),
                        "epistemic_std": np.zeros_like(p50),
                    }

        conformal_preds = self.calibrator.calibrate(raw_preds) if apply_conformal else raw_preds

        # Compute summary metrics
        summary = {
            "mean_1d_return": float(np.mean(raw_preds[1]["p50"])),
            "mean_5d_return": float(np.mean(raw_preds[5]["p50"])) if 5 in raw_preds else 0.0,
            "mean_20d_return": float(np.mean(raw_preds[20]["p50"])) if 20 in raw_preds else 0.0,
            "mean_60d_return": float(np.mean(raw_preds[60]["p50"])) if 60 in raw_preds else 0.0,
            "mean_uncertainty_spread_1d": float(np.mean(raw_preds[1]["p90"] - raw_preds[1]["p10"])),
        }

        return MultiHorizonForecastOutput(
            horizons=self.horizons,
            quantiles=self.quantiles,
            predictions=raw_preds,
            conformal_intervals=conformal_preds,
            summary_metrics=summary,
        )

    def compute_pinball_loss(
        self,
        predictions: Dict[int, np.ndarray],
        targets: Dict[int, np.ndarray],
    ) -> Dict[int, float]:
        """Compute pinball / quantile loss for calibration evaluation."""
        losses: Dict[int, float] = {}
        for h in self.horizons:
            if h not in predictions or h not in targets:
                continue
            pred_q = predictions[h]  # (B, 3)
            y = targets[h].reshape(-1, 1)  # (B, 1)
            diff = y - pred_q
            h_loss = 0.0
            for i, tau in enumerate(self.quantiles):
                d = diff[:, i]
                loss_tau = np.maximum(tau * d, (tau - 1.0) * d)
                h_loss += float(np.mean(loss_tau))
            losses[h] = h_loss / len(self.quantiles)
        return losses

    def calibrate_conformal(
        self,
        val_embeddings: np.ndarray,
        val_targets: Dict[int, np.ndarray],
    ) -> Dict[int, float]:
        """Calibrate prediction intervals against a validation dataset."""
        forecast = self.predict(val_embeddings, mc_passes=1, apply_conformal=False)
        return self.calibrator.fit(forecast.predictions, val_targets)


def create_multi_horizon_forecaster(
    d_model: int = 128,
    horizons: Tuple[int, ...] = (1, 5, 20, 60),
    use_torch: bool = True,
    seed: int = 42,
) -> MultiHorizonSequenceForecaster:
    """Factory helper function for MultiHorizonSequenceForecaster."""
    return MultiHorizonSequenceForecaster(
        d_model=d_model,
        horizons=horizons,
        use_torch=use_torch,
        seed=seed,
    )
