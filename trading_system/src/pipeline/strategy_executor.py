"""
strategy_executor.py — Institutional-Grade Multi-Factor Strategy Execution Engine

Decomposes and modularizes the evaluation of 37 alpha strategies:
  - Standardized StrategyContext contract
  - Per-strategy isolated execution with exception guards & execution telemetry
  - Concurrent thread pool execution with CPU/IO awareness
  - Automated prediction report persistence via PredictionReporter
"""

from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Callable, Union

import numpy as np
import pandas as pd

from src.pipeline.prediction_reporter import save_strategy_predictions_report

logger = logging.getLogger(__name__)


@dataclass
class PipelineStrategyContext:
    """Encapsulates all data and configurations required for multi-factor strategy execution."""
    universe: pd.DataFrame
    infer_data_dict: Dict[str, pd.DataFrame]
    cfg: Any
    symbols_list: List[str] = field(default_factory=list)
    indicator_infer: Optional[pd.DataFrame] = None
    df_rim_input: Optional[pd.DataFrame] = None
    infer_fund_cache: Optional[Dict[str, Any]] = None
    storage: Optional[Any] = None
    model: Optional[Any] = None
    current_2d_regime: Optional[Any] = None
    res_df: Optional[pd.DataFrame] = None
    date_str: Optional[str] = None
    pred_limit: Union[int, str] = 100
    result_dir: str = ""
    strategy_workers: Optional[int] = None
    debug: bool = False

    # Pre-computed shared contexts (populated automatically if empty)
    eff_filings: List[Dict[str, Any]] = field(default_factory=list)
    sentiment_map: Dict[str, Any] = field(default_factory=dict)
    filings_map: Dict[str, str] = field(default_factory=dict)
    tone_transcript_map: Dict[str, Any] = field(default_factory=dict)
    m5_sentiment_metrics_list: List[Any] = field(default_factory=list)
    arm_fund: Dict[str, Any] = field(default_factory=dict)
    sector_mapping: Dict[str, str] = field(default_factory=dict)
    fund_input: Optional[pd.DataFrame] = None

    def __post_init__(self):
        if not self.symbols_list:
            if 'symbol' in self.universe.columns:
                self.symbols_list = self.universe['symbol'].tolist()
            else:
                self.symbols_list = list(self.infer_data_dict.keys())

        if self.fund_input is None and self.df_rim_input is not None and not self.df_rim_input.empty:
            self.fund_input = self.df_rim_input

        if not self.sector_mapping and 'symbol' in self.universe.columns:
            self.sector_mapping = dict(
                zip(self.universe['symbol'], self.universe.get('sector', self.universe.get('industry', 'DEFAULT')))
            )


@dataclass
class StrategySpec:
    """Specification of an alpha strategy for execution and reporting."""
    key: str
    name: str
    evaluator: Callable[[PipelineStrategyContext], pd.DataFrame]
    col: str
    title: str
    file: str
    hdr: str = "Score"
    w: int = 14


@dataclass
class StrategyExecutionResult:
    """Encapsulates execution results across all factor strategies."""
    raw_outputs: Dict[str, pd.DataFrame] = field(default_factory=dict)
    execution_times: Dict[str, float] = field(default_factory=dict)
    m5_sentiment_metrics_list: List[Any] = field(default_factory=list)
    sector_mapping: Dict[str, str] = field(default_factory=dict)
    arm_fund: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        df = self.raw_outputs.get(key)
        return df if (df is not None and isinstance(df, pd.DataFrame)) else (default if default is not None else pd.DataFrame())


