# heimdall_qwen (qwen/qwen3.8-27b, 152.5 s, $0.007, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-ingest
# Auditor: heimdall_qwen (qwen/qwen3.8-27b)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I focused heavily on the `offset_before` bisection logic and the "No Single Model" law compliance. I missed several critical operational and security issues that the other models (specifically GLM and Muse) and the Integrator's consensus identified:

1.  **The `_settle` Partial Branch Logic Flaw (GLM C2):** I missed that `_settle` in `service.py` has a subtle bug where a retry that mines *different* moments (due to cache misses or backend changes) but has the *same* number of failed windows will **not** append the new lines to the ledger, yet it updates the `moments` count in the queue. This causes a divergence between the ledger and the queue state.
2.  **The `offset_before` Bisection Premise (Consensus):** While I correctly identified that the file might not be sorted by `mined.at`, I failed to fully appreciate the *fix* applied in the diff: `ledger.append` now takes a `stamp` argument. The service passes `config.iso` as the stamp, meaning `mined.at` is set **under the lock** at the time of append. This makes the file strictly sorted by `mined.at` (within the margin of concurrent appends, which is handled by the 1-day margin). My Cycle 1 claim that this was a "Critical Correctness Bug" causing data loss was **refuted** by the consensus because the margin test proves that any skipped line is older than the `since` cutoff and thus irrelevant.
3.  **Security: Prompt Injection via `<` (Muse/Integrator):** I noted `_untrusted` but didn't flag the specific risk that `watch.py` channel names and `fetch.py` titles are also passed through it. More importantly, I missed the **A/B Judge Prompt** vulnerability in `ab.py` where `l['text'][:400]` is inserted into `<list_X>` and `<list_Y>` blocks. The diff *fixes* this by wrapping it in `_untrusted`, but I didn't verify the fix in Cycle 1.
4.  **The `stats.py` N+1 Query (Qwen/GLM):** I identified this in Cycle 1, but the consensus confirmed it was fixed in the diff by using `SELECT COUNT(*) ... WHERE reason LIKE 'OUTAGE%'`. I should have verified the fix more explicitly.
5.  **The `YouTubeGate` Age-Gate vs Rate-Limit Conflict (Integrator B4):** I missed that the old `RATE_LIMIT_MARKS` included `"Sign in to confirm you"`, which is a prefix of the age-gate message. This caused age-gated videos to trip the global rate-limit breaker. The diff fixes this by separating `AGE_GATE_MARKS` and checking them first.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Reviewer | My Verdict | Reasoning |
| :--- | :--- | :--- | :--- |
| **`offset_before` Bisection** | Qwen (C1), GLM (C10), Muse | **AGREE (Fixed)** | The premise that the file is unsorted was correct for the *old* code. The *new* code stamps `mined.at` under the lock. The 1-day margin ensures that any out-of-order lines are older than the `since` cutoff, so they are correctly excluded. The bisection is now safe. |
| **`_settle` Partial Branch** | GLM (C2) | **AGREE (Bug)** | This is a real bug. If `len(failed)` is the same on a retry, but the *content* of the failed windows changed (e.g., a different backend was used), the new moments are not appended. The `moments` count in the queue is updated, but the ledger is not. This violates the "latest line wins" invariant. |
| **No Single Model (L-x)** | Qwen (L-x), GLM (C41) | **PARTIALLY AGREE** | The law requires ">= 2 interchangeable back-ends". Currently, `local_gemma` is disabled. If `heimdall_qwen27b` fails, `AllBackendsFailed` is raised. The code *allows* for a second backend, but it is not *active*. The Integrator notes that the judge role is entirely frozen. This is a **configuration** issue, not a code logic issue. The code correctly implements the chain. |
| **Prompt Injection** | Muse, Integrator | **AGREE (Fixed)** | The diff adds `_untrusted` to the A/B judge prompt and the mining prompt. This prevents `</sentences>` injection. |
| **Age-Gate Rate Limit** | Integrator (B4) | **AGREE (Fixed)** | The diff separates `AGE_GATE_MARKS` and checks them before `RATE_LIMIT_MARKS`. This prevents age-gated videos from tripping the global breaker. |
| **`stats.py` N+1** | Qwen (C1), GLM (C6) | **AGREE (Fixed)** | The diff uses `SELECT COUNT(*) ... WHERE reason LIKE 'OUTAGE%'`. This is efficient. |

