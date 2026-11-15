# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_0910
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 40 s finish=stop usage in 7188 / out 2390 usd_reported=0.000519 usd~0.057 (upper-bound price)

# Audit: pp-selectid-20261115_0910 — C1_STEP.diff

Reviewed the diff, the finding, the guard analysis, and the tests against the stated laws (M1 smallest diff, M12 fail closed, LAW 20/M2, ruling 109/107/66/101/90).

## Findings

**[P2] The early-return record omits keys the :2587 return may carry — verify, don't assume.** The finding claims "the same keys" as the :2587 return, and the test `test_the_record_has_the_shape_the_rule_at_2587_returns` compares `set(gate) - {"ruling_109"}` to `set(late)`. But the :2587 return is built by the *later* code path, which may add keys conditionally (e.g. `current_levels`, `no_role`, `trimmed`, `reposted`, `scorer` — the diff's early return does include these, good). The risk: the :2587 path's `out` may include keys set *between* the gate and :2587 that the early return hardcodes differently (e.g. `prescreen` there is the *real* prescreen result, here a synthetic zeroed one). The test only compares one late-fail case (`REFERENT_OUTSIDE` on 2 of 4 moments) — if the :2587 `prescreen` dict ever carries extra keys (e.g. a non-empty `failed` or a non-None `parallel_101` in some other failure mode), the shapes diverge and `open_work`/readers see a different record. The test's single late case doesn't prove shape equality across all :2587 failure modes. Fix: either derive the early-return record from the same code that builds the :2587 return (extract a helper), or add a test asserting the :2587 return's key set is exactly the early return's key set minus/plus `ruling_109` for *several* failure modes. Not a blocker because the readers cited (`res["usable"]`, `res["prescreen"].get("cleared")`, `open_work` via `.get`, `CA.seed` via `record.get("tried") or []`) are all tolerant — but that tolerance is the only thing holding this.

**[P2] `n_usable` vs `len(ms)` inconsistency in the log line.** The early return logs `f"  {n_usable} usable, {len(ms)} in the pool after the free stages: {why_none}"` but `why_none` says "the pool spans {n_ch} channel(s)… a medley needs 3". The test `test_one_or_two_channels_ask_nothing` asserts `out["usable"] == 4` while `out["ruling_109"]["pool"] == 4` — i.e. usable == pool here. But in `test_the_channels_are_counted_after_the_free_stages`, `usable` is 5 while `pool` is 4 (the off-topic moment counts as usable but not in the pool? — actually `ms` should already have the no-role moment removed, yet the test asserts `"w" in out["no_role"]` and `usable == 5`). So `n_usable` (5) ≠ `len(ms)` (4) in that test, meaning the log line prints two different pool sizes and `why_none`'s "pool" (4) is `len(ms)`, not the usable count. That's coherent but confusing: "usable" includes no-role moments while "pool" excludes them. Confirm this matches the base's semantics at :2587 (where `why_none` presumably also counts only cleared/pool moments). If the base's :2587 message counts differently, the two `why_none` strings will disagree for the same underlying pool — a P3-level inconsistency, but the test pins the early-return wording, so any future wording alignment is a test change. Downgrade to P3 if the base wording is confirmed identical.

**[P3] `trims`/`trim_out`/`admitted` referenced in the early return but not shown in the diff context.** The early return reads `trims.items()`, `trim_out`, `admitted`, `no_role`, `current_levels(sources.values(), ctx)`. The finding says the gate sits "after the free stages: usable, reposted_once, scorer_pass, the no-role and trim rules, ad_read_out" — so these are all computed before the gate. Fine, but the diff hunk's context (lines 5–8) only shows `ad_read` being computed; a reviewer must trust the placement. The tests passing (10/10 mutations killed, 552+127 green) is the real evidence. Nit: a comment marking "gate: ruling 109, BEFORE any paid verdict" at the insertion point would prevent someone later inserting a paid call above it.

