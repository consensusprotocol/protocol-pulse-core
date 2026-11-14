# claude-fable-5-2 (81 s) usage={'input_tokens': 3170, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'cache_creation': {'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0}, 'output_tokens': 7554, 'output_tokens_details': {'thinking_tokens': 5410}, 'service_tier': 'standard', 'inference_geo': 'global', 'speed': 'standard'}

**Verdict: not mergeable as shown.** Three BLOCKING findings: degenerate durations now pass, the ≥ 2 channels rule is hollowed out, and nothing in the diff delivers deviations to PROVENANCE or the caption. Line numbers are new-file numbers computed from the hunk headers.

**Limits of the diff.** `edl_rules.py` ~226–230 (where `dur` and `ch` are derived) and ~240–242 (presumably the distinct-channel check) are not shown. No caller, validate-stage, PROVENANCE, caption or qa_gates code is in the diff.

## (1) Integrity weakened

- **1a. BLOCKING: "≥ 2 channels per video" can be met by a channel with no screen time.** The per-channel floor at `edl_rules.py:245-246` is now only a deviation. If the unseen check counts keys of `channels`, then `[{A, 15}, {B, 0}]` returns PASS: channel B is registered at `:238-239` with total 0. Before this change it failed with "min 8s". The 8 s floor was the only visible guarantee that a second channel actually appears on screen.

- **1b. Non-blocking, needs orchestrator confirmation: scope.** REQUESTS R6 item 2 as quoted names only "8-25 s per clip". L-o's taste list as quoted names the hook and clip windows. The per-channel ≥ 8 s demotion (`:245-246`) is covered by neither quote. It is logically needed for a lone 6.1 s clip to survive, but it lacks a replacement hard floor (see 1a).

- **1c. Uncertain: downstream reliance.** No callers are shown, so I cannot verify whether anything depends on R5 rejecting short clips. The strings "min 8s" and "max 25s" are gone, and the pass prefix is now sometimes `R5 PASS with…` rather than `R5 PASS:` (`:251`). Any consumer matching those strings would break.

- **1d. Uncertain: hook in `clips`.** The changed lines apply one 8/25 target to every entry, with no role distinction. If a hook can be in `clips`, it is measured against 25 s, not L-o's 12 s.

## (2) Degenerate durations

- **BLOCKING: zero, negative and infinite durations now pass.** After this change `:233-236` is the only visible per-clip duration check, and it never fails.
  - `0` passes with "8.0s under" recorded.
  - `-3` passes, printed as "clip N: -3.0s (11.0s under…)". Negatives also subtract from the channel total at `:239`.
  - `inf` passes as "infs over"; it previously failed on `> 25`.
- **NaN passes silently with no deviation.** `nan < 8` and `nan > 25` are both False, and the channel total becomes NaN, which also skips `:245`. This predates the change, but the docstring at `:216-220` now asserts the remaining checks are the integrity set.
- **Missing key, None, string: uncertain.** The outcome depends on unseen line ~229. If it is `clip.get("duration", 0)`, a clip with no duration key now passes, where it previously failed. None or a string would raise at `:233` unless coerced; whether an exception fails closed depends on the caller.

## (3) PROVENANCE and caption

- **BLOCKING against the L-o claim: only a reason string is produced.** The diff touches `edl_rules.py` and its test, nothing else. Deviations exist solely as a `"; "`-joined string returned with `ok=True` (`:251`). "The validate stage records it" is unverifiable here, and nothing shows it reaching the Telegram caption. There is no structured return (clip, measured, target, delta).
- **Non-blocking: sizes may be measured against the wrong window.** R5 uses 8/25; L-o as quoted says 12–20 s for clips. A 9 s or 22 s clip records nothing, and a 6.1 s clip records 1.9 s, not 5.9 s. Which window is canonical is uncertain.
- **Non-blocking: double-counting.** For non-negative durations, the channel deviation (`:246`) fires only when every clip on that channel has already fired at `:234`. The test at `test_edl_rules.py:204-205` enshrines the duplicate.
- **Non-blocking: deviations are listed as failures on FAIL.** `:249` joins `failures + deviations` under "R5 FAIL:", so they are indistinguishable from causes. A repair loop or operator reading this would treat taste as a rejection reason.
- **Non-blocking: rounding.** `.1f` at `:234/:236` renders 7.96 s as "8.0s (0.0s under…)", a deviation of recorded size zero.
- **Non-blocking: stale header.** The module docstring at `:18-19` still lists "Every channel >= 8s screen time" as a rule.

## (4) Test weaknesses

- **No degenerate-input tests.** Nothing covers 0, negative, NaN, inf, None, a string or a missing `duration`. The 1a case (two channels, one with zero time) has no must-fail.
- **The must-fail test is loose.** `test_edl_rules.py:213-218` asserts only `startswith("R5 FAIL")`, not which failure fired. Case 1 trips both clip count and (presumably) channel count. Only case 2 isolates the channel check, and that duplicates the existing `test_single_channel_fails`.
- **`test_good_clips_pass` (`:190-191`) asserts only `ok`.** It would not notice a spurious deviation or a changed clean-pass string.
- **No test of the mixed case.** Nothing pins the output of `:249` when failures and deviations coexist.
- **No boundary tests visible.** Exactly 8.0 and 25.0 are not tested in the shown hunks.
- **No end-to-end test.** Nothing asserts that a deviation lands in PROVENANCE or the caption, which is the L-o requirement this change claims to wire.

## Minimum to clear the blocks

1. Add a hard check in `rule_r5` that each duration is a real, finite number greater than 0, and that each counted channel has total time greater than 0. Add must-fail tests for both.
2. Return deviations in structured form, and show (with a test) the code that writes them to PROVENANCE and the caption.