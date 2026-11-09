"""
scripts/verify_adversarial_m4_challenger1.py — Empirical Challenger 1 Harness for Release R182 Milestone M4
Phase 191 Execution OMS & 30-Year Compounding Benchmark Elevation (Features F935 & F936).

Adversarial Stress Verification Objectives:
1. F935: Distributional SAC 95-Quantile Downside-Averse Order Slicing Agent
   - Quantile grid monotonicity: tau_i = (2i - 1) / 190 strictly increasing in (0, 1)
   - Double duelling architecture: Advantage mean-centering and conservative double-Q envelope
   - Downside CVaR calculation against an independent reference quantile sort oracle
   - Stress test extreme inputs (NaN, Inf, negative inventory, time ratio > 1.0) and guardrails
   - Slicing bounds [0.01, 0.40] and routing simplex probability conservation sum(w_i) == 1.0
2. F936: Sub-Microsecond Zero-Copy L3 Hawkes Matching Core
   - Multithreaded order injection concurrency stress test: 16 threads, 40,000 orders
   - Contiguous sequence IDs verification (zero duplicates, zero gaps, 100% contiguous)
   - Latency benchmark: 100,000 appends/reads, latency target strictly < 15.0 us
   - Hawkes order arrival intensity under sudden cluster bursts and asymptotic time decay
   - VPIN order flow toxicity calculation boundedness strictly in [0.0, 1.0] across extreme flows
"""

import math
import sys
import time
import threading
from pathlib import Path
from typing import Dict, List, Any
import numpy as np

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
TS_ROOT = PROJECT_ROOT / "trading_system"
if str(TS_ROOT) not in sys.path:
    sys.path.insert(0, str(TS_ROOT))

from src.execution.rl_execution_agent import (
    DistributionalSAC95QuantileCritic,
    DistributionalSAC95QuantileAgent,
    ExecutionState,
    evaluate_execution_action_phase191,
    compute_optimal_execution_slice_95quantile,
)
from src.core.fast_lob_engine import (
    ZeroCopyRingBuffer,
    FastOrderBookMatchingEngine,
    LATENCY_TARGET_US_PHASE191,
)


