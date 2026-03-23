# TEMPORAL PREDICTIVE ANALYTICS — SCENARIO SIMULATION ENGINE
# Foundation Document · Protocol Pulse Intelligence Terminal
# ML Session — Monte Carlo + Calibrated Probability Engine
# Created: 2026-03-23

---

## WHAT WE'RE BUILDING

The Time Machine. A scenario simulation engine that answers the question
Bloomberg, Glassnode, and CoinMetrics cannot: "Given everything happening right
now, what are the most likely trajectories for Bitcoin over the next 30/90/365
days — and what early signals would confirm each one?"

Not price prediction. Not a chart. A structured intelligence product that models
Bitcoin's future as a probability-weighted tree of named scenarios, each with
detectable precursor signals that Protocol Pulse can monitor in real time.

When someone opens this at a board meeting and shows the probability distribution
across 5 named scenarios with live signal confirmation counts, that's when they
cancel Bloomberg.

---

## ARCHITECTURE: MONTE CARLO + BAYESIAN CALIBRATION

### Why Not Deep Learning

TPA does NOT use a neural network for the core simulation. Here's why:

1. Bitcoin has had ~5 full market cycles. That's 5 data points at the cycle level.
   No neural network trains meaningfully on 5 examples.

2. The value of TPA is EXPLAINABILITY. A user must understand WHY scenario X
   has 34% probability. A black-box neural net can't provide that.

3. Monte Carlo + calibrated priors is the correct tool. It's what institutional
   risk desks use. It produces interpretable, auditable results.

4. The "ML" in TPA is in the CALIBRATION: using historical cycle data + current
   Protocol Pulse signals to set prior probabilities and update them as signals
   fire. This is Bayesian updating — principled, explainable, correct.

---

## THE 5 NAMED SCENARIOS (V1)

Each scenario is a named, structured hypothesis about Bitcoin's next 12 months.
Each has: a description, 5-7 precursor signals (drawn from Protocol Pulse data),
a base probability, and signal-update rules.

### SCENARIO 1: INSTITUTIONAL ADOPTION ACCELERATION
**What it means:** ETF flows sustain, corporate treasury adoption continues,
sovereign wealth fund allocation begins. Bitcoin increasingly functions as
institutional reserve asset.

**Base probability:** 28% (calibrated against 2020-2021 cycle analog)

**Precursor signals (each adds probability when confirmed):**
1. ETF net inflows > $500M/week for 4+ consecutive weeks (+5%)
2. CME futures open interest at 6-month high (+4%)
3. Stablecoin minting > $2B/month for 3+ consecutive months (+4%)
4. Convergence Engine: INSTITUTIONAL_ENTRY_SIGNAL fires CRITICAL (+6%)
5. Exchange reserve ratio declining >3% over 30 days (+4%)
6. Corporate treasury announcement (RSS/news detection) (+3%)

**Scenario progression:** Precursor 1-2 fire → "FORMING" (weak signal).
3-4 fire → "WATCH" (moderate confidence). 5-6 fire → "HIGH CONFIDENCE".

---

### SCENARIO 2: REGULATORY CRACKDOWN CASCADE
**What it means:** Coordinated G20 regulatory action restricts Bitcoin
access, exchange operations, or custody. Creates short-term price pressure
and accelerates capital flight to P2P markets.

**Base probability:** 18%

**Precursor signals:**
1. Regulatory Intelligence: threat_level = "HIGH" for 7+ consecutive days (+7%)
2. Convergence Engine: REGULATORY_SHOCK_PROPAGATION fires (+8%)
3. P2P volume spike >300% in 3+ G20 jurisdictions simultaneously (+5%)
4. Exchange inflows >3x baseline for 14+ consecutive days (+4%)
5. Jurisdiction DB: 2+ countries reclassify from LEGAL to RESTRICTED (+4%)
6. BIS/ECB regulatory coordination language detected in RSS (+3%)

---

### SCENARIO 3: NETWORK SECURITY CRISIS
**What it means:** A credible threat to Bitcoin's consensus mechanism emerges —
hashrate concentration, novel attack vector, or critical protocol vulnerability.
Rare. Devastating short-term. Self-correcting long-term.

**Base probability:** 4%

**Precursor signals (high-confidence signals only — this scenario needs strong evidence):**
1. PCAF anomaly score (v1 or v0) > 85 for 48+ consecutive hours (+10%)
2. Single pool > 45% of trailing 10-block hashrate for 6+ hours (+8%)
3. Orphan block rate > 3x baseline for 24+ hours (+7%)
4. Convergence Engine: MINER_CAPITULATION_CASCADE fires CRITICAL (+6%)
5. Bitcoin Core GitHub: emergency patch PR opened (GitHub API detection) (+5%)

Note: Base probability intentionally low. Even with all 5 signals, max ~40%.
This is a "tail risk" scenario — the system should flag it seriously but
not overestimate frequency.

---

