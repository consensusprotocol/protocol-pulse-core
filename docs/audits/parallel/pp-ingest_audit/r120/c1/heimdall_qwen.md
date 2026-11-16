# heimdall_qwen (qwen/qwen3.8-27b, 68.8 s, $0.003, finish stop)

# PROTOCOL PULSE: CODE AUDIT PACKAGE (pp-ingest; the DIFF only, ruling 107 (2))

## SECTION 1: CORRECTNESS

**Main User Flow Analysis:**
The change addresses a specific latency issue where `post_live` videos (streams that ended but are still processing) were stuck in a `LIVE` state, preventing the pipeline from ingesting their transcripts.

1.  **`fetch.process` Logic (fetch.py:295-300):**
    *   **Condition:** `if live == "is_live" or (live == "post_live" and pipeline_transcript(vid, chan["channel_id"]) is None):`
    *   **Behavior:** If `is_live`, it stays `LIVE`. If `post_live` but *no* transcript exists in the pipeline store, it stays `LIVE` (re-probe). If `post_live` and a transcript *does* exist, it falls through to the standard VOD processing logic.
    *   **Correctness:** This correctly implements the "take the record if available" logic.

2.  **Duration Fallback (fetch.py:308-310):**
    *   **Code:** `if live == "post_live" and not (isinstance(dur, (int, float)) and dur > 0): ... dur = common["duration"] = found[1].get("duration") if found else None`
    *   **Issue:** `found` is the result of `pipeline_transcript(vid, chan["channel_id"])`. In the previous block (line 295), we only know `found` is *not* None if we passed the `LIVE` check. However, `pipeline_transcript` is called again here. This is a redundant DB/IO call. More critically, if `found` is `None` (which shouldn't happen if we passed line 295, but could if the state changed or logic is flawed), `dur` becomes `None`. The subsequent check `if not isinstance(dur, (int, float)) or dur <= 0:` will catch this and set `PROBE_RETRY`. This is safe but inefficient.

3.  **`take_pipeline_transcript` Refusal (fetch.py:327-331):**
    *   **Code:** If `take_pipeline_transcript` returns `False` (refused), and `live == "post_live"`, it sets state to `LIVE` again.
    *   **Correctness:** This prevents a "stuck" state where a refused transcript blocks the video from ever being processed as a VOD. It correctly re-queues it for re-probing.

4.  **`pipeline_sweep` (fetch.py:227-245):**
    *   **SQL:** `WHERE (state IN (?, ?) OR (state = ? AND live_status = ?))`
    *   **Logic:** It now includes `LIVE` rows where `live_status` is `post_live`.
    *   **Correctness:** This ensures that if a `post_live` video is waiting for a transcript (which it now is, because it's not `LIVE` anymore in the "no record" case, but wait... if it *has* a record, it's processed immediately in `process`. If it *doesn't* have a record, it's `LIVE`. The sweep is for videos *waiting on a transcript*.
    *   **Critical Logic Gap:** The docstring says "every video waiting on a transcript... whose record is in the pipeline's store... is made due now".
    *   If a video is `LIVE` and `post_live`, it means `pipeline_transcript` returned `None` in `process`. Therefore, the record is **NOT** in the pipeline's store.
    *   The sweep calls `pipeline_transcript(vid, chan["channel_id"])` inside the loop (line 240). If it returns `None`, it `continue`s.
    *   So, the sweep *will* find `LIVE`/`post_live` rows, check if the transcript exists, and if it does, make it due. This is correct. It handles the race condition where the transcript appears between the `process` call and the sweep.

5.  **`stall.py` (stall.py:58-61):**
    *   **SQL:** `WHERE (state IN ({marks}) OR (state = ? AND live_status = ?))`
    *   **Logic:** Includes `LIVE`/`post_live` in the "waiting" set.
    *   **Correctness:** This allows the stall detector to recognize that a `post_live` video is waiting for its transcript to become available (or for the pipeline to finish processing).

**Race Conditions:**
*   **`pipeline_transcript` calls:** `fetch.process` calls `pipeline_transcript` at line 295 and again at line 309. If the transcript is written between these two calls, the first call returns `None` (stays `LIVE`), and the second call returns the record (sets duration). This is handled correctly by the logic flow.
*   **Sweep vs Process:** The sweep makes a video "due" (sets `next_at` to now). The next `process` call will then pick it up. If `process` runs before the sweep, it might stay `LIVE`. The sweep runs periodically, so this is a minor latency issue, not a correctness bug.

**Edge Cases:**
*   **Empty DB:** Handled by standard SQL.
*   **API Timeout:** `pipeline_transcript` likely handles its own timeouts (not visible in diff, assumed from context).
*   **Bad Input:** `live_status` is validated against `"is_live"` and `"post_live"`. Other values fall through to standard VOD logic.

## SECTION 2: LAW COMPLIANCE

*   **BUILD (Continuous Ingest):** **COMPLIANT.** The change ensures `post_live` videos are ingested as soon as the transcript is available, adhering to the "mine within 10 minutes" ruling.
*   **L-x (No Single Model, Ultron First):** **COMPLIANT.** No model calls are made in this diff. It only handles transcript ingestion and state management.
*   **L-l (Strict Schema, No Repair):** **COMPLIANT.** The code does not repair model replies. It only checks for the existence of a transcript record.
*   **L-h/L-k (Transcript Text):** **COMPLIANT.** The code does not modify transcript text.
*   **L-e (Word Timing):** **COMPLIANT.** The code does not handle word timing.
*   **L-u/L-v (Exclusions):** **COMPLIANT.** The code does not handle exclusions.
*   **Secrets:** **COMPLIANT.** No secrets are used.
*   **SPEND FREEZE:** **COMPLIANT.** No paid frontier vendors are called.

## SECTION 3: SECURITY

*   **SQL Injection:** **COMPLIANT.** All SQL queries use parameterized queries (`?` placeholders).
*   **Authentication Bypasses:** **N/A.** No routes are defined in this diff.
*   **Rate Limiting Gaps:** **N/A.** No external API calls are made in this diff.
*   **Secrets in Code:** **COMPLIANT.** No secrets are hardcoded.
*   **Unvalidated User Input:** **COMPLIANT.** `live_status` is validated against known values. `vid` and `channel_id` are assumed to be validated upstream.

## SECTION 4: FRONTEND QUALITY

**N/A.** This is a backend pipeline change. No frontend code is included in the diff.

## SECTION 5: BACKEND QUALITY

*   **DB Operations:** **COMPLIANT.** `q.x` and `q.rows` are used for DB operations. Error handling is assumed to be in the `q` object (not visible in diff).
*   **External API Calls:** **N/A.** No external API calls are made in this diff.
*   **Cron Job:** **COMPLIANT.** The `pipeline_sweep` and `stall.check` functions are designed to be called periodically. They handle errors gracefully (e.g., `try/except` in `pipeline_sweep`).
*   **Memory Leaks:** **COMPLIANT.** No large objects are created per-request.
*   **Logging:** **PARTIAL.** The code does not log errors explicitly. It relies on the `q` object to log events. This is acceptable if `q` is well-designed, but it's not visible in the diff.

## SECTION 6: WORLD-CLASS GAP ANALYSIS

*   **Redundant `pipeline_transcript` Call:** In `fetch.process`, `pipeline_transcript` is called twice (line 295 and line 309). This is inefficient. The result of the first call should be stored and reused.
*   **Lack of Explicit Logging:** The code does not log when a `post_live` video is processed or when a transcript is taken. This makes debugging difficult.
*   **No Metrics:** The code does not emit metrics for the number of `post_live` videos processed or the time taken to process them. This makes it hard to monitor the performance of the new feature.

## SECTION 7: SCORES (0-100 each)

*   **Backend logic:** 90/100 (Minor inefficiency with redundant DB call)
*   **Frontend/UI:** N/A
*   **Error handling:** 85/100 (Relies on `q` object, no explicit logging)
*   **Security:** 100/100 (Parameterized queries, no secrets)
*   **Performance:** 85/100 (Redundant DB call)
*   **Law compliance:** 100/100 (Complies with all laws)
*   **World-class gap:** 80/100 (Lacks metrics and explicit logging)
*   **OVERALL:** 90/100

## SECTION 8: PRIORITY ACTION PLAN

P1 HIGH | Remove redundant `pipeline_transcript` call in `fetch.process` | `pipeline/ingest/fetch.py:309` | The function is called at line 295 and again at line 309. Store the result of the first call and reuse it to avoid an unnecessary DB/IO operation.
P2 MEDIUM | Add explicit logging for `post_live` video processing | `pipeline/ingest/fetch.py:295-331` | Log when a `post_live` video is processed, when a transcript is taken, and when a transcript is refused. This will make debugging easier.
P2 MEDIUM | Add metrics for `post_live` video processing | `pipeline/ingest/fetch.py:295-331` | Emit metrics for the number of `post_live` videos processed and the time taken to process them. This will help monitor the performance of the new feature.

## SECTION 9: THE ONE THING

Remove the redundant `pipeline_transcript` call in `fetch.process` to improve performance and clarity.

## SECTION 10: FINAL VERDICT

This code is ready for production. It correctly implements the logic to handle `post_live` videos and ensures they are ingested as soon as their transcripts are available. The only minor issue is a redundant database call, which should be fixed for performance and clarity.