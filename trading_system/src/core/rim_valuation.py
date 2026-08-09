"""
src/core/rim_valuation.py
Residual Income Model (RIM / 초과이익모형) Valuation Engine.

Calculates stock intrinsic value (V0) and margin of safety / discount ratio
based on Book Value Per Share (BPS), Return on Equity (ROE), and Required Return (r_e).

Decaying ROE Finite-Horizon Formula (유보금 반영):
  Each year t:
    net_income_t     = BPS_{t-1} × ROE_{t-1}
    excess_income_t  = BPS_{t-1} × (ROE_{t-1} - r_e)
    BPS_t            = BPS_{t-1} + net_income_t × retention_ratio
    ROE_t            = r_e + (ROE_{t-1} - r_e) × (1 - decay_rate)
  V_0 = BPS_0 + Σ PV(excess_income_t) for t=1..years

Discount Ratio = (V_0 - Price) / Price
Scoring: percentile rank [0.0, 1.0] per market.

Earnings Quality Filter (이익의 질 필터):
  순이익에 일회성 이익(영업외수익, 자산매각 등)이 섞이면 ROE가 과대평가되어
  본업 경쟁력이 낮은 기업도 높은 RIM 점수를 받을 수 있다. 이를 방지하기 위해
  operating_income / net_income 비율로 이익의 질을 계산한다.
    - earnings_quality = clip(operating_income / net_income, 0, 1)
    - 지속가능 ROE = ROE × earnings_quality
    - 영업손실(-)인데 순이익(+)이면(일회성 이익으로 순이익 달성) rim_score를 NaN 처리
      (이익의 질 0 → RIM 부적합, 앙상블 가중치 자동 재정규화)
"""
import logging
from typing import Dict, Optional, Any
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# 영업이익/순이익 비율이 이 값 미만이면 순이익의 상당 부분이 영업외/일회성 항목으로
# 판단하여 ROE를 감쇠한다. (0.5 = 순이익의 절반 이상이 영업 이익에서 발생해야 정상)
EARNINGS_QUALITY_MIN_RATIO = 0.5


from src.core.base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta


