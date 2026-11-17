# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261117_0843
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 304 s finish=stop usage in 18342 / out 6323 usd_reported=0.001353 usd~0.150 (upper-bound price)

The code implements **RULING 131** (two-of-three adjudication) for the lock pre-check phase. It ensures that text adoptions are re-derived from raw readings rather than trusted from the record, enforces a 3-token edge buffer, blocks critical word changes, and handles currency formatting and repetitions.

### Audit Findings

**1. Adjudication Logic (Two-of-Three)**
The implementation in `attest.class_131` correctly follows the priority:
- **Currency Formatting:** `currency_pair` identifies "dollars" tokens following numbers. Since `all([])` is `True`, it correctly handles `delete` (run has "dollars", approved doesn't) and `insert` (approved has "dollars", run doesn't) cases.
- **Criticals:** `critical(t, texts)` (the render's `_lv2_critical`) is applied to all tokens in the pair, correctly blocking numbers, names, and negations.
- **Voting:** It uses `reads()` to check if the second recogniser agrees with the approved text first, then the run's text (provided the `edge_distance` $\ge 3$).
- **Fail-Closed:** Any pair that doesn't fit these categories results in `class: None`, which `lock_precheck.decide` treats as a `hold`.

**2. Edge Distance and Sliding**
The `edge_distance` function correctly implements the "slide" for repetitions. By calculating the equal runs before and after a `delete` or `insert` and iterating through possible shifts, it finds the placement that maximizes the distance from the nearest edge. The use of `max(min(a + n, len(r) - (b + n)))` is mathematically sound for this purpose.

**3. Final Spoken Text Validation**
The logic in `class_131` (lines 124–133) ensures that the final `spoken` text is not just a result of the merged adjudication, but that any additional adoptions (via Ruling 72/84) are also supported by the second recogniser's reading. This prevents the "adopt_spoken" layer from introducing hallucinated or unsupported words.

**4. Integration and Regression**
- `lock_precheck.decide` correctly isolates Ruling 131 records using `.startswith(AT.RULE_131)`, ensuring that existing Ruling 84/105 paths remain unchanged.
- `lock_precheck.attested` updates the sealing metadata to include the specific "two of three readings" language required for the release caption.
- The `RULES` string update and `DECODER` constant update align with the integrator's requirements.

**5. Test Coverage**
The `TestRuling131` suite is comprehensive:
- It verifies the "happy path" with real readings.
- It tests "lies" in the record (wrong `took` value, missing pairs, incorrect distances).
- It validates that criticals and edge-buffer violations trigger a `hold`.
- It confirms the sliding logic for repetitions and the currency formatting exception.
- It ensures that non-Ruling 131 records are not processed by the new logic.

### Conclusion
The implementation is robust, strictly adheres to the governing laws, and includes a high-coverage test suite that kills all identified mutations.

P1_OR_WORSE: 0

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 450 s finish=stop usage in 17514 / out 23745 usd_reported=0.017745 usd~0.409 (upper-bound price)



# Code Audit: RULING 131 (pp-selectid-20261117_0843)

## Scope Reviewed

`pipeline/attest.py` (new: `RULE_131`, `EDGE_131`, `currency_pair`, `edge_distance`, `class_131`), `pipeline/lock_precheck.py` (modified: `RULES`, `decide`, `attested`), `tests/package/test_lock_precheck.py` (new: `TestRuling131`, 7 tests), `tests/package/test_ruling_105.py` (1 assertion fix).

---

## Findings

### [P2] `edge_distance` recomputes `SequenceMatcher` per-op; `class_131` calls it a third time for `merged`

`class_131` calls `diff(run_t, pin_t)` (1st SM), then `edge_distance` per non-equal op (each does a 2nd SM on the same `r, p`), then a 3rd SM for the `merged` loop. For a segment with *N* differing pairs this is *O(N)* full `SequenceMatcher` passes over the same two token lists. At clip scale (≤ ~200 tokens, ≤ ~10 pairs) this is negligible, but the `full` opcode list is identical every time and could be computed once and threaded through. Not a correctness issue; a maintainability / future-performance note.

### [P2] `currency_pair` docstring slightly overstates the invariant

The docstring says *"every token on both sides of the pair is a 'dollars' right after a number."* For a delete/insert op one side is empty and `all()` over an empty range is vacuously `True`. The code is correct, but a reader skimming the docstring might think both sides must be non-empty. Suggest: *"every token on the non-empty side is a 'dollars' immediately following a numeric token; the empty side is vacuously satisfied."*

### [P3] `attested()` – the `carried` string for ruling 131 is 4 lines longer than the ruling 84 one

Not a defect, but the sealed record's `carried` field is human-readable release text. The ruling 131 version is dense and could be trimmed to match the existing style (the release caption already prints the short form *"word check settled by two of three readings"*). Purely cosmetic.

### [P3] `test_a_repetition_near_the_start_slides_right` – inline comment "1 without the slide"

The comment `# 1 without the slide` is correct (base distance = `min(1, 14) = 1`), but it sits on the same line as the assertion that checks the *slid* distance (3). A reader might momentarily think the assertion expects 1. Suggest moving the comment to its own line or rewording: `# base distance is 1; sliding right through the equal run yields 3`.

---

## Verification of the Seven Requested Checks

| # | Requirement | Verdict |
|---|---|---|
| 1 | Nothing the ruling forbids can be sealed (number, name, negation, 3-way disagreement, run reading < 3 tokens from edge) | **PASS.** `critical()` (unchanged `_lv2_critical`) gates every non-currency pair before the `reads` check. All-three-differ falls to the `else` → `class: None` → caller holds. `edge_distance < EDGE_131` → `class: None` → hold. Tests `test_what_still_holds` covers all five. |
| 2 | A record that disagrees with this side's derivation always holds | **PASS.** `theirs != mine` → `held(...)`. The record's `pairs` are compared field-by-field (run words, approved words, took, edge_distance) against this side's re-derivation. `test_this_side_rederives_every_pair_and_never_trusts_the_record` exercises 9 lie variants. |
| 3 | Currency test cannot hide a real difference | **PASS.** `currency_pair` requires *every* token in the range to satisfy `canon.dollars_after_number` (token == "dollars", predecessor matches `\d+(\.\d+)?`). "euros" ≠ "dollars" → rejected. "dollars" after a non-numeric token → rejected. Double "dollars" → rejected. Tests cover all four negative cases. |
| 4 | Slide cannot carry a non-repetition or go beyond equal context | **PASS.** Sliding is gated on `tag in ("delete","insert")` (replace never slides). The `left`/`right` bounds are the lengths of the *adjacent equal* opcodes in the full SM list. The per-step condition `seq[x±n] == seq[y±n]` ensures the text is invariant under the shift (true repetition). `test_a_repetition_slides_to_its_furthest_placement` and `test_a_repetition_near_the_start_slides_right` verify both directions. |
| 5 | Ruling 72 layer cannot reintroduce or revert a decided word | **PASS.** Two independent checks: (a) `class_84(spoken, merged)` – every difference must be in ruling 84's class (filler, one function word, carry-over); a content word → `class: None` → hold. (b) `reads(sp, s, a, b)` – every non-equal token in spoken must be the second recogniser's own reading at that position; a word the second recogniser never heard → hold. `test_this_side_rederives_every_pair_and_never_trusts_the_record` case 6 (`"the climbing"` not in second recogniser) and case 7 (second recogniser alone can't adopt a content word) verify this. |
| 6 | Ruling 84 path unchanged for other `adopt_spoken` | **PASS.** The new branch is gated on `str(adj.get("rule") or "").startswith(AT.RULE_131)`. Any other rule string falls through to the existi

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus (pp-selectid_audit_20261117_0843)

SEATS ANSWERED: 2 of 3 (qwen3.8-27b, gemma-4-31b-it; mimo-v2.6-flash-rl spent its 32,000 tokens and returned no
answer). P0/P1: none from either seat. Both traced the seven checks against the code and passed each.

## Findings and what was done
- qwen [P2] currency_pair's docstring overstates the invariant (an empty side is vacuously satisfied): ACCEPTED,
  reworded.
- qwen [P3] the right-slide test's inline comment sits on the assertion of the slid distance: ACCEPTED, moved to its
  own line and reworded.
- qwen [P2] edge_distance re-runs SequenceMatcher per pair: DECLINED. It mirrors the render's own function exactly
  (the integrator's pinned.adjudicate_lock), on clip-scale texts; a different structure here would be a second place
  to keep in step for no measured gain.
- qwen [P3] the ruling 131 "carried" text is longer than ruling 84's: DECLINED. It is the sealed human record of
  exactly what carried over; the release caption's short form is the integrator's, from attested.rule.

## Changed since cycle 1's diff (the integrator's answer of 08:5x Nov 17, its as_spoken edges)
Cycle 1 reviewed a ruling-72 layer test that asked, at each difference between the spoken text and the merged
reading, whether the UNTRIMMED second recogniser read the spoken tokens there (attest.reads). The integrator's
pre-check builds its as_spoken text from the second recogniser's tokens with the neighbours' spill trimmed
(lock_precheck.reading + _spill: every token before the lock's first aligned token goes, unless it repeats the tokens
right after it, the speaker's own 'When, when'; the end alike). So:
- NEW attest.spill_trimmed(lock_tokens, s): that trim, as the integrator gave it.
- The ruling 72 layer is now EXACT: the spoken text's canon tokens must equal the merged reading, or the trimmed
  second reading of the span; and every difference from the merged reading must be in ruling 84's class (class_84,
  unchanged). The position-wise reads test is gone (the exact equality is stricter, and against the untrimmed reading
  it would hold a padding word at the span's edge that the render never adopts).
- NEW test test_ruling_72_on_top_is_the_second_recognisers_reading_with_its_spill_trimmed: padding at the start and the
  end is trimmed and never adopted; the speaker's own edge repeat at the start and at the end is kept and adopts.
- Mutations after a control run: 23 of 23 killed (M5 is now the exact equality; M20-M23 the trim's four branches).
  Suites: 40 files by exit code, 871 tests.

PLEASE CHECK in cycle 2: the trim (start and end, the repeat it keeps), that the exact equality cannot let a spoken
text through that is neither the merged reading nor the second recogniser's trimmed reading, and the earlier seven
checks on the changed code.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261117_0843/C2_STEP.diff (457 lines)
```
   1 | diff --git a/pipeline/attest.py b/pipeline/attest.py
   2 | index f45e4d5..ba38c08 100644
   3 | --- a/pipeline/attest.py
   4 | +++ b/pipeline/attest.py
   5 | @@ -13,7 +13,13 @@ critical() is the render's _lv2_critical with its lists. CPU only, no model call
   6 |  (package_pin, which the integrator's check imports, must never pull it in).
   7 |  
   8 |  RULING 84 (orchestrator 20:41 Nov 13) has its own class, class_84, for the render's lock pre-check only (the
   9 | -second recogniser against the lock): fillers, and ONE function word. carry_class (ruling 67's re-seal) is unchanged."""
  10 | +second recogniser against the lock): fillers, and ONE function word. carry_class (ruling 67's re-seal) is unchanged.
  11 | +
  12 | +RULING 131 (orchestrator 08:25 ET Nov 17) has its own re-check, class_131: (A) per differing pair of the render's lock,
  13 | +two of the three readings (the approved text, the run's decode, the second recogniser) decide it and the sealed text
  14 | +takes that reading, at least 3 tokens from both cut edges; never a number, a name or a negation; all three different
  15 | +holds. (B) a currency symbol is formatting (canon.dollars_after_number, G18's one tolerance). It re-runs the render's own
  16 | +steps on the three readings the lock records and never trusts the record's own classes."""
  17 |  import re
  18 |  from difflib import SequenceMatcher
  19 |  
  20 | @@ -118,6 +124,135 @@ def class_84(spoken, approved):
  21 |      return out
  22 |  
  23 |  
  24 | +# RULING 131 (orchestrator 08:25 ET Nov 17): the render's lock records a two-of-three adjudication under this rule (the
  25 | +# integrator's message of 08:2x Nov 17: lock["adjudication"]["rule"] "ruling 131 (A) (orchestrator 2026-11-17
  26 | +# '08:25')"); a pair takes the run's reading only at EDGE_131 tokens or more from both edges of the run's decode
  27 | +RULE_131 = "ruling 131 (A)"
  28 | +EDGE_131 = 3                                    # pinned.MAJORITY_EDGE
  29 | +
  30 | +
  31 | +def currency_pair(r, p, op):
  32 | +    """RULING 131 (B), the render's own test (pinned.adjudicate_lock): every token on the pair's non-empty side(s) is a
  33 | +    'dollars' right after a number token (canon.dollars_after_number: '$2 billion' is a spoken '2 billion'); an empty
  34 | +    side is vacuously so (audit 20261117_0843 C1, qwen P2)."""
  35 | +    _tag, a, b, c, d = op
  36 | +    return all(canon.dollars_after_number(r, i) for i in range(a, b)) and \
  37 | +        all(canon.dollars_after_number(p, j) for j in range(c, d))
  38 | +
  39 | +
  40 | +def edge_distance(r, p, op):
  41 | +    """RULING 131 (A), as the render's lock measures it (the integrator's message of 08:4x Nov 17): min(a, len(r) - b)
  42 | +    in the run decode's canon tokens r. A pair with an empty side ("delete" or "insert") inside a repetition may slide,
  43 | +    since both texts stay the same ("that's why that's why": difflib may put the extra copy on either): shift -n while
  44 | +    n <= the equal run before it and seq[x - n] == seq[y - n], +n while n <= the equal run after it and
  45 | +    seq[x + n - 1] == seq[y + n - 1] (seq, x, y = r, a, b for a delete; p, c, d for an insert); its distance is the
  46 | +    largest over the shifts (0 included). A replace never slides."""
  47 | +    tag, a, b, c, d = op
  48 | +    shifts = [0]
  49 | +    full = SequenceMatcher(None, r, p, autojunk=False).get_opcodes()
  50 | +    if tag in ("delete", "insert") and tuple(op) in full:
  51 | +        k = full.index(tuple(op))
  52 | +        seq, x, y = (r, a, b) if tag == "delete" else (p, c, d)
  53 | +        left = full[k - 1][2] - full[k - 1][1] if k > 0 and full[k - 1][0] == "equal" else 0
  54 | +        right = full[k + 1][2] - full[k + 1][1] if k + 1 < len(full) and full[k + 1][0] == "equal" else 0
  55 | +        n = 1
  56 | +        while n <= left and seq[x - n] == seq[y - n]:
  57 | +            shifts.append(-n)
  58 | +            n += 1
  59 | +        n = 1
  60 | +        while n <= right and seq[x + n - 1] == seq[y + n - 1]:
  61 | +            shifts.append(n)
  62 | +            n += 1
  63 | +    return max(min(a + n, len(r) - (b + n)) for n in shifts)
  64 | +
  65 | +
  66 | +def spill_trimmed(lock_tokens, s):
  67 | +    """RULING 72's reading of a span, as the integrator's pre-check takes it (its lock_precheck.reading + _spill, the
  68 | +    integrator's message of 08:5x Nov 17): the second recogniser's canon tokens s (its words whose midpoint lies in the
  69 | +    lock's window +- 0.3 s) with the neighbours' spill trimmed: every token before the lock's first aligned token goes
  70 | +    (fillers included), unless those tokens repeat the ones right after them (the speaker's own edge repeat, 'When,
  71 | +    when', is kept); the end alike. -> the trimmed tokens."""
  72 | +    ops = SequenceMatcher(None, lock_tokens, s, autojunk=False).get_opcodes()
  73 | +    lo, hi = 0, len(s)
  74 | +    if ops and ops[0][0] == "insert" and ops[0][1] == 0:
  75 | +        d = ops[0][4]
  76 | +        lo = next((d - n for n in range(d, 0, -1) if s[d - n:d] == s[d:d + n]), d)
  77 | +    if ops and ops[-1][0] == "insert" and ops[-1][1] == len(lock_tokens):
  78 | +        c = ops[-1][3]
  79 | +        hi = next((c + n for n in range(len(s) - c, 0, -1) if s[c:c + n] == s[c - n:c]), c)
  80 | +    return s[lo:max(lo, hi)]
  81 | +
  82 | +
  83 | +def class_131(spoken, approved, adj):
  84 | +    """RULING 131 (A) and (B) (orchestrator 08:25 ET Nov 17): this side's own re-check of an adoption, from the render's
  85 | +    lock record (the pre-check entry's "adjudication": the FIRST lock's "run_decode", "approved", "second_recogniser",
  86 | +    "pairs"), never from the record's own classes. spoken: the entry's spoken text; approved: the segment's approved
  87 | +    text. Each step is the render's own (pinned.adjudicate_lock), re-run on the recorded readings:
  88 | +    1. The ruling-17 diff (diff: canon tokens of the run's decode against the approved text). (B) first: a currency
  89 | +       pair (currency_pair) is no difference and keeps the approved words.
  90 | +    2. A number, a name or a negation in any other pair holds (law L-v 2: the render holds before any vote).
  91 | +    3. Per pair (reads: the render's test of the second recogniser's reading there): it reads the approved words ->
  92 | +       the approved; else it reads the run's AND edge_distance >= EDGE_131 tokens -> the run's; else (all three
  93 | +       differ, or the run's too near an edge) the pair holds.
  94 | +    4. The record's pairs must be exactly these (currency pairs aside), in order: the same words (canon tokens), the
  95 | +       same reading taken, the same edge distance.
  96 | +    5. The spoken text's canon tokens are the merged reading (the approved tokens, each run-taken pair as the run's)
  97 | +       or, with ruling 72's adoptions on top, exactly the second recogniser's own reading of the span (spill_trimmed:
  98 | +       the pre-check's as_spoken text); every difference from the merged reading must be in ruling 84's class
  99 | +       (class_84, as today's adopt_spoken), or it holds.
 100 | +    -> [{"spoken", "approved", "class", "took", "edge_distance"} (+ "why" when it holds)], one per pair in the diff's
 101 | +    order, then ruling 72's differences on the merged text (took "ruling 72"), then one per failed whole-record test;
 102 | +    a class None holds."""
 103 | +    def held(why, **kw):
 104 | +        return dict({"spoken": "", "approved": "", "took": None, "edge_distance": None}, **kw, **{"class": None},
 105 | +                    why=why)
 106 | +    adj = adj if isinstance(adj, dict) else {}
 107 | +    run_t, pin_t, sec_t = adj.get("run_decode"), adj.get("approved"), adj.get("second_recogniser")
 108 | +    if not all(isinstance(t, str) for t in (run_t, pin_t, sec_t, spoken, approved)) or \
 109 | +            canon.canon_tokens(pin_t) != canon.canon_tokens(approved):
 110 | +        return [held("the lock record does not hold the three readings of this segment's approved text")]
 111 | +    texts = (run_t, pin_t)
 112 | +    r, p, ops = diff(run_t, pin_t)
 113 | +    s = canon.canon_tokens(sec_t)
 114 | +    out, took_run = [], set()
 115 | +    for op in ops:
 116 | +        _tag, a, b, c, d = op
 117 | +        row = {"spoken": " ".join(r[a:b]), "approved": " ".join(p[c:d])}
 118 | +        if currency_pair(r, p, op):
 119 | +            out.append(dict(row, took="currency", edge_distance=None, **{"class": "currency format (ruling 131 (B))"}))
 120 | +            continue
 121 | +        row["edge_distance"] = edge_distance(r, p, op)
 122 | +        if any(critical(t, texts) for t in r[a:b] + p[c:d]):
 123 | +            out.append(dict(row, took=None, **{"class": None}, why="a number, a name or a negation (law L-v 2)"))
 124 | +        elif reads(p, s, c, d):
 125 | +            out.append(dict(row, took="approved", **{"class": "two of three readings: the approved words"}))
 126 | +        elif reads(r, s, a, b) and row["edge_distance"] >= EDGE_131:
 127 | +            out.append(dict(row, took="run", **{"class": "two of three readings: as spoken"}))
 128 | +            took_run.add((a, c))
 129 | +        else:
 130 | +            out.append(dict(row, took=None, **{"class": None}, why=(
 131 | +                f"the run's reading within {EDGE_131} tokens of a cut edge" if reads(r, s, a, b) else
 132 | +                "all three readings differ")))
 133 | +    merged = []
 134 | +    for tag, a, b, c, d in SequenceMatcher(None, r, p, autojunk=False).get_opcodes():
 135 | +        merged += r[a:b] if (tag != "equal" and (a, c) in took_run) else p[c:d]
 136 | +    rec = adj.get("pairs")
 137 | +    theirs = [(x.get("run"), x.get("approved"), x.get("took"), x.get("edge_distance")) for x in rec] \
 138 | +        if isinstance(rec, list) and all(isinstance(x, dict) for x in rec) else None
 139 | +    mine = [(x["spoken"], x["approved"], x["took"], x["edge_distance"]) for x in out if x["took"] != "currency"]
 140 | +    if theirs != mine:
 141 | +        out.append(held(f"the lock record's pairs are not this side's: {theirs} against {mine}"[:400]))
 142 | +    sp = canon.canon_tokens(spoken)
 143 | +    if sp != merged and sp != spill_trimmed(merged, s):  # ruling 72 adopts only the second recogniser's own reading
 144 | +        out.append(held("the spoken text is neither the merged reading nor the second recogniser's own reading of the "
 145 | +                        "span (ruling 72 adopts only its reading)"))
 146 | +    for x in class_84(spoken, " ".join(merged)):        # ruling 72 on top of the merged reading, as today
 147 | +        out.append(dict(x, took="ruling 72", edge_distance=None, **(
 148 | +            {"why": "the spoken text differs from the merged reading outside ruling 84's class"} if x["class"] is None
 149 | +            else {})))
 150 | +    return out
 151 | +
 152 | +
 153 |  def reads(x, s, lo, hi):
 154 |      """The second recogniser's tokens s read x's tokens lo..hi-1 AT this position (pinned.adjudicate_lock's reads):
 155 |      they and one neighbour on each side are aligned and consecutive in s; at x's start / end nothing may precede /
 156 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
 157 | index 8eea07a..81dc1a4 100644
 158 | --- a/pipeline/lock_precheck.py
 159 | +++ b/pipeline/lock_precheck.py
 160 | @@ -26,6 +26,12 @@ Outcomes:
 161 |    carry-over class for an insert or a drop; never a number, a name or a negation). Otherwise it is a hold (fail
 162 |    closed). Under ruling 84 (b) the spoken text holds the second recogniser's reading of the one function word; the
 163 |    render's lock keeps its decode's word and records the other reading (the entry's "alternatives").
 164 | +  RULING 131 (A) (orchestrator 08:25 ET Nov 17): when the entry's lock record ("adjudication") is under ruling 131
 165 | +  (A), two of the three readings decided each pair and the spoken text is the lock's merged text. It is adopted only
 166 | +  when this side's own re-check (attest.class_131, from the record's three readings) finds every pair decided the same
 167 | +  way, every run-taken pair at least 3 tokens from both cut edges, no number, name or negation, and the spoken text
 168 | +  the merged reading; anything else is a hold (fail closed). (B): currency format ('$2 billion' for a spoken
 169 | +  '2 billion') is no difference.
 170 |  - hold: the clip may not be used with that text. The reason says why.
 171 |  - error, an outcome this module does not know, or no answer in time: no verdict. Never a pass (law L-m). A request
 172 |    is sent again rather than reusing an error.
 173 | @@ -41,7 +47,9 @@ from datetime import datetime, timezone
 174 |  import attest as AT
 175 |  import canon as C
 176 |  
 177 | -RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105"   # RULING 105 (orchestrator
 178 | +RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + ruling 131"   # RULING 131
 179 | +#   (orchestrator 08:25 ET Nov 17): (A) two of three readings, (B) currency format (the integrator's message of 08:2x
 180 | +#   Nov 17); entries under the old RULES are never read. RULING 105 (orchestrator
 181 |  #   20:13 Nov 14): the unstable second reading joins the rules (the integrator's messages of 20:5x-21:0x Nov 14).
 182 |  #   RULING 103 (orchestrator 14:12 Nov 14): the
 183 |  #   targeted re-listen joins the rules (the integrator's message of 14:3x Nov 14); entries under the old RULES are never
 184 | @@ -158,6 +166,19 @@ def decide(seg, e):
 185 |      spoken, approved = e.get("spoken_text"), seg["approved_text"]
 186 |      if not isinstance(spoken, str) or not spoken.strip():
 187 |          return {"verdict": "error", "outcome": out, "why": "adopt_spoken without a spoken_text"}
 188 | +    adj = e.get("adjudication")
 189 | +    if isinstance(adj, dict) and str(adj.get("rule") or "").startswith(AT.RULE_131):   # RULING 131 (A): two of three
 190 | +        diffs = AT.class_131(spoken, approved, adj)
 191 | +        bad = [x for x in diffs if x["class"] is None]
 192 | +        if bad:                                       # this side's re-check of the lock's record disagrees: fail closed
 193 | +            return {"verdict": "hold", "outcome": out, "differences": diffs,
 194 | +                    "why": "adopt_spoken under ruling 131 (A), but by this side's attest.class_131 it holds: " +
 195 | +                           str([[x["spoken"], x["approved"], x["why"]] for x in bad])[:300]}
 196 | +        if not any(x["took"] == "run" for x in diffs):  # no pair took the spoken reading: the approved text stands
 197 | +            return {"verdict": "pass", "outcome": out, "why": "adopt_spoken under ruling 131 (A) with no pair taking "
 198 | +                                                              "the run's reading: the approved text stands"}
 199 | +        return {"verdict": "adopt", "outcome": out, "why": why, "spoken_text": spoken, "differences": diffs,
 200 | +                "adoption": AT.RULE_131}
 201 |      diffs = AT.class_84(spoken, approved)
 202 |      if not diffs:                                     # the same canonical words: the approved text stands
 203 |          return {"verdict": "pass", "outcome": out, "why": "adopt_spoken with no canonical difference"}
 204 | @@ -262,12 +283,22 @@ def relisten_of(e):
 205 |      return r if isinstance(r, dict) else None
 206 |  
 207 |  
 208 | -def attested(row, run_rule="ruling 72 + ruling 84 (20:41 Nov 13): adopt_spoken, in ruling 84's class"):
 209 | -    """The sealed record of an adopted text (package_pin.SEALED_LATER "attested"), as ruling 67's re-seal records it."""
 210 | -    return {"rule": run_rule, "was": row["approved_text"], "differences": row["differences"],
 211 | -            "carried": "every verdict and gate of this line-up, judged on the text it replaces: each difference is in "
 212 | -                       "ruling 84's class (a filler, one function word, or ruling 67's carry-over class for an insert "
 213 | -                       "or a drop; checked on this side too), and no line quotes the changed words",
 214 | +def attested(row, run_rule=None):
 215 | +    """The sealed record of an adopted text (package_pin.SEALED_LATER "attested"), as ruling 67's re-seal records it:
 216 | +    ruling 84's class, or ruling 131 (A)'s two of three readings (row["adoption"])."""
 217 | +    if row.get("adoption") == AT.RULE_131:
 218 | +        rule = run_rule or "ruling 72 + ruling 131 (A) (08:25 ET Nov 17): adopt_spoken, two of the three readings agree"
 219 | +        carried = ("every verdict and gate of this line-up, judged on the text it replaces: each changed pair is the "
 220 | +                   "reading two of the three readings (the approved text, the render's run decode, the second "
 221 | +                   "recogniser) agree on, re-checked on this side from the lock's record, at least 3 tokens from both "
 222 | +                   "cut edges, never a number, a name or a negation; no line quotes the changed words (marked on the "
 223 | +                   "release: 'word check settled by two of three readings')")
 224 | +    else:
 225 | +        rule = run_rule or "ruling 72 + ruling 84 (20:41 Nov 13): adopt_spoken, in ruling 84's class"
 226 | +        carried = ("every verdict and gate of this line-up, judged on the text it replaces: each difference is in "
 227 | +                   "ruling 84's class (a filler, one function word, or ruling 67's carry-over class for an insert "
 228 | +                   "or a drop; checked on this side too), and no line quotes the changed words")
 229 | +    return {"rule": rule, "was": row["approved_text"], "differences": row["differences"], "carried": carried,
 230 |              "render": {"precheck": row["entry"], "spoken_text": row["spoken_text"]}}
 231 |  
 232 |  
 233 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
 234 | index fb087af..0bd4f5e 100644
 235 | --- a/tests/package/test_lock_precheck.py
 236 | +++ b/tests/package/test_lock_precheck.py
 237 | @@ -11,6 +11,7 @@ import unittest
 238 |  HERE = os.path.dirname(os.path.abspath(__file__))
 239 |  REPO = os.path.dirname(os.path.dirname(HERE))
 240 |  sys.path.insert(0, os.path.join(REPO, "pipeline"))
 241 | +import attest as AT  # noqa: E402
 242 |  import lock_precheck as LP  # noqa: E402
 243 |  
 244 |  HOOK = {"moment_id": "h", "video_id": "DcUbBkyeh9M", "start": 216.0541, "end": 228.6739,
 245 | @@ -133,9 +134,10 @@ class TestRuling84(unittest.TestCase):
 246 |      s = LP.segments_of([BREEDLOVE])[0]
 247 |  
 248 |      def test_the_rules_string_is_the_integrators(self):
 249 | -        """RULING 103 (14:12 Nov 14) and RULING 105 (20:13 Nov 14) joined the integrator's rules string (its messages
 250 | -        of 14:3x and 20:5x Nov 14)."""
 251 | -        self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105")
 252 | +        """RULING 103 (14:12 Nov 14), RULING 105 (20:13 Nov 14) and RULING 131 (08:25 Nov 17) joined the integrator's
 253 | +        rules string (its messages of 14:3x and 20:5x Nov 14 and 08:2x Nov 17)."""
 254 | +        self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + "
 255 | +                                   "ruling 131")
 256 |  
 257 |      def test_the_held_span_of_the_20_12_build_now_adopts(self):
 258 |          spoken = "So over time, um, I came to think, uh, or the money itself was broken."
 259 | @@ -162,6 +164,184 @@ class TestRuling84(unittest.TestCase):
 260 |          self.assertEqual(LP.decide(s2, e)["verdict"], "hold")
 261 |  
 262 |  
 263 | +class TestRuling131(Dirs):
 264 | +    """RULING 131 (orchestrator 08:25 ET Nov 17). (A): per differing pair of the render's lock, two of the three readings
 265 | +    (the approved text, the run's decode, the second recogniser) decide it and the sealed text takes that reading, at
 266 | +    least 3 tokens from both cut edges; never a number, a name or a negation; all three different holds. (B): currency
 267 | +    format is no difference. The render's lock records it (the integrator's message of 08:2x Nov 17); this side
 268 | +    re-derives every pair from the three readings (attest.class_131). Last night's held span: What Bitcoin Did d6adeb54
 269 | +    (WdiF0i925rs 3339.900-3354.680), its three readings as the pre-check recorded them at 03:46:30Z Nov 17."""
 270 | +    RUN = ("i have been recently done a bunch of pieces on the 2023 bull market, that climbing a wall of worry. um there "
 271 | +           "was massive amounts of fear during that period of time. bitcoin was actually trending up into the right, "
 272 | +           "and fear was also trending up into the right during that.")
 273 | +    APPROVED = ("I have been recently done a budget pieces on the 2023 bull market, like climbing a wall of worry. There "
 274 | +                "was massive amounts of fear during that period of time. Bitcoin was actually trending up into the "
 275 | +                "right, and fear was also trending up into the right during that.")
 276 | +    SECOND = ("comes next? I have been, recently done a bunch of pieces on the 2023, uh, bull market, like climbing a "
 277 | +              "wall of worry. Um, there was massive amounts of fear during that period of time. Bitcoin was actually "
 278 | +              "trending up into the right, and fear was also trending up into the right during that,")
 279 | +    MERGED = ("I have been recently done a bunch of pieces on the 2023 bull market, like climbing a wall of worry. Um, "
 280 | +              "there was massive amounts of fear during that period of time. Bitcoin was actually trending up into the "
 281 | +              "right, and fear was also trending up into the right during that.")
 282 | +    SPOKEN = MERGED.replace("2023 bull", "2023, uh, bull")      # ruling 72 on top: the second recogniser's 'uh'
 283 | +    PAIRS = [{"run": "bunch of", "approved": "budget", "second_reads": "run", "took": "run",
 284 | +              "agreed": ["run", "second"], "edge_distance": 6},
 285 | +             {"run": "that", "approved": "like", "second_reads": "approved", "took": "approved",
 286 | +              "agreed": ["approved", "second"], "edge_distance": 14},
 287 | +             {"run": "um", "approved": "", "second_reads": "run", "took": "run", "agreed": ["run", "second"],
 288 | +              "edge_distance": 20}]
 289 | +    WBD = {"moment_id": "w", "video_id": "WdiF0i925rs", "start": 3339.9, "end": 3354.68, "text": APPROVED}
 290 | +
 291 | +    def adj(self, **kw):
 292 | +        return dict({"rule": "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", "verdict": "approved",
 293 | +                     "pairs": self.PAIRS, "recogniser": "elevenlabs:scribe_v1", "usd": 0.0, "run_decode": self.RUN,
 294 | +                     "approved": self.APPROVED, "second_recogniser": self.SECOND}, **kw)
 295 | +
 296 | +    def decide(self, spoken=None, **kw):
 297 | +        s = LP.segments_of([self.WBD])[0]
 298 | +        return LP.decide(s, entry(s, "adopt_spoken", spoken_text=spoken or self.MERGED, adjudication=self.adj(**kw)))
 299 | +
 300 | +    def test_last_nights_held_span_now_adopts_and_is_sealed_with_its_record(self):
 301 | +        d = self.decide()                                          # the merged text as it stands ("same")
 302 | +        self.assertEqual(d["verdict"], "adopt", d.get("why"))
 303 | +        self.assertEqual([(x["spoken"], x["approved"], x["took"]) for x in d["differences"]],
 304 | +                         [("bunch of", "budget", "run"), ("that", "like", "approved"), ("um", "", "run")])
 305 | +        d = self.decide(self.SPOKEN)                               # with ruling 72's 'uh' on top ("adopt")
 306 | +        self.assertEqual(d["verdict"], "adopt", d.get("why"))
 307 | +        self.assertEqual([(x["spoken"], x["approved"], x["took"], x["class"]) for x in d["differences"]][3:],
 308 | +                         [("uh", "", "ruling 72", "filler")])
 309 | +        s = LP.segments_of([self.WBD])[0]
 310 | +        self.put(s, entry(s, "adopt_spoken", spoken_text=self.SPOKEN, adjudication=self.adj()))
 311 | +        pre = LP.check([self.WBD], "r", self.req, self.res, log=lambda m: None)
 312 | +        pk = LP.apply({"segments": [{k: self.WBD[k] for k in ("video_id", "start", "end", "text")}], "lines": []}, pre)
 313 | +        seg = pk["segments"][0]
 314 | +        self.assertEqual((seg["text"], seg["attested"]["was"]), (self.SPOKEN, self.APPROVED))
 315 | +        self.assertIn("ruling 131 (A)", seg["attested"]["rule"])
 316 | +        self.assertIn("two of the three readings", seg["attested"]["carried"])
 317 | +        self.assertEqual(LP.pin_problems(pk), [])
 318 | +
 319 | +    def test_this_side_rederives_every_pair_and_never_trusts_the_record(self):
 320 | +        lie = [dict(self.PAIRS[0]), dict(self.PAIRS[1], took="run", agreed=["run", "second"]), dict(self.PAIRS[2])]
 321 | +        for spoken, kw, why in (
 322 | +                (self.MERGED.replace("like climbing", "that climbing"), {"pairs": lie},   # the second reads 'like'
 323 | +                 "the lock record's pairs are not this side's"),
 324 | +                (self.MERGED, {"pairs": self.PAIRS[:2]}, "the lock record's pairs are not this side's"),
 325 | +                (self.MERGED, {"pairs": [dict(p, edge_distance=9) for p in self.PAIRS]},
 326 | +                 "the lock record's pairs are not this side's"),
 327 | +                (self.MERGED.replace("bunch of", "budget"), {}, "neither the merged reading nor"),
 328 | +                (self.MERGED.replace("massive", "huge"), {}, "neither the merged reading nor"),
 329 | +                (self.MERGED.replace("climbing", "the climbing"), {}, "neither the merged reading nor"),
 330 | +                (self.SPOKEN.replace("massive", "huge"), {"second_recogniser": self.SECOND.replace("massive", "huge")},
 331 | +                 "outside ruling 84's class"),                                     # the second recogniser alone
 332 | +                (self.MERGED, {"second_recogniser": None}, "does not hold the three readings"),
 333 | +                (self.MERGED, {"approved": self.MERGED}, "does not hold the three readings")):
 334 | +            d = self.decide(spoken, **kw)
 335 | +            self.assertEqual(d["verdict"], "hold", (spoken, kw))
 336 | +            self.assertIn(why, d["why"])
 337 | +
 338 | +    def test_what_still_holds(self):
 339 | +        for kw, why in (
 340 | +                ({"second_recogniser": self.SECOND.replace("bunch of", "lunch of")}, "all three readings differ"),
 341 | +                ({"run_decode": self.RUN.replace("have been", "have seen"),               # the 3rd token: 2 from the
 342 | +                  "second_recogniser": self.SECOND.replace("have been", "have seen")},     # edge
 343 | +                 "within 3 tokens of a cut edge"),
 344 | +                ({"run_decode": self.RUN.replace("2023", "2024"),
 345 | +                  "second_recogniser": self.SECOND.replace("2023", "2024")}, "a number, a name or a negation"),
 346 | +                ({"run_decode": self.RUN.replace("there was", "there wasn't"),
 347 | +                  "second_recogniser": self.SECOND.replace("there was", "there wasn't")},
 348 | +                 "a number, a name or a negation"),
 349 | +                ({"run_decode": self.RUN.replace("bunch of", "Saylor"),
 350 | +                  "second_recogniser": self.SECOND.replace("bunch of", "Saylor")}, "a number, a name or a negation")):
 351 | +            d = self.decide(**kw)
 352 | +            self.assertEqual(d["verdict"], "hold", kw)
 353 | +            self.assertIn(why, d["why"])
 354 | +
 355 | +    def test_currency_format_is_no_difference(self):
 356 | +        """BTC Sessions 93cfa865 (2oY7TU6CPok 54.260-61.380), the line-up's second hold: the approved '$2 billion',
 357 | +        '$645 million'; the run's decode and the second recogniser say no 'dollars' (the pre-check at 03:46:32Z)."""
 358 | +        app = ("Meanwhile, Bitcoin had a terrible weekend. We went all the way down to 62K, $2 billion in leverage wiped "
 359 | +               "out, $645 million in just 30 minutes.")
 360 | +        adj = self.adj(pairs=[], run_decode="meanwhile, bitcoin had a terrible weekend. we went all the way down to "
 361 | +                                            "62k, 2 billion in leverage wiped out, 645 million in just 30 minutes.",
 362 | +                       approved=app, second_recogniser="emerging. Meanwhile, Bitcoin had a terrible weekend. We went "
 363 | +                       "all the way down to 62K, two billion in leverage wiped out, 645 million in just 30 minutes.")
 364 | +        s = LP.segments_of([{"video_id": "2oY7TU6CPok", "start": 54.26, "end": 61.38, "text": app}])[0]
 365 | +        rows = AT.class_131(app, app, adj)
 366 | +        self.assertEqual([(x["spoken"], x["approved"], x["took"]) for x in rows],
 367 | +                         [("", "dollars", "currency"), ("", "dollars", "currency")])
 368 | +        self.assertEqual(LP.decide(s, entry(s, "adopt_spoken", spoken_text=app, adjudication=adj))["verdict"], "pass")
 369 | +        self.assertTrue(AT.currency_pair(["2000000000", "dollars"], ["2000000000"], ("delete", 1, 2, 1, 1)))
 370 | +        self.assertTrue(AT.currency_pair(["2000000000"], ["2000000000", "dollars"], ("insert", 1, 1, 1, 2)))
 371 | +        self.assertFalse(AT.currency_pair(["many", "dollars"], ["many"], ("delete", 1, 2, 1, 1)))   # no number before
 372 | +        self.assertFalse(AT.currency_pair(["5", "dollars", "dollars"], ["5", "dollars"], ("delete", 2, 3, 2, 2)))
 373 | +        self.assertFalse(AT.currency_pair(["5", "euros"], ["5", "dollars"], ("replace", 1, 2, 1, 2)))
 374 | +        self.assertFalse(AT.currency_pair(["5", "dollars"], ["5", "euros"], ("replace", 1, 2, 1, 2)))
 375 | +
 376 | +    def test_a_repetition_slides_to_its_furthest_placement(self):
 377 | +        """mKNAcOFMYD4 755.454-764.214, held Nov 13 (its real readings): difflib puts the extra "that's why" on the
 378 | +        second copy, 2 tokens from the end; the first copy gives the same two texts and is 4 from it (the integrator's
 379 | +        message of 08:4x Nov 17). A spoken text that reverts the vote holds, though it is in ruling 84's class."""
 380 | +        run = ("my biggest fear is that i go to the bank and i punch in my code and the money's not there because the "
 381 | +               "bank owns the money and they could just take it from me. and that's why that's why we bitcoin.")
 382 | +        app = ("My biggest fear is that I go to the bank and I punch you my code and the money's not there because the "
 383 | +               "bank owns the money and they could just take it from me. And that's why we Bitcoin.")
 384 | +        sec = ("second biggest. My biggest fear is that I go to the bank and I punch in my code and the money's not "
 385 | +               "there, 'cause the bank owns the money and they could just take it from me, and that's why, that's why "
 386 | +               "we Bitcoin.")
 387 | +        merged = app.replace("punch you", "punch in").replace("that's why we", "that's why that's why we")
 388 | +        pairs = [{"run": "in", "approved": "you", "took": "run", "edge_distance": 13},
 389 | +                 {"run": "that's why", "approved": "", "took": "run", "edge_distance": 4}]
 390 | +        s = LP.segments_of([{"video_id": "mKNAcOFMYD4", "start": 755.454, "end": 764.214, "text": app}])[0]
 391 | +        adj = self.adj(pairs=pairs, run_decode=run, approved=app, second_recogniser=sec)
 392 | +        self.assertEqual(LP.decide(s, entry(s, "adopt_spoken", spoken_text=merged, adjudication=adj))["verdict"],
 393 | +                         "adopt")
 394 | +        back = LP.decide(s, entry(s, "adopt_spoken", spoken_text=app, adjudication=adj))
 395 | +        self.assertEqual(back["verdict"], "hold")
 396 | +        self.assertIn("neither the merged reading nor", back["why"])
 397 | +
 398 | +    def test_a_repetition_near_the_start_slides_right(self):
 399 | +        """The same repetition near the span's start: difflib puts the extra "that's why" on the FIRST copy (1 token
 400 | +        from the edge); sliding right through the equal words gives 3."""
 401 | +        app = "So that's why we went to the bank and asked them for the money back."
 402 | +        run = "so that's why that's why we went to the bank and asked them for the money back."
 403 | +        s = LP.segments_of([{"video_id": "x", "start": 1.0, "end": 9.0, "text": app}])[0]
 404 | +        adj = self.adj(pairs=[{"run": "that's why", "approved": "", "took": "run", "edge_distance": 3}],
 405 | +                       run_decode=run, approved=app, second_recogniser=run)
 406 | +        r, p, ops = AT.diff(run, app)
 407 | +        # the base distance is min(1, 14) = 1; sliding right through the equal run gives 3
 408 | +        self.assertEqual((ops, AT.edge_distance(r, p, ops[0])), ([("delete", 1, 3, 1, 1)], 3))
 409 | +        d = LP.decide(s, entry(s, "adopt_spoken", spoken_text="So that's why that's why we went to the bank and asked "
 410 | +                                                               "them for the money back.", adjudication=adj))
 411 | +        self.assertEqual(d["verdict"], "adopt", d.get("why"))
 412 | +
 413 | +    def test_ruling_72_on_top_is_the_second_recognisers_reading_with_its_spill_trimmed(self):
 414 | +        """The pre-check's as_spoken text is the second recogniser's tokens with the neighbours' spill trimmed, except
 415 | +        the speaker's own edge repeat ('When, when'); a padding word ('So') is never adopted."""
 416 | +        app = "When we started this we had a budget pieces of the plan and it worked out."
 417 | +        run = "when we started this we had a bunch of pieces of the plan and it worked out."
 418 | +        sec = "So when, when we started this we had a bunch of pieces of the plan and it worked out."
 419 | +        s = LP.segments_of([{"video_id": "y", "start": 2.0, "end": 9.0, "text": app}])[0]
 420 | +        adj = self.adj(pairs=[{"run": "bunch of", "approved": "budget", "took": "run", "edge_distance": 7}],
 421 | +                       run_decode=run, approved=app, second_recogniser=sec)
 422 | +        merged = app.replace("a budget", "a bunch of")
 423 | +        self.assertEqual(AT.spill_trimmed(AT.canon.canon_tokens(merged), AT.canon.canon_tokens(sec))[:3],
 424 | +                         ["when", "when", "we"])
 425 | +        twice = "When, when " + merged[5:]
 426 | +        for second, spoken, verdict in ((sec, merged, "adopt"), (sec, twice, "adopt"),
 427 | +                                        (sec, "So when, when " + merged[5:], "hold"), (sec, "So " + merged, "hold"),
 428 | +                                        (sec + " And then", twice, "adopt"),            # the next sentence's spill
 429 | +                                        (sec + " And then", twice[:-1] + " and then.", "hold"),
 430 | +                                        (sec + " out", twice[:-1] + ", out.", "adopt")):   # the speaker's own repeat
 431 | +            d = LP.decide(s, entry(s, "adopt_spoken", spoken_text=spoken,
 432 | +                                   adjudication=dict(adj, second_recogniser=second)))
 433 | +            self.assertEqual(d["verdict"], verdict, (second, spoken, d.get("why")))
 434 | +
 435 | +    def test_only_a_ruling_131_record_is_rechecked_by_two_of_three(self):
 436 | +        d = self.decide(rule="ruling 17 (orchestrator 2026-11-12 '10:20')")                # ruling 84's class: a
 437 | +        self.assertEqual(d["verdict"], "hold")                                             # content word holds
 438 | +        self.assertIn("outside ruling 84's class", d["why"])
 439 | +
 440 | +
 441 |  class TestCheck(Dirs):
 442 |      def run_check(self, segs, appear=None, timeout=60.0):
 443 |          t = [0.0]
 444 | diff --git a/tests/package/test_ruling_105.py b/tests/package/test_ruling_105.py
 445 | index 0b8d8b9..9e5d466 100644
 446 | --- a/tests/package/test_ruling_105.py
 447 | +++ b/tests/package/test_ruling_105.py
 448 | @@ -39,7 +39,7 @@ BLOCKWARE = record()
 449 |  
 450 |  class TestTheRules(Dirs):
 451 |      def test_the_rules_and_decoder_are_the_integrators_ruling_105_ones(self):
 452 | -        self.assertTrue(LP.RULES.endswith("+ ruling 103 + ruling 105"))
 453 | +        self.assertIn("+ ruling 103 + ruling 105", LP.RULES)                      # ruling 131 joined after it
 454 |          self.assertEqual(LP.DECODER, "a4c307f78c94")
 455 |          s = LP.segments_of([HOOK])[0]
 456 |          self.put(s, entry(s, rules="ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103",
 457 | 
```

---

pp-selectid: RULING 131 (orchestrator 08:25 ET Nov 17), the builder's lockstep half. "(A) ADOPTED as written: per
differing pair, two of the three readings (approved text, the render's run decode, the second recogniser) decide it
and the sealed text takes that reading, for fillers, function words, repetitions and content words, each at least 3
words from a cut edge; never a number (save B), a name or a negation; a pair where all three differ HOLDS. (B)
ADOPTED: a currency symbol is formatting ('$2 billion' equals a spoken '2 billion'), a canon like 401k."
The render's lock (the integrator's side, pinned.adjudicate_lock) applies it and records it; THIS side only reads the
lock pre-check's answer for a segment and decides whether to seal it. Files: pipeline/attest.py,
pipeline/lock_precheck.py, tests/package/test_lock_precheck.py, tests/package/test_ruling_105.py. canon.py is the
integrator's, taken byte-identical at landing: this side uses only canon.dollars_after_number(tokens, k) (tokens[k] ==
"dollars", k > 0, tokens[k-1] matches \d+(\.\d+)?), canon.canon_tokens and canon.canon_spans (all UNCHANGED otherwise).

THE RECORD (the integrator's messages of 08:2x-08:4x Nov 17): an entry with outcome "adopt_spoken" whose
"adjudication" (the FIRST lock's) has rule "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", the three full readings
"run_decode", "approved", "second_recogniser", and "pairs" [{"run", "approved", "second_reads", "took":
"run"|"approved", "agreed", "edge_distance"}], currency pairs NOT among them. "spoken_text" is the lock's merged text,
or that with ruling 72's adoptions on top (the second recogniser's fillers / a repetition / one function word beyond
the merged text: today's adopt_spoken layer). The render's rule per pair: the approved reading where the second
recogniser reads the approved words; else the run's where it reads the run's AND edge_distance >= 3; else HOLD.
edge_distance = min(a, len(run) - b) in the run decode's canon tokens, except that a pair with an empty side (delete /
insert) inside a repetition may slide through the equal tokens beside it (both texts stay the same), taking the
largest distance over its placements.

THE CHANGE:
(a) attest.class_131(spoken, approved, adj) (attest.py:168): THIS SIDE'S OWN RE-CHECK, re-running the render's steps
    on the recorded readings, never trusting the record's classes. attest.diff (UNCHANGED :69: canon tokens,
    SequenceMatcher non-equal opcodes); per pair: currency_pair (:134) -> no difference, keeps the approved words; a
    number, a name or a negation (attest.critical, UNCHANGED :54, the render's _lv2_critical) -> holds; the second
    recogniser reads the approved words (attest.reads, UNCHANGED :239, the render's own test) -> took approved; else
    reads the run's AND edge_distance (:142) >= 3 -> took run; else holds. Whole-record tests: the record's pairs must
    equal this side's (run, approved, took, edge_distance) in order; the record's approved reading must be the
    segment's approved text (canon tokens); the spoken text against the merged tokens: every difference must be in
    ruling 84's class (attest.class_84, UNCHANGED :94) AND be the second recogniser's own reading there (reads).
(b) lock_precheck.decide (lock_precheck.py:148): an adopt_spoken whose adjudication rule starts with "ruling 131 (A)"
    goes to class_131: any class None -> hold (fail closed); no pair took the run's reading -> pass (the approved
    stands); else adopt with "adoption": "ruling 131 (A)". Every other adopt_spoken keeps class_84 exactly as before.
    Ruling 105's check runs first for every pass and adoption (UNCHANGED :155).
(c) lock_precheck.attested (:286): the sealed record's rule holds the literal "ruling 131 (A)" (the integrator's
    release caption prints 'word check settled by two of three readings' from it) when the row's adoption is ruling
    131's, else ruling 84's as before. apply (UNCHANGED :311) seals the spoken text with it and still refuses when a
    line quotes the changed words (:326); pin_problems (UNCHANGED :348) still needs the pre-check to cover the segments
    as they now stand.
(d) RULES gains "+ ruling 131" (an entry under the old rules is never read: _matches, UNCHANGED :105). DECODER moves to
    the integrator's final sha at landing (a constant; the old one joins the never-read list).

TESTS (TestRuling131, 7 tests): last night's held span (WdiF0i925rs 3339.900-3354.680, its REAL three readings)
adopts as merged and with ruling 72's 'uh' on top, sealed through check/apply with the ruling 131 record; a record
that lies (a pair claimed run that the second reads as approved; a missing pair; a wrong edge distance; a spoken text
outside the class; a function word the second recogniser never heard; a content word only the second recogniser
heard; no readings; another approved text) holds; all three different, a run pair 2 tokens from the edge, a number,
a negation, a name hold; mKNAcOFMYD4's real readings: the repeated "that's why" slides left to 4 and adopts, and a
spoken text that reverts the vote holds; the same repetition near the start slides right (1 -> 3); the BTC Sessions
span (real readings) is currency format only and passes; currency_pair's edges; an adopt_spoken under ruling 17's
record keeps ruling 84's class. Mutations M1-M19 after a control run: 19 of 19 killed.

PLEASE CHECK: (1) that nothing the ruling forbids can be sealed: a number, a name, a negation, a three-way
disagreement, a run reading within 3 tokens of an edge; (2) that a record which disagrees with this side's own
derivation always holds, never passes; (3) that the currency test cannot hide a real difference; (4) that the slide
cannot carry a pair that is not a true repetition, nor beyond the equal tokens beside it; (5) that ruling 72's layer
on the merged text cannot reintroduce or revert a decided word; (6) that ruling 84's existing path is unchanged for
any other adopt_spoken; (7) the tests.


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
