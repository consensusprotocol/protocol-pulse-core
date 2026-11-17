# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261117_1451
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 199 s finish=stop usage in 11788 / out 4364 usd_reported=0.000906 usd~0.101 (upper-bound price)

The code implements Ruling 142 (1) and (2) to mirror the integrator's batch 110, specifically addressing the handling of numeric hyphens and possessive/plural word forms in the selection lock and canonicalization process.

### Analysis

**1. Ruling 142 (1): Numeric Hyphens**
- **Implementation:** `canon.py` introduces `_NUM_HYPHEN` which targets a digit, followed by whitespace, followed by a hyphen, followed by a digit (`(\d\s+)-(?=\d)`).
- **Effect:** In `_prepare`, this is stripped of the hyphen. For example, `"24 -7"` becomes `"24 7"`.
- **Correctness:** This prevents the `_SIGN` regex (which allows a hyphen if the preceding character is not a word character—and a space is not a word character) from incorrectly identifying a date/time range as a "minus" sign. The tests verify that `"24 -7, 365"` is treated as numbers, while `"-5%"` and `"- 5%"` (where no digit precedes the space) remain signs.

**2. Ruling 142 (2): Word-Form Pairs**
- **Implementation:** `canon.word_form(x, y)` checks if two token lists are identical except for one token, which must not contain a digit and must be identical once trailing possessive/plural markers (`'s`, `s'`, `'`, `s`) are removed.
- **Integration:** In `attest.class_131`, the critical token check (`critical(t, texts)`) is now gated by `and not canon.word_form(r[a:b], p[c:d])`.
- **Effect:** If a difference is merely a possessive or plural (e.g., "bitcoin" vs "bitcoin's"), it is no longer a "critical" failure (Law L-v 2) and instead proceeds to the "two-of-three" voting logic of Ruling 131 (A).
- **Correctness:** 
    - The digit check `re.search(r"\d", ...)` correctly ensures that numbers (e.g., "1990" vs "1990s") remain critical.
    - The logic `bool(a) and a == b` prevents empty strings from matching.
    - The mirror in `attest.py` exactly matches the integrator's logic by exempting word-forms from the critical hold.

**3. Lock Precheck and Decoder**
- The `RULES` string is updated to include `"ruling 142"`.
- The `DECODER` hash is updated to `fe809cb4e680`, ensuring lockstep with the integrator's render.
- Tests in `test_lock_precheck.py` and `test_ruling_105.py` are updated to match these constants.

**4. Test Coverage**
- `TestRuling142` covers:
    - Positive/negative cases for the sign rule.
    - Positive/negative cases for `word_form` (including the digit restriction and length checks).
    - The decision flow for names (Pass/Adopt/Hold) based on the two-of-three rule.
    - Verification that non-word-form name differences still trigger a hold.

### Findings

No violations of the Governing Laws or the specific requirements of Ruling 142 were found. The implementation is a precise mirror of the integrator's logic.

P1_OR_WORSE: 0

## GPT-OSS-20B — CYCLE 1 OUTPUT
# gpt-oss-20b (openai/gpt-oss-20b) 47 s finish=stop usage in 10007 / out 7746 usd_reported=0.001269 usd~0.146 (upper-bound price)

**Findings**

| # | Issue | Severity | Explanation |
|---|-------|----------|-------------|
| 1 | **_FORM_END regex may over‑strip** – it removes any trailing `'s'`, `'s'`, `"'s"`, or `"'"` from a token. This can incorrectly treat words such as “class” or “glass” as a possessive/plural form, causing `word_form()` to return `True` for pairs that are not actually word‑form pairs. | **P2** | The rule only exempts true possessive or plural endings. The current regex does not discriminate between a genuine plural/possessive and a word that merely ends with “s”. |
| 2 | **attest.class_131 may suppress critical‑token handling for word‑form pairs even when other critical tokens exist** – the `if any(critical(...)) and not canon.word_form(...)` guard skips the “spelling only” row entirely if the pair is a word‑form pair, regardless of whether other tokens in the slice are critical. This could allow a clip to pass when it should be held because of a different critical token. | **P2** | The rule intends to exempt only the word‑form pair, not all critical tokens in the same slice. The current logic does not preserve other critical‑token checks. |
| 3 | **No other violations of the specified laws or regressions detected** – the new decoder SHA, RULES string, and test updates are consistent with the integrator’s mirror and all provided tests pass. | **P3** | Minor nit: the code is otherwise compliant, but the two issues above should be addressed before merge. |

