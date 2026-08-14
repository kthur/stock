"""
Crowding Monitor Forwarder:
Re-exports CrowdingRiskMonitor from trading_system.src.risk.crowding_monitor.
"""

from trading_system.src.risk.crowding_monitor import CrowdingRiskMonitor

__all__ = ["CrowdingRiskMonitor"]
