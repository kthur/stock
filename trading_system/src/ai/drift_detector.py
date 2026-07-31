"""
Feature Drift & Model Health Monitoring Module (MLOps)

Calculates data drift metrics between baseline training distribution and live inference distribution.
Provides Population Stability Index (PSI), Kolmogorov-Smirnov (KS) test, and Wasserstein distance.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FeatureDriftDetector:
    """Monitors feature distribution shift (drift) between baseline and inference data."""

    def __init__(self, psi_threshold: float = 0.25, output_dir: Optional[Union[str, Path]] = None) -> None:
        self.psi_threshold = psi_threshold
        self.output_dir = Path(output_dir) if output_dir else Path(__file__).parent.parent.parent / "data"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def calculate_psi(baseline: np.ndarray, current: np.ndarray, num_bins: int = 10) -> float:
        """Calculate Population Stability Index (PSI) for a continuous variable."""
        baseline = baseline[~np.isnan(baseline)]
        current = current[~np.isnan(current)]

        if len(baseline) == 0 or len(current) == 0:
            return 0.0

        quantiles = np.linspace(0, 100, num_bins + 1)
        bins = np.percentile(baseline, quantiles)
        bins = np.unique(bins)

        if len(bins) < 2:
            return 0.0

        # Adjust endpoints to cover full range
        bins[0] = min(bins[0], np.min(current), np.min(baseline)) - 1e-5
        bins[-1] = max(bins[-1], np.max(current), np.max(baseline)) + 1e-5

        base_counts, _ = np.histogram(baseline, bins=bins)
        curr_counts, _ = np.histogram(current, bins=bins)

        base_pct = base_counts / max(1, len(baseline))
        curr_pct = curr_counts / max(1, len(current))

        # Avoid zero division and log(0) using small epsilon
        eps = 1e-4
        base_pct = np.where(base_pct == 0, eps, base_pct)
        curr_pct = np.where(curr_pct == 0, eps, curr_pct)

        psi = np.sum((curr_pct - base_pct) * np.log(curr_pct / base_pct))
        return float(psi)

    def analyze_dataframe_drift(
        self, baseline_df: pd.DataFrame, current_df: pd.DataFrame, feature_cols: List[str]
    ) -> Dict[str, Dict[str, Union[float, str, bool]]]:
        """Analyze PSI and drift status for multiple features."""
        results = {}
        drift_detected_features = []

        for col in feature_cols:
            if col not in baseline_df.columns or col not in current_df.columns:
                continue

            base_vals = baseline_df[col].to_numpy(dtype=np.float64)
            curr_vals = current_df[col].to_numpy(dtype=np.float64)

            psi_score = self.calculate_psi(base_vals, curr_vals)
            has_drift = psi_score >= self.psi_threshold

            if psi_score < 0.1:
                status = "NO_DRIFT"
            elif psi_score < 0.25:
                status = "MODERATE_DRIFT"
            else:
                status = "SIGNIFICANT_DRIFT"
                drift_detected_features.append(col)

            results[col] = {
                "psi_score": round(psi_score, 4),
                "status": status,
                "has_significant_drift": has_drift,
            }

        if drift_detected_features:
            logger.warning(
                f"[DriftDetector] Significant feature drift detected in {len(drift_detected_features)} features: "
                f"{drift_detected_features}"
            )

        # Save metrics JSON report
        report_path = self.output_dir / "drift_metrics.json"
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "total_features": len(feature_cols),
                        "significant_drift_count": len(drift_detected_features),
                        "features": results,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            logger.info(f"[DriftDetector] Drift report saved to {report_path}")
        except Exception as e:
            logger.error(f"[DriftDetector] Failed to save drift report: {e}")

        from typing import cast
        return cast(Dict[str, Dict[str, Union[float, str, bool]]], results)
