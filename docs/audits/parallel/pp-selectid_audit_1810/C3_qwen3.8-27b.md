# qwen3.8-27b (qwen/qwen3.8-27b) 105 s finish=stop usage in 16412 / out 4392 usd~0.115 (upper-bound price)

**P0 Findings**

1.  **`pipeline/package.py` (lines 123-128 in diff): `same_speech` logic is inverted for the "re-post" exclusion.**
    *   **Scenario:** A moment `m` in video `vNew` contains the text "Bitcoin is up." A delivered clip `d` in video `vOld` contains the text "Bitcoin is up."
    *   **Code:** `elif any(d.get("text") and d.get("video_id") != m["video_id"] and same_speech(d["text"], m.get("text")) for d in spans):`
    *   **Analysis:** The condition `d.get("video_id") != m["video_id"]` ensures we only check *cross-video* re-posts. However, `same_speech` returns `True` if the texts are equal (canonicalized). If `m` is a *new* moment in a *different* video that happens to have the same text as a delivered clip, it is correctly excluded.
    *   **Wait, let's look closer at the "Missed" case.** The law says: "A span that has been DELIVERED in any video is never used again... extend it to... the same speech re-posted on another channel."
    *   **Critical Flaw:** The check `d.get("video_id") != m["video_id"]` excludes the same-video case from the `same_speech` check. This is correct because the *previous* `elif` block (line 120) handles same-video overlap via time spans (`overlap`).
    *   **However**, what if the same speech is re-posted in the *same* video but at a *different* time (non-overlapping)?
        *   Example: Video `v1` has "Bitcoin is up" at 0-10s (Delivered) and "Bitcoin is up" at 50-60s (New Moment).
        *   `overlap` check: `0 < 60` and `50 < 10` is False. No overlap.
        *   `same_speech` check: `d.video_id == m.video_id` (both `v1`). The condition `d.get("video_id") != m["video_id"]` is **False**. The `any(...)` loop skips this delivered span.
        *   Result: The new moment is **NOT** excluded by `same_speech`. It passes to the next checks.
        *   **Violation:** Ruling 76(b) states "A span that has been DELIVERED in any video is never used again... extend it to... the same speech re-posted on another channel." It implies *any* reuse of the speech is forbidden. The current code only forbids cross-video reuse via `same_speech` and same-video reuse via *time overlap*. It **allows** same-video, non-overlapping reuse of the exact same speech.
        *   **Fix:** The `same_speech` check should apply to *all* delivered spans, regardless of video ID, or the overlap check should be expanded to include text identity. Given the law "never used again", the text identity check should likely be global. If the intent is strictly "cross-channel re-post", the law text "re-posted on another channel" suggests the *primary* new concern is cross-channel. But "A span that has been DELIVERED... is never used again" is the base rule. The base rule was previously "overlap in same video". The *extension* is "same speech in another video".
        *   **Re-reading Law 76(b):** "A span that has been DELIVERED in any video is never used again (already so: keep it, and extend it to any overlapping span of the same video and to the same speech re-posted on another channel)."
        *   Interpretation:
            1.  Keep existing: Overlap in same video.
            2.  Extend to: Same speech in *another* channel/video.
        *   The code implements exactly this. `d.get("video_id") != m["video_id"]` ensures we only trigger the *new* `same_speech` logic for cross-video cases. Same-video non-overlapping identical speech is *not* explicitly forbidden by the *new* extension, nor was it by the *old* rule (which only checked overlap).
        *   **Is this a P0?** If the owner's intent "never reuse any of it" implies *any* textual reuse, this is a P0. If it implies "don't show the same clip twice" (overlap) and "don't show a copy from another channel" (cross-video), then it's compliant.
        *   **Ambiguity Risk:** "Never reuse any of it" is strong. However, the specific instruction "extend it to... the same speech re-posted on another channel" limits the *new* scope to cross-channel. I will flag this as **P1** due to the potential gap in same-video non-overlapping text reuse, which might violate the spirit of "never reuse".

2.  **`pipeline/package.py` (lines 112-114 in diff): `expired` check uses `ctx.now` but `usable` is called with `ctx` which might not have `now` set correctly or consistently with the "Render Clock".**
    *   **Scenario:** `usable` is called during the *selection* phase. `ctx.now` is the time selection started. The *pin* phase happens later.
    *   **Law 76(c):** "Open candidates and sealed-but-unrendered pins are re-checked against (a) at the moment they would render."
    *   **Code:** `package_pin.window_problems` is called at the pin stage (line 252 in `proof_ledger.py`). This handles the *render* clock check.
    *   **Code:** `package.usable` uses `ctx.now`. This handles the *selection* clock check.
    *   **Consistency:** This seems correct. Selection uses selection time, Pin uses render time.
    *   **However**, look at `candidates.expire` (line 233 in `proof_ledger.py`). It is called with `now = datetime.now(timezone.utc)` (line 211). This is the *driver* start time.
    *   **Law 76(a):** "A moment is usable only while its source video's published_at is within 12 HOURS of the RENDER clock."
    *   **Issue:** `candidates.expire` closes candidates based on the *driver* start time. If a candidate is expired at driver start, it is closed. This is fine.
    *   **But**, what if a candidate is *not* expired at driver start, but *is* expired by the time it reaches the pin stage?
    *   **Code:** `package_pin.window_problems` (line 252) checks the segments of the *final package*. If a segment is now >12h old, `window_problems` returns an error, and the pin is refused. This satisfies 76(c).
    *   **P0 Check:** Does `usable` correctly prevent *selection* of expired moments? Yes, line 112.
    *   **P0 Check:** Does `expire` correctly prevent *offering* expired candidates? Yes, line 233.
    *   **P0 Check:** Does `window_problems` correctly prevent *rendering* expired pins? Yes, line 252.
    *   **Verdict:** No P0 here.

