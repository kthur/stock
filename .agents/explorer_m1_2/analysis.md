# Milestone 1: PyTorch & Config Fixes - Investigation and Refactoring Plan

This report provides the results of our read-only investigation into the PyTorch DLL loading crash and the failing unit test `TestMockTradingConfig.test_kis_mock_keys_default_empty`. It details the root causes and outlines actionable strategies to resolve and mock/bypass these issues.

---

## 1. PyTorch DLL Loading Issue & Bypass Strategy

### 1.1 Root Cause & Crash Mechanics
On Windows environments, running `import torch` can trigger an `OSError: [WinError 1114] A dynamic link library (DLL) initialization routine failed.` or cause the Python interpreter to terminate immediately with an **access violation crash** (`0xC0000005`).
- **DLL Initialization Failure (`WinError 1114`)**: This typically occurs due to conflicts between multiple Intel OpenMP (`libiomp5md.dll`) runtimes loaded in the same process address space (e.g., from PyTorch, NumPy, MKL, or LightGBM).
- **Access Violation Crash**: Mismatched or corrupted CUDA binaries, or compiling/loading PyTorch binaries targeting instruction sets (like AVX2) not supported by the host CPU, triggers memory access violations in C++ code (such as `torch_cpu.dll` or `fbgemm.dll`).
- **try/except Ineffectiveness**: In the codebase, several import sites attempt to catch exceptions during import. However, while Python can catch `OSError` (like `WinError 1114`), it **cannot catch an access violation crash** because it occurs at the OS/process level and terminates the Python interpreter immediately.

### 1.2 Locations of `import torch` in the Codebase
The PyTorch dependency is imported at five distinct locations in the backend codebase:

1. **`trading_system/src/ai/prediction_model.py`** (Lines 6–10):
   ```python
   try:
       import torch
       _HAS_CUDA = torch.cuda.is_available()
   except Exception:
       _HAS_CUDA = False
   ```
   *Impact*: While wrapped in a `try/except`, an access violation crash here will immediately terminate the interpreter when importing the AI prediction model.

2. **`trading_system/src/ai/rl_trader.py`** (Lines 12–14):
   ```python
   import torch
   import torch.nn as nn
   import torch.optim as optim
   ```
   *Impact*: Imported unconditionally at module level. Any import of this file will trigger the crash.

3. **`trading_system/src/ai/rl_trading.py`** (Line 6 & Line 181):
   - Line 6 (Implicit Import): `from stable_baselines3 import PPO`. Importing `stable_baselines3` internally triggers `import torch`.
   - Line 181: `import torch` inside the `train_rl_model` function:
     ```python
     if seed is not None:
         import random
         import torch
         random.seed(seed)
         np.random.seed(seed)
         torch.manual_seed(seed)
     ```
   *Impact*: Importing `rl_trading` immediately crashes the interpreter via the `stable_baselines3` import.

4. **`trading_system/src/analysis/macro_predictor.py`** (Lines 26–30):
   ```python
   try:
       import torch
       _HAS_CUDA = torch.cuda.is_available()
   except Exception:
       _HAS_CUDA = False
   ```
   *Impact*: Crashes the interpreter at import time when verifying GPU-based LightGBM/XGBoost options.

5. **`trading_system/src/analysis/ml_engine.py`** (Lines 31–35):
   ```python
   try:
       import torch
       _HAS_CUDA = torch.cuda.is_available()
   except Exception:
       _HAS_CUDA = False
   ```
   *Impact*: Crashes the interpreter at import time of the main ML engine.

---

### 1.3 Resolution & Mock/Bypass Strategy

#### Option A: Resolution of the DLL Crash (For environments requiring PyTorch)
1. **Force Reinstall CPU-only Build**:
   CUDA-related DLLs are the primary source of DLL load failures. Reinstalling the CPU-only package resolves this:
   ```powershell
   pip install torch --index-url https://download.pytorch.org/whl/cpu --force-reinstall
   ```
2. **OpenMP Environment Bypass**:
   Define `KMP_DUPLICATE_LIB_OK=TRUE` to bypass the OpenMP runtimes conflict before loading the libraries.

#### Option B: Clean Bypass via `sys.modules` Mocking (Recommended for Tests & Callbacks)
To prevent the interpreter from ever calling the compiled C/C++ DLLs, we can pre-populate the `sys.modules` cache with mock/fake modules. This is extremely robust because Python's import system checks `sys.modules` first and returns the cached mock object without running module search and file loading.

To handle complex subclassing and type checks (like `class QNetwork(nn.Module)` or `isinstance(model, PPO)`), the mocks should be structured using dummy base classes:

