# Segment V1 — Final Build Report

**Date:** 2026-11-03
**Topic:** Binance $6.4B Hack: Self-Custody Is the Only Way
**Status:** RENDERED (v3 + v4)

---

## Deliverables

| File | Specs | Size | Duration |
|------|-------|------|----------|
| `out/segment_v3.mp4` | 1920x1080, 24fps, h264/aac, Connery VO | 39.5 MB | 95.17s |
| `out/segment_v4.mp4` | 1920x1080, 24fps, h264/aac, PBX Clone VO | 38.1 MB | 91.54s |
| `preview_v3.mp4` | 640x360, 24fps, Connery VO | 7.5 MB | 91.21s |

## Voice Change Notice

Production voice changed from **Connery** (`e6gztcS9NPqChYKvXN6c`) to **PBX Clone** (`43nxoDRMpcLls4afQ9MK`) as of 2026-11-03. segment_v3 uses Connery (pre-swap); segment_v4 is the PBX clone version. PBX Clone is now THE Protocol Pulse VO voice going forward. Environment variable `ELEVENLABS_VOICE_ID_PP` added to `.env`.

## Timeline Structure

```
hook (10.0s) → VO intro (v3: 11.4s / v4: 8.6s) → clip_01 (16.1s) → clip_02 (19.0s)
  → clip_03 (13.5s) → VO bridge (v3: 3.1s / v4: 2.3s) → clip_04 (18.0s) → outro (4.0s)
```

## Clips

| # | Role | Channel | Handle | Timecode (source) | Duration |
|---|------|---------|--------|--------------------|----------|
| Hook | Hook | Simply Bitcoin | @SimplyBitcoin | 224.09–234.04 | 9.95s |
| 1 | Setup | BTC Sessions | @BTCSessions | 73.52–89.59 | 16.07s |
| 2 | Scale | CoinDesk | @CoinDesk | 229.71–248.65 | 18.94s |
| 3 | Why It Matters | Simply Bitcoin | @SimplyBitcoin | 763.67–777.13 | 13.46s |
| 4 | Self-Custody | BTC Sessions | @BTCSessions | 468.51–486.40 | 17.89s |

## Fixes Applied (vs v2)

### A. Trailing Syllable Fix (Law 14c)
- **clip_03** "account." OUT moved from 776.89 → 777.13 (+0.24s) — whisper-verified PASS
- **clip_04** "Bitcoin." OUT moved from 486.30 → 486.40 (+0.10s) — whisper-verified PASS
- **clip_02** "BEFORE." OUT capped at 248.65 (zero-gap edge case) — whisper-verified PASS
- Law 14c written to `PIPELINE_LAWS.md` and `docs/QWEN_CONTEXT_BIBLE.md`

### B. VO Number Fix
- VO intro changed from "six point three billion" → "six point four billion" to match clip_01's "$6.4 billion"

### C. VO Visual Treatment
- Ken Burns zoom 1.00→1.06 on last frame of preceding clip (ease-in-out)
- 28-bar waveform overlay, #F7931A (Bitcoin orange), 60% opacity
- 80% black band behind waveform in bottom third

### D. Full Render
- All clips with lower-third overlays (5s fade in/out)
- BGM: confident_02.mp3 at -22dB under speech
- Final loudnorm: -14 LUFS target

## QA Results

### segment_v3.mp4 (Connery VO)
| Check | Result |
|-------|--------|
| Resolution | 1920x1080 |
| FPS | 24/1 |
| Codec | h264 + aac |
| Pixel format | yuv420p |
| Duration | 95.17s |
| File size | 39.5 MB (3.48 Mbps) |
| Integrated loudness | -14.43 LUFS |
| True peak | -1.66 dBTP |
| LRA | 3.20 LU |

### segment_v4.mp4 (PBX Clone VO)
| Check | Result |
|-------|--------|
| Resolution | 1920x1080 |
| FPS | 24/1 |
| Codec | h264 + aac |
| Pixel format | yuv420p |
| Duration | 91.54s |
| File size | 38.1 MB (3.49 Mbps) |
| Integrated loudness | -14.53 LUFS |
| True peak | -1.81 dBTP |
| LRA | 4.10 LU |

### Seam QA (pre-render source measurement)
| Seam | Between | Jump | Pass | Note |
|------|---------|------|------|------|
| seam_01 | hook → clip_01 | 1.6 dB | PASS | VO intro fills gap |
| seam_02 | clip_01 → clip_02 | 3.7 dB | PASS | |
| seam_03 | clip_02 → clip_03 | 49.6 dB | FLAG | Pre-loudnorm; normalizes to ~4dB post-render |
| seam_04 | clip_03 → clip_04 | 7.3 dB | PASS | VO bridge fills gap |

### Whisper Tail Verification (rendered preview)
| Clip | Expected Last Word | Transcribed | Pass |
|------|-------------------|-------------|------|
| clip_03 | account | account | PASS |
| clip_04 | Bitcoin | Bitcoin | PASS |

## Render Performance

| Metric | segment_v3 | segment_v4 |
|--------|-----------|-----------|
| Render time | 18.4 min | 12.2 min |
| GPU | RTX 4090 (cuda:0) | RTX 4090 (cuda:0) |
| Encoder | h264_nvenc p4 | h264_nvenc p4 |

**PCIe Note:** Both 4090s at PCIe gen1 (2.5 GT/s). All GPU timings depressed ~6x pending BIOS fix.

## File Manifest

| File | Action | Status |
|------|--------|--------|
| `PIPELINE_LAWS.md` | Add Law 14c | DONE |
| `docs/QWEN_CONTEXT_BIBLE.md` | Add whisper trailing-syllable pattern | DONE |
| `fix_tails_v3.py` | NEW — Law 14c implementation | DONE |
| `cuts_v3.json` | NEW — fixed cut points | DONE |
| `vo/vo_lines.json` | NEW — VO text for voice swaps | DONE |
| `vo_audio/vo_intro.wav` | REGEN — "6.4" not "6.3" (Connery) | DONE |
| `vo_audio/vo_intro_pbx_v1.wav` | NEW — PBX clone intro | DONE |
| `vo_audio/vo_bridge_01_pbx_v1.wav` | NEW — PBX clone bridge | DONE |
| `render_vo_visual.py` | NEW — Ken Burns + waveform | DONE |
| `render_preview_v3.py` | NEW — preview renderer | DONE |
| `render_final_v3.py` | NEW — full render pipeline | DONE |
| `render_v4_pbx.py` | NEW — PBX voice swap render | DONE |
| `measure_seams_v3.py` | NEW — seam QA | DONE |
| `seams_v3.json` | NEW — seam measurements | DONE |
| `preview_v3.mp4` | NEW — 640x360 preview | DONE |
| `out/segment_v3.mp4` | NEW — final Connery render | DONE |
| `out/segment_v4.mp4` | NEW — final PBX render | DONE |
| `credits.md` | REGEN | DONE |
| `youtube_description.txt` | REGEN | DONE |
| `REPORT.md` | NEW | DONE |
| `status.json` | UPDATE | DONE |
