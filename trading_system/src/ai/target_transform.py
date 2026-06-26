import numpy as np
import pandas as pd

def transform_return(ret_series: pd.Series) -> pd.Series:
    """Apply clipping and log1p transformation to returns to stabilize targets."""
    # Clip returns to extreme range [-0.5, 0.5] before transformation
    clipped = np.clip(ret_series, -0.5, 0.5)
    return np.log1p(clipped)

def inverse_transform(pred_series: pd.Series) -> pd.Series:
    """Invert the log1p transform back to normal expected returns."""
    return np.expm1(pred_series)
