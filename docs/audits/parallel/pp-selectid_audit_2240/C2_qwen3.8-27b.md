# qwen3.8-27b (qwen/qwen3.8-27b) 139 s finish=stop usage in 39627 / out 2821 usd~0.161 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (FINAL)
# Feature: pp-selectid-2240

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I was overly cautious about the `no_voice` fallback (P0-1) and the `_within` settlement logic (P0-3). The consensus and other models correctly identified that:
1.  **`no_voice` is safe:** The dispatch condition in `build()` (`not med["flagged"]`) combined with the internal guard in `no_voice()` (`med.get("flagged") != []`) ensures a flagged join never ships. I missed that the *dispatch* gate is the primary filter, and `no_voice` is just the executor.
2.  **`_within` settlement is correct:** The test `TestDeadline` proves that `_settle` books the upper bound *once* and clears the reservation. I was worried about double-counting, but the code structure (`_reserve` -> `_settle`) is atomic per call attempt.
3.  **Budget checks are now pervasive:** I missed that `over_budget()` is called *before* every line-up and every write, not just at the end of an angle. This closes the "run past 15 min inside one angle" hole I flagged in C1.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | My C1 View | C2 View | Disposition |
| :--- | :--- | :--- | :--- |
| **No-voice flagged join** | P0 (Uncertain) | **REFUTED** | The code at `package.py:423` explicitly checks `med.get("flagged") != []` and returns `None` if true. The dispatch at `package.py:576` also requires `not med["flagged"]`. Double-locked. |
| **`_within` double-settle** | P0 (Uncertain) | **REFUTED** | `providers.py:770` calls `_settle` once on `DeadlineExceeded`. The reservation is popped. The late thread's result is dropped (`box` is local to the thread, `done` event is set, but the main thread has already moved on). No ledger mutation from the late thread. |
| **Budget timing** | P1 (End-of-angle only) | **FIXED** | `package.py:400-412` defines `over_budget`. It is called at `package.py:505` (before line-up) and `package.py:516` (before write). This is correct. |
| **House Style Scope** | P1 (Medley only?) | **AGREE** | `cheap_checks` at `package.py:364` only runs `HS.lint_lines` if `pk.get("shape") == "medley"`. Since `build()` only produces medleys (L-y), this is correct. Non-medley packages (if any existed) would bypass this, but the scope is defined as medley-only. |
| **`utc_z` Naive Datetime** | P1 (Late failure) | **P2 (Fail-closed)** | `utc_z` returns `None` for naive strings. `recency_problems` rejects `None`. This is fail-closed. The error message is slightly misleading ("must be YYYY...Z" vs "missing offset"), but the behavior is safe. |

## 3. NEW FINDINGS FROM THIS REVIEW

**P1-1: `no_voice` clip addition logic may violate `LY_CLIPS` max.**
`package.py:438-441`: When adding a clip to a no-voice package, the code checks `if len(cand) - 1 > LY_CLIPS[1]`. `LY_CLIPS[1]` is 4. So `len(cand) - 1` must be <= 4, meaning `len(cand)` <= 5. This is correct. However, the check `[x for x in cand[1:-1] if x["duration_s"] < SHORT_CLIP_S]` is used in a boolean context (`if ... or ...`). If this list is non-empty, the condition is True, and the candidate is skipped. This is correct. **No bug.**

**P1-2: `writer_avoid` logic in `build()`.**
`package.py:395-396`: `writer_avoid` is computed as `{router.backends[n].vendor for n in router.chain("angle_write") if n in router.backends} - {angle_reply.vendor}`. This means every write avoids *all* vendors in the chain *except* the one that produced the angle. This ensures the judge (which uses a different role, e.g., `vo_fidelity`) can use a different vendor. However, `write_takeaway` is called with `avoid_vendor=writer_avoid or None`. If `writer_avoid` is empty (e.g., only one vendor in chain), it passes `None`. This is correct.

**P1-3: `sentence_count` edge case with abbreviations.**
`house_style.py:91-98`: `sentence_count` uses `_ABBREV_RE.fullmatch(t)`. `_ABBREV_RE` is `(\w\.)+['\")\]]*`. This matches "u.s.", "e.g.", etc. It does *not* match "u.s." if it's part of a larger word like "u.s.a."? No, `fullmatch` requires the whole token to match. "u.s.a." matches `(\w\.)+`. So "u.s.a. markets fell." -> "u.s.a." is excluded, "markets" is not, "fell." is counted. Correct.
What about "v2f."? `v2f.` matches `(\w\.)+`? `\w` matches `v`, `2`, `f`. So `v2f.` is `v2f` + `.`. The pattern is `(\w\.)+`. This requires a word char followed by a dot, repeated. `v2f.` is `v` (word), `2` (word), `f` (word), `.` (dot). The pattern `(\w\.)+` would match `v.` then `2.`? No, `2` is not followed by `.` in the string "v2f.". The string is "v2f.". The pattern `(\w\.)+` tries to match: `v` then `.`? No, next char is `2`. So `v2f.` does *not* match `_ABBREV_RE`. Therefore, "v2f." is counted as a sentence end. Is this a false positive? "v2f" is likely a version number or code. If a caption says "v2f. is out.", it counts as 1 sentence. If it says "v2f. is out. It is good.", it counts as 2. This seems acceptable.

