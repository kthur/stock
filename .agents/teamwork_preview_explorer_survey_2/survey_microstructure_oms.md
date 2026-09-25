# Survey Report: Phase 66 Microstructure & OMS Architecture

**Analysis Target**: Current Phase 66 implementation for Microstructure & OMS components in preparation for Phase 67 Quantitative Alpha Enhancement (F309.1 & F309.2).  
**Investigated Files**:
1. `trading_system/src/core/fast_lob_engine.py`
2. `trading_system/src/execution/smart_order_router.py`
3. `trading_system/src/execution/oms_engine.py`
4. Reference Test Suites: `tests/test_phase66_oms.py`, `tests/test_phase66_adversarial_oms_benchmark.py`

---

## 1. Fast LOB Engine (`trading_system/src/core/fast_lob_engine.py`)

### 1.1 Architectural Overview & Class Hierarchy
- **Primary Classes**:
  - `FastOrderBookMatchingEngine` (Line 96): High-performance limit order book (LOB) matching engine with L3 microstructure modeling and spacetime hydrodynamic queue acceleration.
  - `FastLOBEngine` (Line 20195): Direct alias assignment `FastLOBEngine = FastOrderBookMatchingEngine`. All methods and properties on `FastOrderBookMatchingEngine` are accessible via `FastLOBEngine`.
  - `DeepHawkesArrivalProcess` (Line 19519): Inherits from `MultivariateHawkesIntensity`. Implements venue-specific Hawkes arrival intensities (LIT, ATS, DARK) and preemptive dark routing allocation under deep toxicity.

### 1.2 Kerr-Newman-Kiselev 45-Dark-Energy DAHA (KNK-45) Implementation
- **Location**: `FastOrderBookMatchingEngine.compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration` (Lines 1413–1458).
- **Physical / Mathematical Parameters (Phase 66)**:
  - Equation of state parameter: $w = -\frac{47}{3} \approx -15.66667$ (`w: float = -47.0 / 3.0`)
  - DAHA coupling constant: $k_{\text{daha}} = 0.37$ (`k_daha: float = 0.37`)
  - Monster Moonshine coupling: $k_{\text{monster}} = 0.36$ (`k_monster: float = 0.36`)
  - DAHA amplification factor: $\text{daha\_45\_factor} = 6.85$ (`daha_45_factor: float = 6.85`)
  - Monster energy density constant: $c_{\text{monster}} = 2^{-47} = 5.9604644775390625 \times 10^{-15}$ (`c_monster: float = 5.9604644775390625e-15`)
  - Effective radial coordinate: $r_{\text{eff}} = \max(10^{-10}, |q_i|)$ where $q_i$ is L3 queue imbalance.
  - Repulsive acceleration component:
    $$\text{dark\_45\_accel} = -24.0 \cdot c_{45} \cdot (r_{\text{eff}}^{47}) \cdot \text{daha\_45\_factor}$$
    Clamped to $[-10^6, 10^6]$.
  - Metric warping expansion order: $+ c \cdot (r^{49}) \cdot \text{daha\_45\_factor}$.

### 1.3 Delegation Pattern & Return Dictionary
- **Delegation**:
  ```python
  base_res = self.compute_kerr_newman_kiselev_44_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
      charge_parameter=charge_parameter, spin_parameter=spin_parameter,
      c_monster=c_monster, w=w, k_daha=k_daha, k_monster=k_monster,
      daha_44_factor=daha_45_factor, theta=theta, levels=levels,
      timestamp_sec=timestamp_sec, **kwargs
  )
  ```
- **Return Keys Populated**:
  - `knk_45_dark_energy_correction`: `round(dark_45_accel, 8)`
  - `knk_45_dark_energy_daha_acceleration`: `round(corrected_accel, 6)`
  - `phase66_knk_acceleration`: `round(corrected_accel, 6)`
  - `daha_45_factor`: `6.85`
  - `k_daha_45`: `0.37`
  - `k_monster_45`: `0.36`
  - `c_monster_45`: `5.9604644775390625e-15`
  - `w_dark_energy_45`: `-47.0 / 3.0`
  - Inherited from `base_res`: `queue_acceleration`, `a_knk`, `predicted_micro_price`, `knk_pcqtgbddddhkmaeetuv_hydrodynamic_acceleration`, etc.

