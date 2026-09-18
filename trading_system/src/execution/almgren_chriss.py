"""
trading_system/src/execution/almgren_chriss.py

Almgren-Chriss Optimal Order Trajectory & Slicing Engine.
Exports AlmgrenChrissScheduler for institutional execution and optimal tranche scheduling.
"""

from trading_system.src.execution.oms_engine import AlmgrenChrissScheduler

__all__ = ["AlmgrenChrissScheduler"]
