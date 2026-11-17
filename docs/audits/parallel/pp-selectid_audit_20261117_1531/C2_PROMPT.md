# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261117_1531
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 263 s finish=stop usage in 8984 / out 5821 usd_reported=0.001000 usd~0.114 (upper-bound price)

The code implements RULING 142, mirroring the integrator's logic for hyphen handling in number sequences and contraction matching for word-form pairs.

### Analysis

**1. Contraction Logic (`canon.word_form`)**
The implementation of the contraction rule `[t + "'s"]` vs `[t, 'is' | 'has']` is robust. It correctly:
- Validates the 1-token vs 2-token structure.
- Restricts the auxiliary verbs to exactly `"is"` or `"has"`.
- Enforces the "no digit" rule (`not re.search(r"\d", a[0])`), preventing numbers like `"1990's"` from being treated as contractions of `"1990 is"`.
- Handles the pair in both directions using `((x, y), (y, x))`.

**2. Hyphen Logic (`canon.canon_spans`)**
The logic to remove hyphens between numbers (`'24' '-7,'` $\rightarrow$ `'24' '7'`) is correctly implemented.
- The `re.match(r"^\s*-\d", w)` ensures the hyphen is at the start of the token.
- The `re.search(r"\d$", ...)` ensures the preceding token ended in a digit.
- The use of `w.replace("-", "", 1)` safely removes only the leading sign.
- It correctly preserves signs when the preceding word is not a number (e.g., `"fell" "-5%"`), as required.

**3. Decoder and Tests**
The `DECODER` hash update to `fc204e4a4385` is consistent across `lock_precheck.py`, `test_lock_precheck.py`, and `test_ruling_105.py`.

**4. Critical Defect in Tests**
There is a fundamental error in `tests/package/test_lock_precheck.py` within the `test_canon_spans_reads_the_hyphen_word_by_word` method:
```python
self.assertIn("minus", [t for t, _, _ in C.canon_spans(["it", "fell", "-5%"])])
```
`canon_spans` is a token-grouping and cleaning function; it returns the tokens as they appear in the text (or combined). It does **not** perform the spoken expansion of symbols (e.g., converting `"-5%"` to `"minus 5 percent"`). That expansion happens in `canon_tokens`. Consequently, `C.canon_spans(["it", "fell", "-5%"])` will return a list containing the token `"-5%"`, not the word `"minus"`. This test will fail every time it is run.

### Findings

[P1] **Broken Test Case**: `tests/package/test_lock_precheck.py:test_canon_spans_reads_the_hyphen_word_by_word` asserts that `canon_spans` returns the expanded word `"minus"`. `canon_spans` only handles token boundaries and grouping; the spoken expansion is handled by `canon_tokens`. This test will fail, blocking the merge.

P1_OR_WORSE: 1

## GPT-OSS-20B — CYCLE 1 OUTPUT
# gpt-oss-20b (openai/gpt-oss-20b) 91 s finish=stop usage in 7778 / out 14883 usd_reported=0.002085 usd~0.247 (upper-bound price)

**Findings**

| # | Issue | Description | Severity |
|---|-------|-------------|----------|
| 1 | `canon.word_form` incorrectly accepts “it’s” ↔ “it has” | The new contraction rule matches any `t + "'s"` against `[t, "is" | "has"]`. It therefore treats “it’s” vs “it has” as a valid word‑form pair, allowing a run‑decode that says “it has” to pass a gate that should reject it. | **[P0]** |
| 2 | Potential breakage of `lock_precheck.DECODER` constant | The decoder SHA was changed from `fe809cb4e680` to `fc204e4a4385`. If any other module imports `pipeline.lock_precheck.DECODER` (outside the updated tests), it will now reference the wrong value, causing lock‑precheck failures or incorrect file naming. | **[P1]** |

**P1_OR_WORSE: 2**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 150 s finish=stop usage in 8594 / out 9169 usd_reported=0.006937 usd~0.163 (upper-bound price)



