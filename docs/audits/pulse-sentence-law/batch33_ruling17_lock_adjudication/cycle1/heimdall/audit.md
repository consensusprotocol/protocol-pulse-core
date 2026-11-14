# Heimdall audit

**Question:** Batch 33 = RULING 17 (orchestrator 2026-11-12 '10:20'): sentence-lock text adjudication; integrity stays fail-closed. In a PINNED run each clip's selection lock is made from the run's own Whisper decode (lock['text'] = the decoded words i0..i1) and records the pin's approved text (lock['selected_text']). NEW (pinned.adjudicate_lock, called in build_edl only when the pin has approved_text): if the two differ canonically, (1) a differing token that is a number, a negation, or a name (a capitalised word not opening a sentence, 'I' excepted) ALWAYS holds (law L-v 2), without a vote; (2) otherwise the independent second recogniser (ElevenLabs scribe_v1 on the acquired window; pipeline/second_recogniser.py, a verbatim copy of the already-audited file of branch ruling7) is read over the locked span's time range; if, at EVERY difference, it reads the approved words (and not the run's), the lock takes the approved text, records the three readings, and its digest is recomputed; if it reads the run's words, or neither, the run HOLDS (PinError) naming the three readings. (3) G18 (word_diff.gate_g18) compares the final's decode with the ADJUDICATED lock text instead of a third decode of the source span, ONLY for adjudicated locks (run_fresh passes 'adjudicated'); unadjudicated locks are unchanged. Tests: synthetic agree / run-side / neither / negation 2-1 / number / name / no-difference cases; the real Nov 12 clip_01 head (scribe_v1 reads 'I think', the pin says 'I mean,') HOLDS; G18 against an adjudicated lock passes the matching final, fails a dropped word, and an unadjudicated lock still fails on the third decode; the Nov 10 G18 fixtures still fail.
FIND: any way a lock takes the approved text without the second recogniser reading the approved words at every difference; any number / name / negation difference that reaches the vote; any way G18 passes a final whose words differ from the lock; tests that do not test what they claim. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, deepseek  |  **Cost:** $0.0236
## Consensus findings (majority of panel agrees)
- **[critical] pipeline/pinned.py:324** For a deletion (approved text has no token at the difference), side returns true whenever the run's token is absent from the second recogniser, even if the second recogniser reads a different word (neither the run's nor the approved empty text). This lets the lock take the approved text when the second recogniser reads neither.
  - evidence: `side = lambda xs, ys, cx, cy: all(i in cx for i in xs) and not any(j in cy for j in ys)
    pin_side = all(side(range(c, d), range(a, b), in_p, in_r) for _, a, b, c, d in ops)`
  - fix: For deletions, require that the second recogniser has no token at that position (or explicitly check that it does not read a different word).
  - raised by deepseek:F2; agree: qwen27b, deepseek
- **[medium] pipeline/pinned.py:273** The number check only matches pure digits with optional decimal, so number tokens like ordinals ('2nd', '3rd') or comma-grouped numbers ('1,000') are not treated as critical and can reach the vote, violating law L-v 2.
  - evidence: `if re.fullmatch(r"-?\d+(\.\d+)?", tok) or tok in LV2_NEGATIONS or tok.endswith("n't"):`
  - fix: Broaden number detection to cover ordinals, comma-grouped numbers, and other numeric forms.
  - raised by deepseek:F3; agree: qwen27b, deepseek

## Raised but not agreed
- deepseek:F1 [critical] The adjudication vote checks only global token presence via SequenceMatcher over the whole span, so the second recogniser can be credited with reading the approved word even when that word occurs elsewhere in the span and the actual difference position reads something else. This allows a lock to take the approved text without the second recogniser reading the approved words at every difference. (agree: 1)

## Added in cross-examination (not voted on)
- none
