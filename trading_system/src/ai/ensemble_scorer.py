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
    Ensembles 31 multi-factor strategy predictions across 3 horizon tiers
    using 2D regime matrix weights, factor orthogonalization (PCA-ZCA & Gram-Schmidt),
    and dynamic exponential Sharpe weighting.
    """

    # 3-Tier Multi-Horizon Alpha Signal Decomposition (Slow: 1M~1Y, Medium: 5D~20D, Fast: 1D~3D)
    ALPHA_HORIZON_TIERS = {
        'slow': [
            'regression', 'rim_valuation', 'factor_neutralized', 'valueup_catalyst',
            'accruals_quality', 'mq_factor', 'arm_factor', 'card_factor', 'latr_factor',
            'vol_target', 'iv_skew', 'earnings_tone_drift',
        ],
        'medium': [
            'vcp_rule', 'vcp_ml', 'surge', 'lead_lag', 'stat_arb', 'sector_rotation',
            'lstm', 'sentiment', 'inst_foreign_sector', 'supply_chain',
            'gamma_squeeze', 'short_squeeze', 'insider_buying', 'trend_efficiency', 'event_driven',
        ],
        'fast': [
            'microstructure', 'order_flow', 'short_term_reversal', 'darkpool',
        ],
    }
    TIER_WEIGHTS = {'slow': 0.50, 'medium': 0.35, 'fast': 0.15}

    # Dynamic Weight Configuration per 1D Market Regime (0: BEAR, 1: SIDEWAYS, 2: BULL)
    # Dynamic Weight Configuration per 1D Market Regime (30 Strategies)
    REGIME_WEIGHTS = {
        0: {  # BEAR (Defensive) — sum = 1.00
            'regression': 0.11,
            'surge': 0.01,
            'lead_lag': 0.02,
            'vcp_rule': 0.01,
            'vcp_ml': 0.01,
            'lstm': 0.02,
            'stat_arb': 0.07,
            'sector_rotation': 0.03,
            'rim_valuation': 0.08,
            'event_driven': 0.03,
            'mq_factor': 0.05,
            'iv_skew': 0.03,
            'order_flow': 0.02,
            'short_term_reversal': 0.04,
            'arm_factor': 0.04,
            'card_factor': 0.04,
            'latr_factor': 0.04,
            'inst_foreign_sector': 0.04,
            'supply_chain': 0.01,
            'sentiment': 0.03,
            'factor_neutralized': 0.03,
            'vol_target': 0.05,
            'microstructure': 0.02,
            'accruals_quality': 0.04,
            'short_squeeze': 0.01,
            'valueup_catalyst': 0.04,
            'trend_efficiency': 0.01,
            'gamma_squeeze': 0.01,
            'insider_buying': 0.02,
            'darkpool': 0.02,
            'earnings_tone_drift': 0.02,
        },
        1: {  # SIDEWAYS (Rotation) — sum = 1.00
            'regression': 0.05,
            'surge': 0.02,
            'lead_lag': 0.03,
            'vcp_rule': 0.02,
            'vcp_ml': 0.03,
            'lstm': 0.04,
            'stat_arb': 0.07,
            'sector_rotation': 0.04,
            'rim_valuation': 0.04,
            'event_driven': 0.04,
            'mq_factor': 0.04,
            'iv_skew': 0.02,
            'order_flow': 0.03,
            'short_term_reversal': 0.03,
            'arm_factor': 0.04,
            'card_factor': 0.04,
            'latr_factor': 0.04,
            'inst_foreign_sector': 0.04,
            'supply_chain': 0.01,
            'sentiment': 0.03,
            'factor_neutralized': 0.03,
            'vol_target': 0.03,
            'microstructure': 0.03,
            'accruals_quality': 0.03,
            'short_squeeze': 0.02,
            'valueup_catalyst': 0.03,
            'trend_efficiency': 0.01,
            'gamma_squeeze': 0.02,
            'insider_buying': 0.03,
            'darkpool': 0.03,
            'earnings_tone_drift': 0.02,
        },
        2: {  # BULL (Aggressive) — sum = 1.00
            'regression': 0.03,
            'surge': 0.07,
            'lead_lag': 0.02,
            'vcp_rule': 0.02,
            'vcp_ml': 0.06,
            'lstm': 0.04,
            'stat_arb': 0.02,
            'sector_rotation': 0.04,
            'rim_valuation': 0.03,
            'event_driven': 0.05,
            'mq_factor': 0.04,
            'iv_skew': 0.02,
            'order_flow': 0.03,
            'short_term_reversal': 0.02,
            'arm_factor': 0.04,
            'card_factor': 0.03,
            'latr_factor': 0.03,
            'inst_foreign_sector': 0.05,
            'supply_chain': 0.03,
            'sentiment': 0.03,
            'factor_neutralized': 0.03,
            'vol_target': 0.02,
            'microstructure': 0.03,
            'accruals_quality': 0.01,
            'short_squeeze': 0.04,
            'valueup_catalyst': 0.01,
            'trend_efficiency': 0.04,
            'gamma_squeeze': 0.04,
            'insider_buying': 0.03,
            'darkpool': 0.03,
            'earnings_tone_drift': 0.02,
        }
    }

    # 2D Market Regime Matrix Weights (6 Combo States across 30 Strategies)
    REGIME_2D_WEIGHTS = {
        'BEAR_LOW_VOL': {  # sum = 1.00
            'regression': 0.11,
            'surge': 0.01,
            'lead_lag': 0.02,
            'vcp_rule': 0.01,
            'vcp_ml': 0.01,
            'lstm': 0.02,
            'stat_arb': 0.07,
            'sector_rotation': 0.03,
            'rim_valuation': 0.08,
            'event_driven': 0.03,
            'mq_factor': 0.05,
            'iv_skew': 0.03,
            'order_flow': 0.02,
            'short_term_reversal': 0.04,
            'arm_factor': 0.04,
            'card_factor': 0.04,
            'latr_factor': 0.04,
            'inst_foreign_sector': 0.04,
            'supply_chain': 0.01,
            'sentiment': 0.03,
            'factor_neutralized': 0.03,
            'vol_target': 0.05,
            'microstructure': 0.02,
            'accruals_quality': 0.04,
            'short_squeeze': 0.01,
            'valueup_catalyst': 0.04,
            'trend_efficiency': 0.01,
            'gamma_squeeze': 0.01,
            'insider_buying': 0.02,
            'darkpool': 0.02,
            'earnings_tone_drift': 0.02,
        },
        'BEAR_HIGH_VOL': {  # sum = 1.00
            'regression': 0.12,
            'surge': 0.00,
            'lead_lag': 0.02,
            'vcp_rule': 0.01,
            'vcp_ml': 0.01,
            'lstm': 0.02,
            'stat_arb': 0.08,
            'sector_rotation': 0.02,
            'rim_valuation': 0.08,
            'event_driven': 0.03,
            'mq_factor': 0.04,
            'iv_skew': 0.04,
            'order_flow': 0.02,
            'short_term_reversal': 0.05,
            'arm_factor': 0.04,
            'card_factor': 0.05,
            'latr_factor': 0.05,
            'inst_foreign_sector': 0.04,
            'supply_chain': 0.00,
            'sentiment': 0.03,
            'factor_neutralized': 0.03,
            'vol_target': 0.05,
            'microstructure': 0.02,
            'accruals_quality': 0.05,
            'short_squeeze': 0.00,
            'valueup_catalyst': 0.04,
            'trend_efficiency': 0.00,
            'gamma_squeeze': 0.00,
            'insider_buying': 0.02,
            'darkpool': 0.02,
            'earnings_tone_drift': 0.02,
        },
        'SIDEWAYS_LOW_VOL': {  # sum = 1.00
            'regression': 0.05,
            'surge': 0.02,
            'lead_lag': 0.03,
            'vcp_rule': 0.02,
            'vcp_ml': 0.03,
            'lstm': 0.04,
            'stat_arb': 0.07,
            'sector_rotation': 0.04,
            'rim_valuation': 0.04,
            'event_driven': 0.04,
            'mq_factor': 0.04,
            'iv_skew': 0.02,
            'order_flow': 0.03,
            'short_term_reversal': 0.03,
            'arm_factor': 0.04,
            'card_factor': 0.04,
            'latr_factor': 0.04,
            'inst_foreign_sector': 0.04,
            'supply_chain': 0.01,
            'sentiment': 0.03,
            'factor_neutralized': 0.03,
            'vol_target': 0.03,
            'microstructure': 0.03,
            'accruals_quality': 0.03,
            'short_squeeze': 0.02,
            'valueup_catalyst': 0.03,
            'trend_efficiency': 0.01,
            'gamma_squeeze': 0.02,
            'insider_buying': 0.03,
            'darkpool': 0.03,
            'earnings_tone_drift': 0.02,
        },
        'SIDEWAYS_HIGH_VOL': {  # sum = 1.00
            'regression': 0.05,
            'surge': 0.02,
            'lead_lag': 0.03,
            'vcp_rule': 0.02,
            'vcp_ml': 0.03,
            'lstm': 0.04,
            'stat_arb': 0.07,
            'sector_rotation': 0.03,
            'rim_valuation': 0.04,
            'event_driven': 0.04,
            'mq_factor': 0.03,
            'iv_skew': 0.03,
            'order_flow': 0.03,
            'short_term_reversal': 0.03,
            'arm_factor': 0.04,
            'card_factor': 0.04,
            'latr_factor': 0.04,
            'inst_foreign_sector': 0.04,
            'supply_chain': 0.01,
            'sentiment': 0.03,
            'factor_neutralized': 0.03,
            'vol_target': 0.04,
            'microstructure': 0.03,
            'accruals_quality': 0.03,
            'short_squeeze': 0.01,
            'valueup_catalyst': 0.03,
            'trend_efficiency': 0.01,
            'gamma_squeeze': 0.02,
            'insider_buying': 0.03,
            'darkpool': 0.03,
            'earnings_tone_drift': 0.02,
        },
        'BULL_LOW_VOL': {  # sum = 1.00
            'regression': 0.03,
            'surge': 0.07,
            'lead_lag': 0.02,
            'vcp_rule': 0.02,
            'vcp_ml': 0.06,
            'lstm': 0.04,
            'stat_arb': 0.02,
            'sector_rotation': 0.04,
            'rim_valuation': 0.03,
            'event_driven': 0.05,
            'mq_factor': 0.04,
            'iv_skew': 0.02,
            'order_flow': 0.03,
            'short_term_reversal': 0.02,
            'arm_factor': 0.04,
            'card_factor': 0.03,
            'latr_factor': 0.03,
            'inst_foreign_sector': 0.05,
            'supply_chain': 0.03,
            'sentiment': 0.03,
            'factor_neutralized': 0.03,
            'vol_target': 0.02,
            'microstructure': 0.03,
            'accruals_quality': 0.01,
            'short_squeeze': 0.04,
            'valueup_catalyst': 0.01,
            'trend_efficiency': 0.04,
            'gamma_squeeze': 0.04,
            'insider_buying': 0.03,
            'darkpool': 0.03,
            'earnings_tone_drift': 0.02,
        },
        'BULL_HIGH_VOL': {  # sum = 1.00
            'regression': 0.02,
            'surge': 0.08,
            'lead_lag': 0.02,
            'vcp_rule': 0.02,
            'vcp_ml': 0.06,
            'lstm': 0.04,
            'stat_arb': 0.02,
            'sector_rotation': 0.03,
            'rim_valuation': 0.03,
            'event_driven': 0.05,
            'mq_factor': 0.04,
            'iv_skew': 0.02,
            'order_flow': 0.03,
            'short_term_reversal': 0.03,
            'arm_factor': 0.04,
            'card_factor': 0.03,
            'latr_factor': 0.03,
            'inst_foreign_sector': 0.05,
            'supply_chain': 0.03,
            'sentiment': 0.03,
            'factor_neutralized': 0.03,
            'vol_target': 0.02,
            'microstructure': 0.03,
            'accruals_quality': 0.01,
            'short_squeeze': 0.04,
            'valueup_catalyst': 0.01,
            'trend_efficiency': 0.04,
            'gamma_squeeze': 0.04,
            'insider_buying': 0.03,
            'darkpool': 0.03,
            'earnings_tone_drift': 0.02,
        }
    }

    # 3D Macro Regime Override Weights (LIQUIDITY_SQUEEZE, HIGH_YIELD_BULL, HIGH_YIELD_BEAR,
    #                                    INFLATION_SHOCK, YIELD_INVERSION)
    # Deltas are applied to 2D regime base weights then re-normalized to sum=1.
    MACRO_WEIGHT_MODIFIERS = {
        'LIQUIDITY_SQUEEZE': {
            'stat_arb': +0.10,
            'vcp_rule': +0.05,
            'vol_target': +0.05,        # 유동성 경색 시 변동성 타게팅 방어 강화
            'surge': -0.10,
            'sector_rotation': -0.05,
            'short_squeeze': -0.03,     # 유동성 경색 시 숏스퀴즈 기회 감소
            'supply_chain': -0.02,
        },
        'HIGH_YIELD_BULL': {
            'sector_rotation': +0.10,
            'surge': +0.05,
            'supply_chain': +0.03,      # 업종 연쇄 온기 전이 가속
            'trend_efficiency': +0.05,  # 강세장 추세 효율성 부스트
            'lead_lag': -0.10,
            'stat_arb': -0.05,
        },
        'HIGH_YIELD_BEAR': {
            'regression': +0.10,
            'stat_arb': +0.10,
            'accruals_quality': +0.04,  # 신용 위험 확대기 회계 품질 필터 강화
            'surge': -0.15,
            'vcp_ml': -0.05,
            'trend_efficiency': -0.04,  # 하락 고수익 채권 국면 추세 전략 억제
        },
        # ① 인플레이션 충격 (유가 + USD/KRW 환율 동시 상승): 국내 제조업 원가 이중 압박
        # MQ Factor(영업이익률/ROE 저하) 가중치 하향, RIM Valuation(안전마진) + Stat-Arb(시장 중립) 상향
        'INFLATION_SHOCK': {
            'mq_factor': -0.08,
            'surge': -0.05,
            'rim_valuation': +0.07,
            'stat_arb': +0.06,
            'accruals_quality': +0.04,  # 원가 압박 시 현금흐름 품질 필터
            'valueup_catalyst': +0.03,  # 저평가 방어주(PBR<1) 선호
        },
        # ② 장단기 금리 역전 (US10Y < US5Y): 6~18개월 내 경기침체 선행 신호
        # 공격적 모멘텀 전략 축소, 가치평가(RIM) + 평균회귀(Stat-Arb) + 단기반전 방어
        'YIELD_INVERSION': {
            'regression': +0.08,
            'rim_valuation': +0.08,
            'stat_arb': +0.06,
            'short_term_reversal': +0.04,
            'accruals_quality': +0.05,  # 침체 선행 신호: 회계 품질 최강화
            'valueup_catalyst': +0.03,  # 저평가 방어 포지션
            'surge': -0.12,
            'vcp_ml': -0.07,
            'sector_rotation': -0.07,
            'trend_efficiency': -0.03,  # 금리 역전 시 추세 전략 축소
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
                if len(s) != len(y):
                    min_len = min(len(s), len(y))
                    s = s[:min_len]
                    y = y[:min_len]
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

    @staticmethod
    def compute_ece_and_brier(probs: np.ndarray, y_true: np.ndarray, n_bins: int = 10) -> Dict[str, float]:
        """
        Computes Expected Calibration Error (ECE) and Brier Score for probability outputs.
        ECE = sum(|bin_acc - bin_conf| * bin_weight)
        Brier = mean((prob - y_true)^2)
        """
        p = np.asarray(probs, dtype=float)
        y = np.asarray(y_true, dtype=float)
        mask = np.isfinite(p) & np.isfinite(y)
        p, y = p[mask], y[mask]
        if len(p) == 0:
            return {"ece": 0.0, "brier": 0.0}

        brier = float(np.mean((p - y) ** 2))
        bins = np.linspace(0.0, 1.0, n_bins + 1)
        ece = 0.0
        n_total = len(p)

        for i in range(n_bins):
            bin_lower, bin_upper = bins[i], bins[i + 1]
            if i == n_bins - 1:
                in_bin = (p >= bin_lower) & (p <= bin_upper)
            else:
                in_bin = (p >= bin_lower) & (p < bin_upper)

            n_in_bin = np.sum(in_bin)
            if n_in_bin > 0:
                acc = np.mean(y[in_bin])
                conf = np.mean(p[in_bin])
                ece += (n_in_bin / n_total) * abs(acc - conf)

        return {"ece": float(ece), "brier": float(brier)}
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
                    if np.isnan(std_ret) or std_ret < 1e-8:
                        std_ret = 1e-6
                    if np.isnan(mean_ret):
                        mean_ret = 0.0
                    sharpe = ((mean_ret - rf_daily) / std_ret) * np.sqrt(252)

                    # Downside semi-deviation Sortino calculation for asymmetric risk penalty
                    downside_diff = np.minimum(0.0, recent.values - rf_daily)
                    downside_std = float(np.sqrt(np.mean(downside_diff ** 2)))
                    if np.isnan(downside_std) or downside_std < 1e-8:
                        downside_std = std_ret
                    sortino = ((mean_ret - rf_daily) / downside_std) * np.sqrt(252)

                    # Hybrid Risk-Adjusted Score (60% Sharpe, 40% Sortino)
                    risk_adj = 0.60 * sharpe + 0.40 * sortino
                    sharpes[strategy] = float(np.clip(risk_adj, -10.0, 10.0))
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
            # 신규: VIX>30 시 추세/숏스퀴즈 모멘텀 억제
            w['trend_efficiency'] = max(0.0, w.get('trend_efficiency', 0.02) - 0.02)
            w['short_squeeze'] = max(0.0, w.get('short_squeeze', 0.02) - 0.01)
            w['supply_chain'] = max(0.0, w.get('supply_chain', 0.02) - 0.01)

        if vix_val > 40.0:
            w['surge'] = max(0.01, w.get('surge', 0.15) * 0.3)
            w['vcp_ml'] = max(0.01, w.get('vcp_ml', 0.10) * 0.3)
            w['trend_efficiency'] = max(0.01, w.get('trend_efficiency', 0.02) * 0.3)
            w['short_squeeze'] = max(0.01, w.get('short_squeeze', 0.02) * 0.3)
            w['stat_arb'] = w.get('stat_arb', 0.10) + 0.15
            w['rim_valuation'] = w.get('rim_valuation', 0.10) + 0.10
            w['vol_target'] = w.get('vol_target', 0.04) + 0.05  # 리스크 파리티 극대화
            w['accruals_quality'] = w.get('accruals_quality', 0.03) + 0.03

        total_w = sum(w.values())
        if total_w > 0:
            return {k: v / total_w for k, v in w.items()}
        n_keys = len(w)
        return {k: 1.0 / n_keys for k in w} if n_keys > 0 else w

    def get_base_weights(self, regime: Union[int, str], vix_val: Optional[float] = None,
                         macro_label: Optional[str] = None) -> Dict[str, float]:
        """Return baseline strategy weights according to 1D integer regime or 2D string regime."""
        if isinstance(regime, str) and regime in self.REGIME_2D_WEIGHTS:
            w = dict(self.REGIME_2D_WEIGHTS[regime])
        elif str(regime).isdigit() and int(regime) in self.REGIME_WEIGHTS:
            w = dict(self.REGIME_WEIGHTS[int(regime)])
        elif isinstance(regime, int) and regime in self.REGIME_WEIGHTS:
            w = dict(self.REGIME_WEIGHTS[regime])
        else:
            w = dict(self.REGIME_2D_WEIGHTS.get(str(regime), self.REGIME_2D_WEIGHTS['SIDEWAYS_LOW_VOL']))

        # Apply 3D Macro Modifier if applicable
        if macro_label and macro_label in self.MACRO_WEIGHT_MODIFIERS:
            mods = self.MACRO_WEIGHT_MODIFIERS[macro_label]
            for strat, delta in mods.items():
                if strat in w:
                    w[strat] = max(0.0, w[strat] + delta)
            total_w = sum(w.values())
            if total_w > 0:
                w = {k: v / total_w for k, v in w.items()}

        # Build baseline weights dynamically from StrategyRegistry
        from src.core.strategy_registry import get_registry
        registry_inst = get_registry()
        registry_inst.auto_discover(["src.core", "src.ai"])
        all_metas = registry_inst.get_all()

        res = dict(w)
        regime_key = str(regime)
        for sid, (_, meta) in all_metas.items():
            if meta.is_standalone:
                res[sid] = 0.0
            elif sid not in res:
                res[sid] = meta.default_regime_weights.get(regime_key, 0.02)

        total_base = sum(res.values())
        if total_base > 0:
            res = {k: v / total_base for k, v in res.items()}

        # Apply VIX Fast Override if active
        res = self.apply_vix_override(res, vix_val=vix_val)

        total = sum(res.values())
        if total == 0.0:
            n = len(res)
            return {k: 1.0 / n for k in res} if n > 0 else res
        return {k: v / total for k, v in res.items()}

    def apply_correlation_orthogonalization_penalty(
        self,
        weights: Dict[str, float],
        scores_df: Optional[pd.DataFrame] = None,
        correlation_threshold: float = 0.65,
        penalty_factor: float = 0.5,
    ) -> Dict[str, float]:
        """
        Calculates pairwise strategy score correlation matrix and applies Gram-Schmidt-style
        orthogonalization penalty for highly collinear strategy pairs (r > threshold).
        """
        if scores_df is None or (isinstance(scores_df, pd.DataFrame) and scores_df.empty) or len(weights) <= 1:
            return weights

        from src.core.strategy_registry import get_registry
        reg = get_registry()
        score_cols = reg.get_all_score_columns()

        valid_cols = {}
        for sid in weights.keys():
            if weights.get(sid, 0.0) > 0:
                str_sid = str(sid)
                reg_col = score_cols.get(str_sid) or (score_cols.get(sid) if isinstance(sid, str) else None)
                if reg_col and reg_col in scores_df.columns:
                    valid_cols[sid] = reg_col
                elif sid in scores_df.columns:
                    valid_cols[sid] = sid
                else:
                    for df_col in scores_df.columns:
                        str_df_col = str(df_col)
                        if str_sid.lower() in str_df_col.lower() or str_df_col.lower().startswith(str_sid[:3].lower()):
                            valid_cols[sid] = df_col
                            break

        if len(valid_cols) < 2:
            return weights

        try:
            subset_df = scores_df[list(valid_cols.values())].apply(pd.to_numeric, errors='coerce').dropna()
            if len(subset_df) < 10:
                return weights

            corr_matrix = subset_df.corr().abs()
            col_to_sid = {v: k for k, v in valid_cols.items()}

            # Löwdin Symmetric Orthogonalization: C^(-1/2) for order-independent penalization
            C = corr_matrix.values
            evals, evecs = np.linalg.eigh(C)
            evals = np.maximum(evals, 1e-4)
            inv_sqrt_C = evecs @ np.diag(1.0 / np.sqrt(evals)) @ evecs.T

            diag_penalties = np.diag(inv_sqrt_C)
            mean_p = np.mean(diag_penalties) if np.mean(diag_penalties) > 0 else 1.0
            norm_penalties = np.clip(diag_penalties / mean_p, 0.4, 2.5)

            penalized_weights = dict(weights)
            for col, p_factor in zip(corr_matrix.columns, norm_penalties):
                strategy_id = col_to_sid.get(col)
                if strategy_id and strategy_id in penalized_weights and penalized_weights[strategy_id] > 0:
                    penalized_weights[strategy_id] *= (1.0 / float(p_factor))

            total = sum(penalized_weights.values())
            if total > 0:
                penalized_weights = {k: v / total for k, v in penalized_weights.items()}
            return penalized_weights
        except Exception as e:
            logger.warning(f"[EnsembleScorer] Correlation penalty calculation failed: {e}")
            return weights

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

        clean_sharpes = {}
        for s, val in rolling_sharpes.items():
            if val is None or np.isnan(val):
                clean_sharpes[s] = 0.0
            else:
                clean_sharpes[s] = float(val)

        all_zero = all(abs(v) < 1e-8 for v in clean_sharpes.values())
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
            sharpe = clean_sharpes.get(strategy, 0.0)
            if sharpe < -0.50:
                # Hard gate pruning for severely underperforming strategies
                scores[strategy] = 0.0
                continue

            clipped_sharpe = float(np.clip(sharpe, -sharpe_clip, sharpe_clip))
            multiplier = float(np.exp(gamma * clipped_sharpe))
            # Convex Sharpe Elasticity Multiplier for high performing strategies
            if clipped_sharpe >= 1.50:
                multiplier *= 1.25
            elif clipped_sharpe >= 1.00:
                multiplier *= 1.15
            elif clipped_sharpe >= 0.50:
                multiplier *= 1.08
            elif clipped_sharpe < 0.0:
                # Asymmetric downside risk mitigation for mild underperformance
                downside_penalty = 1.0 / (1.0 + abs(clipped_sharpe) * 0.40)
                multiplier *= downside_penalty
            scores[strategy] = base_w * multiplier

        # Additionally bound the TOTAL weight ratio (base regime weights already
        # differ up to ~5x, so multiplier-only capping is not enough). Damping the
        # scores with a power < 1 preserves ordering while keeping any single
        # strategy from dominating the ensemble.
        max_total_ratio = 20.0
        _vals = np.array([v for v in scores.values() if v > 0.0], dtype=float)
        if len(_vals) > 0:
            _vmax = float(_vals.max())
            _vmin_floor = _vmax / max_total_ratio
            scores = {k: (max(v, _vmin_floor) if v > 0.0 else 0.0) for k, v in scores.items()}

        total_score = sum(scores.values())
        if total_score == 0.0:
            return base_weights
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
                if target_w == 0.0:
                    smoothed[k] = 0.0
                else:
                    prev_w = self._prev_weights.get(k, target_w)
                    smoothed[k] = eff_alpha * target_w + (1.0 - eff_alpha) * prev_w

            total_w = sum(smoothed.values())
            if total_w > 0:
                smoothed = {k: v / total_w for k, v in smoothed.items()}
            dynamic_weights = smoothed

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

    def compute_dynamic_weights(
        self,
        rolling_sharpes: Dict[str, float],
        regime: Union[int, str] = "SIDEWAYS_LOW_VOL",
        gamma: float = 1.0,
        vix_val: Optional[float] = None
    ) -> Dict[str, float]:
        """Backward-compatible alias for compute_dynamic_weights_from_sharpe."""
        return self.compute_dynamic_weights_from_sharpe(rolling_sharpes, regime, gamma=gamma, vix_val=vix_val)

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
        lines.append(f"\n[{len(base_weights)}-Strategy Dynamic Weight Allocation]")
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
        lines.append("• Target Horizon: 20 Trading Days (20D Expected Net Return after transaction friction)")
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
            lines.append(f"• Effective Strategy Count (N_eff): {n_eff:.2f} / {len(self.correlation_monitor.strategies):.2f}")
            lines.append(f"• Highest Strategy VIF            : {max_vif_strat[0]} ({max_vif_strat[1]:.2f})")
            if top_pairs:
                lines.append(f"• High Inter-Strategy Correlations (|rho| >= 0.50): {len(top_pairs)} pair(s) detected")
                for s1, s2, rho in top_pairs[:3]:
                    lines.append(f"  - {s1} <-> {s2}: {rho:+.2f}")

        return "\n".join(lines)

    def calculate_ensemble_score(self,
                                 regime: Union[int, str] = 'BULL_LOW_VOL',
                                 regression_df: Optional[pd.DataFrame] = None,
                                 surge_df: Optional[pd.DataFrame] = None,
                                 lead_lag_df: Optional[pd.DataFrame] = None,
                                 vcp_ml_df: Optional[pd.DataFrame] = None,
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
                                 supply_chain_df: Optional[pd.DataFrame] = None,
                                 sentiment_df: Optional[pd.DataFrame] = None,
                                 factor_neutralized_df: Optional[pd.DataFrame] = None,
                                 vol_target_df: Optional[pd.DataFrame] = None,
                                 microstructure_df: Optional[pd.DataFrame] = None,
                                 accruals_quality_df: Optional[pd.DataFrame] = None,
                                 short_squeeze_df: Optional[pd.DataFrame] = None,
                                 valueup_catalyst_df: Optional[pd.DataFrame] = None,
                                 trend_efficiency_df: Optional[pd.DataFrame] = None,
                                 gamma_squeeze_df: Optional[pd.DataFrame] = None,
                                 insider_buying_df: Optional[pd.DataFrame] = None,
                                 darkpool_df: Optional[pd.DataFrame] = None,
                                 earnings_tone_drift_df: Optional[pd.DataFrame] = None,
                                 rolling_sharpes: Optional[Dict[str, float]] = None,
                                 sentiment_blacklist: Optional[Union[List[str], Dict[str, Any]]] = None,
                                 target_horizon: int = 20,
                                 gamma: float = 1.0,
                                 held_symbols: Optional[Union[Set[str], List[str]]] = None,
                                 us_regime: Optional[Union[int, str]] = None,
                                 kr_regime: Optional[Union[int, str]] = None,
                                 decoupling_status: Optional[str] = None,
                                 dual_regimes: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Calculates 31-Strategy Dynamic Weighted Ensemble Score [0, 1] per stock.
        Supports dual market regime weighting for US (SP500/NASDAQ/RUSSELL2000) and KR (KOSPI/KOSDAQ).
        """
        v_rule_input = vcp_patterns_df if vcp_patterns_df is not None else vcp_rule_df

        # Resolve dual market regimes
        if dual_regimes:
            us_regime = us_regime if us_regime is not None else dual_regimes.get('us_regime', {}).get('combo_2d_label')
            kr_regime = kr_regime if kr_regime is not None else dual_regimes.get('kr_regime', {}).get('combo_2d_label')
            decoupling_status = decoupling_status if decoupling_status is not None else dual_regimes.get('decoupling_status', 'COUPLED')

        eff_us_regime = us_regime if us_regime is not None else (regime if regime is not None else 'BULL_LOW_VOL')
        eff_kr_regime = kr_regime if kr_regime is not None else (regime if regime is not None else 'SIDEWAYS_LOW_VOL')
        eff_decoupling = decoupling_status if decoupling_status is not None else 'COUPLED'

        us_weights = self.compute_dynamic_weights_from_sharpe(rolling_sharpes or {}, eff_us_regime, gamma=gamma)
        kr_weights = self.compute_dynamic_weights_from_sharpe(rolling_sharpes or {}, eff_kr_regime, gamma=gamma)

        # Apply Decoupling Alpha Tilts if active
        if eff_decoupling == 'DECOUPLING_US_BULL_KR_BEAR':
            # US Bull: amplify momentum & breakout
            for st in ['surge', 'vcp_ml', 'trend_efficiency', 'gamma_squeeze']:
                if st in us_weights:
                    us_weights[st] += 0.015
            # KR Bear: amplify defensive valuation, foreign flow, supply chain & reversal
            for st in ['rim_valuation', 'valueup_catalyst', 'order_flow', 'supply_chain', 'short_term_reversal']:
                if st in kr_weights:
                    kr_weights[st] += 0.015

            us_sum = sum(us_weights.values())
            if us_sum > 0:
                us_weights = {k: v / us_sum for k, v in us_weights.items()}
            kr_sum = sum(kr_weights.values())
            if kr_sum > 0:
                kr_weights = {k: v / kr_sum for k, v in kr_weights.items()}

        elif eff_decoupling == 'DECOUPLING_KR_BULL_US_BEAR':
            # KR Bull: amplify sector rotation & valueup
            for st in ['sector_rotation', 'valueup_catalyst', 'mq_factor']:
                if st in kr_weights:
                    kr_weights[st] += 0.02
            # US Bear: amplify factor neutralized & vol targeting
            for st in ['factor_neutralized', 'vol_target', 'stat_arb']:
                if st in us_weights:
                    us_weights[st] += 0.02

            us_sum = sum(us_weights.values())
            if us_sum > 0:
                us_weights = {k: v / us_sum for k, v in us_weights.items()}
            kr_sum = sum(kr_weights.values())
            if kr_sum > 0:
                kr_weights = {k: v / kr_sum for k, v in kr_weights.items()}

        self.us_strategy_weights = us_weights
        self.kr_strategy_weights = kr_weights
        self.strategy_weights = us_weights

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
            supply_chain_df=supply_chain_df,
            sentiment_df=sentiment_df,
            factor_neutralized_df=factor_neutralized_df,
            vol_target_df=vol_target_df,
            microstructure_df=microstructure_df,
            accruals_quality_df=accruals_quality_df,
            short_squeeze_df=short_squeeze_df,
            valueup_catalyst_df=valueup_catalyst_df,
            trend_efficiency_df=trend_efficiency_df,
            gamma_squeeze_df=gamma_squeeze_df,
            insider_buying_df=insider_buying_df,
            darkpool_df=darkpool_df,
            earnings_tone_drift_df=earnings_tone_drift_df,
            weights=us_weights,
            us_weights=us_weights,
            kr_weights=kr_weights,
            regime=regime,
            us_regime=eff_us_regime,
            kr_regime=eff_kr_regime,
            decoupling_status=eff_decoupling,
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
                            supply_chain_df: Optional[pd.DataFrame] = None,
                            sentiment_df: Optional[pd.DataFrame] = None,
                            factor_neutralized_df: Optional[pd.DataFrame] = None,
                            vol_target_df: Optional[pd.DataFrame] = None,
                            microstructure_df: Optional[pd.DataFrame] = None,
                            accruals_quality_df: Optional[pd.DataFrame] = None,
                            short_squeeze_df: Optional[pd.DataFrame] = None,
                            valueup_catalyst_df: Optional[pd.DataFrame] = None,
                            trend_efficiency_df: Optional[pd.DataFrame] = None,
                            gamma_squeeze_df: Optional[pd.DataFrame] = None,
                            insider_buying_df: Optional[pd.DataFrame] = None,
                            darkpool_df: Optional[pd.DataFrame] = None,
                            earnings_tone_drift_df: Optional[pd.DataFrame] = None,
                            weights: Optional[Dict[str, float]] = None,
                            us_weights: Optional[Dict[str, float]] = None,
                            kr_weights: Optional[Dict[str, float]] = None,
                            regime: Union[int, str] = 'BULL_LOW_VOL',
                            us_regime: Optional[Union[int, str]] = None,
                            kr_regime: Optional[Union[int, str]] = None,
                            decoupling_status: Optional[str] = None,
                            target_horizon: int = 20,
                            sentiment_blacklist: Optional[Union[List[str], Dict[str, Any]]] = None,
                            held_symbols: Optional[Union[Set[str], List[str]]] = None) -> pd.DataFrame:
        """
        Merges 27 strategy prediction DataFrames and computes weighted ensemble score.
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
            vcp_ml_df = pd.DataFrame()
        if lstm_df is None:
            lstm_df = pd.DataFrame()

        META_COLS = ['name', 'market', 'close', 'expected_return', 'expected_return_20d', 'win_rate', 'win_rate_20d']

        # 1. Regression Strategy
        reg_df_copy = reg_df.copy()
        if not reg_df_copy.empty and 'reg_score' not in reg_df_copy.columns:
            target_col: Any = None
            if f'expected_return_{target_horizon}d' in reg_df_copy.columns:
                target_col = f'expected_return_{target_horizon}d'
            elif 'expected_return' in reg_df_copy.columns:
                target_col = 'expected_return'
            elif target_horizon in reg_df_copy.columns:
                target_col = target_horizon
            elif str(target_horizon) in reg_df_copy.columns:
                target_col = str(target_horizon)
            else:
                exp_cols = [c for c in reg_df_copy.columns if isinstance(c, str) and c.startswith('expected_return')]
                if not exp_cols:
                    exp_cols = [c for c in reg_df_copy.columns if c != 'symbol' and c not in META_COLS]
                target_col = exp_cols[0] if exp_cols else None

            if target_col is not None and target_col in reg_df_copy.columns:
                ret_multiplier = self._return_multiplier
                reg_df_copy['reg_score'] = (reg_df_copy[target_col] * ret_multiplier).clip(0.0, 1.0)
            else:
                reg_df_copy['reg_score'] = 0.5

        # 2. Surge Strategy
        s_df_copy = s_df.copy()
        if not s_df_copy.empty and 'surge_score' not in s_df_copy.columns:
            target_col_surge: Any = None
            if f'surge_prob_{target_horizon}d' in s_df_copy.columns:
                target_col_surge = f'surge_prob_{target_horizon}d'
            elif f'surge_{target_horizon}d' in s_df_copy.columns:
                target_col_surge = f'surge_{target_horizon}d'
            elif 'surge_probability' in s_df_copy.columns:
                target_col_surge = 'surge_probability'
            elif target_horizon in s_df_copy.columns:
                target_col_surge = target_horizon
            elif str(target_horizon) in s_df_copy.columns:
                target_col_surge = str(target_horizon)
            else:
                prob_cols = [c for c in s_df_copy.columns if isinstance(c, str) and ('prob' in c or 'surge' in c)]
                if not prob_cols:
                    prob_cols = [c for c in s_df_copy.columns if c != 'symbol' and c not in META_COLS]
                target_col_surge = prob_cols[0] if prob_cols else None

            if target_col_surge is not None and target_col_surge in s_df_copy.columns:
                s_df_copy['surge_score'] = s_df_copy[target_col_surge].clip(0.0, 1.0)
            else:
                s_df_copy['surge_score'] = 0.5

        # 3. Lead-Lag Strategy
        ll_df_copy = ll_df.copy()
        if not ll_df_copy.empty and 'll_score' not in ll_df_copy.columns:
            target_col = 'lead_lag_score' if 'lead_lag_score' in ll_df_copy.columns else ('follower_score' if 'follower_score' in ll_df_copy.columns else None)
            if target_col and target_col in ll_df_copy.columns:
                ll_df_copy['ll_score'] = ll_df_copy[target_col].clip(0.0, 1.0)
            else:
                ll_df_copy['ll_score'] = 0.5

        # 4. VCP Rule-based Pattern Strategy
        if isinstance(v_rule_df, list):
            if v_rule_df and isinstance(v_rule_df[0], dict):
                vr_rows = []
                for _vrec in v_rule_df:
                    if not isinstance(_vrec, dict):
                        continue
                    _vsym = _vrec.get('symbol')
                    if not _vsym:
                        continue
                    try:
                        _vscore = float(_vrec.get('vcp_score', 100.0))
                    except Exception:
                        _vscore = 100.0
                    if _vscore > 1.0:
                        _vscore = _vscore / 100.0
                    vr_rows.append({'symbol': str(_vsym), 'vcp_rule_score': max(0.0, min(1.0, _vscore))})
                vr_df = pd.DataFrame(vr_rows, columns=['symbol', 'vcp_rule_score'])
            else:
                vr_df = pd.DataFrame({'symbol': [str(s) for s in v_rule_df], 'vcp_rule_score': 1.0})
        elif isinstance(v_rule_df, pd.DataFrame) and not v_rule_df.empty:
            vr_df = v_rule_df.copy()
            if 'vcp_rule_score' not in vr_df.columns:
                target_col = 'vcp_score' if 'vcp_score' in vr_df.columns else ('score' if 'score' in vr_df.columns else None)
                if target_col and target_col in vr_df.columns:
                    max_val = vr_df[target_col].max()
                    if max_val > 1.0:
                        vr_df['vcp_rule_score'] = (vr_df[target_col] / 100.0).clip(0.0, 1.0)
                    else:
                        vr_df['vcp_rule_score'] = vr_df[target_col].clip(0.0, 1.0)
                else:
                    vr_df['vcp_rule_score'] = 1.0
        else:
            vr_df = pd.DataFrame(columns=['symbol', 'vcp_rule_score'])

        # 5. VCP ML Strategy
        if not vcp_ml_df.empty:
            v_df = vcp_ml_df.copy()
            if 'vcp_ml_score' not in v_df.columns:
                target_col = None
                for c_cand in [f'vcp_prob_{target_horizon}d', f'vcp_{target_horizon}d', 'vcp_surge_prob', 'vcp_prob', 'surge_prob', 'prob']:
                    if c_cand in v_df.columns:
                        target_col = c_cand
                        break
                if target_col and target_col in v_df.columns:
                    v_df['vcp_ml_score'] = v_df[target_col].clip(0.0, 1.0)
                else:
                    num_cols = [c for c in v_df.columns if c != 'symbol' and pd.api.types.is_numeric_dtype(v_df[c])]
                    target_col = num_cols[0] if num_cols else None
                    if target_col:
                        v_df['vcp_ml_score'] = v_df[target_col].clip(0.0, 1.0)
                    else:
                        v_df['vcp_ml_score'] = 0.5
        else:
            v_df = pd.DataFrame(columns=['symbol', 'vcp_ml_score'])

        # 6. Strict Causal LSTM Strategy
        if lstm_df is not None and not lstm_df.empty:
            l_df = lstm_df.copy()
            target_col = 'lstm_score' if 'lstm_score' in l_df.columns else ('expected_return' if 'expected_return' in l_df.columns else None)
            if target_col and target_col in l_df.columns:
                if target_col == 'expected_return':
                    l_df['lstm_score'] = (l_df[target_col] * self._return_multiplier).clip(0.0, 1.0)
                else:
                    l_df['lstm_score'] = l_df[target_col].clip(0.0, 1.0)

                # Strict Causal LSTM Trend Momentum Booster (Top 15% Deep Learning Trend Signals)
                lstm_trend_mask = l_df['lstm_score'] >= 0.70
                if lstm_trend_mask.any():
                    l_df.loc[lstm_trend_mask, 'lstm_score'] = (l_df.loc[lstm_trend_mask, 'lstm_score'] * 1.08).clip(0.0, 1.0)
            else:
                l_df['lstm_score'] = 0.5
        else:
            l_df = pd.DataFrame(columns=['symbol', 'lstm_score'])

        # 7. Stat-Arb Cointegration Strategy
        if stat_arb_df is not None and not stat_arb_df.empty:
            sa_df = stat_arb_df.copy()
            target_col = 'stat_arb_score' if 'stat_arb_score' in sa_df.columns else ('z_score' if 'z_score' in sa_df.columns else None)
            if target_col and target_col in sa_df.columns:
                if target_col == 'z_score':
                    sa_df['stat_arb_score'] = (np.abs(sa_df[target_col]) / 3.0).clip(0.0, 1.0)
                else:
                    sa_df['stat_arb_score'] = sa_df[target_col].clip(0.0, 1.0)
            else:
                sa_df['stat_arb_score'] = 0.5
        else:
            sa_df = pd.DataFrame(columns=['symbol', 'stat_arb_score'])

        # 8. Sector Rotation Relative Momentum Strategy
        if sector_df is not None and not sector_df.empty:
            sec_df = sector_df.copy()
            target_col = 'sector_score' if 'sector_score' in sec_df.columns else ('sector_momentum' if 'sector_momentum' in sec_df.columns else None)
            if target_col and target_col in sec_df.columns:
                sec_df['sector_score'] = sec_df[target_col].clip(0.0, 1.0)
            else:
                sec_df['sector_score'] = 0.5
        else:
            sec_df = pd.DataFrame(columns=['symbol', 'sector_score'])

        # 9. Strategy 9: RIM Valuation Strategy
        if rim_df is not None and not rim_df.empty:
            r_val_df = rim_df.copy()
            num_cols = [c for c in r_val_df.columns if c != 'symbol' and c not in META_COLS]
            r_col = 'rim_score' if 'rim_score' in r_val_df.columns else (num_cols[-1] if num_cols else r_val_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in r_val_df.columns]
            r_val_df = r_val_df[['symbol'] + meta_cols + [r_col]].rename(columns={r_col: 'rim_score'})
        else:
            r_val_df = pd.DataFrame(columns=['symbol', 'rim_score'])

        # 10. Strategy 10: Event-Driven Catalyst Strategy
        if event_df is not None and not event_df.empty:
            ev_df = event_df.copy()
            num_cols = [c for c in ev_df.columns if c != 'symbol' and c not in META_COLS]
            ev_col = 'event_score' if 'event_score' in ev_df.columns else (num_cols[-1] if num_cols else ev_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in ev_df.columns]
            ev_df = ev_df[['symbol'] + meta_cols + [ev_col]].rename(columns={ev_col: 'event_score'})
        else:
            ev_df = pd.DataFrame(columns=['symbol', 'event_score'])

        # 11. Strategy 11: Momentum Quality (MQ) Strategy
        if mq_df is not None and not mq_df.empty:
            m_df = mq_df.copy()
            num_cols = [c for c in m_df.columns if c != 'symbol' and c not in META_COLS]
            m_col = 'mq_score' if 'mq_score' in m_df.columns else (num_cols[-1] if num_cols else m_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in m_df.columns]
            m_df = m_df[['symbol'] + meta_cols + [m_col]].rename(columns={m_col: 'mq_score'})
        else:
            m_df = pd.DataFrame(columns=['symbol', 'mq_score'])

        # 12. Strategy 12: Options IV Skew Strategy
        if iv_skew_df is not None and not iv_skew_df.empty:
            iv_df = iv_skew_df.copy()
            num_cols = [c for c in iv_df.columns if c != 'symbol' and c not in META_COLS]
            iv_col = 'iv_skew_score' if 'iv_skew_score' in iv_df.columns else (num_cols[-1] if num_cols else iv_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in iv_df.columns]
            iv_df = iv_df[['symbol'] + meta_cols + [iv_col]].rename(columns={iv_col: 'iv_skew_score'})
        else:
            iv_df = pd.DataFrame(columns=['symbol', 'iv_skew_score'])

        # 13. Strategy 13: Order Flow Imbalance Strategy
        if order_flow_df is not None and not order_flow_df.empty:
            of_df = order_flow_df.copy()
            num_cols = [c for c in of_df.columns if c != 'symbol' and c not in META_COLS]
            of_col = 'order_flow_score' if 'order_flow_score' in of_df.columns else (num_cols[-1] if num_cols else of_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in of_df.columns]
            of_df = of_df[['symbol'] + meta_cols + [of_col]].rename(columns={of_col: 'order_flow_score'})
        else:
            of_df = pd.DataFrame(columns=['symbol', 'order_flow_score'])

        # 14. Strategy 14: Short-Term Reversal Strategy
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

        # 19. Strategy 19: Supply Chain Lead-Lag Momentum
        if supply_chain_df is not None and not supply_chain_df.empty:
            sc_df = supply_chain_df.copy()
            num_cols = [c for c in sc_df.columns if c != 'symbol' and c not in META_COLS]
            sc_col = 'supply_chain_score' if 'supply_chain_score' in sc_df.columns else (num_cols[-1] if num_cols else sc_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in sc_df.columns]
            sc_df = sc_df[['symbol'] + meta_cols + [sc_col]].rename(columns={sc_col: 'supply_chain_score'})
            if sc_df['supply_chain_score'].max() > 1.0:
                sc_df['supply_chain_score'] = sc_df['supply_chain_score'] / 100.0
        else:
            sc_df = pd.DataFrame(columns=['symbol', 'supply_chain_score'])

        # 20. Strategy 20: NLP & FinBERT Sentiment Catalyst
        if sentiment_df is not None and not sentiment_df.empty:
            sent_df = sentiment_df.copy()
            num_cols = [c for c in sent_df.columns if c != 'symbol' and c not in META_COLS]
            sent_col = 'sentiment_score' if 'sentiment_score' in sent_df.columns else (num_cols[-1] if num_cols else sent_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in sent_df.columns]
            sent_df = sent_df[['symbol'] + meta_cols + [sent_col]].rename(columns={sent_col: 'sentiment_score'})
            if sent_df['sentiment_score'].max() > 1.0:
                sent_df['sentiment_score'] = sent_df['sentiment_score'] / 100.0
        else:
            sent_df = pd.DataFrame(columns=['symbol', 'sentiment_score'])

        # 21. Strategy 21: Multi-Factor Style Neutralizer
        if factor_neutralized_df is not None and not factor_neutralized_df.empty:
            fn_df = factor_neutralized_df.copy()
            num_cols = [c for c in fn_df.columns if c != 'symbol' and c not in META_COLS]
            fn_col = 'factor_neutralized_score' if 'factor_neutralized_score' in fn_df.columns else ('neutralized_score' if 'neutralized_score' in fn_df.columns else (num_cols[-1] if num_cols else fn_df.columns[-1]))
            meta_cols = [c for c in META_COLS if c in fn_df.columns]
            fn_df = fn_df[['symbol'] + meta_cols + [fn_col]].rename(columns={fn_col: 'factor_neutralized_score'})
            if fn_df['factor_neutralized_score'].max() > 1.0:
                fn_df['factor_neutralized_score'] = fn_df['factor_neutralized_score'] / 100.0
        else:
            fn_df = pd.DataFrame(columns=['symbol', 'factor_neutralized_score'])

        # 22. Strategy 22: Dynamic Volatility Targeting
        if vol_target_df is not None and not vol_target_df.empty:
            vt_df = vol_target_df.copy()
            num_cols = [c for c in vt_df.columns if c != 'symbol' and c not in META_COLS]
            vt_col = 'vol_target_score' if 'vol_target_score' in vt_df.columns else (num_cols[-1] if num_cols else vt_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in vt_df.columns]
            vt_df = vt_df[['symbol'] + meta_cols + [vt_col]].rename(columns={vt_col: 'vol_target_score'})
            if vt_df['vol_target_score'].max() > 1.0:
                vt_df['vol_target_score'] = vt_df['vol_target_score'] / 100.0
        else:
            vt_df = pd.DataFrame(columns=['symbol', 'vol_target_score'])

        # 23. Strategy 23: Order Book Microstructure Imbalance
        if microstructure_df is not None and not microstructure_df.empty:
            micro_df = microstructure_df.copy()
            num_cols = [c for c in micro_df.columns if c != 'symbol' and c not in META_COLS]
            micro_col = 'microstructure_score' if 'microstructure_score' in micro_df.columns else (num_cols[-1] if num_cols else micro_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in micro_df.columns]
            micro_df = micro_df[['symbol'] + meta_cols + [micro_col]].rename(columns={micro_col: 'microstructure_score'})
            if micro_df['microstructure_score'].max() > 1.0:
                micro_df['microstructure_score'] = micro_df['microstructure_score'] / 100.0
        else:
            micro_df = pd.DataFrame(columns=['symbol', 'microstructure_score'])

        # 24. Strategy 24: Accruals Quality Anomaly Engine
        if accruals_quality_df is not None and not accruals_quality_df.empty:
            aq_df = accruals_quality_df.copy()
            num_cols = [c for c in aq_df.columns if c != 'symbol' and c not in META_COLS]
            aq_col = 'accruals_quality_score' if 'accruals_quality_score' in aq_df.columns else (num_cols[-1] if num_cols else aq_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in aq_df.columns]
            aq_df = aq_df[['symbol'] + meta_cols + [aq_col]].rename(columns={aq_col: 'accruals_quality_score'})
            if aq_df['accruals_quality_score'].max() > 1.0:
                aq_df['accruals_quality_score'] = aq_df['accruals_quality_score'] / 100.0
        else:
            aq_df = pd.DataFrame(columns=['symbol', 'accruals_quality_score'])

        # 25. Strategy 25: Short Interest & Squeeze Engine
        if short_squeeze_df is not None and not short_squeeze_df.empty:
            sq_df = short_squeeze_df.copy()
            num_cols = [c for c in sq_df.columns if c != 'symbol' and c not in META_COLS]
            sq_col = 'short_squeeze_score' if 'short_squeeze_score' in sq_df.columns else (num_cols[-1] if num_cols else sq_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in sq_df.columns]
            sq_df = sq_df[['symbol'] + meta_cols + [sq_col]].rename(columns={sq_col: 'short_squeeze_score'})
            if sq_df['short_squeeze_score'].max() > 1.0:
                sq_df['short_squeeze_score'] = sq_df['short_squeeze_score'] / 100.0
        else:
            sq_df = pd.DataFrame(columns=['symbol', 'short_squeeze_score'])

        # 26. Strategy 26: Value-Up & Shareholder Yield Catalyst
        if valueup_catalyst_df is not None and not valueup_catalyst_df.empty:
            vu_df = valueup_catalyst_df.copy()
            num_cols = [c for c in vu_df.columns if c != 'symbol' and c not in META_COLS]
            vu_col = 'valueup_catalyst_score' if 'valueup_catalyst_score' in vu_df.columns else (num_cols[-1] if num_cols else vu_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in vu_df.columns]
            vu_df = vu_df[['symbol'] + meta_cols + [vu_col]].rename(columns={vu_col: 'valueup_catalyst_score'})
            if vu_df['valueup_catalyst_score'].max() > 1.0:
                vu_df['valueup_catalyst_score'] = vu_df['valueup_catalyst_score'] / 100.0
        else:
            vu_df = pd.DataFrame(columns=['symbol', 'valueup_catalyst_score'])

        # 27. Strategy 27: Kaufman Trend Efficiency Engine
        if trend_efficiency_df is not None and not trend_efficiency_df.empty:
            te_df = trend_efficiency_df.copy()
            num_cols = [c for c in te_df.columns if c != 'symbol' and c not in META_COLS]
            te_col = 'trend_efficiency_score' if 'trend_efficiency_score' in te_df.columns else (num_cols[-1] if num_cols else te_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in te_df.columns]
            te_df = te_df[['symbol'] + meta_cols + [te_col]].rename(columns={te_col: 'trend_efficiency_score'})
            if te_df['trend_efficiency_score'].max() > 1.0:
                te_df['trend_efficiency_score'] = te_df['trend_efficiency_score'] / 100.0
        else:
            te_df = pd.DataFrame(columns=['symbol', 'trend_efficiency_score'])

        # 28. Strategy 28: Options Gamma Squeeze Engine
        if gamma_squeeze_df is not None and not gamma_squeeze_df.empty:
            gs_df = gamma_squeeze_df.copy()
            num_cols = [c for c in gs_df.columns if c != 'symbol' and c not in META_COLS]
            gs_col = 'gamma_squeeze_score' if 'gamma_squeeze_score' in gs_df.columns else (num_cols[-1] if num_cols else gs_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in gs_df.columns]
            gs_df = gs_df[['symbol'] + meta_cols + [gs_col]].rename(columns={gs_col: 'gamma_squeeze_score'})
            if gs_df['gamma_squeeze_score'].max() > 1.0:
                gs_df['gamma_squeeze_score'] = gs_df['gamma_squeeze_score'] / 100.0
        else:
            gs_df = pd.DataFrame(columns=['symbol', 'gamma_squeeze_score'])

        # 29. Strategy 29: Insider Buying Engine
        if insider_buying_df is not None and not insider_buying_df.empty:
            ib_df = insider_buying_df.copy()
            num_cols = [c for c in ib_df.columns if c != 'symbol' and c not in META_COLS]
            ib_col = 'insider_buying_score' if 'insider_buying_score' in ib_df.columns else (num_cols[-1] if num_cols else ib_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in ib_df.columns]
            ib_df = ib_df[['symbol'] + meta_cols + [ib_col]].rename(columns={ib_col: 'insider_buying_score'})
            if ib_df['insider_buying_score'].max() > 1.0:
                ib_df['insider_buying_score'] = ib_df['insider_buying_score'] / 100.0
        else:
            ib_df = pd.DataFrame(columns=['symbol', 'insider_buying_score'])

        # 30. Strategy 30: Dark Pool Divergence Engine
        if darkpool_df is not None and not darkpool_df.empty:
            dp_df = darkpool_df.copy()
            num_cols = [c for c in dp_df.columns if c != 'symbol' and c not in META_COLS]
            dp_col = 'darkpool_score' if 'darkpool_score' in dp_df.columns else (num_cols[-1] if num_cols else dp_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in dp_df.columns]
            dp_df = dp_df[['symbol'] + meta_cols + [dp_col]].rename(columns={dp_col: 'darkpool_score'})
            if dp_df['darkpool_score'].max() > 1.0:
                dp_df['darkpool_score'] = dp_df['darkpool_score'] / 100.0
        else:
            dp_df = pd.DataFrame(columns=['symbol', 'darkpool_score'])

        # 31. Strategy 31: Earnings Tone Drift Engine
        if earnings_tone_drift_df is not None and not earnings_tone_drift_df.empty:
            etd_df = earnings_tone_drift_df.copy()
            num_cols = [c for c in etd_df.columns if c != 'symbol' and c not in META_COLS]
            etd_col = 'earnings_tone_drift_score' if 'earnings_tone_drift_score' in etd_df.columns else (num_cols[-1] if num_cols else etd_df.columns[-1])
            meta_cols = [c for c in META_COLS if c in etd_df.columns]
            etd_df = etd_df[['symbol'] + meta_cols + [etd_col]].rename(columns={etd_col: 'earnings_tone_drift_score'})
            if etd_df['earnings_tone_drift_score'].max() > 1.0:
                etd_df['earnings_tone_drift_score'] = etd_df['earnings_tone_drift_score'] / 100.0
        else:
            etd_df = pd.DataFrame(columns=['symbol', 'earnings_tone_drift_score'])

        # Combine all 31 strategy DataFrames efficiently while preserving metadata
        dfs = [reg_df_copy, s_df_copy, ll_df_copy, vr_df, v_df, l_df, sa_df, sec_df, r_val_df, ev_df, m_df, iv_df, of_df, rev_df, a_df, c_df, la_df, ifs_df, sc_df, sent_df, fn_df, vt_df, micro_df, aq_df, sq_df, vu_df, te_df, gs_df, ib_df, dp_df, etd_df]
        valid_dfs = []
        for d in dfs:
            if d is not None and not d.empty and 'symbol' in d.columns:
                d_idx = d.copy()
                d_idx['symbol'] = d_idx['symbol'].astype(str)
                d_idx = d_idx.drop_duplicates(subset=['symbol']).set_index('symbol')
                valid_dfs.append(d_idx)

        if valid_dfs:
            merged = pd.concat(valid_dfs, axis=1)
            if merged.columns.has_duplicates:
                merged = merged.loc[:, ~merged.columns.duplicated(keep='first')]
            merged = merged.reset_index()
        else:
            merged = pd.DataFrame(columns=['symbol'])

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
            ('supply_chain', 'supply_chain_score'),
            ('sentiment', 'sentiment_score'),
            ('factor_neutralized', 'factor_neutralized_score'),
            ('vol_target', 'vol_target_score'),
            ('microstructure', 'microstructure_score'),
            ('accruals_quality', 'accruals_quality_score'),
            ('short_squeeze', 'short_squeeze_score'),
            ('valueup_catalyst', 'valueup_catalyst_score'),
            ('trend_efficiency', 'trend_efficiency_score'),
            ('gamma_squeeze', 'gamma_squeeze_score'),
            ('insider_buying', 'insider_buying_score'),
            ('darkpool', 'darkpool_score'),
            ('earnings_tone_drift', 'earnings_tone_drift_score'),
        ]

        # Phase 3-A: Cross-Sectional Robust Winsorization (0.5% - 99.5% quantile clipping for N >= 20)
        if len(merged) >= 20:
            for _, score_col in strategy_cols:
                if score_col in merged.columns:
                    valid_vals = merged[score_col].dropna()
                    if len(valid_vals) >= 20:
                        q_low = float(np.percentile(valid_vals, 0.5))
                        q_high = float(np.percentile(valid_vals, 99.5))
                        if q_high > q_low:
                            merged[score_col] = merged[score_col].clip(lower=q_low, upper=q_high)

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

        # Phase 3-B.1: Strategy Correlation Orthogonalization Penalty
        weights = self.apply_correlation_orthogonalization_penalty(
            weights,
            scores_df=merged,
            correlation_threshold=0.65,
            penalty_factor=0.5,
        )

        # Phase 3-C: Inter-Strategy Signal Correlation Monitoring & 2D Regime Noise Suppression
        if len(merged) >= 5:
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

        # Dynamic Weight Renormalization & Missingness-Aware Coverage Penalization (Market-Specific Dual Weights)
        total_score_series = pd.Series(0.0, index=merged.index)
        total_weight_series = pd.Series(0.0, index=merged.index)
        valid_count_series = pd.Series(0.0, index=merged.index)

        present_strategy_cols = [score_col for _, score_col in strategy_cols if score_col in merged.columns and merged[score_col].notna().any()]
        num_present_strats = max(float(len(present_strategy_cols)), 1.0)

        eff_us_weights = us_weights if us_weights is not None else (weights if weights is not None else self.REGIME_2D_WEIGHTS.get('BULL_LOW_VOL', {}))
        eff_kr_weights = kr_weights if kr_weights is not None else (weights if weights is not None else self.REGIME_2D_WEIGHTS.get('SIDEWAYS_LOW_VOL', {}))

        # Identify KR vs US symbols for dual-regime weights
        is_kr = pd.Series(False, index=merged.index)
        if 'market' in merged.columns:
            is_kr = merged['market'].astype(str).str.upper().isin(['KOSPI', 'KOSDAQ'])
        elif 'symbol' in merged.columns:
            is_kr = merged['symbol'].astype(str).str.match(r'^\d{6}$') | merged['symbol'].astype(str).str.endswith(('.KS', '.KQ'))

        default_strat_w = 1.0 / max(float(len(strategy_cols)), 1.0)
        for strat_name, score_col in strategy_cols:
            w_us = eff_us_weights.get(strat_name, default_strat_w)
            w_kr = eff_kr_weights.get(strat_name, default_strat_w)
            w_series = pd.Series(np.where(is_kr, w_kr, w_us), index=merged.index)

            if score_col in merged.columns:
                # Fix Task 1: Valid 0.0 scores must NOT be discarded as missing data.
                valid_mask = merged[score_col].notna() & np.isfinite(merged[score_col])
                clean_score = np.where(valid_mask, merged[score_col], 0.0)
                total_score_series += clean_score * w_series
                total_weight_series += w_series * valid_mask.astype(float)
                valid_count_series += valid_mask.astype(float)

        # Avoid division by zero: if no strategy scores exist, score is 0.0
        safe_weight_series = total_weight_series.replace(0.0, np.nan)
        linear_score = (total_score_series / safe_weight_series).fillna(0.0).clip(0.0, 1.0)

        # Apply coverage factor relative to present strategy DataFrames
        coverage_ratio = valid_count_series / num_present_strats
        coverage_penalty = np.where(coverage_ratio < 0.40, 0.5 + 0.5 * (coverage_ratio / 0.40), 1.0)
        linear_score = pd.Series(linear_score * coverage_penalty, index=merged.index).clip(0.0, 1.0)

        # 3-Tier Multi-Horizon Alpha Score Decomposition (Slow, Medium, Fast)
        slow_cols = [sc for sn, sc in strategy_cols if sn in self.ALPHA_HORIZON_TIERS['slow'] and sc in merged.columns]
        med_cols = [sc for sn, sc in strategy_cols if sn in self.ALPHA_HORIZON_TIERS['medium'] and sc in merged.columns]
        fast_cols = [sc for sn, sc in strategy_cols if sn in self.ALPHA_HORIZON_TIERS['fast'] and sc in merged.columns]

        if slow_cols or med_cols or fast_cols:
            def _calc_tier_score(cols_list):
                if not cols_list:
                    return None
                sub_df = merged[cols_list]
                v_mask = sub_df.notna() & np.isfinite(sub_df)
                v_counts = v_mask.sum(axis=1)
                sub_sums = np.where(v_mask, sub_df.values, 0.0).sum(axis=1)
                return np.where(v_counts > 0, sub_sums / np.maximum(v_counts, 1), np.nan)

            s_slow = _calc_tier_score(slow_cols)
            s_med = _calc_tier_score(med_cols)
            s_fast = _calc_tier_score(fast_cols)

            if s_slow is not None:
                merged['slow_alpha_score'] = np.nan_to_num(s_slow, nan=0.5)
            if s_med is not None:
                merged['medium_alpha_score'] = np.nan_to_num(s_med, nan=0.5)
            if s_fast is not None:
                merged['fast_alpha_score'] = np.nan_to_num(s_fast, nan=0.5)
                fast_tilt = np.clip(merged['fast_alpha_score'] - 0.50, -0.15, 0.15)
                if len(merged) >= 5 and 'slow_alpha_score' in merged.columns and 'medium_alpha_score' in merged.columns:
                    hierarchical_score = (
                        self.TIER_WEIGHTS['slow'] * merged['slow_alpha_score'] +
                        self.TIER_WEIGHTS['medium'] * merged['medium_alpha_score']
                    ) * (1.0 + fast_tilt)
                    hierarchical_score = hierarchical_score.clip(0.0, 1.0)
                    linear_score = pd.Series(0.70 * linear_score + 0.30 * hierarchical_score, index=merged.index).clip(0.0, 1.0)

        # Phase 1: 2nd Stage Stacking Meta-Learner Hybrid Blend
        explicit_weights_provided = (weights is not None and len(weights) > 0 and len(merged) < 5)
        try:
            meta_learner = MetaEnsembleLearner()
            if meta_learner.is_fitted and not explicit_weights_provided:
                meta_score = meta_learner.predict(merged)
                meta_weight = 0.50
                if hasattr(meta_learner, 'oob_score_') and pd.notna(meta_learner.oob_score_):
                    meta_weight = float(np.clip(meta_learner.oob_score_, 0.30, 0.75))
                blended_score = pd.Series(
                    (1.0 - meta_weight) * linear_score + meta_weight * meta_score,
                    index=merged.index
                ).clip(0.0, 1.0)
            else:
                blended_score = linear_score
        except Exception as e:
            logger.warning(f"MetaEnsembleLearner prediction fallback to linear score: {e}")
            blended_score = linear_score

        # Phase 2: Convex Multi-Signal Synergy Boost (for real datasets with len >= 5)
        if len(merged) >= 5:
            try:
                # Count strong signals (> 0.65) across independent active strategy columns
                high_signal_mask = pd.DataFrame(0, index=merged.index, columns=[sc for _, sc in strategy_cols if sc in merged.columns])
                for _, sc in strategy_cols:
                    if sc in merged.columns:
                        high_signal_mask[sc] = (merged[sc] >= 0.65).astype(int)
                strong_signal_counts = high_signal_mask.sum(axis=1)

                # Apply convex super-linear boost for multi-factor confluence (3+ signals)
                synergy_multiplier = np.where(strong_signal_counts >= 3, 1.0 + 0.03 * (strong_signal_counts - 2), 1.0)
                blended_score = pd.Series((blended_score * synergy_multiplier), index=merged.index).clip(0.0, 1.0)

                # Phase 2-B: Triple Confirmation Alpha Booster (Valuation + Momentum + Institutional Flow)
                has_val = pd.Series(False, index=merged.index)
                if 'rim_score' in merged.columns:
                    has_val = has_val | merged['rim_score'].ge(0.60)
                if 'valueup_catalyst_score' in merged.columns:
                    has_val = has_val | merged['valueup_catalyst_score'].ge(0.60)
                if 'arm_score' in merged.columns:
                    has_val = has_val | merged['arm_score'].ge(0.60)

                has_mom = pd.Series(False, index=merged.index)
                if 'mq_score' in merged.columns:
                    has_mom = has_mom | merged['mq_score'].ge(0.60)
                if 'trend_efficiency_score' in merged.columns:
                    has_mom = has_mom | merged['trend_efficiency_score'].ge(0.60)
                if 'surge_score' in merged.columns:
                    has_mom = has_mom | merged['surge_score'].ge(0.60)
                if 'vcp_ml_score' in merged.columns:
                    has_mom = has_mom | merged['vcp_ml_score'].ge(0.60)

                has_flow = pd.Series(False, index=merged.index)
                if 'order_flow_score' in merged.columns:
                    has_flow = has_flow | merged['order_flow_score'].ge(0.60)
                if 'inst_foreign_sector_score' in merged.columns:
                    has_flow = has_flow | merged['inst_foreign_sector_score'].ge(0.60)
                if 'darkpool_score' in merged.columns:
                    has_flow = has_flow | merged['darkpool_score'].ge(0.60)

                # Triple Confluence (All 3 pillars confirmed) -> 5.0% super-linear alpha boost
                triple_confluence_mask = (has_val & has_mom & has_flow)
                if triple_confluence_mask.any():
                    blended_score.loc[triple_confluence_mask] = (blended_score.loc[triple_confluence_mask] * 1.050).clip(0.0, 1.0)
                    logger.info(f"[TRIPLE CONFLUENCE] Applied 1.050x boost to {triple_confluence_mask.sum()} high-conviction symbols.")

                # Dual Confluence (2 pillars confirmed, not triple) -> 2.5% synergy boost
                dual_confluence_mask = ((has_mom & has_flow) | (has_val & has_mom) | (has_val & has_flow)) & ~triple_confluence_mask
                if dual_confluence_mask.any():
                    blended_score.loc[dual_confluence_mask] = (blended_score.loc[dual_confluence_mask] * 1.025).clip(0.0, 1.0)

                # Phase 2-C: Fundamental Distress Gatekeeper vs High-Quality Compounder Dual Gate
                if 'operating_margin' in merged.columns or 'roe' in merged.columns:
                    distress_cond = pd.Series(False, index=merged.index)
                    if 'operating_margin' in merged.columns:
                        distress_cond = distress_cond | (merged['operating_margin'] < -0.10)
                    if 'roe' in merged.columns:
                        distress_cond = distress_cond | (merged['roe'] < -0.10)

                    # Exempt tactical turnaround / deep value / squeeze catalysts from distress penalty
                    tactical_exempt = pd.Series(False, index=merged.index)
                    if 'short_squeeze_score' in merged.columns:
                        tactical_exempt = tactical_exempt | (merged['short_squeeze_score'] >= 0.65)
                    if 'valueup_catalyst_score' in merged.columns:
                        tactical_exempt = tactical_exempt | (merged['valueup_catalyst_score'] >= 0.65)
                    if 'reversal_score' in merged.columns:
                        tactical_exempt = tactical_exempt | (merged['reversal_score'] >= 0.65)

                    distress_to_penalize = distress_cond & (~tactical_exempt)
                    if distress_to_penalize.any():
                        blended_score.loc[distress_to_penalize] = (blended_score.loc[distress_to_penalize] * 0.70).clip(0.0, 1.0)
                        logger.info(f"[DISTRESS GATEKEEPER] Applied 0.70x penalty to {distress_to_penalize.sum()} loss-making non-tactical symbols.")

                    # High-Quality Compounder Bonus (Profitable compounding champions)
                    quality_cond = pd.Series(False, index=merged.index)
                    if 'operating_margin' in merged.columns and 'roe' in merged.columns:
                        quality_cond = (merged['operating_margin'] >= 0.15) & (merged['roe'] >= 0.15) & ~distress_cond
                    elif 'operating_margin' in merged.columns:
                        quality_cond = (merged['operating_margin'] >= 0.18) & ~distress_cond
                    elif 'roe' in merged.columns:
                        quality_cond = (merged['roe'] >= 0.18) & ~distress_cond

                    if quality_cond.any():
                        blended_score.loc[quality_cond] = (blended_score.loc[quality_cond] * 1.035).clip(0.0, 1.0)
                        logger.info(f"[QUALITY COMPOUNDER] Applied 1.035x quality bonus to {quality_cond.sum()} high-ROIC firms.")
            except Exception as _be:
                logger.debug(f"Convex multi-signal synergy boost bypassed: {_be}")

        merged['ensemble_score'] = blended_score

        # Fix Task 2: Preserve raw un-mutated strategy scores with actual NaNs for StrategyCoverageAnalyzer
        self.raw_scores = merged.copy()
        if not hasattr(merged, 'attrs'):
            merged.attrs = {}
        merged.attrs['raw_scores'] = self.raw_scores

        # Fill raw NaNs with 0.0 for report formatting after ensemble score calculation
        fill_cols = list(set(['reg_pred', 'll_raw'] + [sc for _, sc in strategy_cols]))
        for col in fill_cols:
            if col in merged.columns:
                merged[col] = merged[col].fillna(0.0)
            else:
                merged[col] = 0.0

        # Scale Ensemble Score to Calibrated Realistic Expected Return Proxy (%) [e.g. 0% ~ 50% max]
        # Horizon-Adaptive Time Scaling: sqrt(h / 20)
        try:
            h_int = int(str(target_horizon).replace('d', '')) if str(target_horizon).replace('d', '').isdigit() else 20
        except Exception:
            h_int = 20
        horizon_scale = float(np.clip(np.sqrt(max(1, h_int) / 20.0), 0.25, 3.0))

        # Regime-dynamic elasticity multiplier (BULL = 1.15, BEAR = 0.85, SIDEWAYS = 1.0)
        regime_str = str(regime).upper()
        if 'BULL' in regime_str or str(regime) == '2':
            regime_elasticity = 1.15
        elif 'BEAR' in regime_str or str(regime) == '0':
            regime_elasticity = 0.85
        else:
            regime_elasticity = 1.0

        raw_exp_ret = merged['ensemble_score'] * float(self._return_multiplier) * horizon_scale * regime_elasticity

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

        # Vectorized Microstructure Friction Model
        mkt_col = merged['market'].fillna('').astype(str).str.upper() if 'market' in merged.columns else pd.Series('', index=merged.index)
        sym_col = merged['symbol'].astype(str)
        is_us_stock = mkt_col.isin(['SP500', 'NASDAQ', 'RUSSELL2000']) | (sym_col.str.isalpha() & (sym_col.str.len() <= 5))

        vol_data = merged['volatility_20d'] if 'volatility_20d' in merged.columns else pd.Series(np.nan, index=merged.index)
        default_vols = np.where(is_us_stock, default_volatility_sp500, default_volatility_krx)
        vols = vol_data.fillna(pd.Series(default_vols, index=merged.index)).astype(float).values
        vols = np.where(vols <= 0, default_vols, vols)

        vol_col = merged['volume'].fillna(0.0).astype(float).values if 'volume' in merged.columns else np.zeros(len(merged))
        close_col = merged['close'].fillna(0.0).astype(float).values if 'close' in merged.columns else np.zeros(len(merged))
        turnover = vol_col * close_col

        stt_tax = np.full(len(merged), 0.0015)
        brokerage_fee = np.full(len(merged), 0.0003)
        base_spread = np.full(len(merged), base_spread_kospi)
        spread_min = np.full(len(merged), 0.0002)
        spread_max = np.full(len(merged), 0.0150)
        q_order = np.full(len(merged), order_size_krx)
        adv_ref = np.full(len(merged), 1_000_000_000.0)
        impact_coeff = np.full(len(merged), impact_coeff_krx)

        m_nasdaq = (mkt_col == 'NASDAQ')
        stt_tax[m_nasdaq] = 0.00003
        brokerage_fee[m_nasdaq] = 0.00005
        base_spread[m_nasdaq] = base_spread_nasdaq
        spread_min[m_nasdaq] = 0.0001
        spread_max[m_nasdaq] = 0.0080
        q_order[m_nasdaq] = order_size_sp500
        adv_ref[m_nasdaq] = 1_000_000.0
        impact_coeff[m_nasdaq] = impact_coeff_sp500

        m_russell = (mkt_col == 'RUSSELL2000')
        stt_tax[m_russell] = 0.00003
        brokerage_fee[m_russell] = 0.00005
        base_spread[m_russell] = base_spread_russell2000
        spread_min[m_russell] = 0.0002
        spread_max[m_russell] = 0.0150
        q_order[m_russell] = order_size_sp500
        adv_ref[m_russell] = 500_000.0
        impact_coeff[m_russell] = impact_coeff_sp500

        m_kosdaq = (mkt_col == 'KOSDAQ') | sym_col.str.endswith('.KQ')
        stt_tax[m_kosdaq] = 0.0018
        brokerage_fee[m_kosdaq] = 0.0003
        base_spread[m_kosdaq] = base_spread_kosdaq
        spread_min[m_kosdaq] = 0.0003
        spread_max[m_kosdaq] = 0.0250
        q_order[m_kosdaq] = order_size_krx
        adv_ref[m_kosdaq] = 1_000_000_000.0
        impact_coeff[m_kosdaq] = impact_coeff_krx

        m_kospi = ((mkt_col == 'KOSPI') | sym_col.str.endswith('.KS') | (sym_col.str.isdigit() & (sym_col.str.len() == 6))) & ~m_kosdaq
        stt_tax[m_kospi] = 0.0015
        brokerage_fee[m_kospi] = 0.0003
        base_spread[m_kospi] = base_spread_kospi
        spread_min[m_kospi] = 0.0002
        spread_max[m_kospi] = 0.0150
        q_order[m_kospi] = order_size_krx
        adv_ref[m_kospi] = 1_000_000_000.0
        impact_coeff[m_kospi] = impact_coeff_krx

        m_other_us = is_us_stock & ~m_nasdaq & ~m_russell & ~m_kosdaq & ~m_kospi
        stt_tax[m_other_us] = 0.00003
        brokerage_fee[m_other_us] = 0.00005
        base_spread[m_other_us] = base_spread_sp500
        spread_min[m_other_us] = 0.0001
        spread_max[m_other_us] = 0.0050
        q_order[m_other_us] = order_size_sp500
        adv_ref[m_other_us] = 1_000_000.0
        impact_coeff[m_other_us] = impact_coeff_sp500

        min_adv = np.where(is_us_stock, 10_000.0, 10_000_000.0)
        adv = np.where(turnover > 0, np.maximum(turnover, min_adv), adv_ref)

        adv_ratio = adv_ref / adv
        vol_ratio = vols / 0.020
        dynamic_spread = base_spread * (adv_ratio ** 0.25) * (vol_ratio ** 0.50)
        clamped_spread = np.clip(dynamic_spread, spread_min, spread_max)

        participation_ratio = q_order / adv
        impact_alpha = getattr(self, 'realized_market_impact_alpha', 0.50)
        impact_one_way = impact_coeff * vols * (participation_ratio ** impact_alpha)

        ov_mask = participation_ratio > 0.10
        impact_one_way[ov_mask] += 0.50 * (participation_ratio[ov_mask] - 0.10)

        raw_total_cost = stt_tax + brokerage_fee + (1.0 * clamped_spread) + (2.0 * impact_one_way)
        cost_scaling = getattr(self, 'cost_scaling_factor', 1.0)
        max_cost_cap = np.where(ov_mask, 0.20, 0.05)
        cost_series = np.minimum(raw_total_cost * cost_scaling, max_cost_cap)
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
                min_krx_turnover = getattr(self.config, 'min_daily_volume_krx', 500_000_000.0) if self.config else 500_000_000.0
                min_us_turnover = getattr(self.config, 'min_daily_volume_sp500', 1_000_000.0) if self.config else 1_000_000.0
                if vol <= 0:
                    return True
                if mkt in ['KOSPI', 'KOSDAQ'] and turnover > 0 and turnover < min_krx_turnover:
                    return True
                if mkt in ['SP500', 'NASDAQ', 'RUSSELL2000'] and turnover > 0 and turnover < min_us_turnover:
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
                    # Fallback construct return series scaled by expected return with uncorrelated noise
                    ret_series = top_candidates.set_index('symbol')['ensemble_expected_return'] / 100.0
                    ret_dict = {}
                    for sym in top_syms:
                        sym_seed = int(abs(hash(str(sym)))) % (2**31)
                        sym_rng = np.random.RandomState(sym_seed)
                        base_noise = sym_rng.normal(0.0, 0.02, 30)
                        ret_dict[sym] = float(ret_series.get(sym, 0.0)) + base_noise
                    returns_matrix_df = pd.DataFrame(ret_dict)

                expected_ret_series = top_candidates.set_index('symbol')['ensemble_expected_return']
                raw_weights = optimizer.optimize_return_tilted_risk_parity(
                    returns_matrix_df,
                    expected_returns=expected_ret_series,
                    tilt_exponent=1.0,
                    max_weight=0.20
                )
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

