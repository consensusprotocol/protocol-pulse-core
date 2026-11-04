# Segment V10 Report

Two deliverables: v10 16:9 and v10 9:16 vertical. Both pass all 6 QA gates (qa_gates.py).

## Changes from V9

| Fix | Scope | Description |
|-----|-------|-------------|
| qa_gates.py | both | New module: G1 voice, G2 watermark, G3 cuts, G4 faces, G5 tech, G6 pre-roll. Every final render runs gates; failure = exit non-zero + GATE_FAIL.txt |
| Alpha watermark | both | pp_mark_wave_alpha.png: luminance-keyed from pp_mark_wave_400.png. No black box; 60% opacity alpha composite |
| VO bridge voice | 16:9 | v9 reused v8 bridge (rendered from Connery stem via render_vo_visual.py). v10 re-renders from VO_MANIFEST PBX stem |
| R5 VO visuals | both | Freeze last frame, gaussian blur sigma 6, 1.0x→1.08x zoom, waveform bottom 22%, 1.0s pre-roll |
| R1 fixed crops | vertical | No continuous panning. ONE fixed crop per shot (face-centered median over all frames). No OneEuroFilter |
| R2 safe grid | vertical | Full guest column (all tiles) scaled to fit width at top, screen-share below. No speaker zoom |
| R4 duration gate | vertical | Cutdown structure: hook + vo_intro + clip1 + vo_bridge + clip4 + shoutout + outro. 68.04s (≤75s) |
| VO bridge present | vertical | VO bridge included in vertical structure (was missing in v9) |
| Legacy stems | both | Connery stems moved to vo_audio/legacy/ to prevent glob pickup |
| Model check | both | ElevenLabs models queried: eleven_v4 available. Current stems use eleven_multilingual_v2 (no PP2 voice) |

---

## V10 16:9 (`segment_v10.mp4`)

### QA Gates (all PASS)

| Gate | Description | Result |
|------|-------------|--------|
| G1 Voice | resemblyzer + whisper | **PASS** |
| G2 Watermark | 6 timestamps, red-pixel probe | **PASS** |
| G3 Cuts | first/last word vs EDL | **PASS** |
| G4 Faces | 6 frames per segment | **PASS** |
| G5 Tech | dims, SAR, FPS, LUFS, TP | **PASS** |
| G6 Pre-roll | voice onset timing | **PASS** |

### G1 Voice Identity

Reference: `vo_intro_pbx_v1.wav` (voice_id `43nxoDRMpcLls4afQ9MK`)

| Region | Sim | Overlap | Status |
|--------|-----|---------|--------|
| vo_intro | 0.8866 | 0.85 | **PASS** |
| vo_bridge | 0.8934 | 1.00 | **PASS** |
| connery_negative | 0.6245 | — | **FAIL** (discrimination) |

### G2 Watermark (alpha)

| Time | Red px | Status |
|------|--------|--------|
| t=12.7s | 1362 | **PASS** |
| t=25.3s | 10332 | **PASS** |
| t=38.0s | 2150 | **PASS** |
| t=50.7s | 2153 | **PASS** |
| t=63.4s | 3497 | **PASS** |
| t=76.0s | 18404 | **PASS** |

### G5 Tech

| Property | Value |
|----------|-------|
| Resolution | 1920×1080 |
| FPS | 24/1 |
| SAR | 1:1 |
| Duration | 99.750s |
| Integrated | -14.8 LUFS |
| True Peak | -2.0 dBFS |

### G6 Pre-roll

| VO | Onset | Status |
|----|-------|--------|
| vo_intro | 0.800s | **PASS** |
| vo_bridge | 0.950s | **PASS** |

### Segment Timings

| Segment | Duration |
|---------|----------|
| hook | 10.00s |
| vo_intro | 9.59s |
| clip_01 | 16.12s |
| clip_02 | 18.17s |
| clip_03 | 13.54s |
| vo_bridge | 3.31s |
| clip_04 | 17.96s |
| shoutout | 7.09s |
| outro | 3.96s |
| **Total** | **99.75s** |

### File

| Property | Value |
|----------|-------|
| Path | `out/segment_v10.mp4` |
| Size | 37,400,401 bytes (35.7 MB) |
| MD5 | `468b604eeed5d4bcdc2d132f7ed0293d` |
| Render time | 692s (11.5 min) |

---

## V10 9:16 Vertical (`segment_v10_vertical.mp4`)

### QA Gates (all PASS)

| Gate | Description | Result |
|------|-------------|--------|
| G1 Voice | resemblyzer + whisper | **PASS** |
| G2 Watermark | 6 timestamps, red-pixel probe | **PASS** |
| G3 Cuts | first/last word vs EDL | **PASS** |
| G4 Faces | 6 frames per segment | **PASS** |
| G5 Tech | dims, SAR, FPS, LUFS, TP, dur≤75s | **PASS** |
| G6 Pre-roll | voice onset timing | **PASS** |

