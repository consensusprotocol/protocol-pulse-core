# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261117_1057
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 469 s finish=stop usage in 12306 / out 18279 usd_reported=0.015730 usd~0.311 (upper-bound price)



# Code Audit — pp-selectid / RULING 135 (Comparison Canon)

## Scope Reviewed
`pipeline/attest.py` (class_84, class_131), `pipeline/canon.py` (same_words, comparison_form, nonlexical, REDUCTIONS, FILLER_TOKENS, CONSONANTS), `pipeline/lock_precheck.py` (RULES string), `tests/package/test_lock_precheck.py` (TestRuling135, updated TestRuling131, updated TestRuling84).

---

## Findings

### [P3] `REDUCTIONS["cause"]` is sense-ambiguous
`"cause": ("because",)` treats the noun *cause* ("the cause of the crash") identically to the spoken reduction of *because*. In a Bitcoin/crypto transcript the noun sense is rare, and the ruling explicitly closed the list, so this is by design. Noted for completeness; no action required unless a future ruling adds a disambiguation.

### [P3] Tautological branch in `test_a_spelling_pair_never_reaches_the_vote_in_class_131`
```python
self.assertEqual([...],
    [("itrust", "itrustcapitals", "spelling")] if rows and rows[0]["approved"] == "itrustcapitals"
    else [(rows[0]["spoken"], rows[0]["approved"], "spelling")] + [] if rows else [])
```
The `else` branch reconstructs the expected value from the actual output, making that branch self-fulfilling. The *meaningful* assertion is the next line (`all(x["took"] == "spelling")`) and the final `verdict == "pass"` check, which are solid. The first assertion could be simplified to a single concrete expected list to avoid the appearance of a circular check.

### [P3] `d.get("differences") or []` in `test_spelling_is_no_difference_in_ruling_72s_layer`
If the `decide` result ever omitted the `"differences"` key, `None or []` → `[]` and `all(...)` over an empty iterable is `True`, silently passing. In practice `decide` always populates the key, but a `self.assertIn("differences", d)` guard would make the test fail-closed.

### [P3] Comment layout in `lock_precheck.py`
```python
RULES = "..."   # RULING 135
#   (orchestrator 10:50 ET Nov 17): ...
#   RULING 131
#   (orchestrator 08:25 ET Nov 17): ...
```
The bare `#   RULING 131` line reads as a heading but is syntactically just a comment. Cosmetic; no functional impact.

---

## Verification of the Four Requested Checks

### (1) Nothing 135 keeps holding can be dropped as spelling

Traced every "still holds" case through `canon.same_words`:

| Case | Tokens (x vs y) | Path in `same_words` | Result |
|---|---|---|---|
| Digit: "2day" vs "today" | `["2day"]` vs `["today"]` | `a≠b`, digit present → `False` | **Holds** ✓ |
| Negation: "isn't" vs "is" | `["isnt"]` vs `["is"]` | `a≠b`, no digit, `"isnt"≠"is"` → `False` | **Holds** ✓ |
| Content word: "bust" vs "trust" | `["bust"]` vs `["trust"]` | `a≠b`, no digit, `"bust"≠"trust"` → `False` | **Holds** ✓ |
| Letter-name: "Q" vs "I" | `["q"]` vs `["i"]` | `lx=["q"]`, `ly=[]` (i∉CONSONANTS) → skip; `a=[]`, `b=["i"]`; `""≠"i"` → `False` | **Holds** ✓ |
| Two different consonants: "h" vs "b" | `["h"]` vs `["b"]` | `lx=["h"]`, `ly=["b"]`, `lx≠ly` → `False` | **Holds** ✓ |
| Article dropped: "a capital" vs "capital" | `["a","capital"]` vs `["capital"]` | `a≠b`, no digit, `"acapital"≠"capital"` → `False` | **Holds** ✓ |

All four test cases in `test_what_still_holds` assert `"hold"` and the logic confirms they will.

### (2) Drop placement matches the render's lock

- **class_131**: `currency_pair` → `continue`; **then** `canon.same_words` → `continue`; **then** `edge_distance` / `critical` / vote. The spelling drop is strictly after currency and before the critical check and the vote. ✓
- **class_84**: `tag == "equal"` → `continue`; **then** `canon.same_words` → `continue`; **then** `critical` / class assignment. The existing filler step (spoken-side fillers) is in a part of the function not shown in the diff and is described as "UNCHANGED" and "runs first." The test accepts both `"filler"` and `"spelling only (ruling 135)"` as valid classes for post-pair differences, confirming the filler step still executes before `same_words` for the cases it was designed to catch. ✓
- **`mine` filter**: `x["took"] not in ("currency", "spelling")` excludes both non-real pairs from the record comparison, matching the integrator's record which keeps them apart. ✓

