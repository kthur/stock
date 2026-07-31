import sys
import os
import pytest

if __name__ == "__main__":
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "regression_result.log")
    with open(log_file, "w", encoding="utf-8") as f:
        sys.stdout = f
        sys.stderr = f
        ret = pytest.main(["tests/", "-v"])
        print(f"\nREGRESSION_PYTEST_RETURN_CODE: {ret}")
        f.flush()
