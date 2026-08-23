"""
src/core/gamma_squeeze.py
Options Gamma Squeeze & Call Wall Acceleration Strategy Engine (Strategy #28).

Calculates Options Gamma Exposure (GEX), Call Wall proximity, and Delta Squeeze scores:
  - Call Wall Proximity: (Current Price / Call Wall Strike) -> [0.0, 1.0]
  - Gamma Exposure (GEX): Net Market Maker gamma imbalance score
  - Squeeze Acceleration Score: Combined trigger score for rapid delta-hedging rallies.
"""

import logging
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from src.core.base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta

logger = logging.getLogger(__name__)


@register_strategy(
    StrategyMeta(
        strategy_id="gamma_squeeze",
        display_name="Options Gamma Squeeze",
        score_column="gamma_squeeze_score",
        category="options",
        output_file="gamma_squeeze_predictions.txt",
        default_regime_weights={
            "BEAR": 0.01, "BEAR_HIGH_VOL": 0.00, "SIDEWAYS_LOW_VOL": 0.02, "BULL_HIGH_VOL": 0.04, "BULL_LOW_VOL": 0.03
        },
    )
)
class OptionsGammaSqueezeEngine(BaseStrategyEngine):
    """
    Strategy #28: Options Gamma Squeeze & Call Wall Acceleration Engine.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        self.config = config

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        symbols = list(prices_dict.keys()) if prices_dict else []
        return self.compute_gamma_squeeze_scores(symbols=symbols, prices_dict=prices_dict, **kwargs)

    def calculate_scores(self, symbols: List[str], prices_dict: Optional[Dict[str, pd.DataFrame]] = None, **kwargs: Any) -> pd.DataFrame:
        return self.compute_gamma_squeeze_scores(symbols=symbols, prices_dict=prices_dict, **kwargs)

    def compute_gamma_squeeze_scores(
        self,
        symbols: List[str],
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        options_chain_dict: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Computes Gamma Squeeze acceleration score per symbol [0.0, 1.0].
        Returns DataFrame with ['symbol', 'gamma_squeeze_score'].
        """
        if options_chain_dict is None:
            options_chain_dict = kwargs.get('options_chain_dict')
        if not symbols:
            return pd.DataFrame(columns=['symbol', 'gamma_squeeze_score'])

        results = []

        for sym in symbols:
            score = 0.50  # Base neutral score

            # 1. Price Momentum & Volume Surge Proxy (when live options chain is simulated/unavailable)
            if prices_dict and (sym in prices_dict or str(sym) in prices_dict):
                df = prices_dict.get(sym, prices_dict.get(str(sym)))
                if df is not None and len(df) >= 10:
                    c_col = 'close' if 'close' in df.columns else ('Close' if 'Close' in df.columns else None)
                    v_col = 'volume' if 'volume' in df.columns else ('Volume' if 'Volume' in df.columns else None)

                    if c_col:
                        c = df[c_col].dropna()
                        v = df[v_col].dropna() if v_col else None

                        if len(c) >= 10:
                            ret_3d = float((c.iloc[-1] / c.iloc[-4]) - 1.0) if len(c) >= 4 else 0.0
                            ret_5d = float((c.iloc[-1] / c.iloc[-6]) - 1.0) if len(c) >= 6 else 0.0
                            high_20d = float(c.iloc[-min(len(c), 20):].max())
                            cur_p = float(c.iloc[-1])

                            # Proximity to 20-day High (Call Wall Proxy)
                            proximity = float(np.clip(cur_p / high_20d, 0.0, 1.0)) if high_20d > 0 else 0.95

                            vol_surge = 1.0
                            if v is not None and len(v) >= 6:
                                v_num = pd.to_numeric(v.iloc[-6:-1], errors='coerce').fillna(1.0)
                                avg_v = float(v_num.mean())
                                try:
                                    cur_v = float(v.iloc[-1])
                                except (ValueError, TypeError):
                                    cur_v = 1.0
                                raw_vol_surge = (cur_v / avg_v) if avg_v > 0 and not np.isnan(avg_v) else 1.0
                                vol_surge = float(np.clip(raw_vol_surge, 0.0, 10.0)) if np.isfinite(raw_vol_surge) else 1.0

                            # Gamma Breakout Ignition Bonus (Strong momentum + volume surge + near 20d high)
                            gamma_ignition_bonus = 0.12 if (proximity >= 0.97 and (ret_5d >= 0.08 or ret_3d >= 0.05) and vol_surge >= 1.8) else 0.0

                            # Squeeze score formula with fallback dampening to prevent pure momentum duplication
                            squeeze_raw = 0.35 * proximity + 0.30 * max(0.0, ret_5d * 5.0) + 0.25 * min(2.0, vol_surge) / 2.0 + 0.10 * max(0.0, ret_3d * 6.0) + gamma_ignition_bonus
                            # Attenuate fallback towards neutral (0.5) when actual options GEX is absent
                            score = float(np.clip(0.50 + (squeeze_raw - 0.50) * 0.50, 0.0, 1.0))

            # 2. Live Options Chain GEX override if available (Full strength for US options)
            if options_chain_dict and sym in options_chain_dict:
                opt_data = options_chain_dict[sym]
                call_wall = opt_data.get('call_wall_strike', 0.0)
                gex = opt_data.get('net_gex', 0.0)
                cur_p = opt_data.get('current_price', 1.0)

                if call_wall > 0 and cur_p > 0:
                    dist_to_wall = abs(cur_p - call_wall) / cur_p
                    if (dist_to_wall < 0.03 and gex < 0) or (cur_p >= call_wall):  # Short Gamma Zone or Call Wall Breakout
                        score = float(np.clip(score + 0.35, 0.0, 1.0))
                        logger.info(f"[GAMMA SQUEEZE ENGINE] High Gamma Squeeze trigger for {sym} (Call Wall={call_wall}, dist={dist_to_wall*100:.1f}%)")
                    elif gex > 0:  # Positive dealer GEX dampens volatility and gamma squeeze potential
                        score = float(np.clip(score * 0.70, 0.0, 1.0))

            results.append({'symbol': sym, 'gamma_squeeze_score': score})

        return pd.DataFrame(results)
