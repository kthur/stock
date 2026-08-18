import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, Any
from .base_strategy import BaseStrategyEngine

logger = logging.getLogger(__name__)

from src.core.strategy_registry import register_strategy, StrategyMeta


@register_strategy(
    StrategyMeta(
        strategy_id="card_factor",
        display_name="Cross-Asset Regime Divergence",
        score_column="card_score",
        category="factor",
        output_file="card_factor_predictions.txt",
        requires_indicators=True,
        default_regime_weights={
            "BEAR": 0.05, "BEAR_HIGH_VOL": 0.05, "SIDEWAYS_LOW_VOL": 0.05, "BULL_HIGH_VOL": 0.04, "BULL_LOW_VOL": 0.04
        },
    )
)
class CARDFactorEngine(BaseStrategyEngine):
    """
    16. Cross-Asset Regime Divergence (CARD) Strategy Engine

    주식 - 원자재(유가/금) - 환율(USD/KRW) - 금리 간 괴리율 역발상 매수 점수 산출.
    - 거시 지표 대비 과도하게 하락한 수혜 섹터/종목 역발상 스코어링
    """
    def __init__(self):
        pass

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Computes CARD factor scores in [0.0, 1.0] for all symbols.
        Returns pd.DataFrame with columns ['symbol', 'card_score'].
        """
        # Handle dict or positional fallback
        if isinstance(prices_dict, pd.DataFrame) and isinstance(fundamentals_dict, dict):
            # Signature was called with swapped parameters
            indicator_df = prices_dict
            prices_dict = fundamentals_dict
        else:
            indicator_df = indicators_df if indicators_df is not None else kwargs.get("indicator_df")

        sector_map = kwargs.get("sector_map") or {}

        if not prices_dict or not isinstance(prices_dict, dict):
            from .base_strategy import make_score_dataframe
            return make_score_dataframe([], 'card_score')

        def _safe_macro(col):
            if indicator_df is None:
                return 0.0
            if isinstance(indicator_df, dict):
                v = float(indicator_df.get(col, 0.0))
                return 0.0 if (np.isnan(v) or np.isinf(v)) else v
            elif isinstance(indicator_df, pd.DataFrame):
                if not indicator_df.empty and col in indicator_df.columns and not indicator_df[col].dropna().empty:
                    v = float(indicator_df[col].dropna().iloc[-1])
                    return 0.0 if (np.isnan(v) or np.isinf(v)) else v
            return 0.0

        # Extract latest macro indicators with safe scaling (supports raw or change keys)
        usdkrw_chg = _safe_macro('usdkrw_change') or _safe_macro('usdkrw_pct') or 0.0
        wti_chg = _safe_macro('wti_change') or _safe_macro('wti_pct') or 0.0
        
        # Determine whether we have raw VIX level (e.g. 25.0) or percentage change (e.g. +5.0%)
        vix_raw = _safe_macro('vix') or _safe_macro('vix_raw')
        vix_change = _safe_macro('vix_change') or _safe_macro('vix_pct')
        if vix_raw and vix_raw > 0:
            vix_val = (vix_raw - 20.0) / 20.0
        elif vix_change:
            # If percentage in 0-100 scale, normalize to decimal
            vix_val = (vix_change / 100.0) if abs(vix_change) > 1.0 else vix_change
        else:
            vix_val = 0.0

        sector_beta = {
            'Semiconductor': 1.5, 'IT': 1.3, 'Automotive': 1.1,
            'Steel': 0.8, 'Chemical': 0.9, 'Finance': 0.7,
            'Energy': 1.4, 'Shipbuilding': 1.2, 'Market': 1.0
        }

        from .base_strategy import make_score_dataframe

        res_rows = []
        for sym, df in prices_dict.items():
            try:
                if df is None or df.empty:
                    res_rows.append({'symbol': sym, 'card_score': 0.5})
                    continue

                col = 'close' if 'close' in df.columns else ('Close' if 'Close' in df.columns else None)
                if not col:
                    res_rows.append({'symbol': sym, 'card_score': 0.5})
                    continue

                close = df[col].dropna()
                if len(close) < 5 or float(close.iloc[-5]) <= 0:
                    res_rows.append({'symbol': sym, 'card_score': 0.5})
                    continue

                c_last = float(close.iloc[-1])
                c_prev = float(close.iloc[-5])
                if np.isnan(c_last) or np.isnan(c_prev) or c_prev <= 0:
                    res_rows.append({'symbol': sym, 'card_score': 0.5})
                    continue

                stock_ret = float((c_last - c_prev) / c_prev * 100)
                if np.isnan(stock_ret) or np.isinf(stock_ret):
                    res_rows.append({'symbol': sym, 'card_score': 0.5})
                    continue

                sec = sector_map.get(sym, 'Market') if isinstance(sector_map, dict) else 'Market'
                beta = sector_beta.get(sec, 1.0)

                macro_impact = ((usdkrw_chg * 0.3) + (wti_chg * 0.3) + (vix_val * 0.4)) * beta * 10.0
                divergence = stock_ret - macro_impact

                card_score = 1.0 / (1.0 + np.exp(np.clip(divergence * 0.1, -50.0, 50.0)))
                if np.isnan(card_score) or np.isinf(card_score):
                    card_score = 0.5
                else:
                    # Check fundamental distress to avoid idiosyncratic collapse value traps
                    fund_dict = kwargs.get('fundamentals_dict') or fundamentals_dict
                    if isinstance(fund_dict, dict) and sym in fund_dict:
                        f_info = fund_dict[sym]
                        op_m = f_info.get('operating_margin', f_info.get('op_margin', np.nan))
                        roe_v = f_info.get('roe', np.nan)
                        if (pd.notna(op_m) and float(op_m) < -0.15) or (pd.notna(roe_v) and float(roe_v) < -0.15):
                            card_score *= 0.70

                    # Asymmetric Upside Booster for extreme macro divergence undervaluation
                    if card_score >= 0.70:
                        card_score = float(np.clip(card_score * 1.10, 0.0, 1.0))
                res_rows.append({'symbol': sym, 'card_score': float(card_score)})
            except Exception as e:
                logger.warning(f"[CARD FACTOR] Error computing score for {sym}: {e}")
                res_rows.append({'symbol': sym, 'card_score': 0.5})

        return make_score_dataframe(res_rows, 'card_score')
