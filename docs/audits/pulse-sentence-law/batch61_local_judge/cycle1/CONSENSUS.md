# Batch 61 cycle 1: four consensus findings, all implemented

C1 [high] (glm F1, qwen27b agrees): the yield race. The flag was checked before taking the lease, so a render asking
in between could find the lease held (its flock is non-blocking, exit 75).
- run() now checks YIELD_FLAG again once the lease is held. If set, it gives the lease back at once, with nothing
  loaded, and waits while the flag stands. It still checks before taking the lease and before every call.
- The protocol: the launcher touches the flag, waits for the lease to come free, starts the render, and removes the
  flag once the render holds the lease. The judge does not take the lease while the flag stands.
- Test: a render asking while the lease is taken gets it back, with no model loaded.

C2 [high] (glm F2, qwen27b agrees): a failed call was recorded and never retried, so the comparison ran on a
shrinking subset.
- done_ids counts only lines WITH an answer. A failed call is asked again by the NEXT run, never twice in one run
  (a 'tried' set), so nothing spins.
- The comparison prefers a line with an answer over a failed one, and still lists local failures.
- Test: a failed call is asked once per run, and again on the next run.

C3 [medium] (glm F3, qwen27b agrees): step A was counted once per (job, vendor answer).
- One vendor answer per job: the earliest that reads in contract. Every count is per moment; any other answer to the
  same prompt is listed (vendor_answers_not_compared), not counted.

C4 [medium] (glm F4, qwen27b agrees): prefilter_rules was multiplied by the number of vendor answers. Fixed by the
same change: one row per job.

Also taken from the cross-examination (not voted):
- a truncated last line (a crash mid-write) is skipped, never a crash (tested);
- the builder's git head falls back to 'unknown';
- the GPU-stop test now proves an answer written before the stop survives.

Not agreed, not changed:
- qwen27b F1, F2, and its cross-examination point on GpuOOM: wrong on the code. The sleep is outside the lease; the
  flag is checked before every call; Gpu0Stop is gpu0's BaseException base class, re-raised explicitly, and the test
  proves GpuOOM propagates.
- glm: "a flag left by an aborted render makes the judge wait forever". Fail-safe by design: GPU0 stays free; the
  launcher owns the flag.

test_local_judge: 8 passed.
