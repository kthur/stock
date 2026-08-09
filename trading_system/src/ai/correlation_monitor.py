import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.

ALL_31_STRATEGIES = [
    'regression', 'surge', 'lead_lag', 'vcp_rule', 'vcp_ml',
    'lstm', 'stat_arb', 'sector_rotation', 'rim_valuation',
    'event_driven', 'mq_factor', 'iv_skew', 'order_flow',
    'short_term_reversal', 'arm_factor', 'card_factor', 'latr_factor',
    'inst_foreign_sector', 'supply_chain', 'sentiment', 'factor_neutralized',
    'vol_target', 'microstructure', 'accruals_quality', 'short_squeeze',
    'valueup_catalyst', 'trend_efficiency', 'gamma_squeeze', 'insider_buying',
    'darkpool', 'earnings_tone_drift'
]
ALL_18_STRATEGIES = ALL_31_STRATEGIES
ALL_17_STRATEGIES = ALL_31_STRATEGIES

STRATEGY_SCORE_COL_MAP = {
    'regression': 'reg_score',
    'surge': 'surge_score',
    'lead_lag': 'll_score',
    'vcp_rule': 'vcp_rule_score',
    'vcp_ml': 'vcp_ml_score',
    'lstm': 'lstm_score',
    'stat_arb': 'stat_arb_score',
    'sector_rotation': 'sector_score',
    'rim_valuation': 'rim_score',
    'event_driven': 'event_score',
    'mq_factor': 'mq_score',
    'iv_skew': 'iv_skew_score',
    'order_flow': 'order_flow_score',
    'short_term_reversal': 'reversal_score',
    'arm_factor': 'arm_score',
    'card_factor': 'card_score',
    'latr_factor': 'latr_score',
    'inst_foreign_sector': 'inst_foreign_sector_score',
    'supply_chain': 'supply_chain_score',
    'sentiment': 'sentiment_score',
    'factor_neutralized': 'factor_neutralized_score',
    'vol_target': 'vol_target_score',
    'microstructure': 'microstructure_score',
    'accruals_quality': 'accruals_quality_score',
    'short_squeeze': 'short_squeeze_score',
    'valueup_catalyst': 'valueup_catalyst_score',
    'trend_efficiency': 'trend_efficiency_score',
    'gamma_squeeze': 'gamma_squeeze_score',
    'insider_buying': 'insider_buying_score',
    'darkpool': 'darkpool_score',
    'earnings_tone_drift': 'earnings_tone_drift_score'
}

# Inverse mapping from score column name to strategy name
SCORE_COL_STRATEGY_MAP = {v: k for k, v in STRATEGY_SCORE_COL_MAP.items()}


