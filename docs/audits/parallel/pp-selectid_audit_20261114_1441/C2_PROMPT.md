# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_1441
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 170 s finish=stop usage in 16407 / out 4968 usd~0.124 (upper-bound price)

<medium> **tail_variant.py:190 — the held-word boundary test uses `<` on the *token* index against the sentence's last token index, but `src.sentences[k][1]` is the *last word index* of sentence k, so a held word that is the FIRST word of sentence k+1...** — actually this is correct; see (b) below. Withdrawn. </medium>

Let me do this properly, clause by clause.

**(a) Gates — what the diff actually does vs. what ruling 104 requires**

The diff only (i) inserts variants into the pool before `inputs.json` is written (proof_ledger.py:265), (ii) changes the finalist order and snap, (iii) adds a key to `pk["spotlight"]`. The background facts state every paid gate runs on each pool moment as before and nothing skips a gate for a variant. So the "faces every gate" requirement is met *structurally* — the variant is just another moment. What I cannot verify from the diff: whether the *cached* step A / ALONE / pre-check verdicts are keyed by moment_id (in which case the variant, having its own id — test line 346-348 asserts the id is the span's own — gets its own verdicts) or by (video, start, end) — in which case the variant, whose start equals the parent's start but whose end differs, still gets its own. Either way the spans differ, so no collision. What I *can* verify: `variant()` copies `m["scores"]` (tail_variant.py:103) — the parent's *mined* scores, not re-rated. That is by design ("the parent's scores, topics and risk" per the ruling), so not a violation, but note the ALONE rating is a separate, later rating, so this is consistent.

One real gap: **`for_pool` never checks the 12 s floor** (ruling 104: "the 12 s floor"). The ruling says the variant "faces every gate again from the start (… the 12 s floor …)", which is fine — the gates will catch it. But `snap()` (spotlight.py:17-19) now *refuses* to snap a variant outward, and the snap is what rescued under-13.7 s moments in the free pool. A variant of, say, 2 sentences at 9 s that would previously have been snapped to 13.7+ s now stays 9 s and must pass the 12 s floor at step A. That's lawful (the ruling lists the floor), but it means the variant can be *added to the pool and paid for* (step A, ALONE, exclusion, pre-check, writes) and then fail the floor — spend without a pin. That's the same as any other moment, so not a defect; noting it because the ruling's "if it passes every gate" is where the 12 s floor bites, and the test at line 493-507 only asserts the *snap* behavior, not that the variant passes the floor. Not a bug.

**(b) Can the variant still contain the held word?**

`for_pool` (tail_variant.py:190): `ks = [k for k in range(k0, k1) if i is not None and src.sentences[k][1] < i]` — sentence k qualifies if its last token index is strictly less than the held word's index i. Since i is an index into `src.tokens` (absolute), and `src.sentences[k][1]` is the last token of sentence k, the variant ends at the last sentence *entirely before* the held word. If the held word is the first word of sentence k+1, then `sentences[k][1] < i` holds for k, so the variant ends at end of sentence k — held word excluded. Correct. If the held word is the *last* word of sentence k, then `sentences[k][1] == i`, so `<` fails for k, and the variant ends at k-1 — the held word (last word of sentence k) is excluded even though ending at k would have kept it. Slightly conservative, not a bug: the hold is about that word, so leaving it out is the point. Wait — is it? The ruling: "seal the tail-side variant ending '...I in the test at line 424: held word "401k." is the last word of sentence 3 ("I don't have a 401k."), and the variant ends at sentence 2. Consistent with the case. But consider: hold on the last word of sentence 1 (of 4). Then ks = [0] (sentences[0][1] < i holds since i = sentences[1][1] > sentences[0][1]... wait, i = sentences[1][1] (last token of sentence 1), sentences[0][1] < that, so k=0 qualifies, variant = sentences 0..0, one sentence. Then the variant is a one-sentence moment. Does `variant()` accept that? Yes: k0 <= k < k1 with k = k0 = 0. But then the variant has no earlier boundary — it's the whole first sentence. Is that lawful? Ruling 104: "ENDS at an earlier sentence boundary of the mined moment" — yes, ending at the end of its first sentence is an earlier boundary. But then the variant's `sentences` = [0,0]... and if that variant itself is later held, `for_pool` skips it (line 175: `k1 > k0` required). Fine.

Hmm, but there's a subtler issue: **`held_word` returns the FIRST difference outside ruling-84's class, at its tokens' FIRST occurrence** (tail_variant.py:154-163). If the held word's tokens occur earlier in the span than the actual held occurrence, the variant can end *before* the earlier occurrence, leaving the later (actual held) occurrence IN the variant. Concrete: parent text "…Bitcoin. … 401k. … 401k." — hold on the second "401k

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 88 s finish=stop usage in 16200 / out 450 usd~0.092 (upper-bound price)

<high> pipeline/tail_variant.py:218 (parents_first) + pipeline/spotlight.py:40 (finalist_order=TV.parents_first(sorted(..., rank_key))) + tests/package/test_ruling_104.py:490: parents_first only reorders spotlight finalists; medley path (package.build on the post-with_variants pool, using rank_key directly per facts) has no equivalent. Concrete sequence: Blockware parent (rank_score=1.0) + its variant (rank_score=9.0, derived_from ruling 104, sentences [0,2]) sorts as [variant, x, parent] by rank_key; medley selects variant as clip (passes step A/CUTTABLE/ALONE>=4/lock-precheck on its own span, no snap), seals pin before parent tried, violating "full clip first (14:12 order)" and ruling 104's "tried first, if lawful". (Uncertain if medley exactly calls rank_key; facts imply same pool+rules.)

<medium> pipeline/tail_variant.py:104 (M.record(..., {"scores": m["scores"]}, ..., M.judge(sp, ctx))): scores (incl. stands_alone/ALONE) copied from parent before clip scorer sees variant in pool. TestTheVariant:278 confirms eligibility fresh but not score recompute. If scorer does not override, variant can reach pin using parent's ALONE (ruling requires its own ALONE>=4); concrete sequence: Blockware variant drops sentences 3-4 (changes "stands_alone" semantics) but inherits parent's 5.0, passes spotlight without its own scorer verdict.

No other breaks of SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, L-b/L-c/L-j, ruling 104 triggers (held_word via class_84+canon_spans, CUT_HOLD, ceil_s), derived_from recording, or gate re-execution verifiable in diff+facts. holds()/for_pool cover the Blockware case exactly (test:420). L-d protected preview untouched.

SHIP: yes with conditions (add parents_first to medley selection order; confirm scorer recomputes ALONE on variants)

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 38 s finish=stop usage in 18116 / out 2261 usd~0.088 (upper-bound price)

I have carefully audited the diff against the Ruling 104 requirements, the governing laws, and the specific attack vectors provided.

### Findings

**<critical> None**
The core logic for creating tail variants (`pipeline/tail_variant.py`) correctly implements the "fail closed" and "sentence law" requirements.
1.  **Boundary Integrity:** `variant()` uses `E.Span(src, k0, k)`, ensuring the new clip ends exactly at a sentence boundary. It does not cut mid-sentence.
2.  **Gate Independence:** The variant is created via `M.record(...)`, which generates a new `moment_id` and re-judges eligibility. The `for_pool` function adds these to the main pool *before* the spotlight/medley stages run. Consequently, the variant faces all gates (Step A, ALONE, Lock Pre-check) as a distinct entity. It does not inherit the parent's cached verdicts.
3.  **Snap Protection:** `spotlight.snap` explicitly checks for `derived_from.ruling == 104` and returns `None` (blocking the snap) if the duration is below the target. This prevents the variant from being extended outward to include the "held" words that caused the parent to fail.
4.  **Ordering:** `finalist_order` ensures the parent is always tried before the variant. If the parent passes (e.g., via a successful re-listen), the variant is never reached. If the parent fails, the variant is tried. This matches the orchestrator's instruction: "FIRST the re-listen... if it holds, seal the tail-side variant".

**<high> None**
1.  **Held Word Placement:** `held_word` correctly identifies the word causing the hold by comparing the `as_spoken` text against the approved text using `attest.class_84`. It finds the *first* difference outside the allowed class. The variant ends at the last sentence boundary *before* this word index. This ensures the held word is excluded from the variant.
2.  **Duplicate Prevention:** `for_pool` checks if the variant's `moment_id` already exists in the pool (`have` set) and skips it if so. This prevents double-counting or conflicting entries.
3.  **Trigger Validity:** Variants are only generated if a specific trigger exists: a Lock Pre-check HOLD, a Ruling 73 cut failure, or a duration ceiling violation. No variant is created "for no reason."

**<medium> 1**
**File:** `pipeline/tail_variant.py`, lines 190-194
**Issue:** Potential off-by-one or boundary ambiguity in `for_pool` when calculating the variant end for a held word.
**Sequence:**
1.  `held_word` returns index `i` of the held word in `src.tokens`.
2.  `for_pool` calculates `ks = [k for k in range(k0, k1) if i is not None and src.sentences[k][1] < i]`.
3.  `src.sentences[k][1]` is the index of the *last* word of sentence `k`.
4.  The condition `src.sentences[k][1] < i` ensures the sentence ends *before* the held word starts.
5.  The variant is created with `k = ks[-1]`.
6.  **Risk:** If the held word `i` is the *first* word of a sentence, `src.sentences[k][1]` (last word of previous sentence) will be `< i`. This is correct. However, if the held word is *inside* a sentence, the variant ends at the *previous* sentence boundary. This is also correct per Ruling 104 ("ends at an earlier sentence boundary").
7.  **Subtle Risk:** The code assumes `src.sentences` is a list of `(start_idx, end_idx)` tuples. If `src.sentences[k][1]` is inclusive (which is standard for word indices in this codebase, as seen in `E.Span` usage), the logic holds. If `src.sentences` were exclusive, the variant might include the held word. Given `E.Span(src, k0, k)` uses `k` as the exclusive end of the sentence range (standard Python slicing), and `src.sentences[k][1]` is the last word index, the comparison `last_word_idx < held_word_idx` is the correct way to ensure the held word is *not* in the variant.
    *   *Verification:* `E.Span(src, k0, k)` creates a span from word `src.sentences[k0][0]` to `src.sentences[k-1][1]` (if `k` is the count of sentences) or similar. Wait, `E.Span(src, k0, k)` in `variant()` takes `k` as the *sentence index* to end at.
    *   In `for_pool`, `ks` contains sentence indices `k` such that the sentence ends before the held word.
    *   `variant(m, src, k, ...)` creates `E.Span(src, k0, k)`.
    *   If `E.Span` interprets the second argument as the *exclusive* sentence index (i.e., sentences `k0` to `k-1`), then ending at `k` means the last sentence included is `k-1`.
    *   The condition `src.sentences[k][1] < i` checks if sentence `k` ends before the held word.
    *   If we pick `k = ks[-1]`, and `variant` uses `E.Span(src, k0, k)`, we need to ensure `E.Span` includes sentence `k-1` but not `k`.
    *   Looking at `test_ruling_104.py` line 345: `v = TV.variant(m, src, 2, CTX, "a held word")`. `m` has sentences `[0, 4]`. `v` has sentences `[0, 2]`. The text is `SENTENCES[:3]` (indices 0, 1, 2).
    *   This implies `E.Span(src, 0, 2)` includes sentences 0 and 1? No, `SENTENCES[:3]` is 3 sentences.


## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 20261114_1441 (ruling 104, the tail-side twin), cycle 1: consensus

Reviewers:
- grok-4.20: yes with conditions. One <high> and one <medium>.
- qwen3.8-27b: SHIP yes. One <medium> (the boundary's index convention), answered by its own reading and the test.
- glm-5.3-flash: yes with conditions. Two conditions and notes.

## Taken: a rework of the trigger (the diff as it stands now)

- **grok <high>: "parents_first only orders the spotlight's finalists; the medley could take the variant before its
  parent".** glm's condition 1 adds that the reordering ran before the 3-finalist cut, so a variant could fall out of
  the finalists behind a low-ranked parent. Both come from one design gap: the parent and its variant COMPETED.
  - The rework:
    - holds() now reads the parent's hold under the CURRENT decoder and rules only, through lock_precheck.answer: the
      newest answer on the exact span, as a hook or a clip. Under ruling 103's rules that hold is FINAL, its targeted
      re-listen included ("the hold is final and the clip may only be saved by a variant that leaves the token out").
    - A parent with such a hold (or ruling 73's cut hold) is REPLACED by its variant in the pool
      (proof_ledger.with_variants, inputs["ruling_104"]["replaced"]), so the two never compete in the medley or the
      spotlight.
    - The full clip is honoured first because the variant exists only once the current pre-check, re-listen
      included, has held the full clip.
    - A parent over the ceiling stays BESIDE its variant: it can't be a spotlight (usable's 35 s), and the medley may
      still use it.
  - parents_first() and spotlight.finalist_order() are REMOVED, and spotlight's finalists are ordered as before.
  - Consequence: an older decoder's hold no longer proposes a variant. A build first re-asks the full clip under the
    current decoder; that is the 14:12 order ("FIRST the re-listen; if it holds, the variant").
  - Tests: an older decoder's or older rules' hold is not read; a newer pass clears the hold; a hold as a clip is seen;
    the newest of the two roles wins; the held parent is replaced and the ceiling parent kept.
  - Mutations: the 19 now killed include H1-H3 (the current answer), R1-R2 (replace or keep) and L1-L2 (the build).

## Refuted

- **grok <medium>: "the variant inherits the parent's stands_alone score and can pass ALONE on it".**
  - The ALONE gate reads the integrator's CLIP SCORER verdict for the moment's own id, and only when it was given on
    its current text (package.with_verdict: the verdict's text_sha256 must equal the text's; spotlight.alone_score).
  - The variant has its own id and text, so it gets only its own verdict, or waits for one.
  - The miner's scores feed rank_score (ranking) only. M.record builds a fresh record and copies no scorer_verdict.
- **glm (b): "a repeated held token: the variant ends before the FIRST occurrence and keeps the later, held one".**
  The variant is a PREFIX ending before the f

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261114_1441/C2_STEP.diff (481 lines)
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
  27 | index 0000000..018239f
  28 | --- /dev/null
  29 | +++ b/pipeline/tail_variant.py
  30 | @@ -0,0 +1,145 @@
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
 152 | +                else:
 153 | +                    notes[mid] = ("no variant: the held word cannot be placed" if i is None else
 154 | +                                  "no variant: the held word is in its first sentence")
 155 | +        if float(m.get("duration_s") or 0) > ceil_s:
 156 | +            t0 = float(m["start"])
 157 | +            ks = [k for k in range(k0, k1) if float(src.tokens[src.sentences[k][1]]["end"]) - t0 <= ceil_s]
 158 | +            if ks:
 159 | +                wanted.append((ks[-1], f"the seconds ceiling ({float(m['duration_s']):.2f} s > {ceil_s:g} s)"))
 160 | +            else:
 161 | +                notes[mid] = f"no variant: no earlier boundary within {ceil_s:g} s"
 162 | +        if not wanted:
 163 | +            continue
 164 | +        k = min(x[0] for x in wanted)
 165 | +        if e is not None:
 166 | +            replaced.add(mid)                            # ruling 103: its hold is final; only the variant may save it
 167 | +        v = variant(m, src, k, ctx, "; ".join(w for _, w in wanted))
 168 | +        if v["moment_id"] in have:
 169 | +            notes[mid] = f"its variant {v['moment_id']} is already in the pool"
 170 | +            continue
 171 | +        have.add(v["moment_id"])
 172 | +        out.append(v)
 173 | +        notes[mid] = (f"variant {v['moment_id']} ({v['duration_s']} s, ends {v['text'][-60:]!r})"
 174 | +                      + (", in its place" if mid in replaced else ", beside it"))
 175 | +    return out, notes, replaced
 176 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 177 | index d2b60dd..b646c26 100644
 178 | --- a/tests/package/proof_ledger.py
 179 | +++ b/tests/package/proof_ledger.py
 180 | @@ -70,6 +70,7 @@ import providers as P  # noqa: E402
 181 |  import speakers as SP  # noqa: E402
 182 |  import spotlight as SPOT  # noqa: E402
 183 |  import lock_precheck as LP  # noqa: E402
 184 | +import tail_variant as TV  # noqa: E402
 185 |  
 186 |  REGISTRY = os.path.join(HERE, "proof", "CANDIDATES.json")     # ruling 66: the candidates, kept
 187 |  SPOTLIGHTS = os.path.join(HERE, "proof", "SPOTLIGHTS.json")   # ruling 90: one spotlight per channel per ET day
 188 | @@ -131,6 +132,20 @@ def applied(router):
 189 |      return applies
 190 |  
 191 |  
 192 | +def with_variants(moments, sources, ctx, inputs, say, results_dir=None):
 193 | +    """RULING 104 (14:12 Nov 14): the build's pool with the tail-side variants (tail_variant.for_pool: a current lock
 194 | +    pre-check hold on the parent's span, a cut the render cannot make, the spotlight's seconds ceiling), so every gate
 195 | +    judges them from the start, the clip scorer included (its pool is made from these moments). A parent whose current
 196 | +    hold is final is replaced by its variant; a parent over the ceiling stays beside it. inputs["ruling_104"] records
 197 | +    them, the replaced parents, and why each parent has a variant or none. -> the new list of moments."""
 198 | +    variants, notes, replaced = TV.for_pool(moments, sources, ctx, results_dir or LP.RESULTS, SPOT.SPOT_S[1])
 199 | +    inputs["ruling_104"] = {"variants": [v["moment_id"] for v in variants], "replaced": sorted(replaced),
 200 | +                            "notes": notes}
 201 | +    say(f"  RULING 104 (the tail-side twin): {len(variants)} variant(s) in the pool, {len(replaced)} held parent(s) "
 202 | +        f"replaced by theirs (ruling 103: the hold is final)" + "".join(f"; {k}: {w}" for k, w in sorted(notes.items())))
 203 | +    return [m for m in moments if m["moment_id"] not in replaced] + variants
 204 | +
 205 | +
 206 |  def start_refused(spent0):
 207 |      """RULING 48, with the orchestrator's stop of 13:02 Nov 14 (the $16 stop passed with leave; at $19 stop and tell on
 208 |      STATE line 1 in capitals): no build starts at or over PL.LY_STOP_USD. -> the refusal line, or None."""
 209 | @@ -259,6 +274,7 @@ def main(argv=None):
 210 |      moments, sources, inputs = LB.build_inputs(rows, ctx, log=say, word_pass=wp,
 211 |                                                 ledger_store=os.path.join(LB.INGEST_ROOT, "data", "editorial"))
 212 |      inputs["word_pass"] = wp_rep
 213 | +    moments = with_variants(moments, sources, ctx, inputs, say)   # RULING 104: beside their parents, every gate again
 214 |      with open(os.path.join(out_dir, "inputs.json"), "w") as f:
 215 |          json.dump({"since": since.isoformat(), "publish_window_h": a.hours, "delivered_pins": pins,
 216 |                     "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments},
 217 | diff --git a/tests/package/test_ruling_104.py b/tests/package/test_ruling_104.py
 218 | new file mode 100644
 219 | index 0000000..c081738
 220 | --- /dev/null
 221 | +++ b/tests/package/test_ruling_104.py
 222 | @@ -0,0 +1,258 @@
 223 | +#!/usr/bin/env python3
 224 | +"""RULING 104 (orchestrator 14:12 ET Nov 14), THE TAIL-SIDE TWIN (pipeline/tail_variant.py and its use in the ledger
 225 | +build and the spotlight): a variant ENDING at an earlier sentence boundary of the mined moment, when that keeps it lawful
 226 | +(a held word after the boundary, a tail the cut cannot make, the seconds ceiling); a new span that faces every gate,
 227 | +recorded as derived from its parent row. The case: Blockware Solutions 06d34e15, held on "401k".
 228 | +Offline: word-timed test sources, a temporary results directory."""
 229 | +import copy
 230 | +import json
 231 | +import os
 232 | +import sys
 233 | +import tempfile
 234 | +import unittest
 235 | +import unittest.mock
 236 | +
 237 | +HERE = os.path.dirname(os.path.abspath(__file__))
 238 | +REPO = os.path.dirname(os.path.dirname(HERE))
 239 | +for _p in ("pipeline", "tests/package", "tests/eligibility"):
 240 | +    sys.path.insert(0, os.path.join(REPO, _p))
 241 | +import eligibility as E  # noqa: E402
 242 | +import lock_precheck as LP  # noqa: E402
 243 | +import moments as M  # noqa: E402
 244 | +import proof_ledger as PLG  # noqa: E402
 245 | +import spotlight as SPOT  # noqa: E402
 246 | +import tail_variant as TV  # noqa: E402
 247 | +import test_spotlight as TS  # noqa: E402
 248 | +from test_eligibility import NOW, REG, source  # noqa: E402
 249 | +
 250 | +SENTENCES = ["On my 20th birthday, I sold every stock in my Roth IRA and put it all into Bitcoin.",
 251 | +             "That ended up being one of the best financial decisions I've ever made, but not for the reason most "
 252 | +             "people think.",
 253 | +             "I'm 26 now, and I still don't use my Roth IRA.",
 254 | +             "I don't have a 401k.",
 255 | +             "I don't own a single share of any index fund, and I'm on pace to be financially independent by 45."]
 256 | +CTX = E.Context(NOW, REG)
 257 | +META = {"scores": {"contempt_outrage": 0, "hook_first_2s": 5, "quotable": 4, "stakes": 5, "stance": 4,     # the real
 258 | +                   "stands_alone": 5, "surprising_fact": 4},                                         # row's, build 11
 259 | +        "names_person": False, "risk": [], "topics": ["bitcoin"], "reason": "Strong personal narrative hook"}
 260 | +
 261 | +
 262 | +def parent(src, k0=0, k1=4, vid="7BqLu-wzbU0"):
 263 | +    sp = E.Span(src, k0, k1)
 264 | +    m = M.record(sp, META, CTX, M.judge(sp, CTX), {"ledger_moment_id": "06d34e155feae654ee56"})
 265 | +    m["rank_score"] = M.rank_score(m)
 266 | +    m["source_key"] = vid
 267 | +    return m
 268 | +
 269 | +
 270 | +def blockware():
 271 | +    src = source(SENTENCES, vid="7BqLu-wzbU0")
 272 | +    return src, parent(src)
 273 | +
 274 | +
 275 | +def hold(m, at="2026-11-14T19:51:07Z", spoken=None, reason="ruling 72/84: ... at [['401k', '401']]",
 276 | +         outcome="hold", role="hook", text=None, rules=None):
 277 | +    return {"rules": LP.RULES if rules is None else rules,
 278 | +            "request_id": "pp-selectid.ledger_x.1", "video_id": m["video_id"], "start": m["start"], "end": m["end"],
 279 | +            "window": [round(m["start"], 3), round(m["end"], 3)], "role": role,
 280 | +            "approved_text": m["text"] if text is None else text, "outcome": outcome, "reason": reason, "at": at,
 281 | +            "as_spoken": {"verdict": outcome, "text": m["text"].replace("401k.", "401 ,") if spoken is None
 282 | +                          else spoken}}
 283 | +
 284 | +
 285 | +def put(d, m, entries, decoder=LP.DECODER):
 286 | +    p = os.path.join(d, f"{m['video_id']}.{round(m['start'], 3):.3f}-{round(m['end'], 3):.3f}.{decoder}.json")
 287 | +    with open(p, "w") as f:
 288 | +        json.dump(entries, f)
 289 | +
 290 | +
 291 | +class TestTheVariant(unittest.TestCase):
 292 | +    def test_it_ends_at_the_boundary_is_a_new_span_and_names_its_parent(self):
 293 | +        src, m = blockware()
 294 | +        v = TV.variant(m, src, 2, CTX, "a held word")
 295 | +        self.assertEqual(v["text"], " ".join(SENTENCES[:3]))
 296 | +        self.assertEqual((v["sentences"], v["start"], v["end"]), ([0, 2], m["start"], src.tokens[src.sentences[2][1]]["end"]))
 297 | +        self.assertNotEqual(v["moment_id"], m["moment_id"])                            # its own id
 298 | +        self.assertEqual(v["moment_id"], M.record(E.Span(src, 0, 2), META, CTX, M.judge(E.Span(src, 0, 2), CTX),
 299 | +                                                  {})["moment_id"])                    # the span's own
 300 | +        d = v["derived_from"]
 301 | +        self.assertEqual((d["ruling"], d["from"], d["ledger_moment_id"], d["sentences"], d["was"]),
 302 | +                         (104, m["moment_id"], "06d34e155feae654ee56", [0, 2], [0, 4]))
 303 | +        self.assertEqual(d["left_out"], " ".join(SENTENCES[3:]))
 304 | +        self.assertEqual(v["mined"]["derived_from"], d)                                 # in its mined record too
 305 | +        self.assertEqual((v["source_key"], v["scores"], v["topics"]), (m["source_key"], m["scores"], m["topics"]))
 306 | +        self.assertEqual(set(v["eligibility"]), {"hook", "clip"})                       # judged afresh on its span
 307 | +        for k in (4, 5, -1, "2"):
 308 | +            with self.assertRaises(ValueError):
 309 | +                TV.variant(m, src, k, CTX, "x")
 310 | +
 311 | +
 312 | +class TestTheHeldWord(unittest.TestCase):
 313 | +    def test_the_401k_hold_is_placed_on_its_word_from_the_texts(self):
 314 | +        src, m = blockware()
 315 | +        i = TV.held_word(m, src, hold(m))
 316 | +        self.assertEqual(src.tokens[i]["word"], "401k.")
 317 | +        self.assertEqual(i, src.sentences[3][0] + 4)                                   # "I don't have a 401k."
 318 | +
 319 | +    def test_a_difference_inside_ruling_84_s_class_is_passed_over(self):
 320 | +        """A one-function-word substitution earlier in the span is in ruling 84's class: the held word is still 401k."""
 321 | +        src, m = blockware()
 322 | +        spoken = m["text"].replace("one of the best", "one of a best").replace("401k.", "401 ,")
 323 | +        self.assertEqual(src.tokens[TV.held_word(m, src, hold(m, spoken=spoken))]["word"], "401k.")
 324 | +
 325 | +    def test_an_insert_before_the_hold_cannot_be_placed_so_no_variant(self):
 326 | +        """The second reading inserts a number in the FIRST sentence and differs on 401k: no variant can leave the
 327 | +        insert out, so the word is not placed (no variant), never the later 401k."""
 328 | +        src, m = blockware()
 329 | +        spoken = m["text"].replace("into Bitcoin.", "into Bitcoin 21.").replace("401k.", "401 ,")
 330 | +        self.assertIsNone(TV.held_word(m, src, hold(m, spoken=spoken)))
 331 | +
 332 | +    def test_what_cannot_be_placed_gives_none(self):
 333 | +        src, m = blockware()
 334 | +        self.assertIsNone(TV.held_word(m, src, hold(m, spoken="")))                          # no second reading
 335 | +        self.assertIsNone(TV.held_word(m, src, dict(hold(m), as_spoken=None)))
 336 | +        self.assertIsNone(TV.held_word(m, src, hold(m, spoken=m["text"].replace("401k.", "401k, um,"))))  # a filler
 337 | +        self.assertIsNone(TV.held_word(m, src, hold(m, spoken=m["text"].replace("Bitcoin.", "Bitcoin 21."))))  # inserted
 338 | +
 339 | +
 340 | +class TestTheHolds(unittest.TestCase):
 341 | +    def setUp(self):
 342 | +        self.d = tempfile.TemporaryDirectory()
 343 | +        self.addCleanup(self.d.cleanup)
 344 | +
 345 | +    def test_the_newest_hold_on_the_exact_span_under_the_current_decoder_and_rules(self):
 346 | +        src, m = blockware()
 347 | +        self.assertIsNone(TV.holds(m, self.d.name))
 348 | +        put(self.d.name, m, [hold(m, at="2026-11-14T20:00:00Z", reason="an older decoder")], decoder="c705b20ed800")
 349 | +        self.assertIsNone(TV.holds(m, self.d.name))                                     # never read: not final now
 350 | +        put(self.d.name, m, [hold(m, at="2026-11-14T18:00:00Z", reason="old"),
 351 | +                             hold(m, at="2026-11-14T20:30:00Z", reason="older rules",
 352 | +                                  rules="ruling 17 + ruling 72 + ruling 73 + ruling 84"),   # never read
 353 | +                             hold(m, at="2026-11-14T18:51:07Z", reason="new"),
 354 | +                             hold(m, outcome="no_difference", at="2026-11-14T18:30:00Z"),       # an older pass
 355 | +                             hold(m, at="2026-11-14T19:30:00Z", text="another text"),           # another span's text
 356 | +                             dict(hold(m, at="2026-11-14T19:31:00Z"), window=[0.0, 9.0])])      # another window
 357 | +        self.assertEqual(TV.holds(m, self.d.name)["reason"], "new")
 358 | +        passed = tempfile.TemporaryDirectory()                                           # a NEWER pass: not held now
 359 | +        self.addCleanup(passed.cleanup)
 360 | +        put(passed.name, m, [hold(m, at="2026-11-14T18:51:07Z"), hold(m, outcome="no_difference",
 361 | +                                                                   at="2026-11-14T19:00:00Z")])
 362 | +        self.assertIsNone(TV.holds(m, passed.name))
 363 | +        clip = tempfile.TemporaryDirectory()                                            # held as a medley clip
 364 | +        self.addCleanup(clip.cleanup)
 365 | +        put(clip.name, m, [hold(m, role="clip", reason="as a clip")])
 366 | +        self.assertEqual(TV.holds(m, clip.name)["reason"], "as a clip")
 367 | +        put(clip.name, m, [hold(m, role="clip", reason="as a clip", at="2026-11-14T19:00:00Z"),
 368 | +                           hold(m, role="hook", reason="as a hook, newer", at="2026-11-14T19:10:00Z")])
 369 | +        self.assertEqual(TV.holds(m, clip.name)["reason"], "as a hook, newer")      # the newest of the two roles
 370 | +        with open(os.path.join(self.d.name, f"{m['video_id']}.0.000-1.000.c705b20ed800.json"), "w") as f:
 371 | +            f.write("{ broken")                                                                  # never read: another span
 372 | +        self.assertEqual(TV.holds(m, self.d.name)["reason"], "new")
 373 | +
 374 | +
 375 | +class TestThePool(unittest.TestCase):
 376 | +    def setUp(self):
 377 | +        self.d = tempfile.TemporaryDirectory()
 378 | +        self.addCleanup(self.d.cleanup)
 379 | +
 380 | +    def pool(self, ms, sources, ceil_s=35.0):
 381 | +        vs, notes, replaced = TV.for_pool(ms, sources, CTX, self.d.name, ceil_s)
 382 | +        self.replaced = replaced
 383 | +        return vs, notes
 384 | +
 385 | +    def test_blockware_held_on_401k_gives_the_variant_ending_before_it(self):
 386 | +        src, m = blockware()
 387 | +        put(self.d.name, m, [hold(m)])
 388 | +        vs, notes = self.pool([m], {"7BqLu-wzbU0": src})
 389 | +        self.assertEqual([v["text"] for v in vs], [" ".join(SENTENCES[:3])])     # "...I still don't use my Roth IRA."
 390 | +        self.assertIn("a held word after the boundary: '401k.'", vs[0]["derived_from"]["why"])
 391 | +        self.assertIn(vs[0]["moment_id"], notes[m["moment_id"]])
 392 | +        self.assertEqual(self.replaced, {m["moment_id"]})                              # its hold is final
 393 | +
 394 | +    def test_a_cut_the_render_cannot_make_drops_the_last_sentence(self):
 395 | +        src, m = blockware()
 396 | +        put(self.d.name, m, [hold(m, reason="ruling 73: the render cannot cut this span: the OUT edge")])
 397 | +        vs, _ = self.pool([m], {"7BqLu-wzbU0": src})
 398 | +        self.assertEqual(vs[0]["sentences"], [0, 3])
 399 | +
 400 | +    def test_the_seconds_ceiling_gives_the_longest_variant_within_it(self):
 401 | +        src, m = blockware()
 402 | +        limit = src.tokens[src.sentences[2][1]]["end"] - m["start"] + 0.01           # sentences 0-2 fit, 0-3 do not
 403 | +        vs, _ = self.pool([m], {"7BqLu-wzbU0": src}, ceil_s=limit)
 404 | +        self.assertEqual(vs[0]["sentences"], [0, 2])
 405 | +        self.assertIn("the seconds ceiling", vs[0]["derived_from"]["why"])
 406 | +        self.assertEqual(self.replaced, set())                                          # the parent stays beside it
 407 | +        put(self.d.name, m, [hold(m, reason="ruling 73: the render cannot cut this span")])   # both: the shorter
 408 | +        vs, _ = self.pool([m], {"7BqLu-wzbU0": src}, ceil_s=limit)
 409 | +        self.assertEqual(vs[0]["sentences"], [0, 2])
 410 | +        self.assertIn("a tail the cut cannot make", vs[0]["derived_from"]["why"])
 411 | +
 412 | +    def test_no_variant_where_none_keeps_it_lawful(self):
 413 | +        src, m = blockware()
 414 | +        put(self.d.name, m, [hold(m, spoken=m["text"].replace("20th", "21st"))])       # held in its FIRST sentence
 415 | +        vs, notes = self.pool([m], {"7BqLu-wzbU0": src})
 416 | +        self.assertEqual((vs, notes[m["moment_id"]]), ([], "no variant: the held word is in its first sentence"))
 417 | +        one = parent(src, 2, 2)                                                           # one sentence: no boundary
 418 | +        put(self.d.name, one, [hold(one)])
 419 | +        self.assertEqual(self.pool([one], {"7BqLu-wzbU0": src}), ([], {}))
 420 | +        self.assertEqual(self.pool([m], {}), ([], {m["moment_id"]: "no variant: its word record is not in this build"}))
 421 | +        clean = blockware()[1]                                                            # no hold, under the ceiling
 422 | +        clean["start"] += 0.0005                                                          # (another span on file)
 423 | +        self.assertEqual(self.pool([clean], {"7BqLu-wzbU0": src}), ([], {}))
 424 | +
 425 | +    def test_a_variant_already_in_the_pool_is_not_added_twice(self):
 426 | +        src, m = blockware()
 427 | +        put(self.d.name, m, [hold(m)])
 428 | +        v = TV.variant(m, src, 2, CTX, "x")
 429 | +        vs, notes = self.pool([m, v], {"7BqLu-wzbU0": src})
 430 | +        self.assertEqual(vs, [])
 431 | +        self.assertIn("already in the pool", notes[m["moment_id"]])
 432 | +
 433 | +    def test_the_ledger_build_replaces_a_held_parent_and_keeps_one_over_the_ceiling(self):
 434 | +        src, m = blockware()
 435 | +        other = parent(src, 3, 4)                                                         # another moment, no trigger
 436 | +        put(self.d.name, m, [hold(m)])
 437 | +        inputs, said = {}, []
 438 | +        out = PLG.with_variants([m, other], {"7BqLu-wzbU0": src}, CTX, inputs, said.append, results_dir=self.d.name)
 439 | +        self.assertEqual([x["moment_id"] for x in out], [other["moment_id"], inputs["ruling_104"]["variants"][0]])
 440 | +        self.assertEqual(out[1]["text"], " ".join(SENTENCES[:3]))
 441 | +        self.assertEqual(inputs["ruling_104"]["replaced"], [m["moment_id"]])
 442 | +        self.assertIn("1 variant(s) in the pool, 1 held parent(s) replaced", said[0])
 443 | +        limit = src.tokens[src.sentences[2][1]]["end"] - m["start"] + 0.01
 444 | +        clean = tempfile.TemporaryDirectory()
 445 | +        self.addCleanup(clean.cleanup)
 446 | +        with unittest.mock.patch.object(SPOT, "SPOT_S", (12.0, limit)):                # over the ceiling: beside it
 447 | +            out = PLG.with_variants([m], {"7BqLu-wzbU0": src}, CTX, {}, said.append, results_dir=clean.name)
 448 | +        self.assertEqual([x["sentences"] for x in out], [[0, 4], [0, 2]])
 449 | +
 450 | +
 451 | +class TestTheSpotlight(unittest.TestCase):
 452 | +    def test_a_variant_is_never_snapped_outward(self):
 453 | +        src, m = blockware()
 454 | +        short = TV.variant(m, src, 1, CTX, "x")                                          # two sentences, under 13.7 s
 455 | +        self.assertLess(short["duration_s"], SPOT.SNAP_TO_S)
 456 | +        caps = lambda vid: ([], None)
 457 | +        v, why = SPOT.snap(short, {"7BqLu-wzbU0": src}, CTX, captions_for=caps)
 458 | +        self.assertIsNone(v)
 459 | +        self.assertIn("never snapped outward", why)
 460 | +        plain = dict(short)
 461 | +        plain.pop("derived_from")
 462 | +        v, _ = SPOT.snap(plain, {"7BqLu-wzbU0": src}, CTX, captions_for=caps)         # any other moment: snapped
 463 | +        self.assertIsNotNone(v)
 464 | +        long_ = TV.variant(m, src, 2, CTX, "x")
 465 | +        self.assertGreaterEqual(long_["duration_s"], SPOT.SNAP_TO_S)
 466 | +        self.assertIs(SPOT.snap(long_, {"7BqLu-wzbU0": src}, CTX, captions_for=caps)[0], long_)
 467 | +
 468 | +    def test_the_spotlight_pin_records_where_the_variant_came_from(self):
 469 | +        m = TS.moment()
 470 | +        pk, why, *_ = TS.package(m=m)
 471 | +        self.assertIsNone(why)
 472 | +        self.assertNotIn("derived_from", pk["spotlight"])                               # every other pin as before
 473 | +        d = {"ruling": 104, "from": "06d34e155feae654ee56", "sentences": [0, 2], "was": [0, 4], "why": "x"}
 474 | +        pk, why, *_ = TS.package(m=dict(copy.deepcopy(m), derived_from=d))
 475 | +        self.assertIsNone(why)
 476 | +        self.assertEqual(pk["spotlight"]["derived_from"], d)
 477 | +
 478 | +
 479 | +if __name__ == "__main__":
 480 | +    unittest.main()
 481 | 
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