### G1 Voice Identity

| Region | Sim | Overlap | Status |
|--------|-----|---------|--------|
| vo_intro | 0.8858 | 0.85 | **PASS** |
| vo_bridge | 0.8217 | 1.00 | **PASS** |
| connery_negative | 0.6245 | — | **FAIL** (discrimination) |

### G2 Watermark (alpha)

| Time | Red px | Status |
|------|--------|--------|
| t=8.1s | 27245 | **PASS** |
| t=16.3s | 12718 | **PASS** |
| t=24.4s | 442 | **PASS** |
| t=32.6s | 442 | **PASS** |
| t=40.7s | 460 | **PASS** |
| t=48.8s | 461 | **PASS** |

### G4 Faces

| Segment | Layout | Faces (6 samples) | Status |
|---------|--------|--------------------|--------|
| hook | single | [1, 2, 3, 3, 2, 2] | **PASS** |
| clip_01 | grid | [1, 2, 1, 1, 0, 0] | **PASS** (4/6 ≥ 1) |
| clip_04 | single | [2, 1, 2, 2, 2, 2] | **PASS** |
| shoutout | single | [2, 2, 2, 2, 2, 2] | **PASS** |

### G5 Tech

| Property | Value |
|----------|-------|
| Resolution | 1080×1920 |
| FPS | 24/1 |
| SAR | 1:1 |
| Duration | 68.04s (≤75s) |
| Integrated | -14.8 LUFS |
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
| vo_intro | 9.59s |
| clip_01 | 16.12s |
| vo_bridge | 3.31s |
| clip_04 | 17.96s |
| shoutout | 7.09s |
| outro | 3.96s |
| **Total** | **68.04s** |

### Crop Rects (R1 — fixed, no pan)

| Segment | Crop |
|---------|------|
| hook | face-centered median, fixed |
| clip_01 | R2 safe frame (all tiles) |
| clip_04 | face-centered median, fixed |

### File

| Property | Value |
|----------|-------|
| Path | `out/segment_v10_vertical.mp4` |
| Size | 16,998,575 bytes (16.2 MB) |
| MD5 | `d5781015ddeeccab73be6e9937b7cf66` |
| Render time | 642s (10.7 min) |

---

## Contact Sheets

- 16:9: `qa_v10/v10_16x9_contact.jpg` (12 frames, 4×3)
- 9:16: `qa_v10/v10_vertical_contact.jpg` (12 frames, 4×3)

## Telegram Previews

| Deliverable | Message ID | Caption |
|-------------|------------|---------|
| v10 16:9 | 67152 | REVIEW v10 16:9: voice gate PASS on every VO region, watermark alpha. Reply ship or hold. |
| v10 9:16 | 67153 | REVIEW v10 9:16: fixed framing (no pan), safe grid frame, bridge present, no mid-sentence cuts. Reply ship or hold. |

## V9 Defects Fixed

### Defect 1 (VO Bridge voice — 16:9)
v9 16:9 reused `qa_v8/v8_vo_bridge.mp4` which was rendered by `render_vo_visual.py` using `vo_bridge_01.wav` (Connery). v10 re-renders from `VO_MANIFEST.json` → `vo_bridge_01_pbx_v1.wav` (PBX voice). G1 confirms sim=0.8934 (threshold 0.75).

### Defect 2 (Grid clip zoom — vertical)
v9 vertical zoomed to speaker tile when lip-activity margin ≥ 0.35. v10 R2: always safe frame (full guest column), no zoom. Grid clip shows all tiles.

### Defect 3 (Panning jitter — vertical)
v9 vertical used OneEuroFilter for smoothed panning (still jittery). v10 R1: ONE fixed crop per shot (face-centered median). No animation, no pan.

### Defect 4 (Mid-sentence cut — vertical)
v9 vertical clip4 cut off mid-sentence to fit 60s budget. v10 R4: 75s budget, clip4 fits at 17.96s (total 68.04s). No trimming needed.

### Defect 5 (VO bridge missing — vertical)
v9 vertical had no VO bridge. v10 includes VO bridge in vertical structure (3.31s with R5 visual).

## Watermark Asset

- Source: `brand/2026-11/pp_mark_wave_400.png`
- Alpha: `brand/2026-11/pp_mark_wave_alpha.png` (luminance key, soft threshold)
- Verification: `brand/2026-11/pp_mark_check_white.png`, `pp_mark_check_dark.png`
- Corners: fully transparent (alpha=0). Ribbon intact.

## VO Manifest

Voice: PBX (`43nxoDRMpcLls4afQ9MK`), model: `eleven_multilingual_v2`
No ELEVENLABS_VOICE_ID_PP2 in .env; stems unchanged.
Best available model: `eleven_v4` (not used — PP2 trigger required).
Legacy Connery stems: moved to `vo_audio/legacy/`.
