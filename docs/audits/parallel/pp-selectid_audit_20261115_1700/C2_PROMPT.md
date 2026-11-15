# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_1700
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 39 s finish=stop usage in 6910 / out 852 usd_reported=0.021523 usd~0.056 (upper-bound price)

**CODE AUDIT: pp-selectid-20261115_1700 (RULING 117 join moments)**

**Summary**  
The diff extracts the candidate-moment selection for the join table into `join_moments()`, replaces the previous inline list-building logic in `build()`, and adds two targeted tests. The new logic implements the exact ordering and filtering described in the ruling and the 16:54 replay analysis: hook first, writer's viable moments, then cleared-pool moments preferring fresh channels before rank-order repeats, while excluding any moment that `lineup_ok` could never accept beside the hook (same video, not clip-eligible, doomed). The join table, `join_table()` question, cache, search, verdicts, and all downstream logic are untouched. All existing tests (including the 40-suite regression), mutation families (K1-K9, J1-J14), and the v2f reference continue to pass.

**Compliance with Governing Laws**  
- **SENTENCE LAW, ONSET/TAIL, L-b EDGE WORDS WHOLE, L-c DISSENT IS RIGHT, L-e PUNCTUATED BEFORE READ, L-g WRITTEN FORMS, L-h TEXT READ AS SPOKEN, L-k ONE CANONICAL FORM**: No transcript, punctuation, boundary, fade, or word-level logic touched. Compliant.  
- **SELECTION LOCK, SNAP LIMIT, NEIGHBOUR**: Selection locks and cut points are set upstream; this stage only chooses which already-locked moments may participate in a coherence search. No recomputation of first/last words. Compliant.  
- **L-f CHANNELS FIRST / L-i THE CLAIM IS THE EVENT**: This change is downstream of cluster selection. The channel-first ordering inside the join candidate list is orthogonal and does not alter cluster formation or claim derivation. Compliant.  
- **CREDITS, L-a SIGN-OFF NAMES ALL, L-d PROTECTED PREVIEW, L-j RELEASE IS AUTHORISED ON THESE BYTES, LAW 22 (v2f byte-identical)**: No renderer, credit card, voice-over, preview reference, attestation, or delivery path modified. The protected 2026-11-11 preview and v2f continue to render identically. Compliant.  
- **M1 (Smallest diff; no new renderer, compositor or selector), M12 FAIL CLOSED, LAW 20 / M2**: The added function is a pure extraction of the previously inline (and buggy) candidate list. It does not add a new selection algorithm, only makes the existing rule explicit, testable, and correct. No gate was relaxed; impossible moments are now simply omitted from the search space so that viable line-ups can still be found within the JOIN_MOMENTS_MAX cap. The change is the minimal surgical fix required to make the ruling work. Compliant.  
- **L-l A MODEL REPLY COUNTS ONLY WHOLE**: No model calls or JSON validation paths touched. Compliant.

**Findings**  
[P3] Docstring for `join_moments` repeats the full ruling text; a reference to the canonical ruling document plus a one-sentence summary would be cleaner.  
[P2] `can()` predicate duplicates the clip-eligibility and video-id checks already present in `lineup_ok`. While currently identical, a future change to one without the other would be a maintenance hazard. Consider a shared helper (`can_stand_beside_hook(m, hook_video, doomed)`) used by both.  
[P3] The nested `bool(((m.get("eligibility") or {}).get("clip") or {}).get("ok"))` is defensively correct but visually noisy; a small helper `is_clip_eligible(m)` would improve readability without changing semantics.  
[P3] Test `test_the_table_holds_only_moments_that_can_stand_beside_the_hook_a_new_channel_first` has a very long name; consider splitting into two shorter tests (one for exclusion, one for channel-first ordering).  

All tests, mutation coverage, and regression gates pass. The fix correctly resolves the zero-line-up problem without loosening any join law or violating any governing constraint.

**P1_OR_WORSE: 0**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 51 s finish=stop usage in 7326 / out 1753 usd_reported=0.002290 usd~0.048 (upper-bound price)

# Code Audit: pp-selectid-20261115_1700 (C1_STEP)

## Scope
Review of `pipeline/package.py` (`join_moments` new function, `build` call-site change) and `tests/package/test_medley.py` (2 new tests).

## Findings

