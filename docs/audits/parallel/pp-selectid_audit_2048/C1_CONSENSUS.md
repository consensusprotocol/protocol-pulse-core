# pp-selectid audit 2048 (ruling 83 (a)+(b): abandoned calls booked at their prompt tokens, a late figure replacing it, cap $20 / stop $16; ruling 84: this side's class): cycle 1 consensus

- **grok:** "SHIP: yes". No P0 or P1. Two P2s.
- **qwen:** "SHIP: NO", on three P0s and one P1. The P0s are refuted below from the code. The P1 is implemented.
- **glm-5.3-flash:** NO ANSWER. The call was still open after 13 min (21:01 ET), against 76 s for the same reviewer
  in audit 1810. This is the Heimdall glm outage of tonight: 5 of 5 glm step-A calls missed 120 s in the 20:12
  build. Cycle 1 rests on grok and qwen. If glm answers later, its file is read before the final consensus.

## Implemented

- **grok P2 (providers.py, abandon):** when the booking raises (SpendLimit on an unreadable ledger), the call still
  stops as before (fail closed: no paid call on a total nobody can read). The `missed_deadline` line is now written
  BEFORE the booking, so the miss is on record either way. New test: the ledger breaks while the call is out. The
  call raises SpendLimit, the next back-end is never asked, the log holds exactly one `missed_deadline`, the
  abandoned thread's late answer changes nothing, and the corrupt ledger is never overwritten.
- **qwen P1-4 (on_late swallows errors):** the late ledger write is now its own method, Router._replace_booking (one
  write under the ledger lock: tmp file + os.replace, so all or nothing). _late catches its failure and records it
  on the late answer's log line (`replaced: false`, `ledger_error`). The prompt-token booking then stands. New
  test: the ledger breaks before the late answer, and the line carries `replaced: false` and the SpendLimit.
  `_within` still drops an exception from on_late: nobody is left to catch it there. _late itself no longer raises
  for a ledger failure.

## Refuted (with the code)

- **qwen P0-1 ("race in _within: no booking when the worker finishes just before the lock"):**
  - If the worker ends between `done.wait` timing out and the main thread taking the lock, then `done.is_set()` is
    True and nothing is abandoned.
  - `_within` then returns the worker's value (set BEFORE `done`), or raises its error.
  - Router.call treats that as an on-time answer: `_settle(key, b, usage, usd, role)` books its full cost, with the
    vendor's figure when there is one. An error books what any error books (the reservation is released).
  - So nothing is under-booked. That is the intended behaviour: an answer at the deadline is used, not abandoned.
  - The booking cannot be skipped for an abandoned call either. `box["abandoned"]` is set only by the on_abandon
    call, under the lock, before the raise, and the worker reads it under the same lock.
  - The ordering test drives the race with events: ["booked", "answered", "booked done", late].
- **qwen P0-2 (the _late arithmetic depends on abandon):** it does, by construction.
  - `_late` runs only when `box` holds on_abandon's value.
  - That value exists only if abandon's `_settle` returned, and that `_settle` added `booked` to
    usd_unreported_estimate (no usd_reported in usage {"in": 0, "out": 0}).
  - The subtraction removes exactly that amount.
  - The test checks the end state equals an on-time answer's: usd_reported 0.0123 and usd_unreported_estimate equal
    to the other back-end's estimate alone.
- **qwen P0-3 (class_84 "fragile"):** its own text concludes "this logic is correct". The case it raises (spoken
  "um" against approved "uh") holds: a filler on the approved side alone is outside the class, as the integrator's
  rule 1 says.

## Recorded (no change)

- **grok P2 (attest.py:56):** this side implements the integrator's exact class (its rules 1-5), not the wider
  variant it also allowed. A decision, stated in QUESTION.txt.
- **qwen P1-6:** the test's 201 tokens are 1 prompt character + 200 (prompt_tokens_upper). This is deliberate: it
  pins the formula.
- **The DECODER constant** (lock_precheck.py) changes to the integrator's new decoder sha when its ruling-84 change is
  live. It is the one line of this change not in the reviewed diff, and nobody else sets it.

## Suites

All 15 OK in dev34 before the fixes (453 tests). After the fixes, test_providers has 20 tests (2 new), OK.
