"""
src/core/mq_factor.py
Momentum Quality (MQ) Factor Engine.
Calculates 12M-1M price momentum (skipping 1M reversal noise) combined with EPS growth,
ROE stability, and earnings quality to produce percentile rank MQ scores [0.0, 1.0].
"""
import logging
from typing import Dict, Optional, Any
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


from src.core.base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta


@register_strategy(
    StrategyMeta(
        strategy_id="mq_factor",
        display_name="Momentum Quality",
        score_column="mq_score",
        category="factor",
        output_file="mq_predictions.txt",
        requires_fundamentals=True,
        default_regime_weights={
            "BEAR": 0.05, "BEAR_HIGH_VOL": 0.05, "SIDEWAYS_LOW_VOL": 0.06, "BULL_HIGH_VOL": 0.08, "BULL_LOW_VOL": 0.06
        },
    )
)
class MQFactorEngine(BaseStrategyEngine):
    """
    Momentum Quality (MQ) Factor Strategy Engine.
    Combines medium-term price momentum (12M-1M) with fundamental earnings quality.
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
        try:
            features_df = kwargs.get("features_df")
            return self.compute_mq_scores(prices_dict, features_df=features_df, fundamentals_dict=fundamentals_dict)
        except Exception as e:
            logger.warning(f"[MQFactorEngine] compute_scores failed: {e}")
            return pd.DataFrame(columns=["symbol", "mq_score"])

    def compute_mq_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        features_df: Optional[pd.DataFrame] = None,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None
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
                c_col = 'Close' if 'Close' in df.columns else ('close' if 'close' in df.columns else None)
                if not c_col:
                    continue
                close = df[c_col]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                close = close.dropna()
                if len(close) < 30:
                    continue

                # 12M-1M price momentum calculation (skip recent 21 trading days)
                p_t21 = float(close.iloc[-21]) if len(close) >= 21 else float(close.iloc[-1])
                if len(close) >= 252:
                    p_base = float(close.iloc[-252])
                    effective_days = 231
                else:
                    p_base = float(close.iloc[0])
                    effective_days = max(1, len(close) - 21)

                raw_mom = (p_t21 / p_base - 1.0) if p_base > 0 else 0.0
                raw_mom = float(raw_mom) if np.isfinite(raw_mom) else 0.0
                if 60 <= effective_days < 231 and raw_mom > -0.8:
                    power = min(3.0, 231.0 / effective_days)
                    price_mom = float(np.clip(((1.0 + raw_mom) ** power) - 1.0, -0.95, 2.0))
                else:
                    price_mom = float(np.clip(raw_mom, -0.95, 2.0))
                price_mom = price_mom if np.isfinite(price_mom) else 0.0

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
        if (features_df is None or features_df.empty) and fundamentals_dict and isinstance(fundamentals_dict, dict):
            fund_rows: list[dict[str, Any]] = []
            for s, fd in fundamentals_dict.items():
                if isinstance(fd, dict):
                    row: dict[str, Any] = {"symbol": s}
                    row["operating_margin"] = fd.get("operating_margin", fd.get("op_margin", np.nan))
                    row["roe"] = fd.get("roe", np.nan)
                    row["eps_growth_1y"] = fd.get("eps_growth_1y", fd.get("eps_growth", np.nan))
                    row["net_profit_margin"] = fd.get("net_profit_margin", fd.get("npm", np.nan))
                    fund_rows.append(row)
            if fund_rows:
                features_df = pd.DataFrame(fund_rows)

        if features_df is not None and not features_df.empty:
            f_df = features_df.copy()
            if 'symbol' not in f_df.columns and f_df.index.name == 'symbol':
                f_df = f_df.reset_index()

            fund_cols = ['symbol', 'operating_margin', 'eps_growth_1y', 'roe', 'net_profit_margin']
            existing_cols = [c for c in fund_cols if c in f_df.columns]
            if len(existing_cols) > 1:
                f_subset = f_df[existing_cols].groupby('symbol').last().reset_index()
                res_df = res_df.merge(f_subset, on='symbol', how='left')

        # Rank components to percentile scores [0, 1] with boundary clipping
        if len(res_df) == 1:
            res_df['mq_score'] = 0.50
            return res_df[['symbol', 'mq_score']]
        res_df['price_mom_rank'] = res_df['price_mom'].rank(pct=True, ascending=True).clip(0.02, 0.98)

        quality_terms = []
        if 'operating_margin' in res_df.columns:
            res_df['op_margin_rank'] = res_df['operating_margin'].rank(pct=True, ascending=True).clip(0.02, 0.98).fillna(0.5)
            quality_terms.append('op_margin_rank')
        if 'eps_growth_1y' in res_df.columns:
            res_df['eps_growth_rank'] = res_df['eps_growth_1y'].rank(pct=True, ascending=True).clip(0.02, 0.98).fillna(0.5)
            quality_terms.append('eps_growth_rank')
        if 'roe' in res_df.columns:
            res_df['roe_rank'] = res_df['roe'].rank(pct=True, ascending=True).clip(0.02, 0.98).fillna(0.5)
            quality_terms.append('roe_rank')

        if quality_terms:
            res_df['quality_score'] = res_df[quality_terms].mean(axis=1)
            # M-4 Fix: Adaptively weight momentum vs quality based on how many fundamental terms are valid
            valid_qual_ratio = len(quality_terms) / 3.0
            w_qual = 0.40 * valid_qual_ratio
            w_mom = 1.0 - w_qual
            res_df['mq_score'] = w_mom * res_df['price_mom_rank'] + w_qual * res_df['quality_score']

            # Quality Gate: Penalize unprofitable distress stocks (operating loss, negative net margin, or negative ROE)
            distress_mask = pd.Series(False, index=res_df.index)
            if 'operating_margin' in res_df.columns:
                distress_mask = distress_mask | (res_df['operating_margin'] < 0)
            if 'net_profit_margin' in res_df.columns:
                distress_mask = distress_mask | (res_df['net_profit_margin'] < 0)
            if 'roe' in res_df.columns:
                distress_mask = distress_mask | (res_df['roe'] < 0)
            if distress_mask.any():
                res_df.loc[distress_mask, 'mq_score'] = (res_df.loc[distress_mask, 'mq_score'] * 0.60).clip(0.0, 1.0)

            # High-Conviction Momentum Quality Super Alpha Booster (smooth continuous sigmoid)
            smooth_boost = 1.0 + 0.10 / (1.0 + np.exp(-10.0 * (res_df['mq_score'] - 0.75)))
            boost_multiplier = np.where(distress_mask, 1.0, smooth_boost)
            res_df['mq_score'] = (res_df['mq_score'] * boost_multiplier).clip(0.0, 1.0)
        else:
            res_df['mq_score'] = res_df['price_mom_rank']

        res_df['mq_score'] = pd.to_numeric(res_df['mq_score'], errors='coerce').fillna(0.50).clip(0.0, 1.0)
        return res_df[['symbol', 'mq_score']]
