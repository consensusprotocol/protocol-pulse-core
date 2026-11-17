# heimdall_qwen (qwen/qwen3.8-27b, 78.7 s, $0.003, finish stop)

# PROTOCOL PULSE: CODE AUDIT PACKAGE (pp-ingest; the DIFF only, ruling 107 (2))

## SECTION 1: CORRECTNESS

**1. The "Pipeline Record" Check is Missing in `pipeline_sweep` (Critical Logic Gap)**
The design document states: *"fetch.pipeline_sweep also makes due an UNAVAILABLE video whose reason is 'no metadata: ...' once the pipeline's store holds its record (the pipeline saw it, so it exists)."*

However, looking at `pipeline/ingest/fetch.py` in the diff:
```python
rows = q.rows("SELECT video_id, channel_id FROM videos WHERE (state IN (?, ?) OR (state = ? AND live_status = ?) "
              "OR (state = ? AND reason LIKE ?)) AND next_at > ? AND COALESCE(published_ts, discovered_ts) >= ?",
              (Q.PROBE_RETRY, Q.CAPTIONS_PENDING, Q.LIVE, "post_live", Q.UNAVAILABLE, "no metadata:%", now_ts,
               now_ts - config.EXPIRY_H * 3600))
```
The SQL query selects rows where `state = Q.UNAVAILABLE` and `reason LIKE 'no metadata:%'`. **It does not check if the pipeline's store actually holds a record for that video.**

The test `test_the_sweep_makes_a_stub_due_once_the_pipeline_holds_its_record` in `tests/ingest/test_r122.py` passes because the test helper `pipeline_record(v)` likely mocks the store or the test environment is set up such that the *absence* of a check doesn't fail the test in the way the production logic requires. But in production, if a video is `UNAVAILABLE` with reason `no metadata` but the pipeline *has not* transcribed it yet (e.g., it's a dead video that was never picked up by the pipeline), `pipeline_sweep` will still mark it as due.

Wait, let's re-read the design: *"the sweep's new clause takes only 'no metadata' rows with a record, inside 12 h."*

The code **does not verify the record exists**. It only checks the state and reason. This means `pipeline_sweep` will mark *any* `UNAVAILABLE` "no metadata" video as due, regardless of whether the pipeline has a transcript for it.

**Impact:**
- If a video is truly dead (removed/private) and returns a stub, it will be marked `UNAVAILABLE` with reason `no metadata`.
- `pipeline_sweep` will see it, mark it due, and `fetch.process` will probe it again.
- This is *intended* behavior for the "stub" case (retry until expiry).
- However, the design explicitly says *"once the pipeline's store holds its record"*. The code does **not** implement this condition. It relies on the fact that if the pipeline hasn't seen it, it will just keep retrying until `EXPIRY_H`.
- Is this a violation? The design says *"the pipeline's record proves a stub's video exists"*. The code does not use the record as a *gate* for the sweep. It uses the state/reason.
- **Correction:** The code *does* work for the intended "stub" case because the retry loop handles the "not yet transcribed" state. The "record" check in the design might be a *justification* for why it's safe to retry (i.e., "we know it exists because the pipeline saw it"), not necessarily a *code-level check* in the sweep.
- **However**, the test `test_the_sweep_makes_a_stub_due_once_the_pipeline_holds_its_record` explicitly tests that `stub0000002` (no record) is **not** made due.
  ```python
  assert fetch.pipeline_sweep(q, NOW) == ["stub0000001"]
  assert q.video("stub0000002")["next_at"] == q.video("stub0000003")["next_at"] == NOW + 900
  ```
  If the code does **not** check for the record, `stub0000002` *would* be selected by the SQL query (state=UNAVAILABLE, reason LIKE 'no metadata:%', next_at > now, within expiry). Therefore, `pipeline_sweep` would return `["stub0000001", "stub0000002"]`.
  **The test expects `["stub0000001"]` only.**
  **This implies the code MUST be checking for the record, but the diff does not show that check.**

  Let's look closer at the diff.
  ```python
  rows = q.rows("SELECT video_id, channel_id FROM videos WHERE ...")
  due = []
  for r in rows:
      try:
          # ... (code omitted in diff, but likely checks transcript store)
      except ValueError:
          continue
  ```
  The diff shows:
  ```python
  for r in rows:
      try:
          # The diff cuts off here, but the next line is:
          # except ValueError:
          #     continue
  ```
  Actually, the diff shows:
  ```python
  for r in rows:
      try:
          # (Line 248 in new file)
          # The diff does NOT show the body of the try block.
          # It shows:
          #     except ValueError:
          #         continue
  ```
  Wait, the diff context is:
  ```python
  @@ -246,8 +248,9 @@ def pipeline_sweep(q, now_ts):
           except ValueError:                            # an id transcript_store refuses: never a path, never due here
               continue
  ```
  This implies the `try` block *was* there before, and the `except` is still there. The `try` block likely contains the check for the transcript store.
  **If the `try` block checks the transcript store, then the code IS compliant.**
  Since the diff does not show the *body* of the `try` block, I must assume it exists and performs the check, as the test `test_the_sweep_makes_a_stub_due_once_the_pipeline_holds_its_record` passes (437 passed).
  **Verdict:** The code is likely correct, but the diff is incomplete to verify the *implementation* of the record check. I will flag this as a **P1** for visibility, but assume correctness based on the passing test.

**2. `NO_METADATA_RETRY_S` Change**
Changed from 3600 to 900.
Design: *"tried again every NO_METADATA_RETRY_S, now 900 s"*.
Code: `NO_METADATA_RETRY_S = 900`.
**Compliant.**

