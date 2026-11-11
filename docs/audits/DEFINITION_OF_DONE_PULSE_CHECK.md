# DEFINITION OF DONE — PULSE CHECK (living document, started 2026-11-11 02:52 ET)

Every PBX rule mapped to the check that enforces it and the must-fail test that proves the check
works. A rule with no check is listed as **UNENFORCED** (in red), never left out. Updated as the work
lands; the commit that changes a row is named in it.

Legend: G = gate (runs in run_fresh.stage_gates / pre-render stage), T = must-fail test file.

## OPEN DECISIONS FOR THE ORCHESTRATOR (evidence; work continues meanwhile)

**OD-1 G12/G15 misfire on correct credit cards (DEC-7).** With the render fixed (real square
avatars from the registry; rings measured 0.999), the UNCHANGED gates still fail the rebuilt Nov 10
card: 16:9 G12 counts 5 "circles" — the extra ones sit on Natalie Brunell's real avatar's ORANGE
background (G12's red mask R>100, R>G+40, R>B+40 includes orange); 9:16 G15 fits a 0.457 ellipse at
(481, 1076) = the middle channel's NAME LABEL text, not a ring. Yesterday's 9:16 G15 failure was the
same label contour. So G12/G15 are content-sensitive; a story crediting such a channel cannot pass
them unchanged. Not changed (mission 1e, DEC-7, M2). If re-specified, the rings-only measurement
would no longer see warped avatar CONTENT, so D4 is now guarded deterministically before render
(shoutout.validate_avatar: square + registry sha prefix; tests in pipeline/test_pulse_20261110_mustfail.py).
Evidence: scratch renders of the rebuilt card, g12_circles overlay (circles on the orange background).

**OD-2 G16/G17 not calibrated to v2f (DEC-1 applied to G3c/G5/G8/G9 only).** v2f predates the
sentence law and fails it on all four segments (table below). Calibrating would set lead/tail to 0 ms
and admit mid-sentence starts, i.e. re-admit D1-D3; PBX's own v2f record calls clip_01's out edge a
ONE-TIME exception with "the 60 ms rule unchanged". New renders must meet the law; v2f stays the
approved legacy reference for everything else.

**OD-3 Prepare-stage picture fidelity is ungated (late Heimdall finding on DEC-1, measured).** G8
compares the final against the PREPARED clip (its pre-DEC-1 approved "relative reference"), so it
measures the render stage only. Measured at G8's own sample instants: on the approved v2f, prepare
(lanczos to 1920x1080, NVENC QP 20) keeps only 0.696 (clip_02) / 0.760 (hook) of the original
download's Laplacian variance (largely grain removal); Nov 10 keeps 0.985-1.040. With the original
download as G8's source the APPROVED reference would fail the unchanged 0.85 ratio (0.689 / 0.770), so
that wiring would need a ratio calibration (an acceptance change) — not taken. Decision for the
orchestrator: gate prepare fidelity (and against what), or accept it as part of the approved look.
Evidence: docs/audits/pulse-sentence-law/dec1_calibration/HEIMDALL_RUN_FRESH_RESPONSE.md.

## 1f — the gate suite on the frozen v2f reference (2026-11-11, scratch copy, production stage_gates)

| gate | format | v2f measured | threshold | approved video shows the defect, or gate stricter than approved? |
|---|---|---|---|---|
| G3c acoustic tail | both | hook: tail rise to −31.4 dB vs speech −21.7 dB → "onset"; passes at depth ≤ 11.63 dB (16:9) / 11.65 dB (9:16) | valley ≤ speech−12 dB, no sustained rise | stricter than approved (REFERENCE_v2f: output fades to −87 dB at 9.52, next word 9.60) → DEC-1 |
| G5 true peak | 9:16 | −1.3 dBFS | ≤ −2.0 | stricter (REFERENCE: "9:16 peak −1.3 dB, approved as reviewed") → DEC-1 |
| G8 sharpness floor | 16:9 / 9:16 | worst segment medians 27.56 (hook) / 10.84 (clip_03) | ≥ 60 | stricter (soft source cameras, approved) → DEC-1 |
| G9 tail luma | 16:9 / 9:16 | 14.3357 / 14.7715 | > 20 | stricter (locked PBX outro ends on black, approved) → DEC-1 |
| G16 sentence boundary | both | hook lead 40 ms genuine, no pad; clip_01 in 238.55 is 80 ms after the pause before 'The', out has no ≥80 ms pause before 'So'; clip_02 no pause before 'One'; clip_03 starts mid-sentence ('of \| a prison'), out 20 ms after 'have.' | sentence law (2026-11-11) | approved video SHOWS the defects the new law prohibits → not calibrated (OD-2) |
| G17a onset/tail | — | leads 40/40/0/190 ms, tails 150/40/190/0 ms | ≥ 80 ms | same → not calibrated (OD-2) |
| G17b edge words | both | PASS (render faithful) | ≥ 85 % | — |
| G1-G2, G3, G3b, G4, G6, G10-G15 | both | PASS | unchanged | — |

## Rule → check → proof

| PBX rule | Enforcing check (code) | Must-fail proof | State |
|---|---|---|---|
| Clip starts on the first word of a sentence | G16 SENTENCE_BOUNDARY IN edge (pipeline/sentence_law.py gate_g16, pre-render stage `sentence_law` + final gate row) | T pulse_20261110: D3a clip_01 '81', D3b clip_02 'days' | landing (1b/1c) |
| Clip ends on the last word of a sentence | G16 OUT edge | T pulse_20261110: D2 clip_01 runs into "All right…" | landing (1b/1c) |
| Expected words fixed at selection, never recomputed | G16 selection-lock check (sha-sealed lock in edl.json vs cuts_final expected words) | T pulse_20261110: TestTautology | landing (1b/1c) |
| A cut never adds/drops a word; snapping only inside the gap | sentence_law.write_lock_cut_table (cuts placed only in the locked pauses ∩ unchanged cut_accept); ±2 s snap + recompute removed | T: test_run_fresh_has_no_recompute_sync_or_wide_snap | landing (1b/1c) |
| No clipped onsets (≥ 80 ms genuine lead-in) | G17a on prepared clips; G16 file-head pad rule | T pulse_20261110: D1 hook (60 ms genuine lead-in) | landing (1b/1c) |
| No clipped tails (≥ 80 ms genuine tail) | G17a tail | T: D3c control (clean tail passes) | landing (1b/1c) |
| Edge words keep ≥ 85 % in the render | G17b on both finals | T: TestG17bRenderedEdges (muted onset fails, 20 ms fade passes) | landing (1b/1c) |
| Round credit avatars of the channels actually used | G12 (count), G15 (ring aspect, continuity), R6 (credits == EDL channels, unique avatar hashes), shoutout.validate_avatar + registry-only avatars | T: TestD4Credits (yesterday's card fails G12/G15; thumbnail refused; v2f passes) | landing (1e) |
| On-brand transitions between channels only | — | — | **UNENFORCED** (Phase 3) |
| Speaker-centred vertical; safe frame only for screen / unidentifiable speaker, flagged | — | — | **UNENFORCED** (Phase 2) |
| Sparse VO with 1 s lead-in | G6 pre-roll (onset ≥ 0.95 s), R4 VO ≤ 25 %, M20 editorial gate | existing tests (test_round2_mustfail, test_editorial_gate) | enforced (pre-existing) |
| No brand sting at the open | — | — | **UNENFORCED** (Phase 3) |
| 1080p (1920x1080 / 1080x1920) | G5 tech (dims, SAR, fps), clip_contract | test_round2_mustfail G5 | enforced (pre-existing) |
| Transcript of the final == intended sentences, word for word | — | — | **UNENFORCED** (Phase 4a, G18) |

## Findings recorded so far (evidence, 2026-11-11)

- D3's third edge (clip_02 out 34.36) is **not** a defect: pause 34.08-34.43 (75 dB deep), the 'I' onset
  is at 34.44; whisper on the prepared clip ends "...many times." The transcript word 'i' 33.92-34.46 is
  a whisper timestamp error. 4 of 6 edges broke the sentence law, not 5.
- D1 is a **source lead-in** problem, not the render: the 'B' onset sits at 85-90 ms in every stage,
  level-identical to the source; the source has 33 ms of codec zero then ~50 ms of room tone.
- D2/D3 root causes: (1) `_download_window` requested `*54-100` but recorded offset 53.57 (and 23 vs
  23.38): every canonical->file time was shifted 0.38-0.52 s; (2) `_find_word_boundaries` picked the
  nearest word, not a sentence start; (3) the ±2 s snap + edge-word recompute (ad7295ea/4cf5a31a)
  validated whatever the moved cut contained; (4) R9/R10 never ran in production (validate_edl was
  called without transcripts; R10 is advisory and always returns True).
- D4 root cause: shoutout._fetch_avatar_on_demand fell back to the 1280x720 VIDEO thumbnail; the frozen
  renderer resizes every avatar to a square. G12/G15 caught it; the QA_GATE_HOLD reclassification was
  wrong. 70 of 75 registry channels had no verified avatar.
- cut_accept (unchanged) uses a fixed speech-25 dB quiet line: on music-bedded sources (DataDash, bed
  ~24 dB under speech) it reads the bed as speech, so the Nov 10 hook's out edge can satisfy either the
  80 ms tail rule or cut_accept, never both -> that window is rejected (fail closed), not forced.

## Decisions (orchestrator, delegated by PBX 2026-11-11)

Received 02:50 ET. Recorded verbatim in substance; implementation status tracked above and below.

- **DEC-1 Reference calibration.** PBX's approved v2f (16:9 and 9:16) is by definition passing (Law 22).
  For any gate the frozen v2f reference outputs FAIL today: show measured vs threshold on the reference,
  then set that gate's threshold to exactly the reference's measured worst value (no extra margin), in a
  named constant citing the reference file and measurement, plus a test asserting the reference passes
  and a must-fail fixture just beyond it. The ONLY permitted change to gate acceptance; only for gates
  the approved reference fails; audited. Each calibrated gate, old and new value, listed here.
- **DEC-2 Screen-share hooks allowed.** Deterministic layout class "screen" (largest detected face under
  a fixed fraction of frame area across samples, or no face), recorded in the EDL. G4 as written for
  talking-head layouts; for "screen": content is the shared screen, vertical uses the wide safe frame,
  caption/EDL say layout=screen. Must-fail test: a talking-head clip mislabelled as screen.
- **DEC-3 Soft cameras.** Covered by DEC-1 if the reference is equally soft; otherwise prefer the sharper
  window when two legal windows score within 0.5; do not reject a clip for source softness alone when
  render/source sharpness ratio >= 0.85.
- **DEC-4 Transition default.** Sentence-aligned cuts with a 6-frame cross-dissolve and matching audio
  crossfade between segments from different channels (variant B without the thump). Still build A, B
  (soft pulse) and C (red pulse-line wipe) once on the corrected Nov 10 cut; send the three to Telegram
  labelled as options; do not block on the answer.
- **DEC-5 Vertical.** Speaker-centred reframe default; stacked bands for 2-3 person layouts; safe frame
  only for layout=screen or when the speaker cannot be identified, flagged in EDL and caption.
- **DEC-6 Sources.** Approved partner channels only (the pipeline/channels.json registry). No guest
  sources until the radar exists.
- **DEC-7 Credits rings.** The gate was right; fix the render.
- **DEC-8 Done means:** (a) the corrected Nov 10 story passes every gate with no waiver and its transcript
  diff is exact; (b) THREE fresh stories in a row via one command (run_fresh.py, auto mode, no pinned
  file, no hand step) at one identical git HEAD, each passing every gate, each delivered to Telegram as
  "HOLD FOR APPROVAL - all gates passed, no waivers"; (c) docs/RUNBOOK_PULSE_CHECK.md; (d) a cron-ready
  wrapper scripts/pulse_check_run.sh (flock, logging, pipeline_ tmux-safe), NOT installed in cron. A HOLD
  for "no producible story" is valid only with a full rejection ledger; it neither counts nor resets. A
  HOLD from a pipeline defect: fix, audit, the count restarts.
- **DEC-9 Stories.** The engine's own top Bitcoin story each time, runs >= 3 hours apart or on different
  story universes so they are genuinely different stories.

### Calibrated gates (DEC-1)

| gate | constant (segment_v1/qa_gates.py) | old value | new value (= v2f measured worst, per format) | reference measurement | commit |
|---|---|---|---|---|---|
| G3c acoustic tail | G3C_VALLEY_DEPTH_DB | 12.0 dB | 16:9 11.63, 9:16 11.65 | strictest depth at which the v2f hook tail passes: 11.6301 / 11.6543 | DEC-1 commit |
| G5 true peak | G5_TRUE_PEAK_MAX_DBFS | -2.0 dBFS | 16:9 -2.0 (unchanged, passed at -2.2), 9:16 -1.3 | segment_vertical.mp4 ebur128 true peak -1.3 | DEC-1 commit |
| G8 sharpness floor | G8_SHARPNESS_FLOOR | 60 | 16:9 27.56, 9:16 10.84 | worst segment medians: 16:9 hook 27.56, 9:16 clip_03 10.84 | DEC-1 commit |
| G9 tail luma | G9_LUMA_FLOOR | 20 (strict >) | 16:9 14.33, 9:16 14.77 (strict > kept) | 14.3357 / 14.7715 (locked outro ends on black) | DEC-1 commit |

Also in the DEC-1 commit (measurement wiring, not acceptance): G8 was never given source clips in
production, so it ALWAYS failed "no_source" and was waived as FLAG. It now gets the prepared clips
(16:9) and the reframed vertical clips (9:16) - the reference then fails only the floor, which is what
was calibrated. DEC-3 (soft source judged by render/source ratio >= 0.85 alone) is inside gate_g8.
The G8 FLAG and the G9 "approved known exception" rows are gone (DEC-8: no waivers).
