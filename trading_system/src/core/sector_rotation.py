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

    # Standard 11 GICS Sector Mapping Table (KRX Raw Sectors → GICS 11 Sectors)
    GICS_SECTOR_MAP = {
        # Information Technology
        '전기전자': 'Information Technology', '반도체': 'Information Technology',
        '소프트웨어': 'Information Technology', 'IT': 'Information Technology',
        'Information Technology': 'Information Technology', 'IT_SEMICON': 'Information Technology',
        # Financials
        '금융업': 'Financials', '은행': 'Financials', '증권': 'Financials', '보험': 'Financials',
        'Financials': 'Financials', 'FINANCE': 'Financials',
        # Health Care
        '의약품': 'Health Care', '제약': 'Health Care', '바이오': 'Health Care',
        '의료정밀': 'Health Care', 'Health Care': 'Health Care', 'BIO_PHARMA': 'Health Care',
        # Consumer Discretionary
        '운수장비': 'Consumer Discretionary', '자동차': 'Consumer Discretionary',
        '유통업': 'Consumer Discretionary', 'Consumer Discretionary': 'Consumer Discretionary',
        'BATTERY_AUTO': 'Consumer Discretionary',
        # Industrials
        '기계': 'Industrials', '건설업': 'Industrials', '운수창고': 'Industrials',
        '조선': 'Industrials', '방산': 'Industrials', 'Industrials': 'Industrials',
        # Materials
        '화학': 'Materials', '철강금속': 'Materials', '비금속광물': 'Materials',
        'Materials': 'Materials', 'ENERGY_CHEMICAL': 'Materials',
        # Energy
        '에너지': 'Energy', '정유': 'Energy', 'Energy': 'Energy',
        # Communication Services
        '통신업': 'Communication Services', '미디어': 'Communication Services',
        'Communication Services': 'Communication Services',
        # Consumer Staples
        '음식료품': 'Consumer Staples', '섬유의복': 'Consumer Staples',
        'Consumer Staples': 'Consumer Staples',
        # Utilities
        '전기가스업': 'Utilities', '전력': 'Utilities', 'Utilities': 'Utilities',
        # Real Estate
        '부동산': 'Real Estate', '리츠': 'Real Estate', 'Real Estate': 'Real Estate',
    }

    @classmethod
    def normalize_sector(cls, raw_sector: Optional[str]) -> str:
        """Normalizes KRX or raw sector string to 11 standard GICS sector names."""
        if not raw_sector or not isinstance(raw_sector, str):
            return "General"
        raw_clean = raw_sector.strip()
        for key, gics in cls.GICS_SECTOR_MAP.items():
            if key in raw_clean or raw_clean in key:
                return gics
        return "General"

    def compute_sector_momentum_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        sector_map: Optional[Dict[str, str]] = None,
        macro_indicators: Optional[pd.DataFrame] = None,
        regime_label: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Calculates 1-month (20d) and 3-month (60d) relative momentum with GICS 11 Sector Mapping,
        Intra-Sector Dispersion weighting, and Macro/Cycle Sensitivity adjustments.
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
                raw_sec = eff_sector_map.get(sym, "General")
                norm_sec = self.normalize_sector(raw_sec)
                records.append({'symbol': sym, 'mom_raw': mom_score, 'sector': norm_sec})
            except Exception as e:
                logger.debug(f"Sector mom calc failed for {sym}: {e}")
                continue

        if not records:
            return pd.DataFrame(columns=['symbol', 'sector_score'])

        res_df = pd.DataFrame(records)

        if len(res_df) > 1:
            res_df['stock_rank'] = res_df['mom_raw'].rank(pct=True)
            if 'sector' in res_df.columns and res_df['sector'].nunique() > 1:
                # Sector mean momentum
                sector_means = res_df.groupby('sector')['mom_raw'].transform('mean')
                res_df['sector_rank'] = sector_means.rank(pct=True)

                # Intra-Sector Dispersion weighting: High dispersion -> favor individual stock rank
                sector_disp = res_df.groupby('sector')['mom_raw'].transform('std').fillna(0.0)
                stock_weight = pd.Series(0.35, index=res_df.index)
                stock_weight[sector_disp > 0.05] = 0.60
                sector_weight = 1.0 - stock_weight

                res_df['sector_score'] = sector_weight * res_df['sector_rank'] + stock_weight * res_df['stock_rank']
            else:
                res_df['sector_score'] = res_df['stock_rank']
        else:
            res_df['sector_score'] = 0.5

        # Macro Sensitivity & Cycle Adjustments
        if 'sector' in res_df.columns:
            macro_boost = pd.Series(0.0, index=res_df.index)

            # Macro indicators boost
            if macro_indicators is not None and not macro_indicators.empty:
                try:
                    latest_usdkrw = float(macro_indicators['usdkrw_change'].iloc[-1]) if 'usdkrw_change' in macro_indicators.columns else 0.0
                    latest_wti = float(macro_indicators['wti_change'].iloc[-1]) if 'wti_change' in macro_indicators.columns else 0.0
                    latest_us10y = float(macro_indicators['us10y'].iloc[-1]) if 'us10y' in macro_indicators.columns else 4.0

                    if latest_usdkrw > 0.5:
                        macro_boost += res_df['sector'].isin(['Information Technology', 'Consumer Discretionary']).astype(float) * 0.05
                    if latest_wti > 2.0:
                        macro_boost += res_df['sector'].isin(['Energy', 'Materials']).astype(float) * 0.05
                        macro_boost -= res_df['sector'].isin(['Health Care', 'Consumer Staples']).astype(float) * 0.03
                    if latest_us10y > 4.2:
                        macro_boost += res_df['sector'].isin(['Financials']).astype(float) * 0.05
                except Exception as ex:
                    logger.debug(f"Macro sector boost error: {ex}")

            # Regime cycle boost
            if regime_label and 'BEAR' in regime_label:
                macro_boost += res_df['sector'].isin(['Utilities', 'Health Care', 'Consumer Staples']).astype(float) * 0.06
            elif regime_label and 'BULL' in regime_label:
                macro_boost += res_df['sector'].isin(['Information Technology', 'Financials', 'Consumer Discretionary']).astype(float) * 0.05

            res_df['sector_score'] = (res_df['sector_score'] + macro_boost).clip(0.0, 1.0)

        return res_df[['symbol', 'sector_score']]

