# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0728
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 69 s finish=stop usage in 5595 / out 1914 usd~0.045 (upper-bound price)

# Audit: pp-selectid — "exactly ONE canonical token" tightening

## What the diff does (verified from the diff)

Both production sites change the acceptance predicate identically:

- **package.py:689-690 (diff lines 9-12)** — old: `tok = canon.canon_tokens(word)[:1]` then `if w1 <= w0 or not tok or tok[0] not in TRIM_WORDS`. New: `tok = canon.canon_tokens(word)` then `if w1 <= w0 or len(tok) != 1 or tok[0] not in TRIM_WORDS`.
- **package_pin.py:128-129 (diff lines 24-29)** — same predicate change on `w` (guarded by `isinstance(w, str)`), plus the message now reads "must be ONE word, one of ...".

Both now match the render's `validate_schema` shape quoted in the brief: `len(tok) != 1 or tok[0] not in TRIMMABLE_LEADING → refuse`. The predicates are structurally identical (tokenize, require exactly one, require membership).

## P0 findings

None.

## P1 findings

None.

## P2 findings

**P2-1 — package.py:689 (diff line 11): the `[:1]`-to-`len!=1` change also silently changes behavior for the *empty/None* case, and the comment claims a guarantee the diff doesn't prove.** Old code: `not tok` caught the empty list. New code: `len(tok) != 1` catches empty, 2+, and — importantly — the case where `canon_tokens` returns more than one token for what looks like one word. That's the intended tightening, but note the diff relies on an unstated assumption: that `canon.canon_tokens` is total (never raises) on any string reaching these lines. In package.py, `word` comes from `toks[w0].get("word") or ""` — the `or ""` guarantees a str, so `canon_tokens("")` must return `[]` for the new predicate to behave like the old one on the empty path. If `canon_tokens("")` ever raised, the old code would have raised too (same call), so this is *not* a regression — but the diff's correctness for the empty-string path (`""` → `[]` → `len != 1` → `return None`) is asserted, not tested: the new test case list (test_medley.py:806-809, diff lines 39-42) adds "And/or" (2 tokens) but no empty-string or punctuation-only case (e.g. `"But,"` → `['but']`, which the brief says must still pass). **Concrete scenario:** if `canon_tokens` stripped punctuation to nothing for a punctuation-only trimmed_leading like `","`, the pin would now be refused where the render (same predicate) would also refuse it — consistent, so not a bug, but the "punctuation allowed as canon strips it" claim in the task is untested in this diff. Severity: P2 (consistency holds either way because both sides use the same function; only test coverage is thin).

**P2-2 — package_pin.py:129 (diff line 28): the `isinstance(w, str)` guard placement means a non-str `trimmed_leading` now produces a different (but still failing) reason, and the error message interpolates `w!r` — fine — but the *new* message text is a seal-relevant change.** `trim_problems` output feeds `package_pin.seal` (the diff's own test at test_medley.py:868-871, diff lines 46-54, asserts seal changes when segment fields change). If any stored/attested artifact (e.g. a pinned package's problem list, or a golden test) compares `trim_problems` strings, the wording change "is not one of" → "must be ONE word, one of" will break it. The diff updates the seal test's *inputs* (adds `{"trimmed_leading": "But so"}` and `{"trimmed_leading": "and/or"}`) but I cannot verify from the diff whether any other test or fixture pins the old message text. **Flag: verify no golden/attestation fixture asserts the old `trim_problems` reason strings.** Severity: P2 (test-only breakage if it exists; the diff author reports all suites OK, which suggests none, but that's their report, not the diff).

