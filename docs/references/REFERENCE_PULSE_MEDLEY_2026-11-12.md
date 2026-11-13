# REFERENCE: the L-y medley of 2026-11-12 (PBX: "yooo!!!!! YES!!!!"; protected by orchestrator note '23:35')

The orchestrator relayed this at 23:35 ET on 2026-11-12. PBX watched the 41f29b1f L-y medley, run
pinned_20261113_031328. The orchestrator had sent him the files in chat at 23:30, and PBX replied, verbatim:
"yooo!!!!! YES!!!!". The orchestrator: "This is the approved SHAPE."

This is the fourth protected reference. The first three are:
- the frozen v2f (references/v2f_2026-11-06, Law 22);
- the approved preview (references/pulse_preview_2026-11-11, law L-d);
- the review video (references/pulse_moments_2026-11-12).

This one is the first medley in the L-y shape.

## What it is a reference for
- **SHAPE (law L-y VOICEOVER IS MINIMAL).** The order is: the hook, then the clips back to back, ONE closing line after
  the last clip, the sign-off (shout-out), then the outro. There is no intro and no bridge. Timeline (seconds; both
  formats, qa/concat_manifest_*.json):

  | Segment | From | To |
  |---|---|---|
  | hook (Natalie Brunell) | 0.000 | 4.667 |
  | clip_01 (What Bitcoin Did) | 4.667 | 24.542 |
  | clip_02 (Stephan Livera) | 24.542 | 41.833 |
  | the closing line (vo_bridge_01, after clip 2) | 41.833 | 52.333 |
  | shout-out | 52.333 | 61.875 |
  | outro | 61.875 | 66.333 |

- **CLIP-TO-CLIP FLOW.** Three channels, joined back to back by hard cuts. The DEC-4 planner placed no dissolve, because
  neither join has room:
  - hook tail 0.31 s against clip_01 lead-in 0.01 s;
  - clip_01 tail 0.07 s against clip_02 lead-in 0.04 s.

  The evidence is TRANSITIONS.json and both render logs' "Transitions (crossfade): []".
- **LAYOUT.** In 16:9 the hook is two faces and clips 1 and 2 are single. In 9:16 the hook is a two-speaker stack
  (stack2) and clips 1 and 2 are single (VERTICAL_LAYOUT.json).
- **THE SINGLE CLOSING LINE.** One line, after the last clip, before the shout-out. The reference is its position and
  that there is only one, not its wording.

## What it is NOT a reference for
- **Recency.** clip_02 (Sjb6lUiL0m4, published 2026-11-11T18:03:23Z) was 33 h old at delivery. Law L-v 3 holds any
  later run whose time-sensitive clip is more than 24 h old at render time.
- **Caption, title, and the takeaway's wording.** All three predate the house-style rules (order '22:40' item 6).

## Open rows, recorded as measured (the run HELD at 23:10 ET; GATE_REPORT.json, ATTESTATION.json)
1. **G20_signoff_names_all, both formats: FAIL.** The script says "... and Stephan Livera". The decode of the
   rendered audio reads "... and stefan lavera", and the registry has no spoken-form alias for that name. Orchestrator
   ruling 24 ('23:20') covers it.
2. **G8_sharpness 9:16: FAIL.**
   - clip_01's output median is 10.8, against the 10.84 floor.
   - clip_02 keeps 0.732 of its source's sharpness after the 9:16 reframe.

   Ruling 25 covers it.
3. **G9_tail 9:16: FAIL.** Tail luma is 13.6 against 14.73. The tail audio, -39.6 dBFS, passes. Ruling 26 covers it.
4. **ATTESTATION.** The record says "executed code not at the recorded revision: HEAD moved during the run 1f50a0ca ->
   9f75e686". The cause was the integrator's own docs commits during the render (bible E-FAIL-078). Ruling 27 covers
   it.

## Where it is
- **Files.** `references/pulse_medley_2026-11-12/` is read-only. `SHA256SUMS` lists all 200 files:
  - `out/segment.mp4` (16:9, sha256 65a85302...) and `out/segment_vertical.mp4` (9:16, sha256 e01c7138...), the run's
    outputs;
  - `PIN.json` (data/moments_pins/MOMENTS_PIN_221238.json, sha256 bbd09ab0..., the builder's seal 41f29b1f);
  - `PINNED_DECISION.json`, `edl.json`, `cuts_final.json`, `CUT_ACCEPTANCE.json`, `SENTENCE_LAW.json`,
    `CLIP_CONTRACT.json`;
  - `TRANSITIONS.json`, `VERTICAL_LAYOUT.json`, `vertical_overrides.json`;
  - `GATE_REPORT.json`, `ATTESTATION.json`, `REPORT.md`, `VERDICT.txt` (HOLD), `status.json`, `PROVENANCE.json`;
  - `run_log.txt` and both render logs;
  - `EDITORIAL_REVIEW.json`, `EDITORIAL_GATE.json`, `STORYBOARD.md`;
  - `qa/`: the prepared clips, the concat and G14 manifests, the contact sheets;
  - `vo_audio/`: the closing line and the sign-off stems, VO_MANIFEST.json;
  - `sources/` and `transcripts/`: the acquired windows;
  - `VERIFY/`;
  - `PBX_VERDICT.md`: his words, this scope and the open rows.

  No REVIEW_DROP.json: the pipeline sent nothing.
- **Run.** runs/pinned_20261113_031328, code 1f50a0ca at launch. Rendered 22:12:50 to 23:10 ET on 2026-11-12.
- **Tag.** `ref-pulse-medley-2026-11-12` (annotated, with PBX's words).

## Protection and the regression fixture (Law 22 spirit: it must keep producing the same shape)
`pipeline/regression.sh` step 8 runs four checks; each must pass:
1. `pipeline/check_reference_manifest.py`: every listed byte is unchanged and nothing has been added.
2. The tag exists.
3. The tracked files equal the tag.
4. `pipeline/check_medley_reference.py`: the reference's decisions reproduce with the CURRENT code on its frozen files.

What check_medley_reference.py reproduces:
- **Shape.** edl_rules R11 passes on its EDL, and pinned.moments_vo builds the same VO slots from its PIN.
- **Selection.** pinned.validate_range gives the same lock indexes.
- **Cuts.** sentence_law.write_lock_cut_table, the table stage_cut writes for this pin, gives cuts within 10 ms.
- **Flow.** The lead-in / tail are within 10 ms, and pulse_transitions.plan gives the junctions the renders used.
- **Layout.** vertical_layout.classify gives the same 9:16 shot classes and boundaries.

The check takes about 70 s, almost all of it layout. Tests: `pipeline/test_check_medley_reference.py` (11). The real
reference and an untouched copy reproduce. Each of these fails:
- an intro line;
- a bridge between clips;
- a moved selection lock;
- a moved cut;
- a changed lead-in;
- a render junction the plan does not place;
- a changed layout;
- a dropped segment.

A missing reference is exit 2.

A full re-render through `run_fresh --pinned` is not part of the regression: it takes about 30 min of GPU0. It would
also stop at the pinned stage by design. The PIN predates the L-v 3 seal fields: no segment states `time_sensitive` or
`source_published_at`, and pinned.prepare now requires both of a moments pin (checked 23:47 ET:
pinned.recency_problems lists all three segments). Its clip_02 is also more than 24 h old. The fixture checks the
decisions that make the shape. It does not bypass any check.
