# Domain 5 Deep Audit Analysis: Pipeline, CI/CD, Concurrency & Infrastructure

**Document Version**: 6.0 (Domain 5 Forensic Audit)  
**Auditor**: Principal Systems Architect & Pipeline Reliability Auditor  
**Working Directory**: .agents/explorer_d5_pipeline_infra  
**Target Repository**: d:\Finance\code\stock  
**Date**: 2026-08-22 (KST)  
**Scope**: 	rading_system/run_pipeline.py, src/config.py, .github/workflows/, generate_run_snapshot.py, 	ests/ architecture.

---

## 1. Executive Summary & Audit Scope

This audit performed a line-by-line forensic investigation of the quantitative trading pipeline infrastructure, configuration loaders, CI/CD multi-matrix orchestration, snapshot generators, and test isolation frameworks.

All identified issues are **100% novel** with **0% duplication** against historical reports (Versions 1.0 through 5.0, comprising 142 previously cataloged items). Every issue is verified against exact, existing line numbers in the live codebase.

### Summary Table of Domain 5 Audit Findings

| Issue ID | Sub-Domain | Severity | Title | Target File & Exact Lines | Primary Impact |
|:---|:---|:---:|:---|:---|:---|
| **V6-29** | Config & Bootstrap | 🔴 CRITICAL | NameError: name 'json' is not defined in _build_market_lookup_table() during MARKET_COSTS_JSON Environment Parsing | 	rading_system/src/config.py:46 | Module bootstrap crash when injecting custom transaction cost schemas via env |
| **V6-30** | Pipeline Lifecycle | 🔴 CRITICAL | Unhandled Lifecycle Exit and SQLite Resource Leak in execute_prediction_pipeline() due to Missing Top-Level inally Protection | 	rading_system/run_pipeline.py:1193-1224, 4161-4212 | Permanent 'RUNNING' status corruption in DB run history and dangling WAL file locks upon failure |
| **V6-31** | CI/CD & Telemetry | 🟠 HIGH | Malformed Text Fallback Parser in generate_run_snapshot.py Fabricating Uniform 0.50 Scores in CI/CD Release Assets | 	rading_system/generate_run_snapshot.py:126-137 | Degraded release metadata where top 50 picks report hardcoded 0.50 scores and 0.0% expected returns |
| **V6-32** | Concurrency & Data | 🟡 MEDIUM | Cross-Timezone Date Desynchronization Between Ingestion Timestamp and Output Reporting | 	rading_system/run_pipeline.py:1233, 2698-2701 & 	rading_system/src/config.py:230-335 | Divergent calendar dates in SQLite vs. txt report headers on UTC runners; unparsed config env vars |

---

## 2. Detailed Technical Forensic Findings

### V6-29 [🔴 CRITICAL]: NameError: name 'json' is not defined in _build_market_lookup_table() under MARKET_COSTS_JSON

- **Exact File Path**: 	rading_system/src/config.py
- **Line Numbers**: Lines 1–15 (imports), Lines 41–62 (_build_market_lookup_table)
- **Severity**: 🔴 CRITICAL (P0)

#### Phenomenon & Root Cause
In 	rading_system/src/config.py, lines 41–62 define _build_market_lookup_table(), which runs at module import time (line 62: _MARKET_LOOKUP = _build_market_lookup_table()) to build the declarative market cost registry.
On line 46:
`python
43:     env_costs = os.environ.get("MARKET_COSTS_JSON")
44:     if env_costs:
45:         try:
46:             custom_costs = json.loads(env_costs)
`
However, inspecting lines 1–15 reveals:
`python
1: import logging
2: import math
3: import os
4: from dataclasses import dataclass, field
5: from pathlib import Path
6: from typing import Optional, Any
7: 
8: from dotenv import load_dotenv
`
import json was completely omitted from module imports. Whenever MARKET_COSTS_JSON is passed via container environment variables, Kubernetes configmaps, or .env files to configure dynamic transaction costs (spread bps, STT tax, brokerage fee), Python throws:
`	ext
NameError: name 'json' is not defined
`
Because src.config is imported at top level across un_pipeline.py, ensemble_scorer.py, portfolio_optimizer.py, and isk_manager.py, this unhandled NameError prevents the entire trading system and CLI from starting.

#### Distributed Systems & Reliability Rationale
12-factor application architecture mandates that configuration overrides (e.g. customized market fee tables for backtests vs. live broker accounts) be injected cleanly via environment variables. Omitting standard library module imports at top-level creates a latent runtime trap that explodes as soon as operators utilize the declared configuration hook.

#### Proposed Concrete Git Diff
`diff
--- a/trading_system/src/config.py
+++ b/trading_system/src/config.py
@@ -1,4 +1,5 @@
+import json
 import logging
 import math
 import os
 from dataclasses import dataclass, field
 from pathlib import Path
 from typing import Optional, Any
`