**P2-3 — test_medley.py:806 (diff line 41): the "And/or" case tests `trim_variant` returns None, but the brief's measured facts say `canon_tokens("and/or") == ['and', 'or']` — two tokens — so this exercises the `len != 1` branch. Good. However the *pin-side* counterpart for "and/or" is only tested via the `bad`-tuple loop (diff line 50), which asserts seal-inequality, not that `trim_problems` reports the ONE-word reason.** The new reason text ("must be ONE word") is therefore never asserted anywhere in the diff. If the message wording matters downstream (see P2-2), nothing catches a regression to the old wording. Severity: P2.

## Equivalence check: nothing valid-at-render now refused

Old acceptance: `tok[:1]` non-empty and `tok[0] in TRIM_WORDS`. New: `len(tok) == 1` and `tok[0] in TRIM_WORDS`.

- Anything with exactly one canonical token: accepted by both. ✔ (includes "But," → ['but'], since canon strips punctuation — per the brief's measured facts; the *code* doesn't need to handle it, canon does.)
- Anything with ≥2 tokens, first in TRIM_WORDS (e.g. "But so", "and/or"): accepted before, refused now. This is the intended tightening, and the brief confirms the render already refused these — so these are *not* valid-at-render losses. 

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 20 s finish=stop usage in 5713 / out 180 usd~0.033 (upper-bound price)

**P0: None**  
**P1: None**  
**P2: None** (verified from diff only)  

The diff tightens `trim_variant` (package.py:11) and `trim_problems` (package_pin.py:27) from `[:1]` to `len(tok) != 1`, exactly matching the render's `validate_schema` requirement of one canonical token. Updated test cases (test_medley.py:41, :50) now cover the newly-rejected multi-token strings "And/or", "But so", "and/or" while preserving the prior expectations for single-token TRIM_WORDS cases (e.g. "But", "Because"). Short-circuit `or` evaluation prevents index errors on len==0. No previously-valid single-token case is refused; no other logic, paths, or constants are altered.  

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 24 s finish=stop usage in 5989 / out 802 usd~0.030 (upper-bound price)

# Audit: pp-selectid C1_STEP.diff

## Verification of the core change

The diff tightens two checks from "first canonical token is in TRIM_WORDS" to "exactly one canonical token, and it is in TRIM_WORDS." This aligns the branch's `trim_variant` (package.py) and `trim_problems` (package_pin.py) with the integrator's `pinned.validate_schema`, which requires `len(tok) != 1 or tok[0] not in L.TRIMMABLE_LEADING` to refuse.

**Does it accept exactly what the render accepts?**
- Render accepts: `len(canon.canon_tokens(tl)) == 1` AND `tok[0] in TRIMMABLE_LEADING`.
- Branch now accepts: `len(canon.canon_tokens(w)) == 1` AND `tok[0] in TRIM_WORDS`.
- These are structurally identical (assuming `TRIM_WORDS == TRIMMABLE_LEADING`, which the background confirms: "the six words"). Punctuation is stripped by `canon.canon_tokens` (e.g., `"But,"` → `['but']`), so a single word with trailing punctuation still yields one token and passes. **Match confirmed.**

**Does it refuse anything that was valid at the render?**
- Previously valid at render = exactly one canonical token in the six words. The new branch check accepts exactly that set. Nothing valid at the render is newly refused. **Confirmed.**

**Does it now refuse things that previously passed the branch but were invalid at the render?**
- `"But so"` → `['but', 'so']` (2 tokens): previously passed branch (`[:1]` → `['but']`), now refused. Render would have refused it. **Correctly closed.**
- `"and/or"` → `['and', 'or']` (2 tokens): same. **Correctly closed.**
- `"Because"` → `['because']` (1 token, not in TRIM_WORDS): refused both before and after. Unchanged. **Correct.**

**Nothing else changed?**
- The diff touches only the two `canon.canon_tokens` call sites and their guard conditions, plus the error message string in `package_pin.py` (cosmetic: "is not one of" → "must be ONE word, one of"). The `MIN_STATEMENT_TOKENS` check in `trim_variant` (line 14) is untouched. The `num` lambda and `untrimmed_start` validation in `trim_problems` (lines 30–32) are untouched. No other files, no logic changes beyond the token-count guard. **Confirmed.**

