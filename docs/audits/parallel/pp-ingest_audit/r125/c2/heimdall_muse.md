# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 161.8 s, $0.003, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT — pp-ingest r125 (cfd3bb9a)

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Honest accounting:**

1. **Observability gap — they caught it, I underweighted it.** Both reviewers flagged the sweep's `is_live` path as unobservable. I noted "silent failure" on `ValueError` (fetch.py:250) but missed the larger point: the *happy path* itself was silent. A row made due via `acquired_at > state_at` looked identical in logs/queue events to any other `next_at` bump. Qwen P1 / Muse P1 correctly demanded the event carry `live_status`, `acquired_at`, `probed_at`. The fix (now in) — `pipeline_transcript_due` event with those fields + `service.py:272-275` logging — is the right call. I should have flagged it P1, not as a footnote.

2. **OSError crash claim — I correctly did NOT flag it, Muse did and was refuted.** Muse P1 claimed `pipeline_transcript()` could raise `OSError` and crash the sweep. Consensus correctly refutes: `fetch.py:184` catches `OSError, ValueError, KeyError, TypeError, AttributeError` per file, and unreadable dir → `glob → []`. I had this right by omission — I listed only `ValueError` as the sweep-level catch (transcript_store id check) and did not claim OSError crash. Point to me, but I should have explicitly stated the per-file catch to preempt the false alarm.

3. **Clock skew — Muse raised, consensus refuted, I missed both.** I did not consider clock skew between `state_at` and `acquired_at`. Muse P2 raised it; consensus refutes correctly: both timestamps are written on this single machine (`config.iso()` in watcher vs pipeline ingest), same clock. No NTP drift between hosts. I should have noted this explicitly as a non-issue — my silence left a gap.

4. **Claim atomicity — I flagged as "request to see", they closed it.** I left `queue.py:171-177 claim()` as an open question ("Request to see implementation"). Qwen + consensus closed it: `UPDATE ... WHERE video_id=? AND state IN (...)` under queue lock, sweep only moves `next_at`. Correct — no race. My hedging was unnecessary; the evidence was already in the diff context.

5. **24/7 stream probe storm — I missed entirely.** Muse P3 raised it, consensus refutes: `transcript_store` skips `is_live` streams, so a still-live stream gets no record; re-transcription = one probe. I did not consider this edge case at all. Low severity but real reasoning gap.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---------|---------|-----|
| **Correctness: `got > probed` gating + fail-closed** | **AGREE** | Both reviewers and I agree. `_zoned` strict, `None` → skip, `<=` → skip. Verified. |
| **Correctness: SELECT/UPDATE consistency** | **AGREE** | WHERE `(state=? AND live_status IN (?,?))` with `("post_live","is_live")` + UPDATE `state IN (4)` — consistent. I verified, they verified. |
| **Correctness: No-loop via `state_at` rewrite** | **AGREE** | `queue.py:166 set_state` + `queue.py:171-177 claim` both rewrite `state_at`. Next sweep sees `got <= probed` → skip. All three agree. |
| **Correctness: Never-taken while `is_live`** | **AGREE** | `fetch.process` unchanged, only `set_state(LIVE)` on `is_live`. Sweep only sets `next_at`. Unanimous. |
| **P1 Observability fix (event with 3 fields)** | **AGREE — was my miss** | Should have been P1 in my Cycle 1. Now fixed, M74 killed. Correct priority. |
| **Muse P1 OSError crash** | **DISAGREE with Muse, AGREE with consensus refutation** | `fetch.py:184` per-file catch + `glob→[]` on bad dir. No crash. I was correct not to flag. |
| **Muse P2 Clock skew** | **AGREE with refutation** | Single-machine clock, both writers use `config.iso()`. Not a real risk. I should have stated this. |
| **Muse P2 Verify claim() atomicity** | **AGREE with refutation** | `UPDATE WHERE video_id=? AND state IN (...)` under lock. Sweep only touches `next_at`. No race. My Cycle 1 "request to see" was overly cautious. |
| **Muse P3 24/7 probe storm** | **AGREE with refutation** | `transcript_store` skips `is_live` → no record → no trigger. One re-transcription = one probe. Correct. |
| **Qwen P3 Parallelise sweep** | **AGREE with refutation** | Few dozen rows, one glob each. N+1 bounded. I correctly called it "PRESENT but bounded" — not worth fixing. |
| **Qwen P2 Warning on missing `state_at`** | **AGREE with "recorded, not fixed"** | `add_video`, `set_state`, `claim` all set `state_at`. Missing → fail-closed. Warning would be noise. Correct to not add. |
| **Muse P2 Batch store reads** | **AGREE with "recorded"** | Same as my N+1 note. Small N, not worth batching. |
| **Muse P3 Log ValueError skips** | **PARTIALLY AGREE** | `transcript_store` ValueError = bad vid id → no folder can exist → skip is correct. Logging it would be low-value noise. But if `transcript_store` ever broadens what raises `ValueError`, silent skip hides bugs. A `debug` log would be cheap insurance. I flagged this in Cycle 1; consensus correctly deprioritizes to P3/recorded. |

