# Heimdall audit

**Question:** Batch 66 = RULING 71 (orchestrator 2026-11-13 '15:45'), verbatim: "G19, THE ONE-FRAME PUNCH-IN. The gate is right: a source shot change after the speaker's last word and before our crossfade is a one-frame flash of a different framing. The defect is in prepare, which measures only the 16:9 and with the hard-cut threshold. Fix at prepare, both formats in parity: in the TAIL region (from speech_off to the clip's out point) any source shot change is snapped out, i.e. the clip's out point moves back to the last frame before it, when that keeps at least the required tail after the last word (G3c / G17 tail rules unchanged; if it cannot, hold with that reason). In the tail region the detection threshold is the lower of the two formats' needs: measure the scene score on both the 16:9 prepared clip and the 9:16 crop, and snap if either is >= 0.3. Same for the HEAD region before speech onset. G19's own threshold stays 0.3. Must-fail test: this hook (frame 406) fails on the old code and passes on the fix."
Background (measured): pin 0c68b589's 9:16 held on G19 because the hook's last frame (406, 16.917 s) is the source's punch-in on the same host, 57 ms after his last word. The ffmpeg scene score of that frame: 16:9 prepared clip 0.2718, the 9:16 crop 0.3172 (the encoded 9:16 final 0.3167). The cut threshold, shot_snap.SCENE_CUT, is 0.3. prepare's shot_snap.apply (orchestrator 08:30, recut run 6) is a VISUAL snap: the frames after a change past the last word hold the last frame before it (and before the first word, the first frame after it). The audio stream and the frame count stay unchanged, so cut times, G3c / G16 / G17 / G18 and the A/V lock are untouched. It measured only the 16:9 prepared clip.
Interpretation taken (recorded for the orchestrator): "the out point moves back to the last frame before it" is implemented as that visual snap (the last visible frame of the speaker's shot is the last before the change; audio stays on the sentence, the 08:30 rule this ruling does not revoke). So the G3c / G17 tail rules stay unchanged by construction. The required quiet is still enforced on the speaker's own shot: after the last word sentence_law.TAIL_MIN_S, and before the first word HEAD_LEAD_MIN_S (80 ms) for the hook, which starts playback, and LEAD_MIN_S otherwise. If the snap cannot keep it, apply() returns "refused" with the reason and stage_prepare raises a HOLD naming it.
The change:
- render_vertical.auto_graph(plan, colour=""): reframe_auto's filtergraph moved verbatim into one function (each shot trimmed, its own filter, the colour re-declared, concatenated to [vout]); reframe_auto calls it.
- shot_snap.scene_changes_9x16(clip): vertical_layout.classify(clip) (CPU, the layout stage's own call) -> render_vertical.auto_graph -> ffmpeg scene scores of the 9:16 picture, before any encode; frames >= SCENE_CUT.
- shot_snap.apply: the 16:9 and 9:16 changes are merged (per frame, the higher score) into the existing plan(); the record keeps hard_cuts (16:9) and hard_cuts_9x16; the guard above returns "refused" before any encode.
- run_fresh.stage_prepare: a refused snap raises Hold("<clip>: shot snap refused (ruling 71): <reason>").
- Tests (test_shot_snap.py):
  - CPU: a change only the 9:16 crop sees is snapped (frame 406 held on 405); nothing to snap leaves the clip; a hook snap that cannot keep 80 ms is refused with no encode, and the same change on a non-hook clip is snapped.
  - GPU0 MUST-FAIL on 0c68b589's real prepared hook: on the old shot_snap.py it FAILS ({406: 0.317224} left after prepare); on the fix the whole file passes 7/7, including the existing synthetic tests.
FIND: a second code path between the renderer's 9:16 picture and the one prepare scores; a change in either format that is still not snapped (head or tail); an audio, frame-count or cut-time change; a guard that refuses wrongly or lets a short quiet through; a HOLD that names no reason; G19 or its threshold changed; a test that does not test what it claims. Only state what you can verify from the diff. Reply with the JSON verdict; keep the reasoning short; at most 4 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0063
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- glm:F1 [medium] The 9:16 scene-score regex drops the last frame's score, so a punch-in on the final frame can never be snapped in the 9:16 path (16:9 path unaffected). (agree: 1)

## Added in cross-examination (not voted on)
- none
