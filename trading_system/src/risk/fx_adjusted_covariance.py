"""
src/risk/fx_adjusted_covariance.py
Cross-Border FX-Adjusted Covariance & Global Calendar Alignment Engine.

1. Aligns KRX (KOSPI, KOSDAQ) and US (SP500, NASDAQ, RUSSELL2000) trading calendars.
2. Integrates USD/KRW FX volatility and compound returns for unified KRW-denominated risk budgeting:
   R_{i,KRW} = (1 + R_{i,USD}) * (1 + R_{USDKRW}) - 1
3. Applies Ledoit-Wolf Shrinkage & Lower-Tail Asymmetric Stress Semi-Covariance.
"""

from __future__ import annotations

import logging
import math
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf

logger = logging.getLogger(__name__)


class FXAdjustedCovarianceEngine:
    """
    Cross-Border Multi-Asset FX-Adjusted Covariance Engine.
    """

    @staticmethod
    def align_price_series(
        prices_dict: Dict[str, pd.DataFrame],
        lookback_days: int = 60
    ) -> pd.DataFrame:
        """
        Extracts Close prices for all symbols and aligns them on a unified global datetime index
        using forward-filling (max 3 days) to handle asynchronous market holidays.
        """
        if not prices_dict:
            return pd.DataFrame()

        close_dict: Dict[str, pd.Series] = {}
        for sym, df in prices_dict.items():
            if df is None or df.empty:
                continue
            close_col = next(
                (c for c in df.columns if str(c).lower() in ("close", "adj close", "adjclose")),
                None
            )
            if close_col is None:
                continue

            s = df[close_col]
            if isinstance(s, pd.DataFrame):
                s = s.iloc[:, 0]
            s = pd.to_numeric(s, errors="coerce").dropna()
            if len(s) >= 5:
                try:
                    s.index = pd.to_datetime(s.index)
                    s = s[~s.index.duplicated(keep="last")].sort_index()
                    close_dict[str(sym)] = s
                except Exception:
                    continue

        if not close_dict:
            return pd.DataFrame()

        df_all = pd.DataFrame(close_dict).sort_index()
        # Forward fill up to 3 business days for holidays, then drop remaining leading NaNs
        df_filled = df_all.ffill(limit=3).tail(lookback_days + 1)
        return df_filled

    @staticmethod
    def compute_krw_adjusted_returns(
        prices_dict: Dict[str, pd.DataFrame],
        usdkrw_series: Optional[pd.Series] = None,
        market_map: Optional[Dict[str, str]] = None,
        lookback_days: int = 60,
        fx_series_dict: Optional[Dict[str, pd.Series]] = None
    ) -> pd.DataFrame:
        """
        Computes unified KRW-denominated daily returns for all global assets.
        For international stocks (US, JP, CN, EU, IN, VN, TW, AU, BR, HK, SG, CA),
        applies the exact compound FX return:
        R_{i, KRW} = (1 + R_{i, local}) * (1 + R_{FX/KRW}) - 1
        """
        df_prices = FXAdjustedCovarianceEngine.align_price_series(prices_dict, lookback_days=lookback_days)
        if df_prices.empty or len(df_prices) < 2:
            return pd.DataFrame()

        returns_df = df_prices.pct_change(fill_method=None).dropna(how="all").fillna(0.0)
        symbols = list(returns_df.columns)
        market_map = market_map or {}

        # Align USD/KRW series if available
        has_fx = False
        fx_ret = pd.Series(0.0, index=returns_df.index)
        if usdkrw_series is not None and len(usdkrw_series) >= 2:
            try:
                fx_s = pd.to_numeric(usdkrw_series, errors="coerce").dropna()
                fx_s.index = pd.to_datetime(fx_s.index)
                fx_s = fx_s[~fx_s.index.duplicated(keep="last")].sort_index()
                fx_aligned = fx_s.reindex(returns_df.index).ffill().bfill()
                fx_ret = fx_aligned.pct_change(fill_method=None).fillna(0.0)
                has_fx = True
            except Exception as e:
                logger.debug(f"[FX Engine] FX series alignment fallback: {e}")

        # Pre-align multi-currency FX return series if provided
        aligned_multi_fx: Dict[str, pd.Series] = {}
        if fx_series_dict:
            for c_pair, c_s in fx_series_dict.items():
                if c_s is not None and len(c_s) >= 2:
                    try:
                        s_clean = pd.to_numeric(c_s, errors="coerce").dropna()
                        s_clean.index = pd.to_datetime(s_clean.index)
                        s_clean = s_clean[~s_clean.index.duplicated(keep="last")].sort_index()
                        s_aligned = s_clean.reindex(returns_df.index).ffill().bfill()
                        aligned_multi_fx[c_pair] = s_aligned.pct_change(fill_method=None).fillna(0.0)
                    except Exception:
                        pass

        krw_returns = returns_df.copy()
        for sym in symbols:
            mkt = str(market_map.get(sym, "")).upper()
            is_krx = mkt in ("KOSPI", "KOSDAQ", "KRX") or (str(sym).isdigit() and len(str(sym)) == 6)

            if not is_krx and has_fx:
                r_loc = returns_df[sym]
                # Check for currency-specific FX series
                curr_fx_ret = fx_ret
                if mkt in ('JAPAN', 'TSE', 'JAPAN_TSE') and 'JPYKRW=X' in aligned_multi_fx:
                    curr_fx_ret = aligned_multi_fx['JPYKRW=X']
                elif mkt in ('EUROPE', 'STOXX', 'EUROPE_STOXX', 'DAX') and 'EURKRW=X' in aligned_multi_fx:
                    curr_fx_ret = aligned_multi_fx['EURKRW=X']
                elif mkt in ('CHINA', 'SSE', 'SZSE', 'CHINA_SSE', 'CHINA_SZSE') and 'CNYKRW=X' in aligned_multi_fx:
                    curr_fx_ret = aligned_multi_fx['CNYKRW=X']
                
                # Compound return in base currency (KRW)
                krw_returns[sym] = (1.0 + r_loc) * (1.0 + curr_fx_ret) - 1.0

        return krw_returns

    @staticmethod
    def denoise_covariance_marchenko_pastur(
        cov_matrix: np.ndarray,
        t_obs: int,
        n_assets: int,
        noise_spread_factor: float = 1.0
    ) -> np.ndarray:
        """
        Applies Random Matrix Theory (RMT) Marchenko-Pastur Spectral Denoising (1967, Lopez de Prado 2020).
        Replaces noise eigenvalues (lambda <= lambda_+) with constant residual average eigenvalue,
        preserving true signal eigenvectors and eliminating spurious high-dimensional correlation spikes.

        lambda_+ = sigma^2 * (1 + sqrt(N/T))^2
        """
        if cov_matrix is None or cov_matrix.size == 0:
            return np.asarray(cov_matrix, dtype=np.float64) if cov_matrix is not None else np.empty((0, 0), dtype=np.float64)
        if n_assets <= 1 or t_obs <= n_assets:
            return np.asarray(cov_matrix, dtype=np.float64)

        try:
            # 1. Convert covariance to correlation matrix and standard deviations
            stds = np.sqrt(np.maximum(np.diag(cov_matrix), 1e-8))
            inv_stds = 1.0 / stds
            corr = inv_stds[:, None] * cov_matrix * inv_stds[None, :]
            corr = np.nan_to_num(corr, nan=0.0)
            np.fill_diagonal(corr, 1.0)

            # 2. Eigen-decomposition of correlation matrix
            eigenvals, eigenvecs = np.linalg.eigh(corr)
            # Sort in descending order
            idx = np.argsort(eigenvals)[::-1]
            eigenvals = eigenvals[idx]
            eigenvecs = eigenvecs[:, idx]

            # 3. Marchenko-Pastur Upper Bound
            q = float(t_obs) / float(n_assets)
            # Estimate residual variance sigma^2 from smallest eigenvalues (exclude market mode lambda_1)
            sigma_sq = float(np.mean(eigenvals[1:])) if len(eigenvals) > 1 else 1.0
            sigma_sq = max(0.10, min(1.0, sigma_sq))
            lambda_plus = sigma_sq * (1.0 + np.sqrt(1.0 / q)) ** 2 * float(noise_spread_factor)

            # 4. Constant Residual Eigenvalue Shrinkage
            is_noise = eigenvals <= lambda_plus
            if np.any(is_noise) and not np.all(is_noise):
                noise_mean = float(np.mean(eigenvals[is_noise]))
                denoised_eigenvals = eigenvals.copy()
                denoised_eigenvals[is_noise] = noise_mean
            else:
                denoised_eigenvals = eigenvals.copy()

            # Ensure all eigenvalues are positive
            denoised_eigenvals = np.maximum(denoised_eigenvals, 1e-6)

            # 5. Reconstruct denoised correlation matrix
            denoised_corr = eigenvecs @ np.diag(denoised_eigenvals) @ eigenvecs.T
            # Rescale diagonal to 1.0
            diag_inv_sqrt = 1.0 / np.sqrt(np.maximum(np.diag(denoised_corr), 1e-8))
            denoised_corr = diag_inv_sqrt[:, None] * denoised_corr * diag_inv_sqrt[None, :]
            np.fill_diagonal(denoised_corr, 1.0)

            # 6. Reconstruct denoised covariance matrix
            denoised_cov = stds[:, None] * denoised_corr * stds[None, :]
            return np.asarray(denoised_cov, dtype=np.float64)
        except Exception as e:
            logger.debug(f"[RMT DENOISE] Fallback to original covariance: {e}")
            return np.asarray(cov_matrix, dtype=np.float64)

    @staticmethod
    def compute_fx_adjusted_covariance(
        prices_dict: Dict[str, pd.DataFrame],
        usdkrw_series: Optional[pd.Series] = None,
        market_map: Optional[Dict[str, str]] = None,
        lookback_days: int = 60,
        tail_stress_weight: float = 0.30,
        use_rmt_denoising: bool = True
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Calculates the regularized FX-adjusted covariance matrix with Ledoit-Wolf shrinkage,
        RMT Marchenko-Pastur spectral denoising, and asymmetric lower-tail stress blending.

        Returns:
            Tuple of (cov_df, krw_adjusted_returns_df)
        """
        krw_returns = FXAdjustedCovarianceEngine.compute_krw_adjusted_returns(
            prices_dict=prices_dict,
            usdkrw_series=usdkrw_series,
            market_map=market_map,
            lookback_days=lookback_days
        )

        symbols = list(krw_returns.columns)
        n_assets = len(symbols)

        if n_assets == 0:
            return pd.DataFrame(), pd.DataFrame()
        if n_assets == 1:
            var_val = float(krw_returns.iloc[:, 0].var()) if len(krw_returns) > 1 else 0.0004
            var_val = max(1e-6, var_val) if math.isfinite(var_val) else 0.0004
            return pd.DataFrame([[var_val]], index=symbols, columns=symbols), krw_returns

        mat = krw_returns.values
        t_obs = len(mat)
        # Fallback if too few rows
        if t_obs < 5:
            diag_vals = np.var(mat, axis=0, ddof=1) if t_obs > 1 else np.full(n_assets, 0.0004)
            diag_vals = np.where(np.isnan(diag_vals) | (diag_vals < 1e-6), 0.0004, diag_vals)
            cov_mat = np.diag(diag_vals)
            return pd.DataFrame(cov_mat, index=symbols, columns=symbols), krw_returns

        # Ledoit-Wolf Shrinkage
        try:
            lw = LedoitWolf()
            cov_shrunk = lw.fit(mat).covariance_
        except Exception:
            cov_shrunk = np.cov(mat, rowvar=False)
            if cov_shrunk.ndim == 0:
                cov_shrunk = np.array([[float(cov_shrunk)]])

        # RMT Marchenko-Pastur Spectral Denoising
        if use_rmt_denoising and t_obs > n_assets and n_assets >= 3:
            cov_shrunk = FXAdjustedCovarianceEngine.denoise_covariance_marchenko_pastur(
                cov_matrix=cov_shrunk,
                t_obs=t_obs,
                n_assets=n_assets
            )

        # Asymmetric Lower-Tail Contagion Stress Blend
        if tail_stress_weight > 0 and len(mat) >= 10:
            try:
                mkt_ret = np.mean(mat, axis=1)
                tail_cutoff = float(np.quantile(mkt_ret, 0.10))
                tail_mask = mkt_ret <= tail_cutoff
                if np.sum(tail_mask) >= 3:
                    tail_cov = np.cov(mat[tail_mask], rowvar=False)
                    if tail_cov.shape == cov_shrunk.shape and np.all(np.isfinite(tail_cov)):
                        k_eff = float(np.clip(tail_stress_weight, 0.0, 0.50))
                        cov_shrunk = (1.0 - k_eff) * cov_shrunk + k_eff * tail_cov
                        np.fill_diagonal(cov_shrunk, np.diag(cov_shrunk) + 1e-6)
            except Exception as e:
                logger.debug(f"[FX Engine] Tail stress calculation bypassed: {e}")

        # Ensure positive definiteness
        cov_shrunk = np.nan_to_num(cov_shrunk, nan=0.0004)
        np.fill_diagonal(cov_shrunk, np.maximum(np.diag(cov_shrunk), 1e-6))

        cov_df = pd.DataFrame(cov_shrunk, index=symbols, columns=symbols)
        return cov_df, krw_returns
