"""
Ray Distributed Compute Orchestrator Module
Scales out data fetch, feature engineering, and 31-strategy inference across worker nodes using Ray Core / Ray Data.
"""

import logging
from typing import Dict, List, Any, Callable, Optional

logger = logging.getLogger(__name__)


class RayClusterOrchestrator:
    """
    Ray Distributed Cluster Manager.
    Maps heavy quantitative computations (XGBoost, LSTM, GNN, LLM sentiment) across Ray workers.
    """

    def __init__(self, address: Optional[str] = None):
        self.address = address
        self.is_ray_available = False
        self._init_ray()

    def _init_ray(self):
        """Attempts to connect to or initialize local/remote Ray cluster."""
        try:
            import ray
            if not ray.is_initialized():
                ray.init(address=self.address, ignore_reinit_error=True, include_dashboard=False)
            self.is_ray_available = True
            logger.info("🚀 [RAY DISTRIBUTED CLUSTER] Successfully initialized Ray Core actor cluster.")
        except Exception as e:
            logger.warning(f"⚠️ [RAY CLUSTER] Ray not available ({e}). Falling back to local process pool.")
            self.is_ray_available = False

    def parallel_map(self, func: Callable, items: List[Any], **kwargs) -> List[Any]:
        """
        Executes parallel map operation across items using Ray actors if available,
        otherwise falls back to standard sequential execution.
        """
        if not items:
            return []

        if self.is_ray_available:
            try:
                import ray
                remote_func = ray.remote(func)
                futures = [remote_func.remote(item, **kwargs) for item in items]
                results = ray.get(futures)
                logger.info(f"✅ [RAY CLUSTER] Completed parallel map for {len(items)} items.")
                return results
            except Exception as e:
                logger.warning(f"Ray parallel map failed: {e}. Executing sequentially.")

        # Sequential fallback
        return [func(item, **kwargs) for item in items]
