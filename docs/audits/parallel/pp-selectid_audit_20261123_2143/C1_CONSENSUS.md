# C1 CONSENSUS (written by the pp-selectid session, ruling 118: Heimdall seats only)
Seats answered: 2 of 2 (gpt-oss-20b at effort low: 0 P0/P1; glm-5.3-flash at effort none: 3 counted, 8 headed P1).
FIXED (real, cheap):
- glm F1: fallback_fields raised IndexError for a line-up with no channel name at all (chans empty): now 'the
  channels'; a single channel keeps its name.
- glm F2: a name run with a doubled space counted as another subject: the run is normalised to single spaces.
TRACED, NO DEFECT:
- F3 (the budget with `written`): the model-write path computes the same takeaway_budget(sum, written); glm marks P2.
- F4 (the flag condition reads `fields`): fields is assigned by the branch that ran (fallback or write) before the
  paid gates; the flag is on the package exactly when the sealed takeaway text equals the fallback's (tested).
- F5 (the clean-pass test): the fallback needs `soft`; glm's own trace agrees.
- F6 (kind_sentences' final `or c`): reached only for a code no table words (none today); renders the code, never a
  crash (ruling 155's audit asked exactly this).
- F7 (the caption lowercased with its names): house style's rule ('caption-lowercase ... all lowercase, names too');
  lint_lines passes it (tested).
- F8 (can the fallback run twice / loop forever): fb_state goes None -> 'due' -> 'used' once; after it only the
  takeaway-alone writes may run (alone_n, bounded by LINE_ONLY_WRITES), then the break (fb_state not None).
Cycle 2 cross-examines the hardened diff.
