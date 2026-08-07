import sys
import os
import pytest

# Root conftest.py to ensure trading_system and root are in sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
ts_dir = os.path.join(root_dir, "trading_system")

if ts_dir not in sys.path:
    sys.path.insert(0, ts_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


@pytest.fixture
def temp_model_dir(tmp_path):
    d = tmp_path / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d

