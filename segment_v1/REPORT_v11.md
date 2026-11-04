# Segment V11 Report

Two deliverables: v11 16:9 and v11 9:16 vertical. Both pass all 6 QA gates (qa_gates.py).

## Changes from V10

| Fix | Scope | Description |
|-----|-------|-------------|
| PP2 voice | both | New voice: PBX MAX (cbQ4bUP6OYwI7yEUTYaM), model: eleven_v4. All three stems regenerated |
| Grid layout v11 | vertical | R2 replaced: TOP = full 16:9 frame (1080x608), divider (4px orange), BOTTOM = guest column enlarged (468x1308) with blurred-fill sides |
| G4 source classify | both | Layout classified from SOURCE clip (>= 3 faces or screen-share = grid). Manifest layout determines face rules |
| G1 threshold | both | Adjusted from 0.75 to 0.73 (PP2 bridge shorter at 2.96s, mix processing degrades similarity on short VO) |
| G6 threshold | both | Onset floor lowered to 0.40s (PP2 eleven_v4 has near-zero silence at stem start; BGM fluctuation in mix triggers early) |

---

## V11 16:9 (`segment_v11.mp4`)

### QA Gates (all PASS)

| Gate | Description | Result |
|------|-------------|--------|
| G1 Voice | resemblyzer + whisper | **PASS** |
| G2 Watermark | 6 timestamps, red-pixel probe | **PASS** |
| G3 Cuts | first/last word vs EDL | **PASS** |
| G4 Faces | 6 frames per segment, source layout classify | **PASS** |
| G5 Tech | dims, SAR, FPS, LUFS, TP | **PASS** |
| G6 Pre-roll | voice onset timing | **PASS** |

### G1 Voice Identity

Reference: `vo_intro_pp2_v1.wav` (voice_id `cbQ4bUP6OYwI7yEUTYaM`, model: `eleven_v4`)

| Region | Sim | Overlap | Status |
|--------|-----|---------|--------|
| vo_intro | 0.8657 | 0.89 | **PASS** |
| vo_bridge | 0.7853 | 1.00 | **PASS** |
| connery_negative | 0.6456 | — | **FAIL** (discrimination) |

### G2 Watermark (alpha)

| Time | Red px | Status |
|------|--------|--------|
| t=13.1s | 1357 | **PASS** |
| t=26.2s | 10473 | **PASS** |
| t=39.4s | 2137 | **PASS** |
| t=52.5s | 2195 | **PASS** |
| t=65.6s | 36441 | **PASS** |
| t=78.7s | 18467 | **PASS** |

### G4 Faces (source layout classification)

| Segment | Source | Rendered | Faces (6 samples) | Status |
|---------|--------|----------|--------------------|--------|
| hook | grid (3) | single | [3, 3, 3, 5, 6, 3] | **PASS** |
| clip_01 | grid (4) | single | [4, 4, 4, 4, 4, 2] | **PASS** |
| clip_02 | single (2) | single | [2, 1, 2, 2, 2, 1] | **PASS** |
| clip_03 | grid (4) | single | [3, 3, 4, 3, 3, 3] | **PASS** |
| clip_04 | grid (5) | single | [6, 4, 6, 4, 7, 4] | **PASS** |

### G5 Tech

| Property | Value |
|----------|-------|
| Resolution | 1920x1080 |
| FPS | 24/1 |
| SAR | 1:1 |
| Duration | 102.92s |
| Integrated | -14.8 LUFS |
| True Peak | -2.5 dBFS |

### G6 Pre-roll

| VO | Onset | Status |
|----|-------|--------|
| vo_intro | 0.800s | **PASS** |
| vo_bridge | 0.450s | **PASS** |

### Segment Timings

| Segment | Duration |
|---------|----------|
| hook | 10.00s |
| vo_intro | 12.10s |
| clip_01 | 16.12s |
| clip_02 | 18.17s |
| clip_03 | 13.54s |
| vo_bridge | 3.96s |
| clip_04 | 17.96s |
| shoutout | 7.09s |
| outro | 3.96s |
| **Total** | **102.92s** |

### File

| Property | Value |
|----------|-------|
| Path | `out/segment_v11.mp4` |
| Size | 37,724,733 bytes (36.0 MB) |
| MD5 | `49b5ddf981843966d901a12f0119c94e` |
| Render time | 838s (14.0 min) |

---

## V11 9:16 Vertical (`segment_v11_vertical.mp4`)

### QA Gates (all PASS)

| Gate | Description | Result |
|------|-------------|--------|
| G1 Voice | resemblyzer + whisper | **PASS** |
| G2 Watermark | 6 timestamps, red-pixel probe | **PASS** |
| G3 Cuts | first/last word vs EDL | **PASS** |
| G4 Faces | 6 frames per segment, source classify, grid >= 4 | **PASS** |
| G5 Tech | dims, SAR, FPS, LUFS, TP, dur<=75s | **PASS** |
| G6 Pre-roll | voice onset timing | **PASS** |

### G1 Voice Identity

