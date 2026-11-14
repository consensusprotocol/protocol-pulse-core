# PBX's verdict on the L-y medley of 2026-11-12 (run pinned_20261113_031328)

The orchestrator relayed it at 23:35 ET on 2026-11-12. PBX watched the 41f29b1f L-y medley. The orchestrator sent him
the files in chat at 23:30 ET. This pipeline sent nothing, because the run HELD. PBX replied, verbatim:

"yooo!!!!! YES!!!!"

The orchestrator: "This is the approved SHAPE."

## What it is a reference for
- SHAPE (law L-y VOICEOVER IS MINIMAL). The order is: the hook, then clip 1 and clip 2 back to back, ONE closing line
  after the last clip, the sign-off (shout-out), then the outro. There is no intro and no bridge. Both concat manifests
  have the same timeline (seconds):

  | Segment | From | To |
  |---|---|---|
  | hook | 0.000 | 4.667 |
  | clip_01 | 4.667 | 24.542 |
  | clip_02 | 24.542 | 41.833 |
  | the closing line (vo_bridge_01, after clip 2) | 41.833 | 52.333 |
  | shout-out | 52.333 | 61.875 |
  | outro | 61.875 | 66.333 |

- CLIP-TO-CLIP FLOW. Three channels, Natalie Brunell, then What Bitcoin Did, then Stephan Livera, joined back to back by
  hard cuts. The DEC-4 planner placed no dissolve, because neither join has room for one:
  - hook tail 0.31 s against clip_01 lead-in 0.01 s;
  - clip_01 tail 0.07 s against clip_02 lead-in 0.04 s.

  The evidence is TRANSITIONS.json and both render logs' line "Transitions (crossfade): []".
- LAYOUT, 16:9 and 9:16. In 9:16 the hook is a two-speaker stack (stack2) and clips 1 and 2 are single; see
  VERTICAL_LAYOUT.json.
- THE SINGLE CLOSING LINE: one line only, after the last clip and before the shout-out. The reference is its position
  and the fact that there is one, not its words.

## What it is NOT a reference for
- RECENCY. clip_02 (Sjb6lUiL0m4, published 2026-11-11T18:03:23Z) was 33 h old at delivery. Law L-v 3 now holds any
  run whose time-sensitive clip is more than 24 h old at render time.
- CAPTION, TITLE AND THE TAKEAWAY'S WORDING. All three predate the house-style rules (order '22:40' item 6).

## Open rows, measured: the run HELD at 23:10 ET (GATE_REPORT.json, ATTESTATION.json)
1. G20_signoff_names_all, both formats: FAIL. The script says "... and Stephan Livera". The decode of the rendered
   audio reads "... and stefan lavera", and the registry has no spoken-form alias for that name. Orchestrator ruling
   24 ('23:20') covers it.
2. G8_sharpness 9:16: FAIL.
   - clip_01's output median is 10.8, against the 10.84 floor.
   - clip_02 keeps 0.732 of its source's sharpness after the 9:16 reframe.

   Ruling 25 covers it.
3. G9_tail 9:16: FAIL. Tail luma is 13.6 against 14.73. The tail audio, -39.6 dBFS, passes. Ruling 26 covers it.
4. ATTESTATION: the run was not deliverable on the pass path. The record says "executed code not at the recorded
   revision: HEAD moved during the run 1f50a0ca -> 9f75e686". The cause was the integrator's own docs commits during
   the render (bible E-FAIL-078). Ruling 27 covers it.

## The run
- Run directory: runs/pinned_20261113_031328.
- PIN: data/moments_pins/MOMENTS_PIN_221238.json (sha256 bbd09ab0...). The builder sealed it as 41f29b1f on branch
  pp-selectid 40938e34.
- Code: 1f50a0ca at launch.
- Rendered from 22:12:50 to 23:10 ET on 2026-11-12. Render took 28.5 min, gates 12.0 min, verify 9.3 min.
