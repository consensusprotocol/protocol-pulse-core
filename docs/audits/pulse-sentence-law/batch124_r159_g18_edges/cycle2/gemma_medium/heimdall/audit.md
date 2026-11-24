# Heimdall audit

**Question:** TASK: cycle 2 of the audit of batch 124 (Protocol Pulse, Python): G18's edge check follows ruling 143 (the same diff as cycle 1). Cycle 1: gemma PASS, glm PASS, qwen PASS; its strongest claim (a shift aligned as replaces) was disproved by running difflib (a shift aligns as delete / equal / insert and stays HARD). Only state what you can verify from the diff and the cited lines. If uncertain, say so. Do not guess.

TRACE AND ANSWER:
T1. Give one concrete (expected, heard) pair of English sentences for which _edges_substituted_only returns True although the CUT is wrong (a clipped, shifted or mid-word cut, not a decoder's reading), and run difflib's opcodes for it by hand. If you cannot construct one, say NONE.
T2. The edge block runs only when row["identity"] is empty. Can an identity difference that the audio did NOT clear ever coexist with the edge block clearing the edges?
T3. Any other defect.

OUTPUT: for each finding, severity (critical|high|medium|low), file:line, the concrete failure, the fix. If none, say NONE.
REMINDER: only what the diff and the cited lines show; say when uncertain.

**Panel:** gemma  |  **Cost:** $0.0030
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- gemma:F1 [high] The edge-clearing block reuses the 'omission_adjudication' result from the identity check, skipping the necessary audio fidelity check for the edges. (agree: 0)

## Added in cross-examination (not voted on)
- none
