# heimdall_qwen (qwen/qwen3.8-27b, 219.9 s, $0.023, finish stop)

This is a focused review of the **A19 (One Copy Per Delivery)** change in `pipeline/ingest/purge.py`, incorporating the Cycle 1 consensus and the specific fixes applied (C1-1 through C1-4).

### 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I correctly identified the core logic flow but missed two specific implementation details that the other models (specifically GLM and Muse) caught, which have since been fixed in the working tree:

1.  **The `kept_of` Logging Bug (C1-2):** I noted that `kept_of` was computed but didn't deeply analyze *how* it was derived. Muse and GLM correctly identified that deriving the "kept copies" list for a deletion log entry by matching the *basename* of the kept file against the video ID would fail if the PROVENANCE file was named something other than `<video_id>.<ext>` (e.g., `section_1.mp4`). The fix in the working tree (changing `kept_copies` to return `{realpath: (video_id, why)}` and filtering by `video_id` in `run_pass`) is correct and necessary.
2.  **Unbounded Memory Growth (C1-3):** I noted the `_SHA` cache but dismissed it as "Low" severity because the keys include `mtime_ns`. GLM correctly pointed out that in a long-running daemon (days/weeks), even with `mtime_ns` in the key, the dictionary grows indefinitely as files are created/deleted/modified. The fix (`SHA_CACHE_MAX = 4096` with a clear) is a necessary production hardening.

### 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Agree with GLM (C1-1):** The concern that `run/sources/` might not be checked was valid *if* the code only checked `sources/`. The code *does* check `run/sources/` in `kept_copies` (line 270: `for sub in ("sources", os.path.join("run", "sources"))`). The test `test_an_attested_section_in_a_references_run_sources...` confirms this works. I agree with the consensus that this is **safe**.
*   **Agree with Muse (C1-2):** The `kept_of` logic was fragile. The fix is robust.
*   **Agree with GLM (C1-3):** The cache bound is necessary.
*   **Disagree with Qwen (Self-Correction):** In Cycle 1, I spent significant effort analyzing a "hash mismatch" scenario that turned out to be handled correctly by the `unresolved` fallback. The code is fail-closed. I was overly suspicious of the `found` logic, but the `unresolved` catch-all makes it safe.

### 3. NEW FINDINGS FROM THIS REVIEW

**N1. Race Condition in `sha256_of` Cache (Low Severity)**
The `_SHA` dictionary is accessed without a lock.
*   **Scenario:** The `purge` loop runs in a thread (`service.py` line 825). If a manual CLI `purge --apply` is run concurrently, or if the service restarts and overlaps (though `service.lock` prevents this for the main service, the CLI `purge` command in `tools/ingest_watch.py` line 190 calls `purge.run_pass` directly without the service lock, only the `purge.lock` file lock which is inside `run_pass`), there is a potential race.
*   **Analysis:** `run_pass` acquires `purge.lock` (line 379). This lock is held for the *entire* pass, including the `kept_copies` call where `sha256_of` is used. Therefore, two `run_pass` calls cannot execute `sha256_of` concurrently.
*   **Verdict:** **Safe.** The `purge.lock` serializes all purge operations, protecting the global `_SHA` cache. No change needed.

**N2. `copies` Collection Efficiency**
In `run_pass` (lines 410-418), the code globs *all* targets to build the `copies` dictionary for *all* delivered videos.
*   **Impact:** If there are many delivered videos and many target files, this is O(N*M) where N is delivered videos and M is total target files.
*   **Verdict:** **Acceptable.** The number of delivered videos is small (15 in the measured run). The number of target files is bounded by the runs. This is not a performance bottleneck compared to the `newest_mtime` walk (which GLM noted is the dominant cost).

**N3. `kept_copies` Double-Read of PROVENANCE**
`unit_videos` (line 139) reads `PROVENANCE.json` to extract video IDs. `kept_copies` (line 256) reads `PROVENANCE.json` again to get the hashes.
*   **Impact:** Double I/O and parsing.
*   **Verdict:** **Minor Inefficiency.** Not a bug. The files are small. The fail-closed behavior is consistent (if it fails in `unit_videos`, the pass stops; if it fails in `kept_copies`, it's treated as `prov=None` and videos become `unresolved`).

### 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Correctness** | 9/10 | 10/10 | The `kept_of` bug (C1-2) was a real defect in the logging/reporting logic that could mislead operators. It is now fixed. The fail-closed logic is robust. |
| **Concurrency** | 8/10 | 9/10 | The `_SHA` cache is protected by the `purge.lock` file lock. The `SHA_CACHE_MAX` bound prevents memory leaks. |
| **Performance** | 8/10 | 8/10 | The `newest_mtime` walk is still the dominant cost (GLM C7). The `copies` collection is acceptable. No new performance issues found. |
| **Test Coverage** | 8/10 | 9/10 | The new tests (C1-1, C1-2, C1-3, C1-4) cover the specific edge cases identified in Cycle 1. The `section_1.mp4` case is now tested. |

### 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1.  **`pipeline/ingest/purge.py` line 351 (`newest_mtime`):** The full `os.walk` of the unit directory to determine idleness is the dominant cost of the purge pass. For large runs with many render intermediates, this is expensive.
    *   *Recommendation:* Consider caching the `newest_mtime` per unit in the queue or a sidecar file, invalidated by file changes. Or, limit the walk to only the `sources/` and `run/sources/` directories if the rest of the unit is known to be static. (This is a pre-existing issue, not introduced by A19, but worth noting for future optimization).

**P3 LOW:**
1.  **`pipeline/ingest/purge.py` line 205 (`_SHA` cache):** The cache is cleared when it reaches `SHA_CACHE_MAX`. This is a simple LRU-like eviction (actually just a clear). A true LRU would be more efficient, but the current approach is sufficient for the expected scale.

### 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The change to `kept_copies` to return `{realpath: (video_id, why)}` and the corresponding update to `run_pass` to filter `kept_of` by `video_id` (C1-2) is the highest-leverage change. It ensures that the audit trail (`deleted.jsonl`) accurately reflects *which* copy was kept for *which* video, even when the file name does not match the video ID. This is critical for debugging and verifying the "One Copy Per Delivery" invariant.

### 7. PRODUCTION READY?

**Yes.**

The code is fail-closed, the race conditions are mitigated by the `purge.lock`, the memory leak is bounded, and the logging is accurate. The tests cover the critical edge cases, including the non-standard file name case. The performance characteristics are acceptable for the expected scale.