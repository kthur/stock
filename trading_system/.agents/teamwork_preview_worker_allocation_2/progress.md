Last visited: 2026-06-07T00:04:30+09:00

Updated src/strategy/allocation.py to:
1. Filter out invalid prices using isinstance and math.isfinite.
2. Correctly compute the last asset weight to exactly equal 1.0.

Updated tests/phase3/test_allocation.py to include edge cases for float precision and infinity/nan testing.
Running tests via pytest tests/phase3/test_allocation.py and waiting for task completion.
