# pp-selectid audit of the 07:42-08:40 diff: cycle 1 consensus (synthesis by the pp-selectid session, 08:45 ET Nov 12)

**Run.** Cycle 1 ran on C1_STEP.diff: 42,648 bytes, prompt 65,170 bytes. The reviewers:
- grok-4.20-0309-reasoning (xAI): SHIP no;
- qwen/qwen3.8-27b, Heimdall, reasoning effort none: SHIP yes with conditions;
- z-ai/glm-5.3-flash, Heimdall, effort none: SHIP yes with conditions.

The earlier attempt through the router's JSON back-end (08:01) returned empty replies and is void.

**The rule** is the same as tonight's earlier audits: consensus (two or more reviewers) is implemented, and a unique
finding is evaluated on its evidence.

## Consensus: implemented

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | self_repair's 4-letter match against the clip's first word is a weak heuristic (grok P2, qwen P1-4 / P2-1, glm P1-3) | IMPLEMENTED: the next word must BE the clip's first word (`_w(next) == _w(first)`, non-empty), so a repair is one dash-ended, same-speaker, proper prefix of exactly that word |
| K2 | the R4 algebra (r4_max_vo_words / min_vo_words against runtime()): qwen and glm verified it by hand; grok asked for proof on every path | IMPLEMENTED as a test: `test_the_r4_word_bounds_invert_runtime_and_the_share_exactly`, over content 15-50 s and 1-4 VO lines. The bound passes; one word more (share) or one word less (60 s) fails |

## Unique findings, evaluated

| finding | disposition |
|---|---|
| grok P0: the runtime / R4 change accepts a package the old gate refused (63 words: R4 41.0 % -> 38.9 %) | KEPT, disclosed. That package is still refused, now by the runtime gate (72.41 s > 70; test_the_moments_r4_on_tonights_numbers). The 45 % cap is the orchestrator's ruling 9, and the deployed edl_rules.py reads MOMENTS_VO_SHARE = 0.45. runtime() is the factory's own arithmetic, read in the deployed edl_rules._r4_moments and pinned.py:290: the gate now refuses exactly what the consumer refuses. The 60 s floor moved: the builder's old estimate was 3-4 s lower. That is disclosed in STATE (07:58: 57.88 s vs 61.23 s), and the render measures the final (design section 8, open) |
| glm P0-1 / P1: majority drops a violation whose slot is not a line slot | REFUTED on the code: check_verdict raises on a claim whose line is not a slot (vo_fidelity.py: `c["line"] not in by_slot` -> ValueError -> VERDICT_UNAVAILABLE, slot "-", not measured), and an unmeasured run votes "fail" on every slot. Hardened anyway (H1): a violation on an unknown slot now fails every slot |
| glm P2-1: does FINAL_TAIL_S hold the sign-off? | CONFIRMED: the deployed edl_rules.py:156 reads `FINAL_TAIL_S = 14.30  # ... credits card + sign-off, outro, cut ...`, equal to eligibility.TAIL_S |
| glm P1-6: is renderer_geometry inside the seal? | OUTSIDE, as intended: package_pin.seal hashes segments, VO, sign-off, title, caption and gates; cut_evidence travels beside the seal (to_pin) |
| glm P1-4: the repaired span loses punctuation | REFUTED: span_text joins the same word texts (`w["text"]`); the rebuilt span is the same form minus the leading repair |
| glm P1-1: replayed = any(run) | KEPT: one replayed run marks the row replayed, which refuses the pin (L-j); fail closed |
| glm P2-3: pin_and_verify fakes validate_range | KEPT, documented: the same offline fake as smoke_r7; the real validate_range runs on the acquired window at the render |
| qwen P1-3: majority does not check that the runs share the lines | KEPT as a caller contract: the only callers pass one `lines` to every run (driver, tests) |
| qwen P1-5: the facts path is hard-coded in the driver | KEPT: it is the orchestrator-designated evidence file (read-only); its sha256 is recorded with the evidence |
| glm (units of VO_S) | REFUTED: VO_S = (6.0, 22.0) is seconds (package.py:49); `VO_S[1] * WPS` is words |
| grok P1: rounding to 2 dp at a 70.00 s edge | KEPT: segment durations are already 2-dp word spans and VO seconds are multiples of 0.4; the factory computes on its own decode's spans, a larger difference than the rounding |

## Edits after the cycle-1 snapshot (in the cycle-2 diff)

- **K1, H1, K2**: as above.
- **Ruling 10 (08:40):** package.MOMENTS_TAKEAWAY_WORD_CAP = 30 for the VO line after the LAST clip; bridges between
  clips keep 20. Tests: 31 words refused, 30 pass, a 21-word bridge between clips refused.
- **08:18 item 4 / 08:29:** package.once_then_majority + with_votes.
  - A model verdict that is not PASS on its first run gets the three-run majority once.
  - The votes go on its inventory row.
  - The driver uses it for fidelity (per line, VF.majority), context, exclusion and coherence.
  - exclusion_for takes a seed.
