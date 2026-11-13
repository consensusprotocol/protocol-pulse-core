# pp-selectid audit 1744 (rulings 68 / 72: the render's lock pre-check, wired before the writes and at the pin stage): cycle 1 consensus

- **grok:** "SHIP: yes". No P0, P1 or P2. It verifies the four required checks line by line.
- **qwen:** "SHIP: Yes". No P0 or P1. Its P2s are verifications.
- **glm:** "SHIP: yes with conditions". No P0; four P1s. Two are verified real and implemented; two are refuted below.

## Implemented

**C1-a (glm P1-2, verified): a pre-check that RAISES crashed the build instead of failing closed.**
- `lock_check(segs)` was called bare in build(), both for the voiced line-up and for the no-voice one.
- Unwrapped exceptions included:
  - an OSError from writing the request (send);
  - an exception inside decide() (attest on an unexpected spoken_text).
- On the driver's normal search, that loses the build record (package.json) and the registry update.
- Fixed:
  - both calls are wrapped; an exception becomes `lock_precheck.failed(e)`, the same no-verdict shape as an error
    answer. No write, and the search stops (`lock_stop`);
  - the no-voice path now also sets `lock_stop` on no verdict (glm P2-1: before, it would wait up to 1200 s again on
    every later line-up);
  - the two `LP.apply` guards catch any exception (glm P2-6), never crashing and never making a pin.
- Test: test_a_pre_check_that_raises_is_no_verdict_never_a_crash (voiced and no-voice). It fails with the wrap
  removed, and with the no-voice stop removed (mutation runs).

**C1-b (glm P1-3, verified): the pin stage's own check did not compare the sealed TEXT.**
- `pin_problems` compared video, start, end and verdict only.
- Fixed:
  - `apply` records, per segment, the text the lock passed (the approved text, or the adopted spoken text) in
    pk["precheck"];
  - `pin_problems` refuses when the package's segment text is not that text ("as they now stand").
- Test: test_the_pin_stage_compares_the_text_the_lock_passed. It fails with the comparison removed.

## Refuted (evidence)

- **glm P1-1** (a resent request id collides, FileExistsError): the ids are "pp-selectid.<build dir>.<n>". The build
  dir is created by `os.makedirs(out_dir)` without exist_ok, and the driver REFUSES an existing one. n increments
  within the process. Two requests can never share an id. (And with C1-a, even a collision would be no verdict,
  not a crash.)
- **glm P1-4** (reused answers may come from different requests): the contract's results are per segment window
  ("<video_id>.<start>-<end>" files; "Take the newest entry whose window equals [start, end] (a one-segment video)").
  The integrator says a repeat "is answered from cache", per segment content.
  - A medley has one clip per channel (L-y 4), so one segment per video.
  - A video with two segments in one line-up would carry a wider window and never match. That is no answer, so an
    error: fail closed.
- **glm P2-3** (the driver's id must fit ID_RE): the build dir's basename is "ledger_YYYYMMDD_HHMMSS", all within
  [A-Za-z0-9_].
- **glm P2-8** (hook_first_words derived differently): `_package` sets `" ".join(segs[0]["text"].split()[:8])`
  (package.py:339). apply uses the same expression.
- **qwen P2-3** ("lock_stop stops only the current angle"): it stops the whole search. Both the inner loop's
  condition and the angle loop's break test it; test_no_verdict_writes_nothing_and_stops_the_search shows no second
  angle is tried.

## Recorded (no change)

- glm P2-2: DECODER / RESULTS are constants. A changed decoder sha changes every result file name, so there is no
  answer: an error, and the search stops (fail closed). The integrator announces a decoder change.
- glm P2-4: exact-string matching, as the contract says ("equal").
- glm P2-5: pk["precheck"] stays in the package (to_pin does not copy it). Only an adopted segment gains "attested"
  in the pin; seal() is unchanged.
- glm P2-7: ruling 67's "lines are re-gated first" is a refusal here (no pin) when a line quotes the changed words.
  The writers are told never to repeat a clip's words. Fail closed.
- glm P2-9: apply is not idempotent. It is called once per package.

## Suites (scratch copy at HEAD + this diff)

All 15 OK:

| suite | tests |
|---|---|
| lock_precheck | 12 |
| medley | 156 |
| candidates | 10 |
| ledger_build | 35 |
| visual_pin | 11 |
| attest | 7 |
| speakers | 23 |
| providers | 16 |
| gates | 18 |
| angles | 28 |
| moments | 7 |
| eligibility | 30 |
| hook_onset | 9 |
| house_style | 23 |
| select_by_id | 27 |
