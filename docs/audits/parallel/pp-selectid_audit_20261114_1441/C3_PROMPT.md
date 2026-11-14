# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_1441
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 413 s finish=stop usage in 16788 / out 12475 usd~0.237 (upper-bound price)

# CYCLE 2 AUDIT — pp-selectid-20261114_1441 (ruling 104, the tail-side twin)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against my Cycle 1 output:

- **grok's <high> (medley ordering)**: I noted the ordering question only obliquely — I verified the spotlight's finalist order but did not trace the medley path (package.build) separately. grok's point that `parents_first` only reordered the spotlight's finalists while the medley used `rank_key` directly was a real gap in my review. **Caught by grok, missed by me.**
- **grok's <medium> (inherited ALONE score)**: I flagged that `variant()` copies `m["scores"]` (tail_variant.py:72-74) but concluded it was "by design, not a violation" — which is right as far as it goes, but I didn't chase the question of whether the *scorer's* verdict (as opposed to the miner's scores) could leak. grok's framing was sharper. However, the consensus refutation (the ALONE gate reads the clip scorer's verdict keyed by the moment's own id and text_sha256, and `M.record` copies no scorer_verdict) answers it — the variant has its own id and text, so it can only ever see its own verdict. **grok raised it; the consensus resolved it; I partially missed the resolution's force.**
- **qwen's <medium> (index convention in `for_pool`)**: I worked through the `<` boundary logic in Cycle 1 and concluded it was correct (my (b) section, which I then partially withdrew mid-argument). qwen's winding verification ends at the same place the test does: `E.Span(src, 0, 2)` + `SENTENCES[:3]` at test line 295-296 pins the convention. **qwen's finding was a question, not a defect; I agree with its own self-resolution.**
- **glm's (b) (repeated held token)**: I raised this myself in Cycle 1 and got cut off mid-argument. The consensus refutation ("the variant is a PREFIX ending before the f[irst occurrence]") is correct: `held_word` returns the *first* occurrence's index (tail_variant.py:116-118, `for i in range(len(toks) - len(want) + 1)`), and `for_pool` ends the variant at the last boundary *before* that first occurrence (tail_variant.py:147), so a later repeated occurrence is left out too. The variant cannot contain the held occurrence. **I raised it; the consensus closed it; my Cycle 1 answer was truncated.**

What nobody caught, including me, in Cycle 1 — see §3.

## 2. WHERE DO I AGREE OR DISAGREE?

**grok <high> (medley ordering) — AGREE, now moot.** The finding was correct against the Cycle 1 diff. The rework removes `parents_first`/`finalist_order` entirely and instead *replaces* held parents in the pool (proof_ledger.py:203: `[m for m in moments if m["moment_id"] not in replaced] + variants`), so parent and variant never compete anywhere — spotlight, medley, or otherwise. This is a stronger fix than ordering: it makes the 14:12 order ("FIRST the re-listen; if it holds, the variant") structural rather than ordinal. The full clip is honoured because the variant only exists once the current pre-check, re-listen included, has held the full clip (holds() reads only current-decoder/current-rules answers, tail_variant.py:83-94). Verified: test lines 433-448 exercise `with_variants` directly and the held parent is dropped. **Resolved.**

**grok <medium> (inherited ALONE) — AGREE with the refutation.** `variant()` (tail_variant.py:72-75) passes `{"scores": m["scores"], ...}` to `M.record` — the *miner's* scores, which feed `rank_score` (line 76) only. The ALONE gate reads the clip scorer's verdict for the moment's own id, and (per the consensus, which I adopt) `package.with_verdict` requires the verdict's `text_sha256` to equal the moment's text's. The variant's text differs from the parent's (test line 295: `SENTENCES[:3]` vs. all five), so a parent's verdict cannot satisfy it. No cached-ALONE path. **Not a defect.**

**qwen <medium> (boundary convention) — AGREE, resolved by the test.** `E.Span(src, 0, 2)` producing `SENTENCES[:3]` (test lines 294-296) and `v["sentences"] == [0, 2]` (line 296) fixes the convention: the second argument is the last sentence *index included*... wait, no — `variant()` at tail_variant.py:64-67 requires `k0 <= k < k1` and builds `E.Span(src, k0, k)`, and the test at line 296 asserts `v["sentences"] == [0, 2]` for `k=2` with text `SENTENCES[:3]` (sentences 0, 1, 2). So `E.Span(src, 0, 2)` includes sentences 0..2 — the second argument is *inclusive* of sentence 2, i.e. it's the last sentence, and `sentences[k][1]` is that sentence's last word. Then `for_pool`'s filter (line 147) `src.sentences[k][1] < i` selects sentences whose last word precedes the held word, and `ks[-1]` is the latest such. With the held word "401k." at `src.sentences[3][0] + 4` (test line 317), sentences 0-2 qualify, variant = [0,2], held word excluded. Correct. **No defect.**

**glm's withdrawn (a) note and its 12 s floor note — AGREE, not defects.** The variant enters the pool be

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 28 s finish=stop usage in 16586 / out 1248 usd~0.114 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-20261114_1441 (fixed diff after rework)**

1. WHAT DID THEY CATCH THAT YOU MISSED?
Grok's <high> on parents_first only reordering spotlight finalists (not medley rank_key path) was missed in my Cycle 1; I focused on variant vs parent competition but did not trace the concrete medley selection sequence that could seal a variant before the full clip. Grok's <medium> on copied scores/ALONE was also missed — I accepted M.record + fresh judge() at face value without verifying text_sha256 + own-moment_id isolation. GLM's repeated-held-token prefix issue (ending before first occurrence, potentially keeping the actual held later token) was overlooked; the Cycle 1 consensus correctly flagged it even though the original test_blockware_held_on_401k passed.

2. WHERE DO YOU AGREE OR DISAGREE?
- Grok <high> (ordering/medley): Agree. The original design allowed competition; the fixed rework (holds() + replaced set + proof_ledger:203 filter) eliminates it entirely. The parent is dropped before medley/spotlight see the pool, so "tried first (14:12 order)" is now structural.
- Grok <medium> (score inheritance): Disagree on the fixed version. Facts + test_ruling_104:306 ("eligibility judged afresh"), spotlight.alone_score (requires text_sha256 match on own id), and M.record(..., M.judge(sp, ctx)) confirm the variant cannot inherit parent's ALONE or cached step-A verdicts. The copied m["scores"] are only for rank_score.
- Qwen <medium> (boundary off-by-one in for_pool:147): Partially agree on the original diff's ks + E.Span(k0, k) ambiguity, but the fixed tests (lines 295-296, 388-390, 402-405, 415-416) plus explicit SENTENCES[:3] assertions and src.sentences[k][1] < i logic now verify correctness for both first-word and last-word held cases. No off-by-one remains.
- GLM (b) (repeated token + first-occurrence): Agree. The fixed held_word:108-118 (canon_spans + first match of want tokens) plus test_an_insert_before_the_hold_cannot_be_placed_so_no_variant (lines 325-330) close the loophole; an earlier insert that cannot be excluded yields None, preventing a variant that keeps the later held word.
- GLM (a) & Qwen on gates/snap/derived_from: Fully agree — the fixed snap:9-11, package_for:20-21, variant:68-79, and "faces every gate again" facts confirm no shortcuts.

3. NEW FINDINGS FROM THIS REVIEW
<medium> pipeline/tail_variant.py:156 (ceiling ks list) + :164 (min k). Concrete sequence: parent 22.94 s with sentences [0,4], ceil_s set so only k=2 fits by token["end"] but floating-point token end times (or a sentence whose cumulative duration rounds to exactly ceil_s + epsilon) produces a variant whose own duration_s > ceil_s. for_pool does not re-check duration after variant() creation; spotlight.pool would later drop it, but the variant is still written to inputs["ruling_104"] and scored, wasting an ALONE call. Test at 402-404 uses +0.01 guard but does not cover token-end rounding. (Uncertain whether token times can actually produce > ceil_s given eligibility.Span, therefore flagged medium.)

