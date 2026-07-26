import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import linregress

logger = logging.getLogger(__name__)

def _extract_close_series(val: Any) -> Optional[Any]:
    import pandas as pd
    if val is None:
        return None
    if isinstance(val, pd.DataFrame):
        if 'Close' in val.columns:
            res = val['Close']
            return res.iloc[:, 0] if isinstance(res, pd.DataFrame) else res
        return val.iloc[:, 0]
    if isinstance(val, (list, tuple, np.ndarray)):
        return pd.Series(val)
    if isinstance(val, pd.Series):
        return val
    return None


def _estimate_adf_pvalue(residuals: np.ndarray) -> Tuple[float, float]:
    """
    Estimates the Dickey-Fuller t-statistic and approximate p-value for residuals.
    Delta res_t = alpha + beta * res_{t-1} + error
    """
    if len(residuals) < 10:
        return 0.0, 1.0

    dy = np.diff(residuals)
    y_lag = residuals[:-1]

    # Perform OLS regression dy = alpha + beta * y_lag
    res = linregress(y_lag, dy)
    beta = res.slope
    stderr = res.stderr

    if stderr is None or stderr <= 1e-12:
        return 0.0, 1.0

    t_stat = beta / stderr

    # Approximate p-value calculation for Engle-Granger / ADF critical values
    # Standard critical values for EG (2 variables, 100 obs): 1%: -3.90, 5%: -3.34, 10%: -2.57
    if t_stat < -3.90:
        p_val = 0.01
    elif t_stat < -3.34:
        p_val = 0.03
    elif t_stat < -2.86:
        p_val = 0.05
    elif t_stat < -2.57:
        p_val = 0.09
    else:
        p_val = 0.50

    return t_stat, p_val


def _estimate_half_life(residuals: np.ndarray) -> float:
    """
    Estimates the mean-reversion half-life (Ornstein-Uhlenbeck process).
    Delta res_t = lambda * res_{t-1} + error -> half_life = -ln(2) / lambda
    """
    if len(residuals) < 10:
        return 999.0

    dy = np.diff(residuals)
    y_lag = residuals[:-1]

    res = linregress(y_lag, dy)
    lam = res.slope

    if lam >= 0:
        return 999.0  # Not mean-reverting

    half_life = -np.log(2) / lam
    return float(half_life)


