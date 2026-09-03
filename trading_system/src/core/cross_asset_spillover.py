"""
cross_asset_spillover.py — Cross-Asset Spillover Momentum Strategy Engine.

Calculates sector sensitivity vectors, global macro impulse (USD/KRW, TNX, WTI, Gold, DXY,
VIX, SOX, S&P 500), and unpriced lead-lag spillover diffusion into equity prices.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from .base_strategy import BaseStrategyEngine, make_score_dataframe
from src.core.strategy_registry import register_strategy, StrategyMeta

logger = logging.getLogger(__name__)

# Sector Elasticity Coefficients across Global Macro Drivers (SOX, FX, WTI, TNX, VIX, Gold, DXY, SP500)
# Positive = Sector thrives on factor appreciation / growth; Negative = Sector suffers from factor rise.
DEFAULT_SECTOR_MACRO_BETAS: Dict[str, Dict[str, float]] = {
    # Semiconductor & Hardware
    "Semiconductor": {"sox": 1.60, "usdkrw": 0.80, "tnx": -0.50, "wti": -0.20, "vix": -1.20, "sp500": 1.30, "gold": 0.00, "dxy": 0.30},
    "반도체": {"sox": 1.60, "usdkrw": 0.80, "tnx": -0.50, "wti": -0.20, "vix": -1.20, "sp500": 1.30, "gold": 0.00, "dxy": 0.30},
    "Information Technology": {"sox": 1.40, "usdkrw": 0.70, "tnx": -0.70, "wti": -0.20, "vix": -1.10, "sp500": 1.30, "gold": -0.10, "dxy": 0.20},
    "Tech": {"sox": 1.40, "usdkrw": 0.70, "tnx": -0.70, "wti": -0.20, "vix": -1.10, "sp500": 1.30, "gold": -0.10, "dxy": 0.20},
    "IT": {"sox": 1.40, "usdkrw": 0.70, "tnx": -0.70, "wti": -0.20, "vix": -1.10, "sp500": 1.30, "gold": -0.10, "dxy": 0.20},
    "전기전자": {"sox": 1.50, "usdkrw": 0.85, "tnx": -0.60, "wti": -0.20, "vix": -1.15, "sp500": 1.30, "gold": 0.00, "dxy": 0.30},
    "IT하드웨어": {"sox": 1.35, "usdkrw": 0.75, "tnx": -0.65, "wti": -0.20, "vix": -1.10, "sp500": 1.25, "gold": -0.10, "dxy": 0.20},
    "IT소프트웨어": {"sox": 0.80, "usdkrw": 0.30, "tnx": -0.90, "wti": -0.10, "vix": -1.00, "sp500": 1.20, "gold": -0.10, "dxy": 0.10},

    # Energy & Commodities
    "Energy": {"sox": 0.10, "usdkrw": 0.20, "tnx": 0.50, "wti": 1.80, "vix": -0.70, "sp500": 0.80, "gold": 0.40, "dxy": -0.50},
    "Oil & Gas": {"sox": 0.10, "usdkrw": 0.20, "tnx": 0.50, "wti": 1.80, "vix": -0.70, "sp500": 0.80, "gold": 0.40, "dxy": -0.50},
    "정유": {"sox": 0.10, "usdkrw": 0.30, "tnx": 0.40, "wti": 1.70, "vix": -0.70, "sp500": 0.80, "gold": 0.30, "dxy": -0.40},
    "에너지": {"sox": 0.10, "usdkrw": 0.20, "tnx": 0.50, "wti": 1.80, "vix": -0.70, "sp500": 0.80, "gold": 0.40, "dxy": -0.50},
    "Materials": {"sox": 0.30, "usdkrw": 0.40, "tnx": 0.20, "wti": 0.90, "vix": -0.80, "sp500": 0.90, "gold": 1.10, "dxy": -0.60},
    "Chemical": {"sox": 0.30, "usdkrw": 0.40, "tnx": 0.20, "wti": 0.90, "vix": -0.80, "sp500": 0.90, "gold": 0.50, "dxy": -0.50},
    "화학": {"sox": 0.30, "usdkrw": 0.40, "tnx": 0.20, "wti": 0.90, "vix": -0.80, "sp500": 0.90, "gold": 0.50, "dxy": -0.50},
    "철강및금속": {"sox": 0.20, "usdkrw": 0.30, "tnx": 0.30, "wti": 0.70, "vix": -0.80, "sp500": 0.85, "gold": 0.90, "dxy": -0.60},
    "Steel": {"sox": 0.20, "usdkrw": 0.30, "tnx": 0.30, "wti": 0.70, "vix": -0.80, "sp500": 0.85, "gold": 0.90, "dxy": -0.60},

    # Financials
    "Financials": {"sox": 0.20, "usdkrw": -0.30, "tnx": 1.30, "wti": 0.30, "vix": -0.90, "sp500": 1.00, "gold": 0.10, "dxy": 0.30},
    "Finance": {"sox": 0.20, "usdkrw": -0.30, "tnx": 1.30, "wti": 0.30, "vix": -0.90, "sp500": 1.00, "gold": 0.10, "dxy": 0.30},
    "금융업": {"sox": 0.20, "usdkrw": -0.30, "tnx": 1.30, "wti": 0.30, "vix": -0.90, "sp500": 1.00, "gold": 0.10, "dxy": 0.30},
    "은행": {"sox": 0.10, "usdkrw": -0.40, "tnx": 1.40, "wti": 0.20, "vix": -0.85, "sp500": 0.90, "gold": 0.00, "dxy": 0.30},
    "증권": {"sox": 0.40, "usdkrw": -0.20, "tnx": 0.60, "wti": 0.10, "vix": -1.30, "sp500": 1.40, "gold": -0.10, "dxy": 0.10},
    "보험": {"sox": 0.10, "usdkrw": -0.20, "tnx": 1.20, "wti": 0.20, "vix": -0.70, "sp500": 0.80, "gold": 0.10, "dxy": 0.20},

    # Industrials, Auto, Defense & Shipbuilding
    "Industrials": {"sox": 0.50, "usdkrw": 0.80, "tnx": 0.20, "wti": -0.30, "vix": -0.90, "sp500": 1.10, "gold": 0.00, "dxy": 0.30},
    "Automotive": {"sox": 0.60, "usdkrw": 1.20, "tnx": 0.10, "wti": -0.50, "vix": -0.95, "sp500": 1.15, "gold": -0.10, "dxy": 0.40},
    "운수장비": {"sox": 0.55, "usdkrw": 1.15, "tnx": 0.15, "wti": -0.40, "vix": -0.90, "sp500": 1.10, "gold": 0.00, "dxy": 0.40},
    "기계": {"sox": 0.60, "usdkrw": 0.80, "tnx": 0.30, "wti": 0.10, "vix": -0.90, "sp500": 1.10, "gold": 0.10, "dxy": 0.30},
    "Defense": {"sox": 0.30, "usdkrw": 0.90, "tnx": 0.40, "wti": 0.20, "vix": 0.20, "sp500": 0.90, "gold": 0.50, "dxy": 0.40},
    "방산": {"sox": 0.30, "usdkrw": 0.90, "tnx": 0.40, "wti": 0.20, "vix": 0.20, "sp500": 0.90, "gold": 0.50, "dxy": 0.40},
    "Shipbuilding": {"sox": 0.30, "usdkrw": 1.00, "tnx": 0.30, "wti": 0.80, "vix": -0.80, "sp500": 1.00, "gold": 0.20, "dxy": 0.40},
    "조선": {"sox": 0.30, "usdkrw": 1.00, "tnx": 0.30, "wti": 0.80, "vix": -0.80, "sp500": 1.00, "gold": 0.20, "dxy": 0.40},

    # Bio & Healthcare
    "Health Care": {"sox": 0.10, "usdkrw": 0.10, "tnx": -1.10, "wti": -0.20, "vix": -0.60, "sp500": 0.75, "gold": 0.20, "dxy": -0.10},
    "Healthcare": {"sox": 0.10, "usdkrw": 0.10, "tnx": -1.10, "wti": -0.20, "vix": -0.60, "sp500": 0.75, "gold": 0.20, "dxy": -0.10},
    "Biotechnology": {"sox": 0.30, "usdkrw": 0.20, "tnx": -1.40, "wti": -0.20, "vix": -0.90, "sp500": 0.90, "gold": 0.30, "dxy": -0.10},
    "의약품": {"sox": 0.10, "usdkrw": 0.10, "tnx": -1.00, "wti": -0.20, "vix": -0.60, "sp500": 0.75, "gold": 0.20, "dxy": -0.10},
    "바이오": {"sox": 0.30, "usdkrw": 0.20, "tnx": -1.40, "wti": -0.20, "vix": -0.90, "sp500": 0.90, "gold": 0.30, "dxy": -0.10},

    # Consumer & Defensive
    "Consumer Discretionary": {"sox": 0.50, "usdkrw": -0.30, "tnx": -0.50, "wti": -0.60, "vix": -1.00, "sp500": 1.15, "gold": -0.20, "dxy": -0.10},
    "유통업": {"sox": 0.10, "usdkrw": -0.60, "tnx": -0.30, "wti": -0.50, "vix": -0.70, "sp500": 0.70, "gold": -0.10, "dxy": -0.30},
    "Consumer Staples": {"sox": 0.00, "usdkrw": -0.60, "tnx": -0.20, "wti": -0.40, "vix": -0.30, "sp500": 0.50, "gold": 0.10, "dxy": -0.20},
    "음식료품": {"sox": 0.00, "usdkrw": -0.70, "tnx": -0.20, "wti": -0.50, "vix": -0.30, "sp500": 0.50, "gold": 0.10, "dxy": -0.30},
    "Utilities": {"sox": 0.00, "usdkrw": -0.80, "tnx": -0.90, "wti": -0.90, "vix": -0.20, "sp500": 0.40, "gold": 0.20, "dxy": -0.40},
    "전기가스업": {"sox": 0.00, "usdkrw": -0.90, "tnx": -0.80, "wti": -1.00, "vix": -0.20, "sp500": 0.40, "gold": 0.20, "dxy": -0.50},
    "통신업": {"sox": 0.10, "usdkrw": -0.50, "tnx": -0.50, "wti": -0.20, "vix": -0.30, "sp500": 0.50, "gold": 0.10, "dxy": -0.20},
    "Communication": {"sox": 0.60, "usdkrw": 0.10, "tnx": -0.60, "wti": -0.20, "vix": -0.90, "sp500": 1.05, "gold": -0.10, "dxy": 0.00},
    "서비스업": {"sox": 0.50, "usdkrw": 0.10, "tnx": -0.60, "wti": -0.20, "vix": -0.90, "sp500": 1.00, "gold": -0.10, "dxy": 0.00},

    # Market Baseline Default
    "Market": {"sox": 0.50, "usdkrw": 0.20, "tnx": 0.00, "wti": 0.10, "vix": -0.80, "sp500": 1.00, "gold": 0.10, "dxy": 0.00},
}


@register_strategy(
    StrategyMeta(
        strategy_id="cross_asset_spillover",
        display_name="Cross-Asset Spillover Momentum",
        score_column="cross_asset_spillover_score",
        category="cross_asset",
        output_file="cross_asset_spillover_predictions.txt",
        requires_indicators=True,
        default_regime_weights={
            "BEAR_LOW_VOL": 0.03,
            "BEAR_HIGH_VOL": 0.04,
            "SIDEWAYS_LOW_VOL": 0.03,
            "SIDEWAYS_HIGH_VOL": 0.03,
            "BULL_LOW_VOL": 0.04,
            "BULL_HIGH_VOL": 0.04,
            "BEAR": 0.03,
            "SIDEWAYS": 0.03,
            "BULL": 0.04,
        },
    )
)
class CrossAssetSpilloverEngine(BaseStrategyEngine):
    """
    Cross-Asset Spillover Momentum Strategy Engine.

    Calculates sector-level macro sensitivities across 8 key global macro factors
    (USD/KRW, TNX, WTI, Gold, DXY, VIX, SOX, S&P 500), evaluates macro impulse tailwinds,
    and identifies unpriced lead-lag diffusion gaps in individual stock prices.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        super().__init__(name="CrossAssetSpilloverEngine", config=config)

    def _extract_macro_vector(self, indicators_df: Optional[Any], is_krx: bool = False) -> Dict[str, float]:
        """
        Extracts multi-horizon macro returns/changes for:
        ['sox', 'usdkrw', 'tnx', 'wti', 'gold', 'dxy', 'vix', 'sp500']
        """
        keys = ["sox", "usdkrw", "tnx", "wti", "gold", "dxy", "vix", "sp500"]
        macro_ret: Dict[str, float] = {k: 0.0 for k in keys}

        if indicators_df is None:
            return macro_ret

        # Column alias candidate map
        col_aliases: Dict[str, List[str]] = {
            "sox": ["sox_change", "sox_pct", "sox", "SOX", "SOXX", "semiconductor_index"],
            "usdkrw": ["usdkrw_change", "usdkrw_pct", "usdkrw", "USDKRW", "usd_krw", "USD_KRW"],
            "tnx": ["tnx_change", "tnx_pct", "tnx", "TNX", "us10y", "yield_10y", "treasury_10y"],
            "wti": ["wti_change", "wti_pct", "wti", "WTI", "crude_oil", "oil", "CL=F"],
            "gold": ["gold_change", "gold_pct", "gold", "GOLD", "GC=F"],
            "dxy": ["dxy_change", "dxy_pct", "dxy", "DXY", "DX-Y.NYB", "dollar_index"],
            "vix": ["vix_change", "vix_pct", "vix", "VIX", "^VIX", "vix_raw"],
            "sp500": ["sp500_change", "sp500_pct", "sp500", "spx", "SP500", "^GSPC", "spy"],
        }

        if isinstance(indicators_df, dict):
            for k, aliases in col_aliases.items():
                for alias in aliases:
                    if alias in indicators_df:
                        val = indicators_df[alias]
                        if val is not None:
                            try:
                                f_val = float(val)
                                if np.isfinite(f_val):
                                    # Normalize percentage scale (e.g., 1.5% -> 0.015 if given in %)
                                    if abs(f_val) > 0.50:
                                        macro_ret[k] = f_val / 100.0
                                    else:
                                        macro_ret[k] = f_val
                                    break
                            except (ValueError, TypeError):
                                pass
            return macro_ret

        if isinstance(indicators_df, pd.DataFrame) and not indicators_df.empty:
            for k, aliases in col_aliases.items():
                matched_col = None
                for alias in aliases:
                    if alias in indicators_df.columns:
                        matched_col = alias
                        break

                if matched_col is not None:
                    series = indicators_df[matched_col].dropna()
                    if not series.empty:
                        # For KRX equities, apply a 1-day lag to US-origin macro series (SP500, SOX, VIX, etc.)
                        # to eliminate the ~14.5 hour timezone lookahead bias.
                        is_us_macro = k in ["sox", "sp500", "vix", "tnx", "wti", "gold", "dxy"]
                        use_lag = is_krx and is_us_macro and len(series) >= 2
                        
                        # If series is already a change / return column
                        if "change" in matched_col.lower() or "pct" in matched_col.lower():
                            val = float(series.iloc[-2] if use_lag else series.iloc[-1])
                            macro_ret[k] = val / 100.0 if abs(val) > 0.50 else val
                        else:
                            # Series of raw prices/levels -> compute 1d, 3d, 5d returns if sufficient history
                            offset = 1 if use_lag else 0
                            min_len = 6 + offset
                            if len(series) >= min_len:
                                idx_now = -1 - offset
                                idx_1d = -2 - offset
                                idx_3d = -4 - offset
                                idx_5d = -6 - offset
                                r1 = (float(series.iloc[idx_now]) / float(series.iloc[idx_1d])) - 1.0 if float(series.iloc[idx_1d]) > 0 else 0.0
                                r3 = (float(series.iloc[idx_now]) / float(series.iloc[idx_3d])) - 1.0 if float(series.iloc[idx_3d]) > 0 else 0.0
                                r5 = (float(series.iloc[idx_now]) / float(series.iloc[idx_5d])) - 1.0 if float(series.iloc[idx_5d]) > 0 else 0.0
                                macro_ret[k] = 0.50 * r1 + 0.30 * r3 + 0.20 * r5
                            elif len(series) >= (2 + offset):
                                idx_now = -1 - offset
                                idx_1d = -2 - offset
                                r1 = (float(series.iloc[idx_now]) / float(series.iloc[idx_1d])) - 1.0 if float(series.iloc[idx_1d]) > 0 else 0.0
                                macro_ret[k] = r1
                            else:
                                macro_ret[k] = 0.0

        return macro_ret

    def calculate_scores(
        self,
        symbols: Optional[List[str]] = None,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        macro_df: Optional[Any] = None,
        indicators_df: Optional[Any] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Universal calculate_scores method compatible with all test suites and pipeline runners."""
        if prices_dict is None and isinstance(symbols, dict):
            prices_dict = symbols
            symbols = None
        if symbols is not None and prices_dict is not None:
            prices_dict = {s: prices_dict[s] for s in symbols if s in prices_dict}
        ind_df = indicators_df if indicators_df is not None else macro_df
        return self.compute_scores(prices_dict=prices_dict, indicators_df=ind_df, **kwargs)

    def compute_scores(
        self,
        prices_dict: Any,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Computes Cross-Asset Spillover Momentum score for all symbols.

        Returns:
            pd.DataFrame / ScoreDataFrame with ['symbol', 'cross_asset_spillover_score']
        """
        # Handle parameter swaps or alternative kwargs
        if isinstance(prices_dict, pd.DataFrame) and isinstance(fundamentals_dict, dict) and "Close" not in prices_dict.columns and "close" not in prices_dict.columns:
            # Swapped dict
            indicator_source = prices_dict
            prices_source = fundamentals_dict
        else:
            indicator_source = indicators_df if indicators_df is not None else kwargs.get("indicator_df", kwargs.get("macro_indicators"))
            prices_source = kwargs.get("df_prices", prices_dict)

        sector_map: Dict[str, str] = kwargs.get("sector_map") or {}

        if not prices_source:
            return make_score_dataframe({}, score_column="cross_asset_spillover_score")

        macro_vector_global = self._extract_macro_vector(indicator_source, is_krx=False)
        macro_vector_krx = self._extract_macro_vector(indicator_source, is_krx=True)
        macro_active_global = any(abs(v) > 1e-6 for v in macro_vector_global.values())
        macro_active_krx = any(abs(v) > 1e-6 for v in macro_vector_krx.values())

        scores: Dict[str, float] = {}

        if isinstance(prices_source, dict):
            symbols = list(prices_source.keys())
        elif isinstance(prices_source, pd.DataFrame):
            if "symbol" in prices_source.columns:
                symbols = prices_source["symbol"].dropna().astype(str).unique().tolist()
            else:
                symbols = list(prices_source.columns)
        else:
            symbols = []

        for sym in symbols:
            sym_str = str(sym).strip()
            is_krx_sym = sym_str.isdigit() or sym_str.endswith(('.KS', '.KQ'))
            macro_vector = macro_vector_krx if is_krx_sym else macro_vector_global
            macro_active = macro_active_krx if is_krx_sym else macro_active_global

            df_ohlcv = self.extract_ohlcv(sym_str, prices_source if isinstance(prices_source, dict) else {sym_str: prices_source}, min_bars=5)

            if df_ohlcv is None or df_ohlcv.empty or len(df_ohlcv) < 5:
                scores[sym_str] = 0.50
                continue

            try:
                close_s = pd.to_numeric(df_ohlcv["Close"], errors="coerce").dropna()
                if len(close_s) < 5:
                    scores[sym_str] = 0.50
                    continue

                # Stock multi-horizon returns
                c_now = float(close_s.iloc[-1])
                c_1d = float(close_s.iloc[-2]) if len(close_s) >= 2 else c_now
                c_3d = float(close_s.iloc[-4]) if len(close_s) >= 4 else c_1d
                c_5d = float(close_s.iloc[-5]) if len(close_s) >= 5 else c_3d

                r1 = (c_now / c_1d - 1.0) if c_1d > 0 else 0.0
                r3 = (c_now / c_3d - 1.0) if c_3d > 0 else 0.0
                r5 = (c_now / c_5d - 1.0) if c_5d > 0 else 0.0

                stock_eff_ret = 0.50 * r1 + 0.30 * r3 + 0.20 * r5
                if not np.isfinite(stock_eff_ret):
                    stock_eff_ret = 0.0

                if not macro_active:
                    # Fallback when no macro indicators available: mild return momentum
                    fallback_score = float(np.clip(0.50 + stock_eff_ret * 2.0, 0.05, 0.95))
                    if not np.isfinite(fallback_score):
                        fallback_score = 0.50
                    scores[sym_str] = round(fallback_score, 4)
                    continue

                # Determine sector and beta vector
                sec = sector_map.get(sym_str, sector_map.get(sym, "Market"))
                beta_map = DEFAULT_SECTOR_MACRO_BETAS.get(sec, DEFAULT_SECTOR_MACRO_BETAS.get(str(sec).strip(), DEFAULT_SECTOR_MACRO_BETAS["Market"]))

                # Calculate Macro Impulse I_i(t)
                macro_impulse = sum(beta_map.get(factor, 0.0) * ret_val for factor, ret_val in macro_vector.items())
                if not np.isfinite(macro_impulse):
                    macro_impulse = 0.0

                # Lead-Lag Diffusion / Unpriced Macro Tailwind Gap
                # Positive delta means macro tailwind is ahead of the stock's recent price reaction
                gamma = 0.70
                delta_spillover = macro_impulse - (gamma * stock_eff_ret)

                # Macro-Trend Coherence Adjustment:
                # 1. Amplification when macro impulse & stock momentum are constructively aligned
                # 2. Dampening when stock is heavily breaking down despite macro tailwinds (idiosyncratic risk)
                if macro_impulse > 0 and stock_eff_ret >= 0:
                    coherence_mult = 1.0 + 0.50 * min(1.0, stock_eff_ret / 0.04)
                    delta_spillover *= coherence_mult
                elif macro_impulse > 0 and stock_eff_ret < -0.03:
                    # Decoupling penalty: idiosyncratic breakdown
                    delta_spillover *= 0.65

                if not np.isfinite(delta_spillover):
                    delta_spillover = 0.0

                # Continuous logistic mapping centered at 0.50
                # Scale factor 16.0 provides responsive sensitivity across [-0.10, +0.10] range
                clipped_exp = np.clip(-16.0 * delta_spillover, -50.0, 50.0)
                raw_score = 1.0 / (1.0 + np.exp(clipped_exp))
                if not np.isfinite(raw_score):
                    clipped_score = 0.50
                else:
                    clipped_score = float(np.clip(raw_score, 0.05, 0.95))

                if not np.isfinite(clipped_score):
                    clipped_score = 0.50

                scores[sym_str] = round(clipped_score, 4)

            except Exception as e:
                logger.debug(f"[CrossAssetSpillover] Error evaluating symbol {sym_str}: {e}")
                scores[sym_str] = 0.50

        res_df = make_score_dataframe(scores, score_column="cross_asset_spillover_score")
        if not res_df.empty:
            s_series = pd.to_numeric(res_df['cross_asset_spillover_score'], errors='coerce').fillna(0.50).clip(0.05, 0.95)
            if len(res_df) > 1:
                ranks = s_series.rank(pct=True, ascending=True)
                # Multi-Tier Cross-Asset Spillover Booster (Top 5% receives 1.15x, Top 15% receives 1.10x)
                enhanced = np.where(ranks >= 0.95, (s_series * 1.15).clip(0.05, 0.95),
                           np.where(ranks >= 0.85, (s_series * 1.10).clip(0.05, 0.95), s_series))
                res_df['cross_asset_spillover_score'] = pd.to_numeric(pd.Series(enhanced, index=res_df.index), errors='coerce').fillna(0.50).clip(0.05, 0.95)
            else:
                res_df['cross_asset_spillover_score'] = s_series
        return res_df


def cross_asset_spillover_score(
    prices_dict: Any,
    indicators_df: Optional[Any] = None,
    **kwargs: Any
) -> pd.DataFrame:
    """
    Convenience function to compute Cross-Asset Spillover Momentum scores.
    """
    engine = CrossAssetSpilloverEngine()
    return engine.compute_scores(prices_dict=prices_dict, indicators_df=indicators_df, **kwargs)
