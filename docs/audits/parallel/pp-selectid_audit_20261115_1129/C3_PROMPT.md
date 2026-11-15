# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_1129
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 502 s finish=stop usage in 21911 / out 12499 usd_reported=0.002229 usd~0.253 (upper-bound price)

# grok-4.20-0309-reasoning — CYCLE 2 AUDIT (pp-selectid, ruling 112's diagnosis driver)

Scope: the FIXED diff (hook112.py, 514 LOC; test_hook112.py, 257 LOC). Second review, with the other models' Cycle 1 findings in hand. Nothing in pipeline/ is touched, so the governing laws are inherited; the driver's job is to *read* records, so every finding below is about whether the reading matches what package.build and spotlight.build actually wrote.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting. In Cycle 1 I would have flagged the obvious things (read-only compliance, the Heimdall filter, the funnel ordering) but I did not have the following:

- **The `calls`-table heuristic (glm's F4 / consensus item 3).** The "a model was called" classification from `cost > 0 or seconds_hook >= 1` was genuinely fragile — a 0-cost cached call or a sub-second call would misclassify. The fix (query pp-ingest's own `calls` table, role IN ('hook','spotlight'), ts in (prev_event, this_event]) is the right one: it uses the producer's own record instead of a proxy. I missed that the *producer* had a better record than the event's `detail`. The consensus says "on the real data the classes move by one event (261 / 43 / 13)" — that's the heuristic being wrong at least once, which validates the fix.
- **The missing-reference resilience (consensus item 5).** `ref_moments` now records the error and continues; the calibration runs on the survivors. I would have called the old behavior "acceptable for a diagnostic" — it's better than that, it's now *correct* for a diagnostic whose deliverable is "is the rater drifting on the approved hooks": one unreadable reference must not silently shrink the calibration set to zero.
- **The cache-key `rsplit(":", 2)` fix (consensus item 4).** Moment ids contain `~` but the key is `<id>:<sha>:<version>`; a plain `split(":")` would break on any id with a colon. I missed the colon-in-id hazard entirely.
- **The "failure before rating" reordering (glm's F1, downgraded by glm itself to P2, then fixed anyway).** The consensus's argument is the one I now find decisive: `package.build` rates ONLY its openers (:2643-2645), so a record never holds both a failure and a rating for one id — but the driver's contract is "place each moment where the record says it stopped," and the record, not the invariant, is the evidence. The fix (every failure checked before `ratings`, lines 138-144) plus the new test (`test_a_failure_is_the_stop_even_beside_a_rating`, :578-581) plus mutation H16 is the right shape: the invariant is now *asserted by the code's order*, not assumed.

What they caught that I'd have missed, ranked: the `calls`-table fix, the reference resilience, the cache-key split, the failure-before-rating order.

## 2. WHERE DO I AGREE / DISAGREE?

**glm F1 (funnel ordering) — agree, and agree with its own downgrade.** The final order at :128-152 is: unusable → no_role → ad → reposted → failed → second(≠PASS) → trim_cut → onset(≠PASS) → ratings → onset+hp.error → onset → 3-channel → pool. Wait — re-read the diff. Lines 138-148:

```
elif mid in second and second[mid] != "PASS":   # every failure before the rating
elif mid in trim_cut:
elif mid in onset and onset[mid] != "PASS":
elif mid in ratings:
elif mid in onset and hp.get("error"):
elif mid in onset:
```

So failures (second≠PASS, trim_cut, onset≠PASS) are all checked before `ratings`. Good. But note: **`trim_cut` is checked before `onset` unconditionally, and `trim_cut` is a failure-only dict** — the consensus (item 1, glm's own self-correction) says `package.build` writes `trim_cut` only when no trimmed cut was reached. That semantics is still *undocumented in the driver* — the comment at :138-140 says "every failure before the rating: package.build rates ONLY its openers... so a record never holds both; were it to, the failure is the stop" — which covers the rating-vs-failure case but not the trim_cut-vs-onset case. If `trim_cut` ever recorded outcomes (a PASS), a moment that passed the cut but failed G17a would be placed at stage 3 with the trim_cut PASS text as its "why" — a wrong reason, right stage. [P3] — the stage is right either way, only the reason text could be wrong, and the record never holds it today. But the load-bearing assumption ("trim_cut is failure-only") deserves one comment word. Actually — check the test: `trim_cut={"t": "FAIL: no trimmed cut was reached"}` and the STAGES comment at :61 says "passed the second pass and CUTTABLE" for stage 3, which *is* the trim_cut+onset+can_open bundle. The comment at :138-140 plus the STAGES text together make the semantics recoverable. Downgrade my own nit to [P3], no change required.

**glm F2 / consensus item 8 (step-A detection by prose) — agree with the consensus's "no change."** The consensus's argument is correct: `spotlight.build`'s `stop(...)`

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 31 s finish=stop usage in 21471 / out 1198 usd_reported=0.036549 usd~0.137 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-20261115_1129 (hook112.py + test_hook112.py)**

1. WHAT DID THEY CATCH THAT YOU MISSED?
   GLM correctly flagged the original medley_trace elif ordering (ratings before failures) and the undocumented semantics of which prescreen dicts store only failures vs. all outcomes; I had only noted the 3-channel fallback path. Both GLM and Qwen highlighted the brittle string-matching for spotlight "step A" stops and the dead-first-alternative regex in reason_class; I missed both. Qwen's deep compliance check on the Heimdall-only chain construction and the calls-table read-only path in hook_pass surfaced subtleties I had treated as "obviously safe." The Cycle-1 consensus synthesis of the two P1s (now fixed) revealed an interaction between the inconsistent-record test and the best-per-moment roll-up that I had not exercised.

2. WHERE DO YOU AGREE OR DISAGREE?
   - GLM P1 (ordering) → fully agree; the fix (failures before ratings, new test at lines 578-581) eliminates the wrong-funnel risk.
   - GLM P2 (spotlight step-A prose match) → partially agree: still brittle (lines 177-178) but now explicitly justified by spotlight.build's stop() contract; the cited producer line makes it maintainable.
   - GLM regex redundancy (STAND_ALONE with…|STAND_ALONE) → agree it is dead code but harmless (same class); still present.
   - Qwen read-only / Heimdall-only analysis → agree on all points; the mode=ro URI, cache=None behavior, and heimdall_hook_chain filter are now rigorously tested.
   - Consensus "may open" clarification and mutation kills → agree; the STAGES comment and new inconsistent-record test close the loop.
   - Minor disagreement on heuristic fallback in hook_pass: the calls table path is definitive; the cost/seconds fallback is now correctly gated behind "has_calls" and tested.

3. NEW FINDINGS FROM THIS REVIEW
   [P2] reason_class still contains a dead left-alternative (hook112.py:75); re.search will always take the second branch for any STAND_ALONE string.  
   [P2] spotlight_trace stepa detection (lines 177-178) and reason_class step-A regex (lines 89-91) duplicate the exact strings produced by spotlight.build; a constant or structured flag would be safer.  
   [P3] resolve() depth limit of 4 (ledger_of:225) is arbitrary magic; a visited set would be clearer though functionally equivalent on current data.  
   [P3] report() and main() are long (70+ and 45+ LOC); the markdown generation mixes presentation with logic.  
   [P2] all_ratings folds spotlight hook_own entries with rater=None when no cache hit (lines 271-276); near_misses treats these as first-class but the test suite never asserts their rating parts match production own_rating logic.  
   [P3] SEEDS, LIMIT_USD, STOP_USD, and STAGES are module globals used both by production path and tests; a small dataclass would improve clarity.

4. REVISED SCORES
   | Subsystem              | Cycle 1 | Cycle 2 | Why changed |
   |------------------------|---------|---------|-------------|
   | Funnel / trace logic   | P1:2    | P2:2    | Ordering and inconsistent-record bugs fixed; only documentation/brittle-match issues remain |
   | Read-only & isolation  | P1:1    | P3:1    | All mutation tests pass; calls table and mode=ro now verified |
   | Calibration / router   | P2:2    | P3:2    | Heimdall filter, stop guard, no-cache, and ref-id isolation all tested |
   | Ledger / roll-up       | P2:1    | P2:1    | Tie-breaking and variant folding solid; new resolve depth nit |
   | Overall                | P1:3    | P2:3    | Fixes addressed every P1; residual issues are maintainability |

5. FINAL PRIORITY LIST
   [P2] hook112.py:75 — remove dead "STAND_ALONE with the clip scorer|" alternative (or make it a comment).  
   [P2] hook112.py:177-178 & 89-91 — replace string matching for step A with a structured sentinel if spotlight.build ever adds one; otherwise add a prominent comment citing the exact producer lines.  
   [P2] hook112.py:271 — add test coverage for spotlight hook_own entries that have no cache hit (rater=None path).  
   [P3] hook112.py:225, 73-86, 436-467 — replace magic depth, extract reason_class patterns to a constant dict, and split report() into smaller pure functions.  
   [P3] test_hook112.py:755 — the FakeRouter rate spy should also assert wf (writers family) avoidance.

   P1_OR_WORSE: 0

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   The single highest-leverage change is the unified 7-stage scale (STAGES + medley_trace/spotlight_trace) that forces every decision point in package.build and spotlight.build to map to one documented funnel bucket.

7. PRODUCTION READY?
   Yes with conditions: (a) remove or comment the dead regex alternative, (b) add the cited producer-line comment for step-A detection, (c) expand the near-misses test to cover a spotlight-only rating with no ca

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 104 s finish=stop usage in 24007 / out 3422 usd_reported=0.005703 usd~0.123 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_1129
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (as the "consensus" voice) correctly identified that the P1s raised by GLM and Qwen were either non-defects or already fixed in the diff. However, looking at the *current* code provided in the prompt, I missed a subtle **P2** issue in `medley_trace` regarding the `went_on` logic that GLM hinted at but didn't fully resolve, and a **P3** issue in `hook_pass` regarding the `last_ts` initialization.

Specifically:
*   **GLM** correctly identified that the ordering of `elif` checks in `medley_trace` was the critical path. The fix in the diff (checking failures before ratings) is correct.
*   **Qwen** correctly verified the read-only compliance and the Heimdall-only constraint.
*   **I missed:** The interaction between `went_on` and the `pool` check in `medley_trace` (lines 153-155). If `went_on` is False, the code checks `mid in pool` and `pre.get("cleared") is not None`. This logic is fragile if `cleared` is `0` (falsy) vs `None`.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM [P1] (Cycle 1):** "medley_trace stage ordering... ratings beats second_pass".
    *   **Agree with the fix:** The diff now checks `second`, `trim_cut`, and `onset` failures *before* `ratings`. This is correct because `package.build` only writes ratings for moments that passed the previous gates. If a record is inconsistent (has both a failure and a rating), the failure is the true stop. The new test `test_a_failure_is_the_stop_even_beside_a_rating` (line 578) validates this.
*   **Qwen [P1] (Cycle 1):** "a moment that passed G17a but was not rated... should be stage 4".
    *   **Disagree with the defect, Agree with the fix:** The consensus correctly noted that "may open" (Stage 4) requires `can_open`, which includes more than just G17a. A moment that passes G17a but fails the opener rule stops at Stage 3 ("cannot open"). The code at line 151-152 handles this: `elif mid in onset: out[mid] = (3, "cannot open...")`. This is correct.
*   **GLM [P2] (Cycle 1):** "spotlight step-A detection matches the text of `out`".
    *   **Agree:** This is a P2. The code at line 177 uses `str(why).startswith("step A")`. This is brittle but acceptable for a diagnostic tool if the producer (`spotlight.build`) is stable. The consensus noted this is "code-written" and "the record's only encoding". I agree it's a P2, not a P1.

## 3. NEW FINDINGS FROM THIS REVIEW

### [P2] F1 — `medley_trace`: `went_on` logic is fragile with `cleared=0`
**File:** `tests/package/hook112.py`, lines 125, 153-155.
```python
went_on = "second_pass" in pre                     # line 125
# ...
elif not went_on and mid in pool and pre.get("cleared") is not None and mid not in failed and \
        (pre.get("screened") or 0) > 0:            # line 153-154
    out[mid] = (2, "the medley ended at its 3-channel rule...", None)
```
If `pre["cleared"]` is `0` (an integer), `pre.get("cleared") is not None` is `True`. However, if the medley ended *before* any moments were cleared, `cleared` might be `0`. The condition `mid in pool` and `mid not in failed` would be true for moments that were screened but not cleared. The message says "fewer than 3 channels cleared step A". If `cleared` is 0, this is accurate. But if `cleared` is `None` (key missing), the condition fails, and the moment falls through to `elif mid in pool: out[mid] = (1, ...)`. This is correct behavior (it didn't even reach the 3-channel rule).
**However**, the variable name `went_on` is misleading. It checks for the *presence* of the `second_pass` key, not whether the medley actually *went on* to the second pass. If `second_pass` is an empty dict `{}`, `went_on` is `True`, but no moments passed. This is fine because the `elif mid in second` checks would fail for all moments, and they would fall through to the `pool` check.
**Verdict:** The logic is correct but the variable name `went_on` is a P3 nit. The condition `pre.get("cleared") is not None` is safe.

### [P2] F2 — `hook_pass`: `last_ts` initialization for the first event
**File:** `tests/package/hook112.py`, lines 340-349.
```python
last_ts = {}
for r in ev:
    # ...
    if has_calls:
        called = bool(db.execute("SELECT 1 FROM calls WHERE video_id = ? AND role IN ('hook', 'spotlight') "
                                 "AND ts > ? AND ts <= ? LIMIT 1",
                                 (r["video_id"], last_ts.get(r["video_id"], 0.0), r["ts"])).fetchone())
    # ...
    last_ts[r["video_id"]] = r["ts"]
```
For the first event of a given `video_id`, `last_ts.get(r["video_id"], 0.0)` returns `0.0`. The query checks for calls with `ts > 0.0 AND ts <= r["ts"]`. This is correct. It finds any call for that video up to the current event's timestamp.
**However**, if the `calls` table ha

## CLAUDE'S CYCLE 1 CONSENSUS
# C2 CONSENSUS — pp-selectid audit 20261115_1129 (ruling 112's diagnosis driver, tests/package/hook112.py)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0; the findings it tags P1 in its text it settles there) and glm-5.3-flash
(P1_OR_WORSE: 1). They disagree on a P1, so Grok was asked: grok-4.20-0309-reasoning (P1_OR_WORSE: 0, all P2/P3).
AUDIT TOTAL: $0.0527 vendor-reported (cap $1.00).

glm's P1 (F12): "the calibration's record_dir (proof/hook112/replies) is never created; if providers.Router does not
mkdir it, the first paid call dies". NOT A DEFECT. providers.Router._record (pipeline/providers.py:1286-1288, UNCHANGED)
does `os.makedirs(os.path.dirname(path), exist_ok=True)` before every recording. The path is
record_dir/<key[:2]>/<key>.json, so the first call creates record_dir and its subfolder. No real defect was found, so
there is no third cycle (ruling 107 (2)). THE CODE LANDED IS THE CODE AUDITED (FINAL.diff = C2_STEP.diff).

ACCEPTED, RECORDED FOR THE NEXT CHANGE TO THIS DRIVER. None changes a stage count, so the run's numbers stand:
1. glm F15 / Grok: reason_class's pattern order (the topic rule before the opener rule) deserves an assertion. Grok:
   its "STAND_ALONE with the clip scorer|" alternative is dead, because "STAND_ALONE" alone matches. It affects
   labels only.
2. glm F7: a test for the ledger-id fallback (a moment with no mined.ledger_moment_id resolves to its build id).
3. glm F4: spotlight_trace keeps `>` on a same-stage tie between pool.out and a folded span; funnel uses `>=`. Only
   the reason label of a tie can differ, never the stage.
4. Grok: a test for a spotlight rating with no cache record (rater None); a comment citing the spotlight.build lines
   that write "step A: ..." (the text the trace matches).
5. glm P3s: comments (the held-back predicates; the first event's call window is the video's whole history, which is
   the right attribution; went_on; the per-seed stop under the router's hard cap). The report prints hook_rows as a
   dict.

AGREED BY ALL: both cycle-1 P1 items are resolved (qwen's withdrawn: "may open" is can_open; glm's fixed, failures
before the rating). The calibration is Heimdall only (the hook list filtered on "heimdall/<family>"; hook_ratings makes
only that one kind of call), uses no cache, gets no shadow, uses its own ledger and stays under the router's $0.30.
Every read of pp-ingest's queue is mode=ro, and its ledger is only read.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261115_1129/C3_STEP.diff (84 lines)
```
   1 | diff --git a/tests/package/hook112.py b/tests/package/hook112.py
   2 | index fdba4ba..61686b4 100644
   3 | --- a/tests/package/hook112.py
   4 | +++ b/tests/package/hook112.py
   5 | @@ -398,6 +398,13 @@ def heimdall_hook_chain(router):
   6 |      return chain
   7 |  
   8 |  
   9 | +def registry(path=os.path.join(REPO, "pipeline", "channels.json")):
  10 | +    """The channel registry the builds' eligibility Context reads (tests/select_by_id/proof_saved_runs.REG is this same
  11 | +    file), read here so the driver needs no module from another test folder."""
  12 | +    with open(path) as f:
  13 | +        return json.load(f)
  14 | +
  15 | +
  16 |  def build_router(spend_path=SPEND, record_dir=None):
  17 |      import deadline_table as DT
  18 |      import providers as P
  19 | @@ -493,12 +500,11 @@ def main(argv=None):
  20 |      cal = {"refs": [], "runs": [], "skipped": a.no_calibration}
  21 |      if not a.no_calibration:
  22 |          import eligibility as E
  23 | -        import proof_saved_runs as PS
  24 |          refs = ref_moments()
  25 |          router = build_router(SPEND, os.path.join(OUT, "replies"))
  26 |          ok = [r for r in refs if not r.get("error")]
  27 |          cal = {"refs": refs, "chain": router.chain("coherence_verdict", "hook"),
  28 | -               "runs": calibrate(router, ok, E.Context(now, PS.REG)), "spent_usd": round(router.spent(), 6)}
  29 | +               "runs": calibrate(router, ok, E.Context(now, registry())), "spent_usd": round(router.spent(), 6)}
  30 |      for fname, obj in (("FUNNEL.json", fun), ("CALIBRATION.json", cal), ("NEAR_MISSES.json", nm),
  31 |                         ("HOOK_PASS.json", hp)):
  32 |          with open(os.path.join(OUT, fname), "w") as f:
  33 | diff --git a/tests/package/test_hook112.py b/tests/package/test_hook112.py
  34 | index cead604..57161c8 100644
  35 | --- a/tests/package/test_hook112.py
  36 | +++ b/tests/package/test_hook112.py
  37 | @@ -2,6 +2,7 @@
  38 |  """RULING 112's diagnosis driver (tests/package/hook112.py), offline: where each moment stopped on the way to the hook
  39 |  job (both paths), the distinct roll-up, the near misses and the part that holds a 3 back, pp-ingest's hook pass read
  40 |  from a database of the same shape, and the calibration's guards (Heimdall only, no cache, the stop)."""
  41 | +import io
  42 |  import json
  43 |  import os
  44 |  import sqlite3
  45 | @@ -253,5 +254,38 @@ class TestTheCalibration(unittest.TestCase):
  46 |          self.assertTrue(all(r["text"] for r in refs))
  47 |  
  48 |  
  49 | +class TestTheDriverEndToEnd(unittest.TestCase):
  50 | +    """main() itself, with the calibration on: the run of 11:52 ET Nov 15 died at an import its tests never reached
  51 | +    (proof_saved_runs, another test folder's module). The router and the one paid call are stubbed; everything else is
  52 | +    the driver's own path, writing into a temporary folder."""
  53 | +
  54 | +    def test_main_runs_the_calibration_and_writes_every_part(self):
  55 | +        from unittest import mock
  56 | +        import package as PK
  57 | +        asked = []
  58 | +
  59 | +        def rate(router, ms, ctx, wv, wf, cache="unset", seed=None):
  60 | +            asked.append((len(ms), cache, seed, ctx.channel("no-such-channel") is None))
  61 | +            return {m["moment_id"]: {"scroll": 4, "alone": 4, "setup": 4, "rating": 4, "why": "w",
  62 | +                                     "backend": "heimdall:qwen"} for m in ms}, None
  63 | +        with tempfile.TemporaryDirectory() as d:
  64 | +            proof, out = os.path.join(d, "proof"), os.path.join(d, "proof", "hook112")
  65 | +            os.makedirs(proof)
  66 | +            with open(os.path.join(proof, "HOOK_CACHE.json"), "w") as f:
  67 | +                json.dump({}, f)
  68 | +            db = TestTheHookPass().db(d)
  69 | +            with mock.patch.object(H, "PROOF", proof), mock.patch.object(H, "OUT", out), \
  70 | +                    mock.patch.object(H, "QUEUE_DB", db), mock.patch.object(H, "LEDGER", os.path.join(d, "none")), \
  71 | +                    mock.patch.object(H, "build_router", lambda *a, **k: FakeRouter(["heimdall:qwen"])), \
  72 | +                    mock.patch.object(PK, "hook_ratings", rate), mock.patch("sys.stdout", new=io.StringIO()):
  73 | +                self.assertEqual(H.main(["--since", "2026-11-13T16:15:00+00:00"]), 0)
  74 | +            cal = json.load(open(os.path.join(out, "CALIBRATION.json")))
  75 | +            self.assertEqual(sorted(os.listdir(out)), ["CALIBRATION.json", "FUNNEL.json", "HOOK_PASS.json",
  76 | +                                                       "NEAR_MISSES.json", "REPORT.md"])
  77 | +        self.assertEqual(asked, [(len(H.REFS), None, s, True) for s in H.SEEDS])   # every seed, no cache, a context
  78 | +        self.assertEqual([r["seed"] for r in cal["runs"]], list(H.SEEDS))
  79 | +        self.assertEqual(len(cal["refs"]), len(H.REFS))
  80 | +
  81 | +
  82 |  if __name__ == "__main__":
  83 |      unittest.main()
  84 | 
```

---

pp-selectid: RULING 112 (orchestrator 11:15 ET Nov 15), THE HOOK SCARCITY DIAGNOSIS. A new driver,
tests/package/hook112.py, and its tests. No bar, gate or routing changes; nothing in pipeline/ is touched.

THE ORDER, in short: before anyone touches the hook bar, find whether the supply is truly weak or the path to a hook
is too narrow. Heimdall only, cap $0.30. The parts:
(1) the funnel for the last 48 h of builds: pool -> allowed to open (with the exclusions by reason) -> rated by the
    hook job -> rated >= 4; how many DISTINCT moments were ever rated, and how many never were, and what removed them;
(2) calibration: the hook job as it stands today on the approved hooks (the protected preview, 37c5b5f5, 41f29b1f,
    the published 0c68b589); an approved hook rated below 4 means rater drift;
(3) the 10 best hooks of the 48 h with their parts and reason, and which part most often holds a 3 back from a 4;
(4) pp-ingest's hook-mining pass (ruling 80) for today's videos;
(5) a recommendation (written by hand from the outputs; not code).

THE DRIVER, READ-ONLY EXCEPT PART (2):
- build_records: every tests/package/proof/ledger_*/package.json and inputs.json since a cutoff.
- medley_trace / spotlight_trace place each moment on ONE scale of 7 stages ("in a pool" ... "rated >= 4") from each
  build's own record:
  - the medley: unusable, no_role, ad_read, reposted, prescreen.failed / second_pass / hook_onset / trim_cut, and
    hook_pool.ratings. These are written by package.build: the second pass at :2617, G17a, then
    `openers = {... if can_open(m)}` at :2643, hook_pool at :2666 (pipeline/package.py, UNCHANGED).
  - the spotlight: pool.out, and moments[*].stage / out / hook_own (spotlight.build :813, UNCHANGED). A stage-0 stop
    is a free screen unless it is step A's (ruling 109's ALONE gate stops at stage 0 BEFORE step A, :858). A
    widened span (pool.snapped) counts as the moment it came from.
- funnel: per build, and DISTINCT moments (a ~trim / ~tail variant is its moment) at their furthest stage over every
  build and both paths. A tie keeps the LATEST build's reason. Classes of the reasons for the never-rated.
- all_ratings + near_misses: every hook rating in the window (the medley's hook_pool.ratings; the spotlight's
  hook_own, completed from HOOK_CACHE.json by moment id), on TODAY's rule. That rule is own_rating, the lower of
  scroll and alone (ruling 61; package.hook_own :1383): an early record that stored a three-part rating is read on
  today's rule. One entry per moment, ranked by rating and then the sum of the parts. "Held back": among those
  rated 3, which part is at 3 (setup is shown apart; it is not in the rating since ruling 61).
- ledger_of / ledger_id: a build gives each re-anchored moment its OWN id (0 of 57 equal their ledger id in
  ledger_20261115_151621); mined.ledger_moment_id maps back, and snapped spans and variants resolve through it.
- hook_pass: pp-ingest's queue database opened with mode=ro (sqlite URI), its 'hooks' events (classed: rows or not,
  a model called or not), the given videos' events, their hook rows in pp-ingest's ledger (read), and how far each
  got in our builds (never_in_pool: the latest build's own inputs report: word-pass refusal, no re-anchor, or a
  duplicate).

THE PAID PART, (2) calibrate:
- package.hook_ratings (:863, UNCHANGED) with cache=None. _load_cache(None) is {} (:497; open(None) raises TypeError,
  caught) and _cache_put(None, ...) returns at once (:508), so the production HOOK_CACHE.json is neither read nor
  written.
- The approved hooks get ids "ref-<key>", so no cached rating can answer for them.
- Asked as production asks: avoiding package._writers(router)'s vendor and family, once per seed (7 is production's;
  8 and 9 show stability).
- The router (build_router) is providers.Router under heimdall_first, built DIRECTLY: not proof_ledger.build_router,
  so no ruling-86 shadow (Grok). Its own spend ledger is tests/package/proof/SPEND_H112.json, limit $0.30 (the
  order's cap); no call starts at or over STOP_USD $0.25.
- Its hook list (ruling 88, "coherence_verdict:hook", providers.Router.chain :794) is production's with every
  non-Heimdall back-end removed: heimdall_hook_chain keeps a back-end whose vendor is "heimdall/<family>" (that is
  how providers.HeimdallBackend names it), and refuses when none is left. Today's list is qwen, glm, deepseek;
  Grok is dropped.

TESTS: tests/package/test_hook112.py (12), offline. Both traces stage by stage. The roll-up's furthest stage, the
latest reason on a tie, and folded variants. The near misses on today's rule, folded, with the held-back counts. The
hook pass over a database and ledger of the same shape. The ledger-id resolution. A REAL Router built by
build_router: its hook chain is Heimdall only, qwen first, no Grok. The calibration's guards: no cache, production's
writers, every seed, no call at the stop, refusal without a Heimdall back-end, and the reference ids absent from
the production cache. 15 of 15 mutations killed after a control run (the unmutated copy passes all 12). Suites: 697
pass.

PLEASE CHECK: (1) that both traces place every moment where package.build and spotlight.build actually stopped it (the
cited lines); (2) the roll-up, the tie rule, and the ledger-id mapping; (3) the near misses' rule and the held-back
count; (4) that the calibration can reach no non-Heimdall back-end, no shadow, and no production cache or spend
ledger, and stops under the cap; (5) that the hook pass and every other read cannot write to pp-ingest's or the
main tree's files; (6) the tests.


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.


THIS THIRD CYCLE CHECKS THE FIX OF CYCLE 2'S REAL DEFECT: found at the first live run (11:52 ET Nov 15), after cycle 2, which did not raise it: main()'s calibration imported proof_saved_runs, a module of tests/select_by_id that is not on this driver's sys.path, so the run died (ModuleNotFoundError) before any router or paid call. The fix reads the same registry file directly (registry(): pipeline/channels.json, which is proof_saved_runs.REG), and a new end-to-end test runs main() with the calibration on (the router and the one paid call stubbed); a mutation restoring the import is killed


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
