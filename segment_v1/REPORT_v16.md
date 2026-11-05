# REPORT_v16: Segment V16 Vertical (9:16, Full Program Parity)

## What changed vs v15

1. **Full program parity**: ALL 9 segments from horizontal, same order.
   - v15 had 7 segments (71s, missing clip_02 and clip_03)
   - v16 has 9 segments (102.9s, identical to horizontal)

2. **Audio from horizontal**: Extracted from `out/segment_v12.mp4` and muxed over vertical video — audio identical by construction. No separate BGM/loudnorm pass needed.

3. **Three layouts by hand table** (no detector decides layout):
   - **A. single**: fixed crop on one face (clip_02 CoinDesk, chyron-safe)
   - **B. stack2**: two source rects, each scaled to 1080x960, speaker TOP (hook, clip_03, clip_04)
   - **C. grid**: full frame top + enlarged guest column bottom (clip_01 only)

4. **stack2 layout**: New. Two 960x1080 halves from source, each scaled to fill 1080x960, stacked vertically. Speaker determined by lip-activity score on mouth band of each rect.

5. **stack2-unequal** (clip_04): Two 640x540 rects → each 1080x911, centered with 49px black bars top/bottom.

6. **G10 chyron-safe**: clip_02 crop excludes bottom 110px of 1080 source (crop_bottom=970=chyron_top). PASS.

7. **G11 parity gate**: Duration delta 0.042s (tolerance 0.25s), segment count 9=9. PASS.

## Segment order (mirrors horizontal)

| # | Label | Duration | Layout | Source |
|---|-------|----------|--------|--------|
| 1 | hook | 10.00s | stack2 | bSmF (Simply Bitcoin) |
| 2 | vo_intro | 12.08s | VO visual | — |
| 3 | clip_01 | 16.12s | grid | Eojd (BTC Sessions) |
| 4 | clip_02 | 18.17s | single (chyron-safe) | 7QIB (CoinDesk) |
| 5 | clip_03 | 13.54s | stack2 | bSmF (Simply Bitcoin) |
| 6 | vo_bridge | 3.96s | VO visual | — |
| 7 | clip_04 | 17.96s | stack2-unequal | Eojd (BTC Sessions) |
| 8 | shoutout | 7.09s | pre-rendered 9:16 | — |
| 9 | outro | 3.96s | pre-rendered 9:16 | — |

## Lip-activity decisions

| Shot | rect_a score | rect_b score | Speaker | Meaning |
|------|-------------|-------------|---------|---------|
| hook | 0.0428 | 0.0079 | a (left=TOP) | Ben Perrin speaking |
| clip_03 | 0.0398 | 0.0761 | b (right=TOP) | Right-side speaker |
| clip_04 | — | — | fixed TOP | Adam O'Brien (verified from transcript) |

## Gate results

| Gate | Result | Details |
|------|--------|---------|
| G2 watermark | PASS | 6 probes, all ≥150 red px |
| G8 sharpness | PASS | hook=201.8, clip_01=404.6, clip_02=28.6, clip_03=226.1, clip_04=42.5, shoutout=1206 |
| G9 tail | PASS | luma=29.4, audio=-21.7 dBFS |
| G10 text-crop | PASS | clip_02 crop_bottom=970=chyron_top |
| G11 parity | PASS | delta=0.042s (tol=0.25s), 9 vs 9 segments |

## Per-stage timings

| Stage | Seconds |
|-------|---------|
| hook (stack2) | 24.3 |
| vo_intro (PIL compositing) | 515.4 |
| clip_01 (grid PIL) | 586.2 |
| clip_02 (single crop) | 13.8 |
| clip_03 (stack2) | 26.8 |
| vo_bridge (PIL compositing) | 168.6 |
| clip_04 (stack2-unequal) | 7.1 |
| Concat + watermark + mux + gates | ~145 |
| **Total** | **1487s (24.8 min)** |

## Final output

- File: `out/segment_v16_vertical.mp4`
- Duration: 102.875s (horizontal: 102.917s, delta: 0.042s)
- Resolution: 1080x1920, 24fps, SAR 1:1
- Size: 31,279,435 bytes (29.8 MB)
- md5: 0197530cfb4335630b2b4f76f82041d7
- Telegram: message_id 67181 (video) + contact sheet (51 frames, 10x6)
