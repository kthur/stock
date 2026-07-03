import logging
import typing
import pandas as pd

logger = logging.getLogger(__name__)

class EnsembleScoringEngine:
    """
    Ensembles multiple predictions (Regression, Surge Classifier, Lead-Lag, VCP ML)
    using dynamic weights based on the current market regime.
    """

    # Dynamic Weight Configuration per Market Regime
    # 0: BEAR, 1: SIDEWAYS, 2: BULL
    REGIME_WEIGHTS = {
        0: {  # BEAR (Defensive: high weight on regression fundamentals, 0% on surge)
            'regression': 0.70,
            'surge': 0.00,
            'lead_lag': 0.20,
            'vcp_ml': 0.10
        },
        1: {  # SIDEWAYS (Rotation: balanced, high weight on Lead-Lag sector flow)
            'regression': 0.35,
            'surge': 0.15,
            'lead_lag': 0.35,
            'vcp_ml': 0.15
        },
        2: {  # BULL (Aggressive: high weight on Surge and VCP ML breakout momentum)
            'regression': 0.15,
            'surge': 0.40,
            'lead_lag': 0.05,
            'vcp_ml': 0.40
        }
    }

    def __init__(self):
        pass

    def calculate_ensemble_score(self,
                                 regime: int,
                                 regression_df: pd.DataFrame,
                                 surge_df: pd.DataFrame,
                                 lead_lag_df: pd.DataFrame,
                                 vcp_ml_df: pd.DataFrame,
                                 target_horizon: int = 20) -> pd.DataFrame:
        """
        Merges all strategy outputs and calculates a unified weighted score.
        Calculates an 'ensemble_return_proxy' suitable for PortfolioAllocator.
        """
        # Ensure regime index is valid, fallback to SIDEWAYS if not
        weights = self.REGIME_WEIGHTS.get(regime, self.REGIME_WEIGHTS[1])
        logger.info(f"Applying Ensemble weights for Regime {regime}: {weights}")

        # 1. Prepare Regression Scores
        # target_horizon or closest numeric column
        reg_df = regression_df.copy()
        horizon_col: typing.Any = target_horizon
        if horizon_col not in reg_df.columns:
            numeric_cols = [c for c in reg_df.columns if isinstance(c, (int, float))]
            if numeric_cols:
                horizon_col = min(numeric_cols, key=lambda x: abs(x - target_horizon))
            else:
                horizon_col = reg_df.columns[-1]  # fallback

        reg_df = reg_df[['symbol', horizon_col]].rename(columns={horizon_col: 'reg_pred'})
        # Rank-normalize regression outputs to [0, 1] range to avoid outlier dominance
        if len(reg_df) > 1:
            reg_df['reg_score'] = reg_df['reg_pred'].rank(pct=True)
        else:
            reg_df['reg_score'] = 1.0

        # 2. Prepare Surge Scores (probabilities already in [0, 1])
        if not surge_df.empty:
            s_df = surge_df.copy()
            # Find the best match for the target horizon
            surge_horizons = [1, 3, 5, 20]
            closest_surge_horizon = min(surge_horizons, key=lambda x: abs(x - target_horizon))
            s_col = f'surge_{closest_surge_horizon}d'
            if s_col not in s_df.columns:
                num_cols = [c for c in s_df.columns if c != 'symbol' and pd.api.types.is_numeric_dtype(s_df[c])]
                s_col = num_cols[-1] if num_cols else s_df.columns[-1]
            s_df = s_df[['symbol', s_col]].rename(columns={s_col: 'surge_score'})
        else:
            s_df = pd.DataFrame(columns=['symbol', 'surge_score'])

        # 3. Prepare Lead-Lag Scores
        if not lead_lag_df.empty:
            ll_df = lead_lag_df.copy()
            ll_col = 'lead_lag_score' if 'lead_lag_score' in ll_df.columns else ll_df.columns[-1]
            ll_df = ll_df[['symbol', ll_col]].rename(columns={ll_col: 'll_raw'})
            # Min-Max normalize Lead-Lag scores to [0, 1]
            if len(ll_df) > 1:
                min_val = ll_df['ll_raw'].min()
                max_val = ll_df['ll_raw'].max()
                denom = (max_val - min_val) if max_val != min_val else 1.0
                ll_df['ll_score'] = (ll_df['ll_raw'] - min_val) / denom
            else:
                ll_df['ll_score'] = 1.0
        else:
            ll_df = pd.DataFrame(columns=['symbol', 'll_raw', 'll_score'])

        # 4. Prepare VCP ML Scores (probabilities already in [0, 1])
        if not vcp_ml_df.empty:
            v_df = vcp_ml_df.copy()
            closest_vcp_horizon = min(surge_horizons, key=lambda x: abs(x - target_horizon))
            v_col = f'vcp_{closest_vcp_horizon}d'
            if v_col not in v_df.columns:
                num_cols = [c for c in v_df.columns if c != 'symbol' and pd.api.types.is_numeric_dtype(v_df[c])]
                v_col = num_cols[-1] if num_cols else v_df.columns[-1]
            v_df = v_df[['symbol', v_col]].rename(columns={v_col: 'vcp_ml_score'})
        else:
            v_df = pd.DataFrame(columns=['symbol', 'vcp_ml_score'])

        # Outer join all strategies
        merged = reg_df.merge(s_df, on='symbol', how='outer')
        merged = merged.merge(ll_df, on='symbol', how='outer')
        merged = merged.merge(v_df, on='symbol', how='outer')

        # Fill NaNs with 0.0 (meaning strategy gave no signal for this symbol)
        fill_cols = ['reg_pred', 'reg_score', 'surge_score', 'll_raw', 'll_score', 'vcp_ml_score']
        for col in fill_cols:
            if col in merged.columns:
                merged[col] = merged[col].fillna(0.0)

        # Calculate final weighted score [0, 1]
        merged['ensemble_score'] = (
            weights['regression'] * merged['reg_score'] +
            weights['surge'] * merged['surge_score'] +
            weights['lead_lag'] * merged['ll_score'] +
            weights['vcp_ml'] * merged['vcp_ml_score']
        )

        # Scale Ensemble Score to a Return Proxy (%) for Portfolio Allocation
        # A maximum score of 1.0 maps to a 20% expected return.
        # This keeps the expectations within standard bounds for stable Kelly optimization.
        merged['ensemble_expected_return'] = merged['ensemble_score'] * 20.0

        # Sort by ensemble score descending
        merged = merged.sort_values(by='ensemble_score', ascending=False).reset_index(drop=True)
        return merged
