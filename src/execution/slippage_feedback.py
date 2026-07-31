"""
Slippage Feedback Module (Forwarder):
Re-exports SlippageFeedbackEngine and SlippageMetrics from trading_system.src.execution.slippage_feedback.
"""

import os
import sys

try:
    from trading_system.src.execution.slippage_feedback import (
        SlippageFeedbackEngine,
        SlippageMetrics,
    )
except ImportError:
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ts_path = os.path.join(parent_dir, "trading_system")
    if ts_path not in sys.path:
        sys.path.insert(0, ts_path)
    from src.execution.slippage_feedback import (
        SlippageFeedbackEngine,
        SlippageMetrics,
    )

__all__ = ["SlippageFeedbackEngine", "SlippageMetrics"]
