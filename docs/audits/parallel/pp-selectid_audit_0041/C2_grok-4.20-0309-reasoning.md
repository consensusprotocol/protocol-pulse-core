# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 32 s finish=stop usage in 18515 / out 1293 usd~0.125 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-0041**

1. WHAT DID THEY CATCH THAT YOU MISSED?
Qwen's <critical> on the synthetic (5, None) in _can_open(pending_verdict=True) was the largest gap in my Cycle 1 reasoning; I had only noted the pending_verdict path as "mostly inert" and missed how it could leak into medley if the call site ever changed. GLM's <high> on hook_trim(m) vs. post-snap v (and the TRIM_MARGIN_S interaction) was also missed — I had not traced the exact order of target=… then if P.hook_trim(v) after snap(). Grok's observation that 'now' was declared but unused in next_attempt was overlooked. The consensus correctly identified that the defer-only spotlight path plus the new test (score=3.0 refused, medley never defers) closes the L-m hole I had understated.

2. WHERE DO YOU AGREE OR DISAGREE?
- Qwen critical on pending_verdict: Partially agree on the original risk; disagree that the merged version still violates L-m. The synthetic 5 is gone, defer is spotlight-only, _can_open now passes the real verdict to SA.opener(..., moments=True), and test_stand_alone.py:304-310 plus TestRuling94HookOpeners explicitly verify fail-closed for medley and for score=3.0. The "leak into sealed pin" scenario is refuted.
- GLM high on snap/trim variant: Agree on the original ordering problem. The fixed pool() (spotlight.py:129,142) now sets target from original m but re-evaluates P.hook_trim(v) on the snapped text and refuses the variant if unusable. The "Bitcoin x." test (test_medley.py:433) and snap_rig case (test_spotlight.py:479) cover it; backward-snap changing the first word is intentional per ruling 94(a) ("the new first word is judged").
- Grok medium on unused 'now' and P.utc_z: Fully agree. Both are resolved (age_h now computed, P is module-level import).
- GLM medium on rs[0] for published_at/channel_name: Agree — still present.
- Consensus on refuted snap-prepend and affirmed() moments=True: Agree; evidence in stand_alone.py:251 and eligibility test matches ruling 60.

3. NEW FINDINGS FROM THIS REVIEW
<medium> spotlight.py:182 (state inner func): rs[0] for pub = P.utc_z(...) and rs[0].get("channel_name") with no check that every row in the video_id group agrees. Concrete input: two rows for video_id="v1", one with published_at="2026-11-13T18:00:00Z", another with "2026-11-14T09:00:00Z" (re-ingest) yields nondeterministic expires_at and age_h. Test data happens to be consistent so passes, but the grouping (by_vid.setdefault) only guarantees same video_id.
<medium> spotlight.py:193: datetime.strptime(pub, "%Y-%m-%dT%H:%M:%SZ") after P.utc_z. If utc_z ever returns a datetime object, a string with fractional seconds, or +00:00 instead of Z, ValueError crashes the report (caught by proof_ledger try/except but produces {"error":...} instead of the ruling-95 facts). Test uses clean +00:00 that utc_z normalizes, so not triggered.
<low> package.py:62 and :65: opens = lambda: defer or SA.opener(...) is evaluated up to twice per call (elig and the final if). Side-effect free here but duplicates the scorer call when defer=False and reasons=={"opener"}.

No violations of L-m (no synthetic pass reaches a sealed pin), SNAP LIMIT (trim only inside heard gap, onset re-checked), SELECTION LOCK (trim variant sits beside original, one video at most once), or L-j byte fidelity. All new paths still route through stand_alone.opener / check_edl / usable.

4. REVISED SCORES
| Subsystem                  | Cycle 1 | Cycle 2 | Why changed |
|----------------------------|---------|---------|-------------|
| pending_verdict / defer    | high    | medium  | Synthetic 5 removed; defer is spotlight-only, tests prove L-m preserved for medley and score<4 |
| hook_trim + snap ordering  | high    | low     | Explicit re-check on post-snap v plus TRIM_MARGIN_S; test coverage added |
| next_attempt / ruling 95   | medium  | medium  | 'now' now used for age_h; rs[0] assumption and strptime fragility remain |
| stand_alone opener + check_edl | low  | low     | Matches integrator exactly; FIRST_SECOND/THIRD split and test matrix comprehensive |
| overall L-m / fail-closed  | high    | low     | Highest-risk path closed by consensus fixes |

5. FINAL PRIORITY LIST
P0 CRITICAL: none
P1 HIGH: none
P2 MEDIUM:
- spotlight.py:182 — rs[0] metadata assumption (add explicit agreement check or use max published_at)
- spotlight.py:193 — brittle strptime on utc_z output (replace with fromisoformat + tz handling)
P3 LOW: package.py:62 double opens() lambda (cache the result).

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
Replacing the hardcoded (5, None) with a spotlight-only defer flag that never assumes a score, combined with the explicit THIRD pronoun gate in stand_alone.opener and the re-check of hook_trim(v) after snap, simultaneously satisfies ruling 94(a/b), L-m, and the integrator's render change.

7. PRODUCTION READY?
Yes with conditions: (1) fix the rs[0] metadata fragility in next_attempt:182 (or document that adapter rows are guaranteed consistent), (2) make expires_at calculation robust to any ISO datetime string or object that P.utc_z may emit. These are report-only issues; the pin-sealing logic is now solid. SHIP: yes with conditions.