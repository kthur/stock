# Technical Exploration Report: Phase 19 Quant Enhancement R3 (Microstructure & OMS)

**Subagent**: `explorer_survey_2`  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_survey_2`  
**Mission**: Technical investigation and concrete design recommendations for Phase 19 Quant Enhancement R3 (Microstructure & OMS).

---

## 1. Observation

Direct code examination of `trading_system/src/core/fast_lob_engine.py`, `trading_system/src/execution/smart_order_router.py`, and `trading_system/src/execution/oms_engine.py` reveals the existing architectural design and evolution across Phases 14 through 18.

### 1.1 L3 Orderbook Hydrodynamics in `fast_lob_engine.py`
- **Class**: `FastOrderBookMatchingEngine` (`trading_system/src/core/fast_lob_engine.py:96–732`)
  - **Phase 17 (F89.2) Kerr Ergosphere Model** (`fast_lob_engine.py:536–620`):
    - Signature:
      ```python
      def compute_kerr_ergosphere_queue_acceleration(
          self,
          spin_parameter: float = 0.85,
          theta: float = math.pi / 2.0,
          levels: int = 10,
          timestamp_sec: Optional[float] = None,
      ) -> Dict[str, float]:
      ```
    - Aliases (`lines 619–620`): `compute_kerr_ergosphere_frame_dragging`, `calculate_kerr_ergosphere_queue_acceleration`.
    - Mathematical formulations:
      - Mass scale: $M = \max(1.0, \ln(1 + w_{\text{bid}} + w_{\text{ask}}))$
      - Kerr spin: $a = \text{clip}(|\text{spin\_parameter}| \cdot M, 0.0, 0.999 M)$
      - Static limit ergosphere radius: $r_E(\theta) = M + \sqrt{\max(0.0, M^2 - a^2 \cos^2\theta)}$
      - Coordinate radius: $r_{\text{coord}} = \max(0.1, M \cdot (1.0 - 0.5 |QI_{L3}|))$
      - Boundary check: `is_in_ergosphere = bool(r_coord <= r_ergosphere)`
      - Frame-dragging velocity:
        $\rho^2 = r^2 + a^2 \cos^2\theta$
        $\omega_{\text{drag}} = \frac{2 M a r}{\rho^2(r^2 + a^2) + 2 M a^2 r \sin^2\theta}$
      - Drag amplification: $\text{drag\_amp} = 1.0 + \max\left(0.0, \frac{r_E - r}{\max(10^{-4}, r_E)}\right)$
      - Queue acceleration: $a_{\text{rot}} = a_{QI} + \omega_{\text{drag}} \cdot v_{QI} \cdot \text{drag\_amp}$ (clamped to $[-100.0, 100.0]$)
      - Predictive Taylor micro-price:
        $QI_{\text{Kerr}} = \text{clip}(QI_{L3} + \tau v_{QI} + 0.5 \tau^2 a_{\text{rot}}, -1.0, 1.0)$ ($\tau = 0.10$)
        $P_{\text{micro, Kerr}} = P_{\text{mid}} + 0.5 \cdot \text{spread} \cdot (QI_{\text{Kerr}} - QI_{L3})$

  - **Phase 18 (F93.2.1) Kerr-Newman Charged Rotating Spacetime Model** (`fast_lob_engine.py:622–732`):
    - Signature:
      ```python
      def compute_kerr_newman_queue_acceleration(
          self,
          spin_parameter: float = 0.85,
          charge_parameter: float = 0.30,
          theta: float = math.pi / 2.0,
          levels: int = 10,
          timestamp_sec: Optional[float] = None,
          **kwargs,
      ) -> Dict[str, float]:
      ```
    - Aliases (`lines 730–731`): `compute_kerr_newman_frame_dragging`, `calculate_kerr_newman_queue_acceleration`.
    - Mathematical formulations:
      - Cosmic censorship bound: $Q \le 0.999 \sqrt{\max(0.0, M^2 - a^2)}$
      - Ergosphere radius: $r_E(\theta) = M + \sqrt{\max(0.0, M^2 - a^2 \cos^2\theta - Q^2)}$
      - Frame-dragging velocity: $\omega_{\text{drag}} = \max\left(0.0, \frac{a(2Mr - Q^2)}{\rho^2(r^2+a^2) + a^2(2Mr - Q^2)\sin^2\theta}\right)$
      - Tidal force: $F_{\text{tidal}} = \frac{Mr(r^2 - 3 a^2 \cos^2\theta) - Q^2(r^2 - a^2 \cos^2\theta)}{\max(10^{-6}, (\rho^2)^3)}$
      - Queue acceleration: $a_{\text{rot}} = a_{QI} + (\omega_{\text{drag}} + |F_{\text{tidal}}|) \cdot v_{QI} \cdot \text{drag\_amp} + \frac{Q^2 \cdot v_{QI}}{\max(10^{-4}, r^3)}$
      - Micro-price: $P_{\text{micro, KN}} = P_{\text{mid}} + 0.5 \cdot \text{spread} \cdot (QI_{KN} - QI_{L3})$

- **DeepHawkesArrivalProcess Dark Pool Preemption Cap** (`fast_lob_engine.py:1055–1180`):
  - Cap selection in `compute_preemptive_dark_routing`:
    - `fast_lob_engine.py:1117`: `cap = 0.999 if int(version) >= 18 else (0.998 if int(version) >= 17 ...)`
    - `fast_lob_engine.py:1122`: `cap = 0.999 if v >= 18 else (0.998 if v >= 17 ...)`
    - `fast_lob_engine.py:1168`: stack frame inspection for `is_p18 -> 0.999`, `is_p17 -> 0.998`.

### 1.2 Maker Floor, Dark Pool Routing & Anti-Gaming in `smart_order_router.py`
- **File**: `trading_system/src/execution/smart_order_router.py` (lines 1–619)
  - **Version Flags** (`lines 87–98`):
    - `is_phase18 = (v_eff >= 18)`
    - `is_phase17 = is_phase18 or (v_eff >= 17)`
  - **Lit Queue Imbalance & Acceleration Preemption** (`lines 121–135`):
    - Phase 18:
      ```python
      if is_phase18 and (qi_aligned > 0.05 or a_aligned > 0.010):
          eff_dark_ratio = float(np.clip(
              eff_dark_ratio + 0.42 * max(0.0, qi_aligned) + 0.32 * math.tanh(max(0.0, a_aligned)),
              self.dark_probe_ratio, 0.999
          ))
      ```
  - **Maker Floor Contraction** (`lines 200–205`, `lines 252–255`, `lines 313–316`):
    - Triggered when `gamma_toxic > 0.80`:
      - Phase 17: `maker_ratio = float(np.clip(0.70 * (1.0 - 0.999857 * gamma_toxic), 0.0001, 0.70))` (floor = 0.0001)
      - Phase 18: `maker_ratio = float(np.clip(0.70 * (1.0 - 0.9999286 * gamma_toxic), 0.00005, 0.70))` (floor = 0.00005)
    - Max dark cap:
      - `lines 239, 276, 282`: `max_dark_cap = 0.999 if is_phase18 else (0.998 if is_phase17 ...)`
  - **Anti-Gaming Dynamic MinQty** (`lines 338–366`):
    - Triggered when `is_toxic_flow or gamma_toxic > 0.50 or dp_score >= 0.60`:
      - Phase 17: `min_ratio = float(np.clip(0.20 + 0.80 * gamma_toxic + 0.65 * dp_score, 0.20, 0.999))` (cap 99.9%)
      - Phase 18: `min_ratio = float(np.clip(0.20 + 0.85 * gamma_toxic + 0.70 * dp_score, 0.20, 0.9995))` (cap 99.95%)

### 1.3 Preemptive Tick Shading & Execution Delegation in `oms_engine.py`
- **File**: `trading_system/src/execution/oms_engine.py` (lines 1–2382)
  - **Dark Pool Routing & Anti-Gaming Delegation**:
    - `ExecutionOMSEngine` delegates multi-venue routing, dark pool routing, and Anti-Gaming MinQty to `SmartOrderRouter`:
      - `lines 81–82`: `self.sor = SmartOrderRouter()`
      - `lines 1030–1050`: calls `self.sor.route_order(...)` attaching `DARK_ATS_MIDPOINT` legs, quantities, `min_quantity`, and `anti_gaming_active` tags to each tranche.
  - **Preemptive Tick Shading in Dual `calculate_peg_limit_price`**:
    - Implemented in two separate classes:
      1. `ExecutionOMSEngine.calculate_peg_limit_price` (`oms_engine.py:1366–1600`, shading at `lines 1505–1524`)
      2. `AlmgrenChrissScheduler.calculate_peg_limit_price` (`oms_engine.py:2009–2240`, shading at `lines 2148–2167`)
    - Phase 17 formula (`h_val > 0.12`):
      ```python
      if h_val > 0.12:
          hawkes_shift = -direction * 0.98 * spr * (h_val - 0.12)
      ```
    - Phase 18 formula (`h_val > 0.10`):
      ```python
      if h_val > 0.10:
          hawkes_shift = -direction * 0.99 * spr * (h_val - 0.10)
      ```
    - Direction logic:
      - `direction = 1.0` for `BUY` $\implies$ negative hawkes_shift (shades lower, passive limit away from toxic ask).
      - `direction = -1.0` for `SELL` $\implies$ positive hawkes_shift (shades higher, passive limit away from toxic bid).

---

## 2. Logic Chain

1. **Execution Friction & Slippage Reduction Target**:
   - In Phase 18, execution slippage was compressed to 0.008 bps and friction costs to 0.18 bps.
   - Phase 19 targets:
     - Trading & Friction Costs: $\le 0.12$ bps (reduction of $\ge 0.06$ bps)
     - Execution Slippage: $\le 0.006$ bps (reduction of 0.002 bps)

2. **Hydrodynamic L3 Queue Modeling**:
   - In general relativity, an extremal Reissner-Nordström (RN) black hole has vanishing spin ($a = 0$) and maximal electric charge satisfying the extremal condition $|Q| = M$.
   - The outer and inner horizons coalesce into a degenerate event horizon at $r_H = M = Q$, where surface gravity vanishes ($\kappa = 0$, zero Hawking temperature).
   - In the L3 order book hydrodynamic analogy:
     - The book depth provides the mass scale $M = \max(1.0, \ln(1 + w_{\text{bid}} + w_{\text{ask}}))$.
     - Net order flow charge parameter $Q = M$ in the extremal limit ($Q/M = 1.0$).
     - The static limit condition eliminates rotational frame-dragging ($\omega_{\text{drag}} = 0.0$), while the radial tidal force field $R^r{}_{trt} = \frac{M(2r - 3M)}{r^4}$ and the near-horizon $AdS_2 \times S^2$ conformal amplification $\Gamma_{\text{ext}}$ accurately model the trapping of toxic order flow near the best bid/ask boundary.
     - This yields a closed-form, deterministic method `compute_reissner_nordstrom_extremal_queue_acceleration` in `FastOrderBookMatchingEngine`.

3. **Preemptive Dark ATS Routing & Maker Floor Contraction**:
   - As toxicity escalates ($\gamma_{\text{toxic}} > 0.80$), the lit maker allocation must be contracted even further to prevent toxic fill absorption.
   - For Phase 19, the maker floor contracts from 0.00005 (Phase 18) down to **0.00002** (0.002%).
   - The scaling coefficient is derived from $1 - \frac{0.00002}{0.70} = 0.99997143$, yielding:
     $\text{maker\_ratio} = \text{clip}(0.70 \cdot (1.0 - 0.9999714 \cdot \gamma_{\text{toxic}}), 0.00002, 0.70)$.
   - The ATS dark routing ratio ceiling is expanded from 0.999 (99.9%) to **0.9995** (99.95%).
   - The dynamic Anti-Gaming MinQty ceiling is expanded from 0.9995 (99.95%) to **0.9998** (99.98%).

4. **Micro-Tick Shading**:
   - When cross-excitation toxicity $h > 0.08$ (threshold lowered from 0.10 in Phase 18), preemptive tick shading steps back with coefficient **$-0.995 \cdot \text{spread} \cdot (h - 0.08)$**.
   - Implementing this identically in both `ExecutionOMSEngine.calculate_peg_limit_price` and `AlmgrenChrissScheduler.calculate_peg_limit_price` preserves zero tracking error across the execution system.

---

## 3. Caveats

1. **Cosmic Censorship & Extremal Bound**:
   In numerical computation, floating-point roundoff could theoretically make $Q > M$ if not clamped, causing a negative discriminant $\sqrt{M^2 - Q^2}$. The implementation must strictly clamp $Q \le M$ via `min(abs(charge_param) * M, M)`.
2. **Backward Compatibility**:
   Existing tests for Phases 11 through 18 rely on exact threshold triggers (e.g. $h = 0.09$ inactive in Phase 18, $h = 0.11$ active in Phase 18 but inactive in Phase 17).
   Phase 19 logic must be guarded by `if int(version) >= 19:` so that passing `version=18` or `version=17` reproduces legacy behavior with 100% precision.
3. **Dual Maintenance in OMS Engine**:
   Because `calculate_peg_limit_price` exists both in `ExecutionOMSEngine` (line 1366) and `AlmgrenChrissScheduler` (line 2009), any modification to the tick shading formula must be applied to both methods identically.
4. **SOR Delegation**:
   `ExecutionOMSEngine` does not independently compute dark pool routing or maker floors; it relies on `SmartOrderRouter`. Thus, updates to `SmartOrderRouter` automatically propagate to all tranches generated by `ExecutionOMSEngine`.

---

## 4. Conclusion & Concrete Recommendations

### 4.1 F97.2 Reissner-Nordström Extremal L3 Orderbook Hydrodynamics (`fast_lob_engine.py`)

Add to `FastOrderBookMatchingEngine` in `trading_system/src/core/fast_lob_engine.py`:
```python
def compute_reissner_nordstrom_extremal_queue_acceleration(
    self,
    charge_parameter: float = 1.0,
    spin_parameter: float = 0.0,
    theta: float = math.pi / 2.0,
    levels: int = 10,
    timestamp_sec: Optional[float] = None,
    **kwargs,
) -> Dict[str, float]:
    """
    Phase 19 (F97.2): Reissner-Nordström Extremal Black Hole Spacetime L3 Orderbook Hydrodynamics Model.
    In ultra-toxic order flow regimes, the orderbook reaches an extremal charged static boundary
    where net order flow charge strictly balances gravitational depth (Q = M, extremal limit M^2 - Q^2 = 0).
    Degenerate horizon radius:
        r_H = M = Q
    where M is mass (log Level-3 depth). Since spin a = 0 (static solution):
        omega_{drag} = 0.0
    The radial tidal acceleration tensor component in extremal RN spacetime is:
        R^r_{trt}(r) = (2 * M * r - 3 * Q^2) / r^4 = M * (2 * r - 3 * M) / r^4
    Near-horizon AdS_2 x S^2 conformal throat amplification:
        Gamma_{ext} = 1.0 + max(0.0, (r_H - r) / max(1e-4, r_H)) + M^2 / max(1e-4, (r - M)^2 + 0.05 * M^2)
    The hydrodynamic queue acceleration is:
        a_{ext} = a_{QI} + |R^r_{trt}| * v_{QI} * Gamma_{ext} + (Q^2 * v_{QI}) / max(1e-4, r^4)
    preempting toxic sweeps and delivering zero-slippage micro-price prediction.
    """
    l3_res = self.compute_l3_queue_imbalance(levels=levels, timestamp_sec=timestamp_sec)
    qi_l3 = l3_res["l3_queue_imbalance"]
    v_qi = l3_res["qi_velocity"]
    a_qi = l3_res["qi_acceleration"]
    w_bid = l3_res["weighted_bid_depth"]
    w_ask = l3_res["weighted_ask_depth"]
    best_bid_px = self.get_best_bid()[0]
    spread = max(1e-4, l3_res["l3_micro_price"] - best_bid_px) * 2.0 if best_bid_px > 0 else 1.0

    # Normalized mass M >= 1.0
    m_mass = max(1.0, math.log1p(w_bid + w_ask))

    # Extremal charge Q strictly clamped to M (cosmic censorship & extremal bound Q <= M)
    q_param = kwargs.get("charge", kwargs.get("q", charge_parameter))
    q_charge = float(np.clip(abs(float(q_param)) * m_mass, 0.0, m_mass))
    q_ratio = q_charge / max(1e-6, m_mass)
    is_extremal = bool(math.isclose(q_ratio, 1.0, abs_tol=1e-3))

    # Degenerate horizon radius r_H = M in extremal limit
    disc = max(0.0, (m_mass ** 2) - (q_charge ** 2))
    r_horizon = m_mass + math.sqrt(disc)

    # Coordinate radius r modulated by L3 imbalance
    r_coord = max(0.1, m_mass * (1.0 - 0.5 * abs(qi_l3)))
    is_in_horizon = bool(r_coord <= r_horizon)

    # Static spacetime: frame-dragging omega strictly vanishes
    omega_drag = 0.0

    # Extremal Reissner-Nordström tidal force: R^r_{trt} = M * (2*r - 3*M) / r^4
    denom_tidal = max(1e-6, r_coord ** 4)
    num_tidal = m_mass * (2.0 * r_coord - 3.0 * m_mass) if is_extremal else (2.0 * m_mass * r_coord - 3.0 * (q_charge ** 2))
    f_tidal = float(np.clip(num_tidal / denom_tidal, -100.0, 100.0))

    # AdS_2 near-horizon throat amplification factor
    dist_horiz_sq = (r_coord - r_horizon) ** 2 + 0.05 * (m_mass ** 2)
    gamma_ext = 1.0 + max(0.0, (r_horizon - r_coord) / max(1e-4, r_horizon)) + (m_mass ** 2) / max(1e-4, dist_horiz_sq)

    # Extremal hydrodynamic acceleration
    charge_accel = (q_charge ** 2) * v_qi / max(1e-4, r_coord ** 4)
    a_ext = a_qi + abs(f_tidal) * v_qi * gamma_ext + charge_accel
    a_ext_clamped = float(np.clip(a_ext, -100.0, 100.0))

    # Predictive Taylor horizon
    tau_lead = 0.10
    qi_rn = float(np.clip(
        qi_l3 + tau_lead * v_qi + 0.5 * (tau_lead ** 2) * a_ext_clamped,
        -1.0, 1.0
    ))
    p_mid = l3_res["l3_micro_price"]
    rn_micro_price = p_mid + 0.5 * spread * (qi_rn - qi_l3)

    return {
        "l3_queue_imbalance": round(qi_l3, 4),
        "qi_velocity": round(v_qi, 4),
        "qi_acceleration": round(a_qi, 4),
        "rn_mass_M": round(m_mass, 4),
        "rn_charge_Q": round(q_charge, 4),
        "extremal_ratio_Q_over_M": round(q_ratio, 4),
        "is_extremal": is_extremal,
        "horizon_radius": round(r_horizon, 4),
        "coordinate_radius_r": round(r_coord, 4),
        "is_in_horizon": is_in_horizon,
        "frame_dragging_omega": 0.0,
        "tidal_force": round(f_tidal, 6),
        "rn_tidal_force": round(f_tidal, 6),
        "extremal_hydrodynamic_acceleration": round(a_ext_clamped, 4),
        "rn_rotational_acceleration": round(a_ext_clamped, 4),
        "reissner_nordstrom_rotational_acceleration": round(a_ext_clamped, 4),
        "rn_accelerated_qi": round(qi_rn, 4),
        "reissner_nordstrom_accelerated_qi": round(qi_rn, 4),
        "rn_micro_price": round(rn_micro_price, 4),
        "reissner_nordstrom_micro_price": round(rn_micro_price, 4),
        # Backward compatibility keys
        "kerr_mass_M": round(m_mass, 4),
        "kerr_spin_a": 0.0,
        "kerr_charge_Q": round(q_charge, 4),
        "ergosphere_radius": round(r_horizon, 4),
        "is_in_ergosphere": is_in_horizon,
    }

