# qwen3.8-27b (qwen/qwen3.8-27b) 94 s finish=stop usage in 37826 / out 5149 usd~0.191 (upper-bound price)

# Code Audit: pp-selectid-2240 (C1_STEP.diff)

## P0 Findings

### P0-1: `no_voice` fallback can ship a package with a flagged join (violates R3 / L-y)
**File:** `pipeline/package.py`, `no_voice()` function (approx. lines 400–481 in diff)

**Scenario:**
1. A medley line-up has a join that the blind clips-alone verdict flags (e.g., `med["flagged"] = ["clip_01 -> clip_02"]`).
2. The takeaway fails its gates twice (`take_failed >= NO_VOICE_AFTER`).
3. `no_voice()` is called. It checks `if not ok2 or nv_med["flagged"]:` **only when it adds a clip** (line 433). If the original line-up’s content is already within `nv_lo..nv_hi` (45.7–55.7 s), it skips the clip-addition block entirely.
4. The original `med` (with `flagged` non-empty) is used as `nv_med` (line 409: `nv_med = med`).
5. The code proceeds to `assemble_medley` and `cheap_checks` without ever verifying that the *original* line-up has no flagged joins.
6. `ly_shape()` (line 353–357) checks `if bridges or after or vo.get("intro"):` for no-voice, but does **not** re-check `med["flagged"]` for the no-voice case. The `flagged` check in `ly_shape` is only in the normal VO path.
7. Result: A no-voice package ships with a join a viewer cannot follow, violating R3 (“provided the clips-alone verdict passed” implies no flagged joins) and L-y.

**Fix:** In `no_voice()`, before proceeding, assert `not med["flagged"]` for the original line-up (not just the re-judged one after adding a clip).

---

### P0-2: `house_style` gate is not required for non-medley packages, but `lint_lines` is only called for medleys
**File:** `pipeline/package.py`, `cheap_checks()` (line 366) and `package_pin.py` (line 614)

**Scenario:**
1. `cheap_checks()` only calls `HS.lint_lines(pk["lines"])` when `pk.get("shape") == "medley"` (line 364–366).
2. `package_pin.MEDLEY_GATES` includes `"house_style"` (line 614), so it is required for medley pins.
3. However, if a non-medley package (e.g., a single-clip or R4 package) has lines that violate house style, they are **not** linted and **not** gated.
4. R6 states “HOUSE STYLE on the three text surfaces” without limiting it to medleys. The title and caption are present in all packages.
5. Result: Non-medley packages can ship with titles/captions that violate PBX’s copy rules (e.g., hashtags, em-dashes, hedges), because the gate is never run.

**Fix:** Either run `HS.lint_lines` for all packages in `cheap_checks()`, or clarify that R6 applies only to medleys. If the latter, document it; if the former, add the gate to `REQUIRED_GATES` for all shapes.

---

### P0-3: `utc_z()` returns `None` for naive datetimes, but `recency_problems()` rejects `None`
**File:** `pipeline/package.py`, `utc_z()` (lines 258–266) and `package_pin.py`, `recency_problems()` (lines 626–643)

**Scenario:**
1. A moment’s `published_at` is a naive ISO string (e.g., `"2026-11-12T01:00:00"` with no offset).
2. `utc_z()` returns `None` (line 266: `return None if t.tzinfo is None else ...`).
3. `_package()` sets `source_published_at: None` (line 277).
4. `recency_problems()` checks `isinstance(at, str) and bool(RECENCY_AT.match(at))` (line 635). `None` is not a `str`, so `ok = False`.
5. The pin is refused with `source_published_at must be YYYY-MM-DDTHH:MM:SSZ (got None)`.
6. This is correct fail-closed behavior, **but** the error message is misleading: it says “must be YYYY-MM-DDTHH:MM:SSZ” when the real issue is “missing offset.” More critically, if a moment’s `published_at` is `None` (not a string), `utc_z(None)` returns `None` (line 264: `except (TypeError, ValueError): return None`), and the same rejection occurs.
7. **However**, the test `test_the_package_states_each_clips_recency_from_its_moment` (line 830) asserts `PK.utc_z("2026-11-11T18:03:23")` is `None`, which is correct. The issue is that **all** moments with naive or missing `published_at` will fail to pin, which may be too strict if the source data is known to be naive. But per R1, the pin must carry a UTC time, so this is likely intentional. **No bug here, but worth noting the strictness.**

