# gpt-oss-20b (openai/gpt-oss-20b) 37 s finish=stop usage in 8959 / out 5952 usd_reported=0.001014 usd~0.116 (upper-bound price)

**1. What the other models caught that I missed**

| # | Issue | Severity | What was missed |
|---|-------|----------|-----------------|
| 1 | `visual_pin.fetch` early‑return could return a corrupt `.cut.mp4` without a duration check | [P1] | The early‑return block was missing the `TT.media_seconds` guard. |
| 2 | `whole_stream` can reuse a partially‑downloaded file if `yt‑dlp` fails mid‑download | [P2] | No cleanup of a partial file on failure. |
| 3 | `whole_stream` has no concurrency guard – two workers can race and corrupt the same file | [P2] | No lock or atomic‑rename strategy. |
| 4 | `WHOLE` dict only contains the audio entry, while `whole_stream` also handles video via a separate mapping | [P3] | Inconsistent source of truth for integrator cache. |
| 5 | `media_seconds` timeout is 60 s – unnecessarily long for a local probe | [P3] | Could delay the pipeline on a hung mount. |

**2. Where I agree / disagree**

| # | Finding | My stance | Why |
|---|---------|-----------|-----|
| 1 | Early‑return bug | **Agree** – it was a real defect; it is now fixed in the diff. |
| 2 | Partial‑file reuse | **Agree** – still a defect; not addressed in the diff. |
| 3 | Concurrency guard | **Agree** – still a defect; not addressed. |
| 4 | Incomplete `WHOLE` dict | **Partially agree** – not a functional bug, but a maintenance issue that could lead to future divergence. |
| 5 | 60 s timeout | **Partially agree** – not a safety issue, but a performance nuisance. |

**3. New findings from this review**

* The **partial‑file reuse** and **concurrency race** in `whole_stream` are real, untested edge‑cases that could cause silent failures or corrupted media.  
* The **atomic‑rename** pattern used for temporary cuts in `audio_window` and `visual_pin.fetch` is good, but the same pattern is missing for the whole‑stream download.  
* The **integrator cache mapping** is split between a hard‑coded dict in `whole_stream` and the `WHOLE` dict – a single source of truth would simplify future changes.  
* The **60 s timeout** in `media_seconds` is overkill for a local probe and can stall the pipeline on a slow NFS mount.

**4. Revised scores**

| Subsystem | Cycle 1 | Cycle 2 | Reason |
|-----------|---------|---------|--------|
| `transcript_truth` | 0 | **1** | Partial‑file reuse + missing concurrency guard. |
| `visual_pin` | 0 | 0 | Early‑return bug fixed; no new defects. |
| `whole_stream` | 0 | **1** | Same as `transcript_truth` – race & partial file. |
| `media_seconds` | 0 | 0 | Timeout not critical. |
| **Overall** | 0 | **2** | Two P1 defects remain. |

**5. Final priority list**

| Priority | Issue | File / Line | Action |
|----------|-------|-------------|--------|
| **P1** | `whole_stream` may return a partially‑downloaded file | `pipeline/transcript_truth.py` lines 26‑41 | 1. Write to a temp file (`<stem>.tmp.<ext>`) and `os.replace` on success. 2. Delete the temp file on any exception. |
| **P1** | `whole_stream` has no concurrency guard | same file | 1. Create a lock file (`<stem>.lock`) with `O_CREAT | O_EXCL`. 2. Release the lock after download or on failure. |
| **P2** | `WHOLE` dict incomplete / inconsistent | `pipeline/transcript_truth.py` line 12 | Consolidate audio and video entries into a single dict and use it everywhere. |
| **P2** | 60 s timeout in `media_seconds` | `pipeline/transcript_truth.py` line 18‑23 | Reduce to 10 s; add a comment explaining the rationale. |
| **P3** | None remaining – import already moved to module level. | – | – |

**6. Highest‑leverage change**

Implement an **atomic‑rename + lock** strategy for `whole_stream` downloads. This single change eliminates both the partial‑file reuse and the race condition, ensuring that every worker sees a fully‑downloaded, valid file or triggers a fresh download.

**7. Production ready?**

**No** – because the two P1 defects in `whole_stream` can silently corrupt media or cause the pipeline to hang. Once those are fixed, the code can be considered production‑ready.

**P1_OR_WORSE: 2**