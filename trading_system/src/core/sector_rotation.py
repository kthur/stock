import logging
from typing import Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class SectorRotationEngine:
    """
    Sector Rotation Strategy Engine.
    Computes sector-level relative momentum (1M / 3M returns) and generates
    per-symbol sector rotation scores [0, 1] based on sector momentum ranking.
    """

    def __init__(self):
        # Key Sector Indexes / Representative ETFs
        self.sector_benchmarks = {
            'IT_SEMICON': ['091160.KS', 'XLK'],
            'BATTERY_AUTO': ['305720.KS', 'XLY'],
            'BIO_PHARMA': ['244580.KS', 'XLV'],
            'FINANCE': ['105560.KS', 'XLF'],
            'ENERGY_CHEMICAL': ['011780.KS', 'XLE']
        }

    def compute_sector_momentum_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        sector_map: Optional[Dict[str, str]] = None,
        macro_indicators: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Calculates 1-month (20d) and 3-month (60d) relative momentum with optional Macro Sensitivity adjustments.
        If sector_map is provided, computes a hybrid score:
          0.65 * Sector Average Momentum Rank + 0.35 * Individual Stock Momentum Rank
        Macro Sensitivity adjustments:
          - USD/KRW Surge (>0.5%): Export sectors (IT_SEMICON, BATTERY_AUTO) boosted
          - Oil Surge (>2.0%): Energy sector boosted, Bio/Consumer penalized
          - Yield Surge (US10Y > 4.2% or rising): Finance boosted, high-multiple Tech penalized
        """
        if not prices_dict:
            return pd.DataFrame(columns=['symbol', 'sector_score'])

        eff_sector_map = sector_map or {}

        records = []
        for sym, df in prices_dict.items():
            if df is None or len(df) < 20:
                continue
            try:
                close = df['Close']
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                close = close.dropna()
                if len(close) < 20:
                    continue

                ret_20d = float(close.iloc[-1] / close.iloc[-20] - 1.0) if len(close) >= 20 else 0.0
                ret_60d = float(close.iloc[-1] / close.iloc[-60] - 1.0) if len(close) >= 60 else ret_20d

                # Composite Momentum Score
                mom_score = 0.6 * ret_20d + 0.4 * ret_60d
                sector_name = eff_sector_map.get(sym, "General")
                records.append({'symbol': sym, 'mom_raw': mom_score, 'sector': sector_name})
            except Exception as e:
                logger.debug(f"Sector mom calc failed for {sym}: {e}")
                continue

        if not records:
            return pd.DataFrame(columns=['symbol', 'sector_score'])

        res_df = pd.DataFrame(records)

        if len(res_df) > 1:
            res_df['stock_rank'] = res_df['mom_raw'].rank(pct=True)
            if 'sector' in res_df.columns and res_df['sector'].nunique() > 1:
                # Calculate sector-level mean momentum
                sector_means = res_df.groupby('sector')['mom_raw'].transform('mean')
                res_df['sector_rank'] = sector_means.rank(pct=True)
                res_df['sector_score'] = 0.65 * res_df['sector_rank'] + 0.35 * res_df['stock_rank']
            else:
                res_df['sector_score'] = res_df['stock_rank']
        else:
            res_df['sector_score'] = 0.5

        # Macro Sensitivity Adjustments if macro_indicators is supplied
        if macro_indicators is not None and not macro_indicators.empty and 'sector' in res_df.columns:
            try:
                latest_usdkrw = float(macro_indicators['usdkrw_change'].iloc[-1]) if 'usdkrw_change' in macro_indicators.columns else 0.0
                latest_wti = float(macro_indicators['wti_change'].iloc[-1]) if 'wti_change' in macro_indicators.columns else 0.0
                latest_us10y = float(macro_indicators['us10y'].iloc[-1]) if 'us10y' in macro_indicators.columns else 4.0

                macro_boost = pd.Series(0.0, index=res_df.index)
                if latest_usdkrw > 0.5:
                    macro_boost += res_df['sector'].isin(['IT_SEMICON', 'BATTERY_AUTO']).astype(float) * 0.05
                if latest_wti > 2.0:
                    macro_boost += res_df['sector'].isin(['ENERGY_CHEMICAL']).astype(float) * 0.05
                    macro_boost -= res_df['sector'].isin(['BIO_PHARMA']).astype(float) * 0.03
                if latest_us10y > 4.2:
                    macro_boost += res_df['sector'].isin(['FINANCE']).astype(float) * 0.05

                res_df['sector_score'] = (res_df['sector_score'] + macro_boost).clip(0.0, 1.0)
            except Exception as ex:
                logger.debug(f"Macro sector boost calculation error: {ex}")

        return res_df[['symbol', 'sector_score']]

