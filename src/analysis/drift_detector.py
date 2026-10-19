# -*- coding: utf-8 -*-
"""
ConceptDriftDetector: Continuous Learning & Population Stability Index (PSI) / Wasserstein Distance Monitor.
Detects market regime shifts, feature distribution decay, and triggers automated model retraining.
"""

import logging
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd
from scipy.stats import wasserstein_distance

logger = logging.getLogger(__name__)


class ConceptDriftDetector:
    """
    Monitors Feature & Target Distribution Drift using PSI and Wasserstein Distance.
    """

    def __init__(self,
                 psi_moderate_threshold: float = 0.10,
                 psi_severe_threshold: float = 0.25,
                 num_bins: int = 10):
        self.psi_moderate_threshold = psi_moderate_threshold
        self.psi_severe_threshold = psi_severe_threshold
        self.num_bins = num_bins

    def calculate_psi(self,
                      reference: np.ndarray,
                      current: np.ndarray,
                      num_bins: Optional[int] = None) -> float:
        """
        Calculates Population Stability Index (PSI) between reference and current samples:
        PSI = sum((Actual% - Expected%) * ln(Actual% / Expected%))
        """
        ref_clean = reference[np.isfinite(reference)]
        cur_clean = current[np.isfinite(current)]

        if len(ref_clean) < 10 or len(cur_clean) < 10:
            return 0.0

        k_bins = num_bins or self.num_bins

        # Create quantiles on reference distribution
        percentiles = np.linspace(0, 100, k_bins + 1)
        bin_edges = np.percentile(ref_clean, percentiles)
        bin_edges = np.unique(bin_edges)

        if len(bin_edges) < 2:
            return 0.0

        bin_edges[0] = -np.inf
        bin_edges[-1] = np.inf

        # Bin counts
        ref_counts, _ = np.histogram(ref_clean, bins=bin_edges)
        cur_counts, _ = np.histogram(cur_clean, bins=bin_edges)

        # Convert to probabilities with Laplace smoothing
        ref_pct = (ref_counts + 1e-4) / (np.sum(ref_counts) + 1e-4 * len(ref_counts))
        cur_pct = (cur_counts + 1e-4) / (np.sum(cur_counts) + 1e-4 * len(cur_counts))

        # PSI sum
        psi_val = np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))
        return float(max(0.0, psi_val))

    def calculate_wasserstein(self,
                              reference: np.ndarray,
                              current: np.ndarray) -> float:
        """
        Calculates 1D Wasserstein Distance (Earth Mover's Distance).
        """
        ref_clean = reference[np.isfinite(reference)]
        cur_clean = current[np.isfinite(current)]

        if len(ref_clean) < 5 or len(cur_clean) < 5:
            return 0.0

        return float(wasserstein_distance(ref_clean, cur_clean))

    def evaluate_feature_drift(
        self,
        ref_df: pd.DataFrame,
        cur_df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluates PSI and Wasserstein drift across all specified numeric features.
        Returns a structured drift diagnosis report.
        """
        cols = feature_cols or [c for c in ref_df.columns if pd.api.types.is_numeric_dtype(ref_df[c])]
        drift_results: Dict[str, Dict[str, Any]] = {}
        severe_count = 0
        moderate_count = 0

        for col in cols:
            if col not in cur_df.columns:
                continue

            ref_vals = pd.to_numeric(ref_df[col], errors='coerce').dropna().values
            cur_vals = pd.to_numeric(cur_df[col], errors='coerce').dropna().values

            if len(ref_vals) < 10 or len(cur_vals) < 10:
                continue

            psi = self.calculate_psi(ref_vals, cur_vals)
            w_dist = self.calculate_wasserstein(ref_vals, cur_vals)

            if psi >= self.psi_severe_threshold:
                status = 'SEVERE_DRIFT'
                severe_count += 1
            elif psi >= self.psi_moderate_threshold:
                status = 'MODERATE_DRIFT'
                moderate_count += 1
            else:
                status = 'STABLE'

            drift_results[col] = {
                'psi': float(psi),
                'wasserstein_distance': float(w_dist),
                'status': status
            }

        # Overall recommendation
        if severe_count >= 2 or (severe_count + moderate_count) >= max(3, len(cols) // 3):
            recommendation = 'RETRAIN_RECOMMENDED'
        elif moderate_count >= 1:
            recommendation = 'MONITOR_CLOSELY'
        else:
            recommendation = 'SYSTEM_STABLE'

        return {
            'overall_status': recommendation,
            'severe_drift_count': severe_count,
            'moderate_drift_count': moderate_count,
            'total_features_evaluated': len(drift_results),
            'feature_details': drift_results
        }
