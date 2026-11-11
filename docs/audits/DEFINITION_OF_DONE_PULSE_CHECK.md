# DEFINITION OF DONE — PULSE CHECK (living document, started 2026-11-11 02:52 ET)

Every PBX rule mapped to the check that enforces it and the must-fail test that proves the check
works. A rule with no check is listed as **UNENFORCED** (in red), never left out. Updated as the work
lands; the commit that changes a row is named in it.

Legend: G = gate (runs in run_fresh.stage_gates / pre-render stage), T = must-fail test file.

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

| gate | constant | old value | new value (= v2f measured worst) | reference measurement | commit |
|---|---|---|---|---|---|
| (pending 1f measurement) | | | | | |