No criticals or highs. All Cycle 1 attack vectors (a)-(e) plus new (f)-(g) are closed by the replacement logic, current-decoder-only holds(), test coverage of older-decoder/pass cases (TestTheHolds:348-362), and "no variant" notes.

4. REVISED SCORES
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| Ordering / replacement | high    | none    | Replacement (for_pool:166, with_variants:203) + current-decoder holds() fully resolves competition and "FIRST the re-listen" that I only partially saw before. |
| ALONE / verdict freshness | medium | none    | Facts + test:306 + text_sha256 requirement eliminate inheritance concern. |
| Held-word placement / boundaries | medium | medium  | Repeated-token and first-sentence cases now explicitly tested; new minor ceiling floating-point edge surfaced. |
| Snap / derived_from recording | low     | none    | Explicit snap guard and pk["spotlight"] addition verified. |

5. FINAL PRIORITY LIST
P2 MEDIUM — pipeline/tail_variant.py:157 (after ks list for ceiling): add `if float(src.tokens[src.sentences[k][1]]["end"]) - t0 > ceil_s: continue` (or post-variant duration check) before appending.  
No P0 CRITICAL or P1 HIGH items. All ruling-104 requirements, SENTENCE LAW, SELECTION LOCK, and attack vectors (a)-(g) are satisfied by the diff + facts + tests.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
Replacing the held parent entirely (for_pool:166, proof_ledger.with_variants:203, inputs["ruling_104"]["replaced"]) so the two never compete, while only triggering after a current-decoder hold, enforces the orchestrator's 14:12 order without any ordering hack.

7. PRODUCTION READY?
Yes with conditions: (1) lock_precheck.answer (used by holds:91) must strictly select only the current decoder/rule

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 124 s finish=stop usage in 18390 / out 4434 usd~0.122 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (Final)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I focused heavily on the boundary logic (`<` vs `<=`) and the "repeated token" edge case. I missed the **structural ordering flaw** that Grok and GLM identified: the original `parents_first` logic only reordered the *spotlight finalists*, but the **medley** path (which runs on the full pool) had no such protection. This meant a high-ranked variant could be selected by the medley *before* its parent was even considered, violating the "full clip first" intent of Ruling 104.