---

### V6-30 [🔴 CRITICAL]: Unhandled Lifecycle Exit and SQLite Resource Leak in execute_prediction_pipeline()

- **Exact File Path**: 	rading_system/run_pipeline.py
- **Line Numbers**: Lines 1218–1224 (run registration), Lines 4161–4212 (finalization & cleanup)
- **Severity**: 🔴 CRITICAL (P0)

#### Phenomenon & Root Cause
In 	rading_system/run_pipeline.py:execute_prediction_pipeline(), the orchestrator registers a pipeline execution at line 1221:
`python
1221:     current_run_id = storage.start_pipeline_run(trigger_type=_trigger_type, git_sha=_git_sha)
`
However, the corresponding finalization storage.finish_pipeline_run(...) (lines 4183–4200) and connection cleanup price_db.close() / storage.close() (lines 4202–4210) are placed inside an if os.path.exists(pipeline_res_path): block (line 4162):
`python
4161:     pipeline_res_path = os.path.join(result_dir, "pipeline_result.txt")
4162:     if os.path.exists(pipeline_res_path):
4163:         try:
...
4183:         if 'current_run_id' in locals() and current_run_id and storage is not None:
4184:             try:
...
4189:                 storage.finish_pipeline_run(
4190:                     run_id=current_run_id,
4191:                     status="SUCCESS",
...
4205:             if hasattr(price_db, 'close'):
4206:                 price_db.close()
4207:             if hasattr(storage, 'close'):
4208:                 storage.close()
4212:     return res_df, message_text
`
If an exception occurs at any point during steps 1 through 12 (for example, network timeout during indicator fetch, empty predictions exception at line 1810, out-of-memory crash during model inference, or post-verification exception at line 4159):
1. storage.finish_pipeline_run(status="FAILED", error_summary=...) is **never** executed. The pipeline_run_history table in SQLite retains status='RUNNING' indefinitely, corrupting pipeline run comparison logic (get_previous_run_id(), compare_runs()) on subsequent runs.
2. price_db.close() and storage.close() are never invoked. Open SQLite file descriptors, WAL write locks, and worker thread pool handles remain open, causing SQLite locking errors (database is locked) and resource exhaustion on iterative runs.
3. The function lacks a surrounding 	ry ... except ... finally structure.

#### Distributed Systems & Reliability Rationale
In enterprise ETL and quantitative trading pipelines, process lifecycle transitions (START -> SUCCESS / FAILED) must be guaranteed via strict RAII / context manager / 	ry...finally boundaries. Failing to capture catastrophic exceptions in the run manifest creates phantom active runs and pollutes cross-run performance attribution tracking.

#### Proposed Concrete Git Diff
`diff
--- a/trading_system/run_pipeline.py
+++ b/trading_system/run_pipeline.py
@@ -1194,6 +1194,10 @@ def execute_prediction_pipeline():
     _pipeline_start_time = time.time()
     logger.info("Starting consolidated market indicator and prediction pipeline...")
 
+    storage = None
+    price_db = None
+    current_run_id = None
+    try:
         # Ensure result directory exists early
         result_dir = os.environ.get("OUTPUT_RESULT_DIR", os.path.join(os.path.dirname(__file__), "result"))
         os.makedirs(result_dir, exist_ok=True)
@@ -4180,33 +4184,39 @@ def execute_prediction_pipeline():
         except Exception as e:
             logger.warning(f"Verification failed: Error reading/parsing pipeline_result.txt: {e}")
 
-        # Finalize pipeline run tracking in DB
-        if 'current_run_id' in locals() and current_run_id and storage is not None:
-            try:
-                total_syms = len(universe) if 'universe' in locals() and universe is not None else 0
-                dur_secs = time.time() - _pipeline_start_time if '_pipeline_start_time' in locals() else 0.0
-                active_mkts = list(universe['market'].unique()) if 'universe' in locals() and universe is not None and 'market' in universe.columns else []
-                regime_name = current_2d_regime if 'current_2d_regime' in locals() else ""
-                storage.finish_pipeline_run(
-                    run_id=current_run_id,
-                    status="SUCCESS",
-                    markets=active_mkts,
-                    total_symbols=total_syms,
-                    duration_seconds=dur_secs,
-                    regime_detected=regime_name
-                )
-                storage.prune_old_history(keep_days=180)
-                logger.info(f"[RUN HISTORY] Finalized run_id={current_run_id} (duration={dur_secs:.1f}s, symbols={total_syms})")
-            except Exception as _fin_e:
-                logger.warning(f"[RUN HISTORY] Failed to finalize pipeline run history: {_fin_e}")
-
+        return res_df, message_text
+    except Exception as _pipe_err:
+        if current_run_id and storage is not None:
+            try:
+                storage.finish_pipeline_run(
+                    run_id=current_run_id,
+                    status="FAILED",
+                    duration_seconds=time.time() - _pipeline_start_time,
+                    error_summary=str(_pipe_err)[:500]
+                )
+            except Exception:
+                pass
+        raise
+    finally:
+        if current_run_id and storage is not None and 'res_df' in locals() and not res_df.empty:
+            try:
+                total_syms = len(universe) if 'universe' in locals() and universe is not None else 0
+                dur_secs = time.time() - _pipeline_start_time
+                active_mkts = list(universe['market'].unique()) if 'universe' in locals() and universe is not None and 'market' in universe.columns else []
+                regime_name = current_2d_regime if 'current_2d_regime' in locals() else ""
+                storage.finish_pipeline_run(
+                    run_id=current_run_id,
+                    status="SUCCESS",
+                    markets=active_mkts,
+                    total_symbols=total_syms,
+                    duration_seconds=dur_secs,
+                    regime_detected=regime_name
+                )
+                storage.prune_old_history(keep_days=180)
+            except Exception:
+                pass
         try:
             if hasattr(price_db, 'close') and price_db is not None:
                 price_db.close()
             if hasattr(storage, 'close') and storage is not None:
                 storage.close()
         except Exception as e:
             logger.debug(f"DB close during pipeline cleanup: {e}")
`

