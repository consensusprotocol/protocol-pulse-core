# Batch 119 (ruling 142 (3), the post_live route's missing half), cycle 2
Seats: qwen27b (high): FAIL, 4 findings; gemma (medium): FAIL, 2; gpt-oss (medium): PASS; gpt-oss (high): no verdict.
- "The probe timeout is 90 s, not cycle 1's 30 s" (gemma medium, qwen medium): DISPROVED. This cycle's STEP.diff was the
  cycle-1 diff; the merged code has `timeout=30` (pipeline/post_live_prefetch.py:27).
- T1 "a timed-out yt-dlp's children keep writing the window file" (gemma high, qwen high): DISPROVED for correctness,
  with evidence. Two orphans (ppid 1) seen 00:04-00:12 ET Nov 24 wrote `<id>.mp4.part`, yt-dlp's temporary name. The
  final `<id>.mp4` is only ever written by yt-dlp's own merge / rename, which a killed yt-dlp never reaches. REAL AS A
  LEAK: an orphan keeps downloading (bandwidth). The fix belongs where the process starts, select_passages._download_window
  (a decoder file): its own process group, killed whole on timeout. PROPOSED for the next decoder lockstep.
- T2 "a partial whole-stream file in the cache is reused" (qwen high): REAL, FAIL-CLOSED. _post_live_window reuses any
  cached file above 100 KB. A window cut from a truncated stream is short or empty. _has_media refuses an empty one;
  a short one fails pinned.acquire's HARD clock guard or the lock's word checks (PinError). PROPOSED for the same
  lockstep: refuse a cached file that still has its `.ytdl` sidecar, and one lock per video directory, because the
  pre-check and the render can fetch the same stream at once.
- "dl_start is rounded" (qwen low): BY DESIGN. It is _download_window's own formula, so pinned.acquire's cache hit
  returns the same start.
