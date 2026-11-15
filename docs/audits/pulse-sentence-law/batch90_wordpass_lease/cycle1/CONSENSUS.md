# Batch 90 cycle 1: consensus (word_pass_worker: a busy GPU1 lease ends the cycle blocked)

Diff: STEP.diff (4e1dc92b..92bb11d8, 182 lines). Panel: qwen27b, glm (Heimdall-first, ruling 107 (2)). Cost $0.000474269 (heimdall/audit.json total_cost).

| Reviewer | Verdict | Confidence | Findings |
|---|---|---|---|
| qwen27b | PASS | 0.95 | none |
| glm | PASS | 0.90 | F1 (low) |

## glm F1 (low): "blocked_rows over-counts when the busy lease hits a later batch". Not agreed; not a defect.

glm's claim: `ready[:BATCH]` "was just worked and its rows written", so `len(ready)` counts decoded moments as blocked.

That reading is wrong. `gpu_batch` returns the busy text only when the lease was **not** had: `gpu0.lease` raised at the door, `tg` is still None, nothing was decoded and no row was written (`word_pass_worker.py:383-387`). A batch that **was** worked returns None, and `ready = ready[BATCH:]` (`:437`) slices it off before the next pass of the loop. So when `busy` is set, `ready` holds exactly the unworked batch plus the jobs behind it. The count is right, and the test checks it (blocked_rows 3, batches 0).

Because a reader can misread the line this way, a comment now says so (commit after 92bb11d8, in cycle 2's diff). Grok was not asked: neither reviewer reports a defect, so there is no disagreement to settle.

No consensus finding. Cycle 2 audits the final diff.
