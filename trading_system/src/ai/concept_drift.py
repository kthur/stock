"""
src/ai/concept_drift.py
Concept Drift & Population Stability Index (PSI) Engine.

Calculates PSI across 27 strategy feature distributions:
  PSI = sum( (Actual_i - Expected_i) * ln(Actual_i / Expected_i) )

Thresholds:
  - PSI < 0.10: No significant drift. Model remains valid.
  - 0.10 <= PSI <= 0.25: Moderate drift. Warning logged.
  - PSI > 0.25: Critical Concept Drift detected -> Triggers automated re-training pipeline.
"""

import logging
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ConceptDriftDetector:
    """
    Population Stability Index (PSI) Concept Drift Detector.
    """

    def __init__(self, psi_threshold: float = 0.25, num_bins: int = 10):
        self.psi_threshold = psi_threshold
        self.num_bins = num_bins

    def compute_psi(
        self,
        expected: np.ndarray,
        actual: np.ndarray
    ) -> float:
        """
        Calculates Population Stability Index between expected (reference/training)
        and actual (current inference) feature distributions.
        """
        exp_arr = np.asarray(expected, dtype=np.float64)
        act_arr = np.asarray(actual, dtype=np.float64)

        exp_clean = exp_arr[~np.isnan(exp_arr)]
        act_clean = act_arr[~np.isnan(act_arr)]

        if len(exp_clean) < 20 or len(act_clean) < 20:
            return 0.0

        try:
            percentiles = np.linspace(0, 100, self.num_bins + 1)
            bins = np.unique(np.percentile(exp_clean, percentiles))
            if len(bins) < 2:
                bins = np.array([-np.inf, np.inf])
            else:
                bins[0] = -np.inf
                bins[-1] = np.inf

            exp_counts, _ = np.histogram(exp_clean, bins=bins)
            act_counts, _ = np.histogram(act_clean, bins=bins)

            exp_pct = exp_counts / float(len(exp_clean))
            act_pct = act_counts / float(len(act_clean))

            # Replace zeros with epsilon to avoid division by zero or log(0) and renormalize
            eps = 1e-4
            exp_pct = np.where(exp_pct == 0, eps, exp_pct)
            act_pct = np.where(act_pct == 0, eps, act_pct)
            exp_pct = exp_pct / exp_pct.sum()
            act_pct = act_pct / act_pct.sum()

            psi_val = float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))
            psi_clean = float(np.nan_to_num(psi_val, nan=0.0, posinf=0.0, neginf=0.0))
            return max(0.0, psi_clean)
        except Exception as e:
            logger.warning(f"PSI calculation failed: {e}")
            return 0.0

    def check_feature_drift(
        self,
        reference_df: pd.DataFrame,
        current_df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Checks PSI across 27 strategy features.
        Returns drift report with 'requires_retraining' boolean flag.
        """
        if reference_df.empty or current_df.empty:
            return {'requires_retraining': False, 'feature_psi': {}, 'max_psi': 0.0}

        target_cols = feature_cols if feature_cols else list(reference_df.select_dtypes(include=[np.number]).columns)

        feature_psi: Dict[str, float] = {}
        drifted_features: List[str] = []

        for col in target_cols:
            if col in reference_df.columns and col in current_df.columns:
                psi_val = self.compute_psi(reference_df[col].values, current_df[col].values)
                feature_psi[col] = psi_val
                if psi_val > self.psi_threshold:
                    drifted_features.append(col)

        max_psi = max(feature_psi.values()) if feature_psi else 0.0
        requires_retraining = bool(max_psi > self.psi_threshold or len(drifted_features) >= 3)

        if requires_retraining:
            logger.warning(f"[CONCEPT DRIFT DETECTED] Max PSI={max_psi:.4f} (> {self.psi_threshold}). Drifted features: {drifted_features}. Triggering automated model re-training!")

        return {
            'requires_retraining': requires_retraining,
            'max_psi': float(max_psi),
            'drifted_features': drifted_features,
            'feature_psi': feature_psi
        }