**[P3] `prescreen` synthetic record hardcodes `held_102: {"first": [], "second": []}`.** Correct for ruling 107's `open_work` (nothing asked → nothing held), and `CA.seed`'s `record.get("tried") or []` handles the missing `tried` key. But if `open_work` or any future reader does `record["prescreen"]["held_102"]["first"]` without `.get` on a *new* key added to the real prescreen record, the synthetic record silently diverges. The shape test (`set(gate["prescreen"]) == set(late["prescreen"])`) covers keys, good. No action needed; noting the coupling.

**[P3] The pre-existing candidate/KeyError defect (proof_ledger.py:484).** Correctly flagged, correctly not fixed (law K2, no candidate due today, all expire first). Agree it need not be fixed *in this change* — the gate's early return adds one more early-return path that skips `out["candidate"]`, but the finding already counts the existing :2587/:2590/:2681 returns, so this change adds no *new* exposure class; it's the sam

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 68 s finish=stop usage in 7772 / out 2251 usd_reported=0.002732 usd~0.057 (upper-bound price)

I have reviewed the diff for `pipeline/package.py` and `tests/package/test_medley.py` against the provided context, laws, and specific check requests.

### Analysis

**1. Subset Argument (Can the gate refuse a valid medley?)**
The gate checks `n_ch < 3` on `ms` (the pool after free stages). The later check at `:2587` checks `len({m["channel_id"] for m in cleared.values()}) < 3`.
*   `cleared` is a subset of `ms` (moments that passed Step A).
*   If `ms` has < 3 channels, `cleared` (being a subset) cannot have > 2 channels. Thus, if the gate triggers (`n_ch < 3`), the later check *would* also trigger (`cleared_channels < 3`).
*   Therefore, the gate does not refuse a pool that *could* seat a medley (i.e., a pool with >= 3 channels). It only refuses pools that are guaranteed to fail the later check.
*   **Verdict:** Correct. No P0/P1.

**2. Paid Calls Before Gate**
The gate is placed after `ad_read_out`, `scorer_pass`, `trim_variant`, `current_levels`, and `no_role` calculations.
*   `ad_read_out`: Free exclusion screen.
*   `scorer_pass`: Scoring is typically local/computational (unless it calls a model, but the context implies "free stages" precede this). The prompt states "free gates first... paid verdict only for what every free gate passed". The gate is *before* `step_a_plan` (which triggers Step A paid calls) and `confirm_ahead` (Ruling 101 paid calls).
*   The prompt explicitly states: "It ends here, before any paid verdict".
*   **Verdict:** Correct. No P0/P1.

**3. Record Shape and Readers**
The gate returns a dict with keys: `shape`, `packages`, `tried`, `unusable`, `usable`, `current_levels`, `no_role`, `ad_read`, `trimmed`, `reposted`, `scorer`, `prescreen`, `angles`, `takeaways`, `package`, `why_none`, `ruling_109`.
*   **`proof_ledger.py` readers:**
    *   `res["usable"]`: Present.
    *   `res["prescreen"].get("cleared")`: Present (value 0).
    *   `open_work`: Reads `prescreen.held_102` (present, empty) and `visual.unmeasured` (absent, but `open_work` likely handles missing keys or the prompt confirms "leaves no open work"). The prompt states: "The gate's record has held_102 empty and no 'visual', so it leaves no open work".
    *   `CA.seed`: Reads `record.get("tried") or []`. Present (empty list).
*   **Comparison to `:2587` return:** The prompt states the gate returns "the record the rule at :2587 returns". The test `test_the_record_has_the_shape_the_rule_on_the_cleared_moments_returns` verifies `set(gate) - {"ruling_109"} == set(late)`. This confirms structural equivalence.
*   **Verdict:** Correct. No P0/P1.

**4. Candidate Exclusion**
The gate condition is `if candidate is None and n_ch < 3:`.
*   If `candidate` is not None, the gate is skipped.
*   The prompt explains: "A build from a ruling-66 candidate returns its outcome in out['candidate']... The gate's record has no 'candidate', so a candidate build keeps its path, unchanged."
*   Test `test_a_build_from_a_candidate_keeps_its_own_path` verifies this.
*   **Verdict:** Correct. No P0/P1.

