"""Korean Stock List Utility"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class KoreanStockList:
    """Thread-safe Korean stock ticker cache. Use get_tickers() to access."""

    def __init__(self):
        self._tickers: Dict[str, str] = {}
        self._tickers_rev: Dict[str, str] = {}

    def load(self) -> Dict[str, str]:
        """Load all KOSPI and KOSDAQ stocks from KRX using FinanceDataReader"""
        if self._tickers:
            return self._tickers

        try:
            import FinanceDataReader as fdr

            logger.info("Fetching KRX stock listing...")
            df = fdr.StockListing("KRX")
            if df is not None and not df.empty:
                for row in df.itertuples(index=False):
                    r_dict = row._asdict() if hasattr(row, '_asdict') else dict(zip(df.columns, row))
                    code_raw = str(r_dict.get("Code", "")).strip()
                    name = str(r_dict.get("Name", "")).strip()
                    market = str(r_dict.get("Market", "")).strip().upper()

                    if not code_raw or not name:
                        continue

                    code = code_raw.zfill(6) if (code_raw.isdigit() and len(code_raw) <= 6) else code_raw

                    if "KOSPI" in market:
                        symbol = f"{code}.KS"
                    elif "KOSDAQ" in market:
                        symbol = f"{code}.KQ"
                    else:
                        continue

                    self._tickers[name] = symbol
                    self._tickers_rev[symbol] = name

            logger.info(f"Successfully loaded {len(self._tickers)} Korean stocks.")
        except Exception as e:
            logger.error(f"Failed to load KRX stocks via FinanceDataReader: {e}")
            self._tickers.update(
                {
                    "삼성전자": "005930.KS",
                    "SK하이닉스": "000660.KS",
                    "현대차": "005380.KS",
                    "기아": "000270.KS",
                    "POSCO홀딩스": "005490.KS",
                    "NAVER": "035420.KS",
                    "네이버": "035420.KS",
                    "카카오": "035720.KS",
                    "셀트리온": "068270.KS",
                    "삼성바이오로직스": "207940.KS",
                    "LG에너지솔루션": "373220.KS",
                    "LG화학": "051910.KS",
                    "삼성SDI": "006400.KS",
                    "KB금융": "105560.KS",
                    "신한지주": "055550.KS",
                    "하나금융지주": "086790.KS",
                    "현대모비스": "012330.KS",
                    "LG전자": "066570.KS",
                    "에코프로비엠": "247540.KQ",
                    "에코프로": "086520.KQ",
                    "HLB": "028300.KQ",
                    "엔씨소프트": "036570.KS",
                    "대한항공": "003490.KS",
                    "SK텔레콤": "017670.KS",
                    "KT": "030200.KS",
                    "한국전력": "015760.KS",
                    "크래프톤": "259960.KS",
                    "SK이노베이션": "096770.KS",
                    "한화에어로스페이스": "012450.KS",
                    "삼성물산": "028260.KS",
                    "고려아연": "010130.KS",
                }
            )
            self._tickers_rev.update({v: k for k, v in self._tickers.items()})

        return self._tickers


_KOR_STOCK_LIST = KoreanStockList()


def get_tickers() -> Dict[str, str]:
    return _KOR_STOCK_LIST.load()


def get_tickers_rev() -> Dict[str, str]:
    if not _KOR_STOCK_LIST._tickers_rev:
        _KOR_STOCK_LIST.load()
    return _KOR_STOCK_LIST._tickers_rev
