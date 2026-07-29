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
    # Dynamic Weight Configuration per 1D Market Regime (14 Strategies)
    REGIME_WEIGHTS = {
        0: {  # BEAR (Defensive)
            'regression': 0.20,
            'surge': 0.03,
            'lead_lag': 0.03,
            'vcp_rule': 0.03,
            'vcp_ml': 0.03,
            'lstm': 0.04,
            'stat_arb': 0.12,
            'sector_rotation': 0.07,
            'rim_valuation': 0.15,
            'event_driven': 0.05,
            'mq_factor': 0.10,
            'iv_skew': 0.05,
            'order_flow': 0.04,
            'short_term_reversal': 0.06
        },
        1: {  # SIDEWAYS (Rotation)
            'regression': 0.10,
            'surge': 0.04,
            'lead_lag': 0.06,
            'vcp_rule': 0.04,
            'vcp_ml': 0.07,
            'lstm': 0.10,
            'stat_arb': 0.12,
            'sector_rotation': 0.08,
            'rim_valuation': 0.10,
            'event_driven': 0.07,
            'mq_factor': 0.08,
            'iv_skew': 0.04,
            'order_flow': 0.05,
            'short_term_reversal': 0.05
        },
        2: {  # BULL (Aggressive)
            'regression': 0.05,
            'surge': 0.15,
            'lead_lag': 0.04,
            'vcp_rule': 0.04,
            'vcp_ml': 0.12,
            'lstm': 0.10,
            'stat_arb': 0.04,
            'sector_rotation': 0.10,
            'rim_valuation': 0.06,
            'event_driven': 0.10,
            'mq_factor': 0.10,
            'iv_skew': 0.03,
            'order_flow': 0.05,
            'short_term_reversal': 0.02
        }
    }

    # 2D Market Regime Matrix Weights (6 Combo States across 14 Strategies)
    REGIME_2D_WEIGHTS = {
        'BEAR_LOW_VOL': {
            'regression': 0.20,
            'surge': 0.03,
            'lead_lag': 0.03,
            'vcp_rule': 0.03,
            'vcp_ml': 0.03,
            'lstm': 0.04,
            'stat_arb': 0.12,
            'sector_rotation': 0.07,
            'rim_valuation': 0.15,
            'event_driven': 0.05,
            'mq_factor': 0.10,
            'iv_skew': 0.05,
            'order_flow': 0.04,
            'short_term_reversal': 0.06
        },
        'BEAR_HIGH_VOL': {
            'regression': 0.22,
            'surge': 0.00,
            'lead_lag': 0.03,
            'vcp_rule': 0.03,
            'vcp_ml': 0.03,
            'lstm': 0.04,
            'stat_arb': 0.15,
            'sector_rotation': 0.04,
            'rim_valuation': 0.15,
            'event_driven': 0.05,
            'mq_factor': 0.10,
            'iv_skew': 0.05,
            'order_flow': 0.04,
            'short_term_reversal': 0.07
        },
        'SIDEWAYS_LOW_VOL': {
            'regression': 0.10,
            'surge': 0.04,
            'lead_lag': 0.06,
            'vcp_rule': 0.04,
            'vcp_ml': 0.07,
            'lstm': 0.10,
            'stat_arb': 0.12,
            'sector_rotation': 0.08,
            'rim_valuation': 0.10,
            'event_driven': 0.07,
            'mq_factor': 0.08,
            'iv_skew': 0.04,
            'order_flow': 0.05,
            'short_term_reversal': 0.05
        },
        'SIDEWAYS_HIGH_VOL': {
            'regression': 0.10,
            'surge': 0.04,
            'lead_lag': 0.06,
            'vcp_rule': 0.04,
            'vcp_ml': 0.07,
            'lstm': 0.07,
            'stat_arb': 0.15,
            'sector_rotation': 0.08,
            'rim_valuation': 0.10,
            'event_driven': 0.07,
            'mq_factor': 0.08,
            'iv_skew': 0.04,
            'order_flow': 0.05,
            'short_term_reversal': 0.05
        },
        'BULL_LOW_VOL': {
            'regression': 0.05,
            'surge': 0.15,
            'lead_lag': 0.04,
            'vcp_rule': 0.04,
            'vcp_ml': 0.12,
            'lstm': 0.10,
            'stat_arb': 0.04,
            'sector_rotation': 0.10,
            'rim_valuation': 0.06,
            'event_driven': 0.10,
            'mq_factor': 0.10,
            'iv_skew': 0.03,
            'order_flow': 0.05,
            'short_term_reversal': 0.02
        },
        'BULL_HIGH_VOL': {
            'regression': 0.04,
            'surge': 0.17,
            'lead_lag': 0.04,
            'vcp_rule': 0.04,
            'vcp_ml': 0.12,
            'lstm': 0.10,
            'stat_arb': 0.04,
            'sector_rotation': 0.07,
            'rim_valuation': 0.06,
            'event_driven': 0.10,
            'mq_factor': 0.10,
            'iv_skew': 0.03,
            'order_flow': 0.05,
            'short_term_reversal': 0.04
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

        # Load Optuna-tuned 2D regime weights from tuned_params.json (if available)
        self._load_tuned_regime_weights()

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
    def compute_rolling_sharpe(self, strategy_returns: Dict[str, Union[List[float], pd.Series]],
                               window: int = 60,
                               risk_free_rate: float = 0.0) -> Dict[str, float]:
        """
        Computes recent rolling Sharpe ratio for each strategy.
        Sharpe_i = (mean(R_i) - r_f/252) / (std(R_i) + 1e-6) * sqrt(252)
        """
        sharpes = {}
        rf_daily = risk_free_rate / 252.0 if risk_free_rate > 0 else 0.0
        for strategy, ret_data in strategy_returns.items():
            try:
                s = pd.Series(ret_data).dropna()
                if len(s) >= 2:
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
            'order_flow': w.get('order_flow', 0.06),
            'short_term_reversal': w.get('short_term_reversal', 0.06),
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

        # Persist EMA weights to disk for continuity across runs
        try:
            from pathlib import Path
            import json
            models_dir = Path(__file__).resolve().parent.parent.parent / "models"
            models_dir.mkdir(exist_ok=True)
            with open(models_dir / "prev_weights.json", "w", encoding="utf-8") as f:
                json.dump(self._prev_weights, f, indent=2)
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
        lines.append("\n[14-Strategy Dynamic Weight Allocation]")
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

        lines.append("\n[Transaction Costs & Liquidity Filter Rationale]")
        lines.append("• Transaction Cost & Slippage Deductions Applied:")
        lines.append("  - KONEX : 0.80% fee + 0.50% slippage = 1.30% net return deduction")
        lines.append("  - KOSDAQ: 0.50% fee + 0.50% slippage = 1.00% net return deduction")
        lines.append("  - KOSPI : 0.35% fee + 0.50% slippage = 0.85% net return deduction")
        lines.append("  - SP500 : 0.10% fee + 0.50% slippage = 0.60% net return deduction")
        lines.append("• Liquidity & Safety Gate:")
        lines.append("  - Zero-weighting preferred stocks (우, B), SPACs, and illiquid symbols from Top recommendations.")

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
                                 rolling_sharpes: Optional[Dict[str, float]] = None,
                                 sentiment_blacklist: Optional[Union[List[str], Dict[str, Any]]] = None,
                                 target_horizon: int = 20,
                                 gamma: float = 1.0) -> pd.DataFrame:
        """
        Calculates 14-Strategy Dynamic Weighted Ensemble Score [0, 1] per stock.
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
            weights=weights,
            target_horizon=target_horizon,
            sentiment_blacklist=sentiment_blacklist
        )

    def combine_predictions(self,
                            reg_df: pd.DataFrame,
                            s_df: pd.DataFrame,
                            ll_df: pd.DataFrame,
                            v_rule_df: Optional[Union[pd.DataFrame, list]] = None,
                            vcp_ml_df: pd.DataFrame = None,
                            lstm_df: Optional[pd.DataFrame] = None,
                            stat_arb_df: Optional[pd.DataFrame] = None,
                            sector_df: Optional[pd.DataFrame] = None,
                            rim_df: Optional[pd.DataFrame] = None,
                            event_df: Optional[pd.DataFrame] = None,
                            mq_df: Optional[pd.DataFrame] = None,
                            iv_skew_df: Optional[pd.DataFrame] = None,
                            order_flow_df: Optional[pd.DataFrame] = None,
                            reversal_df: Optional[pd.DataFrame] = None,
                            weights: Dict[str, float] = None,
                            target_horizon: int = 20,
                            sentiment_blacklist: Optional[Union[List[str], Dict[str, Any]]] = None) -> pd.DataFrame:
        """
        Merges 14 strategy prediction DataFrames and computes weighted ensemble score.
        """
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
            reg_df_copy['reg_score'] = (reg_df_copy['reg_pred'] / 0.25).clip(0.0, 1.0)
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
            ll_df_copy['ll_score'] = (ll_df_copy['ll_raw'] / 100.0).clip(0.0, 1.0)
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

        # Combine all 14 strategy DataFrames efficiently while preserving metadata
        dfs = [reg_df_copy, s_df_copy, ll_df_copy, vr_df, v_df, l_df, sa_df, sec_df, r_val_df, ev_df, m_df, iv_df, of_df, rev_df]
        merged = pd.DataFrame(columns=['symbol'])
        for d in dfs:
            if d is not None and not d.empty:
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
        ]

        # Phase 4-A: Apply Isotonic Regression calibration if calibrators are fitted
        if self.has_calibrators():
            for strategy_name, col in strategy_cols:
                if col in merged.columns and strategy_name in self._calibrators:
                    valid_mask = merged[col].notna() & np.isfinite(merged[col])
                    if valid_mask.any():
                        merged.loc[valid_mask, col] = self.calibrate_scores(strategy_name, merged.loc[valid_mask, col].values)

        # Dynamic Weight Renormalization for missing/NaN strategy scores per symbol
        total_score_series = pd.Series(0.0, index=merged.index)
        total_weight_series = pd.Series(0.0, index=merged.index)

        for strat_name, score_col in strategy_cols:
            w = weights.get(strat_name, 0.10)
            if score_col in merged.columns:
                # Fix Task 1: Valid 0.0 scores must NOT be discarded as missing data.
                valid_mask = merged[score_col].notna() & np.isfinite(merged[score_col])
                total_score_series += merged[score_col].fillna(0.0) * w * valid_mask.astype(float)
                total_weight_series += w * valid_mask.astype(float)

        # Avoid division by zero: if no strategy scores exist, score is 0.0
        safe_weight_series = total_weight_series.replace(0.0, np.nan)
        merged['ensemble_score'] = (total_score_series / safe_weight_series).fillna(0.0).clip(0.0, 1.0)

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
            'iv_skew_score', 'order_flow_score', 'reversal_score'
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

        # Fix Task 4: Apply Market-specific Transaction Cost & Slippage Deductions consistently
        # (KONEX 0.8%, KOSDAQ 0.5%, KOSPI 0.35%, SP500 0.10% + 0.5% slippage)
        slippage = getattr(self.config, 'slippage_krx_market_order', 0.005) if self.config is not None else 0.005

        def _get_cost_pct(row_or_sym) -> float:
            if isinstance(row_or_sym, pd.Series):
                symbol = str(row_or_sym.get('symbol', ''))
                market = str(row_or_sym.get('market', '')).upper()
            else:
                symbol = str(row_or_sym)
                market = ''

            if market == 'KONEX' or symbol.endswith('.KN'):
                return 0.0080 + slippage
            elif market == 'KOSDAQ' or symbol.endswith('.KQ'):
                return 0.0050 + slippage
            elif market == 'KOSPI' or symbol.endswith('.KS') or (symbol.isdigit() and len(symbol) == 6):
                return 0.0035 + slippage
            elif market == 'SP500' or (symbol.isalpha() and len(symbol) <= 5):
                return 0.0010 + slippage
            return 0.0010 + slippage

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
            if 'volume' in row and pd.notna(row['volume']) and float(row['volume']) <= 0:
                return True
            return False

        # Apply illiquid/preferred tag (zero-weight or filter out for top recommendations)
        illiquid_mask = merged.apply(_is_illiquid_or_preferred, axis=1)
        if illiquid_mask.any():
            logger.info(f"[LIQUIDITY GATE] Flagged {illiquid_mask.sum()} preferred/SPAC/illiquid stocks.")
            # Zero-out ensemble score for preferred/SPACs so they do not populate Top 20 recommendations
            merged.loc[illiquid_mask, 'ensemble_score'] = 0.0
            merged.loc[illiquid_mask, 'ensemble_expected_return'] = 0.0

        # Sort by ensemble score descending
        merged = merged.sort_values(by='ensemble_score', ascending=False).reset_index(drop=True)
        return merged
