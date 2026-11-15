# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_2214
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 118 s finish=stop usage in 5886 / out 3240 usd_reported=0.000584 usd~0.066 (upper-bound price)

# Audit: pp-selectid — RULING 109 early ALONE stop in `spotlight.build`

## What the diff does

In `build()`, right after `P.with_verdict` attaches scorer verdicts, it:

1. Builds `low` = moments whose `alone_score(m)` is known and `< ALONE_MIN`.
2. Stops each with reason "ruling 109" (free gate before paid verdict).
3. Filters `ms` to the survivors; if none remain, sets `why_none` and returns **before** `P._writers`, `prescreen` (step A) and everything paid.
4. Records `out["ruling_109"] = {"alone_known_below_min": len(low)}`.

Unscored moments pass through untouched; stage 7's final ALONE ≥ 4 requirement is unchanged, so the early stop is a pure optimization *plus* a behavioral change: a low-ALONE moment that previously reached step A (and possibly got sealed via the paid path) now never does.

---

## Findings

### [P1] The early stop can drop a moment that would have sealed — question (1) answered: yes, in the documented "score changes within the build" case, and the diff's own "UNCHANGED GUARDS" note doesn't cover it

The replay text says the guard is: "stage 7 still requires ALONE ≥ ALONE_MIN (alone_score of the **CURRENT text**) for every finalist, so the earlier stop can never let through a moment the later stage would refuse." That proves **no false pass** — it does *not* prove **no false stop**. Two concrete paths:

**(a) Score changes within the build.** `alone_score` reads `P.verdict_of` for the moment's *current text*. If anything in `build()` before stage 7 can change the text (a snapped span, a re-anchored quote, an editorial rewrite) — and the diff's own test at line 52 constructs moments with *different texts* (`TEXT.replace("money", "asset")`) and passes `alone=[3.0, 4.0, "None"]`-style scores keyed by position, implying alone scores are per-moment, not per-text — then a moment whose *pre-build* score is 3.0 but whose *post-snap* text would score ≥ 4 is now stopped at line 9–12, where before ruling 109 it proceeded, got its (new) score, and could seal. The old code's stage-7 check ran on the current text; the new early check runs on the *pre-build* text's score. If `with_verdict` attaches the verdict for the text the scorer last saw, and the build later snaps/edits the span, the early gate and the stage-7 gate read different texts. The diff's guard note asserts they're the same ("alone_score reads P.verdict_of (the scorer's verdict for the moment's **current text**)") — but that's exactly the thing the diff does not prove: nothing in the diff shows the text is immutable between line 9 and stage 7. If it *is* immutable, the guard note should say *why* (e.g., "build() never mutates `m["text"]` after `with_verdict`; the scorer verdict is keyed by text hash"); as written it's an assertion, not a proof. **Fix: either (i) add a test that a moment whose text is snapped/edited inside build() and whose pre-snap ALONE < 4 but post-snap ≥ 4 still seals (or is documented as intentionally dropped), or (ii) add a comment/test pinning that build() never changes the scored text.**

**(b) `alone_score(m) is not None` vs. the scorer's "no rating" case.** Line 9: `low = {m["moment_id"]: alone_score(m) for m in ms if alone_score(m) is not None and alone_score(m) < ALONE_MIN}`. Note `alone_score(m)` is called **twice** per moment (once in the condition, once as the value) — harmless but see the P3. More importantly: the existing test at line 29–30 expects the reason `"ALONE scorer: no rating"` for `alone=None` — that moment is *not* in `low` (score is None), so it proceeds. Good — question (2): **an unscored moment is never stopped by this diff**; it flows to step A and stage 7 waits, exactly as the two surviving tests (lines 55, 58–60: `alone=[3.0, 4.0, None]` → prescreen sees `["b","c"]`; `alone=[2.0]` → no prescreen at all) pin. But: what if the scorer's verdict *exists* yet contains no rating (a sealed-but-unrated verdict, or a verdict whose rating field is missing — cf. L-l "a model reply counts only whole")? If `alone_score` returns None for "verdict present but rating missing" (L-l says such a reply is a failed call → INCONCLUSIVE), the moment proceeds — correct. But if `alone_score` raises or returns a *string* rating ("4.0" as str), the comparison `alone_score(m) < ALONE_MIN` on line 9's condition would raise TypeError → per M12 fail-closed that's a HOLD, acceptable, but the diff adds no test for a malformed rating. Under L-l, `_v_rate` guarantees a 1–5 number, so this is likely covered upstream; still, the diff relies on that invariant without a test here. **P2: add a test that a verdict whose rating is a string/None-rating (L-l INCONCLUSIVE) flows through as "no score yet", not stopped.**