**P1-4: `EMOJI_RE` range.**
`house_style.py:39`: `[\U0001F300-\U0001FAFF\U0001F1E6-\U0001F1FF☀-➿⭐⭕️]`. This covers most emojis. The test `test_emoji` checks specific ones. It seems robust.

**P1-5: `no_voice` runtime check.**
`package.py:428-430`: `if content > nv_hi: return None`. `nv_hi` is `RUNTIME_S[1] - FINAL_TAIL_S`. `RUNTIME_S` is (60, 70). `FINAL_TAIL_S` is 14.30. So `nv_hi` is 55.7. If the clips alone are > 55.7s, no-voice is refused. This is correct because the sign-off adds time, and the total must be <= 70s.

**P1-6: `no_voice` clip addition when `content < nv_lo`.**
`nv_lo` is `RUNTIME_S[0] - FINAL_TAIL_S` = 60 - 14.30 = 45.7. If clips are < 45.7s, a clip is added. The new content must be <= 55.7s. The code checks `not nv_lo <= sum(...) <= nv_hi`. This is correct.

**P1-7: `ly_shape` for no-voice.**
`package.py:352-357`: If `nv` is not None, it checks `if bridges or after or vo.get("intro")`. This ensures no VO lines. It also checks `if not isinstance(nv, dict) or not str(nv.get("why") or "").strip()`. This ensures the record exists. Correct.

**P1-8: `inventory` style row.**
`package.py:620-622`: `**({"house_style": dict(row(not style, ...), why=[...]) if style is not None else {}})`. If `style` is an empty list (no violations), `not style` is True, so status is "PASS". If `style` has violations, `not style` is False, so status is "FAIL". Correct.

**P1-9: `to_pin` recency check.**
`package_pin.py:693-694`: `recency_problems(pk.get("segments") or [])` is added to `problems`. If any segment fails, `PinRefused` is raised. Correct.

**P1-10: `seal` includes recency fields.**
`package_pin.py:682-683`: `time_sensitive` and `source_published_at` are included in the `body` dict that is hashed. Correct.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **No-Voice Fallback** | P0 (Uncertain) | **PASS** | Verified double-lock on `flagged` joins. Runtime checks are correct. |
| **Budget/Deadline** | P1 (Timing) | **PASS** | `over_budget` is called before every line-up and write. `_within` settlement is correct. |
| **House Style** | P1 (Scope) | **PASS** | Scope is medley-only, which matches the builder's output. Lint logic is sound. |
| **Recency/Pin** | P1 (Late Fail) | **PASS** | Fail-closed. Seal includes fields. `to_pin` validates. |
| **Providers** | P0 (Double Settle) | **PASS** | `_settle` is called once per timeout. Late threads are dropped. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1.  **`package.py:266`**: `utc_z` returns `None` for naive datetimes. The error message in `recency_problems` (`package_pin.py:667`) says "must be YYYY-MM-DDTHH:MM:SSZ" but doesn't explicitly say "missing offset". This is a minor diagnostic improvement, not a bug.
2.  **`house_style.py:95`**: `sentence_count` logic for abbreviations is complex. The test `test_a_one_letter_abbreviation_ends_no_sentence` covers "u.s." but not "v2f." or other edge cases. However, the behavior is acceptable (fail-closed on sentence count).
3.  **`providers.py:732`**: The daemon thread in `_within` is abandoned. If the back-end `complete` method has side effects (e.g., writing to a file), those side effects will still occur. The docstring says "its result is dropped unrecorded," but side effects are not mentioned. This is a known limitation of Python threads and is acceptable for this use case (API calls).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The implementation of `over_budget()` being called **before every line-up and every write** (not just at the end of an angle) is the highest-leverage change. It ensures the 15-minute wall clock and $1.50 reported cost limits are strictly enforced, preventing runaway costs and timeouts that would have been possible in the previous design.

## 7. PRODUCTION READY?

**SHIP: yes**

The code is fail-closed, the budget limits are strictly enforced, the no-voice fallback is safe, and the house style lint is deterministic and correct. The P2 findings are minor diagnostic improvements or known limitations of the Python threading model, not bugs.