## 3. NEW FINDINGS FROM THIS REVIEW

**Nothing that changes the ship decision.** Combined analysis is thorough. Three minor observations that nobody explicitly called out:

1. **Equal-timestamp edge is correct but undocumented.** `got <= probed` means equal timestamps do NOT trigger. This is correct (prevents re-trigger on same record if clocks align to the second), but the invariant is only implicit in code. The test `test_r125.py:33-42` covers it, and the event now logs both times for post-hoc audit. No code change needed — but a comment on the `<=` line would help future readers.

2. **The `next_at > now_ts` WHERE clause is doing double duty.** It both (a) excludes already-due rows from SELECT and (b) provides atomicity for the UPDATE (if `process` already made it due, UPDATE matches 0 rows). Qwen's race analysis spells this out correctly. This is subtle and correct — worth a comment in code, but not a bug.

3. **Test tamper in `test_r120.py:103-104` is load-bearing.** The `acquired_at="2026-01-01T00:00:00+00:00"` tamper makes the record older than probe, so r125 correctly leaves it. If someone removes that tamper thinking it's dead code, r120's invariant test will start failing (or worse, pass for wrong reasons). The test should have a comment explaining *why* the tamper exists (r125 gating). Minor — not blocking.

**No new P0/P1/P2 found.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| **Correctness** | 9/10 | 9/10 | No change. Logic verified by all three + mutations M69-M74 killed. -1 for N+1 (bounded, pre-existing). |
| **Observability** | 6/10 (implicit) | 9/10 | Was my blind spot. Now fixed: event carries `live_status/acquired_at/probed_at`, service logs made-due ids. +3. |
| **Robustness** | 8/10 | 9/10 | OSError, clock skew, claim atomicity, 24/7 storm all refuted with evidence. My open question closed. +1. |
| **Security** | 10/10 | 10/10 | Parameterized queries, no secrets, no injection. Unchanged. |
| **Law Compliance** | 10/10 | 10/10 | BUILD continuous ingest, L-j/L-m fail-closed, L-l strict schema all compliant. Unchanged. |
| **Overall** | **8.5/10** | **9.2/10** | Observability fix + refutations close all gaps. Remaining -0.8 is N+1 (cosmetic) + equal-timestamp comment (cosmetic). |

## 5. FINAL PRIORITY LIST

| Priority | Item | File:Line | Status |
|----------|------|-----------|--------|
| **P0 CRITICAL** | *None* | — | — |
| **P1 HIGH** | Sweep queue event must carry `live_status`, `acquired_at`, `probed_at` for `is_live` due rows | `fetch.py:258` (UPDATE path), `service.py:272-275` (log) | **FIXED** — M74 killed, `test_r125` reads event |
| **P2 MEDIUM** | Add comment on `got <= probed` explaining equal-timestamp non-trigger | `fetch.py:255-256` | Open — 1-line comment, not blocking |
| **P2 MEDIUM** | Add comment on `next_at > now_ts` double duty (filter + atomicity) | `fetch.py:242-258` | Open — 1-line comment, not blocking |
| **P3 LOW** | `debug` log on `ValueError` skip in sweep | `fetch.py:250` | Recorded — not blocking |
| **P3 LOW** | Batch `pipeline_transcript()` reads if row count grows | `fetch.py:248-256` | Recorded — few dozen rows, not blocking |
| **P3 LOW** | Comment on `test_r120.py:103-104` tamper explaining r125 gating | `tests/ingest/test_r120.py:103` | Recorded — not blocking |

**No P0. One P1 fixed. Three P2/P3 recorded as non-blocking.**

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The `is_live` observability event (now fixed) — without it, the sweep's most critical path (making a live stream due once) was invisible in logs and queue state, making the 10-minute ruling violation undetectable in production.

## 7. PRODUCTION READY?

**YES — with no conditions.**

All P0/P1 closed. Evidence:
- `tests/ingest` 449 passed
- Mutations M69-M74: 6/6 killed (M74 specifically guards the observability fix)
- `test_r125` passes unmutated in guarded environment
- No-loop, never-taken, fail-closed all verified by three independent reviewers + mutation testing
- Race, crash, skew, storm all refuted with code evidence

Ship it.