### [P2] `out["ruling_109"]` counts, but the stopped moments' reasons are only in `out["moments"][mid]["out"]` — the summary counter and the per-moment reasons can disagree

`out["ru

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 39 s finish=stop usage in 5999 / out 922 usd_reported=0.022594 usd~0.053 (upper-bound price)

**CODE AUDIT REPORT — pp-selectid-20261114_2214 (spotlight.py + test)**

**Summary of review against all governing laws (SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-a through L-l, LAW 20/M2, M12 FAIL CLOSED, LAW 22, L-d protected preview, smallest-diff rule, exact gate inventory, fail-closed on missing data, canon.py as sole text comparator, model reply validation, no reclassification of failing gates, byte-identical v2f re-renders, etc.):**

The diff implements Ruling 109 by moving the known ALONE < ALONE_MIN check immediately after P.with_verdict() and before any paid prescreen/step A. Low-scoring moments are stopped with a dedicated reason, filtered from the ms list, counted in out["ruling_109"], and cause an early why_none return if nothing remains. Unscored moments (None) continue. Tests updated to match new stop reasons and to assert which moments reach prescreen.

**Findings:**

[P1] Early stop on already-known ALONE score (before prescreen, before any span snapping or refinement) can permanently drop a moment that could still seal. A low initial ALONE on the pre-filter candidate text does not preclude a later snapped span (per SNAP LIMIT + SENTENCE LAW boundary rules) from receiving ALONE >= ALONE_MIN on the final locked selection. Stage 7 only re-checks the *current* text; the early filter therefore introduces false-negative rejections that the later guard cannot recover. This changes effective selection criteria, violates SELECTION LOCK (words fixed at selection time, no later recomputation), L-c (dissent treated as right until final-byte acoustic proof), L-f cluster-to-model flow, and the "smallest diff / no change to what a check accepts" rule (LAW 20/M2). The commit message itself flags this exact risk in "PLEASE CHECK (1)"; the implementation does not mitigate it. Must be fixed before merge.

[P2] New out["ruling_109"] key and mutated stop-reason strings alter the shape of build() output and per-moment "out" entries. While the supplied tests cover the new paths, there is no verification that release_auth.py (L-j), ATTESTATION.json, telegram delivery, or gate-inventory exact-match logic will treat the new fields as non-blocking. Any divergence from "every REQUIRED gate ran, on exactly the bytes that are sent" is a release-authorisation hazard.

[P2] No regression test exercising a moment whose ALONE score changes *after* the new early-check point (e.g. scorer updates, snapped span, or text mutated by step A) to confirm it is not erroneously filtered. The "waits for the alone scorer" test only covers the None case, not a low-then-later-high transition on a refinable candidate.

[P3] Updated test expectations now expect "ruling 109" instead of prior opener-rule or "ALONE scorer: no rating" strings; this reclassifies the failure mode without acoustic or final-byte proof (touches L-c, L-g, L-k canon rules).

[P3] Nit: long test name test_ruling_109_a_known_low_alone_never_reaches_a_paid_verdict mixes implementation detail with ruling number; also, inline comments repeat the orchestrator timestamp instead of citing the specific laws (SENTENCE LAW, SELECTION LOCK, L-c, L-j, M12) the change must obey.

[P3] Diff claims "no sealed pin lost" and references a cost-audit-pack section 10 that is not provided in the review package, preventing independent verification of replay integrity (LAW 22, L-d protected preview).

No P0 findings: no gate is shown passing what must be refused, no data loss, no violation of fail-closed on missing data/model errors (M12), no unpunctuated transcript paths opened (L-e), no model-reply partial fields accepted (L-l), canon.py usage untouched, v2f byte-identical render path unaffected, and ALONE_MIN remains a constant.

The change is small, touches only spotlight path, runs no new models/renderers, and correctly preserves the "if score is None, proceed" case. However, the core logic flaw in (P1) means it does not comply with the governing laws as written.

P1_OR_WORSE: 1

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 106 s finish=stop usage in 6329 / out 4867 usd_reported=0.003764 usd~0.092 (upper-bound price)

I will analyze the provided diff and context against the governing laws and the specific questions asked.

### Context Analysis
**Feature:** `pp-selectid` (Ruling 109).
**Goal:** Enforce "free gates first" in `pipeline/spotlight.py`. If a moment's `ALONE` score is *already known* to be below `ALONE_MIN` (4.0), it must be stopped *before* any paid verdicts (Step A, hook rating, etc.) are requested.
**Constraint:** Moments with *unknown* scores (None) must proceed to paid stages, where they will be evaluated later (Stage 7).
**Law Compliance:**
- **M12 FAIL CLOSED:** The code stops moments with known low scores. It does not pass them. It does not stop unknown scores (which is correct, as they are not "known low").
- **LAW 20:** Thresholds are constants (`ALONE_MIN`).
- **Smallest Diff:** The change is localized to `build()` in `spotlight.py` and tests.

### Code Review

#### 1. Logic in `pipeline/spotlight.py`

```python
ms = [P.with_verdict(m, idx) for m in ms]
low = {m["moment_id"]: alone_score(m) for m in ms if alone_score(m) is not None and alone_score(m) < ALONE_MIN}
for mid, sc in low.items():                  # RULING 109 ...
    stop(mid, f"the ALONE scorer: {sc} (needs {ALONE_MIN:g}), a free gate before any paid verdict (ruling 109)")
