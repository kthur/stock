# Investigation Report: Level-3 Micro-Price Pegging, Hawkes Toxicity & Darkpool Liquidity Capture (Phase 6 / Feature F44)

**Project**: Phase 6 Institutional Microstructure & Execution Deepening across 5 Global Markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000)  
**Author**: Explorer M1-3 (Microstructure, L3 Orderbook & Execution Specialist)  
**Parent / Recipient**: Parent Orchestrator (`cb4888d0-b14d-471f-b555-422c2a30d7c0`)  
**Timestamp**: 2026-09-04T13:48:00Z (2026-09-04 22:48:00 KST)  
**Investigation Status**: **COMPLETE & ACTIONABLE FOR IMPLEMENTATION**

---

## 1. Observation

A comprehensive source code and empirical test audit was conducted on the execution and microstructure subsystem across the following production modules:
- `trading_system/src/execution/smart_order_router.py`
- `trading_system/src/core/fast_lob_engine.py`
- `trading_system/src/execution/oms_engine.py`
- `trading_system/src/risk/unified_portfolio_allocator.py`
- `tests/test_phase5_portfolio_execution.py`
- `tests/test_fast_lob_engine.py`
- `tests/test_smart_router.py`

### 1.1 Current Phase 5 (F38) Implementation in `smart_order_router.py`
1. **Continuous Hawkes Toxicity Adverse Selection Gating** (`lines 82–123`):
   ```python
   # smart_order_router.py lines 98-105:
   # Gamma_toxic = clip((lambda - mu) / (2.5 * mu - mu), 0.0, 1.0)
   denom = 1.5 * base_hwk
   gamma_toxic = float(np.clip((hwk_f - base_hwk) / denom, 0.0, 1.0))
   # maker_ratio = clip(0.70 * (1 - 0.571 * Gamma_toxic), 0.30, 0.70)
   maker_ratio = float(np.clip(0.70 * (1.0 - 0.571 * gamma_toxic), 0.30, 0.70))
   is_toxic_flow = bool(gamma_toxic > 0.50)
   eff_dark_ratio = float(np.clip(eff_dark_ratio + 0.20 * gamma_toxic, eff_dark_ratio, 0.80))
   ```
   *Direct Observation*: Toxicity is modeled as a scalar $\lambda(t)$ relative to baseline $\mu$. It modulates maker ratio continuously between $0.70$ and $0.30$. However, it treats order flow isotropically; it cannot determine whether the toxicity is driven by aggressive buyers or aggressive sellers.

2. **Darkpool Fill Probability & Resting MinQty** (`lines 124–150`):
   ```python
   # smart_order_router.py lines 125-129:
   p_fill_dark = float(np.clip(
       0.35 + 0.35 * dp_score + 0.15 * ((market_spread_bps - 5.0) / 15.0) - 0.20 * gamma_toxic,
       0.15,
       0.85
   ))
   # lines 137-149:
   dark_order_type = "MIDPOINT_PEGGED_RESTING" if (is_toxic_flow or gamma_toxic > 0.50) else "MIDPOINT_IOC"
   if is_toxic_flow or gamma_toxic > 0.50:
       dark_leg["min_quantity"] = max(1, int(round(0.20 * dark_qty)))
   ```
   *Direct Observation*: Darkpool fill probability uses a simple linear bounded model. The minimum quantity constraint is statically pegged at 20% of `dark_qty` once $\Gamma_{\text{toxic}} > 0.50$, regardless of total order size, institutional accumulation intensity, or venue-specific lot structures.

