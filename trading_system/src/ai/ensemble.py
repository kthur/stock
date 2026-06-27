import numpy as np
import pandas as pd
from xgboost import XGBRegressor, XGBClassifier
from lightgbm import LGBMRegressor, LGBMClassifier
from catboost import CatBoostRegressor, CatBoostClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
import logging

logger = logging.getLogger(__name__)

class EnsembleRegressor:
    """A meta-estimator implementing stacking for predictions to increase robustness."""
    def __init__(self, xgb_params: dict, lgb_params: dict, cat_params: dict):
        self.xgb = XGBRegressor(**xgb_params)
        self.lgb = LGBMRegressor(**lgb_params)
        self.cat = CatBoostRegressor(**cat_params)
        self.meta_learner = LinearRegression()
        self.is_fitted = False

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series, X_val: pd.DataFrame = None, y_val: pd.Series = None):
        # Fit base models
        if X_val is not None and y_val is not None:
            self.xgb.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
            self.lgb.fit(X_train, y_train, eval_set=[(X_val, y_val)], callbacks=[])
            self.cat.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        else:
            self.xgb.fit(X_train, y_train)
            self.lgb.fit(X_train, y_train)
            self.cat.fit(X_train, y_train, verbose=False)

        # Generate base predictions to train meta-learner
        X_meta_train = X_val if X_val is not None else X_train
        y_meta_train = y_val if y_val is not None else y_train

        p_xgb = self.xgb.predict(X_meta_train)
        p_lgb = self.lgb.predict(X_meta_train)
        p_cat = self.cat.predict(X_meta_train)

        stacked_features = np.column_stack((p_xgb, p_lgb, p_cat))
        self.meta_learner.fit(stacked_features, y_meta_train)
        self.is_fitted = True
        logger.info(f"EnsembleRegressor meta-learner coefficients: {self.meta_learner.coef_}")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            raise ValueError("Ensemble models are not fitted.")
        p_xgb = self.xgb.predict(X)
        p_lgb = self.lgb.predict(X)
        p_cat = self.cat.predict(X)
        stacked_features = np.column_stack((p_xgb, p_lgb, p_cat))
        return self.meta_learner.predict(stacked_features)  # type: ignore[no-any-return]


class EnsembleClassifier:
    """A meta-estimator implementing stacking for class probabilities."""
    def __init__(self, xgb_params: dict, lgb_params: dict, cat_params: dict):
        self.xgb = XGBClassifier(**xgb_params)
        self.lgb = LGBMClassifier(**lgb_params)
        self.cat = CatBoostClassifier(**cat_params)
        self.meta_learner = LogisticRegression()
        self.is_fitted = False

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series, X_val: pd.DataFrame = None, y_val: pd.Series = None):
        # Fit base models
        if X_val is not None and y_val is not None:
            self.xgb.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
            self.lgb.fit(X_train, y_train, eval_set=[(X_val, y_val)], callbacks=[])
            self.cat.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        else:
            self.xgb.fit(X_train, y_train)
            self.lgb.fit(X_train, y_train)
            self.cat.fit(X_train, y_train, verbose=False)

        # Generate out-of-fold/val probabilities
        X_meta_train = X_val if X_val is not None else X_train
        y_meta_train = y_val if y_val is not None else y_train

        p_xgb = self.xgb.predict_proba(X_meta_train)[:, 1]
        p_lgb = self.lgb.predict_proba(X_meta_train)[:, 1]
        p_cat = self.cat.predict_proba(X_meta_train)[:, 1]

        stacked_features = np.column_stack((p_xgb, p_lgb, p_cat))
        self.meta_learner.fit(stacked_features, y_meta_train)
        self.is_fitted = True
        logger.info(f"EnsembleClassifier meta-learner coefficients: {self.meta_learner.coef_}")

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            raise ValueError("Ensemble models are not fitted.")
        p_xgb = self.xgb.predict_proba(X)[:, 1]
        p_lgb = self.lgb.predict_proba(X)[:, 1]
        p_cat = self.cat.predict_proba(X)[:, 1]
        stacked_features = np.column_stack((p_xgb, p_lgb, p_cat))
        return self.meta_learner.predict_proba(stacked_features)  # type: ignore[no-any-return]

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            raise ValueError("Ensemble models are not fitted.")
        p_xgb = self.xgb.predict(X)
        p_lgb = self.lgb.predict(X)
        p_cat = self.cat.predict(X)
        stacked_features = np.column_stack((p_xgb, p_lgb, p_cat))
        return self.meta_learner.predict(stacked_features)  # type: ignore[no-any-return]
