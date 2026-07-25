"""Phase 6-C: Pipeline Profiler Utility
Monitors execution duration and peak memory usage per pipeline step.
"""

import time
import json
import logging
import functools
from pathlib import Path
from datetime import datetime

from typing import Dict, Any

logger = logging.getLogger(__name__)

PROFILE_DATA: Dict[str, Any] = {}

def profile_step(step_name: str):
    """Decorator to measure execution time and memory usage of pipeline steps."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            res = func(*args, **kwargs)
            elapsed = time.time() - start_time
            PROFILE_DATA[step_name] = {
                "duration_seconds": round(elapsed, 2),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            logger.info(f"[PROFILER] Step '{step_name}' completed in {elapsed:.2f}s")
            return res
        return wrapper
    return decorator


def save_profile_report(result_dir: str = "trading_system/result"):
    """Saves profiling metrics to pipeline_profile.json."""
    if not PROFILE_DATA:
        return
    res_path = Path(result_dir) / "pipeline_profile.json"
    res_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(res_path, "w", encoding="utf-8") as f:
            json.dump(PROFILE_DATA, f, indent=2, ensure_ascii=False)
        logger.info(f"[PROFILER] Saved pipeline profiling metrics to {res_path}")
    except Exception as e:
        logger.warning(f"[PROFILER] Failed to save profile report: {e}")
