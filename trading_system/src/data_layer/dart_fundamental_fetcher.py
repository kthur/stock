"""DART Fundamental Fetcher - Fetches Korean corporate financial statements via OpenDartReader / OpenDART API.

Fetches Book Value (자본총계), BPS, Net Income (당기순이익), Operating Income (영업이익),
Revenue (매출액), Total Debt (부채총계), and Cash Equivalents (현금및현금성자산) for KOSPI and KOSDAQ stocks.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from src.data_layer.dart_corp_mapper import DARTCorpMapper

logger = logging.getLogger(__name__)

# Report codes for OpenDART
REPRT_CODES = [
    ("11013", "1Q", 3, 31, "quarterly"),
    ("11012", "Half", 6, 30, "quarterly"),
    ("11014", "3Q", 9, 30, "quarterly"),
    ("11011", "Annual", 12, 31, "annual"),
]


def _clean_amount(val: Any) -> float:
    """Parse comma-separated amount string into float (in KRW)."""
    if val is None or pd.isna(val):
        return 0.0
    s = str(val).strip().replace(",", "")
    if s in ("", "-", "N/A", "nan", "None"):
        return 0.0
    try:
        f = float(s)
        return f if np.isfinite(f) else 0.0
    except (ValueError, TypeError):
        return 0.0


class DARTFundamentalFetcher:
    """Fetches and parses financial statements for Korean stocks (KOSPI/KOSDAQ) using OpenDartReader."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        corp_mapper: Optional[DARTCorpMapper] = None,
        dart_reader: Optional[Any] = None,
    ):
        self.api_key = api_key or os.environ.get("DART_API_KEY", "").strip()
        self.corp_mapper = corp_mapper or DARTCorpMapper(api_key=self.api_key)
        self._dart_reader = dart_reader
        self._initialized = False

    def _get_reader(self) -> Optional[Any]:
        """Lazy load OpenDartReader instance."""
        if self._dart_reader is not None:
            return self._dart_reader
        if not self.api_key:
            logger.debug("DART_API_KEY is not configured. OpenDartReader unavailable.")
            return None
        try:
            import OpenDartReader
            self._dart_reader = OpenDartReader(self.api_key)
            return self._dart_reader
        except ImportError:
            logger.warning("opendartreader package is not installed.")
            return None
        except Exception as e:
            logger.warning(f"Failed to initialize OpenDartReader: {e}")
            return None

    def fetch_fundamentals(
        self,
        symbol: str,
        years_back: int = 3,
        shares_outstanding: Optional[float] = None,
    ) -> Optional[pd.DataFrame]:
        """Fetch quarterly & annual fundamentals for a given KRX stock symbol.

        Returns DataFrame matching stock_fundamentals schema:
            date (index), date_available, period_type, revenue, operating_income,
            net_income, eps, shares_outstanding, book_value, bps, total_debt,
            cash_equivalents, dividend_per_share, ttm_revenue, ttm_operating_income,
            ttm_net_income, ttm_eps, operating_margin, net_profit_margin, eps_growth_1y
        """
        reader = self._get_reader()
        if reader is None:
            return None

        clean_sym = str(symbol).strip().split('.')[0].zfill(6) if str(symbol).strip().split('.')[0].isdigit() else str(symbol).strip()
        corp_code = self.corp_mapper.get_corp_code(clean_sym)
        lookup_target = corp_code if corp_code else clean_sym

        current_year = datetime.now().year
        rows: List[Dict[str, Any]] = []

        # Iterate over recent years from oldest to newest to build chronological series
        start_year = current_year - max(1, years_back)
        for year in range(start_year, current_year + 1):
            for reprt_code, reprt_name, m_end, d_end, p_type in REPRT_CODES:
                period_dt = datetime(year, m_end, d_end)
                if period_dt > datetime.now():
                    continue

                try:
                    df_fin = reader.finstate(lookup_target, year, reprt_code=reprt_code)
                    if df_fin is None or not isinstance(df_fin, pd.DataFrame) or df_fin.empty:
                        continue

                    parsed_row = self._parse_finstate(df_fin, period_dt, p_type, shares_outstanding)
                    if parsed_row:
                        rows.append(parsed_row)
                except Exception as e:
                    logger.debug(f"OpenDartReader finstate failed for {clean_sym} ({year} {reprt_name}): {e}")

        if not rows:
            return None

        df_res = pd.DataFrame(rows)
        # Deduplicate and sort by date
        df_res = df_res.drop_duplicates(subset=['date_align']).sort_values('date_align')
        df_res = df_res.set_index('date_align')

        # Fallback/refine shares outstanding if available
        if shares_outstanding and shares_outstanding > 0:
            df_res['shares_outstanding'] = float(shares_outstanding)
            df_res['bps'] = np.where(
                df_res['book_value'] > 0,
                df_res['book_value'] / shares_outstanding,
                0.0
            )

        # Compute TTM rolling metrics
        self._compute_ttm_metrics(df_res)
        return df_res

    def _parse_finstate(
        self,
        df_fin: pd.DataFrame,
        period_dt: datetime,
        p_type: str,
        shares_outstanding: Optional[float],
    ) -> Optional[Dict[str, Any]]:
        """Extract standardized accounting accounts from OpenDART finstate DataFrame."""
        if 'account_nm' not in df_fin.columns:
            return None

        # Prioritize CFS (Consolidated / 연결) over OFS (Separate / 개별)
        df_target = df_fin
        if 'fs_div' in df_fin.columns:
            cfs_df = df_fin[df_fin['fs_div'] == 'CFS']
            if not cfs_df.empty:
                df_target = cfs_df
            else:
                ofs_df = df_fin[df_fin['fs_div'] == 'OFS']
                if not ofs_df.empty:
                    df_target = ofs_df

        # Account extraction helper
        def _find_val(keywords: List[str]) -> float:
            for kw in keywords:
                matched = df_target[df_target['account_nm'].astype(str).str.contains(kw, case=False, regex=False)]
                if not matched.empty:
                    val = matched.iloc[0].get('thstrm_amount', 0.0)
                    amt = _clean_amount(val)
                    if amt != 0.0:
                        return amt
                    # Fallback to cumulative amount if thstrm is 0 for quarterly
                    add_val = matched.iloc[0].get('thstrm_add_amount', None)
                    if add_val is not None:
                        add_amt = _clean_amount(add_val)
                        if add_amt != 0.0:
                            return add_amt
            return 0.0

        book_val = _find_val([
            '자본총계', '자본총계(지배기업소유주지분)', '지배기업소유주지분',
            '자본총계(지배기업소유주지분등)', '지배기업소유주지분자본'
        ])
        net_inc = _find_val([
            '당기순이익', '당기순이익(손실)', '분기순이익', '반기순이익',
            '연결당기순이익', '지배기업소유주지분순이익', '지배기업의소유주지분순이익'
        ])
        op_inc = _find_val([
            '영업이익', '영업이익(손실)', '영업수익'
        ])
        rev = _find_val([
            '매출액', '수익(매출액)', '영업수익', '매출'
        ])
        tot_debt = _find_val([
            '부채총계', '총부채', '차입금'
        ])
        cash_eq = _find_val([
            '현금및현금성자산', '현금및현금성자산(기말)', '현금및예치금'
        ])

        # If essential metrics are all zero, treat as unusable report
        if book_val == 0.0 and net_inc == 0.0 and op_inc == 0.0 and rev == 0.0:
            return None

        scale_factor = 1.0 if p_type == 'quarterly' else 0.25

        # Statutory Filing Lag (KRX: 45 days for quarterly, 90 days for annual)
        lag_days = 90 if p_type == 'annual' else 45
        date_available = (period_dt + timedelta(days=lag_days)).strftime('%Y-%m-%d')

        sh_out = float(shares_outstanding or 0.0)
        bps_val = (book_val / sh_out) if (sh_out > 0 and book_val > 0) else 0.0

        return {
            'date_align': period_dt,
            'date_available': date_available,
            'period_type': p_type,
            'revenue': float(rev * scale_factor),
            'operating_income': float(op_inc * scale_factor),
            'net_income': float(net_inc * scale_factor),
            'eps': float(net_inc / sh_out) if (sh_out > 0) else 0.0,
            'shares_outstanding': sh_out,
            'dividend_per_share': 0.0,
            'book_value': float(book_val),
            'bps': float(bps_val),
            'total_debt': float(tot_debt),
            'cash_equivalents': float(cash_eq),
            'operating_cash_flow': 0.0,
        }

    def _compute_ttm_metrics(self, df: pd.DataFrame):
        """Compute rolling 4-quarter TTM and profit margin quality metrics."""
        is_quarterly = (df.get('period_type', '') == 'quarterly').all()
        if is_quarterly and len(df) >= 1:
            df['ttm_revenue'] = df['revenue'].rolling(4, min_periods=1).sum()
            df['ttm_operating_income'] = df['operating_income'].rolling(4, min_periods=1).sum()
            df['ttm_net_income'] = df['net_income'].rolling(4, min_periods=1).sum()
            df['ttm_eps'] = df['eps'].rolling(4, min_periods=1).sum()
        else:
            df['ttm_revenue'] = df['revenue'] * 4.0
            df['ttm_operating_income'] = df['operating_income'] * 4.0
            df['ttm_net_income'] = df['net_income'] * 4.0
            df['ttm_eps'] = df['eps'] * 4.0

        df['operating_margin'] = np.where(
            df['ttm_revenue'] > 0,
            np.clip(df['ttm_operating_income'] / np.maximum(df['ttm_revenue'], 1e-6), -10.0, 10.0),
            0.0
        )
        df['net_profit_margin'] = np.where(
            df['ttm_revenue'] > 0,
            np.clip(df['ttm_net_income'] / np.maximum(df['ttm_revenue'], 1e-6), -10.0, 10.0),
            0.0
        )
        if 'ttm_eps' in df.columns:
            df['eps_growth_1y'] = df['ttm_eps'].pct_change(4).replace([np.inf, -np.inf], np.nan).fillna(0.0)
