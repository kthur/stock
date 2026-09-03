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


def solve_single_stage_entropy_allocation(
    R: np.ndarray,
    w0: np.ndarray,
    tau_entropy: float = 0.05,
    gamma_anchor: float = 1.0,
    w_min: float = 0.005,
    max_iter: int = 150
) -> np.ndarray:
    """
    Solves Single-Stage Convex Information-Entropy Redundancy Allocation Program on Simplex Delta^(K-1):
        min_w  [ 0.5 * w^T R w - tau_entropy * sum(ln(w_i)) + gamma_anchor * ||w - w0||^2 ]
        subject to w_i >= w_min, sum(w_i) = 1.0.
    Directly penalizes multicollinear factor redundancy while ensuring strategy diversification
    and anchoring to macro regime weights w0 without triple-penalty alpha destruction.
    """
    K = len(w0)
    if K <= 1:
        return np.ones(K) if K == 1 else np.array([])

    # Clean correlation matrix and ensure symmetry
    R_sym = (R + R.T) * 0.5
    np.fill_diagonal(R_sym, 1.0)
    w = np.copy(w0).astype(np.float64)
    w = np.maximum(w, w_min)
    w_s = np.sum(w)
    w = w / w_s if w_s > 1e-12 else np.ones(K) / K

    lr = 0.02
    for it in range(max_iter):
        lr_t = lr / (1.0 + 0.05 * it)
        grad = np.dot(R_sym, w) - (tau_entropy / np.maximum(w, 1e-6)) + 2.0 * gamma_anchor * (w - w0)
        w_new = w - lr_t * grad
        w_new = np.maximum(w_new, w_min)
        w_new_s = np.sum(w_new)
        w_new = w_new / w_new_s if w_new_s > 1e-12 else np.ones(K) / K

        if np.max(np.abs(w_new - w)) < 1e-6:
            break
        w = w_new

    w_clean = np.where(np.isfinite(w), w, w_min)
    w_clean = np.maximum(w_clean, w_min)
    w_clean_s = np.sum(w_clean)
    w_clean = w_clean / w_clean_s if w_clean_s > 1e-12 else np.ones(K) / K
    return np.asarray(w_clean, dtype=np.float64)


