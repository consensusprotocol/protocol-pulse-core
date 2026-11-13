# Heimdall audit

**Question:** Batch 53 = RULING 29 (orchestrator 2026-11-13 '01:55'), verbatim: "G5 -15.2 LUFS against -14 +- 1: a render defect. The final mix must be measured and corrected to target before the gates (two-pass loudness on the final, then re-measure). The gate stays."
Measured: pin #1's 16:9 final reads input_i -15.22 LUFS and input_tp -3.29 dBTP (loudnorm pass 1). G5 is ebur128 I = -14 +- 1 and TP <= -2.0. The 9:16 carries the 16:9's mixed audio, identical by construction (Law 23).
New pipeline/loudness.correct_finals(final16, final9), called at the end of run_fresh.stage_render after both postflight checks, before the gates:
- pass 1: ffmpeg loudnorm print_format=json measures the 16:9.
- Within TOL_LU = 0.5 of -14 with TP <= -2.0: nothing is rewritten.
- Otherwise pass 2: loudnorm with the measured values, linear=true, on the 16:9 audio only (video stream copied; AAC 192k / 48 kHz / stereo). The normalization type ffmpeg reports is recorded.
- The 9:16 gets exactly that corrected audio stream, muxed over its own copied video.
- Both are re-measured. They replace the finals (os.replace) only when both are within TOL_LU and TP <= -2.0. Otherwise the rendered finals are kept and the reason recorded; temp files are always removed.
- The record goes to PROVENANCE["loudness"]. G5 is unchanged.
Tests (synthetic finals, 5):
- a quiet pair is corrected: video streams untouched, the 9:16 audio identical to the 16:9's, both on target;
- an in-tolerance pair is never rewritten;
- a failing mux or an off-target re-measure keeps the finals byte-identical;
- an unmeasurable file raises.
FIND:
- AV sync or duration changes from the audio re-encode (AAC priming, edit lists);
- a TP above -2.0 after correction that still replaces the finals;
- the 9:16 audio not identical to the 16:9 after the change;
- a failure path that leaves a half-written final;
- a measurement whose numbers can be misread (the regex on ffmpeg's output);
- whether this can mask a real mix defect the gate should see (the gate still measures the corrected files);
- tests that do not test what they claim.
Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0187
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- glm:F1 [high] Pass-2 loudnorm re-encodes audio without -shortest; if the 16:9 audio stream is longer than the video (common with AAC priming/padding), the corrected final's duration grows, breaking A/V sync at the tail and the 9:16 mux inherits it (agree: 1)
- glm:F2 [medium] The regex only matches a JSON object containing input_i; if ffmpeg's stderr contains another JSON blob first (e.g. from a prior -af or banner), the wrong blob is parsed; also normalization_type is returned as a string while all other keys are floats, so callers comparing it numerically will fail (agree: 1)
- glm:F3 [medium] test_a_pair_within_tolerance_is_never_rewritten does not test what it claims: it calls correct_finals twice on the SAME pair, so the second call's 'none: within tolerance' only proves the first call's correction worked, not that an in-tolerance pair is skipped; the fixture never produces a genuinely in-tolerance (between -14.5 and -13.5) but uncorrected pair (agree: 1)

## Added in cross-examination (not voted on)
- none
