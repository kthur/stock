import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Union, Set, List

try:
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

from .meta_ensemble_learner import MetaEnsembleLearner
from .correlation_monitor import StrategyCorrelationMonitor
from .factor_suppression import RegimeFactorSuppressionEngine
from .factor_orthogonalizer import FactorOrthogonalizerEngine



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
    # Dynamic Weight Configuration per 1D Market Regime (17 Strategies)
    REGIME_WEIGHTS = {
        0: {  # BEAR (Defensive)
            'regression': 0.16,
            'surge': 0.02,
            'lead_lag': 0.02,
            'vcp_rule': 0.02,
            'vcp_ml': 0.02,
            'lstm': 0.03,
            'stat_arb': 0.09,
            'sector_rotation': 0.05,
            'rim_valuation': 0.11,
            'event_driven': 0.04,
            'mq_factor': 0.07,
            'iv_skew': 0.04,
            'order_flow': 0.03,
            'short_term_reversal': 0.05,
            'arm_factor': 0.06,
            'card_factor': 0.07,
            'latr_factor': 0.06,
            'inst_foreign_sector': 0.06
        },
        1: {  # SIDEWAYS (Rotation)
            'regression': 0.07,
            'surge': 0.03,
            'lead_lag': 0.05,
            'vcp_rule': 0.03,
            'vcp_ml': 0.05,
            'lstm': 0.07,
            'stat_arb': 0.09,
            'sector_rotation': 0.06,
            'rim_valuation': 0.07,
            'event_driven': 0.06,
            'mq_factor': 0.06,
            'iv_skew': 0.03,
            'order_flow': 0.04,
            'short_term_reversal': 0.04,
            'arm_factor': 0.06,
            'card_factor': 0.06,
            'latr_factor': 0.06,
            'inst_foreign_sector': 0.07
        },
        2: {  # BULL (Aggressive)
            'regression': 0.04,
            'surge': 0.11,
            'lead_lag': 0.03,
            'vcp_rule': 0.03,
            'vcp_ml': 0.09,
            'lstm': 0.07,
            'stat_arb': 0.03,
            'sector_rotation': 0.07,
            'rim_valuation': 0.05,
            'event_driven': 0.07,
            'mq_factor': 0.07,
            'iv_skew': 0.02,
            'order_flow': 0.04,
            'short_term_reversal': 0.02,
            'arm_factor': 0.07,
            'card_factor': 0.05,
            'latr_factor': 0.06,
            'inst_foreign_sector': 0.08
        }
    }

    # 2D Market Regime Matrix Weights (6 Combo States across 18 Strategies)
    REGIME_2D_WEIGHTS = {
        'BEAR_LOW_VOL': {
            'regression': 0.16,
            'surge': 0.02,
            'lead_lag': 0.02,
            'vcp_rule': 0.02,
            'vcp_ml': 0.02,
            'lstm': 0.03,
            'stat_arb': 0.09,
            'sector_rotation': 0.05,
            'rim_valuation': 0.11,
            'event_driven': 0.04,
            'mq_factor': 0.07,
            'iv_skew': 0.04,
            'order_flow': 0.03,
            'short_term_reversal': 0.05,
            'arm_factor': 0.06,
            'card_factor': 0.07,
            'latr_factor': 0.06,
            'inst_foreign_sector': 0.06
        },
        'BEAR_HIGH_VOL': {
            'regression': 0.17,
            'surge': 0.00,
            'lead_lag': 0.02,
            'vcp_rule': 0.02,
            'vcp_ml': 0.02,
            'lstm': 0.03,
            'stat_arb': 0.11,
            'sector_rotation': 0.03,
            'rim_valuation': 0.11,
            'event_driven': 0.04,
            'mq_factor': 0.07,
            'iv_skew': 0.04,
            'order_flow': 0.03,
            'short_term_reversal': 0.06,
            'arm_factor': 0.05,
            'card_factor': 0.08,
            'latr_factor': 0.06,
            'inst_foreign_sector': 0.05
        },
        'SIDEWAYS_LOW_VOL': {
            'regression': 0.07,
            'surge': 0.03,
            'lead_lag': 0.05,
            'vcp_rule': 0.03,
            'vcp_ml': 0.05,
            'lstm': 0.07,
            'stat_arb': 0.09,
            'sector_rotation': 0.06,
            'rim_valuation': 0.07,
            'event_driven': 0.06,
            'mq_factor': 0.06,
            'iv_skew': 0.03,
            'order_flow': 0.04,
            'short_term_reversal': 0.04,
            'arm_factor': 0.06,
            'card_factor': 0.06,
            'latr_factor': 0.06,
            'inst_foreign_sector': 0.07
        },
        'SIDEWAYS_HIGH_VOL': {
            'regression': 0.07,
            'surge': 0.03,
            'lead_lag': 0.05,
            'vcp_rule': 0.03,
            'vcp_ml': 0.05,
            'lstm': 0.05,
            'stat_arb': 0.11,
            'sector_rotation': 0.06,
            'rim_valuation': 0.07,
            'event_driven': 0.06,
            'mq_factor': 0.06,
            'iv_skew': 0.03,
            'order_flow': 0.04,
            'short_term_reversal': 0.04,
            'arm_factor': 0.05,
            'card_factor': 0.07,
            'latr_factor': 0.06,
            'inst_foreign_sector': 0.07
        },
        'BULL_LOW_VOL': {
            'regression': 0.04,
            'surge': 0.11,
            'lead_lag': 0.03,
            'vcp_rule': 0.03,
            'vcp_ml': 0.09,
            'lstm': 0.07,
            'stat_arb': 0.03,
            'sector_rotation': 0.07,
            'rim_valuation': 0.05,
            'event_driven': 0.07,
            'mq_factor': 0.07,
            'iv_skew': 0.02,
            'order_flow': 0.04,
            'short_term_reversal': 0.02,
            'arm_factor': 0.07,
            'card_factor': 0.05,
            'latr_factor': 0.06,
            'inst_foreign_sector': 0.08
        },
        'BULL_HIGH_VOL': {
            'regression': 0.03,
            'surge': 0.13,
            'lead_lag': 0.03,
            'vcp_rule': 0.03,
            'vcp_ml': 0.09,
            'lstm': 0.07,
            'stat_arb': 0.03,
            'sector_rotation': 0.05,
            'rim_valuation': 0.05,
            'event_driven': 0.07,
            'mq_factor': 0.07,
            'iv_skew': 0.02,
            'order_flow': 0.04,
            'short_term_reversal': 0.03,
            'arm_factor': 0.06,
            'card_factor': 0.06,
            'latr_factor': 0.06,
            'inst_foreign_sector': 0.08
        }
    }

    # 3D Macro Regime Override Weights (LIQUIDITY_SQUEEZE, HIGH_YIELD_BULL, HIGH_YIELD_BEAR,
    #                                    INFLATION_SHOCK, YIELD_INVERSION)
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
        },
        # ① 인플레이션 충격 (유가 + USD/KRW 환율 동시 상승): 국내 제조업 원가 이중 압박
        # MQ Factor(영업이익률/ROE 저하) 가중치 하향, RIM Valuation(안전마진) + Stat-Arb(시장 중립) 상향
        'INFLATION_SHOCK': {
            'mq_factor': -0.08,
            'surge': -0.05,
            'rim_valuation': +0.07,
            'stat_arb': +0.06
        },
        # ② 장단기 금리 역전 (US10Y < US5Y): 6~18개월 내 경기침체 선행 신호
        # 공격적 모멘텀 전략 축소, 가치평가(RIM) + 평균회귀(Stat-Arb) + 단기반전 방어
        'YIELD_INVERSION': {
            'regression': +0.08,
            'rim_valuation': +0.08,
            'stat_arb': +0.06,
            'short_term_reversal': +0.04,
            'surge': -0.12,
            'vcp_ml': -0.07,
            'sector_rotation': -0.07
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
        self._prev_regime: Optional[Union[int, str]] = None

        self.correlation_monitor = StrategyCorrelationMonitor()
        self.factor_suppression = RegimeFactorSuppressionEngine()
        self.orthogonalizer = FactorOrthogonalizerEngine(default_method='pca_symmetric')
        self.orthogonalizer_enabled = True

        # Milestone 4: Slippage execution feedback attributes
        self.slippage_metrics: Optional[Any] = None
        self.cost_scaling_factor: float = 1.0
        self.realized_market_impact_alpha: float = 0.50
        self.market_slippage_bps_map: Dict[str, float] = {}

        # Load Optuna-tuned 2D regime weights from tuned_params.json (if available)
        self._load_tuned_regime_weights()

        # Restore EMA weight continuity across pipeline runs (persisted below)
        self._load_prev_weights()

    def _load_prev_weights(self) -> None:
        """Load persisted EMA ensemble weights for cross-run continuity.

        The persisted regime is restored together with the weights so that a
        regime change between pipeline runs is detected as a shift (alpha=1.0)
        instead of smoothing stale weights from a different regime.
        """
        try:
            from pathlib import Path
            import json
            weights_file = Path(__file__).resolve().parent.parent.parent / "models" / "prev_weights.json"
            if weights_file.exists():
                with open(weights_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                weights_data = data.get("weights", data) if isinstance(data, dict) else data
                if isinstance(weights_data, dict) and weights_data:
                    self._prev_weights = {str(k): float(v) for k, v in weights_data.items()}
                    loaded_regime = data.get("regime") if isinstance(data, dict) else None
                    if loaded_regime:
                        self._prev_regime = loaded_regime
                    logger.info(
                        f"[EMA] Loaded previous ensemble weights from prev_weights.json "
                        f"({len(self._prev_weights)} strategies, regime={loaded_regime})"
                    )
        except Exception as e:
            logger.warning(f"Could not load prev_weights.json: {e}")

    def update_microstructure_costs(self, slippage_metrics: Any) -> None:
        """
        Dynamically updates microstructure cost parameters based on realized execution logs.
        """
        self.slippage_metrics = slippage_metrics
        if slippage_metrics is not None:
            self.cost_scaling_factor = max(0.50, min(3.00, float(getattr(slippage_metrics, 'cost_scaling_factor', 1.0))))
            self.realized_market_impact_alpha = float(getattr(slippage_metrics, 'market_impact_alpha', 0.50))
            self.market_slippage_bps_map = dict(getattr(slippage_metrics, 'market_slippage_map', {}))
            logger.info(
                f"[SLIPPAGE FEEDBACK] Updated microstructure costs: cost_scaling_factor={self.cost_scaling_factor:.2f}x, "
                f"impact_alpha={self.realized_market_impact_alpha:.4f}, avg_slippage={getattr(slippage_metrics, 'avg_slippage_bps', 5.0):.2f}bps "
                f"(sample_count={getattr(slippage_metrics, 'sample_count', 0)})"
            )

    def has_calibrators(self) -> bool:
        """Return True if calibrators dictionary is non-empty."""
        return bool(self._calibrators)

    def _load_tuned_regime_weights(self) -> None:
        """Load Optuna-tuned 2D regime weights from tuned_params.json into REGIME_2D_WEIGHTS."""
        try:
            from pathlib import Path
            import json
            params_file = Path(__file__).resolve().parent.parent.parent / "models" / "tuned_params.json"
            if params_file.exists():
                with open(params_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._tuned_params = data
                        if 'regime_2d_weights' in data:
                            tuned = data['regime_2d_weights']
                            for k, v in tuned.items():
                                if k in self.REGIME_2D_WEIGHTS:
                                    self.REGIME_2D_WEIGHTS[k].update(v)
                        logger.info("Loaded Optuna tuned 2D regime weights from tuned_params.json")
        except Exception as e:
            logger.warning(f"Could not load tuned_params.json: {e}")

    # ------------------------------------------------------------------
    # Phase 4-A: Hybrid Probability Calibration (Isotonic + Platt Scaling)
    # ------------------------------------------------------------------

    def fit_calibrators(
        self,
        strategy_scores: Dict[str, np.ndarray],
        true_labels: np.ndarray,
    ) -> None:
        """Fit per-strategy hybrid calibrators (Isotonic for N>=50, Platt Scaling for 20<=N<50).

        Args:
            strategy_scores: dict of {strategy_name: 1-D score array (N,)}
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
                n_samples = mask.sum()
                if n_samples < 20:
                    logger.warning(f"Calibrator for '{strategy}': too few samples ({n_samples}), skipping.")
                    continue

                if len(np.unique(y[mask])) < 2:
                    logger.warning(f"Calibrator for '{strategy}': target labels have single-class zero variance, skipping.")
                    continue

                if n_samples >= 50:
                    cal = IsotonicRegression(out_of_bounds="clip", increasing=True)
                    cal.fit(s[mask], y[mask])
                    self._calibrators[strategy] = ('isotonic', cal)
                    logger.info(f"Fitted Isotonic calibrator for strategy '{strategy}' on {n_samples} samples.")
                else:
                    cal = LogisticRegression(C=1.0, max_iter=100)
                    cal.fit(s[mask].reshape(-1, 1), y[mask])
                    self._calibrators[strategy] = ('platt', cal)
                    logger.info(f"Fitted Platt Scaling (Logistic) calibrator for strategy '{strategy}' on {n_samples} samples.")
            except Exception as e:
                logger.warning(f"Calibrator fitting failed for '{strategy}': {e}")

    def calibrate_scores(
        self,
        strategy: str,
        scores: np.ndarray,
    ) -> np.ndarray:
        """Apply per-strategy calibrator if available; otherwise return scores unchanged."""
        cal_tuple = self._calibrators.get(strategy)
        if cal_tuple is None:
            return scores
        cal_type, cal = cal_tuple
        try:
            s = np.asarray(scores, dtype=float)
            clean_s = np.where(np.isfinite(s), s, 0.0)
            if cal_type == 'isotonic':
                out = cal.predict(clean_s)
            else:
                out = cal.predict_proba(clean_s.reshape(-1, 1))[:, 1]
            return np.asarray(np.clip(out, 0.0, 1.0))
        except Exception as e:
            logger.warning(f"Calibration predict failed for '{strategy}': {e}")
            return np.asarray(scores)
    def compute_rolling_sharpe(self, strategy_returns: Dict[str, Union[List[float], pd.Series]],
                               window: int = 60,
                               risk_free_rate: float = 0.0,
                               min_obs: int = 2) -> Dict[str, float]:
        """
        Computes recent rolling Sharpe ratio for each strategy.
        Sharpe_i = (mean(R_i) - r_f/252) / (std(R_i) + 1e-6) * sqrt(252)

        Strategies with fewer than ``min_obs`` observations are reported as 0.0
        (no evidence yet) so they keep their neutral base weight instead of
        receiving a noisy Sharpe estimate.
        """
        sharpes = {}
        rf_daily = risk_free_rate / 252.0 if risk_free_rate > 0 else 0.0
        for strategy, ret_data in strategy_returns.items():
            try:
                s = pd.Series(ret_data).dropna()
                if len(s) >= max(2, min_obs):

                    recent = s.tail(window)
                    mean_ret = float(recent.mean())
                    std_ret = float(recent.std())
                    if std_ret < 1e-8:
                        std_ret = 1e-6
                    sharpe = ((mean_ret - rf_daily) / std_ret) * np.sqrt(252)
                    sharpes[strategy] = float(sharpe)
                else:
                    sharpes[strategy] = 0.0
            except Exception as e:
                logger.warning(f"Error calculating rolling Sharpe for {strategy}: {e}")
                sharpes[strategy] = 0.0
        return sharpes

    def apply_vix_override(self, weights: Dict[str, float], vix_val: Optional[float] = None) -> Dict[str, float]:
        if vix_val is None or vix_val <= 25.0:
            return weights

        w = dict(weights)
        if vix_val > 30.0:
            w['surge'] = max(0.0, w.get('surge', 0.15) - 0.10)
            w['sector_rotation'] = max(0.0, w.get('sector_rotation', 0.10) - 0.05)
            w['regression'] = w.get('regression', 0.20) + 0.10
            w['stat_arb'] = w.get('stat_arb', 0.10) + 0.05

        if vix_val > 40.0:
            w['surge'] = 0.0
            w['vcp_ml'] = 0.0
            w['stat_arb'] = w.get('stat_arb', 0.10) + 0.15
            w['rim_valuation'] = w.get('rim_valuation', 0.10) + 0.10

        total_w = sum(w.values())
        return {k: v / total_w for k, v in w.items()}

    def get_base_weights(self, regime: Union[int, str], vix_val: Optional[float] = None,
                         macro_label: Optional[str] = None) -> Dict[str, float]:
        """Return baseline strategy weights according to 1D integer regime or 2D string regime."""
        if isinstance(regime, str) and regime in self.REGIME_2D_WEIGHTS:
            w = dict(self.REGIME_2D_WEIGHTS[regime])
        elif isinstance(regime, int) and regime in self.REGIME_WEIGHTS:
            w = dict(self.REGIME_WEIGHTS[regime])
        else:
            w = dict(self.REGIME_2D_WEIGHTS['SIDEWAYS_LOW_VOL'])

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
            'regression': w.get('regression', 0.10),
            'surge': w.get('surge', 0.05),
            'lead_lag': w.get('lead_lag', 0.05),
            'vcp_rule': w.get('vcp_rule', 0.05),
            'vcp_ml': w.get('vcp_ml', 0.08),
            'lstm': w.get('lstm', 0.08),
            'stat_arb': w.get('stat_arb', 0.10),
            'sector_rotation': w.get('sector_rotation', 0.08),
            'rim_valuation': w.get('rim_valuation', 0.10),
            'event_driven': w.get('event_driven', 0.07),
            'mq_factor': w.get('mq_factor', 0.08),
            'iv_skew': w.get('iv_skew', 0.04),
            'order_flow': w.get('order_flow', 0.05),
            'short_term_reversal': w.get('short_term_reversal', 0.05),
            'arm_factor': w.get('arm_factor', 0.07),
            'card_factor': w.get('card_factor', 0.07),
            'latr_factor': w.get('latr_factor', 0.06),
            'inst_foreign_sector': w.get('inst_foreign_sector', 0.05),
        }

        # Apply VIX Fast Override if active
        res = self.apply_vix_override(res, vix_val=vix_val)

        total = sum(res.values())
        return {k: v / total for k, v in res.items()}

    def compute_dynamic_weights_from_sharpe(self, rolling_sharpes: Dict[str, float],
                                            regime: Union[int, str],
                                            gamma: float = 1.0,
                                            vix_val: Optional[float] = None) -> Dict[str, float]:
        """
        Dynamically adjusts strategy weights using recent rolling Sharpe ratios per strategy.
        Formula: w_i_dynamic = base_w_i * exp(gamma * Sharpe_i) / sum(base_w_j * exp(gamma * Sharpe_j))

        Cold-start behaviour: when no strategy has realized outcomes yet, the regime
        base weights are returned unchanged. Arbitrary "seed" Sharpes would present
        fabricated performance evidence as real — the dashboard must not claim dynamic
        weighting before the evidence exists.
        """
        base_weights = self.get_base_weights(regime, vix_val=vix_val)
        if not rolling_sharpes:
            return base_weights

        all_zero = all(abs(v) < 1e-8 for v in rolling_sharpes.values())
        if all_zero:
            logger.info(
                "[COLD-START] No realized strategy outcomes yet — using regime base weights (dynamic Sharpe weighting inactive)."
            )
            return base_weights

        # Cap the dynamic multiplier range: exp(gamma*clip(sharpe, ±L)) with
        # L = ln(sqrt(MAX_MULTIPLIER_RATIO))/gamma keeps the multiplier ratio
        # <= MAX_MULTIPLIER_RATIO (prevents e^6 ≈ 400:1 single-strategy dominance).
        max_multiplier_ratio = 5.0
        sharpe_clip = float(np.log(np.sqrt(max_multiplier_ratio)) / max(gamma, 1e-6))
        scores = {}
        for strategy, base_w in base_weights.items():
            sharpe = float(rolling_sharpes.get(strategy, 0.0))
            multiplier = float(np.exp(gamma * np.clip(sharpe, -sharpe_clip, sharpe_clip)))
            scores[strategy] = base_w * multiplier

        # Additionally bound the TOTAL weight ratio (base regime weights already
        # differ up to ~5x, so multiplier-only capping is not enough). Damping the
        # scores with a power < 1 preserves ordering while keeping any single
        # strategy from dominating the ensemble.
        max_total_ratio = 20.0
        _vals = np.array([scores[k] for k in scores], dtype=float)
        _vmin, _vmax = float(_vals.min()), float(_vals.max())
        if _vmin > 0.0 and _vmax / _vmin > max_total_ratio:
            _alpha = float(np.log(max_total_ratio) / np.log(_vmax / _vmin))
            scores = {k: scores[k] ** _alpha for k in scores}

        total_score = sum(scores.values())
        dynamic_weights = {k: v / total_score for k, v in scores.items()}

        # Detect regime transition to accelerate EMA weight smoothing (alpha = 1.0 on shift)
        current_regime_str = str(regime)
        is_regime_shift = (self._prev_regime is not None) and (str(self._prev_regime) != current_regime_str)
        self._prev_regime = regime

        eff_alpha = 1.0 if is_regime_shift else self.alpha_smoothing

        # Apply EMA Weight Smoothing to prevent regime transition whipsaws
        if self._prev_weights is not None:
            smoothed = {}
            for k, target_w in dynamic_weights.items():
                prev_w = self._prev_weights.get(k, target_w)
                smoothed[k] = eff_alpha * target_w + (1.0 - eff_alpha) * prev_w
            tot_s = sum(smoothed.values())
            dynamic_weights = {k: v / tot_s for k, v in smoothed.items()}

        self._prev_weights = dict(dynamic_weights)

        # Persist EMA weights to disk for continuity across runs (with the regime
        # that produced them, so cross-run regime shifts force alpha=1.0).
        try:
            from pathlib import Path
            import json
            models_dir = Path(__file__).resolve().parent.parent.parent / "models"
            models_dir.mkdir(exist_ok=True)
            with open(models_dir / "prev_weights.json", "w", encoding="utf-8") as f:
                json.dump({"regime": str(regime), "weights": self._prev_weights}, f, indent=2)
        except Exception as _se:
            logger.warning(f"Could not persist prev_weights.json: {_se}")

        logger.info(f"Dynamically adjusted Sharpe weights for Regime '{regime}' (gamma={gamma}): {dynamic_weights}")
        return dynamic_weights

    def get_regime_reasoning_summary(self, regime: Union[int, str], rolling_sharpes: Optional[Dict[str, float]] = None, decoupling_info: Optional[Dict[str, Any]] = None) -> str:
        """
        Generates a human-readable decision rationale summary for the selected 2D Regime,
        Dual Market Decoupling status, and 14-strategy dynamic weighting scheme.
        """
        reg_str = str(regime)
        lines = []
        lines.append("[2D Market Regime & Strategy Decision Rationale]")
        lines.append(f"• Selected Main Regime State: {reg_str}")

        if decoupling_info:
            status = decoupling_info.get('decoupling_status', 'COUPLED')
            corr = decoupling_info.get('correlation_20d', 1.0)
            us_reg = decoupling_info.get('us_regime', {}).get('combo_2d_label', 'N/A')
            kr_reg = decoupling_info.get('kr_regime', {}).get('combo_2d_label', 'N/A')
            lines.append(f"• Dual Market Correlation (20d): {corr:.2f} | Status: {status}")
            lines.append(f"  - US Market Regime (S&P500): {us_reg}")
            lines.append(f"  - KR Market Regime (KOSPI) : {kr_reg}")
            if status != "COUPLED":
                lines.append(f"  - Market Decoupling Warning: US and KR markets are moving in opposite directions ({status}). Market-specific weighting active.")

        if "BEAR" in reg_str:
            lines.append("  - Market Trend Rationale: Downward trend detected (20d index return < 0). Defensive allocation active.")
        elif "SIDEWAYS" in reg_str:
            lines.append("  - Market Trend Rationale: Range-bound consolidation detected. Rotation & Arbitrage strategies prioritized.")
        elif "BULL" in reg_str:
            lines.append("  - Market Trend Rationale: Upward momentum trend confirmed (20d index return > 0). Momentum & Surge strategies boosted.")

        if "HIGH_VOL" in reg_str:
            lines.append("  - Volatility State: HIGH_VOL (VIX >= 20.0 or High Realized Volatility). Increased weight on defensive Stat-Arb & RIM Valuation.")
        else:
            lines.append("  - Volatility State: LOW_VOL (VIX < 20.0). Standard regime weights applied.")

        base_weights = self.get_base_weights(regime)
        lines.append("\n[18-Strategy Dynamic Weight Allocation]")
        if rolling_sharpes:
            dyn_weights = self.compute_dynamic_weights_from_sharpe(rolling_sharpes, regime)
            lines.append("• Dynamic Weighting Scheme: Base Regime Weight x Exponential Sharpe Multiplier exp(1.0 x Sharpe_20d) with EMA Smoothing")
            for strat, w in dyn_weights.items():
                sh = rolling_sharpes.get(strat, 0.0)
                lines.append(f"  - {strat:<22}: {w*100:>5.1f}% (Base: {base_weights.get(strat, 0.0)*100:>4.1f}%, Rolling Sharpe: {sh:+.2f})")
        else:
            lines.append("• Dynamic Weighting Scheme: Baseline 2D Regime Matrix Weights (No historical performance penalty)")
            for strat, w in base_weights.items():
                lines.append(f"  - {strat:<22}: {w*100:>5.1f}%")

        getattr(self.config, 'order_size_krx', 50_000_000.0) if self.config else 50_000_000.0
        getattr(self.config, 'order_size_sp500', 50_000.0) if self.config else 50_000.0

        lines.append("\n[Transaction Costs & Liquidity Filter Rationale]")
        lines.append("• Microstructure Execution & Market Impact Model Active (Almgren-Chriss Order Size Hypothesis (Q): KRX 50M KRW / SP500 50k USD)")
        lines.append("• Transaction Cost & Slippage Deductions Applied:")
        lines.append("  - RUSSELL2000: 0.08% spread + STT/SEC friction")
        lines.append("  - KOSDAQ     : 0.06% spread + STT friction")
        lines.append("  - KOSPI      : 0.04% spread + STT friction")
        lines.append("  - NASDAQ     : 0.03% spread + SEC friction")
        lines.append("  - SP500      : 0.02% spread + SEC friction")
        lines.append("• Liquidity & Safety Gate:")
        lines.append("  - Zero-weighting preferred stocks (우, B), SPACs, and illiquid symbols from Top recommendations.")

        if hasattr(self, 'correlation_monitor') and self.correlation_monitor.rolling_corr_matrix is not None:
            n_eff = self.correlation_monitor.compute_effective_strategy_count()
            top_pairs = self.correlation_monitor.get_top_collinear_pairs(threshold=0.50)
            vifs = self.correlation_monitor.compute_vif()
            max_vif_strat = max(vifs.items(), key=lambda x: x[1]) if vifs else ("N/A", 1.0)
            lines.append("\n[Multicollinearity Monitoring & Regime Noise Suppression]")
            lines.append(f"• Effective Strategy Count (N_eff): {n_eff:.2f} / 17.00")
            lines.append(f"• Highest Strategy VIF            : {max_vif_strat[0]} ({max_vif_strat[1]:.2f})")
            if top_pairs:
                lines.append(f"• High Inter-Strategy Correlations (|rho| >= 0.50): {len(top_pairs)} pair(s) detected")
                for s1, s2, rho in top_pairs[:3]:
                    lines.append(f"  - {s1} <-> {s2}: {rho:+.2f}")

        return "\n".join(lines)

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
                                 event_df: Optional[pd.DataFrame] = None,
                                 mq_df: Optional[pd.DataFrame] = None,
                                 iv_skew_df: Optional[pd.DataFrame] = None,
                                 order_flow_df: Optional[pd.DataFrame] = None,
                                 reversal_df: Optional[pd.DataFrame] = None,
                                 arm_df: Optional[pd.DataFrame] = None,
                                 card_df: Optional[pd.DataFrame] = None,
                                 latr_df: Optional[pd.DataFrame] = None,
                                 inst_foreign_sector_df: Optional[pd.DataFrame] = None,
                                 rolling_sharpes: Optional[Dict[str, float]] = None,
                                 sentiment_blacklist: Optional[Union[List[str], Dict[str, Any]]] = None,
                                 target_horizon: int = 20,
                                 gamma: float = 1.0,
                                 held_symbols: Optional[Union[Set[str], List[str]]] = None) -> pd.DataFrame:
        """
        Calculates 18-Strategy Dynamic Weighted Ensemble Score [0, 1] per stock.
        """
        v_rule_input = vcp_patterns_df if vcp_patterns_df is not None else vcp_rule_df
        weights = self.compute_dynamic_weights_from_sharpe(rolling_sharpes or {}, regime, gamma=gamma)
        return self.combine_predictions(
            reg_df=regression_df,
            s_df=surge_df,
            ll_df=lead_lag_df,
            v_rule_df=v_rule_input,
            vcp_ml_df=vcp_ml_df,
            lstm_df=lstm_df,
            stat_arb_df=stat_arb_df,
            sector_df=sector_df,
            rim_df=rim_df,
            event_df=event_df,
            mq_df=mq_df,
            iv_skew_df=iv_skew_df,
            order_flow_df=order_flow_df,
            reversal_df=reversal_df,
            arm_df=arm_df,
            card_df=card_df,
            latr_df=latr_df,
            inst_foreign_sector_df=inst_foreign_sector_df,
            weights=weights,
            regime=regime,
            target_horizon=target_horizon,
            sentiment_blacklist=sentiment_blacklist,
            held_symbols=held_symbols
        )

    def combine_predictions(self,
                            reg_df: Optional[pd.DataFrame] = None,
                            s_df: Optional[pd.DataFrame] = None,
                            ll_df: Optional[pd.DataFrame] = None,
                            v_rule_df: Optional[Union[pd.DataFrame, list]] = None,
                            vcp_ml_df: Optional[pd.DataFrame] = None,
                            lstm_df: Optional[pd.DataFrame] = None,
                            stat_arb_df: Optional[pd.DataFrame] = None,
                            sector_df: Optional[pd.DataFrame] = None,
                            rim_df: Optional[pd.DataFrame] = None,
                            event_df: Optional[pd.DataFrame] = None,
                            mq_df: Optional[pd.DataFrame] = None,
                            iv_skew_df: Optional[pd.DataFrame] = None,
                            order_flow_df: Optional[pd.DataFrame] = None,
                            reversal_df: Optional[pd.DataFrame] = None,
                            arm_df: Optional[pd.DataFrame] = None,
                            card_df: Optional[pd.DataFrame] = None,
                            latr_df: Optional[pd.DataFrame] = None,
                            inst_foreign_sector_df: Optional[pd.DataFrame] = None,
                            weights: Optional[Dict[str, float]] = None,
                            regime: Union[int, str] = 'BULL_LOW_VOL',
                            target_horizon: int = 20,
                            sentiment_blacklist: Optional[Union[List[str], Dict[str, Any]]] = None,
                            held_symbols: Optional[Union[Set[str], List[str]]] = None) -> pd.DataFrame:
        """
        Merges 18 strategy prediction DataFrames and computes weighted ensemble score.
        """
        if reg_df is None:
            reg_df = pd.DataFrame()
        if s_df is None:
            s_df = pd.DataFrame()
        if ll_df is None:
            ll_df = pd.DataFrame()
        if weights is None:
            weights = self.REGIME_2D_WEIGHTS['BULL_LOW_VOL']

        if vcp_ml_df is None:
            vcp_ml_df = pd.DataFrame(columns=['symbol', 'vcp_ml_score'])

        META_COLS = ['name', 'market', 'volume', 'close']

        # 1. Strategy 1: Regression (Expected return for horizon -> mapped to [0, 1] score)
        if not reg_df.empty:
            num_cols = [c for c in reg_df.columns if c != 'symbol' and c not in META_COLS]
            reg_col = target_horizon if target_horizon in reg_df.columns else (num_cols[-1] if num_cols else reg_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in reg_df.columns]
            reg_df_copy = reg_df[['symbol'] + meta_cols + [reg_col]].rename(columns={reg_col: 'reg_pred'})
            # M-1: Horizon-dependent return scaling factor
            max_ret_norm = 0.15 if target_horizon <= 5 else (0.25 if target_horizon <= 20 else (0.40 if target_horizon <= 60 else 0.80))
            reg_df_copy['reg_score'] = (reg_df_copy['reg_pred'] / max_ret_norm).clip(0.0, 1.0)
        else:
            reg_df_copy = pd.DataFrame(columns=['symbol', 'reg_pred', 'reg_score'])

        # 2. Strategy 2: Surge Classifier
        if not s_df.empty:
            surge_horizons = [1, 3, 5, 20]
            closest_horizon = min(surge_horizons, key=lambda x: abs(x - target_horizon))
            surge_col = f'surge_{closest_horizon}d'
            if surge_col not in s_df.columns:
                num_cols = [c for c in s_df.columns if c != 'symbol' and c not in META_COLS and pd.api.types.is_numeric_dtype(s_df[c])]
                surge_col = str(num_cols[-1]) if num_cols else str(s_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in s_df.columns]
            s_df_copy = s_df[['symbol'] + meta_cols + [surge_col]].rename(columns={surge_col: 'surge_score'})
        else:
            s_df_copy = pd.DataFrame(columns=['symbol', 'surge_score'])

        # 3. Strategy 3: Lead-Lag
        if not ll_df.empty:
            num_cols = [c for c in ll_df.columns if c != 'symbol' and c not in META_COLS]
            ll_col = 'll_score' if 'll_score' in ll_df.columns else ('follower_score' if 'follower_score' in ll_df.columns else (num_cols[-1] if num_cols else ll_df.columns[-1]))
            meta_cols = [c for c in META_COLS if c in ll_df.columns]
            ll_df_copy = ll_df[['symbol'] + meta_cols + [ll_col]].rename(columns={ll_col: 'll_raw'})
            # M-2: Ensure ll_score is robustly normalized [0, 1] whether raw is 0-1 or 0-100
            max_ll_val = float(ll_df_copy['ll_raw'].max()) if not ll_df_copy['ll_raw'].empty else 1.0
            scale_denom = 100.0 if max_ll_val > 1.0 else 1.0
            ll_df_copy['ll_score'] = (ll_df_copy['ll_raw'] / scale_denom).clip(0.0, 1.0)
        else:
            ll_df_copy = pd.DataFrame(columns=['symbol', 'll_raw', 'll_score'])

        # 4. Strategy 4: VCP Pattern Detector (Rule-based)
        if v_rule_df is not None and isinstance(v_rule_df, list):
            vr_df = pd.DataFrame({'symbol': v_rule_df, 'vcp_rule_score': 1.0})
        elif v_rule_df is not None and not v_rule_df.empty:
            vr_df = v_rule_df.copy()

            if 'vcp_score' in vr_df.columns:
                vr_df['vcp_rule_score'] = vr_df['vcp_score'] / 100.0
            elif 'is_vcp' in vr_df.columns:
                vr_df['vcp_rule_score'] = vr_df['is_vcp'].astype(float)
            else:
                num_cols = [c for c in vr_df.columns if c != 'symbol' and c not in META_COLS and pd.api.types.is_numeric_dtype(vr_df[c])]
                vr_col = num_cols[-1] if num_cols else vr_df.columns[-1]
                vr_df['vcp_rule_score'] = vr_df[vr_col]
            meta_cols = [c for c in META_COLS if c in vr_df.columns]
            vr_df = vr_df[['symbol'] + meta_cols + ['vcp_rule_score']]
        else:
            vr_df = pd.DataFrame(columns=['symbol', 'vcp_rule_score'])

        # 5. Strategy 5: VCP ML
        if not vcp_ml_df.empty:
            v_df = vcp_ml_df.copy()
            num_cols = [c for c in v_df.columns if c != 'symbol' and c not in META_COLS]
            v_col = 'vcp_ml_score' if 'vcp_ml_score' in v_df.columns else (num_cols[-1] if num_cols else v_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in v_df.columns]
            v_df = v_df[['symbol'] + meta_cols + [v_col]].rename(columns={v_col: 'vcp_ml_score'})
        else:
            v_df = pd.DataFrame(columns=['symbol', 'vcp_ml_score'])

        # 6. Strategy 6: LSTM
        if lstm_df is not None and not lstm_df.empty:
            l_df = lstm_df.copy()
            num_cols = [c for c in l_df.columns if c != 'symbol' and c not in META_COLS]
            l_col = 'lstm_score' if 'lstm_score' in l_df.columns else (num_cols[-1] if num_cols else l_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in l_df.columns]
            l_df = l_df[['symbol'] + meta_cols + [l_col]].rename(columns={l_col: 'lstm_score'})
        else:
            l_df = pd.DataFrame(columns=['symbol', 'lstm_score'])

        # 7. Strategy 7: Stat-Arb
        if stat_arb_df is not None and not stat_arb_df.empty:
            sa_df = stat_arb_df.copy()
            num_cols = [c for c in sa_df.columns if c != 'symbol' and c not in META_COLS]
            sa_col = 'stat_arb_score' if 'stat_arb_score' in sa_df.columns else (num_cols[-1] if num_cols else sa_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in sa_df.columns]
            sa_df = sa_df[['symbol'] + meta_cols + [sa_col]].rename(columns={sa_col: 'stat_arb_score'})
        else:
            sa_df = pd.DataFrame(columns=['symbol', 'stat_arb_score'])

        # 8. Strategy 8: Sector Rotation
        if sector_df is not None and not sector_df.empty:
            sec_df = sector_df.copy()
            num_cols = [c for c in sec_df.columns if c != 'symbol' and c not in META_COLS]
            sec_col = 'sector_score' if 'sector_score' in sec_df.columns else (num_cols[-1] if num_cols else sec_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in sec_df.columns]
            sec_df = sec_df[['symbol'] + meta_cols + [sec_col]].rename(columns={sec_col: 'sector_score'})
        else:
            sec_df = pd.DataFrame(columns=['symbol', 'sector_score'])

        # 9. Strategy 9: RIM Valuation
        if rim_df is not None and not rim_df.empty:
            r_val_df = rim_df.copy()
            num_cols = [c for c in r_val_df.columns if c != 'symbol' and c not in META_COLS]
            r_col = 'rim_score' if 'rim_score' in r_val_df.columns else (num_cols[-1] if num_cols else r_val_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in r_val_df.columns]
            r_val_df = r_val_df[['symbol'] + meta_cols + [r_col]].rename(columns={r_col: 'rim_score'})
        else:
            r_val_df = pd.DataFrame(columns=['symbol', 'rim_score'])

        # 10. Strategy 10: Event-Driven
        if event_df is not None and not event_df.empty:
            ev_df = event_df.copy()
            num_cols = [c for c in ev_df.columns if c != 'symbol' and c not in META_COLS]
            ev_col = 'event_score' if 'event_score' in ev_df.columns else (num_cols[-1] if num_cols else ev_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in ev_df.columns]
            ev_df = ev_df[['symbol'] + meta_cols + [ev_col]].rename(columns={ev_col: 'event_score'})
        else:
            ev_df = pd.DataFrame(columns=['symbol', 'event_score'])

        # 11. Strategy 11: MQ Factor
        if mq_df is not None and not mq_df.empty:
            m_df = mq_df.copy()
            num_cols = [c for c in m_df.columns if c != 'symbol' and c not in META_COLS]
            m_col = 'mq_score' if 'mq_score' in m_df.columns else (num_cols[-1] if num_cols else m_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in m_df.columns]
            m_df = m_df[['symbol'] + meta_cols + [m_col]].rename(columns={m_col: 'mq_score'})
        else:
            m_df = pd.DataFrame(columns=['symbol', 'mq_score'])

        # 12. Strategy 12: Options IV Skew
        if iv_skew_df is not None and not iv_skew_df.empty:
            iv_df = iv_skew_df.copy()
            num_cols = [c for c in iv_df.columns if c != 'symbol' and c not in META_COLS]
            iv_col = 'iv_skew_score' if 'iv_skew_score' in iv_df.columns else (num_cols[-1] if num_cols else iv_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in iv_df.columns]
            iv_df = iv_df[['symbol'] + meta_cols + [iv_col]].rename(columns={iv_col: 'iv_skew_score'})
        else:
            iv_df = pd.DataFrame(columns=['symbol', 'iv_skew_score'])

        # 13. Strategy 13: Order Flow Imbalance
        if order_flow_df is not None and not order_flow_df.empty:
            of_df = order_flow_df.copy()
            num_cols = [c for c in of_df.columns if c != 'symbol' and c not in META_COLS]
            of_col = 'order_flow_score' if 'order_flow_score' in of_df.columns else (num_cols[-1] if num_cols else of_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in of_df.columns]
            of_df = of_df[['symbol'] + meta_cols + [of_col]].rename(columns={of_col: 'order_flow_score'})
        else:
            of_df = pd.DataFrame(columns=['symbol', 'order_flow_score'])

        # 14. Strategy 14: Short-Term Reversal
        if reversal_df is not None and not reversal_df.empty:
            rev_df = reversal_df.copy()
            num_cols = [c for c in rev_df.columns if c != 'symbol' and c not in META_COLS]
            rev_col = 'reversal_score' if 'reversal_score' in rev_df.columns else (num_cols[-1] if num_cols else rev_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in rev_df.columns]
            rev_df = rev_df[['symbol'] + meta_cols + [rev_col]].rename(columns={rev_col: 'reversal_score'})
        else:
            rev_df = pd.DataFrame(columns=['symbol', 'reversal_score'])

        # 15. Strategy 15: Analyst Revision Momentum (ARM)
        if arm_df is not None and not arm_df.empty:
            a_df = arm_df.copy()
            num_cols = [c for c in a_df.columns if c != 'symbol' and c not in META_COLS]
            a_col = 'arm_score' if 'arm_score' in a_df.columns else (num_cols[-1] if num_cols else a_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in a_df.columns]
            a_df = a_df[['symbol'] + meta_cols + [a_col]].rename(columns={a_col: 'arm_score'})
        else:
            a_df = pd.DataFrame(columns=['symbol', 'arm_score'])

        # 16. Strategy 16: Cross-Asset Regime Divergence (CARD)
        if card_df is not None and not card_df.empty:
            c_df = card_df.copy()
            num_cols = [c for c in c_df.columns if c != 'symbol' and c not in META_COLS]
            c_col = 'card_score' if 'card_score' in c_df.columns else (num_cols[-1] if num_cols else c_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in c_df.columns]
            c_df = c_df[['symbol'] + meta_cols + [c_col]].rename(columns={c_col: 'card_score'})
        else:
            c_df = pd.DataFrame(columns=['symbol', 'card_score'])

        # 17. Strategy 17: Liquidity-Adjusted Tail Risk (LATR)
        if latr_df is not None and not latr_df.empty:
            la_df = latr_df.copy()
            num_cols = [c for c in la_df.columns if c != 'symbol' and c not in META_COLS]
            la_col = 'latr_score' if 'latr_score' in la_df.columns else (num_cols[-1] if num_cols else la_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in la_df.columns]
            la_df = la_df[['symbol'] + meta_cols + [la_col]].rename(columns={la_col: 'latr_score'})
        else:
            la_df = pd.DataFrame(columns=['symbol', 'latr_score'])

        # 18. Strategy 18: Inst & Foreign 2-Month Accumulation & Sector Correlation
        if inst_foreign_sector_df is not None and not inst_foreign_sector_df.empty:
            ifs_df = inst_foreign_sector_df.copy()
            num_cols = [c for c in ifs_df.columns if c != 'symbol' and c not in META_COLS]
            ifs_col = 'inst_foreign_sector_score' if 'inst_foreign_sector_score' in ifs_df.columns else (num_cols[-1] if num_cols else ifs_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in ifs_df.columns]
            ifs_df = ifs_df[['symbol'] + meta_cols + [ifs_col]].rename(columns={ifs_col: 'inst_foreign_sector_score'})
        else:
            ifs_df = pd.DataFrame(columns=['symbol', 'inst_foreign_sector_score'])

        # Combine all 18 strategy DataFrames efficiently while preserving metadata
        dfs = [reg_df_copy, s_df_copy, ll_df_copy, vr_df, v_df, l_df, sa_df, sec_df, r_val_df, ev_df, m_df, iv_df, of_df, rev_df, a_df, c_df, la_df, ifs_df]
        merged = pd.DataFrame(columns=['symbol'])
        for d in dfs:
            if d is not None and not d.empty:
                if 'symbol' in d.columns:
                    d = d.copy()
                    d['symbol'] = d['symbol'].astype(str)
                if merged.empty:
                    merged = d.copy()
                else:
                    overlap = [c for c in d.columns if c in merged.columns and c != 'symbol']
                    if overlap:
                        merged = merged.merge(d, on='symbol', how='outer', suffixes=('', '_dup'))
                        for col in overlap:
                            dup_col = col + '_dup'
                            if dup_col in merged.columns:
                                merged[col] = merged[col].combine_first(merged[dup_col])
                                merged.drop(columns=[dup_col], inplace=True)
                    else:
                        merged = merged.merge(d, on='symbol', how='outer')

        # Map strategy names to score column names
        strategy_cols = [
            ('regression', 'reg_score'),
            ('surge', 'surge_score'),
            ('lead_lag', 'll_score'),
            ('vcp_rule', 'vcp_rule_score'),
            ('vcp_ml', 'vcp_ml_score'),
            ('lstm', 'lstm_score'),
            ('stat_arb', 'stat_arb_score'),
            ('sector_rotation', 'sector_score'),
            ('rim_valuation', 'rim_score'),
            ('event_driven', 'event_score'),
            ('mq_factor', 'mq_score'),
            ('iv_skew', 'iv_skew_score'),
            ('order_flow', 'order_flow_score'),
            ('short_term_reversal', 'reversal_score'),
            ('arm_factor', 'arm_score'),
            ('card_factor', 'card_score'),
            ('latr_factor', 'latr_score'),
            ('inst_foreign_sector', 'inst_foreign_sector_score'),
        ]

        # Phase 3-B: Factor Orthogonalization (PCA ZCA / Gram-Schmidt)
        if getattr(self, 'orthogonalizer_enabled', True):
            try:
                strategy_score_cols = [col for _, col in strategy_cols if col in merged.columns]
                strat_weights = {col: weights.get(strat_name, 0.10) for strat_name, col in strategy_cols if col in merged.columns}
                merged = self.orthogonalizer.orthogonalize(
                    score_df=merged,
                    strategy_cols=strategy_score_cols,
                    weights=strat_weights,
                    method='pca_symmetric'
                )
            except Exception as _oe:
                logger.warning(f"Factor orthogonalization warning: {_oe}")

        # Phase 3-C: Inter-Strategy Signal Correlation Monitoring & 2D Regime Noise Suppression
        try:
            corr_df = self.correlation_monitor.update_correlation(merged)
            vif_dict = self.correlation_monitor.compute_vif(corr_df)

            tuned_p = getattr(self, '_tuned_params', None)
            suppressed_w = self.factor_suppression.suppress_weights(
                base_weights=weights,
                corr_matrix=corr_df,
                regime_label=str(regime),
                tuned_params=tuned_p
            )
            n_eff = self.correlation_monitor.compute_effective_strategy_count(
                weights=suppressed_w,
                corr_matrix=corr_df
            )
            top_pairs = self.correlation_monitor.get_top_collinear_pairs(threshold=0.50, corr_matrix=corr_df)

            weights = suppressed_w

            if not hasattr(merged, 'attrs') or merged.attrs is None:
                merged.attrs = {}
            merged.attrs['correlation_report'] = {
                'correlation_matrix': corr_df,
                'vif': vif_dict,
                'n_eff': n_eff,
                'suppressed_weights': suppressed_w,
                'penalties': self.factor_suppression.compute_penalties(corr_df, str(regime)),
                'top_collinear_pairs': top_pairs
            }
        except Exception as _ce:
            logger.warning(f"Correlation suppression calculation warning: {_ce}")

        # Phase 4-A: Apply Isotonic Regression calibration if calibrators are fitted
        if self.has_calibrators():
            for strategy_name, col in strategy_cols:
                if col in merged.columns and strategy_name in self._calibrators:
                    valid_mask = merged[col].notna() & np.isfinite(merged[col])
                    if valid_mask.any():
                        merged.loc[valid_mask, col] = self.calibrate_scores(strategy_name, merged.loc[valid_mask, col].values)

        # Dynamic Weight Renormalization & Missingness-Aware Coverage Penalization
        total_score_series = pd.Series(0.0, index=merged.index)
        total_weight_series = pd.Series(0.0, index=merged.index)
        valid_count_series = pd.Series(0.0, index=merged.index)

        present_strategy_cols = [score_col for _, score_col in strategy_cols if score_col in merged.columns and merged[score_col].notna().any()]
        num_present_strats = max(float(len(present_strategy_cols)), 1.0)

        for strat_name, score_col in strategy_cols:
            w = weights.get(strat_name, 0.10)
            if score_col in merged.columns:
                # Fix Task 1: Valid 0.0 scores must NOT be discarded as missing data.
                valid_mask = merged[score_col].notna() & np.isfinite(merged[score_col])
                total_score_series += merged[score_col].fillna(0.0) * w * valid_mask.astype(float)
                total_weight_series += w * valid_mask.astype(float)
                valid_count_series += valid_mask.astype(float)

        # Avoid division by zero: if no strategy scores exist, score is 0.0
        safe_weight_series = total_weight_series.replace(0.0, np.nan)
        linear_score = (total_score_series / safe_weight_series).fillna(0.0).clip(0.0, 1.0)

        # Apply coverage factor relative to present strategy DataFrames
        coverage_ratio = valid_count_series / num_present_strats
        coverage_penalty = np.where(coverage_ratio < 0.40, 0.5 + 0.5 * (coverage_ratio / 0.40), 1.0)
        linear_score = pd.Series(linear_score * coverage_penalty, index=merged.index).clip(0.0, 1.0)

        # Phase 1: 2nd Stage Stacking Meta-Learner Hybrid Blend (50:50 if fitted)
        try:
            meta_learner = MetaEnsembleLearner()
            if meta_learner.is_fitted:
                meta_score = meta_learner.predict(merged)
                blended_score = pd.Series(0.5 * linear_score + 0.5 * meta_score, index=merged.index).clip(0.0, 1.0)
            else:
                blended_score = linear_score
        except Exception as e:
            logger.warning(f"MetaEnsembleLearner prediction fallback to linear score: {e}")
            blended_score = linear_score

        # Phase 3: Turnover Hysteresis Buffer for currently held portfolio symbols (+0.05 bonus)
        if held_symbols:
            h_set = set(held_symbols)
            held_mask = merged['symbol'].isin(h_set)
            if held_mask.any():
                blended_score.loc[held_mask] = (blended_score.loc[held_mask] + 0.05).clip(upper=1.0)
                logger.info(f"[TURNOVER HYSTERESIS] Applied +0.05 hold buffer to {held_mask.sum()} held symbols.")

        merged['ensemble_score'] = blended_score

        # Fix Task 2: Preserve raw un-mutated strategy scores with actual NaNs for StrategyCoverageAnalyzer
        self.raw_scores = merged.copy()
        if not hasattr(merged, 'attrs'):
            merged.attrs = {}
        merged.attrs['raw_scores'] = self.raw_scores

        # Fill raw NaNs with 0.0 for report formatting after ensemble score calculation
        fill_cols = [
            'reg_pred', 'reg_score', 'surge_score', 'll_raw', 'll_score',
            'vcp_rule_score', 'vcp_ml_score', 'lstm_score', 'stat_arb_score',
            'sector_score', 'rim_score', 'event_score', 'mq_score',
            'iv_skew_score', 'order_flow_score', 'reversal_score',
            'arm_score', 'card_score', 'latr_score', 'inst_foreign_sector_score'
        ]
        for col in fill_cols:
            if col in merged.columns:
                merged[col] = merged[col].fillna(0.0)
            else:
                merged[col] = 0.0

        # Scale Ensemble Score to Calibrated Realistic Expected Return Proxy (%) [e.g. 0% ~ 50% max]
        # ensemble_score is [0, 1]. For a 20d horizon, score 1.0 represents ~25% expected gain max.
        mult = self._return_multiplier if self._return_multiplier <= 1.0 else (self._return_multiplier / 100.0)
        raw_exp_ret = merged['ensemble_score'] * mult * 100.0

        # Microstructure execution model: Sell-side STT tax, SEC fees, dynamic Bid-Ask spread,
        # and Kyle/Almgren-Chriss Square-Root Market Impact Cost modeling.
        order_size_krx = getattr(self.config, 'order_size_krx', 50_000_000.0) if self.config is not None else 50_000_000.0
        order_size_sp500 = getattr(self.config, 'order_size_sp500', 50_000.0) if self.config is not None else 50_000.0
        impact_coeff_krx = getattr(self.config, 'market_impact_coeff_krx', 0.75) if self.config is not None else 0.75
        impact_coeff_sp500 = getattr(self.config, 'market_impact_coeff_sp500', 0.50) if self.config is not None else 0.50

        base_spread_kospi = getattr(self.config, 'base_spread_kospi', 0.0006) if self.config is not None else 0.0006
        base_spread_kosdaq = getattr(self.config, 'base_spread_kosdaq', 0.0010) if self.config is not None else 0.0010
        base_spread_nasdaq = getattr(self.config, 'base_spread_nasdaq', 0.0003) if self.config is not None else 0.0003
        base_spread_russell2000 = getattr(self.config, 'base_spread_russell2000', 0.0008) if self.config is not None else 0.0008
        base_spread_sp500 = getattr(self.config, 'base_spread_sp500', 0.0002) if self.config is not None else 0.0002

        default_volatility_krx = getattr(self.config, 'default_volatility_krx', 0.020) if self.config is not None else 0.020
        default_volatility_sp500 = getattr(self.config, 'default_volatility_sp500', 0.015) if self.config is not None else 0.015

        def _get_cost_pct(row: pd.Series) -> float:
            symbol = str(row.get('symbol', ''))
            market = str(row.get('market', '')).upper()
            vol = float(row.get('volume', 0.0)) if pd.notna(row.get('volume')) else 0.0
            close_p = float(row.get('close', 0.0)) if pd.notna(row.get('close')) else 0.0
            turnover = vol * close_p

            is_us_stock = market in ('SP500', 'NASDAQ', 'RUSSELL2000') or (symbol.isalpha() and len(symbol) <= 5)
            default_vol = default_volatility_sp500 if is_us_stock else default_volatility_krx
            volatility = float(row.get('volatility_20d', default_vol)) if pd.notna(row.get('volatility_20d')) else default_vol
            if volatility <= 0:
                volatility = default_vol

            if market == 'NASDAQ':
                stt_tax = 0.00003  # SEC fee
                brokerage_fee = 0.00005
                base_spread = base_spread_nasdaq
                spread_min, spread_max = 0.0001, 0.0080
                q_order = order_size_sp500
                adv_ref = 1_000_000.0
                impact_coeff = impact_coeff_sp500
            elif market == 'RUSSELL2000':
                stt_tax = 0.00003
                brokerage_fee = 0.00005
                base_spread = base_spread_russell2000
                spread_min, spread_max = 0.0002, 0.0150
                q_order = order_size_sp500
                adv_ref = 500_000.0
                impact_coeff = impact_coeff_sp500
            elif market == 'KOSDAQ' or symbol.endswith('.KQ'):
                stt_tax = 0.0018
                brokerage_fee = 0.0003
                base_spread = base_spread_kosdaq
                spread_min, spread_max = 0.0003, 0.0250
                q_order = order_size_krx
                adv_ref = 1_000_000_000.0
                impact_coeff = impact_coeff_krx
            elif market == 'KOSPI' or symbol.endswith('.KS') or (symbol.isdigit() and len(symbol) == 6):
                stt_tax = 0.0015
                brokerage_fee = 0.0003
                base_spread = base_spread_kospi
                spread_min, spread_max = 0.0002, 0.0150
                q_order = order_size_krx
                adv_ref = 1_000_000_000.0
                impact_coeff = impact_coeff_krx
            elif is_us_stock:
                stt_tax = 0.00003  # SEC fee
                brokerage_fee = 0.00005
                base_spread = base_spread_sp500
                spread_min, spread_max = 0.0001, 0.0050
                q_order = order_size_sp500
                adv_ref = 1_000_000.0  # $1M USD
                impact_coeff = impact_coeff_sp500
            else:
                stt_tax = 0.0015
                brokerage_fee = 0.0003
                base_spread = base_spread_kospi
                spread_min, spread_max = 0.0002, 0.0150
                q_order = order_size_krx
                adv_ref = 1_000_000_000.0
                impact_coeff = impact_coeff_krx

            min_adv = 10_000.0 if is_us_stock else 10_000_000.0
            adv = max(turnover, min_adv)

            # 1. Dynamic Bid-Ask Spread Modeling
            adv_ratio = adv_ref / adv
            vol_ratio = volatility / 0.020
            dynamic_spread = base_spread * (adv_ratio ** 0.25) * (vol_ratio ** 0.50)
            clamped_spread = min(max(dynamic_spread, spread_min), spread_max)

            # 2. Order Book Market Impact Modeling (using empirical realized_market_impact_alpha)
            participation_ratio = q_order / adv
            impact_alpha = getattr(self, 'realized_market_impact_alpha', 0.50)
            if impact_alpha == 0.50:
                impact_one_way = impact_coeff * volatility * np.sqrt(participation_ratio)
            else:
                impact_one_way = impact_coeff * volatility * (participation_ratio ** impact_alpha)

            # 3. Participation Rate Overflow Penalty (> 10% ADV)
            if participation_ratio > 0.10:
                impact_one_way += 0.50 * (participation_ratio - 0.10)

            raw_total_cost = stt_tax + brokerage_fee + (1.0 * clamped_spread) + (2.0 * impact_one_way)
            cost_scaling = getattr(self, 'cost_scaling_factor', 1.0)
            total_cost_pct = raw_total_cost * cost_scaling
            return float(total_cost_pct)

        cost_series = merged.apply(_get_cost_pct, axis=1)
        merged['ensemble_expected_return'] = (raw_exp_ret - cost_series * 100.0).clip(lower=0.0, upper=50.0)

        # Apply Sentiment Blacklist filter (zero-weighting for critical disclosure risk)
        if sentiment_blacklist:
            b_set = set(sentiment_blacklist.keys()) if isinstance(sentiment_blacklist, dict) else set(sentiment_blacklist)
            if b_set:
                mask = merged['symbol'].isin(b_set)
                merged.loc[mask, 'ensemble_score'] = 0.0
                merged.loc[mask, 'ensemble_expected_return'] = 0.0
                logger.info(f"[ENSEMBLE SENTIMENT FILTER] Zero-weighted {mask.sum()} blacklisted symbols.")

        # ─── Liquidity Gate & Preferred Stock / SPAC Filter ──────────────────────
        def _is_illiquid_or_preferred(row: pd.Series) -> bool:
            sym = str(row.get('symbol', ''))
            name = str(row.get('name', ''))
            # Preferred stock check
            if name.endswith('우') or name.endswith('우B') or name.endswith('1우') or name.endswith('2우B') or name.endswith('3우B'):
                return True
            if len(sym) == 6 and sym[-1] in ['K', 'L', 'M', 'N', 'O']:
                return True
            # SPAC check
            if '스팩' in name or 'SPAC' in name.upper():
                return True
            if 'volume' in row and pd.notna(row['volume']):
                vol = float(row['volume'])
                close_p = float(row.get('close', 0.0)) if pd.notna(row.get('close')) else 0.0
                turnover = vol * close_p
                mkt = str(row.get('market', '')).upper()
                min_krx_turnover = getattr(self.config, 'min_daily_volume_krx', 5_000_000_000.0) if self.config else 5_000_000_000.0
                min_sp_vol = getattr(self.config, 'min_daily_volume_sp500', 1_000_000.0) if self.config else 1_000_000.0
                if vol <= 0:
                    return True
                if mkt in ['KOSPI', 'KOSDAQ'] and turnover > 0 and turnover < (min_krx_turnover * 0.1): # 10% threshold for daily turnover
                    return True
                if mkt in ['SP500', 'NASDAQ', 'RUSSELL2000'] and vol < (min_sp_vol * 0.1):
                    return True
            return False

        # Apply illiquid/preferred tag (zero-weight or filter out for top recommendations)
        illiquid_mask = merged.apply(_is_illiquid_or_preferred, axis=1)
        if illiquid_mask.any():
            logger.info(f"[LIQUIDITY GATE] Flagged {illiquid_mask.sum()} preferred/SPAC/illiquid stocks.")
            # Zero-out ensemble score for preferred/SPACs so they do not populate Top 20 recommendations
            merged.loc[illiquid_mask, 'ensemble_score'] = 0.0
            merged.loc[illiquid_mask, 'ensemble_expected_return'] = 0.0

        # Sort by net expected return (cost and liquidity adjusted) descending
        merged = merged.sort_values(by=['ensemble_expected_return', 'ensemble_score'], ascending=[False, False]).reset_index(drop=True)

        # ─── Portfolio Optimization & Risk Parity Weight Allocation ─────────────
        merged['portfolio_weight'] = 0.0
        top_candidates = merged.head(20)
        if not top_candidates.empty:
            try:
                from ..risk.portfolio_optimizer import PortfolioOptimizer
                optimizer = PortfolioOptimizer(default_max_weight=0.20, default_max_sector_weight=0.35)

                # C-1 Fix: Build realistic returns matrix for Top candidates based on actual strategy scores
                top_syms = top_candidates['symbol'].tolist()
                score_cols = [c for c in ['reg_score', 'surge_score', 'll_score', 'vcp_ml_score', 'stat_arb_score', 'sector_score', 'rim_score'] if c in top_candidates.columns]

                if score_cols and len(score_cols) >= 2:
                    # Use actual strategy scores per symbol as sample return vectors
                    returns_matrix_df = top_candidates.set_index('symbol')[score_cols].T
                else:
                    # Fallback construct deterministic return series scaled by expected return
                    ret_series = top_candidates.set_index('symbol')['ensemble_expected_return'] / 100.0
                    base_noise = np.linspace(-0.01, 0.01, 30)
                    returns_matrix_df = pd.DataFrame(
                        {sym: ret_series[sym] + base_noise for sym in top_syms}
                    )

                raw_weights = optimizer.optimize_risk_parity(returns_matrix_df)
                sector_map = dict(zip(top_candidates['symbol'], top_candidates.get('sector', 'Unknown')))
                constrained_weights = optimizer.apply_factor_and_sector_constraints(raw_weights, sector_map)

                for sym, w in constrained_weights.items():
                    merged.loc[merged['symbol'] == sym, 'portfolio_weight'] = round(w, 4)
            except Exception as e:
                logger.warning(f"[PORTFOLIO OPTIMIZER] Error allocating weights: {e}")
                # Fallback to equal weighting for Top N
                n_top = len(top_candidates)
                if n_top > 0:
                    merged.loc[:n_top-1, 'portfolio_weight'] = round(1.0 / n_top, 4)

        return merged