**Revised:** This is **not** a P0. It is fail-closed as required. Downgrade to P2 (documentation).

---

### P0-4: `no_voice()` does not re-run `ly_shape()` on the final package
**File:** `pipeline/package.py`, `no_voice()` (lines 400–481)

**Scenario:**
1. `no_voice()` calls `assemble_medley()` (line 442) and `cheap_checks()` (line 444).
2. `cheap_checks()` calls `ly_shape(pk)` (line 365) and adds its failures to `v`.
3. If `ly_shape()` fails (e.g., because the no-voice record is missing or malformed), `cheap` is non-empty, and `no_voice()` returns `None` (line 446–448).
4. This is correct. **However**, `ly_shape()` for no-voice checks `if bridges or after or vo.get("intro"):` (line 356). If `vo` is `{"intro": None, "bridges": [], "bridges_after_clip": []}`, this passes. But if `assemble_medley` accidentally sets `vo["intro"]` to a non-None value, `ly_shape` fails. This is a defensive check, not a bug.

**Revised:** No P0 here.

---

## P1 Findings

### P1-1: `house_style.lint()` does not check for lowercase in titles or takeaways
**File:** `pipeline/house_style.py`, `lint()` (lines 105–164)

**Scenario:**
1. R6 states “lowercase captions” but does not explicitly require lowercase for titles or takeaways.
2. However, PBX’s standing copy rules (line 12) say “lowercase, no hashtags, no em-dashes, no emoji clutter, no AI-sounding phrasing, no hedging” without limiting it to captions.
3. `lint()` only checks `if t != t.lower():` for `kind == "caption"` (line 135). Titles and takeaways can have uppercase letters and pass.
4. If the intent is that **all** surfaces are lowercase, this is a false negative. If only captions are lowercase, this is correct.
5. The test `test_plain_lines_pass` (line 902) asserts `HS.lint("title", "The market no government owns")` passes, which has an uppercase "T". So the intent is that titles are **not** required to be lowercase.
6. **Conclusion:** This is correct per the tests. No bug.

**Revised:** Not a P1.

---

### P1-2: `sentence_count()` may miscount sentences with abbreviations
**File:** `pipeline/house_style.py`, `sentence_count()` (lines 91–98)

**Scenario:**
1. `_ABBREV_RE = re.compile(r"(\w\.)+['\")\]]*")` matches one-letter abbreviations like "u.s.", "e.g.", "i.e.".
2. `_END_RE = re.compile(r"[.!?]['\")\]]*$")` matches tokens ending in `.`, `!`, or `?` followed by optional closing quotes/brackets.
3. A token like "u.s." matches both `_END_RE` and `_ABBREV_RE`, so it is **not** counted as a sentence end.
4. A token like "e.g." matches both, so it is **not** counted.
5. However, a token like "Mr." matches `_END_RE` but **not** `_ABBREV_RE` (because "Mr" is two letters, not one). So "Mr." is counted as a sentence end.
6. This is a false positive: "Mr. Smith went home." would be counted as two sentences, but it is one.
7. R6 does not specify how to handle multi-letter abbreviations. The docstring (line 93) says “not counting a one-letter abbreviation,” implying multi-letter abbreviations **are** counted as sentence ends.
8. **Conclusion:** This is a known limitation, not a bug. The docstring is clear.

**Revised:** Not a P1.

---

### P1-3: `no_voice()` does not check that the added clip is from a different channel
**File:** `pipeline/package.py`, `no_voice()` (lines 400–481)

**Scenario:**
1. R3 states “one more clip of the angle is added in the proposer’s order.”
2. `no_voice()` iterates over `angle["moments"]` and adds the first one that passes the checks (lines 416–427).
3. It checks `m["channel_id"] in chans` (line 418), where `chans` is the set of channels in the current line-up. So it **does** check for a different channel.
4. **Conclusion:** Correct. No bug.

**Revised:** Not a P1.

---

### P1-4: `providers._within()` may leak a reservation if the thread raises an exception after the deadline
**File:** `pipeline/providers.py`, `_within()` (lines 694–712) and `Router.call()` (lines 740–747)