ms = [m for m in ms if m["moment_id"] not in low]   # verdict only for what every free gate passed...
out["ruling_109"] = {"alone_known_below_min": len(low)}
if not ms:
    out["why_none"] = "every moment's ALONE score is known below the minimum: no paid verdict (ruling 109)"
    return out
```

**Analysis:**
- `alone_score(m)` is called. The prompt states: "alone_score reads P.verdict_of (the scorer's verdict for the moment's current text)."
- The filter `if alone_score(m) is not None and alone_score(m) < ALONE_MIN` correctly identifies moments with a *known* low score.
- Moments with `None` score are excluded from `low`, thus remain in `ms` and proceed to `P.prescreen` (paid step A).
- The `stop` function is called for each low moment. Assuming `stop` marks the moment as failed/stopped in the output structure (standard pattern in this codebase based on context), this prevents them from being processed further.
- The list comprehension `ms = [m for m in ms if m["moment_id"] not in low]` removes the stopped moments from the list passed to `P.prescreen`. This ensures no paid calls are made for them.
- The early return `if not ms` handles the case where *all* moments are stopped.

**Potential Issue 1: `stop` side effects.**
Does `stop(mid, ...)` modify `m` in place or just record the stop? If `stop` only records the reason in `out["moments"][mid]["out"]` or similar, the removal from `ms` is necessary to prevent `P.prescreen` from seeing them. The code does remove them from `ms`. This looks correct.

**Potential Issue 2: `alone_score` stability.**
The prompt asks: "Can the early stop drop a moment that could still seal (a score that changes within the build...)?".
The prompt states: "UNCHANGED GUARDS: stage 7 still requires ALONE >= ALONE_MIN ... so the earlier stop can never let through a moment the later stage would refuse".
It also states: "alone_score reads P.verdict_of (the scorer's verdict for the moment's current text)."
If the text doesn't change, the score doesn't change. The "current text" is fixed at this point in the pipeline (post-transcription/selection). Therefore, a known low score will remain low. The early stop is safe.

**Potential Issue 3: Unscored moments.**
"Is an unscored moment ever stopped?"
The condition `alone_score(m) is not None` ensures that only moments with a score are considered for the `low` set. Unscored moments (`None`) are not in `low`, so they are not stopped by this block. They proceed to `P.prescreen`. This is the intended behavior ("a moment with NO score yet goes on, as before").

#### 2. Tests in `tests/package/test_spotlight.py`

**Test 1: `test_ruling_109_a_known_low_alone_never_reaches_a_paid_verdict`**
```python
ms = [moment(mid="a", channel="A"), moment(mid="b", channel="B", text=TEXT.replace("money", "asset")),
      moment(mid="c", channel="C", text=TEXT.replace("money", "thing"))]
out, calls = self.run_build(ms, {"a": 5, "b": 5, "c": 5}, alone=[3.0, 4.0, None])
self.assertEqual(calls.get("prescreen"), ["b", "c"])                       # "a" was never asked
self.assertIn("ruling 109", out["moments"]["a"]["out"])
self.assertEqual(out["ruling_109"], {"alone_known_below_min": 1})
```
- `alone=[3.0, 4.0, None]` maps to `a`, `b`, `c`.
- `a` (3.0) is `< 4.0` and `not None`. It should be stopped.
- `b` (4.0) is `not < 4.0`. It should proceed.
- `c` (None) is `None`. It should proceed.
- `calls.get("prescreen")` should be `["b", "c"]`.
- The test asserts this.
- The test also checks `out["moments"]["a"]["out"]` contains "ruling 109". This depends on how `stop` writes to the output. Given the diff shows `s

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus: pp-selectid audit for ruling 109 (free gates first in the spotlight build)

