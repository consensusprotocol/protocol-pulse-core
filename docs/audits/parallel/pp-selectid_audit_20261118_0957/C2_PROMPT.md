# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261118_0957
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 277 s finish=stop usage in 7965 / out 2974 usd_reported=0.000616 usd~0.069 (upper-bound price)

The code implements a surgical fix for a tokenization bug in `pipeline/attest.py` where the "spaced-thousands" rule in `canon.py` caused false-positive "holds" during the render lock pre-check.

### Analysis

**1. The Defect**
The issue occurred in `class_131` when it joined a list of canon tokens (the merged reading) into a string and then passed that string to `class_84`. `class_84` would then re-tokenize that string. Because `canon.canon_tokens` treats a digit, a space, and three digits as a single number (e.g., `"7 365"` $\rightarrow$ `["7365"]`), the tokens `['24', '7', '365']` became `['24', '7365']`. This created a perceived number difference against the spoken text `['24', '7', '365']`, triggering a "hold" under Law L-v 2 (implied by the "number difference" rule in `class_84`).

**2. The Fix**
The modification to `class_84` introduces an optional `approved_tokens` parameter. 
- If provided, it bypasses the `diff(spoken, approved)` call (which performs the problematic re-tokenization of the `approved` string).
- Instead, it uses the provided tokens directly and computes the `SequenceMatcher` opcodes.
- `class_131` now passes the `merged` token list directly to `class_84`.

**3. Law Compliance**
- **L-k (One Canonical Form):** The fix maintains strict adherence to `canon.py`. It uses `canon.canon_tokens(spoken)` for the spoken side and preserves the existing canon tokens for the approved side, ensuring no ad-hoc normalization is introduced.
- **Law 20 / M2:** This is not a threshold change to force a pass; it is a correction of a logic error (a false positive "hold") that was incorrectly identifying a difference where none existed in the canonical tokens.
- **M12 (Fail Closed):** The logic still "holds" if a genuine difference (e.g., `365` vs `366`) is detected, as verified by the new tests.

**4. Verification of Questions**
- **Genuine differences:** A genuine number, name, or negation difference will still result in a non-equal opcode. Since these are not in the `FILLERS` list or categorized as "function words," they will still return `class: None` and cause a "hold."
- **Critical-word test:** The `texts = (spoken, approved)` assignment remains unchanged, ensuring that the strings used for logging and the critical-word test remain identical to the previous version.
- **Side effects:** The change is isolated to `class_84` and `class_131`. Other callers of `class_84` do not pass `approved_tokens`, so their behavior remains unchanged.

### Findings

No violations of the Governing Laws or technical defects were found. The implementation is correct and the tests are comprehensive.

P1_OR_WORSE: 0

## GPT-OSS-20B — CYCLE 1 OUTPUT
# gpt-oss-20b (openai/gpt-oss-20b) 27 s finish=stop usage in 7047 / out 4407 usd_reported=0.000763 usd~0.087 (upper-bound price)

**Findings**

| # | Finding | Severity | Explanation |
|---|---------|----------|-------------|
| 1 | **Potential misuse of `approved_tokens`** | [P3] | The new optional argument can be supplied incorrectly (e.g., non‑canonical tokens, mismatched to the `approved` string). If a caller passes such a list, the diff will compare against those tokens and may silently accept a genuine number/name/negation difference. The change is internal to `class_131`, but future developers could misuse it. |
| 2 | **Backward‑compatibility guard** | [P3] | The default `approved_tokens=None` preserves the original two‑argument API, but the signature change may cause confusion or accidental passing of a third argument in other modules. No functional impact, but a documentation note is advisable. |
| 3 | **Inconsistent `texts` tuple** | [P3] | `texts = (spoken, approved)` is still built even when `approved_tokens` is supplied. If `approved` does not match the token list, the critical‑word test in `class_131` could compare mismatched data. This is not a current issue because `class_131` passes a consistent string, but the code could be clarified. |
| 4 | **No effect on other callers** | [P3] | All other callers of `class_84` still use the two‑argument form, so the change does not alter their behaviour. |
| 5 | **No new logic errors** | [P3] | The diff logic and filler handling remain unchanged; the only modification is the optional token list. No new gate failures or data loss are introduced. |