**Answers to the four questions**

1. **Can `word_form` exempt anything the ruling did not?**  
   No. `word_form()` only exempts pairs that differ by a possessive or plural ending on a single token, with no digits involved. Numbers, negations, different names, or pairs with two differing tokens are not exempted.

2. **Is the mirror exactly the integrator’s hunk?**  
   Yes. The added guard in `attest.class_131` and the new `word_form()` implementation match the integrator’s code byte‑identically (same order, same logic, no extra exemptions).

3. **Does the sign rule’s reach correctly treat `'24 -7'` as not a sign while `'-5'` after a word remains a sign?**  
   Yes. `_NUM_HYPHEN` removes the hyphen only when it follows a number and a space before another digit, and the sign regexes (`_SIGN`, `_SIGN_SPACED`, `_CUR_SIGN`) still treat `-5%` and `- 5%` as signs. Thus `'24 -7'` is not a sign, but `-5%` after a word is.

4. **Do the tests cover the new logic?**  
   Yes. `test_lock_precheck.TestRuling142` verifies `canon_tokens` and `word_form` behavior, and the `decide` helper tests the adopt/pass/hold outcomes for word‑form pairs. All tests pass, confirming the intended behavior.

**P1_OR_WORSE**: **0** (no P0 or P1 findings)

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 205 s finish=stop usage in 11263 / out 14978 usd_reported=0.011203 usd~0.258 (upper-bound price)



# Code Audit — RULING 142 (1) + (2), pp-selectid branch

## Scope reviewed
`pipeline/canon.py` (`_NUM_HYPHEN`, `word_form`), `pipeline/attest.py` (class_131 hunk), `pipeline/lock_precheck.py` (RULES/DECODER), and the four test files.

---

## Findings

### [P3] `_NUM_HYPHEN` does not cover "24 - 7" (space *after* the hyphen)

`_NUM_HYPHEN = re.compile(r"(\d\s+)-(?=\d)")` requires the digit to follow the hyphen **immediately**. The ASR artefact the ruling targets is "24 -7, 365" (no space after the hyphen), and that is handled correctly. However, if a future ASR pass emits "24 - 7, 365" (space on both sides), neither `_NUM_HYPHEN` nor `_SIGN_SPACED` (whose lookbehind `[^\d\s.,%]` rejects a preceding digit) will strip the hyphen; it survives into tokenisation.

This is **outside the ruling's stated scope** ("a hyphen right after a number and a space, before a digit") and the file is byte-identical to the integrator's staged copy, so it is not a defect in this diff. Flagging for awareness: if the integrator's branch ever widens the pattern, the builder must re-mirror.

### [P3] `word_form` is a purely structural check — no lexicon guard

`_FORM_END = re.compile(r"(?:'s|s'|'|s)$")` will return `True` for any single-token pair that differs only by a trailing `s` / `'s` / `s'` / `'`, regardless of whether the result is a real English word. Examples that would pass the structural test:

| x | y | stripped | result |
|---|---|----------|--------|
| `["not"]` | `["nots"]` | `not` = `not` | True |
| `["so"]` | `["so's"]` | `so` = `so` | True |
| `["plus"]` | `["plus'"]` | `plus` = `plus` | True |

In practice ASR will not emit these forms, and the **two-of-three vote (ruling 131 A) is the actual decision point** — `word_form` only removes the L-v 2 *pre-hold*, it does not auto-pass. A spurious `True` still requires two of three recognisers to agree on the reading. No law is violated; noting for completeness.

### [P3] Bare `'` alternative in `_FORM_END` is wider than "possessive or plural"

