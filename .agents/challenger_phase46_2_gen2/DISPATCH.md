# DISPATCH: Challenger 2 gen2 (OMS & Deliverables Adversarial Challenger)

## Role & Working Directory
- Subagent Type: `teamwork_preview_challenger`
- Role: OMS & Deliverables Adversarial Challenger
- Working Directory: `d:\Finance\code\stock\.agents\challenger_phase46_2_gen2`

## Authoritative Inputs
- Original Request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: ## 2026-09-16T08:29:02Z)
- Orchestrator Plan: `d:\Finance\code\stock\.agents\orchestrator_quant_phase46_1\plan.md`
- Implementation Files to Stress-Test:
  - `trading_system/src/core/fast_lob_engine.py`
  - `trading_system/src/execution/smart_order_router.py`
  - `trading_system/src/execution/oms_engine.py`
  - `trading_system/scripts/benchmark_phase46_quant_performance.py`
  - 4 report paths
  - `AGENTS.md` and `PROJECT.md`

## Adversarial Verification Tasks
1. **Adversarial Precision & Microstructure Boundaries**:
   - Stress-test the lit maker floor $1 \times 10^{-18}$ under extreme toxicities ($\gamma_{\text{toxic}} \in [0.80, 0.99999, 1.0]$). Ensure no catastrophic cancellation, zero underflow, or negative values.
   - Verify dark ATS cap $99.99999999995\%$ under massive order sizes ($10^9$ shares) and rapid queue shifts.
   - Verify dynamic Anti-Gaming MinQty cap $99.99999999998\%$.
   - Verify micro-tick shading activation at $h > 0.00015$ and zero shading at $h \le 0.00015$.
2. **Benchmark Engine & Assertion Stress Test**:
   - Run `python trading_system/scripts/benchmark_phase46_quant_performance.py`.
   - Adversarially perturb baseline and target data to verify assertions actually trigger on failures (oracle test).
3. **4-Path SHA-256 Hash Synchronization Audit**:
   - Compute SHA-256 hashes of:
     * `reports/quant_benchmark_comparison_phase46.md`
     * `trading_system/result/quant_benchmark_comparison_phase46.md`
     * `trading_system/reports/quant_benchmark_comparison_phase46.md`
   - Verify all 3 hashes match 100%.
   - Verify `reports/quant_benchmark_comparison.md` contains Phase 46 table at top and preserved Phase 45 through historical archives.
4. **Full Test Suite Execution**:
   - Run full unit tests:
     ```powershell
     python -m pytest tests/test_phase46_alpha.py tests/test_phase46_risk.py tests/test_phase46_oms.py tests/test_phase45_alpha.py tests/test_phase45_risk.py tests/test_phase45_oms.py -v
     ```
   - Author and execute `tests/test_phase46_adversarial_oms_benchmark.py`.
5. Record empirical verdict: **APPROVE** or **REQUEST_CHANGES** in `handoff.md`.
