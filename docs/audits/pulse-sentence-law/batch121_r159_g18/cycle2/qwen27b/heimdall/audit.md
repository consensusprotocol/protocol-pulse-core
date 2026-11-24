# Heimdall audit

**Question:** TASK: cycle 2 of the audit of batch 121 (Protocol Pulse, Python): G18 follows ruling 143 for every lock (the same diff as cycle 1). Cycle 1: qwen27b (high effort, traced) PASS, gemma PASS, gpt-oss PASS: no findings. This cycle asks for the strongest case AGAINST the change. Only state what you can verify from the diff and the cited lines. If uncertain, say so. Do not guess.

TRACE AND ANSWER:
T1. Construct the most dangerous input you can for the changed line: a final whose words differ from the source span's decode where the difference is classed NON-material but changes what the speaker asserts (a tense, a modal like "will"/"would", "can"/"can't" split by the decoder, a plural/singular). Which of these does pinned.material_pair (via _material) class as material, and which pass now on the audio check?
T2. The audio check (span_fidelity between the prepared clip and the source span) passes when the clip plays the speaker's own audio. In that case, is a decoder's word-form difference ever a claim we make that the speaker did not make?
T3. Any other defect.

OUTPUT: for each finding, severity, file:line, the concrete failure, the fix. If none, say NONE.
REMINDER: only what the diff and the cited lines show; say when uncertain.

**Panel:** qwen27b  |  **Cost:** $0.0097
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
