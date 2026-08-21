import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


class RegimeFactorSuppressionEngine:
    """
    Implements 2D regime-based factor noise suppression penalties targeting
    multicollinear strategy redundancy.

    Penalty Formulation:
      E_ij = max(0, |rho_ij| - theta(R))
      c_ij(R): Cluster relationship multiplier (higher for intra-cluster & high-risk regime target clusters)
      P_i(R) = 1 / sqrt(1 + lambda(R) * sum_{j != i} c_ij(R) * E_ij^2)
      w_i_suppressed = base_w_i * P_i(R) / sum_k (base_w_k * P_k(R))
    """

    CLUSTER_MAP = {
        'CORE_AI': ['regression', 'lstm', 'vol_target'],
        'MOMENTUM': ['surge', 'vcp_ml', 'sector_rotation', 'arm_factor', 'supply_chain', 'short_squeeze', 'trend_efficiency'],
        'VALUATION': ['rim_valuation', 'rim', 'mq_factor', 'factor_neutralized', 'accruals_quality', 'valueup_catalyst', 'value_up'],
        'REVERSAL': ['stat_arb', 'vcp_rule', 'vcp', 'vcp_patterns', 'short_term_reversal', 'card_factor'],
        'FLOW_MICRO': ['lead_lag', 'event_driven', 'iv_skew', 'order_flow', 'latr_factor', 'inst_foreign_sector', 'sentiment', 'microstructure', 'gamma_squeeze', 'insider_buying', 'darkpool', 'darkpool_hft', 'earnings_tone_drift', 'tone_drift', 'hft']
    }

    # Inverse mapping from strategy to cluster name
    STRATEGY_TO_CLUSTER = {}
    for cluster_name, strats in CLUSTER_MAP.items():
        for s in strats:
            STRATEGY_TO_CLUSTER[s] = cluster_name

    # High-Risk Redundant Clusters per 2D Market Regime
    HIGH_RISK_CLUSTERS_PER_REGIME = {
        'SIDEWAYS_LOW_VOL': ['MOMENTUM'],
        'SIDEWAYS_HIGH_VOL': ['MOMENTUM', 'FLOW_MICRO'],
        'BULL_LOW_VOL': ['REVERSAL'],
        'BULL_HIGH_VOL': ['REVERSAL'],
        'BEAR_LOW_VOL': ['MOMENTUM'],
        'BEAR_HIGH_VOL': ['MOMENTUM'],
        # Fallbacks for 1D Regimes & Special State Aliases
        'SIDEWAYS': ['MOMENTUM'],
        'BULL': ['REVERSAL'],
        'BEAR': ['MOMENTUM'],
        'CRISIS': ['MOMENTUM', 'FLOW_MICRO', 'REVERSAL'],
        'HIGH_VOL': ['MOMENTUM', 'FLOW_MICRO'],
        '0': ['MOMENTUM'],
        '1': ['MOMENTUM'],
        '2': ['REVERSAL']
    }

    # Default Correlation Cutoffs theta(R) and Dampening Intensity lambda(R) per Regime
    DEFAULT_REGIME_PARAMS = {
        'SIDEWAYS_LOW_VOL': {'theta': 0.60, 'lambda': 1.20},
        'SIDEWAYS_HIGH_VOL': {'theta': 0.55, 'lambda': 1.50},
        'BULL_LOW_VOL': {'theta': 0.70, 'lambda': 0.80},
        'BULL_HIGH_VOL': {'theta': 0.65, 'lambda': 1.00},
        'BEAR_LOW_VOL': {'theta': 0.65, 'lambda': 1.00},
        'BEAR_HIGH_VOL': {'theta': 0.60, 'lambda': 1.40},
        'CRISIS': {'theta': 0.50, 'lambda': 2.00},
        'HIGH_VOL': {'theta': 0.55, 'lambda': 1.50},
    }

    def __init__(self, default_theta: float = 0.65, default_lambda: float = 1.0):
        self.default_theta = default_theta
        self.default_lambda = default_lambda

    def _get_regime_params(
        self,
        regime_label: str,
        tuned_params: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, float]:
        """Retrieves theta and lambda_penalty parameters for given regime label."""
        reg_str = str(regime_label).upper()

        # Check tuned_params override first
        if tuned_params and 'correlation_suppression' in tuned_params:
            supp_params = tuned_params['correlation_suppression']
            if reg_str in supp_params:
                theta = supp_params[reg_str].get('theta', self.default_theta)
                lam = supp_params[reg_str].get('lambda', self.default_lambda)
                return float(theta), float(lam)

        # Fallback to default regime map
        if reg_str in self.DEFAULT_REGIME_PARAMS:
            p = self.DEFAULT_REGIME_PARAMS[reg_str]
            return float(p['theta']), float(p['lambda'])

        return self.default_theta, self.default_lambda

    def _get_high_risk_clusters(self, regime_label: str) -> List[str]:
        """Returns list of high-risk redundant factor clusters for the given regime."""
        reg_str = str(regime_label).upper()
        if reg_str in self.HIGH_RISK_CLUSTERS_PER_REGIME:
            return self.HIGH_RISK_CLUSTERS_PER_REGIME[reg_str]

        for k, v in self.HIGH_RISK_CLUSTERS_PER_REGIME.items():
            if k in reg_str:
                return v

        return ['MOMENTUM']

    def compute_penalties(
        self,
        corr_matrix: pd.DataFrame,
        regime_label: str,
        theta: float = 0.65,
        lambda_penalty: float = 1.0,
        consensus_precision: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Computes strategy-level dampening penalty factor P_i(R) in [0, 1].

        Formula:
          E_ij = max(0, |rho_ij| - theta(R))
          c_ij = intra_cluster_mult (1.5) or inter_cluster_mult (0.5)
                 * regime_high_risk_mult (1.5 if i in high-risk cluster)
          P_i = 1 / sqrt(1 + lambda * sum_{j != i} c_ij * E_ij^2)
        """
        if corr_matrix is None or corr_matrix.empty:
            return {col: 1.0 for col in corr_matrix.columns} if corr_matrix is not None else {}

        strats = list(corr_matrix.columns)
        n = len(strats)
        high_risk_clusters = self._get_high_risk_clusters(regime_label)

        penalties = {}
        for i in range(n):
            strat_i = strats[i]
            cluster_i = self.STRATEGY_TO_CLUSTER.get(strat_i, 'OTHER')
            is_high_risk_i = cluster_i in high_risk_clusters

            weighted_excess_sq_sum = 0.0
            for j in range(n):
                if i == j:
                    continue
                strat_j = strats[j]
                cluster_j = self.STRATEGY_TO_CLUSTER.get(strat_j, 'OTHER')

                rho_ij = float(corr_matrix.iloc[i, j])
                excess = max(0.0, abs(rho_ij) - theta)
                if excess <= 0.0:
                    continue

                # Cluster relationship coefficient
                if cluster_i == cluster_j and cluster_i != 'OTHER':
                    c_base = 1.5  # Intra-cluster redundancy is punished more severely
                else:
                    c_base = 0.5  # Inter-cluster redundancy is punished moderately

                # High-risk regime multiplier
                if is_high_risk_i:
                    c_base *= 1.5

                weighted_excess_sq_sum += c_base * (excess ** 2)

            denom = np.sqrt(1.0 + lambda_penalty * weighted_excess_sq_sum)
            penalty_i = float(1.0 / denom)

            # Consensus Precision Relief: Prevent over-suppression when strategy has high precision
            if consensus_precision and strat_i in consensus_precision:
                prec = float(consensus_precision[strat_i])
                if prec > 0.55:
                    relief = min(0.60, (prec - 0.55) * 2.0)
                    penalty_i = penalty_i + (1.0 - penalty_i) * relief

            penalties[strat_i] = round(penalty_i, 6)

        return penalties

    def suppress_weights(
        self,
        base_weights: Dict[str, float],
        corr_matrix: pd.DataFrame,
        regime_label: str,
        theta: Optional[float] = None,
        lambda_penalty: Optional[float] = None,
        tuned_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Applies regime-specific correlation factor noise dampening penalties to base strategy weights.
        Returns renormalized suppressed strategy weight dictionary.
        """
        if not base_weights:
            return {}

        if corr_matrix is None or corr_matrix.empty:
            tot = sum(base_weights.values())
            return {k: v / tot for k, v in base_weights.items()} if tot > 0 else base_weights

        # Determine theta and lambda
        default_t, default_l = self._get_regime_params(regime_label, tuned_params=tuned_params)
        eff_theta = theta if theta is not None else default_t
        eff_lambda = lambda_penalty if lambda_penalty is not None else default_l

        penalties = self.compute_penalties(
            corr_matrix=corr_matrix,
            regime_label=regime_label,
            theta=eff_theta,
            lambda_penalty=eff_lambda
        )

        # Apply penalties to base weights
        adjusted_weights = {}
        for strat, base_w in base_weights.items():
            p_i = penalties.get(strat, 1.0)
            adjusted_weights[strat] = base_w * p_i

        tot_w = sum(adjusted_weights.values())
        if tot_w <= 0:
            logger.warning("Sum of suppressed weights <= 0; falling back to base weights.")
            tot_base = sum(base_weights.values())
            return {k: v / tot_base for k, v in base_weights.items()}

        final_weights = {k: v / tot_w for k, v in adjusted_weights.items()}
        return final_weights

    def get_suppression_report(
        self,
        base_weights: Dict[str, float],
        corr_matrix: pd.DataFrame,
        regime_label: str,
        theta: Optional[float] = None,
        lambda_penalty: Optional[float] = None,
        tuned_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Returns diagnostic dictionary detailing initial vs suppressed weights,
        dampening penalties P_i, active high-risk clusters, and cutoff settings.
        """
        eff_t, eff_l = self._get_regime_params(regime_label, tuned_params=tuned_params)
        if theta is not None:
            eff_t = theta
        if lambda_penalty is not None:
            eff_l = lambda_penalty

        penalties = self.compute_penalties(
            corr_matrix=corr_matrix,
            regime_label=regime_label,
            theta=eff_t,
            lambda_penalty=eff_l
        )
        suppressed_w = self.suppress_weights(
            base_weights=base_weights,
            corr_matrix=corr_matrix,
            regime_label=regime_label,
            theta=eff_t,
            lambda_penalty=eff_l,
            tuned_params=tuned_params
        )

        high_risk = self._get_high_risk_clusters(regime_label)

        return {
            'regime': str(regime_label),
            'theta': eff_t,
            'lambda_penalty': eff_l,
            'high_risk_clusters': high_risk,
            'base_weights': base_weights,
            'penalties': penalties,
            'suppressed_weights': suppressed_w
        }
