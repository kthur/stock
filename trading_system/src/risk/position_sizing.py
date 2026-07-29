import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class PortfolioAllocator:
    """
    Optimizes portfolio allocation based on predicted returns, volatility,
    and risk parameters (Kelly Criterion / Sharpe Ratio proxy).
    """

    def __init__(self,
                 max_single_position: float = 0.15,
                 min_single_position: float = 0.02,
                 max_total_allocation: float = 0.85,
                 max_sector_exposure: float = 0.30,
                 target_horizon: int = 20,
                 use_kelly: bool = True,
                 kelly_fraction: float = 0.5):
        self.max_single_position = max_single_position
        self.min_single_position = min_single_position
        self.max_total_allocation = max_total_allocation
        self.max_sector_exposure = max_sector_exposure
        self.target_horizon = target_horizon
        self.use_kelly = use_kelly
        self.kelly_fraction = kelly_fraction

    def allocate(self,
                 predictions_df: pd.DataFrame,
                 prices_dict: Dict[str, pd.DataFrame],
                 total_portfolio_value: float = 10000000.0,
                 use_kelly: Optional[bool] = None,
                 kelly_fraction: Optional[float] = None,
                 use_hrp: bool = False,
                 sector_map: Optional[Dict[str, str]] = None,
                 regime: Optional[Any] = None) -> pd.DataFrame:
        """
        Computes portfolio weights and cash allocation using Regime-Adaptive Kelly Criterion, Sharpe proxy, or HRP.

        Args:
            predictions_df: DataFrame with columns ['symbol', target_horizon] where target_horizon contains predicted returns.
            prices_dict: Dict of symbol -> OHLCV DataFrame to extract recent volatility (vol_20d).
            total_portfolio_value: Total money available to invest.
            use_kelly: Override class setting for Kelly sizing.
            kelly_fraction: Override class setting for Kelly fraction.
            use_hrp: If True, computes weights using Hierarchical Risk Parity algorithm.
            sector_map: Mapping of symbol -> sector name.
            regime: 2D or 1D market regime (BULL, SIDEWAYS, BEAR).

        Returns:
            DataFrame with columns ['symbol', 'predicted_return', 'volatility', 'raw_score', 'weight', 'allocation_amount']
        """
        if predictions_df.empty or not prices_dict:
            logger.warning("Empty predictions or prices_dict. Allocation skipped.")
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

        records = []
        for _, row in predictions_df.iterrows():
            sym = row['symbol']
            pred_ret = row[horizon_col]

            # Skip negative expected returns
            if pred_ret <= 0:
                continue

            df_price = prices_dict.get(sym)
            if df_price is None or len(df_price) < 21:
                continue

            close = df_price['Close']
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]

            daily_returns = close.pct_change().dropna()
            vol = daily_returns.tail(20).std()

            # Liquidity-proportional slippage estimation based on recent 20d volume/value
            volume_series = df_price['Volume'] if 'Volume' in df_price.columns else None
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

            net_pred_ret = pred_ret - cost
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

        # HRP Allocation Path
        if use_hrp:
            from src.analysis.portfolio_optimizer import calculate_hrp_weights
            symbols = df_candidates['symbol'].tolist()
            returns_matrix = []
            for s in symbols:
                df_p = prices_dict[s]
                c = df_p['Close'].iloc[:, 0] if isinstance(df_p['Close'], pd.DataFrame) else df_p['Close']
                r = c.pct_change().tail(60).dropna()
                returns_matrix.append(r)
            if len(returns_matrix) > 1:
                ret_df = pd.concat(returns_matrix, axis=1).fillna(0.0)
                cov_mat = ret_df.cov().values
                hrp_w = calculate_hrp_weights(cov_mat)
                df_candidates['raw_score'] = hrp_w
                df_candidates['weight'] = hrp_w * self.max_total_allocation
            else:
                df_candidates['raw_score'] = 1.0
                df_candidates['weight'] = self.max_total_allocation
        elif use_kelly:
            # Kelly formula with matched 20-day variance horizon: f* = kelly_fraction * (net_return / var_20d)
            vol_floor = 0.005
            vols = np.where(df_candidates['volatility'] < vol_floor, vol_floor, df_candidates['volatility'])
            var_20d = 20.0 * (vols ** 2)  # Scale daily variance to 20-day horizon to match 20-day net_return
            df_candidates['raw_score'] = kelly_fraction * (df_candidates['net_return'] / var_20d)
        else:
            df_candidates['raw_score'] = df_candidates['net_return'] / (df_candidates['volatility'] * np.sqrt(20))


        # Select top candidates (up to 15)
        df_candidates = df_candidates.sort_values('raw_score', ascending=False).head(15).copy()

        if use_hrp:
            pass
        elif use_kelly:
            df_candidates['weight'] = df_candidates['raw_score']
        else:
            total_score = df_candidates['raw_score'].sum()
            if total_score <= 0:
                return pd.DataFrame()
            df_candidates['weight'] = (df_candidates['raw_score'] / total_score) * self.max_total_allocation

        # Enforce maximum single position constraints
        df_candidates['weight'] = df_candidates['weight'].clip(upper=self.max_single_position)

        # Filter out positions that are too small
        df_candidates = df_candidates[df_candidates['weight'] >= self.min_single_position].copy()

        # Enforce maximum total allocation
        current_sum = df_candidates['weight'].sum()
        if current_sum > self.max_total_allocation and current_sum > 0:
            df_candidates['weight'] = (df_candidates['weight'] / current_sum) * self.max_total_allocation

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

        # Compute capital allocation amounts
        df_candidates['allocation_amount'] = df_candidates['weight'] * total_portfolio_value

        return df_candidates.sort_values('weight', ascending=False).reset_index(drop=True)

