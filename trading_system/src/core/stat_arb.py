import logging
from typing import Any, Dict, List

import numpy as np

logger = logging.getLogger(__name__)


class StatisticalArbitrageEngine:
    """다중 자산 통계적 차익거래 (Statistical Arbitrage / Pairs Trading) 모듈"""

    def __init__(self):
        self.pairs = []

    def find_cointegrated_pairs(self, prices_dict: Dict[str, List[float]]) -> List[Dict[str, Any]]:
        symbols = list(prices_dict.keys())
        # Performance optimization: if too many symbols, limit to first 300 to avoid CPU-stalling O(N^2) loop (5M iterations)
        if len(symbols) > 300:
            symbols = symbols[:300]

        found_pairs: List[Dict[str, Any]] = []
        min_len = min(len(v) for v in prices_dict.values()) if prices_dict else 0

        if len(symbols) < 2 or min_len < 30:
            return found_pairs

        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                s1, s2 = symbols[i], symbols[j]
                p1 = np.array(prices_dict[s1][-min_len:], dtype=float)
                p2 = np.array(prices_dict[s2][-min_len:], dtype=float)

                if np.std(p1) < 1e-8 or np.std(p2) < 1e-8:
                    continue

                try:
                    cov = np.cov(p1, p2)
                    beta = cov[0, 1] / cov[1, 1]
                    spread = p1 - beta * p2
                    spread_mean = np.mean(spread)
                    spread_std = np.std(spread)
                    if spread_std < 1e-8:
                        continue
                    z_score = (spread[-1] - spread_mean) / spread_std

                    corr = cov[0, 1] / (np.std(p1) * np.std(p2))
                    if abs(corr) < 0.5:
                        continue

                    signal = "HOLD"
                    if z_score > 2.0:
                        signal = f"SHORT_{s1}_LONG_{s2}"
                    elif z_score < -2.0:
                        signal = f"LONG_{s1}_SHORT_{s2}"

                    found_pairs.append(
                        {
                            "pair": (s1, s2),
                            "z_score": round(float(z_score), 2),
                            "signal": signal,
                            "correlation": round(float(corr), 3),
                            "beta": round(float(beta), 4),
                        }
                    )
                except Exception:
                    continue

        if found_pairs:
            logger.info(f"StatArb found {len(found_pairs)} pair(s): {[p['pair'] for p in found_pairs]}")
        return found_pairs
