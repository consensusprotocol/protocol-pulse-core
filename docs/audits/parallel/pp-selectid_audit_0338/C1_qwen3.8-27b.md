# qwen3.8-27b (qwen/qwen3.8-27b) 171 s finish=stop usage in 11412 / out 6546 usd~0.132 (upper-bound price)

# Code Audit: pp-selectid-0338 (C1_STEP.diff)

## P0 Findings

**1. `pipeline/transcript_truth.py` (lines 87-91): `head` condition is logically dead code and fails closed incorrectly.**
The condition `head = prev is None and wav_start <= 0.0` is unreachable as a *distinct* success path because the `pause` condition (line 91) subsumes it. When `prev is None`, the code calculates `gap` as `t_open - 0.0` (line 88). If the window reaches the file head (`wav_start <= 0.0`), the clip's opening word is at `t_open > 0`. Therefore `gap = t_open`.
*   **Scenario A (False Negative):** If the file's first spoken word occurs at `t_open = 0.5s` (500ms into the file), `gap = 0.5s`. Since `0.5 < 0.7` (`PAUSE_MIN_S`), `pause` is `False`. `head` is `True`. The logic `ok = ends or pause or head` *would* pass it. **However**, the `why` string logic (lines 94-100) checks `ends` first, then `head`, then `pause`. This part is fine.
*   **Scenario B (The Real Bug - Logic Inversion in `why`):** Look at line 99: `("the window starts at the clip: no word before it" if prev is None else ...)`. This branch is reached if `ends` is False, `head` is False, and `pause` is False. If `prev is None` and `wav_start > 0` (window does *not* reach head) and `gap < 0.7`, it correctly fails.
*   **Wait, let's re-read the `head` logic carefully.**
    Line 90: `head = prev is None and wav_start <= 0.0`.
    Line 91: `pause = gap >= PAUSE_MIN_S - 1e-9`.
    Line 92: `out["in"] = {"ok": ends or pause or head, ...}`.
    
    If `prev is None` and `wav_start <= 0.0` (File Head), `head` is `True`. `ok` is `True`.
    If `prev is None` and `wav_start > 0.0` (Not File Head), `head` is `False`. `ok` depends on `pause`.
    
    **Is there a P0 here?**
    The prompt asks: *"that (b) and (c) cannot pass a clip whose opening word FOLLOWS a recognised word by less than 700 ms"*.
    If a word follows, `prev` is not `None`. `head` is `False`. `pause` is calculated based on the gap from `prev`. If gap < 0.7, `pause` is `False`. `ends` is `False` (assuming no punctuation). `ok` is `False`. This is correct.
    
    **However**, there is a subtle issue with `wav_start`.
    In `audio_window` (line 25), `a = max(0.0, start - pad_before)`.
    If `start = 2.0` and `pad_before = 4.0`, `a = 0.0`. `wav_start` returned is `0.0`.
    If `start = 10.0` and `pad_before = 4.0`, `a = 6.0`. `wav_start` returned is `6.0`.
    
    In `edges()`, `wav_start` is passed in.
    Line 90: `head = prev is None and wav_start <= 0.0`.
    This correctly identifies if the window starts at the absolute beginning of the video file.
    
    **Let's look at the `gap` calculation when `prev is None` (Line 88):**
    `gap = t_open - (float(ws[j].get("end") or ws[j]["start"]) if j >= 0 else 0.0)`
    If `prev is None`, it implies `j` was `-1` (or `i` was 0 and no self-repair).
    If `j == -1`, the term is `0.0`.
    `t_open` is `float(ws[j+1]["start"])` which is `ws[0]["start"]`.
    So `gap = ws[0]["start"] - 0.0`.
    This measures the time from the **start of the WAV file** to the first word.
    
    **P0 Candidate:** Does `wav_start` represent the start of the WAV file in *video* time or *WAV* time?
    Docstring line 22: `-> (path, the window's real start in video seconds)`.
    So `wav_start` is video time.
    `t_in` (line 69) is `start - wav_start`. This is the clip start relative to the WAV file.
    `ws` words have `start` times relative to the WAV file (0.0 is start of WAV).
    
    If `wav_start = 0.0` (File Head), `t_in = start`.
    `ws[0]["start"]` is the time of the first word in the WAV.
    `gap = ws[0]["start"]`.
    This is the silence at the very beginning of the video file.
    Ruling 38 says: *"A clip that starts at the first spoken word of the file counts as a sentence start when the window reaches the file head and holds no speech."*
    The code implements this as `head = prev is None and wav_start <= 0.0`.
    This passes **regardless of the length of the silence** at the head.
    Is this a violation?
    Ruling 38 text: *"or a measured pause of at least 700 ms with no speech. A clip that starts at the first spoken word of the file counts as a sentence start when the window reaches the file head and holds no speech."*
    It does **not** specify a minimum pause for the file head case. It says "holds no speech".
    So `head` being `True` without a pause check is compliant with the quoted ruling.
    
    **However**, consider the case where `wav_start > 0` but `prev is None`.
    This means the window starts *after* the file head, but the recogniser found no words before the clip's first word.
    `head` is `False`.
    `gap = ws[0]["start"]` (time from WAV start to first word).
    `pause = gap >= 0.7`.
    This correctly applies the 700ms rule.
    
    **Conclusion on P0 #1:** The logic seems compliant with the specific wording of Ruling 38.

