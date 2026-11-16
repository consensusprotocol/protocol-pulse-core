# r118: the stalled miner (orchestrator 10:50 ET Nov 16), rulings 118 / 119 (3), cycle 2: consensus

Reviewers (Heimdall, diff-scoped): qwen3.8-27b (51 s, $0.0022 reported): "P0 none ... the downsignal.py P0 was
refuted"; muse-spark-open (130 s, $0.0029 reported): "P0 CRITICAL: none. No ship-blocker remains after refutations ...
Production ready? Yes, with conditions" (the condition: the torn-read P1 below). Cycle 2: $0.0051. The audit: $0.0193
of its $1.00 cap (1,031 changed lines; COST.json: c1 qwen $0.0040, muse $0.0102; c2 qwen $0.0022, muse $0.0029).

## Agreed by both (verified)
- muse retracts its cycle-1 P0 (downsignal `config` import): `paths` is DownSignal's own argument; the 11:31 ET run
  logged "wired to .../down_signal_state.json". qwen agrees it was a false positive.
- The transcript intake (after every probe check, every record check, write-once, the main tree read only), the caption
  429 isolation, the own-file clock without `families`, glm in no chain: correct (both, per finding).
- muse retracts its cycle-1 P1s on the stall act's busy retry and burst (the fetch loop's bounds hold).

## Already fixed before this cycle (both reviewers argued from the cycle-1 code)
- Both P1 "pipeline_captions_refused fails open on a torn read: return True". Cycle 2's own package carries C1-1
  (PACKAGE.md lines 272-281): an unparsable breaker file written inside the breaker's 30 minutes (the pipeline writes it
  only when it is refused, so a torn read is a 429 now) IS open; only an unparsable file older than that is not, so a
  broken file can never stop the captions for good (fail closed for the span the breaker itself holds, never forever).
  Tested with three bodies x mtimes; M19 and M20 killed.
- muse N1 / qwen P2 "float('') in _stall_notice": cycle 2's package carries C1-2 (line 630): the act record is read
  once in a try, missing or unreadable means act now; stall.line is called only inside `if chk["stalled"]`. M21 killed.

## Refuted (with the evidence)
- muse P2 "count only probed videos as waiting (published_ts NOT NULL)": an unprobed video held in probe_retry behind the
  gate is exactly the stall of Nov 16 07:47-10:53 ET; the self-check must see it (it is counted while discovered inside
  12 h, and leaves the count at its probe: seen_old, a Short, or transcribed).
- muse N3 "1,200 caption 429s a day (50 videos x 24 retries)": transcript_store's caption breaker is ONE file for the
  whole store (state/caption_circuit.json): after a 429 every download waits 30 min, and while the pipeline's own
  breaker is open none is tried; so at most one refused download (3 tries) per 30 minutes, whatever waits.
- muse "next_at race (fetch sets +5000 s, the act resets it to now)": the act runs at most once per 30 min of a stall
  and costs one extra try of each waiting video then; recorded, not a defect.

## Recorded (a state no code path makes)
- qwen P1-2/3, muse P2-4 "a corrupt staged record blocks the video": a staged record is only ever made by os.link of a
  checked file (this change and transcript_store._write_once), so none can be partial; if one were damaged by hand,
  canonical_transcript re-hashes it and the fetch step logs a crash and retries (as for any staged record before this
  change), never mines it. Deleting records from the store to fall back is not done (records are immutable).
- muse N2 `_vdir`'s ValueError on an invalid id reaches fetch_once's own except (unchanged): a logged retry.

Suite: tests/ingest 414 passed; mutations 20 of 21 killed (M17 equivalent). Verdict: no P0 open; muse ships it, qwen's
remaining conditions are the two fixed in C1 and the recorded unreachable state. r118 goes live at the next restart.
