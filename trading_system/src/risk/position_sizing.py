import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional

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
                 target_horizon: int = 20,
                 use_kelly: bool = True,
                 kelly_fraction: float = 0.5):
        self.max_single_position = max_single_position
        self.min_single_position = min_single_position
        self.max_total_allocation = max_total_allocation
        self.target_horizon = target_horizon
        self.use_kelly = use_kelly
        self.kelly_fraction = kelly_fraction

    def allocate(self, 
                 predictions_df: pd.DataFrame, 
                 prices_dict: Dict[str, pd.DataFrame], 
                 total_portfolio_value: float = 10000000.0,
                 use_kelly: Optional[bool] = None,
                 kelly_fraction: Optional[float] = None) -> pd.DataFrame:
        """
        Computes portfolio weights and cash allocation using Kelly Criterion or Sharpe proxy.
        
        Args:
            predictions_df: DataFrame with columns ['symbol', target_horizon] where target_horizon contains predicted returns.
            prices_dict: Dict of symbol -> OHLCV DataFrame to extract recent volatility (vol_20d).
            total_portfolio_value: Total money available to invest.
            use_kelly: Override class setting for Kelly sizing.
            kelly_fraction: Override class setting for Kelly fraction.
            
        Returns:
            DataFrame with columns ['symbol', 'predicted_return', 'volatility', 'raw_score', 'weight', 'allocation_amount']
        """
        if predictions_df.empty or not prices_dict:
            logger.warning("Empty predictions or prices_dict. Allocation skipped.")
            return pd.DataFrame()

        if use_kelly is None:
            use_kelly = self.use_kelly
        if kelly_fraction is None:
            kelly_fraction = self.kelly_fraction

        # Target horizon check
        horizon_col = self.target_horizon
        if horizon_col not in predictions_df.columns:
            # Fallback to the closest available horizon column
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

            # Calculate recent 20d volatility of daily returns
            close = df_price['Close']
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            
            daily_returns = close.pct_change().dropna()
            vol = daily_returns.tail(20).std()
            
            # Avoid division by zero
            if pd.isna(vol) or vol <= 0:
                vol = 0.05  # high default volatility if unknown
                
            records.append({
                'symbol': sym,
                'predicted_return': float(pred_ret),
                'volatility': float(vol)
            })

        if not records:
            logger.warning("No symbols with positive predicted returns and sufficient price data.")
            return pd.DataFrame()

        df_candidates = pd.DataFrame(records)
        
        # Calculate raw sizing scores
        if use_kelly:
            # Kelly formula: f* = kelly_fraction * (predicted_return / variance)
            # Floor volatility to prevent division by zero or extreme sizing
            vol_floor = 0.005
            vols = np.where(df_candidates['volatility'] < vol_floor, vol_floor, df_candidates['volatility'])
            df_candidates['raw_score'] = kelly_fraction * (df_candidates['predicted_return'] / (vols ** 2))
        else:
            # Sharpe-ratio proxy score (predicted return / volatility)
            df_candidates['raw_score'] = df_candidates['predicted_return'] / df_candidates['volatility']
        
        # Select top candidates (e.g. up to 15) to maintain diversification
        df_candidates = df_candidates.sort_values('raw_score', ascending=False).head(15).copy()
        
        if use_kelly:
            # Under Kelly, the raw_score itself is the target weight
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
        
        # Enforce maximum total allocation (scale down if exceeds, but do NOT scale up under Kelly)
        current_sum = df_candidates['weight'].sum()
        if current_sum > self.max_total_allocation and current_sum > 0:
            df_candidates['weight'] = (df_candidates['weight'] / current_sum) * self.max_total_allocation
            
        # Compute capital allocation amounts
        df_candidates['allocation_amount'] = df_candidates['weight'] * total_portfolio_value
        
        return df_candidates.sort_values('weight', ascending=False).reset_index(drop=True)
