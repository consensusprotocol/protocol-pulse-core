# REFERENCE — Pulse Check review video of 2026-11-12 (PBX "very pleased"; protected, order '20:30' (c))

PBX, after watching Telegram 67806 (16:9) / 67807 (9:16), relayed by the orchestrator at 20:30 ET, verbatim:
"the output was actually good. I was very pleased. You did a great job! The only thing that I need to comment is that
you added too much voiceover and though it wasn't terrible, it was too interruptive most of the time it wasn't
necessary at the very end, it was appreciated. We keep it that we only have one input at the end unless you deem it
necessary to stick together other content, but honestly, all that content work together beautifully as a medley
without my voice."

This is the third protected reference, after the frozen v2f (references/v2f_2026-11-06, Law 22) and the approved
preview (references/pulse_preview_2026-11-11, law L-d).

## What it is a reference for
- YES: clip choice (three channels whose moments work "together beautifully as a medley"), the cuts, the 16:9 and 9:16
  layout (including clip_02's two-speaker stack), and the closing line (the takeaway PBX appreciated: "No ruler. Just
  rules nobody gets to bend. That's the idea, and it's the part most people still miss when they look at Bitcoin.").
- NO: the amount of voiceover. Its intro and its bridge after clip 1 are what PBX called too much and too interruptive.
  Law L-y VOICEOVER IS MINIMAL (same order) sets the shape from now on: hook -> clip -> clip (-> clip) back to back,
  one takeaway line at the end, the sign-off. Checked by edl_rules R11: this video's own EDL fails it (an intro; a
  bridge between clips with no recorded reason), and the same package without those two lines passes
  (test_edl_rules TestR11VoShape).

## Where it is
- Files: `references/pulse_moments_2026-11-12/` (read-only; `SHA256SUMS` lists all 225 files):
  `out/segment.mp4` (16:9, sha256 5fb53826...) and `out/segment_vertical.mp4` (9:16, sha256 1b864cd8...), exactly the
  bytes sent; `PIN.json` (data/moments_pins/MOMENTS_PIN_115548.json, sealed package 37c5b5f5); `PINNED_DECISION.json`;
  `edl.json` (selection locks, the adjudicated lock of clip_01 with its two attested readings); `cuts_final.json`,
  `CUT_ACCEPTANCE.json`, `SENTENCE_LAW.json`, `CLIP_CONTRACT.json`; `VERTICAL_LAYOUT.json`, `vertical_overrides.json`,
  `TRANSITIONS.json`; `GATE_REPORT.json`, `ATTESTATION.json`, `REPORT.md`, `VERDICT.txt` (HOLD), `status.json`,
  `PROVENANCE.json`, `run_log.txt`, both render logs; `EDITORIAL_REVIEW.json` / `EDITORIAL_GATE.json` /
  `STORYBOARD.md`; `REVIEW_DROP.json` (the Telegram drop record, message ids 67806-67808); `qa/` (the prepared clips,
  concat and G14 manifests, contact sheets); `vo_audio/` (the four VO stems and VO_MANIFEST.json); `sources/` +
  `transcripts/` (the acquired windows); `VERIFY/` (joins, credits, contact sheets, vision answers);
  `PBX_VERDICT.md` (his words and this scope).
- Run: runs/pinned_20261112_165629, code 59068f44 (pipeline tree clean at launch), rendered 11:56-13:10 ET on Nov 12.
- Tag: `ref-pulse-moments-2026-11-12` (annotated, with PBX's verdict).

## Status when sent
REVIEW ONLY - NOT A PASS (telegram.review_drop, law L-j (a)): three REQUIRED rows were not PASS and were named with
their measured reasons: G3c_acoustic_tail (clip_02's tail under the music bed), G18_word_for_word (the final's decode
omitted clip_01's soft aside "it's not, you know,"), V1_visual_checklist 9:16 (the two vision models split on clip_02's
stack). Rulings 21, 22 and 23 (a), merged after the send, address each.

## Protection
`pipeline/regression.sh` step 7 runs `pipeline/check_reference_manifest.py`: every listed file present with its listed
sha256 and no unlisted file (exit 1 = changed / missing / added, 2 = not on this machine). Tests:
`pipeline/test_check_reference_manifest.py` (a changed byte, a missing file, an added file, a bad or empty manifest
fail; the untouched copy and the real reference pass).
