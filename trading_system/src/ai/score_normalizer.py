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

    def __init__(self, method: str = 'winsorized_zscore', min_symbols_per_market: int = 10):
        """
        Parameters
        ----------
        method : str
            'winsorized_zscore' / 'zscore' : Gaussian CDF mapping Phi(Z) in [0.005, 0.995] (Preserves fat-tail dispersion, default)
            'percentile_rank' / 'rank_percentile' : Uniform ranking in [0.005, 0.995]
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
        group_col: Optional[str] = 'market',
        sector_col: Optional[str] = None,
    ) -> pd.DataFrame:
        """Alias for normalize_scores matching interface contract."""
        return self.normalize_scores(df=df, strategy_cols=score_cols, market_col=group_col, method=method, sector_col=sector_col)

    def normalize(
        self,
        df: pd.DataFrame,
        score_cols: List[str],
        method: Optional[str] = None,
        group_col: Optional[str] = 'market',
        sector_col: Optional[str] = None,
    ) -> pd.DataFrame:
        """Alias for normalize_scores."""
        return self.normalize_scores(df=df, strategy_cols=score_cols, market_col=group_col, method=method, sector_col=sector_col)

    def normalize_scores(
        self,
        df: pd.DataFrame,
        strategy_cols: List[str],
        market_col: Optional[str] = 'market',
        method: Optional[str] = None,
        sector_col: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Applies cross-sectional normalization to specified strategy score columns.
        NaN values are preserved strictly as NaN.
        Supports sector neutralization if sector_col is provided.
        """
        eff_method = method or self.method
        if df.empty:
            return df.copy()

        out_df = df.copy()
        orig_index = out_df.index
        has_dup_index = bool(orig_index.duplicated().any())
        if has_dup_index:
            out_df = out_df.reset_index(drop=True)

        valid_cols = [c for c in strategy_cols if c in out_df.columns]
        if not valid_cols:
            return df.copy()

        # Ensure float dtype on valid columns to avoid pandas incompatible dtype warnings
        for col in valid_cols:
            out_df[col] = pd.to_numeric(out_df[col], errors='coerce').astype(float)

        # Partition by market and/or sector if available
        has_market = market_col is not None and market_col in out_df.columns and out_df[market_col].notna().any()
        has_sector = sector_col is not None and sector_col in out_df.columns and out_df[sector_col].notna().any()

        if has_market and has_sector:
            mkt_clean = out_df[market_col].fillna('UNKNOWN').astype(str)
            sec_clean = out_df[sector_col].fillna('UNKNOWN').astype(str)
            group_key = mkt_clean + "__" + sec_clean
            sector_groups = out_df.groupby(group_key, dropna=False).groups
            small_indices = []

            for grp_val, group_idx in sector_groups.items():
                if len(group_idx) >= self.min_symbols_per_market:
                    sub_df = out_df.loc[group_idx, valid_cols]
                    out_df.loc[group_idx, valid_cols] = self._normalize_matrix(sub_df, eff_method)
                else:
                    small_indices.extend(list(group_idx))

            # Handle small (market, sector) groups via market fallback
            if small_indices:
                small_df = out_df.loc[small_indices]
                mkt_groups = small_df.groupby(mkt_clean.loc[small_indices], dropna=False).groups
                still_small_indices = []
                for mkt_val, group_idx in mkt_groups.items():
                    if len(group_idx) >= self.min_symbols_per_market:
                        sub_df = out_df.loc[group_idx, valid_cols]
                        out_df.loc[group_idx, valid_cols] = self._normalize_matrix(sub_df, eff_method)
                    else:
                        still_small_indices.extend(list(group_idx))

                # Handle remaining small groups via regional/global fallback
                if still_small_indices:
                    still_small_df = out_df.loc[still_small_indices]
                    region_series = still_small_df[market_col].fillna('UNKNOWN').astype(str).map(
                        lambda m: self.REGION_MAP.get(m.upper(), 'GLOBAL')
                    ).fillna('GLOBAL')
                    region_groups = still_small_df.groupby(region_series, dropna=False).groups
                    for region, actual_idx in region_groups.items():
                        sub_small = out_df.loc[actual_idx, valid_cols]
                        out_df.loc[actual_idx, valid_cols] = self._normalize_matrix(sub_small, eff_method)
        elif has_market:
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
        elif has_sector:
            sec_clean_series = out_df[sector_col].fillna('UNKNOWN').astype(str)
            sector_groups = out_df.groupby(sec_clean_series, dropna=False).groups
            small_indices = []

            for sec_val, group_idx in sector_groups.items():
                if len(group_idx) >= self.min_symbols_per_market:
                    sub_df = out_df.loc[group_idx, valid_cols]
                    out_df.loc[group_idx, valid_cols] = self._normalize_matrix(sub_df, eff_method)
                else:
                    small_indices.extend(list(group_idx))

            if small_indices:
                out_df.loc[small_indices, valid_cols] = self._normalize_matrix(out_df.loc[small_indices, valid_cols], eff_method)
        else:
            out_df[valid_cols] = self._normalize_matrix(out_df[valid_cols], eff_method)

        if has_dup_index:
            out_df.index = orig_index
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
                val_std = float(np.std(vals))
                if val_std < 1e-6:
                    norm_df.loc[valid_mask, col] = 0.50
                else:
                    method_clean = method.lower()
                    if method_clean in ('rank_percentile', 'percentile_rank', 'rank'):
                        # (Rank - 0.5) / N uniformly distributed in (0, 1) with standard 'average' tie handling
                        rank_s = pd.Series(vals).rank(ascending=True, method='average')
                        norm_vals = ((rank_s - 0.5) / float(n_valid)).clip(0.005, 0.995)

                        # V8-MED-09 Fix: Relax threshold from n_valid >= 10 to n_valid >= 4
                        # to protect small sectors (4-9 stocks) from artificial down-ranking on sparse zero factors
                        is_exact_zero = (vals == 0.0)
                        if (
                            n_valid >= 4
                            and (vals >= 0.0).all()
                            and is_exact_zero.any()
                            and not is_exact_zero.all()
                            and (is_exact_zero.sum() / float(n_valid)) > 0.20
                        ):
                            nz_mask = ~is_exact_zero
                            if nz_mask.sum() > 1:
                                nz_vals = vals[nz_mask]
                                nz_rank = pd.Series(nz_vals).rank(ascending=True, method='average')
                                nz_norm = (0.52 + 0.475 * ((nz_rank - 0.5) / float(len(nz_vals)))).clip(0.52, 0.995)
                                norm_vals = np.full(n_valid, 0.50, dtype=np.float64)
                                norm_vals[nz_mask] = nz_norm.values

                        norm_df.loc[valid_mask, col] = norm_vals.values if isinstance(norm_vals, pd.Series) else norm_vals
                    elif method_clean in ('winsorized_zscore', 'zscore'):
                        # V8-MED-09 Fix: Add inactive 0-score block isolation for N >= 4
                        # matching rank_percentile to protect inactive stocks in sparse factors
                        # from artificial negative z-score penalty.
                        is_exact_zero = (vals == 0.0)
                        if (
                            n_valid >= 4
                            and (vals >= 0.0).all()
                            and is_exact_zero.any()
                            and not is_exact_zero.all()
                            and (is_exact_zero.sum() / float(n_valid)) > 0.20
                        ):
                            nz_mask = ~is_exact_zero
                            norm_vals = np.full(n_valid, 0.50, dtype=np.float64)
                            if nz_mask.sum() > 1:
                                nz_vals = vals[nz_mask]
                                q005 = np.percentile(nz_vals, 0.5)
                                q995 = np.percentile(nz_vals, 99.5)
                                w_vals = np.clip(nz_vals, q005, q995)
                                med = float(np.median(w_vals))
                                mad = float(np.median(np.abs(w_vals - med)))
                                robust_std = 1.4826 * mad
                                if robust_std < 1e-6:
                                    sample_std = float(np.std(w_vals))
                                    robust_std = sample_std if sample_std > 1e-6 else 1.0
                                z = (w_vals - med) / (robust_std if robust_std > 1e-6 else 1.0)
                                z_clipped = np.clip(z, -8.0, 8.0)
                                phi_z = 0.5 * (1.0 + erf(z_clipped / np.sqrt(2.0)))
                                phi_clean = np.nan_to_num(phi_z, nan=0.50, posinf=0.995, neginf=0.005)
                                nz_norm = (0.52 + 0.475 * phi_clean).clip(0.52, 0.995)
                                norm_vals[nz_mask] = nz_norm
                            elif nz_mask.sum() == 1:
                                norm_vals[nz_mask] = 0.75
                            norm_df.loc[valid_mask, col] = norm_vals
                        else:
                            q005 = np.percentile(vals, 0.5)
                            q995 = np.percentile(vals, 99.5)
                            w_vals = np.clip(vals, q005, q995)
                            med = float(np.median(w_vals))
                            mad = float(np.median(np.abs(w_vals - med)))
                            robust_std = 1.4826 * mad
                            if robust_std < 1e-6:
                                # Fallback to standard deviation if MAD is zero (e.g. discrete repeated values)
                                sample_std = float(np.std(w_vals))
                                robust_std = sample_std if sample_std > 1e-6 else 1.0
                            z = (w_vals - med) / (robust_std if robust_std > 1e-6 else 1.0)
                            z_clipped = np.clip(z, -8.0, 8.0)
                            # Standard Gaussian CDF Phi(z) = 0.5 * (1 + erf(z / sqrt(2)))
                            phi_z = 0.5 * (1.0 + erf(z_clipped / np.sqrt(2.0)))
                            phi_clean = np.nan_to_num(phi_z, nan=0.50, posinf=0.995, neginf=0.005)
                            norm_df.loc[valid_mask, col] = np.clip(phi_clean, 0.005, 0.995)
                    else:
                        clean_vals = np.nan_to_num(vals, nan=0.50, posinf=1.0, neginf=0.0)
                        norm_df.loc[valid_mask, col] = np.clip(clean_vals, 0.0, 1.0)

        return norm_df
