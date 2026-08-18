# trading_system package init
import os
import sys

_cur_dir = os.path.dirname(os.path.abspath(__file__))
if _cur_dir not in sys.path:
    sys.path.insert(0, _cur_dir)
_parent_dir = os.path.dirname(_cur_dir)
if _parent_dir not in sys.path:
    sys.path.append(_parent_dir)

try:
    from trading_system.trading_system import StockTradingSystem
except Exception:
    pass

__all__ = ["StockTradingSystem"]