class RegimeFactorSuppressionEngine:
    """
    Implements 2D regime-based factor noise suppression penalties and Single-Stage
    Entropy Redundancy Allocation targeting multicollinear strategy redundancy.

    Penalty Formulation:
      E_ij = max(0, |rho_ij| - theta(R))
      c_ij(R): Cluster relationship multiplier (higher for intra-cluster & high-risk regime target clusters)
      P_i(R) = 1 / sqrt(1 + lambda(R) * sum_{j != i} c_ij(R) * E_ij^2)
      w_i_suppressed = base_w_i * P_i(R) / sum_k (base_w_k * P_k(R))
    """

    CLUSTER_MAP = {
        'CORE_AI': ['regression', 'lstm', 'vol_target'],
        'MOMENTUM': ['surge', 'vcp_ml', 'sector_rotation', 'arm_factor', 'supply_chain', 'short_squeeze', 'trend_efficiency', 'supply_chain_gnn', 'cross_asset_spillover', 'range_expansion_breakout', 'range_expansion', 'intraday_breakout'],
        'VALUATION': ['rim_valuation', 'rim', 'mq_factor', 'factor_neutralized', 'accruals_quality', 'valueup_catalyst', 'value_up'],
        'REVERSAL': ['stat_arb', 'vcp_rule', 'vcp', 'vcp_patterns', 'short_term_reversal', 'card_factor', 'dual_correction', 'overnight_gap_reversal', 'overnight_gap'],
        'FLOW_MICRO': ['lead_lag', 'event_driven', 'iv_skew', 'order_flow', 'latr_factor', 'inst_foreign_sector', 'sentiment', 'microstructure', 'gamma_squeeze', 'insider_buying', 'darkpool', 'darkpool_hft', 'earnings_tone_drift', 'tone_drift', 'hft', 'index_rebalance', 'index_rebalance_structural_flow']
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

    def _get_high_risk_clusters(
        self,
        regime_label: str,
        cluster_sharpes: Optional[Dict[str, float]] = None
    ) -> List[str]:
        """Returns list of high-risk redundant factor clusters for the given regime.
        If cluster_sharpes is provided, only clusters with negative performance (Sharpe < -0.20)
        are actively suppressed, preserving profitable cross-sectional signals."""
        reg_str = str(regime_label).upper()
        base_clusters = self.HIGH_RISK_CLUSTERS_PER_REGIME.get(reg_str, None)
        if base_clusters is None:
            for k, v in self.HIGH_RISK_CLUSTERS_PER_REGIME.items():
                if k in reg_str:
                    base_clusters = v
                    break
        if base_clusters is None:
            base_clusters = ['MOMENTUM']

        if cluster_sharpes:
            active_clusters = [c for c in base_clusters if float(cluster_sharpes.get(c, -0.5)) < -0.20]
            return active_clusters
        return base_clusters

    def compute_penalties(
        self,
        corr_matrix: pd.DataFrame,
        regime_label: str,
        theta: Optional[float] = None,
        lambda_penalty: Optional[float] = None,
        consensus_precision: Optional[Dict[str, float]] = None,
        vif_dict: Optional[Dict[str, float]] = None,
        cluster_sharpes: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Computes dynamic suppression penalty multiplier p_i for each strategy.
        p_i = min( 1 / sqrt(1 + lambda * sum(c_ij * excess_ij^2)), vif_damping )
        """
        eff_theta, eff_lambda = self._get_regime_params(regime_label)
        theta_val = theta if theta is not None else eff_theta
        lambda_val = lambda_penalty if lambda_penalty is not None else eff_lambda

        high_risk_clusters = self._get_high_risk_clusters(regime_label, cluster_sharpes=cluster_sharpes)
        strats = list(corr_matrix.columns)
        penalties = {}

        for strat_i in strats:
            cluster_i = self.STRATEGY_TO_CLUSTER.get(strat_i, 'OTHER')
            is_high_risk_i = cluster_i in high_risk_clusters

            weighted_excess_sq_sum = 0.0
            for strat_j in strats:
                if strat_i == strat_j:
                    continue

                cluster_j = self.STRATEGY_TO_CLUSTER.get(strat_j, 'OTHER')
                is_same_cluster = (cluster_i == cluster_j and cluster_i != 'OTHER')

                rho_ij = float(corr_matrix.loc[strat_i, strat_j])
                excess = max(0.0, abs(rho_ij) - theta_val)

                if excess <= 0.0:
                    continue

                # Multiplier c_ij for intra-cluster vs inter-cluster correlation
                if is_same_cluster:
                    c_base = 2.0 if is_high_risk_i else 1.5
                else:
                    c_base = 1.0

                # Asymmetric protection: if strategy i is superior to strategy j, dampen i's penalty from j
                if consensus_precision:
                    prec_i = float(consensus_precision.get(strat_i, 0.50))
                    prec_j = float(consensus_precision.get(strat_j, 0.50))
                    if prec_i > prec_j:
                        asym_scale = max(0.20, 1.0 - (prec_i - prec_j) * 2.0)
                        c_base *= asym_scale

                weighted_excess_sq_sum += c_base * (excess ** 2)

            denom = np.sqrt(1.0 + lambda_val * weighted_excess_sq_sum)
            corr_penalty = float(1.0 / denom)

            # Direct VIF multi-way collinearity damping (V7-05: relaxed threshold to 10.0 for 31-strategy ensemble)
            vif_damping = 1.0
            if vif_dict and strat_i in vif_dict:
                vif_val = float(vif_dict[strat_i])
                if vif_val > 10.0:
                    vif_damping = min(1.0, np.sqrt(10.0 / max(vif_val, 1e-6)))

            # Prevent double-penalizing: apply the stricter of correlation excess or VIF damping
            penalty_i = min(corr_penalty, vif_damping)

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
        tuned_params: Optional[Dict[str, Any]] = None,
        use_entropy_allocation: bool = False,
        vif_dict: Optional[Dict[str, float]] = None,
        consensus_precision: Optional[Dict[str, float]] = None,
        cluster_sharpes: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Applies regime-specific correlation factor noise dampening penalties to base strategy weights.
        Returns renormalized suppressed strategy weight dictionary.
        """
        if not base_weights:
            return {}

        if corr_matrix is None or corr_matrix.empty:
            tot = sum(base_weights.values())
            return {k: v / tot for k, v in base_weights.items()} if tot > 0 else {}

        # Determine theta and lambda
        default_t, default_l = self._get_regime_params(regime_label, tuned_params=tuned_params)
        eff_theta = theta if theta is not None else default_t
        eff_lambda = lambda_penalty if lambda_penalty is not None else default_l

        if use_entropy_allocation:
            try:
                strats = [s for s in base_weights.keys() if s in corr_matrix.columns]
                missing_strats = [s for s in base_weights.keys() if s not in corr_matrix.columns]
                if len(strats) >= 2 and not missing_strats:
                    penalties = self.compute_penalties(
                        corr_matrix=corr_matrix,
                        regime_label=regime_label,
                        theta=eff_theta,
                        lambda_penalty=eff_lambda,
                        consensus_precision=consensus_precision,
                        vif_dict=vif_dict,
                        cluster_sharpes=cluster_sharpes
                    )
                    w0_vec = np.array([float(base_weights[s] * penalties.get(s, 1.0)) for s in strats], dtype=np.float64)
                    w0_sum = float(np.sum(w0_vec))
                    w0_vec = w0_vec / max(w0_sum, 1e-8)
                    R_sub = corr_matrix.loc[strats, strats].to_numpy(dtype=np.float64)

                    opt_w = solve_single_stage_entropy_allocation(
                        R=R_sub,
                        w0=w0_vec,
                        tau_entropy=0.05,
                        gamma_anchor=1.0 / max(0.1, eff_lambda),
                        w_min=0.005
                    )
                    return {s: float(w) for s, w in zip(strats, opt_w)}
            except Exception as _ent_e:
                logger.debug(f"[ENTROPY ALLOCATION] Fallback to standard penalty model: {_ent_e}")

        penalties = self.compute_penalties(
            corr_matrix=corr_matrix,
            regime_label=regime_label,
            theta=eff_theta,
            lambda_penalty=eff_lambda,
            consensus_precision=consensus_precision,
            vif_dict=vif_dict,
            cluster_sharpes=cluster_sharpes
        )

        # Apply penalties to base weights
        adjusted_weights = {}
        for strat, base_w in base_weights.items():
            p_i = penalties.get(strat, 1.0)
            adjusted_weights[strat] = base_w * p_i

        tot_w = sum(adjusted_weights.values())
        if tot_w <= 0 or not np.isfinite(tot_w):
            logger.warning("Sum of suppressed weights <= 0; falling back to base weights.")
            tot_base = sum(base_weights.values())
            return {k: float(v / tot_base) if (tot_base > 0 and np.isfinite(v)) else (1.0 / len(base_weights)) for k, v in base_weights.items()}

        final_weights = {k: float(v / tot_w) if np.isfinite(v / tot_w) else float(base_weights.get(k, 1.0 / len(adjusted_weights))) for k, v in adjusted_weights.items()}
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