qwen3.8-27b reports P1_OR_WORSE 0 and glm-5.3-flash 1. They disagreed, so Grok was asked as the third: 1. Cost: $0.0269
vendor-reported.

THE SHARED P1 (glm, Grok): "the text may change after the early check (a snap, a trim, a rewrite), so a score known
low at the start may not be its final score". REFUTED from the code:
- Snapping happens in spotlight.pool (stage 1, spotlight.py:832, `ms, why = pool(...)`), BEFORE the early check. The
  moments reaching it are already the snapped spans, and with_verdict attaches the score of that exact text.
- No later stage assigns a moment's text: spotlight.py has no `m["text"] =`. A trimmed opener is its own moment
  ("~trim", with its own text and its own score), never a rewrite of another.
- Stage 7 re-attaches the scorer's verdicts (P.with_verdict) for the SAME text under the same scorer sha. A verdict
  is fixed per text and scorer version, so a score known below 4 at the start is the score stage 7 would stop it on.
- Nothing is dropped for good. Every build re-reads the scorer's verdicts, so a new scorer version is read by the
  next build.
- SELECTION LOCK, L-c and L-f: no selected word, cut or cluster changes. The early stop refuses only what stage 7
  refuses anyway, earlier and without a paid call.
Grok P2 (the new out["ruling_109"] key and the reasons): build() output is the builder's record. release_auth and
the pin never read it, and the pin's gate rows are unchanged.
Grok P2 / glm (a test of a low-then-high score): the case cannot arise within a build, for the reasons above.