**P1_OR_WORSE: 0**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 161 s finish=stop usage in 7690 / out 6200 usd_reported=0.005782 usd~0.116 (upper-bound price)



# Code Audit — pp-selectid / RULING 148 (3) / 149

## Summary

The change is a surgical fix to `attest.class_84`: when the caller already holds the approved side's canon tokens (as `class_131` does with its `merged` list), pass them through instead of joining to a string and re-tokenising. The re-tokenisation was the bug: canon's spaced-thousands rule turned `"24 7 365"` into `["24", "7365"]`, creating a phantom number difference against the spoken `["24", "7", "365"]`.

I verified the three questions posed in the diff header, plus law compliance and edge cases.

---

## Findings

### [P3] `autojunk=False` is new relative to the old `diff()` path

```python
ops = [o for o in SequenceMatcher(None, r, p, autojunk=False).get_opcodes() if o[0] != "equal"]
```

If the existing `diff()` helper does **not** pass `autojunk=False`, then for token sequences longer than 200 elements the two paths could produce different opcodes (SequenceMatcher's automatic-junk heuristic would suppress frequent elements). In practice a single clip's transcript will never exceed 200 tokens, so this is theoretical. Still, the new branch is now the *only* place `autojunk=False` is explicit; if `diff()` lacks it, the two code paths are not byte-identical in their diffing semantics for the spoken side. Worth a one-line comment or a shared helper so the invariant is visible.

### [P3] No guard that `approved_tokens` is a list of strings

`list(approved_tokens)` will happily wrap a generator, a set, or a list of non-strings. The function would then fail (or misbehave) at the `r[i] in FILLERS` or the SequenceMatcher comparison. This is an internal function with exactly one caller (`class_131`) that passes `merged` (a list of canon-token strings), so the risk is nil in production. A `typing` annotation (`Sequence[str] | None`) on the signature would document the contract without adding runtime cost.

### [P3] Docstring could state the invariant on `approved_tokens`

The new docstring paragraph explains *why* the parameter exists (the join-re-read bug) but does not state the precondition: **`approved_tokens` must be the output of `canon.canon_tokens` (or the equivalent merged-reading token list) for the same text that `approved` represents.** If a future caller passes tokens from a *different* normalisation, the comparison is silently meaningless. One sentence ("must be the canon tokens of `approved`") would close that gap.

---

## Answers to the three review questions

**(1) Can `approved_tokens` let a genuine number / name / negation difference through?**

No. The classification logic (steps 2–5 of the docstring) operates on the *values* in the opcode spans, not on how the tokens were obtained. I traced three cases:

| Spoken tokens | `approved_tokens` | Opcode | Step that holds |
|---|---|---|---|
| `[…, "41", …]` | `[…, "40", …]` | substitute | 2 – number |
| `[…, "do", "not", …]` | `[…, …]` | insert ×2 | 2 – negation |
| `[…, "euros"]` | `[…, "dollars"]` | substitute | 2 – name |

The test `test_a_number_that_differs_still_holds` confirms this for 365→366 and 24→25.

**(2) Is the merged reading's critical-word test (`texts`) still the same as before?**

Yes. `texts = (spoken, approved)` is set before the branch and is unchanged. `approved` is still the joined string (`" ".join(merged)` in `class_131`). The critical-word scan reads the human-readable text, not the token list. The diff only changes how `r`, `p`, and `ops` are computed for the *structural* comparison.

**(3) Anything else this changes?**

- All other callers of `class_84` pass `approved_tokens=None` (the default) and take the old `diff(spoken, approved)` path. No behavioural change for them.
- `list(approved_tokens)` creates a shallow copy, so the caller's list is not mutated.
- The `drop` / filler-removal / re-compare logic downstream of `ops` is unchanged; it reads `r` (spoken tokens) and the opcode indices, which are now computed against the correct approved tokens.
- Law L-k (one canonical form): both sides of the comparison are canon tokens. Compliant.
- Law 20 / M2: no threshold is changed; a held class is still a hard stop. The fix removes a *false* hold, not a real one.
- M12 fail-closed: no new pass path is introduced; the default path is byte-identical to before.

---

## Law-compliance spot-check

| Law | Status |
|---|---|
| SENTENCE LAW | Not touched by this diff. |
| SELECTION LOCK | Not touched. |
| L-k (canon) | Improved: approved side is now compared as its actual canon tokens. |
| LAW 20 / M2 | Compliant: no threshold or acceptance criterion changed. |
| M12 | Compliant: no new pass path. |
| Smallest diff / M1 | 100-line diff, one function signature change, one call-site change, one test class. Minimal. |

---

## Verdict

The change is correct, well-scoped, and well-tested. The root cause (join → re-tokenise → spaced-thousands

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus (pp-selectid_audit_20261118_0957, ruling 148 (3): class_131 compares the merged reading as its tokens)

SEATS ANSWERED: 3 of 3: P0/P1 none from qwen3.8-27b, gpt-oss-20b, gemma-4-31b-it (their traces quoted above in each
file: approved_tokens, the 7365 re-read, texts unchanged). P2/P3 notes, if any, are style only.

## No change from cycle 1 to cycle 2.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261118_0957/C2_STEP.diff (100 lines)
```
   1 | diff --git a/pipeline/attest.py b/pipeline/attest.py
   2 | index 690d09a..cca269f 100644
   3 | --- a/pipeline/attest.py
   4 | +++ b/pipeline/attest.py
   5 | @@ -98,7 +98,7 @@ def carry_class(r, p, op, texts):
   6 |      return "immediate repetition" if any(repeats(*s) for s in sides) else "function word"
   7 |  
   8 |  
   9 | -def class_84(spoken, approved):
  10 | +def class_84(spoken, approved, approved_tokens=None):
  11 |      """RULING 84 (orchestrator 20:41 Nov 13): the render's lock pre-check class, as the integrator's pre-check applies
  12 |      it (its message of 20:4x Nov 13), on this side's comparison: the spoken text (the second recogniser's reading)
  13 |      against the approved text. -> [{"spoken", "approved", "class"}], one per difference; a class None holds.
  14 | @@ -107,9 +107,17 @@ def class_84(spoken, approved):
  15 |      2. The fillers dropped, the texts are compared again. A number, a negation or a name on either side holds.
  16 |      3. One token against one token, both function words: "one function word". At most ONE per span; another holds.
  17 |      4. Any other substitution (both sides non-empty) holds, a 2-for-2 or 1-for-2 of function words included.
  18 | -    5. An insert or a drop: ruling 67's class (carry_class), unchanged, on the filler-free spoken text."""
  19 | +    5. An insert or a drop: ruling 67's class (carry_class), unchanged, on the filler-free spoken text.
  20 | +    approved_tokens (RULING 148 (3)): the approved side's canon tokens as they are (class_131's merged reading), never
  21 | +    tokenised again from a joined string: canon reads digits, a space and three digits as one number ('24 7 365' ->
  22 | +    ['24', '7365']), so a re-read join can differ from its own tokens (build 149: Yahoo Finance f0a51c45 held on '7 365'
  23 | +    against '7365', which the render's lock adopts). approved stays the text the critical-word test reads."""
  24 |      texts = (spoken, approved)
  25 | -    r, p, ops = diff(spoken, approved)
  26 | +    if approved_tokens is None:
  27 | +        r, p, ops = diff(spoken, approved)
  28 | +    else:
  29 | +        r, p = canon.canon_tokens(spoken), list(approved_tokens)
  30 | +        ops = [o for o in SequenceMatcher(None, r, p, autojunk=False).get_opcodes() if o[0] != "equal"]
  31 |      drop = {i for _tag, a, b, _c, _d in ops for i in range(a, b) if r[i] in FILLERS}
  32 |      out = [{"spoken": r[i], "approved": "", "class": "filler"} for i in sorted(drop)]
  33 |      r2 = [t for i, t in enumerate(r) if i not in drop]
  34 | @@ -263,7 +271,8 @@ def class_131(spoken, approved, adj):
  35 |      if sp != merged and sp != spill_trimmed(merged, s):  # ruling 72 adopts only the second recogniser's own reading
  36 |          out.append(held("the spoken text is neither the merged reading nor the second recogniser's own reading of the "
  37 |                          "span (ruling 72 adopts only its reading)"))
  38 | -    for x in class_84(spoken, " ".join(merged)):        # ruling 72 on top of the merged reading, as today
  39 | +    for x in class_84(spoken, " ".join(merged), merged):   # ruling 72 on top of the merged reading, as today; RULING
  40 | +        #   148 (3): compared as its tokens, never re-read from the join ('24 7 365' would read ['24', '7365'])
  41 |          out.append(dict(x, took="ruling 72", edge_distance=None, **(
  42 |              {"why": "the spoken text differs from the merged reading outside ruling 84's class"} if x["class"] is None
  43 |              else {})))
  44 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
  45 | index 957d68e..a70ed0c 100644
  46 | --- a/tests/package/test_lock_precheck.py
  47 | +++ b/tests/package/test_lock_precheck.py
  48 | @@ -387,6 +387,51 @@ class TestRuling135(unittest.TestCase):
  49 |          self.assertEqual(LP.decide(s, entry(s, "adopt_spoken", spoken_text=app, adjudication=adj))["verdict"], "pass")
  50 |  
  51 |  
  52 | +class TestRuling148TheMergedReadingKeepsItsTokens(unittest.TestCase):
  53 | +    """RULING 148 (3) (orchestrator 09:38 ET Nov 18): build 149 lost Yahoo Finance f0a51c45 to this side's own re-check,
  54 | +    not to the render's lock, which adopts the clip under ruling 131 (A). class_131 joined the merged reading's canon
  55 | +    tokens with spaces and class_84 tokenised the join again; canon reads digits, a space and three digits as one number
  56 | +    (spaced thousands), so '24 7 365' became ['24', '7365'] against the spoken ['24', '7', '365'] and held as a number
  57 | +    (law L-v 2). The readings below are the render's lock record (F536pi4mr7Y 461.650-478.940, decoder 50fa01b400bd)."""
  58 | +    RUN = ("But if you're wondering why having decentralized money that's available 24 -7, 365, that has no CEO and is "
  59 | +           "mined by a decentralized network around the world, like Bitcoin, is important. Well, when you want access "
  60 | +           "to your money with Bitcoin, you have it.")
  61 | +    APP = ("But, you know, if you're wondering why having decentralized money that's available 24 -7, 365, that has no "
  62 | +           "CEO in his mind by a decentralized network. around the world, like Bitcoin is important. Well, when you want "
  63 | +           "access to your money with Bitcoin, you have it.")
  64 | +    SEC = ("is. But, you know, if you're wondering why having decentralized money that's available 24/7/365, uh, that "
  65 | +           "has no CEO and is mined by a decentralized network around the world, like Bitcoin, is important, well, when "
  66 | +           "you want access to your money, with Bitcoin, you have it. Now,")
  67 | +    SPOKEN = APP.replace("in his mind", "and is mined")
  68 | +    PAIRS = [{"run": "", "approved": "you know", "second_reads": "approved", "took": "approved",
  69 | +              "agreed": ["approved", "second"], "edge_distance": 1},
  70 | +             {"run": "and is mined", "approved": "in his mind", "second_reads": "run", "took": "run",
  71 | +              "agreed": ["run", "second"], "edge_distance": 17}]
  72 | +
  73 | +    def adj(self):
  74 | +        return {"rule": "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", "run_decode": self.RUN, "approved": self.APP,
  75 | +                "second_recogniser": self.SEC, "pairs": self.PAIRS}
  76 | +
  77 | +    def test_the_cause_a_join_is_not_its_tokens(self):
  78 | +        self.assertEqual(C.canon_tokens("24 7 365"), ["24", "7365"])
  79 | +        self.assertEqual(C.canon_tokens("24 -7, 365"), ["24", "7", "365"])
  80 | +
  81 | +    def test_the_render_locks_adoption_is_this_sides_too(self):
  82 | +        self.assertEqual([r for r in AT.class_131(self.SPOKEN, self.APP, self.adj()) if r["class"] is None], [])
  83 | +        s = LP.segments_of([{"video_id": "F536pi4mr7Y", "start": 461.65, "end": 478.94, "text": self.APP}])[0]
  84 | +        d = LP.decide(s, entry(s, "adopt_spoken", spoken_text=self.SPOKEN, adjudication=self.adj()))
  85 | +        self.assertEqual((d["verdict"], d.get("adoption")), ("adopt", AT.RULE_131), d)
  86 | +
  87 | +    def test_a_number_that_differs_still_holds(self):
  88 | +        for spoken in (self.SPOKEN.replace("365", "366"), self.SPOKEN.replace("24 -7", "25 -7")):
  89 | +            self.assertTrue([r for r in AT.class_131(spoken, self.APP, self.adj()) if r["class"] is None], spoken)
  90 | +
  91 | +    def test_class_84_reads_given_tokens_as_they_are(self):
  92 | +        self.assertEqual([x for x in AT.class_84("24 -7, 365 days", "24 7 365 days") if x["class"] is None],
  93 | +                         [{"spoken": "7 365", "approved": "7365", "class": None}])    # the join, re-read
  94 | +        self.assertEqual(AT.class_84("24 -7, 365 days", "24 7 365 days", ["24", "7", "365", "days"]), [])
  95 | +
  96 | +
  97 |  class TestRuling142(unittest.TestCase):
  98 |      """RULING 142 (orchestrator 14:32 ET Nov 17), the integrator's batch 110 mirrored (its canon.py byte-identical, its
  99 |      adjudicate_lock hunk in attest.class_131): (1) a hyphen right after a number and a space, before a digit, is never
 100 | 
```

---

pp-selectid: RULING 148 (3) / 149 (orchestrator 09:56 ET Nov 18): ONE RULE IN ONE FILE (pipeline/attest.py).
THE DEFECT (build 149, 09:34 ET): this side's re-check of the render lock's adoption (attest.class_131, step 5) held Yahoo
Finance f0a51c45 although the render's own lock adopts it under ruling 131 (A). class_131 builds the merged reading as
CANON TOKENS (merged), then called class_84(spoken, " ".join(merged)): class_84 tokenises that join AGAIN, and canon reads
digits, a space and three digits as ONE number (its spaced-thousands rule, canon.py _SPACED_THOUSANDS, unchanged:
'74 000' = 74000). So the merged tokens ['24', '7', '365'] re-read as ['24', '7365'] against the spoken text's
['24', '7', '365'] ('24 -7, 365'): a number difference, held (law L-v 2). The record's own readings agree word for word.
THE CHANGE: class_84(spoken, approved, approved_tokens=None). Given approved_tokens, it compares canon_tokens(spoken)
against those tokens AS THEY ARE (the same SequenceMatcher opcodes diff() makes); approved stays the text the critical-
word test reads (texts = (spoken, approved), unchanged). class_131 passes merged as approved_tokens. Every other caller
passes none: unchanged.
TESTS (tests/package/test_lock_precheck.py, TestRuling148TheMergedReadingKeepsItsTokens): the render lock's record of
f0a51c45 (its three readings and two pairs, verbatim) -> class_131 holds nothing and LP.decide adopts under ruling 131
(A); a real number difference (366 for 365, 25 for 24) still holds; class_84 with tokens reads them as they are, and
the join re-read shows the defect. Mutations: 2 of 2 killed (the old join-only call; class_84 ignoring the tokens);
control passes; suites 42 files / 938 passed, exit 0.
PLEASE CHECK: (1) can approved_tokens let a genuine number / name / negation difference through? (2) is the merged
reading's critical-word test (texts) still the same as before? (3) anything else this changes.


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
