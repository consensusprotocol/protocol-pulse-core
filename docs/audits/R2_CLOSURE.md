# R2 Closure Table

**Audit source:** `docs/audits/r2_chatgpt.md` (Round 2 ChatGPT audit, snapshot 7c3a4416)
**Must-fail baseline:** `docs/audits/mustfail_baseline.txt` (13/13 FAIL before fixes)
**Updated:** 2026-11-06

## Per-Finding Status

| ID | Status | Commit | Test Command | Result | Evidence |
|---|---|---|---|---|---|
| R2-01 | open | — | — | — | EDL-derived artifact resolver not yet implemented. render16.py/render_vertical.py still enumerate from cuts/manifest. |
| R2-02 | fixed | 53fb1499 | `pytest pipeline/test_round2_mustfail.py::TestVerticalGatesWired -v` | PASS | G11 wired in run_all_gates with horiz_mp4 param. G8/G9 already called. G12 called. |
| R2-03 | fixed | 53fb1499 | `pytest pipeline/test_round2_mustfail.py::TestCutWordChecks -v` | 3/3 PASS | G3: empty transcript rejected. G3b: prefix matching removed, short words checked. |
| R2-04 | open | — | — | — | G3c terminal burst false-pass. Relative threshold exists but edge cases remain. |
| R2-05 | fixed | 741fb72b, 53fb1499 | `pytest pipeline/test_edl_rules.py::TestAcousticValley -v` | PASS | M19a: 6 dB offset, 80ms gap boundary, FIRST valley >= 60ms, onset after valley, raise on unsafe. Test oracle corrected from 249.37 to [249.62, 249.72]. |
| R2-06 | fixed | 40536aa1 | `pytest pipeline/test_edl_rules.py::TestVOResample -v` | PASS | VO stems resampled to 48kHz stereo before concat. |
| R2-07 | fixed | 53fb1499 | `pytest pipeline/test_round2_mustfail.py::TestNoIntroDoesNotCrashG1 -v` | PASS | G1 handles missing intro — falls back to signoff or any VO stem. |
| R2-08 | open | — | — | — | Sign-off text drift between VO manifest and EDL. |
| R2-09 | open | — | — | — | Vertical independent source ranges and audio remix. A6 not yet implemented. |
| R2-10 | open | — | — | — | Publisher queued-as-posted race. Outside pipeline scope. |
| R2-11 | fixed | (this commit) | `pytest pipeline/test_edl_rules.py::TestOutputPathCollision -v` | PASS | `_resolve_output_names` raises RuntimeError if 16:9 and 9:16 names are identical. |
| R2-12 | fixed | 53fb1499 | `python3 -c "import segment_v1.tg_preview; print('import ok')"` | OK | tg_preview.py rewritten: import-safe, send_preview() function, __main__ guard. |
| R2-13 | fixed | 53fb1499 | `pytest pipeline/test_round2_mustfail.py::TestCutWordChecks::test_g1_negative_control_must_fail_gate -v` | PASS | G1: `if not neg_pass: all_pass = False`. |
| R2-14 | fixed | 53fb1499 | `pytest pipeline/test_round2_mustfail.py::TestDurationWindow -v` | 3/3 PASS | G5: 60-120s window for both aspects. 75s vertical cap removed. |
| R2-15 | open | — | — | — | G10 zero-frame pass, G12 missing shoutout pass. Partial: G12 wired but defective fixture not fixed. |
| R2-16 | fixed | (this commit) | `pytest pipeline/test_edl_rules.py::TestShoutoutHookChannel -v` | PASS | shoutout.py: hook channel extracted first, then clips. Dedup by seen set. |
| R2-17 | open | — | — | — | Registry integration: 75 entries, duplicate slugs, scanner skips. |
| R2-18 | open | — | — | — | Scanner/ranker contract mismatch. |
| R2-19 | open | — | — | — | Publisher factual-integrity (hard-coded $6.4B, unattributed claims). |
| R2-20 | open | — | — | — | YouTube channel ID guard (display title vs immutable ID). |
| R2-21 | fixed | 53fb1499 | `grep -c "\.partial" pipeline/acoustic.py` → 0 | PASS | apply_fades uses .tmp.mp4 suffix (explicit mp4 muxer). |
| R2-22 | fixed | 53fb1499 | `pytest pipeline/test_round2_mustfail.py::TestGateFailClears -v` | PASS | GATE_FAIL.txt removed on passing run. Variable named GATE_FAIL_PATH. |
| R2-23 | open | — | — | — | R6/R7/R8/R9 validation bypass details. |
| R2-24 | open | — | — | — | Test regression/selection blind spots. Partial: oracle corrected (249.37 → [249.62,249.72]). |

## Must-Fail Test Coverage

| Test | Bug | Baseline | After |
|---|---|---|---|
| test_vertical_hook_missing_raises | R2-09 fail-closed | FAIL | PASS |
| test_vertical_intro_missing_raises | R2-09 fail-closed | FAIL | PASS |
| test_vertical_bridge_missing_raises | R2-09 fail-closed | FAIL | PASS |
| test_vertical_shoutout_missing_raises | R2-09 fail-closed | FAIL | PASS |
| test_vertical_outro_missing_raises | R2-09 fail-closed | FAIL | PASS |
| test_gates9_calls_g8_g9_g11_g12 | R2-02 | FAIL | PASS |
| test_g3b_leaks_short_next_word | R2-03 | FAIL | PASS |
| test_g3b_prefix_must_not_match | R2-03 | FAIL | PASS |
| test_g3_empty_transcript_must_fail | R2-03 | FAIL | PASS |
| test_g1_negative_control_must_fail_gate | R2-13 | FAIL | PASS |
| test_gate_fail_cleared_on_pass | R2-22 | FAIL | PASS |
| test_102s_vertical_passes / test_50s_fails / test_130s_fails | R2-14 | FAIL | PASS |
| test_cut_is_after_the_syllable + test_real_clip + test_old_oracle | R2-05 | FAIL | PASS |

**Baseline:** 13/13 FAIL (docs/audits/mustfail_baseline.txt)
**After fixes:** 15/15 PASS (13 original + 2 G8 source-relative)

## Summary

- **Fixed:** R2-02, R2-03, R2-05, R2-06, R2-07, R2-11, R2-12, R2-13, R2-14, R2-16, R2-21, R2-22 (12 of 24)
- **Open:** R2-01, R2-04, R2-08, R2-09, R2-10, R2-15, R2-17, R2-18, R2-19, R2-20, R2-23, R2-24 (12 of 24)
- **A9 (G8 source-relative):** Implemented with DEGRADATION_RATIO=0.85. Policy proposal at docs/audits/G8_POLICY_PROPOSAL.md pending PBX approval.
