"""
Asset Allocation strategies for portfolio construction.

Supports:
- equal_weight: Each asset receives equal weight (1/N).
- risk_parity: Weights inversely proportional to asset volatility.
- momentum: Weights proportional to recent total return.
"""

import math
from typing import Dict, List


def _compute_returns(prices: List[float]) -> List[float]:
    """Compute period-over-period simple returns from a price series."""
    if len(prices) < 2:
        return []
    return [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]


def _stdev(values: List[float]) -> float:
    """Population standard deviation."""
    n = len(values)
    if n == 0:
        return 0.0
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    return math.sqrt(variance)


def _normalize(weights: Dict[str, float]) -> Dict[str, float]:
    """
    Normalize a dict of weights so they sum exactly to 1.0.
    Uses Fraction-style correction on the last key to avoid floating-point drift.
    """
    total = sum(weights.values())
    if total == 0:
        # Fallback: equal weight
        n = len(weights)
        return {k: 1.0 / n for k in weights}

    # Scale all weights
    scaled = {k: v / total for k, v in weights.items()}

    # Force exact sum = 1.0 by adjusting the last key
    keys = list(scaled.keys())
    running_sum = sum(scaled[k] for k in keys[:-1])
    scaled[keys[-1]] = 1.0 - running_sum

    return scaled