class AlphaStrategyExecutor:
    """
    Orchestrates the evaluation of multi-factor alpha strategies.
    Ensures thread safety, exception isolation, clean logging, and structured reporting.
    """

    def __init__(self, specs: Optional[List[StrategySpec]] = None):
        self.specs: List[StrategySpec] = specs if specs is not None else self._build_default_strategy_specs()

    def prepare_shared_context(self, ctx: PipelineStrategyContext) -> None:
        """Pre-computes external filings, sentiment, and fundamental revisions once for all strategies."""
        # 1. DART filings & LLM sentiment
        if not ctx.eff_filings and not ctx.sentiment_map:
            try:
                from src.core.event_driven import EventDrivenEngine
                from src.core.llm_sentiment_engine import LLMSentimentEngine
                dart_key = getattr(ctx.cfg, 'dart_api_key', '') or ''
                if not dart_key or dart_key == 'your_dart_api_key_here':
                    logger.warning("[S-2 WARNING] DART_API_KEY is not configured. Event-Driven and Insider Buying "
                                   "will fall back to volume-breakout-only mode for Korean stocks.")
                event_engine_init = EventDrivenEngine(dart_api_key=dart_key)
                sentiment_engine_init = LLMSentimentEngine(db_storage=ctx.storage)
                ctx.eff_filings = event_engine_init.fetch_recent_dart_filings() or []
                if ctx.eff_filings:
                    ctx.sentiment_map = sentiment_engine_init.batch_analyze_filings(ctx.eff_filings) or {}
                    ctx.m5_sentiment_metrics_list = list(ctx.sentiment_map.values())
                else:
                    sample_syms = ctx.symbols_list[:min(len(ctx.symbols_list), 100)] if ctx.symbols_list else []
                    for s in sample_syms:
                        res = sentiment_engine_init.analyze_filing_text(str(s), f"Corporate operations and financial guidance for {s}")
                        ctx.sentiment_map[str(s)] = res
                        ctx.m5_sentiment_metrics_list.append(res)
            except Exception as e:
                logger.warning(f"[STRATEGY EXECUTOR] Pre-fetching DART filings/sentiment skipped: {e}")

        # 2. Build filings_map for NLP Sentiment
        if ctx.eff_filings and not ctx.filings_map:
            for item in ctx.eff_filings:
                if isinstance(item, dict):
                    sym = str(item.get('stock_code') or item.get('symbol') or '').strip()
                    txt = str(item.get('report_nm') or item.get('title') or item.get('content') or '').strip()
                    if sym and txt:
                        ctx.filings_map[sym] = (ctx.filings_map.get(sym, '') + ' ' + txt).strip()

        # 3. Build transcript_map for Earnings Tone Drift
        if ctx.sentiment_map and not ctx.tone_transcript_map:
            for s_k, s_val in ctx.sentiment_map.items():
                s_score = s_val if isinstance(s_val, (int, float)) else getattr(s_val, 'sentiment_score', 0.5)
                ctx.tone_transcript_map[s_k] = {'previous_quarter_tone': 0.5, 'current_quarter_tone': s_score}

        # 4. Build ARM fundamental revisions dictionary with dynamic filing lag
        if not ctx.arm_fund and ctx.infer_fund_cache:
            cur_dt = pd.to_datetime(ctx.date_str) if ctx.date_str else pd.Timestamp.now()
            for sym, fd in ctx.infer_fund_cache.items():
                if fd is None or len(fd) == 0:
                    continue
                if 'date_available' in fd.columns:
                    fd_valid = fd[pd.to_datetime(fd['date_available']) <= cur_dt]
                elif 'date' in fd.columns:
                    is_krx = str(sym).isdigit() or str(sym).endswith(('.KS', '.KQ'))
                    fund_dts = pd.to_datetime(fd['date'])
                    lags = fund_dts.apply(lambda dt: pd.Timedelta(days=90 if is_krx else 60) if getattr(dt, 'month', 0) == 12 else pd.Timedelta(days=45 if is_krx else 40))
                    fd_valid = fd[fund_dts + lags <= cur_dt]
                else:
                    fd_valid = fd

                if fd_valid.empty:
                    continue

                fd_sorted = fd_valid.sort_values('date') if 'date' in fd_valid.columns else fd_valid
                last_row = fd_sorted.iloc[-1]
                eps_g = 0.0
                rev_g = 0.0
                if len(fd_sorted) >= 2:
                    prev_row = fd_sorted.iloc[-2]
                    pe = float(prev_row.get('eps') or 0.0)
                    pr = float(prev_row.get('revenue') or 0.0)
                    if pe != 0:
                        eps_g = float((float(last_row.get('eps') or 0.0) - pe) / abs(pe))
                    if pr != 0:
                        rev_g = float((float(last_row.get('revenue') or 0.0) - pr) / abs(pr))
                elif isinstance(last_row, pd.Series):
                    eps_g = float(last_row.get('eps_growth_1y') or 0.0)
                    rev_g = float(last_row.get('revenue_growth_1y') or 0.0)

                tp_rev = None
                eps_rev = None
                per_val = None
                if isinstance(last_row, (pd.Series, dict)):
                    tp_rev = last_row.get('tp_revision_pct') or last_row.get('target_price_change_pct')
                    eps_rev = last_row.get('eps_revision_pct') or last_row.get('eps_consensus_change_pct')
                    per_val = last_row.get('per') or last_row.get('pe_ratio')

                if tp_rev is None and isinstance(last_row, (pd.Series, dict)) and 'target_price' in last_row and sym in ctx.infer_data_dict:
                    tp_val = float(last_row.get('target_price') or 0.0)
                    px_df = ctx.infer_data_dict[sym]
                    if tp_val > 0 and px_df is not None and not px_df.empty:
                        cur_px = float(px_df['Close'].iloc[-1])
                        if cur_px > 0:
                            tp_rev = float((tp_val / cur_px - 1.0) * 100.0)

                ctx.arm_fund[sym] = {
                    'eps_revision_pct': eps_rev,
                    'tp_revision_pct': tp_rev,
                    'eps_growth': eps_g,
                    'revenue_growth': rev_g,
                    'per': per_val,
                }

    def execute_all(self, ctx: PipelineStrategyContext) -> StrategyExecutionResult:
        """
        Executes all registered strategies concurrently with full exception isolation.
        """
        self.prepare_shared_context(ctx)

        workers = ctx.strategy_workers
        if workers is None:
            workers = max(1, min(8, getattr(ctx.cfg, 'strategy_scoring_workers', os.cpu_count() or 4)))

        logger.info(f"[STRATEGY EXECUTOR] Evaluating {len(self.specs)} factor strategies concurrently with {workers} worker threads...")

        result = StrategyExecutionResult(
            m5_sentiment_metrics_list=ctx.m5_sentiment_metrics_list,
            sector_mapping=ctx.sector_mapping,
            arm_fund=ctx.arm_fund
        )

        def _run_single(spec: StrategySpec):
            t0 = time.time()
            try:
                df_res = spec.evaluator(ctx)
                if not isinstance(df_res, pd.DataFrame):
                    df_res = pd.DataFrame()
                elapsed = time.time() - t0
                return spec.key, df_res, elapsed, None
            except Exception as err:
                elapsed = time.time() - t0
                logger.warning(f"[STRATEGY EXECUTOR] Strategy '{spec.key}' ({spec.name}) failed: {err}")
                return spec.key, pd.DataFrame(), elapsed, err

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_spec = {executor.submit(_run_single, s): s for s in self.specs}
            for future in as_completed(future_to_spec):
                key, df_res, elapsed, err = future.result()
                result.raw_outputs[key] = df_res
                result.execution_times[key] = elapsed
                if err is None:
                    logger.debug(f"[STRATEGY EXECUTOR] Completed '{key}' in {elapsed:.2f}s ({len(df_res)} rows)")

        # Generate reports for all evaluated strategies
        self.save_all_reports(result, ctx)

        return result

    def save_all_reports(self, result: StrategyExecutionResult, ctx: PipelineStrategyContext) -> None:
        """Saves prediction text reports for all strategies."""
        for spec in self.specs:
            df_s = result.raw_outputs.get(spec.key, pd.DataFrame())
            if df_s is None or df_s.empty:
                continue

            target_col = spec.col
            if target_col not in df_s.columns:
                for alt_c in ['neutralized_score', 'lstm_return_20d', 'score']:
                    if alt_c in df_s.columns:
                        target_col = alt_c
                        break

            if target_col in df_s.columns:
                save_strategy_predictions_report(
                    df_strat=df_s,
                    score_col=target_col,
                    title=spec.title,
                    output_filename=spec.file,
                    result_dir=ctx.result_dir,
                    universe=ctx.universe,
                    pred_limit=ctx.pred_limit,
                    score_header=spec.hdr,
                    header_width=spec.w
                )

    def _build_default_strategy_specs(self) -> List[StrategySpec]:
        """Constructs the standard specification registry for strategies 6, 10–37."""

        def _eval_lstm(ctx: PipelineStrategyContext) -> pd.DataFrame:
            if hasattr(ctx.model, "predict_lstm"):
                return ctx.model.predict_lstm(ctx.infer_data_dict, horizon=20)
            from src.ai.ml_strategy_adapters import LSTMStrategyAdapter
            return LSTMStrategyAdapter(model_instance=ctx.model, config=ctx.cfg).compute_scores(ctx.infer_data_dict)

        def _eval_event(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.event_driven import EventDrivenEngine
            dart_key = getattr(ctx.cfg, 'dart_api_key', '') or ''
            return EventDrivenEngine(dart_api_key=dart_key).compute_event_scores(
                symbols=ctx.symbols_list, prices_dict=ctx.infer_data_dict,
                filings=ctx.eff_filings, sentiment_map=ctx.sentiment_map
            )

        def _eval_mq(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.mq_factor import MQFactorEngine
            return MQFactorEngine().compute_mq_scores(prices_dict=ctx.infer_data_dict, features_df=ctx.fund_input)

        def _eval_iv_skew(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.iv_skew import IVSkewEngine
            return IVSkewEngine().compute_iv_skew_scores(symbols=ctx.symbols_list, prices_dict=ctx.infer_data_dict)

        def _eval_order_flow(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.order_flow import OrderFlowEngine
            return OrderFlowEngine().compute_order_flow_scores(prices_dict=ctx.infer_data_dict)

        def _eval_reversal(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.short_term_reversal import ShortTermReversalEngine
            return ShortTermReversalEngine().compute_reversal_scores(prices_dict=ctx.infer_data_dict, features_df=ctx.fund_input)

        def _eval_arm(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.arm_factor import ARMFactorEngine
            res = ARMFactorEngine().compute_scores(prices_dict=ctx.infer_data_dict, fundamentals_dict=ctx.arm_fund)
            if isinstance(res, dict):
                return pd.DataFrame([{'symbol': k, 'arm_score': v} for k, v in res.items()])
            return res if isinstance(res, pd.DataFrame) else pd.DataFrame()

        def _eval_card(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.card_factor import CARDFactorEngine
            ind_df = ctx.indicator_infer if ctx.indicator_infer is not None else pd.DataFrame()
            res = CARDFactorEngine().compute_scores(prices_dict=ctx.infer_data_dict, indicators_df=ind_df, sector_map=ctx.sector_mapping)
            if isinstance(res, dict):
                return pd.DataFrame([{'symbol': k, 'card_score': v} for k, v in res.items()])
            return res if isinstance(res, pd.DataFrame) else pd.DataFrame()

        def _eval_latr(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.latr_factor import LATRFactorEngine
            res = LATRFactorEngine().compute_scores(ctx.infer_data_dict)
            if isinstance(res, dict):
                return pd.DataFrame([{'symbol': k, 'latr_score': v} for k, v in res.items()])
            return res if isinstance(res, pd.DataFrame) else pd.DataFrame()

        def _eval_inst_foreign_sector(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.inst_foreign_sector import InstForeignSectorEngine
            return InstForeignSectorEngine(accumulation_days=40).compute_scores(ctx.infer_data_dict, flow_data_dict=None, sector_mapping=ctx.sector_mapping)

        def _eval_supply_chain(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.supply_chain import SupplyChainEngine
            return SupplyChainEngine().compute_scores(ctx.infer_data_dict, ctx.universe)

        def _eval_sentiment(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.llm_sentiment_engine import DARTSECSentimentEngine
            eng = DARTSECSentimentEngine(db_storage=ctx.storage)
            return eng.compute_scores(
                universe=ctx.universe, filings_map=ctx.filings_map,
                sentiment_map=ctx.sentiment_map if ctx.sentiment_map else None,
                filings=ctx.eff_filings if ctx.eff_filings else None,
                prices_dict=ctx.infer_data_dict
            )

        def _eval_factor_neutralized(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.multi_factor_neutralizer import MultiFactorNeutralizerEngine
            return MultiFactorNeutralizerEngine().compute_scores(
                prices_dict=ctx.infer_data_dict, universe=ctx.universe,
                raw_scores=ctx.res_df if (ctx.res_df is not None and not ctx.res_df.empty) else None,
                fundamentals_dict=ctx.infer_fund_cache if ctx.infer_fund_cache else None
            )

        def _eval_vol_target(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.vol_target import VolTargetingEngine
            return VolTargetingEngine().compute_scores(ctx.infer_data_dict, ctx.universe)

        def _eval_microstructure(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.hft_engine import MicrostructureImbalanceEngine
            return MicrostructureImbalanceEngine().compute_scores(ctx.infer_data_dict, ctx.universe)

        def _eval_accruals_quality(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.accruals_quality import AccrualsQualityEngine
            return AccrualsQualityEngine(ctx.cfg).calculate_scores(ctx.symbols_list, features_df=ctx.fund_input, prices_dict=ctx.infer_data_dict)

        def _eval_short_squeeze(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.short_interest_squeeze import ShortInterestSqueezeEngine
            return ShortInterestSqueezeEngine(ctx.cfg).calculate_scores(ctx.symbols_list, prices_dict=ctx.infer_data_dict, features_df=ctx.fund_input)

        def _eval_valueup_catalyst(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.valueup_catalyst import ValueUpCatalystEngine
            return ValueUpCatalystEngine(ctx.cfg).calculate_scores(ctx.symbols_list, features_df=ctx.fund_input, prices_dict=ctx.infer_data_dict)

        def _eval_trend_efficiency(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.trend_efficiency import TrendEfficiencyEngine
            return TrendEfficiencyEngine(ctx.cfg).calculate_scores(ctx.symbols_list, prices_dict=ctx.infer_data_dict, features_df=ctx.fund_input)

        def _eval_gamma_squeeze(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.gamma_squeeze import OptionsGammaSqueezeEngine
            return OptionsGammaSqueezeEngine(ctx.cfg).calculate_scores(ctx.symbols_list, prices_dict=ctx.infer_data_dict)

        def _eval_insider_buying(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.insider_buying import InsiderBuyingEngine
            return InsiderBuyingEngine(ctx.cfg).calculate_scores(ctx.symbols_list, prices_dict=ctx.infer_data_dict, insider_filings=ctx.eff_filings if ctx.eff_filings else None)

        def _eval_earnings_tone_drift(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.earnings_tone_drift import EarningsToneDriftEngine
            return EarningsToneDriftEngine(ctx.cfg).calculate_scores(
                ctx.symbols_list, prices_dict=ctx.infer_data_dict,
                transcript_map=ctx.tone_transcript_map if ctx.tone_transcript_map else None,
                features_df=ctx.fund_input
            )

        def _eval_darkpool(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.data_layer.darkpool_tracker import DarkPoolTrackerEngine
            return DarkPoolTrackerEngine(ctx.cfg).calculate_scores(ctx.symbols_list, prices_dict=ctx.infer_data_dict)

        def _eval_dual_correction(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.dual_correction import DualCorrectionEngine
            return DualCorrectionEngine(ctx.cfg).compute_scores(prices_dict=ctx.infer_data_dict, regime=ctx.current_2d_regime)

        def _eval_index_rebalance(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.index_rebalance import IndexRebalanceEngine
            return IndexRebalanceEngine().compute_scores(prices_dict=ctx.infer_data_dict, universe=ctx.universe)

        def _eval_overnight_gap_reversal(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.overnight_gap_reversal import OvernightGapReversalEngine
            return OvernightGapReversalEngine(ctx.cfg).calculate_scores(ctx.symbols_list, prices_dict=ctx.infer_data_dict)

        def _eval_cross_asset_spillover(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.cross_asset_spillover import CrossAssetSpilloverEngine
            return CrossAssetSpilloverEngine().compute_scores(prices_dict=ctx.infer_data_dict, indicators_df=ctx.indicator_infer)

        def _eval_supply_chain_gnn(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.supply_chain_gnn import SupplyChainGNNEngine
            return SupplyChainGNNEngine().compute_scores(prices_dict=ctx.infer_data_dict)

        def _eval_range_expansion_breakout(ctx: PipelineStrategyContext) -> pd.DataFrame:
            from src.core.range_expansion_breakout import RangeExpansionBreakoutEngine
            return RangeExpansionBreakoutEngine(ctx.cfg).compute_scores(prices_dict=ctx.infer_data_dict)

        return [
            StrategySpec('lstm', 'Strict Causal LSTM', _eval_lstm, 'lstm_score', 'Strategy 6: Strict Causal LSTM Predictions', 'lstm_predictions.txt', 'LSTM Score', 14),
            StrategySpec('event', 'Event-Driven Disclosure Catalyst', _eval_event, 'event_score', 'Strategy 10: Event-Driven Disclosure Catalyst Predictions', 'event_driven_predictions.txt', 'Event Score', 14),
            StrategySpec('mq', 'Momentum Quality (MQ) Factor', _eval_mq, 'mq_score', 'Strategy 11: Momentum Quality (MQ) Factor Predictions', 'mq_factor_predictions.txt', 'MQ Score', 14),
            StrategySpec('iv_skew', 'Options Put/Call IV Skew', _eval_iv_skew, 'iv_skew_score', 'Strategy 12: Options Put/Call IV Skew Predictions', 'iv_skew_predictions.txt', 'IV Skew Score', 14),
            StrategySpec('order_flow', 'Order Flow Imbalance (MFI)', _eval_order_flow, 'order_flow_score', 'Strategy 13: Order Flow Imbalance (MFI) Predictions', 'order_flow_predictions.txt', 'Order Flow Score', 16),
            StrategySpec('reversal', 'Short-Term Mean Reversal', _eval_reversal, 'reversal_score', 'Strategy 14: Short-Term Mean Reversal Predictions', 'short_term_reversal_predictions.txt', 'Reversal Score', 16),
            StrategySpec('arm', 'Analyst Revision Momentum (ARM)', _eval_arm, 'arm_score', 'Strategy 15: Analyst Revision Momentum (ARM) Factor Predictions', 'arm_factor_predictions.txt', 'ARM Score', 12),
            StrategySpec('card', 'Cross-Asset Regime Divergence (CARD)', _eval_card, 'card_score', 'Strategy 16: Cross-Asset Regime Divergence (CARD) Factor Predictions', 'card_factor_predictions.txt', 'CARD Score', 14),
            StrategySpec('latr', 'Liquidity-Adjusted Tail Risk (LATR)', _eval_latr, 'latr_score', 'Strategy 17: Liquidity-Adjusted Tail Risk (LATR) Factor Predictions', 'latr_factor_predictions.txt', 'LATR Score', 14),
            StrategySpec('inst_foreign_sector', 'Inst & Foreign Accumulation', _eval_inst_foreign_sector, 'inst_foreign_sector_score', 'Strategy 18: Inst & Foreign 2-Month Accumulation & Sector Correlation Predictions', 'inst_foreign_sector_predictions.txt', 'IFS Score', 14),
            StrategySpec('supply_chain', 'Supply Chain Lead-Lag Momentum', _eval_supply_chain, 'supply_chain_score', 'Strategy 19: Supply Chain Lead-Lag Momentum Predictions', 'supply_chain_predictions.txt', 'SC Score', 14),
            StrategySpec('sentiment', 'NLP & FinBERT Sentiment Catalyst', _eval_sentiment, 'sentiment_score', 'Strategy 20: NLP & FinBERT Sentiment Catalyst Predictions', 'sentiment_predictions.txt', 'Sent Score', 14),
            StrategySpec('factor_neutralized', 'Multi-Factor Style Neutralized', _eval_factor_neutralized, 'factor_neutralized_score', 'Strategy 21: Multi-Factor Style Neutralized Pure Alpha Predictions', 'factor_neutralized_predictions.txt', 'FN Score', 14),
            StrategySpec('vol_target', 'Dynamic Volatility Targeting', _eval_vol_target, 'vol_target_score', 'Strategy 22: Dynamic Volatility Targeting Risk Parity Predictions', 'vol_target_predictions.txt', 'VT Score', 14),
            StrategySpec('microstructure', 'Order Book Microstructure Imbalance', _eval_microstructure, 'microstructure_score', 'Strategy 23: Order Book Microstructure Imbalance Predictions', 'microstructure_predictions.txt', 'Micro Score', 14),
            StrategySpec('accruals_quality', 'Accruals Quality Anomaly', _eval_accruals_quality, 'accruals_quality_score', 'Strategy 24: Accruals Quality Anomaly Predictions', 'accruals_quality_predictions.txt', 'Accruals Score', 16),
            StrategySpec('short_squeeze', 'Short Interest & Squeeze Catalyst', _eval_short_squeeze, 'short_squeeze_score', 'Strategy 25: Short Interest & Squeeze Catalyst Predictions', 'short_squeeze_predictions.txt', 'Squeeze Score', 16),
            StrategySpec('valueup_catalyst', 'Value-Up & Shareholder Yield', _eval_valueup_catalyst, 'valueup_catalyst_score', 'Strategy 26: Value-Up & Shareholder Yield Predictions', 'valueup_catalyst_predictions.txt', 'ValueUp Score', 16),
            StrategySpec('trend_efficiency', 'Kaufman Trend Efficiency', _eval_trend_efficiency, 'trend_efficiency_score', 'Strategy 27: Kaufman Trend Efficiency Predictions', 'trend_efficiency_predictions.txt', 'Trend Score', 16),
            StrategySpec('gamma_squeeze', 'Options Gamma Squeeze', _eval_gamma_squeeze, 'gamma_squeeze_score', 'Strategy 28: Options Gamma Squeeze Predictions', 'gamma_squeeze_predictions.txt', 'Gamma Score', 16),
            StrategySpec('insider_buying', 'Insider Buying Catalyst', _eval_insider_buying, 'insider_buying_score', 'Strategy 29: Insider Buying Catalyst Predictions', 'insider_buying_predictions.txt', 'Insider Score', 16),
            StrategySpec('darkpool', 'HFT Order Flow & Dark Pool', _eval_darkpool, 'darkpool_score', 'Strategy 30: HFT Order Flow & Dark Pool Predictions', 'darkpool_predictions.txt', 'Darkpool Score', 16),
            StrategySpec('earnings_tone_drift', 'Earnings Tone Drift NLP', _eval_earnings_tone_drift, 'earnings_tone_drift_score', 'Strategy 31: Earnings Tone Drift NLP Predictions', 'earnings_tone_drift_predictions.txt', 'Tone Score', 16),
            StrategySpec('cross_asset_spillover', 'Cross-Asset Spillover Momentum', _eval_cross_asset_spillover, 'cross_asset_spillover_score', 'Strategy 32: Cross-Asset Spillover Momentum Predictions', 'cross_asset_spillover_predictions.txt', 'Spillover Score', 16),
            StrategySpec('supply_chain_gnn', 'Supply Chain GNN & Sector Flow', _eval_supply_chain_gnn, 'supply_chain_gnn_score', 'Strategy 33: Supply Chain GNN & Sector Flow Predictions', 'supply_chain_gnn_predictions.txt', 'SC GNN Score', 16),
            StrategySpec('range_expansion_breakout', 'Range Expansion Breakout', _eval_range_expansion_breakout, 'range_expansion_score', 'Strategy 34: Range Expansion Breakout Predictions', 'range_expansion_predictions.txt', 'Breakout Score', 16),
            StrategySpec('dual_correction', 'Dual Correction', _eval_dual_correction, 'dual_correction_score', 'Strategy 35: Dual Correction Predictions', 'dual_correction_predictions.txt', 'Dual Score', 16),
            StrategySpec('index_rebalance', 'Index Rebalance', _eval_index_rebalance, 'index_rebalance_score', 'Strategy 36: Index Rebalance Predictions', 'index_rebalance_predictions.txt', 'Rebal Score', 16),
            StrategySpec('overnight_gap_reversal', 'Overnight Gap Reversal', _eval_overnight_gap_reversal, 'overnight_gap_score', 'Strategy 37: Overnight Gap Reversal Predictions', 'overnight_gap_predictions.txt', 'Gap Score', 16),
        ]
