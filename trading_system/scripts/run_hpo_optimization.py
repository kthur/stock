import sys
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Add trading_system to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ai.optuna_tuner import OptunaStrategyTuner
from src.core.strategy_registry import get_registry

def main():
    logger.info("Initializing 31-Strategy 2D Regime Optuna Tuner...")
    registry = get_registry()
    registry.auto_discover()
    all_strategies = registry.get_all_ids()
    logger.info(f"Registered strategies count: {len(all_strategies)}: {all_strategies}")
    
    tuner = OptunaStrategyTuner()
    
    # Run full optimization across all 31 strategies and 6 regimes
    tuned_params = tuner.tune_all(n_trials=15)
    
    logger.info("Optuna HPO Optimization Complete!")
    logger.info(f"Tuned 2D Regimes: {list(tuned_params.get('regime_2d_weights', {}).keys())}")
    logger.info(f"Parameters saved to: {tuner.params_file}")

if __name__ == "__main__":
    main()
