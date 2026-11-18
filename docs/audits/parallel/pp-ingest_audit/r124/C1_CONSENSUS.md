# r124: the local model stays the last resort whatever the spend meter says, cycle 1: consensus

Reviewers (Heimdall, diff-scoped; qwen + muse). qwen3.8-27b (28 s, $0.002 reported): "No actions required. The code
is ready for production. The fix is correct, compliant, and well-tested." muse-spark-open (194 s, $0.004 reported):
"P0 CRITICAL: None ... Ready for production. Ship it", two P1s, two P2s, two P3s. Cycle 1: $0.0053 of the $1.00 cap.

## Agreed by both (verified)
- Router.order now keeps a last-resort back-end after every other one while the meter is not 'ok'; B1 is otherwise
  unchanged (a non-metered, non-last-resort back-end still goes first; the metered ones are never removed; the meter
  only notifies); with the meter 'ok' the configured chain is used. The real-config test (every meter state, the
  mine / hook / spotlight chains) is the one that proves ruling 118's order (both name it the most valuable part).

## Fixed (with a test that fails without it)
- muse P2 x2 "several last-resort back-ends keep their order" and "a back-end both metered and last-resort appears
  once": test_last_resort_back_ends_keep_their_order_and_a_metered_one_appears_once (chain [l2, hl, h, l1, b], meter
  tripped -> [b, h, l2, hl, l1]); M66 (the last resort before the metered ones) is killed by it too.

## Refuted (with the evidence)
- muse P1 "verify Router.run and Router.effective call Router.order (else r124 is dead code)": they do:
  providers.py:900 `chain = [only] if only else self.order(role)` (run) and :863 `return [b for b in
  self.order(role) if ...]` (effective). test_a_last_resort_back_end_stays_last_while_the_meter_is_not_ok runs the
  router (the gateway answers, the last resort is never called) and M65 (r123's order restored) is killed by it.
- muse P1 "log when Router.order reorders on the meter state": the reorder is a pure function of the meter's state,
  and every state change is already logged ("spend meter (HEIMDALL): <state> <snapshot>"), evented (spend_meter) and
  put on STATE line 1 (service.py:228-234, through spend.CreditMeter._check's on_change); order() runs on every
  request, so a log line there would repeat per request.

## Recorded
- muse P3 frozen / disabled with last_resort: effective() filters after order(), as for every back-end; covered by
  the existing freeze tests. muse P3 and qwen: the providers.json note is long (as every note there).

Suite after the fix: tests/ingest 444 passed. Mutations M65-M68: 4 of 4 killed; control passed.
