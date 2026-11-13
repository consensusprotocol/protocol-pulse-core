# qwen3.8-27b (qwen/qwen3.8-27b) 55 s finish=stop usage in 11455 / out 2029 usd~0.065 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0816
# Reviewer: [Your Model]

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (like GLM) focused heavily on the *tie-breaking* logic of `min()` and the *transitive closure* of union-find. I missed the critical flaw in the **matching heuristic** itself, which QWEN correctly identified as a P0.

**The Miss:** I assumed that `difflib.SequenceMatcher` with an 80% threshold was a robust proxy for "same speech." QWEN demonstrated that for short clips (8-10 words), a single semantic change (e.g., "gold" vs "silver") can still yield >80% word overlap, causing two *distinct* statements to be merged. This violates the core intent of Ruling 53 ("same speech").

**The Fix Verification:** The Cycle 2 diff introduces `_time_aligned()`. This is a significant architectural improvement that I failed to anticipate in Cycle 1. By requiring that matched words not only align in order but also maintain a consistent *temporal offset* (within 0.3s of the median), the code now distinguishes between:
1.  **Re-post:** Same audio, different upload time. Word timings are identical relative to the start of the clip.
2.  **Similar Speech:** Different speakers, different rhythms. Word timings will vary significantly, breaking the "one clock offset" assumption.

I missed that the *timing* data was available and necessary to solve the QWEN P0.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Cycle 1 Finding | Source | My Cycle 2 Verdict | Reasoning |
| :--- | :--- | :--- | :--- |
| **P0: 80% text overlap merges distinct short speeches** | QWEN | **AGREE (Fixed)** | The new `_time_aligned` check resolves this. The test `test_a_re_post_aligns_in_time_and_two_speakers_never_merge` explicitly verifies that "gold" vs "silver" with different rhythms are *not* merged. |
| **P1: Naive timestamps treated as "no time"** | GLM | **AGREE (Fixed)** | Line 63: `t = t if t.tzinfo else t.replace(tzinfo=timezone.utc)`. Naive times are now assumed UTC, preventing a naive original from losing to an aware copy. |
| **P1: Tie-break relies on input order** | GLM | **DISAGREE (Refuted)** | Line 64: `return (0, t.astimezone(timezone.utc).timestamp(), m["moment_id"])`. The tuple includes `moment_id` as the third element. `min()` will correctly break ties by the lexicographically lower ID, regardless of input order. GLM's Cycle 1 analysis was incorrect here. |
| **P2: O(n^2) performance** | GLM/QWEN | **AGREE (Acceptable)** | The multiset pre-check (Line 73-75) prunes most pairs before the expensive `difflib` and `statistics.median` calls. 2.3s for 308 moments is acceptable for a batch build. |
| **P1: Transitive closure merges A~B, B~C even if A!~C** | GLM | **AGREE (Intended)** | Ruling 53 implies "one speech" is a single entity. If A is a re-post of B, and B is a re-post of C, they are all the same speech. Union-find is the correct data structure. |

## 3. NEW FINDINGS FROM THIS REVIEW

### P1-1: `_time_aligned` Median Sensitivity to Outliers
**File:** `pipeline/package.py:39`
**Scenario:** A re-post has a single word with a corrupted or missing timestamp (e.g., `start: 0.0` instead of `12.5`).
**Analysis:** `statistics.median` is robust to *one* outlier, but if the re-post has a significant number of words with slightly drifted timings (e.g., due to variable frame rate or audio sync issues), the median offset might shift. However, the tolerance is `0.3s`. If the median is off by >0.3s, the match fails. This is a *fail-closed* behavior (no merge), which is safe.
**Verdict:** No change needed. Fail-closed is correct for a de-duplication rule.

### P1-2: `canon.canon_tokens` on Empty/None Words
**File:** `pipeline/package.py:23`
**Scenario:** A word token has `word: None` or `word: ""`.
**Analysis:** `t.get("word") or ""` handles `None`. `canon.canon_tokens("")` likely returns `[]` or `""`. The check `if key and ...` ensures empty keys are skipped. This is robust.
**Verdict:** No issue.

### P2-1: `REPOST_TIME_TOL_S` Hardcoded
**File:** `pipeline/package.py:10`
**Scenario:** Different video sources have different audio sync precisions.
**Analysis:** 0.3s is a reasonable default for YouTube/VOD. It is a module-level constant, easy to tune.
**Verdict:** Acceptable.

### P2-2: `out["reposted"]` Structure
**File:** `pipeline/package.py:133`
**Scenario:** Downstream consumers expect `reposted` to be a list of IDs, but it is a dict `{id: reason}`.
**Analysis:** The test `test_the_build_never_offers_the_copy_and_records_it` asserts `list(out["reposted"]) == ["w"]`. This works because `list(dict)` returns keys. The reason string is valuable for auditing.
**Verdict:** Acceptable, but document that `out["reposted"]` is a dict, not a list.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Matching Logic** | 6/10 | 9/10 | QWEN's P0 (text-only overlap) was a critical flaw. The addition of `_time_aligned` with median offset and tolerance is a robust solution that distinguishes re-posts from similar speeches. |
| **Time Handling** | 7/10 | 9/5 | GLM's P1 (naive timestamps) was valid. The fix (assume UTC) is correct and tested. |
| **Tie-Breaking** | 8/10 | 10/10 | GLM's P1 (input order) was refuted. The tuple `(0, ts, id)` correctly breaks ties by ID. |
| **Performance** | 8/10 | 8/10 | O(n^2) with pre-check is acceptable. No change. |
| **Test Coverage** | 7/10 | 9/10 | New tests cover the QWEN P0 scenario (gold/silver), naive times, and same-channel exclusion. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None. The QWEN P0 from Cycle 1 is resolved by the `_time_aligned` logic.

**P1 HIGH:** None. The GLM P1s are either resolved (naive time) or refuted (tie-break).

**P2 MEDIUM:**
1.  **`pipeline/package.py:133`**: Document that `out["reposted"]` is a dictionary `{moment_id: reason}`, not a list. (Low risk, but clarity is good).
2.  **`pipeline/package.py:10`**: Consider making `REPOST_TIME_TOL_S` configurable via `ctx` if different sources have varying sync quality. (Low risk, 0.3s is a safe default).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The introduction of **`_time_aligned`** (lines 29-40) is the highest-leverage change. It transforms the de-duplication rule from a fragile text-similarity heuristic (which QWEN proved could merge distinct speeches) into a robust audio-sync verification (which correctly identifies re-posts by their consistent temporal offset). This single function resolves the only P0 finding from Cycle 1.

## 7. PRODUCTION READY?

**Yes.**

**Conditions:**
1.  The `canon.canon_tokens` function must be stable and deterministic (verified in Cycle 1, assumed unchanged).
2.  The `published_at` field must be present in the moment data (verified in tests).
3.  The 0.3s tolerance for `REPOST_TIME_TOL_S` is appropriate for the target video sources (verified by the 07:14 build success: 38/38 words aligned).

The code is correct, robust, and well-tested. The Cycle 1 P0 is resolved. The Cycle 1 P1s are either fixed or refuted. Ship it.