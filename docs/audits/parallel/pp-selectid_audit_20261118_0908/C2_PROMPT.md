# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261118_0908
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 149 s finish=stop usage in 6276 / out 3278 usd_reported=0.000601 usd~0.068 (upper-bound price)

The code implements a targeted fix for RULING 141 (2) to prevent the loss of a channel when a trim variant fails a hard gate (RULING 33) while the original untrimmed moment was previously excluded from the "never-empty pass" simply because that variant existed.

### Analysis
1.  **Logic Change**: The modification in `pipeline/package.py` removes the condition `m["moment_id"] not in trims` from the `stand_back` logic (now encapsulated in `stand_soft_back`). This ensures that the original moment is flagged as a candidate for the never-empty pass regardless of whether a trim variant was attempted.
2.  **Pool Composition**: The pool of candidates now potentially contains both the original moment (marked `stand_soft`) and its trim variant. 
3.  **Constraint Compliance**: 
    *   **L-y 4 (One clip per video)**: The prompt specifies that the line-up rules enforce a limit of one clip per video. Since the line-up selection logic is not modified, this constraint remains active. The line-up will select either the original or the trim variant, but not both.
    *   **RULING 141 (2)**: The implementation correctly filters for `soft` mode, `no_role` (opener failure), and `no_topic(m) is None` (no topic refusal), adhering to the ruling.
    *   **Fail-Closed (M12)**: The use of `if p` in the comprehension ensures that if `stand_plain(m)` returns `None` or an empty value, the moment is not brought back.
4.  **Test Coverage**: The new test `test_an_original_comes_back_beside_its_trim_variant` correctly verifies that an opener-only moment is recovered while a topic-refused moment remains excluded, and confirms the function no longer depends on the `trims` state.

### Findings
No violations of the Governing Laws or logic errors were found. The change is a minimal, surgical fix that restores the intended fallback behavior without introducing regressions in the selection pool.

P1_OR_WORSE: 0

## GPT-OSS-20B — CYCLE 1 OUTPUT
# gpt-oss-20b (openai/gpt-oss-20b) 60 s finish=stop usage in 5605 / out 10414 usd_reported=0.001464 usd~0.173 (upper-bound price)

**Findings**

- **[P0] Potential rule violation (L‑y 4)** – `stand_soft_back` now returns *both* the original moment and its trim variant when both satisfy the “soft” criteria.  
  This could allow a line‑up to include two clips from the same video, violating the “one clip per video” rule. The change was intended to recover the original clip, but the side‑effect of exposing the trim variant may lead to an over‑inclusive line‑up and thus a data‑loss or wrong‑result scenario.

- **[P3] Minor documentation** – The new function’s docstring still references the old “never‑empty pass” wording and does not explicitly state that trim variants are no longer excluded.  
  Updating the docstring would improve clarity but is not critical.

- **[P3] Minor export** – `stand_soft_back` is not listed in any module’s `__all__` or exported explicitly.  
  While the function is accessed via `PK.stand_soft_back` in tests, adding it to `__all__` would make its public API clearer.

- **[P3] Minor signature check** – The test verifies that the signature contains no `trims` parameter, which is satisfied. No further action required.

**P1_OR_WORSE**: **1** (one P0 finding)

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 169 s finish=stop usage in 5972 / out 4812 usd_reported=0.003709 usd~0.090 (upper-bound price)



## Audit Findings — pp-selectid / C1_STEP.diff

### Context

The diff extracts the never-empty pass's "come-back" logic into `stand_soft_back(ms, no_role, soft)` and removes the `m["moment_id"] not in trims` guard. Rationale: build 147 showed that when a trim variant fails ruling 33 (HARD), the original was still excluded because it *had* an affirmed variant, losing the channel entirely. The fix lets the original re-enter the pool flagged (`stand_soft`) beside its variant, relying on L-y 4 (one clip per video) to prevent double-selection.

---

### Findings

**[P2] No integration test for the build-147 regression path**

The new unit test (`test_an_original_comes_back_beside_its_trim_variant`) exercises `stand_soft_back` in isolation with synthetic moments and verifies the signature no longer accepts `trims`. However, the actual failure mode that motivated this change — a trim variant present in the pool that *fails* ruling 33's trimmed-cut gate, causing the line-up to fall back to the `stand_soft`-flagged original — is not tested end-to-end in this diff. The description states "the existing end-to-end STAND_ALONE tests pass unchanged," but those tests were written under the old invariant (original excluded when a variant exists). A regression test that:

