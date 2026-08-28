# -*- coding: utf-8 -*-
"""
TimeSeriesPatchTransformer: Causal Patch-based Time Series Transformer for Multi-Horizon Return Forecasting.
Integrates Cross-Attention with Macro Indicators and Self-Attention over Temporal Price Patches.
"""

import os
import math
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

logger = logging.getLogger(__name__)


class PositionalEncoding(nn.Module):
    pe: torch.Tensor

    def __init__(self, d_model: int, max_len: int = 500, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, d_model)
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)  # type: ignore[no-any-return]


class TimeSeriesPatchTransformer(nn.Module):
    """
    Patch-based Causal Transformer with Optional Cross-Attention to Macro Indicators.
    """
    def __init__(self,
                 in_features: int = 1,
                 macro_features: int = 4,
                 d_model: int = 64,
                 nhead: int = 4,
                 num_layers: int = 2,
                 dim_feedforward: int = 128,
                 dropout: float = 0.1,
                 horizons: Tuple[int, ...] = (1, 5, 20, 60),
                 patch_size: int = 5,
                 stride: int = 2):
        super().__init__()
        self.in_features = in_features
        self.macro_features = macro_features
        self.d_model = d_model
        self.horizons = horizons
        self.patch_size = patch_size
        self.stride = stride

        # Patch Embedding for stock sequence (e.g. 20-60 timesteps -> patches)
        self.patch_embed = nn.Linear(in_features * patch_size, d_model)
        self.pos_encoder = PositionalEncoding(d_model, max_len=100, dropout=dropout)

        # Macro Embedding
        self.has_macro = macro_features > 0
        if self.has_macro:
            self.macro_embed = nn.Linear(macro_features, d_model)
            self.cross_attn = nn.MultiheadAttention(embed_dim=d_model, num_heads=nhead, dropout=dropout, batch_first=True)
            self.macro_norm = nn.LayerNorm(d_model)

        # Transformer Encoder with causal self-attention
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            activation='gelu'
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.layer_norm = nn.LayerNorm(d_model)

        # Multi-Horizon Prediction Heads
        self.heads = nn.ModuleDict({
            f"h_{h}": nn.Sequential(
                nn.Linear(d_model, 32),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(32, 1)
            ) for h in horizons
        })

    def _generate_patches(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (batch, seq_len, in_features)
        Returns: (batch, num_patches, in_features * patch_size)
        """
        batch_size, seq_len, in_dim = x.shape
        if seq_len < self.patch_size:
            # Pad sequence if shorter than patch_size
            pad_len = self.patch_size - seq_len
            x = torch.cat([x[:, :1, :].repeat(1, pad_len, 1), x], dim=1)
            seq_len = self.patch_size

        patches = []
        for i in range(0, seq_len - self.patch_size + 1, self.stride):
            patch = x[:, i:i + self.patch_size, :].reshape(batch_size, -1)
            patches.append(patch)

        if not patches:
            # Fallback if no full stride
            patches.append(x[:, -self.patch_size:, :].reshape(batch_size, -1))

        # (batch, num_patches, in_features * patch_size)
        return torch.stack(patches, dim=1)

    def forward(self, x: torch.Tensor, macro_x: Optional[torch.Tensor] = None) -> Dict[int, torch.Tensor]:
        """
        x: (batch, seq_len, in_features)
        macro_x: Optional (batch, macro_seq_len, macro_features) or (batch, macro_features)
        """
        patches = self._generate_patches(x)  # (batch, num_patches, patch_dim)
        h = self.patch_embed(patches)        # (batch, num_patches, d_model)
        h = self.pos_encoder(h)

        # Causal mask for temporal patches
        num_patches = h.size(1)
        causal_mask = torch.triu(torch.full((num_patches, num_patches), float('-inf'), device=x.device), diagonal=1)

        encoded = self.transformer_encoder(h, mask=causal_mask)  # (batch, num_patches, d_model)

        # Optional Cross-Attention with Macro indicators
        if self.has_macro and macro_x is not None:
            if macro_x.dim() == 2:
                macro_x = macro_x.unsqueeze(1)  # (batch, 1, macro_dim)
            macro_emb = self.macro_embed(macro_x)  # (batch, macro_seq, d_model)
            cross_out, _ = self.cross_attn(query=encoded, key=macro_emb, value=macro_emb)
            encoded = self.macro_norm(encoded + cross_out)

        encoded = self.layer_norm(encoded)

        # Global average + last-token pooling
        last_rep = encoded[:, -1, :]  # (batch, d_model)
        mean_rep = torch.mean(encoded, dim=1)
        pooled = 0.6 * last_rep + 0.4 * mean_rep

        outputs = {}
        for h_val, head in self.heads.items():
            horizon_int = int(h_val.replace("h_", ""))
            outputs[horizon_int] = head(pooled).squeeze(-1)  # (batch,)

        return outputs


class PatchTransformerPredictor:
    """
    High-level Trainer & Predictor wrapper for TimeSeriesPatchTransformer.
    """
    def __init__(self,
                 horizons: Tuple[int, ...] = (1, 5, 20, 60),
                 seq_len: int = 30,
                 d_model: int = 64,
                 nhead: int = 4,
                 num_layers: int = 2,
                 lr: float = 1e-3,
                 weight_decay: float = 1e-4,
                 batch_size: int = 32,
                 epochs: int = 30,
                 device: Optional[str] = None):
        self.horizons = horizons
        self.seq_len = seq_len
        self.d_model = d_model
        self.nhead = nhead
        self.num_layers = num_layers
        self.lr = lr
        self.weight_decay = weight_decay
        self.batch_size = batch_size
        self.epochs = epochs

        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)

        self.model: Optional[TimeSeriesPatchTransformer] = None
        self.is_fitted = False

    def _init_model(self, in_features: int, macro_features: int):
        self.model = TimeSeriesPatchTransformer(
            in_features=in_features,
            macro_features=macro_features,
            d_model=self.d_model,
            nhead=self.nhead,
            num_layers=self.num_layers,
            horizons=self.horizons
        ).to(self.device)

    def train(self,
              X: np.ndarray,
              y_dict: Dict[int, np.ndarray],
              macro_X: Optional[np.ndarray] = None,
              val_split: float = 0.15) -> Dict[str, List[float]]:
        """
        X: (N, seq_len, in_features)
        y_dict: {horizon: (N,)} expected returns
        macro_X: Optional (N, macro_features)
        """
        N, seq_len, in_features = X.shape
        macro_dim = macro_X.shape[1] if macro_X is not None else 0

        self._init_model(in_features, macro_dim)
        assert self.model is not None

        # Convert to Tensors
        X_tensor = torch.tensor(X, dtype=torch.float32)
        y_tensors = {h: torch.tensor(y_dict[h], dtype=torch.float32) for h in self.horizons if h in y_dict}
        macro_tensor = torch.tensor(macro_X, dtype=torch.float32) if macro_X is not None else None

        # Train / Val Split (Chronological)
        split_idx = int(N * (1.0 - val_split))
        if split_idx < 10:
            split_idx = max(1, N - 5)

        train_X, val_X = X_tensor[:split_idx], X_tensor[split_idx:]
        train_y = {h: y_tensors[h][:split_idx] for h in y_tensors}
        val_y = {h: y_tensors[h][split_idx:] for h in y_tensors}

        train_macro = macro_tensor[:split_idx] if macro_tensor is not None else None
        val_macro = macro_tensor[split_idx:] if macro_tensor is not None else None

        optimizer = optim.AdamW(self.model.parameters(), lr=self.lr, weight_decay=self.weight_decay)
        criterion = nn.HuberLoss(delta=1.0)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5)

        history: Dict[str, List[float]] = {'train_loss': [], 'val_loss': []}
        best_val_loss = float('inf')
        best_state = None

        self.model.train()
        for epoch in range(self.epochs):
            # Mini-batch loop
            permutation = torch.randperm(train_X.size(0))
            epoch_train_loss = 0.0
            num_batches = 0

            for i in range(0, train_X.size(0), self.batch_size):
                indices = permutation[i:i + self.batch_size]
                bx = train_X[indices].to(self.device)
                b_macro = train_macro[indices].to(self.device) if train_macro is not None else None

                optimizer.zero_grad()
                outputs = self.model(bx, b_macro)

                loss = torch.tensor(0.0, device=self.device)
                for h, target in train_y.items():
                    by = target[indices].to(self.device)
                    # Mask NaNs in target
                    valid_mask = torch.isfinite(by)
                    if valid_mask.sum() > 0:
                        loss = loss + criterion(outputs[h][valid_mask], by[valid_mask])

                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                optimizer.step()

                epoch_train_loss += loss.item()
                num_batches += 1

            avg_train_loss = epoch_train_loss / max(num_batches, 1)

            # Validation
            self.model.eval()
            with torch.no_grad():
                val_loss = 0.0
                if val_X.size(0) > 0:
                    vx = val_X.to(self.device)
                    v_macro = val_macro.to(self.device) if val_macro is not None else None
                    v_outputs = self.model(vx, v_macro)

                    for h, target in val_y.items():
                        vy = target.to(self.device)
                        valid_mask = torch.isfinite(vy)
                        if valid_mask.sum() > 0:
                            val_loss += criterion(v_outputs[h][valid_mask], vy[valid_mask]).item()
                else:
                    val_loss = avg_train_loss

            scheduler.step(val_loss)
            history['train_loss'].append(avg_train_loss)
            history['val_loss'].append(val_loss)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {k: v.cpu() for k, v in self.model.state_dict().items()}

            self.model.train()

        if best_state is not None:
            self.model.load_state_dict(best_state)

        self.is_fitted = True
        logger.info(f"[PatchTransformer] Training complete. Best Val Huber Loss: {best_val_loss:.4f}")
        return history

    def predict(self,
                X: np.ndarray,
                macro_X: Optional[np.ndarray] = None) -> Dict[int, np.ndarray]:
        """
        X: (N, seq_len, in_features)
        Returns {horizon: (N,) predictions in % or decimal}
        """
        if not self.is_fitted or self.model is None:
            logger.warning("[PatchTransformer] Model is not fitted. Returning zeros.")
            N = X.shape[0]
            return {h: np.zeros(N, dtype=np.float32) for h in self.horizons}

        self.model.eval()
        with torch.no_grad():
            x_tensor = torch.tensor(X, dtype=torch.float32).to(self.device)
            m_tensor = torch.tensor(macro_X, dtype=torch.float32).to(self.device) if macro_X is not None else None
            outputs = self.model(x_tensor, m_tensor)

            res = {}
            for h, pred_tensor in outputs.items():
                res[h] = pred_tensor.cpu().numpy()
            return res

    def save(self, filepath: str):
        if self.model is None:
            return
        state = {
            'model_state': self.model.state_dict(),
            'horizons': self.horizons,
            'seq_len': self.seq_len,
            'd_model': self.d_model,
            'nhead': self.nhead,
            'num_layers': self.num_layers,
            'in_features': self.model.in_features,
            'macro_features': self.model.macro_features,
            'is_fitted': self.is_fitted
        }
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        torch.save(state, filepath)
        logger.info(f"[PatchTransformer] Model saved to {filepath}")

    def load(self, filepath: str):
        if not os.path.exists(filepath):
            logger.warning(f"[PatchTransformer] Model file not found: {filepath}")
            return False
        state = torch.load(filepath, map_location=self.device)
        self.horizons = state['horizons']
        self.seq_len = state['seq_len']
        self.d_model = state['d_model']
        self.nhead = state['nhead']
        self.num_layers = state['num_layers']
        self.is_fitted = state.get('is_fitted', True)

        self._init_model(state['in_features'], state['macro_features'])
        assert self.model is not None
        self.model.load_state_dict(state['model_state'])
        self.model.eval()
        logger.info(f"[PatchTransformer] Model loaded from {filepath}")
        return True
