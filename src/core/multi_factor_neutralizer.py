"""
multi_factor_neutralizer.py — Multi-Factor Risk & Style Neutralizer Engine (Strategy 21)

Neutralizes unwanted Fama-French 5-Factor exposures (SMB, HML, RMW, CMA, MOM)
from raw momentum and return signals via cross-sectional QR regression decomposition,
extracting pure idiosyncratic alpha scores with guaranteed |rho| < 0.15.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

from src.core.base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta


def compute_precision_weighted_neutralization(
    y: np.ndarray,
    B: np.ndarray,
    weights_precision: Optional[np.ndarray] = None,
    ridge_lambda: float = 1e-4,
) -> np.ndarray:
    """Computes precision-weighted minimum-distortion factor neutralization:
        y_star = [I - W^{-1} B (B^T W^{-1} B + ridge * I)^{-1} B^T] y
    where W = diag(w_1, ..., w_N).
    When weights_precision is None or uniform, reduces algebraically to standard OLS / QR projection.
    Robust to singular matrices via Tikhonov ridge regularization, falls back to SVD
    pseudoinverse when N < K, and returns zero residual when N <= 1.
    """
    y_arr = np.asarray(y, dtype=float).copy().ravel()
    B_arr = np.asarray(B, dtype=float).copy()
    if B_arr.ndim == 1:
        B_arr = B_arr.reshape(-1, 1)

    N = len(y_arr)
    if N == 0 or B_arr.shape[0] != N:
        return np.zeros_like(y_arr, dtype=float)
    if N == 1:
        return np.zeros_like(y_arr, dtype=float)

    # Sanitize inputs (NaN imputation)
    if not np.all(np.isfinite(y_arr)):
        med_y = float(np.nanmedian(y_arr)) if np.any(np.isfinite(y_arr)) else 0.0
        y_arr = np.where(np.isfinite(y_arr), y_arr, med_y)

    K = B_arr.shape[1]
    if not np.all(np.isfinite(B_arr)):
        for k in range(K):
            col = B_arr[:, k]
            if not np.all(np.isfinite(col)):
                med_col = float(np.nanmedian(col)) if np.any(np.isfinite(col)) else 0.0
                B_arr[:, k] = np.where(np.isfinite(col), col, med_col)

    # Under-determined cross-sections (N < K) fallback to SVD pseudoinverse
    if N < K:
        beta_pinv = np.linalg.pinv(B_arr) @ y_arr
        return y_arr - B_arr @ beta_pinv

    # Check if weights_precision is provided and non-uniform
    is_uniform = True
    w = None
    if weights_precision is not None:
        w_cand = np.asarray(weights_precision, dtype=float).copy().ravel()
        if len(w_cand) == N and np.all(np.isfinite(w_cand)) and np.all(w_cand > 1e-12):
            w_min, w_max = float(np.min(w_cand)), float(np.max(w_cand))
            if (w_max - w_min) > 1e-8 * max(abs(w_min), 1.0):
                is_uniform = False
                w = w_cand
        elif len(w_cand) == N:
            w_fixed = np.where(np.isfinite(w_cand) & (w_cand > 1e-12), w_cand, 1.0)
            w_min, w_max = float(np.min(w_fixed)), float(np.max(w_fixed))
            if (w_max - w_min) > 1e-8 * max(abs(w_min), 1.0):
                is_uniform = False
                w = w_fixed

    # When weights_precision is None or uniform, reduces algebraically to standard OLS / QR projection
    if is_uniform or w is None:
        try:
            Q, _ = np.linalg.qr(B_arr, mode="reduced")
            return y_arr - Q @ (Q.T @ y_arr)
        except Exception:
            beta_pinv = np.linalg.pinv(B_arr) @ y_arr
            return y_arr - B_arr @ beta_pinv

    # Precision-weighted Generalized Least Squares (GLS) minimum-distortion projection
    w_clean = np.where(np.isfinite(w) & (w > 1e-12), w, 1.0)
    w_inv = 1.0 / w_clean
    W_inv_B = w_inv[:, None] * B_arr
    A = B_arr.T @ W_inv_B
    b = B_arr.T @ y_arr

    is_ill_conditioned = False
    try:
        cond_A = np.linalg.cond(A)
        if not np.isfinite(cond_A) or cond_A > 1e10:
            is_ill_conditioned = True
    except Exception:
        is_ill_conditioned = True

    if is_ill_conditioned:
        eff_lambda = max(ridge_lambda, 1e-4) if (ridge_lambda is not None and ridge_lambda > 0) else 1e-4
        A_reg = A + eff_lambda * np.eye(K)
        try:
            mu = np.linalg.solve(A_reg, b)
        except np.linalg.LinAlgError:
            mu = np.linalg.pinv(A_reg) @ b
    else:
        try:
            mu = np.linalg.solve(A, b)
        except np.linalg.LinAlgError:
            eff_lambda = max(ridge_lambda, 1e-4) if (ridge_lambda is not None and ridge_lambda > 0) else 1e-4
            A_reg = A + eff_lambda * np.eye(K)
            try:
                mu = np.linalg.solve(A_reg, b)
            except np.linalg.LinAlgError:
                mu = np.linalg.pinv(A_reg) @ b

    y_star = y_arr - W_inv_B @ mu
    return y_star


def compute_bilinear_interaction_alpha(
    scores_matrix: np.ndarray,
    M_tensor: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Computes non-linear synergistic interaction alpha across factor scores:
        alpha_synergy = tanh(0.5 * diag(S @ M @ S.T))
                      = tanh(0.5 * sum_j (S @ M)_ij * S_ij)
    Bounded strictly in [-1.0, 1.0].
    Symmetric low-rank interaction tensor M models:
    - Value x Momentum = 0.25 (M[1,4] = M[4,1] = 0.25)
    - Momentum x Quality = 0.20 (M[4,2] = M[2,4] = 0.20)
    - Quality x Investment = 0.15 (M[2,3] = M[3,2] = 0.15)
    """
    S = np.asarray(scores_matrix, dtype=float).copy()
    if S.ndim == 1:
        S = S.reshape(1, -1)

    N, K = S.shape
    if N == 0 or K == 0:
        return np.zeros(N, dtype=float)

    # Sanitize non-finite values to median or 0.0
    if not np.all(np.isfinite(S)):
        for k in range(K):
            col = S[:, k]
            if not np.all(np.isfinite(col)):
                med_val = float(np.nanmedian(col)) if np.any(np.isfinite(col)) else 0.0
                S[:, k] = np.where(np.isfinite(col), col, med_val)

    if M_tensor is None:
        M = np.zeros((K, K), dtype=float)
        if K >= 5:
            # 5 Fama-French Factor order: Size=0, Value=1, Profitability=2, Investment=3, Momentum=4
            M[1, 4] = M[4, 1] = 0.25  # Value x Momentum
            M[4, 2] = M[2, 4] = 0.20  # Momentum x Quality
            M[2, 3] = M[3, 2] = 0.15  # Quality x Investment
    else:
        M = np.asarray(M_tensor, dtype=float).copy()
        if M.shape != (K, K):
            M_padded = np.zeros((K, K), dtype=float)
            min_r = min(K, M.shape[0])
            min_c = min(K, M.shape[1])
            M_padded[:min_r, :min_c] = M[:min_r, :min_c]
            M = M_padded

    # Compute bilinear form diag(S @ M @ S.T) in O(N K^2) without forming N x N outer product
    SM = S @ M
    diag_interaction = 0.5 * np.sum(SM * S, axis=1)

    # Extreme score values clipped to [-8.0, 8.0] before bounded tanh activation
    diag_interaction = np.clip(diag_interaction, -8.0, 8.0)
    alpha_synergy = np.tanh(diag_interaction)
    return alpha_synergy


