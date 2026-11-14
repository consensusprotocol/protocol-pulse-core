# Heimdall audit

**Question:** Batch 53 cycle 2 (verification). Cycle 1: no consensus; single votes checked on pin #1's REAL finals (durations / frames / AV sync unchanged); a real defect found by that run and fixed (AAC overshoot: pass 2 aims TP -2.5; result -14.13 LUFS / -2.31 dBTP, dynamic); tests rewritten (see CONSENSUS.md).

Batch 53 = RULING 29 (orchestrator 2026-11-13 '01:55'), verbatim: "G5 -15.2 LUFS against -14 +- 1: a render defect. The final mix must be measured and corrected to target before the gates (two-pass loudness on the final, then re-measure). The gate stays."
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
FIND: anything still open; a corrected file that can fail G5; a replaced final that was not re-measured; the 9:16 audio differing; a test that does not test what it claims. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0050
## Consensus findings (majority of panel agrees)
- **[high] pipeline/test_loudness.py:82** test_the_correction_keeps_every_frame_count_and_duration crashes with ValueError: int(n) is called on the duration field (e.g. '12.000000'), which is not a valid integer literal. The test does not test what it claims; it fails before calling correct_finals.
  - evidence: `return {t: (int(n), float(d)) for t, d, n in (l.split(",") for l in out.split())}`
  - fix: Swap the conversion: use float(n) for duration and int(d) for nb_frames, i.e. {t: (int(d), float(n)) for t, d, n in ...}.
  - raised by qwen27b:F1; agree: qwen27b, glm
- **[medium] pipeline/loudness.py:62** The 9:16's audio is not verified to be the 16:9's corrected audio before replacement; only its loudness is checked. A mux that silently substitutes/decays audio (e.g. wrong stream mapped, or a container/codec quirk) would still pass the TP/I check and be promoted, violating Law 23 while the record says 'corrected'.
  - evidence: `a9 = measure(t9); bad = [f"{n} {a['input_i']} LUFS / {a['input_tp']} dBTP" for n, a in (("16x9", a16), ("9x16", a9)) if abs(a["input_i"] - TARGET_I) > TOL_LU or a["input_tp"] > TARGET_TP]; if bad: ...`
  - fix: Before os.replace, compare the two temp files' audio streams (e.g. framemd5 of 0:a, as the test does) and record/keep-on-mismatch.
  - raised by glm:F1; agree: qwen27b, glm

## Raised but not agreed
- qwen27b:F2 [high] os.replace can raise OSError (e.g. PermissionError, FileNotFoundError), which is not caught by 'except RuntimeError'. If the first os.replace succeeds and the second raises, final16 is replaced with the corrected file while final9 retains the original, leaving an inconsistent pair; the uncaught OSError also crashes the pipeline in run_fresh.stage_render. (agree: 1)
- glm:F2 [low] Pass-2 success is gated only on returncode and dst existence; the normalization_type JSON is parsed unconditionally afterwards, so a pass 2 that succeeds but prints no JSON yields None silently (recorded, but the 'linear' guarantee of ruling 29 is not enforced — a dynamic normalization can change duration/frames, which the gates then see). (agree: 1)
- glm:F3 [low] The off-target re-measure test's fake() also rewrites input_i for the 16:9's pass-1 measurement if the final happened to be named '*.loud.mp4'; more importantly it does not assert the temp files were cleaned up (unlike the mux-failure test), so a leftover .loud.mp4 would go unnoticed. (agree: 1)

## Added in cross-examination (not voted on)
- glm: [medium] Pass-1 tolerance check uses before['input_tp'] <= TARGET_TP, but pass 2 targets TP-0.5 (CODEC_TP_MARGIN) and the re-measure gate compares against TARGET_TP; a final measuring exactly in tolerance (e.g. -14.3 LUFS / -1.9 dBTP) is left uncorrected with TP above the -2.0 gate... wait, -1.9 <= -2.0 is false, so it IS corrected — the real gap is the reverse: a final at -14.4/-2.0 passes pass 1, but the gate G5 allows TP <= -2.0 inclusive, so this is consistent. Actually the genuine miss: the 'none: within tolerance' path never re-measures the 9:16, so if the 9:16's copied audio differs (e.g. prior mux drift), it is promoted unchecked.
