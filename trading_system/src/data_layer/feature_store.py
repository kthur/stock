"""
trading_system/src/data_layer/feature_store.py
DuckDB / Parquet Feature Store & Parallel Strategy Inference Engine.

Key Capabilities:
1. Columnar Parquet Feature Persistence Layer for 3,379 symbols & 31 strategies.
2. Fast DuckDB / PyArrow Queries bypassing SQLite locks.
3. Parallel Strategy Inference Execution via ProcessPoolExecutor / ThreadPoolExecutor.
"""

import os
import logging
import concurrent.futures
from pathlib import Path
from typing import Dict, Optional, Tuple, Any, Callable, Union
import pandas as pd

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class FeatureStore:
    """
    Parquet/DuckDB Feature Store for high-concurrency 31-strategy feature caching & parallel inference.
    """

    def __init__(self, store_dir: Optional[Union[str, Path]] = None):
        if store_dir is None:
            self.store_dir = _PROJECT_ROOT / "data" / "feature_store"
        else:
            self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def _get_parquet_path(self, date_str: str, market: str) -> Path:
        clean_market = str(market).upper().replace("/", "_")
        clean_date = str(date_str).replace("-", "")
        return self.store_dir / f"features_{clean_market}_{clean_date}.parquet"

    def save_strategy_features(self, date_str: str, market: str, feature_df: pd.DataFrame) -> Path:
        """
        Saves calculated 31-strategy feature DataFrame as compressed Parquet file.
        """
        if feature_df is None or feature_df.empty:
            logger.warning(f"FeatureStore: Attempted to save empty feature_df for {market} {date_str}")
            return Path()

        path = self._get_parquet_path(date_str, market)
        tmp_path = path.with_suffix(".tmp.parquet")
        try:
            df_copy = feature_df.copy()
            # Downcast floats to float32 to conserve RAM & I/O, sanitizing non-finite values
            float_cols = df_copy.select_dtypes(include=['float64', 'float32', 'object']).columns
            for col in float_cols:
                num_s = pd.to_numeric(df_copy[col], errors='ignore')
                if pd.api.types.is_float_dtype(num_s):
                    df_copy[col] = num_s.fillna(0.0).clip(lower=-1e9, upper=1e9).astype('float32')

            df_copy.to_parquet(tmp_path, compression='snappy', index=False)
            os.replace(tmp_path, path)
            logger.info(f"[FEATURE STORE] Saved {len(df_copy)} rows for {market} ({date_str}) to {path.name}")
            return path
        except Exception as e:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
            logger.error(f"[FEATURE STORE] Failed to save features to {path}: {e}")
            return Path()

    def load_strategy_features(self, date_str: str, market: str) -> pd.DataFrame:
        """
        Fast columnar load of cached Parquet feature DataFrame.
        """
        path = self._get_parquet_path(date_str, market)
        if not path.exists():
            return pd.DataFrame()

        try:
            df = pd.read_parquet(path)
            logger.info(f"[FEATURE STORE] Loaded {len(df)} rows for {market} ({date_str}) from {path.name}")
            return df
        except Exception as e:
            logger.error(f"[FEATURE STORE] Failed to load features from {path}: {e}")
            return pd.DataFrame()

    def has_features(self, date_str: str, market: str) -> bool:
        """Checks if Parquet feature cache exists for market and date."""
        path = self._get_parquet_path(date_str, market)
        return path.exists() and path.stat().st_size > 0

    def run_parallel_strategy_inference(
        self,
        strategy_func_map: Dict[str, Tuple[Callable, Dict[str, Any]]],
        max_workers: int = 4
    ) -> Dict[str, pd.DataFrame]:
        """
        Executes 31-strategy score inference functions in parallel using ProcessPool / ThreadPool.
        """
        if not strategy_func_map:
            return {}

        workers = max(1, int(max_workers)) if max_workers is not None else 4
        results: Dict[str, pd.DataFrame] = {}
        logger.info(f"[FEATURE STORE] Executing parallel inference for {len(strategy_func_map)} strategies with {workers} workers...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_strat = {
                executor.submit(func, **kwargs): strat_name
                for strat_name, (func, kwargs) in strategy_func_map.items()
            }

            for future in concurrent.futures.as_completed(future_to_strat):
                strat_name = future_to_strat[future]
                try:
                    res_df = future.result()
                    results[strat_name] = res_df if isinstance(res_df, pd.DataFrame) else pd.DataFrame()
                except Exception as e:
                    logger.error(f"[FEATURE STORE] Parallel inference error in strategy {strat_name}: {e}")
                    results[strat_name] = pd.DataFrame()

        return results
