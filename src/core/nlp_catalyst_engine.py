"""
src/core/nlp_catalyst_engine.py — Alternative NLP Guidance Drift Acceleration Engine (Feature F682).

Phase 140 Release R140:
- FinBERT document polarity S_FinBERT in [-1.0, +1.0] and conviction (1 - P(Neutral)) in [0.0, 1.0].
- DART/SEC event conviction multipliers: Supply contract (+1.5x), Buyback/cancellation (+2.0x), Convertible bond (-1.8x).
- SEC Form 4 insider conviction weighting: C-suite (+2.0x) vs outside director (+1.0x).
- Guidance tone drift Tone_Drift and second-order tone acceleration Tone_Accel.
- Deterministic 3-Tier Causal Fallback Architecture:
    Transcripts/Filings -> Fundamental Growth Surprise -> PEAD Price-Volume Momentum
- Non-linear composite score strictly bounded within [0.05, 0.95], zero NaNs, zero synthetic rows.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from .base_strategy import BaseStrategyEngine, ScoreDataFrame, make_score_dataframe
from src.core.strategy_registry import register_strategy, StrategyMeta

logger = logging.getLogger(__name__)

# Metadata Constants
VERSION: int = 140
RELEASE: str = "R140"
FEATURE: str = "F682"

# Event Conviction Weights
EVENT_WEIGHTS: Dict[str, float] = {
    "contract": 1.50,            # 단일판매·공급계약체결 / Material supply contract
    "supply_contract": 1.50,
    "buyback": 2.00,             # 자기주식취득/소각 / Share repurchase & cancellation
    "cancellation": 2.00,
    "convertible_bond": -1.80,   # 전환사채(CB) / 신주인수권부사채(BW) 발행 (Dilution)
    "cb_issuance": -1.80,
    "capital_increase": -1.50,   # 유상증자 (Dilution)
    "insider_c_level": 2.00,     # Form 4 CEO/CFO purchase
    "insider_director": 1.00,    # Form 4 Non-executive director purchase
}


def compute_finbert_polarity(
    pos_prob: float,
    neg_prob: float,
    neu_prob: float,
) -> Tuple[float, float]:
    """
    Computes document polarity and conviction:
        S_FinBERT = P(Positive) - P(Negative) in [-1.0, +1.0]
        Conviction = 1.0 - P(Neutral) in [0.0, 1.0]
    """
    if not (np.isfinite(pos_prob) and np.isfinite(neg_prob) and np.isfinite(neu_prob)):
        return 0.0, 0.0
    tot = pos_prob + neg_prob + neu_prob
    if tot > 0:
        p_pos = pos_prob / tot
        p_neg = neg_prob / tot
        p_neu = neu_prob / tot
    else:
        p_pos, p_neg, p_neu = 0.33, 0.33, 0.34

    polarity = float(np.clip(p_pos - p_neg, -1.0, 1.0))
    conviction = float(np.clip(1.0 - p_neu, 0.0, 1.0))
    return polarity, conviction


def compute_tone_drift_and_accel(
    s_curr: float,
    s_prev: float,
    conviction: float = 1.0,
    prev_drift: Optional[float] = None,
) -> Tuple[float, float]:
    """
    Computes guidance tone drift and second-order tone acceleration:
        Tone_Drift(t) = (S_curr(t) - S_prev(t-1)) * Conviction(t)
        Tone_Accel(t) = Tone_Drift(t) - Tone_Drift(t-1)
    """
    if not np.isfinite(s_curr):
        s_curr = 0.0
    if not np.isfinite(s_prev):
        s_prev = s_curr
    if not np.isfinite(conviction):
        conviction = 1.0

    tone_drift = float((s_curr - s_prev) * conviction)
    if prev_drift is not None and np.isfinite(prev_drift):
        tone_accel = float(tone_drift - prev_drift)
    else:
        tone_accel = 0.0

    return tone_drift, tone_accel


@register_strategy(
    StrategyMeta(
        strategy_id="nlp_catalyst_v2",
        display_name="Alternative NLP Catalyst",
        score_column="nlp_catalyst_score",
        category="sentiment",
        output_file="nlp_catalyst_predictions.txt",
        default_regime_weights={
            "BULL_LOW_VOL": 0.035,
            "BULL_HIGH_VOL": 0.030,
            "SIDEWAYS_LOW_VOL": 0.030,
            "SIDEWAYS_HIGH_VOL": 0.025,
            "BEAR_LOW_VOL": 0.020,
            "BEAR_HIGH_VOL": 0.015,
            "RELIEF_RALLY": 0.035,
            "PANIC_CRISIS": 0.010,
            "BULL": 0.035,
            "SIDEWAYS": 0.030,
            "BEAR": 0.020,
        },
    )
)
class NLPCatalystEngine(BaseStrategyEngine):
    """
    Phase 140 Alternative NLP Sentiment Catalyst & Guidance Acceleration Engine (Feature F682).
    Processes guidance sentiment shifts from corporate disclosures, conference call transcripts,
    and SEC Form 4 insider filings, equipped with a 3-tier causal fallback ensuring complete zero-NaN coverage.
    """

    def __init__(
        self,
        config: Optional[Any] = None,
    ) -> None:
        super().__init__(name="NLPCatalystEngine", config=config)

    @staticmethod
    def _canon_sym(s: Any) -> str:
        s_str = str(s).strip()
        part0 = s_str.split(".")[0]
        return part0.zfill(6) if part0.isdigit() else s_str.upper()

    def _compute_pead_proxy(
        self,
        symbol: str,
        prices_dict: Dict[str, pd.DataFrame],
    ) -> float:
        """
        Layer 3 Tertiary Fallback: PEAD Price-Volume Momentum Proxy.
            Delta_PEAD = R_20d - (1/3) R_60d + 0.5 (R_5d - 0.25 R_20d)
        Multiplied by volume confirmation (V_now / V_SMA20).
        """
        df_ohlcv = self.extract_ohlcv(symbol, prices_dict, min_bars=5)
        if df_ohlcv is None or len(df_ohlcv) < 5:
            return 0.0

        try:
            close_s = pd.to_numeric(df_ohlcv["Close"], errors="coerce").dropna()
            vol_s = pd.to_numeric(df_ohlcv["Volume"], errors="coerce").fillna(0.0) if "Volume" in df_ohlcv.columns else pd.Series(dtype=float)

            if len(close_s) < 5:
                return 0.0

            c_now = float(close_s.iloc[-1])
            c_5d = float(close_s.iloc[-5]) if len(close_s) >= 5 else c_now
            c_20d = float(close_s.iloc[-20]) if len(close_s) >= 20 else c_5d
            c_60d = float(close_s.iloc[-60]) if len(close_s) >= 60 else c_20d

            r5 = (c_now / c_5d - 1.0) if c_5d > 0 else 0.0
            r20 = (c_now / c_20d - 1.0) if c_20d > 0 else 0.0
            r60 = (c_now / c_60d - 1.0) if c_60d > 0 else 0.0

            pead_core = r20 - (1.0 / 3.0) * r60 + 0.5 * (r5 - 0.25 * r20)

            if len(vol_s) >= 20:
                v_now = float(vol_s.iloc[-1])
                v_sma20 = float(vol_s.tail(20).mean())
                vol_conf = min(2.5, v_now / max(v_sma20, 1.0)) if (np.isfinite(v_now) and np.isfinite(v_sma20)) else 1.0
            else:
                vol_conf = 1.0

            return float(np.tanh(3.0 * pead_core * vol_conf))
        except Exception:
            return 0.0

    def _compute_fundamental_growth_proxy(
        self,
        fund_data: Optional[Dict[str, Any]],
    ) -> float:
        """
        Layer 2 Secondary Fallback: Operating Margin & EPS Revision Acceleration.
        """
        if not fund_data or not isinstance(fund_data, dict):
            return 0.0

        try:
            op_growth = float(fund_data.get("operating_growth", fund_data.get("op_margin_delta", 0.0)))
            eps_rev = float(fund_data.get("eps_revision", fund_data.get("earnings_surprise", 0.0)))
            rev_accel = float(fund_data.get("revenue_accel", 0.0))

            growth_sig = 0.40 * op_growth + 0.40 * eps_rev + 0.20 * rev_accel
            return float(np.tanh(2.5 * growth_sig)) if np.isfinite(growth_sig) else 0.0
        except Exception:
            return 0.0

    def calculate_scores(
        self,
        symbols: Optional[List[str]] = None,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        transcript_map: Optional[Dict[str, Dict[str, Any]]] = None,
        filing_map: Optional[Dict[str, Dict[str, Any]]] = None,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Universal calculate_scores method compatible with test suites and pipeline runners."""
        if prices_dict is None and isinstance(symbols, dict):
            prices_dict = symbols
            symbols = None
        if symbols is not None and prices_dict is not None:
            prices_dict = {s: prices_dict[s] for s in symbols if s in prices_dict}
        return self.compute_scores(
            prices_dict=prices_dict,
            fundamentals_dict=fundamentals_dict,
            transcript_map=transcript_map,
            filing_map=filing_map,
            **kwargs
        )

    def compute_scores(
        self,
        prices_dict: Any,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        transcript_map: Optional[Dict[str, Dict[str, Any]]] = None,
        filing_map: Optional[Dict[str, Dict[str, Any]]] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Computes Alternative NLP Guidance Drift Acceleration scores.
        Returns ScoreDataFrame with ['symbol', 'nlp_catalyst_score'].
        """
        prices_source = kwargs.get("df_prices", prices_dict)
        if not prices_source:
            return make_score_dataframe({}, score_column="nlp_catalyst_score")

        if isinstance(prices_source, dict):
            p_dict = prices_source
            symbols = list(p_dict.keys())
        elif isinstance(prices_source, pd.DataFrame):
            if "symbol" in prices_source.columns:
                symbols = prices_source["symbol"].dropna().astype(str).unique().tolist()
                p_dict = {s: prices_source[prices_source["symbol"] == s] for s in symbols}
            else:
                symbols = list(prices_source.columns)
                p_dict = {col: pd.DataFrame({"Close": prices_source[col]}) for col in symbols}
        else:
            return make_score_dataframe({}, score_column="nlp_catalyst_score")

        scores: Dict[str, float] = {}
        transcripts = transcript_map or kwargs.get("transcript_map") or {}
        filings = filing_map or kwargs.get("filing_map") or {}
        funds = fundamentals_dict or kwargs.get("fundamentals_dict") or {}

        for sym in symbols:
            sym_str = str(sym).strip()
            sym_c = self._canon_sym(sym_str)

            s_filing = 0.0
            tone_drift = 0.0
            tone_accel = 0.0
            has_nlp_data = False

            # 1. Filing Events (DART/SEC)
            sym_filing = filings.get(sym_str, filings.get(sym_c))
            if sym_filing and isinstance(sym_filing, dict):
                has_nlp_data = True
                event_type = str(sym_filing.get("event_type", "")).lower()
                # Default to magnitude 1.0 if polarity not specified or None
                has_pol = "polarity" in sym_filing and sym_filing["polarity"] is not None and np.isfinite(float(sym_filing["polarity"]))
                raw_pol = float(sym_filing["polarity"]) if has_pol else 1.0
                # Check for explicit insider role
                insider_role = str(sym_filing.get("insider_role", "")).upper()
                if "CEO" in insider_role or "CFO" in insider_role or "COO" in insider_role:
                    w_event = EVENT_WEIGHTS.get("insider_c_level", 2.00)
                elif "DIRECTOR" in insider_role or "OFFICER" in insider_role:
                    w_event = EVENT_WEIGHTS.get("insider_director", 1.00)
                else:
                    w_event = EVENT_WEIGHTS.get(event_type, 1.00)

                # Negative events (dilution/debt) are strictly non-positive, eliminating sign reversal
                if w_event < 0.0:
                    pol_mag = abs(raw_pol) if raw_pol != 0.0 else 1.0
                    s_filing = float(np.clip(-pol_mag * abs(w_event), -1.0, 0.0))
                else:
                    s_filing = float(np.clip(raw_pol * w_event, -1.0, 1.0))

            # 2. Conference Call Transcripts Guidance Drift
            sym_transcript = transcripts.get(sym_str, transcripts.get(sym_c))
            if sym_transcript and isinstance(sym_transcript, dict):
                has_nlp_data = True
                s_curr = float(sym_transcript.get("s_curr", sym_transcript.get("polarity", 0.0)))
                s_prev = float(sym_transcript.get("s_prev", 0.0))
                conv = float(sym_transcript.get("conviction", 1.0))
                prev_d = sym_transcript.get("prev_drift")

                tone_drift, tone_accel = compute_tone_drift_and_accel(
                    s_curr=s_curr, s_prev=s_prev, conviction=conv, prev_drift=prev_d
                )

            # 3. Triple-Layer Causal Fallbacks if Layer 1 Missing
            if not has_nlp_data:
                # Layer 2: Fundamental growth surprise
                fund_data = funds.get(sym_str, funds.get(sym_c))
                fund_proxy = self._compute_fundamental_growth_proxy(fund_data)

                # Layer 3: PEAD price-volume momentum
                pead_proxy = self._compute_pead_proxy(sym_str, p_dict)

                if fund_proxy != 0.0 or pead_proxy != 0.0:
                    tone_drift = 0.50 * fund_proxy + 0.50 * pead_proxy
                    tone_accel = 0.0
                    s_filing = 0.0
                else:
                    tone_drift = 0.0
                    tone_accel = 0.0
                    s_filing = 0.0

            # 4. Composite Scoring Formulation
            # Score_raw = 0.50 + 0.35 * S_DART + 0.40 * Tone_Drift * (1.0 + 0.50 * clip(Tone_Accel, -1.0, 2.0))
            drift_mult = 1.0 + 0.50 * float(np.clip(tone_accel, -1.0, 2.0))
            raw_score = 0.50 + 0.35 * s_filing + 0.40 * tone_drift * drift_mult
            clipped_score = float(np.clip(raw_score, 0.05, 0.95)) if np.isfinite(raw_score) else 0.50
            scores[sym_str] = round(clipped_score, 4)

        return make_score_dataframe(scores, score_column="nlp_catalyst_score")


# Module-level convenience functions
def compute_nlp_catalyst_scores(prices_dict: Any, **kwargs: Any) -> pd.DataFrame:
    """Convenience functional interface for NLPCatalystEngine."""
    engine = NLPCatalystEngine()
    return engine.compute_scores(prices_dict=prices_dict, **kwargs)

nlp_catalyst_score = compute_nlp_catalyst_scores

# Complete Alias Trees
Phase140NLPCatalystEngine = NLPCatalystEngine
F682NLPCatalystEngine = NLPCatalystEngine
FinBERTGuidanceDriftEngine = NLPCatalystEngine
AlternativeNLPCatalystEngine = NLPCatalystEngine
