import numpy as np
import pandas as pd
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

def get_daily_vol(close: pd.Series, lookback: int = 20) -> pd.Series:
    """
    Computes daily volatility using exponential moving average of pct_change.
    """
    returns = close.pct_change()
    vol = returns.ewm(span=lookback).std()
    return vol.fillna(0.01)

def apply_triple_barrier(
    df: pd.DataFrame,
    pt_sl: Tuple[float, float] = (1.5, 1.0),
    num_days: int = 10,
    vol_lookback: int = 20
) -> pd.DataFrame:
    """
    Applies Lopez de Prado's Triple Barrier Method.
    
    Args:
        df: DataFrame containing ['High', 'Low', 'Close']
        pt_sl: (Profit Taking factor, Stop Loss factor) relative to daily vol.
        num_days: Maximum holding period (Vertical Barrier).
        vol_lookback: Lookback period for daily volatility estimation.
        
    Returns:
        DataFrame with columns ['ret', 'label', 'meta_label', 'barrier_hit']
    """
    if df.empty or len(df) < vol_lookback:
        return pd.DataFrame()
        
    close = df['Close'].astype(float)
    high = df['High'].astype(float) if 'High' in df.columns else close
    low = df['Low'].astype(float) if 'Low' in df.columns else close
    
    vol = get_daily_vol(close, lookback=vol_lookback)
    
    labels = []
    meta_labels = []
    barrier_hits = []
    returns = []
    
    pt_factor, sl_factor = pt_sl
    
    for i in range(len(df) - num_days):
        entry_price = close.iloc[i]
        curr_vol = vol.iloc[i]
        
        target_pt = entry_price * (1.0 + pt_factor * curr_vol)
        target_sl = entry_price * (1.0 - sl_factor * curr_vol)
        
        future_high = high.iloc[i+1 : i+1+num_days]
        future_low = low.iloc[i+1 : i+1+num_days]
        future_close = close.iloc[i+1 : i+1+num_days]
        
        pt_hit_idx = np.where(future_high >= target_pt)[0]
        sl_hit_idx = np.where(future_low <= target_sl)[0]
        
        pt_time = pt_hit_idx[0] if len(pt_hit_idx) > 0 else 999
        sl_time = sl_hit_idx[0] if len(sl_hit_idx) > 0 else 999
        
        if pt_time < sl_time and pt_time != 999:
            # Profit target hit first
            label = 1
            meta = 1
            hit = 'pt'
            ret = (target_pt - entry_price) / entry_price
        elif sl_time < pt_time and sl_time != 999:
            # Stop loss hit first
            label = -1
            meta = 0
            hit = 'sl'
            ret = (target_sl - entry_price) / entry_price
        else:
            # Vertical barrier (timeout)
            exit_price = future_close.iloc[-1]
            ret = (exit_price - entry_price) / entry_price
            label = 1 if ret > 0 else -1 if ret < 0 else 0
            meta = 1 if ret >= (pt_factor * curr_vol * 0.5) else 0
            hit = 'time'
            
        returns.append(ret)
        labels.append(label)
        meta_labels.append(meta)
        barrier_hits.append(hit)
        
    res_df = pd.DataFrame({
        'return': returns,
        'label': labels,
        'meta_label': meta_labels,
        'barrier_hit': barrier_hits
    }, index=df.index[:len(returns)])
    
    return res_df
