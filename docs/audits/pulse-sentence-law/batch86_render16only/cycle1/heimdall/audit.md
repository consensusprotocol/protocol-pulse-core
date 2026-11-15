# Heimdall audit

**Question:** Batch 86 = RULING 93 AS AMENDED, the render side (orchestrator 2026-11-14 '21:10', relayed by the builder, in substance): "a clip whose source-burned captions the 9:16 crop cuts mid-word is 16:9-ONLY (sealed formats: ['16x9']); the integrator renders and delivers that format alone". Batch 85 (merged c396c3c8) made the RELEASE follow the sealed formats: release_auth.release_formats(edl) (exactly ('16x9',) or ('16x9','9x16'), absent = both, anything else ValueError) decides, binds and authorises those formats only; run_fresh.stage_pinned copies the pin's sealed moments_package["formats"] into edl.json; telegram's release and review drops send those formats only. Until this change a 16:9-only run still rendered and gated its 9:16 (never deciding, never sent).
The change (this diff): run_fresh.run_formats(run_dir) = release_formats of the EDL, unreadable -> Hold. stage_render: shoutout per sealed format; the 9:16 render, its log, postflight, loudness mux and the vertical fallback probe only when '9x16' is sealed (final9 = man9 = None otherwise); loudness.correct_finals(final16, final9=None) corrects and re-measures the 16:9 alone when final9 is None (no mux, no md5 pairing; _replace_pair of one pair). stage_gates: formats = run_formats; ("9x16" in formats) != bool(final9 and man9) -> Hold; every 9:16 measurement (run_gates, G11, G14 audio offset, G14_frame_similarity, G14c, G15, G20, G17 output, vertical_silent_fallback) only when final9; every per-format loop through each(...) = the sealed formats, in order; rows / notes / evidence / flags / limits keyed by the sealed formats; GATE_REPORT records 'formats'. run_tail's replay (start after render) passes final9 = man9 = None for a 16:9-only run. verify_pack.build: joins, credits, contact sheets and the V1 checklist for the sealed formats only; pack 'complete' / 'passed' over them (release_auth.verification_ok, unchanged, reads 'complete' and 'vision'). write_report: a gates table per format present. pulse_check_run.sh delivers when out/segment.mp4 exists (release_auth.authorise, unchanged, refuses when any SEALED format's final is missing or changed; the script's else branch, unchanged, exits 70 "NOT delivered" when no final exists).
Unchanged guards (not in the diff): release_auth.blockers per format and the inventory (release_auth.py:111); attest/authorise bind and check exactly bound(release_formats) (batch 85); run_fresh.release_verdict decides on release_formats (batch 85); stage_layout (vertical_layout.classify) still runs for every run: G4s_layout_truth and G4 per shot on the 16:9 read its plans.
Tests: test_render16only (stubs at every renderer and gate seam, recording the final each was given): a 16:9-only run renders the 16:9 alone (no 9:16 shoutout, render, postflight, mux), gates it alone (no 9:16 final reaches any gate, no G11 / G14c, rows and measured files 16:9 only), its pack is complete on the 16:9 alone; unreadable formats Hold before anything renders; finals that do not match the sealed formats Hold. MUST-FAIL mirrors: with no sealed formats the same stubs see both formats rendered and gated (G11, G14c, vertical_silent_fallback present) and the pack needs the 9:16. test_loudness ruling_93: the 16:9 alone is corrected; an off-target re-measure keeps it. On the old code (c396c3c8, a full checkout) the 6 new-behaviour tests fail and the 3 mirrors pass.
FIND: a 16:9-only run that still renders, measures or reads a 9:16 anywhere; a both-format run whose behaviour, row set, row order or files changed; a 9:16 row, file or verdict that can be missing from a both-format run without a Hold; a sealed-format mismatch (EDL vs the finals handed to the gates) that does not Hold; a 16:9-only pack marked complete without its 16:9 parts; the loudness path promoting an uncorrected or off-target 16:9. Only state what you can verify from the diff. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0033
## Consensus findings (majority of panel agrees)
- **[low] pipeline/run_fresh.py:1047** stage_gates re-reads edl.json via run_formats, so a 16:9-only run whose EDL changed between render and gates raises Hold (correct) — but the render stage's formats and the gates' formats are read independently; if the EDL is edited between stages the mismatch is caught only by the ('9x16' in formats) != bool(final9 and man9) check, which cannot detect a 16x9→both flip (both sides then truthy, gates silently proceed with a stale final9=None... actually final9 would be None and '9x16' in formats True → Hold fires). No defect found; noted as verified-consistent.
  - evidence: `formats = run_formats(run.dir)  # ruling 93 as amended: the rendered (sealed) formats are gated
if ("9x16" in formats) != bool(final9 and man9):`
  - fix: none
  - raised by glm:F1; agree: qwen27b, glm
- **[low] pipeline/verify_pack.py:1614** verify_pack.run_formats raises OSError/ValueError uncaught (unlike run_fresh.run_formats which wraps in Hold); a 16:9-only run whose EDL is unreadable at pack time fails the stage with a raw traceback rather than a Hold verdict — behaviour, not a defect in the ruling's scope.
  - evidence: `with open(os.path.join(run_dir, "edl.json")) as f:
        return release_auth.release_formats(json.load(f))`
  - fix: none
  - raised by glm:F2; agree: qwen27b, glm
- **[low] pipeline/run_fresh.py:1614** run_tail's replay: when '9x16' not in run_formats, final9=man9=None, but the earlier branch (start='render') may have already produced a 9:16 on disk from a previous both-format run; the gates then Hold via the formats-vs-finals check — consistent, no defect.
  - evidence: `if "9x16" not in run_formats(run.dir):       # a 16:9-only run's replay gates the 16:9 alone
            final9 = man9 = None`
  - fix: none
  - raised by glm:F3; agree: qwen27b, glm

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