### 1.4 Complete Alias Tree (16 Aliases)
Defined at lines 1460–1475:
```python
compute_phase66_lob_acceleration = compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration
phase66_lob_spacetime_hydrodynamics = compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration
compute_knk_45_dark_energy_acceleration = compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration
compute_kerr_newman_kiselev_45_dark_energy_acceleration = compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration
phase66_daha_l3_acceleration = compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration
knk_45_dark_energy_daha_l3 = compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration
daha_l3_phase66_acceleration = compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration
phase66_dark_energy_acceleration = compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration
calculate_phase66_knk_acceleration = compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration
compute_knk_phase66_acceleration = compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration
daha_phase66_acceleration = compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration
phase66_spacetime_hydrodynamics = compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration
phase66_queue_acceleration = compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration
l3_phase66_acceleration = compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration
phase66_knk_acceleration = compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration
compute_phase66_knk_daha_queue_acceleration = compute_kerr_newman_kiselev_45_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration
```

### 1.5 Deep Hawkes Preemptive Dark Routing Cap
- **Location**: `DeepHawkesArrivalProcess.compute_preemptive_dark_routing` (Lines 19561–19740).
- **Cap Evaluation Logic**:
  - Line 19594 (under `elif version is not None:`): Currently caps at `0.99999999999999999995` (`v_int >= 64`).
  - Line 19706 (under `elif getattr(self, "version", None) is not None:`): Sets `cap = 0.999999999999999999995` for `v >= 65`.
  - For Phase 67: Both branches need extension to support Phase 67 (`v >= 67`).

---

## 2. Smart Order Router (`trading_system/src/execution/smart_order_router.py`)

### 2.1 Class Initialization & Version Flags
- **Location**: `SmartOrderRouter.__init__` (Lines 40–80).
- **Flag Definition**:
  ```python
  self.version = int(version)
  self.is_phase66 = (self.version >= 66)
  self.is_phase65 = self.is_phase66 or (self.version >= 65)
  self.is_phase64 = self.is_phase65 or (self.version >= 64)
  ...
  ```
- **Local Resolution in `route_order`**:
  ```python
  v_eff = version if version is not None else int(order_plan.get("version", 6))
  is_phase66 = (v_eff >= 66)
  is_phase65 = is_phase66 or (v_eff >= 65)
  ...
  ```
  (Lines 243–252).

### 2.2 Lit Maker Floor ($10^{-38}$)
- **Locations**:
  1. **Direct `gamma_toxic_dir` Path** (Lines 587–589):
     ```python
     if is_phase66 and gamma_toxic > 0.80:
         # F304.2: Kerr-Newman-Kiselev 45-Dark-Energy DAHA L3 preemption contracts lit maker floor to 1e-38
         maker_ratio = float(np.clip(round(0.70 * (1.0 - 0.99999999999999999999999999999999999986 * gamma_toxic), 52), 1e-38, 0.70))
     ```
  2. **Directional Hawkes `h_buy`/`h_sell` Path** (Lines 783–785):
     ```python
     if is_phase66 and gamma_toxic > 0.80:
         # F304.2: Kerr-Newman-Kiselev 45-Dark-Energy DAHA L3 preemption contracts lit maker floor to 1e-38
         maker_ratio = float(np.clip(round(0.70 * (1.0 - 0.99999999999999999999999999999999999986 * gamma_toxic), 52), 1e-38, 0.70))
     ```
- **Numerical Behavior**: Under worst-case toxicity ($\gamma_{\text{toxic}} = 1.0$), maker ratio contracts exactly to $10^{-38}$ without zero-underflow.

### 2.3 Dark ATS Cap & Anti-Gaming MinQty
- **Dark ATS Cap (`_resolve_max_dark_cap`)**:
  - Lines 81–89:
    ```python
    def _resolve_max_dark_cap(self=None, v_eff: int = 6) -> float:
        ...
        if v_eff >= 65:
            return 0.999999999999999999995  # 21 decimals (19 nines + 95)
        elif v_eff >= 64:
            return 0.99999999999999999995
    ```
- **Anti-Gaming MinQty**:
  - Lines 1068–1071:
    ```python
    if is_phase66 and (gamma_toxic > 0.000000000000005 or is_accum):
        pass  # Phase 66 F304.2 threshold
    elif is_phase65 and (gamma_toxic > 0.00000000000001 or is_accum):
        min_ratio = float(np.clip(0.20 + 0.999999999999999995 * gamma_toxic + 0.999999999999995 * dp_score, 0.20, 0.999999999999999999995))
    ```
  - *Observation*: Notice line 1069 had a `pass` placeholder in Phase 66 (similar to line 332 in queue imbalance preemption). In Phase 67, this branch should be concretely populated rather than passed over.

