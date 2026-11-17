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

- **TestRuling135** (new): 3 test methods covering spelling/segmentation/reduction/stray-consonant (no difference) and digit/negation/content-word/letter-name (still holds), plus the class_131 vote-exclusion path. All assertions are concrete and non-tautological (except the one [P3] noted above). ✓
- **TestRuling131** (updated): fixtures moved to RULING 135 semantics; the old `"um"/""` pair is now `"spelling"`; `HEARD` replaces `SPOKEN` for the second-reading test; the `lie` mutation list drops the now-spelling pair. The "this side rederives every pair" test still catches a tampered `took`, a missing pair, a wrong `edge_distance`, and a content-word substitution. ✓
- **TestRuling84** (updated): the "filler on the approved side alone" case now expects `"adopt"` (was `"hold"`), correctly reflecting RULING 135(d) "wherever it sits." ✓
- **RULES string test**: matches the new constant. ✓
- Mutation coverage: 26/26 killed (M24–M26 are the three new drop sites). ✓

---

## Law Compliance

| Law | Status |
|---|---|
| L-k (one canonical form) | `same_words` lives in `canon.py`, operates on canon tokens, is the single comparison point. ✓ |
| L-l (model reply counts only whole) | Not affected; no model call in this path. ✓ |
| LAW 20 / M2 (thresholds are constants; no reclassification) | RULING 135 defines a new *class* of non-difference; it does not lower a threshold or reclassify a failing gate. The "still holds" set is explicitly enumerated and tested. ✓ |
| M12 (fail closed) | `same_words` is a pure function; no external I/O; an exception would propagate and block. ✓ |
| LAW 22 (v2f byte-identical) | Not touched. ✓ |
| Smallest diff / M1 | No new renderer, compositor, or selector. Three files modified, one test file. ✓ |

---

P1_OR_WORSE: 0