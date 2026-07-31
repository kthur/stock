"""
Forwarder for CPCV & Historical Stress Testing Engine.
Re-exports symbols from trading_system.src.ai.cpcv_stress_tester.
"""

import os
import sys

try:
    from trading_system.src.ai.cpcv_stress_tester import (
        CPCVStressTester,
        StressTestReport,
        run_historical_stress_test,
    )
except ImportError:
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ts_path = os.path.join(parent_dir, "trading_system")
    if ts_path not in sys.path:
        sys.path.insert(0, ts_path)
    from trading_system.src.ai.cpcv_stress_tester import (
        CPCVStressTester,
        StressTestReport,
        run_historical_stress_test,
    )

__all__ = [
    "CPCVStressTester",
    "StressTestReport",
    "run_historical_stress_test",
]
