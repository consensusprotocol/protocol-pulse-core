# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 32 s finish=stop usage in 51762 / out 1386 usd~0.293 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-2322 (spotlight pin kind)**

1. WHAT DID THEY CATCH THAT YOU MISSED?
Qwen's <critical> on the literal `True` for `facts["never_delivered"]` (original spotlight.py:1160) was missed in my Cycle 1 pass; it made the gate non-measured and always-PASS, violating L-m. The fix (this diff: spotlight.py:1158 using `bool(P.usable([m], ...)[0])` + test_spotlight.py:2022-2027 that forces a delivered overlap on the second call) is verifiable in the diff. GLM's latent medley-with-closing seal change (package_pin.py:186-188) was also overlooked; the shape-keyed guard + pin_seal test suite now proves every prior MOMENTS_PIN recomputes identically.

2. WHERE DO YOU AGREE OR DISAGREE?
- Qwen critical (never_delivered hard-coded): Fully agree. Fixed exactly as consensus describes; row now derives from measurement and can FAIL the pin.
- GLM medium (seal compatibility + closing keyed on "closing" in edl_vo): Agree on the original risk. Revised seal() (package_pin.py:186: `if shape == "spotlight"`) and the explicit test (test_spotlight.py:1632-1655, including the medley-vs-spotlight body equality) eliminate it. The integrator's exact call is reproduced in the test.
- GLM medium (LP.apply after closing verdicts): Agree it is not new; identical to medley order, LP.apply refuses mismatched adopted text (ruling 67/84), and scorer_problems refuses mismatched text_sha256 at pin time.
- Grok "no findings / SHIP yes": Partially agree post-fix. The original critical existed; after the usable() re-measure and SPOTLIGHTS re-read in proof_ledger.py:1384, the rest of Grok's checklist (snap bounds, ruling 92 fail-closed, L-s verdicts off writers, per-channel-day including unreadable record, medley unchanged) holds.
- Consensus on refuted points (scorer wait bounded by poll count, thread safety identical to paid_gates, snap re-judged): Agree; diff confirms while-loop in snap(), bounded `range(max(1, int(wait_s // SCORER_POLL_S)))`, and extra= deduplication by (moment_id, text_sha).

3. NEW FINDINGS FROM THIS REVIEW
<medium> spotlight.py:1158 — facts["one_per_channel_day"] recomputes `et_day(ctx.now)` instead of reusing `facts["day"]`. Concrete: a build that starts at 23:59 ET (day="2026-11-13") and reaches package_for() after midnight (now advanced by scorer wait or ThreadPoolExecutor) produces a facts row measuring the next calendar day while pool() used the prior day. Pin-stage re-read (proof_ledger.py:1384) still protects, but the sealed row evidence mismatches the pool decision. (Not a crash, but violates "measured ... exactly as the build measured them" comment at inventory:900.)

<medium> spotlight.py:1100 — scorer wait loop does `for _ in range(max(1, int(wait_s // SCORER_POLL_S)))` with fixed sleep. Concrete: if SCORER_POLL_S=30 and wait_s=600, exactly 20 polls occur even if the verdicts file appears after poll 2; the test mocks sleep but does not assert that a late-arriving rating is used without full wait. Matches production intent but the "bounded number of polls" comment hides that the last poll is not guaranteed to see the rating.

No <critical> or <high>. All governing laws (SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-a through L-c, L-m, L-s) are satisfied by the diff; every checked item in the query holds.

4. REVISED SCORES
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| Seal / pin contract    | 9/10    | 9/10    | No change; tests now explicitly cover spotlight shape/first_comment/closing |
| L-m measurement        | 6/10    | 9/10    | Hard-coded never_delivered fixed; facts re-measure + inventory measured= flags added |
| Ruling 90-92 logic     | 8/10    | 8/10    | New medium on day boundary and poll loop; otherwise identical to Grok checklist |
| Snap / pool re-judge   | 7/10    | 8/10    | Explicit usable() re-call after snap() and full build stages now visible |

5. FINAL PRIORITY LIST
P2 MEDIUM: spotlight.py:1158 — change the set comprehension to `== facts["day"]` (one-line reuse, eliminates midnight-cross theoretical mismatch).  
P2 MEDIUM: spotlight.py:1100 — add assertion in test that a rating arriving on poll N < max uses it immediately (already true in the mock but not asserted).  
No P0/P1 items. All Cycle-1 criticals are closed.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
Re-measuring never_delivered/one_per_channel_day immediately before package_for() (spotlight.py:1157-1160) plus the SPOTLIGHTS re-read at pin time turns the former dead gate into a live, fail-closed guard while preserving the free-pool optimisation.

7. PRODUCTION READY?
Yes with conditions: (1) reuse facts["day"] in the one_per_channel_day line (spotlight.py:1158), (2) extend the scorer-wait test to assert early termination on rating arrival, (3) confirm integrator has deployed decoder c705b20ed800 with the spotlight pinned.py branches. After those three line changes the feature complies with every listed law, the pin contract, and all prior pins recompute identically.

**Findings**  
<medium> spotlight.py:1158 (one_per_channel_day facts): build crossing midnight ET between pool() and package_for() measures a different day than facts["day"] (concrete input: ctx.now=2026-11-13T23:59:59 then advanced by 62 s wait).  
<medium> spotlight.py:1100 (scorer wait loop): fixed poll count can sleep full duration even after rating appears on poll 2 (test uses mock.sleep but does not verify early exit).  

SHIP: yes with conditions