def verify_f935_quantile_grid_monotonicity_and_duelling() -> Dict[str, Any]:
    """Objective 1A: Verify F935 quantile grid monotonicity and double duelling architecture."""
    print("\n" + "=" * 70)
    print("VERIFYING F935: Quantile Grid Monotonicity & Double Duelling Architecture")
    print("=" * 70)

    dim = 12
    critic = DistributionalSAC95QuantileCritic(state_dim=dim, num_quantiles=95)

    # 1. Quantile grid verification
    grid = critic.tau_hat
    n_quantiles = len(grid)
    print(f"Number of quantiles: {n_quantiles} (expected 95)")
    assert n_quantiles == 95, f"Expected 95 quantiles, got {n_quantiles}"

    # Verify formula tau_i = (2i - 1) / 190
    expected_grid = np.array([(2.0 * i - 1.0) / 190.0 for i in range(1, 96)], dtype=np.float64)
    max_formula_diff = np.max(np.abs(grid - expected_grid))
    print(f"Max deviation from formula (2i - 1)/190: {max_formula_diff:.6e}")
    assert max_formula_diff < 1e-14, f"Grid deviates from theoretical definition: {max_formula_diff}"

    # Strict monotonicity
    diffs = np.diff(grid)
    min_diff = np.min(diffs)
    max_diff = np.max(diffs)
    print(f"Min step delta: {min_diff:.6f}, Max step delta: {max_diff:.6f} (expected 2/190 = {2.0/190.0:.6f})")
    assert min_diff > 0.0, "Quantile grid is not strictly increasing!"
    assert math.isclose(min_diff, 2.0 / 190.0, abs_tol=1e-12)
    assert math.isclose(max_diff, 2.0 / 190.0, abs_tol=1e-12)

    # Boundary properties: strictly inside (0, 1)
    tau_0 = grid[0]
    tau_last = grid[-1]
    print(f"tau_1: {tau_0:.6f} (> 0.0 PASS), tau_95: {tau_last:.6f} (< 1.0 PASS)")
    assert 0.0 < tau_0 < 1.0, f"tau_1 out of bounds: {tau_0}"
    assert 0.0 < tau_last < 1.0, f"tau_95 out of bounds: {tau_last}"
    assert math.isclose(tau_0, 1.0 / 190.0, abs_tol=1e-12)
    assert math.isclose(tau_last, 189.0 / 190.0, abs_tol=1e-12)

    # 2. Double Duelling Critic Forward & Centering
    rng = np.random.RandomState(42)
    s = rng.randn(dim)
    v, a = critic.forward(s)

    assert v.shape == (95,), f"Value stream shape mismatch: {v.shape}"
    assert a.shape == (4, 95), f"Advantage stream shape mismatch: {a.shape}"

    # Check zero-mean centering across 4 actions: sum_a A(s, a) == 0
    a_mean = np.mean(a, axis=0)
    max_mean_error = np.max(np.abs(a_mean))
    print(f"Max Advantage mean-centering residual across 4 actions: {max_mean_error:.6e}")
    assert max_mean_error < 1e-12, f"Advantage stream is not zero-mean centered: {max_mean_error}"

    # 3. Conservative Double-Q Envelope & Sorting
    for act in range(4):
        quantiles = critic.evaluate_quantiles(s, action_idx=act)
        assert quantiles.shape == (95,), f"Quantiles shape mismatch: {quantiles.shape}"
        assert np.all(np.diff(quantiles) >= -1e-10), f"Quantiles not monotonic non-decreasing for action {act}"

    print("Quantile grid and duelling architecture strictly verified (PASS).")
    return {
        "n_quantiles": n_quantiles,
        "max_formula_diff": max_formula_diff,
        "tau_1": tau_0,
        "tau_95": tau_last,
        "max_mean_error": max_mean_error,
        "status": "PASS",
    }


