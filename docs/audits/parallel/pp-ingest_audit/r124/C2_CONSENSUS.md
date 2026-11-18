# r124: the local model stays the last resort whatever the spend meter says, cycle 2: consensus

Reviewers (Heimdall, cross-validating cycle 1 and its consensus): qwen3.8-27b (61 s, $0.002 reported): "P0 CRITICAL:
None. P1 HIGH: None ... Ship it", one P2 and one P3; muse-spark-open (106 s, $0.002 reported): "No P0, no P1, no P2
remain open ... Ship r124 as-is ... Conditions: None", its two cycle-1 P1s withdrawn (the delegation verified at
providers.py:863 / 900 and by M65; the per-request log refuted as noise beside the meter's state-change log). Cycle 2:
$0.0046; the audit $0.0100 of its $1.00 cap (COST.json).

## Agreed by both (verified)
- The fix keeps a last-resort back-end last while the meter is not 'ok', the configured chain otherwise; B1 holds; the
  new test (several last-resort back-ends, one also metered) kills M66; the real-config test proves ruling 118's
  order for mine, hook and spotlight at every meter state.

## Refuted
- qwen P2 "make `last` a set (O(1) membership) for large chains": the chains have 2 to 7 back-ends and order() runs
  once per request; a list keeps the chain order the result needs. qwen P3 "a docstring for order()": it has one
  (the diff's own hunk: "A last-resort back-end ... stays after every other back-end of the chain (r124)").

## Recorded
- The cosmetic and frozen / disabled notes of cycle 1 (no change).

Suite: tests/ingest 444 passed. Mutations M65-M68: 4 of 4 killed; control passed. No P0, P1 or P2 open.
