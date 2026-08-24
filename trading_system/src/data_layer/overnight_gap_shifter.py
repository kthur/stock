"""
Pre-Market Overnight Gap Shifter Module:
- Aggregates US Market Close (SPY, QQQ, SOXX), VIX Delta, and USD/KRW NDF/FX shifts.
- Computes estimated KRX Opening Gap percentage (ΔP_open).
- Calibrates 31-strategy ensemble scores and momentum vs defensive tilts before 09:00 KST open.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class OvernightGapShifter:
    """
    Overnight Gap Shifter Engine for Cross-Border Pre-Market Calibration.
    Estimates Korean market opening gap from overnight US & FX factors
    and adjusts tactical factor weights accordingly.
    """

    def __init__(self, spy_beta: float = 0.55, qqq_beta: float = 0.25, vix_beta: float = -0.15, fx_beta: float = -0.10):
        self.spy_beta = spy_beta
        self.qqq_beta = qqq_beta
        self.vix_beta = vix_beta
        self.fx_beta = fx_beta

    def fetch_overnight_factors(self, indicator_df: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """
        Extracts overnight factor deltas from recent global indicator DataFrame or defaults.
        """
        factors = {
            'spy_return': 0.0,
            'qqq_return': 0.0,
            'soxx_return': 0.0,
            'vix_change': 0.0,
            'usdkrw_change': 0.0,
            'wti_change': 0.0
        }

        if indicator_df is not None and not indicator_df.empty:
            last_row = indicator_df.iloc[-1]
            for k in ['sp500_change', 'sp500_ret', 'sp500_pct_change', '^gspc_change']:
                if k in indicator_df.columns:
                    val = float(last_row[k])
                    factors['spy_return'] = val if np.isfinite(val) else 0.0
                    break
            for k in ['nasdaq_change', 'nasdaq_ret', '^ixic_change']:
                if k in indicator_df.columns:
                    val = float(last_row[k])
                    factors['qqq_return'] = val if np.isfinite(val) else 0.0
                    break
            for k in ['vix_change', 'vix_ret', '^vix_change']:
                if k in indicator_df.columns:
                    val = float(last_row[k])
                    factors['vix_change'] = val if np.isfinite(val) else 0.0
                    break
            for k in ['usdkrw_change', 'usdkrw_ret']:
                if k in indicator_df.columns:
                    val = float(last_row[k])
                    factors['usdkrw_change'] = val if np.isfinite(val) else 0.0
                    break
            for k in ['wti_change', 'cl_change']:
                if k in indicator_df.columns:
                    val = float(last_row[k])
                    factors['wti_change'] = val if np.isfinite(val) else 0.0
                    break

        return factors

    def compute_opening_gap_estimate(self, overnight_factors: Dict[str, float]) -> float:
        """
        Calculates estimated opening gap percentage (%) for KRX markets.
        Gap = beta_spy * r_spy + beta_qqq * r_qqq + beta_vix * delta_vix + beta_fx * delta_fx
        """
        spy_r = float(overnight_factors.get('spy_return', 0.0))
        qqq_r = float(overnight_factors.get('qqq_return', spy_r))
        vix_d = float(overnight_factors.get('vix_change', 0.0))
        fx_d = float(overnight_factors.get('usdkrw_change', 0.0))

        raw_gap = (
            self.spy_beta * spy_r +
            self.qqq_beta * qqq_r +
            self.vix_beta * vix_d +
            self.fx_beta * fx_d
        )
        # Bounded between -4.0% and +4.0%
        return float(np.clip(raw_gap, -4.0, 4.0))

    def apply_gap_shift_to_scores(
        self,
        ensemble_df: pd.DataFrame,
        gap_pct: float,
        market: str = "KOSPI"
    ) -> pd.DataFrame:
        """
        Calibrates ensemble scores based on estimated opening gap.
        - Positive Gap (> +0.5%): Amplifies momentum & breakout strategies.
        - Negative Gap (< -0.5%): Amplifies defensive, valuation & mean-reversion strategies.
        """
        if ensemble_df.empty or abs(gap_pct) < 0.20:
            return ensemble_df

        df_out = ensemble_df.copy()
        is_krx = str(market).upper() in ["KOSPI", "KOSDAQ", "KRX"]

        if not is_krx:
            return df_out

        shift_mag = min(0.08, abs(gap_pct) * 0.02)

        if gap_pct > 0:
            # Positive gap: momentum boost
            for mom_col in ['surge_score', 'vcp_ml_score', 'trend_efficiency_score', 'order_flow_score']:
                if mom_col in df_out.columns:
                    df_out[mom_col] = (df_out[mom_col] + shift_mag).clip(0.0, 1.0)
            logger.info(f"[OVERNIGHT GAP SHIFTER] Applied +{shift_mag:.3f} momentum boost for +{gap_pct:.2f}% opening gap.")
        else:
            # Negative gap: defensive / value boost
            for def_col in ['rim_score', 'valueup_catalyst_score', 'reversal_score', 'stat_arb_score', 'vol_target_score']:
                if def_col in df_out.columns:
                    df_out[def_col] = (df_out[def_col] + shift_mag).clip(0.0, 1.0)
            logger.info(f"[OVERNIGHT GAP SHIFTER] Applied +{shift_mag:.3f} defensive boost for {gap_pct:.2f}% opening gap.")

        df_out.attrs['overnight_gap_pct'] = gap_pct
        return df_out
