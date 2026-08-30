import sys

def run_tests():
    print("=== STARTING DIRECT EXECUTION OF ADVERSARIAL M2 TESTS ===", flush=True)
    import pytest
    ret = pytest.main([
        "-v",
        "-s",
        "trading_system/tests/test_adversarial_regime_sharpe_m2.py"
    ])
    print(f"=== PYTEST FINISHED WITH EXIT CODE {ret} ===", flush=True)
    return ret

if __name__ == "__main__":
    sys.exit(run_tests())
