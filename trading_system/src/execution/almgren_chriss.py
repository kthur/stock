"""
trading_system/src/execution/almgren_chriss.py

Almgren-Chriss Optimal Order Trajectory & Slicing Engine.
Exports AlmgrenChrissScheduler for institutional execution and optimal tranche scheduling.
Supports Phase 100 (Feature F473), Phase 101 (Feature F478), Phase 102 (Feature F483) & Phase 103 (Feature F488) Dual-OMS Preemptive Micro-Tick Shading & Intraday U-Curve Slicing.
"""

from trading_system.src.execution.oms_engine import AlmgrenChrissScheduler

__all__ = ["AlmgrenChrissScheduler"]
