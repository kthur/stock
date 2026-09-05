import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union

logger = logging.getLogger(__name__)

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# Phase 6 Quint-Pillar Economic Decomposition Mapping (37 strategies across 5 disjoint canonical pillars)
class QuintPillarMap(dict):
    """
    5-Pillar Canonical Mapping supporting both short keys ('val', 'mom', 'flow', 'cat', 'net')
    and formal cluster labels ('VAL_QUAL', 'MOM_TREND', 'MICRO_FLOW', 'CORP_CAT', 'NETWORK_MACRO').
    """
    _ALIASES = {
        'VAL_QUAL': 'val',
        'MOM_TREND': 'mom',
        'MICRO_FLOW': 'flow',
        'CORP_CAT': 'cat',
        'NETWORK_MACRO': 'net',
    }

    def __getitem__(self, key: str) -> List[str]:
        canonical_key = self._ALIASES.get(str(key).upper(), key)
        return super().__getitem__(canonical_key)

    def get(self, key: str, default: Any = None) -> Any:
        canonical_key = self._ALIASES.get(str(key).upper(), key)
        return super().get(canonical_key, default)


QUINT_PILLAR_MAP = QuintPillarMap({
    'val': ['rim_valuation', 'valueup_catalyst', 'accruals_quality', 'arm_factor', 'factor_neutralized', 'regression'],
    'mom': ['surge', 'vcp_ml', 'trend_efficiency', 'sector_rotation', 'range_expansion', 'mq_factor', 'lead_lag', 'vcp_rule', 'lstm'],
    'flow': ['order_flow', 'inst_foreign_sector', 'darkpool', 'microstructure', 'overnight_gap', 'stat_arb', 'iv_skew', 'short_term_reversal', 'vol_target'],
    'cat': ['event_driven', 'sentiment', 'short_squeeze', 'gamma_squeeze', 'insider_buying', 'earnings_tone_drift'],
    'net': ['supply_chain', 'supply_chain_gnn', 'cross_asset_spillover', 'dual_correction', 'index_rebalance', 'card_factor', 'latr_factor']
})


def apply_quintic_hyperbolic_deadband(
    scores_centered: Union[pd.Series, np.ndarray],
    delta_noise: float = 0.045,
    delta_neg: Optional[float] = None,
    alpha_pos: float = 5.0,
    alpha_neg: Optional[float] = None,
    regime: Optional[Union[str, int]] = None
) -> Union[pd.Series, np.ndarray]:
    """
    Phase 7 Zenith (F48.2) & Phase 8 Sovereign (F52.2): Smooth C^infinity Hyperbolic Deadband:
        z_denoised = z * tanh((|z| / delta_eff(z))^alpha_eff(z))
    - With quintic exponent (alpha = 5.0, Phase 7): squashes >99.9% of near-zero noise (|z| <= 0.010)
      reducing noise leakage down to ~0.05%.
    - With septic exponent (alpha = 7.0, Phase 8): squashes >99.99% of near-zero noise (|z| <= 0.010)
      reducing noise leakage down to <0.003% (suppressing 99.997% of noise, a 20-fold reduction),
      while transmitting 100.0% of high conviction signals (|z| >= 0.150) with strict rank
      monotonicity (Spearman rho == 1.0000) and exact odd symmetry when unconditioned.
    """
    is_series = isinstance(scores_centered, pd.Series)
    z = scores_centered.values if is_series else np.asarray(scores_centered, dtype=np.float64)

    reg_str = str(regime).upper() if regime is not None else ''
    base_alpha = float(alpha_pos)
    if 'CRISIS' in reg_str:
        chi_bear = 1.40
        eff_alpha_neg = base_alpha if alpha_neg is None else float(alpha_neg)
        eff_alpha_pos = base_alpha
    elif 'BEAR_HIGH_VOL' in reg_str or ('BEAR' in reg_str and 'HIGH_VOL' in reg_str):
        chi_bear = 1.35
        eff_alpha_neg = base_alpha if alpha_neg is None else float(alpha_neg)
        eff_alpha_pos = base_alpha
    elif 'BEAR_LOW_VOL' in reg_str or reg_str == '0' or 'BEAR' in reg_str:
        chi_bear = 1.20
        eff_alpha_neg = base_alpha if alpha_neg is None else float(alpha_neg)
        eff_alpha_pos = base_alpha
    elif 'SIDEWAYS_HIGH_VOL' in reg_str:
        chi_bear = 1.15
        eff_alpha_neg = base_alpha if alpha_neg is None else float(alpha_neg)
        eff_alpha_pos = base_alpha
    else:
        chi_bear = 1.00
        eff_alpha_neg = base_alpha if alpha_neg is None else float(alpha_neg)
        eff_alpha_pos = base_alpha

    safe_delta_pos = max(1e-6, float(delta_noise))
    safe_delta_neg = max(1e-6, float(delta_neg)) if delta_neg is not None else (safe_delta_pos * chi_bear)

    is_neg = (z < 0.0)
    delta_eff = np.where(is_neg, safe_delta_neg, safe_delta_pos)
    alpha_eff = np.where(is_neg, eff_alpha_neg, eff_alpha_pos)

    abs_z = np.abs(z)
    ratio = np.clip(abs_z / delta_eff, 0.0, 50.0)
    arg = np.clip(np.power(ratio, alpha_eff), 0.0, 50.0)
    denoised = z * np.tanh(arg)

    if is_series:
        return pd.Series(denoised, index=scores_centered.index)
    return denoised