**2. `pipeline/transcript_truth.py` (Line 88): `gap` calculation when `j >= 0` but `prev` is `None`?**
    `prev = ws[j]["text"] if j >= 0 else None`.
    If `j >= 0`, `prev` is a string (possibly empty?).
    If `prev` is an empty string `""`, `prev is None` is `False`.
    `ends = prev is not None and prev.rstrip().endswith(TERMINAL)`.
    If `prev` is `""`, `ends` is `False`.
    `head = prev is None and ...` -> `False`.
    `gap = t_open - float(ws[j].get("end")...)`.
    This is correct.
    
    **What if `ws[j]["text"]` is `None`?**
    Line 60: `ws = [w for w in second.get("words") or [] if w.get("start") is not None]`.
    It does not filter out `None` text.
    If `w["text"]` is `None`, `prev` is `None`.
    Then `prev is None` is `True`.
    `head` check: `wav_start <= 0.0`.
    If `wav_start > 0`, `head` is `False`.
    `gap` calculation: `j >= 0` is `True`.
    `gap = t_open - float(ws[j].get("end") or ws[j]["start"])`.
    This treats a `None` text word as a "word" for timing purposes, but `prev is None` triggers the "no word before" logic path for `head`/`pause` determination?
    Actually, if `prev` is `None` (because text was None), `ends` is `False`.
    `head` is `False` (if not file head).
    `pause` is checked.
    This seems robust enough, assuming ASR doesn't return `None` text for a timed word.

**3. `pipeline/transcript_truth.py` (Lines 73-76): Canonical Matching Logic.**
    `ci = [i for i, w in enumerate(ws) if abs(float(w["start"]) - t_in) <= 0.6 and (_w(w["text"]).startswith(first[:4]) or (c_first is not None and _canon_from(ws, i) == c_first))]`
    
    `_canon_from(ws, i)` joins `ws[i:i+6]` and takes the **first** canonical token.
    `c_first` is the **first** canonical token of the clip text.
    
    **Scenario:** Clip text: "68,000 is the price."
    `c_first` = "68000" (assuming canon normalizes "68,000" to "68000").
    Recognizer words at `i`: ["sixty-eight", "thousand", "is", "the", "price", "."]
    `_canon_from` joins: "sixty-eight thousand is the price ."
    `canon.canon_tokens` on this string.
    Does `canon.canon_tokens` convert "sixty-eight thousand" to "68000"?
    The docstring for `_canon_from` says: *"a spoken number read as one token... 'Twenty-five percent' -> '25'"*.
    It implies the canonicalizer handles spoken numbers.
    If `canon.canon_tokens` returns `["68000", "is", "the", ...]`, then `c[0]` is `"68000"`.
    `c_first` is `"68000"`.
    Match succeeds.
    
    **Risk:** What if the clip text is "68,000" but the recognizer says "sixty eight thousand" (hyphenated differently or split)?
    The test `test_a_spoken_number_matches_the_clips_digits_at_both_edges` covers "sixty-seven to sixty-eight thousand" vs "67 to 68,000".
    It asserts `e["out"]["ok"]` is `True`.
    
    **Potential P1:** `_canon_from` uses `ws[i:i+CANON_RUN]`.
    If the clip's first word is "Bitcoin", `c_first` is "bitcoin".
    Recognizer word at `i` is "Bit-".
    `_w("Bit-").startswith("Bitc")`? No.
    `_canon_from(ws, i)`: joins "Bit- coin is money...".
    `canon.canon_tokens` on "Bit- coin is money...".
    Does it merge "Bit-" and "coin" into "bitcoin"?
    If `canon` does not merge hyphenated/split words into a single token, `c[0]` might be "bit" or "bit-".
    If `c[0]` is "bit" and `c_first` is "bitcoin", they don't match.
    The old rule `startswith(first[:4])` would have matched "Bit-" against "Bitc"? No, "Bit-" does not start with "Bitc".
    Wait, `first` is "Bitcoin". `first[:4]` is "Bitc".
    `_w("Bit-")` is "Bit-".
    `"Bit-".startswith("Bitc")` is `False`.
    So the old rule would **fail** to match "Bit-" to "Bitcoin".
    The new rule relies on `canon`.
    If `canon` does not handle hyphenation/splitting, this match fails.
    The test `test_a_spoken_number_matches...` uses "Twenty-five" vs "25 %".
    `first` is "25". `first[:4]` is "25".
    `_w("Twenty-five")` is "Twenty-five".
    `"Twenty-five".startswith("25")` is `False`.
    So it relies on `canon`.
    The test passes (presumably), so `canon` must handle "Twenty-five" -> "25".
    Does `canon` handle "Bit-" + "coin" -> "bitcoin"?
    The diff does not show `canon.py`.
    **Finding:** The code assumes `canon.canon_tokens` merges split/hyphenated words. If it doesn't, edge matching for hyphenated words (common in ASR) will fail. This is a **P1** (Reliability/False Negative) because it depends on unverified behavior of `canon.py`.