### [P2] `join_moments` does not enforce the "second pass" filter from RULING 117(2)
The RULING 117(2) order defines the eligible pool as: *"the hook and the clips that passed step A from both vendors, **the second pass** and CUTTABLE"*. The new `join_moments` function filters on:
- `x != h` (not the hook)
- `x not in doomed`
- `m["video_id"] != hv` (not the hook's own video)
- `eligibility.clip.ok` (clip-eligible)

It does **not** explicitly check that the moment passed "the second pass" (i.e., survived the second vendor's step A). The docstring claims this is covered by `cleared` ("from `cleared`: step A from both vendors, the second pass, CUTTABLE"), which implies `cleared` is pre-filtered. However, the old inline code also used `cleared` without an explicit second-pass check, so this is not a regression. That said, if `cleared` ever contains moments that failed the second pass (e.g., due to a future refactor or a bug in the clearing step), `join_moments` would silently include them. The function's contract relies entirely on the caller's invariant about `cleared`. This is a latent fragility, not a current bug, but worth a comment or an assertion.

**Recommendation:** Add a brief comment in `join_moments` stating that `cleared` is assumed to contain only moments that passed both vendors' step A and the second pass, or add a debug assertion.

### [P3] `can()` helper accesses `cleared[x]` without a guard, but `x` is always in `cleared`
In `join_moments`, the `can(x)` helper does `m = cleared[x]`. The callers ensure `x` is in `cleared`:
- `own` list comprehension: `x in cleared` is checked.
- The `for x in sorted(...)` loop iterates over `cleared` keys.

So this is safe. No action needed, but a defensive `cleared.get(x)` would make the function more robust if ever called with a different contract. Nit only.

### [P3] Channel-diversity ordering: `chans` set is mutated during iteration
```python
chans = {cleared[x]["channel_id"] for x in [h, *own]}
first, then = [], []
for x in sorted(...):
    (then if cleared[x]["channel_id"] in chans else first).append(x)
    chans.add(cleared[x]["channel_id"])
```
The `chans` set is updated as moments are added. This means a moment's channel is considered "already in the set" if *any earlier moment in the sorted iteration* (whether in `first` or `then`) is from that channel. This is the intended behavior per the spec: *"one moment of each channel not yet in the set first, then the others in rank order."* The test `test_the_table_holds_only_moments_that_can_stand_beside_the_hook_a_new_channel_first` confirms this: `e1` (E, rank 90) goes to `first` because E is new; `e2` (E, rank 80) goes to `then` because E is now in `chans`. This is correct and deterministic. No issue.

### [P3] `JOIN_MOMENTS_MAX` is referenced but not defined in the diff
The constant `JOIN_MOMENTS_MAX` is used in `join_moments` and was used in the old inline code. It is presumably defined elsewhere in `package.py` (not in the diff). This is fine; no action needed.

### [P3] Test `test_the_writers_own_picks_join_the_table_only_when_they_can_stand_beside_the_hook` does not test the `doomed` parameter's interaction with `own`
The test checks `doomed={"x"}` where `x` is in `angle["moments"]`. This is good. However, it does not test a doomed moment that is *not* in `angle["moments"]` but is in `cleared`. The `can()` function checks `x not in doomed` for all moments, so this is covered by the general logic. The test is sufficient for the stated purpose.

### [P3] No test for the case where `own` is empty
If `angle["moments"]` contains only the hook (or no other cleared moments), `own` is empty. The function should still work: `chans` = {hook's channel}, and the rest of the pool is ordered by channel diversity. This is implicitly covered by the first test (where `own` = ["x", "y"] is non-empty) and the general logic. A dedicated test would be nice but not required.

### [P3] The `build` call-site change is minimal and correct
The old inline code:
```python
own_ = [x for x in angle["moments"] if x != angle["hook"] and x in cleared and x not in doomed]
rest_ = sorted((x for x in cleared if x not in doomed and x != angle["hook"] and x not in own_),
               key=lambda x: (-cleared[x].get("rank_score", 0), x))
jids = ([angle["hook"]] + own_ + rest_)[:JOIN_MOMENTS_MAX]
```
The new code:
```python
jids = join_moments(angle, cleared, doomed)
```
The new function adds two filters the old code lacked:
1. `m["video_id"] != hv` (not the hook's own video)
2. `eligibility.clip.ok` (clip-eligible)
3. Channel-diversity ordering for the `rest` portion.

These are the intended changes per

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261115_1700 (RULING 117 (2)'s set: join_moments)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0); deepseek-v4.1-flash ran out of tokens (finish=length, no answer), so Grok
was asked (P1_OR_WORSE: 0). glm's breaker is open. Cycle 1: $0.0272 vendor-reported. No P1.

P2s, each checked against the code, NOT changed:
- qwen "join_moments relies on its caller's `cleared` holding only the order's pool (step A from both vendors, the
  second pass, CUTTABLE)": it is build()'s own `cleared`, unchanged, the same dict the landed inline fill read and the
  search reads (build() passes it to search_lineups as by_id, pipeline/package.py:3319 and 3403); the docstring names
  the contract. Not a regression.
- Grok "can() repeats lineup_ok's clip-eligibility and video checks; the two could drift": every line-up still goes
  through lineup_ok in the search (pipeline/package.py:2057), so a drift never loosens a line-up in either direction:
  were lineup_ok ever looser, the table would hold fewer moments than it could (a candidate missed, never a looser
  line-up); were it stricter, the table would hold moments the search cannot use (the cost this fix removes, never a
  pass). A shared helper would move code inside lineup_ok, an unchanged guard used at three sites (lineup_for,
  swap_lineup, search_lineups); the smallest diff (M1) keeps it where it is.

P3s noted: the docstring's length; the nested eligibility expression (lineup_ok's own truthy test, None-safe); the long
test names; an empty `own` (covered: join_moments with doomed={"x"} leaves the writer no other moment -> ["h", "q"]).

CHANGED AFTER CYCLE 1 (in cycle 2's diff): ONE TEST, no code. The full mutation run, finished after cycle 1's diff was
taken, showed K9 ("build() calls join_moments without doomed") SURVIVED: no test put a moment doomed in an earlier
angle before a later angle's table. New: test_a_moment_doomed_in_an_earlier_angle_never_joins_a_later_angles_table
(angle 1 dooms x through the exclusion gate; angle 1's table is h, x, y, w, z; angle 2's is h, z, w, y, never x).
16 tests in TestRuling117JoinSearch. Mutations after a control run: 23 of 23 killed (J1-J14 and K1-K9: the hook's own
video allowed, a clip-ineligible moment allowed, rank only, a new channel's second moment counted as new, a doomed
moment allowed, the writer's picks unfiltered, no cap, the build's old fill, the build passing no doomed).


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261115_1700/C2_STEP.diff (90 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 7a058ff..fc9cd76 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -1936,6 +1936,30 @@ def reorder(segs, bad_pairs, judged, repeat_ok=False):
   6 |      return best[1] if best else None
   7 |  
   8 |  
   9 | +def join_moments(angle, cleared, doomed=frozenset()):
  10 | +    """RULING 117 (2): the moments an angle's join table is asked of -> their ids, the hook first: "the moments that
  11 | +    can be in a line-up for an angle" (from `cleared`: step A from both vendors, the second pass, CUTTABLE; not
  12 | +    doomed), at most JOIN_MOMENTS_MAX. lineup_ok's own rules bound the set: every clip is clip-eligible, and every
  13 | +    segment has its own video (one channel per segment, and L-y 4's supply exception still needs a video per segment),
  14 | +    so never a moment of the hook's own video. Order: the hook, its writer's other moments, then the rest of the pool by
  15 | +    rank score, one moment of each channel not yet in the set first (the 16:54 replay: a rank-only fill spent the
  16 | +    table on the hook's own video)."""
  17 | +    h = angle["hook"]
  18 | +    hv = cleared[h]["video_id"]
  19 | +
  20 | +    def can(x):
  21 | +        m = cleared[x]
  22 | +        return x != h and x not in doomed and m["video_id"] != hv and \
  23 | +            bool(((m.get("eligibility") or {}).get("clip") or {}).get("ok"))
  24 | +    own = [x for x in angle["moments"] if x in cleared and can(x)]
  25 | +    chans = {cleared[x]["channel_id"] for x in [h, *own]}
  26 | +    first, then = [], []
  27 | +    for x in sorted((x for x in cleared if can(x) and x not in own), key=lambda x: (-cleared[x].get("rank_score", 0), x)):
  28 | +        (then if cleared[x]["channel_id"] in chans else first).append(x)
  29 | +        chans.add(cleared[x]["channel_id"])
  30 | +    return ([h] + own + first + then)[:JOIN_MOMENTS_MAX]
  31 | +
  32 | +
  33 |  def join_table(router, ms, ctx, writer_vendor, writer_family=None, cache=None, seed=7):
  34 |      """RULING 117 (2): the JOIN TABLE. The clips-alone verdict's own join question (JOIN_QUESTION) asked ONCE per ordered
  35 |      pair of `ms` (the angle's hook first, then its other moments; at most JOIN_MOMENTS_MAX; the hook is never B), one
  36 | @@ -3267,12 +3291,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  37 |              dropped, n_lineup, swapped, filled = set(), 0, None, None
  38 |              jt, a_ratings, ext = {}, {}, angle            # RULING 117: this angle's join table; its clips' ratings
  39 |              if candidate is None and angle["hook"] in cleared and angle["hook"] not in doomed:
  40 | -                # the moments that can be in its line-up: its hook, its writer's other moments, then the rest of the
  41 | -                # cleared pool (step A from both vendors, the second pass, CUTTABLE) by rank score; at most 8
  42 | -                own_ = [x for x in angle["moments"] if x != angle["hook"] and x in cleared and x not in doomed]
  43 | -                rest_ = sorted((x for x in cleared if x not in doomed and x != angle["hook"] and x not in own_),
  44 | -                               key=lambda x: (-cleared[x].get("rank_score", 0), x))
  45 | -                jids = ([angle["hook"]] + own_ + rest_)[:JOIN_MOMENTS_MAX]
  46 | +                jids = join_moments(angle, cleared, doomed)  # the moments that CAN be in its line-up
  47 |                  ext = dict(angle, moments=jids)           # the search's angle: the writer's order first
  48 |                  jms = [cleared[x] for x in jids]
  49 |                  jt, jt_err = join_table(router, jms, ctx, writers_v, writers_f, cache=join_cache)
  50 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  51 | index b00f780..1adf4a6 100644
  52 | --- a/tests/package/test_medley.py
  53 | +++ b/tests/package/test_medley.py
  54 | @@ -1921,6 +1921,35 @@ class TestRuling117JoinSearch(unittest.TestCase):
  55 |          rig.run()
  56 |          self.assertEqual((len(rig.join_calls[0]), rig.join_calls[0][:3]), (8, ["h", "m0", "m1"]))
  57 |  
  58 | +    def test_the_table_holds_only_moments_that_can_stand_beside_the_hook_a_new_channel_first(self):
  59 | +        """The 16:54 replay: never the hook's own video, never a clip-ineligible moment; after the writer's picks, a
  60 | +        moment of a channel not yet in the set comes before a second moment of a channel already in it, whatever their
  61 | +        rank scores."""
  62 | +        ms = [pm("h", "A", 12.0, vid="V1"), pm("x", "B", 14.0), pm("y", "C", 13.0),
  63 | +              pm("a2", "A", 13.0, rank=99.0, vid="V1"),                       # the hook's own video: never
  64 | +              pm("n", "E", 13.0, rank=99.0, clip=False),                      # not clip-eligible: never
  65 | +              pm("b2", "B", 13.0, rank=50.0),                                 # B is in the set already: after...
  66 | +              pm("d", "D", 13.0, rank=1.0),                                   # ...the new channel D
  67 | +              pm("e1", "E", 13.0, rank=90.0), pm("e2", "E", 13.0, rank=80.0)]   # E: its first new, its second not
  68 | +        rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None], joins={})
  69 | +        rig.run()
  70 | +        self.assertEqual(rig.join_calls, [["h", "x", "y", "e1", "d", "e2", "b2"]])
  71 | +
  72 | +    def test_the_writers_own_picks_join_the_table_only_when_they_can_stand_beside_the_hook(self):
  73 | +        c = {m["moment_id"]: m for m in [pm("h", "A", 12.0, vid="V1"), pm("w", "A", 13.0, vid="V1"),
  74 | +                                         pm("z", "C", 13.0, clip=False), pm("x", "D", 13.0), pm("q", "E", 13.0)]}
  75 | +        angle = {"hook": "h", "moments": ["h", "w", "z", "x"]}
  76 | +        self.assertEqual(PK.join_moments(angle, c), ["h", "x", "q"])
  77 | +        self.assertEqual(PK.join_moments(angle, c, doomed={"x"}), ["h", "q"])            # a doomed moment: never
  78 | +
  79 | +    def test_a_moment_doomed_in_an_earlier_angle_never_joins_a_later_angles_table(self):
  80 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 14.0), pm("w", "E", 14.0)]
  81 | +        rig = Rig(ms, [["h", "x", "y"], ["h", "x", "z", "w"]], [(True, [], None, Rig.LINE)] * 2, [None, None],
  82 | +                  excluded={"x"}, joins={})
  83 | +        out = rig.run()
  84 | +        self.assertIn("'x': 'exclusion'", out["tried"][0]["why"])                     # angle 1 dooms x
  85 | +        self.assertEqual(rig.join_calls, [["h", "x", "y", "w", "z"], ["h", "z", "w", "y"]])   # equal ranks: by id
  86 | +
  87 |      def test_no_table_or_an_empty_one_is_the_build_as_before(self):
  88 |          ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
  89 |          for joins in (None, {}):
  90 | 
```

---

pp-selectid: RULING 117 (orchestrator 16:24 ET Nov 15), THE JOINS: SEARCH, DO NOT LOOSEN; (2)'s set of moments.
Files: pipeline/package.py (join_moments, NEW; build()'s one call of it), tests/package/test_medley.py.

THE ORDER, verbatim: "(2) BUILD THE JOIN TABLE: for the moments that can be in a line-up for an angle (the hook and the
clips that passed step A from both vendors, the second pass and CUTTABLE; cap 8 moments an angle), ask ONCE per ordered
pair ...". The join law does NOT move (one bridge); the full verdicts still decide.

WHY: the landed table (audit 20261115_1632, commit 2d2819c3) filled its 8 moments with the hook, the writer's picks,
then the cleared pool by rank score. Replayed on today's builds 8-12 (commit bb8a842c), zero of 10 angles reached a
line-up: 7 of today's 14 cleared moments are of the hooks' own video (one Simply Bitcoin video), and lineup_ok never
lets two segments share a video, so most of each table was moments that can never stand beside that hook.

THE CHANGE: join_moments(angle, cleared, doomed) -> ids, the hook first. It replaces the inline fill in build() at the
same call site (pipeline/package.py:3294); the table (join_table), the search and the verdicts are unchanged.
- A moment is in the set only when it CAN be in a line-up with this hook under lineup_ok's own rules: not the hook,
  not doomed, NOT of the hook's own video, and clip-eligible (eligibility.clip.ok truthy: lineup_ok's own test).
- Order: the hook; the writer's other moments (the writer's order, the same filter); then the rest of the cleared
  pool by rank score (ties by id), one moment of each channel not yet in the set first, then the others in rank
  order. At most JOIN_MOMENTS_MAX (8).

UNCHANGED GUARDS (not in the diff hunks):
- lineup_ok, pipeline/package.py:1591-1619: every clip clip-eligible (1602-1603); one segment per channel, or
  (repeat_ok, L-y 4's supply exception) one channel twice with every segment its own video (1604-1607).
- search_lineups, pipeline/package.py:2031: the hook is the angle's own hook, always first; every candidate goes
  through lineup_ok (2057) with LY_MAX_BRIDGES (pipeline/package.py:243, = 1); build() passes it
  frozenset(dropped | doomed) (3319, 3403), so a doomed or dropped moment never enters a line-up either way.
- join_table, the join question, JOIN_CACHE, medley() / coherence() and their floors: not touched.

TESTS (test_medley TestRuling117JoinSearch, 15): the build-level fill (a moment of the hook's own video and a
clip-ineligible moment never join; a new channel's first moment comes before a second moment of a channel already in
the set, whatever their rank scores; a new channel's second moment counts as a channel already in the set); the
earlier cap test; join_moments directly (the writer's own picks join only when they can stand beside the hook; a
doomed moment never). All 40 suite files pass. Mutations after a control run: the fill (K1-K9) and J1-J14.

PLEASE CHECK: (1) that the filter removes ONLY moments lineup_ok could never accept beside this hook, so the search
loses no line-up it could have found; (2) that the order is as stated and deterministic; (3) that nothing about the
join law, the table's question, its cache or the verdicts moved; (4) the tests.


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


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
