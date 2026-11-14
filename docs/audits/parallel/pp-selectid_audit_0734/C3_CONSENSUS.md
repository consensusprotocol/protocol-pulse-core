# Audit 0734 (the orchestrator's 07:30 rulings (A) and (C)), cycle 3 (the post-cycle-2 delta): consensus

Reviewers:
- grok-4.20: P2 / P3 only, SHIP yes with conditions.
- glm-5.3-flash: one P1, settled from the code below; "yes with conditions".
- qwen3.8-27b: no defect. Its one <high> concludes "This is correct". Its text ends mid-sentence (finish=stop), with no
  SHIP line.

Upper-bound cost: about $0.35 ($0.141 + $0.087 + $0.121). The three cycles together: about $1.04, outside
SPEND_LY.json.

## glm P1, settled ("does merge_fid AND the old verdict's ok, killing (C)'s verdict-failure path?")

No. merge_fid (pipeline/package.py) rebuilds `ok` from the MERGED violations:
- `det["violations"]` = the old ones minus the caption slot's, plus the fixed line's deterministic ones;
  `det["ok"] = not det["violations"]`;
- `ver["ok"] = measured and not ver["violations"]` (over the merged list);
- `ok = det["ok"] and ver["ok"]`.

So a caption-only verdict failure merged with the fixed line's clean record is ok. As glm asked, by execution:
test_c_a_no_voice_caption_that_fails_its_verdict_becomes_the_fixed_caption passes (the package ships, every gate PASS,
the refusal recorded as VERDICT_NO).

## grok's conditions

- (a) "the measured merge": fid3's measured = the paid verdict's measured AND the fixed line's (always True). The (C)
  guard admits only a measured paid verdict, so fid3 is measured.
  - A replayed title verdict makes fid3 replayed. The inventory row then reads replayed, and package_pin.gate_problems
    refuses it (never deliverable), as on every other path. No change.
- (b) IMPLEMENTED (test only): test_c_the_fixed_caption_still_passes_its_own_gates_or_the_line_up_ends now also runs
  the fixed caption's context check UNMEASURED (no verdict). The line-up ends ("the fixed caption ... did not pass its
  gates"), as it does for a measured failure.
  - One code path serves both rulings' no-voice shapes, and the ruling-3 path runs the same no_voice().

## Declined, with reasons

- grok P3 (write rec["no_voice_plan"] on every path): it records why no no-voice line-up existed. When one exists,
  no_voice()'s own note (rec["no_voice"]) carries the plan's outcome. Non-blocking.
- glm P3 (the `refused` records lack a "slot" key): by construction every one is the caption's (lone_slot ==
  "caption"). Record-keeping only; no code change after cycle 3 for it.
- glm P2s (the note string, no_voice_fits importers): verified in C1 / C2 (rewrite_alone passes the same why; grep
  finds no importer).

SHIP. FINAL.diff = C3_STEP.diff plus grok's requested test variant (test only). Mutation check 18 of 18 killed;
19 suites, 546 tests.
