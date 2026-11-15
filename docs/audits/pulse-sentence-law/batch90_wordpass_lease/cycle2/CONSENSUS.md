# Batch 90 cycle 2: consensus (word_pass_worker: a busy GPU1 lease ends the cycle blocked)

Diff: STEP.diff (4e1dc92b..27705f31, 183 lines; since cycle 1, one comment at word_pass_worker.py:431). Panel: qwen27b, glm. Cost $0.0017163336 (heimdall/audit.json total_cost).

| Reviewer | Verdict | Confidence | Findings |
|---|---|---|---|
| qwen27b | PASS | 0.95 | none |
| glm | PASS | 0.90 | F1 (low) |

Cross-vote on glm F1: glm (its author) AGREE; qwen27b DISAGREE. No consensus.

## glm F1 (low): "blocked_rows counts jobs whose record already exists on disk ... moments that will never be retried — but they already have rows". Not a defect.

The claim treats a window RECORD on disk as a ROW. They are different things:

- `passed_ids()` (`word_pass_worker.py:121`) reads only rows (word_pass.jsonl).
- A record without a row is the "written before a crash, its row never appended" case.
- On a busy lease, such a job gets no row this cycle. The next cycle picks it again. `gpu_batch`'s todo filter (`:372`) skips its decode, and `_one` reuses the record and appends the row (the existing test `test_a_record_written_before_a_crash_is_reused_never_decoded_again`).

So the moment is retried. Counting it in `blocked_rows` ("no row written this cycle, picked again") is exact, not an over-count. qwen27b's disagreement agrees on the outcome.

Grok was not asked. Neither reviewer reports a defect, and the only vote for F1 is its author's own; self-agreement is not counted as consensus (see the batch 89 record).

## Batch 90 result

Two cycles, no consensus finding. Cost $0.000474269 + $0.0017163336 = $0.0021906026.