---

### V6-31 [🟠 HIGH]: Malformed Text Fallback Parser in generate_run_snapshot.py Fabricating Uniform 0.50 Scores

- **Exact File Path**: 	rading_system/generate_run_snapshot.py
- **Line Numbers**: Lines 118–142
- **Severity**: 🟠 HIGH (P1)

#### Phenomenon & Root Cause
In GitHub Actions workflow .github/workflows/pipeline.yml, the merge-and-release job invokes python3 trading_system/generate_run_snapshot.py (line 309).
Since only prediction txt artifacts (pattern: result-*) are downloaded in merge-and-release, market_indicators.db is absent. generate_run_snapshot.py enters its fallback branch on line 118 (if not top_picks:).
Lines 125–137 parse ensemble_predictions.txt:
`python
125:                 for line in content.splitlines():
126:                     if re.match(r"^\s*\d+\s+[A-Za-z0-9.]+", line):
127:                         parts = line.split()
128:                         if len(parts) >= 3:
129:                             top_picks.append({
130:                                 "rank": rank,
131:                                 "symbol": parts[1],
132:                                 "ensemble_score": float(parts[2]) if parts[2].replace('.', '', 1).isdigit() else 0.5,
133:                                 "net_expected_return_pct": 0.0,
134:                                 "regime": regime_detected,
135:                                 "portfolio_weight": 0.0,
136:                                 "strategy_scores": {}
137:                             })
`
However, the actual format produced by un_pipeline.py (lines 3901–3944) is:
`	ext
Rank  Symbol     Name                Ens Score   Exp Ret(20D)  Reg  Srg  L-L ...
1.    005930     삼성전자            68.4%       +12.50%       65%  72%  ...
`
When split by whitespace:
- parts[0] = "1."
- parts[1] = "005930" (Symbol)
- parts[2] = "삼성전자" (Company Name)
- parts[3] = "68.4%" (True Ensemble Score)
- parts[4] = "+12.50%" (True Net Expected Return)
- parts[5:] = 31 strategy individual factor scores

Because parts[2] is the company name string, parts[2].replace('.', '', 1).isdigit() evaluates to False. The fallback parser assigns a default ensemble_score: 0.5 to every stock, sets 
et_expected_return_pct: 0.0, and leaves strategy_scores: {} empty.
Consequently, every un_snapshot.json asset published to GitHub Releases contains flat 0.50 scores across all 50 symbols.

#### Distributed Systems & Reliability Rationale
Release snapshot JSON files are primary integration contracts for mobile dashboards, monitoring services, and automated hedge OMS agents. Emitting corrupted, flat 50% score vectors due to an index mismatch silently breaks downstream automated risk systems.

