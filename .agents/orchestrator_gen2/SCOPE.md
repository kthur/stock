# Scope: Price Prediction Feature Upgrades (orchestrator_gen2)

## Architecture
The scope of this update covers:
1. **Data Layer & Feature Engineering**:
   - Calculate stock-level market cap, volume, floating shares, and floating value.
   - Calculate market-level baseline totals daily across the stock universe.
   - Compute normalized features (`norm_market_cap`, `norm_floating_value`, `norm_volume`) for each stock.
   - Maintain static fallback dict (`FALLBACK_METADATA`) for offline/testing scenarios.
2. **Prediction Models**:
   - Update `OnDevicePredictionModel` and feature builder in `prediction_model.py` to use 9 features (adding the 3 normalized features).
   - Update `screener.py` and `macro_predictor.py` to compute and include these features.
   - Retrain/update prediction scripts and pipelines.
3. **Strategy & Scoring Engine**:
   - Update `HybridStrategyEngine` in `strategy_engine.py` to use updated models and incorporate volume expansion momentum (bonus/penalty) and floating value liquidity checks.
   - Update `post_market_scoring.py` to pre-fetch all historical prices, apply cross-sectional normalization, and score the universe.
4. **Verification**:
   - Update documentation in `docs/SYSTEM_ARCHITECTURE.md` and `docs/ALGORITHMS_AND_STRATEGY.md`.
   - Add unit/integration tests to verify normalized feature calculations, training, and scoring pipeline.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Feature Engineering | Compute stock and normalized market features, build fallback metadata. | None | DONE |
| 2 | Model updates | Incorporate 9 features in OnDevicePredictionModel, macro predictor and screener. | M1 | DONE |
| 3 | Strategy/Scoring updates | Update HybridStrategyEngine indicator/allocation logic & post_market_scoring pipeline. | M2 | DONE |
| 4 | E2E Testing & Verification | Implement unit/integration tests, run E2E test track, and run Forensic Audit. | M3 | DONE |

## Interface Contracts
### Market Normalization
- Signature: `OnDevicePredictionModel.apply_market_normalization(self, prices_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]`
- Inputs: Dict of symbol to DataFrame containing price, volume, and stock-level metadata columns.
- Outputs: Dict of symbol to DataFrame with added columns: `norm_market_cap`, `norm_floating_value`, `norm_volume`.

### Technical Indicator Volume Expansion
- Signature: `HybridStrategyEngine._compute_technical_indicators(self, price_bars: list, volume_bars: list = None, floating_shares: float = None) -> Dict`
- Logic:
  - If 5-day volume SMA > 1.5 * 20-day volume SMA (volume expansion):
    - Trend positive (EMA20 > EMA50 or MACD > 0) -> +0.05 bonus.
    - Trend negative -> -0.05 penalty.
  - If floating value is very low -> cap/decrease confidence score.

## Code Layout
- Main prediction model: `trading_system/src/ai/prediction_model.py`
- Macro predictor & Screener: `trading_system/src/analysis/macro_predictor.py`, `trading_system/src/analysis/screener.py`
- Strategy engine: `trading_system/src/core/strategy_engine.py`
- Post market scoring: `trading_system/scripts/post_market_scoring.py`
- Documentation: `trading_system/docs/`
- Tests: `trading_system/tests/`
