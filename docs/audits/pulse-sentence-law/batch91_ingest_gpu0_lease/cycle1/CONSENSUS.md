# Batch 91 cycle 1: consensus (transcript_ingest: the Whisper pass under the GPU0 lease)

Diff: STEP.diff (b22a5e56..52c80556, 300 lines). Panel: qwen27b, glm (Heimdall-first, ruling 107 (2)). Cost $0.0017879684 (heimdall/audit.json total_cost).

| Reviewer | Verdict | Confidence | Findings |
|---|---|---|---|
| qwen27b | PASS | 0.95 | none |
| glm | PASS | 0.90 | F1 (low; its own confidence 0.55) |

Cross-vote on glm F1: glm (its author) AGREE; qwen27b DISAGREE. No consensus.

## glm F1 (low): if ts.release_whisper raises partway through, the lease is released with a model still loaded. Not agreed; not a defect of this diff.

The ExitStack runs `release_whisper` first, then closes the lease, even when the callback raises. So if the unchanged `release_whisper` (`transcript_store.py:291`) failed between its two unloads, the lease would go while a model stayed in this process.

That exception still leaves ingest(). This is a one-shot cron process, so it dies at once, and its CUDA memory and context go with it. The window is the traceback print and the exit, milliseconds. A GPU0 owner that starts inside it sees a foreign process, which law L-r waits out (never kills), and the wait ends when the process exits.

The normal path has the same shape. After a clean unload the CUDA context lives until exit (E-FAIL-084), which here means only the summary write. That is why this pass runs as a one-shot process, as E-FAIL-084 prescribes. qwen27b's disagreement says the same: the change orders the unload before the lease; a fault inside the unchanged unload is not created by the diff, and the one-shot exit bounds it.

No change. Grok was not asked: neither reviewer reports a defect, and the only vote for F1 is its author's own.
