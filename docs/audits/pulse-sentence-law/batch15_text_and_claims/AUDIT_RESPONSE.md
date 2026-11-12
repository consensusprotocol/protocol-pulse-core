# Batch 15 (laws L-h TEXT READ AS SPOKEN, L-i THE CLAIM IS THE EVENT; E-FAIL-036 / 037 / 038): dispositions

Audit on the actual diff (STEP.diff): cross-LLM Grok + GPT-4o + Gemini, both cycles (FINAL_CONSENSUS.md): READY,
zero defect findings; the one shared point (keep the '.t2' embedding-cache bump and its test) is already in place.
Heimdall deepseek + qwen27b + glm (heimdall/): 0 consensus findings (deepseek and glm stopped at the token cap;
the panel rejected qwen27b's 5 in cross-examination). Evaluated on the merits anyway:

## Implemented
- qwen27b: story_semantics._norm decoded entities but did not join split Whisper tokens (an asymmetry with
  read_text); it now does both, so a quote check is right even on raw stored text. Test updated (the Natalie
  '$81,000' quote fails the old reading, counts on the read text and on the raw text).

## Rejected, with evidence
- "underlying_event can become None for a cluster": label_cluster sets current_ok only with a headline, and only
  current_ok labels become candidates.
- "_norm('&') is empty and an empty quote matches everything": quote_in requires >= 5 normalised words.
- "'99 . 100' would be joined": the pattern is the documented split-token artefact (' ,000', ' .S.', ' .3'); no
  separate-number ' . ' join occurs in the store; a false join could only make a quote check fail or match the
  same digits, never add words.
- "the cache test only checks the file name": chunk_vectors encodes exactly each chunk's text, which chunks()
  builds through read_text (tested separately on a stored caption record).

## Verified
- Batch suites 106 passed / 12 GPU-skipped; regression_test.sh 26 PASS / 0 FAIL; pipeline/regression.sh PASS
  incl. PULSE PREVIEW REFERENCE: REPRODUCED.
- Real model (DoD 20:13): with L-h and L-i, Natalie Brunell and Coin Bureau both count for the election
  sell-off / ETF-outflow claim (they counted 0 of 2 in the stopped run).
- Real-model end-to-end TestLayoutGate: still fails "no hook passage scored >= 4.0" for both the cluster and the
  wire candidate (3 channels counted, 2 layout-eligible): the same pre-existing failure recorded in batch 8b
  (11:30 ET) and reproduced at 4ca4b426 (before DEC-13) and with the fixture's own date pinned; the LLM scorer
  rates the synthetic fixture's hooks below HOOK_MIN_SCORE. DEC-13's cluster path ran end to end in it.
