import os
import re

ROOT = r"d:\Finance\code\stock"

tasks = [
    ("V6-01", "trading_system/src/ai/prediction_model.py", [1514, 1775, 2487], "Strict causal LSTM target log1p transform vs regression inverse transform"),
    ("V6-02", "trading_system/src/ai/ensemble_scorer.py", [2559, 2620], "Multi-horizon exponential decay filter column name schema mapping"),
    ("V6-03", "trading_system/src/ai/ensemble_scorer.py", [1900, 1915], "Dual-regime weight squaring and cross-market weight contamination"),
    ("V6-04", "trading_system/src/ai/prediction_model.py", [2593, 2615], "predict_lstm cross-market model hijacking"),
    ("V6-05", "trading_system/src/ai/prediction_model.py", [3064, 3065], "predict_lead_lag fallback multi-year cumulative return scaling"),
    ("V6-06", "trading_system/src/ai/optuna_tuner.py", [553, 624, 698], "Optuna 2D regime bear volatility maximization distortion"),
    ("V6-07", "trading_system/src/ai/optuna_tuner.py", [317, 324], "Strategy 3 HPO selection threshold inflation and 10-symbol cap"),
    ("V6-08", "trading_system/src/ai/meta_ensemble_learner.py", [158, 183], "MetaEnsembleLearner feature permutation validation"),
    ("V6-09", "trading_system/src/risk/portfolio_allocator.py", [927, 960], "Leland dynamic buffer band new entry w_curr=0 suppression"),
    ("V6-10", "trading_system/src/analysis/portfolio_optimizer.py", [209, 221], "Black-Litterman piecewise objective step discontinuity in SLSQP"),
    ("V6-11", "trading_system/src/risk/portfolio_allocator.py", [341, 383], "EVT POT quantile inversion u > VaR_alpha and shape bounds"),
    ("V6-12", "trading_system/src/risk/portfolio_allocator.py", [1381, 1408], "Rockafellar-Uryasev convex CVaR non-differentiable L1 and T constraints"),
    ("V6-13", "trading_system/src/risk/risk_manager.py", [418, 434], "CrisisDetector recovery mode permanent latch"),
    ("V6-14", "trading_system/src/analysis/coverage_analyzer.py", [220, 226], "Coverage analyzer primary missing reason selector dictionary order"),
    ("V6-15", "trading_system/src/risk/portfolio_allocator.py", [151, 157], "Downside semi-cov equicorrelation shrinkage erasing hedge covariance"),
    ("V6-16", "trading_system/src/risk/fx_adjusted_covariance.py", [151, 165], "RMT Marchenko-Pastur hardcoded sigma_sq=1.0 noise variance"),
    ("V6-17", "trading_system/src/data_layer/earnings_data.py", [128, 251], "Sync vs async book value scale discrepancy Total Equity vs BPS"),
    ("V6-18", "trading_system/src/core/sector_rotation.py", [256], "SectorRotationEngine normalize_sector missing symbol argument"),
    ("V6-19", "trading_system/src/core/iv_skew.py", [108, 147], "IVSkewEngine live options chain fetch bypassed by proxy score != 0.5"),
    ("V6-20", "trading_system/src/core/event_driven.py", [149, 280], "EventDrivenEngine 8-digit corp_code direct comparison with 6-digit ticker"),
    ("V6-21", "trading_system/src/core/card_factor.py", [73, 129], "CARDFactorEngine 5:1 temporal horizon mismatch 5d stock vs 1d macro"),
    ("V6-22", "trading_system/src/core/mq_factor.py", [138], "Single-stock evaluation rank saturation bias N=1 score=0.98"),
    ("V6-23", "trading_system/src/core/stat_arb.py", [530], "StatisticalArbitrageEngine 100k array logging at INFO"),
    ("V6-24", "trading_system/src/persistence/database.py", [426, 455], "DataValidator reverse split handling voids and false positive spike removal"),
    ("V6-25", "trading_system/src/execution/oms_engine.py", [325, 390, 500, 573], "ExecutionOMSEngine USD/KRW currency denominator mismatch 1350x sizing"),
    ("V6-26", "trading_system/src/execution/oms_engine.py", [426, 479], "OMS Gates 7.2 & 7.4 return scale ambiguity +/-30% limit-locks"),
    ("V6-27", "trading_system/src/execution/oms_engine.py", [767, 789], "Almgren-Chriss slicing residual underflow producing negative quantities"),
    ("V6-28", "trading_system/src/execution/oms_engine.py", [440, 476], "OMS Gate 7.3 double deduction of friction costs against net alpha"),
    ("V6-29", "trading_system/src/execution/turnover_optimizer.py", [58, 86], "TurnoverOptimizer turnover hysteresis deadlock on liquidated positions"),
    ("V6-30", "trading_system/src/execution/slippage_feedback.py", [70, 105], "SlippageFeedbackEngine BUY_HEDGE sign inversion & SQLite connection leak"),
    ("V6-31", "trading_system/src/execution/sor_router.py", [67, 108], "SmartOrderRouter residual misrouting and duplicate ATS order splitting"),
    ("V6-32", "trading_system/src/config.py", [1, 46], "NameError json not imported in _build_market_lookup_table"),
    ("V6-33", "trading_system/run_pipeline.py", [1221, 4183], "Missing top-level try...finally for SQLite DB close and pipeline finalization"),
    ("V6-34", "trading_system/generate_run_snapshot.py", [118, 142], "generate_run_snapshot.py fallback text parser index mismatch flat 0.50"),
    ("V6-35", "trading_system/run_pipeline.py", [1233, 2700], "UTC vs KST date desync & config __post_init__ unparsed env vars")
]

print("=" * 80)
print("VERIFYING CODEBASE FOR ALL 35 AUDIT TASKS")
print("=" * 80)

for tid, rel_path, lines_to_check, desc in tasks:
    full_path = os.path.join(ROOT, rel_path.replace("/", os.sep))
    if not os.path.exists(full_path):
        # try without trading_system prefix or with it
        alt_path = os.path.join(ROOT, "trading_system", rel_path.replace("/", os.sep))
        if os.path.exists(alt_path):
            full_path = alt_path
        else:
            print(f"[{tid}] [FILE NOT FOUND] {rel_path}")
            continue
    
    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
        file_lines = f.readlines()
        
    line_count = len(file_lines)
    
    # Check if lines are within range
    line_status = []
    for l in lines_to_check:
        if 1 <= l <= line_count:
            snippet = file_lines[l-1].strip()[:60]
            line_status.append(f"L{l}: {snippet}")
        else:
            line_status.append(f"L{l}: [OUT OF RANGE, max={line_count}]")
            
    print(f"[{tid}] {rel_path} (Total Lines: {line_count})")
    print(f"       Description: {desc}")
    for ls in line_status:
        print(f"       -> {ls}")
    print()
