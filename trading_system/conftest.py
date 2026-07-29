import sys
import os

ts_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(ts_dir)

if ts_dir not in sys.path:
    sys.path.insert(0, ts_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
