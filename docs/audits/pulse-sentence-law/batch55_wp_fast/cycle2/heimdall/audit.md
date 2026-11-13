# Heimdall audit

**Question:** Batch 55 cycle 2 (verification). Cycle-1 consensus implemented: a dying fetch writes failure rows and the cycle goes on (tested); the decode-batch test asserts the order (no reference before the last verbatim); timing fields documented.

Batch 55 = ORCHESTRATOR ORDER '02:46' (b): make the word-pass worker faster inside the law. "fetch audio in parallel ahead of the GPU step, bigger cycles, order = last 10 h, then last 24 h, then older. Target: the 332 waiting rows done within the hour."
Measured before: cycles of 40 took 4.5, 14 and 22 min. The structure:
- each video's audio was downloaded sequentially, before any GPU work;
- each window then swapped the two Whisper models (the verbatim WHISPER_MODEL, then REFERENCE_MODEL for punctuation), so two loads per moment, because gpu0.swap_to keeps one model per GPU;
- one 216 s wait on the foreign GPU1 user (the media-sync cron), the correct wait-out.
The change:
- PER_CYCLE 40 -> 120 (PER_CHANNEL = ceil(120/6) = 20); BATCH 8 -> 16.
- pick: tiers in the adapter's rank order: the last 10 h (capped, then uncapped), the last 24 h (capped, then uncapped), older (capped).
- _fetch(vid): meta + the audio once + every window cut, in a 4-thread ThreadPoolExecutor (never under a lease). The main thread runs a GPU batch as soon as BATCH jobs are ready, or when the fetches are done.
- gpu_batch: under gpu0.lease (GPU1), the windows without a record go through decode_batch:
  - every verbatim decode first (one model load);
  - then the punctuation reference only where punctuation.needs_restoration (one load);
  - a failed window returns its exception and the others go on.
  Then _one writes the record and the row (or the failure row, or reuses an existing record without decoding). release_whisper; the lease is left.
- The report adds fetch_s, lease_wait_s, foreign_wait_s (from gpu0.events) and gpu_s.
Tests: 15.
FIND: anything still open; a job decoded twice or never; a lost exception; the lease held across fetches; a test that does not test what it claims. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0023
## Consensus findings (majority of panel agrees)
- **[low] pipeline/word_pass_worker.py:None** The 5 s wait(pending, ...) only runs in the elif branch; when ready is non-empty but below BATCH and futures are pending, the loop spins without waiting (the elif is skipped because the first if's condition len(ready)>=BATCH or (ready and not pending) is false, then elif pending: wait — actually that fires, but when ready is non-empty AND pending, the first if is false and elif pending fires, so it does wait; the real gap: if ready is empty and pending non-empty, wait fires — OK. However when ready has 1..BATCH-1 jobs and pending is non-empty, gpu_batch is not called until either BATCH accrue or all fetches finish; the leftover ready[BATCH:] after a gpu_batch call is only flushed when pending empties — correct. Remaining nit: report['fetch_s'] sums thread durations, overstating wall time; documented as summed, so not a defect. No lost-exception path found in the fetch loop: f.result() is guarded.
  - evidence: `if len(ready) >= BATCH or (ready and not pending):
    gpu_batch(ready[:BATCH])
    ready = ready[BATCH:]
elif pending:
    wait(pending, timeout=5, return_when=FIRST_COMPLETED)`
  - fix: None needed; documented behaviour.
  - raised by glm:F2; agree: qwen27b, glm
- **[low] pipeline/test_word_pass_worker.py:None** TestDecodeBatch asserts load counts (4,2) but the order property is checked only via loads list indices; since decode_batch genuinely runs all verbatim decodes before any reference (the second loop), the assertion last_verbatim < first_reference does test the claimed order — however the test's needs_restoration stub reads words[-1] which would IndexError on an empty words list; bad.wav returns iter([]) so decode_verbatim raises 'no words' before needs_restoration is called, so it is safe. The test does test what it claims.
  - evidence: `last_verbatim = max(i for i, c in enumerate(loads) if c == "verbatim")
first_reference = loads.index("reference")
self.assertLess(last_verbatim, first_reference)`
  - fix: None; assertion is sound.
  - raised by glm:F3; agree: qwen27b, glm

## Raised but not agreed
- qwen27b:F1 [critical] Logic error in `_one` causes a `TypeError` when a window has an existing record (reuse path) but `decoded` is `None`. (agree: 1)
- qwen27b:F2 [high] The `gpu_batch` function filters `todo` based on existing records, but `decode_batch` is called only on `todo`. However, `_one` is called for *all* items in `batch`. If an item is in `batch` but not in `todo` (because it has an existing record), `res.get(...)` returns `None`. This triggers the bug in F1. Even if F1 is fixed, the logic is fragile: `decode_batch` returns a list corresponding to `todo`, but `res` is a dict keyed by `moment_id`. This works, but the interaction with `_one`'s `decoded` parameter is the source of the crash. (agree: 1)
- glm:F1 [medium] A decode_batch exception raised outside the per-window try blocks (e.g. from the zip/loop itself) is lost: gpu_batch calls decode_batch outside any try, so a crash there propagates out of gpu_batch, skips _one for the whole batch, and the finally only releases the lease — the windows are neither decoded nor given failure rows, and the cycle dies (no per-batch isolation). (agree: 1)

## Added in cross-examination (not voted on)
- glm: [medium] Duplicate decode: gpu_batch's todo filter checks record existence, but _one re-checks and reuses; meanwhile a window whose record was written by a PREVIOUS batch in the SAME cycle (same video, overlapping windows) is decoded again if the record appeared between todo-check and _one — minor. The sharper issue: res is keyed by moment_id; two picks sharing a moment_id (ledger can repeat a moment across videos) collide, one loses its decode and hits the raise-None path.
- glm: [low] foreign_wait_s is read from gpu0.events() after the finally-adjacent accounting, but events() may retain prior cycles' entries; ev0 = len(gpu0.events()) snapshots the count, yet if gpu0.events() is capped/rotated between the snapshot and the final read, the slice [ev0:] misindexes and foreign_wait_s silently misses or double-counts waits.