**5. Tests**
*   `test_one_or_two_channels_ask_nothing`: Verifies no paid calls (`screens`, `events`, etc. are empty) and correct `why_none`.
*   `test_the_channels_are_counted_after_the_free_stages`: Verifies that a moment failing a free stage (topic rule) is not counted in `n_ch`. The test adds a moment from channel "C" that fails the topic rule (implied by `no_role` check). The gate counts `n_ch` from `ms` (after free stages). If the "C" moment is removed by a free stage, it won't be in `ms`, so `n_ch` remains 2. The test asserts `ruling_109` channels is 2. This is correct behavior.
*   `test_the_record_has_the_shape...`: Verifies key parity with the late return.
*   `test_three_channels_are_screened_and_packaged_as_before`: Verifies the gate does *not* trigger for 3 channels.
*   `test_a_build_from_a_candidate_keeps_its_own_path`: Verifies candidate exclusion.
*   **Verdict:** Tests are comprehensive and correct. No P0/P1.

**6. Pre-existing Defect (KeyError in proof_ledger for candidate builds)**
The prompt flags a pre-existing defect: "The early returns before :2703 ... give a CANDIDATE build no out['candidate'], so proof_ledger.py:484 would raise KeyError outside its try."
*   The prompt asks: "Say whether you think it must be fixed in this change."
*   **Analysis:** This is a pre-existing bug in `proof_ledger.py` or `package.py`'s early returns for candidate builds. The current change *adds* another early return (the gate) but explicitly excludes candidate builds (`candidate is None`). Therefore, this change does *not* introduce the bug, nor does it fix it.
*   However, the prompt states: "No candidate is due today... Say whether you think it must be fixed in this change."
*   Since the change is specifically about the "free gates first" optimization for non-candidate builds, and the candidate path is explicitly u

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261115_0910 (the medley's ruling-109 channel gate)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0), glm-5.3-flash (P1_OR_WORSE: 0). Grok not asked (they agree). $0.0033
vendor-reported.

AGREED BY BOTH: the subset argument holds (`cleared` at :2562 is a filter of the gate's `ms`, so the rule at :2587
refuses every pool the gate refuses); nothing paid runs before the gate; the candidate exclusion is right; the
pre-existing candidate KeyError (proof_ledger.py:484) need not be fixed in this change.

EACH FINDING AND WHAT WAS DONE:

1. glm [P2] "the record's shape is tested against one late-failure mode only". NO CHANGE: the shape is not mode-dependent.
   The :2587 return is the `out` of ONE dict literal (pipeline/package.py:2563-2572 in the base), and its "prescreen" is
   a literal too (screened, cleared, failed, parallel_101, held_102, last_resort_87). Between :2563 and :2587 only log
   lines run (:2573-2586); nothing is added to `out`. Every failure mode that reaches :2587 returns the same keys.

2. glm [P2] "open_work may subscript the missing 'visual' key: verify". VERIFIED, AND NOW TESTED.
   tests/package/proof_ledger.py:150-154 reads `(res or {}).get("prescreen") or {}`, `pre.get("held_102") or {}` and
   `(res or {}).get("visual") or {}`: all tolerant. A NEW TEST,
   test_the_guard_finds_no_open_work_and_the_registry_no_line_up, runs the real proof_ledger.open_work on the gate's
   record (0: nothing asked or undone) and the real candidates.seed (no key added, no candidate).

3. glm [P2] "usable 5 vs pool 4 in the log line". NO CHANGE: intended. "usable" is package.usable's count (n_usable,
   :2528), which includes the moments the no-role rule later removes, as the base's own log line does
   (:2573 "{n_usable} usable, ... {len(no_role)} left out by the render's STAND_ALONE"); "pool" is what would reach step A.

4. glm [P3] "mark the gate so no paid call is inserted above it". Already there: the comment says "It ends here, before
   any paid verdict", and the test asserts no call of any kind (screens, events, hook, visual and medley calls empty);
   mutation C10 (the gate after a paid step A) is killed.

5. qwen [P3] "is n_usable defined?" Yes: pipeline/package.py:2528 `n_usable = len(ms)`, before the gate.

6. Both [P3] the pre-existing candidate KeyError (proof_ledger.py:484 reads o["candidate"] outside its try; the early
   returns before :2703 set none). TRACKED as an open item in the handoff, for its own change and audit. This change adds
   no exposure: candidate builds skip the gate.