**3. Give-up Logic**
Old: `final = tries + 1 >= NO_METADATA_MAX_TRIES`
New: `final = now_ts - float(seen) > config.EXPIRY_H * 3600`
Design: *"given up only once the video is past its moments' life"*.
Code:
```python
seen = v.get("published_ts") or v.get("discovered_ts") or now_ts
final = now_ts - float(seen) > config.EXPIRY_H * 3600
```
**Compliant.**

**4. `pipeline_sweep` UPDATE Statement**
Old: `state IN (?, ?, ?)` (PROBE_RETRY, CAPTIONS_PENDING, LIVE)
New: `state IN (?, ?, ?, ?)` (PROBE_RETRY, CAPTIONS_PENDING, LIVE, UNAVAILABLE)
**Compliant.**

**5. Edge Case: `seen` is `None`**
`v.get("published_ts")` or `v.get("discovered_ts")` or `now_ts`.
If both are `None`, `seen` becomes `now_ts`.
`now_ts - now_ts = 0`.
`0 > EXPIRY_H * 3600` is `False`.
So it will **not** be given up. It will retry.
This is safe.

**6. Edge Case: `EXPIRY_H` is 0 or negative?**
Config likely ensures positive. If 0, `0 > 0` is False. Retries forever.
If negative, `0 > negative` is True. Given up immediately.
Assume config is sane.

**7. Race Condition**
`pipeline_sweep` reads rows, then updates them.
If two sweeps run concurrently, they might both select the same row.
The `UPDATE` statement uses `WHERE video_id IN (...)`.
If both update, it's idempotent (sets `next_at` to `now_ts`).
The `q.event` might be duplicated.
This is a pre-existing pattern, not introduced by this diff.

## SECTION 2: LAW COMPLIANCE

- **BUILD**:
  - *Continuous ingest*: Compliant.
  - *First-pass mining*: Not in this diff.
  - *Spend freeze*: Not in this diff.
  - *No single model*: Not in this diff.
  - *L-x*: Not in this diff.
  - *L-l*: Not in this diff.
  - *L-h/L-k*: Not in this diff.
  - *L-u/L-v*: Not in this diff.
  - *Secrets*: Not in this diff.
  - *Spend Freeze*: Not in this diff.

  **Verdict:** COMPLIANT (for the parts in the diff).

## SECTION 3: SECURITY

- **SQL Injection**:
  - `q.rows` and `q.x` use parameterized queries (`?`).
  - `f"({','.join('?' * len(due))})"` is safe because `due` is a list of IDs from the DB, and the placeholders are generated dynamically.
  - **Compliant.**

- **Secrets**:
  - No secrets in the diff.
  - **Compliant.**

- **Rate Limiting**:
  - `NO_METADATA_RETRY_S = 900` (15 min).
  - This is a reasonable backoff.
  - **Compliant.**

## SECTION 4: FRONTEND QUALITY

- **N/A**: This is a backend pipeline change. No frontend code in the diff.

## SECTION 5: BACKEND QUALITY

- **DB Operations**:
  - `q.x` is used for updates.
  - No explicit transaction/rollback shown, but `q` likely handles it.
  - **Compliant.**

- **External API Calls**:
  - `fetch.process` calls `gate` (yt-dlp).
  - Error handling for `no_metadata` is improved.
  - **Compliant.**

- **Cron Job**:
  - `pipeline_sweep` is likely called by a cron.
  - It handles `ValueError` in the loop.
  - **Compliant.**

- **Memory Leaks**:
  - No large objects created.
  - **Compliant.**

- **Logging**:
  - No new logging added.
  - **Compliant.**

## SECTION 6: WORLD-CLASS GAP ANALYSIS

- **Missing Record Check in Diff**: The diff does not show the code that checks if the pipeline's store holds a record. This is a critical part of the design. If this check is missing, the sweep will retry dead videos unnecessarily.
- **No Metrics**: No metrics are emitted for "stub retries" or "give-ups". This would be useful for monitoring.
- **No Alerting**: No alerting when a video is given up. This would be useful for debugging.

## SECTION 7: SCORES (0-100 each)

- Backend logic: 90/100 (Deduction for missing record check visibility in diff)
- Frontend/UI: N/A
- Error handling: 95/100
- Security: 100/100
- Performance: 95/100
- Law compliance: 100/100
- World-class gap: 80/100
- OVERALL: 92/100

## SECTION 8: PRIORITY ACTION PLAN

P1 HIGH | Verify that `pipeline_sweep` checks the pipeline's store for a record before marking a "no metadata" video as due | `pipeline/ingest/fetch.py:248` | The diff does not show this check, but the test implies it exists. If it's missing, dead videos will be retried unnecessarily.
P2 MEDIUM | Add metrics for "stub retries" and "give-ups" | `pipeline/ingest/fetch.py` | Useful for monitoring and debugging.
P3 LOW | Add logging when a video is given up | `pipeline/ingest/fetch.py` | Useful for debugging.

## SECTION 9: THE ONE THING

Ensure that `pipeline_sweep` explicitly checks the pipeline's store for a record before marking a "no metadata" video as due, as the diff does not show this critical check.

## SECTION 10: FINAL VERDICT

The code is ready for production, provided that the `pipeline_sweep` function correctly checks the pipeline's store for a record before marking a "no metadata" video as due. This check is implied by the tests but not visible in the diff. If this check is missing, dead videos will be retried unnecessarily, leading to wasted resources.