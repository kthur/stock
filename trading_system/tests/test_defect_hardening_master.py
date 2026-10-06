"""
Master Unified Regression Test Suite for Defect Hardening (D1 ~ D33)
Forwarding import to tests/test_defect_hardening_master.py
"""
import os
import sys

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from tests.test_defect_hardening_master import *
