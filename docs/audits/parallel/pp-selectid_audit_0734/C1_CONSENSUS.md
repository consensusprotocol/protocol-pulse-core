# Audit 0734 (the orchestrator's 07:30 rulings (A) and (C)), cycle 1: consensus

Reviewers:
- grok-4.20: SHIP yes, three <medium>.
- qwen3.8-27b: SHIP yes with conditions. Its <critical> and <high> each resolve inside its own text: "Since nv_order is
  deterministic and inputs are identical, it returns the same plan"; "The extraction seems behavior-preserving".
- glm-5.3-flash: SHIP yes with conditions, all findings <medium>.

No defect that could ship a wrong pin. Upper-bound cost: about $0.37 ($0.091 + $0.123 + $0.158), outside
SPEND_LY.json.

## Implemented

- qwen condition 3: test the added-clip search against a DOOMED clip.
  - test_a_doomed_clip_is_never_the_added_clip: z fails exclusion in angle 1's line-up, which makes it doomed for the
    whole build.
  - Angle 2's takeaway then loses its value verdict on 39 s of clips. nv_order skips z, no no-voice line-up exists,
    and ruling 91's one rewrite is used. z never comes back.
  - Mutation M21 (drop "mid in doomed" from nv_order) is killed by it. The mutation check: 16 of 16 killed.

## glm's conditions, resolved from the code

- (1) "Are fid / cx always bound at the fixed-caption check?" Yes. In no_voice, `fid, cx = paid_gates(...)` runs
  unconditionally inside the `with` block. Every earlier exit (the cheap gate, the clips' own gates) returns None.
  - So when `fixed = None` and the check below it run, both are bound.
  - The (C) tests execute that path: a caption failing its cheap gates, a caption failing its verdict, a failing title.
- (2) "Does any other module import the removed no_voice_fits?" No. grep over the scratch copy (pipeline, tests) and
  over the main tree's pipeline and scripts finds no reference.

## Refuted, with evidence from the code

- grok <medium> 1 / glm (b): "the extraction of fixed_caption_gates may change ruling 65's voiced path".
  - rewrite_alone's build_pk was assemble_medley(order, by_id, dict(fields, **{slot: line}), ctx,
    f"{pk.get('vo_kind')}; {why}") with slot "caption", plus p["medley"] = pk.get("medley"). The helper makes exactly
    that.
  - a_use(pk3) is {sg["label"]: a_by[sg["moment_id"]] for sg in pk3["segments"]}, the helper's dict.
  - man's channels come from pk (before) and pk3 (now): the same segments.
  - Existing tests run the voiced path through the helper: TestRuling65Caption's fixed-caption tests and ruling 66's
    caption case. All pass, and M19 (drop caption_fallback in the helper) kills 4 tests, ruling 65's among them.
- grok <medium> 2: "no_voice passes cleared as by_id". no_voice already assembled its package with cleared as by_id,
  and every clip in the order comes from it: nv_order picks from cleared, and segs is a line-up of cleared moments.
- grok <medium> 3: "where does pk['no_voice']['added_clip'] come from". no_voice's fields carry "no_voice":
  {"why", "added_clip": added, "lineup_before", ...}, unchanged code. assemble_medley copies it to pk["no_voice"].
- qwen condition 1, "seed 7 in fixed_caption_gates' context call". The same seed as before the extraction, and the
  same as paid_gates' own context call (CI.check_contexts(..., writers_v, 7, ...)).
- qwen condition 2, "lone_slot coverage". lone_slot returns a slot only when every violation's slot is in {caption,
  title} and there is exactly one. A "-" rule (RUNTIME, R4, LY_SHAPE, RECENCY) or a clip's own gate returns None, so no
  fixed caption.

## Verified, no change (glm's informational points)

- The candidate construction, the line-up rules and the registry check moved verbatim from ruling 3's no_voice into
  nv_order. glm compared old lines 182-199 with the new 144-160.
- `fid.get("measured")` falsy means no fixed caption (fail closed).
- `segs` is never empty: a line-up is the hook + 2-4 clips.
- registered_skipped is copied into the note when present.
- note["medley"] is recorded when a clip is added, as before.
