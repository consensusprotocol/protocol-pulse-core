# qwen3.8-27b (qwen/qwen3.8-27b) 57 s finish=stop usage in 18314 / out 3757 usd~0.111 (upper-bound price)

I’ll analyze the diff against the specific questions (a)–(e) and the governing laws, focusing on what is verifiable from the provided code.

## Analysis

### (a) Can a tampered or non-sentence-ready window record reach a moment?

**Verification of `window_source()` checks:**
1.  **Path Integrity:** `os.path.dirname(path) != base` ensures the file is in `transcripts/<vid>/windows/`.
2.  **File Hash:** `hashlib.sha256(raw).hexdigest() != wp["record_sha256"]` ensures the file on disk matches the hash in `word_pass.jsonl`.
3.  **Method:** `rec.get("transcript_method") != "whisper_words_punct"` rejects non-punctuated methods.
4.  **Segments Hash:** `rec.get("transcript_sha256") != sha` (where `sha` is computed from `rec["segments"]`) ensures internal consistency.
5.  **Words Hash:** `rec.get("words_sha256") != wsha` (where `wsha` is computed from `rec["words"]`) ensures internal consistency.
6.  **Words vs Segments:** `words_off_segments(rec)` ensures words spell the segments.
7.  **Clock:** `win.get("clock") != "youtube"` rejects non-YouTube clocks.
8.  **Punctuation:** `(rec.get("punctuation") or {}).get("still_unpunctuated") is not False` rejects unpunctuated stretches.
9.  **Span Containment:** `t0 < w0 - WINDOW_TOL_S or t1 > w1 + WINDOW_TOL_S` ensures the ledger row's time span is inside the window.
10. **Channel:** `rec.get("channel_id") != row.get("channel_id")` rejects channel mismatches.
11. **Sentence Ready:** `E.sentence_ready(src)` is called on the constructed Source.

**Potential Gap:**
The check `E.sentence_ready(src)` relies on the `eligibility` module (imported as `E`). The diff does not show the implementation of `E.sentence_ready`. However, the law L-e states: "transcript_store.acquire(prefer_words) returns only a sentence_ready record... editorial_select's word pass treats any other record as failed."
In `window_source`, the record is explicitly checked for `still_unpunctuated is False`. If `E.sentence_ready` also checks for this (or similar conditions), it is redundant but safe. If `E.sentence_ready` checks something else (e.g., minimum word count, valid timing), it adds safety.
Crucially, the `word_pass_index` function filters for `r.get("sentence_ready") is not True` -> `not_ready`. So only rows marked `sentence_ready: true` in the JSONL are passed to `window_source`.
`window_source` then re-verifies the file content.
**Conclusion:** It is very difficult for a tampered or non-ready record to pass. The multi-layered hash and content checks are robust.

### (b) Can a window clip be judged for L-s with LESS than 90s/60s context, or pass when missing?

**Verification of `caption_parts()`:**
-   `before=CONTEXT_BEFORE_S` (90s) and `after=CONTEXT_AFTER_S` (60s) are default arguments.
-   `pre = [tok for tok, a, b in timed if b > t0 - before and a < t0]`
-   `post = [tok for tok, a, b in timed if t1 < a <= t1 + after]`
-   If `cs` (context source) is `None`, or `t0`/`t1` are `None`, or `cs.tokens` is empty, it returns `(None, None)`.
-   If any token in `cs.tokens` has missing start/end times, it returns `(None, None)`.

**Verification of `exclusion_for()` in `package.py`:**
-   `before, after = CI.context_around(...)`
-   `if before is None: cache[key] = {"verdict": "exclude", ... "measured": False}`
-   This implements **Fail Closed** (L-j/M12). If context is missing, the moment is excluded, not passed.