### SCENARIO 4: MACRO LIQUIDITY EXPANSION
**What it means:** Global monetary policy pivots to easing. Dollar weakens.
Risk assets including Bitcoin benefit from expanding liquidity. Historical
analog: 2020 QE response.

**Base probability:** 32% (highest base — macro backdrop currently supportive)

**Precursor signals:**
1. DXY (dollar index) declining >5% over 30-day period (+5%)
2. Fed/ECB pivot signals in regulatory RSS (+4%)
3. Gold +10% over 60 days (+4%)
4. VIX declining from elevated levels (>25 to <18 over 30 days) (+4%)
5. Convergence Engine: SAFE_HAVEN_ROTATION fires (+6%)
6. Stablecoin supply net increase >$5B over 60 days (+4%)

---

### SCENARIO 5: CBDC DISPLACEMENT ATTEMPT
**What it means:** Major economies accelerate CBDC rollout with features
explicitly targeting Bitcoin's use cases (cross-border, privacy, store of value).
Creates regulatory pressure and retail market share competition.

**Base probability:** 18%

**Precursor signals:**
1. Sovereign Layer: 2+ G7 CBDCs advance to "live" or "mandatory" stage (+8%)
2. CBDC programmability features: expiry/geofencing announced in G20 (+7%)
3. P2P volume surge in G7 jurisdictions (citizens exiting fiat) (+4%)
4. Privacy Tech: Coinjoin volume >3x baseline for 30+ days (+4%)
5. BIS working paper on CBDC interoperability with major powers (+3%)

---

## SIMULATION ENGINE

### Monte Carlo Process (runs every 6 hours)

```
For each scenario S (5 scenarios):
    1. Start with base_probability[S]
    2. For each precursor signal P in S.signals:
           if signal_confirmed(P, current_SentinelState):
               base_probability[S] += P.probability_delta
               record_confirmation(S, P, timestamp)
    3. Apply temporal decay: signals confirmed >30 days ago decay 50%
    4. Apply contradiction penalty: if scenario S contradicts scenario T
       and T has high confidence, reduce S by 10%
    5. Clip to [1%, 95%] — never 0 or 100

After updating all scenarios:
    6. Normalize probabilities to sum to 100%
    7. Compute confidence intervals via Monte Carlo:
           For 10,000 iterations:
               sample = jitter each signal confirmation (±20% uncertainty)
               recompute scenario probabilities with jittered inputs
           Report: p10, p50, p90 for each scenario probability
    8. Store result in tpa_state
```

### Contradiction Matrix

Some scenarios are mutually exclusive or inversely correlated:
- S1 (Institutional Adoption) ↔ S2 (Regulatory Crackdown): negative correlation
  If S2 precursors fire, penalize S1 by 15% (and vice versa)
- S4 (Macro Expansion) ↔ S5 (CBDC Displacement): mild negative (-8%)
- S3 (Network Crisis) ↔ S1 (Institutional Adoption): strong negative (-20%)
  Institutional adoption can't accelerate if network security is threatened

Stored in: data/tpa_scenario_correlations.json

---

## HISTORICAL CALIBRATION

Base probabilities were calibrated against 4 historical Bitcoin cycles.
The calibration methodology:

1. For each historical cycle (2013, 2017, 2020-21, 2024):
   - Map which scenario(s) "won" (what actually happened)
   - Score each scenario's precursor signals against historical data
   - Compute: if signals were at today's confirmation level in [year],
     what was the actual outcome?

2. Use scipy.stats.beta distribution fitting:
   For each scenario, fit a beta distribution to historical win rates
   given precursor confirmation counts.
   Beta distribution is ideal: naturally bounded [0,1], captures uncertainty.

3. Current base probabilities reflect posterior means of these beta distributions.

Historical data sources (all free):
- Price: CoinGecko /api/v3/coins/bitcoin/market_chart?days=max
- Hashrate: mempool.space/api/v1/mining/hashrate/3y
- Regulatory events: curated JSON from public Bitcoin policy timeline
  (Coin Center, Bitcoin Policy Institute historical records)

**Important:** Calibration is a one-time process run before deployment.
Results stored in data/tpa_calibration.json. Updated annually.

---

## SIGNAL CONFIRMATION IMPLEMENTATION

Each precursor signal maps to a specific function that queries SentinelState:

```python
def check_signal(signal_id: str, state: dict) -> tuple[bool, float]:
    """
    Returns (confirmed: bool, strength: float 0-1)
    Strength allows partial credit (e.g., ETF inflows at $300M = 0.6 strength
    toward the $500M threshold).
    """
```

Signal checkers for all 27 precursor signals:
- ETF/custodian flows → state["etf"]
- Convergence Engine patterns → state["convergence"]["pattern_results"]
- Exchange reserves → state["sovereign"]["custody_health"]
- PCAF score → state["pcaf_v0"] or state["pcaf_v1"]
- Regulatory → state["regulatory"]
- Sovereign/CBDC → state["sovereign"]["top_alerts"]
- Macro (DXY, Gold, VIX) → state["sentiment"] + signal_feeds
- P2P volume → state["sovereign"]["p2p_volume"]

