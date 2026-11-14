# Batch 60 cycle 1: one consensus finding, [medium]: implemented (the request bound), the GPU part not

C1 (glm F1, qwen27b agrees): a blocked cycle still lets fetches already started call YouTube before the control's
verdict stops the rest.
- Measured reasoning: cancelling earlier (before the control call) would NOT close it. The executor starts a queued
  fetch the moment a worker thread frees, before the main thread sees the failure.
- Implemented in the fetch itself: a threading.Event 'hold', one per cycle. The first sign-in failure sets it IN ITS
  OWN THREAD.
  - A fetch starting while it is set makes no request. Its rows come back SKIPPED: no row written, counted in
    blocked_rows, picked again next cycle.
  - The control answering clears it, so the cycle goes on.
  - A blocked cycle now asks YouTube at most once per fetch already in flight (FETCH_WORKERS = 4), plus ONE control
    request.
- Not implemented: "skip GPU batches when blocked". A decode makes no platform request, and dropping audio already
  downloaded would force a re-download, i.e. MORE requests.
- Tests: a fetch starting after a sign-in failure makes no request (ensure_meta and download_audio never called);
  the control-ok test runs cycles until nothing is picked, because a skipped fetch is retried next cycle; the batch-55
  stand-in takes the new argument. 27 passed, three runs in a row.

Raised but not agreed:
- qwen27b F1 [high], 1 vote: "rows are written for other videos after the block". Only failures that are NOT the
  platform's (window, decode, other acquisition errors), and successes, are written. They are those moments' own
  results. No change.
- qwen27b F2, 1 vote: a transient control failure marks the cycle blocked. That is fail-safe: nothing is burned and
  the next cycle asks again. No change.
- glm F2 [low], 1 vote: report counts can sum past 'picked' for cancelled fetches. Cosmetic. No change.
- Cross-examination, not voted:
  (a) control_ok on a row means the control answered in that cycle, not at that row's failure time. That is as
      specified (one request per cycle). A cycle lasts minutes.
  (b) An exception escaping _fetch writes 'fetch:' rows during a block. _fetch catches every acquisition error
      itself, so only a non-platform fault (e.g. the audio file vanishing) escapes. No change.