**Verification of `caption_source()`:**
-   It looks for a record in `transcripts/<vid>/` where `rec.get("transcript_sha256") == want` (the row's `transcript_sha256`).
-   It also checks `ts.segments_sha256(rec.get("segments") or []) != want`.
-   If no such record is found, it returns `(None, "no record...")`.
-   In `build_inputs`, if `src.context_source` is `None`, it logs `no_caption_context` and sets `src.context_source = None`.
-   Later, `caption_parts` will see `cs is None` and return `(None, None)`, leading to exclusion.

**Potential Gap:**
Does `caption_parts` guarantee *at least* 90s/60s of context?
The code selects *all* tokens within the window. If the video is short, or the caption record doesn't cover that time, the context will be shorter.
However, the law says: "CONTEXT INTEGRITY (L-s): every clip is judged inside its source's transcript from >= 90 s before to >= 60 s after".
If the context is *less* than 90s/60s because the video ends or the caption is missing, does it fail?
The code does **not** explicitly check if `len(pre)` or `len(post)` covers the full 90s/60s duration. It just takes what is there.
If the caption record is the "full-video" record (as stated in the docstring: "a caption record is the whole video"), then for a moment in the middle, it should have 90s/60s.
But what if the moment is near the start or end of the video?
The docstring for `caption_parts` says: "or to the media's edge". This implies that if the video is shorter than 90s before the start, it uses what is available.
Is this a violation of L-s? L-s says ">= 90 s before". If the video is only 10s long, you can't have 90s before.
Usually, "fail closed" applies to *missing data*. If the data exists but is bounded by the media edge, is it a fail?
The law L-s is about *judging* the clip. If the context is truncated by the media edge, the model might make a wrong judgment.
However, the prompt says: "Only state what you can verify from the diff provided."
The diff shows `caption_parts` returns `(None, None)` only if the *record* is missing or *times* are missing. It does *not* return `None` if the context is short.
Therefore, a clip near the start of a video will be judged with <90s of pre-context.
**Finding:** This might be a P1 or P2 depending on interpretation. If L-s strictly requires 90s/60s of *available* context to be present, and the code allows less, it's a gap. But "to the media's edge" is explicitly in the docstring, suggesting this is intended behavior for edge cases. I will flag it as a potential issue if the law is interpreted strictly as "must have 90s of context to proceed".

### (c) Is the caption record the one the ledger mined, and can a wrong one be used?

**Verification of `caption_source()`:**
-   `want = row.get("transcript_sha256")`
-   It iterates through `transcripts/<vid>/transcript.*.json`.
-   It checks `rec.get("transcript_sha256") != want` AND `ts.segments_sha256(rec.get("segments") or []) != want`.
-   This ensures the record's segments hash matches the ledger row's `transcript_sha256`.
-   The ledger row's `transcript_sha256` is the hash of the segments the ledger *mined* from.
-   Therefore, it selects the record that matches the mining source.
-   **Can a wrong one be used?** Only if two different records have the same segments hash (collision, unlikely) or if the ledger row's `transcript_sha256` is wrong (upstream error). The code is correct in its selection logic.

### (d) Does anything change for the full-video records path?

**Verification of `build_inputs()`:**
-   `src, path, passed_over = word_source(rs[0], ctx, store)`
-   If `src is None`, it tries the window path.
-   If `src is NOT None` (full-video record found), it proceeds to `reanchor`.
-   The `context_around` function:
    ```python
    if getattr(src, "window", None) is not None:
        # window path
    win = window(src, k0, k1)
    # full-video path
    ```
-   For full-video records, `src.window` is `None` (it's not set in `word_source`, only in `window_source`).
-   So it uses the old `window()` logic.
-   `exclusion_for` uses `CI.context_around`.
-   For full-video, `context_around` returns the same text as before (using `window()`).
-   **Byte-identical?** The logic for full-video records is unchanged. The `context_around` function branches on `src.window`. If `src.window` is None, it uses the old path.
-   **Conclusion:** No change for full-video records.

### (e) Do the tests fail on the defect each one names?

**Test Analysis:**
1.  `test_the_word_pass_index_reads_each_moments_last_ready_row_and_counts_the_rest`:
    -   Checks `word_pass_index` logic.
    -   Verifies last row wins, failed/not_ready counted.
    -   Seems correct.
2.  `test_a_window_record_is_used_only_when_every_claim_checks_out`:
    -   Uses `window_fixture` to create a valid record.
    -   Tampering:
        -   `w[3]["start"] += 0.05` -> `words_sha256` mismatch. Test expects "words_sha256" in why.
        -   `punctuation={"still_unpunctuated": True}` -> Test expects "still unpunctuated".
        -   `clock="window"` -> Test expects "YouTube clock".
        -   `row={"start": 10.0, "end": 20.0}` -> Test expects "not inside the window".
        -   `record_sha256="0"*64` -> Test expects "record_sha256".
        -   `window_record="transcripts/vidW/x.json"` -> Test expects "not this video's window record".
    -   These tests directly verify the checks in `window_source`.
3.  `test_a_window_from_the_media_start_is_file_head`:
    -   Checks `file_head` logic.
4.  `test_a_video_without_a_full_record_is_built_from_its_window_with_caption_context`:
    -   Checks `build_inputs` with window path.
    -   Verifies `context_source` is set.
    -   Verifies `_window_text` uses caption context.
5.  `test_a_window_without_its_caption_record_has_no_context_and_fails_closed`:
    -   Checks `caption=False` in fixture.
    -   Verifies `no_caption_context` in report.
    -   Verifies `_window_text` returns `(None, None)`.
    -   Verifies `exclusion_for` returns `exclude` with `measured: False`.

**Conclusion:** The tests cover the main failure modes and verify the fail-closed behavior.

## Findings

### P1: Context Length Not Enforced for L-s
**File:** `pipeline/context_integrity.py` (lines 28-29)
**Scenario:** A window record is created for a moment at `t=10s` in a video. The caption record exists and covers the whole video. `caption_parts` calculates `pre` tokens from `t=10s - 90s` to `t=10s`. Since the video starts at `0s`, the available pre-context is only `10s`. The code does not check if the duration of `pre` is >= 90s. It returns the 10s of context. `exclusion_for` uses this 10s context to judge the clip.
**Law Violation:** L-s requires ">= 90 s before". If the context is shorter, the judgment is based on insufficient data. The code should fail closed (exclude) if the context window is not fully populated, unless the media edge is the reason. The docstring says "or to the media's edge", which suggests this is intended. However, if the law is strict, this is a gap. Given the docstring explicitly allows media edge truncation, this might be acceptable. I will rank it P2 as it's a design choice documented in the code.

### P2: `caption_source` Does Not Verify the Caption Record is "Full-Video"
**File:** `pipeline/ledger_build.py` (lines 217-240)
**Scenario:** `caption_source` looks for a record matching `transcript_sha256`. It does not check if the record is a "full-video" caption record or a window record. If a window record happened to have the same `transcript_sha256` as the ledger row (unlikely, as window records have different segments), it could be used. However, the ledger row's `transcript_sha256` is from the *mining* source, which is typically a full-video caption. The code assumes the matching record is the caption. This is safe if the store is well-organized.

### P2: `word_pass_index` Does Not Validate `window_record` Path Format
**File:** `pipeline/ledger_build.py` (lines 123-159)
**Scenario:** `word_pass_index` reads the JSONL. It checks `isinstance(r.get("window_record"), str)`. It does not check if the string looks like a valid path. `window_source` later checks the path. This is fine, as `window_source` is the gatekeeper.

### P1: `context_around` for Window Records Does Not Check if Caption Context is Sufficient
**File:** `pipeline/context_integrity.py` (lines 34-49)
**Scenario:** `context_around` calls `caption_parts`. If `caption_parts` returns `None`, it returns `None, None`. If it returns parts, it joins them. It does not check if the parts cover the required 90s/60s. This is the same as the P1 above.

### P2: `build_inputs` Does Not Log Which Window Record Was Chosen for a Video
**File:** `pipeline/ledger_build.py` (lines 276-300)
**Scenario:** If a video has multiple rows with window records, `build_inputs` picks the first one that passes `window_source`. It logs `window_passed_over` for the others. It logs `window_records` for the chosen one. This is good.

### P1: `exclusion_for` Uses `CI.context_around` Which May Return Short Context
**File:** `pipeline/package.py` (lines 332-338)
**Scenario:** If `context_around` returns short context (due to media edge), `exclusion_verdict` is called with that short context. The model might make a wrong exclusion decision. The law L-s is about *context integrity*. If the context is incomplete, the integrity is compromised. The code should perhaps fail closed if the context is shorter than the required window, unless it's the media edge. The docstring in `caption_parts` says "or to the media's edge", so this is likely intended.

## Verdict

The code is robust in its hash and content checks. The main concern is the interpretation of L-s regarding context length at media edges. The docstring explicitly allows truncation at media edges, which suggests this is a design decision. The fail-closed behavior for missing context is correctly implemented.

**SHIP: yes with conditions**

**Conditions:**
1.  Confirm that L-s allows context truncation at media edges (start/end of video). If not, `caption_parts` must check if the pre/post context duration is >= 90s/60s and fail closed if not.
2.  Ensure `E.sentence_ready` is implemented correctly to reject non-sentence-ready records.