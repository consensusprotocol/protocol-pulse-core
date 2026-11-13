# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 29 s finish=stop usage in 30530 / out 1348 usd~0.186 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-1112 (Rulings 58/59)**

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
Grok caught the per-process `CACHE_LOCK` + hook-cache key omitting context SHA (lines 49, 278). GLM caught the ledger rewrite on pure-cache hits (`if store and (todo or db)`) and the multi-backend cache shape interacting with `second_screen` vendor filtering (lines 199, 280). Qwen surfaced the pre-parallel `cdb` snapshot and the exact `can_open`/`hook_rating=None` edge. I had not explicitly enumerated the ledger-provenance side-effect or the alphabetical-first cache pick when multiple off-writer back-ends exist in the shared cache. Those are real (observable) behavior changes, even if not defects.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- **Grok P2 cache lock & hook key**: Fully agree. Builds are serialized today, so lock is sufficient (P2); hook prompt never sees date/title/window so key is intentionally minimal (K1).  
- **GLM P1-1 ledger rewrite & P1-2 multi-vendor cache pick**: Agree on the observable change; disagree it is P1. The ledger has always been “what this build saw,” not “what it paid for.” The cache shape is explicitly documented in the new docstring. The order-06:22 test still passes because `second_screen` uses a different writer set.  
- **GLM P1-3 reply-contract strictness & P1-4 carried-in `hook_rating`**: Agree. One stray ID kills the batch (fail-closed, L-m). The `if "hook_rating" in m` guard + explicit clear at 500-501 makes the pre/post-build distinction deterministic.  
- **Qwen P0 on cache poisoning / second_screen key mismatch**: Disagree. The `new` dict is populated only on success and the retry loop returns immediately; `_cache_put` merges under lock. `second_screen` rebuilds contexts identically. The refuted R1 in consensus holds.  
- **Consensus refutations (R2-R4)**: All correct; router locks, early returns, and `r=None` before the call are verifiable in the diff + referenced files.

**3. NEW FINDINGS FROM THIS REVIEW**  
- **P2: pipeline/package.py:148 (db[f"{mid}:{STEP_A_VERSION}"] = rec on cache hit)**: When a cache hit supplies the record, the build still mutates its own ledger with a verdict whose `backend` may be from a prior build’s vendor set. Combined with the `if store and (todo or db)` change this makes the ledger non-reproducible from the build’s own calls alone. Concrete scenario: two builds with different `writer_vendor` sets; second build gets all cache hits → its ledger now claims a backend the current writers would have rejected. Not a correctness violation (K5, off-writer filter still applied at read time) but a provenance leak.  
- **P2: pipeline/package.py:576 (hrank dict keyed by moment_id before the stable sort)**: The hook-rank tuple is built only from the *pre*-second-screen passing list. If second_screen drops the top hook, the sort key for remaining angles still uses the stale rating tuple. The re-check at 533-538 prevents a bad hook from being used, but the sort order of the surviving angles is no longer guaranteed “best hook first.” Minor (still best-first among survivors) but not the exact semantics stated in K6.  
- No new P0/P1. Every fail-closed path (unrated hook → `{"rating": None}`, failed batch never cached, corrupt `_load_cache` → {}, out-of-contract angle re-ask, `keep_hook=True` early return) is exercised by the new tests or visible in the diff.

**4. REVISED SCORES**  
| Subsystem          | Cycle 1 | Cycle 2 | Why changed |
|--------------------|---------|---------|-------------|
| prescreen/cache    | P1      | P2      | Ledger rewrite & multi-vendor pick are observable but not correctness-breaking (consensus + test coverage) |
| hook_ratings       | P2      | P2      | No change; contract enforcement and one-retry logic solid |
| build() ordering   | P2      | P2      | New stale-hrank observation but still fail-closed |
| can_open / lineup  | P2      | P2      | All paths updated; K5 default preserved |
| parallelism/locks  | P2      | P2      | Thread lock sufficient given current orchestrator |
| tests              | P2      | P2      | New suites + Rig extension give >95 % path coverage |

**5. FINAL PRIORITY LIST**  
**P2 MEDIUM** (must address before long-term maintenance)  
- pipeline/package.py:148 — ledger mutation on cache hit (add comment or separate “this-build-only” ledger).  
- pipeline/package.py:576 — rebuild `hrank` from post-second-screen passing hooks.  
- pipeline/package.py:49 & 72 — document that `CACHE_LOCK` is intra-process only; consider file lock if parallel builds ever appear.  
- pipeline/package.py:280 — add explicit tie-breaker (e.g. most recent timestamp) inside the `next(...)` if multiple eligible back-ends exist in cache.  

No P0 or P1.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
Make the shared cache *read-only* for provenance (never mutate this build’s ledger with foreign verdicts) while keeping the “paid once” guarantee — this eliminates the entire class of ledger/cache-interaction questions raised by all three Cycle-1 reviewers.

**7. PRODUCTION READY?**  
**Yes with conditions.**  
Conditions: (1) apply the three P2 items above (or accept them as documented tech debt with comments), (2) run the proof_ledger suite against a real 72 h window with the new caches to confirm USD stays under budget, (3) add a one-line assertion in `_cache_put` that no writer-vendor verdict is ever written. With those, the diff implements rulings 58/59 exactly, all fail-closed paths are preserved, and the new hook-first order demonstrably prevents spending on hopeless line-ups.

**P2 findings only. SHIP: yes with conditions**