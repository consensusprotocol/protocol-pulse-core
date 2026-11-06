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

### Grok-2 / clip_02 in-point: "There's only" claim

| Field | Value |
|---|---|
| **Status** | HOLD (PBX editorial list) |
| **Cause** | Grok claimed "There's only" was clipped. Source-vs-output comparison (Amendment 1 S4): source at 624.0-626.0 = "or approximately one-third of market-". Output first 2.0s = "one third of marketable treasuries." Output starts cleanly at "one" — no truncated word. "There's only" is a whisper collapse, not present in source at this position. R10 flags as HOLD for PBX (sentence-start check), not auto-recut. Out-point "trillion." stays. |
| **Commit** | 0c277198 (acoustic cut_in + R10 as HOLD) |
| **Test** | Source whisper: "or approximately one-third of market-" (624.0-626.0), words: or@0.000, approximately@0.080, one@0.620, -third@1.020, of@1.300, market@1.560. Output whisper: "one third of marketable treasuries." (0.0-2.0), words: one@0.000, third@0.360, of@0.680, marketable@0.940, treasuries.@1.460. No truncation proven. cut_in/cut_out unchanged by 0c277198 (Amendment 2 6g confirmed). |

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
| **Status** | HOLD (PBX editorial list) |
| **Cause** | EDL first_word="pris" metadata was inaccurate. Source-vs-output comparison (Amendment 1 S4): source 996.5-999.5 = "built themselves a prison of". "a" at abs 997.6, "prison" at abs 998.26. Output first 2.0s = "a prison of a currency" — starts cleanly at "a", full word present. No truncation of "prison" proven. The antecedent "they" issue goes to PBX's editorial list. R10 flags as HOLD. |
| **Commit** | 0c277198 (acoustic cut_in + R10 as HOLD) |
| **Test** | Source whisper at 996.5: "built themselves a prison of" — words: built@996.500, themselves@996.920, a@997.600, prison@998.260, of@998.720. Output whisper: "a prison of a currency" — words: a@0.000, prison@0.260, of@0.740, a@1.460, currency@1.520. Full first word "a" present, "prison" not truncated. cut_in/cut_out unchanged by 0c277198 (Amendment 2 6g confirmed). |

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
| **Status** | fixed |
| **Cause** | `render_vo_visual_vert()` extracted BG frame from preceding vertical clip (vert_clip_01). That clip uses stack2/single layout leaving 486+490 rows of black bands (51% letterboxed). BG was blurred with bands intact, creating a letterboxed slit instead of full-bleed. Confidence: HIGH |
| **Commit** | pending (S7 edit in render_vertical.py) |
| **Test** | `test_g14_g15.py::TestS7BlackBandDetection` — 3 tests: synthetic letterbox detected + cropped to full-bleed (0 black rows), full-bleed source unchanged, real bridge BG confirmed >20% black bands. All PASS. |
| **Result** | Black band detection (threshold mean>20 per row) finds top_black=486, bot_black=504 (51%). Content region cropped and scaled to 1080x1920 before blur. After blur: row 0 mean=84.8, row 1919 mean=27.4 (comparable to intro BG which has row 1919=27.1). |
| **Evidence** | Pixel analysis of `vo_vert_bg_vo_bridge_01.png` vs `vo_vert_bg_vo_intro.png` |

### S8: VO grounding (M20)

| Field | Value |
|---|---|
| **Status** | HOLD (PBX editorial list) |
| **Cause** | VO claims more certainty than clips establish ("prove", categorical claims). Amendment 1 S8: flag only, agent writes no replacement VO lines. Sign-off stays as generated (approved register; signoff.py produces fresh per video). |
| **Commit** | N/A (flag-only, no code change) |
| **Test** | N/A |

### V12 / GPT: Portrait credits replay at frame 1510 / 62.917s

| Field | Value |
|---|---|
| **Status** | confirmed (independently verified by GPT, see GPT_APPROVED_BENCHMARK_ADDENDUM.md section 3) |
| **Cause** | v2e 9:16 credits card fades out by frame 1509 (62.875s) then abruptly returns at frame 1510 (62.917s). Grayscale mean jumps 2.075 -> 12.382. Same root cause as V02: stale frames from shared build dir. |
| **Commit** | 13b3319a (S2 aspect-isolated build dirs) |
| **Test** | G15 must verify single exit with no return. |

## Superseded (by Amendment 1 / new PBX outro)
- V09: Portrait outro on black — approved portrait uses landscape stinger on black canvas (GPT retraction)
- V10: Dark/quiet ending — approved reference also has dark/quiet terminal fade (reclassified as policy conflict)
- V11: Flare/green glitch — approved reference includes same flare/glitch/streaks (GPT retraction)
- All three close as "superseded by new PBX outro" (Amendment 1 section 2), no code change beyond the outro swap.

### Credits entrance (~0.29s dark at 54.0)

| Field | Value |
|---|---|
| **Status** | CLOSED (matches reference, Amendment 2 6e) |
| **Cause** | Orchestrator measured signalstats YAVG (limited range) across guest-to-card join in all four files. v12: 84 then 17,18,19,19,20...26. v17: 71 then same 17...26 curve. v2e16: 116 then 17,18,18,19,19...26. v2e9: 109 then 17...26. Same card fade-in progression, no inserted black frames. |
| **Commit** | N/A (no code change, no brightness rule added) |
| **Test** | N/A |

## HOLD items (PBX decides)
- Sign-off wording (approved register, signoff.py produces fresh per video)
- Clip 2 completeness and clip 3 "they" antecedent (PBX editorial list)
- VO grounding / certainty claims (S8, flag only)