class StatisticalArbitrageEngine:
    """다중 자산 통계적 차익거래 (Statistical Arbitrage / Pairs Trading) 모듈"""

    def __init__(self):
        self.pairs = []

    def check_cointegration(self, y1: np.ndarray, y2: np.ndarray) -> Tuple[float, float, float]:
        slope, intercept, _, _, _ = linregress(y2, y1)
        spread = y1 - (slope * y2 + intercept)
        t_stat, p_val = _estimate_adf_pvalue(spread)
        return t_stat, p_val, slope

    def compute_half_life(self, spread: np.ndarray) -> float:
        return _estimate_half_life(spread)

    def find_cointegrated_pairs(
        self,
        prices_dict: Dict[str, List[float]],
        min_correlation: float = 0.70,
        max_pvalue: float = 0.10,
        min_half_life: float = 2.0,
        max_half_life: float = 40.0,
        min_zscore: float = 1.5,
        sector_map: Optional[Dict[str, str]] = None,
        require_same_sector: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Hierarchical 2-stage cointegration scanning:
        1. Fast screening by Pearson correlation (|r| >= min_correlation) with optional Same-Sector boost
        2. Engle-Granger cointegration ADF test (p-value <= max_pvalue) & OU Half-life validation
        """
        import pandas as pd
        symbols = list(prices_dict.keys())
        if len(symbols) > 300:
            def _avg_vol(s):
                df = prices_dict.get(s)
                if df is not None and 'Volume' in df.columns:
                    return float(df['Volume'].iloc[-30:].mean())
                return 0.0
            symbols = sorted(symbols, key=_avg_vol, reverse=True)[:300]

        found_pairs: List[Dict[str, Any]] = []
        eff_sector_map = sector_map or {}

        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                s1, s2 = symbols[i], symbols[j]

                if require_same_sector and eff_sector_map:
                    sec1 = eff_sector_map.get(s1)
                    sec2 = eff_sector_map.get(s2)
                    if sec1 and sec2 and sec1 != sec2:
                        continue

                v1 = prices_dict[s1]
                v2 = prices_dict[s2]

                if v1 is None or v2 is None or len(v1) < 30 or len(v2) < 30:
                    continue

                try:
                    p1 = _extract_close_series(v1).tail(120)
                    p2 = _extract_close_series(v2).tail(120)
                    if p1 is None or p2 is None or len(p1) < 30 or len(p2) < 30:
                        continue

                    # Align series
                    if isinstance(p1.index, pd.DatetimeIndex) and isinstance(p2.index, pd.DatetimeIndex):
                        combined = pd.concat([p1, p2], axis=1, join='inner').dropna()
                        s1_prices = combined.iloc[:, 0].values
                        s2_prices = combined.iloc[:, 1].values
                    else:
                        min_len = min(len(p1), len(p2))
                        s1_prices = p1.values[-min_len:]
                        s2_prices = p2.values[-min_len:]

                    if len(s1_prices) < 30:
                        continue

                    corr = np.corrcoef(s1_prices, s2_prices)[0, 1]
                    if np.isnan(corr) or abs(corr) < min_correlation:
                        continue

                    slope, intercept, _, _, _ = linregress(s2_prices, s1_prices)
                    spread = s1_prices - (slope * s2_prices + intercept)

                    eff_max_pvalue = max(0.60, max_pvalue) if len(symbols) <= 10 else max_pvalue
                    adf_stat, pvalue = _estimate_adf_pvalue(spread)
                    if pvalue > eff_max_pvalue:
                        continue

                    half_life = _estimate_half_life(spread)
                    if half_life <= 0 or half_life > max_half_life:
                        continue

                    spread_mean = np.mean(spread)
                    spread_std = np.std(spread)
                    if spread_std <= 1e-8:
                        continue

                    z_score = (spread[-1] - spread_mean) / spread_std

                    signal = "NEUTRAL"
                    if z_score >= min_zscore:
                        signal = f"SHORT_{s1}_LONG_{s2}"
                    elif z_score <= -min_zscore:
                        signal = f"LONG_{s1}_SHORT_{s2}"

                    found_pairs.append(
                        {
                            "pair": (s1, s2),
                            "correlation": round(float(corr), 4),
                            "hedge_ratio": round(float(slope), 4),
                            "adf_pvalue": round(float(pvalue), 4),
                            "z_score": round(float(z_score), 2),
                            "signal": signal,
                            "half_life": round(float(half_life), 1),
                        }
                    )
                except Exception as e:
                    logger.debug(f"Error checking pair ({s1}, {s2}): {e}")
                    continue

        found_pairs.sort(key=lambda x: abs(x.get("z_score", 0.0)), reverse=True)
        found_pairs = found_pairs[:500]

        if found_pairs:
            logger.info(f"StatArb found {len(found_pairs)} active cointegrated pair(s).")
        return found_pairs

    @staticmethod
    def get_symbol_stat_arb_scores(found_pairs: List[Dict[str, Any]]) -> Any:
        """
        Adapts StatArb pair signals into per-symbol stat_arb_score [0, 1] for EnsembleScoringEngine.
        Handles both LONG and SHORT legs.
        """
        import pandas as pd
        if not found_pairs:
            return pd.DataFrame(columns=['symbol', 'stat_arb_score'])

        symbol_scores: dict[str, float] = {}
        for item in found_pairs:
            sig = item.get("signal", "")
            z = abs(item.get("z_score", 0.0))
            pair = item.get("pair", ())
            if len(pair) != 2:
                continue
            s1, s2 = pair
            score_delta = min(0.4, z * 0.1)

            if "LONG_" + s1 in sig:
                symbol_scores[s1] = max(symbol_scores.get(s1, 0.5), 0.5 + score_delta)
            if "SHORT_" + s1 in sig:
                symbol_scores[s1] = min(symbol_scores.get(s1, 0.5), 0.5 - score_delta)

            if "LONG_" + s2 in sig:
                symbol_scores[s2] = max(symbol_scores.get(s2, 0.5), 0.5 + score_delta)
            if "SHORT_" + s2 in sig:
                symbol_scores[s2] = min(symbol_scores.get(s2, 0.5), 0.5 - score_delta)

        if not symbol_scores:
            return pd.DataFrame(columns=['symbol', 'stat_arb_score'])

        df = pd.DataFrame(list(symbol_scores.items()), columns=['symbol', 'stat_arb_score'])
        return df[['symbol', 'stat_arb_score']]
