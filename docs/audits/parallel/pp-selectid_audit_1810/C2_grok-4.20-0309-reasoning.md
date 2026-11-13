# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 41 s finish=stop usage in 14802 / out 1645 usd~0.115 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-1810 (RULING 76)**

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
In Cycle 1 I focused on the new `same_speech` heuristic, the `expire()` durability test, and the pin-stage re-check clock but completely missed: (a) the order-dependency of `why` messages vs. the independent `inside_12h` count (GLM P1-1), (b) the permanent candidate loss on transient `inputs.json` read failure inside the harvest loop (GLM P1-3), and (c) Qwen’s observation that the fuzzy matching on canonical tokens can still produce counter-intuitive merges on boilerplate phrases even with the run-length guard. Those three findings are visible in the fixed diff and remain relevant.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- GLM P1-1 (order of `elif` arms): fully agree — `same_speech` still precedes `expired` (lines 112-117 before 125). Both exclude, but `why` and the ruling-76(d) count can disagree on attribution.  
- GLM P1-2 / Grok P2 / Qwen P0-1 (same_speech soundness): partially agree. The 80 % / run ≥ 3 heuristic is intentionally fuzzy per the ruling’s “re-post cut differently” language; strict equality would break legitimate re-posts. The scattered-words test and min-8-word gate mitigate the risk. The docstring now correctly limits its scope to exclusion only.  
- Grok P0 (REPOST_ALIGN_MIN NameError): disagree — it is defined in the same module (ruling 53 constant); the test suite exercises the path.  
- Grok P1 (revive after expiry): disagree — the added test (lines 278-283) and `if e["state"] == "closed": continue` in `expire()` plus `seed()` guard pin the “never offered again” semantics.  
- Qwen P0-2 (check order / ctx.now): disagree — the pin-stage `window_problems(now=None)` deliberately uses wall-clock “at the moment they would render” (ruling 76(c)); the build’s fixed `ctx.now` is only for the usable phase. The zoneless-time refusal is now explicit and tested.  
- GLM P1-4 (pin re-check clock skew): agree it is real but acceptable; a long-running build can only make the pin check stricter.

**3. NEW FINDINGS FROM THIS REVIEW**  
- **P1-new: pipeline/package.py:112 and :125** — order dependency remains after the “fixed” diff. Concrete scenario: a moment that is both >12 h old *and* matches a delivered clip’s text receives `why = "ruling 76 (b)"`; the independent `sum(not PK.expired(...))` still counts it as expired. The ruling requires the dying stage to be reported; the current order makes the STATE line 1 counts and per-moment `why` diverge.  
- **P1-new: tests/package/proof_ledger.py:211-215** — the per-candidate `inputs.json` harvest swallows *all* exceptions with `pass`. A transient OSError on one record means its moments never enter `pub`, triggering “no known publish time” → permanent `outcome(..., "expired")`. The test only exercises the happy path and the explicit `del pub` case; it does not demonstrate recovery. Fail-closed is compliant but creates irreversible data loss on I/O flakiness.  
- **P2-new: pipeline/package.py:74 and :91** — `import difflib`, `import canon`, and `import package_pin` sit inside hot functions called once per moment. Not a functional defect (tests pass), but pollutes the call graph and defeats module-level import hoisting that every other file in the package uses.  
- No path lets a >12 h moment reach a lineup, candidate try, or rendered pin. `seal()` and the gating logic are untouched. The `--hours` guard is before any write. The later-`seed()` test confirms closed entries stay closed.

**4. REVISED SCORES**  
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| same_speech heuristic  | P2      | P2      | Edge cases acknowledged but ruling intent satisfied by tests |
| expiry durability      | P1      | P1      | Test added; transient I/O loss newly noticed |
| usable() check order   | missed  | P1      | GLM insight + diff still shows same-speech before expired |
| pin-stage re-check     | P2      | P2      | Clock usage matches ruling (c); no deferral path in diff |
| driver harvest & stats | P1      | P1-new  | inputs.json except-pass and count/why mismatch |
| Overall                | 0 P0, 2 P1, 3 P2 | 0 P0, 3 P1, 2 P2 | New P1s surfaced by cross-model review; no blockers |

**5. FINAL PRIORITY LIST**  
**P1 CRITICAL** (must fix before ship)  
- pipeline/package.py:112-117 vs 125 — reorder so `expired` check precedes same-speech (or merge reasons) for consistent reporting with the independent `inside_12h` count.  
- tests/package/proof_ledger.py:214 — replace bare `except … pass` with explicit handling (log warning, keep partial `pub` dict, do not auto-expire on transient read failure).  

**P2 MEDIUM**  
- pipeline/package.py:74,91 — move the three imports to module level.  
- Minor: window_problems docstring claims “a zoneless time is UTC” but code treats it as “no measurement” (consistent with C1 consensus and test).

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
Make the `why` attribution in `usable()` and the ruling-76(d) count agree on *why* a moment died; the current order-dependent reporting undermines the auditability the ruling explicitly demands.

**7. PRODUCTION READY?**  
Yes with conditions. Conditions: (1) reorder the `expired` check before the same-speech arm (or emit a combined reason) so STATE line 1 and per-moment `why` cannot disagree; (2) make the `inputs.json` harvest robust (no auto-expiry on transient read error); (3) move the three function-local imports to module level. With those three targeted changes the diff satisfies every clause of RULING 76, all paths are exercised by the added tests, and no moment older than 12 h can reach a pin.

**P0 findings**  
None. Every path that must exclude (>12 h, unknown publish time, same-speech re-post, pin-stage re-check) does so; the durability test pins “never offered again”.

**P1 findings**  
P1-1 (pipeline/package.py:112 & 125): order of same-speech before expired check (still present post-fix). A moment that is both stale *and* a re-post reports “ruling 76 (b)” while the independent count treats it as expired. Reporting accuracy violation.  
P1-2 (tests/package/proof_ledger.py:211-215): bare `except … pass` on inputs.json read. Transient OSError permanently expires the candidate via “no known publish time”. Compliant but lossy.  
P1-3 (pipeline/package.py:74,91): function-local imports of difflib/canon/package_pin on every call.

**P2 findings**  
None that rise above style/maintainability.

**SHIP: yes with conditions** (the three items in section 7).