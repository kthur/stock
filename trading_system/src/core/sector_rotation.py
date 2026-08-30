import logging
from typing import Dict, Optional, Any
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


from src.core.base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta


@register_strategy(
    StrategyMeta(
        strategy_id="sector_rotation",
        display_name="Sector Rotation",
        score_column="sector_score",
        category="factor",
        output_file="sector_predictions.txt",
        default_regime_weights={
            "BEAR": 0.05, "BEAR_HIGH_VOL": 0.05, "SIDEWAYS_LOW_VOL": 0.08, "BULL_HIGH_VOL": 0.10, "BULL_LOW_VOL": 0.08
        },
    )
)
class SectorRotationEngine(BaseStrategyEngine):
    """
    Sector Rotation Strategy Engine.
    Computes sector-level relative momentum (1M / 3M returns) and generates
    per-symbol sector rotation scores [0, 1] based on sector momentum ranking.
    """

    def __init__(self, w_20d: float = 0.6, w_60d: float = 0.4, config: Optional[Any] = None):
        # Key Sector Indexes / Representative ETFs
        self.w_20d = w_20d
        self.w_60d = w_60d
        self.sector_benchmarks = {
            'IT_SEMICON': ['091160.KS', 'XLK'],
            'BATTERY_AUTO': ['305720.KS', 'XLY'],
            'BIO_PHARMA': ['244580.KS', 'XLV'],
            'FINANCE': ['105560.KS', 'XLF'],
            'ENERGY_CHEMICAL': ['011780.KS', 'XLE']
        }

    # Curated Symbol-to-GICS Sector Registry for high-priority Global/KRX Symbols
    CURATED_SYMBOL_SECTOR_MAP = {
        # Critical test/benchmark and global multi-market symbols
        'MT': 'Materials',              # ArcelorMittal (철강/소재)
        'FANG': 'Energy',               # Diamondback Energy (에너지/원유개발)
        'XPRO': 'Energy',               # Expro Group Holdings (에너지 시추/서비스)
        'MGTX': 'Health Care',          # MeiraGTx Holdings (바이오/유전자 치료제)
        '001450': 'Financials',         # 현대해상 (손해보험)
        '003450': 'Financials',         # 현대차증권 (증권/금융)
        '000720': 'Industrials',        # 현대건설 (건설/산업재)
        '010620': 'Industrials',        # 현대미포조선 (조선/산업재)
        '267250': 'Industrials',        # HD현대일렉트릭 (전력기기/산업재)
        '005490': 'Materials',          # POSCO홀딩스 (철강/소재)
        '004020': 'Materials',          # 현대제철 (철강/소재)
        '096770': 'Energy',             # SK이노베이션 (에너지/정유)
        '010950': 'Energy',             # S-Oil (에너지/정유)
        '005930': 'Information Technology', # 삼성전자
        '000660': 'Information Technology', # SK하이닉스
        '005380': 'Consumer Discretionary', # 현대차
        '000270': 'Consumer Discretionary', # 기아
        '012330': 'Consumer Discretionary', # 현대모비스
        '057050': 'Consumer Discretionary', # 현대홈쇼핑
        '069960': 'Consumer Discretionary', # 현대백화점
        '207940': 'Health Care',         # 삼성바이오로직스
        '068270': 'Health Care',         # 셀트리온
        '035420': 'Communication Services', # NAVER
        '035720': 'Communication Services', # 카카오
        '015760': 'Utilities',          # 한국전력
        '036460': 'Utilities',          # 한국가스공사
        '105560': 'Financials',         # KB금융
        '055550': 'Financials',         # 신한지주
        '086790': 'Financials',         # 하나금융지주
        '316140': 'Financials',         # 우리금융지주
        '000810': 'Financials',         # 삼성화재
        '088350': 'Financials',         # 한화생명
        '003540': 'Financials',         # 대신증권
        '005940': 'Financials',         # NH투자증권
        '039490': 'Financials',         # 키움증권
        '000100': 'Health Care',        # 유한양행
        '128940': 'Health Care',        # 한미약품
        '326030': 'Health Care',        # SK바이오팜
        '302440': 'Health Care',        # SK바이오사이언스
        '097950': 'Consumer Staples',   # CJ제일제당
        '004370': 'Consumer Staples',   # 농심
        '005300': 'Consumer Staples',   # 롯데칠성
        '007310': 'Consumer Staples',   # 오뚜기
        '271560': 'Consumer Staples',   # 오리온
        '051900': 'Consumer Staples',   # LG생활건강
        '090430': 'Consumer Staples',   # 아모레퍼시픽
        # US Key Universe
        'NVDA': 'Information Technology', 'AAPL': 'Information Technology', 'MSFT': 'Information Technology',
        'AVGO': 'Information Technology', 'AMD': 'Information Technology', 'INTC': 'Information Technology',
        'QCOM': 'Information Technology', 'TSM': 'Information Technology', 'ASML': 'Information Technology',
        'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy', 'SLB': 'Energy', 'EOG': 'Energy', 'OXY': 'Energy',
        'JPM': 'Financials', 'BAC': 'Financials', 'WFC': 'Financials', 'GS': 'Financials', 'MS': 'Financials',
        'BLK': 'Financials', 'PGR': 'Financials', 'CB': 'Financials', 'TRV': 'Financials',
        'LLY': 'Health Care', 'UNH': 'Health Care', 'JNJ': 'Health Care', 'ABBV': 'Health Care', 'MRK': 'Health Care',
        'LIN': 'Materials', 'SHW': 'Materials', 'FCX': 'Materials', 'NEM': 'Materials', 'NUE': 'Materials',
        'CAT': 'Industrials', 'GE': 'Industrials', 'UNP': 'Industrials', 'HON': 'Industrials', 'RTX': 'Industrials',
        'AMZN': 'Consumer Discretionary', 'TSLA': 'Consumer Discretionary', 'HD': 'Consumer Discretionary',
        'PG': 'Consumer Staples', 'COST': 'Consumer Staples', 'WMT': 'Consumer Staples', 'KO': 'Consumer Staples',
        'GOOGL': 'Communication Services', 'GOOG': 'Communication Services', 'META': 'Communication Services',
        'NEE': 'Utilities', 'SO': 'Utilities', 'DUK': 'Utilities',
        'PLD': 'Real Estate', 'AMT': 'Real Estate', 'EQIX': 'Real Estate'
    }

    # Standard 11 GICS Sector Mapping Table (KRX Raw Sectors + US Yahoo/FDR Sectors → GICS 11 Sectors)
    GICS_SECTOR_MAP = {
        # Information Technology
        '전기전자': 'Information Technology', '반도체': 'Information Technology',
        '소프트웨어': 'Information Technology', 'IT': 'Information Technology',
        'Information Technology': 'Information Technology', 'IT_SEMICON': 'Information Technology',
        'Technology': 'Information Technology', 'Tech': 'Information Technology',
        # Financials
        '금융업': 'Financials', '은행': 'Financials', '증권': 'Financials', '보험': 'Financials',
        '손해보험': 'Financials', '생명보험': 'Financials', '금융': 'Financials',
        'Financials': 'Financials', 'FINANCE': 'Financials', 'Financial Services': 'Financials',
        'Financial': 'Financials',
        # Health Care
        '의약품': 'Health Care', '제약': 'Health Care', '바이오': 'Health Care',
        '의료정밀': 'Health Care', 'Health Care': 'Health Care', 'BIO_PHARMA': 'Health Care',
        'Healthcare': 'Health Care', 'Biotechnology': 'Health Care', 'Bio': 'Health Care',
        # Consumer Discretionary
        '운수장비': 'Consumer Discretionary', '자동차': 'Consumer Discretionary',
        '유통업': 'Consumer Discretionary', 'Consumer Discretionary': 'Consumer Discretionary',
        'BATTERY_AUTO': 'Consumer Discretionary', 'Consumer Cyclical': 'Consumer Discretionary',
        'Consumer Services': 'Consumer Discretionary',
        # Industrials
        '기계': 'Industrials', '건설업': 'Industrials', '운수창고': 'Industrials',
        '조선': 'Industrials', '방산': 'Industrials', 'Industrials': 'Industrials',
        'Industrial': 'Industrials', 'Capital Goods': 'Industrials',
        # Materials
        '화학': 'Materials', '철강금속': 'Materials', '비금속광물': 'Materials',
        'Materials': 'Materials', 'ENERGY_CHEMICAL': 'Materials', 'Basic Materials': 'Materials',
        '철강': 'Materials',
        # Energy
        '에너지': 'Energy', '정유': 'Energy', 'Energy': 'Energy', 'Oil & Gas': 'Energy',
        # Communication Services
        '통신업': 'Communication Services', '미디어': 'Communication Services',
        'Communication Services': 'Communication Services', 'Communication': 'Communication Services',
        'Telecommunications': 'Communication Services',
        # Consumer Staples
        '음식료품': 'Consumer Staples', '섬유의복': 'Consumer Staples',
        'Consumer Staples': 'Consumer Staples', 'Consumer Defensive': 'Consumer Staples',
        'Consumer Non-Cyclical': 'Consumer Staples', '식음료': 'Consumer Staples',
        # Utilities
        '전기가스업': 'Utilities', '전력': 'Utilities', 'Utilities': 'Utilities',
        # Real Estate
        '부동산': 'Real Estate', '리츠': 'Real Estate', 'Real Estate': 'Real Estate',
    }

    @classmethod
    def _get_gics_sector(cls, ticker: str, metadata: dict) -> str:
        """Looks up a GICS sector code from stock metadata before falling back to string matching."""
        if metadata and ticker in metadata:
            raw_sector = metadata[ticker].get('sector') or metadata[ticker].get('sector_code')
            name = metadata[ticker].get('name')
            if raw_sector or name:
                norm = cls.normalize_sector(raw_sector=str(raw_sector) if raw_sector else None, symbol=ticker, name=name)
                if norm != 'General':
                    return norm
        return cls.normalize_sector(raw_sector=None, symbol=ticker)

    @classmethod
    def normalize_sector(cls, raw_sector: Optional[str], symbol: Optional[str] = None, name: Optional[str] = None) -> str:
        """
        Normalizes sector classification to 11 standard GICS sectors with high-precision
        curated registry and priority-based token classification.
        """
        # 1. Curated Symbol Registry Check
        if symbol:
            clean_sym = str(symbol).strip().upper()
            if clean_sym in cls.CURATED_SYMBOL_SECTOR_MAP:
                return cls.CURATED_SYMBOL_SECTOR_MAP[clean_sym]
            sym_prefix = clean_sym.split('.')[0]
            if sym_prefix in cls.CURATED_SYMBOL_SECTOR_MAP:
                return cls.CURATED_SYMBOL_SECTOR_MAP[sym_prefix]

        # 2. Exact/Clean Sector Map Check
        if raw_sector and isinstance(raw_sector, str) and raw_sector.strip() not in ('', 'General', 'N/A', 'nan'):
            raw_clean = raw_sector.strip()
            if raw_clean in cls.GICS_SECTOR_MAP:
                return cls.GICS_SECTOR_MAP[raw_clean]
            for k, v in cls.GICS_SECTOR_MAP.items():
                if k.lower() == raw_clean.lower():
                    return v

        # 3. High-Precision Priority Name/Keyword Classification
        search_text = f"{name or ''} {raw_sector or ''}".lower()
        if search_text.strip():
            # Financials (Insurance/Banking takes precedence over corporate group prefix like '현대')
            if any(k in search_text for k in ["해상", "화재", "보험", "생명", "증권", "은행", "금융", "캐피탈", "카드", "저축은행", "자산운용", "insurance", "bancorp", "bank", "financial", "credit"]):
                return 'Financials'
            # Health Care / Biotech
            if any(k in search_text for k in ["제약", "바이오", "의약", "생명과학", "치료제", "진단", "임상", "therapeutics", "pharma", "biotech", "genomics", "medical", "oncology"]):
                return 'Health Care'
            # Energy (Oil/Gas)
            if any(k in search_text for k in ["정유", "석유", "원유", "에너지", "s-oil", "oil", "energy", "petroleum", "drilling", "exploration"]):
                return 'Energy'
            # Materials (Steel/Chemicals/Mining)
            if any(k in search_text for k in ["제철", "철강", "화학", "유화", "소재", "비철", "알루미늄", "아연", "시멘트", "포스코", "posco", "steel", "chemical", "materials", "mining", "arcelor"]):
                return 'Materials'
            # Utilities
            if any(k in search_text for k in ["전력", "전기가스", "가스공사", "발전", "utility", "electric", "power", "utilities"]):
                return 'Utilities'
            # Industrials (Construction/Shipbuilding/Defense/Machinery)
            if any(k in search_text for k in ["건설", "엔지니어링", "조선", "중공업", "해양", "방산", "기계", "운수창고", "로지스틱스", "aerospace", "defense", "engineering", "construction", "logistics", "freight"]):
                return 'Industrials'
            # Real Estate
            if any(k in search_text for k in ["리츠", "부동산", "reit", "real estate", "realty", "properties"]):
                return 'Real Estate'
            # Communication Services
            if any(k in search_text for k in ["텔레콤", "통신", "미디어", "엔터테인먼트", "스튜디오", "방송", "telecom", "media", "entertainment", "interactive"]):
                return 'Communication Services'
            # Information Technology
            if any(k in search_text for k in ["반도체", "전자", "하이닉스", "소프트웨어", "인터넷", "솔루션", "시스템", "클라우드", "semiconductor", "software", "technology", "technologies", "micro"]):
                return 'Information Technology'
            # Consumer Staples
            if any(k in search_text for k in ["음식료", "식품", "음료", "주류", "담배", "제당", "제과", "마트", "생활건강", "staples", "foods", "beverage"]):
                return 'Consumer Staples'
            # Consumer Discretionary
            if any(k in search_text for k in ["자동차", "모비스", "타이어", "백화점", "쇼핑", "패션", "의류", "호텔", "레저", "motors", "auto", "automotive", "retail"]):
                return 'Consumer Discretionary'

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
                c_col = 'Close' if 'Close' in df.columns else ('close' if 'close' in df.columns else None)
                if not c_col:
                    continue
                close = df[c_col]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                close = close.dropna()
                if len(close) < 20:
                    continue

                # R6-7 Fix: True 20-day and 60-day lookback indexing (-21 and -61 relative to -1)
                p20 = float(close.iloc[-21]) if len(close) >= 21 else float(close.iloc[0])
                p60 = float(close.iloc[-61]) if len(close) >= 61 else float(close.iloc[0])
                ret_20d = float(close.iloc[-1] / p20 - 1.0) if (len(close) >= 20 and p20 > 0) else 0.0
                ret_60d = float(close.iloc[-1] / p60 - 1.0) if (len(close) >= 60 and p60 > 0) else ret_20d

                # Composite Momentum Score
                mom_score = self.w_20d * ret_20d + self.w_60d * ret_60d
                raw_sec = eff_sector_map.get(sym, "General")
                norm_sec = self.normalize_sector(raw_sec, symbol=sym)
                records.append({'symbol': sym, 'mom_raw': mom_score, 'sector': norm_sec})
            except Exception as e:
                logger.debug(f"Sector mom calc failed for {sym}: {e}")
                continue

        if not records:
            return pd.DataFrame(columns=['symbol', 'sector_score'])

        res_df = pd.DataFrame(records)

        if len(res_df) > 1:
            # R9-7 Fix: Zero variance check in flat/halted markets to prevent arbitrary rank inflation
            if res_df['mom_raw'].std() < 1e-6:
                res_df['stock_rank'] = 0.50
            else:
                res_df['stock_rank'] = res_df['mom_raw'].rank(pct=True).clip(0.02, 0.98)

            valid_sec_df = res_df[res_df['sector'] != 'General'] if 'sector' in res_df.columns else pd.DataFrame()
            if not valid_sec_df.empty and valid_sec_df['sector'].nunique() > 1:
                # Sector mean momentum computed once per unique real sector (excludes 'General' composite skew)
                sec_mom = valid_sec_df.groupby('sector')['mom_raw'].mean()
                K_sec = len(sec_mom)
                if sec_mom.std() < 1e-6 or K_sec <= 1:
                    sec_rank_map = {s: 0.50 for s in sec_mom.index}
                else:
                    sec_ranks = ((sec_mom.rank(ascending=True) - 0.5) / K_sec).clip(0.05, 0.95)
                    sec_rank_map = sec_ranks.to_dict()
                sec_rank_map['General'] = 0.50
                res_df['sector_rank'] = res_df['sector'].map(sec_rank_map).fillna(0.5)

                # Intra-Sector Dispersion weighting: High dispersion -> favor individual stock rank
                sector_counts = res_df.groupby('sector')['mom_raw'].transform('count')
                sector_disp = res_df.groupby('sector')['mom_raw'].transform('std').fillna(0.0)
                # Single-stock sectors use 100% individual stock rank to prevent 0.50 dilution
                stock_weight = np.where(
                    sector_counts <= 1,
                    1.0,
                    (0.35 + sector_disp * 5.0).clip(0.20, 0.70)
                )
                sector_weight = 1.0 - stock_weight

                res_df['sector_score'] = sector_weight * res_df['sector_rank'] + stock_weight * res_df['stock_rank']

                # Sector Leadership Synergy Boost: Top sector (sector_rank >= 0.80) + Top stock momentum (stock_rank >= 0.70)
                leadership_mask = (res_df['sector_rank'] >= 0.80) & (res_df['stock_rank'] >= 0.70)
                if leadership_mask.any():
                    res_df.loc[leadership_mask, 'sector_score'] = (res_df.loc[leadership_mask, 'sector_score'] * 1.08).clip(0.0, 1.0)
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
            general_mask = res_df['sector'] == 'General'
            if general_mask.any():
                if 'stock_rank' in res_df.columns:
                    res_df.loc[general_mask, 'sector_score'] = (0.35 + res_df.loc[general_mask, 'stock_rank'] * 0.30).clip(0.1, 0.9)
                else:
                    res_df.loc[general_mask, 'sector_score'] = 0.50

        return res_df[['symbol', 'sector_score']]

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        try:
            return self.compute_sector_momentum_scores(
                prices_dict,
                sector_map=kwargs.get("sector_map"),
                macro_indicators=indicators_df,
                regime_label=kwargs.get("regime_label"),
            )
        except Exception as e:
            logger.warning(f"[SectorRotationEngine] compute_scores failed: {e}")
            return pd.DataFrame(columns=["symbol", "sector_score"])

    @staticmethod
    def compute_sector_breadth_velocity_thrust(
        sector_returns_df: pd.DataFrame,
        short_window: int = 5,
        long_window: int = 20
    ) -> Dict[str, float]:
        """
        Computes Sector Breadth Velocity Thrust (Acceleration):
        Thrust = Mom_5d - (5/20) * Mom_20d
        Identifies early-stage leading sectors experiencing massive capital acceleration.
        """
        if sector_returns_df is None or sector_returns_df.empty or len(sector_returns_df) < long_window:
            return {}

        thrust_scores = {}
        for col in sector_returns_df.columns:
            s = sector_returns_df[col].dropna()
            if len(s) >= long_window:
                p_now = float(s.iloc[-1])
                p_short = float(s.iloc[-short_window])
                p_long = float(s.iloc[-long_window])
                mom_short = (p_now / p_short - 1.0) if p_short > 0 else 0.0
                mom_long = (p_now / p_long - 1.0) if p_long > 0 else 0.0
                velocity = mom_short - (short_window / long_window) * mom_long
                thrust_scores[col] = float(velocity)
            else:
                thrust_scores[col] = 0.0

        return thrust_scores

