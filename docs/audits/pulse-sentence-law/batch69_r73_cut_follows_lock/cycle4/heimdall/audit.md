# Heimdall audit

**Question:** Batch 69 CYCLE 4 (the second cycle of the amendment; cycle 3: no consensus findings; the diff is unchanged) = RULING 73 (b) AMENDED (orchestrator 2026-11-13 '18:40'), verbatim: "DO NOT RE-BASELINE THE REFERENCE. The medley reference is a video PBX approved as it is; its hook opens 590 ms before the first word and that was fine. My 400 ms was a number I picked; the reference is the evidence. RULING 73 (b) AMENDED: the IN lead cap is 600 ms, not 400. With 600 the medley reference's hook, 41f29b1f and 37c5b5f5 must recompute UNCHANGED to the frame (say so with the numbers; if 37c5b5f5 clip_02 still moves, tell me by how much before merging), and 13949b7c's clip_01 (3.47 s of dead air) still fails on the old code and passes on the fix."
The delta (after cycles 1 and 2 of batch 69):
- sentence_law.IN_LEAD_MAX_S 0.400 -> 0.600. The comment and docstring are amended, and the hold reason prints the cap rounded.
- test_ruling73 is moved to 600 ms:
  - unit expectations (13.84 / 13.4 bounds);
  - a new unit case, the medley hook's own geometry (cut 14.38 with a 0.56 s lead before 'Bitcoin' at 14.94), keeps its cut;
  - MOVED = {} (no delivered cut may move);
  - the 13949b7c must-fail renamed to 600 ms.
MEASURED with the amended code (the cut tables recomputed on the runs' own files):
- 41f29b1f (the medley reference's run): hook 14.38-19.01, clip_01 14.3-34.16, clip_02 14.3-31.56. All UNCHANGED.
- 37c5b5f5: hook 14.79-23.41, clip_01 14.3-25.27, clip_02 14.38-19.01. All UNCHANGED.
- 0c68b589: unchanged. clip_01 OUT recomputes 29.50 against the recorded 29.51 with the OLD code too, within one hop.
- 13949b7c: hook OUT 27.09 -> 27.78 ((a)); clip_01 IN 10.97 -> 13.84 (600 ms before 'I' at 14.44).
- On the old sentence_law the two 13949b7c must-fail tests FAIL; on the amended fix 33 pass.
FIND: a delivered or reference cut that can still move; a 13949b7c-like dead-air head that passes at 600 ms; a test that no longer tests ruling 73 after the change; anything in the delta beyond the constant and the tests. Only state what you can verify from the diff. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0017
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- glm:F1 [low] The new medley-hook unit case does not actually exercise the amended cap: the reference's 0.56 s lead also passes at 400 ms, so the case tests nothing that distinguishes 600 from 400 (the ruling-73 amendment's distinguishing case is 13949b7c, which is only covered by the must-fail class). (agree: 1)

## Added in cross-examination (not voted on)
- none
