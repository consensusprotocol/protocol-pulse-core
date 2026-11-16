# heimdall_qwen (qwen/qwen3.8-27b, 51.2 s, $0.002, finish stop)

# PROTOCOL PULSE: CODE AUDIT REPORT (pp-ingest; r118) — CYCLE 2

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I was overly optimistic, labeling the code "production-ready" and dismissing potential race conditions as "safe" based on logical flow rather than concurrent execution reality.

**Key Misses:**
1.  **The `pipeline_captions_refused` Failure Mode (P1):** I stated that returning `False` on a torn read was "Correct." I missed that this is a **fail-open** security/reliability flaw. If the main tree's circuit breaker file is being written (torn read), the pipeline *should* assume the breaker is open (return `True`) to avoid hammering YouTube. Returning `False` allows the pipeline to proceed, potentially violating rate limits or the "no single model/vendor hammering" spirit of the law.
2.  **The `stall.check` Horizon Logic (P2):** I marked the `COALESCE(published_ts, discovered_ts)` logic as "Correct." I missed the edge case where `published_ts` is NULL (unprobed) and `discovered_ts` is recent. This keeps "old" videos in the "waiting" pool longer than intended, inflating the stall count and potentially delaying the "act" trigger for genuinely stalled items.
3.  **The `take_pipeline_transcript` Validation Gap (P1):** I dismissed the `FileExistsError` catch as "Correct." I missed that if a *corrupt* file exists at `dst` (from a previous crash or manual intervention), the function returns `True` without validating the content. The downstream `_store_captions` relies on `canonical_transcript` to re-hash, but if the file is corrupt, `canonical_transcript` will raise an error, causing the *entire* ingest for that video to fail, rather than just skipping the pipeline transcript and falling back to captions.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Source | My Verdict | Reasoning |
| :--- | :--- | :--- | :--- |
| **`downsignal.py` NameError** | Muse (P0) | **Disagree (Refuted)** | As Claude's consensus noted, `paths` is an argument to `__init__`. The code `state_path or paths["signal_state"]` is valid. Muse hallucinated a missing import. |
| **`pipeline_captions_refused` Fail-Open** | Muse (P1) | **Agree** | I was wrong in Cycle 1. A torn read of the circuit breaker file should be treated as "breaker open" (True) to be conservative. Returning `False` risks rate-limit violations. |
| **`stall.check` Horizon Inflation** | Muse (P1) | **Agree** | I was wrong in Cycle 1. Using `discovered_ts` for unprobed videos keeps them in the "active" window longer than the 12h expiry intent suggests. This is a logic bug, though low severity. |
| **`take_pipeline_transcript` Corrupt File** | Muse (P1) | **Agree** | I was wrong in Cycle 1. Returning `True` on `FileExistsError` without validation is risky. It assumes the existing file is valid. If it's corrupt, the pipeline fails hard instead of gracefully falling back. |
| **`stall.line` None Type Error** | Qwen (Self) | **Agree (Fragile)** | My Cycle 1 analysis was correct: it *is* safe due to the control flow, but it is fragile. If the `kv_set` fails silently or the key is deleted externally, it crashes. |
| **`os.link` Race Condition** | Qwen (Self) | **Agree (Safe)** | My Cycle 1 analysis was correct. `os.link` is atomic. The `FileExistsError` catch is the correct mitigation. |

## 3. NEW FINDINGS FROM THIS REVIEW

**Finding 1: `stall.act` Burst Behavior (P2)**
Muse suggested that `stall.act` making 50 videos "due" at once could cause a burst of yt-dlp calls. I verified this in Cycle 1 and dismissed it. However, re-reading `service.py`, the fetch loop *does* limit concurrency to `YTDLP_CONCURRENCY` (3). So the burst is throttled. **Verdict: Not a bug, but worth documenting.**

**Finding 2: `pipeline_transcript` Non-Deterministic Selection (P2)**
Muse noted that `sorted(glob.glob(...))` picks the last file if ranks are tied. I verified that `METHOD_RANK` is unique per slug. **Verdict: Not a bug.**

**Finding 3: `fetch.process` Early Return Logic (P1)**
If `take_pipeline_transcript` returns `True` (file exists), we call `_store_captions`. If the file is corrupt, `_store_captions` fails. The code does *not* fall back to downloading captions. This is a **P1** because it breaks the "continuous ingest" law if the pipeline transcript is corrupt. The system should fall back to captions if the pipeline transcript is invalid.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Correctness** | 9/10 | 7/10 | Downgraded due to `pipeline_captions_refused` fail-open and `take_pipeline_transcript` corrupt file handling. |
| **Law Compliance** | 10/10 | 9/10 | Downgraded slightly because the fail-open behavior in `pipeline_captions_refused` risks violating rate-limit laws (L-x/L-h). |
| **Robustness** | 8/10 | 6/10 | Downgraded due to fragile `stall.line` and lack of fallback in `fetch.process`. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL**
*   None. The `downsignal.py` P0 was refuted.

**P1 HIGH**
1.  **`pipeline/ingest/fetch.py:42-48`**: Change `pipeline_captions_refused` to return `True` on `OSError`/`ValueError` (torn read). **Reason:** Fail-closed is required for rate-limit protection.
2.  **`pipeline/ingest/fetch.py:185-200`**: In `take_pipeline_transcript`, if `os.path.exists(dst)` is `True`, validate the file (hash check) before returning `True`. If invalid, delete it and proceed with copy. **Reason:** Prevents hard failures on corrupt pipeline transcripts.
3.  **`pipeline/ingest/fetch.py:285-286`**: If `_store_captions` fails due to a corrupt pipeline transcript, fall back to downloading captions. **Reason:** Ensures continuous ingest.

**P2 MEDIUM**
1.  **`pipeline/ingest/stall.py:48`**: Use `published_ts` only if not NULL, else use `discovered_ts` but apply a stricter horizon (e.g., 6h) for unprobed videos. **Reason:** Prevents inflation of "waiting" count.
2.  **`pipeline/ingest/service.py:806-835`**: Add a `try/except` around `float(self.q.kv_get("stall_acted"))` to handle `None` gracefully. **Reason:** Prevents crash if KV store is corrupted.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Fix the `pipeline_captions_refused` fail-open behavior to fail-closed.** This single change prevents the pipeline from hammering YouTube when the main tree's circuit breaker is in a transient state, protecting the entire system from rate-limit bans.

## 7. PRODUCTION READY?

**No.**

**Conditions for Production Readiness:**
1.  Fix `pipeline_captions_refused` to return `True` on read errors (P1).
2.  Add validation to `take_pipeline_transcript` for existing files (P1).
3.  Add fallback logic in `fetch.process` if pipeline transcript is corrupt (P1).
4.  Add defensive coding in `stall.line` for `None` KV values (P2).

Until these are fixed, the system is at risk of rate-limit violations and hard failures on corrupt data.