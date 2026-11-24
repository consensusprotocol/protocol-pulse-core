# Audit L2 (entry, finally, launcher): the findings checked against the code

- **qwen27b F1 (high), rejected by the vote too**: "box['outcomes'] is never assigned, so path=None and the line is never
  written". Misread of code outside the diff: `outcomes.write_once(line, path)` begins `path = path or OUTCOMES`, so
  `path=None` writes data/builds/outcomes.jsonl. tests/package/test_outcomes.py `TestExactlyOneLine.driver` calls
  `main()` with that `None` and finds the one line in (the patched) `OUTCOMES`. The dead argument was removed anyway
  (1f7791888) so no reader trips on it.
- **qwen27b F2 (medium)**: "_main() has no return after logf.close()". The file has it: `logf.close()` then
  `return 0` (the last two lines of `_main`); qwen said itself it could not see past the diff.
- **qwen27b F3 (low), the consensus (qwen + gemma)**: a BaseException raised inside `record_build` escaped the inner
  `except Exception`. FIXED in 1f7791888 (`except BaseException`, reported on stderr, the build's own end stands);
  test `test_a_stop_inside_the_write_is_said_and_never_masks_the_end`.
- **qwen27b, cycle 2, not voted**: a wrapper could set PP_SELECTID_DRIVER_UNDER_TEST and import pytest to pass as a
  test. True of any in-process check; GUARDED in 25110149d: a run under test is refused before it can write into the
  real tests/package/proof folder (test `test_a_run_that_only_claims_a_test_writes_no_real_record`), and the record's
  entry says `under_test` and names argv0 and the __main__ file.
- gpt-oss gave no answer in either cycle (cut at 32,768 tokens at effort high, as on every audit at that effort).
