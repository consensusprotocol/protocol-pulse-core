# Heimdall audit

**Question:** TASK: cycle 2 of the audit of batch 116 (Protocol Pulse, Python), landed in the ruling 153 lockstep: ruling 139 on the render's lock. Same diff as cycle 1. Only state what you can verify from the diff and the cited lines. If uncertain, say so. Do not guess.

RULING 139 (verbatim): "CUTTABLE's sentence-edge part FLAGS when the cut sits at a word boundary; L-v 2's word check and a cut mid-word stay HARD." Ruling 147 (3): it "binds the render's lock too". CYCLE 1: gpt-oss F1 (high): flag_sentence_edges opens edl.json and reads c["clip_id"] without checks. Our reading: stage_cut runs after validate wrote edl.json, and every cuts_final.json entry carries clip_id (write_lock_cut_table); an exception there fails the stage, which HOLDS the run (fail closed), so it can never pass a bad edge. qwen27b's cycle-1 answer was lost at a pause.

TRACE AND ANSWER:
T1. In the diff, list every path by which a lock edge becomes 'sentence_soft' (planned as a sentence boundary and flagged). For each, say whether it can apply to: no audio between the words; a trimmed word's edge; ruling 73's bounds (OUT never before the last locked word's decoded end, IN at most 600 ms before the first word); a cut inside a word.
T2. Is F1 a real defect (a bad edge passing) or a fail-closed stop?
T3. Any other defect.

OUTPUT: for each finding, severity, file:line, the concrete failure, the fix. If none, say NONE.
REMINDER: only what the diff and the cited lines show; say when uncertain.

**Panel:** gptoss  |  **Cost:** $0.0023
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
