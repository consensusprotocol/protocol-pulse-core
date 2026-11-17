# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 98.4 s, $0.003, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT — pp-ingest r122 (9df2df43)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

**Honest accounting:**

*   **Qwen caught a diff-visibility trap I glossed over:** My Cycle 1 walkthrough correctly stated the sweep clause was scoped to `UNAVAILABLE/no metadata` inside 12h, but I did not explicitly call out that the *diff excerpt* truncates the `try:` body at `fetch.py:246`. A reader of only the diff text could conclude the `pipeline_transcript()` gate was missing. Qwen flagged that as P1. I treated it as present because I had the full file context (`fetch.py:246 if pipeline_transcript(...) is not None: due.append`), but I should have made that explicit in the verdict — the diff alone is misleading. Qwen's confusion was legitimate on diff-only evidence.

*   **Muse caught nothing I missed on correctness.** Muse's Cycle 1 was `P0 CRITICAL: None — Ship it`, which aligns with my correctness verdict. Muse did not add new failure modes.

*   **What I caught that they missed/underweighted:** Both other models underweighted the operational risks I flagged:
    *   Qwen spent its analysis on the phantom missing-check and never evaluated `fetch.py:273-278` give-up logic (`tries` vs `EXPIRY_H`), `NO_METADATA_RETRY_S=900`, or the `WHERE next_at > ?` race guard.
    *   Muse dismissed N+1/LIMIT and broad-except concerns without quantifying them, but did not walk through the `float(seen)` falsy-0 edge or the `ValueError` silent-skip debuggability cost.

**Net:** No correctness bug was missed by me. Qwen's P1 was a false positive caused by truncated diff context, correctly refuted in `C1_CONSENSUS.md` with `fetch.py:246` and `test_r122.py: M49/M50`.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Source | Agree? | Why |
|---------|--------|--------|-----|
| **Sweep must check pipeline store before making `no metadata` due** | Qwen P1 | **Agree with intent, Disagree it is missing** | The check exists and is unchanged by this diff: `fetch.py:246 pipeline_transcript(r["video_id"], r["channel_id"]) is not None` inside the `for r in rows:` loop. The new `OR (state=? AND reason LIKE ?)` clause feeds rows *into* that same loop, so they are gated identically to `PROBE_RETRY/CAPTIONS_PENDING/LIVE post_live`. Test `test_the_sweep_makes_a_stub_due_once_the_pipeline_holds_its_record` proves it: `stub0000002` (no record) is NOT made due, `stub0000001` (with record) is. Qwen's reading was based on truncated diff. |
| **P0 CRITICAL: None, ready for production** | Muse | **Agree** | Logic is correct for claimed fix. No wrong variable, no data loss, no law violation. |
| **Add LIMIT to sweep SELECT (10k rows stall)** | Muse P1 (refuted) | **Disagree as P1, Agree as observation** | Consensus refutation is correct: `SELECT` is bounded by `COALESCE(published_ts,discovered_ts) >= now-12h AND next_at > now AND state IN (...)`. At current ingest volume this is dozens, not thousands. `PIPELINE_RECHECK_S=1800s` (30m). No LIMIT needed for correctness. My Cycle 1 P1 on this was overstated — downgrade to P2 hygiene. |
| **Wrap loop body in broad except** | Muse P1 (refuted) | **Disagree** | `pipeline_transcript()` at `fetch.py:184` already catches `OSError, ValueError, KeyError, TypeError, AttributeError` per file. Sweep's `except ValueError: continue` at `fetch.py:247-248` is specifically for `transcript_store` id validation. Broad except would hide bugs. Current is correct. |
| **Stub give-up on EXPIRY_H not tries, 900s retry** | My Cycle 1 | **Re-affirm** | `fetch.py:38 NO_METADATA_RETRY_S=900` and `fetch.py:273-278 final = now - seen > EXPIRY_H*3600` correctly fix CoinDesk bug (4 live probes + 2 stubs = 6 tries premature give-up). `test_r121.py:28-29` with `tries=99` still retries proves it. Neither other model walked this, but it is the core fix. |

## 3. NEW FINDINGS FROM THIS REVIEW

Combined analysis reveals no new correctness bug. What it reveals is **where Cycle 1 over-flagged operational hygiene as blocking:**

1.  **N+1 is not a P1 at this scale — but remains unbounded in code.** Consensus is right that `r119 C1_CONSENSUS.md` already litigated this: same `pipeline_sweep` code, same bound (transcript waits inside 12h). However, the bound is *operational* (current channel count), not *code-enforced* (no `LIMIT`, no metric). If partner adds channels, sweep latency grows linearly with `stat()` calls. This is not a ship-blocker, but it is the only latent scalability risk in this diff. Downgrade from P1 to P2.

