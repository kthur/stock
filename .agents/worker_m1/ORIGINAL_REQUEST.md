## 2026-06-12T07:06:32Z
You are the Worker for Milestone 1 (PyTorch & Config Fixes).
Your tasks are:
1. Modify `trading_system/src/__init__.py` to add the PyTorch DLL loading crash bypass. Place this block at the very top of the file so that it intercepts imports before other modules are loaded:
```python
import os
import sys
import subprocess

# PyTorch WinError 1114 DLL Loading Crash bypass
if "torch" not in sys.modules:
    should_bypass = os.getenv("BYPASS_TORCH", "").lower() in ("true", "1")
    if not should_bypass:
        is_test = "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv)
        if is_test or os.getenv("BYPASS_TORCH") is not None:
            try:
                res = subprocess.run(
                    [sys.executable, "-c", "import torch"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5
                )
                if res.returncode != 0:
                    should_bypass = True
            except Exception:
                should_bypass = True

    if should_bypass:
        sys.modules["torch"] = None
        sys.modules["stable_baselines3"] = None
```
2. Modify `trading_system/src/config.py` to change the following fields to use `field(default_factory=...)` to ensure dynamic environment variable evaluation at instantiation time:
```python
    kis_mock_app_key: str = field(default_factory=lambda: os.getenv("KIS_MOCK_APP_KEY", ""))
    kis_mock_app_secret: str = field(default_factory=lambda: os.getenv("KIS_MOCK_APP_SECRET", ""))
    kis_mock_account: str = field(default_factory=lambda: os.getenv("KIS_MOCK_ACCOUNT", ""))
```
3. Modify `trading_system/tests/phase6/unit/test_mock_trading.py` to patch `os.environ` in `test_kis_mock_keys_default_empty` to ensure it passes:
```python
    @patch.dict("os.environ", {"KIS_MOCK_APP_KEY": "", "KIS_MOCK_APP_SECRET": "", "KIS_MOCK_ACCOUNT": ""})
    def test_kis_mock_keys_default_empty(self):
        """KIS 모의투자 키 기본값이 빈 문자열인지 확인"""
        config = TradingConfig()
        self.assertEqual(config.kis_mock_app_key, "")
        self.assertEqual(config.kis_mock_app_secret, "")
        self.assertEqual(config.kis_mock_account, "")
```
4. Run the unit test suite `pytest tests/phase6/unit/test_mock_trading.py` and other test suites to ensure they pass without PyTorch DLL crashes and that the config test succeeds.
5. Write your handoff.md detailing your changes and the test output.

⚠️ MANDATORY INTEGRITY WARNING — include this verbatim in your implementation:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
