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
        sector_map: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        """
        Calculates 1-month (20d) and 3-month (60d) relative momentum for symbols,
        scoring symbols in outperforming sectors higher [0, 1].
        """
        if not prices_dict:
            return pd.DataFrame(columns=['symbol', 'sector_score'])

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
                records.append({'symbol': sym, 'mom_raw': mom_score})
            except Exception as e:
                logger.debug(f"Sector mom calc failed for {sym}: {e}")
                continue

        if not records:
            return pd.DataFrame(columns=['symbol', 'sector_score'])

        res_df = pd.DataFrame(records)
        if len(res_df) > 1:
            res_df['sector_score'] = res_df['mom_raw'].rank(pct=True)
        else:
            res_df['sector_score'] = 0.5

        return res_df[['symbol', 'sector_score']]
