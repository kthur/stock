"""Base Abstract Strategy Engine definition for Stock Trading System."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import pandas as pd


class BaseStrategyEngine(ABC):
    """Abstract Base Class for all multi-factor and quantitative strategy engines."""

    @abstractmethod
    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Compute strategy scores for given price history and metadata.

        Args:
            prices_dict: Dictionary mapping symbol to OHLCV DataFrame.
            fundamentals_dict: Optional fundamental metrics dict per symbol.
            indicators_df: Optional macro market indicators DataFrame.

        Returns:
            pd.DataFrame with ['symbol', 'score'] (or strategy specific score column)
            normalized to [0.0, 1.0].
        """
        pass
