"""
reporter.py — Output & Reporting Stage Pipeline Component

Exports structured text prediction files (ensemble_predictions.txt, strategy_data_coverage_report.txt, etc.)
and generates the GitHub Pages interactive dashboard (index.html).
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import List
import pandas as pd

logger = logging.getLogger(__name__)


class PipelineReporter:
    """
    Reporting Stage Component: Handles persistent storage of prediction reports,
    coverage metrics, and GitHub Pages HTML generation.
    """

    def export_text_predictions(
        self,
        output_dir: Path,
        ensemble_df: pd.DataFrame,
        coverage_report_text: str,
        market_label: str = "ALL"
    ) -> List[Path]:
        """Saves prediction reports to text files in target output directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        generated_files = []

        date_kst = datetime.now().strftime("%Y-%m-%d %H:%M KST")

        from src.core.strategy_registry import get_registry
        strat_cnt = get_registry().get_strategy_count() or 31

        import math
        # 1. Ensemble Predictions Output
        ens_file = output_dir / f"ensemble_predictions_{market_label}.txt" if market_label != "ALL" else output_dir / "ensemble_predictions.txt"
        tmp_ens = ens_file.with_suffix(".tmp.txt")
        try:
            with open(tmp_ens, "w", encoding="utf-8") as f:
                f.write(f"=== {strat_cnt}-Strategy Dynamic Ensemble Predictions ({market_label}) ===\n")
                f.write(f"Generated: {date_kst}\n\n")
                if ensemble_df is not None and not ensemble_df.empty:
                    top_picks = ensemble_df.head(20)
                    for rank, (_, row) in enumerate(top_picks.iterrows(), 1):
                        sym = str(row.get("symbol", "") or "").strip()
                        name = str(row.get("name", sym) or sym).strip()
                        try:
                            s_raw = float(row.get("ensemble_score", 0.0))
                            score = s_raw if math.isfinite(s_raw) else 0.0
                        except (ValueError, TypeError):
                            score = 0.0
                        try:
                            r_raw = float(row.get("ensemble_expected_return", 0.0))
                            ret = r_raw if math.isfinite(r_raw) else 0.0
                        except (ValueError, TypeError):
                            ret = 0.0
                        f.write(f"#{rank} {sym} ({name}) | Ensemble Score: {score:.2f} | Expected Return: {ret:.2f}%\n")
            tmp_ens.replace(ens_file)
            generated_files.append(ens_file)
            logger.info(f"[PipelineReporter] Saved ensemble predictions report to {ens_file.name}")
        except Exception as e:
            if tmp_ens.exists():
                try:
                    tmp_ens.unlink()
                except Exception:
                    pass
            logger.error(f"[PipelineReporter] Failed to save ensemble predictions report: {e}")

        # 2. Strategy Coverage Report Output
        cov_file = output_dir / f"strategy_data_coverage_report_{market_label}.txt" if market_label != "ALL" else output_dir / "strategy_data_coverage_report.txt"
        tmp_cov = cov_file.with_suffix(".tmp.txt")
        try:
            with open(tmp_cov, "w", encoding="utf-8") as f:
                f.write(coverage_report_text or "No coverage report data available.\n")
            tmp_cov.replace(cov_file)
            generated_files.append(cov_file)
            logger.info(f"[PipelineReporter] Saved coverage report to {cov_file.name}")
        except Exception as e:
            if tmp_cov.exists():
                try:
                    tmp_cov.unlink()
                except Exception:
                    pass
            logger.error(f"[PipelineReporter] Failed to save coverage report: {e}")

        return generated_files