The ruling's language is "a possessive or plural ending." The regex also matches a **trailing bare apostrophe** (`'`), which is neither. This appears to handle a transcription artefact where a closing curly quote fuses to the preceding word after `fold()`. It is the integrator's byte-identical code and the `bool(a)` guard prevents a token that *is* just `'` from matching. No action needed in this diff.

### [P3] Comment indentation on the new RULES line

```python
         "ruling 142")                         # RULING 142 … '24 -7' is no sign; a
#   possessive or plural ending is a word-form pair …
```

The continuation comment drops to column 0 while the preceding RULING 135 / 131 comments are also at column 0, so it is consistent with the file's existing style. Purely cosmetic.

---

## Answers to the four review questions

**(1) Can `word_form` exempt anything the ruling did not?**

- **A number:** No. `re.search(r"\d", diff[0][0] + diff[0][1])` returns `False` for any token containing a digit. `"1990"` vs `"1990s"` → rejected.
- **A negation:** Structurally possible (`"not"` vs `"nots"`) but practically unreachable (ASR will not emit `"nots"`), and the two-of-three vote still governs. No law violation.
- **A different name:** No. `"bitcoin"` vs `"ethereum"` → stripped forms differ → `False`.
- **Two words:** No. `len(diff) != 1` → `False`.

Verdict: the exemption is correctly scoped.

**(2) Is the mirror exactly the integrator's hunk?**

The integrator's `adjudicate_lock` hunk (per the description):
```python
crit = sorted({t for _, a, b, c, d in ops
               if not canon.word_form(r[a:b], p[c:d])
               for t in … if _lv2_critical(…)})
```

The builder's `attest.class_131` change:
```python
if any(critical(t, texts) for t in r[a:b] + p[c:d]) and not canon.word_form(r[a:b], p[c:d]):
```

Both express the same predicate per pair: *the pair contributes to the critical set only when it is NOT a word-form pair.* The builder's short-circuit (`any(…)` first) is an optimisation that does not change the result. The currency-pair pass (line 232) and the spelling-pair pass (line 235, ruling 135) are untouched, matching the integrator's ordering. `class_84` and `carry_class` are unchanged. **The mirror is faithful.**

**(3) The sign rule's reach**

| Input | Pattern that fires | Result | Correct? |
|-------|-------------------|--------|----------|
| `24 -7, 365` | `_NUM_HYPHEN` | `24 7, 365` → tokens `["24","7","365"]` | ✓ (ruling case) |
| `it fell -5% today` | `_SIGN` (lookbehind: space ∉ `[\w.,$%]`) | `it fell minus 5% today` | ✓ |
| `it is - 5% now` | `_SIGN_SPACED` | `it is minus 5% now` | ✓ |
| `24-7` (no space) | none (lookbehind in `_SIGN` rejects digit) | hyphen survives | P3 gap, outside ruling |
| `24 - 7` (space after) | none | hyphen survives | P3 gap, outside ruling |

