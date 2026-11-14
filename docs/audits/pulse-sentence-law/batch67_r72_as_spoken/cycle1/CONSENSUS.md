# Batch 67 cycle 1: no consensus findings; one defect found by the integrator's own measurement, fixed
INTEGRATOR'S OWN FINDING (the scratch measurement at 16:19, where the worktree has no recogniser key):
- When the second reading raised AFTER ruling 17's lock stood, answer() kept outcome 'no_difference' (a pass) with the
  error only in 'reason', and a later request REUSED it. That is a fail-open: the contract says an error is never a pass.
- FIX: any exception in a span's steps sets outcome 'error', lock None, so the entry is not reused.
- New test: test_a_failed_second_reading_is_an_error_never_a_pass. The answer is an error, not reused; asked again, it
  is answered. test_lock_precheck: 23 passed.
Single-vote points, checked, no change:
- qwen27b F1 [critical] "the recogniser is called twice per span": ruling 17's callback and ruling 72 both read
  second_reading, which pays ONCE per acquisition and serves the cached words after. test_one_paid_reading_per_acquisition
  counts the paid function's real calls (1 for two spans).
- qwen27b F2 [high] "spans' indices are not indices into sel": canon.canon_spans(words) returns (token, first word
  index, last word index) INTO the list it is given (sel). Measured: canon_spans(['When,', 'when', 'Bitcoin']) ==
  [('when', 0, 0), ('when', 1, 1), ('bitcoin', 2, 2)].
- glm F1 [medium] "the reading may be paid again per work dir": all spans of one acquisition share one work dir (the
  video's window), and acquire always sets provenance.source_file_sha256.
- glm cross-examination: a refused adoption keeps no lock (the span holds). The reason names the render's own refusal,
  with its run decode, approved and spoken readings, and as_spoken keeps the differences and the spoken text.
