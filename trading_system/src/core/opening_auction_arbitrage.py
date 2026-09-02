"""
opening_auction_arbitrage.py — Strategy 35: Cross-Border Opening Auction Arbitrage Engine

Exploits the 3-hour informational vacuum between the US market close (06:00 KST)
and the KRX Opening Call Auction (08:30~09:00 KST) by projecting fair-value overnight
gaps from US tech leaders (NVDA, TSMC, SOXX, SPY) and FX shifts, capturing high-conviction
opening auction dislocation alpha.
"""

from __future__ import annotations

import logging
import math
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any

from src.core.strategy_registry import StrategyMeta, StrategyRegistry

logger = logging.getLogger(__name__)


class OpeningAuctionArbitrageEngine:
    """
    Strategy 35: Global Opening Auction Arbitrage Engine.
    """

    US_LEADER_MAP = {
        # Sector / theme to global US lead proxy
        "semiconductor": "NVDA",
        "tech": "AAPL",
        "ev_battery": "TSLA",
        "general": "SPY"
    }

    SYMBOL_SECTOR_MAP = {
        "005930": "semiconductor", # Samsung Electronics
        "000660": "semiconductor", # SK Hynix
        "042700": "semiconductor", # Hanmi Semi
        "373220": "ev_battery",   # LG Energy Solution
        "005380": "general",      # Hyundai Motor
        "035420": "tech",         # NAVER
        "035720": "tech",         # Kakao
    }

    def __init__(self, beta_lead: float = 0.75, fx_sensitivity: float = 0.40):
        self.beta_lead = beta_lead
        self.fx_sens = fx_sensitivity

    def compute_expected_opening_gap(
        self,
        us_overnight_returns: Dict[str, float],
        usdkrw_overnight_return: float = 0.0,
        symbol: str = "005930"
    ) -> float:
        """
        Projects fair value opening gap:
        Delta Gap = beta_lead * r_US_Leader + beta_broad * r_SPY + fx_sens * r_USDKRW
        """
        theme = self.SYMBOL_SECTOR_MAP.get(symbol, "general")
        us_proxy = self.US_LEADER_MAP.get(theme, "SPY")

        r_lead = float(us_overnight_returns.get(us_proxy, us_overnight_returns.get("SPY", 0.0)))
        r_spy = float(us_overnight_returns.get("SPY", 0.0))
        r_fx = float(usdkrw_overnight_return)

        fair_gap = (self.beta_lead * r_lead) + (0.25 * r_spy) + (self.fx_sens * r_fx)
        return float(fair_gap)

    def compute_opening_auction_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        us_overnight_returns: Optional[Dict[str, float]] = None,
        indicative_opens_dict: Optional[Dict[str, float]] = None,
        usdkrw_overnight_return: float = 0.0
    ) -> Dict[str, float]:
        """
        Calculates Opening Auction Arbitrage Alpha Score [0.0, 1.0] for target symbols.
        Compares expected fair-value gap with pre-market indicative auction quote.
        """
        if not prices_dict:
            return {}

        us_returns = us_overnight_returns or {"SPY": 0.005, "NVDA": 0.015, "AAPL": 0.008, "TSLA": 0.012}
        indicative_quotes = indicative_opens_dict or {}

        scores: Dict[str, float] = {}

        for sym, df in prices_dict.items():
            if df is None or len(df) < 2:
                scores[sym] = 0.50
                continue

            col = 'Close' if 'Close' in df.columns else ('close' if 'close' in df.columns else None)
            if not col:
                scores[sym] = 0.50
                continue

            prev_close = float(df[col].iloc[-1])
            if prev_close <= 0 or not np.isfinite(prev_close):
                scores[sym] = 0.50
                continue

            expected_gap = self.compute_expected_opening_gap(
                us_overnight_returns=us_returns,
                usdkrw_overnight_return=usdkrw_overnight_return,
                symbol=sym
            )

            # If pre-market indicative auction quote is available
            if sym in indicative_quotes and indicative_quotes[sym] > 0:
                ind_open = float(indicative_quotes[sym])
                indicative_gap = (ind_open - prev_close) / prev_close
                # Dislocation = Expected Gap - Actual Indicative Gap
                # Positive dislocation means the market hasn't fully priced in the US jump -> BUY
                dislocation = expected_gap - indicative_gap
                # Sigmoid scaling around 0.0 dislocation
                score = 1.0 / (1.0 + np.exp(-dislocation * 80.0))
            else:
                # Direct fair-value expected gap score
                score = 1.0 / (1.0 + np.exp(-expected_gap * 50.0))

            scores[sym] = round(float(np.clip(score, 0.01, 0.99)), 4)

        return scores


# Register Strategy 35 with StrategyRegistry
OPENING_AUCTION_META = StrategyMeta(
    strategy_id="opening_auction_arbitrage",
    display_name="Opening Auction Arbitrage",
    score_column="opening_auction_arbitrage_score",
    category="event",
    default_regime_weights={
        "BULL_LOW_VOL": 0.04,
        "BULL_HIGH_VOL": 0.05,
        "SIDEWAYS_LOW_VOL": 0.03,
        "SIDEWAYS_HIGH_VOL": 0.04,
        "BEAR_LOW_VOL": 0.03,
        "BEAR_HIGH_VOL": 0.03,
    },
    output_file="opening_auction_arbitrage_predictions.txt",
    requires_fundamentals=False,
    requires_indicators=True,
    is_standalone=False,
)

StrategyRegistry().register(OPENING_AUCTION_META, OpeningAuctionArbitrageEngine)
