# pp-selectid audit 0332 (ruling 32: snap outward to whole sentences): cycle 1 consensus

Synthesis by the pp-selectid session, 03:33 ET Nov 13, written before cycle 2.

**Run.** C1_STEP.diff covers ledger_build.py, test_ledger_build.py, funnel.py and funnel_pre_edge.py. No P0.
Verdicts:
- grok: no P0, "SHIP: yes";
- qwen: "yes with conditions", P2 only;
- glm: "yes with conditions".

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | SNAP_MAX_S = 20.0 is a copy of package.SEG_MAX_S and can drift (qwen P2-1, glm P1-4 and its condition 1) | IMPLEMENTED: test_the_snap_limit_is_the_packagers_clip_limit asserts LB.SNAP_MAX_S == PK.SEG_MAX_S. ledger_build does not import package; it is the lighter module, and package imports the verdict stack. Both limits are measured the same way: a span's first word start to last word end on its word record (the moment's duration_s, which usable() compares with SEG_MAX_S). |
| K2 | The funnel tools hard-code their paths (qwen P2-2 / P2-3, glm P2-3) | IMPLEMENTED: the ledger path comes from ledger_build.INGEST_ROOT (env PP_INGEST_ROOT), and the WAV dir is proof_ly.SCRATCH/lv2, the build's own default --work-dir. |
| K3 | The 1.0 s marker margin leaves edge-adjacent speaker changes unmeasured at the snap. Is L-v 2's single-speaker rule a REQUIRED, blocking gate (glm P1-2, its condition 2)? | VERIFIED, outside the diff. transcript_truth.verify_segment: `ok = cmp_["ok"] and turns["turn_change_inside"] is False`, so an unmeasured speaker (None) is not ok. package.build: a moment is cleared only when cut_ok (t["ok"] and CUTTABLE). The pin's "second_pass" row needs every segment's ok, and "second_pass" is in package_pin.REQUIRED_GATES. No snapped span reaches a pin without one speaker measured. |
| K4 | snap_risk mangles a non-list risk through list() (glm P1-1, condition 3) | IMPLEMENTED: a risk that is not a list raises TypeError, which make() counts as malformed. Tested. (It was pre-existing behaviour of make(), `list(r.get("risk") or [])`.) |

## Answered or kept

- **SNAP_GUARD's retirement (the audit question):** all three reviewers find no risk class that no downstream gate judges.
  - glm: the moment text is the word record's snapped sentences, so every text-reading gate reads the added words.
  - The exclusion verdict screens every L-u hard risk on the moment text.
  - About-Bitcoin can only gain, since the row's text is a substring.
  - The miner's scores stay the row's, which is ranking only.
- **glm P1-3 (the caption lookup's failure):** answered. caption_source returns (None, why). marker_inside treats None as no measurement, and L-v 2 decides (K3).
- **glm P1-4b (the anchor-time measurement):** unchanged code (offset_s), covered by the existing test_the_hit_is_measured_against_the_rows_own_caption_times.
- **glm P2-1 (">>>" also counts as a marker):** KEPT. It fails closed: a run of three is still a speaker marker in caption text.
- **glm P2-2 (lazy vo_fidelity import):** KEPT. vo_fidelity is pure Python (lexicon and regexes), with no GPU and no network.
- **glm P2-4 to P2-10:** test strictness and tool robustness, all diagnostic or test-only. P2-5 and P2-9 are noted: the asserted info fields exist only on the success path.
- **qwen P1-1 to P1-6:** each one self-resolved as correct in its own text.

## Measured effect (offline, no vendor call; scratchpad snap_effect.py on today's 510 rows at 08:31 UTC)

- 12 rows come back, snapped beyond the old 3-word limit. All are 20 s or less; 4 of them are eligible on screen.
- 23 stay out for running over 20 s.
- 1 stays out for a caption speaker marker inside the span.
- 35 do not anchor at all.

## Verification

- test_ledger_build 33 OK (31 before). Four SNAP_GUARD-era tests became two. New: the 20 s limit, the marker, the price risk and the mirror test. The type check is an assertion inside the price-risk test. (Corrected after cycle 2 started: the cycle-2 prompt carries the earlier, wrong "34".)
