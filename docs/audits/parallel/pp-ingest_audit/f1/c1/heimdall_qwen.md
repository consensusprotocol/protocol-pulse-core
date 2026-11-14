# heimdall_qwen (qwen/qwen3.8-27b, 197.0 s, $0.022, finish stop)

## SECTION 1: CORRECTNESS

**The core logic is sound.** The `calibrate` function correctly implements the "fresh" mode by passing `use_cache=not fresh` to `router.run`. The retry loop correctly identifies unanswered probes (`ans is None`) and re-queues them for the next round. The aggregation logic correctly iterates over the original `jobs` list and looks up the final answer in the `answers` dictionary, ensuring that if a probe is answered in round 2, that answer is used, and if it remains unanswered after all rounds, it is counted as `unmeasured`.

**Potential Race Condition in `service.py` (Low Risk):**
In `service.py` line 489, `self.check_allowed` is read and then `flagcheck.watcher_checkers` is called. If two threads were to call `check_once` simultaneously (which shouldn't happen given the single-threaded loop design, but `check_once` is a public method), they could both trigger a calibration. However, since `check_once` is only called from the `check` loop thread (line 756), this is not a practical issue.

**Edge Case: `rounds` parameter in `calibrate`:**
If `rounds` is 0, `max(1, int(rounds))` ensures at least one round is executed. This is correct.

**Edge Case: `fresh` mode with `use_cache=False`:**
When `fresh=True`, `use_cache=False` is passed to `router.run`. This ensures that the model is actually called, and the reply is not fetched from the cache. This is the correct behavior for F1.

**Edge Case: `watcher_checkers` with `rounds=CALIBRATION_ROUNDS`:**
`watcher_checkers` calls `calibrate` with `fresh=True` and `rounds=rounds`. This is correct.

**Edge Case: `check_once` scheduling logic:**
The logic for `self.check_recal_s` is:
- If `self.check_allowed` is not empty (some backends passed) OR `could` is empty (no backends could pass, i.e., all answered wrong), set `self.check_recal_s = CHECK_RECALIBRATE_S` (1 day).
- Else (no backends passed, but some could pass, i.e., some unanswered), if `self.check_recal_s >= CHECK_RECALIBRATE_S`, reset to `CHECK_RETRY_S` (600s). Else, double it, capped at `CHECK_RECALIBRATE_S`.

This logic is correct. It ensures that if a calibration fails due to an outage (unanswered), it retries quickly (doubling backoff), but if it fails because the model is bad (answered wrong), it waits a day.

**No N+1 query problems.** The code uses SQLite with appropriate indexes.

**No silent failures.** Errors are logged and handled.

## SECTION 2: LAW COMPLIANCE

- **L-x NO SINGLE MODEL, ULTRON FIRST:** COMPLIANT. The `flagcheck` role has two backends (`heimdall_glm53flash`, `heimdall_muse`). The `mine` role has two backends (`heimdall_qwen27b`, `local_gemma`).
- **L-l a model reply counts only whole:** COMPLIANT. The `validator` in `flagcheck.py` strictly validates the JSON response.
- **L-j / L-m: fail closed; nothing measured is never a pass:** COMPLIANT. `watcher_checkers` only allows backends that answered *every* calibration quote right. Unanswered quotes are not counted as right.
- **L-h / L-k: transcript text is read as spoken:** COMPLIANT. The code uses `eligibility.spoken` for text.
- **L-u hard exclusions:** COMPLIANT. The `flagcheck` role is used to verify hard flags.
- **Secrets:** COMPLIANT. Keys are read from the env file.
- **SPEND FREEZE:** COMPLIANT. The `flagcheck` role uses Heimdall backends, which are not frozen.

## SECTION 3: SECURITY

- **SQL injection:** No raw SQL queries with user input.
- **Authentication bypasses:** N/A (internal service).
- **Rate limiting gaps:** The `Router` has backoff and circuit breakers.
- **Secrets in code:** No hardcoded secrets.
- **Unvalidated user input:** The `flagcheck` prompt includes untrusted text from the video, but it is wrapped in `<quote>` tags and marked as untrusted. The `validator` ensures the response is strict JSON.

## SECTION 4: FRONTEND QUALITY

N/A (no frontend).

## SECTION 5: BACKEND QUALITY

- **DB operations:** SQLite with WAL mode. Appropriate error handling.
- **External API calls:** Timeouts and retries are handled by the `Router`.
- **Cron job:** The service is a long-running process, not a cron job.
- **Memory leaks:** No obvious memory leaks.
- **Logging:** Errors are logged with context.

## SECTION 6: WORLD-CLASS GAP ANALYSIS

The code is well-structured and follows the design document closely. The use of a `Router` for model calls is a good abstraction. The `flagcheck` module is well-designed with strict validation and calibration.

One potential improvement: The `calibrate` function could be optimized to stop early if all backends have passed, but this is a minor optimization.

## SECTION 7: SCORES (0-100 each)

- Backend logic: 95/100
- Frontend/UI: N/A
- Error handling: 95/100
- Security: 95/100
- Performance: 90/100
- Law compliance: 100/100
- World-class gap: 90/100
- OVERALL: 95/100

## SECTION 8: PRIORITY ACTION PLAN

P2 MEDIUM | Add early termination to `calibrate` if all backends have passed | `pipeline/ingest/flagcheck.py:295` | Minor performance improvement.
P3 LOW | Add a test for `calibrate` with `rounds=0` | `tests/ingest/test_flagcheck.py` | Edge case coverage.

## SECTION 9: THE ONE THING

The code is production-ready. The only thing that could be improved is adding early termination to the `calibrate` function to save API calls when all backends have passed.

## SECTION 10: FINAL VERDICT

This code is ready for production. It is well-structured, follows the design document, and complies with all governing laws. The only minor improvement is adding early termination to the `calibrate` function.