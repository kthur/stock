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

─── Value Trap Protection (퀀트 가치 함정 방지) ───────────────────────────────

1. Earnings Quality Filter (이익의 질 필터):
   순이익에 일회성 이익(영업외수익, 자산매각 등)이 섞이면 ROE가 과대평가되어
   본업 경쟁력이 낮은 기업도 높은 RIM 점수를 받을 수 있다. 이를 방지하기 위해
   operating_income / net_income 비율로 이익의 질을 계산한다.
     - earnings_quality = clip(operating_income / net_income, 0, 1)
     - 지속가능 ROE = ROE × earnings_quality
     - 영업손실(-)인데 순이익(+)이면(일회성 이익으로 순이익 달성) rim_score를 NaN 처리
       (이익의 질 0 → RIM 부적합, 앙상블 가중치 자동 재정규화)

2. Extreme ROE Normalization (극단 ROE 정규화):
   일회성 염가매수차익, 자산매각 등으로 ROE가 비정상 급등할 때, 영업이익 기반
   지속가능 ROE로 대체하거나 절대 상한 ABSOLUTE_ROE_CAP으로 클리핑한다.
     - 조건: ROE > EXTREME_ROE_THRESHOLD(20%) 이고 EQ(이익의 질) < 0.4
       → roe_normalized = min(operating_income / book_value, ABSOLUTE_ROE_CAP)
     - 무조건 적용: roe_raw를 ABSOLUTE_ROE_CAP(25%)으로 상한 제한
   이를 통해 웅진형 '적정가 10,538원, 할인율 390%' 같은 이상치를 방지한다.

3. Holding Company Discount (지주사 SOTP 할인):
   지주사는 자회사 NAV 이중 카운팅(Double Counting)으로 장부 BPS가 부풀려진다.
   추가적으로 인수금융 레버리지(순부채)가 RIM 공식에 미반영된다. 이를 보정하기 위해:
     - BPS_adjusted = BPS - (net_debt / shares_outstanding)  # 순부채 차감
     - V0_adjusted  = BPS_adjusted + (V0_raw - BPS_raw) × (1 - HOLDING_CO_DISCOUNT)
       where HOLDING_CO_DISCOUNT = 0.40  # 40% 이중 카운팅 할인
   지주사 판별: 종목명 패턴('지주', '홀딩스', 'Holdings') 또는 GICS sector_code 기반.
