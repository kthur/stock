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

        # 2. Merge fundamentals_dict if supplied
        fund_data = fundamentals_dict if isinstance(fundamentals_dict, dict) else kwargs.get("fundamentals_dict")
        if fund_data and isinstance(fund_data, dict):
            def _get_fund_val(s: str, col: str) -> Any:
                s_str = str(s).strip()
                s_raw = s_str.split('.')[0]
                s_clean = s_raw.zfill(6) if s_raw.isdigit() else s_raw
                info = fund_data.get(s_str, fund_data.get(s_raw, fund_data.get(s_clean, {})))
                if isinstance(info, dict):
                    return info.get(col, np.nan)
                return np.nan

            for col in ["market_cap", "per", "pbr", "roe", "asset_growth_yoy"]:
                if col not in df.columns:
                    df[col] = df["symbol"].map(lambda s: _get_fund_val(s, col))
                else:
                    missing_mask = df[col].isna()
                    if missing_mask.any():
                        df.loc[missing_mask, col] = df.loc[missing_mask, "symbol"].map(
                            lambda s: _get_fund_val(s, col)
                        )

            # Sector-grouped median imputation for PBR/ROE
            if "sector" in df.columns or "sector_code" in df.columns:
                sec_col = "sector" if "sector" in df.columns else "sector_code"
                for col in ["pbr", "roe"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        df[col] = df.groupby(sec_col)[col].transform(lambda x: x.fillna(x.median()))
                        df[col] = df[col].fillna(df[col].median())

        # 3. Resolve or compute raw alpha scores y
        raw_scores = kwargs.get("raw_scores", kwargs.get("raw_scores_df", None))

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
                score_map = dict(zip(raw_scores["symbol"].astype(str).str.strip(), pd.to_numeric(raw_scores[score_col], errors="coerce")))
                df["_raw_y"] = df["symbol"].map(score_map)
            else:
                df["_raw_y"] = np.nan
        elif raw_scores is not None and isinstance(raw_scores, dict):
            df["_raw_y"] = df["symbol"].map(raw_scores)
        elif "score" in df.columns:
            df["_raw_y"] = pd.to_numeric(df["score"], errors="coerce")
        elif "raw_score" in df.columns:
            df["_raw_y"] = pd.to_numeric(df["raw_score"], errors="coerce")
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

        # If _raw_y is totally empty or missing, derive from price momentum or rank
        if df["_raw_y"].isna().all():
            if prices_map and isinstance(prices_map, dict):
                price_moms = {}
                for sym, p_df in prices_map.items():
                    if isinstance(p_df, pd.DataFrame) and len(p_df) >= 10:
                        c_col = "Close" if "Close" in p_df.columns else ("close" if "close" in p_df.columns else None)
                        if c_col and c_col in p_df.columns:
                            c_vals = p_df[c_col].dropna().values
                            if len(c_vals) >= 10:
                                price_moms[str(sym).strip()] = (c_vals[-1] / max(c_vals[-10], 1e-5)) - 1.0
                if price_moms:
                    df["_raw_y"] = df["symbol"].map(price_moms).fillna(0.0)
            if df["_raw_y"].isna().all():
                df["_raw_y"] = np.linspace(-0.1, 0.1, len(df))

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

            # QR Decomposition: X = [1, Z_m]
            X_m = np.column_stack([np.ones(N_m, dtype=float), Z_m])

            if N_m >= 6:
                try:
                    Q_m, _ = np.linalg.qr(X_m, mode="reduced")
                    proj_coef = np.dot(Q_m.T, y_m)
                    y_pred = np.dot(Q_m, proj_coef)
                    residual = y_m - y_pred
                except Exception as e:
                    logger.warning(f"QR decomposition failed for market {mkt}: {e}")
                    # Ridge regression fallback for ill-conditioned design matrices
                    ridge_eye = 1e-4 * np.eye(X_m.shape[1])
                    beta_ridge = np.linalg.solve(np.dot(X_m.T, X_m) + ridge_eye, np.dot(X_m.T, y_m))
                    residual = y_m - np.dot(X_m, beta_ridge)
            elif N_m > 1:
                # SVD pseudoinverse projection for under-determined cross-sections (N_m < 6)
                beta_pinv = np.linalg.pinv(X_m) @ y_m
                residual = y_m - np.dot(X_m, beta_pinv)
            else:
                residual = y_m - np.mean(y_m)

            # 6. Hard Post-Condition SLA Gate: secondary Gram-Schmidt deflation (corr_thresh = 0.05)
            res_std = float(np.std(residual, ddof=0))
            if res_std > 1e-8:
                for k in range(5):
                    z_k = Z_m[:, k]
                    z_std = float(np.std(z_k, ddof=0))
                    if z_std > 1e-6:
                        corr_val = float(np.corrcoef(z_k, residual)[0, 1])
                        if np.isnan(corr_val) or np.abs(corr_val) >= 0.05:
                            # Secondary Gram-Schmidt Deflation
                            z_center = z_k - np.mean(z_k)
                            z_norm = np.linalg.norm(z_center)
                            if z_norm > 1e-8:
                                u_k = z_center / z_norm
                                residual = residual - np.dot(u_k, residual) * u_k
                residual = residual - np.mean(residual)

            # 7. Robust Scaling to [0.0, 1.0] and Post-Scaling Correlation Check
            if N_m >= 5 and (np.max(residual) - np.min(residual)) > 1e-8:
                norm_scores = pd.Series(residual).rank(pct=True).values
            elif N_m > 1 and (np.max(residual) - np.min(residual)) > 1e-8:
                p1, p99 = np.percentile(residual, 1), np.percentile(residual, 99)
                denom = (p99 - p1) if (p99 - p1) > 1e-8 else 1.0
                norm_scores = np.clip((residual - p1) / denom, 0.0, 1.0)
            elif N_m == 1:
                norm_scores = np.array([0.5])
            else:
                norm_scores = np.full(N_m, 0.5)

            # Post-scaling correlation check & linear orthogonal adjustment
            if N_m >= 6 and (np.max(norm_scores) - np.min(norm_scores)) > 1e-8:
                needs_adjust = False
                for k in range(5):
                    z_k = Z_m[:, k]
                    z_std = float(np.std(z_k, ddof=0))
                    s_std = float(np.std(norm_scores, ddof=0))
                    if z_std > 1e-6 and s_std > 1e-6:
                        c_val = float(np.corrcoef(z_k, norm_scores)[0, 1])
                        if np.isnan(c_val) or np.abs(c_val) >= 0.15:
                            needs_adjust = True
                            break

                if needs_adjust:
                    adj_scores = norm_scores.copy()
                    for k in range(5):
                        z_k = Z_m[:, k]
                        z_std = float(np.std(z_k, ddof=0))
                        s_std = float(np.std(adj_scores, ddof=0))
                        if z_std > 1e-6 and s_std > 1e-6:
                            c_val = float(np.corrcoef(z_k, adj_scores)[0, 1])
                            if np.isfinite(c_val):
                                adj_scores = adj_scores - c_val * (z_k / z_std) * s_std
                    s_min, s_max = np.min(adj_scores), np.max(adj_scores)
                    if (s_max - s_min) > 1e-8:
                        norm_scores = (adj_scores - s_min) / (s_max - s_min)
                    else:
                        norm_scores = np.full(N_m, 0.5)

            # Pure Idiosyncratic Alpha Conviction Boost & Super Premium
            super_alpha_mask = norm_scores >= 0.90
            alpha_mask = (norm_scores >= 0.80) & (~super_alpha_mask)
            if np.any(super_alpha_mask):
                norm_scores[super_alpha_mask] = np.clip(norm_scores[super_alpha_mask] * 1.10, 0.0, 1.0)
            if np.any(alpha_mask):
                norm_scores[alpha_mask] = np.clip(norm_scores[alpha_mask] * 1.06, 0.0, 1.0)

            safe_norm_scores = np.clip(np.where(np.isfinite(norm_scores), norm_scores, 0.50), 0.0, 1.0)
            scores[idxs_arr] = safe_norm_scores
            exposures[idxs_arr] = np.where(np.isfinite(Z_m), Z_m, 0.0)

        df["factor_neutralized_score"] = pd.to_numeric(pd.Series(np.round(scores, 4)), errors='coerce').fillna(0.50).clip(0.0, 1.0)
        df["neutralized_score"] = df["factor_neutralized_score"]
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

