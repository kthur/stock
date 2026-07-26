import logging
import os
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from typing import cast

logger = logging.getLogger(__name__)

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


class LSTMNetwork(nn.Module):
    """
    Standard PyTorch LSTM architecture.
    Takes input of shape (batch_size, sequence_length, input_size)
    Outputs predicted return of shape (batch_size, output_size)
    """

    def __init__(self, input_size: int = 1, hidden_size: int = 32, num_layers: int = 1, output_size: int = 1):
        super(LSTMNetwork, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        # x: (batch, seq_len, input_size)
        out, _ = self.lstm(x)
        # Take the output of the last time step
        last_step_out = out[:, -1, :]
        pred = self.fc(last_step_out)
        return pred


class LSTMPredictor:
    """
    Wrapper class to train and predict using the PyTorch LSTM model.
    """

    def __init__(self, sequence_length: int = 20, input_size: int = 1, hidden_size: int = 32, epochs: int = 5, lr: float = 0.01):
        self.sequence_length = sequence_length
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.epochs = epochs
        self.lr = lr
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = LSTMNetwork(input_size=input_size, hidden_size=hidden_size, num_layers=1, output_size=1).to(self.device)
        self.is_trained = False

    def train_model(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        """
        Trains the LSTM model.
        Args:
            X_train: numpy array of shape (n_samples, sequence_length) or (n_samples, sequence_length, 1)
            y_train: numpy array of shape (n_samples,) or (n_samples, 1)
        """
        if len(X_train) < 5:
            logger.warning(f"Too few samples for training LSTM: {len(X_train)}")
            return

        try:
            # Reshape inputs to (samples, seq_len, 1)
            if X_train.ndim == 2:
                X_train = np.expand_dims(X_train, axis=-1)
            if y_train.ndim == 1:
                y_train = np.expand_dims(y_train, axis=-1)

            # Convert to PyTorch Tensors
            X_tensor = torch.tensor(X_train, dtype=torch.float32).to(self.device)
            y_tensor = torch.tensor(y_train, dtype=torch.float32).to(self.device)

            criterion = nn.MSELoss()
            optimizer = optim.Adam(self.model.parameters(), lr=self.lr)

            self.model.train()
            batch_size = min(64, len(X_train))
            dataset_size = len(X_train)

            for epoch in range(self.epochs):
                # Simple shuffle and batching
                permutation = torch.randperm(dataset_size)
                epoch_loss = 0.0
                num_batches = 0

                for i in range(0, dataset_size, batch_size):
                    indices = permutation[i:i+batch_size]
                    batch_x, batch_y = X_tensor[indices], y_tensor[indices]

                    optimizer.zero_grad()
                    outputs = self.model(batch_x)
                    loss = criterion(outputs, batch_y)
                    loss.backward()
                    optimizer.step()

                    epoch_loss += loss.item()
                    num_batches += 1

                logger.debug(f"LSTM Epoch {epoch+1}/{self.epochs} - Loss: {epoch_loss / max(num_batches, 1):.6f}")

            self.is_trained = True
            logger.info("LSTM Model trained successfully.")

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
                X_tensor = torch.tensor(X, dtype=torch.float32).to(self.device)
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
                checkpoint = torch.load(filepath, map_location=self.device, weights_only=True)
                self.model.load_state_dict(checkpoint['model_state_dict'])
                self.is_trained = checkpoint['is_trained']
                logger.info(f"LSTM model loaded from {filepath}")
            else:
                logger.warning(f"LSTM model file not found: {filepath}")
        except Exception as e:
            logger.error(f"Failed to load LSTM model: {e}")
            self.is_trained = False
