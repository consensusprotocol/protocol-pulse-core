# qwen3.8-27b (qwen/qwen3.8-27b) 49 s finish=stop usage in 14871 / out 1590 usd~0.068 (upper-bound price)

# Audit: pp-selectid-1545 / C1_STEP (Ruling 69 — Speaker Attribution via Caption Turns)

## P0 Findings (Blockers)

**None.** The core logic correctly implements the "fail-closed" requirement. A wrong name is prevented by the `decide()` function, which forces `unknown` if the turn evidence conflicts with the basis rule, or if the lower third contradicts the decision. The "address" logic correctly requires exactly two people to infer the speaker by elimination.

## P1 Findings (Major Issues)

### 1. `turn_of` Backchannel Merge Logic is Fragile and Potentially Incorrect
**File:** `pipeline/speakers.py`, lines 127-135 (in diff)
**Scenario:** The logic for merging across backchannels assumes that if a segment between two markers is short (<= 3 words), it is a backchannel from the *other* speaker, and the speaker before and after is the *same*.
```python
while b < len(units) and nxt(b) < len(units) and words(b, nxt(b)) <= bc:   # A | b: B's interjection | A again
    skipped.append(" ".join(units[k][1] for k in range(b, nxt(b))))
    spans.append((nxt(b), nxt(nxt(b))))
    b = nxt(nxt(b))
```
**Issue:** This logic blindly merges across *any* short segment between markers. It does not verify that the speaker *before* the short segment is the same as the speaker *after* it. In a fast-paced conversation, Speaker A might say a 2-word phrase, then Speaker B might say a 2-word phrase, then Speaker A might speak again. The code would merge A's first phrase, B's phrase, and A's second phrase into one "turn" of A, effectively attributing B's words to A's turn context. While the *attribution* of the clip itself might still be correct if the clip is in A's part, the `turn_text` provided to the LLM will contain B's words as if they were part of A's turn. This could confuse the LLM or lead to a false positive if B's words contain a name that matches a person in the source lines.
**Recommendation:** The merge logic should be more conservative. It should only merge if the *next* marker after the short segment is followed by content that is clearly a continuation of the previous speaker (e.g., similar topic, or if the short segment is a known backchannel like "Yeah", "Mm-hm"). Alternatively, do not merge at all, and let the LLM handle the context, or require a higher confidence threshold for merging.

### 2. `captions` Function Does Not Validate Timestamps
**File:** `pipeline/speakers.py`, lines 79-105 (in diff)
**Scenario:** The `captions` function reads `transcript.yt_auto.json` and extracts `start` times. It does not validate that the timestamps are monotonically increasing or that they are within a reasonable range.
**Issue:** If the caption file is corrupted or has out-of-order timestamps, `turn_of` will fail or produce incorrect results. For example, if a later caption has an earlier timestamp, the `before` and `nxt` logic in `turn_of` will break.
**Recommendation:** Add validation to ensure timestamps are monotonically increasing. If not, fail closed (return `None, None`).

### 3. `check_turn` Does Not Verify the Quote is in the *Correct* Part of the Turn
**File:** `pipeline/speakers.py`, lines 146-162 (in diff)
**Scenario:** The `check_turn` function verifies that the quote is verbatim in the `turn_text`. However, it does not verify that the quote is in the part of the turn *spoken by the speaker being attributed*.
**Issue:** If the turn contains words from multiple speakers (due to the backchannel merge issue in P1-1), a quote from Speaker B could be used to attribute Speaker A. For example, if Speaker B says "I'm Mark Yusko" in a backchannel, and the code merges it into Speaker A's turn, the LLM might quote it, and `check_turn` would accept it, attributing the clip to Mark Yusko even though Speaker A was speaking.
**Recommendation:** The `check_turn` function should verify that the quote is in the part of the turn that is *not* a backchannel. Alternatively, the backchannel merge should be removed, and the LLM should be given the full context with markers, and the code should verify that the quote is in a segment that is *not* marked as a backchannel.

## P2 Findings (Minor Issues)

### 1. `TURN_MAX_CHARS` Cut May Lose Context
**File:** `pipeline/speakers.py`, lines 138-142 (in diff)
**Scenario:** If the turn is longer than `TURN_MAX_CHARS` (12000), it is cut around the clip.
**Issue:** The cut is done by character count, not by word count. This may cut in the middle of a word or sentence, losing context.
**Recommendation:** Cut by word count, and ensure the cut does not split a word.

### 2. `MARKER_TOL_S` May Be Too Large
**File:** `pipeline/speakers.py`, line 38 (in diff)
**Scenario:** `MARKER_TOL_S` is 0.5 seconds.
**Issue:** If a marker is 0.4 seconds before the clip start, it is considered "before" the clip. If a marker is 0.4 seconds after the clip end, it is considered "after" the clip. This may be too large, and could lead to incorrect turn boundaries.
**Recommendation:** Reduce `MARKER_TOL_S` to 0.1 seconds, or make it configurable.

### 3. `BACKCHANNEL_WORDS` May Be Too Large
**File:** `pipeline/speakers.py`, line 36 (in diff)
**Scenario:** `BACKCHANNEL_WORDS` is 3.
**Issue:** A 3-word interjection may not be a backchannel. For example, "I don't know" is 3 words, but it is a statement, not a backchannel.
**Recommendation:** Reduce `BACKCHANNEL_WORDS` to 1 or 2, or use a list of known backchannels.

## SHIP: No

**Reasons:**
1. The backchannel merge logic is fragile and could lead to incorrect attribution if the merge joins two different speakers' turns.
2. The `check_turn` function does not verify that the quote is in the part of the turn spoken by the speaker being attributed.
3. The `captions` function does not validate timestamps.

**Conditions for Shipment:**
1. Fix the backchannel merge logic to ensure it only merges if the speaker before and after the short segment is the same.
2. Fix the `check_turn` function to verify that the quote is in the part of the turn that is not a backchannel.
3. Add timestamp validation to the `captions` function.
4. Add tests for the backchannel merge logic and the `check_turn` function.