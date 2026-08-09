"""
Report Generation Stage
Outputs structured JSON Lines (.jsonl) predictions and triggers HTML dashboard generation.
"""

import json
import logging
from pathlib import Path
import pandas as pd
from typing import Dict, Any, List

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
        try:
            records = ensemble_df.to_dict(orient="records")
            with open(file_path, "w", encoding="utf-8") as f:
                for rec in records:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            logger.info(f"[REPORT STAGE] Exported {len(records)} prediction records to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to export JSONL predictions: {e}")
            return file_path
