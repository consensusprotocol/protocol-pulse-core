# r118: the stalled miner (orchestrator 10:50 ET Nov 16), rulings 118 / 119 (3), cycle 1: consensus

Reviewers (Heimdall, diff-scoped, ruling 107 (2); glm out of every chain by ruling 119 (3), so the pair is qwen + muse):
qwen3.8-27b (68 s, $0.004 reported): "production-ready ... strictly complies with all governing laws and rulings", one
P1 (hardening). muse-spark-open (319 s, $0.010 reported): "correctly fixes the 3-hour outage ... and the false outage
clock"; two P0s (below: one refuted, one fixed). Cycle 1: $0.0142 of the $1.00 cap (1,012 changed lines; COST.json).

## Agreed by both (verified)
- The pipeline's transcript is taken only after every probe check (Short, live, upcoming, age, length, duplicate) and
  only when it names the video and the channel, is filed under its own method and hashes to its sha256; the bytes
  linked in are the bytes checked (write-once os.link); the main tree is only read.
- A caption 429 no longer trips the gate; the gate still stops every yt-dlp call on a probe's or a listing's refusal.
- The clock runs on the watcher's own file with no `families`; no glm in any chain, no paid route, no frozen vendor.
- The stall SQL is parameterised; the act is one statement.

## Refuted (with the evidence)
- muse P0 "downsignal.py: `config` not imported, NameError when DownSignal() gets no state_path: a crash at start".
  The line is `self.state_path = state_path or paths["signal_state"]`: `paths` is DownSignal's own argument (the
  service passes self.p = config.paths(); unchanged code, downsignal.py `def __init__(self, cfg, router, overrides, q,
  paths, ...)`). Measured: the watcher ran this code 11:31-11:33 ET with no state path and logged "RULING 87: wired to
  .../data/editorial/ingest/down_signal_state.json (mode heimdall_first)".
- muse P1 "stall.act has no busy retry": every write of this process goes through Queue's one connection under its
  lock (timeout 30 s); a failure is caught in _stall_notice and, as the act record is written only after act()
  returns, the next health tick (a minute) acts again.
- muse P1 "an existing staged record is never validated": a staged record is only ever made by os.link of a checked
  file (this change and transcript_store._write_once); canonical_transcript re-hashes every record it reads
  (transcript_records raises on a mismatch), so a damaged one could never be mined silently.
- muse P1 "the act makes 50 videos due at once: a burst of yt-dlp calls": the fetch loop takes at most 10 due videos a
  round and YTDLP_CONCURRENCY (3) at once behind the gate (service.fetch_once, unchanged), the same pace as any listing;
  a probe's 429 still trips the gate; the act runs at most every 30 min.
- muse "two records of the same rank, the last sorted wins": one file per method slug and METHOD_RANK is per slug, so
  no two files share a rank. muse "a not-yet-probed video's discovered_ts keeps an old video waiting": it waits until
  its probe (then seen_old if old); outside 12 h from discovery it is not counted.

## Fixed (each with a test that fails without it)
- C1-1 (muse P0, partly right): the pipeline's breaker file is written in place by transcript_store._open_circuit, and
  only when its ingest is refused: a file that cannot be parsed and was written inside the breaker's own 30 minutes is
  one being written now, so OPEN (no download here); an older unparsable one is not (a broken file never stops the
  captions for good). Test: test_while_the_pipelines_caption_breaker_is_open... (three bodies x mtimes). M19 / M20
  killed.
- C1-2 (qwen P1): _stall_notice reads its act record once, in a try; a record missing or unreadable means "act now",
  never a TypeError / ValueError that would drop the line. Test: the service test starts from an unreadable record.
  M21 killed.

## Recorded
- qwen P2 / muse P2 cache the breaker read or the glob: one small file read or one directory glob per video fetched.
- muse P2 align the probe's 60 s deadline with mining's: ruling 87's probe deadline is the builder's; any family's
  answer resets the clock, so one slow family never makes "down".
- muse P2 a hit-rate counter: each take is a queue event (kind pipeline_transcript) and an attempts.jsonl line.
- qwen "granular stall alerts": the order's measure is 30 minutes; recorded.

Suite after the fixes: tests/ingest 414 passed; mutations 20 of 21 killed (M17 equivalent, see CONTEXT.md).

## Changed after cycle 1 (measured, providers.json only)
The live check of the new chain finished after cycle 1 (the watcher's own mining question, one window each of
Vu0XZSz-aj4 and DO6iIRbccIg, no stored replies): deepseek 4.1 at effort low returned EMPTY (finish_reason length: its
reasoning took the whole 4,000-token budget) after 515 s with the transport retries, and at effort none gave no answer
in 4 min; gemma at its default reasoning was empty too after 739 s, but at effort none 2/2 valid in 21-24 s; gpt-oss
3 of 4 valid in 4-6 s (one reason over 160 characters, asked again by the router); minimax 2/2 (57 s); mimo 2/2 (25 s).
So: gemma's mine and probe back-ends at effort none; deepseek stays second as ordered, its deadline 90 s (was 300), so
while it gives no answer a qwen outage costs a window at most 4 x 90 s once before its breaker (5 failures) sends the
windows on to minimax; the flag check's second back-end is gemma (deepseek could never pass the live calibration),
still never the miner of the row's video (flagcheck.checkers).
