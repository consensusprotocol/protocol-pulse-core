# Heimdall audit

**Question:** Batch 47 cycle 2 (verification). Cycle 1 had no consensus; implemented from single votes: a ONE-word name never matches phonetically (doublemetaphone('Casa') == doublemetaphone('case') == 'KS'), test added. See CONSENSUS.md.

Batch 47 = RULING 24 (b) + the REVIEW-DROP G20 AMENDMENT (orchestrator 2026-11-12 '23:20'). The rulings, verbatim in substance:
- (b) "G20 matches when EITHER the 0.85 text ratio holds OR every token matches phonetically (double-metaphone or equivalent). 'stefan lavera' vs 'Stephan Livera' must match; 'Stephan Livera' vs 'Steven Lubka' must not. Omitted names still fail; registry aliases remain."
- Amendment: "a G20 failure where the sign-off SCRIPT names every credited channel and the only mismatch is the decoder's spelling (text ratio >= 0.75 on that name) is droppable with both strings quoted; a name absent from the script is never droppable."
Implementation:
- gates.spoken_channels gains phonetic=False. Only gate_g20, on the RENDERED voice, passes True. The pre-render law L-a script check (run_fresh stage_voice) stays strict.
- Matching: for a CREDITED channel only, after the exact and the 0.85-ratio routes fail, _phonetic_span requires every canonical token of the name (display name or alias) to share a Double Metaphone code with the transcript token at the same place, consecutive and in order. A token with no code must be equal.
- Double Metaphone is vendored unchanged from PyPI Metaphone 0.6 (pipeline/pp_metaphone; SOURCE.txt has the sha256s; pure string rules, BSD).
- G20's evidence gains "how": the route and the heard stretch per channel.
- telegram.review_drop: _g20_spelling(run_dir, fmt) makes a non-PASS G20 droppable only when ALL of these hold:
  - the evidence (GATE_REPORT G20_<fmt>, VO_MANIFEST signoff text, the registry) is readable;
  - something is missing, nothing extra was heard, and the transcript is not empty;
  - the strict script check names every credited channel;
  - each missing name's best same-length stretch of the decode has SequenceMatcher ratio >= 0.75 against the name or an alias.

  Then the note quotes both strings. Otherwise the drop is refused and the reason is named.
FIND: anything still open from cycle 1; a new way a credited name that was not said passes G20, a non-credited channel is heard, the script check loosens, or a G20 failure becomes droppable without the script naming the name; a test that does not test what it claims. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0018
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- glm:F1 [low] The phonetic route can hear a credited name that was not said: the ratio route is tried first, but when it fails, _phonetic_span scans the whole transcript, so a credited two-token name whose tokens both occur (phonetically) anywhere, even far apart in unrelated words, matches; e.g. 'Stephan Livera' is heard in '... steph, then liver, ...' since 'steph'~'Stephan' and 'liver'~'Livera' share a Double Metaphone code, consecutive-and-in-order only constrains adjacency in the token list, not that they were said together. (agree: 1)

## Added in cross-examination (not voted on)
- none