**Scenario:**
1. `Router.call()` reserves a key (line 733: `key = self._reserve(b, upper)`).
2. If `deadline_s` is set, it calls `_within(deadline_s, lambda: b.complete(...))` (line 741).
3. If the deadline is exceeded, `_within()` raises `DeadlineExceeded` (line 709).
4. `Router.call()` catches `DeadlineExceeded` (line 744) and calls `self._settle(key, b, {"in": 0, "out": 0}, upper, role)` (line 745).
5. This settles the reservation at the upper bound. **Correct.**
6. However, if the thread **completes** just after the deadline is checked (i.e., `done.wait(seconds)` returns `False`, but the thread sets `box["value"]` and `done.set()` immediately after), the result is dropped. The reservation is settled at the upper bound. **Correct.**
7. If the thread raises an exception **before** the deadline, `box["error"]` is set, and `_within()` re-raises it (line 711). `Router.call()` catches it in the `except RequestRejected` or `except Exception` blocks (lines 748–750), which call `self._settle(key)` (line 749). **Correct.**
8. **Conclusion:** No leak. The reservation is always settled.

**Revised:** Not a P1.

---

### P1-5: `house_style.lint()` does not check for em-dashes in the `PROMPT_RULES` string
**File:** `pipeline/house_style.py`, `PROMPT_RULES` (lines 178–189)

**Scenario:**
1. `PROMPT_RULES` is a string that is injected into the writer prompt.
2. It contains the text “no em-dash or en-dash (use a period or a comma).”
3. The string itself does not contain an em-dash, so it is fine.
4. **Conclusion:** No bug.

**Revised:** Not a P1.

---

### P1-6: `no_voice()` does not re-run the `medley` gate on the final package
**File:** `pipeline/package.py`, `no_voice()` (lines 400–481)

**Scenario:**
1. `no_voice()` calls `medley()` (line 431) when adding a clip, and uses the original `med` otherwise.
2. It then calls `cheap_checks()` (line 444), which does **not** re-run the `medley` gate.
3. The `medley` gate is run in the main `build()` loop (line 1085: `ok_m, med = medley(...)`), and its result is stored in `pk["gates"]` via `inventory()` (line 527).
4. In `no_voice()`, the `medley` gate is **not** re-run; it uses the existing `med` or `nv_med`.
5. However, `inventory()` is called with `medley=(True, nv_med)` (line 465), so the gate is recorded.
6. **Conclusion:** The gate is not re-run, but it is recorded. This is correct because the clips-alone verdict is the coherence verdict (line 462).

**Revised:** Not a P1.

---

## P2 Findings

### P2-1: `house_style.lint()` does not check for lowercase in the `STYLE_REFERENCE` string
**File:** `pipeline/house_style.py`, `STYLE_REFERENCE` (lines 58–59)

**Scenario:**
1. `STYLE_REFERENCE` is a string that is injected into the writer prompt.
2. It contains the text “No ruler. Just rules nobody gets to bend. That's the idea, and it's the part most people still miss when they look at Bitcoin.”
3. The string has uppercase letters ("No", "Just", "That's", "Bitcoin"), so if it were linted as a caption, it would fail.
4. However, it is not linted; it is only used as a reference in the prompt.
5. **Conclusion:** No bug.

**Revised:** Not a P2.

---

### P2-2: `utc_z()` does not handle timezone-aware datetimes with non-UTC offsets correctly
**File:** `pipeline/package.py`, `utc_z()` (lines 258–266)

**Scenario:**
1. `utc_z("2026-11-11T13:03:23-05:00")` returns `"2026-11-11T18:03:23Z"` (line 828 test).
2. This is correct: 13:03:23 -05:00 is 18:03:23 UTC.
3. **Conclusion:** Correct.

**Revised:** Not a P2.

---

### P2-3: `no_voice()` does not check that the final package’s runtime is within 60–70 s
**File:** `pipeline/package.py`, `no_voice()` (lines 400–481)

**Scenario:**
1. `no_voice()` checks `if content > nv_hi:` (line 411) and `if content < nv_lo:` (line 414), where `nv_lo, nv_hi = RUNTIME_S[0] - FINAL_TAIL_S, RUNTIME_S[1] - FINAL_TAIL_S` (line 406).
2. `RUNTIME_S` is (60, 70) (assumed from context).
3. `FINAL_TAIL_S` is 14.30 (assumed from context).
4. So `nv_lo = 60 - 14.30 = 45.7` and `nv_hi = 70 - 14.30 = 55.7`.
5. The content (sum of clip durations) must be within 45.7–55.7 s.
6. The runtime estimate is `content + FINAL_TAIL_S` (no VO line), so it must be within 60–70 s.
7. **Conclusion:** Correct.

