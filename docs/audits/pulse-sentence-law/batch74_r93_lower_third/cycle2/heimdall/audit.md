# Heimdall audit

**Question:** Batch 74 CYCLE 2 = RULING 93's render side (cycle 1's question has the ruling and the measurement). Cycle 1's ONE consensus finding was fixed: single_crop returns (None, {"why": "no face samples"}) for an empty face list, and render_vertical keeps its face-centred x for a non-int crop_x (test added). The diff is otherwise unchanged.
VERIFY on the diff: (1) the fix closes the crash without changing any other result; (2) every x single_crop can return keeps every sampled face box inside the crop with FACE_MARGIN_FRAC of the crop width on both sides, or is today's face-centred x; (3) a shot with no lower-third span keeps today's x exactly; (4) nothing changes the shot classes or boundaries (the protected references compare those); (5) G10 stays MONITORING. Only state what you can verify from the diff. Reply with the JSON verdict; at most 3 findings; if nothing, say so.

**Panel:** qwen27b, glm  |  **Cost:** $0.0010
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
