import logging
import typing
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Union, Set, List


logger = logging.getLogger(__name__)

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


class EnsembleScoringEngine:
    """
    Ensembles 5 strategy predictions (Regression, Surge Classifier, Lead-Lag, VCP Rule Detector, VCP ML Predictor)
    using 2D regime matrix weights and dynamic exponential Sharpe weighting.
    """

    # Dynamic Weight Configuration per 1D Market Regime (0: BEAR, 1: SIDEWAYS, 2: BULL)
    REGIME_WEIGHTS = {
        0: {  # BEAR (Defensive: high weight on regression fundamentals)
            'regression': 0.55,
            'surge': 0.05,
            'lead_lag': 0.15,
            'vcp_rule': 0.15,
            'vcp_ml': 0.10
        },
        1: {  # SIDEWAYS (Rotation: balanced)
            'regression': 0.25,
            'surge': 0.15,
            'lead_lag': 0.30,
            'vcp_rule': 0.15,
            'vcp_ml': 0.15
        },
        2: {  # BULL (Aggressive: high weight on Surge and VCP ML)
            'regression': 0.15,
            'surge': 0.35,
            'lead_lag': 0.10,
            'vcp_rule': 0.10,
            'vcp_ml': 0.30
        }
    }

    # 2D Market Regime Matrix Weights (6 Combo States across 5 Strategies)
    REGIME_2D_WEIGHTS = {
        'BEAR_LOW_VOL': {
            'regression': 0.55,
            'surge': 0.05,
            'lead_lag': 0.15,
            'vcp_rule': 0.15,
            'vcp_ml': 0.10
        },
        'BEAR_HIGH_VOL': {
            'regression': 0.65,
            'surge': 0.00,
            'lead_lag': 0.10,
            'vcp_rule': 0.15,
            'vcp_ml': 0.10
        },
        'SIDEWAYS_LOW_VOL': {
            'regression': 0.25,
            'surge': 0.15,
            'lead_lag': 0.30,
            'vcp_rule': 0.15,
            'vcp_ml': 0.15
        },
        'SIDEWAYS_HIGH_VOL': {
            'regression': 0.35,
            'surge': 0.10,
            'lead_lag': 0.25,
            'vcp_rule': 0.15,
            'vcp_ml': 0.15
        },
        'BULL_LOW_VOL': {
            'regression': 0.15,
            'surge': 0.35,
            'lead_lag': 0.10,
            'vcp_rule': 0.10,
            'vcp_ml': 0.30
        },
        'BULL_HIGH_VOL': {
            'regression': 0.10,
            'surge': 0.40,
            'lead_lag': 0.05,
            'vcp_rule': 0.10,
            'vcp_ml': 0.35
        }
    }

    def __init__(self, config=None):
        # Support TradingConfig for centralized constant management
        self._return_multiplier = 20.0  # default
        if config is not None:
            self._return_multiplier = getattr(config, "ensemble_return_multiplier", 20.0)

    def compute_rolling_sharpe(self, strategy_returns: Dict[str, Union[pd.Series, list]],
                              window: int = 20,
                              risk_free_rate: float = 0.0) -> Dict[str, float]:
        """
        Computes recent rolling Sharpe ratio for each strategy.
        Sharpe_i = (mean(R_i) - r_f) / (std(R_i) + 1e-6) * sqrt(252)
        """
        sharpes = {}
        for strategy, ret_data in strategy_returns.items():
            try:
                s = pd.Series(ret_data).dropna()
                if len(s) >= 2:
                    recent = s.tail(window)
                    mean_ret = float(recent.mean())
                    std_ret = float(recent.std())
                    if std_ret < 1e-8:
                        std_ret = 1e-6
                    sharpe = ((mean_ret - risk_free_rate) / std_ret) * np.sqrt(252)
                    sharpes[strategy] = float(sharpe)
                else:
                    sharpes[strategy] = 0.0
            except Exception as e:
                logger.warning(f"Error calculating rolling Sharpe for {strategy}: {e}")
                sharpes[strategy] = 0.0
        return sharpes

    def get_base_weights(self, regime: Union[int, str]) -> Dict[str, float]:
        """Resolves base weights from 1D regime code or 2D regime combo label."""
        if isinstance(regime, str) and regime in self.REGIME_2D_WEIGHTS:
            return dict(self.REGIME_2D_WEIGHTS[regime])

        if isinstance(regime, str):
            # Try parsing integer prefix or label matching
            if 'BEAR' in regime:
                reg_code = 0
            elif 'BULL' in regime:
                reg_code = 2
            else:
                reg_code = 1
        else:
            reg_code = int(regime)

        base = self.REGIME_WEIGHTS.get(reg_code, self.REGIME_WEIGHTS[1])
        # Ensure all 5 strategies are present
        res = {
            'regression': base.get('regression', 0.25),
            'surge': base.get('surge', 0.20),
            'lead_lag': base.get('lead_lag', 0.20),
            'vcp_rule': base.get('vcp_rule', 0.15),
            'vcp_ml': base.get('vcp_ml', 0.20)
        }
        total = sum(res.values())
        return {k: v / total for k, v in res.items()}

    def compute_dynamic_weights_from_sharpe(self, rolling_sharpes: Dict[str, float],
                                            regime: Union[int, str],
                                            gamma: float = 1.0) -> Dict[str, float]:
        """
        Dynamically adjusts strategy weights using recent rolling Sharpe ratios per strategy.
        Formula: w_i_dynamic = base_w_i * exp(gamma * Sharpe_i) / sum(base_w_j * exp(gamma * Sharpe_j))
        """
        base_weights = self.get_base_weights(regime)
        if not rolling_sharpes:
            return base_weights

        scores = {}
        for strategy, base_w in base_weights.items():
            sharpe = float(rolling_sharpes.get(strategy, 0.0))
            # Exponential Sharpe weighting multiplier: exp(gamma * Sharpe)
            multiplier = float(np.exp(gamma * np.clip(sharpe, -3.0, 3.0)))
            scores[strategy] = base_w * multiplier

        total_score = sum(scores.values())
        if total_score <= 0:
            return base_weights

        dynamic_weights = {k: v / total_score for k, v in scores.items()}
        logger.info(f"Dynamically adjusted Sharpe weights for Regime '{regime}' (gamma={gamma}): {dynamic_weights}")
        return dynamic_weights

    def calculate_ensemble_score(self,
                                 regime: Union[int, str],
                                 regression_df: pd.DataFrame,
                                 surge_df: pd.DataFrame,
                                 lead_lag_df: pd.DataFrame,
                                 vcp_ml_df: pd.DataFrame,
                                 vcp_rule_df: Optional[Union[pd.DataFrame, list]] = None,
                                 vcp_patterns_df: Optional[Union[pd.DataFrame, list]] = None,
                                 rolling_sharpes: Optional[Dict[str, float]] = None,
                                 gamma: float = 1.0,
                                 target_horizon: int = 20,
                                 sentiment_blacklist: Optional[Union[Set[str], List[str], Dict[str, Any]]] = None) -> pd.DataFrame:

        """
        Merges all 5 strategy outputs (Regression, Surge, Lead-Lag, VCP Rule, VCP ML)
        and calculates a unified dynamic weighted ensemble score [0, 1] and expected return proxy (%).
        """
        v_rule_input = vcp_patterns_df if vcp_patterns_df is not None else vcp_rule_df
        if isinstance(v_rule_input, list):
            v_rule_df = pd.DataFrame(v_rule_input) if v_rule_input else pd.DataFrame()
        else:
            v_rule_df = v_rule_input
        if rolling_sharpes:
            weights = self.compute_dynamic_weights_from_sharpe(rolling_sharpes, regime, gamma=gamma)
        else:
            weights = self.get_base_weights(regime)

        logger.info(f"Applying 5-Strategy Ensemble weights for Regime '{regime}': {weights}")

        # 1. Strategy 1: Regression
        if not regression_df.empty:
            reg_df = regression_df.copy()
            horizon_col: typing.Any = target_horizon
            if horizon_col not in reg_df.columns:
                num_cols = [c for c in reg_df.columns if isinstance(c, (int, float))]
                if num_cols:
                    horizon_col = min(num_cols, key=lambda x: abs(x - target_horizon))
                else:
                    horizon_col = reg_df.columns[-1]

            reg_df = reg_df[['symbol', horizon_col]].rename(columns={horizon_col: 'reg_pred'})
            if len(reg_df) > 1:
                reg_df['reg_score'] = reg_df['reg_pred'].rank(pct=True)
            else:
                reg_df['reg_score'] = 1.0
        else:
            reg_df = pd.DataFrame(columns=['symbol', 'reg_pred', 'reg_score'])

        # 2. Strategy 2: Surge Classifier
        if not surge_df.empty:
            s_df = surge_df.copy()
            surge_horizons = [1, 3, 5, 20]
            closest_surge_horizon = min(surge_horizons, key=lambda x: abs(x - target_horizon))
            s_col = f'surge_{closest_surge_horizon}d'
            if s_col not in s_df.columns:
                num_cols = [c for c in s_df.columns if c != 'symbol' and pd.api.types.is_numeric_dtype(s_df[c])]
                s_col = num_cols[-1] if num_cols else s_df.columns[-1]
            s_df = s_df[['symbol', s_col]].rename(columns={s_col: 'surge_score'})
        else:
            s_df = pd.DataFrame(columns=['symbol', 'surge_score'])

        # 3. Strategy 3: Lead-Lag Scores
        if not lead_lag_df.empty:
            ll_df = lead_lag_df.copy()
            ll_col = 'lead_lag_score' if 'lead_lag_score' in ll_df.columns else ll_df.columns[-1]
            ll_df = ll_df[['symbol', ll_col]].rename(columns={ll_col: 'll_raw'})
            if len(ll_df) > 1:
                min_val = ll_df['ll_raw'].min()
                max_val = ll_df['ll_raw'].max()
                denom = (max_val - min_val) if max_val != min_val else 1.0
                ll_df['ll_score'] = (ll_df['ll_raw'] - min_val) / denom
            else:
                ll_df['ll_score'] = 1.0
        else:
            ll_df = pd.DataFrame(columns=['symbol', 'll_raw', 'll_score'])

        # 4. Strategy 4: VCP Rule Detector
        if v_rule_df is not None and not v_rule_df.empty:
            vr_df = v_rule_df.copy()

            if 'vcp_score' in vr_df.columns:
                vr_df['vcp_rule_score'] = vr_df['vcp_score'] / 100.0
            elif 'is_vcp' in vr_df.columns:
                vr_df['vcp_rule_score'] = vr_df['is_vcp'].astype(float)
            else:
                num_cols = [c for c in vr_df.columns if c != 'symbol' and pd.api.types.is_numeric_dtype(vr_df[c])]
                vr_col = num_cols[-1] if num_cols else vr_df.columns[-1]
                vr_df['vcp_rule_score'] = vr_df[vr_col]
            vr_df = vr_df[['symbol', 'vcp_rule_score']]
        else:
            vr_df = pd.DataFrame(columns=['symbol', 'vcp_rule_score'])

        # 5. Strategy 5: VCP ML Predictor
        if not vcp_ml_df.empty:
            v_df = vcp_ml_df.copy()
            surge_horizons = [1, 3, 5, 20]
            closest_vcp_horizon = min(surge_horizons, key=lambda x: abs(x - target_horizon))
            v_col = f'vcp_{closest_vcp_horizon}d'
            if v_col not in v_df.columns:
                num_cols = [c for c in v_df.columns if c != 'symbol' and pd.api.types.is_numeric_dtype(v_df[c])]
                v_col = num_cols[-1] if num_cols else v_df.columns[-1]
            v_df = v_df[['symbol', v_col]].rename(columns={v_col: 'vcp_ml_score'})
        else:
            v_df = pd.DataFrame(columns=['symbol', 'vcp_ml_score'])

        # Outer join all 5 strategies
        merged = reg_df.merge(s_df, on='symbol', how='outer')
        merged = merged.merge(ll_df, on='symbol', how='outer')
        merged = merged.merge(vr_df, on='symbol', how='outer')
        merged = merged.merge(v_df, on='symbol', how='outer')

        # Fill NaNs with 0.0
        fill_cols = ['reg_pred', 'reg_score', 'surge_score', 'll_raw', 'll_score', 'vcp_rule_score', 'vcp_ml_score']
        for col in fill_cols:
            if col in merged.columns:
                merged[col] = merged[col].fillna(0.0)
            else:
                merged[col] = 0.0

        # Calculate final 5-strategy weighted score [0, 1]
        merged['ensemble_score'] = (
            weights.get('regression', 0.20) * merged['reg_score'] +
            weights.get('surge', 0.20) * merged['surge_score'] +
            weights.get('lead_lag', 0.20) * merged['ll_score'] +
            weights.get('vcp_rule', 0.20) * merged['vcp_rule_score'] +
            weights.get('vcp_ml', 0.20) * merged['vcp_ml_score']
        )

        # Scale Ensemble Score to Return Proxy (%)
        merged['ensemble_expected_return'] = merged['ensemble_score'] * self._return_multiplier

        # Apply Sentiment Blacklist filter (zero-weighting for critical disclosure risk)
        if sentiment_blacklist:
            b_set = set(sentiment_blacklist.keys()) if isinstance(sentiment_blacklist, dict) else set(sentiment_blacklist)
            if b_set:
                mask = merged['symbol'].isin(b_set)
                merged.loc[mask, 'ensemble_score'] = 0.0
                merged.loc[mask, 'ensemble_expected_return'] = 0.0
                logger.info(f"[ENSEMBLE SENTIMENT FILTER] Zero-weighted {mask.sum()} blacklisted symbols.")

        # Sort by ensemble score descending
        merged = merged.sort_values(by='ensemble_score', ascending=False).reset_index(drop=True)
        return merged

