"""Korean Stock List Utility"""

import logging
import FinanceDataReader as fdr

logger = logging.getLogger(__name__)

# Global cache
KOR_TICKERS = {}
KOR_TICKERS_REV = {}

def load_korean_tickers():
    """Load all KOSPI and KOSDAQ stocks from KRX using FinanceDataReader"""
    global KOR_TICKERS, KOR_TICKERS_REV
    
    if KOR_TICKERS:
        return KOR_TICKERS
        
    try:
        logger.info("Fetching KRX stock listing...")
        df = fdr.StockListing('KRX')
        
        for _, row in df.iterrows():
            code = row['Code']
            name = row['Name']
            market = row['Market']
            
            # Map correctly to Yahoo Finance ticker symbols
            if 'KOSPI' in market:
                symbol = f"{code}.KS"
            elif 'KOSDAQ' in market:
                symbol = f"{code}.KQ"
            else:
                continue # Ignore KONEX etc.
                
            KOR_TICKERS[name] = symbol
            KOR_TICKERS_REV[symbol] = name
            
        logger.info(f"Successfully loaded {len(KOR_TICKERS)} Korean stocks.")
    except Exception as e:
        logger.error(f"Failed to load KRX stocks via FinanceDataReader: {e}")
        # Fallback to hardcoded large-cap list
        KOR_TICKERS.update({
            "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS",
            "기아": "000270.KS", "POSCO홀딩스": "005490.KS", "NAVER": "035420.KS",
            "네이버": "035420.KS", "카카오": "035720.KS", "셀트리온": "068270.KS",
            "삼성바이오로직스": "207940.KS", "LG에너지솔루션": "373220.KS",
            "LG화학": "051910.KS", "삼성SDI": "006400.KS", "KB금융": "105560.KS",
            "신한지주": "055550.KS", "하나금융지주": "086790.KS", "현대모비스": "012330.KS",
            "LG전자": "066570.KS", "에코프로비엠": "247540.KQ", "에코프로": "086520.KQ",
            "HLB": "028300.KQ", "엔씨소프트": "036570.KS", "대한항공": "003490.KS",
            "SK텔레콤": "017670.KS", "KT": "030200.KS", "한국전력": "015760.KS",
            "크래프톤": "259960.KS", "SK이노베이션": "096770.KS", 
            "한화에어로스페이스": "012450.KS", "삼성물산": "028260.KS",
            "고려아연": "010130.KS"
        })
        KOR_TICKERS_REV.update({v: k for k, v in KOR_TICKERS.items()})
        
    return KOR_TICKERS

# Auto-load on import
load_korean_tickers()