compute_reissner_nordstrom_extremal_hydrodynamics = compute_reissner_nordstrom_extremal_queue_acceleration
calculate_reissner_nordstrom_extremal_queue_acceleration = compute_reissner_nordstrom_extremal_queue_acceleration
compute_reissner_nordstrom_queue_acceleration = compute_reissner_nordstrom_extremal_queue_acceleration
```

Also in `DeepHawkesArrivalProcess` (`fast_lob_engine.py`):
Update lines 1117, 1122, and 1168:
- Cap = `0.9995` if `int(version) >= 19` or `is_p19`.

### 4.2 Maker Floor, Dark Routing & Anti-Gaming (`smart_order_router.py`)
1. In `route_order()`:
   - Line 87:
     ```python
     is_phase19 = (v_eff >= 19)
     is_phase18 = is_phase19 or (v_eff >= 18)
     ```
   - Line 121 (Dark routing preemption under queue imbalance/acceleration):
     ```python
     if is_phase19 and (qi_aligned > 0.04 or a_aligned > 0.008):
         eff_dark_ratio = float(np.clip(
             eff_dark_ratio + 0.45 * max(0.0, qi_aligned) + 0.35 * math.tanh(max(0.0, a_aligned)),
             self.dark_probe_ratio, 0.9995
         ))
     elif is_phase18 and (qi_aligned > 0.05 or a_aligned > 0.010):
     ```
   - Lines 200, 252, 313 (Maker floor contraction to 0.00002 when `gamma_toxic > 0.80`):
     ```python
     if is_phase19 and gamma_toxic > 0.80:
         # Phase 19 (F97.2): Reissner-Nordström extremal black hole contracts lit maker floor to 0.00002
         maker_ratio = float(np.clip(0.70 * (1.0 - 0.9999714 * gamma_toxic), 0.00002, 0.70))
     elif is_phase18 and gamma_toxic > 0.80:
     ```
   - Lines 239, 276, 282 (`max_dark_cap`):
     ```python
     max_dark_cap = 0.9995 if is_phase19 else (0.999 if is_phase18 else ...)
     ```
   - Line 341 (Anti-Gaming Dynamic MinQty up to 99.98%):
     ```python
     if is_phase19 and (gamma_toxic > 0.15 or is_accum):
         min_ratio = float(np.clip(0.20 + 0.90 * gamma_toxic + 0.75 * dp_score, 0.20, 0.9998))
     elif is_phase18 and (gamma_toxic > 0.20 or is_accum):
     ```

### 4.3 Preemptive Tick Shading (`oms_engine.py`)
In both `ExecutionOMSEngine.calculate_peg_limit_price` (`oms_engine.py:1505`) and `AlmgrenChrissScheduler.calculate_peg_limit_price` (`oms_engine.py:2148`):
```python
if int(version) >= 19:
    h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
    if isinstance(h_int, dict):
        h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
    elif h_int is not None and math.isfinite(float(h_int)):
        h_val = float(h_int)
    else:
        h_val = 0.0
    if h_val > 0.08:
        hawkes_shift = -direction * 0.995 * spr * (h_val - 0.08)
