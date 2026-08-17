"""Base Abstract Strategy Engine definition for Stock Trading System."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
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


class ScoreDataFrame(pd.DataFrame):
    """Custom DataFrame subclass providing dict-like access for legacy test compatibility."""
    @property
    def _constructor(self):
        return ScoreDataFrame

    def __contains__(self, item: Any) -> bool:
        if super().__contains__(item):
            return True
        if "symbol" in self.columns and item in self["symbol"].values:
            return True
        return False

    def __eq__(self, other: Any) -> Any:
        if isinstance(other, dict):
            if len(other) == 0:
                return self.empty
            if "symbol" in self.columns:
                val_cols = [c for c in self.columns if c != "symbol"]
                if val_cols:
                    cur_dict = self.set_index("symbol")[val_cols[0]].to_dict()
                    return cur_dict == other
            return False
        return super().__eq__(other)

    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, str) and item not in self.columns and "symbol" in self.columns:
            match = self[self["symbol"] == item]
            if not match.empty:
                val_cols = [c for c in self.columns if c != "symbol"]
                if val_cols:
                    return float(match[val_cols[0]].iloc[0])
        return super().__getitem__(item)


def make_score_dataframe(rows: Union[List[Dict[str, Any]], Dict[str, Any], Any], score_column: str) -> pd.DataFrame:
    """Helper to construct a ScoreDataFrame from rows list or dict."""
    if not rows:
        return ScoreDataFrame(columns=["symbol", score_column])
    if isinstance(rows, dict):
        rows = [{"symbol": k, score_column: v} for k, v in rows.items()]
    df = ScoreDataFrame(rows)
    if "symbol" not in df.columns:
        df["symbol"] = ""
    if score_column not in df.columns:
        df[score_column] = 0.5
    else:
        df[score_column] = pd.to_numeric(df[score_column], errors="coerce").fillna(0.5).clip(0.0, 1.0)
    return df

