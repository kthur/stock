import random

fails = 0
for _ in range(1000):
    w = [random.random() for _ in range(100)]
    s = sum(w)
    w = [x/s for x in w]
    others_before = w[:50]
    others_after = w[51:]

    # We want sum(others_before) + w[50] + sum(others_after) == 1.0
    # in left-to-right evaluation.

    best_diff = 1.0
    found = False

    # Just try all possible floats in a small range?
    # Actually, left-to-right evaluation:
    # S1 = sum(others_before)
    # S2 = S1 + w[50]
    # S_final = S2 + others_after[0] + others_after[1] ...

    # Let's try adjusting w[50] to see if ANY value gives exact 1.0
    # We can do binary search!
    low = 0.0
    high = 1.0
    for _ in range(100):
        mid = (low + high) / 2
        w[50] = mid
        current_sum = sum(w)
        if current_sum == 1.0:
            found = True
            break
        elif current_sum < 1.0:
            low = mid
        else:
            high = mid

    if not found:
        fails += 1

print("Unachievable 1.0 sum:", fails)
