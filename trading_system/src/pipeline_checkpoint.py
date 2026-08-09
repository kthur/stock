"""
Pipeline Checkpoint & Resume Manager
Saves and loads intermediate pipeline stage data to disk (pickle/parquet) to support resuming from failures.
"""

import logging
import pickle
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PipelineCheckpoint:
    """Manages disk serialization and restoration of pipeline stage snapshots."""

    STAGES = [
        "macro_indicators",
        "universe_loaded",
        "price_data_fetched",
        "training_data_ready",
        "models_trained",
        "inference_complete",
        "ensemble_scored",
    ]

    def __init__(self, checkpoint_dir: str = "models/checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save(self, stage: str, data: Dict[str, Any]) -> None:
        """Save stage data snapshot to disk."""
        if stage not in self.STAGES:
            logger.warning(f"Unknown checkpoint stage: {stage}")
        file_path = self.checkpoint_dir / f"{stage}.pkl"
        try:
            with open(file_path, "wb") as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info(f"[CHECKPOINT] Stage '{stage}' successfully saved to {file_path}")
        except Exception as e:
            logger.warning(f"Failed to save checkpoint for stage '{stage}': {e}")

    def load(self, stage: str) -> Optional[Dict[str, Any]]:
        """Load stage data snapshot from disk."""
        file_path = self.checkpoint_dir / f"{stage}.pkl"
        if not file_path.exists():
            return None
        try:
            with open(file_path, "rb") as f:
                data = pickle.load(f)
            logger.info(f"[CHECKPOINT] Stage '{stage}' successfully restored from {file_path}")
            from typing import cast
            return cast(Optional[Dict[str, Any]], data)

        except Exception as e:
            logger.warning(f"Failed to load checkpoint for stage '{stage}': {e}")
            return None

    def exists(self, stage: str) -> bool:
        """Check if stage checkpoint exists on disk."""
        return (self.checkpoint_dir / f"{stage}.pkl").exists()

    def clear(self) -> None:
        """Clear all stored stage checkpoints."""
        for stage in self.STAGES:
            fp = self.checkpoint_dir / f"{stage}.pkl"
            if fp.exists():
                fp.unlink()
        logger.info("[CHECKPOINT] Cleared all pipeline stage checkpoints.")