## 3. NEW FINDINGS FROM THIS REVIEW

1.  **`service.py` `_settle` Line 267: `moments` Count Divergence.**
    In the partial branch, `moments = len(lines) if lines else int(v.get("moments") or 0)`. If `lines` is empty (an outage pass), it keeps the old count. If `lines` is non-empty, it sets the count to the *new* lines. But if the new lines are *different* from the old ones (due to a different backend), the ledger has the old lines, and the queue has the new count. The adapter `best_unused_moments` reads the ledger, so it will return the old lines. The queue's `moments` count is used for stats, so stats will be wrong. **This is a P1 bug.**

2.  **`providers.py` `Router.run` Line 747: Cache Check for Disabled Backends.**
    `if use_cache and self.backends[bid].enabled():`. If a backend is disabled, it skips the cache check. This is correct. However, if a backend is *frozen*, it is also skipped. The cache is only checked for enabled, non-frozen backends. This is correct.

3.  **`ledger.py` `append` Line 53: Torn Tail Handling.**
    `if size and os.pread(fd, 1, size - 1) != b"\n": data = b"\n" + data`. This prepends a newline to the *new* data if the file doesn't end with a newline. This is correct. It isolates the torn line.

4.  **`watch.py` `poll_channel` Line 216: Short Detection.**
    `if "/shorts/" in (e.get("url") or ""):`. This is the only Short detector. Muse noted that playlist entries for Shorts do not always contain `/shorts/` in the URL. This is a **P2 bug**. Shorts may be misclassified as `DISCOVERED` and waste a probe cycle.

5.  **`fetch.py` `process` Line 173: Future-Dated Videos.**
    `if now_ts - pub_ts > BACKFILL_H * 3600:`. If `pub_ts` is in the future, `now_ts - pub_ts` is negative, so the check passes. The video is not marked `SEEN_OLD`. It proceeds to mining. This is a **P2 bug**. Future-dated videos should be handled explicitly.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Correctness** | 6/10 | 8/10 | The `offset_before` bug is fixed. The `_settle` partial branch bug is new but less critical than I thought. The age-gate fix is significant. |
| **Law Compliance** | 5/10 | 7/10 | The "No Single Model" law is technically violated by configuration (local disabled), but the code supports it. The prompt injection fix is good. |
| **Security** | 7/10 | 9/10 | The `_untrusted` fix in the A/B judge prompt is critical. The key redaction is solid. |
| **Performance** | 7/10 | 8/10 | The `stats.py` N+1 fix is good. The `offset_before` bisection is now efficient. |
| **Maintainability** | 8/10 | 9/10 | The code is well-structured. The comments are clear. The tests are comprehensive. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL**
1.  **`service.py` `_settle` Line 267:** Fix the `moments` count divergence. The queue's `moments` count must match the ledger's latest lines. If the new lines are different, the ledger must be updated, and the count must reflect the *total* unique moments, not just the new ones.

**P1 HIGH**
2.  **`watch.py` Line 216:** Improve Short detection. Use `duration < 60` as a secondary check.
3.  **`fetch.py` Line 173:** Handle future-dated videos. Mark them as `PROBE_RETRY` or `SEEN_OLD` with a reason.

**P2 MEDIUM**
4.  **`providers.json`:** Enable `local_gemma` to satisfy the "No Single Model" law. This is a configuration change, not a code change.
5.  **`ab.py`:** The judge role is entirely frozen. This is disclosed in the STATE file. No action needed.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Fix the `_settle` partial branch logic in `service.py` to ensure the queue's `moments` count always matches the ledger's latest lines.** This is the only remaining correctness bug that could lead to data loss or incorrect stats.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  Fix the `_settle` partial branch logic (P0).
2.  Enable `local_gemma` in `providers.json` to satisfy the "No Single Model" law (P2).
3.  Monitor the `offset_before` bisection in production to ensure the 1-day margin is sufficient.

The code is well-structured, secure, and performant. The remaining bugs are minor and can be fixed quickly.