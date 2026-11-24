# Heimdall audit

**Question:** TASK: cycle 2 of the audit of batch 124 (Protocol Pulse, Python): G18's edge check follows ruling 143 (the same diff as cycle 1). Cycle 1: gemma PASS, glm PASS, qwen PASS; its strongest claim (a shift aligned as replaces) was disproved by running difflib (a shift aligns as delete / equal / insert and stays HARD). Only state what you can verify from the diff and the cited lines. If uncertain, say so. Do not guess.

TRACE AND ANSWER:
T1. Give one concrete (expected, heard) pair of English sentences for which _edges_substituted_only returns True although the CUT is wrong (a clipped, shifted or mid-word cut, not a decoder's reading), and run difflib's opcodes for it by hand. If you cannot construct one, say NONE.
T2. The edge block runs only when row["identity"] is empty. Can an identity difference that the audio did NOT clear ever coexist with the edge block clearing the edges?
T3. Any other defect.

OUTPUT: for each finding, severity (critical|high|medium|low), file:line, the concrete failure, the fix. If none, say NONE.
REMINDER: only what the diff and the cited lines show; say when uncertain.

**Panel:** qwen27b  |  **Cost:** $0.0084
## Consensus findings (majority of panel agrees)
- **[low] pipeline/word_diff.py:247** T2 answer: No. The guard 'not row["identity"]' on the edge-block entry condition means the block is skipped whenever identity is non-empty. An identity difference the audio did NOT clear (identity remains non-empty) therefore can never coexist with the edge block clearing edges. No defect here.
  - evidence: `if row["edges"] and not row["identity"] and c.get("prepared") and _edges_substituted_only(c["lock_text"], heard):`
  - fix: NONE – the guard is correct.
  - raised by qwen27b:F2; agree: qwen27b

## Raised but not agreed
- qwen27b:F1 [medium] A mid-word cut that truncates an edge word into a different one-for-one token is indistinguishable from a decoder misreading, so _edges_substituted_only returns True for a physically wrong cut. The docstring promises 'An omitted or added word at an edge (a clipped or a shifted cut) … is False', but a mid-word clip that yields a one-for-one replace (not an omission or addition) slips through the tag/length checks. (agree: 0)

## Added in cross-examination (not voted on)
- none
