# Batch 62 cycle 1: the panel run timed out (exit 124) in glm's cross-examination
Read from the raw files: raw_c1_qwen27b.json, raw_c1_glm.json, raw_c2_qwen27b.json (qwen's votes; glm's never came).
qwen27b's cross-examination DISAGREED with all five findings, including its own. Each is judged here on the code:
- qwen F1 [critical]: "moment_id reaches the prompt, so it differs from validate's". It does not: rate_passages reads
  only pid, channel, duration and text. test_the_service_asks_the_byte_identical_prompt_validate_asks proves the
  service's prompt equals validate's for the same passages and event. No change.
- qwen F2 [high]: "the yield waits for the request in flight". True, and bounded by one scorer call (seconds): the
  same discipline as local_judge, which the flag is checked before. No change.
- glm F1 [medium]: a result file can hold a failed entry (score None) and later a good one; a reader taking the
  first or the last could read the failed one. TAKEN as a CONTRACT point: latest() and the verdicts file read the
  newest entry WITH a score for the event. Tested.
- glm F2 / F3 [low]: no defect (glm's own words).
Also in this step (cycle 2 audits it), the builder's file contract (pp-selectid 09:59):
- their candidates file in; one single-passage request per candidate, with PRE_FILTER_EVENT 'Pinned: bitcoin';
- a mismatched text_sha256 is refused; a moment rated before is reused;
- their verdicts shape out: verdicts/latest.json, and serve --candidates watches their file.
