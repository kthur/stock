import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "trading_system"))

from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine
from src.ai.factor_suppression import RegimeFactorSuppressionEngine
from src.ai.ensemble_scorer import EnsembleScoringEngine

def check_ledoit_wolf_math():
    print("--- Checking Ledoit-Wolf Math for K=17 and K=18 ---")
    engine = FactorOrthogonalizerEngine(shrinkage_alpha=0.01)
    
    for K in [2, 5, 10, 17, 18]:
        # Perfectly collinear correlation matrix of ones
        C_ones = np.ones((K, K))
        # Shrinkage
        C_shrunk = (1.0 - 0.01) * C_ones + 0.01 * np.eye(K)
        eigs = np.linalg.eigvalsh(C_shrunk)
        cond = eigs.max() / eigs.min()
        max_theoretical = (K * 0.99 + 0.01) / 0.01
        print(f"K={K:2d}: Min Eig={eigs.min():.4f}, Max Eig={eigs.max():.4f}, Cond={cond:.2f} (Theoretical Max={max_theoretical:.2f})")

if __name__ == "__main__":
    check_ledoit_wolf_math()