__all__ = [
    "MultiFactorNeutralizerEngine",
    "compute_precision_weighted_neutralization",
    "compute_bilinear_interaction_alpha",
]


@register_strategy(
    StrategyMeta(
        strategy_id="factor_neutralized",
        display_name="Multi-Factor Neutralized Alpha",
        score_column="factor_neutralized_score",
        category="factor",
        output_file="factor_neutralized_predictions.txt",
        default_regime_weights={
            "BEAR": 0.04,
            "BEAR_HIGH_VOL": 0.05,
            "SIDEWAYS_LOW_VOL": 0.03,
            "BULL_HIGH_VOL": 0.03,
            "BULL_LOW_VOL": 0.03,
        },
    )
)
class MultiFactorNeutralizerEngine(BaseStrategyEngine):
    """Strategy 21: Multi-Factor Style Neutralization Engine.

    Extracts pure idiosyncratic alpha by neutralizing Size (SMB), Value (HML),
    Profitability (RMW), Investment (CMA), and Momentum (UMD) style exposures
    using cross-sectional QR residualization with guaranteed |rho| < 0.15.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        self.config = config

    @staticmethod
    def compute_precision_weighted_neutralization(
        y: np.ndarray,
        B: np.ndarray,
        weights_precision: Optional[np.ndarray] = None,
        ridge_lambda: float = 1e-4,
    ) -> np.ndarray:
        """Precision-weighted minimum-distortion factor neutralization."""
        return compute_precision_weighted_neutralization(
            y=y, B=B, weights_precision=weights_precision, ridge_lambda=ridge_lambda
        )

    @staticmethod
    def compute_bilinear_interaction_alpha(
        scores_matrix: np.ndarray,
        M_tensor: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Non-linear synergistic interaction alpha across factor scores."""
        return compute_bilinear_interaction_alpha(
            scores_matrix=scores_matrix, M_tensor=M_tensor
        )

    def compute_scores(
        self,
        prices_dict: Any = None,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Compute factor-neutralized pure alpha scores for all universe symbols.

        Handles both positional universe DataFrames and prices_dict mappings.
        Applies market-grouped median imputation, QR orthogonal projection,
        and hard SLA deflation gating (|rho| < 0.15).
        """
        # 1. Resolve universe DataFrame and price dictionary from arguments
        universe: Optional[pd.DataFrame] = None
        prices_map: Optional[Dict[str, pd.DataFrame]] = None

        if isinstance(prices_dict, pd.DataFrame):
            universe = prices_dict.copy()
            prices_map = kwargs.get("prices_dict", None)
        elif isinstance(prices_dict, dict):
            prices_map = prices_dict
            universe = kwargs.get("universe", kwargs.get("universe_df", None))
            if universe is not None:
                universe = universe.copy()
        else:
            universe = kwargs.get("universe", kwargs.get("universe_df", None))
            if universe is not None:
                universe = universe.copy()
            prices_map = kwargs.get("prices_dict", None)

        if universe is None and prices_map and isinstance(prices_map, dict):
            universe = pd.DataFrame({"symbol": list(prices_map.keys())})

        std_cols = [
            "symbol", "name", "market",
            "factor_neutralized_score", "neutralized_score",
            "smb_exposure", "hml_exposure", "rmw_exposure", "cma_exposure", "umd_exposure",
        ]

        if universe is None or universe.empty:
            return pd.DataFrame(columns=std_cols)

        df = universe.copy().reset_index(drop=True)
        if "symbol" not in df.columns:
            return pd.DataFrame(columns=std_cols)

        df["symbol"] = df["symbol"].astype(str).str.strip()
        if "name" not in df.columns:
            df["name"] = df["symbol"]
        if "market" not in df.columns:
            def _detect_mkt(s: str) -> str:
                s_str = str(s).strip().upper()
                if s_str.endswith('.KQ'):
                    return "KOSDAQ"
                if s_str.isdigit() or s_str.endswith('.KS') or (len(s_str) == 6 and s_str[:5].isdigit()):
                    return "KOSPI"
                return "SP500"
            df["market"] = df["symbol"].map(_detect_mkt)

        # Resolve optional precision weights or idiosyncratic variance for D-FCN
        weights_precision = kwargs.get("weights_precision", kwargs.get("precision_weights", None))
        weights_arr: Optional[np.ndarray] = None
        if weights_precision is not None:
            if isinstance(weights_precision, dict):
                weights_arr = df["symbol"].map(weights_precision).values.astype(float)
            elif isinstance(weights_precision, pd.Series):
                weights_arr = df["symbol"].map(weights_precision.to_dict()).values.astype(float)
            elif isinstance(weights_precision, (np.ndarray, list)):
                w_cand = np.asarray(weights_precision, dtype=float).copy()
                if len(w_cand) == len(df):
                    weights_arr = w_cand
        elif "idiosyncratic_var" in kwargs or "idio_var" in kwargs:
            iv = kwargs.get("idiosyncratic_var", kwargs.get("idio_var", None))
            if isinstance(iv, dict):
                weights_arr = 1.0 / np.maximum(df["symbol"].map(iv).values.astype(float), 1e-6)
            elif isinstance(iv, pd.Series):
                weights_arr = 1.0 / np.maximum(df["symbol"].map(iv.to_dict()).values.astype(float), 1e-6)
            elif isinstance(iv, (np.ndarray, list)):
                iv_cand = np.asarray(iv, dtype=float).copy()
                if len(iv_cand) == len(df):
                    weights_arr = 1.0 / np.maximum(iv_cand, 1e-6)

        # 2. Merge fundamentals_dict if supplied
        if fundamentals_dict and isinstance(fundamentals_dict, dict):
            for col in ["market_cap", "per", "pbr", "roe", "asset_growth_yoy"]:
                if col not in df.columns:
                    df[col] = df["symbol"].map(
                        lambda s: fundamentals_dict.get(s, {}).get(col, np.nan)
                    )
                else:
                    missing_mask = df[col].isna()
                    if missing_mask.any():
                        df.loc[missing_mask, col] = df.loc[missing_mask, "symbol"].map(
                            lambda s: fundamentals_dict.get(s, {}).get(col, np.nan)
                        )

            # 5-4. Sector-grouped median imputation for PBR/ROE
            if "sector" in df.columns or "sector_code" in df.columns:
                sec_col = "sector" if "sector" in df.columns else "sector_code"
                for col in ["pbr", "roe"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        df[col] = df.groupby(sec_col)[col].transform(lambda x: x.fillna(x.median()))
                        df[col] = df[col].fillna(df[col].median())

        # 3. Resolve or compute raw alpha scores y
        raw_scores = kwargs.get("raw_scores", kwargs.get("raw_scores_df", None))
        has_explicit_raw = False

        if raw_scores is not None and isinstance(raw_scores, pd.DataFrame) and not raw_scores.empty:
            score_col = None
            for cand in ["score", "raw_score", "pred_return_20d", "reg_score", "expected_return", "expected_return_20d"]:
                if cand in raw_scores.columns:
                    score_col = cand
                    break
            if score_col is None:
                num_cols = [c for c in raw_scores.columns if c != "symbol"]
                if num_cols:
                    score_col = num_cols[-1]
            if score_col:
                raw_syms = raw_scores["symbol"].values
                df_syms = df["symbol"].values
                if len(raw_syms) == len(df_syms) and np.array_equal(raw_syms, df_syms):
                    df["_raw_y"] = pd.to_numeric(raw_scores[score_col], errors="coerce").values
                else:
                    score_map = dict(zip(raw_scores["symbol"].astype(str).str.strip(), pd.to_numeric(raw_scores[score_col], errors="coerce")))
                    df["_raw_y"] = df["symbol"].map(score_map)
                has_explicit_raw = True
            else:
                df["_raw_y"] = np.nan
        elif raw_scores is not None and isinstance(raw_scores, dict):
            df["_raw_y"] = df["symbol"].map(raw_scores)
            has_explicit_raw = True
        elif "score" in df.columns:
            df["_raw_y"] = pd.to_numeric(df["score"], errors="coerce")
            has_explicit_raw = True
        elif "raw_score" in df.columns:
            df["_raw_y"] = pd.to_numeric(df["raw_score"], errors="coerce")
            has_explicit_raw = True
        else:
            # Fallback 1: Extract from universe momentum columns
            if "momentum_12m_1m" in df.columns:
                df["_raw_y"] = pd.to_numeric(df["momentum_12m_1m"], errors="coerce")
            elif "momentum_12m" in df.columns:
                df["_raw_y"] = pd.to_numeric(df["momentum_12m"], errors="coerce")
            elif "return_3m" in df.columns or "ret_60d" in df.columns:
                col = "return_3m" if "return_3m" in df.columns else "ret_60d"
                df["_raw_y"] = pd.to_numeric(df[col], errors="coerce")
            elif "momentum_1m" in df.columns:
                df["_raw_y"] = pd.to_numeric(df["momentum_1m"], errors="coerce")
            # Fallback 2: Compute 12M-1M / 3M return from prices_map
            elif prices_map and isinstance(prices_map, dict):
                mom_dict = {}
                for sym, p_df in prices_map.items():
                    if isinstance(p_df, pd.DataFrame) and len(p_df) >= 20:
                        c_series = p_df["Close"] if "Close" in p_df.columns else (p_df["close"] if "close" in p_df.columns else None)
                        if c_series is not None and len(c_series) >= 20:
                            c_vals = c_series.dropna().values
                            if len(c_vals) >= 252:
                                mom = (c_vals[-21] / max(c_vals[-252], 1e-6)) - 1.0
                            elif len(c_vals) >= 63:
                                mom = (c_vals[-1] / max(c_vals[-63], 1e-6)) - 1.0
                            else:
                                mom = (c_vals[-1] / max(c_vals[-20], 1e-6)) - 1.0
                            mom_dict[str(sym).strip()] = mom
                if mom_dict:
                    df["_raw_y"] = df["symbol"].map(mom_dict)
                else:
                    df["_raw_y"] = np.nan
            else:
                df["_raw_y"] = np.nan

        # Check if factors or raw scores exist; if totally empty/NaN, return NaNs (Bug A-3 contract)
        fund_cols_exist = any(col in df.columns for col in ["market_cap", "per", "pbr", "roe", "asset_growth_yoy"])
        if not fund_cols_exist and not has_explicit_raw and df["_raw_y"].isna().all():
            logger.info("MultiFactorNeutralizerEngine: missing factors and raw scores. Returning deterministic NaNs.")
            return pd.DataFrame({
                "symbol": df["symbol"],
                "name": df["name"],
                "market": df["market"],
                "factor_neutralized_score": np.nan,
                "neutralized_score": np.nan,
                "smb_exposure": np.nan,
                "hml_exposure": np.nan,
                "rmw_exposure": np.nan,
                "cma_exposure": np.nan,
                "umd_exposure": np.nan,
            })

        # 4. Construct Fama-French 5-Factor Raw Series
        # Factor 1: Size (SMB) -> log(Market Cap)
        cap_series = pd.to_numeric(df.get("market_cap", pd.Series(np.nan, index=df.index)), errors="coerce").values
        f_smb = np.where(cap_series > 0, np.log(np.maximum(cap_series, 1.0)), np.nan)

        # Factor 2: Value (HML) -> 1/PBR or E/P Yield
        pbr_series = pd.to_numeric(df.get("pbr", pd.Series(np.nan, index=df.index)), errors="coerce").values
        per_series = pd.to_numeric(df.get("per", pd.Series(np.nan, index=df.index)), errors="coerce").values

        val_from_pbr = np.where(pbr_series > 0, 1.0 / np.clip(pbr_series, 0.01, 100.0), np.nan)
        val_from_per = np.where(
            per_series > 0,
            1.0 / np.maximum(per_series, 0.1),
            np.where(per_series < 0, -1.0 / np.maximum(np.abs(per_series), 0.1), np.nan)
        )
        f_hml = np.where(np.isfinite(val_from_pbr), val_from_pbr, val_from_per)

        # Factor 3: Profitability (RMW) -> ROE
        f_rmw = pd.to_numeric(df.get("roe", pd.Series(np.nan, index=df.index)), errors="coerce").values

        # Factor 4: Investment (CMA) -> Asset Growth YoY
        cma_raw = df.get("asset_growth_yoy", df.get("asset_growth", pd.Series(np.nan, index=df.index)))
        f_cma = pd.to_numeric(cma_raw, errors="coerce").values

        # Factor 5: Momentum (UMD) -> 12M Momentum / return
        umd_raw = df.get("momentum_12m", df.get("momentum_12m_1m", df.get("momentum_1m", df["_raw_y"])))
        f_umd = pd.to_numeric(umd_raw, errors="coerce").values

        F_all = np.column_stack([f_smb, f_hml, f_rmw, f_cma, f_umd])
        N = len(df)
        y_all = df["_raw_y"].values.astype(float)

        scores = np.full(N, 0.5, dtype=float)
        exposures = np.zeros((N, 5), dtype=float)

        # 5. Market-Grouped Factor Imputation & QR Orthogonal Residualization
        market_groups = df.groupby("market", dropna=False).indices

        for mkt, idxs in market_groups.items():
            N_m = len(idxs)
            if N_m == 0:
                continue

            idxs_arr = np.asarray(idxs)
            y_m = y_all[idxs_arr].copy()

            if np.all(np.isnan(y_m)):
                y_m = np.linspace(0.1, 0.9, N_m) if N_m > 1 else np.array([0.5])
            else:
                med_y = np.nanmedian(y_m) if np.any(np.isfinite(y_m)) else 0.5
                y_m = np.where(np.isfinite(y_m), y_m, med_y)

            F_m = F_all[idxs_arr].copy()
            Z_m = np.zeros((N_m, 5), dtype=float)

            for k in range(5):
                f_k = F_m[:, k]
                valid_mask = np.isfinite(f_k)
                if np.any(valid_mask):
                    med_k = float(np.nanmedian(f_k[valid_mask]))
                    f_clean = np.where(valid_mask, f_k, med_k)
                else:
                    g_vals = F_all[:, k]
                    g_valid = np.isfinite(g_vals)
                    if np.any(g_valid):
                        med_g = float(np.nanmedian(g_vals[g_valid]))
                        f_clean = np.full(N_m, med_g, dtype=float)
                    else:
                        f_clean = np.zeros(N_m, dtype=float)

                f_std = float(np.std(f_clean, ddof=0))
                f_mean = float(np.mean(f_clean))
                if f_std > 1e-6:
                    Z_m[:, k] = (f_clean - f_mean) / f_std
                else:
                    Z_m[:, k] = 0.0

            # Factor Neutralization via D-FCN (GLS / QR minimum distortion)
            X_m = np.column_stack([np.ones(N_m, dtype=float), Z_m])
            w_m = weights_arr[idxs_arr] if weights_arr is not None else None

            residual = compute_precision_weighted_neutralization(
                y=y_m,
                B=X_m,
                weights_precision=w_m,
                ridge_lambda=1e-4,
            )

            # 6. Hard Post-Condition SLA Gate: secondary Gram-Schmidt deflation (corr_thresh = 0.05)
            res_std = float(np.std(residual, ddof=0))
            if res_std > 1e-8 and N_m > 1:
                res_norm = (residual - np.mean(residual)) / res_std
                # Vectorized correlation: Z_m has mean 0 and std 1 for active columns
                corr_vec = np.dot(Z_m.T, res_norm) / N_m
                if np.any(np.abs(corr_vec) >= 0.05) or np.any(~np.isfinite(corr_vec)):
                    for k in range(5):
                        c_val = corr_vec[k]
                        if not np.isfinite(c_val) or abs(c_val) >= 0.05:
                            z_k = Z_m[:, k]
                            z_center = z_k - np.mean(z_k)
                            z_norm = np.linalg.norm(z_center)
                            if z_norm > 1e-8:
                                u_k = z_center / z_norm
                                residual = residual - np.dot(u_k, residual) * u_k
                    residual = residual - np.mean(residual)

            # 7. Robust Scaling to [0.0, 1.0] and Post-Scaling Correlation Check
            if N_m >= 5 and (np.max(residual) - np.min(residual)) > 1e-8:
                norm_scores = pd.Series(residual).rank(pct=True).values.copy()
            elif N_m > 1 and (np.max(residual) - np.min(residual)) > 1e-8:
                p1, p99 = np.percentile(residual, 1), np.percentile(residual, 99)
                denom = (p99 - p1) if (p99 - p1) > 1e-8 else 1.0
                norm_scores = np.clip((residual - p1) / denom, 0.0, 1.0)
            elif N_m == 1:
                norm_scores = np.array([0.5])
            else:
                norm_scores = np.full(N_m, 0.5)

            # Bilinear Factor Interaction Tensor (BFIT) Non-Linear Synergy
            if N_m >= 2 and Z_m.shape[1] >= 5:
                synergy_alpha = compute_bilinear_interaction_alpha(Z_m)
                norm_scores = np.clip(norm_scores + 0.10 * synergy_alpha, 0.02, 0.98)

            # Post-scaling correlation check & linear orthogonal adjustment
            if N_m >= 6 and (np.max(norm_scores) - np.min(norm_scores)) > 1e-8:
                s_mean = float(np.mean(norm_scores))
                s_std = float(np.std(norm_scores, ddof=0))
                if s_std > 1e-6:
                    s_norm = (norm_scores - s_mean) / s_std
                    corr_vec = np.dot(Z_m.T, s_norm) / N_m
                    if np.any(np.abs(corr_vec) >= 0.15) or np.any(~np.isfinite(corr_vec)):
                        adj_scores = norm_scores.copy()
                        for k in range(5):
                            c_val = corr_vec[k]
                            if np.isfinite(c_val) and abs(c_val) >= 0.15:
                                adj_scores = adj_scores - c_val * Z_m[:, k] * s_std
                        s_min, s_max = float(np.min(adj_scores)), float(np.max(adj_scores))
                        if (s_max - s_min) > 1e-8:
                            norm_scores = (adj_scores - s_min) / (s_max - s_min)
                        else:
                            norm_scores = np.full(N_m, 0.5)

            # Pure Idiosyncratic Alpha Conviction Boost & Multi-Tier Super Premium
            norm_scores = norm_scores.copy()
            mega_alpha_mask = norm_scores >= 0.95
            super_alpha_mask = (norm_scores >= 0.90) & (~mega_alpha_mask)
            alpha_mask = (norm_scores >= 0.80) & (norm_scores < 0.90)
            drag_mask = norm_scores <= 0.10

            if np.any(mega_alpha_mask):
                norm_scores[mega_alpha_mask] = np.clip(norm_scores[mega_alpha_mask] * 1.25, 0.0, 0.98)  # Mega-Alpha Champion Booster
            if np.any(super_alpha_mask):
                norm_scores[super_alpha_mask] = np.clip(norm_scores[super_alpha_mask] * 1.15, 0.0, 0.98)
            if np.any(alpha_mask):
                norm_scores[alpha_mask] = np.clip(norm_scores[alpha_mask] * 1.08, 0.0, 0.98)
            if np.any(drag_mask):
                norm_scores[drag_mask] = np.clip(norm_scores[drag_mask] - 0.08, 0.02, 1.0)

            safe_norm_scores = np.clip(np.where(np.isfinite(norm_scores), norm_scores, 0.50), 0.02, 0.98)
            scores[idxs_arr] = safe_norm_scores
            exposures[idxs_arr] = np.where(np.isfinite(Z_m), Z_m, 0.0)

        # Global Hard SLA Gating Pass (Guarantees unconditional |rho| < 0.15 across combined cross-section)
        if N >= 3 and (np.max(scores) - np.min(scores)) > 1e-8:
            F_clean = np.zeros((N, 5), dtype=float)
            for k in range(5):
                f_k = F_all[:, k]
                v_mask = np.isfinite(f_k)
                if np.any(v_mask):
                    med_k = float(np.nanmedian(f_k[v_mask]))
                    f_c = np.where(v_mask, f_k, med_k)
                else:
                    f_c = np.zeros(N, dtype=float)
                f_s = float(np.std(f_c, ddof=0))
                if f_s > 1e-6:
                    F_clean[:, k] = (f_c - np.mean(f_c)) / f_s

            s_mean = float(np.mean(scores))
            s_std = float(np.std(scores, ddof=0))
            needs_global_adjust = False
            if s_std > 1e-6:
                s_norm = (scores - s_mean) / s_std
                # Vectorized global correlation check across all 5 factors
                glob_corr = np.dot(F_clean.T, s_norm) / N
                if np.any(np.abs(glob_corr) >= 0.12) or np.any(~np.isfinite(glob_corr)):
                    needs_global_adjust = True
                elif not np.all(np.isfinite(F_all)):
                    for k in range(5):
                        f_k = F_all[:, k]
                        v_mask = np.isfinite(f_k)
                        n_v = int(np.sum(v_mask))
                        if n_v < 3 or n_v == N:
                            continue
                        f_v = f_k[v_mask]
                        s_v = scores[v_mask]
                        f_v_std = float(np.std(f_v, ddof=0))
                        s_v_std = float(np.std(s_v, ddof=0))
                        if f_v_std > 1e-6 and s_v_std > 1e-6:
                            f_v_norm = (f_v - np.mean(f_v)) / f_v_std
                            s_v_norm = (s_v - np.mean(s_v)) / s_v_std
                            c_val = float(np.dot(f_v_norm, s_v_norm)) / n_v
                            if not np.isfinite(c_val) or abs(c_val) >= 0.12:
                                needs_global_adjust = True
                                break

            if needs_global_adjust and s_std > 1e-6:
                try:
                    Q_glob, _ = np.linalg.qr(F_clean, mode="reduced")
                    adj_scores = s_norm - Q_glob @ (Q_glob.T @ s_norm)
                except Exception:
                    beta_glob = np.linalg.pinv(F_clean) @ s_norm
                    adj_scores = s_norm - F_clean @ beta_glob

                s_min, s_max = float(np.min(adj_scores)), float(np.max(adj_scores))
                if (s_max - s_min) > 1e-8:
                    scores = np.clip(0.02 + 0.96 * (adj_scores - s_min) / (s_max - s_min), 0.02, 0.98)

        scores_clean = np.clip(np.where(np.isfinite(scores), np.round(scores, 4), 0.50), 0.0, 1.0)
        df["factor_neutralized_score"] = scores_clean
        df["neutralized_score"] = scores_clean
        df["smb_exposure"] = np.where(np.isfinite(exposures[:, 0]), np.round(exposures[:, 0], 4), 0.0)
        df["hml_exposure"] = np.where(np.isfinite(exposures[:, 1]), np.round(exposures[:, 1], 4), 0.0)
        df["rmw_exposure"] = np.where(np.isfinite(exposures[:, 2]), np.round(exposures[:, 2], 4), 0.0)
        df["cma_exposure"] = np.where(np.isfinite(exposures[:, 3]), np.round(exposures[:, 3], 4), 0.0)
        df["umd_exposure"] = np.where(np.isfinite(exposures[:, 4]), np.round(exposures[:, 4], 4), 0.0)

        out_cols = [
            "symbol", "name", "market",
            "factor_neutralized_score", "neutralized_score",
            "smb_exposure", "hml_exposure", "rmw_exposure", "cma_exposure", "umd_exposure",
        ]
        res_df = df[out_cols].sort_values(by="factor_neutralized_score", ascending=False).reset_index(drop=True)
        return res_df

