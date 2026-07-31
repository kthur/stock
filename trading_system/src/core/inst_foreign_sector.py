"""
src/core/inst_foreign_sector.py
Foreign & Investment Trust 2-Month Accumulation & Sector Correlation Strategy Engine.
Identifies sector leaders heavily bought by foreign/trust investors over ~40 trading days,
and finds highly correlated laggards in the same sector for follow-through upside.
"""

import logging
from typing import Dict, Optional, List
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class InstForeignSectorEngine:
    """
    Tracks 2-month (40d) accumulation separately for Foreigners and Investment Trusts (투신),
    and combines them to evaluate sector leader accumulation and highly correlated laggard follow-through.
    """

    def __init__(self, accumulation_days: int = 40):
        self.accumulation_days = accumulation_days

    def compute_foreign_accumulation(
        self,
        close: pd.Series,
        volume: pd.Series,
        flow_df: Optional[pd.DataFrame] = None
    ) -> float:
        """
        Calculates 2-month (40d) Foreigner accumulation score independently.
        """
        days = min(self.accumulation_days, len(close))
        ret_window = close.pct_change().iloc[-days:].dropna()
        vol_window = volume.iloc[-len(ret_window):]

        # Base Money Flow calculation for foreign buying proxy
        positive_mf = np.where(ret_window > 0, ret_window * vol_window, 0.0).sum()
        total_mf = (abs(ret_window) * vol_window).sum() + 1e-12
        price_mf_ratio = positive_mf / total_mf

        foreign_flow_score = 0.5
        if flow_df is not None and 'foreign_net_buy' in flow_df.columns:
            f_buy_40d = flow_df['foreign_net_buy'].iloc[-days:].sum()
            f_buy_prev = flow_df['foreign_net_buy'].iloc[-days*2:-days].sum() if len(flow_df) >= days * 2 else 0.0
            foreign_flow_score = np.clip(0.5 + (f_buy_40d / (abs(f_buy_prev) + 1e-6)) * 0.1, 0.0, 1.0) if f_buy_40d != 0 else 0.5

        return float(0.5 * price_mf_ratio + 0.5 * foreign_flow_score)

    def compute_trust_accumulation(
        self,
        close: pd.Series,
        volume: pd.Series,
        flow_df: Optional[pd.DataFrame] = None
    ) -> float:
        """
        Calculates 2-month (40d) Investment Trust (투신) accumulation score independently.
        """
        days = min(self.accumulation_days, len(close))
        ret_window = close.pct_change().iloc[-days:].dropna()
        vol_window = volume.iloc[-len(ret_window):]

        # Base Money Flow calculation for trust buying proxy
        positive_mf = np.where(ret_window > 0, ret_window * vol_window, 0.0).sum()
        total_mf = (abs(ret_window) * vol_window).sum() + 1e-12
        price_mf_ratio = positive_mf / total_mf

        trust_flow_score = 0.5
        if flow_df is not None and 'trust_net_buy' in flow_df.columns:
            t_buy_40d = flow_df['trust_net_buy'].iloc[-days:].sum()
            t_buy_prev = flow_df['trust_net_buy'].iloc[-days*2:-days].sum() if len(flow_df) >= days * 2 else 0.0
            trust_flow_score = np.clip(0.5 + (t_buy_40d / (abs(t_buy_prev) + 1e-6)) * 0.1, 0.0, 1.0) if t_buy_40d != 0 else 0.5

        return float(0.5 * price_mf_ratio + 0.5 * trust_flow_score)

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        flow_data_dict: Optional[Dict[str, pd.DataFrame]] = None,
        sector_mapping: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        """
        Computes Foreign/Trust 2-Month Accumulation & Sector Correlation Scores.

        Args:
            prices_dict: Dict of symbol -> OHLCV DataFrame (must include 'Close', 'Volume').
            flow_data_dict: Optional dict of symbol -> Flow DataFrame containing 'foreign_net_buy' and 'trust_net_buy'.
            sector_mapping: Optional dict of symbol -> Sector name (e.g. 'IT', 'Semiconductors').

        Returns:
            DataFrame with columns ['symbol', 'inst_foreign_sector_score', 'foreign_acc_score', 'trust_acc_score', 'accumulation_score', 'sector_corr_score']
        """
        if not prices_dict:
            return pd.DataFrame(columns=['symbol', 'inst_foreign_sector_score', 'foreign_acc_score', 'trust_acc_score', 'accumulation_score', 'sector_corr_score'])

        acc_records = []
        valid_symbols = []

        for sym, df in prices_dict.items():
            if df is None or len(df) < 15:
                continue

            close = df['Close']
            volume = df['Volume']
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            if isinstance(volume, pd.DataFrame):
                volume = volume.iloc[:, 0]

            close = close.dropna()
            volume = volume.dropna()

            if len(close) < 15:
                continue

            valid_symbols.append(sym)
            flow_df = flow_data_dict.get(sym) if flow_data_dict else None

            # 1. Compute Foreign and Investment Trust accumulation separately
            foreign_acc = self.compute_foreign_accumulation(close, volume, flow_df)
            trust_acc = self.compute_trust_accumulation(close, volume, flow_df)

            # 2. Combine the two separate calculations (50% Foreigner + 50% Investment Trust)
            combined_acc = 0.50 * foreign_acc + 0.50 * trust_acc

            acc_records.append({
                'symbol': sym,
                'foreign_acc_score': foreign_acc,
                'trust_acc_score': trust_acc,
                'accumulation_score': combined_acc,
                'sector': sector_mapping.get(sym, 'DEFAULT') if sector_mapping else 'DEFAULT'
            })

        if not acc_records:
            return pd.DataFrame(columns=['symbol', 'inst_foreign_sector_score', 'foreign_acc_score', 'trust_acc_score', 'accumulation_score', 'sector_corr_score'])

        acc_df = pd.DataFrame(acc_records).set_index('symbol')

        # Calculate returns matrix for correlation
        returns_dict = {}
        for sym in valid_symbols:
            df = prices_dict[sym]
            close = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
            returns_dict[sym] = close.pct_change().iloc[-40:]

        returns_df = pd.DataFrame(returns_dict).fillna(0.0)

        # Sector Correlation & Laggard Follow-Through Scoring
        sector_corr_scores = {}
        for sym in valid_symbols:
            sec = acc_df.loc[sym, 'sector']
            sec_peers = acc_df[acc_df['sector'] == sec].index.tolist()

            if len(sec_peers) <= 1:
                # Fallback to market top accumulated leaders if sector has single stock
                leaders = acc_df.nlargest(5, 'accumulation_score').index.tolist()
            else:
                leaders = acc_df.loc[sec_peers].nlargest(min(3, len(sec_peers)), 'accumulation_score').index.tolist()

            # Average correlation with top leaders
            corrs = []
            for ldr in leaders:
                if ldr != sym and ldr in returns_df.columns and sym in returns_df.columns:
                    c = returns_df[sym].corr(returns_df[ldr])
                    if not np.isnan(c):
                        corrs.append(c)

            avg_corr = float(np.mean(corrs)) if corrs else 0.5
            sector_corr_scores[sym] = np.clip(avg_corr, 0.0, 1.0)

        acc_df['sector_corr_score'] = acc_df.index.map(sector_corr_scores).fillna(0.5)

        # Final Composite Score: 60% Combined Accumulation + 40% Sector Correlation / Lead-Lag Potential
        acc_df['raw_composite'] = 0.60 * acc_df['accumulation_score'] + 0.40 * acc_df['sector_corr_score']

        # Rank-normalize to [0, 1]
        acc_df['inst_foreign_sector_score'] = acc_df['raw_composite'].rank(pct=True, ascending=True)

        res_df = acc_df.reset_index()[['symbol', 'inst_foreign_sector_score', 'foreign_acc_score', 'trust_acc_score', 'accumulation_score', 'sector_corr_score']]
        return res_df
