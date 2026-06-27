import json
import os
import xgboost as xgb
import lightgbm as lgb
import catboost as cb
import logging

logger = logging.getLogger(__name__)

def save_model(model, filepath: str, metadata: dict | None = None) -> None:
    """Save machine learning model along with a JSON metadata side-car file."""
    # Ensure folder structure exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Save the model booster/weights depending on library type
    if isinstance(model, xgb.XGBModel):
        model.get_booster().save_model(filepath)
    elif isinstance(model, lgb.LGBMModel):
        model.booster_.save_model(filepath)
    elif isinstance(model, (cb.CatBoostRegressor, cb.CatBoostClassifier)):
        model.save_model(filepath)
    else:
        # Fallback to general pickle/joblib if needed
        import joblib
        joblib.dump(model, filepath)

    # Save side-car JSON file containing metadata
    meta_path = filepath + "_meta.json"
    if metadata is None:
        metadata = {}

    metadata.update({
        "saved_filepath": filepath,
        "model_class": model.__class__.__name__
    })

    try:
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.debug(f"Saved model metadata to {meta_path}")
    except Exception as e:
        logger.error(f"Failed to save metadata to {meta_path}: {e}")
