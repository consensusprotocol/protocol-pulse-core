# Heimdall audit

**Question:** Batch 34 = RULINGS 18 + 19 (orchestrator 2026-11-12 '10:36', '10:51') + ruling 17's cycle-2 boundary fix. Integrity stays fail-closed.
RULING 18: when the run's decode and the pin's approved text differ in a locked span on exactly ONE token (a 1-for-1 replacement), not a number / name / negation (those hold before any vote), and the independent second recogniser reads the RUN's word at that position (an even split), the lock does not hold: it records both attested readings (lock['alternatives']: token_index, readings, the run word's index and source time span) and its digest is recomputed (pinned.adjudicate_lock). Two or more differences, or a reading of neither, still HOLD. G18 (word_diff.gate_g18) for such a lock: the final's decode may read EITHER attested reading at that position (edges() and diff() with alts; any other difference fails), its identity reference is the lock text, AND the token's audio must be the source's: sentence_law.span_fidelity = G17c's frame comparison (every 10 ms source frame above the floor within EDGE_WORD_MAX_DB 1.0 dB, best of +-2 hops, every kept frame compared) on the PREPARED clip over the token's span; the same on the final bytes is recorded as evidence only (the music bed and loudnorm make a 1 dB frame test impossible there). A mismatch fails G18. RULING 19: the comparison floor for G17c AND the token check is EDGE_WORD_FLOOR_DBFS = -90 dBFS (was -96): measured AAC codec noise at -92.9 / -94.2 dBFS in a pause (1.22 dB apart) while every frame above -90 was within 0.52 dB. Ruling 17 cycle-2 F1: at the span's start / end (no neighbour) the second recogniser's reading must begin / end exactly there.
Tests: either reading passes on the untouched prepared clip; a third word fails; the token's audio 3 dB down or silenced fails; 'can'/'can't', '15'/'50', 'one'/'two' hold; two ambiguous tokens hold; a start-of-span difference read with an extra word holds; codec-like noise between -96 and -90 passes, a real 3 dB onset loss at -50 fails.
FIND: any way G18 passes a final whose words differ from the lock other than the one attested alternative; any way the token check passes with the token's audio changed above -90 dBFS; index errors mapping the alternative (canon index vs G18's norm index, edges at the start / end); a critical (number / name / negation) difference that reaches alternatives; tests that do not test what they claim. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

THIS PART of the diff: pipeline/word_diff.py,pipeline/run_fresh.py only (the rest is audited separately). Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, deepseek  |  **Cost:** $0.0185
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- deepseek:F1 [critical] The deciding token check uses the final clip as the 'prepared' clip, so span_fidelity runs on final bytes (music bed + loudnorm) instead of the prepared clip, violating ruling 18's requirement that the token check be on the PREPARED clip and the final bytes be evidence only. (agree: 1)
- deepseek:F2 [critical] No check that there is exactly one alternative. Ruling 18 applies only to exactly ONE token difference; two or more differences must HOLD. The code processes all alternatives, so G18 can pass with two ambiguous tokens. (agree: 1)
- deepseek:F3 [high] The index mapping for edges assumes no extra words at the start/end. If an extra word equals an attested reading, it can substitute and mask the extra word, violating ruling 17 cycle-2 F1 (the second recogniser's reading must begin/end exactly at the span boundary). (agree: 1)

## Added in cross-examination (not voted on)
- deepseek: [critical] G18 does not reject alternatives for critical tokens (number/name/negation), which must hold before any vote.