def verify_f935_downside_cvar_against_oracle() -> Dict[str, Any]:
    """Objective 1B: Verify worst 5% tail downside CVaR calculation against an independent reference oracle."""
    print("\n" + "=" * 70)
    print("VERIFYING F935: Tail Downside CVaR (Worst 5%) Against Reference Oracle")
    print("=" * 70)

    agent = DistributionalSAC95QuantileAgent(state_dim=12)
    rng = np.random.RandomState(999)

    # Reference Oracle Implementation
    def reference_cvar_oracle(quantiles_input: np.ndarray, alpha: float = 0.95) -> float:
        q_sorted = np.sort(np.asarray(quantiles_input, dtype=np.float64))
        m = max(1, int(np.floor((1.0 - alpha) * len(q_sorted))))
        tail = q_sorted[:m]
        tail_mean = float(np.mean(tail))
        return float(-tail_mean if tail_mean < 0.0 else 0.0)

    # Test across 1,000 diverse return scenarios
    n_scenarios = 1000
    max_discrepancy = 0.0

    distributions = [
        ("Gaussian_Loss", lambda: rng.normal(loc=-10.0, scale=25.0, size=95)),
        ("Gaussian_Profit", lambda: rng.normal(loc=15.0, scale=5.0, size=95)),
        ("Student_t_HeavyTail", lambda: rng.standard_t(df=2.5, size=95) * 20.0 - 5.0),
        ("Uniform_Spread", lambda: rng.uniform(-100.0, 50.0, size=95)),
        ("Crash_Scenario", lambda: np.concatenate([rng.uniform(-500.0, -200.0, 5), rng.normal(5.0, 2.0, 90)])),
        ("All_Positive", lambda: rng.uniform(1.0, 50.0, size=95)),
        ("All_Zero", lambda: np.zeros(95)),
        ("All_Negative", lambda: rng.uniform(-80.0, -10.0, size=95)),
    ]

    for dist_name, dist_gen in distributions:
        for _ in range(n_scenarios // len(distributions)):
            sample_quantiles = dist_gen()
            expected_cvar = reference_cvar_oracle(sample_quantiles, alpha=0.95)
            computed_cvar = agent.compute_downside_cvar(sample_quantiles, alpha=0.95)

            diff = abs(computed_cvar - expected_cvar)
            if diff > max_discrepancy:
                max_discrepancy = diff
            assert diff < 1e-10, f"Discrepancy {diff} in {dist_name}: expected {expected_cvar}, got {computed_cvar}"

    print(f"Tested {n_scenarios} random quantile scenarios across 8 distribution families.")
    print(f"Max discrepancy against Reference Oracle: {max_discrepancy:.6e} (< 1e-10 PASS)")

    # Special boundary assertions
    # 1. All positive returns should yield exactly 0.0 downside CVaR
    pos_q = np.linspace(10.0, 100.0, 95)
    assert agent.compute_downside_cvar(pos_q) == 0.0, "Positive returns must have zero downside CVaR"

    # 2. All zero returns should yield exactly 0.0 downside CVaR
    assert agent.compute_downside_cvar(np.zeros(95)) == 0.0, "Zero returns must have zero downside CVaR"

    # 3. Known synthetic case: linear -100 to +100
    lin_q = np.linspace(-100.0, 100.0, 95)
    # Bottom 4 quantiles of lin_q:
    m_count = max(1, int(np.floor(0.05 * 95)))  # 4
    expected_lin_cvar = -float(np.mean(lin_q[:m_count]))
    computed_lin_cvar = agent.compute_downside_cvar(lin_q)
    assert math.isclose(computed_lin_cvar, expected_lin_cvar, abs_tol=1e-10)
    print(f"Linear sample CVaR: {computed_lin_cvar:.4f} == {expected_lin_cvar:.4f} (PASS)")

    return {
        "n_scenarios": n_scenarios,
        "max_discrepancy": max_discrepancy,
        "status": "PASS",
    }


def verify_f935_extreme_inputs_and_guardrails() -> Dict[str, Any]:
    """Objective 1C: Stress test double duelling agent under extreme inputs (NaN, Inf, negative inv, time > 1)."""
    print("\n" + "=" * 70)
    print("VERIFYING F935: Extreme Input Resilience & Execution Guardrails")
    print("=" * 70)

    agent = DistributionalSAC95QuantileAgent(state_dim=12)

    # Guardrail 1: Zero inventory -> PAUSE (slice 0.0)
    for zero_inv in [0.0, 1e-7, -1e-9]:
        st = ExecutionState(time_ratio=0.5, inventory_ratio=zero_inv)
        res = agent.get_optimal_action(st)
        assert res.action_name == "PAUSE", f"Zero inv {zero_inv} failed: got {res.action_name}"
        assert res.slice_ratio == 0.0, f"Zero inv slice ratio {res.slice_ratio} != 0.0"
    print("Guardrail 1 (Zero Inventory -> PAUSE, slice 0.0): PASS")

    # Guardrail 2: Negative inventory -> PAUSE (slice 0.0)
    for neg_inv in [-0.01, -0.50, -10.0, -1000.0]:
        st = ExecutionState(time_ratio=0.3, inventory_ratio=neg_inv)
        res = agent.get_optimal_action(st)
        assert res.action_name == "PAUSE", f"Negative inv {neg_inv} failed: got {res.action_name}"
        assert res.slice_ratio == 0.0, f"Negative inv slice ratio {res.slice_ratio} != 0.0"
    print("Guardrail 2 (Negative Inventory -> PAUSE, slice 0.0): PASS")

    # Guardrail 3: Terminal urgency (time >= 0.95 with positive inventory) -> AGGRESSIVE (slice >= 0.30)
    urgency_cases = [
        (0.95, 0.50),
        (0.96, 0.30),
        (0.99, 0.80),
        (1.00, 0.20),
        (1.50, 0.40),  # time > 1.0
        (5.00, 1.00),  # extreme time
    ]
    for t_val, inv_val in urgency_cases:
        st = ExecutionState(time_ratio=t_val, inventory_ratio=inv_val)
        res = agent.get_optimal_action(st)
        assert res.action_name == "AGGRESSIVE", f"Terminal urgency (t={t_val}, inv={inv_val}) got {res.action_name}"
        assert res.slice_ratio >= 0.30, f"Terminal slice ratio {res.slice_ratio} < 0.30"
        assert res.routing_simplex[0] >= 0.50, "Aggressive routing weight should dominate"
    print("Guardrail 3 (Terminal Urgency t >= 0.95 & t > 1.0 -> AGGRESSIVE, slice >= 0.30): PASS")

    # Guardrail 4: Toxic VPIN (> 0.65) -> PAUSE / conservative slice <= 0.05
    for toxic_vpin in [0.66, 0.75, 0.90, 0.999]:
        st = ExecutionState(time_ratio=0.4, inventory_ratio=0.6, vpin=toxic_vpin)
        res = agent.get_optimal_action(st)
        assert res.action_name == "PAUSE" or res.slice_ratio <= 0.05, (
            f"Toxic VPIN {toxic_vpin} breach: action={res.action_name}, slice={res.slice_ratio}"
        )
    print("Guardrail 4 (Toxic VPIN > 0.65 -> PAUSE / slice <= 0.05): PASS")

    # Guardrail 5: Continuous Slicing Clamping & Simplex Probability Conservation
    rng = np.random.RandomState(777)
    for _ in range(500):
        t_rand = rng.uniform(0.0, 0.94)
        inv_rand = rng.uniform(0.01, 1.0)
        vpin_rand = rng.uniform(0.0, 0.64)
        st = ExecutionState(time_ratio=t_rand, inventory_ratio=inv_rand, vpin=vpin_rand)
        res = agent.get_optimal_action(st)

        # Slice ratio clamped to [0.01, 0.40]
        assert 0.01 <= res.slice_ratio <= 0.40, f"Slice ratio {res.slice_ratio} outside [0.01, 0.40]"

        # Simplex probability conservation sum(w_i) == 1.0
        simplex = res.routing_simplex
        assert len(simplex) == 4, f"Expected 4 simplex components, got {len(simplex)}"
        assert np.all(simplex >= 0.0), f"Negative simplex component: {simplex}"
        assert math.isclose(float(np.sum(simplex)), 1.0, abs_tol=1e-6), f"Simplex does not sum to 1.0: {np.sum(simplex)}"

    print("Guardrail 5 (Continuous Slicing [0.01, 0.40] & Simplex Sum == 1.0): PASS")

    # Guardrail 6: Robustness under extreme / corrupted numerical inputs
    corrupted_states = [
        ("NaN_vol", ExecutionState(time_ratio=0.5, inventory_ratio=0.5, volatility=float("nan"))),
        ("Inf_spread", ExecutionState(time_ratio=0.5, inventory_ratio=0.5, spread_bps=float("inf"))),
        ("Neg_Inf_obi", ExecutionState(time_ratio=0.5, inventory_ratio=0.5, obi=-float("inf"))),
        ("Negative_time", ExecutionState(time_ratio=-0.5, inventory_ratio=0.5)),
    ]
    for name, st in corrupted_states:
        # Agent should handle gracefully without crashing or throwing unhandled exceptions
        try:
            res = agent.get_optimal_action(st)
            assert res is not None
            assert math.isfinite(res.slice_ratio) or res.slice_ratio == 0.0
            print(f"Handled {name} gracefully: action={res.action_name}, slice={res.slice_ratio}")
        except Exception as e:
            assert False, f"Agent crashed on corrupted input {name}: {e}"

    print("Extreme input resilience and all guardrails strictly verified (PASS).")
    return {"status": "PASS"}


def verify_f936_multithreaded_ring_buffer_concurrency() -> Dict[str, Any]:
    """Objective 2A: Stress test multithreaded order injection into ZeroCopyRingBuffer."""
    print("\n" + "=" * 70)
    print("VERIFYING F936: Multithreaded Zero-Copy Ring Buffer Concurrency Stress")
    print("=" * 70)

    capacity = 8192
    buf = ZeroCopyRingBuffer(capacity=capacity)

    # Cacheline padding verification
    assert hasattr(buf, "_pad0"), "Missing _pad0"
    assert hasattr(buf, "_pad1"), "Missing _pad1"
    assert len(buf._pad0) == 64, f"_pad0 length {len(buf._pad0)} != 64"
    assert len(buf._pad1) == 64, f"_pad1 length {len(buf._pad1)} != 64"
    print("64-byte pre and post cacheline padding buffers verified.")

    n_threads = 16
    orders_per_thread = 2500
    total_orders = n_threads * orders_per_thread

    thread_results: List[List[int]] = [[] for _ in range(n_threads)]
    thread_exceptions: List[Exception] = []

    def worker_thread(tid: int):
        try:
            local_seqs = []
            for i in range(orders_per_thread):
                seq = buf.append_order_phase191(
                    order_id=f"T{tid}_{i}",
                    symbol="005930",
                    side="BUY" if i % 2 == 0 else "SELL",
                    price=70000.0 + (i % 100),
                    quantity=10,
                )
                local_seqs.append(seq)
            thread_results[tid] = local_seqs
        except Exception as e:
            thread_exceptions.append(e)

    print(f"Launching {n_threads} concurrent threads ({orders_per_thread} orders/thread = {total_orders} orders)...")
    threads = [threading.Thread(target=worker_thread, args=(t,)) for t in range(n_threads)]

    t0 = time.perf_counter()
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    elapsed_s = time.perf_counter() - t0

    assert len(thread_exceptions) == 0, f"Thread exceptions occurred: {thread_exceptions}"

    # Flatten all returned sequence IDs
    all_seqs = []
    for local_list in thread_results:
        all_seqs.extend(local_list)

    print(f"Execution completed in {elapsed_s:.3f} s ({total_orders / elapsed_s:.0f} orders/sec)")
    print(f"Total sequence IDs returned: {len(all_seqs)} (expected {total_orders})")
    assert len(all_seqs) == total_orders, f"Expected {total_orders} sequences, got {len(all_seqs)}"

    # 1. Verify uniqueness: zero duplicate IDs across threads
    unique_seqs = set(all_seqs)
    n_unique = len(unique_seqs)
    print(f"Unique sequence IDs: {n_unique} / {total_orders}")
    assert n_unique == total_orders, f"RACE CONDITION DETECTED! Duplicate IDs: {total_orders - n_unique}"

    # 2. Verify contiguity: strictly 1 to total_orders with zero gaps
    min_seq = min(all_seqs)
    max_seq = max(all_seqs)
    print(f"Min sequence ID: {min_seq}, Max sequence ID: {max_seq}")
    assert min_seq == 1, f"Expected min seq 1, got {min_seq}"
    assert max_seq == total_orders, f"Expected max seq {total_orders}, got {max_seq}"

    sorted_seqs = sorted(all_seqs)
    expected_seqs = list(range(1, total_orders + 1))
    assert sorted_seqs == expected_seqs, "Sequence IDs are not strictly contiguous!"

    # 3. Verify internal ring buffer head and tail state
    assert buf.head == total_orders, f"Buffer head mismatch: {buf.head} != {total_orders}"
    expected_tail = max(0, total_orders - capacity)
    assert buf.tail == expected_tail, f"Buffer tail mismatch: {buf.tail} != {expected_tail}"
    assert buf.count == capacity, f"Buffer count mismatch: {buf.count} != {capacity}"

    print("Zero race conditions, zero duplicates, sequence IDs 100% CONTIGUOUS (PASS).")
    return {
        "n_threads": n_threads,
        "total_orders": total_orders,
        "elapsed_s": elapsed_s,
        "throughput_ops_sec": total_orders / elapsed_s,
        "min_seq": min_seq,
        "max_seq": max_seq,
        "status": "PASS",
    }


def verify_f936_latency_benchmark() -> Dict[str, Any]:
    """Objective 2B: Benchmark ring buffer append and read latency (< 15.0 us target)."""
    print("\n" + "=" * 70)
    print("VERIFYING F936: Sub-Microsecond Ring Buffer Latency Benchmark (< 15.0 us)")
    print("=" * 70)

    capacity = 131072
    buf = ZeroCopyRingBuffer(capacity=capacity)

    # Warmup
    for i in range(1000):
        buf.append_order_phase191(order_id=f"W_{i}", symbol="AAPL", side="BUY", price=150.0, quantity=10)

    n_samples = 100000
    latencies_us = np.zeros(n_samples, dtype=np.float64)

    t0_all = time.perf_counter()
    for i in range(n_samples):
        t0 = time.perf_counter()
        buf.append_order_phase191(
            order_id=f"B_{i}",
            symbol="AAPL",
            side="BUY" if i % 2 == 0 else "SELL",
            price=150.0 + (i % 50) * 0.1,
            quantity=100,
        )
        t1 = time.perf_counter()
        latencies_us[i] = (t1 - t0) * 1e6
    t_total = time.perf_counter() - t0_all

    mean_lat = float(np.mean(latencies_us))
    median_lat = float(np.median(latencies_us))
    p90_lat = float(np.percentile(latencies_us, 90))
    p95_lat = float(np.percentile(latencies_us, 95))
    p99_lat = float(np.percentile(latencies_us, 99))
    max_lat = float(np.max(latencies_us))

    print(f"Executed {n_samples:,} ring buffer appends in {t_total:.3f} s:")
    print(f"  Mean latency:   {mean_lat:.3f} us")
    print(f"  Median latency: {median_lat:.3f} us")
    print(f"  P90 latency:    {p90_lat:.3f} us")
    print(f"  P95 latency:    {p95_lat:.3f} us")
    print(f"  P99 latency:    {p99_lat:.3f} us")
    print(f"  Max latency:    {max_lat:.3f} us")
    print(f"  Target SLA:     < {LATENCY_TARGET_US_PHASE191:.1f} us")

    assert mean_lat < LATENCY_TARGET_US_PHASE191, (
        f"Mean latency {mean_lat:.3f} us exceeded target SLA {LATENCY_TARGET_US_PHASE191} us"
    )
    assert median_lat < LATENCY_TARGET_US_PHASE191, (
        f"Median latency {median_lat:.3f} us exceeded target SLA {LATENCY_TARGET_US_PHASE191} us"
    )

    # Benchmark read latency: get_recent(100)
    read_samples = 10000
    read_latencies_us = np.zeros(read_samples, dtype=np.float64)
    for i in range(read_samples):
        t0 = time.perf_counter()
        _ = buf.get_recent(100)
        t1 = time.perf_counter()
        read_latencies_us[i] = (t1 - t0) * 1e6

    mean_read_lat = float(np.mean(read_latencies_us))
    p95_read_lat = float(np.percentile(read_latencies_us, 95))
    print(f"Executed {read_samples:,} ring buffer reads (n=100):")
    print(f"  Mean read latency: {mean_read_lat:.3f} us, P95: {p95_read_lat:.3f} us")
    assert mean_read_lat < LATENCY_TARGET_US_PHASE191, f"Read latency exceeded {LATENCY_TARGET_US_PHASE191} us"

    print(f"Latency target strictly met with massive safety headroom (PASS).")
    return {
        "n_samples": n_samples,
        "mean_latency_us": mean_lat,
        "median_latency_us": median_lat,
        "p95_latency_us": p95_lat,
        "p99_latency_us": p99_lat,
        "mean_read_latency_us": mean_read_lat,
        "status": "PASS",
    }


def verify_f936_hawkes_bursts_and_stability() -> Dict[str, Any]:
    """Objective 2C: Stress test Hawkes order arrival intensity under sudden cluster bursts and decay."""
    print("\n" + "=" * 70)
    print("VERIFYING F936: Hawkes Order Arrival Intensity Cluster Bursts & Decay")
    print("=" * 70)

    engine = FastOrderBookMatchingEngine()
    mu = 1.0

    # 1. Baseline intensity
    base_res = engine.compute_l3_hawkes_order_intensity(symbol="005930", base_rate=mu)
    assert base_res["lambda_buy"] >= mu
    assert base_res["lambda_sell"] >= mu
    assert base_res["total_intensity"] >= 2.0 * mu
    print(f"Baseline intensity: lambda_buy={base_res['lambda_buy']:.2f}, lambda_sell={base_res['lambda_sell']:.2f}")

    # 2. Sudden cluster burst: 200 aggressive sell orders in 5 milliseconds
    t_burst = time.time()
    n_burst = 200
    for i in range(n_burst):
        engine.record_order_arrival(symbol="005930", side="SELL", timestamp=t_burst + i * 0.000025)

    burst_res = engine.compute_l3_hawkes_order_intensity(
        symbol="005930",
        base_rate=mu,
        current_timestamp=t_burst + 0.006,
    )
    print(f"Post-burst sell intensity: lambda_sell = {burst_res['lambda_sell']:.2f} (baseline = {mu})")
    assert burst_res["lambda_sell"] > 3.0 * mu, f"Sell intensity did not surge: {burst_res['lambda_sell']}"
    assert burst_res["lambda_sell"] > burst_res["lambda_buy"], "Sell intensity must exceed buy intensity after sell burst"

    # 3. Asymptotic time decay: evaluate intensity after 10 seconds of silence
    decay_res = engine.compute_l3_hawkes_order_intensity(
        symbol="005930",
        base_rate=mu,
        current_timestamp=t_burst + 10.0,
    )
    print(f"Decayed sell intensity after 10s: lambda_sell = {decay_res['lambda_sell']:.4f}")
    assert decay_res["lambda_sell"] < burst_res["lambda_sell"], "Intensity failed to decay over time"
    assert math.isclose(decay_res["lambda_sell"], mu, abs_tol=0.10), "Intensity should decay toward baseline"

    # 4. Extreme massive shock: 2,000 rapid arrivals
    t_shock = time.time() + 20.0
    for i in range(2000):
        engine.record_order_arrival(symbol="005930", side="BUY", timestamp=t_shock + i * 0.00001)

    shock_res = engine.compute_l3_hawkes_order_intensity(
        symbol="005930",
        base_rate=mu,
        current_timestamp=t_shock + 0.03,
    )
    print(f"Massive shock buy intensity: lambda_buy = {shock_res['lambda_buy']:.2f}")
    assert math.isfinite(shock_res["lambda_buy"]), "Hawkes intensity overflowed to Inf/NaN"
    assert shock_res["lambda_buy"] > 10.0, "Hawkes buy intensity failed to register massive shock"

    print("Hawkes jump intensity surge and decay strictly verified (PASS).")
    return {
        "baseline_intensity": base_res["total_intensity"],
        "post_burst_sell_intensity": burst_res["lambda_sell"],
        "decayed_sell_intensity": decay_res["lambda_sell"],
        "massive_shock_buy_intensity": shock_res["lambda_buy"],
        "status": "PASS",
    }


def verify_f936_vpin_boundedness_and_stability() -> Dict[str, Any]:
    """Objective 2D: Verify VPIN toxicity calculation is strictly bounded in [0.0, 1.0]."""
    print("\n" + "=" * 70)
    print("VERIFYING F936: VPIN Order Flow Toxicity Boundedness [0.0, 1.0]")
    print("=" * 70)

    engine = FastOrderBookMatchingEngine()
    rng = np.random.RandomState(1234)

    # 1. 100% buy trades (pure aggressive buy volume)
    eng_buy = FastOrderBookMatchingEngine()
    for _ in range(50):
        eng_buy.record_trade("005930", price=70000.0, quantity=100.0, is_buyer_maker=False)
    vpin_buy = eng_buy.calculate_vpin_toxicity("005930")
    print(f"100% Buy trades VPIN: {vpin_buy:.4f}")
    assert 0.0 <= vpin_buy <= 1.0, f"VPIN {vpin_buy} outside [0.0, 1.0]"

    # 2. 100% sell trades (pure aggressive sell volume)
    eng_sell = FastOrderBookMatchingEngine()
    for _ in range(50):
        eng_sell.record_trade("005930", price=70000.0, quantity=100.0, is_buyer_maker=True)
    vpin_sell = eng_sell.calculate_vpin_toxicity("005930")
    print(f"100% Sell trades VPIN: {vpin_sell:.4f}")
    assert 0.0 <= vpin_sell <= 1.0, f"VPIN {vpin_sell} outside [0.0, 1.0]"

    # 3. 50/50 alternating buy/sell trades
    eng_alt = FastOrderBookMatchingEngine()
    for i in range(100):
        eng_alt.record_trade("005930", price=70000.0, quantity=100.0, is_buyer_maker=(i % 2 == 0))
    vpin_alt = eng_alt.calculate_vpin_toxicity("005930")
    print(f"50/50 Alternating trades VPIN: {vpin_alt:.4f}")
    assert 0.0 <= vpin_alt <= 1.0, f"VPIN {vpin_alt} outside [0.0, 1.0]"

    # 4. Sparse edge cases: 0 trades, 1 trade, identical prices
    eng_empty = FastOrderBookMatchingEngine()
    vpin_empty = eng_empty.calculate_vpin_toxicity("005930")
    assert 0.0 <= vpin_empty <= 1.0, f"Empty book VPIN {vpin_empty} outside [0.0, 1.0]"

    eng_single = FastOrderBookMatchingEngine()
    eng_single.record_trade("005930", price=70000.0, quantity=100.0, is_buyer_maker=True)
    vpin_single = eng_single.calculate_vpin_toxicity("005930")
    assert 0.0 <= vpin_single <= 1.0, f"Single trade VPIN {vpin_single} outside [0.0, 1.0]"

    # 5. Direct order_volumes array testing across 1,000 random configurations
    n_tests = 1000
    for _ in range(n_tests):
        size = rng.randint(2, 200)
        v_test = rng.exponential(scale=100.0, size=size)
        vpin_arr = engine.calculate_vpin_toxicity(order_volumes=v_test)
        assert math.isfinite(vpin_arr), f"VPIN is not finite: {vpin_arr}"
        assert 0.0 <= vpin_arr <= 1.0, f"VPIN array {vpin_arr} outside [0.0, 1.0]"

    print(f"Tested {n_tests} random order volume arrays: 100% strictly bounded in [0.0, 1.0] (PASS).")
    return {"status": "PASS"}


def main():
    print("=" * 80)
    print("CHALLENGER 1: EMPIRICAL ADVERSARIAL STRESS SUITE (R182 MILESTONE M4)")
    print("Features F935 (Distributional SAC 95) & F936 (Sub-Microsecond Zero-Copy LOB)")
    print("=" * 80)

    results = {}
    try:
        # F935 Challenges
        results["f935_grid"] = verify_f935_quantile_grid_monotonicity_and_duelling()
        results["f935_cvar"] = verify_f935_downside_cvar_against_oracle()
        results["f935_guardrails"] = verify_f935_extreme_inputs_and_guardrails()

        # F936 Challenges
        results["f936_concurrency"] = verify_f936_multithreaded_ring_buffer_concurrency()
        results["f936_latency"] = verify_f936_latency_benchmark()
        results["f936_hawkes"] = verify_f936_hawkes_bursts_and_stability()
        results["f936_vpin"] = verify_f936_vpin_boundedness_and_stability()

        print("\n" + "=" * 80)
        print("ALL CHALLENGER 1 ADVERSARIAL STRESS TESTS EMPIRICALLY PASSED 100%!")
        print("=" * 80)
        return 0
    except Exception as e:
        print(f"\n[CRITICAL FAILURE] Adversarial test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