I also underestimated the risk of **stale holds**. I assumed `holds()` would naturally filter for current relevance, but the Cycle 1 code (and my initial reading of the diff) allowed `holds()` to read *any* decoder/rules entry. Grok and GLM correctly flagged that an older decoder's hold could trigger a variant even if the current decoder passed the clip. The rework (replacing parents, using `lock_precheck.answer` for current-only) addresses this, but I need to verify the *implementation* of that rework in the current diff.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Grok <high> (Medley ordering):** **Agree.** The removal of `parents_first` and the introduction of `replaced` (dropping the parent from the pool entirely if held) is the correct fix. If the parent is dropped, it cannot compete in the medley. If it's not held (just over ceiling), it stays "beside" the variant, which is acceptable because the medley can choose either, but the *spotlight* (which has the 35s ceiling) will naturally prefer the variant if the parent is too long, or the parent if the variant is too short. Wait — if the parent is over the ceiling, it *cannot* be a spotlight. So the medley is the only place it competes. Is that a problem? Ruling 104 says "a spotlight (and a medley hook or clip) may be sealed as a variant". It doesn't explicitly forbid the medley from using the parent if the parent is lawful. However, if the parent is *held*, it is *not* lawful. The rework drops held parents. This is correct.
*   **Grok <medium> (ALONE score inheritance):** **Disagree (Refuted).** As noted in the consensus, `M.record` creates a fresh record. The `scores` dict is copied, but the *verdict* (the actual ALONE rating from the clip scorer) is keyed by `moment_id` and `text_sha256`. Since the variant has a new ID and new text, it *must* get a new verdict. The copied `scores` are just the miner's initial heuristic scores, not the final gate verdicts.
*   **GLM (b) (Repeated token):** **Agree (Refuted by design).** The `held_word` function finds the *first* occurrence of the held token. The variant ends *before* that sentence. If the token appears again later, it is in the "left out" part. If it appears *earlier*, the variant ends before the *first* occurrence, so the later one is also left out. The logic `src.sentences[k][1] < i` ensures the variant ends at the last sentence *entirely before* the held word's index. This is robust.
*   **Qwen (Boundary ambiguity):** **Agree (Refuted by tests).** The tests explicitly verify that `E.Span(src, k0, k)` includes sentences `k0` to `k-1` (or `k` inclusive? Let's check). `variant(m, src, 2, ...)` on a parent `[0, 4]` results in `[0, 2]`. The text is `SENTENCES[:3]` (indices 0, 1, 2). So `k=2` means "end at sentence index 2". The span is `E.Span(src, 0, 2)`. In `eligibility.Span`, the second argument is typically the *exclusive* end index for the *sentence list*? No, `E.Span(src, k0, k1)` usually means sentences `k0` to `k1-1`? Or `k0` to `k1`?
    *   Test line 296: `v["sentences"]` is `[0, 2]`.
    *   Test line 295: `v["text"]` is `SENTENCES[:3]` (3 sentences).
    *   So `sentences=[0, 2]` means "from sentence 0 to sentence 2 inclusive".
    *   `E.Span(src, 0, 2)` must therefore be inclusive of the end index `2`.
    *   In `for_pool`, `ks = [k for k in range(k0, k1) if ... src.sentences[k][1] < i]`.
    *   If `i` is the index of the held word, and `src.sentences[k][1]` is the last word index of sentence `k`, then `src.sentences[k][1] < i` means sentence `k` ends *before* the held word.
    *   We pick `k = ks[-1]` (the last such sentence).
    *   We call `variant(m, src, k, ...)`.
    *   This creates a span ending at sentence `k`.
    *   Since sentence `k` ends before the held word, the held word is excluded. Correct.

## 3. NEW FINDINGS FROM THIS REVIEW

**<medium> `pipeline/tail_variant.py:147` — The `held_word` placement uses `canon_spans` on the *parent's* words, but compares against `src.tokens` indices.**
`held_word` returns `w0 + spans[i][1]`. `w0` is `m["words"][0]` (the start word index of the parent). `spans` are computed on `src.tokens[w0:w1+1]`. So `spans[i][1]` is the *relative* index of the last word of the held token within the parent's word slice. Adding `w0` gives the *absolute* index in `src.tokens`. 

## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 20261114_1441 (ruling 104), cycle 2: consensus

Reviewers:
- grok-4.20: yes with conditions. No P0 or P1.
- qwen3.8-27b: yes with conditions. One finding it tags <critical> and lists as P1 (the "doomed variant").
- glm-5.3-flash: yes with conditions. No P0 or P1; five P2 conditions.

All three agree the cycle-1 <high> (medley ordering) is resolved by the rework: a held parent is REPLACED in the pool, so
the two never compete. grok's ALONE <medium> is resolved by the text_sha256 argument, which glm adopts.

## Taken (a one-line fix; cycle 3 reviews it)

- **qwen P1, "the doomed variant".** A parent with a CURRENT hold whose held word cannot be left out:
  - the word cannot be placed, or it sits in the first sentence;
  - the parent is ALSO over the ceiling;
  - so the ceiling trigger still made a variant, and that variant kept the held word. It would fail its own pre-check:
    gates spent, no pin, and never a wrong pin.
  - Now: when a current hold cannot be relieved, for_pool makes NO variant at all, not even the ceiling's, and the
    parent is not replaced.
  - Test: the first-sentence hold over the ceiling gives no variant and replaces nothing. The mutation that puts the
    old behaviour back (P6) is killed.

## Documented, no change

- **grok (1): lock_precheck.answer reads only the current decoder's file under the current rules.** This is unchanged
  code: result_file(seg, results_dir, decoder=DECODER) and _matches (rules == RULES). test_ruling_104 checks it through
  holds(): an older decoder's and older rules' holds are not read.
- **grok (2): read the first production build's ruling-104 notes.** That will be done on STATE line 1 after the build.
- **glm P2-1, an insert anywhere suppresses the variant.** This is the chosen, conservative semantics. held_word places
  only an approved-side token. A spoken-side insert's position is not placed, so no variant is proposed. It errs toward
  no variant, never toward a variant that keeps a held difference.
- **glm P2-2, a held parent with no variant.** It stays in the pool and holds again at its pre-check, exactly as before
  this change. The notes name it on the build's RULING 104 line.
- **glm P2-3, the cut hold does not also try held_word.** A ruling-73 hold is about the cut, not a token, so its
  as_spoken text need not differ. The tail goes, as the ruling says ("a tail the cut cannot make").
- **glm P2-4, a variant whose span is already a pool moment.** That moment keeps its own record. The note records the
  collision ("its variant X is already in the pool").
- **glm P2-5, the two roles' answers are compared by their "at" strings.** Both are the integrator's ISO 8601 UTC
  stamps in one format, written by one service, so the string order is the time order. lock_precheck.answer itself
  picks each role's newest.
- The cycle-1 note said test_ruling_104 holds 15 tests. It holds 14 at cycle 2, and 14 with the fix's assertion added
  to an existing test.

Verification: 20 of 20 mutations

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261114_1441/C3_STEP.diff (486 lines)
```
   1 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
   2 | index 84ef788..370390e 100644
   3 | --- a/pipeline/spotlight.py
   4 | +++ b/pipeline/spotlight.py
   5 | @@ -152,6 +152,9 @@ def snap(m, sources, ctx, captions_for=None, target=SNAP_TO_S):
   6 |          return None, f"the moment itself: {why}"
   7 |      if dur >= target:
   8 |          return m, None                                 # long enough: no snap, the moment as it is
   9 | +    if (m.get("derived_from") or {}).get("ruling") == 104:      # RULING 104: a variant ends where it must; snapping
  10 | +        return None, (f"{dur:.2f} s, and a ruling-104 variant is never snapped outward (that would put back the "
  11 | +                      f"words it leaves out)")
  12 |      blocked = []
  13 |      while dur < target:
  14 |          step = None
  15 | @@ -1122,7 +1125,8 @@ def package_for(router, m, ctx, sources, a_two, truth, exc, pre, facts, log=prin
  16 |                         "alone": alone_score(m), "source": {k: src_rec.get(k) for k in ("ok", "why")},
  17 |                         "closing": {"candidate": (closing0 or {}).get("text"), "kept": pk1 is not None,
  18 |                                     "why_not": None if pk1 is not None else cl_why},
  19 | -                       "writes": [{k: x.get(k) for k in ("write", "backend", "error")} for x in notes]}
  20 | +                       "writes": [{k: x.get(k) for k in ("write", "backend", "error")} for x in notes],
  21 | +                       **({"derived_from": m["derived_from"]} if m.get("derived_from") else {})}   # RULING 104
  22 |      pk["models"] = {"writer": [x.backend for x in replies], "fidelity_verdict": fid.get("backend"),
  23 |                      "context": cx.get("backends"), "value": ((closing_rec or {}).get("value") or {}).get("backend"),
  24 |                      "layout": (src_rec.get("layout") or {}).get("backend")}
  25 | diff --git a/pipeline/tail_variant.py b/pipeline/tail_variant.py
  26 | new file mode 100644
  27 | index 0000000..ce29936
  28 | --- /dev/null
  29 | +++ b/pipeline/tail_variant.py
  30 | @@ -0,0 +1,146 @@
  31 | +"""RULING 104 (orchestrator 14:12 ET Nov 14), THE TAIL-SIDE TWIN: "a spotlight (and a medley hook or clip) may be sealed
  32 | +as a variant that ENDS at an earlier sentence boundary of the mined moment, when that is what keeps it lawful (a held word
  33 | +after the boundary, a tail the cut cannot make, the seconds ceiling). It is a new span: it faces every gate again from
  34 | +the start (step A both families, CUTTABLE at the new OUT, ALONE >= 4, the opener rating, the 12 s floor, the visual check,
  35 | +the lock pre-check), and the variant is recorded as derived from its parent row. Omission is judged by step A as always:
  36 | +a variant that drops the speaker's own condition or conclusion fails there."
  37 | +
  38 | +- variant(): the parent moment cut to end at the end of one of its own earlier sentences, made by the miner's own
  39 | +  machinery (moments.record over eligibility.Span: eligibility judged afresh, its id the span's own), with the parent's
  40 | +  scores, topics and risk, and "derived_from" (here and in its mined record): the parent row.
  41 | +- for_pool(): the variants a build adds to its pool (every gate then judges them as any moment):
  42 | +  - a held word: the lock pre-check's HOLD on the parent's exact span under the CURRENT decoder and rules (holds();
  43 | +    under ruling 103's rules such a hold is final, its targeted re-listen included). The held word is placed on this
  44 | +    side (held_word); the variant ends at the parent's last sentence boundary before it.
  45 | +  - a tail the cut cannot make: a current hold that is ruling 73's ("the render cannot cut this span"): the last
  46 | +    sentence goes.
  47 | +  - the seconds ceiling: a parent longer than ceil_s: the longest variant within it.
  48 | +  When two apply, the shorter variant (it satisfies both). None when no earlier boundary does.
  49 | +  A parent with a current hold is REPLACED by its variant ("the hold is final and the clip may only be saved by a
  50 | +  variant that leaves the token out", ruling 103): the two never compete for a line-up or a finalist's place. A parent
  51 | +  over the ceiling stays beside its variant (the medley may still use it).
  52 | +A variant is never snapped outward (spotlight.snap): that would put back the words it leaves out."""
  53 | +import attest as AT
  54 | +import canon as C
  55 | +import eligibility as E
  56 | +import moments as M
  57 | +
  58 | +CUT_HOLD = "ruling 73"          # a hold whose reason starts so: the render cannot cut this span (the tail goes)
  59 | +
  60 | +
  61 | +def variant(m, src, k, ctx, why):
  62 | +    """The parent moment `m` (a pp.moment/1 record) ending at the end of its source's sentence k, its first sentence
  63 | +    unchanged (m's first sentence <= k < its last). -> the new moment record. ValueError for any other k."""
  64 | +    k0, k1 = m["sentences"]
  65 | +    if not (isinstance(k, int) and k0 <= k < k1):
  66 | +        raise ValueError(f"a tail variant ends at an earlier sentence of the moment: {k!r} is not in [{k0}, {k1})")
  67 | +    sp = E.Span(src, k0, k)
  68 | +    derived = {"ruling": 104, "from": m["moment_id"],
  69 | +               "ledger_moment_id": (m.get("mined") or {}).get("ledger_moment_id"),
  70 | +               "sentences": [k0, k], "was": [k0, k1], "end_was": m.get("end"), "why": why,
  71 | +               "left_out": E.spoken(src.tokens[sp.w1 + 1:src.sentences[k1][1] + 1])}
  72 | +    rec = M.record(sp, {"scores": m["scores"], "names_person": m.get("names_person", False),
  73 | +                        "risk": list(m.get("risk") or []), "topics": list(m.get("topics") or []),
  74 | +                        "reason": m.get("reason") or ""}, ctx, M.judge(sp, ctx),
  75 | +                   dict(m.get("mined") or {}, derived_from=derived))
  76 | +    rec["rank_score"] = M.rank_score(rec)
  77 | +    if m.get("source_key"):
  78 | +        rec["source_key"] = m["source_key"]
  79 | +    rec["derived_from"] = derived
  80 | +    return rec
  81 | +
  82 | +
  83 | +def holds(m, results_dir):
  84 | +    """The newest lock pre-check HOLD on the parent's exact span (its video, start and end to the millisecond, its own
  85 | +    text as the approved text, its trim fields, as a hook or a clip) under the CURRENT decoder and rules
  86 | +    (lock_precheck.answer: entries under any other decoder or rules are never read). -> the entry, or None."""
  87 | +    import lock_precheck as LP
  88 | +    base = LP.segments_of([m])[0]
  89 | +    best = None
  90 | +    for role in ("hook", "clip"):
  91 | +        e = LP.answer(dict(base, role=role), results_dir)
  92 | +        if e is not None and e.get("outcome") == "hold" and (best is None or str(e.get("at") or "") >= best[0]):
  93 | +            best = (str(e.get("at") or ""), e)
  94 | +    return best[1] if best else None
  95 | +
  96 | +
  97 | +def held_word(m, src, entry):
  98 | +    """The index (into src.tokens) of the parent's first word that the HOLD is about, placed on THIS side: the entry's
  99 | +    second reading (as_spoken.text) against the parent's own text, through this side's canon and ruling 84's class
 100 | +    (attest.class_84, as decide() judges an adoption): the first difference outside the class whose approved side is
 101 | +    not empty, at its tokens' first occurrence among the parent's words (canon.canon_spans). Recomputed from the texts,
 102 | +    it does not depend on the canon the entry was written under. -> int, or None when it cannot be placed (no second
 103 | +    reading, no such difference, an insert on the spoken side alone, or tokens not found): then no variant."""
 104 | +    spoken = ((entry or {}).get("as_spoken") or {}).get("text") if isinstance(entry, dict) else None
 105 | +    if not isinstance(spoken, str) or not spoken.strip():
 106 | +        return None
 107 | +    w0, w1 = m["words"]
 108 | +    spans = C.canon_spans([t.get("word") or "" for t in src.tokens[w0:w1 + 1]])
 109 | +    toks = [t for t, _, _ in spans]
 110 | +    for d in AT.class_84(spoken, m["text"]):
 111 | +        if d["class"] is not None:
 112 | +            continue
 113 | +        want = d["approved"].split()
 114 | +        if not want:
 115 | +            return None                                  # the second reading inserted it: nowhere to end before
 116 | +        for i in range(len(toks) - len(want) + 1):
 117 | +            if toks[i:i + len(want)] == want:
 118 | +                return w0 + spans[i][1]
 119 | +        return None
 120 | +    return None
 121 | +
 122 | +
 123 | +def for_pool(moments, sources, ctx, results_dir, ceil_s):
 124 | +    """The ruling-104 variants for this build's pool. -> (variants, {parent id: why it has none / which it got},
 125 | +    {the ids of the parents a current hold makes final: replaced by their variants})."""
 126 | +    import context_integrity as CI
 127 | +    have = {m["moment_id"] for m in moments}
 128 | +    out, notes, replaced = [], {}, set()
 129 | +    for m in moments:
 130 | +        mid = m["moment_id"]
 131 | +        k0, k1 = m.get("sentences") or (None, None)
 132 | +        if not (isinstance(k0, int) and isinstance(k1, int) and k1 > k0):
 133 | +            continue                                     # one sentence: no earlier boundary
 134 | +        wanted = []
 135 | +        e = holds(m, results_dir)
 136 | +        try:
 137 | +            src = CI.source_for(m, sources)
 138 | +        except KeyError:
 139 | +            if e is not None or float(m.get("duration_s") or 0) > ceil_s:
 140 | +                notes[mid] = "no variant: its word record is not in this build"
 141 | +            continue
 142 | +        if e is not None:
 143 | +            if str(e.get("reason") or "").startswith(CUT_HOLD):
 144 | +                wanted.append((k1 - 1, f"a tail the cut cannot make ({str(e.get('reason'))[:160]})"))
 145 | +            else:
 146 | +                i = held_word(m, src, e)
 147 | +                ks = [k for k in range(k0, k1) if i is not None and src.sentences[k][1] < i]
 148 | +                if ks:
 149 | +                    wanted.append((ks[-1], f"a held word after the boundary: {src.tokens[i].get('word')!r} at "
 150 | +                                           f"{src.tokens[i].get('start')} s (the lock pre-check's hold, "
 151 | +                                           f"{e.get('request_id')})"))
 152 | +                else:                                    # no variant can leave the held word out: none at all,
 153 | +                    notes[mid] = ("no variant: the held word cannot be placed" if i is None else   # not even the
 154 | +                                  "no variant: the held word is in its first sentence")             # ceiling's (qwen,
 155 | +                    continue                                                                         # audit 1441 C2)
 156 | +        if float(m.get("duration_s") or 0) > ceil_s:
 157 | +            t0 = float(m["start"])
 158 | +            ks = [k for k in range(k0, k1) if float(src.tokens[src.sentences[k][1]]["end"]) - t0 <= ceil_s]
 159 | +            if ks:
 160 | +                wanted.append((ks[-1], f"the seconds ceiling ({float(m['duration_s']):.2f} s > {ceil_s:g} s)"))
 161 | +            else:
 162 | +                notes[mid] = f"no variant: no earlier boundary within {ceil_s:g} s"
 163 | +        if not wanted:
 164 | +            continue
 165 | +        k = min(x[0] for x in wanted)
 166 | +        if e is not None:
 167 | +            replaced.add(mid)                            # ruling 103: its hold is final; only the variant may save it
 168 | +        v = variant(m, src, k, ctx, "; ".join(w for _, w in wanted))
 169 | +        if v["moment_id"] in have:
 170 | +            notes[mid] = f"its variant {v['moment_id']} is already in the pool"
 171 | +            continue
 172 | +        have.add(v["moment_id"])
 173 | +        out.append(v)
 174 | +        notes[mid] = (f"variant {v['moment_id']} ({v['duration_s']} s, ends {v['text'][-60:]!r})"
 175 | +                      + (", in its place" if mid in replaced else ", beside it"))
 176 | +    return out, notes, replaced
 177 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 178 | index d2b60dd..b646c26 100644
 179 | --- a/tests/package/proof_ledger.py
 180 | +++ b/tests/package/proof_ledger.py
 181 | @@ -70,6 +70,7 @@ import providers as P  # noqa: E402
 182 |  import speakers as SP  # noqa: E402
 183 |  import spotlight as SPOT  # noqa: E402
 184 |  import lock_precheck as LP  # noqa: E402
 185 | +import tail_variant as TV  # noqa: E402
 186 |  
 187 |  REGISTRY = os.path.join(HERE, "proof", "CANDIDATES.json")     # ruling 66: the candidates, kept
 188 |  SPOTLIGHTS = os.path.join(HERE, "proof", "SPOTLIGHTS.json")   # ruling 90: one spotlight per channel per ET day
 189 | @@ -131,6 +132,20 @@ def applied(router):
 190 |      return applies
 191 |  
 192 |  
 193 | +def with_variants(moments, sources, ctx, inputs, say, results_dir=None):
 194 | +    """RULING 104 (14:12 Nov 14): the build's pool with the tail-side variants (tail_variant.for_pool: a current lock
 195 | +    pre-check hold on the parent's span, a cut the render cannot make, the spotlight's seconds ceiling), so every gate
 196 | +    judges them from the start, the clip scorer included (its pool is made from these moments). A parent whose current
 197 | +    hold is final is replaced by its variant; a parent over the ceiling stays beside it. inputs["ruling_104"] records
 198 | +    them, the replaced parents, and why each parent has a variant or none. -> the new list of moments."""
 199 | +    variants, notes, replaced = TV.for_pool(moments, sources, ctx, results_dir or LP.RESULTS, SPOT.SPOT_S[1])
 200 | +    inputs["ruling_104"] = {"variants": [v["moment_id"] for v in variants], "replaced": sorted(replaced),
 201 | +                            "notes": notes}
 202 | +    say(f"  RULING 104 (the tail-side twin): {len(variants)} variant(s) in the pool, {len(replaced)} held parent(s) "
 203 | +        f"replaced by theirs (ruling 103: the hold is final)" + "".join(f"; {k}: {w}" for k, w in sorted(notes.items())))
 204 | +    return [m for m in moments if m["moment_id"] not in replaced] + variants
 205 | +
 206 | +
 207 |  def start_refused(spent0):
 208 |      """RULING 48, with the orchestrator's stop of 13:02 Nov 14 (the $16 stop passed with leave; at $19 stop and tell on
 209 |      STATE line 1 in capitals): no build starts at or over PL.LY_STOP_USD. -> the refusal line, or None."""
 210 | @@ -259,6 +274,7 @@ def main(argv=None):
 211 |      moments, sources, inputs = LB.build_inputs(rows, ctx, log=say, word_pass=wp,
 212 |                                                 ledger_store=os.path.join(LB.INGEST_ROOT, "data", "editorial"))
 213 |      inputs["word_pass"] = wp_rep
 214 | +    moments = with_variants(moments, sources, ctx, inputs, say)   # RULING 104: beside their parents, every gate again
 215 |      with open(os.path.join(out_dir, "inputs.json"), "w") as f:
 216 |          json.dump({"since": since.isoformat(), "publish_window_h": a.hours, "delivered_pins": pins,
 217 |                     "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments},
 218 | diff --git a/tests/package/test_ruling_104.py b/tests/package/test_ruling_104.py
 219 | new file mode 100644
 220 | index 0000000..728f40a
 221 | --- /dev/null
 222 | +++ b/tests/package/test_ruling_104.py
 223 | @@ -0,0 +1,262 @@
 224 | +#!/usr/bin/env python3
 225 | +"""RULING 104 (orchestrator 14:12 ET Nov 14), THE TAIL-SIDE TWIN (pipeline/tail_variant.py and its use in the ledger
 226 | +build and the spotlight): a variant ENDING at an earlier sentence boundary of the mined moment, when that keeps it lawful
 227 | +(a held word after the boundary, a tail the cut cannot make, the seconds ceiling); a new span that faces every gate,
 228 | +recorded as derived from its parent row. The case: Blockware Solutions 06d34e15, held on "401k".
 229 | +Offline: word-timed test sources, a temporary results directory."""
 230 | +import copy
 231 | +import json
 232 | +import os
 233 | +import sys
 234 | +import tempfile
 235 | +import unittest
 236 | +import unittest.mock
 237 | +
 238 | +HERE = os.path.dirname(os.path.abspath(__file__))
 239 | +REPO = os.path.dirname(os.path.dirname(HERE))
 240 | +for _p in ("pipeline", "tests/package", "tests/eligibility"):
 241 | +    sys.path.insert(0, os.path.join(REPO, _p))
 242 | +import eligibility as E  # noqa: E402
 243 | +import lock_precheck as LP  # noqa: E402
 244 | +import moments as M  # noqa: E402
 245 | +import proof_ledger as PLG  # noqa: E402
 246 | +import spotlight as SPOT  # noqa: E402
 247 | +import tail_variant as TV  # noqa: E402
 248 | +import test_spotlight as TS  # noqa: E402
 249 | +from test_eligibility import NOW, REG, source  # noqa: E402
 250 | +
 251 | +SENTENCES = ["On my 20th birthday, I sold every stock in my Roth IRA and put it all into Bitcoin.",
 252 | +             "That ended up being one of the best financial decisions I've ever made, but not for the reason most "
 253 | +             "people think.",
 254 | +             "I'm 26 now, and I still don't use my Roth IRA.",
 255 | +             "I don't have a 401k.",
 256 | +             "I don't own a single share of any index fund, and I'm on pace to be financially independent by 45."]
 257 | +CTX = E.Context(NOW, REG)
 258 | +META = {"scores": {"contempt_outrage": 0, "hook_first_2s": 5, "quotable": 4, "stakes": 5, "stance": 4,     # the real
 259 | +                   "stands_alone": 5, "surprising_fact": 4},                                         # row's, build 11
 260 | +        "names_person": False, "risk": [], "topics": ["bitcoin"], "reason": "Strong personal narrative hook"}
 261 | +
 262 | +
 263 | +def parent(src, k0=0, k1=4, vid="7BqLu-wzbU0"):
 264 | +    sp = E.Span(src, k0, k1)
 265 | +    m = M.record(sp, META, CTX, M.judge(sp, CTX), {"ledger_moment_id": "06d34e155feae654ee56"})
 266 | +    m["rank_score"] = M.rank_score(m)
 267 | +    m["source_key"] = vid
 268 | +    return m
 269 | +
 270 | +
 271 | +def blockware():
 272 | +    src = source(SENTENCES, vid="7BqLu-wzbU0")
 273 | +    return src, parent(src)
 274 | +
 275 | +
 276 | +def hold(m, at="2026-11-14T19:51:07Z", spoken=None, reason="ruling 72/84: ... at [['401k', '401']]",
 277 | +         outcome="hold", role="hook", text=None, rules=None):
 278 | +    return {"rules": LP.RULES if rules is None else rules,
 279 | +            "request_id": "pp-selectid.ledger_x.1", "video_id": m["video_id"], "start": m["start"], "end": m["end"],
 280 | +            "window": [round(m["start"], 3), round(m["end"], 3)], "role": role,
 281 | +            "approved_text": m["text"] if text is None else text, "outcome": outcome, "reason": reason, "at": at,
 282 | +            "as_spoken": {"verdict": outcome, "text": m["text"].replace("401k.", "401 ,") if spoken is None
 283 | +                          else spoken}}
 284 | +
 285 | +
 286 | +def put(d, m, entries, decoder=LP.DECODER):
 287 | +    p = os.path.join(d, f"{m['video_id']}.{round(m['start'], 3):.3f}-{round(m['end'], 3):.3f}.{decoder}.json")
 288 | +    with open(p, "w") as f:
 289 | +        json.dump(entries, f)
 290 | +
 291 | +
 292 | +class TestTheVariant(unittest.TestCase):
 293 | +    def test_it_ends_at_the_boundary_is_a_new_span_and_names_its_parent(self):
 294 | +        src, m = blockware()
 295 | +        v = TV.variant(m, src, 2, CTX, "a held word")
 296 | +        self.assertEqual(v["text"], " ".join(SENTENCES[:3]))
 297 | +        self.assertEqual((v["sentences"], v["start"], v["end"]), ([0, 2], m["start"], src.tokens[src.sentences[2][1]]["end"]))
 298 | +        self.assertNotEqual(v["moment_id"], m["moment_id"])                            # its own id
 299 | +        self.assertEqual(v["moment_id"], M.record(E.Span(src, 0, 2), META, CTX, M.judge(E.Span(src, 0, 2), CTX),
 300 | +                                                  {})["moment_id"])                    # the span's own
 301 | +        d = v["derived_from"]
 302 | +        self.assertEqual((d["ruling"], d["from"], d["ledger_moment_id"], d["sentences"], d["was"]),
 303 | +                         (104, m["moment_id"], "06d34e155feae654ee56", [0, 2], [0, 4]))
 304 | +        self.assertEqual(d["left_out"], " ".join(SENTENCES[3:]))
 305 | +        self.assertEqual(v["mined"]["derived_from"], d)                                 # in its mined record too
 306 | +        self.assertEqual((v["source_key"], v["scores"], v["topics"]), (m["source_key"], m["scores"], m["topics"]))
 307 | +        self.assertEqual(set(v["eligibility"]), {"hook", "clip"})                       # judged afresh on its span
 308 | +        for k in (4, 5, -1, "2"):
 309 | +            with self.assertRaises(ValueError):
 310 | +                TV.variant(m, src, k, CTX, "x")
 311 | +
 312 | +
 313 | +class TestTheHeldWord(unittest.TestCase):
 314 | +    def test_the_401k_hold_is_placed_on_its_word_from_the_texts(self):
 315 | +        src, m = blockware()
 316 | +        i = TV.held_word(m, src, hold(m))
 317 | +        self.assertEqual(src.tokens[i]["word"], "401k.")
 318 | +        self.assertEqual(i, src.sentences[3][0] + 4)                                   # "I don't have a 401k."
 319 | +
 320 | +    def test_a_difference_inside_ruling_84_s_class_is_passed_over(self):
 321 | +        """A one-function-word substitution earlier in the span is in ruling 84's class: the held word is still 401k."""
 322 | +        src, m = blockware()
 323 | +        spoken = m["text"].replace("one of the best", "one of a best").replace("401k.", "401 ,")
 324 | +        self.assertEqual(src.tokens[TV.held_word(m, src, hold(m, spoken=spoken))]["word"], "401k.")
 325 | +
 326 | +    def test_an_insert_before_the_hold_cannot_be_placed_so_no_variant(self):
 327 | +        """The second reading inserts a number in the FIRST sentence and differs on 401k: no variant can leave the
 328 | +        insert out, so the word is not placed (no variant), never the later 401k."""
 329 | +        src, m = blockware()
 330 | +        spoken = m["text"].replace("into Bitcoin.", "into Bitcoin 21.").replace("401k.", "401 ,")
 331 | +        self.assertIsNone(TV.held_word(m, src, hold(m, spoken=spoken)))
 332 | +
 333 | +    def test_what_cannot_be_placed_gives_none(self):
 334 | +        src, m = blockware()
 335 | +        self.assertIsNone(TV.held_word(m, src, hold(m, spoken="")))                          # no second reading
 336 | +        self.assertIsNone(TV.held_word(m, src, dict(hold(m), as_spoken=None)))
 337 | +        self.assertIsNone(TV.held_word(m, src, hold(m, spoken=m["text"].replace("401k.", "401k, um,"))))  # a filler
 338 | +        self.assertIsNone(TV.held_word(m, src, hold(m, spoken=m["text"].replace("Bitcoin.", "Bitcoin 21."))))  # inserted
 339 | +
 340 | +
 341 | +class TestTheHolds(unittest.TestCase):
 342 | +    def setUp(self):
 343 | +        self.d = tempfile.TemporaryDirectory()
 344 | +        self.addCleanup(self.d.cleanup)
 345 | +
 346 | +    def test_the_newest_hold_on_the_exact_span_under_the_current_decoder_and_rules(self):
 347 | +        src, m = blockware()
 348 | +        self.assertIsNone(TV.holds(m, self.d.name))
 349 | +        put(self.d.name, m, [hold(m, at="2026-11-14T20:00:00Z", reason="an older decoder")], decoder="c705b20ed800")
 350 | +        self.assertIsNone(TV.holds(m, self.d.name))                                     # never read: not final now
 351 | +        put(self.d.name, m, [hold(m, at="2026-11-14T18:00:00Z", reason="old"),
 352 | +                             hold(m, at="2026-11-14T20:30:00Z", reason="older rules",
 353 | +                                  rules="ruling 17 + ruling 72 + ruling 73 + ruling 84"),   # never read
 354 | +                             hold(m, at="2026-11-14T18:51:07Z", reason="new"),
 355 | +                             hold(m, outcome="no_difference", at="2026-11-14T18:30:00Z"),       # an older pass
 356 | +                             hold(m, at="2026-11-14T19:30:00Z", text="another text"),           # another span's text
 357 | +                             dict(hold(m, at="2026-11-14T19:31:00Z"), window=[0.0, 9.0])])      # another window
 358 | +        self.assertEqual(TV.holds(m, self.d.name)["reason"], "new")
 359 | +        passed = tempfile.TemporaryDirectory()                                           # a NEWER pass: not held now
 360 | +        self.addCleanup(passed.cleanup)
 361 | +        put(passed.name, m, [hold(m, at="2026-11-14T18:51:07Z"), hold(m, outcome="no_difference",
 362 | +                                                                   at="2026-11-14T19:00:00Z")])
 363 | +        self.assertIsNone(TV.holds(m, passed.name))
 364 | +        clip = tempfile.TemporaryDirectory()                                            # held as a medley clip
 365 | +        self.addCleanup(clip.cleanup)
 366 | +        put(clip.name, m, [hold(m, role="clip", reason="as a clip")])
 367 | +        self.assertEqual(TV.holds(m, clip.name)["reason"], "as a clip")
 368 | +        put(clip.name, m, [hold(m, role="clip", reason="as a clip", at="2026-11-14T19:00:00Z"),
 369 | +                           hold(m, role="hook", reason="as a hook, newer", at="2026-11-14T19:10:00Z")])
 370 | +        self.assertEqual(TV.holds(m, clip.name)["reason"], "as a hook, newer")      # the newest of the two roles
 371 | +        with open(os.path.join(self.d.name, f"{m['video_id']}.0.000-1.000.c705b20ed800.json"), "w") as f:
 372 | +            f.write("{ broken")                                                                  # never read: another span
 373 | +        self.assertEqual(TV.holds(m, self.d.name)["reason"], "new")
 374 | +
 375 | +
 376 | +class TestThePool(unittest.TestCase):
 377 | +    def setUp(self):
 378 | +        self.d = tempfile.TemporaryDirectory()
 379 | +        self.addCleanup(self.d.cleanup)
 380 | +
 381 | +    def pool(self, ms, sources, ceil_s=35.0):
 382 | +        vs, notes, replaced = TV.for_pool(ms, sources, CTX, self.d.name, ceil_s)
 383 | +        self.replaced = replaced
 384 | +        return vs, notes
 385 | +
 386 | +    def test_blockware_held_on_401k_gives_the_variant_ending_before_it(self):
 387 | +        src, m = blockware()
 388 | +        put(self.d.name, m, [hold(m)])
 389 | +        vs, notes = self.pool([m], {"7BqLu-wzbU0": src})
 390 | +        self.assertEqual([v["text"] for v in vs], [" ".join(SENTENCES[:3])])     # "...I still don't use my Roth IRA."
 391 | +        self.assertIn("a held word after the boundary: '401k.'", vs[0]["derived_from"]["why"])
 392 | +        self.assertIn(vs[0]["moment_id"], notes[m["moment_id"]])
 393 | +        self.assertEqual(self.replaced, {m["moment_id"]})                              # its hold is final
 394 | +
 395 | +    def test_a_cut_the_render_cannot_make_drops_the_last_sentence(self):
 396 | +        src, m = blockware()
 397 | +        put(self.d.name, m, [hold(m, reason="ruling 73: the render cannot cut this span: the OUT edge")])
 398 | +        vs, _ = self.pool([m], {"7BqLu-wzbU0": src})
 399 | +        self.assertEqual(vs[0]["sentences"], [0, 3])
 400 | +
 401 | +    def test_the_seconds_ceiling_gives_the_longest_variant_within_it(self):
 402 | +        src, m = blockware()
 403 | +        limit = src.tokens[src.sentences[2][1]]["end"] - m["start"] + 0.01           # sentences 0-2 fit, 0-3 do not
 404 | +        vs, _ = self.pool([m], {"7BqLu-wzbU0": src}, ceil_s=limit)
 405 | +        self.assertEqual(vs[0]["sentences"], [0, 2])
 406 | +        self.assertIn("the seconds ceiling", vs[0]["derived_from"]["why"])
 407 | +        self.assertEqual(self.replaced, set())                                          # the parent stays beside it
 408 | +        put(self.d.name, m, [hold(m, reason="ruling 73: the render cannot cut this span")])   # both: the shorter
 409 | +        vs, _ = self.pool([m], {"7BqLu-wzbU0": src}, ceil_s=limit)
 410 | +        self.assertEqual(vs[0]["sentences"], [0, 2])
 411 | +        self.assertIn("a tail the cut cannot make", vs[0]["derived_from"]["why"])
 412 | +
 413 | +    def test_no_variant_where_none_keeps_it_lawful(self):
 414 | +        src, m = blockware()
 415 | +        put(self.d.name, m, [hold(m, spoken=m["text"].replace("20th", "21st"))])       # held in its FIRST sentence
 416 | +        vs, notes = self.pool([m], {"7BqLu-wzbU0": src})
 417 | +        self.assertEqual((vs, notes[m["moment_id"]]), ([], "no variant: the held word is in its first sentence"))
 418 | +        limit = src.tokens[src.sentences[2][1]]["end"] - m["start"] + 0.01            # and over the ceiling too:
 419 | +        vs, notes = self.pool([m], {"7BqLu-wzbU0": src}, ceil_s=limit)                 # no ceiling variant either
 420 | +        self.assertEqual((vs, notes[m["moment_id"]], self.replaced),                   # (it would keep the held
 421 | +                         ([], "no variant: the held word is in its first sentence", set()))   # word: qwen C2)
 422 | +        one = parent(src, 2, 2)                                                           # one sentence: no boundary
 423 | +        put(self.d.name, one, [hold(one)])
 424 | +        self.assertEqual(self.pool([one], {"7BqLu-wzbU0": src}), ([], {}))
 425 | +        self.assertEqual(self.pool([m], {}), ([], {m["moment_id"]: "no variant: its word record is not in this build"}))
 426 | +        clean = blockware()[1]                                                            # no hold, under the ceiling
 427 | +        clean["start"] += 0.0005                                                          # (another span on file)
 428 | +        self.assertEqual(self.pool([clean], {"7BqLu-wzbU0": src}), ([], {}))
 429 | +
 430 | +    def test_a_variant_already_in_the_pool_is_not_added_twice(self):
 431 | +        src, m = blockware()
 432 | +        put(self.d.name, m, [hold(m)])
 433 | +        v = TV.variant(m, src, 2, CTX, "x")
 434 | +        vs, notes = self.pool([m, v], {"7BqLu-wzbU0": src})
 435 | +        self.assertEqual(vs, [])
 436 | +        self.assertIn("already in the pool", notes[m["moment_id"]])
 437 | +
 438 | +    def test_the_ledger_build_replaces_a_held_parent_and_keeps_one_over_the_ceiling(self):
 439 | +        src, m = blockware()
 440 | +        other = parent(src, 3, 4)                                                         # another moment, no trigger
 441 | +        put(self.d.name, m, [hold(m)])
 442 | +        inputs, said = {}, []
 443 | +        out = PLG.with_variants([m, other], {"7BqLu-wzbU0": src}, CTX, inputs, said.append, results_dir=self.d.name)
 444 | +        self.assertEqual([x["moment_id"] for x in out], [other["moment_id"], inputs["ruling_104"]["variants"][0]])
 445 | +        self.assertEqual(out[1]["text"], " ".join(SENTENCES[:3]))
 446 | +        self.assertEqual(inputs["ruling_104"]["replaced"], [m["moment_id"]])
 447 | +        self.assertIn("1 variant(s) in the pool, 1 held parent(s) replaced", said[0])
 448 | +        limit = src.tokens[src.sentences[2][1]]["end"] - m["start"] + 0.01
 449 | +        clean = tempfile.TemporaryDirectory()
 450 | +        self.addCleanup(clean.cleanup)
 451 | +        with unittest.mock.patch.object(SPOT, "SPOT_S", (12.0, limit)):                # over the ceiling: beside it
 452 | +            out = PLG.with_variants([m], {"7BqLu-wzbU0": src}, CTX, {}, said.append, results_dir=clean.name)
 453 | +        self.assertEqual([x["sentences"] for x in out], [[0, 4], [0, 2]])
 454 | +
 455 | +
 456 | +class TestTheSpotlight(unittest.TestCase):
 457 | +    def test_a_variant_is_never_snapped_outward(self):
 458 | +        src, m = blockware()
 459 | +        short = TV.variant(m, src, 1, CTX, "x")                                          # two sentences, under 13.7 s
 460 | +        self.assertLess(short["duration_s"], SPOT.SNAP_TO_S)
 461 | +        caps = lambda vid: ([], None)
 462 | +        v, why = SPOT.snap(short, {"7BqLu-wzbU0": src}, CTX, captions_for=caps)
 463 | +        self.assertIsNone(v)
 464 | +        self.assertIn("never snapped outward", why)
 465 | +        plain = dict(short)
 466 | +        plain.pop("derived_from")
 467 | +        v, _ = SPOT.snap(plain, {"7BqLu-wzbU0": src}, CTX, captions_for=caps)         # any other moment: snapped
 468 | +        self.assertIsNotNone(v)
 469 | +        long_ = TV.variant(m, src, 2, CTX, "x")
 470 | +        self.assertGreaterEqual(long_["duration_s"], SPOT.SNAP_TO_S)
 471 | +        self.assertIs(SPOT.snap(long_, {"7BqLu-wzbU0": src}, CTX, captions_for=caps)[0], long_)
 472 | +
 473 | +    def test_the_spotlight_pin_records_where_the_variant_came_from(self):
 474 | +        m = TS.moment()
 475 | +        pk, why, *_ = TS.package(m=m)
 476 | +        self.assertIsNone(why)
 477 | +        self.assertNotIn("derived_from", pk["spotlight"])                               # every other pin as before
 478 | +        d = {"ruling": 104, "from": "06d34e155feae654ee56", "sentences": [0, 2], "was": [0, 4], "why": "x"}
 479 | +        pk, why, *_ = TS.package(m=dict(copy.deepcopy(m), derived_from=d))
 480 | +        self.assertIsNone(why)
 481 | +        self.assertEqual(pk["spotlight"]["derived_from"], d)
 482 | +
 483 | +
 484 | +if __name__ == "__main__":
 485 | +    unittest.main()
 486 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff and the facts below; if uncertain, say so; do not guess. Be specific: file:line and a concrete
sequence that breaks it.

BACKGROUND (static):
- A MOMENT is a mined span of whole sentences of one word-timed source (moments.record over eligibility.Span(source,
  k0, k1)): its text is the words as spoken, its id is the span's own, and eligibility is judged on the span.
- Each build:
  - adds the ledger's moments to a pool (tests/package/proof_ledger.py, LB.build_inputs);
  - sends the pool to the integrator's clip scorer (the ALONE rating);
  - runs the medley search (package.build) and then the SPOTLIGHT (spotlight.build).
- The spotlight's stages run cheapest first:
  - a free pool (usable, under the 35 s ceiling SPOT_S[1]; a moment under SNAP_TO_S 13.7 s is "snapped OUTWARD" by
    spotlight.snap: whole following sentences are added, then preceding ones);
  - step A from both families, CUTTABLE, the opener rating, the visual check, ALONE >= 4;
  - then, best first (rank_key), up to 3 finalists face the exclusion verdict, the render's lock pre-check
    (lock_precheck), the writes and every gate. The first that passes seals a pin.
- The lock pre-check's answers are list-of-entry files <video>.<start>-<end>.<decoder>.json in the integrator's results
  dir. An entry has outcome ("hold", "no_difference", ...), window, role, approved_text, reason, and as_spoken {verdict,
  differences, text: the second recogniser's full reading}.
- attest.class_84(spoken, approved) is this side's copy of the integrator's ruling-84 class: one dict per difference,
  {"spoken", "approved", "class"}; class None is a difference outside the class (a number, a name, a negation, or a
  substitution other than one function word): it holds. canon.canon_spans(words) gives (token, first word index, last
  word index).
- THE CASE: Blockware Solutions 06d34e15 (video 7BqLu-wzbU0, 0.000-22.940 s, hook 4, ALONE 4.0) is held because the
  second recogniser hears "I don't have a 401" where the lock says "401k". The integrator ran ruling 103's targeted
  re-listen on it; the hold is FINAL. The orchestrator: "if it holds, seal the tail-side variant ending '...I still don't
  use my Roth IRA.' if it passes every gate. It expires 00:00 ET: this is the spotlight demo PBX is waiting for."

THE ORCHESTRATOR'S RULING (14:12 ET Nov 14), verbatim:
"RULING 104, THE TAIL-SIDE TWIN: a spotlight (and a medley hook or clip) may be sealed as a variant that ENDS at an
earlier sentence boundary of the mined moment, when that is what keeps it lawful (a held word after the boundary, a tail
the cut cannot make, the seconds ceiling). It is a new span: it faces every gate again from the start (step A both
families, CUTTABLE at the new OUT, ALONE >= 4, the opener rating, the 12 s floor, the visual check, the lock pre-check),
and the variant is recorded as derived from its parent row. Omission is judged by step A as always: a variant that drops
the speaker's own condition or conclusion fails there."
And: "(3) Blockware 06d34e15: FIRST the re-listen (103) on '401k'; if it passes, seal the full 22.94 s spotlight; if it
holds, seal the tail-side variant ending '...I still don't use my Roth IRA.' if it passes every gate."

UNCHANGED CODE THIS CHANGE RELIES ON (not in the diff; verify against these facts, do not assume them away):
- The pool (proof_ledger.main) is built from `moments` after this change's with_variants(), so the clip scorer, the
  medley and the spotlight all see each variant as a moment.
- package.usable / spotlight.pool keep one video at most once per line-up (L-y 4) and apply every free rule to each
  moment, the variant included.
- Every paid gate (step A both families, CUTTABLE, the opener rating, the visual check, ALONE, exclusion, the lock
  pre-check under the CURRENT decoder and rules, the writes) runs on each pool moment as before. Nothing in the diff
  skips a gate for a variant.
- package_pin seals the segment (video, start, end, text, ...). pk["spotlight"] rides on the pin OUTSIDE the seal
  (moments_package.spotlight).

THE CHANGE (the diff follows):
1. pipeline/tail_variant.py (new):
   - variant(m, src, k, ctx, why): the parent cut to end at its sentence k (k0 <= k < k1), made by
     moments.record(E.Span(src, k0, k)): eligibility judged afresh, its own id, the parent's scores, topics and risk.
     "derived_from" (ruling 104, the parent id, its ledger row, the sentences, why, the words left out) is set on it
     and on its mined record.
   - holds(m, results_dir): the newest HOLD entry on the parent's exact span (window, role hook or clip, approved_text
     equal to the parent's text), under ANY decoder and rules. It only proposes a candidate; the variant faces the
     pre-check under the current ones.
   - held_word(m, src, entry): the parent's first word the hold is about, placed on THIS side by class_84 on the entry's
     second reading against the parent's text (so it does not depend on the canon the entry was written under):
     - the first difference with class None and a non-empty approved side, at its tokens' first occurrence among the
       parent's words;
     - None when it cannot be placed, including an insert on the spoken side, which no variant can leave out.
   - for_pool(moments, sources, ctx, results_dir, ceil_s): per parent with more than one sentence, three triggers:
     - a hold: the variant ends at the last boundary before the held word;
     - ruling 73's cut hold: the last sentence goes;
     - over the ceiling: the longest variant within it.
     When several apply, the shorter variant. No duplicate id. The notes say why each parent has a variant or none.
   - parents_first(ranked): a variant ranked above its own parent moves to just after it; nothing else moves.
2. tests/package/proof_ledger.py: with_variants() adds the variants BESIDE their parents right after the inputs are
   built, records them in inputs["ruling_104"] and prints a RULING 104 line.
3. pipeline/spotlight.py:
   - snap() never snaps a ruling-104 variant outward: that would put back the words it leaves out.
   - finalist_order() = parents_first(sorted(rank_key)), so the full clip is tried first (the 14:12 order).
   - pk["spotlight"]["derived_from"] is set when the moment is a variant (outside the seal).
4. Tests: test_ruling_104.py (new, 16). 19 mutations.

ATTACK:
(a) Can a variant reach a pin without facing every gate, or with its parent's verdicts (cached step A, ALONE, the
    pre-check) instead of its own? Can it be snapped, trimmed or extended back over the held words?
(b) Can a variant still contain the held word (the boundary, the first occurrence, a repeated token)? Can it end
    mid-sentence?
(c) Can the full clip lose its turn (a variant sealed before the parent's own re-listen and pre-check), or a variant
    be added when no trigger applies?
(d) Is "recorded as derived from its parent row" met (on the moment, its mined record, the build record and the
    spotlight pin)? Can the pin's seal change for a pin that is not a variant?
(e) Anything else that could seal a wrong pin, double a moment in a line-up, or spend without a trigger.

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete sequence), then
"SHIP: yes / no / yes with conditions".

CHANGED AFTER CYCLE 1. Review the diff AS IT STANDS NOW. Items 1-3 change as follows:
- holds(m, results_dir) reads the parent's answer under the CURRENT decoder and rules only (lock_precheck.answer: the
  newest answer on the exact span as a hook, then as a clip; the newer of the two). Under ruling 103's rules a current
  hold is final, its re-listen included. An older decoder's or older rules' hold is not read.
- for_pool() returns (variants, notes, replaced). A parent with a current hold, or ruling 73's cut hold, is REPLACED by
  its variant (proof_ledger.with_variants drops it from the pool; inputs["ruling_104"]["replaced"]). A parent over the
  ceiling stays beside its variant.
- parents_first() and spotlight.finalist_order() are removed; spotlight's finalists are ordered as before (rank_key).
CYCLE 2 ATTACK, in addition to (a)-(e):
(f) Can a replaced parent still reach a line-up, a finalist's place or a pin in that build?
(g) Can a variant appear while its parent's CURRENT answer is a pass (no hold), or survive a newer pass?

CHANGED AFTER CYCLE 2 (cycle 3 reviews only this, on the diff as it stands):
- tail_variant.for_pool: when a parent's CURRENT hold cannot be relieved (the held word cannot be placed, or it sits in
  the first sentence), it now gets NO variant at all, not even the ceiling trigger's (that variant would keep the held
  word), and it is not replaced. One `continue`, with a test (the first-sentence hold over the ceiling) and a mutation.
CYCLE 3 ATTACK: (h) Can a current hold still produce a variant that contains the held word or difference? (i) Did the
fix change any other trigger's outcome (a cut hold, a placeable hold, the ceiling alone)?


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
