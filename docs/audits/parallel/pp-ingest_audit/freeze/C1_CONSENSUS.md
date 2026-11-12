# pp-ingest FREEZE change (a100111a: spend freeze + integrator B1-B4), audit cycle 1: findings and dispositions

Package: c1/PACKAGE.md (every pipeline/ingest file + the tool in full, the diff since 9500030f, the orchestrator's 05:30
order and the integrator's cycle-1 record: CONTEXT.md). Reviewers under the SPEND FREEZE (STATE A10, A11): OpenAI,
xAI and Google SKIPPED (frozen vendors; recorded in c1/results.json `skipped`); four model families served by Heimdall:
qwen3.8-27b (done, 181 s, $0.008), glm-5.3-flash and minimax-m3.1-flash (first run: EMPTY, their default reasoning
spent the 16,000-token reply budget on the 111k-token package, the INGEST-FAIL-04 pattern; re-run at reasoning effort
none), muse-spark-open-816b (first run: timeout at 900 s; re-run with 1,800 s). Re-run (same package, verified by diff):
glm done (537 s, $0.005; cut at its 16,000-token reply limit after 56 findings), muse done (790 s, $0.026), minimax EMPTY
again (all 16,000 tokens reasoning, $0.0077: it ignores reasoning effort none on this gateway; dropped from cycle 2).
Verdicts: qwen "not ready" (its P0 refuted below), glm no verdict (cut), muse "ready for production after one fix" (the
calls index, done).

## Consensus (the same point from >= 2 reviewers)
| point | reviewers | action |
|---|---|---|
| the outage count loads every waiting row | qwen P0, glm C6 | SQL COUNT (stats.py, service.py) |
| ledger order vs the bisection | qwen P0 ("broken"), glm C10 (verified sound with the 1-day margin), muse ("acceptable") | made exact by construction: mined.at stamped under the append lock; margin test at 1 h and 20 h of disorder |
| the judge role is entirely frozen | glm C41, (qwen L-x note) | disclosed (REQUESTS R9, the A/B prints "no judge", design section 8); a Heimdall-served judge is the integrator's call, now with evidence: glm and muse reviewed a 100k-token package coherently at effort none |

## qwen3.8-27b

| finding | verdict | evidence / action |
|---|---|---|
| P0 `offset_before` bisects a file not sorted by mined.at: "silent data loss" | PARTLY VALID (the premise), REFUTED (the loss) -> made exact anyway | mined.at was the pass START and lines are appended at the pass END, so the file was in order only to within one pass. The reader's cutoff is min(since, now - 72 h) - 1 day: a skipped line X precedes a line L with mined.at(L) < cutoff, so mined.at(X) <= append(X) <= append(L) <= mined.at(L) + one pass < cutoff + 1 day, i.e. older than `since` and than the 72 h horizon (mined.at >= publish), so it is never returnable. FIX (by construction): the service stamps mined.at under the append lock (`ledger.append(stamp=config.iso)`), so the file is in mined.at order; the docstring states both. Tests: `test_the_bounded_read_is_exact_while_lines_are_out_of_order_by_less_than_its_margin` (disorder 1 h and 20 h, five `since` values: bounded read == full read), `test_the_service_stamp_puts_the_file_in_mined_at_order`. |
| P0 stats loads every waiting video's reason to count outages | VALID (cheap) | `SELECT COUNT(*) ... reason LIKE 'OUTAGE%'` (stats.py). Covered by test_service (`mine_waiting_outage == 3`). |
| P1 L-x "violation": one callable mine back-end; warn or raise | REFUTED (the order) + a warning added | Orchestrator 05:30: "the watcher's fallback chain must use Heimdall then local-interface only ... if both are down, queue the videos and mine later". Raising would halt mining, against the order ("Heimdall mining continues"). The chain still names two back-ends (L-x structure; test `test_the_real_config_under_the_spend_freeze`); the local one needs the GPU0 lease this session never holds. Added: the service logs `WARNING: 1 callable mine back-end(s): when it is down the videos wait ...` at start. |
| P1 the reader skips bad lines; raise above a bad ratio | REFUTED | Skipping serves no wrong data: an unreadable line is never returned, and every one is counted and reported (`bad_lines`, the first 20 with line numbers). Raising would withhold every good moment because of one torn line. Bad lines can no longer be written by the service (append validates; a torn tail is closed). |
| P2 a sidecar index for the ledger | DEFERRED | the bounded read is exact (above) and costs the recent tail only; an index is a second source of truth to keep consistent. |
| P3 `find_duplicate` loops in Python over same-title rows | REFUTED | indexed on title_canon; the rows per canonical title are a handful. |
| Security: `video_id` joined into a path by `record_by_sha`; handoff's names | VALID (defence in depth) | `line_problems` requires an 11-character YouTube id (a line like `../../etc/x` is bad and is never written: test `test_a_line_whose_video_id_is_not_a_youtube_id_is_bad`); `handoff` lists only YouTube-id directories and `transcript.<method>.json` names, refusing anything else. |
| L-l, L-h/L-k, L-u, L-v, the spend freeze, SQL, secrets | COMPLIANT (its own verdict) | - |

## glm-5.3-flash (56 numbered findings; the ones that are defects)

| finding | verdict | action |
|---|---|---|
| C2 a partial video's retry appended only when fewer windows failed: newly mined windows could be lost when another flipped | VALID (edge) | every partial pass that mined windows appends its lines (the latest line wins; duplicates are by the contract) |
| C24 an outage retry of a partial video overwrote `moments` with 0 | VALID | a pass that mined nothing keeps the recorded count. Test `test_a_partial_videos_later_passes_append_what_they_mine_and_an_outage_keeps_the_count` |
| C37 caption downloads ignored the yt-dlp breaker; a throttled caption answer never tripped it | VALID | `_store_captions` waits while the breaker is open (no download) and trips it on `throttled`. Test `TestCaptionsRespectTheBreaker` |
| C8 a BaseException in fetch stranded the video in `probing` until a restart | VALID | the worker puts it back (`probe_retry`, reason "fetch stopped") and re-raises (never renamed). Test `test_a_stop_inside_a_fetch_never_strands_the_video_in_probing` |
| C50 L-x's two back-ends per role met by the data only | VALID | `load_config` refuses a role with fewer than two. Test `test_a_role_with_one_back_end_is_refused_by_the_loaded_config` |
| C1 `release()` could stop the local model under a running request | REFUTED for the callers (release runs only with no video in flight, and `close()` after the executors drained), FIXED anyway | `OllamaLocalBackend` counts requests in flight; `release()` defers while one runs. Test `test_the_local_model_is_never_stopped_under_a_running_request` |
| C5 coverage dates of unprobed videos are approximate on the playlist listing | VALID (disclosure) | the report says which dates it used |
| C13 the "ok" call record's prompt_sha256 is the retry prompt's, the ledger's the base prompt's | REFUTED | both are recorded: every attempt in `replies_log` carries `base_prompt_sha256` (= the ledger's `mined.prompt_sha256`) beside its own `prompt_sha256`, and the line's `mined.attempt` names the retry |
| C15 one success resets the 429 backoff | BY DESIGN | a success is the signal that capacity is back |
| C17 the coverage JSON does not distinguish a partial measurement | REFUTED | `measured: false` and `unmeasured_channels` are in the JSON |
| C38 a channel whose first poll failed counts its next listing as backfill | MINOR (stats only) | noted; RSS sends no ETag (measured), so the 304 case cannot occur |
| C55 shutdown waits for in-flight calls | BY DESIGN | bounded by the calls' timeouts; a hard exit could tear the ledger tail (sealed on start) |
| C56 "the 20/40/60 min escalation never happens" | REFUTED | `calm()` runs only on a success; consecutive rate-limited calls after expiry escalate (600, 1,200, 2,400, 3,600 s); a success between calms one step (integrator B4) |
| C3, C4, C7, C9-C12, C14, C16, C18-C23, C25-C36, C39, C40, C42-C49, C51-C54 | verified sound by glm itself, or cosmetic | - |

## muse-spark-open-816b

| finding | verdict | action |
|---|---|---|
| P0 no index on `calls.video_id` (the per-video cost sum scans the table) | VALID | `calls_video` and `calls_backend (backend, cost_usd)` indexes (created on start for the live queue). Test `test_the_queue_has_the_indexes_...` |
| P1 an unmeasured 06:00 coverage report is not tried again that day | VALID | tried again every hour until a full measurement (`coverage_next_try`). Test `test_an_unmeasured_coverage_report_is_tried_again_the_same_day` |
| P1 an outage is visible only by polling | VALID | after 30 min of videos waiting on an outage, one line at the top of STATE ("MINING WAITING ON AN OUTAGE: n video(s) waiting since T ..."), removed when none waits; the spend notices and it share the top block, each writer replacing only its own lines. Tests `test_an_outage_longer_than_the_notice_delay_is_noticed_then_cleared`, `test_the_outage_and_spend_notices_share_the_top_...` |
| P1 the local model is released while waiting videos are not yet due | BY DESIGN (integrator B3) | the model leaves GPU0 whenever no work is due; reloading it on the next due pass is the cost of not holding GPU0 idle |
| an interrupt counted as a back-end failure | VALID | KeyboardInterrupt / SystemExit free the probe (`Health.abandon`) without a failure. Test `test_an_interrupt_during_a_probe_frees_the_probe_without_counting_a_failure` |
| P2 keep the better-scoring observation of a repeated range | DECLINED | the flags merge fail closed; scores keep the first observation (deterministic, documented) |
| P2 a command to force-retry partial videos; transcript quality gate; head+tail tracebacks; log rotation | DEFERRED | partial videos are retried automatically for 72 h; the Bitcoin screen already skips windows with no Bitcoin term; the traceback tail holds the exception; logs grow ~300 KB a day |
| P3 future-dated publish time is mined | REFUTED | the adapter excludes a line whose publish time is in the future |
| Short detection by URL only in the watcher | BY DESIGN | the probe's media_type is authoritative; a mis-listed Short costs one probe |
