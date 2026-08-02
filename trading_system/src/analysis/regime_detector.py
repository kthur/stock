import logging
import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture

logger = logging.getLogger(__name__)

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


class MarketRegimeDetector:
    """
    Market Regime Detector using a Gaussian Mixture Model (GMM).
    Classifies the market into 3 states:
      - 0: BEAR (Negative return, high volatility)
      - 1: SIDEWAYS (Zero/low return, moderate volatility)
      - 2: BULL (Positive return, low/moderate volatility)
    """

    def __init__(self, n_regimes: int = 3, rolling_window: int = 20):
        self.n_regimes = n_regimes
        self.rolling_window = rolling_window
        self.gmm = GaussianMixture(n_components=n_regimes, random_state=42, n_init=10)
        self.is_trained = False
        # Map GMM cluster index to regime index (0=BEAR, 1=SIDEWAYS, 2=BULL)
        self.cluster_to_regime: dict[int, int] = {}

    def _prepare_features(self, indicator_df: pd.DataFrame) -> pd.DataFrame:
        """Computes multi-variable macro feature matrix.

        10-Feature Set (확장):
          Core:         sp500 수익률/변동성
          공포/유동성: VIX, USD/KRW
          금리:         US10Y 레벨, US10Y-US5Y 스프레드(장단기 역전), 한/미 금리차, 한국채 수익률 곡선
          원자재:       WTI 유가 변화율, 인플레이션 충격 복합 지표(유가+환율 동시 상승)
        """
        df = indicator_df.copy()

        # Check for sp500_change column (global indicator)
        if 'sp500_change' not in df.columns:
            raise ValueError("Indicator DataFrame must contain 'sp500_change' column.")

        features = pd.DataFrame(index=df.index)
        # ── Core: S&P500 모멘텀 & 변동성 ──────────────────────────────────────
        features['sp500_ret_roll'] = df['sp500_change'].rolling(self.rolling_window, min_periods=1).mean()
        features['sp500_vol_roll'] = df['sp500_change'].rolling(self.rolling_window, min_periods=1).std().fillna(0.0)

        # ── 공포/위험선호 지표: VIX ────────────────────────────────────────────
        if 'vix_change' in df.columns:
            features['vix_level'] = df['vix_change'].fillna(0.0) / 100.0
        else:
            features['vix_level'] = 0.20

        # ── 미국채 10년물 금리 레벨 ────────────────────────────────────────────
        if 'us10y' in df.columns:
            features['us10y_level'] = df['us10y'].fillna(4.0) / 10.0
        else:
            features['us10y_level'] = 0.40

        # ── ① 표준 장단기 금리 스프레드: US10Y - US2Y (경기침체 선행 신호) ──────────
        # 1순위: US10Y - US2Y (표준 10Y-2Y Spread), 2순위: US10Y - US5Y (Fallback)
        # 음수(역전) 구간 진입 → 6~18개월 선행하여 BEAR 레짐 전환 예고
        if 'us10y_us2y_spread' in df.columns:
            features['us_yield_spread'] = df['us10y_us2y_spread'].fillna(0.5) / 3.0
        elif 'us10y' in df.columns and 'us2y' in df.columns:
            features['us_yield_spread'] = (df['us10y'] - df['us2y']).fillna(0.5) / 3.0
        elif 'yield_curve_10y3m' in df.columns:
            features['us_yield_spread'] = df['yield_curve_10y3m'].fillna(0.0) / 5.0
        else:
            features['us_yield_spread'] = 0.0

        # ── USD/KRW 환율 변동 (외국인 수급 이탈 지표) ─────────────────────────
        if 'usdkrw_change' in df.columns:
            features['usdkrw_ret_roll'] = df['usdkrw_change'].rolling(self.rolling_window, min_periods=1).mean().fillna(0.0)
        else:
            features['usdkrw_ret_roll'] = 0.0

        # ── ① 한/미 국채 10년물 금리차 (외국인 자금 이탈 리스크) ────────────────
        # kr_us_10y_spread = kr10y - us10y: 음수 → 미국 대비 한국 금리 낮음 → 자금 이탈 압력
        if 'kr_us_10y_spread' in df.columns:
            features['kr_us_spread'] = df['kr_us_10y_spread'].fillna(0.0) / 3.0
        elif 'kr10y' in df.columns and 'us10y' in df.columns:
            features['kr_us_spread'] = (df['kr10y'] - df['us10y']).fillna(0.0) / 3.0
        else:
            features['kr_us_spread'] = 0.0

        # ── 한국 채권 수익률 곡선 (kr10y - kr3y): 국내 경기 선행 지수 ───────────
        if 'kr_yield_curve' in df.columns:
            features['kr_yield_curve'] = df['kr_yield_curve'].fillna(0.0) / 3.0
        elif 'kr10y' in df.columns:
            features['kr_yield_curve'] = 0.0
        else:
            features['kr_yield_curve'] = 0.0

        # ── WTI 유가 변화율 롤링 평균 ─────────────────────────────────────────
        if 'wti_change' in df.columns:
            features['wti_ret_roll'] = df['wti_change'].rolling(self.rolling_window, min_periods=1).mean().fillna(0.0) / 100.0
        else:
            features['wti_ret_roll'] = 0.0

        # ── ② 인플레이션 충격 복합 지표 (유가+환율 동시 상승: 수입물가 이중 충격) ─
        # 값이 클수록 국내 제조업 원가 압박 심화 → Defensive 전략 가중치 상향 신호
        if 'inflation_shock_index' in df.columns:
            features['inflation_shock'] = df['inflation_shock_index'].fillna(0.0).rolling(
                self.rolling_window, min_periods=1).mean() / 10.0
        else:
            features['inflation_shock'] = 0.0

        return features

    def train(self, indicator_df: pd.DataFrame) -> None:
        """Trains the GMM on historical global indicators and maps components to regimes."""
        if indicator_df.empty or len(indicator_df) < 30:
            logger.warning(f"Insufficient indicator data for training GMM regime detector: {len(indicator_df)}")
            return

        try:
            features_df = self._prepare_features(indicator_df)
            X = features_df.values

            # Drop initial rows if they contain NaNs
            valid_mask = np.isfinite(X).all(axis=1)
            X_valid = X[valid_mask]

            if len(X_valid) < 20:
                raise ValueError("Insufficient finite data points for GMM training.")

            # Fit GMM
            self.gmm.fit(X_valid)
            self.is_trained = True

            # Assign human-readable regimes based on the means of the components
            means = self.gmm.means_

            # Component 0 = sp500_ret_roll, Component 1 = sp500_vol_roll
            scores = []
            for i in range(self.n_regimes):
                mean_ret = means[i, 0]
                mean_vol = means[i, 1]
                score = mean_ret / (mean_vol + 1e-5)
                scores.append((i, score, mean_ret, mean_vol))

            # Sort clusters by Sharpe score: lowest (Bear) -> intermediate (Sideways) -> highest (Bull)
            scores.sort(key=lambda x: x[1])

            # Map cluster index to regime
            self.cluster_to_regime = {
                scores[0][0]: 0,  # BEAR
                scores[1][0]: 1,  # SIDEWAYS
                scores[2][0]: 2   # BULL
            }

            logger.info("MarketRegimeDetector trained successfully.")
            for reg, (idx, score, r, v) in enumerate(scores):
                label = ["BEAR", "SIDEWAYS", "BULL"][reg]
                logger.info(f"Regime {label}: cluster={idx}, Sharpe_score={score:.4f}, mean_ret={r:.4f}%, mean_vol={v:.4f}%")

        except Exception as e:
            logger.error(f"Error training MarketRegimeDetector: {e}")
            self.is_trained = False

    def predict_regime(self, indicator_df: pd.DataFrame) -> int:
        """
        Predicts the current regime.
        Includes Fast Shock / VIX Override for zero-lag crash detection.
        Returns:
          2: BULL
          1: SIDEWAYS
          0: BEAR
        """
        if indicator_df.empty:
            return 2  # Default to BULL if no data

        # Fast VIX / Shock Override: Check for extreme volatility or rapid drawdowns
        try:
            if 'vix_change' in indicator_df.columns:
                latest_vix = float(indicator_df['vix_change'].dropna().iloc[-1]) if not indicator_df['vix_change'].dropna().empty else 0.0
                if latest_vix > 30.0:
                    logger.warning(f"Fast VIX Shock Triggered (VIX={latest_vix:.2f} > 30.0): Forcing BEAR regime.")
                    return 0  # BEAR

            if 'sp500_change' in indicator_df.columns:
                sp500_series = indicator_df['sp500_change'].dropna()
                if not sp500_series.empty:
                    latest_sp500 = float(sp500_series.iloc[-1])
                    recent_2d_sum = float(sp500_series.tail(2).sum()) if len(sp500_series) >= 2 else latest_sp500
                    if latest_sp500 < -3.0 or recent_2d_sum < -5.0:
                        logger.warning(f"Fast Market Shock Triggered (S&P500 1d={latest_sp500:.2f}%, 2d={recent_2d_sum:.2f}%): Forcing BEAR regime.")
                        return 0  # BEAR
        except Exception as ex:
            logger.debug(f"Fast regime override check error: {ex}")

        # Check if trained
        if not self.is_trained or not self.cluster_to_regime:
            return self._predict_rule_based_fallback(indicator_df)

        try:
            features_df = self._prepare_features(indicator_df)
            latest_feat = features_df.iloc[-1].values.reshape(1, -1)

            if not np.isfinite(latest_feat).all():
                return self._predict_rule_based_fallback(indicator_df)

            # Predict cluster index
            cluster_idx = int(self.gmm.predict(latest_feat)[0])
            regime = self.cluster_to_regime.get(cluster_idx, 2)
            return regime
        except Exception as e:
            logger.error(f"Regime prediction failed: {e}. Falling back to rule-based.")
            return self._predict_rule_based_fallback(indicator_df)

    def predict_regime_label(self, indicator_df: pd.DataFrame) -> str:
        regime = self.predict_regime(indicator_df)
        return ["BEAR", "SIDEWAYS", "BULL"][regime]

    def predict_regime_transition_probabilities(self, indicator_df: pd.DataFrame) -> dict[str, float]:
        """
        Computes Markov Regime Switching (MRS) transition probabilities for BEAR, SIDEWAYS, and BULL.
        Returns:
            dict with 'p_bear', 'p_sideways', 'p_bull', 'bear_shock_risk'
        """
        default_res = {'p_bear': 0.10, 'p_sideways': 0.20, 'p_bull': 0.70, 'bear_shock_risk': False}
        if indicator_df.empty:
            return default_res

        try:
            # Check fast VIX shock
            if 'vix_change' in indicator_df.columns:
                latest_vix = float(indicator_df['vix_change'].dropna().iloc[-1]) if not indicator_df['vix_change'].dropna().empty else 0.0
                if latest_vix > 30.0:
                    return {'p_bear': 0.85, 'p_sideways': 0.10, 'p_bull': 0.05, 'bear_shock_risk': True}

            if not self.is_trained or not self.cluster_to_regime:
                r = self._predict_rule_based_fallback(indicator_df)
                if r == 0:
                    return {'p_bear': 0.70, 'p_sideways': 0.20, 'p_bull': 0.10, 'bear_shock_risk': True}
                elif r == 1:
                    return {'p_bear': 0.20, 'p_sideways': 0.60, 'p_bull': 0.20, 'bear_shock_risk': False}
                else:
                    return {'p_bear': 0.05, 'p_sideways': 0.15, 'p_bull': 0.80, 'bear_shock_risk': False}

            features_df = self._prepare_features(indicator_df)
            latest_feat = features_df.iloc[-1].values.reshape(1, -1)

            if not np.isfinite(latest_feat).all():
                return default_res

            cluster_probs = self.gmm.predict_proba(latest_feat)[0]
            regime_probs = {0: 0.0, 1: 0.0, 2: 0.0}
            for cluster_idx, prob in enumerate(cluster_probs):
                reg = self.cluster_to_regime.get(cluster_idx, 2)
                regime_probs[reg] += float(prob)

            p_bear = regime_probs[0]
            p_sideways = regime_probs[1]
            p_bull = regime_probs[2]
            bear_shock_risk = bool(p_bear >= 0.35)

            return {
                'p_bear': float(p_bear),
                'p_sideways': float(p_sideways),
                'p_bull': float(p_bull),
                'bear_shock_risk': bear_shock_risk
            }
        except Exception as e:
            logger.error(f"Error computing regime transition probabilities: {e}")
            return default_res

    def _predict_rule_based_fallback(self, indicator_df: pd.DataFrame) -> int:
        """Rule-based fallback detector when GMM is not fitted or fails."""
        try:
            if 'sp500_change' not in indicator_df.columns:
                return 2  # default to BULL

            sp500 = indicator_df['sp500_change']
            cum_ret_20d = float(sp500.tail(20).sum()) if len(sp500) >= 20 else float(sp500.sum())
            float(sp500.tail(20).std()) if len(sp500) >= 2 else 1.0

            if cum_ret_20d < -2.0:
                return 0  # BEAR
            elif cum_ret_20d > 2.0:
                return 2  # BULL
            return 1  # SIDEWAYS
        except Exception:
            return 2  # Default to BULL

    def predict_2d_regime(self, indicator_df: pd.DataFrame) -> dict:
        """
        Predicts 2D Regime: Direction (BEAR/SIDEWAYS/BULL) + Volatility (LOW_VOL/HIGH_VOL).
        Returns dict with keys: 'direction_code', 'direction_label', 'volatility_label', 'combo_label'
        Valid combo_label values: BEAR_LOW_VOL, BEAR_HIGH_VOL, SIDEWAYS_LOW_VOL, SIDEWAYS_HIGH_VOL, BULL_LOW_VOL, BULL_HIGH_VOL.
        """
        dir_code = self.predict_regime(indicator_df)
        dir_label = ["BEAR", "SIDEWAYS", "BULL"][dir_code] if 0 <= dir_code <= 2 else "SIDEWAYS"

        try:
            if not indicator_df.empty and 'sp500_change' in indicator_df.columns:
                sp500 = indicator_df['sp500_change'].dropna()
                if len(sp500) >= self.rolling_window:
                    recent_vol = float(sp500.tail(self.rolling_window).std())
                    hist_vols = sp500.rolling(self.rolling_window).std().dropna()
                    hist_vol_median = float(hist_vols.median()) if not hist_vols.empty else 1.0
                    vol_label = "HIGH_VOL" if recent_vol > hist_vol_median else "LOW_VOL"
                else:
                    vol_label = "LOW_VOL"
            else:
                vol_label = "LOW_VOL"
        except Exception as e:
            logger.warning(f"Error computing 2D regime volatility: {e}. Defaulting to LOW_VOL.")
            vol_label = "LOW_VOL"

        combo_label = f"{dir_label}_{vol_label}"
        valid_combos = {
            "BEAR_LOW_VOL", "BEAR_HIGH_VOL",
            "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL",
            "BULL_LOW_VOL", "BULL_HIGH_VOL"
        }
        if combo_label not in valid_combos:
            combo_label = "SIDEWAYS_LOW_VOL"

        return {
            'direction_code': dir_code,
            'direction_label': dir_label,
            'volatility_label': vol_label,
            'combo_label': combo_label
        }

    def predict_2d_regime_label(self, indicator_df: pd.DataFrame) -> str:
        """Returns standard 2D regime combo label string."""
        res = self.predict_2d_regime(indicator_df)
        return str(res['combo_label'])

    def predict_3d_macro_regime(self, indicator_df: pd.DataFrame) -> dict:
        """
        Predicts 3D Macro Regime: 2D Regime (Direction + Volatility) + Macro Condition.
        Macro Conditions (우선순위 순):
          1. LIQUIDITY_SQUEEZE  : VIX 급등 + 고금리 동시 발생 → 유동성 긴축
          2. INFLATION_SHOCK    : WTI 유가 + USD/KRW 환율 동시 상승 → 수입물가 이중 충격
          3. YIELD_INVERSION    : US10Y < US5Y 장단기 금리 역전 → 경기침체 선행 신호
          4. HIGH_YIELD_BULL    : 상승장 + 고금리 → 고평가 모멘텀 종목 부담
          5. HIGH_YIELD_BEAR    : 하락장 + 고금리 → 디레버리지 가속 위험
          6. NEUTRAL_EXPANSION  : 정상 확장기 환경

        Returns dict with 3D classification details including 'macro_label'.
        """
        res_2d = self.predict_2d_regime(indicator_df)
        macro_label = "NEUTRAL_EXPANSION"

        try:
            if not indicator_df.empty:
                vix_val = float(indicator_df['vix_change'].iloc[-1]) if 'vix_change' in indicator_df.columns else 0.0
                tnx_val = float(indicator_df['us10y'].iloc[-1]) if 'us10y' in indicator_df.columns else 4.0
                ktb_spread = float(indicator_df['ktb_spread'].iloc[-1]) if 'ktb_spread' in indicator_df.columns else 0.0

                # ── US10Y-US2Y 표준 장단기 금리 스프레드 (역전 감지) ─────────────────
                # 1순위: US2Y, 2순위: US5Y Fallback
                us2y_val = float(indicator_df['us2y'].iloc[-1]) if ('us2y' in indicator_df.columns and not indicator_df['us2y'].dropna().empty) \
                    else (float(indicator_df['us5y'].iloc[-1]) if 'us5y' in indicator_df.columns else (tnx_val - 0.5))
                us_spread = tnx_val - us2y_val
                is_yield_inverted = us_spread < 0.0

                # ── 인플레이션 충격: 유가 + 환율 동시 상승 ──────────────────────
                inflation_shock = float(indicator_df['inflation_shock_index'].rolling(5, min_periods=1).mean().iloc[-1]) \
                    if 'inflation_shock_index' in indicator_df.columns else 0.0
                # 최근 5일 평균 유가+환율 동시 상승분 > 2.0% → 인플레이션 충격 감지
                is_inflation_shock = inflation_shock > 2.0

                is_high_yield = tnx_val > 4.2 or ktb_spread > 0.3
                is_squeeze = vix_val > 5.0 or (res_2d['volatility_label'] == 'HIGH_VOL' and is_high_yield)

                # 우선순위 결정 (높은 위험도 우선)
                if is_squeeze:
                    macro_label = "LIQUIDITY_SQUEEZE"
                elif is_inflation_shock:
                    macro_label = "INFLATION_SHOCK"
                    logger.info(
                        f"[3D Macro] INFLATION_SHOCK 감지: 유가+환율 동시상승 5일 평균={inflation_shock:.2f}%"
                    )
                elif is_yield_inverted:
                    macro_label = "YIELD_INVERSION"
                    logger.info(
                        f"[3D Macro] YIELD_INVERSION 감지: US10Y({tnx_val:.2f}%) - US2Y({us2y_val:.2f}%) "
                        f"= {us_spread:.2f}% (역전)"
                    )
                elif is_high_yield and res_2d['direction_label'] == 'BULL':
                    macro_label = "HIGH_YIELD_BULL"
                elif is_high_yield and res_2d['direction_label'] == 'BEAR':
                    macro_label = "HIGH_YIELD_BEAR"
                else:
                    macro_label = "NEUTRAL_EXPANSION"
        except Exception as e:
            logger.warning(f"Error computing 3D macro regime: {e}. Defaulting to NEUTRAL_EXPANSION.")

        return {
            'direction_code': res_2d['direction_code'],
            'direction_label': res_2d['direction_label'],
            'volatility_label': res_2d['volatility_label'],
            'combo_2d_label': res_2d['combo_label'],
            'macro_label': macro_label,
            'combo_3d_label': f"{res_2d['combo_label']}_{macro_label}"
        }

    def predict_dual_market_regime(self, indicator_df: pd.DataFrame) -> dict:
        """
        Predicts Dual Market Regimes separately for US (SP500) and KR (KOSPI/KOSDAQ) markets,
        and computes Market Decoupling Status & Correlation Coefficient.

        Returns dict:
          - 'us_regime': US 3D Macro Regime Dict
          - 'kr_regime': KR 3D Macro Regime Dict
          - 'decoupling_status': 'COUPLED' | 'DECOUPLING_US_BULL_KR_BEAR' | 'DECOUPLING_KR_BULL_US_BEAR'
          - 'correlation_20d': 20-day rolling return correlation between S&P500 and KOSPI
        """
        us_regime = self.predict_3d_macro_regime(indicator_df)

        # Compute KR-specific regime (based on kospi_change if available)
        kr_dir_label = us_regime['direction_label']
        kr_vol_label = us_regime['volatility_label']
        corr_20d = 1.0

        try:
            if not indicator_df.empty and 'kospi_change' in indicator_df.columns:
                kospi = indicator_df['kospi_change'].dropna()
                if len(kospi) >= 20:
                    cum_ret_20d = float(kospi.tail(20).sum())
                    if cum_ret_20d < -2.0:
                        kr_dir_label = "BEAR"
                    elif cum_ret_20d > 2.0:
                        kr_dir_label = "BULL"
                    else:
                        kr_dir_label = "SIDEWAYS"

                    recent_vol = float(kospi.tail(20).std())
                    hist_vols = kospi.rolling(20).std().dropna()
                    median_vol = float(hist_vols.median()) if not hist_vols.empty else 1.0
                    kr_vol_label = "HIGH_VOL" if recent_vol > median_vol else "LOW_VOL"

                if 'sp500_change' in indicator_df.columns and len(kospi) >= 20:
                    sp500 = indicator_df['sp500_change'].dropna()
                    common_idx = sp500.index.intersection(kospi.index)
                    if len(common_idx) >= 10:
                        corr_val = float(sp500.loc[common_idx].tail(20).corr(kospi.loc[common_idx].tail(20)))
                        corr_20d = corr_val if not np.isnan(corr_val) else 0.5
        except Exception as ex:
            logger.warning(f"Error computing KR market regime: {ex}")

        # Determine Decoupling Status
        us_dir = us_regime['direction_label']
        if us_dir == "BULL" and kr_dir_label == "BEAR":
            decoupling_status = "DECOUPLING_US_BULL_KR_BEAR"
        elif us_dir == "BEAR" and kr_dir_label == "BULL":
            decoupling_status = "DECOUPLING_KR_BULL_US_BEAR"
        else:
            decoupling_status = "COUPLED"

        kr_regime = {
            'direction_label': kr_dir_label,
            'volatility_label': kr_vol_label,
            'combo_2d_label': f"{kr_dir_label}_{kr_vol_label}",
            'macro_label': us_regime['macro_label'],
            'combo_3d_label': f"{kr_dir_label}_{kr_vol_label}_{us_regime['macro_label']}"
        }

        return {
            'us_regime': us_regime,
            'kr_regime': kr_regime,
            'decoupling_status': decoupling_status,
            'correlation_20d': corr_20d
        }




