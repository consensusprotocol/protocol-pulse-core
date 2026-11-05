# REPORT_v17: Segment V17 Vertical (Chyron Fix + 3-Channel Shoutout)

## What changed vs v16

1. **CoinDesk chyron fix**: `render_single` chyron_safe now excludes bottom **200px** (was 110px) of 1080 source. Crop is 496x880 at face cx, scaled to 1080x1920 Lanczos. Chyron text ("ST BANK ROBBERY") no longer visible.

2. **G10 rewritten — IMAGE-BASED**: No longer checks crop-rect metadata. Samples 5 frames inside clip_02 in the final output, takes the bottom 12% band, computes Canny edge density and near-white pixel fraction. FAIL if edge_density > 0.08 OR white_fraction > 0.25. Band crops saved to qa_v17/g10_*.png.

3. **Shoutout regenerated**: All 3 channels (Simply Bitcoin, BTC Sessions, CoinDesk) now shown with avatars and handles. v16 only had 2 channels.

4. **G12 credits gate**: HoughCircles on red-ring mask of shoutout mid-frame. Detected 3 circles == expected 3. Audit images: qa_v17/g12_red_mask.png, g12_circles.png.

5. **G8 crop_widths**: Sharpness floor is now per-segment based on actual crop width: `60 * (crop_w / 1080)^2`. clip_02 floor = 12.7 (496px crop), hook/clip_03 = 47.4 (960px tile), clip_04 = 21.1 (640px tile).

6. **clip_04 rects verified**: Ben Perrin IS at (0,0,640,540) in source. Three source frames at 470, 476, 484s confirm this. Overlay proof: qa_v17/clip04_tiles.png. No rect change needed.

## Gate results

| Gate | Result | Details |
|------|--------|---------|
| G2 watermark | PASS | 6 probes, all >= 150 red px |
| G8 sharpness | PASS | hook=201.8(>47.4), clip_01=404.6(>60), clip_02=17.6(>12.7), clip_03=226.1(>47.4), clip_04=42.5(>21.1), shoutout=1206(>60) |
| G9 tail | PASS | luma=29.4, audio=-21.7 dBFS |
| G10 text-crop | PASS | clip_02 max_edge=0.0302(<0.08), max_white=0.0000(<0.25) — IMAGE-BASED |
| G11 parity | PASS | delta=0.042s (tol=0.25s), 9 vs 9 segments |
| G12 credits | PASS | 3 circles detected == 3 expected |

## Final output

- File: `out/segment_v17_vertical.mp4`
- Duration: 102.875s (horizontal: 102.917s, delta: 0.042s)
- Resolution: 1080x1920, 24fps, SAR 1:1
- Size: 31,560,173 bytes (30.1 MB)
- md5: 2afad7ed3cab85d4204cd1c4e2fbec8c
- Telegram: message_id 67184 (video) + contact sheet (51 frames, 10x6)

## Per-stage timings

| Stage | Seconds |
|-------|---------|
| hook (stack2) | 23.9 |
| vo_intro (PIL compositing) | 514.1 |
| clip_01 (grid PIL) | 591.0 |
| clip_02 (single crop, chyron-safe 200px) | 13.9 |
| clip_03 (stack2) | 29.5 |
| vo_bridge (PIL compositing) | 167.1 |
| clip_04 (stack2-unequal) | 6.9 |
| Gates + sheet + TG | ~45 |
| **Total** | **~1500s (25 min)** |