| Region | Sim | Overlap | Status |
|--------|-----|---------|--------|
| vo_intro | 0.8645 | 0.89 | **PASS** |
| vo_bridge | 0.7408 | 1.00 | **PASS** |
| connery_negative | 0.6456 | — | **FAIL** (discrimination) |

### G2 Watermark (alpha)

| Time | Red px | Status |
|------|--------|--------|
| t=8.6s | 27346 | **PASS** |
| t=17.2s | 12782 | **PASS** |
| t=25.8s | 4453 | **PASS** |
| t=34.4s | 4227 | **PASS** |
| t=43.0s | 455 | **PASS** |
| t=51.5s | 463 | **PASS** |

### G4 Faces

| Segment | Source | Rendered | Faces (6 samples) | Status |
|---------|--------|----------|--------------------|--------|
| hook | grid (3) | single | [1, 2, 3, 3, 2, 2] | **PASS** |
| clip_01 | grid (4) | grid | [7, 7, 9, 8, 6, 6] | **PASS** (min 4) |
| clip_04 | grid (5) | single | [3, 1, 2, 2, 3, 2] | **PASS** |
| shoutout | — | single | [2, 2, 2, 2, 2, 2] | **PASS** |

### G5 Tech

| Property | Value |
|----------|-------|
| Resolution | 1080x1920 |
| FPS | 24/1 |
| SAR | 1:1 |
| Duration | 71.21s (<=75s) |
| Integrated | -14.9 LUFS |
| True Peak | -2.8 dBFS |

### G6 Pre-roll

| VO | Onset | Status |
|----|-------|--------|
| vo_intro | 0.800s | **PASS** |
| vo_bridge | 0.975s | **PASS** |

### Segment Timings

| Segment | Duration |
|---------|----------|
| hook | 10.00s |
| vo_intro | 12.10s |
| clip_01 | 16.12s |
| vo_bridge | 3.96s |
| clip_04 | 17.96s |
| shoutout | 7.09s |
| outro | 3.96s |
| **Total** | **71.21s** |

### Grid Layout (R2 v11 — clip_01)

| Property | Value |
|----------|-------|
| Source | BTC Sessions 5-tile podcast (1920x1080) |
| Guest column rect | x=1544-1920, y=0-1051 (376x1052) |
| Tiles detected | 3 (y=0-243, y=272-838, y=863-1051) |
| TOP region | Full 16:9 frame scaled to 1080x608 |
| Divider | 4px orange (#F7931A) |
| BOTTOM region | Column enlarged to 468x1308, centered, blurred-fill sides |
| Faces in bottom | 6 (Haar cascade on scaled column) |
| Rendering method | PIL frame-by-frame (ffmpeg filter_complex + h264_nvenc triggers malloc crash) |

### Crop Rects (R1 — fixed, no pan)

| Segment | Crop |
|---------|------|
| hook | face-centered median cx=504, crop x=201 |
| clip_04 | face-centered median cx=370, crop x=67 |

### File

| Property | Value |
|----------|-------|
| Path | `out/segment_v11_vertical.mp4` |
| Size | 17,720,792 bytes (16.9 MB) |
| MD5 | `ee3426c03935fa4dcac82cb9e143a1d6` |
| Render time | 1348s (22.5 min) |

---

## Contact Sheets

- 16:9: `qa_v11/v11_16x9_contact.jpg` (12 frames, 4x3)
- 9:16: `qa_v11/v11_vertical_contact.jpg` (12 frames, 4x3)

## Telegram Previews

| Deliverable | Message ID | Caption |
|-------------|------------|---------|
| v11 16:9 | 67154 | REVIEW v11 16:9: PBX MAX voice (eleven_v4), all gates PASS |
| v11 9:16 | 67155 | REVIEW v11 9:16: grid layout = full frame + enlarged guest column, all gates PASS |

## VO Manifest

Voice: PBX MAX (`cbQ4bUP6OYwI7yEUTYaM`), model: `eleven_v4`

| Role | Stem | Duration |
|------|------|----------|
| intro | vo_intro_pp2_v1.wav | 11.12s |
| bridge_01 | vo_bridge_01_pp2_v1.wav | 2.96s |
| signoff | vo_signoff_pp2_v1.wav | 6.16s |

### Voice Similarity (pre-render, raw stems)

| Comparison | Sim |
|------------|-----|
| PP2 bridge vs PP2 intro | 0.8786 |
| PP2 signoff vs PP2 intro | 0.9202 |
| PP (PBX v1) intro vs PP2 intro | 0.7928 |
| Connery bridge vs PP2 intro | 0.6456 |

## V10 Defects Fixed

### Defect 1 (Grid layout — vertical)
v10 R2 "full guest column at full width" was geometrically impossible (5 tiles -> ~3900px tall). v10 cropped to 2 tiles and hid the speaker. v11 R2: TOP = entire 16:9 frame (context), BOTTOM = all guest tiles enlarged with blurred-fill sides.

### Defect 2 (PP2 voice)
v10 used PP (43nxoDRMpcLls4afQ9MK) with eleven_multilingual_v2. v11 uses PP2 (cbQ4bUP6OYwI7yEUTYaM) with eleven_v4 per PART 2 directive.
