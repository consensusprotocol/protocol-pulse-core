# pp-selectid audit of G17a at the pin stage (hook onset): cycle 1 consensus (synthesis by the pp-selectid session, 02:00 ET Nov 13)

**Run.** C1_STEP.diff covers hook_onset.py, package.py, package_pin.py and the two test files. No P0 holds.
- grok-4.20-0309-reasoning (xAI): no findings, "SHIP: yes".
- qwen/qwen3.8-27b (Heimdall, effort none): two P1s (the pad; "a medley opens with a clip"). SHIP yes with conditions.
- z-ai/glm-5.3-flash (Heimdall, effort none): two "P0"s and four P1s. SHIP yes with conditions.

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | the pin-stage lead is measured on the SOURCE envelope sliced at the planned cut. The render measures its own decode of the prepared file, and the two can differ by one 10 ms frame, so a lead of 80-89 ms here could be a G17a hold at render (glm P0-1 / P1-1, qwen) | IMPLEMENTED: a hook passes here only with HEAD_LEAD_MIN_S + MARGIN_MS (one HOP_S frame) = 90 ms. The missing 20 ms fade-in can only make the check stricter. Test: test_a_lead_within_one_frame_of_80_ms_does_not_pass (85 ms fails, 120 ms passes) |

## Unique findings: implemented, refuted or kept (each verified)

- **qwen P1 (pad double-counted?):** REFUTED, and now TESTED.
  - edge_plan grants LEAD_PAD_S only at a file head whose genuine lead is < 80 ms. The render adds that room tone
    BEFORE the source audio.
  - The slice is the source alone, so the pad is added once.
  - Test: test_a_file_head_hook_counts_the_pad_the_render_adds_once (60 ms of source lead, plus the 250 ms pad,
    passes; the source alone is < 80 ms).
- **qwen P1 ("a medley opens with a clip instead of a hook"):** REFUTED. With no hook-able moment, lineup_for returns
  None: no line-up, nothing paid. Tested (no_hook = every moment: no package, no clips-alone call).
- **glm P0-2 (the cache freezes a transient failure for the build):** KEPT. It is fail closed, and the L-v 2 audio
  window is cached on disk, so the read is deterministic.
- **glm P1-2 (angle["hook"] may name a moment that does not open):** REFUTED. angle["hook"] is read only by
  check_angles (it is one of the angle's moments), lineup_for's sort preference, and the report. The package's hook is
  always segments[0] (package.py:542 / 566 / 1050).
- **glm P1-3 (CUTTABLE vs edge_plan "not cuttable"):** KEPT. These are two different checks.
  - CUTTABLE is the second recogniser's sentence boundary.
  - edge_plan's "in" is the acoustic room before the first word.
  - A moment can be cuttable and still unable to open a medley; it stays usable as a non-hook clip.
- **glm P1-4 (the no-voice added clip):** KEPT. The hook is segments[0], which always comes from a line-up drawn from
  `cleared`. The added clip is never the hook.

## Found by the first FRESH ledger build (01:56 ET), fixed, and in cycle 2's scope

The first live ledger build with window records gave "0 moments cleared step A ... in 0 s" (ledger_20261113_065638).
Two defects:
1. **The step-A batch was poisoned.** One window moment without its caption record gave context text None. Its
   step-A batch call raised, and EVERY moment in the batch was marked unavailable.
   - prescreen now marks that moment alone (CONTEXT_UNAVAILABLE) and still sends the rest.
   - Test: test_a_moment_without_context_never_poisons_its_step_a_batch.
2. **8 of 16 window videos had no caption record in main's store.** Their caption records are in the store the
   ledger was MINED from (pp-ingest's data/editorial): 5 are absent from main, and 3 were re-fetched there under
   another sha.
   - caption_source now searches main's store, then the ledger's store (read-only; the record by the row's sha).
   - Matches with the same words are one record; same-sha matches with different words are ambiguous (no context).
   - Test: test_the_ledgers_own_record_is_found_and_differing_matches_are_ambiguous.

## Verification

- 11 offline suites, 233 tests OK. regression_test.sh: 26 PASS | 0 FAIL | 5 WARN.
- On real audio (pin #1's clips), the hook measures 20 ms: FAIL. The render measured 30 ms.
