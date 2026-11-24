# Heimdall audit

**Question:** TASK: cycle 2 of the audit of batch 118 (Protocol Pulse, Python): the word-pass worker's main() now survives another program on GPU1 (ruling 145: "so a stray program never kills the word pass again"). Cycle 1 (qwen27b, gpt-oss): PASS, no findings. This cycle checks three concrete traces. Only state what you can verify from the diff and the cited lines. If uncertain, say so. Do not guess.

The same diff as cycle 1. Facts from unchanged code you cannot see, given as file:line:
- pipeline/gpu0.py:94 `class Gpu0Stop(BaseException)`; :98 GpuOOM, :102 Gpu0Foreign, :106 LeaseMissing, :110 LeaseBusy, :114 Gpu0NotFree, :118 Gpu0Unreadable all subclass Gpu0Stop.
- pipeline/word_pass_worker.py:340 cycle() runs gpu_batch() inside `with gpu0.lease(...)`: the lease is an exclusive flock released by the context manager's exit, which runs while any exception (BaseException included) propagates out of the `with` block. gpu_batch's `finally:` calls ts.release_whisper() before that exit; cycle()'s outer `finally:` deletes the temp files.
- A word-pass row is appended only by _one() and _fail() after a batch decodes (word_pass_worker.py:441, :478); a batch whose decode raised writes none.

TRACE AND ANSWER:
T1. Gpu0Foreign raised by gpu0.swap_to inside gpu_batch's `with gpu0.lease(...)`: list, in order, what runs before main()'s new except clause receives it, and say whether the GPU1 lease is still held when main() sleeps.
T2. Python evaluates `except (gpu0.Gpu0Foreign, gpu0.GpuOOM, gpu0.Gpu0NotFree)` against a raised gpu0.LeaseMissing: what happens, and does the test test_a_missing_lease_still_stops_the_worker observe it?
T3. If the new except clause were deleted, which assertion of test_a_foreign_user_an_oom_or_a_full_gpu_ends_the_cycle_and_the_worker_sleeps fails first, and why?

OUTPUT: for each trace, the answer in at most 5 lines, then any finding as severity (critical|high|medium|low), file:line, the failure, the fix. If no finding, say NONE.
REMINDER: only what the diff and the cited lines show; say when uncertain.

**Panel:** qwen27b  |  **Cost:** $0.0035
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
