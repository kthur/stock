"""
trading_system/src/ai/score_normalizer.py
Cross-Sectional Score Normalization Engine for 31 Multi-Factor Strategies.
Eliminates scale, mean, and variance disparities across heterogeneous strategy signals
while strictly preserving NaNs for missing factors.
"""

import logging
from typing import List, Optional
import numpy as np
import pandas as pd
from scipy.special import erf

logger = logging.getLogger(__name__)


class CrossSectionalScoreNormalizer:
    """
    Normalizes multi-factor strategy scores across stock cross-sections
    to eliminate scale and variance disparities while strictly preserving NaNs.
    """

    REGION_MAP = {
        'KOSPI': 'KR',
        'KOSDAQ': 'KR',
        'KRX': 'KR',
        'SP500': 'US',
        'NASDAQ': 'US',
        'RUSSELL2000': 'US',
        'US': 'US',
    }

    def __init__(self, method: str = 'percentile_rank', min_symbols_per_market: int = 10):
        """
        Parameters
        ----------
        method : str
            'percentile_rank' / 'rank_percentile' : Uniform ranking in [0.005, 0.995]
            'winsorized_zscore' / 'zscore' : Gaussian CDF mapping Phi(Z) in [0.005, 0.995]
        min_symbols_per_market : int
            Minimum symbol count to perform per-market partitioning before falling back to regional/global.
        """
        self.method = method
        self.min_symbols_per_market = min_symbols_per_market

    def normalize_cross_section(
        self,
        df: pd.DataFrame,
        score_cols: List[str],
        method: Optional[str] = None,
        group_col: Optional[str] = 'market'
    ) -> pd.DataFrame:
        """Alias for normalize_scores matching interface contract."""
        return self.normalize_scores(df=df, strategy_cols=score_cols, market_col=group_col, method=method)

    def normalize_scores(
        self,
        df: pd.DataFrame,
        strategy_cols: List[str],
        market_col: Optional[str] = 'market',
        method: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Applies cross-sectional normalization to specified strategy score columns.
        NaN values are preserved strictly as NaN.
        """
        eff_method = method or self.method
        if df.empty:
            return df.copy()

        out_df = df.copy()
        valid_cols = [c for c in strategy_cols if c in out_df.columns]
        if not valid_cols:
            return out_df

        # Ensure float dtype on valid columns to avoid pandas incompatible dtype warnings
        for col in valid_cols:
            out_df[col] = pd.to_numeric(out_df[col], errors='coerce').astype(float)

        # Partition by market if market_col is available
        has_market = market_col is not None and market_col in out_df.columns and out_df[market_col].notna().any()

        if has_market:
            mkt_clean_series = out_df[market_col].fillna('UNKNOWN').astype(str)
            market_groups = out_df.groupby(mkt_clean_series, dropna=False).groups
            small_indices = []

            for mkt_val, group_idx in market_groups.items():
                if len(group_idx) >= self.min_symbols_per_market:
                    sub_df = out_df.loc[group_idx, valid_cols]
                    out_df.loc[group_idx, valid_cols] = self._normalize_matrix(sub_df, eff_method)
                else:
                    small_indices.extend(list(group_idx))

            # Handle small market groups via regional fallback or global fallback
            if small_indices:
                small_df = out_df.loc[small_indices]
                region_series = small_df[market_col].fillna('UNKNOWN').astype(str).map(
                    lambda m: self.REGION_MAP.get(m.upper(), 'GLOBAL')
                ).fillna('GLOBAL')
                region_groups = small_df.groupby(region_series, dropna=False).groups
                for region, actual_idx in region_groups.items():
                    sub_small = out_df.loc[actual_idx, valid_cols]
                    out_df.loc[actual_idx, valid_cols] = self._normalize_matrix(sub_small, eff_method)
        else:
            out_df[valid_cols] = self._normalize_matrix(out_df[valid_cols], eff_method)

        return out_df

    def _normalize_matrix(self, sub_df: pd.DataFrame, method: str) -> pd.DataFrame:
        norm_df = pd.DataFrame(index=sub_df.index, columns=sub_df.columns, dtype=float)

        for col in sub_df.columns:
            s = pd.to_numeric(sub_df[col], errors='coerce')
            valid_mask = s.notna() & np.isfinite(s)
            n_valid = int(valid_mask.sum())

            if n_valid == 0:
                norm_df[col] = np.nan
            elif n_valid == 1:
                # Single observation receives neutral midpoint
                norm_df.loc[valid_mask, col] = 0.50
            else:
                vals = s.loc[valid_mask].values
                method_clean = method.lower()
                if method_clean in ('rank_percentile', 'percentile_rank', 'rank'):
                    # (Rank - 0.5) / N uniformly distributed in (0, 1)
                    # Use average ranking for ties
                    rank_s = pd.Series(vals, index=s.loc[valid_mask].index).rank(ascending=True, method='average')
                    norm_vals = ((rank_s - 0.5) / float(n_valid)).clip(0.005, 0.995)
                    norm_df.loc[valid_mask, col] = norm_vals.values
                elif method_clean in ('winsorized_zscore', 'zscore'):
                    q01 = np.percentile(vals, 1.0)
                    q99 = np.percentile(vals, 99.0)
                    w_vals = np.clip(vals, q01, q99)
                    med = float(np.median(w_vals))
                    mad = float(np.median(np.abs(w_vals - med)))
                    robust_std = 1.4826 * mad
                    if robust_std < 1e-6:
                        # Fallback to standard deviation if MAD is zero (e.g. discrete repeated values)
                        sample_std = float(np.std(w_vals))
                        robust_std = sample_std if sample_std > 1e-6 else 1.0
                    z = (w_vals - med) / robust_std
                    # Standard Gaussian CDF Phi(z) = 0.5 * (1 + erf(z / sqrt(2)))
                    phi_z = 0.5 * (1.0 + erf(z / np.sqrt(2.0)))
                    norm_df.loc[valid_mask, col] = np.clip(phi_z, 0.005, 0.995)
                else:
                    norm_df.loc[valid_mask, col] = np.clip(vals, 0.0, 1.0)

        return norm_df