2.  **Silent `except ValueError: continue` is intentional, not a bug.** I flagged this as P2 debuggability. Consensus clarifies: `transcript_store` refuses malformed ids by raising `ValueError` — those ids should never be due via this path. Logging them would be noise. Correct to silently skip. My P2 stands only as "consider debug-level log", not required.

3.  **`float(seen)` falsy-0 edge is real but unreachable.** `seen = v.get("published_ts") or v.get("discovered_ts") or now_ts` — if `published_ts=0` (epoch), it falls through. DB default is `discovered_ts=now_ts` at insert, and YouTube `published_ts` is never 0 for real videos. No fix needed. Noted for completeness.

4.  **No new law compliance issue.** All three reviewers agree: diff is narrowly scoped to `fetch.py` ingest retry/sweep, touches no model, no ledger, no queue, no transcript writer. `BUILD`, `L-x`, `L-l/L-j/L-m`, `L-h/L-k`, `SPEND FREEZE` all COMPLIANT.

**No new P0/P1 found in Cycle 2.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| **Correctness — stub retry/give-up** | 9/10 | **10/10** | Re-verified `tries` no longer gates, `EXPIRY_H` gates, 900s interval. Qwen's phantom missing-check refuted with `fetch.py:246` + M49/M50. No bug. |
| **Correctness — pipeline_sweep scoping** | 9/10 | **10/10** | Correctly scoped to `no metadata` inside 12h, other `UNAVAILABLE` untouched (`gone0000001`), outside 12h untouched (`stub0000003`), no-record untouched (`stub0000002`). `WHERE next_at > ?` race guard correct. |
| **Production risk — N+1 / unbounded SELECT** | P1 | **P2** | Consensus evidence accepted: bound is operational (dozens inside 12h), sweep every 30m. Not blocking. Remains as hygiene. |
| **Debuggability — silent ValueError** | P2 | **P3 (info)** | Intentional per `transcript_store` contract. No log needed. |
| **Law Compliance** | COMPLIANT | **COMPLIANT** | No change. All reviewers agree. |
| **Overall Ship Confidence** | Ship with notes | **Ship** | No blocking issue. Suite 437 passed, M44-M50 7/7 killed. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL — Must fix before ship:**
*   None.

**P1 HIGH — Should fix before ship:**
*   None. All Cycle 1 P1s refuted with evidence (`fetch.py:246` gate, `fetch.py:184` per-file except, operational bound).

**P2 MEDIUM — Fix next cycle / hygiene (not blocking):**
*   `fetch.py:239-247 pipeline_sweep` — Consider adding `LIMIT 500` or metric `sweep_rows_scanned` to make operational bound code-visible. Currently unbounded SELECT + N `stat()` calls. Safe at current scale (dozens), but no code guard if channel count 10x. Low cost, high future-proofing.
*   `fetch.py:273 seen = ... or ...` — Consider `v.get("published_ts") if v.get("published_ts") is not None else ...` to handle `0` correctly. Not reachable today, but removes falsy-0 footgun.

**P3 INFO:**
*   `fetch.py:247-248 except ValueError: continue` — Optionally add `logger.debug("sweep skip invalid id %s", r["video_id"])` for debuggability. Not required.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Ship r122 as-is** — it correctly fixes premature give-up of real streams that transiently return stubs by gating on `EXPIRY_H` not `tries` and narrowly promoting only `no metadata` stubs with pipeline records inside 12h; no code change is higher leverage than merging this fix.

## 7. PRODUCTION READY?

**Yes — Production Ready, no conditions.**

*   Correctness verified: `fetch.py:38` (900s), `fetch.py:239-242` (scoped SELECT), `fetch.py:246` (pipeline record gate), `fetch.py:251-253` (next_at guard), `fetch.py:273-278` (EXPIRY_H give-up).
*   Tests: `tests/ingest 437 passed`, mutations `M44-M50 7/7 killed`, `test_r122.py` covers all 4 sweep cases (with record / no record / outside 12h / other UNAVAILABLE) + post-sweep `TRANSCRIBED` via whisper.
*   Laws: COMPLIANT (no model, no ledger, no queue change).
*   Cost: $0.0069 of $1.00 cap.

No rollback plan needed beyond existing `EXPIRY_H` expiry — worst case a stub retries 48x in 12h (1 probe/15m), negligible load.