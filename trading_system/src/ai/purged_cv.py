import numpy as np
import pandas as pd
import logging
from typing import Generator, Tuple, Optional

logger = logging.getLogger(__name__)

class PurgedKFold:
    """
    Purged K-Fold Cross-Validation with Embargoing (Marcos Lopez de Prado).
    Prevents data leakage and overlap between train and test sets in financial time-series.
    """

    def __init__(self, n_splits: int = 5, pct_embargo: float = 0.01):
        self.n_splits = n_splits
        self.pct_embargo = pct_embargo

    def split(
        self,
        X: pd.DataFrame,
        y: Optional[pd.Series] = None,
        event_times: Optional[pd.Series] = None
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """
        Generates train/test indices with purging and embargoing.

        Args:
            X: Input DataFrame
            y: Optional target series
            event_times: Optional Series where index is start time and value is end time of trade event
        """
        n_samples = len(X)
        indices = np.arange(n_samples)
        embargo = int(n_samples * self.pct_embargo)

        test_bounds = np.linspace(0, n_samples, self.n_splits + 1, dtype=int)

        for i in range(self.n_splits):
            test_start = test_bounds[i]
            test_end = test_bounds[i + 1]
            test_indices = indices[test_start:test_end]

            # Train indices before test set
            train_before = indices[:max(0, test_start)]

            # Train indices after test set (apply embargo)
            train_after_start = min(n_samples, test_end + embargo)
            train_after = indices[train_after_start:]

            train_indices = np.concatenate([train_before, train_after])

            # Event-based purging if event_times is supplied
            if event_times is not None and not event_times.empty:
                test_event_end = event_times.iloc[test_indices].max()
                if pd.notna(test_event_end):
                    # Purge any train samples starting before test event ends
                    train_indices = np.array([
                        idx for idx in train_indices
                        if event_times.index[idx] > test_event_end or idx < test_start
                    ])

            yield train_indices, test_indices
