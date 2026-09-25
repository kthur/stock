# DISPATCH

## 2026-09-25T15:20:00Z

Task: Phase 67 Quantitative Alpha Enhancement - Microstructure & OMS Specialist Worker (Features F309.1 & F309.2)
Target Files:
- `trading_system/src/core/fast_lob_engine.py`
- `trading_system/src/execution/smart_order_router.py`
- `trading_system/src/execution/oms_engine.py`

Key Requirements:
1. `fast_lob_engine.py`:
   - KNK-46 dark-energy DAHA:
     * w = -48/3
     * k_daha = 0.38
     * k_monster = 0.37
     * daha_46_factor = 7.10
     * c_monster = 2.9802322387695312e-15 (2^-48)
     * Repulsive acceleration formula: `-24.0 * c_monster * (r ** 48) * daha_46_factor` delegating to KNK-45.
     * Full alias trees matching established KNK patterns.
2. `smart_order_router.py`:
   - Advance lit maker floor from `1e-38` to `1e-39` under `gamma_toxic > 0.80`.
   - Update 39-decimal precision rounding.
   - Add `is_phase67` flag and preserve backward compatibility for earlier phases.
3. `oms_engine.py`:
   - Advance tick shading threshold from `h > 0.0000005` to `h > 0.0000004` and shading coefficient from 19 nines to 20 nines (`0.99999999999999999999`).
   - Apply under `version >= 67` in both `ExecutionOMSEngine` and `AlmgrenChrissScheduler`.
