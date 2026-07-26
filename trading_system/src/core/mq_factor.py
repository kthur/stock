"""
src/core/mq_factor.py
Momentum Quality (MQ) Factor Engine.
Calculates 12M-1M price momentum (skipping 1M reversal noise) combined with EPS growth,
ROE stability, and earnings quality to produce percentile rank MQ scores [0.0, 1.0].
"""
import logging
from typing import Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class MQFactorEngine:
    """
    Momentum Quality (MQ) Factor Strategy Engine.
    Combines medium-term price momentum (12M-1M) with fundamental earnings quality.
    """

    def compute_mq_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        features_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Computes composite MQ Factor scores for a set of symbols.
        Returns DataFrame with ['symbol', 'mq_score'].
        """
        if not prices_dict:
            return pd.DataFrame(columns=['symbol', 'mq_score'])

        records = []
        for sym, df in prices_dict.items():
            if df is None or len(df) < 30:
                continue
            try:
                close = df['Close']
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                close = close.dropna()
                if len(close) < 30:
                    continue

                # 12M-1M price momentum calculation (skip recent 21 trading days)
                p_t21 = float(close.iloc[-21]) if len(close) >= 21 else float(close.iloc[-1])
                p_t252 = float(close.iloc[-252]) if len(close) >= 252 else float(close.iloc[0])

                price_mom = (p_t21 / p_t252 - 1.0) if p_t252 > 0 else 0.0

                records.append({
                    'symbol': sym,
                    'price_mom': price_mom,
                })
            except Exception as e:
                logger.debug(f"MQ price mom failed for {sym}: {e}")
                continue

        if not records:
            return pd.DataFrame(columns=['symbol', 'mq_score'])

        res_df = pd.DataFrame(records)

        # Merge fundamental features if available
        if features_df is not None and not features_df.empty:
            f_df = features_df.copy()
            if 'symbol' not in f_df.columns and f_df.index.name == 'symbol':
                f_df = f_df.reset_index()

            fund_cols = ['symbol', 'operating_margin', 'eps_growth_1y', 'roe', 'net_profit_margin']
            existing_cols = [c for c in fund_cols if c in f_df.columns]
            if len(existing_cols) > 1:
                f_subset = f_df[existing_cols].groupby('symbol').last().reset_index()
                res_df = res_df.merge(f_subset, on='symbol', how='left')

        # Rank components to percentile scores [0, 1]
        res_df['price_mom_rank'] = res_df['price_mom'].rank(pct=True, ascending=True)

        quality_terms = []
        if 'operating_margin' in res_df.columns:
            res_df['op_margin_rank'] = res_df['operating_margin'].rank(pct=True, ascending=True).fillna(0.5)
            quality_terms.append('op_margin_rank')
        if 'eps_growth_1y' in res_df.columns:
            res_df['eps_growth_rank'] = res_df['eps_growth_1y'].rank(pct=True, ascending=True).fillna(0.5)
            quality_terms.append('eps_growth_rank')
        if 'roe' in res_df.columns:
            res_df['roe_rank'] = res_df['roe'].rank(pct=True, ascending=True).fillna(0.5)
            quality_terms.append('roe_rank')

        if quality_terms:
            res_df['quality_score'] = res_df[quality_terms].mean(axis=1)
            res_df['mq_score'] = 0.60 * res_df['price_mom_rank'] + 0.40 * res_df['quality_score']
        else:
            res_df['mq_score'] = res_df['price_mom_rank']

        res_df['mq_score'] = res_df['mq_score'].clip(0.0, 1.0)
        return res_df[['symbol', 'mq_score']]
