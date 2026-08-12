"""
Feature Drift & Model Staleness Detector Module
Computes Population Stability Index (PSI) and Page-Hinkley test on model prediction residuals to detect concept drift.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class FeatureDriftDetector:
    """
    Detects distribution shifts in top model features (PSI) and concept drift in predictions (Page-Hinkley).
    """

    def __init__(self, psi_threshold: float = 0.25, page_hinkley_delta: float = 0.005, page_hinkley_lambda: float = 50.0):
        self.psi_threshold = psi_threshold
        self.ph_delta = page_hinkley_delta
        self.ph_lambda = page_hinkley_lambda
        
        # Page-Hinkley state
        self._ph_sum = 0.0
        self._ph_min = 0.0
        self._ph_n = 0

    @staticmethod
    def compute_psi(reference_dist: np.ndarray, target_dist: np.ndarray, num_bins: int = 10) -> float:
        """
        Calculates Population Stability Index (PSI) between reference (train) and target (inference) distributions.
        Rules of thumb:
        - PSI < 0.10: No significant change.
        - 0.10 <= PSI < 0.25: Moderate shift.
        - PSI >= 0.25: Significant distribution shift -> Trigger model retraining.
        """
        ref_clean = np.asarray(reference_dist, dtype=np.float64)
        ref_clean = ref_clean[~np.isnan(ref_clean)]
        tar_clean = np.asarray(target_dist, dtype=np.float64)
        tar_clean = tar_clean[~np.isnan(tar_clean)]

        if len(ref_clean) < 10 or len(tar_clean) < 10:
            return 0.0

        quantiles = np.linspace(0, 100, num_bins + 1)
        bins = np.percentile(ref_clean, quantiles)
        bins[0] -= 1e-5
        bins[-1] += 1e-5
        bins = np.unique(bins)
        if len(bins) < 2:
            return 0.0

        ref_counts, _ = np.histogram(ref_clean, bins=bins)
        tar_counts, _ = np.histogram(tar_clean, bins=bins)

        ref_pct = ref_counts / float(len(ref_clean)) + 1e-6
        tar_pct = tar_counts / float(len(tar_clean)) + 1e-6

        psi_val = np.sum((tar_pct - ref_pct) * np.log(tar_pct / ref_pct))
        return float(psi_val)

    def update_page_hinkley(self, error: float) -> bool:
        """
        Updates Page-Hinkley test with the latest prediction residual error.
        Returns True if concept drift is detected.
        """
        self._ph_n += 1
        mean_error = self._ph_sum / float(self._ph_n) if self._ph_n > 1 else error
        self._ph_sum += error
        
        # Cumulative sum of deviation
        cum_dev = (error - mean_error - self.ph_delta)
        self._ph_min = min(self._ph_min, cum_dev)
        
        ph_stat = cum_dev - self._ph_min
        if ph_stat > self.ph_lambda:
            logger.warning(f"🚨 [CONCEPT DRIFT] Page-Hinkley test triggered (stat={ph_stat:.2f} > threshold={self.ph_lambda})")
            # Reset detector state
            self._ph_sum = 0.0
            self._ph_min = 0.0
            self._ph_n = 0
            return True
        return False

    def check_feature_drift(
        self,
        ref_df: pd.DataFrame,
        target_df: pd.DataFrame,
        top_features: List[str]
    ) -> Dict[str, Any]:
        """
        Checks PSI for all specified top features and returns report.
        """
        drift_results = {}
        flagged_features = []

        for feat in top_features:
            if feat in ref_df.columns and feat in target_df.columns:
                psi = self.compute_psi(ref_df[feat].values, target_df[feat].values)
                drift_results[feat] = round(psi, 4)
                if psi >= self.psi_threshold:
                    flagged_features.append(feat)
                    logger.warning(f"⚠️ [FEATURE DRIFT] Feature '{feat}' PSI = {psi:.4f} (>= {self.psi_threshold})")

        requires_retrain = len(flagged_features) > 0
        return {
            "psi_scores": drift_results,
            "flagged_features": flagged_features,
            "requires_retrain": requires_retrain
        }