No change. Mutations: 3 of 3 killed (no free gate first; an unscored moment stopped; exactly 4.0 stopped).


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261114_2214/C2_STEP.diff (65 lines)
```
   1 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
   2 | index 6011dcf..f2290d0 100644
   3 | --- a/pipeline/spotlight.py
   4 | +++ b/pipeline/spotlight.py
   5 | @@ -852,6 +852,14 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
   6 |          ({}, {"read": False, "why": "no verdicts file given"})
   7 |      out["scorer"] = srec
   8 |      ms = [P.with_verdict(m, idx) for m in ms]
   9 | +    low = {m["moment_id"]: alone_score(m) for m in ms if alone_score(m) is not None and alone_score(m) < ALONE_MIN}
  10 | +    for mid, sc in low.items():                  # RULING 109 (orchestrator 21:30 ET Nov 14): free gates first; a paid
  11 | +        stop(mid, f"the ALONE scorer: {sc} (needs {ALONE_MIN:g}), a free gate before any paid verdict (ruling 109)")
  12 | +    ms = [m for m in ms if m["moment_id"] not in low]   # verdict only for what every free gate passed: an ALONE score
  13 | +    out["ruling_109"] = {"alone_known_below_min": len(low)}   # known below 4 never reaches step A (stage 7 would stop it)
  14 | +    if not ms:
  15 | +        out["why_none"] = "every moment's ALONE score is known below the minimum: no paid verdict (ruling 109)"
  16 | +        return out
  17 |      wv, wf = P._writers(router)
  18 |      a_by, fails, _, _ = P.prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log, cache=step_a_cache,
  19 |                                      kind="step_a_first", **P.first_bounds(router))   # as the medley's (rulings 85, 88)
  20 | diff --git a/tests/package/test_spotlight.py b/tests/package/test_spotlight.py
  21 | index e6b4035..c99d420 100644
  22 | --- a/tests/package/test_spotlight.py
  23 | +++ b/tests/package/test_spotlight.py
  24 | @@ -520,9 +520,9 @@ class TestRuling94And95(unittest.TestCase):
  25 |          t = ("This is ultimately a bipartisan issue for Bitcoin and for every holder of it, whatever their politics, "
  26 |               "as far as I can tell.")
  27 |          b = TestBuild()
  28 | -        for alone, sealed, why in ((3.0, False, "cannot open cold"),        # a verdict that does not affirm: the
  29 | -                                   (None, False, "ALONE scorer: no rating"),  # opener rule itself refuses; none yet:
  30 | -                                   (4.0, True, None)):                          # deferred, then refused at ALONE
  31 | +        for alone, sealed, why in ((3.0, False, "ruling 109"),              # a verdict below 4: refused by the free
  32 | +                                   (None, False, "ALONE scorer: no rating"),  # gate before any paid verdict (ruling
  33 | +                                   (4.0, True, None)):                          # 109); none yet: deferred, then refused
  34 |              m = moment(mid="t", channel="T", text=t, scorer_verdict=None)
  35 |              m.pop("scorer_verdict")
  36 |              out, calls = b.run_build([m], {"t": 5}, alone=[alone])
  37 | @@ -664,6 +664,7 @@ class TestBuild(unittest.TestCase):
  38 |          calls = {}
  39 |  
  40 |          def prescreen(router, ms_, *a, **k):
  41 | +            calls.setdefault("prescreen", []).extend(m["moment_id"] for m in ms_)      # ruling 109: who reaches step A
  42 |              return {m["moment_id"]: dict(a_item("hook"), backend="fake:xai") for m in ms_}, \
  43 |                  {m["moment_id"]: [] for m in ms_}, set(), set()
  44 |  
  45 | @@ -735,6 +736,19 @@ class TestBuild(unittest.TestCase):
  46 |          self.assertIn("layout 'conversation'", out["moments"]["a"]["source"])
  47 |          self.assertIn("0.61 speaker turns a minute", out["moments"]["a"]["source"])
  48 |  
  49 | +    def test_ruling_109_a_known_low_alone_never_reaches_a_paid_verdict(self):
  50 | +        """RULING 109 (21:30 Nov 14): free gates first. An ALONE score already known below 4 stops the moment before
  51 | +        step A; a moment with no score yet still goes on (stage 7 waits for the scorer, as before)."""
  52 | +        ms = [moment(mid="a", channel="A"), moment(mid="b", channel="B", text=TEXT.replace("money", "asset")),
  53 | +              moment(mid="c", channel="C", text=TEXT.replace("money", "thing"))]
  54 | +        out, calls = self.run_build(ms, {"a": 5, "b": 5, "c": 5}, alone=[3.0, 4.0, None])
  55 | +        self.assertEqual(calls.get("prescreen"), ["b", "c"])                       # "a" was never asked
  56 | +        self.assertIn("ruling 109", out["moments"]["a"]["out"])
  57 | +        self.assertEqual(out["ruling_109"], {"alone_known_below_min": 1})
  58 | +        out, calls = self.run_build([moment(mid="a", channel="A")], {"a": 5}, alone=[2.0])
  59 | +        self.assertNotIn("prescreen", calls)                                        # nothing paid at all
  60 | +        self.assertIn("ruling 109", out["why_none"])
  61 | +
  62 |      def test_it_waits_for_the_alone_scorer_and_reports_the_nearest(self):
  63 |          ms = [moment(mid="a", channel="A")]
  64 |          later = {"a": sv(TEXT, 4.0)}
  65 | 
```

---

pp-selectid, RULING 109 (the orchestrator, 21:30 ET Nov 14): "free gates run first, cheapest first; a paid verdict is
asked only of a moment every free gate has passed".

THE REPLAY (records only, cost audit pack section 10): no sealed pin lost. In the medley path the free screens already
run before step A (the 12 h, the exclusions, the clip scorer's STAND_ALONE). In the spotlight path the free ALONE
>= 4 check ran LAST, after the paid step A, hook rating, visual check and second family.

THE CHANGE (pipeline/spotlight.py build(); tests/package/test_spotlight.py):
- right after the clip scorer's verdicts are attached (P.with_verdict), a moment whose ALONE score is ALREADY KNOWN
  below ALONE_MIN (4) is stopped with the reason "a free gate before any paid verdict (ruling 109)". It never reaches
  step A or any later paid stage.
- a moment with NO score yet goes on, as before: stage 7 waits for the scorer.
- no moment left: why_none, with no paid call. out["ruling_109"] records how many were stopped.
- tests: a known 3.0 never reaches step A, while a 4.0 and an unscored moment do; all low means no paid call. Two
  existing tests change only the expected reason: the ALONE score now stops the moment earlier than the opener rule
  or stage 7 did.
UNCHANGED GUARDS: stage 7 still requires ALONE >= ALONE_MIN (alone_score of the CURRENT text) for every finalist, so
the earlier stop can never let through a moment the later stage would refuse; alone_score reads P.verdict_of (the
scorer's verdict for the moment's current text).
PLEASE CHECK: (1) Can the early stop drop a moment that could still seal (a score that changes within the build, a
snapped span rated differently)? (2) Is an unscored moment ever stopped? (3) Do the tests pin it?


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