# Code Audit — pp-selectid / RULING 142 (batches 111 + 112 mirror)

## Scope Reviewed

- `pipeline/canon.py` — `canon_spans` hyphen rule + `word_form` contraction
- `pipeline/lock_precheck.py` — DECODER constant bump
- `tests/package/test_lock_precheck.py` — new tests + decoder pins
- `tests/package/test_ruling_105.py` — decoder pin

---

## Findings

### [P3] canon_spans hyphen rule: theoretical sign-drop in a compound-ASR-error edge

The new condition

```python
if i and re.match(r"^\s*-\d", w) and re.search(r"\d$", (words[i - 1] or "").rstrip()):
    w = w.replace("-", "", 1)
```

drops the hyphen whenever a `-<digit>` token immediately follows a digit-ending token. This is correct for the ruling's target case (ASR splitting a compound like "24-7" into "24" "-7,") and is consistent with the existing standalone-`"-"` handler above it (which already guards on `not re.search(r"[\d.,%]\s*$", words[i-1])`).

The only scenario where a *genuine* minus sign would be lost is if ASR emits exactly `["…24", "-7"]` for the spoken phrase "twenty-four minus seven" with no intervening conjunction. In natural speech (and in the pipeline's financial/Bitcoin domain) a speaker would say "24, then minus 7" or "24 to negative 7," producing a non-digit token between them. The existing standalone-`"-"` path already handles the case where ASR keeps the sign as its own token. This is a ruling-sanctioned reading, not a bug, but it is worth a one-line comment in `canon_spans` noting the assumption (hyphen-attached-to-digit after a bare digit = tokenisation artifact, not a sign) so a future reader doesn't "fix" it.

### [P3] word_form contraction: possessive "X's" vs "X has" classified as a word-form pair

```python
if len(a) == 1 and len(b) == 2 and b[1] in ("is", "has") and a[0] == b[0] + "'s" \
        and not re.search(r"\d", a[0]):
    return True
```

This correctly matches the ruling's case ("Bitcoin's" ↔ "Bitcoin is") and the grammatical contraction ("it's" ↔ "it has"). It would also match a possessive reading ("Bitcoin's price" ↔ "Bitcoin has price"), but `word_form` is a *classification* only: it tells ruling 131 (A) that the two readings differ by a word-form pair, after which the two-of-three adjudication (sealed text, run decode, second recogniser) still decides. A genuine possessive-vs-verb mismatch would be caught by the second recogniser or the sealed text disagreeing, producing a HOLD. No gate is bypassed. No action needed; noting for completeness.

### [P3] Test coverage: no explicit negative for punctuation on the preceding word

`test_canon_spans_reads_the_hyphen_word_by_word` verifies:
- `["24", "-7,", "365"]` → `["24", "7", "365"]` (hyphen dropped)
- `["it", "fell", "-5%"]` → contains `"minus"` (hyphen kept)

A third assertion such as `["24.", "-7"]` → hyphen kept (previous word ends in `.`, not a bare digit) would pin the boundary of the `re.search(r"\d$", …)` guard. Low risk since the regex is straightforward, but it would make the test suite self-documenting for the next person touching `canon_spans`.

### Decoder lockstep — verified

- `DECODER` bumped `fe809cb4e680` → `fc204e4a4385`; full SHA in the comment matches the 12-char prefix.
- Both test files (`test_lock_precheck.py`, `test_ruling_105.py`) updated to the new prefix.
- Result-file naming embeds the decoder, so old results under the previous SHA are not accidentally read (fail-closed by construction).
- `RULES` string unchanged (ruling 142 is covered by the existing rule set per the comment).
- The builder's mirror correctly excludes the integrator's acquisition-side code (post_live fallback, offset guard) — those live in branch `r142-postlive 70e78551`.

### Law compliance check

| Law | Status |
|-----|--------|
| L-k (one canonical form) | Compliant. The contraction and hyphen rules make canon read what the listener hears; the two-of-three adjudication prevents auto-pass. |
| L-l (model reply counts only whole) | Not touched. |
| LAW 20 / M2 (thresholds are constants; no reclassification) | Compliant. DECODER is a constant; no gate threshold changed; no failing gate reclassified. |
| M12 (fail closed) | Compliant. `word_form` returning `True` is a classification, not a pass; the adjudication still gates. |
| LAW 22 (v2f byte-identical) | The canon change could alter text comparisons in gates that read v2f transcripts. The ruling notes this is a lockstep with the integrator's audited branch; v2f's lock_precheck results will be regenerated under the new decoder. No byte-identity risk to the *render* (canon is not in the render path). |
| Smallest diff / no new renderer | Compliant. 4 files, ~30 lines of logic change. |

### Answers to the three requested checks

1. **Can the contraction rule exempt anything the ruling did not?** No. It is restricted to `[t + "'s"]` vs `[t, "is"|"has"]`, either direction, no digit in `t

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus (pp-selectid_audit_20261117_1531, batches 111 + 112's mirror)

SEATS ANSWERED: 3 of 3. qwen3.8-27b: P0/P1 none. gemma-4-31b-it: one P1 claimed. gpt-oss-20b: one P0 and one P1
claimed. All three are refuted below from the code and the passing tests.

1. gemma [P1] "test_canon_spans_reads_the_hyphen_word_by_word asserts canon_spans gives 'minus'; canon_spans only groups
   tokens, so the test fails": REFUTED. The test passes (test_lock_precheck + test_attest + test_ruling_105: 63 passed).
   canon_spans returns CANONICAL tokens with their word spans: the sign expansion is part of it ('fell' '-5%' gives
   'minus' '5' 'percent'). Mutation X4 (the new hyphen rule removed) is killed by that test.
2. gpt-oss [P0] "word_form accepts "it's" against 'it has', letting a run decode that says 'it has' pass a gate":
   REFUTED. word_form never passes anything. attest.class_131 uses it ONLY to lift law L-v 2's critical-token HOLD
   (a number, a name, a negation) from one pair. The pair then goes to ruling 131 (A)'s two of three, unchanged: the
   approved words when the second recogniser reads them, the run's reading only at an edge >= 3, all three different
   holds (test_the_contraction_is_the_same_word_form_pair covers all three). "it" is not a critical token at all, so
   such a pair reaches the same vote with or without word_form. The contraction both ways ('is' / 'has') is the ruled
   design (ruling 142 (2), feb4b72f's own case) and the integrator's shared canon.py, byte-identical.
3. gpt-oss [P1] "another module may hold the old DECODER": REFUTED. lock_precheck.DECODER is the one source. Its
   readers are lock_precheck.result_file and the tests (grep above). The lockstep moves both sides together; entries
   under another decoder are never read (unchanged rule).

## No change from cycle 1 to cycle 2.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261117_1531/C2_STEP.diff (111 lines)
```
   1 | diff --git a/pipeline/canon.py b/pipeline/canon.py
   2 | index c12c8a1..043464d 100644
   3 | --- a/pipeline/canon.py
   4 | +++ b/pipeline/canon.py
   5 | @@ -254,6 +254,8 @@ def canon_spans(words):
   6 |          if w.strip() in ("-", "+", "\u2212") and j < len(words) and re.match(r"^\s*\$?\d", words[j] or "") and \
   7 |                  (w.strip() != "-" or not i or not re.search(r"[\d.,%]\s*$", words[i - 1] or "")):
   8 |              w, j = w.strip() + (words[j] or "").strip(), j + 1        # '-' '5%' = '-5%'; '70' '-' '75' stays a range
   9 | +        if i and re.match(r"^\s*-\d", w) and re.search(r"\d$", (words[i - 1] or "").rstrip()):
  10 | +            w = w.replace("-", "", 1)        # ruling 142 (1), word by word as in the text: '24' '-7,' reads '24' '7'
  11 |          while j < len(words) and (re.match(r"^\s*[.,][0-9A-Za-z]", words[j] or "") or (     # '$81' ',000'
  12 |                  re.fullmatch(r"\$?\d{1,3}(\d{3})*", w.strip()) and re.fullmatch(r"\d{3}[.,!?]*", (words[j] or "").strip()))):
  13 |              w, j = w + (words[j] or "").strip(), j + 1                                      # '74' '000'
  14 | @@ -316,8 +318,14 @@ def word_form(x, y):
  15 |      """Ruling 142 (2) (orchestrator 2026-11-17 '14:32'): two readings that differ ONLY by a possessive or plural ending
  16 |      on ONE word ('bitcoin' / "bitcoin's" / 'bitcoins' / "bitcoins'"): a word-form pair, decided like any other differing
  17 |      pair by ruling 131 (A)'s two of three (the sealed text takes that reading; all three different still holds). Never
  18 | -    a token with a digit ('1990s' is not '1990': a number stays law L-v 2's)."""
  19 | +    a token with a digit ('1990s' is not '1990': a number stays law L-v 2's). The same "'s" written as a contraction is
  20 | +    the same pair (the ruling's own case, Natalie Brunell feb4b72f: "Bitcoin's a responsibility" against "Bitcoin is a
  21 | +    responsibility"): [t + "'s"] against [t, 'is'] or [t, 'has']."""
  22 |      x, y = list(x or []), list(y or [])
  23 | +    for a, b in ((x, y), (y, x)):                             # the contraction, either way round
  24 | +        if len(a) == 1 and len(b) == 2 and b[1] in ("is", "has") and a[0] == b[0] + "'s" \
  25 | +                and not re.search(r"\d", a[0]):
  26 | +            return True
  27 |      if len(x) != len(y) or not x:
  28 |          return False
  29 |      diff = [(a, b) for a, b in zip(x, y) if a != b]
  30 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
  31 | index 01138c8..43b30d8 100644
  32 | --- a/pipeline/lock_precheck.py
  33 | +++ b/pipeline/lock_precheck.py
  34 | @@ -61,7 +61,7 @@ RULES = ("ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 10
  35 |  #   targeted re-listen joins the rules (the integrator's message of 14:3x Nov 14); entries under the old RULES are never
  36 |  #   read. RULING 84 (orchestrator 20:41 Nov 13): the integrator's
  37 |  #   RULES string (its message of 20:4x Nov 13). RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's
  38 | -DECODER = "fe809cb4e680"                      # side): the render's own cut placement joins the pre-check (a passing
  39 | +DECODER = "fc204e4a4385"                      # side): the render's own cut placement joins the pre-check (a passing
  40 |  #   entry carries "cut"; a span the render cannot cut holds: "ruling 73: the render cannot cut this span: ..."). RULING
  41 |  #   84 changed the render's adjudicate_lock (pinned.py), so the decoder_sha changed: 962353613cb0e065008ab0405ca8550111ddd3ca3ba70f0ae65b4b77ab1876d8
  42 |  #   (ruling 73's was 8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7). RULING 90 (the integrator's
  43 | @@ -78,6 +78,9 @@ DECODER = "fe809cb4e680"                      # side): the render's own cut plac
  44 |  #   b52c9354d604ab2303a91e6e6e5f926990987d46448992579684934f62e9392d
  45 |  #   RULING 142 (canon's '24 -7' and canon.word_form, adjudicate_lock's word-form exemption; the integrator's branch
  46 |  #   r141-sign f02dd73c, audited; lockstep as with 135): fe809cb4e680a3bc5df49e4c397e79f6cf2277650ea02c05cf88b34ecc573ebd
  47 | +#   RULING 142, the integrator's batches 111 (the post_live fallback, acquisition-side) + 112 (canon_spans reads '24' '-7,'
  48 | +#   as '24' '7'; word_form takes the contraction [t + "'s"] / [t, 'is' | 'has']; branch r142-postlive 70e78551; one
  49 | +#   lockstep): fc204e4a4385a1906ef858923936cd6d6ed3a65ea78f2007281e2d4945038e09
  50 |  RESULTS = "/home/ultron/protocol_pulse/data/lock_precheck/results"        # the integrator's; read only
  51 |  REQUESTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
  52 |                          "lock_requests")      # this worktree's; the service only reads it
  53 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
  54 | index 17514ac..34476f1 100644
  55 | --- a/tests/package/test_lock_precheck.py
  56 | +++ b/tests/package/test_lock_precheck.py
  57 | @@ -60,7 +60,7 @@ class TestRequest(Dirs):
  58 |          self.assertNotIn("trimmed_leading", s[1])                                        # only a trimmed moment
  59 |          self.assertEqual((s[2]["trimmed_leading"], s[2]["untrimmed_start"]), ("And", 1690.9))
  60 |          self.assertEqual(os.path.basename(LP.result_file(s[0], self.res)),
  61 | -                         "DcUbBkyeh9M.216.054-228.674.fe809cb4e680.json")             # ruling 142's decoder
  62 | +                         "DcUbBkyeh9M.216.054-228.674.fc204e4a4385.json")             # batches 111 + 112's decoder
  63 |  
  64 |      def test_a_request_is_renamed_from_its_tmp_and_never_written_over(self):
  65 |          segs = LP.segments_of([HOOK, CLIP])
  66 | @@ -422,6 +422,31 @@ class TestRuling142(unittest.TestCase):
  67 |          self.assertEqual((d["verdict"], d.get("adoption")), ("adopt", AT.RULE_131), d)
  68 |          self.assertEqual(self.decide(self.APP, self.THIRD, None)["verdict"], "hold")    # all three differ
  69 |  
  70 | +    def test_the_contraction_is_the_same_word_form_pair(self):
  71 | +        """Batch 112 (the ruling's own case, Natalie Brunell feb4b72f): "Bitcoin's a responsibility" against "Bitcoin is
  72 | +        a responsibility": [t + "'s"] against [t, 'is' | 'has'], either way round, no digit in t."""
  73 | +        self.assertTrue(C.word_form(["bitcoin's"], ["bitcoin", "is"]))
  74 | +        self.assertTrue(C.word_form(["bitcoin", "has"], ["bitcoin's"]))
  75 | +        for x, y in ((["1990's"], ["1990", "is"]), (["bitcoin's"], ["bitcoin", "was"]), (["bitcoin's"], ["ether", "is"])):
  76 | +            self.assertFalse(C.word_form(x, y), (x, y))
  77 | +        app = "Holding your own keys means Bitcoin's a responsibility that nobody else can carry for you in the end."
  78 | +        run = "Holding your own keys means Bitcoin is a responsibility that nobody else can carry for you in the end."
  79 | +        third = "Holding your own keys means Bitcoin was a responsibility that nobody else can carry for you in the end."
  80 | +        s = LP.segments_of([{"video_id": "x", "start": 1.0, "end": 9.0, "text": app}])[0]
  81 | +
  82 | +        def decide(spoken, second, took):
  83 | +            adj = {"rule": "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", "run_decode": run, "approved": app,
  84 | +                   "second_recogniser": second,
  85 | +                   "pairs": [{"run": "bitcoin is", "approved": "bitcoin's", "took": took, "edge_distance": 5}]}
  86 | +            return LP.decide(s, entry(s, "adopt_spoken", spoken_text=spoken, adjudication=adj))
  87 | +        self.assertEqual(decide(app, app, "approved")["verdict"], "pass")
  88 | +        self.assertEqual(decide(run, run, "run")["verdict"], "adopt")
  89 | +        self.assertEqual(decide(app, third, None)["verdict"], "hold")
  90 | +
  91 | +    def test_canon_spans_reads_the_hyphen_word_by_word(self):
  92 | +        self.assertEqual([t for t, _, _ in C.canon_spans(["24", "-7,", "365"])], ["24", "7", "365"])
  93 | +        self.assertIn("minus", [t for t, _, _ in C.canon_spans(["it", "fell", "-5%"])])
  94 | +
  95 |      def test_a_name_that_is_no_word_form_still_holds(self):
  96 |          app = self.APP.replace("Bitcoin's", "Ethereum's")
  97 |          adj = {"rule": "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", "run_decode": self.RUN, "approved": app,
  98 | diff --git a/tests/package/test_ruling_105.py b/tests/package/test_ruling_105.py
  99 | index ecccdfc..0a732d6 100644
 100 | --- a/tests/package/test_ruling_105.py
 101 | +++ b/tests/package/test_ruling_105.py
 102 | @@ -40,7 +40,7 @@ BLOCKWARE = record()
 103 |  class TestTheRules(Dirs):
 104 |      def test_the_rules_and_decoder_are_the_integrators_ruling_105_ones(self):
 105 |          self.assertIn("+ ruling 103 + ruling 105", LP.RULES)                      # ruling 131 joined after it
 106 | -        self.assertEqual(LP.DECODER, "fe809cb4e680")                                 # ruling 142 moved it
 107 | +        self.assertEqual(LP.DECODER, "fc204e4a4385")                                 # batches 111 + 112 moved it
 108 |          s = LP.segments_of([HOOK])[0]
 109 |          self.put(s, entry(s, rules="ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103",
 110 |                            at="2026-11-14T21:00:00Z"))
 111 | 
```

---

pp-selectid: RULING 142, the BUILDER'S MIRROR of the integrator's batches 111 + 112 (one decoder lockstep; its branch
r142-postlive 70e78551, audited on its side). The previous lockstep (batch 110 / my 45ad6040) is live. The re-judges under
it still held: f0a51c45 because pinned._majority_text maps tokens back to words with canon.canon_spans word by word, and
the word "-7," alone still read "minus 7"; feb4b72f because its "Bitcoin's" is the CONTRACTION of "Bitcoin is" (a 2-token
against 1-token pair, outside 110's one-token word_form). Files: pipeline/canon.py (copied BYTE-IDENTICAL from the
integrator's staged file, sha256 90f23312a02d402b40daaaf58d89556ecdd2ee526795cd74113b778eb3fbf2a5),
pipeline/lock_precheck.py (DECODER only), tests/package/test_lock_precheck.py, tests/package/test_ruling_105.py.

THE CHANGE:
(a) canon.canon_spans: a word "-<digit>..." right after a word ending in a digit loses its hyphen (the word-by-word form
    of 110's _NUM_HYPHEN; '24' '-7,' reads '24' '7'); a sign after a word ('fell' '-5%') stays 'minus'.
(b) canon.word_form also takes the contraction [t + "'s"] against [t, 'is'] or [t, 'has'], either way round, with no
    digit in t. attest.class_131's critical check already calls canon.word_form (my 45ad6040, unchanged here), so the
    contraction pair reaches ruling 131 (A)'s two of three with the copy: the approved words when the second recogniser
    reads them, the run's reading only at an edge >= 3, all three different still holds.
(c) lock_precheck.DECODER fc204e4a4385 (full sha in the comment). RULES unchanged (ruling 142 covers it). The post_live
    fallback and its offset guard are the integrator's acquisition code (not in my files).

TESTS (test_lock_precheck TestRuling142, 2 new; the decoder pins updated): the contraction both ways round, and what is
not one (a digit, 'was', another word); feb4b72f's shape decided two of three both ways and held when all three differ;
canon_spans reads '24' '-7,' as '24' '7' and keeps 'fell' '-5%' a sign. Mutations: 6 of 6 killed.

PLEASE CHECK: (1) can the contraction rule exempt anything the ruling did not (a number, another verb, another word)?
(2) does the canon_spans change ever drop a real sign? (3) the decoder and the tests.


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