@register_strategy(
    StrategyMeta(
        strategy_id="rim_valuation",
        display_name="RIM Valuation",
        score_column="rim_score",
        category="factor",
        output_file="rim_predictions.txt",
        requires_fundamentals=True,
        default_regime_weights={
            "BEAR": 0.12, "BEAR_HIGH_VOL": 0.15, "SIDEWAYS_LOW_VOL": 0.08, "BULL_HIGH_VOL": 0.05, "BULL_LOW_VOL": 0.08
        },
    )
)
class RIMValuationEngine(BaseStrategyEngine):
    def __init__(self, default_required_return: float = 0.08, decay_rate: float = 0.10, retention_ratio: float = 0.6, config: Optional[Any] = None):
        """
        :param default_required_return: Baseline required rate of return (r_e), default 8.0%
        :param decay_rate: ROE persistence decay rate per year (0.10 = 10% decay toward r_e)
        :param retention_ratio: Fraction of net income retained (유보율), default 0.6 (60%)
        """
        self.default_required_return = default_required_return
        self.decay_rate = decay_rate
        self.retention_ratio = retention_ratio

    def derive_required_return(self, market: str = "KOSPI", us10y_yield: Optional[float] = None) -> float:
        """
        Derives dynamic required return r_e based on US 10Y Treasury Yield + Equity Risk Premium (ERP).
        """
        base_rf = (us10y_yield / 100.0) if (us10y_yield is not None and us10y_yield > 0) else 0.04
        erp = 0.05 if market == 'SP500' else 0.06
        dynamic_re = np.clip(base_rf + erp, 0.06, 0.15)
        return float(dynamic_re)

    def calculate_intrinsic_value(
        self,
        bps: float,
        roe: float,
        required_return: Optional[float] = None,
        years: int = 8,
    ) -> float:
        """
        Computes RIM intrinsic value V_0 per share.
        Uses finite-horizon decaying ROE with retained earnings (유보금) accumulation.
        Returns np.nan if BPS is invalid or non-positive.
        """
        r_e = required_return if (required_return is not None and required_return > 0) else self.default_required_return

        if np.isnan(bps) or bps <= 0:
            return np.nan

        if np.isnan(roe):
            roe = r_e  # Neutral assumption: ROE = r_e => V_0 = BPS

        if self.decay_rate <= 0:
            # Constant ROE Perpetuity Formula (legacy, no 유보금):
            # V_0 = BPS * (1 + (ROE - r_e) / r_e)
            if r_e <= 0:
                return bps
            excess_return_ratio = (roe - r_e) / r_e
            excess_return_ratio = max(-0.8, min(5.0, excess_return_ratio))
            return bps * (1.0 + excess_return_ratio)
        else:
            # Finite horizon / Decaying ROE with 유보금 retention
            pv_excess = 0.0
            current_bps = bps
            current_roe = roe
            for t in range(1, years + 1):
                net_income = current_bps * current_roe
                excess_income = current_bps * (current_roe - r_e)
                pv_excess += excess_income / ((1.0 + r_e) ** t)
                # BPS grows by retained positive net income (or decreases by net losses)
                retention = self.retention_ratio if net_income > 0 else 1.0
                current_bps += net_income * retention
                current_roe = r_e + (current_roe - r_e) * (1.0 - self.decay_rate)
            # Standard RIM intrinsic value V0 = BPS0 + Sum(PV of Excess Income).
            # Terminal value beyond horizon N assumes ROE = r_e (excess income = 0).
            return bps + pv_excess

    def compute_rim_scores(
        self,
        features_df: pd.DataFrame,
        symbol_market_map: Optional[Dict[str, str]] = None,
        required_return: Optional[float] = None,
        us10y_yield: Optional[float] = None,
    ) -> pd.DataFrame:
        """
        Computes RIM intrinsic values and percentile scores using finite-horizon decaying ROE model
        with 유보금 (retained earnings) accumulation.
        Missing fundamental BPS yields NaN rim_score for dynamic ensemble weight renormalization.
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

        # Ensure Market Column
        if 'market' not in df.columns:
            if symbol_market_map:
                df['market'] = df['symbol'].map(symbol_market_map).fillna('KOSPI')
            else:
                df['market'] = 'KOSPI'

        # Ensure Close / Price
        if 'Close' not in df.columns:
            df['Close'] = df.get('price', np.nan)

        # Handle BPS: Set to NaN if missing or non-positive
        if 'bps' not in df.columns:
            if 'book_value' in df.columns and 'shares_outstanding' in df.columns:
                df['bps'] = (df['book_value'] / df['shares_outstanding']).replace([np.inf, -np.inf], np.nan)
            elif 'eps' in df.columns and 'roe' in df.columns:
                df['bps'] = (df['eps'] / df['roe']).replace([np.inf, -np.inf], np.nan)
            else:
                df['bps'] = np.nan
        df['bps'] = df['bps'].replace([np.inf, -np.inf, 0], np.nan)
        # Fallback BPS from eps/roe when book_value is unavailable (DB default=0)
        nan_mask = df['bps'].isna()
        if nan_mask.any() and 'eps' in df.columns and 'roe' in df.columns:
            fallback = (df.loc[nan_mask, 'eps'] / df.loc[nan_mask, 'roe']).replace([np.inf, -np.inf], np.nan)
            df.loc[nan_mask, 'bps'] = fallback
        # Only fill NaN BPS with Close*0.8 when fundamentals exist for that stock but BPS is temporarily missing
        # Never invent BPS from price alone — that creates an artificial -20% discount for all symbols

        # Handle ROE
        if 'roe' not in df.columns:
            if 'eps' in df.columns and 'bps' in df.columns:
                df['roe'] = (df['eps'] / df['bps']).replace([np.inf, -np.inf], np.nan)
            else:
                df['roe'] = np.nan
        df['roe'] = df['roe'].replace([np.inf, -np.inf], np.nan).fillna(self.default_required_return)

        # ---- Earnings Quality Filter (이익의 질 필터) ----
        # 순이익이 영업이익보다 크게 높으면(일회성 이익 포함) ROE를 감쇠하고,
        # 영업손실인데 순이익이 양수이면(전적으로 영업외/일회성 이익) RIM 점수를 무효화한다.
        df['earnings_quality'] = 1.0
        df['rim_filter_reason'] = ''
        has_op_inc = 'operating_income' in df.columns
        has_net_inc = 'net_income' in df.columns

        if has_op_inc or has_net_inc:
            op_inc = df['operating_income'].replace([np.inf, -np.inf], np.nan) if has_op_inc else pd.Series(np.nan, index=df.index)
            net_inc = df['net_income'].replace([np.inf, -np.inf], np.nan) if has_net_inc else pd.Series(np.nan, index=df.index)

            # earnings_quality: 0.0 ~ 1.0 (영업이익/순이익 비율, 음수 순이익은 1.0 보존)
            with np.errstate(divide='ignore', invalid='ignore'):
                op_arr = op_inc.to_numpy()
                net_arr = net_inc.to_numpy()
                eq_ratio = np.where(
                    (net_arr > 0) & ~np.isnan(op_arr),
                    np.clip(op_arr / net_arr, 0.0, 1.0),
                    1.0,
                )
            df['earnings_quality'] = eq_ratio

            # 영업손실(-) & 순이익 양수(+): 순이익이 전적으로 일회성/영업외 이익 → RIM 부적합
            suspicious = (op_inc <= 0) & (net_inc > 0)
            # 영업이익/순이익 비율이 임계 미만 → 이익의 질 낮음 → ROE 감쇠
            low_quality = pd.Series(eq_ratio, index=df.index) < EARNINGS_QUALITY_MIN_RATIO

            df.loc[suspicious, 'rim_filter_reason'] = 'LOW_EARNINGS_QUALITY'
            df.loc[low_quality & ~suspicious, 'rim_filter_reason'] = 'QUALITY_ADJUSTED'
            # 이익의 질이 낮은 종목만 ROE 감쇠 (정상 기업 ROE 불변)
            df.loc[low_quality, 'roe'] = df.loc[low_quality, 'roe'] * eq_ratio[low_quality.to_numpy()]
            # 영업손실 + 순이익 양수 → 지속가능 이익 없음으로 간주
            df.loc[suspicious, 'roe'] = 0.0

        n_suspicious = int(df['rim_filter_reason'].eq('LOW_EARNINGS_QUALITY').sum())
        n_adjusted = int(df['rim_filter_reason'].eq('QUALITY_ADJUSTED').sum())
        if n_suspicious or n_adjusted:
            logger.info(
                f"Earnings quality filter: {n_suspicious} symbols invalidated (one-off gains), "
                f"{n_adjusted} symbols ROE-adjusted"
            )

        # Vectorized calculation per market with dynamic r_e
        v0_list = []
        discount_list = []

        for idx, row in df.iterrows():
            mkt = row.get('market', 'KOSPI')
            if us10y_yield is not None:
                r_e = self.derive_required_return(mkt, us10y_yield)
            elif required_return is not None and required_return > 0:
                r_e = required_return
            else:
                r_e = self.default_required_return

            b = float(row['bps']) if pd.notna(row['bps']) else np.nan
            r = float(row['roe']) if pd.notna(row['roe']) else r_e
            p = float(row['Close']) if pd.notna(row['Close']) else np.nan

            v0 = self.calculate_intrinsic_value(b, r, required_return=r_e)
            v0_list.append(v0)

            if pd.notna(p) and p > 0 and pd.notna(v0) and v0 > 0:
                disc = (v0 - p) / p
            else:
                disc = np.nan
            discount_list.append(disc)

        df['intrinsic_value'] = v0_list
        df['discount_ratio'] = discount_list

        # Transform Discount Ratio to Percentile Score [0.0, 1.0] per Market
        df['rim_score'] = df.groupby('market')['discount_ratio'].rank(pct=True, ascending=True).fillna(0.5)

        # 영업손실 + 순이익 양수(일회성 이익 의존) 종목은 RIM 점수 무효화
        # → 앙상블에서 자동 제외되고 가중치가 재정규화된다.
        invalid_mask = df['rim_filter_reason'].eq('LOW_EARNINGS_QUALITY')
        if invalid_mask.any():
            df.loc[invalid_mask, ['rim_score', 'discount_ratio']] = np.nan
            logger.info(f"RIM scores invalidated for {int(invalid_mask.sum())} symbols (low earnings quality)")

        out_cols = ['symbol', 'market', 'Close', 'bps', 'roe', 'earnings_quality', 'rim_filter_reason',
                    'intrinsic_value', 'discount_ratio', 'rim_score']
        return df[[c for c in out_cols if c in df.columns]]

    def compute_scores(
        self,
        prices_dict: Any = None,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        try:
            features_df = kwargs.get("features_df", kwargs.get("universe", pd.DataFrame()))
            if features_df.empty and isinstance(prices_dict, pd.DataFrame):
                features_df = prices_dict
            return self.compute_rim_scores(features_df)
        except Exception as e:
            logger.warning(f"[RIMValuationEngine] compute_scores failed: {e}")
            return pd.DataFrame(columns=["symbol", "rim_score"])

