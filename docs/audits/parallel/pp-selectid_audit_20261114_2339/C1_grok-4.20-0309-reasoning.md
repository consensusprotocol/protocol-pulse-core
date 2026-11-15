# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 30 s finish=stop usage in 13928 / out 612 usd_reported=0.026573 usd~0.085 (upper-bound price)

**CODE AUDIT: pp-selectid / RULING 110 (replay110.py + test)**

**Summary**  
The change adds a self-contained, resumable replay driver (`tests/package/replay110.py`) and its unit test exactly as described in the ruling. It re-uses `replay85.py` decision/comparison logic without modification, creates isolated Heimdall candidate back-ends from the production template (no config or routing mutation), respects ruling 100 deadlines, applies the spend stop, treats parse failures as “out of contract”, writes only to its own proof/ directory, and never touches production state, release paths, or any governed pipeline stage (EDL, render, gates, selection, punctuation, clusters, voice-over, etc.). All governing laws that apply to model replies, fail-closed behavior, canonical text handling, and release authorization are satisfied. The test suite exercises every major branch (in-time/late/timeout/out-of-contract/spend-stop/rate-limit/record filtering/summary arithmetic).

**Findings**

- **[P3]** Docstring claims “GATEWAY_MODELS.json” is read; the implementation hard-codes the two model IDs instead. Pure documentation nit; behavior matches the ruling text.
- **[P2]** Timeout detection in `replay_one` uses `if "abandoned at the deadline" in str(e)`. While it works for the current `ProviderError`, it is a brittle string match. A change in exception wording would silently alter classification. Prefer a dedicated exception attribute or subclass (still a test-only script, so not a production gate).
- **[P3]** `router.down.pop(name(m), None)` before every call is intentional (“each call is tried afresh”) but undocumented in the module docstring. Readers must infer the intent from the inline comment.
- **[P2]** Multi-threaded spend-stop check (`router.spent() >= stop_usd`) has no explicit lock around the read+possible call. The Router’s own reservation logic plus the per-`one()` lock on writing results make actual overspend unlikely, but the stop condition is not strictly serialized. Acceptable for a one-off replay with $0.75 limit, yet worth a small refactor for cleanliness.
- **[P3]** `incumbent()` re-parses `RESULTS.jsonl` on every `table()` invocation. Negligible for 319 records but could be memoized.

No violations of SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-a through L-l, LAW 20/M2, M12 FAIL CLOSED, LAW 22 (v2f byte-identical render), release authorization rules, or canonical-form requirements. No production code, renderer, selector, DB schema, or UI change. Smallest diff (only the new test driver + test). All must-fail/must-pass cases from the ruling are exercised by the unit tests.

P1_OR_WORSE: 0