## Findings

**P0:** None.

**P1:** None.

**P2:**
- `package_pin.py:29` — The error message now says "must be ONE word, one of …" but the check is on canonical tokens, not raw words. A string like `"But, so"` (two words, two tokens) would produce the message "must be ONE word," which is accurate in spirit. However, a hypothetical single-word string that canon expands to two tokens (none known in the six-word set, but canon rules could theoretically do this for a non-TRIM word) would produce a slightly misleading message. This is cosmetic and does not affect correctness. No action required.

## SHIP: yes

The change is minimal, correctly closes the gap between the branch's checks and the render's `validate_schema`, introduces no new rejections of render-valid pins, and the tests cover the two concrete failure cases (`"But so"`, `"and/or"`) plus the existing valid/invalid cases. All other suites pass. No law violations, no scope creep, no new dependencies.

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 0728 (one canonical token for a trimmed word): cycle 1 consensus

- grok, qwen and glm: no P0 or P1, all three "SHIP: yes". The predicates now match the render's validate_schema
  exactly. The only behaviour change is the intended one: a multi-token trimmed word ("But so", "and/or") is refused
  here instead of at the render's prepare.
- glm's P2s are recorded, with no change.
  - P2-1: an empty token list is refused before and after.
  - P2-2: the reason's text is not part of the seal; only segment fields are sealed.
  - P2-3: the pin-side "and/or" case is covered by the bad-value loop, which now includes it.