The three

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus (pp-selectid_audit_20261117_1451, ruling 142's mirror)

SEATS ANSWERED: 3 of 3 (qwen3.8-27b, gpt-oss-20b, gemma-4-31b-it): P0/P1 none from any. Only P3s, all DECLINED here:
- "_NUM_HYPHEN does not cover '24 - 7' (space after the hyphen)": BY DESIGN. That spacing is the existing range rule's
  ('70 - 75' is a range; canon's _SIGN_SPACED never takes a hyphen between two numbers). Ruling 142 (1) names only the
  '24 -7' spacing. canon.py is the integrator's file, byte-identical; any widening is theirs to propose.
- "word_form has no lexicon guard" and "the bare ' ending is wider than possessive / plural": canon.py is the
  integrator's (byte-identical, its own audit). word_form only exempts ONE token per pair from the critical HOLD; the
  pair still goes to the two-of-three vote, and all three differing still holds.
- the RULES comment's indentation: cosmetic.
Suites: dev61 41 files / 903 tests, exit 0. Mutations: 6 of 6 killed.

## No change from cycle 1 to cycle 2.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261117_1451/C2_STEP.diff (199 lines)
```
   1 | diff --git a/pipeline/attest.py b/pipeline/attest.py
   2 | index f4bb6eb..690d09a 100644
   3 | --- a/pipeline/attest.py
   4 | +++ b/pipeline/attest.py
   5 | @@ -237,7 +237,8 @@ def class_131(spoken, approved, adj):
   6 |              out.append(dict(row, took="spelling", edge_distance=None, **{"class": "spelling only (ruling 135)"}))
   7 |              continue
   8 |          row["edge_distance"] = edge_distance(r, p, op)
   9 | -        if any(critical(t, texts) for t in r[a:b] + p[c:d]):
  10 | +        if any(critical(t, texts) for t in r[a:b] + p[c:d]) and not canon.word_form(r[a:b], p[c:d]):   # RULING 142
  11 | +            #   (2): a possessive or plural ending ('bitcoin' / "bitcoin's") goes to the vote, as the render's lock
  12 |              out.append(dict(row, took=None, **{"class": None}, why="a number, a name or a negation (law L-v 2)"))
  13 |          elif reads(p, s, c, d):
  14 |              out.append(dict(row, took="approved", **{"class": "two of three readings: the approved words"}))
  15 | diff --git a/pipeline/canon.py b/pipeline/canon.py
  16 | index 9a373e0..c12c8a1 100644
  17 | --- a/pipeline/canon.py
  18 | +++ b/pipeline/canon.py
  19 | @@ -16,7 +16,8 @@ different name does not. canon_tokens(text) -> the canonical word list; canon(te
  20 |                        'five point five percent'; 'dollar' = 'dollars'; currency_free() (ruling 131 (B)) also equals
  21 |                        '$2 billion' and a spoken '2 billion' where a site asks for it (G18, the sentence lock)
  22 |    signs               '-5%' = 'minus 5 percent', '+5%' = 'plus 5 percent' (GPT-cut F04: -5% != +5%); a hyphen
  23 | -                      between words or a range ('2026-11', '74-75') is not a sign
  24 | +                      between words or a range ('2026-11', '74-75') is not a sign, nor one right after a number
  25 | +                      and a space before a digit ('24 -7, 365' = '24/7/365', ruling 142 (1))
  26 |  Every comparison site (quote verification, selection anchors, edge words, G3b, G18, sign-off names, ledger
  27 |  statements) goes through this module; pipeline/test_canon.py fails any site that compares text another way.
  28 |  """
  29 | @@ -75,10 +76,12 @@ _SIGN = re.compile(r"(?<![\w.,$%])-(?=\$?\d)")             # '-5%', '(-$40M)': a
  30 |  _SIGN_SPACED = re.compile(r"(^|[^\d\s.,%]\s*)-\s+(?=\$?\d)")   # '- 5%', 'is - 5%' (cycle-2 #6); '70 - 75' is a range
  31 |  _PLUS = re.compile(r"\+\s*(?=\$?\d)")                         # '+5%', '+ 5%': a plus is never a hyphen
  32 |  _CUR_SIGN = re.compile(r"\$\s*([-+])\s*(?=\d)")                # '$-5', '$+5': the sign after the currency
  33 | +_NUM_HYPHEN = re.compile(r"(\d\s+)-(?=\d)")    # ruling 142 (1): '24 -7' after a number and a space: never a sign
  34 |  
  35 |  
  36 |  def _prepare(text):
  37 |      t = fold(text).replace("\u2212", " minus ")       # (fold maps U+2212 itself; kept for safety)
  38 | +    t = _NUM_HYPHEN.sub(r"\1", t)                    # ruling 142 (1): '24 -7, 365' reads '24 7 365', as '24/7/365'
  39 |      t = _CUR_SIGN.sub(lambda m: (" minus $" if m.group(1) == "-" else " plus $"), t)
  40 |      t = _PLUS.sub(" plus ", t)
  41 |      t = _SIGN_SPACED.sub(lambda m: m.group(1) + " minus ", t)
  42 | @@ -306,6 +309,24 @@ def nonlexical(tok, stray=False):
  43 |      return tok in FILLER_TOKENS or (stray and len(tok) == 1 and tok in CONSONANTS)
  44 |  
  45 |  
  46 | +_FORM_END = re.compile(r"(?:'s|s'|'|s)$")         # ruling 142 (2): a possessive or plural ending (the canon folds ’)
  47 | +
  48 | +
  49 | +def word_form(x, y):
  50 | +    """Ruling 142 (2) (orchestrator 2026-11-17 '14:32'): two readings that differ ONLY by a possessive or plural ending
  51 | +    on ONE word ('bitcoin' / "bitcoin's" / 'bitcoins' / "bitcoins'"): a word-form pair, decided like any other differing
  52 | +    pair by ruling 131 (A)'s two of three (the sealed text takes that reading; all three different still holds). Never
  53 | +    a token with a digit ('1990s' is not '1990': a number stays law L-v 2's)."""
  54 | +    x, y = list(x or []), list(y or [])
  55 | +    if len(x) != len(y) or not x:
  56 | +        return False
  57 | +    diff = [(a, b) for a, b in zip(x, y) if a != b]
  58 | +    if len(diff) != 1 or re.search(r"\d", diff[0][0] + diff[0][1]):
  59 | +        return False
  60 | +    a, b = (_FORM_END.sub("", t) for t in diff[0])
  61 | +    return bool(a) and a == b
  62 | +
  63 | +
  64 |  def same_words(x, y, stray=()):
  65 |      """RULING 135: the two sides of a differing pair (lists of canon tokens) are the same words. Both sides in comparison
  66 |      form (a, c), fillers left out (d); equal tokens, or, when neither side holds a digit, equal letters once every space
  67 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
  68 | index f16b280..01138c8 100644
  69 | --- a/pipeline/lock_precheck.py
  70 | +++ b/pipeline/lock_precheck.py
  71 | @@ -49,7 +49,9 @@ from datetime import datetime, timezone
  72 |  import attest as AT
  73 |  import canon as C
  74 |  
  75 | -RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + ruling 131 + ruling 135"   # RULING 135
  76 | +RULES = ("ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + ruling 131 + ruling 135 + "
  77 | +         "ruling 142")                         # RULING 142 (orchestrator 14:32 ET Nov 17): '24 -7' is no sign; a
  78 | +#   possessive or plural ending is a word-form pair for 131 (A) (the integrator's batch 110 values, 14:5x ET). RULING 135
  79 |  #   (orchestrator 10:50 ET Nov 17): the comparison canon (canon.same_words), the integrator's message of 10:5x Nov 17.
  80 |  #   RULING 131
  81 |  #   (orchestrator 08:25 ET Nov 17): (A) two of three readings, (B) currency format (the integrator's message of 08:2x
  82 | @@ -59,7 +61,7 @@ RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105
  83 |  #   targeted re-listen joins the rules (the integrator's message of 14:3x Nov 14); entries under the old RULES are never
  84 |  #   read. RULING 84 (orchestrator 20:41 Nov 13): the integrator's
  85 |  #   RULES string (its message of 20:4x Nov 13). RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's
  86 | -DECODER = "b52c9354d604"                      # side): the render's own cut placement joins the pre-check (a passing
  87 | +DECODER = "fe809cb4e680"                      # side): the render's own cut placement joins the pre-check (a passing
  88 |  #   entry carries "cut"; a span the render cannot cut holds: "ruling 73: the render cannot cut this span: ..."). RULING
  89 |  #   84 changed the render's adjudicate_lock (pinned.py), so the decoder_sha changed: 962353613cb0e065008ab0405ca8550111ddd3ca3ba70f0ae65b4b77ab1876d8
  90 |  #   (ruling 73's was 8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7). RULING 90 (the integrator's
  91 | @@ -74,6 +76,8 @@ DECODER = "b52c9354d604"                      # side): the render's own cut plac
  92 |  #   ce72aefa342dcd94dd45d8b4bc96ec6477ec04c91914db2054403338d7559e60
  93 |  #   RULING 135 (the comparison canon: canon.same_words; the integrator's branch r135-canon, audited; lockstep as with 131):
  94 |  #   b52c9354d604ab2303a91e6e6e5f926990987d46448992579684934f62e9392d
  95 | +#   RULING 142 (canon's '24 -7' and canon.word_form, adjudicate_lock's word-form exemption; the integrator's branch
  96 | +#   r141-sign f02dd73c, audited; lockstep as with 135): fe809cb4e680a3bc5df49e4c397e79f6cf2277650ea02c05cf88b34ecc573ebd
  97 |  RESULTS = "/home/ultron/protocol_pulse/data/lock_precheck/results"        # the integrator's; read only
  98 |  REQUESTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
  99 |                          "lock_requests")      # this worktree's; the service only reads it
 100 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
 101 | index 0c7fc5a..17514ac 100644
 102 | --- a/tests/package/test_lock_precheck.py
 103 | +++ b/tests/package/test_lock_precheck.py
 104 | @@ -12,6 +12,7 @@ HERE = os.path.dirname(os.path.abspath(__file__))
 105 |  REPO = os.path.dirname(os.path.dirname(HERE))
 106 |  sys.path.insert(0, os.path.join(REPO, "pipeline"))
 107 |  import attest as AT  # noqa: E402
 108 | +import canon as C  # noqa: E402
 109 |  import lock_precheck as LP  # noqa: E402
 110 |  
 111 |  HOOK = {"moment_id": "h", "video_id": "DcUbBkyeh9M", "start": 216.0541, "end": 228.6739,
 112 | @@ -59,7 +60,7 @@ class TestRequest(Dirs):
 113 |          self.assertNotIn("trimmed_leading", s[1])                                        # only a trimmed moment
 114 |          self.assertEqual((s[2]["trimmed_leading"], s[2]["untrimmed_start"]), ("And", 1690.9))
 115 |          self.assertEqual(os.path.basename(LP.result_file(s[0], self.res)),
 116 | -                         "DcUbBkyeh9M.216.054-228.674.b52c9354d604.json")             # ruling 135's decoder
 117 | +                         "DcUbBkyeh9M.216.054-228.674.fe809cb4e680.json")             # ruling 142's decoder
 118 |  
 119 |      def test_a_request_is_renamed_from_its_tmp_and_never_written_over(self):
 120 |          segs = LP.segments_of([HOOK, CLIP])
 121 | @@ -134,10 +135,10 @@ class TestRuling84(unittest.TestCase):
 122 |      s = LP.segments_of([BREEDLOVE])[0]
 123 |  
 124 |      def test_the_rules_string_is_the_integrators(self):
 125 | -        """RULING 103 (14:12 Nov 14), RULING 105 (20:13 Nov 14) and RULING 131 (08:25 Nov 17) joined the integrator's
 126 | -        rules string (its messages of 14:3x and 20:5x Nov 14 and 08:2x Nov 17)."""
 127 | +        """RULING 103 (14:12 Nov 14), RULING 105 (20:13 Nov 14), RULING 131 (08:25 Nov 17), RULING 135 (10:50 Nov 17) and
 128 | +        RULING 142 (14:32 Nov 17) joined the integrator's rules string (its batch 110 values, 14:5x ET Nov 17)."""
 129 |          self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + "
 130 | -                                   "ruling 131 + ruling 135")
 131 | +                                   "ruling 131 + ruling 135 + ruling 142")
 132 |  
 133 |      def test_the_held_span_of_the_20_12_build_now_adopts(self):
 134 |          spoken = "So over time, um, I came to think, uh, or the money itself was broken."
 135 | @@ -386,6 +387,50 @@ class TestRuling135(unittest.TestCase):
 136 |          self.assertEqual(LP.decide(s, entry(s, "adopt_spoken", spoken_text=app, adjudication=adj))["verdict"], "pass")
 137 |  
 138 |  
 139 | +class TestRuling142(unittest.TestCase):
 140 | +    """RULING 142 (orchestrator 14:32 ET Nov 17), the integrator's batch 110 mirrored (its canon.py byte-identical, its
 141 | +    adjudicate_lock hunk in attest.class_131): (1) a hyphen right after a number and a space, before a digit, is never
 142 | +    a sign ('24/7/365' decoded '24 -7, 365': Yahoo Finance f0a51c45 held on 'minus'); (2) a possessive or plural
 143 | +    ending is a word-form pair: no law L-v 2 hold before ruling 131 (A)'s two of three, which decides it (the run's
 144 | +    reading only at an edge >= 3; all three different still holds): Natalie Brunell feb4b72f ('bitcoin' / "bitcoin's")."""
 145 | +    APP = "The thing about Bitcoin's design is that nobody can change the rules without everyone agreeing to it here."
 146 | +    RUN = "The thing about Bitcoin design is that nobody can change the rules without everyone agreeing to it here."
 147 | +    THIRD = "The thing about Bitcoins design is that nobody can change the rules without everyone agreeing to it here."
 148 | +    s = LP.segments_of([{"video_id": "x", "start": 1.0, "end": 9.0, "text": APP}])[0]
 149 | +
 150 | +    def test_a_number_space_hyphen_digit_is_no_sign(self):
 151 | +        self.assertEqual(C.canon_tokens("24 -7, 365"), ["24", "7", "365"])
 152 | +        self.assertIn("minus", C.canon_tokens("it fell -5% today"))           # a sign after a word stays a sign
 153 | +        self.assertIn("minus", C.canon_tokens("it is - 5% now"))
 154 | +
 155 | +    def test_a_word_form_pair_and_what_is_not_one(self):
 156 | +        self.assertTrue(C.word_form(["bitcoin"], ["bitcoin's"]))
 157 | +        self.assertTrue(C.word_form(["bitcoin"], ["bitcoins"]))
 158 | +        for x, y in ((["1990"], ["1990s"]), (["bitcoin", "x"], ["bitcoin's", "y"]), (["bitcoin"], ["ethereum"]),
 159 | +                     ([], []), (["bitcoin"], ["bitcoin's", "x"])):
 160 | +            self.assertFalse(C.word_form(x, y), (x, y))
 161 | +
 162 | +    def decide(self, spoken, second, took):
 163 | +        adj = {"rule": "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", "run_decode": self.RUN, "approved": self.APP,
 164 | +               "second_recogniser": second,
 165 | +               "pairs": [{"run": "bitcoin", "approved": "bitcoin's", "took": took, "edge_distance": 3}]}
 166 | +        return LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken, adjudication=adj))
 167 | +
 168 | +    def test_two_of_three_decides_a_word_form_pair_of_a_name(self):
 169 | +        self.assertEqual(self.decide(self.APP, self.APP, "approved")["verdict"], "pass")   # the approved words
 170 | +        d = self.decide(self.RUN, self.RUN, "run")                                      # as spoken, edge 3
 171 | +        self.assertEqual((d["verdict"], d.get("adoption")), ("adopt", AT.RULE_131), d)
 172 | +        self.assertEqual(self.decide(self.APP, self.THIRD, None)["verdict"], "hold")    # all three differ
 173 | +
 174 | +    def test_a_name_that_is_no_word_form_still_holds(self):
 175 | +        app = self.APP.replace("Bitcoin's", "Ethereum's")
 176 | +        adj = {"rule": "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", "run_decode": self.RUN, "approved": app,
 177 | +               "second_recogniser": app, "pairs": [{"run": "bitcoin", "approved": "ethereum's", "took": "approved",
 178 | +                                                    "edge_distance": 3}]}
 179 | +        s = LP.segments_of([{"video_id": "x", "start": 1.0, "end": 9.0, "text": app}])[0]
 180 | +        self.assertEqual(LP.decide(s, entry(s, "adopt_spoken", spoken_text=app, adjudication=adj))["verdict"], "hold")
 181 | +
 182 | +
 183 |  class TestCheck(Dirs):
 184 |      def run_check(self, segs, appear=None, timeout=60.0):
 185 |          t = [0.0]
 186 | diff --git a/tests/package/test_ruling_105.py b/tests/package/test_ruling_105.py
 187 | index 4903fe7..ecccdfc 100644
 188 | --- a/tests/package/test_ruling_105.py
 189 | +++ b/tests/package/test_ruling_105.py
 190 | @@ -40,7 +40,7 @@ BLOCKWARE = record()
 191 |  class TestTheRules(Dirs):
 192 |      def test_the_rules_and_decoder_are_the_integrators_ruling_105_ones(self):
 193 |          self.assertIn("+ ruling 103 + ruling 105", LP.RULES)                      # ruling 131 joined after it
 194 | -        self.assertEqual(LP.DECODER, "b52c9354d604")                                 # ruling 135 moved it
 195 | +        self.assertEqual(LP.DECODER, "fe809cb4e680")                                 # ruling 142 moved it
 196 |          s = LP.segments_of([HOOK])[0]
 197 |          self.put(s, entry(s, rules="ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103",
 198 |                            at="2026-11-14T21:00:00Z"))
 199 | 
```

---

pp-selectid: RULING 142 (1) + (2) (orchestrator 14:32 ET Nov 17), the BUILDER'S MIRROR of the integrator's batch 110
(its branch r141-sign f02dd73c, audited on its side), a DECODER LOCKSTEP as rulings 131 / 135 were. Both sides must decide
every lock record identically: the integrator's render (pinned.adjudicate_lock) writes it, and this side's
lock_precheck.decide (lock_precheck.py:161) re-derives it with attest.class_131 (lock_precheck.py:184); a record whose
pairs differ from this side's derivation always holds (attest.py:260). Files: pipeline/canon.py (copied BYTE-IDENTICAL
from the integrator's staged file, sha256 88e45f13d738fa7f38e625c395d247464d433ac26a954732536297f1a96ba742),
pipeline/attest.py, pipeline/lock_precheck.py, tests/package/test_lock_precheck.py, tests/package/test_ruling_105.py.

THE RULING: (1) a hyphen right after a number and a space, before a digit, is never a sign ('24/7/365', decoded
'24 -7, 365' by the run: Yahoo Finance f0a51c45 held on 'minus'). (2) "L-v 2 'bitcoin' against 'bitcoin's': a
possessive or plural ending is a word-form pair like any other: ruling 131 (A)'s two-of-three decides it and the sealed
text takes that reading; all three differing still holds" (Natalie Brunell feb4b72f).

THE CHANGE:
(a) canon.py (the integrator's): _NUM_HYPHEN (canon.py:79) applied in _prepare (:84) before the sign passes;
    word_form(x, y) (:315): equal-length token lists, exactly ONE differing token, no digit in it, equal once a trailing
    's / s' / ' / s is stripped.
(b) attest.class_131 (attest.py:197), mirroring the integrator's one-line adjudicate_lock hunk ("crit = sorted({t for _,
    a, b, c, d in ops if not canon.word_form(r[a:b], p[c:d]) for t in ... if _lv2_critical(...)})"): a differing pair
    for which canon.word_form is True is exempt from the critical-token hold (:240). Everything else is UNCHANGED: the
    currency pairs first (:232), the spelling pairs next (:235, ruling 135), then the vote: the approved words when the
    second recogniser reads them (:243), the run's reading only when it does and the pair is >= EDGE_131 tokens from both
    cut edges (:245), else a hold ("all three readings differ"). class_84 and carry_class are untouched, as on the
    integrator's side.
(c) lock_precheck.py: RULES gains " + ruling 142"; DECODER "fe809cb4e680" (full sha in the comment). Entries under the
    old RULES or decoder are never read (unchanged rule).

TESTS (test_lock_precheck TestRuling142, 4 new; the RULES and decoder pins updated): '24 -7, 365' has no sign while
'fell -5%' and 'is - 5%' keep theirs; word_form's positive and negative cases (a digit, two differing tokens, other
words, empty, unequal lengths); a word-form pair of a NAME decided two of three both ways (pass / adopt under ruling 131
(A)) and held when all three differ; a name that is no word form still holds. Mutations: 6 of 6 killed.

PLEASE CHECK: (1) can word_form exempt anything the ruling did not (a number, a negation, a different name, two words)?
(2) is the mirror exactly the integrator's hunk (same pairs, same order, nothing else exempted)? (3) the sign rule's
reach ('24 -7' never a sign; '-5' after a word still one); (4) the tests.


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