3.  **`pipeline/package.py` (lines 85-86 in diff): `same_speech` uses `difflib.SequenceMatcher` with `autojunk=False`.**
    *   **Scenario:** Two long texts with many common words but different order.
    *   **Law:** "at least 80 % of the shorter one's words lie in runs of SAME_SPEECH_RUN or more words that the other says in the same order".
    *   **Code:** `sum(x.size for x in sm.get_matching_blocks() if x.size >= SAME_SPEECH_RUN) >= REPOST_ALIGN_MIN * short`.
    *   **Analysis:** `get_matching_blocks` returns contiguous matching sequences. `x.size` is the length of that sequence. The code sums the sizes of blocks that are >= 3 words long.
    *   **Correctness:** This correctly implements "runs of >= 3 words".
    *   **Edge Case:** What if the matching blocks are scattered? `SequenceMatcher` finds the *longest* matching blocks recursively. It does not guarantee that the sum of *all* blocks >= 3 covers 80% of the text if the text is fragmented.
    *   **Example:**
        *   Text A: "The quick brown fox jumps over the lazy dog" (9 words)
        *   Text B: "The quick brown cat jumps over the lazy mouse" (9 words)
        *   Matches: "The quick brown" (3), "jumps over the lazy" (4).
        *   Sum of blocks >= 3: 3 + 4 = 7.
        *   7 >= 0.8 * 9 (7.2)? No. 7 < 7.2.
        *   Result: `False`.
    *   **Example 2:**
        *   Text A: "The quick brown fox jumps over the lazy dog" (9 words)
        *   Text B: "The quick brown fox jumps over the lazy dog" (9 words)
        *   Matches: One block of 9.
        *   Sum: 9.
        *   9 >= 7.2? Yes.
        *   Result: `True`.
    *   **Example 3 (The "Scattered" Trap):**
        *   Text A: "A B C D E F G H I J" (10 words)
        *   Text B: "A B C X Y D E F G H I J" (12 words)
        *   Matches: "A B C" (3), "D E F G H I J" (7).
        *   Sum: 3 + 7 = 10.
        *   Shorter is 10. 0.8 * 10 = 8.
        *   10 >= 8. Result: `True`.
        *   Is this "same speech"? It's a re-post with an insertion. The law says "re-post cut a little differently is still the same speech". This seems acceptable.
    *   **Potential P1:** `difflib` is O(N^2) or worse for large texts. `same_speech` is called in a loop over `spans` for every `moment`. If `spans` is large (many delivered clips) and `moments` is large, this could be a performance bottleneck. However, `spans` are "delivered in the previous 24h" (or similar window), so likely small. `moments` are candidates, likely small.
    *   **Verdict:** No P0.

4.  **`pipeline/candidates.py` (lines 27-50 in diff): `expire` function.**
    *   **Code:**
        ```python
        for mid in e.get("lineup") or []:
            try:
                t = _at(published[mid])
            except (KeyError, TypeError, ValueError):
                old.append(f"{mid}: no known publish time")
                continue
            age = (now - t).total_seconds() / 3600.0
            if age > window_h:
                old.append(f"{mid}: {age:.1f} h")
        if old:
            outcome(e, "expired", ...)
        ```
    *   **Logic:** If *any* moment in the lineup is expired or has unknown publish time, the *entire candidate* is expired.
    *   **Law 76(a):** "A moment is usable only while its source video's published_at is within 12 HOURS... Past 12 h it is expired for good: out of the pool, out of the candidates registry, never offered again."
    *   **Analysis:** The law says the *moment* is expired. The candidate is a *lineup* of moments. If one moment in the lineup is expired, can the candidate still be used with the other moments?
    *   **Context:** `candidates.py` manages "lineups". A lineup is a specific combination of clips. If one clip in the combination is no longer valid (expired), the *combination* is no longer valid. You cannot "drop" the expired clip and keep the rest as the *same* candidate, because the candidate is defined by its specific lineup (sha256 sealed).
    *   **Verdict:** This is correct. If a component of the sealed lineup is invalid, the lineup is invalid.

