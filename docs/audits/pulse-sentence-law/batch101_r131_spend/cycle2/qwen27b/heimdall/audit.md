# Heimdall audit

**Question:** Review this diff (orchestrator RULING 131, 08:25 ET Nov 17), verbatim: "every outside dollar your services spend (Scribe and any other) is to be written into the day ledger the builder reads, so the day's $1.00 is one true number". The diff writes one ledger line per paid outside call at each vendor call site, and reuses a window's earlier second-recogniser reading under a new decoder code so it is not paid for twice.

Cycle 2: try to BREAK it. Report ONLY a defect you can show with a CONCRETE input or sequence traced through the diff's code. Keep each "issue" under 80 words. If you cannot break it, answer PASS with no findings.

FACTS (unchanged code, not in the diff):
- lock_precheck.work_dir(vid, lo, hi, sha) = ROOT/work/"{vid}.{lo:.3f}-{hi:.3f}.{sha[:12]}"; a YouTube video id contains no '.'.
- A window's download offset is float(round(max(0, start - 15))): the same window always gives the same offset.
- pinned._second_recogniser_words (unchanged) calls second_recogniser.scribe_words and returns usd = secs/60*0.012.
- Ruling 77 purges each work dir's media after use, so a re-download's source_file_sha256 never matches an older reading's.
- Ruling 105's history (unchanged) matches earlier passes by source_file_sha256.
- The decoder sha hashes select_passages.py, punctuation.py, pinned.py, sentence_law.py, canon.py, gpu0.py: none is in this diff.
- run_fresh.main, replay.main and lock_precheck.main are the processes' entry points.

BREAK-IT TARGETS:
T1. A paid outside call (Scribe, the xAI sign-off, TTS) that leaves NO ledger line, or a ledger line for a call that was never made.
T2. An xAI line whose usd is not exactly what xAI reported (a guess, a wrong scale, a bool or string counted).
T3. A day total that counts a line from outside the window, misses one inside it, or counts an unpriced line as $0.
T4. An earlier second reading reused for a DIFFERENT window, video or offset, or reused when its words do not read as this decode; or a reuse that still pays.
T5. A ledger failure that raises into a render or the pre-check, or loses the call's result.
T6. Two processes writing at once leaving a torn or merged line.

**Panel:** qwen27b  |  **Cost:** $0.0079
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
