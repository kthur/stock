import math
import random
import sys

sys.path.append(r"d:\Finance\code\stock\trading_system")

from src.strategy.allocation import allocate_assets

def run_tests():
    errors = []

    print("Test 1")
    res = allocate_assets({})
    if res != {}: errors.append(f"Expected empty dict for {{}}, got {res}")

    print("Test 2")
    res = allocate_assets({'A': 0, 'B': -1, 'C': -0.0})
    if res != {}: errors.append(f"Expected empty dict for all <= 0, got {res}")

    print("Test 3")
    res = allocate_assets({'A': 10, 'B': 30})
    if sum(res.values()) != 1.0: errors.append(f"Sum not 1.0 for normal case: {sum(res.values())}")

    print("Test 4")
    for i in range(100):
        n = random.randint(10, 1000)
        prices = {f"Asset_{j}": random.uniform(0.01, 1000.0) for j in range(n)}
        prices['Zero'] = 0.0
        prices['Neg'] = -10.0
        res = allocate_assets(prices)
        s = sum(res.values())
        if s != 1.0:
            errors.append(f"Sum is not exactly 1.0, it is {s} for {n} items")
            break

    print("Test 5")
    try:
        res = allocate_assets({'A': 10, 'B': float('inf')})
        s = sum(res.values())
        if math.isnan(s):
            errors.append("Sum is NaN when inf price is given")
    except Exception as e:
        errors.append(f"Exception on inf price: {e}")

    print("Test 6")
    try:
        res = allocate_assets({'A': 10, 'B': float('nan')})
        s = sum(res.values())
        if s != 1.0:
            errors.append(f"Sum not 1.0 for NaN price: {s}")
    except Exception as e:
        errors.append(f"Exception on nan price: {e}")

    print("Test 7")
    for i in range(1000):
        prices = {f"{j}": random.random() for j in range(100)}
        res = allocate_assets(prices)
        s = sum(res.values())
        if s != 1.0:
            errors.append(f"Sum is not exactly 1.0 on test 7: {s}")
            break

    if errors:
        for e in errors:
            print("ERROR:", e)
        print("FAIL")
        sys.exit(1)
    else:
        print("PASS")

if __name__ == '__main__':
    run_tests()