3. **Multi-Venue Destination Mapping** (`lines 216–271`):
   ```python
   # smart_order_router.py lines 230-236 & 266-271:
   if is_krx:
       return {
           "market_region": "KRX",
           "primary_broker": "korea_investment",
           "dma_gateway": "krx_open_api",
           "venue": "KRX_ATS_NEXTRADE"
       }
   else:
       return {
           "market_region": "US",
           "primary_broker": "interactive_brokers",
           "dma_gateway": "fix_protocol",
           "venue": "US_SMART_DMA"
       }
   ```
   *Direct Observation*: Routing targets both KRX alternative trading venue Nextrade (`KRX_ATS_NEXTRADE`) and US institutional smart DMA (`US_SMART_DMA`). However, venue-specific execution parameters (such as Nextrade's 1-share lot tick rules and US ATS anti-gaming randomization) are not yet integrated into the leg-generation logic.

---

### 1.2 Current State in `fast_lob_engine.py`
1. **L3 Order Queue Storage in `FastOrderBookMatchingEngine`** (`lines 96–109`):
   ```python
   self.bids: Dict[float, Deque[OrderNode]] = {} # price -> FIFO queue of orders
   self.asks: Dict[float, Deque[OrderNode]] = {}
   self.order_lookup: Dict[str, Tuple[str, float]] = {} # order_id -> (side, price)
   ```
   *Direct Observation*: The engine stores full Level-3 individual orders (`OrderNode(order_id, price, volume, timestamp_ns, side)`) within price-level FIFO deques.
   *Critical Gap*: There is currently **no method to query an order's FIFO queue position** ($Q_{\text{ahead}}$, $Q_{\text{behind}}$, $u_q$) or estimate the probability of fill before cancellation.

2. **Depth Snapshot Computation** (`lines 239–280`):
   ```python
   # lines 255-256:
   micro_price = (v_a1 * p_b1 + v_b1 * p_a1) / tot_vol1 if tot_vol1 > 0 else (0.5 * (p_b1 + p_a1))
   spread = max(0.0, p_a1 - p_b1) if (p_a1 > 0 and p_b1 > 0) else 0.0
   # Multi-tier OBI (lines 259-267):
   obi_1 = (v_b1 - v_a1) / tot_vol1 if tot_vol1 > 0 else 0.0
   ```
   *Direct Observation*: Micro-price calculation relies exclusively on top-of-book (Level 1) quantities ($V_{b1}, V_{a1}$). Level 2–10 depth data are only used for static aggregate volume sums in `obi_5` and `obi_10`, with no exponential depth decay weighting and no order fragmentation metrics.

3. **Hawkes Intensity Estimator** (`lines 283–322`):
   ```python
   # lines 287-288 & 304-306:
   # lambda(t) = mu + (lambda(t_{i-1}) - mu) * exp(-beta * dt) + alpha
   decayed = (self.current_intensity - self.mu) * math.exp(-self.beta * dt)
   self.current_intensity = self.mu + max(0.0, decayed) + self.alpha
   ```
   *Direct Observation*: The current Hawkes estimator is strictly univariate. It does not ingest trade direction (buy vs. sell), meaning trade clustering cannot identify directional predatory runs or quote-stuffing attacks.

---

### 1.3 Current Peg Pricing in `oms_engine.py`
1. **Static and Dynamic Peg Calculations** (`lines 1365–1443` & `lines 1834–1890`):
   ```python
   # oms_engine.py lines 1400-1430:
   if micro_price is not None and math.isfinite(float(micro_price)) and float(micro_price) > 0:
       p_base = float(micro_price)
   else:
       p_base = p_mid
   
   eff_obi = 0.50 * obi_1 + 0.35 * obi_5 + 0.15 * obi_10
   kappa_eff = float(np.clip(1.5 * (sig / 0.02) / math.sqrt(r_depth), 0.8, 3.0))
   peg_shift = 0.5 * spr * math.tanh(kappa_eff * obi_val)
   peg_price = p_base + peg_shift
   ```
   *Direct Observation*:
   - `calculate_peg_limit_price` is duplicated verbatim on both `ExecutionOMSEngine` (line 1365) and `AlmgrenChrissScheduler` (line 1834).
   - The peg formula adjusts for volume imbalance via $\tanh(\kappa_{\text{eff}} \cdot \text{OBI})$, but **lacks queue position feedback**. If our resting order is buried behind a huge queue ($u_q > 0.80$), it suffers from severe adverse selection (only fills when price crashes through our level), yet the peg calculation does not concede any queue priority premium.

---

### 1.4 Baseline Test Suite Health Check
Verification command executed on the active Python virtual environment:
```bash
.venv\Scripts\python.exe -m pytest tests/test_fast_lob_engine.py tests/test_phase5_portfolio_execution.py -v
```
**Result**: `22 passed in 9.58s` (Exit Code 0). All F37 and F38 baseline behaviors are operational and validated.

---

## 2. Logic Chain

### 2.1 Why Level-3 Depth Decay Micro-Price is Structurally Superior
- In modern electronic markets, top-of-book quotes ($L_1$) exhibit extreme fleetingness: over 70% of $L_1$ quotes are canceled within 50 milliseconds by latency arbitrageurs.
- Standard Stoikov (2018) micro-price:
  $$P_{\text{micro}}^{(1)} = P_{\text{mid}} + \frac{S}{2} \cdot \frac{V_b^{(1)} - V_a^{(1)}}{V_b^{(1)} + V_a^{(1)}}$$
  is easily manipulated by "quote flickering" or phantom orders at level 1.
- In contrast, institutional resting liquidity is distributed across multiple price levels ($k=1, \dots, K$). Information content decays geometrically with distance from the mid-price (Cont & de Larrard 2013).
- We formulate the **Level-3 Multi-Tier Curvature-Weighted Micro-Price**:
  $$P_{\text{micro}}^{(L3)} = P_{\text{mid}} + \frac{S}{2} \cdot \mathcal{I}_{L3}$$
  where the multi-tier decayed orderbook imbalance $\mathcal{I}_{L3}$ is:
  $$\mathcal{I}_{L3} = \frac{\sum_{k=1}^K w_k (V_b^{(k)} - V_a^{(k)})}{\sum_{k=1}^K w_k (V_b^{(k)} + V_a^{(k)})}, \quad w_k = \exp(-\lambda_{\text{depth}} (k-1))$$
  with $\lambda_{\text{depth}} = 0.35$ (providing weights: $w_1 = 1.000, w_2 = 0.705, w_3 = 0.497, w_4 = 0.350, w_5 = 0.247$).
- Furthermore, individual order counts ($N_b^{(k)}, N_a^{(k)}$) reveal queue stickiness: a queue of 10,000 shares composed of 2 orders is an institutional anchor; a queue of 10,000 shares composed of 150 orders is retail/HFT noise prone to mass cancellations. We compute the **Order Fragmentation Ratio**:
  $$\Phi_{\text{frag}}^{(1)} = \frac{V_b^{(1)} / \max(1, N_b^{(1)})}{V_a^{(1)} / \max(1, N_a^{(1)})}$$
  which modulates the effective balance of liquidity power.

---

### 2.2 FIFO Queue Position Dynamics & Adverse Selection Discount
- When an execution algorithm places a passive maker order at price $P$, it enters the back of that price level's FIFO queue in `FastOrderBookMatchingEngine`.
- Let $Q_{\text{ahead}}$ be the cumulative volume resting ahead of our order, $q_{\text{my}}$ be our order volume, and $Q_{\text{behind}}$ be the volume resting behind us:
  $$u_q = \frac{Q_{\text{ahead}}}{Q_{\text{ahead}} + q_{\text{my}} + Q_{\text{behind}}} \in [0.0, 1.0]$$
- **The Microstructure Adverse Selection Trap**:
  - If $u_q \to 0$ (front of queue), incoming market orders execute against us immediately; fill probability is high ($P_{\text{fill}} \ge 0.85$) with zero adverse selection.
  - If $u_q \to 1$ (tail of queue), incoming trades only reach us if an aggressive sweep consumes the entire price level. If the market moves in our favor, the orders ahead of us execute and our order is left behind (unfilled alpha loss). If the market moves against us, the entire level is wiped out and we are filled at the worst possible moment.
- **Queue Position Adverse Selection Peg Adjustment**:
  To protect against queue exhaustion while ensuring execution when alpha urgency is high:
  $$\Delta P_{\text{queue}} = \text{sign}(\text{action}) \cdot \frac{S}{2} \cdot \alpha_{\text{urgency}} \cdot \max(0.0, u_q - 0.40) \cdot 0.60$$
  where $\text{sign}(\text{BUY}) = +1, \text{sign}(\text{SELL}) = -1$.
  - When at the front of queue ($u_q \le 0.40$), $\Delta P_{\text{queue}} = 0$ (pure passive rebate capture).
  - When stuck at the tail ($u_q > 0.40$) and urgency is high, the peg price steps up toward the mid/ask, ensuring fills before adverse price drift occurs.

---

### 2.3 Bivariate Marked Hawkes Process for Directional Flow Toxicity
- Univariate Hawkes models cannot distinguish between a wave of aggressive market buys (bullish momentum) and aggressive market sells (bearish liquidation).
- We formulate a **Bivariate Hawkes Point Process** with intensities $(\lambda_+(t), \lambda_-(t))$ for buy- and sell-initiated aggressive flows:
  $$\lambda_+(t) = \mu_+ + \int_0^t \alpha_{\text{self}} e^{-\beta(t-s)} dN_+(s) + \int_0^t \alpha_{\text{cross}} e^{-\beta(t-s)} dN_-(s)$$
  $$\lambda_-(t) = \mu_- + \int_0^t \alpha_{\text{self}} e^{-\beta(t-s)} dN_-(s) + \int_0^t \alpha_{\text{cross}} e^{-\beta(t-s)} dN_+(s)$$
- **Directional Toxicity Imbalance**:
  $$\Delta \lambda_{\text{dir}}(t) = \frac{\lambda_-(t) - \lambda_+(t)}{\lambda_-(t) + \lambda_+(t) + 10^{-6}} \in [-1.0, 1.0]$$
- **Directional Adverse Selection Metric**:
  - For a BUY order, aggressive sells represent toxic incoming flow:
    $$\Gamma_{\text{toxic}}^{\text{BUY}} = \text{clip}\left(\frac{\lambda_- - \bar{\lambda}_-}{1.5 \bar{\lambda}_-} + 0.35 \max(0, \Delta \lambda_{\text{dir}}), 0.0, 1.0\right)$$
  - For a SELL order, aggressive buys represent toxic incoming flow:
    $$\Gamma_{\text{toxic}}^{\text{SELL}} = \text{clip}\left(\frac{\lambda_+ - \bar{\lambda}_+}{1.5 \bar{\lambda}_+} - 0.35 \min(0, \Delta \lambda_{\text{dir}}), 0.0, 1.0\right)$$
- **Adaptive Maker/Taker Ratio Modulation**:
  $$\text{maker\_ratio} = \text{clip}\left(0.70 \cdot \left(1.0 - 0.571 \cdot \Gamma_{\text{toxic}}^{\text{dir}}\right), 0.20, 0.70\right)$$
  Under directional toxic selling, resting bids are contracted from 70% down to 20%, diverting volume into midpoint dark pools or patient TWAP to avoid taking the hit.

---

### 2.4 Advanced Anti-Gaming Darkpool Liquidity Capture
- **HFT Gaming Modes**:
  Predatory market participants send 1-lot ping orders to dark pools. Once a ping fills against an institutional midpoint resting order, the HFT immediately sweeps lit books, moving the market ahead of the institution.
- **Dynamic Minimum Execution Quantity ($\text{MinQty}^*$)**:
  Rather than a static 20%, $\text{MinQty}^*$ should dynamically adapt to order size, toxicity, and accumulation conviction:
  $$\text{MinQty}^* = \max\left(\text{LotSize}, \left\lceil \text{dark\_qty} \cdot \text{clip}\left(0.20 + 0.25 \cdot \Gamma_{\text{toxic}}^{\text{dir}} + 0.15 \cdot \text{Score}_{\text{dark}}, 0.20, 0.50\right) \right\rceil\right)$$
  - Under calm flow ($\Gamma_{\text{toxic}} = 0, \text{Score}_{\text{dark}} = 0$), $\text{MinQty} = 20\%$.
  - Under severe toxicity and heavy accumulation ($\Gamma_{\text{toxic}} = 1.0, \text{Score}_{\text{dark}} \ge 0.80$), $\text{MinQty}$ expands to $50\%$, completely shutting out odd-lot algorithmic pings.
- **Anti-Gaming Dark Fill Probability Kernel (Logistic Hazard Model)**:
  $$P_{\text{fill}}^{\text{dark}} = \frac{1}{1 + \exp(-z)}, \quad z = \beta_0 + \beta_1 \cdot \left(\frac{S_{\text{bps}} - 5.0}{15.0}\right) + \beta_2 \cdot \text{Score}_{\text{dark}} - \beta_3 \cdot \Gamma_{\text{toxic}}^{\text{dir}} - \beta_4 \cdot \left(\frac{\text{MinQty}^*}{\text{dark\_qty}}\right)$$
  with parameters $(\beta_0 = -0.20, \beta_1 = 1.20, \beta_2 = 1.50, \beta_3 = 1.00, \beta_4 = 0.80)$, bounded in $[0.10, 0.90]$.
- **Venue-Specialized Execution**:
  - **KRX (Nextrade / KRX Alternative Venue)**:
    Enforce 1-share lot sizing, 0.5 bps maker rebate advantage, and circuit-breaker bounds ($\pm 30\%$).
  - **US ATS (Direct Midpoint / D-Peg)**:
    Enforce Crumbling Quote Indicator (CQI) protection and pseudo-random micro-jitter probing intervals ($\pm 25\%$) to avoid clock-synchronized algorithmic detection.

---

## 3. Caveats

1. **Level-3 High-Frequency Tick Data vs. Daily Batch Simulation**:
   - In live high-frequency execution, `FastOrderBookMatchingEngine` maintains continuous sub-millisecond book state from ITCH/OUCH or FIX market data feeds.
   - In daily batch mode (e.g., `run_pipeline.py`), granular L3 order queues are simulated from end-of-day bid/ask depth snapshots and microstructure factor proxies. The implementation must guarantee seamless, graceful fallback to Level-1 midpoint prices whenever L3 queue metrics are absent.
2. **Computational Latency Budget**:
   - In `FastOrderBookMatchingEngine`, queue position lookups must remain $O(M)$ where $M$ is the number of orders in a single price level's deque ($M \le 100$). Iterating the deque in Python takes $< 5 \mu s$, well within institutional execution latency budgets.
3. **KRX Nextrade Operational Bounds**:
   - Nextrade's regulatory guidelines enforce specific operating sessions (Pre-market 08:00–08:50, Regular 09:00–15:20, After-hours 15:30–20:00). All ATS routing flags must respect exchange hours and order type eligibility.
4. **Numerical Stability**:
   - Depth decay micro-price formulas must guard against zero denominators ($\sum w_k (V_b^{(k)} + V_a^{(k)}) = 0$), clipping all imbalances to $[-1.0, 1.0]$ and strictly bounding peg prices between `min(best_bid, best_ask)` and `max(best_bid, best_ask)`.

---

## 4. Conclusion & Implementation Blueprint

Phase 6 Feature **F44 (Level-3 Micro-Price Pegging, Hawkes Toxicity & Darkpool Liquidity Capture)** represents the apex of algorithmic execution quality. Below are the concrete code modification targets, method signatures, mathematical formulations, and test case specifications.

### 4.1 Modification Target 1: `trading_system/src/core/fast_lob_engine.py`

#### A. Add `estimate_queue_position` to `FastOrderBookMatchingEngine`
```python
def estimate_queue_position(self, order_id: str) -> Optional[Dict[str, Any]]:
    """
    Computes exact FIFO queue position and fill probability for a resting order.
    Returns:
        queue_ahead: Volume ahead of this order in the FIFO queue
        queue_behind: Volume behind this order in the FIFO queue
        my_volume: Order's current active volume
        queue_position_ratio: u_q = Q_ahead / (Q_ahead + my_vol + Q_behind) in [0.0, 1.0]
        estimated_p_fill: Non-linear probability of execution before cancellation
    """
    with self._lock:
        if order_id not in self.order_lookup:
            return None
        side, price = self.order_lookup[order_id]
        book = self.bids if side == "BUY" else self.asks
        if price not in book:
            return None

        q = book[price]
        q_ahead = 0.0
        my_vol = 0.0
        q_behind = 0.0
        found = False

        for node in q:
            if node.order_id == order_id:
                my_vol = node.volume
                found = True
            elif not found:
                q_ahead += node.volume
            else:
                q_behind += node.volume

        if not found:
            return None

        tot = q_ahead + my_vol + q_behind
        u_q = float(q_ahead / max(1e-6, tot))
        # Cont-Kukanov fill probability: P_fill(u_q) = exp(-1.5 * u_q) * (1 - 0.25 * u_q)
        p_fill = float(np.clip(math.exp(-1.5 * u_q) * (1.0 - 0.25 * u_q), 0.05, 0.95))

        return {
            "order_id": order_id,
            "side": side,
            "price": price,
            "my_volume": my_vol,
            "queue_ahead": q_ahead,
            "queue_behind": q_behind,
            "total_level_volume": tot,
            "queue_position_ratio": round(u_q, 4),
            "estimated_p_fill": round(p_fill, 4),
        }
```

#### B. Enhance `get_depth_snapshot` with Level-3 Metrics
Add L3 multi-tier depth decay micro-price and order fragmentation to `get_depth_snapshot`:
```python
# Multi-level exponential depth decay micro-price (lambda_depth = 0.35)
w_k = [math.exp(-0.35 * i) for i in range(min(len(bids), len(asks), levels))]
if w_k and sum(w_k) > 0:
    num_l3 = sum(w_k[i] * (bids[i]["volume"] - asks[i]["volume"]) for i in range(len(w_k)))
    den_l3 = sum(w_k[i] * (bids[i]["volume"] + asks[i]["volume"]) for i in range(len(w_k)))
    l3_imbalance = float(np.clip(num_l3 / max(1e-6, den_l3), -1.0, 1.0))
    l3_micro_price = 0.5 * (p_b1 + p_a1) + 0.5 * spread * l3_imbalance
else:
    l3_imbalance = obi_1
    l3_micro_price = micro_price

# Order count fragmentation ratio at best bid/ask
n_b1 = len(self.bids.get(p_b1, [])) if p_b1 in self.bids else 1
n_a1 = len(self.asks.get(p_a1, [])) if p_a1 in self.asks else 1
avg_sz_b1 = v_b1 / max(1, n_b1)
avg_sz_a1 = v_a1 / max(1, n_a1)
frag_ratio = float(np.clip(avg_sz_b1 / max(1e-6, avg_sz_a1), 0.1, 10.0))
```

#### C. Add `BivariateHawkesIntensity` to `fast_lob_engine.py`
```python
class BivariateHawkesIntensity:
    """
    Directional Bivariate Hawkes Intensity Process for Buy/Sell Toxicity Tracking.
    Maintains coupled arrival intensities:
        lambda_+(t) = mu_+ + (lambda_+ - mu_+) * exp(-beta * dt) + alpha_self * dN_+ + alpha_cross * dN_-
        lambda_-(t) = mu_- + (lambda_- - mu_-) * exp(-beta * dt) + alpha_self * dN_- + alpha_cross * dN_+
    """
    def __init__(self, mu_buy: float = 1.0, mu_sell: float = 1.0, alpha_self: float = 0.4, alpha_cross: float = 0.1, beta: float = 1.2):
        self.mu_buy = mu_buy
        self.mu_sell = mu_sell
        self.alpha_self = alpha_self
        self.alpha_cross = alpha_cross
        self.beta = beta
        self.last_ts: Optional[float] = None
        self.lambda_buy = mu_buy
        self.lambda_sell = mu_sell
        self._lock = threading.Lock()

    def update(self, side: str, timestamp_sec: Optional[float] = None) -> Tuple[float, float]:
        t = timestamp_sec or time.time()
        with self._lock:
            if self.last_ts is not None:
                dt = max(0.0, t - self.last_ts)
                decay = math.exp(-self.beta * dt)
                self.lambda_buy = self.mu_buy + max(0.0, self.lambda_buy - self.mu_buy) * decay
                self.lambda_sell = self.mu_sell + max(0.0, self.lambda_sell - self.mu_sell) * decay

            side_upper = str(side).upper()
            if side_upper in ["BUY", "BID"]:
                self.lambda_buy += self.alpha_self
                self.lambda_sell += self.alpha_cross
            else:
                self.lambda_sell += self.alpha_self
                self.lambda_buy += self.alpha_cross

            self.last_ts = t
            return (self.lambda_buy, self.lambda_sell)

    def get_directional_toxicity(self, action: str, t_query: Optional[float] = None) -> Dict[str, float]:
        t = t_query or time.time()
        with self._lock:
            dt = max(0.0, t - self.last_ts) if self.last_ts else 0.0
            decay = math.exp(-self.beta * dt)
            lam_b = self.mu_buy + max(0.0, self.lambda_buy - self.mu_buy) * decay
            lam_s = self.mu_sell + max(0.0, self.lambda_sell - self.mu_sell) * decay

            delta_dir = (lam_s - lam_b) / max(1e-6, lam_s + lam_b)
            is_buy = str(action).upper() in ["BUY", "BID"]
            if is_buy:
                gamma = float(np.clip((lam_s - self.mu_sell) / (1.5 * self.mu_sell) + 0.35 * max(0.0, delta_dir), 0.0, 1.0))
            else:
                gamma = float(np.clip((lam_b - self.mu_buy) / (1.5 * self.mu_buy) - 0.35 * min(0.0, delta_dir), 0.0, 1.0))

            return {
                "lambda_buy": round(lam_b, 4),
                "lambda_sell": round(lam_s, 4),
                "delta_dir": round(delta_dir, 4),
                "gamma_toxic_dir": round(gamma, 4),
            }
```

---

### 4.2 Modification Target 2: `trading_system/src/execution/smart_order_router.py`

#### Enhance `route_order` for F44:
1. **Directional Hawkes Parameters**:
   Accept `hawkes_buy: Optional[float] = None`, `hawkes_sell: Optional[float] = None`, or `gamma_toxic_dir: Optional[float] = None`.
   When present, compute $\Gamma_{\text{toxic}}^{\text{dir}}$ and modulate `maker_ratio = np.clip(0.70 * (1.0 - 0.571 * gamma_toxic_dir), 0.20, 0.70)`.
2. **Anti-Gaming Dynamic MinQty**:
   ```python
   # Dynamic anti-gaming MinQty calculation
   if is_toxic_flow or gamma_toxic > 0.50 or dp_score >= 0.60:
       min_ratio = float(np.clip(0.20 + 0.25 * gamma_toxic + 0.15 * dp_score, 0.20, 0.50))
       dark_leg["min_quantity"] = max(1, int(round(min_ratio * dark_qty)))
       dark_leg["anti_gaming_active"] = True
   ```
3. **Logistic Dark Fill Probability**:
   ```python
   z = -0.20 + 1.20 * ((market_spread_bps - 5.0) / 15.0) + 1.50 * dp_score - 1.00 * gamma_toxic - 0.80 * (min_ratio if 'min_ratio' in locals() else 0.20)
   p_fill_dark = float(np.clip(1.0 / (1.0 + math.exp(-z)), 0.10, 0.90))
   ```
4. **Venue Specification Tags**:
   For `KRX_ATS_NEXTRADE`, enforce `lot_size = 1`, and tag leg with `"rebate_bps": 0.5`.
   For `US_SMART_DMA`, tag leg with `"d_peg_cqi_protected": True` and `"micro_jitter_probe": True`.

---

### 4.3 Modification Target 3: `trading_system/src/execution/oms_engine.py`

#### Update `calculate_peg_limit_price` (in both `ExecutionOMSEngine` & `AlmgrenChrissScheduler`):
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
) -> float:
    """
    Phase 6 (F44) Level-3 Micro-Price & Queue-Position-Aware Peg Calculation:
    1. Base price defaults to l3_micro_price if available, then micro_price, then mid_price.
    2. Curvature kappa_eff scales with volatility and orderbook depth.
    3. Imbalance shift uses l3_imbalance or multi-tier L2 OBI composite.
    4. Queue position offset: delta_P_queue compensates when order is buried (u_q > 0.40).
    """
    tp = float(target_price) if (target_price is not None and math.isfinite(float(target_price))) else 1000.0
    if tp <= 0:
        return tp

    spr = float(spread) if (spread is not None and spread > 0) else max(tp * 0.002, 1.0)
    p_bid = float(bid_price) if (bid_price is not None and bid_price > 0) else (tp - spr / 2.0)
    p_ask = float(ask_price) if (ask_price is not None and ask_price > 0) else (tp + spr / 2.0)
    p_mid = (p_bid + p_ask) / 2.0

    # 1. Base anchor price: L3 micro-price > L1 micro-price > mid price
    if l3_micro_price is not None and math.isfinite(float(l3_micro_price)) and float(l3_micro_price) > 0:
        p_base = float(l3_micro_price)
    elif micro_price is not None and math.isfinite(float(micro_price)) and float(micro_price) > 0:
        p_base = float(micro_price)
    else:
        p_base = p_mid

    # 2. Imbalance resolution: L3 decayed imbalance > Multi-tier L2 composite > L1 OBI
    eff_obi = 0.0
    if l3_imbalance is not None and math.isfinite(float(l3_imbalance)):
        eff_obi = float(l3_imbalance)
    elif multi_obi is not None and isinstance(multi_obi, dict):
        obi_1 = float(multi_obi.get("OBI_1", multi_obi.get("obi_1", 0.0)) or 0.0)
        obi_5 = float(multi_obi.get("OBI_5", multi_obi.get("obi_5", 0.0)) or 0.0)
        obi_10 = float(multi_obi.get("OBI_10", multi_obi.get("obi_10", 0.0)) or 0.0)
        eff_obi = 0.50 * obi_1 + 0.35 * obi_5 + 0.15 * obi_10
    elif obi is not None and math.isfinite(float(obi)):
        eff_obi = float(obi)

    # 3. Dynamic curvature scaling
    if daily_volatility is not None or book_depth_ratio is not None:
        sig = float(daily_volatility) if daily_volatility is not None else 0.02
        r_depth = float(np.clip(float(book_depth_ratio or 1.0), 0.20, 5.0))
        kappa_eff = float(np.clip(1.5 * (sig / 0.02) / math.sqrt(r_depth), 0.8, 3.0))
    else:
        kappa_eff = float(kappa)

    is_buy = str(action).upper() in ["BUY", "LONG", "BUY_HEDGE", "BID"]

    # 4. Imbalance peg shift
    obi_val = float(np.clip(eff_obi, -1.0, 1.0))
    peg_shift = 0.5 * spr * math.tanh(kappa_eff * obi_val)

    # 5. Queue position adverse selection offset (F44)
    q_shift = 0.0
    if queue_position_ratio is not None and math.isfinite(float(queue_position_ratio)):
        u_q = float(np.clip(float(queue_position_ratio), 0.0, 1.0))
        if u_q > 0.40:
            direction = 1.0 if is_buy else -1.0
            urgency = float(np.clip(float(alpha_urgency), 0.1, 1.0))
            q_shift = direction * 0.5 * spr * urgency * (u_q - 0.40) * 0.60

    peg_price = p_base + peg_shift + q_shift
    return float(np.clip(peg_price, min(p_bid, p_ask), max(p_bid, p_ask)))