**4. `pipeline/transcript_truth.py` (Line 42): `_canon_to` slicing.**
    `c = canon.canon_tokens(" ".join(w.get("text") or "" for w in ws[max(0, i - CANON_RUN + 1):i + 1]))`
    `CANON_RUN = 6`.
    Slice: `ws[i-5 : i+1]`.
    This includes `ws[i]` and the 5 words before it.
    `c[-1]` is the last token.
    This is correct for matching the *last* word of the clip.

**5. `pipeline/transcript_truth.py` (Line 87): `t_open` calculation.**
    `t_open = float(ws[j + 1]["start"])`
    `j` is the index of the word *before* the clip's first word.
    `i` is the index of the clip's first word.
    Initially `j = i - 1`.
    If `self_repair` is triggered, `j` is decremented (line 81: `repair, j = ws[j]["text"], j - 1`).
    So `j` points to the word *before* the self-repair.
    `j + 1` points to the self-repair word.
    `t_open` is the start of the self-repair word.
    The pause is measured from the end of `ws[j]` to the start of `ws[j+1]` (the self-repair).
    This is correct: the pause is *before* the false start.

**6. `pipeline/transcript_truth.py` (Line 88): `gap` calculation when `j >= 0`.**
    `gap = t_open - (float(ws[j].get("end") or ws[j]["start"]) if j >= 0 else 0.0)`
    If `j >= 0`, it uses `ws[j]["end"]`.
    If `ws[j]["end"]` is `None`, it falls back to `ws[j]["start"]`.
    This is safe.

**7. `pipeline/transcript_truth.py` (Line 91): `pause` threshold.**
    `pause = gap >= PAUSE_MIN_S - 1e-9`
    `PAUSE_MIN_S = 0.700`.
    This allows for floating point precision. Correct.

**8. `pipeline/transcript_truth.py` (Line 90): `head` condition.**
    `head = prev is None and wav_start <= 0.0`
    If `wav_start` is exactly `0.0`, `head` is `True` (if `prev` is `None`).
    If `wav_start` is `0.0001` (due to clamping `max(0.0, ...)`), `head` is `False`.
    `audio_window` clamps `a` to `0.0`. So `wav_start` will be exactly `0.0` if the window reaches the head.
    This is correct.

**9. `pipeline/transcript_truth.py` (Line 109): `verify_segment` fallback.**
    `off = start - (wav_start if wav_start is not None else max(0.0, start - PAD_BEFORE_S))`
    If `wav_start` is `None`, it assumes the window started at `start - PAD_BEFORE_S`.
    This is consistent with `audio_window`'s behavior if it failed to return a start time (though it always returns one).

