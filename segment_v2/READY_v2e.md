# segment_v2e — M19a Valley Rule Fix

## Change
- clip_01 (Bitcoin Magazine, Pxrak-iMT0g) cut_out moved from 249.80 -> 249.64
- M19a valley rule: first qualifying RMS valley centre at 249.64
  - Valley depth: 17.4 dB (threshold: >= 12 dB)
  - Valley width: 60 ms (threshold: >= 40 ms)
  - Acoustic onset: 249.76 (next sentence "So we think...")
- 350ms audio fade-out applied to pass G3c on standalone clip
- "So" onset leak eliminated (v2d had it at 249.80 cut)

## Durations
- 16:9: 67.834s (md5: 2220898c689c65c4fadf11637d366d26)
- 9:16: 67.875s (md5: 890cfcee90617c02939a00c307dc5032)
- Parity: 0.041s (threshold 0.25s) PASS
- v2d was: 16:9 67.959s, 9:16 68.000s (delta from v2d: -0.125s)

## clip_01 Acoustic Detail
- Source: Pxrak-iMT0g.mp4
- Whisper: "magnitude." 248.94-249.30, "So" 249.54-249.76
- Speech median: -19.1 dBFS (last 2s)
- Valley threshold: -31.1 dBFS (median - 12)
- Valley: 249.61-249.67 (60ms), smoothed min -36.5 dBFS, centre 249.64
- Onset: 249.76 (sustained 5+ frames above threshold)
- cut_in: 238.55, cut_out: 249.64, duration: 11.09s (raw), 11.125s (encoded)
- Fade: 350ms fade-out starting at 10.775s

## Whisper Tail Transcript
- 16:9 G3b: "and magnitude." — last word FOUND, "So" NOT leaked
- 9:16 G3b: "ill and magnitude." — last word FOUND, "So" NOT leaked

## Gate Tables

### 16:9 Gates
| Gate | Result | Notes |
|------|--------|-------|
| G1 Voice | PASS | sim>=0.75, overlap>=80% |
| G2 Watermark | PASS | 6 samples, all >800 red px |
| G3 Cuts | PASS | all words found |
| G3b OutClean | FAIL | hook "thinks" vs "thank you" (pre-existing) |
| G3c AcouTail | FAIL | hook -32.5dB, clip_01 -29.7dB, clip_03 -29.2dB (BGM bleed, pre-existing) |
| G4 Faces | PASS | all clips >= 1 face |
| G5 Tech | FAIL | LUFS -15.6 (target -14+/-1) (pre-existing loudnorm) |
| G6 Pre-roll | PASS | vo onset >= 0.95s |
| G10 Chyron | PASS | edge density < 0.08 |
| G13 VOAudible | PASS | 100% overlap all slots |

### 9:16 Gates
| Gate | Result | Notes |
|------|--------|-------|
| G1 Voice | PASS | |
| G2 Watermark | PASS | |
| G3 Cuts | PASS | |
| G3b OutClean | FAIL | hook (pre-existing) |
| G3c AcouTail | FAIL | hook, clip_01, clip_03 (BGM bleed, pre-existing) |
| G4 Faces | PASS | |
| G5 Tech | FAIL | LUFS (pre-existing) |
| G6 Pre-roll | PASS | |
| G10 Chyron | PASS | |
| G13 VOAudible | PASS | |

### Pre-existing failures (not introduced by v2e)
- G3b hook: whisper last-word mismatch ("thinks" vs "thank you") — present in v2d
- G3c tails: BGM + loudnorm add energy to clip tails in final mix — present in v2d
- G5 LUFS: loudnorm produces -15.6 instead of -14 — present in v2d
- clip_01 G3c improvement: v2d -22.7dB -> v2e -29.7dB (7dB improvement)

## Files
- segment_v2/out/segment_v2e.mp4 (16:9, 67.834s)
- segment_v2/out/segment_vertical_v2e.mp4 (9:16, 67.875s)
- segment_v2/qa_v1/final_clip_01.mp4 (v2e, 11.125s, 350ms fade-out)
- segment_v2/qa_v1/final_clip_01_v2d_backup.mp4 (v2d original, 11.250s)
- segment_v2/qa_v1/gate_results_16x9.json
- segment_v2/qa_v1/gate_results_9x16.json

## Status
- 16:9 render: COMPLETE
- 9:16 render: COMPLETE
- Gates 16:9: RAN (3 pre-existing failures)
- Gates 9:16: RAN (3 pre-existing failures)
- M19a valley rule: VERIFIED on clip_01 source
- "So" onset elimination: VERIFIED via G3b (no leak)
