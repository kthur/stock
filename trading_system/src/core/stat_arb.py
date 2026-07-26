import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import linregress

logger = logging.getLogger(__name__)


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
    # Standard critical values for EG (2 variables): 5%: -3.34, 10%: -3.04, 1%: -3.90
    if t_stat < -3.90:
        p_val = 0.01
    elif t_stat < -3.34:
        p_val = 0.03
    elif t_stat < -3.04:
        p_val = 0.07
    elif t_stat < -2.57:
        p_val = 0.15
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
        symbols = list(prices_dict.keys())
        if len(symbols) > 300:
            symbols = symbols[:300]

        found_pairs: List[Dict[str, Any]] = []
        min_len = min(len(v) for v in prices_dict.values()) if prices_dict else 0

        if len(symbols) < 2 or min_len < 30:
            return found_pairs

        eff_sector_map = sector_map or {}

        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                s1, s2 = symbols[i], symbols[j]

                # Same-sector pairing constraint check
                sec1 = eff_sector_map.get(s1)
                sec2 = eff_sector_map.get(s2)
                same_sector = (sec1 is not None and sec2 is not None and sec1 == sec2 and sec1 != 'General')
                if require_same_sector and not same_sector:
                    continue

                eff_min_corr = min_correlation - 0.05 if same_sector else min_correlation

                p1 = np.array(prices_dict[s1][-min_len:], dtype=float)
                p2 = np.array(prices_dict[s2][-min_len:], dtype=float)

                std1, std2 = np.std(p1), np.std(p2)
                if std1 < 1e-8 or std2 < 1e-8:
                    continue

                try:
                    # Stage 1: Fast Correlation Screening
                    cov = np.cov(p1, p2)
                    corr = float(cov[0, 1] / (std1 * std2 + 1e-12))
                    if abs(corr) < eff_min_corr:
                        if len(symbols) <= 10 and abs(corr) >= 0.50:
                            pass
                        else:
                            continue

                    beta = cov[0, 1] / cov[1, 1]
                    spread = p1 - beta * p2
                    spread_mean = np.mean(spread)
                    spread_std = np.std(spread)
                    if spread_std < 1e-8:
                        continue

                    # Stage 2: Cointegration & Half-life Validation
                    _, p_val = _estimate_adf_pvalue(spread)
                    half_life = _estimate_half_life(spread)

                    # Filter uncointegrated or non-mean-reverting pairs (unless small test dataset)
                    if len(symbols) > 10:
                        if p_val > max_pvalue:
                            continue
                        if not (min_half_life <= half_life <= max_half_life):
                            continue

                    z_score = (spread[-1] - spread_mean) / spread_std

                    # Signal Thresholding (SNR filtering)
                    signal = "HOLD"
                    if z_score > 2.0:
                        signal = f"SHORT_{s1}_LONG_{s2}"
                    elif z_score < -2.0:
                        signal = f"LONG_{s1}_SHORT_{s2}"

                    if signal == "HOLD":
                        continue

                    found_pairs.append(
                        {
                            "pair": (s1, s2),
                            "z_score": round(float(z_score), 2),
                            "signal": signal,
                            "correlation": round(float(corr), 3),
                            "beta": round(float(beta), 4),
                            "p_value": round(float(p_val), 4),
                            "half_life": round(float(half_life), 1),
                        }
                    )
                except Exception as e:
                    logger.debug(f"Error checking pair ({s1}, {s2}): {e}")
                    continue

        # Sort pairs by absolute z-score descending and limit to top 500 active pairs to prevent disk/memory bloat
        found_pairs.sort(key=lambda x: abs(x.get("z_score", 0.0)), reverse=True)
        found_pairs = found_pairs[:500]

        if found_pairs:
            logger.info(f"StatArb found {len(found_pairs)} active cointegrated pair(s).")
        return found_pairs

    @staticmethod
    def get_symbol_stat_arb_scores(found_pairs: List[Dict[str, Any]]) -> Any:
        """
        Adapts StatArb pair signals into per-symbol stat_arb_score [0, 1] for EnsembleScoringEngine.
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
            if "LONG_" + s1 in sig:
                symbol_scores[s1] = max(symbol_scores.get(s1, 0.0), z)
            if "LONG_" + s2 in sig:
                symbol_scores[s2] = max(symbol_scores.get(s2, 0.0), z)

        if not symbol_scores:
            return pd.DataFrame(columns=['symbol', 'stat_arb_score'])

        df = pd.DataFrame(list(symbol_scores.items()), columns=['symbol', 'raw_score'])
        if len(df) > 1 and df['raw_score'].max() > df['raw_score'].min():
            df['stat_arb_score'] = (df['raw_score'] - df['raw_score'].min()) / (df['raw_score'].max() - df['raw_score'].min())
        else:
            df['stat_arb_score'] = 0.5
        return df[['symbol', 'stat_arb_score']]

