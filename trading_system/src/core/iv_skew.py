"""
src/core/iv_skew.py
Options-Implied Volatility (IV) Skew Engine.
Fetches options chains for optionable tickers (SP500 / US equities) and calculates Put-Call IV Skew.
High Put/Call IV Skew signals extreme market hedging fear -> Contrarian bullish score.
"""
import logging
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class IVSkewEngine:
    """
    Options-Implied Volatility (IV) Skew Strategy Engine.
    Evaluates options market sentiment via Put IV vs Call IV ratios.
    """

    def __init__(self):
        pass

    def compute_skew_for_ticker(self, ticker: str) -> float:
        """
        Attempts to calculate Put-Call IV Skew for a given US ticker via yfinance.
        Returns score in [0.0, 1.0]. Neutral = 0.5.
        """
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            expirations = t.options
            if not expirations:
                return 0.5

            # Get current stock price to filter near-the-money (ATM) options
            hist = t.history(period='5d')
            if hist.empty:
                return 0.5
            underlying_price = float(hist['Close'].iloc[-1])

            # Pick nearest expiration date
            exp = expirations[0]
            chain = t.option_chain(exp)
            calls, puts = chain.calls, chain.puts

            if calls.empty or puts.empty:
                return 0.5

            # Filter ATM options (strike within ±8% of underlying price)
            atm_calls = calls[abs(calls['strike'] - underlying_price) / underlying_price <= 0.08]
            atm_puts = puts[abs(puts['strike'] - underlying_price) / underlying_price <= 0.08]

            eff_calls = atm_calls if not atm_calls.empty else calls
            eff_puts = atm_puts if not atm_puts.empty else puts

            call_iv = eff_calls['impliedVolatility'].median()
            put_iv = eff_puts['impliedVolatility'].median()

            if call_iv <= 0 or np.isnan(call_iv) or put_iv <= 0 or np.isnan(put_iv):
                return 0.5

            skew_ratio = put_iv / call_iv

            # Normal skew ratio is around 1.0 - 1.2
            # Extreme skew (> 1.4) represents panic hedging -> contrarian bullish score
            # Low skew (< 0.8) represents excessive call buying / complacency -> cautious score
            score = 0.5 + (skew_ratio - 1.1) * 0.5
            return float(np.clip(score, 0.0, 1.0))
        except Exception as e:
            logger.debug(f"IV Skew calculation failed for {ticker}: {e}")
            return 0.5

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
            score = 0.5
            # 1. Fast in-memory realized price volatility & return skewness proxy (0 network calls)
            if prices_dict and sym in prices_dict:
                df = prices_dict[sym]
                if df is not None and len(df) >= 20:
                    try:
                        c = df['Close']
                        if isinstance(c, pd.DataFrame):
                            c = c.iloc[:, 0]
                        c = c.dropna()
                        if len(c) >= 20:
                            ret = c.pct_change().dropna()
                            down_ret = ret[ret < 0]
                            up_ret = ret[ret > 0]
                            down_vol = float(down_ret.iloc[-20:].std()) if len(down_ret) >= 2 else 0.01
                            up_vol = float(up_ret.iloc[-20:].std()) if len(up_ret) >= 2 else 0.01
                            if np.isnan(down_vol) or down_vol <= 0:
                                down_vol = 0.01
                            if np.isnan(up_vol) or up_vol <= 0:
                                up_vol = 0.01
                            skew_ratio = down_vol / up_vol
                            ret_skew = float(ret.tail(20).skew()) if len(ret) >= 20 else 0.0
                            if np.isnan(ret_skew):
                                ret_skew = 0.0
                            score = float(np.clip(0.5 + (skew_ratio - 1.0) * 0.25 - ret_skew * 0.15, 0.0, 1.0))
                    except Exception:
                        score = 0.5

            # 2. Optional live options chain lookup for US tickers only if explicitly enabled
            if score == 0.5 and not sym.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')) and '.' not in sym:
                try:
                    import os
                    if os.getenv("ENABLE_LIVE_OPTIONS_FETCH", "false").lower() == "true":
                        score = self.compute_skew_for_ticker(sym)
                except Exception:
                    pass

            return sym, score


        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(_evaluate_one, sym): sym for sym in symbols}
            for future in as_completed(futures):
                try:
                    sym, score = future.result()
                    results[sym] = score
                except Exception as e:
                    logger.debug(f"IV Skew task error: {e}")

        res_list = [{'symbol': sym, 'iv_skew_score': results.get(sym, 0.5)} for sym in symbols]
        return pd.DataFrame(res_list)