class StrategyCorrelationMonitor:
    """
    Computes daily cross-sectional Spearman rank correlation matrix R (17x17),
    maintains rolling correlation smoothing, computes Variance Inflation Factor (VIF)
    per strategy, and calculates Effective Strategy Count (N_eff).
    """

    def __init__(self, window: int = 20, alpha_corr: float = 0.15, strategies: Optional[List[str]] = None):
        self.window = window
        self.alpha_corr = alpha_corr
        self.strategies = strategies if strategies is not None else ALL_17_STRATEGIES
        self.rolling_corr_matrix: Optional[pd.DataFrame] = None
        self._init_default_matrix()

    def _init_default_matrix(self) -> None:
        """Initializes default identity correlation matrix (uncorrelated baseline)."""
        n = len(self.strategies)
        mat = np.eye(n, dtype=float)
        self.rolling_corr_matrix = pd.DataFrame(mat, index=self.strategies, columns=self.strategies)

    def extract_score_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extracts strategy prediction scores from input DataFrame, mapping score columns or
        strategy name columns into a normalized DataFrame with strategy names as columns.
        """
        scores_dict = {}
        for strat in self.strategies:
            score_col = STRATEGY_SCORE_COL_MAP.get(strat, f"{strat}_score")
            if score_col in df.columns:
                scores_dict[strat] = df[score_col]
            elif strat in df.columns:
                scores_dict[strat] = df[strat]
            else:
                scores_dict[strat] = pd.Series(np.nan, index=df.index)

        return pd.DataFrame(scores_dict, index=df.index)

    def update_correlation(self, strategy_scores_df: pd.DataFrame) -> pd.DataFrame:
        """
        Computes cross-sectional Spearman rank correlation matrix across all active strategies
        for the given trading day/batch and applies rolling EMA smoothing.

        Formula:
          R_ij,t = SpearmanRankCorr(S_i, S_j)
          R_bar_t = alpha_corr * R_t + (1 - alpha_corr) * R_bar_{t-1}
        """
        score_df = self.extract_score_dataframe(strategy_scores_df)

        # Drop rows where all strategy scores are NaN
        valid_df = score_df.dropna(how='all')

        if len(valid_df) < 3:
            logger.warning("Insufficient data points (<3) to compute Spearman rank correlation matrix; keeping existing rolling matrix.")
            return self.rolling_corr_matrix

        # Compute cross-sectional Spearman rank correlation
        current_corr = valid_df.corr(method='spearman')

        # Ensure matrix contains all strategies
        for s in self.strategies:
            if s not in current_corr.columns:
                current_corr[s] = 0.0
                current_corr.loc[s] = 0.0
                current_corr.loc[s, s] = 1.0

        current_corr = current_corr.reindex(index=self.strategies, columns=self.strategies).fillna(0.0)

        # Fix diagonal to 1.0 and clip off-diagonals
        np.fill_diagonal(current_corr.values, 1.0)
        current_corr = current_corr.clip(lower=-1.0, upper=1.0)

        # Symmetry enforcement R = (R + R^T) / 2
        sym_vals = (current_corr.values + current_corr.values.T) / 2.0
        np.fill_diagonal(sym_vals, 1.0)
        current_corr = pd.DataFrame(sym_vals, index=self.strategies, columns=self.strategies)

        # Exponential moving average smoothing
        if self.rolling_corr_matrix is None or (self.rolling_corr_matrix.values == np.eye(len(self.strategies))).all():
            self.rolling_corr_matrix = current_corr
        else:
            smoothed = self.alpha_corr * current_corr.values + (1.0 - self.alpha_corr) * self.rolling_corr_matrix.values
            smoothed = (smoothed + smoothed.T) / 2.0
            np.fill_diagonal(smoothed, 1.0)
            self.rolling_corr_matrix = pd.DataFrame(smoothed, index=self.strategies, columns=self.strategies).clip(lower=-1.0, upper=1.0)

        return self.rolling_corr_matrix

    def compute_vif(self, corr_matrix: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """
        Computes Variance Inflation Factor (VIF) for each strategy from correlation matrix R.
        Formula: VIF_i = (R^-1)_ii

        Handles near-singular matrices using pseudo-inverse or ridge regularization.
        """
        mat_df = corr_matrix if corr_matrix is not None else self.rolling_corr_matrix
        if mat_df is None or mat_df.empty:
            return {s: 1.0 for s in self.strategies}

        strats = list(mat_df.columns)
        R = mat_df.values

        # Ridge regularized inverse to ensure numerical stability
        ridge = 1e-6
        R_reg = R + ridge * np.eye(len(R))
        try:
            inv_R = np.linalg.inv(R_reg)
        except np.linalg.LinAlgError:
            inv_R = np.linalg.pinv(R_reg)

        vif_diag = np.diag(inv_R)
        vif_dict = {}
        for s, vif in zip(strats, vif_diag):
            # VIF cannot be less than 1.0
            vif_val = float(np.clip(vif, 1.0, 100.0))
            vif_dict[s] = round(vif_val, 4)

        return vif_dict

    def compute_effective_strategy_count(
        self,
        weights: Optional[Dict[str, float]] = None,
        corr_matrix: Optional[pd.DataFrame] = None
    ) -> float:
        """
        Computes Effective Strategy Count N_eff of the strategy ensemble.
        Formula: N_eff = (sum w_i)^2 / sum_i sum_j (w_i * w_j * rho_ij)
        """
        mat_df = corr_matrix if corr_matrix is not None else self.rolling_corr_matrix
        if mat_df is None or mat_df.empty:
            return float(len(self.strategies))

        strats = list(mat_df.columns)
        n = len(strats)

        if weights is None:
            w_vec = np.ones(n) / float(n)
        else:
            w_vec = np.array([weights.get(s, 1.0 / float(n)) for s in strats], dtype=float)

        w_sum = np.sum(w_vec)
        if w_sum <= 0:
            return 1.0

        # W_i * W_j * Rho_ij denominator
        R = mat_df.values
        denom = np.dot(w_vec, np.dot(R, w_vec))
        if denom <= 1e-8:
            denom = 1e-8

        n_eff = float((w_sum ** 2) / denom)
        return float(np.clip(n_eff, 1.0, float(n)))

    def get_top_collinear_pairs(
        self,
        threshold: float = 0.50,
        corr_matrix: Optional[pd.DataFrame] = None
    ) -> List[Tuple[str, str, float]]:
        """
        Extracts strategy pairs with correlation magnitude |rho_ij| >= threshold.
        Returns list of (strat_i, strat_j, corr_value) sorted descending by absolute correlation.
        """
        mat_df = corr_matrix if corr_matrix is not None else self.rolling_corr_matrix
        if mat_df is None or mat_df.empty:
            return []

        strats = list(mat_df.columns)
        pairs = []
        n = len(strats)
        for i in range(n):
            for j in range(i + 1, n):
                rho = float(mat_df.iloc[i, j])
                if abs(rho) >= threshold:
                    pairs.append((strats[i], strats[j], round(rho, 4)))

        pairs.sort(key=lambda x: abs(x[2]), reverse=True)
        return pairs
