"""
Strategy Scoring Stage
Evaluates all 27 multi-factor trading strategies using ThreadPoolExecutor for concurrent execution.
"""

import logging
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any

logger = logging.getLogger(__name__)


class StrategyScoringStage:
    """Orchestrates parallel execution of all multi-factor strategy engines."""

    def __init__(self, max_workers: int = 8):
        self.max_workers = max(1, int(max_workers)) if max_workers is not None else 8

    def run_all_strategies(
        self,
        strategy_engines: Dict[str, Any],
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Dict[str, Dict[str, Any]],
        macro_indicators: Dict[str, Any],
        universe_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Runs all strategy scoring methods concurrently using ThreadPoolExecutor."""
        if not strategy_engines:
            return {}

        logger.info(f"[STRATEGY SCORING] Executing strategies in parallel using ThreadPoolExecutor (workers={self.max_workers})...")
        results: Dict[str, Any] = {}

        def _score_wrapper(name: str, engine: Any):
            try:
                if hasattr(engine, "compute_scores"):
                    # Check method parameters
                    import inspect
                    sig = inspect.signature(engine.compute_scores)
                    params = sig.parameters

                    kwargs = {}
                    if "prices_dict" in params or "df_prices" in params:
                        kwargs["df_prices" if "df_prices" in params else "prices_dict"] = prices_dict
                    if "fundamentals_dict" in params or "features_df" in params:
                        kwargs["fundamentals_dict" if "fundamentals_dict" in params else "features_df"] = fundamentals_dict
                    if "universe" in params or "universe_df" in params:
                        kwargs["universe" if "universe" in params else "universe_df"] = universe_df
                    if "macro_indicators" in params:
                        kwargs["macro_indicators"] = macro_indicators

                    res = engine.compute_scores(**kwargs)
                    return name, res
                elif hasattr(engine, "find_cointegrated_pairs"):
                    res = engine.find_cointegrated_pairs(prices_dict)
                    return name, res
                elif callable(engine):
                    return name, engine()
            except Exception as e:
                logger.warning(f"Strategy '{name}' parallel execution exception: {e}")
                return name, None
            return name, None

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(_score_wrapper, strat_name, engine)
                for strat_name, engine in strategy_engines.items()
            ]

            for future in as_completed(futures):
                strat_name, score_res = future.result()
                if score_res is not None:
                    results[strat_name] = score_res
                    logger.info(f"  [PARALLEL STRATEGY] Strategy '{strat_name}' completed.")

        logger.info(f"[STRATEGY SCORING] Completed parallel scoring for {len(results)} strategies.")
        return results
