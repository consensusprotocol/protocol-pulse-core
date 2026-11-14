# Ruling 40 P1 (the second-model check in the watcher), cycle 1: consensus and dispositions

Reviewers (Heimdall-served): glm-5.3-flash (198 s, $0.005), qwen3.8-27b (215 s, $0.008), muse-spark-open-816b
(419 s, $0.026). glm: "P0 none: the diff is production-safe as written"; muse: "No P0 issues in this diff. All
fail-closed paths are correct."

## IMPLEMENTED
| finding | reviewer | fix | proof |
|---|---|---|---|
| the check loop re-parsed a day of the ledger every 30 s | glm P1 (muse P3) | skipped while the ledger's size / mtime are unchanged and no retry is due | test_service `test_the_check_loop_does_not_reread_an_unchanged_ledger` |
| `record()` stamped the current definitions' version whatever the definitions were (a trap if the sharpened answers ever enter the ledger) | glm P2 | `record(ans, version)`: an answer carries the version it was given under; the adapter counts only the current one | tests: a stale version keeps the flag (`test_anything_but_a_counting_no_keeps_the_flag[...flagcheck/0]`) |
| the check loop's newest-first sort compared a missing publish time with a string (safe only because expired / undated rows are skipped first) | muse P1 | the sort key is always a string | service.check_once |
| `remeasure` read `checks["accusation"]` of a saved run without a guard | glm P3 | `.get` | flagcheck.remeasure |

## REFUTED / BY DESIGN / OUT OF SCOPE
| finding | reviewer | evidence |
|---|---|---|
| P0 "carry_forward reads before append writes: concurrent appends lose flags" | qwen | every append of the service holds `wlock` across the read and the append (service._append); one service per store (its flock); settled in the ruling 80 audit (glm and muse, cycle 2: "correct for single-process; the flock in append redundant but safe") |
| P1 "localhost overrides can be spoofed" | qwen | the override file lives in the service's own store (written by this user); unchanged by this diff |
| P1 a cost guard on the daily recalibration | glm | 48 short calls a day (about $0.003), each recorded in the calls table (role flagcheck) and in live.json `second_model_checks_12h.usd` |
| P1 surface what was released | glm | live.json `second_model_checks_12h` (rows checked, answers, released, cost, calibration); every check is an event with its moment id and answers; the adapter's report counts `released_by_the_second_model` |
| P1 an alerting webhook | muse | out of this builder's scope: nothing is sent to Telegram or published by pp-ingest (standing order); the notices go to line 1 of STATE |
| P1 ledger rotation | muse | the bounded read (offset_before) keeps every read to the last day and a half whatever the file's size |
| P2 scope the miners to the mine role | muse | lines are written only by the moment and hook passes (mined.backend is their miner); a checker's answer lives in risk_checks, never in mined |
| P2 a test for a stale prompt_version | muse | present: `test_anything_but_a_counting_no_keeps_the_flag` (version flagcheck/0) |
