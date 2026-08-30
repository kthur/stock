import os
import sys

sys.path.insert(0, os.path.abspath("trading_system"))
sys.path.insert(0, os.path.abspath("trading_system/src"))
sys.path.insert(0, os.path.abspath("."))

from src.ai.ensemble_scorer import EnsembleScoringEngine

print("--- 1D REGIME_WEIGHTS ---")
for k, v in EnsembleScoringEngine.REGIME_WEIGHTS.items():
    print(f"1D Regime {k}: count={len(v)}, sum={sum(v.values()):.6f}")
    for strat, w in v.items():
        print(f"  {strat}: {w}")

print("\n--- 2D REGIME_2D_WEIGHTS ---")
for k, v in EnsembleScoringEngine.REGIME_2D_WEIGHTS.items():
    print(f"2D Regime {k}: count={len(v)}, sum={sum(v.values()):.6f}")