1. **Test-specific Injection (`conftest.py`)**:
   Create a `trading_system/tests/conftest.py` file to set up the mock environment before any test module is loaded:

   ```python
   import sys
   import os
   from unittest.mock import MagicMock

   # Check if we should bypass torch DLL load
   if os.getenv("BYPASS_TORCH", "True").lower() == "true":
       # Define dummy classes to allow subclassing and isinstance checks
       class DummyModule:
           def __init__(self, *args, **kwargs):
               pass
           def __call__(self, *args, **kwargs):
               return MagicMock()

       class DummyPPO:
           def __init__(self, *args, **kwargs):
               self.env = MagicMock()
           def learn(self, *args, **kwargs):
               return self

       # Create custom Mock Module that acts like PyTorch
       class MockModule(MagicMock):
           @property
           def __spec__(self):
               return None

       mock_torch = MockModule()
       mock_torch.cuda = MockModule()
       mock_torch.cuda.is_available.return_value = False
       mock_torch.device.return_value = "cpu"
       mock_torch.manual_seed.return_value = None

       mock_nn = MockModule()
       mock_nn.Module = DummyModule

       mock_sb3 = MockModule()
       mock_sb3.PPO = DummyPPO

       # Inject into sys.modules
       sys.modules['torch'] = mock_torch
       sys.modules['torch.nn'] = mock_nn
       sys.modules['torch.optim'] = MockModule()
       sys.modules['stable_baselines3'] = mock_sb3
   ```

2. **Production/Runtime Bypass (`src/__init__.py`)**:
   If the runtime application (dashboard and callbacks) needs to run on environments where PyTorch is broken or missing, the same injection logic can be placed in `trading_system/src/__init__.py`.

---

## 2. KIS Config Key Unit Test Failure

### 2.1 Root Cause
The unit test `TestMockTradingConfig.test_kis_mock_keys_default_empty` in `trading_system/tests/phase6/unit/test_mock_trading.py` instantiates `TradingConfig()` and expects the KIS mock keys to be empty:
```python
    def test_kis_mock_keys_default_empty(self):
        config = TradingConfig()
        self.assertEqual(config.kis_mock_app_key, "")
        self.assertEqual(config.kis_mock_app_secret, "")
        self.assertEqual(config.kis_mock_account, "")
```
However, in `trading_system/src/config.py`, `.env` is loaded using `load_dotenv` at the top of the file:
```python
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
```
And the KIS keys evaluate `os.getenv` at **class definition (import) time**:
```python
@dataclass
class TradingConfig:
    # ...
    kis_mock_app_key: str = os.getenv("KIS_MOCK_APP_KEY", "")
    kis_mock_app_secret: str = os.getenv("KIS_MOCK_APP_SECRET", "")
    kis_mock_account: str = os.getenv("KIS_MOCK_ACCOUNT", "")
```
Because `trading_system/.env` has keys defined (`your_kis_mock_app_key_here`, etc.), the default values for these class-level attributes are set to these strings during module import. Patching `os.environ` *during* the test execution does not change the already-evaluated class attributes. Thus, `TradingConfig()` yields the strings from `.env`, failing the test.

---

### 2.2 Proposed Solution

#### A. Source Code Modification (`src/config.py`)
Evaluate the environment variables at **instantiation time** (when `TradingConfig()` is called) using `dataclasses.field(default_factory=...)` instead of class definition time:

**Before (Lines 33–35 in `trading_system/src/config.py`)**:
```python
    # KIS 모의투자 키 설정
    kis_mock_app_key: str = os.getenv("KIS_MOCK_APP_KEY", "")
    kis_mock_app_secret: str = os.getenv("KIS_MOCK_APP_SECRET", "")
    kis_mock_account: str = os.getenv("KIS_MOCK_ACCOUNT", "")
```

**After**:
```python
    # KIS 모의투자 키 설정
    kis_mock_app_key: str = field(default_factory=lambda: os.getenv("KIS_MOCK_APP_KEY", ""))
    kis_mock_app_secret: str = field(default_factory=lambda: os.getenv("KIS_MOCK_APP_SECRET", ""))
    kis_mock_account: str = field(default_factory=lambda: os.getenv("KIS_MOCK_ACCOUNT", ""))
```

#### B. Unit Test Modification (`tests/phase6/unit/test_mock_trading.py`)
Patch the environment variables to empty strings during the test execution. Because we modified `src/config.py` to use `default_factory`, the mock values will be fetched dynamically from the patched environment when the test instantiates `TradingConfig()`:

**Before (Lines 21–27 in `trading_system/tests/phase6/unit/test_mock_trading.py`)**:
```python
    def test_kis_mock_keys_default_empty(self):
        """KIS 모의투자 키 기본값이 빈 문자열인지 확인"""
        config = TradingConfig()
        self.assertEqual(config.kis_mock_app_key, "")
        self.assertEqual(config.kis_mock_app_secret, "")
        self.assertEqual(config.kis_mock_account, "")
```

**After**:
```python
    @patch.dict("os.environ", {"KIS_MOCK_APP_KEY": "", "KIS_MOCK_APP_SECRET": "", "KIS_MOCK_ACCOUNT": ""})
    def test_kis_mock_keys_default_empty(self):
        """KIS 모의투자 키 기본값이 빈 문자열인지 확인"""
        config = TradingConfig()
        self.assertEqual(config.kis_mock_app_key, "")
        self.assertEqual(config.kis_mock_app_secret, "")
        self.assertEqual(config.kis_mock_account, "")
```
*Note*: By using `@patch.dict("os.environ", ...)` with a string identifier, we don't even need to add `import os` to the test file.
