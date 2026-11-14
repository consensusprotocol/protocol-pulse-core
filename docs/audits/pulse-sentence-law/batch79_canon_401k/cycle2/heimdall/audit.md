# Heimdall audit

**Question:** Batch 79 cycle 2 = the same change, re-examined after cycle 1 (unchanged diff). A defect in pipeline/canon.py under LAW L-k (ONE CANONICAL FORM, verbatim: "every text comparison in the pipeline uses pipeline/canon.py; two strings a listener hears as the same words compare equal, and a different number, unit, sign, name, negation or dropped word never does"). Found 2026-11-14 by the builder's spotlight pre-check on 7BqLu-wzbU0 ("I don't have a 401k."): canon read the retirement plan's name "401k" through its number suffix rule (_NUM + _SUFFIX: 'k' = thousand) as 401000, so canon.same("a 401k", "a 401,000") was True (a FALSE EQUAL: a different number compared equal), and "401(k)" (tokenised '401', 'k') read as 401 + 'k', so the plan's two spellings differed.
The change: _PLANS = ("401k", "403b", "457b"); in _canon_seq, before the number branch, a token in _PLANS, or a token followed by ONE single-letter token that together spell one of them ('401', 'k' from "401(k)"), becomes that name as one token spanning every word it covers, but only when no '$' is owed (owed is None): "$401k" stays the amount 401000 dollars. Everything else is unchanged: "40k" = 40000, "74k" = seventy four thousand, "401 kilos" stays 401 + kilos, and "401k" vs "401" (the second recogniser's reading in the pre-check) still differs, so that integrity hold is unaffected.
Tests: test_canon TestRetirementPlans (5): a plan never equals the number (401k / 401(k) vs 401,000 and 401 thousand; 403(b) vs 403 billion; 457b vs 457,000,000,000); the plan's spellings are one name; the pre-check case still differs; amounts unchanged; the split form spans both words (canon_spans). On the old file 3 fail (the defect) and 2 pass (the guards). The whole test_canon suite: 23 passed.
Context: canon.py is used by every text comparison (quote verification, selection anchors, edge words, G3 / G3b, G18, G20, G1 / G13, pin approved text); it is an input of the lock pre-check's decoder sha.
Cycle 1: qwen27b, glm and Grok all PASS, no findings. Facts measured since: canon_aligned is built from canon_spans (a token's FIRST word index), so the split form '403', 'b' becomes ('403b', its first word); the only plan names in the protected references are a speaker-attribution line in the published first pass's PIN (segments[0].speaker.people[*].line, 'how concentrated your 401(k) might be', not an approved text or lock) and 'roll over an existing 401k' in a v2f source transcript; every suite importing canon passes (test_lock_precheck 36, test_stand_alone 16; test_g3b_majority's one failure is gpu0.LeaseMissing for whisper:medium under CUDA_VISIBLE_DEVICES='', identical on the unchanged tree).
FIND: anything cycle 1 missed: a comparison site that counts canonical tokens per source word (so two words becoming one token shifts an index); a FALSE EQUAL the change introduces; a '$' amount or an ordinary 'k' / 'b' amount ('40k', '1.5b') changed; a lock edge (first / last word) that moves. Only state what you can verify from the diff. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0004
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
