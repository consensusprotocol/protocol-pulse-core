# F1 (the flag check's calibration asks the models live), cycle 1: consensus

Reviewers (Heimdall): qwen3.8-27b (197 s, $0.022): "production-ready"; glm-5.3-flash (306 s, $0.006): "ready for
production ... Before merge: confirm the unseen `_router` fixture's `transport_retries` ... add the crash-path
backoff"; muse-spark-open (602 s, $0.031): "ready for production ... a surgical, well-tested fix for a genuine L-m
violation". Each finding checked against the code. Cycle 1: $0.059. Diff reviewed: 0abeb304 against 159c6709.

## Agreed by all three (verified)
- The fix does what it claims: `calibrate(fresh=True)` passes `use_cache=False`, so the router's cache branch
  (providers.py run) is never taken and every quote reaches the model; a live reply still refreshes the cache file.
- The rounds loop aggregates each (back-end, quote) once from the final `answers`; only unanswered quotes are re-asked;
  a back-end with no effective entry gets no jobs and no admission; `max(1, int(rounds))` guards 0.
- The schedule is bounded: 600 -> 1200 -> ... -> 86400, then back to 600; a pass or an all-wrong result -> daily; at
  least 600 s between failed calibrations; no tight loop (`check_calibrated` is set after the calibration returns).
- Fail closed: an unanswered quote never counts as right (`of == len(probes) and right == of`); no checker -> every
  flag stands.

## Fixed (each with a test)
- C1-1 (glm P0, one reviewer, verified): a calibration that RAISES (any exception out of watcher_checkers, e.g. after
  its live calls) left `check_calibrated` unchanged, so the check loop would run it again every 30 s; the old cached
  calibration made that path free, the live one would not. Now `Service._calibrate_checkers` catches it: an event
  `check_calibration_crash` (traceback), nobody answers (`check_allowed = []`: an earlier allowance is not kept;
  nothing measured), the stored calibration is emptied, and the next calibration follows the same doubling wait as
  an unanswered one. Test: test_service test_f1_a_calibration_that_crashes_fails_closed_and_waits_like_an_unanswered_one
  (fails on 0abeb304: the RuntimeError escapes).
- C1-2 (glm P1, verified): the wrong answers were discarded after the calibration. The stored calibration (queue kv
  `check_calibration`, live.json `second_model_checks_12h.calibration`) now carries per back-end `wrong` (flag,
  expected, answered, the quote's first 80 characters) and the log line names them. Test: test_service
  test_f1_a_checker_that_answers_a_quote_wrong_waits_for_the_daily_calibration (fails on 0abeb304: KeyError 'wrong').
- C1-3 (glm P2, muse P3): the calibration's duration (`seconds`) is stored and logged ("asked live, N s").
- C1-4 (glm P3): `asked_at` is the calibration's START, the same for every back-end of one calibration; the design
  said "per back-end". The design now says what it is (the start) next to `seconds` (its duration).
- C1-5 (glm P1 "the test's arithmetic depends on an unseen fixture constant"): the fixture is tests/ingest/helpers.py
  router_cfg, `throttle.transport_retries: 2`, so the asserted 3 / 4 calls were right; the test now derives the
  per-run call count from the router's own config (1 + transport_retries) and asserts the role has no override, so it
  holds for any value.

## Refuted or recorded
- glm P2 "treat a back-end whose calls were all SKIPPED as daily, like a wrong one": refuted. Skipped includes an
  open breaker (a transient outage: exactly the case the quick retry exists for); and a skipped call makes no model
  call and costs nothing, so a permanently misconfigured back-end costs no calls on the retries. (A disabled or frozen
  back-end is not in `router.effective` at all: never asked.)
- glm P2 "add daily_budget_usd to the two flagcheck back-ends": declined. With C1-1 no unbounded calibration path is
  left (at most about eight calibrations a day while failing); the gateway's account meter (90 % NOTIFY) covers the
  account; a per-back-end budget would add a new way for the check path to go dark for no measured need.
- glm P3 "plumb rounds / workers from the service": not needed (one caller, one value); recorded.
- glm E3 "a back-end with a wrong AND an unanswered quote is retried, its wrong quotes re-asked": accepted as built
  (its unanswered quote may answer; the doubling bounds the cost).
- qwen P2 "stop early when all back-ends passed": already so (the loop breaks when nothing is unanswered; a passing
  back-end has nothing unanswered). qwen P3 "a test for rounds=0": `max(1, int(rounds))`; recorded, not added.
- muse P1 "the cache check reads cfg enabled, not enabled() (the local back-end's GPU lease)": by design and commented
  at providers.py run ("a stored validated reply costs nothing, calls nobody, proves nothing about health (frozen / no
  lease: reused)"); not in this diff.
- muse P1 (state + event writes not one transaction), P1 (a metrics endpoint), P2 (offset_before on malformed lines,
  an end-to-end test on a recorded transcript, a hook score floor, the conversation cache): pre-existing, outside
  this change; recorded for a later change.

Suite after the fixes: tests/ingest 287 passed (5 F1 tests; each fails on the code before it).