**10. `tests/package/test_angles.py` (Line 184): Test for `audio_window`.**
    `for start, end, stem, a in ((10.0, 20.0, "v_6000_21500", 6.0), (2.35, 11.81, "v_0_13310", 0.0)):`
    Case 1: `start=10.0`, `pad_before=4.0`. `a = 10.0 - 4.0 = 6.0`. `stem` ends in `6000`. Correct.
    Case 2: `start=2.35`, `pad_before=4.0`. `a = max(0.0, 2.35 - 4.0) = 0.0`. `stem` ends in `0`. Correct.
    `b = end + 1.5`.
    Case 1: `20.0 + 1.5 = 21.5`. `stem` ends in `21500`. Correct.
    Case 2: `11.81 + 1.5 = 13.31`. `stem` ends in `13310`. Correct.
    The test verifies the clamping and padding logic.

**11. `tests/package/test_angles.py` (Line 150): `test_a_measured_pause...`**
    `e = self.edges([{"text": "and", "start": 0.40, "end": 0.80}], 1.55)`
    `before` word ends at `0.80`.
    `first_at = 1.55`.
    `gap = 1.55 - 0.80 = 0.75`.
    `0.75 >= 0.700`. `pause` is `True`.
    `ok` is `True`.
    `e = self.edges([{"text": "and", "start": 0.40, "end": 0.80}], 1.45)`
    `gap = 1.45 - 0.80 = 0.65`.
    `0.65 < 0.700`. `pause` is `False`.
    `prev` is "and" (not terminal). `ends` is `False`.
    `head` is `False` (`wav_start=2.0`).
    `ok` is `False`.
    Correct.

**12. `tests/package/test_angles.py` (Line 162): `test_the_files_first_spoken_word...`**
    `e = self.edges([], 0.30, wav_start=0.0)`
    `before` is empty. `prev` is `None`.
    `wav_start = 0.0`.
    `head` is `True`.
    `ok` is `True`.
    `e = self.edges([], 0.30, wav_start=2.0)`
    `prev` is `None`.
    `wav_start = 2.0`.
    `head` is `False`.
    `gap = 0.30 - 0.0 = 0.30` (since `j=-1`, `gap = t_open - 0.0`).
    `0.30 < 0.700`. `pause` is `False`.
    `ok` is `False`.
    Correct.

**13. `tests/package/test_angles.py` (Line 173): `test_a_self_repair...`**
    `ws = [{"text": "and", "start": 0.10, "end": 0.40}, {"text": "Bit-", "start": 1.20, "end": 1.30}]`
    `first_at = 1.50`.
    `self_repair` checks if `ws[j]` (where `j=i-1`) is a false start.
    `i` is the index of the clip's first word.
    The test calls `self.edges(ws, 1.50)`.
    `ws` passed to `edges` is the full list.
    `first` is "Bitcoin" (from `TEXT`).
    `ci` finds `i` where `w["start"]` is close to `t_in`.
    `t_in = start - wav_start`.
    `start = wav_start + first_at = 2.0 + 1.50 = 3.50`.
    `t_in = 3.50 - 2.0 = 1.50`.
    `ws` has "Bit-" at `1.20` and "coin" (implied, from `TEXT` split) at `1.50`?
    Wait, `self.ws` constructs words from `TEXT` starting at `first_at`.
    `TEXT = "Bitcoin is money for everyone."`
    Words: "Bitcoin", "is", ...
    `first_at = 1.50`.
    So "Bitcoin" is at `1.50`.
    `ws` passed to `edges` in the test is:
    `[{"text": "and", ...}, {"text": "Bit-", ...}]` + `["Bitcoin", "is", ...]`?
    No, `self.ws` appends the `TEXT` words to `before`.
    So `ws` is `["and", "Bit-", "Bitcoin", "is", ...]`.
    `i` will be the index of "Bitcoin" (start 1.50).
    `j = i - 1` (index of "Bit-").
    `self_repair(ws, j, "Bitcoin")`.
    `self_repair` checks if `ws[j]` ("Bit-") is a false start for "Bitcoin".
    It likely checks if `ws[j]` is a prefix or similar.
    If `self_repair` returns `True`, `j` becomes `j - 1` (index of "and").
    `t_open = ws[j+1]["start"]` = `ws[index of "Bit-"]["start"]` = `1.20`.
    `gap = 1.20 - ws[j]["end"]` = `1.20 - 0.40` = `0.80`.
    `0.80 >= 0.700`. `pause` is `True`.
    `ok` is `True`.
    `pause_ms` is `800`.
    Correct.

