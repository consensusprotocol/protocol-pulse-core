# Findings checked against the code (01:30 ET Nov 24)
Seats: qwen27b, gpt-oss and gemma answered in cycle 1 (this diff is short); qwen and gemma in cycle 2.

1. gpt-oss F1 / gemma F1 [critical] "undefined variable 'pre' in the set comprehension" and, cycle 2, "undefined
   variable 'h'": REFUTED. open_work's first lines bind both (`pre, sp = ...`, `h = pre.get("held_102") ...`), above
   the hunk shown; the tests call open_work (TestRuling107UnmeasuredIsUndone, test_ledger_build) and pass.
2. qwen F1 [medium] "a non-dict value raises AttributeError" and, cycle 2, the same for never_empty / soft_record:
   FIXED for the whole function (every level read through one helper: a malformed record is read as empty), with
   tests on four malformed records.
