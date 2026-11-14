# F1 (the flag check's calibration asks the models live), cycle 2: consensus

Reviewers (Heimdall), on the whole change (159c6709..2af6c379) with C1_CONSENSUS.md and CONTEXT_C2.md:
glm-5.3-flash (232 s, $0.005): "Yes, with one condition" (N4); muse-spark-open (360 s, $0.028): "Yes, with one
condition" (the empty calibration); qwen3.8-27b (385 s, $0.023): "Yes with conditions" (providers.py:851, early
termination, a rounds=0 test). Cycle 2: $0.056. All three: no P0 left; the cycle 1 fixes verified correct (the crash
path closed, an earlier allowance not kept on a crash, the wrong answers stored, the test derived from the config).

## Fixed (each with a test that fails on 2af6c379)
- C2-1 (muse P1, its condition): a calibration in which no back-end of the role could be called (`router.effective`
  empty: `cal == {}`) waited a day. Today that set changes only with the config (a restart calibrates anyway), but a
  checker under the GPU0 lease (law L-x, Ultron first) would make it transient, and such a calibration asks nothing,
  so retrying costs no call. `could` now also holds for an empty calibration: the next comes after CHECK_RETRY_S,
  doubling. Test: test_service test_f1_a_calibration_with_no_back_end_to_ask_is_tried_again_soon (on 2af6c379:
  86400 != 600).
- C2-2 (glm N4, its condition): a crashed calibration was visible in live.json only as an empty `calibration`.
  `second_model_checks_12h.calibration_crashes` now counts the `check_calibration_crash` events of the last 12 h.
  Test: the crash test asserts it (on 2af6c379: KeyError).
- C2-3 (qwen P2): the rounds test also runs rounds=0 (one round, `max(1, int(rounds))`).

## Refuted or recorded
- qwen P1 / muse P2 "providers.py:851: the cache branch reads cfg enabled, not enabled() (the GPU0 lease)": refuted
  as a defect, and outside this diff (glm agrees: latent and documented as intentional). The lease gates a LIVE call
  on GPU0; a stored reply loads nothing on GPU0 and spends nothing (the code's own comment: "a stored validated reply
  costs nothing, calls nobody, proves nothing about health (frozen / no lease: reused)"); and local_gemma is
  `enabled: false`, so for it the branch is never taken. Recorded for the integrator if the local back-end is enabled.
- qwen P2 "early termination when all back-ends passed": already so (the loop breaks when nothing is unanswered);
  glm c2 agrees the full calibration is the better trade.
- glm N2 "a permanently crashing calibration costs ~64 calibrations a day": refuted arithmetic. The waits are 600,
  1200, 2400, 4800, 9600, 19200, 38400, 76800, 86400 s, then 600 again: at most 8 calibrations in the first 24 h and
  9 per ~2.8 days after that (about 3.3 a day); the comment "a few calibrations a day" stands.
- glm N7 "pin CHECK_RETRY_S (600) > the breaker's open_s (300)": not an invariant. A calibration that finds a breaker
  still open is skipped at no cost (a skipped call is free) and the doubling outgrows any open window; recorded.
- muse P2 `int(rounds)` on None: only internal callers with an int; a programming error would take the crash path
  (fail closed). muse P2 `asked_at` (wall clock) vs `seconds` (the service clock): the same clock in production;
  recorded. muse P3 the calibration holds the check loop for minutes: by design ("the loop waits for it"), now with
  its duration logged and stored.
- glm N1 (a crash inside the rounds discards that round's answers: fail closed; the calls' spend stays counted in the
  calls log), N3, N5, N6 (the breaker / meter / signal interplay: correct as written), N8 (retracted by glm):
  confirmations, no change.
- Pre-existing items carried from cycle 1 (offset_before on malformed lines, state + event atomicity, a metrics
  endpoint, an end-to-end test on a recorded transcript, the conversation cache): outside this change; recorded.

Suite: tests/ingest 288 passed (6 F1 tests). Audit total: c1 $0.059 + c2 $0.056 = $0.115 (Heimdall).