**Revised:** Not a P2.

---

### P2-4: `house_style.lint()` does not check for em-dashes in the `detail` string
**File:** `pipeline/house_style.py`, `lint()` (lines 105–164)

**Scenario:**
1. The `detail` string is a human-readable message.
2. It may contain em-dashes if the offending text does.
3. However, the `detail` string is not linted; it is only used for reporting.
4. **Conclusion:** No bug.

**Revised:** Not a P2.

---

### P2-5: `no_voice()` does not check that the added clip is not already in the line-up
**File:** `pipeline/package.py`, `no_voice()` (lines 400–481)

**Scenario:**
1. `no_voice()` checks `if m is None or m in segs or mid in dropped or mid in doomed` (line 418).
2. `m in segs` checks if the moment is already in the line-up.
3. **Conclusion:** Correct.

**Revised:** Not a P2.

---

### P2-6: `house_style.lint()` does not check for lowercase in the `PROMPT_RULES` string
**File:** `pipeline/house_style.py`, `PROMPT_RULES` (lines 178–189)

**Scenario:**
1. `PROMPT_RULES` is a string that is injected into the writer prompt.
2. It contains the text “HOUSE STYLE (PBX’s standing copy rules; a line that breaks one is rejected):”
3. The string has uppercase letters ("HOUSE", "STYLE", "PBX’s"), so if it were linted as a caption, it would fail.
4. However, it is not linted; it is only used as a reference in the prompt.
5. **Conclusion:** No bug.

**Revised:** Not a P2.

---

### P2-7: `no_voice()` does not check that the final package’s title and caption are not empty
**File:** `pipeline/package.py`, `no_voice()` (lines 400–481)

**Scenario:**
1. `no_voice()` uses `last_fields["title"]` and `last_fields["caption"]` (line 436).
2. If `last_fields` is `None`, `no_voice()` is not called (line 545: `last_fields is not None`).
3. If `last_fields["title"]` or `last_fields["caption"]` is empty, `assemble_medley()` will fail (line 297: `dict(fields["title"], slot="title")` would raise a `KeyError` if `fields["title"]` is `None`).
4. However, `last_fields` is set to `fields` (line 505), which is the result of `write_takeaway()`, which always returns a non-None `fields` dict with non-empty title and caption (assumed from context).
5. **Conclusion:** Correct.

**Revised:** Not a P2.

---

### P2-8: `house_style.lint()` does not check for lowercase in the `detail` string
**File:** `pipeline/house_style.py`, `lint()` (lines 105–164)

**Scenario:**
1. The `detail` string is a human-readable message.
2. It may contain uppercase letters if the offending text does.
3. However, the `detail` string is not linted; it is only used for reporting.
4. **Conclusion:** No bug.

**Revised:** Not a P2.

---

### P2-9: `no_voice()` does not check that the final package’s segments are not empty
**File:** `pipeline/package.py`, `no_voice()` (lines 400–481)

**Scenario:**
1. `no_voice()` uses `order` (line 409), which is a list of segments.
2. If `order` is empty, `assemble_medley()` will fail (line 283: `n_clips = len(segs) - 1` would be -1).
3. However, `order` is initialized to `list(segs)` (line 409), which is non-empty (assumed from context).
4. **Conclusion:** Correct.

**Revised:** Not a P2.

---

### P2-10: `house_style.lint()` does not check for lowercase in the `slot` string
**File:** `pipeline/house_style.py`, `lint()` (lines 105–164)

**Scenario:**
1. The `slot` string is a key in the violation dict.
2. It is not linted; it is only used for reporting.
3. **Conclusion:** No bug.

**Revised:** Not a P2.

---

## Summary of Findings

| Severity | Count | Description |
|----------|-------|-------------|
| P0       | 2     | `no_voice` can ship a flagged join; `house_style` not gated for non-medleys |
| P1       | 0     | — |
| P2       | 0     | — |

## Verdict

**SHIP: no**

The two P0 findings must be fixed before merging:
1. `no_voice()` must verify that the original line-up has no flagged joins before shipping a no-voice package.
2. `house_style` must be gated for all packages, not just medleys, or the scope of R6 must be clarified and documented.