import logging
import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from typing import cast, Optional, List, Tuple

logger = logging.getLogger(__name__)

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.

DEFAULT_LSTM_FEATURES = ['ret_1d', 'volume_ratio', 'range_pos_20d', 'rsi_14', 'macd_hist_norm', 'mfi_14', 'vix_change', 'usdkrw_change']

class LSTMNetwork(nn.Module):
    """
    Enhanced PyTorch LSTM architecture with LayerNorm and Dropout.
    Takes input of shape (batch_size, sequence_length, input_size)
    Outputs predicted return of shape (batch_size, output_size)
    """

    def __init__(self, input_size: int = 1, hidden_size: int = 64, num_layers: int = 2, dropout: float = 0.2, output_size: int = 1):
        super(LSTMNetwork, self).__init__()
        self.use_layer_norm = True
        self.layer_norm = nn.LayerNorm(input_size)
        self.lstm = nn.LSTM(
            input_size,
            hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        # x: (batch, seq_len, input_size)
        x_norm = self.layer_norm(x) if self.use_layer_norm else x
        out, _ = self.lstm(x_norm)
        # Take the output of the last time step
        last_step_out = out[:, -1, :]
        pred = self.fc(last_step_out)
        return pred


class LSTMPredictor:
    """
    Wrapper class to train and predict using the PyTorch LSTM model.
    """

    def __init__(self, sequence_length: int = 20, input_size: int = 1, hidden_size: int = 64, epochs: int = 25, lr: float = 0.01):
        self.sequence_length = sequence_length
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.epochs = epochs
        self.lr = lr
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = LSTMNetwork(input_size=input_size, hidden_size=hidden_size, num_layers=2, dropout=0.2, output_size=1).to(self.device)
        self.is_trained = False

    @staticmethod
    def prepare_multivariate_sequences(df: pd.DataFrame, target_col: str, seq_len: int = 20, features: Optional[List[str]] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare multivariate sequences for LSTM per stock.
        Each feature is standardized per stock before stacking.
        Handles missing features gracefully by falling back to available ones.
        """
        if features is None:
            features = DEFAULT_LSTM_FEATURES

        if 'symbol' in df.columns:
            groups = df.groupby('symbol')
        else:
            groups = [('ALL', df)]

        X_all, y_all, indices_all = [], [], []

        for sym, group in groups:
            group_sorted = group.sort_values('date') if 'date' in group.columns else group
            if len(group_sorted) < seq_len:
                continue

            # Identify available features
            avail_features = [f for f in features if f in group_sorted.columns]
            if not avail_features:
                if 'ret_1d' in group_sorted.columns:
                    avail_features = ['ret_1d']
                elif 'close' in group_sorted.columns:
                    group_sorted = group_sorted.copy()
                    group_sorted['ret_1d'] = group_sorted['close'].pct_change().fillna(0.0)
                    avail_features = ['ret_1d']
                elif 'Close' in group_sorted.columns:
                    group_sorted = group_sorted.copy()
                    group_sorted['ret_1d'] = group_sorted['Close'].pct_change().fillna(0.0)
                    avail_features = ['ret_1d']
                else:
                    continue

            # Per-stock normalization
            normed_feats = []
            for f in avail_features:
                vals = group_sorted[f].fillna(0.0).values
                std = np.std(vals)
                if std > 1e-6:
                    vals = (vals - np.mean(vals)) / std
                else:
                    vals = vals - np.mean(vals)
                normed_feats.append(vals)

            stacked_feats = np.column_stack(normed_feats)

            target_vals = group_sorted[target_col].values if target_col in group_sorted.columns else np.zeros(len(group_sorted))
            idx_vals = group_sorted.index.values

            for i in range(len(group_sorted) - seq_len + 1):
                X_all.append(stacked_feats[i:i+seq_len])
                y_all.append(target_vals[i+seq_len-1])
                indices_all.append(idx_vals[i+seq_len-1])

        if not X_all:
            return np.array([]), np.array([]), np.array([])

        return np.array(X_all), np.array(y_all), np.array(indices_all)

    def train_model(self, X_train: np.ndarray, y_train: np.ndarray, val_split: float = 0.15, max_grad_norm: float = 1.0, date_labels: Optional[np.ndarray] = None) -> None:
        """
        Trains the LSTM model with gradient clipping, LR scheduling, and early stopping.
        Args:
            X_train: numpy array of shape (n_samples, sequence_length) or (n_samples, sequence_length, 1)
            y_train: numpy array of shape (n_samples,) or (n_samples, 1)
            val_split: fraction of data used for validation/early stopping
            max_grad_norm: maximum gradient norm for clipping
            date_labels: optional date timestamps for date-aware panel split
        """
        if len(X_train) < 5:
            logger.warning(f"Too few samples for training LSTM: {len(X_train)}")
            return

        try:
            # Reshape inputs to (samples, seq_len, input_size)
            if X_train.ndim == 2:
                X_train = np.expand_dims(X_train, axis=-1)
            if y_train.ndim == 1:
                y_train = np.expand_dims(y_train, axis=-1)

            # Auto-adapt input_size for multivariate sequences
            actual_input_size = int(X_train.shape[2])
            if actual_input_size != self.input_size:
                self.input_size = actual_input_size
                self.model = LSTMNetwork(
                    input_size=actual_input_size,
                    hidden_size=self.hidden_size,
                    num_layers=2,
                    dropout=0.2,
                    output_size=1
                ).to(self.device)

            # Clean NaNs and Infs in training data
            X_train = np.nan_to_num(X_train, nan=0.0, posinf=0.0, neginf=0.0)
            y_train = np.nan_to_num(y_train, nan=0.0, posinf=0.0, neginf=0.0)

            # Chronological split for validation if enough samples
            n_total = len(X_train)
            if n_total >= 30 and val_split > 0:
                if date_labels is not None and len(date_labels) == n_total:
                    unique_dates = np.sort(np.unique(date_labels))
                    cutoff_idx = int(len(unique_dates) * (1.0 - val_split))
                    cutoff_date = unique_dates[cutoff_idx]
                    tr_mask = date_labels < cutoff_date
                    val_mask = date_labels >= cutoff_date
                    X_tr, y_tr = X_train[tr_mask], y_train[tr_mask]
                    X_val, y_val = X_train[val_mask], y_train[val_mask]
                else:
                    embargo = max(1, int(n_total * 0.02))
                    n_train = int(n_total * (1.0 - val_split))
                    X_tr, y_tr = X_train[:n_train], y_train[:n_train]
                    X_val, y_val = X_train[n_train + embargo:], y_train[n_train + embargo:]
            else:
                X_tr, y_tr = X_train, y_train
                X_val, y_val = None, None

            # Convert to PyTorch Tensors
            float_dtype = getattr(torch, 'float32', getattr(torch, 'float', None))
            X_tr_tensor = torch.tensor(X_tr, dtype=float_dtype).to(self.device)
            y_tr_tensor = torch.tensor(y_tr, dtype=float_dtype).to(self.device)

            if X_val is not None and len(X_val) > 0:
                X_val_tensor = torch.tensor(X_val, dtype=float_dtype).to(self.device)
                y_val_tensor = torch.tensor(y_val, dtype=float_dtype).to(self.device)
            else:
                X_val_tensor, y_val_tensor = None, None

            criterion = nn.MSELoss()
            optimizer = optim.Adam(self.model.parameters(), lr=self.lr, weight_decay=1e-4)
            scheduler = optim.lr_scheduler.ReduceLROnPlateau(
                optimizer, mode='min', factor=0.5, patience=2, min_lr=1e-5
            )
            cosine_scheduler = optim.lr_scheduler.CosineAnnealingLR(
                optimizer, T_max=self.epochs, eta_min=1e-6
            )

            batch_size = min(64, len(X_tr))
            dataset_size = len(X_tr)
            best_val_loss = float('inf')
            best_state = None
            patience_counter = 0
            max_patience = 4

            for epoch in range(self.epochs):
                self.model.train()
                permutation = torch.randperm(dataset_size)
                epoch_loss = 0.0
                num_batches = 0

                for i in range(0, dataset_size, batch_size):
                    indices = permutation[i : i + batch_size]
                    batch_x, batch_y = X_tr_tensor[indices], y_tr_tensor[indices]

                    optimizer.zero_grad()
                    outputs = self.model(batch_x)
                    loss = criterion(outputs, batch_y)
                    loss.backward()

                    # Gradient clipping to prevent exploding gradients
                    if max_grad_norm > 0:
                        torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=max_grad_norm)

                    optimizer.step()
                    epoch_loss += loss.item()
                    num_batches += 1

                avg_train_loss = epoch_loss / max(num_batches, 1)

                # Validation step
                if X_val_tensor is not None:
                    self.model.eval()
                    with torch.no_grad():
                        val_outputs = self.model(X_val_tensor)
                        val_loss = criterion(val_outputs, y_val_tensor).item()

                    scheduler.step(val_loss)
                    cosine_scheduler.step()
                    if val_loss < best_val_loss:
                        best_val_loss = val_loss
                        best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
                        patience_counter = 0
                    else:
                        patience_counter += 1
                        if patience_counter >= max_patience:
                            logger.debug(f"Early stopping at epoch {epoch+1}")
                            break
                else:
                    scheduler.step(avg_train_loss)
                    cosine_scheduler.step()

            if best_state is not None:
                self.model.load_state_dict({k: v.to(self.device) for k, v in best_state.items()})

            self.is_trained = True
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("LSTM Model trained successfully with gradient clipping and adaptive scheduler.")

        except Exception as e:
            logger.error(f"Error during LSTM training: {e}")
            self.is_trained = False

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predicts expected returns.
        Args:
            X: numpy array of shape (n_samples, sequence_length) or (n_samples, sequence_length, 1)
        """
        if not self.is_trained:
            logger.warning("LSTM Model is not trained. Returning zeros.")
            return np.zeros(len(X))

        try:
            if X.ndim == 2:
                X = np.expand_dims(X, axis=-1)

            self.model.eval()
            with torch.no_grad():
                float_dtype = getattr(torch, 'float32', getattr(torch, 'float', None))
                X_tensor = torch.tensor(X, dtype=float_dtype).to(self.device)
                preds = self.model(X_tensor)
                # Convert back to numpy
                return cast(np.ndarray, preds.cpu().numpy().flatten())
        except Exception as e:
            logger.error(f"Error during LSTM prediction: {e}")
            return np.zeros(len(X))

    def save_model(self, filepath: str) -> None:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            torch.save({
                'model_state_dict': self.model.state_dict(),
                'is_trained': self.is_trained
            }, filepath)
            logger.info(f"LSTM model saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save LSTM model: {e}")

    def load_model(self, filepath: str) -> None:
        try:
            if os.path.exists(filepath):
                checkpoint = torch.load(filepath, map_location=self.device, weights_only=False)  # nosec B614
                if isinstance(checkpoint, dict):
                    if 'model_state_dict' in checkpoint:
                        self.model.load_state_dict(checkpoint['model_state_dict'])
                    elif 'state_dict' in checkpoint:
                        self.model.load_state_dict(checkpoint['state_dict'])
                    else:
                        logger.warning(f"LSTM checkpoint {filepath} has no state dict key (keys: {list(checkpoint.keys())[:6]}). Treating as untrained.")
                        self.is_trained = False
                        return
                    self.is_trained = bool(checkpoint.get('is_trained', True))
                else:
                    # Legacy format: bare state dict
                    self.model.load_state_dict(checkpoint)
                    self.is_trained = True
                logger.info(f"LSTM model loaded from {filepath}")
            else:
                logger.warning(f"LSTM model file not found: {filepath}")
        except Exception as e:
            logger.error(f"Failed to load LSTM model: {e}")
            self.is_trained = False
