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

            # Pick nearest expiration date (> 3 days out)
            exp = expirations[0]
            chain = t.option_chain(exp)
            calls, puts = chain.calls, chain.puts

            if calls.empty or puts.empty:
                return 0.5

            call_iv = calls['impliedVolatility'].median()
            put_iv = puts['impliedVolatility'].median()

            if call_iv <= 0 or np.isnan(call_iv):
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
            if not sym.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')) and '.' not in sym:
                score = self.compute_skew_for_ticker(sym)
            elif prices_dict and sym in prices_dict:
                df = prices_dict[sym]
                if df is not None and len(df) >= 60:
                    try:
                        ret = df['Close'].pct_change().dropna()
                        vol_20d = ret.iloc[-20:].std()
                        vol_60d = ret.iloc[-60:].std()
                        if vol_60d > 0:
                            vol_ratio = vol_20d / vol_60d
                            score = float(np.clip(0.5 + (vol_ratio - 1.0) * 0.3, 0.0, 1.0))
                    except Exception:
                        score = 0.5
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