- Verification: test_medley 81 OK; every other suite OK.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0728/C2_STEP.diff (55 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 5fce642..63f680d 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -685,8 +685,8 @@ def trim_variant(m, sources):
   6 |          word, nxt = toks[w0].get("word") or "", toks[w0 + 1]
   7 |      except (KeyError, IndexError, TypeError, ValueError):
   8 |          return None
   9 | -    tok = canon.canon_tokens(word)[:1]
  10 | -    if w1 <= w0 or not tok or tok[0] not in TRIM_WORDS:
  11 | +    tok = canon.canon_tokens(word)                 # exactly ONE canonical token, as the render's validate_schema
  12 | +    if w1 <= w0 or len(tok) != 1 or tok[0] not in TRIM_WORDS:          # ("and/or" is two: the integrator, 07:19)
  13 |          return None
  14 |      if len(canon.canon_tokens(E.spoken(toks[w0 + 1:w1 + 1]))) < E.MIN_STATEMENT_TOKENS:
  15 |          return None                          # the kept words still make a statement (audit 0530 C1, glm P0-2)
  16 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
  17 | index 733acbe..dfbb94f 100644
  18 | --- a/pipeline/package_pin.py
  19 | +++ b/pipeline/package_pin.py
  20 | @@ -125,9 +125,9 @@ def trim_problems(segments):
  21 |              out.append(f"segment {i}: trimmed_leading and untrimmed_start come together (ruling 33 part 2)")
  22 |              continue
  23 |          w, u, st = s["trimmed_leading"], s["untrimmed_start"], s.get("start")
  24 | -        tok = canon.canon_tokens(w)[:1] if isinstance(w, str) else []
  25 | -        if not tok or tok[0] not in TRIM_WORDS:
  26 | -            out.append(f"segment {i}: trimmed_leading {w!r} is not one of {'/'.join(TRIM_WORDS)}")
  27 | +        tok = canon.canon_tokens(w) if isinstance(w, str) else []          # exactly ONE canonical token: the
  28 | +        if len(tok) != 1 or tok[0] not in TRIM_WORDS:                      # render's pinned.validate_schema
  29 | +            out.append(f"segment {i}: trimmed_leading {w!r} must be ONE word, one of {'/'.join(TRIM_WORDS)}")
  30 |          num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
  31 |          if not num(u) or not num(st) or not 0 <= float(u) < float(st):   # never raises (audit 0530 C1, glm P0-8)
  32 |              out.append(f"segment {i}: untrimmed_start {u!r} must be a number with 0 <= it < start {st!r}")
  33 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  34 | index c68fcc1..e231c02 100644
  35 | --- a/tests/package/test_medley.py
  36 | +++ b/tests/package/test_medley.py
  37 | @@ -803,6 +803,7 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
  38 |      def test_only_one_word_and_only_the_ruled_words(self):
  39 |          for sentence in ("But then Bitcoin had six negative weeks back to back in its whole history.",    # 'then'
  40 |                           "Because Bitcoin had six negative weeks back to back in its whole history.",      # not ruled
  41 | +                         "And/or Bitcoin had six negative weeks back to back in its whole history.",       # 2 tokens
  42 |                           "Bitcoin had six negative weeks back to back in its whole history."):             # no opener
  43 |              m, srcs = self.moment(sentence)
  44 |              self.assertIsNone(PK.trim_variant(m, srcs), sentence)
  45 | @@ -868,7 +869,8 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
  46 |          self.assertNotEqual(package_pin.seal(other, *args), mp["package_sha256"])
  47 |          other[1]["trimmed_leading"], other[1]["scorer_pending"] = "But", False      # and so is scorer_pending
  48 |          self.assertNotEqual(package_pin.seal(other, *args), mp["package_sha256"])
  49 | -        for bad in ({"trimmed_leading": "Because"}, {"untrimmed_start": 0.5}, {"untrimmed_start": -1.0},
  50 | +        for bad in ({"trimmed_leading": "Because"}, {"trimmed_leading": "But so"}, {"trimmed_leading": "and/or"},
  51 | +                    {"untrimmed_start": 0.5}, {"untrimmed_start": -1.0},
  52 |                      {"scorer_pending": False}):                                       # ruling 49 (a) in plain words
  53 |              p = spk(pk)
  54 |              p["segments"][1] = dict(p["segments"][1], **bad)
  55 | 
```

---

You are auditing a small diff on branch pp-selectid (Protocol Pulse: moments-first packaging). This branch seals pins
of short video medleys; the integrator renders them. Your role: a strict reviewer of a one-rule tightening.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background:
- Ruling 33 part 2 lets a clip that opens on ONE leading word (but/and/so/well/now/yeah) be cut one word in. The pin
  carries the trimmed word as "trimmed_leading".
- The render's pinned.validate_schema (the integrator's branch) requires the trimmed word to be EXACTLY ONE canonical
  token: `tok = canon.canon_tokens(tl); if len(tok) != 1 or tok[0] not in L.TRIMMABLE_LEADING: refuse`.
- The integrator found (07:19 ET Nov 13) that this branch's checks read only the FIRST canonical token
  (`canon.canon_tokens(w)[:1]`). So "But so" (tokens ['but', 'so']) or "and/or" (['and', 'or']) passed here, and the
  render would refuse that pin at prepare. Measured: canon.canon_tokens("But so") == ['but', 'so'],
  canon.canon_tokens("and/or") == ['and', 'or'], canon.canon_tokens("But,") == ['but'].

The change:
1. pipeline/package.py, trim_variant (the moment's own test): the trimmed word must be exactly one canonical token,
   one of TRIM_WORDS; else no variant.
2. pipeline/package_pin.py, trim_problems (the pin's test): the same; the reason says "must be ONE word".
3. tests/package/test_medley.py: a moment opening on "And/or" gives no variant; a pin with trimmed_leading "But so" or
   "and/or" is refused.
- test_medley 81 OK, every other suite OK.

Check that the two tests now accept exactly what the render's validate_schema accepts (one canonical token in the
six words, punctuation allowed as canon strips it), that nothing that passed before and is valid at the render is now
refused, and that nothing else changed.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".


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