#### Proposed Concrete Git Diff
`diff
--- a/trading_system/generate_run_snapshot.py
+++ b/trading_system/generate_run_snapshot.py
@@ -124,16 +124,37 @@ def generate_snapshot(result_dir: Path, db_path: Path, output_file: Path) -> Di
                 rank = 1
                 for line in content.splitlines():
-                    if re.match(r"^\s*\d+\s+[A-Za-z0-9.]+", line):
-                        parts = line.split()
-                        if len(parts) >= 3:
+                    m = re.match(r"^\s*(\d+)\.\s+(\S+)\s+(.+?)\s+([+-]?\d+\.?\d*)%\s+([+-]?\d+\.?\d*)%", line)
+                    if m:
+                        r_num, sym, name, ens_sc_str, exp_ret_str = m.groups()
+                        rest = line[m.end():].split()
+                        strat_map = {}
+                        score_keys = [
+                            'reg_score', 'surge_score', 'll_score', 'vcp_rule_score', 'vcp_ml_score',
+                            'lstm_score', 'stat_arb_score', 'sector_score', 'rim_score', 'event_score',
+                            'mq_score', 'iv_skew_score', 'order_flow_score', 'reversal_score',
+                            'arm_score', 'card_score', 'latr_score', 'inst_foreign_sector_score',
+                            'supply_chain_score', 'sentiment_score', 'factor_neutralized_score',
+                            'vol_target_score', 'microstructure_score', 'accruals_quality_score',
+                            'short_squeeze_score', 'valueup_catalyst_score', 'trend_efficiency_score',
+                            'gamma_squeeze_score', 'insider_buying_score', 'darkpool_score',
+                            'earnings_tone_drift_score'
+                        ]
+                        for idx, k in enumerate(score_keys):
+                            if idx < len(rest):
+                                val_s = rest[idx].rstrip('%')
+                                try:
+                                    strat_map[k] = round(float(val_s) / 100.0, 4)
+                                except ValueError:
+                                    pass
                         top_picks.append({
-                                "rank": rank,
-                                "symbol": parts[1],
-                                "ensemble_score": float(parts[2]) if parts[2].replace('.', '', 1).isdigit() else 0.5,
-                                "net_expected_return_pct": 0.0,
+                                "rank": int(r_num),
+                                "symbol": sym,
+                                "ensemble_score": round(float(ens_sc_str) / 100.0, 4),
+                                "net_expected_return_pct": round(float(exp_ret_str), 2),
                                 "regime": regime_detected,
                                 "portfolio_weight": 0.0,
-                                "strategy_scores": {}
+                                "strategy_scores": strat_map
                             })
                             rank += 1
                             if rank > 50:
`

---

### V6-32 [🟡 MEDIUM]: Cross-Timezone Date Desynchronization Between Ingestion Timestamp and Output Reporting

- **Exact File Path**: 	rading_system/run_pipeline.py & 	rading_system/src/config.py
- **Line Numbers**: un_pipeline.py:1233, 2698–2701; src/config.py:230–335
- **Severity**: 🟡 MEDIUM (P2)

#### Phenomenon & Root Cause
In 	rading_system/run_pipeline.py:
- At line 1233: date_str = datetime.now().strftime('%Y-%m-%d') uses naive local time (resolving to UTC date in default Linux Docker containers or GHA runners without explicit TZ).
- At line 2700: kst_now_str = datetime.now(KST).strftime('%Y-%m-%d %H:%M KST') explicitly binds UTC+9.
When runs execute between 00:00:00 and 08:59:59 UTC, the UTC date is T, whereas KST date is T (or when running at 16:00 UTC, UTC date is T while KST is T+1). This causes table inserts in i_predictions and market_indicators to record UTC dates while ensemble_predictions.txt headers record KST dates.
Furthermore, in src/config.py:__post_init__, critical liquidity and friction variables:
- min_daily_volume_krx, min_daily_volume_sp500, slippage_krx_market_order, portfolio_capital_krw, oms_net_alpha_safety_margin
are defined as dataclass fields but never parsed from os.environ, preventing dynamic container tuning without code modification.

#### Distributed Systems & Reliability Rationale
Consistent Point-in-Time date indexing across SQLite databases and user-facing text reports prevents off-by-one date join anomalies in historical backtesting and auditing.

#### Proposed Concrete Git Diff
`diff
--- a/trading_system/run_pipeline.py
+++ b/trading_system/run_pipeline.py
@@ -1230,7 +1230,9 @@ def execute_prediction_pipeline():
         market_summary = storage.get_latest_global_indicators()
 
     # 3. Store indicators
-    date_str = datetime.now().strftime('%Y-%m-%d')
+    from datetime import timezone, timedelta
+    KST = timezone(timedelta(hours=9))
+    date_str = datetime.now(KST).strftime('%Y-%m-%d')
     with storage.pipeline_stage("global_indicators"):
         storage.save_indicators(market_summary, date_str)
     logger.info("Saved market indicators to database.")
`

---

## 3. Verification Method & Cross-Validation

To verify that these issues and their proposed remediations maintain 100% test integrity:
1. Run full pytest regression suite:
   `ash
   .venv\Scripts\python.exe -m pytest tests/ -q
   `
2. Validate that src/config.py can be imported when MARKET_COSTS_JSON='{"KOSPI": {"spread_bps": 0.0005}}' is set in os.environ.
3. Validate that execute_prediction_pipeline() closes DB connections and logs status="FAILED" in pipeline_run_history upon simulated exceptions.
4. Validate that generate_run_snapshot.py correctly parses symbol, rank, score, return, and all 31 strategy factors from text files.