5.  **`tests/package/proof_ledger.py` (lines 212-214 in diff): `--hours` validation.**
    *   **Code:**
        ```python
        if not 0 < a.hours <= package_pin.WINDOW_H:
            print(f"REFUSED (ruling 76): --hours {a.hours} is outside (0, {package_pin.WINDOW_H:g}]", file=sys.stderr)
            return 2
        ```
    *   **Law:** "If the 12 h pool cannot form a video, the stage it dies at is reported, rather than widening the window."
    *   **Analysis:** This prevents the user from passing `--hours 24` to widen the window. It enforces the 12h limit.
    *   **Verdict:** Correct.

**P1 Findings**

1.  **`pipeline/package.py` (lines 123-128 in diff): `same_speech` does not check same-video non-overlapping text reuse.**
    *   **Scenario:** Video `v1` has a delivered clip "Bitcoin is up" at 0-10s. A new moment "Bitcoin is up" exists at 50-60s in `v1`.
    *   **Current Behavior:**
        *   `overlap` check: False (0-10 does not overlap 50-60).
        *   `same_speech` check: `d.video_id == m.video_id` is True. The condition `d.get("video_id") != m["video_id"]` is False. The `any(...)` loop does not flag this.
        *   Result: The new moment is **usable**.
    *   **Risk:** The owner said "never reuse any of it". While the specific extension in 76(b) mentions "re-posted on another channel", the base rule "A span that has been DELIVERED... is never used again" could be interpreted to forbid *any* reuse of the speech, even in the same video if it's a distinct segment.
    *   **Recommendation:** Clarify if same-video non-overlapping identical text should be excluded. If yes, remove the `d.get("video_id") != m["video_id"]` condition from the `same_speech` check, or add a separate check for same-video text identity.

2.  **`pipeline/package.py` (lines 75-86 in diff): `same_speech` imports `canon` and `difflib` inside the function.**
    *   **Performance:** Importing modules inside a function called in a tight loop (for every moment, for every delivered span) is inefficient.
    *   **Recommendation:** Move imports to the top of the file.

3.  **`pipeline/package_pin.py` (lines 144-165 in diff): `window_problems` uses `datetime.now(timezone.utc)` if `now` is not provided.**
    *   **Consistency:** `package.usable` uses `ctx.now`. `candidates.expire` uses `now` passed from the driver. `window_problems` defaults to `datetime.now`.
    *   **Risk:** If `window_problems` is called without `now` (e.g., in a test or a different code path), it uses the *current* time, which might differ from the `ctx.now` used in selection.
    *   **Code Check:** In `proof_ledger.py` line 252, `package_pin.window_problems(res["package"]["segments"])` is called **without** `now`.
    *   **Impact:** This means the pin-stage check uses the *actual current time* at the moment of pinning, not the `ctx.now` from the selection phase.
    *   **Law 76(c):** "re-checked against (a) at the moment they would render."
    *   **Analysis:** Using the actual current time at the pin stage is *more* accurate for "the moment they would render" than using the selection time. This is likely **correct** and desirable. The selection time might be minutes ago. The pin time is closer to the render time.
    *   **Verdict:** This is actually a **good** implementation of 76(c). No finding.

4.  **`tests/package/test_medley.py` (lines 363-379 in diff): `test_delivered_speech_is_never_used_again_in_any_other_video`.**
    *   **Code:**
        ```python
        self.assertTrue(PK.same_speech(said, said.upper()))
        self.assertFalse(PK.same_speech("Bitcoin", "Bitcoin"))
        ```
    *   **Analysis:** `same_speech("Bitcoin", "Bitcoin")` returns `False` because `short < 2` (line 79-80 in `package.py`).
    *   **Law:** "two texts of at least two words are the same speech".
    *   **Verdict:** Correct.

**P2 Findings**

1.  **`pipeline/candidates.py` (lines 27-50 in diff): `expire` function does not log the specific `mid` that caused the expiry in the `why` string if multiple are expired.**
    *   **Code:** `"; ".join(old)`.
    *   **Verdict:** It does log them. `old` contains strings like `"mid: 12.0 h"`. This is fine.

2.  **`tests/package/proof_ledger.py` (lines 222-232 in diff): Reading `inputs.json` for publish times.**
    *   **Code:**
        ```python
        src = os.path.join(e["source"], "inputs.json")
        try:
            with open(os.path.join(REPO, src)) as f:
                pub.update(...)
        except ...:
            notes[k] = f"{src} could not be read..."
        ```
    *   **Risk:** If `inputs.json` is missing or malformed, the candidate is expired (fail closed). This is correct per Law 76(a) "unknown age is never assumed fresh".

**SHIP: yes with conditions**

**Conditions:**
1.  **Clarify Same-Video Text Reuse:** Confirm with the owner if "never reuse any of it" forbids same-video, non-overlapping identical text. If yes, update `package.usable` to apply `same_speech` to same-video spans as well (or add a specific check). If no, document this exception.
2.  **Move Imports:** Move `import difflib` and `import canon` to the top of `pipeline/package.py` for performance.
3.  **Verify `ctx.now` vs `datetime.now`:** Ensure that the use of `datetime.now` in `window_problems` (when called without args) is intentional and aligns with "the moment they would render". (It appears correct, but confirm).