"""
import logging
import re
from typing import Dict, Optional, Any
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── 이익의 질 필터 ─────────────────────────────────────────────────────────────
# 영업이익/순이익 비율이 이 값 미만이면 순이익의 상당 부분이 영업외/일회성 항목으로
# 판단하여 ROE를 감쇠한다. (0.5 = 순이익의 절반 이상이 영업 이익에서 발생해야 정상)
EARNINGS_QUALITY_MIN_RATIO = 0.5

# ── 극단 ROE 정규화 (Value Trap 방지) ──────────────────────────────────────────
# ROE가 이 값을 초과하면서 이익의 질이 낮으면 영업이익 기반 ROE로 대체
EXTREME_ROE_THRESHOLD = 0.20   # 20%: ROE > 20% & EQ < 0.4 → 영업이익 기반 정규화
# ROE 절대 상한: 어떤 기업도 이 값을 초과하는 ROE를 RIM에 사용할 수 없음
# (초과분은 비지속 가능한 일회성 이익으로 간주)
ABSOLUTE_ROE_CAP = 0.25        # 25%: 업종 불문 영구 ROE 상한
# EQ 임계치: ROE가 극단 임계 초과 시 이 값 미만이면 영업이익 기반 ROE로 강제 대체
EXTREME_EQ_THRESHOLD = 0.40    # 40%: 순이익의 60% 이상이 비영업 → 대체

# ── 지주사 SOTP 할인 ──────────────────────────────────────────────────────────
# 지주사 이중 카운팅(Double Counting) NAV 할인율
HOLDING_CO_DISCOUNT = 0.40     # 40%: 지주사 초과이익(BPS 초과분)에 적용
# 종목명 기반 지주사 패턴 (대소문자 무관)
_HOLDING_CO_NAME_RE = re.compile(
    r"(지주|홀딩스|holding|holdings|그룹|지배구조|HD\b)", re.IGNORECASE
)
# GICS/KRX 업종코드: 지주사로 분류되는 코드 목록
_HOLDING_CO_SECTOR_CODES = frozenset({
    "6020",   # KRX: 지주회사
    "CGLC",   # GICS: Capital Markets (일부 지주 혼재)
    "20202020",  # GICS: Diversified Financial Services (지주 포함)
})

# ── 우선주 심볼 판별 ──────────────────────────────────────────────────────────
#   - 6자리 코드 마지막 자리 5~9: 005935(삼성전자우), 000025(한진칼우) 등
#   - 6자리 + K/L 접미사: 00680K(미래에셋증권2우B), 33626L(두산퓨얼셀2우B) 등
_KRX_PREFERRED_RE = re.compile(r"^\d{5}[56789KLM]$")


def is_preferred_share(symbol: str) -> bool:
    """True if the symbol is a Korean preferred share (우선주)."""
    return bool(_KRX_PREFERRED_RE.match(str(symbol).strip().upper()))


def _is_holding_company(name: Optional[str], sector_code: Optional[str]) -> bool:
    """True if the stock is classified as a holding company (지주사).

    Criteria (OR logic):
    1. 종목명에 지주·홀딩스·Holdings 등 패턴 포함
    2. GICS/KRX 업종코드가 지주사 코드 목록에 해당
    """
    if name and _HOLDING_CO_NAME_RE.search(str(name)):
        return True
    if sector_code and str(sector_code).strip() in _HOLDING_CO_SECTOR_CODES:
        return True
    return False


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
    def __init__(
        self,
        default_required_return: float = 0.08,
        decay_rate: float = 0.10,
        retention_ratio: float = 0.6,
        config: Optional[Any] = None,
    ):
        """
        :param default_required_return: Baseline required rate of return (r_e), default 8.0%
        :param decay_rate: ROE persistence decay rate per year (0.10 = 10% decay toward r_e)
        :param retention_ratio: Fraction of net income retained (유보율), default 0.6 (60%)
        """
        self.default_required_return = default_required_return
        self.decay_rate = decay_rate
        self.retention_ratio = retention_ratio

    def derive_required_return(
        self,
        market: str = "KOSPI",
        us10y_yield: Optional[float] = None,
        vix_val: Optional[float] = None,
        credit_spread: Optional[float] = None,
        asset_beta: Optional[float] = None,
        is_small_cap: bool = False,
    ) -> float:
        """
        Derives dynamic countercyclical asset & country-specific required return:
          r_{e,i} = R_{f,mkt} + beta_i * ERP_dynamic + CRP_mkt + size_premium
        Expands ERP during high VIX / credit distress and scales by asset beta
        to prevent the Value Trap on high-beta speculative names.
        """
        mkt = str(market).strip().upper()
        # Country baseline 10Y risk-free rates
        rf_map = {
            'KOSPI': 0.033, 'KOSDAQ': 0.033, 'KRX': 0.033,
            'SP500': 0.040, 'NASDAQ': 0.040, 'RUSSELL2000': 0.040, 'US': 0.040,
            'CHINA': 0.022, 'CHINA_SSE': 0.022, 'CHINA_SZSE': 0.022, 'SSE': 0.022, 'SZSE': 0.022,
            'JAPAN': 0.012, 'JAPAN_TSE': 0.012, 'TSE': 0.012,
            'INDIA': 0.068, 'INDIA_NSE': 0.068, 'NSE': 0.068,
            'EUROPE': 0.024, 'EUROPE_STOXX': 0.024, 'STOXX': 0.024, 'DAX': 0.024, 'FTSE': 0.040,
            'VIETNAM': 0.030, 'VIETNAM_HOSE': 0.030, 'HOSE': 0.030,
            'TAIWAN': 0.016, 'TAIWAN_TWSE': 0.016, 'TWSE': 0.016,
            'AUSTRALIA': 0.042, 'AUSTRALIA_ASX': 0.042, 'ASX': 0.042,
            'BRAZIL': 0.115, 'BRAZIL_B3': 0.115, 'B3': 0.115,
            'HKEX': 0.038, 'HONGKONG': 0.038,
            'SINGAPORE': 0.028, 'SINGAPORE_SGX': 0.028, 'SGX': 0.028,
            'CANADA': 0.034, 'CANADA_TSX': 0.034, 'TSX': 0.034,
        }
        # Country Risk Premium (CRP)
        crp_map = {
            'KOSPI': 0.005, 'KOSDAQ': 0.005, 'KRX': 0.005,
            'SP500': 0.000, 'NASDAQ': 0.000, 'RUSSELL2000': 0.000, 'US': 0.000,
            'CHINA': 0.009, 'CHINA_SSE': 0.009, 'CHINA_SZSE': 0.009, 'SSE': 0.009, 'SZSE': 0.009,
            'JAPAN': 0.000, 'JAPAN_TSE': 0.000, 'TSE': 0.000,
            'INDIA': 0.020, 'INDIA_NSE': 0.020, 'NSE': 0.020,
            'EUROPE': 0.002, 'EUROPE_STOXX': 0.002, 'STOXX': 0.002, 'DAX': 0.000, 'FTSE': 0.003,
            'VIETNAM': 0.035, 'VIETNAM_HOSE': 0.035, 'HOSE': 0.035,
            'TAIWAN': 0.006, 'TAIWAN_TWSE': 0.006, 'TWSE': 0.006,
            'AUSTRALIA': 0.000, 'AUSTRALIA_ASX': 0.000, 'ASX': 0.000,
            'BRAZIL': 0.032, 'BRAZIL_B3': 0.032, 'B3': 0.032,
            'HKEX': 0.006, 'HONGKONG': 0.006,
            'SINGAPORE': 0.000, 'SINGAPORE_SGX': 0.000, 'SGX': 0.000,
            'CANADA': 0.000, 'CANADA_TSX': 0.000, 'TSX': 0.000,
        }

        mkt_rf = rf_map.get(mkt, 0.040)
        base_rf = (us10y_yield / 100.0) if (us10y_yield is not None and us10y_yield > 0 and mkt in ('SP500', 'NASDAQ', 'RUSSELL2000', 'US')) else mkt_rf
        crp = crp_map.get(mkt, 0.005)

        if mkt in ('SP500', 'NASDAQ', 'RUSSELL2000', 'US', 'JAPAN', 'JAPAN_TSE', 'TSE', 'SINGAPORE', 'AUSTRALIA', 'CANADA'):
            base_erp = 0.050
        elif mkt in ('INDIA', 'INDIA_NSE', 'NSE', 'VIETNAM', 'VIETNAM_HOSE', 'HOSE', 'BRAZIL', 'BRAZIL_B3', 'B3'):
            base_erp = 0.065
        else:
            base_erp = 0.055

        beta_eff = float(np.clip(asset_beta, 0.50, 2.0)) if (asset_beta is not None and np.isfinite(asset_beta)) else 1.0
        size_prem = 0.010 if is_small_cap else 0.0

        # Dynamic Countercyclical ERP expansion (VIX > 20 expands ERP by up to +4%)
        vix_expansion = 0.0
        if vix_val is not None and np.isfinite(vix_val) and vix_val > 20.0:
            vix_expansion = float(np.clip((vix_val - 20.0) * 0.0025, 0.0, 0.04))

        # High Yield Credit Spread adjustment (Spread > 4.0% expands ERP by up to +3%)
        spread_expansion = 0.0
        if credit_spread is not None and np.isfinite(credit_spread) and credit_spread > 4.0:
            spread_expansion = float(np.clip((credit_spread - 4.0) * 0.01, 0.0, 0.03))

        dynamic_erp = base_erp + vix_expansion + spread_expansion
        dynamic_re = np.clip(base_rf + beta_eff * dynamic_erp + crp + size_prem, 0.05, 0.25)
        return float(dynamic_re)

    def normalize_roe(
        self,
        roe_raw: float,
        earnings_quality: float,
        operating_income: Optional[float],
        book_value: Optional[float],
    ) -> tuple[float, bool]:
        """Normalize an extreme ROE to a sustainable level to prevent Value Trap distortions.

        Two-stage normalization applied in order:
          Stage 1 — Nonrecurring income replacement:
            If ROE > EXTREME_ROE_THRESHOLD (20%) AND earnings_quality < EXTREME_EQ_THRESHOLD (0.4),
            the raw ROE is replaced with the operating-income-based sustainable ROE:
              roe_op = operating_income / book_value
            This prevents inflated ROEs from one-off gains (e.g., bargain-purchase gains,
            asset disposals) from driving intrinsic values to unrealistic levels.
          Stage 2 — Absolute cap:
            roe_normalized = min(roe_after_stage1, ABSOLUTE_ROE_CAP=0.25)
            No company is allowed a perpetual ROE assumption above 25%.

        Returns:
            (roe_normalized, was_normalized: bool)
        """
        was_normalized = False
        roe = roe_raw

        # Stage 1: 비경상 이익 대체 (영업이익 기반 ROE)
        if (
            roe > EXTREME_ROE_THRESHOLD
            and earnings_quality < EXTREME_EQ_THRESHOLD
            and operating_income is not None
            and np.isfinite(operating_income)
            and book_value is not None
            and np.isfinite(book_value)
            and book_value > 0
        ):
            roe_op = operating_income / book_value
            # 영업이익 기반 ROE가 음수이거나 원래보다 높은 경우 보수적으로 처리
            roe_op = float(np.clip(roe_op, 0.0, EXTREME_ROE_THRESHOLD))
            if roe_op < roe:
                roe = roe_op
                was_normalized = True

        # Stage 2: 절대 상한 (25%)
        if roe > ABSOLUTE_ROE_CAP:
            roe = ABSOLUTE_ROE_CAP
            was_normalized = True

        return roe, was_normalized

    def apply_holding_company_discount(
        self,
        bps: float,
        v0_raw: float,
        net_debt_per_share: float,
    ) -> tuple[float, float]:
        """Apply SOTP discount for holding companies (지주사 이중 카운팅 할인).

        Adjustments:
          1. BPS_adjusted = max(BPS - net_debt_per_share, BPS * 0.3)
             → 순부채 차감 (단, BPS의 30% 미만으로는 내리지 않음)
          2. V0_adjusted  = BPS_adjusted + (V0_raw - BPS_raw) × (1 - HOLDING_CO_DISCOUNT)
             → 초과이익(BPS 초과분)에 40% 할인 적용

        Returns:
            (bps_adjusted, v0_adjusted)
        """
        net_debt = float(net_debt_per_share) if np.isfinite(net_debt_per_share) else 0.0

        # 순부채 차감 (BPS의 30% 하한 유지)
        bps_adjusted = max(bps - net_debt, bps * 0.30)

        # 초과이익 부분에 지주사 할인 적용
        excess_income_pv = v0_raw - bps  # BPS 초과분 (RIM 핵심 가치)
        if excess_income_pv > 0:
            v0_adjusted = bps_adjusted + excess_income_pv * (1.0 - HOLDING_CO_DISCOUNT)
        else:
            # 초과이익 없으면 BPS 조정분만 반영
            v0_adjusted = bps_adjusted + excess_income_pv

        return bps_adjusted, v0_adjusted

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

        Note: roe passed here should already be normalized via normalize_roe().
        """
        r_e = required_return if (required_return is not None and required_return > 0) else self.default_required_return

        if np.isnan(bps) or bps <= 0:
            return np.nan

        if np.isnan(roe):
            roe = r_e  # Neutral assumption: ROE = r_e => V_0 = BPS
        else:
            roe = max(-0.5, min(float(ABSOLUTE_ROE_CAP), float(roe)))

        # R7-6 Fix: Enforce minimum 2% ROE decay floor to prevent perpetuity bubble traps on temporarily high ROE firms
        eff_decay = max(0.02, float(self.decay_rate)) if self.decay_rate > 0 else 0.05
        pv_excess = 0.0
        current_bps = bps
        current_roe = roe
        for t in range(1, years + 1):
            if current_bps <= 0.0:
                excess_income = 0.0
                current_bps = 0.0
            else:
                net_income = current_bps * current_roe
                excess_income = current_bps * (current_roe - r_e)
                # BPS grows by retained positive net income (or decreases by net losses)
                retention = self.retention_ratio if net_income > 0 else 1.0
                current_bps += net_income * retention
            pv_excess += excess_income / ((1.0 + r_e) ** t)
        # Ohlson (1995) Terminal Residual Income Persistence Annuity beyond Horizon T
        omega = 1.0 - eff_decay
        denom_tv = (1.0 + r_e - omega)
        if denom_tv > 1e-4 and current_bps > 0:
            tv_excess = (current_bps * (current_roe - r_e) * omega) / denom_tv
            pv_excess += tv_excess / ((1.0 + r_e) ** years)

        # Intrinsic equity value cannot be negative due to corporate limited liability.
        return max(0.0, float(bps + pv_excess))

    def compute_rim_scores(
        self,
        features_df: pd.DataFrame,
        symbol_market_map: Optional[Dict[str, str]] = None,
        required_return: Optional[float] = None,
        us10y_yield: Optional[float] = None,
        vix_val: Optional[float] = None,
        credit_spread: Optional[float] = None,
    ) -> pd.DataFrame:
        """
        Computes RIM intrinsic values and percentile scores using finite-horizon decaying ROE model
        with 유보금 (retained earnings) accumulation and countercyclical dynamic ERP.

        Value Trap mitigations applied (in order):
          1. Earnings quality filter: op_income/net_income < 0.5 → ROE decay
          2. Extreme ROE normalization: ROE > 20% & EQ < 0.4 → operating-income-based ROE
          3. Absolute ROE cap: ROE capped at 25% unconditionally
          4. Holding company discount: 40% discount on excess earnings, net debt deducted from BPS

        Missing fundamental BPS yields NaN rim_score for dynamic ensemble weight renormalization.
        """
        if features_df is None or features_df.empty:
            logger.warning("Empty features_df provided to RIMValuationEngine.")
            return pd.DataFrame(columns=[
                'symbol', 'market', 'Close', 'bps', 'bps_adjusted',
                'roe_raw', 'roe', 'roe_normalized',
                'earnings_quality', 'holding_co_flag', 'net_debt_per_share',
                'rim_filter_reason',
                'intrinsic_value', 'discount_ratio', 'rim_score',
            ])

        df = features_df.copy()
        if 'symbol' not in df.columns:
            if df.index.name == 'symbol':
                df = df.reset_index()
            else:
                df['symbol'] = [f"SYM_{i}" for i in range(len(df))]

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
        if 'Close' in df.columns:
            df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        elif 'price' in df.columns:
            df['Close'] = pd.to_numeric(df['price'], errors='coerce')
        else:
            df['Close'] = pd.Series(np.nan, index=df.index, dtype=float)

        # Handle BPS: derive ONLY from genuine bps column or book_value / shares_outstanding
        # Absolutely NO synthetic BPS fabrication (e.g. eps / 0.08 or eps / roe)
        bps_series = pd.Series(np.nan, index=df.index, dtype=float)
        if 'bps' in df.columns:
            bps_col = pd.to_numeric(df['bps'], errors='coerce').replace([np.inf, -np.inf, 0.0], np.nan)
            bps_series = bps_col.copy()

        if 'book_value' in df.columns:
            bv = pd.to_numeric(df['book_value'], errors='coerce').replace([np.inf, -np.inf, 0.0], np.nan)
            shares = (
                pd.to_numeric(df['shares_outstanding'], errors='coerce').fillna(0.0)
                if 'shares_outstanding' in df.columns
                else pd.Series(0.0, index=df.index)
            )
            bv_per_share = np.where((shares > 0) & bv.notna() & (bv > 0), bv / np.maximum(shares, 1.0), np.nan)
            bps_series = bps_series.combine_first(pd.Series(bv_per_share, index=df.index))

        bps_series = bps_series.replace([np.inf, -np.inf, 0.0], np.nan)
        df['bps'] = np.where(bps_series > 0, bps_series, np.nan)

        # Handle ROE: store raw value first, then clip for safety in downstream ops
        if 'roe' in df.columns:
            df['roe'] = pd.to_numeric(df['roe'], errors='coerce')
        elif 'eps' in df.columns and 'bps' in df.columns:
            eps_s = pd.to_numeric(df['eps'], errors='coerce')
            bps_s = pd.to_numeric(df['bps'], errors='coerce')
            with np.errstate(divide='ignore', invalid='ignore'):
                df['roe'] = np.where((bps_s > 0) & eps_s.notna(), eps_s / bps_s, np.nan)
        else:
            df['roe'] = pd.Series(np.nan, index=df.index)

        df['roe'] = df['roe'].replace([np.inf, -np.inf], np.nan).fillna(self.default_required_return)
        # Store true raw ROE BEFORE any clipping — needed for normalize_roe() to detect extreme values
        df['roe_raw'] = df['roe'].copy()
        # Initial safety clip: prevents numerical overflow in downstream ops.
        # The absolute cap of ABSOLUTE_ROE_CAP is enforced later by normalize_roe().
        df['roe'] = df['roe'].clip(-0.5, 0.5)

        # ── Earnings Quality Filter (이익의 질 필터) ────────────────────────────
        # 순이익이 영업이익보다 크게 높으면(일회성 이익 포함) ROE를 감쇠하고,
        # 영업손실(-) & 순이익 양수(+): 전적으로 일회성/영업외 이익 → RIM 부적합
        df['earnings_quality'] = 1.0
        df['rim_filter_reason'] = ''
        has_op_inc = 'operating_income' in df.columns
        has_net_inc = 'net_income' in df.columns

        if has_op_inc or has_net_inc:
            op_inc = (
                pd.to_numeric(df['operating_income'], errors='coerce').replace([np.inf, -np.inf], np.nan)
                if has_op_inc
                else pd.Series(np.nan, index=df.index)
            )
            net_inc = (
                pd.to_numeric(df['net_income'], errors='coerce').replace([np.inf, -np.inf], np.nan)
                if has_net_inc
                else pd.Series(np.nan, index=df.index)
            )

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

            # 영업손실(-) 또는 순손실(-): 사업 본연의 수익성이 훼손된 기업 → RIM 점수 왜곡 방지를 위해 무효화
            op_loss = (op_inc < 0) | (net_inc < 0)
            # 영업손실(-) & 순이익 양수(+): 순이익이 전적으로 일회성/영업외 이익 → RIM 부적합
            suspicious = (op_inc <= 0) & (net_inc > 0)
            # 영업이익/순이익 비율이 임계 미만 → 이익의 질 낮음 → ROE 감쇠
            low_quality = pd.Series(eq_ratio, index=df.index) < EARNINGS_QUALITY_MIN_RATIO

            df.loc[op_loss, 'rim_filter_reason'] = 'OPERATING_LOSS'
            df.loc[suspicious, 'rim_filter_reason'] = 'LOW_EARNINGS_QUALITY'
            df.loc[low_quality & ~suspicious & ~op_loss, 'rim_filter_reason'] = 'QUALITY_ADJUSTED'
            # 이익의 질이 낮은 종목만 ROE 감쇠 (정상 기업 ROE 불변)
            df.loc[low_quality & ~op_loss, 'roe'] = df.loc[low_quality & ~op_loss, 'roe'] * eq_ratio[(low_quality & ~op_loss).to_numpy()]
            # 영업손실 또는 순손실 → 지속가능 이익 없음으로 간주
            df.loc[op_loss | suspicious, 'roe'] = 0.0

        # ── Extreme ROE Normalization (Value Trap 방지) ─────────────────────────
        # 조건: ROE > 20%(EXTREME_ROE_THRESHOLD) & EQ < 0.4(EXTREME_EQ_THRESHOLD)
        # → 영업이익 기반 ROE로 대체 + 절대 상한 25%(ABSOLUTE_ROE_CAP) 강제 적용
        df['roe_normalized'] = False  # 정규화 적용 여부 플래그
        has_bv = 'book_value' in df.columns

        def _apply_roe_normalization(row) -> tuple:
            # Use roe_raw (original, pre-EQ-filter value) so Stage 1 correctly detects
            # extreme ROEs that EQ filter may have already partially decayed.
            roe_raw_val = row.get('roe_raw', row.get('roe', self.default_required_return))
            eq = row.get('earnings_quality', 1.0)
            op_inc_val = row.get('operating_income', None) if has_op_inc else None
            bv_val = row.get('book_value', None) if has_bv else None

            roe_out, normalized = self.normalize_roe(
                roe_raw=float(roe_raw_val) if pd.notna(roe_raw_val) else row['roe'],
                earnings_quality=float(eq) if pd.notna(eq) else 1.0,
                operating_income=float(op_inc_val) if (op_inc_val is not None and pd.notna(op_inc_val)) else None,
                book_value=float(bv_val) if (bv_val is not None and pd.notna(bv_val)) else None,
            )
            # The normalized ROE replaces the current working roe (already EQ-decayed).
            # Take the minimum to be conservative: don't allow normalize_roe to *increase* roe.
            final_roe = min(roe_out, row['roe']) if normalized else row['roe']
            # However if Stage 2 (absolute cap) alone fired, still apply the cap
            if not normalized and row['roe'] > ABSOLUTE_ROE_CAP:
                final_roe = ABSOLUTE_ROE_CAP
                normalized = True
            return final_roe, normalized

        # Only apply to rows that are not already invalidated
        valid_for_norm = ~df['rim_filter_reason'].isin(['OPERATING_LOSS', 'LOW_EARNINGS_QUALITY'])
        if valid_for_norm.any():
            norm_results = df[valid_for_norm].apply(_apply_roe_normalization, axis=1)
            df.loc[valid_for_norm, 'roe'] = norm_results.apply(lambda x: x[0])
            norm_flags = norm_results.apply(lambda x: x[1])
            df.loc[valid_for_norm & norm_flags, 'roe_normalized'] = True
            df.loc[valid_for_norm & norm_flags & (df['rim_filter_reason'] == ''), 'rim_filter_reason'] = 'EXTREME_ROE_NORMALIZED'
            # QUALITY_ADJUSTED + normalized → upgrade label
            df.loc[valid_for_norm & norm_flags & (df['rim_filter_reason'] == 'QUALITY_ADJUSTED'), 'rim_filter_reason'] = 'QUALITY_ADJUSTED+ROE_NORMALIZED'

        n_normalized = int(df['roe_normalized'].sum())
        if n_normalized:
            logger.info(f"Extreme ROE normalization applied to {n_normalized} symbols (ROE capped/replaced)")

        # ── Preferred Share Filter (우선주 필터) ─────────────────────────────────
        pref_mask = df['symbol'].astype(str).apply(is_preferred_share)
        if pref_mask.any():
            df.loc[pref_mask, 'rim_filter_reason'] = 'PREFERRED_SHARE'

        # ── Holding Company Detection (지주사 판별) ────────────────────────────
        has_name = 'name' in df.columns
        has_sector = 'sector_code' in df.columns
        df['holding_co_flag'] = False

        if has_name or has_sector:
            df['holding_co_flag'] = df.apply(
                lambda r: _is_holding_company(
                    name=str(r['name']) if has_name and pd.notna(r.get('name')) else None,
                    sector_code=str(r['sector_code']) if has_sector and pd.notna(r.get('sector_code')) else None,
                ),
                axis=1,
            )
        n_holding = int(df['holding_co_flag'].sum())
        if n_holding:
            logger.info(f"Holding company discount will be applied to {n_holding} symbols")

        # ── Net Debt Per Share (순부채/주당) ─────────────────────────────────────
        df['net_debt_per_share'] = 0.0
        has_total_debt = 'total_debt' in df.columns
        has_cash = 'cash_equivalents' in df.columns
        has_shares = 'shares_outstanding' in df.columns

        if has_total_debt or has_cash:
            total_debt = pd.to_numeric(df['total_debt'], errors='coerce').fillna(0.0) if has_total_debt else pd.Series(0.0, index=df.index)
            cash = pd.to_numeric(df['cash_equivalents'], errors='coerce').fillna(0.0) if has_cash else pd.Series(0.0, index=df.index)
            net_debt = (total_debt - cash).clip(lower=0.0)  # 순현금 보유 시 0 처리 (BPS 감소 없음)

            if has_shares:
                shares = pd.to_numeric(df['shares_outstanding'], errors='coerce').replace([0.0, np.inf, -np.inf], np.nan)
                df['net_debt_per_share'] = (net_debt / shares).replace([np.inf, -np.inf], np.nan).fillna(0.0)
            else:
                df['net_debt_per_share'] = 0.0

        # ── Log filter statistics ─────────────────────────────────────────────
        n_op_loss = int(df['rim_filter_reason'].eq('OPERATING_LOSS').sum())
        n_suspicious = int(df['rim_filter_reason'].eq('LOW_EARNINGS_QUALITY').sum())
        n_adjusted = int(df['rim_filter_reason'].str.startswith('QUALITY_ADJUSTED').sum())
        n_preferred = int(df['rim_filter_reason'].eq('PREFERRED_SHARE').sum())
        if n_op_loss or n_suspicious or n_adjusted or n_preferred or n_normalized:
            logger.info(
                f"RIM filters: {n_op_loss} operating loss, {n_suspicious} low quality (NaN), "
                f"{n_adjusted} ROE-quality-adjusted, {n_normalized} extreme-ROE-normalized, "
                f"{n_preferred} preferred shares invalidated"
            )

        # ── Intrinsic Value Calculation ───────────────────────────────────────
        v0_list = []
        discount_list = []
        bps_adj_list = []

        for row in df.itertuples(index=False):
            r_dict = row._asdict() if hasattr(row, '_asdict') else dict(zip(df.columns, row))
            if r_dict.get('rim_filter_reason') == 'PREFERRED_SHARE':
                v0_list.append(np.nan)
                discount_list.append(np.nan)
                bps_adj_list.append(np.nan)
                continue

            mkt = r_dict.get('market', 'KOSPI')
            if us10y_yield is not None or vix_val is not None:
                r_e = self.derive_required_return(mkt, us10y_yield=us10y_yield, vix_val=vix_val, credit_spread=credit_spread)
            elif required_return is not None and required_return > 0:
                r_e = required_return
            else:
                r_e = self.default_required_return

            b_val = r_dict.get('bps')
            r_val = r_dict.get('roe')
            p_val = r_dict.get('Close')
            b = float(b_val) if (b_val is not None and pd.notna(b_val) and np.isfinite(b_val)) else np.nan
            r = float(r_val) if (r_val is not None and pd.notna(r_val) and np.isfinite(r_val)) else r_e
            p = float(p_val) if (p_val is not None and pd.notna(p_val) and np.isfinite(p_val)) else np.nan
            nd_ps = float(r_dict.get('net_debt_per_share', 0.0) or 0.0)

            if np.isnan(b) or b <= 0:
                v0 = np.nan
                b_adj = np.nan
            else:
                # Raw RIM intrinsic value (with normalized ROE already applied)
                v0_raw = self.calculate_intrinsic_value(b, r, required_return=r_e)

                # Holding company SOTP discount
                is_hc = bool(r_dict.get('holding_co_flag', False))
                if is_hc and pd.notna(v0_raw) and pd.notna(b) and b > 0:
                    b_adj, v0 = self.apply_holding_company_discount(b, v0_raw, nd_ps)
                else:
                    b_adj = b
                    v0 = v0_raw

            v0_list.append(v0)
            bps_adj_list.append(b_adj)

            if pd.notna(p) and p > 0 and pd.notna(v0) and v0 > 0:
                disc = (v0 - p) / p
                # Clip extreme discount ratios to prevent rank pollution
                # (> +500% or < -90% are artifacts of data issues, not real value)
                disc = float(np.clip(disc, -0.90, 5.00))
            else:
                disc = np.nan
            discount_list.append(disc)

        df['intrinsic_value'] = v0_list
        df['discount_ratio'] = discount_list
        df['bps_adjusted'] = bps_adj_list

        # ── Percentile Scoring ────────────────────────────────────────────────
        # Transform Discount Ratio to Percentile Score [0.0, 1.0] per Market with boundary clipping
        invalid_mask = df['rim_filter_reason'].isin(['LOW_EARNINGS_QUALITY', 'PREFERRED_SHARE', 'OPERATING_LOSS'])
        if 'bps' in df.columns:
            bps_numeric = pd.to_numeric(df['bps'], errors='coerce')
            invalid_mask = invalid_mask | bps_numeric.isna() | (bps_numeric <= 0)
        else:
            invalid_mask = pd.Series(True, index=df.index)

        # Distressed companies or missing BPS have NaN discount ratio so they do not pollute percentile ranking
        df.loc[invalid_mask, 'discount_ratio'] = np.nan
        df.loc[invalid_mask, 'intrinsic_value'] = np.nan

        # Rank valid stocks per market
        df['rim_score'] = df.groupby('market')['discount_ratio'].rank(pct=True, ascending=True).clip(0.02, 0.98)

        # Margin of safety acceleration for high-quality value stocks (Discount >= 30% and ROE >= required_return)
        mos_mask = (df['discount_ratio'] >= 0.30) & (df['roe'] >= 0.08) & (~invalid_mask)
        if mos_mask.any():
            df.loc[mos_mask, 'rim_score'] = (df.loc[mos_mask, 'rim_score'] * 1.05).clip(0.0, 1.0)

        # 영업손실, 순손실, 일회성 이익 의존, 우선주 및 자본잠식 종목은 RIM 점수 무효화 (NaN 유지)
        # → 앙상블에서 자동 제외되고 가중치가 재정규화된다.
        if invalid_mask.any():
            df.loc[invalid_mask, ['rim_score', 'discount_ratio', 'intrinsic_value']] = np.nan
            logger.info(f"RIM scores invalidated for {int(invalid_mask.sum())} symbols (distress, low quality or preferred share)")

        out_cols = [
            'symbol', 'market', 'Close', 'bps', 'bps_adjusted',
            'roe_raw', 'roe', 'roe_normalized',
            'earnings_quality', 'holding_co_flag', 'net_debt_per_share',
            'rim_filter_reason',
            'intrinsic_value', 'discount_ratio', 'rim_score',
        ]
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
            if features_df is None or (isinstance(features_df, pd.DataFrame) and features_df.empty):
                if isinstance(prices_dict, pd.DataFrame):
                    features_df = prices_dict.copy()
                elif fundamentals_dict and isinstance(fundamentals_dict, dict):
                    rows = []
                    for sym, f_data in fundamentals_dict.items():
                        r = dict(f_data) if isinstance(f_data, dict) else {}
                        r["symbol"] = sym
                        if prices_dict and isinstance(prices_dict, dict) and sym in prices_dict:
                            p_df = prices_dict[sym]
                            if isinstance(p_df, pd.DataFrame) and not p_df.empty:
                                c_col = "Close" if "Close" in p_df.columns else ("close" if "close" in p_df.columns else None)
                                if c_col:
                                    r["Close"] = float(p_df[c_col].dropna().iloc[-1])
                        rows.append(r)
                    if rows:
                        features_df = pd.DataFrame(rows)
                elif prices_dict and isinstance(prices_dict, dict):
                    rows = []
                    for sym, p_df in prices_dict.items():
                        if isinstance(p_df, pd.DataFrame) and not p_df.empty:
                            c_col = "Close" if "Close" in p_df.columns else ("close" if "close" in p_df.columns else None)
                            if c_col:
                                rows.append({"symbol": sym, "Close": float(p_df[c_col].dropna().iloc[-1])})
                    if rows:
                        features_df = pd.DataFrame(rows)
            indicators_df = kwargs.get('indicators_df')
            us10y = kwargs.get('us10y_yield')
            vix = kwargs.get('vix_val')
            if us10y is None and isinstance(indicators_df, pd.DataFrame) and 'us10y' in indicators_df.columns:
                try:
                    us10y = float(indicators_df['us10y'].iloc[-1])
                except Exception:
                    pass
            if vix is None and isinstance(indicators_df, pd.DataFrame) and 'vix' in indicators_df.columns:
                try:
                    vix = float(indicators_df['vix'].iloc[-1])
                except Exception:
                    pass
            return self.compute_rim_scores(features_df, us10y_yield=us10y, vix_val=vix)
        except Exception as e:
            logger.warning(f"[RIMValuationEngine] compute_scores failed: {e}")
            return pd.DataFrame(columns=["symbol", "rim_score"])