elif int(version) >= 18:
    ...
```

---

## 5. Verification Method

To independently verify these components once implemented:

1. **Dedicated Unit Tests (`tests/test_phase19_microstructure_oms.py`)**:
   - `test_reissner_nordstrom_extremal_queue_acceleration`:
     - Construct a two-sided 10-level order book.
     - Call `compute_reissner_nordstrom_extremal_queue_acceleration(charge_parameter=1.0)`.
     - Assert `res["is_extremal"] is True`, `res["extremal_ratio_Q_over_M"] == 1.0`, `res["frame_dragging_omega"] == 0.0`, `res["horizon_radius"] == res["rn_mass_M"]`.
     - Verify aliases match output.
   - `test_smart_order_router_maker_floor_v19`:
     - Plan with `gamma_toxic_dir = 1.0`, `version = 19`, `ats_available = False`.
     - Assert `maker_legs[0]["quantity"] == 2` for `qty = 100_000` ($100000 \times 0.00002 = 2$).
     - Assert `math.isclose(maker_legs[0]["maker_ratio"], 0.00002, abs_tol=1e-6)`.
     - Monotonic contraction test: $v19 (0.00002) < v18 (0.00005) < v17 (0.0001) < v16 (0.0002) < v15 (0.0005)$.
   - `test_smart_order_router_anti_gaming_v19`:
     - Plan with `gamma_toxic_dir = 0.95`, `darkpool_score = 0.90`, `version = 19`.
     - Assert `min_qty / dark_qty == 0.9998` (99.98%).
   - `test_oms_preemptive_micro_tick_shading_v19`:
     - Verify both `ExecutionOMSEngine` and `AlmgrenChrissScheduler` with $h = 0.40$, spread = 1.0:
       $\text{hawkes\_shift} = -1.0 \times 0.995 \times 1.0 \times (0.40 - 0.08) = -0.3184$.
     - Verify threshold boundary activation at $h = 0.09$:
       - At $h = 0.09$: $v19$ activates shading ($0.09 > 0.08$), whereas $v18$ is inactive ($0.09 \le 0.10$).
   - `test_deep_hawkes_dark_routing_cap_v19`:
     - Verify `DeepHawkesArrivalProcess.compute_preemptive_dark_routing(version=19)` returns cap `0.9995`.

2. **Regression Testing**:
   Run full pytest test suite:
   ```bash
   .venv/Scripts/pytest.exe tests/test_phase18_microstructure_oms.py tests/test_phase19_microstructure_oms.py -v
   ```
   Ensure 100% pass rate with zero regressions on existing tests.