1. places a moment in `ms` with an affirmed trim variant in `trims`,
2. causes the variant to fail `trim_refused` / ruling 33,
3. asserts the original carries `stand_soft` and is selectable,

would lock in the fix and prevent a future refactor from silently re-introducing the `not in trims` guard.

**[P2] L-y 4 mutual-exclusion not verified in this diff's tests**

The docstring and the change description both state "one line-up never takes both (one clip per video, L-y 4)." Now that both the original and its trim variant can coexist in the pool, the line-up selection must enforce that only one is chosen. This diff's tests do not assert that constraint for the new co-existence case. If L-y 4 is enforced elsewhere with its own tests, this is a coverage gap in *this* diff rather than a correctness bug; but a one-line assertion in the new test (or a companion test) that the line-up picks exactly one of {original, variant} would make the invariant explicit at the point where the co-existence is introduced.

**[P3] `import inspect` inside the test method**

```python
import inspect
self.assertNotIn("trims", inspect.signature(PK.stand_soft_back).parameters)
```

The import is local to the method. Functionally harmless, but inconsistent with the module's top-level imports and slightly obscures the test's intent (it's really a "the helper must not depend on trims" assertion, which could be phrased as a docstring note or a `# noqa`-style comment). Nit only.

---

### Law-compliance check

| Law | Status |
|-----|--------|
| SENTENCE LAW | Unaffected — no boundary logic changed. |
| SELECTION LOCK | Unaffected — `selection_lock` / sha256 seal untouched. |
| SNAP LIMIT / NEIGHBOUR / ONSET-TAIL | Unaffected. |
| L-a … L-l | Unaffected. |
| LAW 20 / M2 | Compliant — no gate threshold altered; no failing gate reclassified. The trim variant still must pass ruling 33 independently; the original still must pass the opener rule (softly). |
| M12 FAIL CLOSED | Compliant — `soft=False` returns `{}`; `no_topic(m) is not None` excludes the moment; `stand_plain(m)` returning falsy excludes it. No path produces a pass from missing data. |
| LAW 22 (v2f) | Unaffected. |
| Smallest diff / M1 | Compliant — one function extracted, one condition removed, one call-site updated. No new renderer, compositor, or selector. |

No [P0] or [P1] violations identified.

---

P1_OR_WORSE: 0

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus (pp-selectid_audit_20261118_0908, the STAND_ALONE come-back beside a trim variant)

SEATS ANSWERED: 3 of 3. qwen3.8-27b and gemma-4-31b-it: P0/P1 none. gpt-oss-20b: one P0 claimed, REFUTED:
gpt-oss [P0] "both the original and its trim variant can be taken, against L-y 4": REFUTED. stand_soft_back returns
ORIGINALS only (from the pool before the trims are added); the variant was always added beside them. A line-up can never
take both: package.lineup_ok (unchanged) allows one segment per channel or, under the supply exception (repeat_ok), one
channel with two clips from TWO DIFFERENT VIDEOS (len({m["video_id"]}) == len(segs)); an original and its trim variant
share one video. Every picker's line-up goes through lineup_ok.

## No change from cycle 1 to cycle 2.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261118_0908/C2_STEP.diff (55 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index c962a66..250c4f1 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -1614,6 +1614,16 @@ def stand_soft_rows(stand, segs):
   6 |      return out or None
   7 |  
   8 |  
   9 | +def stand_soft_back(ms, no_role, soft):
  10 | +    """RULING 141 (2), the never-empty pass: {moment id: plain reason} of the moments brought back as clips, flagged:
  11 | +    left out ONLY by the render's STAND_ALONE opener rule (no topic refusal, ruling 34). An affirmed trim variant no
  12 | +    longer keeps its original out (build 147, 09:05 ET Nov 18: Natalie Brunell feb4b72f's 'And'-trimmed variant failed
  13 | +    ruling 33's trimmed cut, HARD, and the original was lost with it): the two sit side by side, and one line-up never
  14 | +    takes both (one clip per video, L-y 4). The clean pass brings nothing back."""
  15 | +    return {m["moment_id"]: p for m in ms if soft and m["moment_id"] in no_role and no_topic(m) is None
  16 | +            for p in [stand_plain(m)] if p}
  17 | +
  18 | +
  19 |  def stand_ok(segs):
  20 |      """The render's STAND_ALONE on a line-up for the line-up rules (lineup_ok, lineup_for): it passes, or RULING 141 (2),
  21 |      its only failures are clips the never-empty pass brought back failing only the opener rule (stand_soft_rows)."""
  22 | @@ -3382,8 +3392,7 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  23 |               for v in [trim_variant(m, sources)] if v}                      # joins the pool (the original stays a clip)
  24 |      trim_out = {k: why for k, v in trims.items() for why in [trim_refused(v)] if why}   # ruling 56: never sealed
  25 |      trims = {k: v for k, v in trims.items() if k not in trim_out}
  26 | -    stand_back = {m["moment_id"]: p for m in ms if soft and m["moment_id"] in no_role and m["moment_id"] not in trims
  27 | -                  and no_topic(m) is None for p in [stand_plain(m)] if p}   # RULING 141 (2): STAND_ALONE SOFT in the
  28 | +    stand_back = stand_soft_back(ms, no_role, soft)                         # RULING 141 (2): STAND_ALONE SOFT in the
  29 |      for m in ms:                                                            # never-empty pass: a moment left out ONLY
  30 |          if m["moment_id"] in stand_back:                                    # by the opener rule (no topic refusal, no
  31 |              m["stand_soft"] = stand_back[m["moment_id"]]                    # affirmed trim) comes back as a clip,
  32 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
  33 | index 25b32cb..5f8d8c9 100644
  34 | --- a/tests/package/test_ruling_137.py
  35 | +++ b/tests/package/test_ruling_137.py
  36 | @@ -357,6 +357,18 @@ class TestRuling141StandAloneSoft(unittest.TestCase):
  37 |      def test_a_mark_carried_in_is_never_read(self):
  38 |          self.assertIsNone(self.rig(False, carry=True)["package"])
  39 |  
  40 | +    def test_an_original_comes_back_beside_its_trim_variant(self):
  41 | +        """Build 147 (09:05 ET Nov 18): the trim variant of Natalie Brunell feb4b72f failed ruling 33's trimmed cut and
  42 | +        the original, which needs no trim, had been kept out by it. The come-back no longer reads the trims at all."""
  43 | +        from test_moments import pm
  44 | +        ms = [dict(pm("a", "N", 9.6), text="And Bitcoin a x."), dict(pm("b", "Y", 9.6), text="But nothing here.")]
  45 | +        no_role = {"a": "opener", "b": "opener; topic"}
  46 | +        got = PK.stand_soft_back(ms, no_role, True)
  47 | +        self.assertEqual(list(got), ["a"])                        # the topic refusal (b) stays out
  48 | +        self.assertEqual(PK.stand_soft_back(ms, no_role, False), {})
  49 | +        import inspect
  50 | +        self.assertNotIn("trims", inspect.signature(PK.stand_soft_back).parameters)
  51 | +
  52 |      def test_the_line_up_rules_take_a_marked_clip_and_refuse_an_unmarked_one(self):
  53 |          from test_moments import pm
  54 |          h = dict(pm("h", "A", 12.0), hook_onset={"pass": True})
  55 | 
