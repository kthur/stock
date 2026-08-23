"""
src/core/order_flow.py
Order Flow Imbalance ( 수급 불균형 모니터링 ) Engine.
Evaluates Institutional and Foreign net buying pressure, volume-weighted order imbalance,
and flow acceleration to generate order_flow_scores [0.0, 1.0].
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
        strategy_id="order_flow",
        display_name="Order Flow Imbalance",
        score_column="order_flow_score",
        category="factor",
        output_file="order_flow_predictions.txt",
        default_regime_weights={
            "BEAR": 0.05, "BEAR_HIGH_VOL": 0.05, "SIDEWAYS_LOW_VOL": 0.04, "BULL_HIGH_VOL": 0.06, "BULL_LOW_VOL": 0.04
        },
    )
)
class OrderFlowEngine(BaseStrategyEngine):
    """
    Order Flow Imbalance Strategy Engine.
    Scorers stock demand/supply imbalance based on institutional/foreign trading volume and price impact.
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
            flow_data_dict = kwargs.get("flow_data_dict")
            return self.compute_order_flow_scores(prices_dict, flow_data_dict=flow_data_dict)
        except Exception as e:
            logger.warning(f"[OrderFlowEngine] compute_scores failed: {e}")
            return pd.DataFrame(columns=["symbol", "order_flow_score"])

    def compute_order_flow_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        flow_data_dict: Optional[Dict[str, pd.DataFrame]] = None
    ) -> pd.DataFrame:
        """
        Computes Order Flow scores for a set of symbols.
        Returns DataFrame with ['symbol', 'order_flow_score'].
        """
        if not prices_dict:
            return pd.DataFrame(columns=['symbol', 'order_flow_score'])

        records = []

        for sym, df in prices_dict.items():
            if df is None or len(df) < 10:
                continue
            try:
                c_col = 'Close' if 'Close' in df.columns else ('close' if 'close' in df.columns else None)
                v_col = 'Volume' if 'Volume' in df.columns else ('volume' if 'volume' in df.columns else None)
                if not c_col or not v_col:
                    continue

                close = df[c_col]
                volume = df[v_col]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                if isinstance(volume, pd.DataFrame):
                    volume = volume.iloc[:, 0]

                close = close.dropna()
                volume = volume.dropna()

                if len(close) < 10 or len(volume) < 10:
                    continue

                # Volume-Weighted Price Trend (On-Balance Volume Proxy / Money Flow)
                ret = close.pct_change().dropna()
                vol_sub = volume.iloc[-len(ret):]

                # Directional Money Flow Volume (14-day Rolling MFI)
                ret_14 = ret.tail(14)
                vol_14 = vol_sub.tail(14)
                pos_flow = float(np.where(ret_14 > 0, ret_14 * vol_14, 0.0).sum())
                neg_flow = float(np.where(ret_14 < 0, abs(ret_14) * vol_14, 0.0).sum())
                tot_flow = pos_flow + neg_flow
                # R11-3 Fix: Return neutral 0.50 for flat/zero-flow stocks rather than false bearish 0.0
                if tot_flow < 1e-12:
                    mfi_ratio = 0.50
                else:
                    mfi_ratio = float(pos_flow / tot_flow)

                # OBV (On-Balance Volume) 10-day slope trend normalized by 10-day volume sum
                obv_slice = (np.sign(ret.tail(20)) * vol_sub.tail(20)).cumsum()
                vol_10d_sum = float(vol_sub.tail(10).sum())
                obv_trend = float((obv_slice.iloc[-1] - obv_slice.iloc[-10]) / max(vol_10d_sum, 1.0)) if len(obv_slice) >= 10 else 0.0

                # Volume Acceleration Ratio (5d avg volume / 20d avg volume)
                # R7-7 Fix: Clip single-day volume spikes at 3.0 * vol_20d to avoid single-day outlier distortions
                vol_20d = float(volume.iloc[-20:].mean()) if len(volume) >= 20 else float(volume.mean())
                vol_5d_sub = volume.iloc[-5:].clip(upper=max(1.0, 3.0 * vol_20d)) if len(volume) >= 5 else volume.iloc[-1:]
                vol_5d = float(vol_5d_sub.mean())
                vol_accel = (vol_5d / (vol_20d + 1e-6)) if vol_20d > 0 else 1.0

                # VWAP Deviation Signal (Current Close vs 20-day VWAP)
                vol_20_slice = volume.iloc[-20:]
                close_20_slice = close.iloc[-20:]
                vwap_20d = (close_20_slice * vol_20_slice).sum() / (vol_20_slice.sum() + 1e-6)
                vwap_dev = (float(close.iloc[-1]) - float(vwap_20d)) / (float(vwap_20d) + 1e-6)
                vwap_score = float(np.clip(0.5 + vwap_dev * 5.0, 0.0, 1.0))

                # Composite order flow indicator (MFI + OBV + Volume Accel + VWAP Deviation)
                composite_flow = (
                    0.45 * mfi_ratio +
                    0.20 * np.clip(0.5 + obv_trend * 0.1, 0.0, 1.0) +
                    0.15 * np.clip(vol_accel / 2.0, 0.0, 1.0) +
                    0.20 * vwap_score
                )

                # Check if detailed foreign/institutional flow data is available
                inst_boost = 0.0
                if flow_data_dict and sym in flow_data_dict:
                    f_df = flow_data_dict[sym]
                    if f_df is not None and not f_df.empty:
                        try:
                            # Align flow dates with price dates
                            f_df_aligned = f_df.reindex(df.index).ffill()
                            v_col = 'Volume' if 'Volume' in df.columns else ('volume' if 'volume' in df.columns else None)
                            vol_5d = float(df[v_col].iloc[-5:].sum()) if (v_col and len(df) >= 5) else 1e6
                            vol_5d = max(vol_5d, 1.0)

                            if 'foreign_net_buy' in f_df_aligned.columns:
                                f_buy = float(f_df_aligned['foreign_net_buy'].iloc[-5:].sum())
                                if f_buy > 0:
                                    inst_boost += min(0.10, (f_buy / vol_5d) * 0.5)
                            if 'inst_net_buy' in f_df_aligned.columns:
                                i_buy = float(f_df_aligned['inst_net_buy'].iloc[-5:].sum())
                                if i_buy > 0:
                                    inst_boost += min(0.10, (i_buy / vol_5d) * 0.5)
                        except Exception:
                            pass

                records.append({
                    'symbol': sym,
                    'mfi_ratio': composite_flow + inst_boost
                })
            except Exception as e:
                logger.debug(f"Order flow score failed for {sym}: {e}")
                continue

        if not records:
            return pd.DataFrame(columns=['symbol', 'order_flow_score'])

        res_df = pd.DataFrame(records)
        if len(res_df) == 1:
            res_df['order_flow_score'] = 0.50
            return res_df[['symbol', 'order_flow_score']]

        raw_ranks = res_df['mfi_ratio'].rank(pct=True, ascending=True).clip(0.02, 0.98)
        # Smart Money Dual Inflow Booster for top 15% high-demand order flow leaders
        smart_money_mask = raw_ranks >= 0.85
        enhanced_score = np.where(smart_money_mask, (raw_ranks * 1.10).clip(0.0, 0.98), raw_ranks)
        res_df['order_flow_score'] = pd.Series(enhanced_score, index=res_df.index).clip(0.0, 1.0)
        return res_df[['symbol', 'order_flow_score']]
