# qwen3.8-27b (qwen/qwen3.8-27b) 230 s finish=stop usage in 9409 / out 8485 usd_reported=0.007305 usd~0.156 (upper-bound price)



# Code Audit — pp-selectid / RULING 155 (1)

## Findings

### [P1] `kind_sentences` will raise `KeyError` for any soft/edge code absent from the `_MANY` dicts when it appears on ≥ 2 clips

**Location:** `pipeline/package.py`, `kind_sentences`, line 37 of the diff:

```python
out.append(f"{COUNT_WORDS.get(len(lbs), str(len(lbs)))} clips ({chans}): "
           f"{STEP_A_SOFT_MANY.get(c) or EDGE_WORDS_MANY[c]}.")
```

The original `flag_sentence` falls back through `STEP_A_SOFT.get(code) or EDGE_WORDS[code]` — two dicts that together cover every code the pipeline can emit. The new multi-clip path falls back through `STEP_A_SOFT_MANY.get(c) or EDGE_WORDS_MANY[c]`. `STEP_A_SOFT_MANY` has exactly four keys (NOT_OWN_SINCERE, REFERENT_OUTSIDE, CONDITION_OUTSIDE, UNCERTAIN) and `EDGE_WORDS_MANY` has two (EDGE_IN, EDGE_OUT). If `STEP_A_SOFT` (or `EDGE_WORDS`) contains any additional code — a new soft code added later, a legacy code, a code the orchestrator introduces — and that code lands on two or more clips, `STEP_A_SOFT_MANY.get(c)` returns `None`, the `or` evaluates `EDGE_WORDS_MANY[c]`, and the pipeline crashes with `KeyError`.

The crash is fail-closed (M12) so no bad package ships, but it blocks every package that carries the affected code on ≥ 2 clips. The fix is to mirror the original's two-dict coverage:

```python
body = STEP_A_SOFT_MANY.get(c) or EDGE_WORDS_MANY.get(c) or STEP_A_SOFT.get(c) or EDGE_WORDS[c]
```

or, better, build `STEP_A_SOFT_MANY` / `EDGE_WORDS_MANY` as derived views of the canonical dicts so they can never drift.

---

### [P2] `COUNT_WORDS` tops out at 5; a 6-clip medley produces "6 clips" which `_CLIP_REF` cannot strip, silently inflating the kind count

**Location:** `pipeline/package.py` line 9 (`COUNT_WORDS = {2: "Two", …, 5: "Five"}`) and `pipeline/package_pin.py` `_CLIP_REF`.

The medley is hook + up to 5 clips = 6 positions. If all six carry the same code, `COUNT_WORDS.get(6, str(6))` yields `"6"`, producing the sentence `"6 clips (A, B, C, D, E, F): …"`. The `_CLIP_REF` regex expects `[A-Z][a-z]+ clips` (a capitalised word), so `"6 clips"` does not match. The clip reference is never stripped, the kind string retains the channel list, and two different groups of six clips with the same code would count as **two** kinds instead of one — potentially pushing a package over the 3-kind cap that should pass.

Fix: extend `COUNT_WORDS` to at least 6 (or use `num2words`), and add a test with 6 clips.

---

### [P2] `content_flags` now filters to `status == "FLAGGED"` rows; the original counted every flag returned by `review_flags_of` regardless of row status

**Location:** `pipeline/package_pin.py`, new `content_flags`.

Original:
```python
return len([f for f in review_flags_of(gates) if f not in exc])
```

New:
```python
return len({flag_kind(g, f) for g, row in gates.items()
            if g != EXCEPTION_GATE and isinstance(row, dict)
            and row.get("status") == "FLAGGED"
            for f in row.get("flags") or [] if isinstance(f, str)})
```

If any gate row can carry a non-empty `flags` list while its `status` is `"PASS"` or `"MONITORING"` (e.g., an informational note attached to a passing gate), the old code counted those flags toward the cap; the new code does not. The ruling text says "the FLAGGED rows," so this is likely intentional, but it is a silent behavioural change from the original. Verify that no production gate row ever has `flags` without `status == "FLAGGED"`, or add a comment / assertion documenting the invariant.

---

### [P3] No test exercises the multi-clip path for a code that is *not* in `STEP_A_SOFT_MANY` / `EDGE_WORDS_MANY`

The `TestRuling155FlagKinds` suite only uses REFERENT_OUTSIDE, NOT_OWN_SINCERE, EDGE_OUT, and STAND_ALONE — all of which have `_MANY` entries. A regression test that feeds a hypothetical `"TOPIC_DRIFT"` code on two clips would have caught the P1 KeyError above.

---

### [P3] `_CLIP_REF` does not match "The first clip"

The alternation is `opening|second|third|fourth|fifth`. If any code path ever emits `"The first clip (…): …"` (e.g., a future layout where the hook is labelled "first" rather than "opening"), the prefix won't be stripped and the kind will include the channel name, breaking the merge. Low risk given the current naming convention, but worth a comment or a broader pattern (`The \w+ clip`).

---

## Answers to the four review questions

| # | Question | Verdict |
|---|----------|---------|
| 1 | Can a package carry > 3 kinds? | **No.** `content_flags` counts distinct kinds; `review_problems` emits a problem string when `n > cap`; the integrator's `check_pin_only` treats that as a pin failure. The test confirms 4 kinds → refused, 3 → pass. |
| 2 | Can two different kinds collapse to one? | **No, in the current code.** `flag_kind` prefixes non-PER_CLIP_KIND kinds with the gate name, and the body text for each code is unique. The only theoretical collision is the P2 above (6-clip regex miss), which *inflates* the count, never deflates it. |
| 3 | Does the integrator's exact-text match break? | **No.** `PER_CLIP_KIND` includes `"stand_alone"`, so `flag_kind` returns the bare gate name and the per-clip sentences (with `STAND_SOFT_PREFIX`) are untouched. `review_flags_of` is explicitly unchanged. The `review_problems` message text changed ("kinds of review flag") but that string is not matched by the integrator. |
| 4 | Is the merged sentence correct for every code? | **Not yet.** It is correct for the four `STEP_A_SOFT_MANY` codes and the two `EDGE_WORDS_MANY` codes. For any other code the function crashes (P1). Once the fallback is fixed, the sentence template (`"N clips (chans): <body>.")` is correct for all codes. |

---

P1_OR_WORSE: 1