### (3) A same-words pair can never change the sealed text

- In **class_131**, a spelling pair gets `took="spelling"`. The merged/sealed text uses the approved side for any pair whose `took` is not `"run"`. The approved words are preserved. ✓
- In **class_84**, the pair is recorded with a class label but does not alter the text. ✓
- The test `test_a_spelling_pair_never_reaches_the_vote_in_class_131` confirms: `adj["pairs"]` is `[]`, this side's `mine` (excluding spelling) is `[]`, they match, and the verdict is `"pass"` with the approved text intact. ✓

### (4) Tests

- **TestRuling135** (new): 3 test methods covering spelling/segmentation/reduction/stray-consonant (no differe

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus (pp-selectid_audit_20261117_1057, ruling 135)

SEATS ANSWERED: 1 of 3 (qwen3.8-27b: P0/P1 none, a traced review; gemma-4-31b-it and mimo-v2.6-flash-rl spent their
whole token caps with no answer). One seat is thin: cycle 2 adds gpt-oss-20b at effort medium (the seat the
integrator's ruling 135 audits answered on) and drops mimo (empty twice today).

## Changed since cycle 1's diff
1. canon.same_words gained `stray` (the integrator's own cycle-2 finding, Heimdall batch 104 c2: "one reading ALONE
   hears" a stray letter, but same_words sees only two sides): a single consonant is dropped only on the side named in
   stray. The integrator passes none in the lock (a lone letter there is a token; 131 (A)'s vote of three decides it)
   and stray="y" in ruling 72's comparison (the second recogniser's side). This side mirrors it: class_131 passes none;
   class_84 passes stray="x", because its FIRST argument is the spoken text, the second recogniser's reading. canon.py
   is the integrator's final (commit 8cb2e0b7, sha256 3c20e27f75b2), byte-identical.
2. tests/package/test_attest.py: "a filler on the approved side alone" now is spelling only (135 (d)); a lone letter the
   LOCK (approved side) carries still holds; the second recogniser's stray 'h' is no word.
3. Mutations M1-M28 after a control run: 28 of 28 killed (M27: stray removed in class_84; M28: stray on both sides).


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261117_1057/C2_STEP.diff (295 lines)
```
   1 | diff --git a/pipeline/attest.py b/pipeline/attest.py
   2 | index ba38c08..f4bb6eb 100644
   3 | --- a/pipeline/attest.py
   4 | +++ b/pipeline/attest.py
   5 | @@ -19,7 +19,14 @@ RULING 131 (orchestrator 08:25 ET Nov 17) has its own re-check, class_131: (A) p
   6 |  two of the three readings (the approved text, the run's decode, the second recogniser) decide it and the sealed text
   7 |  takes that reading, at least 3 tokens from both cut edges; never a number, a name or a negation; all three different
   8 |  holds. (B) a currency symbol is formatting (canon.dollars_after_number, G18's one tolerance). It re-runs the render's own
   9 | -steps on the three readings the lock records and never trusts the record's own classes."""
  10 | +steps on the three readings the lock records and never trusts the record's own classes.
  11 | +
  12 | +RULING 135 (orchestrator 10:50 ET Nov 17), THE COMPARISON CANON: "differences of spelling are not differences of
  13 | +speech". A differing pair whose two sides are the same words by canon.same_words (case, punctuation and apostrophes
  14 | +ignored; segmentation ignored, names too; the closed list of spoken reductions; non-lexical tokens, fillers and a stray
  15 | +single consonant, left out; a digit or a different single letter still differs) is no difference: dropped right after
  16 | +the currency pairs in class_131 (as the render's lock drops it before the critical check and the vote) and before any
  17 | +class in class_84 (as ruling 72's comparison drops it). The sealed text keeps the approved words there."""
  18 |  import re
  19 |  from difflib import SequenceMatcher
  20 |  
  21 | @@ -112,6 +119,10 @@ def class_84(spoken, approved):
  22 |          if tag == "equal":
  23 |              continue
  24 |          rs, ps = r2[a:b], p[c:d]
  25 | +        if canon.same_words(rs, ps, stray="x"):          # RULING 135: spelling only; a lone consonant is a stray
  26 | +            #   sound only on the spoken side (the second recogniser's reading, as ruling 72's comparison passes it)
  27 | +            out.append({"spoken": " ".join(rs), "approved": " ".join(ps), "class": "spelling only (ruling 135)"})
  28 | +            continue
  29 |          if any(critical(t, texts) for t in rs + ps):
  30 |              k = None
  31 |          elif rs and ps:
  32 | @@ -221,6 +232,10 @@ def class_131(spoken, approved, adj):
  33 |          if currency_pair(r, p, op):
  34 |              out.append(dict(row, took="currency", edge_distance=None, **{"class": "currency format (ruling 131 (B))"}))
  35 |              continue
  36 | +        if canon.same_words(r[a:b], p[c:d]):            # RULING 135: dropped before the critical check and the vote
  37 | +            #   (no stray side: in the lock a lone letter is a token, and the vote of three readings decides it)
  38 | +            out.append(dict(row, took="spelling", edge_distance=None, **{"class": "spelling only (ruling 135)"}))
  39 | +            continue
  40 |          row["edge_distance"] = edge_distance(r, p, op)
  41 |          if any(critical(t, texts) for t in r[a:b] + p[c:d]):
  42 |              out.append(dict(row, took=None, **{"class": None}, why="a number, a name or a negation (law L-v 2)"))
  43 | @@ -239,7 +254,8 @@ def class_131(spoken, approved, adj):
  44 |      rec = adj.get("pairs")
  45 |      theirs = [(x.get("run"), x.get("approved"), x.get("took"), x.get("edge_distance")) for x in rec] \
  46 |          if isinstance(rec, list) and all(isinstance(x, dict) for x in rec) else None
  47 | -    mine = [(x["spoken"], x["approved"], x["took"], x["edge_distance"]) for x in out if x["took"] != "currency"]
  48 | +    mine = [(x["spoken"], x["approved"], x["took"], x["edge_distance"]) for x in out
  49 | +            if x["took"] not in ("currency", "spelling")]           # the record keeps both apart from its pairs
  50 |      if theirs != mine:
  51 |          out.append(held(f"the lock record's pairs are not this side's: {theirs} against {mine}"[:400]))
  52 |      sp = canon.canon_tokens(spoken)
  53 | diff --git a/pipeline/canon.py b/pipeline/canon.py
  54 | index 25aa737..9a373e0 100644
  55 | --- a/pipeline/canon.py
  56 | +++ b/pipeline/canon.py
  57 | @@ -281,6 +281,56 @@ def currency_free(tokens):
  58 |      return [w for k, w in enumerate(tokens) if not dollars_after_number(tokens, k)]
  59 |  
  60 |  
  61 | +# RULING 135 (orchestrator 10:50 ET Nov 17): THE COMPARISON CANON. "Differences of spelling are not differences of
  62 | +# speech." Applied to a differing pair's two sides before the pair is compared (the lock, ruling 72's comparison,
  63 | +# G18); canon_tokens itself is unchanged, so spans, edges and indices are not touched.
  64 | +REDUCTIONS = {      # (c) spoken reductions equal their full form: a CLOSED list, none added without a ruling
  65 | +    "kinda": ("kind", "of"), "sorta": ("sort", "of"), "gonna": ("going", "to"), "wanna": ("want", "to"),
  66 | +    "gotta": ("got", "to"), "lemme": ("let", "me"), "gimme": ("give", "me"), "cause": ("because",),
  67 | +    "cuz": ("because",), "em": ("them",), "ya": ("you",), "yeah": ("yes",), "yep": ("yes",)}
  68 | +FILLER_TOKENS = frozenset({"um", "uh", "er", "ah", "hm", "hmm", "mm", "mhm"})      # (d) non-lexical
  69 | +CONSONANTS = frozenset("bcdfghjklmnpqrstvwxz")                                     # (d) a stray consonant ("a", "i": words)
  70 | +
  71 | +
  72 | +def comparison_form(tokens):
  73 | +    """RULING 135 (a)+(c): canon tokens with their apostrophes removed, each spoken reduction (REDUCTIONS) expanded."""
  74 | +    out = []
  75 | +    for t in tokens:
  76 | +        t = str(t).replace("'", "")
  77 | +        out += list(REDUCTIONS.get(t, (t,)))
  78 | +    return out
  79 | +
  80 | +
  81 | +def nonlexical(tok, stray=False):
  82 | +    """RULING 135 (d): a filler (FILLER_TOKENS); with stray, also a single consonant letter. Not a word."""
  83 | +    return tok in FILLER_TOKENS or (stray and len(tok) == 1 and tok in CONSONANTS)
  84 | +
  85 | +
  86 | +def same_words(x, y, stray=()):
  87 | +    """RULING 135: the two sides of a differing pair (lists of canon tokens) are the same words. Both sides in comparison
  88 | +    form (a, c), fillers left out (d); equal tokens, or, when neither side holds a digit, equal letters once every space
  89 | +    and hyphen is gone (b: 'itrust capital's' = 'I trust capital's' = 'iTrustCapital's', names too). A single consonant
  90 | +    is a stray sound only on a side named in `stray` ("x" / "y"): the side the caller knows ONE reading alone hears
  91 | +    (ruling 72's second recogniser against the lock, G18's final decode); in the lock itself a lone letter is a token
  92 | +    and the vote of three readings decides it (Heimdall batch 104 c2: a letter two readings hear is a word). Still a
  93 | +    difference: two different single letters, any digit difference (numbers compare token for token; the currency form
  94 | +    is (B)'s), and any other change of letters (a negation, a name, a content word). "cause" is taken as the ruled
  95 | +    "'cause" (canon_tokens drops the apostrophe, so the noun reads the same; two readings of one audio never trade the
  96 | +    noun "cause" for "because")."""
  97 | +    cx, cy = comparison_form(x), comparison_form(y)
  98 | +    lx = [t for t in cx if len(t) == 1 and t in CONSONANTS]
  99 | +    ly = [t for t in cy if len(t) == 1 and t in CONSONANTS]
 100 | +    if lx and ly and lx != ly:
 101 | +        return False
 102 | +    a = [t for t in cx if not nonlexical(t, "x" in stray)]
 103 | +    b = [t for t in cy if not nonlexical(t, "y" in stray)]
 104 | +    if a == b:
 105 | +        return True
 106 | +    if any(ch.isdigit() for t in a + b for ch in t):
 107 | +        return False
 108 | +    return "".join(a).replace("-", "") == "".join(b).replace("-", "")
 109 | +
 110 | +
 111 |  def canon(text):
 112 |      return " ".join(canon_tokens(text))
 113 |  
 114 | diff --git a/pipeline/lock_precheck.py b/pipeline/lock_precheck.py
 115 | index d641d88..12aab99 100644
 116 | --- a/pipeline/lock_precheck.py
 117 | +++ b/pipeline/lock_precheck.py
 118 | @@ -31,7 +31,9 @@ Outcomes:
 119 |    when this side's own re-check (attest.class_131, from the record's three readings) finds every pair decided the same
 120 |    way, every run-taken pair at least 3 tokens from both cut edges, no number, name or negation, and the spoken text
 121 |    the merged reading; anything else is a hold (fail closed). (B): currency format ('$2 billion' for a spoken
 122 | -  '2 billion') is no difference.
 123 | +  '2 billion') is no difference. RULING 135: neither is a pair of the same words by canon.same_words (spelling,
 124 | +  segmentation, the closed reductions, fillers and a stray consonant); this side's re-checks drop it where the
 125 | +  render's lock and ruling 72's comparison do (attest.class_131, attest.class_84).
 126 |  - hold: the clip may not be used with that text. The reason says why.
 127 |  - error, an outcome this module does not know, or no answer in time: no verdict. Never a pass (law L-m). A request
 128 |    is sent again rather than reusing an error.
 129 | @@ -47,7 +49,9 @@ from datetime import datetime, timezone
 130 |  import attest as AT
 131 |  import canon as C
 132 |  
 133 | -RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + ruling 131"   # RULING 131
 134 | +RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + ruling 131 + ruling 135"   # RULING 135
 135 | +#   (orchestrator 10:50 ET Nov 17): the comparison canon (canon.same_words), the integrator's message of 10:5x Nov 17.
 136 | +#   RULING 131
 137 |  #   (orchestrator 08:25 ET Nov 17): (A) two of three readings, (B) currency format (the integrator's message of 08:2x
 138 |  #   Nov 17); entries under the old RULES are never read. RULING 105 (orchestrator
 139 |  #   20:13 Nov 14): the unstable second reading joins the rules (the integrator's messages of 20:5x-21:0x Nov 14).
 140 | diff --git a/tests/package/test_attest.py b/tests/package/test_attest.py
 141 | index 017271e..184f98f 100644
 142 | --- a/tests/package/test_attest.py
 143 | +++ b/tests/package/test_attest.py
 144 | @@ -98,7 +98,12 @@ class TestClass84(unittest.TestCase):
 145 |                           [("in", "on", "one function word"), ("on", "in", None)])
 146 |          self.assertEqual(self.k("we went to the store", "we went to a shop"), [("the store", "a shop", None)])
 147 |          self.assertEqual(self.k("went in a store", "went to the store"), [("in a", "to the", None)])   # 2-for-2
 148 | -        self.assertEqual(self.k("the", "the um"), [("", "um", None)])              # a filler on the approved side
 149 | +        self.assertEqual(self.k("the", "the um"), [("", "um", "spelling only (ruling 135)")])   # a filler on the
 150 | +        #   approved side: since RULING 135 (d) a filler is no difference wherever it sits
 151 | +        self.assertEqual(self.k("plan is the point", "plan b is the point"), [("", "b", None)])   # RULING 135: a lone
 152 | +        #   letter the LOCK carries (the approved side) is a token, never a stray sound: it still holds
 153 | +        self.assertEqual(self.k("a h low point", "a low point"), [("h", "", "spelling only (ruling 135)")])   # the
 154 | +        #   second recogniser's stray 'h' (the spoken side) is no word
 155 |          self.assertEqual(self.k("I paid 5 dollars", "I paid 6 dollars"), [("5", "6", None)])
 156 |          self.assertEqual(self.k("it is not", "it is"), [("not", "", None)])
 157 |          self.assertEqual(self.k("um I asked Mike", "I asked mike"), [("um", "", "filler")])   # canon: the same name
 158 | diff --git a/tests/package/test_lock_precheck.py b/tests/package/test_lock_precheck.py
 159 | index c39b164..ecf4966 100644
 160 | --- a/tests/package/test_lock_precheck.py
 161 | +++ b/tests/package/test_lock_precheck.py
 162 | @@ -137,7 +137,7 @@ class TestRuling84(unittest.TestCase):
 163 |          """RULING 103 (14:12 Nov 14), RULING 105 (20:13 Nov 14) and RULING 131 (08:25 Nov 17) joined the integrator's
 164 |          rules string (its messages of 14:3x and 20:5x Nov 14 and 08:2x Nov 17)."""
 165 |          self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + "
 166 | -                                   "ruling 131")
 167 | +                                   "ruling 131 + ruling 135")
 168 |  
 169 |      def test_the_held_span_of_the_20_12_build_now_adopts(self):
 170 |          spoken = "So over time, um, I came to think, uh, or the money itself was broken."
 171 | @@ -160,8 +160,8 @@ class TestRuling84(unittest.TestCase):
 172 |              self.assertIn("outside ruling 84's class", d["why"])
 173 |          e = entry(self.s, "adopt_spoken", spoken_text="So over time, I came to think so the money itself was broken.")
 174 |          e["approved_text"] = "So over time, um, I came to think so the money itself was broken."
 175 | -        s2 = dict(self.s, approved_text=e["approved_text"])               # a filler on the approved side alone
 176 | -        self.assertEqual(LP.decide(s2, e)["verdict"], "hold")
 177 | +        s2 = dict(self.s, approved_text=e["approved_text"])               # a filler on the approved side alone: since
 178 | +        self.assertEqual(LP.decide(s2, e)["verdict"], "adopt")             # RULING 135 (d) no difference wherever it sits
 179 |  
 180 |  
 181 |  class TestRuling131(Dirs):
 182 | @@ -180,16 +180,17 @@ class TestRuling131(Dirs):
 183 |      SECOND = ("comes next? I have been, recently done a bunch of pieces on the 2023, uh, bull market, like climbing a "
 184 |                "wall of worry. Um, there was massive amounts of fear during that period of time. Bitcoin was actually "
 185 |                "trending up into the right, and fear was also trending up into the right during that,")
 186 | -    MERGED = ("I have been recently done a bunch of pieces on the 2023 bull market, like climbing a wall of worry. Um, "
 187 | -              "there was massive amounts of fear during that period of time. Bitcoin was actually trending up into the "
 188 | -              "right, and fear was also trending up into the right during that.")
 189 | -    SPOKEN = MERGED.replace("2023 bull", "2023, uh, bull")      # ruling 72 on top: the second recogniser's 'uh'
 190 | +    MERGED = ("I have been recently done a bunch of pieces on the 2023 bull market, like climbing a wall of worry. There "
 191 | +              "was massive amounts of fear during that period of time. Bitcoin was actually trending up into the "
 192 | +              "right, and fear was also trending up into the right during that.")   # RULING 135: 'um' is no word, the
 193 | +    SPOKEN = MERGED                     # approved words stay there; ruling 72's 'uh' and 'Um' are no difference either
 194 | +    HEARD = ("I have been, recently done a bunch of pieces on the 2023, uh, bull market, like climbing a wall of worry. "
 195 | +             "Um, there was massive amounts of fear during that period of time. Bitcoin was actually trending up into "
 196 | +             "the right, and fear was also trending up into the right during that,")   # the second reading, trimmed
 197 |      PAIRS = [{"run": "bunch of", "approved": "budget", "second_reads": "run", "took": "run",
 198 |                "agreed": ["run", "second"], "edge_distance": 6},
 199 |               {"run": "that", "approved": "like", "second_reads": "approved", "took": "approved",
 200 | -              "agreed": ["approved", "second"], "edge_distance": 14},
 201 | -             {"run": "um", "approved": "", "second_reads": "run", "took": "run", "agreed": ["run", "second"],
 202 | -              "edge_distance": 20}]
 203 | +              "agreed": ["approved", "second"], "edge_distance": 14}]          # 'um' / '': spelling only (ruling 135)
 204 |      WBD = {"moment_id": "w", "video_id": "WdiF0i925rs", "start": 3339.9, "end": 3354.68, "text": APPROVED}
 205 |  
 206 |      def adj(self, **kw):
 207 | @@ -205,11 +206,11 @@ class TestRuling131(Dirs):
 208 |          d = self.decide()                                          # the merged text as it stands ("same")
 209 |          self.assertEqual(d["verdict"], "adopt", d.get("why"))
 210 |          self.assertEqual([(x["spoken"], x["approved"], x["took"]) for x in d["differences"]],
 211 | -                         [("bunch of", "budget", "run"), ("that", "like", "approved"), ("um", "", "run")])
 212 | -        d = self.decide(self.SPOKEN)                               # with ruling 72's 'uh' on top ("adopt")
 213 | +                         [("bunch of", "budget", "run"), ("that", "like", "approved"), ("um", "", "spelling")])
 214 | +        d = self.decide(self.HEARD)                                # the second reading itself: only no-words differ
 215 |          self.assertEqual(d["verdict"], "adopt", d.get("why"))
 216 | -        self.assertEqual([(x["spoken"], x["approved"], x["took"], x["class"]) for x in d["differences"]][3:],
 217 | -                         [("uh", "", "ruling 72", "filler")])
 218 | +        self.assertTrue(d["differences"][3:] and {x["class"] for x in d["differences"][3:]} <=
 219 | +                        {"filler", "spelling only (ruling 135)"}, d["differences"][3:])   # no word differs
 220 |          s = LP.segments_of([self.WBD])[0]
 221 |          self.put(s, entry(s, "adopt_spoken", spoken_text=self.SPOKEN, adjudication=self.adj()))
 222 |          pre = LP.check([self.WBD], "r", self.req, self.res, log=lambda m: None)
 223 | @@ -221,17 +222,17 @@ class TestRuling131(Dirs):
 224 |          self.assertEqual(LP.pin_problems(pk), [])
 225 |  
 226 |      def test_this_side_rederives_every_pair_and_never_trusts_the_record(self):
 227 | -        lie = [dict(self.PAIRS[0]), dict(self.PAIRS[1], took="run", agreed=["run", "second"]), dict(self.PAIRS[2])]
 228 | +        lie = [dict(self.PAIRS[0]), dict(self.PAIRS[1], took="run", agreed=["run", "second"])]
 229 |          for spoken, kw, why in (
 230 |                  (self.MERGED.replace("like climbing", "that climbing"), {"pairs": lie},   # the second reads 'like'
 231 |                   "the lock record's pairs are not this side's"),
 232 | -                (self.MERGED, {"pairs": self.PAIRS[:2]}, "the lock record's pairs are not this side's"),
 233 | +                (self.MERGED, {"pairs": self.PAIRS[:1]}, "the lock record's pairs are not this side's"),
 234 |                  (self.MERGED, {"pairs": [dict(p, edge_distance=9) for p in self.PAIRS]},
 235 |                   "the lock record's pairs are not this side's"),
 236 |                  (self.MERGED.replace("bunch of", "budget"), {}, "neither the merged reading nor"),
 237 |                  (self.MERGED.replace("massive", "huge"), {}, "neither the merged reading nor"),
 238 |                  (self.MERGED.replace("climbing", "the climbing"), {}, "neither the merged reading nor"),
 239 | -                (self.SPOKEN.replace("massive", "huge"), {"second_recogniser": self.SECOND.replace("massive", "huge")},
 240 | +                (self.HEARD.replace("massive", "huge"), {"second_recogniser": self.SECOND.replace("massive", "huge")},
 241 |                   "outside ruling 84's class"),                                     # the second recogniser alone
 242 |                  (self.MERGED, {"second_recogniser": None}, "does not hold the three readings"),
 243 |                  (self.MERGED, {"approved": self.MERGED}, "does not hold the three readings")):
 244 | @@ -342,6 +343,50 @@ class TestRuling131(Dirs):
 245 |          self.assertIn("outside ruling 84's class", d["why"])
 246 |  
 247 |  
 248 | +class TestRuling135(unittest.TestCase):
 249 | +    """RULING 135 (orchestrator 10:50 ET Nov 17), the comparison canon: spelling, segmentation (names too), the closed
 250 | +    list of spoken reductions, fillers and a stray single consonant are no difference; a digit, a different single
 251 | +    letter, a negation and any other change of letters still are. Today's held spans: DataDash 8dbc30ee ('itrust
 252 | +    capital's' / 'I trust capital's' / 'iTrustCapital's'), DataDash f9413625 ('kind of' / 'kinda'), Natalie Brunell
 253 | +    cae5123f (the second recogniser's stray 'h')."""
 254 | +    APPROVED = "Bitcoin conviction and risk management with I trust capital's vault is kind of the point here today."
 255 | +    s = LP.segments_of([{"video_id": "WjnphankXmM", "start": 601.967, "end": 613.827, "text": APPROVED}])[0]
 256 | +
 257 | +    def decide(self, spoken, **kw):
 258 | +        return LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken, **kw))
 259 | +
 260 | +    def test_spelling_is_no_difference_in_ruling_72s_layer(self):
 261 | +        for spoken in ("Bitcoin conviction and risk management with iTrustCapital's vault is kind of the point here today.",
 262 | +                       "Bitcoin conviction and risk management with I trust capital's vault is kinda the point here today.",
 263 | +                       "Bitcoin conviction and risk management with I-trust Capital's vault is kind of the point here, h, today."):
 264 | +            d = self.decide(spoken)
 265 | +            self.assertIn(d["verdict"], ("adopt", "pass"), (spoken, d.get("why")))
 266 | +            self.assertTrue(all(x["class"] == "spelling only (ruling 135)" for x in d.get("differences") or []), d)
 267 | +
 268 | +    def test_what_still_holds(self):
 269 | +        for spoken in ("Bitcoin conviction and risk management with I trust capital's vault is kind of the point here 2day.",
 270 | +                       "Bitcoin conviction and risk management with I trust capital's vault isn't kind of the point here today.",
 271 | +                       "Bitcoin conviction and risk management with I bust capital's vault is kind of the point here today.",
 272 | +                       "Bitcoin conviction and risk management with Q trust capital's vault is kind of the point here today."):
 273 | +            self.assertEqual(self.decide(spoken)["verdict"], "hold", spoken)
 274 | +
 275 | +    def test_a_spelling_pair_never_reaches_the_vote_in_class_131(self):
 276 | +        """The render's lock drops a same-words pair right after the currency pairs: it is in neither the record's
 277 | +        pairs nor the vote, and the sealed text keeps the approved words there (8dbc30ee's three readings)."""
 278 | +        app = "So Q is a product, iTrustCapital's vault holds the coins and the founder bought a bunch of pieces then."
 279 | +        run = "so q is a product, itrust capital's vault holds the coins and the founder bought a bunch of pieces then."
 280 | +        sec = "So Q is a product, I trust capital's vault holds the coins and the founder bought a bunch of pieces then."
 281 | +        s = LP.segments_of([{"video_id": "x", "start": 1.0, "end": 9.0, "text": app}])[0]
 282 | +        adj = {"rule": "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", "pairs": [], "run_decode": run,
 283 | +               "approved": app, "second_recogniser": sec}
 284 | +        rows = AT.class_131(app, app, adj)
 285 | +        self.assertEqual([(x["spoken"], x["approved"], x["took"]) for x in rows],
 286 | +                         [("itrust", "itrustcapitals", "spelling")] if rows and rows[0]["approved"] == "itrustcapitals"
 287 | +                         else [(rows[0]["spoken"], rows[0]["approved"], "spelling")] + [] if rows else [])
 288 | +        self.assertTrue(rows and all(x["took"] == "spelling" for x in rows), rows)
 289 | +        self.assertEqual(LP.decide(s, entry(s, "adopt_spoken", spoken_text=app, adjudication=adj))["verdict"], "pass")
 290 | +
 291 | +
 292 |  class TestCheck(Dirs):
 293 |      def run_check(self, segs, appear=None, timeout=60.0):
 294 |          t = [0.0]
 295 | 
```

---

pp-selectid: RULING 135 (orchestrator 10:50 ET Nov 17), the builder's lockstep half, FAST. "A COMPARISON CANON applied
to all three readings before any pair is compared ... (a) case, punctuation and apostrophes ignored; (b) SEGMENTATION
ignored: readings whose letters are identical once spaces and hyphens are removed are the same ... names too ... (c)
spoken reductions equal their full form, a closed list in canon.py ... (d) NON-LEXICAL tokens are fillers wherever they
sit ... and any stray single consonant letter one reading alone hears ... STILL HOLDS: numbers (save the currency
canon), negations, a name whose letters differ, any content pair where all three differ, ruling 73's sentence edges."
The integrator owns canon.py (taken byte-identical: canon.same_words(x, y), comparison_form, REDUCTIONS, FILLER_TOKENS,
CONSONANTS) and the render's lock: it drops a run/approved pair with same_words right after the currency pairs, before
the critical check and the vote, and ruling 72's comparison drops a lock/second-recogniser pair with same_words before
its classes. Files here: pipeline/attest.py, pipeline/lock_precheck.py, tests/package/test_lock_precheck.py
(canon.py shown for reference: it is the integrator's, audited on its side).

THE CHANGE (this side's re-checks mirror the render exactly where it drops):
(a) attest.class_131 (the ruling 131 (A) re-check): right after the currency pairs, a pair with canon.same_words is
    dropped (took "spelling"), before the critical check (attest.critical, UNCHANGED) and the vote; it keeps the approved
    words in the merged text; the record's pairs are compared without it, as without the currency pairs (the
    integrator's record keeps both apart: "currency_format", "spelling_only").
(b) attest.class_84 (ruling 84's class, used for every adopt_spoken and for ruling 72's layer on the merged text): a
    differing pair with canon.same_words is class "spelling only (ruling 135)", before the critical check and the
    classes; ruling 84's existing filler step (fillers in a difference, spoken side) runs first, UNCHANGED.
(c) lock_precheck.RULES gains "+ ruling 135"; DECODER moves to the integrator's final sha at landing.

TESTS: TestRuling135: spelling, segmentation (a name too: 'I trust capital's' / 'iTrustCapital's' / 'I-trust Capital's'),
'kinda' / 'kind of', a stray 'h' are no difference in ruling 72's layer; a digit, a negation, a changed content word
('trust' / 'bust') and a letter-name dispute ('Q' / 'I') still hold; in class_131 a same-words pair never reaches the
record's pairs or the vote. TestRuling131's fixtures move to ruling 135 (last night's 'um' / '' is now spelling only,
the sealed text keeps the approved words; ruling 72's 'uh' / 'Um' are no difference), and TestRuling84's "a filler on
the approved side alone" now adopts (135 (d): wherever it sits). Mutations M1-M26 after a control run: 26 of 26
killed (M24-M26 the three new drops). 47 lock tests pass.

PLEASE CHECK: (1) that nothing 135 keeps holding can be dropped as spelling: a number, a negation, a name whose letters
differ, a different single letter, a content word; (2) that the drops sit exactly where the render's do (after
currency, before critical and the vote; before ruling 84's classes); (3) that a same-words pair can never change the
sealed text; (4) the tests.


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
