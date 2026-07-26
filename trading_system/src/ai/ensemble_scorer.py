import logging
import typing
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Union, Set, List

try:
    from sklearn.isotonic import IsotonicRegression
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False


logger = logging.getLogger(__name__)

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


class EnsembleScoringEngine:
    """
    Ensembles 5 strategy predictions (Regression, Surge Classifier, Lead-Lag, VCP Rule Detector, VCP ML Predictor)
    using 2D regime matrix weights and dynamic exponential Sharpe weighting.
    """

    # Dynamic Weight Configuration per 1D Market Regime (0: BEAR, 1: SIDEWAYS, 2: BULL)
    # Dynamic Weight Configuration per 1D Market Regime (9 Strategies)
    REGIME_WEIGHTS = {
        0: {  # BEAR (Defensive: high weight on regression, RIM valuation, stat_arb)
            'regression': 0.30,
            'surge': 0.05,
            'lead_lag': 0.05,
            'vcp_rule': 0.05,
            'vcp_ml': 0.05,
            'lstm': 0.05,
            'stat_arb': 0.15,
            'sector_rotation': 0.10,
            'rim_valuation': 0.20
        },
        1: {  # SIDEWAYS (Rotation: high weight on Stat-Arb, RIM Valuation, Sector Rotation)
            'regression': 0.15,
            'surge': 0.05,
            'lead_lag': 0.10,
            'vcp_rule': 0.05,
            'vcp_ml': 0.10,
            'lstm': 0.15,
            'stat_arb': 0.15,
            'sector_rotation': 0.10,
            'rim_valuation': 0.15
        },
        2: {  # BULL (Aggressive: high weight on Surge, VCP ML, LSTM, Sector Rotation)
            'regression': 0.08,
            'surge': 0.22,
            'lead_lag': 0.05,
            'vcp_rule': 0.05,
            'vcp_ml': 0.18,
            'lstm': 0.14,
            'stat_arb': 0.05,
            'sector_rotation': 0.15,
            'rim_valuation': 0.08
        }
    }

    # 2D Market Regime Matrix Weights (6 Combo States across 9 Strategies)
    REGIME_2D_WEIGHTS = {
        'BEAR_LOW_VOL': {
            'regression': 0.30,
            'surge': 0.05,
            'lead_lag': 0.05,
            'vcp_rule': 0.05,
            'vcp_ml': 0.05,
            'lstm': 0.05,
            'stat_arb': 0.15,
            'sector_rotation': 0.10,
            'rim_valuation': 0.20
        },
        'BEAR_HIGH_VOL': {
            'regression': 0.35,
            'surge': 0.00,
            'lead_lag': 0.05,
            'vcp_rule': 0.05,
            'vcp_ml': 0.05,
            'lstm': 0.05,
            'stat_arb': 0.20,
            'sector_rotation': 0.05,
            'rim_valuation': 0.20
        },
        'SIDEWAYS_LOW_VOL': {
            'regression': 0.15,
            'surge': 0.05,
            'lead_lag': 0.10,
            'vcp_rule': 0.05,
            'vcp_ml': 0.10,
            'lstm': 0.15,
            'stat_arb': 0.15,
            'sector_rotation': 0.10,
            'rim_valuation': 0.15
        },
        'SIDEWAYS_HIGH_VOL': {
            'regression': 0.15,
            'surge': 0.05,
            'lead_lag': 0.10,
            'vcp_rule': 0.05,
            'vcp_ml': 0.10,
            'lstm': 0.10,
            'stat_arb': 0.20,
            'sector_rotation': 0.10,
            'rim_valuation': 0.15
        },
        'BULL_LOW_VOL': {
            'regression': 0.08,
            'surge': 0.22,
            'lead_lag': 0.05,
            'vcp_rule': 0.05,
            'vcp_ml': 0.18,
            'lstm': 0.14,
            'stat_arb': 0.05,
            'sector_rotation': 0.15,
            'rim_valuation': 0.08
        },
        'BULL_HIGH_VOL': {
            'regression': 0.05,
            'surge': 0.25,
            'lead_lag': 0.05,
            'vcp_rule': 0.05,
            'vcp_ml': 0.18,
            'lstm': 0.14,
            'stat_arb': 0.05,
            'sector_rotation': 0.10,
            'rim_valuation': 0.08
        }
    }

    # 3D Macro Regime Override Weights (LIQUIDITY_SQUEEZE, HIGH_YIELD_BULL, HIGH_YIELD_BEAR)
    MACRO_WEIGHT_MODIFIERS = {
        'LIQUIDITY_SQUEEZE': {
            'stat_arb': +0.10,
            'vcp_rule': +0.05,
            'surge': -0.10,
            'sector_rotation': -0.05
        },
        'HIGH_YIELD_BULL': {
            'sector_rotation': +0.10,
            'surge': +0.05,
            'lead_lag': -0.10,
            'stat_arb': -0.05
        },
        'HIGH_YIELD_BEAR': {
            'regression': +0.10,
            'stat_arb': +0.10,
            'surge': -0.15,
            'vcp_ml': -0.05
        }
    }

    def __init__(self, config=None, alpha_smoothing: float = 0.2):
        # Support TradingConfig for centralized constant management
        self.config = config
        self.alpha_smoothing = alpha_smoothing
        self._return_multiplier = 20.0  # default
        if config is not None:
            self._return_multiplier = getattr(config, "ensemble_return_multiplier", 20.0)
        # Per-strategy Isotonic Regression calibrators (fitted via fit_calibrators)
        self._calibrators: Dict[str, Any] = {}
        self._prev_weights: Optional[Dict[str, float]] = None

        # Attempt to load Optuna-tuned 2D regime weights from tuned_params.json

        try:
            from pathlib import Path
            import json
            params_file = Path(__file__).resolve().parent.parent.parent / "models" / "tuned_params.json"
            if params_file.exists():
                with open(params_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and 'regime_2d_weights' in data:
                        tuned = data['regime_2d_weights']
                        for k, v in tuned.items():
                            if k in self.REGIME_2D_WEIGHTS:
                                self.REGIME_2D_WEIGHTS[k].update(v)
                        logger.info("Loaded Optuna tuned 2D regime weights from tuned_params.json")
        except Exception as e:
            logger.warning(f"Could not load tuned_params.json: {e}")

    # ------------------------------------------------------------------
    # Phase 4-A: Isotonic Regression Probability Calibration
    # ------------------------------------------------------------------

    def fit_calibrators(
        self,
        strategy_scores: Dict[str, np.ndarray],
        true_labels: np.ndarray,
    ) -> None:
        """Fit per-strategy Isotonic Regression calibrators.

        Args:
            strategy_scores: dict of {strategy_name: 1-D score array (N,)}
                Keys must be subset of: 'regression', 'surge', 'lead_lag', 'vcp_rule', 'vcp_ml'.
            true_labels: binary outcome array (1 = >20% gain, 0 = not), shape (N,).
        """
        if not _HAS_SKLEARN:
            logger.warning("scikit-learn not available; calibration skipped.")
            return
        for strategy, scores in strategy_scores.items():
            try:
                s = np.asarray(scores, dtype=float)
                y = np.asarray(true_labels, dtype=float)
                mask = np.isfinite(s) & np.isfinite(y)
                if mask.sum() < 20:
                    logger.warning(f"Calibrator for '{strategy}': too few samples ({mask.sum()}), skipping.")
                    continue
                cal = IsotonicRegression(out_of_bounds="clip", increasing=True)
                cal.fit(s[mask], y[mask])
                self._calibrators[strategy] = cal
                logger.info(f"Fitted Isotonic calibrator for strategy '{strategy}' on {mask.sum()} samples.")
            except Exception as e:
                logger.warning(f"Calibrator fitting failed for '{strategy}': {e}")

    def calibrate_scores(
        self,
        strategy: str,
        scores: np.ndarray,
    ) -> np.ndarray:
        """Apply per-strategy calibrator if available; otherwise return scores unchanged."""
        cal = self._calibrators.get(strategy)
        if cal is None:
            return scores
        try:
            s = np.asarray(scores, dtype=float)
            out = cal.predict(np.where(np.isfinite(s), s, 0.0))
            return np.asarray(np.clip(out, 0.0, 1.0))
        except Exception as e:
            logger.warning(f"Calibration predict failed for '{strategy}': {e}")
            return np.asarray(scores)

    def has_calibrators(self) -> bool:
        """Returns True if at least one strategy calibrator has been fitted."""
        return len(self._calibrators) > 0

    def compute_rolling_sharpe(self, strategy_returns: Dict[str, Union[pd.Series, list]],
                              window: int = 20,
                              risk_free_rate: float = 0.0) -> Dict[str, float]:
        """
        Computes recent rolling Sharpe ratio for each strategy.
        Sharpe_i = (mean(R_i) - r_f) / (std(R_i) + 1e-6) * sqrt(252)
        """
        sharpes = {}
        for strategy, ret_data in strategy_returns.items():
            try:
                s = pd.Series(ret_data).dropna()
                if len(s) >= 2:
                    recent = s.tail(window)
                    mean_ret = float(recent.mean())
                    std_ret = float(recent.std())
                    if std_ret < 1e-8:
                        std_ret = 1e-6
                    sharpe = ((mean_ret - risk_free_rate) / std_ret) * np.sqrt(252)
                    sharpes[strategy] = float(sharpe)
                else:
                    sharpes[strategy] = 0.0
            except Exception as e:
                logger.warning(f"Error calculating rolling Sharpe for {strategy}: {e}")
                sharpes[strategy] = 0.0
        return sharpes

    def apply_vix_override(self, weights: Dict[str, float], vix_val: Optional[float] = None) -> Dict[str, float]:
        """
        Fast VIX Shock Override: Adjusts strategy weights in high volatility environments.
        - vix_val > 30.0 (High fear): Reduce surge/sector_rotation, increase regression/stat_arb
        - vix_val > 40.0 (Extreme panic): Maximize stat_arb/regression defensiveness
        """
        if vix_val is None or vix_val <= 25.0:
            return weights

        w = dict(weights)
        if vix_val > 30.0:
            w['surge'] = max(0.0, w.get('surge', 0.15) - 0.10)
            w['sector_rotation'] = max(0.0, w.get('sector_rotation', 0.10) - 0.05)
            w['regression'] = w.get('regression', 0.20) + 0.10
            w['stat_arb'] = w.get('stat_arb', 0.10) + 0.05

        if vix_val > 40.0:
            w['vcp_ml'] = max(0.0, w.get('vcp_ml', 0.15) - 0.10)
            w['stat_arb'] = w.get('stat_arb', 0.10) + 0.10

        total = sum(w.values())
        return {k: v / total for k, v in w.items()} if total > 0 else weights

    def get_base_weights(self, regime: Union[int, str, dict], vix_val: Optional[float] = None) -> Dict[str, float]:
        """Resolves base weights from 1D, 2D, or 3D macro regime inputs, applying Fast VIX Override."""
        macro_label = None
        if isinstance(regime, dict):
            macro_label = regime.get('macro_label')
            if vix_val is None:
                vix_val = regime.get('vix_val')
            regime = regime.get('combo_2d_label') or regime.get('combo_label') or regime.get('direction_label', 'SIDEWAYS')

        if isinstance(regime, str) and regime in self.REGIME_2D_WEIGHTS:
            w = dict(self.REGIME_2D_WEIGHTS[regime])
        elif isinstance(regime, str):
            # Try parsing integer prefix or label matching
            if 'BEAR' in regime:
                reg_code = 0
            elif 'BULL' in regime:
                reg_code = 2
            else:
                reg_code = 1
            w = dict(self.REGIME_WEIGHTS.get(reg_code, self.REGIME_WEIGHTS[1]))
        else:
            reg_code = int(regime) if isinstance(regime, (int, np.integer)) else 1
            w = dict(self.REGIME_WEIGHTS.get(reg_code, self.REGIME_WEIGHTS[1]))

        # Apply 3D Macro Modifier if applicable
        if macro_label and macro_label in self.MACRO_WEIGHT_MODIFIERS:
            mods = self.MACRO_WEIGHT_MODIFIERS[macro_label]
            for strat, delta in mods.items():
                if strat in w:
                    w[strat] = max(0.0, w[strat] + delta)
            total_w = sum(w.values())
            if total_w > 0:
                w = {k: v / total_w for k, v in w.items()}

        res = {
            'regression': w.get('regression', 0.20),
            'surge': w.get('surge', 0.15),
            'lead_lag': w.get('lead_lag', 0.10),
            'vcp_rule': w.get('vcp_rule', 0.10),
            'vcp_ml': w.get('vcp_ml', 0.15),
            'lstm': w.get('lstm', 0.10),
            'stat_arb': w.get('stat_arb', 0.10),
            'sector_rotation': w.get('sector_rotation', 0.10)
        }

        # Apply VIX Fast Override if active
        res = self.apply_vix_override(res, vix_val=vix_val)

        total = sum(res.values())
        return {k: v / total for k, v in res.items()}

    def compute_dynamic_weights_from_sharpe(self, rolling_sharpes: Dict[str, float],
                                            regime: Union[int, str],
                                            gamma: float = 1.0) -> Dict[str, float]:
        """
        Dynamically adjusts strategy weights using recent rolling Sharpe ratios per strategy.
        Formula: w_i_dynamic = base_w_i * exp(gamma * Sharpe_i) / sum(base_w_j * exp(gamma * Sharpe_j))
        """
        base_weights = self.get_base_weights(regime)
        if not rolling_sharpes:
            return base_weights

        scores = {}
        for strategy, base_w in base_weights.items():
            sharpe = float(rolling_sharpes.get(strategy, 0.0))
            # Exponential Sharpe weighting multiplier: exp(gamma * Sharpe)
            multiplier = float(np.exp(gamma * np.clip(sharpe, -3.0, 3.0)))
            scores[strategy] = base_w * multiplier

        total_score = sum(scores.values())
        dynamic_weights = {k: v / total_score for k, v in scores.items()}

        # Apply EMA Weight Smoothing to prevent regime transition whipsaws
        if self._prev_weights is not None:
            smoothed = {}
            for k, target_w in dynamic_weights.items():
                prev_w = self._prev_weights.get(k, target_w)
                smoothed[k] = self.alpha_smoothing * target_w + (1 - self.alpha_smoothing) * prev_w
            tot_s = sum(smoothed.values())
            dynamic_weights = {k: v / tot_s for k, v in smoothed.items()}

        self._prev_weights = dict(dynamic_weights)
        logger.info(f"Dynamically adjusted Sharpe weights for Regime '{regime}' (gamma={gamma}): {dynamic_weights}")
        return dynamic_weights


    def calculate_ensemble_score(self,
                                 regime: Union[int, str],
                                 regression_df: pd.DataFrame,
                                 surge_df: pd.DataFrame,
                                 lead_lag_df: pd.DataFrame,
                                 vcp_ml_df: pd.DataFrame,
                                  vcp_rule_df: Optional[Union[pd.DataFrame, list]] = None,
                                  vcp_patterns_df: Optional[Union[pd.DataFrame, list]] = None,
                                  lstm_df: Optional[pd.DataFrame] = None,
                                  stat_arb_df: Optional[pd.DataFrame] = None,
                                  sector_df: Optional[pd.DataFrame] = None,
                                  rim_df: Optional[pd.DataFrame] = None,
                                  rolling_sharpes: Optional[Dict[str, float]] = None,
                                  gamma: float = 1.0,
                                  target_horizon: int = 20,
                                  sentiment_blacklist: Optional[Union[Set[str], List[str], Dict[str, Any]]] = None) -> pd.DataFrame:

        """
        Merges 9 strategy outputs (Regression, Surge, Lead-Lag, VCP Rule, VCP ML, LSTM, Stat-Arb, Sector Rotation, RIM Valuation)
        and calculates a unified dynamic weighted ensemble score [0, 1] and expected return proxy (%).
        """
        v_rule_input = vcp_patterns_df if vcp_patterns_df is not None else vcp_rule_df
        if isinstance(v_rule_input, list):
            v_rule_df = pd.DataFrame(v_rule_input) if v_rule_input else pd.DataFrame()
        else:
            v_rule_df = v_rule_input
        if rolling_sharpes:
            weights = self.compute_dynamic_weights_from_sharpe(rolling_sharpes, regime, gamma=gamma)
        else:
            weights = self.get_base_weights(regime)

        logger.info(f"Applying 9-Strategy Ensemble weights for Regime '{regime}': {weights}")

        # 1. Strategy 1: Regression
        if not regression_df.empty:
            reg_df = regression_df.copy()
            horizon_col: typing.Any = target_horizon
            if horizon_col not in reg_df.columns:
                num_cols = [c for c in reg_df.columns if isinstance(c, (int, float))]
                if num_cols:
                    horizon_col = min(num_cols, key=lambda x: abs(x - target_horizon))
                else:
                    horizon_col = reg_df.columns[-1]

            reg_df = reg_df[['symbol', horizon_col]].rename(columns={horizon_col: 'reg_pred'})
            if len(reg_df) > 1:
                reg_df['reg_score'] = reg_df['reg_pred'].rank(pct=True)
            else:
                reg_df['reg_score'] = 1.0
        else:
            reg_df = pd.DataFrame(columns=['symbol', 'reg_pred', 'reg_score'])

        # 2. Strategy 2: Surge Classifier
        if not surge_df.empty:
            s_df = surge_df.copy()
            surge_horizons = [1, 3, 5, 20]
            closest_surge_horizon = min(surge_horizons, key=lambda x: abs(x - target_horizon))
            s_col = f'surge_{closest_surge_horizon}d'
            if s_col not in s_df.columns:
                num_cols = [c for c in s_df.columns if c != 'symbol' and pd.api.types.is_numeric_dtype(s_df[c])]
                s_col = str(num_cols[-1]) if num_cols else str(s_df.columns[-1])
            s_df = s_df[['symbol', s_col]].rename(columns={s_col: 'surge_score'})
        else:
            s_df = pd.DataFrame(columns=['symbol', 'surge_score'])

        # 3. Strategy 3: Lead-Lag Scores
        if not lead_lag_df.empty:
            ll_df = lead_lag_df.copy()
            ll_col = 'lead_lag_score' if 'lead_lag_score' in ll_df.columns else ll_df.columns[-1]
            ll_df = ll_df[['symbol', ll_col]].rename(columns={ll_col: 'll_raw'})
            if len(ll_df) > 1:
                min_val = ll_df['ll_raw'].min()
                max_val = ll_df['ll_raw'].max()
                denom = (max_val - min_val) if max_val != min_val else 1.0
                ll_df['ll_score'] = (ll_df['ll_raw'] - min_val) / denom
            else:
                ll_df['ll_score'] = 1.0
        else:
            ll_df = pd.DataFrame(columns=['symbol', 'll_raw', 'll_score'])

        # 4. Strategy 4: VCP Rule Detector
        if v_rule_df is not None and not v_rule_df.empty:
            vr_df = v_rule_df.copy()

            if 'vcp_score' in vr_df.columns:
                vr_df['vcp_rule_score'] = vr_df['vcp_score'] / 100.0
            elif 'is_vcp' in vr_df.columns:
                vr_df['vcp_rule_score'] = vr_df['is_vcp'].astype(float)
            else:
                num_cols = [c for c in vr_df.columns if c != 'symbol' and pd.api.types.is_numeric_dtype(vr_df[c])]
                vr_col = num_cols[-1] if num_cols else vr_df.columns[-1]
                vr_df['vcp_rule_score'] = vr_df[vr_col]
            vr_df = vr_df[['symbol', 'vcp_rule_score']]
        else:
            vr_df = pd.DataFrame(columns=['symbol', 'vcp_rule_score'])

        # 5. Strategy 5: VCP ML Predictor
        if not vcp_ml_df.empty:
            v_df = vcp_ml_df.copy()
            surge_horizons = [1, 3, 5, 20]
            closest_vcp_horizon = min(surge_horizons, key=lambda x: abs(x - target_horizon))
            v_col = f'vcp_{closest_vcp_horizon}d'
            if v_col not in v_df.columns:
                num_cols = [c for c in v_df.columns if c != 'symbol' and pd.api.types.is_numeric_dtype(v_df[c])]
                v_col = str(num_cols[-1]) if num_cols else str(v_df.columns[-1])
            v_df = v_df[['symbol', v_col]].rename(columns={v_col: 'vcp_ml_score'})
        else:
            v_df = pd.DataFrame(columns=['symbol', 'vcp_ml_score'])

        # 6. Strategy 6: Strict Causal LSTM
        if lstm_df is not None and not lstm_df.empty:
            l_df = lstm_df.copy()
            l_col = 'lstm_score' if 'lstm_score' in l_df.columns else l_df.columns[-1]
            l_df = l_df[['symbol', l_col]].rename(columns={l_col: 'lstm_score'})
        else:
            l_df = pd.DataFrame(columns=['symbol', 'lstm_score'])

        # 7. Strategy 7: Stat-Arb Z-score
        if stat_arb_df is not None and not stat_arb_df.empty:
            sa_df = stat_arb_df.copy()
            sa_col = 'stat_arb_score' if 'stat_arb_score' in sa_df.columns else sa_df.columns[-1]
            sa_df = sa_df[['symbol', sa_col]].rename(columns={sa_col: 'stat_arb_score'})
        else:
            sa_df = pd.DataFrame(columns=['symbol', 'stat_arb_score'])

        # 8. Strategy 8: Sector Rotation Momentum
        if sector_df is not None and not sector_df.empty:
            sec_df = sector_df.copy()
            sec_col = 'sector_score' if 'sector_score' in sec_df.columns else sec_df.columns[-1]
            sec_df = sec_df[['symbol', sec_col]].rename(columns={sec_col: 'sector_score'})
        else:
            sec_df = pd.DataFrame(columns=['symbol', 'sector_score'])

        # 9. Strategy 9: RIM Valuation Score
        if rim_df is not None and not rim_df.empty:
            r_val_df = rim_df.copy()
            r_col = 'rim_score' if 'rim_score' in r_val_df.columns else r_val_df.columns[-1]
            r_val_df = r_val_df[['symbol', r_col]].rename(columns={r_col: 'rim_score'})
        else:
            r_val_df = pd.DataFrame(columns=['symbol', 'rim_score'])

        # Outer join all 9 strategies
        merged = reg_df.merge(s_df, on='symbol', how='outer')
        merged = merged.merge(ll_df, on='symbol', how='outer')
        merged = merged.merge(vr_df, on='symbol', how='outer')
        merged = merged.merge(v_df, on='symbol', how='outer')
        merged = merged.merge(l_df, on='symbol', how='outer')
        merged = merged.merge(sa_df, on='symbol', how='outer')
        merged = merged.merge(sec_df, on='symbol', how='outer')
        merged = merged.merge(r_val_df, on='symbol', how='outer')

        # Fill NaNs with 0.0 or neutral 0.5
        fill_cols = ['reg_pred', 'reg_score', 'surge_score', 'll_raw', 'll_score', 'vcp_rule_score', 'vcp_ml_score', 'lstm_score', 'stat_arb_score', 'sector_score', 'rim_score']
        for col in fill_cols:
            if col in merged.columns:
                merged[col] = merged[col].fillna(0.0)
            else:
                merged[col] = 0.0

        # Phase 4-A: Apply Isotonic Regression calibration if calibrators are fitted
        if self.has_calibrators():
            for strategy_col in [
                ('regression', 'reg_score'),
                ('surge', 'surge_score'),
                ('lead_lag', 'll_score'),
                ('vcp_rule', 'vcp_rule_score'),
                ('vcp_ml', 'vcp_ml_score'),
                ('lstm', 'lstm_score'),
                ('stat_arb', 'stat_arb_score'),
                ('sector_rotation', 'sector_score'),
                ('rim_valuation', 'rim_score'),
            ]:
                strategy_name, col = strategy_col
                if col in merged.columns and strategy_name in self._calibrators:
                    merged[col] = self.calibrate_scores(strategy_name, merged[col].values)

        # Calculate final 9-strategy weighted score [0, 1]
        merged['ensemble_score'] = (
            weights.get('regression', 0.15) * merged['reg_score'] +
            weights.get('surge', 0.15) * merged['surge_score'] +
            weights.get('lead_lag', 0.05) * merged['ll_score'] +
            weights.get('vcp_rule', 0.05) * merged['vcp_rule_score'] +
            weights.get('vcp_ml', 0.15) * merged['vcp_ml_score'] +
            weights.get('lstm', 0.15) * merged['lstm_score'] +
            weights.get('stat_arb', 0.10) * merged['stat_arb_score'] +
            weights.get('sector_rotation', 0.10) * merged['sector_score'] +
            weights.get('rim_valuation', 0.10) * merged['rim_score']
        )

        # Scale Ensemble Score to Return Proxy (%)
        raw_exp_ret = merged['ensemble_score'] * self._return_multiplier

        # Apply Market-specific Transaction Cost & Slippage Deductions
        slippage = getattr(self.config, 'slippage_krx_market_order', 0.005) if self.config is not None else 0.005

        def _get_cost_pct(symbol: str) -> float:
            if symbol.isdigit() or symbol.endswith(('.KS', '.KQ', '.KN')):
                if symbol.endswith('.KN'):
                    return 0.0080 + slippage
                elif symbol.endswith('.KQ'):
                    return 0.0050 + slippage
                return 0.0035 + slippage
            return 0.0010

        cost_series = merged['symbol'].apply(_get_cost_pct)
        merged['ensemble_expected_return'] = (raw_exp_ret - cost_series * 100.0).clip(lower=0.0)

        # Apply Sentiment Blacklist filter (zero-weighting for critical disclosure risk)
        if sentiment_blacklist:
            b_set = set(sentiment_blacklist.keys()) if isinstance(sentiment_blacklist, dict) else set(sentiment_blacklist)
            if b_set:
                mask = merged['symbol'].isin(b_set)
                merged.loc[mask, 'ensemble_score'] = 0.0
                merged.loc[mask, 'ensemble_expected_return'] = 0.0
                logger.info(f"[ENSEMBLE SENTIMENT FILTER] Zero-weighted {mask.sum()} blacklisted symbols.")

        # Sort by ensemble score descending
        merged = merged.sort_values(by='ensemble_score', ascending=False).reset_index(drop=True)
        return merged

