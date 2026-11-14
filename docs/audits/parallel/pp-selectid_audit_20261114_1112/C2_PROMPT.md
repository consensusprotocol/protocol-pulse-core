# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_1112
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 466 s finish=stop usage in 8881 / out 13166 usd~0.224 (upper-bound price)

<critical>
None found.

</critical>

<high>
**H1. `without_manifest_date` silently returns the text unchanged on a malformed manifest date — but the test's "no date" case passes a dict without the key, not a malformed value, and the ruling says the date must equal the manifest's.** vo_fidelity.py:46-48. `date.fromisoformat(str((manifest or {}).get("date") or ""))` raises only `ValueError`; `str(None)` → `"None"` → `ValueError` → return `text or ""`. That part is fine. But note the failure mode: a manifest with `"date": "2026-11-12T00:00:00"` (ISO datetime, plausible from a real manifest) — `date.fromisoformat` in Python 3.11+ accepts it and returns 2026-11-12, so the date is stripped. That's actually correct behavior. The real gap: **`TypeError` is not caught**. If `manifest` is a non-dict truthy object (e.g. a list `[("date","2026-11-12")]`), `.get` raises `AttributeError`/`TypeError` inside `check_deterministic`, which per M12 must fail closed — but here the exception propagates out of the deterministic layer. Whether that's a violation depends on whether `check_deterministic`'s caller catches. Not verifiable from the diff. Downgrade risk: the ruling says "no manifest date: the text as it is", and the test only covers a missing key, not a malformed string like `"date": "12/11/2026"` → `ValueError` → text unchanged → the date's digits are then read by NUMBER → a must-pass case ("Pulse Check for 2026-11-12." with a US-format manifest date) fails. Concrete input: `man = {"date": "11/12/2026"}`; `"Pulse Check for 2026-11-12."` → NUMBER+NEEDS_SOURCE. Whether real manifests use ISO is not verifiable from the diff.

</high>

<high>
**H2. The written-date regex's `(?![\w.]?\d)` lookahead lets a date inside a larger number escape, and the ISO alternative's `(?![\w-])` lets `2026-11-120` partially match — but the test at test_gates.py:110-111 asserts the opposite, so one of them is wrong.** vo_fidelity.py:50-51.

