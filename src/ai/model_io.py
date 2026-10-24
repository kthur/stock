import logging
from typing import Optional, Dict, Any, List, Union
from pathlib import Path

logger = logging.getLogger(__name__)


def save_model(
    model: Any,
    filepath: Union[str, Path],
    metadata: Optional[Dict[str, Any]] = None,
    feature_names: Optional[List[str]] = None,
) -> bool:
    """Save machine learning model atomically with SHA-256 checksum and JSON metadata sidecar."""
    from src.ai.model_cache import ModelCacheManager
    manager = ModelCacheManager.get_instance()
    return manager.save_model_atomic(
        model=model,
        filepath=filepath,
        metadata=metadata,
        feature_names=feature_names,
    )


def load_model(
    filepath: Union[str, Path],
    verify_checksum: bool = True,
    expected_features: Optional[List[str]] = None,
    **kwargs,
) -> Optional[Any]:
    """Safely load machine learning model with checksum verification and feature fingerprint checking."""
    from src.ai.model_cache import ModelCacheManager
    manager = ModelCacheManager.get_instance()
    return manager.load_model_safe(
        filepath=filepath,
        verify_checksum=verify_checksum,
        expected_features=expected_features,
        **kwargs,
    )

