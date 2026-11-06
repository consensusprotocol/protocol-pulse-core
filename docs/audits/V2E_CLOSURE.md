# V2E CLOSURE TABLE

Status: IN PROGRESS
Last updated: 2026-11-06

## Key
- **confirmed**: independently verified defect
- **fixed**: fix committed and tested
- **suspected**: reported but not independently verified
- **disputed**: conflicting evidence
- **reference-dependent**: requires PBX-approved reference to classify
- **HOLD**: PBX decides after comparing with v12/v17 reference

---

## Merged Findings

### V01 / Grok-1 / P1+P2+P4+P5: 16:9 TIMELINE (picture behind audio 14-31s)

| Field | Value |
|---|---|
| **Status** | fixed |
| **Cause** | Shared `shoutout_frames_raw/` dir caused frame contamination (S2); concat demuxer drift from 22050→48000 Hz VO resampling mismatch (A2/R2-06); no canonical timeline enforcement. Confidence: HIGH |
| **Commit** | 40536aa1 (A2 resample), 13b3319a (S2 isolated dirs + G14/G15 gates) |
| **Test** | `test_g14_g15.py::test_v2e_16x9_must_fail_g14` — v2e FAILS with 3500ms scene offset at clip_01 boundary. `test_current_16x9_passes_g14` — current PASSES within 22ms |
| **Result** | Current 16:9 scene changes: 14.0, 28.375, 40.5, 54.333 match manifest within 42ms. v2e had 17.5, 31.125 (3.5s late) |
| **Evidence** | `ffmpeg scene detect on segment_v2e.mp4 vs segment.mp4` |

Subfindings:
- P1 (hook held 14-17): FIXED — scene change now at 14.0 (manifest: 14.022)
- P2 (BMTV freeze/lip sync 17-19): FIXED — clip_01 now starts synced at 14.0
- P4 (bridge stays on BMTV 24-28): FIXED — bridge now at correct position
- P5 (Bitcoin Layer audio over BMTV 28-31): FIXED — clip_02 scene at 28.375 (manifest: 28.367)

### V02 / P6 / P6b: SHOUT-OUT TWICE / SQUISHED CARD

| Field | Value |
|---|---|
| **Status** | fixed |
| **Cause** | `scene_shoutout.py:234` uses shared `shoutout_frames_raw/` dir. When 9:16 renders more frames (233) than 16:9 (214), leftover frames from 9:16 are encoded into 16:9 output, inserting a vertical card at frames 215-231. Confidence: HIGH |
| **Commit** | 13b3319a (S2 aspect-isolated build dirs + G15 gate) |
| **Test** | `test_g14_g15.py::test_v2e_16x9_must_fail_g15` — v2e FAILS (mid-card scene change detected). `test_current_16x9_passes_g15` — current PASSES |
| **Result** | v2e has 17 frames of squished 9:16 card (ring 494x156 px = aspect 0.32). Current render: continuous card, rings within 0.95-1.05 |
| **Evidence** | `shoutout_frames_raw/` had 233 files but only 214 scheduled for 16:9 |

P6b (9:16 card replay): Same root cause. 9:16 directory had extra frames from prior render, causing the card to appear extended. Fixed by isolated build dirs.

### P3 / Grok "magnitude": WORD COMPLETION AT 24s

| Field | Value |
|---|---|
| **Status** | confirmed: word is complete |
| **Cause** | PBX perceived the word as chopped due to 3.5s video lag in v2e. The picture showed an earlier frame at the word's ending, creating perceptual mismatch. The audio samples are present. Confidence: HIGH |
| **Commit** | A1 (741fb72b) fixed cut_out to 249.37 (valley end). S1 (13b3319a) fixed the video sync. |
| **Test** | S3 whisper analysis: source last 0.5s → "magnetism." (whisper substitution); output last 0.5s → "magnitude." (complete). RMS: -19.6 dBFS before cut, -19.4 dBFS after (clean valley). |
| **Result** | Word "magnitude" is acoustically complete. Valley: 19.2 dB deep, 40ms wide at 249.35-249.37, onset at 249.42. Cut at 249.37 lands cleanly in the valley. |
| **Evidence** | `qa_v1/s3_src_last500ms.wav`, `qa_v1/s3_output_last500ms.wav` |

### V03 / ChatGPT: Evidence packet mixing v2f metadata into v2e

| Field | Value |
|---|---|
| **Status** | open (E1 in order) |
| **Cause** | `blind_review.py` read mutable working files instead of immutable run dir. |
| **Commit** | TBD |
| **Test** | TBD |

### V04 / ChatGPT: Contact sheet frame timing ~0.458s early

| Field | Value |
|---|---|
| **Status** | open (E2 in order) |
| **Cause** | Frame selection uses time-based seek instead of frame index with true PTS. |
| **Commit** | TBD |
| **Test** | TBD |

### Grok-2 / clip_02 9:16: garbled word at 28.0s

| Field | Value |
|---|---|
| **Status** | open (S4 in order) |
| **Cause** | cut_in 624.63 clips "There's only" — needs sentence-start rule. |
| **Commit** | TBD |
| **Test** | TBD |

### Grok-3 / 51s silence gap: audible gap before sign-off

| Field | Value |
|---|---|
| **Status** | open |
| **Cause** | Missing crossfade or VO timing gap between clip_03 out and sign-off VO. |
| **Commit** | TBD |
| **Test** | TBD |

### Grok clip_03 in-point: first_word "pris" (fragment)

| Field | Value |
|---|---|
| **Status** | open (S4 in order) |
| **Cause** | cut_in 998.0 vs word_start 997.3 — misses the article "a". EDL first_word="pris" indicates mid-word entry. |
| **Commit** | TBD |
| **Test** | TBD |

### S5: 9:16 face safety at 53.0s

| Field | Value |
|---|---|
| **Status** | open |
| **Cause** | Face-centred crop cuts through guest's glasses. |
| **Commit** | TBD |
| **Test** | TBD |

### S6: 9:16 screen-share (clip_02)

| Field | Value |
|---|---|
| **Status** | open |
| **Cause** | Dual-face layout with black band in vertical crop. |
| **Commit** | TBD |
| **Test** | TBD |

### S7: 9:16 bridge plate

| Field | Value |
|---|---|
| **Status** | open |
| **Cause** | Bridge at 24.33-28.04 is letterboxed 16:9 slit instead of full-bleed blur. |
| **Commit** | TBD |
| **Test** | TBD |

### S8: VO grounding (M20)

| Field | Value |
|---|---|
| **Status** | open |
| **Cause** | VO claims more certainty than clips establish ("prove", categorical claims). |
| **Commit** | TBD |
| **Test** | TBD |

## HOLD items (PBX decides)
- Outro glitch/flare and dark silent tail (66.5-67.6)
- 9:16 outro as 16:9 band in black
- Shout-out card art and entrance (~0.29s dark at 54.0)
- Sign-off wording
