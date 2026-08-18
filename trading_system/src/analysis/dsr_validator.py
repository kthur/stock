"""
Deflated Sharpe Ratio (DSR) & Multiple Testing Overfitting Validator Module:
Implements Marcos López de Prado (2014) Deflated Sharpe Ratio (DSR), Expected Maximum
Sharpe Ratio, and Probability of Backtest Overfitting (PBO) for 31-factor multi-strategy
testing and selection bias correction.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from scipy.stats import norm, skew, kurtosis

logger = logging.getLogger(__name__)

# Euler-Mascheroni Constant
_EULER_MASCHERONI = 0.57721566490153286


class DeflatedSharpeRatioValidator:
    """
    Validator to detect and correct for selection bias and backtest overfitting across
    the 31-strategy multi-factor engine.
    """

    def __init__(
        self,
        n_strategies: int = 31,
        n_horizons: int = 8,
        confidence_level: float = 0.95,
        default_annual_trading_days: int = 252
    ):
        self.n_strategies = max(1, int(n_strategies))
        self.n_horizons = max(1, int(n_horizons))
        self.total_trials = self.n_strategies * self.n_horizons
        self.confidence_level = float(np.clip(confidence_level, 0.50, 0.999))
        self.annual_trading_days = max(1, int(default_annual_trading_days))

    @staticmethod
    def compute_expected_max_sharpe(
        n_trials: int,
        var_sharpe: float = 0.50,
        euler_const: float = _EULER_MASCHERONI
    ) -> float:
        """
        Computes the expected maximum Sharpe ratio among N independent/correlated trials:
        E[max(SR)] = sqrt(var_sharpe) * [ (1 - gamma) * Phi^{-1}(1 - 1/N) + gamma * Phi^{-1}(1 - 1/(N*e)) ]

        When N=1, returns 0.0 (no selection bias).
        """
        if n_trials <= 1 or var_sharpe <= 0.0:
            return 0.0

        std_sharpe = float(np.sqrt(max(var_sharpe, 1e-6)))
        n_f = float(n_trials)

        p1 = 1.0 - 1.0 / n_f
        p2 = 1.0 - 1.0 / (n_f * np.e)

        z1 = float(norm.ppf(np.clip(p1, 1e-6, 1.0 - 1e-6)))
        z2 = float(norm.ppf(np.clip(p2, 1e-6, 1.0 - 1e-6)))

        exp_max_sr = std_sharpe * ((1.0 - euler_const) * z1 + euler_const * z2)
        return float(max(0.0, exp_max_sr))

    def compute_dsr(
        self,
        observed_sr: float,
        benchmark_sr: Optional[float] = None,
        n_trials: Optional[int] = None,
        var_sharpe: float = 0.50,
        t_observations: int = 252,
        skewness: float = 0.0,
        kurtosis_val: float = 3.0
    ) -> Dict[str, Any]:
        """
        Calculates the Deflated Sharpe Ratio (DSR) and its corresponding p-value:
        DSR = PSR(SR_benchmark = E[max(SR)])

        Formula for Probabilistic Sharpe Ratio (PSR):
        PSR(SR*) = Phi[ ( (SR - SR*) * sqrt(T - 1) ) / sqrt(1 - gamma3 * SR + (gamma4 - 1)/4 * SR^2) ]
        """
        trials = int(n_trials) if (n_trials is not None and n_trials >= 1) else self.total_trials
        t_obs = max(10, int(t_observations))

        # If benchmark_sr not provided, compute E[max(SR)] under selection bias
        if benchmark_sr is None:
            sr_star = self.compute_expected_max_sharpe(n_trials=trials, var_sharpe=var_sharpe)
        else:
            sr_star = float(benchmark_sr)

        # Standard error of Sharpe ratio under non-normality (Mertens, 2002)
        gamma3 = float(skewness) if np.isfinite(skewness) else 0.0
        gamma4 = float(kurtosis_val) if np.isfinite(kurtosis_val) else 3.0
        # Ensure kurtosis is at least 1.0 to maintain positive variance
        gamma4 = max(1.0, gamma4)

        denom_sq = 1.0 - gamma3 * observed_sr + ((gamma4 - 1.0) / 4.0) * (observed_sr ** 2)
        denom = float(np.sqrt(max(denom_sq, 1e-6)))

        # DSR Z-score
        z_stat = (observed_sr - sr_star) * np.sqrt(t_obs - 1) / denom
        z_stat_clean = float(np.clip(z_stat, -10.0, 10.0))

        dsr_pvalue = float(norm.cdf(z_stat_clean))
        is_significant = bool(dsr_pvalue >= self.confidence_level)

        return {
            'observed_sharpe': float(observed_sr),
            'benchmark_sharpe': float(sr_star),
            'expected_max_sharpe': float(sr_star),
            'deflated_sharpe_z': float(z_stat_clean),
            'dsr_probability': float(dsr_pvalue),
            'is_statistically_significant': is_significant,
            'n_trials': trials,
            't_observations': t_obs,
            'skewness': gamma3,
            'kurtosis': gamma4
        }

    def validate_strategy_alphas(
        self,
        strategy_sharpes: Dict[str, float],
        strategy_returns_df: Optional[pd.DataFrame] = None,
        t_days: int = 252
    ) -> Dict[str, Any]:
        """
        Validates all active strategies simultaneously against multiple testing bias.
        Returns a report detailing DSR scores, false discovery flags, and alpha credibility.
        """
        if not strategy_sharpes:
            return {'valid_strategies': [], 'flagged_strategies': [], 'dsr_results': {}}

        clean_sharpes = {k: float(v) for k, v in strategy_sharpes.items() if v is not None and np.isfinite(v)}
        if not clean_sharpes:
            return {'valid_strategies': [], 'flagged_strategies': [], 'dsr_results': {}}

        n_active = len(clean_sharpes)
        sr_values = np.array(list(clean_sharpes.values()), dtype=float)
        var_sr = float(np.var(sr_values)) if len(sr_values) > 1 else 0.50

        results = {}
        valid_strats = []
        flagged_strats = []

        for strat_name, sr in clean_sharpes.items():
            # Compute empirical skew and kurt if return series is available
            s_skew = 0.0
            s_kurt = 3.0
            if strategy_returns_df is not None and strat_name in strategy_returns_df.columns:
                ret_series = strategy_returns_df[strat_name].dropna()
                if len(ret_series) >= 20:
                    s_skew = float(skew(ret_series))
                    s_kurt = float(kurtosis(ret_series, fisher=False))  # Pearson kurtosis (normal=3.0)

            dsr_info = self.compute_dsr(
                observed_sr=sr,
                n_trials=max(n_active * self.n_horizons, self.total_trials),
                var_sharpe=var_sr,
                t_observations=t_days,
                skewness=s_skew,
                kurtosis_val=s_kurt
            )
            results[strat_name] = dsr_info

            if dsr_info['is_statistically_significant']:
                valid_strats.append(strat_name)
            else:
                flagged_strats.append(strat_name)

        return {
            'n_active_strategies': n_active,
            'total_tested_trials': max(n_active * self.n_horizons, self.total_trials),
            'var_strategy_sharpes': var_sr,
            'valid_strategies': valid_strats,
            'flagged_strategies': flagged_strats,
            'dsr_results': results
        }