Written form: `(?![\w.]?\d)` after the day. For "November 120": month matches "November", day `0?{d.day}` matches "12", then lookahead: next char is "0", `[\w.]?` matches "0"? No — `[\w.]?` is one char, "0" is `\w`, so it matches, then `\d` needs a digit after it — end of string, fails; backtrack: `[\w.]?` matches empty, `\d` matches "0" → lookahead succeeds → the match is "November 12" inside "November 120", leaving "0" behind. So "November 120" → " 0" remains → NUMBER sees 0, not 120. The test at :110-111 asserts the NUMBER detail's first token is "120". **Contradiction unless fact_numbers reads "0" as... no, it would report "0"**. Wait — the test asserts `["120"]`. Let me recheck: after sub, text = "We stopped at  0." — fact_numbers reads "0", detail starts "0 ...". Test expects "120". So either the regex is right and the test fails, or... Actually recheck the lookahead: `(?![\w.]?\d)` — for "November 120", after matching "November 12", remaining is "0". Try `[\w.]?` = "0", then `\d` — nothing left → fail. Try `[\w.]?` = empty, then `\d` = "0" → succeeds → negative lookahead FAILS → so the match at day=12 fails; regex backtracks: `0?` can match empty, day "1"? No, `{d.day}` is literal "12". So the whole written alternative fails at that position... then the ISO alternative: "November 120" doesn't contain "2026-11-12". So **no match at all** → "November 120" stays whole → NUMBER reads 120. Test passes. Good — the lookahead does its job. Now ISO: "2026-11-120": `2026-11-12` matches, then `(?![\w-])` — next char "0" is `\w` → fails → backtrack... no shorter ISO match. So "2026-11-120" stays whole → NUMBER reads 120. Test at :105 expects NUMBER for "2026-11-120" — passes. And "November 12, 2025": written matches "November 12" (year part optional, 2025≠2026 so the year group fails, but it's optional) → "November 12" stripped, ", 2025" remains → NUMBER reads 2025 → NUMBER+NEEDS_SOURCE. Test :104 expects both. Consistent. So H2 downgrades to: the mechanism works, but note "November 12, 2025" leaves "2025" as a NUMBER violation — the ruling says "never a bare number" and "only when it equals the manifest's date", so a 2025 year alone being flagged is arguably correct per ruling. No bug. **Withdrawn as a finding; noted as verified-correct.**

</high>

<high>
**H3. NEEDS_SOURCE and the NUMBER loop now read *different* texts when the line's date spans a chunk boundary — no, they read the same function, but the two call sites can disagree when the date's day is the last token of a chunk.** vo_fidelity.py:62-63 vs :72. `_governed` splits at sentence ends; "Pulse Check for November 12. Next sentence $40M." → NEEDS_SOURCE reads the whole line, date stripped → no NEEDS_SOURCE. The NUMBER loop reads each chunk: chunk 1 = "Pulse Check for November 12." → stripped → no number → no NUMBER. Consistent. But: "November 12, 2026" — the written form with the manifest's year: the regex's year part is `(?:,?\s+{d.year})

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 61 s finish=stop usage in 8949 / out 205 usd~0.050 (upper-bound price)

<critical> vo_fidelity.py:39 (without_manifest_date) + :62/:72/:81 (fact_numbers calls): concrete input "Pulse Check for 2026-11-12." (manifest={"date": "2026-11-12", ...}) now yields no NUMBER/NEEDS_SOURCE after date removal (see added test lines 102-103, 112); previously triggered per background. Violates LAW 20/M2 ("never change what a check accepts to make a render pass; never reclassify a failing gate as a false positive").
<medium> ledger_build.py:24 (b - a > SNAP_MAX_S): with new 35.0 ceiling + test input of 75-word / 22.5 s snap (test_ledger_build.py:143), reanchor now returns non-None (line 144); facts confirm medley usable() still drops at 20 s but cannot verify downstream hook/clip/scorer assumptions from diff+facts alone.

SHIP: no

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 26 s finish=stop usage in 9743 / out 1821 usd~0.057 (upper-bound price)

I have reviewed the diff against the governing laws, the orchestrator's rulings, and the provided background facts. Here are the findings.

### Findings

**<high> Ruling (2) Implementation: `SNAP_MAX_S` Decoupling Risk**
*   **File:** `pipeline/ledger_build.py:9-11`
*   **Issue:** The change hardcodes `SNAP_MAX_S = 35.0` with a comment referencing `spotlight.SPOT_S[1]`. However, the code does not import or reference `spotlight.SPOT_S`. If `spotlight.SPOT_S` is ever changed (e.g., to 40s), `ledger_build.py` will silently retain the 35s ceiling, violating the intent of "the read's snap ceiling is the spotlight's".
*   **Verification:** The test `test_the_snap_ceiling_is_the_spotlights_and_the_medley_keeps_its_own_20_s` (line 134) asserts `LB.SNAP_MAX_S == SPOT.SPOT_S[1]`. This test will catch a drift, but the production code itself is fragile.
*   **Recommendation:** Import `spotlight` and set `SNAP_MAX_S = spotlight.SPOT_S[1]` to ensure single-source-of-truth.

**<medium> Ruling (3) Regex Edge Case: `without_manifest_date`**
*   **File:** `pipeline/vo_fidelity.py:50`
*   **Issue:** The regex for written dates is:
    `rf"\b{month}\s+0?{d.day}(?:st|nd|rd|th)?(?:,?\s+{d.year})?(?![\w.]?\d)"`
    The negative lookahead `(?![\w.]?\d)` is intended to prevent matching "November 12" inside "November 120". However, `\w` includes digits. If the text is "November 12.5" (a decimal), the lookahead `(?![\w.]?\d)` sees `.` (which matches `[\w.]?`) and then `5` (which matches `\d`), so it fails to match. This is correct.
    But consider "November 12, 2026". The regex allows `,?\s+{d.year}`. If the manifest date is `2026-11-12`, `d.year` is `2026`. The regex will match "November 12, 2026".
    What if the text is "November 12, 20261"? The lookahead `(?![\w.]?\d)` after the optional year group. If the year group matches `2026`, the next char is `1`. `[\w.]?` can match empty, then `\d` matches `1`. Lookahead fails. Correct.
    **Potential Bug:** The ISO date regex is `re.escape(d.isoformat())`. `d.isoformat()` is `2026-11-12`. The regex is `(?<![\w-])2026\-11\-12(?![\w-])`.
    If the text is "2026-11-120", the lookahead `(?![\w-])` sees `0`. `0` is `\w`. Lookahead fails. Correct.
    If the text is "12026-11-12", the lookbehind `(?<![\w-])` sees `2`. `2` is `\w`. Lookbehind fails. Correct.
    **However**, the test case `test_number_takes_the_manifests_own_show_date_whole_and_nothing_else` (line 105) includes `"Pulse Check for 2026-11-120."` as a `bad` case (expecting NUMBER violation). The regex correctly fails to match `2026-11-12` in `2026-11-120` because of the trailing `0`. So `fact_numbers` will see `2026-11-120` as a number. This is correct behavior.
    **Wait**, look at line 111: `self.assertEqual([x["detail"].split()[0] for x in v["violations"] if x["rule"] == "NUMBER"], ["120"])`.
    The input is `"We stopped at November 120."`. The manifest date is `2026-11-12`.
    The regex for written date: `\b(November|Nov)\s+0?12(?:st|nd|rd|th)?(?:,?\s+2026)?(?![\w.]?\d)`.
    In "November 120", it tries to match "November 12". The next char is `0`. The lookahead `(?![\w.]?\d)` checks if the next char is a digit. `0` is a digit. So the match fails.
    Therefore, "November 120" is NOT removed. `fact_numbers` sees "120". The violation detail is "120". This matches the test expectation.
    **Conclusion:** The regex logic appears sound for the provided tests.

**<medium> Ruling (3) `strict_features` Consistency**
*   **File:** `pipeline/vo_fidelity.py:81`
*   **Issue:** `strict_features` now uses `without_manifest_date`. The test (line 112-114) verifies that `strict_features` returns `[]` for the manifest date and `["a number"]` for a different date. This is consistent with the `NUMBER` rule.
*   **Verification:** The background states: "a 'production' claim must cite the manifest and carry no strict feature". If the VO line is "Pulse Check for 2026-11-12." and it is a production claim, `strict_features` returns `[]`, so it passes the "no strict feature" check. This is the intended behavior.

**<low> Test Coverage for `without_manifest_date`**
*   **File:** `tests/package/test_gates.py:93-114`
*   **Issue:** The tests cover ISO, written, ordinal, year, and negative cases. They do not explicitly test a missing manifest date (line 109 covers `{"show": "Pulse Check"}` which has no `date` key). The function handles this by returning the text unchanged (line 48). This is correct.

### SHIP: yes with conditions

**Conditions:**
1.  **Refactor `SNAP_MAX_S`:** Change `pipeline/ledger_build.py` to import `spotlight` and set `SNAP_MAX_S = spotlight.SPOT_S[1]` instead of hardcoding `35.0`. This ensures the "spotlight's ceiling" is truly dynamic and prevents drift if `SPOT_S` changes.
2.  **Verify `spotlight` Import:** Ensure `spotlight` is importable in `ledger_build.py` without circular dependencies. If `spotlight` imports `ledge

## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 1112 (the orchestrator's 10:48 rulings (2) the snap ceiling, (3) NUMBER and the show date), cycle 1: consensus

**Folder:** this audit ran as label 1112 into docs/audits/parallel/pp-selectid_audit_1112, which already held the Nov 13 11:12 audit of rulings 58 + 59 (commit 5cb00867). The labels are times of day, so they collide across days. Its tracked files were restored from git before anything was committed, and this audit moved here under a dated label. Cycle 1's prompt and diff name the old path as they were sent.

Reviewers:
- grok-4.20: SHIP no. One <critical> (refuted: the change is the ruling) and one <medium> (answered from the code).
- qwen3.8-27b: SHIP yes with conditions. One <high> (refuted), two <medium> that verify the regex and strict_features
  as correct.
- glm-5.3-flash (466 s): SHIP yes with conditions:
  - the locale of the month names (implemented);
  - no third reader of SNAP_MAX_S (verified);
  - the manifest date's format (verified);
  - the medley's downstream with a 21-35 s moment (answered: it never reaches one).
  Its H1-H6 resolve inside its own text, and M1-M4 are recorded below.

Upper-bound cost: about $0.39 ($0.050 + qwen's + $0.224). Outside SPEND_LY.json.

## Implemented

- glm M2: without_manifest_date built its month pattern with strftime('%B') / ('%b'), which follow the process locale.
  Under a non-English LC_TIME, 'November 12' would no longer be taken out, and the 30 dated sign-offs would fail again.
  Now a literal English table (vo_fidelity.MONTHS) gives the month and its 3-letter form, whatever the locale. The 9
  mutations are still all killed. 57 tests in the two suites pass.

## Verified from the code (glm's and grok's conditions)

- "No other reader of SNAP_MAX_S assumes 20 s" (glm, grok <medium>): grep over pipeline/, tests/ and scripts/ finds it
  only in ledger_build.py (the docstring, the constant, the check and its reason) and test_ledger_build.py.
- "Can a 21-35 s moment reach a MEDLEY?" (grok <medium>, glm): no.
  - package.usable(..., seg_max=SEG_MAX_S) (package.py:162; SEG_MAX_S = 20.0 at :67) drops any moment over 20 s before
    any medley stage: angles, step A, cut, hook rule, scorer candidates.
  - The spotlight already takes 12-35 s moments by ruling 90: usable(..., seg_max=SPOT_S[1]) at spotlight.py:196, :217.
    Its stages (cut, onset, ALONE scorer, layout) have run on moments up to 35 s since 22:40 Nov 13.
  - The first build after this lands is the live check: its log shows what snapped past 20 s and where it stopped.
- The manifest date's format (glm H1, M3): the packager's manifest and every exam case carry "YYYY-MM-DD". A date that
  date.fromisoformat cannot read leaves the text as it is, which is the stricter old behaviour (its digits are numbers
  again), never a looser one. (This machine runs Python 3.10, whose fromisoformat reads only YYYY-MM-DD.)

## Refuted, with evidence

- grok <critical>: "LAW 20 / M2: never change what a check accepts to make a render pass".


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261114_1112/C2_STEP.diff (162 lines)
```
   1 | diff --git a/pipeline/ledger_build.py b/pipeline/ledger_build.py
   2 | index 71411d3..88a255b 100644
   3 | --- a/pipeline/ledger_build.py
   4 | +++ b/pipeline/ledger_build.py
   5 | @@ -43,10 +43,12 @@ import sentence_law as SL
   6 |  import transcript_store as ts
   7 |  import vo_fidelity as VF          # snap_risk's price mentions (pure Python; at module level: audit 0332 C2, grok + qwen)
   8 |  
   9 | -SNAP_MAX_S = 20.0         # RULING 32 (orchestrator 02:45 ET Nov 13): a row whose anchored text is not whole sentences
  10 | +SNAP_MAX_S = 35.0         # THE ORCHESTRATOR'S 10:48 RULING (2), Nov 14: the read's snap ceiling is the spotlight's 35 s
  11 | +                          # (spotlight.SPOT_S[1]); the medley's own 20 s stays in package.usable (SEG_MAX_S, L-u).
  12 | +                          # Before it, 20 s here dropped rows of 21-23 s before the spotlight's ceiling could apply.
  13 | +                          # RULING 32 (orchestrator 02:45 ET Nov 13): a row whose anchored text is not whole sentences
  14 |                            # is SNAPPED OUTWARD to the word record's whole sentences, instead of dropped, when the
  15 | -                          # snapped span stays inside the clip length limit (= package.SEG_MAX_S, L-u) and shows no
  16 | -                          # speaker change. The added words are the speaker's own, so nothing is changed by omission;
  17 | +                          # snapped span stays inside this ceiling and shows no speaker change. The added words are the speaker's own, so nothing is changed by omission;
  18 |                            # the snapped span is judged as usual: step A (L-s), the exclusion verdict (every L-u risk),
  19 |                            # L-v 2 (every number and negation both ways, exactly one speaker measured) and usable() (time
  20 |                            # words). It replaces SNAP_WORDS = 3 and SNAP_GUARD (audit 2315 C1), whose concern was words
  21 | @@ -402,7 +404,8 @@ def reanchor(row, src, cap=None):
  22 |          if a is None or b is None:
  23 |              return None, f"{snap}, its length is not measured (a word time is missing)"
  24 |          if b - a > SNAP_MAX_S:
  25 | -            return None, f"{snap} it runs {b - a:.2f} s > {SNAP_MAX_S:.0f} s (ruling 32: the clip length limit)"
  26 | +            return None, (f"{snap} it runs {b - a:.2f} s > {SNAP_MAX_S:.0f} s (ruling 32 with the 10:48 ruling (2): "
  27 | +                          f"the spotlight's clip ceiling)")
  28 |          t = marker_inside(cap if cap is not None else getattr(src, "context_source", None), a, b)
  29 |          if t is not None:
  30 |              return None, f"{snap} it holds a caption speaker marker at {t:.2f} s: a measured speaker change (ruling 32)"
  31 | diff --git a/pipeline/vo_fidelity.py b/pipeline/vo_fidelity.py
  32 | index d0bb83c..010a13e 100644
  33 | --- a/pipeline/vo_fidelity.py
  34 | +++ b/pipeline/vo_fidelity.py
  35 | @@ -414,6 +414,26 @@ def time_words(text, meta=()):
  36 |      return out
  37 |  
  38 |  
  39 | +MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
  40 | +          "December")
  41 | +
  42 | +
  43 | +def without_manifest_date(text, manifest=None):
  44 | +    """THE ORCHESTRATOR'S 10:48 RULING (3), Nov 14: NUMBER accepts the manifest's OWN show date as production metadata,
  45 | +    the WHOLE date only ('2026-11-12', 'November 12', 'Nov 12'; a written date may carry its ordinal, 'November 12th',
  46 | +    and the manifest's own year, 'November 12, 2026'), never a bare number, and only when it equals the manifest's date.
  47 | +    -> the text with each such date taken out; everything else is read as before. No manifest date: the text as it is."""
  48 | +    from datetime import date
  49 | +    try:
  50 | +        d = date.fromisoformat(str((manifest or {}).get("date") or ""))
  51 | +    except ValueError:
  52 | +        return text or ""
  53 | +    name = MONTHS[d.month - 1]                           # English, whatever the process locale (audit 1112 C1, glm)
  54 | +    month = rf"(?:{name}|{name[:3]})"                    # 'Nov.' is not one: its period ends a sentence
  55 | +    written = rf"\b{month}\s+0?{d.day}(?:st|nd|rd|th)?(?:,?\s+{d.year})?(?![\w.]?\d)"
  56 | +    return re.sub(rf"(?<![\w-]){re.escape(d.isoformat())}(?![\w-])|{written}", " ", text or "", flags=re.I)
  57 | +
  58 | +
  59 |  def fact_numbers(text, meta_nums=frozenset()):
  60 |      """The numbers of a text that state a fact, [(value, unit)]: leaves out the package's own count beside a production
  61 |      noun ('three voices') and 'one' written as a word (a determiner or pronoun: 'one thing', 'one of')."""
  62 | @@ -454,7 +474,8 @@ def check_deterministic(segments, lines, manifest=None, current_levels=None):
  63 |          names = names_of(text, meta)
  64 |          quotes = [q for pair in _QUOTE.findall(text) for q in pair if q]
  65 |          times = time_words(text, meta)
  66 | -        if (fact_numbers(text, meta_nums) or names or quotes or atts or times) and not cited:
  67 | +        if (fact_numbers(without_manifest_date(text, manifest), meta_nums) or names or quotes or atts or times) \
  68 | +                and not cited:                                       # the 10:48 ruling (3): the show date needs none
  69 |              V("NEEDS_SOURCE", "a line with a number, name, quote, attribution or time word cites no segment")
  70 |          pools = []                                                   # per attribution: the governing segments
  71 |          for subj0, form, _ in atts:
  72 | @@ -499,7 +520,7 @@ def check_deterministic(segments, lines, manifest=None, current_levels=None):
  73 |          for chunk, ai in _governed(text, atts):
  74 |              gov = pools[ai] if ai is not None and pools[ai] else cited
  75 |              gpool = [t for c in gov for t in seg_toks[c]]
  76 | -            for val, unit in fact_numbers(chunk, meta_nums):
  77 | +            for val, unit in fact_numbers(without_manifest_date(chunk, manifest), meta_nums):   # 10:48 ruling (3)
  78 |                  if not _has_number(gpool, val, unit):
  79 |                      V("NUMBER", f"{val}{' ' + unit if unit else ''} is not in the cited sentences" +
  80 |                        (" of the attributed speaker / show" if ai is not None and pools[ai] else ""))
  81 | @@ -610,7 +631,7 @@ def strict_features(words, segments, manifest=None, production=False):
  82 |      word, 'as X put it'. -> [feature, ...] (empty: the words may be commentary)."""
  83 |      meta, meta_nums = manifest_terms(segments, manifest)
  84 |      out = []
  85 | -    if fact_numbers(words, meta_nums):
  86 | +    if fact_numbers(without_manifest_date(words, manifest), meta_nums):     # the 10:48 ruling (3): the show date
  87 |          out.append("a number")
  88 |      if names_of(words, meta):
  89 |          out.append(f"a name ({', '.join(names_of(words, meta)[:3])})")
  90 | diff --git a/tests/package/test_gates.py b/tests/package/test_gates.py
  91 | index c0a2d96..cbe3582 100644
  92 | --- a/tests/package/test_gates.py
  93 | +++ b/tests/package/test_gates.py
  94 | @@ -300,6 +300,29 @@ class TestDeterministicRules(unittest.TestCase):
  95 |          self.assertIn("IMPERATIVE", self.rules("It's time to buy.", ["m1"]))
  96 |          self.assertEqual(self.rules("Short-term holders are selling.", ["m1"]), set())
  97 |  
  98 | +    def test_number_takes_the_manifests_own_show_date_whole_and_nothing_else(self):
  99 | +        """The orchestrator's 10:48 ruling (3), Nov 14: NUMBER accepts the manifest's own show date as production
 100 | +        metadata, the WHOLE date only, never a bare number, and only when it equals the manifest's date."""
 101 | +        man = {"date": "2026-11-12", "show": "Pulse Check", "channels": ["Coin Bureau"]}
 102 | +
 103 | +        def rules(text, m=man):
 104 | +            return {v["rule"] for v in VF.check_deterministic(self.SEGS, [{"slot": "signoff", "text": text,
 105 | +                                                                           "cites": []}], m)["violations"]}
 106 | +        for ok in ("Pulse Check for 2026-11-12.", "Pulse Check for November 12.", "Pulse Check, Nov 12.",
 107 | +                   "Pulse Check for November 12, 2026.", "That's Pulse Check, november 12th."):
 108 | +            self.assertEqual(rules(ok), set(), ok)                 # no NUMBER, and no NEEDS_SOURCE for it either
 109 | +        for bad in ("Pulse Check for 2026-11-13.", "Pulse Check for November 13.", "Pulse Check number 12.",
 110 | +                    "Pulse Check for 12.", "Pulse Check for November 12, 2025.", "Pulse Check for 2026-11-120.",
 111 | +                    "Pulse Check, Nov. 12."):                      # (the abbreviation's period ends a sentence)
 112 | +            self.assertIn("NUMBER", rules(bad), bad)
 113 | +            self.assertIn("NEEDS_SOURCE", rules(bad), bad)
 114 | +        self.assertIn("NUMBER", rules("Pulse Check for 2026-11-12.", {"show": "Pulse Check"}))   # no date: as before
 115 | +        v = VF.check_deterministic(self.SEGS, [{"slot": "x", "text": "We stopped at November 120.", "cites": []}], man)
 116 | +        self.assertEqual([x["detail"].split()[0] for x in v["violations"] if x["rule"] == "NUMBER"], ["120"])
 117 | +        self.assertEqual(VF.strict_features("Pulse Check for 2026-11-12", self.SEGS, man, production=True), [])
 118 | +        self.assertEqual(VF.strict_features("Pulse Check for 2026-11-13", self.SEGS, man, production=True),
 119 | +                         ["a number"])                      # the verdict layer's production claim reads it the same
 120 | +
 121 |      def test_price_now_reads_history_forecasts_and_counts(self):
 122 |          self.assertIn("PRICE_NOW", self.rules("Bitcoin just set an all-time high at $126,000.", ["m1"], [73000.0]))
 123 |          self.assertIn("PRICE_NOW", self.rules("Since 2022, Bitcoin is at $126,000.", ["m1"], [73000.0]))
 124 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 125 | index 3c96174..2f4a7a3 100644
 126 | --- a/tests/package/test_ledger_build.py
 127 | +++ b/tests/package/test_ledger_build.py
 128 | @@ -82,18 +82,28 @@ class TestReanchor(unittest.TestCase):
 129 |              sp, info = LB.reanchor(row("anyone can stop Bitcoin from settling a payment."), src)
 130 |              self.assertEqual(info["added"]["before"], word)
 131 |  
 132 | -    def test_the_snap_limit_is_the_packagers_clip_limit(self):                 # audit 0332 C1, qwen P2-1
 133 | +    def test_the_snap_ceiling_is_the_spotlights_and_the_medley_keeps_its_own_20_s(self):
 134 | +        """The orchestrator's 10:48 ruling (2), Nov 14: the read's snap ceiling is 35 s (spotlight.SPOT_S[1]); the
 135 | +        medley's own 20 s stays in package.usable (SEG_MAX_S)."""
 136 |          import package as PK
 137 | -        self.assertEqual(LB.SNAP_MAX_S, PK.SEG_MAX_S)
 138 | +        import spotlight as SPOT
 139 | +        self.assertEqual((LB.SNAP_MAX_S, SPOT.SPOT_S[1], PK.SEG_MAX_S), (35.0, 35.0, 20.0))
 140 |  
 141 | -    def test_a_snap_longer_than_20_s_stays_out(self):
 142 | -        long_ = "Bitcoin " + " ".join(["keeps"] * 72) + " settling payments."             # 75 words, 0.3 s each
 143 | +    def test_a_snap_of_21_to_35_s_is_read_and_one_longer_than_35_s_stays_out(self):
 144 | +        mid = "Bitcoin " + " ".join(["keeps"] * 72) + " settling payments."              # 75 words: 22.5 s
 145 | +        src = source([mid, "That is the plan."])
 146 | +        a, b = src.sentences[0]
 147 | +        self.assertGreater(src.tokens[b]["end"] - src.tokens[a]["start"], 20.0)
 148 | +        sp, info = LB.reanchor(row(" ".join(["keeps"] * 8) + " settling payments."), src)
 149 | +        self.assertIsNotNone(sp)                                      # read now (the medley's usable() drops it)
 150 | +        self.assertEqual(info["snapped_words"][0], 65)
 151 | +        long_ = "Bitcoin " + " ".join(["keeps"] * 122) + " settling payments."           # 125 words: 37.5 s
 152 |          src = source([long_, "That is the plan."])
 153 |          a, b = src.sentences[0]
 154 |          self.assertGreater(src.tokens[b]["end"] - src.tokens[a]["start"], LB.SNAP_MAX_S)
 155 |          sp, why = LB.reanchor(row(" ".join(["keeps"] * 8) + " settling payments."), src)
 156 |          self.assertIsNone(sp)
 157 | -        self.assertIn("> 20 s (ruling 32", why)
 158 | +        self.assertIn("> 35 s (ruling 32 with the 10:48 ruling (2)", why)
 159 |          sp, info = LB.reanchor(row(long_), src)                       # whole sentences: no snap, usable() measures it
 160 |          self.assertEqual(info["snapped_words"], [0, 0])
 161 |  
 162 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff and the facts below; if uncertain, say so; do not guess. Be specific: file:line and a concrete
input that breaks it.

BACKGROUND (static):
- The builder reads a miner's ledger of candidate moments (pipeline/ledger_build.py). A row whose anchored text is not
  whole sentences is SNAPPED OUTWARD to the word record's whole sentences (ruling 32), when the snapped span stays
  inside a ceiling and holds no caption speaker marker; otherwise the row is dropped. Two products use the moments: the
  MEDLEY (hook + 2-4 clips; at most 20 s per source video, law L-u) and the SPOTLIGHT (one moment of 12-35 s, ruling 90).
- pipeline/vo_fidelity.py judges every VO line, the title and the caption. Its deterministic layer includes NUMBER
  (every number in a line is in the sentences it cites) and NEEDS_SOURCE (a line with a fact - a number, name, quote,
  attribution or time word - cites at least one segment). Production metadata (the credited shows, the show, the
  date's month and weekday names, the package's own counts) may be stated without a citation. The model-verdict layer
  labels each claim; a "production" claim must cite the manifest and carry no strict feature (strict_features: "a
  number", a name, ...).

UNCHANGED CODE THIS CHANGE RELIES ON (not in the diff; verify against these facts, do not assume them away):
- package.usable(moments, ctx, ..., seg_max=SEG_MAX_S) (package.py:162) drops a moment longer than seg_max; SEG_MAX_S
  = 20.0 (package.py:67) is the medley's default. The spotlight calls usable(..., seg_max=SPOT_S[1]) (spotlight.py:196,
  :217) with SPOT_S = (12.0, 35.0) (spotlight.py:53). So the medley keeps its own 20 s whatever the read lets in.
- vo_fidelity._governed(text, atts) (:352) splits a line into chunks at sentence ends (and attributions); the NUMBER
  check reads each chunk. NEEDS_SOURCE reads the whole line.
- vo_fidelity.manifest_terms (:276) admits the show date's month / weekday NAMES as production metadata, not its digits.
- vo_fidelity.check (:740) ALWAYS asks the model verdict, whatever the deterministic layer found; the deterministic
  layer is code, so a change to it applies at scoring time without new model calls.

THE ORCHESTRATOR'S RULINGS (10:48 ET Nov 14), verbatim:
"(2) YES: the ledger read's snap ceiling is 35 s; the medley's own 20 s stays in package.usable.
 (3) YES: vo_fidelity's NUMBER rule accepts the manifest's own show date as production metadata, the WHOLE date only
 ('2026-11-12', 'November 12', 'Nov 12'), never a bare number, and only when it equals the manifest's date. pp-tests
 keeps its 30 cases."
Context: before (2), the read dropped rows whose snap ran 21-23 s before the spotlight's 35 s ceiling could apply.
Before (3), "Pulse Check for 2026-11-12." (the manifest's own date) failed NUMBER in 16 of pp-tests' 40 must-pass VO
cases, and gave 14 must-fail cases a rejection for the wrong reason.

THE CHANGE (the diff follows):
1. ledger_build.SNAP_MAX_S 20.0 -> 35.0 (= spotlight.SPOT_S[1]); its comment and the drop reason say so. Tests: the
   ceiling equals the spotlight's while the medley's SEG_MAX_S stays 20; a 22.5 s snap is now read; a 37.5 s one stays
   out.
2. vo_fidelity.without_manifest_date(text, manifest): takes out of a text the manifest's OWN date, whole: ISO
   ('2026-11-12'), or written ('November 12' / 'Nov 12', an optional ordinal 'th', an optional ', 2026' of the
   manifest's year), case-insensitive, never followed by another digit; no manifest date: the text as it is. 'Nov.' is
   NOT accepted (its period ends a sentence in _governed, so the day would be read alone). It is applied at the three
   places a number is read for this purpose: the NUMBER loop (each chunk), NEEDS_SOURCE (the whole line) and
   strict_features (a production claim's words). Tests: the five accepted forms give NO violation; a different day, a
   bare '12', 'number 12', a different year, '2026-11-120' and 'Nov. 12' are still NUMBER and NEEDS_SOURCE; no manifest
   date: as before; strict_features agrees; a longer number keeps its whole value ('120'). 9 mutations, each killed;
   20 suites, 570 tests.

ATTACK:
(a) Ruling (2): can a moment of 21-35 s now reach a MEDLEY? Does anything between the read and package.usable assume
    20 s (a cut, a hook rule, the clip scorer, the candidate registry)? Can a snap now cross a speaker change?
(b) Ruling (3): can any number OTHER than the manifest's own whole date escape NUMBER or NEEDS_SOURCE (a price, a count,
    a day alone, another date, a date inside a larger number, a date in a quote)? Is 'November 12, 2025' handled? A
    malformed or missing manifest date? Can the change make a must-fail case pass by construction?
(c) Anything else that could seal a wrong pin or score the exam wrongly.

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete input), then
"SHIP: yes / no / yes with conditions".


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