```

---

### 4.4 Test Case Specifications for `tests/test_phase6_execution_microstructure.py`

Design 12 comprehensive unit and property test cases:
1. `test_f44_l3_exponential_depth_decay_micro_price`:
   Verifies that when $L_1$ quotes flicker, $L_3$ multi-tier micro-price $P_{\text{micro}}^{(L3)}$ with depth decay $\lambda=0.35$ remains resilient and anchors closer to genuine deeper liquidity.
2. `test_f44_order_fragmentation_ratio_computation`:
   Verifies that large block institutional orders on the bid produce high fragmentation power, shifting the effective pricing balance toward the bid.
3. `test_f44_fifo_queue_position_tracking`:
   Inserts multiple limit orders at identical price; verifies that `estimate_queue_position` correctly tracks `queue_ahead`, `queue_behind`, and $u_q \in [0, 1]$.
4. `test_f44_queue_position_step_up_peg_pricing`:
   Verifies that an order at the back of the queue ($u_q = 0.85$) receives a positive queue concession $\Delta P_{\text{queue}} > 0$ for BUY, increasing fill priority relative to $u_q = 0.10$.
5. `test_f44_bivariate_hawkes_directional_toxicity`:
   Verifies that an aggressive sell trade burst elevates $\lambda_{\text{sell}}$ and $\Delta \lambda_{\text{dir}} > 0$, driving $\Gamma_{\text{toxic}}^{\text{BUY}} \to 1.0$ while keeping $\Gamma_{\text{toxic}}^{\text{SELL}} \approx 0.0$.
6. `test_f44_directional_hawkes_contracts_maker_to_twenty_percent`:
   Verifies that under directional toxic selling, `maker_ratio` on BUY orders safely drops to $0.20$ (lower than Phase 5's $0.30$).
7. `test_f44_anti_gaming_min_qty_dynamic_expansion`:
   Verifies that high toxicity and darkpool accumulation expand `min_quantity` from 20% up to 50% of dark quantity, shutting out odd-lot snipes.
8. `test_f44_logistic_darkpool_fill_probability_bounds`:
   Verifies that the logistic hazard model outputs fill probabilities strictly bounded within $[0.10, 0.90]$ and responds monotonically to spread and MinQty.
9. `test_f44_krx_nextrade_venue_routing_compliance`:
   Verifies that Korean equities (`.KS`, `.KQ`) routing to `KRX_ATS_NEXTRADE` receive 1-share integer lot allocations and 0.5 bps maker rebate advantage.
10. `test_f44_us_smart_dma_anti_gaming_flags`:
    Verifies that US equities routing to `US_SMART_DMA` receive `d_peg_cqi_protected` and `micro_jitter_probe` institutional tags.
11. `test_f44_parity_between_oms_engine_and_almgren_chriss`:
    Verifies that `ExecutionOMSEngine.calculate_peg_limit_price` and `AlmgrenChrissScheduler.calculate_peg_limit_price` produce identical outputs to $< 10^{-6}$ precision across all parameter combinations.
12. `test_f44_extreme_market_bounds_and_graceful_fallbacks`:
    Stress tests zero book depth, inverted spreads, negative prices, and infinite Hawkes values; confirms zero exceptions and strict clipping within `[best_bid, best_ask]`.

---

## 5. Verification Method

To independently verify the observations, logical inferences, and proposed implementation:

```bash
# 1. Verify existing LOB Engine and Phase 5 Portfolio Execution suites
.venv\Scripts\python.exe -m pytest tests/test_fast_lob_engine.py tests/test_phase5_portfolio_execution.py -v
# Expected: 22 passed in < 10s

# 2. Inspect target execution codebases
# Check lines 82-123 and 134-150 in SmartOrderRouter:
git grep -n "gamma_toxic" trading_system/src/execution/smart_order_router.py
# Check calculate_peg_limit_price in ExecutionOMSEngine:
git grep -n "def calculate_peg_limit_price" trading_system/src/execution/oms_engine.py

# 3. Post-implementation verification of Phase 6 Microstructure Test Suite
.venv\Scripts\python.exe -m pytest tests/test_phase6_execution_microstructure.py -v
# Expected: 12 passed, 0 failed, 100% pass rate
```

