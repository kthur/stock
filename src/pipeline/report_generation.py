"""
Report Generation Stage
Outputs structured JSON Lines (.jsonl) predictions and triggers HTML dashboard generation.
"""

import json
import logging
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)


class ReportGenerationStage:
    """Manages structured JSONL exports and dashboard report invocation."""

    def __init__(self, output_dir: str = "trading_system"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_jsonl_predictions(
        self,
        ensemble_df: pd.DataFrame,
        file_name: str = "ensemble_predictions.jsonl"
    ) -> Path:
        """Exports ensemble prediction DataFrame as structured JSON Lines format."""
        file_path = self.output_dir / file_name
        tmp_path = file_path.with_suffix(".tmp.jsonl")
        try:
            if ensemble_df is None or ensemble_df.empty:
                records = []
            else:
                records = ensemble_df.to_dict(orient="records")

            with open(tmp_path, "w", encoding="utf-8") as f:
                for rec in records:
                    if isinstance(rec, dict):
                        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            tmp_path.replace(file_path)
            logger.info(f"[REPORT STAGE] Exported {len(records)} prediction records to {file_path}")
            return file_path
        except Exception as e:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
            logger.error(f"Failed to export JSONL predictions: {e}")
            return file_path
