# Heimdall audit

**Question:** Review this diff (orchestrator RULING 131, 08:25 ET Nov 17), verbatim: "(A) ADOPTED as written: per differing pair, two of the three readings (approved text, the render's run decode, the second recogniser) decide it and the sealed text takes that reading, for fillers, function words, repetitions and content words, each at least 3 words from a cut edge; never a number (save B), a name or a negation; a pair where all three differ HOLDS. (B) ADOPTED: a currency symbol is formatting ('$2 billion' equals a spoken '2 billion'), a canon like 401k. Both MARKED in the Telegram note in plain words when used."

Cycle 2: try to BREAK it. Report ONLY a defect you can show with a CONCRETE input (the run decode, the approved text, the second recogniser's text) traced through the diff's code. Keep each "issue" under 80 words. If you cannot break it, answer PASS with no findings.

FACTS (unchanged code, not in the diff):
- pinned.adjudicate_lock's inner reads(x, xmap, lo, hi): True only when the second recogniser's tokens hold x[lo:hi] with one neighbour on each side, all aligned and consecutive; at a span end nothing may precede / follow it. pin_side = every pair reads(p...); run_side = every pair reads(r...).
- pinned._lv2_critical(t, texts): a digit, a negation, an ordinal or a capitalised non-sentence-initial name.
- The critical check (crit -> PinError "number, name or negation") runs on the pairs left in ops BEFORE the second recogniser is called (pinned.py, right after "tag = ...").
- Below the (A) block, unchanged: ruling 18 (one replaced token, run_side -> both readings recorded), the HOLD when not pin_side, ruling 84 (b) (pin_side: one function word kept as the decode's with both readings; two or more hold), ruling 17 (pin_side: the approved text).
- lock_precheck.second_reading: ONE paid call per acquisition, cached in the work dir by the source file's sha256; a cached call returns usd 0.0.
- pinned.segment_lock = make_lock -> trimmed_lock -> adjudicate_lock is the render's own lock path (build_edl uses it).
- word_diff.norm used to drop every 'dollars' right after a token matching \d+(\.\d+)?: the same rule is now canon.dollars_after_number.
- telegram.bar_lines (unchanged) reads PINNED_DECISION.json the same way and binds it to the attested EDL by moments_package.package_sha256 == edl["moments_package_sha256"].

BREAK-IT TARGETS:
B1. The lock passes (no PinError) but at some position its text holds a reading that only ONE of the three readings has.
B2. A number, a name or a negation differs between the run decode and the approved text, and the lock still passes (with or without a '$').
B3. The run decode's reading is taken for a pair that is fewer than 3 run-decode tokens from a span end in EVERY valid placement of that pair.
B4. The merged text's canonical tokens differ from the tokens the votes settled.
B5. The pre-check seals a spoken_text that the render's own lock (segment_lock with it as approved_text) would refuse.
B6. The release note prints a ruling 131 line when the rule was not used, or omits one when it was.
B7. G18's comparison (word_diff.norm, word_diff._alt_positions) gives a different result than before for any input.

**Panel:** gptoss  |  **Cost:** $0.0020
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