---

## FRONTEND — SCENARIO ENGINE PANEL

New dedicated page: protocolpulse.io/intelligence/scenarios

**Layout:**

```
┌──────────────────────────────────────────────────────────┐
│  TEMPORAL PREDICTIVE ANALYTICS · Updated 4h ago          │
│  Horizon: [30D] [90D] [365D]   Confidence: [P10-P90]    │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  INSTITUTIONAL ADOPTION ACCELERATION    32% [▓▓▓▓░░░]   │
│  ↑ +4% since last update · 3/6 signals confirmed        │
│  ████ ETF inflows ✓  ████ CME OI ✓  ░░░ Stablecoin...  │
│                                                          │
│  MACRO LIQUIDITY EXPANSION              28% [▓▓▓░░░░]   │
│  → stable · 2/6 signals confirmed                       │
│                                                          │
│  REGULATORY CRACKDOWN CASCADE           22% [▓▓░░░░░]   │
│  ↑ +3% since last update · 1/5 signals confirmed        │
│  ████ Reg threat HIGH ✓                                  │
│                                                          │
│  CBDC DISPLACEMENT ATTEMPT              12% [▓░░░░░░]   │
│  → stable · 0/5 signals confirmed                       │
│                                                          │
│  NETWORK SECURITY CRISIS                 6% [░░░░░░░]   │
│  ↓ -1% · 0/5 signals confirmed                          │
│                                                          │
├──────────────────────────────────────────────────────────┤
│  [TRACK THIS SCENARIO ▼]  [SIGNAL HISTORY]  [SHARE]     │
└──────────────────────────────────────────────────────────┘
```

**Scenario tracking alerts:**
User can click "TRACK THIS SCENARIO" — if the scenario's probability
changes >10% in either direction, they get a Telegram/push notification.
Stored in user preferences table.

**Share button:** Generates a snapshot URL with current probabilities
and confirmed signals. The thing that gets posted to X and goes viral.

---

## SENTINELSTATE INTEGRATION

```python
tpa: dict = field(default_factory=lambda: {
    "scenarios": [
        {
            "id": "INSTITUTIONAL_ADOPTION",
            "name": "Institutional Adoption Acceleration",
            "probability": 28.0,       # current probability %
            "probability_p10": 22.0,   # Monte Carlo confidence interval
            "probability_p90": 35.0,
            "base_probability": 28.0,  # unmodified prior
            "delta_since_last": 0.0,   # change in last 6h update
            "trend": "stable",         # rising/falling/stable
            "signals_confirmed": 0,    # count
            "signals_total": 6,
            "confirmed_signal_ids": [],
            "last_updated": 0.0,
        },
        # ... 4 more scenarios
    ],
    "last_evaluated_at": 0.0,
    "next_evaluation_at": 0.0,
    "calibration_date": "",
    "data_quality": "good",  # "good"/"degraded"/"stale"
})
```

---

## FILES TO CREATE

NEW:
  services/tpa_engine.py            — Monte Carlo simulation + signal checkers
  services/tpa_calibrator.py        — One-time historical calibration script
  data/tpa_scenarios.json           — Scenario definitions (editable)
  data/tpa_calibration.json         — Historical calibration results
  data/tpa_scenario_correlations.json — Contradiction matrix
  core/templates/scenarios.html     — Dedicated scenario UI page
  core/templates/scenario_card.html — Reusable scenario card component

MODIFY:
  services/sentinel.py
    - Add tpa field to SentinelState
    - Load TPAEngine via importlib.util
    - Run TPA every 6 hours

  core/blueprints/intelligence.py
    - GET /intelligence/scenarios — scenarios page
    - GET /api/intelligence/tpa — full TPA state JSON
    - POST /api/intelligence/tpa/track — track a scenario (store in user prefs)
    - GET /api/intelligence/tpa/snapshot/<id> — shareable snapshot URL

---

## DEPENDENCIES

No new Python packages needed beyond what's installed.
scipy (already installed) handles the beta distribution fitting.
numpy (already installed) handles Monte Carlo sampling.

This is the one ML feature that runs entirely without GPU.
Monte Carlo runs on CPU in < 2 seconds for 10,000 iterations.

---

## SUCCESS CRITERIA

1. Calibration script runs successfully on 4-year price history
2. All 5 scenarios initialized with calibrated base probabilities
3. Signal checkers verified: each of 27 signals correctly reads from SentinelState
4. Monte Carlo produces consistent p10/p50/p90 intervals (run 5x, variance < 3%)
5. Scenario probabilities sum to 100% after normalization
6. Temporal decay works: signal confirmed 31 days ago has 50% strength
7. Contradiction matrix: S1+S2 can't both be >40% simultaneously
8. /intelligence/scenarios page renders all 5 scenarios with live data
9. Probability update visible within 10 minutes of a convergence pattern firing
10. Share URL generates correctly, survives 24h without decay