class AssetAllocator:
    """
    Portfolio asset allocator supporting multiple weighting strategies.

    Args:
        strategy: One of 'equal_weight', 'risk_parity', 'momentum', 'black_litterman'.
    """

    SUPPORTED_STRATEGIES = ("equal_weight", "risk_parity", "momentum", "black_litterman")

    def __init__(self, strategy: str = "equal_weight"):
        if strategy not in self.SUPPORTED_STRATEGIES:
            raise ValueError(f"Unknown strategy '{strategy}'. Supported: {self.SUPPORTED_STRATEGIES}")
        self.strategy = strategy

    # ------------------------------------------------------------------
    def allocate(self, price_data: Dict[str, List[float]], predicted_returns: dict | None = None) -> Dict[str, float]:
        """
        Compute portfolio weights from price data.

        Args:
            price_data: Mapping of ticker -> list of prices (oldest to newest).
                        Each list must have at least 2 prices.
            predicted_returns: Optional mapping of ticker -> expected return (float) for Black-Litterman.

        Returns:
            Dict mapping ticker -> weight (float), weights sum exactly to 1.0.

        Raises:
            ValueError: If price_data is empty or prices are invalid.
        """
        if not price_data:
            raise ValueError("price_data must not be empty")

        tickers = list(price_data.keys())

        # Validate each price series
        for ticker, prices in price_data.items():
            if len(prices) < 2:
                raise ValueError(f"Ticker '{ticker}' must have at least 2 price points, got {len(prices)}")

        if self.strategy == "equal_weight":
            return self._equal_weight(tickers)

        elif self.strategy == "risk_parity":
            return self._risk_parity(price_data)

        elif self.strategy == "momentum":
            return self._momentum(price_data)

        elif self.strategy == "black_litterman":
            return self._black_litterman(price_data, predicted_returns)

        else:
            # Should never reach here due to __init__ validation
            raise ValueError(f"Unknown strategy: {self.strategy}")

    # ------------------------------------------------------------------
    def _equal_weight(self, tickers: List[str]) -> Dict[str, float]:
        """Assign equal weight to every asset."""
        raw = {ticker: 1.0 for ticker in tickers}
        return _normalize(raw)

    def _risk_parity(self, price_data: Dict[str, List[float]]) -> Dict[str, float]:
        """
        True Risk Parity (Equal Risk Contribution) weighting using numerical optimization.
        """
        import numpy as np

        from src.analysis.portfolio_optimizer import calculate_risk_parity_weights

        tickers = list(price_data.keys())
        n = len(tickers)
        if n == 0:
            return {}
        if n == 1:
            return {tickers[0]: 1.0}

        # a. Compute period simple returns for each ticker using _compute_returns
        returns_dict = {}
        for ticker in tickers:
            returns_dict[ticker] = _compute_returns(price_data[ticker])

        # b. Align returns series to shared minimum historical length. If < 2, fallback to equal weighting.
        min_len = min(len(r) for r in returns_dict.values()) if returns_dict else 0
        if min_len < 2:
            return self._equal_weight(tickers)

        returns_arr = np.array([returns_dict[t][:min_len] for t in tickers])

        # c. Compute the sample covariance matrix using numpy.cov
        cov_matrix = np.cov(returns_arr)

        # d. Call calculate_risk_parity_weights to get the weights
        weights = calculate_risk_parity_weights(cov_matrix)

        # e. Return normalized weights using the existing _normalize helper
        weights_dict = {tickers[i]: float(weights[i]) for i in range(n)}
        return _normalize(weights_dict)

    def _momentum(self, price_data: Dict[str, List[float]]) -> Dict[str, float]:
        """
        Momentum weighting proportional to total return over the price series.
        total_return_i = last_price / first_price
        Negative or zero returns are floored at a small positive epsilon.
        """
        MIN_RETURN = 1e-9  # floor for non-positive returns

        raw: Dict[str, float] = {}
        for ticker, prices in price_data.items():
            first = prices[0]
            last = prices[-1]
            if first <= 0:
                total_return = MIN_RETURN
            else:
                total_return = last / first
                # Convert to positive relative return (floor at epsilon)
                total_return = max(MIN_RETURN, total_return)
            raw[ticker] = total_return

        return _normalize(raw)

    def _black_litterman(self, price_data: Dict[str, List[float]], predicted_returns: dict | None = None) -> Dict[str, float]:
        """
        Black-Litterman portfolio optimization ensembled with return predictions.
        """
        import numpy as np
        from src.analysis.portfolio_optimizer import calculate_black_litterman_weights

        tickers = list(price_data.keys())
        n = len(tickers)
        if n == 0:
            return {}
        if n == 1:
            return {tickers[0]: 1.0}

        # Compute period simple returns for each ticker
        returns_dict = {}
        for ticker in tickers:
            returns_dict[ticker] = _compute_returns(price_data[ticker])

        # Align returns
        min_len = min(len(r) for r in returns_dict.values()) if returns_dict else 0
        if min_len < 2:
            return self._equal_weight(tickers)

        returns_arr = np.array([returns_dict[t][:min_len] for t in tickers])

        # Compute covariance matrix
        cov_matrix = np.cov(returns_arr)

        # Prepare predicted returns vector Q (views)
        pred_list = []
        for t in tickers:
            if predicted_returns and t in predicted_returns:
                pred_list.append(float(predicted_returns[t]))
            else:
                # Default to historical momentum return as view
                prices = price_data[t]
                if prices[0] > 0:
                    pred_list.append(max(0.0, (prices[-1] / prices[0]) - 1.0))
                else:
                    pred_list.append(0.0)

        predicted_arr = np.array(pred_list)

        # Compute Black-Litterman weights
        weights = calculate_black_litterman_weights(cov_matrix, predicted_arr)

        weights_dict = {tickers[i]: float(weights[i]) for i in range(n)}
        return _normalize(weights_dict)


# ─── Convenience function ─────────────────────────────────────────────────────


def allocate_assets(
    prices_dict: Dict[str, List[float]],
    strategy: str = "equal_weight",
    predicted_returns: dict | None = None,
) -> Dict[str, float]:
    """
    Convenience function to compute portfolio weights.

    Args:
        prices_dict: Mapping of ticker -> list of historical prices.
        strategy: Allocation strategy ('equal_weight', 'risk_parity', 'momentum', 'black_litterman').
        predicted_returns: Optional mapping of ticker -> expected return (float).

    Returns:
        Dict mapping ticker -> weight. Weights sum exactly to 1.0.
    """
    allocator = AssetAllocator(strategy=strategy)
    return allocator.allocate(prices_dict, predicted_returns)