### 2.4 Precision Formatting (38 Decimals)
- **Maker Ratio & Min Ratio Rounding**:
  - Line 1265 (Maker leg dictionary):
    `"maker_ratio": round(float(maker_ratio), 38 if is_phase66 else (37 if is_phase65 else ...))`
  - Line 1312 (Routing result dictionary `maker_ratio`):
    `"maker_ratio": round(float(maker_ratio), 38 if is_phase66 else (37 if is_phase65 else ...))`
  - Line 1315 (Routing result dictionary `min_ratio`):
    `"min_ratio": round(float(min_ratio), 38 if is_phase66 else (37 if is_phase65 else ...))`

---

## 3. OMS Engine (`trading_system/src/execution/oms_engine.py`)

### 3.1 Preemptive Micro-Tick Shading
- **Mathematical Specification**:
  When Hawkes cross-excitation intensity exceeds threshold $h > 0.0000005$, the peg limit price is shaded downward (for BUY) or upward (for SELL) against toxic queue arrivals:
  $$\Delta_{\text{hawkes}} = -\text{direction} \cdot 0.9999999999999999999 \cdot \text{spr} \cdot (h - 0.0000006)$$
  where coefficient contains 19 nines: `0.9999999999999999999`.
- **Implementation in `ExecutionOMSEngine`**:
  - Lines 1505–1515 in `calculate_peg_limit_price`:
    ```python
    hawkes_shift = 0.0
    if int(version) >= 66:
        # Phase 66 F304.3: Tick shading h>0.0000005 threshold
        h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
        if isinstance(h_int, dict):
            h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
        elif h_int is not None and math.isfinite(float(h_int)):
            h_val = float(h_int)
        else:
            h_val = 0.0
        if h_val > 0.0000005:
            hawkes_shift = -direction * 0.9999999999999999999 * spr * (h_val - 0.0000006)
    ```
- **Implementation in `AlmgrenChrissScheduler`**:
  - Lines 2629–2639 in `calculate_peg_limit_price` (identical logic and coefficient).

### 3.2 Method Signature and Parameter Mapping
- **Method Signature**:
  ```python
  @staticmethod
  def calculate_peg_limit_price(
      target_price: float,
      bid_price: Optional[float] = None,
      ask_price: Optional[float] = None,
      spread: Optional[float] = None,
      alpha_urgency: float = 0.50,
      action: str = "BUY",
      obi: Optional[float] = None,
      kappa: float = 1.5,
      micro_price: Optional[float] = None,
      multi_obi: Optional[Dict[str, float]] = None,
      daily_volatility: Optional[float] = None,
      book_depth_ratio: Optional[float] = None,
      queue_position_ratio: Optional[float] = None,
      l3_micro_price: Optional[float] = None,
      l3_imbalance: Optional[float] = None,
      hawkes_toxicity: Optional[float] = None,
      hawkes_arrival_imbalance: Optional[float] = None,
      queue_imbalance: Optional[float] = None,
      qi_acceleration: Optional[float] = None,
      cross_asset_toxicity: Optional[float] = None,
      version: int = 6,
      qi_jerk: Optional[float] = None,
      deep_ofi: Optional[float] = None,
      hawkes_intensity: Optional[Union[float, Dict[str, float]]] = None,
      **kwargs
  ) -> float:
  ```
- **Call Sites Inside OMS**:
  1. `ExecutionOMSEngine.create_execution_order` (Line 908): Adjusts order target price for `MIDPOINT_PEG` or high OBI/micro-price.
  2. `ExecutionOMSEngine.create_execution_order` (Line 983): Adjusts individual tranche slice limit price.

---

## 4. Phase 66 vs. Phase 67 Progression Mapping

