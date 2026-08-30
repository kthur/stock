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

        from .base_strategy import make_score_dataframe
        if not prices_dict or not isinstance(prices_dict, dict):
            return make_score_dataframe({}, 'card_score')

        def _safe_macro(col):
            if indicator_df is None:
                return 0.0
            if isinstance(indicator_df, dict):
                v = float(indicator_df.get(col, 0.0))
                return 0.0 if (np.isnan(v) or np.isinf(v)) else v
            elif isinstance(indicator_df, pd.DataFrame):
                if not indicator_df.empty and col in indicator_df.columns and not indicator_df[col].dropna().empty:
                    s = indicator_df[col].dropna()
                    # If computing multi-day macro impact and history exists, take 5-day rolling change
                    if len(s) >= 5 and ('change' in col or 'pct' in col or col in ['usdkrw', 'wti']):
                        base_val = float(s.iloc[-5])
                        v = float((s.iloc[-1] / base_val - 1.0) * 100.0) if (base_val > 0 and 'change' not in col and 'pct' not in col) else float(s.tail(5).sum())
                    else:
                        v = float(s.iloc[-1])
                    return 0.0 if (np.isnan(v) or np.isinf(v)) else v
            return 0.0

        # Extract latest macro indicators with safe scaling (supports raw or change keys)
        usdkrw_chg = _safe_macro('usdkrw_change') or _safe_macro('usdkrw_pct') or 0.0
        wti_chg = _safe_macro('wti_change') or _safe_macro('wti_pct') or 0.0

        # Standardize VIX shock to percentage scale matching FX and commodities
        vix_raw = _safe_macro('vix') or _safe_macro('vix_raw')
        vix_change = _safe_macro('vix_change') or _safe_macro('vix_pct')
        if vix_raw and vix_raw > 0:
            vix_pct_shock = ((vix_raw - 20.0) / 20.0) * 10.0  # Normalized % shock proxy
        elif vix_change:
            vix_pct_shock = vix_change if abs(vix_change) > 1.0 else (vix_change * 100.0)
        else:
            vix_pct_shock = 0.0

        DEFAULT_SECTOR_BETAS = {
            # GICS Sectors (US & Global)
            'Information Technology': 1.4, 'IT': 1.3, 'Technology': 1.4, 'Semiconductor': 1.5,
            'Financials': 0.8, 'Finance': 0.7, 'Financial Services': 0.8,
            'Energy': 1.4, 'Oil & Gas': 1.4,
            'Materials': 1.1, 'Chemical': 0.9, 'Steel': 0.8,
            'Industrials': 1.1, 'Automotive': 1.1, 'Shipbuilding': 1.2,
            'Consumer Discretionary': 1.2, 'Consumer Staples': 0.6,
            'Health Care': 0.7, 'Healthcare': 0.7, 'Biotechnology': 1.2,
            'Communication Services': 1.1, 'Communication': 1.0,
            'Utilities': 0.5, 'Real Estate': 0.7,
            # KRX Sectors (Korean)
            '전기전자': 1.4, '반도체': 1.5, 'IT하드웨어': 1.3, 'IT소프트웨어': 1.2,
            '화학': 0.9, '철강및금속': 0.8, '기계': 1.1, '운수장비': 1.1,
            '운수창고': 1.0, '유통업': 0.9, '건설업': 0.8, '통신업': 0.6,
            '금융업': 0.7, '증권': 1.2, '보험': 0.7, '은행': 0.7,
            '의약품': 0.8, '의료정밀': 0.9, '음식료품': 0.6, '섬유의복': 0.7,
            '전기가스업': 0.5, '서비스업': 1.0, '제조업': 1.0, 'Market': 1.0
        }

        scores = {}
        for sym, df in prices_dict.items():
            try:
                if df is None or df.empty:
                    scores[sym] = 0.5
                    continue

                col = 'close' if 'close' in df.columns else ('Close' if 'Close' in df.columns else None)
                if not col:
                    scores[sym] = 0.5
                    continue

                close = df[col].dropna()
                if len(close) < 5 or float(close.iloc[-5]) <= 0:
                    scores[sym] = 0.5
                    continue

                c_last = float(close.iloc[-1])
                c_prev = float(close.iloc[-5])
                if np.isnan(c_last) or np.isnan(c_prev) or c_prev <= 0:
                    scores[sym] = 0.5
                    continue

                stock_ret = float((c_last - c_prev) / c_prev * 100)
                if np.isnan(stock_ret) or np.isinf(stock_ret):
                    scores[sym] = 0.5
                    continue

                sec = sector_map.get(sym, 'Market') if isinstance(sector_map, dict) else 'Market'
                base_beta = DEFAULT_SECTOR_BETAS.get(sec, DEFAULT_SECTOR_BETAS.get(str(sec).strip(), 1.0))

                # Dynamic rolling empirical beta adjustment if price history is sufficient
                if len(close) >= 20:
                    ret_series = close.pct_change().dropna()
                    stock_vol = float(ret_series.std()) if len(ret_series) > 5 else 0.02
                    stock_vol = stock_vol if (np.isfinite(stock_vol) and stock_vol > 0) else 0.02
                    # Scale beta proportionally to realized volatility relative to baseline 2% daily vol
                    vol_scale = float(np.clip(stock_vol / 0.020, 0.5, 2.0))
                    beta = float(np.clip(0.4 * base_beta + 0.6 * (base_beta * vol_scale), 0.1, 3.0))
                else:
                    beta = float(np.clip(base_beta, 0.1, 3.0))

                # Dynamic rolling OLS macro impact
                macro_impact = None
                if indicator_df is not None and isinstance(indicator_df, pd.DataFrame) and len(close) >= 60 and len(indicator_df) >= 60:
                    try:
                        ret_60 = close.pct_change().tail(60).dropna()

                        # Align indicators to stock price dates using reindex with ffill
                        aligned_indicators = indicator_df.reindex(ret_60.index, method='ffill')

                        # Defensive guard: if all are NaN after alignment, fall through to heuristic
                        if not (aligned_indicators.empty or aligned_indicators.isna().all().all()):
                            fx_60 = aligned_indicators.get('usdkrw_change', aligned_indicators.get('usdkrw_pct', pd.Series(0.0, index=aligned_indicators.index))) / 100.0
                            wti_60 = aligned_indicators.get('wti_change', aligned_indicators.get('wti_pct', pd.Series(0.0, index=aligned_indicators.index))) / 100.0
                            vix_60 = aligned_indicators.get('vix_change', aligned_indicators.get('vix_pct', pd.Series(0.0, index=aligned_indicators.index))) / 100.0

                            df_ols = pd.DataFrame({'R': ret_60, 'FX': fx_60, 'WTI': wti_60, 'VIX': vix_60}).dropna()
                            if len(df_ols) >= 30:
                                import statsmodels.api as sm
                                X = sm.add_constant(df_ols[['FX', 'WTI', 'VIX']])
                                model = sm.OLS(df_ols['R'], X).fit()
                                macro_impact = (model.params.get('FX', 0.0) * usdkrw_chg + model.params.get('WTI', 0.0) * wti_chg - model.params.get('VIX', 0.0) * vix_pct_shock)
                    except Exception:
                        pass

                if macro_impact is None:
                    sec_str = str(sec).lower()
                    if any(kw in sec_str for kw in ['energy', 'oil', 'gas', 'chem', '정유', '화학', '에너지']):
                        w_fx, w_wti, w_vix = 0.20, 0.60, 0.20
                    elif any(kw in sec_str for kw in ['tech', 'semi', 'it', 'it서비스', '반도체', '전기전자']):
                        w_fx, w_wti, w_vix = 0.45, 0.15, 0.40
                    elif any(kw in sec_str for kw in ['utility', 'defensive', 'consumer staple', '통신', '유틸리티', '음식료']):
                        w_fx, w_wti, w_vix = 0.20, 0.20, 0.60
                    else:
                        w_fx, w_wti, w_vix = 0.35, 0.35, 0.30
                    macro_impact = ((usdkrw_chg * w_fx) + (wti_chg * w_wti) - (vix_pct_shock * w_vix)) * beta

                raw_div = stock_ret - macro_impact
                divergence = float(np.clip(raw_div, -200.0, 200.0)) if np.isfinite(raw_div) else 0.0

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

                    # Asymmetric Upside Booster for extreme macro divergence undervaluation (smooth continuous)
                    smooth_boost = 1.0 + 0.10 / (1.0 + np.exp(-12.0 * (card_score - 0.70)))
                    card_score = float(np.clip(card_score * smooth_boost, 0.0, 1.0))
                scores[sym] = float(card_score)
            except Exception as e:
                logger.warning(f"[CARD FACTOR] Error computing score for {sym}: {e}")
                scores[sym] = 0.5

        return make_score_dataframe(scores, 'card_score')