def apply_asymmetric_wavelet_deadband(
    scores_centered: Union[pd.Series, np.ndarray],
    delta_noise: float = 0.045,
    delta_neg: Optional[float] = None,
    alpha_pos: float = 7.0,
    alpha_neg: Optional[float] = None,
    regime: Optional[Union[str, int]] = None
) -> Union[pd.Series, np.ndarray]:
    """
    Phase 8 Sovereign (F52.2): Asymmetric Septic Wavelet Noise Deadband:
        z_denoised = z * tanh((|z| / delta_eff(z))^7)
    With septic exponent (alpha = 7.0), suppresses 99.997% of near-zero noise (|z| <= 0.010)
    reducing noise leakage down to < 0.003% (a 20-fold reduction vs Phase 7 quintic deadband),
    while transmitting 100.000% of high conviction signals (|z| >= 0.150) with strict rank
    monotonicity (Spearman rho == 1.0000) and exact odd symmetry when unconditioned.
    """
    return apply_quintic_hyperbolic_deadband(
        scores_centered=scores_centered,
        delta_noise=delta_noise,
        delta_neg=delta_neg,
        alpha_pos=alpha_pos,
        alpha_neg=alpha_neg,
        regime=regime
    )



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

    # Phase 6 Quint-Pillar Economic Decomposition Mapping (37 strategies)
    QUINT_PILLAR_MAP = QUINT_PILLAR_MAP

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

    @staticmethod
    def calibrate_cutoff(
        theta_0: float,
        n_samples: Optional[int],
        z_score: float = 1.645,
        min_theta: float = 0.35,
        max_theta: float = 0.85
    ) -> float:
        """
        Statistically calibrated correlation suppression cutoff:
            theta(R, N) = clip( theta_0(R) + z_{0.95} / sqrt(max(N - 3, 1)), min_theta, max_theta )
        Under Fisher's z-transformation, asymptotic standard error SE(r) ~ 1/sqrt(N-3).
        Guarantees that collinearity suppression operates only when empirical correlation
        statistically significantly exceeds the base threshold at the 95% one-sided confidence level.
        """
        if n_samples is None or n_samples <= 3:
            return float(theta_0)
        calibrated = float(theta_0) + float(z_score) / np.sqrt(float(max(n_samples - 3, 1)))
        return float(np.clip(calibrated, min_theta, max_theta))

    def _get_regime_params(
        self,
        regime_label: str,
        tuned_params: Optional[Dict[str, Any]] = None,
        n_samples: Optional[int] = None
    ) -> Tuple[float, float]:
        """Retrieves theta and lambda_penalty parameters for given regime label,
        applying sample-size statistical calibration theta(R, N) = theta_0(R) + 1.645 / sqrt(N-3)."""
        reg_str = str(regime_label).upper()

        theta_0 = self.default_theta
        lam = self.default_lambda

        # Check tuned_params override first
        if tuned_params and 'correlation_suppression' in tuned_params:
            supp_params = tuned_params['correlation_suppression']
            if reg_str in supp_params:
                theta_0 = float(supp_params[reg_str].get('theta', self.default_theta))
                lam = float(supp_params[reg_str].get('lambda', self.default_lambda))
                eff_theta = self.calibrate_cutoff(theta_0, n_samples)
                return float(eff_theta), float(lam)

        # Fallback to default regime map
        if reg_str in self.DEFAULT_REGIME_PARAMS:
            p = self.DEFAULT_REGIME_PARAMS[reg_str]
            theta_0 = float(p['theta'])
            lam = float(p['lambda'])
            eff_theta = self.calibrate_cutoff(theta_0, n_samples)
            return float(eff_theta), float(lam)

        eff_theta = self.calibrate_cutoff(theta_0, n_samples)
        return float(eff_theta), float(lam)

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
        cluster_sharpes: Optional[Dict[str, float]] = None,
        n_samples: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        Computes dynamic suppression penalty multiplier p_i for each strategy.
        p_i = min( 1 / sqrt(1 + lambda * sum(c_ij * excess_ij^2)), vif_damping )
        """
        eff_n = n_samples
        if eff_n is None and hasattr(corr_matrix, 'attrs') and 'n_samples' in corr_matrix.attrs:
            eff_n = corr_matrix.attrs.get('n_samples')

        eff_theta, eff_lambda = self._get_regime_params(regime_label, n_samples=eff_n)
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
        use_entropy_allocation: Optional[bool] = None,
        vif_dict: Optional[Dict[str, float]] = None,
        consensus_precision: Optional[Dict[str, float]] = None,
        cluster_sharpes: Optional[Dict[str, float]] = None,
        n_samples: Optional[int] = None,
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

        eff_n = n_samples
        if eff_n is None and hasattr(corr_matrix, 'attrs') and 'n_samples' in corr_matrix.attrs:
            eff_n = corr_matrix.attrs.get('n_samples')

        # Determine theta and lambda
        default_t, default_l = self._get_regime_params(regime_label, tuned_params=tuned_params, n_samples=eff_n)
        eff_theta = theta if theta is not None else default_t
        eff_lambda = lambda_penalty if lambda_penalty is not None else default_l

        # Enable entropy allocation if explicitly True, or auto-enable when N >= 10 and not explicitly False
        eff_use_entropy = use_entropy_allocation
        if eff_use_entropy is None:
            eff_use_entropy = (eff_n is not None and np.isfinite(eff_n) and eff_n >= 10)

        if eff_use_entropy:
            try:
                strats = [s for s in base_weights.keys() if s in corr_matrix.columns]
                missing_strats = [s for s in base_weights.keys() if s not in corr_matrix.columns]
                if len(strats) >= 2:
                    penalties = self.compute_penalties(
                        corr_matrix=corr_matrix,
                        regime_label=regime_label,
                        theta=eff_theta,
                        lambda_penalty=eff_lambda,
                        consensus_precision=consensus_precision,
                        vif_dict=vif_dict,
                        cluster_sharpes=cluster_sharpes,
                        n_samples=eff_n,
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
                    if not missing_strats:
                        return {s: float(w) for s, w in zip(strats, opt_w)}
                    else:
                        # Proportionately combine active entropy-optimized weights with missing strategies
                        sum_present_base = sum(base_weights[s] for s in strats)
                        sum_missing_base = sum(base_weights[s] for s in missing_strats)
                        total_base = sum_present_base + sum_missing_base
                        p_share = sum_present_base / total_base if total_base > 0 else 1.0
                        m_share = sum_missing_base / total_base if total_base > 0 else 0.0

                        res = {}
                        for s, w in zip(strats, opt_w):
                            res[s] = float(w * p_share)
                        for s in missing_strats:
                            m_w = base_weights[s] * penalties.get(s, 1.0)
                            res[s] = float((m_w / max(sum_missing_base, 1e-8)) * m_share)

                        tot_res = sum(res.values())
                        return {k: float(v / tot_res) for k, v in res.items()} if tot_res > 0 else res
            except Exception as _ent_e:
                logger.debug(f"[ENTROPY ALLOCATION] Fallback to standard penalty model: {_ent_e}")

        penalties = self.compute_penalties(
            corr_matrix=corr_matrix,
            regime_label=regime_label,
            theta=eff_theta,
            lambda_penalty=eff_lambda,
            consensus_precision=consensus_precision,
            vif_dict=vif_dict,
            cluster_sharpes=cluster_sharpes,
            n_samples=eff_n,
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
        tuned_params: Optional[Dict[str, Any]] = None,
        n_samples: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Returns diagnostic dictionary detailing initial vs suppressed weights,
        dampening penalties P_i, active high-risk clusters, and cutoff settings.
        """
        eff_n = n_samples
        if eff_n is None and hasattr(corr_matrix, 'attrs') and 'n_samples' in corr_matrix.attrs:
            eff_n = corr_matrix.attrs.get('n_samples')

        eff_t, eff_l = self._get_regime_params(regime_label, tuned_params=tuned_params, n_samples=eff_n)
        if theta is not None:
            eff_t = theta
        if lambda_penalty is not None:
            eff_l = lambda_penalty

        penalties = self.compute_penalties(
            corr_matrix=corr_matrix,
            regime_label=regime_label,
            theta=eff_t,
            lambda_penalty=eff_l,
            n_samples=eff_n,
        )
        suppressed_w = self.suppress_weights(
            base_weights=base_weights,
            corr_matrix=corr_matrix,
            regime_label=regime_label,
            theta=eff_t,
            lambda_penalty=eff_l,
            tuned_params=tuned_params,
            n_samples=eff_n,
        )

        high_risk = self._get_high_risk_clusters(regime_label)

        return {
            'regime': str(regime_label),
            'theta': eff_t,
            'lambda_penalty': eff_l,
            'n_samples': eff_n,
            'high_risk_clusters': high_risk,
            'base_weights': base_weights,
            'penalties': penalties,
            'suppressed_weights': suppressed_w
        }

