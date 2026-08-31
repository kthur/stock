import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class PortfolioAllocator:
    """
    3-Layer 하향식 포트폴리오 배분 엔진 (Top-down Market Budget → Regime Overlay → Kelly/HRP)

    Layer 1 — 시장별 기본 예산 (Market Budget):
        변동성 역비례 × 유동성(시장규모) × 거래비용 조정으로 시장별 최대 투자 비중 확정
        (RUSSELL2000 고변동·소형주 → 보수적 예산, SP500 저위험·고유동성 → 높은 예산)
    Layer 2 — 레짐/디커플링 조정 (Regime Overlay):
        YIELD_INVERSION / INFLATION_SHOCK / 디커플링 발생 시 시장별 예산 동적 조정
    Layer 3 — 종목별 Kelly/HRP 미세 배분:
        시장 예산 범위 내에서 Kelly Criterion 또는 HRP 알고리즘으로 종목별 최종 배분
    """

    # Layer 1: 시장별 기본 속성 (변동성·유동성·거래비용 기반 예산 비율)
    # 기준: 글로벌 시장 시가총액 + 일평균거래량 비중 + 비용 조정
    MARKET_BASE_BUDGETS = {
        'SP500':         {'vol_proxy': 0.14, 'liquidity': 0.80, 'cost': 0.006},   # 저변동·고유동·저비용
        'NASDAQ':        {'vol_proxy': 0.18, 'liquidity': 0.70, 'cost': 0.0065},  # 중변동·고유동·저비용
        'RUSSELL2000':   {'vol_proxy': 0.24, 'liquidity': 0.45, 'cost': 0.008},   # 중고변동·중유동·중비용
        'KOSPI':         {'vol_proxy': 0.18, 'liquidity': 0.60, 'cost': 0.0085},  # 중변동·중유동·중비용
        'KOSDAQ':        {'vol_proxy': 0.26, 'liquidity': 0.35, 'cost': 0.010},   # 고변동·저유동·고비용
        'JAPAN_TSE':     {'vol_proxy': 0.16, 'liquidity': 0.70, 'cost': 0.007},   # 일본 TSE 선진국 대형주
        'JAPAN':         {'vol_proxy': 0.16, 'liquidity': 0.70, 'cost': 0.007},
        'EUROPE_STOXX':  {'vol_proxy': 0.16, 'liquidity': 0.65, 'cost': 0.007},   # 유럽 유로스톡스
        'EUROPE':        {'vol_proxy': 0.16, 'liquidity': 0.65, 'cost': 0.007},
        'TAIWAN_TWSE':   {'vol_proxy': 0.19, 'liquidity': 0.55, 'cost': 0.009},   # 대만 IT 테크 중심
        'TAIWAN':        {'vol_proxy': 0.19, 'liquidity': 0.55, 'cost': 0.009},
        'CHINA_SSE':     {'vol_proxy': 0.20, 'liquidity': 0.65, 'cost': 0.008},   # 중국 본토
        'CHINA_SZSE':    {'vol_proxy': 0.22, 'liquidity': 0.60, 'cost': 0.0085},
        'CHINA':         {'vol_proxy': 0.20, 'liquidity': 0.65, 'cost': 0.008},
        'INDIA_NSE':     {'vol_proxy': 0.18, 'liquidity': 0.50, 'cost': 0.008},   # 인도 Nifty
        'INDIA':         {'vol_proxy': 0.18, 'liquidity': 0.50, 'cost': 0.008},
        'SINGAPORE_SGX': {'vol_proxy': 0.14, 'liquidity': 0.45, 'cost': 0.006},   # 싱가포르 SGX
        'SINGAPORE':     {'vol_proxy': 0.14, 'liquidity': 0.45, 'cost': 0.006},
        'AUSTRALIA_ASX': {'vol_proxy': 0.16, 'liquidity': 0.50, 'cost': 0.007},   # 호주 ASX 원자재/금융
        'AUSTRALIA':     {'vol_proxy': 0.16, 'liquidity': 0.50, 'cost': 0.007},
        'CANADA_TSX':    {'vol_proxy': 0.15, 'liquidity': 0.55, 'cost': 0.0065},  # 캐나다 TSX
        'CANADA':        {'vol_proxy': 0.15, 'liquidity': 0.55, 'cost': 0.0065},
        'HKEX':          {'vol_proxy': 0.22, 'liquidity': 0.60, 'cost': 0.008},   # 홍콩 HKEX
        'BRAZIL_B3':     {'vol_proxy': 0.26, 'liquidity': 0.35, 'cost': 0.012},   # 브라질 B3 원자재/금융
        'BRAZIL':        {'vol_proxy': 0.26, 'liquidity': 0.35, 'cost': 0.012},
        'VIETNAM_HOSE':  {'vol_proxy': 0.25, 'liquidity': 0.30, 'cost': 0.014},   # 베트남 HOSE 신흥국
        'VIETNAM':       {'vol_proxy': 0.25, 'liquidity': 0.30, 'cost': 0.014},
    }

    def __init__(self,
                 max_single_position: float = 0.15,
                 min_single_position: float = 0.02,
                 max_total_allocation: float = 0.85,
                 max_sector_exposure: float = 0.30,
                 target_horizon: int = 20,
                 use_kelly: bool = True,
                 kelly_fraction: float = 0.5):
        s_single = float(max_single_position) if (max_single_position is not None and np.isfinite(max_single_position)) else 0.15
        s_single = s_single / 100.0 if s_single > 1.0 else s_single
        self.max_single_position = max(0.0, min(1.0, s_single))

        s_min_single = float(min_single_position) if (min_single_position is not None and np.isfinite(min_single_position)) else 0.02
        s_min_single = s_min_single / 100.0 if s_min_single > 1.0 else s_min_single
        self.min_single_position = max(0.0, min(1.0, s_min_single))

        s_tot = float(max_total_allocation) if (max_total_allocation is not None and np.isfinite(max_total_allocation)) else 0.85
        s_tot = s_tot / 100.0 if s_tot > 1.0 else s_tot
        self.max_total_allocation = max(0.0, min(1.0, s_tot))

        s_sec = float(max_sector_exposure) if (max_sector_exposure is not None and np.isfinite(max_sector_exposure)) else 0.30
        s_sec = s_sec / 100.0 if s_sec > 1.0 else s_sec
        self.max_sector_exposure = max(0.0, min(1.0, s_sec))

        self.target_horizon = max(1, int(target_horizon)) if target_horizon is not None else 20
        self.use_kelly = bool(use_kelly)
        s_kelly = float(kelly_fraction) if (kelly_fraction is not None and np.isfinite(kelly_fraction)) else 0.5
        self.kelly_fraction = max(0.05, min(2.0, s_kelly))

    def compute_market_budgets(self,
                               regime: Optional[Any] = None,
                               decoupling_info: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        Layer 1 + 2: 시장별 포트폴리오 예산 비율을 계산합니다.

        기본 산식:
            raw_budget = (1 / vol_proxy) * liquidity * (1 - cost)
        정규화 후 합산 = 1.0

        레짐/디커플링 Overlay(Layer 2):
            - YIELD_INVERSION: 한국 소형주 예산 추가 축소 (경기침체 선행)
            - INFLATION_SHOCK: 중소형주 (RUSSELL2000, KOSDAQ) 예산 축소
            - DECOUPLING_US_BULL_KR_BEAR: US 시장 예산 확대, KR 시장 예산 축소
            - DECOUPLING_KR_BULL_US_BEAR: KR 시장 예산 확대, US 시장 예산 축소
        """
        # Layer 1: 기본 예산 계산
        raw = {}
        for mkt, props in self.MARKET_BASE_BUDGETS.items():
            raw[mkt] = (1.0 / props['vol_proxy']) * props['liquidity'] * (1.0 - props['cost'])

        # Layer 2: 레짐 및 디커플링 Overlay
        regime_str = str(regime).upper() if regime is not None else ""

        if "YIELD_INVERSION" in regime_str:
            # 장단기 금리 역전 → 소형주 예산 축소
            raw['KOSDAQ'] *= 0.60
            raw['RUSSELL2000'] *= 0.70
            logger.info("[Market Budget] YIELD_INVERSION: Small-cap budget reduced.")

        if "INFLATION_SHOCK" in regime_str:
            # 인플레이션 충격 → 중소형주 예산 축소
            raw['RUSSELL2000'] *= 0.60
            raw['KOSDAQ'] *= 0.75
            logger.info("[Market Budget] INFLATION_SHOCK: Small-cap budget reduced.")

        if "LIQUIDITY_SQUEEZE" in regime_str or "BEAR" in regime_str:
            # 유동성 위기·약세장 → 고변동 시장 축소, SP500/NASDAQ 방어 집중
            raw['KOSDAQ'] *= 0.50
            raw['RUSSELL2000'] *= 0.60
            raw['KOSPI']  *= 0.75

        if decoupling_info:
            status = decoupling_info.get('decoupling_status', 'COUPLED')
            corr = decoupling_info.get('correlation_20d', 1.0)
            # 상관관계가 낮을수록 디커플링 조정 강도 증가 (최대 ×1.5배 조정)
            decoupling_strength = max(0.0, 1.0 - max(0.0, corr)) * 0.5

            if status == 'DECOUPLING_US_BULL_KR_BEAR':
                raw['SP500']  *= (1.0 + decoupling_strength)
                raw['NASDAQ'] *= (1.0 + decoupling_strength)
                raw['KOSPI']  *= (1.0 - decoupling_strength)
                raw['KOSDAQ'] *= (1.0 - decoupling_strength)
                logger.info(f"[Market Budget] DECOUPLING_US_BULL_KR_BEAR: US boosted, KR reduced (strength={decoupling_strength:.2f})")
            elif status == 'DECOUPLING_KR_BULL_US_BEAR':
                raw['SP500']  *= (1.0 - decoupling_strength)
                raw['NASDAQ'] *= (1.0 - decoupling_strength)
                raw['KOSPI']  *= (1.0 + decoupling_strength)
                raw['KOSDAQ'] *= (1.0 + decoupling_strength * 0.7)
                logger.info(f"[Market Budget] DECOUPLING_KR_BULL_US_BEAR: KR boosted, US reduced (strength={decoupling_strength:.2f})")

        # 정규화: 합산 = 1.0
        total = float(sum(raw.values()))
        budgets = {k: v / total for k, v in raw.items()} if (total > 1e-12 and np.isfinite(total)) else \
                  {k: 1.0 / max(len(raw), 1) for k in raw}

        logger.info(f"[Market Budget] Layer1+2 Final Budgets: { {k: f'{v:.1%}' for k, v in budgets.items()} }")
        return budgets

    @staticmethod
    def calculate_conviction_alpha_weights(
        expected_returns: np.ndarray,
        volatilities: np.ndarray,
        gamma: float = 1.5,
        max_single_cap: float = 0.20
    ) -> np.ndarray:
        """
        Precision-Weighted Conviction Alpha Sizing (Information Ratio Maximizer):
        w_i = (alpha_i)^gamma / (sigma_i^2)
        Tilts aggressive capital toward top high-conviction ideas while penalizing volatility.
        Prevents risk parity from flattening out outsized alpha opportunities.
        """
        rets = np.maximum(0.0, np.asarray(expected_returns, dtype=float))
        vols = np.maximum(0.005, np.asarray(volatilities, dtype=float))

        raw_weights = (rets ** gamma) / (vols ** 2)
        tot = np.sum(raw_weights)
        if tot <= 0:
            n = len(rets)
            return np.full(n, 1.0 / max(n, 1))

        w = raw_weights / tot
        w = np.clip(w, 0.0, max_single_cap)
        s = np.sum(w)
        return w / s if s > 0 else np.full(len(w), 1.0 / len(w))

    @staticmethod
    def compute_dynamic_capital_flight_budgets(
        us_momentum_60d: float,
        kr_momentum_60d: float,
        base_budgets: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Inter-Market Dynamic Capital Flight Engine:
        Shifts capital up to 85% into the strongly outperforming market (US vs KR)
        based on 60-day relative momentum spread (M_US - M_KR).
        """
        spread = float(us_momentum_60d - kr_momentum_60d)
        us_share = float(np.clip(0.55 + 0.30 * np.tanh(spread / 0.10), 0.15, 0.85))
        kr_share = 1.0 - us_share

        return {
            'SP500': round(us_share * 0.55, 4),
            'NASDAQ': round(us_share * 0.40, 4),
            'RUSSELL2000': round(us_share * 0.05, 4),
            'KOSPI': round(kr_share * 0.70, 4),
            'KOSDAQ': round(kr_share * 0.30, 4),
        }

    def allocate(self,
                 predictions_df: pd.DataFrame,
                 prices_dict: Dict[str, pd.DataFrame],
                 total_portfolio_value: float = 10000000.0,
                 use_kelly: Optional[bool] = None,
                 kelly_fraction: Optional[float] = None,
                 use_hrp: bool = False,
                 sector_map: Optional[Dict[str, str]] = None,
                 regime: Optional[Any] = None,
                 market_col: Optional[str] = 'market',
                 decoupling_info: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        3-Layer 하향식 포트폴리오 배분:
          Layer 1+2: compute_market_budgets()로 시장별 예산 비율 확정
          Layer 3: 시장 예산 내에서 Kelly/HRP로 종목별 최종 배분

        Args:
            predictions_df: DataFrame with columns ['symbol', market_col, target_horizon].
            prices_dict: Dict of symbol -> OHLCV DataFrame.
            total_portfolio_value: Total money available to invest.
            use_kelly: Override class setting for Kelly sizing.
            kelly_fraction: Override class setting for Kelly fraction.
            use_hrp: If True, computes weights using Hierarchical Risk Parity algorithm.
            sector_map: Mapping of symbol -> sector name.
            regime: 2D or 1D market regime string (BULL, SIDEWAYS, BEAR, YIELD_INVERSION, etc.).
            market_col: Column name for market identifier in predictions_df ('market').
            decoupling_info: Dict from predict_dual_market_regime() with decoupling_status & correlation_20d.

        Returns:
            DataFrame with columns ['symbol', 'market', 'predicted_return', 'volatility',
                                    'raw_score', 'weight', 'market_budget', 'allocation_amount']
        """
        if predictions_df.empty or not prices_dict or self.max_total_allocation <= 0.0 or self.max_single_position <= 0.0:
            logger.warning("Empty predictions, prices_dict, or zero allocation limit. Allocation skipped.")
            return pd.DataFrame()

        if use_kelly is None:
            use_kelly = self.use_kelly

        # Resolve Regime-Adaptive Kelly Fraction & Macro Adjustment
        if kelly_fraction is None:
            regime_str = str(regime).upper() if regime is not None else ""
            if "YIELD_INVERSION" in regime_str or "LIQUIDITY_SQUEEZE" in regime_str:
                kelly_fraction = 0.10  # 장단기 금리 역전 / 유동성 위기 시 극보수적 포지션 (10%)
                logger.info(f"[RISK ADAPTIVE SIZING] Macro Crisis Regime ({regime_str}) -> Reduced Kelly Fraction to {kelly_fraction}")
            elif "INFLATION_SHOCK" in regime_str or "BEAR" in regime_str or regime == 0:
                kelly_fraction = 0.15  # 인플레이션 충격 / 약세장 시 보수적 포지션 (15%)
                logger.info(f"[RISK ADAPTIVE SIZING] Defensive Regime ({regime_str}) -> Reduced Kelly Fraction to {kelly_fraction}")
            elif "BULL" in regime_str or regime == 2:
                kelly_fraction = 0.40  # 강세장 시 적극적 포지션 (40%)
            else:
                kelly_fraction = self.kelly_fraction  # 기본 (25%)

        # Target horizon check
        horizon_col: Any = self.target_horizon
        if horizon_col not in predictions_df.columns:
            numeric_cols = [c for c in predictions_df.columns if isinstance(c, (int, float))]
            if not numeric_cols:
                logger.error("No numeric prediction horizons found in DataFrame.")
                return pd.DataFrame()
            horizon_col = min(numeric_cols, key=lambda x: abs(x - self.target_horizon))
            logger.warning(f"Horizon {self.target_horizon}d not found. Falling back to {horizon_col}d.")

        sym_col = next((c for c in predictions_df.columns if str(c).lower() in ('symbol', 'ticker')), 'symbol')
        records = []
        for row in predictions_df.itertuples(index=False):
            r_dict = dict(zip(predictions_df.columns, row))
            sym = r_dict.get(sym_col)
            if not sym:
                continue
            pred_ret = r_dict.get(horizon_col, 0.0)

            # Skip negative expected returns
            if pred_ret <= 0 or pd.isna(pred_ret):
                continue

            df_price = prices_dict.get(sym)
            if df_price is None or len(df_price) < 21:
                continue

            close_col = next((c for c in df_price.columns if str(c).lower() in ('close', 'adj close', 'adjclose')), None)
            if not close_col:
                continue

            close = df_price[close_col]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]

            close_s = pd.to_numeric(close, errors='coerce').dropna()
            if len(close_s) < 21:
                continue

            daily_returns = close_s.pct_change(fill_method=None).dropna()
            vol = float(daily_returns.tail(20).std())
            vol = max(vol, 1e-4) if np.isfinite(vol) else 0.02

            # Liquidity-proportional slippage estimation based on recent 20d volume/value
            vol_col_name = next((c for c in df_price.columns if str(c).lower() == 'volume'), None)
            volume_series = df_price[vol_col_name] if vol_col_name else None
            if isinstance(volume_series, pd.DataFrame):
                volume_series = volume_series.iloc[:, 0]

            if volume_series is not None and len(volume_series) >= 20:
                avg_vol = float(volume_series.tail(20).mean())
                last_price = float(close.iloc[-1])
                daily_val = avg_vol * last_price
                # Higher slippage for low daily value (< 5B KRW or $1M)
                if daily_val < 500_000_000:
                    cost = 0.0085  # 0.85% total cost
                elif daily_val < 5_000_000_000:
                    cost = 0.0043  # 0.43% total cost
                else:
                    cost = 0.0026  # 0.26% total cost
            else:
                cost = 0.005

            # Avoid double-deducting friction costs if input is already net expected return
            is_net = (
                'ensemble_expected_return' in predictions_df.columns
                or getattr(self, '_is_already_net', False)
                or 20 in predictions_df.columns
                or '20' in predictions_df.columns
            )
            if is_net:
                net_pred_ret = pred_ret
            else:
                eff_cost = cost if pred_ret <= 1.0 else (cost * 100.0)
                net_pred_ret = pred_ret - eff_cost
            if net_pred_ret <= 0:
                continue

            if pd.isna(vol) or vol <= 0:
                vol = 0.05

            records.append({
                'symbol': sym,
                'predicted_return': float(pred_ret),
                'net_return': float(max(0.0, net_pred_ret)),
                'volatility': float(vol)
            })

        if not records:
            logger.warning("No symbols with positive predicted returns and sufficient price data.")
            return pd.DataFrame()

        df_candidates = pd.DataFrame(records)

        # ── Layer 1 + 2: Market Budget 계산 ──────────────────────────────────
        market_budgets = self.compute_market_budgets(regime=regime, decoupling_info=decoupling_info)

        # 종목별 시장 레이블 매핑 (predictions_df에 market 컬럼이 있을 경우 활용)
        if market_col and market_col in predictions_df.columns:
            sym_to_market = predictions_df.set_index('symbol')[market_col].to_dict()
            df_candidates['market'] = df_candidates['symbol'].map(sym_to_market).fillna('KOSPI')
        else:
            df_candidates['market'] = 'KOSPI'  # 기본값

        present_markets = set(df_candidates['market'].str.upper())
        raw_present = {m: market_budgets.get(m, 0.25) for m in present_markets}
        tot_present = sum(raw_present.values())
        if tot_present > 0:
            norm_market_budgets = {m: b / tot_present for m, b in raw_present.items()}
        else:
            norm_market_budgets = market_budgets

        df_candidates['market_budget'] = df_candidates['market'].map(
            lambda m: norm_market_budgets.get(m.upper(), 1.0 / max(len(present_markets), 1))
        )

        # HRP / HERC Allocation Path
        # NOTE: HRP/HERC weights are a risk-parity allocation tool, NOT a signal score.
        # raw_score must stay the expected-return based ranking metric so that
        # Top-N selection is driven by the ensemble signal; HRP only sizes positions.
        if use_hrp or locals().get('use_herc', False):
            from src.analysis.portfolio_optimizer import calculate_hrp_weights, calculate_herc_weights
            symbols = df_candidates['symbol'].tolist()
            try:
                from src.risk.fx_adjusted_covariance import FXAdjustedCovarianceEngine
                cand_prices = {s: prices_dict[s] for s in symbols if s in prices_dict}
                mkt_map = dict(zip(df_candidates['symbol'], df_candidates['market']))
                cov_df, ret_df = FXAdjustedCovarianceEngine.compute_fx_adjusted_covariance(
                    prices_dict=cand_prices,
                    market_map=mkt_map,
                    lookback_days=60
                )
                if not cov_df.empty and cov_df.shape[0] == len(symbols):
                    cov_mat = cov_df.values
                else:
                    raise ValueError("Incomplete covariance matrix from FX engine")
            except Exception:
                returns_matrix = []
                for s in symbols:
                    df_p = prices_dict[s]
                    c = df_p['Close'].iloc[:, 0] if isinstance(df_p['Close'], pd.DataFrame) else df_p['Close']
                    r = c.pct_change(fill_method=None).tail(60).dropna()
                    returns_matrix.append(r)
                if len(returns_matrix) > 1:
                    raw_ret = pd.concat(returns_matrix, axis=1)
                    ret_df = raw_ret.ffill().bfill().dropna()
                    if len(ret_df) < 10:
                        ret_df = raw_ret.fillna(raw_ret.mean())
                        col_std = raw_ret.std().fillna(0.0).values + 1e-6
                        rng = np.random.default_rng(0)
                        ret_df = ret_df + rng.normal(0.0, 1e-4 * col_std, size=ret_df.shape)
                    cov_mat = ret_df.cov().values
                else:
                    cov_mat = np.eye(len(symbols)) * 0.0004

            df_candidates['raw_score'] = df_candidates['net_return'] / (df_candidates['volatility'] * np.sqrt(20))
            if len(symbols) > 1 and 'cov_mat' in locals() and cov_mat.shape == (len(symbols), len(symbols)):
                if np.any(np.isnan(cov_mat)):
                    np.fill_diagonal(cov_mat, np.nan_to_num(np.diag(cov_mat), nan=1e-4))
                if locals().get('use_herc', False):
                    hrp_w = calculate_herc_weights(cov_mat, symbols=symbols)
                else:
                    hrp_w = calculate_hrp_weights(cov_mat, symbols=symbols)
                df_candidates['hrp_weight'] = hrp_w
                # ── Layer 3: Market Budget × HRP weight ──
                df_candidates['weight'] = hrp_w * df_candidates['market_budget'] * self.max_total_allocation
            else:
                df_candidates['hrp_weight'] = 1.0
                df_candidates['weight'] = df_candidates['market_budget'] * self.max_total_allocation
        elif use_kelly:
            # Kelly formula: f* = kelly_fraction × (net_return / var_20d) × vol_scale
            vol_floor = 0.005
            vols = np.where(df_candidates['volatility'] < vol_floor, vol_floor, df_candidates['volatility'])
            var_20d = 20.0 * (vols ** 2)
            # Target Volatility Scaling (15% target annualized vol anchoring)
            ann_vol = vols * np.sqrt(252)
            vol_scale = np.clip(0.15 / np.maximum(ann_vol, 0.05), 0.30, 2.0)
            df_candidates['raw_score'] = kelly_fraction * (df_candidates['net_return'] / var_20d) * vol_scale
        else:
            df_candidates['raw_score'] = df_candidates['net_return'] / (df_candidates['volatility'] * np.sqrt(20))

        # Resolve Regime-Adaptive Max Candidates, Effective Max Allocation, & Minimum Position Threshold
        regime_str = str(regime).upper() if regime is not None else ""
        if "BULL" in regime_str or regime == 2:
            max_top_n = 30           # 강세장: 최상위 유망주 20~30개 적극 배분으로 수익률 극대화
            effective_min_pos = 0.005 # 최소 투자비중 0.5%로 완화하여 유망 종목 폭넓게 포착
            effective_max_alloc = max(self.max_total_allocation, 0.98) # Cash Drag Eliminator
        elif "BEAR" in regime_str or regime == 0 or "CRISIS" in regime_str:
            max_top_n = 8            # 약세장/위기: 방어주 5~8개로 엄격하게 압축하여 손실 방어
            effective_min_pos = 0.02  # 최소 투자비중 2.0%
            effective_max_alloc = min(self.max_total_allocation, 0.50)
        else:
            # 횡보장 / 기본 미지정 레짐: 안정적 분산 및 사용자가 지정한 max_total_allocation 준수
            max_top_n = 20
            effective_min_pos = 0.01
            effective_max_alloc = self.max_total_allocation

        # Select top candidates based on regime dynamics
        df_candidates = df_candidates.sort_values('raw_score', ascending=False).head(max_top_n).copy()

        if locals().get('use_conviction', False):
            # Conviction Alpha Precision Sizing (Information Ratio Maximizer)
            conv_w = self.calculate_conviction_alpha_weights(
                expected_returns=df_candidates['net_return'].values,
                volatilities=df_candidates['volatility'].values,
                gamma=1.5,
                max_single_cap=self.max_single_position
            )
            df_candidates['weight'] = conv_w * effective_max_alloc
        elif use_hrp:
            # C2 FIX: After Top-N slicing, HRP weights only sum to a fraction of 1.0
            # (e.g. 0.40 if 15 of 60 stocks selected). Renormalize UP to effective_max_alloc.
            current_hrp_sum = df_candidates['weight'].sum()
            if current_hrp_sum > 1e-8 and current_hrp_sum < effective_max_alloc:
                df_candidates['weight'] = (df_candidates['weight'] / current_hrp_sum) * effective_max_alloc
                logger.info(f"[HRP] Renormalized weights after Top-N slicing: {current_hrp_sum:.3f} -> {effective_max_alloc:.3f}")
        elif use_kelly:
            # ── Layer 3: Kelly raw_score × Market Budget ──
            df_candidates['weight'] = df_candidates['raw_score'] * df_candidates['market_budget']
        else:
            # ── Layer 3: Sharpe-proxy score × Market Budget 정규화 ──
            # 시장별로 그룹화하여 Market Budget 내에서 종목 가중치 합산
            market_weights = []
            for mkt, grp in df_candidates.groupby('market'):
                budget = norm_market_budgets.get(mkt.upper(), 1.0 / max(len(present_markets), 1))
                total_score = grp['raw_score'].sum()
                if total_score > 0:
                    grp = grp.copy()
                    grp['weight'] = (grp['raw_score'] / total_score) * budget * effective_max_alloc
                else:
                    grp = grp.copy()
                    grp['weight'] = 0.0
                market_weights.append(grp)
            df_candidates = pd.concat(market_weights).sort_values('raw_score', ascending=False)

        # Enforce maximum single position constraints
        df_candidates['weight'] = df_candidates['weight'].clip(upper=self.max_single_position)

        # Filter out positions that are too small based on regime-adaptive minimum
        df_candidates = df_candidates[df_candidates['weight'] >= effective_min_pos].copy()

        # Enforce maximum total allocation
        current_sum = df_candidates['weight'].sum()
        if current_sum > effective_max_alloc and current_sum > 0:
            df_candidates['weight'] = (df_candidates['weight'] / current_sum) * effective_max_alloc

        # Enforce sector risk cap
        effective_sector_map = sector_map or {}
        if 'sector' in df_candidates.columns or effective_sector_map:
            if 'sector' not in df_candidates.columns:
                df_candidates['sector'] = df_candidates['symbol'].map(lambda s: effective_sector_map.get(s, "Unknown"))

            sector_totals = df_candidates.groupby('sector')['weight'].sum()
            for sec, sec_weight in sector_totals.items():
                if sec_weight > self.max_sector_exposure and sec_weight > 0:
                    scale = self.max_sector_exposure / sec_weight
                    sec_mask = df_candidates['sector'] == sec
                    df_candidates.loc[sec_mask, 'weight'] *= scale

        # Compute capital allocation amounts and discrete lot sizing
        latest_prices = []
        lot_size_list = []
        min_order_qty_list = []

        for _, row in df_candidates.iterrows():
            sym = str(row['symbol'])
            mkt = str(row.get('market', '')).upper()
            p_val = 0.0
            if prices_dict and sym in prices_dict and not prices_dict[sym].empty:
                df_p = prices_dict[sym]
                c_col = 'Close' if 'Close' in df_p.columns else ('close' if 'close' in df_p.columns else None)
                if c_col:
                    cl_series = df_p[c_col]
                    if isinstance(cl_series, pd.DataFrame):
                        cl_series = cl_series.iloc[:, 0]
                    p_val = float(cl_series.iloc[-1])
            if (p_val <= 0 or np.isnan(p_val)) and 'close' in row and pd.notna(row['close']):
                p_val = float(row['close'])
            if (p_val <= 0 or np.isnan(p_val)) and 'close_price' in row and pd.notna(row['close_price']):
                p_val = float(row['close_price'])

            latest_prices.append(max(0.0, p_val))

            # Market-specific standard lot size (KRX: 1, US: 1, JP/VN/HK: 100)
            if mkt in ['JAPAN_TSE', 'VIETNAM_HOSE', 'HKEX'] or sym.endswith(('.T', '.VN', '.HK')):
                l_sz = 100
            else:
                l_sz = 1
            lot_size_list.append(l_sz)
            min_order_qty_list.append(l_sz)

        # Apply discrete lot-sizing allocation
        from src.analysis.portfolio_optimizer import discretize_weights_to_lot_sizes
        has_prices = any(p > 0 for p in latest_prices)
        if has_prices and total_portfolio_value > 0:
            disc_result = discretize_weights_to_lot_sizes(
                weights=df_candidates['weight'].values,
                prices=latest_prices,
                total_capital=total_portfolio_value,
                lot_sizes=lot_size_list,
                min_order_quantities=min_order_qty_list,
                max_single_cap=self.max_single_position,
                allow_greedy_remainder=True
            )
            df_candidates['shares'] = disc_result['shares']
            df_candidates['lot_size'] = disc_result['lot_sizes']
            df_candidates['min_order_qty'] = disc_result['min_order_quantities']
            df_candidates['executable_amount'] = disc_result['amounts']
            df_candidates['realized_weight'] = disc_result['realized_weights']
            df_candidates['is_executable'] = disc_result['is_executable']
            df_candidates['allocation_amount'] = disc_result['amounts']
            df_candidates['weight'] = np.where(disc_result['shares'] > 0, disc_result['realized_weights'], df_candidates['weight'])
        else:
            df_candidates['shares'] = 0
            df_candidates['lot_size'] = lot_size_list
            df_candidates['min_order_qty'] = min_order_qty_list
            df_candidates['executable_amount'] = df_candidates['weight'] * total_portfolio_value
            df_candidates['realized_weight'] = df_candidates['weight']
            df_candidates['is_executable'] = True
            df_candidates['allocation_amount'] = df_candidates['weight'] * total_portfolio_value

        return df_candidates.sort_values('weight', ascending=False).reset_index(drop=True)

    def allocate_black_litterman(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        predicted_returns: Dict[str, float],
        total_portfolio_value: float = 100_000_000,
        tau: float = 0.05,
        risk_aversion: float = 2.5
    ) -> pd.DataFrame:
        """
        Calculates Black-Litterman optimal asset allocation weights.
        """
        from src.analysis.portfolio_optimizer import calculate_black_litterman_weights, discretize_weights_to_lot_sizes
        symbols = [s for s in predicted_returns.keys() if s in prices_dict]
        if len(symbols) < 2:
            return pd.DataFrame()

        returns_list = []
        valid_symbols = []
        preds = []
        for s in symbols:
            df_p = prices_dict[s]
            c = df_p['Close'].iloc[:, 0] if isinstance(df_p['Close'], pd.DataFrame) else df_p['Close']
            r = c.pct_change().tail(60).dropna()
            if len(r) >= 20:
                returns_list.append(r)
                valid_symbols.append(s)
                preds.append(predicted_returns[s])

        if len(valid_symbols) < 2:
            return pd.DataFrame()

        ret_raw = pd.concat(returns_list, axis=1)
        common = ret_raw.dropna(how='any')
        if len(common) >= 10:
            ret_df = common
        else:
            ret_df = ret_raw.fillna(ret_raw.mean())
        cov_matrix = ret_df.cov().values
        prior_weights = np.full(len(valid_symbols), 1.0 / len(valid_symbols))

        bl_weights = calculate_black_litterman_weights(
            cov_matrix=cov_matrix,
            predicted_returns=np.array(preds),
            prior_weights=prior_weights,
            risk_aversion=risk_aversion,
            tau=tau
        )

        latest_prices = []
        lot_sizes = []
        for s in valid_symbols:
            df_p = prices_dict[s]
            c = df_p['Close'].iloc[:, 0] if isinstance(df_p['Close'], pd.DataFrame) else df_p['Close']
            latest_prices.append(float(c.iloc[-1]))
            if str(s).endswith(('.T', '.VN', '.HK')):
                lot_sizes.append(100)
            else:
                lot_sizes.append(1)

        disc = discretize_weights_to_lot_sizes(
            weights=bl_weights,
            prices=latest_prices,
            total_capital=total_portfolio_value,
            lot_sizes=lot_sizes,
            max_single_cap=self.max_single_position,
            allow_greedy_remainder=True
        )

        res_df = pd.DataFrame({
            'symbol': valid_symbols,
            'weight': disc['realized_weights'],
            'allocation_amount': disc['amounts'],
            'shares': disc['shares'],
            'lot_size': disc['lot_sizes'],
            'min_order_qty': disc['min_order_quantities'],
            'is_executable': disc['is_executable']
        }).sort_values(by='weight', ascending=False).reset_index(drop=True)

        return res_df

    def apply_slippage_feedback_haircut(
        self,
        weights_dict: Dict[str, float],
        realized_slippage_map: Optional[Dict[str, float]] = None,
        max_slippage_bps_threshold: float = 30.0
    ) -> Dict[str, float]:
        """
        Applies dynamic position haircut based on realized execution slippage from trade_logs.db.
        If an asset's realized slippage exceeds threshold (e.g. 30 bps = 0.30%),
        its allocation is scaled down by kappa_slip = max(0.50, 1.0 - (excess_bps / 100.0) * 2.0).
        """
        if not weights_dict or not realized_slippage_map:
            return dict(weights_dict)

        adjusted_weights = {}
        for sym, w in weights_dict.items():
            slip_bps = float(realized_slippage_map.get(sym, 0.0))
            if slip_bps > max_slippage_bps_threshold:
                excess_bps = slip_bps - max_slippage_bps_threshold
                haircut = max(0.50, 1.0 - (excess_bps / 100.0) * 2.0)
                adj_w = w * haircut
                adjusted_weights[sym] = float(adj_w)
                logger.info(
                    f"[SLIPPAGE SIZING HAIRCUT] Symbol {sym}: Realized Slippage {slip_bps:.1f} bps > {max_slippage_bps_threshold} bps threshold "
                    f"-> Haircut multiplier {haircut:.2f} applied (Weight: {w:.3f} -> {adj_w:.3f})"
                )
            else:
                adjusted_weights[sym] = float(w)

        return adjusted_weights


