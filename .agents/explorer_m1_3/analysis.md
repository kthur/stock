# PyTorch & Config Fixes Analysis

## 1. PyTorch WinError 1114 / Access Violation Investigation

### Problem Description
On Windows environments, importing PyTorch (`import torch`) raises `OSError: [WinError 1114] A dynamic link library (DLL) initialization routine failed` or causes a fatal `access violation` (0xc0000005) crash in the C-runtime, terminating the Python interpreter immediately. This crash makes it impossible to collect or run unit tests that directly or indirectly import PyTorch, even if the tests do not execute any deep learning code.

### Transitive Import Chain causing the Crash
Through a detailed traceback of the crash during pytest test collection of `test_mock_trading.py`, we identified the exact transitive import path that triggers the crash:
1. `trading_system/tests/phase6/unit/test_mock_trading.py` imports `src.core.order_management` (line 9).
2. Importing `src` runs `src/__init__.py` which imports `src.data_layer` (line 12).
3. `src.data_layer`'s `__init__.py` imports `src.data_layer.market_data_handler` (line 4).
4. `market_data_handler.py` imports `src.analysis` (line 15).
5. `src.analysis`'s `__init__.py` imports `src.analysis.backtest` (line 3).
6. `backtest.py` imports `src.analysis.ml_engine` (line 14).
7. `ml_engine.py` executes `import torch` (line 32).
8. Python crashes with an access violation inside `torch\__init__.py` during `_load_dll_libraries`.

### Codebase Import Locations
The codebase contains `import torch` in the following locations:
1. **`trading_system/src/analysis/ml_engine.py`** (Line 32):
   ```python
   try:
       import torch
       _HAS_CUDA = torch.cuda.is_available()
   except Exception:
       _HAS_CUDA = False
   ```
2. **`trading_system/src/analysis/macro_predictor.py`** (Line 27):
   ```python
   try:
       import torch
       _HAS_CUDA = torch.cuda.is_available()
   except Exception:
       _HAS_CUDA = False
   ```
3. **`trading_system/src/ai/prediction_model.py`** (Line 7):
   ```python
   try:
       import torch
       _HAS_CUDA = torch.cuda.is_available()
   except Exception:
       _HAS_CUDA = False
   ```
4. **`trading_system/src/ai/rl_trader.py`** (Lines 12–14):
   ```python
   import torch
   import torch.nn as nn
   import torch.optim as optim
   ```
5. **`trading_system/src/ai/rl_trading.py`** (Lines 6 & 181):
   - Line 6: `from stable_baselines3 import PPO` (imports PyTorch transitively).
   - Line 181: `import torch` (inside `train_rl_model`).

### Recommendations & Remediation Strategy

#### A. System-Level Resolution
If PyTorch is actually required (e.g., to run reinforcement learning/prediction models) and PyTorch's GPU/CUDA DLLs are failing:
1. **Re-install CPU-only PyTorch**: Reinstalling PyTorch as a CPU-only version avoids loading CUDA DLLs, which is the primary source of `WinError 1114` on environments without properly configured graphics drivers.
   ```powershell
   trading_system\.venv\Scripts\pip install torch --index-url https://download.pytorch.org/whl/cpu --force-reinstall
   ```
2. **NVIDIA Driver Update**: Update the NVIDIA graphics driver and CUDA Toolkit.
3. **Environment Flag**: Add `KMP_DUPLICATE_LIB_OK=TRUE` to system environment variables to prevent Intel OpenMP conflicts.

#### B. Software-Level Bypass / Mocking (Recommended Workaround)
To prevent the interpreter from crashing when PyTorch cannot be loaded (especially during unit tests), we can dynamically intercept and mock `torch` and `stable_baselines3` at import time. 

Since the C-level DLL crash cannot be caught by `try-except`, we must prevent `import torch` from loading the native library. We can achieve this by injecting a mocked `torch` object into `sys.modules` before any imports are resolved.

We recommend placing this auto-detection and mocking logic at the very top of `trading_system/src/__init__.py`:

```python
import sys
import os
import subprocess
from unittest.mock import MagicMock

def _setup_torch_bypass():
    # Allow manual bypass via env var or auto-detect if on Windows
    bypass = os.getenv("BYPASS_TORCH", "").lower() == "true"
    
    if not bypass and sys.platform == "win32":
        cache_file = os.path.join(os.path.dirname(__file__), ".torch_broken")
        if os.path.exists(cache_file):
            bypass = True
        else:
            try:
                # Run a fast, isolated subprocess to check if importing torch crashes
                res = subprocess.run(
                    [sys.executable, "-c", "import torch"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=3
                )
                if res.returncode != 0:
                    bypass = True
                    # Cache the result to avoid spawning subprocesses in the future
                    try:
                        with open(cache_file, "w") as f:
                            f.write("true")
                    except Exception:
                        pass
            except Exception:
                bypass = True
                
    if bypass:
        # Inject mock torch to prevent native DLL loading
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_torch.__version__ = "2.12.0"
        
        sys.modules['torch'] = mock_torch
        sys.modules['torch.nn'] = mock_torch.nn
        sys.modules['torch.optim'] = mock_torch.optim
        
        # Mock transitive dependencies that rely on torch
        sys.modules['stable_baselines3'] = MagicMock()
        sys.modules['stable_baselines3.PPO'] = MagicMock()
        sys.modules['gymnasium'] = MagicMock()
        
        print("WARNING: PyTorch DLL loading is broken or bypassed. Using mocked torch to prevent interpreter crash.")

_setup_torch_bypass()
```