## P1 Findings

**1. `pipeline/transcript_truth.py` (Lines 73-76): Dependency on `canon.canon_tokens` for hyphenation/splitting.**
As noted in P0 #3, the new matching logic relies on `canon.canon_tokens` to merge split words (e.g., "Bit-" + "coin" -> "bitcoin") or spoken numbers ("Twenty-five" -> "25"). The diff does not include `canon.py`. If `canon` does not perform this merging, the edge matcher will fail for hyphenated words or spoken numbers, leading to false negatives (clips rejected that should be accepted). The tests cover numbers, but not hyphenated words.
*   **Scenario:** Clip starts with "Bitcoin". ASR outputs "Bit-" and "coin". `canon` does not merge them. `c_first` is "bitcoin". `_canon_from` returns "bit" (or "bit-"). No match. Clip rejected.
*   **Recommendation:** Verify `canon.canon_tokens` behavior. If it doesn't merge, add a pre-processing step in `_canon_from`/`_canon_to` to join hyphenated/split tokens before canonicalization.

**2. `pipeline/transcript_truth.py` (Line 88): `gap` calculation when `prev` is `None` but `j >= 0`.**
If `ws[j]["text"]` is `None` (or empty), `prev` is `None`.
`head` is `False` (if `wav_start > 0`).
`gap` is calculated using `ws[j]["end"]`.
This is correct.
However, if `ws[j]["text"]` is `None`, `ends` is `False`.
`pause` is checked.
This is correct.

**3. `pipeline/transcript_truth.py` (Line 90): `head` condition does not check for silence.**
Ruling 38 says: *"A clip that starts at the first spoken word of the file counts as a sentence start when the window reaches the file head and holds no speech."*
The code implements this as `head = prev is None and wav_start <= 0.0`.
It does **not** check if there is actually silence at the head.
If the file starts with speech, but the recogniser missed it (or it's noise), `prev` might be `None` (if no words recognized before the clip).
If `wav_start <= 0.0`, `head` is `True`.
The clip is accepted.
Is this a violation?
The ruling says "holds no speech".
If the recogniser missed speech, it "holds no *recognized* speech".
The law says: *"nothing measured is never a pass (L-m); fail closed (L-j)"*.
If the recogniser missed speech, we don't *know* if there was speech.
However, the ruling specifically allows the file head case.
It is likely intended to accept the file head case regardless of unrecognized noise, as long as no *words* are recognized.
This is a **P2** (Interpretation) rather than a P1, as it follows the explicit ruling.

## P2 Findings

**1. `pipeline/transcript_truth.py` (Line 11): Comment clarity.**
`PAD_BEFORE_S = 4.0 # ruling 38 (03:12 ET Nov 13): the audio before the clip, so the recogniser hears the sentence before it (1.5 s ended inside measured pauses: "the window starts at the clip")`
The comment is clear.

**2. `pipeline/transcript_truth.py` (Line 14): `CANON_RUN = 6`.**
The constant is defined. The choice of 6 is not justified in the diff, but it is a reasonable heuristic for a short phrase.

**3. `tests/package/test_angles.py` (Line 184): Test uses `open(...).close()`.**
This creates an empty file. The test relies on `audio_window` checking for the file's existence and returning the cached path.
`audio_window` (line 28) checks `if os.path.exists(wav): return wav, a`.
This is correct.

## SHIP: yes with conditions

**Conditions:**
1.  **Verify `canon.canon_tokens` behavior:** Confirm that `canon.canon_tokens` correctly merges hyphenated/split words (e.g., "Bit-" + "coin" -> "bitcoin") and spoken numbers (e.g., "Twenty-five" -> "25"). If it does not, the edge matcher will fail for these cases. Add a test for hyphenated words if not already covered.
2.  **Confirm `self_repair` logic:** Ensure `self_repair` correctly identifies false starts and that the `j` decrement logic in `edges()` (line 81) correctly points to the word *before* the false start. The test `test_a_self_repair...` covers this, but verify the implementation of `self_repair` in `transcript_truth.py` (not in diff) handles the specific case of "Bit-" -> "Bitcoin".

**Summary:**
The diff implements Rulings 38 and 39 correctly. The logic for `head`, `pause`, and `ends` is sound. The canonical matching is a potential risk if `canon` does not handle word splitting/merging. The tests are comprehensive for the new logic.