| Parameter / Feature | Phase 66 (v73) Current State | Phase 67 (v74) Required Target | File & Location |
|---|---|---|---|
| **KNK Dark Energy Order** | 45th ($w = -47/3$) | 46th ($w = -48/3 = -16.0$) | `fast_lob_engine.py`: Lines 1413–1458 |
| **KNK $k_{\text{daha}} / k_{\text{monster}}$** | $0.37 / 0.36$ | $0.38 / 0.37$ | `fast_lob_engine.py`: Lines 1419–1420 |
| **KNK DAHA Factor** | 6.85 | 7.10 | `fast_lob_engine.py`: Line 1421 |
| **KNK Monster Density ($c_{\text{monster}}$)** | $5.9604644775390625 \times 10^{-15}$ ($2^{-47}$) | $2.9802322387695312 \times 10^{-15}$ ($2^{-48}$) | `fast_lob_engine.py`: Line 1417 |
| **KNK Acceleration Formula** | $-24.0 \cdot c \cdot r^{47} \cdot 6.85$ | $-24.5$ or $-25.0 \cdot c \cdot r^{49} \cdot 7.10$ | `fast_lob_engine.py`: Line 1445 |
| **KNK Method & Alias Tree** | `compute_kerr_newman_kiselev_45_...` + 16 aliases | `compute_kerr_newman_kiselev_46_...` + 16+ aliases | `fast_lob_engine.py`: Lines 1413–1475 |
| **SOR Lit Maker Floor** | $10^{-38}$ | $10^{-39}$ | `smart_order_router.py`: Lines 589, 785 |
| **SOR Precision Rounding** | 38 decimal places | 39 decimal places | `smart_order_router.py`: Lines 1265, 1312, 1315 |
| **SOR Version Flag** | `self.is_phase66 = (self.version >= 66)` | `self.is_phase67 = (self.version >= 67)` | `smart_order_router.py`: Lines 41, 249 |
| **Tick Shading Threshold** | $h > 0.0000005$ | $h > 0.0000004$ | `oms_engine.py`: Lines 1514, 2638 |
| **Tick Shading Coefficient** | 19 nines (`0.9999999999999999999`) | 20 nines (`0.99999999999999999999`) | `oms_engine.py`: Lines 1515, 2639 |
| **Tick Shading Gating** | `int(version) >= 66` | `int(version) >= 67` | `oms_engine.py`: Lines 1505, 2629 |

---

## 5. Implementation Recommendations for Phase 67 Workers

1. **`fast_lob_engine.py`**:
   - Define `compute_kerr_newman_kiselev_46_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration` immediately above line 1413.
   - Delegate to `compute_kerr_newman_kiselev_45_...` with default parameters:
     `c_monster = 2.9802322387695312e-15`, `w = -48.0 / 3.0`, `k_daha = 0.38`, `k_monster = 0.37`, `daha_46_factor = 7.10`.
   - Apply 46th dark energy correction: `dark_46_accel = -24.5 * c_46 * (r_eff ** 49) * daha_46_factor` (or -25.0).
   - Add all 16 Phase 67 method aliases (`compute_phase67_lob_acceleration`, `phase67_lob_spacetime_hydrodynamics`, etc.).
   - Update `DeepHawkesArrivalProcess.compute_preemptive_dark_routing` to support `v >= 67` and `version >= 67`.

2. **`smart_order_router.py`**:
   - In `__init__`, add `self.is_phase67 = (self.version >= 67)` and chaining:
     `self.is_phase66 = self.is_phase67 or (self.version >= 66)`.
   - In `route_order`, add `is_phase67 = (v_eff >= 67)` and chaining:
     `is_phase66 = is_phase67 or (v_eff >= 66)`.
   - In maker floor clamping (lines 587 and 783), add `if is_phase67 and gamma_toxic > 0.80:` clipping with `1e-39`.
   - In anti-gaming MinQty (line 1068), implement the concrete formula for `is_phase67`:
     `min_ratio = float(np.clip(0.20 + 0.9999999999999999995 * gamma_toxic + 0.9999999999999995 * dp_score, 0.20, 0.9999999999999999999995))` (and fix the `pass` in `is_phase66` if necessary, preserving test expectations).
   - In `_resolve_max_dark_cap`, add `if v_eff >= 67:` or update to 22+ decimals if specified.
   - In decimal rounding (lines 1265, 1312, 1315), prepend `39 if is_phase67 else (38 if is_phase66 else ...)`.

3. **`oms_engine.py`**:
   - In both `ExecutionOMSEngine.calculate_peg_limit_price` (line 1504) and `AlmgrenChrissScheduler.calculate_peg_limit_price` (line 2628):
     Add `if int(version) >= 67:` with threshold $h > 0.0000004$, 20 nines coefficient (`0.99999999999999999999`), and offset `(h_val - 0.0000005)` or `(h_val - 0.0000004)`.
   - Keep existing `elif int(version) >= 66:` block intact for backward compatibility.