---

## 2. Unit Test `TestMockTradingConfig.test_kis_mock_keys_default_empty` Investigation

### Problem Description
The test `test_kis_mock_keys_default_empty` in `trading_system/tests/phase6/unit/test_mock_trading.py` instantiates `TradingConfig()` and verifies that `kis_mock_app_key`, `kis_mock_app_secret`, and `kis_mock_account` are empty strings by default.

However, `trading_system/.env` defines these keys:
```env
KIS_MOCK_APP_KEY=your_kis_mock_app_key_here
KIS_MOCK_APP_SECRET=your_kis_mock_app_secret_here
KIS_MOCK_ACCOUNT=your_kis_mock_account_here
```
When `TradingConfig` is imported, it automatically calls `load_dotenv()`, loading these values into `os.environ`. Because the fields in `TradingConfig` are defined with class-level defaults evaluated at import time:
```python
    kis_mock_app_key: str = os.getenv("KIS_MOCK_APP_KEY", "")
```
the class default becomes `"your_kis_mock_app_key_here"`. As a result, the test fails with:
`AssertionError: 'your_kis_mock_app_key_here' != ''`

### Recommendations & Remediation Strategy

We suggest two options to make the test pass regardless of what is set in the local `.env` file:

#### Option 1: Evaluate Environment Variables at Instantiation Time (Recommended Code Fix)
Modify `trading_system/src/config.py` to use `dataclasses.field` with a `default_factory` for these environment variables. This shifts their evaluation from class definition time (import time) to instance creation time (runtime):

```python
from dataclasses import dataclass, field
import os

@dataclass
class TradingConfig:
    # ...
    # Evaluate at instantiation time using default_factory
    kis_mock_app_key: str = field(default_factory=lambda: os.getenv("KIS_MOCK_APP_KEY", ""))
    kis_mock_app_secret: str = field(default_factory=lambda: os.getenv("KIS_MOCK_APP_SECRET", ""))
    kis_mock_account: str = field(default_factory=lambda: os.getenv("KIS_MOCK_ACCOUNT", ""))
```

If this is implemented, the unit test in `test_mock_trading.py` can be decorated with `patch.dict` to clear the environment variables during the test execution:

```python
    @patch.dict(os.environ, {
        "KIS_MOCK_APP_KEY": "",
        "KIS_MOCK_APP_SECRET": "",
        "KIS_MOCK_ACCOUNT": ""
    })
    def test_kis_mock_keys_default_empty(self):
        """KIS 모의투자 키 기본값이 빈 문자열인지 확인"""
        config = TradingConfig()
        self.assertEqual(config.kis_mock_app_key, "")
        self.assertEqual(config.kis_mock_app_secret, "")
        self.assertEqual(config.kis_mock_account, "")
```

#### Option 2: Test-Side Module Reloading (Zero Code Changes to `src/config.py`)
If `src/config.py` must remain completely unchanged, the unit test can isolate itself from the cached imports by temporarily deleting `src.config` from `sys.modules`, clearing the environment variables, importing a fresh copy of the module to verify defaults, and restoring the original module afterwards:

```python
    def test_kis_mock_keys_default_empty(self):
        """KIS 모의투자 키 기본값이 빈 문자열인지 확인"""
        import sys
        import os
        import importlib
        from unittest.mock import patch
        
        # 1. Save original config module if already loaded
        original_config = sys.modules.get('src.config')
        
        # 2. Clear config from sys.modules to force a fresh re-import
        if 'src.config' in sys.modules:
            del sys.modules['src.config']
            
        try:
            # 3. Clear environment variables and import fresh config module
            with patch.dict(os.environ, {
                "KIS_MOCK_APP_KEY": "",
                "KIS_MOCK_APP_SECRET": "",
                "KIS_MOCK_ACCOUNT": ""
            }):
                import src.config
                config = src.config.TradingConfig()
                self.assertEqual(config.kis_mock_app_key, "")
                self.assertEqual(config.kis_mock_app_secret, "")
                self.assertEqual(config.kis_mock_account, "")
        finally:
            # 4. Clean up and restore the original cached module
            if 'src.config' in sys.modules:
                del sys.modules['src.config']
            if original_config:
                sys.modules['src.config'] = original_config
```
This is fully self-contained within the test file and guarantees the test will pass on any environment regardless of the `.env` settings.