```

---

pp-selectid: RULING 141 (2) (STAND_ALONE soft in the never-empty pass), ONE FIX found by build 147 (09:05 ET Nov 18,
ruling 147 (B)). The come-back (package.py, in _build right after the trims) brought back a moment left out ONLY by the
render's STAND_ALONE opener rule, flagged, but NOT when it had an affirmed one-word trim variant ("and m['moment_id'] not
in trims"): the variant was preferred as the clean path. In build 147 Natalie Brunell feb4b72f's 'And'-trimmed variant
then failed ruling 33's trimmed cut (HARD: the trimmed word co-articulated), and the untrimmed original, which needs no
trim, had been kept out by it: the channel was lost and nothing sealed.
THE CHANGE: the come-back is now package.stand_soft_back(ms, no_role, soft), which no longer reads the trims: the
original comes back flagged beside its trim variant (the variant keeps its own place, as ruling 94 (a)'s hook trims
already do); one line-up never takes both (one clip per video, L-y 4). Everything else is unchanged: only the never-empty
pass, only the opener rule (no topic refusal, ruling 34), the plain reason, the flag, the hook's opener HARD.
File: pipeline/package.py, tests/package/test_ruling_137.py.
TESTS: the helper brings back an opener-only moment, keeps a topic refusal out, and brings nothing back in the clean pass;
the existing end-to-end STAND_ALONE tests pass unchanged.
PLEASE CHECK: (1) can a line-up now take both a moment and its trim variant? (2) anything else this lets through.


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
