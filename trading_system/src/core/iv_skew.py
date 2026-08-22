"""
src/core/iv_skew.py
Options-Implied Volatility (IV) Skew Engine.
Fetches options chains for optionable tickers (SP500 / US equities) and calculates Put-Call IV Skew.
High Put/Call IV Skew signals extreme market hedging fear -> Contrarian bullish score.
"""
import logging
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


from src.core.base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta


@register_strategy(
    StrategyMeta(
        strategy_id="iv_skew",
        display_name="Options IV Skew",
        score_column="iv_skew_score",
        category="factor",
        output_file="iv_skew_predictions.txt",
        default_regime_weights={
            "BEAR": 0.05, "BEAR_HIGH_VOL": 0.05, "SIDEWAYS_LOW_VOL": 0.03, "BULL_HIGH_VOL": 0.04, "BULL_LOW_VOL": 0.03
        },
    )
)
class IVSkewEngine(BaseStrategyEngine):
    """
    Options-Implied Volatility (IV) Skew Strategy Engine.
    Evaluates options market sentiment via Put IV vs Call IV ratios.
    """

    def __init__(self, atm_threshold: float = 0.08, config: Optional[Any] = None):
        self.atm_threshold = atm_threshold
        self.config = config

    def compute_skew_for_ticker(self, ticker: str) -> float:
        """
        Attempts to calculate Put-Call IV Skew for a given US ticker via yfinance.
        Returns score in [0.0, 1.0].
        """
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            expirations = t.options
            if not expirations:
                return np.nan

            # Get current stock price to filter near-the-money (ATM) options
            hist = t.history(period='5d')
            if hist.empty:
                return np.nan
            underlying_price = float(hist['Close'].iloc[-1])

            # Pick nearest expiration date
            exp = expirations[0]
            chain = t.option_chain(exp)
            calls, puts = chain.calls, chain.puts

            if calls.empty or puts.empty:
                return np.nan

            # Filter ATM options (strike within ±atm_threshold of underlying price)
            atm_calls = calls[abs(calls['strike'] - underlying_price) / underlying_price <= self.atm_threshold]
            atm_puts = puts[abs(puts['strike'] - underlying_price) / underlying_price <= self.atm_threshold]

            eff_calls = atm_calls if not atm_calls.empty else calls
            eff_puts = atm_puts if not atm_puts.empty else puts

            call_iv = eff_calls['impliedVolatility'].median()
            put_iv = eff_puts['impliedVolatility'].median()

            if call_iv <= 0 or np.isnan(call_iv) or put_iv <= 0 or np.isnan(put_iv):
                return np.nan

            skew_ratio = put_iv / call_iv

            # Normal skew ratio is around 1.0 - 1.2
            # Extreme skew (> 1.4) represents panic hedging -> contrarian bullish score
            # Low skew (< 0.8) represents excessive call buying / complacency -> cautious score
            score = 0.5 + (skew_ratio - 1.1) * 0.5
            return float(np.clip(score, 0.0, 1.0))
        except Exception as e:
            logger.debug(f"IV Skew calculation failed for {ticker}: {e}")
            return np.nan

    def compute_iv_skew_scores(
        self,
        symbols: List[str],
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None
    ) -> pd.DataFrame:
        """
        Computes IV Skew scores for a list of symbols in parallel using ThreadPoolExecutor.
        Returns DataFrame with ['symbol', 'iv_skew_score'].
        """
        if not symbols:
            return pd.DataFrame(columns=['symbol', 'iv_skew_score'])

        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = {}

        def _evaluate_one(sym: str):
            score = np.nan
            is_us_ticker = not sym.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')) and '.' not in sym

            # 1. Live options chain lookup takes priority for US tickers if explicitly enabled
            if is_us_ticker:
                try:
                    import os
                    if os.getenv("ENABLE_LIVE_OPTIONS_FETCH", "false").lower() == "true":
                        live_score = self.compute_skew_for_ticker(sym)
                        if pd.notna(live_score):
                            return sym, live_score
                except Exception:
                    pass

            # 2. Fast in-memory realized price volatility & return skewness fallback (0 network calls)
            if prices_dict and sym in prices_dict:
                df = prices_dict[sym]
                if df is not None and len(df) >= 2:
                    try:
                        c_col = 'Close' if 'Close' in df.columns else ('close' if 'close' in df.columns else None)
                        if not c_col:
                            return sym, np.nan
                        c = df[c_col]
                        if isinstance(c, pd.DataFrame):
                            c = c.iloc[:, 0]
                        c = c.dropna()
                        if len(c) >= 2:
                            ret = c.pct_change().dropna()
                            ret_window = ret.tail(20)
                            if len(ret_window) >= 1 and float(abs(ret_window).sum()) > 1e-6:
                                down_diff = np.minimum(ret_window.values, 0.0)
                                up_diff = np.maximum(ret_window.values, 0.0)
                                down_vol = float(np.sqrt(np.mean(down_diff ** 2)))
                                up_vol = float(np.sqrt(np.mean(up_diff ** 2)))
                                if np.isnan(down_vol) or down_vol <= 0:
                                    down_vol = 0.005
                                if np.isnan(up_vol) or up_vol <= 0:
                                    up_vol = 0.005
                                skew_ratio = down_vol / up_vol
                                ret_skew = float(ret_window.skew()) if len(ret_window) >= 3 else 0.0
                                if np.isnan(ret_skew):
                                    ret_skew = 0.0
                                # Extreme panic turnaround booster (skew_ratio >= 1.5 with positive 1D turnaround return)
                                turnaround_bonus = 0.10 if (skew_ratio >= 1.5 and float(ret.iloc[-1]) > 0.0) else 0.0
                                score = float(np.clip(0.5 + (skew_ratio - 1.0) * 0.25 - ret_skew * 0.15 + turnaround_bonus, 0.0, 1.0))
                            else:
                                score = np.nan
                    except Exception:
                        score = np.nan

            return sym, score

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(_evaluate_one, sym): sym for sym in symbols}
            for future in as_completed(futures):
                try:
                    sym, score = future.result()
                    results[sym] = score
                except Exception as e:
                    logger.debug(f"IV Skew task error: {e}")

        res_list = [{'symbol': sym, 'iv_skew_score': results.get(sym, np.nan)} for sym in symbols]
        return pd.DataFrame(res_list)

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        try:
            symbols = list(prices_dict.keys()) if isinstance(prices_dict, dict) else []
            return self.compute_iv_skew_scores(symbols, prices_dict=prices_dict if isinstance(prices_dict, dict) else None)
        except Exception as e:
            logger.warning(f"[IVSkewEngine] compute_scores failed: {e}")
            return pd.DataFrame(columns=["symbol", "iv_skew_score"])