THE CODE NOW: the same gate; test_medley.py gains the open_work / seed test (6 tests in TestRuling109Channels). Suites:
tests/package 553 pass. Mutations: 10 of 10 killed.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261115_0910/C2_STEP.diff (102 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 967f665..08c0035 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -2543,6 +2543,24 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
   6 |      #   video at most once, L-y 4)
   7 |      ad_read = ad_read_out(ms, sources)                # the exclusion screen's free part, BEFORE the angle is built
   8 |      ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
   9 | +    n_ch = len({m["channel_id"] for m in ms})
  10 | +    if candidate is None and n_ch < 3:
  11 | +        # RULING 109 (free gates first) on the medley's 3-channel rule (orchestrator 08:56 ET Nov 15: "one channel
  12 | +        # cannot make a medley ... run the SPOTLIGHT path"). Every later stage only removes moments (step A's `cleared`
  13 | +        # is a subset of this pool), so the same rule on the cleared moments below would refuse this pool anyway, after
  14 | +        # step A and ruling 101's confirm ahead were paid. It ends here, before any paid verdict; the spotlight (ruling
  15 | +        # 90) runs next as usual. A candidate build (ruling 66) keeps its own path: its outcome is out["candidate"].
  16 | +        why_none = (f"the pool spans {n_ch} channel(s) after the free stages: a medley needs 3; no paid verdict "
  17 | +                    f"(ruling 109)")
  18 | +        log(f"  {n_usable} usable, {len(ms)} in the pool after the free stages: {why_none}")
  19 | +        return {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable,   # out's shape
  20 | +                "current_levels": current_levels(sources.values(), ctx), "no_role": no_role, "ad_read": ad_read,
  21 | +                "trimmed": {k: v["moment_id"] for k, v in trims.items()}, "reposted": reposted,
  22 | +                "scorer": dict(scorer["record"], admitted=admitted, trims_affirmed=sorted(trims), trims_out=trim_out),
  23 | +                "prescreen": {"screened": 0, "cleared": 0, "failed": {}, "parallel_101": None,
  24 | +                              "held_102": {"first": [], "second": []}, "last_resort_87": {}},
  25 | +                "angles": [], "takeaways": [], "package": None, "why_none": why_none,
  26 | +                "ruling_109": {"channels": n_ch, "pool": len(ms)}}
  27 |      wv, wf = _writers(router)
  28 |      fb = first_bounds(router)
  29 |      plan = step_a_plan(router, ms, sources, ctx, wv, wf, store=store, cache=step_a_cache, **fb)   # RULING 101
  30 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  31 | index af68ac8..5e7aa2f 100644
  32 | --- a/tests/package/test_medley.py
  33 | +++ b/tests/package/test_medley.py
  34 | @@ -3817,5 +3817,67 @@ class TestTakeawayValueRow(unittest.TestCase):
  35 |          package_pin.to_pin(spk(dict(pk, gates=TestMedleyPackageAndPin().gates(pk))), "test")   # the right row: pins
  36 |  
  37 |  
  38 | +class TestRuling109Channels(unittest.TestCase):
  39 | +    """RULING 109 (free gates first) on the medley's 3-channel rule (orchestrator 08:56 ET Nov 15: "one channel cannot
  40 | +    make a medley ... run the SPOTLIGHT path"): a pool of fewer than 3 channels after the free stages ends the medley
  41 | +    before any paid verdict, with the record the rule on the cleared moments returns; 3 channels are screened and
  42 | +    packaged as before; a build from a ruling-66 candidate keeps its own path."""
  43 | +    ALL = ["h", "x", "y", "z"]
  44 | +
  45 | +    def pool(self, chans):
  46 | +        return [pm(mid, ch, 12.0 + i) for i, (mid, ch) in enumerate(zip(self.ALL, chans))]
  47 | +
  48 | +    def test_one_or_two_channels_ask_nothing(self):
  49 | +        for chans in ("AAAA", "AABB"):
  50 | +            rig = Rig(self.pool(chans), self.ALL, [], [])
  51 | +            out = rig.run()
  52 | +            self.assertEqual((rig.screens, rig.events, rig.hook_calls, rig.visual_calls, rig.medley_calls),
  53 | +                             ([], [], [], [], []), chans)                  # no step A, no call of any kind
  54 | +            n = len(set(chans))
  55 | +            self.assertEqual(out["why_none"], f"the pool spans {n} channel(s) after the free stages: a medley needs 3; "
  56 | +                                              f"no paid verdict (ruling 109)")
  57 | +            self.assertEqual((out["package"], out["usable"], out["prescreen"]["cleared"], out["ruling_109"]),
  58 | +                             (None, 4, 0, {"channels": n, "pool": 4}))
  59 | +
  60 | +    def test_the_channels_are_counted_after_the_free_stages(self):
  61 | +        off = dict(pm("w", "C", 12.0), text="The weather was lovely at the lake today.")   # a third channel, but no
  62 | +        rig = Rig(self.pool("AABB") + [off], self.ALL, [], [])                             # place under the topic rule
  63 | +        out = rig.run()
  64 | +        self.assertEqual((rig.screens, rig.events), ([], []))
  65 | +        self.assertIn("w", out["no_role"])
  66 | +        self.assertEqual((out["usable"], out["ruling_109"]), (5, {"channels": 2, "pool": 4}))
  67 | +
  68 | +    def test_the_record_has_the_shape_the_rule_on_the_cleared_moments_returns(self):
  69 | +        gate = Rig(self.pool("AABB"), self.ALL, [], []).run()
  70 | +        late = Rig(self.pool("ABCD"), self.ALL, [], [],
  71 | +                   a_fail={("xai", "y"): ["REFERENT_OUTSIDE"], ("xai", "z"): ["REFERENT_OUTSIDE"]}).run()
  72 | +        self.assertEqual(late["why_none"], "2 moments cleared step A from fewer than 3 channels")   # the rule, after
  73 | +        self.assertEqual(set(gate) - {"ruling_109"}, set(late))                                     # step A was paid
  74 | +        self.assertEqual(set(gate["prescreen"]), set(late["prescreen"]))
  75 | +        self.assertEqual(set(gate["scorer"]), set(late["scorer"]))
  76 | +
  77 | +    def test_the_guard_finds_no_open_work_and_the_registry_no_line_up(self):
  78 | +        import candidates as CA
  79 | +        import proof_ledger as PLG
  80 | +        gate = Rig(self.pool("AABB"), self.ALL, [], []).run()
  81 | +        self.assertEqual(PLG.open_work(gate, {}), 0)                        # ruling 107 (1): nothing asked or undone
  82 | +        reg = CA.new_registry()
  83 | +        self.assertEqual((CA.seed(reg, gate, "proof/ledger_x"), reg["candidates"]), ([], {}))   # ruling 66: none kept
  84 | +
  85 | +    def test_three_channels_are_screened_and_packaged_as_before(self):
  86 | +        rig = Rig(self.pool("ABCA"), self.ALL, [(True, [], None, Rig.LINE)], [None])
  87 | +        out = rig.run()
  88 | +        self.assertEqual(rig.screens[0], ("xai:grok", self.ALL))
  89 | +        self.assertIsNotNone(out["package"])
  90 | +        self.assertNotIn("ruling_109", out)
  91 | +
  92 | +    def test_a_build_from_a_candidate_keeps_its_own_path(self):
  93 | +        c = PK.load_candidate(TestRuling66Candidate().record())
  94 | +        rig = Rig(self.pool("AABB"), self.ALL, [], [], candidate=c)
  95 | +        out = rig.run()
  96 | +        self.assertEqual(rig.screens, [("xai:grok", self.ALL)])           # screened as before this gate
  97 | +        self.assertNotIn("ruling_109", out)
  98 | +
  99 | +
 100 |  if __name__ == "__main__":
 101 |      unittest.main()
 102 | 
```

---

pp-selectid, THE ORCHESTRATOR'S ORDER 08:56 ET Nov 15, item 2: "one channel cannot make a medley (channel rules), so
run the SPOTLIGHT path on it (ruling 109 free gates first, ruling 107 guard)". RULING 109 (21:30 ET Nov 14): free
gates first; a paid verdict only for what every free gate passed.

THE FINDING. The build driver (tests/package/proof_ledger.py, UNCHANGED) always runs the medley first (package.build),
then the spotlight (spotlight.build, ruling 90; proof_ledger.py:500). The medley pays step A on EVERY moment of its pool
(package.prescreen, pipeline/package.py:2554 in the base) and ruling 101's Grok confirm ahead beside it (:2548-2551)
BEFORE its 3-channel rule (:2587, UNCHANGED: `if len({m["channel_id"] for m in cleared.values()}) < 3:` -> why_none,
return out). This morning's 12-h pool is 63 moments from 2 channels, so the medley pays step A (and the confirm ahead)
on all of them and then refuses. The spotlight's own free gate (ruling 109: an ALONE score known below 4 never reaches
step A, pipeline/spotlight.py:855-862, UNCHANGED) asks only what passes it.

THE CHANGE (pipeline/package.py build(), after the free stages: usable, reposted_once, scorer_pass, the no-role and
trim rules, ad_read_out; before _writers / first_bounds / step_a_plan / confirm_ahead / prescreen): when the pool spans
fewer than 3 channels and the build is not from a ruling-66 candidate, build() returns at once with the record the rule
at :2587 returns (the same keys; prescreen: screened 0, cleared 0, failed {}, parallel_101 None, held_102 empty,
last_resort_87 {}), why_none "the pool spans N channel(s) after the free stages: a medley needs 3; no paid verdict
(ruling 109)", and "ruling_109": {"channels": N, "pool": the pool's size}.

WHY IT CHANGES NO OUTCOME. Nothing between the gate and :2587 adds a moment: `cleared` (:2562) is a subset of `ms`, the
pool at the gate. So the rule at :2587 refuses every pool the gate refuses; the gate only removes the paid calls before
it. The spotlight runs next as usual (proof_ledger.py:500), with its own free gates, and reads the same step-A cache.

WHY CANDIDATE BUILDS ARE LEFT OUT. A build from a ruling-66 candidate returns its outcome in out["candidate"] (set at
:2703, after this point), and proof_ledger's try_one reads it (tests/package/proof_ledger.py:484
`return o, o["candidate"]["class"], ...`, outside its try). The gate's record has no "candidate", so a candidate build
keeps its path, unchanged.

A PRE-EXISTING DEFECT, FLAGGED, NOT FIXED HERE (law K2). The early returns before :2703 (the rule at :2587, :2590 no
work_dir, the no-opener return, :2681, the no-hook return) give a CANDIDATE build no out["candidate"], so
proof_ledger.py:484 would raise KeyError outside its try. No candidate is due today: all are over 12 h old and expire
first (CA.expire, proof_ledger.py:380; this morning's build logged "RULING 66: no candidate is due"). Say whether you
think it must be fixed in this change.

THE GUARD. Ruling 107 (1)'s open_work (proof_ledger.py:146-155, UNCHANGED) reads prescreen.held_102 and visual.unmeasured.
The gate's record has held_102 empty and no "visual", so it leaves no open work, which is right: nothing was asked.
CA.seed (tests/package/candidates.py:61, UNCHANGED) reads record.get("tried") or []: the gate's record has none.

TESTS: tests/package/test_medley.py, class TestRuling109Channels (5), on the existing Rig (every model stubbed):
- one or two channels ask nothing (no step A, no call of any kind);
- the channels are counted after the free stages (a third channel whose only moment fails the topic rule is not counted);
- the record's keys are those the rule at :2587 returns;
- three channels are screened and packaged as before;
- a candidate build keeps its path.
10 of 10 mutations are killed. tests/package (552) and tests/moments, select_by_id and providers (127) all pass.

PLEASE CHECK: (1) that the gate cannot refuse a pool that could seat a medley (the subset argument: does anything after
the gate ADD a moment or a channel?); (2) that nothing paid runs before it (scorer_pass, trim_variant, ad_read_out,
current_levels); (3) the record's shape against the :2587 return and its readers (proof_ledger: res["usable"],
res["prescreen"].get("cleared"), open_work; CA.seed); (4) the candidate exclusion; (5) the tests.


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
