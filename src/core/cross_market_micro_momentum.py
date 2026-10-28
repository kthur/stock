"""
src/core/cross_market_micro_momentum.py — 14.5-Hour Timezone Lead-Lag & Level-2 OFI Velocity Engine (Feature F681).

Phase 140 Release R140:
- 14.5-hour timezone lead-lag delta capturing unpriced overnight US mega-cap shocks prior to KRX opening auction:
    Delta_overnight,i = beta_i,m * R_m,US^overnight - R_i,KRX^pre-open
- Level-2 Order Flow Imbalance (OFI) velocity across top 5 price levels: w_k = [0.40, 0.25, 0.15, 0.12, 0.08].
- Canonical OHLCV opening gap and volume surge proxy (OFI_Proxy) for historical backtests without tick stream.
- Directional Coherence alignment bonus (+0.025 / -0.025).
- Continuous logistic activation bounded strictly in [0.05, 0.95], zero NaNs, zero synthetic rows.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from .base_strategy import BaseStrategyEngine, ScoreDataFrame, make_score_dataframe
from src.core.strategy_registry import register_strategy, StrategyMeta

logger = logging.getLogger(__name__)

# Metadata Constants
VERSION: int = 140
RELEASE: str = "R140"
FEATURE: str = "F681"

# Sector-specific US benchmark drivers & default betas
SECTOR_BENCHMARK_DRIVERS: Dict[str, Dict[str, Any]] = {
    "Semiconductor": {"us_lead": "NVDA", "us_macro": "sox", "beta": 1.45},
    "반도체": {"us_lead": "NVDA", "us_macro": "sox", "beta": 1.45},
    "IT": {"us_lead": "AAPL", "us_macro": "sp500", "beta": 1.25},
    "전기전자": {"us_lead": "NVDA", "us_macro": "sox", "beta": 1.35},
    "Automotive": {"us_lead": "TSLA", "us_macro": "sp500", "beta": 1.15},
    "운수장비": {"us_lead": "TSLA", "us_macro": "sp500", "beta": 1.15},
    "Secondary Battery": {"us_lead": "TSLA", "us_macro": "sp500", "beta": 1.30},
    "2차전지": {"us_lead": "TSLA", "us_macro": "sp500", "beta": 1.30},
    "Defense": {"us_lead": "LMT", "us_macro": "sp500", "beta": 0.95},
    "방산": {"us_lead": "LMT", "us_macro": "sp500", "beta": 0.95},
    "Bio / Healthcare": {"us_lead": "LLY", "us_macro": "sp500", "beta": 0.85},
    "의약품": {"us_lead": "LLY", "us_macro": "sp500", "beta": 0.85},
    "Energy": {"us_lead": "XOM", "us_macro": "wti", "beta": 1.20},
    "Market": {"us_lead": "SPY", "us_macro": "sp500", "beta": 1.00},
}

# Specific leader symbol overrides
SYMBOL_BENCHMARK_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "000660": {"us_lead": "NVDA", "us_macro": "sox", "beta": 1.50},  # SK Hynix
    "005930": {"us_lead": "MU", "us_macro": "sox", "beta": 1.35},    # Samsung Electronics
    "042700": {"us_lead": "NVDA", "us_macro": "sox", "beta": 1.65},  # Hanmi Semi
    "373220": {"us_lead": "TSLA", "us_macro": "sp500", "beta": 1.35}, # LG Energy Solution
    "005380": {"us_lead": "TSLA", "us_macro": "sp500", "beta": 1.15}, # Hyundai Motor
    "012450": {"us_lead": "LMT", "us_macro": "sp500", "beta": 1.10},  # Hanwha Aerospace
    "267260": {"us_lead": "GE", "us_macro": "sp500", "beta": 1.25},   # HD Hyundai Electric
    "010120": {"us_lead": "ETN", "us_macro": "sp500", "beta": 1.20},  # LS Electric
    "207940": {"us_lead": "LLY", "us_macro": "sp500", "beta": 0.90},  # Samsung Biologics
}

OFI_DEPTH_WEIGHTS: np.ndarray = np.array([0.40, 0.25, 0.15, 0.12, 0.08], dtype=np.float64)


def compute_overnight_tailwind_delta(
    r_us_overnight: float,
    r_krx_preopen: float,
    beta: float = 1.0,
) -> float:
    """
    Computes unpriced overnight tailwind delta:
        Delta_overnight = beta * R_US_overnight - R_KRX_preopen
    """
    if not np.isfinite(r_us_overnight):
        r_us_overnight = 0.0
    if not np.isfinite(r_krx_preopen):
        r_krx_preopen = 0.0
    if not np.isfinite(beta):
        beta = 1.0
    return float(beta * r_us_overnight - r_krx_preopen)


def compute_level2_ofi_velocity(
    bid_prices: np.ndarray,
    bid_sizes: np.ndarray,
    ask_prices: np.ndarray,
    ask_sizes: np.ndarray,
    prev_bid_prices: Optional[np.ndarray] = None,
    prev_bid_sizes: Optional[np.ndarray] = None,
    prev_ask_prices: Optional[np.ndarray] = None,
    prev_ask_sizes: Optional[np.ndarray] = None,
    mean_ofi: float = 0.0,
    std_ofi: float = 1.0,
) -> float:
    """
    Computes 5-depth Level-2 Order Flow Imbalance (OFI) standardized velocity.
    Weights: w_k = [0.40, 0.25, 0.15, 0.12, 0.08].
    Guarantees Zero-NaN and eliminates divide-by-zero warnings under corrupted feeds.
    """
    try:
        lengths = [
            len(bid_prices) if bid_prices is not None else 0,
            len(bid_sizes) if bid_sizes is not None else 0,
            len(ask_prices) if ask_prices is not None else 0,
            len(ask_sizes) if ask_sizes is not None else 0,
        ]
        if prev_bid_prices is not None:
            lengths.append(len(prev_bid_prices))
        if prev_bid_sizes is not None:
            lengths.append(len(prev_bid_sizes))
        if prev_ask_prices is not None:
            lengths.append(len(prev_ask_prices))
        if prev_ask_sizes is not None:
            lengths.append(len(prev_ask_sizes))

        k_levels = min(5, min(lengths)) if lengths else 0
        if k_levels <= 0:
            return 0.0

        # Sanitize current arrays: convert to float64, replace NaNs/Infs with 0.0, clamp sizes >= 0.0
        bp = np.nan_to_num(np.asarray(bid_prices[:k_levels], dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0)
        bs = np.maximum(np.nan_to_num(np.asarray(bid_sizes[:k_levels], dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0), 0.0)
        ap = np.nan_to_num(np.asarray(ask_prices[:k_levels], dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0)
        as_ = np.maximum(np.nan_to_num(np.asarray(ask_sizes[:k_levels], dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0), 0.0)

        w = OFI_DEPTH_WEIGHTS[:k_levels]
        w_sum = np.sum(w)
        w = w / (w_sum if w_sum > 0 else 1.0)

        if prev_bid_prices is None or prev_ask_prices is None:
            # Single-snapshot fallback: net imbalance of current book
            sum_sizes = np.maximum(bs + as_, 1e-6)
            net_q = (bs - as_) / sum_sizes
            net_q = np.nan_to_num(net_q, nan=0.0, posinf=0.0, neginf=0.0)
            raw_ofi = float(np.sum(w * net_q))
            if not np.isfinite(raw_ofi):
                return 0.0
            return float(np.clip(raw_ofi, -3.0, 3.0))

        # Two-snapshot dynamic OFI
        prev_bp = np.nan_to_num(np.asarray(prev_bid_prices[:k_levels], dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0)
        prev_ap = np.nan_to_num(np.asarray(prev_ask_prices[:k_levels], dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0)
        prev_bs = (
            np.maximum(np.nan_to_num(np.asarray(prev_bid_sizes[:k_levels], dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0), 0.0)
            if prev_bid_sizes is not None
            else np.zeros(k_levels, dtype=np.float64)
        )
        prev_as = (
            np.maximum(np.nan_to_num(np.asarray(prev_ask_sizes[:k_levels], dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0), 0.0)
            if prev_ask_sizes is not None
            else np.zeros(k_levels, dtype=np.float64)
        )

        ofi_tiers = np.zeros(k_levels, dtype=np.float64)
        for k in range(k_levels):
            # Bid side logic
            pb, pb_prev = bp[k], prev_bp[k]
            qb, qb_prev = bs[k], prev_bs[k]
            if pb > pb_prev:
                delta_b = qb
            elif pb == pb_prev:
                delta_b = qb - qb_prev
            else:
                delta_b = -qb_prev

            # Ask side logic
            pa, pa_prev = ap[k], prev_ap[k]
            qa, qa_prev = as_[k], prev_as[k]
            if pa < pa_prev:
                delta_a = qa
            elif pa == pa_prev:
                delta_a = qa - qa_prev
            else:
                delta_a = -qa_prev

            ofi_tiers[k] = delta_b - delta_a

        ofi_agg = float(np.sum(w * ofi_tiers))

        # Standardize velocity
        mean_val = float(mean_ofi) if np.isfinite(mean_ofi) else 0.0
        denom = float(std_ofi) if (np.isfinite(std_ofi) and std_ofi > 1e-6) else 1.0
        vel = (ofi_agg - mean_val) / denom
        if not np.isfinite(vel):
            return 0.0
        return float(np.clip(vel, -5.0, 5.0))
    except Exception:
        return 0.0


def compute_ohlcv_ofi_proxy(
    open_price: float,
    prev_close: float,
    volume: float,
    volume_sma20: float,
) -> float:
    """
    Canonical OHLCV proxy for Order Flow Imbalance when Level-2 order book depth is unavailable:
        OFI_Proxy = sign(O_t - C_{t-1}) * min(3.0, V_t / max(V_sma, 1.0)) * sqrt(|O_t / C_{t-1} - 1.0|)
    """
    if not (np.isfinite(open_price) and np.isfinite(prev_close) and prev_close > 0.0):
        return 0.0
    gap = (open_price / prev_close) - 1.0
    v_norm = min(3.0, volume / max(volume_sma20, 1.0)) if (np.isfinite(volume) and np.isfinite(volume_sma20)) else 1.0
    proxy = np.sign(gap) * v_norm * np.sqrt(abs(gap))
    return float(proxy) if np.isfinite(proxy) else 0.0


@register_strategy(
    StrategyMeta(
        strategy_id="cross_market_micro_momentum",
        display_name="Cross-Market Timezone Lead-Lag & Level-2 OFI Velocity",
        score_column="cross_market_micro_mom_score",
        category="microstructure",
        output_file="cross_market_micro_momentum_predictions.txt",
        default_regime_weights={
            "BULL_HIGH_VOL": 0.040,
            "SIDEWAYS_HIGH_VOL": 0.035,
            "BULL_LOW_VOL": 0.030,
            "SIDEWAYS_LOW_VOL": 0.025,
            "BEAR_LOW_VOL": 0.020,
            "BEAR_HIGH_VOL": 0.020,
            "PANIC_CRISIS": 0.000,
            "BULL": 0.035,
            "SIDEWAYS": 0.030,
            "BEAR": 0.020,
        },
    )
)
class CrossMarketMicroMomentumEngine(BaseStrategyEngine):
    """
    Phase 140 Cross-Market Timezone Lead-Lag & Level-2 OFI Velocity Engine (Feature F681).
    Exploits the 14.5-hour timezone trading gap between US market close and KRX opening auction,
    coupling overnight leader price momentum with high-frequency Level-2 OFI velocity to generate
    predictive alpha prior to the cash opening bell.
    """

    def __init__(
        self,
        config: Optional[Any] = None,
        tailwind_threshold: float = 0.018,
    ) -> None:
        super().__init__(name="CrossMarketMicroMomentumEngine", config=config)
        self.tailwind_threshold = tailwind_threshold

    @staticmethod
    def _canon_sym(s: Any) -> str:
        s_str = str(s).strip()
        part0 = s_str.split(".")[0]
        return part0.zfill(6) if part0.isdigit() else s_str.upper()

    def _extract_us_overnight_return(
        self,
        us_lead: str,
        prices_dict: Dict[str, pd.DataFrame],
        indicators_df: Optional[Any] = None,
    ) -> float:
        """Extracts overnight return of the US driver ticker or macro indicator."""
        # 1. Check prices_dict
        lead_c = self._canon_sym(us_lead)
        for sym_cand in [us_lead, lead_c, f"{lead_c}.US"]:
            if sym_cand in prices_dict:
                df = self.extract_ohlcv(sym_cand, prices_dict, min_bars=2)
                if df is not None and len(df) >= 2:
                    c = pd.to_numeric(df["Close"], errors="coerce").dropna()
                    if len(c) >= 2 and c.iloc[-2] > 0:
                        return float((c.iloc[-1] / c.iloc[-2]) - 1.0)

        # 2. Check indicators_df for macro proxy
        if indicators_df is not None and isinstance(indicators_df, pd.DataFrame):
            for cand in [us_lead.lower(), us_lead.upper(), "sox", "sp500", "vix"]:
                if cand in indicators_df.columns:
                    s = pd.to_numeric(indicators_df[cand], errors="coerce").dropna()
                    if len(s) >= 2 and s.iloc[-2] > 0:
                        return float((s.iloc[-1] / s.iloc[-2]) - 1.0)

        return 0.0

    def calculate_scores(
        self,
        symbols: Optional[List[str]] = None,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        level2_dict: Optional[Dict[str, Dict[str, np.ndarray]]] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Universal calculate_scores method compatible with test suites and pipeline runners."""
        if prices_dict is None and isinstance(symbols, dict):
            prices_dict = symbols
            symbols = None
        if symbols is not None and prices_dict is not None:
            prices_dict = {s: prices_dict[s] for s in symbols if s in prices_dict}
        return self.compute_scores(prices_dict=prices_dict, level2_dict=level2_dict, **kwargs)

    def compute_scores(
        self,
        prices_dict: Any,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        level2_dict: Optional[Dict[str, Dict[str, np.ndarray]]] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Computes Cross-Market Timezone Lead-Lag & Level-2 OFI Velocity scores.
        Returns ScoreDataFrame with ['symbol', 'cross_market_micro_mom_score'].
        """
        prices_source = kwargs.get("df_prices", prices_dict)
        sector_map: Dict[str, str] = kwargs.get("sector_map") or {}

        if not prices_source:
            return make_score_dataframe({}, score_column="cross_market_micro_mom_score")

        if isinstance(prices_source, dict):
            p_dict = prices_source
            symbols = list(p_dict.keys())
        elif isinstance(prices_source, pd.DataFrame):
            if "symbol" in prices_source.columns:
                symbols = prices_source["symbol"].dropna().astype(str).unique().tolist()
                p_dict = {s: prices_source[prices_source["symbol"] == s] for s in symbols}
            else:
                symbols = list(prices_source.columns)
                p_dict = {col: pd.DataFrame({"Close": prices_source[col]}) for col in symbols}
        else:
            return make_score_dataframe({}, score_column="cross_market_micro_mom_score")

        scores: Dict[str, float] = {}
        us_lead_cache: Dict[str, float] = {}

        for sym in symbols:
            sym_str = str(sym).strip()
            sym_c = self._canon_sym(sym_str)

            # Determine benchmark driver configuration
            driver_info = SYMBOL_BENCHMARK_OVERRIDES.get(sym_c)
            if not driver_info:
                sec = sector_map.get(sym_str, sector_map.get(sym_c, "Market"))
                driver_info = SECTOR_BENCHMARK_DRIVERS.get(sec, SECTOR_BENCHMARK_DRIVERS["Market"])

            us_lead = driver_info.get("us_lead", "SPY")
            beta = float(driver_info.get("beta", 1.0))

            # 1. Overnight US return with memoization
            if us_lead not in us_lead_cache:
                us_lead_cache[us_lead] = self._extract_us_overnight_return(us_lead, p_dict, indicators_df=indicators_df)
            r_us = us_lead_cache[us_lead]

            # 2. Local KRX price series & pre-open indicative return (fast direct numpy extraction)
            df_sym = p_dict.get(sym_str, p_dict.get(sym_c))
            if df_sym is not None and isinstance(df_sym, pd.DataFrame) and len(df_sym) >= 2:
                cols = df_sym.columns
                c_idx = cols.get_loc("Close") if "Close" in cols else (cols.get_loc("close") if "close" in cols else None)
                o_idx = cols.get_loc("Open") if "Open" in cols else (cols.get_loc("open") if "open" in cols else None)
                v_idx = cols.get_loc("Volume") if "Volume" in cols else (cols.get_loc("volume") if "volume" in cols else None)

                if c_idx is not None:
                    vals = df_sym.values
                    c_raw = np.asarray(vals[:, c_idx], dtype=np.float64)
                    c_clean = c_raw[np.isfinite(c_raw)]
                    if len(c_clean) >= 1:
                        c_now = float(c_clean[-1])
                        c_prev = float(c_clean[-2]) if len(c_clean) >= 2 else c_now

                        if o_idx is not None:
                            o_raw = np.asarray(vals[:, o_idx], dtype=np.float64)
                            o_clean = o_raw[np.isfinite(o_raw)]
                            o_now = float(o_clean[-1]) if len(o_clean) >= 1 else c_now
                        else:
                            o_now = c_now

                        r_krx_preopen = ((o_now / c_prev) - 1.0) if c_prev > 0 else 0.0

                        if v_idx is not None:
                            v_raw = np.nan_to_num(np.asarray(vals[:, v_idx], dtype=np.float64), nan=0.0)
                            v_now = float(v_raw[-1]) if len(v_raw) >= 1 else 0.0
                            v_sma20 = float(np.mean(v_raw[-20:])) if len(v_raw) >= 5 else 1.0
                        else:
                            v_now, v_sma20 = 0.0, 1.0
                    else:
                        r_krx_preopen = 0.0
                        o_now, c_prev, v_now, v_sma20 = 1.0, 1.0, 0.0, 1.0
                else:
                    r_krx_preopen = 0.0
                    o_now, c_prev, v_now, v_sma20 = 1.0, 1.0, 0.0, 1.0
            else:
                r_krx_preopen = 0.0
                o_now, c_prev, v_now, v_sma20 = 1.0, 1.0, 0.0, 1.0

            # 3. Unpriced overnight delta
            delta_overnight = compute_overnight_tailwind_delta(r_us, r_krx_preopen, beta=beta)

            # 4. Level-2 OFI Velocity or OHLCV Proxy Fallback
            ofi_vel = 0.0
            if level2_dict and sym_str in level2_dict:
                l2_data = level2_dict[sym_str]
                bp = l2_data.get("bid_prices", np.array([], dtype=float))
                bs = l2_data.get("bid_sizes", np.array([], dtype=float))
                ap = l2_data.get("ask_prices", np.array([], dtype=float))
                as_ = l2_data.get("ask_sizes", np.array([], dtype=float))
                prev_bp = l2_data.get("prev_bid_prices")
                prev_bs = l2_data.get("prev_bid_sizes")
                prev_ap = l2_data.get("prev_ask_prices")
                prev_as = l2_data.get("prev_ask_sizes")
                ofi_vel = compute_level2_ofi_velocity(
                    bid_prices=bp, bid_sizes=bs, ask_prices=ap, ask_sizes=as_,
                    prev_bid_prices=prev_bp, prev_bid_sizes=prev_bs,
                    prev_ask_prices=prev_ap, prev_ask_sizes=prev_as,
                )
            else:
                # Canonical OHLCV proxy fallback
                ofi_vel = compute_ohlcv_ofi_proxy(o_now, c_prev, v_now, v_sma20)

            # 5. Directional Coherence bonus
            coherence = 0.0
            if delta_overnight > 0.005 and ofi_vel > 0.05:
                coherence = 0.025
            elif delta_overnight < -0.005 and ofi_vel < -0.05:
                coherence = -0.025

            # 6. Composite scoring
            # Formula: 0.35 * tanh(12 * delta) + 0.25 * tanh(0.80 * ofi_vel) + 0.15 * coherence
            lin_sig = (
                0.35 * np.tanh(12.0 * delta_overnight) +
                0.25 * np.tanh(0.80 * ofi_vel) +
                coherence
            )
            # Sigmoid activation mapping to [0.05, 0.95] centered at 0.50
            clipped_exp = np.clip(-14.0 * lin_sig, -50.0, 50.0)
            raw_score = 1.0 / (1.0 + np.exp(clipped_exp))
            clipped_score = float(np.clip(raw_score, 0.05, 0.95)) if np.isfinite(raw_score) else 0.50
            scores[sym_str] = round(clipped_score, 4)

        return make_score_dataframe(scores, score_column="cross_market_micro_mom_score")


# Module-level convenience functions
def compute_cross_market_micro_momentum_scores(prices_dict: Any, **kwargs: Any) -> pd.DataFrame:
    """Convenience functional interface for CrossMarketMicroMomentumEngine."""
    engine = CrossMarketMicroMomentumEngine()
    return engine.compute_scores(prices_dict=prices_dict, **kwargs)

cross_market_micro_mom_score = compute_cross_market_micro_momentum_scores

# Complete Alias Trees
Phase140CrossMarketMicroMomentumEngine = CrossMarketMicroMomentumEngine
F681CrossMarketMicroMomentumEngine = CrossMarketMicroMomentumEngine
TimezoneLeadLagOFIEngine = CrossMarketMicroMomentumEngine
CrossMarketMicroEngine = CrossMarketMicroMomentumEngine
