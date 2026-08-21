"""
src/core/base_strategy.py
Base Strategy Engine abstract class for quantitative factor strategy engines.
Provides unified OHLCV extraction, rank-normalization, ScoreDataFrame, and missing data handling.
"""

from abc import ABC, abstractmethod
import logging
from typing import Dict, List, Optional, Any, Union
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ScoreDataFrame(pd.DataFrame):
    """DataFrame subclass supporting both DataFrame operations and dict-like symbol indexing/comparison."""
    @property
    def _constructor(self):
        return ScoreDataFrame

    def __getitem__(self, key):
        if isinstance(key, str) and key in self.columns:
            return super().__getitem__(key)
        if isinstance(key, str) and 'symbol' in self.columns and len(self.columns) >= 2:
            match = self[self['symbol'] == key]
            if not match.empty:
                score_cols = [c for c in self.columns if c != 'symbol']
                if score_cols:
                    return match[score_cols[0]].iloc[0]
        return super().__getitem__(key)

    def __contains__(self, key):
        if isinstance(key, str) and 'symbol' in self.columns:
            if key in self['symbol'].values:
                return True
        return super().__contains__(key)

    def __eq__(self, other):
        if isinstance(other, dict):
            if not other and self.empty:
                return True
            if not other and not self.empty:
                return False
            if 'symbol' in self.columns:
                score_cols = [c for c in self.columns if c != 'symbol']
                if score_cols:
                    d = dict(zip(self['symbol'], self[score_cols[0]]))
                    return d == other
            return False
        return super().__eq__(other)

    def get(self, key, default=None):
        try:
            return self[key]
        except (KeyError, IndexError):
            return default


def make_score_dataframe(
    scores: Union[Dict[str, float], List[Dict[str, Any]]],
    score_column: str = "score"
) -> ScoreDataFrame:
    """Creates a ScoreDataFrame with ['symbol', score_column]."""
    if isinstance(scores, dict):
        data = [{'symbol': k, score_column: v} for k, v in scores.items()]
    elif isinstance(scores, list):
        data = scores
    else:
        data = []
    df = ScoreDataFrame(data)
    if 'symbol' not in df.columns:
        df['symbol'] = []
    if score_column not in df.columns:
        df[score_column] = []
    return df


def safe_pct_rank(series: pd.Series, min_clip: float = 0.05, max_clip: float = 0.95) -> pd.Series:
    """Percentile ranks a pandas series safely clipping between min_clip and max_clip."""
    if series.empty or series.nunique() <= 1:
        return pd.Series(0.5, index=series.index)
    ranks = series.rank(pct=True)
    return ranks.clip(lower=min_clip, upper=max_clip)


class BaseStrategyEngine(ABC):
    """
    Abstract Base Class for multi-factor quantitative strategy engines.
    """

    def __init__(self, name: str = "BaseStrategy", config: Optional[Any] = None):
        self.name = name
        self.config = config

    @staticmethod
    def extract_ohlcv(
        symbol: str,
        prices_dict: Dict[str, pd.DataFrame],
        min_bars: int = 5
    ) -> Optional[pd.DataFrame]:
        """
        Safely extracts and standardizes OHLCV DataFrame for a symbol.
        Standardizes column casing (Open, High, Low, Close, Volume) and cleans NaNs.
        """
        if not prices_dict or symbol not in prices_dict:
            return None

        df = prices_dict[symbol]
        if df is None or df.empty or len(df) < min_bars:
            return None

        try:
            df_copy = df.copy()
            if isinstance(df_copy.columns, pd.MultiIndex):
                df_copy.columns = df_copy.columns.droplevel(1)

            col_map = {c: str(c).capitalize() for c in df_copy.columns if str(c).lower() in ['open', 'high', 'low', 'close', 'volume']}
            df_copy = df_copy.rename(columns=col_map)

            if 'Close' not in df_copy.columns:
                return None

            return df_copy
        except Exception as e:
            logger.debug(f"Error extracting OHLCV for {symbol}: {e}")
            return None

    @staticmethod
    def normalize_scores_series(
        raw_scores: Union[pd.Series, Dict[str, float]],
        min_clip: float = 0.05,
        max_clip: float = 0.95,
        neutral_fill: float = 0.50
    ) -> Dict[str, float]:
        """
        Applies percentile rank normalization to raw scores, clipping between [min_clip, max_clip].
        """
        if isinstance(raw_scores, dict):
            if not raw_scores:
                return {}
            s = pd.Series(raw_scores, dtype=float)
        else:
            s = raw_scores.copy()

        if s.empty:
            return {}

        valid_mask = s.notna() & np.isfinite(s)
        if valid_mask.sum() < 2:
            return {k: neutral_fill for k in s.index}

        ranked = s[valid_mask].rank(pct=True)
        scaled = np.clip(ranked, min_clip, max_clip)

        result = s.to_dict()
        for k in s.index:
            if k in scaled.index:
                result[k] = float(scaled[k])
            else:
                result[k] = float(neutral_fill)

        return result
