"""
src/core/rim_valuation.py
Residual Income Model (RIM / 초과이익모형) Valuation Engine.

Calculates stock intrinsic value (V0) and margin of safety / discount ratio
based on Book Value Per Share (BPS), Return on Equity (ROE), and Required Return (r_e).

Formula:
  V_0 = BPS * (1 + (ROE - r_e) / r_e)
  Discount Ratio = (V_0 - Price) / Price

Scoring:
  Transforms discount ratio to percentile rank [0.0, 1.0] per market.
"""
import logging
from typing import Dict, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class RIMValuationEngine:
    def __init__(self, default_required_return: float = 0.08, decay_rate: float = 0.0):
        """
        :param default_required_return: Baseline required rate of return (r_e), default 8.0%
        :param decay_rate: ROE persistence decay rate per year (0.0 = constant ROE, 0.10 = 10% decay)
        """
        self.default_required_return = default_required_return
        self.decay_rate = decay_rate

    def calculate_intrinsic_value(
        self,
        bps: float,
        roe: float,
        required_return: Optional[float] = None,
        years: int = 5,
    ) -> float:
        """
        Computes RIM intrinsic value V_0 per share.
        """
        r_e = required_return if (required_return is not None and required_return > 0) else self.default_required_return

        if bps <= 0 or np.isnan(bps):
            return 0.0

        if np.isnan(roe):
            roe = r_e  # Neutral assumption: ROE = r_e => V_0 = BPS

        if self.decay_rate <= 0:
            # Constant ROE Perpetuity Formula: V_0 = BPS * (1 + (ROE - r_e) / r_e)
            if r_e <= 0:
                return bps
            excess_return_ratio = (roe - r_e) / r_e
            # Cap excess_return_ratio to avoid negative valuation or extreme explosion [-0.8, 5.0]
            excess_return_ratio = max(-0.8, min(5.0, excess_return_ratio))
            return bps * (1.0 + excess_return_ratio)
        else:
            # Finite horizon / Decaying ROE formula
            pv_excess = 0.0
            current_bps = bps
            current_roe = roe
            for t in range(1, years + 1):
                excess_income = current_bps * (current_roe - r_e)
                pv_excess += excess_income / ((1.0 + r_e) ** t)
                current_bps += excess_income
                current_roe = r_e + (current_roe - r_e) * (1.0 - self.decay_rate)
            return bps + pv_excess

    def compute_rim_scores(
        self,
        features_df: pd.DataFrame,
        symbol_market_map: Optional[Dict[str, str]] = None,
        required_return: Optional[float] = None,
    ) -> pd.DataFrame:
        """
        Computes RIM intrinsic values and percentile scores for a dataset of stocks.

        Expected columns in features_df:
          - 'symbol' (or index as symbol)
          - 'Close' or 'price'
          - Optional: 'bps', 'roe', 'eps', 'eps_yield', 'net_profit_margin', 'market'

        Returns pd.DataFrame with columns:
          ['symbol', 'market', 'Close', 'bps', 'roe', 'intrinsic_value', 'discount_ratio', 'rim_score']
        """
        if features_df is None or features_df.empty:
            logger.warning("Empty features_df provided to RIMValuationEngine.")
            return pd.DataFrame(columns=['symbol', 'market', 'Close', 'bps', 'roe', 'intrinsic_value', 'discount_ratio', 'rim_score'])

        df = features_df.copy()
        if 'symbol' not in df.columns and df.index.name == 'symbol':
            df = df.reset_index()

        # Handle latest row per symbol if time series is passed
        if 'date' in df.columns and 'symbol' in df.columns:
            df = df.sort_values('date').groupby('symbol').last().reset_index()

        r_e = required_return if (required_return is not None and required_return > 0) else self.default_required_return

        # Ensure Market Column
        if 'market' not in df.columns:
            if symbol_market_map:
                df['market'] = df['symbol'].map(symbol_market_map).fillna('KOSPI')
            else:
                df['market'] = 'KOSPI'

        # Ensure Close / Price
        if 'Close' not in df.columns:
            df['Close'] = df.get('price', 0.0)

        # Derive BPS & ROE if not directly provided
        if 'bps' not in df.columns:
            if 'book_value' in df.columns and 'shares_outstanding' in df.columns:
                df['bps'] = (df['book_value'] / df['shares_outstanding']).fillna(0.0)
            elif 'eps' in df.columns and 'roe' in df.columns:
                df['bps'] = (df['eps'] / df['roe']).replace([np.inf, -np.inf], np.nan).fillna(0.0)
            else:
                # Estimate BPS using Close & fallback PBR
                pbr_proxy = 1.0
                df['bps'] = (df['Close'] / pbr_proxy).fillna(0.0)

        if 'roe' not in df.columns:
            if 'eps' in df.columns and 'bps' in df.columns:
                df['roe'] = (df['eps'] / df['bps']).replace([np.inf, -np.inf], np.nan).fillna(r_e)
            elif 'eps_yield' in df.columns:
                df['roe'] = (df['eps_yield']).fillna(r_e)
            elif 'net_profit_margin' in df.columns:
                df['roe'] = (df['net_profit_margin'] * 0.5).fillna(r_e)
            else:
                df['roe'] = r_e

        # Compute Intrinsic Value V_0 & Discount Ratio
        v0_list = []
        discount_list = []

        for _, row in df.iterrows():
            p = float(row.get('Close', 0.0))
            b = float(row.get('bps', 0.0))
            r = float(row.get('roe', r_e))

            v0 = self.calculate_intrinsic_value(b, r, required_return=r_e)
            v0_list.append(v0)

            if p > 0 and v0 > 0:
                disc = (v0 - p) / p
            else:
                disc = 0.0
            discount_list.append(disc)

        df['intrinsic_value'] = v0_list
        df['discount_ratio'] = discount_list

        # Transform Discount Ratio to Percentile Score [0.0, 1.0] per Market
        def rank_market(group: pd.DataFrame) -> pd.Series:
            if len(group) <= 1:
                return pd.Series(0.5, index=group.index)
            return group['discount_ratio'].rank(pct=True, ascending=True)

        df['rim_score'] = df.groupby('market', group_keys=False).apply(rank_market).fillna(0.5)

        out_cols = ['symbol', 'market', 'Close', 'bps', 'roe', 'intrinsic_value', 'discount_ratio', 'rim_score']
        return df[[c for c in out_cols if c in df.columns]]
